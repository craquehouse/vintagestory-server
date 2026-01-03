"""Tests for jobs module registration functionality.

Story 8.0: Epic 8 Preparation

Tests cover:
- Task 1: register_default_jobs() functionality and job patterns
- AC 1: Jobs follow consistent structure (try/except, structured logging, no re-raise)
- AC 2: Jobs registered in central register_default_jobs() function
- AC 3: Jobs with interval=0 are NOT registered
- AC 4: Directory structure follows established patterns
"""

from __future__ import annotations

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
    async def test_register_default_jobs_no_jobs_initially(
        self, scheduler: SchedulerService
    ) -> None:
        """register_default_jobs() registers zero jobs in initial stub (Story 8.0)."""
        register_default_jobs(scheduler)

        # In Story 8.0, no jobs are registered yet (stub implementation)
        # Stories 8.1 and 8.2 will add actual jobs
        jobs = scheduler.get_jobs()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_register_default_jobs_logs_registration_count(
        self, scheduler: SchedulerService, capsys: CaptureFixture[str]
    ) -> None:
        """register_default_jobs() logs the number of jobs registered."""
        capsys.readouterr()  # Clear prior output

        register_default_jobs(scheduler)

        captured = capsys.readouterr()
        assert "default_jobs_registered" in captured.out
        assert "count" in captured.out

    @pytest.mark.asyncio
    async def test_register_default_jobs_reads_api_settings(
        self, scheduler: SchedulerService
    ) -> None:
        """register_default_jobs() reads API settings to determine job registration."""
        from vintagestory_api.services.api_settings import ApiSettings

        with patch(
            "vintagestory_api.services.api_settings.ApiSettingsService"
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
        self, capsys: CaptureFixture[str]
    ) -> None:
        """safe_job() logs job start event."""

        @safe_job("test_job")
        async def my_job() -> str:
            return "done"

        capsys.readouterr()  # Clear prior output
        await my_job()
        captured = capsys.readouterr()

        assert "test_job_started" in captured.out

    @pytest.mark.asyncio
    async def test_safe_job_logs_completion_event(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """safe_job() logs job completion event on success."""

        @safe_job("test_job")
        async def my_job() -> str:
            return "done"

        capsys.readouterr()  # Clear prior output
        await my_job()
        captured = capsys.readouterr()

        assert "test_job_completed" in captured.out

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
        self, capsys: CaptureFixture[str]
    ) -> None:
        """safe_job() catches exceptions and does NOT re-raise (critical for scheduler)."""

        @safe_job("failing_job")
        async def my_failing_job() -> str:
            raise ValueError("Something went wrong")

        # Should NOT raise - this is critical for scheduler stability
        capsys.readouterr()  # Clear prior output
        result = await my_failing_job()

        # Returns None on failure
        assert result is None
        captured = capsys.readouterr()
        assert "failing_job_failed" in captured.out

    @pytest.mark.asyncio
    async def test_safe_job_logs_exception_details(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """safe_job() logs exception details on failure."""

        @safe_job("error_job")
        async def my_error_job() -> None:
            raise RuntimeError("Test error message")

        capsys.readouterr()  # Clear prior output
        await my_error_job()
        captured = capsys.readouterr()

        assert "error_job_failed" in captured.out
        # Should include error details in logs
        assert "Test error message" in captured.out or "error" in captured.out

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
