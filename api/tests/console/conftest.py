"""Shared fixtures for console tests."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.services.server import ServerService, get_server_service
from vintagestory_api.services.ws_token_service import (
    WebSocketTokenService,
    get_ws_token_service,
    reset_ws_token_service,
)

# pyright: reportPrivateUsage=false
# Note: Tests need access to private members to verify internal state

# Test API keys - must match expected format
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create temp data directory with server files."""
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    serverdata_dir = tmp_path / "serverdata"
    serverdata_dir.mkdir()
    vsmanager_dir = tmp_path / "vsmanager"
    vsmanager_dir.mkdir()

    # Create required server files to mark as "installed"
    (server_dir / "VintagestoryServer.dll").touch()
    (server_dir / "VintagestoryLib.dll").touch()
    (vsmanager_dir / "current_version").write_text("1.21.3")

    return tmp_path


@pytest.fixture
def test_settings(temp_data_dir: Path) -> Settings:
    """Create test settings with known API keys."""
    return Settings(
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        data_dir=temp_data_dir,
        debug=True,
    )


@pytest.fixture
def test_service(test_settings: Settings) -> ServerService:
    """Create ServerService with test settings."""
    return ServerService(test_settings)


@pytest.fixture
def test_token_service() -> Generator[WebSocketTokenService, None, None]:
    """Create fresh WebSocketTokenService for each test."""
    reset_ws_token_service()
    service = get_ws_token_service()
    yield service
    reset_ws_token_service()


@pytest.fixture
def integration_app(
    test_settings: Settings, test_service: ServerService
) -> Generator[FastAPI, None, None]:
    """Create app with test settings for integration testing."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_server_service] = lambda: test_service

    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(integration_app: FastAPI) -> TestClient:
    """Create test client for integration tests."""
    return TestClient(integration_app)


@pytest.fixture
def ws_client(
    test_settings: Settings, test_service: ServerService, test_token_service: WebSocketTokenService
) -> Generator[TestClient, None, None]:
    """Create test client with overrides for WebSocket testing.

    Uses Starlette's synchronous TestClient which properly handles WebSockets.
    """
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_server_service] = lambda: test_service
    app.dependency_overrides[get_ws_token_service] = lambda: test_token_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Headers with admin API key."""
    return {"X-API-Key": TEST_ADMIN_KEY}


@pytest.fixture
def monitor_headers() -> dict[str, str]:
    """Headers with monitor API key (non-admin)."""
    return {"X-API-Key": TEST_MONITOR_KEY}
