"""Jobs module for periodic background tasks.

Story 8.0: Epic 8 Preparation

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

    Note:
        Story 8.0 creates this stub. Stories 8.1 and 8.2 will add actual jobs:
        - 8.1: mod_cache_refresh job
        - 8.2: server_versions_check job
    """
    # Import settings service here to avoid circular imports
    from vintagestory_api.services.api_settings import ApiSettingsService

    settings = ApiSettingsService().get_settings()
    jobs_registered = 0

    # Story 8.1 will add: mod_cache_refresh job
    if settings.mod_list_refresh_interval > 0:
        # TODO(story-8.1): Implement mod_cache_refresh job
        # from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache
        # scheduler.add_interval_job(
        #     refresh_mod_cache,
        #     seconds=settings.mod_list_refresh_interval,
        #     job_id="mod_cache_refresh"
        # )
        # jobs_registered += 1
        pass

    # Story 8.2 will add: server_versions_check job
    if settings.server_versions_refresh_interval > 0:
        # TODO(story-8.2): Implement server_versions_check job
        # from vintagestory_api.jobs.server_versions import check_server_versions
        # scheduler.add_interval_job(
        #     check_server_versions,
        #     seconds=settings.server_versions_refresh_interval,
        #     job_id="server_versions_check"
        # )
        # jobs_registered += 1
        pass

    logger.info("default_jobs_registered", count=jobs_registered)
