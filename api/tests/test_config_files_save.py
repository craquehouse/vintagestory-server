"""Tests for ConfigFilesService.save_file and check_text.

Story 23.4: Config Files Can Be Saved Through the API (FR314, FR316, FR317;
Epic 23 ADR-1 decision 5, ADR-4 decisions 2, 3, 5, 6 and 10)
"""

import hashlib
import os
import stat
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vintagestory_api.services.config_files import (
    CONFIG_FILE_MAX_BYTES,
    ConfigFileChangedError,
    ConfigFileInvalidError,
    ConfigFileNotFoundError,
    ConfigFileNotSupportedError,
    ConfigFilesService,
    ConfigFileTooLargeError,
    ConfigFileWriteError,
    ConfigPathInvalidError,
    content_version,
)
from vintagestory_api.services.config_history import ConfigHistory, ConfigHistoryWriteError

BOM = b"\xef\xbb\xbf"
NEW_TEXT = '{\n    // keep this comment\n  "a" :  2,   "b": [1,2,],\n}\n'


@pytest.fixture
def serverdata(tmp_path: Path) -> Path:
    path = tmp_path / "serverdata"
    (path / "ModConfig").mkdir(parents=True)
    return path


@pytest.fixture
def history_root(tmp_path: Path) -> Path:
    return tmp_path / "state" / "config-history"


@pytest.fixture
def limits() -> list[tuple[int, int]]:
    """The history limits the service reads at each save; a test may replace the value."""
    return [(20, 0)]


@pytest.fixture
def service(
    serverdata: Path, history_root: Path, limits: list[tuple[int, int]]
) -> ConfigFilesService:
    settings = MagicMock()
    settings.serverdata_dir = serverdata
    return ConfigFilesService(
        settings=settings,
        history=ConfigHistory(history_root),
        history_limits=lambda: limits[0],
    )


def _write(path: Path, data: bytes) -> str:
    path.write_bytes(data)
    return content_version(data)


def _leftovers(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir() if p.name.endswith(".tmp"))


