"""Pending restart-required edits are written back at exits and starts (Story 22.7, ADR-15).

The game rewrites serverconfig.json with its own values after a live change; these tests
simulate that write and check that the saved edit is in the file again after the exit,
before every spawn and at API start, and that it is dropped once a start has loaded it.
"""

from __future__ import annotations

import asyncio
import json
import signal
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from structlog.testing import capture_logs

from vintagestory_api import jobs as jobs_module
from vintagestory_api import main as main_module
from vintagestory_api.config import Settings
from vintagestory_api.jobs.scheduled_restart import run_restart_sequence
from vintagestory_api.models.server import ServerState
from vintagestory_api.services import mods as mods_module
from vintagestory_api.services import server as server_module
from vintagestory_api.services.mods import get_restart_state
from vintagestory_api.services.pending_config_edits import PENDING_CONFIG_EDITS_FILENAME
from vintagestory_api.services.server import (
    ServerService,
    reapply_pending_config_edits_at_api_start,
)


class _EmptyStream:
    """stdout/stderr that are at EOF at once."""

    async def readline(self) -> bytes:
        return b""


class _FakeStdin:
    def __init__(self) -> None:
        self.written: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        return None


class FakeGameProcess:
    """A game process that stays alive until the test (or a signal) ends it."""

    def __init__(self, *, ignore_sigterm: bool = False) -> None:
        self.pid = 4242
        self.returncode: int | None = None
        self.stdin = _FakeStdin()
        self.stdout = _EmptyStream()
        self.stderr = _EmptyStream()
        self.ignore_sigterm = ignore_sigterm
        self.on_signal: Callable[[int], None] | None = None
        self._exited = asyncio.Event()

    def exit(self, code: int) -> None:
        self.returncode = code
        self._exited.set()

    async def wait(self) -> int:
        await self._exited.wait()
        return self.returncode if self.returncode is not None else 0

    def send_signal(self, sig: int) -> None:
        if self.on_signal is not None:
            self.on_signal(sig)
            return
        if sig == signal.SIGTERM and not self.ignore_sigterm:
            self.exit(0)

    def kill(self) -> None:
        self.exit(-9)


class Spawner:
    """Stands in for asyncio.create_subprocess_exec; records the Port each spawn saw."""

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.ports_seen: list[object] = []
        self.processes: list[FakeGameProcess] = []
        self.error: Exception | None = None
        self.on_spawn: Callable[[], None] | None = None
        self.ignore_sigterm = False

    async def __call__(self, *args: object, **kwargs: object) -> FakeGameProcess:
        if self.error is not None:
            raise self.error
        self.ports_seen.append(json.loads(self.config_path.read_text()).get("Port"))
        if self.on_spawn is not None:
            self.on_spawn()
        process = FakeGameProcess(ignore_sigterm=self.ignore_sigterm)
        self.processes.append(process)
        return process


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
def service(installed_settings: Settings, config_path: Path) -> ServerService:
    """An installed, stopped service with a pending Port edit of 42421 (file: 42420)."""
    service = ServerService(installed_settings)
    service.pending_config_edits.record("Port", 42421)
    return service


async def start_with_the_edit_overwritten(service: ServerService, config_path: Path) -> None:
    """Start (which loads the edit), then save Port 42421 while running and let the game
    rewrite the file with 42420 after a live change, as Story 22.3 measured."""
    await service.start_server()
    service.pending_config_edits.record("Port", 42421)
    game_writes(config_path, 42421)
    game_writes(config_path, 42420)


def port_in(config_path: Path) -> object:
    return json.loads(config_path.read_text()).get("Port")


def game_writes(config_path: Path, port: int = 42420) -> None:
    """The game's own write of its config after a live /serverconfig command."""
    config = json.loads(config_path.read_text())
    config["Port"] = port
    config_path.write_text(json.dumps(config, indent=2))


def events(logs: Sequence[Mapping[str, object]], name: str) -> list[Mapping[str, object]]:
    return [log for log in logs if log["event"] == name]


def stored_edits(settings: Settings) -> object:
    return json.loads((settings.state_dir / PENDING_CONFIG_EDITS_FILENAME).read_text())


async def run_until(condition: Callable[[], bool]) -> None:
    for _ in range(100):
        if condition():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition not reached")


