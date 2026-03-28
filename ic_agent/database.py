import sqlite3
from datetime import datetime, timezone
from typing import Any


DB_PATH = "ic_agent.db"


CORE_STUDENT_COLUMNS = {"id", "name", "drive_folder_id", "student_identifier"}


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _student_columns(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("PRAGMA table_info(students)").fetchall()
    return [str(row["name"]) for row in rows]


def _resolve_identifier_column(columns: list[str]) -> str:
    if "student_identifier" in columns:
        return "student_identifier"
    for name in columns:
        if name not in CORE_STUDENT_COLUMNS:
            return name
    return "student_identifier"


def init_db() -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                student_identifier TEXT UNIQUE,
                drive_folder_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                drive_file_id TEXT,
                file_name TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                ai_analysis TEXT,
                ic_decision TEXT,
                decided_at TEXT,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
            """
        )

        report_columns = [str(row["name"]) for row in conn.execute("PRAGMA table_info(reports)").fetchall()]
        if "drive_file_id" not in report_columns:
            conn.execute("ALTER TABLE reports ADD COLUMN drive_file_id TEXT")

        columns = _student_columns(conn)
        if "student_identifier" not in columns:
            conn.execute("ALTER TABLE students ADD COLUMN student_identifier TEXT")
            source_column = _resolve_identifier_column(columns)
            if source_column != "student_identifier":
                conn.execute(
                    f"""
                    UPDATE students
                    SET student_identifier = {source_column}
                    WHERE (student_identifier IS NULL OR student_identifier = '')
                    """
                )

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_students_student_identifier
            ON students(student_identifier)
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_drive_file_id
            ON reports(drive_file_id)
            WHERE drive_file_id IS NOT NULL AND drive_file_id != ''
            """
        )


def add_student(name: str, student_identifier: str, drive_folder_id: str | None = None) -> int:
    with _get_connection() as conn:
        columns = _student_columns(conn)
        identifier_column = _resolve_identifier_column(columns)
        conn.execute(
            f"""
            INSERT INTO students (name, {identifier_column}, drive_folder_id)
            VALUES (?, ?, ?)
            ON CONFLICT({identifier_column})
            DO UPDATE SET
                name = excluded.name,
                drive_folder_id = excluded.drive_folder_id
            """,
            (name, student_identifier, drive_folder_id),
        )
        row = conn.execute(
            f"SELECT id FROM students WHERE {identifier_column} = ?",
            (student_identifier,),
        ).fetchone()
        return int(row["id"])


def get_student_by_identifier(student_identifier: str) -> dict[str, Any] | None:
    with _get_connection() as conn:
        columns = _student_columns(conn)
        identifier_column = _resolve_identifier_column(columns)
        row = conn.execute(
            f"""
            SELECT id, name, {identifier_column} AS student_identifier, drive_folder_id
            FROM students
            WHERE {identifier_column} = ?
            """,
            (student_identifier,),
        ).fetchone()
        return dict(row) if row else None


def update_student_identifier(student_id: int, student_identifier: str) -> bool:
    with _get_connection() as conn:
        columns = _student_columns(conn)
        identifier_column = _resolve_identifier_column(columns)
        cursor = conn.execute(
            f"""
            UPDATE students
            SET {identifier_column} = ?
            WHERE id = ?
            """,
            (student_identifier, student_id),
        )
        return cursor.rowcount > 0


def save_report(
    student_id: int,
    file_name: str,
    ai_analysis: str,
    drive_file_id: str | None = None,
    submitted_at: str | None = None,
) -> int:
    submitted_at_value = submitted_at or datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reports (student_id, drive_file_id, file_name, submitted_at, status, ai_analysis)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (student_id, drive_file_id, file_name, submitted_at_value, ai_analysis),
        )
        return int(cursor.lastrowid)


