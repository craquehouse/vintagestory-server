"""Updates for mods installed from a GitHub or Forgejo release (Story 28.5, ADR-7).

A mod installed from a link whose path is `/{owner}/{repo}/releases/download/{tag}/{asset}`
is a release mod: on `github.com` a GitHub release, on any other host a Forgejo (or
Gitea) release. The update check asks the repo's latest release (drafts and pre-releases
skipped by both APIs) through the guarded transport, picks the matching `.zip` asset and
compares the tag with the installed `modinfo.json` version.
"""

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import cast
from urllib.parse import quote

import anyio
import httpx

from vintagestory_api.services.mod_link import (
    LinkDownloadError,
    check_link,
    link_client,
    open_following,
)
from vintagestory_api.services.safe_fetch import GuardedTransport

LOOKUP_TIMEOUT_S = 60.0
"""The whole lookup's limit, on top of the connect and read timeouts (review)."""

MAX_RELEASE_JSON_BYTES = 2 * 1024 * 1024
"""A latest-release answer is a few kilobytes; anything far larger is refused."""

_VERSION_PART = re.compile(r"v?\d+(?:\.\d+)+(?:[-+][0-9A-Za-z.]+)?|v\d+", re.IGNORECASE)


@dataclass(frozen=True)
class ReleaseLink:
    """A release asset link, split into its parts."""

    scheme: str
    host: str
    port: int | None
    owner: str
    repo: str
    tag: str
    asset: str

    @property
    def is_github(self) -> bool:
        return self.host.lower() == "github.com"

    @property
    def _netloc(self) -> str:
        return self.host if self.port is None else f"{self.host}:{self.port}"

    def latest_release_url(self) -> str:
        """The repo's latest release in its forge's API (ADR-7 decision 2).

        Owner and repo are re-encoded, so a `?` or `#` in them stays part of the path
        (Story 28.5 review).
        """
        repo_path = f"{quote(self.owner, safe='')}/{quote(self.repo, safe='')}"
        if self.is_github:
            return f"https://api.github.com/repos/{repo_path}/releases/latest"
        return f"{self.scheme}://{self._netloc}/api/v1/repos/{repo_path}/releases/latest"

    def asset_link(self, tag: str, asset: str) -> str:
        """The release asset's link in the same `/releases/download/` form.

        Stored as a release mod's link after an update: Forgejo's API gives an asset's
        download URL as `/attachments/<uuid>`, which is not a release link, so storing
        it would end the mod's updates (Story 28.5 review). Both forges serve this form.
        """
        parts = (self.owner, self.repo, "releases", "download", tag, asset)
        path = "/".join(quote(part, safe="") for part in parts)
        return f"{self.scheme}://{self._netloc}/{path}"


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str


@dataclass(frozen=True)
class LatestRelease:
    tag: str
    assets: list[ReleaseAsset]


ReleaseLookup = Callable[[ReleaseLink], Awaitable[LatestRelease]]
"""Fetches a release link's latest release; the update check's way to ask a forge."""


def parse_release_link(url: str | None) -> ReleaseLink | None:
    """The release link's parts, or None when the link is not a release asset link."""
    if not url:
        return None
    try:
        parsed = httpx.URL(url)
    except httpx.InvalidURL, TypeError, ValueError:
        return None
    if parsed.scheme not in ("https", "http") or not parsed.host:
        return None
    parts = parsed.path.split("/")
    # ['', owner, repo, 'releases', 'download', tag, asset]
    if len(parts) != 7 or parts[0] != "" or parts[3:5] != ["releases", "download"]:
        return None
    # httpx has already decoded the path's escapes; decoding again would change a name
    # with a literal `%hh` in it (Story 28.5 review)
    owner, repo, tag, asset = parts[1], parts[2], parts[5], parts[6]
    if not all((owner, repo, tag, asset)) or "/" in owner + repo:
        return None
    return ReleaseLink(
        scheme=parsed.scheme,
        host=parsed.host,
        port=parsed.port,
        owner=owner,
        repo=repo,
        tag=tag,
        asset=asset,
    )


def tag_version(tag: str) -> str:
    """The version a tag names: the tag without a leading `v` (ADR-7 decision 4)."""
    return tag[1:] if tag[:1] in ("v", "V") and tag[1:2].isdigit() else tag


