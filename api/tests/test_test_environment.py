"""Tests for the environment the API tests run in (Story 24.1, Epic 24 ADR-8)."""

import os
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent


def _admin_key_after_conftest(environ: dict[str, str]) -> str:
    """Import conftest.py in a fresh interpreter and return the admin key it leaves."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, conftest; print(os.environ['VS_API_KEY_ADMIN'])",
        ],
        cwd=TESTS_DIR,
        env=environ,
        capture_output=True,
        text=True,
        # Under pytest-timeout's 10 s (pyproject.toml), so this guard can fire first
        timeout=8,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    # The app logs at import; the printed key is the last line
    return result.stdout.strip().splitlines()[-1]


def _environ_without_admin_key() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != "VS_API_KEY_ADMIN"}


def test_conftest_sets_a_placeholder_admin_key_when_none_is_set() -> None:
    """A fresh clone without .env imports the app with a non-empty key (VSS-uhek)."""
    key = _admin_key_after_conftest(_environ_without_admin_key())

    assert key == "test-placeholder-admin-key"


def test_conftest_keeps_an_admin_key_that_is_already_set() -> None:
    """A key from .env (through mise) or CI wins over the placeholder."""
    environ = _environ_without_admin_key() | {"VS_API_KEY_ADMIN": "from-dot-env"}

    assert _admin_key_after_conftest(environ) == "from-dot-env"
