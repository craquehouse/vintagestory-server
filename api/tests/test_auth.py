"""Tests for API key authentication middleware."""

# pyright: reportUnusedFunction=false
# Note: Functions decorated with @app.get/@app.post inside fixtures are registered
# with FastAPI but not directly called, so pyright incorrectly flags them as unused.

from collections.abc import Generator

import pytest
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY  # type: ignore[import-not-found]
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import CurrentUser, UserRole, get_settings


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


class TestGetClientIp:
    """Tests for get_client_ip IP extraction logic."""

    def test_x_forwarded_for_header(self, test_app: FastAPI) -> None:
        """Extract client IP from X-Forwarded-For header (leftmost IP)."""
        from vintagestory_api.middleware.auth import get_client_ip

        client = TestClient(test_app)

        @test_app.get("/test-ip")
        async def test_ip_endpoint(request: Request) -> dict[str, str]:
            return {"ip": get_client_ip(request)}

        response = client.get(
            "/test-ip",
            headers={"X-Forwarded-For": "203.0.113.1, 198.51.100.1, 192.0.2.1"},
        )

        assert response.status_code == 200
        assert response.json() == {"ip": "203.0.113.1"}

    def test_x_forwarded_for_single_ip(self, test_app: FastAPI) -> None:
        """Extract client IP from X-Forwarded-For header with single IP."""
        from vintagestory_api.middleware.auth import get_client_ip

        client = TestClient(test_app)

        @test_app.get("/test-ip-single")
        async def test_ip_endpoint_single(request: Request) -> dict[str, str]:
            return {"ip": get_client_ip(request)}

        response = client.get(
            "/test-ip-single",
            headers={"X-Forwarded-For": "198.51.100.50"},
        )

        assert response.status_code == 200
        assert response.json() == {"ip": "198.51.100.50"}

    def test_x_forwarded_for_with_spaces(self, test_app: FastAPI) -> None:
        """Extract client IP from X-Forwarded-For header and strip whitespace."""
        from vintagestory_api.middleware.auth import get_client_ip

        client = TestClient(test_app)

        @test_app.get("/test-ip-spaces")
        async def test_ip_endpoint_spaces(request: Request) -> dict[str, str]:
            return {"ip": get_client_ip(request)}

        response = client.get(
            "/test-ip-spaces",
            headers={"X-Forwarded-For": " 192.0.2.100 , 198.51.100.1"},
        )

        assert response.status_code == 200
        assert response.json() == {"ip": "192.0.2.100"}

    def test_x_real_ip_header(self, test_app: FastAPI) -> None:
        """Extract client IP from X-Real-IP header when no X-Forwarded-For."""
        from vintagestory_api.middleware.auth import get_client_ip

        client = TestClient(test_app)

        @test_app.get("/test-ip2")
        async def test_ip_endpoint2(request: Request) -> dict[str, str]:
            return {"ip": get_client_ip(request)}

        response = client.get(
            "/test-ip2",
            headers={"X-Real-IP": "203.0.113.42"},
        )

        assert response.status_code == 200
        assert response.json() == {"ip": "203.0.113.42"}

    def test_fallback_to_direct_connection(self, test_app: FastAPI) -> None:
        """Fallback to direct connection IP when no proxy headers present."""
        from vintagestory_api.middleware.auth import get_client_ip

        client = TestClient(test_app)

        @test_app.get("/test-ip3")
        async def test_ip_endpoint3(request: Request) -> dict[str, str]:
            return {"ip": get_client_ip(request)}

        response = client.get("/test-ip3")

        assert response.status_code == 200
        # TestClient uses "testclient" as the default host
        assert response.json()["ip"] == "testclient"

    def test_x_forwarded_for_takes_precedence_over_x_real_ip(self, test_app: FastAPI) -> None:
        """X-Forwarded-For takes priority when both headers are present."""
        from vintagestory_api.middleware.auth import get_client_ip

        client = TestClient(test_app)

        @test_app.get("/test-ip-precedence")
        async def test_ip_endpoint_precedence(request: Request) -> dict[str, str]:
            return {"ip": get_client_ip(request)}

        response = client.get(
            "/test-ip-precedence",
            headers={
                "X-Forwarded-For": "10.0.0.1, 10.0.0.2",
                "X-Real-IP": "10.0.0.99",
            },
        )

        assert response.status_code == 200
        # Should use X-Forwarded-For, not X-Real-IP
        assert response.json() == {"ip": "10.0.0.1"}


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
