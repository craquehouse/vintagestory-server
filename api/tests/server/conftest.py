"""Shared fixtures for server tests."""

import shutil
import tarfile
import tempfile
from collections.abc import AsyncGenerator, Generator
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.routers.server import get_server_service
from vintagestory_api.services.server import ServerService

# pyright: reportPrivateUsage=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

# Test API keys
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"

# Mock VintageStory API response
MOCK_STABLE_API_RESPONSE = {
    "1.21.6": {
        "linuxserver": {
            "filename": "vs_server_linux-x64_1.21.6.tar.gz",
            "filesize": "40.2 MB",
            "md5": "abc123def456",
            "urls": {
                "cdn": "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz",
                "local": "https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz",
            },
            "latest": True,
        },
        "windowsserver": {},
    },
    "1.21.5": {
        "linuxserver": {
            "filename": "vs_server_linux-x64_1.21.5.tar.gz",
            "filesize": "40.1 MB",
            "md5": "xyz789abc",
            "urls": {
                "cdn": "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.5.tar.gz",
                "local": "https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_1.21.5.tar.gz",
            },
            "latest": False,
        },
    },
}

MOCK_UNSTABLE_API_RESPONSE = {
    "1.22.0-pre.1": {
        "linuxserver": {
            "filename": "vs_server_linux-x64_1.22.0-pre.1.tar.gz",
            "filesize": "41.0 MB",
            "md5": "pre123hash",
            "urls": {
                "cdn": "https://cdn.vintagestory.at/gamefiles/unstable/vs_server_linux-x64_1.22.0-pre.1.tar.gz",
                "local": "https://vintagestory.at/api/gamefiles/unstable/vs_server_linux-x64_1.22.0-pre.1.tar.gz",
            },
            "latest": True,
        },
    },
}


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary data directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_settings(temp_data_dir: Path) -> Settings:
    """Create test settings with temporary data directory."""
    return Settings(
        data_dir=temp_data_dir,
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
    )


@pytest.fixture
async def server_service(
    test_settings: Settings,
) -> AsyncGenerator[ServerService, None]:
    """Create a server service for testing."""
    service = ServerService(test_settings)
    yield service
    await service.close()


@pytest.fixture
def installed_server(temp_data_dir: Path) -> Path:
    """Create a mock installed server directory."""
    server_dir = temp_data_dir / "server"
    server_dir.mkdir(parents=True)

    # Create required server files
    (server_dir / "VintagestoryServer.dll").touch()
    (server_dir / "VintagestoryLib.dll").touch()

    # Create version tracking
    vsmanager_dir = temp_data_dir / "vsmanager"
    vsmanager_dir.mkdir(parents=True)
    (vsmanager_dir / "current_version").write_text("1.21.6")

    return temp_data_dir


@pytest.fixture
def installed_settings(installed_server: Path) -> Settings:
    """Create test settings with an installed server."""
    return Settings(
        data_dir=installed_server,
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
    )


@pytest.fixture
async def installed_service(
    installed_settings: Settings,
) -> AsyncGenerator[ServerService, None]:
    """Create a server service with installed server."""
    service = ServerService(installed_settings)
    yield service
    await service.close()


@pytest.fixture
def mock_subprocess() -> Generator[AsyncMock, None, None]:
    """Create a mock subprocess for lifecycle tests."""
    mock_process = AsyncMock()
    mock_process.returncode = None
    mock_process.pid = 12345
    mock_process.stdout = AsyncMock()
    mock_process.stderr = AsyncMock()
    mock_process.stdout.readline = AsyncMock(return_value=b"")
    mock_process.stderr.readline = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.send_signal = Mock()
    mock_process.terminate = Mock()
    mock_process.kill = Mock()
    mock_process.stdin = AsyncMock()
    mock_process.stdin.write = Mock()
    mock_process.stdin.drain = AsyncMock()
    yield mock_process


@pytest.fixture
def integration_app(
    test_settings: Settings, server_service: ServerService
) -> Generator[FastAPI, None, None]:
    """Create app with test settings for integration testing."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_server_service] = lambda: server_service

    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(integration_app: FastAPI) -> TestClient:
    """Create test client for integration tests."""
    return TestClient(integration_app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Headers with admin API key."""
    return {"X-API-Key": TEST_ADMIN_KEY}


@pytest.fixture
def monitor_headers() -> dict[str, str]:
    """Headers with monitor API key."""
    return {"X-API-Key": TEST_MONITOR_KEY}


def create_mock_tarball(files: dict[str, bytes] | None = None) -> bytes:
    """Create a mock tarball with optional files.

    Args:
        files: Dict mapping filename to content. If None, creates default server files.

    Returns:
        bytes: The tarball content.
    """
    if files is None:
        files = {
            "VintagestoryServer.dll": b"mock dll content",
            "VintagestoryLib.dll": b"mock lib content",
            "Mods/": b"",  # Directory
        }

    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in files.items():
            if name.endswith("/"):
                # Directory
                info = tarfile.TarInfo(name=name)
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            else:
                # File
                info = tarfile.TarInfo(name=name)
                info.size = len(content)
                tar.addfile(info, BytesIO(content))

    return buffer.getvalue()
