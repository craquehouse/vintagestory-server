"""Receiving a mod file from outside the mod database (Epic 28 ADR-3).

An uploaded body (Story 28.2) or a downloaded link (Story 28.3) is written to a working
file under `{cache_dir}/incoming/<random>/<name>`, outside the download cache that the
eviction scans (`{cache_dir}/mods`). `ModService.install_archive` then checks and places
it. The working folder is deleted on every exit, and any leftover at start-up.
"""

import re
import shutil
import uuid
from collections.abc import AsyncIterator, Generator
from contextlib import contextmanager
from pathlib import Path

import structlog

logger = structlog.get_logger()

INCOMING_DIR_NAME = "incoming"
"""Folder under the cache directory that holds files being received."""

MAX_ARCHIVE_NAME_BYTES = 255
"""A file name's limit on ext4 and most volumes, in bytes (UTF-8)."""

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class ModFileInvalidError(Exception):
    """The file is not a usable mod archive, or its name is not a safe archive name."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ModFileTooLargeError(Exception):
    """The file is over the size limit (VS_MOD_UPLOAD_MAX_MB)."""

    def __init__(self, limit_bytes: int) -> None:
        self.limit_bytes = limit_bytes
        limit_mb = limit_bytes // (1024 * 1024)
        super().__init__(f"The file is larger than the {limit_mb} MB limit (VS_MOD_UPLOAD_MAX_MB).")


def safe_archive_name(name: str) -> str | None:
    """The name if it is a safe base name for a mod archive, else None (ADR-3 decision 4).

    It must end in `.zip` (lowercase: the manager and the game on Linux load only that,
    Story 28.2 review), be at most 255 bytes in UTF-8 (the volume's limit), have no path
    separator or control character, and not start with a dot. Nothing is changed: a name
    that needs changing is refused, so the file is never stored under a name the admin
    did not give.
    """
    if not name or len(name.encode("utf-8")) > MAX_ARCHIVE_NAME_BYTES:
        return None
    if "/" in name or "\\" in name or _CONTROL_CHARS.search(name):
        return None
    if name.startswith(".") or not name.endswith(".zip"):
        return None
    return name


def incoming_root(cache_dir: Path) -> Path:
    return cache_dir / INCOMING_DIR_NAME


@contextmanager
def incoming_file(cache_dir: Path, name: str) -> Generator[Path]:
    """A path named `name` in a new working folder, deleted with the folder on exit.

    `name` must already have passed `safe_archive_name`.
    """
    folder = incoming_root(cache_dir) / uuid.uuid4().hex
    folder.mkdir(parents=True)
    try:
        yield folder / name
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def clear_incoming(cache_dir: Path) -> int:
    """Delete what a crash left in the incoming folder; returns how many entries went.

    Called once at start-up, before any request is served (Story 28.2 AC 7).
    """
    root = incoming_root(cache_dir)
    if not root.is_dir():
        return 0
    removed = 0
    for entry in root.iterdir():
        try:
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
            removed += 1
        except OSError as e:
            logger.warning("mod_incoming_leftover_not_removed", path=str(entry), error=str(e))
    return removed


async def write_limited(chunks: AsyncIterator[bytes], dest: Path, limit_bytes: int) -> int:
    """Write the chunks to `dest`, stopping with ModFileTooLargeError past the limit.

    Returns the number of bytes written. The caller deletes `dest` on any error (it lives
    in an `incoming_file` folder).
    """
    written = 0
    with dest.open("wb") as handle:
        async for chunk in chunks:
            written += len(chunk)
            if written > limit_bytes:
                raise ModFileTooLargeError(limit_bytes)
            handle.write(chunk)
    return written
