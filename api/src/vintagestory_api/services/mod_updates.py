"""Mod update detection (Epic 14, Story 14.1).

Rules are defined in _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md,
ADR-1. "Newer" means earlier in the mod database's release list (newest first); version
strings are only compared for the base-version check on mods already on a pre-release.
"""

from dataclasses import dataclass

from vintagestory_api.models.mod_updates import StoredRelease, UnknownReason, UpdateState
from vintagestory_api.services.mod_api import CompatibilityStatus, check_compatibility


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
