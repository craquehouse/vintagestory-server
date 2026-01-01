"""Config files service for raw configuration file access.

Story 6.5: Raw Config Viewer

Provides read-only access to configuration files in the serverdata directory.
Administrators and monitors can list and read JSON configuration files
for troubleshooting purposes.

Security:
    Path traversal prevention is critical. All file paths are validated
    using the _safe_path() pattern to prevent escaping the serverdata_dir.
"""

from pathlib import Path

import structlog

from vintagestory_api.config import Settings

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

    def list_files(self) -> list[str]:
        """List all JSON configuration files in serverdata directory.

        Returns:
            List of JSON filenames (not full paths) found in serverdata_dir.
            Empty list if directory doesn't exist or contains no JSON files.
        """
        serverdata_dir = self.settings.serverdata_dir

        if not serverdata_dir.exists():
            logger.debug("serverdata_dir_not_found", path=str(serverdata_dir))
            return []

        # Find all JSON files in the serverdata directory (not recursive)
        json_files = sorted(
            f.name for f in serverdata_dir.iterdir() if f.is_file() and f.suffix == ".json"
        )

        logger.debug("config_files_listed", count=len(json_files))
        return json_files

    def read_file(self, filename: str) -> dict[str, object]:
        """Read a JSON configuration file and return its content.

        Args:
            filename: Name of the file to read (must be in serverdata_dir).

        Returns:
            Dictionary with:
            - filename: The requested filename
            - content: Parsed JSON content from the file

        Raises:
            ConfigPathInvalidError: If filename contains path traversal.
            ConfigFileNotFoundError: If the file does not exist.
        """
        import json

        serverdata_dir = self.settings.serverdata_dir

        # Validate path - this raises ConfigPathInvalidError if invalid
        safe_path = self._safe_path(serverdata_dir, filename)

        # Check file exists
        if not safe_path.exists():
            logger.debug("config_file_not_found", filename=filename)
            raise ConfigFileNotFoundError(filename)

        # Read and parse JSON
        try:
            content = json.loads(safe_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            # Log but still return - let caller handle malformed JSON
            logger.warning("config_file_json_invalid", filename=filename, error=str(e))
            # Return raw text as content if JSON parsing fails
            content = {"_raw": safe_path.read_text(encoding="utf-8"), "_parse_error": str(e)}

        logger.debug("config_file_read", filename=filename)
        return {"filename": filename, "content": content}
