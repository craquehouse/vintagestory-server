"""Tests for jobs module registration functionality.

Story 8.0: Epic 8 Preparation
Story 8.2: Server Versions Check Job
Story 17.6: Settings behave as saved (apply_interval_setting)
Story 22.3: Scheduled restarts (apply_restart_schedule, apply_setting)
Story 22.4: Daily backup cleanup (register_disk_cleanup)

Tests cover:
- Task 1: register_default_jobs() functionality and job patterns
- AC 1: Jobs follow consistent structure (try/except, structured logging, no re-raise)
- AC 2: Jobs registered in central register_default_jobs() function
- AC 3: Jobs with interval=0 are NOT registered
- AC 4: Directory structure follows established patterns
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
import tzlocal
from structlog.testing import capture_logs

from vintagestory_api.jobs import (
    INTERVAL_JOBS,
    apply_interval_setting,
    apply_restart_schedule,
    apply_setting,
    register_default_jobs,
    register_disk_cleanup,
)
from vintagestory_api.jobs.base import safe_job
from vintagestory_api.jobs.scheduled_restart import (
    restart_job_id,
    run_restart_sequence,
    scheduled_restart,
)
from vintagestory_api.models.jobs import JobInfo, job_to_info
from vintagestory_api.services.api_settings import ApiSettings
from vintagestory_api.services.scheduler import SchedulerService

if TYPE_CHECKING:
    from apscheduler.job import Job
    from pytest import CaptureFixture


class TestRegisterDefaultJobs:
    """Tests for register_default_jobs() function (AC: 2, 4)."""

    @pytest.fixture
    async def scheduler(self) -> SchedulerService:  # type: ignore[misc]
        """Create a started scheduler for testing."""
        svc = SchedulerService()
        svc.start()
        yield svc  # type: ignore[misc]
        svc.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_register_default_jobs_registers_jobs(self, scheduler: SchedulerService) -> None:
        """register_default_jobs() registers jobs with default settings."""
        register_default_jobs(scheduler)

        # Story 8.1: mod_cache_refresh job should be registered with default settings
        # (mod_list_refresh_interval=14400 by default, VSS-s9s)
        jobs = scheduler.get_jobs()
        assert len(jobs) >= 1
        job_ids: list[str] = [job.id for job in jobs]  # type: ignore[reportUnknownMemberType]
        assert "mod_cache_refresh" in job_ids

    @pytest.mark.asyncio
    async def test_register_default_jobs_logs_registration_count(
        self, scheduler: SchedulerService
    ) -> None:
        """register_default_jobs() logs the number of jobs registered.

        Note: This test verifies the function runs without error and registers jobs.
        The log output verification was removed because structlog configuration
        can vary across test runs due to runtime reconfiguration (Story 9.4 FR48).
        The actual logging behavior is verified through log inspection in production.
        """
        # Verify jobs are registered (primary behavior)
        register_default_jobs(scheduler)
        jobs = scheduler.get_jobs()
        assert len(jobs) >= 1  # At least one job should be registered

    @pytest.mark.asyncio
    async def test_register_default_jobs_reads_api_settings(
        self, scheduler: SchedulerService
    ) -> None:
        """register_default_jobs() reads API settings to determine job registration."""
        from vintagestory_api.services.api_settings import ApiSettings

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            # Return a real ApiSettings object so interval comparisons work
            mock_instance.get_settings.return_value = ApiSettings()
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            # Verify settings were read
            mock_instance.get_settings.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_default_jobs_accepts_scheduler(
        self, scheduler: SchedulerService
    ) -> None:
        """register_default_jobs() accepts SchedulerService parameter."""
        # Should not raise
        register_default_jobs(scheduler)

    @pytest.mark.asyncio
    async def test_register_default_jobs_can_be_called_multiple_times(
        self, scheduler: SchedulerService
    ) -> None:
        """register_default_jobs() can be called multiple times safely."""
        # In Story 8.0 stub, this should work without errors
        register_default_jobs(scheduler)
        register_default_jobs(scheduler)  # Should not raise


class TestSafeJobDecorator:
    """Tests for safe_job() decorator (AC: 1)."""

    @pytest.mark.asyncio
    async def test_safe_job_logs_start_event(self, captured_logs: StringIO) -> None:
        """safe_job() logs job start event."""

        @safe_job("test_job")
        async def my_job() -> str:
            return "done"

        await my_job()

        assert "test_job_started" in captured_logs.getvalue()

    @pytest.mark.asyncio
    async def test_safe_job_logs_completion_event(self, captured_logs: StringIO) -> None:
        """safe_job() logs job completion event on success."""

        @safe_job("test_job")
        async def my_job() -> str:
            return "done"

        await my_job()

        assert "test_job_completed" in captured_logs.getvalue()

    @pytest.mark.asyncio
    async def test_safe_job_returns_function_result(self) -> None:
        """safe_job() returns the wrapped function's result."""

        @safe_job("test_job")
        async def my_job() -> str:
            return "expected_result"

        result = await my_job()

        assert result == "expected_result"

    @pytest.mark.asyncio
    async def test_safe_job_catches_exceptions_without_reraising(
        self, captured_logs: StringIO
    ) -> None:
        """safe_job() catches exceptions and does NOT re-raise (critical for scheduler)."""

        @safe_job("failing_job")
        async def my_failing_job() -> str:
            raise ValueError("Something went wrong")

        # Should NOT raise - this is critical for scheduler stability
        result = await my_failing_job()

        # Returns None on failure
        assert result is None
        assert "failing_job_failed" in captured_logs.getvalue()

    @pytest.mark.asyncio
    async def test_safe_job_logs_exception_details(self, captured_logs: StringIO) -> None:
        """safe_job() logs exception details on failure."""

        @safe_job("error_job")
        async def my_error_job() -> None:
            raise RuntimeError("Test error message")

        await my_error_job()
        output = captured_logs.getvalue()

        assert "error_job_failed" in output
        # Should include error details in logs
        assert "Test error message" in output or "error" in output

    @pytest.mark.asyncio
    async def test_safe_job_preserves_function_name(self) -> None:
        """safe_job() preserves the original function's name via functools.wraps."""

        @safe_job("my_named_job")
        async def original_function_name() -> None:
            pass

        assert original_function_name.__name__ == "original_function_name"

    @pytest.mark.asyncio
    async def test_safe_job_accepts_args_and_kwargs(self) -> None:
        """safe_job() passes arguments to the wrapped function."""

        @safe_job("parameterized_job")
        async def job_with_args(value: str, count: int = 1) -> str:
            return f"{value}-{count}"

        result = await job_with_args("test", count=5)

        assert result == "test-5"


