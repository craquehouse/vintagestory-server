"""Jobs module for periodic background tasks.

Story 8.0: Epic 8 Preparation
Story 8.1: Mod Cache Refresh Job
Story 8.2: Server Versions Check Job

This module provides the infrastructure for registering and managing periodic
background jobs. Jobs are registered during application startup via the
`register_default_jobs()` function, which is called from main.py lifespan.

Job Registration Pattern:
    Jobs are only registered if their corresponding interval setting is > 0.
    This allows disabling jobs by setting interval to 0 in api-settings.json.

Example:
    >>> from vintagestory_api.jobs import register_default_jobs
    >>> register_default_jobs(scheduler)  # Called during lifespan startup
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from vintagestory_api.services.api_settings import ApiSettingsService

if TYPE_CHECKING:
    from vintagestory_api.services.scheduler import SchedulerService

logger = structlog.get_logger()


def register_default_jobs(scheduler: SchedulerService) -> None:
    """Register all default periodic jobs with the scheduler.

    This function is called during application startup (in main.py lifespan)
    after the scheduler has been started. It reads API settings to determine
    which jobs should be registered based on their interval values.

    Jobs with interval=0 are NOT registered (disabled).

    Args:
        scheduler: The SchedulerService instance to register jobs with.

    Registered Jobs:
        - mod_cache_refresh (Story 8.1): Refreshes mod metadata from API
        - server_versions_check (Story 8.2): Checks for new VintageStory versions
    """
    settings = ApiSettingsService().get_settings()
    jobs_registered = 0

    # Story 8.1: mod_cache_refresh job
    # Registered when settings.mod_list_refresh_interval > 0
    if settings.mod_list_refresh_interval > 0:
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        scheduler.add_interval_job(
            refresh_mod_cache,
            seconds=settings.mod_list_refresh_interval,
            job_id="mod_cache_refresh",
        )
        jobs_registered += 1
        logger.info(
            "job_registered",
            job_id="mod_cache_refresh",
            interval_seconds=settings.mod_list_refresh_interval,
        )

    # Story 8.2: server_versions_check job
    # Registered when settings.server_versions_refresh_interval > 0
    # Runs immediately at startup to populate version cache, then on interval
    if settings.server_versions_refresh_interval > 0:
        from vintagestory_api.jobs.server_versions import check_server_versions

        scheduler.add_interval_job(
            check_server_versions,
            seconds=settings.server_versions_refresh_interval,
            job_id="server_versions_check",
            run_immediately=True,  # Populate cache at startup
        )
        jobs_registered += 1
        logger.info(
            "job_registered",
            job_id="server_versions_check",
            interval_seconds=settings.server_versions_refresh_interval,
            run_immediately=True,
        )

    logger.info("default_jobs_registered", count=jobs_registered)
