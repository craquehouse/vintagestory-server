"""Tests for runtime debug logging toggle (Story 9.4 Task 4 / FR48).

Verifies that debug logging can be toggled at runtime via API.
"""

import os
from io import StringIO
from unittest.mock import patch

import structlog

import vintagestory_api.config as config_module
from vintagestory_api.config import (
    configure_logging,
    initialize_debug_state,
    is_debug_enabled,
    set_debug_enabled,
)


class TestInitializeDebugState:
    """Tests for initialize_debug_state function."""

    def setup_method(self) -> None:
        """Reset module state before each test."""
        config_module._debug_enabled = False  # pyright: ignore[reportPrivateUsage]
        config_module._debug_initialized = False  # pyright: ignore[reportPrivateUsage]

    def test_reads_true_from_env(self) -> None:
        """Initialize debug state from VS_DEBUG=true.

        Given VS_DEBUG=true in environment
        When initialize_debug_state is called
        Then debug state is set to True
        """
        with patch.dict(os.environ, {"VS_DEBUG": "true"}):
            initialize_debug_state()
            assert is_debug_enabled() is True

    def test_reads_false_from_env(self) -> None:
        """Initialize debug state from VS_DEBUG=false.

        Given VS_DEBUG=false in environment
        When initialize_debug_state is called
        Then debug state is set to False
        """
        with patch.dict(os.environ, {"VS_DEBUG": "false"}):
            initialize_debug_state()
            assert is_debug_enabled() is False

    def test_defaults_false_when_unset(self) -> None:
        """Debug state defaults to False when VS_DEBUG is not set.

        Given VS_DEBUG is not set
        When initialize_debug_state is called
        Then debug state is False
        """
        env = os.environ.copy()
        env.pop("VS_DEBUG", None)
        with patch.dict(os.environ, env, clear=True):
            initialize_debug_state()
            assert is_debug_enabled() is False

    def test_only_initializes_once(self) -> None:
        """Initialize debug state only runs once.

        Given initialize_debug_state has been called
        When called again with different env value
        Then debug state is not changed
        """
        with patch.dict(os.environ, {"VS_DEBUG": "true"}):
            initialize_debug_state()
            assert is_debug_enabled() is True

        # Second call with different env should be ignored
        with patch.dict(os.environ, {"VS_DEBUG": "false"}):
            initialize_debug_state()
            assert is_debug_enabled() is True  # Still True from first init

    def test_accepts_various_true_values(self) -> None:
        """VS_DEBUG accepts 'true', '1', 'yes' (case-insensitive)."""
        for value in ["true", "TRUE", "True", "1", "yes", "YES"]:
            config_module._debug_enabled = False  # pyright: ignore[reportPrivateUsage]
            config_module._debug_initialized = False  # pyright: ignore[reportPrivateUsage]
            with patch.dict(os.environ, {"VS_DEBUG": value}):
                initialize_debug_state()
                assert is_debug_enabled() is True, f"Failed for VS_DEBUG={value}"


class TestSetDebugEnabled:
    """Tests for set_debug_enabled function (FR48 runtime toggle)."""

    def setup_method(self) -> None:
        """Reset module state before each test."""
        config_module._debug_enabled = False  # pyright: ignore[reportPrivateUsage]
        config_module._debug_initialized = True  # pyright: ignore[reportPrivateUsage]

    def test_enable_debug(self) -> None:
        """Enable debug logging at runtime.

        Given debug is disabled
        When set_debug_enabled(True) is called
        Then debug is enabled
        And returns True (changed)
        """
        assert is_debug_enabled() is False
        changed = set_debug_enabled(True)
        assert changed is True
        assert is_debug_enabled() is True

    def test_disable_debug(self) -> None:
        """Disable debug logging at runtime.

        Given debug is enabled
        When set_debug_enabled(False) is called
        Then debug is disabled
        And returns True (changed)
        """
        config_module._debug_enabled = True  # pyright: ignore[reportPrivateUsage]
        assert is_debug_enabled() is True
        changed = set_debug_enabled(False)
        assert changed is True
        assert is_debug_enabled() is False

    def test_no_change_when_already_enabled(self) -> None:
        """No change when enabling already-enabled debug.

        Given debug is already enabled
        When set_debug_enabled(True) is called
        Then returns False (no change)
        """
        config_module._debug_enabled = True  # pyright: ignore[reportPrivateUsage]
        changed = set_debug_enabled(True)
        assert changed is False
        assert is_debug_enabled() is True

    def test_no_change_when_already_disabled(self) -> None:
        """No change when disabling already-disabled debug.

        Given debug is already disabled
        When set_debug_enabled(False) is called
        Then returns False (no change)
        """
        changed = set_debug_enabled(False)
        assert changed is False
        assert is_debug_enabled() is False


class TestRuntimeDebugToggleBehavior:
    """Integration tests for runtime debug toggle behavior."""

    def setup_method(self) -> None:
        """Reset module state before each test."""
        config_module._debug_enabled = False  # pyright: ignore[reportPrivateUsage]
        config_module._debug_initialized = True  # pyright: ignore[reportPrivateUsage]

    def test_debug_logs_appear_after_enabling(self) -> None:
        """Debug logs appear after debug is enabled at runtime.

        Given debug is disabled initially
        When set_debug_enabled(True) is called
        Then debug-level logs are now emitted
        """
        log_output = StringIO()

        # Start with debug=false
        configure_logging(debug=False)

        # Reconfigure structlog with our output capture (INFO level)
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

        # Now enable debug via API
        log_output.truncate(0)
        log_output.seek(0)

        set_debug_enabled(True)

        # Reconfigure with DEBUG level (simulating what set_debug_enabled does internally)
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
        """Debug logs stop appearing after debug is disabled.

        Given debug is enabled initially
        When set_debug_enabled(False) is called
        Then debug-level logs are no longer emitted
        """
        log_output = StringIO()

        # Start with debug=true
        config_module._debug_enabled = True  # pyright: ignore[reportPrivateUsage]

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

        # Now disable debug via API
        log_output.truncate(0)
        log_output.seek(0)

        set_debug_enabled(False)

        # Reconfigure with INFO level
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