class TestExit:
    @pytest.mark.asyncio
    async def test_stop_writes_the_edit_back(
        self, service: ServerService, spawner: Spawner, config_path: Path
    ) -> None:
        """AC 1."""
        await start_with_the_edit_overwritten(service, config_path)

        with capture_logs() as logs:
            await service.stop_server()

        assert port_in(config_path) == 42421
        [line] = events(logs, "pending_config_edits_reapplied")
        assert line["keys"] == ["Port"]
        assert line["trigger"] == "exit"
        assert line["log_level"] == "info"
        # Pending until the next start has loaded it
        assert service.pending_config_edits.edits["Port"].value == 42421

    @pytest.mark.asyncio
    async def test_stop_then_start_drops_the_edit(
        self,
        service: ServerService,
        spawner: Spawner,
        config_path: Path,
        installed_settings: Settings,
    ) -> None:
        """AC 1."""
        await start_with_the_edit_overwritten(service, config_path)
        await service.stop_server()

        with capture_logs() as logs:
            await service.start_server()

        assert spawner.ports_seen[-1] == 42421
        assert service.pending_config_edits.edits == {}
        [dropped] = events(logs, "pending_config_edits_dropped")
        assert dropped["reason"] == "started"
        assert dropped["keys"] == ["Port"]
        assert stored_edits(installed_settings) == {"edits": {}}
        await service.stop_server()

    @pytest.mark.asyncio
    async def test_killed_process_writes_the_edit_back(
        self, service: ServerService, spawner: Spawner, config_path: Path
    ) -> None:
        spawner.ignore_sigterm = True
        await start_with_the_edit_overwritten(service, config_path)

        with capture_logs() as logs:
            await service.stop_server(timeout=0.01)

        assert spawner.processes[0].returncode == -9
        assert port_in(config_path) == 42421
        assert events(logs, "pending_config_edits_reapplied")[0]["trigger"] == "exit"

    @pytest.mark.asyncio
    async def test_exit_by_itself_writes_the_edit_back(
        self, service: ServerService, spawner: Spawner, config_path: Path
    ) -> None:
        """AC 2: a crash or /stop."""
        await start_with_the_edit_overwritten(service, config_path)

        with capture_logs() as logs:
            spawner.processes[0].exit(1)
            await run_until(lambda: service.get_server_status().state == ServerState.INSTALLED)
            await run_until(lambda: port_in(config_path) == 42421)

        [line] = events(logs, "pending_config_edits_reapplied")
        assert line["trigger"] == "exit"

    @pytest.mark.asyncio
    async def test_failed_stop_of_an_exited_process_writes_the_edit_back(
        self, service: ServerService, spawner: Spawner, config_path: Path
    ) -> None:
        """AC 2, "ADR against the code" 2."""
        await start_with_the_edit_overwritten(service, config_path)
        process = spawner.processes[0]

        def exited_already(_: int) -> None:
            process.returncode = 3
            raise ProcessLookupError("process already exited")

        process.on_signal = exited_already

        with capture_logs() as logs, pytest.raises(RuntimeError):
            await service.stop_server()

        assert service.get_server_status().state == ServerState.INSTALLED
        assert port_in(config_path) == 42421
        assert events(logs, "pending_config_edits_reapplied")[0]["trigger"] == "exit"

    @pytest.mark.asyncio
    async def test_missing_config_at_exit_is_not_created(
        self, service: ServerService, spawner: Spawner, config_path: Path
    ) -> None:
        await start_with_the_edit_overwritten(service, config_path)
        config_path.unlink()

        await service.stop_server()

        assert not config_path.exists()
        assert service.pending_config_edits.edits["Port"].value == 42421


class TestBeforeSpawn:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", ["start", "restart"])
    async def test_a_fresh_service_writes_the_edit_before_the_spawn(
        self,
        service: ServerService,
        spawner: Spawner,
        config_path: Path,
        installed_settings: Settings,
        action: str,
    ) -> None:
        """No exit was seen (the container stopped): the start writes it back."""
        fresh = ServerService(installed_settings)

        with capture_logs() as logs:
            if action == "start":
                await fresh.start_server()
            else:
                await fresh.restart_server()

        assert spawner.ports_seen == [42421]
        [line] = events(logs, "pending_config_edits_reapplied")
        assert line["trigger"] == "start"
        assert fresh.pending_config_edits.edits == {}
        await fresh.stop_server()

    @pytest.mark.asyncio
    async def test_scheduled_restart_starts_with_the_edit(
        self, service: ServerService, spawner: Spawner, config_path: Path
    ) -> None:
        """AC 2: a scheduled restart goes through restart_server()."""
        await start_with_the_edit_overwritten(service, config_path)

        async def no_sleep(_: float) -> None:
            return None

        await run_restart_sequence(
            "04:00", server=service, still_scheduled=lambda: True, sleep=no_sleep
        )

        assert len(spawner.processes) == 2
        assert spawner.ports_seen[-1] == 42421
        assert service.pending_config_edits.edits == {}
        await service.stop_server()

    @pytest.mark.asyncio
    async def test_equal_values_write_nothing(
        self, service: ServerService, spawner: Spawner, config_path: Path
    ) -> None:
        game_writes(config_path, 42421)
        before = config_path.stat().st_mtime_ns

        with capture_logs() as logs:
            await service.start_server()

        assert config_path.stat().st_mtime_ns == before
        assert events(logs, "pending_config_edits_reapplied") == []
        assert service.pending_config_edits.edits == {}
        await service.stop_server()

    @pytest.mark.asyncio
    async def test_a_failed_spawn_keeps_the_edit_and_the_flag(
        self, service: ServerService, spawner: Spawner
    ) -> None:
        get_restart_state().require_restart("Setting 'Port' changed - requires server restart")
        spawner.error = OSError("Cannot spawn process")

        with capture_logs() as logs, pytest.raises(RuntimeError):
            await service.start_server()

        assert service.pending_config_edits.edits["Port"].value == 42421
        assert events(logs, "pending_config_edits_dropped") == []
        assert get_restart_state().pending_restart

    @pytest.mark.asyncio
    async def test_an_edit_recorded_during_the_spawn_is_kept(
        self, service: ServerService, spawner: Spawner
    ) -> None:
        """ "ADR against the code" 3: the drop is by identity."""
        spawner.on_spawn = lambda: service.pending_config_edits.record("Port", 42424)

        await service.start_server()

        assert service.pending_config_edits.edits["Port"].value == 42424
        await service.stop_server()


