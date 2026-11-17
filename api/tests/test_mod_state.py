"""Unit tests for ModStateManager service."""

import json
import re
import zipfile
from collections.abc import Generator
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from vintagestory_api.models.mods import ModState
from vintagestory_api.services.mod_state import ModStateManager, ModSyncSummary
from vintagestory_api.services.pending_restart import PendingRestartState


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


class TestModStateManagerInit:
    """Tests for ModStateManager initialization."""

    def test_creates_with_directories(self, temp_state_dir: Path, temp_mods_dir: Path) -> None:
        """ModStateManager initializes with state and mods directories."""
        manager = ModStateManager(
            state_dir=temp_state_dir,
            mods_dir=temp_mods_dir,
        )
        assert manager.state_dir == temp_state_dir
        assert manager.mods_dir == temp_mods_dir

    def test_state_file_path(self, state_manager: ModStateManager) -> None:
        """State file is at state_dir/mods.json."""
        assert state_manager.state_file.name == "mods.json"


class TestModStateManagerLoad:
    """Tests for loading mod state from file."""

    def test_load_creates_empty_state_if_no_file(self, state_manager: ModStateManager) -> None:
        """load() returns empty dict if state file doesn't exist."""
        state_manager.load()
        assert state_manager.list_mods() == []

    def test_load_reads_existing_state(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """load() reads state from existing mods.json."""
        state_data = {
            "testmod_1.0.0.zip": {
                "filename": "testmod_1.0.0.zip",
                "slug": "testmod",
                "version": "1.0.0",
                "enabled": True,
                "installed_at": "2025-12-29T10:30:00Z",
            }
        }
        (temp_state_dir / "mods.json").write_text(json.dumps(state_data))

        state_manager.load()
        mods = state_manager.list_mods()

        assert len(mods) == 1
        assert mods[0].slug == "testmod"
        assert mods[0].version == "1.0.0"
        assert mods[0].enabled is True

    def test_load_handles_corrupt_json(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """load() handles corrupt JSON by starting fresh."""
        (temp_state_dir / "mods.json").write_text("{ invalid json")

        # Should not raise, should start with empty state
        state_manager.load()
        assert state_manager.list_mods() == []

    def test_load_handles_empty_file(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """load() handles empty state file by starting fresh."""
        (temp_state_dir / "mods.json").write_text("")

        # Should not raise, should start with empty state
        state_manager.load()
        assert state_manager.list_mods() == []

    def test_load_handles_valid_json_invalid_schema(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """load() handles valid JSON with invalid mod state schema."""
        # Valid JSON but missing required fields like 'filename', 'slug', etc.
        invalid_state = {
            "testmod_1.0.0.zip": {
                "not_a_valid_field": "garbage",
                # Missing: filename, slug, version, enabled, installed_at
            }
        }
        (temp_state_dir / "mods.json").write_text(json.dumps(invalid_state))

        # Should not raise, should start with empty state (Pydantic validation fails)
        state_manager.load()
        assert state_manager.list_mods() == []

    def test_load_handles_non_dict_json(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """load() handles JSON that is not a dict (e.g., array, string)."""
        # Valid JSON but wrong structure (array instead of dict)
        (temp_state_dir / "mods.json").write_text('["not", "a", "dict"]')

        # Should not raise, should start with empty state
        state_manager.load()
        assert state_manager.list_mods() == []

    def test_load_handles_null_json(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """load() handles JSON null value."""
        (temp_state_dir / "mods.json").write_text("null")

        # Should not raise, should start with empty state
        state_manager.load()
        assert state_manager.list_mods() == []


class TestModStateManagerSave:
    """Tests for saving mod state to file."""

    def test_save_writes_state_file(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """save() writes state to mods.json."""
        now = datetime(2025, 12, 29, 10, 30, 0, tzinfo=UTC)
        state = ModState(
            filename="testmod_1.0.0.zip",
            slug="testmod",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("testmod_1.0.0.zip", state)
        state_manager.save()

        # Verify file was written
        state_file = temp_state_dir / "mods.json"
        assert state_file.exists()

        # Verify content
        saved_data = json.loads(state_file.read_text())
        assert "testmod_1.0.0.zip" in saved_data
        assert saved_data["testmod_1.0.0.zip"]["slug"] == "testmod"

    def test_save_uses_atomic_write(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """save() uses temp file + rename for atomic write."""
        now = datetime.now(UTC)
        state = ModState(
            filename="testmod.zip",
            slug="testmod",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("testmod.zip", state)
        state_manager.save()

        # After save, there should be no .tmp file
        tmp_files = list(temp_state_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

        # State file should exist
        assert (temp_state_dir / "mods.json").exists()

    def test_save_creates_directory_if_missing(self, tmp_path: Path) -> None:
        """save() creates state directory if it doesn't exist."""
        state_dir = tmp_path / "nonexistent" / "state"
        mods_dir = tmp_path / "mods"
        mods_dir.mkdir(parents=True)

        manager = ModStateManager(state_dir=state_dir, mods_dir=mods_dir)
        now = datetime.now(UTC)
        state = ModState(
            filename="test.zip",
            slug="test",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        manager.set_mod_state("test.zip", state)
        manager.save()

        assert (state_dir / "mods.json").exists()

    def test_save_cleans_up_temp_file_on_error(
        self, state_manager: ModStateManager, temp_state_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save() cleans up temp file if rename fails with OSError."""
        now = datetime.now(UTC)
        state = ModState(
            filename="test.zip",
            slug="test",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("test.zip", state)

        # Mock rename to raise OSError
        original_rename = Path.rename

        def raise_os_error(self: Path, target: Any) -> Path:
            if ".tmp" in str(self):
                # Ensure temp file exists to test cleanup
                self.touch()
                raise OSError("Rename failed")
            return original_rename(self, target)

        monkeypatch.setattr(Path, "rename", raise_os_error)

        # save() should raise OSError and clean up temp file
        temp_file = temp_state_dir / "mods.json.tmp"
        with pytest.raises(OSError):
            state_manager.save()

        # Temp file should be cleaned up
        assert not temp_file.exists()


class TestModStateManagerDiskIOErrors:
    """Tests for disk I/O error handling in ModStateManager."""

    def test_load_handles_state_file_is_directory(
        self, temp_state_dir: Path, temp_mods_dir: Path
    ) -> None:
        """load() handles case when state file path is a directory."""
        # Create a directory where the state file should be
        state_file_as_dir = temp_state_dir / "mods.json"
        state_file_as_dir.mkdir(parents=True)

        manager = ModStateManager(state_dir=temp_state_dir, mods_dir=temp_mods_dir)
        # Should not raise, should start with empty state
        manager.load()
        assert manager.list_mods() == []

    def test_load_handles_permission_error(
        self, temp_state_dir: Path, temp_mods_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load() handles PermissionError when reading state file."""
        # Create a valid state file first
        state_file = temp_state_dir / "mods.json"
        state_file.write_text("{}")

        manager = ModStateManager(state_dir=temp_state_dir, mods_dir=temp_mods_dir)

        # Mock read_text to raise PermissionError
        def raise_permission_error(*args: object, **kwargs: object) -> str:
            raise PermissionError("Access denied")

        monkeypatch.setattr(Path, "read_text", raise_permission_error)

        # Should not raise, should start with empty state
        manager.load()
        assert manager.list_mods() == []

    def test_save_handles_permission_error(
        self, temp_state_dir: Path, temp_mods_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save() handles PermissionError when writing state file."""
        manager = ModStateManager(state_dir=temp_state_dir, mods_dir=temp_mods_dir)
        now = datetime.now(UTC)
        state = ModState(
            filename="test.zip",
            slug="test",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        manager.set_mod_state("test.zip", state)

        # Mock write_text to raise PermissionError
        original_write_text = Path.write_text

        def raise_permission_error(self: Path, *args: Any, **kwargs: Any) -> int:
            if "mods.json" in str(self) or ".tmp" in str(self):
                raise PermissionError("Access denied")
            return original_write_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", raise_permission_error)

        # save() should raise PermissionError since it's a critical operation
        with pytest.raises(PermissionError):
            manager.save()

    def test_save_handles_directory_creation_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save() handles OSError when creating state directory."""
        state_dir = tmp_path / "nonexistent" / "state"
        mods_dir = tmp_path / "mods"
        mods_dir.mkdir(parents=True)

        manager = ModStateManager(state_dir=state_dir, mods_dir=mods_dir)
        now = datetime.now(UTC)
        state = ModState(
            filename="test.zip",
            slug="test",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        manager.set_mod_state("test.zip", state)

        # Mock mkdir to raise OSError
        original_mkdir = Path.mkdir

        def raise_os_error(self: Path, *args: Any, **kwargs: Any) -> None:
            if "nonexistent" in str(self):
                raise OSError("Disk full")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", raise_os_error)

        # save() should raise OSError since it's a critical operation
        with pytest.raises(OSError):
            manager.save()


class TestModStateManagerGetMod:
    """Tests for getting individual mod state."""

    def test_get_mod_returns_none_if_not_found(self, state_manager: ModStateManager) -> None:
        """get_mod() returns None for unknown filename."""
        assert state_manager.get_mod("nonexistent.zip") is None

    def test_get_mod_returns_state_by_filename(self, state_manager: ModStateManager) -> None:
        """get_mod() returns ModState for known filename."""
        now = datetime.now(UTC)
        state = ModState(
            filename="testmod_1.0.0.zip",
            slug="testmod",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("testmod_1.0.0.zip", state)

        result = state_manager.get_mod("testmod_1.0.0.zip")
        assert result is not None
        assert result.slug == "testmod"
        assert result.version == "1.0.0"


class TestModStateManagerListMods:
    """Tests for listing all mod states."""

    def test_list_mods_empty_initially(self, state_manager: ModStateManager) -> None:
        """list_mods() returns empty list initially."""
        assert state_manager.list_mods() == []

    def test_list_mods_returns_all_mods(self, state_manager: ModStateManager) -> None:
        """list_mods() returns all stored mod states."""
        now = datetime.now(UTC)

        state1 = ModState(
            filename="mod1.zip",
            slug="mod1",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state2 = ModState(
            filename="mod2.zip",
            slug="mod2",
            version="2.0.0",
            enabled=False,
            installed_at=now,
        )
        state_manager.set_mod_state("mod1.zip", state1)
        state_manager.set_mod_state("mod2.zip", state2)

        mods = state_manager.list_mods()
        assert len(mods) == 2
        slugs = {m.slug for m in mods}
        assert slugs == {"mod1", "mod2"}


class TestModStateManagerFilenames:
    """filenames() returns exactly the state's keys (Story 19.4, Epic 19 ADR-8)."""

    def test_filenames_follow_set_and_remove(self, state_manager: ModStateManager) -> None:
        now = datetime.now(UTC)
        assert state_manager.filenames() == []

        for name, slug in (("Foo.zip", "foo"), ("bar.zip.disabled", "bar")):
            state_manager.set_mod_state(
                name,
                ModState(filename=name, slug=slug, version="1.0.0", enabled=True, installed_at=now),
            )
        assert sorted(state_manager.filenames()) == ["Foo.zip", "bar.zip.disabled"]

        state_manager.remove_mod("Foo.zip")
        assert state_manager.filenames() == ["bar.zip.disabled"]


class TestModStateManagerSetModState:
    """Tests for updating mod state."""

    def test_set_mod_state_adds_new_mod(self, state_manager: ModStateManager) -> None:
        """set_mod_state() adds new mod to state."""
        now = datetime.now(UTC)
        state = ModState(
            filename="newmod.zip",
            slug="newmod",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("newmod.zip", state)

        result = state_manager.get_mod("newmod.zip")
        assert result is not None
        assert result.slug == "newmod"

    def test_set_mod_state_updates_existing_mod(self, state_manager: ModStateManager) -> None:
        """set_mod_state() updates existing mod state."""
        now = datetime.now(UTC)
        state1 = ModState(
            filename="testmod.zip",
            slug="testmod",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("testmod.zip", state1)

        # Update to disabled
        state2 = ModState(
            filename="testmod.zip",
            slug="testmod",
            version="1.0.0",
            enabled=False,
            installed_at=now,
        )
        state_manager.set_mod_state("testmod.zip", state2)

        result = state_manager.get_mod("testmod.zip")
        assert result is not None
        assert result.enabled is False


class TestModStateManagerRemoveMod:
    """Tests for removing mod from state."""

    def test_remove_mod_deletes_from_state(self, state_manager: ModStateManager) -> None:
        """remove_mod() removes mod from state index."""
        now = datetime.now(UTC)
        state = ModState(
            filename="testmod.zip",
            slug="testmod",
            version="1.0.0",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("testmod.zip", state)
        assert state_manager.get_mod("testmod.zip") is not None

        state_manager.remove_mod("testmod.zip")
        assert state_manager.get_mod("testmod.zip") is None

    def test_remove_mod_ignores_nonexistent(self, state_manager: ModStateManager) -> None:
        """remove_mod() silently ignores non-existent mods."""
        # Should not raise
        state_manager.remove_mod("nonexistent.zip")


class TestModStateManagerGetModBySlug:
    """Tests for finding mod by slug."""

    def test_get_mod_by_slug_returns_none_if_not_found(
        self, state_manager: ModStateManager
    ) -> None:
        """get_mod_by_slug() returns None for unknown slug."""
        assert state_manager.get_mod_by_slug("nonexistent") is None

    def test_get_mod_by_slug_finds_mod(self, state_manager: ModStateManager) -> None:
        """get_mod_by_slug() finds mod by slug."""
        now = datetime.now(UTC)
        state = ModState(
            filename="smithingplus_1.8.3.zip",
            slug="smithingplus",
            version="1.8.3",
            enabled=True,
            installed_at=now,
        )
        state_manager.set_mod_state("smithingplus_1.8.3.zip", state)

        result = state_manager.get_mod_by_slug("smithingplus")
        assert result is not None
        assert result.filename == "smithingplus_1.8.3.zip"


# --- Task 3: import_mod and metadata caching tests ---


def create_mod_zip(
    zip_path: Path,
    modinfo: dict[str, object],
    extra_files: dict[str, bytes] | None = None,
) -> None:
    """Helper to create a test mod zip file.

    Args:
        zip_path: Path where zip file will be created.
        modinfo: Dictionary to serialize as modinfo.json.
        extra_files: Optional dict of {filename: content} for additional files.
    """
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("modinfo.json", json.dumps(modinfo))
        if extra_files:
            for name, content in extra_files.items():
                zf.writestr(name, content)


class TestImportMod:
    """Tests for import_mod() function."""

    def test_import_mod_extracts_metadata(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() extracts modinfo.json and returns ModMetadata."""
        zip_path = temp_mods_dir / "testmod_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {
                "modid": "testmod",
                "name": "Test Mod",
                "version": "1.0.0",
                "authors": ["Author1"],
                "description": "A test mod",
            },
        )

        metadata = state_manager.import_mod(zip_path)

        assert metadata.modid == "testmod"
        assert metadata.name == "Test Mod"
        assert metadata.version == "1.0.0"
        assert metadata.authors == ["Author1"]
        assert metadata.description == "A test mod"

    def test_import_mod_accepts_universal_side(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """A modinfo with side "Universal" imports its real modid and version (Better Ruins)."""
        zip_path = temp_mods_dir / "BetterRuinsv0.6.4.zip"
        create_mod_zip(
            zip_path,
            {
                "type": "content",
                "modid": "betterruins",
                "name": "BetterRuins",
                "version": "0.6.4",
                "side": "Universal",
                "dependencies": {"game": "1.22.0"},
            },
        )

        metadata = state_manager.import_mod(zip_path)

        assert (metadata.modid, metadata.version, metadata.side) == ("betterruins", "0.6.4", "Both")

    def test_import_mod_reads_capitalized_keys(
        self, state_manager: ModStateManager, temp_mods_dir: Path, temp_state_dir: Path
    ) -> None:
        """Top-level keys are matched without case: an archive with "ModID" and "Version"
        imports its real mod ID and version, and its cache is readable (VSS-0jl)."""
        zip_path = temp_mods_dir / "Demo_v1.2.3.zip"
        create_mod_zip(
            zip_path,
            {
                "ModID": "demo",
                "Name": "Demo",
                "Version": "1.2.3",
                "Authors": ["a"],
                "Side": "Universal",
            },
        )

        metadata = state_manager.import_mod(zip_path)

        assert (metadata.modid, metadata.version, metadata.side) == ("demo", "1.2.3", "Both")
        assert metadata.authors == ["a"]
        cache_path = temp_state_dir / "mods" / "demo" / "1.2.3" / "modinfo.json"
        assert json.loads(cache_path.read_text()) == {
            "modid": "demo",
            "name": "Demo",
            "version": "1.2.3",
            "authors": ["a"],
            "side": "Universal",
        }
        cached = state_manager.get_cached_metadata("demo", "1.2.3")
        assert cached is not None
        assert (cached.modid, cached.name, cached.version) == ("demo", "Demo", "1.2.3")

    def test_import_mod_lowercases_only_top_level_keys(
        self, state_manager: ModStateManager, temp_mods_dir: Path, temp_state_dir: Path
    ) -> None:
        """Values, including nested objects, keep their keys; the mod ID keeps its spelling."""
        zip_path = temp_mods_dir / "demo.zip"
        create_mod_zip(
            zip_path,
            {
                "ModID": "Demo",
                "Name": "Demo",
                "Version": "1.2.3",
                "Dependencies": {"Game": "1.20"},
            },
        )

        metadata = state_manager.import_mod(zip_path)

        assert metadata.modid == "Demo"
        cache_path = temp_state_dir / "mods" / "Demo" / "1.2.3" / "modinfo.json"
        cached = json.loads(cache_path.read_text())
        assert cached["dependencies"] == {"Game": "1.20"}

    def test_import_mod_later_key_wins_when_keys_differ_only_in_case(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        zip_path = temp_mods_dir / "demo.zip"
        create_mod_zip(
            zip_path,
            {"modid": "first", "ModID": "second", "name": "Demo", "version": "1.0.0"},
        )

        assert state_manager.import_mod(zip_path).modid == "second"

    def test_import_mod_caches_modinfo(
        self, state_manager: ModStateManager, temp_mods_dir: Path, temp_state_dir: Path
    ) -> None:
        """import_mod() caches modinfo.json in state directory."""
        zip_path = temp_mods_dir / "smithingplus_1.8.3.zip"
        create_mod_zip(
            zip_path,
            {
                "modid": "smithingplus",
                "name": "Smithing Plus",
                "version": "1.8.3",
            },
        )

        state_manager.import_mod(zip_path)

        # Check cache location: state/mods/<slug>/<version>/modinfo.json
        cache_path = temp_state_dir / "mods" / "smithingplus" / "1.8.3" / "modinfo.json"
        assert cache_path.exists()

        # Verify content
        cached_data = json.loads(cache_path.read_text())
        assert cached_data["modid"] == "smithingplus"
        assert cached_data["version"] == "1.8.3"

    def test_import_mod_handles_minimal_modinfo(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() handles modinfo with only required fields."""
        zip_path = temp_mods_dir / "minimal_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {
                "modid": "minimal",
                "name": "Minimal Mod",
                "version": "1.0.0",
            },
        )

        metadata = state_manager.import_mod(zip_path)

        assert metadata.modid == "minimal"
        assert metadata.authors == []  # Default empty list
        assert metadata.description is None  # Default None

    def test_import_mod_handles_missing_modinfo(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() uses filename fallback if modinfo.json is missing."""
        zip_path = temp_mods_dir / "unknownmod_2.0.0.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("assets/readme.txt", "No modinfo here")

        metadata = state_manager.import_mod(zip_path)

        # Should use filename-derived fallback
        assert metadata.modid == "unknownmod_2.0.0"  # From filename
        assert metadata.name == "unknownmod_2.0.0"  # From filename
        assert metadata.version == "unknown"

    def test_import_mod_handles_corrupt_modinfo(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() uses filename fallback if modinfo.json is corrupt."""
        zip_path = temp_mods_dir / "corruptmod_1.0.0.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("modinfo.json", "{ invalid json")

        metadata = state_manager.import_mod(zip_path)

        # Should use filename-derived fallback
        assert metadata.modid == "corruptmod_1.0.0"
        assert metadata.version == "unknown"

    def test_import_mod_handles_bad_zip_file(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() uses filename fallback if zip file is completely corrupt."""
        zip_path = temp_mods_dir / "badzip_1.0.0.zip"
        # Write garbage data that isn't a valid zip
        zip_path.write_bytes(b"this is not a zip file at all")

        metadata = state_manager.import_mod(zip_path)

        # Should use filename-derived fallback (BadZipFile is caught)
        assert metadata.modid == "badzip_1.0.0"
        assert metadata.version == "unknown"

    def test_import_mod_handles_truncated_zip(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() uses filename fallback if zip is truncated."""
        zip_path = temp_mods_dir / "truncated_2.0.0.zip"
        # Write partial zip header but truncated
        zip_path.write_bytes(b"PK\x03\x04" + b"\x00" * 20)  # Incomplete zip

        metadata = state_manager.import_mod(zip_path)

        # Should use filename-derived fallback
        assert metadata.modid == "truncated_2.0.0"
        assert metadata.version == "unknown"

    def test_import_mod_handles_empty_zip(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() uses filename fallback if zip is empty (no files)."""
        zip_path = temp_mods_dir / "emptyzip_1.0.0.zip"
        # Create a valid zip with no files inside
        with zipfile.ZipFile(zip_path, "w"):
            pass  # Empty zip

        metadata = state_manager.import_mod(zip_path)

        # Should use filename-derived fallback
        assert metadata.modid == "emptyzip_1.0.0"
        assert metadata.version == "unknown"

    def test_import_mod_handles_modinfo_invalid_schema(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() uses filename fallback if modinfo.json has invalid schema."""
        zip_path = temp_mods_dir / "invalidschema_2.0.0.zip"
        # Valid JSON but missing required fields (modid, name, version)
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "modinfo.json",
                json.dumps({"not_modid": "something", "random_field": 42}),
            )

        metadata = state_manager.import_mod(zip_path)

        # Should use filename-derived fallback since required fields are missing
        assert metadata.modid == "invalidschema_2.0.0"
        assert metadata.version == "unknown"

    def test_import_mod_handles_modinfo_null_values(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() handles modinfo.json with null values for required fields."""
        zip_path = temp_mods_dir / "nullfields_1.5.0.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "modinfo.json",
                json.dumps({"modid": None, "name": None, "version": None}),
            )

        metadata = state_manager.import_mod(zip_path)

        # Should use filename-derived fallback since values are null
        assert metadata.modid == "nullfields_1.5.0"
        assert metadata.version == "unknown"

    def test_import_mod_handles_modinfo_empty_strings(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() handles modinfo.json with empty string values."""
        zip_path = temp_mods_dir / "emptystrings_3.0.0.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "modinfo.json",
                json.dumps({"modid": "", "name": "", "version": ""}),
            )

        metadata = state_manager.import_mod(zip_path)

        # Empty strings are technically valid but may cause issues
        # The current implementation accepts them as-is
        # This test documents the current behavior
        assert metadata.modid == ""
        assert metadata.version == ""

    def test_import_mod_handles_modinfo_array_instead_of_object(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() uses fallback if modinfo.json is an array not object."""
        zip_path = temp_mods_dir / "arraymod_1.0.0.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("modinfo.json", '["not", "an", "object"]')

        metadata = state_manager.import_mod(zip_path)

        # Should use filename-derived fallback
        assert metadata.modid == "arraymod_1.0.0"
        assert metadata.version == "unknown"

    def test_import_mod_zip_slip_protection(
        self, state_manager: ModStateManager, temp_mods_dir: Path, temp_state_dir: Path
    ) -> None:
        """import_mod() prevents zip slip attack attempts."""
        zip_path = temp_mods_dir / "malicious.zip"

        # Create a zip with path traversal attempt in the modinfo path
        # Note: We can't actually create a malicious path easily with ZipFile,
        # but we test that normal extraction is safe
        create_mod_zip(
            zip_path,
            {
                "modid": "safemod",
                "name": "Safe Mod",
                "version": "1.0.0",
            },
        )

        metadata = state_manager.import_mod(zip_path)

        # Should extract safely
        assert metadata.modid == "safemod"

        # Cache should be in expected location, not escaped
        cache_path = temp_state_dir / "mods" / "safemod" / "1.0.0" / "modinfo.json"
        assert cache_path.exists()


class TestZipSlipProtection:
    """Tests for zip slip protection via import_mod() (Review Item #3).

    These tests verify that malicious zip files with path traversal attempts
    in their modinfo.json locations are handled safely by falling back to
    filename-derived metadata.
    """

    def test_import_mod_blocks_simple_traversal(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() blocks modinfo.json with simple path traversal (../)."""
        zip_path = temp_mods_dir / "malicious_simple.zip"
        modinfo_content = json.dumps(
            {
                "modid": "evilmod",
                "name": "Evil Mod",
                "version": "1.0.0",
            }
        )

        # Create zip with path traversal in modinfo.json path
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../modinfo.json", modinfo_content)

        metadata = state_manager.import_mod(zip_path)

        # Should use fallback since malicious path is blocked
        assert metadata.modid == "malicious_simple"
        assert metadata.version == "unknown"

    def test_import_mod_blocks_nested_traversal(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() blocks modinfo.json with nested path traversal (subdir/../../)."""
        zip_path = temp_mods_dir / "malicious_nested.zip"
        modinfo_content = json.dumps(
            {
                "modid": "sneakymod",
                "name": "Sneaky Mod",
                "version": "2.0.0",
            }
        )

        # Create zip with nested path traversal
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("subdir/../../etc/modinfo.json", modinfo_content)

        metadata = state_manager.import_mod(zip_path)

        # Should use fallback since malicious path is blocked
        assert metadata.modid == "malicious_nested"
        assert metadata.version == "unknown"

    def test_import_mod_blocks_absolute_path(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() blocks modinfo.json with absolute path."""
        zip_path = temp_mods_dir / "malicious_absolute.zip"
        modinfo_content = json.dumps(
            {
                "modid": "absmod",
                "name": "Absolute Mod",
                "version": "3.0.0",
            }
        )

        # Create zip with absolute path
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("/etc/modinfo.json", modinfo_content)

        metadata = state_manager.import_mod(zip_path)

        # Should use fallback since malicious path is blocked
        assert metadata.modid == "malicious_absolute"
        assert metadata.version == "unknown"

    def test_import_mod_accepts_safe_subdirectory(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() accepts modinfo.json in safe subdirectory."""
        zip_path = temp_mods_dir / "safe_subdir.zip"
        modinfo_content = json.dumps(
            {
                "modid": "safemod",
                "name": "Safe Mod",
                "version": "1.0.0",
            }
        )

        # Create zip with modinfo.json in subdirectory (safe pattern)
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("content/modinfo.json", modinfo_content)

        metadata = state_manager.import_mod(zip_path)

        # Should extract from safe subdirectory
        assert metadata.modid == "safemod"
        assert metadata.version == "1.0.0"

    def test_import_mod_accepts_dots_in_filename(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """import_mod() accepts modinfo.json with dots in directory names (not traversal)."""
        zip_path = temp_mods_dir / "dots_in_name.zip"
        modinfo_content = json.dumps(
            {
                "modid": "dotmod",
                "name": "Dot Mod",
                "version": "1.2.3",
            }
        )

        # Create zip with dots in directory name (safe - not traversal)
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("mod.v1.2.3/modinfo.json", modinfo_content)

        metadata = state_manager.import_mod(zip_path)

        # Should extract normally
        assert metadata.modid == "dotmod"
        assert metadata.version == "1.2.3"


class TestCacheModinfo:
    """Tests for _cache_modinfo() function."""

    def test_cache_modinfo_blocks_path_traversal_in_slug(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """_cache_modinfo() blocks path traversal in slug parameter."""
        modinfo_data: dict[str, object] = {"modid": "../evil", "name": "Evil", "version": "1.0.0"}

        # Should not raise, but should not create cache
        state_manager._cache_modinfo("../evil", "1.0.0", modinfo_data)

        # No cache directory should be created outside state dir
        cache_path = temp_state_dir / "mods" / "../evil" / "1.0.0" / "modinfo.json"
        assert not cache_path.exists()

    def test_cache_modinfo_blocks_path_traversal_in_version(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """_cache_modinfo() blocks path traversal in version parameter."""
        modinfo_data: dict[str, object] = {
            "modid": "testmod",
            "name": "Test",
            "version": "../1.0.0",
        }

        # Should not raise, but should not create cache
        state_manager._cache_modinfo("testmod", "../1.0.0", modinfo_data)

        # No cache directory should be created with traversal
        cache_path = temp_state_dir / "mods" / "testmod" / "../1.0.0" / "modinfo.json"
        assert not cache_path.exists()

    def test_cache_modinfo_blocks_slash_in_slug(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """_cache_modinfo() blocks slash in slug parameter."""
        modinfo_data: dict[str, object] = {"modid": "evil/mod", "name": "Evil", "version": "1.0.0"}

        # Should not raise, but should not create cache
        state_manager._cache_modinfo("evil/mod", "1.0.0", modinfo_data)

        # No cache directory should be created with slash
        cache_path = temp_state_dir / "mods" / "evil/mod" / "1.0.0" / "modinfo.json"
        assert not cache_path.exists()

    def test_cache_modinfo_blocks_slash_in_version(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """_cache_modinfo() blocks slash in version parameter."""
        modinfo_data: dict[str, object] = {"modid": "testmod", "name": "Test", "version": "1/0/0"}

        # Should not raise, but should not create cache
        state_manager._cache_modinfo("testmod", "1/0/0", modinfo_data)

        # No cache directory should be created with slash
        cache_path = temp_state_dir / "mods" / "testmod" / "1/0/0" / "modinfo.json"
        assert not cache_path.exists()


class TestGetCachedMetadata:
    """Tests for get_cached_metadata() function."""

    def test_get_cached_metadata_returns_none_if_not_cached(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None if no cache exists."""
        result = state_manager.get_cached_metadata("nonexistent", "1.0.0")
        assert result is None

    def test_get_cached_metadata_blocks_path_traversal_in_slug(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None for path traversal in slug."""
        result = state_manager.get_cached_metadata("../evil", "1.0.0")
        assert result is None

    def test_get_cached_metadata_blocks_path_traversal_in_version(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None for path traversal in version."""
        result = state_manager.get_cached_metadata("testmod", "../1.0.0")
        assert result is None

    def test_get_cached_metadata_blocks_slash_in_slug(self, state_manager: ModStateManager) -> None:
        """get_cached_metadata() returns None for slash in slug."""
        result = state_manager.get_cached_metadata("evil/mod", "1.0.0")
        assert result is None

    def test_get_cached_metadata_blocks_slash_in_version(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None for slash in version."""
        result = state_manager.get_cached_metadata("testmod", "1/0/0")
        assert result is None

    def test_get_cached_metadata_reads_from_cache(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """get_cached_metadata() reads cached modinfo.json."""
        # Create cache manually
        cache_dir = temp_state_dir / "mods" / "testmod" / "2.0.0"
        cache_dir.mkdir(parents=True)
        (cache_dir / "modinfo.json").write_text(
            json.dumps(
                {
                    "modid": "testmod",
                    "name": "Test Mod",
                    "version": "2.0.0",
                    "authors": ["Author1"],
                }
            )
        )

        metadata = state_manager.get_cached_metadata("testmod", "2.0.0")

        assert metadata is not None
        assert metadata.modid == "testmod"
        assert metadata.name == "Test Mod"
        assert metadata.version == "2.0.0"
        assert metadata.authors == ["Author1"]

    def test_get_cached_metadata_handles_corrupt_cache(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """get_cached_metadata() returns None if cache is corrupt."""
        cache_dir = temp_state_dir / "mods" / "badcache" / "1.0.0"
        cache_dir.mkdir(parents=True)
        (cache_dir / "modinfo.json").write_text("{ not valid json")

        result = state_manager.get_cached_metadata("badcache", "1.0.0")
        assert result is None


# --- Task 4: mod directory scanner tests ---


class TestScanModsDirectory:
    """Tests for scan_mods_directory() function."""

    def test_scan_mods_directory_finds_zip_files(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """scan_mods_directory() discovers .zip files."""
        # Create some mod zips
        create_mod_zip(
            temp_mods_dir / "mod1_1.0.0.zip",
            {"modid": "mod1", "name": "Mod 1", "version": "1.0.0"},
        )
        create_mod_zip(
            temp_mods_dir / "mod2_2.0.0.zip",
            {"modid": "mod2", "name": "Mod 2", "version": "2.0.0"},
        )

        filenames = state_manager.scan_mods_directory()

        assert len(filenames) == 2
        assert "mod1_1.0.0.zip" in filenames
        assert "mod2_2.0.0.zip" in filenames

    def test_scan_mods_directory_ignores_non_zip_files(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """scan_mods_directory() ignores non-.zip files."""
        create_mod_zip(
            temp_mods_dir / "mod1_1.0.0.zip",
            {"modid": "mod1", "name": "Mod 1", "version": "1.0.0"},
        )
        (temp_mods_dir / "readme.txt").write_text("Not a mod")
        (temp_mods_dir / "config.json").write_text("{}")

        filenames = state_manager.scan_mods_directory()

        assert len(filenames) == 1
        assert "mod1_1.0.0.zip" in filenames

    def test_scan_mods_directory_finds_disabled_mods(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """scan_mods_directory() includes .zip.disabled files."""
        create_mod_zip(
            temp_mods_dir / "enabled_1.0.0.zip",
            {"modid": "enabled", "name": "Enabled", "version": "1.0.0"},
        )
        # Create disabled mod (rename after creation)
        disabled_path = temp_mods_dir / "disabled_1.0.0.zip"
        create_mod_zip(
            disabled_path,
            {"modid": "disabled", "name": "Disabled", "version": "1.0.0"},
        )
        disabled_path.rename(temp_mods_dir / "disabled_1.0.0.zip.disabled")

        filenames = state_manager.scan_mods_directory()

        assert len(filenames) == 2
        assert "enabled_1.0.0.zip" in filenames
        assert "disabled_1.0.0.zip.disabled" in filenames

    def test_scan_mods_directory_empty_returns_empty_list(
        self, state_manager: ModStateManager
    ) -> None:
        """scan_mods_directory() returns empty list for empty directory."""
        filenames = state_manager.scan_mods_directory()
        assert filenames == []

    def test_scan_mods_directory_handles_nonexistent_directory(self, tmp_path: Path) -> None:
        """scan_mods_directory() returns empty list if mods directory doesn't exist."""
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        mods_dir = tmp_path / "nonexistent_mods"  # Don't create this directory

        manager = ModStateManager(state_dir=state_dir, mods_dir=mods_dir)
        filenames = manager.scan_mods_directory()

        assert filenames == []


class TestSyncStateWithDisk:
    """Tests for sync_state_with_disk() function."""

    def test_sync_adds_new_mods_to_state(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """sync_state_with_disk() imports new mods found on disk."""
        create_mod_zip(
            temp_mods_dir / "newmod_1.0.0.zip",
            {"modid": "newmod", "name": "New Mod", "version": "1.0.0"},
        )

        state_manager.sync_state_with_disk()

        assert len(state_manager.list_mods()) == 1
        mod = state_manager.get_mod("newmod_1.0.0.zip")
        assert mod is not None
        assert mod.slug == "newmod"
        assert mod.version == "1.0.0"
        assert mod.enabled is True

    def test_sync_removes_deleted_mods_from_state(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """sync_state_with_disk() removes state for mods deleted from disk."""
        # Create mod, sync, then delete
        mod_path = temp_mods_dir / "deleteme_1.0.0.zip"
        create_mod_zip(
            mod_path,
            {"modid": "deleteme", "name": "Delete Me", "version": "1.0.0"},
        )
        state_manager.sync_state_with_disk()
        assert state_manager.get_mod("deleteme_1.0.0.zip") is not None

        # Delete the mod file
        mod_path.unlink()

        # Sync again
        state_manager.sync_state_with_disk()

        assert state_manager.get_mod("deleteme_1.0.0.zip") is None
        assert len(state_manager.list_mods()) == 0

    def test_sync_preserves_existing_state_for_unchanged_mods(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """sync_state_with_disk() doesn't re-import mods already in state."""
        create_mod_zip(
            temp_mods_dir / "existing_1.0.0.zip",
            {"modid": "existing", "name": "Existing", "version": "1.0.0"},
        )

        # First sync
        state_manager.sync_state_with_disk()
        mod_state = state_manager.get_mod("existing_1.0.0.zip")
        assert mod_state is not None
        original_installed_at = mod_state.installed_at

        # Second sync should preserve the existing state
        state_manager.sync_state_with_disk()
        mod_state = state_manager.get_mod("existing_1.0.0.zip")
        assert mod_state is not None
        new_installed_at = mod_state.installed_at

        assert original_installed_at == new_installed_at

    def test_sync_uses_cached_metadata(
        self, state_manager: ModStateManager, temp_mods_dir: Path, temp_state_dir: Path
    ) -> None:
        """sync_state_with_disk() uses cached metadata when available."""
        # Create and import mod first
        create_mod_zip(
            temp_mods_dir / "cachedmod_1.0.0.zip",
            {"modid": "cachedmod", "name": "Cached Mod", "version": "1.0.0"},
        )
        state_manager.sync_state_with_disk()

        # Verify cache exists
        cache_path = temp_state_dir / "mods" / "cachedmod" / "1.0.0" / "modinfo.json"
        assert cache_path.exists()

        # Get the cached metadata
        metadata = state_manager.get_cached_metadata("cachedmod", "1.0.0")
        assert metadata is not None
        assert metadata.name == "Cached Mod"

    def test_sync_detects_disabled_mods(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """sync_state_with_disk() marks .disabled mods as enabled=False."""
        # Create a disabled mod
        zip_path = temp_mods_dir / "disabledmod_1.0.0.zip"
        create_mod_zip(
            zip_path,
            {"modid": "disabledmod", "name": "Disabled Mod", "version": "1.0.0"},
        )
        zip_path.rename(temp_mods_dir / "disabledmod_1.0.0.zip.disabled")

        state_manager.sync_state_with_disk()

        mod = state_manager.get_mod("disabledmod_1.0.0.zip.disabled")
        assert mod is not None
        assert mod.enabled is False

    def test_sync_saves_state_after_changes(
        self, state_manager: ModStateManager, temp_mods_dir: Path, temp_state_dir: Path
    ) -> None:
        """sync_state_with_disk() persists state to mods.json."""
        create_mod_zip(
            temp_mods_dir / "persistmod_1.0.0.zip",
            {"modid": "persistmod", "name": "Persist Mod", "version": "1.0.0"},
        )

        state_manager.sync_state_with_disk()

        # Verify state file was written
        state_file = temp_state_dir / "mods.json"
        assert state_file.exists()

        # Create new manager and load state
        new_manager = ModStateManager(state_dir=temp_state_dir, mods_dir=temp_mods_dir)
        new_manager.load()

        assert new_manager.get_mod("persistmod_1.0.0.zip") is not None


def directory_snapshot(directory: Path) -> list[tuple[str, bytes | None]]:
    """Sorted names in a directory, with each regular file's bytes (None otherwise)."""
    return sorted(
        (p.name, p.read_bytes() if p.is_file() and not p.is_symlink() else None)
        for p in directory.iterdir()
    )


def mod_state_entry(filename: str, slug: str, version: str = "1.0.0") -> ModState:
    """A state entry as an install through the manager leaves it."""
    return ModState(
        filename=filename,
        slug=slug,
        version=version,
        enabled=not filename.endswith(".disabled"),
        installed_at=datetime(2025, 1, 1, tzinfo=UTC),
        asset_id=42,
    )


def patch_zip_member_header(zip_path: Path, *, compression: int | None = None) -> None:
    """Rewrite the one member's headers: set a compression method, or the encryption flag."""
    data = bytearray(zip_path.read_bytes())
    local = data.find(b"PK\x03\x04")
    central = data.find(b"PK\x01\x02")
    if compression is not None:
        data[local + 8 : local + 10] = compression.to_bytes(2, "little")
        data[central + 10 : central + 12] = compression.to_bytes(2, "little")
    else:
        data[local + 6] |= 0x01
        data[central + 8] |= 0x01
    zip_path.write_bytes(bytes(data))


def write_bad_archive(path: Path, kind: str) -> None:
    """Write `path` as one kind of archive the sync cannot use (Story 19.5 AC 4)."""
    if kind == "not-a-zip":
        path.write_bytes(b"this is not a zip archive")
    elif kind == "no-modinfo":
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("readme.txt", "no modinfo here")
    elif kind == "modinfo-array":
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("modinfo.json", json.dumps([{"modid": "bad"}]))
    elif kind == "modinfo-without-modid":
        create_mod_zip(path, {"name": "Bad", "version": "1.0.0"})
    elif kind == "unsupported-compression":
        create_mod_zip(path, {"modid": "badmod", "name": "Bad", "version": "1.0.0"})
        patch_zip_member_header(path, compression=99)
    elif kind == "encrypted":
        create_mod_zip(path, {"modid": "badmod", "name": "Bad", "version": "1.0.0"})
        patch_zip_member_header(path)
    elif kind == "deeply-nested-json":
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("modinfo.json", "[" * 200000)
    else:  # "no-read-permission": any readable archive; the reader is made to raise
        create_mod_zip(path, {"modid": "badmod", "name": "Bad", "version": "1.0.0"})


def log_lines(captured_logs: StringIO, event: str) -> list[str]:
    """The captured log lines of one event, without colour codes."""
    lines = [re.sub(r"\x1b\[[0-9;]*m", "", line) for line in captured_logs.getvalue().splitlines()]
    return [line for line in lines if line.partition("] ")[2].split(" ", 1)[0] == event]


class TestSyncAtStartUp:
    """Story 19.5 (Epic 19 ADR-10): the state follows the mods directory at start-up."""

    def test_adds_hand_copied_archives_with_their_modinfo(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        temp_state_dir: Path,
    ) -> None:
        """AC 1: keys matched without case; enabled from the name; asset_id 0."""
        create_mod_zip(
            temp_mods_dir / "New.zip", {"modid": "newmod", "name": "New", "version": "1.2.3"}
        )
        create_mod_zip(
            temp_mods_dir / "Off.zip.disabled",
            {"ModID": "offmod", "Name": "Off", "Version": "2.0.0"},
        )
        before = datetime.now(UTC)

        summary = state_manager.sync_state_with_disk()

        after = datetime.now(UTC)
        assert summary == ModSyncSummary(added=2, removed=0, skipped=0)
        new = state_manager.get_mod("New.zip")
        off = state_manager.get_mod("Off.zip.disabled")
        assert new is not None and off is not None
        assert (new.slug, new.version, new.enabled, new.asset_id) == ("newmod", "1.2.3", True, 0)
        assert (off.slug, off.version, off.enabled, off.asset_id) == ("offmod", "2.0.0", False, 0)
        assert before <= new.installed_at <= after
        assert before <= off.installed_at <= after
        saved = json.loads((temp_state_dir / "mods.json").read_text())
        assert sorted(saved) == ["New.zip", "Off.zip.disabled"]
        assert (temp_state_dir / "mods" / "newmod" / "1.2.3" / "modinfo.json").is_file()
        assert (temp_state_dir / "mods" / "offmod" / "2.0.0" / "modinfo.json").is_file()

    def test_removes_an_entry_whose_file_is_gone(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        temp_state_dir: Path,
    ) -> None:
        """AC 2: the entry goes, the state is saved, no file is touched."""
        create_mod_zip(
            temp_mods_dir / "Kept.zip", {"modid": "kept", "name": "Kept", "version": "1.0.0"}
        )
        state_manager.set_mod_state("Kept.zip", mod_state_entry("Kept.zip", "kept"))
        state_manager.set_mod_state("ghost.zip", mod_state_entry("ghost.zip", "ghost"))
        listing = directory_snapshot(temp_mods_dir)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=1, skipped=0)
        assert state_manager.get_mod("ghost.zip") is None
        assert state_manager.get_mod("Kept.zip") == mod_state_entry("Kept.zip", "kept")
        assert sorted(json.loads((temp_state_dir / "mods.json").read_text())) == ["Kept.zip"]
        assert directory_snapshot(temp_mods_dir) == listing

    def test_keeps_an_entry_whose_file_has_another_extension(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        temp_state_dir: Path,
    ) -> None:
        """AC 3: a file present under a non-zip name keeps its entry; nothing is saved."""
        (temp_mods_dir / "odd.cs").write_text("// a code mod")
        entry = mod_state_entry("odd.cs", "oddmod")
        state_manager.set_mod_state("odd.cs", entry)
        state_file = temp_state_dir / "mods.json"
        state_file.unlink(missing_ok=True)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=0, skipped=0)
        assert state_manager.get_mod("odd.cs") == entry
        assert not state_file.exists()

    @pytest.mark.parametrize(
        "kind",
        [
            "not-a-zip",
            "no-modinfo",
            "modinfo-array",
            "modinfo-without-modid",
            "unsupported-compression",
            "encrypted",
            "deeply-nested-json",
            "no-read-permission",
        ],
    )
    def test_skips_an_archive_it_cannot_use(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
        kind: str,
    ) -> None:
        """AC 4: no entry under any name, bytes unchanged, one skip warning."""
        bad = temp_mods_dir / "bad.zip"
        write_bad_archive(bad, kind)
        create_mod_zip(
            temp_mods_dir / "New.zip", {"modid": "newmod", "name": "New", "version": "1.2.3"}
        )
        if kind == "no-read-permission":
            read = state_manager._extract_modinfo_from_zip

            def refuse(path: Path) -> dict[str, object] | None:
                if path.name == "bad.zip":
                    raise PermissionError(13, "Permission denied", str(path))
                return read(path)

            monkeypatch.setattr(state_manager, "_extract_modinfo_from_zip", refuse)
        listing = directory_snapshot(temp_mods_dir)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=1, removed=0, skipped=1)
        assert [m.filename for m in state_manager.list_mods()] == ["New.zip"]
        assert state_manager.get_mod_by_slug("bad") is None
        assert directory_snapshot(temp_mods_dir) == listing
        [line] = log_lines(captured_logs, "mod_state_sync_skipped")
        assert "bad.zip" in line
        assert "unreadable" in line

    def test_skips_an_archive_of_an_installed_mod_id(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        captured_logs: StringIO,
    ) -> None:
        """AC 5: mod IDs compared without case, like the mod lock; one warning names both."""
        create_mod_zip(
            temp_mods_dir / "Foo.zip", {"modid": "foo", "name": "Foo", "version": "1.0.0"}
        )
        create_mod_zip(
            temp_mods_dir / "Foo-copy.zip", {"modid": "FOO", "name": "Foo", "version": "2.0.0"}
        )
        entry = mod_state_entry("Foo.zip", "foo")
        state_manager.set_mod_state("Foo.zip", entry)
        listing = directory_snapshot(temp_mods_dir)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=0, skipped=1)
        assert state_manager.list_mods() == [entry]
        assert directory_snapshot(temp_mods_dir) == listing
        [line] = log_lines(captured_logs, "mod_state_sync_skipped")
        assert "Foo-copy.zip" in line
        assert "Foo.zip" in line.replace("Foo-copy.zip", "")
        assert "duplicate_mod_id" in line

    def test_of_two_new_archives_with_one_mod_id_the_first_by_name_wins_every_time(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """AC 5: the same file wins on every start; a second sync changes nothing."""
        create_mod_zip(
            temp_mods_dir / "b-twin.zip", {"modid": "twin", "name": "Twin", "version": "2.0.0"}
        )
        create_mod_zip(
            temp_mods_dir / "a-twin.zip", {"modid": "Twin", "name": "Twin", "version": "1.0.0"}
        )

        first = state_manager.sync_state_with_disk()
        state_after_first = state_manager.list_mods()
        second = state_manager.sync_state_with_disk()

        assert first == ModSyncSummary(added=1, removed=0, skipped=1)
        assert [m.filename for m in state_after_first] == ["a-twin.zip"]
        assert second == ModSyncSummary(added=0, removed=0, skipped=1)
        assert state_manager.list_mods() == state_after_first

    def test_ignores_working_files_directories_and_other_files(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        temp_state_dir: Path,
    ) -> None:
        """AC 6: nothing added, nothing skipped, the directory unchanged."""
        modinfo: dict[str, object] = {"modid": "amod", "name": "A", "version": "1.0.0"}
        for name in ("a.zip.vsm-tmp", "a.zip.vsm-bak", "b.zip.tmp", "b.zip.bak"):
            create_mod_zip(temp_mods_dir / name, modinfo)
        (temp_mods_dir / "notes.txt").write_text("notes")
        (temp_mods_dir / "dir.zip").mkdir()
        (temp_mods_dir / "plain").mkdir()
        listing = directory_snapshot(temp_mods_dir)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=0, skipped=0)
        assert state_manager.list_mods() == []
        assert directory_snapshot(temp_mods_dir) == listing
        assert not (temp_state_dir / "mods.json").exists()

    @pytest.mark.parametrize("case", ["absent", "unlistable", "a-regular-file"])
    def test_a_missing_or_unlistable_mods_directory_removes_nothing(
        self,
        temp_state_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        case: str,
    ) -> None:
        """AC 8: no entry removed, nothing saved (unlike an empty directory, below)."""
        mods_dir = tmp_path / "Mods"
        if case == "unlistable":
            mods_dir.mkdir()
            listing = Path.iterdir

            def refuse(self: Path) -> Generator[Path]:
                if self == mods_dir:
                    raise PermissionError(13, "Permission denied", str(self))
                yield from listing(self)

            monkeypatch.setattr(Path, "iterdir", refuse)
        elif case == "a-regular-file":
            mods_dir.write_bytes(b"not a directory")
        manager = ModStateManager(state_dir=temp_state_dir, mods_dir=mods_dir)
        entries = [mod_state_entry("One.zip", "one"), mod_state_entry("Two.zip", "two")]
        for entry in entries:
            manager.set_mod_state(entry.filename, entry)
        state_file = temp_state_dir / "mods.json"
        state_file.unlink(missing_ok=True)

        summary = manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=0, skipped=0)
        assert manager.list_mods() == entries
        assert not state_file.exists()

    def test_an_empty_mods_directory_removes_every_entry(
        self, state_manager: ModStateManager, temp_state_dir: Path
    ) -> None:
        """ADR-10: an existing, empty directory means no mod is installed (unlike AC 8)."""
        for entry in (mod_state_entry("One.zip", "one"), mod_state_entry("Two.zip", "two")):
            state_manager.set_mod_state(entry.filename, entry)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=2, skipped=0)
        assert state_manager.list_mods() == []
        assert json.loads((temp_state_dir / "mods.json").read_text()) == {}

    def test_a_mod_renamed_by_hand_to_enabled_is_listed_once_under_its_new_name(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """AC 11: removals come before additions, so the mod does not vanish."""
        state_manager.set_mod_state("Ren.zip.disabled", mod_state_entry("Ren.zip.disabled", "ren"))
        create_mod_zip(
            temp_mods_dir / "Ren.zip", {"modid": "ren", "name": "Ren", "version": "1.0.0"}
        )

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=1, removed=1, skipped=0)
        [mod] = state_manager.list_mods()
        assert (mod.filename, mod.slug, mod.enabled) == ("Ren.zip", "ren", True)

    def test_a_mod_replaced_by_hand_is_listed_once_at_its_new_version(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """AC 11: a file of the same mod ID under another name replaces the entry."""
        state_manager.set_mod_state("Up_1.0.zip", mod_state_entry("Up_1.0.zip", "up"))
        create_mod_zip(
            temp_mods_dir / "Up_1.1.zip", {"modid": "up", "name": "Up", "version": "1.1.0"}
        )

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=1, removed=1, skipped=0)
        [mod] = state_manager.list_mods()
        assert (mod.filename, mod.slug, mod.version) == ("Up_1.1.zip", "up", "1.1.0")

    @pytest.mark.parametrize(
        ("entry_name", "backup_name"),
        [
            ("Foo.zip", "Foo.zip.vsm-bak"),
            ("Foo.zip.disabled", "Foo.zip.disabled.vsm-bak"),
            ("Foo.zip", "foo.zip.vsm-bak"),
        ],
        ids=["same-name", "disabled", "other-case"],
    )
    def test_an_entry_whose_original_is_kept_aside_stays(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        captured_logs: StringIO,
        entry_name: str,
        backup_name: str,
    ) -> None:
        """Review MEDIUM-1: names compared ignoring case, as the 19.4 recovery does."""
        entry = mod_state_entry(entry_name, "foo")
        state_manager.set_mod_state(entry_name, entry)
        create_mod_zip(
            temp_mods_dir / backup_name, {"modid": "Foo", "name": "Foo", "version": "1.0.0"}
        )
        listing = directory_snapshot(temp_mods_dir)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=0, skipped=0)
        assert state_manager.list_mods() == [entry]
        assert directory_snapshot(temp_mods_dir) == listing
        [line] = log_lines(captured_logs, "mod_state_sync_kept_aside")
        assert "warning" in line
        assert f"filename={entry_name} " in f"{line} "
        assert f"backup={backup_name} " in f"{line} "

    def test_another_mods_kept_aside_original_does_not_keep_an_entry(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """One mod's backup never decides another mod's entry."""
        state_manager.set_mod_state("Foo.zip", mod_state_entry("Foo.zip", "foo"))
        create_mod_zip(
            temp_mods_dir / "foo.zip.vsm-bak", {"modid": "bar", "name": "Bar", "version": "1.0.0"}
        )

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=1, skipped=0)
        assert state_manager.list_mods() == []

    def test_an_unreadable_kept_aside_original_keeps_the_entry(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """Its mod is unknown, so the entry is kept: keeping is the safe side."""
        entry = mod_state_entry("Foo.zip", "foo")
        state_manager.set_mod_state("Foo.zip", entry)
        (temp_mods_dir / "Foo.zip.vsm-bak").write_bytes(b"not a zip")

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=0, skipped=0)
        assert state_manager.list_mods() == [entry]

    def test_a_failed_save_keeps_the_changes_in_memory(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC 13: no exception; the summary counts the changes."""
        create_mod_zip(
            temp_mods_dir / "New.zip", {"modid": "newmod", "name": "New", "version": "1.2.3"}
        )
        state_manager.set_mod_state("ghost.zip", mod_state_entry("ghost.zip", "ghost"))

        def fail() -> None:
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(state_manager, "save", fail)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=1, removed=1, skipped=0)
        assert [m.filename for m in state_manager.list_mods()] == ["New.zip"]

    def test_an_entry_is_added_when_its_modinfo_cannot_be_cached(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        create_mod_zip(
            temp_mods_dir / "New.zip", {"modid": "newmod", "name": "New", "version": "1.2.3"}
        )

        def fail(slug: str, version: str, modinfo_data: dict[str, object]) -> None:
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(state_manager, "_cache_modinfo", fail)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=1, removed=0, skipped=0)
        assert state_manager.get_mod("New.zip") is not None

    def test_an_entry_under_a_dangling_symlink_stays(
        self, state_manager: ModStateManager, temp_mods_dir: Path, tmp_path: Path
    ) -> None:
        """The listing rule: a name in the directory keeps its entry, whatever it is."""
        (temp_mods_dir / "Link.zip").symlink_to(tmp_path / "nowhere.zip")
        entry = mod_state_entry("Link.zip", "link")
        state_manager.set_mod_state("Link.zip", entry)

        summary = state_manager.sync_state_with_disk()

        assert summary == ModSyncSummary(added=0, removed=0, skipped=0)
        assert state_manager.list_mods() == [entry]

    def test_a_case_only_rename_by_hand_ends_under_the_name_on_disk(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """Names are compared exactly, so the entry follows the spelling on disk."""
        state_manager.set_mod_state("Foo.zip", mod_state_entry("Foo.zip", "foo"))
        create_mod_zip(
            temp_mods_dir / "foo.zip", {"modid": "foo", "name": "Foo", "version": "1.0.0"}
        )

        state_manager.sync_state_with_disk()

        [mod] = state_manager.list_mods()
        assert (mod.filename, mod.slug) == ("foo.zip", "foo")


class TestSyncLogging:
    """Story 19.5 (Epic 19 ADR-10): every change is logged, and one summary line."""

    @staticmethod
    def assert_one_summary(captured_logs: StringIO, added: int, removed: int, skipped: int) -> None:
        [line] = log_lines(captured_logs, "mod_state_synced")
        assert f"added={added} " in f"{line} "
        assert f"removed={removed} " in f"{line} "
        assert f"skipped={skipped} " in f"{line} "
        for old_event in ("mod_state_added", "mod_state_removed_deleted_file"):
            assert log_lines(captured_logs, old_event) == []

    def test_each_addition_is_logged_with_file_name_and_mod_id(
        self, state_manager: ModStateManager, temp_mods_dir: Path, captured_logs: StringIO
    ) -> None:
        """AC 1 and AC 9."""
        create_mod_zip(
            temp_mods_dir / "New.zip", {"modid": "newmod", "name": "New", "version": "1.2.3"}
        )
        create_mod_zip(
            temp_mods_dir / "Off.zip.disabled",
            {"ModID": "offmod", "Name": "Off", "Version": "2.0.0"},
        )

        state_manager.sync_state_with_disk()

        lines = log_lines(captured_logs, "mod_state_sync_added")
        assert len(lines) == 2
        assert "filename=New.zip" in lines[0] and "slug=newmod" in lines[0]
        assert "filename=Off.zip.disabled" in lines[1] and "slug=offmod" in lines[1]
        assert "info" in lines[0]
        self.assert_one_summary(captured_logs, added=2, removed=0, skipped=0)

    def test_a_removal_is_logged_with_file_name_and_mod_id(
        self, state_manager: ModStateManager, captured_logs: StringIO
    ) -> None:
        """AC 2 and AC 9."""
        state_manager.set_mod_state("ghost.zip", mod_state_entry("ghost.zip", "ghost"))

        state_manager.sync_state_with_disk()

        [line] = log_lines(captured_logs, "mod_state_sync_removed")
        assert "info" in line
        assert "filename=ghost.zip" in line and "slug=ghost" in line
        self.assert_one_summary(captured_logs, added=0, removed=1, skipped=0)

    def test_a_skipped_archive_is_one_warning_and_counted(
        self, state_manager: ModStateManager, temp_mods_dir: Path, captured_logs: StringIO
    ) -> None:
        """AC 4 and AC 9: an exception's text is logged with the skip."""
        write_bad_archive(temp_mods_dir / "bad.zip", "encrypted")

        state_manager.sync_state_with_disk()

        [line] = log_lines(captured_logs, "mod_state_sync_skipped")
        assert "warning" in line
        assert "filename=bad.zip" in line and "reason=unreadable" in line
        assert "error=" in line
        self.assert_one_summary(captured_logs, added=0, removed=0, skipped=1)

    def test_a_duplicate_is_one_warning_naming_both_files(
        self, state_manager: ModStateManager, temp_mods_dir: Path, captured_logs: StringIO
    ) -> None:
        """AC 5 and AC 9."""
        create_mod_zip(
            temp_mods_dir / "Foo.zip", {"modid": "foo", "name": "Foo", "version": "1.0.0"}
        )
        create_mod_zip(
            temp_mods_dir / "Foo-copy.zip", {"modid": "FOO", "name": "Foo", "version": "2.0.0"}
        )
        state_manager.set_mod_state("Foo.zip", mod_state_entry("Foo.zip", "foo"))

        state_manager.sync_state_with_disk()

        [line] = log_lines(captured_logs, "mod_state_sync_skipped")
        assert "filename=Foo-copy.zip" in line and "existing=Foo.zip" in line
        assert "reason=duplicate_mod_id" in line
        self.assert_one_summary(captured_logs, added=0, removed=0, skipped=1)

    def test_nothing_to_do_still_logs_the_summary(
        self, state_manager: ModStateManager, captured_logs: StringIO
    ) -> None:
        """AC 9: also when all numbers are zero."""
        state_manager.sync_state_with_disk()

        self.assert_one_summary(captured_logs, added=0, removed=0, skipped=0)

    def test_a_missing_mods_directory_is_a_warning_and_a_zero_summary(
        self, temp_state_dir: Path, tmp_path: Path, captured_logs: StringIO
    ) -> None:
        """AC 8 and AC 9."""
        manager = ModStateManager(state_dir=temp_state_dir, mods_dir=tmp_path / "Mods")
        manager.set_mod_state("One.zip", mod_state_entry("One.zip", "one"))

        manager.sync_state_with_disk()

        [line] = log_lines(captured_logs, "mod_state_sync_mods_directory_not_found")
        assert "warning" in line
        assert "Mods" in line
        self.assert_one_summary(captured_logs, added=0, removed=0, skipped=0)

    def test_an_unlistable_mods_directory_is_a_warning_and_a_zero_summary(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        """AC 8 and AC 9."""
        state_manager.set_mod_state("One.zip", mod_state_entry("One.zip", "one"))
        listing = Path.iterdir

        def refuse(self: Path) -> Generator[Path]:
            if self == temp_mods_dir:
                raise PermissionError(13, "Permission denied", str(self))
            yield from listing(self)

        monkeypatch.setattr(Path, "iterdir", refuse)

        state_manager.sync_state_with_disk()

        [line] = log_lines(captured_logs, "mod_state_sync_mods_directory_unreadable")
        assert "warning" in line
        assert "Permission denied" in line
        assert log_lines(captured_logs, "mod_state_sync_removed") == []
        self.assert_one_summary(captured_logs, added=0, removed=0, skipped=0)

    def test_removing_every_entry_is_one_extra_warning(
        self, state_manager: ModStateManager, temp_mods_dir: Path, captured_logs: StringIO
    ) -> None:
        """Review LOW-2: an empty directory still removes everything (ADR-10), visibly."""
        for entry in (mod_state_entry("One.zip", "one"), mod_state_entry("Two.zip", "two")):
            state_manager.set_mod_state(entry.filename, entry)

        state_manager.sync_state_with_disk()

        [line] = log_lines(captured_logs, "mod_state_sync_removed_all")
        assert "warning" in line
        assert "removed=2" in line
        assert str(temp_mods_dir) in line
        assert state_manager.list_mods() == []

    @pytest.mark.parametrize("entries", [0, 1], ids=["no-entries", "one-of-two-kept"])
    def test_no_removed_all_warning_otherwise(
        self,
        state_manager: ModStateManager,
        temp_mods_dir: Path,
        captured_logs: StringIO,
        entries: int,
    ) -> None:
        if entries:
            create_mod_zip(
                temp_mods_dir / "One.zip", {"modid": "one", "name": "One", "version": "1.0.0"}
            )
            for entry in (mod_state_entry("One.zip", "one"), mod_state_entry("Two.zip", "two")):
                state_manager.set_mod_state(entry.filename, entry)

        state_manager.sync_state_with_disk()

        assert log_lines(captured_logs, "mod_state_sync_removed_all") == []

    def test_a_failed_save_is_an_error(
        self,
        state_manager: ModStateManager,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        """AC 13 and AC 9."""
        state_manager.set_mod_state("ghost.zip", mod_state_entry("ghost.zip", "ghost"))

        def fail() -> None:
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(state_manager, "save", fail)

        state_manager.sync_state_with_disk()

        [line] = log_lines(captured_logs, "mod_state_sync_save_failed")
        assert "error" in line
        assert "No space left on device" in line
        self.assert_one_summary(captured_logs, added=0, removed=1, skipped=0)


# --- Task 5: pending restart tracking tests ---


class TestPendingRestartState:
    """Tests for PendingRestartState tracking."""

    def test_initial_state_no_restart_pending(self) -> None:
        """PendingRestartState starts with no restart pending."""
        state = PendingRestartState()
        assert state.pending_restart is False
        assert state.pending_changes == []

    def test_require_restart_sets_flag(self) -> None:
        """require_restart() sets pending_restart to True."""
        state = PendingRestartState()
        state.require_restart("Mod 'testmod' was enabled")

        assert state.pending_restart is True

    def test_require_restart_adds_reason(self) -> None:
        """require_restart() adds reason to pending_changes list."""
        state = PendingRestartState()
        state.require_restart("Mod 'mod1' was enabled")
        state.require_restart("Mod 'mod2' was disabled")

        assert len(state.pending_changes) == 2
        assert "Mod 'mod1' was enabled" in state.pending_changes
        assert "Mod 'mod2' was disabled" in state.pending_changes

    def test_clear_restart_resets_state(self) -> None:
        """clear_restart() resets pending_restart and pending_changes."""
        state = PendingRestartState()
        state.require_restart("Test reason")
        assert state.pending_restart is True

        state.clear_restart()

        assert state.pending_restart is False
        assert state.pending_changes == []

    def test_multiple_require_restart_calls(self) -> None:
        """Multiple require_restart() calls accumulate reasons."""
        state = PendingRestartState()
        state.require_restart("First change")
        state.require_restart("Second change")
        state.require_restart("Third change")

        assert state.pending_restart is True
        assert len(state.pending_changes) == 3


class TestRepairFallbackEntries:
    """Entries imported with filename fallback metadata are re-read at startup (VSS-tpe
    follow-up: Better Ruins declared side "Universal", which older builds rejected)."""

    MODINFO: dict[str, object] = {
        "modid": "betterruins",
        "name": "BetterRuins",
        "version": "0.6.4",
        "side": "Universal",
    }

    def fallback_entry(
        self, manager: ModStateManager, filename: str, *, enabled: bool = True
    ) -> ModState:
        entry = ModState(
            filename=filename,
            slug=filename.removesuffix(".disabled").removesuffix(".zip"),
            version="unknown",
            enabled=enabled,
            installed_at=datetime(2026, 1, 2, tzinfo=UTC),
            asset_id=4242,
        )
        manager.set_mod_state(filename, entry)
        manager.save()
        return entry

    def test_repairs_slug_and_version_and_keeps_the_rest(
        self, state_manager: ModStateManager, temp_mods_dir: Path, temp_state_dir: Path
    ) -> None:
        create_mod_zip(temp_mods_dir / "BetterRuinsv0.6.4.zip.disabled", self.MODINFO)
        self.fallback_entry(state_manager, "BetterRuinsv0.6.4.zip.disabled", enabled=False)

        repaired = state_manager.repair_fallback_entries()

        assert repaired == ["BetterRuinsv0.6.4.zip.disabled"]
        reloaded = ModStateManager(state_dir=temp_state_dir, mods_dir=temp_mods_dir)
        reloaded.load()
        entry = reloaded.get_mod("BetterRuinsv0.6.4.zip.disabled")
        assert entry is not None
        assert (entry.slug, entry.version) == ("betterruins", "0.6.4")
        assert (entry.enabled, entry.asset_id) == (False, 4242)
        assert entry.installed_at == datetime(2026, 1, 2, tzinfo=UTC)
        assert reloaded.get_cached_metadata("betterruins", "0.6.4") is not None

    def test_repairs_an_archive_with_capitalized_keys(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        """A mod an older build imported as filename / "unknown" because its modinfo.json
        uses "ModID" and "Version" is repaired at the next start (VSS-0jl)."""
        create_mod_zip(
            temp_mods_dir / "BetterRuinsv0.6.4.zip",
            {"ModID": "betterruins", "Name": "BetterRuins", "Version": "0.6.4"},
        )
        self.fallback_entry(state_manager, "BetterRuinsv0.6.4.zip")

        assert state_manager.repair_fallback_entries() == ["BetterRuinsv0.6.4.zip"]
        entry = state_manager.get_mod("BetterRuinsv0.6.4.zip")
        assert entry is not None
        assert (entry.slug, entry.version) == ("betterruins", "0.6.4")
        assert state_manager.get_cached_metadata("betterruins", "0.6.4") is not None

    def test_still_unreadable_archive_is_left_alone(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        (temp_mods_dir / "broken.zip").write_bytes(b"not a zip")
        entry = self.fallback_entry(state_manager, "broken.zip")

        assert state_manager.repair_fallback_entries() == []
        assert state_manager.get_mod("broken.zip") == entry

    def test_missing_file_is_left_alone(self, state_manager: ModStateManager) -> None:
        entry = self.fallback_entry(state_manager, "gone.zip")

        assert state_manager.repair_fallback_entries() == []
        assert state_manager.get_mod("gone.zip") == entry

    def test_repair_that_would_duplicate_an_installed_mod_is_skipped(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        create_mod_zip(
            temp_mods_dir / "betterruins_0.6.3.zip", {**self.MODINFO, "version": "0.6.3"}
        )
        state_manager.set_mod_state(
            "betterruins_0.6.3.zip",
            ModState(
                filename="betterruins_0.6.3.zip",
                slug="betterruins",
                version="0.6.3",
                installed_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        )
        create_mod_zip(temp_mods_dir / "BetterRuinsv0.6.4.zip", self.MODINFO)
        entry = self.fallback_entry(state_manager, "BetterRuinsv0.6.4.zip")

        assert state_manager.repair_fallback_entries() == []
        assert state_manager.get_mod("BetterRuinsv0.6.4.zip") == entry

    def test_entries_with_real_versions_are_not_reread(
        self, state_manager: ModStateManager, temp_mods_dir: Path
    ) -> None:
        create_mod_zip(temp_mods_dir / "betterruins.zip", self.MODINFO)
        entry = ModState(
            filename="betterruins.zip",
            slug="something-else",
            version="0.6.0",
            installed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        state_manager.set_mod_state("betterruins.zip", entry)

        assert state_manager.repair_fallback_entries() == []
        assert state_manager.get_mod("betterruins.zip") == entry
