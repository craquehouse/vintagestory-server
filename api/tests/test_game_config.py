"""Tests for GameConfigService.

Story 6.2: Game Settings API

Tests are organized by task/AC:
- Task 1: GameConfigService class + LIVE_SETTINGS + get_settings() + update_setting()
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.game_config import (
    LIVE_SETTINGS,
    GameConfigService,
    ServerSetting,
    SettingEnvManagedError,
    SettingUnknownError,
    SettingUpdateFailedError,
)


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    """Create Settings with temporary data directory."""
    with patch.dict(os.environ, {"VS_API_KEY_ADMIN": "test-key"}):
        settings = Settings(data_dir=tmp_path)
    return settings


@pytest.fixture
def sample_config() -> dict[str, object]:
    """Sample serverconfig.json content for testing."""
    return {
        "ServerName": "Test Server",
        "ServerDescription": "A test server",
        "WelcomeMessage": "Welcome!",
        "Port": 42420,
        "Ip": "",
        "MaxClients": 16,
        "MaxChunkRadius": 12,
        "Password": "",
        "AllowPvP": True,
        "AllowFireSpread": True,
        "AllowFallingBlocks": True,
        "EntitySpawning": True,
        "PassTimeWhenEmpty": False,
        "Upnp": False,
        "AdvertiseServer": True,
    }


@pytest.fixture
def config_file(temp_settings: Settings, sample_config: dict[str, object]) -> Path:
    """Create a sample serverconfig.json file."""
    config_path = temp_settings.serverdata_dir / "serverconfig.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(sample_config, indent=2))
    return config_path


@pytest.fixture
def mock_server_service() -> MagicMock:
    """Create a mock ServerService."""
    service = MagicMock()
    mock_status = MagicMock()
    mock_status.state = ServerState.RUNNING
    service.get_server_status.return_value = mock_status
    service.send_command = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_pending_restart() -> MagicMock:
    """Create a mock PendingRestartState."""
    state = MagicMock()
    state.pending_restart = False
    state.pending_changes = []
    return state


@pytest.fixture
def game_config_service(
    temp_settings: Settings,
    config_file: Path,
    mock_server_service: MagicMock,
    mock_pending_restart: MagicMock,
) -> GameConfigService:
    """Create GameConfigService with mocked dependencies."""
    return GameConfigService(
        settings=temp_settings,
        server_service=mock_server_service,
        pending_restart_state=mock_pending_restart,
    )


# ==============================================================================
# Task 1.1: GameConfigService class exists
# ==============================================================================


class TestGameConfigServiceClass:
    """Tests for GameConfigService class structure."""

    def test_game_config_service_exists(self) -> None:
        """GameConfigService class is importable."""
        from vintagestory_api.services.game_config import GameConfigService

        assert GameConfigService is not None

    def test_game_config_service_has_required_methods(
        self, game_config_service: GameConfigService
    ) -> None:
        """GameConfigService has required public methods."""
        assert hasattr(game_config_service, "get_settings")
        assert hasattr(game_config_service, "update_setting")
        assert callable(game_config_service.get_settings)
        assert callable(game_config_service.update_setting)


# ==============================================================================
# Task 1.2: LIVE_SETTINGS dict with ServerSetting model
# ==============================================================================


class TestLiveSettings:
    """Tests for LIVE_SETTINGS configuration dict."""

    def test_live_settings_exists(self) -> None:
        """LIVE_SETTINGS dict is defined."""
        assert LIVE_SETTINGS is not None
        assert isinstance(LIVE_SETTINGS, dict)

    def test_live_settings_has_expected_keys(self) -> None:
        """LIVE_SETTINGS contains expected setting keys."""
        expected_keys = [
            "ServerName",
            "ServerDescription",
            "WelcomeMessage",
            "MaxClients",
            "MaxChunkRadius",
            "Password",
            "AllowPvP",
            "AllowFireSpread",
            "AllowFallingBlocks",
            "EntitySpawning",
            "PassTimeWhenEmpty",
            "Upnp",
            "AdvertiseServer",
            "Port",
            "Ip",
        ]
        for key in expected_keys:
            assert key in LIVE_SETTINGS, f"Missing key: {key}"

    def test_live_settings_values_are_server_setting(self) -> None:
        """LIVE_SETTINGS values are ServerSetting instances."""
        for key, setting in LIVE_SETTINGS.items():
            assert isinstance(setting, ServerSetting), f"Invalid setting type for {key}"

    def test_live_update_settings_have_console_command(self) -> None:
        """Settings with live_update=True have console_command defined."""
        for key, setting in LIVE_SETTINGS.items():
            if setting.live_update:
                assert setting.console_command is not None, f"Missing console_command for {key}"

    def test_restart_required_settings_have_no_console_command(self) -> None:
        """Settings with requires_restart=True have no console_command."""
        for key, setting in LIVE_SETTINGS.items():
            if setting.requires_restart:
                assert setting.console_command is None, f"Unexpected console_command for {key}"
                assert setting.live_update is False, f"live_update should be False for {key}"

    def test_port_requires_restart(self) -> None:
        """Port setting requires restart (no live update)."""
        port_setting = LIVE_SETTINGS["Port"]
        assert port_setting.requires_restart is True
        assert port_setting.live_update is False
        assert port_setting.console_command is None

    def test_ip_requires_restart(self) -> None:
        """Ip setting requires restart (no live update)."""
        ip_setting = LIVE_SETTINGS["Ip"]
        assert ip_setting.requires_restart is True
        assert ip_setting.live_update is False
        assert ip_setting.console_command is None


class TestServerSettingModel:
    """Tests for ServerSetting model."""

    def test_server_setting_string_type(self) -> None:
        """ServerSetting with string type."""
        setting = ServerSetting(
            key="TestSetting",
            value_type="string",
            console_command='/serverconfig test "{value}"',
        )
        assert setting.key == "TestSetting"
        assert setting.value_type == "string"
        assert setting.live_update is True
        assert setting.requires_restart is False

    def test_server_setting_bool_format_true_false(self) -> None:
        """ServerSetting with true/false bool format."""
        setting = LIVE_SETTINGS["AllowPvP"]
        assert setting.value_type == "bool"
        assert setting.bool_format == "true_false"

    def test_server_setting_bool_format_0_1(self) -> None:
        """ServerSetting with 0/1 bool format (Upnp, AdvertiseServer)."""
        upnp = LIVE_SETTINGS["Upnp"]
        assert upnp.bool_format == "0_1"

        advertise = LIVE_SETTINGS["AdvertiseServer"]
        assert advertise.bool_format == "0_1"


# ==============================================================================
# Task 1.3: get_settings() method - returns enriched settings with metadata
# ==============================================================================


class TestGetSettings:
    """Tests for get_settings() method - AC 1."""

    def test_get_settings_returns_all_live_settings(
        self, game_config_service: GameConfigService
    ) -> None:
        """AC 1: get_settings returns all settings defined in LIVE_SETTINGS."""
        response = game_config_service.get_settings()

        assert len(response.settings) == len(LIVE_SETTINGS)
        keys = {s.key for s in response.settings}
        for expected_key in LIVE_SETTINGS.keys():
            assert expected_key in keys, f"Missing setting: {expected_key}"

    def test_get_settings_returns_source_file(
        self, game_config_service: GameConfigService
    ) -> None:
        """AC 1: Response includes source_file metadata."""
        response = game_config_service.get_settings()

        assert response.source_file == "serverconfig.json"

    def test_get_settings_returns_last_modified(
        self, game_config_service: GameConfigService
    ) -> None:
        """AC 1: Response includes last_modified timestamp."""
        response = game_config_service.get_settings()

        assert response.last_modified is not None

    def test_get_settings_includes_value_from_config(
        self, game_config_service: GameConfigService, sample_config: dict[str, object]
    ) -> None:
        """Settings include values from serverconfig.json."""
        response = game_config_service.get_settings()

        # Find ServerName in response
        server_name = next(s for s in response.settings if s.key == "ServerName")
        assert server_name.value == sample_config["ServerName"]

    def test_get_settings_includes_type_metadata(
        self, game_config_service: GameConfigService
    ) -> None:
        """Settings include type metadata."""
        response = game_config_service.get_settings()

        server_name = next(s for s in response.settings if s.key == "ServerName")
        assert server_name.type == "string"

        max_clients = next(s for s in response.settings if s.key == "MaxClients")
        assert max_clients.type == "int"

        allow_pvp = next(s for s in response.settings if s.key == "AllowPvP")
        assert allow_pvp.type == "bool"

    def test_get_settings_includes_live_update_flag(
        self, game_config_service: GameConfigService
    ) -> None:
        """Settings include live_update flag."""
        response = game_config_service.get_settings()

        server_name = next(s for s in response.settings if s.key == "ServerName")
        assert server_name.live_update is True

        port = next(s for s in response.settings if s.key == "Port")
        assert port.live_update is False

    def test_get_settings_includes_requires_restart_for_port(
        self, game_config_service: GameConfigService
    ) -> None:
        """Port setting includes requires_restart=True."""
        response = game_config_service.get_settings()

        port = next(s for s in response.settings if s.key == "Port")
        result_dict = port.to_dict()
        assert result_dict.get("requires_restart") is True

    def test_get_settings_env_managed_false_when_not_set(
        self, game_config_service: GameConfigService
    ) -> None:
        """Settings show env_managed=False when no VS_CFG_* env var is set."""
        response = game_config_service.get_settings()

        server_name = next(s for s in response.settings if s.key == "ServerName")
        assert server_name.env_managed is False
        assert server_name.env_var is None

    def test_get_settings_env_managed_true_when_env_var_set(
        self, game_config_service: GameConfigService
    ) -> None:
        """Settings show env_managed=True when VS_CFG_* env var is set."""
        with patch.dict(os.environ, {"VS_CFG_MAX_CLIENTS": "32"}):
            response = game_config_service.get_settings()

        max_clients = next(s for s in response.settings if s.key == "MaxClients")
        assert max_clients.env_managed is True
        assert max_clients.env_var == "VS_CFG_MAX_CLIENTS"

    def test_get_settings_file_not_found_raises(
        self, temp_settings: Settings
    ) -> None:
        """get_settings raises FileNotFoundError when config doesn't exist."""
        service = GameConfigService(settings=temp_settings)

        with pytest.raises(FileNotFoundError):
            service.get_settings()

    def test_get_settings_to_dict(
        self, game_config_service: GameConfigService
    ) -> None:
        """SettingsResponse.to_dict() produces valid dict for API response."""
        response = game_config_service.get_settings()
        result = response.to_dict()

        assert "settings" in result
        assert "source_file" in result
        assert "last_modified" in result
        assert isinstance(result["settings"], list)


