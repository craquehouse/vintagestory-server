"""Tests for the manager version (Story 15.1, Epic 15 ADR-1)."""

import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from vintagestory_api import __version__

API_ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    with (API_ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def test_version_comes_from_pyproject() -> None:
    assert __version__ == _pyproject_version()


def test_openapi_reports_version(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["version"] == __version__


def test_healthz_reports_version(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["data"]["version"] == __version__


def test_no_source_file_hard_codes_the_version() -> None:
    literal = f'"{_pyproject_version()}"'
    offenders = [
        str(path.relative_to(API_ROOT))
        for path in (API_ROOT / "src").rglob("*.py")
        if literal in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
