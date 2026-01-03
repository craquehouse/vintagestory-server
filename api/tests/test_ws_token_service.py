"""Tests for WebSocket token service.

Story 9.1: Secure WebSocket Authentication

Tests cover:
- Token generation with secure random bytes
- Token validation (valid/invalid/expired cases)
- Token expiry and cleanup behavior
- Role preservation through token lifecycle
- Singleton service behavior
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from vintagestory_api.services.ws_token_service import (
    DEFAULT_TOKEN_TTL_SECONDS,
    StoredToken,
    WebSocketTokenService,
    get_ws_token_service,
    reset_ws_token_service,
)


class TestStoredToken:
    """Tests for StoredToken dataclass."""

    def test_stored_token_creation(self) -> None:
        """StoredToken holds all required fields."""
        now = datetime.now(UTC)
        token = StoredToken(
            token="test-token",
            role="admin",
            expires_at=now + timedelta(seconds=300),
            created_at=now,
        )

        assert token.token == "test-token"
        assert token.role == "admin"
        assert token.expires_at > now
        assert token.created_at == now


class TestWebSocketTokenService:
    """Tests for WebSocketTokenService."""

    @pytest.fixture
    def service(self) -> WebSocketTokenService:
        """Create a fresh token service for each test."""
        return WebSocketTokenService()

    def test_create_token_returns_stored_token(
        self, service: WebSocketTokenService
    ) -> None:
        """create_token returns a StoredToken with all fields populated."""
        result = service.create_token("admin")

        assert isinstance(result, StoredToken)
        assert result.token  # Non-empty
        assert result.role == "admin"
        assert result.expires_at > datetime.now(UTC)
        assert result.created_at <= datetime.now(UTC)

    def test_create_token_uses_secure_random(
        self, service: WebSocketTokenService
    ) -> None:
        """Token generation uses cryptographically secure random bytes."""
        # Create multiple tokens and verify they're unique
        tokens = {service.create_token("admin").token for _ in range(10)}
        assert len(tokens) == 10  # All unique

    def test_create_token_preserves_role_admin(
        self, service: WebSocketTokenService
    ) -> None:
        """create_token preserves 'admin' role."""
        result = service.create_token("admin")
        assert result.role == "admin"

    def test_create_token_preserves_role_monitor(
        self, service: WebSocketTokenService
    ) -> None:
        """create_token preserves 'monitor' role."""
        result = service.create_token("monitor")
        assert result.role == "monitor"

    def test_create_token_sets_expiry(self, service: WebSocketTokenService) -> None:
        """create_token sets expiry based on TTL."""
        result = service.create_token("admin")

        # Expiry should be approximately TTL seconds from now
        expected_expiry = datetime.now(UTC) + timedelta(seconds=DEFAULT_TOKEN_TTL_SECONDS)
        # Allow 1 second tolerance for test execution time
        assert abs((result.expires_at - expected_expiry).total_seconds()) < 1

    def test_create_token_custom_ttl(self) -> None:
        """Service respects custom TTL setting."""
        service = WebSocketTokenService(token_ttl_seconds=60)
        result = service.create_token("admin")

        expected_expiry = datetime.now(UTC) + timedelta(seconds=60)
        assert abs((result.expires_at - expected_expiry).total_seconds()) < 1

    def test_validate_token_returns_role_when_valid(
        self, service: WebSocketTokenService
    ) -> None:
        """validate_token returns role for valid token."""
        stored = service.create_token("admin")

        role = service.validate_token(stored.token)

        assert role == "admin"

    def test_validate_token_returns_none_for_invalid(
        self, service: WebSocketTokenService
    ) -> None:
        """validate_token returns None for non-existent token."""
        role = service.validate_token("invalid-token")

        assert role is None

    def test_validate_token_returns_none_when_expired(
        self, service: WebSocketTokenService
    ) -> None:
        """validate_token returns None for expired token."""
        stored = service.create_token("admin")

        # Manually expire the token by manipulating the stored entry
        service._tokens[stored.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        role = service.validate_token(stored.token)

        assert role is None
        # Token should be removed from storage
        assert stored.token not in service._tokens

    def test_validate_token_removes_expired_from_storage(
        self, service: WebSocketTokenService
    ) -> None:
        """validate_token removes expired tokens from storage."""
        stored = service.create_token("admin")
        token_str = stored.token

        # Expire the token
        service._tokens[token_str].expires_at = datetime.now(UTC) - timedelta(seconds=1)

        # Validate triggers removal
        service.validate_token(token_str)

        assert token_str not in service._tokens

    def test_cleanup_expired_removes_old_tokens(
        self, service: WebSocketTokenService
    ) -> None:
        """_cleanup_expired removes all expired tokens."""
        # Create some tokens
        token1 = service.create_token("admin")
        token2 = service.create_token("monitor")
        token3 = service.create_token("admin")

        # Expire first two
        service._tokens[token1.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )
        service._tokens[token2.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        # Trigger cleanup
        service._cleanup_expired()

        assert token1.token not in service._tokens
        assert token2.token not in service._tokens
        assert token3.token in service._tokens

    def test_active_token_count_after_create(
        self, service: WebSocketTokenService
    ) -> None:
        """active_token_count reflects number of valid tokens."""
        assert service.active_token_count == 0

        service.create_token("admin")
        assert service.active_token_count == 1

        service.create_token("monitor")
        assert service.active_token_count == 2

    def test_active_token_count_excludes_expired(
        self, service: WebSocketTokenService
    ) -> None:
        """active_token_count excludes expired tokens."""
        token1 = service.create_token("admin")
        service.create_token("monitor")

        # Expire one
        service._tokens[token1.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        # Count triggers cleanup
        assert service.active_token_count == 1

    def test_create_triggers_cleanup(self, service: WebSocketTokenService) -> None:
        """Creating a new token triggers cleanup of expired tokens."""
        token1 = service.create_token("admin")

        # Expire the first token
        service._tokens[token1.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        # Create new token - should trigger cleanup
        service.create_token("monitor")

        # Expired token should be gone
        assert token1.token not in service._tokens

    def test_token_length_is_reasonable(self, service: WebSocketTokenService) -> None:
        """Generated tokens have reasonable length for URL safety."""
        token = service.create_token("admin")

        # 32 bytes base64-encoded = 43 characters
        assert len(token.token) == 43


class TestWebSocketTokenServiceSingleton:
    """Tests for singleton service behavior."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_ws_token_service()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        reset_ws_token_service()

    def test_get_ws_token_service_returns_same_instance(self) -> None:
        """get_ws_token_service returns the same instance on multiple calls."""
        service1 = get_ws_token_service()
        service2 = get_ws_token_service()

        assert service1 is service2

    def test_reset_clears_singleton(self) -> None:
        """reset_ws_token_service clears the singleton."""
        service1 = get_ws_token_service()
        reset_ws_token_service()
        service2 = get_ws_token_service()

        assert service1 is not service2

    def test_singleton_persists_tokens(self) -> None:
        """Tokens created via singleton persist across calls."""
        service = get_ws_token_service()
        token = service.create_token("admin")

        # Get service again
        service2 = get_ws_token_service()
        role = service2.validate_token(token.token)

        assert role == "admin"


