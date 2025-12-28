"""Console API endpoints for history and streaming."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from vintagestory_api.middleware.permissions import RequireConsoleAccess
from vintagestory_api.routers.server import get_server_service
from vintagestory_api.services.server import ServerService

router = APIRouter(prefix="/console", tags=["console"])


@router.get("/history")
async def get_console_history(
    _role: RequireConsoleAccess,
    lines: Annotated[int | None, Query(ge=1, le=10000, description="Max lines to return")] = None,
    service: ServerService = Depends(get_server_service),
) -> dict[str, object]:
    """Get console history from the buffer.

    Returns timestamped console output lines from the server's stdout/stderr.
    Oldest lines are returned first. Each line is prefixed with ISO 8601 timestamp.

    Requires Admin role (console access is restricted to administrators).

    Args:
        _role: Enforces Admin-only access via RequireConsoleAccess dependency.
        lines: Optional limit on number of lines to return (most recent N lines).
        service: ServerService containing the console buffer.

    Returns:
        API envelope with lines array and total count.
    """
    history = service.console_buffer.get_history(limit=lines)

    return {
        "status": "ok",
        "data": {
            "lines": history,
            "total": len(service.console_buffer),
            "limit": lines,
        },
    }
