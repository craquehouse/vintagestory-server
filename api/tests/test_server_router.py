"""Tests for server router endpoints (Story 13.6)."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.services.server import ServerService, get_server_service

# Test API keys
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


@pytest.fixture
def integration_app() -> Generator[FastAPI, None, None]:
    """Create app with overridden settings for integration testing."""
    test_settings = Settings(
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        debug=True,
    )

    app.dependency_overrides[get_settings] = lambda: test_settings
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(integration_app: FastAPI) -> TestClient:
    """Create test client for integration tests."""
    return TestClient(integration_app)


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def test_settings(temp_data_dir: Path) -> Settings:
    """Create Settings with temp data directory."""
    return Settings(
        data_dir=temp_data_dir,
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        debug=True,
    )


@pytest.fixture
def test_service(test_settings: Settings) -> ServerService:
    """Create a ServerService with test settings."""
    return ServerService(settings=test_settings)


def create_fake_installation(settings: Settings, version: str) -> None:
    """Helper to create a fake server installation."""
    settings.server_dir.mkdir(parents=True, exist_ok=True)
    settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
    (settings.server_dir / "VintagestoryServer.dll").touch()
    (settings.server_dir / "VintagestoryLib.dll").touch()
    version_file = settings.vsmanager_dir / "current_version"
    version_file.write_text(version)


class TestUninstallServerRouter:
    """Tests for DELETE /api/v1alpha1/server endpoint."""

    def test_uninstall_requires_admin(self, client: TestClient) -> None:
        """Monitor role cannot uninstall server."""
        response = client.delete(
            "/api/v1alpha1/server",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )
        assert response.status_code == 403

    def test_uninstall_requires_auth(self, client: TestClient) -> None:
        """Unauthenticated request returns 401."""
        response = client.delete("/api/v1alpha1/server")
        assert response.status_code == 401

    def test_uninstall_when_not_installed_returns_404(
        self,
        integration_app: FastAPI,
        test_settings: Settings,
        test_service: ServerService,
    ) -> None:
        """Cannot uninstall when no server installed."""
        # Override both settings and service dependencies
        integration_app.dependency_overrides[get_settings] = lambda: test_settings
        integration_app.dependency_overrides[get_server_service] = lambda: test_service

        client = TestClient(integration_app)
        response = client.delete(
            "/api/v1alpha1/server",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == ErrorCode.SERVER_NOT_INSTALLED

        integration_app.dependency_overrides.clear()

    def test_uninstall_when_running_returns_409(
        self,
        integration_app: FastAPI,
        test_settings: Settings,
        test_service: ServerService,
    ) -> None:
        """Cannot uninstall running server."""
        create_fake_installation(test_settings, "1.21.3")

        # Simulate running server
        mock_process = MagicMock()
        mock_process.returncode = None
        test_service._process = mock_process  # pyright: ignore[reportPrivateUsage]

        integration_app.dependency_overrides[get_settings] = lambda: test_settings
        integration_app.dependency_overrides[get_server_service] = lambda: test_service

        client = TestClient(integration_app)
        response = client.delete(
            "/api/v1alpha1/server",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == ErrorCode.SERVER_RUNNING
        assert "stopped" in data["detail"]["message"].lower()

        integration_app.dependency_overrides.clear()

    def test_uninstall_when_stopped_succeeds(
        self,
        integration_app: FastAPI,
        test_settings: Settings,
        test_service: ServerService,
    ) -> None:
        """Uninstall stopped server succeeds."""
        create_fake_installation(test_settings, "1.21.3")

        integration_app.dependency_overrides[get_settings] = lambda: test_settings
        integration_app.dependency_overrides[get_server_service] = lambda: test_service

        client = TestClient(integration_app)
        response = client.delete(
            "/api/v1alpha1/server",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "not_installed"
        assert "successfully" in data["data"]["message"].lower()

        integration_app.dependency_overrides.clear()

    def test_uninstall_preserves_serverdata(
        self,
        integration_app: FastAPI,
        test_settings: Settings,
        test_service: ServerService,
    ) -> None:
        """Uninstall preserves serverdata directory."""
        create_fake_installation(test_settings, "1.21.3")

        # Create test files in serverdata
        test_settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
        config_file = test_settings.serverdata_dir / "serverconfig.json"
        config_file.write_text('{"test": true}')

        integration_app.dependency_overrides[get_settings] = lambda: test_settings
        integration_app.dependency_overrides[get_server_service] = lambda: test_service

        client = TestClient(integration_app)
        response = client.delete(
            "/api/v1alpha1/server",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200

        # Verify serverdata preserved
        assert test_settings.serverdata_dir.exists()
        assert config_file.exists()
        assert config_file.read_text() == '{"test": true}'

        # Verify server dir deleted
        assert not test_settings.server_dir.exists()

        integration_app.dependency_overrides.clear()

    def test_uninstall_returns_proper_error_envelope(
        self,
        integration_app: FastAPI,
        test_settings: Settings,
        test_service: ServerService,
    ) -> None:
        """Error responses use proper detail structure."""
        # Don't create installation - will return 404
        integration_app.dependency_overrides[get_settings] = lambda: test_settings
        integration_app.dependency_overrides[get_server_service] = lambda: test_service

        client = TestClient(integration_app)
        response = client.delete(
            "/api/v1alpha1/server",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        json_response = response.json()
        assert "detail" in json_response
        assert "code" in json_response["detail"]
        assert "message" in json_response["detail"]

        integration_app.dependency_overrides.clear()
