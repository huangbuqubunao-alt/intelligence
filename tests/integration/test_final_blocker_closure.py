"""End-to-end integration tests closing final blockers (P1-F01, P1-F02, P1-F03, P2)."""

from __future__ import annotations

import email.message
import http.cookiejar
import io
import json
import sqlite3
import threading
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.client import HTTPConnection
from pathlib import Path
from typing import Any, cast

import pytest
from yt_dlp.utils import DownloadError  # type: ignore[import-untyped]

from tests.unit.test_manual_ux_remediation import (
    _build_runtime_env,
    _seed_video_source,
    _success_ydl_factory,
)
from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.fast_read_api import FastReadApiApplication
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.providers.youtube import YtDlpMetadataProvider
from youtube_intel.providers.youtube import _bind_test_hooks as bind_metadata_hooks
from youtube_intel.runtime import _production_dependencies
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub
from youtube_intel.youtube_auth_fallback import (
    CIRCUIT_BREAK_MINUTES,
    GLOBAL_COOKIE_SLOT,
    SINGLE_VIDEO_GRANT_MINUTES,
    CookieFilterError,
    ScopedMemoryCookieStore,
    YouTubeAuthFallbackService,
    _filter_cookiejar_domains,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_NOW = datetime(2026, 11, 26, 1, 0, tzinfo=UTC)

SYNTHETIC_COOKIE_A = (
    "# Netscape HTTP Cookie File\n"
    ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\tsynthetic-cookie-alpha\n"
)

SYNTHETIC_VTT = (
    "WEBVTT\n\n"
    "00:00:01.000 --> 00:00:06.000\n"
    "Single video grant recovered synthetic YouTube transcript cleanly.\n\n"
    "00:00:06.500 --> 00:00:12.000\n"
    "Atomic worker orchestration verified without enabling global fallback.\n"
)


class _FakeHttpResponse:
    def __init__(self, body: str, *, status: int = 200) -> None:
        self._buf = io.BytesIO(body.encode("utf-8"))
        self.status = status
        msg = email.message.Message()
        msg["Content-Type"] = "text/vtt; charset=utf-8"
        self.headers = msg

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def __enter__(self) -> _FakeHttpResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _MemorySecret:
    def __init__(self, initial: str | None = None) -> None:
        self.secret = initial

    def get(self) -> str | None:
        return self.secret

    def save(self, secret: str) -> None:
        self.secret = secret

    def delete(self) -> None:
        self.secret = None

    def __bool__(self) -> bool:
        return False


def _http_json(
    port: int,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json", "Host": f"127.0.0.1:{port}"}
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            headers["Origin"] = f"http://127.0.0.1:{port}"
            headers["Sec-Fetch-Site"] = "same-origin"
            headers["X-YIA-Request"] = "local-ui"
        if body is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        return resp.status, (json.loads(raw) if raw.strip() else {})
    finally:
        conn.close()


def _wait_until(predicate: Any, *, timeout: float = 10.0, diag: Any = None) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    extra = f" diag={diag()}" if callable(diag) else ""
    raise AssertionError(f"Timed out waiting for worker/source_run completion{extra}")


def _latest_run(repo: Any, source_id: str, command_id: str | None = None) -> Any:
    runs = [
        r
        for r in repo.list_source_runs()
        if r.source_id == source_id and (command_id is None or r.manual_command_id == command_id)
    ]
    if not runs:
        return None
    runs.sort(key=lambda r: (r.created_at, r.run_id), reverse=True)
    return runs[0]


def test_p1_f01_single_video_auth_real_http_to_worker_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise real loopback HTTP -> ProductOrchestration -> DurableSourceRunWorker -> YouTubeAuthFallbackService."""
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *_a: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *_a: {})
    monkeypatch.setattr("youtube_intel.providers.youtube._resolve_system_proxy_url", lambda: None)
    monkeypatch.setattr("youtube_intel.providers.subtitles._resolve_system_proxy_url", lambda: None)
    monkeypatch.setattr(
        "youtube_intel.youtube_auth_fallback._resolve_system_proxy_url", lambda: None
    )
    monkeypatch.setattr(
        "urllib.request.OpenerDirector.open",
        lambda _self, _req, timeout=None: _FakeHttpResponse(SYNTHETIC_VTT),
    )

    project_root = (tmp_path / "ws").resolve()
    for folder in ("data", "logs", "templates", "vault", "config"):
        (project_root / folder).mkdir(parents=True, exist_ok=True)
    values = load_settings(REPO_ROOT / "config" / "settings.example.yaml").model_dump()
    values["storage"]["vault_root"] = str(project_root / "vault")
    values["local_scoring"]["base_url"] = "http://127.0.0.1:19999"
    values["local_analysis"]["base_url"] = "http://127.0.0.1:19999"
    config = AppConfig(channels=(), settings=AppSettings.model_validate(values))

    clock = {"now": BASE_NOW}
    vid_a = "vidF01AlphA"
    vid_b = "vidF01BetaB"
    url_a = f"https://www.youtube.com/watch?v={vid_a}"
    url_b = f"https://www.youtube.com/watch?v={vid_b}"

    anon_calls: list[str] = []
    auth_calls: list[dict[str, Any]] = []
    auth_outcome = {"mode": "ok"}

    class _BlockedAnonYdl:
        def __enter__(self) -> _BlockedAnonYdl:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

        def extract_info(self, url: str, download: bool = False) -> object:
            del download
            anon_calls.append(url)
            raise DownloadError("Sign in to confirm you're not a bot")

    anon_meta = YtDlpMetadataProvider(timeout_seconds=5.0)
    bind_metadata_hooks(anon_meta, ydl_factory=lambda _opts: _BlockedAnonYdl())

    deps = replace(_production_dependencies(config), metadata_provider=anon_meta)

    def auth_ydl_factory(opts: dict[str, Any]) -> Any:
        auth_calls.append({"opts": dict(opts)})
        if auth_outcome["mode"] == "transient":

            class _TransientYdl:
                cookiejar = None

                def __enter__(self) -> _TransientYdl:
                    return self

                def __exit__(self, *_a: object) -> None:
                    return None

                def extract_info(self, url: str, download: bool = False) -> object:
                    del url, download
                    raise DownloadError("Temporary network timeout")

            return _TransientYdl()
        if auth_outcome["mode"] == "auth_rejected":

            class _RejectedYdl:
                cookiejar = None

                def __enter__(self) -> _RejectedYdl:
                    return self

                def __exit__(self, *_a: object) -> None:
                    return None

                def extract_info(self, url: str, download: bool = False) -> object:
                    del url, download
                    raise DownloadError("HTTP Error 401: Unauthorized Sign in required")

            return _RejectedYdl()

        class _OkYdl:
            cookiejar = None

            def __enter__(self) -> _OkYdl:
                return self

            def __exit__(self, *_a: object) -> None:
                return None

            def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
                del download
                vid = url.split("v=")[-1][:12]
                return {
                    "id": vid,
                    "title": f"Synthetic Recovered {vid}",
                    "channel_id": "UC" + "d" * 22,
                    "channel": "Synthetic Auth Channel",
                    "upload_date": "20261125",
                    "duration": 180,
                    "availability": "public",
                    "live_status": "not_live",
                    "webpage_url": url,
                    "subtitles": {
                        "en": [
                            {
                                "ext": "vtt",
                                "url": f"https://www.youtube.com/api/timedtext?v={vid}",
                            }
                        ]
                    },
                    "automatic_captions": {},
                }

        return _OkYdl()

    yt_auth = YouTubeAuthFallbackService(
        project_root=project_root,
        cookie_store=_MemorySecret(),
        ydl_factory=auth_ydl_factory,
        now=lambda: clock["now"],
    )

    composition = build_local_source_run_runtime(
        config=config,
        project_root=project_root,
        database=project_root / "state.sqlite3",
        dependencies=deps,
        credential_store=_MemorySecret(),
        bigmodel_credential_store=_MemorySecret(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        probe_local_runtime=False,
        now=lambda: clock["now"],
        youtube_auth_fallback=yt_auth,
    )
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=project_root / "data",
        project_root=project_root,
        byok_credential_store=_MemorySecret(),
        installed_ollama_probe=lambda _url: (False, ()),
        now=lambda: clock["now"],
    )
    hub.ensure_ready()
    fast_app = FastReadApiApplication(
        composition.application,
        workspace_hub=hub,
        youtube_auth_fallback=composition.youtube_auth_fallback,
    )

    server = serve_loopback(cast(LocalApiApplication, fast_app), port=0)
    port = int(server.server_port)
    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()
    composition.worker.start()

    try:
        # 1 & 2. Import video A via real HTTP API -> anonymous fails with YOUTUBE_AUTH_REQUIRED, 0 auth calls
        st_imp_a, body_imp_a = _http_json(
            port,
            "POST",
            "/api/v1/sources/import",
            {"url": url_a, "command_id": "imp-a-1"},
        )
        assert st_imp_a == HTTPStatus.ACCEPTED
        src_a = body_imp_a["source"]["source_id"]
        _wait_until(
            lambda: (sub := composition.repository.get_source_subscription(src_a)) is not None
            and sub.last_error_code == "YOUTUBE_AUTH_REQUIRED"
            and (run := _latest_run(composition.repository, src_a, "imp-a-1")) is not None
            and run.state.value == "NEEDS_ATTENTION"
        )
        assert len(anon_calls) >= 1
        assert len(auth_calls) == 0

        # 3. Create single-video grant for video A via real HTTP PUT (global enabled stays False!)
        st_put_a, body_put_a = _http_json(
            port,
            "PUT",
            "/api/v1/workspace-ai/youtube-auth",
            {
                "enabled": True,
                "grant_scope": "single_video",
                "target_video_id": vid_a,
                "auth_mode": "cookie_file",
                "cookies_txt": SYNTHETIC_COOKIE_A,
                "cooldown_seconds": 10,
            },
        )
        assert st_put_a == HTTPStatus.OK
        assert body_put_a["enabled"] is False
        assert body_put_a["scope"] == "single_video"
        assert body_put_a["active_single_video_grants"] == 1

        # 4, 5, 6, 7. Trigger real Source Check API -> real Worker enters auth fallback -> video A recovers
        clock["now"] = clock["now"] + timedelta(seconds=1)
        st_chk_a, _ = _http_json(
            port,
            "POST",
            f"/api/v1/sources/{src_a}/check",
            {"command_id": "chk-a-auth-1"},
        )
        assert st_chk_a == HTTPStatus.ACCEPTED
        _wait_until(
            lambda: composition.repository.get_verified_timed_transcript(video_id=vid_a) is not None
            and (run := _latest_run(composition.repository, src_a, "chk-a-auth-1")) is not None
            and run.state.value == "COMPLETED",
            diag=lambda: {
                "sub": composition.repository.get_source_subscription(src_a),
                "run": _latest_run(composition.repository, src_a, "chk-a-auth-1"),
                "job": composition.repository.latest_content_job(vid_a),
                "timed": composition.repository.get_verified_timed_transcript(video_id=vid_a) is not None,
                "auth_calls": len(auth_calls),
                "yt_status": yt_auth.get_status(),
            },
        )
        assert len(auth_calls) >= 1
        assert composition.repository.current_local_summary_pointer(vid_a) is not None
        # 8. Grant for A is consumed cleanly
        st_after_a, status_after_a = _http_json(port, "GET", "/api/v1/workspace-ai/youtube-auth")
        assert st_after_a == HTTPStatus.OK
        assert status_after_a["enabled"] is False
        assert status_after_a["active_single_video_grants"] == 0
        assert yt_auth.can_attempt(vid_a) == (False, "YOUTUBE_AUTH_DISABLED")

        # 9. Video B cannot inherit grant A (0 extra auth network calls)
        auth_calls_before_b = len(auth_calls)
        clock["now"] = clock["now"] + timedelta(seconds=12)
        st_imp_b, body_imp_b = _http_json(
            port,
            "POST",
            "/api/v1/sources/import",
            {"url": url_b, "command_id": "imp-b-1"},
        )
        assert st_imp_b == HTTPStatus.ACCEPTED
        src_b = body_imp_b["source"]["source_id"]
        _wait_until(
            lambda: (sub := composition.repository.get_source_subscription(src_b)) is not None
            and sub.last_error_code == "YOUTUBE_AUTH_REQUIRED"
            and (run := _latest_run(composition.repository, src_b, "imp-b-1")) is not None
            and run.state.value == "NEEDS_ATTENTION"
        )
        assert len(auth_calls) == auth_calls_before_b

        # 10. Second check on consumed grant (verify on video B after one consumed transient failure -> denied with 0 auth calls)
        auth_outcome["mode"] = "transient"
        _http_json(
            port,
            "PUT",
            "/api/v1/workspace-ai/youtube-auth",
            {
                "enabled": True,
                "grant_scope": "single_video",
                "target_video_id": vid_b,
                "auth_mode": "cookie_file",
                "cookies_txt": SYNTHETIC_COOKIE_A,
                "cooldown_seconds": 10,
            },
        )
        clock["now"] = clock["now"] + timedelta(seconds=1)
        _http_json(
            port,
            "POST",
            f"/api/v1/sources/{src_b}/check",
            {"command_id": "chk-b-consume-once"},
        )
        _wait_until(
            lambda: (run := _latest_run(composition.repository, src_b, "chk-b-consume-once")) is not None
            and run.state.value == "NEEDS_ATTENTION"
        )
        auth_calls_after_consume = len(auth_calls)
        assert auth_calls_after_consume == auth_calls_before_b + 1
        clock["now"] = clock["now"] + timedelta(seconds=12)
        auth_outcome["mode"] = "ok"
        st_chk_b2, _ = _http_json(
            port,
            "POST",
            f"/api/v1/sources/{src_b}/check",
            {"command_id": "chk-b-second-denied"},
        )
        assert st_chk_b2 == HTTPStatus.ACCEPTED
        _wait_until(
            lambda: (run := _latest_run(composition.repository, src_b, "chk-b-second-denied")) is not None
            and run.state.value == "NEEDS_ATTENTION"
        )
        assert len(auth_calls) == auth_calls_after_consume

        # 11a. Expired single-video grant on video B sends 0 auth network calls
        _http_json(
            port,
            "PUT",
            "/api/v1/workspace-ai/youtube-auth",
            {
                "enabled": True,
                "grant_scope": "single_video",
                "target_video_id": vid_b,
                "auth_mode": "cookie_file",
                "cookies_txt": SYNTHETIC_COOKIE_A,
            },
        )
        clock["now"] = clock["now"] + timedelta(minutes=SINGLE_VIDEO_GRANT_MINUTES + 1)
        _http_json(
            port,
            "POST",
            f"/api/v1/sources/{src_b}/check",
            {"command_id": "chk-b-expired"},
        )
        _wait_until(
            lambda: (run := _latest_run(composition.repository, src_b, "chk-b-expired")) is not None
            and run.state.value == "NEEDS_ATTENTION"
        )
        assert len(auth_calls) == auth_calls_after_consume

        # 11b. Revoked grant sends 0 auth network calls
        _http_json(
            port,
            "PUT",
            "/api/v1/workspace-ai/youtube-auth",
            {
                "enabled": True,
                "grant_scope": "single_video",
                "target_video_id": vid_b,
                "auth_mode": "cookie_file",
                "cookies_txt": SYNTHETIC_COOKIE_A,
            },
        )
        _http_json(port, "POST", "/api/v1/workspace-ai/youtube-auth/disconnect", {})
        clock["now"] = clock["now"] + timedelta(seconds=1)
        _http_json(
            port,
            "POST",
            f"/api/v1/sources/{src_b}/check",
            {"command_id": "chk-b-revoked"},
        )
        _wait_until(
            lambda: (run := _latest_run(composition.repository, src_b, "chk-b-revoked")) is not None
            and run.state.value == "NEEDS_ATTENTION"
        )
        assert len(auth_calls) == auth_calls_after_consume

        # 11c. Open circuit breaker sends 0 auth network calls even with a fresh grant
        clock["now"] = clock["now"] + timedelta(seconds=12)
        auth_outcome["mode"] = "auth_rejected"
        _http_json(
            port,
            "PUT",
            "/api/v1/workspace-ai/youtube-auth",
            {
                "enabled": True,
                "grant_scope": "single_video",
                "target_video_id": vid_b,
                "auth_mode": "cookie_file",
                "cookies_txt": SYNTHETIC_COOKIE_A,
            },
        )
        _http_json(
            port,
            "POST",
            f"/api/v1/sources/{src_b}/check",
            {"command_id": "chk-b-trip-circuit"},
        )
        _wait_until(
            lambda: bool(yt_auth.get_status()["circuit_open"])
            and (sub := composition.repository.get_source_subscription(src_b)) is not None
            and sub.last_error_code == "YOUTUBE_AUTH_EXPIRED"
            and (run := _latest_run(composition.repository, src_b, "chk-b-trip-circuit")) is not None
            and run.state.value == "NEEDS_ATTENTION"
        )
        auth_calls_after_trip = len(auth_calls)
        clock["now"] = clock["now"] + timedelta(seconds=1)
        _http_json(
            port,
            "PUT",
            "/api/v1/workspace-ai/youtube-auth",
            {
                "enabled": True,
                "grant_scope": "single_video",
                "target_video_id": vid_b,
                "auth_mode": "cookie_file",
                "cookies_txt": SYNTHETIC_COOKIE_A,
            },
        )
        _http_json(
            port,
            "POST",
            f"/api/v1/sources/{src_b}/check",
            {"command_id": "chk-b-blocked-circuit"},
        )
        _wait_until(
            lambda: (sub := composition.repository.get_source_subscription(src_b)) is not None
            and sub.last_error_code == "YOUTUBE_AUTH_RATE_LIMITED"
            and (run := _latest_run(composition.repository, src_b, "chk-b-blocked-circuit")) is not None
            and run.state.value == "NEEDS_ATTENTION"
        )
        assert len(auth_calls) == auth_calls_after_trip
        clock["now"] = clock["now"] + timedelta(minutes=CIRCUIT_BREAK_MINUTES + 1)
    finally:
        server.shutdown()
        server.server_close()
        composition.worker.stop()
        srv_thread.join(timeout=5)


def test_p1_f02_per_grant_credential_isolation_lifecycle_and_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify per-grant Keychain slot isolation, 3 revocation scopes, legacy migration, crash recovery & concurrency."""
    monkeypatch.setattr("youtube_intel.providers.youtube._resolve_system_proxy_url", lambda: None)
    monkeypatch.setattr("youtube_intel.providers.subtitles._resolve_system_proxy_url", lambda: None)
    monkeypatch.setattr("youtube_intel.youtube_auth_fallback._resolve_system_proxy_url", lambda: None)
    monkeypatch.setattr(
        "urllib.request.OpenerDirector.open",
        lambda _self, _req, timeout=None: _FakeHttpResponse(SYNTHETIC_VTT),
    )

    env = _build_runtime_env(tmp_path, monkeypatch)
    runtime = env["runtime"]
    clock = {"now": BASE_NOW}
    cookie_a = SYNTHETIC_COOKIE_A
    cookie_b = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\tsynthetic-cookie-beta\n"
    cookie_c = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\tsynthetic-cookie-gamma\n"
    cookie_global = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\tsynthetic-cookie-global\n"

    # Legacy table schema must migrate in-place safely without losing grants
    db_path = env["project_root"] / ".workspace-ai" / "hub.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE youtube_auth_video_grants (
                video_id TEXT PRIMARY KEY,
                auth_mode TEXT NOT NULL,
                browser_name TEXT NOT NULL DEFAULT '',
                expires_at TEXT NOT NULL,
                consumed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO youtube_auth_video_grants (video_id, auth_mode, browser_name, expires_at, consumed_at, created_at) "
            "VALUES ('legacyCons01', 'browser', 'chrome', '2026-11-26T02:00:00Z', '2026-11-26T01:05:00Z', '2026-11-26T01:00:00Z')"
        )
        conn.commit()

    store = ScopedMemoryCookieStore()
    seen_cookie_contents: list[tuple[str, str]] = []

    def tracking_ydl_factory(opts: dict[str, Any]) -> Any:
        cf = opts.get("cookiefile")
        body = Path(cf).read_text(encoding="utf-8") if cf else ""
        base = _success_ydl_factory("vidIsoA0001")(opts)

        class _Track:
            cookiejar = None

            def __enter__(self) -> _Track:
                return self

            def __exit__(self, *_a: object) -> None:
                return None

            def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
                seen_cookie_contents.append((url, body))
                return base.extract_info(url, download=download)

        return _Track()

    svc = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=store,
        ydl_factory=tracking_ydl_factory,
        now=lambda: clock["now"],
    )
    fast_app = FastReadApiApplication(
        env["raw_app"],
        workspace_hub=env["hub"],
        youtube_auth_fallback=svc,
    )

    # 1. Global cookie + A + B simultaneously in 3 distinct slots
    svc.update_config(
        {"enabled": True, "grant_scope": "global", "auth_mode": "cookie_file", "cookies_txt": cookie_global, "cooldown_seconds": 10}
    )
    st_a = svc.update_config(
        {"enabled": True, "grant_scope": "single_video", "target_video_id": "vidIsoA0001", "auth_mode": "cookie_file", "cookies_txt": cookie_a}
    )
    st_b = svc.update_config(
        {"enabled": True, "grant_scope": "single_video", "target_video_id": "vidIsoB0002", "auth_mode": "cookie_file", "cookies_txt": cookie_b}
    )
    assert st_a["video_grant"] is not None
    assert st_b["video_grant"] is not None
    assert len(store.slots) == 3
    assert "synthetic-cookie-global" in store.slots[GLOBAL_COOKIE_SLOT]

    # 2. Consume A -> ONLY A's grant slot cleaned; B and global preserved!
    _seed_video_source(env["repo"], source_id="src-iso-a", video_id="vidIsoA0001", now=clock["now"])
    _seed_video_source(env["repo"], source_id="src-iso-b", video_id="vidIsoB0002", now=clock["now"])
    _seed_video_source(env["repo"], source_id="src-iso-c", video_id="vidIsoC0003", now=clock["now"])
    assert svc.attempt_authenticated_ingest(runtime, "src-iso-a", "vidIsoA0001") is None
    assert any("vidIsoA0001" in u and "synthetic-cookie-alpha" in b for u, b in seen_cookie_contents)
    assert len(store.slots) == 2  # global + B only
    assert "synthetic-cookie-global" in store.slots[GLOBAL_COOKIE_SLOT]

    # 3. Revoke ONLY B via HTTP API -> B deleted, global intact
    c_rev_b, b_rev_b = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/youtube-auth/disconnect",
        json.dumps({"scope": "single_video", "target_video_id": "vidIsoB0002"}).encode("utf-8"),
    )
    assert c_rev_b == HTTPStatus.OK
    assert b_rev_b.get("video_grant") is None
    assert list(store.slots.keys()) == [GLOBAL_COOKIE_SLOT]

    # 4. Grant C, then disconnect ONLY global via HTTP API -> C stays active & global cleared!
    svc.update_config(
        {"enabled": True, "grant_scope": "single_video", "target_video_id": "vidIsoC0003", "auth_mode": "cookie_file", "cookies_txt": cookie_c}
    )
    c_dis_g, b_dis_g = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/youtube-auth/disconnect",
        json.dumps({"scope": "global"}).encode("utf-8"),
    )
    assert c_dis_g == HTTPStatus.OK
    assert b_dis_g["enabled"] is False
    assert b_dis_g["cookie_configured"] is False
    assert b_dis_g["active_single_video_grants"] == 1
    assert GLOBAL_COOKIE_SLOT not in store.slots
    assert len(store.slots) == 1

    # 5. Revoke all requires explicit confirm_all=true
    c_no_confirm, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/youtube-auth/disconnect",
        json.dumps({"scope": "all"}).encode("utf-8"),
    )
    assert c_no_confirm == HTTPStatus.UNPROCESSABLE_ENTITY
    assert len(store.slots) == 1

    c_rev_all, b_rev_all = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/youtube-auth/disconnect",
        json.dumps({"scope": "all", "confirm_all": True}).encode("utf-8"),
    )
    assert c_rev_all == HTTPStatus.OK
    assert b_rev_all["active_single_video_grants"] == 0
    assert store.slots == {}

    # 6. Expiry sweeps grant credential; IN_USE crash orphan cleans on restart; old task does not delete new grant
    clock["now"] = clock["now"] + timedelta(seconds=20)
    svc.update_config(
        {"enabled": True, "grant_scope": "single_video", "target_video_id": "vidIsoC0003", "auth_mode": "cookie_file", "cookies_txt": cookie_c}
    )
    clock["now"] = clock["now"] + timedelta(minutes=SINGLE_VIDEO_GRANT_MINUTES + 1)
    assert svc.get_status(video_id="vidIsoC0003")["active_single_video_grants"] == 0
    assert store.slots == {}

    # Simulated crash while IN_USE & old task finalizing after newer grant created for same video
    clock["now"] = clock["now"] + timedelta(seconds=20)
    st_old = svc.update_config(
        {"enabled": True, "grant_scope": "single_video", "target_video_id": "vidIsoA0001", "auth_mode": "cookie_file", "cookies_txt": cookie_a}
    )
    old_gid = st_old["video_grant"]["grant_id"]  # type: ignore[index]
    cfg_old, uid_old = svc._reserve_attempt_slot("vidIsoA0001")
    assert cfg_old is not None and cfg_old.grant_id == old_gid
    # While old is IN_USE, create a newer grant for vidIsoA0001
    svc.update_config(
        {"enabled": True, "grant_scope": "single_video", "target_video_id": "vidIsoA0001", "auth_mode": "cookie_file", "cookies_txt": cookie_b}
    )
    assert len(store.slots) == 2
    svc._finalize_attempt_slot(
        uid_old,
        video_id="vidIsoA0001",
        outcome="SUCCEEDED",
        grant_id=cfg_old.grant_id,
        credential_ref=cfg_old.credential_ref,
    )
    # Only old slot was deleted; newer grant for vidIsoA0001 stays active & intact!
    assert len(store.slots) == 1
    assert svc.get_status(video_id="vidIsoA0001")["video_grant"] is not None

    # Simulate crash on a grant stuck IN_USE and verify startup reconciliation sweeps it
    clock["now"] = clock["now"] + timedelta(seconds=20)
    cfg_crash, _ = svc._reserve_attempt_slot("vidIsoA0001")
    assert cfg_crash is not None
    assert cfg_crash.credential_ref in store.slots
    assert svc.reconcile_orphan_credentials(include_in_use=True) == 1
    assert store.slots == {}

    # Multi-instance race on the same single-video grant: strictly 1 winner
    clock["now"] = clock["now"] + timedelta(seconds=20)
    svc_peer = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=store,
        ydl_factory=tracking_ydl_factory,
        now=lambda: clock["now"],
    )
    svc.update_config(
        {"enabled": True, "grant_scope": "single_video", "target_video_id": "vidIsoB0002", "auth_mode": "cookie_file", "cookies_txt": cookie_b}
    )
    barrier = threading.Barrier(2)
    race_winners: list[str] = []
    race_lock = threading.Lock()

    def _race(instance: YouTubeAuthFallbackService) -> None:
        barrier.wait(timeout=3.0)
        cfg_r, uid_r = instance._reserve_attempt_slot("vidIsoB0002")
        with race_lock:
            race_winners.append("WIN:" + uid_r if cfg_r is not None else "DENY:" + uid_r)

    rt1 = threading.Thread(target=_race, args=(svc,))
    rt2 = threading.Thread(target=_race, args=(svc_peer,))
    rt1.start()
    rt2.start()
    rt1.join(timeout=3.0)
    rt2.join(timeout=3.0)
    assert sum(1 for r in race_winners if r.startswith("WIN:")) == 1
    assert svc.reconcile_orphan_credentials(include_in_use=True) == 1
    assert store.slots == {}

    # 7. Store failure safety: save failure leaves DB untouched; delete failure retains PENDING_DELETE until retried
    class _FailingStore(ScopedMemoryCookieStore):
        def __init__(self) -> None:
            super().__init__()
            self.fail_save = False
            self.fail_delete = False

        def save_slot(self, slot: str, secret: str) -> None:
            if self.fail_save:
                raise RuntimeError("keychain unavailable")
            super().save_slot(slot, secret)

        def delete_slot(self, slot: str) -> None:
            if self.fail_delete:
                raise RuntimeError("keychain busy")
            super().delete_slot(slot)

    fail_store = _FailingStore()
    fail_svc = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=fail_store,
        ydl_factory=tracking_ydl_factory,
        now=lambda: clock["now"],
    )
    clock["now"] = clock["now"] + timedelta(seconds=20)
    fail_store.fail_save = True
    with pytest.raises(ValueError, match="钥匙串"):
        fail_svc.update_config(
            {"enabled": True, "grant_scope": "single_video", "target_video_id": "vidIsoC0003", "auth_mode": "cookie_file", "cookies_txt": cookie_c}
        )
    assert fail_svc.get_status(video_id="vidIsoC0003")["active_single_video_grants"] == 0

    fail_store.fail_save = False
    fail_store.fail_delete = True
    fail_svc.update_config(
        {"enabled": True, "grant_scope": "single_video", "target_video_id": "vidIsoC0003", "auth_mode": "cookie_file", "cookies_txt": cookie_c}
    )
    fail_svc.revoke_video_grant("vidIsoC0003")
    with sqlite3.connect(fail_svc.db_path) as conn:
        pending_cnt = conn.execute(
            "SELECT COUNT(*) FROM youtube_auth_video_grants WHERE cleanup_state = 'PENDING_DELETE'"
        ).fetchone()[0]
    assert pending_cnt == 1
    fail_store.fail_delete = False
    assert fail_svc.reconcile_orphan_credentials(include_in_use=False) == 1
    assert fail_store.slots == {}


