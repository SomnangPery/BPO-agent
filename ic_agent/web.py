import os
import json
import logging
import re
from typing import Any
from flask import Flask, jsonify, render_template, request
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID, WEB_SECRET_KEY
from ic_agent.database import (
    init_db,
    get_or_create_project,
    get_project_by_name,
    get_all_projects,
    save_submission,
    update_submission_analysis,
    get_submissions_by_project,
    get_pending_submissions,
    update_ic_decision
)
from ic_agent.drive import get_all_projects as drive_get_all_projects, classify_project_files
from ic_agent.analyzer import analyze_project
from ic_agent.reports import format_report_message

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.secret_key = WEB_SECRET_KEY or os.urandom(24)

    @app.route("/")
    def index():
        return render_template("staff_chatbot.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app

# Initialize the bot only if a token is configured.
bot = None
updater = None
dispatcher = None
if TELEGRAM_BOT_TOKEN:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
else:
    logger.warning("TELEGRAM_BOT_TOKEN is not set. Telegram bot is disabled.")


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! I am your IC Agent bot. How can I assist you today?")


def handle_query(update: Update, context: CallbackContext):
    query = update.message.text.strip()
    if not query:
        update.message.reply_text("Please provide a query.")
        return

    # Normalize query and folder names for case-insensitive matching
    name_to_find = query.replace("analyze ", "").strip().lower()

    # 1. Find folder
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
        reply = format_report_message(analysis)
        # Handle long messages
        def split_message(message, max_length=4096):
            return [message[i:i+max_length] for i in range(0, len(message), max_length)]

        if len(reply) > 4096:
            for part in split_message(reply):
                update.message.reply_text(part)
        else:
            update.message.reply_text(reply)
    except Exception as exc:
        logger.exception("Analysis failed: %s", exc)
        update.message.reply_text(f"Analysis failed for {project_name}: {exc}")


if updater and dispatcher:
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_query))


if __name__ == "__main__":
    if updater:
        updater.start_polling()
        updater.idle()
    else:
        logger.warning("No TELEGRAM_BOT_TOKEN configured, bot will not start.")
