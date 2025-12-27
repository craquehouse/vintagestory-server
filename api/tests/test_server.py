"""Tests for VintageStory server installation service."""

import hashlib
import io
import re
import shutil
import tarfile
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.models.server import InstallationStage, ServerState
from vintagestory_api.routers.server import get_server_service
from vintagestory_api.services.server import (
    VS_CDN_BASE,
    VS_STABLE_API,
    VS_UNSTABLE_API,
    ServerService,
)

# pyright: reportPrivateUsage=false

# Mock VintageStory API response
MOCK_STABLE_API_RESPONSE = {
    "1.21.6": {
        "linuxserver": {
            "filename": "vs_server_linux-x64_1.21.6.tar.gz",
            "filesize": "40.2 MB",
            "md5": "abc123def456",
            "urls": {
                "cdn": "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz",
                "local": "https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz",
            },
            "latest": True,
        },
        "windowsserver": {},
    },
    "1.21.5": {
        "linuxserver": {
            "filename": "vs_server_linux-x64_1.21.5.tar.gz",
            "filesize": "40.1 MB",
            "md5": "xyz789abc",
            "urls": {
                "cdn": "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.5.tar.gz",
                "local": "https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_1.21.5.tar.gz",
            },
            "latest": False,
        },
    },
}

MOCK_UNSTABLE_API_RESPONSE = {
    "1.22.0-pre.1": {
        "linuxserver": {
            "filename": "vs_server_linux-x64_1.22.0-pre.1.tar.gz",
            "filesize": "41.0 MB",
            "md5": "pre123hash",
            "urls": {
                "cdn": "https://cdn.vintagestory.at/gamefiles/unstable/vs_server_linux-x64_1.22.0-pre.1.tar.gz",
                "local": "https://vintagestory.at/api/gamefiles/unstable/vs_server_linux-x64_1.22.0-pre.1.tar.gz",
            },
            "latest": True,
        },
    },
}


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_settings(temp_data_dir: Path) -> Settings:
    """Create test settings with temporary data directory."""
    return Settings(
        data_dir=temp_data_dir,
        api_key_admin="test-admin-key",
    )


@pytest.fixture
async def server_service(
    test_settings: Settings,
) -> AsyncGenerator[ServerService, None]:
    """Create a server service for testing."""
    service = ServerService(test_settings)
    yield service
    await service.close()


class TestVersionValidation:
    """Tests for version format validation (Subtask 1.4)."""

    def test_valid_release_version(self, test_settings: Settings) -> None:
        """Valid release version format (X.Y.Z) passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.21.3") is True

    def test_valid_prerelease_version(self, test_settings: Settings) -> None:
        """Valid pre-release version format (X.Y.Z-pre.N) passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-pre.1") is True

    def test_valid_rc_version(self, test_settings: Settings) -> None:
        """Valid RC version format passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-rc.2") is True

    def test_valid_rc_version_without_number(self, test_settings: Settings) -> None:
        """Valid RC version without suffix number passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-rc") is True

    def test_valid_alpha_version(self, test_settings: Settings) -> None:
        """Valid alpha version format passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-alpha") is True
        assert service.validate_version("1.22.0-alpha.1") is True

    def test_valid_beta_version(self, test_settings: Settings) -> None:
        """Valid beta version format passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-beta.3") is True

    def test_valid_version_with_build_metadata(self, test_settings: Settings) -> None:
        """Valid version with build metadata passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.21.3+build.123") is True
        assert service.validate_version("1.22.0-pre.1+build.456") is True

    def test_invalid_version_missing_patch(self, test_settings: Settings) -> None:
        """Version without patch number fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.21") is False

    def test_invalid_version_extra_part(self, test_settings: Settings) -> None:
        """Version with extra parts fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.21.3.4") is False

    def test_invalid_version_text(self, test_settings: Settings) -> None:
        """Version with random text fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("latest") is False

    def test_invalid_version_empty(self, test_settings: Settings) -> None:
        """Empty version string fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("") is False

    def test_invalid_version_letters_in_numbers(self, test_settings: Settings) -> None:
        """Version with letters in numeric parts fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.2a.3") is False


