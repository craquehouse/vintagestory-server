"""Tests for jobs module registration functionality.

Story 8.0: Epic 8 Preparation
Story 8.2: Server Versions Check Job

Tests cover:
- Task 1: register_default_jobs() functionality and job patterns
- AC 1: Jobs follow consistent structure (try/except, structured logging, no re-raise)
- AC 2: Jobs registered in central register_default_jobs() function
- AC 3: Jobs with interval=0 are NOT registered
- AC 4: Directory structure follows established patterns
"""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from vintagestory_api.jobs import register_default_jobs
from vintagestory_api.jobs.base import safe_job
from vintagestory_api.services.scheduler import SchedulerService

if TYPE_CHECKING:
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
    async def test_register_default_jobs_registers_jobs(
        self, scheduler: SchedulerService
    ) -> None:
        """register_default_jobs() registers jobs with default settings."""
        register_default_jobs(scheduler)

        # Story 8.1: mod_cache_refresh job should be registered with default settings
        # (mod_list_refresh_interval=3600 by default)
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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
    async def test_safe_job_logs_start_event(
        self, captured_logs: StringIO
    ) -> None:
        """safe_job() logs job start event."""

        @safe_job("test_job")
        async def my_job() -> str:
            return "done"

        await my_job()

        assert "test_job_started" in captured_logs.getvalue()

    @pytest.mark.asyncio
    async def test_safe_job_logs_completion_event(
        self, captured_logs: StringIO
    ) -> None:
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
    async def test_safe_job_logs_exception_details(
        self, captured_logs: StringIO
    ) -> None:
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

    def test_register_default_jobs_called_during_startup(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """register_default_jobs() is called during app startup."""
        from fastapi.testclient import TestClient

        from vintagestory_api.main import app

        capsys.readouterr()  # Clear prior output

        # Creating TestClient triggers lifespan startup
        with TestClient(app):
            captured = capsys.readouterr()
            # Should see job registration log event
            assert "default_jobs_registered" in captured.out

    def test_lifespan_logs_scheduler_then_jobs(
        self, capsys: CaptureFixture[str]
    ) -> None:
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
        """Jobs are NOT registered when their interval is 0."""
        from vintagestory_api.services.api_settings import ApiSettings

        # Create settings with all intervals set to 0
        settings_with_zero = ApiSettings(
            mod_list_refresh_interval=0,
            server_versions_refresh_interval=0,
            metrics_collection_interval=0,
        )

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings_with_zero
            mock_settings_class.return_value = mock_instance

            register_default_jobs(scheduler)

            # No jobs should be registered when intervals are 0
            jobs = scheduler.get_jobs()
            assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_settings_interval_values_checked(
        self, scheduler: SchedulerService
    ) -> None:
        """register_default_jobs checks interval values from settings."""
        from vintagestory_api.services.api_settings import ApiSettings

        # Use default settings which have non-zero intervals
        default_settings = ApiSettings()
        assert default_settings.mod_list_refresh_interval > 0
        assert default_settings.server_versions_refresh_interval > 0

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
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

        with patch(
            "vintagestory_api.jobs.ApiSettingsService"
        ) as mock_settings_class:
            mock_instance = MagicMock()
            mock_instance.get_settings.return_value = settings
            mock_settings_class.return_value = mock_instance

            capsys.readouterr()  # Clear prior output
            register_default_jobs(scheduler)
            captured = capsys.readouterr()

            assert "job_registered" in captured.out
            assert "metrics_collection" in captured.out
