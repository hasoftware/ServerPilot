"""Application configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Base path
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs")))

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "1206"))
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{DATA_DIR / 'control_server.db'}",
)

# Log settings
MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "10"))
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

# Terminal (ttyd) - optional, e.g. http://localhost:7681
TTYD_URL = os.getenv("TTYD_URL", "")
