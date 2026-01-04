"""Application configuration using pydantic-settings."""

import logging
import re
from pathlib import Path

import structlog
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="VS_")

    debug: bool = False
    log_level: str | None = None  # Override log level (DEBUG, INFO, WARNING, ERROR)
    api_key_admin: str = ""
    api_key_monitor: str | None = None
    game_version: str = "stable"
    data_dir: Path = Path("/data")
    cors_origins: str = "http://localhost:5173"  # Comma-separated list of allowed origins
    console_history_lines: int = 100  # Default history lines sent on WebSocket connect
    disk_space_warning_threshold_gb: float = 1.0  # Warn when available space below this
    mod_cache_max_size_mb: int = 500  # Maximum size of mod cache in MB (0 to disable)

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
                "VS_MOD_CACHE_MAX_SIZE_MB must be non-negative. "
                "Use 0 to disable cache eviction."
            )
        return v

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
    """
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), None)
        if level is None:
            level = logging.DEBUG if debug else logging.INFO
    else:
        level = logging.DEBUG if debug else logging.INFO

    # Common processors for both modes - always include ISO 8601 timestamps
    common_processors = [
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
            cache_logger_on_first_use=True,
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
            cache_logger_on_first_use=True,
        )
