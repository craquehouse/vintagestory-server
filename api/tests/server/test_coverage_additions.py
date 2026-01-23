"""Additional tests to improve server.py coverage.

This file contains tests targeting specific uncovered lines and edge cases
to improve overall test coverage.
"""

import asyncio
import io
import re
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.server import (
    VS_CDN_BASE,
    VS_STABLE_API,
    VS_UNSTABLE_API,
    ServerService,
    _vintagestory_tar_filter,
)

# pyright: reportPrivateUsage=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false


def _configure_stream_mocks(process: AsyncMock) -> None:
    """Configure stdout/stderr mocks to return EOF immediately.

    This prevents 'coroutine was never awaited' warnings from stream reading tasks.
    """
    process.stdout = AsyncMock()
    process.stdout.readline = AsyncMock(return_value=b"")
    process.stderr = AsyncMock()
    process.stderr.readline = AsyncMock(return_value=b"")


class TestTarFilterLinkname:
    """Tests for _vintagestory_tar_filter handling of symlinks (line 123)."""

    def test_tar_filter_strips_linkname_prefix(self, test_settings: Settings) -> None:
        """Custom tar filter strips numeric prefix from symlink linkname field."""
        member = tarfile.TarInfo(name="15070731126/somefile.txt")
        member.linkname = "15070731126/target.txt"  # Symlink with bogus prefix

        # Call the filter
        filtered = _vintagestory_tar_filter(member, str(test_settings.server_dir))

        # Both name and linkname should have prefix stripped
        assert filtered is not None
        assert filtered.name == "somefile.txt"
        assert filtered.linkname == "target.txt"  # Line 123 covered

    def test_tar_filter_handles_empty_linkname(self, test_settings: Settings) -> None:
        """Custom tar filter handles empty linkname (no symlink)."""
        member = tarfile.TarInfo(name="15070731126/regular.txt")
        member.linkname = ""  # Regular file, not a symlink

        filtered = _vintagestory_tar_filter(member, str(test_settings.server_dir))

        assert filtered is not None
        assert filtered.name == "regular.txt"
        assert filtered.linkname == ""  # Empty linkname passes through


class TestResolveVersionAliasEdgeCases:
    """Tests for resolve_version_alias edge cases (lines 291, 308-324)."""

    @pytest.mark.asyncio
    async def test_resolve_version_alias_invalid_channel_returns_none(
        self, server_service: ServerService
    ) -> None:
        """resolve_version_alias returns None for invalid channel (line 291)."""
        result = await server_service.resolve_version_alias("invalid-channel")

        assert result is None  # Line 291 covered

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_version_alias_fallback_when_no_latest_flag(
        self, server_service: ServerService
    ) -> None:
        """resolve_version_alias uses fallback when no version marked as latest (lines 308-315)."""
        # Mock API response with no version marked as latest
        mock_response = {
            "1.21.6": {
                "linuxserver": {
                    "filename": "vs_server_linux-x64_1.21.6.tar.gz",
                    "filesize": "40.2 MB",
                    "md5": "abc123",
                    "urls": {
                        "cdn": f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.6.tar.gz",
                        "local": "https://local.example.com/1.21.6.tar.gz",
                    },
                    "latest": False,  # NOT marked as latest
                }
            },
            "1.21.5": {
                "linuxserver": {
                    "filename": "vs_server_linux-x64_1.21.5.tar.gz",
                    "filesize": "40.1 MB",
                    "md5": "def456",
                    "urls": {
                        "cdn": f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.5.tar.gz",
                        "local": "https://local.example.com/1.21.5.tar.gz",
                    },
                    "latest": False,  # NOT marked as latest
                }
            },
        }

        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=mock_response))

        result = await server_service.resolve_version_alias("stable")

        # Should return highest version as fallback (lines 308-315)
        assert result == "1.21.6"

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_version_alias_handles_http_error(
        self, server_service: ServerService
    ) -> None:
        """resolve_version_alias handles HTTPError gracefully (lines 318-324)."""
        # Mock API to raise HTTPError
        respx.get(VS_STABLE_API).mock(return_value=Response(500))

        result = await server_service.resolve_version_alias("stable")

        # Should return None and log warning (lines 318-324)
        assert result is None


