"""Application configuration using pydantic-settings."""

import logging

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="VS_")

    debug: bool = False
    api_key_admin: str = ""
    api_key_monitor: str | None = None
    game_version: str = "stable"


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


