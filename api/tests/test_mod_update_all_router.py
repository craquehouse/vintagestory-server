"""API tests for POST /mods/updates/apply-all (Story 14.4)."""

import io
import json
import zipfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    ModUpdateAllInProgressError,
    ModUpdateService,
    ModUpdateStore,
    get_mod_update_service,
)
from vintagestory_api.services.mods import ModService, get_mod_service
from vintagestory_api.services.pending_restart import PendingRestartState

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"
MOD_URL = "https://mods.vintagestory.at/api/mod/carryon"
DOWNLOAD_URL = "https://mods.vintagestory.at/download"
ADMIN = {"X-API-Key": TEST_ADMIN_KEY}
MONITOR = {"X-API-Key": TEST_MONITOR_KEY}
URL = "/api/v1alpha1/mods/updates/apply-all"


def carryon() -> dict[str, Any]:
    return json.loads((FIXTURES / "mod_carryon.json").read_text())


def zip_bytes(modinfo: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("modinfo.json", json.dumps(modinfo))
    return buffer.getvalue()


@pytest.fixture
def mod_service(tmp_path: Path) -> ModService:
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
def update_service(tmp_path: Path, mod_service: ModService) -> ModUpdateService:
    svc = ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=mod_service,
        game_version_provider=lambda: "1.22.7",
    )
    svc.store.set(
        "carryon",
        StoredModRecord(
            checked_at=datetime(2026, 11, 9, tzinfo=UTC),
            found=True,
            releases=[StoredRelease.from_api(r) for r in carryon()["mod"]["releases"]],
        ),
    )
    return svc


