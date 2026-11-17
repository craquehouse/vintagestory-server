"""Config files service for raw configuration file access.

Story 6.5: Raw Config Viewer

Provides read-only access to configuration files in the serverdata directory.
Administrators and monitors can list and read JSON configuration files
for troubleshooting purposes.

Story 19.1 (FR205, FR206, Epic 19 ADR-1): the viewer serves only regular files
whose requested and resolved names end in .json (any letter case), that are at
most 2 MiB and UTF-8 text (a leading byte order mark is allowed). The listing
uses the same file rule. Content that does not parse, or that nests more than
CONFIG_FILE_MAX_DEPTH levels deep, is returned as `_raw` and `_parse_error`.

Story 19.1 (FR208, Epic 19 ADR-3): roles other than Admin list and read the root
of the server data directory and MONITOR_CONFIG_DIRECTORIES (ModConfig) only,
decided on resolved paths; any other directory is ConfigDirectoryForbiddenError.
Admin lists and reads every directory.

Story 17.5 (FR186), Story 19.1 (FR207): only the Admin role receives secrets. For
any other role, in every file and at every depth, the value of a key that names a
secret (game_config.is_secret_key: Password, StartupCommands, or a name containing
password, token, secret, API key, webhook and similar) is replaced by "[redacted]"
unless it is null or "", and so is any string that is a URL with user info or a
Discord webhook URL (game_config.is_secret_value); a file that does not parse as
JSON is returned without its text (`_raw` is "[redacted]").

Security:
    Path traversal prevention is critical. All file paths are validated
    using the _safe_path() pattern to prevent escaping the serverdata_dir.
"""

import json
from pathlib import Path
from typing import TypeGuard

import structlog

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import UserRole
from vintagestory_api.services.game_config import REDACTED, redact_secrets

logger = structlog.get_logger()

CONFIG_FILE_MAX_BYTES = 2 * 1024 * 1024
"""The largest config file the viewer reads, in bytes (Epic 19 ADR-1 decision 5)."""

MONITOR_CONFIG_DIRECTORIES: frozenset[str] = frozenset({"ModConfig"})
"""Directories, besides the root, that roles other than Admin may list and read (Epic 19 ADR-3)."""

_MONITOR_CONFIG_DIRECTORIES_FOLDED = frozenset(d.casefold() for d in MONITOR_CONFIG_DIRECTORIES)

CONFIG_FILE_MAX_DEPTH = 200
"""How deeply parsed content may nest objects and arrays before it is returned as `_raw`.

Deeper content cannot be serialized into the response (about 254 levels at Story 19.1),
and the limit keeps the recursive redaction far below Python's recursion limit.
"""


class ConfigFileNotFoundError(Exception):
    """Raised when a requested config file does not exist."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.message = f"Config file not found: {filename}"
        super().__init__(self.message)


class ConfigPathInvalidError(Exception):
    """Raised when a path traversal attack is detected."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.message = f"Invalid file path: {filename}"
        super().__init__(self.message)


class ConfigDirectoryForbiddenError(Exception):
    """Raised when the caller's role may not list or read a directory (Story 19.1).

    The message is the same whether or not the directory or file exists.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self.message = f"This directory needs the Admin role: {path}"
        super().__init__(self.message)


class ConfigFileNotSupportedError(Exception):
    """Raised when a path is not a regular .json file that is UTF-8 text (Story 19.1)."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.message = f"Only .json files that are UTF-8 text can be viewed: {filename}"
        super().__init__(self.message)


class ConfigFileTooLargeError(Exception):
    """Raised when a config file is larger than CONFIG_FILE_MAX_BYTES (Story 19.1)."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.message = (
            f"Config file is larger than {CONFIG_FILE_MAX_BYTES // (1024 * 1024)} MiB "
            f"and cannot be viewed: {filename}"
        )
        super().__init__(self.message)


class ConfigFileReadError(Exception):
    """Raised when a config file cannot be read for a reason other than its absence."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.message = f"Config file could not be read: {filename}"
        super().__init__(self.message)


