"""A mod can be installed from an HTTPS link (Story 28.3, Epic 28 ADR-5)."""

import io
import ipaddress
import json
import zipfile
from collections.abc import AsyncIterator, Callable, Generator, Iterable
from io import StringIO
from pathlib import Path
from typing import Any

import httpcore
import httpx
import pytest
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.routers.mods import get_link_transport
from vintagestory_api.services.mod_link import (
    LinkDownloadError,
    ModUrlInvalidError,
    check_link,
    downloaded,
    name_from_modinfo,
    stored_link,
)
from vintagestory_api.services.mod_updates import (
    ModUpdateService,
    ModUpdateStore,
    get_mod_update_service,
)
from vintagestory_api.services.mods import ModService, get_mod_service
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.safe_fetch import (
    AddressBlockedError,
    GuardedBackend,
    GuardedTransport,
    address_refusal,
    parse_private_hosts,
)

LINK_URL = "/api/v1alpha1/mods/install-from-url"
ADMIN = {"X-API-Key": TEST_ADMIN_KEY}
MONITOR = {"X-API-Key": TEST_MONITOR_KEY}
GITHUB_ASSET = "https://github.com/me/demo/releases/download/v1.0.0/demo_1.0.0.zip"


def demo_zip(modid: str = "demo", version: str = "1.0.0") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(
            "modinfo.json", json.dumps({"modid": modid, "name": "Demo", "version": version})
        )
    return buffer.getvalue()


# --- Address rules (ADR-5 decision 3 and 4) ---------------------------------------------


class TestAddressRules:
    @pytest.mark.parametrize(
        ("address", "reason"),
        [
            ("127.0.0.1", "loopback"),
            ("::1", "loopback"),
            ("169.254.169.254", "link-local"),
            ("fe80::1", "link-local"),
            ("0.0.0.0", "unspecified"),
            ("::", "unspecified"),
            ("224.0.0.1", "multicast"),
            ("240.0.0.1", "reserved"),
            # Story 28.3 review: NAT64 of 127.0.0.1; pinned in case Python reclassifies it
            ("64:ff9b::7f00:1", "reserved"),
        ],
    )
    def test_always_refused_even_for_a_listed_host(self, address: str, reason: str) -> None:
        ip = ipaddress.ip_address(address)
        assert address_refusal(ip, private_allowed=False) == reason
        assert address_refusal(ip, private_allowed=True) == reason

    @pytest.mark.parametrize(
        "address",
        [
            "10.0.0.5",
            "172.16.0.1",
            "192.168.1.5",
            "100.64.0.1",
            "fc00::1",
            # Story 28.3 review: 6to4 and Teredo forms that embed a loopback address
            "2002:7f00:1::",
            "2001::7f00:1",
        ],
    )
    def test_private_is_refused_unless_the_host_is_listed(self, address: str) -> None:
        ip = ipaddress.ip_address(address)
        assert address_refusal(ip, private_allowed=False) == "private"
        assert address_refusal(ip, private_allowed=True) is None

    @pytest.mark.parametrize("address", ["140.82.112.3", "2606:4700::6810:84e5"])
    def test_global_is_allowed(self, address: str) -> None:
        assert address_refusal(ipaddress.ip_address(address), private_allowed=False) is None

    def test_private_hosts_are_parsed_lower_cased(self) -> None:
        assert parse_private_hosts(" Git.LAN , forgejo.home.,, ") == frozenset(
            {"git.lan", "forgejo.home"}
        )
        assert parse_private_hosts("") == frozenset()


# --- The guarded backend ----------------------------------------------------------------


def resolver(answers: dict[str, list[str]]) -> Callable[[str, int], Any]:
    async def resolve(host: str, port: int) -> list[str]:
        return answers[host]

    return resolve


class RecordingBackend(httpcore.AsyncMockBackend):
    """A mock network that answers every connection with `buffer`, recording the hosts."""

    def __init__(self, buffer: list[bytes]) -> None:
        super().__init__(buffer)
        self.connected: list[str] = []

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        self.connected.append(host)
        return await super().connect_tcp(host, port, timeout, local_address, socket_options)


