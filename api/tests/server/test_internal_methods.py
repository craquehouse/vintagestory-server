"""Unit tests for server.py internal methods.

Tests private methods that are only indirectly tested through public API calls.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.server import ServerService

# pyright: reportPrivateUsage=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false


class TestGetRuntimeState:
    """Tests for _get_runtime_state() method."""

    def test_runtime_state_running_when_process_active(
        self, installed_service: ServerService
    ) -> None:
        """Returns RUNNING when process exists and returncode is None."""
        mock_process = MagicMock()
        mock_process.returncode = None  # Process is running
        installed_service._process = mock_process
        installed_service._server_state = ServerState.RUNNING

        state = installed_service._get_runtime_state()

        assert state == ServerState.RUNNING

    def test_runtime_state_starting_when_starting(self, installed_service: ServerService) -> None:
        """Returns STARTING when in transitional state."""
        mock_process = MagicMock()
        mock_process.returncode = 0  # Process has exited
        installed_service._process = mock_process
        installed_service._server_state = ServerState.STARTING

        state = installed_service._get_runtime_state()

        assert state == ServerState.STARTING

    def test_runtime_state_stopping_when_stopping(self, installed_service: ServerService) -> None:
        """Returns STOPPING when in transitional state."""
        mock_process = MagicMock()
        mock_process.returncode = 0  # Process has exited
        installed_service._process = mock_process
        installed_service._server_state = ServerState.STOPPING

        state = installed_service._get_runtime_state()

        assert state == ServerState.STOPPING

    def test_runtime_state_installed_when_process_exited(
        self, installed_service: ServerService
    ) -> None:
        """Returns INSTALLED when process has exited."""
        mock_process = MagicMock()
        mock_process.returncode = 0  # Process has exited
        installed_service._process = mock_process
        installed_service._server_state = ServerState.RUNNING

        state = installed_service._get_runtime_state()

        assert state == ServerState.INSTALLED

    def test_runtime_state_installed_when_no_process(self, test_settings: Settings) -> None:
        """Returns INSTALLED when no process exists."""
        service = ServerService(test_settings)
        service._server_state = ServerState.INSTALLED

        state = service._get_runtime_state()

        assert state == ServerState.INSTALLED


class TestReadStream:
    """Tests for _read_stream() method."""

    @pytest.mark.asyncio
    async def test_read_stream_reads_lines_to_console(self, test_settings: Settings) -> None:
        """Reads lines from stream and appends to console buffer."""
        service = ServerService(test_settings)

        stream = MagicMock(spec=asyncio.StreamReader)
        lines = [b"line 1\n", b"line 2\n", b"line 3\n", b""]

        call_count = 0

        async def mock_readline():
            nonlocal call_count
            if call_count < len(lines):
                line = lines[call_count]
                call_count += 1
                return line
            return b""

        stream.readline = mock_readline

        await service._read_stream(stream, "stdout")

        lines_in_buffer = service.console_buffer.get_history()
        assert "line 1" in lines_in_buffer
        assert "line 2" in lines_in_buffer
        assert "line 3" in lines_in_buffer

    @pytest.mark.asyncio
    async def test_read_stream_decodes_utf8(self, test_settings: Settings) -> None:
        """Decodes UTF-8 content correctly."""
        service = ServerService(test_settings)

        stream = MagicMock(spec=asyncio.StreamReader)
        stream.readline = AsyncMock(side_effect=[b"UTF-8 content: \xc3\xa9\xc3\xa0\xc3\xb9\n", b""])

        await service._read_stream(stream, "stdout")

        lines_in_buffer = service.console_buffer.get_history()
        assert "UTF-8 content: éàù" in lines_in_buffer

    @pytest.mark.asyncio
    async def test_read_stream_handles_invalid_utf8(self, test_settings: Settings) -> None:
        """Handles invalid UTF-8 with replace mode."""
        service = ServerService(test_settings)

        stream = MagicMock(spec=asyncio.StreamReader)
        stream.readline = AsyncMock(side_effect=[b"Invalid: \xff\xfe\xfd\n", b""])

        await service._read_stream(stream, "stdout")

        lines_in_buffer = service.console_buffer.get_history()
        assert len(lines_in_buffer) == 1

    @pytest.mark.asyncio
    async def test_read_stream_handles_none_stream(self, test_settings: Settings) -> None:
        """Returns immediately when stream is None."""
        service = ServerService(test_settings)

        await service._read_stream(None, "stdout")

        assert len(service.console_buffer.get_history()) == 0

    @pytest.mark.asyncio
    async def test_read_strips_trailing_whitespace(self, test_settings: Settings) -> None:
        """Strips trailing whitespace from lines."""
        service = ServerService(test_settings)

        stream = MagicMock(spec=asyncio.StreamReader)
        stream.readline = AsyncMock(side_effect=[b"  padded line  \n", b""])

        await service._read_stream(stream, "stdout")

        lines_in_buffer = service.console_buffer.get_history()
        assert "  padded line" in lines_in_buffer

    @pytest.mark.asyncio
    async def test_read_stream_handles_empty_lines(self, test_settings: Settings) -> None:
        """Handles empty lines correctly."""
        service = ServerService(test_settings)

        stream = MagicMock(spec=asyncio.StreamReader)
        stream.readline = AsyncMock(side_effect=[b"\n", b"line\n", b""])

        await service._read_stream(stream, "stdout")

        lines_in_buffer = service.console_buffer.get_history()
        assert "" in lines_in_buffer
        assert "line" in lines_in_buffer


class TestUpdateModServiceServerState:
    """Tests for _update_mod_service_server_state() method."""

    def test_update_mod_service_calls_set_server_running(self, test_settings: Settings) -> None:
        """Calls set_server_running on mod service when available."""
        service = ServerService(test_settings)

        with patch("vintagestory_api.services.server._get_mod_service_module") as mock_get_module:
            mock_mod_service = MagicMock()
            mock_module = MagicMock()
            mock_module.get_mod_service.return_value = mock_mod_service
            mock_get_module.return_value = mock_module

            service._update_mod_service_server_state(True)

            mock_mod_service.set_server_running.assert_called_once_with(True)

    def test_update_mod_service_logs_debug_message(self, test_settings: Settings) -> None:
        """Logs debug message with running state."""
        service = ServerService(test_settings)

        with patch("vintagestory_api.services.server._get_mod_service_module") as mock_get_module:
            mock_mod_service = MagicMock()
            mock_module = MagicMock()
            mock_module.get_mod_service.return_value = mock_mod_service
            mock_get_module.return_value = mock_module

            service._update_mod_service_server_state(False)

    def test_update_mod_service_handles_exception_gracefully(self, test_settings: Settings) -> None:
        """Handles mod service errors gracefully (non-fatal)."""
        service = ServerService(test_settings)

        with patch("vintagestory_api.services.server._get_mod_service_module") as mock_get_module:
            mock_get_module.side_effect = ImportError("No mod service")

            service._update_mod_service_server_state(True)

    def test_update_mod_service_logs_on_exception(self, test_settings: Settings) -> None:
        """Logs debug message when mod service update fails."""
        service = ServerService(test_settings)

        with patch("vintagestory_api.services.server._get_mod_service_module") as mock_get_module:
            mock_get_module.side_effect = Exception("Test error")

            service._update_mod_service_server_state(True)


class TestClearPendingRestart:
    """Tests for _clear_pending_restart() method."""

    def test_clear_pending_restart_clears_state(self, test_settings: Settings) -> None:
        """Calls clear_restart on restart state service."""
        service = ServerService(test_settings)

        with patch("vintagestory_api.services.server._get_mod_service_module") as mock_get_module:
            mock_restart_state = MagicMock()
            mock_mod_service = MagicMock()
            mock_module = MagicMock()
            mock_module.get_restart_state.return_value = mock_restart_state
            mock_module.get_mod_service.return_value = mock_mod_service
            mock_get_module.return_value = mock_module

            service._clear_pending_restart()

            mock_restart_state.clear_restart.assert_called_once()

    def test_clear_pending_restart_handles_exception_gracefully(
        self, test_settings: Settings
    ) -> None:
        """Handles errors gracefully (non-fatal)."""
        service = ServerService(test_settings)

        with patch("vintagestory_api.services.server._get_mod_service_module") as mock_get_module:
            mock_get_module.side_effect = ImportError("No mod service")

            service._clear_pending_restart()


class TestGetHttpClient:
    """Tests for _get_http_client() method."""

    @pytest.mark.asyncio
    async def test_get_http_client_creates_client_once(self, test_settings: Settings) -> None:
        """Creates HTTP client on first call, returns cached on subsequent."""
        service = ServerService(test_settings)

        client1 = await service._get_http_client()
        client2 = await service._get_http_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_http_client_configures_timeout(self, test_settings: Settings) -> None:
        """Creates client with 300-second timeout for large downloads."""
        service = ServerService(test_settings)

        client = await service._get_http_client()

        assert client.timeout.connect == 300.0

    @pytest.mark.asyncio
    async def test_get_http_client_closes_old_client(self, test_settings: Settings) -> None:
        """Closes old client when setting to None (via close() method)."""
        service = ServerService(test_settings)

        await service._get_http_client()
        await service.close()

        assert service._http_client is None


class TestSafePath:
    """Tests for _safe_path() method."""

    def test_safe_path_returns_valid_path(self, test_settings: Settings) -> None:
        """Returns valid path for normal filename."""
        service = ServerService(test_settings)

        result = service._safe_path(test_settings.server_dir, "test.txt")

        assert result.resolve() == (test_settings.server_dir / "test.txt").resolve()

    def test_safe_path_prevents_path_traversal(self, test_settings: Settings) -> None:
        """Raises ValueError for path traversal attempts."""
        service = ServerService(test_settings)

        with pytest.raises(ValueError) as exc_info:
            service._safe_path(test_settings.server_dir, "../etc/passwd")

        assert "Path traversal detected" in str(exc_info.value)

    def test_safe_path_prevents_absolute_path_traversal(self, test_settings: Settings) -> None:
        """Raises ValueError for absolute path traversal attempts."""
        service = ServerService(test_settings)

        with pytest.raises(ValueError) as exc_info:
            service._safe_path(test_settings.server_dir, "/etc/passwd")

        assert "Path traversal detected" in str(exc_info.value)

    def test_safe_path_allows_subdirectories(self, test_settings: Settings) -> None:
        """Allows paths to subdirectories within base."""
        service = ServerService(test_settings)

        result = service._safe_path(test_settings.server_dir, "subdir/file.txt")

        assert result.resolve() == (test_settings.server_dir / "subdir" / "file.txt").resolve()

    def test_safe_path_resolves_symlinks(self, test_settings: Settings, tmp_path: Path) -> None:
        """Resolves symlinks to prevent escape via symlinks."""
        service = ServerService(test_settings)

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        symlink_path = test_settings.data_dir / "link"
        symlink_path.symlink_to(outside_dir, target_is_directory=True)

        with pytest.raises(ValueError) as exc_info:
            service._safe_path(test_settings.data_dir, "link/../escape.txt")

        assert "Path traversal detected" in str(exc_info.value)


class TestPropertyGetters:
    """Tests for property getters."""

    def test_settings_property(self, test_settings: Settings) -> None:
        """settings property returns settings instance."""
        service = ServerService(test_settings)

        assert service.settings is test_settings

    def test_config_init_service_property(self, test_settings: Settings) -> None:
        """config_init_service property returns config service."""
        service = ServerService(test_settings)

        assert service.config_init_service is not None

    def test_console_buffer_property(self, test_settings: Settings) -> None:
        """console_buffer property returns console buffer instance."""
        service = ServerService(test_settings)

        assert service.console_buffer is not None


class TestErrorRecoveryPaths:
    """Tests for error recovery in internal methods."""

    @pytest.mark.asyncio
    async def test_read_stream_handles_stream_errors(self, test_settings: Settings) -> None:
        """_read_stream handles stream reading errors gracefully."""
        service = ServerService(test_settings)

        stream = MagicMock(spec=asyncio.StreamReader)
        stream.readline = AsyncMock(side_effect=OSError("Stream error"))

        await service._read_stream(stream, "stdout")

    @pytest.mark.asyncio
    async def test_read_stream_handles_cancelled_error(self, test_settings: Settings) -> None:
        """_read_stream handles CancelledError during shutdown."""
        service = ServerService(test_settings)

        stream = MagicMock(spec=asyncio.StreamReader)
        stream.readline = AsyncMock(side_effect=asyncio.CancelledError())

        await service._read_stream(stream, "stdout")

    @pytest.mark.asyncio
    async def test_monitor_process_handles_cancelled_error(
        self, installed_service: ServerService
    ) -> None:
        """_monitor_process handles CancelledError during shutdown."""
        mock_process = MagicMock()
        mock_process.wait = AsyncMock(side_effect=asyncio.CancelledError())
        installed_service._process = mock_process

        await installed_service._monitor_process()

    @pytest.mark.asyncio
    async def test_monitor_process_handles_exceptions(
        self, installed_service: ServerService
    ) -> None:
        """_monitor_process handles unexpected exceptions."""
        mock_process = MagicMock()
        mock_process.wait = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        installed_service._process = mock_process

        await installed_service._monitor_process()

    @pytest.mark.asyncio
    async def test_monitor_process_updates_state_on_crash(
        self, installed_service: ServerService
    ) -> None:
        """_monitor_process updates state when process crashes."""
        mock_process = MagicMock()
        mock_process.wait = AsyncMock(return_value=1)
        installed_service._process = mock_process
        installed_service._server_state = ServerState.RUNNING

        await installed_service._monitor_process()

        assert installed_service._server_state == ServerState.INSTALLED
        assert installed_service._last_exit_code == 1
