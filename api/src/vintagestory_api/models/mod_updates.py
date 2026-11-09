"""Models for mod update detection (Epic 14).

See _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md, ADR-1 and ADR-4.
"""

from datetime import datetime
from typing import Any, Literal

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


class StoredRelease(BaseModel):
    """One mod database release, kept for update detection and version changes."""

    modversion: str
    modidstr: str
    tags: list[str] = []
    fileid: int = 0
    filename: str = ""
    created: str | None = None

    @classmethod
    def from_api(cls, release: dict[str, Any]) -> StoredRelease:
        """Build from a release object in a mod database response."""
        tags: list[Any] = release.get("tags") or []
        return cls(
            modversion=str(release.get("modversion") or ""),
            modidstr=str(release.get("modidstr") or ""),
            tags=[str(tag) for tag in tags],
            fileid=int(release.get("fileid") or 0),
            filename=str(release.get("filename") or ""),
            created=release.get("created"),
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
    mods: dict[str, StoredModRecord] = {}


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

