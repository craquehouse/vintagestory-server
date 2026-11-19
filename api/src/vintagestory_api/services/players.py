"""Players online, counted from the game's join and leave lines (Epic 22 ADR-1)."""

import re

import structlog

logger = structlog.get_logger()

# PROVISIONAL until the maintainer's sample lines (Story 22.1, Task 6.4): the game's
# Logger.Event lines are assumed to carry the "[Event]" tag (seen in v1.22.7 logs), with
# nothing but a timestamp (no "[") before it. A chat line carries its own tag first, so it
# never matches.
_EVENT_PREFIX = re.compile(r"^[^\[]*\[Event\] (?P<message>.+)$")

# The VintagestoryLib.dll v1.22.7 literals, anchored at the end of the message.
_JOIN = re.compile(r"^(?P<name>.+) \S+ joins\.$")  # '{0} {1} joins.'
_LEAVE = re.compile(r"^Player (?P<name>.+) left\.$")  # 'Player {0} left.'
_REJOIN = re.compile(r"^(?P<name>.+) joined again, killing previous client\.$")


class PlayerTracker:
    """The set of player names online. Names never leave this class.

    Logging carries counts only: no line at any level holds a player name, a player
    address or the game line (Story 22.1, "What is logged").
    """

    def __init__(self) -> None:
        self._online: set[str] = set()

    @property
    def count(self) -> int:
        """The number of names in the set, whatever the game state."""
        return len(self._online)

    def observe(self, line: str) -> None:
        """Update the set from one game output line; any other line changes nothing."""
        prefixed = _EVENT_PREFIX.match(line)
        if prefixed is None:
            return
        message = prefixed.group("message")

        rejoined = _REJOIN.match(message)
        if rejoined is not None:
            self._join(rejoined.group("name"))
            return

        joined = _JOIN.match(message)
        if joined is not None:
            self._join(joined.group("name"))
            return

        left = _LEAVE.match(message)
        if left is not None:
            self._leave(left.group("name"))

    def reset(self) -> None:
        """Empty the set: the game started, stopped or exited."""
        previous_count = len(self._online)
        self._online.clear()
        logger.debug("players_reset", previous_count=previous_count)

    def _join(self, name: str) -> None:
        if name in self._online:
            logger.debug("player_join_ignored", reason="already_online", count=self.count)
            return
        self._online.add(name)
        logger.debug("player_joined", count=self.count)

    def _leave(self, name: str) -> None:
        if name not in self._online:
            logger.debug("player_leave_ignored", reason="not_online", count=self.count)
            return
        self._online.discard(name)
        logger.debug("player_left", count=self.count)
