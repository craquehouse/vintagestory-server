"""Tests for VintageStory server installation service."""

import asyncio
import hashlib
import io
import re
import shutil
import signal
import tarfile
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import (
    InstallationStage,
    InstallProgress,
    LifecycleAction,
    ServerState,
)
from vintagestory_api.routers.server import get_server_service
from vintagestory_api.services.server import (
    VS_CDN_BASE,
    VS_STABLE_API,
    VS_UNSTABLE_API,
    ServerService,
)

# pyright: reportPrivateUsage=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnusedVariable=false
# pyright: reportMissingTypeArgument=false
# Note: Above suppressions are for pytest fixture injection patterns.
# Pyright doesn't understand pytest's fixture system, so fixtures passed as
# parameters trigger unknown type errors. The mock_subprocess fixture in
# particular causes cascading errors across all lifecycle tests.

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
        test_settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.server_dir / "VintagestoryServer.dll").touch()
        (test_settings.server_dir / "VintagestoryLib.dll").touch()
        (test_settings.vsmanager_dir / "current_version").write_text("1.21.3")

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
        test_settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.server_dir / "VintagestoryServer.dll").touch()
        (test_settings.server_dir / "VintagestoryLib.dll").touch()
        (test_settings.vsmanager_dir / "current_version").write_text("1.21.3")

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
    async def test_concurrent_install_requests_serialized(self, test_settings: Settings) -> None:
        """Concurrent install requests are serialized by asyncio.Lock."""
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
        # Filter to InstallProgress results (exclude any BaseException from gather)
        progress_results = [r for r in results if isinstance(r, InstallProgress)]
        success_count = sum(1 for r in progress_results if r.state == ServerState.INSTALLED)
        error_count = sum(1 for r in progress_results if r.state == ServerState.ERROR)

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

    def test_extract_handles_malformed_ustar_prefix(self, test_settings: Settings) -> None:
        """Extraction handles VintageStory tarballs with malformed USTAR prefix.

        VintageStory tarballs have garbage numeric data in the USTAR prefix
        field. Python's tarfile module interprets this literally, creating
        incorrect paths like '15070731126/VintagestoryServer.dll'.

        This test verifies that custom filter strips the bogus prefix.
        """
        from vintagestory_api.services.server import _strip_numeric_prefix

        # Test cases for prefix stripping
        assert _strip_numeric_prefix("15070731126/assets") == "assets"
        assert _strip_numeric_prefix("15070731127/VintagestoryServer.dll") == (
            "VintagestoryServer.dll"
        )
        assert _strip_numeric_prefix("15070731126/Lib/ICSharpCode.dll") == ("Lib/ICSharpCode.dll")

        # Should NOT strip non-numeric prefixes
        assert _strip_numeric_prefix("assets/game/textures") == "assets/game/textures"
        assert _strip_numeric_prefix("VintagestoryServer.dll") == ("VintagestoryServer.dll")

        # Should NOT strip numeric-looking normal directories (8-digit year-month OK)
        assert _strip_numeric_prefix("2024/backup.tar") == "2024/backup.tar"
        assert _strip_numeric_prefix("20250128/logs/server.log") == "20250128/logs/server.log"

        # Edge case: Nested paths with mixed prefixes
        assert _strip_numeric_prefix("15070731126/VintagestoryServer.dll/subdir/file.txt") == (
            "VintagestoryServer.dll/subdir/file.txt"
        )

        # Edge case: Legitimate numeric directory name (10 digits from year-month)
        assert _strip_numeric_prefix("20250128/logs/server.log") == "20250128/logs/server.log"

        # Edge case: Empty prefix (should return as-is)
        assert _strip_numeric_prefix("VintagestoryServer.dll") == "VintagestoryServer.dll"

        # Edge case: Prefix with zeros
        assert _strip_numeric_prefix("0000000001/Mods/core.dll") == "Mods/core.dll"

    def test_extract_handles_symlink_prefix(self, test_settings: Settings) -> None:
        """Extraction handles symlinks with malformed USTAR prefix.

        Verifies that the custom filter correctly strips prefixes from symlink
        target paths (linkname field in tarball).
        """
        from vintagestory_api.services.server import _strip_numeric_prefix

        # Symlink linkname with bogus numeric prefix
        assert _strip_numeric_prefix("15070731126/Mods/VSCreativeMod") == ("Mods/VSCreativeMod")

        # Symlink without prefix (should pass through)
        assert _strip_numeric_prefix("Mods/VSEssentials") == "Mods/VSEssentials"


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

    def test_get_installed_version_none_when_no_file(self, test_settings: Settings) -> None:
        """get_installed_version returns None when version file doesn't exist."""
        service = ServerService(test_settings)
        assert service.get_installed_version() is None

    def test_get_installed_version_returns_version(self, test_settings: Settings) -> None:
        """get_installed_version returns version from file."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        test_settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.vsmanager_dir / "current_version").write_text("1.21.6")

        service = ServerService(test_settings)
        assert service.get_installed_version() == "1.21.6"

    def test_save_installed_version(self, test_settings: Settings) -> None:
        """save_installed_version persists version to file."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        test_settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service._save_installed_version("1.21.6")

        version_file = test_settings.vsmanager_dir / "current_version"
        assert version_file.exists()
        assert version_file.read_text() == "1.21.6"

    def test_save_installed_version_atomic(self, test_settings: Settings) -> None:
        """save_installed_version uses atomic write (no .tmp file left)."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        test_settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service._save_installed_version("1.21.6")

        tmp_file = test_settings.vsmanager_dir / "current_version.tmp"
        assert not tmp_file.exists()


class TestPostInstallSetup:
    """Tests for post-installation setup (Task 4)."""

    def test_setup_creates_serverdata_dir(self, test_settings: Settings) -> None:
        """setup_post_install creates serverdata directory."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service.setup_post_install()

        assert test_settings.serverdata_dir.exists()
        assert test_settings.serverdata_dir.is_dir()

    def test_setup_creates_vsmanager_dir(self, test_settings: Settings) -> None:
        """setup_post_install creates vsmanager directory."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service.setup_post_install()

        assert test_settings.vsmanager_dir.exists()
        assert test_settings.vsmanager_dir.is_dir()

    def test_setup_sets_stage_configuring(self, test_settings: Settings) -> None:
        """setup_post_install sets stage to configuring."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        service = ServerService(test_settings)
        service.setup_post_install()

        assert service._install_stage == InstallationStage.CONFIGURING


