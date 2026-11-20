"""Tests for frontend file serving, run against the real route registration."""

import json
import re
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import (
    FILE_SECURITY_HEADERS,
    WEB_ROUTE_PREFIXES,
    frontend_security_headers,
    register_frontend,
)

INDEX = "<html>SPA index</html>"
PRIVATE = "outside the static directory"


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    root = tmp_path / "static"
    (root / "assets").mkdir(parents=True)
    (root / "nested").mkdir()
    (root / "index.html").write_text(INDEX)
    (root / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    (root / "nested" / "page.txt").write_text("nested file")
    (root / "assets" / "main.js").write_text("console.log('app');")

    (tmp_path / "private.txt").write_text(PRIVATE)
    sibling = tmp_path / "static-private"
    sibling.mkdir()
    (sibling / "private.txt").write_text(PRIVATE)
    return root


@pytest.fixture
def client(static_dir: Path) -> TestClient:
    target = FastAPI()
    register_frontend(target, static_dir, Settings(api_key_admin="admin"))
    return TestClient(target)


def assert_serves_index(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.text == INDEX


def assert_not_found(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert PRIVATE not in response.text
    assert INDEX not in response.text


class TestFrontendFiles:
    def test_serves_file_in_static_dir(self, client: TestClient) -> None:
        response = client.get("/favicon.ico")

        assert response.status_code == 200
        assert response.content == b"\x00\x00\x01\x00"

    def test_serves_file_in_subdirectory(self, client: TestClient) -> None:
        response = client.get("/nested/page.txt")

        assert response.status_code == 200
        assert response.text == "nested file"

    def test_serves_mounted_assets(self, client: TestClient) -> None:
        response = client.get("/assets/main.js")

        assert response.status_code == 200
        assert "console.log('app');" in response.text

    @pytest.mark.parametrize("path", ["/", "/dashboard", "/game-server/mods/browse"])
    def test_client_routes_fall_back_to_index(self, client: TestClient, path: str) -> None:
        assert_serves_index(client, path)

    @pytest.mark.parametrize(
        "path",
        [
            "/game-server/mods/browse/some.mod",
            "/game-server/mods/browse/carrycapacity.v2",
            "/mods/browse/some.mod",
            "/config/file.json",
            "/game-server/mods/installed/",
        ],
    )
    def test_web_ui_routes_with_a_dot_fall_back_to_index(
        self, client: TestClient, path: str
    ) -> None:
        """A mod slug can contain a dot; the web UI's routes always get the page (ADR-2)."""
        assert_serves_index(client, path)

    @pytest.mark.parametrize(
        "path", ["/missing.png", "/favicon.svg", "/nested/missing.js", "/vite.svg", "/a.b/c.txt"]
    )
    def test_missing_files_with_an_extension_are_404(self, client: TestClient, path: str) -> None:
        """A missing file outside the web UI's routes fails visibly (FR329, ADR-2)."""
        assert_not_found(client, path)

    def test_a_missing_file_has_the_page_headers(self, static_dir: Path) -> None:
        target = FastAPI()
        register_frontend(target, static_dir, Settings(api_key_admin="admin", csp_mode="enforce"))

        response = TestClient(target).get("/missing.png")

        assert response.status_code == 404
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "content-security-policy" in response.headers

    def test_route_prefixes_match_the_web_ui(self) -> None:
        """Every top-level route of web/src/App.tsx is a web UI prefix (ADR-2 decision 2)."""
        app_tsx = Path(__file__).parents[2] / "web" / "src" / "App.tsx"
        top_level = set(re.findall(r'<Route path="/([^/"*]+)', app_tsx.read_text()))

        assert top_level
        assert top_level <= set(WEB_ROUTE_PREFIXES)

    def test_directory_falls_back_to_index(self, client: TestClient) -> None:
        assert_serves_index(client, "/nested")

    def test_assets_are_optional(self, tmp_path: Path) -> None:
        root = tmp_path / "bare"
        root.mkdir()
        (root / "index.html").write_text(INDEX)
        target = FastAPI()
        register_frontend(target, root, Settings(api_key_admin="admin"))

        assert_serves_index(TestClient(target), "/dashboard")


class TestFrontendContainment:
    @pytest.mark.parametrize(
        "path",
        [
            "/..%2Fprivate.txt",
            "/nested%2F..%2F..%2Fprivate.txt",
            "/..%2Fstatic-private%2Fprivate.txt",
        ],
    )
    def test_relative_paths_cannot_leave_static_dir(self, client: TestClient, path: str) -> None:
        # A missing file with an extension is 404 (Story 24.2); never the private file
        assert_not_found(client, path)

    def test_absolute_paths_cannot_leave_static_dir(
        self, client: TestClient, static_dir: Path
    ) -> None:
        private = static_dir.parent / "private.txt"

        assert_not_found(client, f"/{quote(str(private), safe='')}")

    def test_symlinks_cannot_leave_static_dir(self, client: TestClient, static_dir: Path) -> None:
        (static_dir / "link.txt").symlink_to(static_dir.parent / "private.txt")

        assert_not_found(client, "/link.txt")

    @pytest.mark.parametrize("path", ["/bad%00name", "/" + "a" * 5000])
    def test_invalid_paths_fall_back_to_index(self, client: TestClient, path: str) -> None:
        assert_serves_index(client, path)


class TestRuntimeConfig:
    """GET /config.js hands the web UI its API key at runtime (Story 15.2, ADR-5)."""

    def _client(self, static_dir: Path, settings: Settings) -> TestClient:
        target = FastAPI()
        register_frontend(target, static_dir, settings)
        return TestClient(target)

    def test_serves_vs_api_key(self, static_dir: Path) -> None:
        client = self._client(static_dir, Settings(api_key_admin="admin", api_key="web"))

        response = client.get("/config.js")

        assert response.status_code == 200
        assert response.text == 'window.__VSM_CONFIG__ = {"apiKey": "web"};\n'

    def test_serves_an_empty_key_when_vs_api_key_is_unset(self, static_dir: Path) -> None:
        # No fallback to the Admin key (Epic 19 ADR-5)
        client = self._client(static_dir, Settings(api_key_admin="admin", api_key=None))

        assert client.get("/config.js").text == 'window.__VSM_CONFIG__ = {"apiKey": ""};\n'

    def test_key_is_json_encoded(self, static_dir: Path) -> None:
        key = 'a"b\\c\u2028'
        client = self._client(static_dir, Settings(api_key_admin="admin", api_key=key))

        body = client.get("/config.js").text

        assert body == f"window.__VSM_CONFIG__ = {json.dumps({'apiKey': key})};\n"
        assert '"a\\"b' in body and "\\u2028" in body

    def test_markup_characters_in_the_key_are_escaped(self, static_dir: Path) -> None:
        # Defence in depth (Story 19.2 review L-1): the body could never close a script element
        key = "k</script><script>alert(1)</script>&amp;"
        client = self._client(static_dir, Settings(api_key_admin="admin", api_key=key))

        body = client.get("/config.js").text

        assert body == (
            'window.__VSM_CONFIG__ = {"apiKey": '
            '"k\\u003c/script\\u003e\\u003cscript\\u003ealert(1)\\u003c/script\\u003e\\u0026amp;"'
            "};\n"
        )
        assert not any(char in body for char in "<>&")
        prefix, suffix = "window.__VSM_CONFIG__ = ", ";\n"
        assert json.loads(body.removeprefix(prefix).removesuffix(suffix)) == {"apiKey": key}

    def test_is_a_never_cached_script(self, static_dir: Path) -> None:
        client = self._client(static_dir, Settings(api_key_admin="admin", api_key=None))

        response = client.get("/config.js")

        assert response.headers["content-type"].startswith("application/javascript")
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_other_sites_cannot_include_it(self, static_dir: Path) -> None:
        # A classic <script src> from another site's page skips CORS; CORP blocks it
        client = self._client(static_dir, Settings(api_key_admin="admin", api_key=None))

        response = client.get("/config.js")

        assert response.headers["cross-origin-resource-policy"] == "same-origin"

    def test_wins_over_a_built_placeholder(self, static_dir: Path) -> None:
        (static_dir / "config.js").write_text("window.__VSM_CONFIG__ = {};")
        client = self._client(static_dir, Settings(api_key_admin="admin", api_key="web"))

        assert '"apiKey": "web"' in client.get("/config.js").text


# Written out, not imported from main: a changed directive is a deliberate edit in two places
POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-src 'none'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
ALWAYS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}
HEADERS_BY_MODE: dict[str, dict[str, str]] = {
    "enforce": {"Content-Security-Policy": POLICY, "X-Frame-Options": "DENY", **ALWAYS},
    "report-only": {"Content-Security-Policy-Report-Only": POLICY, **ALWAYS},
    "off": dict(ALWAYS),
}
POLICY_HEADERS = ("content-security-policy", "content-security-policy-report-only")


class TestSecurityHeaders:
    """The web UI's pages carry the Content-Security-Policy (Story 19.3, Epic 19 ADR-6)."""

    def _client(self, static_dir: Path, csp_mode: str) -> TestClient:
        target = FastAPI()
        register_frontend(target, static_dir, Settings(api_key_admin="admin", csp_mode=csp_mode))
        return TestClient(target)

    @pytest.mark.parametrize("mode", ["enforce", "report-only", "off"])
    def test_headers_for_each_mode(self, mode: str) -> None:
        assert frontend_security_headers(mode) == HEADERS_BY_MODE[mode]

    @pytest.mark.parametrize(
        "path", ["/", "/dashboard", "/game-server/mods/browse/x", "/favicon.ico"]
    )
    def test_enforce(self, static_dir: Path, path: str) -> None:
        response = self._client(static_dir, "enforce").get(path)

        assert response.status_code == 200
        assert response.headers["content-security-policy"] == POLICY
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-frame-options"] == "DENY"
        assert "content-security-policy-report-only" not in response.headers

    @pytest.mark.parametrize(
        "path", ["/", "/dashboard", "/game-server/mods/browse/x", "/favicon.ico"]
    )
    def test_report_only(self, static_dir: Path, path: str) -> None:
        response = self._client(static_dir, "report-only").get(path)

        assert response.status_code == 200
        assert response.headers["content-security-policy-report-only"] == POLICY
        assert "content-security-policy" not in response.headers
        assert "x-frame-options" not in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"

    @pytest.mark.parametrize(
        "path", ["/", "/dashboard", "/game-server/mods/browse/x", "/favicon.ico"]
    )
    def test_off(self, static_dir: Path, path: str) -> None:
        response = self._client(static_dir, "off").get(path)

        assert response.status_code == 200
        assert not any(header in response.headers for header in POLICY_HEADERS)
        assert "x-frame-options" not in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"

    def test_file_keeps_its_own_headers(self, static_dir: Path) -> None:
        response = self._client(static_dir, "enforce").get("/favicon.ico")

        assert "etag" in response.headers
        assert "last-modified" in response.headers

    def test_config_js_keeps_exactly_its_three_headers(self, static_dir: Path) -> None:
        response = self._client(static_dir, "enforce").get("/config.js")

        assert not any(header in response.headers for header in POLICY_HEADERS)
        assert "x-frame-options" not in response.headers
        assert "referrer-policy" not in response.headers
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["cross-origin-resource-policy"] == "same-origin"
        assert response.headers["x-content-type-options"] == "nosniff"

    @pytest.mark.parametrize("mode", ["enforce", "report-only", "off"])
    def test_assets_carry_the_file_headers(self, static_dir: Path, mode: str) -> None:
        """nosniff and Referrer-Policy apply to files too (FR330, VSS-koo1 item 1)."""
        response = self._client(static_dir, mode).get("/assets/main.js")

        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert {k: response.headers[k] for k in FILE_SECURITY_HEADERS} == FILE_SECURITY_HEADERS

    def test_assets_have_no_policy(self, static_dir: Path) -> None:
        response = self._client(static_dir, "enforce").get("/assets/main.js")

        assert response.status_code == 200
        assert not any(header in response.headers for header in POLICY_HEADERS)
        assert "x-frame-options" not in response.headers
