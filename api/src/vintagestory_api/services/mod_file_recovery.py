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
    case takes the same-file path (Epic 19 ADR-8 decision 4). The change completed when
    the state describes that file: an entry under its name with the version it holds.
    """
    mods_dir = state_manager.mods_dir
    name = backup.name.removesuffix(KEPT_ASIDE_SUFFIX)
    key = name.casefold()
    current = [p for p in mods_dir.iterdir() if p.name.casefold() == key]

    if not current:
        backup.rename(mods_dir / name)
        logger.warning("mod_backup_restored", filename=name)
        return

    if any(_state_describes(state_manager, path) for path in current):
        backup.unlink()
        logger.info("mod_backup_removed", filename=backup.name)
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


def _state_describes(state_manager: ModStateManager, path: Path) -> bool:
    state = state_manager.get_mod(path.name)
    if state is None:
        return False
    metadata = state_manager.read_modinfo(path)
    return metadata is not None and metadata.version == state.version
