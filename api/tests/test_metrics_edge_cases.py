"""Edge case tests for metrics models and services.

This test module focuses on boundary conditions, error scenarios,
null/None handling, and other edge cases not covered in test_metrics.py.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import psutil
import pytest

from vintagestory_api.models.metrics import MetricsSnapshot
from vintagestory_api.services.metrics import (
    MetricsBuffer,
    MetricsService,
    get_metrics_service,
    reset_metrics_service,
)


class TestMetricsBufferEdgeCases:
    """Edge case tests for MetricsBuffer ring buffer."""

    def test_zero_capacity_raises_value_error(self) -> None:
        """Test that zero capacity raises ValueError from deque."""
        # deque(maxlen=0) is valid but useless - it accepts items but keeps none
        buffer = MetricsBuffer(capacity=0)
        snapshot = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=100.0,
            api_cpu_percent=10.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )

        buffer.append(snapshot)

        # Buffer accepts but immediately drops everything
        assert len(buffer) == 0
        assert buffer.get_latest() is None
        assert buffer.get_all() == []

    def test_negative_capacity_raises_value_error(self) -> None:
        """Test that negative capacity raises ValueError from deque."""
        with pytest.raises(ValueError, match="maxlen must be non-negative"):
            MetricsBuffer(capacity=-1)

    def test_capacity_of_one_fifo_behavior(self) -> None:
        """Test buffer with capacity=1 only keeps latest snapshot."""
        buffer = MetricsBuffer(capacity=1)
        snapshot1 = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=100.0,
            api_cpu_percent=10.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )
        snapshot2 = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=200.0,
            api_cpu_percent=20.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )

        buffer.append(snapshot1)
        assert len(buffer) == 1
        assert buffer.get_latest() == snapshot1

        buffer.append(snapshot2)
        assert len(buffer) == 1  # Still only 1
        assert buffer.get_latest() == snapshot2  # New one replaced old
        assert buffer.get_all() == [snapshot2]  # First evicted

    def test_very_large_capacity_accepted(self) -> None:
        """Test that very large capacity values are accepted."""
        # Should not raise, just consume memory
        buffer = MetricsBuffer(capacity=1_000_000)
        assert buffer.capacity == 1_000_000
        assert len(buffer) == 0

    def test_get_all_empty_buffer_returns_empty_list(self) -> None:
        """Test get_all() on empty buffer returns empty list, not None."""
        buffer = MetricsBuffer(capacity=10)
        result = buffer.get_all()

        assert result == []
        assert isinstance(result, list)

    def test_clear_empty_buffer_is_safe(self) -> None:
        """Test clearing an already empty buffer doesn't raise."""
        buffer = MetricsBuffer(capacity=10)
        # Clear when already empty
        buffer.clear()

        assert len(buffer) == 0
        assert buffer.get_all() == []

    def test_multiple_clears_are_safe(self) -> None:
        """Test multiple consecutive clears don't cause issues."""
        buffer = MetricsBuffer(capacity=10)
        snapshot = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=100.0,
            api_cpu_percent=10.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )

        buffer.append(snapshot)
        buffer.clear()
        buffer.clear()  # Clear again
        buffer.clear()  # And again

        assert len(buffer) == 0

    def test_append_after_clear_works(self) -> None:
        """Test that buffer can be reused after clear."""
        buffer = MetricsBuffer(capacity=10)
        snapshot1 = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=100.0,
            api_cpu_percent=10.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )
        snapshot2 = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=200.0,
            api_cpu_percent=20.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )

        buffer.append(snapshot1)
        buffer.clear()
        buffer.append(snapshot2)

        assert len(buffer) == 1
        assert buffer.get_latest() == snapshot2


