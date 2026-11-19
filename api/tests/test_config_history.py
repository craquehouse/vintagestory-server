"""Tests for the config history store (Story 23.6, FR321-FR323, Epic 23 ADR-7)."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vintagestory_api.services.config_history import (
    ConfigHistory,
    ConfigHistoryWriteError,
    RevisionInvalidError,
    RevisionNotFoundError,
)

START = datetime(2026, 11, 19, 12, 0, 0, 123456, tzinfo=UTC)


class Clock:
    """A clock the tests move."""

    def __init__(self, now: datetime = START) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "state" / "config-history"


@pytest.fixture
def history(root: Path, clock: Clock) -> ConfigHistory:
    return ConfigHistory(root, now=clock)


class TestRecord:
    def test_records_the_bytes_and_an_index_entry(self, history: ConfigHistory, root: Path) -> None:
        data = b'\xef\xbb\xbf{"a": 1} // c'

        revision = history.record("ModConfig/x.json", data, "admin")

        directory = root / "ModConfig" / "x.json"
        assert revision.id == "20261119T120000123456Z"
        assert (directory / f"{revision.id}.json").read_bytes() == data
        index = json.loads((directory / "index.json").read_text())
        assert index == {
            "revisions": [
                {
                    "id": revision.id,
                    "saved_at": "2026-11-19T12:00:00.123456Z",
                    "saved_by": "admin",
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            ]
        }

    def test_lists_newest_first(self, history: ConfigHistory, clock: Clock) -> None:
        first = history.record("x.json", b"1", "admin")
        clock.now += timedelta(seconds=1)
        second = history.record("x.json", b"2", "admin")

        assert [r.id for r in history.list("x.json")] == [second.id, first.id]

    def test_a_collision_gets_a_suffix(self, history: ConfigHistory) -> None:
        first = history.record("x.json", b"1", "admin")
        second = history.record("x.json", b"2", "admin")
        third = history.record("x.json", b"3", "admin")

        assert second.id == f"{first.id}-2"
        assert third.id == f"{first.id}-3"
        assert history.read("x.json", second.id)[1] == b"2"

    def test_an_unwritable_store_raises_without_a_path(
        self, history: ConfigHistory, root: Path
    ) -> None:
        root.parent.mkdir(parents=True)
        root.write_text("not a directory")

        with pytest.raises(ConfigHistoryWriteError) as exc_info:
            history.record("ModConfig/x.json", b"1", "admin")

        assert str(root) not in exc_info.value.message

    @pytest.mark.parametrize("relative", ["../x.json", "/etc/x.json", "a//b.json", ""])
    def test_a_path_outside_the_store_is_refused(
        self, history: ConfigHistory, relative: str
    ) -> None:
        with pytest.raises(ConfigHistoryWriteError):
            history.record(relative, b"1", "admin")

        assert history.list(relative) == []


class TestReadAndRemove:
    def test_reads_a_revision(self, history: ConfigHistory) -> None:
        revision = history.record("x.json", b"old", "admin")

        read_revision, data = history.read("x.json", revision.id)

        assert read_revision == revision
        assert data == b"old"

    @pytest.mark.parametrize(
        "revision_id", ["../x", "20261119T000000000000Z/../a", "", "index", "20261119T1Z"]
    )
    def test_a_malformed_id_is_invalid(self, history: ConfigHistory, revision_id: str) -> None:
        history.record("x.json", b"old", "admin")

        with pytest.raises(RevisionInvalidError):
            history.read("x.json", revision_id)
        with pytest.raises(RevisionInvalidError):
            history.remove("x.json", revision_id)

    def test_an_unknown_id_is_not_found(self, history: ConfigHistory) -> None:
        history.record("x.json", b"old", "admin")

        with pytest.raises(RevisionNotFoundError):
            history.read("x.json", "20200101T000000000000Z")

    def test_a_listed_revision_whose_file_is_gone_is_not_found(
        self, history: ConfigHistory, root: Path
    ) -> None:
        revision = history.record("x.json", b"old", "admin")
        (root / "x.json" / f"{revision.id}.json").unlink()

        with pytest.raises(RevisionNotFoundError):
            history.read("x.json", revision.id)

    def test_remove_drops_the_entry_and_the_file(self, history: ConfigHistory, root: Path) -> None:
        revision = history.record("x.json", b"old", "admin")

        history.remove("x.json", revision.id)

        assert history.list("x.json") == []
        assert not (root / "x.json" / f"{revision.id}.json").exists()


class TestIndex:
    def test_no_history_is_an_empty_list(self, history: ConfigHistory) -> None:
        assert history.list("ModConfig/never.json") == []

    def test_an_unreadable_index_lists_nothing_and_a_record_starts_again(
        self, history: ConfigHistory, root: Path
    ) -> None:
        directory = root / "x.json"
        directory.mkdir(parents=True)
        (directory / "index.json").write_text("{ broken")

        assert history.list("x.json") == []
        revision = history.record("x.json", b"new", "admin")
        assert [r.id for r in history.list("x.json")] == [revision.id]


class TestPrune:
    def _record(self, history: ConfigHistory, clock: Clock, count: int, step: timedelta) -> None:
        for index in range(count):
            history.record("x.json", str(index).encode(), "admin")
            clock.now += step

    def test_keeps_the_newest_by_count(
        self, history: ConfigHistory, clock: Clock, root: Path
    ) -> None:
        self._record(history, clock, 5, timedelta(seconds=1))
        ids = [r.id for r in history.list("x.json")]

        removed = history.prune("x.json", keep_count=3, max_age_days=0)

        assert sorted(removed) == sorted(ids[3:])
        assert [r.id for r in history.list("x.json")] == ids[:3]
        assert sorted(p.name for p in (root / "x.json").iterdir()) == sorted(
            [f"{i}.json" for i in ids[:3]] + ["index.json"]
        )

    def test_removes_old_revisions_but_never_the_newest(
        self, history: ConfigHistory, clock: Clock
    ) -> None:
        self._record(history, clock, 3, timedelta(days=2))
        clock.now += timedelta(days=5)
        newest = history.list("x.json")[0].id

        history.prune("x.json", keep_count=20, max_age_days=1)

        assert [r.id for r in history.list("x.json")] == [newest]

    def test_age_zero_keeps_old_revisions(self, history: ConfigHistory, clock: Clock) -> None:
        self._record(history, clock, 3, timedelta(days=400))

        assert history.prune("x.json", keep_count=20, max_age_days=0) == []
        assert len(history.list("x.json")) == 3
