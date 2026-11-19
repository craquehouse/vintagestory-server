"""Scheduled restarts: warn the players, then restart a running game (Epic 22 ADR-6).

Story 22.3: Scheduled Restarts

Each time in the `scheduled_restart_times` API setting is a daily cron job,
`scheduled_restart_HHMM`, that fires WARNING_LEAD_MINUTES before the time. The job
announces the restart 15, 5 and 1 minutes ahead and then restarts the game through
`ServerService.restart_server()`, the Restart button's path.

A stopped game is never started. At every step the sequence first checks that its own
job is still registered, so removing the time (or deleting the job) during the warnings
cancels the restart. At the restart it does not wait for a manual start, stop, restart,
uninstall or install in progress: it skips the restart. Every skip is logged as
`scheduled_restart_skipped` with its reason.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal, Protocol

import structlog

from vintagestory_api.jobs.base import safe_job

if TYPE_CHECKING:
    from vintagestory_api.services.scheduler import SchedulerService

logger = structlog.get_logger()

RESTART_JOB_PREFIX = "scheduled_restart_"
WARNING_LEAD_MINUTES = 15
WARNINGS: tuple[tuple[int, str, float], ...] = (
    (15, "Server restarts in 15 minutes", 600.0),
    (5, "Server restarts in 5 minutes", 240.0),
    (1, "Server restarts in 1 minute", 60.0),
)
"""(minutes left, the /announce text, seconds to wait after it); the waits add up to 15 minutes."""

RestartOutcome = Literal["restarted", "not_running", "lifecycle_busy", "cancelled", "failed"]
SkipReason = Literal["not_running", "lifecycle_busy", "cancelled"]

_MINUTES_PER_DAY = 1440


def restart_job_id(restart_time: str) -> str:
    """The job id of a restart time: "04:00" -> "scheduled_restart_0400"."""
    return RESTART_JOB_PREFIX + restart_time.replace(":", "")


def warning_start(restart_time: str) -> tuple[int, int]:
    """(hour, minute) of the first warning: "04:00" -> (3, 45); "00:10" -> (23, 55)."""
    hours, minutes = restart_time.split(":")
    start = (int(hours) * 60 + int(minutes) - WARNING_LEAD_MINUTES) % _MINUTES_PER_DAY
    hour, minute = divmod(start, 60)
    return hour, minute


class RestartTarget(Protocol):
    """What the sequence needs from ServerService (a test fake satisfies it too)."""

    @property
    def game_running(self) -> bool: ...
    @property
    def lifecycle_busy(self) -> bool: ...
    @property
    def players_online(self) -> int | None: ...
    async def send_command(self, command: str) -> bool: ...
    async def restart_server(self, timeout: float = 10.0) -> object: ...


def _skip(restart_time: str, reason: SkipReason, minutes_left: int) -> SkipReason:
    """Log a skipped restart; a manual operation in progress is a warning."""
    if reason == "lifecycle_busy":
        logger.warning(
            "scheduled_restart_skipped",
            restart_time=restart_time,
            reason=reason,
            minutes_left=minutes_left,
        )
    else:
        logger.info(
            "scheduled_restart_skipped",
            restart_time=restart_time,
            reason=reason,
            minutes_left=minutes_left,
        )
    return reason


async def run_restart_sequence(
    restart_time: str,
    *,
    server: RestartTarget,
    still_scheduled: Callable[[], bool],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> RestartOutcome:
    """Warn the players, then restart the game if it still runs (Epic 22 ADR-6).

    Args:
        restart_time: The restart time, HH:MM.
        server: The game server (ServerService).
        still_scheduled: True while this time's job is registered; False cancels.
        sleep: The wait between steps (a fake in tests).

    Returns:
        What happened: restarted, or why not.
    """
    for minutes_left, text, wait in WARNINGS:
        if not still_scheduled():
            return _skip(restart_time, "cancelled", minutes_left)
        if not server.game_running:
            return _skip(restart_time, "not_running", minutes_left)
        if not await server.send_command(f"/announce {text}"):
            # The process ended between the check and the write.
            return _skip(restart_time, "not_running", minutes_left)
        logger.info(
            "scheduled_restart_warning", restart_time=restart_time, minutes_left=minutes_left
        )
        await sleep(wait)

    # Busy before running: a manual stop or start holds the lock in STOPPING or STARTING,
    # which is not running either. No await from here to restart_server(): the game cannot
    # be found running and then be started from stopped.
    if not still_scheduled():
        return _skip(restart_time, "cancelled", 0)
    if server.lifecycle_busy:
        return _skip(restart_time, "lifecycle_busy", 0)
    if not server.game_running:
        return _skip(restart_time, "not_running", 0)
    logger.info(
        "scheduled_restart_restarting",
        restart_time=restart_time,
        players_online=server.players_online,
    )
    try:
        await server.restart_server()
    except RuntimeError as e:
        # ServerService raises RuntimeError(ErrorCode...); not retried.
        logger.error("scheduled_restart_failed", restart_time=restart_time, error_code=str(e))
        return "failed"
    logger.info("scheduled_restart_done", restart_time=restart_time)
    return "restarted"


@safe_job("scheduled_restart")
async def scheduled_restart(restart_time: str, scheduler: SchedulerService) -> None:
    """The job function: one per restart time, fired WARNING_LEAD_MINUTES before it."""
    from vintagestory_api.services.server import get_server_service

    job_id = restart_job_id(restart_time)
    await run_restart_sequence(
        restart_time,
        server=get_server_service(),
        still_scheduled=lambda: scheduler.get_job(job_id) is not None,
    )
