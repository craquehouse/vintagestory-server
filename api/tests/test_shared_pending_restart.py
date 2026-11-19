"""Game settings and mods share one pending-restart state (Story 22.2, AC 13, FR306)."""

import asyncio
import json
import zipfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import create_app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.server import LifecycleAction, LifecycleResponse, ServerState
from vintagestory_api.routers import config as config_router
from vintagestory_api.services import mods as mods_module
from vintagestory_api.services.mods import ModService, get_mod_service, get_restart_state
from vintagestory_api.services.server import ServerService, get_server_service

ADMIN_KEY = "shared-restart-admin-KEY-1"
HEADERS = {"X-API-Key": ADMIN_KEY}


@pytest.fixture(autouse=True)
def fresh_restart_state(monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh shared singleton for each test; monkeypatch restores the old one after
    monkeypatch.setattr(mods_module, "_restart_state", None)
    # get_server_status reads the disk space through Settings() from the environment
    monkeypatch.setattr("vintagestory_api.routers.health.get_disk_space_data", lambda: None)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(api_key_admin=ADMIN_KEY, debug=False, data_dir=tmp_path / "data")


@pytest.fixture
def service(settings: Settings) -> Generator[ServerService]:
    """An installed, stopped server on a temp dir, with a serverconfig.json."""
    settings.server_dir.mkdir(parents=True, exist_ok=True)
    (settings.server_dir / "VintagestoryServer.dll").touch()
    (settings.server_dir / "VintagestoryLib.dll").touch()
    settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
    (settings.vsmanager_dir / "current_version").write_text("1.22.7")
    settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
    (settings.serverdata_dir / "serverconfig.json").write_text(json.dumps({"Port": 42420}))
    yield ServerService(settings)


@pytest.fixture
def mod_service(tmp_path: Path) -> ModService:
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir()
    return ModService(
        state_dir=tmp_path / "state",
        mods_dir=mods_dir,
        cache_dir=tmp_path / "cache",
        restart_state=get_restart_state(),
    )


@pytest.fixture
def client(
    tmp_path: Path,
    settings: Settings,
    service: ServerService,
    mod_service: ModService,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>SPA index</html>")
    app = create_app(settings, static_dir=static_dir)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_server_service] = lambda: service
    app.dependency_overrides[get_mod_service] = lambda: mod_service
    # /healthz calls get_server_service directly, not through a dependency
    monkeypatch.setattr("vintagestory_api.routers.health.get_server_service", lambda: service)
    # No `with` block: the lifespan does not run, so nothing is written under dev/
    return TestClient(app)


def lifecycle(action: LifecycleAction, new_state: ServerState) -> LifecycleResponse:
    return LifecycleResponse(
        action=action,
        previous_state=ServerState.INSTALLED,
        new_state=new_state,
        message="mocked",
    )


def pending_everywhere(client: TestClient) -> tuple[bool, bool]:
    """The flag as /healthz and the mods list (the web's banner) report it."""
    health = client.get("/healthz")
    assert health.status_code == 200
    mods = client.get("/api/v1alpha1/mods", headers=HEADERS)
    assert mods.status_code == 200
    return (
        health.json()["data"]["game_server_pending_restart"],
        mods.json()["data"]["pending_restart"],
    )


def save_port(client: TestClient) -> None:
    response = client.post(
        "/api/v1alpha1/config/game/settings/Port", json={"value": 42421}, headers=HEADERS
    )
    assert response.status_code == 200


def test_config_router_state_is_the_mods_state() -> None:
    assert config_router.get_pending_restart_state() is get_restart_state()


def test_game_setting_change_shows_until_a_restart(
    client: TestClient, service: ServerService, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert pending_everywhere(client) == (False, False)

    save_port(client)
    assert pending_everywhere(client) == (True, True)

    # No dotnet: the start is mocked; the game is stopped, so nothing is stopped
    monkeypatch.setattr(
        service,
        "_start_server_locked",
        AsyncMock(return_value=lifecycle(LifecycleAction.START, ServerState.RUNNING)),
    )
    response = client.post("/api/v1alpha1/server/restart", headers=HEADERS)
    assert response.status_code == 200
    assert pending_everywhere(client) == (False, False)


# Controller decision during validation: any successful start loads every pending
# change, so it clears the shared flag (Start button, auto-start, restart).


def test_start_after_a_game_setting_change_clears_the_flag(
    client: TestClient, service: ServerService, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_port(client)
    assert pending_everywhere(client) == (True, True)

    monkeypatch.setattr(
        service,
        "_start_server_locked",
        AsyncMock(return_value=lifecycle(LifecycleAction.START, ServerState.RUNNING)),
    )
    response = client.post("/api/v1alpha1/server/start", headers=HEADERS)
    assert response.status_code == 200
    assert pending_everywhere(client) == (False, False)


def test_stop_then_start_after_a_mod_change_clears_the_flag(
    client: TestClient,
    service: ServerService,
    mod_service: ModService,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with zipfile.ZipFile(tmp_path / "mods" / "examplemod_1.0.0.zip", "w") as archive:
        archive.writestr(
            "modinfo.json",
            json.dumps({"modid": "examplemod", "name": "Example Mod", "version": "1.0.0"}),
        )
    mod_service.state_manager.sync_state_with_disk()
    mod_service.set_server_running(True)
    mod_service.disable_mod("examplemod")
    assert pending_everywhere(client) == (True, True)

    monkeypatch.setattr(
        service,
        "_stop_server_locked",
        AsyncMock(return_value=lifecycle(LifecycleAction.STOP, ServerState.INSTALLED)),
    )
    assert client.post("/api/v1alpha1/server/stop", headers=HEADERS).status_code == 200
    # A stop loads nothing: the change still waits
    assert pending_everywhere(client) == (True, True)

    monkeypatch.setattr(
        service,
        "_start_server_locked",
        AsyncMock(return_value=lifecycle(LifecycleAction.START, ServerState.RUNNING)),
    )
    assert client.post("/api/v1alpha1/server/start", headers=HEADERS).status_code == 200
    assert pending_everywhere(client) == (False, False)


def test_failed_start_keeps_the_flag(client: TestClient) -> None:
    save_port(client)

    # The real start path, with a spawn that fails
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("Cannot spawn process")):
        response = client.post("/api/v1alpha1/server/start", headers=HEADERS)

    assert response.status_code == 500
    assert pending_everywhere(client) == (True, True)


# Story 22.7: a restart-required change saved while a game process lives is recorded


class _FakeStdin:
    def write(self, data: bytes) -> None:
        return None

    async def drain(self) -> None:
        return None


class _LiveProcess:
    """A game process that stays alive for the test (`returncode` None)."""

    def __init__(self) -> None:
        self.pid = 4242
        self.returncode: int | None = None
        self.stdin = _FakeStdin()


class _EmptyStream:
    async def readline(self) -> bytes:
        return b""


class _StoppableProcess(_LiveProcess):
    """A live process that exits on SIGTERM; its streams are at EOF."""

    def __init__(self) -> None:
        super().__init__()
        self.stdout = _EmptyStream()
        self.stderr = _EmptyStream()

    def send_signal(self, sig: int) -> None:
        self.returncode = 0

    async def wait(self) -> int:
        while self.returncode is None:
            await asyncio.sleep(0)
        return self.returncode

    def kill(self) -> None:
        self.returncode = -9


def test_port_saved_while_running_is_recorded(
    client: TestClient,
    service: ServerService,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "_process", _LiveProcess())
    monkeypatch.setattr(service, "_server_state", ServerState.RUNNING)

    save_port(client)

    assert service.pending_config_edits.edits["Port"].value == 42421
    stored = json.loads((settings.state_dir / "pending-config-edits.json").read_text())
    assert stored["edits"]["Port"]["value"] == 42421


def test_port_saved_while_running_survives_the_game_write_through_stop_and_start(
    client: TestClient,
    service: ServerService,
    settings: Settings,
    mod_service: ModService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story 22.7 AC 1 through the routes."""
    # The stop and start tell the mod service; never one built from Settings() (dev/)
    monkeypatch.setattr(mods_module, "_mod_service", mod_service)
    config_path = settings.serverdata_dir / "serverconfig.json"
    process = _StoppableProcess()

    async def spawn(*args: object, **kwargs: object) -> _StoppableProcess:
        return _StoppableProcess()

    monkeypatch.setattr(service, "_process", process)
    monkeypatch.setattr(service, "_server_state", ServerState.RUNNING)
    save_port(client)
    # The game's own write after a live /serverconfig command
    config_path.write_text(json.dumps({"Port": 42420}))

    assert client.post("/api/v1alpha1/server/stop", headers=HEADERS).status_code == 200
    assert json.loads(config_path.read_text())["Port"] == 42421

    monkeypatch.setattr("asyncio.create_subprocess_exec", spawn)
    assert client.post("/api/v1alpha1/server/start", headers=HEADERS).status_code == 200

    health = client.get("/healthz")
    assert health.json()["data"]["game_server_pending_restart"] is False
    assert service.pending_config_edits.edits == {}
