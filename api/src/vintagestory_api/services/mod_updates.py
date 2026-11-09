"""Mod update detection (Epic 14, Story 14.1).

Rules are defined in _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md,
ADR-1. "Newer" means earlier in the mod database's release list (newest first); version
strings are only compared for the base-version check on mods already on a pre-release.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

import structlog
from pydantic import ValidationError

from vintagestory_api.config import Settings
from vintagestory_api.models.mod_updates import (
    ModUpdatesFile,
    ModUpdateStatusItem,
    StoredModRecord,
    StoredRelease,
    UnknownReason,
    UpdateState,
)
from vintagestory_api.models.mods import ModInfo
from vintagestory_api.services.mod_api import (
    CompatibilityStatus,
    ExternalApiError,
    ModApiClient,
    check_compatibility,
)

logger = structlog.get_logger()

STORE_FILENAME = "mod-updates.json"


def is_prerelease(version: str) -> bool:
    """Whether a mod version is a pre-release (contains `-`, such as `2.0.0-rc.1`)."""
    return "-" in version


def parse_base_version(version: str) -> tuple[int, ...] | None:
    """Parse the base version: the part before any `-`, as dot-separated integers.

    Returns None if the base is empty or any part is not a plain number.
    """
    base = version.split("-", 1)[0]
    parts = base.split(".")
    if not base or not all(part.isascii() and part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def _base_at_least(version: str, minimum: tuple[int, ...]) -> bool:
    base = parse_base_version(version)
    if base is None:
        return False
    width = max(len(base), len(minimum))
    return base + (0,) * (width - len(base)) >= minimum + (0,) * (width - len(minimum))


@dataclass(frozen=True)
class UpdateEvaluation:
    """Result of evaluating one installed mod against its mod database releases."""

    status: UpdateState
    offered: StoredRelease | None = None
    offered_compatibility: CompatibilityStatus | None = None
    reason: UnknownReason | None = None


def evaluate_update(
    modid: str,
    installed_version: str,
    releases: list[StoredRelease],
    game_version: str,
) -> UpdateEvaluation:
    """Decide the update status of an installed mod.

    Args:
        modid: The installed mod's modid.
        installed_version: The installed mod's version.
        releases: The mod database entry's releases, newest first.
        game_version: The installed game version, or "" if no server is installed.

    If a modid lists the same version more than once, the first (newest) occurrence is
    treated as the installed release.
    """
    own = [r for r in releases if r.modidstr == modid]
    installed_index = next(
        (i for i, r in enumerate(own) if r.modversion == installed_version), None
    )
    if installed_index is None:
        return UpdateEvaluation("unknown", reason="installed_release_not_listed")

    newer = own[:installed_index]
    if is_prerelease(installed_version):
        installed_base = parse_base_version(installed_version)
        if installed_base is None:
            return UpdateEvaluation("unknown", reason="version_unparsable")
        eligible = [r for r in newer if _base_at_least(r.modversion, installed_base)]
    else:
        eligible = [r for r in newer if not is_prerelease(r.modversion)]

    if not eligible:
        return UpdateEvaluation("up_to_date")

    classified = [(r, check_compatibility({"tags": r.tags}, game_version)) for r in eligible]
    preference: tuple[CompatibilityStatus, ...] = ("compatible", "not_verified")
    for wanted in preference:
        for candidate, compatibility in classified:
            if compatibility == wanted:
                return UpdateEvaluation(
                    "update_available", offered=candidate, offered_compatibility=wanted
                )
    return UpdateEvaluation("blocked")


class ModUpdateStore:
    """Persistent mod database data for update detection (ADR-4).

    Stores release data rather than final statuses, so status is computed at read
    time against the current installed mods and game version.
    """

    def __init__(self, state_dir: Path) -> None:
        self._path = state_dir / STORE_FILENAME
        self._data = self._load()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def last_full_check(self) -> datetime | None:
        return self._data.last_full_check

    @last_full_check.setter
    def last_full_check(self, value: datetime | None) -> None:
        self._data.last_full_check = value

    def get(self, modid: str) -> StoredModRecord | None:
        return self._data.mods.get(modid)

    def set(self, modid: str, record: StoredModRecord) -> None:
        self._data.mods[modid] = record

    def lookup_error(self, modid: str) -> str | None:
        """The last lookup failure for a mod that has no stored record."""
        return self._data.lookup_errors.get(modid)

    def set_lookup_error(self, modid: str, error: str) -> None:
        self._data.lookup_errors[modid] = error

    def clear_lookup_error(self, modid: str) -> None:
        self._data.lookup_errors.pop(modid, None)

    def prune(self, keep: set[str]) -> None:
        """Drop records and lookup errors for modids not in `keep`."""
        for mods in (self._data.mods, self._data.lookup_errors):
            for modid in [m for m in mods if m not in keep]:
                del mods[modid]

    def save(self) -> None:
        """Write the store atomically: temp file, then rename."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_suffix(".tmp")
        temp.write_text(self._data.model_dump_json(indent=2))
        temp.rename(self._path)

    def _load(self) -> ModUpdatesFile:
        if not self._path.exists():
            return ModUpdatesFile()
        try:
            return ModUpdatesFile.model_validate_json(self._path.read_text())
        except (OSError, ValidationError) as e:
            logger.warning("mod_update_store_unreadable", path=str(self._path), error=str(e))
            return ModUpdatesFile()


