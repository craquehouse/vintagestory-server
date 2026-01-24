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
        assert settings.mod_list_refresh_interval == 14400
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
        assert result.mod_list_refresh_interval == 14400
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
        assert result.mod_list_refresh_interval == 14400

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
        assert result.mod_list_refresh_interval == 14400


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


class TestBooleanCoercion:
    """Tests for additional boolean coercion edge cases."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_string_for_boolean(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting rejects invalid string values for boolean fields."""
        # Lines 188-190: String value that can't be coerced to boolean
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("auto_start_server", "invalid")

        assert "must be a boolean" in str(exc_info.value)
        assert exc_info.value.key == "auto_start_server"

    @pytest.mark.asyncio
    async def test_coerces_string_variations_to_bool(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting coerces various string representations to boolean."""
        # Test "1" -> True
        result = await service.update_setting("auto_start_server", "1")
        assert result["value"] is True

        # Test "yes" -> True
        result = await service.update_setting("auto_start_server", "yes")
        assert result["value"] is True

        # Test "0" -> False
        result = await service.update_setting("auto_start_server", "0")
        assert result["value"] is False

        # Test "no" -> False
        result = await service.update_setting("auto_start_server", "no")
        assert result["value"] is False

    @pytest.mark.asyncio
    async def test_coerces_integer_to_bool(self, service: ApiSettingsService) -> None:
        """update_setting coerces non-boolean integer values to boolean."""
        # Lines 191-192: Integer (not boolean) coercion to bool
        result = await service.update_setting("auto_start_server", 1)
        assert result["value"] is True

        result = await service.update_setting("auto_start_server", 0)
        assert result["value"] is False

        result = await service.update_setting("auto_start_server", 42)
        assert result["value"] is True

    @pytest.mark.asyncio
    async def test_rejects_non_bool_non_int_non_str_for_boolean(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting rejects non-bool/non-int/non-str types for boolean."""
        # Lines 193-194: Fallback for types that aren't bool/int/str
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("auto_start_server", [1, 2, 3])

        assert "must be a boolean" in str(exc_info.value)


class TestIntegerCoercion:
    """Tests for additional integer coercion edge cases."""

    @pytest.mark.asyncio
    async def test_rejects_non_bool_non_int_non_str_for_integer(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting rejects non-bool/non-int/non-str types for integer."""
        # Lines 206-208: Fallback for types that aren't bool/int/str
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("mod_list_refresh_interval", {"key": "value"})

        assert "must be an integer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rejects_list_for_integer(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting rejects list values for integer fields."""
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("mod_list_refresh_interval", [100])

        assert "must be an integer" in str(exc_info.value)


class TestOtherTypeHandling:
    """Tests for handling field types other than bool and int."""

    @pytest.mark.asyncio
    async def test_handles_non_bool_non_int_field_types(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting handles fields with types other than bool/int."""
        # Line 208: validated_value = value (else branch for non-bool, non-int types)
        # This tests the fallback path for future field types (str, float, etc.)
        from pydantic import Field
        from pydantic.fields import FieldInfo
        from unittest.mock import patch

        # Create an extended model with a string field for testing
        class ExtendedApiSettings(ApiSettings):
            test_string_field: str = Field(default="default", description="Test string field")

        # Mock both the model_fields dict AND the ApiSettings class itself
        # to make the service think it's working with the extended model
        mock_field = FieldInfo(annotation=str, default="default", description="Test string field")

        # We need to patch at the module level where ApiSettingsService imports ApiSettings
        import vintagestory_api.services.api_settings as api_settings_module

        original_model = api_settings_module.ApiSettings

        try:
            # Replace ApiSettings with our extended model
            api_settings_module.ApiSettings = ExtendedApiSettings

            # Now update_setting will use ExtendedApiSettings
            result = await service.update_setting("test_string_field", "custom_value")

            # The value should be stored (line 208 will be executed for str type)
            assert result["key"] == "test_string_field"
            assert result["value"] == "custom_value"

        finally:
            # Restore the original model
            api_settings_module.ApiSettings = original_model


class TestSaveSettingsErrorHandling:
    """Tests for _save_settings error handling."""

    @pytest.mark.asyncio
    async def test_handles_permission_error_during_save(
        self, settings: Settings, tmp_path: Path
    ) -> None:
        """_save_settings handles permission errors and cleans up temp file."""
        # Lines 269-281: OSError handling with temp file cleanup
        service = ApiSettingsService(settings=settings)

        # Create the settings file as read-only directory (causes write error)
        service.settings_file.parent.mkdir(parents=True, exist_ok=True)

        # Write initial valid settings
        await service.update_setting("auto_start_server", True)

        # Make the settings file directory read-only to trigger OSError
        import os
        import stat

        # Store original permissions
        original_mode = service.settings_file.parent.stat().st_mode

        try:
            # Remove write permissions from parent directory
            service.settings_file.parent.chmod(stat.S_IRUSR | stat.S_IXUSR)

            # Attempt update should raise OSError
            with pytest.raises(OSError):
                await service.update_setting("auto_start_server", False)

        finally:
            # Restore permissions for cleanup
            service.settings_file.parent.chmod(original_mode)

    @pytest.mark.asyncio
    async def test_cleans_up_temp_file_on_rename_failure(
        self, settings: Settings, tmp_path: Path, monkeypatch
    ) -> None:
        """_save_settings cleans up temp file if rename fails."""
        import os
        from unittest.mock import Mock, patch

        service = ApiSettingsService(settings=settings)
        service.settings_file.parent.mkdir(parents=True, exist_ok=True)

        # Mock Path.rename to raise OSError
        original_rename = Path.rename

        def mock_rename(self, target):
            if str(self).endswith(".tmp"):
                raise OSError("Simulated rename failure")
            return original_rename(self, target)

        with patch.object(Path, "rename", mock_rename):
            with pytest.raises(OSError) as exc_info:
                await service.update_setting("auto_start_server", True)

            assert "Simulated rename failure" in str(exc_info.value)

            # Verify temp file was cleaned up
            temp_file = service.settings_file.with_suffix(".tmp")
            assert not temp_file.exists(), "Temp file should be cleaned up"

    @pytest.mark.asyncio
    async def test_handles_unlink_failure_during_cleanup(
        self, settings: Settings
    ) -> None:
        """_save_settings handles OSError when temp file unlink fails during cleanup."""
        # Lines 279-280: Nested exception handler for unlink failure
        from unittest.mock import Mock, patch

        service = ApiSettingsService(settings=settings)
        service.settings_file.parent.mkdir(parents=True, exist_ok=True)

        call_count = {"rename": 0, "unlink": 0}

        original_rename = Path.rename
        original_unlink = Path.unlink

        def mock_rename(self, target):
            call_count["rename"] += 1
            if str(self).endswith(".tmp"):
                raise OSError("Simulated rename failure")
            return original_rename(self, target)

        def mock_unlink(self, missing_ok=False):
            call_count["unlink"] += 1
            if str(self).endswith(".tmp"):
                # Simulate unlink also failing
                raise OSError("Simulated unlink failure")
            return original_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "rename", mock_rename):
            with patch.object(Path, "unlink", mock_unlink):
                # This should raise the rename OSError, not the unlink OSError
                with pytest.raises(OSError) as exc_info:
                    await service.update_setting("auto_start_server", True)

                assert "Simulated rename failure" in str(exc_info.value)
                # unlink should have been attempted despite failing
                assert call_count["unlink"] >= 1


class TestExceptionInitialization:
    """Tests for custom exception class initialization."""

    def test_api_setting_unknown_error_stores_key(self) -> None:
        """ApiSettingUnknownError stores the key attribute correctly."""
        # Lines 60-68: Test exception __init__ and attribute assignment
        error = ApiSettingUnknownError("unknown_setting")

        assert error.key == "unknown_setting"
        assert error.message == "Unknown API setting: 'unknown_setting'"
        assert "unknown_setting" in str(error)

    def test_api_setting_invalid_error_stores_attributes(self) -> None:
        """ApiSettingInvalidError stores key and reason attributes correctly."""
        # Lines 74-84: Test exception __init__ and attribute assignment
        error = ApiSettingInvalidError("my_setting", "value must be positive")

        assert error.key == "my_setting"
        assert error.reason == "value must be positive"
        assert error.message == "Invalid value for 'my_setting': value must be positive"
        assert "my_setting" in str(error)
        assert "value must be positive" in str(error)

    def test_exceptions_inherit_from_base_exception(self) -> None:
        """Custom exceptions properly inherit from Exception."""
        unknown_error = ApiSettingUnknownError("test")
        invalid_error = ApiSettingInvalidError("test", "reason")

        assert isinstance(unknown_error, Exception)
        assert isinstance(invalid_error, Exception)


class TestSettingsFileProperty:
    """Tests for settings_file property accessor."""

    def test_settings_file_property_returns_path(self, service: ApiSettingsService) -> None:
        """settings_file property returns the correct Path object."""
        # Lines 112-115: Test property getter
        file_path = service.settings_file

        assert isinstance(file_path, Path)
        assert file_path.name == "api-settings.json"
        assert "vsmanager" in str(file_path)
        assert "state" in str(file_path)


class TestServiceInitialization:
    """Tests for ApiSettingsService initialization."""

    def test_initialization_without_settings_creates_default(self) -> None:
        """Service initializes with default Settings() when settings=None."""
        # Line 108: Test settings or Settings() fallback
        service = ApiSettingsService(settings=None)

        assert service._settings is not None
        assert isinstance(service._settings, Settings)
        assert service._scheduler_callback is None

    def test_initialization_with_callback(self, settings: Settings) -> None:
        """Service stores scheduler_callback when provided."""
        # Lines 95-110: Test callback attribute assignment
        callback = MagicMock()
        service = ApiSettingsService(settings=settings, scheduler_callback=callback)

        assert service._scheduler_callback is callback


class TestBooleanStringMixedCase:
    """Tests for mixed-case boolean string coercion."""

    @pytest.mark.asyncio
    async def test_coerces_uppercase_true_to_bool(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting coerces uppercase 'TRUE' to boolean."""
        # Lines 182-190: Test case-insensitive boolean string matching
        result = await service.update_setting("auto_start_server", "TRUE")
        assert result["value"] is True

    @pytest.mark.asyncio
    async def test_coerces_uppercase_false_to_bool(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting coerces uppercase 'FALSE' to boolean."""
        result = await service.update_setting("auto_start_server", "FALSE")
        assert result["value"] is False

    @pytest.mark.asyncio
    async def test_coerces_mixed_case_true_to_bool(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting coerces mixed-case 'True' to boolean."""
        result = await service.update_setting("auto_start_server", "True")
        assert result["value"] is True

    @pytest.mark.asyncio
    async def test_coerces_mixed_case_false_to_bool(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting coerces mixed-case 'False' to boolean."""
        result = await service.update_setting("auto_start_server", "False")
        assert result["value"] is False

    @pytest.mark.asyncio
    async def test_coerces_uppercase_yes_to_bool(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting coerces uppercase 'YES' to boolean."""
        result = await service.update_setting("auto_start_server", "YES")
        assert result["value"] is True

    @pytest.mark.asyncio
    async def test_coerces_uppercase_no_to_bool(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting coerces uppercase 'NO' to boolean."""
        result = await service.update_setting("auto_start_server", "NO")
        assert result["value"] is False


class TestIntegerStringValidation:
    """Tests for integer string validation edge cases."""

    @pytest.mark.asyncio
    async def test_rejects_float_string_for_integer(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting rejects float strings like '123.45' for integer fields."""
        # Lines 200-204: Test float string rejection via int() conversion
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("mod_list_refresh_interval", "123.45")

        assert "must be an integer" in str(exc_info.value)
        assert exc_info.value.key == "mod_list_refresh_interval"

    @pytest.mark.asyncio
    async def test_rejects_scientific_notation_string_for_integer(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting rejects scientific notation strings for integer fields."""
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("mod_list_refresh_interval", "1.5e3")

        assert "must be an integer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_accepts_very_large_integer_string(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting accepts very large valid integer strings."""
        result = await service.update_setting("mod_list_refresh_interval", "999999999")
        assert result["value"] == 999999999


class TestLoggingVerification:
    """Tests for logging statements in critical paths."""

    @pytest.mark.asyncio
    async def test_logs_setting_update(
        self, service: ApiSettingsService
    ) -> None:
        """update_setting logs the setting change with old and new values."""
        # Lines 235-241: Test logger.info call with old/new values
        from unittest.mock import patch
        import vintagestory_api.services.api_settings as api_settings_module

        # Set initial value
        await service.update_setting("auto_start_server", True)

        # Mock logger to capture calls
        with patch.object(api_settings_module.logger, "info") as mock_logger:
            await service.update_setting("auto_start_server", False)

            # Verify logger.info was called (may be called multiple times for save + update)
            assert mock_logger.call_count >= 1
            # Check that one of the calls was for the setting update event
            call_args_list = [call[0][0] for call in mock_logger.call_args_list]
            assert "api_setting_updated" in call_args_list

    def test_logs_file_not_found(
        self, service: ApiSettingsService
    ) -> None:
        """get_settings logs debug message when file not found."""
        from unittest.mock import patch
        import vintagestory_api.services.api_settings as api_settings_module

        with patch.object(api_settings_module.logger, "debug") as mock_logger:
            service.get_settings()

            # Verify logger.debug was called with file not found event
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args
            assert call_args[0][0] == "api_settings_file_not_found"

    def test_logs_settings_loaded(
        self, service: ApiSettingsService
    ) -> None:
        """get_settings logs debug message when settings loaded successfully."""
        from unittest.mock import patch
        import vintagestory_api.services.api_settings as api_settings_module

        # Create settings file
        service.settings_file.parent.mkdir(parents=True, exist_ok=True)
        service.settings_file.write_text('{"auto_start_server": true}')

        with patch.object(api_settings_module.logger, "debug") as mock_logger:
            service.get_settings()

            # Verify logger.debug was called with settings loaded event
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args
            assert call_args[0][0] == "api_settings_loaded"


class TestValidationErrorPath:
    """Tests for Pydantic ValidationError handling after type coercion."""

    @pytest.mark.asyncio
    async def test_handles_validation_error_with_custom_validator(
        self, settings: Settings
    ) -> None:
        """update_setting handles ValidationError from Pydantic model validation."""
        # Lines 214-217: Test ValidationError exception handler
        # This path is triggered when Pydantic's model validation raises ValidationError
        # The existing test_rejects_negative_interval already covers this path,
        # but let's test it explicitly with validation that happens in model instantiation
        service = ApiSettingsService(settings=settings)

        # Test with a value that passes type coercion but fails Pydantic validation
        # Negative intervals fail Pydantic's ge=0 constraint
        with pytest.raises(ApiSettingInvalidError) as exc_info:
            await service.update_setting("mod_list_refresh_interval", -1)

        # Verify error is properly caught and converted
        assert exc_info.value.key == "mod_list_refresh_interval"
        # The error message should contain information from the ValidationError
        assert "mod_list_refresh_interval" in str(exc_info.value)


class TestDirectoryCreation:
    """Tests for directory creation edge cases."""

    @pytest.mark.asyncio
    async def test_handles_existing_directory_during_save(
        self, settings: Settings
    ) -> None:
        """_save_settings handles existing directory gracefully (exist_ok=True)."""
        # Line 261: Test mkdir with exist_ok=True when directory already exists
        service = ApiSettingsService(settings=settings)

        # Create directory first
        service.settings_file.parent.mkdir(parents=True, exist_ok=True)

        # This should succeed without error
        await service.update_setting("auto_start_server", True)

        # Verify file was created
        assert service.settings_file.exists()

        # Try again with directory already existing
        await service.update_setting("auto_start_server", False)

        # Should still succeed
        persisted = service.get_settings()
        assert persisted.auto_start_server is False
