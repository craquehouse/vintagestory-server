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
    fixture_json,
    install_existing,
    make_service,
    mod_zip_bytes,
)

from vintagestory_api.services.mod_api import DownloadError
from vintagestory_api.services.mod_api import ModNotFoundError as ApiModNotFoundError
from vintagestory_api.services.mod_state import ModStateManager
from vintagestory_api.services.mods import (
    InstallResult,
    ModAlreadyInstalledError,
    ModFileConflictError,
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
    archive_modinfo: dict[str, Any] | None = None,
) -> respx.Route:
    """Lookup and both downloads for `modid`; files are named `<modid>-<version>.zip`.

    `archive_modinfo` replaces the modinfo.json of both archives. Returns the lookup route.
    """
    lookup = respx.get(MOD_URL.format(modid)).mock(
        return_value=Response(
            200, json=entry(modid, f"{modid}-1.1.0.zip", f"{modid}-1.0.0.zip", fileids)
        )
    )
    for fileid, version in zip(fileids, ("1.1.0", "1.0.0"), strict=True):
        content = mod_zip_bytes(
            archive_modinfo
            or {"modid": modid, "name": modid, "version": archive_version or version}
        )
        respx.get(DOWNLOAD_URL, params={"fileid": str(fileid)}).mock(
            return_value=Response(200, content=content)
        )
    return lookup


