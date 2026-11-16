"""Tests for mod update detection (Story 14.1)."""

import asyncio
import json
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any, get_args

import httpx
import pytest
import respx
from httpx import Response

from vintagestory_api.models.mod_updates import Compatibility, StoredModRecord, StoredRelease
from vintagestory_api.models.moddb import MOD_FIELDS, RELEASE_FIELDS, ReleaseDict, normalize_mod
from vintagestory_api.models.mods import ModInfo
from vintagestory_api.services.mod_api import CompatibilityStatus, ModApiClient
from vintagestory_api.services.mod_updates import (
    ModUpdateCheckInProgressError,
    ModUpdateService,
    ModUpdateStore,
    build_status_items,
    evaluate_update,
    is_prerelease,
    parse_base_version,
)

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"


def fixture_releases(name: str) -> list[StoredRelease]:
    data = json.loads((FIXTURES / f"mod_{name}.json").read_text())
    return [StoredRelease.from_api(r) for r in data["mod"]["releases"]]


def release(version: str, tags: list[str], modid: str = "demo") -> StoredRelease:
    return StoredRelease(
        modversion=version, modidstr=modid, tags=tags, fileid=1, filename=f"{version}.zip"
    )


class TestVersionHelpers:
    @pytest.mark.parametrize(
        ("version", "expected"),
        [("2.0.0-rc.1", True), ("2.0.0-pre.8", True), ("1.14.3", False), ("5.0.3", False)],
    )
    def test_is_prerelease(self, version: str, expected: bool) -> None:
        assert is_prerelease(version) is expected

    @pytest.mark.parametrize(
        ("version", "expected"),
        [
            ("2.0.0-pre.8", (2, 0, 0)),
            ("1.14.3", (1, 14, 3)),
            ("2.0", (2, 0)),
            ("1.0.10", (1, 0, 10)),
            ("2.0.0a-pre.1", None),
            ("", None),
            ("v1.2.3", None),
        ],
    )
    def test_parse_base_version(self, version: str, expected: tuple[int, ...] | None) -> None:
        assert parse_base_version(version) == expected


class TestCarryOn:
    """Publish order differs from version order (Story 14.0)."""

    def test_prerelease_install_is_offered_newer_prerelease_not_older_stable(self) -> None:
        result = evaluate_update("carryon", "2.0.0-pre.8", fixture_releases("carryon"), "1.22.0")

        assert result.status == "update_available"
        assert result.offered is not None
        assert result.offered.modversion == "2.0.0-rc.1"

    def test_prerelease_install_skips_stable_with_lower_base(self) -> None:
        # pre.8 is not tagged for 1.22.7, rc.1 is; 1.14.3 is tagged but has a lower base.
        result = evaluate_update("carryon", "2.0.0-pre.7", fixture_releases("carryon"), "1.22.7")

        assert result.offered is not None
        assert result.offered.modversion == "2.0.0-rc.1"
        assert result.offered_compatibility == "compatible"

    def test_stable_install_is_never_offered_a_prerelease(self) -> None:
        result = evaluate_update("carryon", "1.14.3", fixture_releases("carryon"), "1.22.7")

        assert result.status == "up_to_date"
        assert result.offered is None

    def test_stable_install_is_offered_newest_compatible_stable(self) -> None:
        result = evaluate_update("carryon", "1.14.1", fixture_releases("carryon"), "1.22.7")

        assert result.status == "update_available"
        assert result.offered is not None
        assert result.offered.modversion == "1.14.3"
        assert result.offered_compatibility == "compatible"

    def test_installed_version_not_listed_is_unknown(self) -> None:
        result = evaluate_update("carryon", "9.9.9", fixture_releases("carryon"), "1.22.7")

        assert result.status == "unknown"
        assert result.reason == "installed_release_not_listed"