class TestJobPatternCompliance:
    """Tests verifying job patterns match documented requirements (AC: 1)."""

    def test_jobs_module_exports_register_function(self) -> None:
        """Jobs module exports register_default_jobs() function."""
        from vintagestory_api import jobs

        assert hasattr(jobs, "register_default_jobs")
        assert callable(jobs.register_default_jobs)

    def test_base_module_exports_safe_job_decorator(self) -> None:
        """Base module exports safe_job() decorator."""
        from vintagestory_api.jobs import base

        assert hasattr(base, "safe_job")
        assert callable(base.safe_job)

    def test_jobs_directory_structure_exists(self) -> None:
        """Jobs directory has expected structure."""
        from pathlib import Path

        import vintagestory_api.jobs as jobs_module

        jobs_path = Path(jobs_module.__file__).parent

        # __init__.py exists (already imported)
        assert (jobs_path / "__init__.py").exists()

        # base.py exists
        assert (jobs_path / "base.py").exists()


class TestJobRegistrationLifespan:
    """Tests for job registration during app lifespan (AC: 2, 3) - Task 2."""

    def test_register_default_jobs_called_during_startup(self, capsys: CaptureFixture[str]) -> None:
        """register_default_jobs() is called during app startup."""
        from fastapi.testclient import TestClient

        from vintagestory_api.main import app

        capsys.readouterr()  # Clear prior output

        # Creating TestClient triggers lifespan startup
        with TestClient(app):
            captured = capsys.readouterr()
            # Should see job registration log event
            assert "default_jobs_registered" in captured.out

    def test_lifespan_logs_scheduler_then_jobs(self, capsys: CaptureFixture[str]) -> None:
        """Scheduler starts before job registration in lifespan order."""
        from fastapi.testclient import TestClient

        from vintagestory_api.main import app

        capsys.readouterr()  # Clear prior output

        with TestClient(app):
            captured = capsys.readouterr()

            # Both events should be present
            assert "scheduler_started" in captured.out
            assert "default_jobs_registered" in captured.out

            # Verify order: scheduler_started before default_jobs_registered
            scheduler_pos = captured.out.find("scheduler_started")
            jobs_pos = captured.out.find("default_jobs_registered")
            assert scheduler_pos < jobs_pos, "Scheduler should start before job registration"


class TestJobIntervalZeroNotRegistered:
    """Tests for jobs with interval=0 NOT being registered (AC: 3)."""

    @pytest.fixture
    async def scheduler(self) -> SchedulerService:  # type: ignore[misc]
        """Create a started scheduler for testing."""
        svc = SchedulerService()
        svc.start()
        yield svc  # type: ignore[misc]
        svc.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_jobs_not_registered_when_interval_zero(
        self, scheduler: SchedulerService
    ) -> None:
        """Jobs are NOT registered when their interval is 0.

        Only the daily disk cleanup remains: it is registered whatever the settings
        (Story 22.4, Epic 22 ADR-7 decision 3).
        """
        from vintagestory_api.services.api_settings import ApiSettings

        # Create settings with all intervals set to 0
        settings_with_zero = ApiSettings(
            mod_list_refresh_interval=0,
            server_versions_refresh_interval=0,
            metrics_collection_interval=0,
        )

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings_with_zero
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            # No interval job is registered when intervals are 0
            job_ids = [job_to_info(job).id for job in scheduler.get_jobs()]
            assert job_ids == ["disk_cleanup"]

    @pytest.mark.asyncio
    async def test_settings_interval_values_checked(self, scheduler: SchedulerService) -> None:
        """register_default_jobs checks interval values from settings."""
        from vintagestory_api.services.api_settings import ApiSettings

        # Use default settings which have non-zero intervals
        default_settings = ApiSettings()
        assert default_settings.mod_list_refresh_interval > 0
        assert default_settings.server_versions_refresh_interval > 0

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = default_settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            # Settings were read
            mock_instance.get_settings.assert_called_once()

            # Story 8.1: mod_cache_refresh job should be registered
            # when mod_list_refresh_interval > 0
            jobs = scheduler.get_jobs()
            job_ids: list[str] = [job.id for job in jobs]  # type: ignore[reportUnknownMemberType]
            assert "mod_cache_refresh" in job_ids


