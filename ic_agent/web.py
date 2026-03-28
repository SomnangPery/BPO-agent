import json
import logging
import re
import hashlib
from typing import Any

from flask import Flask, jsonify, render_template, request

from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID, WEB_SECRET_KEY
from ic_agent.config import GOOGLE_OPPM_FOLDER_ID, GOOGLE_SRS_FOLDER_ID, GOOGLE_REPORTS_FOLDER_ID
from ic_agent.database import (
    add_student,
    get_student_by_identifier,
    update_student_identifier,
    get_report_by_drive_file_id,
    search_students_by_name,
    get_latest_report_for_student,
    save_report,
    update_report_analysis,
)
from ic_agent.drive import list_student_files, list_files_recursive, read_file_content
from ic_agent.analyzer import analyze_student_work, analyze_weekly_report


logger = logging.getLogger(__name__)


STOP_WORDS = {
    "oppm",
    "srs",
    "submission",
    "student",
    "report",
    "final",
    "draft",
    "version",
    "v1",
    "v2",
    "v3",
    "pdf",
    "doc",
    "docx",
}

FILE_KIND_TOKENS = {"oppm", "srs", "report"}


def _strip_multi_extension(filename: str) -> str:
    return re.sub(r"(\.[A-Za-z0-9]{1,6})+$", "", filename)


def _extract_student_name_from_filename(filename: str) -> str | None:
    base = _strip_multi_extension(filename).lower()
    # Split on separators so variants like OPPM-Pery_Somnang, oppm pery somnang work.
    tokens = re.findall(r"[a-z0-9]+", base)
    cleaned = [token for token in tokens if token not in STOP_WORDS and not token.isdigit()]
    if not cleaned:
        return None
    return " ".join(cleaned).title().strip() or None


def _extract_submission_meta(filename: str, parent_folder_name: str = "") -> tuple[str, str] | None:
    """Return (kind, student_name) from names like `srs_nou_chylong.pdf`.

    The file kind can be discovered from either filename or parent folder name.
    """
    base = _strip_multi_extension(filename).lower()
    parent = (parent_folder_name or "").lower()
    tokens = re.findall(r"[a-z0-9]+", base)

    detected_kind = ""
    for token in tokens:
        if token in FILE_KIND_TOKENS:
            detected_kind = token
            break
    if not detected_kind:
        for token in FILE_KIND_TOKENS:
            if token in parent:
                detected_kind = token
                break
    if not detected_kind:
        return None

    student_name = _extract_student_name_from_filename(filename)
    if not student_name:
        return None
    return detected_kind, student_name


def _identifier_from_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", name.lower()) or "student"
    # Stable 8-digit numeric id derived from student name.
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    base = int(digest[:12], 16) % 90_000_000 + 10_000_000
    return str(base)


def _generate_unique_numeric_identifier(name: str, current_student_id: int | None = None) -> str:
    base = int(_identifier_from_name(name))
    for offset in range(1000):
        candidate = str(((base - 10_000_000 + offset) % 90_000_000) + 10_000_000)
        existing = get_student_by_identifier(candidate)
        if not existing:
            return candidate
        if current_student_id is not None and int(existing.get("id", -1)) == int(current_student_id):
            return candidate
    # Extremely unlikely fallback.
    return str(base)


def _collect_submission_files() -> list[dict[str, Any]]:
    """Collect candidate submission files from configured folders.

    Priority:
    1) Explicit OPPM/SRS/REPORTS folders
    2) Recursive listing under main folder
    """
    files: list[dict[str, Any]] = []

    if GOOGLE_OPPM_FOLDER_ID or GOOGLE_SRS_FOLDER_ID or GOOGLE_REPORTS_FOLDER_ID:
        if GOOGLE_OPPM_FOLDER_ID:
            items = list_student_files(GOOGLE_OPPM_FOLDER_ID)
            for item in items:
                item["parent_folder_name"] = "oppm"
            files.extend(items)
        if GOOGLE_SRS_FOLDER_ID:
            items = list_student_files(GOOGLE_SRS_FOLDER_ID)
            for item in items:
                item["parent_folder_name"] = "srs"
            files.extend(items)
        if GOOGLE_REPORTS_FOLDER_ID:
            items = list_student_files(GOOGLE_REPORTS_FOLDER_ID)
            for item in items:
                item["parent_folder_name"] = "report"
            files.extend(items)
        return files

    if not GOOGLE_DRIVE_FOLDER_ID:
        return []

    try:
        return list_files_recursive(GOOGLE_DRIVE_FOLDER_ID)
    except Exception:
        return list_student_files(GOOGLE_DRIVE_FOLDER_ID)


