"""Mod operations never replace or lose a mod's file (Story 19.4, Epic 19 ADR-8, ADR-9).

Enable and disable refuse a name in use in the mods directory or the mod state, compared
ignoring case. Every refusal leaves the directory, the state (in memory and on disk) and
the restart flag as they were.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
import respx
from test_mod_operation_lock import mock_foo_zip
from test_mod_version_change import (
    install_existing,
    installed_version_on_disk,
    make_service,
    mock_demo,
    mod_files,
    snapshot,
)

from vintagestory_api.services.mods import (
    ModFileConflictError,
    ModFileMissingError,
    ModService,
)


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


def lose_own_file(service: ModService, name: str, how: str, tmp_path: Path) -> None:
    """Remove the mod's own file by hand: deleted, or replaced by a dangling symlink."""
    path = service.state_manager.mods_dir / name
    path.unlink()
    if how == "dangling-symlink":
        path.symlink_to(tmp_path / "missing-target.zip")


class TestOwnFileMissing:
    """AC 13, 14 (FR222): a mod whose file was removed by hand answers MOD_FILE_MISSING."""

    @pytest.mark.parametrize("how", ["deleted", "dangling-symlink"])
    def test_disable_is_refused_and_nothing_changes(self, tmp_path: Path, how: str) -> None:
        service = make_service(tmp_path)
        service.set_server_running(True)
        install_existing(service, "moda", "1.0.0", "Foo.zip")
        lose_own_file(service, "Foo.zip", how, tmp_path)
        before = snapshot(service)

        with pytest.raises(ModFileMissingError) as raised:
            service.disable_mod("moda")

        assert (raised.value.slug, raised.value.filename) == ("moda", "Foo.zip")
        assert raised.value.operation == "disable"
        assert str(raised.value) == (
            "Cannot disable 'moda': its file Foo.zip is no longer in the mods directory. "
            "Remove the mod and install it again."
        )
        assert snapshot(service) == before
        assert service.restart_state.pending_restart is False

    @pytest.mark.parametrize("how", ["deleted", "dangling-symlink"])
    def test_enable_is_refused_and_nothing_changes(self, tmp_path: Path, how: str) -> None:
        service = make_service(tmp_path)
        service.set_server_running(True)
        install_existing(service, "moda", "1.0.0", "Foo.zip", enabled=False)
        lose_own_file(service, "Foo.zip.disabled", how, tmp_path)
        before = snapshot(service)

        with pytest.raises(ModFileMissingError) as raised:
            service.enable_mod("moda")

        assert raised.value.filename == "Foo.zip.disabled"
        assert raised.value.operation == "enable"
        assert str(raised.value) == (
            "Cannot enable 'moda': its file Foo.zip.disabled is no longer in the mods "
            "directory. Remove the mod and install it again."
        )
        assert snapshot(service) == before
        assert service.restart_state.pending_restart is False

    def test_a_missing_file_is_reported_before_a_name_in_the_way(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "moda", "1.0.0", "Foo.zip")
        lose_own_file(service, "Foo.zip", "deleted", tmp_path)
        stray("Foo.zip.disabled")(service, tmp_path)
        before = snapshot(service)

        with pytest.raises(ModFileMissingError):
            service.disable_mod("moda")

        assert snapshot(service) == before

    def test_an_idempotent_call_still_succeeds(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        service.set_server_running(True)
        install_existing(service, "moda", "1.0.0", "Foo.zip")
        lose_own_file(service, "Foo.zip", "deleted", tmp_path)
        before = snapshot(service)

        result = service.enable_mod("moda")

        assert (result.enabled, result.pending_restart) == (True, False)
        assert snapshot(service) == before

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize("how", ["deleted", "dangling-symlink"])
    async def test_a_version_change_is_refused_before_any_lookup(
        self, tmp_path: Path, how: str
    ) -> None:
        """Story 24.3 (FR331, Epic 24 ADR-5 decision 1): 409, not a 500 after a download."""
        service = make_service(tmp_path)
        service.set_server_running(True)
        install_existing(service, "moda", "1.0.0", "Foo.zip")
        lose_own_file(service, "Foo.zip", how, tmp_path)
        before = snapshot(service)

        with pytest.raises(ModFileMissingError) as raised:
            await service.change_version("moda", "2.0.0")

        assert raised.value.operation == "change the version of"
        assert str(raised.value) == (
            "Cannot change the version of 'moda': its file Foo.zip is no longer in the mods "
            "directory. Remove the mod and install it again."
        )
        assert respx.calls.call_count == 0
        assert snapshot(service) == before
        assert service.restart_state.pending_restart is False

    @pytest.mark.asyncio
    async def test_a_version_change_to_the_installed_version_still_succeeds(
        self, tmp_path: Path
    ) -> None:
        """Changing to the installed version changes nothing, so it needs no file."""
        service = make_service(tmp_path)
        install_existing(service, "moda", "1.0.0", "Foo.zip").unlink()

        result = await service.change_version("moda", "1.0.0")

        assert result.changed is False

    @pytest.mark.parametrize("enabled", [True, False], ids=["enabled", "disabled"])
    def test_the_mod_can_still_be_removed(self, tmp_path: Path, enabled: bool) -> None:
        service = make_service(tmp_path)
        path = install_existing(service, "moda", "1.0.0", "Foo.zip", enabled=enabled)
        path.unlink()

        result = service.remove_mod("moda")

        assert result.slug == "moda"
        assert service.state_manager.get_mod_by_slug("moda") is None
        assert snapshot(service)[1] == {"saved": {}, "memory": {}}


LEFTOVERS = {
    "Foo.zip.vsm-tmp": b"working copy",
    "Foo.zip.vsm-bak": b"kept aside",
    "Foo.zip.tmp": b"old-style temp",
}


def put_leftovers(service: ModService) -> None:
    mods_dir = service.state_manager.mods_dir
    mods_dir.mkdir(parents=True, exist_ok=True)
    for name, content in LEFTOVERS.items():
        (mods_dir / name).write_bytes(content)


def leftover_bytes(service: ModService, *names: str) -> dict[str, bytes]:
    return {n: (service.state_manager.mods_dir / n).read_bytes() for n in names}


class TestLeftoversAreNotConflicts:
    """AC 17 (FR223): working files never count as a name in use (ADR-9 decision 8)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_install(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        put_leftovers(service)
        mock_foo_zip("moda")

        result = await service.install_mod("moda")

        assert result.filename == "Foo.zip"
        # The install's own working copy is Foo.zip.vsm-tmp; it became Foo.zip
        assert mod_files(service) == ["Foo.zip", "Foo.zip.tmp", "Foo.zip.vsm-bak"]
        assert leftover_bytes(service, "Foo.zip.tmp", "Foo.zip.vsm-bak") == {
            "Foo.zip.tmp": LEFTOVERS["Foo.zip.tmp"],
            "Foo.zip.vsm-bak": LEFTOVERS["Foo.zip.vsm-bak"],
        }

    def test_enable_and_disable(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "moda", "1.0.0", "Foo.zip")
        put_leftovers(service)

        service.disable_mod("moda")
        assert "Foo.zip.disabled" in mod_files(service)
        service.enable_mod("moda")

        assert mod_files(service) == sorted(["Foo.zip", *LEFTOVERS])
        assert leftover_bytes(service, *LEFTOVERS) == LEFTOVERS

    @respx.mock
    @pytest.mark.asyncio
    async def test_same_name_version_change(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "Foo.zip")
        put_leftovers(service)
        mock_demo("Foo.zip", "Foo.zip")

        result = await service.change_version("demo", "1.1.0")

        assert result.filename == "Foo.zip"
        assert installed_version_on_disk(service, "Foo.zip") == "1.1.0"
        # Its own backup replaced the leftover .vsm-bak and was then deleted
        assert mod_files(service) == ["Foo.zip", "Foo.zip.tmp"]
        assert leftover_bytes(service, "Foo.zip.tmp") == {"Foo.zip.tmp": LEFTOVERS["Foo.zip.tmp"]}