class TestSeveralModids:
    def test_releases_for_other_modids_are_ignored(self) -> None:
        # vsinstrumentsbase also has a 1.0.1, and newer releases tagged for 1.21.
        result = evaluate_update("instruments", "1.0.1", fixture_releases("instruments"), "1.21.6")

        assert result.status == "blocked"
        assert result.offered is None

    def test_newest_release_of_own_modid_is_up_to_date(self) -> None:
        result = evaluate_update("instruments", "1.2.2", fixture_releases("instruments"), "1.21.6")

        assert result.status == "up_to_date"

    def test_second_modid_in_entry_is_not_offered_the_first(self) -> None:
        result = evaluate_update(
            "egocaribresinmapmarkers", "1.0.0", fixture_releases("egocaribautomapmarkers"), "1.22.0"
        )

        assert result.status == "up_to_date"

    def test_compatible_update_within_modid(self) -> None:
        result = evaluate_update(
            "egocaribautomapmarkers", "5.0.2", fixture_releases("egocaribautomapmarkers"), "1.22.0"
        )

        assert result.offered is not None
        assert result.offered.modversion == "5.0.3"
        assert result.offered_compatibility == "compatible"


class TestOfferSelection:
    def test_compatible_preferred_over_newer_not_verified(self) -> None:
        releases = [
            release("1.3.0", ["1.22.5"]),  # not_verified for 1.22.0
            release("1.2.0", ["1.22.0"]),  # compatible
            release("1.1.0", ["1.22.0"]),
        ]

        result = evaluate_update("demo", "1.1.0", releases, "1.22.0")

        assert result.offered is not None
        assert result.offered.modversion == "1.2.0"
        assert result.offered_compatibility == "compatible"

    def test_not_verified_offered_when_nothing_compatible(self) -> None:
        releases = [release("1.2.0", ["1.22.5"]), release("1.1.0", ["1.22.0"])]

        result = evaluate_update("demo", "1.1.0", releases, "1.22.0")

        assert result.offered is not None
        assert result.offered.modversion == "1.2.0"
        assert result.offered_compatibility == "not_verified"

    def test_only_incompatible_newer_releases_is_blocked(self) -> None:
        releases = [release("1.2.0", ["1.20.0"]), release("1.1.0", ["1.22.0"])]

        result = evaluate_update("demo", "1.1.0", releases, "1.22.0")

        assert result.status == "blocked"
        assert result.offered is None

    def test_no_server_installed_offers_newest_as_not_verified(self) -> None:
        result = evaluate_update("carryon", "1.14.1", fixture_releases("carryon"), "")

        assert result.offered is not None
        assert result.offered.modversion == "1.14.3"
        assert result.offered_compatibility == "not_verified"


class TestUnparsableVersions:
    def test_unparsable_installed_prerelease_is_unknown(self) -> None:
        releases = [release("2.0.0-rc.1", ["1.22.0"]), release("2.0.0a-pre.1", ["1.22.0"])]

        result = evaluate_update("demo", "2.0.0a-pre.1", releases, "1.22.0")

        assert result.status == "unknown"
        assert result.reason == "version_unparsable"

    def test_unparsable_newer_release_is_skipped(self) -> None:
        releases = [
            release("2.1.x-rc.1", ["1.22.0"]),
            release("2.0.0-rc.2", ["1.22.0"]),
            release("2.0.0-rc.1", ["1.22.0"]),
        ]

        result = evaluate_update("demo", "2.0.0-rc.1", releases, "1.22.0")

        assert result.offered is not None
        assert result.offered.modversion == "2.0.0-rc.2"



def installed(slug: str, version: str, name: str = "Demo") -> ModInfo:
    return ModInfo(
        filename=f"{slug}_{version}.zip",
        slug=slug,
        version=version,
        enabled=True,
        installed_at=datetime(2026, 1, 1, tzinfo=UTC),
        name=name,
    )


def record(
    releases: list[StoredRelease], *, found: bool = True, error: str | None = None
) -> StoredModRecord:
    return StoredModRecord(
        checked_at=datetime(2026, 11, 9, 12, 0, tzinfo=UTC),
        found=found,
        releases=releases,
        error=error,
    )


class TestModUpdateStore:
    def test_missing_file_starts_empty(self, tmp_path: Path) -> None:
        store = ModUpdateStore(tmp_path)

        assert store.get("carryon") is None
        assert store.last_full_check is None

    def test_data_survives_a_new_instance(self, tmp_path: Path) -> None:
        store = ModUpdateStore(tmp_path)
        store.set("carryon", record(fixture_releases("carryon")))
        store.last_full_check = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
        store.save()

        reloaded = ModUpdateStore(tmp_path)

        stored = reloaded.get("carryon")
        assert stored is not None
        assert [r.modversion for r in stored.releases] == [
            r.modversion for r in fixture_releases("carryon")
        ]
        assert reloaded.last_full_check == datetime(2026, 11, 9, 12, 0, tzinfo=UTC)

    def test_file_is_versioned_and_written_atomically(self, tmp_path: Path) -> None:
        store = ModUpdateStore(tmp_path)
        store.set("demo", record([]))
        store.save()

        data = json.loads((tmp_path / "mod-updates.json").read_text())
        assert data["schema_version"] == 1
        assert "demo" in data["mods"]
        assert not list(tmp_path.glob("*.tmp"))

    def test_corrupt_file_starts_empty(self, tmp_path: Path) -> None:
        (tmp_path / "mod-updates.json").write_text("{not json")

        store = ModUpdateStore(tmp_path)

        assert store.get("carryon") is None


