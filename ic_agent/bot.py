# Patch imghdr before telegram imports — safety net if this module
# is ever imported before main.py (e.g. during testing or direct run)
import sys
from types import ModuleType

if sys.version_info >= (3, 13) and "imghdr" not in sys.modules:
    _imghdr = ModuleType("imghdr")
    _imghdr.what = lambda file, h=None: None
    sys.modules["imghdr"] = _imghdr

import logging
import os
from typing import Optional

from telegram import Update
from telegram.error import Conflict, TelegramError
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from ic_agent.analyzer import analyze_project
from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID
from ic_agent.database import (
    get_or_create_project,
    save_submission,
    update_submission_analysis,
)
from ic_agent.drive import get_all_projects as drive_get_all_projects, classify_project_files
from ic_agent.reports import format_report_message
from ic_agent.fuzzy import find_best_project_match

logger = logging.getLogger(__name__)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Hello! I am your IC Agent bot.\n\n"
        "Send me a project name (e.g. Tiger) and I'll analyze "
        "its OPPM, SRS, and reports from Google Drive.\n\n"
        "Case doesn't matter — 'tiger', 'TIGER', 'Tiger' all work."
    )


def handle_query(update: Update, context: CallbackContext):
    query = update.message.text.strip()
    if not query:
        update.message.reply_text("Please provide a project name.")
        return

    # Strip "analyze " prefix if present (case-insensitive)
    name_to_find = query
    if name_to_find.lower().startswith("analyze "):
        name_to_find = name_to_find[8:].strip()

    logger.info("Received query: '%s' -> searching for '%s'", query, name_to_find)
    update.message.reply_text(f"🔍 Searching for project '{name_to_find}'...")

    # ── Step 1: Find project in Drive ────────────────────────────────────────
    try:
        drive_projects = drive_get_all_projects(GOOGLE_DRIVE_FOLDER_ID)
        logger.info("Drive returned %d projects", len(drive_projects) if drive_projects else 0)
    except Exception as exc:
        logger.exception("Drive connection failed: %s", exc)
        update.message.reply_text(
            f"❌ Could not connect to Google Drive.\nError: {exc}\n\n"
            "Check your GOOGLE_CREDENTIALS_PATH or GOOGLE_CREDENTIALS_JSON in .env"
        )
        return

    if not drive_projects:
        update.message.reply_text(
            "⚠️ No projects found in Google Drive.\n"
            f"Check that GOOGLE_DRIVE_FOLDER_ID is correct: {GOOGLE_DRIVE_FOLDER_ID or 'NOT SET'}"
        )
        return

    # ── Step 2: Fuzzy match ───────────────────────────────────────────────────
    try:
        target, confidence = find_best_project_match(name_to_find, drive_projects, threshold=70)
    except Exception as exc:
        logger.exception("Fuzzy match failed: %s", exc)
        update.message.reply_text(f"❌ Matching failed: {exc}")
        return

    if not target:
        available = "\n• ".join(p["project_name"] for p in drive_projects[:10])
        update.message.reply_text(
            f"❌ No project found matching '{name_to_find}'.\n\n"
            f"Available projects:\n• {available}"
        )
        return

    if confidence < 75:
        logger.warning("Low confidence match: '%s' → '%s' (%d%%)", name_to_find, target["project_name"], confidence)

    project_name = target["project_name"]
    folder_id = target["folder_id"]
    logger.info("Matched project: '%s' (confidence: %d%%)", project_name, confidence)

    update.message.reply_text(
        f"📁 Found: '{project_name}' (match: {confidence}%)\n"
        "Reading files from Drive..."
    )

    # ── Step 3: Classify files ────────────────────────────────────────────────
    try:
        classified = classify_project_files(folder_id)
        oppm_found = bool(classified.get("oppm"))
        srs_found  = bool(classified.get("srs"))
        reports    = classified.get("reports", [])
        logger.info(
            "Files classified — OPPM: %s, SRS: %s, Reports: %d",
            oppm_found, srs_found, len(reports)
        )
    except Exception as exc:
        logger.exception("File classification failed: %s", exc)
        update.message.reply_text(f"❌ Could not read project files: {exc}")
        return

    update.message.reply_text(
        f"📄 Files found:\n"
        f"  • OPPM: {'✅' if oppm_found else '❌ Not found'}\n"
        f"  • SRS:  {'✅' if srs_found else '❌ Not found'}\n"
        f"  • Reports: {len(reports)} file(s)\n\n"
        "🤖 Running analysis (this takes ~30–60 seconds)..."
    )

    # ── Step 4: Save submission ───────────────────────────────────────────────
    try:
        project = get_or_create_project(project_name, folder_id)
        sub_id  = save_submission(project["id"], [r["file_name"] for r in reports])
    except Exception as exc:
        logger.exception("Database save failed: %s", exc)
        update.message.reply_text(f"❌ Database error: {exc}")
        return

    # ── Step 5: Run analysis ──────────────────────────────────────────────────
    try:
        analysis = analyze_project(project_name, classified)
        update_submission_analysis(sub_id, analysis)
        logger.info("Analysis complete for '%s'", project_name)
    except Exception as exc:
        logger.exception("Analysis failed for '%s': %s", project_name, exc)
        update.message.reply_text(
            f"❌ Analysis failed for '{project_name}'.\n"
            f"Error: {type(exc).__name__}: {exc}\n\n"
            "Check terminal logs for full traceback."
        )
        return

    # ── Step 6: Send report ───────────────────────────────────────────────────
    try:
        reply = format_report_message(analysis)
    except Exception as exc:
        logger.exception("Report formatting failed: %s", exc)
        update.message.reply_text(f"❌ Could not format report: {exc}")
        return

    for i in range(0, len(reply), 4096):
        update.message.reply_text(reply[i: i + 4096])


def error_handler(update: Update, context: CallbackContext):
    if context.error:
        logger.error("Telegram error: %s", context.error, exc_info=context.error)
        if isinstance(context.error, Conflict):
            logger.error("Conflict — stop all other bot instances and use --workers 1")


def create_telegram_updater() -> Optional[Updater]:
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Bot disabled.")
        return None

    try:
        updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_query))
        dp.add_error_handler(error_handler)
        return updater
    except TelegramError as exc:
        logger.exception("Could not create updater: %s", exc)
        return None


def run_telegram_bot() -> None:
    updater = create_telegram_updater()
    if not updater:
        return

    logger.info("Starting Telegram bot polling...")
    try:
        # start_polling() launches background threads and returns immediately.
        # Do NOT call updater.stop() here — that would kill polling instantly.
        # Do NOT call updater.idle() — it uses OS signals, only works on main thread.
        # The polling threads stay alive as long as the Flask process runs.
        updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot polling is active.")
    except Conflict as exc:
        logger.error("Polling conflict: %s — ensure --workers 1 and no other bot instances", exc)
    except TelegramError as exc:
        logger.exception("Polling failed to start: %s", exc)


if __name__ == "__main__":
    from ic_agent.database import init_db
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    init_db()
    run_telegram_bot()