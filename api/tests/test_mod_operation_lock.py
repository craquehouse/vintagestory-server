"""Operations on the same mod never run at the same time (Story 17.3, Epic 17 ADR-3).

Every test holds the first operation inside its critical section with a gate on the
download, acts while it is suspended, then releases it. No timing: `started` proves the
first operation is inside its lock, `release` lets it continue.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest
import respx
from httpx import Response
from test_mod_version_change import (
    DOWNLOAD_URL,
    MOD_URL,
    install_existing,
    make_service,
    mod_zip_bytes,
)

from vintagestory_api.services.mod_api import ModNotFoundError as ApiModNotFoundError
from vintagestory_api.services.mods import (
    ModNotFoundError,
    ModOperationInProgressError,
    ModService,
    ModValidationError,
    ModVersionChangeFailedError,
)


def entry(modid: str, file_new: str, file_old: str, fileids: tuple[int, int]) -> dict[str, Any]:
    """A mod database entry with releases 1.1.0 (newest) and 1.0.0 of one mod ID."""
    new_id, old_id = fileids
    return {
        "statuscode": "200",
        "mod": {
            "assetid": 1,
            "releases": [
                {"modversion": "1.1.0", "modidstr": modid, "fileid": new_id,
                 "filename": file_new, "tags": ["1.22.7"]},
                {"modversion": "1.0.0", "modidstr": modid, "fileid": old_id,
                 "filename": file_old, "tags": ["1.22.7"]},
            ],
        },
    }


def mock_mod(
    modid: str,
    fileids: tuple[int, int] = (11, 10),
    *,
    archive_version: str | None = None,
) -> None:
    """Lookup and both downloads for `modid`; files are named `<modid>-<version>.zip`."""
    respx.get(MOD_URL.format(modid)).mock(
        return_value=Response(
            200, json=entry(modid, f"{modid}-1.1.0.zip", f"{modid}-1.0.0.zip", fileids)
        )
    )
    for fileid, version in zip(fileids, ("1.1.0", "1.0.0"), strict=True):
        content = mod_zip_bytes(
            {"modid": modid, "name": modid, "version": archive_version or version}
        )
        respx.get(DOWNLOAD_URL, params={"fileid": str(fileid)}).mock(
            return_value=Response(200, content=content)
        )


def gate_download(
    service: ModService, monkeypatch: pytest.MonkeyPatch, slug: str | None = None
) -> tuple[asyncio.Event, asyncio.Event]:
    """Hold downloads (of `slug` only, if given) until `release` is set."""
    started, release = asyncio.Event(), asyncio.Event()
    original = service.api_client.download_release_file

    async def held(mod_slug: str, fileid: int, filename: str) -> Path:
        if slug is None or mod_slug == slug:
            started.set()
            await release.wait()
        return await original(mod_slug, fileid, filename)

    monkeypatch.setattr(service.api_client, "download_release_file", held)
    return started, release


def mod_files(service: ModService) -> list[str]:
    return sorted(p.name for p in service.state_manager.mods_dir.iterdir())


def state_of(service: ModService, slug: str) -> tuple[str, str, bool] | None:
    state = service.state_manager.get_mod_by_slug(slug)
    return None if state is None else (state.filename, state.version, state.enabled)


class TestVersionChangeHoldsTheLock:
    @respx.mock
    @pytest.mark.asyncio
    async def test_v1_remove_is_refused_and_the_change_completes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        mock_mod("demo")
        started, release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()
        assert service.busy_mod_ids == frozenset({"demo"})
        with pytest.raises(ModOperationInProgressError) as raised:
            service.remove_mod("demo")
        assert raised.value.slug == "demo"
        assert mod_files(service) == ["demo-1.0.0.zip"]
        release.set()
        result = await first

        assert result.version == "1.1.0"
        assert mod_files(service) == ["demo-1.1.0.zip"]
        assert state_of(service, "demo") == ("demo-1.1.0.zip", "1.1.0", True)
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_v2_disable_is_refused_and_the_file_is_not_renamed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        mock_mod("demo")
        started, release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()
        with pytest.raises(ModOperationInProgressError):
            service.disable_mod("demo")
        assert mod_files(service) == ["demo-1.0.0.zip"]
        assert state_of(service, "demo") == ("demo-1.0.0.zip", "1.0.0", True)
        release.set()
        await first

        assert mod_files(service) == ["demo-1.1.0.zip"]
        assert state_of(service, "demo") == ("demo-1.1.0.zip", "1.1.0", True)
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_v3_enable_of_a_disabled_mod_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip", enabled=False)
        mock_mod("demo")
        started, release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()
        with pytest.raises(ModOperationInProgressError):
            service.enable_mod("demo")
        assert mod_files(service) == ["demo-1.0.0.zip.disabled"]
        release.set()
        await first

        assert mod_files(service) == ["demo-1.1.0.zip.disabled"]
        assert state_of(service, "demo") == ("demo-1.1.0.zip.disabled", "1.1.0", False)
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_v4_second_change_of_the_same_mod_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        mock_mod("demo")
        started, release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()
        lookups = respx.get(MOD_URL.format("demo")).calls.call_count
        with pytest.raises(ModOperationInProgressError):
            await service.change_version("demo", "1.1.0")
        assert respx.get(MOD_URL.format("demo")).calls.call_count == lookups
        release.set()
        await first

        assert mod_files(service) == ["demo-1.1.0.zip"]
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_operations_differing_only_in_case_share_the_lock(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        mock_mod("demo")
        started, release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()
        with pytest.raises(ModOperationInProgressError) as raised:
            service.disable_mod("DEMO")
        assert raised.value.slug == "DEMO"
        with pytest.raises(ModOperationInProgressError):
            await service.change_version("Demo", "1.1.0")
        release.set()
        await first

        assert state_of(service, "demo") == ("demo-1.1.0.zip", "1.1.0", True)
        assert service.busy_mod_ids == frozenset()

    @pytest.mark.asyncio
    async def test_busy_mod_that_is_not_installed_is_refused_not_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Enable, disable and remove check the lock before the state lookup."""
        service = make_service(tmp_path)
        started, release = asyncio.Event(), asyncio.Event()

        async def held_lookup(slug: str) -> None:
            started.set()
            await release.wait()

        monkeypatch.setattr(service.api_client, "get_mod", held_lookup)
        # The lock is held during the lookup too. "Demo" shares demo's lock key but is
        # not an installed mod ID (state lookups are exact).
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        first = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()

        for operation in (service.enable_mod, service.disable_mod, service.remove_mod):
            with pytest.raises(ModOperationInProgressError):
                operation("Demo")
        release.set()
        with pytest.raises(ApiModNotFoundError):
            await first
        assert service.busy_mod_ids == frozenset()
        with pytest.raises(ModNotFoundError):
            service.enable_mod("Demo")

    @respx.mock
    @pytest.mark.asyncio
    async def test_v6_other_mods_proceed_while_one_is_held(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        install_existing(service, "other", "1.0.0", "other-1.0.0.zip")
        install_existing(service, "third", "1.0.0", "third-1.0.0.zip")
        mock_mod("demo")
        mock_mod("third", (31, 30))
        started, release = gate_download(service, monkeypatch, slug="demo")

        first = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()
        assert service.disable_mod("other").enabled is False
        assert service.enable_mod("other").enabled is True
        service.remove_mod("other")
        changed = await service.change_version("third", "1.1.0")
        assert changed.version == "1.1.0"
        assert service.busy_mod_ids == frozenset({"demo"})
        release.set()
        await first

        assert mod_files(service) == ["demo-1.1.0.zip", "third-1.1.0.zip"]
        assert state_of(service, "other") is None
        assert service.busy_mod_ids == frozenset()


class TestLockIsReleased:
    @respx.mock
    @pytest.mark.asyncio
    async def test_v7_after_a_validation_failure(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        mock_mod("demo", archive_version="9.9.9")

        with pytest.raises(ModValidationError):
            await service.change_version("demo", "1.1.0")

        assert service.busy_mod_ids == frozenset()
        assert service.disable_mod("demo").enabled is False
        assert state_of(service, "demo") == ("demo-1.0.0.zip.disabled", "1.0.0", False)

    @respx.mock
    @pytest.mark.asyncio
    async def test_v7_after_a_rolled_back_change(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        mock_mod("demo")
        real_save = service.state_manager.save
        calls = {"n": 0}

        def failing_save() -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("disk full")
            real_save()

        monkeypatch.setattr(service.state_manager, "save", failing_save)

        with pytest.raises(ModVersionChangeFailedError):
            await service.change_version("demo", "1.1.0")

        assert mod_files(service) == ["demo-1.0.0.zip"]
        assert state_of(service, "demo") == ("demo-1.0.0.zip", "1.0.0", True)
        assert service.busy_mod_ids == frozenset()
        assert service.disable_mod("demo").enabled is False
        assert mod_files(service) == ["demo-1.0.0.zip.disabled"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_v8_after_cancellation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        mock_mod("demo")
        started, _release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first

        assert service.busy_mod_ids == frozenset()
        assert mod_files(service) == ["demo-1.0.0.zip"]
        assert state_of(service, "demo") == ("demo-1.0.0.zip", "1.0.0", True)
        service.remove_mod("demo")
        assert mod_files(service) == []
        assert state_of(service, "demo") is None
