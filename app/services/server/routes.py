"""Server APIs - logs, systemd services."""
import subprocess

from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_setup_complete
from app.config import LOG_DIR, VNC_WS_URL
from app.database.models import User

router = APIRouter(prefix="/api/server", tags=["server"])


@router.get("/logs")
async def get_logs(
    source: str = Query("journal", description="journal | app"),
    lines: int = Query(100, le=500),
    unit: str = Query("", description="systemd unit for journal"),
    current_user: User = Depends(require_setup_complete),
):
    """Get server logs - journalctl or app logs."""
    try:
        if source == "journal":
            cmd = ["journalctl", "-n", str(lines), "--no-pager"]
            if unit:
                cmd.extend(["-u", unit])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {"logs": result.stdout or result.stderr or ""}
        elif source == "app":
            # App logs from LOG_DIR if exists
            log_file = LOG_DIR / "app.log"
            if not log_file.exists():
                return {"logs": "(Chưa có log file)"}
            result = subprocess.run(
                ["tail", "-n", str(lines), str(log_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return {"logs": result.stdout or ""}
    except Exception as e:
        return {"logs": f"Lỗi: {str(e)}"}
    return {"logs": ""}


@router.get("/services")
async def get_services(
    current_user: User = Depends(require_setup_complete),
):
    """List systemd services - simple text parse."""
    try:
        result = subprocess.run(
            [
                "systemctl", "list-units", "--type=service",
                "--no-pager", "--no-legend",
                "-o", "table", "--plain",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = result.stdout or result.stderr or ""
        lines = out.strip().split("\n")[1:]  # skip header
        services = []
        for line in lines:
            parts = line.split(maxsplit=4)
            if len(parts) >= 5:
                services.append({
                    "unit": parts[0],
                    "load": parts[1],
                    "active": parts[2],
                    "sub": parts[3],
                    "description": parts[4],
                })
        return {"services": services}
    except Exception as e:
        return {"services": [], "error": str(e)}


@router.get("/vnc-url")
async def get_vnc_url(
    request: Request,
    current_user: User = Depends(require_setup_complete),
):
    """Lấy URL WebSocket của VNC (từ .env). Bạn tự cấu hình VNC server + websockify."""
    if VNC_WS_URL:
        return {"url": VNC_WS_URL}
    host = request.headers.get("host", "localhost").split(":")[0]
    scheme = "wss" if request.url.scheme == "https" else "ws"
    return {"url": f"{scheme}://{host}:6080", "hint": "Mặc định port 6080 - cấu hình VNC_WS_URL trong .env"}