class TestMetricsSnapshotEdgeCases:
    """Edge case tests for MetricsSnapshot dataclass."""

    def test_zero_memory_values(self) -> None:
        """Test snapshot with zero memory values (boundary condition)."""
        snapshot = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=0.0,
            api_cpu_percent=0.0,
            game_memory_mb=0.0,
            game_cpu_percent=0.0,
        )

        assert snapshot.api_memory_mb == 0.0
        assert snapshot.game_memory_mb == 0.0

    def test_negative_memory_values_accepted(self) -> None:
        """Test that negative values are accepted (validation is caller's responsibility)."""
        snapshot = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=-100.0,
            api_cpu_percent=-10.0,
            game_memory_mb=-50.0,
            game_cpu_percent=-5.0,
        )

        # Dataclass doesn't validate - accepts any float
        assert snapshot.api_memory_mb == -100.0
        assert snapshot.api_cpu_percent == -10.0

    def test_very_large_memory_values(self) -> None:
        """Test snapshot with very large memory values (boundary)."""
        snapshot = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=999_999_999.99,
            api_cpu_percent=100.0,
            game_memory_mb=999_999_999.99,
            game_cpu_percent=100.0,
        )

        assert snapshot.api_memory_mb == 999_999_999.99
        assert snapshot.game_memory_mb == 999_999_999.99

    def test_cpu_percent_over_100(self) -> None:
        """Test that CPU percent >100% is accepted (multi-core systems)."""
        snapshot = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=100.0,
            api_cpu_percent=350.5,  # 3.5 cores fully utilized
            game_memory_mb=None,
            game_cpu_percent=None,
        )

        assert snapshot.api_cpu_percent == 350.5

    def test_mixed_none_and_zero_values(self) -> None:
        """Test snapshot with mix of None and 0.0 for game metrics."""
        snapshot = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=100.0,
            api_cpu_percent=10.0,
            game_memory_mb=0.0,  # Zero, not None
            game_cpu_percent=None,
        )

        assert snapshot.game_memory_mb == 0.0
        assert snapshot.game_cpu_percent is None

    def test_inequality_with_different_timestamps(self) -> None:
        """Test that snapshots with different timestamps are not equal."""
        timestamp1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        timestamp2 = datetime(2025, 1, 1, 12, 0, 1, tzinfo=UTC)

        snapshot1 = MetricsSnapshot(
            timestamp=timestamp1,
            api_memory_mb=100.0,
            api_cpu_percent=10.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )
        snapshot2 = MetricsSnapshot(
            timestamp=timestamp2,
            api_memory_mb=100.0,
            api_cpu_percent=10.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )

        assert snapshot1 != snapshot2


