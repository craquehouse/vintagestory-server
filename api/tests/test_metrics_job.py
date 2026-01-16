"""Tests for metrics collection job.

Story 12.2: Metrics Collection Service

Tests cover:
- Job execution collects metrics successfully
- Job uses @safe_job decorator for error handling
- Job stores metrics in the buffer
"""

from __future__ import annotations

from collections.abc import Generator
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from vintagestory_api.jobs.metrics_collection import collect_metrics
from vintagestory_api.services.metrics import MetricsBuffer, MetricsService, reset_metrics_service


class TestCollectMetricsJob:
    """Tests for collect_metrics() job function."""

    @pytest.fixture(autouse=True)
    def reset_service(self) -> Generator[None, None, None]:
        """Reset metrics service singleton before each test."""
        reset_metrics_service()
        yield
        reset_metrics_service()

    @pytest.mark.asyncio
    async def test_collect_metrics_executes_successfully(self) -> None:
        """collect_metrics() executes without error (AC: 1)."""
        # Should not raise
        await collect_metrics()

    @pytest.mark.asyncio
    async def test_collect_metrics_stores_in_buffer(self) -> None:
        """collect_metrics() stores metrics in the service buffer."""
        from vintagestory_api.services.metrics import get_metrics_service

        # Get the service and check initial state
        service = get_metrics_service()
        initial_count = len(service.buffer)

        await collect_metrics()

        # Buffer should have one more entry
        assert len(service.buffer) == initial_count + 1

    @pytest.mark.asyncio
    async def test_collect_metrics_logs_start_event(
        self, captured_logs: StringIO
    ) -> None:
        """collect_metrics() logs job start event (via @safe_job)."""
        await collect_metrics()

        assert "metrics_collection_started" in captured_logs.getvalue()

    @pytest.mark.asyncio
    async def test_collect_metrics_logs_completion_event(
        self, captured_logs: StringIO
    ) -> None:
        """collect_metrics() logs job completion event (via @safe_job)."""
        await collect_metrics()

        assert "metrics_collection_completed" in captured_logs.getvalue()

    @pytest.mark.asyncio
    async def test_collect_metrics_logs_via_service(
        self, captured_logs: StringIO
    ) -> None:
        """collect_metrics() logs collected metrics details via service."""
        await collect_metrics()

        output = captured_logs.getvalue()
        # Logging is handled by MetricsService.collect(), not the job
        assert "metrics_collected" in output
        assert "api_memory_mb" in output

    @pytest.mark.asyncio
    async def test_collect_metrics_handles_service_error_gracefully(
        self, captured_logs: StringIO
    ) -> None:
        """collect_metrics() handles errors gracefully via @safe_job."""
        with patch(
            "vintagestory_api.jobs.metrics_collection.get_metrics_service"
        ) as mock_get:
            mock_service = MagicMock()
            mock_service.collect.side_effect = RuntimeError("Simulated error")
            mock_get.return_value = mock_service

            # Should not raise due to @safe_job decorator
            result = await collect_metrics()

            # Returns None on error
            assert result is None
            # Error should be logged
            assert "metrics_collection_failed" in captured_logs.getvalue()


class TestCollectMetricsJobIntegration:
    """Integration tests for metrics collection job."""

    @pytest.fixture(autouse=True)
    def reset_service(self) -> Generator[None, None, None]:
        """Reset metrics service singleton before each test."""
        reset_metrics_service()
        yield
        reset_metrics_service()

    @pytest.mark.asyncio
    async def test_multiple_collections_accumulate_in_buffer(self) -> None:
        """Multiple job executions accumulate metrics in buffer."""
        from vintagestory_api.services.metrics import get_metrics_service

        service = get_metrics_service()

        # Run job multiple times
        await collect_metrics()
        await collect_metrics()
        await collect_metrics()

        # Should have 3 entries (plus any from service initialization)
        assert len(service.buffer) >= 3

    @pytest.mark.asyncio
    async def test_buffer_eviction_works_with_job(self) -> None:
        """Buffer evicts oldest entries when job fills it beyond capacity."""
        # Create service with tiny buffer
        small_buffer = MetricsBuffer(capacity=2)
        service = MetricsService(buffer=small_buffer)

        with patch(
            "vintagestory_api.jobs.metrics_collection.get_metrics_service",
            return_value=service,
        ):
            # Run job 3 times with capacity 2
            await collect_metrics()
            await collect_metrics()
            await collect_metrics()

            # Buffer should be at capacity (2), oldest evicted
            assert len(service.buffer) == 2
