"""Tests for mod database normalization (Story 17.1, Epic 17 ADR-1)."""

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest

from vintagestory_api.models.moddb import (
    MOD_FIELDS,
    RELEASE_FIELDS,
    SCREENSHOT_FIELDS,
    normalize_mod,
    normalize_mod_list,
    normalize_release,
)

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"

MOD_INT_FIELDS = ["modid", "assetid", "downloads", "follows", "trendingpoints"]
MOD_STR_FIELDS = ["name", "author", "side", "type"]
MOD_OPTIONAL_STR_FIELDS = [
    "text",
    "summary",
    "urlalias",
    "logofilename",
    "logo",
    "homepageurl",
    "sourcecodeurl",
    "created",
    "lastreleased",
    "trailervideourl",
]
MOD_STR_LIST_FIELDS = ["tags", "modidstrs"]

RELEASE_STR_FIELDS = ["modversion", "modidstr", "filename", "created"]

# Values of the wrong type for each kind of field. A bool is not an int.
NOT_INT: list[object] = [None, "12", 1.5, True, [], {}]
NOT_STR: list[object] = [None, 12, 1.5, True, [], {}]
NOT_LIST: list[object] = [None, 12, 1.5, True, {}]


def load_fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / f"mod_{name}.json").read_text())
    return data["mod"]


def normalized_mod(raw: object) -> dict[str, Any]:
    result = normalize_mod(raw)
    assert result is not None
    return result


def normalized_release(raw: object) -> dict[str, Any]:
    result = normalize_release(raw)
    assert result is not None
    return result


class TestFieldTables:
    """The tables name every field the API reads."""

    def test_mod_fields(self) -> None:
        assert set(MOD_FIELDS) == {
            *MOD_INT_FIELDS,
            *MOD_STR_FIELDS,
            *MOD_OPTIONAL_STR_FIELDS,
            *MOD_STR_LIST_FIELDS,
            "releases",
            "screenshots",
        }

    def test_release_fields(self) -> None:
        assert set(RELEASE_FIELDS) == {
            *RELEASE_STR_FIELDS,
            "downloads",
            "changelog",
            "tags",
            "fileid",
        }

    def test_screenshot_fields(self) -> None:
        assert set(SCREENSHOT_FIELDS) == {
            "mainfile",
            "thumbnailfilename",
            "filename",
            "fileid",
            "created",
        }


