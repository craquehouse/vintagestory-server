"""Tests for GameConfigService.

Story 6.2: Game Settings API
Story 17.6: settings with a game default known to the manager carry `default`

Tests are organized by task/AC:
- Task 1: GameConfigService class + LIVE_SETTINGS + get_settings() + update_setting()
"""

from __future__ import annotations

import copy
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from structlog.testing import capture_logs

from vintagestory_api.config import Settings
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.game_config import (
    LIVE_SETTINGS,
    REDACTED,
    SECRET_SETTING_KEYS,
    GameConfigService,
    ServerConfigInvalidError,
    ServerSetting,
    SettingEnvManagedError,
    SettingInfo,
    SettingUnknownError,
    SettingUpdateFailedError,
    SettingValueInvalidError,
    has_secret_value,
    is_secret_key,
    is_secret_value,
    redact_secrets,
)
from vintagestory_api.services.mod_update_alerts import DISCORD_HOSTS, is_discord_webhook
from vintagestory_api.services.server import ServerService

# Story 17.5: a made-up password for the redaction tests; never a real value.
SECRET = "pw-Zq9-monitor-must-not-see"


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
    # Story 25.3: no Entity Spawning value reported yet
    service.entity_spawning.record = None
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

    def test_server_setting_is_not_secret_by_default(self) -> None:
        """Story 17.5: a setting is a secret only when it says so."""
        setting = ServerSetting(key="TestSetting", value_type="string")
        assert setting.secret is False

    def test_password_is_the_only_secret_setting(self) -> None:
        """Story 17.5: Password is the one secret among the managed settings."""
        assert LIVE_SETTINGS["Password"].secret is True
        assert SECRET_SETTING_KEYS == frozenset({"Password"})
        others = [key for key, setting in LIVE_SETTINGS.items() if setting.secret]
        assert others == ["Password"]


# ==============================================================================
# Story 17.5: secret helpers
# ==============================================================================


