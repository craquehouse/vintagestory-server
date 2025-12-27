"""Pytest configuration and fixtures."""

import os

# Set VS_DEBUG=true for all tests to expose test_rbac endpoints
# This ensures RBAC integration tests work regardless of environment
# IMPORTANT: Must be set BEFORE importing app, as app initializes once
os.environ["VS_DEBUG"] = "true"

import pytest
from fastapi.testclient import TestClient

from vintagestory_api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for FastAPI app."""
    return TestClient(app)
