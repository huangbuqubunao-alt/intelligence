"""OS authority and real CONNECT/TLS, with no external network or real VPN."""

import importlib
import select
import socket
import socketserver
import ssl
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from youtube_intel.following_provider import TrackingError
from youtube_intel.providers import youtube_network as net

CHANNEL = "UCLA_DiR1FfKNvjuUpBHmylQ"
FEED = (Path(__file__).parents[1] / "fixtures/youtube/rss_live_shape.xml").read_bytes()
PAGE = f'<link rel="canonical" href="https://www.youtube.com/channel/{CHANNEL}"><meta property="og:title" content="NASA"><meta itemprop="identifier" content="{CHANNEL}">'.encode()


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    root = tmp_path_factory.mktemp("youtube-tls")
    files = {}
    for name, host in [("valid", "www.youtube.com"), ("wrong", "attacker.example")]:
        config = root / (name + ".cnf")
        config.write_text(
            f"[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN={host}\n[ext]\nsubjectAltName=DNS:{host}\nbasicConstraints=critical,CA:TRUE\n"
        )
        cert, key = root / (name + ".crt"), root / (name + ".key")
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-config",
                str(config),
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ],
            check=True,
            capture_output=True,
        )
        files[name] = (cert, key)
    return files


@contextmanager
def tunnel(certificates, *, cert="valid", status=200, body=None, connect_status=200):
    seen = {"connect": [], "requests": [], "sni": []}
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(*map(str, certificates[cert]))
    context.set_servername_callback(lambda sock, host, ctx: seen["sni"].append(host))

    class Origin(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                with context.wrap_socket(self.request, server_side=True) as stream:
                    stream.settimeout(2)
                    request = b""
                    while b"\r\n\r\n" not in request:
                        request += stream.recv(4096)
                    seen["requests"].append(request.decode())
                    payload = (
                        body
                        if body is not None
                        else FEED
                        if b"/feeds/" in request
                        else PAGE
                    )
                    stream.sendall(
                        f"HTTP/1.1 {status} Test\r\nContent-Length: {len(payload)}\r\nLocation: https://attacker.example/\r\nConnection: close\r\n\r\n".encode()
                        + payload
                    )
            except (OSError, ssl.SSLError):
                pass  # Expected for certificate/hostname rejection.

    class Proxy(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(2)
            request = b""
            while b"\r\n\r\n" not in request:
                request += self.request.recv(4096)
            seen["connect"].append(request.decode())
            assert request.split(b"\r\n")[0] in (
                b"CONNECT www.youtube.com:443 HTTP/1.0",
                b"CONNECT www.youtube.com:443 HTTP/1.1",
            )
            self.request.sendall(f"HTTP/1.1 {connect_status} Test\r\n\r\n".encode())
            if connect_status != 200:
                return
            with socket.create_connection(origin.server_address, timeout=2) as upstream:
                sockets = [self.request, upstream]
                while True:
                    ready, _, _ = select.select(sockets, [], [], 2)
                    if not ready:
                        return
                    for source in ready:
                        data = source.recv(16384)
                        if not data:
                            return
                        (upstream if source is self.request else self.request).sendall(
                            data
                        )

    with (
        socketserver.ThreadingTCPServer(("127.0.0.1", 0), Origin) as origin,
        socketserver.ThreadingTCPServer(("127.0.0.1", 0), Proxy) as proxy,
    ):
        origin.daemon_threads = proxy.daemon_threads = True
        threads = [
            threading.Thread(target=s.serve_forever, daemon=True)
            for s in (origin, proxy)
        ]
        for thread in threads:
            thread.start()
        try:
            yield f"http://127.0.0.1:{proxy.server_address[1]}", seen
        finally:
            origin.shutdown()
            proxy.shutdown()
            for thread in threads:
                thread.join(timeout=3)
                assert not thread.is_alive()


def trust(monkeypatch, certificates, name="valid"):
    default = ssl.create_default_context

    def context():
        result = default(cafile=str(certificates[name][0]))
        assert result.check_hostname and result.verify_mode == ssl.CERT_REQUIRED
        return result

    monkeypatch.setattr(net.ssl, "create_default_context", context)


def test_system_proxy_connect_tls_without_destination_dns(monkeypatch, certificates):
    trust(monkeypatch, certificates)
    monkeypatch.setattr(
        net,
        "public_addresses",
        lambda _: pytest.fail("proxy must not resolve YouTube locally"),
    )
    with tunnel(certificates) as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        assert net.channel_feed(CHANNEL) == FEED
        assert seen["sni"] == ["www.youtube.com"]
        assert "Host: www.youtube.com" in seen["requests"][0]
        assert "Cookie:" not in seen["requests"][0]
        assert "Authorization:" not in seen["connect"][0]


@pytest.mark.parametrize("kind", ["hostname", "certificate"])
def test_final_tls_identity_failure(monkeypatch, certificates, kind):
    trust(monkeypatch, certificates, "wrong" if kind == "hostname" else "valid")
    with tunnel(certificates, cert="wrong") as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
            net.channel_feed(CHANNEL)
        assert not seen["requests"]


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_redirect_does_not_escape(monkeypatch, certificates, status):
    trust(monkeypatch, certificates)
    with tunnel(certificates, status=status) as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        with pytest.raises(TrackingError, match="METADATA_FAILED"):
            net.channel_feed(CHANNEL)
        assert len(seen["connect"]) == len(seen["requests"]) == 1


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://",
        "http://localhost",
        "http://localhost:0",
        "http://localhost:65536",
        "http://localhost:bad",
        "https://localhost:80",
        "socks5://localhost:80",
        "http://user:secret@localhost:80",
        "http://user@localhost:80",
        "http://localhost:80/path",
        "http://localhost:80?x=y",
        "http://localhost:80#x",
        "http://local host:80",
        "http://localhost:80\r\nX:secret",
    ],
)
def test_invalid_or_authenticated_configuration_fails_safely(monkeypatch, url):
    monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
    with pytest.raises(TrackingError) as failure:
        net.channel_feed(CHANNEL)
    assert str(failure.value) == "NETWORK_UNAVAILABLE"


