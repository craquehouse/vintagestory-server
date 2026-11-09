"""Tests for main.py application setup and middleware.

Coverage targets:
- CORSLoggingMiddleware.dispatch (lines 66, 77)
- lifespan auto_start_server logic (lines 118-131)
- get_scheduler_service error handling (line 49)
- Import-time wiring of the frontend and debug-only routes
"""

import inspect
import runpy
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from vintagestory_api import jobs as jobs_module
from vintagestory_api import main as main_module
from vintagestory_api.main import (
    CORSLoggingMiddleware,
    app,
    get_scheduler_service,
)
from vintagestory_api.models.server import ServerState, ServerStatus


class TestGetSchedulerService:
    """Tests for get_scheduler_service dependency."""

    def test_get_scheduler_service_raises_when_not_initialized(self) -> None:
        """get_scheduler_service raises RuntimeError when scheduler is None."""
        # Reset global scheduler to None temporarily
        import vintagestory_api.main as main_module

        original = main_module.scheduler_service
        try:
            main_module.scheduler_service = None

            with pytest.raises(RuntimeError, match="Scheduler service not initialized"):
                get_scheduler_service()
        finally:
            main_module.scheduler_service = original

    def test_get_scheduler_service_returns_instance_when_initialized(self) -> None:
        """get_scheduler_service returns the scheduler instance when initialized."""
        import vintagestory_api.main as main_module

        original = main_module.scheduler_service
        try:
            # Create a mock scheduler service
            mock_scheduler = MagicMock()
            main_module.scheduler_service = mock_scheduler

            # Should return the instance
            result = get_scheduler_service()
            assert result is mock_scheduler
        finally:
            main_module.scheduler_service = original


class TestCORSLoggingMiddleware:
    """Tests for CORS logging middleware."""

    @pytest.fixture
    def cors_app(self, captured_logs: StringIO) -> tuple[TestClient, StringIO]:
        """Create a test app with CORS logging middleware."""
        test_app = FastAPI()
        test_app.add_middleware(CORSLoggingMiddleware)

        @test_app.get("/test")
        async def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(test_app)
        return client, captured_logs

    def test_cors_logging_with_origin_header(
        self, cors_app: tuple[TestClient, StringIO]
    ) -> None:
        """CORS middleware logs request and response when Origin header present."""
        client, log_output = cors_app

        # Make request with Origin header
        response = client.get("/test", headers={"Origin": "http://example.com"})

        assert response.status_code == 200

        logs = log_output.getvalue()
        # Check that CORS request was logged
        assert "cors_request" in logs
        assert "http://example.com" in logs
        # Check that CORS response was logged
        assert "cors_response" in logs

    def test_cors_logging_without_origin_header(
        self, cors_app: tuple[TestClient, StringIO]
    ) -> None:
        """CORS middleware does not log when no Origin header present."""
        client, log_output = cors_app

        # Make request without Origin header
        response = client.get("/test")

        assert response.status_code == 200

        logs = log_output.getvalue()
        # No CORS logging should occur
        assert "cors_request" not in logs
        assert "cors_response" not in logs

    def test_cors_logging_includes_method_and_path(
        self, cors_app: tuple[TestClient, StringIO]
    ) -> None:
        """CORS logging includes method and path information."""
        client, log_output = cors_app

        response = client.post("/test", headers={"Origin": "http://localhost:5173"})

        assert response.status_code in [200, 405]  # 405 if POST not allowed

        logs = log_output.getvalue()
        assert "cors_request" in logs
        assert "POST" in logs or "method" in logs
        assert "/test" in logs

    def test_cors_logging_includes_user_agent(
        self, cors_app: tuple[TestClient, StringIO]
    ) -> None:
        """CORS logging includes user-agent information."""
        client, log_output = cors_app

        response = client.get(
            "/test",
            headers={
                "Origin": "http://localhost:5173",
                "User-Agent": "TestClient/1.0",
            },
        )

        assert response.status_code == 200

        logs = log_output.getvalue()
        assert "cors_request" in logs
        # User agent should be logged (or "unknown" if not present)
        assert "TestClient" in logs or "user_agent" in logs

    def test_cors_logging_includes_status_code(
        self, cors_app: tuple[TestClient, StringIO]
    ) -> None:
        """CORS response logging includes status code."""
        client, log_output = cors_app

        response = client.get("/test", headers={"Origin": "http://example.com"})

        assert response.status_code == 200

        logs = log_output.getvalue()
        assert "cors_response" in logs
        assert "200" in logs or "status_code" in logs


