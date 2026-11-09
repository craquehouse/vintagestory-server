"""Tests for mod update detection (Story 14.1)."""

import json
from pathlib import Path

import pytest

from vintagestory_api.models.mod_updates import StoredRelease
from vintagestory_api.services.mod_updates import (
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
