"""Latest versions cache service.

Story 8.2: Server Versions Check Job

This module provides an in-memory cache for storing the latest available
VintageStory server versions. The cache is updated by the server_versions_check
periodic job and consumed by the status API to show available updates.

The cache is a singleton to ensure consistent state across the application.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

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

    This cache stores the most recent stable and unstable versions
    discovered by the server_versions_check job. The data is used
    by the status API to inform administrators of available updates.

    Thread-safety note: This is a simple in-memory cache used by async
    code. The GIL provides sufficient protection for single-assignment
    operations on dataclass fields.
    """

    def __init__(self) -> None:
        """Initialize an empty cache."""
        self._versions = LatestVersions()

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

    def clear(self) -> None:
        """Clear all cached version data.

        Resets the cache to initial empty state. Primarily used for testing.
        """
        self._versions = LatestVersions()


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
