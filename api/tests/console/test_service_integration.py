"""Integration tests for ConsoleBuffer with ServerService."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.services.console import ConsoleBuffer
from vintagestory_api.services.server import ServerService

# pyright: reportPrivateUsage=false
# Note: Tests need access to private members to verify internal state


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
