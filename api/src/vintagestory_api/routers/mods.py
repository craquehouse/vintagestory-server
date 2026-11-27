"""Mod management API endpoints."""

import asyncio
import math
import uuid
from dataclasses import asdict
from functools import partial
from typing import Annotated, Any, Literal

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import get_current_user, get_settings
from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.mods import ModBrowseItem, ModBrowseResponse, ModInfo, PaginationMeta
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.services.mod_api import (
    DownloadError,
    ExternalApiError,
    GameVersionNotFoundError,
    ModDict,
    ModReleaseNotDownloadableError,
    ModVersionNotFoundError,
    SortOption,
    search_mods,
    sort_mods,
    validate_slug,
)
from vintagestory_api.services.mod_api import (
    ModNotFoundError as ApiModNotFoundError,
)
from vintagestory_api.services.mod_link import (
    LinkDownloadError,
    ModUrlInvalidError,
    check_link,
    downloaded,
    name_from_modinfo,
    stored_link,
)
from vintagestory_api.services.mod_media import checked_url, mod_image_url
from vintagestory_api.services.mod_updates import (
    ModUpdateAllInProgressError,
    ModUpdateCheckInProgressError,
    ModUpdateService,
    get_mod_update_service,
    is_release_mod,
)
from vintagestory_api.services.mod_upload import (
    ModFileInvalidError,
    ModFileTooLargeError,
    incoming_file,
    safe_archive_name,
    write_limited,
)
from vintagestory_api.services.mods import (
    ArchiveInstallResult,
    InvalidSlugError,
    ModAlreadyInstalledError,
    ModConfirmationRequiredError,
    ModFileConflictError,
    ModFileMissingError,
    ModNotFoundError,
    ModNotFromDatabaseError,
    ModOperationInProgressError,
    ModsBusyError,
    ModService,
    ModValidationError,
    ModVersionChangeFailedError,
    UnusedFileDeleteFailedError,
    UnusedFileNotFoundError,
    get_mod_service,
)
from vintagestory_api.services.safe_fetch import AddressBlockedError, parse_private_hosts

logger = structlog.get_logger()

router = APIRouter(prefix="/mods", tags=["Mods"])


# Type alias for authenticated user (Admin or Monitor)
RequireAuth = Annotated[str, Depends(get_current_user)]


@router.get("", response_model=ApiResponse, summary="List installed mods")
async def list_mods(
    _: RequireAuth,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """List all installed mods with status information.

    Returns a list of installed mods with their metadata, enabled status,
    and compatibility information. Also includes pending_restart flag.

    Both Admin and Monitor roles can access this read-only endpoint.

    Returns:
        ApiResponse with data containing:
        - mods: Array of mod information objects
        - pending_restart: Whether server restart is required

    Raises:
        HTTPException: 401 if not authenticated
    """
    logger.debug("router_list_mods_start")
    mods = service.list_mods()
    pending_restart = service.restart_state.pending_restart
    logger.debug("router_list_mods_complete", mod_count=len(mods), pending_restart=pending_restart)

    return ApiResponse(
        status="ok",
        data={
            "mods": [m.model_dump(mode="json") for m in mods],
            "pending_restart": pending_restart,
        },
    )


def _mod_updates_payload(service: ModUpdateService) -> dict[str, Any]:
    items = service.get_status()
    last_check = service.store.last_full_check
    return {
        "game_version": service.game_version() or None,
        "checked_at": last_check.isoformat().replace("+00:00", "Z") if last_check else None,
        "update_count": sum(1 for item in items if item.status == "update_available"),
        "mods": [item.model_dump(mode="json") for item in items],
    }


@router.get("/updates", response_model=ApiResponse, summary="Get mod update status")
async def get_mod_updates(
    _: RequireAuth,
    service: ModUpdateService = Depends(get_mod_update_service),
) -> ApiResponse:
    """Get update status for every installed mod (Admin or Monitor).

    Status is computed from the last check's stored data against the installed game
    version; this endpoint makes no calls to the mod database.
    """
    return ApiResponse(status="ok", data=_mod_updates_payload(service))


@router.post("/updates/check", response_model=ApiResponse, summary="Check for mod updates")
async def check_mod_updates(
    _: RequireAdmin,
    service: ModUpdateService = Depends(get_mod_update_service),
) -> ApiResponse:
    """Refresh release data for installed mods from the mod database (Admin only).

    Lookups that fail keep the mod's previous data and are listed in `check.failed_slugs`.

    Raises:
        HTTPException: 409 if a check is already running.
    """
    try:
        summary = await service.check()
    except ModUpdateCheckInProgressError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_UPDATE_CHECK_IN_PROGRESS,
                "message": "A mod update check is already running",
            },
        ) from None
    data = _mod_updates_payload(service)
    data["check"] = {
        "checked": summary.checked,
        "failed": summary.failed,
        "failed_slugs": summary.failed_slugs,
    }
    return ApiResponse(status="ok", data=data)


@router.post(
    "/updates/apply-all", response_model=ApiResponse, summary="Apply all compatible mod updates"
)
async def apply_all_mod_updates(
    _: RequireAdmin,
    update_service: ModUpdateService = Depends(get_mod_update_service),
    mod_service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """Update every mod whose offered update is compatible, one at a time (Admin only).

    Not verified offers are skipped for individual review; a mod that fails does not stop
    the others. Each result is `updated`, `skipped` (with reasons) or `failed` (with error).
    Each completed change stores that mod's update record from its own lookup (Story 18.2).

    Raises:
        HTTPException: 409 if update all is already running.
    """
    try:
        summary = await update_service.apply_all(
            partial(mod_service.change_version, record_releases=update_service.record_releases)
        )
    except ModUpdateAllInProgressError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_UPDATE_ALL_IN_PROGRESS,
                "message": "Update all is already running",
            },
        ) from None
    return ApiResponse(status="ok", data=asdict(summary))


BrowseSide = Literal["client", "server", "both"]
BrowseType = Literal["mod", "externaltool", "other"]

_BROWSE_SIDES: dict[str, BrowseSide] = {"client": "client", "server": "server", "both": "both"}
_BROWSE_TYPES: dict[str, BrowseType] = {
    "mod": "mod",
    "externaltool": "externaltool",
    "other": "other",
}


def _browse_side(mod: ModDict) -> BrowseSide:
    """A normalized mod's side, lowercased; empty or unknown shows as "both"."""
    return _BROWSE_SIDES.get(mod["side"].lower(), "both")


