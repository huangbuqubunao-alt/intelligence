"""Cookie-free public video adapter. No media, account, browser or ASR path.

Only fixed public metadata/player endpoints and explicit subtitle CDN paths are
reachable. HTTPS sockets pin validated public DNS addresses while retaining TLS
hostname verification. Redirects, proxies, cookies and compression are unused.
"""

from __future__ import annotations

import http.client
import ipaddress
import json
import math
import queue
import re
import socket
import ssl
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlsplit

from youtube_intel.source_transcript import MediaTranscript
from youtube_intel.state import TimedTranscriptCueWrite

if TYPE_CHECKING:
    from youtube_intel.providers.bilibili_creator import (
        CreatorIdentity,
        CreatorMetadata,
        CreatorPage,
    )

# Measured against the real provider, not guessed. Phase 11R sampled 8 public
# videos (`.var/phase11r/evidence/r2_response_sizes.json`):
#   /x/web-interface/view  2 084 .. 371 358 bytes
#   /x/player/v2          2 323 ..   4 199 bytes
# The previous 256 KiB bound rejected a genuine 371 358-byte response, so it was
# refusing real public videos. 512 KiB keeps the memory guard while giving 1.4x
# headroom over the largest response actually observed. Raising it further would
# be a guess with no evidence behind it.
MAX_METADATA = 512 * 1024
MAX_CAPTION = 2 * 1024 * 1024
MAX_CUES = 4096
TIMEOUT = 10.0
DNS_TIMEOUT = 3.0
MAX_ATTEMPTS = 3
# A resolver answer set is bounded so DNS cannot be used to exhaust memory, but
# the bound is a memory guard only: it is far above any real CDN fan-out and it
# is never used to decide whether a *target* is acceptable.  Every address that
# survives the bound is still validated as public and unicast.
MAX_RESOLVED_ADDRESSES = 512
# A provider that is risk-controlling or rate-limiting us must be left alone for
# long enough to stop.  Re-asking sooner does not make the next answer better
# and only deepens the refusal, so risk control backs off far longer than a
# plain access denial.
PROVIDER_BACKOFF_SECONDS = {
    "RISK_CONTROLLED": 15 * 60,
    "RATE_LIMITED": 15 * 60,
    "ACCESS_DENIED": 30,
}
_PROVIDER_BACKOFF_CODES = frozenset(PROVIDER_BACKOFF_SECONDS)
_BV = re.compile(r"BV1[1-9A-HJ-NP-Za-km-z]{9}\Z")
_REQUEST_SLOTS = threading.BoundedSemaphore(2)
_PACE_LOCK = threading.Lock()
_NEXT_REQUEST = 0.0
_RATE_UNTIL = 0.0
_DNS_SLOTS = threading.BoundedSemaphore(2)

# ---------------------------------------------------------------------------
# Phase 11R real-world capability decision (Bilibili creator Following).
#
# The only public endpoint that lists a creator's videos is
# ``/x/space/arc/search``.  A cookie-free client is risk-controlled by it:
#
#   * independent reconnaissance, 10 creators, one request each, 4 s apart:
#     4 x HTTP 412 ``-412 request was banned``, 6 x HTTP 200 ``-799 请求过于频繁``,
#     0 accepted;
#   * Phase 11R bounded fair single-shot probe, 3 creators, one provider
#     request each, 6 s apart: 3 x HTTP 412 ``-412 request was banned``,
#     0 accepted.
#
# ``/x/web-interface/card`` (the creator display name) and
# ``/x/web-interface/view`` (video metadata) are unaffected.  Recovering this
# path would require a request identity the product is explicitly forbidden to
# use, so continuous Bilibili creator tracking is withdrawn from normal pilot
# use instead of being advertised as ready.  Stored creator rows stay readable
# and are never deleted or rewritten.
# ---------------------------------------------------------------------------
CREATOR_FOLLOWING_AVAILABLE = False
CREATOR_FOLLOWING_CODE = "CREATOR_TRACKING_UNAVAILABLE"
CREATOR_FOLLOWING_ENDPOINT = "/x/space/arc/search"


class BilibiliError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class BilibiliIdentity:
    bvid: str

    @property
    def content_id(self) -> str:
        return "bilibili-" + self.bvid

    @property
    def canonical_url(self) -> str:
        return f"https://www.bilibili.com/video/{self.bvid}/"


