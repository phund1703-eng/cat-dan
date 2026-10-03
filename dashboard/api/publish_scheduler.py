"""
Lightweight publish scheduler for the dashboard API (Task 3.3).

APScheduler periodically asks the worker for jobs at stage ``scheduled``
whose time has arrived. It is intentionally easy to disable in tests and
one-off CLI runs through ``CATDAN_PUBLISH_SCHEDULER_ENABLED=0``.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from loguru import logger

_scheduler: Optional[Any] = None


def scheduler_enabled() -> bool:
    """Return whether the in-process publish scheduler should run."""
    raw = os.getenv("CATDAN_PUBLISH_SCHEDULER_ENABLED")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    # Pytest imports the API app in-process; never start a real background
    # thread unless a test explicitly opts in via the environment flag.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    return True


def start_publish_scheduler() -> Optional[Any]:
    """Start the due-publish polling job, or return the existing scheduler."""
    global _scheduler
    if not scheduler_enabled():
        logger.info("Publish scheduler disabled by environment/test mode")
        return None
    if _scheduler is not None:
        return _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        from dashboard.worker.video_tasks import run_due_publish_jobs

        try:
            interval_seconds = int(os.getenv("CATDAN_PUBLISH_SCHEDULER_INTERVAL_SECONDS", "30"))
        except ValueError:
            interval_seconds = 30
        interval_seconds = max(5, interval_seconds)

        scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
        scheduler.add_job(
            run_due_publish_jobs,
            trigger="interval",
            seconds=interval_seconds,
            id="catdan_due_publish_jobs",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        _scheduler = scheduler
        logger.info(f"Publish scheduler started (every {interval_seconds}s)")
        return scheduler
    except Exception as exc:
        logger.warning(f"Could not start publish scheduler: {exc}")
        return None


def shutdown_publish_scheduler() -> None:
    """Stop the process-local scheduler during API shutdown."""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception as exc:
            logger.warning(f"Could not stop publish scheduler cleanly: {exc}")
        finally:
            _scheduler = None
