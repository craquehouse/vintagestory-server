"""Tests for mods router API endpoints."""

import io
import json
import zipfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY  # type: ignore[import-not-found]
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.services.mods import ModService, get_mod_service
from vintagestory_api.services.pending_restart import PendingRestartState


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
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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


class TestLookupModEndpoint:
    """Tests for GET /api/v1alpha1/mods/lookup/{slug} endpoint."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Return headers for monitor authentication."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    @respx.mock
    def test_lookup_mod_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/lookup/{slug} returns mod details with compatibility."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        response = client.get(
            "/api/v1alpha1/mods/lookup/smithingplus",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["slug"] == "smithingplus"
        assert data["data"]["name"] == "Smithing Plus"
        assert data["data"]["author"] == "jayu"
        assert data["data"]["latest_version"] == "1.8.3"
        assert data["data"]["downloads"] == 49726
        assert data["data"]["side"] == "Both"
        assert data["data"]["compatibility"]["status"] == "compatible"
        assert data["data"]["compatibility"]["game_version"] == "1.21.3"
        assert data["data"]["compatibility"]["mod_version"] == "1.8.3"
        assert data["data"]["compatibility"]["message"] is None

    @respx.mock
    def test_lookup_mod_monitor_access(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
    ) -> None:
        """GET /mods/lookup/{slug} is accessible by Monitor role."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        response = client.get(
            "/api/v1alpha1/mods/lookup/smithingplus",
            headers=monitor_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @respx.mock
    def test_lookup_mod_not_found(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/lookup/{slug} returns 404 for non-existent mod."""
        respx.get("https://mods.vintagestory.at/api/mod/nonexistent").mock(
            return_value=Response(
                200,
                json={"statuscode": "404", "mod": None},
            )
        )

        response = client.get(
            "/api/v1alpha1/mods/lookup/nonexistent",
            headers=admin_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "MOD_NOT_FOUND"

    @respx.mock
    def test_lookup_mod_api_unavailable(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/lookup/{slug} returns 502 when API is unavailable."""
        import httpx

        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        response = client.get(
            "/api/v1alpha1/mods/lookup/smithingplus",
            headers=admin_headers,
        )

        assert response.status_code == 502
        data = response.json()
        assert data["detail"]["code"] == "EXTERNAL_API_ERROR"

    def test_lookup_mod_invalid_slug(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/lookup/{slug} returns 400 for invalid slug format."""
        # Use a slug with invalid characters (periods/slashes aren't allowed)
        response = client.get(
            "/api/v1alpha1/mods/lookup/invalid.slug.with.dots",
            headers=admin_headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_SLUG"

    def test_lookup_mod_rejects_windows_reserved_name(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/lookup/{slug} rejects Windows reserved device names."""
        response = client.get(
            "/api/v1alpha1/mods/lookup/con",
            headers=admin_headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_SLUG"

    def test_lookup_mod_requires_auth(self, client: TestClient) -> None:
        """GET /mods/lookup/{slug} requires authentication."""
        response = client.get("/api/v1alpha1/mods/lookup/smithingplus")

        assert response.status_code == 401

    @respx.mock
    def test_lookup_mod_with_url(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/lookup/{slug} accepts full URL in path."""
        # Using URL-encoded path
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        # The {slug:path} captures the full URL segment
        response = client.get(
            "/api/v1alpha1/mods/lookup/https://mods.vintagestory.at/smithingplus",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["slug"] == "smithingplus"


def create_mod_zip_file(path: Path, modinfo: dict[str, object]) -> None:
    """Create a mod zip file at the given path."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("modinfo.json", json.dumps(modinfo))


class TestEnableModEndpoint:
    """Tests for POST /api/v1alpha1/mods/{slug}/enable endpoint."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Return headers for monitor authentication."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    def test_enable_mod_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """POST /mods/{slug}/enable successfully enables a disabled mod."""
        mods_dir = temp_data_dir / "mods"
        zip_path = mods_dir / "testmod_1.0.0.zip"
        create_mod_zip_file(zip_path, {"modid": "testmod", "name": "Test", "version": "1.0.0"})
        zip_path.rename(mods_dir / "testmod_1.0.0.zip.disabled")
        mod_service.state_manager.sync_state_with_disk()

        response = client.post(
            "/api/v1alpha1/mods/testmod/enable",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["slug"] == "testmod"
        assert data["data"]["enabled"] is True
        assert data["data"]["pending_restart"] is False

        # Verify file was renamed
        assert (mods_dir / "testmod_1.0.0.zip").exists()
        assert not (mods_dir / "testmod_1.0.0.zip.disabled").exists()

    def test_enable_already_enabled_mod_idempotent(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """POST /mods/{slug}/enable on already-enabled mod returns success."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "enabledmod_1.0.0.zip",
            {"modid": "enabledmod", "name": "Enabled", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        response = client.post(
            "/api/v1alpha1/mods/enabledmod/enable",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["slug"] == "enabledmod"
        assert data["data"]["enabled"] is True
        assert data["data"]["pending_restart"] is False

    def test_enable_mod_not_installed(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """POST /mods/{slug}/enable returns 404 for non-installed mod."""
        response = client.post(
            "/api/v1alpha1/mods/nonexistent/enable",
            headers=admin_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "MOD_NOT_INSTALLED"

    def test_enable_mod_requires_admin(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """POST /mods/{slug}/enable requires Admin role."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "admintest_1.0.0.zip",
            {"modid": "admintest", "name": "Admin Test", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        response = client.post(
            "/api/v1alpha1/mods/admintest/enable",
            headers=monitor_headers,
        )

        assert response.status_code == 403

    def test_enable_mod_requires_auth(self, client: TestClient) -> None:
        """POST /mods/{slug}/enable requires authentication."""
        response = client.post("/api/v1alpha1/mods/testmod/enable")

        assert response.status_code == 401


class TestDisableModEndpoint:
    """Tests for POST /api/v1alpha1/mods/{slug}/disable endpoint."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Return headers for monitor authentication."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    def test_disable_mod_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """POST /mods/{slug}/disable successfully disables an enabled mod."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "disablemod_1.0.0.zip",
            {"modid": "disablemod", "name": "Disable Me", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        response = client.post(
            "/api/v1alpha1/mods/disablemod/disable",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["slug"] == "disablemod"
        assert data["data"]["enabled"] is False
        assert data["data"]["pending_restart"] is False

        # Verify file was renamed
        assert (mods_dir / "disablemod_1.0.0.zip.disabled").exists()
        assert not (mods_dir / "disablemod_1.0.0.zip").exists()

    def test_disable_already_disabled_mod_idempotent(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """POST /mods/{slug}/disable on already-disabled mod returns success."""
        mods_dir = temp_data_dir / "mods"
        zip_path = mods_dir / "disabledmod_1.0.0.zip"
        modinfo: dict[str, object] = {
            "modid": "disabledmod",
            "name": "Disabled",
            "version": "1.0.0",
        }
        create_mod_zip_file(zip_path, modinfo)
        zip_path.rename(mods_dir / "disabledmod_1.0.0.zip.disabled")
        mod_service.state_manager.sync_state_with_disk()

        response = client.post(
            "/api/v1alpha1/mods/disabledmod/disable",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["slug"] == "disabledmod"
        assert data["data"]["enabled"] is False
        assert data["data"]["pending_restart"] is False

    def test_disable_mod_not_installed(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """POST /mods/{slug}/disable returns 404 for non-installed mod."""
        response = client.post(
            "/api/v1alpha1/mods/nonexistent/disable",
            headers=admin_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "MOD_NOT_INSTALLED"

    def test_disable_mod_requires_admin(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """POST /mods/{slug}/disable requires Admin role."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "admintest_1.0.0.zip",
            {"modid": "admintest", "name": "Admin Test", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        response = client.post(
            "/api/v1alpha1/mods/admintest/disable",
            headers=monitor_headers,
        )

        assert response.status_code == 403

    def test_disable_mod_requires_auth(self, client: TestClient) -> None:
        """POST /mods/{slug}/disable requires authentication."""
        response = client.post("/api/v1alpha1/mods/testmod/disable")

        assert response.status_code == 401


class TestRemoveModEndpoint:
    """Tests for DELETE /api/v1alpha1/mods/{slug} endpoint."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Return headers for monitor authentication."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    def test_remove_mod_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """DELETE /mods/{slug} successfully removes a mod."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "removemod_1.0.0.zip",
            {"modid": "removemod", "name": "Remove Me", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        response = client.delete(
            "/api/v1alpha1/mods/removemod",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["slug"] == "removemod"
        assert data["data"]["pending_restart"] is False

        # Verify file was deleted
        assert not (mods_dir / "removemod_1.0.0.zip").exists()

    def test_remove_disabled_mod(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """DELETE /mods/{slug} removes a disabled mod."""
        mods_dir = temp_data_dir / "mods"
        zip_path = mods_dir / "removedisabled_1.0.0.zip"
        modinfo: dict[str, object] = {
            "modid": "removedisabled",
            "name": "Remove Disabled",
            "version": "1.0.0",
        }
        create_mod_zip_file(zip_path, modinfo)
        zip_path.rename(mods_dir / "removedisabled_1.0.0.zip.disabled")
        mod_service.state_manager.sync_state_with_disk()

        response = client.delete(
            "/api/v1alpha1/mods/removedisabled",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["slug"] == "removedisabled"

        # Verify file was deleted
        assert not (mods_dir / "removedisabled_1.0.0.zip.disabled").exists()

    def test_remove_mod_not_installed(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """DELETE /mods/{slug} returns 404 for non-installed mod."""
        response = client.delete(
            "/api/v1alpha1/mods/nonexistent",
            headers=admin_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "MOD_NOT_INSTALLED"

    def test_remove_mod_requires_admin(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """DELETE /mods/{slug} requires Admin role."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "admintest_1.0.0.zip",
            {"modid": "admintest", "name": "Admin Test", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        response = client.delete(
            "/api/v1alpha1/mods/admintest",
            headers=monitor_headers,
        )

        assert response.status_code == 403

    def test_remove_mod_requires_auth(self, client: TestClient) -> None:
        """DELETE /mods/{slug} requires authentication."""
        response = client.delete("/api/v1alpha1/mods/testmod")

        assert response.status_code == 401

    def test_remove_mod_with_pending_restart(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """DELETE /mods/{slug} sets pending_restart when server is running."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "restartmod_1.0.0.zip",
            {"modid": "restartmod", "name": "Restart Test", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        # Simulate server running
        mod_service.set_server_running(True)

        response = client.delete(
            "/api/v1alpha1/mods/restartmod",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["pending_restart"] is True


class TestListModsEndpoint:
    """Tests for GET /api/v1alpha1/mods endpoint."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

    @pytest.fixture
    def restart_state(self) -> PendingRestartState:
        """Create a dedicated restart state for testing."""
        return PendingRestartState()

    @pytest.fixture
    def mod_service(
        self, temp_data_dir: Path, restart_state: PendingRestartState
    ) -> ModService:
        """Create a ModService with test directories."""
        return ModService(
            state_dir=temp_data_dir / "state",
            mods_dir=temp_data_dir / "mods",
            cache_dir=temp_data_dir / "cache",
            restart_state=restart_state,
            game_version="1.21.3",
        )

    @pytest.fixture
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Return headers for monitor authentication."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    def test_list_mods_admin_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """GET /mods returns list of installed mods as Admin (AC: 1)."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "testmod_1.0.0.zip",
            {"modid": "testmod", "name": "Test Mod", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        response = client.get("/api/v1alpha1/mods", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "mods" in data["data"]
        assert "pending_restart" in data["data"]
        assert len(data["data"]["mods"]) == 1

        mod = data["data"]["mods"][0]
        assert mod["slug"] == "testmod"
        assert mod["name"] == "Test Mod"
        assert mod["version"] == "1.0.0"
        assert mod["enabled"] is True

    def test_list_mods_monitor_success(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """GET /mods returns list of installed mods as Monitor (AC: 2)."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "monitortest_1.0.0.zip",
            {"modid": "monitortest", "name": "Monitor Test", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        response = client.get("/api/v1alpha1/mods", headers=monitor_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert len(data["data"]["mods"]) == 1
        assert data["data"]["mods"][0]["slug"] == "monitortest"

    def test_list_mods_empty_array_when_no_mods(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods returns empty array when no mods installed (AC: 3)."""
        response = client.get("/api/v1alpha1/mods", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["mods"] == []
        assert data["data"]["pending_restart"] is False

    def test_list_mods_includes_pending_restart_flag(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
        restart_state: PendingRestartState,
    ) -> None:
        """GET /mods includes pending_restart: true when restart is pending (AC: 4)."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "restarttest_1.0.0.zip",
            {"modid": "restarttest", "name": "Restart Test", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        # Set pending restart flag
        restart_state.require_restart("Test mod change")

        response = client.get("/api/v1alpha1/mods", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["pending_restart"] is True

    def test_list_mods_requires_auth(self, client: TestClient) -> None:
        """GET /mods returns 401 without authentication (AC: 5)."""
        response = client.get("/api/v1alpha1/mods")

        assert response.status_code == 401

    def test_list_mods_rejects_invalid_api_key(self, client: TestClient) -> None:
        """GET /mods returns 401 with invalid API key (AC: 5)."""
        response = client.get(
            "/api/v1alpha1/mods",
            headers={"X-API-Key": "invalid-key-that-does-not-exist"},
        )

        assert response.status_code == 401

    def test_list_mods_includes_multiple_mods(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """GET /mods returns all installed mods."""
        mods_dir = temp_data_dir / "mods"

        # Create multiple mods
        create_mod_zip_file(
            mods_dir / "mod1_1.0.0.zip",
            {"modid": "mod1", "name": "Mod One", "version": "1.0.0"},
        )
        create_mod_zip_file(
            mods_dir / "mod2_2.0.0.zip",
            {"modid": "mod2", "name": "Mod Two", "version": "2.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()

        response = client.get("/api/v1alpha1/mods", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["mods"]) == 2

        slugs = {mod["slug"] for mod in data["data"]["mods"]}
        assert slugs == {"mod1", "mod2"}

    def test_list_mods_includes_disabled_mods(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """GET /mods includes disabled mods with enabled=False."""
        mods_dir = temp_data_dir / "mods"

        # Create a disabled mod
        zip_path = mods_dir / "disabledmod_1.0.0.zip"
        create_mod_zip_file(
            zip_path,
            {"modid": "disabledmod", "name": "Disabled Mod", "version": "1.0.0"},
        )
        zip_path.rename(mods_dir / "disabledmod_1.0.0.zip.disabled")
        mod_service.state_manager.sync_state_with_disk()

        response = client.get("/api/v1alpha1/mods", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["mods"]) == 1
        assert data["data"]["mods"][0]["slug"] == "disabledmod"
        assert data["data"]["mods"][0]["enabled"] is False


# --- Sample data for browse endpoint tests ---

BROWSE_MODS_API_RESPONSE: dict[str, Any] = {
    "statuscode": "200",
    "mods": [
        {
            "modid": 2655,
            "name": "Smithing Plus",
            "summary": "Expanded smithing mechanics",
            "author": "jayu",
            "downloads": 204656,
            "follows": 2348,
            "trendingpoints": 1853,
            "side": "both",
            "type": "mod",
            "logo": "https://moddbcdn.vintagestory.at/smithingplus/logo.png",
            "tags": ["Crafting", "QoL"],
            "lastreleased": "2025-10-09 21:28:57",
            "urlalias": "smithingplus",
            "modidstrs": ["smithingplus"],
        },
        {
            "modid": 1234,
            "name": "Old Popular Mod",
            "summary": "A very popular mod",
            "author": "author1",
            "downloads": 500000,
            "follows": 5000,
            "trendingpoints": 100,
            "side": "server",
            "type": "mod",
            "logo": None,
            "tags": ["Gameplay"],
            "lastreleased": "2024-01-15 10:00:00",
            "urlalias": "oldpopular",
            "modidstrs": ["oldpopular"],
        },
        {
            "modid": 5678,
            "name": "Trending New Mod",
            "summary": "Trending right now",
            "author": "author2",
            "downloads": 1000,
            "follows": 500,
            "trendingpoints": 5000,
            "side": "client",
            "type": "mod",
            "logo": "https://moddbcdn.vintagestory.at/trending/logo.png",
            "tags": ["UI"],
            "lastreleased": "2025-12-01 15:30:00",
            "urlalias": "trendingnew",
            "modidstrs": ["trendingnew"],
        },
    ],
}


class TestBrowseModsEndpoint:
    """Tests for GET /api/v1alpha1/mods/browse endpoint."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Return headers for monitor authentication."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    @respx.mock
    def test_browse_mods_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse returns paginated list of mods (AC: 1)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "mods" in data["data"]
        assert "pagination" in data["data"]

        # Verify mod structure
        mods = data["data"]["mods"]
        assert len(mods) == 3
        mod = mods[0]  # First mod (sorted by recent, trendingnew is newest)
        assert "slug" in mod
        assert "name" in mod
        assert "author" in mod
        assert "downloads" in mod
        assert "tags" in mod
        assert "logo_url" in mod
        assert "side" in mod
        assert "mod_type" in mod

    @respx.mock
    def test_browse_mods_pagination_metadata(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse returns proper pagination metadata (AC: 2)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?page=1&page_size=2", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        pagination = data["data"]["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 2
        assert pagination["total_items"] == 3
        assert pagination["total_pages"] == 2
        assert pagination["has_next"] is True
        assert pagination["has_prev"] is False

    @respx.mock
    def test_browse_mods_page_size_default(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse uses default page_size=20 (AC: 2)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["pagination"]["page_size"] == 20

    @respx.mock
    def test_browse_mods_sort_by_downloads(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse?sort=downloads sorts by downloads desc (AC: 3)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?sort=downloads", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]

        # Verify sort order: oldpopular (500000) > smithingplus (204656) > trendingnew (1000)
        assert mods[0]["slug"] == "oldpopular"
        assert mods[1]["slug"] == "smithingplus"
        assert mods[2]["slug"] == "trendingnew"

    @respx.mock
    def test_browse_mods_sort_by_trending(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse?sort=trending sorts by trending points desc (AC: 3)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?sort=trending", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]

        # Verify sort order: trendingnew (5000) > smithingplus (1853) > oldpopular (100)
        assert mods[0]["slug"] == "trendingnew"
        assert mods[1]["slug"] == "smithingplus"
        assert mods[2]["slug"] == "oldpopular"

    @respx.mock
    def test_browse_mods_sort_by_recent(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse?sort=recent sorts by last released desc (AC: 3)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?sort=recent", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]

        # Verify sort order by lastreleased:
        # trendingnew (2025-12-01) > smithingplus (2025-10-09) > oldpopular (2024-01-15)
        assert mods[0]["slug"] == "trendingnew"
        assert mods[1]["slug"] == "smithingplus"
        assert mods[2]["slug"] == "oldpopular"

    @respx.mock
    def test_browse_mods_sort_by_name(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse?sort=name sorts alphabetically ascending."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?sort=name", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]

        # Verify alphabetical sort order:
        # Old Popular Mod < Smithing Plus < Trending New Mod
        assert mods[0]["slug"] == "oldpopular"
        assert mods[1]["slug"] == "smithingplus"
        assert mods[2]["slug"] == "trendingnew"

    @respx.mock
    def test_browse_mods_api_unavailable(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse returns 502 when external API is unavailable (AC: 4)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 502
        data = response.json()
        assert data["detail"]["code"] == "EXTERNAL_API_ERROR"

    def test_browse_mods_invalid_page(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse returns 422 for page=0 (AC: 5)."""
        response = client.get(
            "/api/v1alpha1/mods/browse?page=0", headers=admin_headers
        )

        assert response.status_code == 422

    def test_browse_mods_invalid_page_size(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse returns 422 for page_size > 100 (AC: 5)."""
        response = client.get(
            "/api/v1alpha1/mods/browse?page_size=500", headers=admin_headers
        )

        assert response.status_code == 422

    def test_browse_mods_requires_auth(self, client: TestClient) -> None:
        """GET /mods/browse requires authentication."""
        response = client.get("/api/v1alpha1/mods/browse")

        assert response.status_code == 401

    @respx.mock
    def test_browse_mods_monitor_access(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse is accessible by Monitor role."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=monitor_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @respx.mock
    def test_browse_mods_second_page(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse?page=2 returns correct second page."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?page=2&page_size=2", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Page 2 with page_size=2 should have 1 mod (total 3 mods)
        mods = data["data"]["mods"]
        assert len(mods) == 1

        pagination = data["data"]["pagination"]
        assert pagination["page"] == 2
        assert pagination["has_next"] is False
        assert pagination["has_prev"] is True

    @respx.mock
    def test_browse_mods_empty_results(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse handles empty mod list."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json={"statuscode": "200", "mods": []})
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["mods"] == []
        assert data["data"]["pagination"]["total_items"] == 0
        assert data["data"]["pagination"]["total_pages"] == 1

    @respx.mock
    def test_browse_mods_invalid_sort_value(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse returns 422 for invalid sort value."""
        response = client.get(
            "/api/v1alpha1/mods/browse?sort=invalid", headers=admin_headers
        )

        assert response.status_code == 422

    @respx.mock
    def test_browse_mods_page_beyond_total(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse clamps page number to valid range."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?page=100", headers=admin_headers
        )

        # Should not error, but clamp to last valid page
        assert response.status_code == 200
        data = response.json()
        # With 3 mods and page_size=20, there's only 1 page
        assert data["data"]["pagination"]["page"] == 1

    @respx.mock
    def test_browse_mods_mod_fields_transform(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse transforms API field names correctly."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?sort=downloads", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mod = data["data"]["mods"][0]  # oldpopular (highest downloads)

        # Verify field transformations:
        # urlalias -> slug
        assert mod["slug"] == "oldpopular"
        # trendingpoints -> trending_points
        assert mod["trending_points"] == 100
        # type -> mod_type
        assert mod["mod_type"] == "mod"
        # logo -> logo_url (can be null)
        assert mod["logo_url"] is None
        # lastreleased -> last_released
        assert mod["last_released"] == "2024-01-15 10:00:00"

    @respx.mock
    def test_browse_mods_with_version_filter(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse?version=1.21.3 filters mods by game version."""
        # Mock game versions endpoint
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        {"tagid": -281565171286015, "name": "1.21.3", "color": "#CCCCCC"},
                        {"tagid": -281565171220479, "name": "1.21.2", "color": "#CCCCCC"},
                    ],
                },
            )
        )

        # Mock mods endpoint with gameversion parameter
        route = respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": "-281565171286015"},
        ).mock(return_value=Response(200, json=BROWSE_MODS_API_RESPONSE))

        response = client.get(
            "/api/v1alpha1/mods/browse?version=1.21.3", headers=admin_headers
        )

        assert response.status_code == 200
        assert route.called
        data = response.json()
        assert data["status"] == "ok"
        assert "mods" in data["data"]
        assert len(data["data"]["mods"]) == 3

    @respx.mock
    def test_browse_mods_version_not_found(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse?version=invalid returns 400 with error."""
        # Mock game versions endpoint with limited versions
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        {"tagid": -281565171286015, "name": "1.21.3", "color": "#CCCCCC"},
                    ],
                },
            )
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?version=9.99.99", headers=admin_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "GAME_VERSION_NOT_FOUND"
        assert "9.99.99" in data["detail"]["message"]

    @respx.mock
    def test_browse_mods_version_with_search(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse?version=1.21.3&search=smith combines filters."""
        # Mock game versions endpoint
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        {"tagid": -281565171286015, "name": "1.21.3", "color": "#CCCCCC"},
                    ],
                },
            )
        )

        # Mock mods endpoint with gameversion parameter
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": "-281565171286015"},
        ).mock(return_value=Response(200, json=BROWSE_MODS_API_RESPONSE))

        response = client.get(
            "/api/v1alpha1/mods/browse?version=1.21.3&search=smithing",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Only "Smithing Plus" matches the search
        assert len(data["data"]["mods"]) == 1
        assert data["data"]["mods"][0]["slug"] == "smithingplus"

    @respx.mock
    def test_browse_mods_without_version_uses_cache(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse without version uses cached get_all_mods."""
        route = respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        # First request
        response1 = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)
        assert response1.status_code == 200
        assert route.call_count == 1

        # Second request should use cache
        response2 = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)
        assert response2.status_code == 200
        assert route.call_count == 1  # Still 1 - cached

    @respx.mock
    def test_browse_mods_version_filter_api_error(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/browse?version returns 502 when API fails."""
        import httpx

        # Mock game versions endpoint to fail
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?version=1.21.3", headers=admin_headers
        )

        assert response.status_code == 502
        data = response.json()
        assert data["detail"]["code"] == "EXTERNAL_API_ERROR"


class TestGameVersionsEndpoint:
    """Tests for GET /api/v1alpha1/mods/gameversions endpoint.

    Story VSS-vth: Game version filter for mod browser.
    """

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self, test_app: FastAPI) -> TestClient:
        """Create test client with dependency overrides applied."""
        return TestClient(test_app)

    @pytest.fixture
    def admin_headers(self) -> dict[str, str]:
        """Headers with Admin API key."""
        return {"X-API-Key": TEST_ADMIN_KEY}

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Headers with Monitor API key."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    @respx.mock
    def test_gameversions_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/gameversions returns sorted list of versions."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        {"tagid": -281565171089407, "name": "1.21.0"},
                        {"tagid": -281565171286015, "name": "1.21.3"},
                        {"tagid": -281565170958335, "name": "1.20.0"},
                        {"tagid": -281565171155199, "name": "1.21.1"},
                    ],
                },
            )
        )

        response = client.get("/api/v1alpha1/mods/gameversions", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Versions should be sorted newest first
        versions = data["data"]["versions"]
        assert len(versions) == 4
        assert versions[0] == "1.21.3"
        assert versions[1] == "1.21.1"
        assert versions[2] == "1.21.0"
        assert versions[3] == "1.20.0"

    @respx.mock
    def test_gameversions_requires_auth(self, client: TestClient) -> None:
        """GET /mods/gameversions requires authentication."""
        response = client.get("/api/v1alpha1/mods/gameversions")
        assert response.status_code == 401

    @respx.mock
    def test_gameversions_monitor_access(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
    ) -> None:
        """GET /mods/gameversions is accessible by Monitor role."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        {"tagid": -281565171286015, "name": "1.21.3"},
                    ],
                },
            )
        )

        response = client.get("/api/v1alpha1/mods/gameversions", headers=monitor_headers)
        assert response.status_code == 200

    @respx.mock
    def test_gameversions_api_error(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/gameversions returns 502 when external API fails."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        response = client.get("/api/v1alpha1/mods/gameversions", headers=admin_headers)

        assert response.status_code == 502
        data = response.json()
        assert data["detail"]["code"] == "EXTERNAL_API_ERROR"

    @respx.mock
    def test_gameversions_caches_result(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/gameversions caches results."""
        route = respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        {"tagid": -281565171286015, "name": "1.21.3"},
                    ],
                },
            )
        )

        # First request
        response1 = client.get("/api/v1alpha1/mods/gameversions", headers=admin_headers)
        assert response1.status_code == 200
        assert route.call_count == 1

        # Second request should use cache
        response2 = client.get("/api/v1alpha1/mods/gameversions", headers=admin_headers)
        assert response2.status_code == 200
        assert route.call_count == 1  # Still 1 - cached

    @respx.mock
    def test_gameversions_empty_response(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/gameversions handles empty versions list gracefully."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [],
                },
            )
        )

        response = client.get("/api/v1alpha1/mods/gameversions", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["versions"] == []


class TestModTagsEndpoint:
    """Tests for GET /api/v1alpha1/mods/tags endpoint."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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

    @pytest.fixture
    def monitor_headers(self) -> dict[str, str]:
        """Return headers for monitor authentication."""
        return {"X-API-Key": TEST_MONITOR_KEY}

    @respx.mock
    def test_list_mod_tags_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/tags returns sorted list of unique tags."""
        mods_with_tags = {
            "statuscode": "200",
            "mods": [
                {
                    "modid": 1,
                    "name": "Mod 1",
                    "tags": ["Crafting", "QoL"],
                },
                {
                    "modid": 2,
                    "name": "Mod 2",
                    "tags": ["Gameplay", "CRAFTING"],  # Duplicate in different case
                },
                {
                    "modid": 3,
                    "name": "Mod 3",
                    "tags": ["UI", "QoL"],  # Another duplicate
                },
            ],
        }

        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=mods_with_tags)
        )

        response = client.get("/api/v1alpha1/mods/tags", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        tags = data["data"]["tags"]

        # Tags should be lowercased, deduplicated, and sorted
        assert tags == ["crafting", "gameplay", "qol", "ui"]

    @respx.mock
    def test_list_mod_tags_empty(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/tags handles mods with no tags."""
        mods_without_tags = {
            "statuscode": "200",
            "mods": [
                {"modid": 1, "name": "Mod 1"},
                {"modid": 2, "name": "Mod 2", "tags": []},
            ],
        }

        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=mods_without_tags)
        )

        response = client.get("/api/v1alpha1/mods/tags", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tags"] == []

    @respx.mock
    def test_list_mod_tags_monitor_access(
        self,
        client: TestClient,
        monitor_headers: dict[str, str],
    ) -> None:
        """GET /mods/tags is accessible by Monitor role."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json={"statuscode": "200", "mods": []})
        )

        response = client.get("/api/v1alpha1/mods/tags", headers=monitor_headers)
        assert response.status_code == 200

    def test_list_mod_tags_requires_auth(self, client: TestClient) -> None:
        """GET /mods/tags requires authentication."""
        response = client.get("/api/v1alpha1/mods/tags")
        assert response.status_code == 401

    @respx.mock
    def test_list_mod_tags_api_error(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/tags returns 502 when external API fails."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        response = client.get("/api/v1alpha1/mods/tags", headers=admin_headers)

        assert response.status_code == 502
        data = response.json()
        assert data["detail"]["code"] == "EXTERNAL_API_ERROR"


class TestBrowseItemSlugUrlalias:
    """Tests for VSS-brs: urlalias vs modidstrs slug handling.

    Some mods have different urlalias and modidstrs values. The browse API
    should use modidstrs[0] as the slug (for API lookups) and expose urlalias
    separately (for website URLs).
    """

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self, test_app: FastAPI) -> TestClient:
        """Create test client with dependency overrides applied."""
        return TestClient(test_app)

    @pytest.fixture
    def admin_headers(self) -> dict[str, str]:
        """Headers with Admin API key."""
        return {"X-API-Key": TEST_ADMIN_KEY}

    @respx.mock
    def test_browse_slug_uses_modidstrs_not_urlalias(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """VSS-brs: slug should be modidstrs[0], not urlalias.

        The "Mineral Necklaces" mod has:
        - urlalias: "mineralnecklaces"
        - modidstrs: ["mineraljewelry"]

        The API lookup endpoint requires modidstrs[0], so slug must be "mineraljewelry".
        """
        # Mod where urlalias differs from modidstrs
        mineral_necklaces_mod = {
            "modid": 3456,
            "assetid": 7890,
            "name": "Mineral Necklaces",
            "summary": "Craftable mineral jewelry",
            "author": "jewelcrafter",
            "downloads": 5000,
            "follows": 100,
            "trendingpoints": 50,
            "side": "both",
            "type": "mod",
            "logo": None,
            "tags": ["Crafting"],
            "lastreleased": "2025-11-01 12:00:00",
            "urlalias": "mineralnecklaces",  # Different from modidstrs!
            "modidstrs": ["mineraljewelry"],  # This is what the API expects
        }

        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mods": [mineral_necklaces_mod]},
            )
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        assert len(mods) == 1

        mod = mods[0]
        # slug should be modidstrs[0], NOT urlalias
        assert mod["slug"] == "mineraljewelry"
        # urlalias should be exposed separately
        assert mod["urlalias"] == "mineralnecklaces"

    @respx.mock
    def test_browse_slug_fallback_when_no_modidstrs(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """When modidstrs is empty, fall back to modid."""
        mod_without_modidstrs: dict[str, Any] = {
            "modid": 9999,
            "assetid": 1234,
            "name": "Legacy Mod",
            "summary": "An old mod",
            "author": "oldauthor",
            "downloads": 100,
            "follows": 10,
            "trendingpoints": 5,
            "side": "both",
            "type": "mod",
            "logo": None,
            "tags": [],
            "lastreleased": "2024-01-01 00:00:00",
            "urlalias": "legacymod",
            "modidstrs": [],  # Empty!
        }

        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mods": [mod_without_modidstrs]},
            )
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        mod = data["data"]["mods"][0]

        # Should fall back to modid as string
        assert mod["slug"] == "9999"
        # urlalias still exposed
        assert mod["urlalias"] == "legacymod"

    @respx.mock
    def test_browse_slug_fallback_when_modidstrs_is_null(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """When modidstrs is null (not just empty), fall back to modid."""
        mod_with_null_modidstrs: dict[str, Any] = {
            "modid": 7654,
            "assetid": 4567,
            "name": "Null Modidstrs Mod",
            "summary": "A mod with null modidstrs",
            "author": "author",
            "downloads": 50,
            "follows": 5,
            "trendingpoints": 1,
            "side": "both",
            "type": "mod",
            "logo": None,
            "tags": [],
            "lastreleased": "2024-06-01 00:00:00",
            "urlalias": "nullmod",
            "modidstrs": None,  # Null, not empty!
        }

        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mods": [mod_with_null_modidstrs]},
            )
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        mod = data["data"]["mods"][0]

        # Should fall back to modid as string when modidstrs is null
        assert mod["slug"] == "7654"
        assert mod["urlalias"] == "nullmod"

    @respx.mock
    def test_browse_urlalias_null_when_not_present(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """When urlalias is not set in API response, it should be null."""
        mod_without_urlalias = {
            "modid": 8888,
            "assetid": 5678,
            "name": "No Alias Mod",
            "summary": "A mod without urlalias",
            "author": "author",
            "downloads": 50,
            "follows": 5,
            "trendingpoints": 1,
            "side": "both",
            "type": "mod",
            "logo": None,
            "tags": [],
            "lastreleased": "2024-06-01 00:00:00",
            # No urlalias field
            "modidstrs": ["noaliasmod"],
        }

        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mods": [mod_without_urlalias]},
            )
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        mod = data["data"]["mods"][0]

        assert mod["slug"] == "noaliasmod"
        assert mod["urlalias"] is None

    @respx.mock
    def test_browse_slug_matches_urlalias_when_same(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """When modidstrs[0] matches urlalias, both should have the same value."""
        mod_matching = {
            "modid": 7777,
            "assetid": 4321,
            "name": "Matching Mod",
            "summary": "A mod where slug matches urlalias",
            "author": "author",
            "downloads": 200,
            "follows": 20,
            "trendingpoints": 10,
            "side": "both",
            "type": "mod",
            "logo": None,
            "tags": [],
            "lastreleased": "2025-01-01 00:00:00",
            "urlalias": "matchingmod",
            "modidstrs": ["matchingmod"],  # Same as urlalias
        }

        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mods": [mod_matching]},
            )
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        mod = data["data"]["mods"][0]

        # Both should be the same value
        assert mod["slug"] == "matchingmod"
        assert mod["urlalias"] == "matchingmod"


class TestBrowseModsFilters:
    """Tests for browse endpoint filters: side, mod_type, and tags."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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

    @pytest.fixture
    def diverse_mods(self) -> dict[str, Any]:
        """Return API response with mods of different sides, types, and tags."""
        return {
            "statuscode": "200",
            "mods": [
                {
                    "modid": 1,
                    "name": "Client Only Mod",
                    "side": "client",
                    "type": "mod",
                    "tags": ["UI", "Visual"],
                    "modidstrs": ["clientmod"],
                    "urlalias": "clientmod",
                    "downloads": 100,
                    "follows": 10,
                    "trendingpoints": 5,
                    "lastreleased": "2025-01-01 00:00:00",
                },
                {
                    "modid": 2,
                    "name": "Server Only Mod",
                    "side": "server",
                    "type": "mod",
                    "tags": ["Gameplay", "Balance"],
                    "modidstrs": ["servermod"],
                    "urlalias": "servermod",
                    "downloads": 200,
                    "follows": 20,
                    "trendingpoints": 10,
                    "lastreleased": "2025-01-02 00:00:00",
                },
                {
                    "modid": 3,
                    "name": "Both Sides Mod",
                    "side": "both",
                    "type": "mod",
                    "tags": ["Crafting"],
                    "modidstrs": ["bothmod"],
                    "urlalias": "bothmod",
                    "downloads": 300,
                    "follows": 30,
                    "trendingpoints": 15,
                    "lastreleased": "2025-01-03 00:00:00",
                },
                {
                    "modid": 4,
                    "name": "External Tool",
                    "side": "both",
                    "type": "externaltool",
                    "tags": ["Tools"],
                    "modidstrs": ["externaltool"],
                    "urlalias": "externaltool",
                    "downloads": 50,
                    "follows": 5,
                    "trendingpoints": 2,
                    "lastreleased": "2025-01-04 00:00:00",
                },
            ],
        }

    @respx.mock
    def test_browse_filter_by_side_client(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        diverse_mods: dict[str, Any],
    ) -> None:
        """GET /mods/browse?side=client filters to client-only mods."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=diverse_mods)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?side=client", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        assert len(mods) == 1
        assert mods[0]["slug"] == "clientmod"
        assert mods[0]["side"] == "client"

    @respx.mock
    def test_browse_filter_by_side_server(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        diverse_mods: dict[str, Any],
    ) -> None:
        """GET /mods/browse?side=server filters to server-only mods."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=diverse_mods)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?side=server", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        assert len(mods) == 1
        assert mods[0]["slug"] == "servermod"
        assert mods[0]["side"] == "server"

    @respx.mock
    def test_browse_filter_by_side_both(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        diverse_mods: dict[str, Any],
    ) -> None:
        """GET /mods/browse?side=both filters to both-side mods."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=diverse_mods)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?side=both", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        assert len(mods) == 2
        slugs = {m["slug"] for m in mods}
        assert slugs == {"bothmod", "externaltool"}

    @respx.mock
    def test_browse_filter_by_mod_type(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        diverse_mods: dict[str, Any],
    ) -> None:
        """GET /mods/browse?mod_type=externaltool filters by type."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=diverse_mods)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?mod_type=externaltool", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        assert len(mods) == 1
        assert mods[0]["slug"] == "externaltool"
        assert mods[0]["mod_type"] == "externaltool"

    @respx.mock
    def test_browse_filter_by_tags_single(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        diverse_mods: dict[str, Any],
    ) -> None:
        """GET /mods/browse?tags=Crafting filters by tag."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=diverse_mods)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?tags=Crafting", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        assert len(mods) == 1
        assert mods[0]["slug"] == "bothmod"

    @respx.mock
    def test_browse_filter_by_tags_multiple_or_logic(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        diverse_mods: dict[str, Any],
    ) -> None:
        """GET /mods/browse?tags=UI,Crafting uses OR logic."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=diverse_mods)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?tags=UI,Crafting", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        assert len(mods) == 2
        slugs = {m["slug"] for m in mods}
        assert slugs == {"clientmod", "bothmod"}

    @respx.mock
    def test_browse_filter_tags_with_whitespace(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        diverse_mods: dict[str, Any],
    ) -> None:
        """GET /mods/browse?tags= trims whitespace from tags."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=diverse_mods)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?tags= UI , Crafting ", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        assert len(mods) == 2

    @respx.mock
    def test_browse_filter_tags_empty_after_trim(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        diverse_mods: dict[str, Any],
    ) -> None:
        """GET /mods/browse?tags=,, returns all when tags are empty after trim."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=diverse_mods)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?tags=,,", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        # Should return all mods when tag list is effectively empty
        assert len(mods) == 4

    @respx.mock
    def test_browse_combined_filters(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        diverse_mods: dict[str, Any],
    ) -> None:
        """GET /mods/browse can combine side, mod_type, and tags filters."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=diverse_mods)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?side=both&mod_type=mod&tags=Crafting",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        mods = data["data"]["mods"]
        assert len(mods) == 1
        assert mods[0]["slug"] == "bothmod"


class TestInstallModVersionNotFound:
    """Test install mod with specific version not found."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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
    def test_install_mod_version_not_found(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """POST /mods returns 404 when specific version not found."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )

        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "smithingplus", "version": "99.99.99"},
            headers=admin_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "MOD_VERSION_NOT_FOUND"
        assert "99.99.99" in data["detail"]["message"]

    @respx.mock
    def test_install_mod_download_error(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """POST /mods returns 502 when download fails."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(
                200,
                json={"statuscode": "200", "mod": SMITHINGPLUS_MOD},
            )
        )
        # Mock download to fail
        respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
            side_effect=httpx.ConnectError("download failed")
        )

        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "smithingplus"},
            headers=admin_headers,
        )

        assert response.status_code == 502
        data = response.json()
        assert data["detail"]["code"] == "DOWNLOAD_FAILED"


class TestEnableDisableRemoveInvalidSlug:
    """Test enable/disable/remove with invalid slug."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
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

    def test_enable_mod_invalid_slug(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """POST /mods/{slug}/enable returns 400 for invalid slug."""
        # Use a slug with invalid characters (dots aren't allowed in mod slugs)
        response = client.post(
            "/api/v1alpha1/mods/invalid.slug.with.dots/enable",
            headers=admin_headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_SLUG"

    def test_disable_mod_invalid_slug(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """POST /mods/{slug}/disable returns 400 for invalid slug."""
        # Use a slug with invalid characters
        response = client.post(
            "/api/v1alpha1/mods/invalid.slug.with.dots/disable",
            headers=admin_headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_SLUG"

    def test_remove_mod_invalid_slug(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """DELETE /mods/{slug} returns 400 for invalid slug."""
        # Use a slug with invalid characters
        response = client.delete(
            "/api/v1alpha1/mods/invalid.slug.with.dots",
            headers=admin_headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_SLUG"


class TestGameVersionsParsing:
    """Test game versions endpoint with complex version strings."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path) -> Path:
        """Create temporary data directory structure."""
        data_dir = tmp_path / "data"
        (data_dir / "state").mkdir(parents=True)
        (data_dir / "mods").mkdir(parents=True)
        (data_dir / "cache").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def test_settings(self, temp_data_dir: Path) -> Settings:
        """Create test settings with known API keys."""
        return Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
            debug=True,
        )

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
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI, None, None]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self, test_app: FastAPI) -> TestClient:
        """Create test client with dependency overrides applied."""
        return TestClient(test_app)

    @pytest.fixture
    def admin_headers(self) -> dict[str, str]:
        """Headers with Admin API key."""
        return {"X-API-Key": TEST_ADMIN_KEY}

    @respx.mock
    def test_gameversions_with_rc_versions(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/gameversions handles RC and pre-release versions."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        {"tagid": 1, "name": "1.22.0"},
                        {"tagid": 2, "name": "1.22.0-rc1"},
                        {"tagid": 3, "name": "1.21.3"},
                        {"tagid": 4, "name": "1.21.3-pre5"},
                        {"tagid": 5, "name": "1.21.0"},
                        {"tagid": 6, "name": "alpha-1.20.0"},
                    ],
                },
            )
        )

        response = client.get("/api/v1alpha1/mods/gameversions", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        versions = data["data"]["versions"]

        # Versions should be sorted newest first with proper handling of rc/pre/alpha
        assert len(versions) == 6
        # Exact order depends on the parsing logic, but stable releases should come before pre-releases
        assert "1.22.0" in versions
        assert "1.22.0-rc1" in versions
        assert "1.21.3" in versions
        assert "1.21.3-pre5" in versions

    @respx.mock
    def test_gameversions_with_mixed_format_versions(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/gameversions handles versions with digits followed by suffix."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        {"tagid": 1, "name": "1.22.0"},
                        {"tagid": 2, "name": "1.22.0-1rc1"},  # Digit followed by suffix
                        {"tagid": 3, "name": "1.21.3-2beta"},  # Digit followed by suffix
                        {"tagid": 4, "name": "1.21.0"},
                    ],
                },
            )
        )

        response = client.get("/api/v1alpha1/mods/gameversions", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        versions = data["data"]["versions"]

        # Should handle versions with mixed numeric/text parts
        assert len(versions) == 4
        assert "1.22.0" in versions
        assert "1.22.0-1rc1" in versions
        assert "1.21.3-2beta" in versions