class TestPathTraversalProtection:
    """Tests for path traversal attack prevention (Security)."""

    def test_safe_path_normal_filename(self, test_settings: Settings) -> None:
        """Normal filename returns valid path within base dir."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        service = ServerService(test_settings)

        result = service._safe_path(test_settings.server_dir, "test.tar.gz")

        # Use resolve() on expected path too (handles symlinks like /var -> /private/var)
        expected = (test_settings.server_dir / "test.tar.gz").resolve()
        assert result == expected

    def test_safe_path_blocks_parent_traversal(self, test_settings: Settings) -> None:
        """Path with .. traversal is rejected."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        service = ServerService(test_settings)

        with pytest.raises(ValueError, match="Path traversal detected"):
            service._safe_path(test_settings.server_dir, "../../../etc/passwd")

    def test_safe_path_blocks_absolute_path(self, test_settings: Settings) -> None:
        """Absolute path is rejected."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        service = ServerService(test_settings)

        with pytest.raises(ValueError, match="Path traversal detected"):
            service._safe_path(test_settings.server_dir, "/etc/passwd")

    def test_safe_path_blocks_version_with_traversal(self, test_settings: Settings) -> None:
        """Version string containing traversal is rejected."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        service = ServerService(test_settings)

        malicious_version = "1.21.3/../../../etc/passwd"
        filename = f"vs_server_linux-x64_{malicious_version}.tar.gz"

        with pytest.raises(ValueError, match="Path traversal detected"):
            service._safe_path(test_settings.server_dir, filename)


class TestGetAvailableVersions:
    """Tests for fetching available versions from VintageStory API (Subtask 1.2)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_stable_versions_success(self, server_service: ServerService) -> None:
        """Successfully fetch available stable versions."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))

        versions = await server_service.get_available_versions("stable")

        assert len(versions) == 2
        assert "1.21.6" in versions
        assert "1.21.5" in versions
        assert versions["1.21.6"].is_latest is True
        assert versions["1.21.5"].is_latest is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_unstable_versions_success(self, server_service: ServerService) -> None:
        """Successfully fetch available unstable versions."""
        respx.get(VS_UNSTABLE_API).mock(return_value=Response(200, json=MOCK_UNSTABLE_API_RESPONSE))

        versions = await server_service.get_available_versions("unstable")

        assert len(versions) == 1
        assert "1.22.0-pre.1" in versions
        assert versions["1.22.0-pre.1"].channel == "unstable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_info_contains_all_fields(self, server_service: ServerService) -> None:
        """Version info includes all expected fields."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))

        versions = await server_service.get_available_versions("stable")
        version = versions["1.21.6"]

        assert version.version == "1.21.6"
        assert version.filename == "vs_server_linux-x64_1.21.6.tar.gz"
        assert version.filesize == "40.2 MB"
        assert version.md5 == "abc123def456"
        assert "cdn.vintagestory.at" in version.cdn_url
        assert version.channel == "stable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_versions_api_error(self, server_service: ServerService) -> None:
        """API error raises HTTPStatusError."""
        respx.get(VS_STABLE_API).mock(return_value=Response(500))

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            await server_service.get_available_versions("stable")


class TestCheckVersionAvailable:
    """Tests for checking version availability (Subtask 1.3)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_stable_version_available(self, server_service: ServerService) -> None:
        """Version available in stable channel returns True with channel."""
        url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.3.tar.gz"
        respx.head(url).mock(return_value=Response(200))

        available, channel = await server_service.check_version_available("1.21.3")

        assert available is True
        assert channel == "stable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_unstable_version_available_fallback(self, server_service: ServerService) -> None:
        """Version available only in unstable channel found via fallback."""
        stable_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.22.0-pre.1.tar.gz"
        unstable_url = f"{VS_CDN_BASE}/unstable/vs_server_linux-x64_1.22.0-pre.1.tar.gz"

        respx.head(stable_url).mock(return_value=Response(404))
        respx.head(unstable_url).mock(return_value=Response(200))

        available, channel = await server_service.check_version_available("1.22.0-pre.1")

        assert available is True
        assert channel == "unstable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_not_found_any_channel(self, server_service: ServerService) -> None:
        """Version not found in any channel returns False."""
        stable_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.99.0.tar.gz"
        unstable_url = f"{VS_CDN_BASE}/unstable/vs_server_linux-x64_1.99.0.tar.gz"

        respx.head(stable_url).mock(return_value=Response(404))
        respx.head(unstable_url).mock(return_value=Response(404))

        available, channel = await server_service.check_version_available("1.99.0")

        assert available is False
        assert channel is None

    @pytest.mark.asyncio
    async def test_invalid_version_format_returns_false(
        self, server_service: ServerService
    ) -> None:
        """Invalid version format returns False without making API calls."""
        available, channel = await server_service.check_version_available("invalid")

        assert available is False
        assert channel is None


