"""Tests for ModApiClient - VintageStory mod database API client."""

from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from vintagestory_api.services.mod_api import (
    DownloadError,
    DownloadResult,
    ExternalApiError,
    ModApiClient,
    ModNotFoundError,
    ModVersionNotFoundError,
    check_compatibility,
    extract_slug,
    validate_slug,
)

# --- Helper fixtures ---


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture
def mod_api_client(cache_dir: Path) -> ModApiClient:
    """Create a ModApiClient with test cache directory."""
    return ModApiClient(cache_dir=cache_dir)


# Sample mod API response for "smithingplus"
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
        {
            "releaseid": 25000,
            "modversion": "1.7.0",
            "filename": "smithingplus_1.7.0.zip",
            "fileid": 55000,
            "downloads": 10000,
            "tags": ["1.20.0", "1.20.1"],
        },
    ],
}


# --- Tests for extract_slug ---


class TestExtractSlug:
    """Tests for extract_slug function."""

    def test_returns_slug_unchanged(self) -> None:
        """Plain slug is returned as-is."""
        assert extract_slug("smithingplus") == "smithingplus"

    def test_extracts_from_full_url(self) -> None:
        """Extracts slug from full mod URL."""
        url = "https://mods.vintagestory.at/smithingplus"
        assert extract_slug(url) == "smithingplus"

    def test_extracts_from_url_with_mod_prefix(self) -> None:
        """Extracts slug from URL with /mod/ prefix."""
        url = "https://mods.vintagestory.at/mod/smithingplus"
        assert extract_slug(url) == "smithingplus"

    def test_handles_trailing_slash(self) -> None:
        """Handles URLs with trailing slash."""
        url = "https://mods.vintagestory.at/smithingplus/"
        # Note: urlparse will include trailing slash in path
        assert extract_slug(url) == "smithingplus"

    def test_http_url(self) -> None:
        """Works with http:// URLs."""
        url = "http://mods.vintagestory.at/smithingplus"
        assert extract_slug(url) == "smithingplus"


# --- Tests for validate_slug ---


class TestValidateSlug:
    """Tests for validate_slug function."""

    def test_valid_simple_slug(self) -> None:
        """Simple alphanumeric slug is valid."""
        assert validate_slug("smithingplus") is True

    def test_valid_slug_with_dash(self) -> None:
        """Slug with dashes is valid."""
        assert validate_slug("my-cool-mod") is True

    def test_valid_slug_with_underscore(self) -> None:
        """Slug with underscores is valid."""
        assert validate_slug("my_cool_mod") is True

    def test_valid_slug_with_numbers(self) -> None:
        """Slug with numbers is valid."""
        assert validate_slug("mod123") is True

    def test_empty_slug_invalid(self) -> None:
        """Empty slug is invalid."""
        assert validate_slug("") is False

    def test_slug_too_long(self) -> None:
        """Slug over 50 chars is invalid."""
        assert validate_slug("a" * 51) is False

    def test_slug_at_limit(self) -> None:
        """Slug at exactly 50 chars is valid."""
        assert validate_slug("a" * 50) is True

    def test_slug_with_special_chars_invalid(self) -> None:
        """Slug with special characters is invalid."""
        assert validate_slug("mod@name") is False
        assert validate_slug("mod name") is False
        assert validate_slug("mod/name") is False
        assert validate_slug("mod.name") is False

    def test_path_traversal_rejected(self) -> None:
        """Path traversal patterns are rejected."""
        assert validate_slug("../etc") is False
        assert validate_slug("..\\windows") is False
        assert validate_slug("mod/../secret") is False
        assert validate_slug("./current") is False

    def test_windows_reserved_names_rejected(self) -> None:
        """Windows reserved device names are rejected."""
        # Basic reserved names
        assert validate_slug("con") is False
        assert validate_slug("prn") is False
        assert validate_slug("aux") is False
        assert validate_slug("nul") is False
        # Case insensitive
        assert validate_slug("CON") is False
        assert validate_slug("Con") is False
        # COM and LPT ports
        assert validate_slug("com1") is False
        assert validate_slug("COM9") is False
        assert validate_slug("lpt1") is False
        assert validate_slug("LPT9") is False

    def test_valid_slug_similar_to_reserved(self) -> None:
        """Slugs that contain but aren't reserved names are valid."""
        assert validate_slug("console") is True
        assert validate_slug("mycon") is True
        assert validate_slug("auxiliary") is True
        assert validate_slug("com10") is True  # Only COM1-9 are reserved


