"""Tests for request context middleware.

Verifies that:
- Request ID is generated for each request
- Request ID appears in all log entries for that request
- Context is cleared between requests
"""

import re
import uuid
from io import StringIO

import pytest
import structlog
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import vintagestory_api.config as config_module
from vintagestory_api.middleware.request_context import RequestContextMiddleware


def extract_request_ids(logs: str) -> list[str]:
    """Extract request IDs from log output, handling ANSI escape codes.

    The ConsoleRenderer adds ANSI color codes around keys and values, so we need
    a pattern that handles both plain and colorized output.

    Example raw log line (actual escape sequences):
    \\x1b[36mrequest_id\\x1b[0m=\\x1b[35mfb7fe681-aea2-4309-a817-89fb462b57f9\\x1b[0m

    The pattern needs to handle:
    - Optional ANSI color code BEFORE the key name
    - The key name "request_id"
    - Optional ANSI reset AFTER the key name
    - The = sign
    - Optional ANSI color code BEFORE the value
    - The UUID value itself
    """
    # Match request_id with optional ANSI around key/value
    # Pattern: (opt ANSI) request_id (opt ANSI) = (opt ANSI) uuid
    uuid_pattern = (
        r"(?:\x1b\[[0-9;]*m)?"  # Optional ANSI before key
        r"request_id"  # Key name
        r"(?:\x1b\[[0-9;]*m)?"  # Optional ANSI after key (reset)
        r"="  # Equals sign
        r"(?:\x1b\[[0-9;]*m)?"  # Optional ANSI before value
        r"([a-f0-9-]{36})"  # UUID capture group
    )
    return re.findall(uuid_pattern, logs)


@pytest.fixture
def request_context_app(captured_logs: StringIO) -> tuple[TestClient, StringIO]:
    """Create a test FastAPI app with request context middleware.

    Uses the captured_logs fixture from conftest.py to ensure log capture
    is properly configured AFTER the autouse fixture runs.

    IMPORTANT: Sets _last_debug_state to True to prevent the middleware from
    calling configure_logging() which would override our test log capture.
    The middleware's reconfigure_logging_if_changed() only reconfigures when
    the state changes, so pre-setting it prevents reconfiguration.

    Args:
        captured_logs: StringIO buffer from conftest.py fixture

    Returns:
        Tuple of (TestClient, log output buffer)
    """
    # Pre-set the debug state to match VS_DEBUG=true (set in conftest.py)
    # This prevents middleware from calling configure_logging() which would
    # override our captured_logs configuration with stdout
    config_module._last_debug_state = True  # pyright: ignore[reportPrivateUsage]

    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    logger = structlog.get_logger()

    @app.get("/test")
    async def test_endpoint(request: Request) -> dict[str, str]:
        logger.info("endpoint_called", endpoint="/test")
        return {"message": "ok"}

    @app.get("/multi-log")
    async def multi_log_endpoint(request: Request) -> dict[str, str]:
        logger.info("first_log", step=1)
        logger.info("second_log", step=2)
        logger.info("third_log", step=3)
        return {"message": "ok"}

    client = TestClient(app, raise_server_exceptions=False)
    return client, captured_logs


class TestRequestContextMiddleware:
    """Test suite for RequestContextMiddleware."""

    def test_request_id_is_generated(
        self, request_context_app: tuple[TestClient, StringIO]
    ) -> None:
        """Verify that a request ID is generated for each request."""
        client, log_output = request_context_app

        response = client.get("/test")

        assert response.status_code == 200

        logs = log_output.getvalue()
        matches = extract_request_ids(logs)

        assert len(matches) >= 1, f"Expected request_id in logs, got: {logs}"
        # Verify it's a valid UUID
        uuid.UUID(matches[0])

    def test_request_id_consistent_across_logs(
        self, request_context_app: tuple[TestClient, StringIO]
    ) -> None:
        """Verify that the same request ID appears in all logs for a single request."""
        client, log_output = request_context_app

        response = client.get("/multi-log")

        assert response.status_code == 200

        logs = log_output.getvalue()
        matches = extract_request_ids(logs)

        # Should have multiple log entries with the same request_id
        assert len(matches) >= 3, (
            f"Expected at least 3 request_ids in logs, got {len(matches)}: {logs}"
        )
        # All request_ids should be the same
        assert len(set(matches)) == 1, f"Expected all request_ids to match, got: {set(matches)}"

    def test_different_requests_have_different_ids(
        self, request_context_app: tuple[TestClient, StringIO]
    ) -> None:
        """Verify that different requests get different IDs."""
        client, log_output = request_context_app

        client.get("/test")
        first_logs = log_output.getvalue()

        log_output.truncate(0)
        log_output.seek(0)

        client.get("/test")
        second_logs = log_output.getvalue()

        first_ids = extract_request_ids(first_logs)
        second_ids = extract_request_ids(second_logs)

        assert len(first_ids) >= 1
        assert len(second_ids) >= 1
        assert first_ids[0] != second_ids[0], "Different requests should have different IDs"

    def test_context_cleared_between_requests(
        self, request_context_app: tuple[TestClient, StringIO]
    ) -> None:
        """Verify that context vars are cleared between requests."""
        client, log_output = request_context_app

        # First request
        client.get("/test")

        # Clear log output
        log_output.truncate(0)
        log_output.seek(0)

        # Second request - should only have new request_id
        client.get("/test")
        logs = log_output.getvalue()

        matches = extract_request_ids(logs)

        # All IDs in second request should be the same (not mixed with first)
        unique_ids = set(matches)
        assert len(unique_ids) == 1, f"Expected single request_id per request, got: {unique_ids}"


class TestRequestContextMiddlewareIntegration:
    """Integration tests verifying middleware works with logging infrastructure."""

    def test_request_id_format_is_uuid4(
        self, request_context_app: tuple[TestClient, StringIO]
    ) -> None:
        """Verify request ID follows UUID4 format."""
        client, log_output = request_context_app

        client.get("/test")

        logs = log_output.getvalue()
        matches = extract_request_ids(logs)

        assert len(matches) >= 1
        # Validate UUID format
        parsed = uuid.UUID(matches[0])
        assert parsed.version == 4, f"Expected UUID v4, got version {parsed.version}"
