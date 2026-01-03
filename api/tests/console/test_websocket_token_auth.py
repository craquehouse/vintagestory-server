"""WebSocket token authentication tests for Story 9.1.

Tests cover:
- Token authentication for console WebSocket (AC: 2)
- Token authentication for logs WebSocket (AC: 2)
- Invalid/expired token rejection (AC: 3)
- Monitor role token rejection for console access (AC: 6)
- Backwards compatibility with legacy api_key (Task 3.4)
"""

from fastapi.testclient import TestClient

from vintagestory_api.services.server import ServerService
from vintagestory_api.services.ws_token_service import WebSocketTokenService

from .conftest import TEST_ADMIN_KEY

# pyright: reportPrivateUsage=false


class TestConsoleWebSocketTokenAuth:
    """Token authentication tests for /api/v1alpha1/console/ws (AC: 2, 3, 6)."""

    # ======================================
    # Valid token tests (AC: 2)
    # ======================================

    def test_websocket_accepts_valid_admin_token(
        self, ws_client: TestClient, test_token_service: WebSocketTokenService
    ) -> None:
        """Given valid admin token, WebSocket connection succeeds (AC: 2)."""
        # Create token
        token = test_token_service.create_token("admin")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?token={token.token}"
        ) as ws:
            # Connection should stay open - close it from client side
            ws.close()

    def test_websocket_sends_history_with_token_auth(
        self,
        ws_client: TestClient,
        test_service: ServerService,
        test_token_service: WebSocketTokenService,
    ) -> None:
        """Token-authenticated WebSocket receives history on connect."""
        # Add some lines to buffer
        test_service.console_buffer._buffer.append("[2024-01-01] Line 1")
        test_service.console_buffer._buffer.append("[2024-01-01] Line 2")

        token = test_token_service.create_token("admin")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?token={token.token}"
        ) as ws:
            line1 = ws.receive_text()
            assert "Line 1" in line1

            line2 = ws.receive_text()
            assert "Line 2" in line2

            ws.close()

    # ======================================
    # Invalid/expired token tests (AC: 3)
    # ======================================

    def test_websocket_rejects_invalid_token(self, ws_client: TestClient) -> None:
        """Given invalid token, WebSocket rejected with code 4001 (AC: 3)."""
        with ws_client.websocket_connect(
            "/api/v1alpha1/console/ws?token=invalid-token-12345"
        ) as ws:
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001
            assert "Invalid or expired token" in data["reason"]

    def test_websocket_rejects_expired_token(
        self, ws_client: TestClient, test_token_service: WebSocketTokenService
    ) -> None:
        """Given expired token, WebSocket rejected with code 4001 (AC: 3)."""
        from datetime import UTC, datetime, timedelta

        # Create token then manually expire it
        token = test_token_service.create_token("admin")
        test_token_service._tokens[token.token].expires_at = datetime.now(
            UTC
        ) - timedelta(seconds=1)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?token={token.token}"
        ) as ws:
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001
            assert "Invalid or expired token" in data["reason"]

    def test_websocket_rejects_missing_both_token_and_api_key(
        self, ws_client: TestClient
    ) -> None:
        """Given neither token nor api_key, WebSocket rejected with 4001."""
        with ws_client.websocket_connect("/api/v1alpha1/console/ws") as ws:
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001

    # ======================================
    # Monitor role token tests (AC: 6)
    # ======================================

    def test_websocket_rejects_monitor_token(
        self, ws_client: TestClient, test_token_service: WebSocketTokenService
    ) -> None:
        """Given monitor role token, console WebSocket rejected with 4003 (AC: 6)."""
        token = test_token_service.create_token("monitor")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?token={token.token}"
        ) as ws:
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4003
            assert "Admin role required" in data["reason"]

    # ======================================
    # Token precedence tests (Task 3.4)
    # ======================================

    def test_websocket_token_takes_precedence_over_api_key(
        self, ws_client: TestClient, test_token_service: WebSocketTokenService
    ) -> None:
        """When both token and api_key provided, token takes precedence."""
        # Create admin token
        token = test_token_service.create_token("admin")

        # Provide both token and invalid api_key - should succeed with token
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?token={token.token}&api_key=invalid-key"
        ) as ws:
            ws.close()

    def test_websocket_invalid_token_fails_even_with_valid_api_key(
        self, ws_client: TestClient
    ) -> None:
        """Invalid token fails even if valid api_key is provided."""
        # Provide invalid token with valid api_key - token takes precedence
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?token=invalid-token&api_key={TEST_ADMIN_KEY}"
        ) as ws:
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001

    # ======================================
    # Legacy api_key backwards compatibility (Task 3.4)
    # ======================================

    def test_websocket_legacy_api_key_still_works(self, ws_client: TestClient) -> None:
        """Legacy api_key authentication still works for backwards compatibility."""
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/ws?api_key={TEST_ADMIN_KEY}"
        ) as ws:
            ws.close()


