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

def main() -> None:
    print("Initializing Project-Only IC Agent...")
    init_db()
    
    # Start Telegram bot in a background thread
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        print("Starting Telegram bot thread...")
        bot_thread = threading.Thread(target=start_bot, daemon=True)
        bot_thread.start()
    else:
        print("TELEGRAM_BOT_TOKEN not found, skipping bot startup.")

    app = create_app()
    
    # Configuration from environment variables
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV", "development").lower() != "production"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    
    print(f"Starting IC Agent web server at http://{host}:{port}")
    app.run(debug=debug, host=host, port=port)

if __name__ == "__main__":
    main()
