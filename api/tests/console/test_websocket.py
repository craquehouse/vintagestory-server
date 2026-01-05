"""WebSocket tests for /api/v1alpha1/console/ws endpoint."""

import time
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from vintagestory_api.services.server import ServerService

from .conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY

# pyright: reportPrivateUsage=false
# Note: Tests need access to private members to verify internal state


class TestConsoleWebSocket:
    """WebSocket tests for /api/v1alpha1/console/ws endpoint (Story 4.2)."""

    # ======================================
    # Authentication tests (AC: 1, 4, 5)
    # ======================================

    def test_websocket_rejects_missing_api_key(self, ws_client: TestClient) -> None:
        """Test that WebSocket rejects connections without API key (AC: 5)."""
        with ws_client.websocket_connect("/api/v1alpha1/console/ws") as ws:
            # Server should close with 4001 after accepting
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001
            assert data["reason"] == "Unauthorized: Invalid API key"

    def test_websocket_rejects_invalid_api_key(self, ws_client: TestClient) -> None:
        """Test that WebSocket rejects invalid API keys (AC: 5)."""
        with ws_client.websocket_connect(
            "/api/v1alpha1/console/ws?api_key=invalid-key-12345"
        ) as ws:
            # Server should close with 4001 after accepting
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001
            assert data["reason"] == "Unauthorized: Invalid API key"

    def test_websocket_rejects_monitor_role(self, ws_client: TestClient) -> None:
        """Test that WebSocket rejects Monitor role (Admin only) (AC: 4)."""
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_MONITOR_KEY}"
        ) as ws:
            # Server should close with 4003 after accepting
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4003
            assert data["reason"] == "Forbidden: Admin role required"

    def test_websocket_accepts_admin_key(self, ws_client: TestClient) -> None:
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


class TestConsoleWebSocketCommands:
    """WebSocket command handling tests for Story 4.3 (Task 3)."""

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

            # Verify echo format and content (includes ANSI color codes)
            assert "[CMD] /time set day" in response
            # Verify ANSI cyan color code is present (Story 9.5)
            assert "\x1b[36m" in response, "Echo should include ANSI cyan code"
            assert "\x1b[0m" in response, "Echo should include ANSI reset code"

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
