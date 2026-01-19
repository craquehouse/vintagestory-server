"""Integration tests for Role-Based Access Control across API endpoints.

These tests verify the full RBAC flow against the actual application,
testing all role/endpoint combinations.
"""

from collections.abc import Generator

import pytest
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY  # type: ignore[import-not-found]
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import UserRole, get_settings


@pytest.fixture
def integration_app() -> Generator[FastAPI, None, None]:
    """Create app with overridden settings for integration testing.

    NOTE: DEBUG mode is enabled for these tests so that test_rbac
    endpoints are available. In production (DEBUG=false), these
    endpoints are hidden per DEBUG gating.
    """
    test_settings = Settings(
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        debug=True,  # Enable DEBUG mode to expose test endpoints
    )

    app.dependency_overrides[get_settings] = lambda: test_settings
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(integration_app: FastAPI) -> TestClient:
    """Create test client for integration tests."""
    return TestClient(integration_app)


class TestRBACReadEndpoint:
    """Integration tests for GET /api/v1alpha1/test/read (AC: 1, 2)."""

    def test_admin_can_access_read_endpoint(self, client: TestClient) -> None:
        """Admin role allows access to read endpoint."""
        response = client.get(
            "/api/v1alpha1/test/read",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["test"] == "read"

    def test_monitor_can_access_read_endpoint(self, client: TestClient) -> None:
        """Monitor role allows access to read endpoint."""
        response = client.get(
            "/api/v1alpha1/test/read",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["test"] == "read"

    def test_unauthenticated_blocked_from_read(self, client: TestClient) -> None:
        """Unauthenticated request to read endpoint returns 401."""
        response = client.get("/api/v1alpha1/test/read")

        assert response.status_code == 401


class TestRBACWriteEndpoint:
    """Integration tests for POST /api/v1alpha1/test/write (AC: 1, 3, 5)."""

    def test_admin_can_access_write_endpoint(self, client: TestClient) -> None:
        """Admin role allows access to write endpoint."""
        response = client.post(
            "/api/v1alpha1/test/write",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["test"] == "write"

    def test_monitor_blocked_from_write_endpoint(self, client: TestClient) -> None:
        """Monitor role is blocked from write endpoint with 403."""
        response = client.post(
            "/api/v1alpha1/test/write",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403

    def test_monitor_write_returns_forbidden_error_envelope(self, client: TestClient) -> None:
        """Monitor write attempt returns proper error envelope format."""
        response = client.post(
            "/api/v1alpha1/test/write",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        error = response.json()["detail"]
        assert error["code"] == "FORBIDDEN"
        assert "Admin" in error["message"]
        assert "role required" in error["message"].lower()

    def test_unauthenticated_blocked_from_write(self, client: TestClient) -> None:
        """Unauthenticated request to write endpoint returns 401."""
        response = client.post("/api/v1alpha1/test/write")

        assert response.status_code == 401


class TestRBACConsoleEndpoint:
    """Integration tests for GET /api/v1alpha1/test/console (AC: 4, 5)."""

    def test_admin_can_access_console_endpoint(self, client: TestClient) -> None:
        """Admin role allows access to console endpoint."""
        response = client.get(
            "/api/v1alpha1/test/console",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["test"] == "console"

    def test_monitor_blocked_from_console_endpoint(self, client: TestClient) -> None:
        """Monitor role is blocked from console endpoint with 403."""
        response = client.get(
            "/api/v1alpha1/test/console",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403

    def test_monitor_console_returns_specific_error_message(self, client: TestClient) -> None:
        """Monitor console attempt returns console-specific error message."""
        response = client.get(
            "/api/v1alpha1/test/console",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        error = response.json()["detail"]
        assert error["code"] == "FORBIDDEN"
        assert error["message"] == "Console access requires Admin role"


class TestAuthMeEndpointRBAC:
    """Integration tests for /auth/me working with both roles (AC: 1, 2)."""

    def test_auth_me_works_for_admin(self, client: TestClient) -> None:
        """GET /api/v1alpha1/auth/me works for Admin."""
        response = client.get(
            "/api/v1alpha1/auth/me",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["role"] == UserRole.ADMIN

    def test_auth_me_works_for_monitor(self, client: TestClient) -> None:
        """GET /api/v1alpha1/auth/me works for Monitor."""
        response = client.get(
            "/api/v1alpha1/auth/me",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["role"] == UserRole.MONITOR


class TestHealthEndpointsRemainPublic:
    """Integration tests confirming health endpoints remain public (AC: 1, 2)."""

    def test_healthz_endpoint_no_auth_required(self, client: TestClient) -> None:
        """GET /healthz works without authentication."""
        response = client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_readyz_endpoint_no_auth_required(self, client: TestClient) -> None:
        """GET /readyz works without authentication."""
        response = client.get("/readyz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestErrorResponseEnvelopeFormat:
    """Integration tests for error response envelope format (AC: 3, 5)."""

    def test_403_response_uses_detail_structure(self, client: TestClient) -> None:
        """403 response uses FastAPI's detail structure with code and message."""
        response = client.post(
            "/api/v1alpha1/test/write",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        json_response = response.json()
        assert "detail" in json_response
        assert "code" in json_response["detail"]
        assert "message" in json_response["detail"]

    def test_401_response_uses_detail_structure(self, client: TestClient) -> None:
        """401 response uses same detail structure for consistency."""
        response = client.get("/api/v1alpha1/test/read")

        json_response = response.json()
        assert "detail" in json_response
        assert "code" in json_response["detail"]
        assert "message" in json_response["detail"]

    def test_403_includes_required_role_in_message(self, client: TestClient) -> None:
        """403 error message clearly indicates the required role."""
        response = client.post(
            "/api/v1alpha1/test/write",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        error = response.json()["detail"]
        # Message should mention Admin as the required role
        assert "Admin" in error["message"]


class TestRoleEndpointMatrix:
    """Comprehensive test of all role/endpoint combinations.

    This verifies the complete permission matrix:
    | Role    | Read (GET) | Write (POST) | Console |
    |---------|------------|--------------|---------|
    | Admin   | 200 OK     | 200 OK       | 200 OK  |
    | Monitor | 200 OK     | 403 Forbidden| 403 Forbidden |
    | None    | 401 Unauth | 401 Unauth   | 401 Unauth |
    """

    @pytest.mark.parametrize(
        "endpoint,method,admin_expected,monitor_expected,unauth_expected",
        [
            ("/api/v1alpha1/test/read", "GET", 200, 200, 401),
            ("/api/v1alpha1/test/write", "POST", 200, 403, 401),
            ("/api/v1alpha1/test/console", "GET", 200, 403, 401),
            ("/api/v1alpha1/auth/me", "GET", 200, 200, 401),
        ],
    )
    def test_role_endpoint_permissions(
        self,
        client: TestClient,
        endpoint: str,
        method: str,
        admin_expected: int,
        monitor_expected: int,
        unauth_expected: int,
    ) -> None:
        """Verify all role/endpoint permission combinations."""
        # Admin request
        if method == "GET":
            admin_response = client.get(endpoint, headers={"X-API-Key": TEST_ADMIN_KEY})
            monitor_response = client.get(endpoint, headers={"X-API-Key": TEST_MONITOR_KEY})
            unauth_response = client.get(endpoint)
        else:
            admin_response = client.post(endpoint, headers={"X-API-Key": TEST_ADMIN_KEY})
            monitor_response = client.post(endpoint, headers={"X-API-Key": TEST_MONITOR_KEY})
            unauth_response = client.post(endpoint)

        assert admin_response.status_code == admin_expected, (
            f"Admin {method} {endpoint}: expected {admin_expected}, "
            f"got {admin_response.status_code}"
        )
        assert monitor_response.status_code == monitor_expected, (
            f"Monitor {method} {endpoint}: expected {monitor_expected}, "
            f"got {monitor_response.status_code}"
        )
        assert unauth_response.status_code == unauth_expected, (
            f"Unauthenticated {method} {endpoint}: expected {unauth_expected}, "
            f"got {unauth_response.status_code}"
        )
