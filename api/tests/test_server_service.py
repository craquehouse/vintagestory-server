"""Tests for ServerService uninstall functionality (Story 13.6)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.server import ServerService


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def settings(temp_data_dir: Path) -> Settings:
    """Create Settings with temp data directory."""
    return Settings(data_dir=temp_data_dir)


@pytest.fixture
def service(settings: Settings) -> ServerService:
    """Create a ServerService with test settings."""
    return ServerService(settings=settings)


def create_fake_installation(settings: Settings, version: str) -> None:
    """Helper to create a fake server installation."""
    # Ensure directories exist
    settings.server_dir.mkdir(parents=True, exist_ok=True)
    settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)

    # Create required server files
    (settings.server_dir / "VintagestoryServer.dll").touch()
    (settings.server_dir / "VintagestoryLib.dll").touch()

    # Create version tracking file
    version_file = settings.vsmanager_dir / "current_version"
    version_file.write_text(version)


class TestUninstallServerService:
    """Tests for ServerService.uninstall_server() method."""

    @pytest.mark.asyncio
    async def test_uninstall_deletes_server_dir(
        self, service: ServerService, settings: Settings
    ) -> None:
        """Uninstall removes server directory and its contents."""
        create_fake_installation(settings, "1.21.3")

        # Verify installation exists
        assert service.is_installed()
        assert (settings.server_dir / "VintagestoryServer.dll").exists()

        # Uninstall
        result = await service.uninstall_server()

        # Verify server dir deleted
        assert result is True
        assert not settings.server_dir.exists()

    @pytest.mark.asyncio
    async def test_uninstall_removes_version_file(
        self, service: ServerService, settings: Settings
    ) -> None:
        """Uninstall removes version tracking file."""
        create_fake_installation(settings, "1.21.3")

        version_file = settings.vsmanager_dir / "current_version"
        assert version_file.exists()
        assert version_file.read_text() == "1.21.3"

        # Uninstall
        await service.uninstall_server()

        # Verify version file deleted
        assert not version_file.exists()

    @pytest.mark.asyncio
    async def test_uninstall_preserves_serverdata(
        self, service: ServerService, settings: Settings
    ) -> None:
        """Uninstall preserves serverdata directory (configs, mods, worlds)."""
        create_fake_installation(settings, "1.21.3")

        # Create test files in serverdata
        settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
        config_file = settings.serverdata_dir / "serverconfig.json"
        config_file.write_text('{"test": true}')
        mods_dir = settings.serverdata_dir / "Mods"
        mods_dir.mkdir()
        (mods_dir / "test_mod.zip").touch()

        # Uninstall
        await service.uninstall_server()

        # Verify serverdata preserved
        assert settings.serverdata_dir.exists()
        assert config_file.exists()
        assert config_file.read_text() == '{"test": true}'
        assert (mods_dir / "test_mod.zip").exists()

    @pytest.mark.asyncio
    async def test_uninstall_resets_state_to_not_installed(
        self, service: ServerService, settings: Settings
    ) -> None:
        """Uninstall resets service state to NOT_INSTALLED."""
        create_fake_installation(settings, "1.21.3")

        # Verify initial state
        assert service.is_installed()

        # Uninstall
        await service.uninstall_server()

        # Verify state reset
        assert not service.is_installed()
        status = service.get_server_status()
        assert status.state == ServerState.NOT_INSTALLED

    @pytest.mark.asyncio
    async def test_uninstall_raises_when_not_installed(self, service: ServerService) -> None:
        """Uninstall raises RuntimeError when server not installed."""
        assert not service.is_installed()

        with pytest.raises(RuntimeError) as exc_info:
            await service.uninstall_server()

        assert str(exc_info.value) == ErrorCode.SERVER_NOT_INSTALLED

    @pytest.mark.asyncio
    async def test_uninstall_raises_when_server_running(
        self, service: ServerService, settings: Settings
    ) -> None:
        """Uninstall raises RuntimeError when server is running."""
        create_fake_installation(settings, "1.21.3")

        # Simulate running server by setting process with None returncode
        mock_process = MagicMock()
        mock_process.returncode = None  # Indicates process is running
        service._process = mock_process  # pyright: ignore[reportPrivateUsage]

        with pytest.raises(RuntimeError) as exc_info:
            await service.uninstall_server()

        assert str(exc_info.value) == ErrorCode.SERVER_RUNNING

    @pytest.mark.asyncio
    async def test_uninstall_succeeds_when_server_stopped(
        self, service: ServerService, settings: Settings
    ) -> None:
        """Uninstall succeeds when server has exited (returncode is set)."""
        create_fake_installation(settings, "1.21.3")

        # Simulate stopped server by setting process with returncode
        mock_process = MagicMock()
        mock_process.returncode = 0  # Process has exited
        service._process = mock_process  # pyright: ignore[reportPrivateUsage]

        # Should succeed
        result = await service.uninstall_server()
        assert result is True
        assert not settings.server_dir.exists()

    @pytest.mark.asyncio
    async def test_uninstall_handles_missing_version_file(
        self, service: ServerService, settings: Settings
    ) -> None:
        """Uninstall succeeds even if version file doesn't exist."""
        # Create server files but no version file
        settings.server_dir.mkdir(parents=True, exist_ok=True)
        (settings.server_dir / "VintagestoryServer.dll").touch()
        (settings.server_dir / "VintagestoryLib.dll").touch()

        version_file = settings.vsmanager_dir / "current_version"
        assert not version_file.exists()

        # Should succeed
        result = await service.uninstall_server()
        assert result is True
        assert not settings.server_dir.exists()