# API endpoint tests
TEST_ADMIN_KEY = "test-admin-key-12345"
TEST_MONITOR_KEY = "test-monitor-key-67890"


class TestServerInstallEndpoint:
    """Tests for POST /api/v1alpha1/server/install endpoint (AC: 1-5)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
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

    def test_install_requires_authentication(self, integration_client: TestClient) -> None:
        """POST /server/install requires API key (AC: 5.4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.21.3"},
        )

        assert response.status_code == 401

    def test_install_requires_admin_role(self, integration_client: TestClient) -> None:
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

    def test_install_missing_patch_returns_422(self, integration_client: TestClient) -> None:
        """POST /server/install with incomplete version returns 422."""
        response = integration_client.post(
            "/api/v1alpha1/server/install",
            json={"version": "1.2"},  # Missing patch number - fails regex
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Pydantic validation error returns 422
        assert response.status_code == 422

    @respx.mock
    def test_install_version_not_found_returns_404(self, integration_client: TestClient) -> None:
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
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

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
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=mock_api_response))

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
        vsmanager_dir = temp_data_dir / "vsmanager"
        assert (server_dir / "VintagestoryServer.dll").exists()
        assert (server_dir / "VintagestoryLib.dll").exists()
        assert (vsmanager_dir / "current_version").read_text() == version

        # Verify serverdata dir created
        assert (temp_data_dir / "serverdata").is_dir()


