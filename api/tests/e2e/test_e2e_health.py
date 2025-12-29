"""E2E tests for health endpoints.

These tests verify the application health endpoints are accessible
against the running Docker application.

Note: Health endpoints are at root level (K8s convention), not under /api/v1alpha1.
API endpoint tests use Playwright's request context (direct HTTP) rather than
browser navigation, since the web server serves the SPA for browser requests.
"""

import re

from playwright.sync_api import Page, expect


def test_healthz_endpoint_returns_ok(page: Page, base_url: str) -> None:
    """Verify /healthz liveness probe returns health status."""
    response = page.request.get(f"{base_url}/healthz")

    assert response.ok
    data = response.json()
    assert data.get("status") == "ok"
    assert "data" in data
    assert data["data"].get("api") == "healthy"


def test_readyz_endpoint_returns_ready(page: Page, base_url: str) -> None:
    """Verify /readyz readiness probe returns ready status."""
    response = page.request.get(f"{base_url}/readyz")

    assert response.ok
    data = response.json()
    assert data.get("status") == "ok"
    assert data["data"].get("ready") is True


def test_web_ui_loads_successfully(page: Page, base_url: str) -> None:
    """Verify the web UI loads and shows expected title."""
    page.goto(base_url)

    # The page should have a title containing VintageStory or similar
    expect(page).to_have_title(re.compile(r"VintageStory|VS Server", re.IGNORECASE))
