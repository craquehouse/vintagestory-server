"""Mod management service orchestrator.

This service orchestrates mod state management, providing a unified interface
for listing, enabling, disabling, and installing mods. It coordinates the
ModStateManager for state persistence, ModApiClient for external API access,
and PendingRestartState for restart tracking.
"""

import asyncio
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import structlog

from vintagestory_api.config import Settings
from vintagestory_api.models.mod_updates import StoredRelease
from vintagestory_api.models.mods import (
    CompatibilityInfo,
    DisableResult,
    EnableResult,
    ModInfo,
    ModLookupResponse,
    ModRelease,
    ModState,
    RemoveResult,
)
from vintagestory_api.services.cache_eviction import CacheEvictionService
from vintagestory_api.services.mod_api import (
    CompatibilityStatus,
    ExternalApiError,
    ModApiClient,
    ModVersionNotFoundError,
    check_compatibility,
    extract_slug,
    safe_release_filename,
    validate_slug,
)
from vintagestory_api.services.mod_api import (
    ModNotFoundError as ApiModNotFoundError,
)
from vintagestory_api.services.mod_state import ModStateManager
from vintagestory_api.services.mod_updates import installed_game_version, is_prerelease
from vintagestory_api.services.pending_restart import PendingRestartState

logger = structlog.get_logger()

# Version placeholder when server is not installed or version unknown
UNKNOWN_VERSION = "stable"

# Module-level service instance (singleton pattern)
_mod_service: ModService | None = None

# Shared restart state (shared with other services that may need it)
_restart_state: PendingRestartState | None = None


def get_restart_state() -> PendingRestartState:
    """Get or create the shared restart state singleton."""
    global _restart_state
    if _restart_state is None:
        _restart_state = PendingRestartState()
    return _restart_state


def get_mod_service() -> ModService:
    """Get or create the mod service singleton.

    Uses paths from Settings:
    - state_dir: {vsmanager_dir}/state
    - mods_dir: {serverdata_dir}/Mods
    - cache_dir: {vsmanager_dir}/cache (for downloaded mod files)

    Returns:
        ModService instance configured for the application.
    """
    global _mod_service
    if _mod_service is None:
        settings = Settings()
        state_dir = settings.vsmanager_dir / "state"
        mods_dir = settings.serverdata_dir / "Mods"
        cache_dir = settings.cache_dir

        _mod_service = ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            cache_dir=cache_dir,
            restart_state=get_restart_state(),
            game_version=settings.game_version,
            mod_cache_max_size_mb=settings.mod_cache_max_size_mb,
        )

        # Load existing state
        _mod_service.state_manager.load()

        logger.info(
            "mod_service_initialized",
            state_dir=str(state_dir),
            mods_dir=str(mods_dir),
            cache_dir=str(cache_dir),
            mod_cache_max_size_mb=settings.mod_cache_max_size_mb,
        )

    return _mod_service


async def close_mod_service() -> None:
    """Close the mod service singleton and release resources.

    Should be called during application shutdown to prevent resource leaks.
    Safe to call even if the service was never initialized.
    """
    global _mod_service
    if _mod_service is not None:
        await _mod_service.close()
        _mod_service = None


class ModNotFoundError(Exception):
    """Raised when a mod is not found by slug."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Mod '{slug}' not found")


class ModAlreadyInstalledError(Exception):
    """Raised when attempting to install a mod that is already installed."""

    def __init__(self, slug: str, current_version: str) -> None:
        self.slug = slug
        self.current_version = current_version
        super().__init__(f"Mod '{slug}' is already installed (version {current_version})")


class InvalidSlugError(Exception):
    """Raised when a mod slug is invalid."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Invalid mod slug: '{slug}'")


class ModConfirmationRequiredError(Exception):
    """Raised when a version change needs explicit confirmation (ADR-2)."""

    def __init__(
        self, slug: str, version: str, reasons: list[str], compatibility: CompatibilityStatus
    ) -> None:
        self.slug = slug
        self.version = version
        self.reasons = reasons
        self.compatibility = compatibility
        super().__init__(
            f"Changing '{slug}' to {version} needs confirmation: {', '.join(reasons)}"
        )