@pytest.fixture
def client(
    tmp_path: Path, mod_service: ModService, update_service: ModUpdateService
) -> Generator[TestClient]:
    settings = Settings(
        api_key_admin=TEST_ADMIN_KEY, api_key_monitor=TEST_MONITOR_KEY, data_dir=tmp_path
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mod_service] = lambda: mod_service
    app.dependency_overrides[get_mod_update_service] = lambda: update_service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class TestApplyAllEndpoint:
    @respx.mock
    def test_updates_compatible_mods(self, client: TestClient, mod_service: ModService) -> None:
        release = next(r for r in carryon()["mod"]["releases"] if r["modversion"] == "1.14.3")
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        respx.get(DOWNLOAD_URL, params={"fileid": str(release["fileid"])}).mock(
            return_value=Response(
                200, content=zip_bytes({"modid": "carryon", "name": "x", "version": "1.14.3"})
            )
        )

        response = client.post(URL, headers=ADMIN)

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "data": {
                "results": [
                    {
                        "slug": "carryon",
                        "name": "carryon",
                        "from_version": "1.14.1",
                        "to_version": "1.14.3",
                        "outcome": "updated",
                        "reasons": [],
                        "error": None,
                    }
                ],
                "updated": 1,
                "skipped": 0,
                "failed": 0,
                "pending_restart": False,
            },
        }
        state = mod_service.state_manager.get_mod_by_slug("carryon")
        assert state is not None
        assert state.version == "1.14.3"

    @respx.mock
    def test_offer_no_longer_compatible_is_skipped_not_confirmed(
        self, client: TestClient, mod_service: ModService
    ) -> None:
        live = carryon()
        for release in live["mod"]["releases"]:
            if release["modversion"] == "1.14.3":
                release["tags"] = ["1.22.0"]  # same minor as 1.22.7: not verified
        respx.get(MOD_URL).mock(return_value=Response(200, json=live))
        download = respx.get(DOWNLOAD_URL).mock(return_value=Response(500))

        response = client.post(URL, headers=ADMIN)

        assert response.status_code == 200
        result = response.json()["data"]["results"][0]
        assert (result["outcome"], result["reasons"]) == ("skipped", ["not_verified"])
        assert not download.called
        state = mod_service.state_manager.get_mod_by_slug("carryon")
        assert state is not None
        assert state.version == "1.14.1"

    @respx.mock
    def test_failed_lookup_is_reported(self, client: TestClient) -> None:
        respx.get(MOD_URL).mock(return_value=Response(500))

        response = client.post(URL, headers=ADMIN)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["failed"] == 1
        assert data["results"][0]["outcome"] == "failed"
        assert data["results"][0]["error"]

    def test_run_in_progress_returns_409(
        self,
        client: TestClient,
        update_service: ModUpdateService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def busy(*args: object) -> None:
            raise ModUpdateAllInProgressError()

        monkeypatch.setattr(update_service, "apply_all", busy)

        response = client.post(URL, headers=ADMIN)

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == ErrorCode.MOD_UPDATE_ALL_IN_PROGRESS

    def test_monitor_is_forbidden(self, client: TestClient) -> None:
        assert client.post(URL, headers=MONITOR).status_code == 403

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.post(URL).status_code == 401


DEMO_URL = "https://mods.vintagestory.at/api/mod/demo"
SEEDED_AT = datetime(2026, 11, 9, tzinfo=UTC)


def demo() -> dict[str, Any]:
    """A mod database entry for `demo`: 1.2.0-rc.1 (newest), 1.1.0 and 1.0.0."""
    return {
        "statuscode": "200",
        "mod": {
            "assetid": 2,
            "releases": [
                {
                    "modversion": version,
                    "modidstr": "demo",
                    "fileid": fileid,
                    "filename": f"demo-{version}.zip",
                    "tags": ["1.22.7"],
                }
                for version, fileid in (("1.2.0-rc.1", 32), ("1.1.0", 31), ("1.0.0", 30))
            ],
        },
    }


class TestApplyAllStoresEachChangesRecord:
    """Story 18.2 AC 10 (FR200, Epic 18 ADR-5)."""

    @pytest.fixture
    def seeded(
        self, mod_service: ModService, update_service: ModUpdateService
    ) -> dict[str, StoredModRecord]:
        """`demo` 1.0.0 installed beside carryon; both records still offer an update."""
        path = mod_service.state_manager.mods_dir / "demo-1.0.0.zip"
        path.write_bytes(zip_bytes({"modid": "demo", "name": "Demo", "version": "1.0.0"}))
        mod_service.state_manager.set_mod_state(
            path.name,
            ModState(
                filename=path.name,
                slug="demo",
                version="1.0.0",
                enabled=True,
                installed_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        )
        mod_service.state_manager.save()
        records = {
            "carryon": StoredModRecord(
                checked_at=SEEDED_AT,
                found=True,
                releases=[
                    StoredRelease.from_api(r)
                    for r in carryon()["mod"]["releases"]
                    if r["modidstr"] == "carryon" and r["modversion"] in ("1.14.3", "1.14.1")
                ],
            ),
            "demo": StoredModRecord(
                checked_at=SEEDED_AT,
                found=True,
                releases=[StoredRelease.from_api(r) for r in demo()["mod"]["releases"][1:]],
            ),
        }
        for slug, record in records.items():
            update_service.store.set(slug, record)
        return records

    def mock_lookups(self, *, demo_download: Response) -> None:
        carryon_release = next(
            r for r in carryon()["mod"]["releases"] if r["modversion"] == "1.14.3"
        )
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        respx.get(DOWNLOAD_URL, params={"fileid": str(carryon_release["fileid"])}).mock(
            return_value=Response(
                200, content=zip_bytes({"modid": "carryon", "name": "x", "version": "1.14.3"})
            )
        )
        respx.get(DEMO_URL).mock(return_value=Response(200, json=demo()))
        respx.get(DOWNLOAD_URL, params={"fileid": "31"}).mock(return_value=demo_download)

    @respx.mock
    def test_each_changed_mod_stores_its_own_lookup(
        self,
        client: TestClient,
        update_service: ModUpdateService,
        seeded: dict[str, StoredModRecord],
    ) -> None:
        self.mock_lookups(
            demo_download=Response(
                200, content=zip_bytes({"modid": "demo", "name": "Demo", "version": "1.1.0"})
            )
        )

        response = client.post(URL, headers=ADMIN)

        assert response.status_code == 200
        outcomes = {r["slug"]: r["outcome"] for r in response.json()["data"]["results"]}
        assert outcomes == {"carryon": "updated", "demo": "updated"}
        stored_carryon = update_service.store.get("carryon")
        stored_demo = update_service.store.get("demo")
        assert stored_carryon is not None
        assert stored_demo is not None
        assert stored_carryon.releases == [
            StoredRelease.from_api(r) for r in carryon()["mod"]["releases"]
        ]
        assert stored_demo.releases == [
            StoredRelease.from_api(r) for r in demo()["mod"]["releases"]
        ]
        assert stored_carryon.checked_at > SEEDED_AT
        assert stored_demo.checked_at > SEEDED_AT

    @respx.mock
    def test_a_failed_mod_keeps_its_record(
        self,
        client: TestClient,
        update_service: ModUpdateService,
        seeded: dict[str, StoredModRecord],
    ) -> None:
        self.mock_lookups(demo_download=Response(500))

        response = client.post(URL, headers=ADMIN)

        assert response.status_code == 200
        outcomes = {r["slug"]: r["outcome"] for r in response.json()["data"]["results"]}
        assert outcomes == {"carryon": "updated", "demo": "failed"}
        assert update_service.store.get("demo") == seeded["demo"]
        stored_carryon = update_service.store.get("carryon")
        assert stored_carryon is not None
        assert stored_carryon.releases == [
            StoredRelease.from_api(r) for r in carryon()["mod"]["releases"]
        ]
        assert stored_carryon.checked_at > SEEDED_AT