def _has_json_suffix(name: str) -> bool:
    """Whether a file name ends in .json, in any letter case (Epic 19 ADR-1)."""
    return name.casefold().endswith(".json")


def _is_viewable_file(path: Path) -> bool:
    """The viewer's file rule, shared by the listing and the read (Epic 19 ADR-1).

    A regular file (symlinks followed) whose own name and resolved name end in .json.
    Size and encoding are content checks made when the file is read.
    """
    return path.is_file() and _has_json_suffix(path.name) and _has_json_suffix(path.resolve().name)


def _is_json_object(value: object) -> TypeGuard[dict[str, object]]:
    """Whether parsed JSON is an object. `json.loads` only builds dicts with string keys."""
    return isinstance(value, dict)


def _is_json_array(value: object) -> TypeGuard[list[object]]:
    """Whether parsed JSON is an array."""
    return isinstance(value, list)


def _nesting_depth_exceeds(value: object, limit: int) -> bool:
    """Whether parsed JSON nests objects and arrays more than `limit` levels deep.

    Iterative, so it cannot hit the recursion limit itself.
    """
    stack: list[tuple[object, int]] = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        children: list[object]
        if _is_json_object(item):
            children = list(item.values())
        elif _is_json_array(item):
            children = item
        else:
            continue
        depth += 1
        if depth > limit:
            return True
        stack.extend((child, depth) for child in children)
    return False


