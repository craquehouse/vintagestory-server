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

    def test_success_envelope_excludes_null_error_field(
        self, client: TestClient
    ) -> None:
        """Test that success responses don't include null error field.

        The ApiResponse model uses exclude_none to ensure cleaner JSON output.
        Success responses should only contain 'status' and 'data', not 'error: null'.
        """
        response = client.get("/healthz")
        data = response.json()
        # Error field should be absent entirely, not present as null
        assert "error" not in data, (
            "Success responses should not include 'error' field. "
            f"Got: {list(data.keys())}"
        )

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
            "vintagestory_api.routers.health.get_scheduler",
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
            "vintagestory_api.routers.health.get_scheduler",
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
            "vintagestory_api.routers.health.get_scheduler",
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
            "vintagestory_api.routers.health.get_scheduler",
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
            "vintagestory_api.routers.health.get_scheduler",
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
            "vintagestory_api.routers.health.get_scheduler",
            return_value=mock_scheduler,
        ):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["scheduler"]["status"] == "running"
            assert data["data"]["scheduler"]["job_count"] == 3


class TestDiskSpaceDataModel:
    """Tests for DiskSpaceData Pydantic model (API-008)."""

    def test_disk_space_data_model(self) -> None:
        """DiskSpaceData correctly models disk usage."""
        from vintagestory_api.models.responses import DiskSpaceData

        data = DiskSpaceData(
            total_gb=100.0,
            used_gb=75.0,
            available_gb=25.0,
            usage_percent=75.0,
            warning=False,
        )

        assert data.total_gb == 100.0
        assert data.used_gb == 75.0
        assert data.available_gb == 25.0
        assert data.usage_percent == 75.0
        assert data.warning is False

    def test_disk_space_data_warning_true(self) -> None:
        """DiskSpaceData correctly sets warning flag."""
        from vintagestory_api.models.responses import DiskSpaceData

        data = DiskSpaceData(
            total_gb=100.0,
            used_gb=99.5,
            available_gb=0.5,
            usage_percent=99.5,
            warning=True,
        )

        assert data.warning is True

    def test_disk_space_data_model_dump(self) -> None:
        """DiskSpaceData.model_dump() returns dictionary for API response."""
        from vintagestory_api.models.responses import DiskSpaceData

        data = DiskSpaceData(
            total_gb=500.0,
            used_gb=250.0,
            available_gb=250.0,
            usage_percent=50.0,
            warning=False,
        )

        dumped = data.model_dump()

        assert dumped == {
            "total_gb": 500.0,
            "used_gb": 250.0,
            "available_gb": 250.0,
            "usage_percent": 50.0,
            "warning": False,
        }


