"""Start-up recovery of the files an interrupted mod operation leaves (Epic 19 ADR-9).

An install copies its archive to `<name>.vsm-tmp` and renames it into place. A version
change does the same and, when the new file has the old one's name (ignoring case), first
moves the original aside as `<name>.vsm-bak`, deleted after the state is saved. A process
killed in between leaves these files; `recover_working_files` puts the directory right
before any mod operation runs. Imports only `mod_state`, so `services.mods` can use it.
"""

from pathlib import Path

import structlog

from vintagestory_api.services.mod_state import ModStateManager

logger = structlog.get_logger()

WORKING_COPY_SUFFIX = ".vsm-tmp"
"""Suffix of a copy that is not yet in place: always safe to delete."""

KEPT_ASIDE_SUFFIX = ".vsm-bak"
"""Suffix of an original moved aside during a same-name version change."""

UNKNOWN_LEFTOVER_SUFFIXES = (".tmp", ".bak")
"""Suffixes of files the manager does not name: reported, never deleted (ADR-9 d. 7)."""


def recover_working_files(state_manager: ModStateManager) -> None:
    """Put the mods directory right after an interrupted install or version change (ADR-9).

    Runs once at start-up, before any mod operation. The mod state is the source of truth
    and is never changed here. Each action is logged; a failure is logged and the next
    file is tried.
    """
    mods_dir = state_manager.mods_dir
    if not mods_dir.is_dir():
        return

    for path in sorted(mods_dir.iterdir()):
        if path.name.endswith(WORKING_COPY_SUFFIX):
            try:
                path.unlink()
                logger.info("mod_working_copy_removed", filename=path.name)
            except OSError as e:
                logger.error("mod_recovery_failed", filename=path.name, error=str(e))

    for backup in sorted(p for p in mods_dir.iterdir() if p.name.endswith(KEPT_ASIDE_SUFFIX)):
        try:
            _recover_kept_aside(state_manager, backup)
        except OSError as e:
            logger.error("mod_recovery_failed", filename=backup.name, error=str(e))

    unknown = sorted(
        p.name for p in mods_dir.iterdir() if p.name.lower().endswith(UNKNOWN_LEFTOVER_SUFFIXES)
    )
    if unknown:
        logger.warning("mod_directory_unknown_leftovers", files=unknown)


def _recover_kept_aside(state_manager: ModStateManager, backup: Path) -> None:
    """Delete the original if its change completed, else put it back under its name.

    The new file is looked up ignoring case, since a release whose name differs only in
    case takes the same-file path (Epic 19 ADR-8 decision 4). A state from before Story
    19.4 may hold two mods whose names differ only in case, so every decision is checked
    against the mod the backup holds (its modinfo.json, else the entry under its name):
    - the change completed only when exactly one state key matches the name, that entry
      is the backup's mod, its file is in the directory under that spelling and holds
      the entry's version: the backup is deleted;
    - otherwise the backup is restored, replacing only files of its own mod; when another
      mod's file or entry is in the way, the backup is kept and a warning logged.
    """
    mods_dir = state_manager.mods_dir
    name = backup.name.removesuffix(KEPT_ASIDE_SUFFIX)
    key = name.casefold()
    current = [p for p in mods_dir.iterdir() if p.name.casefold() == key]
    owner = _backup_owner(state_manager, backup, name)

    if owner is not None and _change_completed(state_manager, current, key, owner):
        backup.unlink()
        logger.info("mod_backup_removed", filename=backup.name)
        return

    exact = state_manager.get_mod(name)
    in_the_way = [p.name for p in current if not _belongs_to(state_manager, p, owner)]
    if exact is not None and owner is not None and exact.slug.casefold() != owner:
        in_the_way.append(name)
    if in_the_way:
        logger.warning(
            "mod_backup_kept",
            filename=backup.name,
            reason="another mod's file or entry has this name in some letter case",
            in_the_way=", ".join(sorted(set(in_the_way))),
        )
        return

    if not current:
        backup.rename(mods_dir / name)
        logger.warning("mod_backup_restored", filename=name)
        return

    # The change did not complete and the state still describes the original
    for path in current:
        if path.name != name:
            path.unlink()
    backup.replace(mods_dir / name)
    logger.warning(
        "mod_backup_restored",
        filename=name,
        replaced=", ".join(p.name for p in current),
    )


def _backup_owner(state_manager: ModStateManager, backup: Path, name: str) -> str | None:
    """The mod ID (casefolded) of the kept-aside original, or None when unknown."""
    metadata = state_manager.read_modinfo(backup)
    if metadata is not None:
        return metadata.modid.casefold()
    entry = state_manager.get_mod(name)
    return None if entry is None else entry.slug.casefold()


def _change_completed(
    state_manager: ModStateManager, current: list[Path], key: str, owner: str
) -> bool:
    """True when the one state entry for this name is the owner's and describes its file."""
    keys = [k for k in state_manager.filenames() if k.casefold() == key]
    if len(keys) != 1:
        return False
    entry = state_manager.get_mod(keys[0])
    path = next((p for p in current if p.name == keys[0]), None)
    if entry is None or path is None or entry.slug.casefold() != owner:
        return False
    metadata = state_manager.read_modinfo(path)
    return metadata is not None and metadata.version == entry.version


def _belongs_to(state_manager: ModStateManager, path: Path, owner: str | None) -> bool:
    """Whether `path` may be replaced by the owner's original: it is not another mod's.

    The entry under its exact name decides; without one, its modinfo.json does. A file
    that names no mod is the interrupted change's own new file (it was validated before
    it was placed, so this is a damaged copy). With no known owner nothing is replaced.
    """
    if owner is None:
        return False
    entry = state_manager.get_mod(path.name)
    if entry is not None:
        return entry.slug.casefold() == owner
    metadata = state_manager.read_modinfo(path)
    return metadata is None or metadata.modid.casefold() == owner