def _status_item(
    mod: ModInfo,
    status: UpdateState,
    *,
    record: StoredModRecord | None = None,
    reason: UnknownReason | None = None,
    offered: StoredRelease | None = None,
    compatibility: CompatibilityStatus | None = None,
    error: str | None = None,
) -> ModUpdateStatusItem:
    return ModUpdateStatusItem(
        slug=mod.slug,
        name=mod.name,
        installed_version=mod.version,
        status=status,
        reason=reason,
        offered_version=offered.modversion if offered else None,
        offered_compatibility=compatibility,
        offered_prerelease=is_prerelease(offered.modversion) if offered else None,
        checked_at=record.checked_at if record else None,
        error=record.error if record else error,
    )


def build_status_items(
    mods: list[ModInfo], store: ModUpdateStore, game_version: str
) -> list[ModUpdateStatusItem]:
    """Compute update status for each installed mod from stored mod database data."""
    items: list[ModUpdateStatusItem] = []
    for mod in mods:
        record = store.get(mod.slug)
        if record is None:
            error = store.lookup_error(mod.slug)
            items.append(_status_item(mod, "unknown", reason="not_checked", error=error))
        elif not record.found:
            items.append(_status_item(mod, "unknown", record=record, reason="not_in_database"))
        else:
            result = evaluate_update(mod.slug, mod.version, record.releases, game_version)
            items.append(
                _status_item(
                    mod,
                    result.status,
                    record=record,
                    reason=result.reason,
                    offered=result.offered,
                    compatibility=result.offered_compatibility,
                )
            )
    return items


class InstalledModSource(Protocol):
    """What the update service needs from ModService."""

    @property
    def api_client(self) -> ModApiClient: ...

    def list_mods(self) -> list[ModInfo]: ...


class ModUpdateCheckInProgressError(Exception):
    """Raised when a check is requested while another is running."""


@dataclass(frozen=True)
class CheckSummary:
    """Outcome of one update check."""

    checked: int
    failed: int
    failed_slugs: list[str] = field(default_factory=lambda: list[str]())