def _sync_report_submissions(files: list[dict[str, Any]], student_by_name: dict[str, int]) -> int:
    """Save newly discovered report_* files as pending submissions."""
    created_reports = 0
    for file_item in files:
        filename = str(file_item.get("name", "") or "")
        parent_name = str(file_item.get("parent_folder_name", "") or "")
        meta = _extract_submission_meta(filename, parent_name)
        if not meta:
            continue
        kind, parsed_name = meta
        if kind != "report":
            continue

        student_id = student_by_name.get(parsed_name.lower())
        if not student_id:
            continue

        drive_file_id = str(file_item.get("id", "") or "").strip()
        if not drive_file_id:
            continue

        if get_report_by_drive_file_id(drive_file_id):
            continue

        submitted_at = str(file_item.get("modifiedTime", "") or "").strip() or None
        save_report(
            student_id=student_id,
            file_name=filename,
            ai_analysis="",
            drive_file_id=drive_file_id,
            submitted_at=submitted_at,
        )
        created_reports += 1

    return created_reports


def _sync_students_from_drive() -> dict[str, int]:
    if not (GOOGLE_DRIVE_FOLDER_ID or GOOGLE_OPPM_FOLDER_ID or GOOGLE_SRS_FOLDER_ID or GOOGLE_REPORTS_FOLDER_ID):
        return {"processed": 0, "created": 0, "updated": 0}

    files = _collect_submission_files()
    seen_names: set[str] = set()
    created = 0
    updated = 0

    student_by_name: dict[str, int] = {}

    for file_item in files:
        name = str(file_item.get("name", "")).strip()
        parent_name = str(file_item.get("parent_folder_name", "") or "")
        meta = _extract_submission_meta(name, parent_name)
        if not meta:
            continue
        _, parsed_name = meta
        if parsed_name in seen_names:
            continue
        seen_names.add(parsed_name)

        existing_by_name = [
            row
            for row in search_students_by_name(parsed_name)
            if str(row.get("name", "")).strip().lower() == parsed_name.lower()
        ]
        if existing_by_name:
            row = existing_by_name[0]
            student_by_name[parsed_name.lower()] = int(row.get("id"))
            current_identifier = str(row.get("student_identifier", "") or "")
            if not current_identifier.isdigit():
                new_identifier = _generate_unique_numeric_identifier(parsed_name, int(row.get("id")))
                if new_identifier != current_identifier:
                    update_student_identifier(int(row.get("id")), new_identifier)
            updated += 1
            continue

        student_identifier = _generate_unique_numeric_identifier(parsed_name)
        existed = get_student_by_identifier(student_identifier) is not None
        student_id = add_student(parsed_name, student_identifier, None)
        student_by_name[parsed_name.lower()] = int(student_id)
        if existed:
            updated += 1
        else:
            created += 1

    # Backfill map for names that were skipped by seen_names logic.
    for row in search_students_by_name(""):
        row_name = str(row.get("name", "") or "").strip().lower()
        if row_name and row_name not in student_by_name:
            student_by_name[row_name] = int(row.get("id"))

    new_reports = _sync_report_submissions(files, student_by_name)

    return {"processed": len(files), "created": created, "updated": updated, "new_reports": new_reports}


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = WEB_SECRET_KEY

    @app.route("/")
    def index():
        return render_template("staff_chatbot.html")

    @app.route("/api/search_student", methods=["GET"])
    def search_student():
        query = request.args.get("q", "").strip()
        if not query or len(query) < 2:
            return jsonify({"results": [], "message": "Please enter at least 2 characters."})

        try:
            try:
                sync_result = _sync_students_from_drive()
                logger.info("Drive sync before search: %s", sync_result)
            except Exception as sync_exc:
                logger.warning("Drive sync skipped due to error: %s", sync_exc)

            results = search_students_by_name(query)
            # Parse AI analysis if exists
            for result in results:
                if result.get("latest_analysis"):
                    try:
                        result["latest_analysis"] = json.loads(result["latest_analysis"])
                    except Exception:
                        result["latest_analysis"] = {}
            return jsonify({"results": results, "success": True})
        except Exception as exc:
            logger.exception("Search failed: %s", exc)
            return jsonify({"results": [], "success": False, "message": "Search failed."})

    @app.route("/api/analyze_student", methods=["POST"])
    def analyze_student():
        data = request.get_json(silent=True) or {}
        student_id = data.get("student_id") or data.get("id")
        if not student_id:
            return jsonify({"success": False, "message": "student_id is required"}), 400

        try:
            # ensure student exists
            conn_student = None
            # search by id in DB
            # use search_students_by_name to find matching id
            students = []
            try:
                students = [s for s in search_students_by_name("") if s.get("id") == int(student_id)]
            except Exception:
                students = []

            if not students:
                return jsonify({"success": False, "message": "student not found"}), 404

            student = students[0]
            student_name = student.get("name")

            # find oppm, srs and latest weekly report files in Drive for this student
            files = _collect_submission_files()

            def file_matches(f: dict[str, Any], required_kind: str) -> bool:
                meta = _extract_submission_meta(
                    str(f.get("name", "") or ""),
                    str(f.get("parent_folder_name", "") or ""),
                )
                if not meta:
                    return False
                kind, parsed_name = meta
                return kind == required_kind and parsed_name.lower() == str(student_name).lower()

            oppm = next((f for f in files if file_matches(f, "oppm")), None)
            srs = next((f for f in files if file_matches(f, "srs")), None)
            report_candidates = [f for f in files if file_matches(f, "report")]
            report_candidates.sort(key=lambda f: str(f.get("modifiedTime", "") or ""), reverse=True)
            report = report_candidates[0] if report_candidates else None

            if not oppm or not srs or not report:
                return jsonify({"success": False, "message": "Could not locate OPPM, SRS and latest Report files for this student in Drive."}), 404

            oppm_content = read_file_content(oppm["id"])
            srs_content = read_file_content(srs["id"])
            report_content = read_file_content(report["id"])

            # run analysis
            try:
                analysis = analyze_weekly_report(student_name, oppm_content, srs_content, report_content)
            except Exception as e:
                logger.exception("Analysis failed: %s", e)
                return jsonify({"success": False, "message": f"Analysis failed: {e}"}), 502

            # attach analysis to latest report or create new report
            latest = get_latest_report_for_student(int(student_id))
            current_drive_report = get_report_by_drive_file_id(str(report.get("id", "") or ""))
            if current_drive_report:
                report_id = int(current_drive_report["id"])
            elif latest:
                report_id = int(latest["id"])
            else:
                report_id = save_report(
                    int(student_id),
                    str(report.get("name", "weekly-report")),
                    json.dumps(analysis, ensure_ascii=False),
                    drive_file_id=str(report.get("id", "") or None),
                    submitted_at=str(report.get("modifiedTime", "") or None),
                )

            update_ok = update_report_analysis(report_id, json.dumps(analysis, ensure_ascii=False))

            return jsonify({"success": True, "analysis": analysis, "updated_report": update_ok})
        except Exception as exc:
            logger.exception("Analyze failed: %s", exc)
            return jsonify({"success": False, "message": "Analyze failed."}), 500

    return app
