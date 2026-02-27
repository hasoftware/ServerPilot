"""Cronjob URL executor - CURL/WGET style execution."""
import time
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LOG_RETENTION_DAYS
from app.database.database import async_session
from app.database.models import Cronjob, CronjobLog


async def execute_cronjob(cronjob_id: int, url: str, method: str) -> None:
    """
    Execute cronjob URL using httpx (equivalent to CURL/WGET).
    CURL and WGET both do HTTP GET by default - we support GET/POST via method.
    """
    start = time.perf_counter()
    status = "failed"
    status_code = None
    output = None
    error = None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "WGET" or method.upper() == "GET":
                response = await client.get(url)
            elif method.upper() == "POST":
                response = await client.post(url)
            elif method.upper() == "CURL":
                # CURL default is GET
                response = await client.get(url)
            else:
                response = await client.get(url)

            status_code = response.status_code
            status = "success" if 200 <= status_code < 400 else "failed"
            output = response.text[:10000] if response.text else None  # Limit output size

    except Exception as e:
        error = str(e)[:2000]  # Limit error size
        status = "error"

    duration_ms = int((time.perf_counter() - start) * 1000)

    async with async_session() as db:
        result = await db.execute(select(Cronjob).where(Cronjob.id == cronjob_id))
        cronjob = result.scalar_one_or_none()
        if cronjob and cronjob.enable_log:
            log_entry = CronjobLog(
                cronjob_id=cronjob_id,
                status=status,
                status_code=status_code,
                output=output,
                error=error,
                duration_ms=duration_ms,
            )
            db.add(log_entry)
            await db.commit()

            # Clean old logs if needed (limit per cronjob)
            await _cleanup_logs(db, cronjob_id)


async def _cleanup_logs(db: AsyncSession, cronjob_id: int) -> None:
    """Keep only recent logs based on LOG_RETENTION_DAYS."""
    from sqlalchemy import delete
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=LOG_RETENTION_DAYS)
    await db.execute(delete(CronjobLog).where(
        CronjobLog.cronjob_id == cronjob_id,
        CronjobLog.executed_at < cutoff
    ))
    await db.commit()
