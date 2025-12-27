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
        settings = Settings()
        assert settings.data_dir == Path("/data")

    def test_data_dir_from_env(self) -> None:
        """Data directory can be configured via environment variable."""
        with patch.dict(os.environ, {"VS_DATA_DIR": "/custom/path"}):
            settings = Settings()
            assert settings.data_dir == Path("/custom/path")

    def test_state_dir_property(self) -> None:
        """State directory is a subdirectory of data_dir."""
        settings = Settings()
        assert settings.state_dir == settings.data_dir / "state"

    def test_server_dir_property(self) -> None:
        """Server directory is a subdirectory of data_dir."""
        settings = Settings()
        assert settings.server_dir == settings.data_dir / "server"

    def test_mods_dir_property(self) -> None:
        """Mods directory is a subdirectory of data_dir."""
        settings = Settings()
        assert settings.mods_dir == settings.data_dir / "mods"

    def test_config_dir_property(self) -> None:
        """Config directory is a subdirectory of data_dir."""
        settings = Settings()
        assert settings.config_dir == settings.data_dir / "config"

    def test_logs_dir_property(self) -> None:
        """Logs directory is a subdirectory of data_dir."""
        settings = Settings()
        assert settings.logs_dir == settings.data_dir / "logs"

    def test_backups_dir_property(self) -> None:
        """Backups directory is a subdirectory of data_dir."""
        settings = Settings()
        assert settings.backups_dir == settings.data_dir / "backups"


class TestEnsureDataDirectories:
    """Tests for ensure_data_directories method."""

    def test_creates_all_directories(self, tmp_path: Path) -> None:
        """ensure_data_directories creates all required subdirectories."""
        with patch.dict(os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}):
            settings = Settings()
            settings.ensure_data_directories()

            assert settings.state_dir.exists()
            assert settings.server_dir.exists()
            assert settings.mods_dir.exists()
            assert settings.config_dir.exists()
            assert settings.logs_dir.exists()
            assert settings.backups_dir.exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        """Calling ensure_data_directories multiple times is safe."""
        with patch.dict(os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}):
            settings = Settings()
            settings.ensure_data_directories()
            settings.ensure_data_directories()  # Should not raise

            assert settings.state_dir.exists()

    def test_creates_nested_directories(self, tmp_path: Path) -> None:
        """Creates directories even if parent doesn't exist."""
        nested_path = tmp_path / "deeply" / "nested" / "data"
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(nested_path), "VS_API_KEY_ADMIN": "test-key"}
        ):
            settings = Settings()
            settings.ensure_data_directories()

            assert settings.state_dir.exists()
            assert settings.state_dir.parent == nested_path


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
            assert settings.state_dir.exists()

    def test_allows_none_for_optional_api_key_monitor(self, tmp_path: Path) -> None:
        """api_key_monitor can be None (optional)."""
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "valid-key"}
        ):
            settings = Settings(api_key_monitor=None)
            settings.ensure_data_directories()  # Should not raise
            assert settings.state_dir.exists()
