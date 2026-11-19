"""Earlier versions of config files saved through the API (Story 23.6, Epic 23 ADR-7).

Each save through `PUT /config/files/{path}` (or a restore) keeps the text it replaces as
a revision in `vsmanager/state/config-history/<path relative to serverdata>/`: the bytes
exactly as they were in `<id>.json`, and `index.json` listing the revisions newest first
(id, saved_at, saved_by, size, sha256). The store is outside `serverdata`, so neither the
game nor mods load it. Only saves made through the API are recorded.

Revision ids are the UTC time of the save that replaced the text,
`YYYYMMDDTHHMMSSffffffZ`, with `-2`, `-3`... on a collision. An id is used to build a path
only when it is well formed and listed in the index. No log line or message holds an
absolute path or file content.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog
from pydantic import BaseModel, Field, ValidationError

logger = structlog.get_logger()

REVISION_ID = re.compile(r"^\d{8}T\d{12}Z(-\d+)?$")
"""The form of a revision id (Epic 23 ADR-7 decision 2)."""

INDEX_FILENAME = "index.json"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ConfigHistoryWriteError(Exception):
    """A revision could not be kept; the save that needed it must not go ahead."""

    def __init__(self, relative: str) -> None:
        self.relative = relative
        self.message = f"An earlier version of the file could not be kept: {relative}"
        super().__init__(self.message)


class RevisionInvalidError(Exception):
    """A revision id that is not of the form REVISION_ID."""

    def __init__(self, revision_id: str) -> None:
        self.revision_id = revision_id
        self.message = "Invalid revision id"
        super().__init__(self.message)


class RevisionNotFoundError(Exception):
    """A well-formed revision id that is not in the file's history."""

    def __init__(self, revision_id: str) -> None:
        self.revision_id = revision_id
        self.message = f"Revision not found: {revision_id}"
        super().__init__(self.message)


class Revision(BaseModel):
    """One kept version of a config file."""

    id: str
    saved_at: datetime
    saved_by: str
    size: int
    sha256: str


class RevisionIndex(BaseModel):
    """The shape of a file's `index.json`, newest first."""

    revisions: list[Revision] = Field(default_factory=list[Revision])


def _write_atomically(path: Path, data: bytes) -> None:
    """Write through a temporary file in the same directory, then replace."""
    temp = path.parent / f".{path.name}.{secrets.token_hex(6)}.tmp"
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError:
        temp.unlink(missing_ok=True)
        raise


