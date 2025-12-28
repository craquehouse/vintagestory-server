"""Tests for application configuration."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from vintagestory_api.config import Settings


class TestDataDirectories:
    """Tests for data directory configuration."""

    def test_default_data_dir(self) -> None:
        """Default data directory is /data."""
        # Clear any VS_DATA_DIR from environment to test the default
        with patch.dict(os.environ, {"VS_DATA_DIR": ""}, clear=False):
            # Remove the key if it exists
            env = os.environ.copy()
            env.pop("VS_DATA_DIR", None)
            with patch.dict(os.environ, env, clear=True):
                settings = Settings()
                assert settings.data_dir == Path("/data")

    def test_data_dir_from_env(self) -> None:
        """Data directory can be configured via environment variable."""
        with patch.dict(os.environ, {"VS_DATA_DIR": "/custom/path"}):
            settings = Settings()
            assert settings.data_dir == Path("/custom/path")

    def test_server_dir_property(self) -> None:
        """Server directory is a subdirectory of data_dir."""
        settings = Settings()
        assert settings.server_dir == settings.data_dir / "server"

    def test_serverdata_dir_property(self) -> None:
        """Serverdata directory is a subdirectory of data_dir."""
        settings = Settings()
        assert settings.serverdata_dir == settings.data_dir / "serverdata"

    def test_vsmanager_dir_property(self) -> None:
        """Vsmanager directory is a subdirectory of data_dir."""
        settings = Settings()
        assert settings.vsmanager_dir == settings.data_dir / "vsmanager"


class TestEnsureDataDirectories:
    """Tests for ensure_data_directories method."""

    def test_creates_all_directories(self, tmp_path: Path) -> None:
        """ensure_data_directories creates all required subdirectories."""
        with patch.dict(os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}):
            settings = Settings()
            settings.ensure_data_directories()

            assert settings.server_dir.exists()
            assert settings.serverdata_dir.exists()
            assert settings.vsmanager_dir.exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        """Calling ensure_data_directories multiple times is safe."""
        with patch.dict(os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}):
            settings = Settings()
            settings.ensure_data_directories()
            settings.ensure_data_directories()  # Should not raise

            assert settings.server_dir.exists()

    def test_creates_nested_directories(self, tmp_path: Path) -> None:
        """Creates directories even if parent doesn't exist."""
        nested_path = tmp_path / "deeply" / "nested" / "data"
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(nested_path), "VS_API_KEY_ADMIN": "test-key"}
        ):
            settings = Settings()
            settings.ensure_data_directories()

            assert settings.server_dir.exists()
            assert settings.server_dir.parent == nested_path


class TestApiKeyValidation:
    """Tests for API key security validation."""

    def test_rejects_empty_api_key_admin(self) -> None:
        """ensure_data_directories raises ValueError for empty api_key_admin."""
        settings = Settings(api_key_admin="")

        with pytest.raises(ValueError, match="VS_API_KEY_ADMIN must be set"):
            settings.ensure_data_directories()

    def test_rejects_whitespace_only_api_key_admin(self) -> None:
        """ensure_data_directories raises ValueError for whitespace-only api_key_admin."""
        settings = Settings(api_key_admin="   ")

        with pytest.raises(ValueError, match="VS_API_KEY_ADMIN must be set"):
            settings.ensure_data_directories()

    def test_accepts_valid_api_key_admin(self, tmp_path: Path) -> None:
        """ensure_data_directories accepts valid api_key_admin."""
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "valid-key"}
        ):
            settings = Settings()
            settings.ensure_data_directories()  # Should not raise
            assert settings.server_dir.exists()

    def test_allows_none_for_optional_api_key_monitor(self, tmp_path: Path) -> None:
        """api_key_monitor can be None (optional)."""
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "valid-key"}
        ):
            settings = Settings(api_key_monitor=None)
            settings.ensure_data_directories()  # Should not raise
            assert settings.server_dir.exists()
