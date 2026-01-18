"""Tests for metrics API endpoints.

Story 12.3: Metrics API Endpoints

Tests for GET /metrics/current and GET /metrics/history endpoints,
including authentication, authorization, and response format.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.metrics import MetricsSnapshot
from vintagestory_api.services.metrics import (
    MetricsBuffer,
    MetricsService,
    reset_metrics_service,
)

# Test API keys - match the test configuration
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


def _create_snapshot(
    timestamp: datetime | None = None,
    api_memory: float = 100.0,
    api_cpu: float = 5.0,
    game_memory: float | None = 200.0,
    game_cpu: float | None = 10.0,
) -> MetricsSnapshot:
    """Helper to create test snapshots."""
    return MetricsSnapshot(
        timestamp=timestamp or datetime.now(UTC),
        api_memory_mb=api_memory,
        api_cpu_percent=api_cpu,
        game_memory_mb=game_memory,
        game_cpu_percent=game_cpu,
    )


@pytest.fixture
def integration_app() -> Generator[FastAPI, None, None]:
    """Create app with overridden settings for integration testing."""
    test_settings = Settings(
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        debug=True,
    )

    app.dependency_overrides[get_settings] = lambda: test_settings
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(integration_app: FastAPI) -> TestClient:
    """Create a test client for FastAPI app."""
    return TestClient(integration_app)


@pytest.fixture
def mock_metrics_service() -> Generator[MagicMock, None, None]:
    """Create a mock metrics service with configurable buffer."""
    mock_service = MagicMock(spec=MetricsService)
    mock_buffer = MagicMock(spec=MetricsBuffer)
    mock_service.buffer = mock_buffer

    with patch(
        "vintagestory_api.routers.metrics.get_metrics_service",
        return_value=mock_service,
    ):
        yield mock_service


@pytest.fixture(autouse=True)
def reset_service() -> Generator[None, None, None]:
    """Reset metrics service singleton before each test."""
    reset_metrics_service()
    yield
    reset_metrics_service()


class TestMetricsCurrentEndpoint:
    """Tests for GET /metrics/current (AC: 1, 5)."""

    def test_current_returns_latest_snapshot_as_admin(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """AC 1: Returns latest MetricsSnapshot with all required fields as Admin."""
        timestamp = datetime.now(UTC)
        mock_metrics_service.buffer.get_latest.return_value = _create_snapshot(
            timestamp=timestamp,
            api_memory=128.5,
            api_cpu=2.3,
            game_memory=512.0,
            game_cpu=15.2,
        )

        response = client.get(
            "/api/v1alpha1/metrics/current",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["status"] == "ok"

        data = json_data["data"]
        assert data is not None
        # Check camelCase aliases in response
        assert data["apiMemoryMb"] == 128.5
        assert data["apiCpuPercent"] == 2.3
        assert data["gameMemoryMb"] == 512.0
        assert data["gameCpuPercent"] == 15.2
        assert "timestamp" in data

    def test_current_returns_null_when_buffer_empty(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """AC 5: Returns null for data when no metrics collected yet."""
        mock_metrics_service.buffer.get_latest.return_value = None

        response = client.get(
            "/api/v1alpha1/metrics/current",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["status"] == "ok"
        assert json_data["data"] is None

    def test_current_with_null_game_metrics(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """Test response when game server is not running (game metrics null)."""
        mock_metrics_service.buffer.get_latest.return_value = _create_snapshot(
            api_memory=100.0,
            api_cpu=5.0,
            game_memory=None,
            game_cpu=None,
        )

        response = client.get(
            "/api/v1alpha1/metrics/current",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["apiMemoryMb"] == 100.0
        assert data["gameMemoryMb"] is None
        assert data["gameCpuPercent"] is None


class TestMetricsHistoryEndpoint:
    """Tests for GET /metrics/history (AC: 2, 3, 5)."""

    def test_history_returns_all_metrics_without_filter(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """AC 2: Returns all available metrics when no minutes parameter."""
        snapshots = [
            _create_snapshot(
                timestamp=datetime.now(UTC) - timedelta(minutes=30), api_memory=100.0
            ),
            _create_snapshot(
                timestamp=datetime.now(UTC) - timedelta(minutes=15), api_memory=150.0
            ),
            _create_snapshot(timestamp=datetime.now(UTC), api_memory=200.0),
        ]
        mock_metrics_service.buffer.get_all.return_value = snapshots

        response = client.get(
            "/api/v1alpha1/metrics/history",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["status"] == "ok"

        data = json_data["data"]
        assert data["count"] == 3
        assert len(data["metrics"]) == 3
        # Check ordering preserved (oldest first)
        assert data["metrics"][0]["apiMemoryMb"] == 100.0
        assert data["metrics"][2]["apiMemoryMb"] == 200.0

    def test_history_filters_by_minutes_parameter(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """AC 3: Returns only metrics from last N minutes when minutes specified."""
        now = datetime.now(UTC)
        # Create snapshots: 90min ago, 45min ago, 15min ago
        snapshots = [
            _create_snapshot(timestamp=now - timedelta(minutes=90), api_memory=100.0),
            _create_snapshot(timestamp=now - timedelta(minutes=45), api_memory=150.0),
            _create_snapshot(timestamp=now - timedelta(minutes=15), api_memory=200.0),
        ]
        mock_metrics_service.buffer.get_all.return_value = snapshots

        response = client.get(
            "/api/v1alpha1/metrics/history?minutes=60",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        # Only 45min and 15min snapshots should be included
        assert data["count"] == 2
        assert len(data["metrics"]) == 2
        assert data["metrics"][0]["apiMemoryMb"] == 150.0
        assert data["metrics"][1]["apiMemoryMb"] == 200.0

    def test_history_returns_empty_list_when_buffer_empty(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """AC 5: Returns empty list (not error) when no metrics collected."""
        mock_metrics_service.buffer.get_all.return_value = []

        response = client.get(
            "/api/v1alpha1/metrics/history",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 0
        assert data["metrics"] == []

    def test_history_validates_minutes_minimum(self, client: TestClient) -> None:
        """Test minutes parameter must be >= 1."""
        response = client.get(
            "/api/v1alpha1/metrics/history?minutes=0",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 422  # Validation error

    def test_history_validates_minutes_maximum(self, client: TestClient) -> None:
        """Test minutes parameter must be <= 1440 (24 hours)."""
        response = client.get(
            "/api/v1alpha1/metrics/history?minutes=1441",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 422  # Validation error


class TestMetricsAuthorization:
    """Tests for authorization (AC: 4)."""

    def test_current_requires_admin_role(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """AC 4: Monitor role receives 403 on /current endpoint."""
        mock_metrics_service.buffer.get_latest.return_value = _create_snapshot()

        response = client.get(
            "/api/v1alpha1/metrics/current",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403
        error = response.json()["detail"]
        assert error["code"] == "FORBIDDEN"
        assert "Admin" in error["message"]

    def test_history_requires_admin_role(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """AC 4: Monitor role receives 403 on /history endpoint."""
        mock_metrics_service.buffer.get_all.return_value = []

        response = client.get(
            "/api/v1alpha1/metrics/history",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403
        error = response.json()["detail"]
        assert error["code"] == "FORBIDDEN"
        assert "Admin" in error["message"]

    def test_current_returns_401_without_auth(self, client: TestClient) -> None:
        """Test unauthenticated request returns 401."""
        response = client.get("/api/v1alpha1/metrics/current")

        assert response.status_code == 401

    def test_history_returns_401_without_auth(self, client: TestClient) -> None:
        """Test unauthenticated request returns 401."""
        response = client.get("/api/v1alpha1/metrics/history")

        assert response.status_code == 401


class TestMetricsResponseFormat:
    """Tests for response format compliance."""

    def test_current_response_uses_camel_case_aliases(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """Test response uses camelCase field names for frontend."""
        mock_metrics_service.buffer.get_latest.return_value = _create_snapshot()

        response = client.get(
            "/api/v1alpha1/metrics/current",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()["data"]
        # camelCase keys expected
        assert "apiMemoryMb" in data
        assert "apiCpuPercent" in data
        assert "gameMemoryMb" in data
        assert "gameCpuPercent" in data
        # snake_case keys should NOT be in response
        assert "api_memory_mb" not in data
        assert "api_cpu_percent" not in data

    def test_history_response_structure(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """Test history response has metrics list and count."""
        mock_metrics_service.buffer.get_all.return_value = [
            _create_snapshot(),
            _create_snapshot(),
        ]

        response = client.get(
            "/api/v1alpha1/metrics/history",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()["data"]
        assert "metrics" in data
        assert "count" in data
        assert isinstance(data["metrics"], list)
        assert isinstance(data["count"], int)

    def test_current_response_follows_api_envelope(
        self, client: TestClient, mock_metrics_service: MagicMock
    ) -> None:
        """Test response follows standard ApiResponse envelope."""
        mock_metrics_service.buffer.get_latest.return_value = _create_snapshot()

        response = client.get(
            "/api/v1alpha1/metrics/current",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        json_data = response.json()
        assert "status" in json_data
        assert json_data["status"] == "ok"
        assert "data" in json_data
