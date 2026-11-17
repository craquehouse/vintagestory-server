"""The app factory builds the application from the settings it is given (Epic 19 ADR-5)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import create_app

ADMIN_KEY = "factory-admin-KEY-1"
MONITOR_KEY = "factory-monitor-KEY-2"


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    root = tmp_path / "static"
    root.mkdir()
    (root / "index.html").write_text("<html>SPA index</html>")
    return root


def make_settings(tmp_path: Path, web_key: str | None) -> Settings:
    """Settings with made-up keys whose data directory is under tmp_path, never dev/."""
    return Settings(
        api_key_admin=ADMIN_KEY,
        api_key_monitor=MONITOR_KEY,
        api_key=web_key,
        data_dir=tmp_path / "data",
    )


class TestCreateApp:
    """create_app(settings) starts and serves /config.js with the settings it was given."""

    def test_app_starts_with_the_settings_it_was_given(
        self, tmp_path: Path, static_dir: Path
    ) -> None:
        app = create_app(make_settings(tmp_path, "given-key"), static_dir=static_dir)

        with TestClient(app) as client:
            assert (tmp_path / "data" / "vsmanager" / "state").is_dir()
            assert client.get("/healthz").status_code == 200
            assert client.get("/readyz").status_code == 200

    def test_config_js_comes_from_the_given_settings(
        self, tmp_path: Path, static_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VS_API_KEY", "env-key")
        app = create_app(make_settings(tmp_path, "given-key"), static_dir=static_dir)

        with TestClient(app) as client:
            body = client.get("/config.js").text

        assert "given-key" in body
        assert "env-key" not in body

    def test_no_frontend_without_a_static_directory(self, tmp_path: Path) -> None:
        app = create_app(make_settings(tmp_path, "given-key"), static_dir=tmp_path / "missing")

        with TestClient(app) as client:
            assert client.get("/config.js").status_code == 404
            assert client.get("/healthz").status_code == 200


WEB_KEY_EVENTS = ("web_api_key_not_set", "web_api_key_is_admin_key", "web_api_key_matches_no_role")

# VS_API_KEY -> (what /config.js serves, the one warning logged at start-up or None)
WEB_KEY_STATES: list[tuple[str | None, str, str | None]] = [
    (None, "", "web_api_key_not_set"),
    ("  ", "", "web_api_key_not_set"),
    (ADMIN_KEY, ADMIN_KEY, "web_api_key_is_admin_key"),
    (MONITOR_KEY, MONITOR_KEY, None),
    ("other-key", "other-key", "web_api_key_matches_no_role"),
]
STATE_IDS = ["unset", "blank", "admin", "monitor", "no_role"]


class TestWebApiKeyStates:
    """Each VS_API_KEY state: what /config.js serves and what start-up logs (AC 1, 4, 5, 8)."""

    @pytest.mark.parametrize(("web_key", "served", "event"), WEB_KEY_STATES, ids=STATE_IDS)
    def test_config_js_and_probes(
        self,
        tmp_path: Path,
        static_dir: Path,
        web_key: str | None,
        served: str,
        event: str | None,
    ) -> None:
        app = create_app(make_settings(tmp_path, web_key), static_dir=static_dir)

        with TestClient(app) as client:
            response = client.get("/config.js")
            assert client.get("/healthz").status_code == 200
            assert client.get("/readyz").status_code == 200

        assert response.status_code == 200
        assert response.text == f'window.__VSM_CONFIG__ = {{"apiKey": "{served}"}};\n'
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["cross-origin-resource-policy"] == "same-origin"
        assert response.headers["x-content-type-options"] == "nosniff"

    @pytest.mark.parametrize(("web_key", "served", "event"), WEB_KEY_STATES, ids=STATE_IDS)
    def test_start_up_log(
        self,
        tmp_path: Path,
        static_dir: Path,
        capsys: pytest.CaptureFixture[str],
        web_key: str | None,
        served: str,
        event: str | None,
    ) -> None:
        app = create_app(make_settings(tmp_path, web_key), static_dir=static_dir)
        capsys.readouterr()

        with TestClient(app):
            out = capsys.readouterr().out

        assert "api_starting" in out
        for name in WEB_KEY_EVENTS:
            assert (name in out) is (name == event), name
        for key in (ADMIN_KEY, MONITOR_KEY, "other-key"):
            assert key not in out
