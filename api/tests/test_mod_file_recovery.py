"""Start-up recovery of the manager's working files (Story 19.4, Epic 19 ADR-9).

Each test builds the mods directory an interrupted install or version change leaves, runs
the recovery and checks the listing, the bytes and that the mod state is not changed.
"""

from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
from test_mod_version_change import make_service, mod_files, mod_zip_bytes, snapshot

from vintagestory_api.models.mods import ModState
from vintagestory_api.services.mod_file_recovery import (
    KEPT_ASIDE_SUFFIX,
    WORKING_COPY_SUFFIX,
    recover_working_files,
)
from vintagestory_api.services.mods import ModService


def archive(version: str) -> bytes:
    return mod_zip_bytes({"modid": "demo", "name": "Demo", "version": version})


def build(service: ModService, files: dict[str, bytes], state: tuple[str, str] | None) -> None:
    """Write `files` into the mods directory and save `state` (file name, version)."""
    manager = service.state_manager
    manager.mods_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (manager.mods_dir / name).write_bytes(content)
    if state is not None:
        filename, version = state
        manager.set_mod_state(
            filename,
            ModState(
                filename=filename,
                slug="demo",
                version=version,
                enabled=not filename.endswith(".disabled"),
                installed_at=datetime(2026, 1, 1, tzinfo=UTC),
                asset_id=1,
            ),
        )
        manager.save()


def contents(service: ModService) -> dict[str, bytes]:
    mods_dir = service.state_manager.mods_dir
    return {p.name: p.read_bytes() for p in sorted(mods_dir.iterdir())}


def log_lines(logs: StringIO, event: str) -> list[str]:
    return [line for line in logs.getvalue().splitlines() if event in line]


V1, V2 = archive("1.0.0"), archive("1.1.0")
TMP, BAK = WORKING_COPY_SUFFIX, KEPT_ASIDE_SUFFIX

# (directory, state, directory afterwards, the log events), for `X.zip` + suffix
Interruption = tuple[dict[str, bytes], tuple[str, str] | None, dict[str, bytes], list[str]]
INTERRUPTIONS: dict[str, Interruption] = {
    "install-after-copy": (
        {f"X.zip{{s}}{TMP}": V2},
        None,
        {},
        ["mod_working_copy_removed"],
    ),
    "same-name-after-move-aside": (
        {f"X.zip{{s}}{TMP}": V2, f"X.zip{{s}}{BAK}": V1},
        ("X.zip{s}", "1.0.0"),
        {"X.zip{s}": V1},
        ["mod_working_copy_removed", "mod_backup_restored"],
    ),
    "same-name-after-rename": (
        {"X.zip{s}": V2, f"X.zip{{s}}{BAK}": V1},
        ("X.zip{s}", "1.0.0"),
        {"X.zip{s}": V1},
        ["mod_backup_restored"],
    ),
    "same-name-after-save": (
        {"X.zip{s}": V2, f"X.zip{{s}}{BAK}": V1},
        ("X.zip{s}", "1.1.0"),
        {"X.zip{s}": V2},
        ["mod_backup_removed"],
    ),
    "case-only-after-rename": (
        {"x.zip{s}": V2, f"X.zip{{s}}{BAK}": V1},
        ("X.zip{s}", "1.0.0"),
        {"X.zip{s}": V1},
        ["mod_backup_restored"],
    ),
    "case-only-after-save": (
        {"x.zip{s}": V2, f"X.zip{{s}}{BAK}": V1},
        ("x.zip{s}", "1.1.0"),
        {"x.zip{s}": V2},
        ["mod_backup_removed"],
    ),
}


