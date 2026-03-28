import os
from pathlib import Path

from dotenv import load_dotenv


# Prefer values from this project's .env over inherited shell/user env vars.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DOTENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "ic-agent-dev-key-change-in-production")
IC_STAFF_PASSWORD = os.getenv("IC_STAFF_PASSWORD", "ic-staff-password")
# Optional: explicit subfolder IDs for OPPM, SRS and reports. If set, these will be
# preferred over auto-discovery of subfolders under GOOGLE_DRIVE_FOLDER_ID.
GOOGLE_OPPM_FOLDER_ID = os.getenv("GOOGLE_OPPM_FOLDER_ID", "")
GOOGLE_SRS_FOLDER_ID = os.getenv("GOOGLE_SRS_FOLDER_ID", "")
GOOGLE_REPORTS_FOLDER_ID = os.getenv("GOOGLE_REPORTS_FOLDER_ID", "")