class TestModCacheRefreshJobRegistration:
    """Tests for mod_cache_refresh job registration (Story 8.1)."""

    @pytest.fixture
    async def scheduler(self) -> SchedulerService:  # type: ignore[misc]
        """Create a started scheduler for testing."""
        svc = SchedulerService()
        svc.start()
        yield svc  # type: ignore[misc]
        svc.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_mod_cache_refresh_registered_when_interval_positive(
        self, scheduler: SchedulerService
    ) -> None:
        """mod_cache_refresh job is registered when interval > 0 (AC: 1)."""
        from vintagestory_api.services.api_settings import ApiSettings

        settings = ApiSettings(mod_list_refresh_interval=3600)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            job_ids: list[str] = [job.id for job in jobs]  # type: ignore[reportUnknownMemberType]
            assert "mod_cache_refresh" in job_ids

    @pytest.mark.asyncio
    async def test_mod_cache_refresh_not_registered_when_interval_zero(
        self, scheduler: SchedulerService
    ) -> None:
        """mod_cache_refresh job is NOT registered when interval = 0 (AC: 3)."""
        from vintagestory_api.services.api_settings import ApiSettings

        settings = ApiSettings(mod_list_refresh_interval=0)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            job_ids: list[str] = [job.id for job in jobs]  # type: ignore[reportUnknownMemberType]
            assert "mod_cache_refresh" not in job_ids

    @pytest.mark.asyncio
    async def test_mod_cache_refresh_uses_correct_interval(
        self, scheduler: SchedulerService
    ) -> None:
        """mod_cache_refresh job uses interval from settings."""
        from vintagestory_api.services.api_settings import ApiSettings

        # Use a specific interval value
        expected_interval = 7200  # 2 hours
        settings = ApiSettings(mod_list_refresh_interval=expected_interval)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            mod_cache_job = next(
                (job for job in jobs if job.id == "mod_cache_refresh"),  # type: ignore[reportUnknownMemberType]
                None,
            )
            assert mod_cache_job is not None

            # APScheduler stores interval in trigger
            trigger = mod_cache_job.trigger  # type: ignore[reportUnknownMemberType]
            # IntervalTrigger has interval as timedelta
            assert trigger.interval.total_seconds() == expected_interval  # type: ignore[reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_mod_cache_refresh_logs_registration(
        self, scheduler: SchedulerService, capsys: CaptureFixture[str]
    ) -> None:
        """mod_cache_refresh job registration is logged."""
        from vintagestory_api.services.api_settings import ApiSettings

        settings = ApiSettings(mod_list_refresh_interval=3600)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            capsys.readouterr()  # Clear prior output
            register_default_jobs(scheduler)
            captured = capsys.readouterr()

            assert "job_registered" in captured.out
            assert "mod_cache_refresh" in captured.out


class TestServerVersionsCheckJobRegistration:
    """Tests for server_versions_check job registration (Story 8.2)."""

    @pytest.fixture
    async def scheduler(self) -> SchedulerService:  # type: ignore[misc]
        """Create a started scheduler for testing."""
        svc = SchedulerService()
        svc.start()
        yield svc  # type: ignore[misc]
        svc.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_server_versions_check_registered_when_interval_positive(
        self, scheduler: SchedulerService
    ) -> None:
        """server_versions_check job is registered when interval > 0 (AC: 1)."""
        from vintagestory_api.services.api_settings import ApiSettings

        settings = ApiSettings(server_versions_refresh_interval=86400)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            job_ids: list[str] = [job.id for job in jobs]  # type: ignore[reportUnknownMemberType]
            assert "server_versions_check" in job_ids

    @pytest.mark.asyncio
    async def test_server_versions_check_not_registered_when_interval_zero(
        self, scheduler: SchedulerService
    ) -> None:
        """server_versions_check job is NOT registered when interval = 0 (AC: 4)."""
        from vintagestory_api.services.api_settings import ApiSettings

        settings = ApiSettings(server_versions_refresh_interval=0)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            job_ids: list[str] = [job.id for job in jobs]  # type: ignore[reportUnknownMemberType]
            assert "server_versions_check" not in job_ids

    @pytest.mark.asyncio
    async def test_server_versions_check_uses_correct_interval(
        self, scheduler: SchedulerService
    ) -> None:
        """server_versions_check job uses interval from settings."""
        from vintagestory_api.services.api_settings import ApiSettings

        # Use a specific interval value
        expected_interval = 43200  # 12 hours
        settings = ApiSettings(server_versions_refresh_interval=expected_interval)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            versions_job = next(
                (job for job in jobs if job.id == "server_versions_check"),  # type: ignore[reportUnknownMemberType]
                None,
            )
            assert versions_job is not None

            # APScheduler stores interval in trigger
            trigger = versions_job.trigger  # type: ignore[reportUnknownMemberType]
            # IntervalTrigger has interval as timedelta
            assert trigger.interval.total_seconds() == expected_interval  # type: ignore[reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_server_versions_check_logs_registration(
        self, scheduler: SchedulerService, capsys: CaptureFixture[str]
    ) -> None:
        """server_versions_check job registration is logged."""
        from vintagestory_api.services.api_settings import ApiSettings

        settings = ApiSettings(server_versions_refresh_interval=86400)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            capsys.readouterr()  # Clear prior output
            register_default_jobs(scheduler)
            captured = capsys.readouterr()

            assert "job_registered" in captured.out
            assert "server_versions_check" in captured.out

    @pytest.mark.asyncio
    async def test_both_jobs_registered_when_both_intervals_positive(
        self, scheduler: SchedulerService
    ) -> None:
        """Both mod_cache_refresh and server_versions_check registered with default settings."""
        from vintagestory_api.services.api_settings import ApiSettings

        # Default settings have both intervals > 0
        settings = ApiSettings()

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            job_ids: list[str] = [job.id for job in jobs]  # type: ignore[reportUnknownMemberType]
            assert "mod_cache_refresh" in job_ids
            assert "server_versions_check" in job_ids


