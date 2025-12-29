"""Integration tests for ModService orchestrator."""

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vintagestory_api.models.mods import ModInfo
from vintagestory_api.services.mods import ModService, get_mod_service
from vintagestory_api.services.pending_restart import PendingRestartState


def create_mod_zip(
    zip_path: Path,
    modinfo: dict[str, object],
) -> None:
    """Helper to create a test mod zip file."""
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("modinfo.json", json.dumps(modinfo))


@pytest.fixture
def temp_dirs(tmp_path: Path) -> tuple[Path, Path]:
    """Create temporary state and mods directories."""
    state_dir = tmp_path / "state"
    mods_dir = tmp_path / "mods"
    state_dir.mkdir(parents=True)
    mods_dir.mkdir(parents=True)
    return state_dir, mods_dir


@pytest.fixture
def restart_state() -> PendingRestartState:
    """Create a PendingRestartState instance."""
    return PendingRestartState()


@pytest.fixture
def mod_service(
    temp_dirs: tuple[Path, Path],
    restart_state: PendingRestartState,
) -> ModService:
    """Create a ModService with test directories."""
    state_dir, mods_dir = temp_dirs
    return ModService(
        state_dir=state_dir,
        mods_dir=mods_dir,
        restart_state=restart_state,
    )


class TestModServiceInit:
    """Tests for ModService initialization."""

    def test_creates_with_directories(
        self, temp_dirs: tuple[Path, Path], restart_state: PendingRestartState
    ) -> None:
        """ModService initializes with correct directories."""
        state_dir, mods_dir = temp_dirs
        service = ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            restart_state=restart_state,
        )
        assert service.state_manager.state_dir == state_dir
        assert service.state_manager.mods_dir == mods_dir


