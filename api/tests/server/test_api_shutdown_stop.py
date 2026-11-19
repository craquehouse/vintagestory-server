"""The API's shutdown stops a running game through the normal stop (Story 22.8, ADR-16).

When the container stops, uvicorn runs the lifespan shutdown; the game must be stopped
the normal way first (SIGTERM, so it saves the world; a kill after 8 seconds) and no
start may happen once the shutdown has begun.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from structlog.testing import capture_logs

from vintagestory_api.config import Settings
from vintagestory_api.jobs.scheduled_restart import run_restart_sequence
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import ServerState
from vintagestory_api.services import mods as mods_module
from vintagestory_api.services import server as server_module
from vintagestory_api.services.server import (
    SHUTDOWN_STOP_TIMEOUT_SECONDS,
    ServerService,
    stop_game_server_for_api_shutdown,
)

from .test_pending_config_edits_lifecycle import (
    FakeGameProcess,
    Spawner,
    events,
    game_writes,
    port_in,
    run_until,
)


@pytest.fixture(autouse=True)
def no_real_mod_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fresh shared restart flag, and no mod service built from Settings() (dev/)."""
    monkeypatch.setattr(mods_module, "_restart_state", None)
    monkeypatch.setattr(mods_module, "_mod_service", MagicMock())
    # get_server_status reads the disk space through Settings() from the environment
    monkeypatch.setattr("vintagestory_api.routers.health.get_disk_space_data", lambda: None)


@pytest.fixture
def config_path(installed_settings: Settings) -> Path:
    path = installed_settings.serverdata_dir / "serverconfig.json"
    path.write_text(json.dumps({"Port": 42420, "ServerName": "x"}, indent=2))
    return path


@pytest.fixture
def spawner(config_path: Path, monkeypatch: pytest.MonkeyPatch) -> Spawner:
    spawner = Spawner(config_path)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawner)
    return spawner


@pytest.fixture
async def running(installed_settings: Settings, spawner: Spawner) -> ServerService:
    """A service whose game (the spawner's fake) runs."""
    service = ServerService(installed_settings)
    await service.start_server()
    return service


def event_names(logs: Sequence[Mapping[str, object]]) -> list[object]:
    return [log["event"] for log in logs]


def state_of(service: ServerService) -> ServerState:
    return service.get_server_status().state


def fail_if_built(*args: object, **kwargs: object) -> ServerService:
    raise AssertionError("no ServerService may be built at shutdown")


