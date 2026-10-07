"""Automatic OS routing for the fixed public YouTube Following destination.

This module deliberately offers no URL/host/proxy input to content callers.
"""

from __future__ import annotations

import http.client
import importlib
import ipaddress
import re
import ssl
import sys
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from youtube_intel.following_provider import TrackingError
from youtube_intel.providers.bilibili import _PinnedHTTPS, public_addresses

_HOST = "www.youtube.com"
_TIMEOUT = 10.0


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


def _connection() -> http.client.HTTPSConnection:
    proxy = _current_proxy()
    if proxy is None:
        return _PinnedHTTPS(_HOST, public_addresses(_HOST)[0])
    connection = http.client.HTTPSConnection(
        proxy.host, proxy.port, timeout=_TIMEOUT, context=ssl.create_default_context()
    )
    # HTTPSConnection verifies _tunnel_host, not proxy.host; no local YouTube DNS.
    connection.set_tunnel(_HOST, 443)
    return connection


def _get(path: str, limit: int) -> bytes:
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
        body = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TrackingError("NETWORK_UNAVAILABLE")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(16384, limit + 1 - len(body)))
            if not chunk:
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
    return _get(path, 4 * 1024 * 1024)


def channel_feed(channel_id: str) -> bytes:
    from youtube_intel.providers.youtube_channel import MAX_FEED, canonical_channel

    canonical_channel(channel_id)
    return _get("/feeds/videos.xml?channel_id=" + channel_id, MAX_FEED)
