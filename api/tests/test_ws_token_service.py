"""Tests for WebSocket token service.

Story 9.1: Secure WebSocket Authentication

Tests cover:
- Token generation with secure random bytes
- Token validation (valid/invalid/expired cases)
- Token expiry and cleanup behavior
- Role preservation through token lifecycle
- Singleton service behavior
- Thread-safety via asyncio.Lock
- Memory limits via max_tokens

Note: Tests access private members (_tokens, _cleanup_expired_unlocked) to verify internal
state changes that can't be observed through the public API. This is intentional
for testing purposes.
"""

# pyright: reportPrivateUsage=false

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from vintagestory_api.services.ws_token_service import (
    DEFAULT_TOKEN_TTL_SECONDS,
    MAX_TOKEN_COUNT,
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

    @pytest.mark.asyncio
    async def test_create_token_returns_stored_token(
        self, service: WebSocketTokenService
    ) -> None:
        """create_token returns a StoredToken with all fields populated."""
        result = await service.create_token("admin")

        assert isinstance(result, StoredToken)
        assert result.token  # Non-empty
        assert result.role == "admin"
        assert result.expires_at > datetime.now(UTC)
        assert result.created_at <= datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_create_token_uses_secure_random(
        self, service: WebSocketTokenService
    ) -> None:
        """Token generation uses cryptographically secure random bytes."""
        # Create multiple tokens and verify they're unique
        tokens: set[str] = set()
        for _ in range(10):
            t = await service.create_token("admin")
            tokens.add(t.token)
        assert len(tokens) == 10  # All unique

    @pytest.mark.asyncio
    async def test_create_token_preserves_role_admin(
        self, service: WebSocketTokenService
    ) -> None:
        """create_token preserves 'admin' role."""
        result = await service.create_token("admin")
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_create_token_preserves_role_monitor(
        self, service: WebSocketTokenService
    ) -> None:
        """create_token preserves 'monitor' role."""
        result = await service.create_token("monitor")
        assert result.role == "monitor"

    @pytest.mark.asyncio
    async def test_create_token_sets_expiry(
        self, service: WebSocketTokenService
    ) -> None:
        """create_token sets expiry based on TTL."""
        result = await service.create_token("admin")

        # Expiry should be approximately TTL seconds from now
        expected_expiry = datetime.now(UTC) + timedelta(seconds=DEFAULT_TOKEN_TTL_SECONDS)
        # Allow 1 second tolerance for test execution time
        assert abs((result.expires_at - expected_expiry).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_create_token_custom_ttl(self) -> None:
        """Service respects custom TTL setting."""
        service = WebSocketTokenService(token_ttl_seconds=60)
        result = await service.create_token("admin")

        expected_expiry = datetime.now(UTC) + timedelta(seconds=60)
        assert abs((result.expires_at - expected_expiry).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_validate_token_returns_role_when_valid(
        self, service: WebSocketTokenService
    ) -> None:
        """validate_token returns role for valid token."""
        stored = await service.create_token("admin")

        role = await service.validate_token(stored.token)

        assert role == "admin"

    @pytest.mark.asyncio
    async def test_validate_token_returns_none_for_invalid(
        self, service: WebSocketTokenService
    ) -> None:
        """validate_token returns None for non-existent token."""
        role = await service.validate_token("invalid-token")

        assert role is None

    @pytest.mark.asyncio
    async def test_validate_token_returns_none_when_expired(
        self, service: WebSocketTokenService
    ) -> None:
        """validate_token returns None for expired token."""
        stored = await service.create_token("admin")

        # Manually expire the token by manipulating the stored entry
        service._tokens[stored.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        role = await service.validate_token(stored.token)

        assert role is None
        # Token should be removed from storage
        assert stored.token not in service._tokens

    @pytest.mark.asyncio
    async def test_validate_token_removes_expired_from_storage(
        self, service: WebSocketTokenService
    ) -> None:
        """validate_token removes expired tokens from storage."""
        stored = await service.create_token("admin")
        token_str = stored.token

        # Expire the token
        service._tokens[token_str].expires_at = datetime.now(UTC) - timedelta(seconds=1)

        # Validate triggers removal
        await service.validate_token(token_str)

        assert token_str not in service._tokens

    @pytest.mark.asyncio
    async def test_cleanup_expired_removes_old_tokens(
        self, service: WebSocketTokenService
    ) -> None:
        """_cleanup_expired_unlocked removes all expired tokens."""
        # Create some tokens
        token1 = await service.create_token("admin")
        token2 = await service.create_token("monitor")
        token3 = await service.create_token("admin")

        # Expire first two
        service._tokens[token1.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )
        service._tokens[token2.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        # Trigger cleanup (must acquire lock manually for internal method)
        async with service._lock:
            service._cleanup_expired_unlocked()

        assert token1.token not in service._tokens
        assert token2.token not in service._tokens
        assert token3.token in service._tokens

    @pytest.mark.asyncio
    async def test_active_token_count_after_create(
        self, service: WebSocketTokenService
    ) -> None:
        """active_token_count reflects number of valid tokens."""
        assert await service.active_token_count() == 0

        await service.create_token("admin")
        assert await service.active_token_count() == 1

        await service.create_token("monitor")
        assert await service.active_token_count() == 2

    @pytest.mark.asyncio
    async def test_active_token_count_excludes_expired(
        self, service: WebSocketTokenService
    ) -> None:
        """active_token_count excludes expired tokens."""
        token1 = await service.create_token("admin")
        await service.create_token("monitor")

        # Expire one
        service._tokens[token1.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        # Count triggers cleanup
        assert await service.active_token_count() == 1

    @pytest.mark.asyncio
    async def test_create_triggers_cleanup(
        self, service: WebSocketTokenService
    ) -> None:
        """Creating a new token triggers cleanup of expired tokens."""
        token1 = await service.create_token("admin")

        # Expire the first token
        service._tokens[token1.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        # Create new token - should trigger cleanup
        await service.create_token("monitor")

        # Expired token should be gone
        assert token1.token not in service._tokens

    @pytest.mark.asyncio
    async def test_token_length_is_reasonable(
        self, service: WebSocketTokenService
    ) -> None:
        """Generated tokens have reasonable length for URL safety."""
        token = await service.create_token("admin")

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

    @pytest.mark.asyncio
    async def test_singleton_persists_tokens(self) -> None:
        """Tokens created via singleton persist across calls."""
        service = get_ws_token_service()
        token = await service.create_token("admin")

        # Get service again
        service2 = get_ws_token_service()
        role = await service2.validate_token(token.token)

        assert role == "admin"


class TestTokenExpiration:
    """Tests for token expiration edge cases."""

    @pytest.mark.asyncio
    async def test_token_valid_just_before_expiry(self) -> None:
        """Token is valid right before expiration."""
        service = WebSocketTokenService(token_ttl_seconds=300)
        stored = await service.create_token("admin")

        # Set expiry to 1 second from now
        service._tokens[stored.token].expires_at = datetime.now(UTC) + timedelta(
            seconds=1
        )

        role = await service.validate_token(stored.token)
        assert role == "admin"

    @pytest.mark.asyncio
    async def test_token_invalid_just_after_expiry(self) -> None:
        """Token is invalid right after expiration."""
        service = WebSocketTokenService(token_ttl_seconds=300)
        stored = await service.create_token("admin")

        # Set expiry to 1 microsecond ago
        service._tokens[stored.token].expires_at = datetime.now(UTC) - timedelta(
            microseconds=1
        )

        role = await service.validate_token(stored.token)
        assert role is None

    @pytest.mark.asyncio
    async def test_multiple_tokens_same_role(self) -> None:
        """Multiple tokens can be created for the same role."""
        service = WebSocketTokenService()

        token1 = await service.create_token("admin")
        token2 = await service.create_token("admin")

        assert token1.token != token2.token
        assert await service.validate_token(token1.token) == "admin"
        assert await service.validate_token(token2.token) == "admin"

    @pytest.mark.asyncio
    async def test_token_reuse_after_expiry_fails(self) -> None:
        """Cannot reuse a token after it expires."""
        service = WebSocketTokenService()
        stored = await service.create_token("admin")

        # Validate once - should work
        assert await service.validate_token(stored.token) == "admin"

        # Expire the token
        service._tokens[stored.token].expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )

        # Validate again - should fail
        assert await service.validate_token(stored.token) is None


class TestTokenEviction:
    """Tests for token eviction when max limit is reached."""

    @pytest.mark.asyncio
    async def test_evicts_oldest_when_over_limit(self) -> None:
        """Service evicts oldest tokens when max limit is reached."""
        service = WebSocketTokenService(max_tokens=3)

        # Create 3 tokens (at limit)
        token1 = await service.create_token("admin")
        token2 = await service.create_token("admin")
        token3 = await service.create_token("admin")

        assert len(service._tokens) == 3

        # Create 4th token - should evict token1
        token4 = await service.create_token("admin")

        assert len(service._tokens) == 3
        assert token1.token not in service._tokens  # Oldest evicted
        assert token2.token in service._tokens
        assert token3.token in service._tokens
        assert token4.token in service._tokens

    @pytest.mark.asyncio
    async def test_max_token_count_constant(self) -> None:
        """MAX_TOKEN_COUNT constant is defined."""
        assert MAX_TOKEN_COUNT == 10000


class TestConcurrency:
    """Tests for concurrent access to token service."""

    @pytest.mark.asyncio
    async def test_concurrent_create_tokens(self) -> None:
        """Concurrent token creation is thread-safe (AC: Review item)."""
        service = WebSocketTokenService()

        # Create 100 tokens concurrently
        async def create_token(role: str) -> str:
            stored = await service.create_token(role)
            return stored.token

        tasks = [create_token("admin") for _ in range(100)]
        tokens = await asyncio.gather(*tasks)

        # All tokens should be unique
        assert len(set(tokens)) == 100

        # All should be valid
        for token in tokens:
            assert await service.validate_token(token) == "admin"

    @pytest.mark.asyncio
    async def test_concurrent_validate_tokens(self) -> None:
        """Concurrent token validation is thread-safe."""
        service = WebSocketTokenService()
        stored = await service.create_token("admin")

        # Validate same token 100 times concurrently
        async def validate() -> str | None:
            return await service.validate_token(stored.token)

        tasks = [validate() for _ in range(100)]
        results = await asyncio.gather(*tasks)

        # All should return "admin"
        assert all(r == "admin" for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_create_and_validate(self) -> None:
        """Concurrent creation and validation is thread-safe."""
        service = WebSocketTokenService()

        # First create a token
        stored = await service.create_token("admin")

        async def create_and_validate() -> tuple[str, str | None]:
            new_token = await service.create_token("monitor")
            # Also validate the existing token
            role = await service.validate_token(stored.token)
            return new_token.token, role

        tasks = [create_and_validate() for _ in range(50)]
        results = await asyncio.gather(*tasks)

        # All validations should succeed
        for _, role in results:
            assert role == "admin"

        # All new tokens should be unique
        new_tokens = [t for t, _ in results]
        assert len(set(new_tokens)) == 50
