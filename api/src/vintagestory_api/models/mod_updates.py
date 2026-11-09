"""Models for mod update detection (Epic 14).

See _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md, ADR-1 and ADR-4.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

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
    tags: list[str] = Field(default_factory=list)
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
