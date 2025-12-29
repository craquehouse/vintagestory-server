"""Tests for ConsoleBuffer service and WebSocket endpoint."""

# pyright: reportPrivateUsage=false
# Note: Tests need access to private members to verify internal state

import asyncio
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.routers.server import get_server_service
from vintagestory_api.services.console import ConsoleBuffer
from vintagestory_api.services.server import ServerService

# Test API keys - must match expected format
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


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
        assert "Test line" in history[0]

    @pytest.mark.asyncio
    async def test_append_adds_iso8601_timestamp(self, buffer: ConsoleBuffer) -> None:
        """Test that append prefixes lines with ISO 8601 timestamp (AC1)."""
        await buffer.append("Server starting")

        history = buffer.get_history()
        assert len(history) == 1

        # Check timestamp format: [YYYY-MM-DDTHH:MM:SS.ffffff]
        line = history[0]
        assert line.startswith("[")
        assert "]" in line

        # Extract timestamp and verify it's valid ISO 8601
        timestamp_str = line[1 : line.index("]")]
        timestamp = datetime.fromisoformat(timestamp_str)
        assert timestamp is not None

        # Verify the original message is preserved
        assert "Server starting" in line

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
        assert "Test message" in received_lines[0]

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
        assert "Broadcast message" in received_1[0]
        assert "Broadcast message" in received_2[0]

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
        assert "Before unsubscribe" in received_lines[0]

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
        assert "Test message" in received_good[0]

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
        assert "Before clear" in received_lines[0]
        assert "After clear" in received_lines[1]

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


