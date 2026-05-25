import re
import unicodedata
from typing import List, Optional


def _clean_text(text: str) -> str:
    if text is None:
        return ""
    value = unicodedata.normalize("NFKD", text)
    value = value.strip()
    value = re.sub(r"[\r\n]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def _extract_student_name_from_filename(filename: str) -> Optional[str]:
    if not filename:
        return None

    name = filename.rsplit(".", 1)[0]
    name = name.replace("_", " ").replace("-", " ")
    name = _clean_text(name)
    name = re.sub(r"\b(oppm|srs|report|submission|final|draft|student|project|document|docx|pdf|pptx|xlsx|v\d+)\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip()
    if not name or len(name) < 2:
        return None
    return name


def _identifier_from_name(name: str) -> str:
    value = _clean_text(name)
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    return value or "unknown"


def _format_detailed_project_summary(
    project_name: str,
    completion: int,
    reports: int,
    score: int,
    recommendation: str,
    matched_items: List[str],
    missing_items: List[str],
    suspicious_signals: List[str],
    summary: str,
) -> str:
    parts = [
        f"Project: {project_name}",
        f"Completion: {completion}%",
        f"Reports: {reports}",
        f"Score: {score}",
        f"Recommendation: {recommendation}",
        "",
        "Summary:",
        summary,
    ]
    if matched_items:
        parts.append("")
        parts.append("Matched items:")
        parts.extend(f"- {item}" for item in matched_items)
    if missing_items:
        parts.append("")
        parts.append("Missing items:")
        parts.extend(f"- {item}" for item in missing_items)
    if suspicious_signals:
        parts.append("")
        parts.append("Suspicious signals:")
        parts.extend(f"- {item}" for item in suspicious_signals)
    return "\n".join(parts)


def _format_detailed_student_summary(
    name: str,
    total: int,
    completed: int,
    pending: int,
    score: int,
    recommendation: str,
    matched_items: List[str],
    missing_items: List[str],
    suspicious_signals: List[str],
    summary: str,
) -> str:
    parts = [
        f"Student: {name}",
        f"Total tasks: {total}",
        f"Completed: {completed}",
        f"Pending: {pending}",
        f"Score: {score}",
        f"Recommendation: {recommendation}",
        "",
        "Summary:",
        summary,
    ]
    if matched_items:
        parts.append("")
        parts.append("Matched items:")
        parts.extend(f"- {item}" for item in matched_items)
    if missing_items:
        parts.append("")
        parts.append("Missing items:")
        parts.extend(f"- {item}" for item in missing_items)
    if suspicious_signals:
        parts.append("")
        parts.append("Suspicious signals:")
        parts.extend(f"- {item}" for item in suspicious_signals)
    return "\n".join(parts)
