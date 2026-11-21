"""Entity Spawning replies from the game's console (Story 25.3, Epic 25 ADR-4, ADR-5).

The lines are the game's own, recorded on 1.22.7 in Story 25.3 Task 1.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from vintagestory_api.services.entity_spawning import (
    ENTITY_SPAWNING_FILENAME,
    ENV_VAR,
    EntitySpawningStore,
    EntitySpawningWatcher,
    env_value,
    is_ready_line,
    parse_reply,
    set_command,
)

TS = "21.11.2026 01:32:28"
CURRENT_ON = f"{TS} [Server Notification] Current Entity spawning mode is on"
CURRENT_OFF = f"{TS} [Server Notification] Current Entity spawning mode is off"
SET_OFF = f"{TS} [Server Notification] Entity spawning mode set to off"
SET_ON = f"{TS} [Server Notification] Entity spawning mode set to on"
READY = f"{TS} [Server Event] Dedicated Server now running on Port 42420 and all ips!"
HANDLING = f"{TS} [Server Notification] Handling Console Command /serverconfig entityspawning"
NOW = datetime(2026, 11, 21, 1, 32, 28, tzinfo=UTC)


class FakeGame:
    """`send_command` for the watcher: records commands and answers like the game."""

    def __init__(self, answer: bool = True, accepted: bool = True) -> None:
        self.commands: list[str] = []
        self.answer = answer
        self.accepted = accepted
        self.watcher: EntitySpawningWatcher | None = None
        self.state = True

    async def send(self, command: str) -> bool:
        self.commands.append(command)
        if not self.accepted:
            return False
        if self.answer and self.watcher is not None:
            watcher = self.watcher
            if command == "/serverconfig entityspawning":
                reply = CURRENT_ON if self.state else CURRENT_OFF
            else:
                self.state = command.endswith("true")
                reply = SET_ON if self.state else SET_OFF
            # The game answers after a moment, on the stream reader's side
            asyncio.get_running_loop().call_soon(
                lambda: (watcher.observe(HANDLING), watcher.observe(reply))
            )
        return True


def make(
    tmp_path: Path, game: FakeGame | None = None, *, timeout: float = 0.2
) -> tuple[EntitySpawningWatcher, FakeGame]:
    game = game or FakeGame()
    watcher = EntitySpawningWatcher(tmp_path, game.send, now=lambda: NOW, timeout=timeout)
    game.watcher = watcher
    return watcher, game


# ==============================================================================
# The line patterns (ADR-4 decision 1)
# ==============================================================================


class TestPatterns:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            (CURRENT_ON, ("current", True)),
            (CURRENT_OFF, ("current", False)),
            (SET_OFF, ("set", False)),
            (SET_ON, ("set", True)),
            ("[Server Notification] Current Entity spawning mode is on", ("current", True)),
        ],
    )
    def test_replies(self, line: str, expected: tuple[str, bool]) -> None:
        assert parse_reply(line) == expected

    @pytest.mark.parametrize(
        "line",
        [
            HANDLING,
            f"{TS} [Server Chat] 0 | Bob: [Server Notification] Entity spawning mode set to off",
            f"{TS} [Server Chat] 0 | Bob: Current Entity spawning mode is off",
            f"{TS} [Server Notification] Current Entity spawning mode is maybe",
            f"{TS} [Server Notification] Current Entity spawning mode is on!",
            f"{TS} [Server Notification] Current Max amount of clients is 16",
            f"{TS} [Server Event] Current Entity spawning mode is on",
            "",
        ],
        ids=["handling", "chat-tag", "chat", "word", "suffix", "other-setting", "event", "empty"],
    )
    def test_other_lines_are_not_replies(self, line: str) -> None:
        assert parse_reply(line) is None

    def test_ready_line(self) -> None:
        assert is_ready_line(READY)
        assert is_ready_line("19.11.2026 17:14:19 [Event] Dedicated Server now running on Port 1")
        assert not is_ready_line(f"{TS} [Server Chat] 0 | Bob: Dedicated Server now running on")

    def test_only_true_or_false_is_sent(self) -> None:
        assert set_command(True) == "/serverconfig entityspawning true"
        assert set_command(False) == "/serverconfig entityspawning false"


# ==============================================================================
# The record (ADR-5 decision 1)
# ==============================================================================


class TestStore:
    def test_no_file_is_no_record(self, tmp_path: Path) -> None:
        assert EntitySpawningStore(tmp_path).record is None

    def test_saved_and_read_back(self, tmp_path: Path) -> None:
        EntitySpawningStore(tmp_path, now=lambda: NOW).observe(False, "console")

        record = EntitySpawningStore(tmp_path).record
        assert record is not None
        assert record.value is False
        assert record.observed_at == NOW
        assert record.via == "console"
        assert not (tmp_path / "entity_spawning.tmp").exists()

    @pytest.mark.parametrize("text", ["{not json", '{"value": "yes"}', "[]"])
    def test_a_corrupt_file_is_no_record(self, tmp_path: Path, text: str) -> None:
        (tmp_path / ENTITY_SPAWNING_FILENAME).write_text(text)

        with capture_logs() as logs:
            assert EntitySpawningStore(tmp_path).record is None
        assert [e["event"] for e in logs] == ["entity_spawning_record_unreadable"]

    def test_a_failed_save_keeps_the_value(self, tmp_path: Path) -> None:
        blocked = tmp_path / "state"
        blocked.write_text("a file where the directory should be")
        store = EntitySpawningStore(blocked, now=lambda: NOW)

        with capture_logs() as logs:
            store.observe(True, "query")

        assert store.record is not None and store.record.value is True
        assert any(e["event"] == "entity_spawning_record_save_failed" for e in logs)
        assert str(blocked) not in json.dumps(logs, default=str)


# ==============================================================================
# The watcher (ADR-4)
# ==============================================================================


class TestWatcher:
    async def test_query_reads_the_reply(self, tmp_path: Path) -> None:
        watcher, game = make(tmp_path)

        assert await watcher.query() is True

        assert game.commands == ["/serverconfig entityspawning"]
        assert watcher.record is not None and watcher.record.via == "query"
        assert watcher.seen_since_start

    async def test_set_reads_the_value_the_game_reports(self, tmp_path: Path) -> None:
        watcher, game = make(tmp_path)

        assert await watcher.set(False) is False

        assert game.commands == ["/serverconfig entityspawning false"]
        assert watcher.record is not None
        assert watcher.record.value is False
        assert watcher.record.via == "set"

    async def test_no_reply_is_none_and_keeps_the_record(self, tmp_path: Path) -> None:
        watcher, _ = make(tmp_path, FakeGame(answer=False))
        watcher.observe(CURRENT_ON)

        with capture_logs() as logs:
            assert await watcher.set(False) is None

        assert watcher.record is not None and watcher.record.value is True
        assert [e["event"] for e in logs] == ["entity_spawning_reply_timeout"]

    async def test_a_command_that_cannot_be_sent_is_none(self, tmp_path: Path) -> None:
        watcher, _ = make(tmp_path, FakeGame(accepted=False))

        assert await watcher.query() is None
        assert watcher.record is None

    async def test_a_value_typed_in_the_console_is_recorded(self, tmp_path: Path) -> None:
        watcher, _ = make(tmp_path)

        watcher.observe(HANDLING)
        watcher.observe(SET_OFF)

        assert watcher.record is not None
        assert watcher.record.value is False
        assert watcher.record.via == "console"

    async def test_a_set_waits_for_a_set_reply_not_a_query_reply(self, tmp_path: Path) -> None:
        watcher, _ = make(tmp_path, FakeGame(answer=False), timeout=1.0)
        task = asyncio.create_task(watcher.set(False))
        await asyncio.sleep(0)

        watcher.observe(CURRENT_ON)  # someone's query, interleaved
        await asyncio.sleep(0)
        assert not task.done()
        watcher.observe(SET_OFF)

        assert await task is False

    async def test_reset_ends_a_wait_and_forgets_readiness(self, tmp_path: Path) -> None:
        watcher, _ = make(tmp_path, FakeGame(answer=False), timeout=5.0)
        watcher.observe(READY)
        task = asyncio.create_task(watcher.query())
        await asyncio.sleep(0)

        watcher.reset()

        assert await task is None
        assert not watcher.is_ready
        assert not watcher.seen_since_start

    async def test_the_record_outlives_a_reset(self, tmp_path: Path) -> None:
        watcher, _ = make(tmp_path)
        watcher.observe(SET_OFF)

        watcher.reset()

        assert watcher.record is not None and watcher.record.value is False
        assert not watcher.seen_since_start


class TestReadyHook:
    async def run_ready(self, watcher: EntitySpawningWatcher) -> None:
        watcher.observe(READY)
        assert watcher.is_ready
        for _ in range(20):
            await asyncio.sleep(0.01)
            if watcher.seen_since_start:
                return

    async def test_ready_asks_for_the_value(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(ENV_VAR, raising=False)
        watcher, game = make(tmp_path)

        await self.run_ready(watcher)

        assert game.commands == ["/serverconfig entityspawning"]
        assert watcher.record is not None and watcher.record.via == "query"

    @pytest.mark.parametrize(("raw", "command"), [("false", "false"), ("1", "true")])
    async def test_ready_applies_the_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: str, command: str
    ) -> None:
        monkeypatch.setenv(ENV_VAR, raw)
        watcher, game = make(tmp_path)

        await self.run_ready(watcher)

        assert game.commands == [f"/serverconfig entityspawning {command}"]
        assert watcher.record is not None and watcher.record.via == "set"

    async def test_an_invalid_env_var_asks_instead(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ENV_VAR, "sometimes")
        watcher, game = make(tmp_path)

        with capture_logs() as logs:
            await self.run_ready(watcher)

        assert game.commands == ["/serverconfig entityspawning"]
        assert any(e["event"] == "entity_spawning_env_invalid" for e in logs)

    async def test_a_second_ready_line_is_ignored(self, tmp_path: Path) -> None:
        watcher, game = make(tmp_path)
        await self.run_ready(watcher)

        watcher.observe(READY)
        await asyncio.sleep(0.05)

        assert game.commands == ["/serverconfig entityspawning"]

    async def test_a_failing_hook_is_logged(self, tmp_path: Path) -> None:
        async def broken(_: str) -> bool:
            raise RuntimeError("stdin closed")

        watcher = EntitySpawningWatcher(tmp_path, broken, now=lambda: NOW, timeout=0.1)

        with capture_logs() as logs:
            watcher.observe(READY)
            await asyncio.sleep(0.05)

        assert [e["event"] for e in logs] == ["entity_spawning_ready_hook_failed"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, None), ("true", True), ("FALSE", False), ("0", False), ("x", None)],
)
def test_env_value(monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: bool | None) -> None:
    if raw is None:
        monkeypatch.delenv(ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(ENV_VAR, raw)
    assert env_value() == expected
