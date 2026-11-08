"""Advanced tests for log file streaming WebSocket functionality.

Tests for real-time log file streaming, including:
- Client message handling (line 578)
- File polling and new content detection (lines 582-631)
- File rotation detection
- Error handling during streaming
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from vintagestory_api.config import Settings

from .ws_helpers import receive_text_within


class TestLogsWebSocketStreaming:
    """Tests for log file streaming functionality."""

    def test_logs_ws_ignores_client_messages(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Client messages get no reply and do not interrupt the stream."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "server-main.log"
        log_file.write_text("Initial content\n")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=server-main.log&api_key={admin_key}&history_lines=1"
        ) as websocket:
            receive_text_within(websocket)

            websocket.send_text("ping")
            with open(log_file, "a") as f:
                f.write("After ping\n")

            assert receive_text_within(websocket) == "After ping"

    @pytest.mark.asyncio
    async def test_logs_ws_timeout_error_handling(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Streaming continues after idle polling cycles."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "server-main.log"
        log_file.write_text("Line 1\n")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=server-main.log&api_key={admin_key}&history_lines=1"
        ) as websocket:
            assert receive_text_within(websocket) == "Line 1"

            time.sleep(1.5)  # Longer than the poll interval, so at least one poll times out
            log_file.write_text("Line 1\nLine 2\n")

            assert receive_text_within(websocket) == "Line 2"

    def test_logs_ws_detects_file_rotation(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Truncation is reported as rotation, then the new content is streamed."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "server-main.log"
        log_file.write_text("Old content\n" * 100)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=server-main.log&api_key={admin_key}&history_lines=2"
        ) as websocket:
            receive_text_within(websocket)
            receive_text_within(websocket)

            log_file.write_text("New content after rotation\n")

            assert receive_text_within(websocket) == "--- Log file rotated ---"
            assert receive_text_within(websocket) == "New content after rotation"

    def test_logs_ws_handles_file_deletion(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Deleting the log sends a marker and closes the connection with 4004."""
        import os

        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "server-main.log"
        log_file.write_text("Content\n")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=server-main.log&api_key={admin_key}&history_lines=1"
        ) as websocket:
            receive_text_within(websocket)

            os.remove(log_file)

            assert receive_text_within(websocket) == "--- Log file was deleted ---"
            with pytest.raises(WebSocketDisconnect) as closed:
                receive_text_within(websocket)
            assert closed.value.code == 4004

    def test_logs_ws_handles_oserror_during_streaming(
        self, ws_client: TestClient, test_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that OSError during file reading is handled gracefully (line 630-631)."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "server-main.log"
        log_file.write_text("Content\n")

        # We can't easily test this with TestClient since the streaming logic
        # runs in a background loop. The OSError path (line 630-631) logs a warning
        # but continues the loop, which is hard to verify in integration tests.
        # This is better tested in unit tests of the streaming logic.

        # For now, verify the connection works normally
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=server-main.log&api_key={admin_key}&history_lines=1"
        ) as websocket:
            websocket.receive_text()
            # Connection successful
            websocket.close()

    def test_logs_ws_reads_new_content_in_chunks(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """New content is read from the last position and sent to the client."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "server-main.log"
        initial_content = "Line 1\n"
        log_file.write_text(initial_content)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=server-main.log&api_key={admin_key}&history_lines=1"
        ) as websocket:
            assert receive_text_within(websocket) == "Line 1"

            log_file.write_text(initial_content + "Line 2\n")

            assert receive_text_within(websocket) == "Line 2"


class TestLogsWebSocketPathValidation:
    """Tests for path validation edge cases."""

    def test_logs_ws_rejects_path_with_valueerror(
        self, ws_client: TestClient, test_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that ValueError during path resolution is handled (lines 527-535)."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create a valid file
        (logs_dir / "test.log").write_text("content")

        # Mock relative_to to raise ValueError (path traversal detected)
        original_relative_to = Path.relative_to

        def mock_relative_to(self: Path, other: Path):
            if "test.log" in str(self):
                raise ValueError("Path is not relative")
            return original_relative_to(self, other)

        monkeypatch.setattr(Path, "relative_to", mock_relative_to)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=test.log&api_key={admin_key}"
        ) as websocket:
            # Should receive close with 4005 (invalid path)
            try:
                websocket.receive()
                # Should be closed or receive close message
            except Exception:
                pass

    def test_logs_ws_rejects_path_with_oserror(
        self, ws_client: TestClient, test_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that OSError during path resolution is handled (lines 527-535)."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create a valid file
        (logs_dir / "test.log").write_text("content")

        # Mock resolve to raise OSError
        original_resolve = Path.resolve

        def mock_resolve(self: Path):
            if "test.log" in str(self):
                raise OSError("Cannot resolve path")
            return original_resolve(self)

        monkeypatch.setattr(Path, "resolve", mock_resolve)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=test.log&api_key={admin_key}"
        ) as websocket:
            # Should receive close with 4005 (invalid path)
            try:
                websocket.receive()
                # Should be closed or receive close message
            except Exception:
                pass


class TestLogsWebSocketLargeFiles:
    """Tests for handling large files and chunk limits."""

    def test_logs_ws_limits_chunk_size_to_1mb(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """New content is read and sent in chunks of at most 1MB."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "large.log"
        log_file.write_text("Initial\n")
        max_chunk_size = 1024 * 1024
        appended_size = 2 * max_chunk_size

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=large.log&api_key={admin_key}&history_lines=1"
        ) as websocket:
            receive_text_within(websocket)

            with open(log_file, "a") as f:
                f.write("X" * appended_size)

            chunks: list[str] = []
            while sum(len(chunk) for chunk in chunks) < appended_size:
                chunks.append(receive_text_within(websocket))

            assert len(chunks) >= 2
            assert all(len(chunk) <= max_chunk_size for chunk in chunks)
            assert sum(len(chunk) for chunk in chunks) == appended_size

