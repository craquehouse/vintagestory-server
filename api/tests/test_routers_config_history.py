"""Router tests for config file history (Story 23.6, FR321, FR323; Epic 23 ADR-7).

GET /api/v1alpha1/config/history/{path} (list, or ?revision= to read one) and
POST /api/v1alpha1/config/history/{path}/restore, over HTTP, with a real ServerService
on a temporary data directory (no game process).
"""

from __future__ import annotations

import hashlib
from collections.abc import Generator
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
from vintagestory_api.services.config_files import ConfigFilesService
from vintagestory_api.services.server import ServerService, get_server_service

FILES_URL = "/api/v1alpha1/config/files"
HISTORY_URL = "/api/v1alpha1/config/history"
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
def saved_twice(client: TestClient, settings: Settings) -> Path:
    """ModConfig/x.json saved from {"a": 1} to {"a": 2} to {"a": 3}."""
    path = settings.serverdata_dir / "ModConfig" / "x.json"
    path.write_bytes(b'{"a": 1}')
    for before, after in ((b'{"a": 1}', '{"a": 2}'), (b'{"a": 2}', '{"a": 3}')):
        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": after, "version": _version(before)},
        )
        assert response.status_code == 200
    return path


class TestList:
    def test_lists_newest_first(self, client: TestClient, saved_twice: Path) -> None:
        response = client.get(f"{HISTORY_URL}/ModConfig/x.json", headers=ADMIN)

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        data = response.json()["data"]
        assert data["filename"] == "ModConfig/x.json"
        revisions = data["revisions"]
        assert [r["sha256"] for r in revisions] == [_version(b'{"a": 2}'), _version(b'{"a": 1}')]
        assert set(revisions[0]) == {"id", "saved_at", "saved_by", "size", "sha256"}
        assert revisions[0]["saved_by"] == "admin"

    def test_no_history_is_an_empty_list(self, client: TestClient) -> None:
        response = client.get(f"{HISTORY_URL}/ModConfig/never.json", headers=ADMIN)

        assert response.status_code == 200
        assert response.json()["data"] == {"filename": "ModConfig/never.json", "revisions": []}


