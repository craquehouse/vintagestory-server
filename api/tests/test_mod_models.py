"""Unit tests for mod models."""

from datetime import UTC, datetime

from vintagestory_api.models.mods import ModInfo, ModMetadata, ModState


class TestModMetadata:
    """Tests for ModMetadata model (extracted from modinfo.json)."""

    def test_create_with_required_fields(self) -> None:
        """ModMetadata can be created with only required fields."""
        metadata = ModMetadata(
            modid="smithingplus",
            name="Smithing Plus",
            version="1.8.3",
        )
        assert metadata.modid == "smithingplus"
        assert metadata.name == "Smithing Plus"
        assert metadata.version == "1.8.3"
        assert metadata.authors == []
        assert metadata.description is None

    def test_create_with_all_fields(self) -> None:
        """ModMetadata can be created with all fields populated."""
        metadata = ModMetadata(
            modid="smithingplus",
            name="Smithing Plus",
            version="1.8.3",
            authors=["Tyron", "radfast"],
            description="Expanded smithing mechanics",
        )
        assert metadata.authors == ["Tyron", "radfast"]
        assert metadata.description == "Expanded smithing mechanics"

    def test_serialization_roundtrip(self) -> None:
        """ModMetadata serializes to JSON and deserializes correctly."""
        original = ModMetadata(
            modid="testmod",
            name="Test Mod",
            version="2.0.0",
            authors=["author1"],
            description="A test mod",
        )
        json_str = original.model_dump_json()
        restored = ModMetadata.model_validate_json(json_str)

        assert restored.modid == original.modid
        assert restored.name == original.name
        assert restored.version == original.version
        assert restored.authors == original.authors
        assert restored.description == original.description

    def test_from_modinfo_json(self) -> None:
        """ModMetadata can be parsed from typical modinfo.json content."""
        modinfo_data = {
            "modid": "smithingplus",
            "name": "Smithing Plus",
            "version": "1.8.3",
            "authors": ["Tyron", "radfast"],
            "description": "Expanded smithing mechanics",
            "type": "code",  # Extra field should be ignored
            "dependencies": {"game": "1.21.0"},  # Extra field should be ignored
        }
        metadata = ModMetadata.model_validate(modinfo_data)

        assert metadata.modid == "smithingplus"
        assert metadata.name == "Smithing Plus"
        assert metadata.version == "1.8.3"
        assert metadata.authors == ["Tyron", "radfast"]
        assert metadata.description == "Expanded smithing mechanics"


class TestModState:
    """Tests for ModState model (state index entry)."""

    def test_create_with_required_fields(self) -> None:
        """ModState can be created with required fields and defaults."""
        now = datetime.now(UTC)
        state = ModState(
            filename="smithingplus_1.8.3.zip",
            slug="smithingplus",
            version="1.8.3",
            installed_at=now,
        )
        assert state.filename == "smithingplus_1.8.3.zip"
        assert state.slug == "smithingplus"
        assert state.version == "1.8.3"
        assert state.enabled is True  # Default
        assert state.installed_at == now

    def test_disabled_state(self) -> None:
        """ModState tracks enabled/disabled status."""
        state = ModState(
            filename="testmod.zip.disabled",
            slug="testmod",
            version="1.0.0",
            enabled=False,
            installed_at=datetime.now(UTC),
        )
        assert state.enabled is False

    def test_serialization_roundtrip(self) -> None:
        """ModState serializes to JSON and deserializes correctly."""
        now = datetime(2025, 12, 29, 10, 30, 0, tzinfo=UTC)
        original = ModState(
            filename="testmod_2.0.0.zip",
            slug="testmod",
            version="2.0.0",
            enabled=True,
            installed_at=now,
        )
        json_str = original.model_dump_json()
        restored = ModState.model_validate_json(json_str)

        assert restored.filename == original.filename
        assert restored.slug == original.slug
        assert restored.version == original.version
        assert restored.enabled == original.enabled
        assert restored.installed_at == original.installed_at

    def test_state_index_format(self) -> None:
        """ModState serializes to match expected state index format."""
        now = datetime(2025, 12, 29, 10, 30, 0, tzinfo=UTC)
        state = ModState(
            filename="smithingplus_1.8.3.zip",
            slug="smithingplus",
            version="1.8.3",
            enabled=True,
            installed_at=now,
        )
        # Use mode="json" to serialize datetime as ISO string
        data = state.model_dump(mode="json")

        assert data == {
            "filename": "smithingplus_1.8.3.zip",
            "slug": "smithingplus",
            "version": "1.8.3",
            "enabled": True,
            "installed_at": "2025-12-29T10:30:00Z",
        }


class TestModInfo:
    """Tests for ModInfo model (combined local + remote information)."""

    def test_create_with_local_only(self) -> None:
        """ModInfo can be created with only local information."""
        now = datetime.now(UTC)
        info = ModInfo(
            filename="testmod_1.0.0.zip",
            slug="testmod",
            version="1.0.0",
            enabled=True,
            installed_at=now,
            name="Test Mod",
        )
        assert info.filename == "testmod_1.0.0.zip"
        assert info.slug == "testmod"
        assert info.version == "1.0.0"
        assert info.enabled is True
        assert info.name == "Test Mod"
        assert info.authors == []
        assert info.description is None

    def test_create_with_metadata(self) -> None:
        """ModInfo can include full metadata from modinfo.json."""
        now = datetime.now(UTC)
        info = ModInfo(
            filename="smithingplus_1.8.3.zip",
            slug="smithingplus",
            version="1.8.3",
            enabled=True,
            installed_at=now,
            name="Smithing Plus",
            authors=["Tyron", "radfast"],
            description="Expanded smithing mechanics",
        )
        assert info.name == "Smithing Plus"
        assert info.authors == ["Tyron", "radfast"]
        assert info.description == "Expanded smithing mechanics"

    def test_serialization_for_api_response(self) -> None:
        """ModInfo serializes correctly for API responses."""
        now = datetime(2025, 12, 29, 10, 30, 0, tzinfo=UTC)
        info = ModInfo(
            filename="testmod_1.0.0.zip",
            slug="testmod",
            version="1.0.0",
            enabled=True,
            installed_at=now,
            name="Test Mod",
            authors=["author1"],
            description="A test mod",
        )
        data = info.model_dump(mode="json")

        assert data["slug"] == "testmod"
        assert data["name"] == "Test Mod"
        assert data["version"] == "1.0.0"
        assert data["enabled"] is True
        assert data["authors"] == ["author1"]
        assert data["description"] == "A test mod"
        assert data["installed_at"] == "2025-12-29T10:30:00Z"
