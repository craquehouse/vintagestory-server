"""Mod management service orchestrator.

This service orchestrates mod state management, providing a unified interface
for listing, enabling, and disabling mods. It coordinates the ModStateManager
for state persistence and PendingRestartState for restart tracking.
"""

from pathlib import Path

import structlog

from vintagestory_api.config import Settings
from vintagestory_api.models.mods import ModInfo
from vintagestory_api.services.mod_state import ModStateManager
from vintagestory_api.services.pending_restart import PendingRestartState

logger = structlog.get_logger()

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

    Returns:
        ModService instance configured for the application.
    """
    global _mod_service
    if _mod_service is None:
        settings = Settings()
        state_dir = settings.vsmanager_dir / "state"
        mods_dir = settings.serverdata_dir / "Mods"

        _mod_service = ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            restart_state=get_restart_state(),
        )

        # Load existing state
        _mod_service.state_manager.load()

        logger.info(
            "mod_service_initialized",
            state_dir=str(state_dir),
            mods_dir=str(mods_dir),
        )

    return _mod_service


class ModNotFoundError(Exception):
    """Raised when a mod is not found by slug."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Mod '{slug}' not found")


class ModService:
    """Orchestrates mod management operations.

    Provides a unified interface for mod operations, coordinating:
    - ModStateManager for state persistence
    - PendingRestartState for restart tracking
    - File system operations for enable/disable

    Attributes:
        state_manager: The ModStateManager instance.
    """

    def __init__(
        self,
        state_dir: Path,
        mods_dir: Path,
        restart_state: PendingRestartState,
    ) -> None:
        """Initialize the mod service.

        Args:
            state_dir: Directory for state files (mods.json).
            mods_dir: Directory containing mod zip files.
            restart_state: Shared PendingRestartState for restart tracking.
        """
        self._state_manager = ModStateManager(state_dir=state_dir, mods_dir=mods_dir)
        self._restart_state = restart_state
        self._server_running = False

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

    def enable_mod(self, slug: str) -> None:
        """Enable a disabled mod.

        Renames the mod file from .zip.disabled to .zip and updates state.
        Sets pending_restart if the server is running.

        Args:
            slug: The mod slug (modid) to enable.

        Raises:
            ModNotFoundError: If the mod is not found.
        """
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
            raise ModNotFoundError(slug)

        # Already enabled - nothing to do
        if state.enabled:
            logger.debug("mod_already_enabled", slug=slug)
            return

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
        if self._server_running:
            self._restart_state.require_restart(f"Mod '{slug}' was enabled")

    def disable_mod(self, slug: str) -> None:
        """Disable an enabled mod.

        Renames the mod file from .zip to .zip.disabled and updates state.
        Sets pending_restart if the server is running.

        Args:
            slug: The mod slug (modid) to disable.

        Raises:
            ModNotFoundError: If the mod is not found.
        """
        state = self._state_manager.get_mod_by_slug(slug)
        if state is None:
            raise ModNotFoundError(slug)

        # Already disabled - nothing to do
        if not state.enabled:
            logger.debug("mod_already_disabled", slug=slug)
            return

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
        if self._server_running:
            self._restart_state.require_restart(f"Mod '{slug}' was disabled")
