"""A mod can be installed by uploading its file (Story 28.2, Epic 28 ADR-3 and ADR-4)."""

import asyncio
import io
import json
import zipfile
from collections.abc import AsyncIterator, Generator, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.mod_updates import StoredModRecord
from vintagestory_api.models.mods import ModState
from vintagestory_api.services import mods as mods_module
from vintagestory_api.services.mod_api import ModNotFoundError as ApiModNotFoundError
from vintagestory_api.services.mod_updates import (
    ModUpdateService,
    ModUpdateStore,
    get_mod_update_service,
)
from vintagestory_api.services.mod_upload import (
    ModFileInvalidError,
    ModFileTooLargeError,
    clear_incoming,
    incoming_file,
    safe_archive_name,
    write_limited,
)
from vintagestory_api.services.mods import (
    ModAlreadyInstalledError,
    ModFileConflictError,
    ModFileMissingError,
    ModOperationInProgressError,
    ModService,
    ModVersionChangeFailedError,
    get_mod_service,
)
from vintagestory_api.services.pending_restart import PendingRestartState

UPLOAD_URL = "/api/v1alpha1/mods/upload"
ADMIN = {"X-API-Key": TEST_ADMIN_KEY}
MONITOR = {"X-API-Key": TEST_MONITOR_KEY}


def mod_zip(modinfo: dict[str, Any] | None, *, extra: dict[str, bytes] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        if modinfo is not None:
            zf.writestr("modinfo.json", json.dumps(modinfo))
        for name, data in (extra or {}).items():
            zf.writestr(name, data)
    return buffer.getvalue()


def demo_zip(modid: str = "demo", version: str = "1.0.0") -> bytes:
    return mod_zip({"modid": modid, "name": "Demo", "version": version})


@pytest.fixture
def service(tmp_path: Path) -> ModService:
    return ModService(
        state_dir=tmp_path / "state",
        mods_dir=tmp_path / "mods",
        restart_state=PendingRestartState(),
        cache_dir=tmp_path / "cache",
        game_version_provider=lambda: "1.22.7",
    )


def received(service: ModService, name: str, data: bytes) -> Path:
    """A file as the route leaves it for `install_archive`: in a working folder."""
    folder = service.cache_dir / "incoming" / "test"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    return path


def installed(
    service: ModService,
    modid: str,
    version: str,
    filename: str,
    *,
    enabled: bool = True,
    asset_id: int = 15312,
) -> Path:
    mods_dir = service.state_manager.mods_dir
    mods_dir.mkdir(parents=True, exist_ok=True)
    name = filename if enabled else f"{filename}.disabled"
    path = mods_dir / name
    path.write_bytes(demo_zip(modid, version))
    service.state_manager.set_mod_state(
        name,
        ModState(
            filename=name,
            slug=modid,
            version=version,
            enabled=enabled,
            installed_at=datetime(2026, 1, 1, tzinfo=UTC),
            asset_id=asset_id,
            source="moddb",
        ),
    )
    service.state_manager.save()
    return path


class TestSafeArchiveName:
    @pytest.mark.parametrize("name", ["demo_1.0.0.zip", "Demo.ZIP", "a b (fork).zip"])
    def test_accepts_a_plain_zip_name(self, name: str) -> None:
        assert safe_archive_name(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "",
            ".zip",
            ".hidden.zip",
            "demo.zip.disabled",
            "demo.tar.gz",
            "../demo.zip",
            "dir/demo.zip",
            "dir\\demo.zip",
            "de\nmo.zip",
            "de\x00mo.zip",
            "a" * 252 + ".zip",
        ],
    )
    def test_refuses_anything_else(self, name: str) -> None:
        assert safe_archive_name(name) is None


