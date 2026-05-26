import os
import logging
from pathlib import Path

from dotenv import load_dotenv


# Prefer values from this project's .env over inherited shell/user env vars.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DOTENV_PATH = _PROJECT_ROOT / ".env"
if _DOTENV_PATH.exists():
    print(f"Loading environment from {_DOTENV_PATH}")
    load_dotenv(dotenv_path=_DOTENV_PATH, override=True)
else:
    print(f"No .env file found at {_DOTENV_PATH}")

logger = logging.getLogger(__name__)

# Check deployment environment
FLASK_ENV = os.getenv("FLASK_ENV", "development")
IS_PRODUCTION = FLASK_ENV.lower() == "production"

def _csv_env_list(name: str) -> list[str]:
	raw = os.getenv(name, "")
	return [item.strip() for item in raw.split(",") if item.strip()]


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
AGENT_MODEL = os.getenv("AGENT_MODEL", CLAUDE_MODEL)
CHAT_USE_REACT_AGENT = os.getenv("CHAT_USE_REACT_AGENT", "0").strip().lower() in {"1", "true", "yes", "on"}
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_DRIVE_FOLDER_IDS = _csv_env_list("GOOGLE_DRIVE_FOLDER_IDS")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "")
IC_STAFF_PASSWORD = os.getenv("IC_STAFF_PASSWORD", "")
KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", str(_PROJECT_ROOT / "knowledge"))
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(_PROJECT_ROOT / "chroma_store"))
# Optional: explicit subfolder IDs for OPPM, SRS and reports. If set, these will be
# preferred over auto-discovery of subfolders under GOOGLE_DRIVE_FOLDER_ID.
GOOGLE_OPPM_FOLDER_ID = os.getenv("GOOGLE_OPPM_FOLDER_ID", "")
GOOGLE_SRS_FOLDER_ID = os.getenv("GOOGLE_SRS_FOLDER_ID", "")
GOOGLE_REPORTS_FOLDER_ID = os.getenv("GOOGLE_REPORTS_FOLDER_ID", "")

# Production safety checks
if IS_PRODUCTION:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is required in production")
    if not WEB_SECRET_KEY:
        raise ValueError("WEB_SECRET_KEY must be set in production (use a secure random value)")
    if not IC_STAFF_PASSWORD:
        raise ValueError("IC_STAFF_PASSWORD must be set in production")
else:
    # Development mode - provide safe defaults
    if not WEB_SECRET_KEY:
        WEB_SECRET_KEY = "dev-key-change-in-production"
    if not IC_STAFF_PASSWORD:
        IC_STAFF_PASSWORD = "dev-password-change-in-production"
    logger.warning("Running in DEVELOPMENT mode. Set FLASK_ENV=production for production deployments.")

