"""Tests for version fetching and availability checking."""

import pytest
import respx
from httpx import Response

from vintagestory_api.services.server import (
    VS_CDN_BASE,
    VS_STABLE_API,
    VS_UNSTABLE_API,
    ServerService,
)

from .conftest import MOCK_STABLE_API_RESPONSE, MOCK_UNSTABLE_API_RESPONSE

# pyright: reportPrivateUsage=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false


class TestGetAvailableVersions:
    """Tests for fetching available versions from VintageStory API (Subtask 1.2)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_stable_versions_success(self, server_service: ServerService) -> None:
        """Successfully fetch available stable versions."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))

        versions = await server_service.get_available_versions("stable")

        assert len(versions) == 2
        assert "1.21.6" in versions
        assert "1.21.5" in versions
        assert versions["1.21.6"].is_latest is True
        assert versions["1.21.5"].is_latest is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_unstable_versions_success(self, server_service: ServerService) -> None:
        """Successfully fetch available unstable versions."""
        respx.get(VS_UNSTABLE_API).mock(return_value=Response(200, json=MOCK_UNSTABLE_API_RESPONSE))

        versions = await server_service.get_available_versions("unstable")

        assert len(versions) == 1
        assert "1.22.0-pre.1" in versions
        assert versions["1.22.0-pre.1"].channel == "unstable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_info_contains_all_fields(self, server_service: ServerService) -> None:
        """Version info includes all expected fields."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))

        versions = await server_service.get_available_versions("stable")
        version = versions["1.21.6"]

        assert version.version == "1.21.6"
        assert version.filename == "vs_server_linux-x64_1.21.6.tar.gz"
        assert version.filesize == "40.2 MB"
        assert version.md5 == "abc123def456"
        assert "cdn.vintagestory.at" in version.cdn_url
        assert version.channel == "stable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_versions_api_error(self, server_service: ServerService) -> None:
        """API error raises HTTPStatusError."""
        respx.get(VS_STABLE_API).mock(return_value=Response(500))

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            await server_service.get_available_versions("stable")


class TestCheckVersionAvailable:
    """Tests for checking version availability (Subtask 1.3)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_stable_version_available(self, server_service: ServerService) -> None:
        """Version available in stable channel returns True with channel."""
        url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.3.tar.gz"
        respx.head(url).mock(return_value=Response(200))

        available, channel = await server_service.check_version_available("1.21.3")

        assert available is True
        assert channel == "stable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_unstable_version_available_fallback(self, server_service: ServerService) -> None:
        """Version available only in unstable channel found via fallback."""
        stable_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.22.0-pre.1.tar.gz"
        unstable_url = f"{VS_CDN_BASE}/unstable/vs_server_linux-x64_1.22.0-pre.1.tar.gz"

        respx.head(stable_url).mock(return_value=Response(404))
        respx.head(unstable_url).mock(return_value=Response(200))

        available, channel = await server_service.check_version_available("1.22.0-pre.1")

        assert available is True
        assert channel == "unstable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_not_found_any_channel(self, server_service: ServerService) -> None:
        """Version not found in any channel returns False."""
        stable_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.99.0.tar.gz"
        unstable_url = f"{VS_CDN_BASE}/unstable/vs_server_linux-x64_1.99.0.tar.gz"

        respx.head(stable_url).mock(return_value=Response(404))
        respx.head(unstable_url).mock(return_value=Response(404))

        available, channel = await server_service.check_version_available("1.99.0")

        assert available is False
        assert channel is None

    @pytest.mark.asyncio
    async def test_invalid_version_format_returns_false(
        self, server_service: ServerService
    ) -> None:
        """Invalid version format returns False without making API calls."""
        available, channel = await server_service.check_version_available("invalid")

        assert available is False
        assert channel is None


class TestGetVersionInfo:
    """Tests for getting detailed version information (Subtask 1.3)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_version_info_stable(self, server_service: ServerService) -> None:
        """Get version info for stable version."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))

        info = await server_service.get_version_info("1.21.6")

        assert info is not None
        assert info.version == "1.21.6"
        assert info.md5 == "abc123def456"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_version_info_unstable_fallback(self, server_service: ServerService) -> None:
        """Get version info for unstable version via fallback."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))
        respx.get(VS_UNSTABLE_API).mock(return_value=Response(200, json=MOCK_UNSTABLE_API_RESPONSE))

        info = await server_service.get_version_info("1.22.0-pre.1")

        assert info is not None
        assert info.version == "1.22.0-pre.1"
        assert info.channel == "unstable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_version_info_not_found(self, server_service: ServerService) -> None:
        """Get version info for non-existent version returns None."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))
        respx.get(VS_UNSTABLE_API).mock(return_value=Response(200, json=MOCK_UNSTABLE_API_RESPONSE))

        info = await server_service.get_version_info("1.99.0")

        assert info is None

    @pytest.mark.asyncio
    async def test_get_version_info_invalid_format(self, server_service: ServerService) -> None:
        """Get version info for invalid format returns None."""
        info = await server_service.get_version_info("invalid")

        assert info is None