class TestSecretHelpers:
    """Story 17.5: is_secret_key, has_secret_value and redact_secrets."""

    @pytest.mark.parametrize("key", ["Password", "password", "PASSWORD", "pAsSwOrD"])
    def test_secret_key_in_any_letter_case(self, key: str) -> None:
        """A secret setting's key is recognized in any letter case."""
        assert is_secret_key(key) is True

    @pytest.mark.parametrize(
        "key",
        [
            # One key per fragment (Epic 19 ADR-2 decision 2)
            "MyPassword",
            "db_passwd",
            "clientSecret",
            "bot_token",
            "ApiKey",
            "Private.Key",
            "AWS Access Key",
            "credentials",
            "WebhookUrl",
            "Authorization",
            # Unmanaged secret keys of serverconfig.json
            "StartupCommands",
            "startup_commands",
            # Separators and letter case are ignored
            "api_key",
            "api-key",
            "api.key",
            "API Key",
            "Passwords",
        ],
    )
    def test_secret_key_by_name(self, key: str) -> None:
        """Story 19.1 AC 6: secret settings, unmanaged secret keys and secret fragments."""
        assert is_secret_key(key) is True

    @pytest.mark.parametrize(
        "key",
        ["ServerName", "Pass", "", "ServerIdentifier", "Seed", "WorldSeed", "Key1", "Port"],
    )
    def test_other_keys_are_not_secret(self, key: str) -> None:
        """Story 19.1 AC 6: other key names are not secret keys."""
        assert is_secret_key(key) is False

    @pytest.mark.parametrize(
        "value",
        [
            "https://user:pass@host/x",
            "https://user@host/",
            "https://discord.com/api/webhooks/1/abc",
            "https://DiscordApp.com/api/webhooks/1/abc",
            "https://ptb.discord.com/api/webhooks/1/abc",
            "https://canary.discord.com/api/webhooks/1/abc",
            "https://PTB.Discord.com/api/webhooks/1/abc",
        ],
    )
    def test_secret_values(self, value: str) -> None:
        """Story 19.1 AC 7: URLs with user info and Discord webhook URLs are secrets."""
        assert is_secret_value(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            "https://example.com/api/webhooks/1",
            "https://discord.com/channels/1",
            "https://ptb.discord.com/channels/1",
            "https://canary.discord.com/api/other",
            "not a url",
            "",
            "http://[",
            "C:\\path",
        ],
    )
    def test_other_values_are_not_secret(self, value: str) -> None:
        """Story 19.1 AC 7: other URLs and strings are not secrets."""
        assert is_secret_value(value) is False

    @pytest.mark.parametrize("host", sorted(DISCORD_HOSTS))
    def test_redaction_and_the_webhook_sender_share_the_discord_hosts(self, host: str) -> None:
        """Story 21.3 AC 10: one set of Discord hosts (Epic 21 ADR-5 decision 1)."""
        url = f"https://{host}/api/webhooks/1/x"

        assert is_secret_value(url) is True
        assert is_discord_webhook(url) is True

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(None, False), ("", False), (SECRET, True), (" ", True), (0, True), (False, True)],
    )
    def test_has_secret_value(self, value: object, expected: bool) -> None:
        """Anything but null and the empty string counts as a set secret."""
        assert has_secret_value(value) is expected

    def test_redact_object(self) -> None:
        """Top-level secret keys with a value are replaced; other keys stay."""
        content = {"ServerName": "Test", "Password": SECRET, "Port": 42420}
        assert redact_secrets(content) == {
            "ServerName": "Test",
            "Password": REDACTED,
            "Port": 42420,
        }

    def test_redact_every_letter_case(self) -> None:
        """Password, password and PASSWORD are all redacted."""
        content = {"Password": "a1", "password": "b2", "PASSWORD": "c3"}
        assert redact_secrets(content) == {
            "Password": REDACTED,
            "password": REDACTED,
            "PASSWORD": REDACTED,
        }

    @pytest.mark.parametrize("value", [None, ""])
    def test_unset_secret_is_unchanged(self, value: object) -> None:
        """null and "" hold no secret and are returned as they are."""
        assert redact_secrets({"Password": value}) == {"Password": value}

    def test_non_string_secret_value_is_redacted(self) -> None:
        """A secret value that is not a string is redacted too."""
        assert redact_secrets({"Password": 123}) == {"Password": REDACTED}

    def test_nested_secret_is_redacted(self) -> None:
        """Story 19.1 AC 6: secret keys are redacted at every depth."""
        content = {"Other": {"Password": "nested"}}
        assert redact_secrets(content) == {"Other": {"Password": REDACTED}}

    def test_secret_keys_in_a_list_of_objects(self) -> None:
        """Story 19.1 AC 6: objects inside arrays are redacted too."""
        assert redact_secrets([{"Token": "t"}, {"ApiKey": "k"}]) == [
            {"Token": REDACTED},
            {"ApiKey": REDACTED},
        ]

    @pytest.mark.parametrize("value", [{"a": "b"}, ["a", "b"], 123, True])
    def test_whole_value_of_a_secret_key_is_redacted(self, value: object) -> None:
        """Story 19.1 AC 6: a secret key's value is replaced whatever its type."""
        assert redact_secrets({"Mod": {"bot_token": value}}) == {"Mod": {"bot_token": REDACTED}}

    @pytest.mark.parametrize("value", [None, ""])
    def test_unset_secret_at_depth_is_unchanged(self, value: object) -> None:
        """Story 19.1 AC 6: null and "" under a secret key stay at any depth."""
        content = {"Mod": [{"Password": value}]}
        assert redact_secrets(content) == content

    def test_secret_url_at_depth_in_an_array(self) -> None:
        """Story 19.1 AC 7: a secret URL is redacted under any key name, at any depth."""
        content = {"A": {"B": ["https://user:pass@host/", "https://example.com/"]}}
        assert redact_secrets(content) == {"A": {"B": [REDACTED, "https://example.com/"]}}

    def test_startup_commands_are_redacted(self) -> None:
        """Story 19.1 AC 7: StartupCommands is free text and a secret."""
        assert redact_secrets({"StartupCommands": "/op x"}) == {"StartupCommands": REDACTED}

    def test_other_keys_at_depth_are_unchanged(self) -> None:
        """Story 19.1 AC 6: Seed, WorldSeed and ServerName are unchanged at any depth."""
        content = {"Seed": "123", "World": {"WorldSeed": 4, "ServerName": "x", "Key1": "k"}}
        assert redact_secrets(content) == content

    def test_does_not_change_nested_argument(self) -> None:
        """Story 19.1: the parsed content is not modified in place, at any depth."""
        content: object = {"A": [{"Password": SECRET, "B": {"Token": SECRET}}]}
        before = copy.deepcopy(content)
        redact_secrets(content)
        assert content == before

    def test_fails_closed_on_recursion_limit(self) -> None:
        """Story 19.1: content too deep to walk is redacted as a whole."""
        content: list[object] = []
        inner = content
        for _ in range(5000):
            child: list[object] = []
            inner.append(child)
            inner = child
        inner.append(SECRET)

        assert redact_secrets(content) == REDACTED

    @pytest.mark.parametrize("content", [[1, 2], "text", 42, None, True])
    def test_arrays_and_scalars_are_unchanged(self, content: object) -> None:
        """Arrays and scalars that hold no secret are unchanged."""
        assert redact_secrets(content) == content

    def test_does_not_change_its_argument(self) -> None:
        """The parsed content is not modified in place."""
        content = {"Password": SECRET}
        redact_secrets(content)
        assert content == {"Password": SECRET}