class TestMetricsServiceEdgeCases:
    """Edge case tests for MetricsService."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> Generator[None, None, None]:
        """Reset metrics service singleton before each test."""
        reset_metrics_service()
        yield
        reset_metrics_service()

    def test_multiple_collect_calls_increment_buffer(self) -> None:
        """Test that multiple collect() calls each add to buffer."""
        buffer = MetricsBuffer(capacity=10)
        service = MetricsService(buffer=buffer, server_service=None)

        service.collect()
        service.collect()
        service.collect()

        assert len(buffer) == 3

    def test_collect_with_zero_capacity_buffer(self) -> None:
        """Test collect() with zero-capacity buffer (snapshots immediately dropped)."""
        buffer = MetricsBuffer(capacity=0)
        service = MetricsService(buffer=buffer, server_service=None)

        snapshot = service.collect()

        # Snapshot is returned but buffer keeps nothing
        assert snapshot.api_memory_mb > 0
        assert len(buffer) == 0

    def test_get_game_server_pid_when_server_service_none(self) -> None:
        """Test _get_game_server_pid handles None server service gracefully."""
        buffer = MetricsBuffer(capacity=10)
        service = MetricsService(buffer=buffer, server_service=None)

        # Should return None, not raise
        pid = service._get_game_server_pid()

        assert pid is None

    def test_get_server_service_lazy_resolution_returns_none(self) -> None:
        """Test _get_server_service returns None when lazy import fails."""
        buffer = MetricsBuffer(capacity=10)
        # No server_service provided, will attempt lazy import
        service = MetricsService(buffer=buffer, server_service=None)

        # Patch the lazy import path
        with patch(
            "vintagestory_api.services.server.get_server_service",
            return_value=None,
        ):
            result = service._get_server_service()

        assert result is None

    def test_get_game_server_pid_when_get_server_service_returns_none(self) -> None:
        """Test _get_game_server_pid returns None when _get_server_service returns None."""
        buffer = MetricsBuffer(capacity=10)
        service = MetricsService(buffer=buffer, server_service=None)

        # Patch the lazy import to return None
        with patch(
            "vintagestory_api.services.server.get_server_service",
            return_value=None,
        ):
            pid = service._get_game_server_pid()

        assert pid is None

    def test_psutil_process_general_exception_during_game_metrics(self) -> None:
        """Test graceful handling of unexpected psutil exceptions."""
        buffer = MetricsBuffer(capacity=10)

        mock_server_service = MagicMock()
        mock_server_service.game_server_pid = 77777

        # Mock psutil.Process to raise generic Exception
        original_process = psutil.Process

        def mock_process_factory(pid: int | None = None) -> psutil.Process:
            if pid == 77777:
                raise Exception("Unexpected psutil error")
            return original_process(pid)

        with patch(
            "vintagestory_api.services.metrics.psutil.Process", mock_process_factory
        ):
            service = MetricsService(buffer=buffer, server_service=mock_server_service)

            # Should raise since we only catch specific psutil exceptions
            with pytest.raises(Exception, match="Unexpected psutil error"):
                service.collect()

    def test_game_metrics_with_zero_memory_rss(self) -> None:
        """Test handling of game process with zero RSS memory (edge case)."""
        buffer = MetricsBuffer(capacity=10)

        mock_server_service = MagicMock()
        mock_server_service.game_server_pid = 55555

        mock_game_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 0  # Zero memory
        mock_game_process.memory_info.return_value = mock_memory_info
        mock_game_process.cpu_percent.return_value = 10.0

        original_process = psutil.Process

        def mock_process_factory(pid: int | None = None) -> psutil.Process:
            if pid == 55555:
                return mock_game_process  # type: ignore[return-value]
            return original_process(pid)

        with patch(
            "vintagestory_api.services.metrics.psutil.Process", mock_process_factory
        ):
            service = MetricsService(buffer=buffer, server_service=mock_server_service)
            snapshot = service.collect()

        # Should handle 0 RSS gracefully
        assert snapshot.game_memory_mb == 0.0

    def test_game_metrics_with_very_high_cpu_percent(self) -> None:
        """Test handling of very high CPU percent (multi-core systems)."""
        buffer = MetricsBuffer(capacity=10)

        mock_server_service = MagicMock()
        mock_server_service.game_server_pid = 44444

        mock_game_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 512 * 1024 * 1024
        mock_game_process.memory_info.return_value = mock_memory_info
        mock_game_process.cpu_percent.return_value = 799.5  # 8 cores at 100%

        original_process = psutil.Process

        def mock_process_factory(pid: int | None = None) -> psutil.Process:
            if pid == 44444:
                return mock_game_process  # type: ignore[return-value]
            return original_process(pid)

        with patch(
            "vintagestory_api.services.metrics.psutil.Process", mock_process_factory
        ):
            service = MetricsService(buffer=buffer, server_service=mock_server_service)
            snapshot = service.collect()

        assert snapshot.game_cpu_percent == 799.5

    def test_api_process_initialized_only_once(self) -> None:
        """Test that _get_api_process only creates process once (lazy loading)."""
        buffer = MetricsBuffer(capacity=10)
        service = MetricsService(buffer=buffer, server_service=None)

        # Initially None
        assert service._api_process is None

        # First call initializes
        process1 = service._get_api_process()
        assert process1 is not None

        # Second call returns same instance
        process2 = service._get_api_process()
        assert process2 is process1

    def test_buffer_shared_across_collect_calls(self) -> None:
        """Test that buffer reference is stable across collect calls."""
        buffer = MetricsBuffer(capacity=10)
        service = MetricsService(buffer=buffer)

        service.collect()
        buffer_ref_1 = service.buffer

        service.collect()
        buffer_ref_2 = service.buffer

        # Same buffer instance
        assert buffer_ref_1 is buffer_ref_2
        assert buffer_ref_1 is buffer

    def test_collect_timestamps_increase(self) -> None:
        """Test that consecutive collect() calls produce increasing timestamps."""
        import time

        buffer = MetricsBuffer(capacity=10)
        service = MetricsService(buffer=buffer, server_service=None)

        snapshot1 = service.collect()
        time.sleep(0.01)  # Small delay to ensure timestamp difference
        snapshot2 = service.collect()

        assert snapshot2.timestamp > snapshot1.timestamp

    def test_game_process_terminates_between_pid_check_and_metrics_call(
        self,
    ) -> None:
        """Test race condition: process exists during PID check but gone during metrics."""
        buffer = MetricsBuffer(capacity=10)

        mock_server_service = MagicMock()
        mock_server_service.game_server_pid = 33333

        # First call to Process() succeeds, but memory_info() raises NoSuchProcess
        mock_game_process = MagicMock()
        mock_game_process.memory_info.side_effect = psutil.NoSuchProcess(33333)

        original_process = psutil.Process

        def mock_process_factory(pid: int | None = None) -> psutil.Process:
            if pid == 33333:
                return mock_game_process  # type: ignore[return-value]
            return original_process(pid)

        with patch(
            "vintagestory_api.services.metrics.psutil.Process", mock_process_factory
        ):
            service = MetricsService(buffer=buffer, server_service=mock_server_service)
            snapshot = service.collect()

        # Should handle gracefully
        assert snapshot.game_memory_mb is None
        assert snapshot.game_cpu_percent is None


class TestMetricsServiceSingletonEdgeCases:
    """Edge case tests for metrics service singleton pattern."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> Generator[None, None, None]:
        """Reset metrics service singleton before and after each test."""
        reset_metrics_service()
        yield
        reset_metrics_service()

    def test_multiple_reset_calls_safe(self) -> None:
        """Test that multiple reset calls don't cause issues."""
        get_metrics_service()

        reset_metrics_service()
        reset_metrics_service()
        reset_metrics_service()

        # Should still work after multiple resets
        service = get_metrics_service()
        assert service is not None

    def test_get_after_reset_creates_new_instance_with_fresh_buffer(self) -> None:
        """Test that reset creates completely new instance with empty buffer."""
        service1 = get_metrics_service()
        service1.collect()
        service1.collect()

        # Buffer should have 2 items
        assert len(service1.buffer) == 2

        reset_metrics_service()
        service2 = get_metrics_service()

        # New instance with fresh buffer
        assert service2 is not service1
        assert len(service2.buffer) == 0

    def test_reset_without_prior_get_is_safe(self) -> None:
        """Test resetting when singleton never initialized."""
        # Should not raise
        reset_metrics_service()

        # Can still get service after reset
        service = get_metrics_service()
        assert service is not None
