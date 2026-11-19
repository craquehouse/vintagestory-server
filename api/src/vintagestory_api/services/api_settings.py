"""API settings service for management API configuration.

Story 6.3: API Settings Service
Story 17.6: Settings behave as saved (interval bound, ApiSettingNotAppliedError)
Story 22.3: Scheduled restarts (scheduled_restart_times, Epic 22 ADR-5)

This service provides read and update operations for API operational settings
stored in api-settings.json. Unlike game settings, these are direct file
persistence without console command integration.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_origin
from urllib.parse import urlsplit

import structlog
from pydantic import BaseModel, Field, ValidationError, field_validator

from vintagestory_api.config import Settings

logger = structlog.get_logger()

MAX_INTERVAL_SECONDS = 31_536_000
"""Upper bound of the refresh interval settings: 365 days (Story 17.6).

Longer intervals cannot be scheduled reliably (now + interval can pass the largest date
the scheduler holds), and 0 already disables a job, so anything longer means "never".
"""

RESTART_TIMES_SETTING = "scheduled_restart_times"
MAX_RESTART_TIMES = 24
MIN_RESTART_GAP_MINUTES = 16
"""Each sequence runs from 15 minutes before its time to the restart (Epic 22 ADR-6 decision 6)."""
_RESTART_TIME = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")
_MINUTES_PER_DAY = 1440
_SHOWN_ENTRY_LENGTH = 16


def _minutes(restart_time: str) -> int:
    """Minutes after midnight of a validated HH:MM time."""
    hours, minutes = restart_time.split(":")
    return int(hours) * 60 + int(minutes)


def _is_json_array(value: object) -> bool:
    """True for a JSON array (a list); kept out of line so pyright does not narrow Any."""
    return isinstance(value, list)


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
        default=14400,
        ge=0,
        le=MAX_INTERVAL_SECONDS,
        description=(
            "Seconds between mod API cache refreshes (0 = disabled, at most 365 days). "
            "Default: 4 hours"
        ),
    )
    server_versions_refresh_interval: int = Field(
        default=86400,
        ge=0,
        le=MAX_INTERVAL_SECONDS,
        description=(
            "Seconds between checking for new VS versions (0 = disabled, at most 365 days)"
        ),
    )
    metrics_collection_interval: int = Field(
        default=10,
        ge=0,
        le=MAX_INTERVAL_SECONDS,
        description="Seconds between metrics collection (0 = disabled, at most 365 days)",
    )
    scheduled_restart_times: list[str] = Field(
        default_factory=list[str],
        description=(
            "Daily restart times, HH:MM (24-hour) in the container's time zone (TZ, UTC when "
            "unset). Players are warned 15, 5 and 1 minutes before; a stopped server is not "
            "started; a time less than 15 minutes ahead first runs the next day. At most 24, "
            "at least 16 minutes apart."
        ),
    )
    mod_update_webhook_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Webhook for mod update alerts (Story 14.6). Secret: never logged or read back",
    )

    @field_validator("mod_update_webhook_url")
    @classmethod
    def _validate_webhook_url(cls, value: str | None) -> str | None:
        # Messages must not include the value: it is a secret.
        if value is None or value == "":
            return None
        try:
            parts = urlsplit(value)
        except ValueError:
            raise ValueError("must be an http or https URL") from None
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("must be an http or https URL with a host")
        return value

    @field_validator("scheduled_restart_times")
    @classmethod
    def _validate_restart_times(cls, value: list[str]) -> list[str]:
        # fullmatch and [0-9]: "04:00\n" and full-width digits are refused (Story 22.3).
        for entry in value:
            if not _RESTART_TIME.fullmatch(entry):
                shown = (
                    entry[:_SHOWN_ENTRY_LENGTH] + "..."
                    if len(entry) > _SHOWN_ENTRY_LENGTH
                    else entry
                )
                raise ValueError(f"{shown!r} is not a time in HH:MM (24-hour, 00:00 to 23:59)")
        # Zero-padded HH:MM sorts as text.
        times = sorted(set(value))
        if len(times) > MAX_RESTART_TIMES:
            raise ValueError(f"at most {MAX_RESTART_TIMES} times, got {len(times)}")
        if len(times) >= 2:
            # Each time and the next one, the last wrapping to the first: the jobs are daily,
            # so two times around midnight overlap like any other two (Story 22.3).
            for this, following in zip(times, [*times[1:], times[0]], strict=True):
                gap = (_minutes(following) - _minutes(this)) % _MINUTES_PER_DAY
                if gap < MIN_RESTART_GAP_MINUTES:
                    raise ValueError(
                        f"{this!r} and {following!r} are {gap} minutes apart; restart times "
                        f"must be at least {MIN_RESTART_GAP_MINUTES} minutes apart"
                    )
        return times

    def redacted(self) -> dict[str, Any]:
        """Settings for API responses: secrets replaced by whether they are configured."""
        data = self.model_dump(exclude=set(SECRET_SETTINGS))
        data["mod_update_webhook_configured"] = self.mod_update_webhook_url is not None
        return data


SECRET_SETTINGS = frozenset({"mod_update_webhook_url"})
"""Settings whose values are never logged or returned (FR149)."""

SCHEDULED_SETTINGS = frozenset(
    {
        "mod_list_refresh_interval",
        "server_versions_refresh_interval",
        "metrics_collection_interval",
    }
)
"""Settings whose saved value is passed to the scheduler callback (Story 17.6, Story 22.3).

