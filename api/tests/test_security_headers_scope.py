"""The Content-Security-Policy is on the web UI's pages only (Story 19.3, AC 2)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import create_app
from vintagestory_api.middleware.auth import get_settings

ADMIN_KEY = "scope-admin-KEY-1"
POLICY_HEADERS = ("content-security-policy", "content-security-policy-report-only")


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>SPA index</html>")
    settings = Settings(api_key_admin=ADMIN_KEY, debug=False, data_dir=tmp_path / "data")
    app = create_app(settings, static_dir=static_dir)
    # Request authentication reads the cached settings dependency
    app.dependency_overrides[get_settings] = lambda: settings
    # No `with` block: the lifespan does not run, so nothing is written under dev/
    return TestClient(app)


@pytest.mark.parametrize(
    ("path", "headers", "status"),
    [
        ("/healthz", {}, 200),
        ("/readyz", {}, 200),
        ("/api/v1alpha1/auth/me", {"X-API-Key": ADMIN_KEY}, 200),
        ("/api/v1alpha1/auth/me", {}, 401),
    ],
    ids=["healthz", "readyz", "auth-me-with-key", "auth-me-without-key"],
)
def test_api_and_health_responses_have_no_policy(
    client: TestClient, path: str, headers: dict[str, str], status: int
) -> None:
    response = client.get(path, headers=headers)

    assert response.status_code == status
    assert not any(header in response.headers for header in POLICY_HEADERS)
    assert "x-frame-options" not in response.headers


def test_web_ui_page_on_the_same_app_has_the_policy(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "content-security-policy" in response.headers
    assert response.headers["x-frame-options"] == "DENY"
