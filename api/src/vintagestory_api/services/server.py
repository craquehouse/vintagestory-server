"""VintageStory server installation and lifecycle service."""

import asyncio
import hashlib
import re
import signal
import tarfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import structlog

from vintagestory_api.config import Settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import (
    InstallationStage,
    InstallProgress,
    LifecycleAction,
    LifecycleResponse,
    ServerState,
    ServerStatus,
    VersionInfo,
)
from vintagestory_api.services.config_init_service import ConfigInitService
from vintagestory_api.services.console import ConsoleBuffer

# Lazy import to avoid circular dependency - imported at runtime when needed
_mod_service_module = None


def _get_mod_service_module():
    """Lazy import of mod service module to avoid circular imports."""
    global _mod_service_module
    if _mod_service_module is None:
        from vintagestory_api.services import mods as mod_service_module

        _mod_service_module = mod_service_module
    return _mod_service_module

logger = structlog.get_logger()

# Module-level service instance (singleton pattern for state tracking)
_server_service: "ServerService | None" = None


def get_server_service() -> "ServerService":
    """Get or create the server service singleton.

    Returns:
        ServerService instance configured for the application.
    """
    global _server_service
    if _server_service is None:
        _server_service = ServerService()
    return _server_service

# VintageStory API endpoints
VS_STABLE_API = "https://api.vintagestory.at/stable.json"
VS_UNSTABLE_API = "https://api.vintagestory.at/unstable.json"
VS_CDN_BASE = "https://cdn.vintagestory.at/gamefiles"

# Version pattern: X.Y.Z with optional pre-release suffix (-rc, -pre.1, -alpha.2)
# and optional build metadata (+build.123)
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+(?:\.\d+)?)?(?:\+[a-zA-Z0-9.]+)?$")

# Channel aliases that resolve to the latest version in that channel
VERSION_ALIASES = {"stable", "unstable"}

# Required server files to verify installation
REQUIRED_SERVER_FILES = ["VintagestoryServer.dll", "VintagestoryLib.dll"]


def _strip_numeric_prefix(name: str) -> str:
    """Strip leading numeric directory from tarball member names.

    The VintageStory tarball has malformed USTAR prefix fields containing
    garbage numeric data (inode numbers like 15070731126). Python's tarfile
    module correctly follows the USTAR spec and prepends these prefixes to
    filenames, but they should be stripped for correct extraction.

    Only strips prefixes that are 8+ digits to avoid accidentally stripping
    legitimate year-based directories (e.g., "2024/backup.tar").

    Args:
        name: Original member name from tarball.

    Returns:
        Name with leading numeric directory stripped if present.
    """
    parts = name.split("/", 1)
    # Only strip if first component is all digits AND at least 9 characters
    # (inode numbers are typically 10+ digits, years like 2025 are 4 digits)
    # Use >= 9 to avoid stripping legitimate 8-digit year-month directories like 20250128
    if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) >= 9:
        return parts[1]
    return name


def _vintagestory_tar_filter(member: tarfile.TarInfo, path: str) -> tarfile.TarInfo | None:
    """Custom extraction filter for VintageStory server tarballs.

    This filter handles two issues:
    1. Strips bogus numeric prefixes from USTAR archives with malformed prefix fields
    2. Applies the standard 'data' filter for security (blocks absolute paths,
       symlinks outside destination, device files, etc.)

    Args:
        member: TarInfo object for the member being extracted.
        path: Destination path for extraction.

    Returns:
        Modified TarInfo object or None to skip the member.
    """
    # Strip the bogus numeric prefix from member names
    member.name = _strip_numeric_prefix(member.name)

    # Also fix linkname if it's a symlink/hardlink
    if member.linkname:
        member.linkname = _strip_numeric_prefix(member.linkname)

    # Apply the standard 'data' filter for security
    return tarfile.data_filter(member, path)


