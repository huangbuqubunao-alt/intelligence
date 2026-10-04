"""Public provider fixtures: no account, cookies, media or acoustic execution."""

import json
import socket
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock
from typing import Any

import pytest

from youtube_intel.providers import bilibili
from youtube_intel.providers.bilibili import (
    BilibiliAdapter,
    BilibiliError,
    normalize_input,
    parse_captions,
    validate_request_url,
)

BV = "BV1xx411c7mD"
METADATA = {"code": 0, "data": {"bvid": BV, "aid": 170001, "cid": 279786,
    "title": "Public example", "owner": {"mid": 1, "name": "Public uploader"},
    "pubdate": 1470000000, "duration": 60, "state": 0, "rights": {"pay": 0}}}
CAPTIONS = {"body": [{"from": 0.25, "to": 2.5, "content": "原始字幕。"},
    {"from": 3, "to": 5, "content": " Exact English text. "}]}


@pytest.mark.parametrize("value", [BV, f"https://www.bilibili.com/video/{BV}/?share=abc",
    f"https://m.bilibili.com/video/{BV}", f"https://bilibili.com/video/{BV}/?p=1#reply"])
def test_normalization(value: str) -> None:
    identity = normalize_input(value)
    assert identity.bvid == BV
    assert identity.content_id == "bilibili-" + BV
    assert identity.canonical_url == f"https://www.bilibili.com/video/{BV}/"


@pytest.mark.parametrize("value", ["BV123", "BV0xx411c7mD", "BV1xx411c7m0",
    "https://evil.test/video/" + BV, "https://localhost/video/" + BV,
    "https://127.0.0.1/video/" + BV, "file:///" + BV, "http://www.bilibili.com/video/" + BV,
    "https://www.bilibili.com@evil.test/video/" + BV,
    "https://www.bilibili.com:443/video/" + BV, "https://b23.tv/example",
    f"https://www.bilibili.com/video/{BV}/?p=2", "\x00" + BV])
def test_unsafe_input(value: str) -> None:
    with pytest.raises(BilibiliError):
        normalize_input(value)


@pytest.mark.parametrize("url", ["https://127.0.0.1/caption", "https://10.0.0.1/caption",
    "file:///tmp/caption", "https://evil.hdslb.com/bfs/subtitle/a.json",
    "https://aisubtitle.hdslb.com/other/a.json", "https://api.bilibili.com/anything",
    "https://api.bilibili.com:443/x/player/v2", "https://user@api.bilibili.com/x/player/v2"])
def test_request_allowlist(url: str) -> None:
    with pytest.raises(BilibiliError):
        validate_request_url(url)


def test_exact_timed_caption_language() -> None:
    result = parse_captions(json.dumps(CAPTIONS).encode(), language="ai-zh", duration=60)
    assert result.language == "ai-zh"
    assert result.cues[0].start_ms == 250
    assert result.cues[1].text == " Exact English text. "


@pytest.mark.parametrize("change", [
    lambda b: b["body"][0].update({"from": -1}),
    lambda b: b["body"][0].update({"from": float("nan")}),
    lambda b: b["body"][0].update({"to": float("inf")}),
    lambda b: b["body"][0].update({"to": 0}),
    lambda b: b["body"][0].update({"to": 62}),
    lambda b: b["body"][0].update({"content": " \t"}),
    lambda b: b["body"][0].update({"content": "bad\x00text"}),
    lambda b: b["body"][1].update({"from": 1}),
    lambda b: b.update({"body": []}),
    lambda b: b.update({"body": b["body"] * 5000}),
])
def test_invalid_caption(change: Callable[[dict[str, Any]], Any]) -> None:
    body = json.loads(json.dumps(CAPTIONS))
    change(body)
    with pytest.raises(BilibiliError, match="CAPTION_INVALID"):
        parse_captions(json.dumps(body).encode(), language="zh", duration=60)


def test_oversized_caption() -> None:
    with pytest.raises(BilibiliError, match="CAPTION_INVALID"):
        parse_captions(b"x" * (2 * 1024 * 1024 + 1), language="zh", duration=60)


