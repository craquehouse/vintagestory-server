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
from vintagestory_api.middleware.request_context import RequestContextMiddleware

__all__ = [
    "CurrentUser",
    "RequestContextMiddleware",
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
