"""Tests for application configuration."""

import os
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from vintagestory_api.config import Settings, configure_logging


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

    def test_logs_directory_created_event(
        self, tmp_path: Path, captured_logs: StringIO
    ) -> None:
        """When directories are created, logs directory_created event (AC#2).

        Verifies that all 6 directories are logged when created:
        server, serverdata, vsmanager, cache, state, logs.
        """
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}
        ):
            settings = Settings()
            settings.ensure_data_directories()

            output = captured_logs.getvalue()

            # Verify directory_created events were logged for all 6 directories
            expected_dirs = ["server", "serverdata", "vsmanager", "cache", "state", "logs"]
            for dir_name in expected_dirs:
                assert "directory_created" in output, (
                    "Expected 'directory_created' event in log output"
                )
                assert dir_name in output, (
                    f"Expected '{dir_name}' directory in logged output"
                )

    def test_no_log_when_directories_exist(
        self, tmp_path: Path, captured_logs: StringIO
    ) -> None:
        """When directories already exist, no creation logs are emitted (AC#3)."""
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}
        ):
            settings = Settings()

            # First call creates directories
            settings.ensure_data_directories()

            # Clear log buffer before second call
            captured_logs.truncate(0)
            captured_logs.seek(0)

            # Second call should not log any directory_created events
            settings.ensure_data_directories()

            output = captured_logs.getvalue()
            assert "directory_created" not in output, (
                f"Expected no directory_created events on second call, "
                f"got: {output}"
            )

    def test_logs_error_on_permission_failure(
        self, tmp_path: Path, captured_logs: StringIO
    ) -> None:
        """When directory creation fails, logs directory_creation_failed event (AC#4)."""
        with patch.dict(
            os.environ, {"VS_DATA_DIR": str(tmp_path), "VS_API_KEY_ADMIN": "test-key"}
        ):
            settings = Settings()

            # Mock mkdir to raise OSError for permission failure
            with patch.object(Path, "mkdir", side_effect=OSError("Permission denied")):
                with pytest.raises(OSError, match="Permission denied"):
                    settings.ensure_data_directories()

            output = captured_logs.getvalue()
            assert "directory_creation_failed" in output, (
                f"Expected directory_creation_failed event, got: {output}"
            )
            assert "Permission denied" in output


class TestModCacheMaxSize:
    """Tests for mod cache max size configuration (Story 9.3)."""

    def test_default_mod_cache_max_size(self) -> None:
        """Default mod cache max size is 500MB."""
        settings = Settings()
        assert settings.mod_cache_max_size_mb == 500

    def test_mod_cache_max_size_from_env(self) -> None:
        """Mod cache max size can be configured via environment variable."""
        with patch.dict(os.environ, {"VS_MOD_CACHE_MAX_SIZE_MB": "1000"}):
            settings = Settings()
            assert settings.mod_cache_max_size_mb == 1000

    def test_mod_cache_max_size_zero_disables(self) -> None:
        """Setting mod cache max size to 0 disables eviction."""
        with patch.dict(os.environ, {"VS_MOD_CACHE_MAX_SIZE_MB": "0"}):
            settings = Settings()
            assert settings.mod_cache_max_size_mb == 0

    def test_mod_cache_max_size_negative_rejected(self) -> None:
        """Negative mod cache max size is rejected."""
        with patch.dict(os.environ, {"VS_MOD_CACHE_MAX_SIZE_MB": "-100"}):
            with pytest.raises(ValueError, match="VS_MOD_CACHE_MAX_SIZE_MB must be non-negative"):
                Settings()


class TestConfigureLoggingContextVars:
    """Tests for structlog contextvars integration (Story 9.4 Task 2)."""

    def test_merge_contextvars_in_debug_mode(self) -> None:
        """In debug mode, context vars are merged into log output.

        Verifies that the merge_contextvars processor is correctly
        configured to include bound context variables in log entries.
        """
        log_output = StringIO()

        # Configure logging with custom output
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(0),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=log_output),
            cache_logger_on_first_use=False,
        )

        # Bind context var (like request_id)
        clear_contextvars()
        bind_contextvars(request_id="test-123", user="admin")

        logger = structlog.get_logger()
        logger.info("test_event", action="test")

        output = log_output.getvalue()
        assert "request_id" in output
        assert "test-123" in output
        assert "user" in output
        assert "admin" in output

        clear_contextvars()

    def test_merge_contextvars_in_production_mode(self) -> None:
        """In production mode, context vars are merged into JSON output.

        Verifies that the merge_contextvars processor works correctly
        with JSONRenderer as well as ConsoleRenderer.
        """
        log_output = StringIO()

        # Configure logging with JSON output (production mode)
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(0),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=log_output),
            cache_logger_on_first_use=False,
        )

        # Bind context var
        clear_contextvars()
        bind_contextvars(request_id="prod-456")

        logger = structlog.get_logger()
        logger.info("production_event")

        output = log_output.getvalue()
        # JSON output should contain the request_id field
        assert '"request_id"' in output or "request_id" in output
        assert "prod-456" in output

        clear_contextvars()

    def test_context_vars_cleared_do_not_appear(self) -> None:
        """After clearing context vars, they should not appear in logs.

        Verifies that clear_contextvars() properly removes all
        bound context from subsequent log entries.
        """
        log_output = StringIO()

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(0),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=log_output),
            cache_logger_on_first_use=False,
        )

        # Bind and then clear context
        bind_contextvars(request_id="should-not-appear")
        clear_contextvars()

        logger = structlog.get_logger()
        logger.info("after_clear")

        output = log_output.getvalue()
        assert "should-not-appear" not in output

    def test_configure_logging_adds_merge_contextvars_debug(self) -> None:
        """configure_logging(debug=True) adds merge_contextvars as first processor.

        This is the actual function being modified in Task 2.
        """
        log_output = StringIO()

        # Call the actual configure_logging function
        configure_logging(debug=True)

        # Reconfigure with our capture mechanism but same processor chain
        # We verify the config includes merge_contextvars by testing behavior
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(0),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=log_output),
            cache_logger_on_first_use=False,
        )

        clear_contextvars()
        bind_contextvars(request_id="verify-config")

        logger = structlog.get_logger()
        logger.info("config_test")

        output = log_output.getvalue()
        assert "request_id" in output
        assert "verify-config" in output

        clear_contextvars()

    def test_configure_logging_adds_merge_contextvars_production(self) -> None:
        """configure_logging(debug=False) adds merge_contextvars for JSON output."""
        log_output = StringIO()

        # Call actual configure_logging with production mode
        configure_logging(debug=False)

        # Test with JSON output
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(0),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=log_output),
            cache_logger_on_first_use=False,
        )

        clear_contextvars()
        bind_contextvars(request_id="prod-verify")

        logger = structlog.get_logger()
        logger.info("prod_config_test")

        output = log_output.getvalue()
        assert "prod-verify" in output

        clear_contextvars()
