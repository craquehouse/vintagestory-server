"""Tests for SchedulerService.

Story 7.1: SchedulerService

Tests cover:
- Task 1: Scheduler lifecycle (start, shutdown, is_running)
- Task 2: Job management (add_interval_job, add_cron_job, remove_job, get_jobs)
"""

from __future__ import annotations

import asyncio

import pytest

# APScheduler v3.x does not ship with type stubs
# TODO: Track APScheduler type stubs availability - may add py.typed in future release
# See: https://github.com/agronholm/apscheduler/issues (no stubs package available as of 2026-01)
from apscheduler.jobstores.base import JobLookupError  # type: ignore[import-untyped]

from vintagestory_api.services.scheduler import SchedulerService


class TestSchedulerServiceLifecycle:
    """Tests for scheduler startup and shutdown (AC: 1, 2)."""

    def test_init_creates_scheduler(self) -> None:
        """SchedulerService initializes with AsyncIOScheduler."""
        scheduler = SchedulerService()

        assert scheduler.scheduler is not None
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_start_sets_running_state(self) -> None:
        """start() sets is_running to True and starts the scheduler."""
        scheduler = SchedulerService()

        scheduler.start()

        assert scheduler.is_running is True
        # Cleanup
        scheduler.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_shutdown_clears_running_state(self) -> None:
        """shutdown() sets is_running to False."""
        scheduler = SchedulerService()
        scheduler.start()

        scheduler.shutdown(wait=False)

        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_shutdown_with_wait_true(self) -> None:
        """shutdown(wait=True) waits for jobs to complete."""
        scheduler = SchedulerService()
        scheduler.start()

        # Should not raise
        scheduler.shutdown(wait=True)

        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_shutdown_with_wait_false(self) -> None:
        """shutdown(wait=False) terminates immediately."""
        scheduler = SchedulerService()
        scheduler.start()

        # Should not raise
        scheduler.shutdown(wait=False)

        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_start_logs_scheduler_started(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """start() logs 'scheduler_started' event."""
        scheduler = SchedulerService()

        scheduler.start()
        captured = capsys.readouterr()

        # structlog writes to stdout, not logging module
        assert "scheduler_started" in captured.out
        scheduler.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_shutdown_logs_scheduler_stopped(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """shutdown() logs 'scheduler_stopped' event."""
        scheduler = SchedulerService()
        scheduler.start()
        capsys.readouterr()  # Clear startup output

        scheduler.shutdown(wait=False)
        captured = capsys.readouterr()

        # structlog writes to stdout, not logging module
        assert "scheduler_stopped" in captured.out

    def test_scheduler_job_defaults(self) -> None:
        """Scheduler is configured with correct job defaults."""
        scheduler = SchedulerService()

        # Access the underlying scheduler's job defaults (testing internal state)
        job_defaults = scheduler.scheduler._job_defaults  # type: ignore[reportPrivateUsage]

        assert job_defaults.get("coalesce") is True
        assert job_defaults.get("max_instances") == 1
        assert job_defaults.get("misfire_grace_time") == 60


class TestSchedulerServiceJobManagement:
    """Tests for job management methods (AC: 3, 4)."""

    @pytest.fixture
    async def scheduler(self) -> SchedulerService:  # type: ignore[misc]
        """Create and start a scheduler for testing."""
        svc = SchedulerService()
        svc.start()
        yield svc  # type: ignore[misc]
        svc.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_add_interval_job_registers_job(
        self, scheduler: SchedulerService
    ) -> None:
        """add_interval_job() registers a job with interval trigger."""

        async def dummy_job() -> None:
            pass

        job = scheduler.add_interval_job(dummy_job, seconds=60, job_id="test_interval")

        assert job is not None
        assert job.id == "test_interval"  # type: ignore[reportUnknownMemberType]
        assert scheduler.get_job("test_interval") is not None

    @pytest.mark.asyncio
    async def test_add_interval_job_logs_event(
        self, scheduler: SchedulerService, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """add_interval_job() logs job_added event."""

        async def dummy_job() -> None:
            pass

        capsys.readouterr()  # Clear prior output
        scheduler.add_interval_job(dummy_job, seconds=30, job_id="logged_job")
        captured = capsys.readouterr()

        # structlog writes to stdout, not logging module
        assert "job_added" in captured.out

    @pytest.mark.asyncio
    async def test_add_cron_job_registers_job(
        self, scheduler: SchedulerService
    ) -> None:
        """add_cron_job() registers a job with cron trigger."""

        async def dummy_job() -> None:
            pass

        job = scheduler.add_cron_job(dummy_job, "0 */6 * * *", job_id="test_cron")

        assert job is not None
        assert job.id == "test_cron"  # type: ignore[reportUnknownMemberType]
        assert scheduler.get_job("test_cron") is not None

    @pytest.mark.asyncio
    async def test_add_cron_job_logs_event(
        self, scheduler: SchedulerService, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """add_cron_job() logs job_added event."""

        async def dummy_job() -> None:
            pass

        capsys.readouterr()  # Clear prior output
        scheduler.add_cron_job(dummy_job, "0 2 * * *", job_id="cron_logged")
        captured = capsys.readouterr()

        # structlog writes to stdout, not logging module
        assert "job_added" in captured.out

    @pytest.mark.asyncio
    async def test_remove_job_removes_registered_job(
        self, scheduler: SchedulerService
    ) -> None:
        """remove_job() removes a registered job."""

        async def dummy_job() -> None:
            pass

        scheduler.add_interval_job(dummy_job, seconds=60, job_id="to_remove")
        assert scheduler.get_job("to_remove") is not None

        scheduler.remove_job("to_remove")

        assert scheduler.get_job("to_remove") is None

    @pytest.mark.asyncio
    async def test_remove_job_raises_for_unknown_job(
        self, scheduler: SchedulerService
    ) -> None:
        """remove_job() raises JobLookupError for non-existent job."""
        with pytest.raises(JobLookupError):
            scheduler.remove_job("nonexistent")

    @pytest.mark.asyncio
    async def test_remove_job_logs_event(
        self, scheduler: SchedulerService, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """remove_job() logs job_removed event."""

        async def dummy_job() -> None:
            pass

        scheduler.add_interval_job(dummy_job, seconds=60, job_id="remove_logged")
        capsys.readouterr()  # Clear add output

        scheduler.remove_job("remove_logged")
        captured = capsys.readouterr()

        # structlog writes to stdout, not logging module
        assert "job_removed" in captured.out

    @pytest.mark.asyncio
    async def test_get_jobs_returns_all_jobs(
        self, scheduler: SchedulerService
    ) -> None:
        """get_jobs() returns list of all scheduled jobs."""

        async def job1() -> None:
            pass

        async def job2() -> None:
            pass

        scheduler.add_interval_job(job1, seconds=60, job_id="job1")
        scheduler.add_cron_job(job2, "0 * * * *", job_id="job2")

        jobs = scheduler.get_jobs()

        assert len(jobs) == 2
        job_ids: list[str] = [j.id for j in jobs]  # type: ignore[union-attr]
        assert "job1" in job_ids
        assert "job2" in job_ids

    @pytest.mark.asyncio
    async def test_get_jobs_returns_empty_list_when_no_jobs(
        self, scheduler: SchedulerService
    ) -> None:
        """get_jobs() returns empty list when no jobs scheduled."""
        jobs = scheduler.get_jobs()

        assert jobs == []

    @pytest.mark.asyncio
    async def test_get_job_returns_specific_job(
        self, scheduler: SchedulerService
    ) -> None:
        """get_job() returns specific job by ID."""

        async def dummy_job() -> None:
            pass

        scheduler.add_interval_job(dummy_job, seconds=60, job_id="specific_job")

        job = scheduler.get_job("specific_job")

        assert job is not None
        assert job.id == "specific_job"  # type: ignore[reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_get_job_returns_none_for_unknown_job(
        self, scheduler: SchedulerService
    ) -> None:
        """get_job() returns None for non-existent job."""
        job = scheduler.get_job("does_not_exist")

        assert job is None


class TestSchedulerServiceJobExecution:
    """Tests for actual job execution."""

    @pytest.mark.asyncio
    async def test_interval_job_executes(self) -> None:
        """Interval job actually executes when scheduled."""
        scheduler = SchedulerService()
        scheduler.start()

        execution_count = 0

        async def increment_counter() -> None:
            nonlocal execution_count
            execution_count += 1

        # Schedule job to run every 1 second for testing
        scheduler.add_interval_job(increment_counter, seconds=1, job_id="counter_job")

        # Wait a bit for at least one execution
        # Note: First execution happens after interval, not immediately
        await asyncio.sleep(1.5)

        scheduler.shutdown(wait=True)

        # Should have executed at least once
        assert execution_count >= 1

    @pytest.mark.asyncio
    async def test_job_kwargs_passed_to_func(self) -> None:
        """Additional kwargs are passed to the job function."""
        scheduler = SchedulerService()
        scheduler.start()

        received_args: dict[str, str] = {}

        async def capture_args(value: str) -> None:
            received_args["value"] = value

        # Use args parameter to pass arguments
        scheduler.add_interval_job(
            capture_args,
            seconds=1,
            job_id="args_job",
            args=("test_value",),
        )

        await asyncio.sleep(1.5)
        scheduler.shutdown(wait=True)

        assert received_args.get("value") == "test_value"


class TestSchedulerLifespanIntegration:
    """Tests for scheduler integration with FastAPI lifespan (AC: 1, 2)."""

    def test_get_scheduler_service_returns_instance(self) -> None:
        """get_scheduler_service() returns the global scheduler after app starts."""
        from fastapi.testclient import TestClient

        from vintagestory_api.main import app, get_scheduler_service

        # Use context manager to trigger lifespan
        with TestClient(app):
            scheduler = get_scheduler_service()
            assert scheduler is not None
            assert scheduler.is_running is True

    def test_scheduler_logs_started_during_startup(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Scheduler logs 'scheduler_started' during app startup."""
        from fastapi.testclient import TestClient

        from vintagestory_api.main import app

        capsys.readouterr()  # Clear prior output

        # Creating TestClient triggers lifespan startup
        with TestClient(app):
            captured = capsys.readouterr()
            assert "scheduler_started" in captured.out

    def test_scheduler_logs_stopped_during_shutdown(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Scheduler logs 'scheduler_stopped' during app shutdown."""
        from fastapi.testclient import TestClient

        from vintagestory_api.main import app

        # Create and close TestClient to trigger full lifecycle
        with TestClient(app):
            capsys.readouterr()  # Clear startup output

        # After context exits, shutdown should have occurred
        captured = capsys.readouterr()
        assert "scheduler_stopped" in captured.out

    def test_scheduler_is_running_during_request(self) -> None:
        """Scheduler is running and accessible during HTTP requests."""
        from fastapi.testclient import TestClient

        from vintagestory_api.main import app, get_scheduler_service

        # Use context manager to trigger lifespan
        with TestClient(app) as client:
            # Make a request to ensure app is fully initialized
            response = client.get("/healthz")
            assert response.status_code == 200

            # Scheduler should be running
            scheduler = get_scheduler_service()
            assert scheduler.is_running is True

    def test_get_scheduler_service_raises_before_init(self) -> None:
        """get_scheduler_service() raises RuntimeError before initialization."""
        import vintagestory_api.main as main_module

        # Temporarily set to None to test error case
        original = main_module.scheduler_service
        main_module.scheduler_service = None

        try:
            with pytest.raises(RuntimeError, match="Scheduler service not initialized"):
                main_module.get_scheduler_service()
        finally:
            # Restore original
            main_module.scheduler_service = original
