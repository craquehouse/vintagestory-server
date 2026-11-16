"""Tests for the mod media URL rules (Story 18.1, Epic 18 ADR-1 and ADR-2)."""

import re
from io import StringIO
from typing import Any

import pytest

from vintagestory_api.models.mods import ModScreenshot
from vintagestory_api.services.mod_media import (
    MOD_MEDIA_HOSTS,
    YOUTUBE_HOSTS,
    build_screenshots,
    mod_image_url,
    trailer_link_url,
)

EMBED_URL = "https://www.youtube-nocookie.com/embed/mJHZH_sThDM"


class TestHosts:
    def test_mod_media_hosts(self) -> None:
        assert MOD_MEDIA_HOSTS == {"moddbcdn.vintagestory.at"}

    def test_youtube_hosts(self) -> None:
        assert YOUTUBE_HOSTS == {
            "www.youtube-nocookie.com",
            "youtube-nocookie.com",
            "www.youtube.com",
            "youtube.com",
            "m.youtube.com",
            "youtu.be",
        }


class TestModImageUrl:
    """`mod_image_url` keeps only https URLs on the mod database CDN, unchanged."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://moddbcdn.vintagestory.at/a_55_60.jpg",
            "https://MODDBCDN.vintagestory.at/a.jpg",
            "https://moddbcdn.vintagestory.at/Timeline+1_01_02_04_26_abc.jpg",
            "https://moddbcdn.vintagestory.at/a.jpg?v=2",
        ],
    )
    def test_kept_unchanged(self, url: str) -> None:
        assert mod_image_url(url) == url

    @pytest.mark.parametrize(
        "url",
        [
            None,
            "",
            "http://moddbcdn.vintagestory.at/a.jpg",
            "HTTPS://moddbcdn.vintagestory.at/a.jpg",
            "//moddbcdn.vintagestory.at/a.jpg",
            "https://i.imgur.com/a.png",
            "https://moddbcdn.vintagestory.at.evil.example/a",
            "https://evil.example/moddbcdn.vintagestory.at",
            "https://user@moddbcdn.vintagestory.at/a",
            "https://moddbcdn.vintagestory.at@evil.example/a",
            "https://moddbcdn.vintagestory.at:443/a",
            "https://moddbcdn.vintagestory.at:/a",
            "https://moddbcdn.vintagestory.at./a",
            " https://moddbcdn.vintagestory.at/a.jpg",
            "https://moddbcdn.vintagestory.at/a.jpg\n",
            "https://mod\tdbcdn.vintagestory.at/a",
            "https://moddbcdn.vintagestory.at/a b.jpg",
            "https:\\\\moddbcdn.vintagestory.at/a",
            "https://[::1/a",
            "javascript:alert(1)",
            "data:image/png;base64,AA==",
        ],
    )
    def test_rejected(self, url: str | None) -> None:
        assert mod_image_url(url) is None


class TestTrailerWatchUrl:
    """`trailer_link_url` rebuilds a youtube-nocookie embed URL from the video ID alone."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube-nocookie.com/watch?v=mJHZH_sThDM",
            "https://youtube-nocookie.com/embed/mJHZH_sThDM",
            "https://www.youtube.com/watch?v=mJHZH_sThDM",
            "https://youtube.com/watch?t=10s&v=mJHZH_sThDM",
            "https://m.youtube.com/watch?v=mJHZH_sThDM&list=x",
            "https://youtu.be/mJHZH_sThDM",
            "https://youtu.be/mJHZH_sThDM?t=3",
            "https://WWW.YouTube.com/embed/mJHZH_sThDM",
        ],
    )
    def test_accepted(self, url: str) -> None:
        assert trailer_link_url(url) == EMBED_URL

    @pytest.mark.parametrize(
        "url",
        [
            None,
            "",
            "https://apachegaming.net",
            "http://www.youtube.com/watch?v=mJHZH_sThDM",
            "https://www.youtube.com.evil.example/watch?v=mJHZH_sThDM",
            "https://www.youtube.com/watch",
            "https://www.youtube.com/watch?v=short",
            "https://www.youtube.com/watch?v=mJHZH_sThDMx",
            "https://www.youtube.com/watch?v=mJHZH_sTh%0A",
            "https://www.youtube.com/embed/mJHZH_sThDM/",
            "https://www.youtube.com/shorts/mJHZH_sThDM",
            "https://www.youtube.com/playlist?list=x",
            "https://youtu.be/",
            "https://vimeo.com/123",
            "https://www.youtube.com/watch?v=mJHZH_sThDM\n",
            "javascript:alert(1)",
        ],
    )
    def test_rejected(self, url: str | None) -> None:
        assert trailer_link_url(url) is None

    def test_only_the_first_id_is_used(self) -> None:
        url = "https://www.youtube.com/watch?v=mJHZH_sThDM&v=aaaaaaaaaaa"
        assert trailer_link_url(url) == EMBED_URL


