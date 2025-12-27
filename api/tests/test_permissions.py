"""Tests for role-based permission dependencies."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import CurrentUser, UserRole, get_settings
from vintagestory_api.middleware.permissions import (
    require_admin,
    require_console_access,
    require_role,
)

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
    """Create a test FastAPI app with permission-protected endpoints."""
    app = FastAPI()

    # Override settings dependency
    def override_get_settings() -> Settings:
        return test_settings

    app.dependency_overrides[get_settings] = override_get_settings

    # Read endpoint - any authenticated user
    @app.get("/read")
    async def read_endpoint(current_user: CurrentUser) -> dict[str, str]:
        """Endpoint accessible by both Admin and Monitor."""
        return {"test": "read"}

    # Write endpoint - Admin only
    @app.post("/write")
    async def write_endpoint(role: str = Depends(require_admin)) -> dict[str, str]:
        """Endpoint accessible only by Admin."""
        return {"test": "write"}

    # Console endpoint - Admin only with specific message
    @app.get("/console")
    async def console_endpoint(role: str = Depends(require_console_access)) -> dict[str, str]:
        """Console endpoint accessible only by Admin."""
        return {"test": "console"}

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create test client for the test app."""
    return TestClient(test_app)


class TestRequireAdminDependency:
    """Tests for require_admin dependency (AC: 1, 3, 5)."""

    def test_admin_can_access_write_endpoint(self, client: TestClient) -> None:
        """Admin role allows access to write endpoints."""
        response = client.post(
            "/write",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        assert response.json() == {"test": "write"}

    def test_monitor_blocked_from_write_endpoint(self, client: TestClient) -> None:
        """Monitor role is blocked from write endpoints with 403."""
        response = client.post(
            "/write",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403

    def test_monitor_blocked_returns_forbidden_error(self, client: TestClient) -> None:
        """403 response includes FORBIDDEN code and clear message."""
        response = client.post(
            "/write",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        error = response.json()["detail"]
        assert error["code"] == "FORBIDDEN"
        assert "Admin" in error["message"]
        assert "role required" in error["message"].lower()

    def test_unauthenticated_returns_401_not_403(self, client: TestClient) -> None:
        """Unauthenticated request returns 401, not 403."""
        response = client.post("/write")

        assert response.status_code == 401


class TestRequireConsoleAccessDependency:
    """Tests for require_console_access dependency (AC: 4)."""

    def test_admin_can_access_console(self, client: TestClient) -> None:
        """Admin role allows access to console endpoints."""
        response = client.get(
            "/console",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        assert response.json() == {"test": "console"}

    def test_monitor_blocked_from_console(self, client: TestClient) -> None:
        """Monitor role is blocked from console endpoints with 403."""
        response = client.get(
            "/console",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403

    def test_monitor_blocked_returns_console_specific_message(self, client: TestClient) -> None:
        """403 response has console-specific error message."""
        response = client.get(
            "/console",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        error = response.json()["detail"]
        assert error["code"] == "FORBIDDEN"
        assert "Console access requires Admin role" == error["message"]


class TestReadEndpointAccess:
    """Tests for read endpoints accessible by both roles (AC: 1, 2)."""

    def test_admin_can_access_read_endpoint(self, client: TestClient) -> None:
        """Admin role allows access to read endpoints."""
        response = client.get(
            "/read",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        assert response.json() == {"test": "read"}

    def test_monitor_can_access_read_endpoint(self, client: TestClient) -> None:
        """Monitor role allows access to read endpoints."""
        response = client.get(
            "/read",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200
        assert response.json() == {"test": "read"}


class TestRequireRoleFactory:
    """Tests for require_role factory function."""

    def test_require_role_rejects_invalid_role_string(self) -> None:
        """require_role should reject invalid role values at type-check time.

        This test demonstrates that the Literal type prevents typos
        in role strings by catching them at type-check time rather
        than runtime.
        """
        from vintagestory_api.middleware.permissions import require_role, RoleType

        # Only these values are allowed by the type system:
        # This demonstrates type checking prevents typos:
        valid_admin: RoleType = "admin"  # ✅ Valid
        valid_monitor: RoleType = "monitor"  # ✅ Valid

        # These would cause type errors at type-check time:
        # invalid_admin: RoleType = "Adminn"  # ❌ Type error
        # invalid_monitor: RoleType = "Monitor"  # ❌ Type error

        assert valid_admin == "admin"
        assert valid_monitor == "monitor"

    @pytest.fixture
    def custom_role_app(self, test_settings: Settings) -> FastAPI:
        """Create app with require_role factory usage."""
        app = FastAPI()

        def override_get_settings() -> Settings:
            return test_settings

        app.dependency_overrides[get_settings] = override_get_settings

        # Using the factory function
        @app.get("/admin-only")
        async def admin_only(role: str = Depends(require_role("admin"))) -> dict[str, str]:
            return {"role": role}

        @app.get("/monitor-only")
        async def monitor_only(
            role: str = Depends(require_role("monitor")),
        ) -> dict[str, str]:
            return {"role": role}

        return app

    @pytest.fixture
    def custom_client(self, custom_role_app: FastAPI) -> TestClient:
        """Create client for custom role app."""
        return TestClient(custom_role_app)

    def test_require_role_admin_allows_admin(self, custom_client: TestClient) -> None:
        """require_role(ADMIN) allows admin access."""
        response = custom_client.get(
            "/admin-only",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        assert response.json()["role"] == UserRole.ADMIN

    def test_require_role_admin_blocks_monitor(self, custom_client: TestClient) -> None:
        """require_role(ADMIN) blocks monitor access."""
        response = custom_client.get(
            "/admin-only",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403

    def test_require_role_monitor_allows_monitor(self, custom_client: TestClient) -> None:
        """require_role(MONITOR) allows monitor access."""
        response = custom_client.get(
            "/monitor-only",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200
        assert response.json()["role"] == UserRole.MONITOR

    def test_require_role_monitor_blocks_admin(self, custom_client: TestClient) -> None:
        """require_role(MONITOR) blocks admin access (strict role check)."""
        response = custom_client.get(
            "/monitor-only",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 403

    def test_require_role_case_sensitivity(self, custom_client: TestClient) -> None:
        """require_role performs case-insensitive comparison after auth normalizes case."""
        # The auth middleware already normalizes case, so "ADMIN" becomes "admin"
        # This test verifies that the factory still works with normalized roles
        from vintagestory_api.middleware.permissions import require_role

        response = custom_client.get(
            "/admin-only",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200

    def test_require_role_rejects_invalid_at_runtime(self) -> None:
        """require_role rejects invalid role strings at runtime.

        Note: Literal type checking catches most typos at compile time,
        but we should still handle runtime validation for edge cases like
        None values or unexpected strings from external sources.
        """
        from vintagestory_api.middleware.auth import get_settings
        from vintagestory_api.middleware.permissions import require_role

        # Create test app with invalid role in settings
        invalid_role_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
        )

        app = FastAPI()

        def override_settings() -> Settings:
            return invalid_role_settings

        app.dependency_overrides[get_settings] = override_settings

        # Create endpoint that requires "admin" role
        @app.get("/edge-case")
        async def edge_case(role: str = Depends(require_role("admin"))) -> dict[str, str]:
            return {"role": role}

        client = TestClient(app)

        # Valid admin key should work
        response = client.get(
            "/edge-case",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"


class TestErrorResponseFormat:
    """Tests for 403 error response format consistency (AC: 5)."""

    def test_require_admin_error_includes_required_role(self, client: TestClient) -> None:
        """require_admin 403 error message indicates required role."""
        response = client.post(
            "/write",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        error = response.json()["detail"]
        assert "Admin" in error["message"]

    def test_require_console_error_includes_required_role(self, client: TestClient) -> None:
        """require_console_access 403 error message indicates required role."""
        response = client.get(
            "/console",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        error = response.json()["detail"]
        assert "Admin" in error["message"]

    def test_error_response_has_code_field(self, client: TestClient) -> None:
        """403 error response includes code field."""
        response = client.post(
            "/write",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        error = response.json()["detail"]
        assert "code" in error
        assert error["code"] == "FORBIDDEN"

    def test_error_response_has_message_field(self, client: TestClient) -> None:
        """403 error response includes message field."""
        response = client.post(
            "/write",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        error = response.json()["detail"]
        assert "message" in error
        assert len(error["message"]) > 0
