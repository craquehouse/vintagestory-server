"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="VS_")

    debug: bool = False
    api_key_admin: str = ""
    api_key_monitor: str | None = None
    game_version: str = "stable"


settings = Settings()
