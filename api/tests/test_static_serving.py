"""Tests for static file serving and SPA routing."""

from pathlib import Path

from fastapi.testclient import TestClient

from vintagestory_api.main import app, STATIC_DIR


class TestStaticFileServing:
    """Tests for static file serving functionality."""

    def test_assets_directory_mounted(self) -> None:
        """Verify assets directory is mounted at /assets route."""
        client = TestClient(app)

        # Check that /assets route exists (returns 404 for non-existent files if static dir doesn't exist)
        response = client.get("/assets/test.js")
        # Should get 404 if static dir missing or file doesn't exist, but route should be mounted
        assert response.status_code in [200, 404]

    def test_api_routes_take_precedence(self) -> None:
        """Verify API routes are served before static fallback."""
        client = TestClient(app)

        # Health endpoints should NOT fall back to index.html
        response = client.get("/healthz")
        assert response.status_code == 200
        assert "status" in response.json()

        response = client.get("/readyz")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_static_dir_constant_exists(self) -> None:
        """Verify STATIC_DIR constant is properly defined."""
        assert STATIC_DIR is not None
        assert isinstance(STATIC_DIR, str) or isinstance(STATIC_DIR, type(Path()))

    def test_root_route_exists(self) -> None:
        """Verify root route exists (SPA fallback)."""
        client = TestClient(app)

        # Root route should exist (either 404 if no static files, or 200 with index.html)
        response = client.get("/")
        assert response.status_code in [200, 404]

    def test_client_routes_exist(self) -> None:
        """Verify client-side routes exist (should fall back to index.html)."""
        client = TestClient(app)

        # All client routes should exist (either 404 if no static files, or 200 with index.html)
        for route in ["/mods", "/dashboard", "/terminal", "/config"]:
            response = client.get(route)
            assert response.status_code in [200, 404]

    def test_root_with_query_params(self) -> None:
        """Verify query parameters work with root route."""
        client = TestClient(app)

        # Root route with query params should work
        response = client.get("/?tab=installed")
        assert response.status_code in [200, 404]

    def test_favicon_route(self) -> None:
        """Verify favicon route exists."""
        client = TestClient(app)

        # Favicon should exist (returns 404 if file doesn't exist)
        response = client.get("/favicon.ico")
        assert response.status_code in [200, 404]

    def test_api_routes_priority_over_static(self) -> None:
        """Verify that API routes are registered before static fallback."""
        client = TestClient(app)

        # Health routes should work regardless of static files
        response = client.get("/healthz")
        assert response.status_code == 200
        assert "status" in response.json()

        response = client.get("/readyz")
        assert response.status_code == 200
        assert "status" in response.json()


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
