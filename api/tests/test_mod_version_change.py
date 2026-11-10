"""Tests for mod version changes (Story 14.2)."""

import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import respx
from httpx import Response

from vintagestory_api.models.mods import ModState
from vintagestory_api.services.mod_api import (
    DownloadError,
    ModApiClient,
    ModVersionNotFoundError,
    safe_release_filename,
)
from vintagestory_api.services.mod_state import ModStateManager
from vintagestory_api.services.mods import (
    ModConfirmationRequiredError,
    ModNotFoundError,
    ModService,
    ModValidationError,
)
from vintagestory_api.services.pending_restart import PendingRestartState

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


FIXTURES = Path(__file__).parent / "fixtures" / "moddb"


def fixture_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"mod_{name}.json").read_text())


def fixture_release(name: str, modid: str, version: str) -> dict[str, Any]:
    releases: list[dict[str, Any]] = fixture_json(name)["mod"]["releases"]
    return next(r for r in releases if r["modidstr"] == modid and r["modversion"] == version)


def make_service(tmp_path: Path, game_version: str | None = "1.22.7") -> ModService:
    return ModService(
        state_dir=tmp_path / "state",
        mods_dir=tmp_path / "mods",
        restart_state=PendingRestartState(),
        cache_dir=tmp_path / "cache",
        game_version_provider=lambda: game_version,
    )


def install_existing(
    service: ModService, slug: str, version: str, filename: str, *, enabled: bool = True
) -> Path:
    mods_dir = service.state_manager.mods_dir
    mods_dir.mkdir(parents=True, exist_ok=True)
    name = filename if enabled else f"{filename}.disabled"
    path = mods_dir / name
    path.write_bytes(mod_zip_bytes({"modid": slug, "name": slug, "version": version}))
    service.state_manager.set_mod_state(
        name,
        ModState(
            filename=name,
            slug=slug,
            version=version,
            enabled=enabled,
            installed_at=datetime(2026, 1, 1, tzinfo=UTC),
            asset_id=1,
        ),
    )
    service.state_manager.save()
    return path


def mock_lookup(name: str, slug: str) -> None:
    respx.get(MOD_URL.format(slug)).mock(return_value=Response(200, json=fixture_json(name)))


def mock_download(release: dict[str, Any], modinfo: dict[str, Any] | None = None) -> respx.Route:
    content = mod_zip_bytes(
        modinfo
        or {"modid": release["modidstr"], "name": "x", "version": release["modversion"]}
    )
    return respx.get(DOWNLOAD_URL, params={"fileid": str(release["fileid"])}).mock(
        return_value=Response(200, content=content)
    )