def test_proxy_authentication_refusal_is_not_provider_denial(monkeypatch, certificates):
    with tunnel(certificates, connect_status=407) as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
            net.channel_feed(CHANNEL)
        assert not seen["requests"]


@pytest.mark.parametrize(
    "value",
    [
        "https://attacker.example/@NASA",
        "http://www.youtube.com/@NASA",
        "https://www.youtube.com:444/@NASA",
        "@NASA\r\nCONNECT attacker.example:443",
        "https://www.youtube.com@attacker.example/@NASA",
    ],
)
def test_content_cannot_choose_tunnel_destination(monkeypatch, value):
    monkeypatch.setattr(
        net, "_macos_proxy_url", lambda: pytest.fail("invalid input reached OS route")
    )
    with pytest.raises(TrackingError):
        net.channel_page(value)
    with pytest.raises(TrackingError):
        net.channel_feed(value)


def test_native_discovery_ignores_environment(monkeypatch):
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ):
        monkeypatch.setenv(key, "http://unexpected.example:9000")
    monkeypatch.setattr(net.sys, "platform", "darwin")

    class Native:
        def _get_proxies(self):
            return {}

    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: Native() if name == "_scproxy" else pytest.fail(name),
    )
    assert net._current_proxy() is None


def test_no_system_proxy_retains_validated_pinned_direct(monkeypatch):
    monkeypatch.setattr(net, "_macos_proxy_url", lambda: None)
    monkeypatch.setattr(
        net,
        "public_addresses",
        lambda host: ("8.8.8.8",) if host == "www.youtube.com" else pytest.fail(host),
    )

    class Direct:
        sock = None

        def __init__(self, host, address):
            assert (host, address) == ("www.youtube.com", "8.8.8.8")

        def request(self, method, path, headers):
            assert method == "GET" and path.startswith("/feeds/")

        def getresponse(self):
            return self

        status = 200

        def getheader(self, name, default):
            return default

        def read1(self, size):
            raw, self.raw = getattr(self, "raw", FEED), b""
            return raw

        def close(self):
            pass

    monkeypatch.setattr(net, "_PinnedHTTPS", Direct)
    assert net.channel_feed(CHANNEL) == FEED


