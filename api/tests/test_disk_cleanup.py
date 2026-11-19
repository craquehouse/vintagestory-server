"""Tests for DiskCleanupService (Story 22.4, Epic 22 ADR-9).

Every test builds its own `serverdata` under `tmp_path`, uses a fixed clock and sets the
modification time of every archive directory and backup file explicitly: an archive left
at the wall clock's time would never look old (controller decision 2). Links point at
directories inside `tmp_path` but outside the test's `serverdata`.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Iterator, MutableMapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from structlog.testing import capture_logs

from vintagestory_api.services import disk_cleanup as disk_cleanup_module
from vintagestory_api.services.disk_cleanup import (
    ARCHIVE_DIR,
    BACKUP_DIR,
    CleanupLimits,
    CleanupResult,
    DiskCleanupService,
)

NOW = datetime(2026, 11, 18, 12, 0, 0)
NAME_FORMAT = "%Y-%m-%d_%H_%M_%S"
DEFAULTS = CleanupLimits(log_archive_retention_days=14, log_archive_keep_min=5, backup_keep_count=0)
DEFAULT_FILES = {"server-main.log": b"main log\n", "server-debug.log": b"debug log lines\n"}
DEFAULT_ARCHIVE_BYTES = sum(len(content) for content in DEFAULT_FILES.values())

Logs = list[MutableMapping[str, Any]]


def _name(when: datetime) -> str:
    return when.strftime(NAME_FORMAT)


def _set_mtime(path: Path, when: datetime) -> None:
    stamp = when.timestamp()
    os.utime(path, (stamp, stamp), follow_symlinks=False)


def make_archive(
    serverdata: Path,
    name: str,
    files: dict[str, bytes] | None = None,
    mtime: datetime | None = None,
) -> Path:
    """An archive directory; its modification time is the time in its name by default."""
    directory = serverdata / ARCHIVE_DIR / name
    directory.mkdir(parents=True)
    for file_name, content in (DEFAULT_FILES if files is None else files).items():
        (directory / file_name).write_bytes(content)
    # Last: writing the files changes the directory's modification time.
    _set_mtime(directory, mtime if mtime is not None else datetime.strptime(name, NAME_FORMAT))
    return directory


def make_backup(serverdata: Path, name: str, mtime: datetime, content: bytes = b"backup") -> Path:
    path = serverdata / BACKUP_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    _set_mtime(path, mtime)
    return path


def _archives(serverdata: Path) -> list[str]:
    return sorted(entry.name for entry in (serverdata / ARCHIVE_DIR).iterdir())


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


def _limits(days: int, keep: int, backups: int) -> CleanupLimits:
    return CleanupLimits(
        log_archive_retention_days=days, log_archive_keep_min=keep, backup_keep_count=backups
    )


def _real_scan(directory: Path) -> list[os.DirEntry[str]]:
    with os.scandir(directory) as entries:
        return list(entries)


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
    return DiskCleanupService(serverdata, now=lambda: NOW)


@pytest.fixture
def logs() -> Iterator[Logs]:
    with capture_logs() as captured:
        yield captured


class TestDailyArchives:
    """AC 1: the 20 daily archives with the default limits."""

    def test_deletes_the_six_oldest(
        self, serverdata: Path, service: DiskCleanupService, logs: Logs, tmp_path: Path
    ) -> None:
        names = [_name(datetime(2026, 11, 18, 3) - timedelta(days=day)) for day in range(20)]
        for index, name in enumerate(names):
            make_archive(serverdata, name, files={"server-main.log": b"x" * (index + 1)})

        result = service.run(DEFAULTS)

        deleted = names[14:]
        assert deleted[0] == "2026-11-04_03_00_00"
        assert deleted[-1] == "2026-10-30_03_00_00"
        assert _archives(serverdata) == sorted(names[:14])
        expected_bytes = sum(range(15, 21))
        assert result == CleanupResult(
            archives_deleted=6, archive_bytes=expected_bytes, backups_deleted=0, backup_bytes=0
        )
        lines = _events(logs, "disk_cleanup_deleted")
        assert [(line["kind"], line["path"], line["bytes"]) for line in lines] == [
            ("log_archive", f"Logs/Archive/{name}", names.index(name) + 1) for name in deleted
        ]
        assert all(line["log_level"] == "info" for line in lines)
        finished = _finished(logs)
        assert finished["log_level"] == "info"
        assert finished["archives_deleted"] == 6
        assert finished["archive_bytes"] == expected_bytes
        assert finished["archives_kept"] == 14
        assert finished["backups_deleted"] == 0
        assert finished["backup_bytes"] == 0
        assert finished["backups_kept"] == 0
        assert finished["errors"] == 0
        assert finished["log_archive_retention_days"] == 14
        assert finished["log_archive_keep_min"] == 5
        assert finished["backup_keep_count"] == 0
        _assert_no_absolute_path(logs, tmp_path)

    def test_boundary_is_strictly_older(
        self, serverdata: Path, service: DiskCleanupService
    ) -> None:
        make_archive(serverdata, "2026-11-18_06_00_00")
        make_archive(serverdata, "2026-11-04_12_00_00")
        make_archive(serverdata, "2026-11-04_11_59_59")

        result = service.run(_limits(14, 0, 0))

        assert _archives(serverdata) == ["2026-11-04_12_00_00", "2026-11-18_06_00_00"]
        assert result.archives_deleted == 1

    def test_archive_bytes_count_nested_files(
        self, serverdata: Path, service: DiskCleanupService
    ) -> None:
        make_archive(serverdata, "2026-11-18_06_00_00")
        old = make_archive(serverdata, "2026-10-01_03_00_00", files={"a.log": b"12345"})
        (old / "sub").mkdir()
        (old / "sub" / "b.log").write_bytes(b"123")
        _set_mtime(old, datetime(2026, 10, 1, 3))

        result = service.run(_limits(14, 0, 0))

        assert result.archive_bytes == 8


class TestKeepMinimum:
    """AC 2 and controller decision 1: the newest archives are kept."""

    @pytest.fixture
    def seven_old(self, serverdata: Path) -> list[str]:
        names = [_name(datetime(2026, 10, 1, 3) - timedelta(days=day)) for day in range(7)]
        for name in names:
            make_archive(serverdata, name)
        return names

    def test_keep_five(
        self, serverdata: Path, service: DiskCleanupService, seven_old: list[str]
    ) -> None:
        result = service.run(_limits(14, 5, 0))

        assert _archives(serverdata) == sorted(seven_old[:5])
        assert result.archives_deleted == 2

    def test_keep_zero_keeps_the_newest(
        self, serverdata: Path, service: DiskCleanupService, seven_old: list[str]
    ) -> None:
        result = service.run(_limits(14, 0, 0))

        assert _archives(serverdata) == [seven_old[0]]
        assert result.archives_deleted == 6

    def test_keep_a_thousand_keeps_all(
        self, serverdata: Path, service: DiskCleanupService, seven_old: list[str], logs: Logs
    ) -> None:
        result = service.run(_limits(14, 1000, 0))

        assert _archives(serverdata) == sorted(seven_old)
        assert result.archives_deleted == 0
        assert _finished(logs)["archives_kept"] == 7

    def test_single_old_archive_is_never_deleted(
        self, serverdata: Path, service: DiskCleanupService
    ) -> None:
        make_archive(serverdata, _name(NOW - timedelta(days=30)))

        result = service.run(_limits(1, 0, 0))

        assert _archives(serverdata) == [_name(NOW - timedelta(days=30))]
        assert result.archives_deleted == 0


class TestRetentionZero:
    """AC 3: retention 0 keeps every archive, and Archive/ is not even listed."""

    def test_nothing_deleted_and_not_listed(
        self,
        serverdata: Path,
        service: DiskCleanupService,
        logs: Logs,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        names = [_name(datetime(2026, 10, 1, 3) - timedelta(days=day)) for day in range(20)]
        for name in names:
            make_archive(serverdata, name)
        scanned: list[Path] = []

        def recording_scan(directory: Path) -> list[os.DirEntry[str]]:
            scanned.append(directory)
            return _real_scan(directory)

        monkeypatch.setattr(disk_cleanup_module, "_scan", recording_scan)

        result = service.run(_limits(0, 0, 0))

        assert _archives(serverdata) == sorted(names)
        assert result == CleanupResult()
        assert _events(logs, "disk_cleanup_deleted") == []
        assert scanned == []
        assert _finished(logs)["archives_kept"] == 0


class TestArchiveAge:
    """AC 4 and controller decision 2: the later of the name time and the mtime."""

    def test_later_of_name_and_mtime(self, serverdata: Path, service: DiskCleanupService) -> None:
        make_archive(serverdata, "2026-11-18_06_00_00")
        long_run = _name(NOW - timedelta(days=30))
        make_archive(serverdata, long_run, mtime=NOW - timedelta(hours=1))
        old_mtime = _name(NOW - timedelta(days=1))
        make_archive(serverdata, old_mtime, mtime=NOW - timedelta(days=30))
        both_old = _name(NOW - timedelta(days=30, hours=1))
        make_archive(serverdata, both_old)

        result = service.run(_limits(14, 0, 0))

        assert _archives(serverdata) == sorted(["2026-11-18_06_00_00", long_run, old_mtime])
        assert result.archives_deleted == 1

    def test_mtime_boundary(self, serverdata: Path, service: DiskCleanupService) -> None:
        make_archive(serverdata, "2026-11-18_06_00_00")
        at_limit = _name(NOW - timedelta(days=30))
        make_archive(serverdata, at_limit, mtime=NOW - timedelta(days=14))
        past_limit = _name(NOW - timedelta(days=31))
        make_archive(serverdata, past_limit, mtime=NOW - timedelta(days=14, seconds=1))

        result = service.run(_limits(14, 0, 0))

        assert _archives(serverdata) == sorted(["2026-11-18_06_00_00", at_limit])
        assert result.archives_deleted == 1

    def test_keep_order_follows_the_names(
        self, serverdata: Path, service: DiskCleanupService
    ) -> None:
        newest_name = "2026-10-20_03_00_00"
        make_archive(serverdata, newest_name)
        newest_mtime = "2026-10-01_03_00_00"
        make_archive(serverdata, newest_mtime, mtime=NOW - timedelta(hours=1))
        make_archive(serverdata, "2026-09-30_03_00_00")

        result = service.run(_limits(14, 1, 0))

        assert _archives(serverdata) == sorted([newest_name, newest_mtime])
        assert result.archives_deleted == 1


class TestNotArchives:
    """AC 5: unknown names, regular files and links in Archive/ are never deleted."""

    def _make_odd_entries(self, serverdata: Path, outside: Path) -> tuple[list[str], Path]:
        archive_dir = serverdata / ARCHIVE_DIR
        archive_dir.mkdir(parents=True)
        old = NOW - timedelta(days=100)
        names: list[str] = []
        for name in (
            "notes",
            "2026-11-01_03_00_00.old",
            "2026-11-01_03_00_00\n",
            "２０２６-１１-０１_０３_００_００",
            "2026-13-45_00_00_00",
        ):
            try:
                (archive_dir / name).mkdir()
            except OSError:
                # A file system that refuses the name cannot hold such an entry.
                continue
            _set_mtime(archive_dir / name, old)
            names.append(name)
        regular = archive_dir / "2026-11-01_03_00_00"
        regular.write_bytes(b"not a directory")
        _set_mtime(regular, old)
        names.append(regular.name)
        target = outside / "linked"
        target.mkdir()
        (target / "server-main.log").write_bytes(b"outside log")
        link = archive_dir / "2026-10-01_03_00_00"
        link.symlink_to(target, target_is_directory=True)
        _set_mtime(link, old)
        names.append(link.name)
        return names, target

    def test_none_deleted(
        self,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        logs: Logs,
        tmp_path: Path,
    ) -> None:
        names, target = self._make_odd_entries(serverdata, outside)

        result = service.run(_limits(1, 0, 0))

        assert _archives(serverdata) == sorted(names)
        assert (target / "server-main.log").read_bytes() == b"outside log"
        assert result == CleanupResult()
        skipped = _events(logs, "disk_cleanup_skipped")
        symlinks = [line for line in skipped if line["reason"] == "symlink"]
        assert [(line["path"], line["log_level"]) for line in symlinks] == [
            ("Logs/Archive/2026-10-01_03_00_00", "warning")
        ]
        others = [line for line in skipped if line["reason"] == "not_an_archive"]
        assert sorted(line["path"] for line in others) == sorted(
            f"Logs/Archive/{name}" for name in names if name != "2026-10-01_03_00_00"
        )
        assert all(line["log_level"] == "debug" for line in others)
        assert _finished(logs)["archives_kept"] == 0
        _assert_no_absolute_path(logs, tmp_path)

    def test_not_counted_as_kept(
        self, serverdata: Path, outside: Path, service: DiskCleanupService
    ) -> None:
        names, target = self._make_odd_entries(serverdata, outside)
        make_archive(serverdata, "2026-09-01_03_00_00")

        result = service.run(_limits(1, 1, 0))

        assert _archives(serverdata) == sorted([*names, "2026-09-01_03_00_00"])
        assert (target / "server-main.log").exists()
        assert result.archives_deleted == 0


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
        result = service.run(_limits(14, 5, 3))

        remaining = sorted(entry.name for entry in (serverdata / BACKUP_DIR).iterdir())
        assert remaining == sorted([*backups[:3], "a-directory", "linked.vcdbs"])
        assert (outside / "keep-me.txt").read_bytes() == b"outside"
        assert result.backups_deleted == 5
        assert result.backup_bytes == sum(range(4, 9))
        lines = _events(logs, "disk_cleanup_deleted")
        assert [(line["kind"], line["path"], line["bytes"]) for line in lines] == [
            ("backup", f"Backups/backup-{day}.vcdbs", day) for day in range(4, 9)
        ]
        skipped = {line["path"]: line for line in _events(logs, "disk_cleanup_skipped")}
        assert skipped["Backups/linked.vcdbs"]["reason"] == "symlink"
        assert skipped["Backups/linked.vcdbs"]["log_level"] == "warning"
        assert skipped["Backups/a-directory"]["reason"] == "not_a_file"
        assert skipped["Backups/a-directory"]["log_level"] == "debug"
        finished = _finished(logs)
        assert finished["backups_deleted"] == 5
        assert finished["backups_kept"] == 3
        _assert_no_absolute_path(logs, tmp_path)

    def test_keep_zero_does_not_list_backups(
        self,
        serverdata: Path,
        service: DiskCleanupService,
        backups: list[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        scanned: list[Path] = []

        def recording_scan(directory: Path) -> list[os.DirEntry[str]]:
            scanned.append(directory)
            return _real_scan(directory)

        monkeypatch.setattr(disk_cleanup_module, "_scan", recording_scan)

        result = service.run(_limits(14, 5, 0))

        remaining = sorted(entry.name for entry in (serverdata / BACKUP_DIR).iterdir())
        assert remaining == sorted([*backups, "a-directory", "linked.vcdbs"])
        assert result.backups_deleted == 0
        assert serverdata / BACKUP_DIR not in scanned


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


class TestNeverDeleted:
    """AC 7: everything outside the two target directories is left alone."""

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
        (serverdata / ARCHIVE_DIR).mkdir()
        (serverdata / BACKUP_DIR).mkdir()
        state = tmp_path / "data" / "vsmanager" / "state" / "api-settings.json"
        state.parent.mkdir(parents=True)
        state.write_bytes(b"{}")
        _set_mtime(state, old)
        before = _snapshot(tmp_path)

        result = service.run(_limits(1, 0, 1))

        assert _snapshot(tmp_path) == before
        assert result == CleanupResult()

    def _old_archives_in(self, directory: Path) -> None:
        for day in (100, 101, 102):
            archive = directory / _name(NOW - timedelta(days=day))
            archive.mkdir(parents=True)
            (archive / "server-main.log").write_bytes(b"outside archive")
            _set_mtime(archive, NOW - timedelta(days=day))

    def test_archive_dir_is_a_link(
        self,
        tmp_path: Path,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        logs: Logs,
    ) -> None:
        self._old_archives_in(outside)
        (serverdata / "Logs").mkdir()
        (serverdata / ARCHIVE_DIR).symlink_to(outside, target_is_directory=True)
        before = _snapshot(tmp_path)

        result = service.run(_limits(1, 0, 1))

        assert _snapshot(tmp_path) == before
        assert result == CleanupResult()
        skipped = _events(logs, "disk_cleanup_skipped")
        assert [(line["path"], line["reason"], line["log_level"]) for line in skipped] == [
            ("Logs/Archive", "symlink", "warning")
        ]

    def test_logs_dir_is_a_link(
        self,
        tmp_path: Path,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        logs: Logs,
    ) -> None:
        self._old_archives_in(outside / "Archive")
        (serverdata / "Logs").symlink_to(outside, target_is_directory=True)
        before = _snapshot(tmp_path)

        result = service.run(_limits(1, 0, 1))

        assert _snapshot(tmp_path) == before
        assert result == CleanupResult()
        skipped = _events(logs, "disk_cleanup_skipped")
        assert [(line["path"], line["reason"], line["log_level"]) for line in skipped] == [
            ("Logs", "symlink", "warning")
        ]

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

        result = service.run(_limits(1, 0, 1))

        assert _snapshot(tmp_path) == before
        assert result == CleanupResult()
        skipped = _events(logs, "disk_cleanup_skipped")
        assert [(line["path"], line["reason"], line["log_level"]) for line in skipped] == [
            ("Backups", "symlink", "warning")
        ]


def _failing_for(name: str, real: Callable[[Path], None]) -> Callable[[Path], None]:
    def delete(path: Path) -> None:
        if path.name == name:
            raise PermissionError(13, "Permission denied", str(path))
        real(path)

    return delete


def _unlink(path: Path) -> None:
    path.unlink()


class TestErrors:
    """AC 8: a failure is logged and counted; the other entries are still handled."""

    def test_archive_delete_fails(
        self,
        serverdata: Path,
        service: DiskCleanupService,
        logs: Logs,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        make_archive(serverdata, "2026-11-18_06_00_00")
        old = [_name(NOW - timedelta(days=day)) for day in (30, 31, 32)]
        for name in old:
            make_archive(serverdata, name)
        monkeypatch.setattr(
            disk_cleanup_module, "_delete_tree", _failing_for(old[1], shutil.rmtree)
        )

        result = service.run(_limits(14, 0, 0))

        assert _archives(serverdata) == sorted(["2026-11-18_06_00_00", old[1]])
        assert result.archives_deleted == 2
        assert result.archive_bytes == 2 * DEFAULT_ARCHIVE_BYTES
        assert result.errors == 1
        failed = _events(logs, "disk_cleanup_delete_failed")
        assert len(failed) == 1
        assert failed[0]["log_level"] == "warning"
        assert failed[0]["kind"] == "log_archive"
        assert failed[0]["path"] == f"Logs/Archive/{old[1]}"
        assert failed[0]["error"] == "Permission denied"
        assert failed[0]["errno"] == 13
        finished = _finished(logs)
        assert finished["archives_deleted"] == 2
        assert finished["archives_kept"] == 2
        assert finished["errors"] == 1
        _assert_no_absolute_path(logs, tmp_path)

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
        monkeypatch.setattr(
            disk_cleanup_module, "_delete_file", _failing_for("backup-3.vcdbs", _unlink)
        )

        result = service.run(_limits(14, 5, 1))

        remaining = sorted(entry.name for entry in (serverdata / BACKUP_DIR).iterdir())
        assert remaining == ["backup-1.vcdbs", "backup-3.vcdbs"]
        assert result.backups_deleted == 2
        assert result.errors == 1
        failed = _events(logs, "disk_cleanup_delete_failed")
        assert [(line["kind"], line["path"], line["error"]) for line in failed] == [
            ("backup", "Backups/backup-3.vcdbs", "Permission denied")
        ]
        assert _finished(logs)["errors"] == 1
        _assert_no_absolute_path(logs, tmp_path)

    def test_archive_listing_fails_and_backups_still_run(
        self,
        serverdata: Path,
        service: DiskCleanupService,
        logs: Logs,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        make_archive(serverdata, "2026-11-18_06_00_00")
        make_archive(serverdata, _name(NOW - timedelta(days=30)))
        for day in (1, 2):
            make_backup(serverdata, f"backup-{day}.vcdbs", NOW - timedelta(days=day))

        def failing_scan(directory: Path) -> list[os.DirEntry[str]]:
            if directory.name == "Archive":
                raise PermissionError(13, "Permission denied", str(directory))
            return _real_scan(directory)

        monkeypatch.setattr(disk_cleanup_module, "_scan", failing_scan)

        result = service.run(_limits(14, 0, 1))

        assert len(_archives(serverdata)) == 2
        assert result.archives_deleted == 0
        assert result.backups_deleted == 1
        assert result.errors == 1
        failed = _events(logs, "disk_cleanup_delete_failed")
        assert [(line["kind"], line["path"], line["log_level"]) for line in failed] == [
            ("log_archive", "Logs/Archive", "warning")
        ]
        _assert_no_absolute_path(logs, tmp_path)

    def test_mtime_read_fails_keeps_the_archive(
        self,
        serverdata: Path,
        service: DiskCleanupService,
        logs: Logs,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        make_archive(serverdata, "2026-11-18_06_00_00")
        old = _name(NOW - timedelta(days=30))
        make_archive(serverdata, old)

        def scan_then_remove(directory: Path) -> list[os.DirEntry[str]]:
            entries = _real_scan(directory)
            # Gone before its modification time is read: lstat raises FileNotFoundError.
            shutil.rmtree(directory / old)
            return entries

        monkeypatch.setattr(disk_cleanup_module, "_scan", scan_then_remove)

        result = service.run(_limits(14, 0, 0))

        assert result.archives_deleted == 0
        assert result.errors == 1
        failed = _events(logs, "disk_cleanup_delete_failed")
        assert [(line["path"], line["errno"]) for line in failed] == [(f"Logs/Archive/{old}", 2)]

    @pytest.mark.parametrize("layout", ["no_serverdata", "no_archive", "empty_serverdata"])
    def test_missing_directories(
        self, tmp_path: Path, serverdata: Path, logs: Logs, layout: str
    ) -> None:
        root = serverdata
        if layout == "no_serverdata":
            root = tmp_path / "missing" / "serverdata"
        elif layout == "no_archive":
            (serverdata / "Logs").mkdir()
        service = DiskCleanupService(root, now=lambda: NOW)

        result = service.run(_limits(1, 0, 1))

        assert result == CleanupResult()
        missing = _events(logs, "disk_cleanup_dir_missing")
        assert sorted(line["path"] for line in missing) == ["Backups", "Logs/Archive"]
        assert all(line["log_level"] == "debug" for line in missing)
        assert _finished(logs)["errors"] == 0


class TestPathCheck:
    """An entry replaced by a link between the listing and the deletion is not deleted."""

    def test_archive_replaced_by_a_link(
        self,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        logs: Logs,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        make_archive(serverdata, "2026-11-18_06_00_00")
        old = [_name(NOW - timedelta(days=day)) for day in (30, 31, 32)]
        for name in old:
            make_archive(serverdata, name)
        target = outside / "swapped"
        target.mkdir()
        (target / "server-main.log").write_bytes(b"outside log")

        def scan_then_swap(directory: Path) -> list[os.DirEntry[str]]:
            entries = _real_scan(directory)
            swapped = directory / old[1]
            swapped.rename(outside / "moved-away")
            swapped.symlink_to(target, target_is_directory=True)
            _set_mtime(swapped, NOW - timedelta(days=31))
            return entries

        monkeypatch.setattr(disk_cleanup_module, "_scan", scan_then_swap)

        result = service.run(_limits(14, 0, 0))

        assert _archives(serverdata) == sorted(["2026-11-18_06_00_00", old[1]])
        assert (serverdata / ARCHIVE_DIR / old[1]).is_symlink()
        assert (target / "server-main.log").read_bytes() == b"outside log"
        assert result.archives_deleted == 2
        outside_lines = [
            line for line in _events(logs, "disk_cleanup_skipped") if line["reason"] == "outside"
        ]
        assert [(line["path"], line["log_level"]) for line in outside_lines] == [
            (f"Logs/Archive/{old[1]}", "warning")
        ]
        _assert_no_absolute_path(logs, tmp_path)

    def test_backup_replaced_by_a_link(
        self,
        serverdata: Path,
        outside: Path,
        service: DiskCleanupService,
        logs: Logs,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for day in range(1, 4):
            make_backup(serverdata, f"backup-{day}.vcdbs", NOW - timedelta(days=day))

        def scan_then_swap(directory: Path) -> list[os.DirEntry[str]]:
            entries = _real_scan(directory)
            swapped = directory / "backup-2.vcdbs"
            swapped.unlink()
            swapped.symlink_to(outside / "keep-me.txt")
            _set_mtime(swapped, NOW - timedelta(days=2))
            return entries

        monkeypatch.setattr(disk_cleanup_module, "_scan", scan_then_swap)

        result = service.run(_limits(14, 5, 1))

        remaining = sorted(entry.name for entry in (serverdata / BACKUP_DIR).iterdir())
        assert remaining == ["backup-1.vcdbs", "backup-2.vcdbs"]
        assert (outside / "keep-me.txt").read_bytes() == b"outside"
        assert result.backups_deleted == 1
        outside_lines = [
            line for line in _events(logs, "disk_cleanup_skipped") if line["reason"] == "outside"
        ]
        assert [line["path"] for line in outside_lines] == ["Backups/backup-2.vcdbs"]
