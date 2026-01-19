"""Mod management API endpoints."""

import math
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from vintagestory_api.middleware.auth import get_current_user
from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.mods import ModBrowseItem, ModBrowseResponse, PaginationMeta
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.services.mod_api import (
    DownloadError,
    ExternalApiError,
    GameVersionNotFoundError,
    ModDict,
    ModVersionNotFoundError,
    SortOption,
    search_mods,
    sort_mods,
    validate_slug,
)
from vintagestory_api.services.mod_api import (
    ModNotFoundError as ApiModNotFoundError,
)
from vintagestory_api.services.mods import (
    InvalidSlugError,
    ModAlreadyInstalledError,
    ModNotFoundError,
    ModService,
    get_mod_service,
)

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


def _api_mod_to_browse_item(mod: ModDict) -> ModBrowseItem:
    """Convert a mod dict from the API to a ModBrowseItem.

    Args:
        mod: Raw mod dictionary from VintageStory mod database API.

    Returns:
        ModBrowseItem with normalized field names.
    """
    # Get slug - prefer urlalias, fallback to first modidstrs
    slug = mod.get("urlalias")
    if not slug:
        modidstrs = mod.get("modidstrs", [])
        slug = modidstrs[0] if modidstrs else str(mod.get("modid", "unknown"))

    # Normalize side value to lowercase
    # Type narrowing: pyright can't infer that the `in` check guarantees side_raw
    # is one of the literal values. We've validated it's in the allowed set.
    side_raw = str(mod.get("side", "both")).lower()
    side: Literal["client", "server", "both"] = "both"
    if side_raw in ("client", "server", "both"):
        side = side_raw  # type: ignore[assignment]  # validated by `in` check above

    # Normalize type value
    # Type narrowing: pyright can't infer that the `in` check guarantees type_raw
    # is one of the literal values. We've validated it's in the allowed set.
    type_raw = str(mod.get("type", "mod")).lower()
    mod_type: Literal["mod", "externaltool", "other"] = "mod"
    if type_raw in ("mod", "externaltool", "other"):
        mod_type = type_raw  # type: ignore[assignment]  # validated by `in` check above

    return ModBrowseItem(
        slug=slug,
        name=str(mod.get("name", "")),
        author=str(mod.get("author", "")),
        summary=mod.get("summary"),
        downloads=int(mod.get("downloads", 0)),
        follows=int(mod.get("follows", 0)),
        trending_points=int(mod.get("trendingpoints", 0)),
        side=side,
        mod_type=mod_type,
        logo_url=mod.get("logo"),
        tags=mod.get("tags", []),
        last_released=mod.get("lastreleased"),
    )


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
            description="Filter mods by compatible game version (e.g., '1.21.3')",
        ),
    ] = None,
) -> ApiResponse:
    """Browse available mods from the VintageStory mod database.

    Returns a paginated list of all mods available for installation,
    sorted by the specified criteria. Optionally filter by search term
    and/or game version compatibility.

    Both Admin and Monitor roles can access this read-only endpoint.

    Args:
        page: Page number (1-indexed, default 1).
        page_size: Number of items per page (1-100, default 20).
        sort: Sort order - "downloads", "trending", "recent" (default), or "name".
        search: Optional search term to filter by name, author, summary, or tags.
        version: Optional game version to filter by compatibility (e.g., "1.21.3").

    Returns:
        ApiResponse with ModBrowseResponse containing:
        - mods: List of mod items for the current page
        - pagination: Pagination metadata with total counts

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
    )

    try:
        # Get mods - either filtered by version or all
        if version:
            # Look up the version tagid
            game_versions = await service.api_client.get_game_versions()
            version_tagid = game_versions.get(version)
            if version_tagid is None:
                raise GameVersionNotFoundError(version)

            # Fetch mods filtered by version (server-side filtering)
            all_mods = await service.api_client.get_mods_by_version(version_tagid)
        else:
            # Get all mods from API (cached)
            all_mods = await service.api_client.get_all_mods()

        # Filter by search term if provided
        filtered_mods = search_mods(all_mods, search or "")

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
        browse_items = [_api_mod_to_browse_item(mod) for mod in page_mods]

        # Build pagination metadata
        pagination = PaginationMeta(
            page=actual_page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=actual_page < total_pages,
            has_prev=actual_page > 1,
        )

        response = ModBrowseResponse(mods=browse_items, pagination=pagination)

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
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """Look up mod details and compatibility from the VintageStory mod database.

    Fetches mod information from mods.vintagestory.at and checks compatibility
    with the current game server version. Both Admin and Monitor roles can
    access this read-only endpoint.

    Args:
        slug: Mod slug or full URL to look up.

    Returns:
        ApiResponse with ModLookupResponse containing:
        - slug: Mod identifier
        - name: Display name
        - author: Mod author
        - description: Mod description (may be null)
        - latest_version: Latest release version
        - downloads: Total download count
        - side: "Both", "Client", or "Server"
        - compatibility: Nested object with status, game_version, mod_version, message

    Raises:
        HTTPException: 400 if slug format is invalid
        HTTPException: 404 if mod not found in database
        HTTPException: 502 if mod database API is unavailable
    """
    logger.debug("router_lookup_mod_start", slug=slug)
    try:
        result = await service.lookup_mod(slug)
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
        "If not specified, installs the latest version.",
    )


@router.post("", response_model=ApiResponse)
async def install_mod(
    request: ModInstallRequest,
    _: RequireAdmin,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """Install a mod from the VintageStory mod database.

    Downloads and installs a mod by slug or URL. If version is not specified,
    installs the latest version. Returns compatibility status with the
    installed game version.

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
        HTTPException: 502 if mod database API is unavailable
        HTTPException: 502 if download fails
    """
    logger.debug("router_install_mod_start", slug=request.slug, version=request.version)
    try:
        result = await service.install_mod(request.slug, request.version)
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

    except ModAlreadyInstalledError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.MOD_ALREADY_INSTALLED,
                "message": f"Mod '{e.slug}' is already installed (version {e.current_version})",
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
