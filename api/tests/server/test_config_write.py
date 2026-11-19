"""Tests for ServerService.config_write (Story 23.4, Epic 23 ADR-4 decision 4).

A config file is written only while no game process lives and no lifecycle operation
holds its lock; the save holds the lifecycle lock, so a start waits for it.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from vintagestory_api.models.server import LifecycleAction, LifecycleResponse, ServerState
from vintagestory_api.services.server import GameServerNotStoppedError, ServerService


def _running_process() -> MagicMock:
    process = MagicMock()
    process.returncode = None
    return process


class TestConfigWrite:
    async def test_enters_when_stopped_and_holds_the_lifecycle_lock(
        self, server_service: ServerService
    ) -> None:
        async with server_service.config_write():
            assert server_service._lifecycle_lock.locked()

        assert not server_service._lifecycle_lock.locked()

    async def test_running_process_is_refused(self, server_service: ServerService) -> None:
        server_service._process = _running_process()
        server_service._server_state = ServerState.RUNNING

        with pytest.raises(GameServerNotStoppedError) as exc_info:
            async with server_service.config_write():
                pytest.fail("entered while the game runs")

        assert exc_info.value.reason == "running"
        assert not server_service._lifecycle_lock.locked()

    @pytest.mark.parametrize("state", [ServerState.STARTING, ServerState.STOPPING])
    async def test_transitional_state_is_refused(
        self, server_service: ServerService, state: ServerState
    ) -> None:
        server_service._server_state = state

        with pytest.raises(GameServerNotStoppedError) as exc_info:
            async with server_service.config_write():
                pytest.fail("entered while the game starts or stops")

        assert exc_info.value.reason == "running"

    async def test_held_lifecycle_lock_is_busy_without_waiting(
        self, server_service: ServerService
    ) -> None:
        async with server_service._lifecycle_lock:
            with pytest.raises(GameServerNotStoppedError) as exc_info:
                async with server_service.config_write():
                    pytest.fail("entered while a lifecycle operation runs")

        assert exc_info.value.reason == "busy"

    async def test_held_install_lock_is_busy(self, server_service: ServerService) -> None:
        async with server_service._install_lock:
            with pytest.raises(GameServerNotStoppedError) as exc_info:
                async with server_service.config_write():
                    pytest.fail("entered while an install runs")

        assert exc_info.value.reason == "busy"

    async def test_a_start_waits_for_the_save(
        self, server_service: ServerService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ADR-9 decision 2: a start requested during a save begins after it."""
        events: list[str] = []

        async def fake_start_locked() -> LifecycleResponse:
            events.append("start")
            return LifecycleResponse(
                action=LifecycleAction.START,
                previous_state=ServerState.INSTALLED,
                new_state=ServerState.RUNNING,
            )

        monkeypatch.setattr(server_service, "_start_server_locked", fake_start_locked)

        async with server_service.config_write():
            start = asyncio.create_task(server_service.start_server())
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            events.append("write")

        await start
        assert events == ["write", "start"]