class TestReceiving:
    @pytest.mark.asyncio
    async def test_write_limited_stops_past_the_limit(self, tmp_path: Path) -> None:
        async def chunks() -> AsyncIterator[bytes]:
            for _ in range(3):
                yield b"x" * 10

        with pytest.raises(ModFileTooLargeError):
            await write_limited(chunks(), tmp_path / "f.zip", 25)

    @pytest.mark.asyncio
    async def test_write_limited_writes_up_to_the_limit(self, tmp_path: Path) -> None:
        async def chunks() -> AsyncIterator[bytes]:
            yield b"x" * 10
            yield b"y" * 10

        assert await write_limited(chunks(), tmp_path / "f.zip", 20) == 20
        assert (tmp_path / "f.zip").read_bytes() == b"x" * 10 + b"y" * 10

    def test_the_working_folder_goes_on_every_exit(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError), incoming_file(tmp_path, "a.zip") as path:
            path.write_bytes(b"x")
            raise RuntimeError
        assert list((tmp_path / "incoming").iterdir()) == []

    def test_clear_incoming_removes_leftovers(self, tmp_path: Path) -> None:
        root = tmp_path / "incoming"
        (root / "abc").mkdir(parents=True)
        (root / "abc" / "a.zip").write_bytes(b"x")
        (root / "stray").write_bytes(b"x")

        assert clear_incoming(tmp_path) == 2
        assert list(root.iterdir()) == []
        assert clear_incoming(tmp_path / "nothing") == 0

    def test_start_up_clears_incoming(
        self, service: ModService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Story 28.2 AC 7: a file a crash left half-received is deleted at start-up."""
        leftover = service.cache_dir / "incoming" / "abc" / "a.zip"
        leftover.parent.mkdir(parents=True)
        leftover.write_bytes(b"x")
        monkeypatch.setattr(mods_module, "get_mod_service", lambda: service)

        mods_module.prepare_mod_files()

        assert not leftover.parent.exists()


class TestInstallArchive:
    def test_installs_a_new_mod_with_source_upload(self, service: ModService) -> None:
        path = received(service, "demo-fork.zip", demo_zip())

        result = service.install_archive(path, source="upload")

        assert (result.slug, result.version, result.filename) == ("demo", "1.0.0", "demo-fork.zip")
        assert result.compatibility == "not_verified"
        assert (result.source, result.replaced, result.previous_version) == ("upload", False, None)
        assert result.pending_restart is False
        state = service.state_manager.get_mod_by_slug("demo")
        assert state is not None
        assert (state.filename, state.source, state.asset_id) == ("demo-fork.zip", "upload", 0)
        assert (service.state_manager.mods_dir / "demo-fork.zip").read_bytes() == demo_zip()
        assert service.state_manager.get_cached_metadata("demo", "1.0.0") is not None

    def test_a_running_server_needs_a_restart(self, service: ModService) -> None:
        service.set_server_running(True)

        result = service.install_archive(received(service, "d.zip", demo_zip()), source="upload")

        assert result.pending_restart is True
        assert service.restart_state.pending_restart is True

    @pytest.mark.parametrize(
        ("data", "message"),
        [
            (b"not a zip", "not a zip archive"),
            (mod_zip(None, extra={"readme.txt": b"x"}), "no usable modinfo.json"),
            (mod_zip({"modid": "demo", "name": "Demo"}), "no usable modinfo.json"),
            (mod_zip({"name": "Demo", "version": "1"}), "no usable modinfo.json"),
        ],
    )
    def test_refuses_an_unusable_file(self, service: ModService, data: bytes, message: str) -> None:
        with pytest.raises(ModFileInvalidError, match=message):
            service.install_archive(received(service, "d.zip", data), source="upload")
        assert service.state_manager.list_mods() == []
        assert not service.state_manager.mods_dir.exists() or not any(
            service.state_manager.mods_dir.iterdir()
        )

    def test_an_installed_mod_is_refused_with_its_source(self, service: ModService) -> None:
        installed(service, "demo", "1.0.0", "demo_1.0.0.zip")

        with pytest.raises(ModAlreadyInstalledError) as raised:
            service.install_archive(received(service, "x.zip", demo_zip("Demo")), source="upload")

        assert (raised.value.slug, raised.value.current_version) == ("demo", "1.0.0")
        assert raised.value.source == "moddb"

    def test_replace_swaps_the_file_and_keeps_the_enabled_state(self, service: ModService) -> None:
        old = installed(service, "demo", "1.0.0", "demo_1.0.0.zip", enabled=False)
        path = received(service, "demo-fork.zip", demo_zip(version="1.0.1-fork"))

        result = service.install_archive(path, source="upload", replace=True)

        assert (result.replaced, result.previous_version) == (True, "1.0.0")
        assert result.filename == "demo-fork.zip.disabled"
        assert not old.exists()
        state = service.state_manager.get_mod_by_slug("demo")
        assert state is not None
        assert (state.version, state.enabled, state.source, state.asset_id) == (
            "1.0.1-fork",
            False,
            "upload",
            0,
        )
        assert sorted(p.name for p in service.state_manager.mods_dir.iterdir()) == [
            "demo-fork.zip.disabled"
        ]

    def test_a_failed_replace_restores_the_original(
        self, service: ModService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        old = installed(service, "demo", "1.0.0", "demo_1.0.0.zip")
        path = received(service, "demo-fork.zip", demo_zip(version="2.0.0"))
        real_save = service.state_manager.save
        calls = {"n": 0}

        def failing_save() -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("disk full")
            real_save()

        monkeypatch.setattr(service.state_manager, "save", failing_save)

        with pytest.raises(ModVersionChangeFailedError):
            service.install_archive(path, source="upload", replace=True)

        assert old.read_bytes() == demo_zip("demo", "1.0.0")
        state = service.state_manager.get_mod_by_slug("demo")
        assert state is not None
        assert (state.filename, state.version, state.source) == ("demo_1.0.0.zip", "1.0.0", "moddb")
        assert not (service.state_manager.mods_dir / "demo-fork.zip").exists()

    def test_a_replace_with_the_file_gone_is_refused(self, service: ModService) -> None:
        installed(service, "demo", "1.0.0", "demo_1.0.0.zip").unlink()

        with pytest.raises(ModFileMissingError):
            service.install_archive(
                received(service, "d.zip", demo_zip()), source="upload", replace=True
            )

    @pytest.mark.asyncio
    async def test_a_busy_mod_is_refused(
        self, service: ModService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An upload of a mod whose version change is running is refused, not queued."""
        started, release = asyncio.Event(), asyncio.Event()

        async def held_lookup(slug: str) -> None:
            started.set()
            await release.wait()

        monkeypatch.setattr(service.api_client, "get_mod", held_lookup)
        installed(service, "demo", "1.0.0", "demo_1.0.0.zip")
        change = asyncio.create_task(service.change_version("demo", "1.1.0"))
        await started.wait()

        with pytest.raises(ModOperationInProgressError):
            service.install_archive(
                received(service, "d.zip", demo_zip()), source="upload", replace=True
            )
        release.set()
        with pytest.raises(ApiModNotFoundError):
            await change
        state = service.state_manager.get_mod_by_slug("demo")
        assert state is not None
        assert state.version == "1.0.0"

    def test_a_name_taken_by_another_mod_is_refused(self, service: ModService) -> None:
        installed(service, "other", "1.0.0", "demo.zip")

        with pytest.raises(ModFileConflictError):
            service.install_archive(received(service, "demo.zip", demo_zip()), source="upload")
        state = service.state_manager.get_mod_by_slug("other")
        assert state is not None


@pytest.fixture
def update_service(tmp_path: Path, service: ModService) -> ModUpdateService:
    return ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=service,
        game_version_provider=lambda: "1.22.7",
    )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        api_key_admin=TEST_ADMIN_KEY, api_key_monitor=TEST_MONITOR_KEY, data_dir=tmp_path
    )