# ==============================================================================
# Task 1.4 & 1.5: update_setting() with console command (live update path)
# ==============================================================================


class TestUpdateSettingLiveUpdate:
    """Tests for update_setting() with live update via console command - AC 2."""

    @pytest.mark.asyncio
    async def test_update_setting_uses_console_when_server_running(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """AC 2: When server is running, update uses console command."""
        result = await game_config_service.update_setting("ServerName", "New Name")

        assert result.method == "console_command"
        assert result.pending_restart is False
        mock_server_service.send_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_setting_console_command_format_string(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """String settings use unquoted console command format."""
        await game_config_service.update_setting("ServerName", "New Server Name")

        call_args = mock_server_service.send_command.call_args
        command = call_args[0][0]
        assert command == "/serverconfig name New Server Name"

    @pytest.mark.asyncio
    async def test_update_setting_console_command_format_int(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """Integer settings use unquoted console command format."""
        await game_config_service.update_setting("MaxClients", 32)

        call_args = mock_server_service.send_command.call_args
        command = call_args[0][0]
        assert command == "/serverconfig maxclients 32"

    @pytest.mark.asyncio
    async def test_update_setting_console_command_format_bool_true_false(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """Boolean settings using true/false format."""
        await game_config_service.update_setting("AllowPvP", True)

        call_args = mock_server_service.send_command.call_args
        command = call_args[0][0]
        assert command == "/serverconfig allowpvp true"

    @pytest.mark.asyncio
    async def test_update_setting_console_command_format_bool_0_1(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """Boolean settings using 0/1 format (Upnp, AdvertiseServer)."""
        await game_config_service.update_setting("Upnp", True)

        call_args = mock_server_service.send_command.call_args
        command = call_args[0][0]
        assert command == "/serverconfig upnp 1"

        mock_server_service.send_command.reset_mock()

        await game_config_service.update_setting("AdvertiseServer", False)
        call_args = mock_server_service.send_command.call_args
        command = call_args[0][0]
        assert command == "/serverconfig advertise 0"

    @pytest.mark.asyncio
    async def test_update_setting_returns_correct_result(
        self, game_config_service: GameConfigService
    ) -> None:
        """update_setting returns UpdateResult with correct data."""
        result = await game_config_service.update_setting("ServerName", "Test")

        assert result.key == "ServerName"
        assert result.value == "Test"
        assert result.method == "console_command"
        assert result.pending_restart is False

    @pytest.mark.asyncio
    async def test_update_setting_console_command_fails_raises(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """When console command fails, SettingUpdateFailedError is raised."""
        mock_server_service.send_command.return_value = False

        with pytest.raises(SettingUpdateFailedError) as exc_info:
            await game_config_service.update_setting("ServerName", "Test")

        assert exc_info.value.code == "SETTING_UPDATE_FAILED"


# ==============================================================================
# Task 1.6: update_setting() with file update (restart required path)
# ==============================================================================


class TestUpdateSettingFileUpdate:
    """Tests for update_setting() with file update - AC 3."""

    @pytest.mark.asyncio
    async def test_update_setting_uses_file_when_server_stopped(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """AC 3: When server is stopped, update uses file update."""
        mock_status = MagicMock()
        mock_status.state = ServerState.INSTALLED
        mock_server_service.get_server_status.return_value = mock_status

        result = await game_config_service.update_setting("ServerName", "New Name")

        assert result.method == "file_update"
        mock_server_service.send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_setting_uses_file_for_restart_required(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """AC 3: Restart-required settings use file update even when running."""
        # Server is running (default in mock_server_service fixture)
        result = await game_config_service.update_setting("Port", 42421)

        assert result.method == "file_update"
        assert result.pending_restart is True
        mock_server_service.send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_setting_file_update_writes_config(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """File update writes new value to serverconfig.json."""
        mock_status = MagicMock()
        mock_status.state = ServerState.INSTALLED
        mock_server_service.get_server_status.return_value = mock_status

        await game_config_service.update_setting("ServerName", "Updated Name")

        # Read config file and verify
        config = json.loads(game_config_service.config_path.read_text())
        assert config["ServerName"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_setting_file_update_atomic(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """File update uses atomic write pattern (no .tmp files left)."""
        mock_status = MagicMock()
        mock_status.state = ServerState.INSTALLED
        mock_server_service.get_server_status.return_value = mock_status

        await game_config_service.update_setting("ServerName", "Atomic Test")

        # Verify no temp files
        temp_files = list(game_config_service.config_path.parent.glob("*.tmp"))
        assert len(temp_files) == 0

    @pytest.mark.asyncio
    async def test_update_setting_port_sets_pending_restart(
        self, game_config_service: GameConfigService, mock_pending_restart: MagicMock
    ) -> None:
        """Updating Port calls require_restart()."""
        await game_config_service.update_setting("Port", 42421)

        mock_pending_restart.require_restart.assert_called_once()
        call_args = mock_pending_restart.require_restart.call_args[0][0]
        assert "Port" in call_args


# ==============================================================================
# Task 1.7-1.10: Tests for error scenarios
# ==============================================================================


class TestUpdateSettingErrors:
    """Tests for update_setting() error handling - AC 4."""

    @pytest.mark.asyncio
    async def test_update_unknown_setting_raises(
        self, game_config_service: GameConfigService
    ) -> None:
        """Updating unknown setting raises SettingUnknownError."""
        with pytest.raises(SettingUnknownError) as exc_info:
            await game_config_service.update_setting("UnknownSetting", "value")

        assert exc_info.value.code == "SETTING_UNKNOWN"
        assert "UnknownSetting" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_env_managed_setting_raises(
        self, temp_settings: Settings, config_file: Path
    ) -> None:
        """AC 4: Updating env-managed setting raises SettingEnvManagedError."""
        with patch.dict(os.environ, {"VS_CFG_MAX_CLIENTS": "32"}):
            service = GameConfigService(
                settings=temp_settings,
                block_env_managed_settings=True,
            )

            with pytest.raises(SettingEnvManagedError) as exc_info:
                await service.update_setting("MaxClients", 64)

        assert exc_info.value.code == "SETTING_ENV_MANAGED"
        assert "MaxClients" in str(exc_info.value)
        assert "VS_CFG_MAX_CLIENTS" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_env_managed_setting_allowed_when_disabled(
        self,
        temp_settings: Settings,
        config_file: Path,
        mock_server_service: MagicMock,
    ) -> None:
        """When block_env_managed_settings=False, env-managed settings can be updated."""
        with patch.dict(os.environ, {"VS_CFG_MAX_CLIENTS": "32"}):
            service = GameConfigService(
                settings=temp_settings,
                server_service=mock_server_service,
                block_env_managed_settings=False,
            )

            # Should not raise
            result = await service.update_setting("MaxClients", 64)
            assert result.value == 64


class TestEnvManagedDetection:
    """Tests for env-managed setting detection."""

    def test_env_managed_detected_for_set_vars(
        self, game_config_service: GameConfigService
    ) -> None:
        """Settings are detected as env_managed when VS_CFG_* var is set."""
        with patch.dict(os.environ, {"VS_CFG_SERVER_NAME": "EnvServer"}):
            response = game_config_service.get_settings()

        server_name = next(s for s in response.settings if s.key == "ServerName")
        assert server_name.env_managed is True
        assert server_name.env_var == "VS_CFG_SERVER_NAME"

    def test_env_managed_not_detected_for_unset_vars(
        self, game_config_service: GameConfigService
    ) -> None:
        """Settings are NOT env_managed when VS_CFG_* var is not set."""
        # Ensure no env vars are set
        with patch.dict(os.environ, {}, clear=True):
            # Need to re-patch the API key
            with patch.dict(os.environ, {"VS_API_KEY_ADMIN": "test-key"}):
                response = game_config_service.get_settings()

        for setting in response.settings:
            assert setting.env_managed is False
            assert setting.env_var is None


class TestServerServiceIntegration:
    """Tests for ServerService integration."""

    def test_is_server_running_with_service(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """is_server_running() returns True when server is running."""
        mock_status = MagicMock()
        mock_status.state = ServerState.RUNNING
        mock_server_service.get_server_status.return_value = mock_status
        assert game_config_service.is_server_running() is True

    def test_is_server_running_without_service(
        self, temp_settings: Settings, config_file: Path
    ) -> None:
        """is_server_running() returns False when no ServerService."""
        service = GameConfigService(settings=temp_settings, server_service=None)
        assert service.is_server_running() is False

    def test_is_server_running_when_stopped(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """is_server_running() returns False when server is stopped."""
        mock_status = MagicMock()
        mock_status.state = ServerState.INSTALLED
        mock_server_service.get_server_status.return_value = mock_status
        assert game_config_service.is_server_running() is False


class TestUpdateResultModel:
    """Tests for UpdateResult model."""

    def test_update_result_to_dict(self) -> None:
        """UpdateResult.to_dict() produces valid dict."""
        from vintagestory_api.services.game_config import UpdateResult

        result = UpdateResult(
            key="ServerName",
            value="Test",
            method="console_command",
            pending_restart=False,
        )
        result_dict = result.to_dict()

        assert result_dict["key"] == "ServerName"
        assert result_dict["value"] == "Test"
        assert result_dict["method"] == "console_command"
        assert result_dict["pending_restart"] is False


# ==============================================================================
# Security tests: Command injection prevention
# ==============================================================================


class TestCommandInjectionPrevention:
    """Tests for command injection prevention - Review Follow-up."""

    @pytest.mark.asyncio
    async def test_reject_double_quotes_in_string(
        self, game_config_service: GameConfigService
    ) -> None:
        """String values with double quotes are rejected to prevent command injection."""
        from vintagestory_api.services.game_config import SettingValueInvalidError

        with pytest.raises(SettingValueInvalidError) as exc_info:
            await game_config_service.update_setting("ServerName", 'Test"; /stop')

        assert exc_info.value.code == "SETTING_VALUE_INVALID"
        assert "double quotes" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_reject_backslashes_in_string(
        self, game_config_service: GameConfigService
    ) -> None:
        """String values with backslashes are rejected."""
        from vintagestory_api.services.game_config import SettingValueInvalidError

        with pytest.raises(SettingValueInvalidError) as exc_info:
            await game_config_service.update_setting("ServerName", "Test\\nEscaped")

        assert exc_info.value.code == "SETTING_VALUE_INVALID"
        assert "backslash" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_reject_newlines_in_string(
        self, game_config_service: GameConfigService
    ) -> None:
        """String values with newlines are rejected."""
        from vintagestory_api.services.game_config import SettingValueInvalidError

        with pytest.raises(SettingValueInvalidError) as exc_info:
            await game_config_service.update_setting("ServerName", "Line1\nLine2")

        assert exc_info.value.code == "SETTING_VALUE_INVALID"
        assert "newline" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_reject_carriage_returns_in_string(
        self, game_config_service: GameConfigService
    ) -> None:
        """String values with carriage returns are rejected."""
        from vintagestory_api.services.game_config import SettingValueInvalidError

        with pytest.raises(SettingValueInvalidError) as exc_info:
            await game_config_service.update_setting("ServerName", "Line1\rLine2")

        assert exc_info.value.code == "SETTING_VALUE_INVALID"
        assert "newline" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_accept_safe_string_value(
        self, game_config_service: GameConfigService, mock_server_service: MagicMock
    ) -> None:
        """Safe string values without dangerous characters are accepted."""
        result = await game_config_service.update_setting(
            "ServerName", "My Awesome Server - Version 2.0!"
        )

        assert result.value == "My Awesome Server - Version 2.0!"


# ==============================================================================
# Type validation tests
# ==============================================================================


class TestTypeValidation:
    """Tests for input type validation - Review Follow-up."""

    @pytest.mark.asyncio
    async def test_reject_string_for_int_setting(
        self, game_config_service: GameConfigService
    ) -> None:
        """String value for int setting is rejected."""
        from vintagestory_api.services.game_config import SettingValueInvalidError

        with pytest.raises(SettingValueInvalidError) as exc_info:
            await game_config_service.update_setting("MaxClients", "not-a-number")

        assert exc_info.value.code == "SETTING_VALUE_INVALID"

    @pytest.mark.asyncio
    async def test_accept_int_for_int_setting(
        self, game_config_service: GameConfigService
    ) -> None:
        """Int value for int setting is accepted."""
        result = await game_config_service.update_setting("MaxClients", 32)

        assert result.value == 32

    @pytest.mark.asyncio
    async def test_accept_string_that_parses_to_int(
        self, game_config_service: GameConfigService
    ) -> None:
        """String that can be parsed to int is coerced."""
        result = await game_config_service.update_setting("MaxClients", "64")

        assert result.value == 64
        assert isinstance(result.value, int)

    @pytest.mark.asyncio
    async def test_reject_string_for_bool_setting(
        self, game_config_service: GameConfigService
    ) -> None:
        """Invalid string value for bool setting is rejected."""
        from vintagestory_api.services.game_config import SettingValueInvalidError

        with pytest.raises(SettingValueInvalidError) as exc_info:
            await game_config_service.update_setting("AllowPvP", "maybe")

        assert exc_info.value.code == "SETTING_VALUE_INVALID"

    @pytest.mark.asyncio
    async def test_accept_bool_for_bool_setting(
        self, game_config_service: GameConfigService
    ) -> None:
        """Bool value for bool setting is accepted."""
        result = await game_config_service.update_setting("AllowPvP", True)

        assert result.value is True

    @pytest.mark.asyncio
    async def test_accept_string_true_for_bool_setting(
        self, game_config_service: GameConfigService
    ) -> None:
        """String 'true' for bool setting is coerced to True."""
        result = await game_config_service.update_setting("AllowPvP", "true")

        assert result.value is True
        assert isinstance(result.value, bool)


# ==============================================================================
# Password redaction tests
# ==============================================================================


class TestPasswordRedaction:
    """Tests for password redaction in logs - Review Follow-up."""

    @pytest.mark.asyncio
    async def test_password_value_redacted_in_console_command_log(
        self,
        game_config_service: GameConfigService,
        mock_server_service: MagicMock,
    ) -> None:
        """Password values are redacted in console command logs."""
        with patch("vintagestory_api.services.game_config.logger") as mock_logger:
            await game_config_service.update_setting("Password", "my-secret-password")

            # Check that logger.info was called with value="***"
            calls = [
                c for c in mock_logger.info.call_args_list if "executing_console_command" in str(c)
            ]
            assert len(calls) > 0
            for call in calls:
                kwargs = call[1]
                if "value" in kwargs:
                    assert kwargs["value"] == "***", "Password should be redacted as ***"

    @pytest.mark.asyncio
    async def test_password_value_redacted_in_file_update_log(
        self,
        game_config_service: GameConfigService,
        mock_server_service: MagicMock,
    ) -> None:
        """Password values are redacted in file update logs."""
        # Make server stopped so it uses file update
        mock_status = MagicMock()
        mock_status.state = ServerState.INSTALLED
        mock_server_service.get_server_status.return_value = mock_status

        with patch("vintagestory_api.services.game_config.logger") as mock_logger:
            await game_config_service.update_setting("Password", "my-secret-password")

            # Check that logger.info was called with value="***"
            calls = [
                c for c in mock_logger.info.call_args_list if "setting_updated" in str(c)
            ]
            assert len(calls) > 0
            for call in calls:
                kwargs = call[1]
                if "value" in kwargs:
                    assert kwargs["value"] == "***", "Password should be redacted as ***"


# ==============================================================================
# Additional coverage tests for missing lines
# ==============================================================================


class TestMissingCoverage:
    """Tests to cover missing lines identified in coverage report."""

    def test_setting_info_to_dict_includes_env_var(
        self, game_config_service: GameConfigService
    ) -> None:
        """SettingInfo.to_dict() includes env_var when present (line 223)."""
        with patch.dict(os.environ, {"VS_CFG_SERVER_NAME": "EnvServer"}):
            response = game_config_service.get_settings()

        server_name = next(s for s in response.settings if s.key == "ServerName")
        result_dict = server_name.to_dict()

        # Line 223: result["env_var"] = self.env_var
        assert "env_var" in result_dict
        assert result_dict["env_var"] == "VS_CFG_SERVER_NAME"

    @pytest.mark.asyncio
    async def test_validate_float_value(
        self, temp_settings: Settings, config_file: Path, mock_server_service: MagicMock
    ) -> None:
        """Test float value type validation (lines 496-497)."""
        # Create a float setting for testing
        from vintagestory_api.services.game_config import LIVE_SETTINGS, ServerSetting

        # Add a temporary float setting to test
        LIVE_SETTINGS["TestFloat"] = ServerSetting(
            key="TestFloat",
            value_type="float",
            console_command="/test {value}",
            live_update=True,
        )

        try:
            # Load config and add TestFloat
            config = json.loads(config_file.read_text())
            config["TestFloat"] = 1.5
            config_file.write_text(json.dumps(config, indent=2))

            service = GameConfigService(
                settings=temp_settings,
                server_service=mock_server_service,
            )

            # Test with int value (should convert to float) - lines 496-497
            result = await service.update_setting("TestFloat", 42)
            assert result.value == 42.0
            assert isinstance(result.value, float)

            # Test with float value
            result = await service.update_setting("TestFloat", 3.14)
            assert result.value == 3.14
            assert isinstance(result.value, float)
        finally:
            # Clean up the temporary setting
            if "TestFloat" in LIVE_SETTINGS:
                del LIVE_SETTINGS["TestFloat"]

    @pytest.mark.asyncio
    async def test_execute_console_command_no_console_command(
        self, game_config_service: GameConfigService
    ) -> None:
        """Test error when setting has no console command (line 630)."""
        # Create a setting without a console command
        from vintagestory_api.services.game_config import LIVE_SETTINGS, ServerSetting

        LIVE_SETTINGS["TestNoCmd"] = ServerSetting(
            key="TestNoCmd",
            value_type="string",
            console_command=None,  # No console command
            live_update=True,
        )

        try:
            # Load config and add TestNoCmd
            config = json.loads(game_config_service.config_path.read_text())
            config["TestNoCmd"] = "test"
            game_config_service.config_path.write_text(json.dumps(config, indent=2))

            # This should trigger line 630
            with pytest.raises(SettingUpdateFailedError) as exc_info:
                await game_config_service.update_setting("TestNoCmd", "value")

            assert "No console command available" in str(exc_info.value)
        finally:
            # Clean up
            if "TestNoCmd" in LIVE_SETTINGS:
                del LIVE_SETTINGS["TestNoCmd"]

    @pytest.mark.asyncio
    async def test_execute_console_command_no_server_service(
        self, temp_settings: Settings, config_file: Path
    ) -> None:
        """Test error when ServerService is not available (line 633)."""
        # Create service without server_service but mock is_server_running to return True
        service = GameConfigService(
            settings=temp_settings,
            server_service=None,
        )

        # Patch is_server_running to return True so it tries console command path
        with patch.object(service, "is_server_running", return_value=True):
            # Since server_service is None, line 633 should be triggered
            with pytest.raises(SettingUpdateFailedError) as exc_info:
                await service.update_setting("ServerName", "Test")

            assert "ServerService not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_config_file_exception_handling(
        self, temp_settings: Settings, config_file: Path, mock_server_service: MagicMock
    ) -> None:
        """Test exception handling in _update_config_file (lines 727-729)."""
        mock_status = MagicMock()
        mock_status.state = ServerState.INSTALLED
        mock_server_service.get_server_status.return_value = mock_status

        service = GameConfigService(
            settings=temp_settings,
            server_service=mock_server_service,
        )

        # Patch json.dumps to raise an exception to trigger error handling
        with patch("vintagestory_api.services.game_config.json.dumps", side_effect=TypeError("Mock error")):
            with pytest.raises(SettingUpdateFailedError) as exc_info:
                await service.update_setting("ServerName", "Test")

            # Lines 727-729: exception handling
            assert exc_info.value.code == "SETTING_UPDATE_FAILED"
            assert "ServerName" in str(exc_info.value)
