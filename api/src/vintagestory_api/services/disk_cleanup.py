"""Daily disk cleanup of the game's backups, when asked (Epic 22 ADR-9, as amended 2026-11-19).

Story 22.4: Log Archive and Backup Cleanup

Only `serverdata/Backups/` is ever touched: the `/genbackup` files. When
`backup_keep_count` is above 0, only that many newest files are kept; with 0 (the default)
the directory is not even read.

The game's log archives (`Logs/Archive/`) are not touched: the game keeps at most 5 itself,
and the maintainer dropped the manager's archive cleanup (2026-11-19). Nothing reached
through a symbolic link is deleted, directories are left alone, and each path is checked
again right before it is deleted.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger()

BACKUP_DIR = Path("Backups")
_KIND = "backup"


@dataclass(frozen=True)
class CleanupLimits:
    """The cleanup setting, read from the API settings at each run."""

    backup_keep_count: int
    """Newest files kept in Backups/; 0 keeps all (Backups/ is not read)."""


@dataclass
class CleanupResult:
    """What one cleanup run deleted."""

    backups_deleted: int = 0
    backup_bytes: int = 0
    errors: int = 0


def _scan(directory: Path) -> list[os.DirEntry[str]]:
    """The entries of a directory (a seam for tests)."""
    with os.scandir(directory) as entries:
        return list(entries)


def _delete_file(path: Path) -> None:
    """Delete a backup file (a seam for tests)."""
    path.unlink()


def _error_fields(error: OSError) -> dict[str, object]:
    """The error's text without its file name: str(error) holds the absolute path."""
    return {"error": error.strerror or type(error).__name__, "errno": error.errno}


def _file_size(path: Path) -> int:
    try:
        return path.lstat().st_size
    except OSError:
        return 0


class DiskCleanupService:
    """Deletes old backup files under `serverdata/Backups/` when a limit is set."""

    def __init__(self, serverdata_dir: Path) -> None:
        """Args:
        serverdata_dir: The game's data path (`Settings.serverdata_dir`).
        """
        self._serverdata_dir = serverdata_dir

    def run(self, limits: CleanupLimits) -> CleanupResult:
        """Run the backup pass when a limit is set, and log a summary."""
        result = CleanupResult()
        backups_kept = 0
        if limits.backup_keep_count > 0:
            backups_kept = self._clean_backups(limits, result)
        logger.info(
            "disk_cleanup_finished",
            backups_deleted=result.backups_deleted,
            backup_bytes=result.backup_bytes,
            backups_kept=backups_kept,
            errors=result.errors,
            backup_keep_count=limits.backup_keep_count,
        )
        return result

    def _target(self) -> Path | None:
        """`Backups/`, or None when it is missing or a link."""
        target = self._serverdata_dir / BACKUP_DIR
        if target.is_symlink():
            logger.warning("disk_cleanup_skipped", path=BACKUP_DIR.as_posix(), reason="symlink")
            return None
        if not target.exists():
            logger.debug("disk_cleanup_dir_missing", path=BACKUP_DIR.as_posix())
            return None
        return target

    def _failed(self, relative: Path, error: OSError, result: CleanupResult) -> None:
        result.errors += 1
        logger.warning(
            "disk_cleanup_delete_failed",
            kind=_KIND,
            path=relative.as_posix(),
            **_error_fields(error),
        )

    def _is_inside(self, path: Path, target: Path) -> bool:
        """The path check before every deletion: a direct child of the target, under
        serverdata, and not a link."""
        try:
            target_resolved = target.resolve()
            inside = target_resolved.is_relative_to(self._serverdata_dir.resolve())
            return inside and path.resolve().parent == target_resolved and not path.is_symlink()
        except OSError:
            return False

    def _delete(self, path: Path, target: Path, result: CleanupResult) -> bool:
        """Check and delete one file; True when it was deleted."""
        relative = BACKUP_DIR / path.name
        if not self._is_inside(path, target):
            logger.warning("disk_cleanup_skipped", path=relative.as_posix(), reason="outside")
            return False
        size = _file_size(path)
        try:
            _delete_file(path)
        except OSError as e:
            self._failed(relative, e, result)
            return False
        result.backups_deleted += 1
        result.backup_bytes += size
        logger.info("disk_cleanup_deleted", kind=_KIND, path=relative.as_posix(), bytes=size)
        return True

    def _clean_backups(self, limits: CleanupLimits, result: CleanupResult) -> int:
        """Keep only the newest backup files; returns the number of files left."""
        target = self._target()
        if target is None:
            return 0
        try:
            entries = _scan(target)
        except OSError as e:
            self._failed(BACKUP_DIR, e, result)
            return 0

        candidates: list[tuple[float, str]] = []
        kept = 0
        for entry in entries:
            relative = BACKUP_DIR / entry.name
            if entry.is_symlink():
                logger.warning("disk_cleanup_skipped", path=relative.as_posix(), reason="symlink")
                continue
            if not entry.is_file(follow_symlinks=False):
                logger.debug("disk_cleanup_skipped", path=relative.as_posix(), reason="not_a_file")
                continue
            try:
                mtime = entry.stat(follow_symlinks=False).st_mtime
            except OSError as e:
                # Not deleted: without its time it cannot be ordered.
                self._failed(relative, e, result)
                kept += 1
                continue
            candidates.append((mtime, entry.name))

        # Newest first by modification time, ties by name.
        candidates.sort(reverse=True)
        kept += min(limits.backup_keep_count, len(candidates))
        for _mtime, name in candidates[limits.backup_keep_count :]:
            if not self._delete(target / name, target, result):
                kept += 1
        return kept
