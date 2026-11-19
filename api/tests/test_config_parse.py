"""Tests for the config file parser.

Story 23.1: Configs with Comments Can Be Viewed (FR309, FR310; Epic 23 ADR-1)
"""

import math

import pyjson5
import pytest


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
