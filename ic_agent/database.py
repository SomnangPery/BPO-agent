import sqlite3
import json
import logging
from datetime import datetime
from typing import Any

DB_PATH = "ic_agent.db"

logger = logging.getLogger(__name__)

def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the project-only database schema."""
    with _get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            drive_folder_id TEXT UNIQUE,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            submitted_at TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'pending',
            file_names TEXT,
            ai_analysis TEXT,
            ic_decision TEXT,
            decided_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        """)
        conn.commit()

def get_or_create_project(project_name: str, drive_folder_id: str) -> dict[str, Any]:
    """Ensure project exists in DB using Drive folder info."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE drive_folder_id = ?",
            (drive_folder_id,),
        ).fetchone()
        
        if row:
            return dict(row)
            
        row = conn.execute(
            "SELECT * FROM projects WHERE LOWER(project_name) = LOWER(?)",
            (project_name,),
        ).fetchone()
        
        if row:
            conn.execute("UPDATE projects SET drive_folder_id = ? WHERE id = ?", (drive_folder_id, row["id"]))
            return dict(row)

        cursor = conn.execute(
            "INSERT INTO projects (project_name, drive_folder_id) VALUES (?, ?)",
            (project_name, drive_folder_id),
        )
        pid = cursor.lastrowid
        conn.commit()
        return {"id": pid, "project_name": project_name, "drive_folder_id": drive_folder_id}

def get_project_by_name(name: str) -> dict[str, Any] | None:
    """Fuzzy match on project_name."""
    with _get_connection() as conn:
        wildcard = f"%{name}%"
        row = conn.execute(
            "SELECT * FROM projects WHERE project_name LIKE ? ORDER BY LENGTH(project_name) ASC LIMIT 1",
            (wildcard,),
        ).fetchone()
        return dict(row) if row else None

def get_all_projects() -> list[dict[str, Any]]:
    """Return all projects in DB."""
    with _get_connection() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY project_name ASC").fetchall()
        return [dict(row) for row in rows]

def save_submission(project_id: int, file_names: list[str]) -> int:
    """Create a new submission record."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO submissions (project_id, file_names) VALUES (?, ?)",
            (project_id, json.dumps(file_names, ensure_ascii=False)),
        )
        sid = cursor.lastrowid
        conn.commit()
        return sid

def update_submission_analysis(submission_id: int, ai_analysis: dict[str, Any], status: str = "completed"):
    """Update submission with AI results."""
    with _get_connection() as conn:
        conn.execute(
            "UPDATE submissions SET ai_analysis = ?, status = ? WHERE id = ?",
            (json.dumps(ai_analysis, ensure_ascii=False), status, submission_id),
        )
        conn.commit()

def get_submissions_by_project(project_id: int) -> list[dict[str, Any]]:
    """List all submissions for a project."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM submissions WHERE project_id = ? ORDER BY submitted_at DESC",
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]

def get_pending_submissions() -> list[dict[str, Any]]:
    """List all pending submissions."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.*, p.project_name 
            FROM submissions s 
            JOIN projects p ON s.project_id = p.id 
            WHERE s.status = 'pending' 
            ORDER BY s.submitted_at ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

def update_ic_decision(submission_id: int, decision: str):
    """Store human IC decision."""
    with _get_connection() as conn:
        conn.execute(
            "UPDATE submissions SET ic_decision = ?, decided_at = datetime('now') WHERE id = ?",
            (decision, submission_id),
        )
        conn.commit()

# ============================================================================
# Compatibility wrappers for web.py (maps student/report to project/submission)
# ============================================================================

def get_or_create_student(student_name: str, folder_id: str) -> dict[str, Any]:
    """Compatibility wrapper: map student to project."""
    return get_or_create_project(student_name, folder_id)

def get_student_by_name(student_name: str) -> dict[str, Any] | None:
    """Compatibility wrapper: map student lookup to project lookup."""
    return get_project_by_name(student_name)

def get_student_by_identifier(identifier: str) -> dict[str, Any] | None:
    """Compatibility wrapper: get project by identifier (uses drive_folder_id)."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE drive_folder_id = ?",
            (identifier,),
        ).fetchone()
        return dict(row) if row else None

def update_student_identifier(student_id: int, identifier: str) -> None:
    """Compatibility wrapper: update student identifier."""
    with _get_connection() as conn:
        conn.execute(
            "UPDATE projects SET drive_folder_id = ? WHERE id = ?",
            (identifier, student_id),
        )
        conn.commit()

def get_report_by_drive_file_id(file_id: str) -> dict[str, Any] | None:
    """Compatibility wrapper: get submission by drive_file_id."""
    with _get_connection() as conn:
        # file_id may be stored in file_names JSON, search for it
        rows = conn.execute(
            "SELECT * FROM submissions WHERE file_names LIKE ? ORDER BY submitted_at DESC LIMIT 1",
            (f"%{file_id}%",),
        ).fetchone()
        return dict(rows) if rows else None

def search_students_by_name(query: str) -> list[dict[str, Any]]:
    """Compatibility wrapper: search for projects by name."""
    with _get_connection() as conn:
        if not query or query.strip() == "":
            rows = conn.execute("SELECT * FROM projects ORDER BY project_name ASC").fetchall()
        else:
            wildcard = f"%{query}%"
            rows = conn.execute(
                "SELECT * FROM projects WHERE project_name LIKE ? ORDER BY project_name ASC",
                (wildcard,),
            ).fetchall()
        return [dict(row) for row in rows]

def get_latest_report_for_student(student_id: int) -> dict[str, Any] | None:
    """Compatibility wrapper: get latest submission for a project."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM submissions WHERE project_id = ? ORDER BY submitted_at DESC LIMIT 1",
            (student_id,),
        ).fetchone()
        return dict(row) if row else None

def save_report(student_id: int, drive_file_id: str | None, file_names: list[str], status: str = "pending") -> int:
    """Compatibility wrapper: save a submission report."""
    return save_submission(student_id, file_names)

def update_report_analysis(report_id: int, analysis: str | dict[str, Any]) -> None:
    """Compatibility wrapper: update submission analysis."""
    if isinstance(analysis, str):
        analysis = json.loads(analysis) if analysis.startswith("{") else {"summary": analysis}
    update_submission_analysis(report_id, analysis if isinstance(analysis, dict) else {"summary": str(analysis)})