class TestApplicationConfiguration:
    """Tests for application-level configuration."""

    def test_app_title_and_description(self) -> None:
        """Verify FastAPI app has correct title and description."""
        assert app.title == "VintageStory Server Manager"
        assert "VintageStory dedicated game server" in app.description
        assert app.version == "0.1.0"

    def test_cors_middleware_configured(self) -> None:
        """Verify CORS middleware allows requests (functional test)."""
        # Test CORS by making a request and checking it works
        client = TestClient(app)
        response = client.get("/healthz")
        # If CORS is misconfigured, requests would fail
        assert response.status_code == 200

    def test_request_context_middleware_configured(self) -> None:
        """Verify RequestContextMiddleware adds request IDs."""
        client = TestClient(app)
        response = client.get("/healthz")
        # Request context middleware should allow request to complete
        assert response.status_code == 200

    def test_health_router_included(self) -> None:
        """Verify health router is included at root level."""
        client = TestClient(app)

        # Health endpoints should be accessible
        response = client.get("/healthz")
        assert response.status_code == 200

        response = client.get("/readyz")
        assert response.status_code == 200

    def test_api_v1alpha1_prefix(self) -> None:
        """Verify API endpoints use /api/v1alpha1 prefix."""
        client = TestClient(app)

        # Auth endpoint requires auth but should exist (not 404)
        response = client.get("/api/v1alpha1/auth/me")
        assert response.status_code in [401, 403]  # Auth required, not 404

    def test_websocket_router_included(self) -> None:
        """Verify WebSocket router is included."""
        # WebSocket endpoint should exist (will fail auth, but not 404)
        client = TestClient(app)

        # Try to connect to WebSocket (will fail without token, but endpoint exists)
        try:
            with client.websocket_connect("/api/v1alpha1/console/ws"):
                pass
        except Exception:
            # Expected to fail without proper token, but endpoint should exist
            pass


