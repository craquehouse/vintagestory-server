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

Story 17.6: a saved interval setting reschedules its job through the real
dependency chain (`TestIntervalSettingsReschedule`).
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Generator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY  # type: ignore[import-not-found]
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.jobs import INTERVAL_JOBS
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
from vintagestory_api.routers.config import router as config_router
from vintagestory_api.routers.jobs import get_scheduler
from vintagestory_api.services.api_settings import ApiSettingsService
from vintagestory_api.services.config_files import (
    CONFIG_FILE_MAX_BYTES,
    CONFIG_FILE_MAX_DEPTH,
    ConfigFilesService,
)
from vintagestory_api.services.game_config import GameConfigService
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.scheduler import SchedulerService
from vintagestory_api.services.server import ServerService, get_server_service


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
) -> Generator[FastAPI]:
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


# ==============================================================================
# Story 17.5 (FR186): Monitor keys cannot read the server password
# ==============================================================================

# A made-up password for the redaction tests; never a real value.
SECRET = "pw-Zq9-monitor-must-not-see"
GAME_URL = "/api/v1alpha1/config/game"


def _write_config(config_file: Path, config: dict[str, object]) -> None:
    config_file.write_text(json.dumps(config, indent=2))


def _settings_by_key(response_json: dict[str, Any]) -> dict[str, dict[str, Any]]:
    settings: list[dict[str, Any]] = response_json["data"]["settings"]
    return {setting["key"]: setting for setting in settings}


class TestGetGameSettingsSecrets:
    """Story 17.5: GET /config/game withholds the password from a Monitor key."""

    def test_monitor_gets_no_password(
        self, client: TestClient, config_file: Path, sample_config: dict[str, object]
    ) -> None:
        """AC 1: value null, secret and configured true, the password nowhere in the body."""
        _write_config(config_file, {**sample_config, "Password": SECRET})

        response = client.get(GAME_URL, headers={"X-API-Key": TEST_MONITOR_KEY})

        assert response.status_code == 200
        assert SECRET not in response.text
        password = _settings_by_key(response.json())["Password"]
        assert password["value"] is None
        assert password["secret"] is True
        assert password["configured"] is True

    def test_admin_gets_the_password(
        self, client: TestClient, config_file: Path, sample_config: dict[str, object]
    ) -> None:
        """AC 5: Admin gets the value and secret: true, no configured."""
        _write_config(config_file, {**sample_config, "Password": SECRET})

        response = client.get(GAME_URL, headers={"X-API-Key": TEST_ADMIN_KEY})

        password = _settings_by_key(response.json())["Password"]
        assert password["value"] == SECRET
        assert password["secret"] is True
        assert "configured" not in password

    @pytest.mark.parametrize("stored", [None, "", "missing"])
    def test_no_password(
        self,
        client: TestClient,
        config_file: Path,
        sample_config: dict[str, object],
        stored: str | None,
    ) -> None:
        """AC 2, 5: not configured for Monitor; Admin reads the value as today."""
        config = dict(sample_config)
        if stored == "missing":
            del config["Password"]
        else:
            config["Password"] = stored
        _write_config(config_file, config)

        monitor = client.get(GAME_URL, headers={"X-API-Key": TEST_MONITOR_KEY})
        admin = client.get(GAME_URL, headers={"X-API-Key": TEST_ADMIN_KEY})

        monitor_password = _settings_by_key(monitor.json())["Password"]
        assert monitor_password["value"] is None
        assert monitor_password["secret"] is True
        assert monitor_password["configured"] is False
        admin_password = _settings_by_key(admin.json())["Password"]
        assert admin_password["value"] == (None if stored == "missing" else stored)
        assert "configured" not in admin_password

    def test_lower_case_key(
        self, client: TestClient, config_file: Path, sample_config: dict[str, object]
    ) -> None:
        """A "password" key in another letter case counts as configured and never leaks."""
        config = {k: v for k, v in sample_config.items() if k != "Password"}
        config["password"] = SECRET
        _write_config(config_file, config)

        monitor = client.get(GAME_URL, headers={"X-API-Key": TEST_MONITOR_KEY})
        admin = client.get(GAME_URL, headers={"X-API-Key": TEST_ADMIN_KEY})

        assert SECRET not in monitor.text
        assert _settings_by_key(monitor.json())["Password"]["configured"] is True
        assert _settings_by_key(admin.json())["Password"]["value"] is None

    def test_other_settings_equal_for_both_roles(
        self, client: TestClient, config_file: Path, sample_config: dict[str, object]
    ) -> None:
        """Only Password carries secret (and, for Monitor, configured)."""
        _write_config(config_file, {**sample_config, "Password": SECRET})

        monitor = _settings_by_key(
            client.get(GAME_URL, headers={"X-API-Key": TEST_MONITOR_KEY}).json()
        )
        admin = _settings_by_key(
            client.get(GAME_URL, headers={"X-API-Key": TEST_ADMIN_KEY}).json()
        )

        assert monitor.keys() == admin.keys()
        for key, setting in admin.items():
            assert "configured" not in setting
            if key == "Password":
                continue
            assert "secret" not in setting
            assert "configured" not in monitor[key]
            assert monitor[key] == setting

    @pytest.mark.parametrize("key", [TEST_ADMIN_KEY, TEST_MONITOR_KEY])
    def test_no_store(self, client: TestClient, key: str) -> None:
        """AC 7: the response is never cached, for either role."""
        response = client.get(GAME_URL, headers={"X-API-Key": key})

        assert response.headers["Cache-Control"] == "no-store"