def normalize_input(value: str) -> BilibiliIdentity:
    if not isinstance(value, str) or len(value) > 2048 or any(
        unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value
    ):
        raise BilibiliError("INVALID_INPUT")
    value = value.strip()
    if _BV.fullmatch(value):
        return BilibiliIdentity(value)
    try:
        url = urlsplit(value)
        if url.scheme != "https" or url.netloc.lower() not in {
            "www.bilibili.com", "bilibili.com", "m.bilibili.com"
        }:
            raise BilibiliError("UNSUPPORTED_URL")
        match = re.fullmatch(r"/video/(BV[^/]+)/?", url.path)
        if match is None or not _BV.fullmatch(match[1]):
            raise BilibiliError("INVALID_INPUT")
        query = parse_qs(url.query, keep_blank_values=True, max_num_fields=40)
        if query.get("p", ["1"]) != ["1"]:
            raise BilibiliError("UNSUPPORTED_URL")
        return BilibiliIdentity(match[1])
    except ValueError as error:
        if isinstance(error, BilibiliError):
            raise
        raise BilibiliError("INVALID_INPUT") from None


def validate_request_url(value: str) -> tuple[str, str]:
    try:
        if len(value) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in value):
            raise ValueError()
        url = urlsplit(value)
        host = url.netloc.lower()
        api = host == "api.bilibili.com" and url.path in {
            "/x/web-interface/view", "/x/player/v2", "/x/web-interface/card", "/x/space/arc/search"
        }
        caption = host in {"aisubtitle.hdslb.com", "i0.hdslb.com", "subtitle.bilibili.com"} and bool(
            re.fullmatch(r"/bfs/subtitle/[A-Za-z0-9_.-]+\.json", url.path)
        )
        if url.scheme != "https" or url.fragment or not (api or caption):
            raise ValueError()
        return host, url.path + ("?" + url.query if url.query else "")
    except ValueError:
        raise BilibiliError("UNSUPPORTED_URL") from None


def _usable_address(candidate: str) -> bool:
    """A candidate is connectable only when it is a public, unicast address."""
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return False
    return address.is_global and not (
        address.is_multicast or address.is_unspecified or address.is_loopback
    )


def public_addresses(host: str) -> tuple[str, ...]:
    """Return a bounded set of validated public addresses for an allowed host.

    The security invariant is that *every* address this function may hand to a
    socket is public and unicast.  A legitimate CDN host may answer with far
    more addresses than any fixed cap, so a count gate is not a safety property
    and previously failed all Bilibili traffic whenever ``api.bilibili.com``
    answered with more than sixteen addresses.  The answer set is instead
    bounded so resolver abuse stays impossible, and every candidate that is
    kept is validated; one unsafe answer rejects the whole set rather than being
    silently skipped, which preserves the DNS-rebinding protection.
    """
    if not _DNS_SLOTS.acquire(timeout=1):
        raise BilibiliError("NETWORK_UNAVAILABLE")
    result: queue.Queue[tuple[str, ...] | OSError] = queue.Queue(maxsize=1)
    def resolve() -> None:
        try:
            result.put(tuple(dict.fromkeys(str(r[4][0]) for r in socket.getaddrinfo(
                host, 443, type=socket.SOCK_STREAM))))
        except OSError as error:
            result.put(error)
        finally:
            _DNS_SLOTS.release()
    threading.Thread(target=resolve, daemon=True, name="bilibili-public-dns").start()
    try:
        addresses = result.get(timeout=DNS_TIMEOUT)
    except queue.Empty:
        raise BilibiliError("NETWORK_UNAVAILABLE") from None
    if isinstance(addresses, OSError):
        raise BilibiliError("NETWORK_UNAVAILABLE") from None
    if len(addresses) > MAX_RESOLVED_ADDRESSES or any(
        not _usable_address(candidate) for candidate in addresses
    ):
        raise BilibiliError("ACCESS_DENIED")
    return addresses


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str) -> None:
        self.tls_context = ssl.create_default_context()
        super().__init__(host, timeout=TIMEOUT, context=self.tls_context)
        self.address = address

    def connect(self) -> None:
        raw = socket.create_connection((self.address, 443), timeout=TIMEOUT)
        try:
            self.sock = self.tls_context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def _pace() -> None:
    global _NEXT_REQUEST
    with _PACE_LOCK:
        delay = max(0.0, _NEXT_REQUEST - time.monotonic())
        if delay:
            time.sleep(delay)
        _NEXT_REQUEST = time.monotonic() + 0.5


