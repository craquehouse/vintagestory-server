"""Application configuration using pydantic-settings."""

import logging
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import structlog
from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The mod database's base address; VS_MOD_DB_URL replaces it (Epic 20 ADR-9)
DEFAULT_MOD_DB_URL = "https://mods.vintagestory.at"

_MOD_DB_URL_INVALID = (
    "VS_MOD_DB_URL must be an absolute https URL with a host, "
    "for example https://mods.vintagestory.at."
)
_MOD_DB_URL_CREDENTIALS = "VS_MOD_DB_URL must not contain a user name or password."
_MOD_DB_URL_PATH = (
    "VS_MOD_DB_URL must not contain a path, a query or a fragment; "
    "give the site's base address only."
)
# VS_LOG_LEVEL's values, in order (Epic 21 ADR-4); CRITICAL is not one of them
LOG_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR")
_LOG_LEVEL_INVALID = "VS_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR."

_MOD_DB_URL_PLAIN_HTTP = (
    "VS_MOD_DB_URL uses plain HTTP, which is for testing and needs VS_DEBUG=true. "
    "Use an https address."
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # hide_input_in_errors: a refused setting's value is not printed, so a password typed
    # into VS_MOD_DB_URL or an API key never reaches the start-up log (Epic 20 ADR-9)
    model_config = SettingsConfigDict(env_prefix="VS_", hide_input_in_errors=True)

    debug: bool = False
    # VS_LOG_LEVEL: the API's log level at start-up, one of LOG_LEVELS (Epic 21 ADR-4).
    # Unset or blank: DEBUG with VS_DEBUG=true, INFO otherwise
    log_level: str | None = None
    api_key_admin: str = ""
    api_key_monitor: str | None = None
    # VS_API_KEY: the key the web UI uses, served at runtime by /config.js (Epic 15 ADR-5).
    # No default: unset or blank, the web UI gets no key (Epic 19 ADR-5)
    api_key: str | None = None
    data_dir: Path = Path("/data")
    cors_origins: str = "http://localhost:5173"  # Comma-separated list of allowed origins
    console_history_lines: int = 100  # Default history lines sent on WebSocket connect
    disk_space_warning_threshold_gb: float = 1.0  # Warn when available space below this
    mod_cache_max_size_mb: int = 500  # Maximum size of mod cache in MB (0 to disable)
    # VS_CSP_MODE: how the web UI's Content-Security-Policy is sent (Epic 19 ADR-6):
    # enforce (default), report-only or off. Blank means unset
    csp_mode: str = "enforce"
    # VS_MOD_DB_URL: base address for mod database requests and mod downloads (Epic 20
    # ADR-9). https only; http needs VS_DEBUG=true. Blank means unset
    mod_db_url: str = DEFAULT_MOD_DB_URL

    @property
    def web_api_key(self) -> str:
        """VS_API_KEY, or the empty string when it is unset or blank (Epic 19 ADR-5)."""
        if self.api_key and self.api_key.strip():
            return self.api_key
        return ""

    def web_api_key_state(self) -> Literal["not_set", "admin", "monitor", "no_role"]:
        """Which key the web UI gets: none, the Admin key, the Monitor key or one with no role.

        The Admin key is checked first, so when both role keys are equal the state is
        "admin". An empty Monitor key matches nothing, as in authentication.
        """
        key = self.web_api_key
        if not key:
            return "not_set"
        if key == self.api_key_admin:
            return "admin"
        if self.api_key_monitor and key == self.api_key_monitor:
            return "monitor"
        return "no_role"

    @field_validator("disk_space_warning_threshold_gb")
    @classmethod
    def validate_disk_space_threshold(cls, v: float) -> float:
        """Validate that disk space threshold is non-negative.

        Args:
            v: Threshold in gigabytes

        Returns:
            Validated threshold

        Raises:
            ValueError: If threshold is negative
        """
        if v < 0:
            raise ValueError(
                "VS_DISK_SPACE_WARNING_THRESHOLD_GB must be non-negative. "
                "Use 0 to disable the fixed GB threshold (percentage-based will still apply)."
            )
        return v

    @field_validator("mod_cache_max_size_mb")
    @classmethod
    def validate_mod_cache_max_size(cls, v: int) -> int:
        """Validate that mod cache max size is non-negative.

        Args:
            v: Maximum cache size in megabytes

        Returns:
            Validated cache size

        Raises:
            ValueError: If cache size is negative
        """
        if v < 0:
            raise ValueError(
                "VS_MOD_CACHE_MAX_SIZE_MB must be non-negative. Use 0 to disable cache eviction."
            )
        return v

    @field_validator("csp_mode")
    @classmethod
    def validate_csp_mode(cls, v: str) -> str:
        """Normalize VS_CSP_MODE; a blank value is the default, an unknown one an error.

        A plain str rather than a Literal, so the error names VS_CSP_MODE (Epic 19 ADR-6).
        """
        mode = v.strip().lower()
        if not mode:
            return "enforce"
        if mode not in ("enforce", "report-only", "off"):
            raise ValueError("VS_CSP_MODE must be one of: enforce, report-only, off.")
        return mode

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str | None) -> str | None:
        """Normalize VS_LOG_LEVEL; blank means unset, anything but the four levels an error.

        A plain str rather than a Literal, so the error names VS_LOG_LEVEL (Epic 21 ADR-4).
        """
        if v is None:
            return None
        level = v.strip().upper()
        if not level:
            return None
        if level not in LOG_LEVELS:
            raise ValueError(_LOG_LEVEL_INVALID)
        return level

    @field_validator("mod_db_url")
    @classmethod
    def validate_mod_db_url(cls, v: str, info: ValidationInfo) -> str:
        """Normalize VS_MOD_DB_URL to scheme://host[:port]; refuse anything else.

        A field validator, not a model validator: a failing model validator would print
        every setting in its error. The messages never repeat the value (Epic 20 ADR-9).
        Plain http needs the VS_DEBUG the process started with; if VS_DEBUG itself failed
        to parse, debug is not in info.data and http is refused.
        """
        value = v.strip()
        if not value:
            return DEFAULT_MOD_DB_URL
        if any(ch.isspace() or not ch.isprintable() for ch in value):
            raise ValueError(_MOD_DB_URL_INVALID)
        try:
            parts = urlsplit(value)
            port = parts.port
        except ValueError:
            raise ValueError(_MOD_DB_URL_INVALID) from None
        if parts.scheme not in ("https", "http") or not parts.hostname:
            raise ValueError(_MOD_DB_URL_INVALID)
        if "@" in parts.netloc:
            raise ValueError(_MOD_DB_URL_CREDENTIALS)
        if parts.netloc.endswith(":") or port == 0:
            raise ValueError(_MOD_DB_URL_INVALID)
        if parts.path not in ("", "/") or "?" in value or "#" in value:
            raise ValueError(_MOD_DB_URL_PATH)
        if parts.scheme == "http" and info.data.get("debug") is not True:
            raise ValueError(_MOD_DB_URL_PLAIN_HTTP)
        host = parts.hostname
        if ":" in host:
            host = f"[{host}]"
        address = f"{parts.scheme}://{host}"
        if port is not None:
            address += f":{port}"
        return address

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Validate that CORS origins are well-formed URLs.

        Args:
            v: Comma-separated list of origin URLs

        Returns:
            Validated origins string

        Raises:
            ValueError: If origins are empty or malformed
        """
        if not v or not v.strip():
            raise ValueError(
                "VS_CORS_ORIGINS cannot be empty. "
                "Provide at least one valid origin URL (e.g., http://localhost:5173)."
            )

        origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        if not origins:
            raise ValueError(
                "VS_CORS_ORIGINS must contain at least one valid origin URL. "
                "Example: http://localhost:5173,https://myapp.com"
            )

        # Validate each origin has proper URL structure
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"[a-zA-Z0-9\-._~%!$&'()*+,;=]+"  # hostname/domain
            r"(:[0-9]+)?$"  # optional port
        )

        for origin in origins:
            if not url_pattern.match(origin):
                raise ValueError(
                    f"Invalid CORS origin: '{origin}'. "
                    "Origins must be valid URLs starting with http:// or https:// "
                    "(e.g., http://localhost:5173 or https://example.com)."
                )

        return v

    @property
    def server_dir(self) -> Path:
        """Directory for VintageStory server installation (extracted tarball)."""
        return self.data_dir / "server"

    @property
    def serverdata_dir(self) -> Path:
        """Directory for persistent game data (Mods, Saves, configs).

        This is passed to VintageStory via --dataPath argument.
        Contains: Mods/, Saves/, serverconfig.json, logs, etc.
        """
        return self.data_dir / "serverdata"

    @property
    def vsmanager_dir(self) -> Path:
        """Directory for API manager state (version tracking, install status)."""
        return self.data_dir / "vsmanager"

    @property
    def cache_dir(self) -> Path:
        """Directory for cached data (downloaded mods, etc.)."""
        return self.vsmanager_dir / "cache"

    @property
    def state_dir(self) -> Path:
        """Directory for API state files (mods.json, api-settings.json, etc.)."""
        return self.vsmanager_dir / "state"

    @property
    def logs_dir(self) -> Path:
        """Directory for application log files (if file logging enabled)."""
        return self.vsmanager_dir / "logs"

    def ensure_data_directories(self) -> None:
        """Create data directory structure if it doesn't exist.

        Creates the following directories under data_dir:
        - server/: VintageStory server installation
        - serverdata/: Game data (Mods, Saves, configs)
        - vsmanager/: API manager state
        - vsmanager/cache/: Cached downloads
        - vsmanager/state/: State files
        - vsmanager/logs/: Application logs (if file logging enabled)

        Raises:
            ValueError: If VS_API_KEY_ADMIN is not set
            OSError: If directory creation fails (e.g., permissions)
        """
        # Security: Validate that admin API key is set
        if not self.api_key_admin or self.api_key_admin.strip() == "":
            raise ValueError(
                "VS_API_KEY_ADMIN must be set to a non-empty value for security. "
                "See .env.example for configuration details."
            )

        logger = structlog.get_logger()
        for directory in [
            self.server_dir,
            self.serverdata_dir,
            self.vsmanager_dir,
            self.cache_dir,
            self.state_dir,
            self.logs_dir,
        ]:
            try:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
                    logger.info("directory_created", path=str(directory))
            except OSError as e:
                logger.error(
                    "directory_creation_failed",
                    path=str(directory),
                    error=str(e),
                )
                raise


# Internal debug state - this is the source of truth at runtime.
# Set once at start-up from the settings (VS_DEBUG, VS_LOG_LEVEL), toggled via the API
_debug_enabled: bool = False
_debug_initialized: bool = False
_configured_log_level: str | None = None  # VS_LOG_LEVEL, validated; None when unset
_current_log_level: str = "INFO"  # the level structlog filters at now


def initialize_debug_state(debug: bool, log_level: str | None) -> None:
    """Apply the settings' debug flag and log level once, at start-up (Epic 21 ADR-4).

    Args:
        debug: Settings.debug (VS_DEBUG, parsed by the settings only).
        log_level: Settings.log_level (VS_LOG_LEVEL, validated), or None when unset:
            then DEBUG in debug mode and INFO otherwise.

    Later calls do nothing; use set_debug_enabled() to toggle at runtime.
    """
    global _debug_enabled, _debug_initialized, _configured_log_level, _current_log_level
    if _debug_initialized:
        return
    _debug_enabled = debug
    _configured_log_level = log_level
    _current_log_level = log_level or ("DEBUG" if debug else "INFO")
    _debug_initialized = True
    configure_logging(debug=debug, log_level=_current_log_level)


def current_log_level() -> str:
    """The level the API's log lines are filtered at now."""
    return _current_log_level


