"""Tests for ApiSettingsService.

Story 6.3: API Settings Service
"""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.services.api_settings import (
    ApiSettingInvalidError,
    ApiSettings,
    ApiSettingsService,
    ApiSettingUnknownError,
)


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory structure."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # State dir is now under vsmanager: data/vsmanager/state
    state_dir = data_dir / "vsmanager" / "state"
    state_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def settings(temp_data_dir: Path) -> Settings:
    """Create Settings pointing to temp directory."""
    return Settings(data_dir=temp_data_dir)


@pytest.fixture
def service(settings: Settings) -> ApiSettingsService:
    """Create ApiSettingsService with temp directory."""
    return ApiSettingsService(settings=settings)


class TestApiSettingsModel:
    """Tests for the ApiSettings Pydantic model."""

    def test_default_values(self) -> None:
        """ApiSettings has expected default values."""
        settings = ApiSettings()
        assert settings.auto_start_server is False
        assert settings.block_env_managed_settings is True
        assert settings.enforce_env_on_restart is False
        assert settings.mod_list_refresh_interval == 3600
        assert settings.server_versions_refresh_interval == 86400
        assert settings.metrics_collection_interval == 10  # AC: 5 default 10s

    def test_custom_values(self) -> None:
        """ApiSettings accepts custom values."""
        settings = ApiSettings(
            auto_start_server=True,
            block_env_managed_settings=False,
            mod_list_refresh_interval=1800,
            metrics_collection_interval=30,
        )
        assert settings.auto_start_server is True
        assert settings.block_env_managed_settings is False
        assert settings.mod_list_refresh_interval == 1800
        assert settings.metrics_collection_interval == 30

    def test_interval_validation_rejects_negative(self) -> None:
        """Negative intervals are rejected by Pydantic validation."""
        with pytest.raises(ValueError):
            ApiSettings(mod_list_refresh_interval=-1)

    def test_interval_allows_zero(self) -> None:
        """Zero interval (disabled) is allowed."""
        settings = ApiSettings(mod_list_refresh_interval=0)
        assert settings.mod_list_refresh_interval == 0


class TestGetSettings:
    """Tests for ApiSettingsService.get_settings()."""

    def test_returns_defaults_when_file_missing(self, service: ApiSettingsService) -> None:
        """get_settings returns defaults when api-settings.json does not exist."""
        # Subtask 1.7: returns defaults when file missing
        result = service.get_settings()

        assert result.auto_start_server is False
        assert result.block_env_managed_settings is True
        assert result.mod_list_refresh_interval == 3600
        assert result.server_versions_refresh_interval == 86400
        assert result.metrics_collection_interval == 10

    def test_reads_existing_file_correctly(self, service: ApiSettingsService) -> None:
        """get_settings reads and parses existing api-settings.json."""
        # Subtask 1.8: reads existing file correctly
        service.settings_file.parent.mkdir(parents=True, exist_ok=True)
        service.settings_file.write_text(
            json.dumps(
                {
                    "auto_start_server": True,
                    "block_env_managed_settings": False,
                    "mod_list_refresh_interval": 7200,
                }
            )
        )

        result = service.get_settings()

        assert result.auto_start_server is True
        assert result.block_env_managed_settings is False
        assert result.mod_list_refresh_interval == 7200
        # Non-specified fields should have defaults
        assert result.enforce_env_on_restart is False
        assert result.server_versions_refresh_interval == 86400

    def test_returns_defaults_on_invalid_json(self, service: ApiSettingsService) -> None:
        """get_settings returns defaults if file contains invalid JSON."""
        service.settings_file.parent.mkdir(parents=True, exist_ok=True)
        service.settings_file.write_text("not valid json {{{")

        result = service.get_settings()

        # Should return defaults on parse error
        assert result.auto_start_server is False
        assert result.mod_list_refresh_interval == 3600

    def test_returns_defaults_on_validation_error(
        self, service: ApiSettingsService
    ) -> None:
        """get_settings returns defaults if file values fail validation."""
        service.settings_file.parent.mkdir(parents=True, exist_ok=True)
        service.settings_file.write_text(
            json.dumps({"mod_list_refresh_interval": -999})
        )

        result = service.get_settings()

        # Should return defaults on validation error
        assert result.mod_list_refresh_interval == 3600


