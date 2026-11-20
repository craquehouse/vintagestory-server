"""Cache eviction service for mod downloads.

This module provides LRU-based cache eviction for the mod download cache,
ensuring disk space is managed without manual intervention.
"""

import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import structlog

logger = structlog.get_logger()

STALE_TEMP_AGE = timedelta(hours=1)
"""A download's temporary file older than this was left by a crash (Epic 19 ADR-11).

A download reads with a 120-second timeout per read, so an active one is far younger.
"""


@dataclass
class CacheFileInfo:
    """Information about a cached file for eviction decisions."""

    path: Path
    """Path to the cached file."""

    size_bytes: int
    """Size of the file in bytes."""

    access_time: float
    """Last access time as Unix timestamp (atime)."""


@dataclass
class EvictionResult:
    """Result of a cache eviction operation."""

    files_evicted: int
    """Number of files evicted."""

    bytes_freed: int
    """Total bytes freed by eviction."""

    files_remaining: int
    """Number of files remaining in cache."""

    bytes_remaining: int
    """Total bytes remaining in cache."""


class CacheEvictionService:
    """LRU-based cache eviction service for mod downloads.

    Implements a Least Recently Used (LRU) eviction strategy based on
    file access times. When the cache exceeds the configured size limit,
    the oldest accessed files are evicted until the cache is under the limit.

    Downloads are cached as `mods/<fileid>/<name>` (Epic 19 ADR-11): files are
    counted one level below `mods/`, and a directory eviction empties is removed.

    Attributes:
        cache_dir: Directory containing cached files.
        max_size_bytes: Maximum cache size in bytes (0 to disable eviction).
    """

    # Suffix of a download that is still being written (ModApiClient's `<uuid>.tmp`):
    # never counted or evicted here, only removed by the stale-temp rule
    DOWNLOAD_IN_PROGRESS_SUFFIX = ".tmp"

    def __init__(
        self,
        cache_dir: Path,
        max_size_mb: int = 500,
    ) -> None:
        """Initialize the cache eviction service.

        Args:
            cache_dir: Directory containing cached mod files.
            max_size_mb: Maximum cache size in megabytes. Set to 0 to disable
                         eviction entirely.
        """
        self._cache_dir = cache_dir
        self._max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory path."""
        return self._cache_dir

    @property
    def max_size_bytes(self) -> int:
        """Get the maximum cache size in bytes."""
        return self._max_size_bytes

    @property
    def eviction_enabled(self) -> bool:
        """Check if eviction is enabled."""
        return self._max_size_bytes > 0

    def _get_cache_files(self) -> list[CacheFileInfo]:
        """Get information about all files in the cache (`mods/<fileid>/<name>`).

        A file directly under `mods/` (the layout before Story 19.4) is not counted.

        Returns:
            List of CacheFileInfo for all cache files, sorted by access time
            (oldest first for LRU eviction).
        """
        files: list[CacheFileInfo] = []

        if not self._cache_dir.exists():
            return files

        # Look in the mods subdirectory where ModApiClient stores downloads
        mods_cache = self._cache_dir / "mods"
        if not mods_cache.exists():
            return files

        # Every release file, whatever its type (Epic 24 ADR-5 decision 2)
        for path in mods_cache.glob("*/*"):
            if path.suffix == self.DOWNLOAD_IN_PROGRESS_SUFFIX or not path.is_file():
                continue
            try:
                stat = path.stat()
                files.append(
                    CacheFileInfo(
                        path=path,
                        size_bytes=stat.st_size,
                        access_time=stat.st_atime,
                    )
                )
            except OSError as e:
                logger.warning(
                    "cache_file_stat_failed",
                    path=str(path),
                    error=str(e),
                )

        # Sort by access time, oldest first (for LRU)
        files.sort(key=lambda f: f.access_time)
        return files

    def _remove_stale_temp_files(self) -> None:
        """Delete every `mods/*/*.tmp` older than STALE_TEMP_AGE, then its emptied directory.

        Younger ones may belong to a download still running and are kept.
        """
        mods_cache = self._cache_dir / "mods"
        if not mods_cache.is_dir():
            return
        cutoff = time.time() - STALE_TEMP_AGE.total_seconds()
        for path in mods_cache.glob("*/*.tmp"):
            try:
                if not path.is_file() or path.stat().st_mtime >= cutoff:
                    continue
                path.unlink()
                logger.info("cache_temp_file_removed", file=str(path.relative_to(self._cache_dir)))
            except OSError as e:
                logger.warning(
                    "cache_temp_file_not_removed",
                    file=str(path.relative_to(self._cache_dir)),
                    error=str(e),
                )
                continue
            self._remove_if_empty(path.parent)

    @staticmethod
    def _remove_if_empty(directory: Path) -> None:
        """Remove a file-ID directory that no longer holds anything."""
        try:
            directory.rmdir()
        except OSError as e:
            # Not empty, or already gone: either way nothing to do
            logger.debug("cache_directory_kept", path=str(directory), error=str(e))

    def get_cache_size(self) -> int:
        """Get the current total size of the cache in bytes.

        Returns:
            Total size of all cached files in bytes.
        """
        return sum(f.size_bytes for f in self._get_cache_files())

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with 'file_count', 'total_size_bytes', and
            'max_size_bytes' keys.
        """
        files = self._get_cache_files()
        return {
            "file_count": len(files),
            "total_size_bytes": sum(f.size_bytes for f in files),
            "max_size_bytes": self._max_size_bytes,
        }

    def evict_if_needed(self) -> EvictionResult:
        """Evict files if cache exceeds size limit.

        Uses LRU strategy - evicts oldest accessed files first until
        the cache is under the size limit. First removes temporary files a crashed
        download left, also when eviction is disabled (Epic 19 ADR-11 decision 4).

        Returns:
            EvictionResult with eviction statistics.
        """
        self._remove_stale_temp_files()
        if not self.eviction_enabled:
            files = self._get_cache_files()
            return EvictionResult(
                files_evicted=0,
                bytes_freed=0,
                files_remaining=len(files),
                bytes_remaining=sum(f.size_bytes for f in files),
            )

        files = self._get_cache_files()
        total_size = sum(f.size_bytes for f in files)

        if total_size <= self._max_size_bytes:
            logger.debug(
                "cache_within_limit",
                current_size_mb=total_size / (1024 * 1024),
                max_size_mb=self._max_size_bytes / (1024 * 1024),
            )
            return EvictionResult(
                files_evicted=0,
                bytes_freed=0,
                files_remaining=len(files),
                bytes_remaining=total_size,
            )

        # Need to evict - files are already sorted oldest first (by access time)
        files_evicted = 0
        bytes_freed = 0
        current_size = total_size

        for file_info in files:
            if current_size <= self._max_size_bytes:
                # We're under the limit, stop evicting
                break

            # Still over limit, evict this file (oldest first)
            try:
                file_info.path.unlink()
                logger.info(
                    "cache_evicted",
                    file=str(file_info.path.name),
                    size_bytes=file_info.size_bytes,
                    reason="size_limit",
                )
                self._remove_if_empty(file_info.path.parent)
                bytes_freed += file_info.size_bytes
                current_size -= file_info.size_bytes
                files_evicted += 1
            except OSError as e:
                logger.warning(
                    "cache_eviction_failed",
                    file=str(file_info.path),
                    error=str(e),
                )
                # File couldn't be deleted, it remains in cache

        # Calculate remaining files by re-scanning (accounts for failed deletions)
        remaining_files = self._get_cache_files()
        bytes_remaining = sum(f.size_bytes for f in remaining_files)

        if files_evicted > 0:
            logger.info(
                "cache_eviction_complete",
                files_evicted=files_evicted,
                bytes_freed=bytes_freed,
                bytes_remaining=bytes_remaining,
            )

        return EvictionResult(
            files_evicted=files_evicted,
            bytes_freed=bytes_freed,
            files_remaining=len(remaining_files),
            bytes_remaining=bytes_remaining,
        )

    def evict_all(self) -> EvictionResult:
        """Evict all files from the cache.

        This is a destructive operation that clears the entire cache.
        Useful for manual cache cleanup.

        Returns:
            EvictionResult with eviction statistics.
        """
        files = self._get_cache_files()
        files_evicted = 0
        bytes_freed = 0

        for file_info in files:
            try:
                file_info.path.unlink()
                logger.info(
                    "cache_evicted",
                    file=str(file_info.path.name),
                    size_bytes=file_info.size_bytes,
                    reason="manual_clear",
                )
                self._remove_if_empty(file_info.path.parent)
                bytes_freed += file_info.size_bytes
                files_evicted += 1
            except OSError as e:
                logger.warning(
                    "cache_eviction_failed",
                    file=str(file_info.path),
                    error=str(e),
                )

        return EvictionResult(
            files_evicted=files_evicted,
            bytes_freed=bytes_freed,
            files_remaining=len(files) - files_evicted,
            bytes_remaining=sum(f.size_bytes for f in files) - bytes_freed,
        )
