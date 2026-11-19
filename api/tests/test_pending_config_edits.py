"""Tests for the store of restart-required settings saved while the game runs (Story 22.7)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from vintagestory_api.config import Settings
from vintagestory_api.services.pending_config_edits import (
    PENDING_CONFIG_EDITS_FILENAME,
    PendingConfigEdit,
    PendingConfigEdits,
    reapply_edits,
)
from vintagestory_api.services.server import ServerService

T0 = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
T1 = datetime(2026, 11, 19, 12, 5, 0, tzinfo=UTC)


class Clock:
    """A fixed clock that the test moves on."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "state"


@pytest.fixture
def clock() -> Clock:
    return Clock(T0)


@pytest.fixture
def store(state_dir: Path, clock: Clock) -> PendingConfigEdits:
    return PendingConfigEdits(state_dir, now=clock)


def write_state(state_dir: Path, text: str) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / PENDING_CONFIG_EDITS_FILENAME
    path.write_text(text)
    return path


def edit(value: str | int | float | bool | None, at: datetime = T0) -> PendingConfigEdit:
    return PendingConfigEdit(value=value, recorded_at=at)


class TestLoad:
    def test_missing_file_has_no_edits_and_logs_nothing(self, store: PendingConfigEdits) -> None:
        with capture_logs() as logs:
            assert store.edits == {}
        assert logs == []

    @pytest.mark.parametrize("text", ["", "not json", "[]", '{"edits": 5}'])
    def test_bad_file_has_no_edits_and_warns(self, state_dir: Path, text: str) -> None:
        path = write_state(state_dir, text)
        with capture_logs() as logs:
            store = PendingConfigEdits(state_dir)
            assert store.edits == {}
        warnings = [log for log in logs if log["event"] == "pending_config_edits_unreadable"]
        assert len(warnings) == 1
        assert warnings[0]["log_level"] == "warning"
        assert "error_type" in warnings[0]
        # The bad file is left where it is
        assert path.read_text() == text

    def test_unknown_key_is_dropped_with_a_warning(self, state_dir: Path) -> None:
        recorded = {"value": 42421, "recorded_at": "2026-11-19T12:00:00Z"}
        write_state(state_dir, json.dumps({"edits": {"Port": recorded, "NotASetting": recorded}}))
        with capture_logs() as logs:
            edits = PendingConfigEdits(state_dir).edits
        assert list(edits) == ["Port"]
        unknown = [log for log in logs if log["event"] == "pending_config_edit_unknown_key"]
        assert len(unknown) == 1
        assert unknown[0]["key"] == "NotASetting"
        assert unknown[0]["log_level"] == "warning"

    def test_construction_reads_nothing(self, state_dir: Path) -> None:
        """Controller decision (judgement call 1): the file is read on first use only."""
        write_state(state_dir, "not json")
        with capture_logs() as logs:
            store = PendingConfigEdits(state_dir)
        assert logs == []
        with capture_logs() as logs:
            assert store.edits == {}
        assert [log["event"] for log in logs] == ["pending_config_edits_unreadable"]

    def test_file_is_read_once(self, state_dir: Path) -> None:
        write_state(state_dir, "not json")
        store = PendingConfigEdits(state_dir)
        with capture_logs() as logs:
            assert store.edits == {}
            assert store.edits == {}
        assert len(logs) == 1


class TestOwner:
    def test_server_service_construction_reads_no_state_file(self, tmp_path: Path) -> None:
        """Controller decision: building the owner (dev/ in `just test-api`) reads nothing."""
        settings = Settings(data_dir=tmp_path / "data")
        path = write_state(settings.state_dir, "not json")
        with capture_logs() as logs:
            service = ServerService(settings)
        assert not [log for log in logs if str(log["event"]).startswith("pending_config_edit")]
        with capture_logs() as logs:
            assert service.pending_config_edits.edits == {}
        assert [log["event"] for log in logs] == ["pending_config_edits_unreadable"]
        assert service.pending_config_edits.path == path

    def test_server_service_keeps_one_store(self, tmp_path: Path) -> None:
        service = ServerService(Settings(data_dir=tmp_path / "data"))
        assert service.pending_config_edits is service.pending_config_edits