# --- Tests for check_compatibility ---


class TestCheckCompatibility:
    """Tests for check_compatibility function."""

    def test_exact_version_match(self) -> None:
        """Exact version in tags returns 'compatible'."""
        release = {"modversion": "1.8.3", "tags": ["1.21.0", "1.21.1", "1.21.3"]}
        result = check_compatibility(release, "1.21.3")
        assert result == "compatible"

    def test_major_minor_match(self) -> None:
        """Same major.minor returns 'not_verified'."""
        release = {"modversion": "1.8.3", "tags": ["1.21.0", "1.21.1"]}
        result = check_compatibility(release, "1.21.5")
        assert result == "not_verified"

    def test_no_match(self) -> None:
        """No matching version returns 'incompatible'."""
        release = {"modversion": "1.8.3", "tags": ["1.21.0", "1.21.1"]}
        result = check_compatibility(release, "1.20.0")
        assert result == "incompatible"

    def test_empty_tags(self) -> None:
        """Empty tags returns 'not_verified' (safe default)."""
        release: dict[str, str | list[str]] = {"modversion": "1.8.3", "tags": []}
        result = check_compatibility(release, "1.21.0")
        assert result == "not_verified"

    def test_missing_tags(self) -> None:
        """Missing tags key returns 'not_verified' (safe default)."""
        release = {"modversion": "1.8.3"}
        result = check_compatibility(release, "1.21.0")
        assert result == "not_verified"

    def test_major_only_tag_match(self) -> None:
        """Tag like '1.21' matches version '1.21.3'."""
        release = {"modversion": "1.8.3", "tags": ["1.21"]}
        result = check_compatibility(release, "1.21.3")
        assert result == "not_verified"

    def test_version_with_v_prefix(self) -> None:
        """Version with 'v' prefix is normalized."""
        release = {"modversion": "1.8.3", "tags": ["1.21.3"]}
        result = check_compatibility(release, "v1.21.3")
        assert result == "compatible"

    def test_version_stable_returns_not_verified(self) -> None:
        """Non-numeric version like 'stable' returns safe default."""
        release = {"modversion": "1.8.3", "tags": ["1.21.0", "1.21.1"]}
        result = check_compatibility(release, "stable")
        assert result == "not_verified"

    def test_version_latest_returns_not_verified(self) -> None:
        """Non-numeric version like 'latest' returns safe default."""
        release = {"modversion": "1.8.3", "tags": ["1.21.0"]}
        result = check_compatibility(release, "latest")
        assert result == "not_verified"

    def test_empty_game_version(self) -> None:
        """Empty game version returns 'not_verified'."""
        release = {"modversion": "1.8.3", "tags": ["1.21.0"]}
        result = check_compatibility(release, "")
        assert result == "not_verified"

    def test_single_number_version(self) -> None:
        """Single number version like '1' returns safe default."""
        release = {"modversion": "1.8.3", "tags": ["1.21.0"]}
        result = check_compatibility(release, "1")
        assert result == "not_verified"


# --- Tests for ModApiClient.get_mod ---


