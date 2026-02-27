"""Cronjob API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_setup_complete
from app.database.database import get_db
from app.database.models import Cronjob, CronjobLog, User
from app.services.cronjob.scheduler import load_cronjobs_into_scheduler

router = APIRouter(prefix="/api/cronjobs", tags=["cronjobs"])


class CronjobCreate(BaseModel):
    name: str
    url: str
    method: str = "CURL"
    cron_expression: str
    enable_log: bool = True


class CronjobUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    enable_log: Optional[bool] = None


@router.get("")
async def list_cronjobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_setup_complete),
):
    """List all cronjobs."""
    result = await db.execute(select(Cronjob).order_by(Cronjob.id))
    jobs = result.scalars().all()
    return [
        {
            "id": j.id,
            "name": j.name,
            "url": j.url,
            "method": j.method,
            "cron_expression": j.cron_expression,
            "enabled": j.enabled,
            "enable_log": j.enable_log,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


@router.post("")
async def create_cronjob(
    data: CronjobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_setup_complete),
):
    """Create new cronjob."""
    if data.method.upper() not in ("CURL", "WGET", "GET", "POST"):
        raise HTTPException(status_code=400, detail="Method must be CURL, WGET, GET, or POST")

    cronjob = Cronjob(
        name=data.name,
        url=data.url,
        method=data.method.upper(),
        cron_expression=data.cron_expression.strip(),
        enable_log=data.enable_log,
    )
    db.add(cronjob)
    await db.commit()
    await db.refresh(cronjob)

    await load_cronjobs_into_scheduler()
    return {"id": cronjob.id, "message": "Cronjob created"}


@router.get("/{cronjob_id}")
async def get_cronjob(
    cronjob_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_setup_complete),
):
    """Get single cronjob."""
    result = await db.execute(select(Cronjob).where(Cronjob.id == cronjob_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Cronjob not found")
    return {
        "id": job.id,
        "name": job.name,
        "url": job.url,
        "method": job.method,
        "cron_expression": job.cron_expression,
        "enabled": job.enabled,
        "enable_log": job.enable_log,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.put("/{cronjob_id}")
async def update_cronjob(
    cronjob_id: int,
    data: CronjobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_setup_complete),
):
    """Update cronjob."""
    result = await db.execute(select(Cronjob).where(Cronjob.id == cronjob_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Cronjob not found")

    if data.name is not None:
        job.name = data.name
    if data.url is not None:
        job.url = data.url
    if data.method is not None:
        if data.method.upper() not in ("CURL", "WGET", "GET", "POST"):
            raise HTTPException(status_code=400, detail="Invalid method")
        job.method = data.method.upper()
    if data.cron_expression is not None:
        job.cron_expression = data.cron_expression.strip()
    if data.enabled is not None:
        job.enabled = data.enabled
    if data.enable_log is not None:
        job.enable_log = data.enable_log

    db.add(job)
    await db.commit()
    await load_cronjobs_into_scheduler()
    return {"message": "Cronjob updated"}


@router.delete("/{cronjob_id}")
async def delete_cronjob(
    cronjob_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_setup_complete),
):
    """Delete cronjob."""
    result = await db.execute(select(Cronjob).where(Cronjob.id == cronjob_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Cronjob not found")
    await db.delete(job)
    await db.commit()
    await load_cronjobs_into_scheduler()
    return {"message": "Cronjob deleted"}


@router.post("/{cronjob_id}/run")
async def run_cronjob_now(
    cronjob_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_setup_complete),
):
    """Run cronjob manually once."""
    result = await db.execute(select(Cronjob).where(Cronjob.id == cronjob_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Cronjob not found")

    from app.services.cronjob.executor import execute_cronjob
    await execute_cronjob(job.id, job.url, job.method)
    return {"message": "Cronjob executed"}


@router.get("/{cronjob_id}/logs")
async def get_cronjob_logs(
    cronjob_id: int,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_setup_complete),
):
    """Get logs for a cronjob."""
    result = await db.execute(select(Cronjob).where(Cronjob.id == cronjob_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Cronjob not found")
    if not job.enable_log:
        return {"logs": [], "message": "Logging disabled for this cronjob"}

    logs_result = await db.execute(
        select(CronjobLog)
        .where(CronjobLog.cronjob_id == cronjob_id)
        .order_by(CronjobLog.executed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    logs = logs_result.scalars().all()
    return {
        "logs": [
            {
                "id": l.id,
                "status": l.status,
                "status_code": l.status_code,
                "output": l.output,
                "error": l.error,
                "duration_ms": l.duration_ms,
                "executed_at": l.executed_at.isoformat() if l.executed_at else None,
            }
            for l in logs
        ]
    }
