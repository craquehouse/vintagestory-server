"""Tests for the scheduled restart sequence (Story 22.3, Epic 22 ADR-6).

No test sleeps for real (FakeSleep) and none restarts a real game process: the sequence
runs against FakeServer, or against a temp-dir ServerService whose stop and start are
replaced.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from structlog.testing import capture_logs

import vintagestory_api.services.mods as mods_module
from vintagestory_api.config import Settings
from vintagestory_api.jobs.scheduled_restart import (
    RESTART_JOB_PREFIX,
    WARNING_LEAD_MINUTES,
    WARNINGS,
    restart_job_id,
    run_restart_sequence,
    scheduled_restart,
    warning_start,
)
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.server import ServerService

RESTART_TIME = "04:00"
ANNOUNCE_15 = "/announce Server restarts in 15 minutes"
ANNOUNCE_5 = "/announce Server restarts in 5 minutes"
ANNOUNCE_1 = "/announce Server restarts in 1 minute"

Event = str | float


class FakeServer:
    """What the sequence needs from ServerService, as plain attributes."""

    def __init__(self, events: list[Event]) -> None:
        self.events = events
        self.game_running = True
        self.lifecycle_busy = False
        self.players_online: int | None = 3
        self.accept_commands = True
        self.command_error: Exception | None = None
        self.restart_error: Exception | None = None
        self.sent: list[str] = []
        self.restarts = 0

    async def send_command(self, command: str) -> bool:
        if self.command_error is not None:
            raise self.command_error
        if self.accept_commands:
            self.sent.append(command)
            self.events.append(command)
        return self.accept_commands

    async def restart_server(self, timeout: float = 10.0) -> object:
        self.restarts += 1
        self.events.append("restart")
        if self.restart_error is not None:
            raise self.restart_error
        return None


class FakeSleep:
    """Records each wait; hooks[n] runs during the n-th wait (0 is the first)."""

    def __init__(
        self, events: list[Event], hooks: dict[int, Callable[[], None]] | None = None
    ) -> None:
        self.events = events
        self.hooks = hooks or {}
        self.calls = 0

    async def __call__(self, seconds: float) -> None:
        self.events.append(seconds)
        hook = self.hooks.get(self.calls)
        self.calls += 1
        if hook is not None:
            hook()


class Scheduled:
    """still_scheduled, switchable from a hook."""

    def __init__(self) -> None:
        self.value = True

    def __call__(self) -> bool:
        return self.value


def _skips(logs: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    return [log for log in logs if log["event"] == "scheduled_restart_skipped"]


@pytest.fixture
def events() -> list[Event]:
    return []


@pytest.fixture
def server(events: list[Event]) -> FakeServer:
    return FakeServer(events)


class TestHelpers:
    def test_restart_job_id(self) -> None:
        assert restart_job_id("04:00") == "scheduled_restart_0400"
        assert restart_job_id("23:59") == "scheduled_restart_2359"
        assert restart_job_id("04:00").startswith(RESTART_JOB_PREFIX)

    @pytest.mark.parametrize(
        ("restart_time", "expected"),
        [("04:00", (3, 45)), ("00:10", (23, 55)), ("00:15", (0, 0)), ("23:59", (23, 44))],
    )
    def test_warning_start(self, restart_time: str, expected: tuple[int, int]) -> None:
        assert warning_start(restart_time) == expected

    def test_warnings(self) -> None:
        assert [text for _, text, _ in WARNINGS] == [
            "Server restarts in 15 minutes",
            "Server restarts in 5 minutes",
            "Server restarts in 1 minute",
        ]
        assert [minutes for minutes, _, _ in WARNINGS] == [15, 5, 1]
        assert sum(wait for _, _, wait in WARNINGS) == WARNING_LEAD_MINUTES * 60 == 900


class TestHappyPath:
    """AC 5: three warnings, then the restart."""

    async def test_warns_then_restarts(self, server: FakeServer, events: list[Event]) -> None:
        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME,
                server=server,
                still_scheduled=lambda: True,
                sleep=FakeSleep(events),
            )

        assert outcome == "restarted"
        assert events == [ANNOUNCE_15, 600.0, ANNOUNCE_5, 240.0, ANNOUNCE_1, 60.0, "restart"]
        warnings = [log for log in logs if log["event"] == "scheduled_restart_warning"]
        assert [log["minutes_left"] for log in warnings] == [15, 5, 1]
        assert all(log["restart_time"] == RESTART_TIME for log in warnings)
        restarting = [log for log in logs if log["event"] == "scheduled_restart_restarting"]
        assert restarting == [
            {
                "event": "scheduled_restart_restarting",
                "log_level": "info",
                "restart_time": RESTART_TIME,
                "players_online": 3,
            }
        ]
        done = [log for log in logs if log["event"] == "scheduled_restart_done"]
        assert done == [
            {"event": "scheduled_restart_done", "log_level": "info", "restart_time": RESTART_TIME}
        ]
        assert _skips(logs) == []


class TestNotRunning:
    """AC 6: a stopped game is never started."""

    async def test_stopped_at_the_fire(self, server: FakeServer, events: list[Event]) -> None:
        server.game_running = False
        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME, server=server, still_scheduled=lambda: True, sleep=FakeSleep(events)
            )

        assert outcome == "not_running"
        assert events == []
        assert server.restarts == 0
        assert _skips(logs) == [
            {
                "event": "scheduled_restart_skipped",
                "log_level": "info",
                "restart_time": RESTART_TIME,
                "reason": "not_running",
                "minutes_left": 15,
            }
        ]

    async def test_stopped_during_the_first_wait(
        self, server: FakeServer, events: list[Event]
    ) -> None:
        def stop() -> None:
            server.game_running = False

        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME,
                server=server,
                still_scheduled=lambda: True,
                sleep=FakeSleep(events, {0: stop}),
            )

        assert outcome == "not_running"
        assert server.sent == [ANNOUNCE_15]
        assert server.restarts == 0
        skips = _skips(logs)
        assert len(skips) == 1
        assert skips[0]["reason"] == "not_running"
        assert skips[0]["minutes_left"] == 5

    async def test_stopped_during_the_last_wait(
        self, server: FakeServer, events: list[Event]
    ) -> None:
        def stop() -> None:
            server.game_running = False

        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME,
                server=server,
                still_scheduled=lambda: True,
                sleep=FakeSleep(events, {2: stop}),
            )

        assert outcome == "not_running"
        assert server.sent == [ANNOUNCE_15, ANNOUNCE_5, ANNOUNCE_1]
        assert server.restarts == 0
        skips = _skips(logs)
        assert [(skip["reason"], skip["minutes_left"]) for skip in skips] == [("not_running", 0)]

    async def test_command_not_sent(self, server: FakeServer, events: list[Event]) -> None:
        """send_command returns False when the process ended between the check and the write."""
        server.accept_commands = False
        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME, server=server, still_scheduled=lambda: True, sleep=FakeSleep(events)
            )

        assert outcome == "not_running"
        assert events == []
        assert server.restarts == 0
        assert [(skip["reason"], skip["minutes_left"]) for skip in _skips(logs)] == [
            ("not_running", 15)
        ]
        assert not [log for log in logs if log["event"] == "scheduled_restart_warning"]


class TestBusy:
    """AC 7: a manual operation in progress at the restart skips it, without waiting."""

    async def test_busy_at_the_restart_is_skipped_at_once(
        self, server: FakeServer, events: list[Event]
    ) -> None:
        def busy() -> None:
            server.lifecycle_busy = True

        with capture_logs() as logs:
            outcome = await asyncio.wait_for(
                run_restart_sequence(
                    RESTART_TIME,
                    server=server,
                    still_scheduled=lambda: True,
                    sleep=FakeSleep(events, {2: busy}),
                ),
                timeout=1,
            )

        assert outcome == "lifecycle_busy"
        assert server.restarts == 0
        assert _skips(logs) == [
            {
                "event": "scheduled_restart_skipped",
                "log_level": "warning",
                "restart_time": RESTART_TIME,
                "reason": "lifecycle_busy",
                "minutes_left": 0,
            }
        ]

    async def test_busy_is_checked_before_running(
        self, server: FakeServer, events: list[Event]
    ) -> None:
        """A manual stop in progress: busy and not running together reads as busy."""

        def manual_stop() -> None:
            server.lifecycle_busy = True
            server.game_running = False

        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME,
                server=server,
                still_scheduled=lambda: True,
                sleep=FakeSleep(events, {2: manual_stop}),
            )

        assert outcome == "lifecycle_busy"
        assert server.restarts == 0
        assert [skip["reason"] for skip in _skips(logs)] == ["lifecycle_busy"]

    async def test_busy_during_the_warnings_changes_nothing(
        self, server: FakeServer, events: list[Event]
    ) -> None:
        def busy() -> None:
            server.lifecycle_busy = True

        def idle() -> None:
            server.lifecycle_busy = False

        server.lifecycle_busy = True
        outcome = await run_restart_sequence(
            RESTART_TIME,
            server=server,
            still_scheduled=lambda: True,
            sleep=FakeSleep(events, {0: busy, 2: idle}),
        )

        assert outcome == "restarted"
        assert server.sent == [ANNOUNCE_15, ANNOUNCE_5, ANNOUNCE_1]
        assert server.restarts == 1


class TestCancelled:
    """AC 8: a time removed (its job gone) ends the sequence at its next step."""

    async def test_cancelled_at_the_fire(self, server: FakeServer, events: list[Event]) -> None:
        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME, server=server, still_scheduled=lambda: False, sleep=FakeSleep(events)
            )

        assert outcome == "cancelled"
        assert events == []
        assert [(skip["reason"], skip["minutes_left"]) for skip in _skips(logs)] == [
            ("cancelled", 15)
        ]
        assert _skips(logs)[0]["log_level"] == "info"

    async def test_cancelled_during_the_second_wait(
        self, server: FakeServer, events: list[Event]
    ) -> None:
        scheduled = Scheduled()

        def cancel() -> None:
            scheduled.value = False

        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME,
                server=server,
                still_scheduled=scheduled,
                sleep=FakeSleep(events, {1: cancel}),
            )

        assert outcome == "cancelled"
        assert server.sent == [ANNOUNCE_15, ANNOUNCE_5]
        assert server.restarts == 0
        assert [(skip["reason"], skip["minutes_left"]) for skip in _skips(logs)] == [
            ("cancelled", 1)
        ]

    async def test_cancelled_during_the_last_wait(
        self, server: FakeServer, events: list[Event]
    ) -> None:
        scheduled = Scheduled()

        def cancel() -> None:
            scheduled.value = False

        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME,
                server=server,
                still_scheduled=scheduled,
                sleep=FakeSleep(events, {2: cancel}),
            )

        assert outcome == "cancelled"
        assert server.restarts == 0
        assert [(skip["reason"], skip["minutes_left"]) for skip in _skips(logs)] == [
            ("cancelled", 0)
        ]

    async def test_still_scheduled_throughout(
        self, server: FakeServer, events: list[Event]
    ) -> None:
        outcome = await run_restart_sequence(
            RESTART_TIME, server=server, still_scheduled=Scheduled(), sleep=FakeSleep(events)
        )

        assert outcome == "restarted"
        assert server.restarts == 1


class TestFailure:
    """AC 9: a failed restart is logged, not retried, and nothing else starts the game."""

    async def test_restart_raises_runtime_error(
        self, server: FakeServer, events: list[Event]
    ) -> None:
        server.restart_error = RuntimeError("SERVER_STOP_FAILED")
        with capture_logs() as logs:
            outcome = await run_restart_sequence(
                RESTART_TIME, server=server, still_scheduled=lambda: True, sleep=FakeSleep(events)
            )

        assert outcome == "failed"
        assert server.restarts == 1
        failed = [log for log in logs if log["event"] == "scheduled_restart_failed"]
        assert failed == [
            {
                "event": "scheduled_restart_failed",
                "log_level": "error",
                "restart_time": RESTART_TIME,
                "error_code": "SERVER_STOP_FAILED",
            }
        ]
        assert not [log for log in logs if log["event"] == "scheduled_restart_done"]


class _StubScheduler:
    """Answers get_job like a scheduler that still holds every job; records the ids."""

    def __init__(self, registered: bool = True) -> None:
        self.registered = registered
        self.asked: list[str] = []

    def get_job(self, job_id: str) -> object | None:
        self.asked.append(job_id)
        return object() if self.registered else None


class TestJobFunction:
    """scheduled_restart, the function a restart job runs."""

    async def test_other_errors_reach_safe_job(
        self, server: FakeServer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        server.command_error = OSError("broken pipe")
        monkeypatch.setattr("vintagestory_api.services.server.get_server_service", lambda: server)

        with capture_logs() as logs:
            result = await scheduled_restart(restart_time=RESTART_TIME, scheduler=_StubScheduler())

        assert result is None
        assert server.restarts == 0
        events = [log["event"] for log in logs]
        assert "scheduled_restart_started" in events
        assert "scheduled_restart_failed" in events
        assert "scheduled_restart_completed" not in events
        failed = next(log for log in logs if log["event"] == "scheduled_restart_failed")
        assert failed["log_level"] == "error"
        assert failed["error"] == "broken pipe"

    async def test_job_uses_its_own_id_and_the_server_service(
        self, server: FakeServer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        server.game_running = False
        monkeypatch.setattr("vintagestory_api.services.server.get_server_service", lambda: server)
        scheduler = _StubScheduler()

        with capture_logs() as logs:
            await scheduled_restart(restart_time=RESTART_TIME, scheduler=scheduler)

        assert scheduler.asked == ["scheduled_restart_0400"]
        events = [log["event"] for log in logs]
        assert events == [
            "scheduled_restart_started",
            "scheduled_restart_skipped",
            "scheduled_restart_completed",
        ]

    async def test_a_removed_job_is_cancelled(
        self, server: FakeServer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("vintagestory_api.services.server.get_server_service", lambda: server)

        with capture_logs() as logs:
            await scheduled_restart(
                restart_time=RESTART_TIME, scheduler=_StubScheduler(registered=False)
            )

        assert server.sent == []
        assert [skip["reason"] for skip in _skips(logs)] == ["cancelled"]


# ==============================================================================
# The sequence against a real ServerService (AC 5, pending restart)
# ==============================================================================


class _FakeStdin:
    def __init__(self) -> None:
        self.written: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        return None


class _FakeProcess:
    def __init__(self) -> None:
        self.pid = 4242
        self.returncode: int | None = None
        self.stdin = _FakeStdin()


@pytest.fixture
def installed_service(tmp_path: Path) -> ServerService:
    """A temp-dir ServerService that looks installed (as tests/server/conftest.py)."""
    data_dir = tmp_path / "data"
    (data_dir / "server").mkdir(parents=True)
    (data_dir / "vsmanager").mkdir(parents=True)
    (data_dir / "serverdata").mkdir(parents=True)
    (data_dir / "server" / "VintagestoryServer.dll").touch()
    (data_dir / "server" / "VintagestoryLib.dll").touch()
    (data_dir / "vsmanager" / "current_version").write_text("1.22.3")
    return ServerService(Settings(data_dir=data_dir, api_key_admin="placeholder-admin-key"))


@pytest.fixture
def running_service(
    installed_service: ServerService, monkeypatch: pytest.MonkeyPatch
) -> tuple[ServerService, _FakeProcess, AsyncMock, AsyncMock]:
    """The service with a fake running process, its stop and start replaced, a restart pending."""
    process = _FakeProcess()
    stop = AsyncMock()
    start = AsyncMock()
    monkeypatch.setattr(installed_service, "_process", process)
    monkeypatch.setattr(installed_service, "_server_state", ServerState.RUNNING)
    monkeypatch.setattr(installed_service, "_stop_server_locked", stop)
    monkeypatch.setattr(installed_service, "_start_server_locked", start)
    monkeypatch.setattr(mods_module, "_restart_state", None)
    mods_module.get_restart_state().require_restart("placeholder change")
    return installed_service, process, stop, start


class TestRealServerService:
    async def test_announces_restarts_and_clears_the_pending_restart(
        self,
        running_service: tuple[ServerService, _FakeProcess, AsyncMock, AsyncMock],
        events: list[Event],
    ) -> None:
        service, process, stop, start = running_service

        outcome = await run_restart_sequence(
            RESTART_TIME, server=service, still_scheduled=lambda: True, sleep=FakeSleep(events)
        )

        assert outcome == "restarted"
        assert process.stdin.written == [
            f"{ANNOUNCE_15}\n".encode(),
            f"{ANNOUNCE_5}\n".encode(),
            f"{ANNOUNCE_1}\n".encode(),
        ]
        history = service.console_buffer.get_history()
        for command in (ANNOUNCE_15, ANNOUNCE_5, ANNOUNCE_1):
            assert any(f"[CMD] {command}" in line for line in history)
        stop.assert_awaited_once()
        start.assert_awaited_once()
        assert mods_module.get_restart_state().pending_restart is False

    async def test_lifecycle_lock_held_skips_the_restart(
        self,
        running_service: tuple[ServerService, _FakeProcess, AsyncMock, AsyncMock],
        events: list[Event],
    ) -> None:
        service, _, stop, start = running_service

        with capture_logs() as logs:
            async with service._lifecycle_lock:
                outcome = await asyncio.wait_for(
                    run_restart_sequence(
                        RESTART_TIME,
                        server=service,
                        still_scheduled=lambda: True,
                        sleep=FakeSleep(events),
                    ),
                    timeout=1,
                )

        assert outcome == "lifecycle_busy"
        stop.assert_not_awaited()
        start.assert_not_awaited()
        assert [skip["reason"] for skip in _skips(logs)] == ["lifecycle_busy"]
        assert mods_module.get_restart_state().pending_restart is True

    async def test_manual_stop_in_progress_skips_as_busy(
        self,
        running_service: tuple[ServerService, _FakeProcess, AsyncMock, AsyncMock],
        events: list[Event],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        service, _, stop, start = running_service

        def manual_stop_begins() -> None:
            monkeypatch.setattr(service, "_server_state", ServerState.STOPPING)

        with capture_logs() as logs:
            async with service._lifecycle_lock:
                outcome = await asyncio.wait_for(
                    run_restart_sequence(
                        RESTART_TIME,
                        server=service,
                        still_scheduled=lambda: True,
                        sleep=FakeSleep(events, {2: manual_stop_begins}),
                    ),
                    timeout=1,
                )

        assert outcome == "lifecycle_busy"
        stop.assert_not_awaited()
        start.assert_not_awaited()
        assert [skip["reason"] for skip in _skips(logs)] == ["lifecycle_busy"]
