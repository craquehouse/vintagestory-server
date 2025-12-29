"""Tests for server lifecycle management (start, stop, restart, status)."""

import asyncio
import signal
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import (
    InstallationStage,
    LifecycleAction,
    ServerState,
)
from vintagestory_api.services.server import ServerService

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


@pytest.fixture
def mock_subprocess() -> Generator[tuple[MagicMock, AsyncMock], None, None]:
    """Mock asyncio.create_subprocess_exec for testing.

    Uses an Event to simulate blocking wait that can be unblocked for stop tests.
    Configures stdout/stderr to return empty bytes immediately (EOF) to avoid
    unawaited coroutine warnings from auto-mocked streams.
    """
    with patch("asyncio.create_subprocess_exec") as mock:
        process = AsyncMock()
        process.pid = 12345
        process.returncode = None  # None = still running

        # Configure streams to avoid unawaited coroutine warnings
        _configure_stream_mocks(process)

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
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
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
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """start_server() returns LifecycleResponse with correct data."""
        del mock_subprocess  # Fixture sets up mock, not inspected

        response = await installed_service.start_server()

        assert response.action == LifecycleAction.START
        assert response.previous_state == ServerState.INSTALLED
        assert response.new_state == ServerState.RUNNING
        assert response.message == "Server start initiated"

    @pytest.mark.asyncio
    async def test_start_server_updates_state_to_running(
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """start_server() updates server state to RUNNING."""
        del mock_subprocess  # Fixture sets up mock, not inspected

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
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """start_server() raises error when server already running."""
        del mock_subprocess  # Fixture sets up mock, not inspected

        # Start server once
        await installed_service.start_server()

        # Try to start again
        with pytest.raises(RuntimeError) as exc_info:
            await installed_service.start_server()

        assert ErrorCode.SERVER_ALREADY_RUNNING in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_server_starts_monitor_task(
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """start_server() starts background monitor task."""
        del mock_subprocess  # Fixture sets up mock, not inspected

        await installed_service.start_server()

        assert installed_service._monitor_task is not None
        assert not installed_service._monitor_task.done()

    @pytest.mark.asyncio
    async def test_start_server_includes_data_path_arg(
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """start_server() includes --dataPath argument."""
        mock_exec, _ = mock_subprocess

        await installed_service.start_server()

        call_args = mock_exec.call_args[0]
        assert "--dataPath" in call_args


class TestStopServer:
    """Tests for stop_server() method (Subtask 1.3, AC: 2)."""

    @pytest.mark.asyncio
    async def test_stop_server_sends_sigterm(
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """stop_server() sends SIGTERM for graceful shutdown."""
        _, mock_process = mock_subprocess

        await installed_service.start_server()
        await installed_service.stop_server()

        mock_process.send_signal.assert_called_with(signal.SIGTERM)

    @pytest.mark.asyncio
    async def test_stop_server_returns_lifecycle_response(
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """stop_server() returns LifecycleResponse with correct data."""
        del mock_subprocess  # Fixture sets up mock, not inspected

        await installed_service.start_server()
        response = await installed_service.stop_server()

        assert response.action == LifecycleAction.STOP
        assert response.previous_state == ServerState.RUNNING
        assert response.new_state == ServerState.INSTALLED
        assert response.message == "Server stopped"

    @pytest.mark.asyncio
    async def test_stop_server_updates_state_to_installed(
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """stop_server() updates server state back to INSTALLED."""
        del mock_subprocess  # Fixture sets up mock, not inspected

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
            _configure_stream_mocks(process)

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
            _configure_stream_mocks(process)

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
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """restart_server() stops and starts when server is running."""
        del mock_subprocess  # Fixture sets up mock, not inspected

        await installed_service.start_server()
        response = await installed_service.restart_server()

        assert response.action == LifecycleAction.RESTART
        assert response.previous_state == ServerState.RUNNING
        assert response.new_state == ServerState.RUNNING
        assert response.message == "Server restarted"

    @pytest.mark.asyncio
    async def test_restart_server_when_stopped(
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """restart_server() starts server when not running."""
        del mock_subprocess  # Fixture sets up mock, not inspected

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
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """Monitor task updates state when process crashes."""
        _, mock_process = mock_subprocess
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
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """Monitor task records exit code on crash."""
        _, mock_process = mock_subprocess
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
            _configure_stream_mocks(process)

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
            _configure_stream_mocks(process)

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
        self, installed_service: ServerService, mock_subprocess: tuple[MagicMock, AsyncMock]
    ) -> None:
        """Concurrent start calls are serialized by lock."""
        _, mock_process = mock_subprocess

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
            _configure_stream_mocks(process)

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
            _configure_stream_mocks(process)

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
        _configure_stream_mocks(mock_process)

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
            _configure_stream_mocks(new_process)

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
            _configure_stream_mocks(process)

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
            _configure_stream_mocks(new_process)

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
            _configure_stream_mocks(process)

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
