"""Tests for the mod media URL rules (Story 18.1, Epic 18 ADR-1 and ADR-2; Story 19.6)."""

import json
import re
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
import respx
from httpx import Response

from vintagestory_api.models.mods import ModScreenshot
from vintagestory_api.services.mod_api import extract_slug
from vintagestory_api.services.mod_media import (
    MAX_LINK_LENGTH,
    MOD_MEDIA_HOSTS,
    YOUTUBE_HOSTS,
    build_screenshots,
    checked_url,
    external_link_url,
    mod_image_url,
    trailer_link_url,
)
from vintagestory_api.services.mods import ModService
from vintagestory_api.services.pending_restart import PendingRestartState

FIXTURES = Path(__file__).parent / "fixtures" / "moddb"

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


def _plain(captured_logs: StringIO) -> str:
    """The captured log text without the console renderer's colors."""
    return re.sub(r"\x1b\[[0-9;]*m", "", captured_logs.getvalue())


def _url_of_length(length: int) -> str:
    prefix = "https://example.com/"
    return prefix + "a" * (length - len(prefix))


class TestExternalLinkUrl:
    """`external_link_url` keeps only well-formed https URLs with a host (Story 19.6)."""

    def test_max_link_length(self) -> None:
        assert MAX_LINK_LENGTH == 2048

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/a/b",
            "https://example.com:8443/x?y#z",
            "https://[::1]/",
            "https://x.com%40y.com/",
            _url_of_length(MAX_LINK_LENGTH),
        ],
    )
    def test_kept_unchanged(self, url: str) -> None:
        assert external_link_url(url) == url

    @pytest.mark.parametrize(
        "url",
        [
            None,
            "",
            "http://example.com",
            "HTTPS://example.com",
            "//example.com",
            "javascript:alert(1)",
            "data:text/html,x",
            "https://",
            "https:///path",
            "https://:443/",
            "https://u:p@example.com",
            "https://@example.com",
            "https://example.com:abc",
            "https://example.com:99999",
            "https://example.com:0",
            "https://[::1",
            "https://example.com/a b",
            " https://example.com",
            "https://example.com/\t",
            "https://example.com/\n",
            "https://example.com\u00a0/",
            "https:\\\\example.com",
            "https://example.com/\\a",
            _url_of_length(MAX_LINK_LENGTH + 1),
        ],
    )
    def test_rejected(self, url: str | None) -> None:
        assert external_link_url(url) is None


class TestCheckedUrl:
    """`checked_url` applies a rule and logs a dropped URL without its text (Story 19.6)."""

    def test_returns_the_rules_value(self) -> None:
        url = "https://moddbcdn.vintagestory.at/a.png"
        assert checked_url(url, mod_image_url, slug="m", field="logo_url") == url
        assert checked_url("https://evil.example/a", mod_image_url, slug="m", field="f") is None

    def test_dropped_url_is_logged_at_debug_without_the_url(self, captured_logs: StringIO) -> None:
        checked_url(
            "javascript:alert('evil')", external_link_url, slug="somemod", field="homepage_url"
        )
        output = _plain(captured_logs)
        assert "mod_url_dropped" in output
        assert "debug" in output
        assert "slug=somemod" in output
        assert "field=homepage_url" in output
        assert "evil" not in output
        assert "javascript" not in output

    @pytest.mark.parametrize("url", [None, ""])
    def test_empty_or_missing_is_not_logged(self, captured_logs: StringIO, url: str | None) -> None:
        assert checked_url(url, external_link_url, slug="somemod", field="source_url") is None
        assert "mod_url_dropped" not in _plain(captured_logs)

    def test_kept_url_is_not_logged(self, captured_logs: StringIO) -> None:
        checked_url("https://github.com/a/b", external_link_url, slug="m", field="source_url")
        assert "mod_url_dropped" not in _plain(captured_logs)


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


class TestRulesDoNotFollowModDbUrl:
    """VS_MOD_DB_URL moves the requests, not the image host or the link rules (Story 20.6 AC 3)."""

    @pytest.mark.asyncio
    async def test_lookup_on_a_mirror_keeps_the_same_rules(self, tmp_path: Path) -> None:
        payload = json.loads((FIXTURES / "mod_betterruins.json").read_text())
        mod = payload["mod"]
        mod["logofilename"] = "https://mirror.example/logo.png"
        mod["homepageurl"] = "http://example.com/home"
        mod["sourcecodeurl"] = "https://example.com/source"
        mirror_shot = dict(mod["screenshots"][0])
        mirror_shot["mainfile"] = "https://mirror.example/shot.jpg"
        mirror_shot["thumbnailfilename"] = "https://mirror.example/shot_55_60.jpg"
        mod["screenshots"] = [mirror_shot, mod["screenshots"][1]]
        cdn_shot = mod["screenshots"][1]["mainfile"]
        service = ModService(
            state_dir=tmp_path / "state",
            mods_dir=tmp_path / "Mods",
            cache_dir=tmp_path / "cache",
            restart_state=PendingRestartState(),
            game_version="1.22.7",
            mod_db_url="https://mirror.example",
        )

        with respx.mock(assert_all_mocked=True) as mock:
            mock.get("https://mirror.example/api/mod/betterruins").mock(
                return_value=Response(200, json=payload)
            )
            result = await service.lookup_mod("betterruins")
        await service.api_client.close()

        assert result.logo_url is None
        assert result.homepage_url is None
        assert result.source_url == "https://example.com/source"
        assert [shot.image_url for shot in result.screenshots] == [cdn_shot]

    def test_cdn_logo_is_kept_on_any_mod_db_url(self) -> None:
        url = "https://moddbcdn.vintagestory.at/logo.png"

        assert mod_image_url(url) == url
        assert mod_image_url("https://mirror.example/logo.png") is None

    def test_extract_slug_accepts_the_same_forms(self) -> None:
        assert extract_slug("https://mods.vintagestory.at/smithingplus") == "smithingplus"
        assert extract_slug("https://mirror.example/smithingplus") == "smithingplus"
