"""Console buffer service for capturing and storing game server output."""

from collections import deque
from collections.abc import Awaitable, Callable
from datetime import datetime

import structlog

logger = structlog.get_logger()

# Type alias for subscriber callbacks
ConsoleSubscriber = Callable[[str], Awaitable[None]]


class ConsoleBuffer:
    """Ring buffer for console output with subscriber support.

    Stores timestamped console output lines in a FIFO ring buffer.
    Supports async callbacks for real-time notification to subscribers
    (e.g., WebSocket connections).

    Attributes:
        max_lines: Maximum number of lines to store before oldest are discarded.
    """

    def __init__(self, max_lines: int = 10000) -> None:
        """Initialize the console buffer.

        Args:
            max_lines: Maximum number of lines to store (default 10,000).
        """
        self._buffer: deque[str] = deque(maxlen=max_lines)
        self._subscribers: set[ConsoleSubscriber] = set()
        self._max_lines = max_lines
        logger.info("console_buffer_initialized", max_lines=max_lines)

    @property
    def max_lines(self) -> int:
        """Get the maximum buffer capacity."""
        return self._max_lines

    async def append(self, line: str) -> None:
        """Add a line to the buffer with timestamp and notify subscribers.

        The line is prefixed with an ISO 8601 timestamp before storage.
        All registered subscribers are notified asynchronously.
        Failed subscribers are automatically removed.

        Args:
            line: The console output line to add.
        """
        timestamped = f"[{datetime.now().isoformat()}] {line}"
        self._buffer.append(timestamped)

        # Notify all subscribers
        # Use list() to avoid "set changed size during iteration" if callback fails
        for callback in list(self._subscribers):
            try:
                await callback(timestamped)
            except Exception as e:
                # Remove failed subscriber (e.g., disconnected WebSocket)
                self._subscribers.discard(callback)
                logger.debug(
                    "subscriber_removed_on_error",
                    error=str(e),
                    remaining_subscribers=len(self._subscribers),
                )

    def get_history(self, limit: int | None = None) -> list[str]:
        """Get buffered lines, optionally limited to last N lines.

        Args:
            limit: Optional maximum number of lines to return (newest lines).
                If None, returns all buffered lines.

        Returns:
            List of timestamped console lines, oldest first.
        """
        if limit is None:
            return list(self._buffer)
        return list(self._buffer)[-limit:]

    def subscribe(self, callback: ConsoleSubscriber) -> None:
        """Subscribe to new console lines.

        The callback will be invoked with each new timestamped line.
        Used by WebSocket connections for real-time streaming.

        Args:
            callback: Async function to call with each new line.
        """
        self._subscribers.add(callback)
        logger.debug(
            "subscriber_added",
            total_subscribers=len(self._subscribers),
        )

    def unsubscribe(self, callback: ConsoleSubscriber) -> None:
        """Unsubscribe from new console lines.

        Args:
            callback: The callback to remove.
        """
        self._subscribers.discard(callback)
        logger.debug(
            "subscriber_removed",
            total_subscribers=len(self._subscribers),
        )

    def clear(self) -> None:
        """Clear all buffered lines.

        Note: This does not affect subscribers.
        """
        self._buffer.clear()
        logger.info("console_buffer_cleared")

    def __len__(self) -> int:
        """Get current number of lines in buffer."""
        return len(self._buffer)
