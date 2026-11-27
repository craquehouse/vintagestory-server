"""Downloading a mod from a link (Story 28.3, Epic 28 ADR-5).

`downloaded` fetches the link through `GuardedTransport` (addresses checked at connect
time), follows at most five redirects itself so each hop's scheme is checked, ignores
proxy settings, applies the time limits and the size limit, and yields the file in an
incoming working folder that is removed on every exit. `ModService.install_archive`
installs it.
"""

import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from email.message import Message
from pathlib import Path
from urllib.parse import unquote

import anyio
import httpx
import structlog

from vintagestory_api.services.mod_upload import (
    ModFileTooLargeError,
    incoming_folder,
    safe_archive_name,
    write_limited,
)
from vintagestory_api.services.safe_fetch import GuardedTransport

logger = structlog.get_logger()

MAX_REDIRECTS = 5
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 30.0
TOTAL_TIMEOUT_S = 300.0

UNNAMED = "download.zip"
"""The working name of a download whose name cannot be used; the route renames it."""

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class ModUrlInvalidError(Exception):
    """The link (or a redirect) is not one the manager follows (ADR-5 decision 2)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class LinkDownloadError(Exception):
    """The download failed: an error answer, a timeout or a connection error."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def check_link(url: str, *, allow_http: bool) -> httpx.URL:
    """The link as a URL, or ModUrlInvalidError (https only; http with VS_DEBUG)."""
    try:
        parsed = httpx.URL(url)
    except (httpx.InvalidURL, TypeError, ValueError) as e:
        raise ModUrlInvalidError(f"The link is not a valid URL: {e}") from None
    schemes = ("https", "http") if allow_http else ("https",)
    if parsed.scheme not in schemes:
        raise ModUrlInvalidError(
            "The link must start with https:// (plain http is only for testing, with "
            "VS_DEBUG=true)."
        )
    if not parsed.host:
        raise ModUrlInvalidError("The link has no host.")
    if parsed.userinfo:
        raise ModUrlInvalidError(
            "The link must not contain a user name or password; use a public or presigned link."
        )
    return parsed


def stored_link(url: httpx.URL) -> str:
    """The link without its query string, fragment or user info (ADR-1 decision 4).

    A presigned S3 link carries its signature in the query, so the stored form never
    holds a credential and can be shown and logged. `check_link` has already refused
    user info.
    """
    return str(url.copy_with(query=None, fragment=None))


def name_from_response(response: httpx.Response) -> str | None:
    """A usable file name from Content-Disposition, else the final URL's last segment."""
    disposition = response.headers.get("content-disposition")
    if disposition:
        message = Message()
        message["content-disposition"] = disposition
        candidate = message.get_filename()
        if candidate and safe_archive_name(candidate):
            return candidate
    segment = unquote(response.url.path.rsplit("/", 1)[-1])
    return segment if safe_archive_name(segment) else None


def name_from_modinfo(modid: str, version: str) -> str | None:
    """`{modid}_{version}.zip` with unusual characters replaced, if it is a usable name."""
    stem = _UNSAFE_NAME_CHARS.sub("_", f"{modid}_{version}").strip("._")
    return safe_archive_name(f"{stem}.zip") if stem else None


def _client(transport: httpx.AsyncBaseTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=transport,
        follow_redirects=False,
        trust_env=False,
        timeout=httpx.Timeout(READ_TIMEOUT_S, connect=CONNECT_TIMEOUT_S),
        headers={"User-Agent": "vintagestory-server-manager"},
    )


async def _fetch(
    client: httpx.AsyncClient,
    url: httpx.URL,
    folder: Path,
    *,
    limit_bytes: int,
    allow_http: bool,
) -> tuple[Path, bool]:
    """Download into `folder`; returns the file and whether its name came from the server."""
    current = url
    for _hop in range(MAX_REDIRECTS + 1):
        request = client.build_request("GET", current)
        response = await client.send(request, stream=True)
        try:
            # 301, 302, 303, 307 and 308 only: a 304 or 305 is an answer, not a redirect
            if response.has_redirect_location:
                location = response.headers["location"]
                current = check_link(str(current.join(location)), allow_http=allow_http)
                continue
            if not response.is_success:
                raise LinkDownloadError(
                    f"The server answered {response.status_code} {response.reason_phrase}."
                )
            declared = response.headers.get("content-length")
            if declared is not None and declared.isascii() and declared.isdigit():
                if int(declared) > limit_bytes:
                    raise ModFileTooLargeError(limit_bytes)
            name = name_from_response(response)
            path = folder / (name or UNNAMED)
            await write_limited(response.aiter_bytes(), path, limit_bytes)
            return path, name is not None
        finally:
            await response.aclose()
    raise ModUrlInvalidError(f"The link redirects more than {MAX_REDIRECTS} times.")


@asynccontextmanager
async def downloaded(
    url: str,
    *,
    cache_dir: Path,
    limit_bytes: int,
    allow_http: bool,
    transport: httpx.AsyncBaseTransport | None = None,
    private_hosts: frozenset[str] = frozenset(),
) -> AsyncGenerator[tuple[Path, bool]]:
    """The downloaded file and whether its name came from the server, removed on exit.

    Raises:
        ModUrlInvalidError: The link or a redirect is not https (or http with VS_DEBUG),
            has credentials, or there are more than five redirects.
        AddressBlockedError: A host resolves to an internal address (ADR-5 decision 3).
        ModFileTooLargeError: Over the size limit, by Content-Length or while reading.
        LinkDownloadError: An error answer, a timeout or a connection error.
    """
    link = check_link(url, allow_http=allow_http)
    with incoming_folder(cache_dir) as folder:
        async with _client(transport or GuardedTransport(private_hosts)) as client:
            try:
                with anyio.fail_after(TOTAL_TIMEOUT_S):
                    result = await _fetch(
                        client, link, folder, limit_bytes=limit_bytes, allow_http=allow_http
                    )
            except TimeoutError:
                raise LinkDownloadError(
                    f"The download took longer than {int(TOTAL_TIMEOUT_S)} seconds."
                ) from None
            except httpx.TimeoutException:
                raise LinkDownloadError("The server took too long to answer.") from None
            except httpx.TransportError as e:
                raise LinkDownloadError(f"Could not download the link: {e}") from None
        yield result
