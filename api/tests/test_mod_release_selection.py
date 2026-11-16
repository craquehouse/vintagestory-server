"""Tests for release selection for install (Story 17.2, Epic 17 ADR-2)."""

import copy
import json
from pathlib import Path

import pytest

from vintagestory_api.models.moddb import ReleaseDict, normalize_mod
from vintagestory_api.services.mod_release_selection import (
    InstallSelection,
    has_file,
    is_prerelease,
    select_install_release,
)

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"


def _fixture_releases(name: str) -> list[ReleaseDict]:
    """A fixture's releases, normalized as `ModApiClient.get_mod` returns them."""
    payload = json.loads((FIXTURES / f"mod_{name}.json").read_text())
    mod = normalize_mod(payload["mod"])
    assert mod is not None
    return mod["releases"]


def _synthetic(modid: str, releases: list[tuple[str, int | None]]) -> list[ReleaseDict]:
    """One-mod-ID releases, newest first, as (modversion, fileid)."""
    return [
        {
            "releaseid": 100 + i,
            "modversion": version,
            "modidstr": modid,
            "filename": f"{modid}_{version}.zip" if fileid else "",
            "fileid": fileid,
            "downloads": 1,
            "tags": [],
            "created": "2026-01-01 00:00:00",
        }
        for i, (version, fileid) in enumerate(releases)
    ]


class TestHasFile:
    @pytest.mark.parametrize(
        ("fileid", "expected"), [(1, True), (138875, True), (0, False), (-1, False), (None, False)]
    )
    def test_only_a_positive_file_id_is_a_file(self, fileid: int | None, expected: bool) -> None:
        assert has_file(fileid) is expected


class TestIsPrerelease:
    def test_still_importable_from_mod_updates(self) -> None:
        from vintagestory_api.services.mod_updates import is_prerelease as from_updates

        assert from_updates is is_prerelease
        assert from_updates("2.0.0-rc.1") is True
        assert from_updates("1.14.3") is False


class TestSelectFromFixtures:
    @pytest.mark.parametrize(
        ("fixture", "slug", "version", "mod_id", "expected_version", "file_id"),
        [
            ("instruments", "instruments", None, "instruments", "1.2.2", 12840),
            ("instruments", "instruments", "1.0.1", "instruments", "1.0.1", 1002),
            ("instruments", "vsinstruments", None, "vsinstruments", "1.2.7", 18954),
            ("instruments", "vsinstrumentsbase", None, "vsinstrumentsbase", "2.0.7", 72936),
            ("instruments", "Instruments", None, "vsinstrumentsbase", "2.0.7", 72936),
            ("carryon", "carryon", None, "carryon", "1.14.3", 113014),
            ("carryon", "carryon", "2.0.0-rc.1", "carryon", "2.0.0-rc.1", 130071),
            (
                "egocaribautomapmarkers",
                "automapmarkers",
                None,
                "egocaribautomapmarkers",
                "5.0.3",
                90054,
            ),
            (
                "egocaribautomapmarkers",
                "egocaribresinmapmarkers",
                None,
                "egocaribresinmapmarkers",
                "1.0.0",
                1631,
            ),
            ("canjewelry", "canjewelry", None, "canjewelry", "0.8.2", 138875),
        ],
    )
    def test_selects(
        self,
        fixture: str,
        slug: str,
        version: str | None,
        mod_id: str,
        expected_version: str,
        file_id: int,
    ) -> None:
        selection = select_install_release(slug, _fixture_releases(fixture), version)

        assert selection.refusal is None
        assert selection.mod_id == mod_id
        assert selection.release is not None
        assert selection.release["modidstr"] == mod_id
        assert selection.release["modversion"] == expected_version
        assert selection.file_id == file_id

    @pytest.mark.parametrize(
        ("fixture", "slug", "version", "refusal"),
        [
            ("instruments", "instruments", "2.0.7", "version_not_found"),
            ("carryon", "carryon", "latest", "version_not_found"),
            ("canjewelry", "canjewelry", "0.2.20", "no_file"),
        ],
    )
    def test_refuses(self, fixture: str, slug: str, version: str, refusal: str) -> None:
        selection = select_install_release(slug, _fixture_releases(fixture), version)

        assert selection.refusal == refusal
        assert selection.mod_id == slug
        assert selection.release is None
        assert selection.file_id is None


class TestSelectSynthetic:
    def test_only_prereleases_picks_the_first(self) -> None:
        releases = _synthetic("demo", [("2.0.0-rc.2", 2), ("2.0.0-rc.1", 1)])

        selection = select_install_release("demo", releases)

        assert selection.release is not None
        assert selection.release["modversion"] == "2.0.0-rc.2"
        assert selection.file_id == 2

    def test_stable_with_a_file_wins_over_a_newer_prerelease(self) -> None:
        releases = _synthetic("demo", [("2.0.0", None), ("1.9.0-rc.1", 2), ("1.8.0", 1)])

        selection = select_install_release("demo", releases)

        assert selection.release is not None
        assert selection.release["modversion"] == "1.8.0"
        assert selection.file_id == 1

    def test_prerelease_without_a_file_is_skipped(self) -> None:
        releases = _synthetic("demo", [("1.0.0-rc.2", None), ("1.0.0-rc.1", 1)])

        selection = select_install_release("demo", releases)

        assert selection.release is not None
        assert selection.release["modversion"] == "1.0.0-rc.1"

    def test_no_release_with_a_file_is_refused(self) -> None:
        releases = _synthetic("demo", [("2.0.0", None), ("1.0.0", None)])

        selection = select_install_release("demo", releases)

        assert selection == InstallSelection(
            mod_id="demo", release=None, file_id=None, refusal="no_file"
        )

    def test_named_version_uses_the_listing_with_a_file(self) -> None:
        releases = _synthetic("demo", [("1.0.0", None), ("1.0.0", 7)])

        selection = select_install_release("demo", releases, "1.0.0")

        assert selection.refusal is None
        assert selection.release is releases[1]
        assert selection.file_id == 7

    def test_file_id_zero_is_no_file(self) -> None:
        releases = _synthetic("demo", [("1.0.0", 0)])

        selection = select_install_release("demo", releases)

        assert selection.refusal == "no_file"
        assert selection.release is None

    def test_no_releases(self) -> None:
        selection = select_install_release("x", [])

        assert selection == InstallSelection(
            mod_id="x", release=None, file_id=None, refusal="no_file"
        )

    def test_input_is_not_mutated(self) -> None:
        releases = _fixture_releases("instruments")
        before = copy.deepcopy(releases)

        select_install_release("instruments", releases)
        select_install_release("instruments", releases, "1.0.1")

        assert releases == before