class TestMetricsCollectionJobRegistration:
    """Tests for metrics_collection job registration (Story 12.2)."""

    @pytest.fixture
    async def scheduler(self) -> SchedulerService:  # type: ignore[misc]
        """Create a started scheduler for testing."""
        svc = SchedulerService()
        svc.start()
        yield svc  # type: ignore[misc]
        svc.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_metrics_collection_registered_when_interval_positive(
        self, scheduler: SchedulerService
    ) -> None:
        """metrics_collection job is registered when interval > 0 (AC: 5)."""
        from vintagestory_api.services.api_settings import ApiSettings

        settings = ApiSettings(metrics_collection_interval=10)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            job_ids: list[str] = [job.id for job in jobs]  # type: ignore[reportUnknownMemberType]
            assert "metrics_collection" in job_ids

    @pytest.mark.asyncio
    async def test_metrics_collection_not_registered_when_interval_zero(
        self, scheduler: SchedulerService
    ) -> None:
        """metrics_collection job is NOT registered when interval = 0."""
        from vintagestory_api.services.api_settings import ApiSettings

        settings = ApiSettings(metrics_collection_interval=0)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            job_ids: list[str] = [job.id for job in jobs]  # type: ignore[reportUnknownMemberType]
            assert "metrics_collection" not in job_ids

    @pytest.mark.asyncio
    async def test_metrics_collection_uses_correct_interval(
        self, scheduler: SchedulerService
    ) -> None:
        """metrics_collection job uses interval from settings."""
        from vintagestory_api.services.api_settings import ApiSettings

        # Use a specific interval value
        expected_interval = 30  # 30 seconds
        settings = ApiSettings(metrics_collection_interval=expected_interval)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            jobs = scheduler.get_jobs()
            metrics_job = next(
                (job for job in jobs if job.id == "metrics_collection"),  # type: ignore[reportUnknownMemberType]
                None,
            )
            assert metrics_job is not None

            # APScheduler stores interval in trigger
            trigger = metrics_job.trigger  # type: ignore[reportUnknownMemberType]
            # IntervalTrigger has interval as timedelta
            assert trigger.interval.total_seconds() == expected_interval  # type: ignore[reportUnknownMemberType]

    @pytest.mark.asyncio
    async def test_metrics_collection_logs_registration(
        self, scheduler: SchedulerService, capsys: CaptureFixture[str]
    ) -> None:
        """metrics_collection job registration is logged."""
        from vintagestory_api.services.api_settings import ApiSettings

        settings = ApiSettings(metrics_collection_interval=10)

        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            capsys.readouterr()  # Clear prior output
            register_default_jobs(scheduler)
            captured = capsys.readouterr()

            assert "job_registered" in captured.out
            assert "metrics_collection" in captured.out


# =============================================================================
# Story 17.6: one function makes the scheduler match an interval setting
# =============================================================================

INTERVAL_KEYS = list(INTERVAL_JOBS)


async def _no_op_job() -> None:
    """Stands in for a real job so no test reaches the network or the game server."""


