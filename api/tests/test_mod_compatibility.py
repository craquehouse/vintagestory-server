"""Tests for supported game versions per mod ID (Story 16.3, Epic 16 ADR-2)."""

import json
from pathlib import Path
from typing import Any

import pytest

from vintagestory_api.services.mod_compatibility import (
    SupportedRange,
    compare_game_versions,
    supported_game_versions,
)

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"


def _releases(name: str) -> list[dict[str, Any]]:
    payload = json.loads((FIXTURES / f"mod_{name}.json").read_text())
    return payload["mod"]["releases"]


def _release(modid: str, *tags: str) -> dict[str, Any]:
    return {"modidstr": modid, "modversion": "1.0.0", "tags": list(tags)}


class TestSupportedGameVersions:
    def test_playercorpse_highest_is_stable_not_its_release_candidates(self) -> None:
        result = supported_game_versions(_releases("playercorpse"), "playercorpse")

        assert result == SupportedRange(lowest="1.14.0", highest="1.21.1")

    @pytest.mark.parametrize(
        ("modid", "highest"),
        [
            ("instruments", "1.18.6"),
            ("vsinstruments", "1.19.3"),
            ("vsinstrumentsbase", "1.21.6"),
        ],
    )
    def test_instruments_each_mod_id_has_its_own_range(self, modid: str, highest: str) -> None:
        result = supported_game_versions(_releases("instruments"), modid)

        assert result is not None
        assert result.highest == highest

    def test_carryon_release_order_is_not_version_order(self) -> None:
        result = supported_game_versions(_releases("carryon"), "carryon")

        assert result == SupportedRange(lowest="1.22.0", highest="1.22.7")

    def test_unknown_mod_id_has_no_range(self) -> None:
        assert supported_game_versions(_releases("playercorpse"), "instruments") is None

    def test_pre_releases_used_only_without_stable_tags(self) -> None:
        releases = [_release("m", "1.23.0-rc.1", "1.23.0-rc.2"), _release("m", "1.22.0-pre.1")]

        result = supported_game_versions(releases, "m")

        assert result == SupportedRange(lowest="1.22.0-pre.1", highest="1.23.0-rc.1")

    def test_stable_preferred_even_when_a_pre_release_is_newer(self) -> None:
        releases = [_release("m", "1.23.0-rc.1"), _release("m", "1.22.7", "1.22.6")]

        result = supported_game_versions(releases, "m")

        assert result == SupportedRange(lowest="1.22.6", highest="1.22.7")

    def test_unparsable_tags_are_ignored(self) -> None:
        releases = [_release("m", "stable", "1.x", "", "v1.30.0", "1.21.3")]

        assert supported_game_versions(releases, "m") == SupportedRange("1.21.3", "1.21.3")

    def test_only_unparsable_tags_gives_no_range(self) -> None:
        assert supported_game_versions([_release("m", "latest")], "m") is None

    def test_trailing_zero_parts_compare_equal(self) -> None:
        releases = [_release("m", "1.21", "1.20.0"), _release("m", "1.21.0")]

        result = supported_game_versions(releases, "m")

        assert result is not None
        assert result.lowest == "1.20.0"
        # 1.21 and 1.21.0 are the same version; the first one seen is kept
        assert result.highest == "1.21"

    def test_missing_modidstr_and_tags_are_tolerated(self) -> None:
        releases: list[dict[str, Any]] = [{"modversion": "1.0.0"}, {"modidstr": "m", "tags": None}]

        assert supported_game_versions(releases, "m") is None


class TestCompareGameVersions:
    @pytest.mark.parametrize(
        ("left", "right", "expected"),
        [
            ("1.21.1", "1.22.7", -1),
            ("1.23.0", "1.22.7", 1),
            ("1.22.7", "1.22.7", 0),
            ("1.21", "1.21.0", 0),
            ("1.22.7-rc.1", "1.22.7", -1),
            ("1.22.7", "1.22.7-rc.1", 1),
            ("1.22.7-rc.1", "1.22.7-rc.2", 0),
            ("1.22.10", "1.22.9", 1),
        ],
    )
    def test_ordering(self, left: str, right: str, expected: int) -> None:
        assert compare_game_versions(left, right) == expected

    def test_unparsable_gives_none(self) -> None:
        assert compare_game_versions("stable", "1.22.7") is None
        assert compare_game_versions("1.22.7", "unknown") is None
