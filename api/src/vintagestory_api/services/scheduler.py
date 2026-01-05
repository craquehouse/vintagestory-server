"""Scheduler service for managing periodic background tasks.

Story 7.1: SchedulerService

This service wraps APScheduler's AsyncIOScheduler to provide a clean interface
for scheduling periodic jobs. It integrates with FastAPI's lifespan context
for proper startup/shutdown handling.

CRITICAL: Use APScheduler v3.11.x patterns only, NOT v4.x (still alpha).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog

# APScheduler v3.x does not ship with type stubs
# TODO: Track APScheduler type stubs availability - may add py.typed in future release
# See: https://github.com/agronholm/apscheduler/issues (no stubs package available as of 2026-01)
from apscheduler.executors.asyncio import AsyncIOExecutor  # type: ignore[import-untyped]
from apscheduler.job import Job  # type: ignore[import-untyped]
from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore[import-untyped]
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]

logger = structlog.get_logger()


class SchedulerService:
    """Manages periodic background tasks using APScheduler.

    This service provides a simplified interface for scheduling interval and cron
    jobs, with proper lifecycle management for FastAPI integration.

    Attributes:
        scheduler: The underlying APScheduler AsyncIOScheduler instance.
        is_running: Whether the scheduler is currently running.

    Example:
        >>> scheduler = SchedulerService()
        >>> scheduler.start()
        >>> scheduler.add_interval_job(my_async_func, seconds=60, job_id="my_job")
        >>> # Later...
        >>> scheduler.shutdown()
    """

    def __init__(self) -> None:
        """Initialize the scheduler with memory-based job store.

        Configures job defaults for robustness:
        - coalesce: True - Combine missed runs into one
        - max_instances: 1 - Prevent overlapping executions
        - misfire_grace_time: 60 - Allow 60s late execution
        """
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            executors={"default": AsyncIOExecutor()},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 60,
            },
        )
        self._running = False

    def start(self) -> None:
        """Start the scheduler.

        This should be called during application startup (e.g., in FastAPI lifespan).
        Logs "scheduler_started" on successful start.
        """
        self.scheduler.start()
        self._running = True
        logger.info("scheduler_started")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler gracefully.

        Args:
            wait: If True, wait for running jobs to complete before returning.
                  If False, terminate immediately.

        This should be called during application shutdown (e.g., in FastAPI lifespan).
        Logs "scheduler_stopped" on successful shutdown.
        """
        self.scheduler.shutdown(wait=wait)
        self._running = False
        logger.info("scheduler_stopped")

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is currently running.

        Returns:
            True if scheduler is running, False otherwise.
        """
        return self._running

    def add_interval_job(
        self,
        func: Callable[..., Any],
        seconds: int,
        job_id: str,
        **kwargs: Any,
    ) -> Job:
        """Add a job that runs at fixed intervals.

        Args:
            func: The async or sync function to execute.
            seconds: Interval between executions in seconds.
            job_id: Unique identifier for the job.
            **kwargs: Additional arguments passed to scheduler.add_job().

        Returns:
            The APScheduler Job instance.

        Example:
            >>> async def refresh_cache():
            ...     pass
            >>> scheduler.add_interval_job(refresh_cache, seconds=3600, job_id="cache_refresh")
        """
        job: Job = self.scheduler.add_job(  # type: ignore[reportUnknownMemberType]
            func,
            trigger=IntervalTrigger(seconds=seconds),
            id=job_id,
            replace_existing=True,
            **kwargs,
        )
        logger.info("job_added", job_id=job_id, trigger_type="interval", seconds=seconds)
        return job

    def add_cron_job(
        self,
        func: Callable[..., Any],
        cron_expr: str,
        job_id: str,
        **kwargs: Any,
    ) -> Job:
        """Add a job that runs on a cron schedule.

        Args:
            func: The async or sync function to execute.
            cron_expr: Cron expression string (e.g., "0 */6 * * *" for every 6 hours).
            job_id: Unique identifier for the job.
            **kwargs: Additional arguments passed to scheduler.add_job().

        Returns:
            The APScheduler Job instance.

        Example:
            >>> async def daily_cleanup():
            ...     pass
            >>> scheduler.add_cron_job(daily_cleanup, "0 2 * * *", job_id="daily_cleanup")
        """
        job: Job = self.scheduler.add_job(  # type: ignore[reportUnknownMemberType]
            func,
            trigger=CronTrigger.from_crontab(cron_expr),  # type: ignore[reportUnknownMemberType]
            id=job_id,
            replace_existing=True,
            **kwargs,
        )
        logger.info("job_added", job_id=job_id, trigger_type="cron", cron_expr=cron_expr)
        return job

    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job.

        Args:
            job_id: The unique identifier of the job to remove.

        Raises:
            JobLookupError: If no job with the given ID exists.
        """
        self.scheduler.remove_job(job_id)  # type: ignore[reportUnknownMemberType]
        logger.info("job_removed", job_id=job_id)

    def get_jobs(self) -> list[Job]:  # type: ignore[type-arg]
        """Get all scheduled jobs.

        Returns:
            List of all currently scheduled Job instances.
        """
        return self.scheduler.get_jobs()  # type: ignore[return-value]

    def get_job(self, job_id: str) -> Job | None:  # type: ignore[return]
        """Get a specific job by ID.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            The Job instance if found, None otherwise.
        """
        return self.scheduler.get_job(job_id)  # type: ignore[return-value]