class ModUpdateService:
    """Checks the mod database for updates and reports update status (Story 14.1)."""

    def __init__(
        self,
        store: ModUpdateStore,
        mod_source: InstalledModSource,
        game_version_provider: Callable[[], str | None],
    ) -> None:
        self._store = store
        self._mod_source = mod_source
        self._game_version_provider = game_version_provider
        self._check_lock = asyncio.Lock()

    @property
    def store(self) -> ModUpdateStore:
        return self._store

    def game_version(self) -> str:
        """The installed game version, or "" if no server is installed."""
        return self._game_version_provider() or ""

    def get_status(self) -> list[ModUpdateStatusItem]:
        """Update status for every installed mod, computed from stored data."""
        return build_status_items(self._mod_source.list_mods(), self._store, self.game_version())

    async def check(self) -> CheckSummary:
        """Refresh release data for every installed mod from the mod database.

        A failed lookup keeps that mod's previous data and records the error.
        `last_full_check` is only updated when every lookup succeeds. Records for
        mods that are no longer installed are removed.

        Raises:
            ModUpdateCheckInProgressError: If a check is already running.
        """
        if self._check_lock.locked():
            raise ModUpdateCheckInProgressError()
        async with self._check_lock:
            mods = self._mod_source.list_mods()
            logger.info("mod_update_check_started", mod_count=len(mods))
            failed: list[str] = []
            for mod in mods:
                if not await self._check_one(mod.slug):
                    failed.append(mod.slug)
            self._store.prune({mod.slug for mod in mods})
            if not failed:
                self._store.last_full_check = datetime.now(UTC)
            try:
                self._store.save()
            except OSError as e:
                # Results stay available in memory until restart.
                logger.error(
                    "mod_update_store_save_failed", path=str(self._store.path), error=str(e)
                )
            logger.info("mod_update_check_complete", checked=len(mods), failed=len(failed))
            return CheckSummary(checked=len(mods), failed=len(failed), failed_slugs=failed)

    async def _check_one(self, slug: str) -> bool:
        """Refresh one mod. Returns False if the lookup failed."""
        try:
            data = await self._mod_source.api_client.get_mod(slug)
            record = _record_from_payload(data)
        except (ExternalApiError, ValueError, TypeError) as e:
            # ValueError covers a non-JSON body and pydantic validation errors;
            # TypeError covers payloads with the wrong shape.
            logger.warning("mod_update_lookup_failed", slug=slug, error=str(e))
            previous = self._store.get(slug)
            if previous is not None:
                self._store.set(slug, previous.model_copy(update={"error": str(e)}))
            else:
                self._store.set_lookup_error(slug, str(e))
            return False

        self._store.set(slug, record)
        self._store.clear_lookup_error(slug)
        return True


def _record_from_payload(data: object) -> StoredModRecord:
    """Build a stored record from a get_mod() result (None means not found).

    Raises:
        TypeError: If the payload or its release list has the wrong shape.
        ValueError: If a release has unusable field values.
    """
    now = datetime.now(UTC)
    if data is None:
        return StoredModRecord(checked_at=now, found=False)
    if not isinstance(data, dict):
        raise TypeError("mod payload is not an object")
    raw_releases: object = cast(dict[str, Any], data).get("releases") or []
    if not isinstance(raw_releases, list):
        raise TypeError("mod releases is not a list")
    releases = [StoredRelease.from_api(r) for r in cast(list[object], raw_releases)]
    return StoredModRecord(checked_at=now, found=True, releases=releases)


_mod_update_service: ModUpdateService | None = None


def _installed_game_version() -> str | None:
    # Imported here: services/server.py imports the mods module lazily, so a top-level
    # import would risk a cycle.
    from vintagestory_api.services.server import get_server_service

    return get_server_service().get_installed_version()


def get_mod_update_service() -> ModUpdateService:
    """Get or create the mod update service singleton."""
    global _mod_update_service
    if _mod_update_service is None:
        from vintagestory_api.services.mods import get_mod_service

        _mod_update_service = ModUpdateService(
            store=ModUpdateStore(Settings().state_dir),
            mod_source=get_mod_service(),
            game_version_provider=_installed_game_version,
        )
    return _mod_update_service

