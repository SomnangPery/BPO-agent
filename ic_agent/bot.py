import logging
import os
from typing import Optional

from telegram import Bot, Update
from telegram.error import Conflict, TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, CallbackContext

from ic_agent.analyzer import analyze_project
from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID
from ic_agent.database import (
    get_or_create_project,
    save_submission,
    update_submission_analysis,
)
from ic_agent.drive import get_all_projects as drive_get_all_projects, classify_project_files
from ic_agent.reports import format_report_message

logger = logging.getLogger(__name__)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! I am your IC Agent bot. How can I assist you today?")


def handle_query(update: Update, context: CallbackContext):
    query = update.message.text.strip()
    if not query:
        update.message.reply_text("Please provide a query.")
        return

    name_to_find = query.replace("analyze ", "").strip().lower()
    drive_projects = drive_get_all_projects(GOOGLE_DRIVE_FOLDER_ID)
    matches = [p for p in drive_projects if name_to_find in p["project_name"].lower()]

    if not matches:
        update.message.reply_text(f"No project folder found matching '{query}'.")
        return

    if len(matches) > 1:
        names = ", ".join([p["project_name"] for p in matches[:5]])
        update.message.reply_text(f"Multiple projects matched: {names}. Please be more specific.")
        return

    target = matches[0]
    project_name = target["project_name"]
    folder_id = target["folder_id"]

    project = get_or_create_project(project_name, folder_id)
    classified = classify_project_files(folder_id)
    reports = classified.get("reports", [])
    sub_id = save_submission(project["id"], [r["file_name"] for r in reports])

    try:
        analysis = analyze_project(project_name, classified)
        update_submission_analysis(sub_id, analysis)
        reply = format_report_message(analysis)

        if len(reply) > 4096:
            for i in range(0, len(reply), 4096):
                update.message.reply_text(reply[i : i + 4096])
        else:
            update.message.reply_text(reply)
    except Exception as exc:
        logger.exception("Analysis failed: %s", exc)
        update.message.reply_text(f"Analysis failed for {project_name}: {exc}")


def error_handler(update: Update, context: CallbackContext):
    if context.error:
        logger.error("Telegram update failed: %s", context.error, exc_info=context.error)
        if isinstance(context.error, Conflict):
            logger.error(
                "Telegram is reporting a getUpdates conflict. Stop any other bot process using this token and restart.")


def create_telegram_updater() -> Optional[Updater]:
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured. Telegram bot disabled.")
        return None

    try:
        updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_query))
        dispatcher.add_error_handler(error_handler)
        return updater
    except TelegramError as exc:
        logger.exception("Unable to create Telegram updater: %s", exc)
        return None


def run_telegram_bot() -> None:
    updater = create_telegram_updater()
    if not updater:
        return

    logger.info("Starting Telegram bot polling...")
    try:
        updater.start_polling()
        updater.idle()
    except Conflict as exc:
        logger.error(
            "Cannot start polling due to Telegram conflict: %s. Stop any other bot instances and restart.",
            exc,
        )
    except TelegramError as exc:
        logger.exception("Telegram polling failed: %s", exc)
    finally:
        try:
            updater.stop()
        except Exception:
            pass