The interval keys are the same as `vintagestory_api.jobs.INTERVAL_JOBS`; this module
cannot import that one (`jobs` imports this module), and a test asserts they match. The
web's `INTERVAL_API_SETTINGS` (`web/src/api/config.ts`) lists the interval keys too.
"""


def _describe_validation_errors(error: ValidationError) -> str:
    """Field names and messages only; never the invalid values (they may be secrets)."""
    return "; ".join(
        f"{'.'.join(str(part) for part in detail['loc'])}: {detail['msg']}"
        for detail in error.errors(include_input=False, include_url=False)
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


class ApiSettingNotAppliedError(Exception):
    """Raised when an interval setting was saved but its job could not be rescheduled.

    Story 17.6 (Epic 17 ADR-5 decision 5): the value stays saved and applies at the
    next API start; the failure is reported instead of leaving the screen and the
    scheduler silently disagreeing.
    """

    def __init__(self, key: str, reason: str) -> None:
        """Initialize error with key and the scheduler's reason.

        Args:
            key: The setting key that was saved.
            reason: Why its job could not be rescheduled.
        """
        self.key = key
        self.reason = reason
        self.message = (
            f"Saved '{key}', but its job could not be rescheduled: {reason}. "
            "The saved value applies when the API restarts."
        )
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
            scheduler_callback: Optional callback invoked after a refresh interval
                setting is saved, with (setting_key, new_value). The config router
                passes `apply_interval_setting` bound to the scheduler, so the job
                follows the saved value (Story 17.6).
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
            if not isinstance(data, dict):
                raise ValueError("settings file is not a JSON object")
            settings = ApiSettings.model_validate(data)
            logger.debug("api_settings_loaded", path=str(self._settings_file))
            return settings
        except (ValidationError, ValueError) as e:
            # ValueError covers json.JSONDecodeError, UnicodeDecodeError (bytes that are
            # not UTF-8) and a top level that is not an object.
            # Graceful degradation: return defaults on corrupt/invalid file rather than
            # failing the request. This ensures the API remains operational even if the
            # settings file is manually edited incorrectly. The warning log allows
            # administrators to detect and fix the issue.
            # Never str() a ValidationError: it quotes the input, which can be the
            # webhook URL (FR149). JSONDecodeError messages carry only a position.
            error = _describe_validation_errors(e) if isinstance(e, ValidationError) else str(e)
            logger.warning(
                "api_settings_load_failed",
                path=str(self._settings_file),
                error=error,
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
            ApiSettingNotAppliedError: If the value was saved but the scheduler
                callback failed (Story 17.6).
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
                        raise ApiSettingInvalidError(key, "must be a boolean (true/false)")
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
            elif get_origin(expected_type) is list:
                # A list setting (scheduled_restart_times, Story 22.3): only check it is a
                # JSON array here; the model's validator checks the entries.
                if not _is_json_array(value):
                    raise ApiSettingInvalidError(key, "must be a list of times in HH:MM")
                validated_value = value
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

        # Notify the scheduler of a scheduled setting with the stored value: the validated
        # int for an interval, the sorted list without duplicates for restart times.
        stored = getattr(updated, key)
        if key in SCHEDULED_SETTINGS and self._scheduler_callback:
            try:
                self._scheduler_callback(key, stored)
            except Exception as e:
                # Deliberately broad (Story 17.6, ADR-5 decision 5): any scheduler
                # failure after the save must be reported. It is re-raised as a typed
                # error, not swallowed.
                logger.error(
                    "api_setting_not_applied",
                    key=key,
                    value=stored,
                    error=str(e),
                )
                raise ApiSettingNotAppliedError(key, str(e)) from e

        if key in SECRET_SETTINGS:
            configured = getattr(updated, key) is not None
            logger.info(
                "api_setting_updated",
                key=key,
                configured=configured,
                was_configured=old_value is not None,
                source="api",
            )
            return {"key": key, "configured": configured}

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
