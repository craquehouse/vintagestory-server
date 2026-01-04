"""Tests for console command functionality - service and endpoint."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from vintagestory_api.services.server import ServerService

# pyright: reportPrivateUsage=false
# Note: Tests need access to private members to verify internal state


class TestServerServiceSendCommand:
    """Unit tests for ServerService.send_command() (Story 4.3, Task 1)."""

    @pytest.mark.asyncio
    async def test_send_command_returns_false_when_server_not_running(
        self, test_service: ServerService
    ) -> None:
        """Test that send_command returns False when server is not running."""
        # Server is not running (no process)
        result = await test_service.send_command("/help")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_returns_false_when_process_exited(
        self, test_service: ServerService
    ) -> None:
        """Test that send_command returns False when process has exited."""
        # Set up a mock process that has exited (returncode is not None)
        mock_process = AsyncMock()
        mock_process.returncode = 0  # Process has exited
        mock_process.stdin = AsyncMock()
        test_service._process = mock_process

        result = await test_service.send_command("/help")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_returns_false_when_stdin_not_available(
        self, test_service: ServerService
    ) -> None:
        """Test that send_command returns False when stdin is None."""
        # Set up a mock process with no stdin
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_process.stdin = None  # stdin not available
        test_service._process = mock_process

        result = await test_service.send_command("/help")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_writes_to_stdin_with_newline(
        self, test_service: ServerService
    ) -> None:
        """Test that send_command writes command to stdin with newline."""
        # Set up a mock running process with stdin
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()  # write is sync
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        result = await test_service.send_command("/help")

        assert result is True
        mock_process.stdin.write.assert_called_once_with(b"/help\n")
        mock_process.stdin.drain.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_command_echoes_to_console_buffer(
        self, test_service: ServerService
    ) -> None:
        """Test that send_command echoes command to console buffer with [CMD] prefix and ANSI color."""
        # Set up a mock running process with stdin
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()  # write is sync
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        await test_service.send_command("/time set day")

        # Check that command was echoed to buffer with [CMD] prefix
        history = test_service.console_buffer.get_history()
        assert len(history) == 1
        assert "[CMD] /time set day" in history[0]

    @pytest.mark.asyncio
    async def test_send_command_echo_has_ansi_cyan_color(
        self, test_service: ServerService
    ) -> None:
        """Test that command echo includes ANSI cyan color codes (Story 9.5, AC: 1)."""
        # Set up a mock running process with stdin
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        await test_service.send_command("/help")

        # Check that ANSI codes are present: \x1b[36m (cyan) and \x1b[0m (reset)
        history = test_service.console_buffer.get_history()
        assert len(history) == 1
        echo_line = history[0]
        # Verify cyan color code at start
        assert echo_line.startswith("\x1b[36m"), "Echo should start with ANSI cyan code"
        # Verify reset code at end
        assert echo_line.endswith("\x1b[0m"), "Echo should end with ANSI reset code"
        # Verify full format: \x1b[36m[CMD] /help\x1b[0m
        assert echo_line == "\x1b[36m[CMD] /help\x1b[0m"

    @pytest.mark.asyncio
    async def test_send_command_handles_empty_command(
        self, test_service: ServerService
    ) -> None:
        """Test that send_command handles empty string command."""
        # Set up a mock running process with stdin
        mock_process = AsyncMock()
        mock_process.returncode = None  # Process is running
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        result = await test_service.send_command("")

        # Empty command should still be sent (server will handle it)
        assert result is True
        mock_process.stdin.write.assert_called_once_with(b"\n")

    @pytest.mark.asyncio
    async def test_send_command_handles_special_characters(
        self, test_service: ServerService
    ) -> None:
        """Test that send_command handles commands with special characters."""
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        # Command with unicode and special characters
        result = await test_service.send_command("/say Hello, World! 🎮")

        assert result is True
        mock_process.stdin.write.assert_called_once_with("/say Hello, World! 🎮\n".encode())

    @pytest.mark.asyncio
    async def test_send_command_echo_notifies_subscribers(
        self, test_service: ServerService
    ) -> None:
        """Test that command echo is sent to all subscribers in real-time (AC: 2)."""
        # Set up a mock running process
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        test_service._process = mock_process

        # Subscribe to console buffer
        received_lines: list[str] = []

        async def subscriber(line: str) -> None:
            received_lines.append(line)

        test_service.console_buffer.subscribe(subscriber)

        # Send a command
        await test_service.send_command("/time set day")

        # Verify subscriber received the echoed command
        assert len(received_lines) == 1
        assert "[CMD] /time set day" in received_lines[0]

        # Clean up
        test_service.console_buffer.unsubscribe(subscriber)


class TestConsoleCommandEndpoint:
    """REST API tests for POST /api/v1alpha1/console/command endpoint (Story 4.3, Task 4)."""

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