def _fetch_once(url: str, maximum: int) -> bytes:
    host, target = validate_request_url(url)
    addresses = public_addresses(host)
    connection = _PinnedHTTPS(host, addresses[0])
    deadline = time.monotonic() + TIMEOUT
    try:
        connection.request("GET", target, headers={
            "User-Agent": "YIA-PublicContent/1.0", "Accept": "application/json",
            "Accept-Encoding": "identity",
        })
        response = connection.getresponse()
        if 300 <= response.status < 400:
            # No redirect request is ever made, including to another allowed host.
            raise BilibiliError("UNSUPPORTED_URL")
        if response.status == 404:
            raise BilibiliError("NOT_FOUND")
        if response.status == 429:
            raise BilibiliError("RATE_LIMITED")
        if response.status == 412:
            # Bilibili answers a risk-controlled public request with HTTP 412 and
            # a body such as {"code":-412,"message":"request was banned"}.  It is
            # a statement about *this request*, never about whether the creator
            # or the video exists, so it must never be reported as ACCESS_DENIED.
            raise BilibiliError("RISK_CONTROLLED")
        if response.status in {401, 403}:
            raise BilibiliError("ACCESS_DENIED")
        if response.status >= 500:
            raise BilibiliError("NETWORK_UNAVAILABLE")
        if response.status != 200:
            raise BilibiliError("METADATA_FAILED")
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise BilibiliError("METADATA_FAILED")
        length = response.getheader("Content-Length")
        if length is not None and (not length.isdigit() or len(length) > 20 or int(length) > maximum):
            raise BilibiliError("RESPONSE_TOO_LARGE")
        chunks: list[bytes] = []
        size = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BilibiliError("NETWORK_UNAVAILABLE")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(16384, maximum + 1 - size))
            if not chunk:
                return b"".join(chunks)
            size += len(chunk)
            if size > maximum:
                raise BilibiliError("RESPONSE_TOO_LARGE")
            chunks.append(chunk)
    finally:
        connection.close()


def fetch_public(url: str, maximum: int, *, attempts: int = MAX_ATTEMPTS) -> bytes:
    global _RATE_UNTIL
    validate_request_url(url)
    if maximum not in {MAX_METADATA, MAX_CAPTION} or type(attempts) is not int or not 1 <= attempts <= MAX_ATTEMPTS:
        raise BilibiliError("INVALID_INPUT")
    with _PACE_LOCK:
        if time.monotonic() < _RATE_UNTIL:
            raise BilibiliError("RATE_LIMITED")
    if not _REQUEST_SLOTS.acquire(timeout=1):
        raise BilibiliError("RATE_LIMITED")
    try:
        for attempt in range(attempts):
            _pace()
            try:
                return _fetch_once(url, maximum)
            except (OSError, http.client.HTTPException):
                error = BilibiliError("NETWORK_UNAVAILABLE")
            except BilibiliError as failure:
                if failure.code in _PROVIDER_BACKOFF_CODES:
                    with _PACE_LOCK:
                        _RATE_UNTIL = time.monotonic() + PROVIDER_BACKOFF_SECONDS[
                            failure.code
                        ]
                if failure.code != "NETWORK_UNAVAILABLE":
                    raise
                error = failure
            if attempt == attempts - 1:
                raise error
            time.sleep(0.5 * 2 ** attempt)
        raise BilibiliError("NETWORK_UNAVAILABLE")
    finally:
        _REQUEST_SLOTS.release()


