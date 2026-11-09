"""Edge cases across services: malformed input and files that are not there."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.models.mods import ModState
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.routers.mods import _api_mod_to_browse_item
from vintagestory_api.services.cache_eviction import CacheEvictionService
from vintagestory_api.services.config_init_service import ConfigInitService
from vintagestory_api.services.game_config import GameConfigService, SettingValueInvalidError
from vintagestory_api.services.mod_api import DownloadError, DownloadResult, ModApiClient
from vintagestory_api.services.mod_state import ModStateManager
from vintagestory_api.services.mods import ModService
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.server import VS_CDN_BASE, VS_STABLE_API, ServerService
from vintagestory_api.services.versions_cache import LatestVersionsCache

MOD_URL = "https://mods.vintagestory.at/api/mod/demo"
MOD_DOWNLOAD_URL = "https://mods.vintagestory.at/download?fileid=42"
GAMEVERSIONS_URL = "https://mods.vintagestory.at/api/gameversions"
DEMO_FILENAME = "demo_1.0.0.zip"
DEMO_RELEASE: dict[str, Any] = {
    "releaseid": 1,
    "modversion": "1.0.0",
    "filename": DEMO_FILENAME,
    "fileid": 42,
    "downloads": 1,
    "tags": ["1.22.0"],
}
DEMO_MOD: dict[str, Any] = {
    "modid": 1,
    "assetid": 1,
    "name": "Demo",
    "urlalias": "demo",
    "releases": [DEMO_RELEASE],
}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(api_key_admin="test-admin-key", data_dir=tmp_path / "data")


def demo_state(filename: str, slug: str) -> ModState:
    return ModState(
        filename=filename,
        slug=slug,
        version="1.0.0",
        enabled=True,
        installed_at=datetime.now(UTC),
    )


class TestApiResponse:
    def test_error_response_keeps_error_field(self) -> None:
        error = {"code": "SOME_ERROR", "message": "Failed"}

        assert ApiResponse(status="error", error=error).model_dump()["error"] == error

    def test_success_response_omits_error_field(self) -> None:
        assert "error" not in ApiResponse(status="ok", data={}).model_dump()


class TestModBrowseNormalization:
    def test_unknown_side_defaults_to_both(self) -> None:
        item = _api_mod_to_browse_item({"modidstrs": ["demo"], "side": "sideways"})

        assert item.side == "both"

    def test_unknown_type_defaults_to_mod(self) -> None:
        item = _api_mod_to_browse_item({"modidstrs": ["demo"], "type": "texturepack"})

        assert item.mod_type == "mod"


class TestCacheEvictionEdgeCases:
    def write_cached_mod(self, cache_dir: Path, name: str, size_bytes: int) -> None:
        mods_cache = cache_dir / "mods"
        mods_cache.mkdir(parents=True, exist_ok=True)
        (mods_cache / name).write_bytes(b"x" * size_bytes)

    def test_directories_matching_pattern_are_not_counted(self, tmp_path: Path) -> None:
        self.write_cached_mod(tmp_path, "real.zip", 100)
        (tmp_path / "mods" / "directory.zip").mkdir()

        stats = CacheEvictionService(cache_dir=tmp_path, max_size_mb=100).get_cache_stats()

        assert stats["file_count"] == 1
        assert stats["total_size_bytes"] == 100

    def test_eviction_reports_nothing_freed_when_every_delete_fails(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        size_bytes = 2 * 1024 * 1024
        self.write_cached_mod(tmp_path, "locked.zip", size_bytes)
        service = CacheEvictionService(cache_dir=tmp_path, max_size_mb=1)

        with patch.object(Path, "unlink", side_effect=PermissionError("locked")):
            result = service.evict_if_needed()

        assert result.files_evicted == 0
        assert result.bytes_freed == 0
        assert result.files_remaining == 1
        assert result.bytes_remaining == size_bytes
        assert "cache_eviction_complete" not in capsys.readouterr().out


class TestConfigInitQuotes:
    @pytest.mark.parametrize("value", ["", "a", '"', "'"])
    def test_values_too_short_to_be_quoted_are_unchanged(
        self, settings: Settings, value: str
    ) -> None:
        service = ConfigInitService(settings=settings)

        assert service._strip_surrounding_quotes(value) == value


class TestGameConfigFloatValidation:
    def test_numeric_string_is_coerced(self, settings: Settings) -> None:
        service = GameConfigService(settings=settings)

        assert service._validate_value("Rate", "1.5", "float") == 1.5

    def test_bool_is_not_a_float(self, settings: Settings) -> None:
        service = GameConfigService(settings=settings)

        with pytest.raises(SettingValueInvalidError):
            service._validate_value("Rate", True, "float")


class TestModApiEdgeCases:
    def mock_mod_lookup(self) -> None:
        respx.get(MOD_URL).mock(
            return_value=Response(200, json={"statuscode": "200", "mod": DEMO_MOD})
        )

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_before_download_starts(self, tmp_path: Path) -> None:
        self.mock_mod_lookup()
        respx.get(MOD_DOWNLOAD_URL).mock(side_effect=httpx.TimeoutException("timed out"))

        with pytest.raises(DownloadError, match="timed out"):
            await ModApiClient(cache_dir=tmp_path).download_mod("demo")

    @respx.mock
    @pytest.mark.asyncio
    async def test_write_error_before_temp_file_exists(self, tmp_path: Path) -> None:
        self.mock_mod_lookup()
        respx.get(MOD_DOWNLOAD_URL).mock(return_value=Response(200, content=b"zip"))

        with (
            patch(
                "vintagestory_api.services.mod_api.open",
                create=True,
                side_effect=PermissionError("read-only"),
            ),
            pytest.raises(DownloadError, match="IO error"),
        ):
            await ModApiClient(cache_dir=tmp_path).download_mod("demo")

    @respx.mock
    @pytest.mark.asyncio
    async def test_malformed_game_versions_are_skipped(self, tmp_path: Path) -> None:
        respx.get(GAMEVERSIONS_URL).mock(
            return_value=Response(
                200,
                json={
                    "statuscode": "200",
                    "gameversions": [
                        {"name": "1.22.0", "tagid": 7},
                        {"name": "no-tagid"},
                        {"tagid": 8},
                    ],
                },
            )
        )

        versions = await ModApiClient(cache_dir=tmp_path).get_game_versions()

        assert versions == {"1.22.0": 7}


class TestModStateEdgeCases:
    @pytest.fixture
    def manager(self, tmp_path: Path) -> ModStateManager:
        state_dir = tmp_path / "state"
        mods_dir = tmp_path / "mods"
        state_dir.mkdir()
        mods_dir.mkdir()
        return ModStateManager(state_dir=state_dir, mods_dir=mods_dir)

    def test_lookup_by_slug_searches_past_other_mods(self, manager: ModStateManager) -> None:
        manager.set_mod_state("first.zip", demo_state("first.zip", "first"))
        manager.set_mod_state("second.zip", demo_state("second.zip", "second"))

        found = manager.get_mod_by_slug("second")

        assert found is not None
        assert found.filename == "second.zip"
        assert manager.get_mod_by_slug("missing") is None

    def test_scan_only_lists_mod_files(self, manager: ModStateManager) -> None:
        (manager.mods_dir / "enabled.zip").touch()
        (manager.mods_dir / "disabled.zip.disabled").touch()
        (manager.mods_dir / "notes.txt").touch()
        (manager.mods_dir / "directory.zip").mkdir()

        assert sorted(manager.scan_mods_directory()) == ["disabled.zip.disabled", "enabled.zip"]


class TestModServiceEdgeCases:
    @pytest.fixture
    def service(self, tmp_path: Path) -> ModService:
        state_dir = tmp_path / "state"
        mods_dir = tmp_path / "mods"
        cache_dir = tmp_path / "cache"
        for directory in (state_dir, mods_dir, cache_dir):
            directory.mkdir()
        return ModService(
            state_dir=state_dir,
            mods_dir=mods_dir,
            cache_dir=cache_dir,
            restart_state=PendingRestartState(),
        )

    def test_remove_mod_without_cached_metadata(self, service: ModService) -> None:
        manager = service.state_manager
        (manager.mods_dir / DEMO_FILENAME).touch()
        manager.set_mod_state(DEMO_FILENAME, demo_state(DEMO_FILENAME, "demo"))

        service.remove_mod("demo")

        assert not (manager.mods_dir / DEMO_FILENAME).exists()
        assert manager.get_mod_by_slug("demo") is None

    @pytest.mark.asyncio
    async def test_failed_install_reports_original_error_if_file_is_gone(
        self, service: ModService, tmp_path: Path
    ) -> None:
        cached = tmp_path / "cached.zip"
        cached.write_bytes(b"zip")
        client = MagicMock()
        client.download_mod = AsyncMock(
            return_value=DownloadResult(
                path=cached,
                filename=DEMO_FILENAME,
                version="1.0.0",
                release=DEMO_RELEASE,
                asset_id=1,
            )
        )

        def import_removes_file(path: Path) -> None:
            path.unlink()
            raise ValueError("bad archive")

        with (
            patch.object(service, "_get_mod_api_client", return_value=client),
            patch.object(service.state_manager, "import_mod", side_effect=import_removes_file),
            pytest.raises(ValueError, match="bad archive"),
        ):
            await service.install_mod("demo")

        assert service.state_manager.get_mod_by_slug("demo") is None


class TestServerDownloadEdgeCases:
    @respx.mock
    @pytest.mark.asyncio
    async def test_versions_without_linux_server_are_skipped(self, settings: Settings) -> None:
        filename = "vs_server_linux-x64_1.22.7.tar.gz"
        respx.get(VS_STABLE_API).mock(
            return_value=Response(
                200,
                json={
                    "1.22.7": {
                        "linuxserver": {
                            "filename": filename,
                            "filesize": "40.2 MB",
                            "md5": "abc123",
                            "urls": {
                                "cdn": f"https://cdn.example/{filename}",
                                "local": "https://local.example",
                            },
                            "latest": True,
                        }
                    },
                    "1.22.6": {"windowsserver": {"filename": "server.exe"}},
                },
            )
        )
        service = ServerService(settings)

        versions = await service.get_available_versions("stable")
        await service.close()

        assert list(versions) == ["1.22.7"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_without_content_length_reports_no_progress(
        self, settings: Settings
    ) -> None:
        async def chunks() -> AsyncIterator[bytes]:
            yield b"tar"
            yield b"ball"

        url = f"{VS_CDN_BASE}/stable/vs_server_linux-x64_1.22.7.tar.gz"
        respx.get(url).mock(return_value=Response(200, content=chunks()))
        settings.server_dir.mkdir(parents=True)
        service = ServerService(settings)
        progress = MagicMock()

        tarball = await service.download_server("1.22.7", "stable", progress)
        await service.close()

        assert tarball.read_bytes() == b"tarball"
        progress.assert_not_called()


class TestVersionsCacheEdgeCases:
    def test_unknown_channel_is_not_cached(self) -> None:
        cache = LatestVersionsCache()

        cache.set_versions("nightly", [{"version": "9.9.9"}])

        assert cache.get_versions("nightly") == []
        assert cache.cached_at is None
