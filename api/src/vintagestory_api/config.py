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
    api_key_admin: str = ""
    api_key_monitor: str | None = None
    game_version: str = "stable"
    data_dir: Path = Path("/data")
    cors_origins: str = "http://localhost:5173"  # Comma-separated list of allowed origins

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
    def state_dir(self) -> Path:
        """Directory for API state persistence."""
        return self.data_dir / "state"

    @property
    def server_dir(self) -> Path:
        """Directory for VintageStory server installation."""
        return self.data_dir / "server"

    @property
    def mods_dir(self) -> Path:
        """Directory for mod files."""
        return self.data_dir / "mods"

    @property
    def config_dir(self) -> Path:
        """Directory for game server configuration."""
        return self.data_dir / "config"

    @property
    def logs_dir(self) -> Path:
        """Directory for application logs."""
        return self.data_dir / "logs"

    @property
    def backups_dir(self) -> Path:
        """Directory for server backups."""
        return self.data_dir / "backups"

    def ensure_data_directories(self) -> None:
        """Create data directory structure if it doesn't exist."""
        # Security: Validate that admin API key is set
        if not self.api_key_admin or self.api_key_admin.strip() == "":
            raise ValueError(
                "VS_API_KEY_ADMIN must be set to a non-empty value for security. "
                "See .env.example for configuration details."
            )

        for directory in [
            self.state_dir,
            self.server_dir,
            self.mods_dir,
            self.config_dir,
            self.logs_dir,
            self.backups_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


def configure_logging(debug: bool = False) -> None:
    """Configure structlog for dev (colorful) or prod (JSON) output.

    Args:
        debug: If True, use colorful dev output; otherwise JSON for production.
    """
    if debug:
        # Development: human-readable, colorful output
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Production: JSON, machine-parseable output
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