class TestGetGameSettingsConfigNotFound:
    """Tests for GET /config/game when config file doesn't exist."""

    @pytest.fixture
    def app_without_config(
        self, temp_settings: Settings, mock_server_service: MagicMock
    ) -> Generator[FastAPI]:
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

    @pytest.mark.parametrize("key", [TEST_ADMIN_KEY, TEST_MONITOR_KEY])
    def test_404_is_not_cached(self, app_without_config: FastAPI, key: str) -> None:
        """Story 17.5 (AC 7, review L1): the error response is not cached either."""
        client = TestClient(app_without_config)

        response = client.get("/api/v1alpha1/config/game", headers={"X-API-Key": key})

        assert response.status_code == 404
        assert response.headers["Cache-Control"] == "no-store"


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
        assert "/serverconfig name Console Test" == call_args


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

    def test_update_invalid_value_returns_400(
        self, client: TestClient
    ) -> None:
        """Invalid value returns 400 with SETTING_VALUE_INVALID error."""
        response = client.post(
            "/api/v1alpha1/config/game/settings/Port",
            json={"value": "not_a_number"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.SETTING_VALUE_INVALID

    def test_update_null_for_required_setting_returns_400(
        self, client: TestClient, config_file: Path
    ) -> None:
        """Story 16.8: null for a setting that cannot be empty is rejected, not saved as "None"."""
        before = config_file.read_text()

        response = client.post(
            "/api/v1alpha1/config/game/settings/ServerName",
            json={"value": None},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == ErrorCode.SETTING_VALUE_INVALID
        assert config_file.read_text() == before

    def test_update_cleared_description_reads_back_as_null(
        self, client: TestClient, config_file: Path, mock_server_service: MagicMock
    ) -> None:
        """Story 16.8: a cleared Description is stored and read back as null."""
        mock_server_service.get_server_status.return_value.state = ServerState.INSTALLED

        response = client.post(
            "/api/v1alpha1/config/game/settings/ServerDescription",
            json={"value": ""},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        assert response.json()["data"]["value"] is None
        assert json.loads(config_file.read_text())["ServerDescription"] is None
        settings = client.get(
            "/api/v1alpha1/config/game", headers={"X-API-Key": TEST_ADMIN_KEY}
        ).json()["data"]["settings"]
        description = next(s for s in settings if s["key"] == "ServerDescription")
        assert description["value"] is None

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
) -> Generator[FastAPI]:
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
        assert settings["mod_list_refresh_interval"] == 14400
        assert settings["server_versions_refresh_interval"] == 86400


class TestModUpdateWebhookRedaction:
    """Story 14.6 (FR149): reads and updates never return the webhook URL."""

    URL = "https://discord.com/api/webhooks/1/redaction-token"

    def test_update_and_read_report_only_configured(
        self, api_settings_client: TestClient
    ) -> None:
        headers = {"X-API-Key": TEST_ADMIN_KEY}

        update = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/mod_update_webhook_url",
            json={"value": self.URL},
            headers=headers,
        )
        read = api_settings_client.get("/api/v1alpha1/config/api", headers=headers)

        assert update.status_code == 200
        assert update.json()["data"] == {"key": "mod_update_webhook_url", "configured": True}
        assert read.status_code == 200
        settings = read.json()["data"]["settings"]
        assert settings["mod_update_webhook_configured"] is True
        assert "mod_update_webhook_url" not in settings
        assert "redaction-token" not in update.text + read.text

    def test_monitor_cannot_set_the_webhook(self, api_settings_client: TestClient) -> None:
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/mod_update_webhook_url",
            json={"value": self.URL},
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403

    def test_invalid_url_is_rejected_without_echo(self, api_settings_client: TestClient) -> None:
        response = api_settings_client.post(
            "/api/v1alpha1/config/api/settings/mod_update_webhook_url",
            json={"value": "ftp://example.com/redaction-token"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        assert "redaction-token" not in response.text


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
) -> Generator[FastAPI]:
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


class TestListConfigDirectories:
    """Tests for GET /config/directories endpoint - Story 9.7."""

    def test_list_directories_returns_subdirectories(
        self, temp_settings: Settings, mock_server_service: MagicMock
    ) -> None:
        """Returns list of subdirectory names in serverdata."""
        # Create directories
        serverdata = temp_settings.serverdata_dir
        serverdata.mkdir(parents=True, exist_ok=True)
        (serverdata / "ModConfigs").mkdir()
        (serverdata / "Playerdata").mkdir()
        (serverdata / "serverconfig.json").write_text("{}")

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
                "/api/v1alpha1/config/directories",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "directories" in data["data"]
            assert "ModConfigs" in data["data"]["directories"]
            assert "Playerdata" in data["data"]["directories"]
        finally:
            app.dependency_overrides.clear()

    def test_list_directories_empty_when_no_subdirs(
        self, config_files_client: TestClient
    ) -> None:
        """Returns empty list when no subdirectories exist."""
        response = config_files_client.get(
            "/api/v1alpha1/config/directories",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["directories"] == []

    def test_list_directories_monitor_can_access(
        self, config_files_client: TestClient
    ) -> None:
        """Monitor role can access GET endpoint (read-only)."""
        response = config_files_client.get(
            "/api/v1alpha1/config/directories",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200

    def test_list_directories_unauthenticated_blocked(
        self, config_files_client: TestClient
    ) -> None:
        """Unauthenticated request returns 401."""
        response = config_files_client.get("/api/v1alpha1/config/directories")

        assert response.status_code == 401

    def test_list_directories_with_directory_param(
        self, temp_settings: Settings, mock_server_service: MagicMock
    ) -> None:
        """Story 9.7: Returns subdirectories within a specified directory."""
        # Create nested directories
        serverdata = temp_settings.serverdata_dir
        serverdata.mkdir(parents=True, exist_ok=True)
        cache_dir = serverdata / "Cache"
        cache_dir.mkdir()
        (cache_dir / "unpack").mkdir()
        (cache_dir / "downloads").mkdir()

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
                "/api/v1alpha1/config/directories?directory=Cache",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "unpack" in data["data"]["directories"]
            assert "downloads" in data["data"]["directories"]
        finally:
            app.dependency_overrides.clear()

    def test_list_directories_path_traversal_blocked(
        self, config_files_client: TestClient
    ) -> None:
        """Story 9.7: Rejects path traversal in directory param with 400."""
        response = config_files_client.get(
            "/api/v1alpha1/config/directories?directory=../secret",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.CONFIG_PATH_INVALID


class TestListConfigFiles:
    """Tests for GET /config/files endpoint - Story 6.5 AC 1, Story 9.7."""

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

    def test_list_config_files_with_directory_param(
        self, temp_settings: Settings, mock_server_service: MagicMock
    ) -> None:
        """Story 9.7: Returns files from specified subdirectory."""
        # Create subdirectory with files
        serverdata = temp_settings.serverdata_dir
        serverdata.mkdir(parents=True, exist_ok=True)
        subdir = serverdata / "ModConfigs"
        subdir.mkdir()
        (subdir / "mod1.json").write_text('{"enabled": true}')
        (subdir / "mod2.json").write_text('{"enabled": false}')

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
                "/api/v1alpha1/config/files?directory=ModConfigs",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "mod1.json" in data["data"]["files"]
            assert "mod2.json" in data["data"]["files"]
        finally:
            app.dependency_overrides.clear()

    def test_list_config_files_directory_path_traversal(
        self, config_files_client: TestClient
    ) -> None:
        """Story 9.7: Rejects path traversal in directory param with 400."""
        response = config_files_client.get(
            "/api/v1alpha1/config/files?directory=../secret",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == ErrorCode.CONFIG_PATH_INVALID

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


FILES_URL = "/api/v1alpha1/config/files"


class TestReadConfigFileSecrets:
    """Story 17.5: the config file viewer withholds secrets from a Monitor key."""

    def _get(self, client: TestClient, path: str, key: str):
        return client.get(f"{FILES_URL}/{path}", headers={"X-API-Key": key})

    def test_monitor_gets_serverconfig_redacted(
        self,
        config_files_client: TestClient,
        config_file: Path,
        sample_config: dict[str, object],
    ) -> None:
        """AC 3: Password is "[redacted]"; every other key is as for Admin."""
        _write_config(config_file, {**sample_config, "Password": SECRET})

        monitor = self._get(config_files_client, "serverconfig.json", TEST_MONITOR_KEY)
        admin = self._get(config_files_client, "serverconfig.json", TEST_ADMIN_KEY)

        assert monitor.status_code == 200
        assert SECRET not in monitor.text
        monitor_content = monitor.json()["data"]["content"]
        admin_content = admin.json()["data"]["content"]
        assert monitor_content["Password"] == "[redacted]"
        assert admin_content["Password"] == SECRET
        assert {k: v for k, v in monitor_content.items() if k != "Password"} == {
            k: v for k, v in admin_content.items() if k != "Password"
        }

    @pytest.mark.parametrize("value", [None, ""])
    def test_unset_password_unchanged(
        self,
        config_files_client: TestClient,
        config_file: Path,
        sample_config: dict[str, object],
        value: str | None,
    ) -> None:
        """AC 3: null and "" are returned as they are, to both roles."""
        _write_config(config_file, {**sample_config, "Password": value})

        for key in (TEST_MONITOR_KEY, TEST_ADMIN_KEY):
            response = self._get(config_files_client, "serverconfig.json", key)
            assert response.json()["data"]["content"]["Password"] == value

    @pytest.mark.parametrize(
        "path",
        ["ModConfig/copy.json", "serverconfig.backup.json"],
    )
    def test_copies_are_redacted(
        self,
        config_files_client: TestClient,
        config_file: Path,
        sample_config: dict[str, object],
        path: str,
    ) -> None:
        """AC 4: a copy under another name or directory is redacted too."""
        copy = config_file.parent / path
        copy.parent.mkdir(parents=True, exist_ok=True)
        _write_config(copy, {**sample_config, "Password": SECRET})

        monitor = self._get(config_files_client, path, TEST_MONITOR_KEY)
        admin = self._get(config_files_client, path, TEST_ADMIN_KEY)

        assert SECRET not in monitor.text
        assert monitor.json()["data"]["content"]["Password"] == "[redacted]"
        assert admin.json()["data"]["content"] == {**sample_config, "Password": SECRET}

    def test_every_letter_case_is_redacted(
        self, config_files_client: TestClient, config_file: Path
    ) -> None:
        """AC 4: Password, password and PASSWORD are all redacted."""
        path = config_file.parent / "cases.json"
        _write_config(path, {"Password": "a1-x", "password": "b2-y", "PASSWORD": "c3-z"})

        monitor = self._get(config_files_client, "cases.json", TEST_MONITOR_KEY)
        admin = self._get(config_files_client, "cases.json", TEST_ADMIN_KEY)

        assert monitor.json()["data"]["content"] == {
            "Password": "[redacted]",
            "password": "[redacted]",
            "PASSWORD": "[redacted]",
        }
        assert admin.json()["data"]["content"] == {
            "Password": "a1-x",
            "password": "b2-y",
            "PASSWORD": "c3-z",
        }

    def test_secrets_are_redacted_at_every_depth(
        self, config_files_client: TestClient, config_file: Path
    ) -> None:
        """Story 19.1 AC 6, 7, 8: secret keys and secret URLs, at any depth, for Monitor only."""
        mod: dict[str, object] = {
            "Other": {"Password": SECRET + "-nested"},
            "Accounts": [{"Token": SECRET + "-token"}, {"ApiKey": SECRET + "-apikey"}],
            "bot_token": SECRET + "-bot",
            "WebhookUrl": SECRET + "-webhook",
            "Endpoint": f"https://user:{SECRET}@host/",
            "Notify": {"Url": f"https://discord.com/api/webhooks/1/{SECRET}-discord"},
            "Seed": "12345",
            "Unset": {"Password": None},
            "Empty": {"Password": ""},
        }
        path = config_file.parent / "ModConfig" / "mod.json"
        path.parent.mkdir()
        _write_config(path, mod)

        monitor = self._get(config_files_client, "ModConfig/mod.json", TEST_MONITOR_KEY)
        admin = self._get(config_files_client, "ModConfig/mod.json", TEST_ADMIN_KEY)

        assert monitor.status_code == 200
        assert SECRET not in monitor.text
        assert monitor.json()["data"]["content"] == {
            "Other": {"Password": "[redacted]"},
            "Accounts": [{"Token": "[redacted]"}, {"ApiKey": "[redacted]"}],
            "bot_token": "[redacted]",
            "WebhookUrl": "[redacted]",
            "Endpoint": "[redacted]",
            "Notify": {"Url": "[redacted]"},
            "Seed": "12345",
            "Unset": {"Password": None},
            "Empty": {"Password": ""},
        }
        assert admin.json()["data"]["content"] == mod

    def test_startup_commands_are_redacted(
        self,
        config_files_client: TestClient,
        config_file: Path,
        sample_config: dict[str, object],
    ) -> None:
        """Story 19.1 AC 7, 8: serverconfig.json StartupCommands is for Admin only."""
        config = {**sample_config, "StartupCommands": f"/op {SECRET}"}
        _write_config(config_file, config)

        monitor = self._get(config_files_client, "serverconfig.json", TEST_MONITOR_KEY)
        admin = self._get(config_files_client, "serverconfig.json", TEST_ADMIN_KEY)

        assert SECRET not in monitor.text
        assert monitor.json()["data"]["content"]["StartupCommands"] == "[redacted]"
        assert admin.json()["data"]["content"] == config

    def test_broken_serverconfig(
        self, config_files_client: TestClient, config_file: Path
    ) -> None:
        """AC 4, 5: a file that does not parse returns its text to Admin only."""
        config_file.write_text('{"Password": "' + SECRET + '", }')

        monitor = self._get(config_files_client, "serverconfig.json", TEST_MONITOR_KEY)
        admin = self._get(config_files_client, "serverconfig.json", TEST_ADMIN_KEY)

        assert SECRET not in monitor.text
        monitor_content = monitor.json()["data"]["content"]
        assert monitor_content["_raw"] == "[redacted]"
        assert monitor_content["_parse_error"]
        admin_content = admin.json()["data"]["content"]
        assert SECRET in admin_content["_raw"]
        assert admin_content["_parse_error"]

    def test_game_log_is_refused(
        self, config_files_client: TestClient, config_file: Path
    ) -> None:
        """Story 19.1 AC 2: a game log is not served to either key; its text is in neither body."""
        log = config_file.parent / "Logs" / "server-main.log"
        log.parent.mkdir()
        log.write_text(f"12:00:00 [Event] Handling /serverconfig password {SECRET}\n")

        monitor = self._get(config_files_client, "Logs/server-main.log", TEST_MONITOR_KEY)
        admin = self._get(config_files_client, "Logs/server-main.log", TEST_ADMIN_KEY)

        assert SECRET not in monitor.text
        assert SECRET not in admin.text
        assert monitor.status_code == 400
        assert monitor.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_NOT_SUPPORTED
        assert admin.status_code == 400
        assert admin.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_NOT_SUPPORTED

    @pytest.mark.parametrize("content", [[1, 2], "text"])
    def test_arrays_and_strings_unchanged(
        self, config_files_client: TestClient, config_file: Path, content: object
    ) -> None:
        """A JSON array or string file is returned as it is to both roles."""
        (config_file.parent / "other.json").write_text(json.dumps(content))

        for key in (TEST_MONITOR_KEY, TEST_ADMIN_KEY):
            response = self._get(config_files_client, "other.json", key)
            assert response.json()["data"]["content"] == content

    @pytest.mark.parametrize("key", [TEST_ADMIN_KEY, TEST_MONITOR_KEY])
    def test_no_store(self, config_files_client: TestClient, key: str) -> None:
        """AC 7: the response is never cached, for either role."""
        response = self._get(config_files_client, "serverconfig.json", key)

        assert response.headers["Cache-Control"] == "no-store"

    @pytest.mark.parametrize("key", [TEST_ADMIN_KEY, TEST_MONITOR_KEY])
    @pytest.mark.parametrize(
        ("path", "status"),
        [("nonexistent.json", 404), ("/etc/passwd", 400)],
    )
    def test_errors_are_not_cached(
        self, config_files_client: TestClient, key: str, path: str, status: int
    ) -> None:
        """AC 7 (review L1): a 404 and a 400 are not cached either, for either role."""
        response = self._get(config_files_client, path, key)

        assert response.status_code == status
        assert response.headers["Cache-Control"] == "no-store"


BOTH_KEYS = [TEST_ADMIN_KEY, TEST_MONITOR_KEY]


class TestConfigFileTypes:
    """Story 19.1 (FR205, FR206): what the viewer refuses, and how, for both keys."""

    def _get(self, client: TestClient, path: str, key: str):
        return client.get(f"{FILES_URL}/{path}", headers={"X-API-Key": key})

    @pytest.mark.parametrize("key", BOTH_KEYS)
    def test_unsupported_files_are_400(
        self, config_files_client: TestClient, config_file: Path, key: str
    ) -> None:
        """AC 2, 3: other names (existing or not), a directory, a binary file: 400, no-store."""
        root = config_file.parent
        (root / "notes.txt").write_text('{"a": 1}')
        (root / "dir.json").mkdir()
        (root / "bin.json").write_bytes(bytes(range(256)))

        for path in ("notes.txt", "missing.log", "dir.json", "bin.json"):
            response = self._get(config_files_client, path, key)
            assert response.status_code == 400, path
            assert response.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_NOT_SUPPORTED, path
            assert response.headers["Cache-Control"] == "no-store", path

    @pytest.mark.parametrize("key", BOTH_KEYS)
    def test_too_large_is_413(
        self, config_files_client: TestClient, config_file: Path, key: str
    ) -> None:
        """AC 4: a file larger than 2 MiB is 413, no-store."""
        (config_file.parent / "big.json").write_bytes(b" " * (CONFIG_FILE_MAX_BYTES + 1))

        response = self._get(config_files_client, "big.json", key)

        assert response.status_code == 413
        assert response.json()["detail"]["code"] == ErrorCode.CONFIG_FILE_TOO_LARGE
        assert response.headers["Cache-Control"] == "no-store"

    @pytest.mark.parametrize("opening", ["[", '{"a":'])
    @pytest.mark.parametrize("key", BOTH_KEYS)
    def test_deep_nesting_is_raw_not_500(
        self, config_files_client: TestClient, config_file: Path, key: str, opening: str
    ) -> None:
        """AC 5: 300 levels used to be a plain 500; it is the _raw form now."""
        closing = "]" if opening == "[" else "}"
        text = opening * 300 + "1" + closing * 300
        (config_file.parent / "deep.json").write_text(text)

        response = self._get(config_files_client, "deep.json", key)

        assert response.status_code == 200
        content = response.json()["data"]["content"]
        assert content["_raw"] == (text if key == TEST_ADMIN_KEY else "[redacted]")
        assert content["_parse_error"]

    @pytest.mark.parametrize("opening", ["[", '{"a":'])
    @pytest.mark.parametrize("key", BOTH_KEYS)
    def test_nesting_at_the_limit_is_served(
        self, config_files_client: TestClient, config_file: Path, key: str, opening: str
    ) -> None:
        """AC 5: content nested CONFIG_FILE_MAX_DEPTH levels still serializes."""
        closing = "]" if opening == "[" else "}"
        text = opening * CONFIG_FILE_MAX_DEPTH + "1" + closing * CONFIG_FILE_MAX_DEPTH
        (config_file.parent / "deep.json").write_text(text)

        response = self._get(config_files_client, "deep.json", key)

        assert response.status_code == 200
        assert response.json()["data"]["content"] == json.loads(text)

    @pytest.mark.parametrize("key", BOTH_KEYS)
    def test_read_error_is_500_with_envelope(
        self,
        config_files_client: TestClient,
        config_file: Path,
        monkeypatch: pytest.MonkeyPatch,
        key: str,
    ) -> None:
        """ADR-1 decision 8: an OSError while reading is 500 INTERNAL_ERROR, no-store."""

        def denied(self: Path) -> bytes:
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(Path, "read_bytes", denied)

        response = self._get(config_files_client, "serverconfig.json", key)

        assert response.status_code == 500
        assert response.json() == {
            "detail": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "Config file could not be read: serverconfig.json",
            }
        }
        assert response.headers["Cache-Control"] == "no-store"


class TestOtherConfigPathsWithAPassword:
    """Story 17.5 (AC 7): no other config path gives a Monitor key the password."""

    @pytest.fixture
    def password_set(
        self, config_file: Path, sample_config: dict[str, object]
    ) -> dict[str, object]:
        config = {**sample_config, "Password": SECRET}
        _write_config(config_file, config)
        (config_file.parent / "ModConfig").mkdir()
        _write_config(config_file.parent / "ModConfig" / "copy.json", config)
        return config

    def test_monitor_update_is_refused_without_echo(
        self, client: TestClient, config_file: Path, password_set: dict[str, object]
    ) -> None:
        """POST /game/settings/Password: 403, the body does not echo it, the file is unchanged."""
        before = config_file.read_text()

        response = client.post(
            f"{GAME_URL}/settings/Password",
            json={"value": SECRET + "-new"},
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == ErrorCode.FORBIDDEN
        assert SECRET not in response.text
        assert config_file.read_text() == before

    def test_admin_update_echoes_the_value(
        self, client: TestClient, password_set: dict[str, object]
    ) -> None:
        """AC 5: the Admin update response is unchanged and carries the new value."""
        new_value = SECRET + "-new"

        response = client.post(
            f"{GAME_URL}/settings/Password",
            json={"value": new_value},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        assert response.json()["data"]["value"] == new_value

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1alpha1/config/files",
            "/api/v1alpha1/config/files?directory=ModConfig",
            "/api/v1alpha1/config/directories",
            "/api/v1alpha1/config/directories?directory=ModConfig",
        ],
    )
    def test_listings_carry_names_only(
        self, client: TestClient, password_set: dict[str, object], path: str
    ) -> None:
        """GET /config/files and /config/directories list names, never content."""
        response = client.get(path, headers={"X-API-Key": TEST_MONITOR_KEY})

        assert response.status_code == 200
        assert SECRET not in response.text

    def test_every_config_route_a_monitor_may_read(
        self, client: TestClient, password_set: dict[str, object]
    ) -> None:
        """Sweep: every GET route under /config that Monitor may call.

        The list is written out by hand: a new route has to be added here.
        """
        monitor_routes = [
            "/api/v1alpha1/config/game",
            "/api/v1alpha1/config/files",
            "/api/v1alpha1/config/directories",
            "/api/v1alpha1/config/files/serverconfig.json",
            "/api/v1alpha1/config/files/ModConfig/copy.json",
        ]
        admin_only_routes = ["/api/v1alpha1/config/api"]

        for path in monitor_routes:
            response = client.get(path, headers={"X-API-Key": TEST_MONITOR_KEY})
            assert response.status_code == 200, path
            assert SECRET not in response.text, path
        for path in admin_only_routes:
            response = client.get(path, headers={"X-API-Key": TEST_MONITOR_KEY})
            assert response.status_code == 403, path
            assert SECRET not in response.text, path

        paths: dict[str, dict[str, object]] = app.openapi()["paths"]
        config_get_routes = {
            path
            for path, operations in paths.items()
            if path.startswith("/api/v1alpha1/config") and "get" in operations
        }
        assert config_get_routes == {
            "/api/v1alpha1/config/game",
            "/api/v1alpha1/config/api",
            "/api/v1alpha1/config/directories",
            "/api/v1alpha1/config/files",
            "/api/v1alpha1/config/files/{filename}",
        }

        # Review L2: the OpenAPI paths leave out routes with include_in_schema=False, so
        # also read the config router's own routes, which include hidden ones. (FastAPI
        # 0.162 keeps included routers as private wrappers, so the app's route list
        # cannot be walked through a public API.)
        router_get_routes = {
            route.path
            for route in config_router.routes
            if isinstance(route, APIRoute) and "GET" in (route.methods or set[str]())
        }
        assert router_get_routes == {
            "/config/game",
            "/config/api",
            "/config/directories",
            "/config/files",
            "/config/files/{filename:path}",
        }
        assert all(
            route.include_in_schema
            for route in config_router.routes
            if isinstance(route, APIRoute)
        )


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


# ==============================================================================
# Dependency Injection Tests (for coverage of factory functions)
# ==============================================================================


class TestDependencyInjection:
    """Tests for dependency injection functions to achieve 100% coverage."""

    def test_get_pending_restart_state_singleton_initialization(self) -> None:
        """Test that get_pending_restart_state creates singleton on first call.

        This covers lines 74-76 where the singleton is initialized.
        """
        # Import the module to reset the global state
        from vintagestory_api.routers import config as config_module

        # Clear any existing singleton to test initialization path
        config_module._pending_restart_state = None

        # First call should initialize the singleton
        state1 = config_module.get_pending_restart_state()
        assert state1 is not None
        assert isinstance(state1, PendingRestartState)

        # Second call should return the same instance
        state2 = config_module.get_pending_restart_state()
        assert state2 is state1

    def test_get_game_config_service_factory(
        self, temp_settings: Settings, mock_server_service: MagicMock
    ) -> None:
        """Test that get_game_config_service creates service correctly.

        This covers line 92 where GameConfigService is instantiated.
        """
        from vintagestory_api.routers.config import get_game_config_service

        pending_state = PendingRestartState()
        service = get_game_config_service(
            server_service=mock_server_service,
            pending_restart_state=pending_state,
        )

        assert isinstance(service, GameConfigService)
        # Verify the service was created with the correct settings
        assert service._settings == temp_settings

    def test_get_api_settings_service_factory(
        self, temp_settings: Settings, mock_server_service: MagicMock
    ) -> None:
        """Test that get_api_settings_service creates service correctly.

        Story 17.6: the scheduler is passed too, so a saved interval reschedules its job.
        """
        from vintagestory_api.routers.config import get_api_settings_service

        service = get_api_settings_service(
            server_service=mock_server_service, scheduler=SchedulerService()
        )

        assert isinstance(service, ApiSettingsService)
        # Verify the service was created with the correct settings
        assert service._settings == temp_settings

    def test_get_config_files_service_factory(
        self, temp_settings: Settings, mock_server_service: MagicMock
    ) -> None:
        """Test that get_config_files_service creates service correctly.

        This covers line 360 where ConfigFilesService is instantiated.
        """
        from vintagestory_api.routers.config import get_config_files_service

        service = get_config_files_service(server_service=mock_server_service)

        assert isinstance(service, ConfigFilesService)
        # Verify the service was created with the correct settings
        assert service.settings == temp_settings


# ==============================================================================
# Story 17.6: a setting with no value carries the game's default (AC 9)
# ==============================================================================


class TestGameSettingsDefault:
    """GET /config/game: EntitySpawning carries `default: true`; no other setting does."""

    @pytest.mark.parametrize("api_key", [TEST_ADMIN_KEY, TEST_MONITOR_KEY])
    def test_entity_spawning_missing_from_the_file(
        self,
        client: TestClient,
        config_file: Path,
        sample_config: dict[str, object],
        api_key: str,
    ) -> None:
        config = {k: v for k, v in sample_config.items() if k != "EntitySpawning"}
        _write_config(config_file, config)

        response = client.get(GAME_URL, headers={"X-API-Key": api_key})

        assert response.status_code == 200
        settings = _settings_by_key(response.json())
        assert settings["EntitySpawning"]["value"] is None
        assert settings["EntitySpawning"]["default"] is True
        assert [key for key, s in settings.items() if "default" in s] == ["EntitySpawning"]
        assert settings["AllowPvP"]["value"] is True
        assert "default" not in settings["AllowPvP"]


# ==============================================================================
# Story 17.6: a saved interval setting reschedules its job (AC 1, 2, 3, 6, 7)
# ==============================================================================

INTERVAL_SETTING_JOBS = list(INTERVAL_JOBS.items())


async def _no_op_job() -> None:
    """Stands in for a real job so no test reaches the network or the game server."""


@pytest.fixture
async def reschedule_scheduler(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[SchedulerService]:
    """A real started scheduler whose interval jobs are no-ops."""
    monkeypatch.setattr(
        "vintagestory_api.jobs.mod_cache_refresh.refresh_mod_cache", _no_op_job
    )
    monkeypatch.setattr(
        "vintagestory_api.jobs.server_versions.check_server_versions", _no_op_job
    )
    monkeypatch.setattr(
        "vintagestory_api.jobs.metrics_collection.collect_metrics", _no_op_job
    )
    svc = SchedulerService()
    svc.start()
    yield svc
    svc.shutdown(wait=False)


@pytest.fixture
async def reschedule_client(
    temp_settings: Settings,
    mock_server_service: MagicMock,
    reschedule_scheduler: SchedulerService,
) -> AsyncIterator[httpx.AsyncClient]:
    """Client over the real get_api_settings_service; writes go to the temp dir.

    httpx over ASGITransport runs the app on the test's event loop, the loop the
    scheduler was started on.
    """
    app.dependency_overrides[get_settings] = lambda: temp_settings
    app.dependency_overrides[get_server_service] = lambda: mock_server_service
    app.dependency_overrides[get_scheduler] = lambda: reschedule_scheduler
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as async_client:
            yield async_client
    finally:
        app.dependency_overrides.clear()


ADMIN = {"X-API-Key": TEST_ADMIN_KEY}


async def _jobs(client: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    response = await client.get("/api/v1alpha1/jobs", headers=ADMIN)
    assert response.status_code == 200
    jobs: list[dict[str, Any]] = response.json()["data"]["jobs"]
    return {job["id"]: job for job in jobs}


async def _save(client: httpx.AsyncClient, key: str, value: int) -> httpx.Response:
    return await client.post(
        f"/api/v1alpha1/config/api/settings/{key}", json={"value": value}, headers=ADMIN
    )


class TestIntervalSettingsReschedule:
    """POST /config/api/settings/{interval} changes the scheduler without a restart."""

    @pytest.mark.parametrize(("key", "job_id"), INTERVAL_SETTING_JOBS)
    async def test_change_zero_and_back(
        self,
        reschedule_client: httpx.AsyncClient,
        temp_settings: Settings,
        key: str,
        job_id: str,
    ) -> None:
        response = await _save(reschedule_client, key, 600)
        assert response.status_code == 200
        assert response.json()["data"] == {"key": key, "value": 600}
        jobs = await _jobs(reschedule_client)
        assert jobs[job_id]["trigger_details"] == "every 600 seconds"

        response = await _save(reschedule_client, key, 0)
        assert response.status_code == 200
        assert job_id not in await _jobs(reschedule_client)

        response = await _save(reschedule_client, key, 3600)
        assert response.status_code == 200
        jobs = await _jobs(reschedule_client)
        assert jobs[job_id]["trigger_details"] == "every 3600 seconds"

        # The writes went to the temp state directory
        saved = json.loads(
            (temp_settings.state_dir / "api-settings.json").read_text()
        )
        assert saved[key] == 3600

    async def test_same_value_again_restarts_the_countdown(
        self, reschedule_client: httpx.AsyncClient
    ) -> None:
        """Saving N over N keeps the job and moves its next run forward (review L4)."""
        assert (await _save(reschedule_client, "mod_list_refresh_interval", 600)).status_code == 200
        first = (await _jobs(reschedule_client))["mod_cache_refresh"]
        await asyncio.sleep(0.05)

        assert (await _save(reschedule_client, "mod_list_refresh_interval", 600)).status_code == 200

        second = (await _jobs(reschedule_client))["mod_cache_refresh"]
        assert second["trigger_details"] == "every 600 seconds"
        assert datetime.fromisoformat(second["next_run_time"]) > datetime.fromisoformat(
            first["next_run_time"]
        )

    async def test_a_deleted_job_comes_back_on_the_next_save(
        self, reschedule_client: httpx.AsyncClient
    ) -> None:
        """A job removed with DELETE /jobs/{id} is registered again by a save (review L4)."""
        await _save(reschedule_client, "mod_list_refresh_interval", 600)
        deleted = await reschedule_client.delete(
            "/api/v1alpha1/jobs/mod_cache_refresh", headers=ADMIN
        )
        assert deleted.status_code == 200
        assert "mod_cache_refresh" not in await _jobs(reschedule_client)

        response = await _save(reschedule_client, "mod_list_refresh_interval", 600)

        assert response.status_code == 200
        jobs = await _jobs(reschedule_client)
        assert jobs["mod_cache_refresh"]["trigger_details"] == "every 600 seconds"

    async def test_other_settings_leave_the_jobs_alone(
        self, reschedule_client: httpx.AsyncClient
    ) -> None:
        await _save(reschedule_client, "mod_list_refresh_interval", 600)
        before = await _jobs(reschedule_client)

        response = await reschedule_client.post(
            "/api/v1alpha1/config/api/settings/auto_start_server",
            json={"value": True},
            headers=ADMIN,
        )

        assert response.status_code == 200
        assert await _jobs(reschedule_client) == before

    async def test_value_above_the_bound_is_refused(
        self, reschedule_client: httpx.AsyncClient
    ) -> None:
        await _save(reschedule_client, "mod_list_refresh_interval", 600)
        before = await _jobs(reschedule_client)

        response = await _save(reschedule_client, "mod_list_refresh_interval", 31_536_001)

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == ErrorCode.API_SETTING_INVALID
        assert await _jobs(reschedule_client) == before
        settings = await reschedule_client.get("/api/v1alpha1/config/api", headers=ADMIN)
        assert settings.json()["data"]["settings"]["mod_list_refresh_interval"] == 600

    async def test_scheduler_failure_is_reported_and_the_value_stays_saved(
        self,
        reschedule_client: httpx.AsyncClient,
        reschedule_scheduler: SchedulerService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def failing_add_interval_job(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("scheduler unavailable")

        monkeypatch.setattr(
            reschedule_scheduler, "add_interval_job", failing_add_interval_job
        )

        response = await _save(reschedule_client, "mod_list_refresh_interval", 1800)

        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.API_SETTING_NOT_APPLIED
        assert "mod_list_refresh_interval" in detail["message"]
        assert "scheduler unavailable" in detail["message"]
        assert "applies when the API restarts" in detail["message"]
        settings = await reschedule_client.get("/api/v1alpha1/config/api", headers=ADMIN)
        assert settings.json()["data"]["settings"]["mod_list_refresh_interval"] == 1800
