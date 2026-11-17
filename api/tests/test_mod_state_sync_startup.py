"""Story 19.5 (Epic 19 ADR-10): the mod state sync runs once, at start-up only."""

import json
import zipfile
from collections.abc import Generator
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
import respx
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY
from fastapi.testclient import TestClient

from vintagestory_api import main as main_module
from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.mod_updates import StoredModRecord
from vintagestory_api.models.mods import ModState
from vintagestory_api.services import mod_state as mod_state_module
from vintagestory_api.services import mods as mods_module
from vintagestory_api.services.mod_file_recovery import KEPT_ASIDE_SUFFIX, WORKING_COPY_SUFFIX
from vintagestory_api.services.mod_state import ModStateManager, ModSyncSummary
from vintagestory_api.services.mod_updates import (
    ModUpdateService,
    ModUpdateStore,
    get_mod_update_service,
)
from vintagestory_api.services.mods import (
    ModService,
    get_mod_service,
    prepare_mod_files,
    sync_mod_state_at_startup,
)
from vintagestory_api.services.pending_restart import PendingRestartState


def write_mod_zip(path: Path, modid: str, version: str) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("modinfo.json", json.dumps({"modid": modid, "name": modid, "version": version}))


@pytest.fixture
def service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModService:
    """The mod service singleton, on tmp_path."""
    service = ModService(
        state_dir=tmp_path / "state",
        mods_dir=tmp_path / "mods",
        cache_dir=tmp_path / "cache",
        restart_state=PendingRestartState(),
    )
    service.state_manager.mods_dir.mkdir(parents=True)
    monkeypatch.setattr(mods_module, "_mod_service", service)
    return service