class ConfigFilesService:
    """Service for listing and reading raw configuration files.

    Provides read-only access to JSON configuration files in the
    serverdata directory for troubleshooting purposes.

    Attributes:
        settings: Application settings containing serverdata_dir path.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the service with settings.

        Args:
            settings: Application settings with serverdata_dir.
        """
        self.settings = settings

    def _safe_path(self, base_dir: Path, filename: str) -> Path:
        """Create a safe file path, preventing path traversal attacks.

        Uses Path.resolve() to detect path traversal attempts including:
        - ../etc/passwd (simple parent traversal)
        - subdir/../../etc/passwd (nested traversal)
        - /absolute/path (absolute paths)

        Args:
            base_dir: The base directory that must contain the result.
            filename: The filename to join (may contain malicious sequences).

        Returns:
            Safe path guaranteed to be within base_dir.

        Raises:
            ConfigPathInvalidError: If the resulting path would escape base_dir.
        """
        # Resolve the base to absolute
        base_resolved = base_dir.resolve()

        # Create the target path and resolve it
        target = (base_dir / filename).resolve()

        # Verify the target is within the base directory
        try:
            target.relative_to(base_resolved)
        except ValueError:
            logger.warning(
                "path_traversal_detected",
                filename=filename,
                base_dir=str(base_dir),
            )
            raise ConfigPathInvalidError(filename)

        return target

    def _role_may_open(self, resolved: Path, role: str | None, *, file_request: bool) -> bool:
        """Whether `role` may list (file_request=False) or read (True) the resolved path.

        Admin: always. Any other role: the root itself, a file directly in the root (for a read),
        or anything whose first path part relative to the server data directory is in
        MONITOR_CONFIG_DIRECTORIES, compared with casefold() (Epic 19 ADR-3 decision 3).
        """
        if role == UserRole.ADMIN:
            return True
        base_resolved = self.settings.serverdata_dir.resolve()
        if not resolved.is_relative_to(base_resolved):
            return False
        parts = resolved.relative_to(base_resolved).parts
        if not parts:
            return True
        if len(parts) == 1 and file_request:
            return True
        return parts[0].casefold() in _MONITOR_CONFIG_DIRECTORIES_FOLDED

    def _target_directory(self, directory: str | None, role: str | None) -> Path | None:
        """The resolved directory to list, or None when it does not exist.

        Raises:
            ConfigPathInvalidError: If directory contains path traversal.
            ConfigDirectoryForbiddenError: If the role may not list it (existing or not).
        """
        serverdata_dir = self.settings.serverdata_dir
        if not directory:
            return serverdata_dir.resolve()
        target_dir = self._safe_path(serverdata_dir, directory)
        if not self._role_may_open(target_dir, role, file_request=False):
            raise ConfigDirectoryForbiddenError(directory)
        if not target_dir.is_dir():
            logger.debug("config_subdir_not_found", directory=directory)
            return None
        return target_dir

    def list_directories(self, directory: str | None = None, role: str | None = None) -> list[str]:
        """List subdirectories in serverdata directory or a subdirectory.

        Args:
            directory: Optional subdirectory path within serverdata_dir.
                       If None, lists directories in the root serverdata directory.
            role: The caller's role. Admin lists every directory; any other role, None
                  included, only the root and MONITOR_CONFIG_DIRECTORIES (Story 19.1).

        Returns:
            List of subdirectory names (not full paths) found in the target directory
            that the role may list, decided on each one's resolved path. For Admin,
            includes hidden directories - filtering is left to the frontend.
            Empty list if directory doesn't exist.

        Raises:
            ConfigPathInvalidError: If directory contains path traversal.
            ConfigDirectoryForbiddenError: If the role may not list the directory,
                whether or not it exists.
        """
        serverdata_dir = self.settings.serverdata_dir

        if not serverdata_dir.exists():
            logger.debug("serverdata_dir_not_found", path=str(serverdata_dir))
            return []

        target_dir = self._target_directory(directory, role)
        if target_dir is None:
            return []

        # Find all subdirectories the role may list (including hidden ones for Admin -
        # let frontend handle visibility); decided on each entry's resolved path
        directories = sorted(
            d.name
            for d in target_dir.iterdir()
            if d.is_dir() and self._role_may_open(d.resolve(), role, file_request=False)
        )

        logger.debug("config_directories_listed", count=len(directories), directory=directory)
        return directories

    def list_files(self, directory: str | None = None, role: str | None = None) -> list[str]:
        """List JSON configuration files in serverdata directory or subdirectory.

        Lists the files that pass the viewer's file rule (Story 19.1): regular files
        whose own and resolved names end in .json, in any letter case, resolving
        inside the server data directory, in a directory the role may read. Size and
        encoding are checked on read.

        Args:
            directory: Optional subdirectory name within serverdata_dir.
                       If None, lists files in the root serverdata directory.
            role: The caller's role. Admin lists every directory; any other role, None
                  included, only the root and MONITOR_CONFIG_DIRECTORIES (Story 19.1).

        Returns:
            List of JSON filenames (not full paths) found in the target directory.
            Empty list if directory doesn't exist or contains no JSON files.

        Raises:
            ConfigPathInvalidError: If directory contains path traversal.
            ConfigDirectoryForbiddenError: If the role may not list the directory,
                whether or not it exists.
        """
        serverdata_dir = self.settings.serverdata_dir

        if not serverdata_dir.exists():
            logger.debug("serverdata_dir_not_found", path=str(serverdata_dir))
            return []

        target_dir = self._target_directory(directory, role)
        if target_dir is None:
            return []

        # The files the viewer can read (not recursive): the viewer's file rule,
        # resolving inside the server data directory, in a directory the role may read
        # (Story 19.1, Epic 19 ADR-1 and ADR-3)
        base_resolved = serverdata_dir.resolve()
        json_files = sorted(
            f.name
            for f in target_dir.iterdir()
            if _is_viewable_file(f)
            and f.resolve().is_relative_to(base_resolved)
            and self._role_may_open(f.resolve(), role, file_request=True)
        )

        logger.debug("config_files_listed", count=len(json_files), directory=directory)
        return json_files

    def read_file(self, filename: str, role: str | None = None) -> dict[str, object]:
        """Read a JSON configuration file and return its content.

        Checks, in order (Story 19.1, Epic 19 ADR-1 and ADR-3): the path stays inside
        the server data directory; the role may read the resolved path (any role but
        Admin: a file in the root or under MONITOR_CONFIG_DIRECTORIES); the requested
        name ends in .json (before the disk is touched); the file exists; it is a
        regular file whose resolved name ends in .json; it is at most
        CONFIG_FILE_MAX_BYTES (checked before it is read); it is UTF-8 text (a leading
        byte order mark is dropped).

        Content that does not parse, that the parser gives up on, or that nests more
        than CONFIG_FILE_MAX_DEPTH levels deep is returned as `_raw` and `_parse_error`.

        Secrets are redacted unless the Admin role is passed (Story 17.5, Epic 17
        ADR-4 decision 4): for any other role, None included, secrets are "[redacted]"
        at every depth by key name and by value (game_config.redact_secrets, Story
        19.1) and `_raw` is "[redacted]" instead of the text.
        The Admin role gets the file as is.

        Args:
            filename: Name of the file to read (must be in serverdata_dir).
            role: The caller's role. Only UserRole.ADMIN receives secret values and
                  reads outside the root and MONITOR_CONFIG_DIRECTORIES.

        Returns:
            Dictionary with:
            - filename: The requested filename
            - content: Parsed JSON content from the file, or `_raw` and
              `_parse_error` when it does not parse or nests too deeply

        Raises:
            ConfigPathInvalidError: If filename contains path traversal.
            ConfigDirectoryForbiddenError: If the role may not read the file's directory,
                whether or not the file exists.
            ConfigFileNotSupportedError: If it is not a regular .json file of UTF-8 text.
            ConfigFileNotFoundError: If the file does not exist.
            ConfigFileTooLargeError: If the file is larger than CONFIG_FILE_MAX_BYTES.
            ConfigFileReadError: If the file cannot be read (any other OSError).
        """
        serverdata_dir = self.settings.serverdata_dir

        # Validate path - this raises ConfigPathInvalidError if invalid
        safe_path = self._safe_path(serverdata_dir, filename)

        # The role, on the resolved path, before anything else (Epic 19 ADR-3 decision 5)
        if not self._role_may_open(safe_path, role, file_request=True):
            raise ConfigDirectoryForbiddenError(filename)

        # The requested name, before the disk is touched (ADR-1 decision 3)
        if not _has_json_suffix(filename):
            raise ConfigFileNotSupportedError(filename)

        # Check file exists (safe_path is resolved: a dangling symlink is not found)
        if not safe_path.exists():
            logger.debug("config_file_not_found", filename=filename)
            raise ConfigFileNotFoundError(filename)

        # A regular file whose resolved name ends in .json
        if not (safe_path.is_file() and _has_json_suffix(safe_path.name)):
            raise ConfigFileNotSupportedError(filename)

        try:
            if safe_path.stat().st_size > CONFIG_FILE_MAX_BYTES:
                raise ConfigFileTooLargeError(filename)
            data = safe_path.read_bytes()
        except FileNotFoundError:
            raise ConfigFileNotFoundError(filename)
        except OSError as e:
            logger.error("config_file_read_failed", filename=filename, error=str(e))
            raise ConfigFileReadError(filename)

        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ConfigFileNotSupportedError(filename)

        reveal_secrets = role == UserRole.ADMIN
        content: object
        try:
            content = json.loads(text)
        except (json.JSONDecodeError, RecursionError) as e:
            # Log but still return - let caller handle malformed JSON
            logger.warning("config_file_json_invalid", filename=filename, error=str(e))
            # The text cannot be redacted structurally: only Admin receives it
            content = {"_raw": text if reveal_secrets else REDACTED, "_parse_error": str(e)}
        else:
            if _nesting_depth_exceeds(content, CONFIG_FILE_MAX_DEPTH):
                error = f"Nested more than {CONFIG_FILE_MAX_DEPTH} levels deep"
                logger.warning("config_file_json_invalid", filename=filename, error=error)
                content = {"_raw": text if reveal_secrets else REDACTED, "_parse_error": error}
            elif not reveal_secrets:
                content = redact_secrets(content)

        logger.debug("config_file_read", filename=filename)
        return {"filename": filename, "content": content}
