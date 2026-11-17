"""Tests for ModApiClient - VintageStory mod database API client."""

import asyncio
import gc
import json
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from httpx import Response

from vintagestory_api.models.moddb import ModDict, normalize_mod, normalize_mod_list
from vintagestory_api.services.mod_api import (
    DownloadError,
    DownloadResult,
    ExternalApiError,
    GameVersionNotFoundError,
    ModApiClient,
    ModNotFoundError,
    ModReleaseNotDownloadableError,
    ModVersionNotFoundError,
    SharedFetches,
    check_compatibility,
    extract_slug,
    search_mods,
    sort_mods,
    validate_slug,
)

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"

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


class TestExceptions:
    """Tests for exception classes."""

    def test_game_version_not_found_error(self) -> None:
        """GameVersionNotFoundError stores version and has correct message."""
        error = GameVersionNotFoundError("1.21.3")
        assert error.version == "1.21.3"
        assert "1.21.3" in str(error)
        assert "not found" in str(error)


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
    async def test_get_mod_extracts_slug_from_url(self, mod_api_client: ModApiClient) -> None:
        """get_mod() extracts slug from full URL."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        result = await mod_api_client.get_mod("https://mods.vintagestory.at/smithingplus")

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
    async def test_get_mod_connection_error(self, mod_api_client: ModApiClient) -> None:
        """get_mod() raises ExternalApiError on connection error."""
        respx.get("https://mods.vintagestory.at/api/mod/anymod").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mod("anymod")

        assert "Could not connect" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_unexpected_status(self, mod_api_client: ModApiClient) -> None:
        """get_mod() raises ExternalApiError for unexpected status codes (VSS-d15).

        Returning None would read as "not found" to callers.
        """
        respx.get("https://mods.vintagestory.at/api/mod/anymod").mock(
            return_value=Response(
                200,
                json={"statuscode": "500", "error": "Internal Server Error"},
            )
        )

        with pytest.raises(ExternalApiError, match="unexpected status"):
            await mod_api_client.get_mod("anymod")

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "response",
        [
            Response(500, content=b""),
            Response(502, content=b"<html>Bad Gateway</html>"),
            Response(200, json=["not", "an", "object"]),
        ],
    )
    async def test_get_mod_unusable_body(
        self, mod_api_client: ModApiClient, response: Response
    ) -> None:
        """get_mod() raises ExternalApiError when the body is not a JSON object."""
        respx.get("https://mods.vintagestory.at/api/mod/anymod").mock(return_value=response)

        with pytest.raises(ExternalApiError):
            await mod_api_client.get_mod("anymod")

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_normalizes_canjewelry(self, mod_api_client: ModApiClient) -> None:
        """get_mod() returns the normalized entry: null fileids stay None (Story 17.1)."""
        payload = json.loads((FIXTURES / "mod_canjewelry.json").read_text())
        respx.get("https://mods.vintagestory.at/api/mod/canjewelry").mock(
            return_value=Response(200, json=payload)
        )

        result = await mod_api_client.get_mod("canjewelry")

        assert result is not None
        assert result["tags"] == ["Utility", "Cosmetics", "Crafting"]
        assert len(result["releases"]) == len(payload["mod"]["releases"])
        no_file = [r["modversion"] for r in result["releases"] if r["fileid"] is None]
        assert no_file == ["0.2.20", "0.1.26", "0.2.0"]
        # Fields the entry does not carry get their defaults
        assert result["follows"] == 0
        assert result["text"] is None

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [{"statuscode": "200"}, {"statuscode": "200", "mod": [1, 2]}],
    )
    async def test_get_mod_without_mod_object(
        self, mod_api_client: ModApiClient, payload: dict[str, Any]
    ) -> None:
        """get_mod() raises ExternalApiError when `mod` is missing or not an object."""
        respx.get("https://mods.vintagestory.at/api/mod/anymod").mock(
            return_value=Response(200, json=payload)
        )

        with pytest.raises(ExternalApiError, match="unexpected response"):
            await mod_api_client.get_mod("anymod")

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_generic_http_error(self, mod_api_client: ModApiClient) -> None:
        """get_mod() raises ExternalApiError on generic HTTPError."""
        respx.get("https://mods.vintagestory.at/api/mod/anymod").mock(
            side_effect=httpx.HTTPError("Generic HTTP error")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mod("anymod")

        assert "VintageStory mod API error" in str(exc_info.value)

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
    async def test_download_mod_not_found(self, mod_api_client: ModApiClient) -> None:
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
    async def test_download_version_not_found(self, mod_api_client: ModApiClient) -> None:
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
        from unittest.mock import AsyncMock, Mock, patch

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # Create async iterator that yields one chunk then fails
        async def chunk_iterator(*args: Any, **kwargs: Any):
            yield b"partial"
            raise httpx.HTTPError("connection reset")

        # Mock response object
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_bytes = chunk_iterator

        # Mock the client.stream context manager
        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response

        # Patch the client's stream method
        client = await mod_api_client._get_client()  # pyright: ignore[reportPrivateUsage]
        with patch.object(client, "stream", return_value=mock_stream):
            with pytest.raises(DownloadError):
                await mod_api_client.download_mod("smithingplus")

        # Verify no temp files left behind
        mods_cache = cache_dir / "mods"
        assert list(mods_cache.rglob("*.tmp")) == []
        assert not (mods_cache / "59176" / "smithingplus_1.8.3.zip").exists()

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_timeout_cleans_up(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        """download_mod() cleans up temp file on timeout."""
        from unittest.mock import AsyncMock, Mock, patch

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # Create async iterator that yields one chunk then times out
        async def chunk_iterator(*args: Any, **kwargs: Any):
            yield b"partial"
            raise httpx.TimeoutException("timeout during download")

        # Mock response object
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_bytes = chunk_iterator

        # Mock the client.stream context manager
        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response

        # Patch the client's stream method
        client = await mod_api_client._get_client()  # pyright: ignore[reportPrivateUsage]
        with patch.object(client, "stream", return_value=mock_stream):
            with pytest.raises(DownloadError) as exc_info:
                await mod_api_client.download_mod("smithingplus")

            assert "timed out" in str(exc_info.value)

        # Verify no temp files left behind
        mods_cache = cache_dir / "mods"
        assert list(mods_cache.rglob("*.tmp")) == []
        assert not (mods_cache / "59176" / "smithingplus_1.8.3.zip").exists()

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_io_error_cleans_up(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        """download_mod() cleans up temp file on IO error."""
        from unittest.mock import AsyncMock, Mock, patch

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # Create async iterator that yields chunks
        async def chunk_iterator(*args: Any, **kwargs: Any):
            yield b"partial"
            yield b"more data"

        # Mock response object
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_bytes = chunk_iterator

        # Mock the client.stream context manager
        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response

        # Track call count for write
        write_call_count = 0
        original_open = open

        def mock_open_func(path: Any, mode: str):
            nonlocal write_call_count
            file_obj = original_open(path, mode)
            original_write = file_obj.write

            def write_with_error(data: Any):
                nonlocal write_call_count
                write_call_count += 1
                if write_call_count > 1:
                    raise OSError("No space left on device")
                return original_write(data)

            file_obj.write = write_with_error
            return file_obj

        # Patch the client's stream method and open
        client = await mod_api_client._get_client()  # pyright: ignore[reportPrivateUsage]
        with patch.object(client, "stream", return_value=mock_stream):
            with patch("builtins.open", mock_open_func):
                with pytest.raises(DownloadError) as exc_info:
                    await mod_api_client.download_mod("smithingplus")

                assert "IO error" in str(exc_info.value)

        # Verify no temp files left behind
        mods_cache = cache_dir / "mods"
        assert list(mods_cache.rglob("*.tmp")) == []
        assert not (mods_cache / "59176" / "smithingplus_1.8.3.zip").exists()

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_timeout_with_temp_file_exists(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        """download_mod() removes temp file when timeout occurs after file creation."""
        from unittest.mock import AsyncMock, Mock, patch

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # Mock streaming to raise timeout during iteration
        async def chunk_iterator(*args: Any, **kwargs: Any):
            # Yield to make this an async generator, then raise during iteration
            yield b"partial data"  # First chunk writes to file
            raise httpx.TimeoutException("timeout during stream")

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_bytes = chunk_iterator

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response

        client = await mod_api_client._get_client()  # pyright: ignore[reportPrivateUsage]
        with patch.object(client, "stream", return_value=mock_stream):
            with pytest.raises(DownloadError) as exc_info:
                await mod_api_client.download_mod("smithingplus")

            assert "timed out" in str(exc_info.value)

        # Verify temp file was cleaned up
        mods_cache = cache_dir / "mods"
        assert list(mods_cache.rglob("*.tmp")) == []
        assert not (mods_cache / "59176" / "smithingplus_1.8.3.zip").exists()

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_http_error_with_temp_file_exists(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        """download_mod() removes temp file when HTTPError occurs after file creation."""
        from unittest.mock import AsyncMock, Mock, patch

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # Mock streaming to raise HTTP error during iteration
        async def chunk_iterator(*args: Any, **kwargs: Any):
            # Yield to make this an async generator, then raise during iteration
            yield b"partial data"  # First chunk writes to file
            raise httpx.HTTPError("connection reset by peer")

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_bytes = chunk_iterator

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response

        client = await mod_api_client._get_client()  # pyright: ignore[reportPrivateUsage]
        with patch.object(client, "stream", return_value=mock_stream):
            with pytest.raises(DownloadError):
                await mod_api_client.download_mod("smithingplus")

        # Verify temp file was cleaned up
        mods_cache = cache_dir / "mods"
        assert list(mods_cache.rglob("*.tmp")) == []
        assert not (mods_cache / "59176" / "smithingplus_1.8.3.zip").exists()

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_os_error_with_temp_file_exists(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        """download_mod() removes temp file when OSError occurs after file creation."""
        from unittest.mock import AsyncMock, Mock, patch

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # Mock streaming to raise OS error during iteration
        async def chunk_iterator(*args: Any, **kwargs: Any):
            # Yield to make this an async generator, then raise during iteration
            yield b"partial data"  # First chunk writes to file
            raise OSError("disk full")

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_bytes = chunk_iterator

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response

        client = await mod_api_client._get_client()  # pyright: ignore[reportPrivateUsage]
        with patch.object(client, "stream", return_value=mock_stream):
            with pytest.raises(DownloadError) as exc_info:
                await mod_api_client.download_mod("smithingplus")

            assert "IO error" in str(exc_info.value)

        # Verify temp file was cleaned up
        mods_cache = cache_dir / "mods"
        assert list(mods_cache.rglob("*.tmp")) == []
        assert not (mods_cache / "59176" / "smithingplus_1.8.3.zip").exists()

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_mod_no_releases(self, mod_api_client: ModApiClient) -> None:
        """download_mod() raises ModNotFoundError for mod with no releases."""
        mod_without_releases = {
            **SMITHINGPLUS_MOD,
            "releases": [],
        }

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": mod_without_releases},
            )
        )

        with pytest.raises(ModNotFoundError) as exc_info:
            await mod_api_client.download_mod("smithingplus")

        assert exc_info.value.slug == "smithingplus"

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_api_unavailable(self, mod_api_client: ModApiClient) -> None:
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

        result = await mod_api_client.download_mod("https://mods.vintagestory.at/smithingplus")

        assert result is not None
        assert result.version == "1.8.3"

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_with_cache_eviction(self, cache_dir: Path) -> None:
        """download_mod() triggers cache eviction when service is provided."""
        from unittest.mock import MagicMock

        from vintagestory_api.services.cache_eviction import EvictionResult

        # Create mock cache eviction service
        mock_eviction = MagicMock()
        mock_eviction.evict_if_needed.return_value = EvictionResult(
            files_evicted=2,
            bytes_freed=1024 * 1024,
            files_remaining=5,
            bytes_remaining=5 * 1024 * 1024,
        )

        # Create client with cache eviction service
        client = ModApiClient(
            cache_dir=cache_dir,
            cache_eviction_service=mock_eviction,
        )

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
            return_value=Response(200, content=b"content")
        )

        result = await client.download_mod("smithingplus")

        assert result is not None
        # Verify eviction was called
        mock_eviction.evict_if_needed.assert_called_once()

        await client.close()


# --- Story 17.2: which release download_mod picks (Epic 17 ADR-2) ---


def _fixture_payload(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"mod_{name}.json").read_text())


def _no_file_mod(modid: str) -> dict[str, Any]:
    """A one-mod-ID entry none of whose releases has a file."""
    return {
        "modid": 9998,
        "assetid": 9998,
        "name": modid,
        "urlalias": modid,
        "releases": [
            {
                "releaseid": 1,
                "modversion": "1.0.0",
                "modidstr": modid,
                "filename": f"{modid}_1.0.0.zip",
                "fileid": None,
                "tags": [],
            },
            {
                "releaseid": 2,
                "modversion": "0.9.0",
                "modidstr": modid,
                "filename": "",
                "fileid": 0,
                "tags": [],
            },
        ],
    }


class TestDownloadModReleaseSelection:
    """download_mod() picks the install mod ID's newest stable release with a file."""

    DOWNLOAD = "https://mods.vintagestory.at/download"

    def _mock_entry(self, slug: str, fixture: str) -> None:
        respx.get(f"https://mods.vintagestory.at/api/mod/{slug}").mock(
            return_value=Response(200, json=_fixture_payload(fixture))
        )

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("fixture", "slug", "version", "expected_version", "file_id", "filename"),
        [
            ("instruments", "instruments", None, "1.2.2", 12840, "instruments_1.2.2.zip"),
            ("instruments", "instruments", "1.0.1", "1.0.1", 1002, "instruments_1.0.1.zip"),
            ("instruments", "vsinstruments", None, "1.2.7", 18954, "vsinstruments_1.2.7.zip"),
            ("carryon", "carryon", None, "1.14.3", 113014, "CarryOn-1.22.0_v1.14.3.zip"),
            (
                "carryon",
                "carryon",
                "2.0.0-rc.1",
                "2.0.0-rc.1",
                130071,
                "CarryOn-1.22.0_v2.0.0-rc.1.zip",
            ),
            ("canjewelry", "canjewelry", None, "0.8.2", 138875, "canjewelry_0.8.2.zip"),
        ],
    )
    async def test_downloads_the_selected_release(
        self,
        mod_api_client: ModApiClient,
        fixture: str,
        slug: str,
        version: str | None,
        expected_version: str,
        file_id: int,
        filename: str,
    ) -> None:
        self._mock_entry(slug, fixture)
        download = respx.get(self.DOWNLOAD, params={"fileid": str(file_id)}).mock(
            return_value=Response(200, content=b"zip")
        )

        result = await mod_api_client.download_mod(slug, version)

        assert download.call_count == 1
        assert result is not None
        assert result.version == expected_version
        assert result.filename == filename
        assert result.release["modidstr"] == slug

    @respx.mock
    @pytest.mark.asyncio
    async def test_only_prereleases_downloads_the_first(self, mod_api_client: ModApiClient) -> None:
        payload = _fixture_payload("carryon")
        payload["mod"]["releases"] = [
            r for r in payload["mod"]["releases"] if "-" in r["modversion"]
        ]
        respx.get("https://mods.vintagestory.at/api/mod/carryon").mock(
            return_value=Response(200, json=payload)
        )
        download = respx.get(self.DOWNLOAD, params={"fileid": "130071"}).mock(
            return_value=Response(200, content=b"zip")
        )

        result = await mod_api_client.download_mod("carryon")

        assert download.called
        assert result is not None
        assert result.version == "2.0.0-rc.1"

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("fixture", "slug", "version"),
        [
            ("instruments", "instruments", "2.0.7"),
            ("carryon", "carryon", "latest"),
        ],
    )
    async def test_version_not_of_the_mod_id_is_not_found(
        self, mod_api_client: ModApiClient, fixture: str, slug: str, version: str
    ) -> None:
        self._mock_entry(slug, fixture)
        download = respx.get(self.DOWNLOAD).mock(return_value=Response(200, content=b"zip"))

        with pytest.raises(ModVersionNotFoundError) as exc_info:
            await mod_api_client.download_mod(slug, version)

        assert exc_info.value.slug == slug
        assert exc_info.value.version == version
        assert not download.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_named_release_without_a_file_is_refused(
        self, mod_api_client: ModApiClient
    ) -> None:
        self._mock_entry("canjewelry", "canjewelry")
        download = respx.get(self.DOWNLOAD).mock(return_value=Response(200, content=b"zip"))

        with pytest.raises(ModReleaseNotDownloadableError) as exc_info:
            await mod_api_client.download_mod("canjewelry", "0.2.20")

        assert exc_info.value.slug == "canjewelry"
        assert exc_info.value.version == "0.2.20"
        assert str(exc_info.value) == (
            "Version '0.2.20' of mod 'canjewelry' has no downloadable file in the mod database"
        )
        assert not download.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_mod_id_without_any_file_is_refused(self, mod_api_client: ModApiClient) -> None:
        respx.get("https://mods.vintagestory.at/api/mod/nofile").mock(
            return_value=Response(200, json={"statuscode": "200", "mod": _no_file_mod("nofile")})
        )
        download = respx.get(self.DOWNLOAD).mock(return_value=Response(200, content=b"zip"))

        with pytest.raises(ModReleaseNotDownloadableError) as exc_info:
            await mod_api_client.download_mod("nofile")

        assert exc_info.value.slug == "nofile"
        assert exc_info.value.version is None
        assert str(exc_info.value) == (
            "Mod 'nofile' has no release with a downloadable file in the mod database"
        )
        assert not download.called

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize("fileid", [0, -1])
    async def test_download_release_file_refuses_a_missing_file_id(
        self, mod_api_client: ModApiClient, fileid: int
    ) -> None:
        download = respx.get(self.DOWNLOAD).mock(return_value=Response(200, content=b"zip"))

        with pytest.raises(ModReleaseNotDownloadableError) as exc_info:
            await mod_api_client.download_release_file("demo", fileid, "x.zip")

        assert exc_info.value.slug == "demo"
        assert not download.called


