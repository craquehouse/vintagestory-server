"""Tests for server versions check job.

Story 8.2: Server Versions Check Job
Story 13.1: Server Versions API - Added full version list caching

Tests cover:
- Job populates latest version strings in cache
- Job populates full version lists in cache (Story 13.1)
- API errors preserve stale cache
- Individual channel failures don't affect other channels
"""

from collections.abc import Callable, Generator
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from vintagestory_api.jobs.server_versions import check_server_versions
from vintagestory_api.models.server import VersionInfo
from vintagestory_api.services.versions_cache import get_versions_cache, reset_versions_cache


def make_version_getter(
    versions: dict[str, dict[str, VersionInfo]],
) -> Callable[[str], dict[str, VersionInfo]]:
    """Create a typed getter function for mock side_effect."""
    def getter(channel: str) -> dict[str, VersionInfo]:
        return versions.get(channel, {})
    return getter


@pytest.fixture(autouse=True)
def reset_cache() -> Generator[None]:
    """Reset versions cache before and after each test."""
    reset_versions_cache()
    yield
    reset_versions_cache()


@pytest.fixture
def mock_versions() -> dict[str, dict[str, VersionInfo]]:
    """Sample versions data for mocking."""
    return {
        "stable": {
            "1.21.3": VersionInfo(
                version="1.21.3",
                filename="vs_server_linux-x64_1.21.3.tar.gz",
                filesize="40.2 MB",
                md5="abc123",
                cdn_url="https://cdn.vintagestory.at/stable/1",
                local_url="https://vintagestory.at/stable/1",
                is_latest=True,
                channel="stable",
            ),
            "1.21.2": VersionInfo(
                version="1.21.2",
                filename="vs_server_linux-x64_1.21.2.tar.gz",
                filesize="40.1 MB",
                md5="def456",
                cdn_url="https://cdn.vintagestory.at/stable/2",
                local_url="https://vintagestory.at/stable/2",
                is_latest=False,
                channel="stable",
            ),
        },
        "unstable": {
            "1.22.0-pre.1": VersionInfo(
                version="1.22.0-pre.1",
                filename="vs_server_linux-x64_1.22.0-pre.1.tar.gz",
                filesize="41.0 MB",
                md5="xyz789",
                cdn_url="https://cdn.vintagestory.at/unstable/1",
                local_url="https://vintagestory.at/unstable/1",
                is_latest=True,
                channel="unstable",
            ),
        },
    }