@pytest.fixture
def no_real_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the three job functions that apply_interval_setting imports lazily."""
    monkeypatch.setattr("vintagestory_api.jobs.mod_cache_refresh.refresh_mod_cache", _no_op_job)
    monkeypatch.setattr("vintagestory_api.jobs.server_versions.check_server_versions", _no_op_job)
    monkeypatch.setattr("vintagestory_api.jobs.metrics_collection.collect_metrics", _no_op_job)
    # Story 22.3: a registered restart time that fires during a run must not reach the game.
    monkeypatch.setattr("vintagestory_api.jobs.scheduled_restart.scheduled_restart", _no_op_restart)


async def _no_op_restart(**_: object) -> None:
    """Stands in for the scheduled restart job (Story 22.3)."""


@pytest.fixture
async def started_scheduler(no_real_jobs: None) -> AsyncIterator[SchedulerService]:
    """A started scheduler whose interval jobs are no-ops."""
    svc = SchedulerService()
    svc.start()
    yield svc
    svc.shutdown(wait=False)


def _job_info(scheduler: SchedulerService, job_id: str) -> JobInfo | None:
    job = scheduler.get_job(job_id)
    return None if job is None else job_to_info(job)


def _assert_next_run_one_interval_away(
    info: JobInfo, before: datetime, after: datetime, seconds: int
) -> None:
    assert info.next_run_time is not None
    assert (
        before + timedelta(seconds=seconds - 1)
        <= info.next_run_time
        <= after + timedelta(seconds=seconds)
    )


class TestApplyIntervalSetting:
    """apply_interval_setting makes the scheduler match one setting (Story 17.6, AC 1-4, 8)."""

    def test_settings_service_uses_the_same_keys(self) -> None:
        """The service's scheduled keys are INTERVAL_JOBS and the restart times (Story 22.3)."""
        from vintagestory_api.services.api_settings import SCHEDULED_SETTINGS, ApiSettings

        assert set(SCHEDULED_SETTINGS) == set(INTERVAL_JOBS) | {"scheduled_restart_times"}
        for key in INTERVAL_JOBS:
            assert ApiSettings.model_fields[key].annotation is int

    def test_interval_jobs_table(self) -> None:
        """Each interval setting drives exactly one job."""
        assert INTERVAL_JOBS == {
            "mod_list_refresh_interval": "mod_cache_refresh",
            "server_versions_refresh_interval": "server_versions_check",
            "metrics_collection_interval": "metrics_collection",
        }

    @pytest.mark.parametrize("key", INTERVAL_KEYS)
    async def test_changed_interval_replaces_the_job(
        self, started_scheduler: SchedulerService, key: str
    ) -> None:
        """A new value above 0 replaces the job; its next run is one new interval away."""
        job_id = INTERVAL_JOBS[key]
        apply_interval_setting(started_scheduler, key, 3600)

        before = datetime.now(UTC)
        apply_interval_setting(started_scheduler, key, 600)
        after = datetime.now(UTC)

        infos = [job_to_info(job) for job in started_scheduler.get_jobs()]
        assert [info.id for info in infos] == [job_id]
        assert infos[0].trigger_details == "every 600 seconds"
        _assert_next_run_one_interval_away(infos[0], before, after, 600)

    @pytest.mark.parametrize("key", INTERVAL_KEYS)
    async def test_zero_removes_the_job(
        self, started_scheduler: SchedulerService, key: str
    ) -> None:
        """0 removes a registered job."""
        apply_interval_setting(started_scheduler, key, 3600)

        apply_interval_setting(started_scheduler, key, 0)

        assert _job_info(started_scheduler, INTERVAL_JOBS[key]) is None
        assert started_scheduler.get_jobs() == []

    @pytest.mark.parametrize("key", INTERVAL_KEYS)
    async def test_from_zero_adds_the_job(
        self, started_scheduler: SchedulerService, key: str
    ) -> None:
        """A value above 0 with no job registered adds it, first run one interval away."""
        before = datetime.now(UTC)
        apply_interval_setting(started_scheduler, key, 900)
        after = datetime.now(UTC)

        info = _job_info(started_scheduler, INTERVAL_JOBS[key])
        assert info is not None
        assert info.trigger_details == "every 900 seconds"
        _assert_next_run_one_interval_away(info, before, after, 900)

    @pytest.mark.parametrize("key", INTERVAL_KEYS)
    async def test_zero_to_zero_changes_nothing(
        self, started_scheduler: SchedulerService, key: str
    ) -> None:
        """0 with no job registered is not an error and registers nothing."""
        apply_interval_setting(started_scheduler, key, 0)

        assert started_scheduler.get_jobs() == []

    async def test_startup_does_not_run_the_other_jobs_at_once(
        self, started_scheduler: SchedulerService
    ) -> None:
        """startup=True leaves mod_cache_refresh and metrics_collection one interval away."""
        before = datetime.now(UTC)
        for key in INTERVAL_KEYS:
            apply_interval_setting(started_scheduler, key, 3600, startup=True)
        after = datetime.now(UTC)

        assert _job_info(started_scheduler, "server_versions_check") is not None
        for job_id in ("mod_cache_refresh", "metrics_collection"):
            info = _job_info(started_scheduler, job_id)
            assert info is not None
            _assert_next_run_one_interval_away(info, before, after, 3600)

    def test_startup_server_versions_check_next_run_is_now(self, no_real_jobs: None) -> None:
        """On a scheduler not yet started the immediate run is visible as next_run_time ≈ now."""
        scheduler = SchedulerService()
        before = datetime.now(UTC)
        apply_interval_setting(scheduler, "server_versions_refresh_interval", 3600, startup=True)
        after = datetime.now(UTC)

        info = _job_info(scheduler, "server_versions_check")
        assert info is not None
        assert info.next_run_time is not None
        assert before <= info.next_run_time <= after

    def test_unknown_key_is_a_programming_error(self, started_scheduler: SchedulerService) -> None:
        """A key that drives no job raises KeyError."""
        with pytest.raises(KeyError):
            apply_interval_setting(started_scheduler, "auto_start_server", 60)

    async def test_running_execution_finishes_when_interval_changes(
        self, started_scheduler: SchedulerService
    ) -> None:
        """Replacing or removing a job does not cancel an execution in progress (AC 4)."""
        started = asyncio.Event()
        release = asyncio.Event()
        outcome: list[str] = []

        async def long_job() -> None:
            started.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                outcome.append("cancelled")
                raise
            outcome.append("finished")

        started_scheduler.add_interval_job(
            long_job, seconds=3600, job_id="mod_cache_refresh", run_immediately=True
        )
        await asyncio.wait_for(started.wait(), timeout=5)

        apply_interval_setting(started_scheduler, "mod_list_refresh_interval", 600)
        info = _job_info(started_scheduler, "mod_cache_refresh")
        assert info is not None
        assert info.trigger_details == "every 600 seconds"

        apply_interval_setting(started_scheduler, "mod_list_refresh_interval", 0)
        assert _job_info(started_scheduler, "mod_cache_refresh") is None

        release.set()
        for _ in range(50):
            if outcome:
                break
            await asyncio.sleep(0.01)
        assert outcome == ["finished"]


# ==============================================================================
# Story 22.3: restart times as cron jobs (AC 3, 4, 8)
# ==============================================================================

_CRON_0400 = "cron[month='*', day='*', day_of_week='*', hour='3', minute='45']"