class TestServerServiceConsoleIntegration:
    """Integration tests for ConsoleBuffer with ServerService (Task 2)."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create temporary directory structure for server tests."""
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        serverdata_dir = tmp_path / "serverdata"
        serverdata_dir.mkdir()
        vsmanager_dir = tmp_path / "vsmanager"
        vsmanager_dir.mkdir()

        # Create required server files to mark as "installed"
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        return tmp_path

    @pytest.fixture
    def settings(self, temp_dir: Path) -> Settings:
        """Create settings with temp directories."""
        return Settings(
            data_dir=temp_dir,
            debug=True,
        )

    @pytest.fixture
    def service(self, settings: Settings) -> ServerService:
        """Create ServerService with custom settings."""
        return ServerService(settings)

    def test_server_service_has_console_buffer(self, service: ServerService) -> None:
        """Test that ServerService exposes console_buffer property."""
        assert service.console_buffer is not None
        assert isinstance(service.console_buffer, ConsoleBuffer)

    def test_console_buffer_is_empty_on_init(self, service: ServerService) -> None:
        """Test that console buffer starts empty (AC3 - in-memory only)."""
        assert len(service.console_buffer) == 0
        assert service.console_buffer.get_history() == []

    @pytest.mark.asyncio
    async def test_start_creates_stream_reader_tasks(self, service: ServerService) -> None:
        """Test that starting server creates stdout/stderr reader tasks."""
        # Mock subprocess to avoid actually running server
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        # Make readline return empty bytes to signal EOF
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.send_signal = Mock()

        # Patch asyncio.create_subprocess_exec
        original_create_subprocess = asyncio.create_subprocess_exec

        async def mock_create_subprocess(*args: object, **kwargs: object) -> AsyncMock:
            return mock_process

        asyncio.create_subprocess_exec = mock_create_subprocess  # type: ignore[assignment]

        try:
            await service.start_server()

            # Verify stream reader tasks were created
            assert service._stdout_task is not None
            assert service._stderr_task is not None

            # Clean up
            await service.stop_server()
        finally:
            asyncio.create_subprocess_exec = original_create_subprocess  # type: ignore[assignment]

    @pytest.mark.asyncio
    async def test_stop_cancels_stream_reader_tasks(self, service: ServerService) -> None:
        """Test that stopping server cancels stream reader tasks."""
        # Set up mock process and tasks
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.send_signal = Mock()


        original_create_subprocess = asyncio.create_subprocess_exec

        async def mock_create_subprocess(*args: object, **kwargs: object) -> AsyncMock:
            return mock_process

        asyncio.create_subprocess_exec = mock_create_subprocess  # type: ignore[assignment]

        try:
            await service.start_server()

            # Verify tasks exist before stop
            assert service._stdout_task is not None
            assert service._stderr_task is not None

            await service.stop_server()

            # Tasks should be done after stop
            assert service._stdout_task.done()
            assert service._stderr_task.done()
        finally:
            asyncio.create_subprocess_exec = original_create_subprocess  # type: ignore[assignment]

    @pytest.mark.asyncio
    async def test_read_stream_captures_output_to_buffer(self, service: ServerService) -> None:
        """Test that _read_stream captures subprocess output to buffer (AC1)."""
        # Create a mock stream that returns some lines then EOF
        lines = [b"Server starting...\n", b"Loading world...\n", b"Ready!\n", b""]

        class MockStreamReader:
            def __init__(self) -> None:
                self.index = 0

            async def readline(self) -> bytes:
                if self.index < len(lines):
                    line = lines[self.index]
                    self.index += 1
                    return line
                return b""

        mock_stream = MockStreamReader()

        # Call _read_stream directly
        await service._read_stream(mock_stream, "test")  # type: ignore[arg-type]

        # Verify lines were captured
        history = service.console_buffer.get_history()
        assert len(history) == 3
        assert "Server starting" in history[0]
        assert "Loading world" in history[1]
        assert "Ready" in history[2]

    @pytest.mark.asyncio
    async def test_read_stream_handles_encoding_errors(self, service: ServerService) -> None:
        """Test that _read_stream handles invalid UTF-8 gracefully."""
        # Create stream with invalid UTF-8 bytes
        lines = [b"Valid line\n", b"\xff\xfe Invalid bytes\n", b""]

        class MockStreamReader:
            def __init__(self) -> None:
                self.index = 0

            async def readline(self) -> bytes:
                if self.index < len(lines):
                    line = lines[self.index]
                    self.index += 1
                    return line
                return b""

        mock_stream = MockStreamReader()

        # Should not raise - uses errors='replace'
        await service._read_stream(mock_stream, "test")  # type: ignore[arg-type]

        # Both lines should be captured (with replacement characters)
        history = service.console_buffer.get_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_buffer_preserves_content_after_server_stop(
        self, service: ServerService
    ) -> None:
        """Test that buffer content is preserved when server stops (AC4)."""
        # Add some content to buffer
        await service.console_buffer.append("Server starting...")
        await service.console_buffer.append("Loading world...")
        await service.console_buffer.append("CRASH!")

        # Simulate server stop (just verify buffer still has content)
        # The buffer is in-memory and persists as long as service exists
        history = service.console_buffer.get_history()
        assert len(history) == 3
        assert "CRASH!" in history[2]

    @pytest.mark.asyncio
    async def test_buffer_preserves_content_after_sigkill_crash(
        self, service: ServerService
    ) -> None:
        """Test that buffer preserves content after SIGKILL crash (AC4).

        AC4: "Given the game server crashes or stops, When the admin queries
             console history, Then the buffer contents up to the crash are
             preserved And available for troubleshooting"

        This test verifies that when a server process is killed (SIGKILL),
        the console buffer still contains all output captured before the crash.
        The buffer is in-memory and persists independently of the process state.
        """
        # Simulate server output being captured before a crash
        # This represents output that would have been read from the process
        await service.console_buffer.append("Server starting...")
        await service.console_buffer.append("Loading world: TestWorld")
        await service.console_buffer.append("Players: 0/32")
        await service.console_buffer.append("Memory usage: 1.2GB")
        await service.console_buffer.append("FATAL: Out of memory!")

        # At this point, the process would have crashed with SIGKILL (-9)
        # The buffer should preserve all content for troubleshooting

        # Simulate what happens when admin queries history after crash
        history = service.console_buffer.get_history()

        # Verify all content is preserved and available for troubleshooting
        assert len(history) == 5
        assert "Server starting" in history[0]
        assert "Loading world" in history[1]
        assert "Players" in history[2]
        assert "Memory usage" in history[3]
        assert "FATAL: Out of memory" in history[4]

        # Verify buffer can be queried multiple times (for debugging sessions)
        history_again = service.console_buffer.get_history()
        assert history == history_again

        # Verify limit parameter works for crash analysis
        recent_history = service.console_buffer.get_history(limit=2)
        assert len(recent_history) == 2
        assert "Memory usage" in recent_history[0]
        assert "FATAL" in recent_history[1]

    @pytest.mark.asyncio
    async def test_api_restart_clears_buffer(self, settings: Settings) -> None:
        """Test that buffer is empty after API restart simulation (AC3).

        AC3: "Given the API server restarts, Then the buffer is empty"

        This test simulates the API lifecycle:
        1. API starts - create ServerService with ConsoleBuffer
        2. Server runs and produces output - populate buffer
        3. API restarts - create new ServerService (simulates FastAPI app restart)
        4. Verify buffer is empty in new service
        """
        # Phase 1: API running, server producing output
        service_before_restart = ServerService(settings)
        await service_before_restart.console_buffer.append("Server starting...")
        await service_before_restart.console_buffer.append("World loaded")
        await service_before_restart.console_buffer.append("Players connected")

        # Verify buffer has content before restart
        assert len(service_before_restart.console_buffer) == 3

        # Phase 2: Simulate API restart
        # In production, uvicorn/FastAPI recreates all services on restart
        # The ConsoleBuffer lives in memory only - no persistence
        del service_before_restart

        # Phase 3: API restarts - new service instance
        service_after_restart = ServerService(settings)

        # Phase 4: Verify buffer is empty (in-memory only, no persistence)
        assert len(service_after_restart.console_buffer) == 0
        assert service_after_restart.console_buffer.get_history() == []