class TestLogsWebSocketTokenAuth:
    """Token authentication tests for /api/v1alpha1/console/logs/ws (AC: 2, 3, 6)."""

    # ======================================
    # Valid token tests (AC: 2)
    # ======================================

    def test_logs_websocket_accepts_valid_admin_token(
        self,
        ws_client: TestClient,
        test_token_service: WebSocketTokenService,
        temp_data_dir,  # type: ignore[no-untyped-def]
    ) -> None:
        """Given valid admin token, logs WebSocket connection succeeds (AC: 2)."""
        from pathlib import Path

        # Create log file
        logs_dir = Path(temp_data_dir) / "serverdata" / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "test.log").write_text("Test log line")

        token = test_token_service.create_token("admin")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=test.log&token={token.token}"
        ) as ws:
            # Should receive history
            line = ws.receive_text()
            assert "Test log line" in line
            ws.close()

    # ======================================
    # Invalid/expired token tests (AC: 3)
    # ======================================

    def test_logs_websocket_rejects_invalid_token(
        self, ws_client: TestClient, temp_data_dir  # type: ignore[no-untyped-def]
    ) -> None:
        """Given invalid token, logs WebSocket rejected with code 4001 (AC: 3)."""
        from pathlib import Path

        # Create log file
        logs_dir = Path(temp_data_dir) / "serverdata" / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "test.log").write_text("Test log line")

        with ws_client.websocket_connect(
            "/api/v1alpha1/console/logs/ws?file=test.log&token=invalid-token"
        ) as ws:
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001
            assert "Invalid or expired token" in data["reason"]

    def test_logs_websocket_rejects_expired_token(
        self,
        ws_client: TestClient,
        test_token_service: WebSocketTokenService,
        temp_data_dir,  # type: ignore[no-untyped-def]
    ) -> None:
        """Given expired token, logs WebSocket rejected with code 4001 (AC: 3)."""
        from datetime import UTC, datetime, timedelta
        from pathlib import Path

        # Create log file
        logs_dir = Path(temp_data_dir) / "serverdata" / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "test.log").write_text("Test log line")

        # Create token then manually expire it
        token = test_token_service.create_token("admin")
        test_token_service._tokens[token.token].expires_at = datetime.now(
            UTC
        ) - timedelta(seconds=1)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=test.log&token={token.token}"
        ) as ws:
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4001

    # ======================================
    # Monitor role token tests (AC: 6)
    # ======================================

    def test_logs_websocket_rejects_monitor_token(
        self,
        ws_client: TestClient,
        test_token_service: WebSocketTokenService,
        temp_data_dir,  # type: ignore[no-untyped-def]
    ) -> None:
        """Given monitor role token, logs WebSocket rejected with 4003 (AC: 6)."""
        from pathlib import Path

        # Create log file
        logs_dir = Path(temp_data_dir) / "serverdata" / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "test.log").write_text("Test log line")

        token = test_token_service.create_token("monitor")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=test.log&token={token.token}"
        ) as ws:
            data = ws.receive()
            assert data["type"] == "websocket.close"
            assert data["code"] == 4003
            assert "Admin role required" in data["reason"]

    # ======================================
    # Legacy api_key backwards compatibility (Task 3.4)
    # ======================================

    def test_logs_websocket_legacy_api_key_still_works(
        self, ws_client: TestClient, temp_data_dir  # type: ignore[no-untyped-def]
    ) -> None:
        """Legacy api_key authentication still works for backwards compatibility."""
        from pathlib import Path

        # Create log file
        logs_dir = Path(temp_data_dir) / "serverdata" / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "test.log").write_text("Test log line")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=test.log&api_key={TEST_ADMIN_KEY}"
        ) as ws:
            ws.close()
