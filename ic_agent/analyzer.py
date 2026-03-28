import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

from ic_agent.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS


logger = logging.getLogger(__name__)


def _safe_int(value: Any, default: int = 0) -> int:
	try:
		return int(value)
	except Exception:
		return default


def _normalize_percent(value: Any, field_name: str) -> int:
	parsed = _safe_int(value, 0)
	if parsed != value:
		logger.warning("Model %s was not an integer: %s", field_name, value)
	return max(0, min(100, parsed))


def _recommendation_from_score(score_percent: int) -> str:
	if score_percent >= 80:
		return "approve"
	if score_percent >= 50:
		return "review"
	return "reject"


def _fallback_weekly_summary(
	match_percent: int,
	authenticity_risk: str,
	matched_items: list[str],
	mismatch_items: list[str],
	suspicious_signals: list[str],
) -> str:
	return (
		f"Match {match_percent}%. "
		f"Authenticity risk is {authenticity_risk}. "
		f"Matched items: {len(matched_items)}, mismatches: {len(mismatch_items)}, "
		f"suspicious signals: {len(suspicious_signals)}."
	)


def _derive_error_types(
	authenticity_risk: str,
	mismatch_items: list[str],
	suspicious_signals: list[str],
) -> list[str]:
	error_types: list[str] = []
	combined = " ".join([*mismatch_items, *suspicious_signals]).lower()

	if authenticity_risk == "high":
		error_types.append("possible_fabrication")
	if len(mismatch_items) >= 2:
		error_types.append("oppm_srs_mismatch")
	if "vague" in combined or "unclear" in combined or "generic" in combined:
		error_types.append("vague_reporting")
	if "no evidence" in combined or "without evidence" in combined or "missing proof" in combined:
		error_types.append("missing_evidence")
	if "unrelated" in combined or "out of scope" in combined:
		error_types.append("out_of_scope_claim")
	if "timeline" in combined or "date mismatch" in combined or "inconsistent" in combined:
		error_types.append("timeline_inconsistency")

	if not error_types and suspicious_signals:
		error_types.append("suspicious_pattern")

	# Keep deterministic unique ordering.
	seen: set[str] = set()
	result: list[str] = []
	for item in error_types:
		if item not in seen:
			seen.add(item)
			result.append(item)
	return result