class TestSave:
    def test_text_is_written_exactly(self, service: ConfigFilesService, serverdata: Path) -> None:
        """AC 1: the text as sent; the new version is the SHA-256 of the file now."""
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b'{"a": 1}')
        os.chmod(path, 0o640)

        saved = service.save_file("ModConfig/x.json", NEW_TEXT, version)

        assert path.read_bytes() == NEW_TEXT.encode()
        assert saved.filename == "ModConfig/x.json"
        assert saved.version == hashlib.sha256(NEW_TEXT.encode()).hexdigest()
        assert saved.previous_bytes == b'{"a": 1}'
        assert saved.value == {"a": 2, "b": [1, 2]}
        assert not saved.is_root_serverconfig
        assert stat.S_IMODE(path.stat().st_mode) == 0o640
        assert _leftovers(path.parent) == []

    def test_byte_order_mark_is_kept(self, service: ConfigFilesService, serverdata: Path) -> None:
        path = serverdata / "ModConfig" / "bom.json"
        version = _write(path, BOM + b'{"a": 1}')

        saved = service.save_file("ModConfig/bom.json", '{"a": 2}', version)

        assert path.read_bytes() == BOM + b'{"a": 2}'
        assert saved.version == content_version(BOM + b'{"a": 2}')

    @pytest.mark.parametrize(
        ("filename", "error"),
        [
            ("../outside.json", ConfigPathInvalidError),
            ("ModConfig/x.txt", ConfigFileNotSupportedError),
            ("ModConfig/missing.json", ConfigFileNotFoundError),
            ("ModConfig/dir.json", ConfigFileNotSupportedError),
        ],
    )
    def test_refusals_write_nothing(
        self,
        service: ConfigFilesService,
        serverdata: Path,
        filename: str,
        error: type[Exception],
    ) -> None:
        """AC 2."""
        (serverdata / "ModConfig" / "x.txt").write_text("{}")
        (serverdata / "ModConfig" / "dir.json").mkdir()
        before = sorted(p.name for p in (serverdata / "ModConfig").iterdir())

        with pytest.raises(error):
            service.save_file(filename, "{}", content_version(b"{}"))

        assert sorted(p.name for p in (serverdata / "ModConfig").iterdir()) == before
        assert (serverdata / "ModConfig" / "x.txt").read_text() == "{}"

    def test_too_large(self, service: ConfigFilesService, serverdata: Path) -> None:
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b"{}")
        text = '"' + "a" * CONFIG_FILE_MAX_BYTES + '"'

        with pytest.raises(ConfigFileTooLargeError):
            service.save_file("ModConfig/x.json", text, version)

        assert path.read_bytes() == b"{}"

    @pytest.mark.parametrize("text", ['{\n  "a": 1\n  "b": 2\n}', '{"a": Infinity}'])
    def test_invalid_text(self, service: ConfigFilesService, serverdata: Path, text: str) -> None:
        """AC 3."""
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b"{}")

        with pytest.raises(ConfigFileInvalidError) as exc_info:
            service.save_file("ModConfig/x.json", text, version)

        assert exc_info.value.info.message
        assert path.read_bytes() == b"{}"

    def test_invalid_text_has_a_position(
        self, service: ConfigFilesService, serverdata: Path
    ) -> None:
        version = _write(serverdata / "ModConfig" / "x.json", b"{}")

        with pytest.raises(ConfigFileInvalidError) as exc_info:
            service.save_file("ModConfig/x.json", '{\n  "a": 1\n  "b": 2\n}', version)

        assert (exc_info.value.info.line, exc_info.value.info.column) == (3, 3)

    @pytest.mark.parametrize("text", ['{\n  // c\n  "Port": 1\n}', '{"Port": 1,}'])
    def test_root_serverconfig_must_be_strict_json(
        self, service: ConfigFilesService, serverdata: Path, text: str
    ) -> None:
        """AC 3 (ADR-1 decision 5)."""
        path = serverdata / "serverconfig.json"
        version = _write(path, b'{"Port": 42420}')

        with pytest.raises(ConfigFileInvalidError):
            service.save_file("serverconfig.json", text, version)

        assert path.read_bytes() == b'{"Port": 42420}'

    def test_root_serverconfig_saves_strict_json(
        self, service: ConfigFilesService, serverdata: Path
    ) -> None:
        version = _write(serverdata / "serverconfig.json", b'{"Port": 42420}')

        saved = service.save_file("serverconfig.json", '{"Port": 42421}', version)

        assert saved.is_root_serverconfig
        assert saved.value == {"Port": 42421}

    def test_a_serverconfig_elsewhere_is_json5(
        self, service: ConfigFilesService, serverdata: Path
    ) -> None:
        path = serverdata / "ModConfig" / "serverconfig.json"
        version = _write(path, b"{}")

        saved = service.save_file("ModConfig/serverconfig.json", "{// c\n}", version)

        assert not saved.is_root_serverconfig
        assert path.read_text() == "{// c\n}"

    def test_stale_version(self, service: ConfigFilesService, serverdata: Path) -> None:
        """AC 6."""
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b'{"a": 1}')
        path.write_bytes(b'{"a": 9}')

        with pytest.raises(ConfigFileChangedError):
            service.save_file("ModConfig/x.json", '{"a": 2}', version)

        assert path.read_bytes() == b'{"a": 9}'

    def test_lone_surrogate_is_invalid(self, service: ConfigFilesService, serverdata: Path) -> None:
        version = _write(serverdata / "ModConfig" / "x.json", b"{}")

        with pytest.raises(ConfigFileInvalidError) as exc_info:
            service.save_file("ModConfig/x.json", '{"a": "\ud800"}', version)

        assert exc_info.value.info.message == "The text is not valid UTF-8"

    @pytest.mark.parametrize("failing", ["replace", "open"])
    def test_write_failure_leaves_the_file_and_no_temp(
        self,
        service: ConfigFilesService,
        serverdata: Path,
        monkeypatch: pytest.MonkeyPatch,
        failing: str,
    ) -> None:
        """AC 7."""
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b'{"a": 1}')

        real = getattr(os, failing)

        def fail(*args: object, **kwargs: object) -> object:
            # Only the config file's own write fails; the history's writes go through
            target = args[1] if failing == "replace" else args[0]
            if Path(str(target)).parent == path.parent:
                raise PermissionError(13, "Permission denied", str(path))
            return real(*args, **kwargs)

        monkeypatch.setattr(os, failing, fail)

        with pytest.raises(ConfigFileWriteError) as exc_info:
            service.save_file("ModConfig/x.json", '{"a": 2}', version)

        monkeypatch.undo()
        assert path.read_bytes() == b'{"a": 1}'
        assert _leftovers(path.parent) == []
        assert str(serverdata) not in exc_info.value.message


class TestCheckText:
    def test_valid(self, service: ConfigFilesService) -> None:
        assert service.check_text("ModConfig/new.json", "{// c\n a: 1,}") is None

    def test_invalid_has_a_position(self, service: ConfigFilesService) -> None:
        info = service.check_text("ModConfig/x.json", '{\n  "a": 1\n  "b": 2\n}')

        assert info is not None
        assert (info.line, info.column) == (3, 3)

    def test_root_serverconfig_is_strict(self, service: ConfigFilesService) -> None:
        assert service.check_text("serverconfig.json", '{"a": 1,}') is not None
        assert service.check_text("serverconfig.json", '{"a": 1}') is None

    def test_traversal_is_refused(self, service: ConfigFilesService) -> None:
        with pytest.raises(ConfigPathInvalidError):
            service.check_text("../x.json", "{}")

    def test_non_json_name_is_refused(self, service: ConfigFilesService) -> None:
        with pytest.raises(ConfigFileNotSupportedError):
            service.check_text("ModConfig/x.txt", "{}")

    def test_writes_nothing(self, service: ConfigFilesService, serverdata: Path) -> None:
        service.check_text("ModConfig/new.json", "{}")

        assert not (serverdata / "ModConfig" / "new.json").exists()

    def test_too_large(self, service: ConfigFilesService) -> None:
        with pytest.raises(ConfigFileTooLargeError):
            service.check_text("ModConfig/x.json", " " * (CONFIG_FILE_MAX_BYTES + 1))