class TestGetVersionInfo:
    """Tests for getting detailed version information (Subtask 1.3)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_version_info_stable(self, server_service: ServerService) -> None:
        """Get version info for stable version."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))

        info = await server_service.get_version_info("1.21.6")

        assert info is not None
        assert info.version == "1.21.6"
        assert info.md5 == "abc123def456"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_version_info_unstable_fallback(self, server_service: ServerService) -> None:
        """Get version info for unstable version via fallback."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))
        respx.get(VS_UNSTABLE_API).mock(return_value=Response(200, json=MOCK_UNSTABLE_API_RESPONSE))

        info = await server_service.get_version_info("1.22.0-pre.1")

        assert info is not None
        assert info.version == "1.22.0-pre.1"
        assert info.channel == "unstable"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_version_info_not_found(self, server_service: ServerService) -> None:
        """Get version info for non-existent version returns None."""
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=MOCK_STABLE_API_RESPONSE))
        respx.get(VS_UNSTABLE_API).mock(return_value=Response(200, json=MOCK_UNSTABLE_API_RESPONSE))

        info = await server_service.get_version_info("1.99.0")

        assert info is None

    @pytest.mark.asyncio
    async def test_get_version_info_invalid_format(self, server_service: ServerService) -> None:
        """Get version info for invalid format returns None."""
        info = await server_service.get_version_info("invalid")

        assert info is None


class TestInstallProgress:
    """Tests for installation progress tracking (AC: 2)."""

    def test_initial_state_not_installed(self, test_settings: Settings) -> None:
        """Initial state is not_installed when server not present."""
        service = ServerService(test_settings)
        progress = service.get_install_progress()

        assert progress.state.value == "not_installed"
        assert progress.stage is None
        assert progress.percentage is None
        assert progress.error is None

    def test_installed_state_when_files_exist(self, test_settings: Settings) -> None:
        """State is installed when server files exist."""
        # Create required server files
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.server_dir / "VintagestoryServer.dll").touch()
        (test_settings.server_dir / "VintagestoryLib.dll").touch()
        (test_settings.server_dir / "current_version").write_text("1.21.3")

        service = ServerService(test_settings)
        progress = service.get_install_progress()

        assert progress.state.value == "installed"
        assert progress.version == "1.21.3"


class TestServerInstallation:
    """Tests for server installation (AC: 1, 3, 4, 5)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_install_already_installed_returns_error(self, test_settings: Settings) -> None:
        """Installing when server exists returns error (AC: 5)."""
        # Create required server files to simulate installed state
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.server_dir / "VintagestoryServer.dll").touch()
        (test_settings.server_dir / "VintagestoryLib.dll").touch()
        (test_settings.server_dir / "current_version").write_text("1.21.3")

        service = ServerService(test_settings)
        progress = await service.install_server("1.21.6")

        assert progress.state.value == "error"
        assert progress.error is not None
        assert "already installed" in progress.error.lower()

    @pytest.mark.asyncio
    async def test_install_invalid_version_returns_error(
        self, server_service: ServerService
    ) -> None:
        """Installing with invalid version format returns error (AC: 4)."""
        progress = await server_service.install_server("invalid-version")

        assert progress.state.value == "error"
        assert progress.error is not None
        assert "invalid version format" in progress.error.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_install_version_not_found_returns_error(
        self, server_service: ServerService
    ) -> None:
        """Installing non-existent version returns error (AC: 3)."""
        stable_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.99.0.tar.gz"
        unstable_url = f"{VS_CDN_BASE}/unstable/vs_server_linux-x64_1.99.0.tar.gz"

        respx.head(stable_url).mock(return_value=Response(404))
        respx.head(unstable_url).mock(return_value=Response(404))

        progress = await server_service.install_server("1.99.0")

        assert progress.state.value == "error"
        assert progress.error is not None
        assert "not found" in progress.error.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_error_state_cleared_on_retry(self, test_settings: Settings) -> None:
        """Error state is cleared when retrying installation (AC3: return to not_installed)."""
        respx.head(re.compile(r".*/stable/.*")).mock(return_value=httpx.Response(404))
        respx.head(re.compile(r".*/unstable/.*")).mock(return_value=httpx.Response(404))

        service = ServerService(test_settings)

        # First attempt fails (version not found)
        progress1 = await service.install_server("1.99.0")
        assert progress1.state == ServerState.ERROR
        assert progress1.error_code == "VERSION_NOT_FOUND"
        old_error = progress1.error

        # Before retry, still shows error
        progress2 = service.get_install_progress()
        assert progress2.state == ServerState.ERROR

        # Second attempt with different version (also fails, but with fresh error)
        progress3 = await service.install_server("1.98.0")

        # Should get a fresh error about the NEW version, not the old one
        assert progress3.state == ServerState.ERROR
        assert progress3.error is not None
        assert "1.98.0" in progress3.error  # New version in error message
        assert progress3.error != old_error  # Different error message

        await service.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_concurrent_install_requests_serialized(
        self, test_settings: Settings
    ) -> None:
        """Concurrent install requests are serialized by asyncio.Lock (race condition protection)."""
        import asyncio

        # Mock version checks - all versions "exist"
        respx.head(re.compile(r".*/stable/.*")).mock(return_value=httpx.Response(200))

        # Track how many downloads are attempted
        download_attempts: list[str] = []

        async def slow_download(request: httpx.Request) -> httpx.Response:
            """Simulate slow download and track attempts."""
            # Extract version from URL
            version = request.url.path.split("_")[-1].replace(".tar.gz", "")
            download_attempts.append(version)
            # Simulate download time
            await asyncio.sleep(0.05)
            tarball_bytes, _ = create_mock_server_tarball(Path("/tmp"))
            return httpx.Response(
                200,
                content=tarball_bytes,
                headers={"content-length": str(len(tarball_bytes))},
            )

        respx.get(re.compile(r".*/stable/.*\.tar\.gz")).mock(side_effect=slow_download)

        # Mock API to return no version info (skip checksum verification)
        respx.get(VS_STABLE_API).mock(return_value=httpx.Response(200, json={}))
        respx.get(VS_UNSTABLE_API).mock(return_value=httpx.Response(200, json={}))

        service = ServerService(test_settings)

        # Start 3 concurrent install requests
        results = await asyncio.gather(
            service.install_server("1.21.3"),
            service.install_server("1.21.4"),
            service.install_server("1.21.5"),
            return_exceptions=True,
        )

        # Due to lock, only one should actually start downloading
        # Others should fail because server becomes "installed" after first completes
        success_count = sum(1 for r in results if r.state == ServerState.INSTALLED)
        error_count = sum(1 for r in results if r.state == ServerState.ERROR)

        # Exactly one should succeed (first to acquire lock)
        assert success_count == 1, f"Expected 1 success, got {success_count}"
        # Others should fail with "already installed"
        assert error_count == 2, f"Expected 2 errors, got {error_count}"

        # Verify only ONE download was attempted (lock prevented concurrent downloads)
        assert len(download_attempts) == 1, (
            f"Lock should serialize requests - expected 1 download, got {len(download_attempts)}"
        )

        await service.close()


