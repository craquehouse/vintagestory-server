"""Tests for runtime debug logging toggle (Story 9.4 Task 4 / FR48).

Verifies that VS_DEBUG can be changed at runtime without server restart.
"""

import os
from io import StringIO
from unittest.mock import patch

import structlog

import vintagestory_api.config as config_module
from vintagestory_api.config import (
    get_current_debug_setting,
    reconfigure_logging_if_changed,
)


class TestGetCurrentDebugSetting:
    """Tests for get_current_debug_setting function."""

    def test_returns_true_for_true(self) -> None:
        """VS_DEBUG=true returns True."""
        with patch.dict(os.environ, {"VS_DEBUG": "true"}):
            assert get_current_debug_setting() is True

    def test_returns_true_for_1(self) -> None:
        """VS_DEBUG=1 returns True."""
        with patch.dict(os.environ, {"VS_DEBUG": "1"}):
            assert get_current_debug_setting() is True

    def test_returns_true_for_yes(self) -> None:
        """VS_DEBUG=yes returns True."""
        with patch.dict(os.environ, {"VS_DEBUG": "yes"}):
            assert get_current_debug_setting() is True

    def test_returns_true_case_insensitive(self) -> None:
        """VS_DEBUG=TRUE (uppercase) returns True."""
        with patch.dict(os.environ, {"VS_DEBUG": "TRUE"}):
            assert get_current_debug_setting() is True

    def test_returns_false_for_false(self) -> None:
        """VS_DEBUG=false returns False."""
        with patch.dict(os.environ, {"VS_DEBUG": "false"}):
            assert get_current_debug_setting() is False

    def test_returns_false_for_empty(self) -> None:
        """VS_DEBUG='' returns False."""
        with patch.dict(os.environ, {"VS_DEBUG": ""}):
            assert get_current_debug_setting() is False

    def test_returns_false_when_unset(self) -> None:
        """Missing VS_DEBUG returns False."""
        env = os.environ.copy()
        env.pop("VS_DEBUG", None)
        with patch.dict(os.environ, env, clear=True):
            assert get_current_debug_setting() is False


class TestReconfigureLoggingIfChanged:
    """Tests for reconfigure_logging_if_changed function (FR48)."""

    def setup_method(self) -> None:
        """Reset module state before each test."""
        config_module._last_debug_state = None  # pyright: ignore[reportPrivateUsage]

    def test_reconfigures_on_first_call(self) -> None:
        """First call always configures logging.

        Given VS_DEBUG is not set
        When reconfigure_logging_if_changed is called
        Then logging is configured
        And returns True
        """
        with patch.dict(os.environ, {"VS_DEBUG": "false"}):
            result = reconfigure_logging_if_changed()
            assert result is True

    def test_no_reconfigure_when_unchanged(self) -> None:
        """No reconfiguration when VS_DEBUG unchanged.

        Given VS_DEBUG=false
        When reconfigure_logging_if_changed is called twice
        Then second call returns False (no change)
        """
        with patch.dict(os.environ, {"VS_DEBUG": "false"}):
            reconfigure_logging_if_changed()  # First call
            result = reconfigure_logging_if_changed()  # Second call
            assert result is False

    def test_reconfigures_when_debug_enabled(self) -> None:
        """Reconfigures when VS_DEBUG changes from false to true (AC: 2).

        Given VS_DEBUG is changed at runtime
        When the environment variable is updated
        Then debug logging is enabled without server restart
        """
        with patch.dict(os.environ, {"VS_DEBUG": "false"}):
            reconfigure_logging_if_changed()  # Initial: false

        # Change to true
        with patch.dict(os.environ, {"VS_DEBUG": "true"}):
            result = reconfigure_logging_if_changed()
            assert result is True  # Should reconfigure

    def test_reconfigures_when_debug_disabled(self) -> None:
        """Reconfigures when VS_DEBUG changes from true to false (AC: 2).

        Given debug logging is enabled
        When VS_DEBUG is set to false
        Then debug logging is disabled without server restart
        """
        with patch.dict(os.environ, {"VS_DEBUG": "true"}):
            reconfigure_logging_if_changed()  # Initial: true

        # Change to false
        with patch.dict(os.environ, {"VS_DEBUG": "false"}):
            result = reconfigure_logging_if_changed()
            assert result is True  # Should reconfigure


class TestRuntimeDebugToggleBehavior:
    """Integration tests for runtime debug toggle behavior."""

    def setup_method(self) -> None:
        """Reset module state before each test."""
        config_module._last_debug_state = None  # pyright: ignore[reportPrivateUsage]

    def test_debug_logs_appear_after_enabling(self) -> None:
        """Debug logs appear after VS_DEBUG is enabled at runtime.

        Given VS_DEBUG=false initially
        When VS_DEBUG is changed to true
        And reconfigure_logging_if_changed is called
        Then debug-level logs are now emitted
        """
        log_output = StringIO()

        # Start with debug=false
        with patch.dict(os.environ, {"VS_DEBUG": "false"}):
            reconfigure_logging_if_changed()

            # Reconfigure structlog with our output capture
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.add_log_level,
                    structlog.dev.ConsoleRenderer(),
                ],
                wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(file=log_output),
                cache_logger_on_first_use=False,
            )

            logger = structlog.get_logger()
            logger.debug("should_not_appear_initial")

        initial_output = log_output.getvalue()
        assert "should_not_appear_initial" not in initial_output

        # Now enable debug
        log_output.truncate(0)
        log_output.seek(0)

        with patch.dict(os.environ, {"VS_DEBUG": "true"}):
            reconfigure_logging_if_changed()

            # Reconfigure with DEBUG level
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.add_log_level,
                    structlog.dev.ConsoleRenderer(),
                ],
                wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(file=log_output),
                cache_logger_on_first_use=False,
            )

            logger = structlog.get_logger()
            logger.debug("should_appear_now")

        final_output = log_output.getvalue()
        assert "should_appear_now" in final_output

    def test_debug_logs_stop_after_disabling(self) -> None:
        """Debug logs stop appearing after VS_DEBUG is disabled.

        Given VS_DEBUG=true initially
        When VS_DEBUG is changed to false
        And reconfigure_logging_if_changed is called
        Then debug-level logs are no longer emitted
        """
        log_output = StringIO()

        # Start with debug=true
        with patch.dict(os.environ, {"VS_DEBUG": "true"}):
            reconfigure_logging_if_changed()

            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.add_log_level,
                    structlog.dev.ConsoleRenderer(),
                ],
                wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(file=log_output),
                cache_logger_on_first_use=False,
            )

            logger = structlog.get_logger()
            logger.debug("should_appear_initial")

        initial_output = log_output.getvalue()
        assert "should_appear_initial" in initial_output

        # Now disable debug
        log_output.truncate(0)
        log_output.seek(0)

        with patch.dict(os.environ, {"VS_DEBUG": "false"}):
            reconfigure_logging_if_changed()

            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.add_log_level,
                    structlog.dev.ConsoleRenderer(),
                ],
                wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(file=log_output),
                cache_logger_on_first_use=False,
            )

            logger = structlog.get_logger()
            logger.debug("should_not_appear_now")
            logger.info("info_still_works")

        final_output = log_output.getvalue()
        assert "should_not_appear_now" not in final_output
        assert "info_still_works" in final_output
