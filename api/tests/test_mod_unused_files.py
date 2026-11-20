"""Unused files in the mods directory, and the rescan (Story 24.5, Epic 24 ADR-3, ADR-4)."""

import io
import json
import os
import zipfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.mods import ModState
from vintagestory_api.services.mod_updates import (
    ModUpdateService,
    ModUpdateStore,
    get_mod_update_service,
)
from vintagestory_api.services.mods import (
    ModsBusyError,
    ModService,
    UnusedFileDeleteFailedError,
    UnusedFileNotFoundError,
    get_mod_service,
)
from vintagestory_api.services.pending_restart import PendingRestartState

ADMIN = {"X-API-Key": TEST_ADMIN_KEY}
MONITOR = {"X-API-Key": TEST_MONITOR_KEY}
MODS = "/api/v1alpha1/mods"


def zip_bytes(modinfo: object) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("modinfo.json", json.dumps(modinfo))
    return buffer.getvalue()


def archive(path: Path, modid: str, version: str = "1.0.0") -> Path:
    path.write_bytes(zip_bytes({"modid": modid, "name": modid, "version": version}))
    return path


def install(service: ModService, filename: str, modid: str) -> Path:
    """A mod as the manager installs it: its file and its entry."""
    path = archive(service.state_manager.mods_dir / filename, modid)
    service.state_manager.set_mod_state(
        filename,
        ModState(
            filename=filename,
            slug=modid,
            version="1.0.0",
            enabled=not filename.endswith(".disabled"),
            installed_at=datetime(2026, 1, 1, tzinfo=UTC),
            asset_id=7,
        ),
    )
    service.state_manager.save()
    return path


@pytest.fixture
def service(tmp_path: Path) -> ModService:
    svc = ModService(
        state_dir=tmp_path / "state",
        mods_dir=tmp_path / "mods",
        restart_state=PendingRestartState(),
        cache_dir=tmp_path / "cache",
        game_version_provider=lambda: "1.22.7",
    )
    svc.state_manager.mods_dir.mkdir(parents=True)
    return svc


def names(service: ModService) -> dict[str, str]:
    return {item.name: item.reason for item in service.list_unused_files()}


class TestListing:
    """AC 1 (FR337, FR340; ADR-3)."""

    def test_lists_leftovers_unreadable_and_duplicate_archives(self, service: ModService) -> None:
        mods_dir = service.state_manager.mods_dir
        install(service, "carryon_1.0.0.zip", "carryon")
        (mods_dir / "old.zip.bak").write_bytes(b"backup")
        (mods_dir / "x.TMP").write_bytes(b"temp")
        (mods_dir / "broken.zip").write_bytes(b"not a zip")
        (mods_dir / "nomodinfo.zip.disabled").write_bytes(zip_bytes([1, 2]))
        archive(mods_dir / "carryon_0.9.0.zip", "CarryOn")

        listing = {item.name: item for item in service.list_unused_files()}

        assert {name: item.reason for name, item in listing.items()} == {
            "old.zip.bak": "leftover",
            "x.TMP": "leftover",
            "broken.zip": "unreadable",
            "nomodinfo.zip.disabled": "unreadable",
            "carryon_0.9.0.zip": "duplicate_mod_id",
        }
        assert listing["carryon_0.9.0.zip"].installed_as == "carryon_1.0.0.zip"
        assert listing["old.zip.bak"].size_bytes == len(b"backup")
        assert listing["old.zip.bak"].modified_at.tzinfo is UTC

    def test_never_lists_mods_code_folders_or_the_managers_own_files(
        self, service: ModService
    ) -> None:
        mods_dir = service.state_manager.mods_dir
        install(service, "carryon_1.0.0.zip", "carryon")
        install(service, "Off.zip.disabled", "offmod")
        (mods_dir / "SourceMod.cs").write_text("class A {}")
        (mods_dir / "FolderMod").mkdir()
        (mods_dir / "FolderMod" / "inner.bak").write_bytes(b"x")
        (mods_dir / "readme.txt").write_text("notes")
        (mods_dir / "a.zip.vsm-tmp").write_bytes(b"x")
        (mods_dir / "a.zip.vsm-bak").write_bytes(b"x")
        (mods_dir / "link.bak").symlink_to(mods_dir / "readme.txt")

        assert names(service) == {}

    def test_an_archive_the_sync_would_add_is_not_unused(self, service: ModService) -> None:
        archive(service.state_manager.mods_dir / "new.zip", "newmod")

        assert names(service) == {}

    def test_a_name_an_entry_uses_in_another_case_is_not_listed(self, service: ModService) -> None:
        install(service, "Foo.zip.bak", "foo")

        assert names(service) == {}

    def test_a_missing_mods_directory_lists_nothing(self, tmp_path: Path) -> None:
        svc = ModService(
            state_dir=tmp_path / "state",
            mods_dir=tmp_path / "missing",
            restart_state=PendingRestartState(),
            cache_dir=tmp_path / "cache",
        )

        assert svc.list_unused_files() == []

    def test_the_listing_agrees_with_what_the_sync_skips(self, service: ModService) -> None:
        """ADR-3 decision 3: one set of rules, so a skipped archive is always listed."""
        mods_dir = service.state_manager.mods_dir
        install(service, "a.zip", "moda")
        archive(mods_dir / "a-copy.zip", "moda")
        (mods_dir / "broken.zip").write_bytes(b"not a zip")
        archive(mods_dir / "b.zip", "modb")

        listed_archives = {n for n in names(service) if n.endswith(".zip")}
        summary = service.state_manager.sync_state_with_disk()

        assert summary.skipped == len(listed_archives) == 2
        assert summary.added == 1