def _browse_type(mod: ModDict) -> BrowseType:
    """A normalized mod's type, lowercased; empty or unknown shows as "mod"."""
    return _BROWSE_TYPES.get(mod["type"].lower(), "mod")


def _api_mod_to_browse_item(
    mod: ModDict, release_mod_ids: frozenset[int] | None = None
) -> ModBrowseItem:
    """Convert a normalized mod dict from the API to a ModBrowseItem.

    Args:
        mod: Mod dictionary from the VintageStory mod database API, normalized by
            `ModApiClient` (Story 17.1, Epic 17 ADR-1).
        release_mod_ids: The numeric mod IDs of the entries with a release tagged for the
            installed game version, or None when not known (Story 18.3). An item without
            a numeric mod ID (normalized to 0) cannot be matched and gets None.

    Returns:
        ModBrowseItem with normalized field names.
    """
    # Get slug from modidstrs[0] - this is what the /api/mod/{slug} endpoint expects
    # VSS-brs: urlalias differs from modidstrs for some mods, causing lookup failures
    modidstrs: list[str] = mod["modidstrs"]
    slug: str = modidstrs[0] if modidstrs else (str(mod["modid"]) if mod["modid"] else "unknown")

    return ModBrowseItem(
        slug=slug,
        # Every mod ID once, in listing order; the listing can hold empty strings
        mod_ids=list(dict.fromkeys(m for m in modidstrs if m)),
        # Kept separate from the slug for website URL construction
        urlalias=mod["urlalias"],
        asset_id=mod["assetid"],
        name=mod["name"],
        author=mod["author"],
        summary=mod["summary"],
        downloads=mod["downloads"],
        follows=mod["follows"],
        trending_points=mod["trendingpoints"],
        side=_browse_side(mod),
        mod_type=_browse_type(mod),
        # Only the page's items are checked, never the cached listing (Epic 19 ADR-12)
        logo_url=checked_url(mod["logo"], mod_image_url, slug=slug, field="logo_url"),
        tags=mod["tags"],
        last_released=mod["lastreleased"],
        has_release_for_game_version=(
            (mod["modid"] in release_mod_ids)
            if release_mod_ids is not None and mod["modid"]
            else None
        ),
    )


def _mods_busy_error(error: ModsBusyError) -> HTTPException:
    return HTTPException(
        status_code=409, detail={"code": ErrorCode.MODS_BUSY, "message": str(error)}
    )


@router.get(
    "/unused-files", response_model=ApiResponse, summary="List unused files in the mods folder"
)
async def list_unused_files(
    _: RequireAdmin,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """List the files in the mods folder that the manager does not use (Admin only).

    Story 24.5 (Epic 24 ADR-3): `.tmp` and `.bak` leftovers, archives without a readable
    modinfo.json, and archives of a mod ID installed under another file. `.cs` files,
    folders and mods' own files are never listed.
    """
    files = service.list_unused_files()
    return ApiResponse(
        status="ok", data={"files": [item.model_dump(mode="json") for item in files]}
    )


@router.delete("/unused-files/{name}", response_model=ApiResponse, summary="Delete an unused file")
async def delete_unused_file(
    name: Annotated[str, Path(min_length=1, max_length=255, description="File name")],
    _: RequireAdmin,
    service: ModService = Depends(get_mod_service),
    update_service: ModUpdateService = Depends(get_mod_update_service),
) -> ApiResponse:
    """Delete one file of the unused-file listing (Admin only, Story 24.5).

    Only a file in the listing computed for this request can be deleted.

    Raises:
        HTTPException: 404 UNUSED_FILE_NOT_FOUND if the name is not in the listing.
        HTTPException: 409 MODS_BUSY while an install, version change, update all or
            update check runs (Epic 24 ADR-4).
        HTTPException: 500 UNUSED_FILE_DELETE_FAILED if the file could not be deleted.
    """
    try:
        result = service.delete_unused_file(name, other_operation_running=update_service.is_running)
    except ModsBusyError as e:
        raise _mods_busy_error(e) from None
    except UnusedFileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"code": ErrorCode.UNUSED_FILE_NOT_FOUND, "message": str(e)},
        ) from None
    except UnusedFileDeleteFailedError as e:
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.UNUSED_FILE_DELETE_FAILED, "message": str(e)},
        ) from None
    return ApiResponse(status="ok", data=result.model_dump(mode="json"))


@router.post("/rescan", response_model=ApiResponse, summary="Rescan the mods folder")
async def rescan_mods(
    _: RequireAdmin,
    service: ModService = Depends(get_mod_service),
    update_service: ModUpdateService = Depends(get_mod_update_service),
) -> ApiResponse:
    """Pick up mods copied into the mods folder, and drop entries whose file is gone.

    Admin only (Story 24.5, Epic 24 ADR-4). Runs the start-up sync again. The handler is
    `async` with no `await`, so it runs on the event loop and nothing interleaves with it.

    Raises:
        HTTPException: 409 MODS_BUSY while an install, version change, update all or
            update check runs.
    """
    try:
        result = service.rescan(other_operation_running=update_service.is_running)
    except ModsBusyError as e:
        raise _mods_busy_error(e) from None
    return ApiResponse(status="ok", data=result.model_dump(mode="json"))


