"""APScheduler-based cronjob scheduler - loads from DB, no system crontab."""
import asyncio
import logging
from typing import Set

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import async_session
from app.database.models import Cronjob
from app.services.cronjob.executor import execute_cronjob

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()
_running_jobs: Set[int] = set()  # Track running jobs to prevent duplicates


async def _run_cronjob(cronjob_id: int) -> None:
    """Wrapper to execute cronjob - prevents duplicate runs."""
    if cronjob_id in _running_jobs:
        logger.warning(f"Cronjob {cronjob_id} already running, skipping")
        return

    _running_jobs.add(cronjob_id)
    try:
        async with async_session() as db:
            result = await db.execute(
                select(Cronjob).where(Cronjob.id == cronjob_id, Cronjob.enabled == True)
            )
            cronjob = result.scalar_one_or_none()
            if cronjob:
                await execute_cronjob(cronjob_id, cronjob.url, cronjob.method)
    except Exception as e:
        logger.exception(f"Error executing cronjob {cronjob_id}: {e}")
    finally:
        _running_jobs.discard(cronjob_id)


def _job_wrapper(cronjob_id: int):
    """Sync wrapper - schedule async task in running event loop."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run_cronjob(cronjob_id))
    except Exception as e:
        logger.exception(f"Scheduler job wrapper error for {cronjob_id}: {e}")


def _parse_cron_expression(expr: str) -> dict:
    """
    Parse cron expression to APScheduler format.
    Hỗ trợ 5 field: minute hour day month day_of_week (giây = 0)
    Hỗ trợ 6 field: second minute hour day month day_of_week
    """
    parts = expr.strip().split()
    if len(parts) == 6:
        return {
            "second": parts[0],
            "minute": parts[1],
            "hour": parts[2],
            "day": parts[3],
            "month": parts[4],
            "day_of_week": parts[5],
        }
    if len(parts) == 5:
        return {
            "second": "0",
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
        }
    raise ValueError(f"Invalid cron: {expr} (cần 5 hoặc 6 field)")


async def load_cronjobs_into_scheduler() -> None:
    """Load all enabled cronjobs from DB into scheduler. Removes old jobs first."""
    # Remove existing jobs for our app
    for job in scheduler.get_jobs():
        if job.id and job.id.startswith("cronjob_"):
            try:
                scheduler.remove_job(job.id)
            except Exception:
                pass

    async with async_session() as db:
        result = await db.execute(select(Cronjob).where(Cronjob.enabled == True))
        cronjobs = result.scalars().all()

    for cj in cronjobs:
        try:
            trigger = _parse_cron_expression(cj.cron_expression)
            job_id = f"cronjob_{cj.id}"
            scheduler.add_job(
                _job_wrapper,
                trigger=CronTrigger(**trigger),
                id=job_id,
                args=[cj.id],
                replace_existing=True,
            )
            logger.info(f"Loaded cronjob {cj.id} ({cj.name}) with expression {cj.cron_expression}")
        except Exception as e:
            logger.error(f"Failed to load cronjob {cj.id}: {e}")

    logger.info(f"Scheduler loaded {len(cronjobs)} cronjobs")


def start_scheduler() -> None:
    """Start the scheduler (call after app startup)."""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")


def shutdown_scheduler() -> None:
    """Shutdown scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("APScheduler shutdown")


# Alias for clarity
cron_scheduler = scheduler