class TestGuardedBackend:
    @pytest.mark.asyncio
    async def test_connects_to_the_address_it_checked(self) -> None:
        inner = RecordingBackend([])
        backend = GuardedBackend(inner=inner, resolve=resolver({"mods.example": ["140.82.112.3"]}))

        await backend.connect_tcp("mods.example", 443)

        assert inner.connected == ["140.82.112.3"]

    @pytest.mark.asyncio
    async def test_a_host_with_any_internal_answer_is_refused(self) -> None:
        inner = RecordingBackend([])
        backend = GuardedBackend(
            inner=inner, resolve=resolver({"split.example": ["140.82.112.3", "10.0.0.5"]})
        )

        with pytest.raises(AddressBlockedError, match="split.example"):
            await backend.connect_tcp("split.example", 443)
        assert inner.connected == []

    @pytest.mark.asyncio
    async def test_a_listed_host_may_use_a_private_address_but_not_loopback(self) -> None:
        inner = RecordingBackend([])
        backend = GuardedBackend(
            frozenset({"git.lan"}),
            inner=inner,
            resolve=resolver({"git.lan": ["192.168.1.5"], "GIT.lan.": ["127.0.0.1"]}),
        )

        await backend.connect_tcp("git.lan", 443)
        with pytest.raises(AddressBlockedError):
            await backend.connect_tcp("GIT.lan.", 443)
        assert inner.connected == ["192.168.1.5"]

    @pytest.mark.asyncio
    async def test_an_ipv4_mapped_loopback_is_refused(self) -> None:
        backend = GuardedBackend(
            inner=RecordingBackend([]), resolve=resolver({"x.example": ["::ffff:127.0.0.1"]})
        )

        with pytest.raises(AddressBlockedError):
            await backend.connect_tcp("x.example", 443)

    @pytest.mark.asyncio
    async def test_a_name_that_does_not_resolve_is_a_connect_error(self) -> None:
        async def fail(host: str, port: int) -> list[str]:
            raise OSError("Name or service not known")

        backend = GuardedBackend(inner=RecordingBackend([]), resolve=fail)

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp("nowhere.example", 443)


def http_response(status: str, headers: dict[str, str], body: bytes = b"") -> bytes:
    lines = [f"HTTP/1.1 {status}", *(f"{k}: {v}" for k, v in headers.items())]
    lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode() + body


class TestRedirectsAreCheckedPerConnection:
    @pytest.mark.asyncio
    async def test_a_redirect_to_an_internal_host_is_refused(self, tmp_path: Path) -> None:
        """The first hop is public; the redirect's host resolves to the metadata service."""
        inner = RecordingBackend(
            [http_response("302 Found", {"Location": "http://internal.example/latest.zip"})]
        )
        backend = GuardedBackend(
            inner=inner,
            resolve=resolver(
                {"public.example": ["140.82.112.3"], "internal.example": ["169.254.169.254"]}
            ),
        )

        with pytest.raises(AddressBlockedError, match="internal.example"):
            async with downloaded(
                "http://public.example/mod.zip",
                cache_dir=tmp_path,
                limit_bytes=1024 * 1024,
                allow_http=True,
                transport=GuardedTransport(backend=backend),
            ):
                pass
        assert inner.connected == ["140.82.112.3"]
        assert list((tmp_path / "incoming").iterdir()) == []

    @pytest.mark.asyncio
    async def test_a_public_download_through_the_guard(self, tmp_path: Path) -> None:
        body = demo_zip()
        inner = RecordingBackend(
            [
                http_response(
                    "200 OK", {"Content-Disposition": 'attachment; filename="demo-1.zip"'}, body
                )
            ]
        )
        backend = GuardedBackend(inner=inner, resolve=resolver({"cdn.example": ["140.82.112.3"]}))

        async with downloaded(
            "http://cdn.example/get?id=1",
            cache_dir=tmp_path,
            limit_bytes=1024 * 1024,
            allow_http=True,
            transport=GuardedTransport(backend=backend),
        ) as (path, named):
            assert (path.name, named) == ("demo-1.zip", True)
            assert path.read_bytes() == body
        assert list((tmp_path / "incoming").iterdir()) == []

    @pytest.mark.asyncio
    async def test_loopback_is_refused_by_the_real_transport(self, tmp_path: Path) -> None:
        """No mock: the default transport refuses 127.0.0.1 without connecting."""
        for url in ("https://127.0.0.1:9/x.zip", "https://localhost:9/x.zip"):
            with pytest.raises(AddressBlockedError):
                async with downloaded(url, cache_dir=tmp_path, limit_bytes=1024, allow_http=False):
                    pass


# --- Links, names and the stored form ---------------------------------------------------