class TestSettingInfoSecretFields:
    """Story 17.5: SettingInfo carries secret and configured."""

    def _info(self, secret: bool = False, configured: bool | None = None) -> SettingInfo:
        return SettingInfo(
            key="Password",
            value=None,
            value_type="string",
            live_update=True,
            requires_restart=False,
            env_managed=False,
            secret=secret,
            configured=configured,
        )

    def test_defaults_omit_both_fields(self) -> None:
        """A setting that is not secret carries neither field."""
        info = SettingInfo(
            key="ServerName",
            value="x",
            value_type="string",
            live_update=True,
            requires_restart=False,
            env_managed=False,
        )
        assert info.secret is False
        assert info.configured is None
        result = info.to_dict()
        assert "secret" not in result
        assert "configured" not in result

    def test_secret_is_included_when_set(self) -> None:
        """secret: true is in the dict when the setting is a secret."""
        result = self._info(secret=True).to_dict()
        assert result["secret"] is True
        assert "configured" not in result

    @pytest.mark.parametrize("configured", [True, False])
    def test_configured_is_included_when_not_none(self, configured: bool) -> None:
        """configured is in the dict whenever it is known, False included."""
        result = self._info(secret=True, configured=configured).to_dict()
        assert result["configured"] is configured


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

    def test_get_settings_returns_source_file(self, game_config_service: GameConfigService) -> None:
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

    def test_get_settings_file_not_found_raises(self, temp_settings: Settings) -> None:
        """get_settings raises FileNotFoundError when config doesn't exist."""
        service = GameConfigService(settings=temp_settings)

        with pytest.raises(FileNotFoundError):
            service.get_settings()

    def test_get_settings_to_dict(self, game_config_service: GameConfigService) -> None:
        """SettingsResponse.to_dict() produces valid dict for API response."""
        response = game_config_service.get_settings()
        result = response.to_dict()

        assert "settings" in result
        assert "source_file" in result
        assert "last_modified" in result
        assert isinstance(result["settings"], list)


def _write_config(config_file: Path, sample_config: dict[str, object], **changes: object) -> None:
    """Rewrite the temp serverconfig.json with some keys changed."""
    config_file.write_text(json.dumps({**sample_config, **changes}, indent=2))


def _password(response_settings: list[SettingInfo]) -> SettingInfo:
    return next(s for s in response_settings if s.key == "Password")