def is_debug_enabled() -> bool:
    """Get current debug state.

    Returns:
        True if debug logging is currently enabled.
    """
    return _debug_enabled


def set_debug_enabled(enabled: bool) -> bool:
    """Set debug state and reconfigure logging.

    Called by API endpoint to toggle debug logging at runtime (FR48). On gives DEBUG;
    off returns to the configured level (VS_LOG_LEVEL, or INFO) (Epic 21 ADR-4).

    Args:
        enabled: True to enable debug logging, False to disable.

    Returns:
        True if the debug state or the level changed, False if both were already
        as requested.
    """
    global _debug_enabled, _current_log_level
    level = "DEBUG" if enabled else (_configured_log_level or "INFO")
    if _debug_enabled == enabled and _current_log_level == level:
        return False
    previous = _debug_enabled
    _debug_enabled = enabled
    _current_log_level = level
    configure_logging(debug=enabled, log_level=level)
    log = structlog.get_logger()
    log.info("debug_logging_toggled", previous=previous, current=enabled)
    return True


def get_current_debug_setting() -> bool:
    """Get current debug state.

    DEPRECATED: Use is_debug_enabled() instead.
    This function is kept for backwards compatibility with existing tests.

    Returns:
        True if debug logging is currently enabled.
    """
    return _debug_enabled