class TestNormalizeModRules:
    """Each mod entry field gets its default when missing, null or of the wrong type."""

    def test_empty_entry_has_every_field_with_its_default(self) -> None:
        mod = normalized_mod({})
        assert set(mod) == set(MOD_FIELDS)
        for field in MOD_INT_FIELDS:
            assert mod[field] == 0
        for field in MOD_STR_FIELDS:
            assert mod[field] == ""
        for field in MOD_OPTIONAL_STR_FIELDS:
            assert mod[field] is None
        for field in MOD_STR_LIST_FIELDS:
            assert mod[field] == []
        assert mod["releases"] == []
        assert mod["screenshots"] == []

    @pytest.mark.parametrize("field", MOD_INT_FIELDS)
    @pytest.mark.parametrize("value", NOT_INT)
    def test_int_field_wrong_value_is_zero(self, field: str, value: object) -> None:
        assert normalized_mod({field: value})[field] == 0

    @pytest.mark.parametrize("field", MOD_INT_FIELDS)
    def test_int_field_kept(self, field: str) -> None:
        assert normalized_mod({field: 42})[field] == 42

    @pytest.mark.parametrize("field", MOD_STR_FIELDS)
    @pytest.mark.parametrize("value", NOT_STR)
    def test_str_field_wrong_value_is_empty(self, field: str, value: object) -> None:
        assert normalized_mod({field: value})[field] == ""

    @pytest.mark.parametrize("field", MOD_STR_FIELDS + MOD_OPTIONAL_STR_FIELDS)
    def test_str_field_kept(self, field: str) -> None:
        assert normalized_mod({field: " Some Text "})[field] == " Some Text "

    @pytest.mark.parametrize("field", MOD_OPTIONAL_STR_FIELDS)
    @pytest.mark.parametrize("value", NOT_STR)
    def test_optional_str_field_wrong_value_is_none(self, field: str, value: object) -> None:
        assert normalized_mod({field: value})[field] is None

    @pytest.mark.parametrize("field", MOD_STR_LIST_FIELDS)
    @pytest.mark.parametrize("value", NOT_LIST)
    def test_str_list_field_wrong_value_is_empty(self, field: str, value: object) -> None:
        assert normalized_mod({field: value})[field] == []

    @pytest.mark.parametrize("field", MOD_STR_LIST_FIELDS)
    def test_str_list_drops_null_and_non_string_elements(self, field: str) -> None:
        value = ["Utility", None, 3, True, ["x"], {"a": 1}, "Crafting"]
        assert normalized_mod({field: value})[field] == ["Utility", "Crafting"]

    @pytest.mark.parametrize("field", MOD_STR_LIST_FIELDS)
    def test_str_list_from_one_string(self, field: str) -> None:
        assert normalized_mod({field: "Utility"})[field] == ["Utility"]

    @pytest.mark.parametrize("value", NOT_LIST)
    def test_releases_wrong_value_is_empty(self, value: object) -> None:
        assert normalized_mod({"releases": value})["releases"] == []

    def test_releases_drops_non_objects_and_normalizes_the_rest(self) -> None:
        mod = normalized_mod(
            {"releases": [None, "oops", 3, ["a"], {"modversion": "1.0.0", "fileid": None}]}
        )
        assert len(mod["releases"]) == 1
        assert mod["releases"][0] == normalized_release({"modversion": "1.0.0", "fileid": None})

    @pytest.mark.parametrize("raw", [None, "mod", 3, True, [1, 2], ["a"]])
    def test_non_object_entry_is_none(self, raw: object) -> None:
        assert normalize_mod(raw) is None


class TestNormalizeReleaseRules:
    """Each release field gets its default when missing, null or of the wrong type."""

    def test_empty_release_has_every_field_with_its_default(self) -> None:
        release = normalized_release({})
        assert release == {
            "modversion": "",
            "modidstr": "",
            "filename": "",
            "created": "",
            "downloads": 0,
            "changelog": None,
            "tags": [],
            "fileid": None,
        }

    @pytest.mark.parametrize("field", RELEASE_STR_FIELDS)
    @pytest.mark.parametrize("value", NOT_STR)
    def test_str_field_wrong_value_is_empty(self, field: str, value: object) -> None:
        assert normalized_release({field: value})[field] == ""

    @pytest.mark.parametrize("field", [*RELEASE_STR_FIELDS, "changelog"])
    def test_str_field_kept(self, field: str) -> None:
        assert normalized_release({field: "<p>text</p>"})[field] == "<p>text</p>"

    @pytest.mark.parametrize("value", NOT_INT)
    def test_downloads_wrong_value_is_zero(self, value: object) -> None:
        assert normalized_release({"downloads": value})["downloads"] == 0

    def test_downloads_kept(self) -> None:
        assert normalized_release({"downloads": 7})["downloads"] == 7

    @pytest.mark.parametrize("value", NOT_STR)
    def test_changelog_wrong_value_is_none(self, value: object) -> None:
        assert normalized_release({"changelog": value})["changelog"] is None

    @pytest.mark.parametrize("value", NOT_LIST)
    def test_tags_wrong_value_is_empty(self, value: object) -> None:
        assert normalized_release({"tags": value})["tags"] == []

    def test_tags_drop_null_and_non_string_elements(self) -> None:
        assert normalized_release({"tags": ["1.21.0", None, 1.21, "1.22.0"]})["tags"] == [
            "1.21.0",
            "1.22.0",
        ]

    def test_tags_from_one_string(self) -> None:
        assert normalized_release({"tags": "1.21.0"})["tags"] == ["1.21.0"]

    @pytest.mark.parametrize("value", NOT_INT)
    def test_fileid_wrong_value_is_none(self, value: object) -> None:
        assert normalized_release({"fileid": value})["fileid"] is None

    def test_fileid_missing_is_none(self) -> None:
        assert normalized_release({"modversion": "1.0.0"})["fileid"] is None

    def test_fileid_int_kept(self) -> None:
        assert normalized_release({"fileid": 59176})["fileid"] == 59176

    def test_fileid_zero_kept(self) -> None:
        assert normalized_release({"fileid": 0})["fileid"] == 0

    @pytest.mark.parametrize("raw", [None, "release", 3, False, [1], ["a"]])
    def test_non_object_release_is_none(self, raw: object) -> None:
        assert normalize_release(raw) is None


