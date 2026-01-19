"""Mod state persistence and management service.

This service manages the mod state index file (mods.json) which tracks
installed mods and their enabled/disabled status. It uses atomic writes
to prevent corruption.
"""

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import structlog

from vintagestory_api.models.mods import ModMetadata, ModState

logger = structlog.get_logger()


class ModStateManager:
    """Manages mod state persistence to the state index file.

    The state index (mods.json) maps filenames to mod metadata for fast
    lookup without re-extracting from zip files.

    Attributes:
        state_dir: Directory containing state files (/data/vsmanager/state).
        mods_dir: Directory containing mod zip files (/data/serverdata/mods).
        state_file: Path to the mods.json state index file.
    """

    def __init__(self, state_dir: Path, mods_dir: Path) -> None:
        """Initialize the mod state manager.

        Args:
            state_dir: Directory for state files (will contain mods.json).
            mods_dir: Directory containing installed mod zip files.
        """
        self._state_dir = state_dir
        self._mods_dir = mods_dir
        self._state: dict[str, ModState] = {}

    @property
    def state_dir(self) -> Path:
        """Get the state directory path."""
        return self._state_dir

    @property
    def mods_dir(self) -> Path:
        """Get the mods directory path."""
        return self._mods_dir

    @property
    def state_file(self) -> Path:
        """Get the path to the mods.json state file."""
        return self._state_dir / "mods.json"

    def load(self) -> None:
        """Load mod state from the state index file.

        If the file doesn't exist or is corrupt, starts with empty state.
        """
        if not self.state_file.exists():
            logger.debug("mod_state_file_not_found", path=str(self.state_file))
            self._state = {}
            return

        try:
            data = json.loads(self.state_file.read_text())
            self._state = {
                filename: ModState.model_validate(state_data)
                for filename, state_data in data.items()
            }
            logger.info(
                "mod_state_loaded",
                mod_count=len(self._state),
                path=str(self.state_file),
            )
        except (
            json.JSONDecodeError,
            ValueError,
            AttributeError,
            TypeError,
            IsADirectoryError,
            PermissionError,
        ) as e:
            logger.warning(
                "mod_state_corrupt",
                error=str(e),
                path=str(self.state_file),
            )
            self._state = {}

    def save(self) -> None:
        """Save mod state to the state index file.

        Uses atomic write (temp file + rename) to prevent corruption.
        Creates the state directory if it doesn't exist.
        """
        # Ensure state directory exists
        self._state_dir.mkdir(parents=True, exist_ok=True)

        # Serialize state to JSON
        data = {
            filename: state.model_dump(mode="json")
            for filename, state in self._state.items()
        }
        json_content = json.dumps(data, indent=2)

        # Atomic write: write to temp file first, then rename
        temp_file = self.state_file.with_suffix(".tmp")
        try:
            temp_file.write_text(json_content)
            temp_file.rename(self.state_file)
            logger.debug(
                "mod_state_saved",
                mod_count=len(self._state),
                path=str(self.state_file),
            )
        except OSError as e:
            logger.error(
                "mod_state_save_failed",
                error=str(e),
                path=str(self.state_file),
            )
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise

    def get_mod(self, filename: str) -> ModState | None:
        """Get mod state by filename.

        Args:
            filename: The mod zip filename (e.g., "smithingplus_1.8.3.zip").

        Returns:
            ModState if found, None otherwise.
        """
        return self._state.get(filename)

    def get_mod_by_slug(self, slug: str) -> ModState | None:
        """Get mod state by slug (modid).

        Args:
            slug: The mod slug/modid (e.g., "smithingplus").

        Returns:
            ModState if found, None otherwise.
        """
        for state in self._state.values():
            if state.slug == slug:
                return state
        return None

    def list_mods(self) -> list[ModState]:
        """Get all mod states.

        Returns:
            List of all ModState objects.
        """
        return list(self._state.values())

    def set_mod_state(self, filename: str, state: ModState) -> None:
        """Set or update mod state.

        Args:
            filename: The mod zip filename (key in state index).
            state: The ModState to store.
        """
        self._state[filename] = state
        logger.debug(
            "mod_state_updated",
            filename=filename,
            slug=state.slug,
            enabled=state.enabled,
        )

    def remove_mod(self, filename: str) -> None:
        """Remove mod from state index.

        Args:
            filename: The mod zip filename to remove.
        """
        if filename in self._state:
            slug = self._state[filename].slug
            del self._state[filename]
            logger.info("mod_state_removed", filename=filename, slug=slug)

    def import_mod(self, zip_path: Path) -> ModMetadata:
        """Import a mod from a zip file.

        Extracts modinfo.json from the zip, parses metadata, and caches
        the modinfo.json to the state directory for fast future access.

        Args:
            zip_path: Path to the mod zip file.

        Returns:
            ModMetadata extracted from modinfo.json, or fallback metadata
            if modinfo.json is missing or corrupt.
        """
        filename = zip_path.name

        # Try to extract and parse modinfo.json from zip
        modinfo_data = self._extract_modinfo_from_zip(zip_path)

        if modinfo_data is not None:
            try:
                metadata = ModMetadata.model_validate(modinfo_data)

                # Cache the modinfo.json
                self._cache_modinfo(metadata.modid, metadata.version, modinfo_data)

                logger.info(
                    "mod_imported",
                    filename=filename,
                    modid=metadata.modid,
                    version=metadata.version,
                )
                return metadata
            except ValueError as e:
                logger.warning(
                    "modinfo_parse_failed",
                    filename=filename,
                    error=str(e),
                )

        # Fallback: use filename-derived metadata
        fallback_name = filename.removesuffix(".zip").removesuffix(".disabled")
        metadata = ModMetadata(
            modid=fallback_name,
            name=fallback_name,
            version="unknown",
        )
        logger.warning(
            "mod_imported_with_fallback",
            filename=filename,
            modid=metadata.modid,
        )
        return metadata

    def _is_safe_zip_path(self, name: str) -> bool:
        """Validate that a zip member path is safe (no path traversal).

        Uses Path.resolve() to detect path traversal attempts including:
        - ../etc/passwd (simple parent traversal)
        - subdir/../../etc/passwd (nested traversal)
        - /absolute/path (absolute paths)
        - \\windows\\path (Windows absolute paths)

        Args:
            name: The zip member name to validate.

        Returns:
            True if the path is safe, False if it attempts path traversal.
        """
        # Use a dummy base directory to simulate extraction
        base_dir = Path("/safe/base")
        base_resolved = base_dir.resolve()

        # Construct target path and resolve it
        target_path = (base_dir / name).resolve()

        # Check if resolved path stays within base directory
        try:
            target_path.relative_to(base_resolved)
            return True
        except ValueError:
            # Path escapes the base directory
            return False

    def _extract_modinfo_from_zip(self, zip_path: Path) -> dict[str, object] | None:
        """Extract modinfo.json content from a mod zip file.

        Args:
            zip_path: Path to the mod zip file.

        Returns:
            Parsed modinfo.json as dict, or None if not found or corrupt.
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Look for modinfo.json at the root of the zip
                for name in zf.namelist():
                    # Handle both root-level and any directory structure
                    if name.endswith("modinfo.json"):
                        # Security: validate path doesn't escape using resolve()
                        # This catches all path traversal attempts including:
                        # - ../etc/passwd
                        # - subdir/../../etc/passwd
                        # - /absolute/path
                        # - ./leading/dot
                        if not self._is_safe_zip_path(name):
                            logger.warning(
                                "modinfo_path_traversal_attempt",
                                filename=zip_path.name,
                                path=name,
                            )
                            continue

                        content = zf.read(name).decode("utf-8")
                        return json.loads(content)

                logger.debug(
                    "modinfo_not_found_in_zip",
                    filename=zip_path.name,
                )
                return None

        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
            logger.warning(
                "modinfo_extraction_failed",
                filename=zip_path.name,
                error=str(e),
            )
            return None

    def _cache_modinfo(self, slug: str, version: str, modinfo_data: dict[str, object]) -> None:
        """Cache modinfo.json to the state directory.

        Cache location: state/mods/<slug>/<version>/modinfo.json

        Args:
            slug: The mod slug (modid).
            version: The mod version.
            modinfo_data: The modinfo.json content as a dict.
        """
        # Validate slug and version don't contain path traversal
        if ".." in slug or "/" in slug or ".." in version or "/" in version:
            logger.warning(
                "cache_path_traversal_attempt",
                slug=slug,
                version=version,
            )
            return

        cache_dir = self._state_dir / "mods" / slug / version
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_file = cache_dir / "modinfo.json"
        cache_file.write_text(json.dumps(modinfo_data, indent=2))

        logger.debug(
            "modinfo_cached",
            slug=slug,
            version=version,
            path=str(cache_file),
        )

    def get_cached_metadata(self, slug: str, version: str) -> ModMetadata | None:
        """Get cached modinfo.json metadata.

        Args:
            slug: The mod slug (modid).
            version: The mod version.

        Returns:
            ModMetadata if cached, None otherwise.
        """
        # Validate slug and version don't contain path traversal
        if ".." in slug or "/" in slug or ".." in version or "/" in version:
            return None

        cache_file = self._state_dir / "mods" / slug / version / "modinfo.json"

        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text())
            return ModMetadata.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "cached_modinfo_corrupt",
                slug=slug,
                version=version,
                error=str(e),
            )
            return None

    def scan_mods_directory(self) -> list[str]:
        """Scan the mods directory for mod zip files.

        Discovers all .zip and .zip.disabled files in the mods directory.

        Returns:
            List of filenames (not full paths) of discovered mod files.
        """
        if not self._mods_dir.exists():
            logger.debug("mods_directory_not_found", path=str(self._mods_dir))
            return []

        filenames: list[str] = []

        for path in self._mods_dir.iterdir():
            if path.is_file():
                name = path.name
                if name.endswith(".zip") or name.endswith(".zip.disabled"):
                    filenames.append(name)

        logger.debug(
            "mods_directory_scanned",
            mod_count=len(filenames),
            path=str(self._mods_dir),
        )
        return filenames

    def sync_state_with_disk(self) -> None:
        """Reconcile state index with actual files in mods directory.

        - For each .zip file on disk not in state: import and add to state
        - For each state entry without matching file: remove from state
        - Saves state after making changes
        """
        disk_files = set(self.scan_mods_directory())
        state_files = set(self._state.keys())

        changes_made = False

        # New files: import and add to state
        for filename in disk_files - state_files:
            zip_path = self._mods_dir / filename
            metadata = self.import_mod(zip_path)

            # Determine if mod is disabled based on filename
            is_disabled = filename.endswith(".disabled")

            state = ModState(
                filename=filename,
                slug=metadata.modid,
                version=metadata.version,
                enabled=not is_disabled,
                installed_at=datetime.now(UTC),
            )
            self._state[filename] = state
            changes_made = True

            logger.info(
                "mod_state_added",
                filename=filename,
                slug=metadata.modid,
                enabled=not is_disabled,
            )

        # Deleted files: remove from state
        for filename in state_files - disk_files:
            slug = self._state[filename].slug
            del self._state[filename]
            changes_made = True

            logger.info(
                "mod_state_removed_deleted_file",
                filename=filename,
                slug=slug,
            )

        # Save if changes were made
        if changes_made:
            self.save()
            logger.info(
                "mod_state_synced",
                total_mods=len(self._state),
                added=len(disk_files - state_files),
                removed=len(state_files - disk_files),
            )
