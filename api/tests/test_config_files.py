"""Tests for ConfigFilesService.

Story 6.5: Raw Config Viewer

Tests the config files service for listing and reading raw configuration files.
Focuses heavily on path traversal prevention as the core security requirement.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vintagestory_api.services.config_files import (
    ConfigFileNotFoundError,
    ConfigFilesService,
    ConfigPathInvalidError,
)


@pytest.fixture
def mock_settings(tmp_path: Path) -> MagicMock:
    """Create mock settings with a temporary serverdata directory."""
    settings = MagicMock()
    settings.serverdata_dir = tmp_path / "serverdata"
    settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
    return settings


@pytest.fixture
def service(mock_settings: MagicMock) -> ConfigFilesService:
    """Create a ConfigFilesService with mock settings."""
    return ConfigFilesService(settings=mock_settings)


class TestListDirectories:
    """Tests for ConfigFilesService.list_directories()."""

    def test_list_directories_returns_subdirectory_names(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should return list of subdirectory names in serverdata_dir."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "ModConfigs").mkdir()
        (serverdata / "Playerdata").mkdir()
        (serverdata / "Macros").mkdir()
        # Also create a file to verify it's not included
        (serverdata / "serverconfig.json").write_text('{}')

        result = service.list_directories()

        assert result == ["Macros", "ModConfigs", "Playerdata"]

    def test_list_directories_empty_directory(
        self, service: ConfigFilesService
    ) -> None:
        """Should return empty list when no subdirectories exist."""
        result = service.list_directories()
        assert result == []

    def test_list_directories_directory_not_exists(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should return empty list when serverdata_dir doesn't exist."""
        mock_settings.serverdata_dir.rmdir()

        result = service.list_directories()

        assert result == []

    def test_list_directories_excludes_hidden_directories(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should not include hidden directories (starting with dot)."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "ModConfigs").mkdir()
        (serverdata / ".hidden").mkdir()

        result = service.list_directories()

        assert result == ["ModConfigs"]

    def test_list_directories_excludes_files(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should only return directories, not files."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "ModConfigs").mkdir()
        (serverdata / "serverconfig.json").write_text('{}')
        (serverdata / "not-a-dir.txt").write_text('text')

        result = service.list_directories()

        assert result == ["ModConfigs"]


class TestListFiles:
    """Tests for ConfigFilesService.list_files()."""

    def test_list_files_returns_json_files(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should return list of JSON filenames in serverdata_dir."""
        # Create some JSON files
        serverdata = mock_settings.serverdata_dir
        (serverdata / "serverconfig.json").write_text('{"key": "value"}')
        (serverdata / "other-config.json").write_text('{"foo": "bar"}')
        (serverdata / "not-json.txt").write_text("plain text")

        result = service.list_files()

        assert result == ["other-config.json", "serverconfig.json"]

    def test_list_files_empty_directory(self, service: ConfigFilesService) -> None:
        """Should return empty list when no JSON files exist."""
        result = service.list_files()
        assert result == []

    def test_list_files_directory_not_exists(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should return empty list when serverdata_dir doesn't exist."""
        # Remove the directory
        mock_settings.serverdata_dir.rmdir()

        result = service.list_files()

        assert result == []

    def test_list_files_excludes_subdirectories(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should not include files from subdirectories."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "serverconfig.json").write_text('{"key": "value"}')
        subdir = serverdata / "subdir"
        subdir.mkdir()
        (subdir / "nested.json").write_text('{"nested": true}')

        result = service.list_files()

        assert result == ["serverconfig.json"]


class TestReadFile:
    """Tests for ConfigFilesService.read_file()."""

    def test_read_file_success(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should return filename and parsed JSON content."""
        serverdata = mock_settings.serverdata_dir
        content = {"Port": 42420, "ServerName": "Test Server"}
        (serverdata / "serverconfig.json").write_text(json.dumps(content))

        result = service.read_file("serverconfig.json")

        assert result == {"filename": "serverconfig.json", "content": content}

    def test_read_file_not_found(self, service: ConfigFilesService) -> None:
        """Should raise ConfigFileNotFoundError for missing files."""
        with pytest.raises(ConfigFileNotFoundError) as exc_info:
            service.read_file("nonexistent.json")

        assert exc_info.value.filename == "nonexistent.json"
        assert "Config file not found" in exc_info.value.message

    def test_read_file_invalid_json(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should handle malformed JSON gracefully."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "broken.json").write_text("not valid json {")

        result = service.read_file("broken.json")

        assert result["filename"] == "broken.json"
        content = result["content"]
        assert isinstance(content, dict)
        assert "_raw" in content
        assert "_parse_error" in content


class TestPathTraversalPrevention:
    """Security tests for path traversal prevention.

    These tests verify the service properly rejects all forms of
    path traversal attacks as specified in the story requirements.
    """

    def test_simple_parent_traversal(self, service: ConfigFilesService) -> None:
        """Should reject ../secrets.json (simple parent traversal)."""
        with pytest.raises(ConfigPathInvalidError) as exc_info:
            service.read_file("../secrets.json")

        assert exc_info.value.filename == "../secrets.json"
        assert "Invalid file path" in exc_info.value.message

    def test_nested_parent_traversal(self, service: ConfigFilesService) -> None:
        """Should reject subdir/../../secrets.json (nested traversal)."""
        with pytest.raises(ConfigPathInvalidError) as exc_info:
            service.read_file("subdir/../../secrets.json")

        assert exc_info.value.filename == "subdir/../../secrets.json"

    def test_absolute_path(self, service: ConfigFilesService) -> None:
        """Should reject /etc/passwd (absolute path)."""
        with pytest.raises(ConfigPathInvalidError) as exc_info:
            service.read_file("/etc/passwd")

        assert exc_info.value.filename == "/etc/passwd"

    def test_double_dot_variations(self, service: ConfigFilesService) -> None:
        """Should handle ....//secrets.json (double-dot variations).

        Note: ....// is not a valid path traversal sequence - it's treated
        as a literal filename. The file simply won't exist, so we get
        ConfigFileNotFoundError rather than ConfigPathInvalidError.
        This is correct behavior as Path.resolve() normalizes the path
        and it stays within serverdata_dir.
        """
        # This is not actually path traversal - it's a weird but valid filename
        # that doesn't exist, so we get FileNotFoundError
        with pytest.raises(ConfigFileNotFoundError):
            service.read_file("....//secrets.json")

    def test_url_encoded_traversal(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should handle URL-encoded traversal (decoded at router level).

        Note: URL-encoded paths like %2e%2e%2f would be decoded by FastAPI
        before reaching the service. The service sees the decoded version.
        This test verifies the decoded version is still rejected.
        """
        # After URL decoding, %2e%2e%2f becomes ../
        with pytest.raises(ConfigPathInvalidError):
            service.read_file("../secrets.json")

    def test_multiple_slashes(self, service: ConfigFilesService) -> None:
        """Should reject paths with multiple slashes trying to escape."""
        with pytest.raises(ConfigPathInvalidError) as exc_info:
            service.read_file("foo/../../../etc/passwd")

        assert exc_info.value.filename == "foo/../../../etc/passwd"

    def test_windows_style_path_traversal(self, service: ConfigFilesService) -> None:
        """Should reject Windows-style backslash traversal attempts."""
        # On POSIX, backslashes might be treated as literal characters,
        # but we should still validate the resolved path
        with pytest.raises((ConfigPathInvalidError, ConfigFileNotFoundError)):
            # This may raise either error depending on how OS handles backslashes
            service.read_file("..\\secrets.json")

    def test_subdirectory_within_serverdata_allowed(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should allow reading files from subdirectories within serverdata.

        Files in subdirectories are valid as long as they remain within
        the serverdata_dir boundary. This allows reading config files
        that VintageStory might place in subdirectories.
        """
        serverdata = mock_settings.serverdata_dir
        subdir = serverdata / "subdir"
        subdir.mkdir()
        (subdir / "config.json").write_text('{"nested": true}')

        result = service.read_file("subdir/config.json")

        assert result["filename"] == "subdir/config.json"
        assert result["content"] == {"nested": True}


class TestSafePathMethod:
    """Direct tests for the _safe_path() method.

    Note: _safe_path is a private method, but we test it directly to ensure
    the security-critical path validation logic works correctly.
    """

    def test_safe_path_valid_filename(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should return resolved path for valid filename."""
        base_dir = mock_settings.serverdata_dir
        # pyright: ignore[reportPrivateUsage] - Testing private security method
        result = service._safe_path(base_dir, "serverconfig.json")  # pyright: ignore[reportPrivateUsage]

        assert result == base_dir.resolve() / "serverconfig.json"

    def test_safe_path_rejects_traversal(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should raise ConfigPathInvalidError for path traversal."""
        base_dir = mock_settings.serverdata_dir

        with pytest.raises(ConfigPathInvalidError):
            service._safe_path(base_dir, "../etc/passwd")  # pyright: ignore[reportPrivateUsage]
