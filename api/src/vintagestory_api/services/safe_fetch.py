"""An HTTP transport that never connects to an internal address (Epic 28 ADR-5).

A link an administrator gives could point at the Docker host, a cloud metadata service or
the LAN. The check is made when each connection is opened, on the addresses the host name
resolves to, and the connection goes to the address that was checked. So a redirect, or a
DNS answer that changes between the check and the connection, cannot reach an internal
address. TLS still verifies the certificate against the host name.

Rules (`address_refusal`):

- loopback, link-local, unspecified, multicast and reserved addresses: always refused;
- global addresses: allowed;
- any other address (private ranges, carrier-grade NAT, unique local IPv6): allowed only
  for a host named in VS_MOD_URL_PRIVATE_HOSTS (a self-hosted Forgejo on the LAN).

A host is refused when any address it resolves to is refused, so a name that answers with
a public and a private address cannot be used to reach the private one.
"""

import ipaddress
import socket
import ssl
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from typing import Any, cast

import anyio
import httpcore
import httpx

Resolver = Callable[[str, int], Awaitable[list[str]]]
"""Resolves a host name and port to IP address strings."""

_IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

_CORE_ERRORS = (
    httpcore.NetworkError,
    httpcore.ProtocolError,
    httpcore.ProxyError,
    httpcore.UnsupportedProtocol,
)
"""httpcore's errors other than timeouts (its common base is not exported)."""


class AddressBlockedError(Exception):
    """A connection to an internal address was refused (Epic 28 ADR-5 decision 3)."""

    def __init__(self, host: str) -> None:
        self.host = host
        super().__init__(
            f"The link's host {host} is on a private or local network, which the manager "
            "does not connect to. A LAN host can be allowed in VS_MOD_URL_PRIVATE_HOSTS."
        )


def parse_private_hosts(value: str) -> frozenset[str]:
    """VS_MOD_URL_PRIVATE_HOSTS: comma-separated host names, compared lower-cased."""
    return frozenset(h.strip().lower().rstrip(".") for h in value.split(",") if h.strip())


def _as_address(text: str) -> _IpAddress:
    """The IP address of a resolver answer, without an IPv6 zone, IPv4-mapped unwrapped."""
    address = ipaddress.ip_address(text.split("%", 1)[0])
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def address_refusal(address: _IpAddress, *, private_allowed: bool) -> str | None:
    """Why the address is refused, or None when it may be connected to."""
    if address.is_loopback:
        return "loopback"
    if address.is_link_local:
        return "link-local"
    if address.is_unspecified:
        return "unspecified"
    if address.is_multicast:
        return "multicast"
    if address.is_reserved:
        return "reserved"
    if address.is_global:
        return None
    return None if private_allowed else "private"


async def resolve_with_anyio(host: str, port: int) -> list[str]:
    answers = await anyio.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(sockaddr[0]) for _family, _type, _proto, _name, sockaddr in answers]


class GuardedBackend(httpcore.AsyncNetworkBackend):
    """A network backend that checks each resolved address before connecting to it."""

    def __init__(
        self,
        private_hosts: frozenset[str] = frozenset(),
        *,
        inner: httpcore.AsyncNetworkBackend | None = None,
        resolve: Resolver = resolve_with_anyio,
    ) -> None:
        self._private_hosts = private_hosts
        # httpcore declares AnyIOBackend as a stub when anyio is missing; anyio is a
        # dependency here, so it is the real backend
        self._inner: httpcore.AsyncNetworkBackend = (
            inner
            if inner is not None
            else cast(httpcore.AsyncNetworkBackend, httpcore.AnyIOBackend())
        )
        self._resolve = resolve

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        name = host.lower().rstrip(".")
        private_allowed = name in self._private_hosts
        try:
            with anyio.fail_after(timeout):
                answers = await self._resolve(host, port)
        except TimeoutError as e:  # before OSError, which it is a kind of
            raise httpcore.ConnectTimeout(f"Resolving {host} timed out") from e
        except OSError as e:  # socket.gaierror is an OSError
            raise httpcore.ConnectError(f"Could not resolve {host}: {e}") from e
        addresses = [_as_address(a) for a in answers]
        if not addresses:
            raise httpcore.ConnectError(f"Could not resolve {host}")
        if any(address_refusal(a, private_allowed=private_allowed) for a in addresses):
            raise AddressBlockedError(host)
        last_error: Exception | None = None
        for address in addresses:
            try:
                return await self._inner.connect_tcp(
                    str(address),
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as e:
                last_error = e
        assert last_error is not None
        raise last_error

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise httpcore.ConnectError("Unix sockets are not used for links")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


class _ResponseStream(httpx.AsyncByteStream):
    def __init__(self, stream: Any) -> None:
        self._stream = stream

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            async for chunk in self._stream:
                yield chunk
        except httpcore.TimeoutException as e:
            raise httpx.ReadTimeout(str(e)) from e
        except _CORE_ERRORS as e:
            raise httpx.ReadError(str(e)) from e

    async def aclose(self) -> None:
        if hasattr(self._stream, "aclose"):
            await self._stream.aclose()


class GuardedTransport(httpx.AsyncBaseTransport):
    """An httpx transport over `GuardedBackend`, with no proxy (Epic 28 ADR-5)."""

    def __init__(
        self,
        private_hosts: frozenset[str] = frozenset(),
        *,
        backend: httpcore.AsyncNetworkBackend | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context or httpx.create_ssl_context(trust_env=False),
            network_backend=backend or GuardedBackend(private_hosts),
            max_connections=4,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if not isinstance(request.stream, httpx.AsyncByteStream):
            raise TypeError("GuardedTransport needs an async request body")
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        try:
            response = await self._pool.handle_async_request(core_request)
        except httpcore.ConnectTimeout as e:
            raise httpx.ConnectTimeout(str(e), request=request) from e
        except httpcore.TimeoutException as e:
            raise httpx.TimeoutException(str(e), request=request) from e
        except httpcore.ConnectError as e:
            raise httpx.ConnectError(str(e), request=request) from e
        except _CORE_ERRORS as e:
            raise httpx.TransportError(str(e), request=request) from e
        # httpcore types `extensions` as a bare dict; httpx reads the reason phrase and the
        # HTTP version from it
        extensions: dict[str, Any] = dict(getattr(response, "extensions"))
        return httpx.Response(
            status_code=response.status,
            headers=response.headers,
            stream=_ResponseStream(response.stream),
            extensions=extensions,
        )

    async def aclose(self) -> None:
        await self._pool.aclose()
