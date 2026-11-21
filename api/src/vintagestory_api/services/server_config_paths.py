"""Check the mod and save paths in serverconfig.json (Story 25.1, Epic 25 ADR-2).

FR346: each `ModPaths` entry and the save file, as given, as resolved, and how it stands.
FR347: whether the folder the manager installs mods into is one the game loads.

The rules were confirmed on game 1.22.7 (ADR-2 decision 1): a relative `ModPaths` entry
resolves against the server install directory; the save file defaults to
`{serverdata}/Saves/default.vcdbs` and a relative one resolves against the game's working
directory, the data directory. The game creates `serverdata/Saves` and `serverdata/Mods`
at start, but stops when another save file's folder is missing.

Only `stat` and `os.access` touch the file system: nothing is listed, opened or followed
(ADR-2 decision 4).
"""

import os
import stat
from pathlib import Path

from vintagestory_api.config import Settings
from vintagestory_api.models.server_config import (
    PROBLEM_STATUSES,
    PathCheck,
    PathEntry,
    PathStatus,
    ServerConfigFile,
)

DEFAULT_SAVE_FILE = Path("Saves") / "default.vcdbs"
"""The save file under the data path when `SaveFileLocation` is null (ADR-2 decision 1)."""


def check_paths(
    model: ServerConfigFile,
    invalid_keys: tuple[str, ...],
    settings: Settings,
    *,
    game_installed: bool,
) -> PathCheck:
    """The path check for serverconfig.json as read by `GameConfigService.read_config`.

    Args:
        model: The typed read.
        invalid_keys: The named keys read as missing because of their type.
        settings: For the install, data and serverdata directories.
        game_installed: Whether a game server is installed (`ServerService.is_installed`).
    """
    manager_folder = _norm(settings.serverdata_dir / "Mods")
    mod_paths: list[PathEntry]
    # An explicit null is not a list of strings either (Story 25.1 review L1)
    explicit_null = "mod_paths" in model.model_fields_set and model.mod_paths is None
    if "ModPaths" in invalid_keys or explicit_null:
        mod_paths = [_entry(None, None, "invalid")]
    else:
        mod_paths = [
            _mod_path(given, settings, manager_folder, game_installed)
            for given in model.mod_paths or []
        ]
    listed = any(entry.resolved == manager_folder for entry in mod_paths)
    given_save = model.world_config.save_file_location if model.world_config else None
    invalid_save = "WorldConfig.SaveFileLocation" in invalid_keys or "WorldConfig" in invalid_keys
    save_file = _entry(None, None, "invalid") if invalid_save else _save_file(given_save, settings)
    return PathCheck(mod_paths=mod_paths, save_file=save_file, manager_mods_folder_listed=listed)


def _norm(path: Path | str) -> str:
    """The path with `.` and `..` collapsed, without following symlinks."""
    return os.path.normpath(path)


def _entry(given: str | None, resolved: str | None, status: PathStatus) -> PathEntry:
    return PathEntry(
        given=given, resolved=resolved, status=status, problem=status in PROBLEM_STATUSES
    )


def _is_under(path: str, directory: str) -> bool:
    return path == directory or path.startswith(directory.rstrip(os.sep) + os.sep)


class _UnusablePathError(Exception):
    """The path cannot name a file at all: a NUL byte, too long, or a symlink loop."""


def _stat(path: str) -> os.stat_result | None:
    """`os.stat`, or None when the path does not exist (or a parent is not a directory).

    Raises:
        PermissionError: If a parent directory cannot be searched.
        _UnusablePathError: If the path cannot be used (Story 25.1 review M1), so the
            check reports it instead of answering 500.
    """
    try:
        return os.stat(path)
    except FileNotFoundError, NotADirectoryError:
        return None
    except PermissionError:
        raise
    except (OSError, ValueError) as e:
        raise _UnusablePathError from e


def _mod_path(
    given: str, settings: Settings, manager_folder: str, game_installed: bool
) -> PathEntry:
    resolved = _norm(settings.server_dir / given)
    try:
        info = _stat(resolved)
    except PermissionError:
        return _entry(given, resolved, "not_readable")
    except _UnusablePathError:
        return _entry(given, resolved, "invalid")
    if info is None:
        if resolved == manager_folder:
            # Created by the first install, and by the game at start
            return _entry(given, resolved, "not_created_yet")
        if not game_installed and _is_under(resolved, _norm(settings.server_dir)):
            # The game's own mods folder, before a game is installed
            return _entry(given, resolved, "not_installed")
        return _entry(given, resolved, "missing")
    if not stat.S_ISDIR(info.st_mode):
        return _entry(given, resolved, "not_a_directory")
    if not os.access(resolved, os.R_OK | os.X_OK):
        return _entry(given, resolved, "not_readable")
    return _entry(given, resolved, "ok")


def _save_file(given: str | None, settings: Settings) -> PathEntry:
    default = _norm(settings.serverdata_dir / DEFAULT_SAVE_FILE)
    if given is None or given.strip() == "":
        is_default, resolved = True, default
    else:
        is_default, resolved = False, _norm(settings.data_dir / given)
    shown = None if given is None else given
    try:
        info = _stat(resolved)
        if info is not None:
            if not stat.S_ISREG(info.st_mode):
                return _entry(shown, resolved, "not_a_file")
            if not os.access(resolved, os.R_OK | os.W_OK):
                return _entry(shown, resolved, "not_writable")
            return _entry(shown, resolved, "ok")
        parent = os.path.dirname(resolved)
        parent_info = _stat(parent)
    except PermissionError:
        return _entry(shown, resolved, "not_writable")
    except _UnusablePathError:
        return _entry(shown, resolved, "invalid")
    if parent_info is None:
        # The game creates its default Saves folder, and stops for any other
        return _entry(shown, resolved, "not_created_yet" if is_default else "missing")
    if not stat.S_ISDIR(parent_info.st_mode):
        # Something that is not a folder holds the name: the game cannot create it, even
        # for the default save (Story 25.1 review M2)
        return _entry(shown, resolved, "missing")
    if not os.access(parent, os.W_OK | os.X_OK):
        return _entry(shown, resolved, "not_writable")
    return _entry(shown, resolved, "ok")
