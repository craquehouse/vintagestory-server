"""Unit tests for mod models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from vintagestory_api.models.mods import (
    CompatibilityInfo,
    ModBrowseItem,
    ModBrowseResponse,
    ModInfo,
    ModLookupResponse,
    ModMetadata,
    ModState,
    PaginationMeta,
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
            "logo_url": None,
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


class TestModBrowseItem:
    """Tests for ModBrowseItem model (mod in browse list)."""

    def test_create_with_required_fields(self) -> None:
        """ModBrowseItem can be created with required fields and defaults."""
        item = ModBrowseItem(
            slug="smithingplus",
            name="Smithing Plus",
            author="jayu",
            downloads=204656,
            follows=2348,
            trending_points=1853,
            side="both",
            mod_type="mod",
        )
        assert item.slug == "smithingplus"
        assert item.name == "Smithing Plus"
        assert item.author == "jayu"
        assert item.downloads == 204656
        assert item.follows == 2348
        assert item.trending_points == 1853
        assert item.side == "both"
        assert item.mod_type == "mod"
        assert item.summary is None
        assert item.logo_url is None
        assert item.tags == []
        assert item.last_released is None

    def test_create_with_all_fields(self) -> None:
        """ModBrowseItem can be created with all fields populated."""
        item = ModBrowseItem(
            slug="smithingplus",
            name="Smithing Plus",
            author="jayu",
            summary="Expanded smithing mechanics",
            downloads=204656,
            follows=2348,
            trending_points=1853,
            side="both",
            mod_type="mod",
            logo_url="https://moddbcdn.vintagestory.at/logo.png",
            tags=["Crafting", "QoL"],
            last_released="2025-10-09 21:28:57",
        )
        assert item.summary == "Expanded smithing mechanics"
        assert item.logo_url == "https://moddbcdn.vintagestory.at/logo.png"
        assert item.tags == ["Crafting", "QoL"]
        assert item.last_released == "2025-10-09 21:28:57"

    def test_side_literal_values(self) -> None:
        """ModBrowseItem validates side literal values."""
        # Valid values
        for side in ["client", "server", "both"]:
            item = ModBrowseItem(
                slug="test",
                name="Test",
                author="Test",
                downloads=0,
                follows=0,
                trending_points=0,
                side=side,  # type: ignore[arg-type]
                mod_type="mod",
            )
            assert item.side == side

    def test_side_invalid_value_raises(self) -> None:
        """ModBrowseItem raises on invalid side value."""
        with pytest.raises(ValidationError):
            ModBrowseItem(
                slug="test",
                name="Test",
                author="Test",
                downloads=0,
                follows=0,
                trending_points=0,
                side="invalid",  # type: ignore[arg-type]
                mod_type="mod",
            )

    def test_mod_type_literal_values(self) -> None:
        """ModBrowseItem validates mod_type literal values."""
        # Valid values
        for mod_type in ["mod", "externaltool", "other"]:
            item = ModBrowseItem(
                slug="test",
                name="Test",
                author="Test",
                downloads=0,
                follows=0,
                trending_points=0,
                side="both",
                mod_type=mod_type,  # type: ignore[arg-type]
            )
            assert item.mod_type == mod_type

    def test_from_api_response_data(self) -> None:
        """ModBrowseItem can be parsed from typical VintageStory API data."""
        # Simulates transforming API data to our model format
        # (The actual transformation happens in ModApiClient)
        item = ModBrowseItem(
            slug="smithingplus",  # from urlalias
            name="Smithing Plus",
            author="jayu",
            summary="Expanded smithing",
            downloads=204656,
            follows=2348,
            trending_points=1853,  # from trendingpoints
            side="both",
            mod_type="mod",  # from type
            logo_url="https://moddbcdn.vintagestory.at/logo.png",  # from logo
            tags=["Crafting", "QoL"],
            last_released="2025-10-09 21:28:57",  # from lastreleased
        )

        assert item.slug == "smithingplus"
        assert item.name == "Smithing Plus"
        assert item.trending_points == 1853
        assert item.mod_type == "mod"

    def test_serialization_roundtrip(self) -> None:
        """ModBrowseItem serializes to JSON and deserializes correctly."""
        original = ModBrowseItem(
            slug="testmod",
            name="Test Mod",
            author="TestAuthor",
            summary="A test mod",
            downloads=12345,
            follows=100,
            trending_points=50,
            side="server",
            mod_type="mod",
            logo_url="https://example.com/logo.png",
            tags=["Category1", "Category2"],
            last_released="2025-12-29 10:30:00",
        )
        json_str = original.model_dump_json()
        restored = ModBrowseItem.model_validate_json(json_str)

        assert restored.slug == original.slug
        assert restored.name == original.name
        assert restored.author == original.author
        assert restored.summary == original.summary
        assert restored.downloads == original.downloads
        assert restored.follows == original.follows
        assert restored.trending_points == original.trending_points
        assert restored.side == original.side
        assert restored.mod_type == original.mod_type
        assert restored.logo_url == original.logo_url
        assert restored.tags == original.tags
        assert restored.last_released == original.last_released

    def test_serialization_for_api_response(self) -> None:
        """ModBrowseItem serializes correctly for API responses."""
        item = ModBrowseItem(
            slug="smithingplus",
            name="Smithing Plus",
            author="jayu",
            summary="Expanded smithing",
            downloads=204656,
            follows=2348,
            trending_points=1853,
            side="both",
            mod_type="mod",
            logo_url="https://moddbcdn.vintagestory.at/logo.png",
            tags=["Crafting", "QoL"],
            last_released="2025-10-09 21:28:57",
        )
        data = item.model_dump(mode="json")

        assert data == {
            "slug": "smithingplus",
            "name": "Smithing Plus",
            "author": "jayu",
            "summary": "Expanded smithing",
            "downloads": 204656,
            "follows": 2348,
            "trending_points": 1853,
            "side": "both",
            "mod_type": "mod",
            "logo_url": "https://moddbcdn.vintagestory.at/logo.png",
            "tags": ["Crafting", "QoL"],
            "last_released": "2025-10-09 21:28:57",
        }


class TestPaginationMeta:
    """Tests for PaginationMeta model (pagination metadata)."""

    def test_create_first_page(self) -> None:
        """PaginationMeta for first page of multi-page results."""
        meta = PaginationMeta(
            page=1,
            page_size=20,
            total_items=550,
            total_pages=28,
            has_next=True,
            has_prev=False,
        )
        assert meta.page == 1
        assert meta.page_size == 20
        assert meta.total_items == 550
        assert meta.total_pages == 28
        assert meta.has_next is True
        assert meta.has_prev is False

    def test_create_middle_page(self) -> None:
        """PaginationMeta for middle page with both prev and next."""
        meta = PaginationMeta(
            page=5,
            page_size=20,
            total_items=550,
            total_pages=28,
            has_next=True,
            has_prev=True,
        )
        assert meta.page == 5
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_create_last_page(self) -> None:
        """PaginationMeta for last page of results."""
        meta = PaginationMeta(
            page=28,
            page_size=20,
            total_items=550,
            total_pages=28,
            has_next=False,
            has_prev=True,
        )
        assert meta.page == 28
        assert meta.has_next is False
        assert meta.has_prev is True

    def test_create_single_page(self) -> None:
        """PaginationMeta for results that fit on one page."""
        meta = PaginationMeta(
            page=1,
            page_size=20,
            total_items=10,
            total_pages=1,
            has_next=False,
            has_prev=False,
        )
        assert meta.total_pages == 1
        assert meta.has_next is False
        assert meta.has_prev is False

    def test_create_empty_results(self) -> None:
        """PaginationMeta for empty results."""
        meta = PaginationMeta(
            page=1,
            page_size=20,
            total_items=0,
            total_pages=0,
            has_next=False,
            has_prev=False,
        )
        assert meta.total_items == 0
        assert meta.total_pages == 0

    def test_serialization_roundtrip(self) -> None:
        """PaginationMeta serializes to JSON and deserializes correctly."""
        original = PaginationMeta(
            page=3,
            page_size=20,
            total_items=550,
            total_pages=28,
            has_next=True,
            has_prev=True,
        )
        json_str = original.model_dump_json()
        restored = PaginationMeta.model_validate_json(json_str)

        assert restored.page == original.page
        assert restored.page_size == original.page_size
        assert restored.total_items == original.total_items
        assert restored.total_pages == original.total_pages
        assert restored.has_next == original.has_next
        assert restored.has_prev == original.has_prev

    def test_serialization_for_api_response(self) -> None:
        """PaginationMeta serializes correctly for API responses."""
        meta = PaginationMeta(
            page=1,
            page_size=20,
            total_items=550,
            total_pages=28,
            has_next=True,
            has_prev=False,
        )
        data = meta.model_dump(mode="json")

        assert data == {
            "page": 1,
            "page_size": 20,
            "total_items": 550,
            "total_pages": 28,
            "has_next": True,
            "has_prev": False,
        }


class TestModBrowseResponse:
    """Tests for ModBrowseResponse model (browse endpoint response)."""

    def test_create_with_mods(self) -> None:
        """ModBrowseResponse can be created with mod list and pagination."""
        mods = [
            ModBrowseItem(
                slug="mod1",
                name="Mod 1",
                author="Author1",
                downloads=1000,
                follows=100,
                trending_points=50,
                side="both",
                mod_type="mod",
            ),
            ModBrowseItem(
                slug="mod2",
                name="Mod 2",
                author="Author2",
                downloads=2000,
                follows=200,
                trending_points=100,
                side="server",
                mod_type="mod",
            ),
        ]
        pagination = PaginationMeta(
            page=1,
            page_size=20,
            total_items=550,
            total_pages=28,
            has_next=True,
            has_prev=False,
        )
        response = ModBrowseResponse(mods=mods, pagination=pagination)

        assert len(response.mods) == 2
        assert response.mods[0].slug == "mod1"
        assert response.mods[1].slug == "mod2"
        assert response.pagination.page == 1
        assert response.pagination.total_items == 550

    def test_create_empty_results(self) -> None:
        """ModBrowseResponse can be created with empty results."""
        pagination = PaginationMeta(
            page=1,
            page_size=20,
            total_items=0,
            total_pages=0,
            has_next=False,
            has_prev=False,
        )
        response = ModBrowseResponse(mods=[], pagination=pagination)

        assert len(response.mods) == 0
        assert response.pagination.total_items == 0

    def test_serialization_roundtrip(self) -> None:
        """ModBrowseResponse serializes to JSON and deserializes correctly."""
        mods = [
            ModBrowseItem(
                slug="testmod",
                name="Test Mod",
                author="TestAuthor",
                downloads=1000,
                follows=100,
                trending_points=50,
                side="both",
                mod_type="mod",
                tags=["Category1"],
            )
        ]
        pagination = PaginationMeta(
            page=1,
            page_size=20,
            total_items=1,
            total_pages=1,
            has_next=False,
            has_prev=False,
        )
        original = ModBrowseResponse(mods=mods, pagination=pagination)

        json_str = original.model_dump_json()
        restored = ModBrowseResponse.model_validate_json(json_str)

        assert len(restored.mods) == 1
        assert restored.mods[0].slug == "testmod"
        assert restored.mods[0].tags == ["Category1"]
        assert restored.pagination.total_items == 1

    def test_serialization_for_api_response(self) -> None:
        """ModBrowseResponse serializes correctly for API responses."""
        mods = [
            ModBrowseItem(
                slug="smithingplus",
                name="Smithing Plus",
                author="jayu",
                summary="Expanded smithing",
                downloads=204656,
                follows=2348,
                trending_points=1853,
                side="both",
                mod_type="mod",
                logo_url="https://example.com/logo.png",
                tags=["Crafting"],
                last_released="2025-10-09 21:28:57",
            )
        ]
        pagination = PaginationMeta(
            page=1,
            page_size=20,
            total_items=550,
            total_pages=28,
            has_next=True,
            has_prev=False,
        )
        response = ModBrowseResponse(mods=mods, pagination=pagination)

        data = response.model_dump(mode="json")

        assert "mods" in data
        assert "pagination" in data
        assert len(data["mods"]) == 1
        assert data["mods"][0]["slug"] == "smithingplus"
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_items"] == 550

    def test_nested_models_serialization(self) -> None:
        """ModBrowseResponse properly nests ModBrowseItem and PaginationMeta."""
        mod = ModBrowseItem(
            slug="testmod",
            name="Test Mod",
            author="Author",
            downloads=1000,
            follows=100,
            trending_points=50,
            side="client",
            mod_type="externaltool",
            tags=["Tools"],
        )
        pagination = PaginationMeta(
            page=2,
            page_size=10,
            total_items=25,
            total_pages=3,
            has_next=True,
            has_prev=True,
        )
        response = ModBrowseResponse(mods=[mod], pagination=pagination)

        data = response.model_dump(mode="json")

        # Verify nested structures
        assert data["mods"][0]["side"] == "client"
        assert data["mods"][0]["mod_type"] == "externaltool"
        assert data["mods"][0]["tags"] == ["Tools"]
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["has_prev"] is True
