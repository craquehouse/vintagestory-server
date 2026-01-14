"""Tests for ServerService uninstall functionality (Story 13.6)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.server import ServerService

# pyright: reportPrivateUsage=false


def create_fake_installation(settings: Settings, version: str) -> None:
    """Helper to create a fake server installation."""
    settings.server_dir.mkdir(parents=True, exist_ok=True)
    settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
    (settings.server_dir / "VintagestoryServer.dll").touch()
    (settings.server_dir / "VintagestoryLib.dll").touch()
    version_file = settings.vsmanager_dir / "current_version"
    version_file.write_text(version)


class TestUninstallServer:
    """Tests for ServerService.uninstall_server() method."""

    @pytest.mark.asyncio
    async def test_uninstall_deletes_server_dir(
        self, test_settings: Settings, temp_data_dir: Path
    ) -> None:
        """Uninstall removes server directory and its contents."""
        create_fake_installation(test_settings, "1.21.3")
        service = ServerService(settings=test_settings)

        assert service.is_installed()
        assert (test_settings.server_dir / "VintagestoryServer.dll").exists()

        result = await service.uninstall_server()

        assert result is True
        assert not test_settings.server_dir.exists()

    @pytest.mark.asyncio
    async def test_uninstall_removes_version_file(
        self, test_settings: Settings, temp_data_dir: Path
    ) -> None:
        """Uninstall removes version tracking file."""
        create_fake_installation(test_settings, "1.21.3")
        service = ServerService(settings=test_settings)

        version_file = test_settings.vsmanager_dir / "current_version"
        assert version_file.exists()
        assert version_file.read_text() == "1.21.3"

        await service.uninstall_server()

        assert not version_file.exists()

    @pytest.mark.asyncio
    async def test_uninstall_preserves_serverdata(
        self, test_settings: Settings, temp_data_dir: Path
    ) -> None:
        """Uninstall preserves serverdata directory (configs, mods, worlds)."""
        create_fake_installation(test_settings, "1.21.3")
        service = ServerService(settings=test_settings)

        # Create test files in serverdata
        test_settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
        config_file = test_settings.serverdata_dir / "serverconfig.json"
        config_file.write_text('{"test": true}')
        mods_dir = test_settings.serverdata_dir / "Mods"
        mods_dir.mkdir()
        (mods_dir / "test_mod.zip").touch()

        await service.uninstall_server()

        assert test_settings.serverdata_dir.exists()
        assert config_file.exists()
        assert config_file.read_text() == '{"test": true}'
        assert (mods_dir / "test_mod.zip").exists()

    @pytest.mark.asyncio
    async def test_uninstall_resets_state_to_not_installed(
        self, test_settings: Settings, temp_data_dir: Path
    ) -> None:
        """Uninstall resets service state to NOT_INSTALLED."""
        create_fake_installation(test_settings, "1.21.3")
        service = ServerService(settings=test_settings)

        assert service.is_installed()

        await service.uninstall_server()

        assert not service.is_installed()
        status = service.get_server_status()
        assert status.state == ServerState.NOT_INSTALLED

    @pytest.mark.asyncio
    async def test_uninstall_raises_when_not_installed(
        self, test_settings: Settings, temp_data_dir: Path
    ) -> None:
        """Uninstall raises RuntimeError when server not installed."""
        service = ServerService(settings=test_settings)
        assert not service.is_installed()

        with pytest.raises(RuntimeError) as exc_info:
            await service.uninstall_server()

        assert str(exc_info.value) == ErrorCode.SERVER_NOT_INSTALLED

    @pytest.mark.asyncio
    async def test_uninstall_raises_when_server_running(
        self, test_settings: Settings, temp_data_dir: Path
    ) -> None:
        """Uninstall raises RuntimeError when server is running."""
        create_fake_installation(test_settings, "1.21.3")
        service = ServerService(settings=test_settings)

        # Simulate running server
        mock_process = MagicMock()
        mock_process.returncode = None
        service._process = mock_process

        with pytest.raises(RuntimeError) as exc_info:
            await service.uninstall_server()

        assert str(exc_info.value) == ErrorCode.SERVER_RUNNING

    @pytest.mark.asyncio
    async def test_uninstall_succeeds_when_server_stopped(
        self, test_settings: Settings, temp_data_dir: Path
    ) -> None:
        """Uninstall succeeds when server has exited (returncode is set)."""
        create_fake_installation(test_settings, "1.21.3")
        service = ServerService(settings=test_settings)

        # Simulate stopped server
        mock_process = MagicMock()
        mock_process.returncode = 0
        service._process = mock_process

        result = await service.uninstall_server()
        assert result is True
        assert not test_settings.server_dir.exists()

    @pytest.mark.asyncio
    async def test_uninstall_handles_missing_version_file(
        self, test_settings: Settings, temp_data_dir: Path
    ) -> None:
        """Uninstall succeeds even if version file doesn't exist."""
        # Create server files but no version file
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.server_dir / "VintagestoryServer.dll").touch()
        (test_settings.server_dir / "VintagestoryLib.dll").touch()

        service = ServerService(settings=test_settings)
        version_file = test_settings.vsmanager_dir / "current_version"
        assert not version_file.exists()

        result = await service.uninstall_server()
        assert result is True
        assert not test_settings.server_dir.exists()
