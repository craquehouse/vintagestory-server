"""Machine-readable error codes for API responses."""


class ErrorCode:
    """Centralized error codes used across the API.

    These codes are returned in error responses for machine parsing.
    Human-readable messages accompany them for debugging.
    """

    # Authentication
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # Server lifecycle
    SERVER_NOT_RUNNING = "SERVER_NOT_RUNNING"
    SERVER_NOT_INSTALLED = "SERVER_NOT_INSTALLED"
    SERVER_ALREADY_RUNNING = "SERVER_ALREADY_RUNNING"

    # Mods
    MOD_NOT_FOUND = "MOD_NOT_FOUND"
    MOD_INCOMPATIBLE = "MOD_INCOMPATIBLE"
    MOD_ALREADY_INSTALLED = "MOD_ALREADY_INSTALLED"

    # Config
    INVALID_CONFIG = "INVALID_CONFIG"
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"

    # External APIs
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    EXTERNAL_API_TIMEOUT = "EXTERNAL_API_TIMEOUT"

    # General
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
