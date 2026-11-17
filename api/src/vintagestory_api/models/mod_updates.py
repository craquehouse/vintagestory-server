"""Models for mod update detection (Epic 14).

See _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md, ADR-1 and ADR-4.
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from vintagestory_api.models.moddb import normalize_release

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

        The release goes through the same normalizer as every mod database release
        (Epic 17 ADR-1); then lone surrogates are cleaned from the text. A release
        without a downloadable file (`fileid` None) is stored with `fileid` 0.

        Raises:
            TypeError: If the release is not an object.
        """
        data = normalize_release(release)
        if data is None:
            raise TypeError("release is not an object")
        fileid: int | None = data["fileid"]
        return cls(
            modversion=_clean_text(data["modversion"]),
            modidstr=_clean_text(data["modidstr"]),
            tags=[_clean_text(tag) for tag in data["tags"]],
            fileid=fileid if fileid is not None else 0,
            filename=_clean_text(data["filename"]),
            created=_clean_text(data["created"]),
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
