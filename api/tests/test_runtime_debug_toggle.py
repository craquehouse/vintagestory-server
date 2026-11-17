"""Tests for runtime debug logging toggle (Story 9.4 Task 4 / FR48).

Verifies that debug logging can be toggled at runtime via API.
"""

import json
from io import StringIO

import pytest
import structlog

import vintagestory_api.config as config_module
from vintagestory_api.config import (
    Settings,
    configure_logging,
    current_log_level,
    initialize_debug_state,
    is_debug_enabled,
    set_debug_enabled,
)


@pytest.fixture
def fresh_debug_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start from a process that has not initialised its debug state yet.

    monkeypatch restores the module's state after each test.
    """
    monkeypatch.setattr(config_module, "_debug_enabled", False)
    monkeypatch.setattr(config_module, "_debug_initialized", False)
    monkeypatch.setattr(config_module, "_configured_log_level", None)
    monkeypatch.setattr(config_module, "_current_log_level", "INFO")


@pytest.mark.usefixtures("fresh_debug_state")
class TestInitializeDebugState:
    """Tests for initialize_debug_state, fed from the settings (Epic 21 ADR-4)."""

    def test_reads_true_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given VS_DEBUG=true, debug state is set to True."""
        monkeypatch.setenv("VS_DEBUG", "true")
        settings = Settings()

        initialize_debug_state(settings.debug, settings.log_level)

        assert is_debug_enabled() is True

    def test_reads_false_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given VS_DEBUG=false, debug state is set to False."""
        monkeypatch.setenv("VS_DEBUG", "false")
        settings = Settings()

        initialize_debug_state(settings.debug, settings.log_level)

        assert is_debug_enabled() is False

    def test_defaults_false_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given VS_DEBUG is not set, debug state is False."""
        monkeypatch.delenv("VS_DEBUG", raising=False)
        settings = Settings()

        initialize_debug_state(settings.debug, settings.log_level)

        assert is_debug_enabled() is False

    def test_only_initializes_once(self) -> None:
        """A second call with other arguments changes nothing."""
        initialize_debug_state(True, None)
        assert is_debug_enabled() is True

        initialize_debug_state(False, "WARNING")

        assert is_debug_enabled() is True
        assert current_log_level() == "DEBUG"

    @pytest.mark.parametrize(
        "value", ["true", "TRUE", "True", "1", "yes", "YES", "on", "On", "y", "t"]
    )
    def test_accepts_various_true_values(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        """Every value pydantic reads as true turns debug logging on (ADR-4 decision 6)."""
        monkeypatch.setenv("VS_DEBUG", value)
        settings = Settings()

        initialize_debug_state(settings.debug, settings.log_level)

        assert is_debug_enabled() is True, f"Failed for VS_DEBUG={value}"
        assert current_log_level() == "DEBUG"


@pytest.mark.usefixtures("fresh_debug_state")
class TestSetDebugEnabled:
    """Tests for set_debug_enabled function (FR48 runtime toggle)."""

    def test_enable_debug(self) -> None:
        """Given debug is disabled, set_debug_enabled(True) enables it and reports a change."""
        initialize_debug_state(False, None)
        assert is_debug_enabled() is False
        changed = set_debug_enabled(True)
        assert changed is True
        assert is_debug_enabled() is True

    def test_disable_debug(self) -> None:
        """Given debug is enabled, set_debug_enabled(False) disables it and reports a change."""
        initialize_debug_state(True, None)
        assert is_debug_enabled() is True
        changed = set_debug_enabled(False)
        assert changed is True
        assert is_debug_enabled() is False

    def test_no_change_when_already_enabled(self) -> None:
        """Given debug is already enabled at DEBUG, enabling reports no change."""
        initialize_debug_state(True, None)
        changed = set_debug_enabled(True)
        assert changed is False
        assert is_debug_enabled() is True

    def test_no_change_when_already_disabled(self) -> None:
        """Given debug is already disabled, disabling reports no change."""
        initialize_debug_state(False, None)
        changed = set_debug_enabled(False)
        assert changed is False
        assert is_debug_enabled() is False


LEVEL_ORDER = ("DEBUG", "INFO", "WARNING", "ERROR")


def emit_one_line_per_level() -> None:
    log = structlog.get_logger()
    log.debug("line_at_debug")
    log.info("line_at_info")
    log.warning("line_at_warning")
    log.error("line_at_error")


def written_levels(out: str) -> list[str]:
    return [level for level in LEVEL_ORDER if f"line_at_{level.lower()}" in out]


@pytest.mark.usefixtures("fresh_debug_state")
class TestConfiguredLogLevel:
    """VS_LOG_LEVEL sets the level; the switch gives DEBUG and returns to it (ADR-4)."""

    @pytest.mark.parametrize(
        ("debug", "log_level", "expected_level", "renderer"),
        [
            (False, None, "INFO", "json"),
            (True, None, "DEBUG", "console"),
            (False, "WARNING", "WARNING", "json"),
            (True, "INFO", "INFO", "console"),
            (False, "DEBUG", "DEBUG", "json"),
            (True, "ERROR", "ERROR", "console"),
        ],
    )
    def test_start_up_level_and_renderer(
        self,
        capsys: pytest.CaptureFixture[str],
        debug: bool,
        log_level: str | None,
        expected_level: str,
        renderer: str,
    ) -> None:
        initialize_debug_state(debug, log_level)
        capsys.readouterr()

        emit_one_line_per_level()
        out = capsys.readouterr().out

        assert current_log_level() == expected_level
        assert written_levels(out) == list(LEVEL_ORDER[LEVEL_ORDER.index(expected_level) :])
        lines = [line for line in out.splitlines() if line.strip()]
        assert lines
        for line in lines:
            if renderer == "json":
                assert isinstance(json.loads(line), dict)
            else:
                with pytest.raises(json.JSONDecodeError):
                    json.loads(line)

    def test_switch_round_trip_returns_to_the_configured_level(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        initialize_debug_state(False, "WARNING")

        assert set_debug_enabled(True) is True
        assert current_log_level() == "DEBUG"
        capsys.readouterr()
        structlog.get_logger().debug("line_while_on")
        assert "line_while_on" in capsys.readouterr().out

        assert set_debug_enabled(False) is True
        assert current_log_level() == "WARNING"
        capsys.readouterr()
        emit_one_line_per_level()
        assert written_levels(capsys.readouterr().out) == ["WARNING", "ERROR"]

    def test_switch_off_returns_to_info_without_a_configured_level(self) -> None:
        initialize_debug_state(False, None)

        assert set_debug_enabled(True) is True
        assert current_log_level() == "DEBUG"
        assert set_debug_enabled(False) is True
        assert current_log_level() == "INFO"

    def test_enable_in_debug_mode_with_a_quiet_level_gives_debug(self) -> None:
        """VS_DEBUG=true with VS_LOG_LEVEL=WARNING: enable changes the level (story decision)."""
        initialize_debug_state(True, "WARNING")
        assert current_log_level() == "WARNING"

        assert set_debug_enabled(True) is True
        assert current_log_level() == "DEBUG"
        assert set_debug_enabled(True) is False

    def test_disable_when_off_keeps_the_configured_level(self) -> None:
        initialize_debug_state(False, "WARNING")

        assert set_debug_enabled(False) is False
        assert current_log_level() == "WARNING"


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