class TestRead:
    def test_reads_a_revision(self, client: TestClient, saved_twice: Path) -> None:
        revisions = client.get(f"{HISTORY_URL}/ModConfig/x.json", headers=ADMIN).json()["data"][
            "revisions"
        ]

        response = client.get(
            f"{HISTORY_URL}/ModConfig/x.json",
            headers=ADMIN,
            params={"revision": revisions[1]["id"]},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["text"] == '{"a": 1}'
        assert data["revision"]["id"] == revisions[1]["id"]

    @pytest.mark.parametrize("revision", ["../x", "20261119T000000000000Z/../a", "nope"])
    def test_a_malformed_id_is_400(
        self, client: TestClient, saved_twice: Path, revision: str
    ) -> None:
        response = client.get(
            f"{HISTORY_URL}/ModConfig/x.json", headers=ADMIN, params={"revision": revision}
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_REVISION_INVALID
        assert response.headers["Cache-Control"] == "no-store"

    def test_an_unknown_id_is_404(self, client: TestClient, saved_twice: Path) -> None:
        response = client.get(
            f"{HISTORY_URL}/ModConfig/x.json",
            headers=ADMIN,
            params={"revision": "20200101T000000000000Z"},
        )

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_REVISION_NOT_FOUND


class TestRestore:
    def _revisions(self, client: TestClient) -> list[dict[str, object]]:
        return client.get(f"{HISTORY_URL}/ModConfig/x.json", headers=ADMIN).json()["data"][
            "revisions"
        ]

    def test_restores_and_keeps_the_current_text(
        self, client: TestClient, saved_twice: Path
    ) -> None:
        oldest = self._revisions(client)[1]

        response = client.post(
            f"{HISTORY_URL}/ModConfig/x.json/restore",
            headers=ADMIN,
            json={"revision": oldest["id"], "version": _version(b'{"a": 3}')},
        )

        assert response.status_code == 200
        assert response.json()["data"] == {
            "filename": "ModConfig/x.json",
            "version": _version(b'{"a": 1}'),
        }
        assert saved_twice.read_bytes() == b'{"a": 1}'
        assert self._revisions(client)[0]["sha256"] == _version(b'{"a": 3}')

    def test_a_stale_version_is_409(self, client: TestClient, saved_twice: Path) -> None:
        oldest = self._revisions(client)[1]

        response = client.post(
            f"{HISTORY_URL}/ModConfig/x.json/restore",
            headers=ADMIN,
            json={"revision": oldest["id"], "version": _version(b'{"a": 1}')},
        )

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_CHANGED
        assert saved_twice.read_bytes() == b'{"a": 3}'

    def test_a_running_server_is_409(
        self, client: TestClient, saved_twice: Path, server_service: ServerService
    ) -> None:
        oldest = self._revisions(client)[1]
        server_service._server_state = ServerState.STARTING

        response = client.post(
            f"{HISTORY_URL}/ModConfig/x.json/restore",
            headers=ADMIN,
            json={"revision": oldest["id"], "version": _version(b'{"a": 3}')},
        )

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_SERVER_RUNNING

    def test_an_unknown_revision_is_404(self, client: TestClient, saved_twice: Path) -> None:
        response = client.post(
            f"{HISTORY_URL}/ModConfig/x.json/restore",
            headers=ADMIN,
            json={"revision": "20200101T000000000000Z", "version": _version(b'{"a": 3}')},
        )

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_REVISION_NOT_FOUND


class TestRefusals:
    @pytest.mark.parametrize("method", ["list", "read", "restore"])
    def test_monitor_is_forbidden(self, client: TestClient, saved_twice: Path, method: str) -> None:
        if method == "restore":
            response = client.post(
                f"{HISTORY_URL}/ModConfig/x.json/restore",
                headers=MONITOR,
                json={"revision": "20200101T000000000000Z", "version": _version(b"x")},
            )
        else:
            params = {"revision": "20200101T000000000000Z"} if method == "read" else None
            response = client.get(f"{HISTORY_URL}/ModConfig/x.json", headers=MONITOR, params=params)

        assert response.status_code == 403

    def test_traversal_is_400(self, client: TestClient) -> None:
        response = client.get(f"{HISTORY_URL}/ModConfig/..%2F..%2Fx.json", headers=ADMIN)

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_PATH_INVALID

    def test_a_history_failure_refuses_the_save(
        self, client: TestClient, settings: Settings
    ) -> None:
        path = settings.serverdata_dir / "ModConfig" / "x.json"
        path.write_bytes(b'{"a": 1}')
        history_root = settings.state_dir / "config-history"
        history_root.parent.mkdir(parents=True, exist_ok=True)
        history_root.write_text("not a directory")

        response = client.put(
            f"{FILES_URL}/ModConfig/x.json",
            headers=ADMIN,
            json={"text": '{"a": 2}', "version": _version(b'{"a": 1}')},
        )

        assert response.status_code == 500
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_HISTORY_WRITE_FAILED
        assert str(settings.data_dir) not in response.text
        assert path.read_bytes() == b'{"a": 1}'


class TestReviewFixesOverHttp:
    """Story 23.6 review M1: every refusal is typed and never cached."""

    @pytest.mark.parametrize("revision", ["", "2" * 100])
    def test_an_empty_or_long_revision_is_400_on_restore(
        self, client: TestClient, saved_twice: Path, revision: str
    ) -> None:
        response = client.post(
            f"{HISTORY_URL}/ModConfig/x.json/restore",
            headers=ADMIN,
            json={"revision": revision, "version": _version(b'{"a": 3}')},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_REVISION_INVALID
        assert response.headers["Cache-Control"] == "no-store"

    def test_a_long_revision_is_400_on_read(self, client: TestClient, saved_twice: Path) -> None:
        response = client.get(
            f"{HISTORY_URL}/ModConfig/x.json", headers=ADMIN, params={"revision": "2" * 100}
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_REVISION_INVALID

    def test_the_monitor_403_is_not_cached(self, client: TestClient) -> None:
        response = client.get(f"{HISTORY_URL}/ModConfig/x.json", headers=MONITOR)

        assert response.status_code == 403
        assert response.headers["Cache-Control"] == "no-store"
