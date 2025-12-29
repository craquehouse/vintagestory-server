"""Shared fixtures for server tests."""

import shutil
import tarfile
import tempfile
from collections.abc import AsyncGenerator, Generator
from io import BytesIO
from pathlib import Path

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.services.server import ServerService

# pyright: reportPrivateUsage=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnusedVariable=false
# pyright: reportMissingTypeArgument=false
# Note: Above suppressions are for pytest fixture injection patterns.

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
        api_key_admin="test-admin-key",
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
def installed_settings(temp_data_dir: Path) -> Settings:
    """Create test settings with installed server files."""
    server_dir = temp_data_dir / "server"
    server_dir.mkdir(parents=True, exist_ok=True)
    vsmanager_dir = temp_data_dir / "vsmanager"
    vsmanager_dir.mkdir(parents=True, exist_ok=True)
    serverdata_dir = temp_data_dir / "serverdata"
    serverdata_dir.mkdir(parents=True, exist_ok=True)

    # Create marker files
    (server_dir / "VintagestoryServer.dll").touch()
    (server_dir / "VintagestoryLib.dll").touch()
    (vsmanager_dir / "current_version").write_text("1.21.3")

    return Settings(
        data_dir=temp_data_dir,
        api_key_admin="test-admin-key",
    )


@pytest.fixture
async def installed_service(
    installed_settings: Settings,
) -> AsyncGenerator[ServerService, None]:
    """Create server service with installed server state."""
    service = ServerService(installed_settings)
    yield service
    await service.close()


def create_mock_tarball() -> tuple[bytes, str]:
    """Create a mock server tarball for testing.

    Returns:
        Tuple of (tarball_bytes, md5_hash)
    """
    import hashlib

    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        # Add mock server files
        for filename in ["VintagestoryServer.dll", "VintagestoryLib.dll"]:
            data = f"mock {filename} content".encode()
            info = tarfile.TarInfo(name=filename)
            info.size = len(data)
            tar.addfile(info, BytesIO(data))

    tarball_bytes = buffer.getvalue()
    md5_hash = hashlib.md5(tarball_bytes).hexdigest()
    return tarball_bytes, md5_hash
