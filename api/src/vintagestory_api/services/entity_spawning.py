"""Entity Spawning, read from and set on the running game (Epic 25 ADR-4, ADR-5, ADR-6).

Story 25.3: Entity Spawning Comes from the Running Game (FR349 to FR353)

Game 1.22.7 keeps Entity Spawning in the world save, not in serverconfig.json. The
manager asks the running game with `/serverconfig entityspawning` and changes it with
`/serverconfig entityspawning true|false`. The game answers on stdout (recorded in
Story 25.3 Task 1, ADR-4 decision 1):

    [Server Notification] Current Entity spawning mode is on
    [Server Notification] Entity spawning mode set to off

`EntitySpawningWatcher` is fed every console line by `ServerService._read_stream`. It
keeps the last value the game reported in `state/entity_spawning.json`, so Game Settings
can show it while the game is stopped (ADR-5). When the game logs that it is ready, the
watcher asks for the value, or applies `VS_CFG_ENTITY_SPAWNING` when it is set (ADR-6).
"""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import structlog
from pydantic import BaseModel, ValidationError

from vintagestory_api.services.config_init import parse_env_value

logger = structlog.get_logger()

ENTITY_SPAWNING_FILENAME = "entity_spawning.json"
"""The record's file in the state directory (ADR-5 decision 1)."""

ENV_VAR = "VS_CFG_ENTITY_SPAWNING"
"""Applied through the console after each start (ADR-6 decisions 3 and 4)."""

REPLY_TIMEOUT_SECONDS = 5.0
"""How long a query or a set waits for the game's reply (ADR-4 decision 4)."""

QUERY_COMMAND = "/serverconfig entityspawning"

# Nothing but a timestamp before the tag, so a chat line ("[Server Chat] ...") never
# matches, whatever a player types (as the player tracker, Epic 22 ADR-1)
_NOTIFICATION = r"^[^\[]*\[Server Notification\] "
_CURRENT = re.compile(_NOTIFICATION + r"Current Entity spawning mode is (?P<value>on|off)$")
_SET = re.compile(_NOTIFICATION + r"Entity spawning mode set to (?P<value>on|off)$")
_READY = re.compile(r"^[^\[]*\[(?:Server )?Event\] Dedicated Server now running ")

Via = Literal["query", "set", "console"]
ReplyKind = Literal["current", "set"]


class EntitySpawningRecord(BaseModel):
    """The last value the game reported (ADR-5 decision 1)."""

    value: bool
    observed_at: datetime
    via: Via


def set_command(value: bool) -> str:
    """The console command that sets the value; only `true` or `false` is ever sent."""
    return f"{QUERY_COMMAND} {'true' if value else 'false'}"


def parse_reply(line: str) -> tuple[ReplyKind, bool] | None:
    """A query or set reply as (kind, value); None for any other line."""
    current = _CURRENT.match(line)
    if current is not None:
        return "current", current.group("value") == "on"
    set_reply = _SET.match(line)
    if set_reply is not None:
        return "set", set_reply.group("value") == "on"
    return None


class _ProcessEndedError(Exception):
    """A waiting query or set ended because the game process started or ended."""


def is_ready_line(line: str) -> bool:
    """Whether the line says the game has finished starting."""
    return _READY.match(line) is not None


def _utc_now() -> datetime:
    return datetime.now(UTC)