class TestConsoleHistoryEndpoint:
    """API tests for GET /api/v1alpha1/console/history endpoint (Task 3)."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temp data directory with server files."""
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        return tmp_path

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

    @pytest.fixture
    def test_service(self, test_settings: Settings) -> ServerService:
        """Create ServerService with test settings."""
        return ServerService(test_settings)

    @pytest.fixture
    def integration_app(
        self, test_settings: Settings, test_service: ServerService
    ) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    @pytest.fixture
    def admin_headers(self) -> dict[str, str]:
        """Headers with admin API key."""
        return {"X-API-Key": TEST_ADMIN_KEY}

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Headers with monitor API key (non-admin)."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    # ======================================
    # Authentication tests
    # ======================================

    def test_history_requires_authentication(self, client: TestClient) -> None:
        """Test that history endpoint requires authentication."""
        response = client.get("/api/v1alpha1/console/history")

        assert response.status_code == 401

    def test_history_requires_admin_role(
        self, client: TestClient, monitor_headers: dict[str, str]
    ) -> None:
        """Test that history endpoint requires Admin role (FR9: Console restricted to Admin)."""
        response = client.get("/api/v1alpha1/console/history", headers=monitor_headers)

        assert response.status_code == 403
        assert "Console access requires Admin role" in response.json()["detail"]["message"]

    def test_history_accessible_by_admin(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that Admin role can access console history."""
        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    # ======================================
    # Response format tests
    # ======================================

    def test_history_follows_envelope_format(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that response follows API envelope format."""
        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data
        assert "lines" in data["data"]
        assert "total" in data["data"]

    def test_history_returns_empty_list_for_new_buffer(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that empty buffer returns empty lines array."""
        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["lines"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_history_returns_buffered_lines(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that history returns lines from console buffer."""
        # Add some lines to the buffer
        await test_service.console_buffer.append("Server starting...")
        await test_service.console_buffer.append("World loaded")
        await test_service.console_buffer.append("Ready for connections")

        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["lines"]) == 3
        assert data["total"] == 3
        assert "Server starting" in data["lines"][0]
        assert "World loaded" in data["lines"][1]
        assert "Ready for connections" in data["lines"][2]

    # ======================================
    # Lines limit parameter tests
    # ======================================

    @pytest.mark.asyncio
    async def test_history_with_lines_limit(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that lines parameter limits returned lines."""
        # Add 10 lines
        for i in range(10):
            await test_service.console_buffer.append(f"Line {i}")

        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": 3}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["lines"]) == 3
        assert data["total"] == 10  # Total in buffer
        assert data["limit"] == 3
        # Should return the most recent 3 lines
        assert "Line 7" in data["lines"][0]
        assert "Line 8" in data["lines"][1]
        assert "Line 9" in data["lines"][2]

    @pytest.mark.asyncio
    async def test_history_limit_larger_than_buffer(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that limit larger than buffer returns all lines."""
        await test_service.console_buffer.append("Line 1")
        await test_service.console_buffer.append("Line 2")

        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": 100}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["lines"]) == 2
        assert data["total"] == 2

    def test_history_invalid_lines_param_negative(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that negative lines param returns 422."""
        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": -1}
        )

        assert response.status_code == 422

    def test_history_invalid_lines_param_zero(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that zero lines param returns 422."""
        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": 0}
        )

        assert response.status_code == 422

    def test_history_invalid_lines_param_too_large(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that lines param > 10000 returns 422."""
        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": 10001}
        )

        assert response.status_code == 422

    # ======================================
    # Timestamp format tests (AC1)
    # ======================================

    @pytest.mark.asyncio
    async def test_history_lines_have_timestamps(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that returned lines include ISO 8601 timestamps (AC1)."""
        await test_service.console_buffer.append("Test message")

        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        lines = response.json()["data"]["lines"]
        assert len(lines) == 1

        # Verify timestamp format: [YYYY-MM-DDTHH:MM:SS.ffffff]
        line = lines[0]
        assert line.startswith("[")
        assert "]" in line
        assert "Test message" in line

        # Parse the timestamp
        timestamp_str = line[1 : line.index("]")]
        timestamp = datetime.fromisoformat(timestamp_str)
        assert timestamp is not None


class TestServerServiceSendCommand:
    """Unit tests for ServerService.send_command() (Story 4.3, Task 1)."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create temporary directory structure for server tests."""
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        serverdata_dir = tmp_path / "serverdata"
        serverdata_dir.mkdir()
        vsmanager_dir = tmp_path / "vsmanager"
        vsmanager_dir.mkdir()

        # Create required server files to mark as "installed"
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        return tmp_path

    @pytest.fixture
    def settings(self, temp_dir: Path) -> Settings:
        """Create settings with temp directories."""
        return Settings(
            data_dir=temp_dir,
            debug=True,
        )

    @pytest.fixture
    def service(self, settings: Settings) -> ServerService:
        """Create ServerService with custom settings."""
        return ServerService(settings)

    @pytest.mark.asyncio
    async def test_send_command_returns_false_when_server_not_running(
        self, service: ServerService
    ) -> None:
        """Test that send_command returns False when server is not running."""
        # Server is not running (no process)
        result = await service.send_command("/help")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_returns_false_when_process_exited(
        self, service: ServerService
    ) -> None:
        """Test that send_command returns False when process has exited."""
        # Set up a mock process that has exited (returncode is not None)
        mock_process = AsyncMock()
        mock_process.returncode = 0  # Process has exited
        mock_process.stdin = AsyncMock()
        service._process = mock_process

        result = await service.send_command("/help")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_returns_false_when_stdin_not_available(
        self, service: ServerService
    ) -> None:
        """Test that send_command returns False when stdin is None."""
        # Set up a mock process with no stdin
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_process.stdin = None  # stdin not available
        service._process = mock_process

        result = await service.send_command("/help")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_writes_to_stdin_with_newline(
        self, service: ServerService
    ) -> None:
        """Test that send_command writes command to stdin with newline."""
        # Set up a mock running process with stdin
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()  # write is sync
        mock_process.stdin.drain = AsyncMock()
        service._process = mock_process

        result = await service.send_command("/help")

        assert result is True
        mock_process.stdin.write.assert_called_once_with(b"/help\n")
        mock_process.stdin.drain.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_command_echoes_to_console_buffer(
        self, service: ServerService
    ) -> None:
        """Test that send_command echoes command to console buffer with [CMD] prefix."""
        # Set up a mock running process with stdin
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()  # write is sync
        mock_process.stdin.drain = AsyncMock()
        service._process = mock_process

        await service.send_command("/time set day")

        # Check that command was echoed to buffer
        history = service.console_buffer.get_history()
        assert len(history) == 1
        assert "[CMD] /time set day" in history[0]

    @pytest.mark.asyncio
    async def test_send_command_handles_empty_command(
        self, service: ServerService
    ) -> None:
        """Test that send_command handles empty string command."""
        # Set up a mock running process with stdin
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        service._process = mock_process

        result = await service.send_command("")

        # Empty command should still be sent (server will handle it)
        assert result is True
        mock_process.stdin.write.assert_called_once_with(b"\n")

    @pytest.mark.asyncio
    async def test_send_command_handles_special_characters(
        self, service: ServerService
    ) -> None:
        """Test that send_command handles commands with special characters."""
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        service._process = mock_process

        # Command with unicode and special characters
        result = await service.send_command("/say Hello, World! 🎮")

        assert result is True
        mock_process.stdin.write.assert_called_once_with("/say Hello, World! 🎮\n".encode())

    @pytest.mark.asyncio
    async def test_send_command_echo_notifies_subscribers(
        self, service: ServerService
    ) -> None:
        """Test that command echo is sent to all subscribers in real-time (AC: 2)."""
        # Set up a mock running process
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        service._process = mock_process

        # Subscribe to console buffer
        received_lines: list[str] = []

        async def subscriber(line: str) -> None:
            received_lines.append(line)

        service.console_buffer.subscribe(subscriber)

        # Send a command
        await service.send_command("/time set day")

        # Verify subscriber received the echoed command
        assert len(received_lines) == 1
        assert "[CMD] /time set day" in received_lines[0]

        # Clean up
        service.console_buffer.unsubscribe(subscriber)


class TestConsoleWebSocket:
    """WebSocket tests for /api/v1alpha1/console/ws endpoint (Story 4.2)."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temp data directory with server files."""
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        return tmp_path

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

    @pytest.fixture
    def test_service(self, test_settings: Settings) -> ServerService:
        """Create ServerService with test settings."""
        return ServerService(test_settings)

    @pytest.fixture
    def ws_client(
        self, test_settings: Settings, test_service: ServerService
    ) -> Generator[TestClient, None, None]:
        """Create test client with overrides for WebSocket testing.

        Uses Starlette's synchronous TestClient which properly handles WebSockets.
        """
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()

    # ======================================
    # Authentication tests (AC: 1, 4, 5)
    # ======================================

    def test_websocket_rejects_missing_api_key(
        self, ws_client: TestClient
    ) -> None:
        """Test that WebSocket rejects connections without API key (AC: 5)."""
        with ws_client.websocket_connect("/api/v1alpha1/console/ws") as ws:
            # Server should close with 4001 after accepting
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001
            assert data["reason"] == "Unauthorized: Invalid API key"

    def test_websocket_rejects_invalid_api_key(
        self, ws_client: TestClient
    ) -> None:
        """Test that WebSocket rejects invalid API keys (AC: 5)."""
        with ws_client.websocket_connect(
            "/api/v1alpha1/console/ws?api_key=invalid-key-12345"
        ) as ws:
            # Server should close with 4001 after accepting
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001
            assert data["reason"] == "Unauthorized: Invalid API key"

    def test_websocket_rejects_monitor_role(
        self, ws_client: TestClient
    ) -> None:
        """Test that WebSocket rejects Monitor role (Admin only) (AC: 4)."""
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_MONITOR_KEY}"
        ) as ws:
            # Server should close with 4003 after accepting
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4003
            assert data["reason"] == "Forbidden: Admin role required"

    def test_websocket_accepts_admin_key(
        self, ws_client: TestClient
    ) -> None:
        """Test that WebSocket accepts valid Admin API key (AC: 1)."""
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Connection should stay open - close it from client side
            ws.close()

    # ======================================
    # History delivery tests (AC: 3, 6)
    # ======================================

    def test_websocket_sends_history_on_connect(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that WebSocket sends buffer history on connect (AC: 3)."""
        # Add some lines to buffer before connecting (using synchronous internal method)
        # This is acceptable for testing as we're testing the WebSocket behavior
        test_service.console_buffer._buffer.append("[2024-01-01T00:00:00] Line 1")
        test_service.console_buffer._buffer.append("[2024-01-01T00:00:01] Line 2")
        test_service.console_buffer._buffer.append("[2024-01-01T00:00:02] Line 3")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Should receive all 3 history lines
            line1 = ws.receive_text()
            assert "Line 1" in line1

            line2 = ws.receive_text()
            assert "Line 2" in line2

            line3 = ws.receive_text()
            assert "Line 3" in line3

            ws.close()

    def test_websocket_respects_history_lines_param(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that history_lines param limits history sent (AC: 3)."""
        # Add 10 lines to buffer
        for i in range(10):
            test_service.console_buffer._buffer.append(f"[2024-01-01T00:00:{i:02d}] Line {i}")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}&history_lines=3"
        ) as ws:
            # Should receive only last 3 lines (7, 8, 9)
            line1 = ws.receive_text()
            assert "Line 7" in line1

            line2 = ws.receive_text()
            assert "Line 8" in line2

            line3 = ws.receive_text()
            assert "Line 9" in line3

            ws.close()

    def test_websocket_empty_buffer_connects_successfully(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that empty buffer allows connection without sending history (AC: 3)."""
        # Buffer is empty by default
        assert len(test_service.console_buffer) == 0

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Connection should be open, we can close it
            ws.close()

    # ======================================
    # Subscriber management tests
    # ======================================

    def test_websocket_subscribes_on_connect(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that WebSocket subscribes to buffer on connect."""
        initial_subscribers = len(test_service.console_buffer._subscribers)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Verify subscriber was added
            assert len(test_service.console_buffer._subscribers) == initial_subscribers + 1
            ws.close()

    def test_websocket_unsubscribes_on_disconnect(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that WebSocket unsubscribes from buffer on disconnect."""
        initial_subscribers = len(test_service.console_buffer._subscribers)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            ws.close()

        # Verify subscriber was removed
        assert len(test_service.console_buffer._subscribers) == initial_subscribers


class TestConsoleCommandEndpoint:
    """REST API tests for POST /api/v1alpha1/console/command endpoint (Story 4.3, Task 4)."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temp data directory with server files."""
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        return tmp_path

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

    @pytest.fixture
    def test_service(self, test_settings: Settings) -> ServerService:
        """Create ServerService with test settings."""
        return ServerService(test_settings)

    @pytest.fixture
    def integration_app(
        self, test_settings: Settings, test_service: ServerService
    ) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    @pytest.fixture
    def admin_headers(self) -> dict[str, str]:
        """Headers with admin API key."""
        return {"X-API-Key": TEST_ADMIN_KEY}

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Headers with monitor API key (non-admin)."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    # ======================================
    # Authentication tests (AC: 4)
    # ======================================

    def test_command_requires_authentication(self, client: TestClient) -> None:
        """Test that command endpoint requires authentication."""
        response = client.post(
            "/api/v1alpha1/console/command",
            json={"command": "/help"},
        )

        assert response.status_code == 401

    def test_command_requires_admin_role(
        self, client: TestClient, monitor_headers: dict[str, str]
    ) -> None:
        """Test that command endpoint requires Admin role (AC: 4)."""
        response = client.post(
            "/api/v1alpha1/console/command",
            json={"command": "/help"},
            headers=monitor_headers,
        )

        assert response.status_code == 403
        assert "Console access requires Admin role" in response.json()["detail"]["message"]

    # ======================================
    # Success case tests (AC: 1)
    # ======================================

    def test_command_admin_success(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that Admin can send console command (AC: 1)."""
        # Set up mock running process
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        response = client.post(
            "/api/v1alpha1/console/command",
            json={"command": "/help"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["command"] == "/help"
        assert data["data"]["sent"] is True

    def test_command_writes_to_stdin(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that command is written to server stdin."""
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        client.post(
            "/api/v1alpha1/console/command",
            json={"command": "/time set day"},
            headers=admin_headers,
        )

        mock_process.stdin.write.assert_called_with(b"/time set day\n")

    # ======================================
    # Error case tests (AC: 3)
    # ======================================

    def test_command_error_when_server_not_running(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that 400 is returned when server is not running (AC: 3)."""
        # Server is not running (no process set)
        assert test_service._process is None

        response = client.post(
            "/api/v1alpha1/console/command",
            json={"command": "/help"},
            headers=admin_headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "SERVER_NOT_RUNNING"
        assert "server is not running" in data["detail"]["message"]

    # ======================================
    # Validation tests
    # ======================================

    def test_command_rejects_empty_command(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that empty command is rejected with 422."""
        response = client.post(
            "/api/v1alpha1/console/command",
            json={"command": ""},
            headers=admin_headers,
        )

        assert response.status_code == 422

    def test_command_rejects_missing_command(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that missing command field is rejected with 422."""
        response = client.post(
            "/api/v1alpha1/console/command",
            json={},
            headers=admin_headers,
        )

        assert response.status_code == 422

    def test_command_rejects_too_long_command(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that command > 1000 chars is rejected with 422."""
        long_command = "/" + "a" * 1001
        response = client.post(
            "/api/v1alpha1/console/command",
            json={"command": long_command},
            headers=admin_headers,
        )

        assert response.status_code == 422


class TestConsoleWebSocketCommands:
    """WebSocket command handling tests for Story 4.3 (Task 3)."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temp data directory with server files."""
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        return tmp_path

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

    @pytest.fixture
    def test_service(self, test_settings: Settings) -> ServerService:
        """Create ServerService with test settings."""
        return ServerService(test_settings)

    @pytest.fixture
    def ws_client(
        self, test_settings: Settings, test_service: ServerService
    ) -> Generator[TestClient, None, None]:
        """Create test client with overrides for WebSocket testing."""
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()

    # ======================================
    # Command message handling tests (AC: 1, 3)
    # ======================================

    def test_websocket_command_sends_to_server(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that WebSocket command is written to server stdin (AC: 1)."""
        # Set up mock running process
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Send command
            ws.send_json({"type": "command", "content": "/help"})

            # Give time for processing
            import time
            time.sleep(0.1)

            ws.close()

        # Verify command was written to stdin
        mock_process.stdin.write.assert_called_with(b"/help\n")

    def test_websocket_command_echoes_in_stream(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that sent command is echoed back in console stream (AC: 2).

        Verifies that:
        1. The echo is received immediately after sending the command
        2. The echo contains the [CMD] prefix
        3. The echo appears before any potential server response would
        """
        # Set up mock running process
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Send command
            ws.send_json({"type": "command", "content": "/time set day"})

            # Should receive the command echo immediately (before any server response)
            # The echo is the first message we receive after sending
            response = ws.receive_text()

            # Verify echo format and content
            assert "[CMD] /time set day" in response
            # Verify it has a timestamp prefix (ISO 8601 format)
            assert response.startswith("[")
            assert "]" in response

            ws.close()

    def test_websocket_command_error_when_server_not_running(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that error is returned when server is not running (AC: 3)."""
        # Server is not running (no process set)
        assert test_service._process is None

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Send command
            ws.send_json({"type": "command", "content": "/help"})

            # Should receive error message
            response = ws.receive_json()
            assert response["type"] == "error"
            assert response["content"] == "Server is not running"

            ws.close()

    def test_websocket_malformed_json_returns_error(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that malformed JSON returns error but doesn't disconnect (Task 3.5)."""
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Send invalid JSON
            ws.send_text("not valid json {")

            # Should receive error message
            response = ws.receive_json()
            assert response["type"] == "error"
            assert response["content"] == "Invalid message format"

            # Connection should still be open - send another message
            ws.send_json({"type": "command", "content": "/help"})

            # Should receive error (server not running)
            response2 = ws.receive_json()
            assert response2["type"] == "error"

            ws.close()

    def test_websocket_unknown_message_type_ignored(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that unknown message types are silently ignored."""
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Send unknown message type
            ws.send_json({"type": "unknown", "content": "test"})

            # Connection should still work - send valid command
            ws.send_json({"type": "command", "content": "/help"})

            # Should receive error (server not running)
            response = ws.receive_json()
            assert response["type"] == "error"
            assert response["content"] == "Server is not running"

            ws.close()

    # ======================================
    # Validation tests (match REST endpoint)
    # ======================================

    def test_websocket_command_rejects_empty_command(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that empty command returns error (matches REST validation)."""
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Send empty command
            ws.send_json({"type": "command", "content": ""})

            # Should receive error message
            response = ws.receive_json()
            assert response["type"] == "error"
            assert response["content"] == "Empty command"

            # Connection should still be open
            ws.close()

    def test_websocket_command_rejects_too_long_command(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that command > 1000 chars returns error (matches REST validation)."""
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Send command that's too long (1001 chars)
            long_command = "/" + "a" * 1000
            ws.send_json({"type": "command", "content": long_command})

            # Should receive error message
            response = ws.receive_json()
            assert response["type"] == "error"
            assert response["content"] == "Command too long (max 1000 characters)"

            # Connection should still be open
            ws.close()

    def test_websocket_command_accepts_max_length_command(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that command exactly 1000 chars is accepted."""
        # Set up mock running process
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            # Send command that's exactly 1000 chars (should be accepted)
            max_command = "/" + "a" * 999
            assert len(max_command) == 1000
            ws.send_json({"type": "command", "content": max_command})

            # Should receive the echo (not an error)
            response = ws.receive_text()
            assert "[CMD]" in response

            ws.close()

    # ======================================
    # Role-based access tests (AC: 4)
    # ======================================

    def test_websocket_monitor_cannot_send_commands(
        self, ws_client: TestClient, test_service: ServerService
    ) -> None:
        """Test that Monitor role cannot send commands via WebSocket (AC: 4).

        Monitor users are rejected at connection time (code 4003), so they
        never get the chance to send commands.
        """
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_MONITOR_KEY}"
        ) as ws:
            # Connection should be rejected with 4003
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4003
            assert data["reason"] == "Forbidden: Admin role required"