@router.get("/browse", response_model=ApiResponse, summary="Browse available mods")
async def browse_mods(
    _: RequireAuth,
    service: ModService = Depends(get_mod_service),
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)"),
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page (max 100)"),
    ] = 20,
    sort: Annotated[
        SortOption,
        Query(description="Sort order: downloads, trending, recent, or name"),
    ] = "recent",
    search: Annotated[
        str | None,
        Query(
            max_length=100,
            description="Search term to filter mods by name, author, summary, or tags",
        ),
    ] = None,
    version: Annotated[
        str | None,
        Query(
            max_length=20,
            pattern=r"^[0-9]+(\.[0-9]+)*(-[a-zA-Z0-9]+)?$",
            description="Filter mods by compatible game version (e.g., '1.21.3')",
        ),
    ] = None,
    side: Annotated[
        Literal["client", "server", "both"] | None,
        Query(description="Filter by mod side: 'client', 'server', or 'both'"),
    ] = None,
    mod_type: Annotated[
        Literal["mod", "externaltool", "other"] | None,
        Query(description="Filter by mod type: 'mod', 'externaltool', or 'other'"),
    ] = None,
    tags: Annotated[
        str | None,
        Query(
            max_length=500,
            description="Comma-separated list of tags to filter by (OR logic)",
        ),
    ] = None,
) -> ApiResponse:
    """Browse available mods from the VintageStory mod database.

    Returns a paginated list of all mods available for installation,
    sorted by the specified criteria. Supports filtering by search term,
    game version compatibility, mod side, mod type, and tags.

    All filters are applied server-side before pagination, ensuring
    accurate counts and consistent results across pages.

    Both Admin and Monitor roles can access this read-only endpoint.

    Args:
        page: Page number (1-indexed, default 1).
        page_size: Number of items per page (1-100, default 20).
        sort: Sort order - "downloads", "trending", "recent" (default), or "name".
        search: Optional search term to filter by name, author, summary, or tags.
        version: Optional game version to filter by compatibility (e.g., "1.21.3").
        side: Optional filter by mod side ('client', 'server', or 'both').
        mod_type: Optional filter by mod type ('mod', 'externaltool', or 'other').
        tags: Optional comma-separated tags to filter by (OR logic within tags).

    Returns:
        ApiResponse with ModBrowseResponse containing:
        - mods: List of mod items for the current page; `logo_url` is null unless it is
          an https URL on the mod database CDN (Story 19.6); each with
          `has_release_for_game_version`: whether the entry has a release tagged for
          exactly the installed game version (Story 18.3), or null when not known
        - pagination: Pagination metadata with total counts
        - game_version: The installed game version those flags refer to, or null when
          the flags are null

        The flags come from the mod database's listing filtered by the installed
        version, cached for 5 minutes. A failed or slow flag lookup never fails the
        request: the flags are then from the last copy, or null.

    Raises:
        HTTPException: 400 if pagination parameters are invalid
        HTTPException: 400 if game version is not found
        HTTPException: 401 if not authenticated
        HTTPException: 502 if mod database API is unavailable
    """
    logger.debug(
        "router_browse_mods_start",
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
        version=version,
        side=side,
        mod_type=mod_type,
        tags=tags,
    )

    # The version the cards' flags refer to (Story 18.3); None when no server is installed.
    # Read on every request, so another installed version is used at once (another tag).
    # A version file that cannot be read leaves the flags null; browse still answers.
    try:
        installed_version = service.game_version()
    except OSError as e:
        logger.warning("browse_game_version_unreadable", error=str(e))
        installed_version = None
    game_version = (installed_version or "").lstrip("vV") or None

    try:
        # Get mods - either filtered by version or all (both cached)
        if version:
            # Look up the version tagid
            game_versions = await service.api_client.get_game_versions()
            version_tagid = game_versions.get(version)
            if version_tagid is None:
                raise GameVersionNotFoundError(version)

            # Mods filtered by version (server-side filtering)
            listing = service.api_client.get_mods_by_version(version_tagid)
        else:
            listing = service.api_client.get_all_mods()

        # The flag lookup runs alongside the listing; it is bounded and never raises
        release_mod_ids: frozenset[int] | None = None
        if game_version is None:
            all_mods = await listing
        else:
            all_mods, release_mod_ids = await asyncio.gather(
                listing, service.api_client.get_version_mod_ids(game_version)
            )

        # Filter by search term if provided
        filtered_mods = search_mods(all_mods, search or "")

        # Filter by side if provided (the card uses the same helper, so they agree)
        if side:
            filtered_mods = [m for m in filtered_mods if _browse_side(m) == side]

        # Filter by mod_type if provided
        if mod_type:
            filtered_mods = [m for m in filtered_mods if _browse_type(m) == mod_type]

        # Filter by tags if provided (OR logic - mod must have at least one matching tag)
        if tags:
            tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
            if tag_list:
                filtered_mods = [
                    m for m in filtered_mods if any(t.lower() in tag_list for t in m["tags"])
                ]

        # Sort mods
        sorted_mods = sort_mods(filtered_mods, sort_by=sort)

        # Calculate pagination
        total_items = len(sorted_mods)
        total_pages = max(1, math.ceil(total_items / page_size))

        # Clamp page to valid range
        actual_page = min(page, total_pages) if total_pages > 0 else 1

        # Calculate slice indices
        start_idx = (actual_page - 1) * page_size
        end_idx = start_idx + page_size

        # Get page slice and convert to models
        page_mods = sorted_mods[start_idx:end_idx]
        browse_items = [_api_mod_to_browse_item(mod, release_mod_ids) for mod in page_mods]

        # Build pagination metadata
        pagination = PaginationMeta(
            page=actual_page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=actual_page < total_pages,
            has_prev=actual_page > 1,
        )

        response = ModBrowseResponse(
            mods=browse_items,
            pagination=pagination,
            game_version=game_version if release_mod_ids is not None else None,
        )

        logger.debug(
            "router_browse_mods_complete",
            page=actual_page,
            page_size=page_size,
            total_items=total_items,
            items_returned=len(browse_items),
        )

        return ApiResponse(
            status="ok",
            data=response.model_dump(mode="json"),
        )

    except GameVersionNotFoundError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.GAME_VERSION_NOT_FOUND,
                "message": f"Game version '{e.version}' not found",
            },
        )

    except ExternalApiError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": ErrorCode.EXTERNAL_API_ERROR,
                "message": str(e),
            },
        )


@router.get("/gameversions", response_model=ApiResponse, summary="List game versions")
async def list_game_versions(
    _: RequireAuth,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """List available game versions for mod filtering.

    Returns a list of game version strings that can be used to filter
    mods by compatibility. Versions are sorted newest to oldest.

    Both Admin and Monitor roles can access this read-only endpoint.

    Returns:
        ApiResponse with data containing:
        - versions: Array of game version strings (e.g., ["1.21.3", "1.21.0", ...])

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 502 if mod database API is unavailable
    """
    logger.debug("router_list_game_versions_start")

    try:
        # Get version -> tagid mapping from API
        game_versions = await service.api_client.get_game_versions()

        # Extract version strings and sort newest first (semantic version sort)
        # Handles non-numeric parts like "1.21.3-rc1" by splitting on both . and -
        # and preserving non-numeric suffixes in sort order
        def parse_version(v: str) -> list[tuple[int, str]]:
            """Parse version into sortable tuples.

            Each part becomes (numeric_value, suffix_string).
            "1.21.3-rc1" -> [(1, ""), (21, ""), (3, ""), (-1, "rc1")]
            Non-numeric parts get -1 for numeric so they sort before numeric parts.
            """
            import re

            parts = re.split(r"[.\-]", v)
            result: list[tuple[int, str]] = []
            for part in parts:
                if part.isdigit():
                    result.append((int(part), ""))
                else:
                    # Extract leading digits if any, then suffix
                    match = re.match(r"^(\d*)(.*)$", part)
                    if match and match.group(1):
                        result.append((int(match.group(1)), match.group(2)))
                    else:
                        # Pure non-numeric (like "rc1") - sort before numbers
                        result.append((-1, part))
            return result

        versions = sorted(
            game_versions.keys(),
            key=parse_version,
            reverse=True,
        )

        logger.debug("router_list_game_versions_complete", version_count=len(versions))

        return ApiResponse(
            status="ok",
            data={"versions": versions},
        )

    except ExternalApiError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": ErrorCode.EXTERNAL_API_ERROR,
                "message": str(e),
            },
        )


