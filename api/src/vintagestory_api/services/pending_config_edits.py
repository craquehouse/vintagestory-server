"""Restart-required game settings saved while the game server runs (Epic 22 ADR-15).

The game rewrites `serverconfig.json` with its own in-memory values after a live
`/serverconfig` command, so a `Port` or `Ip` change written to the file while the game
runs can be lost before the next start. This store keeps such edits in
`vsmanager/state/pending-config-edits.json`; `reapply_edits` writes them to
`serverconfig.json` again (after an exit, before every start and at API start).

Story 22.7: Restart-required settings survive a live change (FR307)
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import structlog
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from vintagestory_api.services.game_config import LIVE_SETTINGS

logger = structlog.get_logger()

PENDING_CONFIG_EDITS_FILENAME = "pending-config-edits.json"
"""The store's file in the state directory (ADR-15 decision 2)."""

# "file_edited": a serverconfig.json save through the API changed the key (Story 23.4)
DropReason = Literal["started", "changed_again", "file_edited"]

EditValue = str | int | float | bool | None

_JSON_OBJECT: TypeAdapter[dict[str, object]] = TypeAdapter(dict[str, object])
"""serverconfig.json must be a JSON object; its keys are always strings."""


class PendingConfigEdit(BaseModel):
    """One restart-required value saved while a game process lived."""

    value: EditValue
    recorded_at: datetime


class PendingConfigEditsFile(BaseModel):
    """The shape of `pending-config-edits.json`."""

    edits: dict[str, PendingConfigEdit] = Field(default_factory=dict)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class PendingConfigEdits:
    """The pending restart-required edits, kept in the state directory.

    The file is read on first use, not at construction (controller decision, Story 22.7
    validation judgement call 1), so building the service that owns the store reads
    nothing from disk.
    """

    def __init__(self, state_dir: Path, *, now: Callable[[], datetime] = _utc_now) -> None:
        self._path = state_dir / PENDING_CONFIG_EDITS_FILENAME
        self._now = now
        self._edits: dict[str, PendingConfigEdit] | None = None

    @property
    def path(self) -> Path:
        """The store's file."""
        return self._path

    @property
    def edits(self) -> dict[str, PendingConfigEdit]:
        """A copy of the pending edits, by setting key."""
        return dict(self._loaded())

    def record(self, key: str, value: EditValue) -> None:
        """Record (or replace) the pending edit of a key and save."""
        edits = self._loaded()
        edits[key] = PendingConfigEdit(value=value, recorded_at=self._now())
        self._save()
        logger.info("pending_config_edit_recorded", key=key)

    def drop(self, keys: Iterable[str], reason: DropReason) -> None:
        """Remove the edits of these keys; save and log only when one was removed."""
        edits = self._loaded()
        removed = [key for key in keys if key in edits]
        if not removed:
            return
        for key in removed:
            del edits[key]
        self._save()
        logger.info("pending_config_edits_dropped", keys=removed, reason=reason)

    def drop_if_unchanged(
        self, written: Mapping[str, PendingConfigEdit], reason: DropReason
    ) -> None:
        """Remove each edit that is still the one in `written` (value and recorded_at).

        An edit recorded again since (a newer one) is kept, and one dropped since stays dropped.
        """
        edits = self._loaded()
        self.drop([key for key, edit in written.items() if edits.get(key) == edit], reason)

    def _loaded(self) -> dict[str, PendingConfigEdit]:
        if self._edits is None:
            self._edits = self._load()
        return self._edits

    def _load(self) -> dict[str, PendingConfigEdit]:
        if not self._path.exists():
            return {}
        try:
            data = PendingConfigEditsFile.model_validate_json(self._path.read_text())
        except (OSError, ValidationError) as e:
            logger.warning("pending_config_edits_unreadable", error_type=type(e).__name__)
            return {}
        edits: dict[str, PendingConfigEdit] = {}
        for key, edit in data.edits.items():
            if key not in LIVE_SETTINGS:
                logger.warning("pending_config_edit_unknown_key", key=key)
                continue
            edits[key] = edit
        return edits

    def _save(self) -> None:
        """Write the file atomically; a failure is logged and the edits stay in memory."""
        data = PendingConfigEditsFile(edits=self._loaded())
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temp = self._path.with_suffix(".tmp")
            temp.write_text(data.model_dump_json(indent=2))
            temp.rename(self._path)
        except OSError as e:
            # No str(e): its text holds the absolute path (Story 22.4)
            logger.error(
                "pending_config_edits_save_failed",
                error_type=type(e).__name__,
                errno=e.errno,
                strerror=e.strerror,
            )


def reapply_edits(config_path: Path, edits: Mapping[str, PendingConfigEdit]) -> list[str]:
    """Write the pending edits into `serverconfig.json` (ADR-15 decision 3).

    Returns the keys whose value changed. Nothing is touched when there are no edits or the
    file does not exist (it is not created), and nothing is written when every value is
    already equal. `OSError` and `ValueError` (invalid JSON, not an object) propagate.
    Never reads `VS_CFG_*` (decision 6).
    """
    if not edits or not config_path.exists():
        return []
    config = _JSON_OBJECT.validate_python(json.loads(config_path.read_text()))
    changed: list[str] = []
    for key, edit in edits.items():
        if key not in config or config[key] != edit.value:
            config[key] = edit.value
            changed.append(key)
    if not changed:
        return []
    temp = config_path.with_suffix(".tmp")
    temp.write_text(json.dumps(config, indent=2))
    temp.rename(config_path)
    return changed