class TestRecord:
    def test_record_writes_the_file(self, store: PendingConfigEdits, state_dir: Path) -> None:
        with capture_logs() as logs:
            store.record("Port", 42421)
        raw = json.loads((state_dir / PENDING_CONFIG_EDITS_FILENAME).read_text())
        assert raw["edits"]["Port"]["value"] == 42421
        assert datetime.fromisoformat(raw["edits"]["Port"]["recorded_at"]) == T0
        assert logs == [
            {"event": "pending_config_edit_recorded", "key": "Port", "log_level": "info"}
        ]

    def test_a_new_instance_loads_it_as_int(
        self, store: PendingConfigEdits, state_dir: Path
    ) -> None:
        store.record("Port", 42421)
        loaded = PendingConfigEdits(state_dir).edits
        assert loaded["Port"].value == 42421
        assert type(loaded["Port"].value) is int
        assert loaded["Port"].recorded_at == T0

    def test_record_again_replaces(
        self, store: PendingConfigEdits, state_dir: Path, clock: Clock
    ) -> None:
        store.record("Port", 42421)
        clock.now = T1
        store.record("Port", 42422)
        assert store.edits == {"Port": edit(42422, T1)}
        assert PendingConfigEdits(state_dir).edits == {"Port": edit(42422, T1)}

    def test_none_round_trips(self, store: PendingConfigEdits, state_dir: Path) -> None:
        store.record("Ip", None)
        assert PendingConfigEdits(state_dir).edits == {"Ip": edit(None)}

    def test_bool_stays_bool(self, store: PendingConfigEdits, state_dir: Path) -> None:
        store.record("AllowPvP", True)
        loaded = PendingConfigEdits(state_dir).edits
        assert type(loaded["AllowPvP"].value) is bool

    def test_edits_is_a_copy(self, store: PendingConfigEdits) -> None:
        store.record("Port", 42421)
        copy = store.edits
        copy.clear()
        assert "Port" in store.edits


class TestSave:
    def test_no_temp_file_is_left(self, store: PendingConfigEdits, state_dir: Path) -> None:
        store.record("Port", 42421)
        assert sorted(p.name for p in state_dir.iterdir()) == [PENDING_CONFIG_EDITS_FILENAME]

    def test_failed_save_logs_and_keeps_the_edit(
        self, store: PendingConfigEdits, monkeypatch: pytest.MonkeyPatch, state_dir: Path
    ) -> None:
        def failing_rename(self: Path, target: Path) -> Path:
            raise OSError(28, "No space left on device", str(self))

        monkeypatch.setattr(Path, "rename", failing_rename)
        with capture_logs() as logs:
            store.record("Port", 42421)
        failed = [log for log in logs if log["event"] == "pending_config_edits_save_failed"]
        assert len(failed) == 1
        assert failed[0] == {
            "event": "pending_config_edits_save_failed",
            "log_level": "error",
            "error_type": "OSError",
            "errno": 28,
            "strerror": "No space left on device",
        }
        assert str(state_dir) not in repr(logs)
        assert store.edits["Port"].value == 42421


class TestDrop:
    def test_drop_removes_and_logs_once(self, store: PendingConfigEdits, state_dir: Path) -> None:
        store.record("Port", 42421)
        store.record("Ip", "10.0.0.1")
        with capture_logs() as logs:
            store.drop(["Port", "Ip", "ServerName"], "changed_again")
        assert store.edits == {}
        assert logs == [
            {
                "event": "pending_config_edits_dropped",
                "keys": ["Port", "Ip"],
                "reason": "changed_again",
                "log_level": "info",
            }
        ]
        raw = json.loads((state_dir / PENDING_CONFIG_EDITS_FILENAME).read_text())
        assert raw == {"edits": {}}

    def test_dropping_an_absent_key_logs_and_writes_nothing(
        self, store: PendingConfigEdits, state_dir: Path
    ) -> None:
        with capture_logs() as logs:
            store.drop(["Port"], "changed_again")
        assert logs == []
        assert not (state_dir / PENDING_CONFIG_EDITS_FILENAME).exists()


