"""Role-based permission dependencies for API endpoints."""

from typing import Annotated, Literal

from fastapi import Depends, HTTPException

from vintagestory_api.middleware.auth import UserRole, get_current_user
from vintagestory_api.models.errors import ErrorCode

# Type alias for allowed role values
RoleType = Literal["admin", "monitor"]


async def require_admin(
    current_role: str = Depends(get_current_user),
) -> str:
    """Require Admin role for the endpoint.

    Use this dependency for write operations (POST, PUT, DELETE) that
    should only be accessible to administrators.

    Args:
        current_role: The authenticated user's role from get_current_user

    Returns:
        The user's role (will always be ADMIN if this returns)

    Raises:
        HTTPException: 403 if the user is not an Admin
    """
    if current_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail={
                "code": ErrorCode.FORBIDDEN,
                "message": "Admin role required for this operation",
            },
        )
    return current_role


async def require_console_access(
    current_role: str = Depends(get_current_user),
) -> str:
    """Require Admin role for console access (sensitive data).

    Use this dependency for console-related endpoints that contain
    sensitive server data and commands.

    Args:
        current_role: The authenticated user's role from get_current_user

    Returns:
        The user's role (will always be ADMIN if this returns)

    Raises:
        HTTPException: 403 with console-specific error message
    """
    if current_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail={
                "code": ErrorCode.FORBIDDEN,
                "message": "Console access requires Admin role",
            },
        )
    return current_role


def require_role(required_role: RoleType):
    """Factory function to create a role-checking dependency.

    Use this for custom role requirements beyond the predefined
    require_admin and require_console_access dependencies.

    Args:
        required_role: The role required to access the endpoint ("admin" or "monitor" only)

    Returns:
        A FastAPI dependency function that checks for the required role

    Example:
        @router.get("/special")
        async def special_endpoint(role: str = Depends(require_role("admin"))):
            pass
    """

    async def check_role(
        current_role: str = Depends(get_current_user),
    ) -> str:
        if current_role != required_role:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": ErrorCode.FORBIDDEN,
                    "message": f"{required_role.title()} role required for this operation",
                },
            )
        return current_role

    return check_role


# Type aliases for cleaner dependency injection
RequireAdmin = Annotated[str, Depends(require_admin)]
RequireConsoleAccess = Annotated[str, Depends(require_console_access)]
