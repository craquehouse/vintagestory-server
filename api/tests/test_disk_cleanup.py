"""Tests for DiskCleanupService (Story 22.4, Epic 22 ADR-9 as amended 2026-11-19).

The cleanup handles `serverdata/Backups/` only: the maintainer dropped the log-archive
cleanup because the game keeps at most 5 archives itself, so nothing under `Logs/` is read
or deleted. Every test builds its own `serverdata` under `tmp_path` and sets the
modification time of every backup file explicitly. Links point at directories inside
`tmp_path` but outside the test's `serverdata`.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, MutableMapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from structlog.testing import capture_logs

from vintagestory_api.services import disk_cleanup as disk_cleanup_module
from vintagestory_api.services.disk_cleanup import (
    BACKUP_DIR,
    CleanupLimits,
    CleanupResult,
    DiskCleanupService,
)

NOW = datetime(2026, 11, 18, 12, 0, 0)

Logs = list[MutableMapping[str, Any]]


def _set_mtime(path: Path, when: datetime) -> None:
    stamp = when.timestamp()
    os.utime(path, (stamp, stamp), follow_symlinks=False)


def make_backup(serverdata: Path, name: str, mtime: datetime, content: bytes = b"backup") -> Path:
    path = serverdata / BACKUP_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    _set_mtime(path, mtime)
    return path


def _backups(serverdata: Path) -> list[str]:
    return sorted(entry.name for entry in (serverdata / BACKUP_DIR).iterdir())


def _events(logs: Logs, event: str) -> Logs:
    return [log for log in logs if log["event"] == event]


def _finished(logs: Logs) -> MutableMapping[str, Any]:
    finished = _events(logs, "disk_cleanup_finished")
    assert len(finished) == 1
    return finished[0]


def _assert_no_absolute_path(logs: Logs, tmp_path: Path) -> None:
    for log in logs:
        for value in log.values():
            assert str(tmp_path) not in str(value)
            assert str(tmp_path.resolve()) not in str(value)


def _real_scan(directory: Path) -> list[os.DirEntry[str]]:
    with os.scandir(directory) as entries:
        return list(entries)


def _snapshot(root: Path) -> dict[str, bytes | None]:
    """Relative path -> bytes for files, None for directories, the target for links."""
    tree: dict[str, bytes | None] = {}
    for directory, dir_names, file_names in os.walk(root, followlinks=False):
        for name in [*dir_names, *file_names]:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                tree[relative] = os.readlink(path).encode()
            elif path.is_dir():
                tree[relative] = None
            else:
                tree[relative] = path.read_bytes()
    return tree


@pytest.fixture
def serverdata(tmp_path: Path) -> Path:
    path = tmp_path / "data" / "serverdata"
    path.mkdir(parents=True)
    return path


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    """A directory inside tmp_path but outside serverdata, with a file in it."""
    path = tmp_path / "outside"
    path.mkdir()
    (path / "keep-me.txt").write_bytes(b"outside")
    return path


@pytest.fixture
def service(serverdata: Path) -> DiskCleanupService:
    return DiskCleanupService(serverdata)


@pytest.fixture
def logs() -> Iterator[Logs]:
    with capture_logs() as captured:
        yield captured


class TestBackups:
    """AC 6: the newest backup files are kept; directories and links are never deleted."""

    @pytest.fixture
    def backups(self, serverdata: Path, outside: Path) -> list[str]:
        names = [f"backup-{day}.vcdbs" for day in range(1, 9)]
        for day, name in enumerate(names, start=1):
            make_backup(serverdata, name, NOW - timedelta(days=day), content=b"b" * day)
        directory = serverdata / BACKUP_DIR / "a-directory"
        directory.mkdir()
        _set_mtime(directory, NOW - timedelta(days=100))
        link = serverdata / BACKUP_DIR / "linked.vcdbs"
        link.symlink_to(outside / "keep-me.txt")
        _set_mtime(link, NOW - timedelta(days=100))
        return names

    def test_keep_three(
        self,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        backups: list[str],
        logs: Logs,
        tmp_path: Path,
    ) -> None:
        result = service.run(CleanupLimits(backup_keep_count=3))

        assert _backups(serverdata) == sorted([*backups[:3], "a-directory", "linked.vcdbs"])
        assert (outside / "keep-me.txt").read_bytes() == b"outside"
        assert result == CleanupResult(backups_deleted=5, backup_bytes=sum(range(4, 9)))
        lines = _events(logs, "disk_cleanup_deleted")
        assert [(line["kind"], line["path"], line["bytes"]) for line in lines] == [
            ("backup", f"Backups/backup-{day}.vcdbs", day) for day in range(4, 9)
        ]
        assert all(line["log_level"] == "info" for line in lines)
        skipped = {line["path"]: line for line in _events(logs, "disk_cleanup_skipped")}
        assert skipped["Backups/linked.vcdbs"]["reason"] == "symlink"
        assert skipped["Backups/linked.vcdbs"]["log_level"] == "warning"
        assert skipped["Backups/a-directory"]["reason"] == "not_a_file"
        assert skipped["Backups/a-directory"]["log_level"] == "debug"
        finished = _finished(logs)
        assert finished["log_level"] == "info"
        assert finished["backups_deleted"] == 5
        assert finished["backup_bytes"] == sum(range(4, 9))
        assert finished["backups_kept"] == 3
        assert finished["errors"] == 0
        assert finished["backup_keep_count"] == 3
        _assert_no_absolute_path(logs, tmp_path)

    def test_ties_are_ordered_by_name(self, serverdata: Path, service: DiskCleanupService) -> None:
        for name in ("a.vcdbs", "b.vcdbs", "c.vcdbs"):
            make_backup(serverdata, name, NOW - timedelta(days=1))

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert _backups(serverdata) == ["c.vcdbs"]
        assert result.backups_deleted == 2

    def test_keep_zero_does_not_list_backups(
        self,
        serverdata: Path,
        service: DiskCleanupService,
        backups: list[str],
        logs: Logs,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        scanned: list[Path] = []

        def recording_scan(directory: Path) -> list[os.DirEntry[str]]:
            scanned.append(directory)
            return _real_scan(directory)

        monkeypatch.setattr(disk_cleanup_module, "_scan", recording_scan)

        result = service.run(CleanupLimits(backup_keep_count=0))

        assert _backups(serverdata) == sorted([*backups, "a-directory", "linked.vcdbs"])
        assert result == CleanupResult()
        assert scanned == []
        finished = _finished(logs)
        assert finished["backups_deleted"] == 0
        assert finished["backups_kept"] == 0
        assert finished["backup_keep_count"] == 0


def _old_archives_in(directory: Path) -> None:
    for day in (100, 101, 102):
        when = NOW - timedelta(days=day)
        archive = directory / when.strftime("%Y-%m-%d_%H_%M_%S")
        archive.mkdir(parents=True)
        (archive / "server-main.log").write_bytes(b"archived log")
        _set_mtime(archive, when)


class TestNeverDeleted:
    """AC 7 (amended): everything outside Backups/ is left alone, Logs/ included."""

    def test_full_tree_unchanged(
        self, tmp_path: Path, serverdata: Path, service: DiskCleanupService
    ) -> None:
        files = [
            "BackupSaves/x",
            "Saves/default.vcdbs",
            "Mods/m.zip",
            "ModConfig/c.json",
            "Playerdata/p.json",
            "Logs/server-main.log",
            "Logs/server-audit.log",
            "Logs/server-build.log",
            "Logs/server-chat.log",
            "Logs/server-debug.log",
            "Logs/server-worldgen.log",
            "serverconfig.json",
        ]
        old = NOW - timedelta(days=100)
        for relative in files:
            path = serverdata / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(relative.encode())
            _set_mtime(path, old)
        _old_archives_in(serverdata / "Logs" / "Archive")
        (serverdata / BACKUP_DIR).mkdir()
        state = tmp_path / "data" / "vsmanager" / "state" / "api-settings.json"
        state.parent.mkdir(parents=True)
        state.write_bytes(b"{}")
        _set_mtime(state, old)
        before = _snapshot(tmp_path)

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert _snapshot(tmp_path) == before
        assert result == CleanupResult()

    def test_logs_are_never_read(
        self,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        logs: Logs,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The game keeps its own archives (maintainer's decision, 2026-11-19)."""
        _old_archives_in(serverdata / "Logs" / "Archive")
        (serverdata / "Logs" / "Archive" / "2026-10-01_03_00_00").symlink_to(
            outside, target_is_directory=True
        )
        make_backup(serverdata, "new.vcdbs", NOW - timedelta(days=1))
        make_backup(serverdata, "old.vcdbs", NOW - timedelta(days=2))
        scanned: list[Path] = []

        def recording_scan(directory: Path) -> list[os.DirEntry[str]]:
            scanned.append(directory)
            return _real_scan(directory)

        monkeypatch.setattr(disk_cleanup_module, "_scan", recording_scan)

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert scanned == [serverdata / BACKUP_DIR]
        assert result.backups_deleted == 1
        assert len(list((serverdata / "Logs" / "Archive").iterdir())) == 4
        assert _events(logs, "disk_cleanup_skipped") == []
        assert all("Logs" not in str(log.get("path", "")) for log in logs)

    def test_logs_dir_link_is_not_followed(
        self,
        tmp_path: Path,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        logs: Logs,
    ) -> None:
        _old_archives_in(outside / "Archive")
        (serverdata / "Logs").symlink_to(outside, target_is_directory=True)
        before = _snapshot(tmp_path)

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert _snapshot(tmp_path) == before
        assert result == CleanupResult()
        assert _events(logs, "disk_cleanup_skipped") == []

    def test_backup_dir_is_a_link(
        self,
        tmp_path: Path,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        logs: Logs,
    ) -> None:
        for day in range(1, 6):
            path = outside / f"backup-{day}.vcdbs"
            path.write_bytes(b"outside backup")
            _set_mtime(path, NOW - timedelta(days=day))
        (serverdata / BACKUP_DIR).symlink_to(outside, target_is_directory=True)
        before = _snapshot(tmp_path)

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert _snapshot(tmp_path) == before
        assert result == CleanupResult()
        skipped = _events(logs, "disk_cleanup_skipped")
        assert [(line["path"], line["reason"], line["log_level"]) for line in skipped] == [
            ("Backups", "symlink", "warning")
        ]


