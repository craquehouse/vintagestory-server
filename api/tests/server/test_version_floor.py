"""Tests for the minimum supported VintageStory version (1.22, the first on .NET 10)."""

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import respx
from conftest import TEST_ADMIN_KEY
from fastapi.testclient import TestClient
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.services.server import (
    VS_STABLE_API,
    ServerService,
    get_server_service,
)


def linux_server_entry(version: str, *, latest: bool = False) -> dict[str, Any]:
    filename = f"vs_server_linux-x64_{version}.tar.gz"
    return {
        "linuxserver": {
            "filename": filename,
            "filesize": "40.2 MB",
            "md5": "abc123",
            "urls": {"cdn": f"https://cdn.example/{filename}", "local": "https://local.example"},
            "latest": latest,
        }
    }


def mark_installed(settings: Settings, version: str) -> None:
    settings.server_dir.mkdir(parents=True, exist_ok=True)
    settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
    (settings.server_dir / "VintagestoryServer.dll").touch()
    (settings.server_dir / "VintagestoryLib.dll").touch()
    (settings.vsmanager_dir / "current_version").write_text(version)


@pytest.fixture
def settings(temp_data_dir: Path) -> Settings:
    return Settings(
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor="test-monitor-key",
        data_dir=temp_data_dir,
    )


@pytest.fixture
def client(settings: Settings) -> Generator[TestClient, None, None]:
    service = ServerService(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_server_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class TestIsVersionSupported:
    @pytest.mark.parametrize(
        ("version", "expected"),
        [
            ("1.22.0", True),
            ("1.22.0-pre.1", True),
            ("1.22.7", True),
            ("1.23.0", True),
            ("2.0.0", True),
            ("1.21.99", False),
            ("1.21.6-rc.1", False),
            ("1.9.3", False),
            ("0.99.0", False),
            ("not-a-version", False),
        ],
    )
    def test_compares_major_and_minor(
        self, server_service: ServerService, version: str, expected: bool
    ) -> None:
        assert server_service.is_version_supported(version) is expected


class TestVersionListing:
    @respx.mock
    @pytest.mark.asyncio
    async def test_unsupported_versions_are_not_listed(
        self, server_service: ServerService
    ) -> None:
        respx.get(VS_STABLE_API).mock(
            return_value=Response(
                200,
                json={
                    "1.22.7": linux_server_entry("1.22.7", latest=True),
                    "1.21.6": linux_server_entry("1.21.6"),
                },
            )
        )

        versions = await server_service.get_available_versions("stable")

        assert list(versions) == ["1.22.7"]


class TestInstallRejectsUnsupportedVersions:
    def test_endpoint_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.21.6"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 422
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.VERSION_NOT_SUPPORTED
        assert "1.22 or newer" in error["message"]

    @pytest.mark.asyncio
    async def test_service_reports_error(self, server_service: ServerService) -> None:
        progress = await server_service.install_server("1.21.6")

        assert progress.state.value == "error"
        assert progress.error_code == ErrorCode.VERSION_NOT_SUPPORTED


class TestStartRejectsUnsupportedInstall:
    def test_endpoint_returns_400(self, client: TestClient, settings: Settings) -> None:
        mark_installed(settings, "1.21.6")

        response = client.post(
            "/api/v1alpha1/server/start",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.VERSION_NOT_SUPPORTED
        assert "1.22 or newer" in error["message"]

    @pytest.mark.asyncio
    async def test_service_does_not_spawn_process(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mark_installed(settings, "1.21.6")
        service = ServerService(settings)

        async def fail_if_spawned(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("server process should not be started")

        monkeypatch.setattr("asyncio.create_subprocess_exec", fail_if_spawned)

        with pytest.raises(RuntimeError, match=ErrorCode.VERSION_NOT_SUPPORTED):
            await service.start_server()
