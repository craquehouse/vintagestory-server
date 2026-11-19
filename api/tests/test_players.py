"""Tests for the player tracker (Story 22.1, Epic 22 ADR-1).

Names and addresses are placeholders: ExamplePlayer, AnotherPlayer and the
documentation ranges 203.0.113.0/24, 198.51.100.0/24 (RFC 5737) and 2001:db8::/32
(RFC 3849).
"""

import re

import pytest
from structlog.testing import capture_logs

from vintagestory_api.services import players
from vintagestory_api.services.players import PlayerTracker

NAME = "ExamplePlayer"
ADDRESS = "203.0.113.5:42420"
OTHER = "AnotherPlayer"
OTHER_ADDRESS = "198.51.100.7:42420"


def event(message: str) -> str:
    """A game output line carrying an event message.

    PROVISIONAL, as the tracker's prefix: the timestamp and "[Event]" tag are assumed
    until the maintainer's sample lines arrive (Story 22.1, Task 6.4).
    """
    return f"18.11.2026 10:15:32 [Event] {message}"


def join(name: str, address: str) -> str:
    return event(f"{name} {address} joins.")


def leave(name: str) -> str:
    return event(f"Player {name} left.")


def rejoin(name: str) -> str:
    return event(f"{name} joined again, killing previous client.")


def _name(pattern: re.Pattern[str], message: str) -> str | None:
    match = pattern.match(message)
    return match.group("name") if match else None


class TestLiteralPatterns:
    """The VintagestoryLib.dll literals, independent of the line prefix."""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("ExamplePlayer 203.0.113.5:42420 joins.", "ExamplePlayer"),
            ("Some Name 203.0.113.5:42420 joins.", "Some Name"),
            ("ExamplePlayer [2001:db8::1]:42420 joins.", "ExamplePlayer"),
        ],
    )
    def test_join_name(self, message: str, expected: str) -> None:
        assert _name(players._JOIN, message) == expected

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("Player ExamplePlayer left.", "ExamplePlayer"),
            ("Player Some Name left.", "Some Name"),
        ],
    )
    def test_leave_name(self, message: str, expected: str) -> None:
        assert _name(players._LEAVE, message) == expected

    def test_rejoin_name(self) -> None:
        message = "ExamplePlayer joined again, killing previous client."
        assert _name(players._REJOIN, message) == "ExamplePlayer"

    @pytest.mark.parametrize(
        "message",
        [
            "Client 3 disconnected.",
            "ExamplePlayer joined. Say hi :)",
            "ExamplePlayer joins.",
        ],
    )
    def test_not_matched(self, message: str) -> None:
        for pattern in (players._JOIN, players._LEAVE, players._REJOIN):
            assert pattern.match(message) is None


class TestCounting:
    """Join, leave and rejoin lines (AC 1, 2)."""

    def test_join_and_leave_sequence(self) -> None:
        tracker = PlayerTracker()
        assert tracker.count == 0

        tracker.observe(join(NAME, ADDRESS))
        assert tracker.count == 1

        tracker.observe(join(OTHER, OTHER_ADDRESS))
        assert tracker.count == 2

        tracker.observe(join(NAME, ADDRESS))
        assert tracker.count == 2

        tracker.observe(rejoin(NAME))
        assert tracker.count == 2

        tracker.observe(leave("Nobody"))
        assert tracker.count == 2

        tracker.observe(leave(NAME))
        assert tracker.count == 1

        tracker.observe(leave(NAME))
        assert tracker.count == 1

        tracker.observe(leave(OTHER))
        assert tracker.count == 0

        tracker.observe(leave(OTHER))
        assert tracker.count == 0

    def test_rejoin_of_a_name_not_online_counts_it(self) -> None:
        """A rejoin says the player is on the server; a name the set missed is added."""
        tracker = PlayerTracker()
        tracker.observe(rejoin(NAME))
        assert tracker.count == 1

    def test_name_with_spaces_joins_and_leaves(self) -> None:
        tracker = PlayerTracker()
        tracker.observe(join("Some Name", ADDRESS))
        assert tracker.count == 1
        tracker.observe(leave("Some Name"))
        assert tracker.count == 0

    def test_ipv6_address_join(self) -> None:
        tracker = PlayerTracker()
        tracker.observe(join(NAME, "[2001:db8::1]:42420"))
        tracker.observe(leave(NAME))
        assert tracker.count == 0


