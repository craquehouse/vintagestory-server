"""WebSocket token service for secure authentication.

Story 9.1: Secure WebSocket Authentication

This service manages short-lived tokens for WebSocket authentication.
Tokens are stored in memory (not persisted) and have a 5-minute TTL
to limit exposure window if intercepted.

Key design decisions:
- In-memory storage (not database) for ephemeral tokens
- Token generation uses cryptographically secure random bytes
- Cleanup of expired tokens on each create operation
- Role is embedded in token for authorization at connection time
- Thread-safe operations via asyncio.Lock for concurrent access
- Size limit to prevent unbounded memory growth
"""

from __future__ import annotations

import secrets
from asyncio import Lock
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger()

# Default token TTL: 5 minutes (300 seconds)
DEFAULT_TOKEN_TTL_SECONDS = 300

# Maximum number of tokens to store (prevents memory exhaustion)
MAX_TOKEN_COUNT = 10000


@dataclass
class StoredToken:
    """Represents a stored WebSocket authentication token.

    Attributes:
        token: The token string (URL-safe base64)
        role: User role ('admin' or 'monitor')
        expires_at: When the token expires
        created_at: When the token was created
    """

    token: str
    role: str
    expires_at: datetime
    created_at: datetime


class WebSocketTokenService:
    """Manages WebSocket authentication tokens.

    This service creates and validates short-lived tokens that can be
    used to authenticate WebSocket connections. Tokens replace the need
    to pass API keys in WebSocket URLs, improving security.

    All public methods are async and use asyncio.Lock for thread-safety
    in concurrent environments. The service also enforces a maximum token
    count to prevent unbounded memory growth.

    Attributes:
        _tokens: In-memory storage mapping token strings to StoredToken instances.
        _token_ttl: Token time-to-live in seconds.
        _lock: Asyncio lock for thread-safe operations.
        _max_tokens: Maximum number of tokens allowed.

    Example:
        >>> service = WebSocketTokenService()
        >>> stored = await service.create_token("admin")
        >>> role = await service.validate_token(stored.token)
        >>> assert role == "admin"
    """

    def __init__(
        self,
        token_ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
        max_tokens: int = MAX_TOKEN_COUNT,
    ) -> None:
        """Initialize the token service.

        Args:
            token_ttl_seconds: How long tokens remain valid (default: 300 = 5 minutes).
            max_tokens: Maximum tokens to store (default: 10000).
        """
        self._tokens: dict[str, StoredToken] = {}
        self._token_ttl = token_ttl_seconds
        self._max_tokens = max_tokens
        self._lock = Lock()

    async def create_token(self, role: str) -> StoredToken:
        """Create a new WebSocket authentication token.

        Generates a cryptographically secure token string, stores it with
        the associated role, and schedules cleanup of expired tokens.

        Thread-safe via asyncio.Lock.

        Args:
            role: The user role to associate with the token ('admin' or 'monitor').

        Returns:
            StoredToken with token string, role, and expiration info.
        """
        async with self._lock:
            # Generate cryptographically secure token (32 bytes = 43 chars URL-safe base64)
            token = secrets.token_urlsafe(32)
            now = datetime.now(UTC)

            stored = StoredToken(
                token=token,
                role=role,
                expires_at=now + timedelta(seconds=self._token_ttl),
                created_at=now,
            )

            self._tokens[token] = stored

            # Cleanup expired tokens opportunistically
            self._cleanup_expired_unlocked()

            # Evict oldest tokens if over limit (after cleanup)
            self._evict_oldest_unlocked()

            logger.debug(
                "ws_token_created",
                role=role,
                expires_in_seconds=self._token_ttl,
                active_tokens=len(self._tokens),
            )

            return stored

    async def validate_token(self, token: str) -> str | None:
        """Validate a WebSocket token and return the associated role.

        Checks if the token exists and hasn't expired. If expired, the
        token is removed from storage.

        Thread-safe via asyncio.Lock.

        Args:
            token: The token string to validate.

        Returns:
            The role string ('admin' or 'monitor') if valid, None otherwise.
        """
        async with self._lock:
            stored = self._tokens.get(token)

            if stored is None:
                logger.debug("ws_token_not_found")
                return None

            if datetime.now(UTC) > stored.expires_at:
                # Token expired - remove it
                del self._tokens[token]
                logger.debug("ws_token_expired", role=stored.role)
                return None

            logger.debug("ws_token_validated", role=stored.role)
            return stored.role

    def _cleanup_expired_unlocked(self) -> None:
        """Remove all expired tokens from storage.

        Called opportunistically during token creation to prevent
        unbounded memory growth.

        Note: Must be called while holding self._lock.
        """
        now = datetime.now(UTC)
        expired = [t for t, s in self._tokens.items() if now > s.expires_at]

        for t in expired:
            del self._tokens[t]

        if expired:
            logger.debug("ws_tokens_expired_cleaned", count=len(expired))

    def _evict_oldest_unlocked(self) -> None:
        """Evict oldest tokens if over the maximum limit.

        Removes tokens in creation order (oldest first) until under limit.

        Note: Must be called while holding self._lock.
        """
        if len(self._tokens) <= self._max_tokens:
            return

        # Sort by creation time and remove oldest
        sorted_tokens = sorted(
            self._tokens.items(),
            key=lambda x: x[1].created_at,
        )
        tokens_to_remove = len(self._tokens) - self._max_tokens

        for token_str, _ in sorted_tokens[:tokens_to_remove]:
            del self._tokens[token_str]

        logger.warning(
            "ws_tokens_evicted",
            count=tokens_to_remove,
            reason="max_token_limit_reached",
        )

    async def active_token_count(self) -> int:
        """Return the number of active (non-expired) tokens.

        Performs cleanup before counting to ensure accuracy.
        Thread-safe via asyncio.Lock.

        Returns:
            Number of valid tokens currently stored.
        """
        async with self._lock:
            self._cleanup_expired_unlocked()
            return len(self._tokens)


# Singleton instance for dependency injection
_ws_token_service: WebSocketTokenService | None = None


def get_ws_token_service() -> WebSocketTokenService:
    """Get the singleton WebSocketTokenService instance.

    Creates the service on first call. Used as a FastAPI dependency.

    Returns:
        The WebSocketTokenService singleton.
    """
    global _ws_token_service
    if _ws_token_service is None:
        _ws_token_service = WebSocketTokenService()
    return _ws_token_service


def reset_ws_token_service() -> None:
    """Reset the singleton for testing.

    This should only be called in tests to ensure clean state.
    """
    global _ws_token_service
    _ws_token_service = None
