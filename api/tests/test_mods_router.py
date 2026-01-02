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

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
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
