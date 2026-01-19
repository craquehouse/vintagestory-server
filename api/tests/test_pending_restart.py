"""Unit tests for PendingRestartState."""

from io import StringIO

import pytest
import structlog

from vintagestory_api.services.pending_restart import PendingRestartState


class TestPendingRestartStateInit:
    """Tests for PendingRestartState initialization."""

    def test_init_no_restart_pending(self) -> None:
        """PendingRestartState initializes with no restart pending."""
        state = PendingRestartState()

        assert state.pending_restart is False
        assert state.pending_changes == []

    def test_init_creates_independent_instances(self) -> None:
        """Multiple instances are independent."""
        state1 = PendingRestartState()
        state2 = PendingRestartState()

        state1.require_restart("change1")

        assert state1.pending_restart is True
        assert state2.pending_restart is False
        assert len(state1.pending_changes) == 1
        assert len(state2.pending_changes) == 0


class TestPendingRestartStateProperties:
    """Tests for property accessors."""

    def test_pending_restart_property_returns_bool(self) -> None:
        """pending_restart property returns boolean value."""
        state = PendingRestartState()

        assert isinstance(state.pending_restart, bool)
        assert state.pending_restart is False

        state.require_restart("test")
        assert state.pending_restart is True

    def test_pending_changes_property_returns_copy(self) -> None:
        """pending_changes property returns a copy, not the internal list."""
        state = PendingRestartState()
        state.require_restart("change1")

        changes = state.pending_changes
        changes.append("external_modification")

        # Internal state should be unchanged
        assert len(state.pending_changes) == 1
        assert "external_modification" not in state.pending_changes

    def test_pending_changes_property_returns_empty_list(self) -> None:
        """pending_changes property returns empty list when no changes."""
        state = PendingRestartState()

        assert state.pending_changes == []
        assert isinstance(state.pending_changes, list)


class TestRequireRestart:
    """Tests for require_restart() method."""

    def test_require_restart_sets_pending_flag(self) -> None:
        """require_restart() sets pending_restart to True."""
        state = PendingRestartState()
        state.require_restart("mod enabled")

        assert state.pending_restart is True

    def test_require_restart_appends_reason(self) -> None:
        """require_restart() appends reason to pending_changes."""
        state = PendingRestartState()
        state.require_restart("mod enabled: testmod")

        assert len(state.pending_changes) == 1
        assert state.pending_changes[0] == "mod enabled: testmod"

    def test_require_restart_multiple_reasons(self) -> None:
        """require_restart() can be called multiple times to accumulate reasons."""
        state = PendingRestartState()

        state.require_restart("mod enabled: mod1")
        state.require_restart("mod disabled: mod2")
        state.require_restart("config changed: maxplayers")

        assert state.pending_restart is True
        assert len(state.pending_changes) == 3
        assert state.pending_changes[0] == "mod enabled: mod1"
        assert state.pending_changes[1] == "mod disabled: mod2"
        assert state.pending_changes[2] == "config changed: maxplayers"

    def test_require_restart_preserves_order(self) -> None:
        """require_restart() preserves insertion order of reasons."""
        state = PendingRestartState()
        reasons = ["first", "second", "third", "fourth", "fifth"]

        for reason in reasons:
            state.require_restart(reason)

        assert state.pending_changes == reasons

    def test_require_restart_logs_event(self, captured_logs: StringIO) -> None:
        """require_restart() logs restart_required event."""
        state = PendingRestartState()
        state.require_restart("test reason")

        log_output = captured_logs.getvalue()
        assert "restart_required" in log_output
        assert "reason" in log_output
        assert "test reason" in log_output

    def test_require_restart_logs_total_pending_changes(self, captured_logs: StringIO) -> None:
        """require_restart() logs total count of pending changes."""
        state = PendingRestartState()

        state.require_restart("change1")
        state.require_restart("change2")

        log_output = captured_logs.getvalue()
        assert "total_pending_changes" in log_output
        # Should show 2 for the second call
        assert "2" in log_output

    def test_require_restart_accepts_empty_string(self) -> None:
        """require_restart() accepts empty string as reason."""
        state = PendingRestartState()
        state.require_restart("")

        assert state.pending_restart is True
        assert state.pending_changes == [""]

    def test_require_restart_accepts_unicode(self) -> None:
        """require_restart() handles Unicode characters in reason."""
        state = PendingRestartState()
        state.require_restart("配置已更改: 玩家数量")

        assert state.pending_restart is True
        assert "配置已更改: 玩家数量" in state.pending_changes

    def test_require_restart_accepts_multiline_string(self) -> None:
        """require_restart() handles multiline reason strings."""
        state = PendingRestartState()
        reason = "mod enabled: testmod\nversion: 1.0.0\nauthor: test"
        state.require_restart(reason)

        assert state.pending_restart is True
        assert state.pending_changes[0] == reason


