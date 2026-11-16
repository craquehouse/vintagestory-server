"""Which mod database media URLs the API passes on (Epic 18 ADR-1 and ADR-2).

A URL from the mod database is author-controlled data that the web puts into `src`
and `href`. `models/moddb.py` checks types; this module is the one place that
decides which URLs are allowed. Anything else becomes None and never fails a lookup.

Rules:

- An image URL is kept unchanged only when it starts with `https://`, contains no
  ASCII control character, space or backslash, parses, and its whole `netloc` is a
  host in `MOD_MEDIA_HOSTS` (compared without case). Comparing the `netloc` rejects
  user info, any port (also an empty one) and a trailing dot.
- A trailer URL is never passed on: the 11-character video ID is taken from a
  YouTube `/watch?v=<id>`, `/embed/<id>` or `youtu.be/<id>` URL on `YOUTUBE_HOSTS`
  and the link is rebuilt as `TRAILER_WATCH_URL` + ID.

Pure helpers: no I/O.
"""

import re
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

TRAILER_WATCH_URL = "https://www.youtube.com/watch?v="
"""Where the trailer link points; the video ID is appended."""

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


def trailer_watch_url(url: str | None) -> str | None:
    """`https://www.youtube.com/watch?v=<id>` for a YouTube video URL, else None."""
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
    return f"{TRAILER_WATCH_URL}{video_id}"


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
