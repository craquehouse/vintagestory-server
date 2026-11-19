"""Daily disk cleanup of the game's log archives and, when asked, its backups (Epic 22 ADR-9).

Story 22.4: Log Archive and Backup Cleanup

Only two directories under `serverdata` are ever touched:

- `Logs/Archive/`: the game moves the previous run's logs there at every start, into a
  directory named after that run's start time (`YYYY-MM-DD_HH_MM_SS`, the game's local
  time). Archives older than the retention are deleted, the newest ones always kept.
- `Backups/`: `/genbackup` files. Only the newest `backup_keep_count` files are kept, and
  only when that limit is above 0.

Nothing reached through a symbolic link is deleted, names that are not the game's are
left alone, and each path is checked again right before it is deleted.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import structlog

logger = structlog.get_logger()

ARCHIVE_DIR = Path("Logs") / "Archive"
BACKUP_DIR = Path("Backups")
# [0-9] and fullmatch: \d matches any Unicode digit and $ matches before a trailing newline.
_ARCHIVE_NAME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}")
_ARCHIVE_TIME_FORMAT = "%Y-%m-%d_%H_%M_%S"

CleanupKind = Literal["log_archive", "backup"]


@dataclass(frozen=True)
class CleanupLimits:
    """The three cleanup settings, read from the API settings at each run."""

    log_archive_retention_days: int
    """Archives older than this many days are deleted; 0 keeps all."""

    log_archive_keep_min: int
    """The newest archives always kept; the newest one is kept also with 0."""

    backup_keep_count: int
    """Newest files kept in Backups/; 0 keeps all (Backups/ is not read)."""


@dataclass
class CleanupResult:
    """What one cleanup run deleted."""

    archives_deleted: int = 0
    archive_bytes: int = 0
    backups_deleted: int = 0
    backup_bytes: int = 0
    errors: int = 0


def _scan(directory: Path) -> list[os.DirEntry[str]]:
    """The entries of a directory (a seam for tests)."""
    with os.scandir(directory) as entries:
        return list(entries)


def _delete_tree(path: Path) -> None:
    """Delete an archive directory (a seam for tests).

    No `onexc`, `onerror` or `ignore_errors`: a link at the top must raise, and the first
    error must reach the caller rather than leave a partial deletion unreported.
    """
    shutil.rmtree(path)


def _delete_file(path: Path) -> None:
    """Delete a backup file (a seam for tests)."""
    path.unlink()


def _error_fields(error: OSError) -> dict[str, object]:
    """The error's text without its file name: str(error) holds the absolute path."""
    return {"error": error.strerror or type(error).__name__, "errno": error.errno}


def _archive_time(name: str) -> datetime | None:
    """The start time in an archive's name, or None when the name is not an archive's."""
    if not _ARCHIVE_NAME.fullmatch(name):
        return None
    try:
        return datetime.strptime(name, _ARCHIVE_TIME_FORMAT)
    except ValueError:
        return None


def _tree_size(path: Path) -> int:
    """Bytes of the regular files under a directory, links not followed."""
    total = 0
    for directory, _dir_names, file_names in os.walk(path, followlinks=False):
        for name in file_names:
            try:
                info = (Path(directory) / name).lstat()
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
    return total


def _file_size(path: Path) -> int:
    try:
        return path.lstat().st_size
    except OSError:
        return 0


