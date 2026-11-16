"""A real race through the API: one request holds a mod, others for it get 409 (Story 17.3).

`TestClient` is synchronous and cannot hold one request open while sending another, so
these tests use `httpx.AsyncClient` over `ASGITransport`. The mod database is replaced by
the captured `carryon` entry and the download by a gate that writes the archive.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY
from test_mod_version_change import mod_zip_bytes

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.moddb import ModDict, normalize_mod
from vintagestory_api.models.mods import ModState
from vintagestory_api.services.mods import ModService, get_mod_service
from vintagestory_api.services.pending_restart import PendingRestartState

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"
ADMIN = {"X-API-Key": TEST_ADMIN_KEY}
MODS = "/api/v1alpha1/mods"
BUSY_BODY = {
    "detail": {
        "code": "MOD_OPERATION_IN_PROGRESS",
        "message": (
            "Another operation on mod 'carryon' is in progress. Try again when it has finished."
        ),
    }
}


def carryon() -> ModDict:
    mod = normalize_mod(json.loads((FIXTURES / "mod_carryon.json").read_text())["mod"])
    assert mod is not None
    return mod


class Gate:
    """Replaces the mod database lookup and holds every download until `release` is set."""

    def __init__(self, service: ModService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.downloads = 0
        self._dir = tmp_path / "downloads"
        self._dir.mkdir()
        self._versions = {r["fileid"]: r["modversion"] for r in carryon()["releases"]}
        monkeypatch.setattr(service.api_client, "get_mod", self.get_mod)
        monkeypatch.setattr(service.api_client, "download_release_file", self.download)

    async def get_mod(self, slug: str) -> ModDict | None:
        return carryon() if slug == "carryon" else None

    async def download(self, slug: str, fileid: int, filename: str) -> Path:
        self.downloads += 1
        self.started.set()
        await self.release.wait()
        path = self._dir / Path(filename).name
        path.write_bytes(
            mod_zip_bytes({"modid": slug, "name": "Carry On", "version": self._versions[fileid]})
        )
        return path


def make_service(tmp_path: Path, *, installed: str | None) -> ModService:
    service = ModService(
        state_dir=tmp_path / "state",
        mods_dir=tmp_path / "mods",
        restart_state=PendingRestartState(),
        cache_dir=tmp_path / "cache",
        game_version_provider=lambda: "1.22.7",
    )
    service.state_manager.mods_dir.mkdir(parents=True)
    if installed is not None:
        name = f"carryon_{installed}.zip"
        (service.state_manager.mods_dir / name).write_bytes(
            mod_zip_bytes({"modid": "carryon", "name": "Carry On", "version": installed})
        )
        service.state_manager.set_mod_state(
            name,
            ModState(
                filename=name,
                slug="carryon",
                version=installed,
                enabled=True,
                installed_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        )
        service.state_manager.save()
    return service


@pytest.fixture
def service(tmp_path: Path) -> ModService:
    return make_service(tmp_path, installed="1.14.1")


@pytest.fixture
async def client(tmp_path: Path, service: ModService) -> AsyncGenerator[httpx.AsyncClient]:
    settings = Settings(
        api_key_admin=TEST_ADMIN_KEY, api_key_monitor=TEST_MONITOR_KEY, data_dir=tmp_path
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mod_service] = lambda: service
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as async_client:
            yield async_client
    finally:
        app.dependency_overrides.clear()


def installed(response: httpx.Response) -> list[tuple[str, str, bool]]:
    mods: list[dict[str, Any]] = response.json()["data"]["mods"]
    return [(m["slug"], m["version"], m["enabled"]) for m in mods]


class TestBusyModThroughTheApi:
    @pytest.mark.asyncio
    async def test_operations_during_a_version_change_get_409(
        self,
        client: httpx.AsyncClient,
        service: ModService,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        gate = Gate(service, tmp_path, monkeypatch)

        first = asyncio.create_task(
            client.put(f"{MODS}/carryon/version", json={"version": "1.14.3"}, headers=ADMIN)
        )
        await gate.started.wait()
        busy = [
            await client.post(f"{MODS}/carryon/disable", headers=ADMIN),
            await client.post(f"{MODS}/carryon/enable", headers=ADMIN),
            await client.delete(f"{MODS}/carryon", headers=ADMIN),
            await client.put(f"{MODS}/carryon/version", json={"version": "1.14.3"}, headers=ADMIN),
        ]
        gate.release.set()
        response = await first

        for refused in busy:
            assert (refused.status_code, refused.json()) == (409, BUSY_BODY)
        assert response.status_code == 200
        assert response.json()["data"]["version"] == "1.14.3"
        assert installed(await client.get(MODS, headers=ADMIN)) == [("carryon", "1.14.3", True)]
        assert gate.downloads == 1
        assert service.busy_mod_ids == frozenset()
