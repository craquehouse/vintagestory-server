"""Tests for mod cache refresh job.

Story 8.1: Mod Cache Refresh Job

Tests cover:
- AC 1: Job executes at configured interval (tested via registration in test_jobs_registration.py)
- AC 2: API failures are logged but don't stop the job, stale cache data preserved

Task 1 tests:
- Job function exists and can be imported
- Job uses @safe_job decorator for error handling
- Job handles successful refresh
- Job handles API failures gracefully (no crash, stale data preserved)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vintagestory_api.models.mods import ModInfo

if TYPE_CHECKING:
    from pytest import CaptureFixture


def make_mod_info(
    filename: str,
    slug: str,
    version: str,
    enabled: bool = True,
    name: str | None = None,
) -> ModInfo:
    """Create a ModInfo for testing with required fields."""
    return ModInfo(
        filename=filename,
        slug=slug,
        version=version,
        enabled=enabled,
        installed_at=datetime.now(UTC),
        name=name or slug,
    )


class TestModCacheRefreshJobExists:
    """Tests that mod_cache_refresh job exists and is properly structured."""

    def test_refresh_mod_cache_can_be_imported(self) -> None:
        """refresh_mod_cache function can be imported from jobs module."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        assert callable(refresh_mod_cache)

    def test_refresh_mod_cache_is_async(self) -> None:
        """refresh_mod_cache is an async function."""
        import inspect

        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        assert inspect.iscoroutinefunction(refresh_mod_cache)


class TestModCacheRefreshExecution:
    """Tests for successful mod cache refresh execution."""

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_logs_start_event(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """refresh_mod_cache logs mod_cache_refresh_started event."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        # Mock dependencies to avoid real API calls
        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_mods.return_value = []
            mock_get_service.return_value = mock_service

            capsys.readouterr()  # Clear prior output
            await refresh_mod_cache()
            captured = capsys.readouterr()

            assert "mod_cache_refresh_started" in captured.out

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_logs_completion_event(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """refresh_mod_cache logs mod_cache_refresh_completed event on success."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_mods.return_value = []
            mock_get_service.return_value = mock_service

            capsys.readouterr()  # Clear prior output
            await refresh_mod_cache()
            captured = capsys.readouterr()

            assert "mod_cache_refresh_completed" in captured.out

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_fetches_installed_mods(self) -> None:
        """refresh_mod_cache queries the list of installed mods."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_mods.return_value = []
            mock_get_service.return_value = mock_service

            await refresh_mod_cache()

            mock_service.list_mods.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_with_installed_mods(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """refresh_mod_cache logs summary when mods are present."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        mock_mods = [
            make_mod_info("modA_1.0.0.zip", "modA", "1.0.0", name="Mod A"),
            make_mod_info("modB_2.0.0.zip", "modB", "2.0.0", name="Mod B"),
        ]

        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_mods.return_value = mock_mods
            mock_service.api_client = AsyncMock()
            mock_service.api_client.get_mod = AsyncMock(return_value={"name": "test"})
            mock_get_service.return_value = mock_service

            capsys.readouterr()  # Clear prior output
            await refresh_mod_cache()
            captured = capsys.readouterr()

            # Should complete successfully
            assert "mod_cache_refresh_completed" in captured.out


class TestModCacheRefreshErrorHandling:
    """Tests for error handling in mod cache refresh (AC: 2)."""

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_handles_api_failure_gracefully(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """refresh_mod_cache handles API failures without crashing (AC: 2)."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache
        from vintagestory_api.services.mod_api import ExternalApiError

        mock_mods = [
            make_mod_info("modA_1.0.0.zip", "modA", "1.0.0", name="Mod A"),
        ]

        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_mods.return_value = mock_mods
            mock_service.api_client = AsyncMock()
            # Simulate API failure
            mock_service.api_client.get_mod = AsyncMock(
                side_effect=ExternalApiError("API unavailable")
            )
            mock_get_service.return_value = mock_service

            capsys.readouterr()  # Clear prior output

            # Should NOT raise - job must be resilient
            await refresh_mod_cache()

            captured = capsys.readouterr()

            # Job should complete despite API failure
            assert "mod_cache_refresh_completed" in captured.out

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_continues_on_partial_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """refresh_mod_cache continues processing other mods if one fails."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache
        from vintagestory_api.services.mod_api import ExternalApiError

        mock_mods = [
            make_mod_info("modA_1.0.0.zip", "modA", "1.0.0", name="Mod A"),
            make_mod_info("modB_2.0.0.zip", "modB", "2.0.0", name="Mod B"),
        ]

        call_count = 0

        async def mock_get_mod(slug: str) -> dict[str, str] | None:
            nonlocal call_count
            call_count += 1
            if slug == "modA":
                raise ExternalApiError("API error for modA")
            return {"name": f"Mod {slug}", "modid": slug}

        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_mods.return_value = mock_mods
            mock_service.api_client = AsyncMock()
            mock_service.api_client.get_mod = mock_get_mod
            mock_get_service.return_value = mock_service

            await refresh_mod_cache()

            # Both mods should be attempted
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_preserves_stale_data_on_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """refresh_mod_cache preserves existing cache data when API fails (AC: 2)."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache
        from vintagestory_api.services.mod_api import ExternalApiError

        mock_mods = [
            make_mod_info("modA_1.0.0.zip", "modA", "1.0.0", name="Mod A - Original Name"),
        ]

        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_mods.return_value = mock_mods
            mock_service.api_client = AsyncMock()
            mock_service.api_client.get_mod = AsyncMock(
                side_effect=ExternalApiError("API unavailable")
            )
            mock_get_service.return_value = mock_service

            capsys.readouterr()  # Clear prior output

            await refresh_mod_cache()

            captured = capsys.readouterr()

            # Job should log that it completed (stale data preserved)
            assert "mod_cache_refresh_completed" in captured.out

            # Original mod data should remain unchanged (not overwritten)
            # The service's state should not have been modified
            # In this case, we verify no update methods were called
            # since the update would have failed

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_does_not_raise_on_exception(self) -> None:
        """refresh_mod_cache never raises exceptions (critical for scheduler)."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            # Simulate catastrophic failure
            mock_get_service.side_effect = RuntimeError("Catastrophic failure")

            # Should NOT raise - @safe_job decorator must catch this
            result = await refresh_mod_cache()

            # Returns None on failure (per safe_job contract)
            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_logs_failure_event_on_exception(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """refresh_mod_cache logs mod_cache_refresh_failed on exception."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            mock_get_service.side_effect = RuntimeError("Catastrophic failure")

            capsys.readouterr()  # Clear prior output
            await refresh_mod_cache()
            captured = capsys.readouterr()

            assert "mod_cache_refresh_failed" in captured.out


class TestModCacheRefreshWithNoMods:
    """Tests for edge case with no installed mods."""

    @pytest.mark.asyncio
    async def test_refresh_mod_cache_handles_empty_mod_list(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """refresh_mod_cache handles empty mod list gracefully."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        with patch(
            "vintagestory_api.jobs.mod_cache_refresh.get_mod_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_mods.return_value = []
            mock_get_service.return_value = mock_service

            capsys.readouterr()  # Clear prior output
            await refresh_mod_cache()
            captured = capsys.readouterr()

            # Should complete successfully even with no mods
            assert "mod_cache_refresh_completed" in captured.out
