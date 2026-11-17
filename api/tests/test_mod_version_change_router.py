"""API tests for PUT /mods/{slug}/version (Story 14.2)."""

import io
import json
import zipfile
from collections.abc import Generator
from datetime import UTC, datetime
from io import StringIO
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
from vintagestory_api.models.mod_updates import StoredModRecord, StoredRelease
from vintagestory_api.models.mods import ModState
from vintagestory_api.services.mod_updates import (
    ModUpdateService,
    ModUpdateStore,
    get_mod_update_service,
)
from vintagestory_api.services.mods import (
    ModFileConflictError,
    ModOperationInProgressError,
    ModService,
    ModVersionChangeFailedError,
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
def update_service(tmp_path: Path, service: ModService) -> ModUpdateService:
    """Update service on the temp directory: a version change stores records (Story 18.2)."""
    return ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=service,
        game_version_provider=lambda: "1.22.7",
    )


@pytest.fixture
def client(
    tmp_path: Path, service: ModService, update_service: ModUpdateService
) -> Generator[TestClient]:
    settings = Settings(
        api_key_admin=TEST_ADMIN_KEY, api_key_monitor=TEST_MONITOR_KEY, data_dir=tmp_path
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mod_service] = lambda: service
    app.dependency_overrides[get_mod_update_service] = lambda: update_service
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
    def test_release_without_a_file_is_refused(
        self, client: TestClient, service: ModService
    ) -> None:
        """Story 17.2: canjewelry 0.2.20 has no file; 422 before any confirmation."""
        path = service.state_manager.mods_dir / "canjewelry_0.2.19.zip"
        path.write_bytes(zip_bytes({"modid": "canjewelry", "name": "x", "version": "0.2.19"}))
        service.state_manager.set_mod_state(
            path.name,
            ModState(
                filename=path.name,
                slug="canjewelry",
                version="0.2.19",
                enabled=True,
                installed_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        )
        service.state_manager.save()
        respx.get("https://mods.vintagestory.at/api/mod/canjewelry").mock(
            return_value=Response(
                200, json=json.loads((FIXTURES / "mod_canjewelry.json").read_text())
            )
        )
        download = respx.get(DOWNLOAD_URL).mock(return_value=Response(200, content=b"zip"))

        response = client.put(
            "/api/v1alpha1/mods/canjewelry/version", json={"version": "0.2.20"}, headers=ADMIN
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.MOD_RELEASE_NOT_DOWNLOADABLE
        assert detail["message"] == (
            "Version '0.2.20' of mod 'canjewelry' has no downloadable file in the mod database"
        )
        assert not download.called

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
                ModOperationInProgressError("carryon"),
                409,
                ErrorCode.MOD_OPERATION_IN_PROGRESS,
            ),
            (
                ModVersionChangeFailedError("carryon", "disk"),
                500,
                ErrorCode.MOD_VERSION_CHANGE_FAILED,
            ),
            (
                ModFileConflictError("carryon", "x.zip", operation="change the version of"),
                409,
                ErrorCode.MOD_FILE_CONFLICT,
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

    @respx.mock
    def test_a_taken_file_name_is_a_conflict(
        self, client: TestClient, service: ModService, update_service: ModUpdateService
    ) -> None:
        """Story 19.4 AC 4 (FR219): 409 MOD_FILE_CONFLICT, nothing changed or recorded."""
        seeded = seed_record(update_service)
        new_name = release("1.14.3")["filename"]
        stray = service.state_manager.mods_dir / new_name
        stray.write_bytes(b"stray bytes")
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        mock_download("1.14.3")

        response = client.put(URL, json={"version": "1.14.3"}, headers=ADMIN)

        assert response.status_code == 409
        assert response.json() == {
            "detail": {
                "code": "MOD_FILE_CONFLICT",
                "message": (
                    f"Cannot change the version of 'carryon': a file named {new_name} "
                    "already exists in the mods directory."
                ),
            }
        }
        assert stray.read_bytes() == b"stray bytes"
        assert sorted(p.name for p in service.state_manager.mods_dir.iterdir()) == sorted(
            ["carryon_1.14.1.zip", new_name]
        )
        state = service.state_manager.get_mod_by_slug("carryon")
        assert state is not None
        assert (state.filename, state.version) == ("carryon_1.14.1.zip", "1.14.1")
        assert update_service.store.get("carryon") == seeded
        assert ModUpdateStore(update_service.store.path.parent).get("carryon") == seeded

    def test_monitor_is_forbidden(self, client: TestClient) -> None:
        assert client.put(URL, json={"version": "1.14.3"}, headers=MONITOR).status_code == 403

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.put(URL, json={"version": "1.14.3"}).status_code == 401

    def test_version_is_required(self, client: TestClient) -> None:
        assert client.put(URL, json={}, headers=ADMIN).status_code == 422


SEEDED_AT = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def seed_record(update_service: ModUpdateService) -> StoredModRecord:
    """A stored carryon record listing only the installed 1.14.1."""
    seeded = StoredModRecord(
        checked_at=SEEDED_AT, found=True, releases=[StoredRelease.from_api(release("1.14.1"))]
    )
    update_service.store.set("carryon", seeded)
    update_service.store.save()
    return seeded


def carryon_status(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/v1alpha1/mods/updates", headers=ADMIN)
    assert response.status_code == 200
    item: dict[str, Any] = next(
        m for m in response.json()["data"]["mods"] if m["slug"] == "carryon"
    )
    return item


class TestVersionChangeStoresTheUpdateRecord:
    """Story 18.2 (FR200, Epic 18 ADR-5)."""

    @respx.mock
    def test_status_is_real_right_after_the_change(
        self, client: TestClient, update_service: ModUpdateService
    ) -> None:
        """AC 8: no `installed_release_not_listed`, with one lookup and no check."""
        seed_record(update_service)
        lookup = respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        mock_download("1.14.3")
        assert carryon_status(client)["status"] == "up_to_date"

        response = client.put(URL, json={"version": "1.14.3"}, headers=ADMIN)

        assert response.status_code == 200
        item = carryon_status(client)
        assert item["status"] == "up_to_date"
        assert item["reason"] is None
        assert item["installed_version"] == "1.14.3"
        assert lookup.call_count == 1

    @respx.mock
    def test_response_keys_are_unchanged(self, client: TestClient) -> None:
        """AC 9."""
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        mock_download("1.14.3")

        response = client.put(URL, json={"version": "1.14.3"}, headers=ADMIN)

        assert set(response.json()["data"]) == {
            "slug",
            "previous_version",
            "version",
            "filename",
            "compatibility",
            "changed",
            "pending_restart",
        }

    @respx.mock
    def test_a_failed_save_does_not_fail_the_change(
        self,
        client: TestClient,
        service: ModService,
        update_service: ModUpdateService,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        """AC 11: 200 with the same body, and a warning."""
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        mock_download("1.14.3")

        def fail_save() -> None:
            raise OSError("disk full")

        monkeypatch.setattr(update_service.store, "save", fail_save)

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
        state = service.state_manager.get_mod_by_slug("carryon")
        assert state is not None
        assert state.version == "1.14.3"
        warning = next(
            line
            for line in captured_logs.getvalue().splitlines()
            if "mod_update_record_after_version_change_failed" in line
        )
        assert "warning" in warning
        assert "disk full" in warning

    @respx.mock
    @pytest.mark.parametrize(
        ("version", "status"), [("2.0.0-rc.1", 409), ("1.14.1", 200)], ids=["confirm", "same"]
    )
    def test_no_change_leaves_the_record(
        self, client: TestClient, update_service: ModUpdateService, version: str, status: int
    ) -> None:
        """AC 11: confirmation required, or the installed version requested."""
        seeded = seed_record(update_service)
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))

        response = client.put(URL, json={"version": version}, headers=ADMIN)

        assert response.status_code == status
        assert update_service.store.get("carryon") == seeded
        assert ModUpdateStore(update_service.store.path.parent).get("carryon") == seeded