def configure_logging(debug: bool = False, log_level: str | None = None) -> None:
    """Configure structlog for dev (colorful) or prod (JSON) output.

    Args:
        debug: If True, use colorful dev output; otherwise JSON for production.
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR). If None,
                   defaults to DEBUG in debug mode, INFO in production.

    Logging Conventions:
        - All logs include ISO 8601 timestamps for consistency
        - Dev mode: colorful ConsoleRenderer for readability
        - Prod mode: JSONRenderer for machine parsing
        - Use structured key=value pairs, not string interpolation
        - Never log sensitive data (API keys, passwords)

    Runtime Debug Toggle (FR48):
        Do not call this directly to change the level: start-up goes through
        initialize_debug_state() and the runtime switch through set_debug_enabled(),
        which keep the debug state and current_log_level() in step (Epic 21 ADR-4).
    """
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), None)
        if level is None:
            level = logging.DEBUG if debug else logging.INFO
    else:
        level = logging.DEBUG if debug else logging.INFO

    # Common processors for both modes
    # IMPORTANT: merge_contextvars MUST be first to include request context (request_id)
    common_processors = [
        structlog.contextvars.merge_contextvars,  # Merge request context (request_id, etc.)
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
    ]

    if debug:
        # Development: human-readable, colorful output with timestamps
        structlog.configure(
            processors=[
                *common_processors,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            # cache_logger_on_first_use=False allows runtime reconfiguration
            cache_logger_on_first_use=False,
        )
    else:
        # Production: JSON, machine-parseable output
        structlog.configure(
            processors=[
                *common_processors,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            # cache_logger_on_first_use=False allows runtime reconfiguration
            cache_logger_on_first_use=False,
        )


# Track last known debug state for change detection
_last_debug_state: bool | None = None


def reconfigure_logging_if_changed() -> bool:
    """Check VS_DEBUG environment and reconfigure logging if changed.

    This function enables runtime toggling of debug logging (FR48) by:
    1. Reading current VS_DEBUG from environment
    2. Comparing to last known state
    3. Reconfiguring structlog if state changed

    Should be called periodically or per-request (e.g., in middleware).

    Returns:
        True if logging was reconfigured, False if unchanged.
    """
    global _last_debug_state

    current_debug = get_current_debug_setting()

    # First call or state changed
    if _last_debug_state is None or current_debug != _last_debug_state:
        previous = _last_debug_state
        _last_debug_state = current_debug

        # Reconfigure logging with new debug state
        configure_logging(debug=current_debug, log_level=_current_log_level)

        # Log the change (only if this isn't the first initialization)
        if previous is not None:
            logger = structlog.get_logger()
            logger.info(
                "debug_logging_toggled",
                previous=previous,
                current=current_debug,
            )

        return True

    return False
