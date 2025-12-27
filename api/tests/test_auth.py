"""Tests for API key authentication middleware."""

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import CurrentUser, UserRole, get_settings

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
def test_app(test_settings: Settings) -> FastAPI:
    """Create a test FastAPI app with auth-protected endpoint."""
    app = FastAPI()

    # Override settings dependency
    def override_get_settings() -> Settings:
        return test_settings

    app.dependency_overrides[get_settings] = override_get_settings

    @app.get("/protected")
    async def protected_endpoint(current_user: CurrentUser) -> dict[str, str]:
        """Test endpoint that requires authentication."""
        return {"role": current_user}

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create test client for the test app."""
    return TestClient(test_app)


class TestAdminKeyAuthentication:
    """Tests for Admin API key authentication (AC: 1)."""

    def test_valid_admin_key_returns_admin_role(self, client: TestClient) -> None:
        """Given a valid Admin API key, authentication succeeds with Admin role."""
        response = client.get(
            "/protected",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        assert response.json() == {"role": UserRole.ADMIN}

    def test_admin_key_is_case_sensitive(self, client: TestClient) -> None:
        """API keys are case-sensitive."""
        response = client.get(
            "/protected",
            headers={"X-API-Key": TEST_ADMIN_KEY.upper()},
        )

        assert response.status_code == 401


class TestMonitorKeyAuthentication:
    """Tests for Monitor API key authentication (AC: 2)."""

    def test_valid_monitor_key_returns_monitor_role(self, client: TestClient) -> None:
        """Given a valid Monitor API key, authentication succeeds with Monitor role."""
        response = client.get(
            "/protected",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200
        assert response.json() == {"role": UserRole.MONITOR}

    def test_monitor_key_optional(self, test_settings: Settings) -> None:
        """Monitor key is optional in settings."""
        settings_no_monitor = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=None,
        )

        app = FastAPI()

        def override_settings() -> Settings:
            return settings_no_monitor

        app.dependency_overrides[get_settings] = override_settings

        @app.get("/protected")
        async def protected(current_user: CurrentUser) -> dict[str, str]:
            return {"role": current_user}

        client = TestClient(app)

        # Admin should still work
        response = client.get(
            "/protected",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )
        assert response.status_code == 200
        assert response.json() == {"role": UserRole.ADMIN}

        # Monitor key should fail (not configured)
        response = client.get(
            "/protected",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )
        assert response.status_code == 401


class TestMissingApiKey:
    """Tests for missing API key handling (AC: 3)."""

    def test_missing_api_key_returns_401(self, client: TestClient) -> None:
        """Request without API key returns 401 Unauthorized."""
        response = client.get("/protected")

        assert response.status_code == 401

    def test_missing_api_key_returns_error_envelope(self, client: TestClient) -> None:
        """401 response uses standard error format with UNAUTHORIZED code."""
        response = client.get("/protected")

        error_detail = response.json()["detail"]
        assert error_detail["code"] == "UNAUTHORIZED"
        assert error_detail["message"] == "API key required"

    def test_empty_api_key_returns_401(self, client: TestClient) -> None:
        """Request with empty string API key returns 401 with 'API key required'."""
        response = client.get(
            "/protected",
            headers={"X-API-Key": ""},
        )

        assert response.status_code == 401
        error_detail = response.json()["detail"]
        assert error_detail["code"] == "UNAUTHORIZED"
        assert error_detail["message"] == "API key required"


class TestInvalidApiKey:
    """Tests for invalid API key handling (AC: 4)."""

    def test_invalid_api_key_returns_401(self, client: TestClient) -> None:
        """Request with invalid API key returns 401 Unauthorized."""
        response = client.get(
            "/protected",
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 401

    def test_invalid_api_key_returns_error_envelope(self, client: TestClient) -> None:
        """401 response for invalid key uses standard error format."""
        response = client.get(
            "/protected",
            headers={"X-API-Key": "invalid-key"},
        )

        error_detail = response.json()["detail"]
        assert error_detail["code"] == "UNAUTHORIZED"
        assert error_detail["message"] == "Invalid API key"


class TestAuthLogging:
    """Tests for authentication logging (AC: 4, 5 - NFR4, NFR7)."""

    def test_failed_auth_logs_without_key_value(
        self, client: TestClient, capfd: pytest.CaptureFixture[str]
    ) -> None:
        """Failed auth logs request context but NEVER the API key value."""
        invalid_key = "super-secret-invalid-key"

        # Make request with invalid key
        client.get(
            "/protected",
            headers={"X-API-Key": invalid_key},
        )

        # Capture log output
        captured = capfd.readouterr()
        log_output = captured.out + captured.err

        # Key value should NOT appear in logs
        assert invalid_key not in log_output

        # Note: We can't easily verify log content in unit tests without
        # more infrastructure. Integration tests would verify this more thoroughly.


class TestUserRoleConstants:
    """Tests for UserRole constants."""

    def test_admin_role_value(self) -> None:
        """Admin role has expected string value."""
        assert UserRole.ADMIN == "admin"

    def test_monitor_role_value(self) -> None:
        """Monitor role has expected string value."""
        assert UserRole.MONITOR == "monitor"


class TestAuthMeEndpointIntegration:
    """Integration tests for GET /api/v1alpha1/auth/me endpoint.

    These tests verify the full auth flow against the actual application.
    """

    @pytest.fixture
    def integration_app(self) -> Generator[FastAPI, None, None]:
        """Create app with overridden settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
        )

        app.dependency_overrides[get_settings] = lambda: test_settings
        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_auth_me_with_admin_key(self, integration_client: TestClient) -> None:
        """GET /api/v1alpha1/auth/me returns admin role with admin key."""
        response = integration_client.get(
            "/api/v1alpha1/auth/me",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["role"] == "admin"

    def test_auth_me_with_monitor_key(self, integration_client: TestClient) -> None:
        """GET /api/v1alpha1/auth/me returns monitor role with monitor key."""
        response = integration_client.get(
            "/api/v1alpha1/auth/me",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["role"] == "monitor"

    def test_auth_me_without_key_returns_401(self, integration_client: TestClient) -> None:
        """GET /api/v1alpha1/auth/me returns 401 without API key."""
        response = integration_client.get("/api/v1alpha1/auth/me")

        assert response.status_code == 401
        error = response.json()["detail"]
        assert error["code"] == "UNAUTHORIZED"
        assert error["message"] == "API key required"

    def test_auth_me_with_invalid_key_returns_401(self, integration_client: TestClient) -> None:
        """GET /api/v1alpha1/auth/me returns 401 with invalid API key."""
        response = integration_client.get(
            "/api/v1alpha1/auth/me",
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 401
        error = response.json()["detail"]
        assert error["code"] == "UNAUTHORIZED"
        assert error["message"] == "Invalid API key"

    def test_auth_me_response_follows_envelope_format(self, integration_client: TestClient) -> None:
        """GET /api/v1alpha1/auth/me follows standard API response envelope."""
        response = integration_client.get(
            "/api/v1alpha1/auth/me",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"
        assert data.get("error") is None
