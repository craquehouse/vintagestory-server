"""serverconfig.json is read through one typed model (Story 25.1, Epic 25 ADR-1).

FR344: the API reads serverconfig.json through `ServerConfigFile`; keys the model does
not name are kept when the manager writes the file.
FR345: a serverconfig.json that is not valid JSON is a 422 with the line and column.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import ServerState
from vintagestory_api.models.server_config import ServerConfigFile
from vintagestory_api.routers.config import get_game_config_service
from vintagestory_api.services.game_config import (
    NOT_AN_OBJECT_MESSAGE,
    GameConfigService,
    ServerConfigInvalidError,
)
from vintagestory_api.services.server import get_server_service

SAMPLE = Path(__file__).parent / "fixtures" / "serverconfig-1.22.7.json"
"""The dev stack's game-written file (game 1.22.7, ConfigVersion 1.10), name and ID replaced."""


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


@pytest.fixture
def config_path(settings: Settings) -> Path:
    path = settings.serverdata_dir / "serverconfig.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def stopped_server() -> MagicMock:
    """A ServerService whose game is stopped, so updates write the file."""
    service = MagicMock()
    status = MagicMock()
    status.state = ServerState.INSTALLED
    service.get_server_status.return_value = status
    service.game_server_pid = None
    return service


def write(path: Path, content: object) -> None:
    path.write_text(json.dumps(content, indent=2))


# ==============================================================================
# The model (ADR-1 decisions 1 and 3)
# ==============================================================================


class TestModel:
    def test_reads_the_1_22_7_sample(self) -> None:
        read = ServerConfigFile.from_raw(json.loads(SAMPLE.read_text()))

        assert read.invalid_keys == ()
        model = read.model
        assert model.max_clients == 16
        assert model.port == 42420
        assert model.mod_paths == ["Mods", "/data/serverdata/Mods"]
        assert model.world_config is not None
        assert model.world_config.save_file_location is None
        assert model.only_whitelisted is False
        assert model.whitelist_mode == 0
        # A key the model does not name is kept, not dropped
        assert model.model_extra is not None
        assert "Roles" in model.model_extra

    def test_value_of_uses_the_file_names(self) -> None:
        model = ServerConfigFile.from_raw({"MaxClients": 8, "AllowPvP": False}).model

        assert model.value_of("MaxClients") == 8
        assert model.value_of("AllowPvP") is False
        assert model.value_of("ServerName") is None

    def test_value_of_an_unnamed_key_raises(self) -> None:
        model = ServerConfigFile.from_raw({}).model

        with pytest.raises(KeyError):
            model.value_of("Roles")

    @pytest.mark.parametrize(
        ("content", "invalid"),
        [
            ({"MaxClients": "sixteen"}, ("MaxClients",)),
            ({"MaxClients": "16"}, ("MaxClients",)),
            ({"MaxClients": True}, ("MaxClients",)),
            ({"MaxClients": 16.5}, ("MaxClients",)),
            ({"AllowPvP": 1}, ("AllowPvP",)),
            ({"ServerName": 7}, ("ServerName",)),
            ({"ModPaths": "Mods"}, ("ModPaths",)),
            ({"ModPaths": ["Mods", 1]}, ("ModPaths",)),
            ({"WorldConfig": "none"}, ("WorldConfig",)),
            ({"WorldConfig": {"SaveFileLocation": 3}}, ("WorldConfig.SaveFileLocation",)),
        ],
    )
    def test_a_wrong_type_is_read_as_missing(
        self, content: dict[str, object], invalid: tuple[str, ...]
    ) -> None:
        raw = {**content, "Port": 42420}
        before = json.dumps(raw)

        read = ServerConfigFile.from_raw(raw)

        assert read.invalid_keys == invalid
        assert read.model.port == 42420
        assert json.dumps(raw) == before, "the parsed dict is never changed"

    def test_several_wrong_types_at_once(self) -> None:
        read = ServerConfigFile.from_raw(
            {"MaxClients": "x", "Upnp": "no", "WorldConfig": {"SaveFileLocation": 1}}
        )

        assert sorted(read.invalid_keys) == ["MaxClients", "Upnp", "WorldConfig.SaveFileLocation"]
        assert read.model.world_config is not None


# ==============================================================================
# GameConfigService reads through the model (FR344, FR345)
# ==============================================================================


