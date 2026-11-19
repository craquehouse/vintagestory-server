"""Tests for ConfigFilesService.

Story 6.5: Raw Config Viewer

Tests the config files service for listing and reading raw configuration files.
Focuses heavily on path traversal prevention as the core security requirement.
"""

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vintagestory_api.services.config_files import (
    CONFIG_FILE_MAX_BYTES,
    ConfigDirectoryForbiddenError,
    ConfigFileNotFoundError,
    ConfigFileNotSupportedError,
    ConfigFileReadError,
    ConfigFilesService,
    ConfigFileTooLargeError,
    ConfigPathInvalidError,
)
from vintagestory_api.services.config_parse import CONFIG_FILE_MAX_DEPTH
from vintagestory_api.services.game_config import REDACTED

# Story 17.5: a made-up password for the redaction tests; never a real value.
SECRET = "pw-Zq9-monitor-must-not-see"


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
        (serverdata / "serverconfig.json").write_text("{}")

        result = service.list_directories(role="admin")

        assert result == ["Macros", "ModConfigs", "Playerdata"]

    def test_list_directories_empty_directory(self, service: ConfigFilesService) -> None:
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

    def test_list_directories_includes_hidden_directories(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should include hidden directories (frontend handles filtering)."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "ModConfigs").mkdir()
        (serverdata / ".hidden").mkdir()

        result = service.list_directories(role="admin")

        assert result == [".hidden", "ModConfigs"]

    def test_list_directories_excludes_files(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should only return directories, not files."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "ModConfigs").mkdir()
        (serverdata / "serverconfig.json").write_text("{}")
        (serverdata / "not-a-dir.txt").write_text("text")

        result = service.list_directories(role="admin")

        assert result == ["ModConfigs"]

    def test_list_directories_with_subdirectory(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should list directories within a subdirectory (nested browsing)."""
        serverdata = mock_settings.serverdata_dir
        cache_dir = serverdata / "Cache"
        cache_dir.mkdir()
        (cache_dir / "unpack").mkdir()
        (cache_dir / "downloads").mkdir()
        (cache_dir / "temp.json").write_text("{}")

        result = service.list_directories("Cache", role="admin")

        assert result == ["downloads", "unpack"]

    def test_list_directories_nested_subdirectory(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should list directories at any nesting level."""
        serverdata = mock_settings.serverdata_dir
        deep_dir = serverdata / "Cache" / "unpack" / "modname"
        deep_dir.mkdir(parents=True)
        (deep_dir / "assets").mkdir()
        (deep_dir / "lang").mkdir()

        result = service.list_directories("Cache/unpack/modname", role="admin")

        assert result == ["assets", "lang"]

    def test_list_directories_path_traversal_blocked(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should reject path traversal attempts in directory parameter."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "ModConfigs").mkdir()

        with pytest.raises(ConfigPathInvalidError):
            service.list_directories("../")

    def test_list_directories_nonexistent_subdirectory(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should return empty list for nonexistent subdirectory."""
        result = service.list_directories("NonexistentDir", role="admin")

        assert result == []


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

    def test_list_files_in_subdirectory(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should return JSON files from specified subdirectory."""
        serverdata = mock_settings.serverdata_dir
        subdir = serverdata / "ModConfigs"
        subdir.mkdir()
        (subdir / "mod1.json").write_text('{"enabled": true}')
        (subdir / "mod2.json").write_text('{"enabled": false}')
        (subdir / "readme.txt").write_text("not json")
        # Root level file should not be included
        (serverdata / "serverconfig.json").write_text("{}")

        result = service.list_files(directory="ModConfigs", role="admin")

        assert result == ["mod1.json", "mod2.json"]

    def test_list_files_subdirectory_not_exists(self, service: ConfigFilesService) -> None:
        """Should return empty list when subdirectory doesn't exist."""
        result = service.list_files(directory="NonExistent", role="admin")

        assert result == []

    def test_list_files_subdirectory_path_traversal(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should reject path traversal in directory parameter."""
        # Create a file outside serverdata that we shouldn't be able to access
        outside_dir = mock_settings.serverdata_dir.parent / "secret"
        outside_dir.mkdir()
        (outside_dir / "passwords.json").write_text('{"admin": "secret"}')

        with pytest.raises(ConfigPathInvalidError):
            service.list_files(directory="../secret")

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

    def test_list_files_uses_the_viewer_file_rule(
        self, service: ConfigFilesService, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """Story 19.1 AC 1: the listing holds exactly the files the viewer can read."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "a.json").write_text("{}")
        (serverdata / "B.JSON").write_text("{}")
        (serverdata / "notes.txt").write_text("text")
        (serverdata / "dir.json").mkdir()
        (serverdata / "link.json").symlink_to(serverdata / "notes.txt")
        outside = tmp_path / "outside.json"
        outside.write_text("{}")
        (serverdata / "out.json").symlink_to(outside)

        result = service.list_files(role="admin")

        assert result == ["B.JSON", "a.json"]
        for name in result:
            assert service.read_file(name, "admin")["filename"] == name

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

    def test_read_file_success(self, service: ConfigFilesService, mock_settings: MagicMock) -> None:
        """Should return filename and parsed JSON content."""
        serverdata = mock_settings.serverdata_dir
        content = {"Port": 42420, "ServerName": "Test Server"}
        (serverdata / "serverconfig.json").write_text(json.dumps(content))

        result = service.read_file("serverconfig.json")

        assert result == {"filename": "serverconfig.json", "content": content, "parse_error": None}

    def test_read_file_not_found(self, service: ConfigFilesService) -> None:
        """Should raise ConfigFileNotFoundError for missing files."""
        with pytest.raises(ConfigFileNotFoundError) as exc_info:
            service.read_file("nonexistent.json")

        assert exc_info.value.filename == "nonexistent.json"
        assert "Config file not found" in exc_info.value.message

    def test_read_file_invalid_json_admin_gets_the_text(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Should handle malformed JSON gracefully: Admin gets the text as _raw."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "broken.json").write_text("not valid json {")

        result = service.read_file("broken.json", "admin")

        assert result["filename"] == "broken.json"
        content = result["content"]
        assert isinstance(content, dict)
        assert content["_raw"] == "not valid json {"
        assert "_parse_error" in content

    def test_read_file_invalid_json_redacted_without_a_role(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """Story 17.5: without the Admin role the text of a broken file is withheld."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "broken.json").write_text("not valid json {")

        result = service.read_file("broken.json")

        content = result["content"]
        assert isinstance(content, dict)
        assert content["_raw"] == REDACTED
        assert content["_parse_error"]


def _forbid_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any read of file content fail the test."""

    def fail(self: Path, *args: object, **kwargs: object) -> bytes:
        raise AssertionError(f"{self} was read")

    monkeypatch.setattr(Path, "read_bytes", fail)
    monkeypatch.setattr(Path, "read_text", fail)


ROLES = ["admin", "monitor"]


class TestViewableFiles:
    """Story 19.1 (FR205, FR206): the viewer serves regular .json files that are UTF-8 text."""

    @pytest.mark.parametrize("role", ROLES)
    @pytest.mark.parametrize("name", ["notes.txt", "server-main.log", "x.zip", "noext"])
    @pytest.mark.parametrize("exists", [True, False])
    def test_other_names_are_refused_unread(
        self,
        service: ConfigFilesService,
        mock_settings: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        role: str,
        name: str,
        exists: bool,
    ) -> None:
        """AC 2: a name that does not end in .json is refused before the file is opened."""
        if exists:
            (mock_settings.serverdata_dir / name).write_text('{"a": 1}')
        _forbid_reads(monkeypatch)

        with pytest.raises(ConfigFileNotSupportedError) as exc_info:
            service.read_file(name, role)

        assert exc_info.value.filename == name
        assert exc_info.value.message == (
            f"Only .json files that are UTF-8 text can be viewed: {name}"
        )

    @pytest.mark.parametrize("role", ROLES)
    def test_things_that_are_not_json_files_are_refused(
        self, service: ConfigFilesService, mock_settings: MagicMock, role: str
    ) -> None:
        """AC 3: a directory, a directory named x.json, a symlink to another type, a FIFO."""
        serverdata = mock_settings.serverdata_dir
        (serverdata / "Logs").mkdir()
        (serverdata / "dir.json").mkdir()
        (serverdata / "notes.txt").write_text('{"a": 1}')
        (serverdata / "link.json").symlink_to(serverdata / "notes.txt")
        os.mkfifo(serverdata / "pipe.json")

        for name in ("Logs", "dir.json", "link.json", "pipe.json"):
            with pytest.raises(ConfigFileNotSupportedError):
                service.read_file(name, role)

    @pytest.mark.parametrize("role", ROLES)
    @pytest.mark.parametrize(
        "data", [bytes(range(256)), '{"a": "\u00e9"}'.encode("latin-1")], ids=["bin", "latin"]
    )
    def test_text_that_is_not_utf8_is_refused(
        self, service: ConfigFilesService, mock_settings: MagicMock, role: str, data: bytes
    ) -> None:
        """AC 3: a .json file that is not UTF-8 text is refused, never a 500."""
        (mock_settings.serverdata_dir / "bin.json").write_bytes(data)

        with pytest.raises(ConfigFileNotSupportedError):
            service.read_file("bin.json", role)

    @pytest.mark.parametrize("role", ROLES)
    def test_too_large_is_refused_unread(
        self,
        service: ConfigFilesService,
        mock_settings: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        role: str,
    ) -> None:
        """AC 4: a file larger than 2 MiB is refused before it is read."""
        (mock_settings.serverdata_dir / "big.json").write_bytes(b" " * (CONFIG_FILE_MAX_BYTES + 1))
        _forbid_reads(monkeypatch)

        with pytest.raises(ConfigFileTooLargeError) as exc_info:
            service.read_file("big.json", role)

        assert exc_info.value.filename == "big.json"
        assert exc_info.value.message == (
            "Config file is larger than 2 MiB and cannot be viewed: big.json"
        )

    @pytest.mark.parametrize("role", ROLES)
    def test_exactly_the_limit_is_served(
        self, service: ConfigFilesService, mock_settings: MagicMock, role: str
    ) -> None:
        """AC 4: a file of exactly 2,097,152 bytes is served."""
        text = '"' + "a" * (CONFIG_FILE_MAX_BYTES - 2) + '"'
        (mock_settings.serverdata_dir / "exact.json").write_text(text)

        assert service.read_file("exact.json", role)["content"] == "a" * (CONFIG_FILE_MAX_BYTES - 2)

    @pytest.mark.parametrize("role", ROLES)
    def test_byte_order_mark_is_parsed(
        self, service: ConfigFilesService, mock_settings: MagicMock, role: str
    ) -> None:
        """AC 5: a UTF-8 file with a byte order mark is parsed."""
        (mock_settings.serverdata_dir / "bom.json").write_bytes(b"\xef\xbb\xbf" + b'{"a": 1}')

        assert service.read_file("bom.json", role)["content"] == {"a": 1}

    @pytest.mark.parametrize("role", ROLES)
    def test_upper_case_suffix_is_served_and_listed(
        self, service: ConfigFilesService, mock_settings: MagicMock, role: str
    ) -> None:
        """AC 1: .json is compared without letter case."""
        (mock_settings.serverdata_dir / "X.JSON").write_text('{"a": 1}')

        assert service.read_file("X.JSON", role)["content"] == {"a": 1}
        assert service.list_files() == ["X.JSON"]

    @pytest.mark.parametrize("role", ROLES)
    @pytest.mark.parametrize("opening", ["[", '{"a":'])
    def test_nesting_up_to_the_limit_is_parsed(
        self, service: ConfigFilesService, mock_settings: MagicMock, role: str, opening: str
    ) -> None:
        """AC 5: content nested exactly CONFIG_FILE_MAX_DEPTH levels deep is parsed."""
        closing = "]" if opening == "[" else "}"
        text = opening * CONFIG_FILE_MAX_DEPTH + "1" + closing * CONFIG_FILE_MAX_DEPTH
        (mock_settings.serverdata_dir / "deep.json").write_text(text)

        assert service.read_file("deep.json", role)["content"] == json.loads(text)

    @pytest.mark.parametrize("opening", ["[", '{"a":'])
    @pytest.mark.parametrize("levels", [CONFIG_FILE_MAX_DEPTH + 1, 100_000])
    def test_deeper_nesting_is_raw(
        self, service: ConfigFilesService, mock_settings: MagicMock, opening: str, levels: int
    ) -> None:
        """AC 5: deeper content (and content the parser gives up on) is the _raw form."""
        closing = "]" if opening == "[" else "}"
        text = opening * levels + "1" + closing * levels
        (mock_settings.serverdata_dir / "deep.json").write_text(text)

        admin = service.read_file("deep.json", "admin")["content"]
        monitor = service.read_file("deep.json", "monitor")["content"]

        assert isinstance(admin, dict)
        assert isinstance(monitor, dict)
        assert admin["_raw"] == text
        assert monitor["_raw"] == REDACTED
        assert admin["_parse_error"]
        assert monitor["_parse_error"] == admin["_parse_error"]
        if levels == CONFIG_FILE_MAX_DEPTH + 1:
            assert admin["_parse_error"] == (
                f"Nested more than {CONFIG_FILE_MAX_DEPTH} levels deep"
            )

    @pytest.mark.parametrize("role", ROLES)
    def test_read_error_is_reported_and_logged(
        self,
        service: ConfigFilesService,
        mock_settings: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        role: str,
    ) -> None:
        """ADR-1 decision 8: any other OSError is ConfigFileReadError, logged at error level."""
        (mock_settings.serverdata_dir / "locked.json").write_text("{}")

        def denied(self: Path) -> bytes:
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(Path, "read_bytes", denied)

        with pytest.raises(ConfigFileReadError) as exc_info:
            service.read_file("locked.json", role)

        assert exc_info.value.message == "Config file could not be read: locked.json"
        out = capsys.readouterr().out
        assert "config_file_read_failed" in out
        assert "Permission denied" in out

    @pytest.mark.parametrize("role", ROLES)
    def test_file_removed_while_reading_is_not_found(
        self,
        service: ConfigFilesService,
        mock_settings: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        role: str,
    ) -> None:
        """A file removed between the checks and the read is 404, not a read error."""
        (mock_settings.serverdata_dir / "gone.json").write_text("{}")

        def gone(self: Path) -> bytes:
            raise FileNotFoundError(2, "No such file or directory")

        monkeypatch.setattr(Path, "read_bytes", gone)

        with pytest.raises(ConfigFileNotFoundError):
            service.read_file("gone.json", role)


class TestReadFileSecrets:
    """Story 17.5 (FR186): read_file withholds secrets unless the role is Admin."""

    @pytest.fixture
    def serverconfig(self, mock_settings: MagicMock) -> Path:
        path = mock_settings.serverdata_dir / "serverconfig.json"
        path.write_text(json.dumps({"ServerName": "Test", "Password": SECRET, "Port": 42420}))
        (mock_settings.serverdata_dir / "ModConfig").mkdir()
        return path

    @pytest.mark.parametrize(
        "filename",
        ["serverconfig.json", "./serverconfig.json", "ModConfig/../serverconfig.json"],
    )
    @pytest.mark.parametrize("role", [None, "monitor", "", "ADMIN", "Admin"])
    def test_any_path_to_serverconfig_is_redacted(
        self,
        service: ConfigFilesService,
        serverconfig: Path,
        filename: str,
        role: str | None,
    ) -> None:
        """AC 3, 6: every path to the file, every role but Admin: redacted."""
        result = service.read_file(filename) if role is None else service.read_file(filename, role)

        assert result["content"] == {"ServerName": "Test", "Password": REDACTED, "Port": 42420}
        assert SECRET not in json.dumps(result)

    @pytest.mark.parametrize(
        "filename",
        ["serverconfig.json", "./serverconfig.json", "ModConfig/../serverconfig.json"],
    )
    def test_admin_gets_the_password(
        self, service: ConfigFilesService, serverconfig: Path, filename: str
    ) -> None:
        """AC 5: Admin gets the file as it is."""
        result = service.read_file(filename, "admin")

        assert result["content"] == {"ServerName": "Test", "Password": SECRET, "Port": 42420}

    def test_symlink_to_serverconfig_is_redacted(
        self, service: ConfigFilesService, serverconfig: Path, mock_settings: MagicMock
    ) -> None:
        """AC 3: a symlink that resolves to the file is redacted too."""
        (mock_settings.serverdata_dir / "ModConfig" / "link.json").symlink_to(serverconfig)

        monitor = service.read_file("ModConfig/link.json", "monitor")
        admin = service.read_file("ModConfig/link.json", "admin")

        assert SECRET not in json.dumps(monitor)
        content = monitor["content"]
        assert isinstance(content, dict)
        assert content["Password"] == REDACTED
        admin_content = admin["content"]
        assert isinstance(admin_content, dict)
        assert admin_content["Password"] == SECRET

    @pytest.mark.parametrize("value", [None, ""])
    def test_unset_password_is_unchanged(
        self, service: ConfigFilesService, mock_settings: MagicMock, value: str | None
    ) -> None:
        """AC 3: null and "" are returned as they are."""
        (mock_settings.serverdata_dir / "serverconfig.json").write_text(
            json.dumps({"Password": value})
        )

        assert service.read_file("serverconfig.json")["content"] == {"Password": value}

    def test_broken_serverconfig_is_withheld(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """AC 4: a serverconfig.json that does not parse returns no text to Monitor."""
        # Story 23.1: a trailing comma is JSON5 now; a missing brace still does not parse
        text = '{"Password": "' + SECRET + '", "Port": 1'
        (mock_settings.serverdata_dir / "serverconfig.json").write_text(text)

        monitor = service.read_file("serverconfig.json", "monitor")
        admin = service.read_file("serverconfig.json", "admin")

        assert SECRET not in json.dumps(monitor)
        content = monitor["content"]
        assert isinstance(content, dict)
        assert content["_raw"] == REDACTED
        assert content["_parse_error"]
        admin_content = admin["content"]
        assert isinstance(admin_content, dict)
        assert admin_content["_raw"] == text


class TestRoleDirectories:
    """Story 19.1 (FR208, Epic 19 ADR-3): other roles see the root and ModConfig only."""

    @pytest.fixture
    def data(self, mock_settings: MagicMock) -> Path:
        serverdata: Path = mock_settings.serverdata_dir
        nested = serverdata / "ModConfig" / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "c.json").write_text('{"c": 1}')
        (serverdata / "Playerdata").mkdir()
        (serverdata / "Playerdata" / "p.json").write_text('{"p": 1}')
        (serverdata / "Saves").mkdir()
        (serverdata / ".hidden").mkdir()
        (serverdata / "serverconfig.json").write_text('{"s": 1}')
        return serverdata

    @pytest.mark.parametrize("role", ["monitor", None])
    def test_root_lists_modconfig_only(
        self, service: ConfigFilesService, data: Path, role: str | None
    ) -> None:
        """AC 9: every directory string that resolves to the root lists ModConfig only."""
        assert service.list_directories(role=role) == ["ModConfig"]
        assert service.list_directories(".", role=role) == ["ModConfig"]
        assert service.list_directories("ModConfig/..", role=role) == ["ModConfig"]
        assert service.list_directories("ModConfig", role=role) == ["a"]
        assert service.list_files(role=role) == ["serverconfig.json"]

    @pytest.mark.parametrize("role", ["monitor", None])
    @pytest.mark.parametrize(
        "directory", ["Playerdata", "playerdata", "PLAYERDATA", "Saves", "NoSuchDir"]
    )
    def test_other_directories_are_forbidden(
        self, service: ConfigFilesService, data: Path, role: str | None, directory: str
    ) -> None:
        """AC 10: other directories, in any letter case, existing or not, are forbidden."""
        with pytest.raises(ConfigDirectoryForbiddenError) as exc_info:
            service.list_directories(directory, role=role)
        assert exc_info.value.message == f"This directory needs the Admin role: {directory}"
        with pytest.raises(ConfigDirectoryForbiddenError):
            service.list_files(directory, role=role)

    @pytest.mark.parametrize("role", ["monitor", None])
    @pytest.mark.parametrize(
        "filename", ["Playerdata/p.json", "NoSuchDir/x.json", "Playerdata/x.log"]
    )
    def test_files_in_other_directories_are_forbidden(
        self, service: ConfigFilesService, data: Path, role: str | None, filename: str
    ) -> None:
        """AC 10: a file outside the allowed directories is forbidden, before its suffix."""
        with pytest.raises(ConfigDirectoryForbiddenError) as exc_info:
            service.read_file(filename, role)
        assert exc_info.value.message == f"This directory needs the Admin role: {filename}"

    @pytest.mark.parametrize("role", ["monitor", None])
    def test_root_and_modconfig_files_are_served(
        self, service: ConfigFilesService, data: Path, role: str | None
    ) -> None:
        """AC 11: files in the root and anywhere under ModConfig are served."""
        assert service.read_file("ModConfig/a/b/c.json", role)["content"] == {"c": 1}
        assert service.read_file("serverconfig.json", role)["content"] == {"s": 1}

    @pytest.mark.parametrize("role", ["monitor", None])
    def test_symlinks_out_of_modconfig_are_forbidden(
        self, service: ConfigFilesService, data: Path, role: str | None
    ) -> None:
        """AC 11: symlinks in ModConfig that resolve into Playerdata are neither listed nor read."""
        (data / "ModConfig" / "link.json").symlink_to(data / "Playerdata" / "p.json")
        (data / "ModConfig" / "pd").symlink_to(data / "Playerdata")

        with pytest.raises(ConfigDirectoryForbiddenError):
            service.read_file("ModConfig/link.json", role)
        with pytest.raises(ConfigDirectoryForbiddenError):
            service.read_file("ModConfig/pd/p.json", role)
        with pytest.raises(ConfigDirectoryForbiddenError):
            service.list_files("ModConfig/pd", role=role)
        assert service.list_files("ModConfig", role=role) == []
        assert service.list_directories("ModConfig", role=role) == ["a"]

    @pytest.mark.parametrize("role", ["monitor", None])
    def test_root_symlink_named_modconfig_is_judged_by_its_target(
        self, tmp_path: Path, role: str | None
    ) -> None:
        """ADR against the code 2: the rule is on resolved paths, not on names."""
        serverdata = tmp_path / "other-serverdata"
        (serverdata / "Saves").mkdir(parents=True)
        (serverdata / "Saves" / "x.json").write_text('{"x": 1}')
        (serverdata / "ModConfig").symlink_to(serverdata / "Saves")
        settings = MagicMock()
        settings.serverdata_dir = serverdata
        service = ConfigFilesService(settings=settings)

        assert service.list_directories(role=role) == []
        with pytest.raises(ConfigDirectoryForbiddenError):
            service.read_file("ModConfig/x.json", role)

        # A root symlink under another name that resolves to ModConfig is allowed
        (serverdata / "ModConfig").unlink()
        (serverdata / "ModConfig").mkdir()
        (serverdata / "ModConfig" / "m.json").write_text('{"m": 1}')
        (serverdata / "Alias").symlink_to(serverdata / "ModConfig")

        assert service.list_directories(role=role) == ["Alias", "ModConfig"]
        assert service.read_file("Alias/m.json", role)["content"] == {"m": 1}

    @pytest.mark.parametrize("role", ["monitor", None])
    def test_containment_is_checked_first(
        self, service: ConfigFilesService, data: Path, role: str | None
    ) -> None:
        """AC 11: a path that leaves the data directory is invalid, not forbidden."""
        with pytest.raises(ConfigPathInvalidError):
            service.read_file("../x.json", role)
        with pytest.raises(ConfigPathInvalidError):
            service.list_files("../outside", role=role)

    def test_admin_sees_everything(self, service: ConfigFilesService, data: Path) -> None:
        """AC 9, 10: Admin's listings are unchanged, hidden directories included."""
        assert service.list_directories(role="admin") == [
            ".hidden",
            "ModConfig",
            "Playerdata",
            "Saves",
        ]
        assert service.list_directories("Playerdata", role="admin") == []
        assert service.list_files("Playerdata", role="admin") == ["p.json"]
        assert service.list_files("NoSuchDir", role="admin") == []
        assert service.read_file("Playerdata/p.json", "admin")["content"] == {"p": 1}
        with pytest.raises(ConfigFileNotSupportedError):
            service.read_file("Playerdata/x.log", "admin")


class TestReviewFixes:
    """Story 19.1 review: a NUL byte, a too-long integer, a file that grows."""

    @pytest.mark.parametrize("role", ROLES)
    def test_nul_byte_is_an_invalid_path(self, service: ConfigFilesService, role: str) -> None:
        """M1: a NUL byte in a path is ConfigPathInvalidError for the read and both listings."""
        with pytest.raises(ConfigPathInvalidError):
            service.read_file("foo\x00.json", role)
        with pytest.raises(ConfigPathInvalidError):
            service.list_files("ModConfig\x00", role=role)
        with pytest.raises(ConfigPathInvalidError):
            service.list_directories("ModConfig\x00", role=role)

    def test_integer_too_long_is_raw(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """M2: json.loads' plain ValueError gives the _raw form, no file content in the error."""
        text = '{"n": ' + "1" * 5000 + "}"
        (mock_settings.serverdata_dir / "bigint.json").write_text(text)

        admin = service.read_file("bigint.json", "admin")["content"]
        monitor = service.read_file("bigint.json", "monitor")["content"]

        assert isinstance(admin, dict)
        assert isinstance(monitor, dict)
        assert admin["_raw"] == text
        assert monitor["_raw"] == REDACTED
        assert monitor["_parse_error"] == admin["_parse_error"]
        assert isinstance(admin["_parse_error"], str)
        assert "1" * 50 not in admin["_parse_error"]

    @pytest.mark.parametrize("role", ROLES)
    def test_file_that_grew_is_too_large(
        self,
        service: ConfigFilesService,
        mock_settings: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        role: str,
    ) -> None:
        """L1: the size is checked again on the bytes read."""
        (mock_settings.serverdata_dir / "grows.json").write_text("{}")

        def grown(self: Path) -> bytes:
            return b" " * (CONFIG_FILE_MAX_BYTES + 1)

        monkeypatch.setattr(Path, "read_bytes", grown)

        with pytest.raises(ConfigFileTooLargeError):
            service.read_file("grows.json", role)


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
            service.read_file("....//secrets.json", "admin")

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

        result = service.read_file("subdir/config.json", "admin")

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


@pytest.mark.parametrize("role", ["admin", "monitor", None])
class TestLinksOutsideTheDataDirectory:
    """Story 21.3 AC 11: no listing shows an entry resolving outside (Epic 21 ADR-5 d. 2)."""

    @pytest.fixture
    def linked(self, mock_settings: MagicMock, tmp_path: Path) -> Path:
        serverdata = mock_settings.serverdata_dir
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "x.json").write_text("{}")
        (serverdata / "serverconfig.json").write_text("{}")
        for parent in (serverdata, serverdata / "ModConfig"):
            parent.mkdir(exist_ok=True)
            (parent / "away").symlink_to(outside, target_is_directory=True)
            (parent / "away.json").symlink_to(outside / "x.json")
        (serverdata / "ModConfig" / "real.json").write_text("{}")
        return serverdata

    def test_directory_listings_leave_the_link_out(
        self, service: ConfigFilesService, linked: Path, role: str | None
    ) -> None:
        assert service.list_directories(role=role) == ["ModConfig"]
        assert service.list_directories("ModConfig", role) == []

    def test_file_listings_leave_the_link_out(
        self, service: ConfigFilesService, linked: Path, role: str | None
    ) -> None:
        assert service.list_files(role=role) == ["serverconfig.json"]
        assert service.list_files("ModConfig", role) == ["real.json"]

    def test_admin_still_may_not_open_them(
        self, service: ConfigFilesService, linked: Path, role: str | None
    ) -> None:
        with pytest.raises(ConfigPathInvalidError):
            service.read_file("away/x.json", "admin")
        with pytest.raises(ConfigPathInvalidError):
            service.list_directories("away", "admin")


class TestMissingDataDirectory:
    """Story 21.3 AC 12: the path and role checks run before the existence check (ADR-5 d. 3)."""

    @pytest.fixture(autouse=True)
    def missing(self, mock_settings: MagicMock) -> None:
        mock_settings.serverdata_dir.rmdir()

    @pytest.mark.parametrize("role", ["monitor", None])
    def test_a_forbidden_directory_is_forbidden(
        self, service: ConfigFilesService, role: str | None
    ) -> None:
        with pytest.raises(ConfigDirectoryForbiddenError):
            service.list_directories("Playerdata", role)
        with pytest.raises(ConfigDirectoryForbiddenError):
            service.list_files("Playerdata", role)

    @pytest.mark.parametrize("role", ["monitor", None])
    @pytest.mark.parametrize("directory", [None, "ModConfig"])
    def test_an_allowed_directory_is_empty(
        self, service: ConfigFilesService, role: str | None, directory: str | None
    ) -> None:
        assert service.list_directories(directory, role) == []
        assert service.list_files(directory, role) == []

    @pytest.mark.parametrize("role", ["admin", "monitor", None])
    def test_a_traversal_is_invalid(self, service: ConfigFilesService, role: str | None) -> None:
        with pytest.raises(ConfigPathInvalidError):
            service.list_directories("../x", role)
        with pytest.raises(ConfigPathInvalidError):
            service.list_files("../x", role)

    def test_admin_gets_an_empty_list(self, service: ConfigFilesService) -> None:
        assert service.list_directories("Playerdata", "admin") == []
        assert service.list_files("Playerdata", "admin") == []


# Story 23.1 (Epic 23 ADR-9 decision 4): the shape of ModConfig/seasonalflowers.json
COMMENTED_MOD_CONFIG = """{
  // How often flowers bloom
  "BloomChance": 0.5, /* a block comment */
  "Homepage": "http://example.com//path",
  "password": "pw-in-a-mod-config",
  "Seasons": [null, "spring", null,],
  "Enabled": true, // a comment after the last property
}
"""

PARSED_MOD_CONFIG = {
    "BloomChance": 0.5,
    "Homepage": "http://example.com//path",
    "password": "pw-in-a-mod-config",
    "Seasons": [None, "spring", None],
    "Enabled": True,
}


class TestJson5Read:
    """Story 23.1 (FR309-FR311): JSON5, parse_error, and text/version for Admin."""

    def _write(self, mock_settings: MagicMock, name: str, data: bytes) -> None:
        mod_config = mock_settings.serverdata_dir / "ModConfig"
        mod_config.mkdir(exist_ok=True)
        (mod_config / name).write_bytes(data)

    def test_comments_parse_for_admin(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """AC 1: Admin gets the parsed content, the text with comments and a version."""
        data = COMMENTED_MOD_CONFIG.encode()
        self._write(mock_settings, "flowers.json", data)

        result = service.read_file("ModConfig/flowers.json", "admin")

        assert result == {
            "filename": "ModConfig/flowers.json",
            "content": PARSED_MOD_CONFIG,
            "parse_error": None,
            "text": COMMENTED_MOD_CONFIG,
            "version": hashlib.sha256(data).hexdigest(),
        }

    def test_comments_parse_and_are_redacted_by_key_for_monitor(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """AC 1: Monitor gets the content redacted key by key, no text, no version."""
        self._write(mock_settings, "flowers.json", COMMENTED_MOD_CONFIG.encode())

        result = service.read_file("ModConfig/flowers.json", "monitor")

        assert result == {
            "filename": "ModConfig/flowers.json",
            "content": {**PARSED_MOD_CONFIG, "password": REDACTED},
            "parse_error": None,
        }

    @pytest.mark.parametrize("role", ROLES)
    def test_single_quotes_unquoted_keys_and_hex(
        self, service: ConfigFilesService, mock_settings: MagicMock, role: str
    ) -> None:
        """AC 2."""
        self._write(mock_settings, "loose.json", b"{name: 'x', 'n': 0x1F}")

        assert service.read_file("ModConfig/loose.json", role)["content"] == {"name": "x", "n": 31}

    @pytest.mark.parametrize("role", ROLES)
    @pytest.mark.parametrize("value", ["Infinity", "-Infinity", "NaN"])
    def test_infinity_and_nan_are_a_parse_error(
        self, service: ConfigFilesService, mock_settings: MagicMock, role: str, value: str
    ) -> None:
        """AC 3."""
        text = '{"a": ' + value + "}"
        self._write(mock_settings, "inf.json", text.encode())

        result = service.read_file("ModConfig/inf.json", role)

        assert result["parse_error"] == {
            "message": "Infinity and NaN cannot be shown",
            "line": None,
            "column": None,
        }
        assert result["content"] == {
            "_raw": text if role == "admin" else REDACTED,
            "_parse_error": "Infinity and NaN cannot be shown",
        }

    def test_unparseable_file_for_admin(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """AC 4: the position, the text and the version for Admin."""
        text = '{\n  "a": 1\n  "b": 2\n}\n'
        self._write(mock_settings, "broken.json", text.encode())

        result = service.read_file("ModConfig/broken.json", "admin")

        parse_error = result["parse_error"]
        assert isinstance(parse_error, dict)
        assert parse_error["line"] == 3
        assert parse_error["column"] == 3
        assert result["content"] == {"_raw": text, "_parse_error": parse_error["message"]}
        assert result["text"] == text
        assert result["version"] == hashlib.sha256(text.encode()).hexdigest()

    def test_unparseable_file_for_monitor(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """AC 4: Monitor gets the position, but not the text or a version."""
        text = '{\n  "a": 1\n  "b": 2\n}\n'
        self._write(mock_settings, "broken.json", text.encode())

        admin = service.read_file("ModConfig/broken.json", "admin")
        monitor = service.read_file("ModConfig/broken.json", "monitor")

        admin_content = admin["content"]
        assert isinstance(admin_content, dict)
        assert monitor["parse_error"] == admin["parse_error"]
        assert monitor["content"] == {
            "_raw": REDACTED,
            "_parse_error": admin_content["_parse_error"],
        }
        assert "text" not in monitor
        assert "version" not in monitor

    def test_byte_order_mark_is_not_in_the_text_but_in_the_version(
        self, service: ConfigFilesService, mock_settings: MagicMock
    ) -> None:
        """AC 5: the text drops the BOM; the version hashes the bytes as read."""
        data = b"\xef\xbb\xbf" + b'{"a": 1} // note\n'
        self._write(mock_settings, "bom.json", data)

        result = service.read_file("ModConfig/bom.json", "admin")

        assert result["text"] == '{"a": 1} // note\n'
        assert result["version"] == hashlib.sha256(data).hexdigest()
        assert result["parse_error"] is None
