"""Server APIs - logs, systemd services."""
import json
import platform
import subprocess

from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_setup_complete
from app.config import LOG_DIR, VNC_WS_URL
from app.database.models import User

router = APIRouter(prefix="/api/server", tags=["server"])

# Full path cho Linux (tránh Errno 2 khi PATH không có)
JOURNALCTL = "/usr/bin/journalctl"
SYSTEMCTL = "/usr/bin/systemctl"
TAIL = "/usr/bin/tail"


@router.get("/logs")
async def get_logs(
    source: str = Query("journal", description="journal | app"),
    lines: int = Query(100, le=500),
    unit: str = Query("", description="systemd unit for journal"),
    current_user: User = Depends(require_setup_complete),
):
    """Get server logs - journalctl or app logs."""
    if platform.system() != "Linux":
        return {"logs": "journalctl và app logs chỉ khả dụng trên Linux."}
    try:
        if source == "journal":
            cmd = [JOURNALCTL, "-n", str(lines), "--no-pager"]
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
            log_file = LOG_DIR / "app.log"
            if not log_file.exists():
                return {"logs": "(Chưa có log file)"}
            result = subprocess.run(
                [TAIL, "-n", str(lines), str(log_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return {"logs": result.stdout or ""}
    except FileNotFoundError:
        return {"logs": "Lệnh journalctl/tail không tìm thấy. Chạy trên Ubuntu/Linux."}
    except Exception as e:
        return {"logs": f"Lỗi: {str(e)}"}
    return {"logs": ""}


@router.get("/services")
async def get_services(
    current_user: User = Depends(require_setup_complete),
):
    """List systemd services - dùng JSON hoặc parse table."""
    if platform.system() != "Linux":
        return {"services": [], "error": "systemctl chỉ khả dụng trên Linux"}
    try:
        # Thử JSON trước (systemd 230+)
        result = subprocess.run(
            [
                SYSTEMCTL, "list-units", "--type=service",
                "--no-pager", "--output=json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            units = data if isinstance(data, list) else (data.get("units") or data.get("data") or data.get("node") or [])
            if not isinstance(units, list):
                units = []
            services = []
            for u in units:
                if isinstance(u, dict):
                    unit = u.get("unit") or u.get("id") or ""
                    load = u.get("load") or u.get("load_state") or ""
                    active = u.get("active") or u.get("active_state") or ""
                    sub = u.get("sub") or u.get("sub_state") or ""
                    desc = u.get("description") or ""
                else:
                    continue
                if unit:
                    services.append({
                        "unit": str(unit),
                        "load": str(load),
                        "active": str(active),
                        "sub": str(sub),
                        "description": str(desc),
                    })
            if services:
                return {"services": services}

        # Fallback: parse table
        result = subprocess.run(
            [
                SYSTEMCTL, "list-units", "--type=service",
                "--no-pager", "--no-legend", "-o", "table", "--plain",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = result.stdout or result.stderr or ""
        line_list = [l for l in out.strip().split("\n") if l.strip()]
        services = []
        for line in line_list:
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
    except FileNotFoundError:
        return {"services": [], "error": "systemctl không tìm thấy"}
    except json.JSONDecodeError:
        return {"services": [], "error": "Không parse được output systemctl"}
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