def test_proxy_transitions_are_observed_without_restart(monkeypatch, certificates):
    trust(monkeypatch, certificates)
    state = {"url": None}
    monkeypatch.setattr(net, "_macos_proxy_url", lambda: state["url"])
    monkeypatch.setattr(
        net, "public_addresses", lambda _: (_ for _ in ()).throw(OSError("offline"))
    )
    with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
        net.channel_feed(CHANNEL)
    with tunnel(certificates) as (url, seen):
        state["url"] = url
        assert net.channel_page("@NASA") == PAGE
        assert net.channel_feed(CHANNEL) == FEED
        state["url"] = None
        with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
            net.channel_feed(CHANNEL)
        assert len(seen["connect"]) == 2


def test_response_bound(monkeypatch, certificates):
    trust(monkeypatch, certificates)
    with tunnel(certificates, body=b"x" * (256 * 1024 + 1)) as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        with pytest.raises(TrackingError, match="RESPONSE_TOO_LARGE"):
            net.channel_feed(CHANNEL)


def test_alias_and_feed_share_os_route_and_authority(
    monkeypatch, certificates, tmp_path
):
    from conftest import _load_module

    from youtube_intel.providers import youtube_channel

    support = _load_module("test_phase12_live_feed")
    repo, tracker, fixture, runtime = support.live_shape_setup(tmp_path, monkeypatch)
    provider = tracker.providers["YOUTUBE"]
    provider._resolve = provider._resolve_public
    provider._fetch = youtube_channel._feed
    state = {"url": None}
    monkeypatch.setattr(net, "_macos_proxy_url", lambda: state["url"])
    monkeypatch.setattr(
        net,
        "public_addresses",
        lambda _: (_ for _ in ()).throw(OSError("offline private detail")),
    )
    trust(monkeypatch, certificates)
    with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
        tracker.follow("@NASA", provider="YOUTUBE")
    assert repo.list_source_subscriptions() == ()
    assert repo.list_videos() == ()
    with tunnel(certificates) as (url, seen):
        state["url"] = url
        source = tracker.follow("@NASA", provider="YOUTUBE")
        projection = tracker.projection(source.source_id)
        assert projection["baseline_at"] and projection["verified_at"]
        assert projection["latest_published_at"] and projection["health"] == "HEALTHY"
        assert source.channel_id == CHANNEL and repo.list_videos() == ()
        assert [r.split(" ")[1] for r in seen["requests"]] == [
            "/@NASA",
            "/feeds/videos.xml?channel_id=" + CHANNEL,
        ]
        with repo._connect() as db:
            stored = str(
                [tuple(r) for r in db.execute("SELECT * FROM source_subscriptions")]
            )
            assert "127.0.0.1" not in stored and url not in stored
        fixture.tick()
        state["url"] = None
        assert tracker.check(source.source_id) == "OFFLINE"
        after = tracker.projection(source.source_id)
        for field in ("baseline_at", "verified_at", "latest_published_at"):
            assert after[field] == projection[field]
        assert not after["checking"] and repo.list_videos() == ()


def test_failed_feed_has_no_false_baseline_and_short_network_retry(
    monkeypatch, certificates, tmp_path
):
    from datetime import timedelta

    from conftest import _load_module

    from youtube_intel.providers import youtube_channel

    support = _load_module("test_phase12_live_feed")
    repo, tracker, fixture, runtime = support.live_shape_setup(tmp_path, monkeypatch)
    provider = tracker.providers["YOUTUBE"]
    provider._fetch = youtube_channel._feed
    monkeypatch.setattr(net, "_macos_proxy_url", lambda: None)
    monkeypatch.setattr(
        net, "public_addresses", lambda _: (_ for _ in ()).throw(OSError("offline"))
    )
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    before = tracker.projection(source.source_id)
    assert before["health"] == "OFFLINE" and not before["checking"]
    assert all(
        before[k] is None for k in ("baseline_at", "verified_at", "latest_published_at")
    )
    assert repo.get_source_subscription(source.source_id).last_success_at is None
    assert repo.list_videos() == ()
    assert support.observations(repo) == []
    assert tracker.check(source.source_id) == "COOLDOWN"
    with repo._connect() as db:
        assert (
            db.execute(
                "SELECT count(*) FROM source_checks WHERE status='RUNNING'"
            ).fetchone()[0]
            == 0
        )
    trust(monkeypatch, certificates)
    with tunnel(certificates) as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        fixture.now += timedelta(seconds=6)
        assert tracker.check(source.source_id) == "COMPLETE"
        after = tracker.projection(source.source_id)
        assert (
            after["baseline_at"]
            and after["verified_at"]
            and after["health"] == "HEALTHY"
        )
        assert repo.list_videos() == ()
        assert len(support.observations(repo)) == 1
        assert (
            tracker.check(source.source_id) == "COOLDOWN"
        )  # Success still has normal cooldown.
        from youtube_intel.following_tracking import FollowingTrackingService
        from youtube_intel.state import SQLiteStateRepository

        reopened = SQLiteStateRepository(repo._database_path)
        reopened.bind_source_storage(runtime._data_root)
        restarted = FollowingTrackingService(
            reopened, tracker.publisher, youtube=provider, now=lambda: fixture.now
        )
        assert restarted.projection(source.source_id) == after