class TestLinks:
    @pytest.mark.parametrize(
        ("url", "allow_http"),
        [
            ("http://example.com/a.zip", False),
            ("ftp://example.com/a.zip", True),
            ("file:///etc/passwd", True),
            ("https://user:pass@example.com/a.zip", False),
            ("https:///a.zip", False),
            ("not a url", False),
        ],
    )
    def test_refused(self, url: str, allow_http: bool) -> None:
        with pytest.raises(ModUrlInvalidError):
            check_link(url, allow_http=allow_http)

    def test_http_only_with_debug(self) -> None:
        assert check_link("http://example.com/a.zip", allow_http=True).scheme == "http"

    def test_the_stored_link_has_no_query_or_fragment(self) -> None:
        url = check_link(
            "https://bucket.s3.amazonaws.com/mods/a%20b.zip?X-Amz-Signature=secret#x",
            allow_http=False,
        )
        assert stored_link(url) == "https://bucket.s3.amazonaws.com/mods/a%20b.zip"

    @pytest.mark.parametrize(
        ("modid", "version", "expected"),
        [
            ("demo", "1.0.0", "demo_1.0.0.zip"),
            ("de mo", "1.0/0", "de_mo_1.0_0.zip"),
        ],
    )
    def test_name_from_modinfo(self, modid: str, version: str, expected: str) -> None:
        assert name_from_modinfo(modid, version) == expected


# --- The route --------------------------------------------------------------------------


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
def settings(tmp_path: Path) -> Settings:
    # The tests run with VS_DEBUG=true (conftest); a deployment does not, so plain http
    # links are refused here as they are in production
    return Settings(
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        data_dir=tmp_path,
        debug=False,
    )


Handler = Callable[[httpx.Request], httpx.Response]


class Web:
    """The links' server: a handler per URL (without query), recording requests."""

    def __init__(self) -> None:
        self.routes: dict[str, Handler] = {}
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = str(request.url.copy_with(query=None))
        if key not in self.routes:
            return httpx.Response(404)
        return self.routes[key](request)

    def serve(self, url: str, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.routes[url] = lambda _r: httpx.Response(200, content=body, headers=headers)

    def redirect(self, url: str, location: str) -> None:
        self.routes[url] = lambda _r: httpx.Response(302, headers={"Location": location})


@pytest.fixture
def web() -> Web:
    return Web()


@pytest.fixture
def client(
    tmp_path: Path, settings: Settings, service: ModService, web: Web
) -> Generator[TestClient]:
    update_service = ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=service,
        game_version_provider=lambda: "1.22.7",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mod_service] = lambda: service
    app.dependency_overrides[get_mod_update_service] = lambda: update_service
    app.dependency_overrides[get_link_transport] = lambda: httpx.MockTransport(web.handle)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def leftovers(service: ModService) -> list[Path]:
    root = service.cache_dir / "incoming"
    return list(root.rglob("*")) if root.exists() else []


