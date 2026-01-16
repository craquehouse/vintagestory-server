"""Metrics collection service for server resource monitoring."""

from __future__ import annotations

from collections import deque

import structlog

from vintagestory_api.models.metrics import MetricsSnapshot

logger = structlog.get_logger()


class MetricsBuffer:
    """Ring buffer for metrics snapshots.

    Stores metrics samples in a FIFO ring buffer. When the buffer
    reaches capacity, the oldest samples are automatically evicted.

    Thread-safe for single writer (APScheduler job) + multiple readers (API).
    Uses collections.deque which is thread-safe for append/read operations.

    Attributes:
        DEFAULT_CAPACITY: Default buffer size (360 = 1 hour at 10s intervals).
    """

    DEFAULT_CAPACITY = 360  # 1 hour at 10s intervals

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        """Initialize the metrics buffer.

        Args:
            capacity: Maximum number of samples to store before oldest are evicted.
        """
        self._buffer: deque[MetricsSnapshot] = deque(maxlen=capacity)
        self._capacity = capacity
        logger.debug("metrics_buffer_initialized", capacity=capacity)

    @property
    def capacity(self) -> int:
        """Get the maximum buffer capacity."""
        return self._capacity

    def append(self, snapshot: MetricsSnapshot) -> None:
        """Add a metrics snapshot to the buffer.

        If the buffer is at capacity, the oldest snapshot is evicted (FIFO).

        Args:
            snapshot: The metrics snapshot to add.
        """
        self._buffer.append(snapshot)
        logger.debug(
            "metrics_appended",
            buffer_size=len(self._buffer),
            timestamp=snapshot.timestamp.isoformat(),
        )

    def get_all(self) -> list[MetricsSnapshot]:
        """Get all buffered snapshots.

        Returns:
            List of metrics snapshots, oldest first.
        """
        return list(self._buffer)

    def get_latest(self) -> MetricsSnapshot | None:
        """Get the most recent snapshot.

        Returns:
            The latest snapshot, or None if buffer is empty.
        """
        if not self._buffer:
            return None
        return self._buffer[-1]

    def clear(self) -> None:
        """Clear all buffered snapshots."""
        self._buffer.clear()
        logger.debug("metrics_buffer_cleared")

    def __len__(self) -> int:
        """Get current number of snapshots in buffer."""
        return len(self._buffer)
