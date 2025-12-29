"""Tests for server REST API endpoints (start, stop, restart, status)."""

import asyncio
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.models.server import ServerState
from vintagestory_api.routers.server import get_server_service
from vintagestory_api.services.server import ServerService

# pyright: reportPrivateUsage=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false


def _configure_stream_mocks(process: AsyncMock) -> None:
    """Configure stdout/stderr mocks to return EOF immediately.

    This prevents 'coroutine was never awaited' warnings from stream reading tasks.
    """
    process.stdout = AsyncMock()
    process.stdout.readline = AsyncMock(return_value=b"")
    process.stderr = AsyncMock()
    process.stderr.readline = AsyncMock(return_value=b"")


# Test API keys
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


class TestServerStartEndpoint:
    """Tests for POST /api/v1alpha1/server/start endpoint (AC: 1)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_start_requires_authentication(self, integration_client: TestClient) -> None:
        """POST /server/start requires API key."""
        response = integration_client.post("/api/v1alpha1/server/start")
        assert response.status_code == 401

    def test_start_requires_admin_role(self, integration_client: TestClient) -> None:
        """POST /server/start requires Admin role."""
        response = integration_client.post(
            "/api/v1alpha1/server/start",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"

    def test_start_not_installed_returns_400(self, integration_client: TestClient) -> None:
        """POST /server/start returns 400 when no server installed (AC: 4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/start",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )
        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == "SERVER_NOT_INSTALLED"

    def test_start_success(self, integration_client: TestClient, temp_data_dir: Path) -> None:
        """POST /server/start successfully starts server (AC: 1)."""
        # Create server files to simulate installed state
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()
            _configure_stream_mocks(process)

            # Block forever for monitor
            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            response = integration_client.post(
                "/api/v1alpha1/server/start",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["action"] == "start"
        assert data["data"]["previous_state"] == "installed"
        assert data["data"]["new_state"] == "running"

    def test_start_already_running_returns_409(
        self, integration_app: FastAPI, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/start returns 409 when already running."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        # Get the service and manually set state to running
        test_service = integration_app.dependency_overrides[get_server_service]()
        test_service._server_state = ServerState.RUNNING

        # Mock process to simulate running
        mock_process = AsyncMock()
        mock_process.returncode = None  # None = still running
        test_service._process = mock_process

        # Second start should fail
        response = integration_client.post(
            "/api/v1alpha1/server/start",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 409
        error = response.json()["detail"]
        assert error["code"] == "SERVER_ALREADY_RUNNING"


class TestServerStopEndpoint:
    """Tests for POST /api/v1alpha1/server/stop endpoint (AC: 2)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_stop_requires_authentication(self, integration_client: TestClient) -> None:
        """POST /server/stop requires API key."""
        response = integration_client.post("/api/v1alpha1/server/stop")
        assert response.status_code == 401

    def test_stop_requires_admin_role(self, integration_client: TestClient) -> None:
        """POST /server/stop requires Admin role."""
        response = integration_client.post(
            "/api/v1alpha1/server/stop",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )
        assert response.status_code == 403

    def test_stop_not_installed_returns_400(self, integration_client: TestClient) -> None:
        """POST /server/stop returns 400 when no server installed (AC: 4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/stop",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )
        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == "SERVER_NOT_INSTALLED"

    def test_stop_not_running_returns_409(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/stop returns 409 when server not running."""
        # Create server files (installed but not running)
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        response = integration_client.post(
            "/api/v1alpha1/server/stop",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 409
        error = response.json()["detail"]
        assert error["code"] == "SERVER_NOT_RUNNING"

    def test_stop_success(self, integration_client: TestClient, temp_data_dir: Path) -> None:
        """POST /server/stop successfully stops running server (AC: 2)."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()
            _configure_stream_mocks(process)

            # Use event to control wait behavior
            started = False

            async def controlled_wait():
                nonlocal started
                if not started:
                    started = True
                    await asyncio.sleep(100)  # Block for monitor
                # After stop, return immediately
                process.returncode = 0
                return 0

            process.wait = AsyncMock(side_effect=controlled_wait)
            mock_exec.return_value = process

            # Start server first
            response1 = integration_client.post(
                "/api/v1alpha1/server/start",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )
            assert response1.status_code == 200

            # Make wait() complete on stop
            async def stop_wait():
                process.returncode = 0
                return 0

            process.wait = AsyncMock(side_effect=stop_wait)

            # Stop server
            response2 = integration_client.post(
                "/api/v1alpha1/server/stop",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response2.status_code == 200
        data = response2.json()
        assert data["status"] == "ok"
        assert data["data"]["action"] == "stop"
        assert data["data"]["new_state"] == "installed"


class TestServerRestartEndpoint:
    """Tests for POST /api/v1alpha1/server/restart endpoint (AC: 3)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_restart_requires_authentication(self, integration_client: TestClient) -> None:
        """POST /server/restart requires API key."""
        response = integration_client.post("/api/v1alpha1/server/restart")
        assert response.status_code == 401

    def test_restart_requires_admin_role(self, integration_client: TestClient) -> None:
        """POST /server/restart requires Admin role."""
        response = integration_client.post(
            "/api/v1alpha1/server/restart",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )
        assert response.status_code == 403

    def test_restart_not_installed_returns_400(self, integration_client: TestClient) -> None:
        """POST /server/restart returns 400 when no server installed (AC: 4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/restart",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )
        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == "SERVER_NOT_INSTALLED"

    def test_restart_success_from_stopped(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/restart starts server when stopped (AC: 3)."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()
            _configure_stream_mocks(process)

            # Block forever for monitor
            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            response = integration_client.post(
                "/api/v1alpha1/server/restart",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["action"] == "restart"
        assert data["data"]["previous_state"] == "installed"
        assert data["data"]["new_state"] == "running"

    def test_restart_success_from_running(
        self, integration_app: FastAPI, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/restart stops and starts when running (AC: 3)."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        # Get the service and manually set state to running
        test_service = integration_app.dependency_overrides[get_server_service]()
        test_service._server_state = ServerState.RUNNING

        # Create mock process that's "running"
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None  # None = still running
        mock_process.send_signal = MagicMock()
        mock_process.kill = MagicMock()
        _configure_stream_mocks(mock_process)

        # wait() completes immediately for stop
        async def stop_wait():
            mock_process.returncode = 0
            return 0

        mock_process.wait = AsyncMock(side_effect=stop_wait)
        test_service._process = mock_process

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # New process for restart
            new_process = AsyncMock()
            new_process.pid = 12346
            new_process.returncode = None
            new_process.send_signal = MagicMock()
            new_process.kill = MagicMock()
            _configure_stream_mocks(new_process)

            # Block forever for new monitor
            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            new_process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = new_process

            # Restart server
            response = integration_client.post(
                "/api/v1alpha1/server/restart",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["action"] == "restart"
        assert data["data"]["previous_state"] == "running"
        assert data["data"]["new_state"] == "running"


class TestRestartEndpointErrorHandling:
    """Tests for /restart endpoint error handling (API level)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_restart_stop_failed_returns_500(
        self, integration_app: FastAPI, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/restart returns 500 when stop fails."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        # Get the service and set up a running state
        test_service = integration_app.dependency_overrides[get_server_service]()
        test_service._server_state = ServerState.RUNNING

        # Create a mock process that will fail to stop
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.send_signal = MagicMock(side_effect=OSError("Permission denied"))
        mock_process.kill = MagicMock()
        _configure_stream_mocks(mock_process)

        async def blocking_wait():
            await asyncio.sleep(100)
            return 0

        mock_process.wait = AsyncMock(side_effect=blocking_wait)
        test_service._process = mock_process

        response = integration_client.post(
            "/api/v1alpha1/server/restart",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 500
        error = response.json()["detail"]
        assert error["code"] == "SERVER_STOP_FAILED"

    def test_restart_start_failed_returns_500(
        self, integration_app: FastAPI, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/restart returns 500 when start fails after successful stop."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        # Server is not running, so restart will just try to start
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = OSError("Cannot spawn process")

            response = integration_client.post(
                "/api/v1alpha1/server/restart",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response.status_code == 500
        error = response.json()["detail"]
        assert error["code"] == "SERVER_START_FAILED"


class TestServerStatusEndpoint:
    """Tests for GET /api/v1alpha1/server/status endpoint (Story 3.3, AC: 1-4).

    Acceptance Criteria Coverage:
    - AC1: Admin can access status with state, version, uptime
    - AC2: Monitor can access status (read-only)
    - AC3: Uptime calculated from process start time, version from installed server
    - AC4: Not installed returns state="not_installed" with null version/uptime
    """

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_status_requires_authentication(self, integration_client: TestClient) -> None:
        """GET /server/status returns 401 without API key (AC: 1, 2)."""
        response = integration_client.get("/api/v1alpha1/server/status")

        assert response.status_code == 401
        error = response.json()["detail"]
        assert error["code"] == "UNAUTHORIZED"

    def test_status_accessible_by_admin(self, integration_client: TestClient) -> None:
        """GET /server/status accessible by Admin role (AC: 1)."""
        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data

    def test_status_accessible_by_monitor(self, integration_client: TestClient) -> None:
        """GET /server/status accessible by Monitor role (AC: 2)."""
        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data

    def test_status_returns_not_installed(self, integration_client: TestClient) -> None:
        """GET /server/status returns not_installed when server missing (AC: 4)."""
        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "not_installed"
        assert data["data"]["version"] is None
        assert data["data"]["uptime_seconds"] is None

    def test_status_returns_installed_stopped(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """GET /server/status returns installed when server exists but stopped (AC: 1, 3)."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "installed"
        assert data["data"]["version"] == "1.21.3"
        assert data["data"]["uptime_seconds"] is None

    def test_status_returns_running_with_uptime(self, temp_data_dir: Path) -> None:
        """GET /server/status includes uptime when server running (AC: 1, 3).

        Note: This test creates its own TestClient instead of using the shared
        integration_client fixture because it needs to configure a specific
        service state (RUNNING with mock process) BEFORE making requests. The
        shared fixture creates a fresh service on each dependency resolution.
        """
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        # Create service and configure running state
        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.RUNNING
        test_service._server_start_time = time.time() - 60

        # Mock process with None returncode (still running)
        mock_process = MagicMock()
        mock_process.returncode = None
        test_service._process = mock_process

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["data"]["state"] == "running"
            assert data["data"]["version"] == "1.21.3"
            # Uptime should be at least 60 seconds (with some tolerance)
            assert data["data"]["uptime_seconds"] is not None
            assert data["data"]["uptime_seconds"] >= 59
        finally:
            app.dependency_overrides.clear()

    def test_status_follows_api_envelope_format(self, integration_client: TestClient) -> None:
        """GET /server/status follows standard API envelope (AC: 1, Task 1.3)."""
        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Verify Content-Type header
        assert response.headers.get("content-type") == "application/json"

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"
        # Check expected fields in data - exactly 4 fields, no extras
        assert set(data["data"].keys()) == {"state", "version", "uptime_seconds", "last_exit_code"}

    def test_status_returns_starting_state(self, temp_data_dir: Path) -> None:
        """GET /server/status returns starting state during server startup (AC: 1)."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.STARTING

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["state"] == "starting"
        finally:
            app.dependency_overrides.clear()

    def test_status_returns_stopping_state(self, temp_data_dir: Path) -> None:
        """GET /server/status returns stopping state during server shutdown (AC: 1)."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.STOPPING

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["state"] == "stopping"
        finally:
            app.dependency_overrides.clear()

    def test_status_returns_installed_after_error(self, temp_data_dir: Path) -> None:
        """GET /server/status returns installed after process error (AC: 1).

        Note: ERROR is a transitional state during failed operations. Once the
        process ends, the status returns to INSTALLED since the server files
        exist. This test verifies the expected behavior after an error.
        """
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        # Simulate a previous error - server crashed with exit code 1
        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.INSTALLED  # Reverted from ERROR
        test_service._last_exit_code = 1  # Non-zero indicates error

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["state"] == "installed"
            assert data["data"]["last_exit_code"] == 1  # Error indicated by exit code
        finally:
            app.dependency_overrides.clear()

    def test_status_returns_negative_exit_code(self, temp_data_dir: Path) -> None:
        """GET /server/status includes negative exit codes (signal kills) (AC: 1)."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.INSTALLED
        test_service._last_exit_code = -9  # Killed by SIGKILL

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["last_exit_code"] == -9
        finally:
            app.dependency_overrides.clear()

    def test_status_uptime_calculation_accuracy(self, temp_data_dir: Path) -> None:
        """GET /server/status calculates uptime from server start time accurately (AC: 3)."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        # Set a precise start time
        start_time = time.time() - 120.5  # 120.5 seconds ago

        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.RUNNING
        test_service._server_start_time = start_time

        mock_process = MagicMock()
        mock_process.returncode = None
        test_service._process = mock_process

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            # Uptime should be 120 seconds (truncated from 120.5)
            # Allow 1 second tolerance for test execution time
            assert 119 <= data["data"]["uptime_seconds"] <= 122
        finally:
            app.dependency_overrides.clear()
