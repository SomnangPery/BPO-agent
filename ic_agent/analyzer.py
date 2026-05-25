import datetime
import json
import logging
import re
from typing import Any
from anthropic import Anthropic
from ic_agent.config import AGENT_MODEL, ANTHROPIC_API_KEY, LLM_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

def _call_llm(prompt: str) -> dict[str, Any]:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=AGENT_MODEL,
        max_tokens=4000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text
    # Clean possible markdown
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    try:
        return json.loads(text.strip())
    except Exception:
        logger.error("Failed to parse LLM JSON: %s", text)
        return {"error": "Invalid JSON from LLM"}

def analyze_project(project_name: str, classified_files: dict[str, Any]) -> dict[str, Any]:
    timestamp = datetime.datetime.now().isoformat()
    oppm = classified_files.get("oppm") or {}
    srs = classified_files.get("srs") or {}
    reports = classified_files.get("reports") or []

    # STEP 1 - OPPM Extraction
    step1_prompt = f"""
Return ONLY raw JSON. No markdown, no backticks, no explanation.
Extract everything from this OPPM document.
{{
  "project_title": "...",
  "skills": [...],
  "milestones": [...],
  "deliverables": [...],
  "timeline": [...],
  "total_count": int
}}
OPPM: {oppm.get("content", "No OPPM file found")}
"""
    oppm_summary = _call_llm(step1_prompt)

    # STEP 2 - SRS Extraction
    step2_prompt = f"""
Return ONLY raw JSON. No markdown, no backticks, no explanation.
Extract everything from this SRS document.
{{
  "system_name": "...",
  "features": [...],
  "modules": [...],
  "requirements": [...],
  "total_count": int
}}
SRS: {srs.get("content", "No SRS file found")}
"""
    srs_summary = _call_llm(step2_prompt)

    # STEP 3 - Validate report files
    validated_reports = []
    oppm_reqs = oppm_summary.get("deliverables", []) + oppm_summary.get("skills", [])
    srs_features = srs_summary.get("features", []) + srs_summary.get("requirements", [])
    
    for r in reports:
        step3_prompt = f"""
Return ONLY raw JSON. No markdown, no backticks, no explanation.
You are checking if this submitted file provides evidence of work toward any project requirement. 
You are NOT checking who submitted it.

OPPM requirements: {json.dumps(oppm_reqs)}
SRS features: {json.dumps(srs_features)}

FILE:
  Name: {r["file_name"]}
  Type: {r["mime_type"]}
  Content: {r["content"][:5000]}

A file is VALID if its content or name connects to ANY requirement. 
Early-stage work counts as valid. FAKE only if empty or unrelated.

{{
  "file_name": "{r["file_name"]}",
  "mime_type": "{r["mime_type"]}",
  "is_valid": true/false,
  "validity_reason": "...",
  "matches_oppm_item": "...",
  "matches_srs_item": "...",
  "evidence_type": "final_deliverable | work_in_progress | planning_evidence | no_evidence",
  "is_fake": true/false,
  "fake_reason": "...",
  "quality": "strong | moderate | weak",
  "quality_note": "..."
}}
"""
        val = _call_llm(step3_prompt)
        validated_reports.append(val)

    # STEP 4 - Progress Calculation
    step4_prompt = f"""
Return ONLY raw JSON. No markdown, no backticks, no explanation.
Calculate project completion using tiered coverage:
  completed    = file IS final deliverable → 100% credit
  in_progress  = active work → 50% credit
  planned      = discussed → 20% credit
  not_started  = no file → 0% credit

Project stage:
  0-15%   = Planning & Documentation Stage
  16-35%  = Early Development Stage
  36-60%  = Active Development Stage
  61-85%  = Testing & Refinement Stage
  86-100% = Finalization Stage

OPPM requirements: {json.dumps(oppm_reqs)}
SRS features: {json.dumps(srs_features)}
Validated files: {json.dumps(validated_reports)}

{{
  "total_requirements": int,
  "completion_percentage": float,
  "project_stage": "...",
  "stage_description": "...",
  "requirement_coverage": [
    {{
      "requirement": "...",
      "coverage_tier": "completed|in_progress|planned|not_started",
      "covered_by": "filename or null",
      "evidence": "..."
    }}
  ],
  "missing_items": [{{ "requirement": "...", "priority": "high|medium|low" }}],
  "valid_files": int,
  "fake_files": int,
  "fake_file_names": [...]
}}
"""
    progress = _call_llm(step4_prompt)

    # STEP 5 - Final Verdict
    step5_prompt = f"""
Return ONLY raw JSON. No markdown, no backticks, no explanation.
Give honest verdict for this project submission.
APPROVED (>=80% & no fake), IN_PROGRESS, NEEDS_REVIEW, REJECTED (fake or zero work).

{{
  "verdict": "APPROVED|IN_PROGRESS|NEEDS_REVIEW|REJECTED",
  "verdict_reason": "...",
  "confidence": int,
  "risk_flags": [],
  "strengths": [],
  "weaknesses": [],
  "ic_recommendation": "...",
  "project_feedback": "..."
}}

Project: {project_name}
Completion: {progress.get("completion_percentage", 0)}%
Stage: {progress.get("project_stage", "Unknown")}
Missing: {json.dumps(progress.get("missing_items", []))}
Fake: {json.dumps(progress.get("fake_file_names", []))}
"""
    verdict = _call_llm(step5_prompt)

    return {
        "project_name": project_name,
        "timestamp": timestamp,
        "oppm_summary": oppm_summary,
        "srs_summary": srs_summary,
        "file_validations": validated_reports,
        "progress": progress,
        "verdict": verdict
    }


# ============================================================================
# Compatibility wrappers for web.py
# ============================================================================

def analyze_student_work(student_id: int, classified_files: dict[str, Any], student_name: str = "") -> dict[str, Any]:
    """Compatibility wrapper: analyze student work (maps to analyze_project)."""
    return analyze_project(student_name or f"Student_{student_id}", classified_files)

def analyze_submission_report(classified_files: dict[str, Any], project_name: str = "") -> dict[str, Any]:
    """Compatibility wrapper: analyze submission report (maps to analyze_project)."""
    return analyze_project(project_name or "Submission", classified_files)