# --- Tests for ModApiClient lifecycle ---


class TestResolveInstall:
    """resolve_install() is download_mod's lookup and selection without the download
    (Story 17.3): install needs the install mod ID before it downloads anything."""

    DOWNLOAD = "https://mods.vintagestory.at/download"

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("fixture", "slug", "mod_id", "version", "file_id", "asset_id"),
        [
            ("instruments", "instruments", "instruments", "1.2.2", 12840, 463),
            (
                "egocaribautomapmarkers",
                "automapmarkers",
                "egocaribautomapmarkers",
                "5.0.3",
                90054,
                797,
            ),
        ],
    )
    async def test_resolves_without_downloading(
        self,
        mod_api_client: ModApiClient,
        fixture: str,
        slug: str,
        mod_id: str,
        version: str,
        file_id: int,
        asset_id: int,
    ) -> None:
        respx.get(f"https://mods.vintagestory.at/api/mod/{slug}").mock(
            return_value=Response(200, json=_fixture_payload(fixture))
        )
        download = respx.get(self.DOWNLOAD).mock(return_value=Response(200, content=b"zip"))

        resolved = await mod_api_client.resolve_install(slug)

        assert (resolved.slug, resolved.mod_id) == (slug, mod_id)
        assert resolved.release["modversion"] == version
        assert resolved.release["modidstr"] == mod_id
        assert (resolved.file_id, resolved.asset_id) == (file_id, asset_id)
        assert not download.called
        # Story 17.4: the whole entry's releases, newest first, for the update record
        entry = normalize_mod(_fixture_payload(fixture)["mod"])
        assert entry is not None
        assert resolved.releases == entry["releases"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_accepts_a_url_and_a_version(self, mod_api_client: ModApiClient) -> None:
        respx.get("https://mods.vintagestory.at/api/mod/instruments").mock(
            return_value=Response(200, json=_fixture_payload("instruments"))
        )

        resolved = await mod_api_client.resolve_install(
            "https://mods.vintagestory.at/instruments", "1.0.1"
        )

        assert (resolved.slug, resolved.mod_id, resolved.file_id) == (
            "instruments",
            "instruments",
            1002,
        )

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_resolved_downloads_that_file(
        self, mod_api_client: ModApiClient
    ) -> None:
        respx.get("https://mods.vintagestory.at/api/mod/instruments").mock(
            return_value=Response(200, json=_fixture_payload("instruments"))
        )
        download = respx.get(self.DOWNLOAD, params={"fileid": "12840"}).mock(
            return_value=Response(200, content=b"zip")
        )
        resolved = await mod_api_client.resolve_install("instruments")

        result = await mod_api_client.download_resolved(resolved)

        assert download.call_count == 1
        assert (result.filename, result.version, result.asset_id) == (
            "instruments_1.2.2.zip",
            "1.2.2",
            463,
        )
        assert result.release is resolved.release
        assert result.path.read_bytes() == b"zip"


def gated_downloads(bodies: dict[int, bytes]) -> tuple[asyncio.Event, list[int]]:
    """Serve each file ID's body in two halves with `release` awaited in between.

    Returns (release, started): `started` lists the file IDs whose first half was sent.
    """
    release = asyncio.Event()
    started: list[int] = []

    class GatedStream(httpx.AsyncByteStream):
        def __init__(self, fileid: int) -> None:
            self.fileid = fileid

        async def __aiter__(self) -> AsyncIterator[bytes]:
            body = bodies[self.fileid]
            yield body[: len(body) // 2]
            started.append(self.fileid)
            await release.wait()
            yield body[len(body) // 2 :]

    def serve(request: httpx.Request) -> Response:
        fileid = int(request.url.params["fileid"])
        return Response(200, stream=GatedStream(fileid))

    respx.get("https://mods.vintagestory.at/download").mock(side_effect=serve)
    return release, started


async def release_when_started(release: asyncio.Event, started: list[int], count: int) -> None:
    while len(started) < count:
        await asyncio.sleep(0)
    release.set()


class TestCacheKeyedByFileId:
    """Story 19.4 (FR221, Epic 19 ADR-11): cache/mods/<fileid>/<name>."""

    def test_cache_path(self, mod_api_client: ModApiClient, cache_dir: Path) -> None:
        mods_cache = cache_dir / "mods"
        assert mod_api_client.cache_path(7, "Demo.zip") == mods_cache / "7" / "Demo.zip"
        assert mod_api_client.cache_path(8, "Demo.zip") != mod_api_client.cache_path(7, "Demo.zip")
        assert mod_api_client.cache_path(7, "../../x/evil.zip") == mods_cache / "7" / "evil.zip"
        with pytest.raises(ValueError):
            mod_api_client.cache_path(7, "..")

    @respx.mock
    @pytest.mark.asyncio
    async def test_two_mods_with_one_file_name_in_turn(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        respx.get("https://mods.vintagestory.at/download", params={"fileid": "11"}).mock(
            return_value=Response(200, content=b"mod a")
        )
        respx.get("https://mods.vintagestory.at/download", params={"fileid": "21"}).mock(
            return_value=Response(200, content=b"mod b")
        )

        first = await mod_api_client.download_release_file("moda", 11, "Same.zip")
        second = await mod_api_client.download_release_file("modb", 21, "Same.zip")

        assert first == cache_dir / "mods" / "11" / "Same.zip"
        assert second == cache_dir / "mods" / "21" / "Same.zip"
        assert (first.read_bytes(), second.read_bytes()) == (b"mod a", b"mod b")

    @respx.mock
    @pytest.mark.asyncio
    async def test_two_mods_with_one_file_name_at_once(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        bodies = {11: b"mod a " * 1000, 21: b"mod b " * 1000}
        release, started = gated_downloads(bodies)

        first, second, _ = await asyncio.gather(
            mod_api_client.download_release_file("moda", 11, "Same.zip"),
            mod_api_client.download_release_file("modb", 21, "Same.zip"),
            release_when_started(release, started, 2),
        )

        assert sorted(started) == [11, 21]
        assert first.read_bytes() == bodies[11]
        assert second.read_bytes() == bodies[21]
        assert list((cache_dir / "mods").rglob("*.tmp")) == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_one_release_twice_at_once(
        self, mod_api_client: ModApiClient, cache_dir: Path
    ) -> None:
        bodies = {11: b"mod a " * 1000}
        release, started = gated_downloads(bodies)

        first, second, _ = await asyncio.gather(
            mod_api_client.download_release_file("moda", 11, "Same.zip"),
            mod_api_client.download_release_file("moda", 11, "Same.zip"),
            release_when_started(release, started, 2),
        )

        assert first == second == cache_dir / "mods" / "11" / "Same.zip"
        assert first.read_bytes() == bodies[11]
        assert [p.name for p in (cache_dir / "mods" / "11").iterdir()] == ["Same.zip"]

    def test_remove_flat_layout(self, mod_api_client: ModApiClient, cache_dir: Path) -> None:
        mods_cache = cache_dir / "mods"
        for name in ("Old.zip", "other.cs", "Half.zip.tmp"):
            (mods_cache / name).write_bytes(b"old")
        (mods_cache / "11").mkdir()
        (mods_cache / "11" / "New.zip").write_bytes(b"new")

        assert mod_api_client.remove_flat_layout() == 3

        assert [p.name for p in mods_cache.iterdir()] == ["11"]
        assert (mods_cache / "11" / "New.zip").read_bytes() == b"new"

    def test_remove_flat_layout_unlinks_a_symlink_not_its_target(
        self, mod_api_client: ModApiClient, cache_dir: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / "target.zip"
        target.write_bytes(b"target")
        (cache_dir / "mods" / "Link.zip").symlink_to(target)

        assert mod_api_client.remove_flat_layout() == 1

        assert list((cache_dir / "mods").iterdir()) == []
        assert target.read_bytes() == b"target"


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


# --- Sample data for browse tests ---


# Sample mod list from /api/mods endpoint
BROWSE_MODS_LIST: list[dict[str, Any]] = [
    {
        "modid": 2655,
        "name": "Smithing Plus",
        "summary": "Expanded smithing mechanics",
        "author": "jayu",
        "downloads": 204656,
        "follows": 2348,
        "trendingpoints": 1853,
        "side": "both",
        "type": "mod",
        "logo": "https://moddbcdn.vintagestory.at/smithingplus/logo.png",
        "tags": ["Crafting", "QoL"],
        "lastreleased": "2025-10-09 21:28:57",
        "urlalias": "smithingplus",
    },
    {
        "modid": 1234,
        "name": "Old Popular Mod",
        "summary": "A very popular mod",
        "author": "author1",
        "downloads": 500000,
        "follows": 5000,
        "trendingpoints": 100,
        "side": "server",
        "type": "mod",
        "logo": None,
        "tags": ["Gameplay"],
        "lastreleased": "2024-01-15 10:00:00",
        "urlalias": "oldpopular",
    },
    {
        "modid": 5678,
        "name": "Trending New Mod",
        "summary": "Trending right now",
        "author": "author2",
        "downloads": 1000,
        "follows": 500,
        "trendingpoints": 5000,
        "side": "client",
        "type": "mod",
        "logo": "https://moddbcdn.vintagestory.at/trending/logo.png",
        "tags": ["UI"],
        "lastreleased": "2025-12-01 15:30:00",
        "urlalias": "trendingnew",
    },
]

BROWSE_MODS_RESPONSE: dict[str, Any] = {
    "statuscode": "200",
    "mods": [
        {
            "modid": 2655,
            "name": "Smithing Plus",
            "summary": "Expanded smithing mechanics",
            "author": "jayu",
            "downloads": 204656,
            "follows": 2348,
            "trendingpoints": 1853,
            "side": "both",
            "type": "mod",
            "logo": "https://moddbcdn.vintagestory.at/smithingplus/logo.png",
            "tags": ["Crafting", "QoL"],
            "lastreleased": "2025-10-09 21:28:57",
            "urlalias": "smithingplus",
        },
        {
            "modid": 1234,
            "name": "Old Popular Mod",
            "summary": "A very popular mod",
            "author": "author1",
            "downloads": 500000,
            "follows": 5000,
            "trendingpoints": 100,
            "side": "server",
            "type": "mod",
            "logo": None,
            "tags": ["Gameplay"],
            "lastreleased": "2024-01-15 10:00:00",
            "urlalias": "oldpopular",
        },
        {
            "modid": 5678,
            "name": "Trending New Mod",
            "summary": "Trending right now",
            "author": "author2",
            "downloads": 1000,
            "follows": 500,
            "trendingpoints": 5000,
            "side": "client",
            "type": "mod",
            "logo": "https://moddbcdn.vintagestory.at/trending/logo.png",
            "tags": ["UI"],
            "lastreleased": "2025-12-01 15:30:00",
            "urlalias": "trendingnew",
        },
    ],
}


# --- Tests for sort_mods ---


def normalized(mods: object) -> list[ModDict]:
    """sort_mods and search_mods take normalized data, as the router passes it (Story 17.1)."""
    result = normalize_mod_list(mods)
    assert result is not None
    return result


class TestSortMods:
    """Tests for sort_mods function."""

    def test_sort_by_downloads(self) -> None:
        """Sorts mods by downloads descending."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(normalized(mods), sort_by="downloads")

        assert result[0]["urlalias"] == "oldpopular"  # 500000 downloads
        assert result[1]["urlalias"] == "smithingplus"  # 204656 downloads
        assert result[2]["urlalias"] == "trendingnew"  # 1000 downloads

    def test_sort_by_trending(self) -> None:
        """Sorts mods by trending points descending."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(normalized(mods), sort_by="trending")

        assert result[0]["urlalias"] == "trendingnew"  # 5000 trending
        assert result[1]["urlalias"] == "smithingplus"  # 1853 trending
        assert result[2]["urlalias"] == "oldpopular"  # 100 trending

    def test_sort_by_recent(self) -> None:
        """Sorts mods by last released descending."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(normalized(mods), sort_by="recent")

        assert result[0]["urlalias"] == "trendingnew"  # 2025-12-01
        assert result[1]["urlalias"] == "smithingplus"  # 2025-10-09
        assert result[2]["urlalias"] == "oldpopular"  # 2024-01-15

    def test_sort_by_name(self) -> None:
        """Sorts mods by name ascending (alphabetical)."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(normalized(mods), sort_by="name")

        assert result[0]["urlalias"] == "oldpopular"  # Old Popular Mod
        assert result[1]["urlalias"] == "smithingplus"  # Smithing Plus
        assert result[2]["urlalias"] == "trendingnew"  # Trending New Mod

    def test_sort_by_name_ignores_leading_spaces_case_and_accents(self) -> None:
        """Story 16.8: name sort ignores surrounding spaces, letter case and accents."""
        mods: list[dict[str, object]] = [
            {"name": "Farm", "assetid": 1},
            {"name": "Étiquettes", "assetid": 2},
            {"name": "butcher", "assetid": 3},
            {"name": " Auto Map", "assetid": 4},
            {"name": "Apple", "assetid": 5},
            {"name": "etiquettes plus", "assetid": 6},
        ]
        result = sort_mods(normalized(mods), sort_by="name")

        assert [m["assetid"] for m in result] == [5, 4, 3, 2, 6, 1]

    def test_sort_by_name_handles_null_and_missing_names(self) -> None:
        """Story 16.8: a null or missing name sorts as empty instead of raising."""
        mods: list[dict[str, object]] = [
            {"name": "Beta", "assetid": 1},
            {"name": None, "assetid": 2},
            {"assetid": 3},
        ]
        result = sort_mods(normalized(mods), sort_by="name")

        assert [m["assetid"] for m in result] == [2, 3, 1]

    def test_sort_by_name_orders_equal_names_by_asset_id(self) -> None:
        """Story 16.8: equal names keep one order, by asset ID, whatever the input order."""
        mods: list[dict[str, object]] = [
            {"name": "Same", "assetid": 30},
            {"name": "same", "assetid": 10},
            {"name": "Same", "assetid": 20},
        ]
        result = sort_mods(normalized(mods), sort_by="name")
        reversed_result = sort_mods(normalized(list(reversed(mods))), sort_by="name")

        assert [m["assetid"] for m in result] == [20, 30, 10]
        assert [m["assetid"] for m in reversed_result] == [20, 30, 10]

    def test_sort_default_is_recent(self) -> None:
        """Default sort is by recent."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(normalized(mods))

        # Same as sort_by="recent"
        assert result[0]["urlalias"] == "trendingnew"

    def test_sort_handles_missing_values(self) -> None:
        """Normalization gives a missing count 0, so it sorts last (Story 17.1)."""
        mods = [
            {"urlalias": "mod1", "downloads": 100},
            {"urlalias": "mod2"},  # No downloads field
            {"urlalias": "mod3", "downloads": 200},
        ]
        result = sort_mods(normalized(mods), sort_by="downloads")

        assert result[0]["urlalias"] == "mod3"  # 200
        assert result[1]["urlalias"] == "mod1"  # 100
        assert result[2]["urlalias"] == "mod2"  # 0 (default)

    def test_sort_empty_list(self) -> None:
        """Handles empty mod list."""
        result = sort_mods([], sort_by="downloads")
        assert result == []

    def test_sort_single_mod(self) -> None:
        """Handles single mod list."""
        mods = normalized([{"urlalias": "single", "downloads": 100}])
        result = sort_mods(mods, sort_by="downloads")
        assert result == mods
        assert result[0]["urlalias"] == "single"
        assert result[0]["downloads"] == 100


# --- Tests for search_mods ---


class TestSearchMods:
    """Tests for search_mods function."""

    def test_search_empty_returns_all(self) -> None:
        """Empty search returns all mods."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(normalized(mods), "")
        assert len(result) == 3

    def test_search_by_name(self) -> None:
        """Searches mod names."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(normalized(mods), "smithing")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_by_author(self) -> None:
        """Searches mod authors."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(normalized(mods), "jayu")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_by_summary(self) -> None:
        """Searches mod summaries."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(normalized(mods), "trending")
        assert len(result) == 1
        assert result[0]["urlalias"] == "trendingnew"

    def test_search_by_summary_only(self) -> None:
        """Searches mod summaries when not in name or author."""
        mods = [
            {
                "urlalias": "mod1",
                "name": "Alpha Mod",
                "author": "Bob",
                "summary": "A mod with unique description",
                "tags": ["tag1"],
            },
        ]
        # Search for a term only in the summary
        result = search_mods(normalized(mods), "unique")
        assert len(result) == 1
        assert result[0]["urlalias"] == "mod1"

    def test_search_by_tag(self) -> None:
        """Searches mod tags."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(normalized(mods), "qol")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_case_insensitive(self) -> None:
        """Search is case insensitive."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(normalized(mods), "SMITHING")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_whitespace_trimmed(self) -> None:
        """Whitespace is trimmed from search term."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(normalized(mods), "  smithing  ")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_no_matches(self) -> None:
        """Returns empty list when no matches."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(normalized(mods), "nonexistent")
        assert result == []

    def test_search_with_none_summary(self) -> None:
        """Handles mods with None summary."""
        mods = [
            {
                "urlalias": "mod1",
                "name": "Mod One",
                "author": "author1",
                "summary": None,  # None summary
                "tags": ["tag1"],
            },
            {
                "urlalias": "mod2",
                "name": "Searchable Mod",
                "author": "author2",
                "summary": "Has searchable summary",
                "tags": ["tag2"],
            },
        ]
        result = search_mods(normalized(mods), "searchable")
        assert len(result) == 1
        assert result[0]["urlalias"] == "mod2"

    def test_search_with_tags_containing_term(self) -> None:
        """Searches within tag strings."""
        mods = [
            {
                "urlalias": "mod1",
                "name": "Mod One",
                "author": "author1",
                "summary": "Summary",
                "tags": ["gameplay", "crafting"],
            },
        ]
        result = search_mods(normalized(mods), "craft")
        assert len(result) == 1
        assert result[0]["urlalias"] == "mod1"

    def test_search_stops_at_first_match(self) -> None:
        """Returns mod on first field match (name takes priority)."""
        mods = [
            {
                "urlalias": "mod1",
                "name": "Test Name",
                "author": "Test Author",
                "summary": "Test Summary",
                "tags": ["Test"],
            },
        ]
        # Should find it in name first, but result is same
        result = search_mods(normalized(mods), "test")
        assert len(result) == 1


# --- Tests for ModApiClient.get_all_mods ---


class TestModApiClientGetAllMods:
    """Tests for ModApiClient.get_all_mods()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_success(self, mod_api_client: ModApiClient) -> None:
        """get_all_mods() returns list of mods on success."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_RESPONSE)
        )

        result = await mod_api_client.get_all_mods()

        assert len(result) == 3
        assert result[0]["name"] == "Smithing Plus"
        assert result[1]["name"] == "Old Popular Mod"
        assert result[2]["name"] == "Trending New Mod"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_normalizes_items(self, mod_api_client: ModApiClient) -> None:
        """get_all_mods() normalizes items and drops those that are not objects (Story 17.1)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "mods": [{"name": "A", "tags": ["QoL", None]}, None, "oops", {"name": "B"}],
                },
            )
        )

        result = await mod_api_client.get_all_mods()

        assert [m["name"] for m in result] == ["A", "B"]
        assert result[0]["tags"] == ["QoL"]
        assert result[1]["downloads"] == 0

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            {"statuscode": "200"},
            {"statuscode": "200", "mods": None},
            {"statuscode": "200", "mods": {}},
        ],
    )
    async def test_get_all_mods_without_mods_list(
        self, mod_api_client: ModApiClient, payload: dict[str, Any]
    ) -> None:
        """get_all_mods() raises, and caches nothing, when `mods` is not a list (Story 17.1)."""
        route = respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=payload)
        )

        with pytest.raises(ExternalApiError, match="unexpected response"):
            await mod_api_client.get_all_mods()
        with pytest.raises(ExternalApiError):
            await mod_api_client.get_all_mods()

        assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_caches_result(self, mod_api_client: ModApiClient) -> None:
        """get_all_mods() caches result and returns cached data on subsequent calls."""
        route = respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_RESPONSE)
        )

        # First call - fetches from API
        result1 = await mod_api_client.get_all_mods()
        assert route.call_count == 1

        # Second call - returns cached data
        result2 = await mod_api_client.get_all_mods()
        assert route.call_count == 1  # No additional API call

        # Results are the same
        assert result1 == result2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_force_refresh(self, mod_api_client: ModApiClient) -> None:
        """get_all_mods(force_refresh=True) bypasses cache."""
        route = respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_RESPONSE)
        )

        # First call - fetches from API
        await mod_api_client.get_all_mods()
        assert route.call_count == 1

        # Second call with force_refresh - fetches again
        await mod_api_client.get_all_mods(force_refresh=True)
        assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_timeout(self, mod_api_client: ModApiClient) -> None:
        """get_all_mods() raises ExternalApiError on timeout."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_all_mods()

        assert "timed out" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_connection_error(self, mod_api_client: ModApiClient) -> None:
        """get_all_mods() raises ExternalApiError on connection error."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_all_mods()

        assert "Could not connect" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_generic_http_error(self, mod_api_client: ModApiClient) -> None:
        """get_all_mods() raises ExternalApiError on generic HTTPError."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            side_effect=httpx.HTTPError("Generic HTTP error")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_all_mods()

        assert "VintageStory mod API error" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_unexpected_status(self, mod_api_client: ModApiClient) -> None:
        """get_all_mods() raises ExternalApiError on unexpected status."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json={"statuscode": "500", "error": "Server error"})
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_all_mods()

        assert "unexpected status" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_empty_list(self, mod_api_client: ModApiClient) -> None:
        """get_all_mods() handles empty mod list."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json={"statuscode": "200", "mods": []})
        )

        result = await mod_api_client.get_all_mods()

        assert result == []


# --- Tests for ModApiClient browse cache ---


class TestModApiClientBrowseCache:
    """Tests for ModApiClient browse cache methods."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_clear_browse_cache(self, mod_api_client: ModApiClient) -> None:
        """clear_browse_cache() clears the cache."""
        route = respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_RESPONSE)
        )

        # Populate cache
        await mod_api_client.get_all_mods()
        assert route.call_count == 1

        # Clear cache
        mod_api_client.clear_browse_cache()

        # Next call should fetch from API again
        await mod_api_client.get_all_mods()
        assert route.call_count == 2

    def test_is_browse_cache_valid_when_empty(self, mod_api_client: ModApiClient) -> None:
        """_is_browse_cache_valid() returns False when cache is empty."""
        # Access protected member for testing
        result = mod_api_client._is_browse_cache_valid()  # pyright: ignore[reportPrivateUsage]
        assert result is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_is_browse_cache_valid_when_populated(self, mod_api_client: ModApiClient) -> None:
        """_is_browse_cache_valid() returns True after cache is populated."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_RESPONSE)
        )

        await mod_api_client.get_all_mods()

        # Access protected member for testing
        result = mod_api_client._is_browse_cache_valid()  # pyright: ignore[reportPrivateUsage]
        assert result is True


# --- Test data for game versions ---

GAMEVERSIONS_RESPONSE: dict[str, Any] = {
    "statuscode": "200",
    "gameversions": [
        {"tagid": -281565171286015, "name": "1.21.3", "color": "#CCCCCC"},
        {"tagid": -281565171220479, "name": "1.21.2", "color": "#CCCCCC"},
        {"tagid": -281565171154943, "name": "1.21.1", "color": "#CCCCCC"},
        {"tagid": -281565171089407, "name": "1.21.0", "color": "#CCCCCC"},
    ],
}


# --- Tests for ModApiClient game versions cache ---


class TestModApiClientGameVersions:
    """Tests for ModApiClient game versions methods."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_success(self, mod_api_client: ModApiClient) -> None:
        """get_game_versions() returns version mapping on success."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, json=GAMEVERSIONS_RESPONSE)
        )

        result = await mod_api_client.get_game_versions()

        assert len(result) == 4
        assert result["1.21.3"] == -281565171286015
        assert result["1.21.0"] == -281565171089407

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_caches_result(self, mod_api_client: ModApiClient) -> None:
        """get_game_versions() caches result and returns cached data on subsequent calls."""
        route = respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, json=GAMEVERSIONS_RESPONSE)
        )

        # First call - fetches from API
        result1 = await mod_api_client.get_game_versions()
        assert route.call_count == 1

        # Second call - returns cached data
        result2 = await mod_api_client.get_game_versions()
        assert route.call_count == 1  # No additional API call

        # Results are the same
        assert result1 == result2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_force_refresh(self, mod_api_client: ModApiClient) -> None:
        """get_game_versions(force_refresh=True) bypasses cache."""
        route = respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, json=GAMEVERSIONS_RESPONSE)
        )

        # First call - fetches from API
        await mod_api_client.get_game_versions()
        assert route.call_count == 1

        # Second call with force_refresh - fetches again
        await mod_api_client.get_game_versions(force_refresh=True)
        assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_timeout(self, mod_api_client: ModApiClient) -> None:
        """get_game_versions() raises ExternalApiError on timeout."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "timed out" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_connection_error(self, mod_api_client: ModApiClient) -> None:
        """get_game_versions() raises ExternalApiError on connection error."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "Could not connect" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_http_error(self, mod_api_client: ModApiClient) -> None:
        """get_game_versions() raises ExternalApiError on HTTP error status."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(503, content=b"Service Unavailable")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "HTTP 503" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_invalid_json(self, mod_api_client: ModApiClient) -> None:
        """get_game_versions() raises ExternalApiError on invalid JSON."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, content=b"<html>Not JSON</html>")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "invalid JSON" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_unexpected_status(self, mod_api_client: ModApiClient) -> None:
        """get_game_versions() raises ExternalApiError on unexpected status."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, json={"statuscode": "500", "error": "Server error"})
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "unexpected status" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_generic_http_error(self, mod_api_client: ModApiClient) -> None:
        """get_game_versions() raises ExternalApiError on generic HTTPError."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            side_effect=httpx.HTTPError("Generic HTTP error")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "VintageStory mod API error" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_clear_gameversions_cache(self, mod_api_client: ModApiClient) -> None:
        """clear_gameversions_cache() clears the cache."""
        route = respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, json=GAMEVERSIONS_RESPONSE)
        )

        # Populate cache
        await mod_api_client.get_game_versions()
        assert route.call_count == 1

        # Clear cache
        mod_api_client.clear_gameversions_cache()

        # Next call should fetch from API again
        await mod_api_client.get_game_versions()
        assert route.call_count == 2

    def test_is_gameversions_cache_valid_when_empty(self, mod_api_client: ModApiClient) -> None:
        """_is_gameversions_cache_valid() returns False when cache is empty."""
        # Access protected member for testing
        # pyright: ignore[reportPrivateUsage]
        result = mod_api_client._is_gameversions_cache_valid()  # pyright: ignore[reportPrivateUsage]
        assert result is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_skips_malformed_entries(
        self, mod_api_client: ModApiClient
    ) -> None:
        """Non-object entries and ones without a str name and int tagid are skipped (18.3)."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        None,
                        "x",
                        {"name": 5, "tagid": -1},
                        {"name": "1.0.0", "tagid": "a"},
                        {"name": "1.0.1", "tagid": True},
                        {"name": "1.22.7", "tagid": -7},
                        {"name": "1.21.3", "tagid": -3},
                    ],
                },
            )
        )

        result = await mod_api_client.get_game_versions()

        assert result == {"1.22.7": -7, "1.21.3": -3}

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "body",
        [
            [{"name": "1.22.7", "tagid": -7}],
            {"statuscode": "200", "gameversions": "x"},
        ],
    )
    async def test_get_game_versions_unexpected_body_raises(
        self, mod_api_client: ModApiClient, body: object
    ) -> None:
        """A body that is not an object, or a non-list `gameversions`, raises (Story 18.3)."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, json=body)
        )

        with pytest.raises(ExternalApiError, match="unexpected response"):
            await mod_api_client.get_game_versions()

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_missing_key_is_empty(
        self, mod_api_client: ModApiClient
    ) -> None:
        """A missing `gameversions` key gives an empty map, as before (Story 18.3)."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, json={"statuscode": "200"})
        )

        assert await mod_api_client.get_game_versions() == {}