class TestCheckServerVersionsJob:
    """Tests for check_server_versions job."""

    @pytest.mark.asyncio
    async def test_populates_latest_versions(
        self, mock_versions: dict[str, dict[str, VersionInfo]]
    ) -> None:
        """Job should populate latest version strings in cache."""
        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=make_version_getter(mock_versions)
            )
            mock_get_service.return_value = mock_service

            await check_server_versions()

            cache = get_versions_cache()
            latest = cache.get_latest_versions()
            assert latest.stable_version == "1.21.3"
            assert latest.unstable_version == "1.22.0-pre.1"

    @pytest.mark.asyncio
    async def test_populates_full_version_lists(
        self, mock_versions: dict[str, dict[str, VersionInfo]]
    ) -> None:
        """Job should populate full version lists in cache (Story 13.1)."""
        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=make_version_getter(mock_versions)
            )
            mock_get_service.return_value = mock_service

            await check_server_versions()

            cache = get_versions_cache()

            # Check stable versions list
            stable_list = cache.get_versions("stable")
            assert len(stable_list) == 2
            stable_versions = {v["version"] for v in stable_list}
            assert stable_versions == {"1.21.3", "1.21.2"}

            # Check unstable versions list
            unstable_list = cache.get_versions("unstable")
            assert len(unstable_list) == 1
            assert unstable_list[0]["version"] == "1.22.0-pre.1"

    @pytest.mark.asyncio
    async def test_updates_cached_at_timestamp(
        self, mock_versions: dict[str, dict[str, VersionInfo]]
    ) -> None:
        """Job should update cached_at timestamp when populating cache."""
        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=make_version_getter(mock_versions)
            )
            mock_get_service.return_value = mock_service

            # Cache should be empty initially
            cache = get_versions_cache()
            assert cache.cached_at is None

            await check_server_versions()

            assert cache.cached_at is not None

    @pytest.mark.asyncio
    async def test_stable_error_preserves_unstable(
        self, mock_versions: dict[str, dict[str, VersionInfo]]
    ) -> None:
        """Stable API error should not affect unstable cache."""
        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()

            # Stable fails, unstable succeeds
            async def side_effect(channel: str):
                if channel == "stable":
                    raise httpx.HTTPStatusError(
                        "Error",
                        request=httpx.Request("GET", "http://test"),
                        response=httpx.Response(500),
                    )
                return mock_versions.get(channel, {})

            mock_service.get_available_versions = AsyncMock(side_effect=side_effect)
            mock_get_service.return_value = mock_service

            await check_server_versions()

            cache = get_versions_cache()
            latest = cache.get_latest_versions()

            # Stable should be None (not cached)
            assert latest.stable_version is None
            # Unstable should be populated
            assert latest.unstable_version == "1.22.0-pre.1"

            # Full version list checks
            assert cache.get_versions("stable") == []  # Not cached due to error
            assert len(cache.get_versions("unstable")) == 1

    @pytest.mark.asyncio
    async def test_unstable_error_preserves_stable(
        self, mock_versions: dict[str, dict[str, VersionInfo]]
    ) -> None:
        """Unstable API error should not affect stable cache."""
        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()

            # Unstable fails, stable succeeds
            async def side_effect(channel: str):
                if channel == "unstable":
                    raise httpx.HTTPStatusError(
                        "Error",
                        request=httpx.Request("GET", "http://test"),
                        response=httpx.Response(500),
                    )
                return mock_versions.get(channel, {})

            mock_service.get_available_versions = AsyncMock(side_effect=side_effect)
            mock_get_service.return_value = mock_service

            await check_server_versions()

            cache = get_versions_cache()
            latest = cache.get_latest_versions()

            # Stable should be populated
            assert latest.stable_version == "1.21.3"
            # Unstable should be None (not cached)
            assert latest.unstable_version is None

            # Full version list checks
            assert len(cache.get_versions("stable")) == 2
            assert cache.get_versions("unstable") == []  # Not cached due to error

    @pytest.mark.asyncio
    async def test_both_errors_preserve_stale_cache(
        self, mock_versions: dict[str, dict[str, VersionInfo]]
    ) -> None:
        """Both API errors should preserve stale cache data."""
        cache = get_versions_cache()
        # Pre-populate cache with stale data
        cache.set_latest_versions(stable="1.21.0", unstable="1.22.0-pre.0")
        cache.set_versions(
            "stable", [{"version": "1.21.0", "channel": "stable"}]
        )
        cache.set_versions(
            "unstable", [{"version": "1.22.0-pre.0", "channel": "unstable"}]
        )

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()

            # Both channels fail
            async def side_effect(channel: str):
                raise httpx.HTTPStatusError(
                    "Error",
                    request=httpx.Request("GET", "http://test"),
                    response=httpx.Response(500),
                )

            mock_service.get_available_versions = AsyncMock(side_effect=side_effect)
            mock_get_service.return_value = mock_service

            await check_server_versions()

            # Stale cache should be preserved
            latest = cache.get_latest_versions()
            assert latest.stable_version == "1.21.0"
            assert latest.unstable_version == "1.22.0-pre.0"

            # Full version lists should be preserved
            assert cache.get_versions("stable") == [
                {"version": "1.21.0", "channel": "stable"}
            ]
            assert cache.get_versions("unstable") == [
                {"version": "1.22.0-pre.0", "channel": "unstable"}
            ]
