"""Game Settings read and set Entity Spawning on the game (Story 25.3, Epic 25 ADR-5, ADR-6).

FR349-FR352: the value comes from the game's console replies, a change goes through the
console only while the game is ready, and VS_CFG_ENTITY_SPAWNING is never written to the
file.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import ServerState
from vintagestory_api.routers.config import get_game_config_service
from vintagestory_api.services.config_init import GAME_KEPT_KEYS
from vintagestory_api.services.config_init_service import ConfigInitService
from vintagestory_api.services.entity_spawning import ENV_VAR, EntitySpawningWatcher
from vintagestory_api.services.game_config import (
    LIVE_SETTINGS,
    GameConfigService,
    SettingEnvManagedError,
    SettingNeedsRunningServerError,
    SettingNoReplyError,
)
from vintagestory_api.services.server import get_server_service

TS = "21.11.2026 01:32:28"
READY = f"{TS} [Server Event] Dedicated Server now running on Port 42420 and all ips!"
NOW = datetime(2026, 11, 21, 1, 32, 28, tzinfo=UTC)
URL = "/api/v1alpha1/config/game/settings/EntitySpawning"
SAMPLE = {"ServerName": "Test", "Port": 42420, "EntitySpawning": True}


class Game:
    """A ServerService stand-in with a real watcher and a game that answers (or not)."""

    def __init__(self, settings: Settings, *, running: bool, answers: bool = True) -> None:
        self.settings = settings
        self.answers = answers
        self.state = True
        self.commands: list[str] = []
        self.service = MagicMock()
        self.service.settings = settings
        self.service.game_server_pid = 4242 if running else None
        status = MagicMock()
        status.state = ServerState.RUNNING if running else ServerState.INSTALLED
        self.service.get_server_status.return_value = status
        self.watcher = EntitySpawningWatcher(
            settings.state_dir, self.send, now=lambda: NOW, timeout=0.2
        )
        self.service.entity_spawning = self.watcher

    async def send(self, command: str) -> bool:
        self.commands.append(command)
        if not self.answers:
            return True
        if command == "/serverconfig entityspawning":
            line = f"Current Entity spawning mode is {'on' if self.state else 'off'}"
        else:
            self.state = command.endswith("true")
            line = f"Entity spawning mode set to {'on' if self.state else 'off'}"
        asyncio.get_running_loop().call_soon(
            self.watcher.observe, f"{TS} [Server Notification] {line}"
        )
        return True

    async def become_ready(self) -> None:
        """The game logs its ready line; the hook's query is answered."""
        self.watcher.observe(READY)
        for _ in range(50):
            await asyncio.sleep(0.01)
            if self.watcher.seen_since_start or not self.answers:
                break
        self.commands.clear()

    def config_service(self) -> GameConfigService:
        return GameConfigService(settings=self.settings, server_service=self.service)


@pytest.fixture
def settings(
    tmp_path: Path, admin_headers: dict[str, str], monitor_headers: dict[str, str]
) -> Settings:
    settings = Settings(
        data_dir=tmp_path,
        api_key_admin=admin_headers["X-API-Key"],
        api_key_monitor=monitor_headers["X-API-Key"],
        debug=True,
    )
    settings.serverdata_dir.mkdir(parents=True)
    (settings.serverdata_dir / "serverconfig.json").write_text(json.dumps(SAMPLE, indent=2))
    return settings


@pytest.fixture(autouse=True)
def no_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)


def entity_spawning(service: GameConfigService, role: str = "admin") -> dict[str, object]:
    settings = service.get_settings(role).to_dict()["settings"]
    return next(s for s in settings if s["key"] == "EntitySpawning")


def config_text(settings: Settings) -> str:
    return (settings.serverdata_dir / "serverconfig.json").read_text()


class TestDefinition:
    def test_entity_spawning_is_the_one_game_setting(self) -> None:
        game = {key for key, s in LIVE_SETTINGS.items() if s.location == "game"}
        assert game == {"EntitySpawning"}
        assert game == GAME_KEPT_KEYS, "config init skips the same keys"
        assert LIVE_SETTINGS["EntitySpawning"].default is None


# ==============================================================================
# GET: value and source (AC 7)
# ==============================================================================


class TestRead:
    def test_unknown_before_any_reply(self, settings: Settings) -> None:
        game = Game(settings, running=False)

        result = entity_spawning(game.config_service())

        assert result["value"] is None
        assert result["source"] == "unknown"
        assert "observed_at" not in result
        assert "default" not in result

    async def test_game_while_running_and_seen_since_start(self, settings: Settings) -> None:
        game = Game(settings, running=True)
        game.state = False
        await game.become_ready()

        result = entity_spawning(game.config_service())

        assert result["value"] is False, "from the game, not the file's True"
        assert result["source"] == "game"
        assert result["observed_at"] == NOW.isoformat()

    async def test_last_seen_after_the_game_stops(self, settings: Settings) -> None:
        game = Game(settings, running=True)
        game.state = False
        await game.become_ready()
        game.watcher.reset()
        game.service.game_server_pid = None

        result = entity_spawning(game.config_service(), "monitor")

        assert result["value"] is False
        assert result["source"] == "last_seen"

    def test_last_seen_from_an_earlier_api_run(self, settings: Settings) -> None:
        settings.state_dir.mkdir(parents=True, exist_ok=True)
        (settings.state_dir / "entity_spawning.json").write_text(
            json.dumps({"value": True, "observed_at": NOW.isoformat(), "via": "query"})
        )
        game = Game(settings, running=True)  # running, but not seen since this start

        result = entity_spawning(game.config_service())

        assert result["value"] is True
        assert result["source"] == "last_seen"

    def test_env_managed(self, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_VAR, "false")

        result = entity_spawning(Game(settings, running=False).config_service())

        assert result["env_managed"] is True
        assert result["env_var"] == ENV_VAR