def test_p2_cookiejar_filter_fail_closed_zero_external_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify _filter_cookiejar_domains raises CookieFilterError on any failure and aborts with 0 network calls."""
    # 1. Helper Fail-Closed edge cases
    class _BrokenIterJar:
        def __iter__(self) -> Any:
            raise RuntimeError("iteration error")

    with pytest.raises(CookieFilterError, match="YOUTUBE_AUTH_COOKIE_FILTER_FAILED"):
        _filter_cookiejar_domains(_BrokenIterJar())

    class _RaiseClearJar(http.cookiejar.CookieJar):
        def clear(self, domain: str | None = None, path: str | None = None, name: str | None = None) -> None:
            del domain, path, name
            raise RuntimeError("cannot clear")

    bad_cookie = http.cookiejar.Cookie(
        version=0, name="SID", value="EVIL_SECRET", port=None, port_specified=False,
        domain=".evil.example", domain_specified=True, domain_initial_dot=True,
        path="/", path_specified=True, secure=True, expires=1893456000,
        discard=False, comment=None, comment_url=None, rest={},
    )
    jar_raise = _RaiseClearJar()
    jar_raise.set_cookie(bad_cookie)
    with pytest.raises(CookieFilterError):
        _filter_cookiejar_domains(jar_raise)

    # Malformed non-string domain
    class _MalformedCookie:
        domain = 12345
        name = "X"
        path = "/"

    class _StubbornJar:
        def __init__(self, items: list[Any]) -> None:
            self._items = items

        def __iter__(self) -> Any:
            return iter(self._items)

        def remove(self, _c: Any) -> None:
            # Silent no-op: caught by mandatory post-filter verification pass!
            return None

    with pytest.raises(CookieFilterError):
        _filter_cookiejar_domains(_StubbornJar([_MalformedCookie()]))
    with pytest.raises(CookieFilterError):
        _filter_cookiejar_domains(_StubbornJar([bad_cookie]))

    # 2. End-to-end: CookieFilterError aborts BEFORE extract_info or opener with 0 external calls & zero secret leaks
    env = _build_runtime_env(tmp_path, monkeypatch)
    runtime = env["runtime"]
    _seed_video_source(env["repo"], source_id="src-cj-1", video_id="vidCookieFail1")
    external_calls: list[str] = []

    def bad_jar_ydl_factory(_opts: dict[str, Any]) -> Any:
        class _Ydl:
            cookiejar = _StubbornJar([bad_cookie])

            def __enter__(self) -> _Ydl:
                return self

            def __exit__(self, *_a: object) -> None:
                return None

            def extract_info(self, url: str, download: bool = False) -> object:
                del download
                external_calls.append(url)
                return {}

        return _Ydl()

    svc = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=ScopedMemoryCookieStore(),
        ydl_factory=bad_jar_ydl_factory,
        now=lambda: BASE_NOW,
    )
    svc.update_config({"enabled": True, "auth_mode": "browser", "browser_name": "chrome"})
    err_code = svc.attempt_authenticated_ingest(runtime, "src-cj-1", "vidCookieFail1")
    assert err_code == "YOUTUBE_AUTH_COOKIE_FILTER_FAILED"
    assert external_calls == []
    assert "EVIL_SECRET" not in json.dumps(svc.get_status())
    assert svc.get_status()["circuit_open"] is False