class TestGetSettingsSecrets:
    """Story 17.5 (FR186): get_settings withholds secrets unless the role is Admin."""

    def test_admin_receives_the_password(
        self,
        game_config_service: GameConfigService,
        config_file: Path,
        sample_config: dict[str, object],
    ) -> None:
        """Admin gets the value, secret is set and configured is not."""
        _write_config(config_file, sample_config, Password=SECRET)

        password = _password(game_config_service.get_settings("admin").settings)

        assert password.value == SECRET
        assert password.secret is True
        assert password.configured is None

    @pytest.mark.parametrize("role", [None, "monitor", "", "ADMIN", "Admin", "someone"])
    def test_any_other_role_gets_it_redacted(
        self,
        game_config_service: GameConfigService,
        config_file: Path,
        sample_config: dict[str, object],
        role: str | None,
    ) -> None:
        """AC 6: no role, Monitor and unknown roles all get the redacted form."""
        _write_config(config_file, sample_config, Password=SECRET)

        response = (
            game_config_service.get_settings()
            if role is None
            else game_config_service.get_settings(role)
        )
        password = _password(response.settings)

        assert password.value is None
        assert password.secret is True
        assert password.configured is True
        assert SECRET not in json.dumps(response.to_dict())

    @pytest.mark.parametrize("stored", [None, "", "missing"])
    def test_no_password_is_not_configured(
        self,
        game_config_service: GameConfigService,
        config_file: Path,
        sample_config: dict[str, object],
        stored: str | None,
    ) -> None:
        """AC 2: null, "" or a missing key reads as not configured."""
        config = dict(sample_config)
        if stored == "missing":
            del config["Password"]
        else:
            config["Password"] = stored
        config_file.write_text(json.dumps(config))

        monitor = _password(game_config_service.get_settings("monitor").settings)
        admin = _password(game_config_service.get_settings("admin").settings)

        assert monitor.value is None
        assert monitor.configured is False
        assert admin.value == (None if stored == "missing" else stored)
        assert admin.configured is None

    def test_lower_case_key_counts_as_configured(
        self,
        game_config_service: GameConfigService,
        config_file: Path,
        sample_config: dict[str, object],
    ) -> None:
        """A hand-edited "password" key is a set password; Admin reads Password as today."""
        config = {k: v for k, v in sample_config.items() if k != "Password"}
        config["password"] = SECRET
        config_file.write_text(json.dumps(config))

        monitor = game_config_service.get_settings("monitor")
        admin = game_config_service.get_settings("admin")

        assert _password(monitor.settings).configured is True
        assert SECRET not in json.dumps(monitor.to_dict())
        assert _password(admin.settings).value is None

    def test_other_settings_are_the_same_for_both_roles(
        self,
        game_config_service: GameConfigService,
        config_file: Path,
        sample_config: dict[str, object],
    ) -> None:
        """Only Password differs between the roles."""
        _write_config(config_file, sample_config, Password=SECRET)

        monitor = {s.key: s.to_dict() for s in game_config_service.get_settings().settings}
        admin = {s.key: s.to_dict() for s in game_config_service.get_settings("admin").settings}

        for key, setting in admin.items():
            if key == "Password":
                continue
            assert monitor[key] == setting
            assert "secret" not in setting
            assert "configured" not in setting


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
    async def test_reject_newlines_in_string(self, game_config_service: GameConfigService) -> None:
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
    async def test_accept_int_for_int_setting(self, game_config_service: GameConfigService) -> None:
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
# Story 16.8: settings with no value (VSS-7ed)
# ==============================================================================


def _stop_server(mock_server_service: MagicMock) -> None:
    mock_status = MagicMock()
    mock_status.state = ServerState.INSTALLED
    mock_server_service.get_server_status.return_value = mock_status