def test_metadata_and_caption_success() -> None:
    requests = []
    def fetch(url: str, maximum: int) -> bytes:
        requests.append(url)
        if "/view?" in url:
            return json.dumps(METADATA).encode()
        if "/v2?" in url:
            return json.dumps({"code": 0, "data": {"subtitle": {"subtitles": [
                {"id": 1, "lan": "zh-CN", "lan_doc": "中文", "subtitle_url": "//aisubtitle.hdslb.com/bfs/subtitle/example.json"}
            ]}}}).encode()
        return json.dumps(CAPTIONS).encode()
    adapter = BilibiliAdapter(fetch=fetch)
    metadata = adapter.fetch_metadata(normalize_input(BV))
    acquired = adapter.fetch_caption(metadata)
    assert metadata.uploader_id == "1"
    assert acquired.transcript is not None and acquired.transcript.language == "zh-CN"
    assert acquired.status == "READY"
    assert len(requests) == 3
    assert all("cookie" not in r.lower() for r in requests)


def test_no_caption_is_honest() -> None:
    def fetch(url: str, maximum: int) -> bytes:
        return json.dumps(METADATA if "/view?" in url else {"code": 0,
            "data": {"need_login_subtitle": True, "subtitle": {"subtitles": []}}}).encode()
    adapter = BilibiliAdapter(fetch=fetch)
    result = adapter.fetch_caption(adapter.fetch_metadata(normalize_input(BV)))
    assert result.status == "CAPTION_UNAVAILABLE" and result.transcript is None


@pytest.mark.parametrize("payload,code", [(b"not json", "METADATA_FAILED"),
    (b"x" * (256 * 1024 + 1), "METADATA_FAILED"),
    (b'{"code":-404}', "NOT_FOUND"), (b'{"code":-403}', "ACCESS_DENIED"),
    (b'{"code":-799}', "RATE_LIMITED"), (b'{"code":0,"data":{}}', "METADATA_FAILED")])
def test_metadata_failure(payload: bytes, code: str) -> None:
    with pytest.raises(BilibiliError, match=code):
        BilibiliAdapter(fetch=lambda u, m: payload).fetch_metadata(normalize_input(BV))


def test_paid_resource_denied() -> None:
    data = json.loads(json.dumps(METADATA))
    data["data"]["rights"]["pay"] = 1
    with pytest.raises(BilibiliError, match="ACCESS_DENIED"):
        BilibiliAdapter(fetch=lambda u, m: json.dumps(data).encode()).fetch_metadata(normalize_input(BV))


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "::1", "fc00::1", "169.254.1.1", "224.0.0.1"])
def test_private_dns_is_denied(address: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", (address, 443))])
    with pytest.raises(BilibiliError, match="ACCESS_DENIED"):
        bilibili.public_addresses("api.bilibili.com")


def test_finite_retry_and_no_access_denial_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    delays = []
    monkeypatch.setattr(bilibili, "_RATE_UNTIL", 0.0)
    monkeypatch.setattr(bilibili, "_pace", lambda: None)
    monkeypatch.setattr(bilibili.time, "sleep", delays.append)
    def fail(url: str, maximum: int) -> bytes:
        calls.append(url)
        raise OSError("offline")
    monkeypatch.setattr(bilibili, "_fetch_once", fail)
    with pytest.raises(BilibiliError, match="NETWORK_UNAVAILABLE"):
        bilibili.fetch_public("https://api.bilibili.com/x/player/v2", bilibili.MAX_METADATA)
    assert len(calls) == 3 and delays == [0.5, 1.0]
    calls.clear()
    def denied(url: str, maximum: int) -> bytes:
        calls.append(url)
        raise BilibiliError("ACCESS_DENIED")
    monkeypatch.setattr(bilibili, "_fetch_once", denied)
    with pytest.raises(BilibiliError, match="ACCESS_DENIED"):
        bilibili.fetch_public("https://api.bilibili.com/x/player/v2", bilibili.MAX_METADATA)
    assert len(calls) == 1
    assert bilibili._RATE_UNTIL > bilibili.time.monotonic()


def test_concurrency_bound_across_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    active = 0
    peak = 0
    lock = Lock()
    entered = Barrier(3)
    release = Event()
    monkeypatch.setattr(bilibili, "_pace", lambda: None)
    def fetch(url: str, maximum: int) -> bytes:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        entered.wait(timeout=3)
        release.wait(timeout=3)
        with lock:
            active -= 1
        return b"{}"
    monkeypatch.setattr(bilibili, "_fetch_once", fetch)
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(bilibili.fetch_public, "https://api.bilibili.com/x/player/v2", bilibili.MAX_METADATA) for _ in range(2)]
        entered.wait(timeout=3)
        third = pool.submit(bilibili.fetch_public, "https://api.bilibili.com/x/player/v2", bilibili.MAX_METADATA)
        with pytest.raises(BilibiliError, match="RATE_LIMITED"):
            third.result(timeout=2)
        release.set()
        assert [job.result() for job in jobs] == [b"{}", b"{}"]
    assert peak == 2


