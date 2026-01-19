"""Unit tests for ConsoleBuffer service."""

import pytest

from vintagestory_api.services.console import ConsoleBuffer

# pyright: reportPrivateUsage=false
# Note: Tests need access to private members to verify internal state


class TestConsoleBuffer:
    """Unit tests for ConsoleBuffer."""

    @pytest.fixture
    def buffer(self) -> ConsoleBuffer:
        """Create a console buffer for testing."""
        return ConsoleBuffer(max_lines=100)

    @pytest.fixture
    def small_buffer(self) -> ConsoleBuffer:
        """Create a small buffer for testing FIFO behavior."""
        return ConsoleBuffer(max_lines=5)

    # ======================================
    # Basic buffer operations (AC1, AC4)
    # ======================================

    @pytest.mark.asyncio
    async def test_append_adds_line_to_buffer(self, buffer: ConsoleBuffer) -> None:
        """Test that append adds a line to the buffer."""
        await buffer.append("Test line")

        assert len(buffer) == 1
        history = buffer.get_history()
        assert len(history) == 1
        assert history[0] == "Test line"

    @pytest.mark.asyncio
    async def test_append_stores_line_without_modification(self, buffer: ConsoleBuffer) -> None:
        """Test that append stores lines without modification.

        VintageStory server output already includes timestamps, so we don't
        add our own. Lines are stored exactly as received.
        """
        # Simulate VintageStory server output with its own timestamp
        server_line = "[12:34:56] Server starting"
        await buffer.append(server_line)

        history = buffer.get_history()
        assert len(history) == 1
        assert history[0] == server_line  # Exact match, no modification

    @pytest.mark.asyncio
    async def test_append_multiple_lines_preserves_order(self, buffer: ConsoleBuffer) -> None:
        """Test that multiple lines are stored in order."""
        await buffer.append("Line 1")
        await buffer.append("Line 2")
        await buffer.append("Line 3")

        history = buffer.get_history()
        assert len(history) == 3
        assert "Line 1" in history[0]
        assert "Line 2" in history[1]
        assert "Line 3" in history[2]

    # ======================================
    # FIFO behavior (AC2)
    # ======================================

    @pytest.mark.asyncio
    async def test_fifo_discards_oldest_when_full(self, small_buffer: ConsoleBuffer) -> None:
        """Test that oldest lines are discarded when buffer is full (AC2)."""
        # Fill the buffer (max_lines=5)
        for i in range(5):
            await small_buffer.append(f"Line {i}")

        assert len(small_buffer) == 5
        history = small_buffer.get_history()
        assert "Line 0" in history[0]
        assert "Line 4" in history[4]

        # Add one more line - should discard Line 0
        await small_buffer.append("Line 5")

        assert len(small_buffer) == 5
        history = small_buffer.get_history()
        assert "Line 0" not in str(history)  # Line 0 should be gone
        assert "Line 1" in history[0]  # Line 1 is now oldest
        assert "Line 5" in history[4]  # Line 5 is newest

    @pytest.mark.asyncio
    async def test_fifo_capacity_not_exceeded(self, small_buffer: ConsoleBuffer) -> None:
        """Test that buffer never exceeds max_lines capacity (AC2)."""
        # Add many more lines than capacity
        for i in range(100):
            await small_buffer.append(f"Line {i}")

        # Buffer should still be at max capacity
        assert len(small_buffer) == 5

        # Only the last 5 lines should remain
        history = small_buffer.get_history()
        assert "Line 95" in history[0]
        assert "Line 96" in history[1]
        assert "Line 97" in history[2]
        assert "Line 98" in history[3]
        assert "Line 99" in history[4]

    # ======================================
    # get_history() with limit
    # ======================================

    @pytest.mark.asyncio
    async def test_get_history_returns_all_without_limit(self, buffer: ConsoleBuffer) -> None:
        """Test that get_history returns all lines when no limit specified."""
        for i in range(10):
            await buffer.append(f"Line {i}")

        history = buffer.get_history()
        assert len(history) == 10

    @pytest.mark.asyncio
    async def test_get_history_with_limit_returns_newest(self, buffer: ConsoleBuffer) -> None:
        """Test that get_history with limit returns newest lines."""
        for i in range(10):
            await buffer.append(f"Line {i}")

        history = buffer.get_history(limit=3)
        assert len(history) == 3
        assert "Line 7" in history[0]
        assert "Line 8" in history[1]
        assert "Line 9" in history[2]

    @pytest.mark.asyncio
    async def test_get_history_limit_greater_than_buffer(self, buffer: ConsoleBuffer) -> None:
        """Test that limit greater than buffer size returns all lines."""
        await buffer.append("Line 1")
        await buffer.append("Line 2")

        history = buffer.get_history(limit=100)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_history_empty_buffer(self, buffer: ConsoleBuffer) -> None:
        """Test that get_history on empty buffer returns empty list."""
        history = buffer.get_history()
        assert history == []

        history_limited = buffer.get_history(limit=10)
        assert history_limited == []

    # ======================================
    # Subscriber pattern
    # ======================================

    @pytest.mark.asyncio
    async def test_subscribe_receives_new_lines(self, buffer: ConsoleBuffer) -> None:
        """Test that subscribers receive new lines."""
        received_lines: list[str] = []

        async def callback(line: str) -> None:
            received_lines.append(line)

        buffer.subscribe(callback)
        await buffer.append("Test message")

        assert len(received_lines) == 1
        assert received_lines[0] == "Test message"

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_notified(self, buffer: ConsoleBuffer) -> None:
        """Test that all subscribers are notified."""
        received_1: list[str] = []
        received_2: list[str] = []

        async def callback_1(line: str) -> None:
            received_1.append(line)

        async def callback_2(line: str) -> None:
            received_2.append(line)

        buffer.subscribe(callback_1)
        buffer.subscribe(callback_2)
        await buffer.append("Broadcast message")

        assert len(received_1) == 1
        assert len(received_2) == 1
        assert received_1[0] == "Broadcast message"
        assert received_2[0] == "Broadcast message"

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_notifications(self, buffer: ConsoleBuffer) -> None:
        """Test that unsubscribed callbacks no longer receive lines."""
        received_lines: list[str] = []

        async def callback(line: str) -> None:
            received_lines.append(line)

        buffer.subscribe(callback)
        await buffer.append("Before unsubscribe")

        buffer.unsubscribe(callback)
        await buffer.append("After unsubscribe")

        assert len(received_lines) == 1
        assert received_lines[0] == "Before unsubscribe"

    @pytest.mark.asyncio
    async def test_failed_subscriber_is_removed(self, buffer: ConsoleBuffer) -> None:
        """Test that subscribers that raise exceptions are removed."""
        call_count = 0

        async def failing_callback(line: str) -> None:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("WebSocket disconnected")

        buffer.subscribe(failing_callback)
        await buffer.append("Line 1")  # Should call and remove
        await buffer.append("Line 2")  # Should not call (already removed)

        assert call_count == 1  # Only called once, then removed

    @pytest.mark.asyncio
    async def test_subscriber_failure_does_not_affect_others(self, buffer: ConsoleBuffer) -> None:
        """Test that one subscriber's failure doesn't affect other subscribers."""
        received_good: list[str] = []

        async def good_callback(line: str) -> None:
            received_good.append(line)

        async def bad_callback(line: str) -> None:
            raise RuntimeError("I'm broken")

        buffer.subscribe(bad_callback)
        buffer.subscribe(good_callback)
        await buffer.append("Test message")

        # Good subscriber should still receive the message
        assert len(received_good) == 1
        assert received_good[0] == "Test message"

    # ======================================
    # Buffer properties and clear
    # ======================================

    def test_max_lines_property(self) -> None:
        """Test that max_lines property returns configured value."""
        buffer = ConsoleBuffer(max_lines=500)
        assert buffer.max_lines == 500

    def test_default_max_lines(self) -> None:
        """Test that default max_lines is 10,000."""
        buffer = ConsoleBuffer()
        assert buffer.max_lines == 10000

    @pytest.mark.asyncio
    async def test_clear_empties_buffer(self, buffer: ConsoleBuffer) -> None:
        """Test that clear removes all buffered lines."""
        await buffer.append("Line 1")
        await buffer.append("Line 2")
        assert len(buffer) == 2

        buffer.clear()

        assert len(buffer) == 0
        assert buffer.get_history() == []

    @pytest.mark.asyncio
    async def test_clear_does_not_affect_subscribers(self, buffer: ConsoleBuffer) -> None:
        """Test that clear preserves subscribers."""
        received_lines: list[str] = []

        async def callback(line: str) -> None:
            received_lines.append(line)

        buffer.subscribe(callback)
        await buffer.append("Before clear")
        buffer.clear()
        await buffer.append("After clear")

        assert len(received_lines) == 2
        assert received_lines[0] == "Before clear"
        assert received_lines[1] == "After clear"

    # ======================================
    # Buffer preservation after server stop (AC4)
    # ======================================

    @pytest.mark.asyncio
    async def test_buffer_preserves_content(self, buffer: ConsoleBuffer) -> None:
        """Test that buffer content is preserved (AC4 - for troubleshooting)."""
        # Simulate server output before crash
        await buffer.append("Server starting...")
        await buffer.append("Loading world...")
        await buffer.append("FATAL ERROR: Something went wrong")

        # Buffer should still contain all content
        history = buffer.get_history()
        assert len(history) == 3
        assert "Server starting" in history[0]
        assert "Loading world" in history[1]
        assert "FATAL ERROR" in history[2]

    # ======================================
    # In-memory only behavior (AC3)
    # ======================================

    def test_new_buffer_is_empty(self) -> None:
        """Test that a new buffer starts empty (AC3 - in-memory only)."""
        buffer = ConsoleBuffer()
        assert len(buffer) == 0
        assert buffer.get_history() == []

    # ======================================
    # Memory behavior under stress
    # ======================================

    @pytest.mark.asyncio
    async def test_stress_large_number_of_lines(self, buffer: ConsoleBuffer) -> None:
        """Test that buffer handles large number of lines without memory issues."""
        # Add 10,000 lines (typical max_lines default)
        for i in range(10000):
            await buffer.append(f"[{i:05d}] Server output line")

        # Buffer should be at capacity
        assert len(buffer) == 100

        # Get history should work efficiently
        history = buffer.get_history()
        assert len(history) == 100

    @pytest.mark.asyncio
    async def test_stress_large_line_content(self, buffer: ConsoleBuffer) -> None:
        """Test that buffer handles lines with large content."""
        # Create a very long line (simulating crash dump or stack trace)
        large_line = "A" * 10000

        await buffer.append(large_line)

        history = buffer.get_history()
        assert len(history) == 1
        assert len(history[0]) == 10000

    @pytest.mark.asyncio
    async def test_stress_mixed_line_sizes(self, small_buffer: ConsoleBuffer) -> None:
        """Test that buffer handles mixed line sizes correctly."""
        # Add lines of varying sizes
        await small_buffer.append("Short")
        await small_buffer.append("Medium sized line")
        await small_buffer.append("X" * 1000)
        await small_buffer.append("Another medium line")
        await small_buffer.append("Y" * 500)

        # Add one more to trigger FIFO
        await small_buffer.append("Z" * 200)

        # Verify buffer still respects max_lines
        assert len(small_buffer) == 5
        history = small_buffer.get_history()

        # First line (short) should be gone
        assert history[0] != "Short"
        # Newest line should be last
        assert history[4] == "Z" * 200

    @pytest.mark.asyncio
    async def test_stress_rapid_append_operations(self, buffer: ConsoleBuffer) -> None:
        """Test that rapid append operations work correctly."""
        # Simulate rapid server output
        for i in range(1000):
            await buffer.append(f"Line {i}")

        # All lines should be stored (buffer capacity is 100)
        assert len(buffer) == 100
        history = buffer.get_history()
        assert len(history) == 100

    # ======================================
    # Concurrent operations
    # ======================================

    @pytest.mark.asyncio
    async def test_subscribe_during_append(self, buffer: ConsoleBuffer) -> None:
        """Test that subscribing during append operations is safe."""
        received_early: list[str] = []
        received_late: list[str] = []

        async def early_callback(line: str) -> None:
            received_early.append(line)

        async def late_callback(line: str) -> None:
            received_late.append(line)

        # Subscribe first callback
        buffer.subscribe(early_callback)
        await buffer.append("Line 1")

        # Subscribe second callback mid-stream
        buffer.subscribe(late_callback)
        await buffer.append("Line 2")

        # Both should have received Line 2
        assert len(received_early) == 2
        assert len(received_late) == 1
        assert received_late[0] == "Line 2"

    @pytest.mark.asyncio
    async def test_unsubscribe_during_append(self, buffer: ConsoleBuffer) -> None:
        """Test that unsubscribing during append operations is safe."""
        received_lines: list[str] = []

        async def callback(line: str) -> None:
            received_lines.append(line)

        buffer.subscribe(callback)
        await buffer.append("Line 1")

        # Unsubscribe mid-stream
        buffer.unsubscribe(callback)
        await buffer.append("Line 2")

        # Should only have Line 1
        assert len(received_lines) == 1
        assert received_lines[0] == "Line 1"

    @pytest.mark.asyncio
    async def test_multiple_subscribe_unsubscribe_cycles(self, buffer: ConsoleBuffer) -> None:
        """Test that multiple subscribe/unsubscribe cycles work correctly."""
        received_lines: list[str] = []

        async def callback(line: str) -> None:
            received_lines.append(line)

        # Subscribe, append, unsubscribe
        buffer.subscribe(callback)
        await buffer.append("Line 1")
        buffer.unsubscribe(callback)

        # Subscribe again
        buffer.subscribe(callback)
        await buffer.append("Line 2")
        buffer.unsubscribe(callback)

        # Subscribe once more
        buffer.subscribe(callback)
        await buffer.append("Line 3")

        # Should have received lines from each subscription
        assert len(received_lines) == 3
        assert received_lines == ["Line 1", "Line 2", "Line 3"]

    @pytest.mark.asyncio
    async def test_subscribe_all_failing_subscribers_removed(self, buffer: ConsoleBuffer) -> None:
        """Test that when all subscribers fail, buffer continues to work."""

        async def failing_callback_1(line: str) -> None:
            raise RuntimeError("Error 1")

        async def failing_callback_2(line: str) -> None:
            raise RuntimeError("Error 2")

        buffer.subscribe(failing_callback_1)
        buffer.subscribe(failing_callback_2)

        # Should not raise, both subscribers should be removed
        await buffer.append("Line 1")

        # Subscribers should be removed
        assert len(buffer._subscribers) == 0  # type: ignore

        # Buffer should continue working
        received_lines: list[str] = []

        async def good_callback(line: str) -> None:
            received_lines.append(line)

        buffer.subscribe(good_callback)
        await buffer.append("Line 2")

        assert len(received_lines) == 1

    # ======================================
    # Additional edge cases
    # ======================================

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_callback(self, buffer: ConsoleBuffer) -> None:
        """Test that unsubscribing a non-existent callback is safe."""

        async def callback(line: str) -> None:
            pass

        # Should not raise
        buffer.unsubscribe(callback)

        # Even after subscribing and unsubscribing
        buffer.subscribe(callback)
        buffer.unsubscribe(callback)

        # Unsubscribing again should be safe
        buffer.unsubscribe(callback)

    @pytest.mark.asyncio
    async def test_get_history_limit_zero(self, buffer: ConsoleBuffer) -> None:
        """Test that get_history with limit=0 returns all lines (Python slicing behavior)."""
        await buffer.append("Line 1")
        await buffer.append("Line 2")

        history = buffer.get_history(limit=0)
        # In Python, list[-0:] returns the entire list, not empty
        assert history == ["Line 1", "Line 2"]

    @pytest.mark.asyncio
    async def test_get_history_negative_limit(self, buffer: ConsoleBuffer) -> None:
        """Test that get_history with negative limit returns empty list."""
        await buffer.append("Line 1")

        history = buffer.get_history(limit=-1)
        assert history == []

    @pytest.mark.asyncio
    async def test_append_empty_string(self, buffer: ConsoleBuffer) -> None:
        """Test that appending empty string is allowed."""
        await buffer.append("")
        await buffer.append("Line 1")

        history = buffer.get_history()
        assert len(history) == 2
        assert history[0] == ""
        assert history[1] == "Line 1"

    @pytest.mark.asyncio
    async def test_append_unicode_content(self, buffer: ConsoleBuffer) -> None:
        """Test that buffer handles unicode content correctly."""
        unicode_lines = [
            "Hello 世界",
            "Привет мир",
            "مرحبا",
            "🎮 Gaming",
            "Special chars: ©®™",
        ]

        for line in unicode_lines:
            await buffer.append(line)

        history = buffer.get_history()
        assert len(history) == 5
        assert "🎮 Gaming" in history[3]

    @pytest.mark.asyncio
    async def test_clear_on_empty_buffer(self, buffer: ConsoleBuffer) -> None:
        """Test that clearing an empty buffer is safe."""
        assert len(buffer) == 0

        # Should not raise
        buffer.clear()

        assert len(buffer) == 0
        assert buffer.get_history() == []

    @pytest.mark.asyncio
    async def test_len_property_accuracy(self, buffer: ConsoleBuffer) -> None:
        """Test that __len__ property accurately reflects buffer size."""
        assert len(buffer) == 0

        await buffer.append("Line 1")
        assert len(buffer) == 1

        await buffer.append("Line 2")
        assert len(buffer) == 2

        buffer.clear()
        assert len(buffer) == 0
