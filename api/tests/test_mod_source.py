"""Each installed mod records where it came from (Story 28.1, Epic 28 ADR-1 and ADR-2)."""

import io
import json
import zipfile
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
from vintagestory_api.models.mods import ModInfo, ModState
from vintagestory_api.services.mod_updates import (
    ModUpdateService,
    ModUpdateStore,
    build_status_items,
)
from vintagestory_api.services.mods import ModService, get_mod_service
from vintagestory_api.services.pending_restart import PendingRestartState

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"
INSTALLED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def zip_bytes(modid: str, version: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("modinfo.json", json.dumps({"modid": modid, "name": modid, "version": version}))
    return buffer.getvalue()


@pytest.fixture
def mod_service(tmp_path: Path) -> ModService:
    return ModService(
        state_dir=tmp_path / "state",
        mods_dir=tmp_path / "mods",
        restart_state=PendingRestartState(),
        cache_dir=tmp_path / "cache",
        game_version_provider=lambda: "1.22.7",
    )


def add_mod(
    service: ModService,
    modid: str,
    *,
    source: str,
    source_url: str | None = None,
    asset_id: int = 0,
) -> None:
    """Place an archive and a state entry with the given source."""
    mods_dir = service.state_manager.mods_dir
    mods_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{modid}_1.0.0.zip"
    (mods_dir / filename).write_bytes(zip_bytes(modid, "1.0.0"))
    service.state_manager.import_mod(mods_dir / filename)
    service.state_manager.set_mod_state(
        filename,
        ModState.model_validate(
            {
                "filename": filename,
                "slug": modid,
                "version": "1.0.0",
                "installed_at": INSTALLED_AT,
                "asset_id": asset_id,
                "source": source,
                "source_url": source_url,
            }
        ),
    )
    service.state_manager.save()


class TestLegacyEntries:
    """ADR-1 decision 3: an entry saved before Epic 28 reads by its asset ID."""

    def entry(self, **extra: Any) -> dict[str, Any]:
        return {
            "filename": "a.zip",
            "slug": "a",
            "version": "1.0.0",
            "installed_at": "2026-01-01T00:00:00Z",
            **extra,
        }

    def test_an_entry_with_an_asset_id_is_from_the_mod_database(self) -> None:
        assert ModState.model_validate(self.entry(asset_id=15312)).source == "moddb"

    @pytest.mark.parametrize("extra", [{}, {"asset_id": 0}, {"asset_id": True}])
    def test_an_entry_without_one_was_found_in_the_folder(self, extra: dict[str, Any]) -> None:
        assert ModState.model_validate(self.entry(**extra)).source == "folder"

    def test_a_stored_source_is_kept(self) -> None:
        state = ModState.model_validate(
            self.entry(asset_id=1, source="url", source_url="https://example.com/a.zip")
        )
        assert state.source == "url"
        assert state.source_url == "https://example.com/a.zip"

    def test_loading_rewrites_nothing(self, mod_service: ModService) -> None:
        state_file = mod_service.state_manager.state_file
        state_file.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps({"a.zip": self.entry(asset_id=7)})
        state_file.write_text(text)

        mod_service.state_manager.load()

        assert state_file.read_text() == text
        entry = mod_service.state_manager.get_mod("a.zip")
        assert entry is not None
        assert entry.source == "moddb"


class TestWhoSetsTheSource:
    def test_the_sync_marks_a_found_file_as_folder(self, mod_service: ModService) -> None:
        mods_dir = mod_service.state_manager.mods_dir
        mods_dir.mkdir(parents=True)
        (mods_dir / "demo_1.0.0.zip").write_bytes(zip_bytes("demo", "1.0.0"))

        mod_service.state_manager.sync_state_with_disk()

        entry = mod_service.state_manager.get_mod_by_slug("demo")
        assert entry is not None
        assert entry.source == "folder"
        saved = json.loads(mod_service.state_manager.state_file.read_text())
        assert saved["demo_1.0.0.zip"]["source"] == "folder"

    def test_list_and_get_carry_the_source(self, mod_service: ModService) -> None:
        add_mod(mod_service, "linked", source="url", source_url="https://example.com/l.zip")

        listed = mod_service.list_mods()
        got = mod_service.get_mod("linked")

        assert [(m.source, m.source_url) for m in listed] == [("url", "https://example.com/l.zip")]
        assert got is not None
        assert (got.source, got.source_url) == ("url", "https://example.com/l.zip")


class TestListRoute:
    def test_each_mod_has_source_and_source_url(
        self, tmp_path: Path, mod_service: ModService, admin_headers: dict[str, str]
    ) -> None:
        add_mod(mod_service, "uploaded", source="upload")
        settings = Settings(
            api_key_admin=TEST_ADMIN_KEY, api_key_monitor=TEST_MONITOR_KEY, data_dir=tmp_path
        )
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_mod_service] = lambda: mod_service
        try:
            response = TestClient(app).get("/api/v1alpha1/mods", headers=admin_headers)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        mod = response.json()["data"]["mods"][0]
        assert mod["source"] == "upload"
        assert mod["source_url"] is None


