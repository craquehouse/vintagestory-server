"""Unit tests for ModStateManager service."""

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from vintagestory_api.models.mods import ModState
from vintagestory_api.services.mod_state import ModStateManager
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

    def test_creates_with_directories(
        self, temp_state_dir: Path, temp_mods_dir: Path
    ) -> None:
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

    def test_load_creates_empty_state_if_no_file(
        self, state_manager: ModStateManager
    ) -> None:
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

    def test_get_mod_returns_none_if_not_found(
        self, state_manager: ModStateManager
    ) -> None:
        """get_mod() returns None for unknown filename."""
        assert state_manager.get_mod("nonexistent.zip") is None

    def test_get_mod_returns_state_by_filename(
        self, state_manager: ModStateManager
    ) -> None:
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

    def test_set_mod_state_updates_existing_mod(
        self, state_manager: ModStateManager
    ) -> None:
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

    def test_remove_mod_deletes_from_state(
        self, state_manager: ModStateManager
    ) -> None:
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

    def test_remove_mod_ignores_nonexistent(
        self, state_manager: ModStateManager
    ) -> None:
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
        modinfo_content = json.dumps({
            "modid": "evilmod",
            "name": "Evil Mod",
            "version": "1.0.0",
        })

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
        modinfo_content = json.dumps({
            "modid": "sneakymod",
            "name": "Sneaky Mod",
            "version": "2.0.0",
        })

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
        modinfo_content = json.dumps({
            "modid": "absmod",
            "name": "Absolute Mod",
            "version": "3.0.0",
        })

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
        modinfo_content = json.dumps({
            "modid": "safemod",
            "name": "Safe Mod",
            "version": "1.0.0",
        })

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
        modinfo_content = json.dumps({
            "modid": "dotmod",
            "name": "Dot Mod",
            "version": "1.2.3",
        })

        # Create zip with dots in directory name (safe - not traversal)
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("mod.v1.2.3/modinfo.json", modinfo_content)

        metadata = state_manager.import_mod(zip_path)

        # Should extract normally
        assert metadata.modid == "dotmod"
        assert metadata.version == "1.2.3"


class TestGetCachedMetadata:
    """Tests for get_cached_metadata() function."""

    def test_get_cached_metadata_returns_none_if_not_cached(
        self, state_manager: ModStateManager
    ) -> None:
        """get_cached_metadata() returns None if no cache exists."""
        result = state_manager.get_cached_metadata("nonexistent", "1.0.0")
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
