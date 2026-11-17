"""Mod state persistence and management service.

This service manages the mod state index file (mods.json) which tracks
installed mods and their enabled/disabled status. It uses atomic writes
to prevent corruption.
"""

import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import structlog
from pydantic import TypeAdapter, ValidationError

from vintagestory_api.models.mods import ModMetadata, ModState

logger = structlog.get_logger()

FALLBACK_VERSION = "unknown"
"""Version recorded when a mod's modinfo.json cannot be read (filename fallback)."""

_JSON_OBJECT: TypeAdapter[dict[str, object]] = TypeAdapter(dict[str, object])
"""A modinfo.json must be a JSON object; its keys are always strings."""


@dataclass(frozen=True)
class ModSyncSummary:
    """What one run of `ModStateManager.sync_state_with_disk` changed (Epic 19 ADR-10)."""

    added: int
    removed: int
    skipped: int


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

    def filenames(self) -> list[str]:
        """Get the file names the state holds (its keys), as `get_mod` looks them up.

        Returns:
            List of the state's file names.
        """
        return list(self._state)

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

        Top-level keys are matched case-insensitively, as VintageStory does
        (for example "ModID" or "Version"); the cached modinfo.json holds them lowercased.

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
            version=FALLBACK_VERSION,
        )
        logger.warning(
            "mod_imported_with_fallback",
            filename=filename,
            modid=metadata.modid,
        )
        return metadata

    def read_modinfo(self, zip_path: Path) -> ModMetadata | None:
        """Read and validate an archive's modinfo.json without caching or fallback.

        Top-level keys are matched case-insensitively, as VintageStory does
        (for example "ModID" or "Version").

        Returns:
            The metadata, or None if modinfo.json is missing, unreadable or invalid.
        """
        data = self._extract_modinfo_from_zip(zip_path)
        if data is None:
            return None
        try:
            return ModMetadata.model_validate(data)
        except ValueError as e:
            logger.warning("modinfo_invalid", filename=zip_path.name, error=str(e))
            return None

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
            Parsed modinfo.json as dict, or None if not found or corrupt. Top-level keys
            are lowercased, as VintageStory matches them case-insensitively (for example
            "ModID" or "Version"); values, including nested objects, are unchanged. When
            two keys differ only in case, the later one in the file wins.
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

                        content = zf.read(name).decode("utf-8-sig")
                        try:
                            modinfo = _JSON_OBJECT.validate_python(json.loads(content))
                        except ValidationError:
                            logger.warning("modinfo_not_object", filename=zip_path.name)
                            return None
                        return {key.lower(): value for key, value in modinfo.items()}

                logger.debug(
                    "modinfo_not_found_in_zip",
                    filename=zip_path.name,
                )
                return None

        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as e:
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

    def repair_fallback_entries(self) -> list[str]:
        """Re-read mods whose stored metadata came from the filename fallback.

        Older builds stored a filename-derived slug and version "unknown" when they could
        not read a modinfo.json (for example `"side": "Universal"`). Each such entry whose
        archive now yields real metadata gets its slug and version updated; its enabled
        state, install time and asset id are kept. An entry is left alone if its file is
        missing, its archive is still unreadable, or the repaired slug belongs to another
        installed mod. Saves only when something changed.

        Returns:
            Filenames of the repaired entries.
        """
        repaired: list[str] = []
        for filename, entry in list(self._state.items()):
            if entry.version != FALLBACK_VERSION:
                continue
            path = self._mods_dir / filename
            if not path.is_file():
                continue
            metadata = self.import_mod(path)
            if metadata.version == FALLBACK_VERSION:
                continue
            other = self.get_mod_by_slug(metadata.modid)
            if other is not None and other.filename != filename:
                logger.warning(
                    "mod_state_repair_skipped_duplicate",
                    filename=filename,
                    slug=metadata.modid,
                    existing=other.filename,
                )
                continue
            self._state[filename] = entry.model_copy(
                update={"slug": metadata.modid, "version": metadata.version}
            )
            repaired.append(filename)
            logger.info(
                "mod_state_repaired",
                filename=filename,
                old_slug=entry.slug,
                slug=metadata.modid,
                version=metadata.version,
            )
        if repaired:
            self.save()
        return repaired

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

    def sync_state_with_disk(self) -> ModSyncSummary:
        """Bring the state in line with the mods directory (Epic 19 ADR-10).

        Meant to be called once, at start-up, before any mod operation can run: it
        changes the state without a mod lock.

        - Removed: an entry whose own file name is not in one listing of the mods
          directory. Nothing is removed when the directory does not exist or cannot be
          listed. An entry whose name is listed stays, whatever the file is.
        - Added: a `.zip` or `.zip.disabled` file without an entry whose `modinfo.json`
          is readable and valid, enabled unless its name ends in `.disabled`, with
          `asset_id` 0. Removals come first, so a mod renamed or replaced by hand keeps
          one entry under the file that is there.
        - Skipped, with a warning: an archive that cannot be read or has no usable
          `modinfo.json`, and an archive whose mod ID is already installed under
          another file.

        Creates, renames and deletes no file in the mods directory. Saves once, only
        when something changed; a failed save is logged and the in-memory state keeps
        the changes. Never raises for anything the directory or an archive can hold.

        Returns:
            The numbers of entries added and removed and of files skipped.
        """
        mods_dir = self._mods_dir
        if not mods_dir.is_dir():
            logger.warning("mod_state_sync_mods_directory_not_found", path=str(mods_dir))
            return self._log_sync_summary(ModSyncSummary(added=0, removed=0, skipped=0))
        try:
            names = {path.name for path in mods_dir.iterdir()}
            candidates = sorted(self.scan_mods_directory())
        except OSError as e:
            logger.warning(
                "mod_state_sync_mods_directory_unreadable", path=str(mods_dir), error=str(e)
            )
            return self._log_sync_summary(ModSyncSummary(added=0, removed=0, skipped=0))

        # Removals first: a hand rename or replacement is then one removal and one
        # addition, instead of the new file being skipped as a duplicate of its own mod
        removed = 0
        for filename in sorted(self._state):
            if filename in names:
                continue
            entry = self._state.pop(filename)
            removed += 1
            logger.info("mod_state_sync_removed", filename=filename, slug=entry.slug)

        # Mod IDs are compared lower-cased, as ModService._lock_key does
        by_mod_id: dict[str, str] = {}
        for filename in sorted(self._state):
            by_mod_id.setdefault(self._state[filename].slug.lower(), filename)

        added = 0
        skipped = 0
        now = datetime.now(UTC)
        for filename in candidates:
            if filename in self._state:
                continue
            metadata = self._read_new_archive(mods_dir / filename)
            if metadata is None:
                skipped += 1
                continue
            modinfo_data, metadata = metadata
            existing = by_mod_id.get(metadata.modid.lower())
            if existing is not None:
                skipped += 1
                logger.warning(
                    "mod_state_sync_skipped",
                    filename=filename,
                    reason="duplicate_mod_id",
                    slug=metadata.modid,
                    existing=existing,
                )
                continue
            try:
                self._cache_modinfo(metadata.modid, metadata.version, modinfo_data)
            except OSError as e:
                logger.warning(
                    "mod_state_sync_modinfo_not_cached",
                    filename=filename,
                    slug=metadata.modid,
                    error=str(e),
                )
            enabled = not filename.endswith(".disabled")
            self._state[filename] = ModState(
                filename=filename,
                slug=metadata.modid,
                version=metadata.version,
                enabled=enabled,
                installed_at=now,
            )
            by_mod_id[metadata.modid.lower()] = filename
            added += 1
            logger.info(
                "mod_state_sync_added",
                filename=filename,
                slug=metadata.modid,
                version=metadata.version,
                enabled=enabled,
            )

        if added or removed:
            try:
                self.save()
            except OSError as e:
                logger.error("mod_state_sync_save_failed", error=str(e), path=str(self.state_file))
        return self._log_sync_summary(ModSyncSummary(added=added, removed=removed, skipped=skipped))

    def _read_new_archive(self, path: Path) -> tuple[dict[str, object], ModMetadata] | None:
        """Read the modinfo.json of an archive the sync found, or log why it is skipped.

        Any exception is caught: the set that zipfile and json raise for a broken or
        hostile archive is open, and one bad file must not stop the API (ADR-10).
        """
        try:
            data = self._extract_modinfo_from_zip(path)
            if data is None:
                logger.warning("mod_state_sync_skipped", filename=path.name, reason="unreadable")
                return None
            return data, ModMetadata.model_validate(data)
        except Exception as e:
            logger.warning(
                "mod_state_sync_skipped",
                filename=path.name,
                reason="unreadable",
                error_type=type(e).__name__,
                error=str(e),
            )
            return None

    def _log_sync_summary(self, summary: ModSyncSummary) -> ModSyncSummary:
        """Log the one summary line of a sync and return the summary."""
        logger.info(
            "mod_state_synced",
            added=summary.added,
            removed=summary.removed,
            skipped=summary.skipped,
            total=len(self._state),
        )
        return summary
