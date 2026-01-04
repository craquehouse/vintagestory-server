"""Debug configuration endpoints (FR48).

Provides endpoints to view and toggle debug logging at runtime
without requiring server restart.

Security Note:
- All debug endpoints require admin authentication
- Debug state changes are logged for audit purposes
"""

import structlog
from fastapi import APIRouter

from vintagestory_api.config import is_debug_enabled, set_debug_enabled
from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.responses import ApiResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("", response_model=ApiResponse)
async def get_debug_status(_: RequireAdmin) -> ApiResponse:
    """Get current debug logging status.

    Returns:
        ApiResponse with current debug state.
    """
    return ApiResponse(
        status="ok",
        data={
            "debug_enabled": is_debug_enabled(),
        },
    )


@router.post("/enable", response_model=ApiResponse)
async def enable_debug_logging(_: RequireAdmin) -> ApiResponse:
    """Enable debug logging at runtime (FR48).

    Enables verbose DEBUG-level logging without requiring server restart.
    Changes take effect immediately for subsequent log entries.

    Returns:
        ApiResponse with updated debug state and whether change occurred.
    """
    changed = set_debug_enabled(True)
    logger.info("debug_logging_api_enable", changed=changed, new_state=True)
    return ApiResponse(
        status="ok",
        data={
            "debug_enabled": True,
            "changed": changed,
        },
    )


@router.post("/disable", response_model=ApiResponse)
async def disable_debug_logging(_: RequireAdmin) -> ApiResponse:
    """Disable debug logging at runtime (FR48).

    Disables verbose DEBUG-level logging without requiring server restart.
    Changes take effect immediately for subsequent log entries.

    Returns:
        ApiResponse with updated debug state and whether change occurred.
    """
    changed = set_debug_enabled(False)
    logger.info("debug_logging_api_disable", changed=changed, new_state=False)
    return ApiResponse(
        status="ok",
        data={
            "debug_enabled": False,
            "changed": changed,
        },
    )