def asset_stem(name: str) -> str:
    """The asset name with its version-like parts removed, lower-cased (ADR-7 decision 3)."""
    return _VERSION_PART.sub("", name).lower()


def match_asset(installed_asset: str, assets: list[ReleaseAsset]) -> ReleaseAsset | None:
    """The release's `.zip` asset that matches the installed one, or None (decision 3).

    The asset whose name, without version-like parts, equals the installed asset's;
    else, when the release has exactly one `.zip`, that one.
    """
    zips = [a for a in assets if a.name.lower().endswith(".zip")]
    wanted = asset_stem(installed_asset)
    same = [a for a in zips if asset_stem(a.name) == wanted]
    if len(same) == 1:
        return same[0]
    if not same and len(zips) == 1:
        return zips[0]
    return None


def is_newer(candidate: str, installed: str) -> bool | None:
    """Whether `candidate` is a newer version than `installed`; None if either is unparsable."""
    # services.mod_updates imports this module; import its parser here to avoid a cycle
    from vintagestory_api.services.mod_updates import parse_base_version

    new, old = parse_base_version(candidate), parse_base_version(installed)
    if new is None or old is None:
        return None
    width = max(len(new), len(old))
    return new + (0,) * (width - len(new)) > old + (0,) * (width - len(old))


def _parse_latest(body: bytes) -> LatestRelease:
    """The tag and assets of a GitHub or Forgejo latest-release answer (same fields)."""
    try:
        data: object = json.loads(body)
    except ValueError as e:
        raise LinkDownloadError(f"The release answer is not JSON: {e}") from None
    if not isinstance(data, dict):
        raise LinkDownloadError("The release answer is not an object.")
    release = cast(dict[str, object], data)
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not tag:
        raise LinkDownloadError("The latest release has no tag.")
    assets: list[ReleaseAsset] = []
    raw_assets = release.get("assets")
    if isinstance(raw_assets, list):
        for item in cast(list[object], raw_assets):
            if not isinstance(item, dict):
                continue
            entry = cast(dict[str, object], item)
            name, url = entry.get("name"), entry.get("browser_download_url")
            if isinstance(name, str) and isinstance(url, str):
                assets.append(ReleaseAsset(name=name, download_url=url))
    return LatestRelease(tag=tag, assets=assets)


def release_lookup(
    *,
    allow_http: bool,
    private_hosts: frozenset[str] = frozenset(),
    transport: httpx.AsyncBaseTransport | None = None,
) -> ReleaseLookup:
    """A lookup that asks the forge through the guarded transport (ADR-7 decision 2)."""

    async def lookup(link: ReleaseLink) -> LatestRelease:
        url = check_link(link.latest_release_url(), allow_http=allow_http)
        headers = {"Accept": "application/vnd.github+json"} if link.is_github else {}
        # A new transport per lookup: closing the client closes its transport
        client_transport = transport or GuardedTransport(private_hosts)
        try:
            with anyio.fail_after(LOOKUP_TIMEOUT_S):
                body = await _read_latest(client_transport, url, allow_http, headers)
        except TimeoutError:
            raise LinkDownloadError(
                f"The forge took longer than {int(LOOKUP_TIMEOUT_S)} seconds to answer."
            ) from None
        return _parse_latest(body)

    return lookup


async def _read_latest(
    transport: httpx.AsyncBaseTransport,
    url: httpx.URL,
    allow_http: bool,
    headers: dict[str, str],
) -> bytes:
    """The latest-release answer's body, at most MAX_RELEASE_JSON_BYTES."""
    async with link_client(transport) as client:
        try:
            response = await open_following(client, url, allow_http=allow_http, headers=headers)
        except httpx.TimeoutException:
            raise LinkDownloadError("The forge took too long to answer.") from None
        except httpx.TransportError as e:
            raise LinkDownloadError(f"Could not reach the forge: {e}") from None
        try:
            if not response.is_success:
                raise LinkDownloadError(
                    f"The forge answered {response.status_code} {response.reason_phrase}."
                )
            body = b""
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) > MAX_RELEASE_JSON_BYTES:
                    raise LinkDownloadError("The release answer is too large.")
        finally:
            await response.aclose()
    return body
