"""The API documentation pages are served only with VS_DEBUG on (Story 19.3, Epic 19 ADR-7)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vintagestory_api import __version__
from vintagestory_api.config import Settings
from vintagestory_api.main import create_app

DOC_PATHS = ["/docs", "/redoc", "/openapi.json"]
INDEX = b"<html>SPA index</html>"


def make_client(tmp_path: Path, *, debug: bool, frontend: bool) -> TestClient:
    """An app from the factory; no `with` block, so the lifespan never runs."""
    static_dir = tmp_path / "static"
    if frontend:
        static_dir.mkdir()
        (static_dir / "index.html").write_bytes(INDEX)
    settings = Settings(api_key_admin="docs-admin", debug=debug, data_dir=tmp_path / "data")
    return TestClient(create_app(settings, static_dir=static_dir))


class TestWithoutFrontend:
    def test_debug_on_serves_the_docs(self, tmp_path: Path) -> None:
        client = make_client(tmp_path, debug=True, frontend=False)

        for path in ("/docs", "/redoc"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")

        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        assert schema.headers["content-type"] == "application/json"
        assert schema.json()["info"]["version"] == __version__

    @pytest.mark.parametrize("path", [*DOC_PATHS, "/docs/oauth2-redirect"])
    def test_debug_off_serves_none_of_them(self, tmp_path: Path, path: str) -> None:
        client = make_client(tmp_path, debug=False, frontend=False)

        assert client.get(path).status_code == 404


class TestWithFrontend:
    @pytest.mark.parametrize("path", ["/docs", "/redoc"])
    def test_debug_off_answers_with_the_web_ui_page(self, tmp_path: Path, path: str) -> None:
        client = make_client(tmp_path, debug=False, frontend=True)

        response = client.get(path)

        assert response.status_code == 200
        assert response.content == INDEX
        assert "content-security-policy" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

    def test_debug_off_schema_is_a_missing_file(self, tmp_path: Path) -> None:
        """/openapi.json names a file, so without the schema it is 404 (Epic 24 ADR-2)."""
        client = make_client(tmp_path, debug=False, frontend=True)

        response = client.get("/openapi.json")

        assert response.status_code == 404
        assert response.content != INDEX
        assert "content-security-policy" in response.headers

    def test_debug_on_serves_the_docs_without_the_policy(self, tmp_path: Path) -> None:
        client = make_client(tmp_path, debug=True, frontend=True)

        docs = client.get("/docs")
        assert docs.status_code == 200
        assert "swagger-ui" in docs.text
        assert "content-security-policy" not in docs.headers
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").json()["info"]["version"] == __version__

        assert "content-security-policy" in client.get("/").headers
