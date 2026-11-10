"""API tests for PUT /mods/{slug}/version (Story 14.2)."""

import io
import json
import zipfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY
from fastapi.testclient import TestClient
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.mods import ModState
from vintagestory_api.services.mods import (
    ModService,
    ModVersionChangeFailedError,
    ModVersionChangeInProgressError,
    get_mod_service,
)
from vintagestory_api.services.pending_restart import PendingRestartState

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"
MOD_URL = "https://mods.vintagestory.at/api/mod/carryon"
DOWNLOAD_URL = "https://mods.vintagestory.at/download"
ADMIN = {"X-API-Key": TEST_ADMIN_KEY}
MONITOR = {"X-API-Key": TEST_MONITOR_KEY}
URL = "/api/v1alpha1/mods/carryon/version"


def carryon() -> dict[str, Any]:
    return json.loads((FIXTURES / "mod_carryon.json").read_text())


def release(version: str) -> dict[str, Any]:
    return next(r for r in carryon()["mod"]["releases"] if r["modversion"] == version)


def zip_bytes(modinfo: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("modinfo.json", json.dumps(modinfo))
    return buffer.getvalue()


@pytest.fixture
def service(tmp_path: Path) -> ModService:
    svc = ModService(
        state_dir=tmp_path / "state",
        mods_dir=tmp_path / "mods",
        restart_state=PendingRestartState(),
        cache_dir=tmp_path / "cache",
        game_version_provider=lambda: "1.22.7",
    )
    svc.state_manager.mods_dir.mkdir(parents=True)
    path = svc.state_manager.mods_dir / "carryon_1.14.1.zip"
    path.write_bytes(zip_bytes({"modid": "carryon", "name": "Carry On", "version": "1.14.1"}))
    svc.state_manager.set_mod_state(
        path.name,
        ModState(
            filename=path.name,
            slug="carryon",
            version="1.14.1",
            enabled=True,
            installed_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )
    svc.state_manager.save()
    return svc


@pytest.fixture
def client(tmp_path: Path, service: ModService) -> Generator[TestClient]:
    settings = Settings(
        api_key_admin=TEST_ADMIN_KEY, api_key_monitor=TEST_MONITOR_KEY, data_dir=tmp_path
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mod_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def mock_download(version: str, modid: str = "carryon") -> None:
    respx.get(DOWNLOAD_URL, params={"fileid": str(release(version)["fileid"])}).mock(
        return_value=Response(
            200, content=zip_bytes({"modid": modid, "name": "x", "version": version})
        )
    )


def error_code(response: Any) -> str:
    """Error code from a TestClient response."""
    code: str = response.json()["detail"]["code"]
    return code


class TestChangeVersionEndpoint:
    @respx.mock
    def test_successful_update(self, client: TestClient) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        mock_download("1.14.3")

        response = client.put(URL, json={"version": "1.14.3"}, headers=ADMIN)

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "data": {
                "slug": "carryon",
                "previous_version": "1.14.1",
                "version": "1.14.3",
                "filename": release("1.14.3")["filename"],
                "compatibility": "compatible",
                "changed": True,
                "pending_restart": False,
            },
        }

    @respx.mock
    def test_confirmation_required_lists_reasons(self, client: TestClient) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))

        response = client.put(URL, json={"version": "2.0.0-rc.1"}, headers=ADMIN)

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.MOD_CONFIRMATION_REQUIRED
        assert detail["details"] == {"reasons": ["prerelease"], "compatibility": "compatible"}

    @respx.mock
    def test_confirmed_prerelease_switch(self, client: TestClient) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        mock_download("2.0.0-rc.1")

        response = client.put(URL, json={"version": "2.0.0-rc.1", "confirm": True}, headers=ADMIN)

        assert response.status_code == 200
        assert response.json()["data"]["version"] == "2.0.0-rc.1"

    def test_mod_not_installed(self, client: TestClient) -> None:
        response = client.put(
            "/api/v1alpha1/mods/missing/version", json={"version": "1.0.0"}, headers=ADMIN
        )

        assert response.status_code == 404
        assert error_code(response) == ErrorCode.MOD_NOT_INSTALLED

    @respx.mock
    def test_mod_not_in_database(self, client: TestClient) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json={"statuscode": "404"}))

        response = client.put(URL, json={"version": "1.14.3"}, headers=ADMIN)

        assert response.status_code == 404
        assert error_code(response) == ErrorCode.MOD_NOT_FOUND

    @respx.mock
    def test_version_not_listed(self, client: TestClient) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))

        response = client.put(URL, json={"version": "9.9.9"}, headers=ADMIN)

        assert response.status_code == 404
        assert error_code(response) == ErrorCode.MOD_VERSION_NOT_FOUND

    @respx.mock
    def test_archive_validation_failure(self, client: TestClient) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        mock_download("1.14.3", modid="someothermod")

        response = client.put(URL, json={"version": "1.14.3"}, headers=ADMIN)

        assert response.status_code == 422
        assert error_code(response) == ErrorCode.MOD_VALIDATION_FAILED

    @respx.mock
    def test_mod_database_unavailable(self, client: TestClient) -> None:
        respx.get(MOD_URL).mock(side_effect=httpx.ConnectError("down"))

        response = client.put(URL, json={"version": "1.14.3"}, headers=ADMIN)

        assert response.status_code == 502
        assert error_code(response) == ErrorCode.EXTERNAL_API_ERROR

    @respx.mock
    def test_download_failure(self, client: TestClient) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        respx.get(DOWNLOAD_URL).mock(return_value=Response(500))

        response = client.put(URL, json={"version": "1.14.3"}, headers=ADMIN)

        assert response.status_code == 502
        assert error_code(response) == ErrorCode.DOWNLOAD_FAILED

    @pytest.mark.parametrize(
        ("error", "status", "code"),
        [
            (
                ModVersionChangeInProgressError("carryon"),
                409,
                ErrorCode.MOD_VERSION_CHANGE_IN_PROGRESS,
            ),
            (
                ModVersionChangeFailedError("carryon", "disk"),
                500,
                ErrorCode.MOD_VERSION_CHANGE_FAILED,
            ),
        ],
    )
    def test_service_errors_map_to_responses(
        self,
        client: TestClient,
        service: ModService,
        monkeypatch: pytest.MonkeyPatch,
        error: Exception,
        status: int,
        code: str,
    ) -> None:
        async def fail(*args: object, **kwargs: object) -> None:
            raise error

        monkeypatch.setattr(service, "change_version", fail)

        response = client.put(URL, json={"version": "1.14.3"}, headers=ADMIN)

        assert response.status_code == status
        assert error_code(response) == code

    def test_monitor_is_forbidden(self, client: TestClient) -> None:
        assert client.put(URL, json={"version": "1.14.3"}, headers=MONITOR).status_code == 403

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.put(URL, json={"version": "1.14.3"}).status_code == 401

    def test_version_is_required(self, client: TestClient) -> None:
        assert client.put(URL, json={}, headers=ADMIN).status_code == 422
