"""Tests for health check endpoints.

Includes Story 7.3: Scheduler Health - tests for scheduler status in /healthz endpoint.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from vintagestory_api.models.responses import SchedulerHealthData
from vintagestory_api.models.server import ServerState, ServerStatus


class TestSchedulerHealthDataModel:
    """Tests for SchedulerHealthData Pydantic model (Story 7.3, Task 1)."""

    def test_scheduler_health_data_running(self) -> None:
        """SchedulerHealthData correctly models running scheduler."""
        data = SchedulerHealthData(status="running", job_count=5)

        assert data.status == "running"
        assert data.job_count == 5

    def test_scheduler_health_data_stopped(self) -> None:
        """SchedulerHealthData correctly models stopped scheduler."""
        data = SchedulerHealthData(status="stopped", job_count=0)

        assert data.status == "stopped"
        assert data.job_count == 0

    def test_scheduler_health_data_default_job_count(self) -> None:
        """SchedulerHealthData defaults job_count to 0."""
        data = SchedulerHealthData(status="running")

        assert data.status == "running"
        assert data.job_count == 0

    def test_scheduler_health_data_model_dump(self) -> None:
        """SchedulerHealthData.model_dump() returns dictionary for API response."""
        data = SchedulerHealthData(status="running", job_count=3)

        dumped = data.model_dump()

        assert dumped == {"status": "running", "job_count": 3}

    def test_scheduler_health_data_model_dump_json(self) -> None:
        """SchedulerHealthData serializes to valid JSON."""
        data = SchedulerHealthData(status="stopped", job_count=0)

        json_str = data.model_dump_json()

        assert '"status":"stopped"' in json_str
        assert '"job_count":0' in json_str


class TestHealthz:
    """Tests for the /healthz liveness probe endpoint."""

    def test_healthz_returns_200(self, client: TestClient) -> None:
        """Test that /healthz returns HTTP 200."""
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_healthz_follows_envelope_format(self, client: TestClient) -> None:
        """Test that /healthz response follows the API envelope format."""
        response = client.get("/healthz")
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data
        assert data["data"]["api"] == "healthy"

    def test_healthz_includes_game_server_status(self, client: TestClient) -> None:
        """Test that /healthz includes game_server status field."""
        response = client.get("/healthz")
        data = response.json()
        assert "game_server" in data["data"]
        assert data["data"]["game_server"] in [
            "not_installed",
            "stopped",
            "starting",
            "running",
            "stopping",
        ]

    def test_healthz_game_server_not_installed_by_default(
        self, client: TestClient
    ) -> None:
        """Test that game_server status is not_installed by default."""
        response = client.get("/healthz")
        data = response.json()
        assert data["data"]["game_server"] == "not_installed"

    def test_healthz_includes_game_server_version(self, client: TestClient) -> None:
        """Test that /healthz includes game_server_version field."""
        response = client.get("/healthz")
        data = response.json()
        assert "game_server_version" in data["data"]
        # Version is None when server is not installed
        assert data["data"]["game_server_version"] is None

    def test_healthz_includes_game_server_uptime(self, client: TestClient) -> None:
        """Test that /healthz includes game_server_uptime field."""
        response = client.get("/healthz")
        data = response.json()
        assert "game_server_uptime" in data["data"]
        # Uptime is None when server is not running
        assert data["data"]["game_server_uptime"] is None

    def test_healthz_includes_pending_restart(self, client: TestClient) -> None:
        """Test that /healthz includes game_server_pending_restart field."""
        response = client.get("/healthz")
        data = response.json()
        assert "game_server_pending_restart" in data["data"]
        # Pending restart is False by default
        assert data["data"]["game_server_pending_restart"] is False


class TestHealthzWithMockedServer:
    """Tests for /healthz with mocked server state."""

    def test_healthz_returns_version_when_installed(self, client: TestClient) -> None:
        """Test that game_server_version is returned when server is installed."""
        mock_status = ServerStatus(
            state=ServerState.INSTALLED,
            version="1.19.8",
            uptime_seconds=None,
        )
        mock_service = MagicMock()
        mock_service.get_server_status.return_value = mock_status

        with patch(
            "vintagestory_api.routers.health.get_server_service",
            return_value=mock_service,
        ):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["game_server_version"] == "1.19.8"
            assert data["data"]["game_server"] == "stopped"

    def test_healthz_returns_uptime_when_running(self, client: TestClient) -> None:
        """Test that game_server_uptime is returned when server is running."""
        mock_status = ServerStatus(
            state=ServerState.RUNNING,
            version="1.19.8",
            uptime_seconds=3600,
        )
        mock_service = MagicMock()
        mock_service.get_server_status.return_value = mock_status

        with patch(
            "vintagestory_api.routers.health.get_server_service",
            return_value=mock_service,
        ):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["game_server_uptime"] == 3600
            assert data["data"]["game_server"] == "running"

    def test_healthz_returns_pending_restart_when_true(
        self, client: TestClient
    ) -> None:
        """Test that game_server_pending_restart reflects actual state."""
        mock_restart_state = MagicMock()
        mock_restart_state.pending_restart = True

        with patch(
            "vintagestory_api.routers.health.get_restart_state",
            return_value=mock_restart_state,
        ):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["game_server_pending_restart"] is True

    def test_healthz_handles_restart_state_error(self, client: TestClient) -> None:
        """Test that health check succeeds even if get_restart_state() fails."""
        with patch(
            "vintagestory_api.routers.health.get_restart_state",
            side_effect=RuntimeError("Restart state unavailable"),
        ):
            response = client.get("/healthz")
            assert response.status_code == 200
            data = response.json()
            # Should default to False on error
            assert data["data"]["game_server_pending_restart"] is False


class TestReadyz:
    """Tests for the /readyz readiness probe endpoint."""

    def test_readyz_returns_200(self, client: TestClient) -> None:
        """Test that /readyz returns HTTP 200."""
        response = client.get("/readyz")
        assert response.status_code == 200

    def test_readyz_includes_ready_status(self, client: TestClient) -> None:
        """Test that /readyz includes ready status."""
        response = client.get("/readyz")
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["ready"] is True

    def test_readyz_includes_checks(self, client: TestClient) -> None:
        """Test that /readyz includes checks dictionary."""
        response = client.get("/readyz")
        data = response.json()
        assert "checks" in data["data"]
        assert data["data"]["checks"]["api"] is True

    def test_readyz_includes_game_server_check(self, client: TestClient) -> None:
        """Test that /readyz includes game_server check."""
        response = client.get("/readyz")
        data = response.json()
        assert "game_server" in data["data"]["checks"]
        # Game server is not running by default, so check is False
        assert data["data"]["checks"]["game_server"] is False


class TestHealthEndpointsNoAuth:
    """Tests that health endpoints require no authentication."""

    def test_healthz_requires_no_auth(self, client: TestClient) -> None:
        """Test that /healthz works without X-API-Key header."""
        # Make request without any authentication headers
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_readyz_requires_no_auth(self, client: TestClient) -> None:
        """Test that /readyz works without X-API-Key header."""
        # Make request without any authentication headers
        response = client.get("/readyz")
        assert response.status_code == 200


class TestApiAvailability:
    """Tests that API remains available regardless of game server status."""

    def test_api_responds_when_game_server_not_installed(
        self, client: TestClient
    ) -> None:
        """Test that API responds to health checks when game server not installed."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        # API should be healthy even when game server is not installed
        assert data["data"]["api"] == "healthy"
        assert data["data"]["game_server"] == "not_installed"


