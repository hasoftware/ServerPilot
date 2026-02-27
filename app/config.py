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

# VNC - WebSocket URL (websockify), ví dụ: ws://localhost:6080
# Bạn tự cài VNC server (TigerVNC, x11vnc) + websockify, đăng nhập do bạn cấu hình
VNC_WS_URL = os.getenv("VNC_WS_URL", "")
