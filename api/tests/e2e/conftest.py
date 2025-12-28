"""Playwright E2E test fixtures.

This module provides base fixtures for end-to-end testing with Playwright.
Tests in this directory verify the application works correctly when deployed
in Docker with all components running together.
"""

import os

import pytest
from playwright.sync_api import Page


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
    page.evaluate(f"localStorage.setItem('apiKey', '{api_key}')")
    return page
