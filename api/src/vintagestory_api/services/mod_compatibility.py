"""Supported game versions per mod ID (Story 16.3, Epic 16 ADR-2 decision 1).

A mod ID's supported game versions are the tags on its releases (releases whose
`modidstr` is that mod ID). Tags are compared with `parse_base_version` and
`is_prerelease` from `mod_updates`: by base version, then a stable tag above
pre-releases of the same base. Pre-releases of the same base are not ordered among
themselves (there is no pre-release parser); the first one seen is kept.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from vintagestory_api.services.mod_updates import is_prerelease, parse_base_version

type _VersionKey = tuple[tuple[int, ...], int]


@dataclass(frozen=True)
class SupportedRange:
    """Lowest and highest game version tags of one mod ID."""

    lowest: str
    highest: str


def _version_key(version: str) -> _VersionKey | None:
    """Sort key for a game version, or None when it does not parse.

    Trailing zero parts are dropped so that `1.21` and `1.21.0` compare equal.
    """
    base = parse_base_version(version)
    if base is None:
        return None
    parts = list(base)
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return (tuple(parts), 0 if is_prerelease(version) else 1)


def compare_game_versions(left: str, right: str) -> int | None:
    """Compare two game versions: -1, 0 or 1, or None when either does not parse."""
    left_key = _version_key(left)
    right_key = _version_key(right)
    if left_key is None or right_key is None:
        return None
    return (left_key > right_key) - (left_key < right_key)


def supported_game_versions(
    releases: Iterable[Mapping[str, Any]], modid: str
) -> SupportedRange | None:
    """The lowest and highest game versions the mod ID's releases are tagged for.

    Stable tags are preferred for both ends; pre-release tags are used only when the
    mod ID has no stable tag. Tags that do not parse are ignored. Returns None when
    no tag of the mod ID parses.
    """
    stable: list[tuple[_VersionKey, str]] = []
    pre: list[tuple[_VersionKey, str]] = []
    for release in releases:
        if (release.get("modidstr") or "") != modid:
            continue
        tags: list[Any] = release.get("tags") or []
        for tag in tags:
            if not isinstance(tag, str):
                continue
            key = _version_key(tag)
            if key is None:
                continue
            (pre if key[1] == 0 else stable).append((key, tag))

    candidates = stable or pre
    if not candidates:
        return None
    # min()/max() keep the first of equal keys, so ties go to the first tag seen
    lowest = min(candidates, key=lambda item: item[0])[1]
    highest = max(candidates, key=lambda item: item[0])[1]
    return SupportedRange(lowest=lowest, highest=highest)
