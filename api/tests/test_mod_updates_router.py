"""API tests for mod update endpoints (Story 14.1)."""

import json
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

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
from vintagestory_api.models.mods import ModInfo
from vintagestory_api.services.mod_api import ModApiClient
from vintagestory_api.services.mod_updates import (
    ModUpdateCheckInProgressError,
    ModUpdateService,
    ModUpdateStore,
    get_mod_update_service,
)

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"
UPDATES_URL = "/api/v1alpha1/mods/updates"
CHECK_URL = "/api/v1alpha1/mods/updates/check"
ADMIN = {"X-API-Key": TEST_ADMIN_KEY}
MONITOR = {"X-API-Key": TEST_MONITOR_KEY}


def carryon_releases() -> list[StoredRelease]:
    data = json.loads((FIXTURES / "mod_carryon.json").read_text())
    return [StoredRelease.from_api(r) for r in data["mod"]["releases"]]


class FakeModSource:
    def __init__(self, cache_dir: Path) -> None:
        self.api_client = ModApiClient(cache_dir=cache_dir)

    def list_mods(self) -> list[ModInfo]:
        return [
            ModInfo(
                filename="CarryOn-1.14.1.zip",
                slug="carryon",
                version="1.14.1",
                enabled=True,
                installed_at=datetime(2026, 1, 1, tzinfo=UTC),
                name="Carry On",
            )
        ]


@pytest.fixture
def service(tmp_path: Path) -> ModUpdateService:
    return ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=FakeModSource(tmp_path / "cache"),
        game_version_provider=lambda: "1.22.7",
    )


@pytest.fixture
def client(tmp_path: Path, service: ModUpdateService) -> Generator[TestClient]:
    settings = Settings(
        api_key_admin=TEST_ADMIN_KEY, api_key_monitor=TEST_MONITOR_KEY, data_dir=tmp_path
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mod_update_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class TestGetModUpdates:
    def test_returns_status_for_installed_mods(
        self, client: TestClient, service: ModUpdateService
    ) -> None:
        service.store.set(
            "carryon",
            StoredModRecord(
                checked_at=datetime(2026, 11, 9, tzinfo=UTC),
                found=True,
                releases=carryon_releases(),
            ),
        )

        response = client.get(UPDATES_URL, headers=ADMIN)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        data = body["data"]
        assert data["game_version"] == "1.22.7"
        assert data["checked_at"] is None
        assert data["update_count"] == 1
        assert data["mods"] == [
            {
                "slug": "carryon",
                "name": "Carry On",
                "installed_version": "1.14.1",
                "status": "update_available",
                "offered_version": "1.14.3",
                "offered_compatibility": "compatible",
                "offered_prerelease": False,
                "reason": None,
                "checked_at": "2026-11-09T00:00:00Z",
                "error": None,
            }
        ]

    def test_monitor_can_read(self, client: TestClient) -> None:
        response = client.get(UPDATES_URL, headers=MONITOR)

        assert response.status_code == 200
        assert response.json()["data"]["mods"][0]["reason"] == "not_checked"

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(UPDATES_URL).status_code == 401


class TestCheckModUpdates:
    @respx.mock
    def test_admin_check_refreshes_and_reports(self, client: TestClient) -> None:
        respx.get("https://mods.vintagestory.at/api/mod/carryon").mock(
            return_value=Response(200, json=json.loads((FIXTURES / "mod_carryon.json").read_text()))
        )

        response = client.post(CHECK_URL, headers=ADMIN)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["check"] == {"checked": 1, "failed": 0, "failed_slugs": []}
        assert data["checked_at"] is not None
        assert data["mods"][0]["offered_version"] == "1.14.3"

    @respx.mock
    def test_upstream_lone_surrogate_does_not_break_responses(self, client: TestClient) -> None:
        body = (
            b'{"statuscode": "200", "mod": {"releases": ['
            b'{"modversion": "1.14.9\\ud800", "modidstr": "carryon", "tags": ["1.22.7"]},'
            b'{"modversion": "1.14.1", "modidstr": "carryon", "tags": ["1.22.7"]}]}}'
        )
        respx.get("https://mods.vintagestory.at/api/mod/carryon").mock(
            return_value=Response(200, content=body)
        )

        checked = client.post(CHECK_URL, headers=ADMIN)
        status = client.get(UPDATES_URL, headers=ADMIN)

        assert checked.status_code == 200
        assert status.status_code == 200
        assert status.json()["data"]["mods"][0]["offered_version"] == "1.14.9\ufffd"

    def test_monitor_cannot_check(self, client: TestClient) -> None:
        assert client.post(CHECK_URL, headers=MONITOR).status_code == 403

    def test_check_in_progress_returns_409(
        self, client: TestClient, service: ModUpdateService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def busy() -> None:
            raise ModUpdateCheckInProgressError()

        monkeypatch.setattr(service, "check", busy)

        response = client.post(CHECK_URL, headers=ADMIN)

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == ErrorCode.MOD_UPDATE_CHECK_IN_PROGRESS
