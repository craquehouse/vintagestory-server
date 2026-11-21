"""The serverconfig.json path check (Story 25.1, Epic 25 ADR-2).

FR346: each ModPaths entry and the save file come back as given, as resolved, with a
status and whether it is a problem. FR347: whether the manager's mods folder is listed.
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server_config import PathCheck, ServerConfigFile
from vintagestory_api.routers.config import get_game_config_service
from vintagestory_api.services.game_config import GameConfigService
from vintagestory_api.services.server import get_server_service
from vintagestory_api.services.server_config_paths import check_paths

ROOT = hasattr(os, "geteuid") and os.geteuid() == 0
needs_permissions = pytest.mark.skipif(ROOT, reason="root ignores file permissions")


@pytest.fixture
def settings(
    tmp_path: Path, admin_headers: dict[str, str], monitor_headers: dict[str, str]
) -> Settings:
    return Settings(
        data_dir=tmp_path,
        api_key_admin=admin_headers["X-API-Key"],
        api_key_monitor=monitor_headers["X-API-Key"],
        debug=True,
    )


def check(
    settings: Settings,
    raw: dict[str, object],
    *,
    game_installed: bool = True,
) -> PathCheck:
    read = ServerConfigFile.from_raw(raw)
    return check_paths(read.model, read.invalid_keys, settings, game_installed=game_installed)


def statuses(result: PathCheck) -> list[str]:
    return [entry.status for entry in result.mod_paths]


@contextmanager
def mode(path: Path, bits: int) -> Generator[None]:
    """Set a path's permission bits for the test, then put them back."""
    before = path.stat().st_mode
    path.chmod(bits)
    try:
        yield
    finally:
        path.chmod(before)


# ==============================================================================
# ModPaths (ADR-2 decisions 1 to 4)
# ==============================================================================


