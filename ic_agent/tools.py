import json
import logging
from typing import Any
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID
from ic_agent.database import (
    get_project_by_name,
    get_or_create_project,
    save_submission,
    update_submission_analysis,
    get_pending_submissions,
    update_ic_decision,
)
from ic_agent.drive import get_all_projects, classify_project_files
from ic_agent.analyzer import analyze_project
from ic_agent.reports import format_report_message
from ic_agent.fuzzy import find_best_project_match

logger = logging.getLogger(__name__)

class ProjectQueryInput(BaseModel):
    project_query: str = Field(..., description="Project name or keyword")

class DecisionInput(BaseModel):
    submission_id: int = Field(..., description="Submission ID from database")
    decision: str = Field(..., description="Decision: approved or rejected")

def analyze_project_tool(project_query: str) -> str:
    """Find a project folder, classify files, run analysis, and return report."""
    # 1. Find folder using fuzzy matching
    drive_projects = get_all_projects(GOOGLE_DRIVE_FOLDER_ID)
    target, confidence = find_best_project_match(project_query, drive_projects, threshold=70)
    
    if not target:
        available = ", ".join([p["project_name"] for p in drive_projects[:10]])
        return f"No project folder found matching '{project_query}'.\n\nAvailable projects:\n{available}"
    
    if confidence < 75:
        logger.warning(f"Low confidence match for '{project_query}': {target['project_name']} ({confidence}%)")
    
    project_name = target["project_name"]
    folder_id = target["folder_id"]

    # 2. DB project
    project = get_or_create_project(project_name, folder_id)

    # 3. Classify files
    classified = classify_project_files(folder_id)
    
    # 4. Save submission
    reports = classified.get("reports", [])
    sub_id = save_submission(project["id"], [r["file_name"] for r in reports])

    # 5. Analyze
    try:
        analysis = analyze_project(project_name, classified)
        update_submission_analysis(sub_id, analysis)
        return format_report_message(analysis)
    except Exception as exc:
        logger.exception("Tool analysis failed: %s", exc)
        return f"Analysis failed for {project_name}: {exc}"

def list_pending_submissions_tool() -> str:
    """List all submissions waiting for IC decision."""
    subs = get_pending_submissions()
    if not subs:
        return "No pending submissions."
    lines = ["Pending Submissions:"]
    for s in subs:
        lines.append(f"- ID: {s['id']} | Project: {s['project_name']} | Files: {s['file_names']}")
    return "\n".join(lines)

def decide_submission_tool(submission_id: int, decision: str) -> str:
    """Approve or reject a submission."""
    update_ic_decision(submission_id, decision)
    return f"Submission {submission_id} has been {decision}."

def build_tools() -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            func=analyze_project_tool,
            name="analyze_project",
            description="Run full analysis on a project folder from Drive.",
            args_schema=ProjectQueryInput,
        ),
        StructuredTool.from_function(
            func=list_pending_submissions_tool,
            name="list_pending_submissions",
            description="List all submissions that need an IC decision.",
        ),
        StructuredTool.from_function(
            func=decide_submission_tool,
            name="decide_submission",
            description="Approve or reject a project submission.",
            args_schema=DecisionInput,
        ),
    ]
