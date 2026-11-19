"""Tests for the daily disk cleanup job (Story 22.4, Epic 22 ADR-9 decision 6).

The cleanup handles `Backups/` only (maintainer's decision, 2026-11-19). The real job
function is imported at module import time, before the autouse fixture in conftest.py
replaces the module attribute with a no-op, so these tests run the real code. Every
Settings here points under tmp_path; nothing reads or writes dev/ or ./data.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from vintagestory_api.config import Settings
from vintagestory_api.jobs.disk_cleanup import (
    DISK_CLEANUP_CRON,
    DISK_CLEANUP_JOB_ID,
    disk_cleanup,
    run_disk_cleanup,
)
from vintagestory_api.services.api_settings import ApiSettingsService
from vintagestory_api.services.disk_cleanup import (
    BACKUP_DIR,
    CleanupLimits,
    CleanupResult,
    DiskCleanupService,
)

NOW = datetime(2026, 11, 18, 12, 0, 0)


def _backup(settings: Settings, name: str, days_old: int) -> None:
    path = settings.serverdata_dir / BACKUP_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"backup")
    stamp = (NOW - timedelta(days=days_old)).timestamp()
    os.utime(path, (stamp, stamp))


def _backups(settings: Settings) -> list[str]:
    return sorted(entry.name for entry in (settings.serverdata_dir / BACKUP_DIR).iterdir())


def _write_api_settings(settings: Settings, values: dict[str, int]) -> None:
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    (settings.state_dir / "api-settings.json").write_text(json.dumps(values))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    (data_dir / "serverdata").mkdir(parents=True)
    return Settings(data_dir=data_dir)


class FakeServerService:
    """Stands in for ServerService: the job only reads its settings."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings


def test_constants() -> None:
    assert DISK_CLEANUP_JOB_ID == "disk_cleanup"
    assert DISK_CLEANUP_CRON == "0 3 * * *"


class TestRunDiskCleanup:
    """run_disk_cleanup reads the limit at each run (Epic 22 ADR-7 decision 4)."""

    async def test_saved_limit_applies(self, settings: Settings) -> None:
        _write_api_settings(settings, {"backup_keep_count": 1})
        _backup(settings, "newer.vcdbs", 1)
        _backup(settings, "older.vcdbs", 2)

        result = await run_disk_cleanup(settings)

        assert _backups(settings) == ["newer.vcdbs"]
        assert result == CleanupResult(backups_deleted=1, backup_bytes=6)

    async def test_default_keeps_all(self, settings: Settings) -> None:
        for day in range(1, 6):
            _backup(settings, f"backup-{day}.vcdbs", day * 100)

        result = await run_disk_cleanup(settings)

        assert len(_backups(settings)) == 5
        assert result == CleanupResult()

    async def test_limit_is_read_at_each_run(self, settings: Settings) -> None:
        _write_api_settings(settings, {"backup_keep_count": 1})
        _backup(settings, "a.vcdbs", 1)
        _backup(settings, "b.vcdbs", 2)

        first = await run_disk_cleanup(settings)
        assert first.backups_deleted == 1

        await ApiSettingsService(settings).update_setting("backup_keep_count", 0)
        _backup(settings, "c.vcdbs", 30)

        second = await run_disk_cleanup(settings)

        assert second.backups_deleted == 0
        assert _backups(settings) == ["a.vcdbs", "c.vcdbs"]

    async def test_logs_are_left_alone(self, settings: Settings) -> None:
        """The game keeps its own log archives (maintainer's decision, 2026-11-19)."""
        _write_api_settings(settings, {"backup_keep_count": 1})
        archive = settings.serverdata_dir / "Logs" / "Archive" / "2020-01-01_03_00_00"
        archive.mkdir(parents=True)
        (archive / "server-main.log").write_bytes(b"old log")

        await run_disk_cleanup(settings)

        assert (archive / "server-main.log").read_bytes() == b"old log"


class TestDiskCleanupJob:
    """The job function under safe_job."""

    async def test_logs_around_the_run(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        server = FakeServerService(settings)
        monkeypatch.setattr("vintagestory_api.services.server.get_server_service", lambda: server)

        with capture_logs() as logs:
            result = await disk_cleanup()

        assert result is None
        events = [log["event"] for log in logs]
        assert events.index("disk_cleanup_started") < events.index("disk_cleanup_finished")
        assert events.index("disk_cleanup_finished") < events.index("disk_cleanup_completed")
        assert "disk_cleanup_failed" not in events

    async def test_uses_the_server_service_settings(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_api_settings(settings, {"backup_keep_count": 1})
        _backup(settings, "newer.vcdbs", 1)
        _backup(settings, "older.vcdbs", 2)
        server = FakeServerService(settings)
        monkeypatch.setattr("vintagestory_api.services.server.get_server_service", lambda: server)

        await disk_cleanup()

        assert _backups(settings) == ["newer.vcdbs"]

    async def test_failure_is_logged_not_raised(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        server = FakeServerService(settings)
        monkeypatch.setattr("vintagestory_api.services.server.get_server_service", lambda: server)

        def failing_run(_self: DiskCleanupService, _limits: CleanupLimits) -> CleanupResult:
            raise OSError("disk unavailable")

        monkeypatch.setattr(DiskCleanupService, "run", failing_run)

        with capture_logs() as logs:
            result = await disk_cleanup()

        assert result is None
        events = [log["event"] for log in logs]
        assert "disk_cleanup_failed" in events
        assert "disk_cleanup_completed" not in events
