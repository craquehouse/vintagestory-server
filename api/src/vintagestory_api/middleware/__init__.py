"""API middleware."""

from vintagestory_api.middleware.auth import (
    CurrentUser,
    UserRole,
    get_client_ip,
    get_current_user,
    get_settings,
)
from vintagestory_api.middleware.permissions import (
    RequireAdmin,
    RequireConsoleAccess,
    require_admin,
    require_console_access,
    require_role,
)

__all__ = [
    "CurrentUser",
    "RequireAdmin",
    "RequireConsoleAccess",
    "UserRole",
    "get_client_ip",
    "get_current_user",
    "get_settings",
    "require_admin",
    "require_console_access",
    "require_role",
]