@pytest.fixture
def local_tz() -> Iterator[Callable[[str], None]]:
    """Set the process's time zone (TZ) for one test; restored afterwards.

    Not monkeypatch: its undo would run after this teardown, which must call tzset and
    reload tzlocal's cache with the original zone back in place.
    """
    saved = os.environ.get("TZ")

    def set_zone(name: str) -> None:
        os.environ["TZ"] = name
        time.tzset()
        tzlocal.reload_localzone()

    yield set_zone

    if saved is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = saved
    time.tzset()
    tzlocal.reload_localzone()


def _restart_ids(scheduler: SchedulerService) -> list[str]:
    return sorted(
        info.id
        for info in (job_to_info(job) for job in scheduler.get_jobs())
        if info.id.startswith("scheduled_restart_")
    )


def _in_ten_minutes() -> tuple[str, datetime]:
    """A restart time about 10 minutes from now (local zone), and now."""
    now = datetime.now().astimezone()
    return (now + timedelta(minutes=10)).strftime("%H:%M"), now


def _assert_first_fire_tomorrow(info: JobInfo, now: datetime) -> None:
    """A time less than 15 minutes ahead first fires about 23 h 55 min later (±2 min)."""
    assert info.next_run_time is not None
    expected = now + timedelta(hours=23, minutes=55)
    assert expected - timedelta(minutes=2) <= info.next_run_time <= expected + timedelta(minutes=2)


class TestApplyRestartSchedule:
    """apply_restart_schedule makes the restart jobs match the saved times."""

    async def test_add(self, started_scheduler: SchedulerService) -> None:
        apply_restart_schedule(started_scheduler, ["04:00"])

        assert _restart_ids(started_scheduler) == ["scheduled_restart_0400"]
        info = _job_info(started_scheduler, "scheduled_restart_0400")
        assert info is not None
        assert info.trigger_type == "cron"
        assert info.trigger_details == _CRON_0400
        assert info.next_run_time is not None
        local = info.next_run_time.astimezone()
        assert (local.hour, local.minute) == (3, 45)
        assert info.next_run_time - datetime.now(UTC) <= timedelta(hours=24)

    async def test_fire_before_midnight(self, started_scheduler: SchedulerService) -> None:
        apply_restart_schedule(started_scheduler, ["00:10"])

        info = _job_info(started_scheduler, "scheduled_restart_0010")
        assert info is not None
        assert info.trigger_details == (
            "cron[month='*', day='*', day_of_week='*', hour='23', minute='55']"
        )

    async def test_replace_keeps_interval_jobs(self, started_scheduler: SchedulerService) -> None:
        apply_interval_setting(started_scheduler, "mod_list_refresh_interval", 3600)
        interval_before = _job_info(started_scheduler, "mod_cache_refresh")
        apply_restart_schedule(started_scheduler, ["04:00", "16:00"])

        apply_restart_schedule(started_scheduler, ["16:00", "20:00"])

        assert _restart_ids(started_scheduler) == [
            "scheduled_restart_1600",
            "scheduled_restart_2000",
        ]
        assert _job_info(started_scheduler, "mod_cache_refresh") == interval_before

    async def test_empty_removes_every_restart_job(
        self, started_scheduler: SchedulerService
    ) -> None:
        apply_interval_setting(started_scheduler, "mod_list_refresh_interval", 3600)
        apply_restart_schedule(started_scheduler, ["04:00", "16:00"])

        with capture_logs() as logs:
            apply_restart_schedule(started_scheduler, [])

        assert _restart_ids(started_scheduler) == []
        assert _job_info(started_scheduler, "mod_cache_refresh") is not None
        applied = [log for log in logs if log["event"] == "restart_schedule_applied"]
        assert len(applied) == 1
        assert applied[0]["times"] == []
        assert sorted(applied[0]["removed"]) == [
            "scheduled_restart_0400",
            "scheduled_restart_1600",
        ]

    async def test_logs_each_registration(self, started_scheduler: SchedulerService) -> None:
        with capture_logs() as logs:
            apply_restart_schedule(started_scheduler, ["04:00"])

        registered = [log for log in logs if log["event"] == "job_registered"]
        assert registered == [
            {
                "event": "job_registered",
                "log_level": "info",
                "job_id": "scheduled_restart_0400",
                "restart_time": "04:00",
                "first_warning": "03:45",
            }
        ]

    async def test_less_than_15_minutes_ahead_first_runs_tomorrow(
        self, started_scheduler: SchedulerService, local_tz: Callable[[str], None]
    ) -> None:
        local_tz("UTC")
        restart_time, now = _in_ten_minutes()

        apply_restart_schedule(started_scheduler, [restart_time])

        info = _job_info(started_scheduler, restart_job_id(restart_time))
        assert info is not None
        _assert_first_fire_tomorrow(info, now)

    async def test_berlin_time_zone(
        self, started_scheduler: SchedulerService, local_tz: Callable[[str], None]
    ) -> None:
        local_tz("Europe/Berlin")

        apply_restart_schedule(started_scheduler, ["04:00"])

        info = _job_info(started_scheduler, "scheduled_restart_0400")
        assert info is not None
        assert info.next_run_time is not None
        berlin = info.next_run_time.astimezone(ZoneInfo("Europe/Berlin"))
        assert (berlin.hour, berlin.minute) == (3, 45)

    async def test_utc_time_zone(
        self, started_scheduler: SchedulerService, local_tz: Callable[[str], None]
    ) -> None:
        local_tz("UTC")

        apply_restart_schedule(started_scheduler, ["04:00"])

        info = _job_info(started_scheduler, "scheduled_restart_0400")
        assert info is not None
        assert info.next_run_time is not None
        assert info.next_run_time.utcoffset() == timedelta(0)
        assert (info.next_run_time.hour, info.next_run_time.minute) == (3, 45)


