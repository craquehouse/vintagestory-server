"""Pytest configuration and fixtures."""

import os
import sys
from collections.abc import Generator
from io import StringIO

# Set VS_DEBUG=true for all tests to expose test_rbac endpoints
# This ensures RBAC integration tests work regardless of environment
# IMPORTANT: Must be set BEFORE importing app, as app initializes once
os.environ["VS_DEBUG"] = "true"
# mise loads a developer's .env (.mise.toml); a mirror address there must not reach tests
# that mock https://mods.vintagestory.at/... (Epic 20 ADR-9)
os.environ.pop("VS_MOD_DB_URL", None)
# Nor may a developer's VS_LOG_LEVEL change any test's result (Epic 21 ADR-4)
os.environ.pop("VS_LOG_LEVEL", None)

import pytest
import structlog
from fastapi.testclient import TestClient

import vintagestory_api.main as main_module
from vintagestory_api.main import app

# Shared test API keys - use these instead of defining locally in test files
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


@pytest.fixture(autouse=True)
def reset_structlog_for_tests() -> Generator[None]:
    """Reset structlog configuration before each test for consistent behavior.

    This autouse fixture ensures that structlog is configured to write to stdout
    before each test runs. This is needed because Story 9.4's runtime debug
    toggle (FR48) uses cache_logger_on_first_use=False, which can cause
    inconsistent logger behavior when tests modify the configuration.

    Without this fixture, tests that check capsys.out for log output may fail
    intermittently depending on test ordering.
    """
    # Configure structlog to write to stdout for capsys capture
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )

    yield

    # No cleanup needed - next test will reconfigure


class PrepareModFilesRecorder:
    """Stands in for `prepare_mod_files` in the API's lifespan (Story 19.4).

    Appends "prepare_mod_files" to `calls` on each call; raises `error` when it is set.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.error: Exception | None = None

    def __call__(self) -> None:
        self.calls.append("prepare_mod_files")
        if self.error is not None:
            raise self.error


@pytest.fixture(autouse=True)
def prepare_mod_files_recorder(monkeypatch: pytest.MonkeyPatch) -> PrepareModFilesRecorder:
    """Keep every lifespan a test runs away from the real mods directory, state and cache.

    `just test-api` sets VS_DATA_DIR to the dev stack's data (`dev/`); the real start-up
    work renames and deletes files there and syncs the mod state with that mods directory
    (Story 19.5), which writes `state/mods.json`. Tests of `prepare_mod_files` itself
    import it from `services.mods` and give it a temporary service.
    """
    recorder = PrepareModFilesRecorder()
    monkeypatch.setattr(main_module, "prepare_mod_files", recorder)
    return recorder


class ReapplyAtApiStartRecorder:
    """Stands in for `reapply_pending_config_edits_at_api_start` in the lifespan (Story 22.7).

    Appends "reapply_pending_config_edits_at_api_start" to `calls` on each call; raises
    `error` when it is set. A test that checks the order with `prepare_mod_files` gives both
    recorders one list.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.error: Exception | None = None

    def __call__(self) -> None:
        self.calls.append("reapply_pending_config_edits_at_api_start")
        if self.error is not None:
            raise self.error


@pytest.fixture(autouse=True)
def reapply_at_api_start_recorder(monkeypatch: pytest.MonkeyPatch) -> ReapplyAtApiStartRecorder:
    """Keep every lifespan a test runs away from the real state and serverconfig.json.

    `just test-api` sets VS_DATA_DIR to the dev stack's data (`dev/`); the real start-up
    step builds the `ServerService` singleton with `Settings()`, reads
    `dev/vsmanager/state/pending-config-edits.json` and could write
    `dev/serverdata/serverconfig.json`. Tests of the real step put it back on `main_module`
    and give it a temporary service.
    """
    recorder = ReapplyAtApiStartRecorder()
    monkeypatch.setattr(main_module, "reapply_pending_config_edits_at_api_start", recorder)
    return recorder


class StopGameAtShutdownRecorder:
    """Stands in for `stop_game_server_for_api_shutdown` in the lifespan (Story 22.8).

    Appends "stop_game_server_for_api_shutdown" to `calls` on each call; raises `error`
    when it is set. A test that checks the order with other shutdown steps gives them
    this list.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.error: Exception | None = None

    async def __call__(self) -> None:
        self.calls.append("stop_game_server_for_api_shutdown")
        if self.error is not None:
            raise self.error


@pytest.fixture(autouse=True)
def stop_game_at_shutdown_recorder(monkeypatch: pytest.MonkeyPatch) -> StopGameAtShutdownRecorder:
    """Keep every lifespan a test runs away from a real game process and its files.

    `just test-api` sets VS_DATA_DIR to the dev stack's data (`dev/`); the real shutdown
    step stops the `ServerService` singleton another test may have built with `Settings()`,
    which could write `dev/serverdata/serverconfig.json` and the state file. Tests of the
    real step put it back on `main_module` and give it a temporary service.
    """
    recorder = StopGameAtShutdownRecorder()
    monkeypatch.setattr(main_module, "stop_game_server_for_api_shutdown", recorder)
    return recorder


async def _no_op_disk_cleanup() -> None:
    """Stands in for the daily disk cleanup job (Story 22.4)."""


@pytest.fixture(autouse=True)
def no_real_disk_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every registered disk cleanup job away from the real serverdata (Story 22.4).

    `just test-api` sets VS_DATA_DIR to the dev stack's data (`dev/`); a registered
    `disk_cleanup` job that fired at 03:00 during a test run would delete backups in
    `dev/serverdata`. `register_disk_cleanup` imports the job function lazily,
    so every registration in every test (lifespan clients, `register_default_jobs`,
    `reschedule_client`) gets this no-op. The job's own tests import the real function
    before this fixture runs and give it a temporary data directory.
    """
    monkeypatch.setattr("vintagestory_api.jobs.disk_cleanup.disk_cleanup", _no_op_disk_cleanup)


@pytest.fixture
def client() -> TestClient:
    """Create a test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Headers with admin API key for authenticated requests."""
    return {"X-API-Key": TEST_ADMIN_KEY}


@pytest.fixture
def monitor_headers() -> dict[str, str]:
    """Headers with monitor API key (read-only, non-admin) for authenticated requests."""
    return {"X-API-Key": TEST_MONITOR_KEY}


@pytest.fixture
def captured_logs() -> Generator[StringIO]:
    """Configure structlog to capture logs to a StringIO for testing.

    This fixture ensures consistent log capture across tests, regardless of
    global structlog configuration state (which can vary due to runtime
    reconfiguration from Story 9.4 FR48).

    Usage:
        def test_logging(captured_logs: StringIO) -> None:
            logger = structlog.get_logger()
            logger.info("test_event", key="value")
            assert "test_event" in captured_logs.getvalue()
    """
    output = StringIO()

    # Configure structlog with explicit output for this test
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output),
        cache_logger_on_first_use=False,
    )

    yield output

    # Note: We don't restore original config as tests run in isolation
    # and conftest.py always resets for next test
