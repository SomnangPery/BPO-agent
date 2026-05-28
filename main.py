# ============================================================
# MUST BE FIRST — before any other import, including ic_agent
# Patches imghdr for Python 3.13 compatibility with PTB v13
# ============================================================
import sys
from types import ModuleType
 
if sys.version_info >= (3, 13) and "imghdr" not in sys.modules:
    _imghdr = ModuleType("imghdr")
    _imghdr.what = lambda file, h=None: None
    sys.modules["imghdr"] = _imghdr
 
# ============================================================
# Now safe to import telegram / ic_agent
# ============================================================
import logging
import os
import threading
 
from ic_agent.database import init_db
from ic_agent.server import create_app
from ic_agent.bot import run_telegram_bot
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
 
logger = logging.getLogger(__name__)
 
 
def start_bot():
    """Run the Telegram bot in a separate thread."""
    try:
        run_telegram_bot()
    except Exception as e:
        logger.error(f"Error in Telegram bot thread: {e}")
 
 
# ------------------------------------------------------------------
# Global init — runs once when gunicorn loads this module.
# Guard with _BOT_STARTED so multi-worker gunicorn doesn't launch
# multiple polling threads (only 1 worker should poll Telegram).
# ------------------------------------------------------------------
init_db()
 
_BOT_STARTED = False
if os.getenv("TELEGRAM_BOT_TOKEN") and not _BOT_STARTED:
    _BOT_STARTED = True
    logger.info("Starting Telegram bot thread...")
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    import time; time.sleep(2)
    logger.info("Bot thread alive: %s", bot_thread.is_alive())
 
app = create_app()
 
 
def main() -> None:
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV", "development").lower() != "production"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
 
    print(f"Starting IC Agent web server at http://{host}:{port}")
 
    if os.getenv("FLASK_ENV") == "production":
        print("PRODUCTION MODE: Please use 'gunicorn' to serve the application.")
        print("Example: gunicorn --workers 1 --bind 0.0.0.0:$PORT main:app")
 
    app.run(debug=debug, host=host, port=port)
 
 
if __name__ == "__main__":
    main()
 