@router.get("/tags", response_model=ApiResponse, summary="List available mod tags")
async def list_mod_tags(
    _: RequireAuth,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """List all unique tags across all mods.

    Returns a sorted list of tags that can be used for filtering mods.
    Tags are extracted from all mods in the database and deduplicated.

    Both Admin and Monitor roles can access this read-only endpoint.

    Returns:
        ApiResponse with data containing:
        - tags: Array of unique tag strings, sorted alphabetically

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 502 if mod database API is unavailable
    """
    logger.debug("router_list_mod_tags_start")

    try:
        # Get all mods from API (cached)
        all_mods = await service.api_client.get_all_mods()

        # Extract unique tags
        tag_set: set[str] = set()
        for mod in all_mods:
            for tag in mod["tags"]:
                tag_set.add(tag.lower())

        # Sort alphabetically
        tags = sorted(tag_set)

        logger.debug("router_list_mod_tags_complete", tag_count=len(tags))

        return ApiResponse(
            status="ok",
            data={"tags": tags},
        )

    except ExternalApiError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": ErrorCode.EXTERNAL_API_ERROR,
                "message": str(e),
            },
        )


@router.get("/lookup/{slug:path}", response_model=ApiResponse)
async def lookup_mod(
    slug: Annotated[
        str,
        Path(
            description="Mod slug (e.g., 'smithingplus') or full URL "
            "(e.g., 'https://mods.vintagestory.at/smithingplus')",
            min_length=1,
            max_length=200,
        ),
    ],
    _: RequireAuth,
    version: Annotated[
        str | None,
        Query(
            description="Release version to evaluate compatibility for (e.g., the "
            "installed version). Defaults to the newest release of the mod ID.",
            min_length=1,
            max_length=100,
        ),
    ] = None,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """Look up mod details and compatibility from the VintageStory mod database.

    Fetches mod information from mods.vintagestory.at and checks compatibility
    with the current game server version. Both Admin and Monitor roles can
    access this read-only endpoint.

    Compatibility is reported for one mod ID of the entry: the installed one when
    any of the entry's mod IDs is installed, otherwise the install mod ID (Epic 16
    ADR-2, Epic 17 ADR-2 decision 6).

    Args:
        slug: Mod slug or full URL to look up.
        version: Optional release version to evaluate (the Installed list passes
            the installed version); defaults to the mod ID's newest release.

    Returns:
        ApiResponse with ModLookupResponse containing:
        - slug: Mod identifier
        - name: Display name
        - author: Mod author
        - description: Mod description (may be null)
        - latest_version: The version an install without a named version picks for
          install_mod_id (its newest stable release with a downloadable file); null
          when none of its releases has a file
        - install_mod_id: The mod ID an install of this slug installs (the slug when
          a release carries it, otherwise the newest release's mod ID)
        - downloads: Total download count
        - side: "Both", "Client", or "Server"
        - compatibility: Nested object with status, game_version, mod_version, message,
          latest_supported_game_version
        - screenshots: List of {image_url, thumbnail_url, filename} in mod database
          order; only https URLs on the mod database CDN; [] when there are none
        - trailer_url: https://www.youtube-nocookie.com/embed/<id> for the entry's trailer,
          or null
        - logo_url: The mod's logo, only an https URL on the mod database CDN; otherwise
          null
        - homepage_url: The author's homepage when it is a well-formed https URL of at
          most 2,048 characters with a host and no user info; otherwise null (an empty
          value is null)
        - source_url: The source code URL, under the same rule as homepage_url

    Raises:
        HTTPException: 400 if slug format is invalid
        HTTPException: 404 if mod not found in database
        HTTPException: 502 if mod database API is unavailable
    """
    logger.debug("router_lookup_mod_start", slug=slug, version=version)
    try:
        result = await service.lookup_mod(slug, version)
        logger.debug("router_lookup_mod_complete", slug=slug, name=result.name)

        return ApiResponse(
            status="ok",
            data=result.model_dump(mode="json"),
        )

    except InvalidSlugError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.INVALID_SLUG,
                "message": f"Invalid mod slug format: '{e.slug}'",
            },
        )

    except ModNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.MOD_NOT_FOUND,
                "message": f"Mod '{e.slug}' not found in mod database",
            },
        )

    except ExternalApiError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": ErrorCode.EXTERNAL_API_ERROR,
                "message": str(e),
            },
        )


class ModInstallRequest(BaseModel):
    """Request body for mod installation."""

    slug: str = Field(
        ...,
        description="Mod slug (e.g., 'smithingplus') or full URL "
        "(e.g., 'https://mods.vintagestory.at/smithingplus')",
        min_length=1,
        max_length=200,
    )
    version: str | None = Field(
        default=None,
        description="Specific version to install (e.g., '1.8.3'). "
        "If not specified, installs the newest stable release of the mod ID that has a "
        "downloadable file.",
    )