class TestBuildStatusItems:
    def test_never_checked_mod_is_unknown(self, tmp_path: Path) -> None:
        store = ModUpdateStore(tmp_path)

        items = build_status_items([installed("carryon", "1.14.1")], store, "1.22.7")

        assert items[0].status == "unknown"
        assert items[0].reason == "not_checked"
        assert items[0].checked_at is None

    def test_mod_missing_from_database_is_unknown(self, tmp_path: Path) -> None:
        store = ModUpdateStore(tmp_path)
        store.set("gone", record([], found=False))

        items = build_status_items([installed("gone", "1.0.0")], store, "1.22.7")

        assert items[0].status == "unknown"
        assert items[0].reason == "not_in_database"

    def test_status_reflects_the_game_version_passed_at_read_time(self, tmp_path: Path) -> None:
        store = ModUpdateStore(tmp_path)
        store.set("carryon", record(fixture_releases("carryon")))
        mods = [installed("carryon", "1.14.1", name="Carry On")]

        on_server = build_status_items(mods, store, "1.22.7")[0]
        no_server = build_status_items(mods, store, "")[0]

        assert on_server.status == "update_available"
        assert on_server.name == "Carry On"
        assert on_server.installed_version == "1.14.1"
        assert on_server.offered_version == "1.14.3"
        assert on_server.offered_compatibility == "compatible"
        assert on_server.offered_prerelease is False
        assert no_server.offered_compatibility == "not_verified"

    def test_last_check_error_is_reported_with_kept_data(self, tmp_path: Path) -> None:
        store = ModUpdateStore(tmp_path)
        store.set("carryon", record(fixture_releases("carryon"), error="mod database unavailable"))

        item = build_status_items([installed("carryon", "2.0.0-pre.8")], store, "1.22.0")[0]

        assert item.error == "mod database unavailable"
        assert item.offered_version == "2.0.0-rc.1"
        assert item.offered_prerelease is True


MOD_URL = "https://mods.vintagestory.at/api/mod/{}"


def fixture_response(name: str) -> Response:
    return Response(200, json=json.loads((FIXTURES / f"mod_{name}.json").read_text()))


class FakeModSource:
    """Installed mods plus a real ModApiClient, standing in for ModService."""

    def __init__(self, mods: list[ModInfo], cache_dir: Path) -> None:
        self._mods = mods
        self.api_client = ModApiClient(cache_dir=cache_dir)

    def list_mods(self) -> list[ModInfo]:
        return self._mods


def make_service(
    tmp_path: Path, mods: list[ModInfo], game_version: str | None = "1.22.7"
) -> tuple[ModUpdateService, ModUpdateStore]:
    store = ModUpdateStore(tmp_path / "state")
    service = ModUpdateService(
        store=store,
        mod_source=FakeModSource(mods, tmp_path / "cache"),
        game_version_provider=lambda: game_version,
    )
    return service, store