@pytest.mark.parametrize("location", ["https://127.0.0.1/caption", "https://10.0.0.1/caption",
    "https://api.bilibili.com/x/player/v2", "https://evil.test/a"])
def test_redirect_chain_is_never_followed(location: str, monkeypatch: pytest.MonkeyPatch) -> None:
    requests = []
    class Response:
        status = 302
        def getheader(self, key: str, default: str = "") -> str:
            return location if key == "Location" else default
    class Connection:
        def __init__(self, host: str, address: str) -> None:
            assert address == "8.8.8.8"
        def request(self, method: str, target: str, headers: dict[str, str]) -> None:
            requests.append(target)
            assert "Cookie" not in headers and "Authorization" not in headers
        def getresponse(self) -> Response:
            return Response()
        def close(self) -> None:
            pass
    monkeypatch.setattr(bilibili, "public_addresses", lambda h: ("8.8.8.8",))
    monkeypatch.setattr(bilibili, "_PinnedHTTPS", Connection)
    with pytest.raises(BilibiliError, match="UNSUPPORTED_URL"):
        bilibili._fetch_once("https://api.bilibili.com/x/player/v2", bilibili.MAX_METADATA)
    assert requests == ["/x/player/v2"]  # Chain bound zero, even for allowed redirects.


def test_dns_timeout_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    release = Event()
    def stuck(*args: Any, **kwargs: Any) -> list[Any]:
        release.wait(timeout=1)
        return []
    monkeypatch.setattr(socket, "getaddrinfo", stuck)
    monkeypatch.setattr(bilibili, "DNS_TIMEOUT", 0.02)
    try:
        with pytest.raises(BilibiliError, match="NETWORK_UNAVAILABLE"):
            bilibili.public_addresses("api.bilibili.com")
    finally:
        release.set()


def test_rate_denial_applies_provider_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(bilibili, "_RATE_UNTIL", 0.0)
    monkeypatch.setattr(bilibili, "_pace", lambda: None)
    def limited(url: str, maximum: int) -> bytes:
        calls.append(url)
        raise BilibiliError("RATE_LIMITED")
    monkeypatch.setattr(bilibili, "_fetch_once", limited)
    for _ in range(2):
        with pytest.raises(BilibiliError, match="RATE_LIMITED"):
            bilibili.fetch_public("https://api.bilibili.com/x/player/v2", bilibili.MAX_METADATA)
    assert len(calls) == 1


@pytest.mark.parametrize('headers,payload,code', [
    ({'Content-Length': str(bilibili.MAX_METADATA + 1)}, b'{}', 'RESPONSE_TOO_LARGE'),
    ({'Content-Length': '9' * 5000}, b'{}', 'RESPONSE_TOO_LARGE'),
    ({'Content-Length': '-1'}, b'{}', 'RESPONSE_TOO_LARGE'),
    ({'Content-Encoding': 'gzip'}, b'compressed', 'METADATA_FAILED'),
    ({}, b'x' * (bilibili.MAX_METADATA + 1), 'RESPONSE_TOO_LARGE'),
])
def test_transport_bounds_body_and_rejects_compression(headers: dict[str, str], payload: bytes,
    code: str, monkeypatch: pytest.MonkeyPatch) -> None:
    consumed = 0
    closed = []
    class Response:
        status = 200
        def getheader(self, key: str, default: str | None = None) -> str | None:
            return headers.get(key, default)
        def read1(self, count: int) -> bytes:
            nonlocal consumed
            chunk = payload[consumed:consumed + count]
            consumed += len(chunk)
            return chunk
    class Connection:
        sock = None
        def __init__(self, host: str, address: str) -> None:
            pass
        def request(self, method: str, target: str, headers: dict[str, str]) -> None:
            assert set(headers) == {'User-Agent', 'Accept', 'Accept-Encoding'}
        def getresponse(self) -> Response:
            return Response()
        def close(self) -> None:
            closed.append(True)
    monkeypatch.setattr(bilibili, 'public_addresses', lambda h: ('8.8.8.8',))
    monkeypatch.setattr(bilibili, '_PinnedHTTPS', Connection)
    with pytest.raises(BilibiliError, match=code):
        bilibili._fetch_once('https://api.bilibili.com/x/player/v2', bilibili.MAX_METADATA)
    assert consumed <= bilibili.MAX_METADATA + 1 and closed == [True]
