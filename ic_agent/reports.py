from typing import Any


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def format_report_message(student_name: str, analysis_dict: dict[str, Any]) -> str:
    score = analysis_dict.get("score_percent", 0)
    matched_skills = analysis_dict.get("matched_skills", [])
    missing_skills = analysis_dict.get("missing_skills", [])
    summary = analysis_dict.get("summary", "No summary provided.")
    recommendation = str(analysis_dict.get("recommendation", "review")).upper()

    return (
        f"📋 *IC Agent Analysis Report*\n"
        f"👤 *Student:* {student_name}\n"
        f"📊 *Score:* {score}%\n"
        f"🧭 *Recommendation:* {recommendation}\n\n"
        f"✅ *Matched Skills*\n{_bullet_list(matched_skills)}\n\n"
        f"⚠️ *Missing Skills*\n{_bullet_list(missing_skills)}\n\n"
        f"📝 *Summary*\n{summary}"
    )


def format_report_dict(analysis_dict: dict[str, Any]) -> dict[str, Any]:
    """Format analysis dict for web display (JSON-compatible)."""
    return {
        "score_percent": analysis_dict.get("score_percent", 0),
        "matched_skills": analysis_dict.get("matched_skills", []),
        "missing_skills": analysis_dict.get("missing_skills", []),
        "summary": analysis_dict.get("summary", ""),
        "recommendation": analysis_dict.get("recommendation", "review"),
    }
