"""Additional tests for ModStateManager to improve coverage.

This file contains targeted tests for specific edge cases and error paths
that were missing from the main test suite.
"""

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from vintagestory_api.models.mods import ModState
from vintagestory_api.services.mod_state import ModStateManager


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    return state_dir


@pytest.fixture
def temp_mods_dir(tmp_path: Path) -> Path:
    """Create a temporary mods directory."""
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir(parents=True)
    return mods_dir


@pytest.fixture
def state_manager(temp_state_dir: Path, temp_mods_dir: Path) -> ModStateManager:
    """Create a ModStateManager with test directories."""
    return ModStateManager(
        state_dir=temp_state_dir,
        mods_dir=temp_mods_dir,
    )


class TestSaveOSErrorCleanup:
    """Tests for line 128: temp_file.unlink() in OSError handling."""

    def test_save_cleans_up_existing_temp_file_on_rename_error(
        self, state_manager: ModStateManager, temp_state_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save() cleans up temp file if it exists when rename fails."""
        now = datetime.now(UTC)
        state = ModState(
            filename="test.zip",
            slug="test",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("test.zip", state)

        # Pre-create the temp file to ensure cleanup path is exercised
        temp_file = temp_state_dir / "mods.json.tmp"

        # Mock write_text to succeed (creates temp file)
        original_write_text = Path.write_text

        # Mock rename to raise OSError AFTER temp file is written
        original_rename = Path.rename

        def raise_os_error_on_rename(self: Path, target: Any) -> None:
            if str(self).endswith(".tmp"):
                # File should exist at this point from write_text
                if not self.exists():
                    # Ensure it exists for the cleanup test
                    self.write_text("{}")
                raise OSError("Simulated rename failure")
            return original_rename(self, target)

        monkeypatch.setattr(Path, "rename", raise_os_error_on_rename)

        # save() should raise OSError
        with pytest.raises(OSError, match="Simulated rename failure"):
            state_manager.save()

        # Temp file should be cleaned up (line 128)
        assert not temp_file.exists()

    def test_save_handles_cleanup_when_temp_file_already_removed(
        self, state_manager: ModStateManager, temp_state_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save() handles case where temp file doesn't exist during cleanup."""
        now = datetime.now(UTC)
        state = ModState(
            filename="test.zip",
            slug="test",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("test.zip", state)

        # Mock rename to raise OSError without creating temp file
        def raise_os_error_on_rename(self: Path, target: Any) -> None:
            if str(self).endswith(".tmp"):
                # Don't create the file - simulate it not existing
                raise OSError("Rename failed")
            raise OSError("Unexpected call")

        monkeypatch.setattr(Path, "rename", raise_os_error_on_rename)

        # save() should raise OSError
        with pytest.raises(OSError, match="Rename failed"):
            state_manager.save()

        # No temp file should exist
        temp_file = temp_state_dir / "mods.json.tmp"
        assert not temp_file.exists()


class TestCacheModinfoPathTraversal:
    """Tests for lines 331-336: path traversal validation in _cache_modinfo()."""

    def test_cache_modinfo_warns_on_double_dot_in_slug(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """_cache_modinfo() returns early for '..' in slug (lines 331-336)."""
        modinfo_data = {"modid": "../evil", "name": "Evil", "version": "1.0.0"}

        # Should not raise, but should not create cache
        state_manager._cache_modinfo("../evil", "1.0.0", modinfo_data)

        # No cache should be created
        # Verify no directories were created under mods/
        mods_cache_dir = temp_state_dir / "mods"
        if mods_cache_dir.exists():
            # Should be empty or not contain the malicious path
            assert not (mods_cache_dir / ".." / "evil").exists()
            assert not (mods_cache_dir / "evil").exists()

    def test_cache_modinfo_warns_on_double_dot_in_version(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """_cache_modinfo() returns early for '..' in version (lines 331-336)."""
        modinfo_data = {"modid": "testmod", "name": "Test", "version": "../1.0.0"}

        # Should not raise, but should not create cache
        state_manager._cache_modinfo("testmod", "../1.0.0", modinfo_data)

        # No cache should be created
        mods_cache_dir = temp_state_dir / "mods" / "testmod"
        if mods_cache_dir.exists():
            assert not (mods_cache_dir / ".." / "1.0.0").exists()

    def test_cache_modinfo_warns_on_slash_in_slug(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """_cache_modinfo() returns early for '/' in slug (lines 331-336)."""
        modinfo_data = {"modid": "evil/mod", "name": "Evil", "version": "1.0.0"}

        # Should not raise, but should not create cache
        state_manager._cache_modinfo("evil/mod", "1.0.0", modinfo_data)

        # No cache should be created with the slash
        assert not (temp_state_dir / "mods" / "evil" / "mod" / "1.0.0" / "modinfo.json").exists()

    def test_cache_modinfo_warns_on_slash_in_version(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """_cache_modinfo() returns early for '/' in version (lines 331-336)."""
        modinfo_data = {"modid": "testmod", "name": "Test", "version": "1/0/0"}

        # Should not raise, but should not create cache
        state_manager._cache_modinfo("testmod", "1/0/0", modinfo_data)

        # No cache should be created with slashes in version
        testmod_cache = temp_state_dir / "mods" / "testmod"
        if testmod_cache.exists():
            assert not (testmod_cache / "1" / "0" / "0" / "modinfo.json").exists()


class TestGetCachedMetadataPathTraversal:
    """Tests for line 363: path traversal return in get_cached_metadata()."""

    def test_get_cached_metadata_returns_none_for_double_dot_slug(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None for '..' in slug (line 363)."""
        result = state_manager.get_cached_metadata("../evil", "1.0.0")
        assert result is None

    def test_get_cached_metadata_returns_none_for_double_dot_version(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None for '..' in version (line 363)."""
        result = state_manager.get_cached_metadata("testmod", "../1.0.0")
        assert result is None

    def test_get_cached_metadata_returns_none_for_slash_slug(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None for '/' in slug (line 363)."""
        result = state_manager.get_cached_metadata("evil/mod", "1.0.0")
        assert result is None

    def test_get_cached_metadata_returns_none_for_slash_version(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None for '/' in version (line 363)."""
        result = state_manager.get_cached_metadata("testmod", "1/0/0")
        assert result is None

    def test_get_cached_metadata_returns_none_for_combined_traversal(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None for combined '..' and '/' (line 363)."""
        # Test multiple traversal attempts
        assert state_manager.get_cached_metadata("../../etc", "passwd") is None
        assert state_manager.get_cached_metadata("etc/../../root", "1.0.0") is None
        assert state_manager.get_cached_metadata("mod", "../../etc/passwd") is None


class TestScanModsDirectoryNotFound:
    """Tests for lines 391-392: mods_directory_not_found when directory doesn't exist."""

    def test_scan_mods_directory_logs_when_directory_missing(
        self, tmp_path: Path
    ) -> None:
        """scan_mods_directory() returns empty list when mods dir doesn't exist (lines 391-392)."""
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)

        # Don't create mods_dir - it doesn't exist
        mods_dir = tmp_path / "nonexistent_mods_directory"

        manager = ModStateManager(state_dir=state_dir, mods_dir=mods_dir)

        # This should hit lines 391-392
        filenames = manager.scan_mods_directory()

        assert filenames == []
        assert not mods_dir.exists()

    def test_scan_mods_directory_handles_deleted_directory(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """scan_mods_directory() handles case where directory is deleted after init."""
        # Directory exists at init
        assert temp_mods_dir.exists()

        # Delete the directory
        temp_mods_dir.rmdir()

        # Should handle gracefully and return empty list (lines 391-392)
        filenames = state_manager.scan_mods_directory()
        assert filenames == []


class TestExtractModinfoPathTraversal:
    """Tests for path traversal detection in _extract_modinfo_from_zip()."""

    def test_extract_modinfo_blocks_traversal_in_modinfo_path(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """_extract_modinfo_from_zip() blocks path traversal attempts in zip member paths."""
        zip_path = temp_mods_dir / "malicious_traversal.zip"
        modinfo_content = json.dumps({
            "modid": "evilmod",
            "name": "Evil Mod",
            "version": "1.0.0",
        })

        # Create zip with various traversal attempts
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Try multiple traversal patterns
            zf.writestr("../../../etc/modinfo.json", modinfo_content)
            zf.writestr("safe/../../modinfo.json", modinfo_content)
            zf.writestr("/etc/modinfo.json", modinfo_content)

        # Should not extract from malicious paths - returns None
        result = state_manager._extract_modinfo_from_zip(zip_path)
        assert result is None

    def test_extract_modinfo_accepts_safe_nested_path(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """_extract_modinfo_from_zip() accepts safe nested paths."""
        zip_path = temp_mods_dir / "safe_nested.zip"
        modinfo_content = json.dumps({
            "modid": "safemod",
            "name": "Safe Mod",
            "version": "1.0.0",
        })

        # Create zip with safe nested path
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("content/data/modinfo.json", modinfo_content)

        # Should extract from safe path
        result = state_manager._extract_modinfo_from_zip(zip_path)
        assert result is not None
        assert result["modid"] == "safemod"
