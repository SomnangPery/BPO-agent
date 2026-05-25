import logging
from ic_agent.database import init_db
from ic_agent.web import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

def main() -> None:
    print("Initializing Project-Only IC Agent...")
    init_db()
    app = create_app()
    print("Starting IC Agent web server at http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