class TestService:
    def test_settings_come_from_the_model(self, settings: Settings, config_path: Path) -> None:
        config_path.write_text(SAMPLE.read_text())

        result = GameConfigService(settings=settings).get_settings("admin")

        values = {s.key: s.value for s in result.settings}
        assert values["MaxClients"] == 16
        assert values["AllowPvP"] is True
        assert values["ServerName"] == "Test Server"

    def test_a_wrong_type_shows_no_value_and_is_logged_by_key(
        self, settings: Settings, config_path: Path
    ) -> None:
        write(config_path, {"MaxClients": "sixteen-secret-text", "Port": 42420})

        with capture_logs() as logs:
            result = GameConfigService(settings=settings).get_settings("admin")

        values = {s.key: s.value for s in result.settings}
        assert values["MaxClients"] is None
        assert values["Port"] == 42420
        invalid = [entry for entry in logs if entry["event"] == "serverconfig_field_invalid"]
        assert [entry["key"] for entry in invalid] == ["MaxClients"]
        assert "sixteen-secret-text" not in json.dumps(logs, default=str)

    @pytest.mark.parametrize(
        ("text", "line", "column"),
        [('{\n  "Port": 42420,\n  oops\n}', 3, 3), ("[1, 2]", None, None)],
        ids=["malformed", "array"],
    )
    def test_malformed_file_raises_with_line_and_column(
        self, settings: Settings, config_path: Path, text: str, line: int | None, column: int | None
    ) -> None:
        config_path.write_text(text)

        with pytest.raises(ServerConfigInvalidError) as excinfo:
            GameConfigService(settings=settings).get_settings("admin")

        assert excinfo.value.info.line == line
        assert excinfo.value.info.column == column
        if line is None:
            assert excinfo.value.info.message == NOT_AN_OBJECT_MESSAGE

    def test_max_clients_raises_the_typed_error_for_a_malformed_file(
        self, settings: Settings, config_path: Path
    ) -> None:
        config_path.write_text("{not json")

        with pytest.raises(ServerConfigInvalidError):
            GameConfigService(settings=settings).get_max_clients()


class TestRoundTrip:
    """ADR-1 decision 2: a setting update changes only its key."""

    async def test_only_the_changed_key_differs(
        self, settings: Settings, config_path: Path, stopped_server: MagicMock
    ) -> None:
        config_path.write_text(SAMPLE.read_text())
        before = json.loads(SAMPLE.read_text())
        service = GameConfigService(settings=settings, server_service=stopped_server)

        result = await service.update_setting("MaxClients", 24)

        assert result.method == "file_update"
        after = json.loads(config_path.read_text())
        assert list(after) == list(before), "same keys in the same order"
        assert after["MaxClients"] == 24
        assert {k: v for k, v in after.items() if k != "MaxClients"} == {
            k: v for k, v in before.items() if k != "MaxClients"
        }

    async def test_a_wrong_typed_key_survives_another_update(
        self, settings: Settings, config_path: Path, stopped_server: MagicMock
    ) -> None:
        write(config_path, {"MaxClients": "sixteen", "Port": 42420, "Roles": [{"Code": "admin"}]})
        service = GameConfigService(settings=settings, server_service=stopped_server)

        await service.update_setting("Port", 42421)

        after = json.loads(config_path.read_text())
        assert after == {"MaxClients": "sixteen", "Port": 42421, "Roles": [{"Code": "admin"}]}

    async def test_malformed_file_is_not_touched(
        self, settings: Settings, config_path: Path, stopped_server: MagicMock
    ) -> None:
        config_path.write_text("{not json")
        service = GameConfigService(settings=settings, server_service=stopped_server)

        with pytest.raises(ServerConfigInvalidError):
            await service.update_setting("Port", 42421)

        assert config_path.read_text() == "{not json"


# ==============================================================================
# Routes: 422 CONFIG_FILE_INVALID (FR345, ADR-1 decision 4)
# ==============================================================================


@pytest.fixture
def routed_app(settings: Settings, stopped_server: MagicMock) -> Generator[FastAPI]:
    stopped_server.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_server_service] = lambda: stopped_server
    app.dependency_overrides[get_game_config_service] = lambda: GameConfigService(
        settings=settings, server_service=stopped_server
    )
    yield app
    app.dependency_overrides.clear()


class TestRoutes:
    @pytest.mark.parametrize("role", ["admin", "monitor"])
    def test_get_answers_422_with_line_and_column(
        self,
        routed_app: FastAPI,
        config_path: Path,
        admin_headers: dict[str, str],
        monitor_headers: dict[str, str],
        role: str,
    ) -> None:
        config_path.write_text('{\n  "Port": 42420,\n  oops\n}')
        headers = admin_headers if role == "admin" else monitor_headers

        response = TestClient(routed_app).get("/api/v1alpha1/config/game", headers=headers)

        assert response.status_code == 422
        assert response.headers["Cache-Control"] == "no-store"
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.CONFIG_FILE_INVALID
        assert detail["parse_error"]["line"] == 3
        assert detail["parse_error"]["column"] == 3

    def test_update_answers_422_and_leaves_the_file(
        self, routed_app: FastAPI, config_path: Path, admin_headers: dict[str, str]
    ) -> None:
        config_path.write_text("{not json")

        response = TestClient(routed_app).post(
            "/api/v1alpha1/config/game/settings/Port",
            headers=admin_headers,
            json={"value": 42421},
        )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_INVALID
        assert config_path.read_text() == "{not json"