def create_mock_server_tarball(server_dir: Path) -> tuple[bytes, str]:
    """Create a mock server tarball containing required files.

    Returns:
        Tuple of (tarball_bytes, md5_hash)
    """
    # Create an in-memory tarball
    tar_buffer = io.BytesIO()

    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add required server files
        for filename in ["VintagestoryServer.dll", "VintagestoryLib.dll"]:
            # Create file content
            content = f"mock content for {filename}".encode()
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(content)
            tar.addfile(tarinfo, io.BytesIO(content))

    tarball_bytes = tar_buffer.getvalue()
    md5_hash = hashlib.md5(tarball_bytes).hexdigest()

    return tarball_bytes, md5_hash


class TestDownloadServer:
    """Tests for server download functionality (Subtask 2.1)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_server_success(self, test_settings: Settings) -> None:
        """Successfully download server tarball."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        tarball_bytes, _ = create_mock_server_tarball(test_settings.server_dir)

        url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.3.tar.gz"
        respx.get(url).mock(
            return_value=Response(
                200,
                content=tarball_bytes,
                headers={"content-length": str(len(tarball_bytes))},
            )
        )

        service = ServerService(test_settings)
        tarball_path = await service.download_server("1.21.3", "stable")
        await service.close()

        assert tarball_path.exists()
        assert tarball_path.name == "vs_server_linux-x64_1.21.3.tar.gz"
        assert tarball_path.read_bytes() == tarball_bytes

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_server_tracks_progress(self, test_settings: Settings) -> None:
        """Download updates progress percentage."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        tarball_bytes, _ = create_mock_server_tarball(test_settings.server_dir)

        url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.3.tar.gz"
        respx.get(url).mock(
            return_value=Response(
                200,
                content=tarball_bytes,
                headers={"content-length": str(len(tarball_bytes))},
            )
        )

        progress_values: list[int] = []

        def track_progress(pct: int) -> None:
            progress_values.append(pct)

        service = ServerService(test_settings)
        await service.download_server("1.21.3", "stable", progress_callback=track_progress)
        await service.close()

        # Progress should end at 100%
        assert len(progress_values) > 0
        assert progress_values[-1] == 100

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_server_sets_stage(self, test_settings: Settings) -> None:
        """Download sets installation stage to downloading."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        tarball_bytes, _ = create_mock_server_tarball(test_settings.server_dir)

        url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.3.tar.gz"
        respx.get(url).mock(
            return_value=Response(
                200,
                content=tarball_bytes,
                headers={"content-length": str(len(tarball_bytes))},
            )
        )

        service = ServerService(test_settings)
        await service.download_server("1.21.3", "stable")

        # Stage should be downloading (or later)
        assert service._install_stage == InstallationStage.DOWNLOADING
        await service.close()


