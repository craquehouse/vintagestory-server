"""Pending restart state tracking for server changes.

This module provides a simple state class to track when the game server
needs to be restarted due to configuration or mod changes.
"""

import structlog

logger = structlog.get_logger()


class PendingRestartState:
    """Tracks pending restart state due to server changes.

    When mods are enabled/disabled or certain configurations change,
    the game server needs to be restarted for changes to take effect.
    This class tracks whether a restart is pending and why.

    Attributes:
        pending_restart: Whether a restart is pending.
        pending_changes: List of reasons why restart is needed.
    """

    def __init__(self) -> None:
        """Initialize with no restart pending."""
        self._pending_restart = False
        self._pending_changes: list[str] = []

    @property
    def pending_restart(self) -> bool:
        """Whether a restart is pending."""
        return self._pending_restart

    @property
    def pending_changes(self) -> list[str]:
        """List of reasons why restart is needed."""
        return self._pending_changes.copy()

    def require_restart(self, reason: str) -> None:
        """Mark that a restart is required.

        Args:
            reason: Description of why restart is needed.
        """
        self._pending_restart = True
        self._pending_changes.append(reason)

        logger.info(
            "restart_required",
            reason=reason,
            total_pending_changes=len(self._pending_changes),
        )

    def clear_restart(self) -> None:
        """Clear the pending restart state.

        Called after a successful server restart.
        """
        if self._pending_restart:
            change_count = len(self._pending_changes)
            self._pending_restart = False
            self._pending_changes = []

            logger.info(
                "restart_cleared",
                cleared_changes=change_count,
            )
