"""Tests for the mod cache refresh job.

Story 8.1: Mod Cache Refresh Job (runs on `mod_list_refresh_interval`; registration and
interval 0 are tested in test_jobs_registration.py).
Story 14.5 (ADR-5): the job records update status by running the mod update check, so
scheduled and on-demand checks share one code path and one set of mod database requests.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import respx
from httpx import Response

from vintagestory_api.models.mods import ModInfo
from vintagestory_api.services.mod_api import ModApiClient
from vintagestory_api.services.mod_updates import (
    ModUpdateCheckInProgressError,
    ModUpdateService,
    ModUpdateStore,
)

if TYPE_CHECKING:
    from pytest import CaptureFixture

FIXTURES = Path(__file__).parent.parent / "fixtures" / "moddb"
SERVICE = "vintagestory_api.jobs.mod_cache_refresh.get_mod_update_service"


class FakeModSource:
    def __init__(self, cache_dir: Path, mods: list[tuple[str, str]]) -> None:
        self.api_client = ModApiClient(cache_dir=cache_dir)
        self.mods = mods

    def list_mods(self) -> list[ModInfo]:
        return [
            ModInfo(
                filename=f"{slug}.zip",
                slug=slug,
                version=version,
                enabled=True,
                installed_at=datetime(2026, 1, 1, tzinfo=UTC),
                name=slug,
            )
            for slug, version in self.mods
        ]


@pytest.fixture
def service(tmp_path: Path) -> Iterator[ModUpdateService]:
    svc = ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=FakeModSource(tmp_path / "cache", [("carryon", "1.14.1"), ("broken", "1.0.0")]),
        game_version_provider=lambda: "1.22.7",
    )
    with patch(SERVICE, return_value=svc):
        yield svc


class TestModCacheRefreshJobExists:
    def test_refresh_mod_cache_is_async(self) -> None:
        import inspect

        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        assert inspect.iscoroutinefunction(refresh_mod_cache)


class TestScheduledUpdateCheck:
    @respx.mock
    @pytest.mark.asyncio
    async def test_records_update_status_for_each_installed_mod(
        self, service: ModUpdateService, capsys: CaptureFixture[str]
    ) -> None:
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        carryon = json.loads((FIXTURES / "mod_carryon.json").read_text())
        respx.get("https://mods.vintagestory.at/api/mod/carryon").mock(
            return_value=Response(200, json=carryon)
        )
        respx.get("https://mods.vintagestory.at/api/mod/broken").mock(
            return_value=Response(500, content=b"")
        )

        capsys.readouterr()
        await refresh_mod_cache()
        out = capsys.readouterr().out

        status = {item.slug: item for item in service.get_status()}
        assert status["carryon"].status == "update_available"
        assert status["carryon"].offered_version == "1.14.3"
        # One failed lookup does not affect the others, and is recorded on that mod
        assert status["broken"].status == "unknown"
        assert status["broken"].error
        assert "mod_cache_refresh_summary" in out
        assert "mod_cache_refresh_completed" in out

    @pytest.mark.asyncio
    async def test_skips_when_a_check_is_already_running(
        self,
        service: ModUpdateService,
        monkeypatch: pytest.MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        async def busy() -> None:
            raise ModUpdateCheckInProgressError()

        monkeypatch.setattr(service, "check", busy)

        capsys.readouterr()
        await refresh_mod_cache()
        out = capsys.readouterr().out

        assert "mod_cache_refresh_skipped" in out
        assert "mod_cache_refresh_completed" in out

    @pytest.mark.asyncio
    async def test_no_installed_mods(
        self, tmp_path: Path, capsys: CaptureFixture[str]
    ) -> None:
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        svc = ModUpdateService(
            store=ModUpdateStore(tmp_path / "state"),
            mod_source=FakeModSource(tmp_path / "cache", []),
            game_version_provider=lambda: "1.22.7",
        )
        with patch(SERVICE, return_value=svc):
            capsys.readouterr()
            await refresh_mod_cache()
            out = capsys.readouterr().out

        assert svc.get_status() == []
        assert "mod_cache_refresh_completed" in out


class TestModCacheRefreshErrorHandling:
    @pytest.mark.asyncio
    async def test_does_not_raise_and_logs_failure(self, capsys: CaptureFixture[str]) -> None:
        """The scheduler must never see an exception (safe_job contract)."""
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache

        with patch(SERVICE, side_effect=RuntimeError("Catastrophic failure")):
            capsys.readouterr()
            result = await refresh_mod_cache()
            out = capsys.readouterr().out

        assert result is None
        assert "mod_cache_refresh_failed" in out
