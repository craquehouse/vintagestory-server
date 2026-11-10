"""Tests for applying all compatible updates (Story 14.4)."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vintagestory_api.models.mod_updates import StoredModRecord, StoredRelease
from vintagestory_api.models.mods import ModInfo
from vintagestory_api.services.mod_api import (
    DownloadError,
    ExternalApiError,
    ModApiClient,
)
from vintagestory_api.services.mod_updates import (
    ModUpdateAllInProgressError,
    ModUpdateService,
    ModUpdateStore,
)
from vintagestory_api.services.mods import (
    ModConfirmationRequiredError,
    ModVersionChangeFailedError,
    VersionChangeResult,
)

GAME = "1.22.7"


class FakeModSource:
    def __init__(self, cache_dir: Path, mods: list[tuple[str, str]]) -> None:
        self.api_client = ModApiClient(cache_dir=cache_dir)
        self.mods = mods

    def list_mods(self) -> list[ModInfo]:
        return [
            ModInfo(
                filename=f"{slug}_{version}.zip",
                slug=slug,
                version=version,
                enabled=True,
                installed_at=datetime(2026, 1, 1, tzinfo=UTC),
                name=slug.title(),
            )
            for slug, version in self.mods
        ]


def record(slug: str, *releases: tuple[str, str]) -> StoredModRecord:
    """Releases as (version, tag), newest first."""
    return StoredModRecord(
        checked_at=datetime(2026, 11, 9, tzinfo=UTC),
        found=True,
        releases=[StoredRelease(modversion=v, modidstr=slug, tags=[tag]) for v, tag in releases],
    )


def make_service(tmp_path: Path, mods: list[tuple[str, str]]) -> ModUpdateService:
    return ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=FakeModSource(tmp_path / "cache", mods),
        game_version_provider=lambda: GAME,
    )


def changed(slug: str, previous: str, version: str, pending: bool = False) -> VersionChangeResult:
    return VersionChangeResult(
        slug=slug,
        previous_version=previous,
        version=version,
        filename=f"{slug}_{version}.zip",
        compatibility="compatible",
        changed=True,
        pending_restart=pending,
    )


@pytest.fixture
def service(tmp_path: Path) -> ModUpdateService:
    svc = make_service(
        tmp_path,
        [("alpha", "1.0.0"), ("beta", "2.0.0"), ("gamma", "3.0.0"), ("delta", "4.0.0")],
    )
    svc.store.set("alpha", record("alpha", ("1.1.0", GAME), ("1.0.0", GAME)))
    svc.store.set("beta", record("beta", ("2.1.0", "1.22.0"), ("2.0.0", GAME)))  # not verified
    svc.store.set("gamma", record("gamma", ("3.0.0", GAME)))  # up to date
    svc.store.set("delta", record("delta", ("4.1.0", GAME), ("4.0.0", GAME)))
    return svc


class TestApplyAll:
    @pytest.mark.asyncio
    async def test_updates_compatible_and_skips_not_verified(
        self, service: ModUpdateService
    ) -> None:
        calls: list[tuple[str, str]] = []

        async def change_version(slug: str, version: str) -> VersionChangeResult:
            calls.append((slug, version))
            previous = {"alpha": "1.0.0", "delta": "4.0.0"}[slug]
            return changed(slug, previous, version)

        summary = await service.apply_all(change_version)

        assert calls == [("alpha", "1.1.0"), ("delta", "4.1.0")]
        assert [(r.slug, r.outcome, r.from_version, r.to_version) for r in summary.results] == [
            ("alpha", "updated", "1.0.0", "1.1.0"),
            ("beta", "skipped", "2.0.0", "2.1.0"),
            ("delta", "updated", "4.0.0", "4.1.0"),
        ]
        beta = summary.results[1]
        assert beta.reasons == ["not_verified"]
        assert beta.name == "Beta"
        assert (summary.updated, summary.skipped, summary.failed) == (2, 1, 0)
        assert summary.pending_restart is False

    @pytest.mark.asyncio
    async def test_reports_pending_restart_when_any_change_set_it(
        self, service: ModUpdateService
    ) -> None:
        async def change_version(slug: str, version: str) -> VersionChangeResult:
            return changed(slug, "x", version, pending=slug == "delta")

        summary = await service.apply_all(change_version)

        assert summary.pending_restart is True

    @pytest.mark.asyncio
    async def test_confirmation_required_is_skipped_not_confirmed(
        self, service: ModUpdateService
    ) -> None:
        async def change_version(slug: str, version: str) -> VersionChangeResult:
            if slug == "alpha":
                raise ModConfirmationRequiredError(slug, version, ["not_verified"], "not_verified")
            return changed(slug, "4.0.0", version)

        summary = await service.apply_all(change_version)

        alpha = summary.results[0]
        assert (alpha.outcome, alpha.reasons, alpha.error) == ("skipped", ["not_verified"], None)
        assert summary.results[2].outcome == "updated"
        assert (summary.updated, summary.skipped, summary.failed) == (1, 2, 0)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error",
        [
            ModVersionChangeFailedError("alpha", "disk full"),
            DownloadError("alpha", "connection reset"),
            ExternalApiError("mod database unavailable"),
            OSError("read-only file system"),
            ValueError("state could not be serialized"),
            TypeError("unexpected release data"),
        ],
    )
    async def test_one_failure_does_not_stop_the_rest(
        self, service: ModUpdateService, error: Exception
    ) -> None:
        async def change_version(slug: str, version: str) -> VersionChangeResult:
            if slug == "alpha":
                raise error
            return changed(slug, "4.0.0", version)

        summary = await service.apply_all(change_version)

        alpha = summary.results[0]
        assert alpha.outcome == "failed"
        assert alpha.error == str(error)
        assert summary.results[2].outcome == "updated"
        assert (summary.updated, summary.skipped, summary.failed) == (1, 1, 1)

    @pytest.mark.asyncio
    async def test_nothing_to_update(self, tmp_path: Path) -> None:
        service = make_service(tmp_path, [("gamma", "3.0.0")])
        service.store.set("gamma", record("gamma", ("3.0.0", GAME)))

        async def change_version(slug: str, version: str) -> VersionChangeResult:
            raise AssertionError("not called")

        summary = await service.apply_all(change_version)

        assert summary.results == []
        assert (summary.updated, summary.skipped, summary.failed) == (0, 0, 0)

    @pytest.mark.asyncio
    async def test_overlapping_run_is_rejected(self, service: ModUpdateService) -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        async def change_version(slug: str, version: str) -> VersionChangeResult:
            started.set()
            await release.wait()
            return changed(slug, "x", version)

        first = asyncio.create_task(service.apply_all(change_version))
        await started.wait()

        with pytest.raises(ModUpdateAllInProgressError):
            await service.apply_all(change_version)

        release.set()
        summary = await first
        assert summary.updated == 2