# ==============================================================================
# Updates (AC 3, 4, 5)
# ==============================================================================


class TestUpdate:
    async def test_set_through_the_console_while_ready(self, settings: Settings) -> None:
        game = Game(settings, running=True)
        await game.become_ready()
        before = config_text(settings)

        result = await game.config_service().update_setting("EntitySpawning", False)

        assert game.commands == ["/serverconfig entityspawning false"]
        assert result.method == "console_command"
        assert result.value is False
        assert result.pending_restart is False
        assert game.watcher.record is not None and game.watcher.record.via == "set"
        assert config_text(settings) == before

    async def test_stopped_is_409_and_sends_nothing(self, settings: Settings) -> None:
        game = Game(settings, running=False)
        before = config_text(settings)

        with pytest.raises(SettingNeedsRunningServerError):
            await game.config_service().update_setting("EntitySpawning", False)

        assert game.commands == []
        assert config_text(settings) == before

    async def test_running_but_not_ready_is_409(self, settings: Settings) -> None:
        game = Game(settings, running=True)

        with pytest.raises(SettingNeedsRunningServerError):
            await game.config_service().update_setting("EntitySpawning", True)

        assert game.commands == []

    async def test_no_reply_is_an_error_and_keeps_the_record(self, settings: Settings) -> None:
        game = Game(settings, running=True)
        await game.become_ready()
        game.answers = False
        before = game.watcher.record

        with pytest.raises(SettingNoReplyError):
            await game.config_service().update_setting("EntitySpawning", False)

        assert game.watcher.record == before

    async def test_env_managed_is_refused_first(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ENV_VAR, "true")
        game = Game(settings, running=True)
        await game.become_ready()

        with pytest.raises(SettingEnvManagedError):
            await game.config_service().update_setting("EntitySpawning", False)

        assert game.commands == []

    async def test_strings_are_coerced_as_for_other_bools(self, settings: Settings) -> None:
        game = Game(settings, running=True)
        await game.become_ready()

        result = await game.config_service().update_setting("EntitySpawning", "false")

        assert result.value is False
        assert game.commands == ["/serverconfig entityspawning false"]


# ==============================================================================
# Routes (AC 4, 5)
# ==============================================================================


@pytest.fixture
def routed(settings: Settings) -> Generator[tuple[FastAPI, Game]]:
    game = Game(settings, running=False)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_server_service] = lambda: game.service
    app.dependency_overrides[get_game_config_service] = game.config_service
    yield app, game
    app.dependency_overrides.clear()


class TestRoutes:
    def test_stopped_is_409(
        self, routed: tuple[FastAPI, Game], admin_headers: dict[str, str]
    ) -> None:
        client_app, _ = routed

        response = TestClient(client_app).post(URL, headers=admin_headers, json={"value": False})

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == ErrorCode.SETTING_NEEDS_RUNNING_SERVER

    def test_no_reply_is_502(
        self, routed: tuple[FastAPI, Game], admin_headers: dict[str, str]
    ) -> None:
        """The service's no-reply error (tested above) maps to 502."""
        client_app, _ = routed
        failing = MagicMock(spec=GameConfigService)
        failing.update_setting = AsyncMock(side_effect=SettingNoReplyError("EntitySpawning"))
        app.dependency_overrides[get_game_config_service] = lambda: failing

        response = TestClient(client_app).post(URL, headers=admin_headers, json={"value": False})

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == ErrorCode.SETTING_UPDATE_FAILED

    def test_monitor_cannot_change_it(
        self, routed: tuple[FastAPI, Game], monitor_headers: dict[str, str]
    ) -> None:
        client_app, game = routed

        response = TestClient(client_app).post(URL, headers=monitor_headers, json={"value": False})

        assert response.status_code == 403
        assert game.commands == []


# ==============================================================================
# Config init (AC 8)
# ==============================================================================


class TestConfigInit:
    def test_the_env_var_is_not_written_to_a_new_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, admin_headers: dict[str, str]
    ) -> None:
        settings = Settings(data_dir=tmp_path / "fresh", api_key_admin=admin_headers["X-API-Key"])
        monkeypatch.setenv(ENV_VAR, "false")
        monkeypatch.setenv("VS_CFG_MAX_CLIENTS", "8")
        service = ConfigInitService(settings=settings)
        service.config_path.parent.mkdir(parents=True)

        service.initialize_config()

        config = json.loads(service.config_path.read_text())
        assert "EntitySpawning" not in config
        assert config["MaxClients"] == 8, "other VS_CFG_* variables still apply"
