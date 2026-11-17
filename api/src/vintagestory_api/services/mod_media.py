"""Which mod database URLs the API passes on (Epic 18 ADR-1, ADR-2; Epic 19 ADR-12).

A URL from the mod database is author-controlled data that the web puts into `src`
and `href`. `models/moddb.py` checks types; this module is the one place that
decides which URLs are allowed. Anything else becomes None and never fails a lookup.

Rules:

- An image URL (a screenshot, its thumbnail or the mod's logo) is kept unchanged only
  when it starts with `https://`, contains no ASCII control character, space or
  backslash, parses, and its whole `netloc` is a host in `MOD_MEDIA_HOSTS` (compared
  without case). Comparing the `netloc` rejects user info, any port (also an empty
  one) and a trailing dot.
- A link URL (the mod's homepage or source code) is kept unchanged only when it starts
  with `https://`, is at most `MAX_LINK_LENGTH` characters, contains no ASCII control
  character, backslash or whitespace of any kind, parses with a host, has no user info
  and, when it has a port, a number from 1 to 65535. Any host is allowed. An empty
  value is None.
- A trailer URL is never passed on: the 11-character video ID is taken from a
  YouTube `/watch?v=<id>`, `/embed/<id>` or `youtu.be/<id>` URL on `YOUTUBE_HOSTS`
  and the link is rebuilt as `TRAILER_EMBED_URL` + ID, on the privacy-enhanced
  youtube-nocookie.com domain (the maintainer's choice; its `/watch` path is a 404).

Pure helpers: no I/O apart from the debug log of a dropped URL, which never holds the URL.
"""

import re
from collections.abc import Callable
from typing import Any
from urllib.parse import SplitResult, parse_qs, urlsplit

import structlog

from vintagestory_api.models.mods import ModScreenshot

logger = structlog.get_logger()

MOD_MEDIA_HOSTS = frozenset({"moddbcdn.vintagestory.at"})
"""Hosts a screenshot's image or thumbnail URL may be on."""

YOUTUBE_HOSTS = frozenset(
    {
        "www.youtube-nocookie.com",
        "youtube-nocookie.com",
        "www.youtube.com",
        "youtube.com",
        "m.youtube.com",
        "youtu.be",
    }
)
"""Hosts a trailer URL may be on."""

TRAILER_EMBED_URL = "https://www.youtube-nocookie.com/embed/"
"""Where the trailer link points; the video ID is appended."""

MAX_LINK_LENGTH = 2048
"""Longest homepage or source URL the API passes on, in characters (Epic 19 ADR-12)."""

_UNSAFE = re.compile(r"[\x00-\x20\x7f\\]")  # control characters, space, backslash
_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def _https_parts(url: str | None, hosts: frozenset[str]) -> SplitResult | None:
    if not url or _UNSAFE.search(url) or not url.startswith("https://"):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    return parts if parts.netloc.lower() in hosts else None


def mod_image_url(url: str | None) -> str | None:
    """`url` unchanged when it is an https URL on the mod database CDN, else None."""
    return url if _https_parts(url, MOD_MEDIA_HOSTS) is not None else None


def external_link_url(url: str | None) -> str | None:
    """`url` unchanged when it is a well-formed https URL with a host, else None (ADR-12)."""
    if (
        not url
        or len(url) > MAX_LINK_LENGTH
        or _UNSAFE.search(url)
        or any(ch.isspace() for ch in url)
        or not url.startswith("https://")
    ):
        return None
    try:
        parts = urlsplit(url)
        port = parts.port  # raises ValueError for a port that is not a number in range
    except ValueError:
        return None
    if not parts.hostname or "@" in parts.netloc or port == 0:
        return None
    return url


def checked_url(
    url: str | None, rule: Callable[[str | None], str | None], *, slug: str, field: str
) -> str | None:
    """`rule(url)`; a non-empty URL the rule drops is logged at debug level, without the URL.

    The URL is author-controlled and can be long, so the log names only the mod and the
    response field (Epic 19 ADR-12 decision 6). Empty and missing values are the normal
    case for links and are not logged.
    """
    kept = rule(url)
    if kept is None and url:
        logger.debug("mod_url_dropped", slug=slug, field=field)
    return kept


def trailer_link_url(url: str | None) -> str | None:
    """`https://www.youtube-nocookie.com/embed/<id>` for a YouTube video URL, else None."""
    parts = _https_parts(url, YOUTUBE_HOSTS)
    if parts is None:
        return None
    if parts.netloc.lower() == "youtu.be":
        video_id = parts.path.removeprefix("/")
    elif parts.path == "/watch":
        video_id = (parse_qs(parts.query).get("v") or [""])[0]
    elif parts.path.startswith("/embed/"):
        video_id = parts.path.removeprefix("/embed/")
    else:
        return None
    if not _VIDEO_ID.fullmatch(video_id):
        return None
    return f"{TRAILER_EMBED_URL}{video_id}"


def build_screenshots(screenshots: list[dict[str, Any]], slug: str) -> list[ModScreenshot]:
    """The entry's screenshots whose image URL is allowed, in order (ADR-1 decision 3).

    A screenshot whose thumbnail is missing or not allowed uses its image URL as the
    thumbnail. A dropped screenshot is logged at debug level without its URL.
    """
    result: list[ModScreenshot] = []
    for index, screenshot in enumerate(screenshots):
        image_url = mod_image_url(screenshot["mainfile"])
        if image_url is None:
            logger.debug("mod_screenshot_dropped", slug=slug, index=index)
            continue
        result.append(
            ModScreenshot(
                image_url=image_url,
                thumbnail_url=mod_image_url(screenshot["thumbnailfilename"]) or image_url,
                filename=screenshot["filename"],
            )
        )
    return result