@pytest.mark.parametrize(
    "page",
    [
        b"",
        b"\xff",
        b'<link rel="canonical" href="http://www.youtube.com/channel/'
        + CHANNEL.encode()
        + b'">',
        b'<link rel="canonical" href="https://attacker.example/channel/'
        + CHANNEL.encode()
        + b'">',
        PAGE + b'<meta itemprop="identifier" content="UCbbbbbbbbbbbbbbbbbbbbbb">',
        b'<meta itemprop="identifier" content="invalid">',
    ],
)
def test_alias_metadata_contract_rejects_spoofing(monkeypatch, page):
    from youtube_intel.providers import youtube_channel as provider_module

    monkeypatch.setattr(provider_module, "channel_page", lambda alias: page)
    with pytest.raises(TrackingError):
        provider_module.YouTubeFollowingProvider()._resolve_public("@NASA")


@pytest.mark.parametrize(
    "status,code",
    [
        (403, "ACCESS_DENIED"),
        (429, "RATE_LIMITED"),
        (500, "METADATA_FAILED"),
        (404, "NOT_FOUND"),
    ],
)
def test_provider_status_stays_distinct(monkeypatch, certificates, status, code):
    trust(monkeypatch, certificates)
    with tunnel(certificates, status=status) as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        with pytest.raises(TrackingError, match=code):
            net.channel_feed(CHANNEL)


def test_non_macos_route_does_not_inherit_env(monkeypatch):
    monkeypatch.setattr(net.sys, "platform", "linux")
    monkeypatch.setenv("HTTPS_PROXY", "http://unexpected.example:9000")
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: pytest.fail("must not import native bridge"),
    )
    assert net._current_proxy() is None


def test_following_resolution_has_no_yt_dlp_or_credential_side_effects(
    monkeypatch, certificates
):
    import yt_dlp

    from youtube_intel.providers.youtube_channel import YouTubeFollowingProvider

    monkeypatch.setattr(
        yt_dlp,
        "YoutubeDL",
        lambda *args, **kwargs: pytest.fail(
            "Following must not construct an unrestricted/cookie/config client"
        ),
    )
    trust(monkeypatch, certificates)
    with tunnel(certificates) as (url, seen):
        monkeypatch.setattr(net, "_macos_proxy_url", lambda: url)
        identity = YouTubeFollowingProvider()._resolve_public("@NASA")
        assert identity.channel_id == CHANNEL
        assert len(seen["requests"]) == 1
        assert (
            "Cookie:" not in seen["requests"][0]
            and "Authorization:" not in seen["requests"][0]
        )


def test_native_discovery_failure_is_truthful(monkeypatch):
    monkeypatch.setattr(net.sys, "platform", "darwin")
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda _: (_ for _ in ()).throw(OSError("private config")),
    )
    with pytest.raises(TrackingError) as failure:
        net.channel_feed(CHANNEL)
    assert str(failure.value) == "NETWORK_UNAVAILABLE"


def test_response_deadline_is_enforced_and_connection_closed(monkeypatch):
    import io

    clock = iter([0, 0, 11])
    monkeypatch.setattr(net.time, "monotonic", lambda: next(clock))

    class Connection:
        sock = None
        closed = False

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            response = io.BytesIO(FEED)
            response.status = 200
            response.getheader = lambda name, default: default
            return response

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(net, "_connection", lambda: connection)
    with pytest.raises(TrackingError, match="NETWORK_UNAVAILABLE"):
        net.channel_feed(CHANNEL)
    assert connection.closed
