"""Daily disk cleanup job (Epic 22 ADR-9 decision 6, as amended 2026-11-19).

Story 22.4: Log Archive and Backup Cleanup

Every day at 03:00 in the process's local time zone, when `backup_keep_count` is above 0,
keeps only that many newest `/genbackup` files in `serverdata/Backups/` (see
`services/disk_cleanup.py` for the rules). The game's log archives are left to the game,
which keeps at most 5. The limit is read from `api-settings.json` at each run, so a saved
limit applies at the next run without touching the job (Epic 22 ADR-7 decision 4). The job
runs whether the game server is running or not.
"""

from __future__ import annotations

import asyncio

from vintagestory_api.config import Settings
from vintagestory_api.jobs.base import safe_job
from vintagestory_api.services.api_settings import ApiSettingsService
from vintagestory_api.services.disk_cleanup import (
    CleanupLimits,
    CleanupResult,
    DiskCleanupService,
)

DISK_CLEANUP_JOB_ID = "disk_cleanup"
DISK_CLEANUP_CRON = "0 3 * * *"
"""03:00 every day in the process's local time zone (TZ, UTC when unset)."""


async def run_disk_cleanup(settings: Settings) -> CleanupResult:
    """Read the limit now and run the cleanup in a worker thread.

    The worker thread keeps file deletion from blocking the event loop (console,
    WebSocket, requests); the service touches no shared state.
    """
    api_settings = ApiSettingsService(settings).get_settings()
    limits = CleanupLimits(backup_keep_count=api_settings.backup_keep_count)
    service = DiskCleanupService(settings.serverdata_dir)
    return await asyncio.to_thread(service.run, limits)


@safe_job("disk_cleanup")
async def disk_cleanup() -> None:
    """The job function: get_server_service().settings, then run_disk_cleanup."""
    from vintagestory_api.services.server import get_server_service

    await run_disk_cleanup(get_server_service().settings)