class EntitySpawningStore:
    """`state/entity_spawning.json`, read on first use and written atomically."""

    def __init__(self, state_dir: Path, *, now: Callable[[], datetime] = _utc_now) -> None:
        self._path = state_dir / ENTITY_SPAWNING_FILENAME
        self._now = now
        self._record: EntitySpawningRecord | None = None
        self._loaded = False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def record(self) -> EntitySpawningRecord | None:
        if not self._loaded:
            self._record = self._load()
            self._loaded = True
        return self._record

    def observe(self, value: bool, via: Via) -> EntitySpawningRecord:
        """Record a value the game reported, and save."""
        record = EntitySpawningRecord(value=value, observed_at=self._now(), via=via)
        self._record = record
        self._loaded = True
        self._save(record)
        return record

    def _load(self) -> EntitySpawningRecord | None:
        if not self._path.exists():
            return None
        try:
            return EntitySpawningRecord.model_validate_json(self._path.read_text())
        except (OSError, ValidationError) as e:
            logger.warning("entity_spawning_record_unreadable", error_type=type(e).__name__)
            return None

    def _save(self, record: EntitySpawningRecord) -> None:
        """A failed save is logged; the value stays in memory."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temp = self._path.with_suffix(".tmp")
            temp.write_text(record.model_dump_json(indent=2))
            temp.rename(self._path)
        except OSError as e:
            # No str(e): its text holds the absolute path (Story 22.4)
            logger.error(
                "entity_spawning_record_save_failed",
                error_type=type(e).__name__,
                errno=e.errno,
            )


def env_value() -> bool | None:
    """`VS_CFG_ENTITY_SPAWNING` as a bool; None when unset or not a bool (logged)."""
    raw = os.environ.get(ENV_VAR)
    if raw is None:
        return None
    try:
        value = parse_env_value(raw, "bool")
    except ValueError:
        logger.warning("entity_spawning_env_invalid", env_var=ENV_VAR)
        return None
    return value if isinstance(value, bool) else None


class EntitySpawningWatcher:
    """Watches the game's console for Entity Spawning replies (ADR-4).

    `observe` is called with every console line, synchronously, from the stream reader.
    It records any reply (a value typed in the console included, ADR-4 decision 3) and
    resolves the waiter of a pending query or set. The ready line starts the ready hook.
    """

    def __init__(
        self,
        state_dir: Path,
        send_command: Callable[[str], Awaitable[bool]],
        *,
        now: Callable[[], datetime] = _utc_now,
        timeout: float = REPLY_TIMEOUT_SECONDS,
    ) -> None:
        self._store = EntitySpawningStore(state_dir, now=now)
        self._send_command = send_command
        self._timeout = timeout
        self._ready = False
        self._seen_since_start = False
        self._waiters: list[tuple[ReplyKind, asyncio.Future[bool]]] = []
        self._ready_task: asyncio.Task[None] | None = None

    @property
    def record(self) -> EntitySpawningRecord | None:
        """The last value the game reported, from any start (ADR-5)."""
        return self._store.record

    @property
    def is_ready(self) -> bool:
        """Whether the game logged that it is ready since this start."""
        return self._ready

    @property
    def seen_since_start(self) -> bool:
        """Whether the game reported the value since this start (ADR-5 decision 2)."""
        return self._seen_since_start

    def reset(self) -> None:
        """A game process starts or ends: forget readiness and stop waiting."""
        self._ready = False
        self._seen_since_start = False
        for _, future in self._waiters:
            if not future.done():
                future.set_exception(_ProcessEndedError())
        self._waiters.clear()
        if self._ready_task is not None and not self._ready_task.done():
            self._ready_task.cancel()
        self._ready_task = None

    def observe(self, line: str) -> None:
        """Take one console line; any other line changes nothing."""
        if not self._ready and is_ready_line(line):
            self._ready = True
            self._ready_task = asyncio.get_running_loop().create_task(self._on_ready())
            return
        reply = parse_reply(line)
        if reply is None:
            return
        kind, value = reply
        waiting = [future for waiting_kind, future in self._waiters if waiting_kind == kind]
        # A reply nobody waits for was typed in the console (ADR-4 decision 3)
        via: Via = ("query" if kind == "current" else "set") if waiting else "console"
        self._store.observe(value, via)
        self._seen_since_start = True
        logger.info("entity_spawning_observed", value=value, via=via)
        for future in waiting:
            if not future.done():
                future.set_result(value)

    async def query(self) -> bool | None:
        """Ask the game; the value it reported, or None without a reply in time."""
        return await self._ask(QUERY_COMMAND, "current", "query")

    async def set(self, value: bool) -> bool | None:
        """Set the value; the value the game reported, or None without a reply in time."""
        return await self._ask(set_command(value), "set", "set")

    async def _ask(self, command: str, kind: ReplyKind, via: Via) -> bool | None:
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        entry = (kind, future)
        # Registered before the command is sent, so the reply cannot be missed
        self._waiters.append(entry)
        try:
            if not await self._send_command(command):
                return None
            return await asyncio.wait_for(future, self._timeout)
        except TimeoutError:
            logger.warning("entity_spawning_reply_timeout", via=via)
            return None
        except _ProcessEndedError:
            return None
        finally:
            if entry in self._waiters:
                self._waiters.remove(entry)

    async def _on_ready(self) -> None:
        """Apply the env var, or ask for the value (ADR-6 decision 3)."""
        try:
            wanted = env_value()
            if wanted is None:
                await self.query()
            else:
                await self.set(wanted)
        except Exception as e:
            # Never stops console capture or the start (ADR-4 decision 5)
            logger.warning("entity_spawning_ready_hook_failed", error_type=type(e).__name__)