class TestOtherLines:
    """Chat and other lines are not counted (AC 4)."""

    @pytest.mark.parametrize(
        "line",
        [
            "18.11.2026 10:15:33 [Chat] AnotherPlayer: he joins.",
            f"18.11.2026 10:15:33 [Chat] {OTHER}: {NAME} {ADDRESS} joins.",
            f"18.11.2026 10:15:33 [Chat] 0 | {OTHER}: Player {NAME} left.",
            f"18.11.2026 10:15:33 [Chat] x [Event] {NAME} {ADDRESS} joins.",
            f"{NAME} {ADDRESS} joins.",
            f"18.11.2026 10:15:33 [Notification] {NAME} {ADDRESS} joins.",
            event("Client 3 disconnected."),
            event(f"{NAME} joined. Say hi :)"),
            "",
        ],
    )
    def test_line_not_counted(self, line: str) -> None:
        tracker = PlayerTracker()
        tracker.observe(line)
        assert tracker.count == 0

    def test_chat_leave_does_not_remove_an_online_player(self) -> None:
        tracker = PlayerTracker()
        tracker.observe(join(NAME, ADDRESS))
        tracker.observe(f"18.11.2026 10:15:33 [Chat] 0 | {OTHER}: Player {NAME} left.")
        assert tracker.count == 1


class TestReset:
    def test_reset_empties_the_set(self) -> None:
        tracker = PlayerTracker()
        tracker.observe(join(NAME, ADDRESS))
        tracker.observe(join(OTHER, OTHER_ADDRESS))

        tracker.reset()
        assert tracker.count == 0

        tracker.observe(join(NAME, ADDRESS))
        assert tracker.count == 1


class TestLogging:
    """DEBUG events with counts only; no name, address or line (AC 5)."""

    def test_events_and_fields(self) -> None:
        tracker = PlayerTracker()
        with capture_logs() as logs:
            tracker.observe(join(NAME, ADDRESS))
            tracker.observe(join(NAME, ADDRESS))
            tracker.observe(rejoin(NAME))
            tracker.observe(leave(NAME))
            tracker.observe(leave(OTHER))
            tracker.observe(join(OTHER, OTHER_ADDRESS))
            tracker.reset()

        assert logs == [
            {"event": "player_joined", "log_level": "debug", "count": 1},
            {
                "event": "player_join_ignored",
                "log_level": "debug",
                "reason": "already_online",
                "count": 1,
            },
            {
                "event": "player_join_ignored",
                "log_level": "debug",
                "reason": "already_online",
                "count": 1,
            },
            {"event": "player_left", "log_level": "debug", "count": 0},
            {
                "event": "player_leave_ignored",
                "log_level": "debug",
                "reason": "not_online",
                "count": 0,
            },
            {"event": "player_joined", "log_level": "debug", "count": 1},
            {"event": "players_reset", "log_level": "debug", "previous_count": 1},
        ]
        captured = repr(logs)
        for secret in (NAME, OTHER, ADDRESS, OTHER_ADDRESS, "203.0.113", "198.51.100"):
            assert secret not in captured

    def test_unrelated_lines_log_nothing(self) -> None:
        tracker = PlayerTracker()
        with capture_logs() as logs:
            tracker.observe(f"18.11.2026 10:15:33 [Chat] {OTHER}: he joins.")
            tracker.observe(event("Saved player world data"))
        assert logs == []
