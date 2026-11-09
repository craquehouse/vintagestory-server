"""Tests for frontend file serving, run against the real route registration."""

from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.main import register_frontend

INDEX = "<html>SPA index</html>"
PRIVATE = "outside the static directory"


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    root = tmp_path / "static"
    (root / "assets").mkdir(parents=True)
    (root / "nested").mkdir()
    (root / "index.html").write_text(INDEX)
    (root / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    (root / "nested" / "page.txt").write_text("nested file")
    (root / "assets" / "main.js").write_text("console.log('app');")

    (tmp_path / "private.txt").write_text(PRIVATE)
    sibling = tmp_path / "static-private"
    sibling.mkdir()
    (sibling / "private.txt").write_text(PRIVATE)
    return root


@pytest.fixture
def client(static_dir: Path) -> TestClient:
    target = FastAPI()
    register_frontend(target, static_dir)
    return TestClient(target)


def assert_serves_index(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.text == INDEX


class TestFrontendFiles:
    def test_serves_file_in_static_dir(self, client: TestClient) -> None:
        response = client.get("/favicon.ico")

        assert response.status_code == 200
        assert response.content == b"\x00\x00\x01\x00"

    def test_serves_file_in_subdirectory(self, client: TestClient) -> None:
        response = client.get("/nested/page.txt")

        assert response.status_code == 200
        assert response.text == "nested file"

    def test_serves_mounted_assets(self, client: TestClient) -> None:
        response = client.get("/assets/main.js")

        assert response.status_code == 200
        assert "console.log('app');" in response.text

    @pytest.mark.parametrize("path", ["/", "/dashboard", "/game-server/mods/browse"])
    def test_client_routes_fall_back_to_index(self, client: TestClient, path: str) -> None:
        assert_serves_index(client, path)

    def test_directory_falls_back_to_index(self, client: TestClient) -> None:
        assert_serves_index(client, "/nested")

    def test_assets_are_optional(self, tmp_path: Path) -> None:
        root = tmp_path / "bare"
        root.mkdir()
        (root / "index.html").write_text(INDEX)
        target = FastAPI()
        register_frontend(target, root)

        assert_serves_index(TestClient(target), "/dashboard")


class TestFrontendContainment:
    @pytest.mark.parametrize(
        "path",
        [
            "/..%2Fprivate.txt",
            "/nested%2F..%2F..%2Fprivate.txt",
            "/..%2Fstatic-private%2Fprivate.txt",
        ],
    )
    def test_relative_paths_cannot_leave_static_dir(self, client: TestClient, path: str) -> None:
        assert_serves_index(client, path)

    def test_absolute_paths_cannot_leave_static_dir(
        self, client: TestClient, static_dir: Path
    ) -> None:
        private = static_dir.parent / "private.txt"

        assert_serves_index(client, f"/{quote(str(private), safe='')}")

    def test_symlinks_cannot_leave_static_dir(self, client: TestClient, static_dir: Path) -> None:
        (static_dir / "link.txt").symlink_to(static_dir.parent / "private.txt")

        assert_serves_index(client, "/link.txt")

    @pytest.mark.parametrize("path", ["/bad%00name", "/" + "a" * 5000])
    def test_invalid_paths_fall_back_to_index(self, client: TestClient, path: str) -> None:
        assert_serves_index(client, path)
