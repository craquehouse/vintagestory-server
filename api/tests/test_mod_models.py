"""Unit tests for mod models."""

from datetime import UTC, datetime

from vintagestory_api.models.mods import (
    CompatibilityInfo,
    ModInfo,
    ModLookupResponse,
    ModMetadata,
    ModState,
)


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


class TestCompatibilityInfo:
    """Tests for CompatibilityInfo model (compatibility status)."""

    def test_create_compatible_status(self) -> None:
        """CompatibilityInfo can be created with compatible status."""
        info = CompatibilityInfo(
            status="compatible",
            game_version="1.21.3",
            mod_version="1.8.3",
            message=None,
        )
        assert info.status == "compatible"
        assert info.game_version == "1.21.3"
        assert info.mod_version == "1.8.3"
        assert info.message is None

    def test_create_not_verified_status(self) -> None:
        """CompatibilityInfo can be created with not_verified status."""
        info = CompatibilityInfo(
            status="not_verified",
            game_version="1.21.3",
            mod_version="1.8.3",
            message="Mod not explicitly verified for version 1.21.3. May still work.",
        )
        assert info.status == "not_verified"
        assert info.message is not None
        assert "1.21.3" in info.message

    def test_create_incompatible_status(self) -> None:
        """CompatibilityInfo can be created with incompatible status."""
        info = CompatibilityInfo(
            status="incompatible",
            game_version="1.21.3",
            mod_version="1.7.0",
            message="Mod version 1.7.0 is only compatible with 1.20.x. "
            "Installation may cause issues.",
        )
        assert info.status == "incompatible"
        assert info.message is not None
        assert "1.20.x" in info.message

    def test_serialization_roundtrip(self) -> None:
        """CompatibilityInfo serializes to JSON and deserializes correctly."""
        original = CompatibilityInfo(
            status="not_verified",
            game_version="1.21.3",
            mod_version="1.8.3",
            message="Mod not explicitly verified for version 1.21.3.",
        )
        json_str = original.model_dump_json()
        restored = CompatibilityInfo.model_validate_json(json_str)

        assert restored.status == original.status
        assert restored.game_version == original.game_version
        assert restored.mod_version == original.mod_version
        assert restored.message == original.message

    def test_serialization_for_api_response(self) -> None:
        """CompatibilityInfo serializes correctly for API responses."""
        info = CompatibilityInfo(
            status="compatible",
            game_version="1.21.3",
            mod_version="1.8.3",
        )
        data = info.model_dump(mode="json")

        assert data == {
            "status": "compatible",
            "game_version": "1.21.3",
            "mod_version": "1.8.3",
            "message": None,
        }


class TestModLookupResponse:
    """Tests for ModLookupResponse model (lookup endpoint response)."""

    def test_create_with_required_fields(self) -> None:
        """ModLookupResponse can be created with all required fields."""
        compat = CompatibilityInfo(
            status="compatible",
            game_version="1.21.3",
            mod_version="1.8.3",
        )
        response = ModLookupResponse(
            slug="smithingplus",
            name="Smithing Plus",
            author="jayu",
            latest_version="1.8.3",
            downloads=49726,
            side="Both",
            compatibility=compat,
        )
        assert response.slug == "smithingplus"
        assert response.name == "Smithing Plus"
        assert response.author == "jayu"
        assert response.description is None
        assert response.latest_version == "1.8.3"
        assert response.downloads == 49726
        assert response.side == "Both"
        assert response.compatibility.status == "compatible"

    def test_create_with_all_fields(self) -> None:
        """ModLookupResponse can be created with all fields populated."""
        compat = CompatibilityInfo(
            status="not_verified",
            game_version="1.21.3",
            mod_version="1.8.2",
            message="Mod not explicitly verified for version 1.21.3.",
        )
        response = ModLookupResponse(
            slug="smithingplus",
            name="Smithing Plus",
            author="jayu",
            description="Expanded smithing mechanics for VintageStory",
            latest_version="1.8.2",
            downloads=49726,
            side="Both",
            compatibility=compat,
        )
        assert response.description == "Expanded smithing mechanics for VintageStory"
        assert response.compatibility.status == "not_verified"
        assert response.compatibility.message is not None

    def test_serialization_roundtrip(self) -> None:
        """ModLookupResponse serializes to JSON and deserializes correctly."""
        compat = CompatibilityInfo(
            status="compatible",
            game_version="1.21.3",
            mod_version="1.8.3",
        )
        original = ModLookupResponse(
            slug="testmod",
            name="Test Mod",
            author="TestAuthor",
            description="A test mod",
            latest_version="2.0.0",
            downloads=12345,
            side="Server",
            compatibility=compat,
        )
        json_str = original.model_dump_json()
        restored = ModLookupResponse.model_validate_json(json_str)

        assert restored.slug == original.slug
        assert restored.name == original.name
        assert restored.author == original.author
        assert restored.description == original.description
        assert restored.latest_version == original.latest_version
        assert restored.downloads == original.downloads
        assert restored.side == original.side
        assert restored.compatibility.status == original.compatibility.status

    def test_serialization_for_api_response(self) -> None:
        """ModLookupResponse serializes correctly for API responses."""
        compat = CompatibilityInfo(
            status="compatible",
            game_version="1.21.3",
            mod_version="1.8.3",
        )
        response = ModLookupResponse(
            slug="smithingplus",
            name="Smithing Plus",
            author="jayu",
            description="Expanded smithing",
            latest_version="1.8.3",
            downloads=49726,
            side="Both",
            compatibility=compat,
        )
        data = response.model_dump(mode="json")

        assert data == {
            "slug": "smithingplus",
            "name": "Smithing Plus",
            "author": "jayu",
            "description": "Expanded smithing",
            "latest_version": "1.8.3",
            "downloads": 49726,
            "side": "Both",
            "compatibility": {
                "status": "compatible",
                "game_version": "1.21.3",
                "mod_version": "1.8.3",
                "message": None,
            },
        }

    def test_nested_compatibility_info(self) -> None:
        """ModLookupResponse properly nests CompatibilityInfo."""
        compat = CompatibilityInfo(
            status="incompatible",
            game_version="1.21.3",
            mod_version="1.5.0",
            message="Mod version 1.5.0 is only compatible with 1.19.x",
        )
        response = ModLookupResponse(
            slug="oldmod",
            name="Old Mod",
            author="someone",
            latest_version="1.5.0",
            downloads=1000,
            side="Client",
            compatibility=compat,
        )

        # Verify nested serialization
        data = response.model_dump(mode="json")
        assert data["compatibility"]["status"] == "incompatible"
        assert (
            data["compatibility"]["message"]
            == "Mod version 1.5.0 is only compatible with 1.19.x"
        )
