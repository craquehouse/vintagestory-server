"""Tests for ModApiClient - VintageStory mod database API client."""

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from httpx import Response

from vintagestory_api.services.mod_api import (
    DownloadError,
    DownloadResult,
    ExternalApiError,
    GameVersionNotFoundError,
    ModApiClient,
    ModNotFoundError,
    ModVersionNotFoundError,
    check_compatibility,
    extract_slug,
    search_mods,
    sort_mods,
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

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_unexpected_status(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_mod() returns None for unexpected status codes."""
        respx.get("https://mods.vintagestory.at/api/mod/anymod").mock(
            return_value=Response(
                200,
                json={"statuscode": "500", "error": "Internal Server Error"},
            )
        )

        result = await mod_api_client.get_mod("anymod")
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mod_generic_http_error(
        self, mod_api_client: ModApiClient
    ) -> None:
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
        from unittest.mock import AsyncMock, Mock, patch

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # Create async iterator that yields one chunk then fails
        async def chunk_iterator(*args, **kwargs):
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
        assert list(mods_cache.glob("*.tmp")) == []
        assert not (mods_cache / "smithingplus_1.8.3.zip").exists()

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
        async def chunk_iterator(*args, **kwargs):
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
        assert list(mods_cache.glob("*.tmp")) == []

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
        async def chunk_iterator(*args, **kwargs):
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

        def mock_open_func(path, mode):
            nonlocal write_call_count
            file_obj = original_open(path, mode)
            original_write = file_obj.write

            def write_with_error(data):
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
        assert list(mods_cache.glob("*.tmp")) == []

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
        async def chunk_iterator(*args, **kwargs):
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
        temp_path = mods_cache / "smithingplus_1.8.3.zip.tmp"
        assert not temp_path.exists()

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
        async def chunk_iterator(*args, **kwargs):
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
        temp_path = mods_cache / "smithingplus_1.8.3.zip.tmp"
        assert not temp_path.exists()

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
        async def chunk_iterator(*args, **kwargs):
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
        temp_path = mods_cache / "smithingplus_1.8.3.zip.tmp"
        assert not temp_path.exists()

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_mod_no_releases(
        self, mod_api_client: ModApiClient
    ) -> None:
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


class TestSortMods:
    """Tests for sort_mods function."""

    def test_sort_by_downloads(self) -> None:
        """Sorts mods by downloads descending."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(mods, sort_by="downloads")

        assert result[0]["urlalias"] == "oldpopular"  # 500000 downloads
        assert result[1]["urlalias"] == "smithingplus"  # 204656 downloads
        assert result[2]["urlalias"] == "trendingnew"  # 1000 downloads

    def test_sort_by_trending(self) -> None:
        """Sorts mods by trending points descending."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(mods, sort_by="trending")

        assert result[0]["urlalias"] == "trendingnew"  # 5000 trending
        assert result[1]["urlalias"] == "smithingplus"  # 1853 trending
        assert result[2]["urlalias"] == "oldpopular"  # 100 trending

    def test_sort_by_recent(self) -> None:
        """Sorts mods by last released descending."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(mods, sort_by="recent")

        assert result[0]["urlalias"] == "trendingnew"  # 2025-12-01
        assert result[1]["urlalias"] == "smithingplus"  # 2025-10-09
        assert result[2]["urlalias"] == "oldpopular"  # 2024-01-15

    def test_sort_by_name(self) -> None:
        """Sorts mods by name ascending (alphabetical)."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(mods, sort_by="name")

        assert result[0]["urlalias"] == "oldpopular"  # Old Popular Mod
        assert result[1]["urlalias"] == "smithingplus"  # Smithing Plus
        assert result[2]["urlalias"] == "trendingnew"  # Trending New Mod

    def test_sort_default_is_recent(self) -> None:
        """Default sort is by recent."""
        mods = BROWSE_MODS_LIST.copy()
        result = sort_mods(mods)

        # Same as sort_by="recent"
        assert result[0]["urlalias"] == "trendingnew"

    def test_sort_handles_missing_values(self) -> None:
        """Handles mods with missing sort fields."""
        mods = [
            {"urlalias": "mod1", "downloads": 100},
            {"urlalias": "mod2"},  # No downloads field
            {"urlalias": "mod3", "downloads": 200},
        ]
        result = sort_mods(mods, sort_by="downloads")

        assert result[0]["urlalias"] == "mod3"  # 200
        assert result[1]["urlalias"] == "mod1"  # 100
        assert result[2]["urlalias"] == "mod2"  # 0 (default)

    def test_sort_empty_list(self) -> None:
        """Handles empty mod list."""
        result = sort_mods([], sort_by="downloads")
        assert result == []

    def test_sort_single_mod(self) -> None:
        """Handles single mod list."""
        mods = [{"urlalias": "single", "downloads": 100}]
        result = sort_mods(mods, sort_by="downloads")
        assert result == [{"urlalias": "single", "downloads": 100}]


# --- Tests for search_mods ---


class TestSearchMods:
    """Tests for search_mods function."""

    def test_search_empty_returns_all(self) -> None:
        """Empty search returns all mods."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(mods, "")
        assert len(result) == 3

    def test_search_by_name(self) -> None:
        """Searches mod names."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(mods, "smithing")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_by_author(self) -> None:
        """Searches mod authors."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(mods, "jayu")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_by_summary(self) -> None:
        """Searches mod summaries."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(mods, "trending")
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
        result = search_mods(mods, "unique")
        assert len(result) == 1
        assert result[0]["urlalias"] == "mod1"

    def test_search_by_tag(self) -> None:
        """Searches mod tags."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(mods, "qol")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_case_insensitive(self) -> None:
        """Search is case insensitive."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(mods, "SMITHING")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_whitespace_trimmed(self) -> None:
        """Whitespace is trimmed from search term."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(mods, "  smithing  ")
        assert len(result) == 1
        assert result[0]["urlalias"] == "smithingplus"

    def test_search_no_matches(self) -> None:
        """Returns empty list when no matches."""
        mods = BROWSE_MODS_LIST.copy()
        result = search_mods(mods, "nonexistent")
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
        result = search_mods(mods, "searchable")
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
        result = search_mods(mods, "craft")
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
        result = search_mods(mods, "test")
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
    async def test_get_all_mods_caches_result(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_all_mods_force_refresh(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_all_mods_connection_error(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_all_mods() raises ExternalApiError on connection error."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_all_mods()

        assert "Could not connect" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_generic_http_error(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_all_mods() raises ExternalApiError on generic HTTPError."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            side_effect=httpx.HTTPError("Generic HTTP error")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_all_mods()

        assert "VintageStory mod API error" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_all_mods_unexpected_status(
        self, mod_api_client: ModApiClient
    ) -> None:
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

    def test_is_browse_cache_valid_when_empty(
        self, mod_api_client: ModApiClient
    ) -> None:
        """_is_browse_cache_valid() returns False when cache is empty."""
        # Access protected member for testing
        result = mod_api_client._is_browse_cache_valid()  # pyright: ignore[reportPrivateUsage]
        assert result is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_is_browse_cache_valid_when_populated(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_game_versions_success(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_game_versions_caches_result(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_game_versions_force_refresh(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_game_versions_timeout(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_game_versions() raises ExternalApiError on timeout."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "timed out" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_connection_error(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_game_versions() raises ExternalApiError on connection error."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "Could not connect" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_http_error(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_game_versions() raises ExternalApiError on HTTP error status."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(503, content=b"Service Unavailable")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "HTTP 503" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_invalid_json(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_game_versions() raises ExternalApiError on invalid JSON."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, content=b"<html>Not JSON</html>")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "invalid JSON" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_unexpected_status(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_game_versions() raises ExternalApiError on unexpected status."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, json={"statuscode": "500", "error": "Server error"})
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "unexpected status" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_game_versions_generic_http_error(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_game_versions() raises ExternalApiError on generic HTTPError."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            side_effect=httpx.HTTPError("Generic HTTP error")
        )

        with pytest.raises(ExternalApiError) as exc_info:
            await mod_api_client.get_game_versions()

        assert "VintageStory mod API error" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_clear_gameversions_cache(
        self, mod_api_client: ModApiClient
    ) -> None:
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

    def test_is_gameversions_cache_valid_when_empty(
        self, mod_api_client: ModApiClient
    ) -> None:
        """_is_gameversions_cache_valid() returns False when cache is empty."""
        # Access protected member for testing
        # pyright: ignore[reportPrivateUsage]
        result = mod_api_client._is_gameversions_cache_valid()  # pyright: ignore[reportPrivateUsage]
        assert result is False


# --- Tests for ModApiClient get_mods_by_version ---


class TestModApiClientModsByVersion:
    """Tests for ModApiClient.get_mods_by_version() method."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_success(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_mods_by_version_not_cached(
        self, mod_api_client: ModApiClient
    ) -> None:
        """get_mods_by_version() does not use browse cache (each call fetches)."""
        version_tagid = -281565171286015
        route = respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": str(version_tagid)},
        ).mock(return_value=Response(200, json=BROWSE_MODS_RESPONSE))

        # First call
        await mod_api_client.get_mods_by_version(version_tagid)
        assert route.call_count == 1

        # Second call - should fetch again (not cached)
        await mod_api_client.get_mods_by_version(version_tagid)
        assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_mods_by_version_timeout(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_mods_by_version_connection_error(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_mods_by_version_http_error(
        self, mod_api_client: ModApiClient
    ) -> None:
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
    async def test_get_mods_by_version_invalid_json(
        self, mod_api_client: ModApiClient
    ) -> None:
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
