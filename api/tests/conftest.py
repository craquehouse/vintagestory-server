"""Pytest configuration and fixtures."""

import os
import sys
from collections.abc import Generator
from io import StringIO

# Set VS_DEBUG=true for all tests to expose test_rbac endpoints
# This ensures RBAC integration tests work regardless of environment
# IMPORTANT: Must be set BEFORE importing app, as app initializes once
os.environ["VS_DEBUG"] = "true"

import pytest
import structlog
from fastapi.testclient import TestClient

from vintagestory_api.main import app


@pytest.fixture(autouse=True)
def reset_structlog_for_tests() -> Generator[None, None, None]:
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


@pytest.fixture
def client() -> TestClient:
    """Create a test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def captured_logs() -> Generator[StringIO, None, None]:
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
