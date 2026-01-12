"""Versions API endpoints.

Story 13.1: Server Versions API

Provides endpoints for listing and viewing VintageStory server versions.
Supports channel filtering and includes cache status indicators.
"""

from typing import Literal

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query

from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.models.server import VersionInfo
from vintagestory_api.models.versions import VersionDetailResponse, VersionListResponse
from vintagestory_api.services.server import get_server_service
from vintagestory_api.services.versions_cache import get_versions_cache

logger = structlog.get_logger()

router = APIRouter(prefix="/versions", tags=["Versions"])


async def _fetch_versions_for_channel(channel: str) -> dict[str, VersionInfo]:
    """Fetch versions from API for a single channel.

    Args:
        channel: "stable" or "unstable"

    Returns:
        Dictionary of version -> VersionInfo

    Raises:
        httpx.HTTPError: If API request fails
    """
    server_service = get_server_service()
    return await server_service.get_available_versions(channel)


async def _get_all_versions() -> tuple[list[VersionInfo], bool]:
    """Get all versions from both channels.

    Returns:
        Tuple of (versions_list, is_cached)
    """
    cache = get_versions_cache()
    all_versions: list[VersionInfo] = []
    is_cached = False

    try:
        # Fetch from both channels
        stable_versions = await _fetch_versions_for_channel("stable")
        unstable_versions = await _fetch_versions_for_channel("unstable")

        all_versions = list(stable_versions.values()) + list(unstable_versions.values())
        is_cached = False

    except httpx.HTTPError as e:
        logger.warning("versions_api_error_using_cache", error=str(e))
        # Fall back to cache if API fails
        if cache.has_cached_versions():
            cached_data = cache.get_all_versions()
            for channel_versions in cached_data.values():
                for v in channel_versions:
                    all_versions.append(VersionInfo(**v))
            is_cached = True
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": ErrorCode.EXTERNAL_API_ERROR,
                    "message": "VintageStory API unavailable and no cached data",
                },
            ) from e

    return all_versions, is_cached


async def _get_channel_versions(
    channel: Literal["stable", "unstable"],
) -> tuple[list[VersionInfo], bool]:
    """Get versions for a specific channel.

    Args:
        channel: "stable" or "unstable"

    Returns:
        Tuple of (versions_list, is_cached)
    """
    cache = get_versions_cache()
    is_cached = False

    try:
        versions_dict = await _fetch_versions_for_channel(channel)
        versions_list = list(versions_dict.values())
        is_cached = False

    except httpx.HTTPError as e:
        logger.warning(
            "versions_api_error_using_cache", channel=channel, error=str(e)
        )
        # Fall back to cache if API fails
        cached = cache.get_versions(channel)
        if cached:
            versions_list = [VersionInfo(**v) for v in cached]
            is_cached = True
        else:
            msg = f"VintageStory API unavailable for {channel} channel"
            raise HTTPException(
                status_code=503,
                detail={
                    "code": ErrorCode.EXTERNAL_API_ERROR,
                    "message": f"{msg} and no cached data",
                },
            ) from e

    return versions_list, is_cached


@router.get("", response_model=ApiResponse)
async def list_versions(
    channel: Literal["stable", "unstable"] | None = Query(
        None, description="Filter by release channel"
    ),
) -> ApiResponse:
    """List available server versions.

    Returns all versions or filters by channel. Includes cache status
    to indicate data freshness.

    Args:
        channel: Optional filter for "stable" or "unstable" channel.

    Returns:
        ApiResponse with versions list, total count, and cache status.
    """
    cache = get_versions_cache()

    if channel:
        versions, is_cached = await _get_channel_versions(channel)
    else:
        versions, is_cached = await _get_all_versions()

    response_data = VersionListResponse(
        versions=versions,
        total=len(versions),
        cached=is_cached,
        cached_at=cache.cached_at if is_cached else None,
    )

    return ApiResponse(status="ok", data=response_data.model_dump(mode="json"))


@router.get("/{version}", response_model=ApiResponse)
async def get_version_detail(version: str) -> ApiResponse:
    """Get details for a specific version.

    Searches both stable and unstable channels.

    Args:
        version: Version string (e.g., "1.21.3" or "1.22.0-pre.1")

    Returns:
        ApiResponse with version details and cache status.

    Raises:
        HTTPException: 404 if version not found.
    """
    cache = get_versions_cache()
    found_version: VersionInfo | None = None
    is_cached = False

    try:
        # Search stable channel first
        stable_versions = await _fetch_versions_for_channel("stable")
        if version in stable_versions:
            found_version = stable_versions[version]
        else:
            # Search unstable channel
            unstable_versions = await _fetch_versions_for_channel("unstable")
            if version in unstable_versions:
                found_version = unstable_versions[version]

    except httpx.HTTPError as e:
        logger.warning("versions_api_error_using_cache", error=str(e))
        # Fall back to cache if API fails
        if cache.has_cached_versions():
            is_cached = True
            for channel in ["stable", "unstable"]:
                cached = cache.get_versions(channel)
                for v in cached:
                    if v.get("version") == version:
                        found_version = VersionInfo(**v)
                        break
                if found_version:
                    break
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": ErrorCode.EXTERNAL_API_ERROR,
                    "message": "VintageStory API unavailable and no cached data",
                },
            ) from e

    if found_version is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.VERSION_NOT_FOUND,
                "message": f"Version '{version}' not found",
            },
        )

    response_data = VersionDetailResponse(
        version=found_version,
        cached=is_cached,
        cached_at=cache.cached_at if is_cached else None,
    )

    return ApiResponse(status="ok", data=response_data.model_dump(mode="json"))
