"""Normalization of VintageStory mod database data (Epic 17 ADR-1).

The mod database sometimes returns `null`, or a value of another type, for fields that
are usually set (for example a release with `"fileid": null`, or a `null` inside an
entry's `tags`). `ModApiClient` passes every entry through `normalize_mod` where it
enters the API, so callers can read each known field directly instead of defending
each read.

Rules (one table per object, `MOD_FIELDS` and `RELEASE_FIELDS`):

- A missing key, a `null` or a value of the wrong type becomes the field's default:
  `""` for text, `0` for counts, `[]` for lists, `None` for optional text.
  A `bool` is not an int.
- A release's `fileid` is the exception: anything but an int becomes `None`, which
  means the release has no downloadable file.
- Lists drop elements that are `null` or of the wrong type; a single string where a
  list of strings is expected becomes a one-element list.
- Unknown keys are copied unchanged. Inputs are never mutated, and normalizing a
  normalized dict changes nothing.

This module imports nothing from the rest of the package, so `models/` can use it.
"""

from collections.abc import Callable
from typing import Any, cast

# Type aliases for mod database objects (a mod entry or listing item, and a release)
ModDict = dict[str, Any]
ReleaseDict = dict[str, Any]

FieldNormalizer = Callable[[object], Any]


def _as_int(value: object) -> int:
    """An int (not a bool), else 0."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _as_optional_int(value: object) -> int | None:
    """An int (not a bool), else None."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _as_str(value: object) -> str:
    """A str, else ""."""
    return value if isinstance(value, str) else ""


def _as_optional_str(value: object) -> str | None:
    """A str, else None."""
    return value if isinstance(value, str) else None


def _as_str_list(value: object) -> list[str]:
    """The str elements of a list; a non-empty str is a list of one."""
    if isinstance(value, str):
        return [value] if value else []
    if not isinstance(value, list):
        return []
    return [item for item in cast(list[object], value) if isinstance(item, str)]


def _as_release_list(value: object) -> list[ReleaseDict]:
    """The object elements of a list, each normalized as a release."""
    if not isinstance(value, list):
        return []
    releases: list[ReleaseDict] = []
    for item in cast(list[object], value):
        release = normalize_release(item)
        if release is not None:
            releases.append(release)
    return releases


MOD_FIELDS: dict[str, FieldNormalizer] = {
    "modid": _as_int,
    "assetid": _as_int,
    "downloads": _as_int,
    "follows": _as_int,
    "trendingpoints": _as_int,
    "name": _as_str,
    "author": _as_str,
    "side": _as_str,
    "type": _as_str,
    "text": _as_optional_str,
    "summary": _as_optional_str,
    "urlalias": _as_optional_str,
    "logofilename": _as_optional_str,
    "logo": _as_optional_str,
    "homepageurl": _as_optional_str,
    "sourcecodeurl": _as_optional_str,
    "created": _as_optional_str,
    "lastreleased": _as_optional_str,
    "tags": _as_str_list,
    "modidstrs": _as_str_list,
    "releases": _as_release_list,
}
"""Fields of a mod entry (`/api/mod/{slug}`) or listing item (`/api/mods`)."""

RELEASE_FIELDS: dict[str, FieldNormalizer] = {
    "modversion": _as_str,
    "modidstr": _as_str,
    "filename": _as_str,
    "created": _as_str,
    "downloads": _as_int,
    "changelog": _as_optional_str,
    "tags": _as_str_list,
    "fileid": _as_optional_int,
}
"""Fields of a release. `fileid` is None when the release has no downloadable file."""


def _normalize(raw: object, fields: dict[str, FieldNormalizer]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    data = cast(dict[str, Any], raw)
    result = dict(data)
    for field, normalize in fields.items():
        result[field] = normalize(data.get(field))
    return result


def normalize_release(raw: object) -> ReleaseDict | None:
    """Normalize one release; None if it is not an object."""
    return _normalize(raw, RELEASE_FIELDS)


def normalize_mod(raw: object) -> ModDict | None:
    """Normalize one mod entry or listing item, with its releases; None if not an object."""
    return _normalize(raw, MOD_FIELDS)


def normalize_mod_list(raw: object) -> list[ModDict] | None:
    """Normalize a listing's `mods` array, dropping items that are not objects.

    Returns None when `raw` is not a list.
    """
    if not isinstance(raw, list):
        return None
    mods: list[ModDict] = []
    for item in cast(list[object], raw):
        mod = normalize_mod(item)
        if mod is not None:
            mods.append(mod)
    return mods
