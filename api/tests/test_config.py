"""Tests for application configuration."""

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import structlog

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

    def test_cache_dir_property(self) -> None:
        """Cache directory is a subdirectory of vsmanager_dir."""
        settings = Settings()
        assert settings.cache_dir == settings.vsmanager_dir / "cache"

    def test_state_dir_property(self) -> None:
        """State directory is a subdirectory of vsmanager_dir."""
        settings = Settings()
        assert settings.state_dir == settings.vsmanager_dir / "state"

    def test_logs_dir_property(self) -> None:
        """Logs directory is a subdirectory of vsmanager_dir."""
        settings = Settings()
        assert settings.logs_dir == settings.vsmanager_dir / "logs"


class TestEnsureDataDirectories:
    """Tests for ensure_data_directories method."""

    def test_creates_all_directories(self, tmp_path: Path) -> None:
        """ensure_data_directories creates all required subdirectories including logs."""
        with patch.dict(os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}):
            settings = Settings()
            settings.ensure_data_directories()

            assert settings.server_dir.exists()
            assert settings.serverdata_dir.exists()
            assert settings.vsmanager_dir.exists()
            assert settings.cache_dir.exists()
            assert settings.state_dir.exists()
            assert settings.logs_dir.exists()

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


class TestDirectoryCreationLogging:
    """Tests for directory creation logging (Story 9.2 AC#2, AC#3)."""

    def test_logs_directory_created_event(self, tmp_path: Path) -> None:
        """When directories are created, logs directory_created event (AC#2).

        Verifies that all 6 directories are logged when created:
        server, serverdata, vsmanager, cache, state, logs.
        """
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}
        ):
            settings = Settings()

            # Capture logs
            log_events: list[dict[str, Any]] = []

            def capture_log(
                logger: Any, method_name: str, event_dict: dict[str, Any]
            ) -> dict[str, Any]:
                log_events.append(event_dict.copy())
                return event_dict

            # API-027: structlog type stubs incomplete - processors type mismatch
            structlog.configure(
                processors=[capture_log, structlog.dev.ConsoleRenderer()],  # type: ignore[list-item]
                wrapper_class=structlog.make_filtering_bound_logger(0),
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(),
                cache_logger_on_first_use=False,
            )

            settings.ensure_data_directories()

            # Verify directory_created events were logged for all 6 directories
            creation_events = [
                e for e in log_events if e.get("event") == "directory_created"
            ]
            assert len(creation_events) == 6, (
                f"Expected 6 directory_created events "
                f"(server, serverdata, vsmanager, cache, state, logs), "
                f"got {len(creation_events)}: {creation_events}"
            )

            # Verify each expected directory was logged
            logged_paths = {str(e.get("path", "")) for e in creation_events}
            expected_dirs = ["server", "serverdata", "vsmanager", "cache", "state", "logs"]
            for dir_name in expected_dirs:
                assert any(dir_name in path for path in logged_paths), (
                    f"Expected '{dir_name}' directory in logged paths, got: {logged_paths}"
                )

    def test_no_log_when_directories_exist(self, tmp_path: Path) -> None:
        """When directories already exist, no creation logs are emitted (AC#3)."""
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}
        ):
            settings = Settings()

            # First call creates directories
            settings.ensure_data_directories()

            # Capture logs on second call
            log_events: list[dict[str, Any]] = []

            def capture_log(
                logger: Any, method_name: str, event_dict: dict[str, Any]
            ) -> dict[str, Any]:
                log_events.append(event_dict.copy())
                return event_dict

            # Configure structlog with custom processor for log capture
            # API-027: structlog type stubs incomplete - processors type mismatch
            structlog.configure(
                processors=[capture_log, structlog.dev.ConsoleRenderer()],  # type: ignore[list-item]
                wrapper_class=structlog.make_filtering_bound_logger(0),
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(),
                cache_logger_on_first_use=False,
            )

            # Second call should not log any directory_created events
            settings.ensure_data_directories()

            creation_events = [
                e for e in log_events if e.get("event") == "directory_created"
            ]
            assert len(creation_events) == 0, (
                f"Expected no directory_created events on second call, "
                f"got: {creation_events}"
            )

    def test_logs_error_on_permission_failure(self, tmp_path: Path) -> None:
        """When directory creation fails, logs directory_creation_failed event (AC#4)."""
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}
        ):
            settings = Settings()

            # Capture logs
            log_events: list[dict[str, Any]] = []

            def capture_log(
                logger: Any, method_name: str, event_dict: dict[str, Any]
            ) -> dict[str, Any]:
                log_events.append(event_dict.copy())
                return event_dict

            # Configure structlog with custom processor for log capture
            # API-027: structlog type stubs incomplete - processors type mismatch
            structlog.configure(
                processors=[capture_log, structlog.dev.ConsoleRenderer()],  # type: ignore[list-item]
                wrapper_class=structlog.make_filtering_bound_logger(0),
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(),
                cache_logger_on_first_use=False,
            )

            # Mock mkdir to raise OSError for permission failure
            with patch.object(Path, "mkdir", side_effect=OSError("Permission denied")):
                with pytest.raises(OSError, match="Permission denied"):
                    settings.ensure_data_directories()

            # Verify directory_creation_failed was logged
            error_events = [
                e for e in log_events if e.get("event") == "directory_creation_failed"
            ]
            assert len(error_events) >= 1, (
                f"Expected directory_creation_failed event, got: {log_events}"
            )
            assert "Permission denied" in str(error_events[0].get("error", ""))