class TestServerInstallStatusEndpoint:
    """Tests for GET /api/v1alpha1/server/install/status endpoint (AC: 2)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
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

    def test_status_requires_authentication(self, integration_client: TestClient) -> None:
        """GET /server/install/status requires API key."""
        response = integration_client.get("/api/v1alpha1/server/install/status")

        assert response.status_code == 401

    def test_status_returns_not_installed(self, integration_client: TestClient) -> None:
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
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "installed"
        assert data["data"]["version"] == "1.21.3"

    def test_status_follows_envelope_format(self, integration_client: TestClient) -> None:
        """GET /server/install/status follows standard API envelope."""
        response = integration_client.get(
            "/api/v1alpha1/server/install/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"

    def test_status_accessible_by_monitor(self, integration_client: TestClient) -> None:
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


# ============================================
# Server Lifecycle Tests (Story 3.2)
# ============================================


@pytest.fixture
def installed_service(test_settings: Settings) -> ServerService:
    """Create a server service with server files in place (simulating installed state)."""
    # Create required server files
    test_settings.server_dir.mkdir(parents=True, exist_ok=True)
    test_settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
    (test_settings.server_dir / "VintagestoryServer.dll").touch()
    (test_settings.server_dir / "VintagestoryLib.dll").touch()
    (test_settings.vsmanager_dir / "current_version").write_text("1.21.3")
    return ServerService(test_settings)


@pytest.fixture
def mock_subprocess() -> Generator[tuple[MagicMock, AsyncMock], None, None]:
    """Mock asyncio.create_subprocess_exec for testing.

    Uses an Event to simulate blocking wait that can be unblocked for stop tests.
    """
    with patch("asyncio.create_subprocess_exec") as mock:
        process = AsyncMock()
        process.pid = 12345
        process.returncode = None  # None = still running

        # Use an Event that can be set to unblock wait()
        process._wait_event = asyncio.Event()

        async def controlled_wait():
            """Wait until unblocked or return immediately if stopped."""
            try:
                # Wait for event to be set, but with a short timeout for cleanup
                await asyncio.wait_for(process._wait_event.wait(), timeout=0.01)
            except TimeoutError:
                pass
            return process.returncode if process.returncode is not None else 0

        process.wait = AsyncMock(side_effect=controlled_wait)
        process.send_signal = MagicMock()
        process.kill = MagicMock()
        mock.return_value = process
        yield mock, process


class TestServerLifecycleStateEnum:
    """Tests for new ServerState enum values (Subtask 1.5)."""

    def test_server_state_has_starting(self) -> None:
        """ServerState enum includes 'starting' value."""
        assert ServerState.STARTING.value == "starting"

    def test_server_state_has_running(self) -> None:
        """ServerState enum includes 'running' value."""
        assert ServerState.RUNNING.value == "running"

    def test_server_state_has_stopping(self) -> None:
        """ServerState enum includes 'stopping' value."""
        assert ServerState.STOPPING.value == "stopping"


class TestStartServer:
    """Tests for start_server() method (Subtask 1.2, AC: 1)."""

    @pytest.mark.asyncio
    async def test_start_server_spawns_process(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """start_server() spawns subprocess with correct command."""
        mock_exec, _ = mock_subprocess

        await installed_service.start_server()

        mock_exec.assert_called_once()
        # Check command contains dotnet and VintagestoryServer.dll
        call_args = mock_exec.call_args[0]
        assert "dotnet" in call_args
        assert any("VintagestoryServer.dll" in str(arg) for arg in call_args)

    @pytest.mark.asyncio
    async def test_start_server_returns_lifecycle_response(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """start_server() returns LifecycleResponse with correct data."""
        mock_exec, mock_process = mock_subprocess

        response = await installed_service.start_server()

        assert response.action == LifecycleAction.START
        assert response.previous_state == ServerState.INSTALLED
        assert response.new_state == ServerState.RUNNING
        assert response.message == "Server start initiated"

    @pytest.mark.asyncio
    async def test_start_server_updates_state_to_running(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """start_server() updates server state to RUNNING."""
        mock_exec, mock_process = mock_subprocess

        await installed_service.start_server()

        status = installed_service.get_server_status()
        assert status.state == ServerState.RUNNING

    @pytest.mark.asyncio
    async def test_start_server_fails_when_not_installed(self, test_settings: Settings) -> None:
        """start_server() raises error when server not installed."""
        service = ServerService(test_settings)

        with pytest.raises(RuntimeError) as exc_info:
            await service.start_server()

        assert ErrorCode.SERVER_NOT_INSTALLED in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_server_fails_when_already_running(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """start_server() raises error when server already running."""
        mock_exec, mock_process = mock_subprocess

        # Start server once
        await installed_service.start_server()

        # Try to start again
        with pytest.raises(RuntimeError) as exc_info:
            await installed_service.start_server()

        assert ErrorCode.SERVER_ALREADY_RUNNING in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_server_starts_monitor_task(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """start_server() starts background monitor task."""
        mock_exec, mock_process = mock_subprocess

        await installed_service.start_server()

        assert installed_service._monitor_task is not None
        assert not installed_service._monitor_task.done()

    @pytest.mark.asyncio
    async def test_start_server_includes_data_path_arg(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """start_server() includes --dataPath argument."""
        mock_exec, mock_process = mock_subprocess

        await installed_service.start_server()

        call_args = mock_exec.call_args[0]
        assert "--dataPath" in call_args


class TestStopServer:
    """Tests for stop_server() method (Subtask 1.3, AC: 2)."""

    @pytest.mark.asyncio
    async def test_stop_server_sends_sigterm(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """stop_server() sends SIGTERM for graceful shutdown."""
        mock_exec, mock_process = mock_subprocess

        await installed_service.start_server()
        await installed_service.stop_server()

        mock_process.send_signal.assert_called_with(signal.SIGTERM)

    @pytest.mark.asyncio
    async def test_stop_server_returns_lifecycle_response(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """stop_server() returns LifecycleResponse with correct data."""
        mock_exec, mock_process = mock_subprocess

        await installed_service.start_server()
        response = await installed_service.stop_server()

        assert response.action == LifecycleAction.STOP
        assert response.previous_state == ServerState.RUNNING
        assert response.new_state == ServerState.INSTALLED
        assert response.message == "Server stopped"

    @pytest.mark.asyncio
    async def test_stop_server_updates_state_to_installed(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """stop_server() updates server state back to INSTALLED."""
        mock_exec, mock_process = mock_subprocess

        await installed_service.start_server()
        await installed_service.stop_server()

        status = installed_service.get_server_status()
        assert status.state == ServerState.INSTALLED

    @pytest.mark.asyncio
    async def test_stop_server_fails_when_not_running(
        self, installed_service: ServerService
    ) -> None:
        """stop_server() raises error when server not running."""
        with pytest.raises(RuntimeError) as exc_info:
            await installed_service.stop_server()

        assert ErrorCode.SERVER_NOT_RUNNING in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stop_server_fails_when_not_installed(self, test_settings: Settings) -> None:
        """stop_server() raises error when server not installed."""
        service = ServerService(test_settings)

        with pytest.raises(RuntimeError) as exc_info:
            await service.stop_server()

        assert ErrorCode.SERVER_NOT_INSTALLED in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stop_server_kills_after_timeout(self, installed_service: ServerService) -> None:
        """stop_server() sends SIGKILL after timeout expires."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            call_count = 0

            async def slow_then_complete():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call (from monitor task or stop) - blocks forever
                    await asyncio.sleep(100)
                # After kill(), return immediately
                process.returncode = -9
                return -9

            process.wait = AsyncMock(side_effect=slow_then_complete)
            mock_exec.return_value = process

            await installed_service.start_server()

            # Override wait() to timeout on first call, return immediately after kill
            wait_call = 0

            async def timeout_then_complete():
                nonlocal wait_call
                wait_call += 1
                if wait_call == 1:
                    # First wait() should timeout
                    raise TimeoutError()
                # After kill(), complete
                process.returncode = -9
                return -9

            process.wait = AsyncMock(side_effect=timeout_then_complete)

            # Use short timeout
            await installed_service.stop_server(timeout=0.1)

            # Should have called kill after timeout
            process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_server_records_exit_code(self, installed_service: ServerService) -> None:
        """stop_server() records process exit code."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            # Block the monitor forever
            async def blocking_monitor_wait():
                await asyncio.sleep(100)
                return 0

            process.wait = AsyncMock(side_effect=blocking_monitor_wait)
            mock_exec.return_value = process

            await installed_service.start_server()

            # For stop, wait should complete quickly and set returncode
            async def stop_wait():
                process.returncode = 0
                return 0

            process.wait = AsyncMock(side_effect=stop_wait)

            await installed_service.stop_server()

            status = installed_service.get_server_status()
            assert status.last_exit_code == 0


class TestRestartServer:
    """Tests for restart_server() method (Subtask 2.1, AC: 3)."""

    @pytest.mark.asyncio
    async def test_restart_server_when_running(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """restart_server() stops and starts when server is running."""
        mock_exec, mock_process = mock_subprocess

        await installed_service.start_server()
        response = await installed_service.restart_server()

        assert response.action == LifecycleAction.RESTART
        assert response.previous_state == ServerState.RUNNING
        assert response.new_state == ServerState.RUNNING
        assert response.message == "Server restarted"

    @pytest.mark.asyncio
    async def test_restart_server_when_stopped(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """restart_server() starts server when not running."""
        mock_exec, mock_process = mock_subprocess

        response = await installed_service.restart_server()

        assert response.action == LifecycleAction.RESTART
        assert response.previous_state == ServerState.INSTALLED
        assert response.new_state == ServerState.RUNNING

    @pytest.mark.asyncio
    async def test_restart_server_fails_when_not_installed(self, test_settings: Settings) -> None:
        """restart_server() raises error when server not installed."""
        service = ServerService(test_settings)

        with pytest.raises(RuntimeError) as exc_info:
            await service.restart_server()

        assert ErrorCode.SERVER_NOT_INSTALLED in str(exc_info.value)


class TestProcessMonitoring:
    """Tests for process monitoring and crash detection (Subtask 1.4, AC: 5)."""

    @pytest.mark.asyncio
    async def test_crash_detected_updates_state(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """Monitor task updates state when process crashes."""
        mock_exec, mock_process = mock_subprocess
        # Simulate crash with non-zero exit code
        mock_process.wait = AsyncMock(return_value=1)
        mock_process.returncode = 1

        await installed_service.start_server()

        # Let monitor task run
        await asyncio.sleep(0.1)

        status = installed_service.get_server_status()
        assert status.state == ServerState.INSTALLED
        assert status.last_exit_code == 1

    @pytest.mark.asyncio
    async def test_crash_records_exit_code(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """Monitor task records exit code on crash."""
        mock_exec, mock_process = mock_subprocess
        mock_process.wait = AsyncMock(return_value=137)  # Killed by SIGKILL
        mock_process.returncode = 137

        await installed_service.start_server()

        # Let monitor task run
        await asyncio.sleep(0.1)

        status = installed_service.get_server_status()
        assert status.last_exit_code == 137


class TestServerStatus:
    """Tests for get_server_status() method."""

    def test_status_not_installed(self, test_settings: Settings) -> None:
        """get_server_status() returns NOT_INSTALLED when no server files."""
        service = ServerService(test_settings)

        status = service.get_server_status()

        assert status.state == ServerState.NOT_INSTALLED
        assert status.version is None

    def test_status_installed_stopped(self, installed_service: ServerService) -> None:
        """get_server_status() returns INSTALLED when stopped."""
        status = installed_service.get_server_status()

        assert status.state == ServerState.INSTALLED
        assert status.version == "1.21.3"
        assert status.uptime_seconds is None

    @pytest.mark.asyncio
    async def test_status_running_has_uptime(self, installed_service: ServerService) -> None:
        """get_server_status() includes uptime when running."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None  # None = still running
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            # Block forever to simulate running process
            async def blocking_wait():
                await asyncio.sleep(100)
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            await installed_service.start_server()

            # Wait a moment for uptime
            await asyncio.sleep(0.1)

            status = installed_service.get_server_status()
            assert status.state == ServerState.RUNNING
            assert status.uptime_seconds is not None
            assert status.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_status_after_stop_has_exit_code(self, installed_service: ServerService) -> None:
        """get_server_status() includes exit code after stopping."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            # Block forever for monitor
            async def blocking_wait():
                await asyncio.sleep(100)
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            await installed_service.start_server()

            # For stop, wait should complete immediately
            async def stop_wait():
                process.returncode = 0
                return 0

            process.wait = AsyncMock(side_effect=stop_wait)

            await installed_service.stop_server()

            status = installed_service.get_server_status()
            assert status.state == ServerState.INSTALLED
            assert status.last_exit_code == 0


class TestConcurrentLifecycleOperations:
    """Tests for lifecycle lock preventing race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_starts_serialized(
        self, installed_service: ServerService, mock_subprocess: tuple
    ) -> None:
        """Concurrent start calls are serialized by lock."""
        mock_exec, mock_process = mock_subprocess

        # Add delay to start to simulate slow startup
        original_wait = mock_process.wait

        async def slow_start():
            await asyncio.sleep(0.1)
            return await original_wait()

        mock_process.wait = slow_start

        # Start concurrent operations
        results = await asyncio.gather(
            installed_service.start_server(),
            installed_service.start_server(),
            return_exceptions=True,
        )

        # One should succeed, one should fail with already running
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        error_count = sum(1 for r in results if isinstance(r, RuntimeError))

        assert success_count == 1
        assert error_count == 1


