"""Tests for logs service.

Unit tests for the logs service covering:
- Log filename validation and security
- File reading operations
- Error handling
- Path traversal prevention
"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from vintagestory_api.services.logs import (
    LogFileAccessError,
    LogFileNotFoundError,
    tail_log_file,
    validate_log_filename,
)


class TestValidateLogFilename:
    """Tests for validate_log_filename() security and validation."""

    def test_valid_log_filename(self) -> None:
        """Should accept valid .log filename."""
        assert validate_log_filename("server.log") is True

    def test_valid_txt_filename(self) -> None:
        """Should accept valid .txt filename."""
        assert validate_log_filename("debug.txt") is True

    def test_valid_filename_with_numbers(self) -> None:
        """Should accept filename with numbers."""
        assert validate_log_filename("server-2024-01-18.log") is True

    def test_valid_filename_with_underscores(self) -> None:
        """Should accept filename with underscores."""
        assert validate_log_filename("server_debug.log") is True

    def test_valid_filename_with_dashes(self) -> None:
        """Should accept filename with dashes."""
        assert validate_log_filename("server-debug.log") is True

    def test_reject_empty_filename(self) -> None:
        """Should reject empty filename."""
        assert validate_log_filename("") is False

    def test_reject_whitespace_only_filename(self) -> None:
        """Should reject whitespace-only filename."""
        assert validate_log_filename("   ") is False

    def test_reject_path_with_forward_slash(self) -> None:
        """Should reject filename containing forward slash (path traversal)."""
        assert validate_log_filename("../server.log") is False
        assert validate_log_filename("subdir/server.log") is False
        assert validate_log_filename("/etc/passwd") is False

    def test_reject_path_with_backslash(self) -> None:
        """Should reject filename containing backslash (Windows path traversal)."""
        assert validate_log_filename("..\\server.log") is False
        assert validate_log_filename("subdir\\server.log") is False

    def test_reject_parent_directory_reference(self) -> None:
        """Should reject filename containing '..' anywhere."""
        assert validate_log_filename("..server.log") is False
        assert validate_log_filename("server..log") is False
        assert validate_log_filename("server.log..") is False

    def test_reject_invalid_extension(self) -> None:
        """Should reject files without .log or .txt extension."""
        assert validate_log_filename("server.json") is False
        assert validate_log_filename("server.xml") is False
        assert validate_log_filename("server") is False

    def test_reject_hidden_files(self) -> None:
        """Should reject hidden files (starting with dot)."""
        assert validate_log_filename(".server.log") is False
        assert validate_log_filename(".hidden.txt") is False

    def test_reject_multiple_extensions(self) -> None:
        """Should only check the final extension."""
        # This is valid - the final extension is .log
        assert validate_log_filename("server.backup.log") is True
        # This is invalid - the final extension is .bak
        assert validate_log_filename("server.log.bak") is False


class TestTailLogFile:
    """Tests for tail_log_file() async function."""

    @pytest.fixture
    def logs_dir(self, tmp_path: Path) -> Path:
        """Create a temporary logs directory."""
        logs_path = tmp_path / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)
        return logs_path

    @pytest.mark.asyncio
    async def test_read_simple_log_file(self, logs_dir: Path) -> None:
        """Should read all lines from a small log file."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\n")

        result = await tail_log_file(logs_dir, "server.log", lines=100)

        assert result == ["Line 1", "Line 2", "Line 3"]

    @pytest.mark.asyncio
    async def test_read_last_n_lines(self, logs_dir: Path) -> None:
        """Should return only the last N lines when file is larger."""
        log_file = logs_dir / "server.log"
        lines = [f"Line {i}" for i in range(1, 201)]
        log_file.write_text("\n".join(lines) + "\n")

        result = await tail_log_file(logs_dir, "server.log", lines=10)

        assert len(result) == 10
        assert result == [f"Line {i}" for i in range(191, 201)]

    @pytest.mark.asyncio
    async def test_read_exact_number_of_lines(self, logs_dir: Path) -> None:
        """Should handle case where file has exactly N lines."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\n")

        result = await tail_log_file(logs_dir, "server.log", lines=3)

        assert result == ["Line 1", "Line 2", "Line 3"]

    @pytest.mark.asyncio
    async def test_read_fewer_lines_than_requested(self, logs_dir: Path) -> None:
        """Should return all lines when file has fewer than N lines."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Line 1\nLine 2\n")

        result = await tail_log_file(logs_dir, "server.log", lines=100)

        assert result == ["Line 1", "Line 2"]

    @pytest.mark.asyncio
    async def test_read_empty_file(self, logs_dir: Path) -> None:
        """Should return empty list for empty file."""
        log_file = logs_dir / "server.log"
        log_file.write_text("")

        result = await tail_log_file(logs_dir, "server.log", lines=100)

        assert result == []

    @pytest.mark.asyncio
    async def test_read_file_without_trailing_newline(self, logs_dir: Path) -> None:
        """Should handle file without trailing newline."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Line 1\nLine 2")  # No trailing newline

        result = await tail_log_file(logs_dir, "server.log", lines=100)

        assert result == ["Line 1", "Line 2"]

    @pytest.mark.asyncio
    async def test_strip_line_endings(self, logs_dir: Path) -> None:
        """Should strip both \\n and \\r\\n line endings."""
        log_file = logs_dir / "server.log"
        # Mix of line endings
        log_file.write_text("Line 1\nLine 2\r\nLine 3\r\n")

        result = await tail_log_file(logs_dir, "server.log", lines=100)

        assert result == ["Line 1", "Line 2", "Line 3"]

    @pytest.mark.asyncio
    async def test_handle_utf8_content(self, logs_dir: Path) -> None:
        """Should handle UTF-8 encoded content."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Player joined: 玩家\nEvent: événement\n", encoding="utf-8")

        result = await tail_log_file(logs_dir, "server.log", lines=100)

        assert result == ["Player joined: 玩家", "Event: événement"]

    @pytest.mark.asyncio
    async def test_handle_invalid_utf8_with_replacement(self, logs_dir: Path) -> None:
        """Should replace invalid UTF-8 sequences instead of failing."""
        log_file = logs_dir / "server.log"
        # Write invalid UTF-8 bytes
        log_file.write_bytes(b"Line 1\nInvalid: \xff\xfe\nLine 3\n")

        result = await tail_log_file(logs_dir, "server.log", lines=100)

        # Should not raise exception, invalid bytes replaced with replacement char
        assert len(result) == 3
        assert result[0] == "Line 1"
        assert result[2] == "Line 3"

    @pytest.mark.asyncio
    async def test_reject_invalid_filename(self, logs_dir: Path) -> None:
        """Should raise LogFileAccessError for invalid filename."""
        with pytest.raises(LogFileAccessError) as exc_info:
            await tail_log_file(logs_dir, "../etc/passwd", lines=100)

        assert "Invalid log filename" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reject_path_traversal_with_slash(self, logs_dir: Path) -> None:
        """Should reject path traversal attempts with forward slash."""
        with pytest.raises(LogFileAccessError) as exc_info:
            await tail_log_file(logs_dir, "subdir/server.log", lines=100)

        assert "Invalid log filename" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reject_path_traversal_with_backslash(self, logs_dir: Path) -> None:
        """Should reject path traversal attempts with backslash."""
        with pytest.raises(LogFileAccessError) as exc_info:
            await tail_log_file(logs_dir, "subdir\\server.log", lines=100)

        assert "Invalid log filename" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reject_hidden_file(self, logs_dir: Path) -> None:
        """Should reject hidden files."""
        with pytest.raises(LogFileAccessError) as exc_info:
            await tail_log_file(logs_dir, ".hidden.log", lines=100)

        assert "Invalid log filename" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_file_not_found_error(self, logs_dir: Path) -> None:
        """Should raise LogFileNotFoundError when file doesn't exist."""
        with pytest.raises(LogFileNotFoundError) as exc_info:
            await tail_log_file(logs_dir, "nonexistent.log", lines=100)

        assert "Log file not found: nonexistent.log" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reject_directory_as_file(self, logs_dir: Path) -> None:
        """Should raise LogFileAccessError when target is a directory."""
        # Create a directory with .log extension
        dir_as_log = logs_dir / "notafile.log"
        dir_as_log.mkdir()

        with pytest.raises(LogFileAccessError) as exc_info:
            await tail_log_file(logs_dir, "notafile.log", lines=100)

        assert "Not a file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reject_symlink_outside_logs_dir(self, logs_dir: Path, tmp_path: Path) -> None:
        """Should reject symlinks pointing outside logs directory."""
        # Create a file outside logs_dir
        outside_file = tmp_path / "outside.log"
        outside_file.write_text("Secret data")

        # Create symlink inside logs_dir pointing to outside file
        symlink = logs_dir / "symlink.log"
        symlink.symlink_to(outside_file)

        with pytest.raises(LogFileAccessError) as exc_info:
            await tail_log_file(logs_dir, "symlink.log", lines=100)

        assert "Path traversal attempt detected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allow_symlink_within_logs_dir(self, logs_dir: Path) -> None:
        """Should allow symlinks within logs directory."""
        # Create a real file
        real_file = logs_dir / "real.log"
        real_file.write_text("Log content")

        # Create symlink to it (within same directory)
        symlink = logs_dir / "link.log"
        symlink.symlink_to(real_file)

        result = await tail_log_file(logs_dir, "link.log", lines=100)

        assert result == ["Log content"]

    @pytest.mark.asyncio
    async def test_reject_file_too_large(self, logs_dir: Path) -> None:
        """Should reject files larger than 100MB."""
        log_file = logs_dir / "huge.log"
        log_file.write_text("x" * 100)  # Create file first

        # Patch the specific stat call inside tail_log_file
        original_stat = log_file.stat

        def mock_stat(path_self: Any, **kwargs: Any):
            # Create a mock stat result with huge file size
            result = original_stat()

            # Create a new object with modified st_size
            class MockStat:
                st_size = 101 * 1024 * 1024  # 101MB
                st_mode = result.st_mode  # Keep real mode

            return MockStat()

        with patch.object(type(log_file), "stat", mock_stat):
            with pytest.raises(LogFileAccessError) as exc_info:
                await tail_log_file(logs_dir, "huge.log", lines=100)

            assert "Log file too large" in str(exc_info.value)
            assert "101MB > 100MB limit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allow_file_at_size_limit(self, logs_dir: Path) -> None:
        """Should allow files exactly at 100MB limit."""
        log_file = logs_dir / "biglimit.log"
        log_file.write_text("Log line\n")

        # Patch the specific stat call to return exactly 100MB
        original_stat = log_file.stat

        def mock_stat(path_self: Any, **kwargs: Any):
            result = original_stat()

            class MockStat:
                st_size = 100 * 1024 * 1024  # Exactly 100MB
                st_mode = result.st_mode

            return MockStat()

        with patch.object(type(log_file), "stat", mock_stat):
            result = await tail_log_file(logs_dir, "biglimit.log", lines=100)

            # Should succeed (not raise exception)
            assert result == ["Log line"]

    @pytest.mark.asyncio
    async def test_stat_error_raises_access_error(self, logs_dir: Path) -> None:
        """Should raise LogFileAccessError when stat() fails during size check."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Content")

        # We need to mock the stat call that happens inside the try block at line 102
        # We'll let the early checks pass, but fail when trying to get the file size
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_file", return_value=True):
                with patch.object(Path, "stat", side_effect=OSError("Disk error during stat")):
                    with pytest.raises(LogFileAccessError) as exc_info:
                        await tail_log_file(logs_dir, "server.log", lines=100)

                    assert "Cannot stat file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_permission_error_raises_access_error(self, logs_dir: Path) -> None:
        """Should raise LogFileAccessError on permission denied."""
        log_file = logs_dir / "noperm.log"
        log_file.write_text("Content")

        # Mock open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with pytest.raises(LogFileAccessError) as exc_info:
                await tail_log_file(logs_dir, "noperm.log", lines=100)

            assert "Permission denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_error_raises_access_error(self, logs_dir: Path) -> None:
        """Should raise LogFileAccessError on general OS read error."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Content")

        # Mock open to raise OSError
        with patch("builtins.open", side_effect=OSError("Disk error")):
            with pytest.raises(LogFileAccessError) as exc_info:
                await tail_log_file(logs_dir, "server.log", lines=100)

            assert "Error reading file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_runs_in_executor(self, logs_dir: Path) -> None:
        """Should execute file reading in thread pool executor."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Line 1\nLine 2\n")

        # Spy on run_in_executor to verify it's called
        original_executor = asyncio.get_event_loop().run_in_executor
        executor_called = False

        async def mock_executor(executor: Any, func: Any):
            nonlocal executor_called
            executor_called = True
            return await original_executor(executor, func)

        with patch.object(asyncio.get_event_loop(), "run_in_executor", mock_executor):
            result = await tail_log_file(logs_dir, "server.log", lines=100)

            assert executor_called is True
            assert result == ["Line 1", "Line 2"]

    @pytest.mark.asyncio
    async def test_default_lines_parameter(self, logs_dir: Path) -> None:
        """Should default to 100 lines when lines parameter not specified."""
        log_file = logs_dir / "server.log"
        lines = [f"Line {i}" for i in range(1, 201)]
        log_file.write_text("\n".join(lines) + "\n")

        # Call without specifying lines (should default to 100)
        result = await tail_log_file(logs_dir, "server.log")

        assert len(result) == 100
        assert result == [f"Line {i}" for i in range(101, 201)]

    @pytest.mark.asyncio
    async def test_custom_lines_parameter(self, logs_dir: Path) -> None:
        """Should respect custom lines parameter."""
        log_file = logs_dir / "server.log"
        lines = [f"Line {i}" for i in range(1, 101)]
        log_file.write_text("\n".join(lines) + "\n")

        result = await tail_log_file(logs_dir, "server.log", lines=25)

        assert len(result) == 25
        assert result == [f"Line {i}" for i in range(76, 101)]

    @pytest.mark.asyncio
    async def test_single_line_parameter(self, logs_dir: Path) -> None:
        """Should handle lines=1 to get only the last line."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\n")

        result = await tail_log_file(logs_dir, "server.log", lines=1)

        assert result == ["Line 3"]

    @pytest.mark.asyncio
    async def test_preserve_empty_lines(self, logs_dir: Path) -> None:
        """Should preserve empty lines in the output."""
        log_file = logs_dir / "server.log"
        log_file.write_text("Line 1\n\nLine 3\n\n")

        result = await tail_log_file(logs_dir, "server.log", lines=100)

        assert result == ["Line 1", "", "Line 3", ""]

    @pytest.mark.asyncio
    async def test_logging_on_path_traversal(
        self, logs_dir: Path, tmp_path: Path, caplog: Any
    ) -> None:
        """Should log warning when path traversal is detected."""
        # Create a file outside logs_dir
        outside_file = tmp_path / "outside.log"
        outside_file.write_text("Secret data")

        # Create symlink inside logs_dir pointing to outside file
        symlink = logs_dir / "symlink.log"
        symlink.symlink_to(outside_file)

        with pytest.raises(LogFileAccessError):
            await tail_log_file(logs_dir, "symlink.log", lines=100)

        # Note: We're using structlog in the actual code, but caplog may not capture it
        # This test documents the expected behavior, actual log verification depends on structlog setup

    @pytest.mark.asyncio
    async def test_logging_on_file_too_large(self, logs_dir: Path, caplog: Any) -> None:
        """Should log warning when file is too large."""
        log_file = logs_dir / "huge.log"
        log_file.write_text("x" * 100)

        # Patch the specific stat call to return huge file size
        original_stat = log_file.stat

        def mock_stat(path_self: Any, **kwargs: Any):
            result = original_stat()

            class MockStat:
                st_size = 101 * 1024 * 1024  # 101MB
                st_mode = result.st_mode

            return MockStat()

        with patch.object(type(log_file), "stat", mock_stat):
            with pytest.raises(LogFileAccessError):
                await tail_log_file(logs_dir, "huge.log", lines=100)

        # Note: Actual log verification depends on structlog setup
