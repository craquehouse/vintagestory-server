"""Tests for server installation REST API endpoints."""

from collections.abc import Generator
from pathlib import Path

import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.routers.server import get_server_service
from vintagestory_api.services.server import (
    VS_CDN_BASE,
    VS_STABLE_API,
    ServerService,
)

from .test_install import create_mock_server_tarball

# pyright: reportPrivateUsage=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false

# Test API keys
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


class TestServerInstallEndpoint:
    """Tests for POST /api/v1alpha1/server/install endpoint (AC: 1-5)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        # Create a test service with test settings
        test_service = ServerService(test_settings)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_install_requires_authentication(self, integration_client: TestClient) -> None:
        """POST /server/install requires API key (AC: 5.4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.21.3"},
        )

        assert response.status_code == 401

    def test_install_requires_admin_role(self, integration_client: TestClient) -> None:
        """POST /server/install requires Admin role (AC: 5.4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.21.3"},
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"

    def test_install_invalid_version_format_returns_422(
        self, integration_client: TestClient
    ) -> None:
        """POST /server/install with invalid version format returns 422 (AC: 4)."""
        # "invalid" doesn't match Pydantic regex pattern - rejected before our code
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "invalid"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Pydantic validation error returns 422
        assert response.status_code == 422

    def test_install_missing_patch_returns_422(self, integration_client: TestClient) -> None:
        """POST /server/install with incomplete version returns 422."""
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.2"},  # Missing patch number - fails regex
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Pydantic validation error returns 422
        assert response.status_code == 422

    @respx.mock
    def test_install_version_not_found_returns_404(self, integration_client: TestClient) -> None:
        """POST /server/install with non-existent version returns 404 (AC: 3)."""
        stable_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.99.0.tar.gz"
        unstable_url = f"{VS_CDN_BASE}/unstable/vs_server_linux-x64_1.99.0.tar.gz"

        respx.head(stable_url).mock(return_value=Response(404))
        respx.head(unstable_url).mock(return_value=Response(404))

        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.99.0"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["code"] == "VERSION_NOT_FOUND"

    def test_install_already_installed_returns_409(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/install when server exists returns 409 (AC: 5)."""
        # Create server files to simulate installed state
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.21.6"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 409
        error = response.json()["detail"]
        assert error["code"] == "SERVER_ALREADY_INSTALLED"

    @respx.mock
    def test_install_success_completes_end_to_end(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/install completes installation end-to-end (AC: 1, 2).

        Verifies:
        1. Initial response shows "installing" state
        2. Background task completes successfully
        3. Status endpoint shows "installed" state
        4. Server files exist on disk
        """
        # Use version 1.21.6 which exists in our mock stable.json response
        version = "1.21.6"

        # Create mock tarball and get its actual MD5
        tarball_bytes, actual_md5 = create_mock_server_tarball(Path("/tmp"))

        # Create mock API response with the correct MD5 checksum
        mock_api_response = {
            version: {
                "linuxserver": {
                    "filename": f"vs_server_linux-x64_{version}.tar.gz",
                    "filesize": "40.2 MB",
                    "md5": actual_md5,  # Use actual checksum
                    "urls": {
                        "cdn": f"{VS_CDN_BASE}/stable/vs_server_linux-x64_{version}.tar.gz",
                        "local": f"https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_{version}.tar.gz",
                    },
                    "latest": True,
                }
            }
        }

        # Mock HEAD request for version availability check
        head_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_{version}.tar.gz"
        respx.head(head_url).mock(return_value=Response(200))

        # Mock stable.json for version info lookup (used by background task)
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=mock_api_response))

        # Mock the actual download (used by background task)
        download_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_{version}.tar.gz"
        respx.get(download_url).mock(
            return_value=Response(
                200,
                content=tarball_bytes,
                headers={"content-length": str(len(tarball_bytes))},
            )
        )

        # POST to start installation
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": version},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Verify initial response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "installing"
        assert data["data"]["version"] == version

        # Background tasks run synchronously in TestClient, so installation
        # should be complete. Verify via status endpoint.
        status_response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "ok"
        assert status_data["data"]["state"] == "installed"
        assert status_data["data"]["version"] == version

        # Verify server files actually exist on disk
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        assert (server_dir / "VintagestoryServer.dll").exists()
        assert (server_dir / "VintagestoryLib.dll").exists()
        assert (vsmanager_dir / "current_version").read_text() == version

        # Verify serverdata dir created
        assert (temp_data_dir / "serverdata").is_dir()


class TestServerInstallStatusEndpoint:
    """Tests for GET /api/v1alpha1/server/install/status endpoint (AC: 2)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_status_requires_authentication(self, integration_client: TestClient) -> None:
        """GET /server/install/status requires API key."""
        response = integration_client.get("/api/v1alpha1/server/install/status")

        assert response.status_code == 401

    def test_status_returns_not_installed(self, integration_client: TestClient) -> None:
        """GET /server/install/status returns not_installed when server missing."""
        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "not_installed"

    def test_status_returns_installed(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """GET /server/install/status returns installed when server exists."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "installed"
        assert data["data"]["version"] == "1.21.3"

    def test_status_follows_envelope_format(self, integration_client: TestClient) -> None:
        """GET /server/install/status follows standard API envelope."""
        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"

    def test_status_accessible_by_monitor(self, integration_client: TestClient) -> None:
        """GET /server/install/status accessible by Monitor role."""
        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        # Should be accessible (read endpoint)
        assert response.status_code == 200

    def test_status_includes_error_code_on_failure(
        self, integration_app: FastAPI, integration_client: TestClient
    ) -> None:
        """GET /server/install/status includes error_code in error state."""
        from vintagestory_api.models.errors import ErrorCode

        # Get the service and set error state
        test_service = integration_app.dependency_overrides[get_server_service]()
        test_service._set_install_error(
            "Downloaded server file checksum verification failed",
            ErrorCode.CHECKSUM_MISMATCH,
        )

        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["state"] == "error"
        assert data["data"]["error"] == "Downloaded server file checksum verification failed"
        assert data["data"]["error_code"] == ErrorCode.CHECKSUM_MISMATCH