def get_report_by_drive_file_id(drive_file_id: str) -> dict[str, Any] | None:
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, student_id, drive_file_id, file_name, submitted_at, status, ai_analysis, ic_decision, decided_at
            FROM reports
            WHERE drive_file_id = ?
            LIMIT 1
            """,
            (drive_file_id,),
        ).fetchone()
        return dict(row) if row else None


def get_pending_reports() -> list[dict[str, Any]]:
    with _get_connection() as conn:
        columns = _student_columns(conn)
        identifier_column = _resolve_identifier_column(columns)
        rows = conn.execute(
            f"""
            SELECT
                r.id,
                r.student_id,
                r.file_name,
                r.submitted_at,
                r.status,
                r.ai_analysis,
                s.name AS student_name,
                s.{identifier_column} AS student_identifier
            FROM reports r
            JOIN students s ON s.id = r.student_id
            WHERE r.status = 'pending'
            ORDER BY r.submitted_at ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def update_report_decision(report_id: int, decision: str) -> bool:
    decided_at = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE reports
            SET status = ?, ic_decision = ?, decided_at = ?
            WHERE id = ?
            """,
            (decision, decision, decided_at, report_id),
        )
        return cursor.rowcount > 0


def update_report_analysis(report_id: int, ai_analysis: str, status: str = "analyzed") -> bool:
    decided_at = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE reports
            SET ai_analysis = ?, status = ?, decided_at = ?
            WHERE id = ?
            """,
            (ai_analysis, status, decided_at, report_id),
        )
        return cursor.rowcount > 0


def get_report_by_id(report_id: int) -> dict[str, Any] | None:
    with _get_connection() as conn:
        columns = _student_columns(conn)
        identifier_column = _resolve_identifier_column(columns)
        row = conn.execute(
            f"""
            SELECT
                r.id,
                r.student_id,
                r.file_name,
                r.submitted_at,
                r.status,
                r.ai_analysis,
                r.ic_decision,
                r.decided_at,
                s.name AS student_name,
                s.{identifier_column} AS student_identifier
            FROM reports r
            JOIN students s ON s.id = r.student_id
            WHERE r.id = ?
            """,
            (report_id,),
        ).fetchone()
        return dict(row) if row else None


def get_latest_report_for_student(student_id: int) -> dict[str, Any] | None:
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, student_id, file_name, submitted_at, status, ai_analysis, ic_decision, decided_at
            FROM reports
            WHERE student_id = ?
            ORDER BY submitted_at DESC
            LIMIT 1
            """,
            (student_id,),
        ).fetchone()
        return dict(row) if row else None


def search_students_by_name(name_query: str) -> list[dict[str, Any]]:
    """Search for students by name and return their progress."""
    with _get_connection() as conn:
        columns = _student_columns(conn)
        identifier_column = _resolve_identifier_column(columns)
        rows = conn.execute(
            f"""
            SELECT
                s.id,
                s.name,
                s.{identifier_column} AS student_identifier,
                COUNT(r.id) AS total_submissions,
                SUM(CASE WHEN r.status = 'pending' THEN 1 ELSE 0 END) AS pending_submissions,
                SUM(CASE WHEN r.status != 'pending' THEN 1 ELSE 0 END) AS completed_submissions,
                MAX(r.submitted_at) AS last_submission,
                (
                    SELECT ai_analysis 
                    FROM reports 
                    WHERE student_id = s.id 
                    ORDER BY submitted_at DESC 
                    LIMIT 1
                ) AS latest_analysis,
                (
                    SELECT ic_decision 
                    FROM reports 
                    WHERE student_id = s.id 
                    ORDER BY submitted_at DESC 
                    LIMIT 1
                ) AS latest_decision
            FROM students s
            LEFT JOIN reports r ON s.id = r.student_id
            WHERE s.name LIKE ?
            GROUP BY s.id
            ORDER BY s.name ASC
            """,
            (f"%{name_query}%",),
        ).fetchall()
        return [dict(row) for row in rows]
