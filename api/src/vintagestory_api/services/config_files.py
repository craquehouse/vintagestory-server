"""Config files service for raw configuration file access.

Story 6.5: Raw Config Viewer

Provides read-only access to configuration files in the serverdata directory.
Administrators and monitors can list and read JSON configuration files
for troubleshooting purposes.

Story 17.5 (FR186): only the Admin role receives secrets. For any other role,
every top-level key that names a secret setting (Password, in any letter case)
and has a value is replaced by "[redacted]", in every file; a file that does not
parse as JSON is returned without its text (`_raw` is "[redacted]").

Security:
    Path traversal prevention is critical. All file paths are validated
    using the _safe_path() pattern to prevent escaping the serverdata_dir.
"""

import json
from pathlib import Path

import structlog

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import UserRole
from vintagestory_api.services.game_config import REDACTED, redact_secrets

logger = structlog.get_logger()


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

    def list_directories(self, directory: str | None = None) -> list[str]:
        """List subdirectories in serverdata directory or a subdirectory.

        Args:
            directory: Optional subdirectory path within serverdata_dir.
                       If None, lists directories in the root serverdata directory.

        Returns:
            List of subdirectory names (not full paths) found in the target directory.
            Includes hidden directories - filtering is left to the frontend.
            Empty list if directory doesn't exist.

        Raises:
            ConfigPathInvalidError: If directory contains path traversal.
        """
        serverdata_dir = self.settings.serverdata_dir

        if not serverdata_dir.exists():
            logger.debug("serverdata_dir_not_found", path=str(serverdata_dir))
            return []

        # Determine target directory
        if directory:
            # Validate path traversal
            target_dir = self._safe_path(serverdata_dir, directory)
            if not target_dir.is_dir():
                logger.debug("config_subdir_not_found", directory=directory)
                return []
        else:
            target_dir = serverdata_dir

        # Find all subdirectories (including hidden - let frontend handle visibility)
        directories = sorted(d.name for d in target_dir.iterdir() if d.is_dir())

        logger.debug("config_directories_listed", count=len(directories), directory=directory)
        return directories

    def list_files(self, directory: str | None = None) -> list[str]:
        """List JSON configuration files in serverdata directory or subdirectory.

        Args:
            directory: Optional subdirectory name within serverdata_dir.
                       If None, lists files in the root serverdata directory.

        Returns:
            List of JSON filenames (not full paths) found in the target directory.
            Empty list if directory doesn't exist or contains no JSON files.

        Raises:
            ConfigPathInvalidError: If directory contains path traversal.
        """
        serverdata_dir = self.settings.serverdata_dir

        if not serverdata_dir.exists():
            logger.debug("serverdata_dir_not_found", path=str(serverdata_dir))
            return []

        # Determine target directory
        if directory:
            # Validate path traversal
            target_dir = self._safe_path(serverdata_dir, directory)
            if not target_dir.is_dir():
                logger.debug("config_subdir_not_found", directory=directory)
                return []
        else:
            target_dir = serverdata_dir

        # Find all JSON files in the target directory (not recursive)
        json_files = sorted(
            f.name for f in target_dir.iterdir() if f.is_file() and f.suffix == ".json"
        )

        logger.debug("config_files_listed", count=len(json_files), directory=directory)
        return json_files

    def read_file(self, filename: str, role: str | None = None) -> dict[str, object]:
        """Read a JSON configuration file and return its content.

        Secrets are redacted unless the Admin role is passed (Story 17.5, Epic 17
        ADR-4 decision 4): for any other role, None included, top-level secret keys
        with a value are "[redacted]" and a file that does not parse has
        `_raw: "[redacted]"` instead of its text. The Admin role gets the file as is.

        Args:
            filename: Name of the file to read (must be in serverdata_dir).
            role: The caller's role. Only UserRole.ADMIN receives secret values.

        Returns:
            Dictionary with:
            - filename: The requested filename
            - content: Parsed JSON content from the file, or `_raw` and
              `_parse_error` when it does not parse

        Raises:
            ConfigPathInvalidError: If filename contains path traversal.
            ConfigFileNotFoundError: If the file does not exist.
        """
        serverdata_dir = self.settings.serverdata_dir

        # Validate path - this raises ConfigPathInvalidError if invalid
        safe_path = self._safe_path(serverdata_dir, filename)

        # Check file exists
        if not safe_path.exists():
            logger.debug("config_file_not_found", filename=filename)
            raise ConfigFileNotFoundError(filename)

        # Read and parse JSON
        reveal_secrets = role == UserRole.ADMIN
        text = safe_path.read_text(encoding="utf-8")
        content: object
        try:
            content = json.loads(text)
        except json.JSONDecodeError as e:
            # Log but still return - let caller handle malformed JSON
            logger.warning("config_file_json_invalid", filename=filename, error=str(e))
            # The text cannot be redacted structurally: only Admin receives it
            content = {"_raw": text if reveal_secrets else REDACTED, "_parse_error": str(e)}
        else:
            if not reveal_secrets:
                content = redact_secrets(content)

        logger.debug("config_file_read", filename=filename)
        return {"filename": filename, "content": content}
