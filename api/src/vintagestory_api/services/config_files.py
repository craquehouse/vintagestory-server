"""Config files service for raw configuration file access.

Story 6.5: Raw Config Viewer

Provides read-only access to configuration files in the serverdata directory.
Administrators and monitors can list and read JSON configuration files
for troubleshooting purposes.

Story 19.1 (FR205, FR206, Epic 19 ADR-1): the viewer serves only regular files
whose requested and resolved names end in .json (any letter case), that are at
most 2 MiB and UTF-8 text (a leading byte order mark is allowed). The listing
uses the same file rule. Content that does not parse, or that nests more than
config_parse.CONFIG_FILE_MAX_DEPTH levels deep, is returned as `_raw` and `_parse_error`.

Story 23.1 (FR309-FR311, Epic 23 ADR-1, ADR-2): files are parsed as JSON5
(config_parse.parse_config_text: comments, trailing commas, single quotes, unquoted
keys), as the game's own reader is lenient. Every read returns `parse_error`
(null, or the message with its 1-based line and column); an Admin read also returns
the file's `text` and its `version` (the SHA-256 of its bytes).

Story 19.1 (FR208, Epic 19 ADR-3): roles other than Admin list and read the root
of the server data directory and MONITOR_CONFIG_DIRECTORIES (ModConfig) only,
decided on resolved paths; any other directory is ConfigDirectoryForbiddenError.
Admin lists and reads every directory.

Story 17.5 (FR186), Story 19.1 (FR207): only the Admin role receives secrets. For
any other role, in every file and at every depth, the value of a key that names a
secret (game_config.is_secret_key: Password, StartupCommands, or a name containing
password, token, secret, API key, webhook and similar) is replaced by "[redacted]"
unless it is null or "", and so is any string that is a URL with user info or a
Discord webhook URL (game_config.is_secret_value); a file that does not parse is
returned without its text (`_raw` is "[redacted]").

Security:
    Path traversal prevention is critical. All file paths are validated
    using the _safe_path() pattern to prevent escaping the serverdata_dir.
"""

import hashlib
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

import structlog

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import UserRole
from vintagestory_api.services.config_parse import (
    ConfigParseError,
    ParseErrorInfo,
    parse_config_text,
)
from vintagestory_api.services.game_config import REDACTED, redact_secrets

logger = structlog.get_logger()

CONFIG_FILE_MAX_BYTES = 2 * 1024 * 1024
"""The largest config file the viewer reads, in bytes (Epic 19 ADR-1 decision 5)."""

MONITOR_CONFIG_DIRECTORIES: frozenset[str] = frozenset({"ModConfig"})
"""Directories, besides the root, that roles other than Admin may list and read (Epic 19 ADR-3)."""

_MONITOR_CONFIG_DIRECTORIES_FOLDED = frozenset(d.casefold() for d in MONITOR_CONFIG_DIRECTORIES)


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


class ConfigFileInvalidError(Exception):
    """Raised when a text to save does not parse under the file's rule (Story 23.4)."""

    def __init__(self, info: ParseErrorInfo) -> None:
        self.info = info
        self.message = f"The text could not be parsed: {info.message}"
        super().__init__(self.message)


class ConfigFileChangedError(Exception):
    """Raised when a file changed on disk since the version the save carries (Story 23.4)."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.message = f"The file changed on disk since it was read: {filename}"
        super().__init__(self.message)


class ConfigFileWriteError(Exception):
    """Raised when a config file could not be written; the original is unchanged (Story 23.4)."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.message = f"Config file could not be written: {filename}"
        super().__init__(self.message)


@dataclass(frozen=True)
class SavedConfigFile:
    """What a save wrote (Story 23.4)."""

    filename: str
    version: str
    previous_bytes: bytes
    value: object
    is_root_serverconfig: bool


def _is_object(value: object) -> TypeGuard[dict[str, object]]:
    """Whether parsed content is an object (the parsers build dicts with string keys)."""
    return isinstance(value, dict)


def changed_top_level_keys(old: object, new: object) -> set[str]:
    """The keys of `new` whose presence or value differs from `old` (Story 23.4, ADR-4 d7).

    When `old` is not an object (the old text did not parse, or is not an object), every
    key of `new` counts as changed; when `new` is not an object, none does.
    """
    if not _is_object(new):
        return set()
    if not _is_object(old):
        return set(new)
    keys = set(old) | set(new)
    return {key for key in keys if (key in old) != (key in new) or old.get(key) != new.get(key)}