class TestReviewFollowUps:
    """Story 24.5 review: a stale entry, a failed delete, the restart rule per reason."""

    def test_an_entry_whose_file_is_gone_does_not_make_the_only_copy_a_duplicate(
        self, service: ModService
    ) -> None:
        """M1: until a rescan, the state can name a file deleted by hand."""
        install(service, "moda_2.0.0.zip", "moda").unlink()
        archive(service.state_manager.mods_dir / "moda_1.0.0.zip", "moda")

        assert names(service) == {}
        with pytest.raises(UnusedFileNotFoundError):
            service.delete_unused_file("moda_1.0.0.zip")
        assert (service.state_manager.mods_dir / "moda_1.0.0.zip").exists()
        # The rescan adopts it
        assert service.rescan().added == 1

    def test_a_delete_that_fails_raises_and_keeps_the_file(
        self, service: ModService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = service.state_manager.mods_dir / "x.tmp"
        path.write_bytes(b"x")

        def refuse(self: Path, missing_ok: bool = False) -> None:
            raise PermissionError(13, "Permission denied", str(self))

        monkeypatch.setattr(Path, "unlink", refuse)

        with pytest.raises(UnusedFileDeleteFailedError):
            service.delete_unused_file("x.tmp")
        monkeypatch.undo()
        assert path.exists()

    def test_deleting_an_unreadable_archive_while_the_server_runs_requires_a_restart(
        self, service: ModService
    ) -> None:
        (service.state_manager.mods_dir / "broken.zip").write_bytes(b"not a zip")
        service.set_server_running(True)

        assert service.delete_unused_file("broken.zip").pending_restart is True


class TestDelete:
    """AC 2, 3 (FR338; ADR-3 decision 5, ADR-4 decision 5)."""

    def test_deletes_a_listed_file(self, service: ModService) -> None:
        path = service.state_manager.mods_dir / "old.zip.bak"
        path.write_bytes(b"x")

        result = service.delete_unused_file("old.zip.bak")

        assert (result.name, result.pending_restart) == ("old.zip.bak", False)
        assert not path.exists()
        assert names(service) == {}

    @pytest.mark.parametrize(
        "name",
        [
            "carryon_1.0.0.zip",
            "SourceMod.cs",
            "FolderMod",
            "a.zip.vsm-bak",
            "../state/mods.json",
            "..",
            "gone.bak",
            "OLD.ZIP.BAK",
        ],
    )
    def test_refuses_a_name_not_in_the_listing(self, service: ModService, name: str) -> None:
        mods_dir = service.state_manager.mods_dir
        install(service, "carryon_1.0.0.zip", "carryon")
        (mods_dir / "SourceMod.cs").write_text("class A {}")
        (mods_dir / "FolderMod").mkdir()
        (mods_dir / "a.zip.vsm-bak").write_bytes(b"x")
        (mods_dir / "old.zip.bak").write_bytes(b"x")
        before = sorted(p.name for p in mods_dir.iterdir())

        with pytest.raises(UnusedFileNotFoundError):
            service.delete_unused_file(name)

        assert sorted(p.name for p in mods_dir.iterdir()) == before
        assert service.state_manager.state_file.is_file()

    def test_deleting_a_skipped_archive_while_the_server_runs_requires_a_restart(
        self, service: ModService
    ) -> None:
        install(service, "a.zip", "moda")
        archive(service.state_manager.mods_dir / "a-old.zip", "moda")
        service.set_server_running(True)

        result = service.delete_unused_file("a-old.zip")

        assert result.pending_restart is True
        assert service.restart_state.pending_restart is True

    def test_deleting_a_leftover_while_the_server_runs_needs_no_restart(
        self, service: ModService
    ) -> None:
        (service.state_manager.mods_dir / "x.tmp").write_bytes(b"x")
        service.set_server_running(True)

        assert service.delete_unused_file("x.tmp").pending_restart is False
        assert service.restart_state.pending_restart is False

    def test_a_second_archive_left_by_an_interrupted_rename_can_be_deleted(
        self, service: ModService
    ) -> None:
        """VSS-3tb1 item 2: the old archive stays after the rename; it is a duplicate."""
        install(service, "moda_2.0.0.zip", "moda")
        archive(service.state_manager.mods_dir / "moda_1.0.0.zip", "moda")

        assert names(service) == {"moda_1.0.0.zip": "duplicate_mod_id"}
        service.delete_unused_file("moda_1.0.0.zip")
        assert sorted(p.name for p in service.state_manager.mods_dir.iterdir()) == [
            "moda_2.0.0.zip"
        ]


class TestBusyRule:
    """AC 5 (FR336, FR338; ADR-4 decisions 2 and 3)."""

    def test_rescan_and_delete_are_refused_while_a_mods_lock_is_held(
        self, service: ModService
    ) -> None:
        (service.state_manager.mods_dir / "x.tmp").write_bytes(b"x")

        with service._hold("carryon"):
            with pytest.raises(ModsBusyError):
                service.rescan()
            with pytest.raises(ModsBusyError):
                service.delete_unused_file("x.tmp")

        assert (service.state_manager.mods_dir / "x.tmp").exists()

    def test_rescan_and_delete_are_refused_while_another_operation_runs(
        self, service: ModService
    ) -> None:
        (service.state_manager.mods_dir / "x.tmp").write_bytes(b"x")

        with pytest.raises(ModsBusyError):
            service.rescan(other_operation_running=True)
        with pytest.raises(ModsBusyError):
            service.delete_unused_file("x.tmp", other_operation_running=True)

    @pytest.mark.asyncio
    async def test_the_update_service_reports_a_running_check_or_update_all(
        self, tmp_path: Path, service: ModService
    ) -> None:
        update_service = ModUpdateService(
            store=ModUpdateStore(tmp_path / "state"),
            mod_source=service,
            game_version_provider=lambda: "1.22.7",
        )
        assert update_service.is_running is False

        async with update_service._check_lock:
            assert update_service.is_running is True
        async with update_service._apply_lock:
            assert update_service.is_running is True
        assert update_service.is_running is False


class TestRescan:
    """AC 4 (FR336; ADR-4 decisions 1 and 5)."""

    def test_adds_a_copied_in_archive(self, service: ModService) -> None:
        archive(service.state_manager.mods_dir / "new.zip", "newmod")

        result = service.rescan()

        assert (result.added, result.removed, result.skipped) == (1, 0, 0)
        assert result.pending_restart is False
        assert service.state_manager.get_mod_by_slug("newmod") is not None

    def test_a_change_while_the_server_runs_requires_a_restart(self, service: ModService) -> None:
        archive(service.state_manager.mods_dir / "new.zip", "newmod")
        service.set_server_running(True)

        assert service.rescan().pending_restart is True
        assert service.restart_state.pending_restart is True

    def test_no_change_needs_no_restart(self, service: ModService) -> None:
        install(service, "a.zip", "moda")
        service.set_server_running(True)

        result = service.rescan()

        assert (result.added, result.removed, result.pending_restart) == (0, 0, False)
        assert service.restart_state.pending_restart is False


class TestRoutes:
    """The three Admin routes (AC 1 to 5)."""

    @pytest.fixture
    def update_service(self, tmp_path: Path, service: ModService) -> ModUpdateService:
        return ModUpdateService(
            store=ModUpdateStore(tmp_path / "state"),
            mod_source=service,
            game_version_provider=lambda: "1.22.7",
        )

    @pytest.fixture
    def client(
        self, tmp_path: Path, service: ModService, update_service: ModUpdateService
    ) -> Generator[TestClient]:
        settings = Settings(
            api_key_admin=TEST_ADMIN_KEY, api_key_monitor=TEST_MONITOR_KEY, data_dir=tmp_path
        )
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_mod_service] = lambda: service
        app.dependency_overrides[get_mod_update_service] = lambda: update_service
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.clear()

    def test_list(self, client: TestClient, service: ModService) -> None:
        path = service.state_manager.mods_dir / "old.zip.bak"
        path.write_bytes(b"12345")
        mtime = datetime(2026, 11, 1, 12, 0, tzinfo=UTC).timestamp()
        os.utime(path, (mtime, mtime))

        response = client.get(f"{MODS}/unused-files", headers=ADMIN)

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "data": {
                "files": [
                    {
                        "name": "old.zip.bak",
                        "size_bytes": 5,
                        "modified_at": "2026-11-01T12:00:00Z",
                        "reason": "leftover",
                        "installed_as": None,
                    }
                ]
            },
        }

    def test_delete(self, client: TestClient, service: ModService) -> None:
        (service.state_manager.mods_dir / "old.zip.bak").write_bytes(b"x")

        response = client.delete(f"{MODS}/unused-files/old.zip.bak", headers=ADMIN)

        assert response.status_code == 200
        assert response.json()["data"] == {"name": "old.zip.bak", "pending_restart": False}

    @pytest.mark.parametrize("name", ["missing.bak", "mods.json", "%2E%2E"])
    def test_delete_of_a_name_not_listed_is_404(
        self, client: TestClient, service: ModService, name: str
    ) -> None:
        service.state_manager.save()

        response = client.delete(f"{MODS}/unused-files/{name}", headers=ADMIN)

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "UNUSED_FILE_NOT_FOUND"
        assert service.state_manager.state_file.is_file()

    def test_a_path_with_a_separator_never_reaches_the_route(
        self, client: TestClient, service: ModService
    ) -> None:
        """An encoded slash is decoded by the router, so the path matches no route."""
        service.state_manager.save()

        response = client.delete(f"{MODS}/unused-files/..%2Fstate%2Fmods.json", headers=ADMIN)

        assert response.status_code in (404, 405)
        assert service.state_manager.state_file.is_file()

    def test_rescan(self, client: TestClient, service: ModService) -> None:
        archive(service.state_manager.mods_dir / "new.zip", "newmod")

        response = client.post(f"{MODS}/rescan", headers=ADMIN)

        assert response.status_code == 200
        assert response.json()["data"] == {
            "added": 1,
            "removed": 0,
            "skipped": 0,
            "pending_restart": False,
        }
        listed = client.get(MODS, headers=ADMIN).json()["data"]
        assert [mod["slug"] for mod in listed["mods"]] == ["newmod"]

    def test_a_delete_that_fails_is_500(
        self, client: TestClient, service: ModService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (service.state_manager.mods_dir / "x.tmp").write_bytes(b"x")

        def refuse(self: Path, missing_ok: bool = False) -> None:
            raise PermissionError(13, "Permission denied", str(self))

        monkeypatch.setattr(Path, "unlink", refuse)
        response = client.delete(f"{MODS}/unused-files/x.tmp", headers=ADMIN)
        monkeypatch.undo()

        assert response.status_code == 500
        assert response.json()["detail"]["code"] == "UNUSED_FILE_DELETE_FAILED"

    def test_busy_is_409(self, client: TestClient, service: ModService) -> None:
        (service.state_manager.mods_dir / "x.tmp").write_bytes(b"x")

        with service._hold("carryon"):
            rescan = client.post(f"{MODS}/rescan", headers=ADMIN)
            delete = client.delete(f"{MODS}/unused-files/x.tmp", headers=ADMIN)

        for response in (rescan, delete):
            assert response.status_code == 409
            assert response.json()["detail"]["code"] == "MODS_BUSY"

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("get", "/unused-files"),
            ("delete", "/unused-files/x.tmp"),
            ("post", "/rescan"),
        ],
    )
    def test_monitor_is_refused(
        self, client: TestClient, service: ModService, method: str, path: str
    ) -> None:
        (service.state_manager.mods_dir / "x.tmp").write_bytes(b"x")

        response = client.request(method.upper(), f"{MODS}{path}", headers=MONITOR)

        assert response.status_code == 403
        assert (service.state_manager.mods_dir / "x.tmp").exists()