class TestModServiceListMods:
    """Tests for list_mods() function."""

    def test_list_mods_empty_initially(self, mod_service: ModService) -> None:
        """list_mods() returns empty list when no mods installed."""
        mods = mod_service.list_mods()
        assert mods == []

    def test_list_mods_returns_installed_mods(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """list_mods() returns all installed mods with metadata."""
        _, mods_dir = temp_dirs
        create_mod_zip(
            mods_dir / "testmod_1.0.0.zip",
            {"modid": "testmod", "name": "Test Mod", "version": "1.0.0"},
        )
        create_mod_zip(
            mods_dir / "othermod_2.0.0.zip",
            {"modid": "othermod", "name": "Other Mod", "version": "2.0.0"},
        )

        # Sync state with disk
        mod_service.state_manager.sync_state_with_disk()

        mods = mod_service.list_mods()

        assert len(mods) == 2
        slugs = {m.slug for m in mods}
        assert slugs == {"testmod", "othermod"}

    def test_list_mods_includes_metadata(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """list_mods() includes full metadata in ModInfo objects."""
        _, mods_dir = temp_dirs
        create_mod_zip(
            mods_dir / "richmod_1.0.0.zip",
            {
                "modid": "richmod",
                "name": "Rich Mod",
                "version": "1.0.0",
                "authors": ["Author1", "Author2"],
                "description": "A rich test mod",
            },
        )

        mod_service.state_manager.sync_state_with_disk()

        mods = mod_service.list_mods()

        assert len(mods) == 1
        mod = mods[0]
        assert isinstance(mod, ModInfo)
        assert mod.slug == "richmod"
        assert mod.name == "Rich Mod"
        assert mod.version == "1.0.0"
        assert mod.authors == ["Author1", "Author2"]
        assert mod.description == "A rich test mod"


class TestModServiceGetMod:
    """Tests for get_mod() function."""

    def test_get_mod_returns_none_for_unknown(self, mod_service: ModService) -> None:
        """get_mod() returns None for unknown slug."""
        result = mod_service.get_mod("nonexistent")
        assert result is None

    def test_get_mod_returns_mod_info(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """get_mod() returns ModInfo for known slug."""
        _, mods_dir = temp_dirs
        create_mod_zip(
            mods_dir / "findme_1.0.0.zip",
            {"modid": "findme", "name": "Find Me", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        result = mod_service.get_mod("findme")

        assert result is not None
        assert isinstance(result, ModInfo)
        assert result.slug == "findme"
        assert result.name == "Find Me"


class TestModServiceEnableMod:
    """Tests for enable_mod() function."""

    def test_enable_mod_removes_disabled_suffix(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """enable_mod() renames .zip.disabled to .zip."""
        _, mods_dir = temp_dirs

        # Create a disabled mod
        zip_path = mods_dir / "disabledmod_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {"modid": "disabledmod", "name": "Disabled Mod", "version": "1.0.0"},
        )
        disabled_path = mods_dir / "disabledmod_1.0.0.zip.disabled"
        zip_path.rename(disabled_path)

        mod_service.state_manager.sync_state_with_disk()

        # Enable the mod
        mod_service.enable_mod("disabledmod")

        # File should be renamed back to .zip
        assert (mods_dir / "disabledmod_1.0.0.zip").exists()
        assert not disabled_path.exists()

    def test_enable_mod_updates_state(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """enable_mod() updates mod state to enabled=True."""
        _, mods_dir = temp_dirs

        zip_path = mods_dir / "enableme_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {"modid": "enableme", "name": "Enable Me", "version": "1.0.0"},
        )
        zip_path.rename(mods_dir / "enableme_1.0.0.zip.disabled")

        mod_service.state_manager.sync_state_with_disk()
        disabled_state = mod_service.state_manager.get_mod("enableme_1.0.0.zip.disabled")
        assert disabled_state is not None
        assert disabled_state.enabled is False

        mod_service.enable_mod("enableme")

        # State should reflect new filename and enabled status
        new_state = mod_service.state_manager.get_mod("enableme_1.0.0.zip")
        assert new_state is not None
        assert new_state.enabled is True

    def test_enable_mod_sets_pending_restart(
        self,
        mod_service: ModService,
        temp_dirs: tuple[Path, Path],
        restart_state: PendingRestartState,
    ) -> None:
        """enable_mod() triggers pending restart when server is running."""
        _, mods_dir = temp_dirs

        zip_path = mods_dir / "restartmod_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {"modid": "restartmod", "name": "Restart Mod", "version": "1.0.0"},
        )
        zip_path.rename(mods_dir / "restartmod_1.0.0.zip.disabled")

        mod_service.state_manager.sync_state_with_disk()

        # Simulate server running
        mod_service.set_server_running(True)

        mod_service.enable_mod("restartmod")

        assert restart_state.pending_restart is True
        assert len(restart_state.pending_changes) == 1
        assert "restartmod" in restart_state.pending_changes[0]

    def test_enable_already_enabled_mod_no_op(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """enable_mod() on already enabled mod does nothing."""
        _, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "alreadyenabled_1.0.0.zip",
            {"modid": "alreadyenabled", "name": "Already Enabled", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        # Should not raise or change anything
        mod_service.enable_mod("alreadyenabled")

        state = mod_service.state_manager.get_mod("alreadyenabled_1.0.0.zip")
        assert state is not None
        assert state.enabled is True

    def test_enable_unknown_mod_raises(self, mod_service: ModService) -> None:
        """enable_mod() raises for unknown mod slug."""
        from vintagestory_api.services.mods import ModNotFoundError

        with pytest.raises(ModNotFoundError):
            mod_service.enable_mod("nonexistent")


class TestModServiceDisableMod:
    """Tests for disable_mod() function."""

    def test_disable_mod_adds_disabled_suffix(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """disable_mod() renames .zip to .zip.disabled."""
        _, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "tobedisabled_1.0.0.zip",
            {"modid": "tobedisabled", "name": "To Be Disabled", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        mod_service.disable_mod("tobedisabled")

        # File should be renamed
        assert (mods_dir / "tobedisabled_1.0.0.zip.disabled").exists()
        assert not (mods_dir / "tobedisabled_1.0.0.zip").exists()

    def test_disable_mod_updates_state(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """disable_mod() updates mod state to enabled=False."""
        _, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "disableme_1.0.0.zip",
            {"modid": "disableme", "name": "Disable Me", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()
        enabled_state = mod_service.state_manager.get_mod("disableme_1.0.0.zip")
        assert enabled_state is not None
        assert enabled_state.enabled is True

        mod_service.disable_mod("disableme")

        new_state = mod_service.state_manager.get_mod("disableme_1.0.0.zip.disabled")
        assert new_state is not None
        assert new_state.enabled is False

    def test_disable_mod_sets_pending_restart(
        self,
        mod_service: ModService,
        temp_dirs: tuple[Path, Path],
        restart_state: PendingRestartState,
    ) -> None:
        """disable_mod() triggers pending restart when server is running."""
        _, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "disablerestartmod_1.0.0.zip",
            {"modid": "disablerestartmod", "name": "Disable Restart Mod", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()
        mod_service.set_server_running(True)

        mod_service.disable_mod("disablerestartmod")

        assert restart_state.pending_restart is True
        assert "disablerestartmod" in restart_state.pending_changes[0]

    def test_disable_already_disabled_mod_no_op(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """disable_mod() on already disabled mod does nothing."""
        _, mods_dir = temp_dirs

        zip_path = mods_dir / "alreadydisabled_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {"modid": "alreadydisabled", "name": "Already Disabled", "version": "1.0.0"},
        )
        zip_path.rename(mods_dir / "alreadydisabled_1.0.0.zip.disabled")

        mod_service.state_manager.sync_state_with_disk()

        # Should not raise or change anything
        mod_service.disable_mod("alreadydisabled")

        state = mod_service.state_manager.get_mod("alreadydisabled_1.0.0.zip.disabled")
        assert state is not None
        assert state.enabled is False

    def test_disable_unknown_mod_raises(self, mod_service: ModService) -> None:
        """disable_mod() raises for unknown mod slug."""
        from vintagestory_api.services.mods import ModNotFoundError

        with pytest.raises(ModNotFoundError):
            mod_service.disable_mod("nonexistent")


# --- Task 7: FastAPI integration tests ---


class TestGetModServiceDependency:
    """Tests for get_mod_service() dependency injection."""

    def test_get_mod_service_returns_singleton(self) -> None:
        """get_mod_service() returns same instance on repeated calls."""
        # Reset module-level service for clean test
        import vintagestory_api.services.mods as mods_module

        mods_module._mod_service = None  # pyright: ignore[reportPrivateUsage]

        with patch.object(mods_module, "Settings") as mock_settings:
            mock_settings.return_value.vsmanager_dir = Path("/tmp/test-state")
            mock_settings.return_value.serverdata_dir = Path("/tmp/test-mods")

            service1 = get_mod_service()
            service2 = get_mod_service()

            assert service1 is service2

    def test_get_mod_service_uses_settings_paths(self, tmp_path: Path) -> None:
        """get_mod_service() uses paths from Settings."""
        import vintagestory_api.services.mods as mods_module

        mods_module._mod_service = None  # pyright: ignore[reportPrivateUsage]

        custom_state = tmp_path / "custom" / "state"
        custom_serverdata = tmp_path / "custom" / "serverdata"
        custom_cache = tmp_path / "custom" / "cache"

        with patch.object(mods_module, "Settings") as mock_settings:
            mock_settings.return_value.vsmanager_dir = custom_state
            mock_settings.return_value.serverdata_dir = custom_serverdata
            mock_settings.return_value.cache_dir = custom_cache
            mock_settings.return_value.game_version = "1.21.3"

            service = get_mod_service()

            assert service.state_manager.state_dir == custom_state / "state"
            assert service.state_manager.mods_dir == custom_serverdata / "Mods"


# --- Tests for ModService.install_mod ---


SMITHINGPLUS_MOD = {
    "modid": 2655,
    "name": "Smithing Plus",
    "urlalias": "smithingplus",
    "author": "jayu",
    "releases": [
        {
            "releaseid": 27001,
            "modversion": "1.8.3",
            "filename": "smithingplus_1.8.3.zip",
            "fileid": 59176,
            "downloads": 49726,
            "tags": ["1.21.0", "1.21.1", "1.21.2", "1.21.3"],
        },
        {
            "releaseid": 26543,
            "modversion": "1.8.2",
            "filename": "smithingplus_1.8.2.zip",
            "fileid": 57894,
            "downloads": 31245,
            "tags": ["1.21.0", "1.21.1"],
        },
    ],
}


class TestModServiceInstallMod:
    """Integration tests for ModService.install_mod()."""

    @pytest.fixture
    def install_service(
        self,
        temp_dirs: tuple[Path, Path],
        restart_state: PendingRestartState,
    ) -> ModService:
        """Create a ModService with cache directory for install tests."""
        state_dir, mods_dir = temp_dirs
        cache_dir = state_dir.parent / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        return ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            cache_dir=cache_dir,
            restart_state=restart_state,
            game_version="1.21.3",
        )

    @pytest.mark.asyncio
    async def test_install_mod_latest_version(
        self, install_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """install_mod() downloads and installs latest version."""
        import respx
        from httpx import Response

        _state_dir, mods_dir = temp_dirs

        # Create fake mod zip content with modinfo.json
        mod_zip_content = create_mod_zip_bytes(
            {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.3"}
        )

        with respx.mock:
            # Mock mod lookup
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
                )
            )

            # Mock file download
            respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
                return_value=Response(200, content=mod_zip_content)
            )

            result = await install_service.install_mod("smithingplus")

        assert result.success is True
        assert result.version == "1.8.3"
        assert result.filename == "smithingplus_1.8.3.zip"
        assert result.slug == "smithingplus"
        assert result.compatibility == "compatible"  # 1.21.3 in tags

        # Verify file exists in mods directory
        assert (mods_dir / "smithingplus_1.8.3.zip").exists()

        # Verify state was updated
        mod_state = install_service.state_manager.get_mod_by_slug("smithingplus")
        assert mod_state is not None
        assert mod_state.version == "1.8.3"
        assert mod_state.enabled is True

    @pytest.mark.asyncio
    async def test_install_mod_specific_version(
        self, install_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """install_mod() installs specific version when requested."""
        import respx
        from httpx import Response

        _, _mods_dir = temp_dirs

        mod_zip_content = create_mod_zip_bytes(
            {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.2"}
        )

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
                )
            )

            respx.get("https://mods.vintagestory.at/download?fileid=57894").mock(
                return_value=Response(200, content=mod_zip_content)
            )

            result = await install_service.install_mod("smithingplus", version="1.8.2")

        assert result.success is True
        assert result.version == "1.8.2"
        assert result.filename == "smithingplus_1.8.2.zip"
        assert result.compatibility == "not_verified"  # 1.21.3 not in 1.8.2 tags

    @pytest.mark.asyncio
    async def test_install_mod_from_url(
        self, install_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """install_mod() works with full URL input."""
        import respx
        from httpx import Response

        mod_zip_content = create_mod_zip_bytes(
            {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.3"}
        )

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
                )
            )

            respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
                return_value=Response(200, content=mod_zip_content)
            )

            result = await install_service.install_mod(
                "https://mods.vintagestory.at/smithingplus"
            )

        assert result.success is True
        assert result.slug == "smithingplus"

    @pytest.mark.asyncio
    async def test_install_mod_already_installed(
        self, install_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """install_mod() raises error for already installed mod."""
        from vintagestory_api.services.mods import ModAlreadyInstalledError

        _, mods_dir = temp_dirs

        # Pre-install the mod
        create_mod_zip(
            mods_dir / "smithingplus_1.8.0.zip",
            {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.0"},
        )
        install_service.state_manager.sync_state_with_disk()

        with pytest.raises(ModAlreadyInstalledError) as exc_info:
            await install_service.install_mod("smithingplus")

        assert exc_info.value.slug == "smithingplus"
        assert exc_info.value.current_version == "1.8.0"

    @pytest.mark.asyncio
    async def test_install_mod_not_found(self, install_service: ModService) -> None:
        """install_mod() raises error for missing mod."""
        import respx
        from httpx import Response

        from vintagestory_api.services.mod_api import ModNotFoundError

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/nonexistent").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "404", "mod": None},
                )
            )

            with pytest.raises(ModNotFoundError) as exc_info:
                await install_service.install_mod("nonexistent")

            assert exc_info.value.slug == "nonexistent"

    @pytest.mark.asyncio
    async def test_install_mod_sets_pending_restart(
        self,
        install_service: ModService,
        temp_dirs: tuple[Path, Path],
        restart_state: PendingRestartState,
    ) -> None:
        """install_mod() triggers pending restart when server is running."""
        import respx
        from httpx import Response

        mod_zip_content = create_mod_zip_bytes(
            {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.3"}
        )

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
                )
            )

            respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
                return_value=Response(200, content=mod_zip_content)
            )

            # Simulate server running
            install_service.set_server_running(True)

            result = await install_service.install_mod("smithingplus")

        assert result.pending_restart is True
        assert restart_state.pending_restart is True
        assert "smithingplus" in restart_state.pending_changes[0]


def create_mod_zip_bytes(modinfo: dict[str, object]) -> bytes:
    """Create a mod zip file as bytes for mocking downloads."""
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("modinfo.json", json.dumps(modinfo))
    return buffer.getvalue()