@router.post("", response_model=ApiResponse)
async def install_mod(
    request: ModInstallRequest,
    _: RequireAdmin,
    service: ModService = Depends(get_mod_service),
    update_service: ModUpdateService = Depends(get_mod_update_service),
) -> ApiResponse:
    """Install a mod from the VintageStory mod database.

    Downloads and installs a mod by slug or URL. If version is not specified,
    installs the newest stable release of the mod ID that has a downloadable file
    (Epic 17 ADR-2). Returns compatibility status with the
    installed game version. The new mod's update status is stored from the install's
    own lookup, so it shows without waiting for the next update check (Story 17.4).

    Args:
        request: Installation request with slug and optional version.

    Returns:
        ApiResponse with installation result including:
        - slug: Installed mod identifier
        - version: Installed version
        - filename: Name of the installed mod file
        - compatibility: "compatible", "not_verified", or "incompatible"
        - pending_restart: Whether server restart is required

    Raises:
        HTTPException: 404 if mod not found in database
        HTTPException: 404 if specific version not found
        HTTPException: 409 if mod is already installed
        HTTPException: 409 if a file with the download's name (or its .disabled form) is
            already in the mods directory or the mod state, ignoring letter case
        HTTPException: 409 if another operation on this mod is in progress
        HTTPException: 422 if the release to install has no downloadable file
        HTTPException: 502 if mod database API is unavailable
        HTTPException: 502 if download fails
    """
    logger.debug("router_install_mod_start", slug=request.slug, version=request.version)
    try:
        result = await service.install_mod(request.slug, request.version)
        # Never raises; a failure is logged and the install still succeeds
        update_service.record_install(result.slug, result.releases)
        logger.debug(
            "router_install_mod_complete",
            slug=result.slug,
            version=result.version,
            compatibility=result.compatibility,
        )

        return ApiResponse(
            status="ok",
            data={
                "slug": result.slug,
                "version": result.version,
                "filename": result.filename,
                "compatibility": result.compatibility,
                "pending_restart": result.pending_restart,
            },
        )

    except ModFileConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_FILE_CONFLICT,
                "message": str(e),
            },
        )

    except ModAlreadyInstalledError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_ALREADY_INSTALLED,
                "message": f"Mod '{e.slug}' is already installed (version {e.current_version})",
            },
        )

    except ModOperationInProgressError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_OPERATION_IN_PROGRESS,
                "message": str(e),
            },
        )

    except ApiModNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.MOD_NOT_FOUND,
                "message": f"Mod '{e.slug}' not found in mod database",
            },
        )

    except ModVersionNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.MOD_VERSION_NOT_FOUND,
                "message": f"Version '{e.version}' not found for mod '{e.slug}'",
            },
        )

    except ModReleaseNotDownloadableError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "code": ErrorCode.MOD_RELEASE_NOT_DOWNLOADABLE,
                "message": str(e),
            },
        )

    except ExternalApiError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": ErrorCode.EXTERNAL_API_ERROR,
                "message": str(e),
            },
        )

    except DownloadError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": ErrorCode.DOWNLOAD_FAILED,
                "message": str(e),
            },
        )


def archive_install_response(result: ArchiveInstallResult) -> ApiResponse:
    """The answer of a file install (Epic 28 ADR-4 decision 5)."""
    return ApiResponse(
        status="ok",
        data={
            "slug": result.slug,
            "version": result.version,
            "filename": result.filename,
            "compatibility": result.compatibility,
            "pending_restart": result.pending_restart,
            "source": result.source,
            "replaced": result.replaced,
            "previous_version": result.previous_version,
        },
    )


def archive_install_error(error: Exception) -> HTTPException:
    """Map an `install_archive` error to its answer (Epic 28 ADR-3, ADR-4)."""
    if isinstance(error, ModFileInvalidError):
        return HTTPException(
            status_code=422, detail={"code": ErrorCode.MOD_FILE_INVALID, "message": str(error)}
        )
    if isinstance(error, ModFileTooLargeError):
        return HTTPException(
            status_code=413, detail={"code": ErrorCode.MOD_FILE_TOO_LARGE, "message": str(error)}
        )
    if isinstance(error, (ModUrlInvalidError, AddressBlockedError)):
        code = (
            ErrorCode.MOD_URL_INVALID
            if isinstance(error, ModUrlInvalidError)
            else ErrorCode.MOD_URL_BLOCKED
        )
        return HTTPException(status_code=422, detail={"code": code, "message": str(error)})
    if isinstance(error, LinkDownloadError):
        return HTTPException(
            status_code=502, detail={"code": ErrorCode.DOWNLOAD_FAILED, "message": str(error)}
        )
    if isinstance(error, ModAlreadyInstalledError):
        return HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_ALREADY_INSTALLED,
                "message": f"Mod '{error.slug}' is already installed "
                f"(version {error.current_version})",
                "slug": error.slug,
                "installed_version": error.current_version,
                "source": error.source,
            },
        )
    if isinstance(error, ModOperationInProgressError):
        code = ErrorCode.MOD_OPERATION_IN_PROGRESS
    elif isinstance(error, ModFileConflictError):
        code = ErrorCode.MOD_FILE_CONFLICT
    elif isinstance(error, ModFileMissingError):
        code = ErrorCode.MOD_FILE_MISSING
    elif isinstance(error, ModVersionChangeFailedError):
        return HTTPException(
            status_code=500,
            detail={"code": ErrorCode.MOD_VERSION_CHANGE_FAILED, "message": str(error)},
        )
    else:
        raise error
    return HTTPException(status_code=409, detail={"code": code, "message": str(error)})


def file_write_error(error: OSError) -> HTTPException:
    """A full disk or an unwritable folder while receiving or placing the file; the
    working folder and any placed file are already removed (Story 28.2 review)."""
    return HTTPException(
        status_code=500,
        detail={
            "code": ErrorCode.MOD_FILE_WRITE_FAILED,
            "message": f"The file could not be written: {error.strerror or error}",
        },
    )


ARCHIVE_INSTALL_ERRORS = (
    ModUrlInvalidError,
    AddressBlockedError,
    LinkDownloadError,
    ModFileInvalidError,
    ModFileTooLargeError,
    ModAlreadyInstalledError,
    ModOperationInProgressError,
    ModFileConflictError,
    ModFileMissingError,
    ModVersionChangeFailedError,
)