class TestUpdateSetting:
    """Tests for ApiSettingsService.update_setting()."""

    @pytest.mark.asyncio
    async def test_validates_and_persists_setting(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting validates value and persists to file."""
        # Subtask 1.9: validates and persists setting
        result = await service.update_setting("auto_start_server", True)

        assert result["key"] == "auto_start_server"
        assert result["value"] is True

        # Verify persisted
        persisted = service.get_settings()
        assert persisted.auto_start_server is True

    @pytest.mark.asyncio
    async def test_update_integer_setting(self, service: ApiSettingsService) -> None:
        """update_setting correctly handles integer settings."""
        result = await service.update_setting("mod_list_refresh_interval", 1800)

        assert result["key"] == "mod_list_refresh_interval"
        assert result["value"] == 1800

        persisted = service.get_settings()
        assert persisted.mod_list_refresh_interval == 1800

    @pytest.mark.asyncio
    async def test_rejects_unknown_key(self, service: ApiSettingsService) -> None:
        """update_setting raises ApiSettingUnknownError for unknown keys."""
        # Subtask 1.10: validation errors for unknown keys
        with pytest.raises(ApiSettingUnknownError) as exc_info:
            await service.update_setting("nonexistent_setting", "value")

        assert "nonexistent_setting" in str(exc_info.value)
        assert exc_info.value.key == "nonexistent_setting"

    @pytest.mark.asyncio
    async def test_rejects_negative_interval(self, service: ApiSettingsService) -> None:
        """update_setting raises ApiSettingInvalidError for negative intervals."""
        # Subtask 1.10: validation errors for negative intervals
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("mod_list_refresh_interval", -100)

        assert "mod_list_refresh_interval" in str(exc_info.value)
        assert exc_info.value.key == "mod_list_refresh_interval"

    @pytest.mark.asyncio
    async def test_rejects_wrong_type_for_integer(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting raises ApiSettingInvalidError for wrong types."""
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("mod_list_refresh_interval", "not-a-number")

        assert "mod_list_refresh_interval" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rejects_boolean_for_integer_field(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting rejects boolean values for integer fields."""
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("mod_list_refresh_interval", True)

        assert "must be an integer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allows_zero_interval(self, service: ApiSettingsService) -> None:
        """update_setting allows zero for interval (disables feature)."""
        result = await service.update_setting("mod_list_refresh_interval", 0)

        assert result["value"] == 0
        persisted = service.get_settings()
        assert persisted.mod_list_refresh_interval == 0

    @pytest.mark.asyncio
    async def test_coerces_string_to_bool(self, service: ApiSettingsService) -> None:
        """update_setting coerces string 'true'/'false' to boolean."""
        result = await service.update_setting("auto_start_server", "true")
        assert result["value"] is True

        result = await service.update_setting("auto_start_server", "false")
        assert result["value"] is False

    @pytest.mark.asyncio
    async def test_coerces_string_to_int(self, service: ApiSettingsService) -> None:
        """update_setting coerces numeric string to integer."""
        result = await service.update_setting("mod_list_refresh_interval", "7200")
        assert result["value"] == 7200


class TestAtomicWrite:
    """Tests for atomic file write behavior."""

    @pytest.mark.asyncio
    async def test_creates_parent_directory(
        self, settings: Settings
    ) -> None:
        """_save_settings creates parent directory if missing."""
        # Subtask 1.5: atomic file writes (temp file + rename)
        # Remove the state directory (now under vsmanager)
        state_dir = settings.state_dir
        if state_dir.exists():
            shutil.rmtree(state_dir)

        service = ApiSettingsService(settings=settings)
        await service.update_setting("auto_start_server", True)

        assert service.settings_file.exists()
        assert service.settings_file.parent.exists()

    @pytest.mark.asyncio
    async def test_file_content_is_valid_json(
        self, service: ApiSettingsService
    ) -> None:
        """Saved file contains valid, parseable JSON."""
        await service.update_setting("auto_start_server", True)

        content = service.settings_file.read_text()
        data = json.loads(content)

        assert data["auto_start_server"] is True
        assert "mod_list_refresh_interval" in data

    @pytest.mark.asyncio
    async def test_preserves_other_settings_on_update(
        self, service: ApiSettingsService
    ) -> None:
        """Updating one setting preserves other settings."""
        # Set initial values
        await service.update_setting("auto_start_server", True)
        await service.update_setting("mod_list_refresh_interval", 1800)

        # Update a different setting
        await service.update_setting("block_env_managed_settings", False)

        # Verify all settings preserved
        persisted = service.get_settings()
        assert persisted.auto_start_server is True
        assert persisted.mod_list_refresh_interval == 1800
        assert persisted.block_env_managed_settings is False


class TestSchedulerCallback:
    """Tests for scheduler callback integration."""

    @pytest.mark.asyncio
    async def test_callback_invoked_on_interval_change(
        self, settings: Settings
    ) -> None:
        """Scheduler callback is invoked when refresh interval changes."""
        # Subtask 4.3: callback invoked on interval change (Task 4)
        callback = MagicMock()
        service = ApiSettingsService(settings=settings, scheduler_callback=callback)

        await service.update_setting("mod_list_refresh_interval", 7200)

        callback.assert_called_once_with("mod_list_refresh_interval", 7200)

    @pytest.mark.asyncio
    async def test_callback_invoked_for_versions_interval(
        self, settings: Settings
    ) -> None:
        """Callback invoked for server_versions_refresh_interval too."""
        callback = MagicMock()
        service = ApiSettingsService(settings=settings, scheduler_callback=callback)

        await service.update_setting("server_versions_refresh_interval", 43200)

        callback.assert_called_once_with("server_versions_refresh_interval", 43200)

    @pytest.mark.asyncio
    async def test_callback_not_invoked_for_non_interval_settings(
        self, settings: Settings
    ) -> None:
        """Callback NOT invoked when updating non-interval settings."""
        callback = MagicMock()
        service = ApiSettingsService(settings=settings, scheduler_callback=callback)

        await service.update_setting("auto_start_server", True)

        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_invoked_for_metrics_interval(
        self, settings: Settings
    ) -> None:
        """Callback invoked for metrics_collection_interval (AC: 5)."""
        callback = MagicMock()
        service = ApiSettingsService(settings=settings, scheduler_callback=callback)

        await service.update_setting("metrics_collection_interval", 30)

        callback.assert_called_once_with("metrics_collection_interval", 30)

    @pytest.mark.asyncio
    async def test_works_without_callback(self, service: ApiSettingsService) -> None:
        """Service works fine when no scheduler_callback provided."""
        # Default service has no callback
        result = await service.update_setting("mod_list_refresh_interval", 1800)

        assert result["value"] == 1800