class TestApiResponseEnvelope:
    """Tests for the API response envelope format."""

    def test_success_envelope_has_required_fields(self, client: TestClient) -> None:
        """Test that success responses have status and data fields."""
        response = client.get("/healthz")
        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"
        # Error field should be None or absent for success
        assert data.get("error") is None

    def test_envelope_status_is_literal(self, client: TestClient) -> None:
        """Test that status field only contains valid values."""
        response = client.get("/healthz")
        data = response.json()
        assert data["status"] in ["ok", "error"]


class TestHealthzScheduler:
    """Tests for scheduler status in /healthz endpoint (Story 7.3, Task 2)."""

    def test_healthz_includes_scheduler_status(self, client: TestClient) -> None:
        """Test that /healthz includes scheduler status."""
        response = client.get("/healthz")
        data = response.json()
        assert "scheduler" in data["data"]
        assert data["data"]["scheduler"]["status"] in ["running", "stopped"]

    def test_healthz_scheduler_running_status(self, client: TestClient) -> None:
        """Test that scheduler status is 'running' when scheduler is active."""
        mock_scheduler = MagicMock()
        mock_scheduler.is_running = True
        mock_scheduler.get_jobs.return_value = []

        with patch(
            "vintagestory_api.routers.health._get_scheduler_service",
            return_value=mock_scheduler,
        ):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["scheduler"]["status"] == "running"

    def test_healthz_includes_job_count(self, client: TestClient) -> None:
        """Test that scheduler includes job_count field."""
        response = client.get("/healthz")
        data = response.json()
        assert "job_count" in data["data"]["scheduler"]
        assert isinstance(data["data"]["scheduler"]["job_count"], int)
        assert data["data"]["scheduler"]["job_count"] >= 0

    def test_healthz_job_count_is_zero_by_default(self, client: TestClient) -> None:
        """Test that job_count is 0 when no jobs are registered."""
        mock_scheduler = MagicMock()
        mock_scheduler.is_running = True
        mock_scheduler.get_jobs.return_value = []

        with patch(
            "vintagestory_api.routers.health._get_scheduler_service",
            return_value=mock_scheduler,
        ):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["scheduler"]["job_count"] == 0

    def test_healthz_scheduler_stopped_when_unavailable(
        self, client: TestClient
    ) -> None:
        """Test that scheduler status is 'stopped' when scheduler unavailable."""
        with patch(
            "vintagestory_api.routers.health._get_scheduler_service",
            side_effect=RuntimeError("Scheduler not initialized"),
        ):
            response = client.get("/healthz")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["scheduler"]["status"] == "stopped"
            assert data["data"]["scheduler"]["job_count"] == 0

    def test_healthz_scheduler_stopped_on_unexpected_error(
        self, client: TestClient
    ) -> None:
        """Test that scheduler status is 'stopped' on unexpected errors."""
        with patch(
            "vintagestory_api.routers.health._get_scheduler_service",
            side_effect=ValueError("Unexpected error"),
        ):
            response = client.get("/healthz")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["scheduler"]["status"] == "stopped"
            assert data["data"]["scheduler"]["job_count"] == 0

    def test_healthz_scheduler_stopped_when_not_running(
        self, client: TestClient
    ) -> None:
        """Test that scheduler status is 'stopped' when is_running is False."""
        mock_scheduler = MagicMock()
        mock_scheduler.is_running = False
        mock_scheduler.get_jobs.return_value = []

        with patch(
            "vintagestory_api.routers.health._get_scheduler_service",
            return_value=mock_scheduler,
        ):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["scheduler"]["status"] == "stopped"
            assert data["data"]["scheduler"]["job_count"] == 0

    def test_healthz_reflects_actual_job_count(self, client: TestClient) -> None:
        """Test that job_count reflects actual number of scheduled jobs."""
        mock_scheduler = MagicMock()
        mock_scheduler.is_running = True
        # Simulate 3 registered jobs
        mock_scheduler.get_jobs.return_value = [MagicMock(), MagicMock(), MagicMock()]

        with patch(
            "vintagestory_api.routers.health._get_scheduler_service",
            return_value=mock_scheduler,
        ):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["scheduler"]["status"] == "running"
            assert data["data"]["scheduler"]["job_count"] == 3