def screenshot(name: str, **overrides: Any) -> dict[str, Any]:
    """A normalized screenshot on the CDN, with `overrides` applied."""
    item: dict[str, Any] = {
        "fileid": 1,
        "mainfile": f"https://moddbcdn.vintagestory.at/{name}.jpg",
        "filename": f"{name}.jpg",
        "thumbnailfilename": f"https://moddbcdn.vintagestory.at/{name}_55_60.jpg",
        "created": None,
    }
    item.update(overrides)
    return item


class TestBuildScreenshots:
    """`build_screenshots` keeps the allowed screenshots in order."""

    def test_all_good_in_order(self) -> None:
        result = build_screenshots([screenshot("a"), screenshot("b")], "somemod")
        assert result == [
            ModScreenshot(
                image_url="https://moddbcdn.vintagestory.at/a.jpg",
                thumbnail_url="https://moddbcdn.vintagestory.at/a_55_60.jpg",
                filename="a.jpg",
            ),
            ModScreenshot(
                image_url="https://moddbcdn.vintagestory.at/b.jpg",
                thumbnail_url="https://moddbcdn.vintagestory.at/b_55_60.jpg",
                filename="b.jpg",
            ),
        ]

    @pytest.mark.parametrize(
        "mainfile",
        ["http://moddbcdn.vintagestory.at/x.jpg", "https://i.imgur.com/x.png", None],
    )
    def test_rejected_image_is_dropped(self, mainfile: str | None) -> None:
        items = [screenshot("a"), screenshot("x", mainfile=mainfile), screenshot("c")]
        result = build_screenshots(items, "somemod")
        assert [s.filename for s in result] == ["a.jpg", "c.jpg"]

    @pytest.mark.parametrize(
        "thumbnail",
        [None, "http://moddbcdn.vintagestory.at/a_55_60.jpg", "https://evil.example/a.jpg"],
    )
    def test_rejected_thumbnail_uses_the_image(self, thumbnail: str | None) -> None:
        result = build_screenshots([screenshot("a", thumbnailfilename=thumbnail)], "somemod")
        assert len(result) == 1
        assert result[0].thumbnail_url == result[0].image_url

    def test_empty_filename_kept(self) -> None:
        result = build_screenshots([screenshot("a", filename="")], "somemod")
        assert result[0].filename == ""

    def test_empty(self) -> None:
        assert build_screenshots([], "somemod") == []

    def test_dropped_screenshot_is_logged_at_debug(self, captured_logs: StringIO) -> None:
        items = [screenshot("a"), screenshot("x", mainfile="https://evil.example/x.jpg")]
        build_screenshots(items, "somemod")
        # The console renderer colors keys and values; compare the plain text
        output = re.sub(r"\x1b\[[0-9;]*m", "", captured_logs.getvalue())
        assert "mod_screenshot_dropped" in output
        assert "debug" in output
        assert "slug=somemod" in output
        assert "index=1" in output
        # The rejected URL is not logged
        assert "evil.example" not in output
