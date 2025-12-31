"""Tests for health check endpoints."""

from fastapi.testclient import TestClient


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
