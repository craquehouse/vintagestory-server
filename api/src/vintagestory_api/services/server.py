"""VintageStory server installation and lifecycle service."""

import asyncio
import hashlib
import re
import shutil
import tarfile
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
    ServerState,
    VersionInfo,
)

logger = structlog.get_logger()

# VintageStory API endpoints
VS_STABLE_API = "https://api.vintagestory.at/stable.json"
VS_UNSTABLE_API = "https://api.vintagestory.at/unstable.json"
VS_CDN_BASE = "https://cdn.vintagestory.at/gamefiles"

# Version pattern: X.Y.Z with optional pre-release suffix (-rc, -pre.1, -alpha.2)
# and optional build metadata (+build.123)
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+(?:\.\d+)?)?(?:\+[a-zA-Z0-9.]+)?$")

# Required server files to verify installation
REQUIRED_SERVER_FILES = ["VintagestoryServer.dll", "VintagestoryLib.dll"]


class ServerService:
    """Service for VintageStory server installation and lifecycle management."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the server service.

        Args:
            settings: Application settings. If None, creates new Settings instance.
        """
        self._settings = settings or Settings()
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

    @property
    def settings(self) -> Settings:
        """Get application settings."""
        return self._settings

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
        version_file = self._settings.server_dir / "current_version"
        if version_file.exists():
            return version_file.read_text().strip()
        return None

    def _save_installed_version(self, version: str) -> None:
        """Record installed version to file.

        Args:
            version: Version string that was installed.
        """
        version_file = self._settings.server_dir / "current_version"
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
            raise ValueError(
                f"Path traversal detected: {filename} escapes {base_dir}"
            ) from None

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

        Args:
            tarball_path: Path to tarball file.

        Raises:
            tarfile.TarError: If extraction fails.
        """
        self._install_stage = InstallationStage.EXTRACTING
        self._install_percentage = None

        logger.info("extracting_server", tarball=str(tarball_path))

        with tarfile.open(tarball_path, "r:gz") as tar:
            # filter="tar" preserves permissions while blocking path traversal attacks
            tar.extractall(self._settings.server_dir, filter="tar")

        # Clean up tarball after extraction
        tarball_path.unlink()
        logger.info("extraction_complete")

    def setup_directories_and_symlinks(self) -> None:
        """Create required directories and symlinks after installation.

        Creates:
        - /data/mods/ directory
        - /data/config/ directory
        - Copies default config files if /data/config/ is empty
        - Symlink: /data/server/Mods -> /data/mods/
        """
        self._install_stage = InstallationStage.CONFIGURING

        # Ensure directories exist
        self._settings.mods_dir.mkdir(parents=True, exist_ok=True)
        self._settings.config_dir.mkdir(parents=True, exist_ok=True)

        # Copy default config files if config dir is empty (AC: 1)
        if not any(self._settings.config_dir.iterdir()):
            # VintageStory extracts default configs to serverconfig.json in server dir
            server_config = self._settings.server_dir / "serverconfig.json"
            if server_config.exists():
                shutil.copy2(server_config, self._settings.config_dir)
                logger.info("default_config_copied", file="serverconfig.json")

        # Create symlink for mods (persist mods across updates)
        server_mods = self._settings.server_dir / "Mods"

        # Remove existing Mods directory/symlink if present
        if server_mods.is_symlink():
            server_mods.unlink()
        elif server_mods.is_dir():
            shutil.rmtree(server_mods)

        # Create symlink
        server_mods.symlink_to(self._settings.mods_dir)
        logger.info(
            "symlink_created",
            link=str(server_mods),
            target=str(self._settings.mods_dir),
        )

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
            self.setup_directories_and_symlinks()

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