class TestHistory:
    """Story 23.6 (FR321, FR322, Epic 23 ADR-7 decisions 3 to 5)."""

    def test_a_save_keeps_the_text_it_replaced(
        self, service: ConfigFilesService, serverdata: Path, history_root: Path
    ) -> None:
        version = _write(serverdata / "ModConfig" / "x.json", BOM + b'{"a": 1}')

        service.save_file("ModConfig/x.json", '{"a": 2}', version)

        history = ConfigHistory(history_root)
        revisions = history.list("ModConfig/x.json")
        assert [r.saved_by for r in revisions] == ["admin"]
        assert history.read("ModConfig/x.json", revisions[0].id)[1] == BOM + b'{"a": 1}'

    def test_a_history_failure_refuses_the_save(
        self, service: ConfigFilesService, serverdata: Path, history_root: Path
    ) -> None:
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b'{"a": 1}')
        history_root.parent.mkdir(parents=True)
        history_root.write_text("not a directory")

        with pytest.raises(ConfigHistoryWriteError):
            service.save_file("ModConfig/x.json", '{"a": 2}', version)

        assert path.read_bytes() == b'{"a": 1}'

    def test_a_failed_replace_removes_the_revision(
        self,
        service: ConfigFilesService,
        serverdata: Path,
        history_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b'{"a": 1}')
        real_replace = os.replace

        def fail_for_the_config(src: object, dst: object) -> None:
            if Path(str(dst)) == path.resolve():
                raise PermissionError(13, "Permission denied")
            real_replace(str(src), str(dst))

        monkeypatch.setattr(os, "replace", fail_for_the_config)

        with pytest.raises(ConfigFileWriteError):
            service.save_file("ModConfig/x.json", '{"a": 2}', version)

        monkeypatch.undo()
        assert ConfigHistory(history_root).list("ModConfig/x.json") == []
        assert path.read_bytes() == b'{"a": 1}'

    def test_a_save_prunes_with_the_limits(
        self,
        service: ConfigFilesService,
        serverdata: Path,
        history_root: Path,
        limits: list[tuple[int, int]],
    ) -> None:
        path = serverdata / "ModConfig" / "x.json"
        limits[0] = (2, 0)
        for value in range(4):
            version = content_version(path.read_bytes()) if path.exists() else _write(path, b"{}")
            service.save_file("ModConfig/x.json", f'{{"a": {value}}}', version)

        assert len(ConfigHistory(history_root).list("ModConfig/x.json")) == 2

    def test_a_prune_failure_does_not_fail_the_save(
        self, serverdata: Path, history_root: Path
    ) -> None:
        settings = MagicMock()
        settings.serverdata_dir = serverdata

        def broken() -> tuple[int, int]:
            raise RuntimeError("settings unreadable")

        service = ConfigFilesService(
            settings=settings, history=ConfigHistory(history_root), history_limits=broken
        )
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b"{}")

        service.save_file("ModConfig/x.json", '{"a": 1}', version)

        assert path.read_text() == '{"a": 1}'

    def test_restore_saves_the_revision_and_keeps_the_current_text(
        self, service: ConfigFilesService, serverdata: Path, history_root: Path
    ) -> None:
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b'{"a": 1}')
        saved = service.save_file("ModConfig/x.json", '{"a": 2}', version)
        old = ConfigHistory(history_root).list("ModConfig/x.json")[0]

        restored = service.restore_revision("ModConfig/x.json", old.id, saved.version)

        assert path.read_bytes() == b'{"a": 1}'
        assert restored.version == content_version(b'{"a": 1}')
        revisions = ConfigHistory(history_root).list("ModConfig/x.json")
        assert len(revisions) == 2
        assert ConfigHistory(history_root).read("ModConfig/x.json", revisions[0].id)[1] == (
            b'{"a": 2}'
        )

    def test_restore_follows_the_version_check(
        self, service: ConfigFilesService, serverdata: Path, history_root: Path
    ) -> None:
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b'{"a": 1}')
        service.save_file("ModConfig/x.json", '{"a": 2}', version)
        old = ConfigHistory(history_root).list("ModConfig/x.json")[0]

        with pytest.raises(ConfigFileChangedError):
            service.restore_revision("ModConfig/x.json", old.id, version)

    def test_a_revision_that_does_not_parse_cannot_be_restored(
        self, service: ConfigFilesService, serverdata: Path, history_root: Path
    ) -> None:
        path = serverdata / "ModConfig" / "x.json"
        version = _write(path, b"{ broken")
        saved = service.save_file("ModConfig/x.json", "{}", version)
        old = ConfigHistory(history_root).list("ModConfig/x.json")[0]

        with pytest.raises(ConfigFileInvalidError):
            service.restore_revision("ModConfig/x.json", old.id, saved.version)
