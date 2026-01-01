"""Integration tests for config router endpoints.

Story 6.2: Game Settings API
Story 6.3: API Settings Service
Story 6.5: Raw Config Viewer

Tests the config router endpoints for:

Game Settings (6.2):
- GET /config/game - Read settings with metadata
- POST /config/game/settings/{key} - Update settings
- RBAC: Monitor can read, only Admin can write

API Settings (6.3):
- GET /config/api - Read API settings (Admin only)
- POST /config/api/settings/{key} - Update API settings (Admin only)
- RBAC: Only Admin can access API settings

Config Files (6.5):
- GET /config/files - List JSON config files (read-only)
- GET /config/files/{filename} - Read raw config file content (read-only)
- RBAC: Both Admin and Monitor can access (read-only)
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import ServerState
from vintagestory_api.routers.config import (
    get_api_settings_service,
    get_config_files_service,
    get_game_config_service,
    get_pending_restart_state,
)
from vintagestory_api.services.api_settings import ApiSettingsService
from vintagestory_api.services.config_files import ConfigFilesService
from vintagestory_api.services.game_config import GameConfigService
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.server import ServerService, get_server_service

# Test API keys
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    """Create Settings with temporary data directory and test API keys."""
    settings = Settings(
        data_dir=tmp_path,
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        debug=True,
    )
    return settings


@pytest.fixture
def sample_config() -> dict[str, object]:
    """Sample serverconfig.json content for testing."""
    return {
        "ServerName": "Test Server",
        "ServerDescription": "A test server",
        "WelcomeMessage": "Welcome!",
        "Port": 42420,
        "Ip": "",
        "MaxClients": 16,
        "MaxChunkRadius": 12,
        "Password": "",
        "AllowPvP": True,
        "AllowFireSpread": True,
        "AllowFallingBlocks": True,
        "EntitySpawning": True,
        "PassTimeWhenEmpty": False,
        "Upnp": False,
        "AdvertiseServer": True,
    }


@pytest.fixture
def config_file(temp_settings: Settings, sample_config: dict[str, object]) -> Path:
    """Create a sample serverconfig.json file."""
    config_path = temp_settings.serverdata_dir / "serverconfig.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(sample_config, indent=2))
    return config_path


@pytest.fixture
def mock_server_service(temp_settings: Settings) -> MagicMock:
    """Create a mock ServerService."""
    service = MagicMock(spec=ServerService)
    service.settings = temp_settings
    mock_status = MagicMock()
    mock_status.state = ServerState.RUNNING
    service.get_server_status.return_value = mock_status
    service.send_command = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_pending_restart() -> PendingRestartState:
    """Create a real PendingRestartState instance."""
    return PendingRestartState()


@pytest.fixture
def integration_app(
    temp_settings: Settings,
    config_file: Path,
    mock_server_service: MagicMock,
    mock_pending_restart: PendingRestartState,
) -> Generator[FastAPI, None, None]:
    """Create app with overridden dependencies for integration testing."""

    def get_test_settings() -> Settings:
        return temp_settings

    def get_test_server_service() -> MagicMock:
        return mock_server_service

    def get_test_pending_restart() -> PendingRestartState:
        return mock_pending_restart

    def get_test_game_config_service() -> GameConfigService:
        return GameConfigService(
            settings=temp_settings,
            server_service=mock_server_service,
            pending_restart_state=mock_pending_restart,
        )

    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[get_server_service] = get_test_server_service
    app.dependency_overrides[get_pending_restart_state] = get_test_pending_restart
    app.dependency_overrides[get_game_config_service] = get_test_game_config_service

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
def client(integration_app: FastAPI) -> TestClient:
    """Create test client for integration tests."""
    return TestClient(integration_app)


# ==============================================================================
# GET /config/game endpoint tests (AC: 1)
# ==============================================================================


class TestGetGameSettings:
    """Tests for GET /config/game endpoint - AC 1."""

    def test_get_game_settings_returns_all_settings(
        self, client: TestClient
    ) -> None:
        """AC 1: GET returns all settings with metadata."""
        response = client.get(
            "/api/v1alpha1/config/game",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "settings" in data["data"]
        assert len(data["data"]["settings"]) > 0

    def test_get_game_settings_includes_source_file(
        self, client: TestClient
    ) -> None:
        """AC 1: Response includes source_file metadata."""
        response = client.get(
            "/api/v1alpha1/config/game",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert data["data"]["source_file"] == "serverconfig.json"

    def test_get_game_settings_includes_last_modified(
        self, client: TestClient
    ) -> None:
        """AC 1: Response includes last_modified timestamp."""
        response = client.get(
            "/api/v1alpha1/config/game",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "last_modified" in data["data"]

    def test_get_game_settings_setting_has_metadata(
        self, client: TestClient
    ) -> None:
        """AC 1: Each setting includes key, value, type, live_update, env_managed."""
        response = client.get(
            "/api/v1alpha1/config/game",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        setting = data["data"]["settings"][0]
        assert "key" in setting
        assert "value" in setting
        assert "type" in setting
        assert "live_update" in setting
        assert "env_managed" in setting

    def test_get_game_settings_monitor_can_access(
        self, client: TestClient
    ) -> None:
        """AC 1: Monitor role can access GET endpoint (read-only)."""
        response = client.get(
            "/api/v1alpha1/config/game",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200

    def test_get_game_settings_unauthenticated_blocked(
        self, client: TestClient
    ) -> None:
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1alpha1/config/game")

        assert response.status_code == 401


class TestGetGameSettingsConfigNotFound:
    """Tests for GET /config/game when config file doesn't exist."""

    @pytest.fixture
    def app_without_config(
        self, temp_settings: Settings, mock_server_service: MagicMock
    ) -> Generator[FastAPI, None, None]:
        """Create app without config file."""

        def get_test_settings() -> Settings:
            return temp_settings

        def get_test_server_service() -> MagicMock:
            return mock_server_service

        def get_test_game_config_service() -> GameConfigService:
            return GameConfigService(
                settings=temp_settings,
                server_service=mock_server_service,
            )

        app.dependency_overrides[get_settings] = get_test_settings
        app.dependency_overrides[get_server_service] = get_test_server_service
        app.dependency_overrides[get_game_config_service] = get_test_game_config_service

        yield app

        app.dependency_overrides.clear()

    def test_get_game_settings_returns_404_when_config_missing(
        self, app_without_config: FastAPI, temp_settings: Settings
    ) -> None:
        """GET returns 404 when serverconfig.json doesn't exist."""
        client = TestClient(app_without_config)

        response = client.get(
            "/api/v1alpha1/config/game",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.CONFIG_NOT_FOUND


# ==============================================================================
# POST /config/game/settings/{key} endpoint tests (AC: 2, 3, 4, 5)
# ==============================================================================


class TestUpdateGameSettingLiveUpdate:
    """Tests for POST /config/game/settings/{key} with live update - AC 2."""

    def test_update_setting_live_success(
        self, client: TestClient, mock_server_service: MagicMock
    ) -> None:
        """AC 2: Update setting via console command when server running."""
        response = client.post(
            "/api/v1alpha1/config/game/settings/ServerName",
            json={"value": "New Name"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["key"] == "ServerName"
        assert data["data"]["value"] == "New Name"
        assert data["data"]["method"] == "console_command"
        assert data["data"]["pending_restart"] is False

    def test_update_setting_calls_send_command(
        self, client: TestClient, mock_server_service: MagicMock
    ) -> None:
        """AC 2: Update executes /serverconfig console command."""
        client.post(
            "/api/v1alpha1/config/game/settings/ServerName",
            json={"value": "Console Test"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        mock_server_service.send_command.assert_called_once()
        call_args = mock_server_service.send_command.call_args[0][0]
        assert '/serverconfig name "Console Test"' == call_args


class TestUpdateGameSettingFileUpdate:
    """Tests for POST /config/game/settings/{key} with file update - AC 3."""

    def test_update_port_uses_file_update(
        self, client: TestClient, mock_server_service: MagicMock
    ) -> None:
        """AC 3: Port update uses file update and sets pending_restart."""
        response = client.post(
            "/api/v1alpha1/config/game/settings/Port",
            json={"value": 42421},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["method"] == "file_update"
        assert data["data"]["pending_restart"] is True
        mock_server_service.send_command.assert_not_called()


class TestUpdateGameSettingEnvManaged:
    """Tests for POST /config/game/settings/{key} with env-managed settings - AC 4."""

    def test_update_env_managed_setting_blocked(
        self,
        temp_settings: Settings,
        config_file: Path,
        mock_server_service: MagicMock,
    ) -> None:
        """AC 4: Update blocked for env-managed setting with proper error."""
        with patch.dict(os.environ, {"VS_CFG_MAX_CLIENTS": "32"}):

            def get_test_settings() -> Settings:
                return temp_settings

            def get_test_server_service() -> MagicMock:
                return mock_server_service

            def get_test_game_config_service() -> GameConfigService:
                return GameConfigService(
                    settings=temp_settings,
                    server_service=mock_server_service,
                    block_env_managed_settings=True,
                )

            app.dependency_overrides[get_settings] = get_test_settings
            app.dependency_overrides[get_server_service] = get_test_server_service
            app.dependency_overrides[get_game_config_service] = (
                get_test_game_config_service
            )

            try:
                client = TestClient(app)
                response = client.post(
                    "/api/v1alpha1/config/game/settings/MaxClients",
                    json={"value": 64},
                    headers={"X-API-Key": TEST_ADMIN_KEY},
                )

                assert response.status_code == 400
                error = response.json()["detail"]
                assert error["code"] == ErrorCode.SETTING_ENV_MANAGED
                assert "MaxClients" in error["message"]
                assert "VS_CFG_MAX_CLIENTS" in error["message"]
            finally:
                app.dependency_overrides.clear()


class TestUpdateGameSettingErrors:
    """Tests for POST /config/game/settings/{key} error handling."""

    def test_update_unknown_setting_returns_400(
        self, client: TestClient
    ) -> None:
        """Unknown setting key returns 400 with SETTING_UNKNOWN error."""
        response = client.post(
            "/api/v1alpha1/config/game/settings/UnknownSetting",
            json={"value": "test"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.SETTING_UNKNOWN

    def test_update_console_command_fails(
        self, client: TestClient, mock_server_service: MagicMock
    ) -> None:
        """Console command failure returns 500 with SETTING_UPDATE_FAILED."""
        mock_server_service.send_command.return_value = False

        response = client.post(
            "/api/v1alpha1/config/game/settings/ServerName",
            json={"value": "Fail Test"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 500
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.SETTING_UPDATE_FAILED


# ==============================================================================
# RBAC tests (AC: 5)
# ==============================================================================


class TestUpdateGameSettingRBAC:
    """Tests for POST endpoint RBAC - AC 5."""

    def test_admin_can_update_setting(
        self, client: TestClient
    ) -> None:
        """Admin role can update settings."""
        response = client.post(
            "/api/v1alpha1/config/game/settings/ServerName",
            json={"value": "Admin Updated"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200

    def test_monitor_blocked_from_update(
        self, client: TestClient
    ) -> None:
        """AC 5: Monitor role is blocked from POST with 403 Forbidden."""
        response = client.post(
            "/api/v1alpha1/config/game/settings/ServerName",
            json={"value": "Monitor Attempt"},
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.FORBIDDEN

    def test_unauthenticated_blocked_from_update(
        self, client: TestClient
    ) -> None:
        """Unauthenticated request returns 401."""
        response = client.post(
            "/api/v1alpha1/config/game/settings/ServerName",
            json={"value": "No Auth"},
        )

        assert response.status_code == 401


# ==============================================================================
# API Response format tests
# ==============================================================================


class TestGameSettingsResponseFormat:
    """Tests for game settings API response envelope format."""

    def test_get_response_uses_standard_envelope(
        self, client: TestClient
    ) -> None:
        """GET response uses standard API envelope."""
        response = client.get(
            "/api/v1alpha1/config/game",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"

    def test_post_response_uses_standard_envelope(
        self, client: TestClient
    ) -> None:
        """POST response uses standard API envelope."""
        response = client.post(
            "/api/v1alpha1/config/game/settings/ServerName",
            json={"value": "Envelope Test"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"

    def test_error_response_uses_detail_structure(
        self, client: TestClient
    ) -> None:
        """Error response uses FastAPI detail structure."""
        response = client.post(
            "/api/v1alpha1/config/game/settings/Unknown",
            json={"value": "test"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "detail" in data
        assert "code" in data["detail"]
        assert "message" in data["detail"]


# ==============================================================================
# API Settings Endpoint Tests (Story 6.3)
# ==============================================================================


@pytest.fixture
def api_settings_app(
    temp_settings: Settings,
    mock_server_service: MagicMock,
) -> Generator[FastAPI, None, None]:
    """Create app with overridden dependencies for API settings testing."""

    def get_test_settings() -> Settings:
        return temp_settings

    def get_test_server_service() -> MagicMock:
        return mock_server_service

    def get_test_api_settings_service() -> ApiSettingsService:
        return ApiSettingsService(settings=temp_settings)

    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[get_server_service] = get_test_server_service
    app.dependency_overrides[get_api_settings_service] = get_test_api_settings_service

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
def api_settings_client(api_settings_app: FastAPI) -> TestClient:
    """Create test client for API settings tests."""
    return TestClient(api_settings_app)


class TestGetApiSettings:
    """Tests for GET /config/api endpoint - Story 6.3 AC 1."""

    def test_get_api_settings_returns_all_settings(
        self, api_settings_client: TestClient
    ) -> None:
        """AC 1: GET returns all API settings."""
        response = api_settings_client.get(
            "/api/v1alpha1/config/api",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "settings" in data["data"]

        settings = data["data"]["settings"]
        assert "auto_start_server" in settings
        assert "block_env_managed_settings" in settings
        assert "mod_list_refresh_interval" in settings
        assert "server_versions_refresh_interval" in settings

    def test_get_api_settings_returns_defaults(
        self, api_settings_client: TestClient
    ) -> None:
        """AC 1: When no file exists, returns default values."""
        response = api_settings_client.get(
            "/api/v1alpha1/config/api",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        settings = response.json()["data"]["settings"]
        assert settings["auto_start_server"] is False
        assert settings["block_env_managed_settings"] is True
        assert settings["mod_list_refresh_interval"] == 3600
        assert settings["server_versions_refresh_interval"] == 86400


class TestGetApiSettingsRBAC:
    """Tests for GET /config/api RBAC - Story 6.3 AC 4."""

    def test_admin_can_access_api_settings(
        self, api_settings_client: TestClient
    ) -> None:
        """Admin role can access GET /config/api."""
        response = api_settings_client.get(
            "/api/v1alpha1/config/api",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200

    def test_monitor_blocked_from_api_settings(
        self, api_settings_client: TestClient
    ) -> None:
        """AC 4: Monitor role is blocked from GET /config/api with 403."""
        response = api_settings_client.get(
            "/api/v1alpha1/config/api",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.FORBIDDEN

    def test_unauthenticated_blocked_from_api_settings(
        self, api_settings_client: TestClient
    ) -> None:
        """Unauthenticated request returns 401."""
        response = api_settings_client.get("/api/v1alpha1/config/api")

        assert response.status_code == 401


class TestUpdateApiSetting:
    """Tests for POST /config/api/settings/{key} - Story 6.3 AC 2."""

    def test_update_api_setting_success(
        self, api_settings_client: TestClient
    ) -> None:
        """AC 2: POST updates setting and confirms update."""
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/auto_start_server",
            json={"value": True},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["key"] == "auto_start_server"
        assert data["data"]["value"] is True

    def test_update_api_setting_persists(
        self, api_settings_client: TestClient
    ) -> None:
        """AC 2: Update is persisted to api-settings.json."""
        # Update setting
        api_settings_client.post(
            "/api/v1alpha1/config/api/settings/mod_list_refresh_interval",
            json={"value": 1800},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Verify persisted via GET
        response = api_settings_client.get(
            "/api/v1alpha1/config/api",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        settings = response.json()["data"]["settings"]
        assert settings["mod_list_refresh_interval"] == 1800


class TestUpdateApiSettingErrors:
    """Tests for POST /config/api/settings/{key} error handling."""

    def test_unknown_setting_returns_400(
        self, api_settings_client: TestClient
    ) -> None:
        """Unknown setting returns 400 with API_SETTING_UNKNOWN."""
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/unknown_setting",
            json={"value": "test"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.API_SETTING_UNKNOWN
        assert "unknown_setting" in error["message"]

    def test_invalid_value_returns_400(
        self, api_settings_client: TestClient
    ) -> None:
        """Invalid value returns 400 with API_SETTING_INVALID."""
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/mod_list_refresh_interval",
            json={"value": -100},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.API_SETTING_INVALID


class TestUpdateApiSettingRBAC:
    """Tests for POST /config/api/settings/{key} RBAC - Story 6.3 AC 4."""

    def test_admin_can_update_api_setting(
        self, api_settings_client: TestClient
    ) -> None:
        """Admin role can update API settings."""
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/auto_start_server",
            json={"value": True},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200

    def test_monitor_blocked_from_update_api_setting(
        self, api_settings_client: TestClient
    ) -> None:
        """AC 4: Monitor role is blocked from POST with 403."""
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/auto_start_server",
            json={"value": True},
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.FORBIDDEN

    def test_unauthenticated_blocked_from_update_api_setting(
        self, api_settings_client: TestClient
    ) -> None:
        """Unauthenticated request returns 401."""
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/auto_start_server",
            json={"value": True},
        )

        assert response.status_code == 401


class TestApiSettingsResponseFormat:
    """Tests for API response format - Story 6.3."""

    def test_get_response_uses_standard_envelope(
        self, api_settings_client: TestClient
    ) -> None:
        """GET response uses standard API envelope."""
        response = api_settings_client.get(
            "/api/v1alpha1/config/api",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"

    def test_post_response_uses_standard_envelope(
        self, api_settings_client: TestClient
    ) -> None:
        """POST response uses standard API envelope."""
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/auto_start_server",
            json={"value": True},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"

    def test_error_response_uses_detail_structure(
        self, api_settings_client: TestClient
    ) -> None:
        """Error response uses FastAPI detail structure."""
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/unknown",
            json={"value": "test"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "detail" in data
        assert "code" in data["detail"]
        assert "message" in data["detail"]


# ==============================================================================
# Config Files Endpoint Tests (Story 6.5)
# ==============================================================================


@pytest.fixture
def config_files_app(
    temp_settings: Settings,
    config_file: Path,
    mock_server_service: MagicMock,
) -> Generator[FastAPI, None, None]:
    """Create app with overridden dependencies for config files testing."""

    def get_test_settings() -> Settings:
        return temp_settings

    def get_test_server_service() -> MagicMock:
        return mock_server_service

    def get_test_config_files_service() -> ConfigFilesService:
        return ConfigFilesService(settings=temp_settings)

    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[get_server_service] = get_test_server_service
    app.dependency_overrides[get_config_files_service] = get_test_config_files_service

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
def config_files_client(config_files_app: FastAPI) -> TestClient:
    """Create test client for config files tests."""
    return TestClient(config_files_app)


class TestListConfigFiles:
    """Tests for GET /config/files endpoint - Story 6.5 AC 1."""

    def test_list_config_files_returns_json_files(
        self, config_files_client: TestClient
    ) -> None:
        """AC 1: GET returns list of JSON config files."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "files" in data["data"]
        assert "serverconfig.json" in data["data"]["files"]

    def test_list_config_files_empty_when_no_files(
        self, temp_settings: Settings, mock_server_service: MagicMock
    ) -> None:
        """AC 1: GET returns empty list when no JSON files exist."""
        # Create empty serverdata dir (no config files)
        temp_settings.serverdata_dir.mkdir(parents=True, exist_ok=True)

        def get_test_settings() -> Settings:
            return temp_settings

        def get_test_server_service() -> MagicMock:
            return mock_server_service

        def get_test_config_files_service() -> ConfigFilesService:
            return ConfigFilesService(settings=temp_settings)

        app.dependency_overrides[get_settings] = get_test_settings
        app.dependency_overrides[get_server_service] = get_test_server_service
        app.dependency_overrides[get_config_files_service] = get_test_config_files_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/config/files",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["files"] == []
        finally:
            app.dependency_overrides.clear()

    def test_list_config_files_monitor_can_access(
        self, config_files_client: TestClient
    ) -> None:
        """AC 1: Monitor role can access GET endpoint (read-only)."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200

    def test_list_config_files_unauthenticated_blocked(
        self, config_files_client: TestClient
    ) -> None:
        """Unauthenticated request returns 401."""
        response = config_files_client.get("/api/v1alpha1/config/files")

        assert response.status_code == 401


class TestReadConfigFile:
    """Tests for GET /config/files/{filename} endpoint - Story 6.5 AC 2."""

    def test_read_config_file_returns_content(
        self, config_files_client: TestClient, sample_config: dict[str, object]
    ) -> None:
        """AC 2: GET returns filename and raw JSON content."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files/serverconfig.json",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["filename"] == "serverconfig.json"
        assert data["data"]["content"]["ServerName"] == sample_config["ServerName"]

    def test_read_config_file_not_found(
        self, config_files_client: TestClient
    ) -> None:
        """AC 2: Returns 404 for non-existent file."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files/nonexistent.json",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.CONFIG_FILE_NOT_FOUND

    def test_read_config_file_monitor_can_access(
        self, config_files_client: TestClient
    ) -> None:
        """Monitor role can read config files."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files/serverconfig.json",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200

    def test_read_config_file_unauthenticated_blocked(
        self, config_files_client: TestClient
    ) -> None:
        """Unauthenticated request returns 401."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files/serverconfig.json"
        )

        assert response.status_code == 401


class TestConfigFilePathTraversal:
    """Tests for path traversal prevention - Story 6.5 AC 3.

    Note: FastAPI/Starlette normalizes URL paths at the HTTP level, so
    simple `../` sequences in URL paths are resolved BEFORE reaching
    the handler. For example, `/config/files/../secrets.json` becomes
    `/config/secrets.json` at the routing level.

    Our service-level path validation (using _safe_path) provides
    defense-in-depth for any traversal attempts that bypass HTTP normalization.

    The tests here verify:
    1. HTTP-level normalization happens (tests return 404, not the file)
    2. Service-level validation works (tested in test_config_files.py)
    3. Absolute paths are blocked (double slash creates absolute path)
    """

    def test_path_traversal_simple_parent_normalized_by_http(
        self, config_files_client: TestClient
    ) -> None:
        """AC 3: ../secrets.json is normalized by HTTP layer.

        FastAPI/Starlette normalizes URL paths, so ../secrets.json becomes
        secrets.json. The normalized path may match a different route entirely,
        resulting in a 404 from routing. This is defense-in-depth.
        """
        response = config_files_client.get(
            "/api/v1alpha1/config/files/../secrets.json",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # HTTP normalization prevents the request from reaching our handler
        # with the malicious path - any non-200 response is acceptable
        assert response.status_code in (400, 404)

    def test_path_traversal_nested_normalized_by_http(
        self, config_files_client: TestClient
    ) -> None:
        """AC 3: subdir/../../secrets.json normalized by HTTP layer."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files/subdir/../../secrets.json",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # HTTP normalization prevents the request from reaching our handler
        # with the malicious path - any non-200 response is acceptable
        assert response.status_code in (400, 404)

    def test_path_traversal_absolute_path(
        self, config_files_client: TestClient
    ) -> None:
        """AC 3: Rejects absolute paths like /etc/passwd with 400 error.

        Double slash in URL creates an absolute path that bypasses
        HTTP normalization and reaches our service-level validation.
        """
        response = config_files_client.get(
            "/api/v1alpha1/config/files//etc/passwd",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.CONFIG_PATH_INVALID

    def test_path_traversal_multiple_levels_normalized_by_http(
        self, config_files_client: TestClient
    ) -> None:
        """AC 3: foo/../../../etc/passwd normalized by HTTP layer."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files/foo/../../../etc/passwd",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # HTTP normalization prevents the request from reaching our handler
        # with the malicious path - any non-200 response is acceptable
        assert response.status_code in (400, 404)


class TestConfigFilesResponseFormat:
    """Tests for config files API response format - Story 6.5."""

    def test_list_response_uses_standard_envelope(
        self, config_files_client: TestClient
    ) -> None:
        """GET /config/files response uses standard API envelope."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"

    def test_read_response_uses_standard_envelope(
        self, config_files_client: TestClient
    ) -> None:
        """GET /config/files/{filename} response uses standard API envelope."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files/serverconfig.json",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"
        assert "filename" in data["data"]
        assert "content" in data["data"]

    def test_error_response_uses_detail_structure(
        self, config_files_client: TestClient
    ) -> None:
        """Error response uses FastAPI detail structure."""
        # Use absolute path (double slash) to trigger path traversal error
        response = config_files_client.get(
            "/api/v1alpha1/config/files//etc/passwd",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "detail" in data
        assert "code" in data["detail"]
        assert "message" in data["detail"]