@router.post("/upload", response_model=ApiResponse, summary="Install a mod by uploading its file")
async def upload_mod(
    request: Request,
    filename: Annotated[
        str,
        Query(
            min_length=1,
            max_length=255,
            description="The file's name: a base name ending in lowercase .zip, kept as "
            "the mod's file",
        ),
    ],
    _: RequireAdmin,
    replace: Annotated[
        bool, Query(description="Replace the installed mod with the same mod ID")
    ] = False,
    settings: Settings = Depends(get_settings),
    service: ModService = Depends(get_mod_service),
    update_service: ModUpdateService = Depends(get_mod_update_service),
) -> ApiResponse:
    """Install a mod from the request body, a zip file (Admin only, Story 28.2).

    The body is the file itself (`application/zip` or `application/octet-stream`), not a
    form. It is written to a working file with the size limit counted while reading
    (VS_MOD_UPLOAD_MAX_MB), then checked and installed with source `upload` (Epic 28
    ADR-3, ADR-4). The mod database is never asked about it.

    Raises:
        HTTPException: 413 MOD_FILE_TOO_LARGE over the limit, by Content-Length or read.
        HTTPException: 422 MOD_FILE_INVALID for an unsafe name, a body that is not a zip,
            or no modinfo.json with a mod ID, a name and a version.
        HTTPException: 409 MOD_ALREADY_INSTALLED (with `installed_version` and `source`)
            when the mod ID is installed and `replace` is not set.
        HTTPException: 409 MOD_OPERATION_IN_PROGRESS, MOD_FILE_CONFLICT or
            MOD_FILE_MISSING, as for an install or a version change.
        HTTPException: 500 MOD_VERSION_CHANGE_FAILED when a replace failed; the original
            file and state are restored.
        HTTPException: 500 MOD_FILE_WRITE_FAILED when the file could not be written (for
            example a full disk); nothing is left behind.
    """
    limit_bytes = settings.mod_upload_max_mb * 1024 * 1024
    try:
        name = safe_archive_name(filename)
        if name is None:
            raise ModFileInvalidError(
                "The file name must be a plain name ending in .zip (lowercase), with no "
                "folder, at most 255 bytes, and must not start with a dot."
            )
        declared = request.headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit_bytes:
            raise ModFileTooLargeError(limit_bytes)
        with incoming_file(service.cache_dir, name) as path:
            await write_limited(request.stream(), path, limit_bytes)
            result = service.install_archive(path, source="upload", replace=replace)
    except ARCHIVE_INSTALL_ERRORS as e:
        logger.info("mod_upload_refused", filename=filename, error_type=type(e).__name__)
        raise archive_install_error(e) from None
    except OSError as e:
        logger.error("mod_upload_write_failed", filename=filename, error=str(e))
        raise file_write_error(e) from None
    if result.replaced:
        update_service.forget(result.slug)
    return archive_install_response(result)


class ModLinkInstallRequest(BaseModel):
    """Request body for POST /mods/install-from-url (Story 28.3)."""

    url: str = Field(min_length=1, max_length=4096, description="An https link to a mod zip")
    replace: bool = Field(
        default=False, description="Replace the installed mod with the same mod ID"
    )


def get_link_transport() -> httpx.AsyncBaseTransport | None:
    """The transport for link downloads; None is the guarded one (tests override it)."""
    return None


@router.post(
    "/install-from-url", response_model=ApiResponse, summary="Install a mod from an HTTPS link"
)
async def install_mod_from_url(
    body: ModLinkInstallRequest,
    _: RequireAdmin,
    settings: Settings = Depends(get_settings),
    service: ModService = Depends(get_mod_service),
    update_service: ModUpdateService = Depends(get_mod_update_service),
    transport: httpx.AsyncBaseTransport | None = Depends(get_link_transport),
) -> ApiResponse:
    """Download a mod's zip from a link and install it (Admin only, Story 28.3).

    The link must be https (plain http only with VS_DEBUG=true) without a user name or
    password. Every connection, including after a redirect (at most five), is refused
    when its host resolves to a private, loopback, link-local or other internal address,
    except private addresses of hosts in VS_MOD_URL_PRIVATE_HOSTS (Epic 28 ADR-5). Proxy
    settings are not used. The file is named from Content-Disposition, else the link's
    last path segment, else `{modid}_{version}.zip`, then checked and installed with
    source `url` as an upload is (ADR-4). The link is stored without its query string.

    Raises:
        HTTPException: 422 MOD_URL_INVALID for a link or redirect that is not https, has
            credentials, or redirects more than five times.
        HTTPException: 422 MOD_URL_BLOCKED for a host on an internal address.
        HTTPException: 502 DOWNLOAD_FAILED for an error answer, a timeout (connect 10 s,
            read 30 s, whole download 300 s) or a connection error.
        HTTPException: 413, 422, 409 and 500 as for POST /mods/upload.
    """
    limit_bytes = settings.mod_upload_max_mb * 1024 * 1024
    try:
        async with downloaded(
            body.url,
            cache_dir=service.cache_dir,
            limit_bytes=limit_bytes,
            allow_http=settings.debug,
            transport=transport,
            private_hosts=parse_private_hosts(settings.mod_url_private_hosts),
        ) as (path, named):
            if not named:
                metadata = service.state_manager.read_modinfo(path)
                if metadata is not None:
                    # A unique name when the mod ID and version give none (review)
                    name = name_from_modinfo(metadata.modid, metadata.version)
                    path = path.rename(path.with_name(name or f"mod_{uuid.uuid4().hex[:8]}.zip"))
            result = service.install_archive(
                path,
                source="url",
                source_url=stored_link(check_link(body.url, allow_http=settings.debug)),
                replace=body.replace,
            )
    except ARCHIVE_INSTALL_ERRORS as e:
        logger.info(
            "mod_link_install_refused",
            link=_loggable_link(body.url),
            error_type=type(e).__name__,
            error=str(e),
        )
        raise archive_install_error(e) from None
    except OSError as e:
        logger.error("mod_link_write_failed", link=_loggable_link(body.url), error=str(e))
        raise file_write_error(e) from None
    if result.replaced:
        update_service.forget(result.slug)
    return archive_install_response(result)


def _loggable_link(url: str) -> str:
    """The link for a log line: never its user info, query string or fragment, which may
    hold a password or a signature (Story 28.3 review)."""
    try:
        parsed = httpx.URL(url)
        return str(parsed.copy_with(userinfo=b"", query=None, fragment=None))
    except httpx.InvalidURL, TypeError, ValueError:
        return "<unparsable link>"


