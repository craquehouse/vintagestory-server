"""Tests for mods router API endpoints."""

import io
import json
import zipfile
from collections.abc import Generator
from datetime import timedelta
from io import StringIO
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
from vintagestory_api.models.moddb import MOD_FIELDS, RELEASE_FIELDS
from vintagestory_api.services.mod_updates import (
    ModUpdateService,
    ModUpdateStore,
    get_mod_update_service,
)
from vintagestory_api.services.mods import (
    ModOperationInProgressError,
    ModService,
    get_mod_service,
)
from vintagestory_api.services.pending_restart import PendingRestartState

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"

BUSY_BODY = {
    "detail": {
        "code": "MOD_OPERATION_IN_PROGRESS",
        "message": (
            "Another operation on mod 'smithingplus' is in progress. "
            "Try again when it has finished."
        ),
    }
}
"""The 409 body every mod operation returns while the mod is busy (Story 17.3, AC 1)."""


def raise_busy(*_args: object, **_kwargs: object) -> object:
    raise ModOperationInProgressError("smithingplus")


def all_null_mod() -> dict[str, Any]:
    """A mod entry or listing item with null in every field the API reads (Story 17.1).

    Built from the normalizer's field tables; one all-null release, `tags` `[None, "Utility"]`.
    """
    mod: dict[str, Any] = {field: None for field in MOD_FIELDS}
    mod["releases"] = [{field: None for field in RELEASE_FIELDS}]
    mod["tags"] = [None, "Utility"]
    return mod


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
    def update_service(self, mod_service: ModService, temp_data_dir: Path) -> ModUpdateService:
        """Update service on the temp directory: install stores records (Story 17.4)."""
        return ModUpdateService(
            store=ModUpdateStore(temp_data_dir / "state"),
            mod_source=mod_service,
            game_version_provider=lambda: "1.21.3",
        )

    @pytest.fixture
    def test_app(
        self, mod_service: ModService, test_settings: Settings, update_service: ModUpdateService
    ) -> Generator[FastAPI]:
        """Create app with test mod service and settings injected."""
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_mod_update_service] = lambda: update_service
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
    def test_install_shows_its_update_status_without_a_check(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Story 17.4 AC 4: the install's own lookup gives the new mod a real status."""
        # SMITHINGPLUS_MOD's release has no modidstr, which would leave the status
        # `installed_release_not_listed`; this lookup's release names its mod ID
        lookup: dict[str, object] = {
            **SMITHINGPLUS_MOD,
            "releases": [
                {
                    "releaseid": 27001,
                    "modversion": "1.8.3",
                    "modidstr": "smithingplus",
                    "filename": "smithingplus_1.8.3.zip",
                    "fileid": 59176,
                    "downloads": 49726,
                    "tags": ["1.21.0", "1.21.1", "1.21.2", "1.21.3"],
                }
            ],
        }
        lookup_route = respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(200, json={"statuscode": "200", "mod": lookup})
        )
        respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
            return_value=Response(
                200,
                content=create_mod_zip_bytes(
                    {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.3"}
                ),
            )
        )

        install = client.post(
            "/api/v1alpha1/mods", json={"slug": "smithingplus"}, headers=admin_headers
        )
        updates = client.get("/api/v1alpha1/mods/updates", headers=admin_headers)

        assert install.status_code == 200
        assert updates.status_code == 200
        items = {m["slug"]: m for m in updates.json()["data"]["mods"]}
        assert items["smithingplus"]["status"] == "up_to_date"
        assert items["smithingplus"].get("reason") is None
        assert items["smithingplus"]["checked_at"] is not None
        # No extra mod database request for the status
        assert lookup_route.call_count == 1

    @respx.mock
    def test_install_succeeds_when_storing_the_update_record_fails(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        temp_data_dir: Path,
        update_service: ModUpdateService,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        """Story 17.4 AC 5: a failed save of the update record does not fail the install.

        The failure is logged as a warning.
        """

        def fail_save() -> None:
            raise OSError("disk full")

        monkeypatch.setattr(update_service.store, "save", fail_save)
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(200, json={"statuscode": "200", "mod": SMITHINGPLUS_MOD})
        )
        respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
            return_value=Response(
                200,
                content=create_mod_zip_bytes(
                    {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.3"}
                ),
            )
        )

        response = client.post(
            "/api/v1alpha1/mods", json={"slug": "smithingplus"}, headers=admin_headers
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "data": {
                "slug": "smithingplus",
                "version": "1.8.3",
                "filename": "smithingplus_1.8.3.zip",
                "compatibility": "compatible",
                "pending_restart": False,
            },
        }
        assert (temp_data_dir / "mods" / "smithingplus_1.8.3.zip").exists()
        assert not (temp_data_dir / "state" / "mod-updates.json").exists()
        warning = next(
            line
            for line in captured_logs.getvalue().splitlines()
            if "mod_update_record_after_install_failed" in line
        )
        assert "warning" in warning
        assert "disk full" in warning
        assert "smithingplus" in warning

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

    @respx.mock
    def test_install_refuses_a_file_name_another_mod_uses(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """Story 18.2 AC 1: 409 MOD_FILE_CONFLICT; the other mod's file is untouched."""
        other = temp_data_dir / "mods" / "smithingplus_1.8.3.zip"
        other.write_bytes(
            create_mod_zip_bytes({"modid": "othermod", "name": "Other", "version": "2.0.0"})
        )
        other_bytes = other.read_bytes()
        mod_service.state_manager.sync_state_with_disk()
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(200, json={"statuscode": "200", "mod": SMITHINGPLUS_MOD})
        )
        respx.get("https://mods.vintagestory.at/download?fileid=59176").mock(
            return_value=Response(
                200,
                content=create_mod_zip_bytes(
                    {"modid": "smithingplus", "name": "Smithing Plus", "version": "1.8.3"}
                ),
            )
        )

        response = client.post(
            "/api/v1alpha1/mods", json={"slug": "smithingplus"}, headers=admin_headers
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": {
                "code": "MOD_FILE_CONFLICT",
                "message": (
                    "Cannot install 'smithingplus': a file named smithingplus_1.8.3.zip "
                    "already exists in the mods directory."
                ),
            }
        }
        assert other.read_bytes() == other_bytes
        installed = client.get("/api/v1alpha1/mods", headers=admin_headers)
        assert [m["slug"] for m in installed.json()["data"]["mods"]] == ["othermod"]
        updates = client.get("/api/v1alpha1/mods/updates", headers=admin_headers)
        assert "smithingplus" not in {m["slug"] for m in updates.json()["data"]["mods"]}
        assert not (temp_data_dir / "state" / "mod-updates.json").exists()

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

    def test_install_busy_mod_returns_409(
        self,
        client: TestClient,
        mod_service: ModService,
        admin_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A mod an install or version change is running for answers 409 (Story 17.3)."""
        monkeypatch.setattr(mod_service, "install_mod", raise_busy)

        response = client.post(
            "/api/v1alpha1/mods", json={"slug": "smithingplus"}, headers=admin_headers
        )

        assert response.status_code == 409
        assert response.json() == BUSY_BODY


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
    ) -> Generator[FastAPI]:
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
        assert data["data"]["compatibility"]["latest_supported_game_version"] == "1.21.3"

    @respx.mock
    def test_lookup_mod_version_evaluates_that_release(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/lookup/{slug}?version= reports that release's compatibility (Story 16.3)."""
        mod = {
            **SMITHINGPLUS_MOD,
            "releases": [
                {
                    "releaseid": 27001,
                    "modversion": "1.8.3",
                    "modidstr": "smithingplus",
                    "filename": "smithingplus_1.8.3.zip",
                    "fileid": 59176,
                    "downloads": 49726,
                    "tags": ["1.21.3"],
                },
            ],
        }
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(200, json={"statuscode": "200", "mod": mod})
        )

        response = client.get(
            "/api/v1alpha1/mods/lookup/smithingplus",
            params={"version": "1.0.0"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        compatibility = response.json()["data"]["compatibility"]
        assert compatibility["status"] == "not_verified"
        assert compatibility["mod_version"] == "1.0.0"
        assert "not listed" in compatibility["message"]

    def test_lookup_mod_rejects_empty_version(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """GET /mods/lookup/{slug}?version= with an empty version is a validation error."""
        response = client.get(
            "/api/v1alpha1/mods/lookup/smithingplus",
            params={"version": ""},
            headers=admin_headers,
        )

        assert response.status_code == 422

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

    @respx.mock
    def test_lookup_mod_with_releases_without_a_file(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A mod with `"fileid": null` releases opens: 200, file_id null (Story 17.1, VSS-a0r)."""
        payload = json.loads((FIXTURES / "mod_canjewelry.json").read_text())
        respx.get("https://mods.vintagestory.at/api/mod/canjewelry").mock(
            return_value=Response(200, json=payload)
        )

        response = client.get("/api/v1alpha1/mods/lookup/canjewelry", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        raw_releases = payload["mod"]["releases"]
        assert len(data["releases"]) == len(raw_releases)
        assert [r["version"] for r in data["releases"]] == [
            r["modversion"] for r in raw_releases
        ]
        assert [r["version"] for r in data["releases"] if r["file_id"] is None] == [
            "0.2.20",
            "0.1.26",
            "0.2.0",
        ]
        for release, raw in zip(data["releases"], raw_releases, strict=True):
            assert release["file_id"] == raw["fileid"]
        changelogs = {r["version"]: r["changelog"] for r in data["releases"]}
        assert changelogs["0.3.7"] is None
        assert data["tags"] == ["Utility", "Cosmetics", "Crafting"]

    @respx.mock
    def test_lookup_mod_with_null_in_every_field(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """An entry with null in every field looks up with the defaults (Story 17.1)."""
        respx.get("https://mods.vintagestory.at/api/mod/allnull").mock(
            return_value=Response(200, json={"statuscode": "200", "mod": all_null_mod()})
        )

        response = client.get("/api/v1alpha1/mods/lookup/allnull", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["slug"] == "allnull"
        assert data["name"] == "allnull"
        assert data["author"] == "Unknown"
        assert data["side"] == "Both"
        assert data["asset_id"] == 0
        assert data["follows"] == 0
        assert data["downloads"] == 0
        assert data["tags"] == ["Utility"]
        # Story 17.2: the only release has no file and an empty mod ID
        assert data["latest_version"] is None
        assert data["install_mod_id"] == ""
        assert data["releases"] == [
            {
                "version": "unknown",
                "filename": "",
                "file_id": None,
                "downloads": 0,
                "game_versions": [],
                "created": "",
                "changelog": None,
                "modidstr": "",
            }
        ]


    @respx.mock
    @pytest.mark.parametrize(
        ("fixture", "slug", "install_mod_id", "latest_version"),
        [
            ("instruments", "instruments", "instruments", "1.2.2"),
            ("instruments", "vsinstruments", "vsinstruments", "1.2.7"),
            ("carryon", "carryon", "carryon", "1.14.3"),
            ("egocaribautomapmarkers", "automapmarkers", "egocaribautomapmarkers", "5.0.3"),
            ("canjewelry", "canjewelry", "canjewelry", "0.8.2"),
        ],
    )
    def test_lookup_reports_what_install_picks(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        fixture: str,
        slug: str,
        install_mod_id: str,
        latest_version: str,
    ) -> None:
        """Story 17.2: install_mod_id and latest_version are what a plain install picks."""
        respx.get(f"https://mods.vintagestory.at/api/mod/{slug}").mock(
            return_value=Response(
                200, json=json.loads((FIXTURES / f"mod_{fixture}.json").read_text())
            )
        )

        response = client.get(f"/api/v1alpha1/mods/lookup/{slug}", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["install_mod_id"] == install_mod_id
        assert data["latest_version"] == latest_version
        if slug == "carryon":
            # Compatibility still describes the newest release (Epic 16 ADR-2)
            assert data["compatibility"]["mod_version"] == "2.0.0-rc.1"

    @respx.mock
    def test_lookup_mod_id_without_a_file_has_null_latest_version(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Story 17.2: no release of the install mod ID has a file: 200, null."""
        mod = {
            "modid": 9997,
            "name": "No File",
            "modidstrs": ["nofile"],
            "releases": [
                {"modversion": v, "modidstr": "nofile", "fileid": None, "filename": ""}
                for v in ("2.0.0", "1.0.0")
            ],
        }
        respx.get("https://mods.vintagestory.at/api/mod/nofile").mock(
            return_value=Response(200, json={"statuscode": "200", "mod": mod})
        )

        response = client.get("/api/v1alpha1/mods/lookup/nofile", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["install_mod_id"] == "nofile"
        assert data["latest_version"] is None

    @staticmethod
    def betterruins() -> dict[str, Any]:
        payload: dict[str, Any] = json.loads((FIXTURES / "mod_betterruins.json").read_text())
        return payload

    @respx.mock
    def test_lookup_mod_screenshots_and_trailer(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Story 18.1: screenshots with exactly three keys, and the trailer watch URL."""
        payload = self.betterruins()
        respx.get("https://mods.vintagestory.at/api/mod/betterruins").mock(
            return_value=Response(200, json=payload)
        )

        response = client.get("/api/v1alpha1/mods/lookup/betterruins", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        raw = payload["mod"]["screenshots"]
        assert isinstance(data["screenshots"], list)
        assert len(data["screenshots"]) == len(raw)
        for item, raw_item in zip(data["screenshots"], raw, strict=True):
            assert set(item) == {"image_url", "thumbnail_url", "filename"}
            assert item["image_url"] == raw_item["mainfile"]
        assert data["trailer_url"] == "https://www.youtube-nocookie.com/embed/mJHZH_sThDM"

    @respx.mock
    def test_lookup_mod_bad_media_is_filtered(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Story 18.1: bad screenshots are left out and a bad trailer is null; still 200."""
        payload = self.betterruins()
        good = payload["mod"]["screenshots"][0]
        payload["mod"]["screenshots"] = [
            {"mainfile": "https://i.imgur.com/x.png"},
            None,
            {**good, "thumbnailfilename": "http://moddbcdn.vintagestory.at/x.jpg"},
        ]
        payload["mod"]["trailervideourl"] = "https://apachegaming.net"
        respx.get("https://mods.vintagestory.at/api/mod/betterruins").mock(
            return_value=Response(200, json=payload)
        )

        response = client.get("/api/v1alpha1/mods/lookup/betterruins", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["screenshots"] == [
            {
                "image_url": good["mainfile"],
                "thumbnail_url": good["mainfile"],
                "filename": good["filename"],
            }
        ]
        assert data["trailer_url"] is None

    @respx.mock
    def test_lookup_mod_without_media_has_the_keys(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Story 18.1: an entry without either key gives `[]` and null, keys present."""
        payload = json.loads((FIXTURES / "mod_carryon.json").read_text())
        respx.get("https://mods.vintagestory.at/api/mod/carryon").mock(
            return_value=Response(200, json=payload)
        )

        response = client.get("/api/v1alpha1/mods/lookup/carryon", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["screenshots"] == []
        assert "trailer_url" in data
        assert data["trailer_url"] is None


    @respx.mock
    def test_lookup_drops_unchecked_urls(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Logo, homepage and source URLs that are not allowed are null (Story 19.6)."""
        mod = {
            **SMITHINGPLUS_MOD,
            "logofilename": "http://moddbcdn.vintagestory.at/x.png",
            "homepageurl": "javascript:alert(1)",
            "sourcecodeurl": "",
        }
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(200, json={"statuscode": "200", "mod": mod})
        )

        response = client.get("/api/v1alpha1/mods/lookup/smithingplus", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["logo_url"] is None
        assert data["homepage_url"] is None
        assert data["source_url"] is None

    @respx.mock
    def test_lookup_keeps_checked_urls(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A CDN logo and https links are returned unchanged (Story 19.6)."""
        mod = {
            **SMITHINGPLUS_MOD,
            "logofilename": "https://moddbcdn.vintagestory.at/x.png",
            "homepageurl": "https://example.com/home",
            "sourcecodeurl": "https://github.com/a/b",
        }
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            return_value=Response(200, json={"statuscode": "200", "mod": mod})
        )

        response = client.get("/api/v1alpha1/mods/lookup/smithingplus", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["logo_url"] == "https://moddbcdn.vintagestory.at/x.png"
        assert data["homepage_url"] == "https://example.com/home"
        assert data["source_url"] == "https://github.com/a/b"


    @respx.mock
    def test_lookup_malformed_body_is_502_then_recovers(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A lookup answered with JSON null is 502; a good answer then works (Story 19.6)."""
        respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
            side_effect=[
                Response(200, content=b"null"),
                Response(200, json={"statuscode": "200", "mod": SMITHINGPLUS_MOD}),
            ]
        )

        response = client.get("/api/v1alpha1/mods/lookup/smithingplus", headers=admin_headers)
        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "EXTERNAL_API_ERROR"

        response = client.get("/api/v1alpha1/mods/lookup/smithingplus", headers=admin_headers)
        assert response.status_code == 200


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
    ) -> Generator[FastAPI]:
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

    def test_enable_busy_mod_returns_409(
        self,
        client: TestClient,
        mod_service: ModService,
        admin_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A mod an install or version change is running for answers 409 (Story 17.3)."""
        monkeypatch.setattr(mod_service, "enable_mod", raise_busy)

        response = client.post("/api/v1alpha1/mods/smithingplus/enable", headers=admin_headers)

        assert response.status_code == 409
        assert response.json() == BUSY_BODY

    def test_enable_with_a_file_in_the_way_returns_409(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """A file with the enabled name is never replaced (Story 19.4 AC 1, FR218)."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "testmod_1.0.0.zip.disabled",
            {"modid": "testmod", "name": "Test", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()
        stray = mods_dir / "testmod_1.0.0.zip"
        stray.write_bytes(b"stray bytes")
        listing = client.get("/api/v1alpha1/mods", headers=admin_headers).json()

        response = client.post("/api/v1alpha1/mods/testmod/enable", headers=admin_headers)

        assert response.status_code == 409
        assert response.json() == {
            "detail": {
                "code": "MOD_FILE_CONFLICT",
                "message": (
                    "Cannot enable 'testmod': a file named testmod_1.0.0.zip "
                    "already exists in the mods directory."
                ),
            }
        }
        assert stray.read_bytes() == b"stray bytes"
        assert sorted(p.name for p in mods_dir.iterdir()) == [
            "testmod_1.0.0.zip",
            "testmod_1.0.0.zip.disabled",
        ]
        assert client.get("/api/v1alpha1/mods", headers=admin_headers).json() == listing


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
    ) -> Generator[FastAPI]:
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

    def test_disable_busy_mod_returns_409(
        self,
        client: TestClient,
        mod_service: ModService,
        admin_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A mod an install or version change is running for answers 409 (Story 17.3)."""
        monkeypatch.setattr(mod_service, "disable_mod", raise_busy)

        response = client.post("/api/v1alpha1/mods/smithingplus/disable", headers=admin_headers)

        assert response.status_code == 409
        assert response.json() == BUSY_BODY

    def test_disable_with_a_file_in_the_way_returns_409(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
    ) -> None:
        """A file with the disabled name is never replaced (Story 19.4 AC 2, FR218)."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / "testmod_1.0.0.zip",
            {"modid": "testmod", "name": "Test", "version": "1.0.0"},
        )
        mod_service.state_manager.sync_state_with_disk()
        stray = mods_dir / "testmod_1.0.0.zip.disabled"
        stray.write_bytes(b"stray bytes")
        listing = client.get("/api/v1alpha1/mods", headers=admin_headers).json()

        response = client.post("/api/v1alpha1/mods/testmod/disable", headers=admin_headers)

        assert response.status_code == 409
        assert response.json() == {
            "detail": {
                "code": "MOD_FILE_CONFLICT",
                "message": (
                    "Cannot disable 'testmod': a file named testmod_1.0.0.zip.disabled "
                    "already exists in the mods directory."
                ),
            }
        }
        assert stray.read_bytes() == b"stray bytes"
        assert sorted(p.name for p in mods_dir.iterdir()) == [
            "testmod_1.0.0.zip",
            "testmod_1.0.0.zip.disabled",
        ]
        assert client.get("/api/v1alpha1/mods", headers=admin_headers).json() == listing

    @pytest.mark.parametrize(
        ("action", "on_disk"),
        [("disable", "testmod_1.0.0.zip"), ("enable", "testmod_1.0.0.zip.disabled")],
    )
    def test_a_mod_whose_file_is_gone_returns_409_and_can_be_removed(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mod_service: ModService,
        temp_data_dir: Path,
        action: str,
        on_disk: str,
    ) -> None:
        """Story 19.4 AC 13, 14 (FR222): never a 500; the mod can still be removed."""
        mods_dir = temp_data_dir / "mods"
        create_mod_zip_file(
            mods_dir / on_disk, {"modid": "testmod", "name": "Test", "version": "1.0.0"}
        )
        mod_service.state_manager.sync_state_with_disk()
        (mods_dir / on_disk).unlink()
        listing = client.get("/api/v1alpha1/mods", headers=admin_headers).json()

        response = client.post(f"/api/v1alpha1/mods/testmod/{action}", headers=admin_headers)

        assert response.status_code == 409
        assert response.json() == {
            "detail": {
                "code": "MOD_FILE_MISSING",
                "message": (
                    f"Cannot {action} 'testmod': its file {on_disk} is no longer in the mods "
                    "directory. Remove the mod and install it again."
                ),
            }
        }
        assert client.get("/api/v1alpha1/mods", headers=admin_headers).json() == listing
        removed = client.delete("/api/v1alpha1/mods/testmod", headers=admin_headers)
        assert removed.status_code == 200
        assert mod_service.state_manager.get_mod_by_slug("testmod") is None


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
    ) -> Generator[FastAPI]:
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

    def test_remove_busy_mod_returns_409(
        self,
        client: TestClient,
        mod_service: ModService,
        admin_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A mod an install or version change is running for answers 409 (Story 17.3)."""
        monkeypatch.setattr(mod_service, "remove_mod", raise_busy)

        response = client.delete("/api/v1alpha1/mods/smithingplus", headers=admin_headers)

        assert response.status_code == 409
        assert response.json() == BUSY_BODY


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
    ) -> Generator[FastAPI]:
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

BROWSE_VERSION_LIST: dict[str, Any] = {
    "statuscode": "200",
    "gameversions": [{"tagid": -281565171286015, "name": "1.21.3", "color": "#CCCCCC"}],
}

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
            # No server installed: no game version flags (Story 18.3 tests them)
            game_version_provider=lambda: None,
        )

    @pytest.fixture
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI]:
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
    def test_browse_mods_sort_by_name_pages_through_alphabetical_order(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Story 16.8: sort=name pages through the whole alphabetical list."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        response = client.get(
            "/api/v1alpha1/mods/browse?sort=name&page=2&page_size=2",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        # Old Popular Mod, Smithing Plus | Trending New Mod
        assert [m["slug"] for m in data["mods"]] == ["trendingnew"]
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["total_items"] == 3
        assert data["pagination"]["total_pages"] == 2
        assert data["pagination"]["has_prev"] is True
        assert data["pagination"]["has_next"] is False

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
    def test_browse_mods_serves_the_last_page_for_a_page_beyond_the_results(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A page beyond the results gets exactly the last page's response.

        Story 17.7: the web stores this response as the last page, so moving the
        URL there needs no second request.
        """
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=BROWSE_MODS_API_RESPONSE)
        )

        beyond = client.get(
            "/api/v1alpha1/mods/browse?page=100&page_size=1&sort=downloads",
            headers=admin_headers,
        )
        last = client.get(
            "/api/v1alpha1/mods/browse?page=3&page_size=1&sort=downloads",
            headers=admin_headers,
        )

        assert beyond.status_code == 200
        assert last.status_code == 200
        beyond_data = beyond.json()["data"]
        assert beyond_data == last.json()["data"]
        assert beyond_data["pagination"]["page"] == 3
        assert beyond_data["pagination"]["has_prev"] is True
        assert beyond_data["pagination"]["has_next"] is False
        assert len(beyond_data["mods"]) == 1

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


    @respx.mock
    def test_browse_drops_logos_not_on_the_cdn(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Only https logos on the mod database CDN reach the page (Story 19.6)."""
        base = BROWSE_MODS_API_RESPONSE["mods"][0]
        logos = [
            "https://moddbcdn.vintagestory.at/a/logo.png",
            "http://moddbcdn.vintagestory.at/b/logo.png",
            "https://i.imgur.com/c.png",
            None,
        ]
        listing = {
            "statuscode": "200",
            "mods": [
                {**base, "modid": 100 + i, "modidstrs": [f"mod{i}"], "logo": logo}
                for i, logo in enumerate(logos)
            ],
        }
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=listing)
        )

        response = client.get("/api/v1alpha1/mods/browse?sort=name", headers=admin_headers)

        assert response.status_code == 200
        by_slug = {m["slug"]: m["logo_url"] for m in response.json()["data"]["mods"]}
        assert by_slug == {
            "mod0": "https://moddbcdn.vintagestory.at/a/logo.png",
            "mod1": None,
            "mod2": None,
            "mod3": None,
        }


    @respx.mock
    def test_browse_malformed_listing_is_502_then_recovers(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A listing that is not a JSON object is 502, never 500; a good one then works
        (Story 19.6, FR226)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            side_effect=[
                Response(200, content=b"[]"),
                Response(200, content=b"<html>Not JSON</html>"),
                Response(200, json=BROWSE_MODS_API_RESPONSE),
            ]
        )

        for _ in range(2):
            response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)
            assert response.status_code == 502
            assert response.json()["detail"]["code"] == "EXTERNAL_API_ERROR"

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()["data"]["mods"]) == 3

    @respx.mock
    def test_browse_version_malformed_version_list_is_502(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A game version list that is a JSON string is 502 (Story 19.6, FR226)."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            side_effect=[
                Response(200, content=b'"text"'),
                Response(200, json=BROWSE_VERSION_LIST),
            ]
        )
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": "-281565171286015"},
        ).mock(return_value=Response(200, json=BROWSE_MODS_API_RESPONSE))

        response = client.get("/api/v1alpha1/mods/browse?version=1.21.3", headers=admin_headers)
        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "EXTERNAL_API_ERROR"

        response = client.get("/api/v1alpha1/mods/browse?version=1.21.3", headers=admin_headers)
        assert response.status_code == 200

    @respx.mock
    def test_browse_version_malformed_filtered_listing_is_502(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A filtered listing that is JSON null is 502, never 500 (Story 19.6, FR226)."""
        respx.get("https://mods.vintagestory.at/api/gameversions").mock(
            return_value=Response(200, json=BROWSE_VERSION_LIST)
        )
        respx.get(
            "https://mods.vintagestory.at/api/mods",
            params={"gameversion": "-281565171286015"},
        ).mock(
            side_effect=[
                Response(200, content=b"null"),
                Response(200, json=BROWSE_MODS_API_RESPONSE),
            ]
        )

        response = client.get("/api/v1alpha1/mods/browse?version=1.21.3", headers=admin_headers)
        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "EXTERNAL_API_ERROR"

        response = client.get("/api/v1alpha1/mods/browse?version=1.21.3", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()["data"]["mods"]) == 3


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
    ) -> Generator[FastAPI]:
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
    ) -> Generator[FastAPI]:
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


    @respx.mock
    def test_list_mod_tags_malformed_listing_is_502(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A listing that is a JSON array is 502, never 500 (Story 19.6, FR226)."""
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            side_effect=[
                Response(200, content=b"[]"),
                Response(200, json=BROWSE_MODS_API_RESPONSE),
            ]
        )

        response = client.get("/api/v1alpha1/mods/tags", headers=admin_headers)
        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "EXTERNAL_API_ERROR"

        response = client.get("/api/v1alpha1/mods/tags", headers=admin_headers)
        assert response.status_code == 200


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
            # No server installed: no game version flags (Story 18.3 tests them)
            game_version_provider=lambda: None,
        )

    @pytest.fixture
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI]:
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

    @respx.mock
    @pytest.mark.parametrize(
        ("modidstrs", "expected_slug", "expected_mod_ids"),
        [
            (
                ["instruments", "vsinstruments", "vsinstrumentsbase"],
                "instruments",
                ["instruments", "vsinstruments", "vsinstrumentsbase"],
            ),
            (["a", "", "a", "b"], "a", ["a", "b"]),
            ([], "4321", []),
        ],
    )
    def test_browse_item_lists_every_mod_id(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        modidstrs: list[str],
        expected_slug: str,
        expected_mod_ids: list[str],
    ) -> None:
        """Story 17.4: `mod_ids` holds the listing's `modidstrs`, in order, each once.

        Empty strings are dropped; the slug is unchanged (`modidstrs[0]`, or the
        existing fallback for an entry with no mod IDs).
        """
        listing_mod: dict[str, Any] = {
            "modid": 4321,
            "assetid": 1234,
            "name": "Instruments",
            "summary": "Play music",
            "author": "author",
            "downloads": 50,
            "follows": 5,
            "trendingpoints": 1,
            "side": "both",
            "type": "mod",
            "logo": None,
            "tags": [],
            "lastreleased": "2024-06-01 00:00:00",
            "urlalias": "instruments",
            "modidstrs": modidstrs,
        }
        listing_route = respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json={"statuscode": "200", "mods": [listing_mod]})
        )

        response = client.get("/api/v1alpha1/mods/browse", headers=admin_headers)

        assert response.status_code == 200
        mod = response.json()["data"]["mods"][0]
        assert mod["slug"] == expected_slug
        assert mod["mod_ids"] == expected_mod_ids
        # No request per mod: the listing is the only mocked route, and respx
        # refuses any request that is not mocked
        assert listing_route.call_count == 1
        assert len(respx.calls) == 1


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
            # No server installed: no game version flags (Story 18.3 tests them)
            game_version_provider=lambda: None,
        )

    @pytest.fixture
    def test_app(
        self, mod_service: ModService, test_settings: Settings
    ) -> Generator[FastAPI]:
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
    ) -> Generator[FastAPI]:
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
    @pytest.mark.parametrize(
        ("fixture", "slug", "version"),
        [
            # 2.0.7 exists only under vsinstrumentsbase, another mod ID of the entry
            ("instruments", "instruments", "2.0.7"),
            # The web used to send the string "latest" as a version name
            ("carryon", "carryon", "latest"),
        ],
    )
    def test_install_version_the_mod_id_does_not_have_is_not_found(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        temp_data_dir: Path,
        mod_service: ModService,
        fixture: str,
        slug: str,
        version: str,
    ) -> None:
        """Story 17.2: only releases of the requested mod ID are considered."""
        respx.get(f"https://mods.vintagestory.at/api/mod/{slug}").mock(
            return_value=Response(
                200, json=json.loads((FIXTURES / f"mod_{fixture}.json").read_text())
            )
        )
        download = respx.get("https://mods.vintagestory.at/download").mock(
            return_value=Response(200, content=b"zip")
        )

        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": slug, "version": version},
            headers=admin_headers,
        )

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "MOD_VERSION_NOT_FOUND"
        assert not download.called
        assert list((temp_data_dir / "mods").iterdir()) == []
        assert mod_service.state_manager.list_mods() == []

    @respx.mock
    def test_install_release_without_a_file_is_refused(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        temp_data_dir: Path,
        mod_service: ModService,
    ) -> None:
        """Story 17.2: a named release without a file is a 422, nothing downloaded."""
        respx.get("https://mods.vintagestory.at/api/mod/canjewelry").mock(
            return_value=Response(
                200, json=json.loads((FIXTURES / "mod_canjewelry.json").read_text())
            )
        )
        download = respx.get("https://mods.vintagestory.at/download").mock(
            return_value=Response(200, content=b"zip")
        )

        response = client.post(
            "/api/v1alpha1/mods",
            json={"slug": "canjewelry", "version": "0.2.20"},
            headers=admin_headers,
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == "MOD_RELEASE_NOT_DOWNLOADABLE"
        assert detail["message"] == (
            "Version '0.2.20' of mod 'canjewelry' has no downloadable file in the mod database"
        )
        assert not download.called
        assert list((temp_data_dir / "mods").iterdir()) == []
        assert mod_service.state_manager.list_mods() == []

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
    ) -> Generator[FastAPI]:
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
    ) -> Generator[FastAPI]:
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
        # Exact order depends on the parsing logic,
        # but stable releases should come before pre-releases
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


def bad_data_listing() -> dict[str, Any]:
    """A `/api/mods` listing with incomplete data (Story 17.1, Epic 17 ADR-1).

    Holds an item with null in every field, an item with a null inside `tags` and
    `modidstrs`, a null element, a string element and one complete item.
    """
    return {
        "statuscode": "200",
        "mods": [
            {field: None for field in MOD_FIELDS},
            {
                "modid": 4242,
                "assetid": 9001,
                "name": "Quality Tweaks",
                "summary": "Small tweaks",
                "author": "someone",
                "downloads": 10,
                "follows": 1,
                "trendingpoints": 2,
                "side": "both",
                "type": "mod",
                "logo": None,
                "tags": ["QoL", None],
                "lastreleased": "2025-06-01 10:00:00",
                "urlalias": None,
                "modidstrs": [None, "qolmod"],
            },
            None,
            "oops",
            BROWSE_MODS_API_RESPONSE["mods"][2],
        ],
    }


class TestBrowseWithIncompleteModData:
    """Browse, filters, search and the tag list read normalized data (Story 17.1)."""

    @pytest.fixture
    def client(self, tmp_path: Path) -> Generator[TestClient]:
        data_dir = tmp_path / "data"
        for sub in ("state", "mods", "cache"):
            (data_dir / sub).mkdir(parents=True)
        settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=data_dir,
            debug=True,
        )
        service = ModService(
            state_dir=data_dir / "state",
            mods_dir=data_dir / "mods",
            cache_dir=data_dir / "cache",
            restart_state=PendingRestartState(),
            # No server installed: no game version flags (Story 18.3 tests them)
            game_version_provider=lambda: None,
        )
        app.dependency_overrides[get_mod_service] = lambda: service
        app.dependency_overrides[get_settings] = lambda: settings
        yield TestClient(app)
        app.dependency_overrides.clear()

    @pytest.fixture
    def headers(self) -> dict[str, str]:
        return {"X-API-Key": TEST_ADMIN_KEY}

    def browse(self, client: TestClient, headers: dict[str, str], query: str) -> dict[str, Any]:
        response = client.get(f"/api/v1alpha1/mods/browse{query}", headers=headers)
        assert response.status_code == 200
        return response.json()["data"]

    @respx.mock
    @pytest.mark.parametrize("sort", ["recent", "downloads", "trending", "name"])
    def test_every_sort_succeeds_with_defaults(
        self, client: TestClient, headers: dict[str, str], sort: str
    ) -> None:
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=bad_data_listing())
        )

        data = self.browse(client, headers, f"?sort={sort}")

        assert data["pagination"]["total_items"] == 3
        by_slug = {m["slug"]: m for m in data["mods"]}
        assert set(by_slug) == {"unknown", "qolmod", "trendingnew"}
        assert by_slug["unknown"] == {
            "slug": "unknown",
            "mod_ids": [],
            "urlalias": None,
            "asset_id": 0,
            "name": "",
            "author": "",
            "summary": None,
            "downloads": 0,
            "follows": 0,
            "trending_points": 0,
            "side": "both",
            "mod_type": "mod",
            "logo_url": None,
            "tags": [],
            "last_released": None,
            "has_release_for_game_version": None,
        }
        assert by_slug["qolmod"]["tags"] == ["QoL"]

    @respx.mock
    def test_side_and_type_filters_match_the_cards(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=bad_data_listing())
        )

        both = self.browse(client, headers, "?side=both")
        mods = self.browse(client, headers, "?mod_type=mod")

        assert {m["slug"] for m in both["mods"]} == {"unknown", "qolmod"}
        assert {m["slug"] for m in mods["mods"]} == {"unknown", "qolmod", "trendingnew"}

    @respx.mock
    def test_unrecognized_side_and_type_match_the_default_filters(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        odd = {
            **BROWSE_MODS_API_RESPONSE["mods"][2],
            "side": "sideways",
            "type": "weird",
            "modidstrs": ["oddmod"],
        }
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json={"statuscode": "200", "mods": [odd]})
        )

        for query in ("?side=both", "?mod_type=mod"):
            cards = self.browse(client, headers, query)["mods"]
            assert [(m["slug"], m["side"], m["mod_type"]) for m in cards] == [
                ("oddmod", "both", "mod")
            ]
        assert self.browse(client, headers, "?side=client")["mods"] == []
        assert self.browse(client, headers, "?mod_type=externaltool")["mods"] == []

    @respx.mock
    def test_tag_filter(self, client: TestClient, headers: dict[str, str]) -> None:
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=bad_data_listing())
        )

        data = self.browse(client, headers, "?tags=qol")

        assert [(m["slug"], m["tags"]) for m in data["mods"]] == [("qolmod", ["QoL"])]

    @respx.mock
    def test_search(self, client: TestClient, headers: dict[str, str]) -> None:
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=bad_data_listing())
        )

        by_name = self.browse(client, headers, "?search=tweaks")
        by_tag = self.browse(client, headers, "?search=ui")

        assert [m["slug"] for m in by_name["mods"]] == ["qolmod"]
        assert [m["slug"] for m in by_tag["mods"]] == ["trendingnew"]

    @respx.mock
    def test_tag_list_has_no_null(self, client: TestClient, headers: dict[str, str]) -> None:
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=bad_data_listing())
        )

        response = client.get("/api/v1alpha1/mods/tags", headers=headers)

        assert response.status_code == 200
        assert response.json()["data"]["tags"] == ["qol", "ui"]

    @respx.mock
    @pytest.mark.parametrize(
        "listing", [{"statuscode": "200", "mods": None}, {"statuscode": "200"}]
    )
    def test_listing_without_mods_is_502(
        self, client: TestClient, headers: dict[str, str], listing: dict[str, Any]
    ) -> None:
        respx.get("https://mods.vintagestory.at/api/mods").mock(
            return_value=Response(200, json=listing)
        )

        browse = client.get("/api/v1alpha1/mods/browse", headers=headers)
        tags = client.get("/api/v1alpha1/mods/tags", headers=headers)

        assert browse.status_code == 502
        assert tags.status_code == 502


# --- Story 18.3: game version flag on browse items ---

MODS_URL = "https://mods.vintagestory.at/api/mods"
GAMEVERSIONS_URL = "https://mods.vintagestory.at/api/gameversions"
TAG_1_22_7 = -7
TAG_1_21_3 = -3
TAG_1_22_8 = -8


def flag_listing(*modids: int) -> dict[str, Any]:
    """A mod database listing with one entry per mod ID (`m<id>` as its mod ID string)."""
    return {
        "statuscode": "200",
        "mods": [
            {
                "modid": i,
                "modidstrs": [f"m{i}"],
                "name": f"Mod {i}",
                "urlalias": f"m{i}",
                "downloads": 100 - i,
            }
            for i in modids
        ],
    }


FLAG_VERSIONS = {
    "statuscode": "200",
    "gameversions": [
        {"tagid": TAG_1_22_7, "name": "1.22.7", "color": "#CCCCCC"},
        {"tagid": TAG_1_21_3, "name": "1.21.3", "color": "#CCCCCC"},
        {"tagid": TAG_1_22_8, "name": "1.22.8", "color": "#CCCCCC"},
    ],
}


def filtered_route(tagid: int) -> respx.Route:
    """The route for the listing filtered by a tag; register before the plain listing."""
    return respx.get(MODS_URL, params={"gameversion": str(tagid)})


class TestBrowseGameVersionFlag:
    """GET /mods/browse reports whether each entry has a release for the installed version."""

    @pytest.fixture
    def installed(self) -> dict[str, str | None]:
        """The installed game version; tests change it."""
        return {"version": "1.22.7"}

    @pytest.fixture
    def mod_service(self, tmp_path: Path, installed: dict[str, str | None]) -> ModService:
        data_dir = tmp_path / "data"
        for sub in ("state", "mods", "cache"):
            (data_dir / sub).mkdir(parents=True)
        return ModService(
            state_dir=data_dir / "state",
            mods_dir=data_dir / "mods",
            cache_dir=data_dir / "cache",
            restart_state=PendingRestartState(),
            game_version_provider=lambda: installed["version"],
        )

    @pytest.fixture
    def client(self, tmp_path: Path, mod_service: ModService) -> Generator[TestClient]:
        settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=tmp_path / "data",
            debug=True,
        )
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        app.dependency_overrides[get_settings] = lambda: settings
        yield TestClient(app)
        app.dependency_overrides.clear()

    def browse(self, client: TestClient, query: str = "") -> dict[str, Any]:
        response = client.get(
            f"/api/v1alpha1/mods/browse{query}", headers={"X-API-Key": TEST_ADMIN_KEY}
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]

    @staticmethod
    def flags(data: dict[str, Any]) -> dict[str, bool | None]:
        return {m["slug"]: m["has_release_for_game_version"] for m in data["mods"]}

    @respx.mock
    @pytest.mark.parametrize("installed_version", ["1.22.7", "v1.22.7"])
    def test_true_and_false(
        self,
        client: TestClient,
        installed: dict[str, str | None],
        installed_version: str,
    ) -> None:
        """Items in the filtered listing are true, the others false (AC 1); a v prefix is
        stripped."""
        installed["version"] = installed_version
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))
        filtered = filtered_route(TAG_1_22_7).mock(
            return_value=Response(200, json=flag_listing(1))
        )
        plain = respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1, 2, 3)))

        data = self.browse(client)

        assert data["game_version"] == "1.22.7"
        assert self.flags(data) == {"m1": True, "m2": False, "m3": False}
        assert filtered.call_count == 1
        assert plain.call_count == 1

    @respx.mock
    def test_one_filtered_request_for_many_browse_requests(self, client: TestClient) -> None:
        """Pages, sorts and searches share one filtered listing request; no per-mod request
        (AC 2). respx fails any request to /api/mod/<slug>, which has no route."""
        versions = respx.get(GAMEVERSIONS_URL).mock(
            return_value=Response(200, json=FLAG_VERSIONS)
        )
        filtered = filtered_route(TAG_1_22_7).mock(
            return_value=Response(200, json=flag_listing(1))
        )
        plain = respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1, 2, 3)))

        page_1 = self.browse(client, "?page=1&page_size=2&sort=downloads")
        page_2 = self.browse(client, "?page=2&page_size=2&sort=downloads")
        by_name = self.browse(client, "?sort=name")
        searched = self.browse(client, "?search=Mod%201")

        assert self.flags(page_1) == {"m1": True, "m2": False}
        assert self.flags(page_2) == {"m3": False}
        assert self.flags(by_name) == {"m1": True, "m2": False, "m3": False}
        assert self.flags(searched) == {"m1": True}
        assert filtered.call_count == 1
        assert versions.call_count == 1
        assert plain.call_count == 1

    @respx.mock
    def test_no_server_installed(
        self, client: TestClient, installed: dict[str, str | None]
    ) -> None:
        """No server: game_version and every flag null, no version list or filtered request
        (AC 4)."""
        installed["version"] = None
        versions = respx.get(GAMEVERSIONS_URL).mock(
            return_value=Response(200, json=FLAG_VERSIONS)
        )
        filtered = filtered_route(TAG_1_22_7).mock(
            return_value=Response(200, json=flag_listing(1))
        )
        respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1, 2)))

        data = self.browse(client)

        assert data["game_version"] is None
        assert self.flags(data) == {"m1": None, "m2": None}
        assert versions.call_count == 0
        assert filtered.call_count == 0

    @respx.mock
    def test_unreadable_version_file(self, tmp_path: Path, client: TestClient) -> None:
        """An error reading the installed version leaves the flags null; browse still
        answers (ADR-3 decision 5, review L1)."""

        def unreadable() -> str | None:
            raise PermissionError("current_version")

        data_dir = tmp_path / "data"
        app.dependency_overrides[get_mod_service] = lambda: ModService(
            state_dir=data_dir / "state",
            mods_dir=data_dir / "mods",
            cache_dir=data_dir / "cache",
            restart_state=PendingRestartState(),
            game_version_provider=unreadable,
        )
        filtered = filtered_route(TAG_1_22_7).mock(
            return_value=Response(200, json=flag_listing(1))
        )
        respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1, 2)))

        data = self.browse(client)

        assert data["game_version"] is None
        assert self.flags(data) == {"m1": None, "m2": None}
        assert filtered.call_count == 0

    @respx.mock
    @pytest.mark.parametrize("installed_version", ["1.99.0", "stable"])
    def test_version_without_tag(
        self,
        client: TestClient,
        installed: dict[str, str | None],
        installed_version: str,
    ) -> None:
        """An installed version with no tag: nulls, one version list request (AC 4)."""
        installed["version"] = installed_version
        versions = respx.get(GAMEVERSIONS_URL).mock(
            return_value=Response(200, json=FLAG_VERSIONS)
        )
        filtered = filtered_route(TAG_1_22_7).mock(
            return_value=Response(200, json=flag_listing(1))
        )
        respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1, 2)))

        data = self.browse(client)
        self.browse(client)

        assert data["game_version"] is None
        assert self.flags(data) == {"m1": None, "m2": None}
        assert versions.call_count == 1
        assert filtered.call_count == 0

    @respx.mock
    def test_filtered_listing_fails_without_copy(self, client: TestClient) -> None:
        """A failed filtered listing with no earlier copy: 200 with nulls (AC 5)."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))
        filtered_route(TAG_1_22_7).mock(return_value=Response(500, content=b"error"))
        respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1, 2)))

        data = self.browse(client)

        assert data["game_version"] is None
        assert self.flags(data) == {"m1": None, "m2": None}

    @respx.mock
    def test_filtered_listing_fails_with_earlier_copy(
        self, client: TestClient, mod_service: ModService
    ) -> None:
        """A failed refresh serves the flags of the last copy, even an expired one (AC 5)."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))
        filtered = filtered_route(TAG_1_22_7).mock(
            side_effect=[
                Response(200, json=flag_listing(1)),
                Response(500, content=b"error"),
            ]
        )
        respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1, 2)))

        first = self.browse(client)
        mod_service.api_client.BROWSE_CACHE_TTL = timedelta(0)
        second = self.browse(client)

        assert filtered.call_count == 2
        assert second["game_version"] == "1.22.7"
        assert self.flags(second) == self.flags(first) == {"m1": True, "m2": False}

    @respx.mock
    def test_version_list_fails(self, client: TestClient) -> None:
        """A failed game version list: 200 with nulls (AC 5)."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(503, content=b"down"))
        respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1, 2)))

        data = self.browse(client)

        assert data["game_version"] is None
        assert self.flags(data) == {"m1": None, "m2": None}

    @respx.mock
    def test_main_listing_fails_is_still_502(self, client: TestClient) -> None:
        """A failed main listing is still 502 EXTERNAL_API_ERROR (AC 5)."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))
        filtered_route(TAG_1_22_7).mock(return_value=Response(200, json=flag_listing(1)))
        respx.get(MODS_URL).mock(side_effect=httpx.ConnectError("refused"))

        response = client.get(
            "/api/v1alpha1/mods/browse", headers={"X-API-Key": TEST_ADMIN_KEY}
        )

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "EXTERNAL_API_ERROR"

    @respx.mock
    def test_changed_installed_version(
        self, client: TestClient, installed: dict[str, str | None]
    ) -> None:
        """Another installed version is used on the next request, without clearing (AC 6)."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))
        route_7 = filtered_route(TAG_1_22_7).mock(
            return_value=Response(200, json=flag_listing(1))
        )
        route_8 = filtered_route(TAG_1_22_8).mock(
            return_value=Response(200, json=flag_listing(2))
        )
        plain = respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1, 2)))

        before = self.browse(client)
        installed["version"] = "1.22.8"
        after = self.browse(client)

        assert before["game_version"] == "1.22.7"
        assert self.flags(before) == {"m1": True, "m2": False}
        assert after["game_version"] == "1.22.8"
        assert self.flags(after) == {"m1": False, "m2": True}
        assert route_7.call_count == 1
        assert route_8.call_count == 1
        assert plain.call_count == 1

    @respx.mock
    def test_item_without_modid_is_null(self, client: TestClient) -> None:
        """An item without a numeric modid cannot be matched: its flag is null."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))
        filtered_route(TAG_1_22_7).mock(return_value=Response(200, json=flag_listing(1)))
        listing = flag_listing(1, 2)
        listing["mods"].append({"modidstrs": ["noid"], "name": "No ID", "urlalias": "noid"})
        respx.get(MODS_URL).mock(return_value=Response(200, json=listing))

        data = self.browse(client)

        assert self.flags(data) == {"m1": True, "m2": False, "noid": None}

    @respx.mock
    def test_version_filter_with_flags(self, client: TestClient) -> None:
        """A version filter is cached per version; flags still refer to the installed one
        (AC 7)."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))
        route_3 = filtered_route(TAG_1_21_3).mock(
            return_value=Response(200, json=flag_listing(4, 5, 6))
        )
        route_7 = filtered_route(TAG_1_22_7).mock(
            return_value=Response(200, json=flag_listing(5))
        )
        plain = respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1)))

        page_1 = self.browse(client, "?version=1.21.3&page=1&page_size=2&sort=downloads")
        page_2 = self.browse(client, "?version=1.21.3&page=2&page_size=2&sort=downloads")

        assert self.flags(page_1) == {"m4": False, "m5": True}
        assert self.flags(page_2) == {"m6": False}
        assert page_1["game_version"] == page_2["game_version"] == "1.22.7"
        assert page_1["pagination"]["total_items"] == 3
        assert route_3.call_count == 1
        assert route_7.call_count == 1
        assert plain.call_count == 0

    @respx.mock
    def test_version_filter_by_installed_version(self, client: TestClient) -> None:
        """Filtering by the installed version makes one filtered request in total (AC 2, 7)."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))
        route_7 = filtered_route(TAG_1_22_7).mock(
            return_value=Response(200, json=flag_listing(1, 2))
        )
        plain = respx.get(MODS_URL).mock(return_value=Response(200, json=flag_listing(1)))

        data = self.browse(client, "?version=1.22.7")
        self.browse(client, "?version=1.22.7&page=2&page_size=1")

        assert self.flags(data) == {"m1": True, "m2": True}
        assert route_7.call_count == 1
        assert plain.call_count == 0

    @respx.mock
    def test_unknown_filter_version_is_still_400(self, client: TestClient) -> None:
        """An unknown filter version is still 400 GAME_VERSION_NOT_FOUND (AC 7)."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))

        response = client.get(
            "/api/v1alpha1/mods/browse?version=9.9.9", headers={"X-API-Key": TEST_ADMIN_KEY}
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "GAME_VERSION_NOT_FOUND"

    @respx.mock
    def test_filter_listing_fails_is_still_502(self, client: TestClient) -> None:
        """A failed filter listing is still 502 EXTERNAL_API_ERROR (AC 7)."""
        respx.get(GAMEVERSIONS_URL).mock(return_value=Response(200, json=FLAG_VERSIONS))
        filtered_route(TAG_1_21_3).mock(side_effect=httpx.ConnectError("refused"))
        filtered_route(TAG_1_22_7).mock(return_value=Response(200, json=flag_listing(1)))

        response = client.get(
            "/api/v1alpha1/mods/browse?version=1.21.3", headers={"X-API-Key": TEST_ADMIN_KEY}
        )

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "EXTERNAL_API_ERROR"