class TestGetAvailableVersionsEdgeCases:
    """Tests for get_available_versions edge cases (lines 357-364)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_available_versions_skips_missing_cdn_url(
        self, server_service: ServerService
    ) -> None:
        """get_available_versions skips versions with missing CDN URL (lines 357-364)."""
        mock_response = {
            "1.21.6": {
                "linuxserver": {
                    "filename": "vs_server_linux-x64_1.21.6.tar.gz",
                    "filesize": "40.2 MB",
                    "md5": "abc123",
                    "urls": {
                        "cdn": f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.6.tar.gz",
                        "local": "https://local.example.com/1.21.6.tar.gz",
                    },
                    "latest": True,
                }
            },
            "1.21.5": {
                "linuxserver": {
                    "filename": "vs_server_linux-x64_1.21.5.tar.gz",
                    "filesize": "40.1 MB",
                    "md5": "def456",
                    "urls": {
                        # Missing CDN URL - should skip this version
                        "local": "https://local.example.com/1.21.5.tar.gz",
                    },
                    "latest": False,
                }
            },
        }

        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=mock_response))

        versions = await server_service.get_available_versions("stable")

        # Should only include 1.21.6, skip 1.21.5 (lines 357-364)
        assert len(versions) == 1
        assert "1.21.6" in versions
        assert "1.21.5" not in versions

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_available_versions_skips_missing_local_url(
        self, server_service: ServerService
    ) -> None:
        """get_available_versions skips versions with missing local URL (lines 357-364)."""
        mock_response = {
            "1.21.6": {
                "linuxserver": {
                    "filename": "vs_server_linux-x64_1.21.6.tar.gz",
                    "filesize": "40.2 MB",
                    "md5": "abc123",
                    "urls": {
                        "cdn": f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.6.tar.gz",
                        # Missing local URL - should skip this version
                    },
                    "latest": True,
                }
            },
        }

        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=mock_response))

        versions = await server_service.get_available_versions("stable")

        # Should skip 1.21.6 (lines 357-364)
        assert len(versions) == 0


class TestCheckVersionAvailableEdgeCases:
    """Tests for check_version_available edge cases (lines 405-406)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_check_version_available_logs_http_error(
        self, server_service: ServerService
    ) -> None:
        """check_version_available handles HTTPError and continues (lines 405-406)."""

        def raise_error(request: httpx.Request) -> Response:
            raise httpx.ConnectError("Connection failed")

        # First channel raises error, second succeeds
        stable_url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.3.tar.gz"
        unstable_url = f"{VS_CDN_BASE}/unstable/vs_server_linux-x64_1.21.3.tar.gz"

        respx.head(stable_url).mock(side_effect=raise_error)
        respx.head(unstable_url).mock(return_value=Response(200))

        available, channel = await server_service.check_version_available("1.21.3")

        # Should handle error gracefully and try unstable (lines 405-406)
        assert available is True
        assert channel == "unstable"


class TestGetVersionInfoEdgeCases:
    """Tests for get_version_info edge cases (lines 434-435)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_version_info_handles_http_error_gracefully(
        self, server_service: ServerService
    ) -> None:
        """get_version_info handles HTTPError and continues (lines 434-435)."""
        # Stable fails with HTTP error
        respx.get(VS_STABLE_API).mock(return_value=Response(500))

        # Unstable succeeds
        mock_unstable = {
            "1.21.3": {
                "linuxserver": {
                    "filename": "vs_server_linux-x64_1.21.3.tar.gz",
                    "filesize": "40.2 MB",
                    "md5": "abc123",
                    "urls": {
                        "cdn": f"{VS_CDN_BASE}/unstable/vs_server_linux-x64_1.21.3.tar.gz",
                        "local": "https://local.example.com/1.21.3.tar.gz",
                    },
                    "latest": True,
                }
            },
        }
        respx.get(VS_UNSTABLE_API).mock(return_value=Response(200, json=mock_unstable))

        info = await server_service.get_version_info("1.21.3")

        # Should handle stable error and try unstable (lines 434-435)
        assert info is not None
        assert info.version == "1.21.3"
        assert info.channel == "unstable"


class TestInstallServerVersionAlias:
    """Tests for install_server version alias resolution (lines 727-735)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_install_server_resolves_stable_alias(self, test_settings: Settings) -> None:
        """install_server resolves 'stable' alias to actual version (lines 727-735)."""
        mock_stable = {
            "1.21.6": {
                "linuxserver": {
                    "filename": "vs_server_linux-x64_1.21.6.tar.gz",
                    "filesize": "40.2 MB",
                    "md5": "abc123",
                    "urls": {
                        "cdn": f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.21.6.tar.gz",
                        "local": "https://local.example.com/1.21.6.tar.gz",
                    },
                    "latest": True,
                }
            },
        }

        respx.get(VS_STABLE_API).mock(return_value=Response(200, json=mock_stable))

        # Mock the version availability check
        respx.head(re.compile(r".*/stable/.*")).mock(return_value=Response(200))

        # Mock the download to return corrupted data (will fail during extraction)
        respx.get(re.compile(r".*/stable/.*\.tar\.gz")).mock(
            return_value=Response(
                200,
                content=b"corrupted",
                headers={"content-length": "9"},
            )
        )

        service = ServerService(test_settings)

        # Try to install "stable" alias
        progress = await service.install_server("stable")

        # Should resolve the alias then fail during installation (lines 727-735)
        # The key is that it tried to resolve "stable" to "1.21.6"
        assert progress.state == ServerState.ERROR
        assert progress.version == "1.21.6"  # Proves alias was resolved

        await service.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_install_server_alias_resolution_failure(
        self, test_settings: Settings
    ) -> None:
        """install_server returns error when alias resolution fails (lines 727-735)."""
        # Mock API to return empty (no versions)
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json={}))

        service = ServerService(test_settings)
        progress = await service.install_server("stable")

        # Should fail with error about resolving alias (lines 727-735)
        assert progress.state == ServerState.ERROR
        assert progress.error is not None
        assert "could not resolve" in progress.error.lower()
        assert progress.error_code == ErrorCode.VERSION_NOT_FOUND

        await service.close()