class ServerService:
    """Service for VintageStory server installation and lifecycle management."""

    def __init__(
        self,
        settings: Settings | None = None,
        config_init_service: ConfigInitService | None = None,
    ) -> None:
        """Initialize the server service.

        Args:
            settings: Application settings. If None, creates new Settings instance.
            config_init_service: Config init service. If None, creates one with settings.
        """
        self._settings = settings or Settings()
        self._config_init_service = config_init_service or ConfigInitService(
            settings=self._settings
        )
        self._http_client: httpx.AsyncClient | None = None

        # Installation progress tracking
        self._install_state = ServerState.NOT_INSTALLED
        self._install_stage: InstallationStage | None = None
        self._install_percentage: int | None = None
        self._install_error: str | None = None
        self._install_error_code: str | None = None
        self._installing_version: str | None = None

        # Lock to prevent concurrent installations (race condition protection)
        self._install_lock = asyncio.Lock()

        # Process lifecycle management
        # Invariants:
        # - _process is None when no subprocess has been spawned
        # - _process.returncode is None while process is running
        # - _process.returncode is int after process terminates
        # - _server_state tracks lifecycle: INSTALLED (stopped), STARTING, RUNNING, STOPPING
        self._process: asyncio.subprocess.Process | None = None
        self._monitor_task: asyncio.Task[None] | None = None
        self._stdout_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._server_state: ServerState = ServerState.INSTALLED  # Runtime state
        self._last_exit_code: int | None = None
        self._server_start_time: float | None = None

        # Lock to prevent concurrent lifecycle operations
        self._lifecycle_lock = asyncio.Lock()

        # Console buffer for capturing server output
        self._console_buffer = ConsoleBuffer()

    @property
    def settings(self) -> Settings:
        """Get application settings."""
        return self._settings

    @property
    def config_init_service(self) -> ConfigInitService:
        """Get the config init service."""
        return self._config_init_service

    @property
    def console_buffer(self) -> ConsoleBuffer:
        """Get the console buffer for server output."""
        return self._console_buffer

    def _update_mod_service_server_state(self, running: bool) -> None:
        """Update the mod service with current server running state.

        This allows the mod service to know when to set pending_restart flags.
        Uses lazy import to avoid circular dependencies.

        Args:
            running: Whether the server is currently running.
        """
        try:
            mod_module = _get_mod_service_module()
            mod_service = mod_module.get_mod_service()
            mod_service.set_server_running(running)
            logger.debug("mod_service_server_state_updated", running=running)
        except Exception as e:
            # Non-fatal: mod service integration is optional
            logger.debug(
                "mod_service_update_skipped",
                reason=str(e),
                running=running,
            )

    def _clear_pending_restart(self) -> None:
        """Clear the pending restart state after successful server restart.

        Called after the server has been successfully restarted.
        """
        try:
            mod_module = _get_mod_service_module()
            restart_state = mod_module.get_restart_state()
            restart_state.clear_restart()
            logger.debug("pending_restart_cleared")
        except Exception as e:
            # Non-fatal: restart state integration is optional
            logger.debug("pending_restart_clear_skipped", reason=str(e))

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for API requests.

        Uses a 5-minute timeout for downloads (~40MB server tarball).
        """
        if self._http_client is None:
            # 300s timeout for large file downloads on slow connections
            self._http_client = httpx.AsyncClient(timeout=300.0)
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def validate_version(self, version: str) -> bool:
        """Validate version string format.

        Args:
            version: Version string to validate (e.g., "1.21.3" or "1.22.0-pre.1")

        Returns:
            True if version format is valid, False otherwise.
        """
        return VERSION_PATTERN.match(version) is not None

    def is_version_alias(self, version: str) -> bool:
        """Check if version string is an alias (e.g., "stable", "unstable").

        Args:
            version: Version string to check.

        Returns:
            True if version is an alias, False otherwise.
        """
        return version.lower() in VERSION_ALIASES

    async def resolve_version_alias(self, alias: str) -> str | None:
        """Resolve a version alias to the latest actual version number.

        Args:
            alias: Version alias ("stable" or "unstable").

        Returns:
            Latest version string for the channel, or None if not found.
        """
        channel = alias.lower()
        if channel not in VERSION_ALIASES:
            return None

        try:
            versions = await self.get_available_versions(channel)
            # Find version marked as latest
            for version, info in versions.items():
                if info.is_latest:
                    logger.info(
                        "resolved_version_alias",
                        alias=alias,
                        version=version,
                    )
                    return version

            # Fallback: if no version is marked as latest, return the highest version
            if versions:
                # Sort versions and return the highest
                sorted_versions = sorted(versions.keys(), reverse=True)
                latest = sorted_versions[0]
                logger.info(
                    "resolved_version_alias_fallback",
                    alias=alias,
                    version=latest,
                )
                return latest

            return None
        except httpx.HTTPError as e:
            logger.warning(
                "failed_to_resolve_alias",
                alias=alias,
                error=str(e),
            )
            return None

    async def get_available_versions(self, channel: str = "stable") -> dict[str, VersionInfo]:
        """Fetch available versions from VintageStory API.

        Args:
            channel: Release channel ("stable" or "unstable")

        Returns:
            Dictionary mapping version strings to VersionInfo objects.

        Raises:
            httpx.HTTPError: If API request fails.
        """
        api_url = VS_STABLE_API if channel == "stable" else VS_UNSTABLE_API
        client = await self._get_http_client()

        logger.info("fetching_versions", channel=channel, url=api_url)

        response = await client.get(api_url)
        response.raise_for_status()

        versions_data: dict[str, Any] = response.json()
        versions: dict[str, VersionInfo] = {}

        for version, platforms in versions_data.items():
            linux_server = platforms.get("linuxserver")
            if linux_server:
                versions[version] = VersionInfo(
                    version=version,
                    filename=linux_server["filename"],
                    filesize=linux_server["filesize"],
                    md5=linux_server["md5"],
                    cdn_url=linux_server["urls"]["cdn"],
                    local_url=linux_server["urls"]["local"],
                    is_latest=linux_server.get("latest", False),
                    channel=channel,
                )

        logger.info("versions_fetched", channel=channel, count=len(versions))
        return versions

    async def check_version_available(self, version: str) -> tuple[bool, str | None]:
        """Check if a specific version is available for download.

        Tries stable channel first, then unstable.

        Args:
            version: Version string to check (e.g., "1.21.3")

        Returns:
            Tuple of (is_available, channel) where channel is "stable" or "unstable"
            if found, None if not found.
        """
        if not self.validate_version(version):
            return False, None

        client = await self._get_http_client()

        # Try stable channel first
        for channel in ["stable", "unstable"]:
            url = f"{VS_CDN_BASE}/{channel}/vs_server_linux-x64_{version}.tar.gz"
            try:
                response = await client.head(url)
                if response.status_code == 200:
                    logger.info("version_found", version=version, channel=channel)
                    return True, channel
            except httpx.HTTPError as e:
                logger.warning(
                    "version_check_failed",
                    version=version,
                    channel=channel,
                    error=str(e),
                )

        logger.info("version_not_found", version=version)
        return False, None

    async def get_version_info(self, version: str) -> VersionInfo | None:
        """Get detailed information about a specific version.

        Args:
            version: Version string (e.g., "1.21.3")

        Returns:
            VersionInfo if version exists, None otherwise.
        """
        if not self.validate_version(version):
            return None

        # Try stable first, then unstable
        for channel in ["stable", "unstable"]:
            try:
                versions = await self.get_available_versions(channel)
                if version in versions:
                    return versions[version]
            except httpx.HTTPError:
                continue

        return None

    def get_install_progress(self) -> InstallProgress:
        """Get current installation progress.

        Returns:
            InstallProgress with current state and progress info.
        """
        # If there's an error state, return it (takes priority over file checks)
        if self._install_state == ServerState.ERROR:
            return InstallProgress(
                state=self._install_state,
                error=self._install_error,
                error_code=self._install_error_code,
                version=self._installing_version,
            )

        # If currently installing, return progress
        if self._install_state == ServerState.INSTALLING:
            return InstallProgress(
                state=self._install_state,
                stage=self._install_stage,
                percentage=self._install_percentage,
                version=self._installing_version,
            )

        # Check if already installed (based on files)
        if self.is_installed():
            installed_version = self.get_installed_version()
            return InstallProgress(
                state=ServerState.INSTALLED,
                version=installed_version,
            )

        # Default: not installed
        return InstallProgress(
            state=ServerState.NOT_INSTALLED,
        )

    def is_installed(self) -> bool:
        """Check if server is installed.

        Returns:
            True if server files exist and are valid.
        """
        server_dir = self._settings.server_dir
        return all((server_dir / f).exists() for f in REQUIRED_SERVER_FILES)

    def get_installed_version(self) -> str | None:
        """Get currently installed server version.

        Returns:
            Version string if installed, None otherwise.
        """
        version_file = self._settings.vsmanager_dir / "current_version"
        if version_file.exists():
            return version_file.read_text().strip()
        return None

    def _save_installed_version(self, version: str) -> None:
        """Record installed version to file.

        Args:
            version: Version string that was installed.
        """
        version_file = self._settings.vsmanager_dir / "current_version"
        # Atomic write: write to temp then rename
        temp_file = version_file.with_suffix(".tmp")
        temp_file.write_text(version)
        temp_file.rename(version_file)
        logger.info("version_saved", version=version)

    def _reset_install_state(self) -> None:
        """Reset installation state to not installed."""
        self._install_state = ServerState.NOT_INSTALLED
        self._install_stage = None
        self._install_percentage = None
        self._install_error = None
        self._install_error_code = None
        self._installing_version = None

    def _set_install_error(self, error: str, error_code: str | None = None) -> None:
        """Set installation error state.

        Args:
            error: Error message to record.
            error_code: Optional error code (e.g., ErrorCode.CHECKSUM_MISMATCH).
        """
        self._install_state = ServerState.ERROR
        self._install_error = error
        self._install_error_code = error_code
        logger.error("installation_error", error=error, error_code=error_code)

    def _safe_path(self, base_dir: Path, filename: str) -> Path:
        """Create a safe file path, preventing path traversal attacks.

        Args:
            base_dir: The base directory that must contain the result.
            filename: The filename to join (may contain malicious sequences).

        Returns:
            Safe path guaranteed to be within base_dir.

        Raises:
            ValueError: If the resulting path would escape base_dir.
        """
        # Resolve the base to absolute
        base_resolved = base_dir.resolve()

        # Create the target path and resolve it
        target = (base_dir / filename).resolve()

        # Verify the target is within the base directory
        try:
            target.relative_to(base_resolved)
        except ValueError:
            raise ValueError(f"Path traversal detected: {filename} escapes {base_dir}") from None

        return target

    async def download_server(
        self,
        version: str,
        channel: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> Path:
        """Download server tarball with streaming and progress tracking.

        Args:
            version: Version to download
            channel: Release channel ("stable" or "unstable")
            progress_callback: Optional callback(percentage: int) for progress updates

        Returns:
            Path to downloaded tarball.

        Raises:
            httpx.HTTPError: If download fails.
            ValueError: If version contains path traversal or is not found.
        """
        # Sanitize version to prevent path traversal attacks
        tarball_filename = f"vs_server_linux-x64_{version}.tar.gz"
        tarball_path = self._safe_path(self._settings.server_dir, tarball_filename)

        url = f"{VS_CDN_BASE}/{channel}/vs_server_linux-x64_{version}.tar.gz"

        # Ensure server directory exists
        self._settings.server_dir.mkdir(parents=True, exist_ok=True)

        self._install_stage = InstallationStage.DOWNLOADING
        self._install_percentage = 0

        client = await self._get_http_client()

        logger.info("downloading_server", version=version, url=url)

        async with client.stream("GET", url) as response:
            response.raise_for_status()

            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with tarball_path.open("wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        percentage = downloaded * 100 // total
                        self._install_percentage = percentage
                        if progress_callback:
                            progress_callback(percentage)

        logger.info("download_complete", version=version, size=downloaded)
        return tarball_path

    def verify_checksum(self, file_path: Path, expected_md5: str) -> bool:
        """Verify MD5 checksum of downloaded file.

        Args:
            file_path: Path to file to verify.
            expected_md5: Expected MD5 hash.

        Returns:
            True if checksum matches, False otherwise.
        """
        logger.info("verifying_checksum", file=str(file_path))

        md5_hash = hashlib.md5()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)

        actual_md5 = md5_hash.hexdigest()
        matches = actual_md5 == expected_md5

        if matches:
            logger.info("checksum_verified", file=str(file_path))
        else:
            logger.warning(
                "checksum_mismatch",
                file=str(file_path),
                expected=expected_md5,
                actual=actual_md5,
            )

        return matches

    def extract_server(self, tarball_path: Path) -> None:
        """Extract server tarball to server directory.

        Uses a custom filter to handle VintageStory tarballs which have malformed
        USTAR prefix fields. The filter strips bogus numeric prefixes and applies
        the standard 'data' filter for security.

        Args:
            tarball_path: Path to tarball file.

        Raises:
            tarfile.TarError: If extraction fails.
        """
        self._install_stage = InstallationStage.EXTRACTING
        self._install_percentage = None

        logger.info("extracting_server", tarball=str(tarball_path))

        with tarfile.open(tarball_path, "r:gz") as tar:
            # Use custom filter that handles VintageStory's malformed USTAR archives
            # and applies security protections from the 'data' filter
            tar.extractall(self._settings.server_dir, filter=_vintagestory_tar_filter)

        # Clean up tarball after extraction
        tarball_path.unlink()
        logger.info("extraction_complete")

    def setup_post_install(self) -> None:
        """Post-installation setup.

        Ensures serverdata directory exists for VintageStory's --dataPath.
        No symlinks needed - VintageStory manages its own data structure
        within the serverdata directory.
        """
        self._install_stage = InstallationStage.CONFIGURING

        # Ensure serverdata directory exists (VintageStory will populate it on first run)
        self._settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
        logger.info("serverdata_dir_ready", path=str(self._settings.serverdata_dir))

        # Ensure vsmanager directory exists (for version tracking, etc)
        self._settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)

    async def install_server(self, version: str) -> InstallProgress:
        """Install VintageStory server.

        Performs:
        1. Version validation and availability check
        2. Download with progress tracking
        3. Checksum verification
        4. Extraction
        5. Post-install setup (directories, symlinks)
        6. Version persistence

        Uses a lock to prevent race conditions from concurrent install requests.

        Args:
            version: Version to install (e.g., "1.21.3")

        Returns:
            InstallProgress with final state.

        Raises:
            ValueError: If version is invalid or not found.
            RuntimeError: If installation fails.
        """
        # Use lock to prevent race conditions from concurrent requests
        async with self._install_lock:
            return await self._install_server_locked(version)

    async def _install_server_locked(self, version: str) -> InstallProgress:
        """Internal installation logic (must be called with lock held)."""
        # Clear any previous error state to allow retry (AC3: return to not_installed)
        if self._install_state == ServerState.ERROR:
            self._reset_install_state()

        # Resolve version aliases (stable/unstable) to actual version numbers
        if version.lower() in VERSION_ALIASES:
            resolved = await self.resolve_version_alias(version)
            if resolved is None:
                self._set_install_error(
                    f"Could not resolve '{version}' to a specific version",
                    ErrorCode.VERSION_NOT_FOUND,
                )
                return self.get_install_progress()
            logger.info("version_alias_resolved", alias=version, resolved_version=resolved)
            version = resolved

        # Validate version format
        if not self.validate_version(version):
            self._set_install_error(
                f"Invalid version format: {version}",
                ErrorCode.INVALID_VERSION,
            )
            return self.get_install_progress()

        # Check if already installed
        if self.is_installed():
            installed_ver = self.get_installed_version()
            self._set_install_error(
                f"Server version {installed_ver} is already installed",
                ErrorCode.SERVER_ALREADY_INSTALLED,
            )
            return self.get_install_progress()

        # Check if installation in progress
        if self._install_state == ServerState.INSTALLING:
            self._set_install_error(
                "Installation already in progress",
                ErrorCode.INSTALLATION_IN_PROGRESS,
            )
            return self.get_install_progress()

        # Check version availability
        available, channel = await self.check_version_available(version)
        if not available or channel is None:
            self._set_install_error(
                f"Version {version} not found in stable or unstable channels",
                ErrorCode.VERSION_NOT_FOUND,
            )
            return self.get_install_progress()

        # Get version info for checksum
        version_info = await self.get_version_info(version)

        # Start installation
        self._install_state = ServerState.INSTALLING
        self._installing_version = version

        try:
            # Download
            tarball = await self.download_server(version, channel)

            # Verify checksum if available
            if version_info and version_info.md5:
                if not self.verify_checksum(tarball, version_info.md5):
                    tarball.unlink()  # Clean up
                    self._set_install_error(
                        "Downloaded server file checksum verification failed",
                        ErrorCode.CHECKSUM_MISMATCH,
                    )
                    return self.get_install_progress()

            # Extract
            self.extract_server(tarball)

            # Verify installation
            if not self.is_installed():
                self._set_install_error(
                    "Installation verification failed - required files missing",
                    ErrorCode.INSTALLATION_FAILED,
                )
                return self.get_install_progress()

            # Post-install setup
            self.setup_post_install()

            # Save version
            self._save_installed_version(version)

            # Success
            self._install_state = ServerState.INSTALLED
            self._install_stage = None
            self._install_percentage = None
            logger.info("installation_complete", version=version)

            return self.get_install_progress()

        except Exception as e:
            # Clean up on failure
            self._cleanup_failed_install()
            self._set_install_error(str(e), ErrorCode.INSTALLATION_FAILED)
            return self.get_install_progress()

    def _cleanup_failed_install(self) -> None:
        """Clean up partial installation after failure."""
        server_dir = self._settings.server_dir

        # Remove any downloaded tarballs
        for tarball in server_dir.glob("*.tar.gz"):
            tarball.unlink()
            logger.info("cleanup_tarball", file=str(tarball))

        # Remove extracted files
        for required_file in REQUIRED_SERVER_FILES:
            file_path = server_dir / required_file
            if file_path.exists():
                file_path.unlink()

        # Reset state
        self._reset_install_state()
        logger.info("cleanup_complete")

    # ============================================
    # Server Lifecycle Management
    # ============================================

    def get_server_status(self) -> ServerStatus:
        """Get current server runtime status.

        Returns:
            ServerStatus with current state, version, uptime, and exit code.
        """
        # If not installed, return not_installed state
        if not self.is_installed():
            return ServerStatus(state=ServerState.NOT_INSTALLED)

        # Determine current runtime state
        current_state = self._get_runtime_state()

        uptime_seconds = None
        if current_state == ServerState.RUNNING and self._server_start_time is not None:
            uptime_seconds = int(time.time() - self._server_start_time)

        return ServerStatus(
            state=current_state,
            version=self.get_installed_version(),
            uptime_seconds=uptime_seconds,
            last_exit_code=self._last_exit_code,
        )

    def _get_runtime_state(self) -> ServerState:
        """Get the current runtime state of the server process.

        Returns:
            Current ServerState based on process status.
        """
        # If process exists and is running
        if self._process is not None and self._process.returncode is None:
            return self._server_state

        # If we're in a transitional state, return it
        if self._server_state in (ServerState.STARTING, ServerState.STOPPING):
            return self._server_state

        # Process is not running - server is installed but stopped
        return ServerState.INSTALLED

    async def start_server(self) -> LifecycleResponse:
        """Start the game server subprocess.

        Returns:
            LifecycleResponse with action result.

        Raises:
            RuntimeError: If server cannot be started.
        """
        async with self._lifecycle_lock:
            return await self._start_server_locked()

    async def _start_server_locked(self) -> LifecycleResponse:
        """Internal start logic (must be called with lock held)."""
        previous_state = self._get_runtime_state()

        # Validate preconditions
        if not self.is_installed():
            logger.warning("start_server_failed", reason="not_installed")
            raise RuntimeError(ErrorCode.SERVER_NOT_INSTALLED)

        if previous_state == ServerState.RUNNING:
            logger.warning("start_server_failed", reason="already_running")
            raise RuntimeError(ErrorCode.SERVER_ALREADY_RUNNING)

        if previous_state == ServerState.STARTING:
            logger.warning("start_server_failed", reason="already_starting")
            raise RuntimeError(ErrorCode.SERVER_ALREADY_RUNNING)

        # Initialize config if needed (first run)
        if self._config_init_service.needs_initialization():
            self._config_init_service.initialize_config()
            logger.info("config_initialized", source="template+env")

        # Build command to run server
        # --dataPath tells VintageStory where to store persistent data (Mods, Saves, configs)
        # VintageStory expects a path relative to its data root (/data), so we extract
        # just the relative portion (e.g., "serverdata" from "/data/serverdata")
        serverdata_relative = self._settings.serverdata_dir.relative_to(
            self._settings.data_dir
        )
        command = [
            "dotnet",
            str(self._settings.server_dir / "VintagestoryServer.dll"),
            "--dataPath",
            str(serverdata_relative),
        ]

        logger.info(
            "starting_server",
            command=command,
            cwd=str(self._settings.data_dir),
            data_dir=str(self._settings.data_dir),
            serverdata_dir=str(self._settings.serverdata_dir),
            serverdata_relative=str(serverdata_relative),
        )

        self._server_state = ServerState.STARTING
        self._last_exit_code = None

        try:
            self._process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._settings.data_dir),  # Run from data dir for relative paths
            )

            # Record start time and update state
            self._server_start_time = time.time()
            self._server_state = ServerState.RUNNING

            # Start background monitoring task
            self._monitor_task = asyncio.create_task(self._monitor_process())

            # Start stream reader tasks for console capture
            self._stdout_task = asyncio.create_task(
                self._read_stream(self._process.stdout, "stdout")
            )
            self._stderr_task = asyncio.create_task(
                self._read_stream(self._process.stderr, "stderr")
            )

            logger.info(
                "server_started",
                pid=self._process.pid,
                state=self._server_state.value,
            )

            # Notify mod service that server is now running
            self._update_mod_service_server_state(True)

            return LifecycleResponse(
                action=LifecycleAction.START,
                previous_state=previous_state,
                new_state=self._server_state,
                message="Server start initiated",
            )

        except Exception as e:
            self._server_state = ServerState.INSTALLED
            logger.error("server_start_failed", error=str(e))
            raise RuntimeError(ErrorCode.SERVER_START_FAILED) from e

    async def stop_server(self, timeout: float = 10.0) -> LifecycleResponse:
        """Stop the game server gracefully, force kill after timeout.

        Args:
            timeout: Seconds to wait for graceful shutdown before SIGKILL.

        Returns:
            LifecycleResponse with action result.

        Raises:
            RuntimeError: If server cannot be stopped.
        """
        async with self._lifecycle_lock:
            return await self._stop_server_locked(timeout)

    async def _stop_server_locked(self, timeout: float) -> LifecycleResponse:
        """Internal stop logic (must be called with lock held)."""
        previous_state = self._get_runtime_state()

        # Validate preconditions
        if not self.is_installed():
            logger.warning("stop_server_failed", reason="not_installed")
            raise RuntimeError(ErrorCode.SERVER_NOT_INSTALLED)

        if self._process is None or self._process.returncode is not None:
            logger.warning("stop_server_failed", reason="not_running")
            raise RuntimeError(ErrorCode.SERVER_NOT_RUNNING)

        logger.info("stopping_server", pid=self._process.pid, timeout=timeout)

        self._server_state = ServerState.STOPPING

        try:
            # Send SIGTERM for graceful shutdown
            self._process.send_signal(signal.SIGTERM)

            try:
                await asyncio.wait_for(self._process.wait(), timeout=timeout)
                logger.info(
                    "server_stopped_gracefully",
                    returncode=self._process.returncode,
                )
            except TimeoutError:
                # Force kill after timeout
                logger.warning("server_stop_timeout", timeout=timeout)
                self._process.kill()
                await self._process.wait()
                logger.info(
                    "server_killed",
                    returncode=self._process.returncode,
                )

            self._last_exit_code = self._process.returncode
            self._server_state = ServerState.INSTALLED
            self._server_start_time = None

            # Cancel monitor and stream reader tasks if still running
            for task in [self._monitor_task, self._stdout_task, self._stderr_task]:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Notify mod service that server is no longer running
            self._update_mod_service_server_state(False)

            return LifecycleResponse(
                action=LifecycleAction.STOP,
                previous_state=previous_state,
                new_state=self._server_state,
                message="Server stopped",
            )

        except Exception as e:
            logger.error("server_stop_failed", error=str(e))
            raise RuntimeError(ErrorCode.SERVER_STOP_FAILED) from e

    async def restart_server(self, timeout: float = 10.0) -> LifecycleResponse:
        """Restart the game server (stop then start).

        Args:
            timeout: Seconds to wait for graceful shutdown before SIGKILL.

        Returns:
            LifecycleResponse with action result.

        Raises:
            RuntimeError: If server cannot be restarted.
        """
        async with self._lifecycle_lock:
            return await self._restart_server_locked(timeout)

    async def _restart_server_locked(self, timeout: float) -> LifecycleResponse:
        """Internal restart logic (must be called with lock held)."""
        previous_state = self._get_runtime_state()

        # Validate preconditions
        if not self.is_installed():
            logger.warning("restart_server_failed", reason="not_installed")
            raise RuntimeError(ErrorCode.SERVER_NOT_INSTALLED)

        # If running, stop first
        if self._process is not None and self._process.returncode is None:
            logger.info("restart_stopping_server")
            # Call the internal method directly (we already hold the lock)
            await self._stop_server_locked(timeout)

        # Now start the server
        logger.info("restart_starting_server")
        await self._start_server_locked()

        # Clear pending restart state since server has been restarted
        self._clear_pending_restart()

        return LifecycleResponse(
            action=LifecycleAction.RESTART,
            previous_state=previous_state,
            new_state=self._server_state,
            message="Server restarted",
        )

    async def _monitor_process(self) -> None:
        """Background task to monitor process and detect crashes."""
        if self._process is None:
            return

        try:
            # Wait for process to exit
            returncode = await self._process.wait()

            # Update state based on exit
            self._last_exit_code = returncode
            self._server_start_time = None

            # Only update state if we weren't already stopping
            if self._server_state != ServerState.STOPPING:
                self._server_state = ServerState.INSTALLED
                # Notify mod service that server is no longer running
                self._update_mod_service_server_state(False)
                if returncode == 0:
                    logger.info("server_exited_normally", returncode=returncode)
                else:
                    logger.warning(
                        "server_crashed",
                        returncode=returncode,
                        exit_code=returncode,
                    )

        except asyncio.CancelledError:
            # Monitor was cancelled during shutdown - this is expected
            pass
        except Exception as e:
            logger.error("monitor_error", error=str(e))

    async def _read_stream(
        self,
        stream: asyncio.StreamReader | None,
        stream_name: str,
    ) -> None:
        """Read lines from subprocess stream and add to console buffer.

        This coroutine runs continuously until the stream is exhausted (process exits).
        Each line is decoded, stripped, and added to the console buffer with a timestamp.

        Args:
            stream: The subprocess stdout or stderr stream.
            stream_name: Name for logging ("stdout" or "stderr").
        """
        if stream is None:
            return

        try:
            while True:
                line = await stream.readline()
                if not line:
                    break
                # Decode and strip the line, handle encoding errors gracefully
                text = line.decode("utf-8", errors="replace").rstrip()
                await self._console_buffer.append(text)
        except asyncio.CancelledError:
            # Stream reading cancelled during shutdown - expected
            pass
        except Exception as e:
            logger.error("stream_read_error", stream=stream_name, error=str(e))

    async def send_command(self, command: str) -> bool:
        """Send a command to the game server's stdin.

        The command is echoed to the console buffer with a [CMD] prefix for
        visibility, then written to the server process stdin.

        Args:
            command: The command to send (without trailing newline).

        Returns:
            True if command was sent, False if server not running.
        """
        if self._process is None or self._process.returncode is not None:
            logger.warning("send_command_failed", reason="server_not_running")
            return False

        if self._process.stdin is None:
            logger.warning("send_command_failed", reason="stdin_not_available")
            return False

        # Echo command to console buffer for visibility
        await self._console_buffer.append(f"[CMD] {command}")

        # Write to stdin with newline
        self._process.stdin.write(f"{command}\n".encode())
        await self._process.stdin.drain()

        logger.debug("command_sent", command_length=len(command))
        return True
