"""E2E tests for health endpoints.

These tests verify the application health endpoints are accessible
via browser automation against the running Docker application.
"""

import re

from playwright.sync_api import Page, expect


def test_healthz_endpoint_returns_ok(page: Page, api_base_url: str) -> None:
    """Verify /healthz endpoint returns health status via browser."""
    page.goto(f"{api_base_url}/healthz")

    # The response should be JSON with status field
    # Playwright displays raw JSON in the page body
    expect(page.locator("body")).to_contain_text("ok")


def test_health_endpoint_returns_detailed_status(page: Page, api_base_url: str) -> None:
    """Verify /health endpoint returns detailed health status."""
    page.goto(f"{api_base_url}/health")

    # Should contain status and version information
    body = page.locator("body")
    expect(body).to_contain_text("status")
    expect(body).to_contain_text("version")


def test_web_ui_loads_successfully(page: Page, base_url: str) -> None:
    """Verify the web UI loads and shows expected title."""
    page.goto(base_url)

    # The page should have a title containing VintageStory or similar
    expect(page).to_have_title(re.compile(r"VintageStory|VS Server", re.IGNORECASE))


def test_api_root_returns_info(page: Page, api_base_url: str) -> None:
    """Verify API root endpoint returns API information."""
    page.goto(api_base_url)

    # API root should return service info
    body = page.locator("body")
    # Check for typical API info fields
    expect(body).to_contain_text("vintagestory")
