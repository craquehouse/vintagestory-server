"""Mods from GitHub and Forgejo releases get updates (Story 28.5, Epic 28 ADR-7)."""

import io
import json
import zipfile
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
import respx
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.routers.mods import get_link_transport
from vintagestory_api.services.mod_link import LinkDownloadError
from vintagestory_api.services.mod_releases import (
    LatestRelease,
    ReleaseAsset,
    ReleaseLink,
    asset_stem,
    is_newer,
    match_asset,
    parse_release_link,
    release_lookup,
    tag_version,
)
from vintagestory_api.services.mod_updates import (
    ModUpdateService,
    ModUpdateStore,
    UpdateAllSummary,
    get_mod_update_service,
)
from vintagestory_api.services.mods import ModService, get_mod_service
from vintagestory_api.services.pending_restart import PendingRestartState

ADMIN = {"X-API-Key": TEST_ADMIN_KEY}
GITHUB_LINK = "https://github.com/me/demo/releases/download/v1.0.0/demo_1.0.0.zip"
NEW_ASSET = "https://github.com/me/demo/releases/download/v1.1.0/demo_1.1.0.zip"


def demo_zip(modid: str = "demo", version: str = "1.0.0") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(
            "modinfo.json", json.dumps({"modid": modid, "name": "Demo", "version": version})
        )
    return buffer.getvalue()


def github_link() -> ReleaseLink:
    link = parse_release_link(GITHUB_LINK)
    assert link is not None
    return link


# --- Links, assets and versions ---------------------------------------------------------


class TestReleaseLinks:
    def test_a_github_release_asset(self) -> None:
        link = parse_release_link(GITHUB_LINK)

        assert link == ReleaseLink(
            scheme="https",
            host="github.com",
            port=None,
            owner="me",
            repo="demo",
            tag="v1.0.0",
            asset="demo_1.0.0.zip",
        )
        assert link is not None
        assert link.latest_release_url() == "https://api.github.com/repos/me/demo/releases/latest"

    def test_a_forgejo_release_asset_with_a_port(self) -> None:
        link = parse_release_link(
            "https://git.example.com:3000/team/my%20mod/releases/download/1.2/my%20mod.zip"
        )

        assert link is not None
        assert (link.repo, link.asset, link.is_github) == ("my mod", "my mod.zip", False)
        assert (
            link.latest_release_url()
            == "https://git.example.com:3000/api/v1/repos/team/my mod/releases/latest"
        )

    @pytest.mark.parametrize(
        "url",
        [
            None,
            "",
            "https://bucket.s3.amazonaws.com/mods/demo.zip",
            "https://github.com/me/demo/archive/refs/tags/v1.zip",
            "https://github.com/me/demo/releases/download/v1/sub/demo.zip",
            "https://github.com/me/demo/releases/latest/download/demo.zip",
            "not a link",
        ],
    )
    def test_anything_else_is_not_a_release_link(self, url: str | None) -> None:
        assert parse_release_link(url) is None

    @pytest.mark.parametrize(
        ("tag", "version"),
        [("v1.2.3", "1.2.3"), ("V2.0", "2.0"), ("1.0", "1.0"), ("vnext", "vnext")],
    )
    def test_tag_version(self, tag: str, version: str) -> None:
        assert tag_version(tag) == version

    @pytest.mark.parametrize(
        ("candidate", "installed", "expected"),
        [
            ("1.1.0", "1.0.0", True),
            ("1.0.0", "1.0.0", False),
            ("1.0", "1.0.0", False),
            ("0.9.9", "1.0.0", False),
            ("2.0.0-rc.1", "1.9.0", True),
            ("next", "1.0.0", None),
            ("1.1.0", "1.0.0-fork", True),
        ],
    )
    def test_is_newer(self, candidate: str, installed: str, expected: bool | None) -> None:
        assert is_newer(candidate, installed) is expected


def asset(name: str) -> ReleaseAsset:
    return ReleaseAsset(name=name, download_url=f"https://example.com/{name}")


class TestMatchAsset:
    def test_matches_the_same_name_with_another_version(self) -> None:
        assets = [asset("demo_1.1.0.zip"), asset("demo-extras_1.1.0.zip"), asset("notes.txt")]

        assert match_asset("demo_1.0.0.zip", assets) == asset("demo_1.1.0.zip")

    def test_v_prefixed_versions_match(self) -> None:
        assert asset_stem("demo-v1.0.0.zip") == asset_stem("demo-v2.3.zip")

    def test_the_only_zip_when_no_name_matches(self) -> None:
        assert match_asset("old-name.zip", [asset("renamed_2.0.zip"), asset("x.txt")]) == asset(
            "renamed_2.0.zip"
        )

    def test_no_match_among_several_zips(self) -> None:
        assert match_asset("old.zip", [asset("a_1.0.zip"), asset("b_1.0.zip")]) is None

    def test_no_zip_at_all(self) -> None:
        assert match_asset("demo_1.0.zip", [asset("demo_1.1.tar.gz")]) is None


