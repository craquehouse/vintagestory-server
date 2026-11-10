"""Models for mod update detection (Epic 14).

See _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md, ADR-1 and ADR-4.
"""

import re
from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel

Compatibility = Literal["compatible", "not_verified", "incompatible"]
"""Compatibility of a release with the installed game version (see mod_api.check_compatibility)."""

UpdateState = Literal["update_available", "up_to_date", "blocked", "unknown"]
"""Update status of an installed mod.

- update_available: an eligible newer release is compatible or not verified
- up_to_date: no eligible newer release exists
- blocked: eligible newer releases exist, but all are incompatible
- unknown: status cannot be determined (see UnknownReason)
"""

UnknownReason = Literal[
    "not_checked",
    "not_in_database",
    "installed_release_not_listed",
    "version_unparsable",
]


_SURROGATES = re.compile("[\ud800-\udfff]")


def _clean_text(value: object) -> str:
    """Convert to str, replacing each lone surrogate (not encodable as UTF-8) with U+FFFD."""
    return _SURROGATES.sub("\ufffd", str(value))


class StoredRelease(BaseModel):
    """One mod database release, kept for update detection and version changes."""

    modversion: str
    modidstr: str
    tags: list[str] = []
    fileid: int = 0
    filename: str = ""
    created: str | None = None

    @classmethod
    def from_api(cls, release: object) -> StoredRelease:
        """Build from a release object in a mod database response.

        Raises:
            TypeError: If the release is not an object.
            ValueError: If a field has an unusable value (pydantic's ValidationError
                is a ValueError).
        """
        if not isinstance(release, dict):
            raise TypeError("release is not an object")
        data = cast(dict[str, Any], release)
        raw_tags: object = data.get("tags") or []
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        tags = (
            [_clean_text(tag) for tag in cast(list[Any], raw_tags)]
            if isinstance(raw_tags, list)
            else []
        )
        created = data.get("created")
        return cls(
            modversion=_clean_text(data.get("modversion") or ""),
            modidstr=_clean_text(data.get("modidstr") or ""),
            tags=tags,
            fileid=int(data.get("fileid") or 0),
            filename=_clean_text(data.get("filename") or ""),
            created=_clean_text(created) if isinstance(created, str) else created,
        )


class StoredModRecord(BaseModel):
    """Mod database data for one installed modid, as of its last check."""

    checked_at: datetime
    found: bool
    """False when the mod database returned not found."""
    releases: list[StoredRelease] = []
    """Releases for the whole mod database entry, newest first."""
    error: str | None = None
    """The last check's failure for this mod, if it failed; earlier data is kept."""


class ModUpdatesFile(BaseModel):
    """Contents of the mod update store file."""

    schema_version: int = 1
    last_full_check: datetime | None = None
    """When the last check in which every lookup succeeded finished."""
    mods: dict[str, StoredModRecord] = {}
    lookup_errors: dict[str, str] = {}
    """Last lookup failure for installed mods that have no stored record yet."""
    notified: dict[str, str] = {}
    """Offered version last alerted per installed modid (Story 14.6, ADR-6)."""


class ModUpdateStatusItem(BaseModel):
    """Update status of one installed mod, as returned by the API."""

    slug: str
    name: str
    installed_version: str
    status: UpdateState
    offered_version: str | None = None
    offered_compatibility: Compatibility | None = None
    offered_prerelease: bool | None = None
    reason: UnknownReason | None = None
    checked_at: datetime | None = None
    error: str | None = None

