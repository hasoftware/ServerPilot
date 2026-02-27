"""Dashboard API - server metrics."""
import time
from pathlib import Path

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth.dependencies import require_setup_complete
from app.database.database import get_db
from app.database.models import Cronjob, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Track server start time for uptime
_server_start_time = time.time()


@router.get("/metrics")
async def get_metrics(
    db=Depends(get_db),
    current_user: User = Depends(require_setup_complete),
):
    """Get server metrics for dashboard."""
    uptime_seconds = int(time.time() - _server_start_time)
    uptime_days = uptime_seconds // 86400
    uptime_hours = (uptime_seconds % 86400) // 3600
    uptime_mins = (uptime_seconds % 3600) // 60
    uptime_str = f"{uptime_days}d {uptime_hours}h {uptime_mins}m"

    cpu_percent = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    result = await db.execute(select(Cronjob).where(Cronjob.enabled == True))
    active_cronjobs = len(result.scalars().all())

    return {
        "uptime": uptime_str,
        "uptime_seconds": uptime_seconds,
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": round(mem.percent, 1),
        "memory_used_gb": round(mem.used / (1024**3), 2),
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "disk_percent": round(disk.percent, 1),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "active_cronjobs": active_cronjobs,
    }