# --- The lookup -------------------------------------------------------------------------


def latest_json(tag: str, *names: str) -> dict[str, object]:
    return {
        "tag_name": tag,
        "assets": [
            {
                "name": n,
                "browser_download_url": f"https://github.com/me/demo/releases/download/{tag}/{n}",
            }
            for n in names
        ],
    }


class TestReleaseLookup:
    @pytest.mark.asyncio
    async def test_asks_githubs_api_for_the_latest_release(self) -> None:
        seen: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=latest_json("v1.1.0", "demo_1.1.0.zip"))

        lookup = release_lookup(allow_http=False, transport=httpx.MockTransport(handle))

        latest = await lookup(github_link())

        assert str(seen[0].url) == "https://api.github.com/repos/me/demo/releases/latest"
        assert seen[0].headers["accept"] == "application/vnd.github+json"
        assert latest == LatestRelease(
            tag="v1.1.0",
            assets=[ReleaseAsset(name="demo_1.1.0.zip", download_url=NEW_ASSET)],
        )

    @pytest.mark.asyncio
    async def test_asks_a_forgejo_host_at_api_v1(self) -> None:
        seen: list[str] = []

        def handle(request: httpx.Request) -> httpx.Response:
            seen.append(str(request.url))
            return httpx.Response(200, json=latest_json("1.0.0", "demo.zip"))

        link = parse_release_link("https://git.example.com/me/demo/releases/download/0.9/demo.zip")
        assert link is not None
        await release_lookup(allow_http=False, transport=httpx.MockTransport(handle))(link)

        assert seen == ["https://git.example.com/api/v1/repos/me/demo/releases/latest"]

    @pytest.mark.asyncio
    async def test_follows_a_renamed_repo_redirect(self) -> None:
        def handle(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/me/demo/releases/latest":
                return httpx.Response(
                    301,
                    headers={"Location": "https://api.github.com/repositories/1/releases/latest"},
                )
            return httpx.Response(200, json=latest_json("v2.0.0", "demo_2.0.0.zip"))

        lookup = release_lookup(allow_http=False, transport=httpx.MockTransport(handle))

        assert (await lookup(github_link())).tag == "v2.0.0"

    @pytest.mark.parametrize(
        ("response", "message"),
        [
            (httpx.Response(404), "404"),
            (httpx.Response(403, text="rate limited"), "403"),
            (httpx.Response(200, text="<html>"), "not JSON"),
            (httpx.Response(200, json=[1, 2]), "not an object"),
            (httpx.Response(200, json={"assets": []}), "no tag"),
            (httpx.Response(200, content=b" " * (2 * 1024 * 1024 + 1)), "too large"),
        ],
    )
    @pytest.mark.asyncio
    async def test_an_unusable_answer_is_an_error(
        self, response: httpx.Response, message: str
    ) -> None:
        lookup = release_lookup(
            allow_http=False, transport=httpx.MockTransport(lambda _r: response)
        )

        with pytest.raises(LinkDownloadError, match=message):
            await lookup(github_link())


# --- The update check -------------------------------------------------------------------


class FakeForge:
    """Latest releases by repo, recording each lookup."""

    def __init__(self) -> None:
        self.latest: dict[str, LatestRelease | Exception] = {}
        self.asked: list[str] = []

    async def __call__(self, link: ReleaseLink) -> LatestRelease:
        self.asked.append(f"{link.host}/{link.owner}/{link.repo}")
        answer = self.latest[f"{link.owner}/{link.repo}"]
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def service(tmp_path: Path) -> ModService:
    return ModService(
        state_dir=tmp_path / "state",
        mods_dir=tmp_path / "mods",
        restart_state=PendingRestartState(),
        cache_dir=tmp_path / "cache",
        game_version_provider=lambda: "1.22.7",
    )


@pytest.fixture
def forge() -> FakeForge:
    return FakeForge()


@pytest.fixture
def update_service(tmp_path: Path, service: ModService, forge: FakeForge) -> ModUpdateService:
    return ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=service,
        game_version_provider=lambda: "1.22.7",
        release_lookup=forge,
    )


def install_linked(
    service: ModService, link: str = GITHUB_LINK, *, version: str = "1.0.0", modid: str = "demo"
) -> None:
    folder = service.cache_dir / "incoming" / "t"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / link.rsplit("/", 1)[-1]
    path.write_bytes(demo_zip(modid, version))
    service.install_archive(path, source="url", source_url=link)


