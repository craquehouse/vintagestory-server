"""Tests for the config file parser.

Story 23.1: Configs with Comments Can Be Viewed (FR309, FR310; Epic 23 ADR-1)
"""

import math

import pyjson5
import pytest

from vintagestory_api.services.config_parse import (
    CONFIG_FILE_MAX_DEPTH,
    ConfigParseError,
    ParseErrorInfo,
    line_and_column,
    parse_config_text,
)


class TestPyjson5Facts:
    """What the parser relies on in pyjson5 2.x (Story 23.1 Task 1, Dev Notes "pyjson5 facts")."""

    def test_position_is_only_in_the_message_as_a_one_based_character_position(self) -> None:
        # The `"` of "b" is at index 9, so its 1-based position is 10
        with pytest.raises(pyjson5.Json5DecoderException) as exc_info:
            pyjson5.decode('{"a": 1\n "b": 2}')

        assert exc_info.value.message is not None
        assert " near 10," in exc_info.value.message

    def test_nesting_over_maxdepth_is_its_own_exception(self) -> None:
        with pytest.raises(pyjson5.Json5NestingTooDeep):
            pyjson5.decode("[" * 201 + "]" * 201, maxdepth=200)

    def test_infinity_and_nan_are_decoded_as_floats(self) -> None:
        infinity = pyjson5.decode("Infinity")
        nan = pyjson5.decode("NaN")

        assert isinstance(infinity, float)
        assert isinstance(nan, float)
        assert math.isinf(infinity)
        assert math.isnan(nan)


# Epic 23 ADR-9 decision 4: the shape of ModConfig/seasonalflowers.json, written by the test
COMMENTED = """{
  // How often flowers bloom
  "BloomChance": 0.5, /* a block comment */
  "Homepage": "http://example.com//path",
  "Seasons": [null, "spring", null,],
  "Enabled": true, // a comment after the last property
}
"""


class TestLenient:
    """parse_config_text without strict: JSON5 (ADR-1 decisions 1 to 4)."""

    def test_comments_trailing_commas_and_nulls(self) -> None:
        assert parse_config_text(COMMENTED) == {
            "BloomChance": 0.5,
            "Homepage": "http://example.com//path",
            "Seasons": [None, "spring", None],
            "Enabled": True,
        }

    def test_single_quotes_unquoted_keys_and_hex(self) -> None:
        assert parse_config_text("{name: 'x', 'n': 0x1F}") == {"name": "x", "n": 31}

    def test_valid_json_parses(self) -> None:
        assert parse_config_text('{"a": [1, 2.5, "s", false]}') == {"a": [1, 2.5, "s", False]}

    @pytest.mark.parametrize(
        ("text", "line", "column"),
        [
            ('{\n  "a": 1\n  "b": 2\n}', 3, 3),
            ('{\r\n  "a": 1\r\n  "b": 2\r\n}', 3, 3),
            ('{\n  "é€😀": 1\n  "b": 2\n}', 3, 3),
        ],
    )
    def test_missing_comma_has_line_and_column(self, text: str, line: int, column: int) -> None:
        with pytest.raises(ConfigParseError) as exc_info:
            parse_config_text(text)

        info = exc_info.value.info
        assert (info.line, info.column) == (line, column)
        assert "near" not in info.message
        assert "b'" not in info.message
        assert info.message == str(exc_info.value)

    @pytest.mark.parametrize("text", ["", "   ", '{"a": 1} x', '{"a": "abc'])
    def test_other_errors_are_parse_errors(self, text: str) -> None:
        with pytest.raises(ConfigParseError) as exc_info:
            parse_config_text(text)

        assert exc_info.value.info.message

    @pytest.mark.parametrize("levels", [CONFIG_FILE_MAX_DEPTH + 1, 100_000])
    def test_too_deep(self, levels: int) -> None:
        with pytest.raises(ConfigParseError) as exc_info:
            parse_config_text("[" * levels + "]" * levels)

        info = exc_info.value.info
        assert info.message == f"Nested more than {CONFIG_FILE_MAX_DEPTH} levels deep"
        assert (info.line, info.column) == (None, None)

    def test_nesting_up_to_the_limit_parses(self) -> None:
        depth = CONFIG_FILE_MAX_DEPTH
        assert parse_config_text("[" * depth + "]" * depth) is not None

    @pytest.mark.parametrize(
        "text", ['{"a": Infinity}', '{"a": -Infinity}', "NaN", '{"a": [1, [NaN]]}']
    )
    def test_infinity_and_nan_are_refused(self, text: str) -> None:
        with pytest.raises(ConfigParseError) as exc_info:
            parse_config_text(text)

        info = exc_info.value.info
        assert info.message == "Infinity and NaN cannot be shown"
        assert (info.line, info.column) == (None, None)


class TestStrict:
    """parse_config_text(strict=True): standard JSON (ADR-1 decision 5)."""

    def test_valid_json_parses(self) -> None:
        assert parse_config_text('{"Port": 42420}', strict=True) == {"Port": 42420}

    def test_comments_are_refused_with_line_and_column(self) -> None:
        with pytest.raises(ConfigParseError) as exc_info:
            parse_config_text('{\n  // no\n  "a": 1\n}', strict=True)

        info = exc_info.value.info
        assert (info.line, info.column) == (2, 3)

    def test_trailing_comma_is_refused(self) -> None:
        with pytest.raises(ConfigParseError):
            parse_config_text('{"a": 1,}', strict=True)

    def test_too_deep(self) -> None:
        levels = CONFIG_FILE_MAX_DEPTH + 1
        with pytest.raises(ConfigParseError) as exc_info:
            parse_config_text("[" * levels + "]" * levels, strict=True)

        assert exc_info.value.info.message == (
            f"Nested more than {CONFIG_FILE_MAX_DEPTH} levels deep"
        )

    def test_far_too_deep_is_not_a_recursion_error(self) -> None:
        levels = 100_000
        with pytest.raises(ConfigParseError) as exc_info:
            parse_config_text("[" * levels + "]" * levels, strict=True)

        assert exc_info.value.info.message == (
            f"Nested more than {CONFIG_FILE_MAX_DEPTH} levels deep"
        )

    def test_integer_too_long_has_a_fixed_message(self) -> None:
        with pytest.raises(ConfigParseError) as exc_info:
            parse_config_text('{"n": ' + "1" * 5000 + "}", strict=True)

        assert "1" * 50 not in exc_info.value.info.message
        assert exc_info.value.info.line is None

    def test_nan_is_refused(self) -> None:
        with pytest.raises(ConfigParseError) as exc_info:
            parse_config_text('{"a": NaN}', strict=True)

        assert exc_info.value.info.message == "Infinity and NaN cannot be shown"


class TestLineAndColumn:
    @pytest.mark.parametrize(
        ("text", "index", "expected"),
        [
            ("abc", 0, (1, 1)),
            ("abc", 2, (1, 3)),
            ("a\nbc", 2, (2, 1)),
            ("a\r\nbc", 3, (2, 1)),
            ("a\nbc", 4, (2, 3)),
        ],
    )
    def test_positions(self, text: str, index: int, expected: tuple[int, int]) -> None:
        assert line_and_column(text, index) == expected

    def test_to_dict(self) -> None:
        assert ParseErrorInfo("m", 1, 2).to_dict() == {"message": "m", "line": 1, "column": 2}