def _generate_with_ollama(prompt: str) -> str:
	if not OLLAMA_MODEL:
		raise ValueError("OLLAMA_MODEL is missing in environment variables")

	base_url = OLLAMA_BASE_URL.rstrip("/")

	# Prefer chat API for newer Ollama servers; fall back to generate for older ones.
	chat_endpoint = base_url + "/api/chat"
	chat_payload = {
		"model": OLLAMA_MODEL,
		"messages": [{"role": "user", "content": prompt}],
		"stream": False,
	}
	chat_body = json.dumps(chat_payload).encode("utf-8")
	chat_request = urllib.request.Request(
		chat_endpoint,
		data=chat_body,
		headers={"Content-Type": "application/json"},
		method="POST",
	)

	try:
		with urllib.request.urlopen(chat_request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
			chat_response_text = response.read().decode("utf-8")
		parsed_chat = json.loads(chat_response_text)
		chat_content = str(parsed_chat.get("message", {}).get("content", "")).strip()
		if chat_content:
			return chat_content
	except urllib.error.HTTPError as exc:
		if exc.code != 404:
			raise ValueError(f"Failed to call Ollama chat endpoint at {chat_endpoint}: {exc}") from exc
	except urllib.error.URLError as exc:
		raise ValueError(f"Failed to reach Ollama at {chat_endpoint}: {exc}") from exc
	except json.JSONDecodeError as exc:
		raise ValueError("Ollama chat endpoint returned non-JSON response") from exc

	generate_endpoint = base_url + "/api/generate"
	generate_payload = {
		"model": OLLAMA_MODEL,
		"prompt": prompt,
		"stream": False,
	}
	generate_body = json.dumps(generate_payload).encode("utf-8")
	generate_request = urllib.request.Request(
		generate_endpoint,
		data=generate_body,
		headers={"Content-Type": "application/json"},
		method="POST",
	)

	try:
		with urllib.request.urlopen(generate_request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
			generate_response_text = response.read().decode("utf-8")
	except urllib.error.URLError as exc:
		raise ValueError(f"Failed to reach Ollama at {generate_endpoint}: {exc}") from exc

	try:
		parsed_generate = json.loads(generate_response_text)
	except json.JSONDecodeError as exc:
		raise ValueError("Ollama generate endpoint returned non-JSON response") from exc

	model_text = str(parsed_generate.get("response", "")).strip()
	if not model_text:
		raise ValueError("Ollama returned an empty response")
	return model_text


def _extract_json_block(text: str) -> str:
	stripped = text.strip()
	if stripped.startswith("{") and stripped.endswith("}"):
		return stripped

	code_fence_match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
	if code_fence_match:
		return code_fence_match.group(1)

	generic_fence_match = re.search(r"```\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
	if generic_fence_match:
		return generic_fence_match.group(1)

	object_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
	if object_match:
		return object_match.group(1)

	first_brace = text.find("{")
	last_brace = text.rfind("}")
	if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
		return text[first_brace : last_brace + 1]

	raise ValueError("No JSON object found in model response")


def _parse_model_json_response(raw_response_text: str, schema_name: str) -> dict[str, Any]:
	try:
		json_text = _extract_json_block(raw_response_text)
		return json.loads(json_text)
	except Exception:
		pass

	# Self-heal: ask model to convert prior response into strict JSON only.
	repair_prompt = f"""
You are a JSON repair formatter.

Task:
Convert the following response into ONLY valid JSON object for schema: {schema_name}.

Rules:
- Output JSON object only
- No markdown, no explanation
- Use double-quoted JSON strings
- If a field is missing, fill with a safe default

Response to convert:
{raw_response_text}
""".strip()

	repaired_text = _generate_with_ollama(repair_prompt)
	json_text = _extract_json_block(repaired_text)
	return json.loads(json_text)


def analyze_student_work(student_name: str, oppm_content: str, srs_content: str) -> dict[str, Any]:
	prompt = f"""
You are an academic evaluation assistant for an Incubation Center.

Evaluate the student's work by comparing OPPM required skills against the SRS evidence.

Instructions:
1) Read the OPPM skill sheet and extract the full list of required skills.
2) Read the SRS document and evaluate whether the student demonstrated each required skill.
3) Produce ONLY valid JSON (no markdown, no commentary) with this exact schema:
{{
  "matched_skills": ["..."],
  "missing_skills": ["..."],
  "score_percent": 0,
  "summary": "...",
  "recommendation": "approve"
}}

Rules:
- recommendation must be one of: "approve", "review", "reject"
- score_percent must be an integer from 0 to 100
- matched_skills and missing_skills must be arrays of strings
- summary should be concise and explain major strengths and gaps

Student Name: {student_name}

OPPM SKILL SHEET:
{oppm_content}

SRS DOCUMENT:
{srs_content}
""".strip()

	response_text = _generate_with_ollama(prompt)

	parsed = _parse_model_json_response(response_text, "student_skill_analysis")

	# Normalize and guard against partial model responses.
	matched = parsed.get("matched_skills", [])
	missing = parsed.get("missing_skills", [])
	score = parsed.get("score_percent", 0)
	summary = str(parsed.get("summary", "")).strip()
	recommendation = str(parsed.get("recommendation", "review")).strip().lower()
	if recommendation not in {"approve", "review", "reject"}:
		recommendation = "review"

	try:
		score = int(score)
	except Exception:
		logger.warning("Model score_percent was not an integer: %s", score)
		score = 0
	score = max(0, min(100, score))

	return {
		"matched_skills": [str(item) for item in matched],
		"missing_skills": [str(item) for item in missing],
		"score_percent": score,
		"summary": summary,
		"recommendation": recommendation,
	}


def analyze_weekly_report(
	student_name: str,
	oppm_content: str,
	srs_content: str,
	report_content: str,
) -> dict[str, Any]:
	prompt = f"""
You are an academic integrity evaluator for an Incubation Center.

Goal:
Assess whether the WEEKLY REPORT is consistent with OPPM plan and SRS scope.
Identify suspicious/fake reporting signals.

Return ONLY valid JSON with this exact schema:
{{
  "match_percent": 0,
  "authenticity_risk": "low",
  "matched_items": ["..."],
  "mismatch_items": ["..."],
  "suspicious_signals": ["..."],
	"error_types": ["..."] ,
  "summary": "...",
  "recommendation": "approve"
}}

Rules:
- authenticity_risk must be one of: "low", "medium", "high"
- recommendation must be one of: "approve", "review", "reject"
- match_percent must be integer 0..100
- error_types is an array of one or more from this list when issues exist:
	"possible_fabrication", "oppm_srs_mismatch", "vague_reporting", "missing_evidence", "out_of_scope_claim", "timeline_inconsistency", "suspicious_pattern"
- if no issue exists, return an empty error_types array
- Be strict about fake indicators: vague claims, no concrete progress, claims unrelated to OPPM/SRS.
- Scoring rubric for match_percent (use this range logic):
	- 90-100: Strong concrete alignment to OPPM/SRS, specific deliverables, minimal mismatch.
	- 75-89: Good alignment with clear evidence, minor gaps.
	- 50-74: Partial alignment; some unclear claims or notable mismatch.
	- 25-49: Weak alignment; multiple mismatches, mostly vague progress.
	- 0-24: No credible alignment or clearly suspicious/fabricated reporting.
- recommendation must follow score range:
	- 80-100 => "approve"
	- 50-79 => "review"
	- 0-49 => "reject"

Student Name: {student_name}

OPPM (plan/tasks/schedule):
{oppm_content}

SRS (project requirements/scope):
{srs_content}

WEEKLY REPORT (submitted work):
{report_content}
""".strip()

	response_text = _generate_with_ollama(prompt)

	parsed = _parse_model_json_response(response_text, "weekly_report_integrity_analysis")

	match_percent = _normalize_percent(parsed.get("match_percent", 0), "match_percent")
	authenticity_risk = str(parsed.get("authenticity_risk", "medium")).strip().lower()
	if authenticity_risk not in {"low", "medium", "high"}:
		authenticity_risk = "medium"

	matched_items = [str(item) for item in parsed.get("matched_items", [])]
	mismatch_items = [str(item) for item in parsed.get("mismatch_items", [])]
	suspicious_signals = [str(item) for item in parsed.get("suspicious_signals", [])]
	allowed_error_types = {
		"possible_fabrication",
		"oppm_srs_mismatch",
		"vague_reporting",
		"missing_evidence",
		"out_of_scope_claim",
		"timeline_inconsistency",
		"suspicious_pattern",
	}
	error_types = [
		str(item).strip().lower()
		for item in parsed.get("error_types", [])
		if str(item).strip().lower() in allowed_error_types
	]

	# Guardrails keep score inside practical ranges when report quality flags are high.
	if authenticity_risk == "high" and match_percent > 59:
		match_percent = 59
	if len(suspicious_signals) >= 3 and match_percent > 49:
		match_percent = 49
	if len(mismatch_items) > len(matched_items) and match_percent > 64:
		match_percent = 64
	if authenticity_risk == "high" and "possible_fabrication" not in error_types:
		error_types.append("possible_fabrication")
	if not error_types:
		error_types = _derive_error_types(authenticity_risk, mismatch_items, suspicious_signals)

	recommendation = _recommendation_from_score(match_percent)

	summary = str(parsed.get("summary", "")).strip()
	if not summary:
		summary = _fallback_weekly_summary(
			match_percent,
			authenticity_risk,
			matched_items,
			mismatch_items,
			suspicious_signals,
		)

	return {
		"match_percent": match_percent,
		"score_percent": match_percent,
		"authenticity_risk": authenticity_risk,
		"matched_items": matched_items,
		"matched_skills": matched_items,
		"mismatch_items": mismatch_items,
		"missing_skills": mismatch_items,
		"suspicious_signals": suspicious_signals,
		"error_types": error_types,
		"summary": summary,
		"recommendation": recommendation,
	}