class TestSyncModStateAtStartup:
    def test_syncs_the_singletons_state_once(
        self,
        service: ModService,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        write_mod_zip(service.state_manager.mods_dir / "New.zip", "newmod", "1.0.0")
        calls: list[ModSyncSummary] = []
        sync = service.state_manager.sync_state_with_disk

        def record() -> ModSyncSummary:
            summary = sync()
            calls.append(summary)
            return summary

        monkeypatch.setattr(service.state_manager, "sync_state_with_disk", record)

        sync_mod_state_at_startup()

        assert calls == [ModSyncSummary(added=1, removed=0, skipped=0)]
        assert service.state_manager.get_mod("New.zip") is not None
        assert captured_logs.getvalue().count("mod_state_synced") == 1

    def test_a_failing_sync_is_logged_as_an_error_and_does_not_raise(
        self,
        service: ModService,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        """AC 13."""

        def fail() -> ModSyncSummary:
            raise RuntimeError("unexpected")

        monkeypatch.setattr(service.state_manager, "sync_state_with_disk", fail)

        sync_mod_state_at_startup()

        logs = captured_logs.getvalue().splitlines()
        [line] = [line for line in logs if "mod_state_sync_failed" in line]
        assert "error" in line
        assert "unexpected" in line

    def test_a_failure_to_build_the_mod_service_is_logged_and_does_not_raise(
        self, monkeypatch: pytest.MonkeyPatch, captured_logs: StringIO
    ) -> None:
        """AC 13 (ADR-10 decision 1): it surfaces again at the first mod request."""

        def fail() -> ModService:
            raise OSError(13, "Permission denied")

        monkeypatch.setattr(mods_module, "get_mod_service", fail)

        sync_mod_state_at_startup()

        logs = captured_logs.getvalue().splitlines()
        [line] = [line for line in logs if "mod_state_sync_failed" in line]
        assert "Permission denied" in line


class TestPrepareModFilesSync:
    def test_recovery_runs_first_and_the_sync_sees_the_recovered_file(
        self, service: ModService, captured_logs: StringIO
    ) -> None:
        """AC 7: an interrupted version change; the mod is neither removed nor added twice."""
        mods_dir = service.state_manager.mods_dir
        entry = ModState(
            filename="Foo.zip",
            slug="foo",
            version="1.0.0",
            enabled=True,
            installed_at=datetime(2025, 1, 1, tzinfo=UTC),
            asset_id=7,
        )
        service.state_manager.set_mod_state("Foo.zip", entry)
        write_mod_zip(mods_dir / f"Foo.zip{KEPT_ASIDE_SUFFIX}", "foo", "1.0.0")
        write_mod_zip(mods_dir / f"Foo.zip{WORKING_COPY_SUFFIX}", "foo", "1.1.0")
        original = (mods_dir / f"Foo.zip{KEPT_ASIDE_SUFFIX}").read_bytes()

        prepare_mod_files()

        assert sorted(p.name for p in mods_dir.iterdir()) == ["Foo.zip"]
        assert (mods_dir / "Foo.zip").read_bytes() == original
        assert service.state_manager.list_mods() == [entry]
        logs = captured_logs.getvalue()
        assert logs.index("mod_backup_restored") < logs.index("mod_state_synced")
        assert "mod_state_sync_removed" not in logs
        assert "mod_state_sync_added" not in logs

    @staticmethod
    def kept_aside_entry(service: ModService) -> ModState:
        """State `Foo.zip` (saved), its original kept aside as `Foo.zip.vsm-bak`, no file."""
        entry = ModState(
            filename="Foo.zip",
            slug="foo",
            version="1.0.0",
            enabled=True,
            installed_at=datetime(2025, 1, 1, tzinfo=UTC),
            asset_id=7,
        )
        service.state_manager.set_mod_state("Foo.zip", entry)
        service.state_manager.save()
        write_mod_zip(
            service.state_manager.mods_dir / f"Foo.zip{KEPT_ASIDE_SUFFIX}", "foo", "1.0.0"
        )
        return entry

    def test_a_failed_restore_keeps_the_entry_until_the_next_start_restores_it(
        self, service: ModService, monkeypatch: pytest.MonkeyPatch, captured_logs: StringIO
    ) -> None:
        """Review MEDIUM-1: `mod_recovery_failed` must not cost the mod its entry."""
        entry = self.kept_aside_entry(service)
        rename = Path.rename

        def refuse_restore(self: Path, target: Path) -> Path:
            if self.name.endswith(KEPT_ASIDE_SUFFIX):
                raise OSError(5, "Input/output error")
            return rename(self, target)

        monkeypatch.setattr(Path, "rename", refuse_restore)

        prepare_mod_files()

        logs = captured_logs.getvalue()
        assert "mod_recovery_failed" in logs
        assert service.state_manager.list_mods() == [entry]
        [line] = [line for line in logs.splitlines() if "mod_state_sync_kept_aside" in line]
        assert f"Foo.zip{KEPT_ASIDE_SUFFIX}" in line
        assert "mod_state_sync_removed" not in logs

        monkeypatch.setattr(Path, "rename", rename)
        service.state_manager.load()
        prepare_mod_files()

        mods_dir = service.state_manager.mods_dir
        assert sorted(p.name for p in mods_dir.iterdir()) == ["Foo.zip"]
        assert service.state_manager.list_mods() == [entry]

    def test_a_backup_kept_for_another_mods_file_keeps_the_entry_until_it_is_restored(
        self, service: ModService, captured_logs: StringIO
    ) -> None:
        """Review MEDIUM-1: `mod_backup_kept` must not cost the mod its entry."""
        entry = self.kept_aside_entry(service)
        mods_dir = service.state_manager.mods_dir
        in_the_way = mods_dir / "foo.zip"
        write_mod_zip(in_the_way, "bar", "3.0.0")

        prepare_mod_files()

        logs = captured_logs.getvalue()
        assert "mod_backup_kept" in logs
        assert service.state_manager.get_mod("Foo.zip") == entry
        [line] = [line for line in logs.splitlines() if "mod_state_sync_kept_aside" in line]
        assert f"Foo.zip{KEPT_ASIDE_SUFFIX}" in line

        in_the_way.unlink()
        service.state_manager.load()
        prepare_mod_files()

        assert sorted(p.name for p in mods_dir.iterdir()) == ["Foo.zip"]
        assert service.state_manager.list_mods() == [entry]

    def test_the_sync_knows_the_recoverys_kept_aside_suffix(self) -> None:
        assert mod_state_module.KEPT_ASIDE_SUFFIX == KEPT_ASIDE_SUFFIX


class TestStartUpOnly:
    def test_no_route_runs_the_sync(self) -> None:
        """AC 10: it runs only at start-up."""
        paths = [getattr(route, "path", "") for route in app.routes]

        assert paths
        assert [path for path in paths if "sync" in path.lower()] == []

    def test_entering_the_app_in_a_test_does_not_sync_the_data_directory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC 14: the autouse conftest guard keeps the lifespan away from VS_DATA_DIR."""
        calls: list[Path] = []

        def spy(self: ModStateManager) -> ModSyncSummary:
            calls.append(self.mods_dir)
            return ModSyncSummary(added=0, removed=0, skipped=0)

        monkeypatch.setattr(ModStateManager, "sync_state_with_disk", spy)

        with TestClient(app):
            pass

        assert calls == []


class TestStartUpSyncThroughTheApi:
    """Task 4: the real lifespan over a hand-built mods directory and state (AC 1, 2, 12)."""

    @pytest.fixture
    def data_dir(self, tmp_path: Path) -> Path:
        data_dir = tmp_path / "data"
        for name in ("state", "mods", "cache"):
            (data_dir / name).mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mod_service(self, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> ModService:
        """The singleton the real start-up work uses, with a state saved before the start."""
        service = ModService(
            state_dir=data_dir / "state",
            mods_dir=data_dir / "mods",
            cache_dir=data_dir / "cache",
            restart_state=PendingRestartState(),
            game_version="1.21.3",
        )
        mods_dir = service.state_manager.mods_dir
        for filename, slug in (("Kept.zip", "kept"), ("Gone.zip", "gone")):
            service.state_manager.set_mod_state(
                filename,
                ModState(
                    filename=filename,
                    slug=slug,
                    version="1.0.0",
                    installed_at=datetime(2025, 1, 1, tzinfo=UTC),
                    asset_id=11,
                ),
            )
        service.state_manager.save()
        write_mod_zip(mods_dir / "Kept.zip", "kept", "1.0.0")
        write_mod_zip(mods_dir / "New.zip", "newmod", "1.2.3")
        write_mod_zip(mods_dir / "Off.zip.disabled", "offmod", "2.0.0")
        monkeypatch.setattr(mods_module, "_mod_service", service)
        monkeypatch.setattr(main_module, "prepare_mod_files", prepare_mod_files)
        return service

    @pytest.fixture
    def update_store(self, data_dir: Path) -> ModUpdateStore:
        """An update store holding a record for the mod whose file is gone."""
        store = ModUpdateStore(data_dir / "state")
        store.set("gone", StoredModRecord(checked_at=datetime(2025, 1, 2, tzinfo=UTC), found=True))
        store.set("kept", StoredModRecord(checked_at=datetime(2025, 1, 2, tzinfo=UTC), found=True))
        store.save()
        return store

    @pytest.fixture
    def client(
        self, mod_service: ModService, update_store: ModUpdateStore, data_dir: Path
    ) -> Generator[TestClient]:
        settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=data_dir,
            debug=True,
        )
        update_service = ModUpdateService(
            store=update_store,
            mod_source=mod_service,
            game_version_provider=lambda: "1.21.3",
        )
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_mod_update_service] = lambda: update_service
        with respx.mock(assert_all_called=False) as router, TestClient(app) as client:
            yield client
            assert router.calls.call_count == 0, "the sync looked something up"
        app.dependency_overrides.clear()

    def test_the_installed_list_follows_the_mods_directory(self, client: TestClient) -> None:
        """AC 1 and AC 2, through `GET /api/v1alpha1/mods`."""
        response = client.get("/api/v1alpha1/mods", headers={"X-API-Key": TEST_ADMIN_KEY})

        assert response.status_code == 200
        data = response.json()["data"]
        mods = {mod["filename"]: mod for mod in data["mods"]}
        assert sorted(mods) == ["Kept.zip", "New.zip", "Off.zip.disabled"]
        assert (mods["New.zip"]["slug"], mods["New.zip"]["enabled"]) == ("newmod", True)
        assert (mods["Off.zip.disabled"]["slug"], mods["Off.zip.disabled"]["enabled"]) == (
            "offmod",
            False,
        )
        assert data["pending_restart"] is False

    def test_a_removed_mod_is_not_installed(self, client: TestClient) -> None:
        """AC 2: its routes answer 404 MOD_NOT_INSTALLED."""
        response = client.post(
            "/api/v1alpha1/mods/gone/disable", headers={"X-API-Key": TEST_ADMIN_KEY}
        )

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "MOD_NOT_INSTALLED"

    def test_update_status_after_the_sync(
        self, client: TestClient, update_store: ModUpdateStore
    ) -> None:
        """AC 12: added mods not checked yet, the removed mod not shown, the store untouched."""
        stored = update_store.path.read_bytes()

        response = client.get("/api/v1alpha1/mods/updates", headers={"X-API-Key": TEST_ADMIN_KEY})

        assert response.status_code == 200
        items = {item["slug"]: item for item in response.json()["data"]["mods"]}
        assert sorted(items) == ["kept", "newmod", "offmod"]
        for slug in ("newmod", "offmod"):
            assert (items[slug]["status"], items[slug]["reason"]) == ("unknown", "not_checked")
        assert update_store.path.read_bytes() == stored
