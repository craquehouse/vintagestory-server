"""GET /metrics at the root, open like /healthz (Story 22.2, Epic 22 ADR-3)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families
from structlog.testing import capture_logs

from vintagestory_api.config import Settings
from vintagestory_api.main import create_app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.prometheus_metrics import (
    GameServerCollector,
    build_registry,
    get_metrics_registry,
)
from vintagestory_api.services.server import ServerService

ADMIN_KEY = "metrics-admin-KEY-1"
SPA_TEXT = "<html>SPA index</html>"
POLICY_HEADERS = (
    "content-security-policy",
    "content-security-policy-report-only",
    "x-frame-options",
)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # get_server_status reads the disk space through Settings() from the environment
    monkeypatch.setattr("vintagestory_api.routers.health.get_disk_space_data", lambda: None)
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(SPA_TEXT)
    settings = Settings(api_key_admin=ADMIN_KEY, debug=False, data_dir=tmp_path / "data")
    service = ServerService(settings)
    state = PendingRestartState()
    registry = build_registry(
        GameServerCollector(server=lambda: service, restart_state=lambda: state)
    )
    app = create_app(settings, static_dir=static_dir)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_metrics_registry] = lambda: registry
    # No `with` block: the lifespan does not run, so nothing is written under dev/
    return TestClient(app)


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-API-Key": "not-the-key"}],
    ids=["no-key", "wrong-key"],
)
def test_metrics_answer_without_a_key(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get("/metrics", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    names = {
        sample.name
        for family in text_string_to_metric_families(response.text)
        for sample in family.samples
    }
    assert "vintagestory_server_up" in names
    assert "python_info" in names


def test_metrics_are_not_the_web_ui(client: TestClient) -> None:
    response = client.get("/metrics")

    assert SPA_TEXT not in response.text
    for header in POLICY_HEADERS:
        assert header not in response.headers


def test_other_paths_still_reach_the_web_ui(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.text == SPA_TEXT
    assert "content-security-policy" in response.headers


def test_post_is_not_allowed(client: TestClient) -> None:
    assert client.post("/metrics").status_code == 405


def test_a_scrape_logs_nothing_at_info_or_above(client: TestClient) -> None:
    with capture_logs() as logs:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert [entry for entry in logs if entry["log_level"] != "debug"] == []
