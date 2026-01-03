"""Server versions check job.

Story 8.2: Server Versions Check Job

This job periodically checks for new VintageStory server versions by querying
the VintageStory API. It caches the latest versions for display in the status
API and logs when new versions are detected.

AC 1: Job executes at configured interval (registration in __init__.py)
AC 2: New versions are logged and made available via status API
AC 3: API failures are logged but don't stop the job, stale cache preserved
"""

from __future__ import annotations

import httpx
import structlog

from vintagestory_api.jobs.base import safe_job
from vintagestory_api.services.server import get_server_service
from vintagestory_api.services.versions_cache import get_versions_cache

logger = structlog.get_logger()


@safe_job("server_versions_check")
async def check_server_versions() -> None:
    """Check for new VintageStory server versions.

    This job queries the VintageStory API for the latest stable and
    unstable versions and caches them for display in the status API.
    When a new version is detected (different from the cached version),
    an info log is emitted.

    The job handles API errors gracefully:
    - Individual channel failures don't affect the other channel
    - Stale cache data is preserved when API is unreachable
    - The scheduler continues running regardless of errors

    Returns:
        None. Results are logged and cached.
    """
    server_service = get_server_service()
    cache = get_versions_cache()
    old_versions = cache.get_latest_versions()

    new_stable: str | None = None
    new_unstable: str | None = None
    stable_error = False
    unstable_error = False

    # Check stable channel
    try:
        stable_versions = await server_service.get_available_versions("stable")
        new_stable = next(
            (v for v, info in stable_versions.items() if info.is_latest),
            None,
        )
    except httpx.HTTPError as e:
        stable_error = True
        logger.warning(
            "server_versions_stable_api_error",
            error=str(e),
        )

    # Check unstable channel
    try:
        unstable_versions = await server_service.get_available_versions("unstable")
        new_unstable = next(
            (v for v, info in unstable_versions.items() if info.is_latest),
            None,
        )
    except httpx.HTTPError as e:
        unstable_error = True
        logger.warning(
            "server_versions_unstable_api_error",
            error=str(e),
        )

    # Detect new versions (only log if we got data and it differs)
    if new_stable and new_stable != old_versions.stable_version:
        logger.info(
            "new_stable_version_detected",
            old_version=old_versions.stable_version,
            new_version=new_stable,
        )

    if new_unstable and new_unstable != old_versions.unstable_version:
        logger.info(
            "new_unstable_version_detected",
            old_version=old_versions.unstable_version,
            new_version=new_unstable,
        )

    logger.info(
        "version_check_summary",
        stable=new_stable,
        unstable=new_unstable,
    )

    # Update cache with any successfully fetched versions
    # If API failed for a channel, preserve the old value (don't update with None)
    if not stable_error and new_stable:
        cache.set_latest_versions(stable=new_stable)
    if not unstable_error and new_unstable:
        cache.set_latest_versions(unstable=new_unstable)

    # Log summary
    logger.info(
        "version_check_summary",
        stable=new_stable,
        unstable=new_unstable,
        stable_error=stable_error,
        unstable_error=unstable_error,
    )