def _failing_for(name: str) -> Callable[[Path], None]:
    def delete(path: Path) -> None:
        if path.name == name:
            raise PermissionError(13, "Permission denied", str(path))
        path.unlink()

    return delete


class TestErrors:
    """AC 8: a failure is logged and counted; the other entries are still handled."""

    def test_backup_delete_fails(
        self,
        serverdata: Path,
        service: DiskCleanupService,
        logs: Logs,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for day in range(1, 5):
            make_backup(serverdata, f"backup-{day}.vcdbs", NOW - timedelta(days=day))
        monkeypatch.setattr(disk_cleanup_module, "_delete_file", _failing_for("backup-3.vcdbs"))

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert _backups(serverdata) == ["backup-1.vcdbs", "backup-3.vcdbs"]
        assert result == CleanupResult(backups_deleted=2, backup_bytes=12, errors=1)
        failed = _events(logs, "disk_cleanup_delete_failed")
        assert [
            (line["kind"], line["path"], line["error"], line["errno"], line["log_level"])
            for line in failed
        ] == [("backup", "Backups/backup-3.vcdbs", "Permission denied", 13, "warning")]
        finished = _finished(logs)
        assert finished["backups_deleted"] == 2
        assert finished["backups_kept"] == 2
        assert finished["errors"] == 1
        _assert_no_absolute_path(logs, tmp_path)

    def test_listing_fails(
        self,
        serverdata: Path,
        service: DiskCleanupService,
        logs: Logs,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for day in (1, 2):
            make_backup(serverdata, f"backup-{day}.vcdbs", NOW - timedelta(days=day))

        def failing_scan(directory: Path) -> list[os.DirEntry[str]]:
            raise PermissionError(13, "Permission denied", str(directory))

        monkeypatch.setattr(disk_cleanup_module, "_scan", failing_scan)

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert len(_backups(serverdata)) == 2
        assert result == CleanupResult(errors=1)
        failed = _events(logs, "disk_cleanup_delete_failed")
        assert [(line["kind"], line["path"], line["log_level"]) for line in failed] == [
            ("backup", "Backups", "warning")
        ]
        assert _finished(logs)["errors"] == 1
        _assert_no_absolute_path(logs, tmp_path)

    def test_mtime_read_fails_keeps_the_file(
        self,
        serverdata: Path,
        service: DiskCleanupService,
        logs: Logs,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for day in (1, 2, 3):
            make_backup(serverdata, f"backup-{day}.vcdbs", NOW - timedelta(days=day))

        def scan_then_remove(directory: Path) -> list[os.DirEntry[str]]:
            entries = _real_scan(directory)
            # Gone before its modification time is read: lstat raises FileNotFoundError.
            (directory / "backup-3.vcdbs").unlink()
            return entries

        monkeypatch.setattr(disk_cleanup_module, "_scan", scan_then_remove)

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert _backups(serverdata) == ["backup-1.vcdbs"]
        assert result.backups_deleted == 1
        assert result.errors == 1
        failed = _events(logs, "disk_cleanup_delete_failed")
        assert [(line["path"], line["errno"]) for line in failed] == [("Backups/backup-3.vcdbs", 2)]

    @pytest.mark.parametrize("layout", ["no_serverdata", "empty_serverdata"])
    def test_missing_directories(
        self, tmp_path: Path, serverdata: Path, logs: Logs, layout: str
    ) -> None:
        root = tmp_path / "missing" / "serverdata" if layout == "no_serverdata" else serverdata
        service = DiskCleanupService(root)

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert result == CleanupResult()
        missing = _events(logs, "disk_cleanup_dir_missing")
        assert [(line["path"], line["log_level"]) for line in missing] == [("Backups", "debug")]
        assert _finished(logs)["errors"] == 0


class TestPathCheck:
    """A file replaced by a link between the listing and the deletion is not deleted."""

    def test_backup_replaced_by_a_link(
        self,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        logs: Logs,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for day in range(1, 4):
            make_backup(serverdata, f"backup-{day}.vcdbs", NOW - timedelta(days=day))

        def scan_then_swap(directory: Path) -> list[os.DirEntry[str]]:
            entries = _real_scan(directory)
            swapped = directory / "backup-2.vcdbs"
            swapped.unlink()
            swapped.symlink_to(outside / "keep-me.txt")
            # The order is read with lstat after the scan: the link's own time is set old.
            _set_mtime(swapped, NOW - timedelta(days=2))
            return entries

        monkeypatch.setattr(disk_cleanup_module, "_scan", scan_then_swap)

        result = service.run(CleanupLimits(backup_keep_count=1))

        assert _backups(serverdata) == ["backup-1.vcdbs", "backup-2.vcdbs"]
        assert (serverdata / BACKUP_DIR / "backup-2.vcdbs").is_symlink()
        assert (outside / "keep-me.txt").read_bytes() == b"outside"
        assert result.backups_deleted == 1
        outside_lines = [
            line for line in _events(logs, "disk_cleanup_skipped") if line["reason"] == "outside"
        ]
        assert [(line["path"], line["log_level"]) for line in outside_lines] == [
            ("Backups/backup-2.vcdbs", "warning")
        ]
        _assert_no_absolute_path(logs, tmp_path)
