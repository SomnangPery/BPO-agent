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

def start_bot():
    """Run the Telegram bot in a separate thread."""
    try:
        run_telegram_bot()
    except Exception as e:
        logging.error(f"Error in Telegram bot thread: {e}")

# Global initialization for production WSGI (like Gunicorn)
init_db()
if os.getenv("TELEGRAM_BOT_TOKEN"):
    logging.info("Starting Telegram bot thread...")
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

app = create_app()

def main() -> None:
    # Configuration from environment variables
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV", "development").lower() != "production"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    
    print(f"Starting IC Agent web server at http://{host}:{port}")
    
    if os.getenv("FLASK_ENV") == "production":
        print("PRODUCTION MODE: Please use 'gunicorn' to serve the application.")
        print("Example: gunicorn --workers 2 --bind 0.0.0.0:$PORT main:app")
    
    app.run(debug=debug, host=host, port=port)

if __name__ == "__main__":
    main()
