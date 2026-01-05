"""Job models for scheduler API responses.

Story 7.2: Job Management API

Provides Pydantic models and serialization helpers for APScheduler jobs.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from apscheduler.job import Job  # type: ignore[import-untyped]


class JobInfo(BaseModel):
    """Serialized job information for API responses.

    Attributes:
        id: Unique job identifier.
        next_run_time: Next scheduled execution time, or None if paused.
        trigger_type: Type of trigger ("interval", "cron", or "unknown").
        trigger_details: Human-readable trigger description.
    """

    id: str
    next_run_time: datetime | None
    trigger_type: str
    trigger_details: str


def job_to_info(job: Job) -> JobInfo:
    """Convert APScheduler Job to API-friendly JobInfo.

    Args:
        job: APScheduler Job instance.

    Returns:
        JobInfo with serialized job details.

    Note:
        Uses dynamic imports to avoid importing APScheduler trigger types
        at module level (they have no type stubs).
    """
    # Import trigger types inside function to avoid module-level import issues
    # TODO: Track APScheduler type stubs availability - may add py.typed in future
    # See: https://github.com/agronholm/apscheduler/issues (no stubs as of 2026-01)
    from apscheduler.triggers.cron import (  # type: ignore[import-untyped]
        CronTrigger,
    )
    from apscheduler.triggers.interval import (  # type: ignore[import-untyped]
        IntervalTrigger,
    )

    trigger = job.trigger  # type: ignore[reportUnknownMemberType]

    if isinstance(trigger, IntervalTrigger):
        trigger_type = "interval"
        # IntervalTrigger stores interval as timedelta
        trigger_details = f"every {int(trigger.interval.total_seconds())} seconds"  # type: ignore[reportUnknownMemberType]
    elif isinstance(trigger, CronTrigger):
        trigger_type = "cron"
        # CronTrigger __str__ returns cron expression representation
        trigger_details = str(trigger)  # type: ignore[reportUnknownArgumentType]
    else:
        trigger_type = "unknown"
        trigger_details = str(trigger)  # type: ignore[reportUnknownArgumentType]

    return JobInfo(
        id=str(job.id),  # type: ignore[reportUnknownMemberType]
        next_run_time=job.next_run_time,  # type: ignore[reportUnknownMemberType]
        trigger_type=trigger_type,
        trigger_details=trigger_details,
    )