def info(slug: str, source: str) -> ModInfo:
    return ModInfo.model_validate(
        {
            "filename": f"{slug}.zip",
            "slug": slug,
            "version": "1.0.0",
            "enabled": True,
            "installed_at": INSTALLED_AT,
            "name": slug,
            "source": source,
        }
    )


class TestStatus:
    """ADR-2 decision 1: uploaded and linked mods are `unknown` / `manual_install`."""

    @pytest.mark.parametrize("source", ["upload", "url"])
    def test_manual_mods_are_manual_install(self, tmp_path: Path, source: str) -> None:
        store = ModUpdateStore(tmp_path)
        items = build_status_items([info("demo", source)], store, "1.22.7")

        assert [(i.status, i.reason) for i in items] == [("unknown", "manual_install")]

    def test_a_record_from_before_a_replace_does_not_apply(self, tmp_path: Path) -> None:
        store = ModUpdateStore(tmp_path)
        store.set_lookup_error("demo", "boom")
        items = build_status_items([info("demo", "upload")], store, "1.22.7")

        assert items[0].reason == "manual_install"
        assert items[0].error is None

    def test_a_folder_mod_is_not_checked_yet_as_before(self, tmp_path: Path) -> None:
        items = build_status_items([info("demo", "folder")], ModUpdateStore(tmp_path), "1.22.7")

        assert items[0].reason == "not_checked"


class TestCheck:
    @pytest.fixture
    def update_service(self, tmp_path: Path, mod_service: ModService) -> ModUpdateService:
        return ModUpdateService(
            store=ModUpdateStore(tmp_path / "state"),
            mod_source=mod_service,
            game_version_provider=lambda: "1.22.7",
        )

    @respx.mock
    @pytest.mark.asyncio
    async def test_manual_mods_are_never_looked_up(
        self, mod_service: ModService, update_service: ModUpdateService
    ) -> None:
        """A fork uploaded under a mod-database mod ID is not offered the original's update."""
        carryon = json.loads((FIXTURES / "mod_carryon.json").read_text())
        route = respx.get("https://mods.vintagestory.at/api/mod/carryon").mock(
            return_value=Response(200, json=carryon)
        )
        add_mod(mod_service, "carryon", source="upload")

        summary = await update_service.check()

        assert route.call_count == 0
        assert summary.checked == 0
        entry = mod_service.state_manager.get_mod_by_slug("carryon")
        assert entry is not None
        assert entry.asset_id == 0
        [item] = update_service.get_status()
        assert (item.status, item.reason) == ("unknown", "manual_install")

    @respx.mock
    @pytest.mark.asyncio
    async def test_a_folder_mod_is_looked_up_and_filled_in(
        self, mod_service: ModService, update_service: ModUpdateService
    ) -> None:
        """ADR-2 decision 2: a copied-in file is still a mod-database mod when it is one."""
        carryon = json.loads((FIXTURES / "mod_carryon.json").read_text())
        route = respx.get("https://mods.vintagestory.at/api/mod/carryon").mock(
            return_value=Response(200, json=carryon)
        )
        add_mod(mod_service, "carryon", source="folder")

        summary = await update_service.check()

        assert route.call_count == 1
        assert summary.checked == 1
        entry = mod_service.state_manager.get_mod_by_slug("carryon")
        assert entry is not None
        assert entry.asset_id == carryon["mod"]["assetid"]
        assert entry.source == "folder"
