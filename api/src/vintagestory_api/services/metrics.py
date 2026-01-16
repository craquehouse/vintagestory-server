"""Metrics collection service for server resource monitoring."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import psutil
import structlog

from vintagestory_api.models.metrics import MetricsSnapshot

if TYPE_CHECKING:
    from vintagestory_api.services.server import ServerService

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


class MetricsService:
    """Service for collecting and storing server metrics.

    Collects metrics from both the API server process and the game server
    process (when running). Uses psutil for process-level resource metrics.

    The API process handle is lazily initialized on first collect() call
    to defer overhead until actually needed. CPU percent tracking baseline
    is also initialized at that time (first call returns 0.0).
    """

    def __init__(
        self,
        buffer: MetricsBuffer | None = None,
        server_service: ServerService | None = None,
    ) -> None:
        """Initialize the metrics service.

        Args:
            buffer: Optional metrics buffer. If None, creates one with default capacity.
            server_service: Optional server service for game server PID discovery.
                If None, will be resolved lazily via get_server_service().
        """
        self._buffer = buffer if buffer is not None else MetricsBuffer()
        self._server_service = server_service
        # Lazy-loaded on first collect() call
        self._api_process: psutil.Process | None = None
        logger.info("metrics_service_initialized", buffer_capacity=self._buffer.capacity)

    @property
    def buffer(self) -> MetricsBuffer:
        """Get the metrics buffer."""
        return self._buffer

    def collect(self) -> MetricsSnapshot:
        """Collect current metrics and store in buffer.

        Collects API server metrics (always available) and game server
        metrics (when game server is running). If game server is not
        running or metrics collection fails, game metrics are set to None.

        Returns:
            The collected metrics snapshot.
        """
        timestamp = datetime.now(UTC)

        # Collect API server metrics (AC: 1)
        api_memory_mb, api_cpu_percent = self._get_api_metrics()

        # Collect game server metrics (AC: 2, 3)
        game_memory_mb, game_cpu_percent = self._get_game_metrics()

        snapshot = MetricsSnapshot(
            timestamp=timestamp,
            api_memory_mb=api_memory_mb,
            api_cpu_percent=api_cpu_percent,
            game_memory_mb=game_memory_mb,
            game_cpu_percent=game_cpu_percent,
        )

        self._buffer.append(snapshot)

        logger.debug(
            "metrics_collected",
            api_memory_mb=round(api_memory_mb, 2),
            api_cpu_percent=round(api_cpu_percent, 2),
            game_memory_mb=round(game_memory_mb, 2) if game_memory_mb else None,
            game_cpu_percent=round(game_cpu_percent, 2) if game_cpu_percent else None,
        )

        return snapshot

    def _get_api_process(self) -> psutil.Process:
        """Get or create the API process handle.

        Lazy initialization defers psutil overhead until first use.
        CPU percent baseline is also initialized on first call.

        Returns:
            psutil.Process handle for the current API process.
        """
        if self._api_process is None:
            self._api_process = psutil.Process()
            # Initialize CPU percent baseline (first call returns 0.0)
            self._api_process.cpu_percent(interval=None)
            logger.debug("api_process_initialized", pid=self._api_process.pid)
        return self._api_process

    def _get_api_metrics(self) -> tuple[float, float]:
        """Get API server process metrics.

        Returns:
            Tuple of (memory_mb, cpu_percent).
        """
        api_process = self._get_api_process()
        memory_info = api_process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Resident Set Size in MB
        cpu_percent = api_process.cpu_percent(interval=None)  # Non-blocking
        return memory_mb, cpu_percent

    def _get_game_server_pid(self) -> int | None:
        """Get the game server process ID if running.

        Returns:
            Game server PID if running, None otherwise.
        """
        server_service = self._get_server_service()
        if server_service is None:
            return None

        # Check if process exists and is still running
        # _process is None when no subprocess has been spawned
        # _process.returncode is None while process is running
        # ADR-E12-002: Direct _process access is the documented pattern
        if (
            server_service._process is not None  # pyright: ignore[reportPrivateUsage]
            and server_service._process.returncode is None  # pyright: ignore[reportPrivateUsage]
        ):
            return server_service._process.pid  # pyright: ignore[reportPrivateUsage]

        return None

    def _get_game_metrics(self) -> tuple[float | None, float | None]:
        """Get game server process metrics.

        Gracefully handles cases where game server is not running
        or process metrics cannot be collected (AC: 3).

        Returns:
            Tuple of (memory_mb, cpu_percent), both None if server not running.
        """
        pid = self._get_game_server_pid()
        if pid is None:
            return None, None

        try:
            game_process = psutil.Process(pid)
            memory_info = game_process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            cpu_percent = game_process.cpu_percent(interval=None)
            return memory_mb, cpu_percent
        except psutil.NoSuchProcess:
            # Process terminated between PID check and metrics collection
            logger.debug("game_process_no_longer_exists", pid=pid)
            return None, None
        except psutil.AccessDenied:
            # Permission denied to access process metrics
            logger.warning("game_process_access_denied", pid=pid)
            return None, None

    def _get_server_service(self) -> ServerService | None:
        """Get the server service instance.

        Lazy resolution to avoid circular imports and allow
        dependency injection for testing.

        Returns:
            ServerService instance or None if not available.
        """
        if self._server_service is not None:
            return self._server_service

        # Lazy import to avoid circular dependency
        from vintagestory_api.services.server import get_server_service

        return get_server_service()


# Module-level singleton
_metrics_service: MetricsService | None = None


def get_metrics_service() -> MetricsService:
    """Get or create the metrics service singleton.

    Returns:
        MetricsService instance.
    """
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


def reset_metrics_service() -> None:
    """Reset the metrics service singleton.

    Used for testing to ensure clean state between tests.
    """
    global _metrics_service
    _metrics_service = None