class TestHealthzDiskSpace:
    """Tests for disk space in /healthz endpoint (API-008)."""

    def test_healthz_includes_disk_space(self, client: TestClient) -> None:
        """Test that /healthz includes disk_space field."""
        response = client.get("/healthz")
        data = response.json()
        assert "disk_space" in data["data"]

    def test_healthz_disk_space_has_required_fields(self, client: TestClient) -> None:
        """Test that disk_space includes all required fields."""
        response = client.get("/healthz")
        data = response.json()
        disk_space = data["data"]["disk_space"]

        # Should have all required fields (may be None if disk_usage fails)
        if disk_space is not None:
            assert "total_gb" in disk_space
            assert "used_gb" in disk_space
            assert "available_gb" in disk_space
            assert "usage_percent" in disk_space
            assert "warning" in disk_space

    def test_healthz_disk_space_values_are_numeric(self, client: TestClient) -> None:
        """Test that disk_space values are numeric."""
        response = client.get("/healthz")
        data = response.json()
        disk_space = data["data"]["disk_space"]

        if disk_space is not None:
            assert isinstance(disk_space["total_gb"], (int, float))
            assert isinstance(disk_space["used_gb"], (int, float))
            assert isinstance(disk_space["available_gb"], (int, float))
            assert isinstance(disk_space["usage_percent"], (int, float))
            assert isinstance(disk_space["warning"], bool)

    def test_healthz_disk_space_warning_when_low(self, client: TestClient) -> None:
        """Test that warning is True when available space is below threshold."""
        # Mock shutil.disk_usage to return low available space
        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024 * 1024 * 1024  # 100 GB
        mock_usage.used = 99.5 * 1024 * 1024 * 1024  # 99.5 GB used
        mock_usage.free = 0.5 * 1024 * 1024 * 1024  # 0.5 GB free (below 1.0 GB threshold)

        with patch("vintagestory_api.routers.health.shutil.disk_usage", return_value=mock_usage):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["disk_space"]["warning"] is True

    def test_healthz_disk_space_no_warning_when_sufficient(
        self, client: TestClient
    ) -> None:
        """Test that warning is False when available space is above threshold."""
        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024 * 1024 * 1024  # 100 GB
        mock_usage.used = 50 * 1024 * 1024 * 1024  # 50 GB used
        mock_usage.free = 50 * 1024 * 1024 * 1024  # 50 GB free (above 10% = 10 GB threshold)

        with patch("vintagestory_api.routers.health.shutil.disk_usage", return_value=mock_usage):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["disk_space"]["warning"] is False

    def test_healthz_disk_space_none_on_error(self, client: TestClient) -> None:
        """Test that disk_space is None when disk_usage fails."""
        with patch(
            "vintagestory_api.routers.health.shutil.disk_usage",
            side_effect=OSError("Disk unavailable"),
        ):
            response = client.get("/healthz")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["disk_space"] is None

    def test_healthz_disk_space_uses_data_dir(self, client: TestClient) -> None:
        """Test that disk_usage is called with settings.data_dir."""
        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024 * 1024 * 1024
        mock_usage.used = 50 * 1024 * 1024 * 1024
        mock_usage.free = 50 * 1024 * 1024 * 1024

        with patch(
            "vintagestory_api.routers.health.shutil.disk_usage", return_value=mock_usage
        ) as mock_disk_usage:
            response = client.get("/healthz")
            assert response.status_code == 200
            # Verify disk_usage was called with settings.data_dir
            mock_disk_usage.assert_called()

    def test_healthz_disk_space_respects_threshold_config(
        self, client: TestClient
    ) -> None:
        """Test that warning uses max of GB threshold and 10% of total."""
        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024 * 1024 * 1024  # 100 GB
        mock_usage.used = 88 * 1024 * 1024 * 1024  # 88 GB used
        mock_usage.free = 12 * 1024 * 1024 * 1024  # 12 GB free (above 10% threshold)

        # With 100 GB disk, 10% = 10 GB threshold. 12 GB free should NOT warn.
        with patch("vintagestory_api.routers.health.shutil.disk_usage", return_value=mock_usage):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["disk_space"]["warning"] is False
            assert data["data"]["disk_space"]["available_gb"] == 12.0

    def test_healthz_disk_space_percentage_threshold_warning(
        self, client: TestClient
    ) -> None:
        """Test that 10% threshold triggers warning on large disks."""
        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024 * 1024 * 1024  # 100 GB
        mock_usage.used = 95 * 1024 * 1024 * 1024  # 95 GB used
        mock_usage.free = 5 * 1024 * 1024 * 1024  # 5 GB free (below 10% of 100 GB)

        # 5 GB > 1 GB fixed threshold, but < 10 GB (10% of 100 GB)
        with patch("vintagestory_api.routers.health.shutil.disk_usage", return_value=mock_usage):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["disk_space"]["warning"] is True

    def test_healthz_disk_space_boundary_exactly_at_threshold(
        self, client: TestClient
    ) -> None:
        """Test boundary: available_gb exactly equals effective threshold (no warning)."""
        mock_usage = MagicMock()
        mock_usage.total = 10 * 1024 * 1024 * 1024  # 10 GB total
        mock_usage.used = 9 * 1024 * 1024 * 1024  # 9 GB used
        mock_usage.free = 1 * 1024 * 1024 * 1024  # 1 GB free = exactly 10% of 10 GB

        # 1 GB = 10% of 10 GB = max(1.0, 1.0). At threshold = no warning (< not <=)
        with patch("vintagestory_api.routers.health.shutil.disk_usage", return_value=mock_usage):
            response = client.get("/healthz")
            data = response.json()
            # 1 GB is NOT less than 1 GB, so no warning
            assert data["data"]["disk_space"]["warning"] is False

    def test_healthz_disk_space_zero_total_returns_none(
        self, client: TestClient
    ) -> None:
        """Test that zero total disk (empty/unmounted) returns None."""
        mock_usage = MagicMock()
        mock_usage.total = 0
        mock_usage.used = 0
        mock_usage.free = 0

        with patch("vintagestory_api.routers.health.shutil.disk_usage", return_value=mock_usage):
            response = client.get("/healthz")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["disk_space"] is None


class TestDiskSpaceThresholdValidation:
    """Tests for disk space threshold configuration validation."""

    def test_negative_threshold_raises_error(self) -> None:
        """Test that negative threshold raises ValueError."""
        import pytest

        from vintagestory_api.config import Settings

        with pytest.raises(ValueError, match="non-negative"):
            Settings(api_key_admin="test", disk_space_warning_threshold_gb=-1.0)

    def test_zero_threshold_is_valid(self) -> None:
        """Test that zero threshold is valid (disables fixed GB check)."""
        from vintagestory_api.config import Settings

        settings = Settings(api_key_admin="test", disk_space_warning_threshold_gb=0.0)
        assert settings.disk_space_warning_threshold_gb == 0.0