class TestFailureRule:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("broken", ["directory", "invalid_json"])
    @pytest.mark.parametrize("action", ["start", "restart"])
    async def test_an_unwritable_config_keeps_the_edit_and_the_flag(
        self,
        service: ServerService,
        spawner: Spawner,
        config_path: Path,
        broken: str,
        action: str,
    ) -> None:
        """AC 6."""
        config_path.unlink()
        if broken == "directory":
            config_path.mkdir()
        else:
            config_path.write_text("not json")
        # The fake spawn reads its Port from a readable file
        spawner.config_path = config_path.parent / "spawn-view.json"
        spawner.config_path.write_text("{}")

        with capture_logs() as logs:
            if action == "start":
                await service.start_server()
            else:
                await service.restart_server()

        [failed] = events(logs, "pending_config_edits_reapply_failed")
        assert failed["log_level"] == "error"
        assert failed["trigger"] == "start"
        assert failed["keys"] == ["Port"]
        assert str(config_path) not in repr(failed)
        assert "42421" not in repr(failed)
        assert service.pending_config_edits.edits["Port"].value == 42421
        assert events(logs, "pending_config_edits_dropped") == []
        state = get_restart_state()
        assert state.pending_restart
        assert any("Port" in reason for reason in state.pending_changes)
        await service.stop_server()


class TestApiStart:
    @pytest.mark.asyncio
    async def test_api_start_writes_the_edit_and_starts_nothing(
        self,
        service: ServerService,
        spawner: Spawner,
        config_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC 3."""
        monkeypatch.setattr(server_module, "get_server_service", lambda: service)

        with capture_logs() as logs:
            reapply_pending_config_edits_at_api_start()

        assert port_in(config_path) == 42421
        [line] = events(logs, "pending_config_edits_reapplied")
        assert line["trigger"] == "api_start"
        assert spawner.processes == []
        assert service.pending_config_edits.edits["Port"].value == 42421

    @pytest.mark.asyncio
    async def test_api_start_does_nothing_while_a_process_lives(
        self, service: ServerService, spawner: Spawner, config_path: Path
    ) -> None:
        await start_with_the_edit_overwritten(service, config_path)

        service.reapply_pending_config_edits_at_api_start()

        assert port_in(config_path) == 42420
        await service.stop_server()

    @pytest.mark.asyncio
    async def test_auto_start_starts_with_the_edit(
        self,
        service: ServerService,
        spawner: Spawner,
        installed_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC 2 and 3: the API start writes it back, the auto-start finds it equal."""
        (installed_settings.state_dir).mkdir(parents=True, exist_ok=True)
        (installed_settings.state_dir / "api-settings.json").write_text(
            json.dumps({"auto_start_server": True})
        )
        monkeypatch.setattr(server_module, "get_server_service", lambda: service)
        monkeypatch.setattr(
            main_module,
            "reapply_pending_config_edits_at_api_start",
            reapply_pending_config_edits_at_api_start,
        )
        scheduler = MagicMock()

        with (
            capture_logs() as logs,
            patch("vintagestory_api.main.initialize_debug_state"),
            patch("vintagestory_api.main.SchedulerService", return_value=scheduler),
            patch.object(jobs_module, "register_default_jobs"),
            patch("vintagestory_api.services.mods.close_mod_service", new_callable=AsyncMock),
        ):
            async with main_module.lifespan_for(installed_settings)(FastAPI()):
                pass

        reapplied = events(logs, "pending_config_edits_reapplied")
        assert [line["trigger"] for line in reapplied] == ["api_start"]
        assert spawner.ports_seen == [42421]
        assert service.pending_config_edits.edits == {}
        await service.stop_server()
