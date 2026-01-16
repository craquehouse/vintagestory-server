"""Tests for metrics models and services."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from vintagestory_api.models.metrics import MetricsSnapshot
from vintagestory_api.services.metrics import MetricsBuffer


class TestMetricsSnapshot:
    """Tests for MetricsSnapshot dataclass."""

    def test_create_with_all_fields(self) -> None:
        """Test creating snapshot with all fields populated."""
        timestamp = datetime.now()
        snapshot = MetricsSnapshot(
            timestamp=timestamp,
            api_memory_mb=100.5,
            api_cpu_percent=25.0,
            game_memory_mb=512.0,
            game_cpu_percent=45.0,
        )

        assert snapshot.timestamp == timestamp
        assert snapshot.api_memory_mb == 100.5
        assert snapshot.api_cpu_percent == 25.0
        assert snapshot.game_memory_mb == 512.0
        assert snapshot.game_cpu_percent == 45.0

    def test_nullable_game_fields_when_server_not_running(self) -> None:
        """Test that game fields can be None when server is not running."""
        timestamp = datetime.now()
        snapshot = MetricsSnapshot(
            timestamp=timestamp,
            api_memory_mb=100.5,
            api_cpu_percent=25.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )

        assert snapshot.api_memory_mb == 100.5
        assert snapshot.api_cpu_percent == 25.0
        assert snapshot.game_memory_mb is None
        assert snapshot.game_cpu_percent is None

    def test_frozen_dataclass_is_immutable(self) -> None:
        """Test that snapshot cannot be modified after creation (frozen=True)."""
        timestamp = datetime.now()
        snapshot = MetricsSnapshot(
            timestamp=timestamp,
            api_memory_mb=100.5,
            api_cpu_percent=25.0,
            game_memory_mb=512.0,
            game_cpu_percent=45.0,
        )

        with pytest.raises(FrozenInstanceError):
            snapshot.api_memory_mb = 200.0  # type: ignore[misc]

    def test_snapshot_equality(self) -> None:
        """Test that snapshots with same values are equal."""
        timestamp = datetime.now()
        snapshot1 = MetricsSnapshot(
            timestamp=timestamp,
            api_memory_mb=100.5,
            api_cpu_percent=25.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )
        snapshot2 = MetricsSnapshot(
            timestamp=timestamp,
            api_memory_mb=100.5,
            api_cpu_percent=25.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )

        assert snapshot1 == snapshot2

    def test_snapshot_is_hashable(self) -> None:
        """Test that frozen snapshot can be used in sets/dicts."""
        timestamp = datetime.now()
        snapshot = MetricsSnapshot(
            timestamp=timestamp,
            api_memory_mb=100.5,
            api_cpu_percent=25.0,
            game_memory_mb=None,
            game_cpu_percent=None,
        )

        # Should be hashable since it's frozen
        snapshot_set = {snapshot}
        assert snapshot in snapshot_set


def _create_snapshot(
    api_memory: float = 100.0,
    api_cpu: float = 10.0,
    game_memory: float | None = None,
    game_cpu: float | None = None,
) -> MetricsSnapshot:
    """Helper to create test snapshots."""
    return MetricsSnapshot(
        timestamp=datetime.now(),
        api_memory_mb=api_memory,
        api_cpu_percent=api_cpu,
        game_memory_mb=game_memory,
        game_cpu_percent=game_cpu,
    )


class TestMetricsBuffer:
    """Tests for MetricsBuffer ring buffer."""

    def test_append_and_get_all(self) -> None:
        """Test appending snapshots and retrieving all."""
        buffer = MetricsBuffer(capacity=10)
        snapshot1 = _create_snapshot(api_memory=100.0)
        snapshot2 = _create_snapshot(api_memory=200.0)

        buffer.append(snapshot1)
        buffer.append(snapshot2)

        all_snapshots = buffer.get_all()
        assert len(all_snapshots) == 2
        assert all_snapshots[0] == snapshot1
        assert all_snapshots[1] == snapshot2

    def test_get_latest(self) -> None:
        """Test getting the most recent snapshot."""
        buffer = MetricsBuffer(capacity=10)
        snapshot1 = _create_snapshot(api_memory=100.0)
        snapshot2 = _create_snapshot(api_memory=200.0)

        buffer.append(snapshot1)
        buffer.append(snapshot2)

        latest = buffer.get_latest()
        assert latest == snapshot2

    def test_get_latest_empty_buffer(self) -> None:
        """Test get_latest returns None for empty buffer."""
        buffer = MetricsBuffer(capacity=10)

        assert buffer.get_latest() is None

    def test_len(self) -> None:
        """Test __len__ returns correct count."""
        buffer = MetricsBuffer(capacity=10)

        assert len(buffer) == 0

        buffer.append(_create_snapshot())
        assert len(buffer) == 1

        buffer.append(_create_snapshot())
        assert len(buffer) == 2

    def test_fifo_eviction_at_capacity(self) -> None:
        """Test that oldest snapshots are evicted when buffer is full (AC: 4)."""
        # Small capacity for easy testing
        buffer = MetricsBuffer(capacity=3)

        # Add 3 snapshots to fill buffer
        snapshot1 = _create_snapshot(api_memory=100.0)
        snapshot2 = _create_snapshot(api_memory=200.0)
        snapshot3 = _create_snapshot(api_memory=300.0)

        buffer.append(snapshot1)
        buffer.append(snapshot2)
        buffer.append(snapshot3)

        assert len(buffer) == 3
        assert buffer.get_all()[0] == snapshot1  # oldest

        # Add 4th snapshot - should evict first
        snapshot4 = _create_snapshot(api_memory=400.0)
        buffer.append(snapshot4)

        assert len(buffer) == 3
        all_snapshots = buffer.get_all()
        assert snapshot1 not in all_snapshots  # evicted
        assert all_snapshots[0] == snapshot2  # new oldest
        assert all_snapshots[1] == snapshot3
        assert all_snapshots[2] == snapshot4  # newest

    def test_capacity_property(self) -> None:
        """Test that capacity property returns configured value."""
        buffer = MetricsBuffer(capacity=100)
        assert buffer.capacity == 100

    def test_default_capacity(self) -> None:
        """Test default capacity is 360 (1 hour at 10s intervals)."""
        buffer = MetricsBuffer()
        assert buffer.capacity == 360

    def test_clear(self) -> None:
        """Test clearing the buffer."""
        buffer = MetricsBuffer(capacity=10)
        buffer.append(_create_snapshot())
        buffer.append(_create_snapshot())

        assert len(buffer) == 2

        buffer.clear()

        assert len(buffer) == 0
        assert buffer.get_latest() is None
        assert buffer.get_all() == []
