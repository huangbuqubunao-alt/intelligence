"""Bounded alias reads and local direct-route failures, with virtual time."""

import json
import socket
import time

import pytest
from conftest import _load_module

from youtube_intel.following_provider import TrackingError
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.providers import bilibili
from youtube_intel.providers import youtube_channel as yt
from youtube_intel.providers import youtube_network as net

CHANNEL = "UCLA_DiR1FfKNvjuUpBHmylQ"
OTHER = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
PAGE = f'<link rel="canonical" href="https://www.youtube.com/channel/{CHANNEL}">'.encode()


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return _load_module("test_youtube_network").certificates.__wrapped__(tmp_path_factory)


def test_real_tls_alias_body_progresses_beyond_ten_seconds(monkeypatch, certificates):
    network = _load_module("test_youtube_network")
    network.trust(monkeypatch, certificates)
    body = PAGE + b" " * (12 * 16384 - len(PAGE))
    with network.tunnel(certificates, body=body, chunk_delay=1) as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        start = time.monotonic()
        assert net.channel_page("@NASA") == body
        assert 10 < time.monotonic() - start < 25
        assert len(seen["requests"]) == 1


def test_real_tls_stalled_alias_read_terminates(monkeypatch, certificates):
    network = _load_module("test_youtube_network")
    network.trust(monkeypatch, certificates)
    monkeypatch.setattr(net, "_TIMEOUT", 0.25)
    with network.tunnel(certificates, body=PAGE, chunk_delay=0.6) as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        start = time.monotonic()
        with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
            net.channel_page("@NASA")
        assert 0.2 <= time.monotonic() - start < 1
        assert len(seen["requests"]) == 1  # failure occurred after headers.


class Clock:
    now = 0.0

    def monotonic(self):
        return self.now


class Response:
    status = 200

    def __init__(self, connection, body, delay, *, extra_length=0):
        self.connection = connection
        self.body = body
        self.delay = delay
        self.length = len(body) + extra_length
        self.reads = 0

    def getheader(self, name, default):
        return default

    def read1(self, size):
        self.reads += 1
        if self.delay > self.connection.timeout:
            self.connection.clock.now += self.connection.timeout
            raise TimeoutError()
        self.connection.clock.now += self.delay
        chunk, self.body = self.body[:size], self.body[size:]
        self.length -= len(chunk)
        return chunk


class Connection:
    def __init__(self, clock, body=PAGE, delay=0, *, header_delay=2, extra_length=0,
                 request_delay=0, detach=False):
        self.clock = clock
        self.sock = self
        self.timeout = 10
        self.header_delay = header_delay
        self.request_delay = request_delay
        self.detach = detach
        self.closed = False
        self.response = Response(self, body, delay, extra_length=extra_length)

    def settimeout(self, timeout):
        self.timeout = timeout

    def request(self, *args, **kwargs):
        self.clock.now += self.request_delay

    def getresponse(self):
        if self.header_delay > self.timeout:
            self.clock.now += self.timeout
            raise TimeoutError()
        self.clock.now += self.header_delay
        if self.detach:
            self.sock = None
        return self.response

    def close(self):
        self.closed = True