class DiskCleanupService:
    """Deletes old log archives and, when asked, old backups under `serverdata`."""

    def __init__(self, serverdata_dir: Path, *, now: Callable[[], datetime] = datetime.now) -> None:
        """Args:
        serverdata_dir: The game's data path (`Settings.serverdata_dir`).
        now: The naive local wall-clock time, the clock the game writes archive names in.
        """
        self._serverdata_dir = serverdata_dir
        self._now = now

    def run(self, limits: CleanupLimits) -> CleanupResult:
        """Run the archive pass, then the backup pass, and log a summary."""
        result = CleanupResult()
        archives_kept = 0
        backups_kept = 0
        if limits.log_archive_retention_days > 0:
            archives_kept = self._clean_archives(limits, result)
        if limits.backup_keep_count > 0:
            backups_kept = self._clean_backups(limits, result)
        logger.info(
            "disk_cleanup_finished",
            archives_deleted=result.archives_deleted,
            archive_bytes=result.archive_bytes,
            archives_kept=archives_kept,
            backups_deleted=result.backups_deleted,
            backup_bytes=result.backup_bytes,
            backups_kept=backups_kept,
            errors=result.errors,
            log_archive_retention_days=limits.log_archive_retention_days,
            log_archive_keep_min=limits.log_archive_keep_min,
            backup_keep_count=limits.backup_keep_count,
        )
        return result

    def _target(self, relative: Path) -> Path | None:
        """The target directory, or None when it (or a parent under serverdata) is a link
        or missing."""
        current = self._serverdata_dir
        if not current.is_dir():
            logger.debug("disk_cleanup_dir_missing", path=relative.as_posix())
            return None
        walked = Path()
        for part in relative.parts:
            current = current / part
            walked = walked / part
            if current.is_symlink():
                logger.warning("disk_cleanup_skipped", path=walked.as_posix(), reason="symlink")
                return None
            if not current.exists():
                logger.debug("disk_cleanup_dir_missing", path=relative.as_posix())
                return None
        return current

    def _list(
        self, target: Path, relative: Path, kind: CleanupKind, result: CleanupResult
    ) -> list[os.DirEntry[str]] | None:
        try:
            return _scan(target)
        except OSError as e:
            result.errors += 1
            logger.warning(
                "disk_cleanup_delete_failed",
                kind=kind,
                path=relative.as_posix(),
                **_error_fields(e),
            )
            return None

    def _is_inside(self, path: Path, target: Path) -> bool:
        """The path check before every deletion: a direct child of the target, under
        serverdata, and not a link."""
        try:
            target_resolved = target.resolve()
            inside = target_resolved.is_relative_to(self._serverdata_dir.resolve())
            return inside and path.resolve().parent == target_resolved and not path.is_symlink()
        except OSError:
            return False

    def _delete(
        self,
        path: Path,
        target: Path,
        relative: Path,
        kind: CleanupKind,
        result: CleanupResult,
    ) -> bool:
        """Check and delete one entry; True when it was deleted."""
        if not self._is_inside(path, target):
            logger.warning("disk_cleanup_skipped", path=relative.as_posix(), reason="outside")
            return False
        size = _tree_size(path) if kind == "log_archive" else _file_size(path)
        try:
            if kind == "log_archive":
                _delete_tree(path)
            else:
                _delete_file(path)
        except OSError as e:
            result.errors += 1
            logger.warning(
                "disk_cleanup_delete_failed",
                kind=kind,
                path=relative.as_posix(),
                **_error_fields(e),
            )
            return False
        if kind == "log_archive":
            result.archives_deleted += 1
            result.archive_bytes += size
        else:
            result.backups_deleted += 1
            result.backup_bytes += size
        logger.info("disk_cleanup_deleted", kind=kind, path=relative.as_posix(), bytes=size)
        return True

    def _clean_archives(self, limits: CleanupLimits, result: CleanupResult) -> int:
        """Delete old archives; returns the number of archives left."""
        target = self._target(ARCHIVE_DIR)
        if target is None:
            return 0
        entries = self._list(target, ARCHIVE_DIR, "log_archive", result)
        if entries is None:
            return 0

        candidates: list[tuple[datetime, str, os.DirEntry[str]]] = []
        for entry in entries:
            relative = ARCHIVE_DIR / entry.name
            if entry.is_symlink():
                logger.warning("disk_cleanup_skipped", path=relative.as_posix(), reason="symlink")
                continue
            name_time = _archive_time(entry.name)
            if name_time is None or not entry.is_dir(follow_symlinks=False):
                logger.debug(
                    "disk_cleanup_skipped", path=relative.as_posix(), reason="not_an_archive"
                )
                continue
            candidates.append((name_time, entry.name, entry))

        # Newest first by the time in the name; the newest is never deleted (decision 1).
        candidates.sort(key=lambda candidate: (candidate[0], candidate[1]), reverse=True)
        keep = max(limits.log_archive_keep_min, 1)
        kept = min(keep, len(candidates))
        cutoff = self._now() - timedelta(days=limits.log_archive_retention_days)
        for name_time, name, entry in candidates[keep:]:
            relative = ARCHIVE_DIR / name
            try:
                mtime = datetime.fromtimestamp(entry.stat(follow_symlinks=False).st_mtime)
            except OSError as e:
                result.errors += 1
                kept += 1
                logger.warning(
                    "disk_cleanup_delete_failed",
                    kind="log_archive",
                    path=relative.as_posix(),
                    **_error_fields(e),
                )
                continue
            # The name is the archived run's start time; the directory is made when the run
            # is archived, so the later of the two is the archive's age (decision 2).
            if max(name_time, mtime) >= cutoff:
                kept += 1
                continue
            if not self._delete(target / name, target, relative, "log_archive", result):
                kept += 1
        return kept

    def _clean_backups(self, limits: CleanupLimits, result: CleanupResult) -> int:
        """Keep only the newest backup files; returns the number of files left."""
        target = self._target(BACKUP_DIR)
        if target is None:
            return 0
        entries = self._list(target, BACKUP_DIR, "backup", result)
        if entries is None:
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
                result.errors += 1
                kept += 1
                logger.warning(
                    "disk_cleanup_delete_failed",
                    kind="backup",
                    path=relative.as_posix(),
                    **_error_fields(e),
                )
                continue
            candidates.append((mtime, entry.name))

        candidates.sort(reverse=True)
        kept += min(limits.backup_keep_count, len(candidates))
        for _mtime, name in candidates[limits.backup_keep_count :]:
            relative = BACKUP_DIR / name
            if not self._delete(target / name, target, relative, "backup", result):
                kept += 1
        return kept