class TestPrepareVersionChange:
    @pytest.mark.asyncio
    async def test_mod_not_installed(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)

        with pytest.raises(ModNotFoundError):
            await service._prepare_version_change("carryon", "1.14.3", confirm=False)

    @respx.mock
    @pytest.mark.asyncio
    async def test_version_of_another_modid_is_not_found(self, tmp_path: Path) -> None:
        service = make_service(tmp_path, game_version="1.21.6")
        install_existing(service, "instruments", "1.0.1", "instruments_1.0.1.zip")
        mock_lookup("instruments", "instruments")

        with pytest.raises(ModVersionNotFoundError):
            await service._prepare_version_change("instruments", "2.0.7", confirm=True)

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("game", "installed", "target", "reasons"),
        [
            ("1.22.2", "1.14.3", "1.14.1", ["older"]),
            ("1.22.2", "1.14.3", "2.0.0-rc.1", ["prerelease"]),
            ("1.22.7", "2.0.0-pre.6", "2.0.0-pre.7", ["not_verified"]),
            ("1.22.7", "1.14.3", "1.14.1", ["not_verified", "older"]),
        ],
    )
    async def test_confirmation_reasons_block_before_download(
        self, tmp_path: Path, game: str, installed: str, target: str, reasons: list[str]
    ) -> None:
        service = make_service(tmp_path, game_version=game)
        install_existing(service, "carryon", installed, f"carryon_{installed}.zip")
        mock_lookup("carryon", "carryon")
        download = mock_download(fixture_release("carryon", "carryon", target))

        with pytest.raises(ModConfirmationRequiredError) as raised:
            await service._prepare_version_change("carryon", target, confirm=False)

        assert raised.value.reasons == reasons
        assert not download.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_confirmed_change_downloads_and_validates(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "carryon", "1.14.3", "carryon_1.14.3.zip")
        mock_lookup("carryon", "carryon")
        release = fixture_release("carryon", "carryon", "1.14.1")
        download = mock_download(release)

        prepared = await service._prepare_version_change("carryon", "1.14.1", confirm=True)

        assert download.called
        assert prepared.target.modversion == "1.14.1"
        assert prepared.archive == tmp_path / "cache" / "mods" / release["filename"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_valid_cached_archive_is_reused(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "carryon", "1.14.1", "carryon_1.14.1.zip")
        mock_lookup("carryon", "carryon")
        release = fixture_release("carryon", "carryon", "1.14.3")
        cached = tmp_path / "cache" / "mods" / release["filename"]
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(mod_zip_bytes({"modid": "carryon", "name": "x", "version": "1.14.3"}))
        download = mock_download(release)

        prepared = await service._prepare_version_change("carryon", "1.14.3", confirm=False)

        assert prepared.archive == cached
        assert not download.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_cached_archive_for_another_version_is_downloaded_again(
        self, tmp_path: Path
    ) -> None:
        service = make_service(tmp_path)
        install_existing(service, "carryon", "1.14.1", "carryon_1.14.1.zip")
        mock_lookup("carryon", "carryon")
        release = fixture_release("carryon", "carryon", "1.14.3")
        cached = tmp_path / "cache" / "mods" / release["filename"]
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(mod_zip_bytes({"modid": "carryon", "name": "x", "version": "0.0.1"}))
        download = mock_download(release)

        prepared = await service._prepare_version_change("carryon", "1.14.3", confirm=False)

        assert download.called
        assert service.state_manager.read_modinfo(prepared.archive) is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_downloaded_archive_for_another_mod_fails(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "carryon", "1.14.1", "carryon_1.14.1.zip")
        mock_lookup("carryon", "carryon")
        release = fixture_release("carryon", "carryon", "1.14.3")
        mock_download(release, modinfo={"modid": "someothermod", "name": "x", "version": "1.14.3"})

        with pytest.raises(ModValidationError):
            await service._prepare_version_change("carryon", "1.14.3", confirm=False)

        assert not (tmp_path / "cache" / "mods" / release["filename"]).exists()

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_failure_propagates(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "carryon", "1.14.1", "carryon_1.14.1.zip")
        mock_lookup("carryon", "carryon")
        release = fixture_release("carryon", "carryon", "1.14.3")
        respx.get(DOWNLOAD_URL, params={"fileid": str(release["fileid"])}).mock(
            return_value=Response(500)
        )

        with pytest.raises(DownloadError):
            await service._prepare_version_change("carryon", "1.14.3", confirm=False)

    @respx.mock
    @pytest.mark.asyncio
    async def test_unusable_release_filename_fails_validation(self, tmp_path: Path) -> None:
        service = make_service(tmp_path)
        install_existing(service, "demo", "1.0.0", "demo_1.0.0.zip")
        body = {
            "statuscode": "200",
            "mod": {
                "releases": [
                    {"modversion": "1.1.0", "modidstr": "demo", "fileid": 5, "filename": ".."},
                    {"modversion": "1.0.0", "modidstr": "demo", "fileid": 4, "filename": "d.zip"},
                ]
            },
        }
        respx.get(MOD_URL.format("demo")).mock(return_value=Response(200, json=body))

        with pytest.raises(ModValidationError):
            await service._prepare_version_change("demo", "1.1.0", confirm=True)