def transport(monkeypatch, **kwargs):
    clock = Clock()
    connection = Connection(clock, **kwargs)
    monkeypatch.setattr(net.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(net, "_connection", lambda: connection)
    return clock, connection


@pytest.mark.parametrize("alias", ["@NASA", CHANNEL])
def test_progressing_alias_body_can_finish_after_original_ten_seconds(monkeypatch, alias):
    body = PAGE + b" " * (128 * 1024)
    clock, connection = transport(monkeypatch, body=body, delay=3)
    assert net.channel_page(alias) == body
    assert 10 < clock.now < 45 + 10
    assert connection.closed


@pytest.mark.parametrize("route", ["page", "feed"])
def test_stalled_body_terminates_as_network_failure(monkeypatch, route):
    clock, connection = transport(monkeypatch, delay=11)
    request = (lambda: net.channel_page("@NASA")) if route == "page" else (lambda: net.channel_feed(CHANNEL))
    with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
        request()
    assert clock.now <= 12
    assert connection.closed


@pytest.mark.parametrize("detach", [False, True])
def test_progress_does_not_extend_alias_absolute_body_budget(monkeypatch, detach):
    clock, connection = transport(monkeypatch, body=b" " * (128 * 1024), delay=9, detach=detach)
    with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
        net.channel_page("@NASA")
    assert clock.now == 47  # two seconds of headers, then 45 seconds of body.
    assert connection.closed


def test_connection_close_body_gets_its_own_read_timeout(monkeypatch):
    body = PAGE + b" " * (64 * 1024)
    clock, connection = transport(monkeypatch, body=body, delay=3,
                                  request_delay=8, header_delay=1, detach=True)
    assert net.channel_page("@NASA") == body
    assert connection.sock is None and clock.now > 10
    assert connection.closed


def test_feed_retains_original_total_ten_second_budget(monkeypatch):
    clock, connection = transport(monkeypatch, body=b" " * (128 * 1024), delay=3)
    with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
        net.channel_feed(CHANNEL)
    assert clock.now == 10
    assert connection.closed


def test_alias_header_timeout_is_not_increased(monkeypatch):
    clock, connection = transport(monkeypatch, header_delay=11)
    with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
        net.channel_page("@NASA")
    assert clock.now == 10 and connection.response.reads == 0
    assert connection.closed


def test_alias_over_four_mib_rejects(monkeypatch):
    _, connection = transport(monkeypatch, body=b" " * (4 * 1024 * 1024 + 1))
    with pytest.raises(TrackingError, match="RESPONSE_TOO_LARGE"):
        net.channel_page("@NASA")
    assert connection.closed


def test_truncated_alias_cannot_return_partial_identity(monkeypatch):
    _, connection = transport(monkeypatch, extra_length=1)
    with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
        net.channel_page("@NASA")
    assert connection.closed


def product(tmp_path, monkeypatch):
    public_operation = yt.public_operation
    support = _load_module("test_phase12_live_feed")
    repo, tracker, fixture, runtime = support.live_shape_setup(tmp_path, monkeypatch)
    # Existing tracking fixtures bypass pacing; restore the real rate boundary.
    monkeypatch.setattr(yt, "public_operation", public_operation)
    monkeypatch.setattr(yt, "_NEXT", 0)
    monkeypatch.setattr(yt, "_RATE_UNTIL", 0)
    provider = tracker.providers["YOUTUBE"]
    provider._resolve = provider._resolve_public
    provider._fetch = yt._feed
    app = LocalApiApplication(
        repo, ProductOrchestrationService(repo, source_tracking=tracker),
        source_tracking=tracker, data_root=runtime._data_root,
    )
    return repo, tracker, app


def follow(app, alias):
    return app.handle("POST", "/api/v1/sources/channels", json.dumps({"input": alias}).encode())


def assert_empty(repo):
    assert repo.list_source_subscriptions() == ()
    assert repo.list_videos() == ()
    with repo._connect() as db:
        assert db.execute("SELECT count(*) FROM source_observations").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM source_checks").fetchone()[0] == 0


def test_failed_alias_body_writes_nothing_and_retry_baselines(tmp_path, monkeypatch):
    repo, tracker, app = product(tmp_path, monkeypatch)
    clock, stalled = transport(monkeypatch, delay=11)
    with pytest.raises(ApiError) as failure:
        follow(app, "@NASA")
    assert failure.value.code == "YOUTUBE_NETWORK_UNAVAILABLE"
    assert stalled.closed and yt._RATE_UNTIL == 0
    assert_empty(repo)
    clock.now += 1
    network = _load_module("test_youtube_network")
    connections = []

    def connect():
        body = PAGE + b" " * (128 * 1024) if not connections else network.FEED
        connection = Connection(clock, body=body, delay=3)
        connections.append(connection)
        return connection

    monkeypatch.setattr(net, "_connection", connect)
    status, result = follow(app, "@NASA")
    assert status == 200 and len(connections) == 2  # one alias, one feed; no blind retries.
    state = tracker.projection(result["source"]["source_id"])
    assert state["baseline_at"] and state["verified_at"]
    assert state["health"] == "HEALTHY" and state["coverage"] == "COMPLETE"
    assert len(repo.list_source_subscriptions()) == 1 and repo.list_videos() == ()
    assert all(c.closed for c in connections)


@pytest.mark.parametrize("addresses", [
    ["198.18.0.12"], ["127.0.0.1"], ["10.0.0.1"], ["::1"],
    ["8.8.8.8", "198.18.0.12"], [],
])
@pytest.mark.parametrize("route", ["page", "feed"])
def test_unusable_direct_dns_fails_closed_without_provider_cooldown(monkeypatch, addresses, route):
    monkeypatch.setattr(net, "_macos_proxy_url", lambda: None)
    monkeypatch.setattr(net.socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in addresses
    ])
    monkeypatch.setattr(net, "_PinnedHTTPS", lambda *a: pytest.fail("unsafe DNS reached socket"))
    monkeypatch.setattr(yt, "_NEXT", 0)
    monkeypatch.setattr(yt, "_RATE_UNTIL", 0)
    with pytest.raises(TrackingError) as failure:
        if route == "page":
            yt.YouTubeFollowingProvider().resolve("@NASA")
        else:
            yt.public_operation(lambda: net.channel_feed(CHANNEL))
    assert failure.value.code == "NETWORK_UNAVAILABLE"
    assert yt._RATE_UNTIL == 0
    if addresses:
        with pytest.raises(bilibili.BilibiliError, match="ACCESS_DENIED"):
            bilibili.public_addresses(net._HOST)  # shared validator remains strict.