# ============================================
# Lifecycle API Endpoint Tests (Story 3.2 - Task 3)
# ============================================


class TestServerStartEndpoint:
    """Tests for POST /api/v1alpha1/server/start endpoint (AC: 1)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
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

    def test_start_requires_authentication(self, integration_client: TestClient) -> None:
        """POST /server/start requires API key."""
        response = integration_client.post("/api/v1alpha1/server/start")
        assert response.status_code == 401

    def test_start_requires_admin_role(self, integration_client: TestClient) -> None:
        """POST /server/start requires Admin role."""
        response = integration_client.post(
            "/api/v1alpha1/server/start",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"

    def test_start_not_installed_returns_400(self, integration_client: TestClient) -> None:
        """POST /server/start returns 400 when no server installed (AC: 4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/start",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )
        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == "SERVER_NOT_INSTALLED"

    def test_start_success(self, integration_client: TestClient, temp_data_dir: Path) -> None:
        """POST /server/start successfully starts server (AC: 1)."""
        # Create server files to simulate installed state
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            # Block forever for monitor
            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            response = integration_client.post(
                "/api/v1alpha1/server/start",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["action"] == "start"
        assert data["data"]["previous_state"] == "installed"
        assert data["data"]["new_state"] == "running"

    def test_start_already_running_returns_409(
        self, integration_app: FastAPI, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/start returns 409 when already running."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        # Get the service and manually set state to running
        test_service = integration_app.dependency_overrides[get_server_service]()
        test_service._server_state = ServerState.RUNNING

        # Mock process to simulate running
        mock_process = AsyncMock()
        mock_process.returncode = None  # None = still running
        test_service._process = mock_process

        # Second start should fail
        response = integration_client.post(
            "/api/v1alpha1/server/start",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 409
        error = response.json()["detail"]
        assert error["code"] == "SERVER_ALREADY_RUNNING"


class TestServerStopEndpoint:
    """Tests for POST /api/v1alpha1/server/stop endpoint (AC: 2)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
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

    def test_stop_requires_authentication(self, integration_client: TestClient) -> None:
        """POST /server/stop requires API key."""
        response = integration_client.post("/api/v1alpha1/server/stop")
        assert response.status_code == 401

    def test_stop_requires_admin_role(self, integration_client: TestClient) -> None:
        """POST /server/stop requires Admin role."""
        response = integration_client.post(
            "/api/v1alpha1/server/stop",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )
        assert response.status_code == 403

    def test_stop_not_installed_returns_400(self, integration_client: TestClient) -> None:
        """POST /server/stop returns 400 when no server installed (AC: 4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/stop",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )
        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == "SERVER_NOT_INSTALLED"

    def test_stop_not_running_returns_409(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/stop returns 409 when server not running."""
        # Create server files (installed but not running)
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        response = integration_client.post(
            "/api/v1alpha1/server/stop",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 409
        error = response.json()["detail"]
        assert error["code"] == "SERVER_NOT_RUNNING"

    def test_stop_success(self, integration_client: TestClient, temp_data_dir: Path) -> None:
        """POST /server/stop successfully stops running server (AC: 2)."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            # Use event to control wait behavior
            started = False

            async def controlled_wait():
                nonlocal started
                if not started:
                    started = True
                    await asyncio.sleep(100)  # Block for monitor
                # After stop, return immediately
                process.returncode = 0
                return 0

            process.wait = AsyncMock(side_effect=controlled_wait)
            mock_exec.return_value = process

            # Start server first
            response1 = integration_client.post(
                "/api/v1alpha1/server/start",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )
            assert response1.status_code == 200

            # Make wait() complete on stop
            async def stop_wait():
                process.returncode = 0
                return 0

            process.wait = AsyncMock(side_effect=stop_wait)

            # Stop server
            response2 = integration_client.post(
                "/api/v1alpha1/server/stop",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response2.status_code == 200
        data = response2.json()
        assert data["status"] == "ok"
        assert data["data"]["action"] == "stop"
        assert data["data"]["new_state"] == "installed"


class TestServerRestartEndpoint:
    """Tests for POST /api/v1alpha1/server/restart endpoint (AC: 3)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
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

    def test_restart_requires_authentication(self, integration_client: TestClient) -> None:
        """POST /server/restart requires API key."""
        response = integration_client.post("/api/v1alpha1/server/restart")
        assert response.status_code == 401

    def test_restart_requires_admin_role(self, integration_client: TestClient) -> None:
        """POST /server/restart requires Admin role."""
        response = integration_client.post(
            "/api/v1alpha1/server/restart",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )
        assert response.status_code == 403

    def test_restart_not_installed_returns_400(self, integration_client: TestClient) -> None:
        """POST /server/restart returns 400 when no server installed (AC: 4)."""
        response = integration_client.post(
            "/api/v1alpha1/server/restart",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )
        assert response.status_code == 400
        error = response.json()["detail"]
        assert error["code"] == "SERVER_NOT_INSTALLED"

    def test_restart_success_from_stopped(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/restart starts server when stopped (AC: 3)."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            # Block forever for monitor
            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            response = integration_client.post(
                "/api/v1alpha1/server/restart",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["action"] == "restart"
        assert data["data"]["previous_state"] == "installed"
        assert data["data"]["new_state"] == "running"

    def test_restart_success_from_running(
        self, integration_app: FastAPI, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/restart stops and starts when running (AC: 3)."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        # Get the service and manually set state to running
        test_service = integration_app.dependency_overrides[get_server_service]()
        test_service._server_state = ServerState.RUNNING

        # Create mock process that's "running"
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None  # None = still running
        mock_process.send_signal = MagicMock()
        mock_process.kill = MagicMock()

        # wait() completes immediately for stop
        async def stop_wait():
            mock_process.returncode = 0
            return 0

        mock_process.wait = AsyncMock(side_effect=stop_wait)
        test_service._process = mock_process

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # New process for restart
            new_process = AsyncMock()
            new_process.pid = 12346
            new_process.returncode = None
            new_process.send_signal = MagicMock()
            new_process.kill = MagicMock()

            # Block forever for new monitor
            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            new_process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = new_process

            # Restart server
            response = integration_client.post(
                "/api/v1alpha1/server/restart",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["action"] == "restart"
        assert data["data"]["previous_state"] == "running"
        assert data["data"]["new_state"] == "running"


# ============================================
# Restart Partial Failure Tests (Code Review Follow-up)
# ============================================


class TestRestartPartialFailures:
    """Tests for restart partial failure scenarios."""

    @pytest.mark.asyncio
    async def test_restart_fails_when_stop_fails(self, installed_service: ServerService) -> None:
        """restart_server() raises SERVER_STOP_FAILED when stop encounters error."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock(side_effect=OSError("Permission denied"))
            process.kill = MagicMock()

            # Block forever for monitor
            async def blocking_wait():
                await asyncio.sleep(100)
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            # Start server first
            await installed_service.start_server()

            # Restart should fail during stop phase
            with pytest.raises(RuntimeError) as exc_info:
                await installed_service.restart_server()

            assert ErrorCode.SERVER_STOP_FAILED in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_restart_fails_when_start_fails_after_stop(
        self, installed_service: ServerService
    ) -> None:
        """restart_server() raises SERVER_START_FAILED when start fails after stop."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            # Block forever for monitor
            async def blocking_wait():
                await asyncio.sleep(100)
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            # Start server first
            await installed_service.start_server()

            # For stop, wait should complete
            async def stop_wait():
                process.returncode = 0
                return 0

            process.wait = AsyncMock(side_effect=stop_wait)

            # Make subprocess creation fail for the restart's start phase
            mock_exec.side_effect = OSError("Cannot spawn process")

            # Restart should fail during start phase
            with pytest.raises(RuntimeError) as exc_info:
                await installed_service.restart_server()

            assert ErrorCode.SERVER_START_FAILED in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_restart_from_starting_state(self, installed_service: ServerService) -> None:
        """restart_server() handles server in STARTING state correctly."""
        # Manually set state to STARTING (simulating startup in progress)
        installed_service._server_state = ServerState.STARTING

        # Create a mock process that appears to be starting
        mock_process = AsyncMock()
        mock_process.returncode = None  # Still running
        mock_process.send_signal = MagicMock()
        mock_process.kill = MagicMock()

        async def stop_wait():
            mock_process.returncode = 0
            return 0

        mock_process.wait = AsyncMock(side_effect=stop_wait)
        installed_service._process = mock_process

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            new_process = AsyncMock()
            new_process.pid = 12346
            new_process.returncode = None
            new_process.send_signal = MagicMock()
            new_process.kill = MagicMock()

            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            new_process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = new_process

            # Should be able to restart even from STARTING state
            response = await installed_service.restart_server()

            assert response.action == LifecycleAction.RESTART
            assert response.new_state == ServerState.RUNNING

    @pytest.mark.asyncio
    async def test_restart_with_graceful_shutdown_timeout(
        self, installed_service: ServerService
    ) -> None:
        """restart_server() uses SIGKILL when graceful shutdown times out."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            # Block forever for monitor
            async def blocking_wait():
                await asyncio.sleep(100)
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            # Start server first
            await installed_service.start_server()

            # Simulate stop timeout - first call blocks, second completes after kill
            call_count = 0

            async def timeout_then_complete():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise TimeoutError()  # First wait times out
                process.returncode = -9  # Killed
                return -9

            process.wait = AsyncMock(side_effect=timeout_then_complete)

            # Create new process for restart's start phase
            new_process = AsyncMock()
            new_process.pid = 12346
            new_process.returncode = None
            new_process.send_signal = MagicMock()
            new_process.kill = MagicMock()

            async def new_blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            new_process.wait = AsyncMock(side_effect=new_blocking_wait)
            mock_exec.return_value = new_process

            # Restart with short timeout
            response = await installed_service.restart_server(timeout=0.1)

            # Should have called kill on the original process
            process.kill.assert_called_once()
            assert response.action == LifecycleAction.RESTART

    @pytest.mark.asyncio
    async def test_restart_from_error_state(self, installed_service: ServerService) -> None:
        """restart_server() can recover from ERROR state."""
        # Set to ERROR state (simulating a previous failed operation)
        installed_service._server_state = ServerState.ERROR

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.send_signal = MagicMock()
            process.kill = MagicMock()

            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            # Restart should succeed - server is installed, process is not running
            response = await installed_service.restart_server()

            assert response.action == LifecycleAction.RESTART
            assert response.new_state == ServerState.RUNNING


class TestRestartEndpointErrorHandling:
    """Tests for /restart endpoint error handling (API level)."""

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
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

    def test_restart_stop_failed_returns_500(
        self, integration_app: FastAPI, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/restart returns 500 when stop fails."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        # Get the service and set up a running state
        test_service = integration_app.dependency_overrides[get_server_service]()
        test_service._server_state = ServerState.RUNNING

        # Create a mock process that will fail to stop
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.send_signal = MagicMock(side_effect=OSError("Permission denied"))
        mock_process.kill = MagicMock()

        async def blocking_wait():
            await asyncio.sleep(100)
            return 0

        mock_process.wait = AsyncMock(side_effect=blocking_wait)
        test_service._process = mock_process

        response = integration_client.post(
            "/api/v1alpha1/server/restart",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 500
        error = response.json()["detail"]
        assert error["code"] == "SERVER_STOP_FAILED"

    def test_restart_start_failed_returns_500(
        self, integration_app: FastAPI, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """POST /server/restart returns 500 when start fails after successful stop."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        # Server is not running, so restart will just try to start
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = OSError("Cannot spawn process")

            response = integration_client.post(
                "/api/v1alpha1/server/restart",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

        assert response.status_code == 500
        error = response.json()["detail"]
        assert error["code"] == "SERVER_START_FAILED"


class TestServerStatusEndpoint:
    """Tests for GET /api/v1alpha1/server/status endpoint (Story 3.3, AC: 1-4).

    Acceptance Criteria Coverage:
    - AC1: Admin can access status with state, version, uptime
    - AC2: Monitor can access status (read-only)
    - AC3: Uptime calculated from process start time, version from installed server
    - AC4: Not installed returns state="not_installed" with null version/uptime
    """

    @pytest.fixture
    def integration_app(self, temp_data_dir: Path) -> Generator[FastAPI, None, None]:
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

    def test_status_requires_authentication(self, integration_client: TestClient) -> None:
        """GET /server/status returns 401 without API key (AC: 1, 2)."""
        response = integration_client.get("/api/v1alpha1/server/status")

        assert response.status_code == 401
        error = response.json()["detail"]
        assert error["code"] == "UNAUTHORIZED"

    def test_status_accessible_by_admin(self, integration_client: TestClient) -> None:
        """GET /server/status accessible by Admin role (AC: 1)."""
        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data

    def test_status_accessible_by_monitor(self, integration_client: TestClient) -> None:
        """GET /server/status accessible by Monitor role (AC: 2)."""
        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_MONITOR_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data

    def test_status_returns_not_installed(self, integration_client: TestClient) -> None:
        """GET /server/status returns not_installed when server missing (AC: 4)."""
        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "not_installed"
        assert data["data"]["version"] is None
        assert data["data"]["uptime_seconds"] is None

    def test_status_returns_installed_stopped(
        self, integration_client: TestClient, temp_data_dir: Path
    ) -> None:
        """GET /server/status returns installed when server exists but stopped (AC: 1, 3)."""
        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "installed"
        assert data["data"]["version"] == "1.21.3"
        assert data["data"]["uptime_seconds"] is None

    def test_status_returns_running_with_uptime(self, temp_data_dir: Path) -> None:
        """GET /server/status includes uptime when server running (AC: 1, 3).

        Note: This test creates its own TestClient instead of using the shared
        integration_client fixture because it needs to configure a specific
        service state (RUNNING with mock process) BEFORE making requests. The
        shared fixture creates a fresh service on each dependency resolution.
        """
        import time

        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        # Create service and configure running state
        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.RUNNING
        test_service._server_start_time = time.time() - 60

        # Mock process with None returncode (still running)
        mock_process = MagicMock()
        mock_process.returncode = None
        test_service._process = mock_process

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["data"]["state"] == "running"
            assert data["data"]["version"] == "1.21.3"
            # Uptime should be at least 60 seconds (with some tolerance)
            assert data["data"]["uptime_seconds"] is not None
            assert data["data"]["uptime_seconds"] >= 59
        finally:
            app.dependency_overrides.clear()

    def test_status_follows_api_envelope_format(self, integration_client: TestClient) -> None:
        """GET /server/status follows standard API envelope (AC: 1, Task 1.3)."""
        response = integration_client.get(
            "/api/v1alpha1/server/status",
            headers={"X-API-Key": TEST_ADMIN_KEY},
        )

        # Verify Content-Type header
        assert response.headers.get("content-type") == "application/json"

        data = response.json()
        assert "status" in data
        assert "data" in data
        assert data["status"] == "ok"
        # Check expected fields in data - exactly 4 fields, no extras
        assert set(data["data"].keys()) == {"state", "version", "uptime_seconds", "last_exit_code"}

    def test_status_returns_starting_state(self, temp_data_dir: Path) -> None:
        """GET /server/status returns starting state during server startup (AC: 1)."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.STARTING

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["state"] == "starting"
        finally:
            app.dependency_overrides.clear()

    def test_status_returns_stopping_state(self, temp_data_dir: Path) -> None:
        """GET /server/status returns stopping state during server shutdown (AC: 1)."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.STOPPING

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["state"] == "stopping"
        finally:
            app.dependency_overrides.clear()

    def test_status_returns_installed_after_error(self, temp_data_dir: Path) -> None:
        """GET /server/status returns installed after process error (AC: 1).

        Note: ERROR is a transitional state during failed operations. Once the
        process ends, the status returns to INSTALLED since the server files
        exist. This test verifies the expected behavior after an error.
        """
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        # Simulate a previous error - server crashed with exit code 1
        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.INSTALLED  # Reverted from ERROR
        test_service._last_exit_code = 1  # Non-zero indicates error

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["state"] == "installed"
            assert data["data"]["last_exit_code"] == 1  # Error indicated by exit code
        finally:
            app.dependency_overrides.clear()

    def test_status_returns_negative_exit_code(self, temp_data_dir: Path) -> None:
        """GET /server/status includes negative exit codes (signal kills) (AC: 1)."""
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.INSTALLED
        test_service._last_exit_code = -9  # Killed by SIGKILL

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["last_exit_code"] == -9
        finally:
            app.dependency_overrides.clear()

    def test_status_uptime_calculation_accuracy(self, temp_data_dir: Path) -> None:
        """GET /server/status calculates uptime from server start time accurately (AC: 3)."""
        import time

        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings

        # Create server files
        server_dir = temp_data_dir / "server"
        vsmanager_dir = temp_data_dir / "vsmanager"
        server_dir.mkdir(parents=True, exist_ok=True)
        vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "VintagestoryServer.dll").touch()
        (server_dir / "VintagestoryLib.dll").touch()
        (vsmanager_dir / "current_version").write_text("1.21.3")

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor=TEST_MONITOR_KEY,
            data_dir=temp_data_dir,
        )

        # Set a precise start time
        start_time = time.time() - 120.5  # 120.5 seconds ago

        test_service = ServerService(test_settings)
        test_service._server_state = ServerState.RUNNING
        test_service._server_start_time = start_time

        mock_process = MagicMock()
        mock_process.returncode = None
        test_service._process = mock_process

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1alpha1/server/status",
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            assert response.status_code == 200
            data = response.json()
            # Uptime should be 120 seconds (truncated from 120.5)
            # Allow 1 second tolerance for test execution time
            assert 119 <= data["data"]["uptime_seconds"] <= 122
        finally:
            app.dependency_overrides.clear()