def mock_fixture(
    fixture: str, slugs: list[str], downloads: dict[int, tuple[str, str]]
) -> respx.Route:
    """Lookups of `slugs` served by a captured entry; downloads by file ID as (modid,
    version). Returns the route of all downloads."""
    for slug in slugs:
        respx.get(MOD_URL.format(slug)).mock(return_value=Response(200, json=fixture_json(fixture)))

    def archive(request: Any) -> Response:
        modid, version = downloads[int(request.url.params["fileid"])]
        return Response(
            200, content=mod_zip_bytes({"modid": modid, "name": modid, "version": version})
        )

    return respx.get(DOWNLOAD_URL).mock(side_effect=archive)


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
    mods_dir = service.state_manager.mods_dir
    return sorted(p.name for p in mods_dir.iterdir()) if mods_dir.exists() else []


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
    async def test_v5_install_of_a_mod_being_changed_is_refused_as_busy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Busy, not "already installed", and refused before any lookup."""
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo-1.0.0.zip")
        lookup = mock_mod("demo")
        started, release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()
        for slug in ("demo", "DEMO"):
            with pytest.raises(ModOperationInProgressError):
                await service.install_mod(slug)
        assert lookup.call_count == 1
        release.set()
        await first

        assert mod_files(service) == ["demo-1.1.0.zip"]
        assert service.busy_mod_ids == frozenset()

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


class TestInstallHoldsTheInstallModId:
    @respx.mock
    @pytest.mark.asyncio
    async def test_i1_two_installs_of_the_same_mod_install_it_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        mock_mod("demo")
        started, release = gate_download(service, monkeypatch)

        tasks = {
            asyncio.create_task(service.install_mod("demo")),
            asyncio.create_task(service.install_mod("demo")),
        }
        await started.wait()
        # The other one is refused at once; it cannot finish before the gate opens.
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        refused = done.pop()
        with pytest.raises(ModOperationInProgressError):
            refused.result()
        release.set()
        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert sum(isinstance(r, InstallResult) for r in results) == 1
        assert sum(isinstance(r, ModOperationInProgressError) for r in results) == 1
        assert mod_files(service) == ["demo-1.1.0.zip"]
        assert [m.slug for m in service.state_manager.list_mods()] == ["demo"]
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_i2_operations_on_a_mod_being_installed_are_refused_as_busy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        mock_mod("demo")
        started, release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.install_mod("demo"))
        await started.wait()
        for operation in (service.remove_mod, service.enable_mod, service.disable_mod):
            with pytest.raises(ModOperationInProgressError):
                operation("demo")
        with pytest.raises(ModOperationInProgressError):
            await service.change_version("demo", "1.0.0")
        assert mod_files(service) == []
        release.set()
        result = await first

        assert (result.slug, result.version) == ("demo", "1.1.0")
        assert state_of(service, "demo") == ("demo-1.1.0.zip", "1.1.0", True)
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_i3_another_slug_of_the_same_install_mod_id_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        downloads = mock_fixture(
            "egocaribautomapmarkers",
            ["automapmarkers", "egocaribautomapmarkers"],
            {90054: ("egocaribautomapmarkers", "5.0.3")},
        )
        started, release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.install_mod("automapmarkers"))
        await started.wait()
        assert service.busy_mod_ids == frozenset({"egocaribautomapmarkers"})
        with pytest.raises(ModOperationInProgressError) as raised:
            await service.install_mod("egocaribautomapmarkers")
        assert raised.value.slug == "egocaribautomapmarkers"
        release.set()
        await first

        assert downloads.call_count == 1
        assert [m.slug for m in service.state_manager.list_mods()] == ["egocaribautomapmarkers"]
        assert len(mod_files(service)) == 1
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_i4_another_mod_id_of_the_same_entry_is_not_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        mock_fixture(
            "instruments",
            ["instruments", "vsinstrumentsbase"],
            {12840: ("instruments", "1.2.2"), 72936: ("vsinstrumentsbase", "2.0.7")},
        )
        started, release = gate_download(service, monkeypatch, slug="instruments")

        first = asyncio.create_task(service.install_mod("instruments"))
        await started.wait()
        second = await service.install_mod("vsinstrumentsbase")
        assert (second.slug, second.version) == ("vsinstrumentsbase", "2.0.7")
        assert service.busy_mod_ids == frozenset({"instruments"})
        release.set()
        await first

        assert mod_files(service) == ["instruments_1.2.2.zip", "vsinstrumentsbase_2.0.7.zip"]
        assert sorted(m.slug for m in service.state_manager.list_mods()) == [
            "instruments",
            "vsinstrumentsbase",
        ]
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_i5_install_mod_id_already_installed_under_another_slug(
        self, tmp_path: Path
    ) -> None:
        service = make_service(tmp_path)
        installed = install_existing(
            service, "egocaribautomapmarkers", "5.0.2", "automapmarkers-5.0.2.zip"
        )
        before = installed.read_bytes()
        downloads = mock_fixture(
            "egocaribautomapmarkers",
            ["automapmarkers"],
            {90054: ("egocaribautomapmarkers", "5.0.3")},
        )

        with pytest.raises(ModAlreadyInstalledError) as raised:
            await service.install_mod("automapmarkers")

        assert (raised.value.slug, raised.value.current_version) == (
            "egocaribautomapmarkers",
            "5.0.2",
        )
        assert not downloads.called
        assert mod_files(service) == ["automapmarkers-5.0.2.zip"]
        assert installed.read_bytes() == before
        assert state_of(service, "egocaribautomapmarkers") == (
            "automapmarkers-5.0.2.zip",
            "5.0.2",
            True,
        )
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_i6_archive_naming_an_installed_mod_places_nothing(
        self, tmp_path: Path
    ) -> None:
        service = make_service(tmp_path)
        # Same filename as the download, to prove the installed file is not replaced
        other = install_existing(service, "other", "1.0.0", "demo-1.1.0.zip")
        service.state_manager.import_mod(other)
        cached = service.state_manager.state_dir / "mods" / "other" / "1.0.0" / "modinfo.json"
        before = (other.read_bytes(), cached.read_bytes(), state_of(service, "other"))
        mock_mod("demo", archive_modinfo={"modid": "other", "name": "Other", "version": "2.0.0"})

        with pytest.raises(ModAlreadyInstalledError) as raised:
            await service.install_mod("demo")

        assert (raised.value.slug, raised.value.current_version) == ("other", "1.0.0")
        assert mod_files(service) == ["demo-1.1.0.zip"]
        assert (other.read_bytes(), cached.read_bytes(), state_of(service, "other")) == before
        assert [m.slug for m in service.state_manager.list_mods()] == ["other"]
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_i7_archive_naming_a_busy_mod_places_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "other", "1.0.0", "other-1.0.0.zip")
        mock_mod("other", (21, 20))
        mock_mod("demo", archive_modinfo={"modid": "other", "name": "Other", "version": "1.1.0"})
        started, release = gate_download(service, monkeypatch, slug="other")

        first = asyncio.create_task(service.change_version("other", "1.1.0"))
        await started.wait()
        with pytest.raises(ModOperationInProgressError) as raised:
            await service.install_mod("demo")
        assert raised.value.slug == "other"
        assert mod_files(service) == ["other-1.0.0.zip"]
        assert service.busy_mod_ids == frozenset({"other"})
        release.set()
        await first

        assert mod_files(service) == ["other-1.1.0.zip"]
        assert [m.slug for m in service.state_manager.list_mods()] == ["other"]
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_i8_archive_spelling_the_mod_id_differently_installs(
        self, tmp_path: Path
    ) -> None:
        service = make_service(tmp_path)
        mock_mod("demo", archive_modinfo={"ModID": "Demo", "Name": "Demo", "Version": "1.1.0"})

        result = await service.install_mod("demo")

        assert result.slug == "Demo"
        assert state_of(service, "Demo") == ("demo-1.1.0.zip", "1.1.0", True)
        with pytest.raises(ModAlreadyInstalledError) as raised:
            await service.install_mod("demo")
        assert raised.value.slug == "Demo"
        assert mod_files(service) == ["demo-1.1.0.zip"]
        assert service.busy_mod_ids == frozenset()


    @respx.mock
    @pytest.mark.asyncio
    async def test_installed_check_ignores_case(self, tmp_path: Path) -> None:
        """Review M1: a mod installed as `Demo` (its archive spelled it so) is found when
        `demo` is installed again, even if that archive says `demo`: no second file or
        entry. Refused before the lookup, naming the installed spelling."""
        service = make_service(tmp_path)
        installed = install_existing(service, "Demo", "1.0.0", "Demo-1.0.0.zip")
        before = installed.read_bytes()
        lookup = mock_mod("demo")

        for slug in ("demo", "DEMO"):
            with pytest.raises(ModAlreadyInstalledError) as raised:
                await service.install_mod(slug)
            assert (raised.value.slug, raised.value.current_version) == ("Demo", "1.0.0")

        assert not lookup.called
        assert mod_files(service) == ["Demo-1.0.0.zip"]
        assert installed.read_bytes() == before
        assert [m.slug for m in service.state_manager.list_mods()] == ["Demo"]
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_install_mod_id_installed_in_another_case_is_refused(
        self, tmp_path: Path
    ) -> None:
        """The install mod ID check ignores case too, and refuses before the download."""
        service = make_service(tmp_path)
        install_existing(service, "EgocaribAutoMapMarkers", "5.0.2", "amm-5.0.2.zip")
        downloads = mock_fixture(
            "egocaribautomapmarkers",
            ["automapmarkers"],
            {90054: ("egocaribautomapmarkers", "5.0.3")},
        )

        with pytest.raises(ModAlreadyInstalledError) as raised:
            await service.install_mod("automapmarkers")

        assert raised.value.slug == "EgocaribAutoMapMarkers"
        assert not downloads.called
        assert mod_files(service) == ["amm-5.0.2.zip"]


class TestInstallReleasesTheLock:
    @respx.mock
    @pytest.mark.asyncio
    async def test_i9_after_cancellation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        mock_mod("demo")
        started, release = gate_download(service, monkeypatch)

        first = asyncio.create_task(service.install_mod("demo"))
        await started.wait()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first

        assert service.busy_mod_ids == frozenset()
        assert mod_files(service) == []
        assert service.state_manager.list_mods() == []
        release.set()
        result = await service.install_mod("demo")
        assert result.slug == "demo"
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_i9_after_a_failed_download(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        respx.get(MOD_URL.format("demo")).mock(
            return_value=Response(200, json=entry("demo", "demo-1.1.0.zip", "demo-1.0.0.zip",
                                                  (11, 10)))
        )
        respx.get(DOWNLOAD_URL).mock(
            side_effect=[
                Response(500),
                Response(
                    200,
                    content=mod_zip_bytes({"modid": "demo", "name": "Demo", "version": "1.1.0"}),
                ),
            ]
        )

        with pytest.raises(DownloadError):
            await service.install_mod("demo")

        assert service.busy_mod_ids == frozenset()
        assert mod_files(service) == []
        assert (await service.install_mod("demo")).slug == "demo"
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_i9_after_a_failed_import(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        mock_mod("demo")
        real_import = service.state_manager.import_mod
        calls = {"n": 0}

        def failing_import(path: Path) -> Any:
            calls["n"] += 1
            if calls["n"] == 1:
                raise ValueError("bad archive")
            return real_import(path)

        monkeypatch.setattr(service.state_manager, "import_mod", failing_import)

        with pytest.raises(ValueError, match="bad archive"):
            await service.install_mod("demo")

        assert service.busy_mod_ids == frozenset()
        assert mod_files(service) == []
        assert service.state_manager.list_mods() == []
        assert (await service.install_mod("demo")).slug == "demo"
        assert service.busy_mod_ids == frozenset()


def mock_foo_zip(modid: str, *, readable: bool = True) -> None:
    """Lookup and download of `modid` 1.0.0, whose release file is named `Foo.zip`.

    With `readable=False` the archive has no modinfo.json.
    """
    respx.get(MOD_URL.format(modid)).mock(
        return_value=Response(
            200,
            json={
                "statuscode": "200",
                "mod": {
                    "assetid": 2,
                    "releases": [
                        {"modversion": "1.0.0", "modidstr": modid, "fileid": 20,
                         "filename": "Foo.zip", "tags": ["1.22.7"]},
                    ],
                },
            },
        )
    )
    content = (
        mod_zip_bytes({"modid": modid, "name": modid, "version": "1.0.0"})
        if readable
        else mod_zip_bytes("not a mod", member="readme.txt")
    )
    respx.get(DOWNLOAD_URL, params={"fileid": "20"}).mock(
        return_value=Response(200, content=content)
    )


def saved_slugs(service: ModService) -> list[str]:
    """Mod IDs in the state file on disk."""
    manager = ModStateManager(
        state_dir=service.state_manager.state_dir, mods_dir=service.state_manager.mods_dir
    )
    manager.load()
    return sorted(m.slug for m in manager.list_mods())


class TestInstallRefusesAFileNameInUse:
    """Story 18.2 (FR199, Epic 18 ADR-4): an install never replaces another mod's file."""

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize("enabled", [True, False], ids=["enabled", "disabled"])
    @pytest.mark.parametrize("readable", [True, False], ids=["modinfo", "no-modinfo"])
    async def test_another_mods_file_is_untouched(
        self, tmp_path: Path, enabled: bool, readable: bool
    ) -> None:
        service = make_service(tmp_path)
        other = install_existing(service, "moda", "1.0.0", "Foo.zip", enabled=enabled)
        other_bytes = other.read_bytes()
        other_state = state_of(service, "moda")
        files_before = mod_files(service)
        mock_foo_zip("modb", readable=readable)

        with pytest.raises(ModFileConflictError) as raised:
            await service.install_mod("modb")

        in_use = "Foo.zip" if enabled else "Foo.zip.disabled"
        assert raised.value.filename == in_use
        assert raised.value.slug == "modb"
        assert str(raised.value) == (
            f"Cannot install 'modb': a file named {in_use} already exists in the mods directory."
        )
        assert other.read_bytes() == other_bytes
        assert state_of(service, "moda") == other_state
        assert mod_files(service) == files_before
        assert service.state_manager.get_mod_by_slug("modb") is None
        assert service.busy_mod_ids == frozenset()
        assert saved_slugs(service) == ["moda"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_a_stray_file_without_state_is_untouched(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        mods_dir = service.state_manager.mods_dir
        mods_dir.mkdir(parents=True)
        stray = mods_dir / "Foo.zip"
        stray.write_bytes(b"stray bytes")
        mock_foo_zip("modb")

        with pytest.raises(ModFileConflictError) as raised:
            await service.install_mod("modb")

        assert raised.value.filename == "Foo.zip"
        assert stray.read_bytes() == b"stray bytes"
        assert mod_files(service) == ["Foo.zip"]
        assert service.state_manager.list_mods() == []
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_a_state_entry_without_a_file_is_untouched(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "moda", "1.0.0", "Foo.zip").unlink()
        entry_before = service.state_manager.get_mod("Foo.zip")
        mock_foo_zip("modb")

        with pytest.raises(ModFileConflictError) as raised:
            await service.install_mod("modb")

        assert raised.value.filename == "Foo.zip"
        assert service.state_manager.get_mod("Foo.zip") == entry_before
        assert mod_files(service) == []
        assert service.state_manager.get_mod_by_slug("modb") is None
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize("installed_as", ["modb", "ModB"])
    async def test_reinstalling_the_same_mod_is_still_already_installed(
        self, tmp_path: Path, installed_as: str
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, installed_as, "1.0.0", "Foo.zip")
        mock_foo_zip("modb")

        with pytest.raises(ModAlreadyInstalledError):
            await service.install_mod("modb")

        assert mod_files(service) == ["Foo.zip"]
        assert service.busy_mod_ids == frozenset()

    @respx.mock
    @pytest.mark.asyncio
    async def test_a_failed_import_cleans_up_only_the_new_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(tmp_path)
        other = install_existing(service, "moda", "1.0.0", "Other.zip")
        other_bytes = other.read_bytes()
        other_state = state_of(service, "moda")
        mock_foo_zip("modb")

        def failing_import(path: Path) -> Any:
            raise ValueError("bad archive")

        monkeypatch.setattr(service.state_manager, "import_mod", failing_import)

        with pytest.raises(ValueError, match="bad archive"):
            await service.install_mod("modb")

        assert mod_files(service) == ["Other.zip"]
        assert other.read_bytes() == other_bytes
        assert state_of(service, "moda") == other_state
        assert service.state_manager.get_mod("Foo.zip") is None
        assert service.busy_mod_ids == frozenset()
