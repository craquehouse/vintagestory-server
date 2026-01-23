"""Integration tests for ModService orchestrator."""

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vintagestory_api.models.mods import ModInfo, ModLookupResponse
from vintagestory_api.services.mods import (
    InvalidSlugError,
    ModNotFoundError,
    ModService,
    get_mod_service,
)
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

    def test_cache_eviction_property(
        self, temp_dirs: tuple[Path, Path], restart_state: PendingRestartState
    ) -> None:
        """cache_eviction property returns CacheEvictionService instance."""
        from vintagestory_api.services.cache_eviction import CacheEvictionService

        state_dir, mods_dir = temp_dirs
        service = ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            restart_state=restart_state,
        )
        assert isinstance(service.cache_eviction, CacheEvictionService)

    @pytest.mark.asyncio
    async def test_close_when_api_client_exists(
        self, temp_dirs: tuple[Path, Path], restart_state: PendingRestartState
    ) -> None:
        """close() closes api_client when it has been initialized."""
        state_dir, mods_dir = temp_dirs
        service = ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            restart_state=restart_state,
        )

        # Access api_client property to initialize it
        _ = service.api_client

        # Close should succeed and clean up the client
        await service.close()

        # After close, the client should be None
        assert service._mod_api_client is None  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.asyncio
    async def test_close_when_api_client_not_initialized(
        self, temp_dirs: tuple[Path, Path], restart_state: PendingRestartState
    ) -> None:
        """close() succeeds even when api_client was never initialized."""
        state_dir, mods_dir = temp_dirs
        service = ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            restart_state=restart_state,
        )

        # Close should succeed without error
        await service.close()


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

    def test_list_mods_fallback_when_no_cached_metadata(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """list_mods() uses slug as name fallback when metadata cache is missing."""
        import shutil

        state_dir, mods_dir = temp_dirs
        create_mod_zip(
            mods_dir / "testmod_1.0.0.zip",
            {"modid": "testmod", "name": "Test Mod", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        # Delete the cached metadata to simulate missing cache
        cache_dir = state_dir / "mods" / "testmod"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        mods = mod_service.list_mods()

        assert len(mods) == 1
        mod = mods[0]
        assert mod.slug == "testmod"
        assert mod.name == "testmod"  # Should use slug as fallback
        assert mod.authors == []  # Empty list when no metadata
        assert mod.description is None


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

    def test_get_mod_fallback_when_no_cached_metadata(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """get_mod() uses slug as name fallback when metadata cache is missing."""
        import shutil

        state_dir, mods_dir = temp_dirs
        create_mod_zip(
            mods_dir / "testmod_1.0.0.zip",
            {"modid": "testmod", "name": "Test Mod", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        # Delete the cached metadata
        cache_dir = state_dir / "mods" / "testmod"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        result = mod_service.get_mod("testmod")

        assert result is not None
        assert result.slug == "testmod"
        assert result.name == "testmod"  # Should use slug as fallback
        assert result.authors == []  # Empty list when no metadata
        assert result.description is None


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
        """enable_mod() on already enabled mod returns success with no state change."""
        _, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "alreadyenabled_1.0.0.zip",
            {"modid": "alreadyenabled", "name": "Already Enabled", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        # Should return success (idempotent)
        result = mod_service.enable_mod("alreadyenabled")

        assert result.slug == "alreadyenabled"
        assert result.enabled is True
        assert result.pending_restart is False  # No change, no restart needed

        state = mod_service.state_manager.get_mod("alreadyenabled_1.0.0.zip")
        assert state is not None
        assert state.enabled is True

    def test_enable_mod_returns_result(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """enable_mod() returns EnableResult with correct values."""
        _, mods_dir = temp_dirs

        zip_path = mods_dir / "resultmod_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {"modid": "resultmod", "name": "Result Mod", "version": "1.0.0"},
        )
        zip_path.rename(mods_dir / "resultmod_1.0.0.zip.disabled")

        mod_service.state_manager.sync_state_with_disk()

        result = mod_service.enable_mod("resultmod")

        assert result.slug == "resultmod"
        assert result.enabled is True
        assert result.pending_restart is False  # Server not running

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
        """disable_mod() on already disabled mod returns success with no state change."""
        _, mods_dir = temp_dirs

        zip_path = mods_dir / "alreadydisabled_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {"modid": "alreadydisabled", "name": "Already Disabled", "version": "1.0.0"},
        )
        zip_path.rename(mods_dir / "alreadydisabled_1.0.0.zip.disabled")

        mod_service.state_manager.sync_state_with_disk()

        # Should return success (idempotent)
        result = mod_service.disable_mod("alreadydisabled")

        assert result.slug == "alreadydisabled"
        assert result.enabled is False
        assert result.pending_restart is False  # No change, no restart needed

        state = mod_service.state_manager.get_mod("alreadydisabled_1.0.0.zip.disabled")
        assert state is not None
        assert state.enabled is False

    def test_disable_mod_returns_result(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """disable_mod() returns DisableResult with correct values."""
        _, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "disableresultmod_1.0.0.zip",
            {"modid": "disableresultmod", "name": "Disable Result Mod", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        result = mod_service.disable_mod("disableresultmod")

        assert result.slug == "disableresultmod"
        assert result.enabled is False
        assert result.pending_restart is False  # Server not running

    def test_disable_unknown_mod_raises(self, mod_service: ModService) -> None:
        """disable_mod() raises for unknown mod slug."""
        from vintagestory_api.services.mods import ModNotFoundError

        with pytest.raises(ModNotFoundError):
            mod_service.disable_mod("nonexistent")


class TestModServiceRemoveMod:
    """Tests for remove_mod() function."""

    def test_remove_mod_deletes_enabled_mod(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """remove_mod() deletes an enabled mod file and removes from state."""
        _, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "removemod_1.0.0.zip",
            {"modid": "removemod", "name": "Remove Mod", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        # Verify mod exists before removal
        assert (mods_dir / "removemod_1.0.0.zip").exists()
        assert mod_service.get_mod("removemod") is not None

        result = mod_service.remove_mod("removemod")

        # File should be deleted
        assert not (mods_dir / "removemod_1.0.0.zip").exists()

        # Mod should be removed from state
        assert mod_service.get_mod("removemod") is None

        # Result should have correct values
        assert result.slug == "removemod"
        assert result.pending_restart is False

    def test_remove_mod_deletes_disabled_mod(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """remove_mod() deletes a disabled mod file and removes from state."""
        _, mods_dir = temp_dirs

        zip_path = mods_dir / "removedisabled_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {"modid": "removedisabled", "name": "Remove Disabled", "version": "1.0.0"},
        )
        # Rename to disabled
        zip_path.rename(mods_dir / "removedisabled_1.0.0.zip.disabled")

        mod_service.state_manager.sync_state_with_disk()

        # Verify disabled mod exists
        assert (mods_dir / "removedisabled_1.0.0.zip.disabled").exists()

        result = mod_service.remove_mod("removedisabled")

        # File should be deleted
        assert not (mods_dir / "removedisabled_1.0.0.zip.disabled").exists()

        # Mod should be removed from state
        assert mod_service.get_mod("removedisabled") is None
        assert result.slug == "removedisabled"

    def test_remove_mod_sets_pending_restart(
        self,
        mod_service: ModService,
        temp_dirs: tuple[Path, Path],
        restart_state: PendingRestartState,
    ) -> None:
        """remove_mod() triggers pending restart when server is running."""
        _, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "removerestartmod_1.0.0.zip",
            {"modid": "removerestartmod", "name": "Remove Restart Mod", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()
        mod_service.set_server_running(True)

        result = mod_service.remove_mod("removerestartmod")

        assert result.pending_restart is True
        assert restart_state.pending_restart is True
        assert "removerestartmod" in restart_state.pending_changes[0]

    def test_remove_mod_unknown_raises(self, mod_service: ModService) -> None:
        """remove_mod() raises for unknown mod slug."""
        with pytest.raises(ModNotFoundError):
            mod_service.remove_mod("nonexistent")

    def test_remove_mod_cleans_up_cached_metadata(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """remove_mod() deletes cached metadata directory."""
        state_dir, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "removecache_1.0.0.zip",
            {"modid": "removecache", "name": "Remove Cache", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        # Verify cached metadata exists (created by import_mod)
        cache_dir = state_dir / "mods" / "removecache"
        assert cache_dir.exists()

        mod_service.remove_mod("removecache")

        # Cache directory should be deleted
        assert not cache_dir.exists()

    def test_remove_mod_handles_already_deleted_file(
        self, mod_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """remove_mod() succeeds even if file was already deleted from disk."""
        _, mods_dir = temp_dirs

        create_mod_zip(
            mods_dir / "deletedfile_1.0.0.zip",
            {"modid": "deletedfile", "name": "Deleted File", "version": "1.0.0"},
        )

        mod_service.state_manager.sync_state_with_disk()

        # Manually delete the file (simulating external deletion)
        (mods_dir / "deletedfile_1.0.0.zip").unlink()

        # Should succeed - just removes from state
        result = mod_service.remove_mod("deletedfile")

        assert result.slug == "deletedfile"
        assert mod_service.get_mod("deletedfile") is None


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

    @pytest.mark.asyncio
    async def test_install_mod_cleans_up_on_import_failure(
        self, install_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """install_mod() cleans up mod file if import or state save fails."""
        import respx
        from httpx import Response

        _, mods_dir = temp_dirs

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

            # Mock state manager save to fail
            with patch.object(
                install_service.state_manager, "save", side_effect=OSError("Disk full")
            ):
                with pytest.raises(OSError, match="Disk full"):
                    await install_service.install_mod("smithingplus")

        # Verify mod file was cleaned up (not left orphaned)
        assert not (mods_dir / "smithingplus_1.8.3.zip").exists()

        # Verify no state was persisted
        assert install_service.state_manager.get_mod_by_slug("smithingplus") is None

    @pytest.mark.asyncio
    async def test_install_mod_handles_copy_failure(
        self, install_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """install_mod() cleans up temp file if copy fails (e.g., disk full)."""
        import shutil

        import respx
        from httpx import Response

        _, mods_dir = temp_dirs

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

            # Mock shutil.copy2 to simulate disk full
            with patch.object(
                shutil, "copy2", side_effect=OSError("No space left on device")
            ):
                with pytest.raises(OSError, match="No space left on device"):
                    await install_service.install_mod("smithingplus")

        # Verify no temp or final files left behind
        assert not (mods_dir / "smithingplus_1.8.3.zip").exists()
        assert not (mods_dir / "smithingplus_1.8.3.tmp").exists()

    @pytest.mark.asyncio
    async def test_install_mod_cleans_up_temp_file_on_rename_failure(
        self, install_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """install_mod() cleans up temp file if rename fails after copy succeeds."""
        # This tests line 736: temp_path.unlink() when temp_path.exists()
        import shutil

        import respx
        from httpx import Response

        _, mods_dir = temp_dirs

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

            # Track whether we're in the mods_dir context (not cache_dir)
            original_rename = Path.rename
            rename_count = {"count": 0}

            def selective_failing_rename(self: Path, target: Path) -> Path:
                # Only fail on the second rename (in mods_dir, not cache_dir)
                # First rename is in download_mod (cache), second is in install_mod (mods_dir)
                if str(self).endswith(".tmp") and str(self.parent) == str(mods_dir):
                    # This is the install_mod rename (line 727)
                    raise OSError("Permission denied - disk full")
                # Otherwise, use original rename for cache operations
                return original_rename(self, target)

            with patch.object(Path, "rename", selective_failing_rename):
                with pytest.raises(OSError, match="Permission denied"):
                    await install_service.install_mod("smithingplus")

        # Verify temp file was cleaned up (line 736 executed)
        assert not (mods_dir / "smithingplus_1.8.3.tmp").exists()
        # Verify final file was not created
        assert not (mods_dir / "smithingplus_1.8.3.zip").exists()

    @pytest.mark.asyncio
    async def test_install_mod_with_corrupt_zip_uses_fallback(
        self, install_service: ModService, temp_dirs: tuple[Path, Path]
    ) -> None:
        """install_mod() succeeds with fallback metadata for corrupt zip."""
        import respx
        from httpx import Response

        _, mods_dir = temp_dirs

        # Create corrupt zip content (not a valid zip)
        corrupt_zip_content = b"this is not a valid zip file"

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
                )
            )

            respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
                return_value=Response(200, content=corrupt_zip_content)
            )

            result = await install_service.install_mod("smithingplus")

        # Should succeed using filename-derived fallback metadata
        assert result.success is True
        assert result.filename == "smithingplus_1.8.3.zip"
        # Slug comes from fallback (filename without version)
        assert result.slug == "smithingplus_1.8.3"

        # Verify file exists
        assert (mods_dir / "smithingplus_1.8.3.zip").exists()

    @pytest.mark.asyncio
    async def test_install_mod_download_returns_none(
        self, install_service: ModService
    ) -> None:
        """install_mod() raises ModNotFoundError when download_mod returns None."""
        from unittest.mock import AsyncMock

        from vintagestory_api.services.mod_api import ModNotFoundError

        # Mock the api_client's download_mod to return None
        mock_client = AsyncMock()
        mock_client.download_mod.return_value = None

        with patch.object(
            install_service, "_get_mod_api_client", return_value=mock_client
        ):
            with pytest.raises(ModNotFoundError) as exc_info:
                await install_service.install_mod("nonexistent")

            assert exc_info.value.slug == "nonexistent"

def create_mod_zip_bytes(modinfo: dict[str, object]) -> bytes:
    """Create a mod zip file as bytes for mocking downloads."""
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("modinfo.json", json.dumps(modinfo))
    return buffer.getvalue()


# --- Tests for ModService.lookup_mod ---

LOOKUP_MOD_COMPATIBLE = {
    "modid": 2655,
    "name": "Smithing Plus",
    "urlalias": "smithingplus",
    "author": "jayu",
    "text": "Expanded smithing mechanics",
    "side": "Both",
    "releases": [
        {
            "releaseid": 27001,
            "modversion": "1.8.3",
            "filename": "smithingplus_1.8.3.zip",
            "fileid": 59176,
            "downloads": 49726,
            "tags": ["1.21.0", "1.21.1", "1.21.2", "1.21.3"],
        },
    ],
}

LOOKUP_MOD_NOT_VERIFIED = {
    "modid": 2655,
    "name": "Smithing Plus",
    "urlalias": "smithingplus",
    "author": "jayu",
    "text": "Expanded smithing mechanics",
    "side": "Both",
    "releases": [
        {
            "releaseid": 27001,
            "modversion": "1.8.3",
            "filename": "smithingplus_1.8.3.zip",
            "fileid": 59176,
            "downloads": 30000,
            "tags": ["1.21.0"],  # Same major.minor as 1.21.3 but different patch
        },
    ],
}

LOOKUP_MOD_INCOMPATIBLE = {
    "modid": 1234,
    "name": "Old Mod",
    "urlalias": "oldmod",
    "author": "someone",
    "text": None,
    "side": "Server",
    "releases": [
        {
            "releaseid": 10000,
            "modversion": "1.5.0",
            "filename": "oldmod_1.5.0.zip",
            "fileid": 10000,
            "downloads": 5000,
            "tags": ["1.20.0", "1.20.1"],  # Different minor version
        },
    ],
}


class TestModServiceLookupMod:
    """Tests for ModService.lookup_mod()."""

    @pytest.fixture
    def lookup_service(
        self,
        temp_dirs: tuple[Path, Path],
        restart_state: PendingRestartState,
    ) -> ModService:
        """Create a ModService for lookup tests."""
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
    async def test_lookup_mod_compatible(self, lookup_service: ModService) -> None:
        """lookup_mod() returns compatible status for exact version match."""
        import respx
        from httpx import Response

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": LOOKUP_MOD_COMPATIBLE},
                )
            )

            result = await lookup_service.lookup_mod("smithingplus")

        assert isinstance(result, ModLookupResponse)
        assert result.slug == "smithingplus"
        assert result.name == "Smithing Plus"
        assert result.author == "jayu"
        assert result.description == "Expanded smithing mechanics"
        assert result.latest_version == "1.8.3"
        assert result.downloads == 49726
        assert result.side == "Both"
        assert result.compatibility.status == "compatible"
        assert result.compatibility.game_version == "1.21.3"
        assert result.compatibility.mod_version == "1.8.3"
        assert result.compatibility.message is None

    @pytest.mark.asyncio
    async def test_lookup_mod_not_verified(self, lookup_service: ModService) -> None:
        """lookup_mod() returns not_verified for same major.minor version."""
        import respx
        from httpx import Response

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": LOOKUP_MOD_NOT_VERIFIED},
                )
            )

            result = await lookup_service.lookup_mod("smithingplus")

        assert result.compatibility.status == "not_verified"
        assert result.compatibility.message is not None
        assert "1.21.3" in result.compatibility.message
        assert "May still work" in result.compatibility.message

    @pytest.mark.asyncio
    async def test_lookup_mod_incompatible(self, lookup_service: ModService) -> None:
        """lookup_mod() returns incompatible for different minor version."""
        import respx
        from httpx import Response

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/oldmod").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": LOOKUP_MOD_INCOMPATIBLE},
                )
            )

            result = await lookup_service.lookup_mod("oldmod")

        assert result.compatibility.status == "incompatible"
        assert result.compatibility.message is not None
        assert "1.20.0" in result.compatibility.message
        assert "Installation may cause issues" in result.compatibility.message

    @pytest.mark.asyncio
    async def test_lookup_mod_not_found(self, lookup_service: ModService) -> None:
        """lookup_mod() raises ModNotFoundError for non-existent mod."""
        import respx
        from httpx import Response

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/nonexistent").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "404", "mod": None},
                )
            )

            with pytest.raises(ModNotFoundError) as exc_info:
                await lookup_service.lookup_mod("nonexistent")

            assert exc_info.value.slug == "nonexistent"

    @pytest.mark.asyncio
    async def test_lookup_mod_api_unavailable(self, lookup_service: ModService) -> None:
        """lookup_mod() raises ExternalApiError when API is unavailable."""
        import httpx
        import respx

        from vintagestory_api.services.mod_api import ExternalApiError

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                side_effect=httpx.ConnectError("connection refused")
            )

            with pytest.raises(ExternalApiError):
                await lookup_service.lookup_mod("smithingplus")

    @pytest.mark.asyncio
    async def test_lookup_mod_with_full_url(self, lookup_service: ModService) -> None:
        """lookup_mod() works with full URL input."""
        import respx
        from httpx import Response

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": LOOKUP_MOD_COMPATIBLE},
                )
            )

            result = await lookup_service.lookup_mod(
                "https://mods.vintagestory.at/smithingplus"
            )

        assert result.slug == "smithingplus"
        assert result.compatibility.status == "compatible"

    @pytest.mark.asyncio
    async def test_lookup_mod_server_not_installed(
        self,
        temp_dirs: tuple[Path, Path],
        restart_state: PendingRestartState,
    ) -> None:
        """lookup_mod() returns not_verified when server version is unknown."""
        import respx
        from httpx import Response

        state_dir, mods_dir = temp_dirs
        # Service with no game version (server not installed)
        service = ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            restart_state=restart_state,
            game_version="",  # Empty = unknown
        )

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": LOOKUP_MOD_COMPATIBLE},
                )
            )

            result = await service.lookup_mod("smithingplus")

        assert result.compatibility.status == "not_verified"
        assert result.compatibility.message is not None
        assert "version unknown" in result.compatibility.message.lower()

    @pytest.mark.asyncio
    async def test_lookup_mod_invalid_slug(self, lookup_service: ModService) -> None:
        """lookup_mod() raises InvalidSlugError for invalid slug format."""
        with pytest.raises(InvalidSlugError) as exc_info:
            await lookup_service.lookup_mod("../invalid/path")

        assert exc_info.value.slug == "../invalid/path"

    @pytest.mark.asyncio
    async def test_lookup_mod_windows_reserved_name(
        self, lookup_service: ModService
    ) -> None:
        """lookup_mod() rejects Windows reserved names."""
        with pytest.raises(InvalidSlugError):
            await lookup_service.lookup_mod("con")

    @pytest.mark.asyncio
    async def test_lookup_mod_calculates_total_downloads(
        self, lookup_service: ModService
    ) -> None:
        """lookup_mod() sums downloads across all releases."""
        import respx
        from httpx import Response

        mod_with_multiple_releases = {
            **LOOKUP_MOD_COMPATIBLE,
            "releases": [
                {
                    "releaseid": 27001,
                    "modversion": "1.8.3",
                    "filename": "smithingplus_1.8.3.zip",
                    "fileid": 59176,
                    "downloads": 30000,
                    "tags": ["1.21.3"],
                },
                {
                    "releaseid": 26000,
                    "modversion": "1.8.2",
                    "filename": "smithingplus_1.8.2.zip",
                    "fileid": 58000,
                    "downloads": 15000,
                    "tags": ["1.21.0"],
                },
                {
                    "releaseid": 25000,
                    "modversion": "1.8.1",
                    "filename": "smithingplus_1.8.1.zip",
                    "fileid": 57000,
                    "downloads": 5000,
                    "tags": ["1.20.5"],
                },
            ],
        }

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": mod_with_multiple_releases},
                )
            )

            result = await lookup_service.lookup_mod("smithingplus")

        assert result.downloads == 50000  # 30000 + 15000 + 5000

    @pytest.mark.asyncio
    async def test_lookup_mod_no_releases(self, lookup_service: ModService) -> None:
        """lookup_mod() raises ModNotFoundError when mod has no releases."""
        import respx
        from httpx import Response

        mod_without_releases = {
            "modid": 1234,
            "name": "No Releases Mod",
            "urlalias": "noreleases",
            "author": "someone",
            "releases": [],  # Empty releases
        }

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/noreleases").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": mod_without_releases},
                )
            )

            with pytest.raises(ModNotFoundError) as exc_info:
                await lookup_service.lookup_mod("noreleases")

            assert exc_info.value.slug == "noreleases"

    @pytest.mark.asyncio
    async def test_lookup_mod_incompatible_many_tags(
        self, lookup_service: ModService
    ) -> None:
        """lookup_mod() truncates compatibility message with many compatible tags."""
        import respx
        from httpx import Response

        mod_with_many_tags = {
            "modid": 1234,
            "name": "Many Tags Mod",
            "urlalias": "manytags",
            "author": "someone",
            "text": None,
            "side": "Both",
            "releases": [
                {
                    "releaseid": 10000,
                    "modversion": "1.5.0",
                    "filename": "manytags_1.5.0.zip",
                    "fileid": 10000,
                    "downloads": 5000,
                    "tags": ["1.18.0", "1.18.1", "1.18.2", "1.18.3", "1.18.4"],
                },
            ],
        }

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/manytags").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": mod_with_many_tags},
                )
            )

            result = await lookup_service.lookup_mod("manytags")

        assert result.compatibility.status == "incompatible"
        assert result.compatibility.message is not None
        # Should show first 3 tags with ellipsis
        assert "1.18.0" in result.compatibility.message
        assert "1.18.1" in result.compatibility.message
        assert "1.18.2" in result.compatibility.message
        assert "..." in result.compatibility.message

    @pytest.mark.asyncio
    async def test_lookup_mod_incompatible_no_tags(
        self,
        temp_dirs: tuple[Path, Path],
        restart_state: PendingRestartState,
    ) -> None:
        """lookup_mod() handles incompatible mod with no tags."""
        import respx
        from httpx import Response

        state_dir, mods_dir = temp_dirs
        service = ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            restart_state=restart_state,
            game_version="1.21.3",
        )

        mod_without_tags = {
            "modid": 1234,
            "name": "No Tags Mod",
            "urlalias": "notags",
            "author": "someone",
            "text": None,
            "side": "Both",
            "releases": [
                {
                    "releaseid": 10000,
                    "modversion": "1.5.0",
                    "filename": "notags_1.5.0.zip",
                    "fileid": 10000,
                    "downloads": 5000,
                    "tags": [],  # No tags = incompatible
                },
            ],
        }

        with respx.mock:
            respx.get("https://mods.vintagestory.at/api/mod/notags").mock(
                return_value=Response(
                    200,
                    json={"statuscode": "200", "mod": mod_without_tags},
                )
            )

            result = await service.lookup_mod("notags")

        # Mods with empty tags are marked as not_verified (not incompatible)
        assert result.compatibility.status == "not_verified"

    @pytest.mark.asyncio
    async def test_lookup_mod_incompatible_none_tags_message(
        self, lookup_service: ModService
    ) -> None:
        """lookup_mod() generates fallback message when incompatible with no tags list."""
        # This tests the line 347 code path: incompatible status with None/empty tags
        # We need to trigger _build_compatibility_message with status="incompatible"
        # and compatible_tags being falsy (None or empty)

        # We'll directly test the _build_compatibility_message method
        message = lookup_service._build_compatibility_message(
            status="incompatible",
            mod_version="2.0.0",
            game_version="1.21.3",
            compatible_tags=None,  # This triggers line 347
        )

        assert message is not None
        assert "2.0.0" in message
        assert "not compatible with 1.21.3" in message
        assert "Installation may cause issues" in message

    @pytest.mark.asyncio
    async def test_lookup_mod_incompatible_empty_tags_list(
        self, lookup_service: ModService
    ) -> None:
        """lookup_mod() generates fallback message when incompatible with empty tags list."""
        # This tests line 347: empty list [] triggers the else branch
        message = lookup_service._build_compatibility_message(
            status="incompatible",
            mod_version="1.5.0",
            game_version="1.21.3",
            compatible_tags=[],  # Empty list triggers line 347
        )

        assert message is not None
        assert "1.5.0" in message
        assert "not compatible with 1.21.3" in message
        assert "Installation may cause issues" in message
