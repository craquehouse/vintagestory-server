"""Tests for mod version changes (Story 14.2)."""

import io
import json
import zipfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from vintagestory_api.services.mod_api import DownloadError, ModApiClient, safe_release_filename
from vintagestory_api.services.mod_state import ModStateManager

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


def mod_zip_bytes(modinfo: object, member: str = "modinfo.json") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(member, modinfo if isinstance(modinfo, str) else json.dumps(modinfo))
    return buffer.getvalue()


class TestReadModinfo:
    @pytest.fixture
    def manager(self, tmp_path: Path) -> ModStateManager:
        return ModStateManager(state_dir=tmp_path / "state", mods_dir=tmp_path / "mods")

    def write(self, tmp_path: Path, data: bytes) -> Path:
        path = tmp_path / "mod.zip"
        path.write_bytes(data)
        return path

    def test_reads_valid_modinfo_without_caching(
        self, manager: ModStateManager, tmp_path: Path
    ) -> None:
        path = self.write(
            tmp_path, mod_zip_bytes({"modid": "demo", "name": "Demo", "version": "1.2.3"})
        )

        metadata = manager.read_modinfo(path)

        assert metadata is not None
        assert (metadata.modid, metadata.version) == ("demo", "1.2.3")
        assert not (tmp_path / "state" / "mods").exists()

    def test_keys_are_case_insensitive(self, manager: ModStateManager, tmp_path: Path) -> None:
        path = self.write(
            tmp_path, mod_zip_bytes({"ModID": "demo", "Name": "Demo", "Version": "1.2.3"})
        )

        metadata = manager.read_modinfo(path)

        assert metadata is not None
        assert metadata.modid == "demo"

    @pytest.mark.parametrize(
        "data",
        [
            mod_zip_bytes({"modid": "demo"}, member="readme.txt"),
            b"not a zip",
            mod_zip_bytes("{not json"),
            mod_zip_bytes({"modid": "demo", "name": "Demo"}),
            mod_zip_bytes({"modid": ["x"], "name": "Demo", "version": "1"}),
            mod_zip_bytes(["not", "an", "object"]),
        ],
        ids=["missing", "corrupt-zip", "invalid-json", "no-version", "wrong-type", "not-object"],
    )
    def test_unusable_archive_returns_none(
        self, manager: ModStateManager, tmp_path: Path, data: bytes
    ) -> None:
        assert manager.read_modinfo(self.write(tmp_path, data)) is None

    def test_byte_order_mark_is_accepted(self, manager: ModStateManager, tmp_path: Path) -> None:
        text = "\ufeff" + json.dumps({"modid": "demo", "name": "Demo", "version": "1"})
        path = self.write(tmp_path, mod_zip_bytes(text))

        metadata = manager.read_modinfo(path)

        assert metadata is not None
        assert metadata.version == "1"

    def test_undecodable_bytes_return_none(self, manager: ModStateManager, tmp_path: Path) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("modinfo.json", b"\xff\xfe\x00bad")

        assert manager.read_modinfo(self.write(tmp_path, buffer.getvalue())) is None

