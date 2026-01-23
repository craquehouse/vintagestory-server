"""Unit tests for WebSocket helper functions in console router.

Tests for internal helper functions that extract client IP, verify API keys,
and handle authentication logic.
"""

from unittest.mock import MagicMock

import pytest


class TestGetWebSocketClientIP:
    """Tests for _get_websocket_client_ip helper function."""

    def test_extracts_x_forwarded_for_header(self) -> None:
        """Test that x-forwarded-for header is used when present."""
        from vintagestory_api.routers.console import _get_websocket_client_ip

        # Create mock WebSocket with x-forwarded-for header
        websocket = MagicMock()
        websocket.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        websocket.client.host = "127.0.0.1"

        result = _get_websocket_client_ip(websocket)

        # Should extract first IP from comma-separated list
        assert result == "192.168.1.1"

    def test_extracts_x_real_ip_header(self) -> None:
        """Test that x-real-ip header is used when x-forwarded-for is absent."""
        from vintagestory_api.routers.console import _get_websocket_client_ip

        # Create mock WebSocket with x-real-ip header
        websocket = MagicMock()
        websocket.headers = {"x-real-ip": "192.168.1.100"}
        websocket.client.host = "127.0.0.1"

        result = _get_websocket_client_ip(websocket)

        assert result == "192.168.1.100"

    def test_prefers_forwarded_for_over_real_ip(self) -> None:
        """Test that x-forwarded-for takes precedence over x-real-ip."""
        from vintagestory_api.routers.console import _get_websocket_client_ip

        websocket = MagicMock()
        websocket.headers = {
            "x-forwarded-for": "192.168.1.1",
            "x-real-ip": "10.0.0.1",
        }
        websocket.client.host = "127.0.0.1"

        result = _get_websocket_client_ip(websocket)

        assert result == "192.168.1.1"

    def test_falls_back_to_client_host(self) -> None:
        """Test that websocket.client.host is used when no proxy headers present."""
        from vintagestory_api.routers.console import _get_websocket_client_ip

        websocket = MagicMock()
        websocket.headers = {}
        websocket.client.host = "127.0.0.1"

        result = _get_websocket_client_ip(websocket)

        assert result == "127.0.0.1"

    def test_handles_missing_client(self) -> None:
        """Test that 'unknown' is returned when websocket.client is None."""
        from vintagestory_api.routers.console import _get_websocket_client_ip

        websocket = MagicMock()
        websocket.headers = {}
        websocket.client = None

        result = _get_websocket_client_ip(websocket)

        assert result == "unknown"


class TestVerifyAPIKeyWithSettings:
    """Tests for _verify_api_key_with_settings helper function."""

    def test_returns_none_for_missing_api_key(self) -> None:
        """Test that None is returned when api_key is None."""
        from vintagestory_api.routers.console import _verify_api_key_with_settings

        result = _verify_api_key_with_settings(None, "admin-key", "monitor-key")

        assert result is None

    def test_returns_none_for_empty_api_key(self) -> None:
        """Test that None is returned when api_key is empty string."""
        from vintagestory_api.routers.console import _verify_api_key_with_settings

        result = _verify_api_key_with_settings("", "admin-key", "monitor-key")

        assert result is None

    def test_returns_admin_for_valid_admin_key(self) -> None:
        """Test that 'admin' is returned for valid admin key."""
        from vintagestory_api.routers.console import _verify_api_key_with_settings

        result = _verify_api_key_with_settings("admin-key", "admin-key", "monitor-key")

        assert result == "admin"

    def test_returns_monitor_for_valid_monitor_key(self) -> None:
        """Test that 'monitor' is returned for valid monitor key."""
        from vintagestory_api.routers.console import _verify_api_key_with_settings

        result = _verify_api_key_with_settings("monitor-key", "admin-key", "monitor-key")

        assert result == "monitor"

    def test_returns_none_for_invalid_key(self) -> None:
        """Test that None is returned for invalid key."""
        from vintagestory_api.routers.console import _verify_api_key_with_settings

        result = _verify_api_key_with_settings("invalid-key", "admin-key", "monitor-key")

        assert result is None

    def test_handles_none_monitor_key(self) -> None:
        """Test that None monitor_key is handled correctly."""
        from vintagestory_api.routers.console import _verify_api_key_with_settings

        # Should return admin for admin key
        result1 = _verify_api_key_with_settings("admin-key", "admin-key", None)
        assert result1 == "admin"

        # Should return None for any other key
        result2 = _verify_api_key_with_settings("other-key", "admin-key", None)
        assert result2 is None

    def test_uses_timing_safe_comparison(self) -> None:
        """Test that timing-safe comparison is used (smoke test)."""
        from vintagestory_api.routers.console import _verify_api_key_with_settings

        # This is a smoke test - we can't easily test that secrets.compare_digest
        # is used, but we can verify the function works correctly with similar keys
        result = _verify_api_key_with_settings(
            "admin-key-wrong",
            "admin-key-right",
            "monitor-key",
        )

        assert result is None


class TestVerifyWSAuth:
    """Tests for _verify_ws_auth helper function."""

    @pytest.mark.asyncio
    async def test_prefers_token_over_api_key(self) -> None:
        """Test that token authentication takes precedence over api_key."""
        from unittest.mock import AsyncMock

        from vintagestory_api.config import Settings
        from vintagestory_api.routers.console import _verify_ws_auth

        # Create mock token service that validates the token
        token_service = AsyncMock()
        token_service.validate_token = AsyncMock(return_value="admin")

        # Create settings with API keys
        settings = Settings(
            api_key_admin="admin-key",
            api_key_monitor="monitor-key",
        )

        # Call with both token and api_key - token should be used
        result = await _verify_ws_auth(
            token="valid-token",
            api_key="admin-key",
            token_service=token_service,
            settings=settings,
            client_ip="127.0.0.1",
        )

        assert result == "admin"
        token_service.validate_token.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_falls_back_to_api_key_when_no_token(self) -> None:
        """Test that api_key is used when token is None."""
        from unittest.mock import AsyncMock

        from vintagestory_api.config import Settings
        from vintagestory_api.routers.console import _verify_ws_auth

        token_service = AsyncMock()
        settings = Settings(
            api_key_admin="admin-key",
            api_key_monitor="monitor-key",
        )

        # Call with only api_key (no token)
        result = await _verify_ws_auth(
            token=None,
            api_key="admin-key",
            token_service=token_service,
            settings=settings,
            client_ip="127.0.0.1",
        )

        assert result == "admin"
        # Token validation should not be called
        token_service.validate_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_token(self) -> None:
        """Test that None is returned when token is invalid."""
        from unittest.mock import AsyncMock

        from vintagestory_api.config import Settings
        from vintagestory_api.routers.console import _verify_ws_auth

        token_service = AsyncMock()
        token_service.validate_token = AsyncMock(return_value=None)

        settings = Settings(api_key_admin="admin-key")

        result = await _verify_ws_auth(
            token="invalid-token",
            api_key=None,
            token_service=token_service,
            settings=settings,
            client_ip="127.0.0.1",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_both_missing(self) -> None:
        """Test that None is returned when both token and api_key are None."""
        from unittest.mock import AsyncMock

        from vintagestory_api.config import Settings
        from vintagestory_api.routers.console import _verify_ws_auth

        token_service = AsyncMock()
        settings = Settings(api_key_admin="admin-key")

        result = await _verify_ws_auth(
            token=None,
            api_key=None,
            token_service=token_service,
            settings=settings,
            client_ip="127.0.0.1",
        )

        assert result is None