class TestChecksumVerification:
    """Tests for MD5 checksum verification (Subtask 2.2)."""

    def test_verify_checksum_success(self, test_settings: Settings) -> None:
        """Checksum verification succeeds with correct hash."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        tarball_bytes, md5_hash = create_mock_server_tarball(test_settings.server_dir)

        tarball_path = test_settings.server_dir / "test.tar.gz"
        tarball_path.write_bytes(tarball_bytes)

        service = ServerService(test_settings)
        result = service.verify_checksum(tarball_path, md5_hash)

        assert result is True

    def test_verify_checksum_failure(self, test_settings: Settings) -> None:
        """Checksum verification fails with incorrect hash."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        tarball_bytes, _ = create_mock_server_tarball(test_settings.server_dir)

        tarball_path = test_settings.server_dir / "test.tar.gz"
        tarball_path.write_bytes(tarball_bytes)

        service = ServerService(test_settings)
        result = service.verify_checksum(tarball_path, "wronghash123")

        assert result is False


class TestExtractServer:
    """Tests for tarball extraction (Subtask 2.3)."""

    def test_extract_server_success(self, test_settings: Settings) -> None:
        """Successfully extract server tarball."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        tarball_bytes, _ = create_mock_server_tarball(test_settings.server_dir)

        tarball_path = test_settings.server_dir / "server.tar.gz"
        tarball_path.write_bytes(tarball_bytes)

        service = ServerService(test_settings)
        service.extract_server(tarball_path)

        # Verify files were extracted
        assert (test_settings.server_dir / "VintagestoryServer.dll").exists()
        assert (test_settings.server_dir / "VintagestoryLib.dll").exists()

        # Verify tarball was removed
        assert not tarball_path.exists()

    def test_extract_server_sets_stage(self, test_settings: Settings) -> None:
        """Extraction sets installation stage to extracting."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        tarball_bytes, _ = create_mock_server_tarball(test_settings.server_dir)

        tarball_path = test_settings.server_dir / "server.tar.gz"
        tarball_path.write_bytes(tarball_bytes)

        service = ServerService(test_settings)
        service.extract_server(tarball_path)

        assert service._install_stage == InstallationStage.EXTRACTING


class TestInstallProgressTracking:
    """Tests for installation progress stage tracking (Subtask 2.4, AC: 2)."""

    def test_progress_includes_stage(self, test_settings: Settings) -> None:
        """Progress includes installation stage."""
        service = ServerService(test_settings)
        service._install_state = ServerState.INSTALLING
        service._install_stage = InstallationStage.DOWNLOADING
        service._install_percentage = 50

        progress = service.get_install_progress()

        assert progress.state == ServerState.INSTALLING
        assert progress.stage == InstallationStage.DOWNLOADING
        assert progress.percentage == 50

    def test_progress_stages_enum_values(self) -> None:
        """Installation stage enum has expected values."""
        assert InstallationStage.DOWNLOADING.value == "downloading"
        assert InstallationStage.EXTRACTING.value == "extracting"
        assert InstallationStage.CONFIGURING.value == "configuring"

    def test_progress_includes_error_code(self, test_settings: Settings) -> None:
        """Progress includes error_code when in error state."""
        from vintagestory_api.models.errors import ErrorCode

        service = ServerService(test_settings)
        service._set_install_error(
            "Checksum verification failed",
            ErrorCode.CHECKSUM_MISMATCH,
        )

        progress = service.get_install_progress()

        assert progress.state == ServerState.ERROR
        assert progress.error == "Checksum verification failed"
        assert progress.error_code == ErrorCode.CHECKSUM_MISMATCH

    def test_set_install_error_with_code(self, test_settings: Settings) -> None:
        """_set_install_error sets both error message and code."""
        from vintagestory_api.models.errors import ErrorCode

        service = ServerService(test_settings)
        service._set_install_error(
            "Version not found",
            ErrorCode.VERSION_NOT_FOUND,
        )

        assert service._install_state == ServerState.ERROR
        assert service._install_error == "Version not found"
        assert service._install_error_code == ErrorCode.VERSION_NOT_FOUND

    def test_set_install_error_without_code(self, test_settings: Settings) -> None:
        """_set_install_error works without error code (backward compatible)."""
        service = ServerService(test_settings)
        service._set_install_error("Generic error")

        assert service._install_state == ServerState.ERROR
        assert service._install_error == "Generic error"
        assert service._install_error_code is None


