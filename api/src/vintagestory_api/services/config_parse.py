"""The one parser for config files (Epic 23 ADR-1).

Story 23.1: Configs with Comments Can Be Viewed (FR309, FR310)

VintageStory reads its configs with Newtonsoft.Json, which accepts comments and
trailing commas, so the config viewer reads `.json` files as JSON5 (`pyjson5`):
comments, trailing commas, single-quoted strings, unquoted keys and hexadecimal
numbers. The strict mode (standard JSON, `json.loads`) is for `serverconfig.json`,
which other services read and rewrite as strict JSON (ADR-1 decision 5).

A failed parse is a `ConfigParseError` whose `info` carries a message and, when it
is known, the 1-based line and column of the error. Infinity and NaN are refused in
both modes: a response holding them cannot be serialized (ADR-1 decision 4).
"""

import json
import math
import re
from dataclasses import dataclass
from typing import TypeGuard

import pyjson5

CONFIG_FILE_MAX_DEPTH = 200
"""How deeply parsed content may nest objects and arrays (Story 19.1, Epic 19 ADR-1).

Deeper content cannot be serialized into the response (about 254 levels at Story 19.1),
and the limit keeps the recursive redaction far below Python's recursion limit.
"""

TOO_DEEP_MESSAGE = f"Nested more than {CONFIG_FILE_MAX_DEPTH} levels deep"
NON_FINITE_MESSAGE = "Infinity and NaN cannot be shown"
VALUE_NOT_CONVERTED_MESSAGE = (
    "A value in the file could not be converted (for example, a number with too many digits)"
)

# pyjson5 puts the position only in its message: "... near 12, found U+0022" or
# "Unclosed b'string' starting near 7" (Story 23.1, Dev Notes "pyjson5 facts")
_NEAR = re.compile(r" (?:starting )?near (\d+)")
_BYTES_WORD = re.compile(r"b'([^']*)'")


@dataclass(frozen=True)
class ParseErrorInfo:
    """Why a config file did not parse, and where (1-based; None when unknown)."""

    message: str
    line: int | None
    column: int | None

    def to_dict(self) -> dict[str, object]:
        """The `parse_error` object of an API response."""
        return {"message": self.message, "line": self.line, "column": self.column}


class ConfigParseError(Exception):
    """Raised when a config file's text does not parse."""

    def __init__(self, info: ParseErrorInfo) -> None:
        self.info = info
        super().__init__(info.message)


def line_and_column(text: str, index: int) -> tuple[int, int]:
    """The 1-based line and column (in characters) of `text[index]`."""
    line = text.count("\n", 0, index) + 1
    column = index - (text.rfind("\n", 0, index) + 1) + 1
    return line, column


def _offset_from_message(message: str) -> int | None:
    """The 0-based character index named by pyjson5's `near N` (1-based), if any."""
    match = _NEAR.search(message)
    if match is None:
        return None
    return int(match.group(1)) - 1


def _clean_message(message: str) -> str:
    """pyjson5's message without the position and without Python byte reprs."""
    return _BYTES_WORD.sub(r"\1", _NEAR.sub("", message))


def _error_at(text: str, message: str, index: int | None) -> ConfigParseError:
    if index is None:
        return ConfigParseError(ParseErrorInfo(message, None, None))
    line, column = line_and_column(text, max(0, min(index, len(text))))
    return ConfigParseError(ParseErrorInfo(message, line, column))


def _is_json_object(value: object) -> TypeGuard[dict[str, object]]:
    """Whether parsed content is an object (both parsers build dicts with string keys)."""
    return isinstance(value, dict)


def _is_json_array(value: object) -> TypeGuard[list[object]]:
    """Whether parsed content is an array."""
    return isinstance(value, list)


def _check_values(value: object, *, check_depth: bool) -> None:
    """Refuse non-finite numbers and, when asked, nesting deeper than the limit.

    Iterative, so it cannot hit the recursion limit itself.
    """
    stack: list[tuple[object, int]] = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        children: list[object]
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ConfigParseError(ParseErrorInfo(NON_FINITE_MESSAGE, None, None))
            continue
        if _is_json_object(item):
            children = list(item.values())
        elif _is_json_array(item):
            children = item
        else:
            continue
        depth += 1
        if check_depth and depth > CONFIG_FILE_MAX_DEPTH:
            raise ConfigParseError(ParseErrorInfo(TOO_DEEP_MESSAGE, None, None))
        stack.extend((child, depth) for child in children)


def _parse_strict(text: str) -> object:
    try:
        value: object = json.loads(text)
    except json.JSONDecodeError as e:
        raise ConfigParseError(ParseErrorInfo(e.msg, e.lineno, e.colno)) from None
    except RecursionError:
        raise ConfigParseError(ParseErrorInfo(TOO_DEEP_MESSAGE, None, None)) from None
    except ValueError:
        # Python's limit on converting long integers; its message is not shown, so no
        # file content can reach the response (Story 19.1 review M2)
        raise ConfigParseError(ParseErrorInfo(VALUE_NOT_CONVERTED_MESSAGE, None, None)) from None
    _check_values(value, check_depth=True)
    return value


def _parse_json5(text: str) -> object:
    try:
        value: object = pyjson5.decode(text, maxdepth=CONFIG_FILE_MAX_DEPTH)
    except pyjson5.Json5NestingTooDeep:
        raise ConfigParseError(ParseErrorInfo(TOO_DEEP_MESSAGE, None, None)) from None
    except pyjson5.Json5DecoderException as e:
        message = e.message or "The file could not be parsed"
        raise _error_at(text, _clean_message(message), _offset_from_message(message)) from None
    _check_values(value, check_depth=False)
    return value


def parse_config_text(text: str, *, strict: bool = False) -> object:
    """Parse a config file's text: JSON5, or standard JSON when `strict`.

    Raises:
        ConfigParseError: If the text does not parse, nests more than
            CONFIG_FILE_MAX_DEPTH levels deep, or holds Infinity or NaN.
    """
    if strict:
        return _parse_strict(text)
    return _parse_json5(text)