def status_of(update_service: ModUpdateService, slug: str = "demo") -> tuple[str, str | None]:
    [item] = [i for i in update_service.get_status() if i.slug == slug]
    return item.status, item.reason


class TestCheck:
    @respx.mock
    @pytest.mark.asyncio
    async def test_a_newer_release_is_offered_not_verified(
        self, service: ModService, update_service: ModUpdateService, forge: FakeForge
    ) -> None:
        moddb = respx.get(url__startswith="https://mods.vintagestory.at/").mock(
            return_value=httpx.Response(500)
        )
        install_linked(service)
        forge.latest["me/demo"] = LatestRelease(
            tag="v1.1.0", assets=[ReleaseAsset("demo_1.1.0.zip", NEW_ASSET)]
        )

        summary = await update_service.check()

        assert (summary.checked, summary.failed) == (1, 0)
        assert forge.asked == ["github.com/me/demo"]
        assert moddb.call_count == 0
        [item] = update_service.get_status()
        assert (item.status, item.offered_version, item.offered_compatibility) == (
            "update_available",
            "1.1.0",
            "not_verified",
        )
        record = update_service.store.get("demo")
        assert record is not None
        assert record.releases[0].download_url == NEW_ASSET

    @pytest.mark.parametrize("tag", ["v1.0.0", "v0.9.0"])
    @pytest.mark.asyncio
    async def test_the_same_or_an_older_release_is_up_to_date(
        self, service: ModService, update_service: ModUpdateService, forge: FakeForge, tag: str
    ) -> None:
        install_linked(service)
        forge.latest["me/demo"] = LatestRelease(
            tag=tag, assets=[ReleaseAsset("demo.zip", NEW_ASSET)]
        )

        await update_service.check()

        assert status_of(update_service) == ("up_to_date", None)

    @pytest.mark.asyncio
    async def test_a_tag_that_is_not_a_version(
        self, service: ModService, update_service: ModUpdateService, forge: FakeForge
    ) -> None:
        install_linked(service)
        forge.latest["me/demo"] = LatestRelease(
            tag="nightly", assets=[ReleaseAsset("demo.zip", NEW_ASSET)]
        )

        await update_service.check()

        assert status_of(update_service) == ("unknown", "version_unparsable")

    @pytest.mark.asyncio
    async def test_no_matching_asset_offers_nothing(
        self, service: ModService, update_service: ModUpdateService, forge: FakeForge
    ) -> None:
        install_linked(service)
        forge.latest["me/demo"] = LatestRelease(
            tag="v2.0.0",
            assets=[ReleaseAsset("a_2.0.0.zip", NEW_ASSET), ReleaseAsset("b_2.0.0.zip", NEW_ASSET)],
        )

        await update_service.check()

        assert status_of(update_service) == ("unknown", "release_asset_not_matched")

    @pytest.mark.asyncio
    async def test_a_failed_lookup_is_recorded_and_the_check_goes_on(
        self, service: ModService, update_service: ModUpdateService, forge: FakeForge
    ) -> None:
        install_linked(service)
        install_linked(
            service,
            "https://github.com/me/other/releases/download/v1/other_1.0.0.zip",
            modid="other",
        )
        forge.latest["me/demo"] = LinkDownloadError("The forge answered 403 rate limit exceeded.")
        forge.latest["me/other"] = LatestRelease(
            tag="v1.0.0", assets=[ReleaseAsset("other_1.0.0.zip", NEW_ASSET)]
        )

        summary = await update_service.check()

        assert (summary.checked, summary.failed, summary.failed_slugs) == (2, 1, ["demo"])
        [demo] = [i for i in update_service.get_status() if i.slug == "demo"]
        assert (demo.status, demo.reason) == ("unknown", "not_checked")
        assert demo.error == "The forge answered 403 rate limit exceeded."
        assert status_of(update_service, "other") == ("up_to_date", None)

    @pytest.mark.asyncio
    async def test_a_link_that_is_not_a_release_stays_manual(
        self, service: ModService, update_service: ModUpdateService, forge: FakeForge
    ) -> None:
        install_linked(service, "https://bucket.s3.amazonaws.com/mods/demo.zip")

        summary = await update_service.check()

        assert summary.checked == 0
        assert forge.asked == []
        assert status_of(update_service) == ("unknown", "manual_install")

    @pytest.mark.asyncio
    async def test_update_all_skips_a_release_offer_as_not_verified(
        self, service: ModService, update_service: ModUpdateService, forge: FakeForge
    ) -> None:
        install_linked(service)
        forge.latest["me/demo"] = LatestRelease(
            tag="v1.1.0", assets=[ReleaseAsset("demo_1.1.0.zip", NEW_ASSET)]
        )
        await update_service.check()

        summary = await update_all(update_service, service)

        assert [(r.slug, r.outcome, r.reasons) for r in summary.results] == [
            ("demo", "skipped", ["not_verified"])
        ]