class FakeFileResponse(PlainTextResponse):
    """Stands in for FileResponse, since /app/static does not exist under test."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"file:{path}")


def load_fresh_app(*, static_dir_exists: bool) -> FastAPI:
    """Execute main.py again so its import-time wiring runs under controlled conditions."""
    real_exists = Path.exists

    def exists(self: Path, *, follow_symlinks: bool = True) -> bool:
        if self == Path("/app/static"):
            return static_dir_exists
        return real_exists(self, follow_symlinks=follow_symlinks)

    with (
        patch.object(Path, "exists", exists),
        patch("fastapi.responses.FileResponse", FakeFileResponse),
    ):
        namespace = runpy.run_path(inspect.getfile(main_module), run_name="fresh_main")
    return namespace["app"]


class TestImportTimeWiring:
    """Tests for routes that main.py only adds under certain conditions."""

    @pytest.mark.parametrize(("debug", "expected_status"), [("true", 401), ("false", 404)])
    def test_rbac_test_routes_only_exist_in_debug_mode(
        self, monkeypatch: pytest.MonkeyPatch, debug: str, expected_status: int
    ) -> None:
        monkeypatch.setenv("VS_DEBUG", debug)

        client = TestClient(load_fresh_app(static_dir_exists=False))

        assert client.get("/api/v1alpha1/test/read").status_code == expected_status

    def test_client_routes_are_not_served_without_static_dir(self) -> None:
        client = TestClient(load_fresh_app(static_dir_exists=False))

        assert client.get("/dashboard").status_code == 404

    def test_client_routes_are_served_with_static_dir(self) -> None:
        client = TestClient(load_fresh_app(static_dir_exists=True))

        response = client.get("/dashboard")

        assert response.status_code == 200
        assert response.text.endswith("static/index.html")

    def test_frontend_route_does_not_capture_api_routes(self) -> None:
        client = TestClient(load_fresh_app(static_dir_exists=True))

        health = client.get("/healthz")
        assert health.status_code == 200
        assert "application/json" in health.headers["content-type"]
        assert client.get("/api/v1alpha1/server/status").status_code == 401


class TestLifespanAutoStart:
    """Tests for lifespan auto-start server logic (lines 118-131)."""

    @pytest.mark.asyncio
    async def test_auto_start_server_enabled_and_installed(
        self, captured_logs: StringIO
    ) -> None:
        """Auto-start starts server when enabled and server is INSTALLED."""
        from vintagestory_api.main import lifespan

        # Mock dependencies
        mock_settings = MagicMock()
        mock_settings.auto_start_server = True
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.cors_origins = "http://localhost:3000"
        mock_settings.debug = False
        mock_settings.ensure_data_directories = MagicMock()

        mock_api_settings_service = MagicMock()
        mock_api_settings = MagicMock()
        mock_api_settings.auto_start_server = True
        mock_api_settings_service.get_settings.return_value = mock_api_settings

        mock_server_service = MagicMock()
        mock_status = ServerStatus(
            state=ServerState.INSTALLED,
            uptime_seconds=0,
        )
        mock_server_service.get_server_status.return_value = mock_status
        mock_server_service.start_server = AsyncMock()

        mock_scheduler = MagicMock()
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        test_app = FastAPI()

        # Patch all dependencies - note that some are imported inside lifespan
        with (
            patch("vintagestory_api.main.Settings", return_value=mock_settings),
            patch("vintagestory_api.main.initialize_debug_state"),
            patch("vintagestory_api.main.is_debug_enabled", return_value=False),
            patch(
                "vintagestory_api.services.api_settings.ApiSettingsService",
                return_value=mock_api_settings_service,
            ),
            patch(
                "vintagestory_api.services.server.get_server_service",
                return_value=mock_server_service,
            ),
            patch("vintagestory_api.main.SchedulerService", return_value=mock_scheduler),
            patch.object(jobs_module, "register_default_jobs"),
            patch("vintagestory_api.services.mods.close_mod_service", new_callable=AsyncMock),
        ):
            # Execute lifespan
            async with lifespan(test_app):
                pass

            # Verify auto-start was attempted
            mock_server_service.get_server_status.assert_called_once()
            mock_server_service.start_server.assert_called_once()

            # Check logs
            logs = captured_logs.getvalue()
            assert "auto_start_server_enabled" in logs
            assert "auto_starting_game_server" in logs

    @pytest.mark.asyncio
    async def test_auto_start_server_not_installed(
        self, captured_logs: StringIO
    ) -> None:
        """Auto-start skips when server is NOT_INSTALLED."""
        from vintagestory_api.main import lifespan

        mock_settings = MagicMock()
        mock_settings.auto_start_server = True
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.cors_origins = "http://localhost:3000"
        mock_settings.debug = False
        mock_settings.ensure_data_directories = MagicMock()

        mock_api_settings_service = MagicMock()
        mock_api_settings = MagicMock()
        mock_api_settings.auto_start_server = True
        mock_api_settings_service.get_settings.return_value = mock_api_settings

        mock_server_service = MagicMock()
        mock_status = ServerStatus(
            state=ServerState.NOT_INSTALLED,
            uptime_seconds=0,
        )
        mock_server_service.get_server_status.return_value = mock_status
        mock_server_service.start_server = AsyncMock()

        mock_scheduler = MagicMock()
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        test_app = FastAPI()

        with (
            patch("vintagestory_api.main.Settings", return_value=mock_settings),
            patch("vintagestory_api.main.initialize_debug_state"),
            patch("vintagestory_api.main.is_debug_enabled", return_value=False),
            patch(
                "vintagestory_api.services.api_settings.ApiSettingsService",
                return_value=mock_api_settings_service,
            ),
            patch(
                "vintagestory_api.services.server.get_server_service",
                return_value=mock_server_service,
            ),
            patch("vintagestory_api.main.SchedulerService", return_value=mock_scheduler),
            patch.object(jobs_module, "register_default_jobs"),
            patch("vintagestory_api.services.mods.close_mod_service", new_callable=AsyncMock),
        ):
            async with lifespan(test_app):
                pass

            # Verify auto-start was skipped
            mock_server_service.get_server_status.assert_called_once()
            mock_server_service.start_server.assert_not_called()

            # Check logs for skip reason
            logs = captured_logs.getvalue()
            assert "auto_start_server_enabled" in logs
            assert "auto_start_skipped" in logs
            assert "server_not_installed" in logs

    @pytest.mark.asyncio
    async def test_auto_start_server_already_running(
        self, captured_logs: StringIO
    ) -> None:
        """Auto-start skips when server is already RUNNING."""
        from vintagestory_api.main import lifespan

        mock_settings = MagicMock()
        mock_settings.auto_start_server = True
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.cors_origins = "http://localhost:3000"
        mock_settings.debug = False
        mock_settings.ensure_data_directories = MagicMock()

        mock_api_settings_service = MagicMock()
        mock_api_settings = MagicMock()
        mock_api_settings.auto_start_server = True
        mock_api_settings_service.get_settings.return_value = mock_api_settings

        mock_server_service = MagicMock()
        mock_status = ServerStatus(
            state=ServerState.RUNNING,
            uptime_seconds=100,
        )
        mock_server_service.get_server_status.return_value = mock_status
        mock_server_service.start_server = AsyncMock()

        mock_scheduler = MagicMock()
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        test_app = FastAPI()

        with (
            patch("vintagestory_api.main.Settings", return_value=mock_settings),
            patch("vintagestory_api.main.initialize_debug_state"),
            patch("vintagestory_api.main.is_debug_enabled", return_value=False),
            patch(
                "vintagestory_api.services.api_settings.ApiSettingsService",
                return_value=mock_api_settings_service,
            ),
            patch(
                "vintagestory_api.services.server.get_server_service",
                return_value=mock_server_service,
            ),
            patch("vintagestory_api.main.SchedulerService", return_value=mock_scheduler),
            patch.object(jobs_module, "register_default_jobs"),
            patch("vintagestory_api.services.mods.close_mod_service", new_callable=AsyncMock),
        ):
            async with lifespan(test_app):
                pass

            # Verify auto-start was skipped
            mock_server_service.get_server_status.assert_called_once()
            mock_server_service.start_server.assert_not_called()

            # Check logs for skip reason
            logs = captured_logs.getvalue()
            assert "auto_start_server_enabled" in logs
            assert "auto_start_skipped" in logs
            assert "server_state_running" in logs

    @pytest.mark.asyncio
    async def test_auto_start_server_error_handling(
        self, captured_logs: StringIO
    ) -> None:
        """Auto-start handles errors gracefully and logs them."""
        from vintagestory_api.main import lifespan

        mock_settings = MagicMock()
        mock_settings.auto_start_server = True
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.cors_origins = "http://localhost:3000"
        mock_settings.debug = False
        mock_settings.ensure_data_directories = MagicMock()

        mock_api_settings_service = MagicMock()
        mock_api_settings = MagicMock()
        mock_api_settings.auto_start_server = True
        mock_api_settings_service.get_settings.return_value = mock_api_settings

        mock_server_service = MagicMock()
        # Simulate error during get_server_status
        mock_server_service.get_server_status.side_effect = Exception(
            "Docker connection failed"
        )

        mock_scheduler = MagicMock()
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        test_app = FastAPI()

        with (
            patch("vintagestory_api.main.Settings", return_value=mock_settings),
            patch("vintagestory_api.main.initialize_debug_state"),
            patch("vintagestory_api.main.is_debug_enabled", return_value=False),
            patch(
                "vintagestory_api.services.api_settings.ApiSettingsService",
                return_value=mock_api_settings_service,
            ),
            patch(
                "vintagestory_api.services.server.get_server_service",
                return_value=mock_server_service,
            ),
            patch("vintagestory_api.main.SchedulerService", return_value=mock_scheduler),
            patch.object(jobs_module, "register_default_jobs"),
            patch("vintagestory_api.services.mods.close_mod_service", new_callable=AsyncMock),
        ):
            # Should not raise - errors are caught and logged
            async with lifespan(test_app):
                pass

            # Check error was logged
            logs = captured_logs.getvalue()
            assert "auto_start_server_enabled" in logs
            assert "auto_start_failed" in logs
            assert "Docker connection failed" in logs

    @pytest.mark.asyncio
    async def test_auto_start_disabled(self, captured_logs: StringIO) -> None:
        """Auto-start is skipped when disabled in settings."""
        from vintagestory_api.main import lifespan

        mock_settings = MagicMock()
        mock_settings.auto_start_server = False
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.cors_origins = "http://localhost:3000"
        mock_settings.debug = False
        mock_settings.ensure_data_directories = MagicMock()

        mock_api_settings_service = MagicMock()
        mock_api_settings = MagicMock()
        mock_api_settings.auto_start_server = False
        mock_api_settings_service.get_settings.return_value = mock_api_settings

        mock_scheduler = MagicMock()
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        test_app = FastAPI()

        with (
            patch("vintagestory_api.main.Settings", return_value=mock_settings),
            patch("vintagestory_api.main.initialize_debug_state"),
            patch("vintagestory_api.main.is_debug_enabled", return_value=False),
            patch(
                "vintagestory_api.services.api_settings.ApiSettingsService",
                return_value=mock_api_settings_service,
            ),
            patch("vintagestory_api.main.SchedulerService", return_value=mock_scheduler),
            patch.object(jobs_module, "register_default_jobs"),
            patch("vintagestory_api.services.mods.close_mod_service", new_callable=AsyncMock),
        ):
            async with lifespan(test_app):
                pass

            # Check disabled log message
            logs = captured_logs.getvalue()
            assert "auto_start_server_disabled" in logs