class TestCleanupOnFailure:
    """Tests for cleanup on installation failure (Subtask 2.5)."""

    def test_cleanup_removes_tarball(self, test_settings: Settings) -> None:
        """Cleanup removes downloaded tarball."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        tarball_bytes, _ = create_mock_server_tarball(test_settings.server_dir)

        tarball_path = test_settings.server_dir / "vs_server_linux-x64_1.21.3.tar.gz"
        tarball_path.write_bytes(tarball_bytes)

        service = ServerService(test_settings)
        service._cleanup_failed_install()

        assert not tarball_path.exists()

    def test_cleanup_resets_state(self, test_settings: Settings) -> None:
        """Cleanup resets installation state."""
        service = ServerService(test_settings)
        service._install_state = ServerState.INSTALLING
        service._install_stage = InstallationStage.DOWNLOADING
        service._install_percentage = 50
        service._install_error = "Test error"
        service._install_error_code = "TEST_ERROR"

        service._cleanup_failed_install()

        assert service._install_state == ServerState.NOT_INSTALLED
        assert service._install_stage is None
        assert service._install_percentage is None
        assert service._install_error is None
        assert service._install_error_code is None


class TestServerStateManagement:
    """Tests for server state management (Task 3)."""

    def test_server_state_enum_values(self) -> None:
        """Server state enum has expected values."""
        assert ServerState.NOT_INSTALLED.value == "not_installed"
        assert ServerState.INSTALLING.value == "installing"
        assert ServerState.INSTALLED.value == "installed"
        assert ServerState.ERROR.value == "error"

    def test_is_installed_false_when_no_files(self, test_settings: Settings) -> None:
        """is_installed returns False when server files don't exist."""
        service = ServerService(test_settings)
        assert service.is_installed() is False

    def test_is_installed_false_when_partial_files(self, test_settings: Settings) -> None:
        """is_installed returns False when only some files exist."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.server_dir / "VintagestoryServer.dll").touch()
        # Missing VintagestoryLib.dll

        service = ServerService(test_settings)
        assert service.is_installed() is False

    def test_is_installed_true_when_all_files(self, test_settings: Settings) -> None:
        """is_installed returns True when all required files exist."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.server_dir / "VintagestoryServer.dll").touch()
        (test_settings.server_dir / "VintagestoryLib.dll").touch()

        service = ServerService(test_settings)
        assert service.is_installed() is True

    def test_get_installed_version_none_when_no_file(
        self, test_settings: Settings
    ) -> None:
        """get_installed_version returns None when version file doesn't exist."""
        service = ServerService(test_settings)
        assert service.get_installed_version() is None

    def test_get_installed_version_returns_version(
        self, test_settings: Settings
    ) -> None:
        """get_installed_version returns version from file."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.server_dir / "current_version").write_text("1.21.6")

        service = ServerService(test_settings)
        assert service.get_installed_version() == "1.21.6"

    def test_save_installed_version(self, test_settings: Settings) -> None:
        """save_installed_version persists version to file."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service._save_installed_version("1.21.6")

        version_file = test_settings.server_dir / "current_version"
        assert version_file.exists()
        assert version_file.read_text() == "1.21.6"

    def test_save_installed_version_atomic(self, test_settings: Settings) -> None:
        """save_installed_version uses atomic write (no .tmp file left)."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service._save_installed_version("1.21.6")

        tmp_file = test_settings.server_dir / "current_version.tmp"
        assert not tmp_file.exists()


class TestDirectoriesAndSymlinks:
    """Tests for post-installation setup (Task 4)."""

    def test_setup_creates_mods_dir(self, test_settings: Settings) -> None:
        """setup_directories_and_symlinks creates mods directory."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service.setup_directories_and_symlinks()

        assert test_settings.mods_dir.exists()
        assert test_settings.mods_dir.is_dir()

    def test_setup_creates_config_dir(self, test_settings: Settings) -> None:
        """setup_directories_and_symlinks creates config directory."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service.setup_directories_and_symlinks()

        assert test_settings.config_dir.exists()
        assert test_settings.config_dir.is_dir()

    def test_setup_creates_symlink(self, test_settings: Settings) -> None:
        """setup_directories_and_symlinks creates Mods symlink."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service.setup_directories_and_symlinks()

        mods_symlink = test_settings.server_dir / "Mods"
        assert mods_symlink.is_symlink()
        assert mods_symlink.resolve() == test_settings.mods_dir.resolve()

    def test_setup_replaces_existing_mods_dir(self, test_settings: Settings) -> None:
        """setup_directories_and_symlinks replaces existing Mods directory."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        # Create existing Mods directory (not symlink)
        existing_mods = test_settings.server_dir / "Mods"
        existing_mods.mkdir()
        (existing_mods / "some_file.txt").touch()

        service = ServerService(test_settings)
        service.setup_directories_and_symlinks()

        mods_symlink = test_settings.server_dir / "Mods"
        assert mods_symlink.is_symlink()

    def test_setup_sets_stage_configuring(self, test_settings: Settings) -> None:
        """setup_directories_and_symlinks sets stage to configuring."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service.setup_directories_and_symlinks()

        assert service._install_stage == InstallationStage.CONFIGURING

    def test_setup_copies_default_config_when_empty(
        self, test_settings: Settings
    ) -> None:
        """setup_directories_and_symlinks copies default config if config dir empty (AC: 1)."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        # Create default serverconfig.json in server dir
        default_config = test_settings.server_dir / "serverconfig.json"
        default_config.write_text('{"ServerName": "Test Server"}')

        service = ServerService(test_settings)
        service.setup_directories_and_symlinks()

        # Config should be copied to config dir
        copied_config = test_settings.config_dir / "serverconfig.json"
        assert copied_config.exists()
        assert copied_config.read_text() == '{"ServerName": "Test Server"}'

    def test_setup_does_not_copy_config_when_not_empty(
        self, test_settings: Settings
    ) -> None:
        """setup_directories_and_symlinks skips copy if config dir has files."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        test_settings.config_dir.mkdir(parents=True, exist_ok=True)

        # Create existing config in config dir
        existing_config = test_settings.config_dir / "serverconfig.json"
        existing_config.write_text('{"ServerName": "Existing"}')

        # Create default config in server dir
        default_config = test_settings.server_dir / "serverconfig.json"
        default_config.write_text('{"ServerName": "Default"}')

        service = ServerService(test_settings)
        service.setup_directories_and_symlinks()

        # Existing config should not be overwritten
        assert existing_config.read_text() == '{"ServerName": "Existing"}'

    def test_setup_handles_missing_default_config(
        self, test_settings: Settings
    ) -> None:
        """setup_directories_and_symlinks handles missing serverconfig.json gracefully."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        # No serverconfig.json in server dir

        service = ServerService(test_settings)
        service.setup_directories_and_symlinks()

        # Should complete without error, config dir should exist but be empty
        assert test_settings.config_dir.exists()
        assert not (test_settings.config_dir / "serverconfig.json").exists()


# API endpoint tests
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


class TestServerInstallEndpoint:
    """Tests for POST /api/v1alpha1/server/install endpoint (AC: 1-5)."""

    @pytest.fixture
    def integration_app(
        self, temp_data_dir: Path
    ) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        # Create a test service with test settings
        test_service = ServerService(test_settings)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_install_requires_authentication(
        self, integration_client: TestClient
    ) -> None:
        """POST /server/install requires API key (AC: 5.4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.21.3"},
        )

        assert response.status_code == 401

    def test_install_requires_admin_role(
        self, integration_client: TestClient
    ) -> None:
        """POST /server/install requires Admin role (AC: 5.4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.21.3"},
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"

    def test_install_invalid_version_format_returns_422(
        self, integration_client: TestClient
    ) -> None:
        """POST /server/install with invalid version format returns 422 (AC: 4)."""
        # "invalid" doesn't match Pydantic regex pattern - rejected before our code
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "invalid"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Pydantic validation error returns 422
        assert response.status_code == 422

    def test_install_missing_patch_returns_422(
        self, integration_client: TestClient
    ) -> None:
        """POST /server/install with incomplete version returns 422."""
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.2"},  # Missing patch number - fails regex
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Pydantic validation error returns 422
        assert response.status_code == 422

    @respx.mock
    def test_install_version_not_found_returns_404(
        self, integration_client: TestClient
    ) -> None:
        """POST /server/install with non-existent version returns 404 (AC: 3)."""
        stable_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.99.0.tar.gz"
        unstable_url = f"{VS_CDN_BASE}/unstable/vs_server_linux-x64_1.99.0.tar.gz"

        respx.head(stable_url).mock(return_value=Response(404))
        respx.head(unstable_url).mock(return_value=Response(404))

        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.99.0"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["code"] == "VERSION_NOT_FOUND"

    def test_install_already_installed_returns_409(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/install when server exists returns 409 (AC: 5)."""
        # Create server files to simulate installed state
        server_dir = temp_data_dir / "server"
        server_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (server_dir / "current_version").write_text("1.21.3")

        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.21.6"},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 409
        error = response.json()["detail"]
        assert error["code"] == "SERVER_ALREADY_INSTALLED"

    @respx.mock
    def test_install_success_completes_end_to_end(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/install completes installation end-to-end (AC: 1, 2).

        Verifies:
        1. Initial response shows "installing" state
        2. Background task completes successfully
        3. Status endpoint shows "installed" state
        4. Server files exist on disk
        """
        # Use version 1.21.6 which exists in our mock stable.json response
        version = "1.21.6"

        # Create mock tarball and get its actual MD5
        tarball_bytes, actual_md5 = create_mock_server_tarball(Path("/tmp"))

        # Create mock API response with the correct MD5 checksum
        mock_api_response = {
            version: {
                "linuxserver": {
                    "filename": f"vs_server_linux-x64_{version}.tar.gz",
                    "filesize": "40.2 MB",
                    "md5": actual_md5,  # Use actual checksum
                    "urls": {
                        "cdn": f"{VS_CDN_BASE}/stable/vs_server_linux-x64_{version}.tar.gz",
                        "local": f"https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_{version}.tar.gz",
                    },
                    "latest": True,
                }
            }
        }

        # Mock HEAD request for version availability check
        head_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_{version}.tar.gz"
        respx.head(head_url).mock(return_value=Response(200))

        # Mock stable.json for version info lookup (used by background task)
        respx.get(VS_STABLE_API).mock(
            return_value=Response(200, json=mock_api_response)
        )

        # Mock the actual download (used by background task)
        download_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_{version}.tar.gz"
        respx.get(download_url).mock(
            return_value=Response(
                200,
                content=tarball_bytes,
                headers={"content-length": str(len(tarball_bytes))},
            )
        )

        # POST to start installation
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": version},
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Verify initial response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "installing"
        assert data["data"]["version"] == version

        # Background tasks run synchronously in TestClient, so installation
        # should be complete. Verify via status endpoint.
        status_response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "ok"
        assert status_data["data"]["state"] == "installed"
        assert status_data["data"]["version"] == version

        # Verify server files actually exist on disk
        server_dir = temp_data_dir / "server"
        assert (server_dir / "VintagestoryServer.dll").exists()
        assert (server_dir / "VintagestoryLib.dll").exists()
        assert (server_dir / "current_version").read_text() == version

        # Verify mods symlink created
        assert (server_dir / "Mods").is_symlink()
        assert (server_dir / "Mods").resolve() == (temp_data_dir / "mods").resolve()


class TestServerInstallStatusEndpoint:
    """Tests for GET /api/v1alpha1/server/install/status endpoint (AC: 2)."""

    @pytest.fixture
    def integration_app(
        self, temp_data_dir: Path
    ) -> Generator[FastAPI, None, None]:
        """Create app with test settings for integration testing."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        yield app
        app.dependency_overrides.clear()

    @pytest.fixture
    def integration_client(self, integration_app: FastAPI) -> TestClient:
        """Create test client for integration tests."""
        return TestClient(integration_app)

    def test_status_requires_authentication(
        self, integration_client: TestClient
    ) -> None:
        """GET /server/install/status requires API key."""
        response = integration_client.get("/api/v1alpha1/server/install/status")

        assert response.status_code == 401

    def test_status_returns_not_installed(
        self, integration_client: TestClient
    ) -> None:
        """GET /server/install/status returns not_installed when server missing."""
        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "not_installed"

    def test_status_returns_installed(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """GET /server/install/status returns installed when server exists."""
        # Create server files
        server_dir = temp_data_dir / "server"
        server_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (server_dir / "current_version").write_text("1.21.3")

        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "installed"
        assert data["data"]["version"] == "1.21.3"

    def test_status_follows_envelope_format(
        self, integration_client: TestClient
    ) -> None:
        """GET /server/install/status follows standard API envelope."""
        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"

    def test_status_accessible_by_monitor(
        self, integration_client: TestClient
    ) -> None:
        """GET /server/install/status accessible by Monitor role."""
        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        # Should be accessible (read endpoint)
        assert response.status_code == 200

    def test_status_includes_error_code_on_failure(
        self, integration_app: FastAPI, integration_client: TestClient
    ) -> None:
        """GET /server/install/status includes error_code in error state."""
        from vintagestory_api.models.errors import ErrorCode

        # Get the service and set error state
        test_service = integration_app.dependency_overrides[get_server_service]()
        test_service._set_install_error(
            "Downloaded server file checksum verification failed",
            ErrorCode.CHECKSUM_MISMATCH,
        )

        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["state"] == "error"
        assert data["data"]["error"] == "Downloaded server file checksum verification failed"
        assert data["data"]["error_code"] == ErrorCode.CHECKSUM_MISMATCH