class TestModPaths:
    def test_relative_entries_resolve_against_the_install_directory(
        self, settings: Settings
    ) -> None:
        (settings.server_dir / "Mods").mkdir(parents=True)

        result = check(settings, {"ModPaths": ["Mods"]})

        entry = result.mod_paths[0]
        assert entry.given == "Mods"
        assert entry.resolved == str(settings.server_dir / "Mods")
        assert entry.status == "ok"
        assert entry.problem is False

    def test_a_missing_folder_is_a_problem(self, settings: Settings) -> None:
        result = check(settings, {"ModPaths": ["/nowhere/Mods"]})

        assert statuses(result) == ["missing"]
        assert result.mod_paths[0].problem is True

    def test_the_double_path_bug_is_missing(self, settings: Settings) -> None:
        """agentdocs/vs-server-troubleshooting.md: '../data/serverdata/Mods' from /data/server."""
        result = check(settings, {"ModPaths": ["../data/serverdata/Mods"]})

        assert result.mod_paths[0].resolved == str(
            settings.data_dir / "data" / "serverdata" / "Mods"
        )
        assert statuses(result) == ["missing"]

    def test_a_file_is_not_a_directory(self, settings: Settings) -> None:
        settings.server_dir.mkdir(parents=True)
        (settings.server_dir / "Mods").write_text("x")

        assert statuses(check(settings, {"ModPaths": ["Mods"]})) == ["not_a_directory"]

    @needs_permissions
    def test_an_unreadable_folder(self, settings: Settings) -> None:
        folder = settings.server_dir / "Mods"
        folder.mkdir(parents=True)

        with mode(folder, 0o000):
            assert statuses(check(settings, {"ModPaths": ["Mods"]})) == ["not_readable"]

    def test_the_games_own_mods_before_install_are_not_a_problem(self, settings: Settings) -> None:
        result = check(settings, {"ModPaths": ["Mods"]}, game_installed=False)

        assert statuses(result) == ["not_installed"]
        assert result.mod_paths[0].problem is False

    def test_a_missing_folder_outside_the_install_is_missing_before_install(
        self, settings: Settings
    ) -> None:
        result = check(settings, {"ModPaths": ["/elsewhere/Mods"]}, game_installed=False)

        assert statuses(result) == ["missing"]

    def test_the_managers_folder_before_the_first_install(self, settings: Settings) -> None:
        result = check(settings, {"ModPaths": [str(settings.serverdata_dir / "Mods")]})

        assert statuses(result) == ["not_created_yet"]
        assert result.mod_paths[0].problem is False
        assert result.manager_mods_folder_listed is True

    @pytest.mark.parametrize("form", ["absolute", "relative"])
    def test_the_managers_folder_is_listed_in_either_form(
        self, settings: Settings, form: str
    ) -> None:
        (settings.serverdata_dir / "Mods").mkdir(parents=True)
        given = (
            str(settings.serverdata_dir / "Mods") if form == "absolute" else "../serverdata/Mods"
        )

        result = check(settings, {"ModPaths": ["Mods", given]})

        assert result.manager_mods_folder_listed is True
        assert result.mod_paths[1].status == "ok"

    def test_the_managers_folder_not_listed(self, settings: Settings) -> None:
        result = check(settings, {"ModPaths": ["Mods"]})

        assert result.manager_mods_folder_listed is False

    def test_no_mod_paths_lists_nothing(self, settings: Settings) -> None:
        result = check(settings, {})

        assert result.mod_paths == []
        assert result.manager_mods_folder_listed is False

    @pytest.mark.parametrize("value", ["Mods", ["Mods", 3], 7])
    def test_mod_paths_of_the_wrong_type_is_one_invalid_entry(
        self, settings: Settings, value: object
    ) -> None:
        result = check(settings, {"ModPaths": value})

        assert [e.model_dump() for e in result.mod_paths] == [
            {"given": None, "resolved": None, "status": "invalid", "problem": True}
        ]

    def test_mod_paths_null_is_one_invalid_entry(self, settings: Settings) -> None:
        """Review L1: an explicit null is not a list of strings."""
        result = check(settings, {"ModPaths": None})

        assert statuses(result) == ["invalid"]
        assert result.mod_paths[0].problem is True

    @pytest.mark.parametrize("given", ["a\u0000b", "a" * 5000], ids=["nul", "too-long"])
    def test_an_unusable_entry_is_invalid_not_an_error(
        self, settings: Settings, given: str
    ) -> None:
        """Review M1: a NUL byte or an over-long name is reported, not raised."""
        result = check(settings, {"ModPaths": [given, "Mods"]})

        assert statuses(result)[0] == "invalid"
        assert result.mod_paths[0].given == given
        assert result.mod_paths[0].resolved is not None
        assert result.mod_paths[0].problem is True

    def test_paths_outside_the_data_directory_are_only_stated(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ADR-2 decision 4: stat and access only; nothing is listed or opened."""

        def refuse(*_: object, **__: object) -> None:
            raise AssertionError("the check must not list or open anything")

        monkeypatch.setattr(os, "listdir", refuse)
        monkeypatch.setattr(os, "scandir", refuse)
        monkeypatch.setattr("builtins.open", refuse)

        result = check(settings, {"ModPaths": ["../../../../etc", "/proc", "/"]})

        assert result.mod_paths[0].resolved == os.path.normpath(
            settings.server_dir / "../../../../etc"
        )
        assert all(entry.status in {"ok", "missing", "not_readable"} for entry in result.mod_paths)


# ==============================================================================
# The save file (ADR-2 decisions 1 and 2)
# ==============================================================================


class TestSaveFile:
    def test_null_is_the_default_save_and_not_created_yet_without_saves(
        self, settings: Settings
    ) -> None:
        result = check(settings, {"WorldConfig": {"SaveFileLocation": None}})

        assert result.save_file.given is None
        assert result.save_file.resolved == str(settings.serverdata_dir / "Saves" / "default.vcdbs")
        assert result.save_file.status == "not_created_yet"
        assert result.save_file.problem is False

    def test_no_world_config_is_the_default_save(self, settings: Settings) -> None:
        assert check(settings, {}).save_file.status == "not_created_yet"

    def test_the_default_save_in_an_existing_folder(self, settings: Settings) -> None:
        (settings.serverdata_dir / "Saves").mkdir(parents=True)

        assert check(settings, {}).save_file.status == "ok"

    def test_an_existing_save(self, settings: Settings) -> None:
        saves = settings.serverdata_dir / "Saves"
        saves.mkdir(parents=True)
        (saves / "default.vcdbs").write_bytes(b"")

        assert check(settings, {}).save_file.status == "ok"

    def test_relative_resolves_against_the_data_directory(self, settings: Settings) -> None:
        (settings.data_dir / "relsaves").mkdir()

        result = check(settings, {"WorldConfig": {"SaveFileLocation": "relsaves/rel.vcdbs"}})

        assert result.save_file.resolved == str(settings.data_dir / "relsaves" / "rel.vcdbs")
        assert result.save_file.status == "ok"

    def test_a_missing_folder_for_another_save_is_a_problem(self, settings: Settings) -> None:
        result = check(settings, {"WorldConfig": {"SaveFileLocation": "/nowhere/world.vcdbs"}})

        assert result.save_file.status == "missing"
        assert result.save_file.problem is True

    def test_a_directory_is_not_a_file(self, settings: Settings) -> None:
        (settings.data_dir / "world.vcdbs").mkdir()

        result = check(settings, {"WorldConfig": {"SaveFileLocation": "world.vcdbs"}})

        assert result.save_file.status == "not_a_file"

    @needs_permissions
    def test_a_read_only_save(self, settings: Settings) -> None:
        save = settings.data_dir / "world.vcdbs"
        save.write_bytes(b"")

        with mode(save, 0o444):
            result = check(settings, {"WorldConfig": {"SaveFileLocation": "world.vcdbs"}})

        assert result.save_file.status == "not_writable"

    @needs_permissions
    def test_a_read_only_folder_for_a_new_save(self, settings: Settings) -> None:
        folder = settings.data_dir / "ro"
        folder.mkdir()

        with mode(folder, 0o555):
            result = check(settings, {"WorldConfig": {"SaveFileLocation": "ro/world.vcdbs"}})

        assert result.save_file.status == "not_writable"

    def test_a_file_named_saves_is_a_problem_for_the_default(self, settings: Settings) -> None:
        """Review M2: the game cannot create Saves when a file holds the name."""
        settings.serverdata_dir.mkdir(parents=True)
        (settings.serverdata_dir / "Saves").write_text("x")

        result = check(settings, {})

        assert result.save_file.status == "missing"
        assert result.save_file.problem is True

    @pytest.mark.parametrize("given", ["w\u0000.vcdbs", "a" * 5000], ids=["nul", "too-long"])
    def test_an_unusable_save_location_is_invalid(self, settings: Settings, given: str) -> None:
        result = check(settings, {"WorldConfig": {"SaveFileLocation": given}})

        assert result.save_file.status == "invalid"
        assert result.save_file.problem is True

    def test_a_save_location_of_the_wrong_type_is_invalid(self, settings: Settings) -> None:
        result = check(settings, {"WorldConfig": {"SaveFileLocation": 3}})

        assert result.save_file.status == "invalid"
        assert result.save_file.problem is True


class TestFreshInstall:
    """AC 10: the CI E2E fixture on a data directory with no game: nothing is a problem."""

    def test_the_e2e_fixture_has_no_problem(self, settings: Settings) -> None:
        fixture = Path(__file__).parents[2] / "web" / "e2e" / "fixtures" / "serverconfig.json"
        raw = json.loads(fixture.read_text())
        # The fixture names the container's paths
        raw["ModPaths"] = ["Mods", str(settings.serverdata_dir / "Mods")]

        result = check(settings, raw, game_installed=False)

        assert statuses(result) == ["not_installed", "not_created_yet"]
        assert result.save_file.status == "not_created_yet"
        assert result.manager_mods_folder_listed is True
        assert not any(entry.problem for entry in [*result.mod_paths, result.save_file])


# ==============================================================================
# GET /config/game/paths (ADR-2 decision 5)
# ==============================================================================


@pytest.fixture
def server_service(settings: Settings) -> MagicMock:
    service = MagicMock()
    service.settings = settings
    service.is_installed.return_value = True
    return service


@pytest.fixture
def routed_app(settings: Settings, server_service: MagicMock) -> Generator[FastAPI]:
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_server_service] = lambda: server_service
    app.dependency_overrides[get_game_config_service] = lambda: GameConfigService(
        settings=settings, server_service=server_service
    )
    yield app
    app.dependency_overrides.clear()


def write_config(settings: Settings, content: object | str) -> None:
    settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
    text = content if isinstance(content, str) else json.dumps(content)
    (settings.serverdata_dir / "serverconfig.json").write_text(text)


URL = "/api/v1alpha1/config/game/paths"


class TestRoute:
    @pytest.mark.parametrize("role", ["admin", "monitor"])
    def test_admin_and_monitor_get_the_check(
        self,
        routed_app: FastAPI,
        settings: Settings,
        admin_headers: dict[str, str],
        monitor_headers: dict[str, str],
        role: str,
    ) -> None:
        write_config(settings, {"ModPaths": ["Mods", "/nowhere"]})

        response = TestClient(routed_app).get(
            URL, headers=admin_headers if role == "admin" else monitor_headers
        )

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        data = response.json()["data"]
        assert [entry["status"] for entry in data["mod_paths"]] == ["missing", "missing"]
        assert data["manager_mods_folder_listed"] is False
        assert data["save_file"]["status"] == "not_created_yet"

    def test_the_install_state_comes_from_the_server_service(
        self,
        routed_app: FastAPI,
        settings: Settings,
        server_service: MagicMock,
        admin_headers: dict[str, str],
    ) -> None:
        write_config(settings, {"ModPaths": ["Mods"]})
        server_service.is_installed.return_value = False

        response = TestClient(routed_app).get(URL, headers=admin_headers)

        assert response.json()["data"]["mod_paths"][0]["status"] == "not_installed"

    def test_an_unusable_entry_answers_200(
        self, routed_app: FastAPI, settings: Settings, admin_headers: dict[str, str]
    ) -> None:
        """Review M1: the check reports a NUL entry instead of answering 500."""
        write_config(settings, '{"ModPaths": ["a\\u0000b"]}')

        response = TestClient(routed_app).get(URL, headers=admin_headers)

        assert response.status_code == 200
        assert response.json()["data"]["mod_paths"][0]["status"] == "invalid"

    def test_no_key_is_401(self, routed_app: FastAPI, settings: Settings) -> None:
        write_config(settings, {})

        assert TestClient(routed_app).get(URL).status_code == 401

    def test_a_missing_file_is_404(
        self, routed_app: FastAPI, admin_headers: dict[str, str]
    ) -> None:
        response = TestClient(routed_app).get(URL, headers=admin_headers)

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_NOT_FOUND
        assert response.headers["Cache-Control"] == "no-store"

    def test_a_malformed_file_is_422(
        self, routed_app: FastAPI, settings: Settings, admin_headers: dict[str, str]
    ) -> None:
        write_config(settings, "{not json")

        response = TestClient(routed_app).get(URL, headers=admin_headers)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.CONFIG_FILE_INVALID
        assert detail["parse_error"]["line"] == 1

    def test_the_route_is_in_the_openapi_paths(self) -> None:
        """Story 24.5's lesson: route presence is read from the OpenAPI paths."""
        assert "get" in app.openapi()["paths"]["/api/v1alpha1/config/game/paths"]