def test_fake_ip_api_failure_then_system_route_recovers_both_channels(tmp_path, monkeypatch):
    repo, tracker, app = product(tmp_path, monkeypatch)
    network = _load_module("test_youtube_network")
    state = {"url": None}
    monkeypatch.setattr(net, "_macos_proxy_url", lambda: state["url"])
    monkeypatch.setattr(net.socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.12", 443))
    ])
    monkeypatch.setattr(net, "_PinnedHTTPS", lambda *a: pytest.fail("Fake-IP connected"))
    with pytest.raises(ApiError) as failure:
        follow(app, "@NASA")
    assert failure.value.code == "YOUTUBE_NETWORK_UNAVAILABLE"
    assert "198.18" not in str(failure.value)
    assert yt._RATE_UNTIL == 0
    assert_empty(repo)
    state["url"] = "http://127.0.0.1:9999"
    connects = []

    class SystemConnection(Connection):
        def __init__(self, host, port, *, timeout, context):
            assert (host, port) == ("127.0.0.1", 9999)
            assert context.check_hostname and context.verify_mode == net.ssl.CERT_REQUIRED
            super().__init__(Clock(), header_delay=0)
            connects.append(self)

        def set_tunnel(self, host, port):
            assert (host, port) == ("www.youtube.com", 443)

        def request(self, method, path, headers):
            channel = OTHER if "GoogleDevelopers" in path or OTHER in path else CHANNEL
            body = network.FEED.replace(CHANNEL[2:].encode(), channel[2:].encode()) if path.startswith("/feeds/") else PAGE.replace(CHANNEL.encode(), channel.encode())
            self.response = Response(self, body, 0)

    monkeypatch.setattr(net.http.client, "HTTPSConnection", SystemConnection)
    for alias, channel in [("@GoogleDevelopers", OTHER), ("@NASA", CHANNEL)]:
        status, result = follow(app, alias)
        assert status == 200 and result["source"]["channel_id"] == channel
        projection = tracker.projection(result["source"]["source_id"])
        assert projection["baseline_at"] and projection["verified_at"]
        assert projection["health"] == "HEALTHY" and projection["coverage"] == "COMPLETE"
    assert yt._RATE_UNTIL == 0 and len(connects) == 4
    assert len(repo.list_source_subscriptions()) == 2 and repo.list_videos() == ()


@pytest.mark.parametrize("status,code", [(401, "ACCESS_DENIED"), (403, "ACCESS_DENIED"), (429, "RATE_LIMITED")])
def test_real_provider_refusal_still_arms_global_cooldown(monkeypatch, status, code):
    clock, connection = transport(monkeypatch)
    connection.response.status = status
    monkeypatch.setattr(yt, "_NEXT", 0)
    monkeypatch.setattr(yt, "_RATE_UNTIL", 0)
    provider = yt.YouTubeFollowingProvider()
    with pytest.raises(TrackingError, match=code):
        provider.resolve("@NASA")
    assert yt._RATE_UNTIL == clock.now + 900
    monkeypatch.setattr(net, "_connection", lambda: pytest.fail("cooldown failed"))
    with pytest.raises(TrackingError, match="RATE_LIMITED"):
        provider.resolve("@GoogleDevelopers")
