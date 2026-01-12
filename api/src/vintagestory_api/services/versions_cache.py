"""Latest versions cache service.

Story 8.2: Server Versions Check Job
Story 13.1: Server Versions API - Extended to cache full version lists

This module provides an in-memory cache for storing the latest available
VintageStory server versions. The cache is updated by the server_versions_check
periodic job and consumed by the status API to show available updates.

Story 13.1 extends this to also cache complete version lists for each channel,
enabling the /versions API endpoint to serve cached data.

The cache is a singleton to ensure consistent state across the application.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

# Module-level singleton instance
_versions_cache: LatestVersionsCache | None = None


@dataclass
class LatestVersions:
    """Container for cached latest version information.

    Attributes:
        stable_version: Latest stable version string (e.g., "1.21.3")
        unstable_version: Latest unstable/pre-release version (e.g., "1.22.0-pre.1")
        last_checked: Timestamp of last successful check (UTC)
    """

    stable_version: str | None = None
    unstable_version: str | None = None
    last_checked: datetime.datetime | None = None


class LatestVersionsCache:
    """In-memory cache for latest VintageStory version information.

    This cache stores:
    1. The most recent stable and unstable versions (for status API)
    2. Full version lists for each channel (for versions API, Story 13.1)

    The data is populated by the server_versions_check job and consumed
    by the status API and versions API.

    Thread-safety note: This is a simple in-memory cache used by async
    code. The GIL provides sufficient protection for single-assignment
    operations on dataclass fields.
    """

    def __init__(self) -> None:
        """Initialize an empty cache."""
        self._versions = LatestVersions()
        # Story 13.1: Full version lists by channel
        self._version_lists: dict[str, list[dict[str, Any]]] = {
            "stable": [],
            "unstable": [],
        }
        self._cached_at: datetime.datetime | None = None

    @property
    def cached_at(self) -> datetime.datetime | None:
        """Timestamp when full version lists were last cached."""
        return self._cached_at

    def get_latest_versions(self) -> LatestVersions:
        """Get cached latest versions.

        Returns:
            LatestVersions with current cached data (may have None fields
            if no versions have been fetched yet).
        """
        return self._versions

    def set_latest_versions(
        self,
        stable: str | None = None,
        unstable: str | None = None,
    ) -> None:
        """Update cached versions.

        Only updates fields that are provided (not None). Call with both
        parameters to update both versions, or with one to update just that
        channel.

        Args:
            stable: Latest stable version string, or None to skip update.
            unstable: Latest unstable version string, or None to skip update.
        """
        if stable is not None:
            self._versions.stable_version = stable
        if unstable is not None:
            self._versions.unstable_version = unstable
        # Only update timestamp when at least one value is provided
        if stable is not None or unstable is not None:
            self._versions.last_checked = datetime.datetime.now(datetime.UTC)

    # Story 13.1: Full version list methods

    def get_versions(self, channel: str) -> list[dict[str, Any]]:
        """Get cached full version list for a channel.

        Args:
            channel: Release channel ("stable" or "unstable").

        Returns:
            List of version dictionaries for the channel, or empty list
            if channel is invalid or no versions cached.
        """
        return self._version_lists.get(channel, [])

    def set_versions(self, channel: str, versions: list[dict[str, Any]]) -> None:
        """Cache full version list for a channel.

        Args:
            channel: Release channel ("stable" or "unstable").
            versions: List of version dictionaries to cache.
        """
        if channel in self._version_lists:
            self._version_lists[channel] = versions
            self._cached_at = datetime.datetime.now(datetime.UTC)

    def get_all_versions(self) -> dict[str, list[dict[str, Any]]]:
        """Get cached versions for all channels.

        Returns:
            Dictionary mapping channel names to version lists.
        """
        return {
            "stable": self._version_lists.get("stable", []),
            "unstable": self._version_lists.get("unstable", []),
        }

    def has_cached_versions(self) -> bool:
        """Check if any versions are cached.

        Returns:
            True if at least one channel has cached versions.
        """
        return bool(self._version_lists.get("stable")) or bool(
            self._version_lists.get("unstable")
        )

    def clear(self) -> None:
        """Clear all cached version data.

        Resets the cache to initial empty state. Primarily used for testing.
        """
        self._versions = LatestVersions()
        self._version_lists = {"stable": [], "unstable": []}
        self._cached_at = None


def get_versions_cache() -> LatestVersionsCache:
    """Get the singleton versions cache instance.

    Returns:
        The global LatestVersionsCache instance.
    """
    global _versions_cache
    if _versions_cache is None:
        _versions_cache = LatestVersionsCache()
    return _versions_cache


def reset_versions_cache() -> None:
    """Reset the singleton versions cache.

    Creates a fresh cache instance. Primarily used for testing to ensure
    test isolation.
    """
    global _versions_cache
    _versions_cache = None
