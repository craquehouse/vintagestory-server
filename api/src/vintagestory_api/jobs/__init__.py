"""Jobs module for periodic background tasks.

Story 8.0: Epic 8 Preparation
Story 8.1: Mod Cache Refresh Job
Story 8.2: Server Versions Check Job
Story 12.2: Metrics Collection Job
Story 17.6: Settings behave as saved (Epic 17 ADR-5)

This module provides the infrastructure for registering and managing periodic
background jobs.

Interval settings drive their jobs, at API startup and whenever a setting changes:
`apply_interval_setting()` makes the scheduler match one interval setting, and
`register_default_jobs()` (called from the main.py lifespan) applies each of them
once at startup. An interval of 0 means the job is not registered.

Example:
    >>> from vintagestory_api.jobs import register_default_jobs
    >>> register_default_jobs(scheduler)  # Called during lifespan startup
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import structlog

from vintagestory_api.services.api_settings import ApiSettingsService

if TYPE_CHECKING:
    from vintagestory_api.services.scheduler import SchedulerService

logger = structlog.get_logger()


INTERVAL_JOBS: dict[str, str] = {
    "mod_list_refresh_interval": "mod_cache_refresh",
    "server_versions_refresh_interval": "server_versions_check",
    "metrics_collection_interval": "metrics_collection",
}
"""Interval setting -> the job it drives (Story 17.6). 0 means the job is not registered."""

_RUN_AT_STARTUP = "server_versions_check"
"""The job that also runs once at API start, to populate the version cache (Story 8.2)."""


def _job_function(key: str) -> Callable[[], Awaitable[None]]:
    """The job function an interval setting drives, imported lazily."""
    if key == "mod_list_refresh_interval":
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        return refresh_mod_cache
    if key == "server_versions_refresh_interval":
        from vintagestory_api.jobs.server_versions import check_server_versions

        return check_server_versions
    from vintagestory_api.jobs.metrics_collection import collect_metrics

    return collect_metrics


def apply_interval_setting(
    scheduler: SchedulerService, key: str, seconds: int, *, startup: bool = False
) -> None:
    """Make the scheduler match one interval setting (Story 17.6, Epic 17 ADR-5).

    Above 0 adds the setting's job or replaces it; its next run is one interval from
    now. 0 removes the job when it is registered. `startup` only makes
    `server_versions_check` run once at once, as it always has at API start.

    A job execution in progress is not cancelled by a replace or a removal: it runs
    to the end.

    Args:
        scheduler: The SchedulerService to update.
        key: An interval setting key (a key of INTERVAL_JOBS).
        seconds: The setting's value; 0 disables the job.
        startup: True only when called from register_default_jobs.

    Raises:
        KeyError: If key is not an interval setting (a programming error).
    """
    job_id = INTERVAL_JOBS[key]

    if seconds <= 0:
        if scheduler.get_job(job_id) is not None:
            scheduler.remove_job(job_id)
        return

    run_immediately = startup and job_id == _RUN_AT_STARTUP
    scheduler.add_interval_job(
        _job_function(key),
        seconds=seconds,
        job_id=job_id,
        run_immediately=run_immediately,
    )
    if run_immediately:
        logger.info(
            "job_registered",
            job_id=job_id,
            interval_seconds=seconds,
            run_immediately=True,
        )
    else:
        logger.info("job_registered", job_id=job_id, interval_seconds=seconds)


def register_default_jobs(scheduler: SchedulerService) -> None:
    """Register all default periodic jobs with the scheduler.

    This function is called during application startup (in main.py lifespan)
    after the scheduler has been started. It reads API settings and applies each
    interval setting through `apply_interval_setting`, the same function a
    settings change uses (Story 17.6).

    Jobs with interval=0 are NOT registered (disabled).

    Args:
        scheduler: The SchedulerService instance to register jobs with.

    Registered Jobs:
        - mod_cache_refresh (Story 8.1): Refreshes mod metadata from API
        - server_versions_check (Story 8.2): Checks for new VintageStory versions,
          also once at startup
        - metrics_collection (Story 12.2): Collects server metrics periodically
    """
    settings = ApiSettingsService().get_settings()
    jobs_registered = 0

    for key in INTERVAL_JOBS:
        seconds: int = getattr(settings, key)
        apply_interval_setting(scheduler, key, seconds, startup=True)
        if seconds > 0:
            jobs_registered += 1

    logger.info("default_jobs_registered", count=jobs_registered)