class ModValidationError(Exception):
    """Raised when a release archive is unusable or does not match the requested release."""

    def __init__(self, slug: str, message: str) -> None:
        self.slug = slug
        super().__init__(f"Release for mod '{slug}' failed validation: {message}")


class ModVersionChangeInProgressError(Exception):
    """Raised when a version change is requested while one is running for the same mod."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"A version change for mod '{slug}' is already in progress")


class ModVersionChangeFailedError(Exception):
    """Raised when placing the new file or updating state fails; the change is rolled back."""

    def __init__(self, slug: str, message: str) -> None:
        self.slug = slug
        super().__init__(f"Version change for mod '{slug}' failed: {message}")


@dataclass(frozen=True)
class VersionChangeResult:
    """Outcome of a version change."""

    slug: str
    previous_version: str
    version: str
    filename: str
    compatibility: CompatibilityStatus | None
    """Compatibility of the new version; None when nothing changed."""
    changed: bool
    pending_restart: bool


@dataclass(frozen=True)
class PreparedVersionChange:
    """A resolved, confirmed and validated version change, ready to apply."""

    target: StoredRelease
    archive: Path
    compatibility: CompatibilityStatus


@dataclass
class InstallResult:
    """Result of a mod installation operation."""

    success: bool
    """Whether the installation succeeded."""

    slug: str
    """The mod slug that was installed."""

    version: str
    """The installed version."""

    filename: str
    """The filename of the installed mod."""

    compatibility: CompatibilityStatus
    """Compatibility status with the game version."""

    pending_restart: bool
    """Whether a server restart is required."""


class ModService:
    """Orchestrates mod management operations.

    Provides a unified interface for mod operations, coordinating:
    - ModStateManager for state persistence
    - ModApiClient for external mod database API access
    - PendingRestartState for restart tracking
    - File system operations for enable/disable/install

    Attributes:
        state_manager: The ModStateManager instance.
    """

    def __init__(
        self,
        state_dir: Path,
        mods_dir: Path,
        restart_state: PendingRestartState,
        cache_dir: Path | None = None,
        game_version: str = "stable",
        mod_cache_max_size_mb: int = 500,
        game_version_provider: Callable[[], str | None] | None = None,
    ) -> None:
        """Initialize the mod service.

        Args:
            state_dir: Directory for state files (mods.json).
            mods_dir: Directory containing mod zip files.
            restart_state: Shared PendingRestartState for restart tracking.
            cache_dir: Directory for caching downloaded mods. Defaults to
                       state_dir.parent / "cache" if not provided.
            game_version: Game version for compatibility checking (e.g., "1.21.3").
            mod_cache_max_size_mb: Maximum cache size in MB (0 to disable eviction).
            game_version_provider: Returns the installed game version for version
                changes (Epic 14). Defaults to the installed server version.
        """
        self._state_manager = ModStateManager(state_dir=state_dir, mods_dir=mods_dir)
        self._restart_state = restart_state
        self._server_running = False

        # Set up cache directory with default
        if cache_dir is None:
            cache_dir = state_dir.parent / "cache"
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Set up cache eviction service
        self._cache_eviction = CacheEvictionService(
            cache_dir=cache_dir,
            max_size_mb=mod_cache_max_size_mb,
        )

        self._game_version = game_version
        self._game_version_provider = game_version_provider or installed_game_version
        self._mod_api_client: ModApiClient | None = None
        self._version_locks: dict[str, asyncio.Lock] = {}

    @property
    def state_manager(self) -> ModStateManager:
        """Get the ModStateManager instance."""
        return self._state_manager

    @property
    def restart_state(self) -> PendingRestartState:
        """Get the restart state instance.

        This allows endpoints to check pending restart status
        using the same restart state that the service uses.
        """
        return self._restart_state

    def set_server_running(self, running: bool) -> None:
        """Set the server running status.

        Used to determine whether to set pending_restart on mod changes.

        Args:
            running: Whether the server is currently running.
        """
        self._server_running = running

    def list_mods(self) -> list[ModInfo]:
        """List all installed mods with full metadata.

        Returns:
            List of ModInfo objects with combined state and metadata.
        """
        mods: list[ModInfo] = []
        for state in self._state_manager.list_mods():
            # Get cached metadata for full info
            metadata = self._state_manager.get_cached_metadata(state.slug, state.version)

            if metadata:
                mod_info = ModInfo(
                    filename=state.filename,
                    slug=state.slug,
                    version=state.version,
                    enabled=state.enabled,
                    installed_at=state.installed_at,
                    asset_id=state.asset_id,
                    name=metadata.name,
                    authors=metadata.authors,
                    description=metadata.description,
                    side=metadata.side,
                )
            else:
                # Fallback if no cached metadata
                mod_info = ModInfo(
                    filename=state.filename,
                    slug=state.slug,
                    version=state.version,
                    enabled=state.enabled,
                    installed_at=state.installed_at,
                    asset_id=state.asset_id,
                    name=state.slug,  # Use slug as name fallback
                )
            mods.append(mod_info)

        return mods

    def get_mod(self, slug: str) -> ModInfo | None:
        """Get mod info by slug.

        Args:
            slug: The mod slug (modid) to look up.

        Returns:
            ModInfo if found, None otherwise.
        """
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
            return None

        metadata = self._state_manager.get_cached_metadata(state.slug, state.version)

        if metadata:
            return ModInfo(
                filename=state.filename,
                slug=state.slug,
                version=state.version,
                enabled=state.enabled,
                installed_at=state.installed_at,
                asset_id=state.asset_id,
                name=metadata.name,
                authors=metadata.authors,
                description=metadata.description,
                side=metadata.side,
            )

        return ModInfo(
            filename=state.filename,
            slug=state.slug,
            version=state.version,
            enabled=state.enabled,
            installed_at=state.installed_at,
            asset_id=state.asset_id,
            name=state.slug,
        )

    def _build_compatibility_message(
        self,
        status: CompatibilityStatus,
        mod_version: str,
        game_version: str,
        compatible_tags: list[str] | None = None,
    ) -> str | None:
        """Build appropriate warning message for compatibility status.

        Args:
            status: The compatibility status.
            mod_version: The mod version being evaluated.
            game_version: The current game version.
            compatible_tags: List of compatible version tags (for incompatible status).

        Returns:
            Warning message string, or None for compatible status.
        """
        if status == "compatible":
            return None
        elif status == "not_verified":
            return f"Mod not explicitly verified for version {game_version}. May still work."
        else:  # incompatible
            if compatible_tags:
                versions = ", ".join(compatible_tags[:3])  # Show up to 3 versions
                if len(compatible_tags) > 3:
                    versions += "..."
                return (
                    f"Mod version {mod_version} is only compatible with {versions}. "
                    "Installation may cause issues."
                )
            return (
                f"Mod version {mod_version} is not compatible with {game_version}. "
                "Installation may cause issues."
            )

    async def lookup_mod(self, slug_or_url: str) -> ModLookupResponse:
        """Look up mod details and compatibility from the VintageStory mod database.

        Fetches mod information from mods.vintagestory.at and checks compatibility
        with the current game version.

        Args:
            slug_or_url: Mod slug (e.g., "smithingplus") or full URL
                         (e.g., "https://mods.vintagestory.at/smithingplus").

        Returns:
            ModLookupResponse with mod details and compatibility status.

        Raises:
            InvalidSlugError: If the slug format is invalid.
            ModNotFoundError: If the mod doesn't exist in the database.
            ExternalApiError: If the mod API is unavailable.
        """
        # Extract and validate slug
        slug = extract_slug(slug_or_url)
        logger.info("lookup_mod_start", slug=slug, input=slug_or_url)

        if not validate_slug(slug):
            raise InvalidSlugError(slug)

        # Fetch mod from API
        api_client = self._get_mod_api_client()
        mod = await api_client.get_mod(slug)

        if mod is None:
            raise ModNotFoundError(slug)

        # Get releases (API returns newest-first)
        releases = mod.get("releases", [])
        if not releases:
            raise ModNotFoundError(slug)

        latest_release = releases[0]
        mod_version = latest_release.get("modversion", "unknown")

        # Check compatibility with current game version
        game_version = self._game_version
        if not game_version or game_version == UNKNOWN_VERSION:
            # Server not installed or version unknown
            status: CompatibilityStatus = "not_verified"
            message = "Game server version unknown - cannot verify compatibility"
        else:
            status = check_compatibility(latest_release, game_version)
            message = self._build_compatibility_message(
                status,
                mod_version,
                game_version,
                latest_release.get("tags", []),
            )

        # Build response
        compatibility = CompatibilityInfo(
            status=status,
            game_version=game_version or "unknown",
            mod_version=mod_version,
            message=message,
        )

        # Calculate total downloads across all releases
        total_downloads = sum(r.get("downloads", 0) for r in releases)

        # Normalize side value to title case (API returns lowercase)
        raw_side = mod.get("side", "Both")
        side = raw_side.title() if raw_side else "Both"

        # Build release list from API data
        mod_releases = [
            ModRelease(
                version=r.get("modversion", "unknown"),
                filename=r.get("filename", ""),
                file_id=r.get("fileid", 0),
                downloads=r.get("downloads", 0),
                game_versions=r.get("tags", []),
                created=r.get("created", ""),
                changelog=r.get("changelog"),
            )
            for r in releases
        ]

        # Get slug from modidstrs[0] - this is what the /api/mod/{slug} endpoint expects
        # VSS-brs: urlalias differs from modidstrs for some mods, causing lookup failures
        modidstrs: list[str] = mod.get("modidstrs") or []
        response_slug: str = modidstrs[0] if modidstrs else slug

        result = ModLookupResponse(
            slug=response_slug,
            urlalias=mod.get("urlalias"),
            asset_id=int(mod.get("assetid", 0)),
            name=mod.get("name", slug),
            author=mod.get("author", "Unknown"),
            description=mod.get("text"),
            latest_version=mod_version,
            downloads=total_downloads,
            follows=mod.get("follows", 0),
            side=side,
            compatibility=compatibility,
            logo_url=mod.get("logofilename"),
            releases=mod_releases,
            tags=mod.get("tags", []),
            homepage_url=mod.get("homepageurl"),
            source_url=mod.get("sourcecodeurl"),
            created=mod.get("created"),
            last_released=mod.get("lastreleased"),
        )

        logger.info(
            "lookup_mod_complete",
            slug=result.slug,
            version=mod_version,
            compatibility=status,
        )

        return result

    def enable_mod(self, slug: str) -> EnableResult:
        """Enable a disabled mod.

        Renames the mod file from .zip.disabled to .zip and updates state.
        Sets pending_restart if the server is running.

        Args:
            slug: The mod slug (modid) to enable.

        Returns:
            EnableResult with the mod slug, enabled status, and pending restart flag.

        Raises:
            ModNotFoundError: If the mod is not found.
        """
        logger.debug("enable_mod_start", slug=slug)
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
            logger.debug("enable_mod_not_found", slug=slug)
            raise ModNotFoundError(slug)

        # Already enabled - idempotent success
        if state.enabled:
            logger.debug("mod_already_enabled", slug=slug)
            return EnableResult(slug=slug, enabled=True, pending_restart=False)

        # Rename file: remove .disabled suffix
        old_path = self._state_manager.mods_dir / state.filename
        new_filename = state.filename.removesuffix(".disabled")
        new_path = self._state_manager.mods_dir / new_filename

        old_path.rename(new_path)

        # Update state
        self._state_manager.remove_mod(state.filename)
        state.filename = new_filename
        state.enabled = True
        self._state_manager.set_mod_state(new_filename, state)
        self._state_manager.save()

        logger.info("mod_enabled", slug=slug, filename=new_filename)

        # Set pending restart if server is running
        pending_restart = False
        if self._server_running:
            self._restart_state.require_restart(f"Mod '{slug}' was enabled")
            pending_restart = True

        return EnableResult(slug=slug, enabled=True, pending_restart=pending_restart)

    def disable_mod(self, slug: str) -> DisableResult:
        """Disable an enabled mod.

        Renames the mod file from .zip to .zip.disabled and updates state.
        Sets pending_restart if the server is running.

        Args:
            slug: The mod slug (modid) to disable.

        Returns:
            DisableResult with the mod slug, enabled status, and pending restart flag.

        Raises:
            ModNotFoundError: If the mod is not found.
        """
        logger.debug("disable_mod_start", slug=slug)
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
            logger.debug("disable_mod_not_found", slug=slug)
            raise ModNotFoundError(slug)

        # Already disabled - idempotent success
        if not state.enabled:
            logger.debug("mod_already_disabled", slug=slug)
            return DisableResult(slug=slug, enabled=False, pending_restart=False)

        # Rename file: add .disabled suffix
        old_path = self._state_manager.mods_dir / state.filename
        new_filename = state.filename + ".disabled"
        new_path = self._state_manager.mods_dir / new_filename

        old_path.rename(new_path)

        # Update state
        self._state_manager.remove_mod(state.filename)
        state.filename = new_filename
        state.enabled = False
        self._state_manager.set_mod_state(new_filename, state)
        self._state_manager.save()

        logger.info("mod_disabled", slug=slug, filename=new_filename)

        # Set pending restart if server is running
        pending_restart = False
        if self._server_running:
            self._restart_state.require_restart(f"Mod '{slug}' was disabled")
            pending_restart = True

        return DisableResult(slug=slug, enabled=False, pending_restart=pending_restart)

    def remove_mod(self, slug: str) -> RemoveResult:
        """Remove an installed mod.

        Deletes the mod file from disk, removes it from state, and cleans up
        cached metadata. Sets pending_restart if the server is running.

        Args:
            slug: The mod slug (modid) to remove.

        Returns:
            RemoveResult with the mod slug and pending restart flag.

        Raises:
            ModNotFoundError: If the mod is not installed.
        """
        logger.debug("remove_mod_start", slug=slug)
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
            logger.debug("remove_mod_not_found", slug=slug)
            raise ModNotFoundError(slug)

        # Delete mod file from disk (handle both enabled and disabled)
        file_path = self._state_manager.mods_dir / state.filename
        if file_path.exists():
            file_path.unlink()
            logger.debug("mod_file_deleted", filename=state.filename)

        # Remove from state index
        self._state_manager.remove_mod(state.filename)
        self._state_manager.save()

        # Clean up cached metadata directory
        cache_dir = self._state_manager.state_dir / "mods" / slug
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            logger.debug("mod_cache_deleted", slug=slug, path=str(cache_dir))

        logger.info("mod_removed", slug=slug, filename=state.filename)

        # Set pending restart if server is running
        pending_restart = False
        if self._server_running:
            self._restart_state.require_restart(f"Mod '{slug}' was removed")
            pending_restart = True

        return RemoveResult(slug=slug, pending_restart=pending_restart)

    @property
    def api_client(self) -> ModApiClient:
        """Get the ModApiClient instance (lazy initialization).

        Provides access to the mod database API client for external use
        (e.g., by the mod_cache_refresh job).

        Returns:
            ModApiClient instance configured for this service.
        """
        if self._mod_api_client is None:
            self._mod_api_client = ModApiClient(
                cache_dir=self._cache_dir,
                cache_eviction_service=self._cache_eviction,
            )
        return self._mod_api_client

    @property
    def cache_eviction(self) -> CacheEvictionService:
        """Get the CacheEvictionService instance.

        Provides access to the cache eviction service for external use
        (e.g., for status queries or manual eviction).

        Returns:
            CacheEvictionService instance configured for this service.
        """
        return self._cache_eviction

    def _get_mod_api_client(self) -> ModApiClient:
        """Get or create the ModApiClient instance (lazy initialization).

        Deprecated: Use api_client property instead. Kept for internal compatibility.
        """
        return self.api_client

    async def close(self) -> None:
        """Close any open resources (HTTP clients, etc.).

        Should be called during application shutdown to prevent resource leaks.
        """
        if self._mod_api_client is not None:
            await self._mod_api_client.close()
            self._mod_api_client = None
            logger.debug("mod_api_client_closed")

    async def change_version(
        self, slug: str, version: str, *, confirm: bool = False
    ) -> VersionChangeResult:
        """Move an installed mod to another listed release: update or rollback (ADR-2).

        The installed file is replaced only after the new archive is validated, and any
        failure afterwards restores the original file and state.

        Raises:
            ModVersionChangeInProgressError: A change for this mod is already running.
            ModVersionChangeFailedError: Placing the file or saving state failed.
            See `_prepare_version_change` for lookup, confirmation and validation errors.
        """
        lock = self._version_locks.setdefault(slug, asyncio.Lock())
        if lock.locked():
            raise ModVersionChangeInProgressError(slug)
        async with lock:
            state = self._state_manager.get_mod_by_slug(slug)
            if state is None:
                raise ModNotFoundError(slug)
            if state.version == version:
                return VersionChangeResult(
                    slug=slug,
                    previous_version=state.version,
                    version=version,
                    filename=state.filename,
                    compatibility=None,
                    changed=False,
                    pending_restart=False,
                )

            prepared = await self._prepare_version_change(slug, version, confirm=confirm)
            filename = self._apply_version_change(state, prepared)

            pending_restart = False
            if self._server_running:
                self._restart_state.require_restart(
                    f"Mod '{slug}' changed from {state.version} to {version}"
                )
                pending_restart = True
            logger.info(
                "mod_version_changed",
                slug=slug,
                previous_version=state.version,
                version=version,
                filename=filename,
                pending_restart=pending_restart,
            )
            return VersionChangeResult(
                slug=slug,
                previous_version=state.version,
                version=version,
                filename=filename,
                compatibility=prepared.compatibility,
                changed=True,
                pending_restart=pending_restart,
            )

    def _apply_version_change(self, state: ModState, prepared: PreparedVersionChange) -> str:
        """Swap the validated archive into the mods directory and update state.

        Returns the new filename. On failure, restores the original file and state.
        """
        slug = state.slug
        mods_dir = self._state_manager.mods_dir
        mods_dir.mkdir(parents=True, exist_ok=True)
        new_name = prepared.archive.name if state.enabled else f"{prepared.archive.name}.disabled"
        old_path = mods_dir / state.filename
        new_path = mods_dir / new_name
        same_file = new_name == state.filename
        if new_path.exists() and not same_file:
            raise ModVersionChangeFailedError(
                slug, f"{new_name} already exists in the mods directory"
            )

        temp_path = new_path.with_name(new_path.name + ".tmp")
        # A reused filename would be overwritten by the rename, so keep the old file aside.
        backup_path = old_path.with_name(old_path.name + ".bak") if same_file else None
        try:
            shutil.copy2(prepared.archive, temp_path)
            if backup_path is not None:
                old_path.rename(backup_path)
            temp_path.rename(new_path)
        except OSError as e:
            temp_path.unlink(missing_ok=True)
            if backup_path is not None and backup_path.exists() and not old_path.exists():
                backup_path.rename(old_path)
            raise ModVersionChangeFailedError(slug, f"could not place the new file: {e}") from e

        old_state = state.model_copy()
        new_state = ModState(
            filename=new_name,
            slug=slug,
            version=prepared.target.modversion,
            enabled=state.enabled,
            installed_at=state.installed_at,
            asset_id=state.asset_id,
        )
        try:
            self._state_manager.remove_mod(state.filename)
            self._state_manager.set_mod_state(new_name, new_state)
            self._state_manager.save()
            if not same_file:
                # Required: with two copies of a modid the game loads one and the API
                # reports the other (Story 14.0).
                old_path.unlink()
        except OSError as e:
            self._rollback_version_change(old_state, new_name, new_path, backup_path)
            raise ModVersionChangeFailedError(slug, f"could not update state or files: {e}") from e

        if backup_path is not None:
            try:
                backup_path.unlink(missing_ok=True)
            except OSError as e:
                logger.warning(
                    "mod_version_backup_not_removed", path=str(backup_path), error=str(e)
                )
        try:
            self._state_manager.import_mod(new_path)
        except OSError as e:
            logger.warning("mod_version_metadata_not_cached", slug=slug, error=str(e))
        return new_name

    def _rollback_version_change(
        self, old_state: ModState, new_name: str, new_path: Path, backup_path: Path | None
    ) -> None:
        """Restore the original file and state after a failed swap."""
        self._state_manager.remove_mod(new_name)
        self._state_manager.set_mod_state(old_state.filename, old_state)
        try:
            self._state_manager.save()
        except OSError as e:
            logger.error("mod_version_rollback_state_not_saved", slug=old_state.slug, error=str(e))
        try:
            if backup_path is not None:
                backup_path.replace(new_path)
            else:
                new_path.unlink(missing_ok=True)
        except OSError as e:
            logger.error(
                "mod_version_rollback_file_not_restored", slug=old_state.slug, error=str(e)
            )
        logger.warning("mod_version_change_rolled_back", slug=old_state.slug)

    async def _prepare_version_change(
        self, slug: str, version: str, *, confirm: bool
    ) -> PreparedVersionChange:
        """Resolve, confirm and fetch the release a version change targets (ADR-1, ADR-2).

        Confirmation reasons are checked before anything is downloaded.

        Raises:
            ModNotFoundError: The mod is not installed.
            ApiModNotFoundError: The mod is not in the mod database.
            ModVersionNotFoundError: No release with this version for the installed modid.
            ModConfirmationRequiredError: Confirmation is needed and `confirm` is false.
            ModValidationError: The archive is unusable or is not the requested release.
            ExternalApiError, DownloadError: The mod database or download failed.
        """
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
            raise ModNotFoundError(slug)

        mod = await self.api_client.get_mod(slug)
        if mod is None:
            raise ApiModNotFoundError(slug)
        try:
            raw_releases: object = mod.get("releases") or []
            if not isinstance(raw_releases, list):
                raise TypeError("mod releases is not a list")
            releases = [StoredRelease.from_api(r) for r in cast(list[object], raw_releases)]
        except (TypeError, ValueError) as e:
            raise ExternalApiError(f"Unexpected mod database response: {e}") from e

        own = [r for r in releases if r.modidstr == slug]
        target_index = next((i for i, r in enumerate(own) if r.modversion == version), None)
        if target_index is None:
            raise ModVersionNotFoundError(slug, version)
        target = own[target_index]
        installed_index = next(
            (i for i, r in enumerate(own) if r.modversion == state.version), None
        )

        compatibility = check_compatibility(
            {"tags": target.tags}, self._game_version_provider() or ""
        )
        reasons: list[str] = []
        if compatibility != "compatible":
            reasons.append(compatibility)
        if is_prerelease(target.modversion) and not is_prerelease(state.version):
            reasons.append("prerelease")
        if installed_index is not None and target_index > installed_index:
            reasons.append("older")
        if reasons and not confirm:
            raise ModConfirmationRequiredError(slug, version, reasons, compatibility)

        archive = await self._acquire_release_archive(slug, target)
        return PreparedVersionChange(target=target, archive=archive, compatibility=compatibility)

    async def _acquire_release_archive(self, slug: str, target: StoredRelease) -> Path:
        """Return a validated archive for the release: a valid cached copy, or a download."""
        try:
            safe_name = safe_release_filename(target.filename)
        except ValueError as e:
            raise ModValidationError(slug, str(e)) from e

        cached = self._cache_dir / "mods" / safe_name
        if cached.exists():
            if self._archive_matches(cached, slug, target.modversion):
                logger.debug("mod_release_cache_hit", slug=slug, version=target.modversion)
                return cached
            self._discard_cached_archive(cached, slug)

        path = await self.api_client.download_release_file(slug, target.fileid, target.filename)
        if not self._archive_matches(path, slug, target.modversion):
            self._discard_cached_archive(path, slug)
            raise ModValidationError(
                slug, f"archive does not contain {slug} version {target.modversion}"
            )
        return path

    def _discard_cached_archive(self, path: Path, slug: str) -> None:
        """Delete a cache file that failed validation.

        A failed delete is logged, not raised: the download replaces the file by rename,
        and a file that stays behind is validated again before any later use.
        """
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning("mod_cache_discard_failed", slug=slug, path=str(path), error=str(e))

    def _archive_matches(self, path: Path, slug: str, version: str) -> bool:
        metadata = self._state_manager.read_modinfo(path)
        return (
            metadata is not None
            and metadata.modid.lower() == slug.lower()
            and metadata.version == version
        )

    async def install_mod(
        self,
        slug_or_url: str,
        version: str | None = None,
    ) -> InstallResult:
        """Install a mod from the VintageStory mod database.

        Downloads the mod from mods.vintagestory.at and installs it to the
        mods directory. Uses the download cache to avoid re-downloading.

        Args:
            slug_or_url: Mod slug (e.g., "smithingplus") or full URL
                         (e.g., "https://mods.vintagestory.at/smithingplus").
            version: Specific version to install, or None for latest.

        Returns:
            InstallResult with installation details.

        Raises:
            ModAlreadyInstalledError: If the mod is already installed.
            ApiModNotFoundError: If the mod doesn't exist in the database.
            ModVersionNotFoundError: If the specific version doesn't exist.
            ExternalApiError: If the mod API is unavailable.
            DownloadError: If the download fails.
        """
        # Extract slug from URL if needed
        slug = extract_slug(slug_or_url)
        logger.debug("install_mod_start", slug=slug, input=slug_or_url, version=version)

        # Check if already installed
        existing = self._state_manager.get_mod_by_slug(slug)
        if existing is not None:
            logger.debug(
                "install_mod_already_installed", slug=slug, current_version=existing.version
            )
            raise ModAlreadyInstalledError(slug, existing.version)

        # Download mod via API client
        api_client = self._get_mod_api_client()
        download_result = await api_client.download_mod(slug, version)

        if download_result is None:
            raise ApiModNotFoundError(slug)

        # Check compatibility with game version
        compatibility = check_compatibility(download_result.release, self._game_version)

        # Copy from cache to mods directory (atomic write pattern)
        dest_path = self._state_manager.mods_dir / download_result.filename
        temp_path = dest_path.with_name(dest_path.name + ".tmp")

        # Ensure mods directory exists
        self._state_manager.mods_dir.mkdir(parents=True, exist_ok=True)

        # Copy file from cache to mods directory using temp file + rename
        logger.debug(
            "mod_file_copy_start",
            source=str(download_result.path),
            dest=str(dest_path),
            temp=str(temp_path),
        )
        try:
            shutil.copy2(download_result.path, temp_path)
            temp_path.rename(dest_path)
            logger.debug(
                "mod_file_copy_complete",
                filename=download_result.filename,
                size_bytes=dest_path.stat().st_size,
            )
        except OSError:
            # Cleanup partial file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise

        # Import mod and save state - cleanup dest_path and state if anything fails
        try:
            # Import mod (extracts modinfo.json and caches metadata)
            logger.debug("mod_import_start", filename=download_result.filename)
            metadata = self._state_manager.import_mod(dest_path)
            logger.debug(
                "mod_import_complete",
                filename=download_result.filename,
                modid=metadata.modid,
                version=metadata.version,
            )

            # Create and save mod state
            mod_state = ModState(
                filename=download_result.filename,
                slug=metadata.modid,
                version=metadata.version,
                enabled=True,
                installed_at=datetime.now(UTC),
                asset_id=download_result.asset_id,
            )
            self._state_manager.set_mod_state(download_result.filename, mod_state)
            self._state_manager.save()
        except Exception:
            # Cleanup orphaned mod file on any failure
            if dest_path.exists():
                dest_path.unlink()
            # Remove from in-memory state if it was added
            self._state_manager.remove_mod(download_result.filename)
            logger.warning(
                "mod_install_cleanup",
                filename=download_result.filename,
                reason="import or state save failed",
            )
            raise

        # Determine if restart is needed
        pending_restart = False
        if self._server_running:
            self._restart_state.require_restart(f"Mod '{slug}' was installed")
            pending_restart = True

        logger.info(
            "mod_installed",
            slug=slug,
            version=download_result.version,
            filename=download_result.filename,
            compatibility=compatibility,
            pending_restart=pending_restart,
        )

        return InstallResult(
            success=True,
            slug=metadata.modid,
            version=download_result.version,
            filename=download_result.filename,
            compatibility=compatibility,
            pending_restart=pending_restart,
        )
