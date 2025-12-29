"""Tests for server installation, download, extraction, and progress tracking."""

import hashlib
import io
import re
import tarfile
from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import (
    InstallationStage,
    InstallProgress,
    ServerState,
)
from vintagestory_api.services.server import (
    VS_CDN_BASE,
    VS_STABLE_API,
    VS_UNSTABLE_API,
    ServerService,
)

# pyright: reportPrivateUsage=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false


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