class TestInstallServerEdgeCases:
    """Tests for install_server edge cases (lines 755-759, 796-820)."""

    @pytest.mark.asyncio
    async def test_install_server_fails_when_already_installing(
        self, test_settings: Settings
    ) -> None:
        """install_server returns error when installation already in progress (lines 755-759)."""
        service = ServerService(test_settings)

        # Manually set state to INSTALLING
        service._install_state = ServerState.INSTALLING

        progress = await service.install_server("1.21.3")

        # Should return error about installation in progress (lines 755-759)
        assert progress.state == ServerState.ERROR
        assert progress.error is not None
        assert "installation already in progress" in progress.error.lower()
        assert progress.error_code == ErrorCode.INSTALLATION_IN_PROGRESS

    @respx.mock
    @pytest.mark.asyncio
    async def test_install_server_verification_failed(self, test_settings: Settings) -> None:
        """install_server handles verification failure (lines 796-800)."""
        # Mock version check to pass
        respx.head(re.compile(r".*/stable/.*")).mock(return_value=Response(200))

        # Mock download to return empty tarball (will fail to extract required files)
        empty_tarball = io.BytesIO()
        with tarfile.open(fileobj=empty_tarball, mode="w:gz") as tar:
            # Add a dummy file that's NOT a required file
            info = tarfile.TarInfo(name="dummy.txt")
            info.size = 5
            tar.addfile(info, io.BytesIO(b"dummy"))

        tarball_bytes = empty_tarball.getvalue()

        respx.get(re.compile(r".*/stable/.*\.tar\.gz")).mock(
            return_value=Response(
                200,
                content=tarball_bytes,
                headers={"content-length": str(len(tarball_bytes))},
            )
        )

        # Mock API to skip checksum
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json={}))
        respx.get(VS_UNSTABLE_API).mock(return_value=Response(200, json={}))

        service = ServerService(test_settings)
        progress = await service.install_server("1.21.3")

        # Should fail verification (lines 796-800)
        assert progress.state == ServerState.ERROR
        assert progress.error is not None
        assert "verification failed" in progress.error.lower()
        assert progress.error_code == ErrorCode.INSTALLATION_FAILED

        await service.close()

    @respx.mock
    @pytest.mark.asyncio
    async def test_install_server_handles_extraction_exception(
        self, test_settings: Settings
    ) -> None:
        """install_server handles exceptions during extraction (lines 816-820)."""
        # Mock version check to pass
        respx.head(re.compile(r".*/stable/.*")).mock(return_value=Response(200))

        # Mock download to return corrupted tarball
        respx.get(re.compile(r".*/stable/.*\.tar\.gz")).mock(
            return_value=Response(
                200,
                content=b"not a valid tarball",
                headers={"content-length": "19"},
            )
        )

        # Mock API to skip checksum
        respx.get(VS_STABLE_API).mock(return_value=Response(200, json={}))
        respx.get(VS_UNSTABLE_API).mock(return_value=Response(200, json={}))

        service = ServerService(test_settings)
        progress = await service.install_server("1.21.3")

        # Should handle exception and set error (lines 816-820)
        assert progress.state == ServerState.ERROR
        assert progress.error is not None
        assert progress.error_code == ErrorCode.INSTALLATION_FAILED

        await service.close()