class ConfigHistory:
    """The history store (Epic 23 ADR-7 decisions 1 to 5)."""

    def __init__(self, root: Path, *, now: Callable[[], datetime] = _utc_now) -> None:
        self._root = root
        self._now = now

    def _directory(self, relative: str) -> Path | None:
        """The file's history directory, or None for a path that cannot be one.

        `relative` comes from ConfigFilesService (a resolved path inside serverdata); this
        refuses anything else as a second line of defence.
        """
        parts = relative.split("/")
        if not relative or any(part in ("", ".", "..") for part in parts):
            return None
        directory = self._root.joinpath(*parts)
        try:
            directory.resolve().relative_to(self._root.resolve())
        except ValueError, OSError:
            return None
        return directory

    def _load(self, directory: Path) -> RevisionIndex:
        path = directory / INDEX_FILENAME
        if not path.exists():
            return RevisionIndex()
        try:
            return RevisionIndex.model_validate_json(path.read_bytes())
        except (OSError, ValidationError) as e:
            logger.warning("config_history_index_unreadable", error_type=type(e).__name__)
            return RevisionIndex()

    def _save(self, directory: Path, index: RevisionIndex) -> None:
        _write_atomically(
            directory / INDEX_FILENAME, index.model_dump_json(indent=2).encode("utf-8")
        )

    def _new_id(self, index: RevisionIndex) -> str:
        base = self._now().astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        taken = {revision.id for revision in index.revisions}
        candidate, suffix = base, 1
        while candidate in taken:
            suffix += 1
            candidate = f"{base}-{suffix}"
        return candidate

    def record(self, relative: str, data: bytes, saved_by: str) -> Revision:
        """Keep `data` as the newest revision of the file.

        Raises:
            ConfigHistoryWriteError: If it could not be kept (nothing of it is left).
        """
        directory = self._directory(relative)
        if directory is None:
            raise ConfigHistoryWriteError(relative)
        revision_path: Path | None = None
        try:
            directory.mkdir(parents=True, exist_ok=True)
            index = self._load(directory)
            revision = Revision(
                id=self._new_id(index),
                saved_at=self._now(),
                saved_by=saved_by,
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            )
            revision_path = directory / f"{revision.id}.json"
            with revision_path.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            self._save(directory, RevisionIndex(revisions=[revision, *index.revisions]))
        except OSError as e:
            if revision_path is not None:
                revision_path.unlink(missing_ok=True)
            logger.error(
                "config_history_write_failed",
                relative=relative,
                error_type=type(e).__name__,
                errno=e.errno,
            )
            raise ConfigHistoryWriteError(relative)
        logger.info("config_history_recorded", relative=relative, id=revision.id, size=len(data))
        return revision

    def list(self, relative: str) -> list[Revision]:
        """The file's revisions, newest first; [] when it has none."""
        directory = self._directory(relative)
        if directory is None or not directory.is_dir():
            return []
        return self._load(directory).revisions

    def _find(self, relative: str, revision_id: str) -> tuple[Path, RevisionIndex, Revision]:
        if not REVISION_ID.fullmatch(revision_id):
            raise RevisionInvalidError(revision_id)
        directory = self._directory(relative)
        if directory is None or not directory.is_dir():
            raise RevisionNotFoundError(revision_id)
        index = self._load(directory)
        for revision in index.revisions:
            if revision.id == revision_id:
                return directory, index, revision
        raise RevisionNotFoundError(revision_id)

    def read(self, relative: str, revision_id: str) -> tuple[Revision, bytes]:
        """A revision and its bytes.

        Raises:
            RevisionInvalidError: If the id is malformed.
            RevisionNotFoundError: If it is not in the history (or its file is gone).
        """
        directory, _, revision = self._find(relative, revision_id)
        try:
            return revision, (directory / f"{revision.id}.json").read_bytes()
        except OSError:
            raise RevisionNotFoundError(revision_id)

    def remove(self, relative: str, revision_id: str) -> None:
        """Remove a revision (its index entry, then its file)."""
        directory, index, revision = self._find(relative, revision_id)
        remaining = [r for r in index.revisions if r.id != revision.id]
        self._save(directory, RevisionIndex(revisions=remaining))
        (directory / f"{revision.id}.json").unlink(missing_ok=True)

    def prune(self, relative: str, keep_count: int, max_age_days: int) -> list[str]:
        """Keep the newest `keep_count` revisions, and drop those older than `max_age_days`.

        `max_age_days` 0 keeps any age; the newest revision is never removed by age
        (Epic 23 ADR-7 decision 5). Returns the removed ids.
        """
        directory = self._directory(relative)
        if directory is None or not directory.is_dir():
            return []
        index = self._load(directory)
        kept = index.revisions[: max(keep_count, 1)]
        if max_age_days > 0 and kept:
            cutoff = self._now() - timedelta(days=max_age_days)
            kept = [kept[0], *(r for r in kept[1:] if r.saved_at >= cutoff)]
        kept_ids = {r.id for r in kept}
        removed = [r.id for r in index.revisions if r.id not in kept_ids]
        if not removed:
            return []
        self._save(directory, RevisionIndex(revisions=kept))
        for revision_id in removed:
            (directory / f"{revision_id}.json").unlink(missing_ok=True)
        logger.info("config_history_pruned", relative=relative, removed=len(removed))
        return removed