class TestModUpdateCheck:
    @respx.mock
    @pytest.mark.asyncio
    async def test_check_stores_found_and_missing_mods(self, tmp_path: Path) -> None:
        respx.get(MOD_URL.format("carryon")).mock(return_value=fixture_response("carryon"))
        respx.get(MOD_URL.format("gone")).mock(return_value=fixture_response("not_found"))
        service, store = make_service(
            tmp_path, [installed("carryon", "1.14.1"), installed("gone", "1.0.0")]
        )

        summary = await service.check()

        assert (summary.checked, summary.failed, summary.failed_slugs) == (2, 0, [])
        assert store.last_full_check is not None
        statuses = {item.slug: item for item in service.get_status()}
        assert statuses["carryon"].offered_version == "1.14.3"
        assert statuses["gone"].reason == "not_in_database"
        reloaded = ModUpdateStore(tmp_path / "state")
        assert reloaded.get("carryon") is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_api_failure_keeps_previous_data_and_reports_it(self, tmp_path: Path) -> None:
        respx.get(MOD_URL.format("carryon")).mock(side_effect=httpx.ConnectError("down"))
        service, store = make_service(tmp_path, [installed("carryon", "1.14.1")])
        store.set("carryon", record(fixture_releases("carryon")))

        summary = await service.check()

        assert (summary.checked, summary.failed, summary.failed_slugs) == (1, 1, ["carryon"])
        kept = store.get("carryon")
        assert kept is not None
        assert len(kept.releases) == len(fixture_releases("carryon"))
        assert kept.error is not None
        item = service.get_status()[0]
        assert item.offered_version == "1.14.3"
        assert item.error is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_non_json_reply_is_a_failure_not_a_crash(self, tmp_path: Path) -> None:
        respx.get(MOD_URL.format("carryon")).mock(return_value=Response(200, text="<html>oops"))
        respx.get(MOD_URL.format("smithingplus")).mock(return_value=fixture_response("carryon"))
        service, _ = make_service(
            tmp_path, [installed("carryon", "1.14.1"), installed("smithingplus", "1.0.0")]
        )

        summary = await service.check()

        assert summary.failed_slugs == ["carryon"]
        assert summary.checked == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_lookup_clears_a_previous_error(self, tmp_path: Path) -> None:
        respx.get(MOD_URL.format("carryon")).mock(return_value=fixture_response("carryon"))
        service, store = make_service(tmp_path, [installed("carryon", "1.14.1")])
        store.set("carryon", record([], error="earlier failure"))

        await service.check()

        refreshed = store.get("carryon")
        assert refreshed is not None
        assert refreshed.error is None

    @pytest.mark.asyncio
    async def test_overlapping_check_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service, _ = make_service(tmp_path, [installed("carryon", "1.14.1")])
        started = asyncio.Event()
        release_lookup = asyncio.Event()

        async def slow_get_mod(slug: str) -> None:
            started.set()
            await release_lookup.wait()

        source = service._mod_source
        monkeypatch.setattr(source.api_client, "get_mod", slow_get_mod)
        first = asyncio.create_task(service.check())
        await started.wait()

        with pytest.raises(ModUpdateCheckInProgressError):
            await service.check()

        release_lookup.set()
        summary = await first
        assert summary.checked == 1

    def test_status_uses_installed_game_version_and_handles_no_server(self, tmp_path: Path) -> None:
        service, store = make_service(tmp_path, [installed("carryon", "1.14.1")], game_version=None)
        store.set("carryon", record(fixture_releases("carryon")))

        item = service.get_status()[0]

        assert service.game_version() == ""
        assert item.offered_compatibility == "not_verified"


MALFORMED_PAYLOADS: list[Any] = [
    {"statuscode": "200", "mod": [1, 2]},
]

# Story 17.1 (Epic 17 ADR-1): a wrong type becomes the field's default and a release
# that is not an object is dropped, so these payloads no longer fail the check.
NORMALIZED_PAYLOADS: list[tuple[Any, list[StoredRelease]]] = [
    (
        {
            "statuscode": "200",
            "mod": {"releases": [{"modversion": "1", "modidstr": "bad", "fileid": "abc"}]},
        },
        [StoredRelease(modversion="1", modidstr="bad", fileid=0, created="")],
    ),
    ({"statuscode": "200", "mod": {"releases": ["oops"]}}, []),
    ({"statuscode": "200", "mod": {"releases": {"a": 1}}}, []),
    (
        {"statuscode": "200", "mod": {"releases": [{"modversion": "1", "created": {"x": 1}}]}},
        [StoredRelease(modversion="1", modidstr="", created="")],
    ),
]


