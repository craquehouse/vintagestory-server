"""Mod management service orchestrator.

This service orchestrates mod state management, providing a unified interface
for listing, enabling, disabling, and installing mods. It coordinates the
ModStateManager for state persistence, ModApiClient for external API access,
and PendingRestartState for restart tracking.
"""

import shutil
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

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
    DownloadResult,
    ModApiClient,
    ModReleaseNotDownloadableError,
    ModVersionNotFoundError,
    ReleaseDict,
    check_compatibility,
    extract_slug,
    validate_slug,
)
from vintagestory_api.services.mod_api import (
    ModNotFoundError as ApiModNotFoundError,
)
from vintagestory_api.services.mod_compatibility import (
    SupportedRange,
    compare_game_versions,
    supported_game_versions,
)
from vintagestory_api.services.mod_file_recovery import (
    KEPT_ASIDE_SUFFIX,
    WORKING_COPY_SUFFIX,
    recover_working_files,
)
from vintagestory_api.services.mod_media import (
    build_screenshots,
    checked_url,
    external_link_url,
    mod_image_url,
    trailer_link_url,
)
from vintagestory_api.services.mod_release_selection import select_install_release
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
            # No game_version: compatibility follows the installed server version
            # (VSS-tpe). VS_GAME_VERSION, a former setting, is gone (Story 19.1).
            mod_cache_max_size_mb=settings.mod_cache_max_size_mb,
        )

        # Load existing state, then re-read mods that older builds imported with
        # filename fallback metadata (for example modinfo side "Universal")
        _mod_service.state_manager.load()
        _mod_service.state_manager.repair_fallback_entries()

        logger.info(
            "mod_service_initialized",
            state_dir=str(state_dir),
            mods_dir=str(mods_dir),
            cache_dir=str(cache_dir),
            mod_cache_max_size_mb=settings.mod_cache_max_size_mb,
        )

    return _mod_service


def prepare_mod_files() -> None:
    """Start-up work on the mods directory and the download cache (Epic 19 ADR-9, ADR-11).

    Called once by the API's lifespan, before the scheduler and the game server
    auto-start, so it runs before any mod operation. Steps, in order:
    1. recover the manager's working files (ADR-9 decisions 6-7);
    2. bring the mod state in line with the mods directory (ADR-10), after step 1 so
       that it sees the recovered files; it never raises;
    3. remove the download cache's old flat layout (ADR-11 decision 5).
    If step 1 raises, the sync does not run: an entry whose file is still kept aside
    would otherwise be removed.

    Uses the process settings through `get_mod_service()` (read from the environment),
    not the app factory's `settings`; the app factory's settings must match the
    environment.
    """
    service = get_mod_service()
    recover_working_files(service.state_manager)
    sync_mod_state_at_startup()
    removed = service.api_client.remove_flat_layout()
    if removed:
        logger.info("mod_cache_old_layout_removed", files=removed)


def sync_mod_state_at_startup() -> None:
    """Bring the mod state in line with the mods directory, once, at start-up (ADR-10).

    Runs before any request is served, any job is registered and the game server is
    auto-started, so it needs no mod lock; it must never be called from a route, a job
    or a thread. Any failure is logged and start-up continues.
    """
    try:
        get_mod_service().state_manager.sync_state_with_disk()
    except Exception as e:
        logger.error("mod_state_sync_failed", error_type=type(e).__name__, error=str(e))


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


