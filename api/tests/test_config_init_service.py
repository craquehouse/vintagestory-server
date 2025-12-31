"""Tests for ConfigInitService.

Story 6.1: ConfigInitService and Template

Tests are organized by task/AC:
- Task 1: ConfigInitService class creation (AC 1, 4, 5)
- Task 2: Environment variable override application (AC 2, 3, 5)
- Task 3: Integration with ServerService (AC 1)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.services.config_init_service import ConfigInitService

if TYPE_CHECKING:
    from vintagestory_api.services.server import ServerService


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    """Create Settings with temporary data directory."""
    # Create minimal settings pointing to temp directory
    with patch.dict(os.environ, {"VS_API_KEY_ADMIN": "test-key"}):
        settings = Settings(data_dir=tmp_path)
    return settings


@pytest.fixture
def config_service(temp_settings: Settings) -> ConfigInitService:
    """Create ConfigInitService with temporary settings."""
    return ConfigInitService(settings=temp_settings)


@pytest.fixture
def sample_template(tmp_path: Path) -> dict[str, object]:
    """Sample template for testing."""
    return {
        "ServerName": "Test Server",
        "Port": 42420,
        "MaxClients": 16,
        "AllowPvP": True,
        "TickTime": 33.333,
        "WorldConfig": {
            "WorldName": "Test World",
            "AllowCreativeMode": False,
        },
    }


# ==============================================================================
# Task 1: ConfigInitService class + tests (AC: 1, 4, 5)
# ==============================================================================


class TestNeedsInitialization:
    """Tests for needs_initialization() method - AC 1, 4."""

    def test_needs_initialization_when_config_missing(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 1: When no serverconfig.json exists, needs_initialization returns True."""
        # Config file doesn't exist yet
        assert not config_service.config_path.exists()
        assert config_service.needs_initialization() is True

    def test_needs_initialization_when_config_exists(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 4: When serverconfig.json exists, needs_initialization returns False."""
        # Create the serverdata directory and config file
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)
        config_service.config_path.write_text('{"ServerName": "Existing"}')

        assert config_service.config_path.exists()
        assert config_service.needs_initialization() is False


class TestIdempotency:
    """Tests for config idempotency - AC 4."""

    def test_existing_config_not_overwritten(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 4: Existing config is NOT overwritten on initialize_config()."""
        # Create existing config with specific content
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)
        existing_content = {"ServerName": "My Existing Server", "Port": 12345}
        config_service.config_path.write_text(json.dumps(existing_content))

        # Try to initialize - should be skipped
        config_service.initialize_config()

        # Verify content unchanged
        actual = json.loads(config_service.config_path.read_text())
        assert actual["ServerName"] == "My Existing Server"
        assert actual["Port"] == 12345

    def test_initialize_creates_config_from_template(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 1: When config doesn't exist, initialize_config creates it from template."""
        # Ensure parent dir exists
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize config
        config_service.initialize_config()

        # Verify config was created
        assert config_service.config_path.exists()

        # Verify it contains template content
        config = json.loads(config_service.config_path.read_text())
        assert "ServerName" in config
        assert config["ServerName"] == "Vintage Story Server"  # Template default


class TestAtomicWrite:
    """Tests for atomic write pattern."""

    def test_atomic_write_no_partial_files(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Config writes use atomic temp-file-then-rename pattern."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize config
        config_service.initialize_config()

        # Verify config exists
        assert config_service.config_path.exists()

        # Verify no temp files left behind
        temp_files = list(config_service.config_path.parent.glob("*.tmp"))
        assert len(temp_files) == 0


class TestConfigPath:
    """Tests for config path resolution."""

    def test_config_path_in_serverdata_dir(
        self,
        config_service: ConfigInitService,
        temp_settings: Settings,
    ) -> None:
        """Config path resolves to serverdata/serverconfig.json."""
        expected = temp_settings.serverdata_dir / "serverconfig.json"
        assert config_service.config_path == expected


# ==============================================================================
# Task 2: Environment variable override tests (AC: 2, 3, 5)
# ==============================================================================


class TestEnvVarOverrides:
    """Tests for environment variable override application."""

    def test_string_override(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 2: VS_CFG_SERVER_NAME overrides ServerName as string."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_SERVER_NAME": "My Custom Server"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["ServerName"] == "My Custom Server"

    def test_integer_override(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 3: VS_CFG_MAX_CLIENTS="32" becomes integer 32 in config."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_MAX_CLIENTS": "32"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["MaxClients"] == 32
        assert isinstance(config["MaxClients"], int)

    def test_boolean_override_true(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Boolean env vars are converted correctly (true)."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_ALLOW_PVP": "true"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["AllowPvP"] is True
        assert isinstance(config["AllowPvP"], bool)

    def test_boolean_override_false(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Boolean env vars are converted correctly (false)."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_ALLOW_PVP": "false"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["AllowPvP"] is False
        assert isinstance(config["AllowPvP"], bool)

    def test_float_override(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Float env vars are converted correctly."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_TICK_TIME": "50.0"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["TickTime"] == 50.0
        assert isinstance(config["TickTime"], float)

    def test_nested_key_override(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Nested keys like WorldConfig.AllowCreativeMode work correctly."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_ALLOW_CREATIVE_MODE": "true"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["WorldConfig"]["AllowCreativeMode"] is True

    def test_nested_world_name_override(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Nested string key WorldConfig.WorldName works correctly."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_WORLD_NAME": "My Epic World"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["WorldConfig"]["WorldName"] == "My Epic World"

    def test_multiple_overrides(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Multiple env vars are all applied."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(
            os.environ,
            {
                "VS_CFG_SERVER_NAME": "Multi-Override Server",
                "VS_CFG_MAX_CLIENTS": "48",
                "VS_CFG_ALLOW_PVP": "false",
            },
        ):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["ServerName"] == "Multi-Override Server"
        assert config["MaxClients"] == 48
        assert config["AllowPvP"] is False


class TestInvalidEnvVarHandling:
    """Tests for graceful handling of invalid env var values - AC 5."""

    def test_invalid_integer_uses_default(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 5: Invalid integer value logged as warning, template default used."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        # "abc" is not a valid integer
        with patch.dict(os.environ, {"VS_CFG_MAX_CLIENTS": "abc"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        # Should use template default of 16, not crash
        assert config["MaxClients"] == 16

    def test_invalid_boolean_uses_default(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 5: Invalid boolean value logged as warning, template default used."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        # "maybe" is not a valid boolean
        with patch.dict(os.environ, {"VS_CFG_ALLOW_PVP": "maybe"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        # Should use template default (True), not crash
        assert config["AllowPvP"] is True

    def test_invalid_float_uses_default(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 5: Invalid float value logged as warning, template default used."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        # "not-a-float" is not valid
        with patch.dict(os.environ, {"VS_CFG_TICK_TIME": "not-a-float"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        # Should use template default, not crash
        assert config["TickTime"] == 33.333332  # Template default

    def test_mixed_valid_invalid_overrides(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """AC 5: Valid overrides applied even when some are invalid."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(
            os.environ,
            {
                "VS_CFG_SERVER_NAME": "Valid Server Name",  # Valid string
                "VS_CFG_MAX_CLIENTS": "invalid",  # Invalid int
                "VS_CFG_SERVER_PORT": "25565",  # Valid int
            },
        ):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        # Valid overrides applied
        assert config["ServerName"] == "Valid Server Name"
        assert config["Port"] == 25565
        # Invalid override uses template default
        assert config["MaxClients"] == 16


class TestEnvVarFiltering:
    """Tests for env var filtering behavior via public interface."""

    def test_only_mapped_env_vars_applied(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Only VS_CFG_* vars with mappings in ENV_VAR_MAP are applied."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(
            os.environ,
            {
                "VS_CFG_SERVER_NAME": "Mapped Var",  # Mapped in ENV_VAR_MAP
                "VS_CFG_UNKNOWN_VAR": "ignored",  # Not in ENV_VAR_MAP
                "OTHER_VAR": "also ignored",  # Not VS_CFG_* prefix
            },
            clear=False,
        ):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        # Mapped var is applied
        assert config["ServerName"] == "Mapped Var"
        # Unknown vars should not appear in config
        assert "VS_CFG_UNKNOWN_VAR" not in str(config)
        assert "OTHER_VAR" not in str(config)


class TestQuoteStripping:
    """Tests for surrounding quote stripping from env var values.

    Docker-compose users often write: VS_CFG_SERVER_NAME="My Server"
    but the quotes are included literally. We strip them for better UX.
    """

    def test_double_quotes_stripped(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Double-quoted values have quotes stripped."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_SERVER_NAME": '"My Docker Server"'}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["ServerName"] == "My Docker Server"

    def test_single_quotes_stripped(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Single-quoted values have quotes stripped."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_SERVER_NAME": "'Single Quoted'"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["ServerName"] == "Single Quoted"

    def test_mismatched_quotes_not_stripped(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Mismatched quotes are NOT stripped (kept as-is)."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_SERVER_NAME": "\"Mismatched'"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["ServerName"] == "\"Mismatched'"

    def test_no_quotes_unchanged(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Values without quotes are unchanged."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_SERVER_NAME": "Plain Value"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["ServerName"] == "Plain Value"

    def test_quoted_integer_stripped_then_parsed(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Quoted integers have quotes stripped before type conversion."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_MAX_CLIENTS": '"64"'}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["MaxClients"] == 64
        assert isinstance(config["MaxClients"], int)


class TestNestedKeyApplication:
    """Tests for nested key application (tested via initialize_config public interface)."""

    def test_nested_key_sets_value(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Nested keys like WorldConfig.AllowCreativeMode are applied correctly."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"VS_CFG_ALLOW_CREATIVE_MODE": "false"}):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        # Template default is True, env var should override to False
        assert config["WorldConfig"]["AllowCreativeMode"] is False

    def test_multiple_nested_keys(
        self,
        config_service: ConfigInitService,
    ) -> None:
        """Multiple nested keys are all applied correctly."""
        config_service.config_path.parent.mkdir(parents=True, exist_ok=True)

        with patch.dict(
            os.environ,
            {
                "VS_CFG_WORLD_NAME": "Custom World",
                "VS_CFG_ALLOW_CREATIVE_MODE": "true",
            },
        ):
            config_service.initialize_config()

        config = json.loads(config_service.config_path.read_text())
        assert config["WorldConfig"]["WorldName"] == "Custom World"
        assert config["WorldConfig"]["AllowCreativeMode"] is True


# ==============================================================================
# Task 3: Integration with ServerService (AC: 1)
# ==============================================================================


class TestServerServiceIntegration:
    """Tests for ConfigInitService integration with ServerService.

    NOTE: These are unit tests that mock the subprocess layer.
    Full integration tests would require a running VintageStory server.
    """

    @pytest.fixture
    def mock_server_service(self, temp_settings: Settings) -> ServerService:
        """Create ServerService with mocked subprocess for testing."""
        from vintagestory_api.services.server import ServerService

        service = ServerService(settings=temp_settings)
        return service

    def test_server_service_has_config_init_service(
        self, mock_server_service: ServerService
    ) -> None:
        """ServerService has ConfigInitService as dependency."""
        assert hasattr(mock_server_service, "config_init_service")
        assert isinstance(mock_server_service.config_init_service, ConfigInitService)

    def test_config_init_service_uses_same_settings(
        self, mock_server_service: ServerService
    ) -> None:
        """ConfigInitService uses the same settings as ServerService."""
        server_settings = mock_server_service.settings
        config_settings = mock_server_service.config_init_service.settings
        assert server_settings is config_settings

    @pytest.mark.asyncio
    async def test_start_server_initializes_config_when_missing(
        self, temp_settings: Settings
    ) -> None:
        """AC 1: Config is created before server start when it doesn't exist."""
        from unittest.mock import AsyncMock, patch

        from vintagestory_api.services.server import ServerService

        # Create server service
        service = ServerService(settings=temp_settings)

        # Create server files so is_installed() returns True
        temp_settings.server_dir.mkdir(parents=True, exist_ok=True)
        (temp_settings.server_dir / "VintagestoryServer.dll").touch()
        (temp_settings.server_dir / "VintagestoryLib.dll").touch()

        # Ensure serverdata dir exists
        temp_settings.serverdata_dir.mkdir(parents=True, exist_ok=True)

        # Config should not exist yet
        config_path = service.config_init_service.config_path
        assert not config_path.exists()

        # Mock the subprocess creation to prevent actual server start
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr.readline = AsyncMock(return_value=b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await service.start_server()

        # Config should now exist (created before server start)
        assert config_path.exists()

        # Cleanup - stop the "server" to cancel background tasks
        mock_process.returncode = 0
        await service.close()

    @pytest.mark.asyncio
    async def test_start_server_does_not_overwrite_existing_config(
        self, temp_settings: Settings
    ) -> None:
        """AC 4: Existing config is NOT overwritten on server start."""
        from unittest.mock import AsyncMock, patch

        from vintagestory_api.services.server import ServerService

        # Create server service
        service = ServerService(settings=temp_settings)

        # Create server files so is_installed() returns True
        temp_settings.server_dir.mkdir(parents=True, exist_ok=True)
        (temp_settings.server_dir / "VintagestoryServer.dll").touch()
        (temp_settings.server_dir / "VintagestoryLib.dll").touch()

        # Create existing config with specific content
        config_path = service.config_init_service.config_path
        config_path.parent.mkdir(parents=True, exist_ok=True)
        existing_content = {"ServerName": "My Precious Server", "Port": 99999}
        config_path.write_text(json.dumps(existing_content))

        # Mock the subprocess creation
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr.readline = AsyncMock(return_value=b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await service.start_server()

        # Verify config content unchanged
        actual = json.loads(config_path.read_text())
        assert actual["ServerName"] == "My Precious Server"
        assert actual["Port"] == 99999

        # Cleanup
        mock_process.returncode = 0
        await service.close()

    @pytest.mark.asyncio
    async def test_start_server_applies_env_overrides_on_first_run(
        self, temp_settings: Settings
    ) -> None:
        """AC 2, 3: Env vars are applied when config is created on first start."""
        from unittest.mock import AsyncMock, patch

        from vintagestory_api.services.server import ServerService

        # Create server service
        service = ServerService(settings=temp_settings)

        # Create server files so is_installed() returns True
        temp_settings.server_dir.mkdir(parents=True, exist_ok=True)
        (temp_settings.server_dir / "VintagestoryServer.dll").touch()
        (temp_settings.server_dir / "VintagestoryLib.dll").touch()
        temp_settings.serverdata_dir.mkdir(parents=True, exist_ok=True)

        # Mock the subprocess creation
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr.readline = AsyncMock(return_value=b"")

        # Set environment variables
        with (
            patch.dict(
                os.environ,
                {
                    "VS_CFG_SERVER_NAME": "Env Override Server",
                    "VS_CFG_MAX_CLIENTS": "64",
                },
            ),
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
        ):
            await service.start_server()

        # Verify config was created with env overrides
        config_path = service.config_init_service.config_path
        actual = json.loads(config_path.read_text())
        assert actual["ServerName"] == "Env Override Server"
        assert actual["MaxClients"] == 64
        assert isinstance(actual["MaxClients"], int)

        # Cleanup
        mock_process.returncode = 0
        await service.close()