async def update_all(update_service: ModUpdateService, service: ModService) -> UpdateAllSummary:
    return await update_service.apply_all(service.change_version)


# --- Applying a release update ----------------------------------------------------------


@pytest.fixture
def web() -> dict[str, bytes]:
    return {}


@pytest.fixture
def client(
    tmp_path: Path,
    service: ModService,
    update_service: ModUpdateService,
    web: dict[str, bytes],
) -> Generator[TestClient]:
    settings = Settings(
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        data_dir=tmp_path,
        debug=False,
    )

    def handle(request: httpx.Request) -> httpx.Response:
        body = web.get(str(request.url))
        return httpx.Response(404) if body is None else httpx.Response(200, content=body)

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mod_service] = lambda: service
    app.dependency_overrides[get_mod_update_service] = lambda: update_service
    app.dependency_overrides[get_link_transport] = lambda: httpx.MockTransport(handle)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


VERSION_URL = "/api/v1alpha1/mods/demo/version"


class TestApplyingAReleaseUpdate:
    @pytest.fixture(autouse=True)
    async def offered(
        self, service: ModService, update_service: ModUpdateService, forge: FakeForge
    ) -> None:
        install_linked(service)
        service.disable_mod("demo")
        forge.latest["me/demo"] = LatestRelease(
            tag="v1.1.0", assets=[ReleaseAsset("demo_1.1.0.zip", NEW_ASSET)]
        )
        await update_service.check()

    def test_needs_confirmation_as_not_verified(self, client: TestClient) -> None:
        response = client.put(VERSION_URL, json={"version": "1.1.0"}, headers=ADMIN)

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.MOD_CONFIRMATION_REQUIRED
        assert detail["details"]["reasons"] == ["not_verified"]

    def test_installs_the_offered_asset_when_confirmed(
        self, client: TestClient, service: ModService, web: dict[str, bytes]
    ) -> None:
        web[NEW_ASSET] = demo_zip(version="1.1.0")

        response = client.put(
            VERSION_URL, json={"version": "1.1.0", "confirm": True}, headers=ADMIN
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert (data["previous_version"], data["version"], data["changed"]) == (
            "1.0.0",
            "1.1.0",
            True,
        )
        state = service.state_manager.get_mod_by_slug("demo")
        assert state is not None
        assert (state.version, state.enabled, state.source, state.source_url) == (
            "1.1.0",
            False,
            "url",
            NEW_ASSET,
        )
        assert state.filename == "demo_1.1.0.zip.disabled"
        assert sorted(p.name for p in service.state_manager.mods_dir.iterdir()) == [
            "demo_1.1.0.zip.disabled"
        ]

    def test_an_archive_of_another_mod_is_refused_and_the_mod_kept(
        self, client: TestClient, service: ModService, web: dict[str, bytes]
    ) -> None:
        web[NEW_ASSET] = demo_zip(modid="impostor", version="1.1.0")

        response = client.put(
            VERSION_URL, json={"version": "1.1.0", "confirm": True}, headers=ADMIN
        )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == ErrorCode.MOD_FILE_INVALID
        assert "impostor" in response.json()["detail"]["message"]
        state = service.state_manager.get_mod_by_slug("demo")
        assert state is not None
        assert state.version == "1.0.0"
        assert service.state_manager.get_mod_by_slug("impostor") is None

    def test_a_version_that_is_not_the_offer_is_404(self, client: TestClient) -> None:
        response = client.put(
            VERSION_URL, json={"version": "9.9.9", "confirm": True}, headers=ADMIN
        )

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == ErrorCode.MOD_VERSION_NOT_FOUND

    def test_the_installed_version_is_no_change(self, client: TestClient) -> None:
        response = client.put(VERSION_URL, json={"version": "1.0.0"}, headers=ADMIN)

        assert response.status_code == 200
        assert response.json()["data"]["changed"] is False

    def test_a_failed_download_keeps_the_mod(self, client: TestClient, service: ModService) -> None:
        response = client.put(
            VERSION_URL, json={"version": "1.1.0", "confirm": True}, headers=ADMIN
        )

        assert response.status_code == 502
        state = service.state_manager.get_mod_by_slug("demo")
        assert state is not None
        assert state.version == "1.0.0"