class TestNullableSettings:
    """Story 16.8: Description, Password and IP Address can have no value (null)."""

    def test_nullable_settings_are_those_with_a_null_default(self) -> None:
        """Exactly the settings whose VintageStory default is null accept null."""
        nullable = {key for key, setting in LIVE_SETTINGS.items() if setting.nullable}
        assert nullable == {"ServerDescription", "Password", "Ip"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("key", ["ServerDescription", "Password", "Ip"])
    @pytest.mark.parametrize("value", [None, "", "   "])
    async def test_cleared_value_is_stored_as_null(
        self,
        game_config_service: GameConfigService,
        mock_server_service: MagicMock,
        key: str,
        value: str | None,
    ) -> None:
        """null, an empty string or only spaces are stored as JSON null (server stopped)."""
        _stop_server(mock_server_service)

        result = await game_config_service.update_setting(key, value)

        config = json.loads(game_config_service.config_path.read_text())
        assert key in config
        assert config[key] is None
        assert result.value is None
        assert result.method == "file_update"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", [None, ""])
    async def test_cleared_password_uses_nopassword_when_running(
        self,
        game_config_service: GameConfigService,
        mock_server_service: MagicMock,
        value: str | None,
    ) -> None:
        """A cleared Password is applied with /serverconfig nopassword while running."""
        result = await game_config_service.update_setting("Password", value)

        mock_server_service.send_command.assert_called_once_with("/serverconfig nopassword")
        assert result.method == "console_command"
        assert result.value is None
        assert result.pending_restart is False

    @pytest.mark.asyncio
    async def test_cleared_description_is_written_to_file_with_restart_when_running(
        self,
        game_config_service: GameConfigService,
        mock_server_service: MagicMock,
        mock_pending_restart: MagicMock,
    ) -> None:
        """No console command clears the description: write the file, flag a restart."""
        result = await game_config_service.update_setting("ServerDescription", None)

        mock_server_service.send_command.assert_not_called()
        assert result.method == "file_update"
        assert result.pending_restart is True
        mock_pending_restart.require_restart.assert_called_once()
        assert "ServerDescription" in mock_pending_restart.require_restart.call_args[0][0]
        config = json.loads(game_config_service.config_path.read_text())
        assert config["ServerDescription"] is None

    @pytest.mark.asyncio
    async def test_cleared_ip_is_written_to_file_with_restart_when_running(
        self,
        game_config_service: GameConfigService,
        mock_server_service: MagicMock,
    ) -> None:
        """IP Address is restart-required, cleared or not."""
        result = await game_config_service.update_setting("Ip", "")

        mock_server_service.send_command.assert_not_called()
        assert result.method == "file_update"
        assert result.pending_restart is True
        config = json.loads(game_config_service.config_path.read_text())
        assert config["Ip"] is None

    @pytest.mark.asyncio
    async def test_non_empty_password_still_uses_password_command(
        self,
        game_config_service: GameConfigService,
        mock_server_service: MagicMock,
    ) -> None:
        """Setting a password is unchanged."""
        await game_config_service.update_setting("Password", "secret")

        mock_server_service.send_command.assert_called_once_with("/serverconfig password secret")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("key", ["ServerName", "WelcomeMessage", "Port", "AllowPvP"])
    async def test_null_is_rejected_for_other_settings(
        self,
        game_config_service: GameConfigService,
        mock_server_service: MagicMock,
        key: str,
    ) -> None:
        """null for a setting that cannot be empty is rejected, never stored as "None"."""
        _stop_server(mock_server_service)
        before = game_config_service.config_path.read_text()

        with pytest.raises(SettingValueInvalidError):
            await game_config_service.update_setting(key, None)

        assert game_config_service.config_path.read_text() == before
        mock_server_service.send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_welcome_message_is_still_an_empty_string(
        self,
        game_config_service: GameConfigService,
        mock_server_service: MagicMock,
    ) -> None:
        """Welcome Message is not nullable: an empty message stays an empty string."""
        _stop_server(mock_server_service)

        await game_config_service.update_setting("WelcomeMessage", "")

        config = json.loads(game_config_service.config_path.read_text())
        assert config["WelcomeMessage"] == ""

    @pytest.mark.asyncio
    async def test_cleared_password_redacted_in_console_command_log(
        self,
        game_config_service: GameConfigService,
    ) -> None:
        """The clear-command path logs the password as ***."""
        with patch("vintagestory_api.services.game_config.logger") as mock_logger:
            await game_config_service.update_setting("Password", None)

            calls = [
                c for c in mock_logger.info.call_args_list if "executing_console_command" in str(c)
            ]
            assert len(calls) == 1
            assert calls[0][1]["value"] == "***"


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
            calls = [c for c in mock_logger.info.call_args_list if "setting_updated" in str(c)]
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
        with patch(
            "vintagestory_api.services.game_config.json.dumps",
            side_effect=TypeError("Mock error"),
        ):
            with pytest.raises(SettingUpdateFailedError) as exc_info:
                await service.update_setting("ServerName", "Test")

            # Lines 727-729: exception handling
            assert exc_info.value.code == "SETTING_UPDATE_FAILED"
            assert "ServerName" in str(exc_info.value)


# ==============================================================================
# Story 17.6: the game's default for a setting with no value (FR188)
# ==============================================================================


class TestGameDefaults:
    """Story 17.6: a setting the game defaults carries `default`; no other does."""

    def test_server_setting_has_no_default_by_default(self) -> None:
        setting = ServerSetting(key="TestSetting", value_type="bool")
        assert setting.default is None

    def test_no_setting_has_a_default(self) -> None:
        """Story 25.3: EntitySpawning, the only one, now comes from the game (ADR-6)."""
        assert all(setting.default is None for setting in LIVE_SETTINGS.values())

    def test_no_secret_setting_has_a_default(self) -> None:
        assert all(setting.default is None for setting in LIVE_SETTINGS.values() if setting.secret)

    def test_setting_info_omits_default_when_none(self) -> None:
        info = SettingInfo(
            key="AllowPvP",
            value=None,
            value_type="bool",
            live_update=True,
            requires_restart=False,
            env_managed=False,
        )
        assert info.default is None
        assert "default" not in info.to_dict()

    def test_setting_info_includes_default_when_set(self) -> None:
        info = SettingInfo(
            key="EntitySpawning",
            value=None,
            value_type="bool",
            live_update=True,
            requires_restart=False,
            env_managed=False,
            default=False,
        )
        assert info.to_dict()["default"] is False

    @pytest.mark.parametrize("role", ["admin", "monitor"])
    def test_entity_spawning_in_the_file_is_never_read(
        self,
        game_config_service: GameConfigService,
        config_file: Path,
        role: str,
    ) -> None:
        """Story 25.3 (AC 7): the file's EntitySpawning (True in the sample) is ignored."""
        settings = {
            s["key"]: s for s in game_config_service.get_settings(role).to_dict()["settings"]
        }

        assert settings["EntitySpawning"]["value"] is None
        assert settings["EntitySpawning"]["source"] == "unknown"
        assert [key for key, s in settings.items() if "default" in s] == []


# ==============================================================================
# MaxClients for the Prometheus metrics (Story 22.2, Epic 22 ADR-4)
# ==============================================================================


class TestGetMaxClients:
    """get_max_clients reads MaxClients from serverconfig.json, nothing else."""

    def test_missing_file_is_none(self, temp_settings: Settings) -> None:
        assert GameConfigService(settings=temp_settings).get_max_clients() is None

    def test_whole_number_is_returned(self, temp_settings: Settings, config_file: Path) -> None:
        del config_file  # Fixture writes MaxClients 16
        assert GameConfigService(settings=temp_settings).get_max_clients() == 16

    @pytest.mark.parametrize(
        "config",
        [
            {},
            {"MaxClients": "16"},
            {"MaxClients": 16.5},
            {"MaxClients": True},
            {"MaxClients": None},
        ],
        ids=["missing-key", "string", "float", "bool", "null"],
    )
    def test_not_a_whole_number_is_none(
        self, temp_settings: Settings, config: dict[str, object]
    ) -> None:
        temp_settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
        (temp_settings.serverdata_dir / "serverconfig.json").write_text(json.dumps(config))
        assert GameConfigService(settings=temp_settings).get_max_clients() is None

    def test_invalid_json_raises(self, temp_settings: Settings) -> None:
        temp_settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
        (temp_settings.serverdata_dir / "serverconfig.json").write_text("{not json")
        # Story 25.1: the typed error of the one strict read (was json.JSONDecodeError)
        with pytest.raises(ServerConfigInvalidError):
            GameConfigService(settings=temp_settings).get_max_clients()


# ==============================================================================
# Story 22.7: restart-required settings saved while a game process lives
# ==============================================================================


class _FakeStdin:
    """The game's stdin: keeps what the console path writes."""

    def __init__(self) -> None:
        self.written: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        return None


class _LiveProcess:
    """A game process that is alive (`returncode` is None) for as long as the test needs."""

    def __init__(self) -> None:
        self.pid = 4242
        self.returncode: int | None = None
        self.stdin = _FakeStdin()


@pytest.fixture
def real_server_service(
    temp_settings: Settings, config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> ServerService:
    """A real ServerService on the temp dir: installed, stopped, no process."""
    temp_settings.server_dir.mkdir(parents=True, exist_ok=True)
    (temp_settings.server_dir / "VintagestoryServer.dll").touch()
    (temp_settings.server_dir / "VintagestoryLib.dll").touch()
    # get_server_status reads the disk space through Settings() from the environment
    monkeypatch.setattr("vintagestory_api.routers.health.get_disk_space_data", lambda: None)
    return ServerService(temp_settings)


def _set_process(
    monkeypatch: pytest.MonkeyPatch, service: ServerService, state: ServerState | None
) -> None:
    """Give the service a live process in `state`, or (None) no process at all."""
    if state is None:
        monkeypatch.setattr(service, "_process", None)
        monkeypatch.setattr(service, "_server_state", ServerState.INSTALLED)
        return
    monkeypatch.setattr(service, "_process", _LiveProcess())
    monkeypatch.setattr(service, "_server_state", state)


def _config_service(service: ServerService) -> GameConfigService:
    return GameConfigService(
        settings=service.settings,
        server_service=service,
        pending_restart_state=MagicMock(),
    )


def _pending_events(logs: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    return [log for log in logs if str(log["event"]).startswith("pending_config_edit")]


class TestPendingConfigEditTracking:
    """Story 22.7 Task 2: record and drop restart-required edits (ADR-15 decisions 1 and 4)."""

    @pytest.mark.asyncio
    async def test_port_while_running_is_recorded(
        self, real_server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_process(monkeypatch, real_server_service, ServerState.RUNNING)

        with capture_logs() as logs:
            result = await _config_service(real_server_service).update_setting("Port", 42421)

        assert result.to_dict() == {
            "key": "Port",
            "value": 42421,
            "method": "file_update",
            "pending_restart": True,
        }
        assert real_server_service.pending_config_edits.edits["Port"].value == 42421
        assert _pending_events(logs) == [
            {"event": "pending_config_edit_recorded", "key": "Port", "log_level": "info"}
        ]

    @pytest.mark.asyncio
    async def test_port_twice_while_running_keeps_the_newer(
        self, real_server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_process(monkeypatch, real_server_service, ServerState.RUNNING)
        service = _config_service(real_server_service)

        await service.update_setting("Port", 42421)
        await service.update_setting("Port", 42422)

        assert real_server_service.pending_config_edits.edits["Port"].value == 42422

    @pytest.mark.asyncio
    async def test_port_with_no_process_drops_the_edit(
        self, real_server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_process(monkeypatch, real_server_service, ServerState.RUNNING)
        service = _config_service(real_server_service)
        await service.update_setting("Port", 42421)

        _set_process(monkeypatch, real_server_service, None)
        with capture_logs() as logs:
            await service.update_setting("Port", 42423)

        assert real_server_service.pending_config_edits.edits == {}
        assert _pending_events(logs) == [
            {
                "event": "pending_config_edits_dropped",
                "keys": ["Port"],
                "reason": "changed_again",
                "log_level": "info",
            }
        ]
        assert json.loads(service.config_path.read_text())["Port"] == 42423

    @pytest.mark.asyncio
    async def test_port_with_no_process_records_nothing(
        self, real_server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC 5: the game reads the file at its next start; no state file is written."""
        _set_process(monkeypatch, real_server_service, None)

        with capture_logs() as logs:
            await _config_service(real_server_service).update_setting("Port", 42421)

        assert real_server_service.pending_config_edits.edits == {}
        assert _pending_events(logs) == []
        assert not real_server_service.pending_config_edits.path.exists()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", [ServerState.STOPPING, ServerState.STARTING])
    async def test_port_while_a_process_lives_in_transition_is_recorded(
        self,
        real_server_service: ServerService,
        monkeypatch: pytest.MonkeyPatch,
        state: ServerState,
    ) -> None:
        _set_process(monkeypatch, real_server_service, state)

        await _config_service(real_server_service).update_setting("Port", 42421)

        assert real_server_service.pending_config_edits.edits["Port"].value == 42421

    @pytest.mark.asyncio
    async def test_cleared_description_then_live_change_is_dropped(
        self, real_server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC 4: a pending description clear followed by a live description change."""
        _set_process(monkeypatch, real_server_service, ServerState.RUNNING)
        service = _config_service(real_server_service)

        cleared = await service.update_setting("ServerDescription", None)
        assert cleared.method == "file_update"
        assert real_server_service.pending_config_edits.edits["ServerDescription"].value is None

        with capture_logs() as logs:
            changed = await service.update_setting("ServerDescription", "Back again")

        assert changed.method == "console_command"
        assert real_server_service.pending_config_edits.edits == {}
        assert _pending_events(logs)[0]["reason"] == "changed_again"

    @pytest.mark.asyncio
    async def test_live_key_written_to_the_file_while_starting_drops_the_edit(
        self, real_server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A newer file write that is not itself recorded drops the key's edit."""
        _set_process(monkeypatch, real_server_service, ServerState.RUNNING)
        service = _config_service(real_server_service)
        await service.update_setting("ServerDescription", None)

        _set_process(monkeypatch, real_server_service, ServerState.STARTING)
        result = await service.update_setting("ServerDescription", "Starting text")

        assert result.method == "file_update"
        assert result.pending_restart is False
        assert real_server_service.pending_config_edits.edits == {}

    @pytest.mark.asyncio
    async def test_env_managed_port_is_refused_and_not_recorded(
        self, real_server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC 8."""
        _set_process(monkeypatch, real_server_service, ServerState.RUNNING)
        monkeypatch.setenv("VS_CFG_SERVER_PORT", "42420")

        with pytest.raises(SettingEnvManagedError):
            await _config_service(real_server_service).update_setting("Port", 42421)

        assert real_server_service.pending_config_edits.edits == {}
        assert not real_server_service.pending_config_edits.path.exists()

    @pytest.mark.asyncio
    async def test_failed_or_invalid_update_changes_no_edit(
        self, real_server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_process(monkeypatch, real_server_service, ServerState.RUNNING)
        service = _config_service(real_server_service)
        await service.update_setting("Port", 42421)
        before = real_server_service.pending_config_edits.edits

        with capture_logs() as logs:
            with pytest.raises(SettingValueInvalidError):
                await service.update_setting("Port", "not a port")
            service.config_path.unlink()
            with pytest.raises(SettingUpdateFailedError):
                await service.update_setting("Port", 42422)

        assert real_server_service.pending_config_edits.edits == before
        assert _pending_events(logs) == []

    @pytest.mark.asyncio
    async def test_no_server_service_records_nothing(
        self, temp_settings: Settings, config_file: Path
    ) -> None:
        service = GameConfigService(settings=temp_settings, server_service=None)

        with capture_logs() as logs:
            result = await service.update_setting("Port", 42421)

        assert result.method == "file_update"
        assert _pending_events(logs) == []
        assert not (temp_settings.state_dir / "pending-config-edits.json").exists()

    def test_no_secret_setting_can_be_recorded(self) -> None:
        """A secret is set and cleared by console command while running, never recorded."""
        for setting in LIVE_SETTINGS.values():
            if setting.secret:
                assert not setting.requires_restart
                assert setting.clear_command is not None

    @pytest.mark.asyncio
    async def test_new_log_lines_carry_no_value(
        self, real_server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_process(monkeypatch, real_server_service, ServerState.RUNNING)
        service = _config_service(real_server_service)

        with capture_logs() as logs:
            await service.update_setting("Port", 42421)
            _set_process(monkeypatch, real_server_service, None)
            await service.update_setting("Port", 42423)

        events = _pending_events(logs)
        assert [event["event"] for event in events] == [
            "pending_config_edit_recorded",
            "pending_config_edits_dropped",
        ]
        for event in events:
            assert "42421" not in repr(event)
            assert "42423" not in repr(event)
