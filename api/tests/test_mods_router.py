"""Tests for mods router API endpoints."""

import io
import json
import zipfile
from collections.abc import Generator
from pathlib import Path

import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from vintagestory_api.main import app
from vintagestory_api.services.mods import ModService, get_mod_service
from vintagestory_api.services.pending_restart import PendingRestartState

# Test API keys - match .env.test
TEST_ADMIN_KEY = "test-admin-key-for-testing"
TEST_MONITOR_KEY = "test-monitor-key-for-testing"


def create_mod_zip_bytes(modinfo: dict[str, object]) -> bytes:
    """Create a mod zip file as bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("modinfo.json", json.dumps(modinfo))
    return buffer.getvalue()


# Sample mod API response - game_version "1.21.3" must be in tags for "compatible"
SMITHINGPLUS_MOD = {
    "modid": 2655,
    "name": "Smithing Plus",
    "urlalias": "smithingplus",
    "author": "jayu",
    "releases": [
        {
            "releaseid": 27001,
            "modversion": "1.8.3",
            "filename": "smithingplus_1.8.3.zip",
            "fileid": 59176,
            "downloads": 49726,
            "tags": ["1.21.0", "1.21.1", "1.21.2", "1.21.3"],
        },
    ],
}


class TestInstallModEndpoint:
    """Tests for POST /api/v1alpha1/mods endpoint."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mod_service(self, temp_data_dir: Path) -> ModService:
        """Create a ModService with test directories."""
        return ModService(
            state_dir=temp_data_dir / "state",
            mods_dir=temp_data_dir / "mods",
            cache_dir=temp_data_dir / "cache",
            restart_state=PendingRestartState(),
            game_version="1.21.3",
        )

    @pytest.fixture
    def test_app(self, mod_service: ModService) -> Generator[FastAPI, None, None]:
        """Create app with test mod service injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self, test_app: FastAPI) -> TestClient:
        """Create test client with dependency overrides applied."""
        return TestClient(test_app)

    @pytest.fixture
    def admin_headers(self) -> dict[str, str]:
        """Return headers for admin authentication."""
        return {"X-API-Key": TEST_ADMIN_KEY}

    @respx.mock
    def test_install_mod_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        temp_data_dir: Path,
    ) -> None:
        """POST /mods successfully installs a mod."""
        mod_zip = create_mod_zip_bytes(
            {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.3"}
        )

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )
        respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
            return_value=Response(200, content=mod_zip)
        )

        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "smithingplus"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["slug"] == "smithingplus"
        assert data["data"]["version"] == "1.8.3"
        assert data["data"]["filename"] == "smithingplus_1.8.3.zip"
        assert data["data"]["compatibility"] == "compatible"
        assert data["data"]["pending_restart"] is False

        # Verify file was created
        assert (temp_data_dir / "mods" / "smithingplus_1.8.3.zip").exists()

    @respx.mock
    def test_install_mod_with_version(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """POST /mods installs specific version when requested."""
        mod_with_versions = {
            **SMITHINGPLUS_MOD,
            "releases": [
                {
                    "releaseid": 27001,
                    "modversion": "1.8.3",
                    "filename": "smithingplus_1.8.3.zip",
                    "fileid": 59176,
                    "tags": ["1.21.3"],
                },
                {
                    "releaseid": 26000,
                    "modversion": "1.8.2",
                    "filename": "smithingplus_1.8.2.zip",
                    "fileid": 58000,
                    "tags": ["1.21.0"],
                },
            ],
        }

        mod_zip = create_mod_zip_bytes(
            {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.2"}
        )

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": mod_with_versions},
            )
        )
        respx.get("https://mods.vintagestory.at/download?fileid=58000").mock(
            return_value=Response(200, content=mod_zip)
        )

        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "smithingplus", "version": "1.8.2"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["version"] == "1.8.2"
        # 1.21.3 not in tags for 1.8.2
        assert data["data"]["compatibility"] == "not_verified"

    @respx.mock
    def test_install_mod_not_found(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """POST /mods returns 404 for non-existent mod."""
        respx.get("https://mods.vintagestory.at/api/mod/nonexistent").mock(
            return_value=Response(
                200,
                json={"statuscode": "404", "mod": None},
            )
        )

        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "nonexistent"},
            headers=admin_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "MOD_NOT_FOUND"

    def test_install_mod_already_installed(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """POST /mods returns 409 for already installed mod."""
        # Pre-install the mod
        mods_dir = temp_data_dir / "mods"
        mod_zip_path = mods_dir / "smithingplus_1.0.0.zip"
        with zipfile.ZipFile(mod_zip_path, "w") as zf:
            zf.writestr(
                "modinfo.json",
                json.dumps({"modid": "smithingplus", "name": "Test", "version": "1.0.0"}),
            )
        mod_service.state_manager.sync_state_with_disk()

        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "smithingplus"},
            headers=admin_headers,
        )

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == "MOD_ALREADY_INSTALLED"
        assert "1.0.0" in data["detail"]["message"]

    def test_install_mod_requires_admin(self, client: TestClient) -> None:
        """POST /mods requires Admin role."""
        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "smithingplus"},
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403

    def test_install_mod_requires_auth(self, client: TestClient) -> None:
        """POST /mods requires authentication."""
        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "smithingplus"},
        )

        assert response.status_code == 401

    def test_install_mod_validates_slug(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """POST /mods validates slug field."""
        # Empty slug
        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": ""},
            headers=admin_headers,
        )
        assert response.status_code == 422

        # Missing slug
        response = client.post(
            "/api/v1alpha1/mods",
            json={},
            headers=admin_headers,
        )
        assert response.status_code == 422

    @respx.mock
    def test_install_mod_api_unavailable(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """POST /mods returns 502 when mod API is unavailable."""
        import httpx

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "smithingplus"},
            headers=admin_headers,
        )

        assert response.status_code == 502
        data = response.json()
        assert data["detail"]["code"] == "EXTERNAL_API_ERROR"
