"""Tests for server versions check job.

Story 8.2: Server Versions Check Job

Tests cover:
- AC 1: Job executes at configured interval (tested via registration in test_jobs_registration.py)
- AC 2: New versions are logged and made available via cache
- AC 3: API failures are logged but don't stop the job, stale cache data preserved

Task 2 tests:
- Job function exists and can be imported
- Job uses @safe_job decorator for error handling
- Job successfully fetches and caches versions
- Job detects and logs new versions
- Job handles API failures gracefully (no crash, stale data preserved)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from vintagestory_api.models.server import VersionInfo
from vintagestory_api.services.versions_cache import reset_versions_cache

if TYPE_CHECKING:
    from pytest import CaptureFixture


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the versions cache before and after each test."""
    reset_versions_cache()
    yield
    reset_versions_cache()


def make_version_info(
    version: str,
    channel: str = "stable",
    is_latest: bool = False,
) -> VersionInfo:
    """Create a VersionInfo for testing."""
    return VersionInfo(
        version=version,
        filename=f"vs_server_linux-x64_{version}.tar.gz",
        filesize="50000000",
        md5="abc123",
        cdn_url=f"https://cdn.vintagestory.at/gamefiles/{channel}/vs_server_linux-x64_{version}.tar.gz",
        local_url=f"https://vintagestory.at/gamefiles/{channel}/vs_server_linux-x64_{version}.tar.gz",
        is_latest=is_latest,
        channel=channel,
    )


class TestServerVersionsJobExists:
    """Tests that server_versions_check job exists and is properly structured."""

    def test_check_server_versions_can_be_imported(self) -> None:
        """check_server_versions function can be imported from jobs module."""
        from vintagestory_api.jobs.server_versions import check_server_versions

        assert callable(check_server_versions)

    def test_check_server_versions_is_async(self) -> None:
        """check_server_versions is an async function."""
        import inspect

        from vintagestory_api.jobs.server_versions import check_server_versions

        assert inspect.iscoroutinefunction(check_server_versions)


