"""Mod management service orchestrator.

This service orchestrates mod state management, providing a unified interface
for listing, enabling, disabling, and installing mods. It coordinates the
ModStateManager for state persistence, ModApiClient for external API access,
and PendingRestartState for restart tracking.
"""

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import structlog

from vintagestory_api.config import Settings
from vintagestory_api.models.mods import (
    CompatibilityInfo,
    DisableResult,
    EnableResult,
    ModInfo,
    ModLookupResponse,
    ModState,
    RemoveResult,
)
from vintagestory_api.services.mod_api import (
    CompatibilityStatus,
    ModApiClient,
    check_compatibility,
    extract_slug,
    validate_slug,
)
from vintagestory_api.services.mod_api import (
    ModNotFoundError as ApiModNotFoundError,
)
from vintagestory_api.services.mod_state import ModStateManager
from vintagestory_api.services.pending_restart import PendingRestartState

logger = structlog.get_logger()

# Version placeholder when server is not installed or version unknown
UNKNOWN_VERSION = "stable"

# Module-level service instance (singleton pattern)
_mod_service: "ModService | None" = None

# Shared restart state (shared with other services that may need it)
_restart_state: PendingRestartState | None = None


def get_restart_state() -> PendingRestartState:
    """Get or create the shared restart state singleton."""
    global _restart_state
    if _restart_state is None:
        _restart_state = PendingRestartState()
    return _restart_state


def get_mod_service() -> "ModService":
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
        )

        # Load existing state
        _mod_service.state_manager.load()

        logger.info(
            "mod_service_initialized",
            state_dir=str(state_dir),
            mods_dir=str(mods_dir),
            cache_dir=str(cache_dir),
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
    ) -> None:
        """Initialize the mod service.

        Args:
            state_dir: Directory for state files (mods.json).
            mods_dir: Directory containing mod zip files.
            restart_state: Shared PendingRestartState for restart tracking.
            cache_dir: Directory for caching downloaded mods. Defaults to
                       state_dir.parent / "cache" if not provided.
            game_version: Game version for compatibility checking (e.g., "1.21.3").
        """
        self._state_manager = ModStateManager(state_dir=state_dir, mods_dir=mods_dir)
        self._restart_state = restart_state
        self._server_running = False

        # Set up cache directory with default
        if cache_dir is None:
            cache_dir = state_dir.parent / "cache"
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        self._game_version = game_version
        self._mod_api_client: ModApiClient | None = None

    @property
    def state_manager(self) -> ModStateManager:
        """Get the ModStateManager instance."""
        return self._state_manager

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
                    name=metadata.name,
                    authors=metadata.authors,
                    description=metadata.description,
                )
            else:
                # Fallback if no cached metadata
                mod_info = ModInfo(
                    filename=state.filename,
                    slug=state.slug,
                    version=state.version,
                    enabled=state.enabled,
                    installed_at=state.installed_at,
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
                name=metadata.name,
                authors=metadata.authors,
                description=metadata.description,
            )

        return ModInfo(
            filename=state.filename,
            slug=state.slug,
            version=state.version,
            enabled=state.enabled,
            installed_at=state.installed_at,
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

        result = ModLookupResponse(
            slug=mod.get("urlalias", slug),
            name=mod.get("name", slug),
            author=mod.get("author", "Unknown"),
            description=mod.get("text"),
            latest_version=mod_version,
            downloads=total_downloads,
            side=mod.get("side", "Both"),
            compatibility=compatibility,
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
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
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
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
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
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
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

    def _get_mod_api_client(self) -> ModApiClient:
        """Get or create the ModApiClient instance (lazy initialization)."""
        if self._mod_api_client is None:
            self._mod_api_client = ModApiClient(cache_dir=self._cache_dir)
        return self._mod_api_client

    async def close(self) -> None:
        """Close any open resources (HTTP clients, etc.).

        Should be called during application shutdown to prevent resource leaks.
        """
        if self._mod_api_client is not None:
            await self._mod_api_client.close()
            self._mod_api_client = None
            logger.debug("mod_api_client_closed")

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

        # Check if already installed
        existing = self._state_manager.get_mod_by_slug(slug)
        if existing is not None:
            raise ModAlreadyInstalledError(slug, existing.version)

        # Download mod via API client
        api_client = self._get_mod_api_client()
        download_result = await api_client.download_mod(slug, version)

        if download_result is None:
            raise ApiModNotFoundError(slug)

        # Check compatibility with game version
        compatibility = check_compatibility(
            download_result.release, self._game_version
        )

        # Copy from cache to mods directory (atomic write pattern)
        dest_path = self._state_manager.mods_dir / download_result.filename
        temp_path = dest_path.with_suffix(".tmp")

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