class TestCheckRobustness:
    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", MALFORMED_PAYLOADS)
    async def test_malformed_payload_fails_that_mod_only(
        self, tmp_path: Path, payload: Any
    ) -> None:
        respx.get(MOD_URL.format("bad")).mock(return_value=Response(200, json=payload))
        respx.get(MOD_URL.format("carryon")).mock(return_value=fixture_response("carryon"))
        service, _ = make_service(
            tmp_path, [installed("bad", "1"), installed("carryon", "1.14.1")]
        )

        summary = await service.check()

        assert summary.failed_slugs == ["bad"]
        assert ModUpdateStore(tmp_path / "state").get("carryon") is not None

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("payload", "expected"), NORMALIZED_PAYLOADS)
    async def test_payload_with_wrong_types_is_normalized(
        self, tmp_path: Path, payload: Any, expected: list[StoredRelease]
    ) -> None:
        respx.get(MOD_URL.format("bad")).mock(return_value=Response(200, json=payload))
        service, _ = make_service(tmp_path, [installed("bad", "1")])

        summary = await service.check()

        assert summary.failed_slugs == []
        stored = ModUpdateStore(tmp_path / "state").get("bad")
        assert stored is not None
        assert stored.found is True
        assert stored.error is None
        assert stored.releases == expected

    @respx.mock
    @pytest.mark.asyncio
    async def test_releases_without_a_file_are_stored(self, tmp_path: Path) -> None:
        """canjewelry: three releases have `"fileid": null`; stored with fileid 0 (Story 17.1)."""
        respx.get(MOD_URL.format("canjewelry")).mock(return_value=fixture_response("canjewelry"))
        service, _ = make_service(tmp_path, [installed("canjewelry", "0.8.2")])

        summary = await service.check()

        assert summary.failed == 0
        stored = ModUpdateStore(tmp_path / "state").get("canjewelry")
        assert stored is not None
        assert stored.error is None
        assert len(stored.releases) == 9
        no_file = [r.modversion for r in stored.releases if r.fileid == 0]
        assert no_file == ["0.2.20", "0.1.26", "0.2.0"]
        assert stored.releases[0].fileid == 138875

    @respx.mock
    @pytest.mark.asyncio
    async def test_entry_with_null_in_every_field_is_checked(self, tmp_path: Path) -> None:
        """An entry with null in every field the API reads does not fail the check (Story 17.1)."""
        mod: dict[str, Any] = {field: None for field in MOD_FIELDS}
        mod["releases"] = [{field: None for field in RELEASE_FIELDS}]
        mod["tags"] = [None, "Utility"]
        respx.get(MOD_URL.format("allnull")).mock(
            return_value=Response(200, json={"statuscode": "200", "mod": mod})
        )
        service, _ = make_service(tmp_path, [installed("allnull", "1")])

        summary = await service.check()

        assert summary.failed == 0
        stored = ModUpdateStore(tmp_path / "state").get("allnull")
        assert stored is not None
        assert stored.releases == [
            StoredRelease(modversion="", modidstr="", tags=[], fileid=0, filename="", created="")
        ]

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize("raw_body", [b"[1, 2]", b'{"statuscode": "200"}'])
    async def test_payload_rejected_inside_get_mod_fails_that_mod_only(
        self, tmp_path: Path, raw_body: bytes
    ) -> None:
        respx.get(MOD_URL.format("bad")).mock(return_value=Response(200, content=raw_body))
        respx.get(MOD_URL.format("carryon")).mock(return_value=fixture_response("carryon"))
        service, _ = make_service(
            tmp_path, [installed("bad", "1"), installed("carryon", "1.14.1")]
        )

        summary = await service.check()

        assert summary.failed_slugs == ["bad"]
        assert ModUpdateStore(tmp_path / "state").get("carryon") is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_unserializable_data_does_not_fail_the_check(self, tmp_path: Path) -> None:
        body = (
            b'{"statuscode": "200", "mod": {"releases": '
            b'[{"modversion": "1", "modidstr": "odd", "filename": "\\ud800.zip"}]}}'
        )
        respx.get(MOD_URL.format("odd")).mock(return_value=Response(200, content=body))
        service, _ = make_service(tmp_path, [installed("odd", "1")])

        summary = await service.check()

        assert summary.failed == 0
        assert service.get_status()[0].status == "up_to_date"

    @respx.mock
    @pytest.mark.asyncio
    async def test_failure_for_never_checked_mod_is_on_its_status(self, tmp_path: Path) -> None:
        route = respx.get(MOD_URL.format("carryon"))
        route.mock(side_effect=httpx.ConnectError("down"))
        service, _ = make_service(tmp_path, [installed("carryon", "1.14.1")])

        await service.check()

        item = service.get_status()[0]
        assert item.reason == "not_checked"
        assert item.error is not None
        reloaded = ModUpdateStore(tmp_path / "state")
        assert reloaded.lookup_error("carryon") is not None

        route.mock(return_value=fixture_response("carryon"))
        await service.check()

        assert service.get_status()[0].error is None
        assert service.store.lookup_error("carryon") is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_last_full_check_is_only_set_when_every_lookup_succeeds(
        self, tmp_path: Path
    ) -> None:
        good = respx.get(MOD_URL.format("carryon"))
        good.mock(return_value=fixture_response("carryon"))
        bad = respx.get(MOD_URL.format("broken"))
        bad.mock(side_effect=httpx.ConnectError("down"))
        service, store = make_service(
            tmp_path, [installed("carryon", "1.14.1"), installed("broken", "1.0.0")]
        )

        await service.check()
        assert store.last_full_check is None

        bad.mock(return_value=fixture_response("not_found"))
        await service.check()
        assert store.last_full_check is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_save_failure_still_returns_results(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        respx.get(MOD_URL.format("carryon")).mock(return_value=fixture_response("carryon"))
        service, store = make_service(tmp_path, [installed("carryon", "1.14.1")])

        def fail_save() -> None:
            raise PermissionError("read-only")

        monkeypatch.setattr(store, "save", fail_save)

        summary = await service.check()

        assert summary.failed == 0
        assert service.get_status()[0].offered_version == "1.14.3"

    @respx.mock
    @pytest.mark.asyncio
    async def test_records_for_uninstalled_mods_are_removed(self, tmp_path: Path) -> None:
        respx.get(MOD_URL.format("carryon")).mock(return_value=fixture_response("carryon"))
        service, store = make_service(tmp_path, [installed("carryon", "1.14.1")])
        store.set("removed", record([]))
        store.set_lookup_error("removed-too", "earlier failure")

        await service.check()

        reloaded = ModUpdateStore(tmp_path / "state")
        assert reloaded.get("removed") is None
        assert reloaded.lookup_error("removed-too") is None
        assert reloaded.get("carryon") is not None


def install_releases(name: str) -> list[ReleaseDict]:
    """The normalized releases `get_mod` hands an install, from a captured lookup."""
    mod = normalize_mod(json.loads((FIXTURES / f"mod_{name}.json").read_text())["mod"])
    assert mod is not None
    return mod["releases"]


class TestRecordInstall:
    """Story 17.4: an install stores the new mod's releases from its own lookup."""

    def test_stores_the_record_and_reports_the_status(self, tmp_path: Path) -> None:
        service, store = make_service(tmp_path, [installed("carryon", "1.14.1")])
        store.set_lookup_error("carryon", "mod database unavailable")

        service.record_install("carryon", install_releases("carryon"))

        item = service.get_status()[0]
        assert item.status == "update_available"
        assert item.offered_version == "1.14.3"
        assert item.reason is None
        assert item.error is None
        assert item.checked_at is not None
        assert store.lookup_error("carryon") is None
        reloaded = ModUpdateStore(tmp_path / "state").get("carryon")
        assert reloaded is not None
        assert reloaded.found is True
        assert len(reloaded.releases) == len(install_releases("carryon"))

    def test_same_record_as_a_check(self, tmp_path: Path) -> None:
        service, store = make_service(tmp_path, [installed("carryon", "1.14.1")])

        service.record_install("carryon", install_releases("carryon"))

        stored = store.get("carryon")
        assert stored is not None
        assert stored.releases == fixture_releases("carryon")

    def test_save_failure_is_logged_and_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_logs: StringIO
    ) -> None:
        service, store = make_service(tmp_path, [installed("carryon", "1.14.1")])

        def fail_save() -> None:
            raise OSError("disk full")

        monkeypatch.setattr(store, "save", fail_save)

        service.record_install("carryon", install_releases("carryon"))

        output = captured_logs.getvalue()
        assert "mod_update_record_after_install_failed" in output
        assert "disk full" in output
        assert "warning" in output
        # The record lives in memory until restart, as after a check whose save failed
        assert service.get_status()[0].status == "update_available"
        assert not (tmp_path / "state").exists()

    def test_bad_release_data_stores_nothing(
        self, tmp_path: Path, captured_logs: StringIO
    ) -> None:
        service, store = make_service(tmp_path, [installed("carryon", "1.14.1")])
        bad: list[ReleaseDict] = json.loads("[1]")

        service.record_install("carryon", bad)

        assert store.get("carryon") is None
        item = service.get_status()[0]
        assert (item.status, item.reason) == ("unknown", "not_checked")
        assert "mod_update_record_after_install_failed" in captured_logs.getvalue()


