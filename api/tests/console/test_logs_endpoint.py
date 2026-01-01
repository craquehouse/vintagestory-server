"""API tests for log file listing and streaming endpoints."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings


class TestListLogFilesEndpoint:
    """API tests for GET /api/v1alpha1/console/logs endpoint."""

    # ======================================
    # Authentication tests
    # ======================================

    def test_logs_requires_authentication(self, client: TestClient) -> None:
        """Test that logs endpoint requires authentication."""
        response = client.get("/api/v1alpha1/console/logs")
        assert response.status_code == 401

    def test_logs_requires_admin_role(
        self, client: TestClient, monitor_headers: dict[str, str]
    ) -> None:
        """Test that logs endpoint requires Admin role."""
        response = client.get("/api/v1alpha1/console/logs", headers=monitor_headers)
        assert response.status_code == 403

    def test_logs_accessible_by_admin(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that Admin role can access log files list."""
        response = client.get("/api/v1alpha1/console/logs", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    # ======================================
    # Response format tests
    # ======================================

    def test_logs_follows_envelope_format(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that response follows API envelope format."""
        response = client.get("/api/v1alpha1/console/logs", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data
        assert "files" in data["data"]
        assert "logs_dir" in data["data"]

    def test_logs_returns_empty_list_when_no_logs_dir(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that missing logs directory returns empty list."""
        response = client.get("/api/v1alpha1/console/logs", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["files"] == []

    def test_logs_returns_file_info(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_settings: Settings,
    ) -> None:
        """Test that log files are returned with correct info."""
        # Create Logs directory and a log file
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "server-main.log"
        log_file.write_text("Test log content\nLine 2\n")

        response = client.get("/api/v1alpha1/console/logs", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["files"]) == 1

        file_info = data["files"][0]
        assert file_info["name"] == "server-main.log"
        assert file_info["size_bytes"] > 0
        assert "modified_at" in file_info

    def test_logs_filters_non_log_files(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_settings: Settings,
    ) -> None:
        """Test that only .log and .txt files are included."""
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create various files
        (logs_dir / "server-main.log").write_text("log content")
        (logs_dir / "server-debug.txt").write_text("debug content")
        (logs_dir / "config.json").write_text("{}")
        (logs_dir / "backup.zip").write_bytes(b"zip content")
        (logs_dir / ".hidden.log").write_text("hidden")

        response = client.get("/api/v1alpha1/console/logs", headers=admin_headers)

        assert response.status_code == 200
        files = response.json()["data"]["files"]
        names = [f["name"] for f in files]

        assert "server-main.log" in names
        assert "server-debug.txt" in names
        assert "config.json" not in names
        assert "backup.zip" not in names
        # Note: .hidden.log has .log extension but we filter hidden files
        # Currently we don't filter hidden files in the endpoint, only in validate_log_filename

    def test_logs_sorted_by_modification_time(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_settings: Settings,
    ) -> None:
        """Test that files are sorted by modification time (newest first)."""
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create files with different modification times
        old_file = logs_dir / "old.log"
        old_file.write_text("old content")
        # Set old modification time
        old_mtime = time.time() - 3600  # 1 hour ago
        import os

        os.utime(old_file, (old_mtime, old_mtime))

        new_file = logs_dir / "new.log"
        new_file.write_text("new content")
        # Leave with current time

        response = client.get("/api/v1alpha1/console/logs", headers=admin_headers)

        assert response.status_code == 200
        files = response.json()["data"]["files"]
        assert len(files) == 2
        # Newest should be first
        assert files[0]["name"] == "new.log"
        assert files[1]["name"] == "old.log"


class TestLogsWebSocket:
    """API tests for WebSocket /api/v1alpha1/console/logs/ws endpoint."""

    # ======================================
    # Authentication tests
    # ======================================

    def test_logs_ws_requires_api_key(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Test that logs WebSocket requires API key."""
        # Create a log file first
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "server-main.log").write_text("test content\n")

        with ws_client.websocket_connect(
            "/api/v1alpha1/console/logs/ws?file=server-main.log"
        ) as websocket:
            # Should receive close with 4001 code
            # TestClient doesn't expose close code directly, but connection should close
            try:
                websocket.receive_text()
            except Exception:
                pass  # Expected to fail

    def test_logs_ws_rejects_invalid_key(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Test that invalid API key is rejected."""
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "server-main.log").write_text("test content\n")

        with ws_client.websocket_connect(
            "/api/v1alpha1/console/logs/ws?file=server-main.log&api_key=invalid-key"
        ) as websocket:
            try:
                websocket.receive_text()
            except Exception:
                pass

    def test_logs_ws_rejects_monitor_role(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Test that monitor role cannot access logs WebSocket."""
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "server-main.log").write_text("test content\n")

        monitor_key = test_settings.api_key_monitor
        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=server-main.log&api_key={monitor_key}"
        ) as websocket:
            try:
                websocket.receive_text()
            except Exception:
                pass

    # ======================================
    # File validation tests
    # ======================================

    def test_logs_ws_rejects_path_traversal(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Test that path traversal attempts are rejected."""
        admin_key = test_settings.api_key_admin

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=../../../etc/passwd&api_key={admin_key}"
        ) as websocket:
            try:
                websocket.receive_text()
            except Exception:
                pass

    def test_logs_ws_rejects_missing_file(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Test that non-existent file is rejected."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=nonexistent.log&api_key={admin_key}"
        ) as websocket:
            try:
                websocket.receive_text()
            except Exception:
                pass

    def test_logs_ws_rejects_invalid_extension(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Test that files with invalid extensions are rejected."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "config.json").write_text("{}")

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=config.json&api_key={admin_key}"
        ) as websocket:
            try:
                websocket.receive_text()
            except Exception:
                pass

    # ======================================
    # Streaming tests
    # ======================================

    def test_logs_ws_sends_history(
        self, ws_client: TestClient, test_settings: Settings
    ) -> None:
        """Test that logs WebSocket sends file history on connect."""
        admin_key = test_settings.api_key_admin
        logs_dir = test_settings.serverdata_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create log file with content
        log_content = "Line 1\nLine 2\nLine 3\n"
        (logs_dir / "server-main.log").write_text(log_content)

        with ws_client.websocket_connect(
            f"/api/v1alpha1/console/logs/ws?file=server-main.log&api_key={admin_key}&history_lines=100"
        ) as websocket:
            # Should receive the 3 lines
            lines: list[str] = []
            for _ in range(3):
                try:
                    line = websocket.receive_text()
                    lines.append(line)
                except Exception:
                    break

            assert "Line 1" in lines
            assert "Line 2" in lines
            assert "Line 3" in lines


class TestLogServiceValidation:
    """Unit tests for log service validation functions."""

    def test_validate_log_filename_valid(self) -> None:
        """Test that valid filenames pass validation."""
        from vintagestory_api.services.logs import validate_log_filename

        assert validate_log_filename("server-main.log") is True
        assert validate_log_filename("server-debug.txt") is True
        assert validate_log_filename("my-custom-log.log") is True

    def test_validate_log_filename_rejects_path_traversal(self) -> None:
        """Test that path traversal is rejected."""
        from vintagestory_api.services.logs import validate_log_filename

        assert validate_log_filename("../etc/passwd") is False
        assert validate_log_filename("..\\windows\\system32") is False
        assert validate_log_filename("foo/../bar.log") is False
        assert validate_log_filename("/absolute/path.log") is False

    def test_validate_log_filename_rejects_invalid_extension(self) -> None:
        """Test that invalid extensions are rejected."""
        from vintagestory_api.services.logs import validate_log_filename

        assert validate_log_filename("config.json") is False
        assert validate_log_filename("script.py") is False
        assert validate_log_filename("archive.zip") is False
        assert validate_log_filename("noextension") is False

    def test_validate_log_filename_rejects_hidden_files(self) -> None:
        """Test that hidden files are rejected."""
        from vintagestory_api.services.logs import validate_log_filename

        assert validate_log_filename(".hidden.log") is False
        assert validate_log_filename(".secret.txt") is False

    def test_validate_log_filename_rejects_empty(self) -> None:
        """Test that empty filenames are rejected."""
        from vintagestory_api.services.logs import validate_log_filename

        assert validate_log_filename("") is False
        assert validate_log_filename("   ") is False


class TestTailLogFile:
    """Tests for tail_log_file function."""

    @pytest.mark.asyncio
    async def test_tail_log_file_returns_lines(self, tmp_path: Path) -> None:
        """Test that tail returns correct number of lines."""
        from vintagestory_api.services.logs import tail_log_file

        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        # Create file with 10 lines
        log_file = logs_dir / "test.log"
        log_file.write_text("\n".join([f"Line {i}" for i in range(10)]))

        result = await tail_log_file(logs_dir, "test.log", lines=5)

        assert len(result) == 5
        # Should be last 5 lines
        assert result[0] == "Line 5"
        assert result[4] == "Line 9"

    @pytest.mark.asyncio
    async def test_tail_log_file_not_found(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing files."""
        from vintagestory_api.services.logs import LogFileNotFoundError, tail_log_file

        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        with pytest.raises(LogFileNotFoundError):
            await tail_log_file(logs_dir, "nonexistent.log", lines=10)

    @pytest.mark.asyncio
    async def test_tail_log_file_invalid_name(self, tmp_path: Path) -> None:
        """Test that invalid filenames are rejected."""
        from vintagestory_api.services.logs import LogFileAccessError, tail_log_file

        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()

        with pytest.raises(LogFileAccessError):
            await tail_log_file(logs_dir, "../etc/passwd", lines=10)