@router.post("/{slug}/enable", response_model=ApiResponse)
async def enable_mod(
    slug: Annotated[
        str,
        Path(
            description="Mod slug (modid) to enable",
            min_length=1,
            max_length=100,
        ),
    ],
    _: RequireAdmin,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """Enable a disabled mod.

    Renames the mod file from .zip.disabled to .zip and updates state.
    Sets pending_restart if the server is currently running.

    This operation is idempotent - enabling an already-enabled mod returns
    success without making changes.

    Args:
        slug: The mod slug (modid) to enable.

    Returns:
        ApiResponse with EnableResult containing:
        - slug: The mod slug that was enabled
        - enabled: Whether the mod is now enabled (always True)
        - pending_restart: Whether server restart is required

    Raises:
        HTTPException: 403 if user is not Admin
        HTTPException: 404 if mod is not installed
        HTTPException: 409 if another operation on this mod is in progress
        HTTPException: 409 if the name the file would be renamed to is taken in the mods
            directory or the mod state (MOD_FILE_CONFLICT)
        HTTPException: 409 if the mod's own file is no longer in the mods directory
            (MOD_FILE_MISSING)
    """
    # Defense-in-depth: validate slug format before state lookup
    if not validate_slug(slug):
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.INVALID_SLUG,
                "message": f"Invalid mod slug: {slug}",
            },
        )

    logger.debug("router_enable_mod_start", slug=slug)
    try:
        result = service.enable_mod(slug)
        logger.debug(
            "router_enable_mod_complete", slug=slug, pending_restart=result.pending_restart
        )

        return ApiResponse(
            status="ok",
            data=result.model_dump(mode="json"),
        )

    except ModNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.MOD_NOT_INSTALLED,
                "message": f"Mod '{e.slug}' is not installed",
            },
        )

    except ModOperationInProgressError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_OPERATION_IN_PROGRESS,
                "message": str(e),
            },
        )

    except ModFileConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_FILE_CONFLICT,
                "message": str(e),
            },
        )

    except ModFileMissingError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_FILE_MISSING,
                "message": str(e),
            },
        )


@router.post("/{slug}/disable", response_model=ApiResponse)
async def disable_mod(
    slug: Annotated[
        str,
        Path(
            description="Mod slug (modid) to disable",
            min_length=1,
            max_length=100,
        ),
    ],
    _: RequireAdmin,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """Disable an enabled mod.

    Renames the mod file from .zip to .zip.disabled and updates state.
    Sets pending_restart if the server is currently running.

    This operation is idempotent - disabling an already-disabled mod returns
    success without making changes.

    Args:
        slug: The mod slug (modid) to disable.

    Returns:
        ApiResponse with DisableResult containing:
        - slug: The mod slug that was disabled
        - enabled: Whether the mod is now enabled (always False)
        - pending_restart: Whether server restart is required

    Raises:
        HTTPException: 403 if user is not Admin
        HTTPException: 404 if mod is not installed
        HTTPException: 409 if another operation on this mod is in progress
        HTTPException: 409 if the name the file would be renamed to is taken in the mods
            directory or the mod state (MOD_FILE_CONFLICT)
        HTTPException: 409 if the mod's own file is no longer in the mods directory
            (MOD_FILE_MISSING)
    """
    # Defense-in-depth: validate slug format before state lookup
    if not validate_slug(slug):
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.INVALID_SLUG,
                "message": f"Invalid mod slug: {slug}",
            },
        )

    logger.debug("router_disable_mod_start", slug=slug)
    try:
        result = service.disable_mod(slug)
        logger.debug(
            "router_disable_mod_complete", slug=slug, pending_restart=result.pending_restart
        )

        return ApiResponse(
            status="ok",
            data=result.model_dump(mode="json"),
        )

    except ModNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.MOD_NOT_INSTALLED,
                "message": f"Mod '{e.slug}' is not installed",
            },
        )

    except ModOperationInProgressError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_OPERATION_IN_PROGRESS,
                "message": str(e),
            },
        )

    except ModFileConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_FILE_CONFLICT,
                "message": str(e),
            },
        )

    except ModFileMissingError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_FILE_MISSING,
                "message": str(e),
            },
        )


@router.delete("/{slug}", response_model=ApiResponse)
async def remove_mod(
    slug: Annotated[
        str,
        Path(
            description="Mod slug (modid) to remove",
            min_length=1,
            max_length=100,
        ),
    ],
    _: RequireAdmin,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """Remove an installed mod.

    Deletes the mod file from disk, removes it from state, and cleans up
    cached metadata. Sets pending_restart if the server is currently running.

    Args:
        slug: The mod slug (modid) to remove.

    Returns:
        ApiResponse with RemoveResult containing:
        - slug: The mod slug that was removed
        - pending_restart: Whether server restart is required

    Raises:
        HTTPException: 403 if user is not Admin
        HTTPException: 404 if mod is not installed
        HTTPException: 409 if another operation on this mod is in progress
    """
    # Defense-in-depth: validate slug format before state lookup
    if not validate_slug(slug):
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.INVALID_SLUG,
                "message": f"Invalid mod slug: {slug}",
            },
        )

    logger.debug("router_remove_mod_start", slug=slug)
    try:
        result = service.remove_mod(slug)
        logger.debug(
            "router_remove_mod_complete", slug=slug, pending_restart=result.pending_restart
        )

        return ApiResponse(
            status="ok",
            data=result.model_dump(mode="json"),
        )

    except ModNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.MOD_NOT_INSTALLED,
                "message": f"Mod '{e.slug}' is not installed",
            },
        )

    except ModOperationInProgressError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_OPERATION_IN_PROGRESS,
                "message": str(e),
            },
        )


class ModVersionChangeRequest(BaseModel):
    """Request body for changing an installed mod's version."""

    version: str = Field(..., min_length=1, description="Release version to install")
    confirm: bool = Field(
        default=False,
        description="Confirm a not-verified, incompatible, pre-release or older release",
    )


def _version_change_error(
    status_code: int, code: str, error: Exception, **details: Any
) -> HTTPException:
    detail: dict[str, Any] = {"code": code, "message": str(error)}
    if details:
        detail["details"] = details
    return HTTPException(status_code=status_code, detail=detail)


