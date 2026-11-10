"""Tests for mod version changes (Story 14.2)."""

from pathlib import Path

import pytest
import respx
from httpx import Response

from vintagestory_api.services.mod_api import DownloadError, ModApiClient, safe_release_filename

MOD_URL = "https://mods.vintagestory.at/api/mod/{}"
DOWNLOAD_URL = "https://mods.vintagestory.at/download"


class TestSafeReleaseFilename:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("CarryOn-1.22.0_v1.14.3.zip", "CarryOn-1.22.0_v1.14.3.zip"),
            ("Auto Map Markers 5.0.3.zip", "Auto Map Markers 5.0.3.zip"),
            ("../evil.zip", "evil.zip"),
            ("a/b/c.zip", "c.zip"),
            ("a\\b.zip", "b.zip"),
            ("/abs/path.zip", "path.zip"),
        ],
    )
    def test_keeps_only_final_component(self, raw: str, expected: str) -> None:
        assert safe_release_filename(raw) == expected

    @pytest.mark.parametrize("raw", ["", ".", "..", "dir/", "dir/..", "bad\x00.zip"])
    def test_rejects_unusable_names(self, raw: str) -> None:
        with pytest.raises(ValueError):
            safe_release_filename(raw)


def mod_with_release(filename: str) -> dict[str, object]:
    return {
        "statuscode": "200",
        "mod": {
            "assetid": 9,
            "releases": [
                {
                    "modversion": "1.0.0",
                    "modidstr": "demo",
                    "fileid": 7,
                    "filename": filename,
                    "tags": [],
                }
            ],
        },
    }


class TestDownloadUsesSafeFilename:
    @respx.mock
    @pytest.mark.asyncio
    async def test_hostile_filename_stays_in_cache(self, tmp_path: Path) -> None:
        respx.get(MOD_URL.format("demo")).mock(
            return_value=Response(200, json=mod_with_release("../../escaped.zip"))
        )
        respx.get(DOWNLOAD_URL).mock(return_value=Response(200, content=b"zip-bytes"))
        client = ModApiClient(cache_dir=tmp_path / "cache")

        result = await client.download_mod("demo")

        assert result is not None
        assert result.filename == "escaped.zip"
        assert result.path == tmp_path / "cache" / "mods" / "escaped.zip"
        assert result.path.read_bytes() == b"zip-bytes"
        assert not (tmp_path / "escaped.zip").exists()
        assert not list((tmp_path / "cache" / "mods").glob("*.tmp"))

    @respx.mock
    @pytest.mark.asyncio
    async def test_unusable_filename_fails_the_download(self, tmp_path: Path) -> None:
        respx.get(MOD_URL.format("demo")).mock(
            return_value=Response(200, json=mod_with_release(".."))
        )
        download = respx.get(DOWNLOAD_URL).mock(return_value=Response(200, content=b"zip-bytes"))
        client = ModApiClient(cache_dir=tmp_path / "cache")

        with pytest.raises(DownloadError):
            await client.download_mod("demo")
        assert not download.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_release_file_writes_to_cache(self, tmp_path: Path) -> None:
        respx.get(DOWNLOAD_URL).mock(return_value=Response(200, content=b"release"))
        client = ModApiClient(cache_dir=tmp_path / "cache")

        path = await client.download_release_file("demo", 7, "x/Demo 1.0.zip")

        assert path == tmp_path / "cache" / "mods" / "Demo 1.0.zip"
        assert path.read_bytes() == b"release"