class TestModApiClientGetMod:
    """Tests for ModApiClient.get_mod()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_success(self, mod_api_client: ModApiClient) -> None:
        """get_mod() returns mod dict on success."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        result = await mod_api_client.get_mod("smithingplus")

        assert result is not None
        assert result["name"] == "Smithing Plus"
        assert result["urlalias"] == "smithingplus"
        assert len(result["releases"]) == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_not_found(self, mod_api_client: ModApiClient) -> None:
        """get_mod() returns None for 404."""
        respx.get("https://mods.vintagestory.at/api/mod/nonexistent").mock(
            return_value=Response(
                200,
                json={"statuscode": "404", "mod": None},
            )
        )

        result = await mod_api_client.get_mod("nonexistent")

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_extracts_slug_from_url(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_mod() extracts slug from full URL."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        result = await mod_api_client.get_mod(
            "https://mods.vintagestory.at/smithingplus"
        )

        assert result is not None
        assert result["name"] == "Smithing Plus"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_timeout(self, mod_api_client: ModApiClient) -> None:
        """get_mod() raises ExternalApiError on timeout."""
        respx.get("https://mods.vintagestory.at/api/mod/slowmod").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mod("slowmod")

        assert "timed out" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_connection_error(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_mod() raises ExternalApiError on connection error."""
        respx.get("https://mods.vintagestory.at/api/mod/anymod").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mod("anymod")

        assert "Could not connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_mod_invalid_slug(self, mod_api_client: ModApiClient) -> None:
        """get_mod() returns None for invalid slug."""
        result = await mod_api_client.get_mod("invalid slug with spaces")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_mod_empty_slug(self, mod_api_client: ModApiClient) -> None:
        """get_mod() returns None for empty slug."""
        result = await mod_api_client.get_mod("")
        assert result is None


# --- Tests for ModApiClient.download_mod ---


class TestModApiClientDownloadMod:
    """Tests for ModApiClient.download_mod()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_latest_version(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        """download_mod() downloads latest when version=None."""
        # Mock mod lookup
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # Mock file download
        respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
            return_value=Response(200, content=b"fake zip content")
        )

        result = await mod_api_client.download_mod("smithingplus")

        assert result is not None
        assert isinstance(result, DownloadResult)
        assert result.version == "1.8.3"  # Latest version
        assert result.filename == "smithingplus_1.8.3.zip"
        assert result.path.exists()
        assert result.path.read_bytes() == b"fake zip content"

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_specific_version(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        """download_mod() downloads specific version when requested."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        respx.get("https://mods.vintagestory.at/download?fileid=57894").mock(
            return_value=Response(200, content=b"version 1.8.2 content")
        )

        result = await mod_api_client.download_mod("smithingplus", version="1.8.2")

        assert result is not None
        assert result.version == "1.8.2"
        assert result.filename == "smithingplus_1.8.2.zip"
        assert result.path.read_bytes() == b"version 1.8.2 content"

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_mod_not_found(
        self, mod_api_client: ModApiClient
    ) -> None:
        """download_mod() raises ModNotFoundError for missing mod."""
        respx.get("https://mods.vintagestory.at/api/mod/nonexistent").mock(
            return_value=Response(
                200,
                json={"statuscode": "404", "mod": None},
            )
        )

        with pytest.raises(ModNotFoundError) as exc_info:
            await mod_api_client.download_mod("nonexistent")

        assert exc_info.value.slug == "nonexistent"

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_version_not_found(
        self, mod_api_client: ModApiClient
    ) -> None:
        """download_mod() raises ModVersionNotFoundError for missing version."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        with pytest.raises(ModVersionNotFoundError) as exc_info:
            await mod_api_client.download_mod("smithingplus", version="99.99.99")

        assert exc_info.value.slug == "smithingplus"
        assert exc_info.value.version == "99.99.99"

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_cleans_up_on_failure(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        """download_mod() cleans up temp file on download failure."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # Mock download failure mid-transfer
        respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
            side_effect=httpx.HTTPError("connection reset")
        )

        with pytest.raises(DownloadError):
            await mod_api_client.download_mod("smithingplus")

        # Verify no temp files left behind
        mods_cache = cache_dir / "mods"
        assert list(mods_cache.glob("*.tmp")) == []
        assert not (mods_cache / "smithingplus_1.8.3.zip").exists()

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_api_unavailable(
        self, mod_api_client: ModApiClient
    ) -> None:
        """download_mod() raises ExternalApiError when API unavailable."""
        respx.get("https://mods.vintagestory.at/api/mod/anymod").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with pytest.raises(ExternalApiError):
            await mod_api_client.download_mod("anymod")

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_extracts_slug_from_url(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        """download_mod() works with full URL input."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
            return_value=Response(200, content=b"content")
        )

        result = await mod_api_client.download_mod(
            "https://mods.vintagestory.at/smithingplus"
        )

        assert result is not None
        assert result.version == "1.8.3"


# --- Tests for ModApiClient lifecycle ---


class TestModApiClientLifecycle:
    """Tests for ModApiClient initialization and cleanup."""

    def test_creates_mods_cache_directory(self, cache_dir: Path) -> None:
        """ModApiClient creates mods cache subdirectory."""
        ModApiClient(cache_dir=cache_dir)
        assert (cache_dir / "mods").exists()
        assert (cache_dir / "mods").is_dir()

    @pytest.mark.asyncio
    async def test_close_closes_client(self, mod_api_client: ModApiClient) -> None:
        """close() properly closes the HTTP client."""
        # Access client to create it (accessing protected members for test verification)
        await mod_api_client._get_client()  # pyright: ignore[reportPrivateUsage]
        assert mod_api_client._client is not None  # pyright: ignore[reportPrivateUsage]

        await mod_api_client.close()
        assert mod_api_client._client is None  # pyright: ignore[reportPrivateUsage]
