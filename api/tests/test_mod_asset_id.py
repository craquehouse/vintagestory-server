"""A hand-added mod gets its mod database asset ID from the update check (Story 24.4).

Epic 24 ADR-1: the check fills in an asset ID that is 0, under the mod's lock, skipping a
busy mod, and never changes one that is set.
"""

import io
import json
import zipfile
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
import respx
from httpx import Response

from vintagestory_api.services.mod_updates import ModUpdateService, ModUpdateStore
from vintagestory_api.services.mods import ModService
from vintagestory_api.services.pending_restart import PendingRestartState

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"
MOD_URL = "https://mods.vintagestory.at/api/mod/carryon"
CARRYON_ASSET_ID = 4405


def carryon() -> dict[str, Any]:
    return json.loads((FIXTURES / "mod_carryon.json").read_text())


def hand_added(service: ModService, modid: str = "carryon", version: str = "1.14.1") -> None:
    """Copy an archive into the mods directory and sync, as a hand-added mod arrives."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("modinfo.json", json.dumps({"modid": modid, "name": "x", "version": version}))
    mods_dir = service.state_manager.mods_dir
    mods_dir.mkdir(parents=True, exist_ok=True)
    (mods_dir / f"{modid}_{version}.zip").write_bytes(buffer.getvalue())
    service.state_manager.sync_state_with_disk()


def asset_id(service: ModService, slug: str) -> int | None:
    state = service.state_manager.get_mod_by_slug(slug)
    return None if state is None else state.asset_id


@pytest.fixture
def mod_service(tmp_path: Path) -> ModService:
    return ModService(
        state_dir=tmp_path / "state",
        mods_dir=tmp_path / "mods",
        restart_state=PendingRestartState(),
        cache_dir=tmp_path / "cache",
        game_version_provider=lambda: "1.22.7",
    )


@pytest.fixture
def update_service(tmp_path: Path, mod_service: ModService) -> ModUpdateService:
    return ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=mod_service,
        game_version_provider=lambda: "1.22.7",
    )


class TestFillAssetId:
    def test_fills_an_asset_id_of_zero_and_saves_it(self, mod_service: ModService) -> None:
        hand_added(mod_service)
        assert asset_id(mod_service, "carryon") == 0

        assert mod_service.fill_asset_id("carryon", CARRYON_ASSET_ID) is True

        assert asset_id(mod_service, "carryon") == CARRYON_ASSET_ID
        saved = json.loads(mod_service.state_manager.state_file.read_text())
        assert saved["carryon_1.14.1.zip"]["asset_id"] == CARRYON_ASSET_ID

    def test_matches_the_mod_id_ignoring_case(self, mod_service: ModService) -> None:
        hand_added(mod_service, modid="CarryOn")

        assert mod_service.fill_asset_id("carryon", CARRYON_ASSET_ID) is True
        assert asset_id(mod_service, "CarryOn") == CARRYON_ASSET_ID

    def test_never_changes_an_asset_id_that_is_set(
        self, mod_service: ModService, captured_logs: StringIO
    ) -> None:
        hand_added(mod_service)
        mod_service.fill_asset_id("carryon", 111)

        assert mod_service.fill_asset_id("carryon", 222) is False

        assert asset_id(mod_service, "carryon") == 111
        assert "mod_asset_id_differs" in captured_logs.getvalue()

    def test_the_same_asset_id_again_is_not_logged(
        self, mod_service: ModService, captured_logs: StringIO
    ) -> None:
        hand_added(mod_service)
        mod_service.fill_asset_id("carryon", 111)

        assert mod_service.fill_asset_id("carryon", 111) is False
        assert "mod_asset_id_differs" not in captured_logs.getvalue()

    @pytest.mark.parametrize("value", [0, -5])
    def test_ignores_an_asset_id_that_is_not_positive(
        self, mod_service: ModService, value: int
    ) -> None:
        hand_added(mod_service)

        assert mod_service.fill_asset_id("carryon", value) is False
        assert asset_id(mod_service, "carryon") == 0

    def test_ignores_a_mod_that_is_not_installed(self, mod_service: ModService) -> None:
        assert mod_service.fill_asset_id("missing", CARRYON_ASSET_ID) is False

    def test_skips_a_busy_mod(self, mod_service: ModService) -> None:
        """An install or version change holds the lock; the next check fills it in."""
        hand_added(mod_service)

        with mod_service._hold("carryon"):
            assert mod_service.fill_asset_id("carryon", CARRYON_ASSET_ID) is False

        assert asset_id(mod_service, "carryon") == 0
        assert mod_service.fill_asset_id("carryon", CARRYON_ASSET_ID) is True

    def test_a_failed_save_is_logged_and_does_not_raise(
        self,
        mod_service: ModService,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        hand_added(mod_service)

        def refuse() -> None:
            raise OSError("read-only file system")

        monkeypatch.setattr(mod_service.state_manager, "save", refuse)

        assert mod_service.fill_asset_id("carryon", CARRYON_ASSET_ID) is True
        assert "mod_asset_id_not_saved" in captured_logs.getvalue()


class TestUpdateCheckFillsTheAssetId:
    @respx.mock
    @pytest.mark.asyncio
    async def test_a_hand_added_mod_gets_its_asset_id(
        self, mod_service: ModService, update_service: ModUpdateService
    ) -> None:
        hand_added(mod_service)
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))

        await update_service.check()

        assert asset_id(mod_service, "carryon") == CARRYON_ASSET_ID
        listed = {mod.slug: mod for mod in mod_service.list_mods()}
        assert listed["carryon"].asset_id == CARRYON_ASSET_ID
        status = {item.slug: item for item in update_service.get_status()}
        assert status["carryon"].status != "unknown"

    @respx.mock
    @pytest.mark.asyncio
    async def test_a_mod_the_database_does_not_know_stays_local(
        self, mod_service: ModService, update_service: ModUpdateService
    ) -> None:
        hand_added(mod_service)
        respx.get(MOD_URL).mock(return_value=Response(200, json={"statuscode": "404", "mod": None}))

        await update_service.check()

        assert asset_id(mod_service, "carryon") == 0
        status = {item.slug: item for item in update_service.get_status()}
        assert (status["carryon"].status, status["carryon"].reason) == (
            "unknown",
            "not_in_database",
        )

    @respx.mock
    @pytest.mark.asyncio
    async def test_the_database_being_unavailable_changes_nothing(
        self, mod_service: ModService, update_service: ModUpdateService
    ) -> None:
        hand_added(mod_service)
        respx.get(MOD_URL).mock(return_value=Response(503))

        summary = await update_service.check()

        assert summary.failed == 1
        assert asset_id(mod_service, "carryon") == 0


class TestReviewFollowUps:
    """Story 24.4 review: two entries of one mod ID, a failing fill, the log."""

    def test_two_entries_of_one_mod_id_are_left_alone(self, mod_service: ModService) -> None:
        hand_added(mod_service, modid="carryon", version="1.0.0")
        hand_added(mod_service, modid="carryon", version="2.0.0")
        # The sync skips the second archive as a duplicate; make the state hold both
        state = mod_service.state_manager.get_mod_by_slug("carryon")
        assert state is not None
        mod_service.state_manager.set_mod_state(
            "carryon_2.0.0.zip", state.model_copy(update={"filename": "carryon_2.0.0.zip"})
        )

        assert mod_service.fill_asset_id("carryon", CARRYON_ASSET_ID) is False
        assert {s.asset_id for s in mod_service.state_manager.list_mods()} == {0}

    def test_a_failed_save_is_not_logged_as_filled(
        self,
        mod_service: ModService,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        hand_added(mod_service)

        def refuse() -> None:
            raise OSError("read-only file system")

        monkeypatch.setattr(mod_service.state_manager, "save", refuse)
        mod_service.fill_asset_id("carryon", CARRYON_ASSET_ID)

        assert "mod_asset_id_filled" not in captured_logs.getvalue()

    @respx.mock
    @pytest.mark.asyncio
    async def test_a_fill_that_raises_does_not_fail_the_check(
        self,
        mod_service: ModService,
        update_service: ModUpdateService,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        hand_added(mod_service)
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))

        def boom(slug: str, asset_id: int) -> bool:
            raise RuntimeError("unexpected")

        monkeypatch.setattr(mod_service, "fill_asset_id", boom)

        summary = await update_service.check()

        assert summary.failed == 0
        assert "mod_asset_id_fill_failed" in captured_logs.getvalue()