class TestInterruptedOperations:
    """AC 15 (FR223): one test per interruption point, enabled and disabled."""

    @pytest.mark.parametrize("suffix", ["", ".disabled"], ids=["enabled", "disabled"])
    @pytest.mark.parametrize(
        "case", list(INTERRUPTIONS.values()), ids=list(INTERRUPTIONS)
    )
    def test_recovered(
        self,
        tmp_path: Path,
        captured_logs: StringIO,
        suffix: str,
        case: Interruption,
    ) -> None:
        files, state, expected, events = case
        service = make_service(tmp_path)
        build(
            service,
            {name.format(s=suffix): content for name, content in files.items()},
            None if state is None else (state[0].format(s=suffix), state[1]),
        )
        state_before = snapshot(service)[1]

        recover_working_files(service.state_manager)

        assert contents(service) == {
            name.format(s=suffix): content for name, content in expected.items()
        }
        assert snapshot(service)[1] == state_before
        for event in events:
            assert len(log_lines(captured_logs, event)) == 1, event
        assert log_lines(captured_logs, "mod_recovery_failed") == []

    def test_a_restore_names_the_file_it_replaced(
        self, tmp_path: Path, captured_logs: StringIO
    ) -> None:
        service = make_service(tmp_path)
        build(service, {"x.zip": V2, f"X.zip{BAK}": V1}, ("X.zip", "1.0.0"))

        recover_working_files(service.state_manager)

        [line] = log_lines(captured_logs, "mod_backup_restored")
        assert "X.zip" in line
        assert "replaced" in line
        assert "x.zip" in line

    def test_an_unreadable_new_file_is_replaced_by_the_backup(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        build(service, {"X.zip": b"not a zip", f"X.zip{BAK}": V1}, ("X.zip", "1.1.0"))

        recover_working_files(service.state_manager)

        assert contents(service) == {"X.zip": V1}

    def test_a_failed_action_is_logged_and_the_rest_is_recovered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_logs: StringIO
    ) -> None:
        service = make_service(tmp_path)
        build(service, {f"A.zip{BAK}": V1, f"B.zip{BAK}": V2, f"C.zip{TMP}": V2}, None)
        original_rename = Path.rename

        def failing_rename(self: Path, target: Path) -> Path:
            if self.name == f"A.zip{BAK}":
                raise OSError("read-only file system")
            return original_rename(self, target)

        monkeypatch.setattr(Path, "rename", failing_rename)

        recover_working_files(service.state_manager)

        assert contents(service) == {f"A.zip{BAK}": V1, "B.zip": V2}
        [line] = log_lines(captured_logs, "mod_recovery_failed")
        assert f"A.zip{BAK}" in line
        assert "read-only file system" in line

    def test_no_mods_directory_is_nothing_to_do(
        self, tmp_path: Path, captured_logs: StringIO
    ) -> None:
        service = make_service(tmp_path)

        recover_working_files(service.state_manager)

        assert not service.state_manager.mods_dir.exists()
        assert log_lines(captured_logs, "mod_recovery_failed") == []

    def test_mods_and_their_files_are_untouched(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        build(service, {"X.zip": V1, "Y.zip.disabled": V2}, ("X.zip", "1.0.0"))

        recover_working_files(service.state_manager)

        assert contents(service) == {"X.zip": V1, "Y.zip.disabled": V2}


class TestUnknownLeftovers:
    """AC 16 (FR223): .tmp/.bak files the manager did not name are reported, never touched."""

    def test_named_in_one_warning_and_kept(self, tmp_path: Path, captured_logs: StringIO) -> None:
        service = make_service(tmp_path)
        files = {"notes.bak": b"notes", "Old.zip.tmp": b"old", "Mod.ZIP.BAK": b"mod"}
        build(service, {**files, "X.zip": V1}, ("X.zip", "1.0.0"))

        recover_working_files(service.state_manager)

        assert contents(service) == {**files, "X.zip": V1}
        [line] = log_lines(captured_logs, "mod_directory_unknown_leftovers")
        for name in files:
            assert name in line

    def test_no_warning_without_them(self, tmp_path: Path, captured_logs: StringIO) -> None:
        service = make_service(tmp_path)
        build(service, {"X.zip": V1}, ("X.zip", "1.0.0"))

        recover_working_files(service.state_manager)

        assert log_lines(captured_logs, "mod_directory_unknown_leftovers") == []
        assert mod_files(service) == ["X.zip"]
