"""Automatic OS routing for the fixed public YouTube Following destination.

This module deliberately offers no URL/host/proxy input to content callers.
"""

from __future__ import annotations

import http.client
import importlib
import ipaddress
import queue
import re
import socket
import ssl
import sys
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from youtube_intel.following_provider import TrackingError
from youtube_intel.providers.bilibili import (
    BilibiliError,
    _PinnedHTTPS,
    public_addresses,
)

_HOST = "www.youtube.com"
_TIMEOUT = 10.0
# Only the up-to-4-MiB alias HTML gets a separate absolute body budget.
# Each blocking read still has the transport's ten-second timeout.
_PAGE_BODY_TIMEOUT = 45.0
_PROXY_DNS_TIMEOUT = 1.0
_PROXY_DNS_SLOTS = threading.BoundedSemaphore(2)


@dataclass(frozen=True, repr=False)
class _SystemProxy:
    host: str
    port: int


def _macos_proxy_url() -> str | None:
    if sys.platform != "darwin":
        return None
    try:
        # Explicit native SystemConfiguration authority. Unlike getproxies(),
        # this cannot inherit HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY.
        values = importlib.import_module("_scproxy")._get_proxies()
        value = values.get("https")
        if value is not None and not isinstance(value, str):
            raise ValueError()
        return value
    except Exception:
        raise TrackingError("NETWORK_UNAVAILABLE") from None


def _current_proxy() -> _SystemProxy | None:
    value = _macos_proxy_url()
    if value is None:
        return None
    try:
        if not value or len(value) > 2048 or any(c.isspace() for c in value):
            raise ValueError()
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
        if (
            parsed.scheme != "http"
            or not host
            or port is None
            or not 1 <= port <= 65535
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if not re.fullmatch(
                r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", host
            ):
                raise ValueError() from None
        return _SystemProxy(host, port)
    except ValueError:
        raise TrackingError("NETWORK_UNAVAILABLE") from None


def _proxy_address(proxy: _SystemProxy) -> str:
    """Bound DNS of a trusted OS endpoint; never resolve the tunnel destination."""
    try:
        address = ipaddress.ip_address(proxy.host)
    except ValueError:
        slots = _PROXY_DNS_SLOTS
        if not slots.acquire(blocking=False):
            raise TrackingError("NETWORK_UNAVAILABLE")
        result: queue.Queue[str | None] = queue.Queue(maxsize=1)

        def resolve() -> None:
            value = None
            try:
                rows = socket.getaddrinfo(
                    proxy.host, proxy.port, type=socket.SOCK_STREAM
                )
                if 0 < len(rows) <= 512:
                    value = str(rows[0][4][0])
            except OSError:
                pass
            finally:
                result.put(value)
                slots.release()

        threading.Thread(
            target=resolve, daemon=True, name="youtube-system-proxy-dns"
        ).start()
        try:
            value = result.get(timeout=_PROXY_DNS_TIMEOUT)
            if value is None:
                raise ValueError()
            address = ipaddress.ip_address(value)
        except (queue.Empty, ValueError):
            raise TrackingError("NETWORK_UNAVAILABLE") from None
    if (
        address.is_unspecified
        or address.is_multicast
        or str(address) == "255.255.255.255"
    ):
        raise TrackingError("NETWORK_UNAVAILABLE")
    # Private/loopback addresses are legitimate OS proxy endpoints, not public
    # content destinations. This does not change public_addresses' policy.
    return str(address)


def _connection() -> http.client.HTTPSConnection:
    proxy = _current_proxy()
    if proxy is None:
        try:
            addresses = public_addresses(_HOST)
        except BilibiliError:
            # No provider request has occurred: unsafe/unusable DNS means the
            # local direct route is unavailable, not a provider refusal.
            raise TrackingError("NETWORK_UNAVAILABLE") from None
        if not addresses:
            raise TrackingError("NETWORK_UNAVAILABLE")
        return _PinnedHTTPS(_HOST, addresses[0])
    connection = http.client.HTTPSConnection(
        _proxy_address(proxy),
        proxy.port,
        timeout=_TIMEOUT,
        context=ssl.create_default_context(),
    )
    # HTTPSConnection verifies _tunnel_host, not proxy.host; no local YouTube DNS.
    connection.set_tunnel(_HOST, 443)
    return connection


def _get(path: str, limit: int, *, body_timeout: float | None = None) -> bytes:
    connection: http.client.HTTPSConnection | None = None
    deadline = time.monotonic() + _TIMEOUT
    try:
        connection = _connection()
        connection.request(
            "GET",
            path,
            headers={
                "User-Agent": "YIA-PublicContent/1.0",
                "Accept-Encoding": "identity",
            },
        )
        # HTTP/1.x Connection: close can detach this socket from the connection
        # after headers; the response still owns it until its body is consumed.
        request_socket = connection.sock
        if connection.sock is not None:
            connection.sock.settimeout(max(0.001, deadline - time.monotonic()))
        response = connection.getresponse()
        if response.status != 200:
            # Redirects are never followed, even to an approved hostname.
            raise TrackingError(
                {
                    429: "RATE_LIMITED",
                    401: "ACCESS_DENIED",
                    403: "ACCESS_DENIED",
                    404: "NOT_FOUND",
                    407: "NETWORK_UNAVAILABLE",
                }.get(response.status, "METADATA_FAILED")
            )
        if response.getheader("Content-Encoding", "identity") != "identity":
            raise TrackingError("METADATA_FAILED")
        body_socket = request_socket if body_timeout is not None else connection.sock
        if body_timeout is not None:
            now = time.monotonic()
            if now >= deadline:
                raise TrackingError("NETWORK_UNAVAILABLE")
            deadline = now + body_timeout
        body = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TrackingError("NETWORK_UNAVAILABLE")
            if body_socket is not None and response.length != 0:
                body_socket.settimeout(min(_TIMEOUT, remaining))
            chunk = response.read1(min(16384, limit + 1 - len(body)))
            if not chunk:
                if response.length not in (None, 0):
                    raise TrackingError("NETWORK_UNAVAILABLE")
                return bytes(body)
            body.extend(chunk)
            if len(body) > limit:
                raise TrackingError("RESPONSE_TOO_LARGE")
    except (OSError, http.client.HTTPException):
        # CONNECT refusal/407 and final certificate/hostname failure are network errors.
        raise TrackingError("NETWORK_UNAVAILABLE") from None
    finally:
        if connection is not None:
            connection.close()


def channel_page(alias: str) -> bytes:
    from youtube_intel.providers.youtube_channel import CHANNEL_ID, channel_input

    value = channel_input(alias)
    path = "/channel/" + value if CHANNEL_ID.fullmatch(value) else "/" + value
    return _get(path, 4 * 1024 * 1024, body_timeout=_PAGE_BODY_TIMEOUT)


def channel_feed(channel_id: str) -> bytes:
    from youtube_intel.providers.youtube_channel import MAX_FEED, canonical_channel

    canonical_channel(channel_id)
    return _get("/feeds/videos.xml?channel_id=" + channel_id, MAX_FEED)