class TestLinkRoute:
    def test_installs_a_github_release_asset(
        self, client: TestClient, service: ModService, web: Web
    ) -> None:
        cdn = "https://objects.githubusercontent.com/github-production-release-asset/1"
        web.redirect(GITHUB_ASSET, f"{cdn}?X-Amz-Signature=secret")
        web.serve(
            cdn,
            demo_zip(),
            {"Content-Disposition": "attachment; filename=demo_1.0.0.zip"},
        )

        response = client.post(LINK_URL, json={"url": GITHUB_ASSET}, headers=ADMIN)

        assert response.status_code == 200
        data = response.json()["data"]
        assert (data["slug"], data["filename"], data["source"]) == (
            "demo",
            "demo_1.0.0.zip",
            "url",
        )
        assert data["compatibility"] == "not_verified"
        listed = client.get("/api/v1alpha1/mods", headers=ADMIN).json()["data"]["mods"]
        assert [(m["source"], m["source_url"]) for m in listed] == [("url", GITHUB_ASSET)]
        assert leftovers(service) == []

    def test_the_stored_link_drops_a_presigned_signature(
        self, client: TestClient, service: ModService, web: Web
    ) -> None:
        url = "https://bucket.s3.amazonaws.com/mods/demo.zip"
        web.serve(url, demo_zip())

        response = client.post(
            LINK_URL, json={"url": f"{url}?X-Amz-Signature=secret"}, headers=ADMIN
        )

        assert response.status_code == 200
        state = service.state_manager.get_mod_by_slug("demo")
        assert state is not None
        assert (state.filename, state.source_url) == ("demo.zip", url)
        assert "secret" not in service.state_manager.state_file.read_text()
        assert web.requests[0].url.query == b"X-Amz-Signature=secret"

    def test_an_unnamed_download_is_named_from_its_modinfo(
        self, client: TestClient, service: ModService, web: Web
    ) -> None:
        web.serve("https://example.com/download", demo_zip(version="2.1.0"))

        response = client.post(
            LINK_URL, json={"url": "https://example.com/download?id=3"}, headers=ADMIN
        )

        assert response.status_code == 200
        assert response.json()["data"]["filename"] == "demo_2.1.0.zip"

    @pytest.mark.parametrize(
        "url",
        ["http://example.com/demo.zip", "https://me:token@example.com/demo.zip", "nope"],
    )
    def test_an_unusable_link_is_422(self, client: TestClient, web: Web, url: str) -> None:
        response = client.post(LINK_URL, json={"url": url}, headers=ADMIN)

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == ErrorCode.MOD_URL_INVALID
        assert web.requests == []

    def test_a_redirect_to_plain_http_is_422(self, client: TestClient, web: Web) -> None:
        web.redirect("https://example.com/demo.zip", "http://example.com/demo.zip")

        response = client.post(
            LINK_URL, json={"url": "https://example.com/demo.zip"}, headers=ADMIN
        )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == ErrorCode.MOD_URL_INVALID
        assert len(web.requests) == 1

    def test_five_redirects_are_followed(self, client: TestClient, web: Web) -> None:
        for n in range(5):
            web.redirect(f"https://example.com/{n}", f"/{n + 1}")
        web.serve("https://example.com/5", demo_zip())

        response = client.post(LINK_URL, json={"url": "https://example.com/0"}, headers=ADMIN)

        assert response.status_code == 200
        assert len(web.requests) == 6

    def test_credentials_in_a_redirect_are_422(self, client: TestClient, web: Web) -> None:
        web.redirect("https://example.com/demo.zip", "https://me:pw@example.com/real.zip")

        response = client.post(
            LINK_URL, json={"url": "https://example.com/demo.zip"}, headers=ADMIN
        )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == ErrorCode.MOD_URL_INVALID
        assert len(web.requests) == 1

    def test_a_304_is_an_answer_not_a_redirect(self, client: TestClient, web: Web) -> None:
        web.routes["https://example.com/demo.zip"] = lambda _r: httpx.Response(
            304, headers={"Location": "https://example.com/other.zip"}
        )

        response = client.post(
            LINK_URL, json={"url": "https://example.com/demo.zip"}, headers=ADMIN
        )

        assert response.status_code == 502
        assert "304" in response.json()["detail"]["message"]
        assert len(web.requests) == 1

    def test_a_refused_link_is_logged_without_its_password_or_signature(
        self, client: TestClient, captured_logs: StringIO
    ) -> None:
        response = client.post(
            LINK_URL,
            json={"url": "https://user:hunter2@example.com/mod.zip?sig=SECRET"},
            headers=ADMIN,
        )

        assert response.status_code == 422
        text = captured_logs.getvalue()
        assert "mod_link_install_refused" in text
        assert "hunter2" not in text
        assert "SECRET" not in text

    def test_more_than_five_redirects_is_422(self, client: TestClient, web: Web) -> None:
        for n in range(7):
            web.redirect(f"https://example.com/{n}", f"/{n + 1}")

        response = client.post(LINK_URL, json={"url": "https://example.com/0"}, headers=ADMIN)

        assert response.status_code == 422
        assert "more than 5" in response.json()["detail"]["message"]
        assert len(web.requests) == 6

    def test_an_internal_host_is_422_blocked_with_the_real_transport(
        self, client: TestClient, service: ModService
    ) -> None:
        app.dependency_overrides.pop(get_link_transport)

        response = client.post(
            LINK_URL, json={"url": "https://127.0.0.1:9/demo.zip"}, headers=ADMIN
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.MOD_URL_BLOCKED
        assert "127.0.0.1" in detail["message"]
        assert leftovers(service) == []

    @pytest.mark.parametrize("status", [404, 503])
    def test_an_error_answer_is_502(
        self, client: TestClient, service: ModService, web: Web, status: int
    ) -> None:
        web.routes["https://example.com/demo.zip"] = lambda _r: httpx.Response(status)
        message = str(status)

        response = client.post(
            LINK_URL, json={"url": "https://example.com/demo.zip"}, headers=ADMIN
        )

        assert response.status_code == 502
        detail = response.json()["detail"]
        assert detail["code"] == ErrorCode.DOWNLOAD_FAILED
        assert message in detail["message"]
        assert leftovers(service) == []

    @pytest.mark.parametrize("error", [httpx.ReadTimeout("slow"), httpx.ConnectError("refused")])
    def test_a_timeout_or_connection_error_is_502(
        self, client: TestClient, web: Web, error: Exception
    ) -> None:
        def fail(_r: httpx.Request) -> httpx.Response:
            raise error

        web.routes["https://example.com/demo.zip"] = fail

        response = client.post(
            LINK_URL, json={"url": "https://example.com/demo.zip"}, headers=ADMIN
        )

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == ErrorCode.DOWNLOAD_FAILED

    def test_a_download_over_the_limit_is_413(
        self, client: TestClient, service: ModService, web: Web, settings: Settings
    ) -> None:
        settings.mod_upload_max_mb = 1
        web.serve("https://example.com/big.zip", b"x" * (1024 * 1024 + 1))

        response = client.post(LINK_URL, json={"url": "https://example.com/big.zip"}, headers=ADMIN)

        assert response.status_code == 413
        assert leftovers(service) == []

    def test_a_streamed_download_over_the_limit_is_413(
        self, client: TestClient, service: ModService, web: Web, settings: Settings
    ) -> None:
        settings.mod_upload_max_mb = 1

        async def chunks() -> AsyncIterator[bytes]:
            for _ in range(3):
                yield b"x" * (512 * 1024)

        def stream(_r: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=chunks())

        web.routes["https://example.com/big.zip"] = stream

        response = client.post(LINK_URL, json={"url": "https://example.com/big.zip"}, headers=ADMIN)

        assert response.status_code == 413
        assert leftovers(service) == []

    def test_a_file_that_is_not_a_mod_is_422(self, client: TestClient, web: Web) -> None:
        web.serve("https://example.com/page.zip", b"<html>login</html>")

        response = client.post(
            LINK_URL, json={"url": "https://example.com/page.zip"}, headers=ADMIN
        )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == ErrorCode.MOD_FILE_INVALID

    def test_an_installed_mod_is_409_then_replaced_when_asked(
        self, client: TestClient, service: ModService, web: Web
    ) -> None:
        web.serve("https://example.com/demo_1.zip", demo_zip(version="1.0.0"))
        web.serve("https://example.com/demo_2.zip", demo_zip(version="2.0.0"))
        assert (
            client.post(
                LINK_URL, json={"url": "https://example.com/demo_1.zip"}, headers=ADMIN
            ).status_code
            == 200
        )

        refused = client.post(
            LINK_URL, json={"url": "https://example.com/demo_2.zip"}, headers=ADMIN
        )
        replaced = client.post(
            LINK_URL,
            json={"url": "https://example.com/demo_2.zip", "replace": True},
            headers=ADMIN,
        )

        assert refused.status_code == 409
        assert refused.json()["detail"]["source"] == "url"
        assert replaced.status_code == 200
        assert (replaced.json()["data"]["replaced"], replaced.json()["data"]["version"]) == (
            True,
            "2.0.0",
        )
        state = service.state_manager.get_mod_by_slug("demo")
        assert state is not None
        assert state.source_url == "https://example.com/demo_2.zip"

    def test_a_monitor_key_is_refused(self, client: TestClient, web: Web) -> None:
        response = client.post(LINK_URL, json={"url": GITHUB_ASSET}, headers=MONITOR)

        assert response.status_code == 403
        assert web.requests == []


class TestNoProxyFromTheEnvironment:
    @pytest.mark.asyncio
    async def test_https_proxy_is_ignored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With trust_env the request would go to the proxy, not to this transport."""
        monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
        monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")
        transport = httpx.MockTransport(lambda _r: httpx.Response(200, content=demo_zip()))

        async with downloaded(
            "https://example.com/demo.zip",
            cache_dir=tmp_path,
            limit_bytes=1024 * 1024,
            allow_http=False,
            transport=transport,
        ) as (path, _named):
            assert path.read_bytes() == demo_zip()


class TestDownloadErrorsAreTyped:
    @pytest.mark.asyncio
    async def test_a_redirect_without_location_is_an_error_answer(self, tmp_path: Path) -> None:
        transport = httpx.MockTransport(lambda _r: httpx.Response(302))

        with pytest.raises(LinkDownloadError, match="302"):
            async with downloaded(
                "https://example.com/a.zip",
                cache_dir=tmp_path,
                limit_bytes=1024,
                allow_http=False,
                transport=transport,
            ):
                pass
