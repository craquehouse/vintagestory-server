"""The RBAC test routes exist only when the app is built with debug on.

Each test builds its app from the factory with explicit settings, so the result does
not depend on VS_DEBUG in the environment (Story 19.3).
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import create_app
from vintagestory_api.middleware.auth import get_settings

ADMIN_KEY = "gating-admin-KEY-1"


def make_app(tmp_path: Path, *, debug: bool) -> FastAPI:
    settings = Settings(api_key_admin=ADMIN_KEY, debug=debug, data_dir=tmp_path / "data")
    app = create_app(settings, static_dir=tmp_path / "no-frontend")
    # Request authentication reads the cached settings dependency
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1alpha1/test/read"),
        ("POST", "/api/v1alpha1/test/write"),
        ("GET", "/api/v1alpha1/test/console"),
    ],
)
class TestRbacTestRoutes:
    def test_exist_with_debug_on(self, tmp_path: Path, method: str, path: str) -> None:
        client = TestClient(make_app(tmp_path, debug=True))

        assert client.request(method, path).status_code == 401
        assert client.request(method, path, headers={"X-API-Key": ADMIN_KEY}).status_code == 200

    def test_absent_with_debug_off(self, tmp_path: Path, method: str, path: str) -> None:
        client = TestClient(make_app(tmp_path, debug=False))

        assert client.request(method, path).status_code == 404
        assert client.request(method, path, headers={"X-API-Key": ADMIN_KEY}).status_code == 404


def test_auth_endpoints_still_work_with_debug_off(tmp_path: Path) -> None:
    client = TestClient(make_app(tmp_path, debug=False))

    assert client.get("/healthz").status_code == 200
    assert client.get("/api/v1alpha1/auth/me", headers={"X-API-Key": ADMIN_KEY}).status_code == 200
    assert client.get("/api/v1alpha1/auth/me").status_code == 401
