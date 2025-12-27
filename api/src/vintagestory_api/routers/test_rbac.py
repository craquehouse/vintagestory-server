"""Test endpoints for RBAC validation.

These endpoints exist solely to validate role-based access control
during development and testing. They do not provide any real functionality.

TODO: Consider removing these endpoints before production release,
or gate them behind a DEBUG/TEST mode flag.
"""

from fastapi import APIRouter, Depends

from vintagestory_api.middleware.auth import CurrentUser
from vintagestory_api.middleware.permissions import require_admin, require_console_access
from vintagestory_api.models.responses import ApiResponse

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/read")
async def test_read(current_user: CurrentUser) -> ApiResponse:
    """Test read endpoint accessible by both Admin and Monitor roles.

    This endpoint verifies that authenticated users with any valid role
    can access read-only endpoints.
    """
    return ApiResponse(
        status="ok",
        data={"role": current_user, "operation": "read", "access": "granted"},
    )


@router.post("/write")
async def test_write(role: str = Depends(require_admin)) -> ApiResponse:
    """Test write endpoint accessible only by Admin role.

    This endpoint verifies that write operations (POST, PUT, DELETE)
    are restricted to Admin users only.

    Monitor role users will receive a 403 Forbidden response.
    """
    return ApiResponse(
        status="ok",
        data={"role": role, "operation": "write", "access": "granted"},
    )


@router.get("/console")
async def test_console(role: str = Depends(require_console_access)) -> ApiResponse:
    """Test console endpoint accessible only by Admin role.

    This endpoint simulates console access, which contains sensitive
    server data and should only be accessible to Admin users.

    Monitor role users will receive a 403 Forbidden response with
    a console-specific error message.
    """
    return ApiResponse(
        status="ok",
        data={"role": role, "operation": "console", "access": "granted"},
    )
