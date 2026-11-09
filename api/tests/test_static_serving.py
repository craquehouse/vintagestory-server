"""Tests for static file serving and SPA routing."""


from fastapi.testclient import TestClient

from vintagestory_api.main import app


class TestStaticFileRoutingBehavior:
    """Tests for static file routing behavior (without mocking filesystem)."""

    def test_nonexistent_static_file_returns_404(self) -> None:
        """Verify missing static files return 404."""
        client = TestClient(app)

        # Assuming static directory doesn't exist or file is missing
        response = client.get("/nonexistent.js")
        assert response.status_code == 404

    def test_nonexistent_client_route_returns_404(self) -> None:
        """Verify nonexistent client routes return 404 (when no static files)."""
        client = TestClient(app)

        # Routes that should fall back to index.html but static files don't exist
        response = client.get("/nonexistent/route")
        assert response.status_code == 404

    def test_health_responses_are_json(self) -> None:
        """Verify health endpoints return JSON responses."""
        client = TestClient(app)

        response = client.get("/healthz")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        response = client.get("/readyz")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
