"""Router tests for saving config files (Story 23.4, FR314-FR318; Epic 23 ADR-4).

PUT /api/v1alpha1/config/files/{path} and POST /api/v1alpha1/config/files/validate,
over HTTP, with a real ServerService on a temporary data directory (no game process).
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import ServerState
from vintagestory_api.routers.config import get_config_files_service
from vintagestory_api.services.config_files import CONFIG_FILE_MAX_BYTES, ConfigFilesService
from vintagestory_api.services.server import (
    GameServerNotStoppedError,
    ServerService,
    get_server_service,
)

FILES_URL = "/api/v1alpha1/config/files"
VALIDATE_URL = "/api/v1alpha1/config/files/validate"
ADMIN = {"X-API-Key": TEST_ADMIN_KEY}
MONITOR = {"X-API-Key": TEST_MONITOR_KEY}


def _version(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    settings = Settings(
        data_dir=tmp_path,
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        debug=True,
    )
    (settings.serverdata_dir / "ModConfig").mkdir(parents=True)
    return settings


@pytest.fixture
def server_service(settings: Settings) -> ServerService:
    return ServerService(settings)


@pytest.fixture
def client(settings: Settings, server_service: ServerService) -> Generator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_server_service] = lambda: server_service
    app.dependency_overrides[get_config_files_service] = lambda: ConfigFilesService(settings)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mod_config(settings: Settings) -> Path:
    path = settings.serverdata_dir / "ModConfig" / "x.json"
    path.write_bytes(b'{"a": 1}')
    return path


class TestSave:
    def test_admin_saves_the_text(self, client: TestClient, mod_config: Path) -> None:
        """AC 1."""
        text = '{\n  // kept\n  "a":   2,\n}\n'

        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": text, "version": _version(b'{"a": 1}')},
        )

        assert response.status_code == 200
        assert response.json()["data"] == {
            "filename": "ModConfig/x.json",
            "version": _version(text.encode()),
        }
        assert response.headers["Cache-Control"] == "no-store"
        assert mod_config.read_text() == text

    def test_a_save_then_a_read_round_trips(self, client: TestClient, mod_config: Path) -> None:
        read = client.get(f"{FILES_URL}/ModConfig/x.json", headers=ADMIN).json()["data"]
        client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": '{"a": 3} // c', "version": read["version"]},
        )

        again = client.get(f"{FILES_URL}/ModConfig/x.json", headers=ADMIN).json()["data"]

        assert again["text"] == '{"a": 3} // c'
        assert again["content"] == {"a": 3}

    @pytest.mark.parametrize("url", [f"{FILES_URL}/ModConfig/x.json", VALIDATE_URL])
    def test_monitor_is_forbidden(self, client: TestClient, mod_config: Path, url: str) -> None:
        """AC 2, AC 9."""
        body = (
            {"filename": "ModConfig/x.json", "text": "{}"}
            if url == VALIDATE_URL
            else {"text": "{}", "version": _version(b'{"a": 1}')}
        )
        method = client.post if url == VALIDATE_URL else client.put

        response = method(url, headers=MONITOR, json=body)

        assert response.status_code == 403
        assert mod_config.read_bytes() == b'{"a": 1}'

    @pytest.mark.parametrize(
        ("path", "status", "code"),
        [
            ("ModConfig/x.txt", 400, ErrorCode.CONFIG_FILE_NOT_SUPPORTED),
            ("ModConfig/missing.json", 404, ErrorCode.CONFIG_FILE_NOT_FOUND),
            ("ModConfig/dir.json", 400, ErrorCode.CONFIG_FILE_NOT_SUPPORTED),
        ],
    )
    def test_path_refusals(
        self, client: TestClient, settings: Settings, path: str, status: int, code: str
    ) -> None:
        """AC 2."""
        (settings.serverdata_dir / "ModConfig" / "x.txt").write_text("{}")
        (settings.serverdata_dir / "ModConfig" / "dir.json").mkdir()

        response = client.put(
            f"{FILES_URL}/{path}", headers=ADMIN, json={"text": "{}", "version": _version(b"{}")}
        )

        assert response.status_code == status
        assert response.json()["detail"]["code"] == code
        assert response.headers["Cache-Control"] == "no-store"

    def test_traversal_is_400(self, client: TestClient) -> None:
        response = client.put(
            f"{FILES_URL}/ModConfig/..%2F..%2Fx.json",
            headers=ADMIN,
            json={"text": "{}", "version": _version(b"{}")},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_PATH_INVALID

    def test_too_large_is_413(self, client: TestClient, mod_config: Path) -> None:
        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": " " * (CONFIG_FILE_MAX_BYTES + 1), "version": _version(b'{"a": 1}')},
        )

        assert response.status_code == 413
        assert mod_config.read_bytes() == b'{"a": 1}'

    def test_invalid_text_is_422_with_a_position(
        self, client: TestClient, mod_config: Path
    ) -> None:
        """AC 3."""
        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": '{\n  "a": 1\n  "b": 2\n}', "version": _version(b'{"a": 1}')},
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.CONFIG_FILE_INVALID
        assert detail["parse_error"]["line"] == 3
        assert detail["parse_error"]["column"] == 3
        assert response.headers["Cache-Control"] == "no-store"
        assert mod_config.read_bytes() == b'{"a": 1}'

    def test_root_serverconfig_with_a_comment_is_422(
        self, client: TestClient, settings: Settings
    ) -> None:
        path = settings.serverdata_dir / "serverconfig.json"
        path.write_bytes(b'{"Port": 42420}')

        response = client.put(
            f"{FILES_URL}/serverconfig.json",
            headers=ADMIN,
            json={"text": '{"Port": 1} // c', "version": _version(b'{"Port": 42420}')},
        )

        assert response.status_code == 422
        assert path.read_bytes() == b'{"Port": 42420}'

    @pytest.mark.parametrize("state", [ServerState.STARTING, ServerState.STOPPING])
    def test_not_stopped_is_409(
        self,
        client: TestClient,
        mod_config: Path,
        server_service: ServerService,
        state: ServerState,
    ) -> None:
        """AC 4."""
        server_service._server_state = state

        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": "{}", "version": _version(b'{"a": 1}')},
        )

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_SERVER_RUNNING
        assert response.headers["Cache-Control"] == "no-store"
        assert mod_config.read_bytes() == b'{"a": 1}'

    def test_busy_is_409(
        self,
        client: TestClient,
        mod_config: Path,
        server_service: ServerService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC 4: the lock is held by another lifecycle operation."""

        @asynccontextmanager
        async def busy() -> AsyncGenerator[None]:
            raise GameServerNotStoppedError("busy")
            yield

        monkeypatch.setattr(server_service, "config_write", busy)

        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": "{}", "version": _version(b'{"a": 1}')},
        )

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_SERVER_BUSY
        assert mod_config.read_bytes() == b'{"a": 1}'

    def test_stale_version_is_409(self, client: TestClient, mod_config: Path) -> None:
        """AC 6."""
        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": "{}", "version": _version(b"something else")},
        )

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_CHANGED
        assert mod_config.read_bytes() == b'{"a": 1}'

    def test_write_failure_is_500_without_a_path(
        self,
        client: TestClient,
        mod_config: Path,
        settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC 7."""

        def fail(*args: object, **kwargs: object) -> None:
            raise PermissionError(13, "Permission denied", str(mod_config))

        monkeypatch.setattr(os, "replace", fail)

        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": "{}", "version": _version(b'{"a": 1}')},
        )

        assert response.status_code == 500
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_WRITE_FAILED
        assert str(settings.data_dir) not in response.text
        monkeypatch.undo()
        assert mod_config.read_bytes() == b'{"a": 1}'

    def test_serverconfig_save_drops_the_pending_edits_it_changes(
        self, client: TestClient, settings: Settings, server_service: ServerService
    ) -> None:
        """AC 8."""
        before = json.dumps({"Port": 42421, "Ip": "10.0.0.5"}).encode()
        (settings.serverdata_dir / "serverconfig.json").write_bytes(before)
        server_service.pending_config_edits.record("Port", 42421)
        server_service.pending_config_edits.record("Ip", "10.0.0.5")

        response = client.put(
            f"{FILES_URL}/serverconfig.json",
            headers=ADMIN,
            json={
                "text": json.dumps({"Port": 50000, "Ip": "10.0.0.5"}),
                "version": _version(before),
            },
        )

        assert response.status_code == 200
        assert set(server_service.pending_config_edits.edits) == {"Ip"}

    def test_another_file_drops_no_pending_edit(
        self, client: TestClient, mod_config: Path, server_service: ServerService
    ) -> None:
        server_service.pending_config_edits.record("Port", 42421)

        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": '{"Port": 1}', "version": _version(b'{"a": 1}')},
        )

        assert response.status_code == 200
        assert set(server_service.pending_config_edits.edits) == {"Port"}


class TestValidate:
    @pytest.mark.parametrize(
        ("filename", "text", "valid"),
        [
            ("ModConfig/new.json", "{// c\n a: 1,}", True),
            ("ModConfig/new.json", '{\n  "a": 1\n  "b": 2\n}', False),
            ("serverconfig.json", '{"a": 1,}', False),
            ("serverconfig.json", '{"a": 1}', True),
        ],
    )
    def test_checks_without_writing(
        self, client: TestClient, settings: Settings, filename: str, text: str, valid: bool
    ) -> None:
        """AC 9."""
        response = client.post(
            VALIDATE_URL, headers=ADMIN, json={"filename": filename, "text": text}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["valid"] is valid
        assert (data["parse_error"] is None) is valid
        assert response.headers["Cache-Control"] == "no-store"
        assert not (settings.serverdata_dir / "ModConfig" / "new.json").exists()

    def test_whatever_the_server_state(
        self, client: TestClient, server_service: ServerService
    ) -> None:
        server_service._server_state = ServerState.STARTING

        response = client.post(
            VALIDATE_URL, headers=ADMIN, json={"filename": "ModConfig/x.json", "text": "{}"}
        )

        assert response.json()["data"] == {"valid": True, "parse_error": None}

    def test_bad_path_is_400(self, client: TestClient) -> None:
        response = client.post(
            VALIDATE_URL, headers=ADMIN, json={"filename": "../x.json", "text": "{}"}
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_PATH_INVALID
