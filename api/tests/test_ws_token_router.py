"""Tests for WebSocket token endpoint.

Story 9.1: Secure WebSocket Authentication

Tests cover:
- Token request with valid Admin API key (AC: 1)
- Token request with valid Monitor API key (AC: 6)
- Token request without API key (401)
- Token request with invalid API key (401)
- Token response format and expiry
"""

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.routers import ws_token
from vintagestory_api.services.ws_token_service import (
    WebSocketTokenService,
    get_ws_token_service,
    reset_ws_token_service,
)


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Helper to run async code in sync test context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# Test API keys
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with known API keys."""
    return Settings(
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
    )


@pytest.fixture
def token_service() -> WebSocketTokenService:
    """Create a fresh token service for each test."""
    # Reset singleton to ensure clean state
    reset_ws_token_service()
    return get_ws_token_service()


@pytest.fixture
def app(test_settings: Settings, token_service: WebSocketTokenService) -> FastAPI:
    """Create test FastAPI app with ws-token router."""
    from vintagestory_api.middleware.auth import get_current_user

    app = FastAPI()

    # Override settings dependency
    app.dependency_overrides[get_settings] = lambda: test_settings

    # Override token service dependency
    app.dependency_overrides[get_ws_token_service] = lambda: token_service

    # Include router with auth dependency like in main.py
    from fastapi import APIRouter, Depends

    api_v1 = APIRouter(prefix="/api/v1alpha1", dependencies=[Depends(get_current_user)])
    api_v1.include_router(ws_token.router)
    app.include_router(api_v1)

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestWebSocketTokenEndpointWithAdminKey:
    """Tests for ws-token endpoint with Admin API key (AC: 1)."""

    def test_request_token_with_admin_key_returns_200(self, client: TestClient) -> None:
        """Given valid Admin API key, token request returns 200."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200

    def test_request_token_returns_ok_status(self, client: TestClient) -> None:
        """Token response has status 'ok'."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert data["status"] == "ok"

    def test_request_token_returns_token_string(self, client: TestClient) -> None:
        """Token response includes non-empty token string."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "token" in data["data"]
        assert isinstance(data["data"]["token"], str)
        assert len(data["data"]["token"]) > 0

    def test_request_token_returns_expires_at(self, client: TestClient) -> None:
        """Token response includes expires_at ISO timestamp."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "expires_at" in data["data"]

        # Verify it's a valid ISO timestamp
        expires_at = data["data"]["expires_at"]
        # Should be parseable (ISO 8601 format)
        datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

    def test_request_token_returns_expires_in_seconds(self, client: TestClient) -> None:
        """Token response includes expires_in_seconds = 300."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "expires_in_seconds" in data["data"]
        assert data["data"]["expires_in_seconds"] == 300

    def test_token_expires_in_future(self, client: TestClient) -> None:
        """Token expires_at is in the future."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        expires_at_str = data["data"]["expires_at"]
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))

        assert expires_at > datetime.now(UTC)

    def test_token_can_be_validated(
        self, client: TestClient, token_service: WebSocketTokenService
    ) -> None:
        """Token returned by endpoint can be validated via service."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        token = response.json()["data"]["token"]
        role = _run_async(token_service.validate_token(token))

        assert role == "admin"


class TestWebSocketTokenEndpointWithMonitorKey:
    """Tests for ws-token endpoint with Monitor API key (AC: 6)."""

    def test_request_token_with_monitor_key_returns_200(
        self, client: TestClient
    ) -> None:
        """Given valid Monitor API key, token request returns 200."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200

    def test_monitor_token_preserves_role(
        self, client: TestClient, token_service: WebSocketTokenService
    ) -> None:
        """Token requested with Monitor key preserves monitor role."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        token = response.json()["data"]["token"]
        role = _run_async(token_service.validate_token(token))

        assert role == "monitor"

    def test_monitor_token_has_same_expiry(self, client: TestClient) -> None:
        """Monitor tokens have same 5-minute expiry as admin tokens."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        data = response.json()
        assert data["data"]["expires_in_seconds"] == 300


class TestWebSocketTokenEndpointAuthErrors:
    """Tests for ws-token endpoint authentication errors."""

    def test_request_without_api_key_returns_401(self, client: TestClient) -> None:
        """Token request without API key returns 401."""
        response = client.post("/api/v1alpha1/auth/ws-token")

        assert response.status_code == 401

    def test_request_without_api_key_returns_error_detail(
        self, client: TestClient
    ) -> None:
        """Token request without API key returns error detail."""
        response = client.post("/api/v1alpha1/auth/ws-token")

        data = response.json()
        assert "detail" in data
        assert data["detail"]["code"] == "UNAUTHORIZED"
        assert "API key" in data["detail"]["message"]

    def test_request_with_invalid_api_key_returns_401(
        self, client: TestClient
    ) -> None:
        """Token request with invalid API key returns 401."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 401

    def test_request_with_empty_api_key_returns_401(self, client: TestClient) -> None:
        """Token request with empty API key returns 401."""
        response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": ""},
        )

        assert response.status_code == 401


class TestWebSocketTokenUniqueness:
    """Tests for token uniqueness."""

    def test_multiple_requests_return_unique_tokens(self, client: TestClient) -> None:
        """Each token request returns a unique token."""
        tokens = set()

        for _ in range(5):
            response = client.post(
                "/api/v1alpha1/auth/ws-token",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )
            token = response.json()["data"]["token"]
            tokens.add(token)

        assert len(tokens) == 5

    def test_admin_and_monitor_get_different_tokens(self, client: TestClient) -> None:
        """Admin and Monitor users get different tokens."""
        admin_response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )
        monitor_response = client.post(
            "/api/v1alpha1/auth/ws-token",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        admin_token = admin_response.json()["data"]["token"]
        monitor_token = monitor_response.json()["data"]["token"]

        assert admin_token != monitor_token