class TestCleanupFailedInstall:
    """Tests for _cleanup_failed_install edge cases (line 835)."""

    def test_cleanup_failed_install_removes_required_files(self, test_settings: Settings) -> None:
        """_cleanup_failed_install removes extracted server files (line 835)."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)

        # Create required files
        (test_settings.server_dir / "VintagestoryServer.dll").write_text("test")
        (test_settings.server_dir / "VintagestoryLib.dll").write_text("test")

        service = ServerService(test_settings)
        service._cleanup_failed_install()

        # Files should be removed (line 835)
        assert not (test_settings.server_dir / "VintagestoryServer.dll").exists()
        assert not (test_settings.server_dir / "VintagestoryLib.dll").exists()


class TestStartServerEdgeCases:
    """Tests for start_server edge cases (lines 936-937)."""

    @pytest.mark.asyncio
    async def test_start_server_fails_when_already_starting(
        self, installed_service: ServerService
    ) -> None:
        """start_server raises error when server already in STARTING state (lines 936-937)."""
        # Manually set state to STARTING
        installed_service._server_state = ServerState.STARTING

        with pytest.raises(RuntimeError) as exc_info:
            await installed_service.start_server()

        # Should raise error about already starting (lines 936-937)
        assert ErrorCode.SERVER_ALREADY_RUNNING in str(exc_info.value)


class TestMonitorProcessEdgeCases:
    """Tests for _monitor_process edge cases (line 1145)."""

    @pytest.mark.asyncio
    async def test_monitor_process_returns_early_when_no_process(
        self, installed_service: ServerService
    ) -> None:
        """_monitor_process returns immediately when process is None (line 1145)."""
        # Ensure process is None
        installed_service._process = None

        # Should return immediately without error (line 1145)
        await installed_service._monitor_process()

        # No assertions needed - just verify it doesn't hang or error


class TestGetServerServiceSingleton:
    """Tests for get_server_service singleton function (lines 57-59)."""

    def test_get_server_service_creates_singleton(self, test_settings: Settings) -> None:
        """get_server_service creates singleton on first call (lines 57-59)."""
        from vintagestory_api.services import server as server_module

        # Reset the singleton
        server_module._server_service = None

        # First call should create the singleton
        service1 = server_module.get_server_service()
        assert service1 is not None

        # Second call should return the same instance
        service2 = server_module.get_server_service()
        assert service1 is service2


class TestSendCommand:
    """Tests for send_command method (lines 1218-1235)."""

    @pytest.mark.asyncio
    async def test_send_command_success(self, installed_service: ServerService) -> None:
        """send_command successfully sends command to running server (lines 1218-1235)."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.stdin = AsyncMock()
            process.stdin.write = MagicMock()
            process.stdin.drain = AsyncMock()
            _configure_stream_mocks(process)

            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            await installed_service.start_server()

            # Send a command
            result = await installed_service.send_command("time get")

            # Should succeed (lines 1218-1235)
            assert result is True
            process.stdin.write.assert_called_once()
            call_args = process.stdin.write.call_args[0][0]
            assert b"time get\n" == call_args

    @pytest.mark.asyncio
    async def test_send_command_echoes_to_console(self, installed_service: ServerService) -> None:
        """send_command echoes command to console buffer (line 1228)."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None
            process.stdin = AsyncMock()
            process.stdin.write = MagicMock()
            process.stdin.drain = AsyncMock()
            _configure_stream_mocks(process)

            async def blocking_wait():
                try:
                    await asyncio.sleep(100)
                except asyncio.CancelledError:
                    pass
                return 0

            process.wait = AsyncMock(side_effect=blocking_wait)
            mock_exec.return_value = process

            await installed_service.start_server()

            # Send a command
            await installed_service.send_command("help")

            # Check console buffer
            history = installed_service.console_buffer.get_history()
            assert any("[CMD] help" in line for line in history)

    @pytest.mark.asyncio
    async def test_send_command_fails_when_no_process(
        self, installed_service: ServerService
    ) -> None:
        """send_command returns False when no process running (line 1218)."""
        result = await installed_service.send_command("test")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_fails_when_process_exited(
        self, installed_service: ServerService
    ) -> None:
        """send_command returns False when process has exited (line 1218)."""
        # Simulate exited process
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.returncode = 0  # Process exited
        installed_service._process = mock_process

        result = await installed_service.send_command("test")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_command_fails_when_stdin_none(
        self, installed_service: ServerService
    ) -> None:
        """send_command returns False when stdin is not available (lines 1222-1224)."""
        # Simulate process with no stdin
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.returncode = None  # Still running
        mock_process.stdin = None  # No stdin
        installed_service._process = mock_process

        result = await installed_service.send_command("test")

        assert result is False


class TestUninstallServerEdgeCases:
    """Tests for uninstall_server edge cases (lines 1292-1294)."""

    @pytest.mark.asyncio
    async def test_uninstall_server_handles_version_file_deletion_error(
        self, test_settings: Settings
    ) -> None:
        """uninstall_server handles OSError when deleting version file (lines 1292-1294)."""
        # Create installed server
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        test_settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
        (test_settings.server_dir / "VintagestoryServer.dll").touch()
        (test_settings.server_dir / "VintagestoryLib.dll").touch()
        version_file = test_settings.vsmanager_dir / "current_version"
        version_file.write_text("1.21.3")

        service = ServerService(test_settings)

        # Make version file read-only to trigger OSError on deletion
        version_file.chmod(0o444)

        # Also make the parent directory read-only
        test_settings.vsmanager_dir.chmod(0o555)

        try:
            with pytest.raises(RuntimeError) as exc_info:
                await service.uninstall_server()

            # Should handle OSError and raise with proper code (lines 1292-1294)
            assert ErrorCode.UNINSTALL_FAILED in str(exc_info.value)
        finally:
            # Cleanup: restore permissions
            test_settings.vsmanager_dir.chmod(0o755)
            if version_file.exists():
                version_file.chmod(0o644)


class TestInstallEndpointValidation:
    """Tests for install endpoint validation in routers/server.py (lines 65, 86)."""

    @respx.mock
    def test_install_invalid_version_after_alias_resolution_returns_422(
        self, temp_data_dir: Path
    ) -> None:
        """POST /server/install returns 422 when resolved alias version is invalid (line 65).

        This tests the case where an alias resolves to an invalid version format,
        which is caught by validate_version() in the router.
        """
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings
        from vintagestory_api.services.server import get_server_service
        from fastapi.testclient import TestClient
        from conftest import TEST_ADMIN_KEY

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor="test-monitor-key",
            data_dir=temp_data_dir,
        )

        # Create a test service
        test_service = ServerService(test_settings)

        # Override dependency
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            # Mock API to return invalid version format
            mock_response = {
                "invalid": {  # Not a valid X.Y.Z format
                    "linuxserver": {
                        "filename": "vs_server_linux-x64_invalid.tar.gz",
                        "filesize": "40.2 MB",
                        "md5": "abc123",
                        "urls": {
                            "cdn": f"{VS_CDN_BASE}/stable/vs_server_linux-x64_invalid.tar.gz",
                            "local": "https://local.example.com/invalid.tar.gz",
                        },
                        "latest": True,
                    }
                }
            }

            respx.get(VS_STABLE_API).mock(return_value=Response(200, json=mock_response))

            client = TestClient(app)
            response = client.post(
                "/api/v1alpha1/server/install",
                json={"version": "stable"},
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            # Should return 422 with INVALID_VERSION error (line 65)
            assert response.status_code == 422
            error = response.json()["detail"]
            assert error["code"] == ErrorCode.INVALID_VERSION
            assert "X.Y.Z" in error["message"]
        finally:
            app.dependency_overrides.clear()

    def test_install_when_installation_in_progress_returns_409(
        self, temp_data_dir: Path
    ) -> None:
        """POST /server/install returns 409 when installation already in progress (line 86).

        This tests the router's check for concurrent installation attempts.
        """
        from vintagestory_api.main import app
        from vintagestory_api.middleware.auth import get_settings
        from vintagestory_api.services.server import get_server_service
        from fastapi.testclient import TestClient
        from conftest import TEST_ADMIN_KEY

        test_settings = Settings(
            api_key_admin=TEST_ADMIN_KEY,
            api_key_monitor="test-monitor-key",
            data_dir=temp_data_dir,
        )

        # Create a test service and set it to INSTALLING state
        test_service = ServerService(test_settings)
        test_service._install_state = ServerState.INSTALLING
        test_service._install_stage = "downloading"
        test_service._install_version = "1.21.3"

        # Override dependency
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_server_service] = lambda: test_service

        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1alpha1/server/install",
                json={"version": "1.21.6"},
                headers={"X-API-Key": TEST_ADMIN_KEY},
            )

            # Should return 409 with INSTALLATION_IN_PROGRESS error (line 86)
            assert response.status_code == 409
            error = response.json()["detail"]
            assert error["code"] == ErrorCode.INSTALLATION_IN_PROGRESS
            assert "already in progress" in error["message"].lower()
        finally:
            app.dependency_overrides.clear()