def _strict_json(payload: bytes, maximum: int, code: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    def invalid_constant(value: str) -> None:
        raise ValueError("nonfinite JSON")
    try:
        if not 0 < len(payload) <= maximum:
            raise ValueError()
        data = json.loads(payload.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=invalid_constant)
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (ValueError, UnicodeError, RecursionError):
        raise BilibiliError(code) from None


def _text(value: Any, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(
        unicodedata.category(c) in {"Cc", "Cf", "Cs"} and c not in "\n\t" for c in value
    ):
        raise ValueError("invalid text")
    return value


def _number(value: Any, minimum: float, maximum: float) -> float:
    if type(value) not in {int, float} or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError("invalid number")
    return float(value)


def parse_captions(payload: bytes, *, language: str, duration: float) -> MediaTranscript:
    data = _strict_json(payload, MAX_CAPTION, "CAPTION_INVALID")
    try:
        _text(language, 64)
        _number(duration, 0.001, 7200)
        body = data["body"]
        if not isinstance(body, list) or not 0 < len(body) <= MAX_CUES:
            raise ValueError()
        cues = []
        previous_end = 0
        for item in body:
            if not isinstance(item, dict):
                raise ValueError()
            start = _number(item["from"], 0, duration + 1)
            end = _number(item["to"], 0, duration + 1)
            start_ms, end_ms = round(start * 1000), round(end * 1000)
            if end < start or start_ms < previous_end or end_ms <= start_ms:
                raise ValueError()
            cues.append(TimedTranscriptCueWrite(start_ms=start_ms, end_ms=end_ms,
                text=_text(item["content"], 2000)))
            previous_end = end_ms
        if len("\n".join(c.text for c in cues).encode()) > MAX_CAPTION:
            raise ValueError()
        return MediaTranscript(cues=tuple(cues), language=language,
            provenance="bilibili-public-caption-v1", raw_output=payload)
    except (ValueError, KeyError, TypeError, OverflowError):
        raise BilibiliError("CAPTION_INVALID") from None


@dataclass(frozen=True)
class BilibiliMetadata:
    identity: BilibiliIdentity
    cid: int
    title: str
    uploader_id: str
    uploader_name: str
    published_at: datetime
    duration: float
    acquired_at: datetime


@dataclass(frozen=True)
class CaptionAcquisition:
    status: str
    transcript: MediaTranscript | None = None
    subtitle_id: str | None = None
    language_name: str | None = None
    source_url: str | None = None


def _api_data(payload: bytes) -> dict[str, Any]:
    data = _strict_json(payload, MAX_METADATA, "METADATA_FAILED")
    code = data.get("code")
    if type(code) is not int:
        raise BilibiliError("METADATA_FAILED")
    if code != 0:
        raise BilibiliError({-404: "NOT_FOUND", -403: "ACCESS_DENIED", -101: "ACCESS_DENIED",
            -111: "ACCESS_DENIED", -352: "RISK_CONTROLLED", -412: "RISK_CONTROLLED",
            -509: "RISK_CONTROLLED", -799: "RATE_LIMITED",
            # Bilibili uses 62xxx for a video the provider will not serve.  The
            # honest answer is "unavailable", never "could not be verified".
            62002: "VIDEO_UNAVAILABLE", 62004: "VIDEO_UNAVAILABLE",
            410002: "VIDEO_UNAVAILABLE"}.get(code, "METADATA_FAILED"))
    if not isinstance(data.get("data"), dict):
        raise BilibiliError("METADATA_FAILED")
    return dict(data["data"])


class BilibiliAdapter:
    provider = "BILIBILI"

    def __init__(self, *, fetch: Callable[[str, int], bytes] = fetch_public) -> None:
        self.fetch = fetch

    normalize_input = staticmethod(normalize_input)

    def _creator_request(self, url: str) -> bytes:
        # Creator checks retry through the durable application cooldown instead
        # of multiplying page retries. Direct video ingestion retains its budget.
        from youtube_intel.providers.bilibili_creator import _creator_data
        global _RATE_UNTIL
        payload = (fetch_public(url, MAX_METADATA, attempts=1)
                   if self.fetch is fetch_public else self.fetch(url, MAX_METADATA))
        try:
            _creator_data(payload)
        except BilibiliError as failure:
            # A refusal discovered while classifying the payload must cool down
            # the shared provider budget too, whichever transport answered it,
            # so one risk-controlled creator cannot keep being re-asked.
            backoff = PROVIDER_BACKOFF_SECONDS.get(failure.code)
            if backoff is not None:
                with _PACE_LOCK:
                    _RATE_UNTIL = max(_RATE_UNTIL, time.monotonic() + backoff)
            raise
        return payload

    def fetch_creator(self, identity: CreatorIdentity) -> CreatorMetadata:
        from youtube_intel.providers.bilibili_creator import parse_creator
        return parse_creator(self._creator_request(
            f"https://api.bilibili.com/x/web-interface/card?mid={identity.mid}"
        ), identity)

    def fetch_creator_page(self, identity: CreatorIdentity, page: int) -> CreatorPage:
        from youtube_intel.providers.bilibili_creator import (
            PAGE_SIZE,
            parse_creator_page,
        )
        if type(page) is not int or not 1 <= page <= 33334:
            raise BilibiliError("INVALID_INPUT")
        return parse_creator_page(self._creator_request(
            f"https://api.bilibili.com/x/space/arc/search?mid={identity.mid}&pn={page}&ps={PAGE_SIZE}&order=pubdate"
        ), identity, page)

    def fetch_metadata(self, identity: BilibiliIdentity) -> BilibiliMetadata:
        data = _api_data(self.fetch(
            f"https://api.bilibili.com/x/web-interface/view?bvid={identity.bvid}", MAX_METADATA))
        try:
            if data["bvid"] != identity.bvid:
                raise ValueError()
            rights = data["rights"]
            if not isinstance(rights, dict) or type(data["state"]) is not int or data["state"] != 0 or any(
                rights.get(key, 0) != 0 for key in ("pay", "ugc_pay", "arc_pay")
            ):
                raise BilibiliError("ACCESS_DENIED")
            cid = data["cid"]
            mid = data["owner"]["mid"]
            if type(cid) is not int or cid <= 0 or type(mid) is not int or mid <= 0:
                raise ValueError()
            duration = _number(data["duration"], 0.001, 86400 * 365)
            if duration > 7200:
                raise BilibiliError("DURATION_UNSUPPORTED")
            return BilibiliMetadata(identity, cid, _text(data["title"], 500), str(mid),
                _text(data["owner"]["name"], 200),
                datetime.fromtimestamp(_number(data["pubdate"], 0, time.time() + 86400), UTC),
                duration, datetime.now(UTC))
        except BilibiliError:
            raise
        except (ValueError, KeyError, TypeError, OverflowError):
            raise BilibiliError("METADATA_FAILED") from None

    def fetch_caption(self, metadata: BilibiliMetadata) -> CaptionAcquisition:
        try:
            data = _api_data(self.fetch(
                f"https://api.bilibili.com/x/player/v2?bvid={metadata.identity.bvid}&cid={metadata.cid}",
                MAX_METADATA))
            if data.get("bvid", metadata.identity.bvid) != metadata.identity.bvid or data.get("cid", metadata.cid) != metadata.cid:
                return CaptionAcquisition("CAPTION_INVALID")
            if data.get("need_login_subtitle") is True:
                return CaptionAcquisition("CAPTION_UNAVAILABLE")
            subtitle = data.get("subtitle", {})
            if not isinstance(subtitle, dict):
                raise BilibiliError("CAPTION_INVALID")
            subtitles = subtitle.get("subtitles", [])
            if not isinstance(subtitles, list) or len(subtitles) > 32:
                raise BilibiliError("CAPTION_INVALID")
            if not subtitles:
                return CaptionAcquisition("CAPTION_UNAVAILABLE")
            # Deterministic source order; output/UI language never influences authority.
            entry = subtitles[0]
            language = _text(entry["lan"], 64)
            language_name = _text(entry.get("lan_doc", language), 100)
            subtitle_id = str(entry["id"])
            if not re.fullmatch(r"[0-9]{1,30}", subtitle_id):
                raise ValueError()
            url = _text(entry["subtitle_url"], 4096)
            if url.startswith("//"):
                url = "https:" + url
            validate_request_url(url)
            if urlsplit(url).netloc.lower() == "api.bilibili.com":
                raise BilibiliError("CAPTION_INVALID")
            transcript = parse_captions(self.fetch(url, MAX_CAPTION), language=language, duration=metadata.duration)
            return CaptionAcquisition("READY", transcript, subtitle_id, language_name, url)
        except BilibiliError as error:
            return CaptionAcquisition("CAPTION_INVALID" if error.code in {
                "METADATA_FAILED", "RESPONSE_TOO_LARGE", "UNSUPPORTED_URL"
            } else error.code)
        except (ValueError, KeyError, TypeError, IndexError):
            return CaptionAcquisition("CAPTION_INVALID")
