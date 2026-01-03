"""Tests for job models and serialization.

Story 7.2: Job Management API - Task 1

Tests cover:
- JobInfo Pydantic model validation
- job_to_info() serialization for interval triggers
- job_to_info() serialization for cron triggers
- job_to_info() handling of unknown trigger types
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from vintagestory_api.models.jobs import JobInfo, job_to_info
from vintagestory_api.services.scheduler import SchedulerService


class TestJobInfoModel:
    """Tests for JobInfo Pydantic model."""

    def test_jobinfo_with_next_run_time(self) -> None:
        """JobInfo accepts datetime for next_run_time."""
        next_run = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)

        job_info = JobInfo(
            id="test_job",
            next_run_time=next_run,
            trigger_type="interval",
            trigger_details="every 60 seconds",
        )

        assert job_info.id == "test_job"
        assert job_info.next_run_time == next_run
        assert job_info.trigger_type == "interval"
        assert job_info.trigger_details == "every 60 seconds"

    def test_jobinfo_with_none_next_run_time(self) -> None:
        """JobInfo accepts None for next_run_time (paused job)."""
        job_info = JobInfo(
            id="paused_job",
            next_run_time=None,
            trigger_type="cron",
            trigger_details="0 */6 * * *",
        )

        assert job_info.id == "paused_job"
        assert job_info.next_run_time is None
        assert job_info.trigger_type == "cron"
        assert job_info.trigger_details == "0 */6 * * *"

    def test_jobinfo_model_dump(self) -> None:
        """JobInfo.model_dump() returns dictionary for API response."""
        next_run = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
        job_info = JobInfo(
            id="test_job",
            next_run_time=next_run,
            trigger_type="interval",
            trigger_details="every 3600 seconds",
        )

        data = job_info.model_dump()

        assert data["id"] == "test_job"
        assert data["next_run_time"] == next_run
        assert data["trigger_type"] == "interval"
        assert data["trigger_details"] == "every 3600 seconds"


class TestJobToInfo:
    """Tests for job_to_info() serialization function."""

    def test_interval_trigger_serialization(self) -> None:
        """job_to_info() correctly serializes interval trigger jobs."""
        # Import real trigger type for mock setup
        from apscheduler.triggers.interval import (  # type: ignore[import-untyped]
            IntervalTrigger,
        )

        # Create mock job with interval trigger
        mock_job = MagicMock()
        mock_job.id = "cache_refresh"
        mock_job.next_run_time = datetime(2026, 1, 2, 13, 0, 0, tzinfo=UTC)
        mock_job.trigger = IntervalTrigger(seconds=3600)

        result = job_to_info(mock_job)

        assert result.id == "cache_refresh"
        assert result.next_run_time == mock_job.next_run_time
        assert result.trigger_type == "interval"
        assert result.trigger_details == "every 3600 seconds"

    def test_interval_trigger_with_minutes(self) -> None:
        """job_to_info() converts interval to total seconds."""
        from apscheduler.triggers.interval import (  # type: ignore[import-untyped]
            IntervalTrigger,
        )

        mock_job = MagicMock()
        mock_job.id = "quick_check"
        mock_job.next_run_time = datetime(2026, 1, 2, 12, 5, 0, tzinfo=UTC)
        mock_job.trigger = IntervalTrigger(minutes=5)

        result = job_to_info(mock_job)

        assert result.trigger_type == "interval"
        assert result.trigger_details == "every 300 seconds"

    def test_cron_trigger_serialization(self) -> None:
        """job_to_info() correctly serializes cron trigger jobs."""
        from apscheduler.triggers.cron import (  # type: ignore[import-untyped]
            CronTrigger,
        )

        mock_job = MagicMock()
        mock_job.id = "daily_cleanup"
        mock_job.next_run_time = datetime(2026, 1, 3, 2, 0, 0, tzinfo=UTC)
        mock_job.trigger = CronTrigger.from_crontab("0 2 * * *")

        result = job_to_info(mock_job)

        assert result.id == "daily_cleanup"
        assert result.trigger_type == "cron"
        # CronTrigger str() returns its representation
        assert "cron" in result.trigger_details.lower() or "*" in result.trigger_details

    def test_cron_trigger_every_six_hours(self) -> None:
        """job_to_info() handles complex cron expressions."""
        from apscheduler.triggers.cron import (  # type: ignore[import-untyped]
            CronTrigger,
        )

        mock_job = MagicMock()
        mock_job.id = "periodic_sync"
        mock_job.next_run_time = datetime(2026, 1, 2, 18, 0, 0, tzinfo=UTC)
        mock_job.trigger = CronTrigger.from_crontab("0 */6 * * *")

        result = job_to_info(mock_job)

        assert result.id == "periodic_sync"
        assert result.trigger_type == "cron"
        # Verify trigger details contains something (str representation varies)
        assert len(result.trigger_details) > 0

    def test_unknown_trigger_type(self) -> None:
        """job_to_info() handles unknown trigger types gracefully."""
        # Create a mock trigger that isn't IntervalTrigger or CronTrigger
        unknown_trigger = MagicMock()
        unknown_trigger.__class__.__name__ = "DateTrigger"

        mock_job = MagicMock()
        mock_job.id = "one_time_job"
        mock_job.next_run_time = datetime(2026, 1, 2, 15, 0, 0, tzinfo=UTC)
        mock_job.trigger = unknown_trigger

        result = job_to_info(mock_job)

        assert result.id == "one_time_job"
        assert result.trigger_type == "unknown"
        # trigger_details should be string representation of the trigger
        assert isinstance(result.trigger_details, str)

    def test_job_with_none_next_run_time(self) -> None:
        """job_to_info() handles paused jobs (None next_run_time)."""
        from apscheduler.triggers.interval import (  # type: ignore[import-untyped]
            IntervalTrigger,
        )

        mock_job = MagicMock()
        mock_job.id = "paused_job"
        mock_job.next_run_time = None
        mock_job.trigger = IntervalTrigger(seconds=60)

        result = job_to_info(mock_job)

        assert result.id == "paused_job"
        assert result.next_run_time is None
        assert result.trigger_type == "interval"
        assert result.trigger_details == "every 60 seconds"


class TestJobInfoIntegration:
    """Integration tests with real SchedulerService jobs."""

    @pytest.fixture
    async def scheduler(self) -> AsyncGenerator[SchedulerService]:
        """Create a started scheduler for testing (async context)."""
        svc = SchedulerService()
        svc.start()
        yield svc
        svc.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_serialize_real_interval_job(
        self, scheduler: SchedulerService
    ) -> None:
        """job_to_info() works with real interval job from scheduler."""

        async def dummy_task() -> None:
            pass

        job = scheduler.add_interval_job(dummy_task, seconds=120, job_id="real_interval")

        result = job_to_info(job)

        assert result.id == "real_interval"
        assert result.trigger_type == "interval"
        assert result.trigger_details == "every 120 seconds"
        assert result.next_run_time is not None

    @pytest.mark.asyncio
    async def test_serialize_real_cron_job(self, scheduler: SchedulerService) -> None:
        """job_to_info() works with real cron job from scheduler."""

        async def dummy_task() -> None:
            pass

        job = scheduler.add_cron_job(dummy_task, "0 3 * * *", job_id="real_cron")

        result = job_to_info(job)

        assert result.id == "real_cron"
        assert result.trigger_type == "cron"
        assert result.next_run_time is not None

    @pytest.mark.asyncio
    async def test_serialize_all_jobs(self, scheduler: SchedulerService) -> None:
        """job_to_info() can serialize all jobs from get_jobs()."""

        async def task1() -> None:
            pass

        async def task2() -> None:
            pass

        scheduler.add_interval_job(task1, seconds=60, job_id="job1")
        scheduler.add_cron_job(task2, "*/5 * * * *", job_id="job2")

        jobs = scheduler.get_jobs()
        results = [job_to_info(job) for job in jobs]

        assert len(results) == 2
        job_ids = {r.id for r in results}
        assert job_ids == {"job1", "job2"}