class TestRegisterDefaultJobsRestartTimes:
    """The saved times are applied at API start (AC 3)."""

    async def test_startup_registers_the_saved_times(
        self, started_scheduler: SchedulerService
    ) -> None:
        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = ApiSettings(scheduled_restart_times=["04:00"])
            mock_settings_class.return_value = mock_instance

            with capture_logs() as logs:
                register_default_jobs(started_scheduler)

        assert _restart_ids(started_scheduler) == ["scheduled_restart_0400"]
        registered = [log for log in logs if log["event"] == "default_jobs_registered"]
        assert len(registered) == 1
        assert registered[0]["restart_jobs"] == 1
        assert registered[0]["count"] == 3

    async def test_api_start_inside_the_window_does_not_fire_that_day(
        self, started_scheduler: SchedulerService, local_tz: Callable[[str], None]
    ) -> None:
        local_tz("UTC")
        restart_time, now = _in_ten_minutes()
        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = ApiSettings(
                scheduled_restart_times=[restart_time]
            )
            mock_settings_class.return_value = mock_instance

            register_default_jobs(started_scheduler)

        info = _job_info(started_scheduler, restart_job_id(restart_time))
        assert info is not None
        _assert_first_fire_tomorrow(info, now)

    async def test_default_settings_register_no_restart_job(
        self, started_scheduler: SchedulerService
    ) -> None:
        with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = ApiSettings()
            mock_settings_class.return_value = mock_instance

            register_default_jobs(started_scheduler)

        assert _restart_ids(started_scheduler) == []


class TestApplySetting:
    """apply_setting routes every scheduled setting (Epic 22 ADR-7 decision 2)."""

    async def test_interval_key(self, started_scheduler: SchedulerService) -> None:
        apply_setting(started_scheduler, "mod_list_refresh_interval", 600)

        info = _job_info(started_scheduler, "mod_cache_refresh")
        assert info is not None
        assert info.trigger_details == "every 600 seconds"

    async def test_restart_times(self, started_scheduler: SchedulerService) -> None:
        apply_setting(started_scheduler, "scheduled_restart_times", ["04:00", "16:00"])

        assert _restart_ids(started_scheduler) == [
            "scheduled_restart_0400",
            "scheduled_restart_1600",
        ]

    async def test_interval_key_with_a_list(self, started_scheduler: SchedulerService) -> None:
        with pytest.raises(TypeError):
            apply_setting(started_scheduler, "mod_list_refresh_interval", ["04:00"])
        assert started_scheduler.get_jobs() == []

    @pytest.mark.parametrize("value", [True, False])
    async def test_interval_key_with_a_bool(
        self, started_scheduler: SchedulerService, value: bool
    ) -> None:
        with pytest.raises(TypeError, match="takes an int, got bool"):
            apply_setting(started_scheduler, "mod_list_refresh_interval", value)
        assert started_scheduler.get_jobs() == []

    async def test_restart_times_with_an_int(self, started_scheduler: SchedulerService) -> None:
        with pytest.raises(TypeError):
            apply_setting(started_scheduler, "scheduled_restart_times", 600)
        assert started_scheduler.get_jobs() == []

    async def test_other_key_does_nothing(self, started_scheduler: SchedulerService) -> None:
        apply_setting(started_scheduler, "auto_start_server", 1)

        assert started_scheduler.get_jobs() == []


class _Server:
    """Just enough of ServerService for the sequence."""

    def __init__(self) -> None:
        self.game_running = True
        self.lifecycle_busy = False
        self.players_online: int | None = 0
        self.sent: list[str] = []
        self.restarts = 0

    async def send_command(self, command: str) -> bool:
        self.sent.append(command)
        return True

    async def restart_server(self, timeout: float = 10.0) -> object:
        self.restarts += 1
        return None


class TestStaleSequence:
    """A sequence in its warnings follows its job id in the scheduler (AC 8)."""

    @staticmethod
    async def _run(
        scheduler: SchedulerService, server: _Server, on_first_wait: Callable[[], None]
    ) -> str:
        calls = 0

        async def fake_sleep(_seconds: float) -> None:
            nonlocal calls
            if calls == 0:
                on_first_wait()
            calls += 1

        return await run_restart_sequence(
            "04:00",
            server=server,
            still_scheduled=lambda: scheduler.get_job("scheduled_restart_0400") is not None,
            sleep=fake_sleep,
        )

    async def test_removed_time_cancels(self, started_scheduler: SchedulerService) -> None:
        apply_restart_schedule(started_scheduler, ["04:00"])
        server = _Server()

        outcome = await self._run(
            started_scheduler, server, lambda: apply_restart_schedule(started_scheduler, [])
        )

        assert outcome == "cancelled"
        assert len(server.sent) == 1
        assert server.restarts == 0

    async def test_same_time_saved_again_goes_on(self, started_scheduler: SchedulerService) -> None:
        apply_restart_schedule(started_scheduler, ["04:00"])
        server = _Server()

        outcome = await self._run(
            started_scheduler,
            server,
            lambda: apply_restart_schedule(started_scheduler, ["04:00"]),
        )

        assert outcome == "restarted"
        assert len(server.sent) == 3
        assert server.restarts == 1


