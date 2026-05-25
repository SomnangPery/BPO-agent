from typing import Any

def format_report_message(analysis: dict[str, Any]) -> str:
    """Format the project analysis into a clean report."""
    progress = analysis.get("progress") or {}
    verdict = analysis.get("verdict") or {}
    validations = analysis.get("file_validations") or []
    
    pct = progress.get("completion_percentage", 0)
    bar_len = 10
    filled = int(round(pct / 100 * bar_len))
    bar = "█" * filled + "░" * (bar_len - filled)

    risk_flags = "\n".join([f"  🚩 {f}" for f in verdict.get("risk_flags", [])]) or "None ✅"
    strengths = verdict.get("strengths", [])
    weaknesses = verdict.get("weaknesses", [])
    
    sw_lines = []
    for i in range(max(len(strengths), len(weaknesses))):
        s = strengths[i] if i < len(strengths) else ""
        w = weaknesses[i] if i < len(weaknesses) else ""
        sw_lines.append(f"✦ {s:<25} |     ✦ {w}")
    sw_section = "\n".join(sw_lines)

    # Simplified grouping for coverage
    coverage_lines = []
    coverage = progress.get("requirement_coverage", [])
    for item in coverage:
        tier = item.get("coverage_tier", "not_started")
        req = item.get("requirement", "Unknown")
        file = item.get("covered_by") or "null"
        if tier == "completed": icon = "✅"
        elif tier == "in_progress": icon = "🔄"
        elif tier == "planned": icon = "📋"
        else: icon = "○"
        
        status_suffix = " (in progress)" if tier == "in_progress" else " mentioned in planning" if tier == "planned" else " not started yet" if tier == "not_started" else ""
        coverage_lines.append(f"  {icon} {req} — {file}{status_suffix}")

    file_lines = []
    for v in validations:
        v_icon = "✅" if v.get("is_valid") else "❌"
        file_lines.append(
            f"  📄 {v['file_name']}\n"
            f"     Valid    : {v_icon}  — {v.get('validity_reason', 'N/A')}\n"
            f"     Evidence : {v.get('evidence_type', 'N/A')}\n"
            f"     Covers   : {v.get('matches_oppm_item', 'none')}\n"
            f"     Quality  : {v.get('quality', 'N/A')} — {v.get('quality_note', 'N/A')}"
        )

    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 IC AGENT — PROJECT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗂️  Project   : {analysis['project_name']}
📅 Analyzed  : {analysis['timestamp']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 PROGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏗️  Stage     : {progress.get('project_stage', 'Unknown')}
📈 Progress  : {pct}%  [{bar}]
📁 Files     : {progress.get('valid_files', 0)} valid  |  {progress.get('fake_files', 0)} fake

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REQUIREMENT COVERAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(coverage_lines)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 SUBMITTED FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(file_lines)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚩 RED FLAGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{risk_flags}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💪 STRENGTHS  |  ⚠️ WEAKNESSES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{sw_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 VERDICT : {verdict.get('verdict', 'NEEDS_REVIEW')}  ({verdict.get('confidence', 0)}%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{verdict.get('verdict_reason', 'No reason provided.')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 IC RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{verdict.get('ic_recommendation', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 PROJECT FEEDBACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{verdict.get('project_feedback', 'No feedback provided.')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