class TestTokenExpiration:
    """Tests for token expiration edge cases."""

    def test_token_valid_just_before_expiry(self) -> None:
        """Token is valid right before expiration."""
        service = WebSocketTokenService(token_ttl_seconds=300)
        stored = service.create_token("admin")

        # Set expiry to 1 second from now
        service._tokens[stored.token].expires_at = datetime.now(UTC) + timedelta(
            seconds=1
        )

        role = service.validate_token(stored.token)
        assert role == "admin"

    def test_token_invalid_just_after_expiry(self) -> None:
        """Token is invalid right after expiration."""
        service = WebSocketTokenService(token_ttl_seconds=300)
        stored = service.create_token("admin")

        # Set expiry to 1 microsecond ago
        service._tokens[stored.token].expires_at = datetime.now(UTC) - timedelta(
            microseconds=1
        )

        role = service.validate_token(stored.token)
        assert role is None

    def test_multiple_tokens_same_role(self) -> None:
        """Multiple tokens can be created for the same role."""
        service = WebSocketTokenService()

        token1 = service.create_token("admin")
        token2 = service.create_token("admin")

        assert token1.token != token2.token
        assert service.validate_token(token1.token) == "admin"
        assert service.validate_token(token2.token) == "admin"

    def test_token_reuse_after_expiry_fails(self) -> None:
        """Cannot reuse a token after it expires."""
        service = WebSocketTokenService()
        stored = service.create_token("admin")

        # Validate once - should work
        assert service.validate_token(stored.token) == "admin"

        # Expire the token
        service._tokens[stored.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        # Validate again - should fail
        assert service.validate_token(stored.token) is None