class TestNormalizeScreenshots:
    """A mod entry's `screenshots` (Story 18.1): types only, no URL check."""

    EMPTY_SCREENSHOT: dict[str, Any] = {
        "mainfile": None,
        "thumbnailfilename": None,
        "filename": "",
        "fileid": None,
        "created": None,
    }

    VALID: dict[str, Any] = {
        "fileid": 7,
        "mainfile": "https://moddbcdn.vintagestory.at/a_1.jpg",
        "filename": "Timeline 1.jpg",
        "thumbnailfilename": "https://moddbcdn.vintagestory.at/a_1_55_60.jpg",
        "created": "2025-01-01 10:00:00",
    }

    @pytest.mark.parametrize("value", [None, "x", 3, True, {}])
    def test_wrong_value_is_empty(self, value: object) -> None:
        assert normalized_mod({"screenshots": value})["screenshots"] == []

    def test_drops_non_objects(self) -> None:
        screenshots = normalized_mod({"screenshots": [None, "x", 3, {"mainfile": "u"}]})[
            "screenshots"
        ]
        assert screenshots == [{**self.EMPTY_SCREENSHOT, "mainfile": "u"}]

    def test_empty_object_has_every_field_with_its_default(self) -> None:
        empty: dict[str, Any] = {}
        assert normalized_mod({"screenshots": [empty]})["screenshots"] == [self.EMPTY_SCREENSHOT]

    @pytest.mark.parametrize(
        ("field", "value", "expected"),
        [
            ("mainfile", 5, None),
            ("thumbnailfilename", [], None),
            ("filename", None, ""),
            ("fileid", "7", None),
            ("fileid", True, None),
            ("created", 5, None),
        ],
    )
    def test_wrong_type_per_field(self, field: str, value: object, expected: object) -> None:
        screenshot = normalized_mod({"screenshots": [{**self.VALID, field: value}]})["screenshots"][
            0
        ]
        assert screenshot[field] == expected

    def test_valid_item_unchanged(self) -> None:
        assert normalized_mod({"screenshots": [self.VALID]})["screenshots"] == [self.VALID]

    def test_unknown_key_kept(self) -> None:
        screenshot = normalized_mod({"screenshots": [{**self.VALID, "extra": 1}]})["screenshots"][0]
        assert screenshot["extra"] == 1

    def test_input_not_mutated(self) -> None:
        raw: dict[str, Any] = {"screenshots": [None, {"mainfile": 5}, dict(self.VALID)]}
        before = copy.deepcopy(raw)
        normalize_mod(raw)
        assert raw == before

    def test_idempotent(self) -> None:
        once = normalized_mod({"screenshots": [None, {"filename": None}, self.VALID]})
        assert normalize_mod(once) == once


class TestNormalizeModList:
    """A listing's `mods` array."""

    @pytest.mark.parametrize("raw", [None, "mods", 3, True, {"a": 1}])
    def test_non_list_is_none(self, raw: object) -> None:
        assert normalize_mod_list(raw) is None

    def test_empty_list(self) -> None:
        assert normalize_mod_list([]) == []

    def test_drops_non_object_items(self) -> None:
        result = normalize_mod_list([None, {"name": "A"}, "oops", 3, [1], {"name": "B"}])
        assert result is not None
        assert [m["name"] for m in result] == ["A", "B"]
        assert result[0] == normalized_mod({"name": "A"})


