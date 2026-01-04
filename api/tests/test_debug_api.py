"""Tests for debug API endpoints (Story 9.4 / FR48).

Verifies the /api/v1alpha1/debug/* endpoints for runtime debug toggle.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import vintagestory_api.config as config_module
from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings

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
def override_settings(test_settings: Settings) -> Generator[None]:
    """Override app settings dependency with test settings."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def admin_client(override_settings: None) -> TestClient:
    """Create a test client with admin authentication."""
    return TestClient(app, headers={"X-API-Key": TEST_ADMIN_KEY})


@pytest.fixture
def monitor_client(override_settings: None) -> TestClient:
    """Create a test client with monitor authentication."""
    return TestClient(app, headers={"X-API-Key": TEST_MONITOR_KEY})


@pytest.fixture
def no_auth_client(override_settings: None) -> TestClient:
    """Create a test client without authentication."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_debug_state():
    """Reset debug state before and after each test."""
    # Save original state
    original_enabled = config_module._debug_enabled  # pyright: ignore[reportPrivateUsage]
    original_initialized = config_module._debug_initialized  # pyright: ignore[reportPrivateUsage]

    # Reset to known state for tests
    config_module._debug_enabled = False  # pyright: ignore[reportPrivateUsage]
    config_module._debug_initialized = True  # pyright: ignore[reportPrivateUsage]

    yield

    # Restore original state
    config_module._debug_enabled = original_enabled  # pyright: ignore[reportPrivateUsage]
    config_module._debug_initialized = original_initialized  # pyright: ignore[reportPrivateUsage]


class TestDebugStatusEndpoint:
    """Tests for GET /api/v1alpha1/debug endpoint."""

    def test_get_debug_status_admin(self, admin_client: TestClient) -> None:
        """Admin can get debug status.

        Given an authenticated admin user
        When GET /api/v1alpha1/debug is called
        Then debug status is returned
        """
        response = admin_client.get("/api/v1alpha1/debug")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "debug_enabled" in data["data"]
        assert data["data"]["debug_enabled"] is False  # Default state

    def test_get_debug_status_monitor_forbidden(self, monitor_client: TestClient) -> None:
        """Monitor users cannot get debug status.

        Given an authenticated monitor user
        When GET /api/v1alpha1/debug is called
        Then 403 Forbidden is returned
        """
        response = monitor_client.get("/api/v1alpha1/debug")
        assert response.status_code == 403

    def test_get_debug_status_unauthenticated(self, no_auth_client: TestClient) -> None:
        """Unauthenticated users cannot get debug status.

        Given no authentication
        When GET /api/v1alpha1/debug is called
        Then 401 Unauthorized is returned
        """
        response = no_auth_client.get("/api/v1alpha1/debug")
        assert response.status_code == 401


class TestDebugEnableEndpoint:
    """Tests for POST /api/v1alpha1/debug/enable endpoint."""

    def test_enable_debug_admin(self, admin_client: TestClient) -> None:
        """Admin can enable debug logging.

        Given an authenticated admin user
        And debug logging is disabled
        When POST /api/v1alpha1/debug/enable is called
        Then debug logging is enabled
        And response indicates change occurred
        """
        response = admin_client.post("/api/v1alpha1/debug/enable")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["debug_enabled"] is True
        assert data["data"]["changed"] is True

        # Verify state was actually changed
        assert config_module._debug_enabled is True  # pyright: ignore[reportPrivateUsage]

    def test_enable_debug_already_enabled(self, admin_client: TestClient) -> None:
        """Enable debug when already enabled returns changed=False.

        Given debug logging is already enabled
        When POST /api/v1alpha1/debug/enable is called
        Then response indicates no change occurred
        """
        config_module._debug_enabled = True  # pyright: ignore[reportPrivateUsage]

        response = admin_client.post("/api/v1alpha1/debug/enable")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["debug_enabled"] is True
        assert data["data"]["changed"] is False

    def test_enable_debug_monitor_forbidden(self, monitor_client: TestClient) -> None:
        """Monitor users cannot enable debug logging.

        Given an authenticated monitor user
        When POST /api/v1alpha1/debug/enable is called
        Then 403 Forbidden is returned
        """
        response = monitor_client.post("/api/v1alpha1/debug/enable")
        assert response.status_code == 403

    def test_enable_debug_unauthenticated(self, no_auth_client: TestClient) -> None:
        """Unauthenticated users cannot enable debug logging.

        Given no authentication
        When POST /api/v1alpha1/debug/enable is called
        Then 401 Unauthorized is returned
        """
        response = no_auth_client.post("/api/v1alpha1/debug/enable")
        assert response.status_code == 401


class TestDebugDisableEndpoint:
    """Tests for POST /api/v1alpha1/debug/disable endpoint."""

    def test_disable_debug_admin(self, admin_client: TestClient) -> None:
        """Admin can disable debug logging.

        Given an authenticated admin user
        And debug logging is enabled
        When POST /api/v1alpha1/debug/disable is called
        Then debug logging is disabled
        And response indicates change occurred
        """
        config_module._debug_enabled = True  # pyright: ignore[reportPrivateUsage]

        response = admin_client.post("/api/v1alpha1/debug/disable")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["debug_enabled"] is False
        assert data["data"]["changed"] is True

        # Verify state was actually changed
        assert config_module._debug_enabled is False  # pyright: ignore[reportPrivateUsage]

    def test_disable_debug_already_disabled(self, admin_client: TestClient) -> None:
        """Disable debug when already disabled returns changed=False.

        Given debug logging is already disabled
        When POST /api/v1alpha1/debug/disable is called
        Then response indicates no change occurred
        """
        response = admin_client.post("/api/v1alpha1/debug/disable")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["debug_enabled"] is False
        assert data["data"]["changed"] is False

    def test_disable_debug_monitor_forbidden(self, monitor_client: TestClient) -> None:
        """Monitor users cannot disable debug logging.

        Given an authenticated monitor user
        When POST /api/v1alpha1/debug/disable is called
        Then 403 Forbidden is returned
        """
        response = monitor_client.post("/api/v1alpha1/debug/disable")
        assert response.status_code == 403

    def test_disable_debug_unauthenticated(self, no_auth_client: TestClient) -> None:
        """Unauthenticated users cannot disable debug logging.

        Given no authentication
        When POST /api/v1alpha1/debug/disable is called
        Then 401 Unauthorized is returned
        """
        response = no_auth_client.post("/api/v1alpha1/debug/disable")
        assert response.status_code == 401


class TestDebugToggleIntegration:
    """Integration tests for debug toggle workflow."""

    def test_full_toggle_cycle(self, admin_client: TestClient) -> None:
        """Test complete enable/disable cycle.

        Given debug logging is initially disabled
        When admin enables then disables debug logging
        Then state transitions correctly through each step
        """
        # Initial state: disabled
        response = admin_client.get("/api/v1alpha1/debug")
        assert response.json()["data"]["debug_enabled"] is False

        # Enable
        response = admin_client.post("/api/v1alpha1/debug/enable")
        assert response.json()["data"]["debug_enabled"] is True
        assert response.json()["data"]["changed"] is True

        # Verify enabled
        response = admin_client.get("/api/v1alpha1/debug")
        assert response.json()["data"]["debug_enabled"] is True

        # Disable
        response = admin_client.post("/api/v1alpha1/debug/disable")
        assert response.json()["data"]["debug_enabled"] is False
        assert response.json()["data"]["changed"] is True

        # Verify disabled
        response = admin_client.get("/api/v1alpha1/debug")
        assert response.json()["data"]["debug_enabled"] is False