class TestServerVersionsExecution:
    """Tests for successful server versions check execution."""

    @pytest.mark.asyncio
    async def test_check_server_versions_logs_start_event(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions logs server_versions_check_started event."""
        from vintagestory_api.jobs.server_versions import check_server_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = AsyncMock(return_value={})
            mock_get_service.return_value = mock_service

            capsys.readouterr()  # Clear prior output
            await check_server_versions()
            captured = capsys.readouterr()

            assert "server_versions_check_started" in captured.out

    @pytest.mark.asyncio
    async def test_check_server_versions_logs_completion_event(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions logs server_versions_check_completed event on success."""
        from vintagestory_api.jobs.server_versions import check_server_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = AsyncMock(return_value={})
            mock_get_service.return_value = mock_service

            capsys.readouterr()  # Clear prior output
            await check_server_versions()
            captured = capsys.readouterr()

            assert "server_versions_check_completed" in captured.out

    @pytest.mark.asyncio
    async def test_check_server_versions_fetches_both_channels(self) -> None:
        """check_server_versions queries both stable and unstable channels."""
        from vintagestory_api.jobs.server_versions import check_server_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = AsyncMock(return_value={})
            mock_get_service.return_value = mock_service

            await check_server_versions()

            # Should call with both stable and unstable
            calls = mock_service.get_available_versions.call_args_list
            channels = [call[0][0] for call in calls]
            assert "stable" in channels
            assert "unstable" in channels

    @pytest.mark.asyncio
    async def test_check_server_versions_caches_latest_versions(self) -> None:
        """check_server_versions updates cache with latest versions."""
        from vintagestory_api.jobs.server_versions import check_server_versions
        from vintagestory_api.services.versions_cache import get_versions_cache

        stable_versions = {
            "1.21.2": make_version_info("1.21.2", "stable", is_latest=False),
            "1.21.3": make_version_info("1.21.3", "stable", is_latest=True),
        }
        unstable_versions = {
            "1.22.0-pre.1": make_version_info("1.22.0-pre.1", "unstable", is_latest=True),
        }

        async def mock_get_versions(channel: str) -> dict[str, VersionInfo]:
            if channel == "stable":
                return stable_versions
            return unstable_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = mock_get_versions
            mock_get_service.return_value = mock_service

            await check_server_versions()

            cache = get_versions_cache()
            versions = cache.get_latest_versions()

            assert versions.stable_version == "1.21.3"
            assert versions.unstable_version == "1.22.0-pre.1"
            assert versions.last_checked is not None


class TestServerVersionsNewVersionDetection:
    """Tests for new version detection (AC: 2)."""

    @pytest.mark.asyncio
    async def test_check_server_versions_logs_new_stable_version(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions logs when new stable version is detected."""
        from vintagestory_api.jobs.server_versions import check_server_versions
        from vintagestory_api.services.versions_cache import get_versions_cache

        # Pre-populate cache with old version
        cache = get_versions_cache()
        cache.set_latest_versions(stable="1.21.2")

        stable_versions = {
            "1.21.3": make_version_info("1.21.3", "stable", is_latest=True),
        }

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = AsyncMock(side_effect=[
                stable_versions,  # stable call
                {},  # unstable call
            ])
            mock_get_service.return_value = mock_service

            capsys.readouterr()
            await check_server_versions()
            captured = capsys.readouterr()

            assert "new_stable_version_detected" in captured.out
            assert "1.21.2" in captured.out  # old version
            assert "1.21.3" in captured.out  # new version

    @pytest.mark.asyncio
    async def test_check_server_versions_logs_new_unstable_version(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions logs when new unstable version is detected."""
        from vintagestory_api.jobs.server_versions import check_server_versions
        from vintagestory_api.services.versions_cache import get_versions_cache

        # Pre-populate cache with old version
        cache = get_versions_cache()
        cache.set_latest_versions(unstable="1.22.0-pre.1")

        unstable_versions = {
            "1.22.0-pre.2": make_version_info("1.22.0-pre.2", "unstable", is_latest=True),
        }

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = AsyncMock(side_effect=[
                {},  # stable call
                unstable_versions,  # unstable call
            ])
            mock_get_service.return_value = mock_service

            capsys.readouterr()
            await check_server_versions()
            captured = capsys.readouterr()

            assert "new_unstable_version_detected" in captured.out
            assert "1.22.0-pre.1" in captured.out  # old version
            assert "1.22.0-pre.2" in captured.out  # new version

    @pytest.mark.asyncio
    async def test_check_server_versions_no_log_when_version_unchanged(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions does not log new version when unchanged."""
        from vintagestory_api.jobs.server_versions import check_server_versions
        from vintagestory_api.services.versions_cache import get_versions_cache

        # Pre-populate cache with current version
        cache = get_versions_cache()
        cache.set_latest_versions(stable="1.21.3")

        stable_versions = {
            "1.21.3": make_version_info("1.21.3", "stable", is_latest=True),
        }

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = AsyncMock(side_effect=[
                stable_versions,
                {},
            ])
            mock_get_service.return_value = mock_service

            capsys.readouterr()
            await check_server_versions()
            captured = capsys.readouterr()

            assert "new_stable_version_detected" not in captured.out


class TestServerVersionsErrorHandling:
    """Tests for error handling in server versions check (AC: 3)."""

    @pytest.mark.asyncio
    async def test_check_server_versions_handles_stable_api_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions handles stable API failure gracefully (AC: 3)."""
        from vintagestory_api.jobs.server_versions import check_server_versions

        unstable_versions = {
            "1.22.0-pre.1": make_version_info("1.22.0-pre.1", "unstable", is_latest=True),
        }

        async def mock_get_versions(channel: str) -> dict[str, VersionInfo]:
            if channel == "stable":
                raise httpx.HTTPError("Stable API unavailable")
            return unstable_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = mock_get_versions
            mock_get_service.return_value = mock_service

            capsys.readouterr()
            await check_server_versions()
            captured = capsys.readouterr()

            # Job should complete despite stable API failure
            assert "server_versions_check_completed" in captured.out
            # Should log the API error
            assert "server_versions_stable_api_error" in captured.out

    @pytest.mark.asyncio
    async def test_check_server_versions_handles_unstable_api_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions handles unstable API failure gracefully (AC: 3)."""
        from vintagestory_api.jobs.server_versions import check_server_versions

        stable_versions = {
            "1.21.3": make_version_info("1.21.3", "stable", is_latest=True),
        }

        async def mock_get_versions(channel: str) -> dict[str, VersionInfo]:
            if channel == "unstable":
                raise httpx.HTTPError("Unstable API unavailable")
            return stable_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = mock_get_versions
            mock_get_service.return_value = mock_service

            capsys.readouterr()
            await check_server_versions()
            captured = capsys.readouterr()

            # Job should complete despite unstable API failure
            assert "server_versions_check_completed" in captured.out
            # Should log the API error
            assert "server_versions_unstable_api_error" in captured.out

    @pytest.mark.asyncio
    async def test_check_server_versions_preserves_stale_stable_on_failure(
        self,
    ) -> None:
        """check_server_versions preserves stale stable version on API failure (AC: 3)."""
        from vintagestory_api.jobs.server_versions import check_server_versions
        from vintagestory_api.services.versions_cache import get_versions_cache

        # Pre-populate cache with stale data
        cache = get_versions_cache()
        cache.set_latest_versions(stable="1.21.2", unstable="1.22.0-pre.1")

        unstable_versions = {
            "1.22.0-pre.2": make_version_info("1.22.0-pre.2", "unstable", is_latest=True),
        }

        async def mock_get_versions(channel: str) -> dict[str, VersionInfo]:
            if channel == "stable":
                raise httpx.HTTPError("Stable API unavailable")
            return unstable_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = mock_get_versions
            mock_get_service.return_value = mock_service

            await check_server_versions()

            versions = cache.get_latest_versions()
            # Stable should be preserved (stale)
            assert versions.stable_version == "1.21.2"
            # Unstable should be updated
            assert versions.unstable_version == "1.22.0-pre.2"

    @pytest.mark.asyncio
    async def test_check_server_versions_preserves_stale_unstable_on_failure(
        self,
    ) -> None:
        """check_server_versions preserves stale unstable version on API failure (AC: 3)."""
        from vintagestory_api.jobs.server_versions import check_server_versions
        from vintagestory_api.services.versions_cache import get_versions_cache

        # Pre-populate cache with stale data
        cache = get_versions_cache()
        cache.set_latest_versions(stable="1.21.2", unstable="1.22.0-pre.1")

        stable_versions = {
            "1.21.3": make_version_info("1.21.3", "stable", is_latest=True),
        }

        async def mock_get_versions(channel: str) -> dict[str, VersionInfo]:
            if channel == "unstable":
                raise httpx.HTTPError("Unstable API unavailable")
            return stable_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = mock_get_versions
            mock_get_service.return_value = mock_service

            await check_server_versions()

            versions = cache.get_latest_versions()
            # Stable should be updated
            assert versions.stable_version == "1.21.3"
            # Unstable should be preserved (stale)
            assert versions.unstable_version == "1.22.0-pre.1"

    @pytest.mark.asyncio
    async def test_check_server_versions_does_not_raise_on_exception(self) -> None:
        """check_server_versions never raises exceptions (critical for scheduler)."""
        from vintagestory_api.jobs.server_versions import check_server_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            # Simulate catastrophic failure
            mock_get_service.side_effect = RuntimeError("Catastrophic failure")

            # Should NOT raise - @safe_job decorator must catch this
            result = await check_server_versions()

            # Returns None on failure (per safe_job contract)
            assert result is None

    @pytest.mark.asyncio
    async def test_check_server_versions_logs_failure_event_on_exception(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions logs server_versions_check_failed on exception."""
        from vintagestory_api.jobs.server_versions import check_server_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_get_service.side_effect = RuntimeError("Catastrophic failure")

            capsys.readouterr()  # Clear prior output
            await check_server_versions()
            captured = capsys.readouterr()

            assert "server_versions_check_failed" in captured.out


class TestServerVersionsWithNoLatestVersion:
    """Tests for edge case when no version is marked as latest."""

    @pytest.mark.asyncio
    async def test_check_server_versions_handles_no_latest_stable(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions handles case when no stable version is marked as latest."""
        from vintagestory_api.jobs.server_versions import check_server_versions
        from vintagestory_api.services.versions_cache import get_versions_cache

        # No version marked as latest
        stable_versions = {
            "1.21.2": make_version_info("1.21.2", "stable", is_latest=False),
            "1.21.3": make_version_info("1.21.3", "stable", is_latest=False),
        }
        unstable_versions = {
            "1.22.0-pre.1": make_version_info("1.22.0-pre.1", "unstable", is_latest=True),
        }

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = AsyncMock(side_effect=[
                stable_versions,
                unstable_versions,
            ])
            mock_get_service.return_value = mock_service

            capsys.readouterr()
            await check_server_versions()
            captured = capsys.readouterr()

            # Should complete successfully
            assert "server_versions_check_completed" in captured.out

            # Unstable should still be cached
            cache = get_versions_cache()
            versions = cache.get_latest_versions()
            assert versions.unstable_version == "1.22.0-pre.1"

    @pytest.mark.asyncio
    async def test_check_server_versions_handles_empty_versions(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """check_server_versions handles empty version lists gracefully."""
        from vintagestory_api.jobs.server_versions import check_server_versions

        with patch(
            "vintagestory_api.jobs.server_versions.get_server_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_versions = AsyncMock(return_value={})
            mock_get_service.return_value = mock_service

            capsys.readouterr()
            await check_server_versions()
            captured = capsys.readouterr()

            # Should complete successfully even with empty versions
            assert "server_versions_check_completed" in captured.out