class TestNormalizeProperties:
    """Unknown keys, mutation and idempotence."""

    def test_unknown_keys_kept(self) -> None:
        raw: dict[str, Any] = {
            "comments": 3,
            "wikiurl": "https://example.com",
            "releases": [{"releaseid": 9, "mainfile": "", "extra": None}],
        }
        mod = normalized_mod(raw)
        assert mod["comments"] == 3
        assert mod["wikiurl"] == "https://example.com"
        release = mod["releases"][0]
        assert release["releaseid"] == 9
        assert release["mainfile"] == ""
        assert "extra" in release and release["extra"] is None

    def test_input_not_mutated(self) -> None:
        raw: dict[str, Any] = {
            "name": None,
            "tags": ["Utility", None],
            "releases": [{"fileid": None, "tags": [None, "1.21.0"]}, "oops"],
        }
        before = copy.deepcopy(raw)
        normalize_mod(raw)
        normalize_mod_list([raw])
        normalize_release(raw["releases"][0])
        assert raw == before

    def test_result_shares_no_list_with_input(self) -> None:
        raw: dict[str, Any] = {"tags": ["Utility"], "releases": [{"tags": ["1.21.0"]}]}
        mod = normalized_mod(raw)
        mod["tags"].append("X")
        mod["releases"][0]["tags"].append("X")
        assert raw == {"tags": ["Utility"], "releases": [{"tags": ["1.21.0"]}]}

    def test_mod_idempotent(self) -> None:
        raw: dict[str, Any] = {
            **{field: None for field in MOD_FIELDS},
            "tags": "Utility",
            "releases": [{field: None for field in RELEASE_FIELDS}, None],
        }
        once = normalized_mod(raw)
        assert normalize_mod(once) == once

    def test_release_idempotent(self) -> None:
        once = normalized_release({"fileid": None, "tags": "1.21.0", "downloads": True})
        assert normalize_release(once) == once

    def test_mod_list_idempotent(self) -> None:
        once = normalize_mod_list([{"tags": [None, "QoL"]}, None])
        assert once is not None
        assert normalize_mod_list(once) == once


def _assert_valid_values_unchanged(
    raw: dict[str, Any], normalized: dict[str, Any], fields: dict[str, Any]
) -> None:
    """Every key of `raw` other than `releases` keeps its value unless it was invalid."""
    for key, value in raw.items():
        if key == "releases":
            continue
        if key not in fields:
            assert normalized[key] == value, key
            continue
        if isinstance(value, list):
            items = cast(list[object], value)
            assert normalized[key] == [v for v in items if isinstance(v, str)], key
        elif value is None:
            continue
        else:
            assert normalized[key] == value, key


class TestFixtures:
    """Captured mod database entries normalize without changing a valid value."""

    @pytest.mark.parametrize(
        "name", ["canjewelry", "carryon", "instruments", "egocaribautomapmarkers", "playercorpse"]
    )
    def test_fixture_values_kept(self, name: str) -> None:
        raw = load_fixture(name)
        mod = normalized_mod(raw)
        _assert_valid_values_unchanged(raw, mod, MOD_FIELDS)
        assert len(mod["releases"]) == len(raw["releases"])
        for raw_release, release in zip(raw["releases"], mod["releases"], strict=True):
            _assert_valid_values_unchanged(raw_release, release, RELEASE_FIELDS)
            assert release["fileid"] == raw_release["fileid"]

    def test_canjewelry_nulls(self) -> None:
        mod = normalized_mod(load_fixture("canjewelry"))
        assert mod["tags"] == ["Utility", "Cosmetics", "Crafting"]
        no_file = [r["modversion"] for r in mod["releases"] if r["fileid"] is None]
        assert no_file == ["0.2.20", "0.1.26", "0.2.0"]
        for release in mod["releases"]:
            if release["fileid"] is None:
                assert release["filename"] == ""
            else:
                assert isinstance(release["fileid"], int)
        changelogs = {r["modversion"]: r["changelog"] for r in mod["releases"]}
        assert changelogs["0.3.7"] is None
        assert changelogs["0.8.2"] == "<ul><li>recipe rotation fix</li></ul>"
