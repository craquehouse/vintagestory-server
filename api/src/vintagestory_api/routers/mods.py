"""Mod management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from vintagestory_api.middleware.auth import get_current_user
from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.services.mod_api import (
    DownloadError,
    ExternalApiError,
    ModVersionNotFoundError,
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

router = APIRouter(prefix="/mods", tags=["Mods"])


# Type alias for authenticated user (Admin or Monitor)
RequireAuth = Annotated[str, Depends(get_current_user)]


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
    try:
        result = await service.lookup_mod(slug)

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
    try:
        result = await service.install_mod(request.slug, request.version)

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