class ModOperationInProgressError(Exception):
    """Raised when an install or version change is running for the same mod (Epic 17 ADR-3)."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(
            f"Another operation on mod '{slug}' is in progress. Try again when it has finished."
        )


ModFileOperation = Literal["install", "enable", "disable", "change the version of"]
"""The mod operations that place or rename a file, as their messages name them."""


class ModFileConflictError(Exception):
    """Raised when a name a mod operation would create is taken (Epic 19 ADR-8)."""

    def __init__(self, slug: str, filename: str, *, operation: ModFileOperation) -> None:
        self.slug = slug
        self.filename = filename
        self.operation = operation
        super().__init__(
            f"Cannot {operation} '{slug}': a file named {filename} "
            "already exists in the mods directory."
        )


class ModFileMissingError(Exception):
    """Raised when a mod's own file is no longer in the mods directory (Epic 19 ADR-9)."""

    def __init__(self, slug: str, filename: str, *, operation: ModFileOperation) -> None:
        self.slug = slug
        self.filename = filename
        self.operation = operation
        super().__init__(
            f"Cannot {operation} '{slug}': its file {filename} is no longer in the mods "
            "directory. Remove the mod and install it again."
        )


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
    releases: list[StoredRelease]
    """Every release of the mod database entry, newest first, from the change's lookup;
    internal, never serialized (Epic 18 ADR-5)."""


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

    releases: list[ReleaseDict]
    """Every release of the mod database entry, newest first, from the install's lookup.

    Not part of the API response: Story 17.4 stores them as the new mod's update record.
    """


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
        game_version: str | None = None,
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
            game_version: A fixed game version for compatibility checks (tests and
                tools). Ignored when `game_version_provider` is given.
            mod_cache_max_size_mb: Maximum cache size in MB (0 to disable eviction).
            game_version_provider: Returns the game version that lookups, installs and
                version changes check compatibility against. Defaults to the installed
                server version, read on each call (VSS-tpe). The former
                VS_GAME_VERSION setting was removed in Story 19.1.
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

        if game_version_provider is None:
            if game_version is not None:
                fixed: str = game_version

                def fixed_version() -> str:
                    return fixed

                game_version_provider = fixed_version
            else:
                game_version_provider = installed_game_version
        self._game_version_provider = game_version_provider
        self._mod_api_client: ModApiClient | None = None
        self._busy: set[str] = set()
        """Lock keys of the mods an install or version change is running for (ADR-3)."""

    @staticmethod
    def _lock_key(mod_id: str) -> str:
        """Mod IDs that differ only in case share a lock, as `_archive_matches` compares them."""
        return mod_id.lower()

    def _refuse_if_busy(self, mod_id: str) -> None:
        """Raise ModOperationInProgressError if an operation holds this mod's lock."""
        if self._lock_key(mod_id) in self._busy:
            raise ModOperationInProgressError(mod_id)

    def _refuse_taken_names(
        self,
        slug: str,
        names: tuple[str, ...],
        own: str | None,
        operation: ModFileOperation,
    ) -> None:
        """Raise ModFileConflictError when a name an operation will create is taken (ADR-8).

        Compares with casefold() against the mods directory listing (not probed, so a name
        that differs only in case and a dangling symlink count on every volume) and the
        state's keys. `own` (the mod's current file, None for an install) is never "taken".
        Working files (.vsm-tmp, .vsm-bak, old .tmp/.bak) are never one of `names`, so they
        never conflict (Epic 19 ADR-9 decision 8). The error names the entry in the way as
        it is spelled in the directory, or else in the state.
        """
        taken: dict[str, str] = {}
        for key in self._state_manager.filenames():
            taken.setdefault(key.casefold(), key)
        mods_dir = self._state_manager.mods_dir
        if mods_dir.is_dir():
            for path in mods_dir.iterdir():
                taken[path.name.casefold()] = path.name
        own_key = None if own is None else own.casefold()
        for name in names:
            key = name.casefold()
            if key != own_key and key in taken:
                raise ModFileConflictError(slug, taken[key], operation=operation)

    @contextmanager
    def _hold(self, mod_id: str) -> Generator[None]:
        """Hold the mod's lock for the block, refusing at once if it is held (never waits).

        The check and the take have no `await` between them, so they are atomic on the
        event loop. The key is released on every exit: return, error or cancellation.
        Use only as `with self._hold(...)`; never add or discard a key anywhere else.
        """
        self._refuse_if_busy(mod_id)
        key = self._lock_key(mod_id)
        self._busy.add(key)
        try:
            yield
        finally:
            self._busy.discard(key)

    @property
    def busy_mod_ids(self) -> frozenset[str]:
        """Lock keys of the mods an install or version change is running for (read-only)."""
        return frozenset(self._busy)

    def game_version(self) -> str | None:
        """The game version compatibility is checked against (installed server by default)."""
        return self._game_version_provider()

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
        supported: SupportedRange | None,
        tagged_elsewhere: bool = False,
    ) -> str | None:
        """Build the warning message for a compatibility status (Epic 16 ADR-2 decision 4).

        Args:
            status: The compatibility status of the evaluated release.
            mod_version: The evaluated release's version.
            game_version: The installed game version.
            supported: Lowest and highest game versions of the evaluated mod ID.
            tagged_elsewhere: Another release of the mod ID is tagged for the
                installed game version (only possible when an older release is evaluated).

        Returns:
            Warning message string, or None for compatible status.
        """
        if status == "compatible":
            return None

        game = game_version.lstrip("vV")
        if status == "not_verified":
            message = f"Mod not explicitly verified for version {game}. May still work."
            if supported is not None and compare_game_versions(supported.highest, game) == -1:
                message += f" Last tagged for {supported.highest}."
            return message

        # incompatible
        highest_vs_game = (
            compare_game_versions(supported.highest, game) if supported is not None else None
        )
        lowest_vs_game = (
            compare_game_versions(supported.lowest, game) if supported is not None else None
        )
        if supported is None or highest_vs_game is None or lowest_vs_game is None:
            return (
                f"Mod version {mod_version} is not compatible with {game}. "
                "Installation may cause issues."
            )
        # A range end equal to the installed version (e.g. tag "1.21.0" for "1.21", which
        # check_compatibility's string match misses) means another release has it
        if tagged_elsewhere or highest_vs_game == 0 or lowest_vs_game == 0:
            return (
                f"Version {mod_version} is not tagged for {game}; "
                "another release of this mod is."
            )
        if highest_vs_game < 0:
            return f"Last supported game version: {supported.highest}."
        if lowest_vs_game > 0:
            return f"Requires game version {supported.lowest} or newer (installed: {game})."
        return f"Not tagged for {game}; supports {supported.lowest} to {supported.highest}."

    def _compatibility_modid(
        self, slug: str, releases: list[ReleaseDict], default: str
    ) -> str:
        """The mod ID whose releases decide a lookup's compatibility (ADR-2 decision 2).

        Mirrors the web's `findInstalledModForEntry` (Story 16.2): the installed mod
        whose ID is the looked-up slug, otherwise the installed mod whose ID has the
        entry's newest release (exact comparison). When none of them is installed, or
        the match has no releases in the entry, `default`: the install mod ID, the mod
        ID an install of this slug installs (Epic 17 ADR-2 decision 6).
        """
        entry_ids: list[str] = []
        for release in releases:
            modid = release.get("modidstr") or ""
            if modid and modid not in entry_ids:
                entry_ids.append(modid)

        installed = {state.slug for state in self._state_manager.list_mods()}
        match = next((c for c in (slug, *entry_ids) if c in installed), None)
        if match is None or not any((r.get("modidstr") or "") == match for r in releases):
            return default
        return match

    async def lookup_mod(
        self, slug_or_url: str, version: str | None = None
    ) -> ModLookupResponse:
        """Look up mod details and compatibility from the VintageStory mod database.

        Fetches mod information from mods.vintagestory.at and checks compatibility
        with the current game version. Compatibility is reported for one mod ID of
        the entry (`_compatibility_modid`): for its newest release, or for its release
        `version` when given (the Installed list asks about the installed release).
        `install_mod_id` and `latest_version` are what an install of this slug without
        a version picks, from the same `select_install_release` that install uses
        (Epic 17 ADR-2 decisions 5 and 6). `screenshots`, `trailer_url`, `logo_url`,
        `homepage_url` and `source_url` pass only the URLs that `services/mod_media.py`
        allows (Epic 18 ADR-1, ADR-2; Epic 19 ADR-12); any other is None.

        Args:
            slug_or_url: Mod slug (e.g., "smithingplus") or full URL
                         (e.g., "https://mods.vintagestory.at/smithingplus").
            version: Release version (`modversion`) to evaluate instead of the newest.

        Returns:
            ModLookupResponse with mod details and compatibility status.

        Raises:
            InvalidSlugError: If the slug format is invalid.
            ModNotFoundError: If the mod doesn't exist in the database.
            ExternalApiError: If the mod API is unavailable.
        """
        # Extract and validate slug
        slug = extract_slug(slug_or_url)
        logger.info("lookup_mod_start", slug=slug, input=slug_or_url, version=version)

        if not validate_slug(slug):
            raise InvalidSlugError(slug)

        # Fetch mod from API
        api_client = self._get_mod_api_client()
        mod = await api_client.get_mod(slug)

        if mod is None:
            raise ModNotFoundError(slug)

        # Get releases (API returns newest-first)
        # Normalized by get_mod (Story 17.1, Epic 17 ADR-1): read the fields directly
        releases: list[ReleaseDict] = mod["releases"]
        if not releases:
            raise ModNotFoundError(slug)

        # Story 17.2 (Epic 17 ADR-2): what a plain install of this slug picks
        selection = select_install_release(slug, releases)
        latest_version = (
            (selection.release["modversion"] or "unknown")
            if selection.release is not None
            else None
        )

        # Story 16.3 (ADR-2 decisions 2 and 3): evaluate one mod ID's release
        modid = self._compatibility_modid(slug, releases, selection.mod_id)
        own = [r for r in releases if (r.get("modidstr") or "") == modid]
        supported = supported_game_versions(own, modid)
        if version is None:
            evaluated: ReleaseDict | None = own[0]
        else:
            evaluated = next((r for r in own if r["modversion"] == version), None)
        mod_version: str = (
            (evaluated["modversion"] or "unknown") if evaluated is not None else str(version)
        )

        # Check compatibility with the installed game version (VSS-tpe)
        game_version = self.game_version()
        if evaluated is None:
            status: CompatibilityStatus = "not_verified"
            message: str | None = (
                f"Version {version} is not listed in the mod database; "
                "cannot verify compatibility."
            )
        elif not game_version or game_version == UNKNOWN_VERSION:
            # Server not installed or version unknown
            status = "not_verified"
            message = "Game server version unknown - cannot verify compatibility"
        else:
            status = check_compatibility(evaluated, game_version)
            tagged_elsewhere = status == "incompatible" and any(
                check_compatibility(r, game_version) == "compatible" for r in own
            )
            message = self._build_compatibility_message(
                status, mod_version, game_version, supported, tagged_elsewhere
            )

        # Build response
        compatibility = CompatibilityInfo(
            status=status,
            game_version=game_version or "unknown",
            mod_version=mod_version,
            message=message,
            latest_supported_game_version=supported.highest if supported else None,
        )

        # Calculate total downloads across all releases
        total_downloads = sum(r["downloads"] for r in releases)

        # Normalize side value to title case (API returns lowercase)
        side = mod["side"].title() if mod["side"] else "Both"

        # Build release list from API data. A release without a downloadable file has
        # file_id None (Epic 17 ADR-1). An empty version shows as "unknown": an empty
        # value would break the web's version select.
        mod_releases = [
            ModRelease(
                version=r["modversion"] or "unknown",
                filename=r["filename"],
                file_id=r["fileid"],
                downloads=r["downloads"],
                game_versions=r["tags"],
                created=r["created"],
                changelog=r["changelog"],
                modidstr=r["modidstr"],
            )
            for r in releases
        ]

        # Get slug from modidstrs[0] - this is what the /api/mod/{slug} endpoint expects
        # VSS-brs: urlalias differs from modidstrs for some mods, causing lookup failures
        modidstrs: list[str] = mod["modidstrs"]
        response_slug: str = modidstrs[0] if modidstrs else slug

        result = ModLookupResponse(
            slug=response_slug,
            urlalias=mod["urlalias"],
            asset_id=mod["assetid"],
            name=mod["name"] or slug,
            author=mod["author"] or "Unknown",
            description=mod["text"],
            latest_version=latest_version,
            install_mod_id=selection.mod_id,
            downloads=total_downloads,
            follows=mod["follows"],
            side=side,
            compatibility=compatibility,
            logo_url=checked_url(
                mod["logofilename"], mod_image_url, slug=response_slug, field="logo_url"
            ),
            releases=mod_releases,
            tags=mod["tags"],
            homepage_url=checked_url(
                mod["homepageurl"], external_link_url, slug=response_slug, field="homepage_url"
            ),
            source_url=checked_url(
                mod["sourcecodeurl"], external_link_url, slug=response_slug, field="source_url"
            ),
            created=mod["created"],
            last_released=mod["lastreleased"],
            screenshots=build_screenshots(mod["screenshots"], response_slug),
            trailer_url=trailer_link_url(mod["trailervideourl"]),
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

        Refused while an install or version change is running for the mod, even if the
        mod is not installed yet or already enabled.
        Does not take the mod's lock: this method is synchronous, so nothing can run
        between its checks and its writes. If it ever becomes `async` or moves to a
        thread, it must hold the lock with `_hold`.

        Args:
            slug: The mod slug (modid) to enable.

        Returns:
            EnableResult with the mod slug, enabled status, and pending restart flag.

        Raises:
            ModOperationInProgressError: An install or version change is running for the mod.
            ModNotFoundError: If the mod is not found.
            ModFileMissingError: The mod's own file is no longer in the mods directory
                (Epic 19 ADR-9).
            ModFileConflictError: The enabled file name is taken in the mods directory or
                the mod state, ignoring case (Epic 19 ADR-8).
        """
        logger.debug("enable_mod_start", slug=slug)
        self._refuse_if_busy(slug)
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

        # A file removed by hand cannot be renamed (Epic 19 ADR-9); a directory or a
        # dangling symlink under the name counts as missing
        if not old_path.is_file():
            raise ModFileMissingError(slug, state.filename, operation="enable")
        # Never replace a file: a rename onto a taken name would (Epic 19 ADR-8)
        self._refuse_taken_names(slug, (new_filename,), state.filename, "enable")
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

        Refused while an install or version change is running for the mod, even if the
        mod is not installed yet or already disabled.
        Does not take the mod's lock: this method is synchronous, so nothing can run
        between its checks and its writes. If it ever becomes `async` or moves to a
        thread, it must hold the lock with `_hold`.

        Args:
            slug: The mod slug (modid) to disable.

        Returns:
            DisableResult with the mod slug, enabled status, and pending restart flag.

        Raises:
            ModOperationInProgressError: An install or version change is running for the mod.
            ModNotFoundError: If the mod is not found.
            ModFileMissingError: The mod's own file is no longer in the mods directory
                (Epic 19 ADR-9).
            ModFileConflictError: The disabled file name is taken in the mods directory or
                the mod state, ignoring case (Epic 19 ADR-8).
        """
        logger.debug("disable_mod_start", slug=slug)
        self._refuse_if_busy(slug)
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

        # A file removed by hand cannot be renamed (Epic 19 ADR-9); a directory or a
        # dangling symlink under the name counts as missing
        if not old_path.is_file():
            raise ModFileMissingError(slug, state.filename, operation="disable")
        # Never replace a file: a rename onto a taken name would (Epic 19 ADR-8)
        self._refuse_taken_names(slug, (new_filename,), state.filename, "disable")
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

        Refused while an install or version change is running for the mod, even if the
        mod is not installed yet.
        Does not take the mod's lock: this method is synchronous, so nothing can run
        between its checks and its writes. If it ever becomes `async` or moves to a
        thread, it must hold the lock with `_hold`.

        Args:
            slug: The mod slug (modid) to remove.

        Returns:
            RemoveResult with the mod slug and pending restart flag.

        Raises:
            ModOperationInProgressError: An install or version change is running for the mod.
            ModNotFoundError: If the mod is not installed.
        """
        logger.debug("remove_mod_start", slug=slug)
        self._refuse_if_busy(slug)
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
        self,
        slug: str,
        version: str,
        *,
        confirm: bool = False,
        record_releases: Callable[[str, list[StoredRelease]], None] | None = None,
    ) -> VersionChangeResult:
        """Move an installed mod to another listed release: update or rollback (ADR-2).

        The installed file is replaced only after the new archive is validated, and any
        failure afterwards restores the original file and state.

        Holds the mod's lock (Epic 17 ADR-3) for the whole call, so no other operation on
        the mod can run during the lookup and the download.

        A completed change hands its lookup's releases to `record_releases`, under the
        mod's lock (Story 18.2, Epic 18 ADR-5). The same-version return and every raise
        never call it. The recorder must not raise.

        Raises:
            ModOperationInProgressError: An install or version change is running for this mod.
            ModFileConflictError: The release's file name, or its .disabled form, is taken
                in the mods directory or the mod state, ignoring case (Epic 19 ADR-8).
            ModVersionChangeFailedError: Placing the file or saving state failed.
            ModReleaseNotDownloadableError: The target release has no downloadable file.
            See `_prepare_version_change` for lookup, confirmation and validation errors.
        """
        with self._hold(slug):
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
            if record_releases is not None:
                record_releases(slug, prepared.releases)

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

        Refuses before writing anything when the release's file name, or its .disabled
        form, is taken by another file or state entry, ignoring case (Epic 19 ADR-8).
        Returns the new filename. On a later failure, restores the original file and state.

        Raises:
            ModFileConflictError: A name the change would create is taken.
            ModVersionChangeFailedError: Placing the file or saving state failed.
        """
        slug = state.slug
        release_name = prepared.archive.name
        self._refuse_taken_names(
            slug,
            (release_name, f"{release_name}.disabled"),
            state.filename,
            "change the version of",
        )
        mods_dir = self._state_manager.mods_dir
        mods_dir.mkdir(parents=True, exist_ok=True)
        new_name = release_name if state.enabled else f"{release_name}.disabled"
        old_path = mods_dir / state.filename
        new_path = mods_dir / new_name
        # A name that differs only in case is the same file on a case-insensitive volume,
        # so it takes the same-file path on every volume (Epic 19 ADR-8 decision 4)
        same_file = new_name.casefold() == state.filename.casefold()

        # The working copy, renamed into place once complete; recovery deletes a leftover
        temp_path = new_path.with_name(new_path.name + WORKING_COPY_SUFFIX)
        # A reused filename would be overwritten by the rename, so keep the old file aside;
        # recovery puts it back, or deletes it once the state names the new file (ADR-9)
        backup_path = (
            old_path.with_name(old_path.name + KEPT_ASIDE_SUFFIX) if same_file else None
        )
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
                # Back under the original name, which a case-only change does not share
                # with the new file: remove that file first (Story 19.4)
                old_path = new_path.with_name(old_state.filename)
                if new_path.name != old_path.name:
                    new_path.unlink(missing_ok=True)
                backup_path.replace(old_path)
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
            ModReleaseNotDownloadableError: That release has no downloadable file
                (checked before confirmation).
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
        # Normalized by get_mod (Epic 17 ADR-1): a list of release objects
        releases = [StoredRelease.from_api(r) for r in mod["releases"]]

        own = [r for r in releases if r.modidstr == slug]
        target_index = next((i for i, r in enumerate(own) if r.modversion == version), None)
        if target_index is None:
            raise ModVersionNotFoundError(slug, version)
        target = own[target_index]
        # StoredRelease stores "no file" as 0 (Epic 17 ADR-1); refuse before confirming
        if target.fileid <= 0:
            raise ModReleaseNotDownloadableError(slug, version)
        installed_index = next(
            (i for i, r in enumerate(own) if r.modversion == state.version), None
        )

        compatibility = check_compatibility(
            {"tags": target.tags}, self.game_version() or ""
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
        return PreparedVersionChange(
            target=target, archive=archive, compatibility=compatibility, releases=releases
        )

    async def _acquire_release_archive(self, slug: str, target: StoredRelease) -> Path:
        """Return a validated archive for the release: a valid cached copy, or a download."""
        try:
            cached = self.api_client.cache_path(target.fileid, target.filename)
        except ValueError as e:
            raise ModValidationError(slug, str(e)) from e

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

        Holds the lock (Epic 17 ADR-3) of the install mod ID (Epic 17 ADR-2), which is
        only known after the mod database lookup, from then until it returns. A busy or
        installed mod is refused before the lookup when it is the requested slug, before
        the download when it is the install mod ID, and before anything is placed when
        it is the mod ID the downloaded archive's modinfo.json names.

        Args:
            slug_or_url: Mod slug (e.g., "smithingplus") or full URL
                         (e.g., "https://mods.vintagestory.at/smithingplus").
            version: Specific version to install, or None for the newest stable
                release of the mod ID that has a downloadable file (Epic 17 ADR-2).

        Returns:
            InstallResult with installation details.

        Raises:
            ModOperationInProgressError: An install or version change is running for the
                requested slug, the install mod ID or the archive's mod ID.
            ModAlreadyInstalledError: If the mod (the requested slug, the install mod ID
                or the archive's mod ID) is already installed.
            ModFileConflictError: If the download's file name, or its .disabled form, is
                already in the mods directory or the mod state, ignoring case (Epic 18
                ADR-4, Epic 19 ADR-8).
            ApiModNotFoundError: If the mod doesn't exist in the database.
            ModVersionNotFoundError: If no release of the mod ID has that version.
            ModReleaseNotDownloadableError: If the release to install has no file.
            ExternalApiError: If the mod API is unavailable.
            DownloadError: If the download fails.
        """
        # Extract slug from URL if needed
        slug = extract_slug(slug_or_url)
        logger.debug("install_mod_start", slug=slug, input=slug_or_url, version=version)

        # 1-2. Fast paths for the requested slug, before any network request
        self._refuse_if_busy(slug)
        self._refuse_if_installed(slug)

        # 3. Resolve the install mod ID; no lock is held and nothing is written yet
        api_client = self._get_mod_api_client()
        resolved = await api_client.resolve_install(slug, version)

        # 4. No await since the lookup: the state may have changed during it
        self._refuse_if_busy(resolved.mod_id)
        self._refuse_if_installed(resolved.mod_id)

        # 5. Hold the install mod ID until the install returns
        with self._hold(resolved.mod_id):
            download_result = await api_client.download_resolved(resolved)
            # 6. Check the archive's own mod ID before anything is placed. No await
            # from here to the state save, so it is checked, not held.
            archive = self._state_manager.read_modinfo(download_result.path)
            if archive is not None and archive.modid != resolved.mod_id:
                if self._lock_key(archive.modid) != self._lock_key(resolved.mod_id):
                    self._refuse_if_busy(archive.modid)
                self._refuse_if_installed(archive.modid)
            # 7. Place the file and save state
            return self._place_install(slug, download_result, resolved.releases)

    def _refuse_if_installed(self, mod_id: str) -> None:
        """Raise ModAlreadyInstalledError if `mod_id` is installed, ignoring case.

        Compared like the lock key, since an archive may spell its mod ID differently
        from the mod database (an installed `Demo` is the mod `demo`). The error names
        the installed spelling.
        """
        key = self._lock_key(mod_id)
        existing = next(
            (m for m in self._state_manager.list_mods() if self._lock_key(m.slug) == key), None
        )
        if existing is not None:
            logger.debug(
                "install_mod_already_installed",
                slug=existing.slug,
                requested=mod_id,
                current_version=existing.version,
            )
            raise ModAlreadyInstalledError(existing.slug, existing.version)

    def _place_install(
        self, slug: str, download_result: DownloadResult, releases: list[ReleaseDict]
    ) -> InstallResult:
        """Copy a downloaded archive into the mods directory, import it and save state.

        Refuses before writing anything when the download's file name, or its .disabled
        form, is already in the mods directory or the mod state, names compared ignoring
        case (Epic 18 ADR-4, Epic 19 ADR-8), so an install never replaces another mod's
        file and its cleanup never removes one.

        Synchronous on purpose: `install_mod` checks the archive's mod ID just before this,
        and no other operation may run between that check and the state save.

        Raises:
            ModFileConflictError: The file name, or its .disabled form, is in use.
        """
        name = download_result.filename
        self._refuse_taken_names(slug, (name, f"{name}.disabled"), None, "install")

        # Check compatibility with game version
        compatibility = check_compatibility(download_result.release, self.game_version() or "")

        # Copy from cache to mods directory (atomic write pattern)
        dest_path = self._state_manager.mods_dir / download_result.filename
        # The working copy, renamed into place once complete; recovery deletes a leftover
        temp_path = dest_path.with_name(dest_path.name + WORKING_COPY_SUFFIX)

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
            releases=releases,
        )