class TestClearRestart:
    """Tests for clear_restart() method."""

    def test_clear_restart_resets_pending_flag(self) -> None:
        """clear_restart() sets pending_restart to False."""
        state = PendingRestartState()
        state.require_restart("test")

        state.clear_restart()

        assert state.pending_restart is False

    def test_clear_restart_clears_changes_list(self) -> None:
        """clear_restart() clears all pending changes."""
        state = PendingRestartState()
        state.require_restart("change1")
        state.require_restart("change2")
        state.require_restart("change3")

        state.clear_restart()

        assert state.pending_changes == []

    def test_clear_restart_when_no_restart_pending(self) -> None:
        """clear_restart() is safe to call when no restart is pending."""
        state = PendingRestartState()

        # Should not raise or log
        state.clear_restart()

        assert state.pending_restart is False
        assert state.pending_changes == []

    def test_clear_restart_logs_when_restart_pending(self, captured_logs: StringIO) -> None:
        """clear_restart() logs restart_cleared event when restart was pending."""
        state = PendingRestartState()
        state.require_restart("change1")
        state.require_restart("change2")

        # Clear logs from require_restart calls
        captured_logs.truncate(0)
        captured_logs.seek(0)

        state.clear_restart()

        log_output = captured_logs.getvalue()
        assert "restart_cleared" in log_output
        assert "cleared_changes" in log_output
        assert "2" in log_output

    def test_clear_restart_no_log_when_not_pending(self, captured_logs: StringIO) -> None:
        """clear_restart() does not log when no restart was pending."""
        state = PendingRestartState()

        state.clear_restart()

        log_output = captured_logs.getvalue()
        assert "restart_cleared" not in log_output

    def test_clear_restart_idempotent(self) -> None:
        """clear_restart() can be called multiple times safely."""
        state = PendingRestartState()
        state.require_restart("test")

        state.clear_restart()
        state.clear_restart()
        state.clear_restart()

        assert state.pending_restart is False
        assert state.pending_changes == []


class TestStateTransitions:
    """Tests for state transition scenarios."""

    def test_state_transitions_require_to_clear(self) -> None:
        """State transitions correctly from no restart → pending → cleared."""
        state = PendingRestartState()

        # Initial state
        assert state.pending_restart is False
        assert len(state.pending_changes) == 0

        # Transition to pending
        state.require_restart("first change")
        assert state.pending_restart is True
        assert len(state.pending_changes) == 1

        # Transition back to no restart
        state.clear_restart()
        assert state.pending_restart is False
        assert len(state.pending_changes) == 0

    def test_state_transitions_multiple_cycles(self) -> None:
        """State can cycle through require/clear multiple times."""
        state = PendingRestartState()

        # Cycle 1
        state.require_restart("cycle1")
        assert state.pending_restart is True
        state.clear_restart()
        assert state.pending_restart is False

        # Cycle 2
        state.require_restart("cycle2a")
        state.require_restart("cycle2b")
        assert len(state.pending_changes) == 2
        state.clear_restart()
        assert len(state.pending_changes) == 0

        # Cycle 3
        state.require_restart("cycle3")
        assert state.pending_restart is True

    def test_state_accumulates_changes_before_clear(self) -> None:
        """Multiple require_restart calls accumulate before clear."""
        state = PendingRestartState()

        state.require_restart("change1")
        state.require_restart("change2")
        state.require_restart("change3")

        assert len(state.pending_changes) == 3
        assert state.pending_restart is True

        state.clear_restart()

        assert len(state.pending_changes) == 0
        assert state.pending_restart is False

    def test_state_independent_after_clear(self) -> None:
        """State after clear is independent from previous state."""
        state = PendingRestartState()

        state.require_restart("old1")
        state.require_restart("old2")
        state.clear_restart()

        state.require_restart("new1")

        assert len(state.pending_changes) == 1
        assert state.pending_changes[0] == "new1"
        assert "old1" not in state.pending_changes
        assert "old2" not in state.pending_changes


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_large_number_of_changes(self) -> None:
        """State handles large number of accumulated changes."""
        state = PendingRestartState()

        num_changes = 1000
        for i in range(num_changes):
            state.require_restart(f"change_{i}")

        assert state.pending_restart is True
        assert len(state.pending_changes) == num_changes
        assert state.pending_changes[0] == "change_0"
        assert state.pending_changes[999] == "change_999"

    def test_very_long_reason_string(self) -> None:
        """State handles very long reason strings."""
        state = PendingRestartState()

        long_reason = "x" * 10000
        state.require_restart(long_reason)

        assert state.pending_restart is True
        assert len(state.pending_changes) == 1
        assert state.pending_changes[0] == long_reason

    def test_duplicate_reasons_allowed(self) -> None:
        """State allows duplicate reasons (does not deduplicate)."""
        state = PendingRestartState()

        state.require_restart("same reason")
        state.require_restart("same reason")
        state.require_restart("same reason")

        assert len(state.pending_changes) == 3
        assert all(r == "same reason" for r in state.pending_changes)

    def test_special_characters_in_reason(self) -> None:
        """State handles special characters in reason strings."""
        state = PendingRestartState()

        special_reasons = [
            "reason with\nnewline",
            "reason with\ttab",
            "reason with 'quotes'",
            'reason with "double quotes"',
            "reason with \x00 null",
            "reason with emoji 🚀",
        ]

        for reason in special_reasons:
            state.require_restart(reason)

        assert len(state.pending_changes) == len(special_reasons)
        assert state.pending_changes == special_reasons


class TestPropertyImmutability:
    """Tests that properties are read-only and cannot be modified externally."""

    def test_cannot_modify_pending_restart_directly(self) -> None:
        """pending_restart property cannot be assigned to."""
        state = PendingRestartState()

        with pytest.raises(AttributeError):
            state.pending_restart = True  # type: ignore[misc]

    def test_cannot_modify_pending_changes_directly(self) -> None:
        """pending_changes property cannot be assigned to."""
        state = PendingRestartState()

        with pytest.raises(AttributeError):
            state.pending_changes = ["external"]  # type: ignore[misc]

    def test_modifying_returned_list_does_not_affect_state(self) -> None:
        """Modifying the list returned by pending_changes doesn't affect internal state."""
        state = PendingRestartState()
        state.require_restart("original")

        # Get the list
        changes = state.pending_changes

        # Try to modify it
        changes.append("added")
        changes.clear()

        # Internal state should be unchanged
        assert state.pending_changes == ["original"]
