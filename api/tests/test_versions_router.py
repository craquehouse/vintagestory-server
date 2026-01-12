"""Tests for versions API router.

Story 13.1: Server Versions API

Tests cover:
- GET /versions endpoint with and without channel filter
- GET /versions/{version} detail endpoint
- Authentication requirements
- Cache behavior
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.server import VersionInfo
from vintagestory_api.services.versions_cache import reset_versions_cache

# Test API keys
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset versions cache before and after each test."""
    reset_versions_cache()
    yield
    reset_versions_cache()


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
def client(override_settings: None) -> TestClient:
    """Create test client with settings override."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Admin authentication headers."""
    return {"X-API-Key": TEST_ADMIN_KEY}


@pytest.fixture
def mock_versions():
    """Sample versions data for mocking."""
    return {
        "stable": {
            "1.21.3": VersionInfo(
                version="1.21.3",
                filename="vs_server_linux-x64_1.21.3.tar.gz",
                filesize="40.2 MB",
                md5="abc123",
                cdn_url="https://cdn.vintagestory.at/stable/1",
                local_url="https://vintagestory.at/stable/1",
                is_latest=True,
                channel="stable",
            ),
            "1.21.2": VersionInfo(
                version="1.21.2",
                filename="vs_server_linux-x64_1.21.2.tar.gz",
                filesize="40.1 MB",
                md5="def456",
                cdn_url="https://cdn.vintagestory.at/stable/2",
                local_url="https://vintagestory.at/stable/2",
                is_latest=False,
                channel="stable",
            ),
        },
        "unstable": {
            "1.22.0-pre.1": VersionInfo(
                version="1.22.0-pre.1",
                filename="vs_server_linux-x64_1.22.0-pre.1.tar.gz",
                filesize="41.0 MB",
                md5="xyz789",
                cdn_url="https://cdn.vintagestory.at/unstable/1",
                local_url="https://vintagestory.at/unstable/1",
                is_latest=True,
                channel="unstable",
            ),
        },
    }


class TestListVersions:
    """Tests for GET /versions endpoint."""

    def test_list_versions_requires_auth(self, client):
        """GET /versions without auth should return 401."""
        # Make request without auth headers
        response = client.get("/api/v1alpha1/versions")

        # 401 for no auth, not 403
        assert response.status_code == 401

    def test_list_versions_all_channels(self, client, auth_headers, mock_versions):
        """GET /versions should return versions from all channels."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=lambda ch: mock_versions.get(ch, {})
            )
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1alpha1/versions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            # Should have versions from both channels
            versions = data["data"]["versions"]
            assert len(versions) == 3
            # Check channels are present
            channels = {v["channel"] for v in versions}
            assert channels == {"stable", "unstable"}

    def test_list_versions_stable_only(self, client, auth_headers, mock_versions):
        """GET /versions?channel=stable should return only stable versions."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                return_value=mock_versions["stable"]
            )
            mock_get_service.return_value = mock_service

            response = client.get(
                "/api/v1alpha1/versions?channel=stable", headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            versions = data["data"]["versions"]
            assert len(versions) == 2
            assert all(v["channel"] == "stable" for v in versions)

    def test_list_versions_unstable_only(self, client, auth_headers, mock_versions):
        """GET /versions?channel=unstable should return only unstable versions."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                return_value=mock_versions["unstable"]
            )
            mock_get_service.return_value = mock_service

            response = client.get(
                "/api/v1alpha1/versions?channel=unstable", headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            versions = data["data"]["versions"]
            assert len(versions) == 1
            assert versions[0]["channel"] == "unstable"

    def test_list_versions_invalid_channel(self, client, auth_headers):
        """GET /versions?channel=invalid should return 422 validation error."""
        response = client.get(
            "/api/v1alpha1/versions?channel=invalid", headers=auth_headers
        )

        assert response.status_code == 422

    def test_list_versions_includes_total(self, client, auth_headers, mock_versions):
        """Response should include total count of versions."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=lambda ch: mock_versions.get(ch, {})
            )
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1alpha1/versions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["total"] == 3

    def test_list_versions_includes_cache_indicator(
        self, client, auth_headers, mock_versions
    ):
        """Response should include cached indicator."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=lambda ch: mock_versions.get(ch, {})
            )
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1alpha1/versions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "cached" in data["data"]
            assert "cached_at" in data["data"]


class TestGetVersionDetail:
    """Tests for GET /versions/{version} endpoint."""

    def test_get_version_requires_auth(self, client):
        """GET /versions/{version} without auth should return 401."""
        response = client.get("/api/v1alpha1/versions/1.21.3")

        assert response.status_code == 401

    def test_get_version_found(self, client, auth_headers, mock_versions):
        """GET /versions/{version} should return version details when found."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=lambda ch: mock_versions.get(ch, {})
            )
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1alpha1/versions/1.21.3", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["data"]["version"]["version"] == "1.21.3"
            assert data["data"]["version"]["channel"] == "stable"
            assert data["data"]["version"]["is_latest"] is True

    def test_get_version_not_found(self, client, auth_headers, mock_versions):
        """GET /versions/{version} should return 404 when version not found."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=lambda ch: mock_versions.get(ch, {})
            )
            mock_get_service.return_value = mock_service

            response = client.get(
                "/api/v1alpha1/versions/99.99.99", headers=auth_headers
            )

            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["code"] == "VERSION_NOT_FOUND"

    def test_get_unstable_version(self, client, auth_headers, mock_versions):
        """GET /versions/{version} should find unstable versions."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=lambda ch: mock_versions.get(ch, {})
            )
            mock_get_service.return_value = mock_service

            response = client.get(
                "/api/v1alpha1/versions/1.22.0-pre.1", headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["version"]["channel"] == "unstable"

    def test_get_version_includes_cache_indicator(
        self, client, auth_headers, mock_versions
    ):
        """Version detail response should include cached indicator."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=lambda ch: mock_versions.get(ch, {})
            )
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1alpha1/versions/1.21.3", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "cached" in data["data"]
            assert "cached_at" in data["data"]


class TestMonitorRoleAccess:
    """Tests for Monitor role access to versions endpoints."""

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Monitor authentication headers."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    def test_list_versions_monitor_role(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
        mock_versions: dict[str, dict[str, VersionInfo]],
    ) -> None:
        """Monitor role should be able to list versions (read-only)."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=lambda ch: mock_versions.get(ch, {})
            )
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1alpha1/versions", headers=monitor_headers)

            assert response.status_code == 200

    def test_get_version_monitor_role(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
        mock_versions: dict[str, dict[str, VersionInfo]],
    ) -> None:
        """Monitor role should be able to get version detail (read-only)."""
        with patch(
            "vintagestory_api.routers.versions.get_server_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_available_versions = AsyncMock(
                side_effect=lambda ch: mock_versions.get(ch, {})
            )
            mock_get_service.return_value = mock_service

            response = client.get(
                "/api/v1alpha1/versions/1.21.3", headers=monitor_headers
            )

            assert response.status_code == 200