class TestRecordReleases:
    """Story 18.2 (Epic 18 ADR-5): a version change stores its own lookup's releases."""

    def test_stores_the_record_and_reports_a_real_status(self, tmp_path: Path) -> None:
        service, store = make_service(tmp_path, [installed("carryon", "1.14.3")])
        store.set("carryon", record([release("1.14.1", ["1.22.7"], modid="carryon")]))
        store.set_lookup_error("carryon", "mod database unavailable")
        assert service.get_status()[0].reason == "installed_release_not_listed"

        service.record_releases("carryon", fixture_releases("carryon"))

        item = service.get_status()[0]
        assert item.status != "unknown"
        assert item.reason is None
        assert item.checked_at is not None
        assert item.checked_at > datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
        assert store.lookup_error("carryon") is None
        reloaded = ModUpdateStore(tmp_path / "state").get("carryon")
        assert reloaded is not None
        assert reloaded.found is True
        assert reloaded.releases == fixture_releases("carryon")

    def test_save_failure_is_logged_and_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_logs: StringIO
    ) -> None:
        service, store = make_service(tmp_path, [installed("carryon", "1.14.3")])

        def fail_save() -> None:
            raise OSError("disk full")

        monkeypatch.setattr(store, "save", fail_save)

        service.record_releases("carryon", fixture_releases("carryon"))

        warning = next(
            line
            for line in captured_logs.getvalue().splitlines()
            if "mod_update_record_after_version_change_failed" in line
        )
        assert "warning" in warning
        assert "disk full" in warning
        assert "carryon" in warning
        assert "mod_update_record_after_install_failed" not in captured_logs.getvalue()
        assert not (tmp_path / "state").exists()