async def _update_release_mod(
    installed: ModInfo,
    request: ModVersionChangeRequest,
    settings: Settings,
    service: ModService,
    update_service: ModUpdateService,
    transport: httpx.AsyncBaseTransport | None,
) -> ApiResponse:
    """Install a release mod's offered release (Story 28.5, ADR-7 decision 6).

    The mod's lock is held only while the file is placed (`install_archive`), not during
    the download, as for a link install: a remove during a slow download is not refused,
    and the finished update installs the mod again. The admin who removed it can remove
    it again.
    """
    slug = installed.slug
    if request.version == installed.version:
        return ApiResponse(
            status="ok",
            data={
                "slug": slug,
                "previous_version": installed.version,
                "version": installed.version,
                "filename": installed.filename,
                "compatibility": None,
                "changed": False,
                "pending_restart": False,
            },
        )
    record = update_service.store.get(slug)
    offer = record.releases[0] if record is not None and record.releases else None
    if offer is None or offer.modversion != request.version or not offer.download_url:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.MOD_VERSION_NOT_FOUND,
                "message": f"Version '{request.version}' is not the latest release of "
                f"'{slug}' as last checked. Check for updates first.",
            },
        )
    if not request.confirm:
        # Never verified against the game version, as any not-verified release
        confirmation = ModConfirmationRequiredError(
            slug, request.version, ["not_verified"], "not_verified"
        )
        raise _version_change_error(
            409,
            ErrorCode.MOD_CONFIRMATION_REQUIRED,
            confirmation,
            reasons=confirmation.reasons,
            compatibility=confirmation.compatibility,
        )
    try:
        async with downloaded(
            offer.download_url,
            cache_dir=service.cache_dir,
            limit_bytes=settings.mod_upload_max_mb * 1024 * 1024,
            allow_http=settings.debug,
            transport=transport,
            private_hosts=parse_private_hosts(settings.mod_url_private_hosts),
        ) as (path, named):
            if not named:
                metadata = service.state_manager.read_modinfo(path)
                if metadata is not None:
                    name = name_from_modinfo(metadata.modid, metadata.version)
                    path = path.rename(path.with_name(name or f"mod_{uuid.uuid4().hex[:8]}.zip"))
            result = service.install_archive(
                path,
                source="url",
                # The release link, not Forgejo's `/attachments/` URL (Story 28.5 review)
                source_url=offer.release_link
                or stored_link(check_link(offer.download_url, allow_http=settings.debug)),
                replace=True,
                expect_modid=slug,
            )
    except ARCHIVE_INSTALL_ERRORS as e:
        logger.info(
            "mod_release_update_refused", slug=slug, error_type=type(e).__name__, error=str(e)
        )
        raise archive_install_error(e) from None
    except OSError as e:
        logger.error("mod_release_update_write_failed", slug=slug, error=str(e))
        raise file_write_error(e) from None
    return ApiResponse(
        status="ok",
        data={
            "slug": result.slug,
            "previous_version": result.previous_version or installed.version,
            "version": result.version,
            "filename": result.filename,
            "compatibility": result.compatibility,
            "changed": True,
            "pending_restart": result.pending_restart,
        },
    )


@router.put("/{slug}/version", response_model=ApiResponse, summary="Change a mod's version")
async def change_mod_version(
    request: ModVersionChangeRequest,
    _: RequireAdmin,
    slug: str = Path(..., description="Installed mod's modid"),
    settings: Settings = Depends(get_settings),
    service: ModService = Depends(get_mod_service),
    update_service: ModUpdateService = Depends(get_mod_update_service),
    transport: httpx.AsyncBaseTransport | None = Depends(get_link_transport),
) -> ApiResponse:
    """Update or roll back an installed mod to a listed release (Admin only).

    A mod installed from a GitHub or Forgejo release link is updated to its latest
    release's matching asset, as the last update check found it (Story 28.5, ADR-7
    decision 6): only that version, confirmed (it is not verified), and only an archive
    of the same mod ID.

    The installed file is only replaced after the new release is validated; any
    failure leaves the mod unchanged. Returns 409 if another operation on this mod is
    in progress. A release file name, or its .disabled form, that is taken in the mods
    directory or the mod state (ignoring case) is 409 MOD_FILE_CONFLICT; a mod whose own
    file is gone is 409 MOD_FILE_MISSING, before any lookup (Story 24.3); an uploaded or
    linked mod is 409 MOD_NOT_FROM_DATABASE, before any lookup (Epic 28 ADR-2); 500
    MOD_VERSION_CHANGE_FAILED is for a failure to place the file or save state, rolled
    back. A completed change stores the mod's update record from its own lookup,
    so its update status shows without waiting for the next check (Story 18.2).
    """
    installed = service.get_mod(slug)
    if installed is not None and is_release_mod(installed):
        return await _update_release_mod(
            installed, request, settings, service, update_service, transport
        )
    try:
        result = await service.change_version(
            slug,
            request.version,
            confirm=request.confirm,
            record_releases=update_service.record_releases,
        )
    except ModNotFoundError as e:
        raise _version_change_error(404, ErrorCode.MOD_NOT_INSTALLED, e) from None
    except ApiModNotFoundError as e:
        raise _version_change_error(404, ErrorCode.MOD_NOT_FOUND, e) from None
    except ModVersionNotFoundError as e:
        raise _version_change_error(404, ErrorCode.MOD_VERSION_NOT_FOUND, e) from None
    except ModReleaseNotDownloadableError as e:
        raise _version_change_error(422, ErrorCode.MOD_RELEASE_NOT_DOWNLOADABLE, e) from None
    except ModConfirmationRequiredError as e:
        raise _version_change_error(
            409,
            ErrorCode.MOD_CONFIRMATION_REQUIRED,
            e,
            reasons=e.reasons,
            compatibility=e.compatibility,
        ) from None
    except ModOperationInProgressError as e:
        raise _version_change_error(409, ErrorCode.MOD_OPERATION_IN_PROGRESS, e) from None
    except ModValidationError as e:
        raise _version_change_error(422, ErrorCode.MOD_VALIDATION_FAILED, e) from None
    except ExternalApiError as e:
        raise _version_change_error(502, ErrorCode.EXTERNAL_API_ERROR, e) from None
    except DownloadError as e:
        raise _version_change_error(502, ErrorCode.DOWNLOAD_FAILED, e) from None
    except ModFileConflictError as e:
        raise _version_change_error(409, ErrorCode.MOD_FILE_CONFLICT, e) from None
    except ModFileMissingError as e:
        raise _version_change_error(409, ErrorCode.MOD_FILE_MISSING, e) from None
    except ModNotFromDatabaseError as e:
        raise _version_change_error(409, ErrorCode.MOD_NOT_FROM_DATABASE, e) from None
    except ModVersionChangeFailedError as e:
        raise _version_change_error(500, ErrorCode.MOD_VERSION_CHANGE_FAILED, e) from None
    return ApiResponse(status="ok", data=asdict(result))
