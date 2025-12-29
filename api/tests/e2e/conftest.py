"""Playwright E2E test fixtures.

This module provides base fixtures for end-to-end testing with Playwright.
Tests in this directory verify the application works correctly when deployed
in Docker with all components running together.

pytest-playwright provides the following fixtures automatically:
- `page`: A new browser page for each test (function-scoped)
- `browser`: The browser instance (session-scoped)
- `context`: The browser context (function-scoped)
- `browser_name`: Name of the browser being used

See: https://playwright.dev/python/docs/test-runners#fixtures

Note: E2E tests are excluded from the main test run (just test-api) because
Playwright's sync_api uses its own event loop which conflicts with pytest-asyncio.
Run E2E tests separately with: just test-e2e-api
"""

import os
import socket
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Page


def _is_server_available(url: str, timeout: float = 0.5) -> bool:
    """Check if a server is accepting connections.

    Args:
        url: URL to check (host and port extracted).
        timeout: Connection timeout in seconds.

    Returns:
        True if server is accepting connections, False otherwise.
    """
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


@pytest.fixture(scope="session", autouse=True)
def require_docker_running(base_url: str) -> None:
    """Skip all E2E tests if Docker application is not running.

    This fixture runs automatically for all E2E tests and skips
    the entire test session if the application server is not reachable.

    Use `just test-e2e` after starting Docker with `just docker-start`.
    """
    if not _is_server_available(base_url):
        pytest.skip(
            f"E2E tests require Docker application running at {base_url}. "
            "Start with: just docker-start"
        )


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for the running application.

    Defaults to http://localhost:8080 which is the Docker Compose exposed port.
    Can be overridden via PLAYWRIGHT_BASE_URL environment variable.
    """
    return os.environ.get("PLAYWRIGHT_BASE_URL", "http://localhost:8080")


@pytest.fixture
def api_base_url(base_url: str) -> str:
    """Base URL for API endpoints."""
    return f"{base_url}/api/v1alpha1"


@pytest.fixture
def authenticated_page(page: Page, base_url: str) -> Page:
    """Page with API key in storage for authenticated requests.

    Note: For E2E tests that need authentication, the API key should be
    passed via environment variable. The web UI stores the API key in
    localStorage after login.
    """
    api_key = os.environ.get("VS_API_KEY", "test-api-key")
    page.goto(base_url)
    # Set API key in localStorage (web UI pattern)
    # Use JSON serialization to prevent XSS if api_key contains special characters
    page.evaluate("([key, value]) => localStorage.setItem(key, value)", ["apiKey", api_key])
    return page