class TestDropIfUnchanged:
    def test_same_edit_is_dropped(self, store: PendingConfigEdits) -> None:
        store.record("Port", 42421)
        snapshot = store.edits
        with capture_logs() as logs:
            store.drop_if_unchanged(snapshot, "started")
        assert store.edits == {}
        assert logs[0]["keys"] == ["Port"]
        assert logs[0]["reason"] == "started"

    def test_edit_replaced_after_the_snapshot_is_kept(
        self, store: PendingConfigEdits, clock: Clock
    ) -> None:
        store.record("Port", 42421)
        snapshot = store.edits
        clock.now = T1
        store.record("Port", 42421)
        store.drop_if_unchanged(snapshot, "started")
        assert store.edits == {"Port": edit(42421, T1)}

    def test_key_dropped_after_the_snapshot_stays_dropped(self, store: PendingConfigEdits) -> None:
        store.record("Port", 42421)
        snapshot = store.edits
        store.drop(["Port"], "changed_again")
        with capture_logs() as logs:
            store.drop_if_unchanged(snapshot, "started")
        assert store.edits == {}
        assert logs == []


class TestReapplyEdits:
    @pytest.fixture
    def config_path(self, tmp_path: Path) -> Path:
        path = tmp_path / "serverconfig.json"
        path.write_text(json.dumps({"Port": 42420, "ServerName": "x"}, indent=2))
        return path

    def test_empty_edits_touch_nothing(self, config_path: Path) -> None:
        before = config_path.stat().st_mtime_ns
        assert reapply_edits(config_path, {}) == []
        assert config_path.stat().st_mtime_ns == before

    def test_missing_config_is_not_created(self, tmp_path: Path) -> None:
        path = tmp_path / "serverconfig.json"
        assert reapply_edits(path, {"Port": edit(42421)}) == []
        assert not path.exists()

    def test_differing_value_is_written(self, config_path: Path) -> None:
        assert reapply_edits(config_path, {"Port": edit(42421)}) == ["Port"]
        assert json.loads(config_path.read_text()) == {"Port": 42421, "ServerName": "x"}
        assert sorted(p.name for p in config_path.parent.iterdir()) == ["serverconfig.json"]

    def test_equal_values_write_nothing(self, config_path: Path) -> None:
        before = config_path.stat().st_mtime_ns
        assert reapply_edits(config_path, {"Port": edit(42420)}) == []
        assert config_path.stat().st_mtime_ns == before

    def test_absent_key_is_added(self, config_path: Path) -> None:
        assert reapply_edits(config_path, {"Ip": edit(None)}) == ["Ip"]
        assert json.loads(config_path.read_text())["Ip"] is None

    @pytest.mark.parametrize("text", ["[]", "not json"])
    def test_config_that_is_not_an_object_raises_value_error(
        self, config_path: Path, text: str
    ) -> None:
        config_path.write_text(text)
        with pytest.raises(ValueError):
            reapply_edits(config_path, {"Port": edit(42421)})

    def test_config_path_that_is_a_directory_raises_os_error(self, tmp_path: Path) -> None:
        path = tmp_path / "serverconfig.json"
        path.mkdir()
        with pytest.raises(OSError):
            reapply_edits(path, {"Port": edit(42421)})

    def test_reads_no_environment(self, config_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VS_CFG_SERVER_PORT", "42420")
        assert reapply_edits(config_path, {"Port": edit(42421)}) == ["Port"]
        assert json.loads(config_path.read_text())["Port"] == 42421
