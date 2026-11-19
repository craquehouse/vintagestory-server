"""Jobs module for periodic background tasks.

Story 8.0: Epic 8 Preparation
Story 8.1: Mod Cache Refresh Job
Story 8.2: Server Versions Check Job
Story 12.2: Metrics Collection Job
Story 17.6: Settings behave as saved (Epic 17 ADR-5)
Story 22.3: Scheduled restarts (Epic 22 ADR-6, ADR-7)
Story 22.4: Daily disk cleanup (Epic 22 ADR-7 decisions 3 and 4, ADR-9)

This module provides the infrastructure for registering and managing periodic
background jobs.

Interval settings drive their jobs, at API startup and whenever a setting changes:
`apply_interval_setting()` makes the scheduler match one interval setting, and
`register_default_jobs()` (called from the main.py lifespan) applies each of them
once at startup. An interval of 0 means the job is not registered.

Restart times drive one cron job each, `scheduled_restart_HHMM`, that fires 15 minutes
before the time: `apply_restart_schedule()` makes the restart jobs match the saved times,
at startup and on save. `apply_setting()` is the one callback for every scheduled setting.

The daily `disk_cleanup` job is registered at startup whatever the settings
(`register_disk_cleanup()`); it reads `backup_keep_count` when it runs, so saving it
touches no job.

Example:
    >>> from vintagestory_api.jobs import register_default_jobs
    >>> register_default_jobs(scheduler)  # Called during lifespan startup
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import structlog

from vintagestory_api.models.jobs import job_to_info
from vintagestory_api.services.api_settings import (
    RESTART_TIMES_SETTING,
    ApiSettingsService,
    ScheduledSettingValue,
)

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


def apply_restart_schedule(scheduler: SchedulerService, times: list[str]) -> None:
    """Make the restart jobs match the saved times (Epic 22 ADR-7 decision 1).

    Removes every `scheduled_restart_*` job whose time is no longer wanted and adds or
    replaces one cron job per time, firing 15 minutes before it in the process's local
    zone (TZ). A time less than 15 minutes ahead first fires the next day. A sequence in
    its warnings is not cancelled here; it ends at its next step when its job is gone.

    Args:
        scheduler: The SchedulerService to update.
        times: The saved restart times, validated HH:MM.
    """
    from vintagestory_api.jobs.scheduled_restart import (
        RESTART_JOB_PREFIX,
        restart_job_id,
        scheduled_restart,
        warning_start,
    )

    wanted = {restart_job_id(restart_time): restart_time for restart_time in times}
    removed: list[str] = []
    for job in scheduler.get_jobs():
        job_id = job_to_info(job).id
        if job_id.startswith(RESTART_JOB_PREFIX) and job_id not in wanted:
            scheduler.remove_job(job_id)
            removed.append(job_id)

    for job_id, restart_time in wanted.items():
        hour, minute = warning_start(restart_time)
        scheduler.add_cron_job(
            scheduled_restart,
            f"{minute} {hour} * * *",
            job_id=job_id,
            kwargs={"restart_time": restart_time, "scheduler": scheduler},
        )
        logger.info(
            "job_registered",
            job_id=job_id,
            restart_time=restart_time,
            first_warning=f"{hour:02d}:{minute:02d}",
        )

    logger.info("restart_schedule_applied", times=times, removed=removed)


def apply_setting(scheduler: SchedulerService, key: str, value: ScheduledSettingValue) -> None:
    """The scheduler callback for every scheduled setting (Epic 22 ADR-7 decisions 1 and 2).

    Args:
        scheduler: The SchedulerService to update.
        key: The saved setting's key.
        value: Its stored value.

    Raises:
        TypeError: If the value does not fit the key (a programming error).
    """
    if key in INTERVAL_JOBS:
        # bool is an int subclass: True would register a 1-second interval.
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{key} takes an int, got {type(value).__name__}")
        apply_interval_setting(scheduler, key, value)
    elif key == RESTART_TIMES_SETTING:
        if not isinstance(value, list):
            raise TypeError(f"{key} takes a list, got {type(value).__name__}")
        apply_restart_schedule(scheduler, value)


def register_disk_cleanup(scheduler: SchedulerService) -> None:
    """Register the daily disk cleanup job at 03:00 local time (Story 22.4).

    Registered whatever the settings (Epic 22 ADR-7 decision 3): the job reads its limits
    when it runs (decision 4). Replaces an existing `disk_cleanup` job.

    Args:
        scheduler: The SchedulerService to register the job with.
    """
    from vintagestory_api.jobs.disk_cleanup import (
        DISK_CLEANUP_CRON,
        DISK_CLEANUP_JOB_ID,
        disk_cleanup,
    )

    scheduler.add_cron_job(disk_cleanup, DISK_CLEANUP_CRON, job_id=DISK_CLEANUP_JOB_ID)
    logger.info("job_registered", job_id=DISK_CLEANUP_JOB_ID, cron=DISK_CLEANUP_CRON)


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
        - scheduled_restart_HHMM (Story 22.3): One per saved restart time, through
          `apply_restart_schedule`
        - disk_cleanup (Story 22.4): Daily at 03:00 (old backups, when a limit is
          set), whatever the settings, through `register_disk_cleanup`
    """
    settings = ApiSettingsService().get_settings()
    jobs_registered = 0

    for key in INTERVAL_JOBS:
        seconds: int = getattr(settings, key)
        apply_interval_setting(scheduler, key, seconds, startup=True)
        if seconds > 0:
            jobs_registered += 1

    apply_restart_schedule(scheduler, settings.scheduled_restart_times)
    register_disk_cleanup(scheduler)

    logger.info(
        "default_jobs_registered",
        count=jobs_registered,
        restart_jobs=len(settings.scheduled_restart_times),
    )
