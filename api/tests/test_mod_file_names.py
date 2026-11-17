"""Mod operations never replace or lose a mod's file (Story 19.4, Epic 19 ADR-8, ADR-9).

Enable and disable refuse a name in use in the mods directory or the mod state, compared
ignoring case. Every refusal leaves the directory, the state (in memory and on disk) and
the restart flag as they were.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from test_mod_version_change import install_existing, make_service, mod_files, snapshot

from vintagestory_api.services.mods import ModFileConflictError, ModService


def stray(name: str) -> Callable[[ModService, Path], None]:
    def put(service: ModService, tmp_path: Path) -> None:
        (service.state_manager.mods_dir / name).write_bytes(b"stray bytes")

    return put


def other_mod(name: str, *, enabled: bool) -> Callable[[ModService, Path], None]:
    def put(service: ModService, tmp_path: Path) -> None:
        install_existing(service, "modb", "2.0.0", name, enabled=enabled)

    return put


def entry_without_file(name: str, *, enabled: bool) -> Callable[[ModService, Path], None]:
    def put(service: ModService, tmp_path: Path) -> None:
        install_existing(service, "modb", "2.0.0", name, enabled=enabled).unlink()

    return put


def dangling_link(name: str) -> Callable[[ModService, Path], None]:
    def put(service: ModService, tmp_path: Path) -> None:
        (service.state_manager.mods_dir / name).symlink_to(tmp_path / "missing-target.zip")

    return put


# (setup, the name the error gives) for a file in the way of `Foo.zip`
IN_THE_WAY_OF_ENABLED = {
    "stray": (stray("Foo.zip"), "Foo.zip"),
    "other-mod": (other_mod("Foo.zip", enabled=True), "Foo.zip"),
    "other-case": (stray("foo.zip"), "foo.zip"),
    "entry-without-file": (entry_without_file("Foo.zip", enabled=True), "Foo.zip"),
    "dangling-symlink": (dangling_link("Foo.zip"), "Foo.zip"),
}

# ... and of `Foo.zip.disabled`
IN_THE_WAY_OF_DISABLED = {
    "stray": (stray("Foo.zip.disabled"), "Foo.zip.disabled"),
    "other-mod": (other_mod("Foo.zip", enabled=False), "Foo.zip.disabled"),
    "other-case": (stray("FOO.ZIP.disabled"), "FOO.ZIP.disabled"),
    "entry-without-file": (
        entry_without_file("Foo.zip", enabled=False),
        "Foo.zip.disabled",
    ),
    "dangling-symlink": (dangling_link("Foo.zip.disabled"), "Foo.zip.disabled"),
}


class TestEnableRefusesANameInUse:
    """AC 1, 7, 9 (FR218, FR220): enabling never replaces a file."""

    @pytest.mark.parametrize(
        "case", list(IN_THE_WAY_OF_ENABLED.values()), ids=list(IN_THE_WAY_OF_ENABLED)
    )
    def test_refused_and_nothing_changes(
        self, tmp_path: Path, case: tuple[Callable[[ModService, Path], None], str]
    ) -> None:
        setup, in_use = case
        service = make_service(tmp_path)
        service.set_server_running(True)
        install_existing(service, "moda", "1.0.0", "Foo.zip", enabled=False)
        setup(service, tmp_path)
        before = snapshot(service)

        with pytest.raises(ModFileConflictError) as raised:
            service.enable_mod("moda")

        assert raised.value.slug == "moda"
        assert raised.value.filename == in_use
        assert raised.value.operation == "enable"
        assert str(raised.value) == (
            f"Cannot enable 'moda': a file named {in_use} already exists in the mods directory."
        )
        assert snapshot(service) == before
        assert service.restart_state.pending_restart is False


class TestDisableRefusesANameInUse:
    """AC 2, 7, 9 (FR218, FR220): disabling never replaces a file."""

    @pytest.mark.parametrize(
        "case", list(IN_THE_WAY_OF_DISABLED.values()), ids=list(IN_THE_WAY_OF_DISABLED)
    )
    def test_refused_and_nothing_changes(
        self, tmp_path: Path, case: tuple[Callable[[ModService, Path], None], str]
    ) -> None:
        setup, in_use = case
        service = make_service(tmp_path)
        service.set_server_running(True)
        install_existing(service, "moda", "1.0.0", "Foo.zip")
        setup(service, tmp_path)
        before = snapshot(service)

        with pytest.raises(ModFileConflictError) as raised:
            service.disable_mod("moda")

        assert raised.value.filename == in_use
        assert raised.value.operation == "disable"
        assert str(raised.value) == (
            f"Cannot disable 'moda': a file named {in_use} already exists in the mods directory."
        )
        assert snapshot(service) == before
        assert service.restart_state.pending_restart is False


class TestEnableDisableWithoutConflict:
    """AC 3 (FR218): with nothing in the way both work as before; idempotent calls stay first."""

    def test_enabling_an_enabled_mod_with_a_name_in_the_way_changes_nothing(
        self, tmp_path: Path
    ) -> None:
        service = make_service(tmp_path)
        service.set_server_running(True)
        install_existing(service, "moda", "1.0.0", "Foo.zip")
        stray("Foo.zip.disabled")(service, tmp_path)
        before = snapshot(service)

        result = service.enable_mod("moda")

        assert (result.enabled, result.pending_restart) == (True, False)
        assert snapshot(service) == before
        assert service.restart_state.pending_restart is False

    def test_disabling_a_disabled_mod_with_a_name_in_the_way_changes_nothing(
        self, tmp_path: Path
    ) -> None:
        service = make_service(tmp_path)
        service.set_server_running(True)
        install_existing(service, "moda", "1.0.0", "Foo.zip", enabled=False)
        stray("Foo.zip")(service, tmp_path)
        before = snapshot(service)

        result = service.disable_mod("moda")

        assert (result.enabled, result.pending_restart) == (False, False)
        assert snapshot(service) == before
        assert service.restart_state.pending_restart is False

    def test_round_trip_leaves_only_the_mods_file(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        path = install_existing(service, "moda", "1.0.0", "Foo.zip")
        original = path.read_bytes()

        service.disable_mod("moda")
        assert mod_files(service) == ["Foo.zip.disabled"]
        service.enable_mod("moda")

        assert mod_files(service) == ["Foo.zip"]
        assert path.read_bytes() == original
        state = service.state_manager.get_mod_by_slug("moda")
        assert state is not None
        assert (state.filename, state.enabled) == ("Foo.zip", True)
