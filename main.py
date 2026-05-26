import logging
import os
from ic_agent.database import init_db
from ic_agent.server import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

def main() -> None:
    print("Initializing Project-Only IC Agent...")
    init_db()
    app = create_app()
    
    # Configuration from environment variables
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV", "production").lower() != "production"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    
    print(f"Starting IC Agent web server at http://{host}:{port}")
    app.run(debug=debug, host=host, port=port)

if __name__ == "__main__":
    main()