class TestStopForApiShutdown:
    @pytest.mark.asyncio
    async def test_a_running_game_is_stopped_the_normal_way(
        self, running: ServerService, spawner: Spawner
    ) -> None:
        """AC 1."""
        with capture_logs() as logs:
            await running.stop_for_api_shutdown()

        assert spawner.processes[0].returncode == 0
        assert state_of(running) == ServerState.INSTALLED
        names = [
            name
            for name in event_names(logs)
            if name
            in (
                "api_shutdown_stopping_game",
                "stopping_server",
                "server_stopped_gracefully",
                "api_shutdown_game_stopped",
            )
        ]
        assert names == [
            "api_shutdown_stopping_game",
            "stopping_server",
            "server_stopped_gracefully",
            "api_shutdown_game_stopped",
        ]
        assert events(logs, "api_shutdown_stopping_game")[0]["timeout"] == 8.0
        assert events(logs, "stopping_server")[0]["timeout"] == 8.0
        assert isinstance(events(logs, "api_shutdown_game_stopped")[0]["seconds"], float)

    def test_the_shutdown_timeout_is_8_seconds(self) -> None:
        assert SHUTDOWN_STOP_TIMEOUT_SECONDS == 8.0

    @pytest.mark.asyncio
    async def test_a_game_that_ignores_sigterm_is_killed(
        self, installed_settings: Settings, spawner: Spawner
    ) -> None:
        """AC 3."""
        spawner.ignore_sigterm = True
        service = ServerService(installed_settings)
        await service.start_server()

        with capture_logs() as logs:
            await service.stop_for_api_shutdown(timeout=0.01)

        assert spawner.processes[0].returncode == -9
        names = event_names(logs)
        assert names.index("server_stop_timeout") < names.index("server_killed")
        assert names.index("server_killed") < names.index("api_shutdown_game_stopped")
        assert state_of(service) == ServerState.INSTALLED

    @pytest.mark.asyncio
    async def test_no_game_started_stops_nothing(
        self, installed_settings: Settings, spawner: Spawner
    ) -> None:
        """AC 2."""
        service = ServerService(installed_settings)

        with capture_logs() as logs:
            await service.stop_for_api_shutdown()

        assert events(logs, "api_shutdown_stopping_game") == []
        assert events(logs, "stopping_server") == []
        assert len(events(logs, "api_shutdown_game_not_running")) == 1

    @pytest.mark.asyncio
    async def test_a_game_that_exited_by_itself_is_not_signalled(
        self, running: ServerService, spawner: Spawner
    ) -> None:
        """AC 2."""
        process = spawner.processes[0]
        signals: list[int] = []
        process.on_signal = signals.append
        process.exit(1)
        await run_until(lambda: state_of(running) == ServerState.INSTALLED)

        with capture_logs() as logs:
            await running.stop_for_api_shutdown()

        assert signals == []
        assert events(logs, "api_shutdown_stopping_game") == []
        assert events(logs, "stopping_server") == []
        assert len(events(logs, "api_shutdown_game_not_running")) == 1

    @pytest.mark.asyncio
    async def test_no_start_after_the_shutdown_began(
        self, running: ServerService, spawner: Spawner, config_path: Path
    ) -> None:
        """AC 4: refused before the state, the template step and the 22.7 write-back."""
        await running.stop_for_api_shutdown()
        running.pending_config_edits.record("Port", 42421)
        game_writes(config_path, 42420)
        spawned = len(spawner.processes)

        with capture_logs() as logs, pytest.raises(RuntimeError) as raised:
            await running.start_server()

        assert str(raised.value) == ErrorCode.SERVER_START_FAILED
        [refused] = events(logs, "start_server_failed")
        assert refused["reason"] == "api_shutting_down"
        assert events(logs, "server_start_failed") == []
        assert events(logs, "pending_config_edits_reapplied") == []
        assert len(spawner.processes) == spawned
        assert state_of(running) == ServerState.INSTALLED
        assert port_in(config_path) == 42420

    @pytest.mark.asyncio
    async def test_a_restart_holding_the_lock_does_not_start_again(
        self, running: ServerService, spawner: Spawner
    ) -> None:
        """AC 4: the restart's stop saves the world, its start is refused."""
        process: FakeGameProcess = spawner.processes[0]
        signals: list[int] = []
        process.on_signal = signals.append

        with capture_logs() as logs:
            restart = asyncio.create_task(running.restart_server())
            await run_until(lambda: running.lifecycle_busy and bool(signals))
            shutdown = asyncio.create_task(running.stop_for_api_shutdown())
            for _ in range(5):
                await asyncio.sleep(0)
            process.exit(0)
            restart_result, shutdown_result = await asyncio.gather(
                restart, shutdown, return_exceptions=True
            )

        assert isinstance(restart_result, RuntimeError)
        assert str(restart_result) == ErrorCode.SERVER_START_FAILED
        assert shutdown_result is None
        [refused] = events(logs, "start_server_failed")
        assert refused["reason"] == "api_shutting_down"
        assert len(spawner.processes) == 1
        assert len(events(logs, "api_shutdown_game_not_running")) == 1
        assert state_of(running) == ServerState.INSTALLED

    @pytest.mark.asyncio
    async def test_a_restart_sequence_in_its_warnings_does_not_start_again(
        self, running: ServerService, spawner: Spawner
    ) -> None:
        """AC 4."""
        process = spawner.processes[0]
        wake = asyncio.Event()

        async def sleep(_: float) -> None:
            await wake.wait()

        with capture_logs() as logs:
            sequence = asyncio.create_task(
                run_restart_sequence(
                    "04:00", server=running, still_scheduled=lambda: True, sleep=sleep
                )
            )
            await run_until(
                lambda: any(data.startswith(b"/announce") for data in process.stdin.written)
            )
            await running.stop_for_api_shutdown()
            wake.set()
            outcome = await sequence

        assert outcome == "not_running"
        assert len(spawner.processes) == 1
        [skipped] = events(logs, "scheduled_restart_skipped")
        assert skipped["reason"] == "not_running"

    @pytest.mark.asyncio
    async def test_the_pending_edit_is_written_back_at_the_stop(
        self, running: ServerService, config_path: Path
    ) -> None:
        """AC 6 (Story 22.7's write-back after the exit)."""
        running.pending_config_edits.record("Port", 42421)
        game_writes(config_path, 42420)

        with capture_logs() as logs:
            await running.stop_for_api_shutdown()

        assert port_in(config_path) == 42421
        [reapplied] = events(logs, "pending_config_edits_reapplied")
        assert reapplied["trigger"] == "exit"
        names = event_names(logs)
        assert names.index("pending_config_edits_reapplied") < names.index(
            "api_shutdown_game_stopped"
        )
        # Only a start drops it
        assert running.pending_config_edits.edits["Port"].value == 42421

    @pytest.mark.asyncio
    async def test_a_failed_stop_is_logged_and_does_not_raise(
        self, running: ServerService, spawner: Spawner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC 5."""

        async def failing_stop(timeout: float) -> None:
            raise RuntimeError(ErrorCode.SERVER_STOP_FAILED)

        monkeypatch.setattr(running, "_stop_server_locked", failing_stop)

        with capture_logs() as logs:
            await running.stop_for_api_shutdown()

        [failed] = events(logs, "api_shutdown_game_stop_failed")
        assert failed["log_level"] == "error"
        assert failed["error_code"] == ErrorCode.SERVER_STOP_FAILED
        assert events(logs, "api_shutdown_game_stopped") == []

        spawner.processes[0].exit(0)
        await run_until(lambda: state_of(running) == ServerState.INSTALLED)


class TestStopGameServerForApiShutdown:
    @pytest.mark.asyncio
    async def test_no_service_builds_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC 2: no Settings() read, no state file."""
        monkeypatch.setattr(server_module, "_server_service", None)
        monkeypatch.setattr(server_module, "ServerService", fail_if_built)

        with capture_logs() as logs:
            await stop_game_server_for_api_shutdown()

        # fail_if_built would have raised; nothing was stopped or looked at
        assert logs == []

    @pytest.mark.asyncio
    async def test_the_running_singleton_is_stopped_with_the_8_second_timeout(
        self, running: ServerService, spawner: Spawner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC 1 and 3."""
        monkeypatch.setattr(server_module, "_server_service", running)

        with capture_logs() as logs:
            await stop_game_server_for_api_shutdown()

        assert spawner.processes[0].returncode == 0
        assert state_of(running) == ServerState.INSTALLED
        assert events(logs, "api_shutdown_stopping_game")[0]["timeout"] == 8.0
