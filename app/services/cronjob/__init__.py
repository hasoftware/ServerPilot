"""Cronjob service module."""
from app.services.cronjob.scheduler import cron_scheduler

__all__ = ["cron_scheduler"]
