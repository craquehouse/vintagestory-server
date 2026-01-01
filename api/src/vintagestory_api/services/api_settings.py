"""API settings service for management API configuration.

Story 6.3: API Settings Service

This service provides read and update operations for API operational settings
stored in api-settings.json. Unlike game settings, these are direct file
persistence without console command integration.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field, ValidationError

from vintagestory_api.config import Settings

logger = structlog.get_logger()


class ApiSettings(BaseModel):
    """API server operational settings."""

    auto_start_server: bool = Field(
        default=False,
        description="Start game server automatically when API launches",
    )
    block_env_managed_settings: bool = Field(
        default=True,
        description="Reject UI changes to settings controlled by VS_CFG_* env vars",
    )
    enforce_env_on_restart: bool = Field(
        default=False,
        description="Re-apply VS_CFG_* values on each game server restart (backlog)",
    )
    mod_list_refresh_interval: int = Field(
        default=3600,
        ge=0,
        description="Seconds between mod API cache refreshes (0 = disabled)",
    )
    server_versions_refresh_interval: int = Field(
        default=86400,
        ge=0,
        description="Seconds between checking for new VS versions (0 = disabled)",
    )


class ApiSettingUnknownError(Exception):
    """Raised when an unknown API setting key is requested."""

    def __init__(self, key: str) -> None:
        """Initialize error with the unknown key.

        Args:
            key: The setting key that was not found.
        """
        self.key = key
        self.message = f"Unknown API setting: '{key}'"
        super().__init__(self.message)


class ApiSettingInvalidError(Exception):
    """Raised when an invalid value is provided for an API setting."""

    def __init__(self, key: str, reason: str) -> None:
        """Initialize error with key and validation reason.

        Args:
            key: The setting key that failed validation.
            reason: Description of why the value is invalid.
        """
        self.key = key
        self.reason = reason
        self.message = f"Invalid value for '{key}': {reason}"
        super().__init__(self.message)


class ApiSettingsService:
    """Service for managing API operational settings.

    Settings are persisted to api-settings.json in the state directory.
    Unlike game settings, these use direct file persistence without
    console command integration.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        scheduler_callback: Callable[[str, int], None] | None = None,
    ) -> None:
        """Initialize the API settings service.

        Args:
            settings: Application settings. If None, creates new Settings instance.
            scheduler_callback: Optional callback invoked when refresh interval
                settings change. Called with (setting_key, new_value).
                This is a stub for Epic 7 scheduler integration.
        """
        self._settings = settings or Settings()
        self._scheduler_callback = scheduler_callback
        self._settings_file = self._settings.state_dir / "api-settings.json"

    @property
    def settings_file(self) -> Path:
        """Path to the api-settings.json file."""
        return self._settings_file

    def get_settings(self) -> ApiSettings:
        """Get current API settings from file or defaults.

        Returns:
            ApiSettings model with current values. Returns defaults if file
            does not exist or cannot be parsed.
        """
        if not self._settings_file.exists():
            logger.debug("api_settings_file_not_found", path=str(self._settings_file))
            return ApiSettings()

        try:
            content = self._settings_file.read_text()
            data = json.loads(content)
            settings = ApiSettings(**data)
            logger.debug("api_settings_loaded", path=str(self._settings_file))
            return settings
        except (json.JSONDecodeError, ValidationError) as e:
            # Graceful degradation: return defaults on corrupt/invalid file rather than
            # failing the request. This ensures the API remains operational even if the
            # settings file is manually edited incorrectly. The warning log allows
            # administrators to detect and fix the issue.
            logger.warning(
                "api_settings_load_failed",
                path=str(self._settings_file),
                error=str(e),
            )
            return ApiSettings()

    async def update_setting(self, key: str, value: Any) -> dict[str, Any]:
        """Update a single API setting.

        Validates the key exists, validates the value type/constraints,
        persists the change, and optionally notifies the scheduler.

        Args:
            key: The setting key to update.
            value: The new value for the setting.

        Returns:
            Dict with "key" and "value" confirming the update.

        Raises:
            ApiSettingUnknownError: If key is not a valid setting.
            ApiSettingInvalidError: If value fails validation.
        """
        # Validate key exists in model
        if key not in ApiSettings.model_fields:
            raise ApiSettingUnknownError(key)

        # Get current settings and capture old value for logging
        current = self.get_settings()
        old_value = getattr(current, key)
        current_dict = current.model_dump()

        # Get the field info for type validation
        field_info = ApiSettings.model_fields[key]
        expected_type = field_info.annotation

        # Validate value type
        try:
            # Handle type coercion for common cases
            if expected_type is bool:
                if isinstance(value, bool):
                    validated_value = value
                elif isinstance(value, str):
                    if value.lower() in ("true", "1", "yes"):
                        validated_value = True
                    elif value.lower() in ("false", "0", "no"):
                        validated_value = False
                    else:
                        raise ApiSettingInvalidError(
                            key, "must be a boolean (true/false)"
                        )
                elif isinstance(value, int) and not isinstance(value, bool):
                    validated_value = bool(value)
                else:
                    raise ApiSettingInvalidError(key, "must be a boolean")
            elif expected_type is int:
                if isinstance(value, bool):
                    raise ApiSettingInvalidError(key, "must be an integer, not boolean")
                elif isinstance(value, int):
                    validated_value = value
                elif isinstance(value, str):
                    try:
                        validated_value = int(value)
                    except ValueError:
                        raise ApiSettingInvalidError(key, "must be an integer")
                else:
                    raise ApiSettingInvalidError(key, "must be an integer")
            else:
                validated_value = value

            # Update the dict and validate with Pydantic
            current_dict[key] = validated_value
            updated = ApiSettings(**current_dict)

        except ValidationError as e:
            # Extract the first error message for user-friendly output
            error_msg = str(e.errors()[0].get("msg", str(e)))
            raise ApiSettingInvalidError(key, error_msg)

        # Persist with atomic write
        self._save_settings(updated)

        # Notify scheduler if refresh interval changed.
        # Note: validated_value is safe to pass here because Pydantic validation
        # (including ge=0 constraint) has already succeeded above. The callback
        # will only receive valid, type-checked integer values.
        if key in ("mod_list_refresh_interval", "server_versions_refresh_interval"):
            if self._scheduler_callback:
                self._scheduler_callback(key, validated_value)

        logger.info(
            "api_setting_updated",
            key=key,
            value=validated_value,
            old_value=old_value,
            source="api",
        )

        return {"key": key, "value": getattr(updated, key)}

    def _save_settings(self, settings: ApiSettings) -> None:
        """Save settings with atomic write pattern.

        Creates parent directory if it doesn't exist.
        Uses temp file + rename for atomicity.

        Args:
            settings: The ApiSettings model to persist.

        Raises:
            OSError: If directory creation or file write fails.
        """
        temp_file = self._settings_file.with_suffix(".tmp")

        try:
            # Ensure directory exists
            self._settings_file.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write: temp file then rename
            temp_file.write_text(json.dumps(settings.model_dump(), indent=2))
            temp_file.rename(self._settings_file)

            logger.info("api_settings_saved", path=str(self._settings_file))

        except OSError as e:
            logger.error(
                "api_settings_save_failed",
                path=str(self._settings_file),
                error=str(e),
            )
            # Clean up temp file if it exists
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            raise