class ChangingModSource:
    """Installed mods that tests change while a check runs (Story 17.4)."""

    def __init__(self, mods: list[ModInfo], cache_dir: Path) -> None:
        self.mods = mods
        self.api_client = ModApiClient(cache_dir=cache_dir)

    def list_mods(self) -> list[ModInfo]:
        return list(self.mods)


class TestCheckWhileInstalling:
    """Story 17.4 AC 6: a check prunes against the installed mods when it ends."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_install_during_a_check_keeps_its_record(self, tmp_path: Path) -> None:
        source = ChangingModSource(
            [installed("carryon", "1.14.1"), installed("removed", "1.0.0")], tmp_path / "cache"
        )
        store = ModUpdateStore(tmp_path / "state")
        service = ModUpdateService(
            store=store, mod_source=source, game_version_provider=lambda: "1.22.7"
        )

        def install_and_remove_during_lookup(request: httpx.Request) -> Response:
            # An install finishes, and a removal happens, while the check awaits a lookup
            source.mods = [installed("carryon", "1.14.1"), installed("instruments", "1.2.2")]
            service.record_install("instruments", install_releases("instruments"))
            return fixture_response("carryon")

        respx.get(MOD_URL.format("carryon")).mock(side_effect=install_and_remove_during_lookup)
        respx.get(MOD_URL.format("removed")).mock(return_value=fixture_response("not_found"))

        await service.check()

        assert store.get("instruments") is not None
        assert store.get("removed") is None
        statuses = {item.slug: item for item in service.get_status()}
        assert statuses["instruments"].reason != "not_checked"
        assert statuses["instruments"].status != "unknown"
        reloaded = ModUpdateStore(tmp_path / "state")
        assert reloaded.get("instruments") is not None
        assert reloaded.get("removed") is None


class TestModelHardening:
    def test_lone_surrogates_are_replaced(self) -> None:
        stored = StoredRelease.from_api(
            {"modversion": "1.0\ud800", "modidstr": "x\udfff", "tags": ["1.22\ud800"]}
        )

        assert stored.modversion == "1.0\ufffd"
        assert stored.modidstr == "x\ufffd"
        assert stored.tags == ["1.22\ufffd"]
        stored.model_dump_json()

    def test_string_tags_are_one_tag(self) -> None:
        stored = StoredRelease.from_api({"modversion": "1", "modidstr": "x", "tags": "1.22.0"})

        assert stored.tags == ["1.22.0"]

    def test_compatibility_literal_matches_mod_api(self) -> None:
        assert get_args(Compatibility) == get_args(CompatibilityStatus)

