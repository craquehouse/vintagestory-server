"""Tests for metrics models and services."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from vintagestory_api.models.metrics import MetricsSnapshot


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