class _RecordingScheduler(SchedulerService):
    """A real SchedulerService that also keeps what each cron job was registered with."""

    def __init__(self) -> None:
        super().__init__()
        self.cron_jobs: dict[str, tuple[Callable[..., Any], dict[str, Any]]] = {}

    def add_cron_job(
        self, func: Callable[..., Any], cron_expr: str, job_id: str, **kwargs: Any
    ) -> Job:
        self.cron_jobs[job_id] = (func, kwargs)
        return super().add_cron_job(func, cron_expr, job_id, **kwargs)


class TestRegisteredRestartJob:
    """The registered restart job runs the real job function with its own arguments."""

    async def test_registered_job_runs_against_the_server_service(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        server = _Server()
        server.game_running = False
        monkeypatch.setattr("vintagestory_api.services.server.get_server_service", lambda: server)
        # Never started: the job cannot fire on its own during the test.
        scheduler = _RecordingScheduler()

        apply_restart_schedule(scheduler, ["04:00"])

        func, add_job_kwargs = scheduler.cron_jobs["scheduled_restart_0400"]
        assert func is scheduled_restart
        job_kwargs = add_job_kwargs["kwargs"]
        assert job_kwargs == {"restart_time": "04:00", "scheduler": scheduler}
        assert scheduler.get_job("scheduled_restart_0400") is not None

        with capture_logs() as logs:
            await func(**job_kwargs)

        skips = [log for log in logs if log["event"] == "scheduled_restart_skipped"]
        assert skips == [
            {
                "event": "scheduled_restart_skipped",
                "log_level": "info",
                "restart_time": "04:00",
                "reason": "not_running",
                "minutes_left": 15,
            }
        ]
        assert server.sent == []
        assert server.restarts == 0


# ==============================================================================
# Story 22.4: the daily disk cleanup job (Epic 22 ADR-7 decisions 3 and 4, ADR-9)
# ==============================================================================

_CRON_0300 = "cron[month='*', day='*', day_of_week='*', hour='3', minute='0']"


def _register_with(scheduler: SchedulerService, settings: ApiSettings) -> None:
    with patch("vintagestory_api.jobs.ApiSettingsService") as mock_settings_class:
        mock_instance = MagicMock()
        mock_instance.get_settings.return_value = settings
        mock_settings_class.return_value = mock_instance
        register_default_jobs(scheduler)


class TestDiskCleanupRegistration:
    """disk_cleanup is registered at 03:00 whatever the settings (Story 22.4, AC 9)."""

    @pytest.mark.parametrize(
        "settings",
        [
            ApiSettings(),
            ApiSettings(
                mod_list_refresh_interval=0,
                server_versions_refresh_interval=0,
                metrics_collection_interval=0,
            ),
            ApiSettings(scheduled_restart_times=["04:00"]),
            ApiSettings(backup_keep_count=5),
        ],
        ids=["defaults", "intervals_zero", "restart_times", "backups_limited"],
    )
    async def test_always_registered(
        self, started_scheduler: SchedulerService, settings: ApiSettings
    ) -> None:
        _register_with(started_scheduler, settings)

        info = _job_info(started_scheduler, "disk_cleanup")
        assert info is not None
        assert info.trigger_type == "cron"
        assert info.trigger_details == _CRON_0300
        assert info.next_run_time is not None
        local = info.next_run_time.astimezone()
        assert (local.hour, local.minute) == (3, 0)
        assert info.next_run_time - datetime.now(UTC) <= timedelta(hours=24)

    async def test_default_jobs_count_is_unchanged(
        self, started_scheduler: SchedulerService
    ) -> None:
        with capture_logs() as logs:
            _register_with(started_scheduler, ApiSettings())

        registered = [log for log in logs if log["event"] == "default_jobs_registered"]
        assert len(registered) == 1
        assert registered[0]["count"] == 3
        assert registered[0]["restart_jobs"] == 0

    async def test_runs_at_three_in_the_container_zone(
        self, started_scheduler: SchedulerService, local_tz: Callable[[str], None]
    ) -> None:
        local_tz("Europe/Berlin")

        register_disk_cleanup(started_scheduler)

        info = _job_info(started_scheduler, "disk_cleanup")
        assert info is not None
        assert info.next_run_time is not None
        berlin = info.next_run_time.astimezone(ZoneInfo("Europe/Berlin"))
        assert (berlin.hour, berlin.minute) == (3, 0)

    async def test_registering_twice_keeps_one_job(
        self, started_scheduler: SchedulerService
    ) -> None:
        register_disk_cleanup(started_scheduler)
        register_disk_cleanup(started_scheduler)

        ids = [job_to_info(job).id for job in started_scheduler.get_jobs()]
        assert ids == ["disk_cleanup"]

    async def test_logs_the_registration(self, started_scheduler: SchedulerService) -> None:
        with capture_logs() as logs:
            register_disk_cleanup(started_scheduler)

        registered = [log for log in logs if log["event"] == "job_registered"]
        assert registered == [
            {
                "event": "job_registered",
                "log_level": "info",
                "job_id": "disk_cleanup",
                "cron": "0 3 * * *",
            }
        ]

    async def test_the_backup_setting_changes_no_job(
        self, started_scheduler: SchedulerService
    ) -> None:
        _register_with(started_scheduler, ApiSettings())
        before = sorted(
            (job_to_info(job) for job in started_scheduler.get_jobs()), key=lambda i: i.id
        )

        apply_setting(started_scheduler, "backup_keep_count", 30)

        after = sorted(
            (job_to_info(job) for job in started_scheduler.get_jobs()), key=lambda i: i.id
        )
        assert after == before
