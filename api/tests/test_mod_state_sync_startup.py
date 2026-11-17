"""Story 19.5 (Epic 19 ADR-10): the mod state sync runs once, at start-up only."""

import json
import zipfile
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vintagestory_api.main import app
from vintagestory_api.models.mods import ModState
from vintagestory_api.services import mods as mods_module
from vintagestory_api.services.mod_file_recovery import KEPT_ASIDE_SUFFIX, WORKING_COPY_SUFFIX
from vintagestory_api.services.mod_state import ModStateManager, ModSyncSummary
from vintagestory_api.services.mods import (
    ModService,
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