@pytest.fixture
def client(
    settings: Settings, service: ModService, update_service: ModUpdateService
) -> Generator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mod_service] = lambda: service
    app.dependency_overrides[get_mod_update_service] = lambda: update_service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def leftovers(service: ModService) -> list[str]:
    root = service.cache_dir / "incoming"
    return [str(p.relative_to(root)) for p in root.rglob("*")] if root.exists() else []


class TestUploadRoute:
    def test_installs_the_body_and_lists_the_mod_as_uploaded(
        self, client: TestClient, service: ModService
    ) -> None:
        response = client.post(
            UPLOAD_URL,
            params={"filename": "demo-fork.zip"},
            content=demo_zip(),
            headers={**ADMIN, "Content-Type": "application/zip"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "data": {
                "slug": "demo",
                "version": "1.0.0",
                "filename": "demo-fork.zip",
                "compatibility": "not_verified",
                "pending_restart": False,
                "source": "upload",
                "replaced": False,
                "previous_version": None,
            },
        }
        listed = client.get("/api/v1alpha1/mods", headers=ADMIN).json()["data"]["mods"]
        assert [(m["slug"], m["source"]) for m in listed] == [("demo", "upload")]
        assert leftovers(service) == []

    def test_a_monitor_key_is_refused(self, client: TestClient, service: ModService) -> None:
        response = client.post(
            UPLOAD_URL, params={"filename": "d.zip"}, content=demo_zip(), headers=MONITOR
        )

        assert response.status_code == 403
        assert service.state_manager.list_mods() == []

    def test_a_declared_length_over_the_limit_is_refused_before_reading(
        self, client: TestClient, service: ModService, settings: Settings
    ) -> None:
        settings.mod_upload_max_mb = 1
        response = client.post(
            UPLOAD_URL,
            params={"filename": "d.zip"},
            content=b"x" * (1024 * 1024 + 1),
            headers=ADMIN,
        )

        assert response.status_code == 413
        assert response.json()["detail"]["code"] == ErrorCode.MOD_FILE_TOO_LARGE
        assert leftovers(service) == []

    def test_a_streamed_body_over_the_limit_is_refused(
        self, client: TestClient, service: ModService, settings: Settings
    ) -> None:
        settings.mod_upload_max_mb = 1

        def body() -> Iterator[bytes]:
            for _ in range(3):
                yield b"x" * (512 * 1024)

        response = client.post(
            UPLOAD_URL, params={"filename": "d.zip"}, content=body(), headers=ADMIN
        )

        assert response.status_code == 413
        assert leftovers(service) == []
        assert service.state_manager.list_mods() == []

    @pytest.mark.parametrize(
        ("filename", "data"),
        [("../d.zip", demo_zip()), ("d.rar", demo_zip()), ("d.zip", b"not a zip")],
    )
    def test_an_unusable_name_or_file_is_422(
        self, client: TestClient, service: ModService, filename: str, data: bytes
    ) -> None:
        response = client.post(
            UPLOAD_URL, params={"filename": filename}, content=data, headers=ADMIN
        )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == ErrorCode.MOD_FILE_INVALID
        assert leftovers(service) == []

    def test_an_installed_mod_is_409_with_its_version_and_source(
        self, client: TestClient, service: ModService
    ) -> None:
        installed(service, "demo", "1.0.0", "demo_1.0.0.zip")

        response = client.post(
            UPLOAD_URL, params={"filename": "d.zip"}, content=demo_zip(), headers=ADMIN
        )

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.MOD_ALREADY_INSTALLED
        assert (detail["slug"], detail["installed_version"], detail["source"]) == (
            "demo",
            "1.0.0",
            "moddb",
        )

    def test_replace_swaps_and_forgets_the_update_record(
        self, client: TestClient, service: ModService, update_service: ModUpdateService
    ) -> None:
        installed(service, "demo", "1.0.0", "demo_1.0.0.zip")
        update_service.store.set(
            "demo", StoredModRecord(found=True, checked_at=datetime(2026, 1, 1, tzinfo=UTC))
        )
        update_service.store.save()

        response = client.post(
            UPLOAD_URL,
            params={"filename": "demo-fork.zip", "replace": "true"},
            content=demo_zip(version="1.0.1"),
            headers=ADMIN,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert (data["replaced"], data["previous_version"], data["version"]) == (
            True,
            "1.0.0",
            "1.0.1",
        )
        assert update_service.store.get("demo") is None
        assert ModUpdateStore(service.state_manager.state_dir).get("demo") is None