# --- Tests for ModApiClient get_mods_by_version ---


class TestModApiClientModsByVersion:
    """Tests for ModApiClient.get_mods_by_version() method."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_success(self, mod_api_client: ModApiClient) -> None:
        """get_mods_by_version() returns mods filtered by version."""
        version_tagid = -281565171286015  # 1.21.3
        route = respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(return_value=Response(200, json=BROWSE_MODS_RESPONSE))

        result = await mod_api_client.get_mods_by_version(version_tagid)

        assert route.called
        assert len(result) == 3  # Uses same test data as browse

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_normalizes_items(self, mod_api_client: ModApiClient) -> None:
        """get_mods_by_version() normalizes items and drops non-objects (Story 17.1)."""
        version_tagid = -281565171286015
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(
            return_value=Response(
                200, json={"statuscode": "200", "mods": [None, {"name": "A", "side": None}]}
            )
        )

        result = await mod_api_client.get_mods_by_version(version_tagid)

        assert len(result) == 1
        assert result[0]["side"] == ""

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload", [{"statuscode": "200"}, {"statuscode": "200", "mods": None}]
    )
    async def test_get_mods_by_version_without_mods_list(
        self, mod_api_client: ModApiClient, payload: dict[str, Any]
    ) -> None:
        """get_mods_by_version() raises when `mods` is missing or not a list (Story 17.1)."""
        version_tagid = -281565171286015
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(return_value=Response(200, json=payload))

        with pytest.raises(ExternalApiError, match="unexpected response"):
            await mod_api_client.get_mods_by_version(version_tagid)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_cache_hit(self, mod_api_client: ModApiClient) -> None:
        """A second call for the same tag is served from the cache (Story 18.3)."""
        version_tagid = -281565171286015
        route = respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(return_value=Response(200, json=BROWSE_MODS_RESPONSE))
        # Registered after the filtered route; it must not answer filtered requests
        plain = respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_RESPONSE)
        )

        first = await mod_api_client.get_mods_by_version(version_tagid)
        second = await mod_api_client.get_mods_by_version(version_tagid)

        assert route.call_count == 1
        assert plain.call_count == 0
        assert first == second

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_cache_miss_for_other_tag(
        self, mod_api_client: ModApiClient
    ) -> None:
        """Another tag makes its own request (Story 18.3)."""
        route_a = respx.get(
            "https://mods.vintagestory.at/api/mods", params={"gameversion": "-1"}
        ).mock(return_value=Response(200, json=_listing(1)))
        route_b = respx.get(
            "https://mods.vintagestory.at/api/mods", params={"gameversion": "-2"}
        ).mock(return_value=Response(200, json=_listing(2)))

        a = await mod_api_client.get_mods_by_version(-1)
        b = await mod_api_client.get_mods_by_version(-2)

        assert route_a.call_count == 1
        assert route_b.call_count == 1
        assert [m["modid"] for m in a] == [1]
        assert [m["modid"] for m in b] == [2]

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_cache_expires(self, mod_api_client: ModApiClient) -> None:
        """With the cache lifetime at zero the second call requests again (Story 18.3)."""
        mod_api_client.BROWSE_CACHE_TTL = timedelta(0)
        route = respx.get(
            "https://mods.vintagestory.at/api/mods", params={"gameversion": "-1"}
        ).mock(return_value=Response(200, json=_listing(1)))

        await mod_api_client.get_mods_by_version(-1)
        await mod_api_client.get_mods_by_version(-1)

        assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_failure_is_not_cached(
        self, mod_api_client: ModApiClient
    ) -> None:
        """A failed fetch raises, and the next call requests again (Story 18.3)."""
        route = respx.get(
            "https://mods.vintagestory.at/api/mods", params={"gameversion": "-1"}
        ).mock(
            side_effect=[
                Response(500, content=b"error"),
                Response(200, json=_listing(1)),
            ]
        )

        with pytest.raises(ExternalApiError):
            await mod_api_client.get_mods_by_version(-1)
        result = await mod_api_client.get_mods_by_version(-1)

        assert route.call_count == 2
        assert [m["modid"] for m in result] == [1]

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_failure_with_expired_copy_raises(
        self, mod_api_client: ModApiClient
    ) -> None:
        """The filter path raises on failure even when an expired copy exists (Story 18.3)."""
        mod_api_client.BROWSE_CACHE_TTL = timedelta(0)
        respx.get("https://mods.vintagestory.at/api/mods", params={"gameversion": "-1"}).mock(
            side_effect=[
                Response(200, json=_listing(1)),
                Response(500, content=b"error"),
            ]
        )

        await mod_api_client.get_mods_by_version(-1)
        with pytest.raises(ExternalApiError):
            await mod_api_client.get_mods_by_version(-1)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_timeout(self, mod_api_client: ModApiClient) -> None:
        """get_mods_by_version() raises ExternalApiError on timeout."""
        version_tagid = -281565171286015
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mods_by_version(version_tagid)

        assert "timed out" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_connection_error(self, mod_api_client: ModApiClient) -> None:
        """get_mods_by_version() raises ExternalApiError on connection error."""
        version_tagid = -281565171286015
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(side_effect=httpx.ConnectError("connection refused"))

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mods_by_version(version_tagid)

        assert "Could not connect" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_http_error(self, mod_api_client: ModApiClient) -> None:
        """get_mods_by_version() raises ExternalApiError on HTTP error status."""
        version_tagid = -281565171286015
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(return_value=Response(500, content=b"Internal Server Error"))

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mods_by_version(version_tagid)

        assert "HTTP 500" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_invalid_json(self, mod_api_client: ModApiClient) -> None:
        """get_mods_by_version() raises ExternalApiError on invalid JSON."""
        version_tagid = -281565171286015
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(return_value=Response(200, content=b"Not valid JSON"))

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mods_by_version(version_tagid)

        assert "invalid JSON" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_unexpected_status(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_mods_by_version() raises ExternalApiError on unexpected status."""
        version_tagid = -281565171286015
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(return_value=Response(200, json={"statuscode": "500", "error": "Server error"}))

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mods_by_version(version_tagid)

        assert "unexpected status" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_generic_http_error(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_mods_by_version() raises ExternalApiError on generic HTTPError."""
        version_tagid = -281565171286015
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(side_effect=httpx.HTTPError("Generic HTTP error"))

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_mods_by_version(version_tagid)

        assert "VintageStory mod API error" in str(exc_info.value)


# --- Tests for the filtered listing cache and the browse flag lookup (Story 18.3) ---

MODS_URL = "https://mods.vintagestory.at/api/mods"
GAMEVERSIONS_URL = "https://mods.vintagestory.at/api/gameversions"
TAG_1_22_7 = -7

VERSION_LIST_RESPONSE: dict[str, Any] = {
    "statuscode": "200",
    "gameversions": [
        {"tagid": TAG_1_22_7, "name": "1.22.7", "color": "#CCCCCC"},
        {"tagid": -3, "name": "1.21.3", "color": "#CCCCCC"},
    ],
}


def _listing(*modids: int) -> dict[str, Any]:
    """A mod database listing body holding one minimal entry per mod ID."""
    return {
        "statuscode": "200",
        "mods": [{"modid": i, "name": f"Mod {i}", "urlalias": f"mod{i}"} for i in modids],
    }


class TestModApiClientVersionListingCache:
    """The cache of filtered listings and get_version_mod_ids() (Story 18.3)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_eviction_keeps_three_newest(self, mod_api_client: ModApiClient) -> None:
        """Fetching four tags evicts the oldest; the other three stay cached."""
        routes = {
            tag: respx.get(MODS_URL, params={"gameversion": str(tag)}).mock(
                return_value=Response(200, json=_listing(-tag))
            )
            for tag in (-1, -2, -3, -4)
        }

        for tag in (-1, -2, -3, -4):
            await mod_api_client.get_mods_by_version(tag)
        for tag in (-4, -3, -2):
            await mod_api_client.get_mods_by_version(tag)
        assert [routes[t].call_count for t in (-1, -2, -3, -4)] == [1, 1, 1, 1]

        await mod_api_client.get_mods_by_version(-1)
        assert routes[-1].call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_concurrent_callers_share_one_fetch(self, mod_api_client: ModApiClient) -> None:
        """The flag lookup and the version filter for one tag make one request together."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=VERSION_LIST_RESPONSE))
        route = respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(
            return_value=Response(200, json=_listing(1, 2))
        )

        ids_a, mods, ids_b = await asyncio.gather(
            mod_api_client.get_version_mod_ids("1.22.7"),
            mod_api_client.get_mods_by_version(TAG_1_22_7),
            mod_api_client.get_version_mod_ids("1.22.7"),
        )

        assert route.call_count == 1
        assert ids_a == ids_b == frozenset({1, 2})
        assert [m["modid"] for m in mods] == [1, 2]

    @respx.mock
    @pytest.mark.asyncio
    async def test_clear_browse_cache_drops_listings(self, mod_api_client: ModApiClient) -> None:
        """clear_browse_cache() also drops the filtered listings."""
        route = respx.get(MODS_URL, params={"gameversion": "-1"}).mock(
            return_value=Response(200, json=_listing(1))
        )

        await mod_api_client.get_mods_by_version(-1)
        mod_api_client.clear_browse_cache()
        await mod_api_client.get_mods_by_version(-1)

        assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_mod_ids_hit(self, mod_api_client: ModApiClient) -> None:
        """Returns the modid set (an entry without modid is left out); then served from cache."""
        versions = respx.get(GAMEVERSIONS_URL).mock(
            return_value=Response(200, json=VERSION_LIST_RESPONSE)
        )
        body = _listing(1, 2)
        body["mods"].append({"name": "No ID", "urlalias": "noid"})
        route = respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(
            return_value=Response(200, json=body)
        )

        first = await mod_api_client.get_version_mod_ids("1.22.7")
        second = await mod_api_client.get_version_mod_ids("1.22.7")

        assert first == second == frozenset({1, 2})
        assert route.call_count == 1
        assert versions.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize("game_version", ["9.9.9", "stable"])
    async def test_version_mod_ids_unknown_version(
        self, mod_api_client: ModApiClient, game_version: str
    ) -> None:
        """A version without a tag gives None and no filtered request."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=VERSION_LIST_RESPONSE))
        route = respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(
            return_value=Response(200, json=_listing(1))
        )

        assert await mod_api_client.get_version_mod_ids(game_version) is None
        assert await mod_api_client.get_version_mod_ids(game_version) is None
        assert route.call_count == 0

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "effect",
        [
            Response(500, content=b"error"),
            httpx.ConnectError("connection refused"),
            Response(200, content=b"not json"),
        ],
    )
    async def test_version_mod_ids_failure_without_copy(
        self, mod_api_client: ModApiClient, effect: Response | Exception
    ) -> None:
        """A failed filtered listing with nothing cached gives None and does not raise."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=VERSION_LIST_RESPONSE))
        respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(side_effect=[effect])

        assert await mod_api_client.get_version_mod_ids("1.22.7") is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_mod_ids_failure_with_expired_copy(
        self, mod_api_client: ModApiClient
    ) -> None:
        """A failed refresh returns the expired copy."""
        mod_api_client.BROWSE_CACHE_TTL = timedelta(0)
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=VERSION_LIST_RESPONSE))
        route = respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(
            side_effect=[Response(200, json=_listing(1)), Response(500, content=b"error")]
        )

        assert await mod_api_client.get_version_mod_ids("1.22.7") == frozenset({1})
        assert await mod_api_client.get_version_mod_ids("1.22.7") == frozenset({1})
        assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_mod_ids_pause_after_failure(self, mod_api_client: ModApiClient) -> None:
        """After a failure the lookup is not retried until VERSION_FLAGS_RETRY_AFTER passes."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=VERSION_LIST_RESPONSE))
        route = respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(
            side_effect=[Response(500, content=b"error"), Response(200, json=_listing(1))]
        )

        assert await mod_api_client.get_version_mod_ids("1.22.7") is None
        assert await mod_api_client.get_version_mod_ids("1.22.7") is None
        assert route.call_count == 1

        mod_api_client.VERSION_FLAGS_RETRY_AFTER = timedelta(0)
        assert await mod_api_client.get_version_mod_ids("1.22.7") == frozenset({1})
        assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_mod_ids_version_list_fails_without_map(
        self, mod_api_client: ModApiClient
    ) -> None:
        """When the game version list fails and no map is known, the result is None."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(503, content=b"down"))
        route = respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(
            return_value=Response(200, json=_listing(1))
        )

        assert await mod_api_client.get_version_mod_ids("1.22.7") is None
        assert route.call_count == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_mod_ids_version_list_fails_with_expired_map_and_listing(
        self, mod_api_client: ModApiClient
    ) -> None:
        """An expired version map and an expired listing still give the old set."""
        mod_api_client.BROWSE_CACHE_TTL = timedelta(0)
        mod_api_client.GAMEVERSIONS_CACHE_TTL = timedelta(0)
        respx.get(GAMEVERSIONS_URL).mock(
            side_effect=[
                Response(200, json=VERSION_LIST_RESPONSE),
                Response(503, content=b"down"),
            ]
        )
        route = respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(
            return_value=Response(200, json=_listing(1))
        )

        assert await mod_api_client.get_version_mod_ids("1.22.7") == frozenset({1})
        assert await mod_api_client.get_version_mod_ids("1.22.7") == frozenset({1})
        assert route.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_slow_fetch_is_bounded_and_fills_cache(
        self, mod_api_client: ModApiClient
    ) -> None:
        """A slow fetch is not waited for beyond VERSION_FLAGS_WAIT and still fills the cache."""
        mod_api_client.VERSION_FLAGS_WAIT = 0.05
        release = asyncio.Event()
        started: list[httpx.Request] = []

        async def slow(request: httpx.Request) -> Response:
            started.append(request)
            await release.wait()
            return Response(200, json=_listing(1, 2))

        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=VERSION_LIST_RESPONSE))
        route = respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(side_effect=slow)

        assert await mod_api_client.get_version_mod_ids("1.22.7") is None
        # Within the pause it answers at once, even with a long wait configured
        mod_api_client.VERSION_FLAGS_WAIT = 30.0
        assert await asyncio.wait_for(mod_api_client.get_version_mod_ids("1.22.7"), 1) is None
        assert len(started) == 1

        release.set()
        mods = await mod_api_client.get_mods_by_version(TAG_1_22_7)
        assert [m["modid"] for m in mods] == [1, 2]
        assert await mod_api_client.get_version_mod_ids("1.22.7") == frozenset({1, 2})
        assert len(started) == 1
        assert route.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_close_cancels_running_fetch(self, mod_api_client: ModApiClient) -> None:
        """close() cancels a fetch that is still running, without an error."""
        mod_api_client.VERSION_FLAGS_WAIT = 0.05
        never = asyncio.Event()

        async def hang(request: httpx.Request) -> Response:
            await never.wait()
            return Response(200, json=_listing(1))

        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=VERSION_LIST_RESPONSE))
        respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(side_effect=hang)

        assert await mod_api_client.get_version_mod_ids("1.22.7") is None
        await mod_api_client.close()

        assert await mod_api_client.get_version_mod_ids("1.22.7") is None


# --- Malformed mod database bodies are an ExternalApiError (Story 19.6, Epic 19 ADR-13) ---

MALFORMED_BODIES = [
    b"<html>Not JSON</html>",
    b"",
    b"[]",
    b'"text"',
    b"null",
    b"5",
]
MOD_URL = "https://mods.vintagestory.at/api/mod/smithingplus"


def _malformed(body: bytes) -> Response:
    return Response(200, content=body)


class TestMalformedBodies:
    """Every fetcher raises ExternalApiError for a body that is not a JSON object, and a
    failed refresh leaves the cached copy and its time as they were (FR226)."""

    @respx.mock
    @pytest.mark.parametrize("body", MALFORMED_BODIES)
    async def test_get_mod(self, mod_api_client: ModApiClient, body: bytes) -> None:
        respx.get(MOD_URL).mock(
            side_effect=[
                _malformed(body),
                Response(200, json={"statuscode": "200", "mod": SMITHINGPLUS_MOD}),
            ]
        )

        with pytest.raises(ExternalApiError):
            await mod_api_client.get_mod("smithingplus")
        mod = await mod_api_client.get_mod("smithingplus")
        assert mod is not None
        assert mod["name"] == "Smithing Plus"

    @respx.mock
    @pytest.mark.parametrize("body", MALFORMED_BODIES)
    async def test_get_all_mods(self, mod_api_client: ModApiClient, body: bytes) -> None:
        respx.get(MODS_URL).mock(
            side_effect=[
                Response(200, json=_listing(1)),
                _malformed(body),
                Response(200, json=_listing(2)),
            ]
        )

        await mod_api_client.get_all_mods()
        cached = mod_api_client._browse_cache
        cached_at = mod_api_client._browse_cache_time
        with pytest.raises(ExternalApiError):
            await mod_api_client.get_all_mods(force_refresh=True)
        assert mod_api_client._browse_cache is cached
        assert mod_api_client._browse_cache_time == cached_at

        mods = await mod_api_client.get_all_mods(force_refresh=True)
        assert [m["modid"] for m in mods] == [2]

    @respx.mock
    @pytest.mark.parametrize("body", MALFORMED_BODIES)
    async def test_get_mods_by_version(self, mod_api_client: ModApiClient, body: bytes) -> None:
        respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(
            side_effect=[
                Response(200, json=_listing(1)),
                _malformed(body),
                Response(200, json=_listing(2)),
            ]
        )

        await mod_api_client.get_mods_by_version(TAG_1_22_7)
        cached = mod_api_client._version_listings[TAG_1_22_7]
        mod_api_client.BROWSE_CACHE_TTL = timedelta(0)
        with pytest.raises(ExternalApiError):
            await mod_api_client.get_mods_by_version(TAG_1_22_7)
        assert mod_api_client._version_listings[TAG_1_22_7] is cached
        assert mod_api_client._version_listings[TAG_1_22_7].fetched_at == cached.fetched_at

        mods = await mod_api_client.get_mods_by_version(TAG_1_22_7)
        assert [m["modid"] for m in mods] == [2]

    @respx.mock
    @pytest.mark.parametrize("body", MALFORMED_BODIES)
    async def test_get_game_versions(self, mod_api_client: ModApiClient, body: bytes) -> None:
        newer = {
            "statuscode": "200",
            "gameversions": [{"tagid": -9, "name": "1.23.0", "color": "#CCCCCC"}],
        }
        respx.get(GAMEVERSIONS_URL).mock(
            side_effect=[
                Response(200, json=VERSION_LIST_RESPONSE),
                _malformed(body),
                Response(200, json=newer),
            ]
        )

        await mod_api_client.get_game_versions()
        cached = mod_api_client._gameversions_cache
        cached_at = mod_api_client._gameversions_cache_time
        with pytest.raises(ExternalApiError):
            await mod_api_client.get_game_versions(force_refresh=True)
        assert mod_api_client._gameversions_cache is cached
        assert mod_api_client._gameversions_cache_time == cached_at

        assert await mod_api_client.get_game_versions(force_refresh=True) == {"1.23.0": -9}


# --- One shared in-flight fetch per cache (Story 19.6, Epic 19 ADR-13 decisions 5, 6) ---


class _Gate:
    """A respx side effect that holds every request until `open()`; counts requests."""

    def __init__(self, *responses: Response) -> None:
        self._responses = list(responses)
        self._event = asyncio.Event()
        self.requests = 0

    async def __call__(self, request: httpx.Request) -> Response:
        self.requests += 1
        await self._event.wait()
        return self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]

    def open(self) -> None:
        self._event.set()

    async def started(self, count: int = 1) -> None:
        """Wait until `count` requests have reached the gate."""
        async with asyncio.timeout(2):
            while self.requests < count:
                await asyncio.sleep(0)


async def _settle() -> None:
    """Let started tasks run up to their first real wait."""
    for _ in range(10):
        await asyncio.sleep(0)


class TestSharedFetches:
    """The game version list, the full listing and the filtered listings each make one
    request for concurrent callers (FR227)."""

    @respx.mock
    async def test_concurrent_cold_listing_calls_share_one_request(
        self, mod_api_client: ModApiClient
    ) -> None:
        gate = _Gate(Response(200, json=_listing(1, 2)))
        respx.get(MODS_URL).mock(side_effect=gate)

        calls = asyncio.gather(*(mod_api_client.get_all_mods() for _ in range(5)))
        await gate.started()
        await _settle()
        gate.open()
        results = await calls

        assert gate.requests == 1
        assert all([m["modid"] for m in r] == [1, 2] for r in results)

    @respx.mock
    async def test_concurrent_cold_game_version_calls_share_one_request(
        self, mod_api_client: ModApiClient
    ) -> None:
        gate = _Gate(Response(200, json=VERSION_LIST_RESPONSE))
        respx.get(GAMEVERSIONS_URL).mock(side_effect=gate)

        calls = asyncio.gather(*(mod_api_client.get_game_versions() for _ in range(5)))
        await gate.started()
        await _settle()
        gate.open()
        results = await calls

        assert gate.requests == 1
        assert all(r == {"1.22.7": TAG_1_22_7, "1.21.3": -3} for r in results)

    @respx.mock
    async def test_listing_failure_reaches_every_caller_and_is_not_kept(
        self, mod_api_client: ModApiClient
    ) -> None:
        gate = _Gate(Response(200, content=b"[]"), Response(200, json=_listing(1)))
        respx.get(MODS_URL).mock(side_effect=gate)

        calls = asyncio.gather(
            *(mod_api_client.get_all_mods() for _ in range(4)), return_exceptions=True
        )
        await gate.started()
        await _settle()
        gate.open()
        results = await calls

        assert gate.requests == 1
        assert all(isinstance(r, ExternalApiError) for r in results)
        mods = await mod_api_client.get_all_mods()
        assert gate.requests == 2
        assert [m["modid"] for m in mods] == [1]

    @respx.mock
    async def test_game_version_failure_reaches_every_caller_and_is_not_kept(
        self, mod_api_client: ModApiClient
    ) -> None:
        gate = _Gate(Response(200, content=b"[]"), Response(200, json=VERSION_LIST_RESPONSE))
        respx.get(GAMEVERSIONS_URL).mock(side_effect=gate)

        calls = asyncio.gather(
            *(mod_api_client.get_game_versions() for _ in range(4)), return_exceptions=True
        )
        await gate.started()
        await _settle()
        gate.open()
        results = await calls

        assert gate.requests == 1
        assert all(isinstance(r, ExternalApiError) for r in results)
        assert (await mod_api_client.get_game_versions())["1.22.7"] == TAG_1_22_7
        assert gate.requests == 2

    @respx.mock
    async def test_forced_listing_refresh_joins_the_running_fetch(
        self, mod_api_client: ModApiClient
    ) -> None:
        gate = _Gate(Response(200, json=_listing(1)))
        respx.get(MODS_URL).mock(side_effect=gate)

        first = asyncio.create_task(mod_api_client.get_all_mods())
        await gate.started()
        forced = asyncio.create_task(mod_api_client.get_all_mods(force_refresh=True))
        await _settle()
        gate.open()

        assert [m["modid"] for m in await first] == [1]
        assert [m["modid"] for m in await forced] == [1]
        assert gate.requests == 1

    @respx.mock
    async def test_forced_game_version_refresh_joins_the_running_fetch(
        self, mod_api_client: ModApiClient
    ) -> None:
        gate = _Gate(Response(200, json=VERSION_LIST_RESPONSE))
        respx.get(GAMEVERSIONS_URL).mock(side_effect=gate)

        first = asyncio.create_task(mod_api_client.get_game_versions())
        await gate.started()
        forced = asyncio.create_task(mod_api_client.get_game_versions(force_refresh=True))
        await _settle()
        gate.open()

        assert await first == await forced
        assert gate.requests == 1

    @respx.mock
    async def test_forced_refresh_without_a_running_fetch_fetches(
        self, mod_api_client: ModApiClient
    ) -> None:
        listing = respx.get(MODS_URL).mock(return_value=Response(200, json=_listing(1)))
        versions = respx.get(GAMEVERSIONS_URL).mock(
            return_value=Response(200, json=VERSION_LIST_RESPONSE)
        )

        await mod_api_client.get_all_mods()
        await mod_api_client.get_all_mods(force_refresh=True)
        await mod_api_client.get_game_versions()
        await mod_api_client.get_game_versions(force_refresh=True)

        assert listing.call_count == 2
        assert versions.call_count == 2

    @respx.mock
    async def test_expired_listing_concurrent_calls_share_one_request(
        self, mod_api_client: ModApiClient
    ) -> None:
        gate = _Gate(Response(200, json=_listing(1)), Response(200, json=_listing(2)))
        respx.get(MODS_URL).mock(side_effect=gate)
        gate.open()
        await mod_api_client.get_all_mods()
        assert gate.requests == 1

        mod_api_client.BROWSE_CACHE_TTL = timedelta(0)
        results = await asyncio.gather(*(mod_api_client.get_all_mods() for _ in range(3)))

        assert gate.requests == 2
        assert all([m["modid"] for m in r] == [2] for r in results)

    @respx.mock
    async def test_cancelled_waiter_does_not_cancel_the_fetch(
        self, mod_api_client: ModApiClient
    ) -> None:
        gate = _Gate(Response(200, json=_listing(1)))
        respx.get(MODS_URL).mock(side_effect=gate)

        first = asyncio.create_task(mod_api_client.get_all_mods())
        await gate.started()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        second = asyncio.create_task(mod_api_client.get_all_mods())
        await _settle()
        gate.open()

        assert [m["modid"] for m in await second] == [1]
        assert gate.requests == 1

    @respx.mock
    async def test_close_cancels_every_running_fetch(self, mod_api_client: ModApiClient) -> None:
        listing = _Gate(Response(200, json=_listing(1)))
        filtered = _Gate(Response(200, json=_listing(1)))
        versions = _Gate(Response(200, json=VERSION_LIST_RESPONSE))
        respx.get(MODS_URL, params={"gameversion": str(TAG_1_22_7)}).mock(side_effect=filtered)
        respx.get(MODS_URL).mock(side_effect=listing)
        respx.get(GAMEVERSIONS_URL).mock(side_effect=versions)

        all_mods = asyncio.create_task(mod_api_client.get_all_mods())
        game_versions = asyncio.create_task(mod_api_client.get_game_versions())
        by_version = asyncio.create_task(mod_api_client.get_mods_by_version(TAG_1_22_7))
        for gate in (listing, filtered, versions):
            await gate.started()

        await mod_api_client.close()
        await asyncio.gather(all_mods, game_versions, by_version, return_exceptions=True)

        assert mod_api_client._all_mods_fetch._tasks == {}
        assert mod_api_client._game_versions_fetch._tasks == {}
        assert mod_api_client._version_fetches._tasks == {}
        assert [t for t in asyncio.all_tasks() if t is not asyncio.current_task()] == []


class TestSharedFetchesHelper:
    """`SharedFetches` itself (Story 19.6)."""

    async def test_running_task_is_shared_and_finished_task_removed(self) -> None:
        fetches = SharedFetches[str, int]()
        release = asyncio.Event()

        async def value(n: int) -> int:
            await release.wait()
            return n

        first = fetches.get("k", lambda: value(1))
        assert fetches.get("k", lambda: value(9)) is first
        release.set()
        assert await first == 1
        await _settle()

        second = fetches.get("k", lambda: value(2))
        assert second is not first
        assert await second == 2

    async def test_unawaited_failure_is_not_reported(self) -> None:
        loop = asyncio.get_running_loop()
        seen: list[dict[str, Any]] = []
        loop.set_exception_handler(lambda _loop, context: seen.append(context))
        try:
            fetches = SharedFetches[str, int]()

            async def boom() -> int:
                raise ExternalApiError("down")

            task = fetches.get("k", boom)
            await _settle()
            assert task.done()
            del task
            gc.collect()
            assert seen == []
        finally:
            loop.set_exception_handler(None)
