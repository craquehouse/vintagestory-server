"""Release selection for install (Story 17.2, Epic 17 ADR-2).

One function decides which release an install downloads, and the mod lookup reports
the same choice, so the UI cannot label one release and install another.

Rules (ADR-2 decisions 1-4), over the normalized releases of one mod database entry,
newest first:

1. **Install mod ID:** the requested slug if a release carries it as `modidstr`
   (exact, case-sensitive); otherwise the mod ID of the entry's newest release.
2. **Candidates:** the releases of the install mod ID that have a file.
3. **No version named:** the first stable candidate in list order; if there is none,
   the first candidate; if there are no candidates, refused (`no_file`).
4. **Version named:** the first candidate with that `modversion`. A release of the
   install mod ID with that version but no file is refused (`no_file`); a version no
   release of the install mod ID has is refused (`version_not_found`).

List order decides (Epic 14 ADR-1): no version strings are compared, and game
compatibility is not an input.

This module imports only `models/moddb.py`, so `mod_api.py`, `mod_updates.py` and
`mods.py` can all import it without an import cycle.
"""

from dataclasses import dataclass
from typing import Literal

from vintagestory_api.models.moddb import ReleaseDict

InstallRefusal = Literal["version_not_found", "no_file"]


def is_prerelease(version: str) -> bool:
    """Whether a mod version is a pre-release (contains `-`, such as `2.0.0-rc.1`)."""
    return "-" in version


def has_file(fileid: int | None) -> bool:
    """Whether a release's file ID names a downloadable file (a positive integer).

    A normalized release stores a missing file as `None` and a stored release as 0;
    neither is a file.
    """
    return fileid is not None and fileid > 0


@dataclass(frozen=True)
class InstallSelection:
    """The release an install picks, or why it picks none."""

    mod_id: str
    """The install mod ID (rule 1); always set."""
    release: ReleaseDict | None
    """The chosen release; None when refused."""
    file_id: int | None
    """The chosen release's file ID; an int whenever `release` is set."""
    refusal: InstallRefusal | None
    """Why nothing was chosen; None when a release was chosen."""


def _file_id(release: ReleaseDict) -> int | None:
    value: object = release["fileid"]
    if isinstance(value, int) and not isinstance(value, bool) and has_file(value):
        return value
    return None


def select_install_release(
    slug: str, releases: list[ReleaseDict], version: str | None = None
) -> InstallSelection:
    """Pick the release an install of `slug` downloads (ADR-2 rules 1-4).

    Args:
        slug: The requested mod slug, after `extract_slug`.
        releases: The entry's normalized releases, newest first. Not modified.
        version: A version to install; None for the default release.

    Returns:
        The selection. A refusal is reported in `refusal`, never raised.
    """
    if releases and not any(r["modidstr"] == slug for r in releases):
        mod_id: str = releases[0]["modidstr"]
    else:
        mod_id = slug

    own = [r for r in releases if r["modidstr"] == mod_id]
    candidates = [(r, file_id) for r in own if (file_id := _file_id(r)) is not None]

    def refused(refusal: InstallRefusal) -> InstallSelection:
        return InstallSelection(mod_id=mod_id, release=None, file_id=None, refusal=refusal)

    if version is None:
        stable = [(r, f) for r, f in candidates if not is_prerelease(r["modversion"])]
        chosen = stable[0] if stable else (candidates[0] if candidates else None)
        if chosen is None:
            return refused("no_file")
        return InstallSelection(mod_id=mod_id, release=chosen[0], file_id=chosen[1], refusal=None)

    for release, file_id in candidates:
        if release["modversion"] == version:
            return InstallSelection(mod_id=mod_id, release=release, file_id=file_id, refusal=None)
    if any(r["modversion"] == version for r in own):
        return refused("no_file")
    return refused("version_not_found")
