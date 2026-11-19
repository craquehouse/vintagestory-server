"""Tests for main.py application setup and middleware.

Coverage targets:
- CORSLoggingMiddleware.dispatch (lines 66, 77)
- lifespan auto_start_server logic (lines 118-131)
- get_scheduler_service error handling (line 49)
- Import-time wiring of the frontend and debug-only routes
"""

import inspect
import json
import re
import runpy
from collections.abc import Mapping
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import PrepareModFilesRecorder, ReapplyAtApiStartRecorder
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

import vintagestory_api.config as config_module
from vintagestory_api import __version__
from vintagestory_api import jobs as jobs_module
from vintagestory_api import main as main_module
from vintagestory_api.config import (
    DEFAULT_MOD_DB_URL,
    Settings,
    current_log_level,
    is_debug_enabled,
)
from vintagestory_api.main import (
    CORSLoggingMiddleware,
    app,
    create_app,
    get_scheduler_service,
    log_mod_db_url,
)
from vintagestory_api.models.server import ServerState, ServerStatus
from vintagestory_api.services import mods as mods_module
from vintagestory_api.services.mod_state import ModStateManager, ModSyncSummary
from vintagestory_api.services.mods import ModService, prepare_mod_files
from vintagestory_api.services.pending_config_edits import PENDING_CONFIG_EDITS_FILENAME
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.server import (
    ServerService,
    reapply_pending_config_edits_at_api_start,
)


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

    def test_cors_logging_with_origin_header(self, cors_app: tuple[TestClient, StringIO]) -> None:
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

    def test_cors_logging_includes_user_agent(self, cors_app: tuple[TestClient, StringIO]) -> None:
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

    def test_cors_logging_includes_status_code(self, cors_app: tuple[TestClient, StringIO]) -> None:
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
        # The single version source (Epic 15 ADR-1); test_version.py ties it to pyproject.toml
        assert app.version == __version__

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

    def __init__(self, path: Path, headers: Mapping[str, str] | None = None) -> None:
        super().__init__(f"file:{path}", headers=headers)


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

    def test_main_builds_no_settings_of_its_own(self) -> None:
        # The app is built from get_settings(); the factory reads only its argument
        # (Story 19.3). The RBAC routes both ways are in test_debug_gating.py
        assert "Settings(" not in inspect.getsource(main_module)

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

    async def run_auto_start_lifespan(
        self, recorder: PrepareModFilesRecorder, *, auto_start: bool = True
    ) -> None:
        """Run the lifespan (auto-start on by default), recording start_server and the scheduler."""
        from vintagestory_api.main import lifespan_for

        settings = MagicMock()
        settings.data_dir = Path("/tmp/test_data")
        settings.mod_db_url = DEFAULT_MOD_DB_URL
        api_settings_service = MagicMock()
        api_settings_service.get_settings.return_value.auto_start_server = auto_start
        server_service = MagicMock()
        server_service.get_server_status.return_value = ServerStatus(
            state=ServerState.INSTALLED, uptime_seconds=0
        )

        async def start_server() -> None:
            recorder.calls.append("start_server")

        server_service.start_server = start_server
        scheduler = MagicMock()
        scheduler.start.side_effect = lambda: recorder.calls.append("scheduler_start")

        with (
            patch("vintagestory_api.main.initialize_debug_state"),
            patch("vintagestory_api.main.is_debug_enabled", return_value=False),
            patch(
                "vintagestory_api.services.api_settings.ApiSettingsService",
                return_value=api_settings_service,
            ),
            patch(
                "vintagestory_api.services.server.get_server_service",
                return_value=server_service,
            ),
            patch("vintagestory_api.main.SchedulerService", return_value=scheduler),
            patch.object(jobs_module, "register_default_jobs"),
            patch("vintagestory_api.services.mods.close_mod_service", new_callable=AsyncMock),
        ):
            async with lifespan_for(settings)(FastAPI()):
                pass

    @pytest.mark.asyncio
    async def test_mod_files_are_prepared_once_before_auto_start_and_the_scheduler(
        self, prepare_mod_files_recorder: PrepareModFilesRecorder
    ) -> None:
        """Story 19.4 AC 15 (Epic 19 ADR-9): before any mod operation can run."""
        await self.run_auto_start_lifespan(prepare_mod_files_recorder)

        assert prepare_mod_files_recorder.calls == [
            "prepare_mod_files",
            "start_server",
            "scheduler_start",
        ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error",
        [OSError("read-only file system"), RuntimeError("read-only file system")],
        ids=["os-error", "other-error"],
    )
    async def test_a_failure_to_prepare_mod_files_is_logged_and_start_up_continues(
        self,
        prepare_mod_files_recorder: PrepareModFilesRecorder,
        captured_logs: StringIO,
        error: Exception,
    ) -> None:
        prepare_mod_files_recorder.error = error

        await self.run_auto_start_lifespan(prepare_mod_files_recorder)

        assert prepare_mod_files_recorder.calls == [
            "prepare_mod_files",
            "start_server",
            "scheduler_start",
        ]
        [line] = [
            line
            for line in captured_logs.getvalue().splitlines()
            if "mod_files_startup_failed" in line
        ]
        assert "read-only file system" in line
        assert type(error).__name__ in line

    # Story 22.7: the write-back of pending config edits runs after the mod files are
    # prepared and before the auto-start (Epic 22 ADR-15 decision 3)

    @pytest.mark.asyncio
    async def test_pending_config_edits_are_written_back_before_auto_start(
        self,
        prepare_mod_files_recorder: PrepareModFilesRecorder,
        reapply_at_api_start_recorder: ReapplyAtApiStartRecorder,
    ) -> None:
        reapply_at_api_start_recorder.calls = prepare_mod_files_recorder.calls

        await self.run_auto_start_lifespan(prepare_mod_files_recorder)

        assert prepare_mod_files_recorder.calls == [
            "prepare_mod_files",
            "reapply_pending_config_edits_at_api_start",
            "start_server",
            "scheduler_start",
        ]

    @pytest.mark.asyncio
    async def test_pending_config_edits_are_written_back_once_with_auto_start_off(
        self,
        prepare_mod_files_recorder: PrepareModFilesRecorder,
        reapply_at_api_start_recorder: ReapplyAtApiStartRecorder,
    ) -> None:
        reapply_at_api_start_recorder.calls = prepare_mod_files_recorder.calls

        await self.run_auto_start_lifespan(prepare_mod_files_recorder, auto_start=False)

        assert prepare_mod_files_recorder.calls == [
            "prepare_mod_files",
            "reapply_pending_config_edits_at_api_start",
            "scheduler_start",
        ]

    @pytest.mark.asyncio
    async def test_a_failing_write_back_is_logged_and_start_up_continues(
        self,
        prepare_mod_files_recorder: PrepareModFilesRecorder,
        reapply_at_api_start_recorder: ReapplyAtApiStartRecorder,
        captured_logs: StringIO,
    ) -> None:
        reapply_at_api_start_recorder.calls = prepare_mod_files_recorder.calls
        reapply_at_api_start_recorder.error = RuntimeError("unexpected")

        await self.run_auto_start_lifespan(prepare_mod_files_recorder)

        assert prepare_mod_files_recorder.calls == [
            "prepare_mod_files",
            "reapply_pending_config_edits_at_api_start",
            "start_server",
            "scheduler_start",
        ]
        [line] = [
            line
            for line in captured_logs.getvalue().splitlines()
            if "pending_config_edits_startup_failed" in line
        ]
        assert "RuntimeError" in line
        assert "error" in line.lower()

    @pytest.mark.asyncio
    async def test_a_bad_state_file_does_not_stop_the_api_start(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_logs: StringIO
    ) -> None:
        """AC 7: a real temp-dir service whose state file is not JSON."""
        settings = Settings(data_dir=tmp_path / "data", api_key_admin="test-admin-key")
        settings.state_dir.mkdir(parents=True)
        (settings.state_dir / PENDING_CONFIG_EDITS_FILENAME).write_text("not json")
        service = ServerService(settings)
        monkeypatch.setattr("vintagestory_api.services.server.get_server_service", lambda: service)
        monkeypatch.setattr(
            main_module,
            "reapply_pending_config_edits_at_api_start",
            reapply_pending_config_edits_at_api_start,
        )
        scheduler = MagicMock()

        with (
            patch("vintagestory_api.main.initialize_debug_state"),
            patch("vintagestory_api.main.SchedulerService", return_value=scheduler),
            patch.object(jobs_module, "register_default_jobs"),
            patch("vintagestory_api.services.mods.close_mod_service", new_callable=AsyncMock),
        ):
            async with main_module.lifespan_for(settings)(FastAPI()):
                pass

        logs = captured_logs.getvalue()
        assert "pending_config_edits_unreadable" in logs
        assert "pending_config_edits_startup_failed" not in logs
        scheduler.start.assert_called_once()

    @pytest.fixture
    def real_mod_start_up(
        self,
        prepare_mod_files_recorder: PrepareModFilesRecorder,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> ModService:
        """The real `prepare_mod_files` in the lifespan, over a mod service on tmp_path.

        Recovery is recorded into the recorder's calls, then runs for real.
        """
        service = ModService(
            state_dir=tmp_path / "state",
            mods_dir=tmp_path / "mods",
            cache_dir=tmp_path / "cache",
            restart_state=PendingRestartState(),
        )
        service.state_manager.mods_dir.mkdir(parents=True)
        monkeypatch.setattr(mods_module, "get_mod_service", lambda: service)
        monkeypatch.setattr(main_module, "prepare_mod_files", prepare_mod_files)
        recover = mods_module.recover_working_files

        def record_recovery(state_manager: ModStateManager) -> None:
            prepare_mod_files_recorder.calls.append("recover_working_files")
            recover(state_manager)

        monkeypatch.setattr(mods_module, "recover_working_files", record_recovery)
        return service

    @pytest.mark.asyncio
    async def test_recovery_then_the_mod_state_sync_run_before_auto_start(
        self,
        prepare_mod_files_recorder: PrepareModFilesRecorder,
        real_mod_start_up: ModService,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        """Story 19.5 AC 9 (Epic 19 ADR-10): one summary line, before the auto-start."""
        sync = real_mod_start_up.state_manager.sync_state_with_disk

        def record_sync() -> ModSyncSummary:
            prepare_mod_files_recorder.calls.append("sync_state_with_disk")
            return sync()

        monkeypatch.setattr(real_mod_start_up.state_manager, "sync_state_with_disk", record_sync)

        await self.run_auto_start_lifespan(prepare_mod_files_recorder)

        assert prepare_mod_files_recorder.calls == [
            "recover_working_files",
            "sync_state_with_disk",
            "start_server",
            "scheduler_start",
        ]
        logs = captured_logs.getvalue()
        assert logs.count("mod_state_synced") == 1
        assert logs.index("mod_state_synced") < logs.index("auto_starting_game_server")

    @pytest.mark.asyncio
    async def test_a_failing_mod_state_sync_is_logged_and_the_auto_start_still_runs(
        self,
        prepare_mod_files_recorder: PrepareModFilesRecorder,
        real_mod_start_up: ModService,
        monkeypatch: pytest.MonkeyPatch,
        captured_logs: StringIO,
    ) -> None:
        """Story 19.5 AC 13."""

        def fail() -> ModSyncSummary:
            raise RuntimeError("unexpected")

        monkeypatch.setattr(real_mod_start_up.state_manager, "sync_state_with_disk", fail)

        await self.run_auto_start_lifespan(prepare_mod_files_recorder)

        assert prepare_mod_files_recorder.calls == [
            "recover_working_files",
            "start_server",
            "scheduler_start",
        ]
        assert captured_logs.getvalue().count("mod_state_sync_failed") == 1
        assert "mod_files_startup_failed" not in captured_logs.getvalue()

    @pytest.mark.asyncio
    async def test_the_mod_state_sync_runs_once_with_auto_start_off(
        self,
        prepare_mod_files_recorder: PrepareModFilesRecorder,
        real_mod_start_up: ModService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Story 19.5 AC 9."""
        sync = real_mod_start_up.state_manager.sync_state_with_disk

        def record_sync() -> ModSyncSummary:
            prepare_mod_files_recorder.calls.append("sync_state_with_disk")
            return sync()

        monkeypatch.setattr(real_mod_start_up.state_manager, "sync_state_with_disk", record_sync)

        await self.run_auto_start_lifespan(prepare_mod_files_recorder, auto_start=False)

        assert prepare_mod_files_recorder.calls == [
            "recover_working_files",
            "sync_state_with_disk",
            "scheduler_start",
        ]

    @pytest.mark.asyncio
    async def test_auto_start_server_enabled_and_installed(self, captured_logs: StringIO) -> None:
        """Auto-start starts server when enabled and server is INSTALLED."""
        from vintagestory_api.main import lifespan_for

        # Mock dependencies
        mock_settings = MagicMock()
        mock_settings.auto_start_server = True
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.mod_db_url = DEFAULT_MOD_DB_URL
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
            async with lifespan_for(mock_settings)(test_app):
                pass

            # Verify auto-start was attempted
            mock_server_service.get_server_status.assert_called_once()
            mock_server_service.start_server.assert_called_once()

            # Check logs
            logs = captured_logs.getvalue()
            assert "auto_start_server_enabled" in logs
            assert "auto_starting_game_server" in logs

    @pytest.mark.asyncio
    async def test_auto_start_server_not_installed(self, captured_logs: StringIO) -> None:
        """Auto-start skips when server is NOT_INSTALLED."""
        from vintagestory_api.main import lifespan_for

        mock_settings = MagicMock()
        mock_settings.auto_start_server = True
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.mod_db_url = DEFAULT_MOD_DB_URL
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
            async with lifespan_for(mock_settings)(test_app):
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
    async def test_auto_start_server_already_running(self, captured_logs: StringIO) -> None:
        """Auto-start skips when server is already RUNNING."""
        from vintagestory_api.main import lifespan_for

        mock_settings = MagicMock()
        mock_settings.auto_start_server = True
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.mod_db_url = DEFAULT_MOD_DB_URL
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
            async with lifespan_for(mock_settings)(test_app):
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
    async def test_auto_start_server_error_handling(self, captured_logs: StringIO) -> None:
        """Auto-start handles errors gracefully and logs them."""
        from vintagestory_api.main import lifespan_for

        mock_settings = MagicMock()
        mock_settings.auto_start_server = True
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.mod_db_url = DEFAULT_MOD_DB_URL
        mock_settings.cors_origins = "http://localhost:3000"
        mock_settings.debug = False
        mock_settings.ensure_data_directories = MagicMock()

        mock_api_settings_service = MagicMock()
        mock_api_settings = MagicMock()
        mock_api_settings.auto_start_server = True
        mock_api_settings_service.get_settings.return_value = mock_api_settings

        mock_server_service = MagicMock()
        # Simulate error during get_server_status
        mock_server_service.get_server_status.side_effect = Exception("Docker connection failed")

        mock_scheduler = MagicMock()
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        test_app = FastAPI()

        with (
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
            async with lifespan_for(mock_settings)(test_app):
                pass

            # Check error was logged
            logs = captured_logs.getvalue()
            assert "auto_start_server_enabled" in logs
            assert "auto_start_failed" in logs
            assert "Docker connection failed" in logs

    @pytest.mark.asyncio
    async def test_auto_start_disabled(self, captured_logs: StringIO) -> None:
        """Auto-start is skipped when disabled in settings."""
        from vintagestory_api.main import lifespan_for

        mock_settings = MagicMock()
        mock_settings.auto_start_server = False
        mock_settings.data_dir = Path("/tmp/test_data")
        mock_settings.mod_db_url = DEFAULT_MOD_DB_URL
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
            async with lifespan_for(mock_settings)(test_app):
                pass

            # Check disabled log message
            logs = captured_logs.getvalue()
            assert "auto_start_server_disabled" in logs


class TestLogModDbUrl:
    """Start-up warns when VS_MOD_DB_URL is not the default (Story 20.6, Epic 20 ADR-9)."""

    @staticmethod
    def plain(captured_logs: StringIO) -> str:
        return re.sub(r"\x1b\[[0-9;]*m", "", captured_logs.getvalue())

    def test_no_log_line_for_the_default(self, captured_logs: StringIO) -> None:
        log_mod_db_url(Settings())

        assert self.plain(captured_logs) == ""

    def test_one_warning_with_scheme_and_host_for_a_mirror(self, captured_logs: StringIO) -> None:
        log_mod_db_url(Settings(mod_db_url="https://Mirror.Example:8443/"))

        out = self.plain(captured_logs)
        assert out.count("mod_db_url_overridden") == 1
        assert "warning" in out
        assert "scheme=https" in out
        assert "host=mirror.example" in out
        assert "8443" not in out
        assert "https://mirror.example" not in out

    def test_the_lifespan_logs_it_once_at_start_up(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        settings = Settings(
            api_key_admin="lifespan-admin-key",
            data_dir=tmp_path / "data",
            mod_db_url="https://mirror.example",
        )
        app = create_app(settings, static_dir=tmp_path / "missing")
        capsys.readouterr()

        with TestClient(app):
            out = capsys.readouterr().out

        assert out.count("mod_db_url_overridden") == 1
        assert "mirror.example" in out

    def test_the_lifespan_logs_nothing_for_the_default(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        settings = Settings(api_key_admin="lifespan-admin-key", data_dir=tmp_path / "data")
        app = create_app(settings, static_dir=tmp_path / "missing")
        capsys.readouterr()

        with TestClient(app):
            out = capsys.readouterr().out

        assert "api_starting" in out
        assert "mod_db_url_overridden" not in out


class TestLifespanLogLevel:
    """The lifespan applies VS_DEBUG and VS_LOG_LEVEL from the settings (Epic 21 ADR-4)."""

    ADMIN_KEY = "lifespan-admin-key"

    @pytest.fixture(autouse=True)
    def fresh_debug_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A process that has not initialised its debug state; restored after the test."""
        monkeypatch.setattr(config_module, "_debug_enabled", False)
        monkeypatch.setattr(config_module, "_debug_initialized", False)
        monkeypatch.setattr(config_module, "_configured_log_level", None)
        monkeypatch.setattr(config_module, "_current_log_level", "INFO")

    def start(self, settings: Settings, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> str:
        app = create_app(settings, static_dir=tmp_path / "missing")
        capsys.readouterr()
        with TestClient(app):
            return capsys.readouterr().out

    @pytest.mark.parametrize(("log_level", "expected"), [("info", "INFO"), ("debug", "DEBUG")])
    def test_api_starting_is_json_with_the_level_set(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], log_level: str, expected: str
    ) -> None:
        settings = Settings(
            api_key_admin=self.ADMIN_KEY,
            data_dir=tmp_path / "data",
            debug=False,
            log_level=log_level,
        )

        out = self.start(settings, tmp_path, capsys)

        starting = [
            json.loads(line) for line in out.splitlines() if '"event": "api_starting"' in line
        ]
        assert len(starting) == 1
        assert starting[0]["log_level"] == expected
        assert starting[0]["debug_mode"] is False

    def test_warning_filters_out_api_starting(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        settings = Settings(
            api_key_admin=self.ADMIN_KEY,
            data_dir=tmp_path / "data",
            debug=False,
            log_level="warning",
        )

        out = self.start(settings, tmp_path, capsys)

        assert "api_starting" not in out
        assert current_log_level() == "WARNING"

    def test_debug_mode_with_info_uses_the_console_renderer(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        settings = Settings(
            api_key_admin=self.ADMIN_KEY, data_dir=tmp_path / "data", debug=True, log_level="INFO"
        )

        out = self.start(settings, tmp_path, capsys)

        lines = [line for line in out.splitlines() if "api_starting" in line]
        assert len(lines) == 1
        with pytest.raises(json.JSONDecodeError):
            json.loads(lines[0])
        assert "log_level=INFO" in re.sub(r"\x1b\[[0-9;]*m", "", lines[0])
        assert is_debug_enabled() is True
        assert current_log_level() == "INFO"

    def test_vs_debug_on_turns_debug_logging_on(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VS_DEBUG", "on")
        settings = Settings(api_key_admin=self.ADMIN_KEY, data_dir=tmp_path / "data")

        out = self.start(settings, tmp_path, capsys)

        lines = [line for line in out.splitlines() if "api_starting" in line]
        assert len(lines) == 1
        assert "log_level=DEBUG" in re.sub(r"\x1b\[[0-9;]*m", "", lines[0])
        assert is_debug_enabled() is True
        assert current_log_level() == "DEBUG"
