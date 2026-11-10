"""Mod cache refresh job.

Story 8.1: Mod Cache Refresh Job. Runs on `mod_list_refresh_interval`; an interval of 0
leaves it unregistered (see `jobs/__init__.py`).

Story 14.5 (ADR-5): the job records update status for every installed mod by running
the mod update check, the same code path as the on-demand check. The check fetches each
installed mod from the mod database (as this job already did), stores its releases, and
isolates failures per mod: a failed lookup keeps that mod's previous data and records
the error.
"""

from __future__ import annotations

import structlog

from vintagestory_api.jobs.base import safe_job
from vintagestory_api.services.mod_updates import (
    ModUpdateCheckInProgressError,
    get_mod_update_service,
)

logger = structlog.get_logger()


@safe_job("mod_cache_refresh")
async def refresh_mod_cache() -> None:
    """Refresh installed mods from the mod database and record their update status.

    Skips the run if an on-demand check is already in progress. Never raises; the
    @safe_job decorator logs unexpected failures.
    """
    service = get_mod_update_service()
    try:
        summary = await service.check()
    except ModUpdateCheckInProgressError:
        logger.info("mod_cache_refresh_skipped", reason="update check already running")
        return

    updates = sum(1 for item in service.get_status() if item.status == "update_available")
    logger.info(
        "mod_cache_refresh_summary",
        checked=summary.checked,
        failed=summary.failed,
        failed_slugs=summary.failed_slugs or None,
        updates_available=updates,
    )