_UTF8_BOM = b"\xef\xbb\xbf"


def _has_json_suffix(name: str) -> bool:
    """Whether a file name ends in .json, in any letter case (Epic 19 ADR-1)."""
    return name.casefold().endswith(".json")


def _is_viewable_file(path: Path) -> bool:
    """The viewer's file rule, shared by the listing and the read (Epic 19 ADR-1).

    A regular file (symlinks followed) whose own name and resolved name end in .json.
    Size and encoding are content checks made when the file is read.
    """
    return path.is_file() and _has_json_suffix(path.name) and _has_json_suffix(path.resolve().name)


def content_version(data: bytes) -> str:
    """The version of a config file: the SHA-256 hex digest of its bytes (Epic 23 ADR-2)."""
    return hashlib.sha256(data).hexdigest()


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
            ConfigPathInvalidError: If the resulting path would escape base_dir, or
                cannot be resolved (a NUL byte, for example).
        """
        # Resolve the base to absolute
        base_resolved = base_dir.resolve()

        # Create the target path, resolve it and verify it is within the base directory.
        # resolve() raises ValueError for a NUL byte and OSError for a path the system
        # refuses; both are invalid paths (Story 19.1 review M1).
        try:
            target = (base_dir / filename).resolve()
            target.relative_to(base_resolved)
        except ValueError, OSError:
            logger.warning(
                "path_traversal_detected",
                filename=filename,
                base_dir=str(base_dir),
            )
            raise ConfigPathInvalidError(filename)

        return target

    def _role_may_open(self, resolved: Path, role: str | None, *, file_request: bool) -> bool:
        """Whether `role` may list (file_request=False) or read (True) the resolved path.

        Nothing outside the server data directory, for any role (Epic 21 ADR-5 decision 2).
        Inside it, Admin: always. Any other role: the root itself, a file directly in the
        root (for a read), or anything whose first path part relative to the server data
        directory is in MONITOR_CONFIG_DIRECTORIES, compared with casefold() (Epic 19 ADR-3
        decision 3).
        """
        base_resolved = self.settings.serverdata_dir.resolve()
        if not resolved.is_relative_to(base_resolved):
            return False
        if role == UserRole.ADMIN:
            return True
        parts = resolved.relative_to(base_resolved).parts
        if not parts:
            return True
        if len(parts) == 1 and file_request:
            return True
        return parts[0].casefold() in _MONITOR_CONFIG_DIRECTORIES_FOLDED

    def _target_directory(self, directory: str | None, role: str | None) -> Path | None:
        """The resolved directory to list, or None when it does not exist.

        The path and role checks run before the existence check, so their answers do
        not depend on whether the server data directory exists (Epic 21 ADR-5 decision 3).

        Raises:
            ConfigPathInvalidError: If directory contains path traversal.
            ConfigDirectoryForbiddenError: If the role may not list it (existing or not).
        """
        serverdata_dir = self.settings.serverdata_dir
        if not directory:
            target_dir = serverdata_dir.resolve()
        else:
            target_dir = self._safe_path(serverdata_dir, directory)
            if not self._role_may_open(target_dir, role, file_request=False):
                raise ConfigDirectoryForbiddenError(directory)
        if not target_dir.is_dir():
            if directory:
                logger.debug("config_subdir_not_found", directory=directory)
            else:
                logger.debug("serverdata_dir_not_found", path=str(serverdata_dir))
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
            that the role may list, decided on each one's resolved path; an entry
            resolving outside the server data directory is never listed. For Admin,
            includes hidden directories - filtering is left to the frontend.
            Empty list only for a directory the role may list that does not exist.

        Raises:
            ConfigPathInvalidError: If directory contains path traversal.
            ConfigDirectoryForbiddenError: If the role may not list the directory,
                whether or not it or the server data directory exists.
        """
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
            List of JSON filenames (not full paths) found in the target directory; a
            file resolving outside the server data directory is never listed. Empty
            list for a directory the role may list that does not exist or contains no
            JSON files.

        Raises:
            ConfigPathInvalidError: If directory contains path traversal.
            ConfigDirectoryForbiddenError: If the role may not list the directory,
                whether or not it or the server data directory exists.
        """
        target_dir = self._target_directory(directory, role)
        if target_dir is None:
            return []

        # The files the viewer can read (not recursive): the viewer's file rule,
        # resolving inside the server data directory, in a directory the role may read
        # (Story 19.1, Epic 19 ADR-1 and ADR-3; containment in _role_may_open, Epic 21 ADR-5)
        json_files = sorted(
            f.name
            for f in target_dir.iterdir()
            if _is_viewable_file(f) and self._role_may_open(f.resolve(), role, file_request=True)
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

        The text is parsed as JSON5 (Story 23.1, Epic 23 ADR-1). Content that does not
        parse, that nests more than config_parse.CONFIG_FILE_MAX_DEPTH levels deep, or that holds
        Infinity or NaN is returned as `_raw` and `_parse_error`, and `parse_error`
        says why and, when known, where.

        Secrets are redacted unless the Admin role is passed (Story 17.5, Epic 17
        ADR-4 decision 4): for any other role, None included, secrets are "[redacted]"
        at every depth by key name and by value (game_config.redact_secrets, Story
        19.1) and `_raw` is "[redacted]" instead of the text.
        The Admin role gets the file as is, and also its text and version (Story 23.1).

        Args:
            filename: Name of the file to read (must be in serverdata_dir).
            role: The caller's role. Only UserRole.ADMIN receives secret values and
                  reads outside the root and MONITOR_CONFIG_DIRECTORIES.

        Returns:
            Dictionary with:
            - filename: The requested filename
            - content: Parsed content from the file, or `_raw` and
              `_parse_error` when it does not parse
            - parse_error: None, or {message, line, column} (line and column 1-based,
              None when unknown)
            - text (Admin only): the file's text, a leading byte order mark dropped
            - version (Admin only): content_version() of the bytes read

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
            # The file may have grown since stat (Story 19.1 review L1)
            if len(data) > CONFIG_FILE_MAX_BYTES:
                raise ConfigFileTooLargeError(filename)
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
        parse_error: ParseErrorInfo | None = None
        try:
            content = parse_config_text(text)
        except ConfigParseError as e:
            # Log but still return - let caller handle malformed content
            parse_error = e.info
            logger.warning("config_file_json_invalid", filename=filename, error=e.info.message)
            # The text cannot be redacted structurally: only Admin receives it
            content = {
                "_raw": text if reveal_secrets else REDACTED,
                "_parse_error": e.info.message,
            }
        else:
            if not reveal_secrets:
                content = redact_secrets(content)

        result: dict[str, object] = {
            "filename": filename,
            "content": content,
            "parse_error": parse_error.to_dict() if parse_error is not None else None,
        }
        # The text and its version only for Admin (Story 23.1, Epic 23 ADR-2 decision 1)
        if reveal_secrets:
            result["text"] = text
            result["version"] = content_version(data)
        logger.debug("config_file_read", filename=filename)
        return result

    def is_root_serverconfig(self, resolved: Path) -> bool:
        """Whether a resolved path is the game's serverconfig.json in the data root.

        That file is read and rewritten as strict JSON by other services, so it is saved
        as strict JSON (Story 23.4, Epic 23 ADR-1 decision 5).
        """
        return (
            resolved.parent == self.settings.serverdata_dir.resolve()
            and resolved.name.casefold() == "serverconfig.json"
        )

    def _encode_and_parse(self, filename: str, text: str, strict: bool) -> tuple[bytes, object]:
        """The text's UTF-8 bytes and parsed value, or the save's refusal."""
        try:
            data = text.encode("utf-8")
        except UnicodeEncodeError:
            raise ConfigFileInvalidError(ParseErrorInfo("The text is not valid UTF-8", None, None))
        if len(data) > CONFIG_FILE_MAX_BYTES:
            raise ConfigFileTooLargeError(filename)
        try:
            value = parse_config_text(text, strict=strict)
        except ConfigParseError as e:
            raise ConfigFileInvalidError(e.info)
        return data, value

    def _target_for_write(self, filename: str) -> Path:
        """The resolved path a save or check applies to (Story 23.4, ADR-4 decision 2)."""
        safe_path = self._safe_path(self.settings.serverdata_dir, filename)
        if not self._role_may_open(safe_path, UserRole.ADMIN, file_request=True):
            raise ConfigDirectoryForbiddenError(filename)
        if not _has_json_suffix(filename):
            raise ConfigFileNotSupportedError(filename)
        return safe_path

    def check_text(self, filename: str, text: str) -> ParseErrorInfo | None:
        """Check a text against the parser rule a save of `filename` would use (Story 23.4).

        The path rules of a save apply, except that the file need not exist; nothing is
        read or written (Epic 23 ADR-4 decision 10).

        Returns:
            None when the text would be accepted, else why not and where.

        Raises:
            ConfigPathInvalidError, ConfigFileNotSupportedError, ConfigFileTooLargeError:
                As for a save.
        """
        safe_path = self._target_for_write(filename)
        try:
            self._encode_and_parse(filename, text, self.is_root_serverconfig(safe_path))
        except ConfigFileInvalidError as e:
            return e.info
        return None

    def save_file(self, filename: str, text: str, version: str) -> SavedConfigFile:
        """Replace an existing config file's text, exactly as sent (Story 23.4, FR314).

        The caller holds ServerService.config_write() (the game server is stopped). Checks,
        in order (Epic 23 ADR-4): the read's path rules for Admin; the file exists and is
        a regular .json file; the text is UTF-8, at most CONFIG_FILE_MAX_BYTES, and parses
        (strict JSON for the root serverconfig.json); the file's current bytes still have
        `version`. Then the text is written atomically, keeping a UTF-8 byte order mark
        the file had, and the file's mode (and owner, when running as root).

        Raises:
            ConfigPathInvalidError, ConfigFileNotSupportedError, ConfigFileNotFoundError,
            ConfigFileTooLargeError, ConfigFileReadError: As for a read.
            ConfigFileInvalidError: If the text does not parse.
            ConfigFileChangedError: If the file changed since `version` was read.
            ConfigFileWriteError: If the file could not be written (it is unchanged).
        """
        safe_path = self._target_for_write(filename)
        if not safe_path.exists():
            raise ConfigFileNotFoundError(filename)
        if not (safe_path.is_file() and _has_json_suffix(safe_path.name)):
            raise ConfigFileNotSupportedError(filename)

        root_serverconfig = self.is_root_serverconfig(safe_path)
        data, value = self._encode_and_parse(filename, text, root_serverconfig)

        try:
            current = safe_path.read_bytes()
        except FileNotFoundError:
            raise ConfigFileNotFoundError(filename)
        except OSError as e:
            logger.error("config_file_read_failed", filename=filename, error_type=type(e).__name__)
            raise ConfigFileReadError(filename)
        old_version = content_version(current)
        if old_version != version:
            logger.info("config_file_save_refused", filename=filename, reason="changed")
            raise ConfigFileChangedError(filename)

        if current.startswith(_UTF8_BOM) and not data.startswith(_UTF8_BOM):
            data = _UTF8_BOM + data
        self._write_atomically(safe_path, data, filename)

        new_version = content_version(data)
        logger.info(
            "config_file_saved",
            filename=filename,
            size=len(data),
            old_version=old_version,
            new_version=new_version,
        )
        return SavedConfigFile(
            filename=filename,
            version=new_version,
            previous_bytes=current,
            value=value,
            is_root_serverconfig=root_serverconfig,
        )

    def _write_atomically(self, path: Path, data: bytes, filename: str) -> None:
        """Write `data` over `path` through a temporary file in the same directory.

        Epic 23 ADR-4 decision 6: the temporary file is created exclusively, written and
        fsynced, given the file's mode (and owner when running as root), and moved over the
        file; then the directory is fsynced. On a failure the temporary file is removed and
        the file is unchanged. No log line or message holds an absolute path.
        """
        temp = path.parent / f".{path.name}.{secrets.token_hex(6)}.tmp"
        try:
            original = path.stat()
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                view = memoryview(data)
                while view:
                    written = os.write(fd, view)
                    view = view[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.chmod(temp, stat.S_IMODE(original.st_mode))
            if os.geteuid() == 0:
                try:
                    os.chown(temp, original.st_uid, original.st_gid)
                except OSError as e:
                    logger.warning("config_file_owner_not_kept", filename=filename, errno=e.errno)
            os.replace(temp, path)
        except OSError as e:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            logger.error(
                "config_file_write_failed",
                filename=filename,
                error_type=type(e).__name__,
                errno=e.errno,
                strerror=e.strerror,
            )
            raise ConfigFileWriteError(filename)
        try:
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError as e:
            logger.warning("config_file_directory_not_synced", filename=filename, errno=e.errno)
