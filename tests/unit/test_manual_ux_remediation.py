"""Regression tests covering manual UX remediation items #1-#4 (YouTube anonymous/Option B auth, network errors, curated downloads, cloud BYOK)."""

from __future__ import annotations

import email.message
import io
import json
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest
from yt_dlp.utils import DownloadError

from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.discovery import AdapterError
from youtube_intel.domain import AppError, ErrorCode
from youtube_intel.fast_read_api import FastReadApiApplication
from youtube_intel.orchestration import ProcessingPolicy, SourceType
from youtube_intel.processing_orchestrator import SourceRunDiscoveryError
from youtube_intel.providers.subtitles import (
    _SAFE_YDL_OPTS as SUBTITLE_SAFE_YDL_OPTS,
)
from youtube_intel.providers.subtitles import (
    YtDlpSubtitleAdapter,
)
from youtube_intel.providers.subtitles import (
    _bind_test_hooks as bind_subtitle_hooks,
)
from youtube_intel.providers.youtube import (
    _SAFE_YDL_OPTS as METADATA_SAFE_YDL_OPTS,
)
from youtube_intel.providers.youtube import (
    YtDlpMetadataProvider,
    _build_ydl_opts,
)
from youtube_intel.providers.youtube import (
    _bind_test_hooks as bind_metadata_hooks,
)
from youtube_intel.runtime import RuntimeOperations
from youtube_intel.runtime_composition import (
    RuntimeSourceRunIngestion,
    build_local_source_run_runtime,
)
from youtube_intel.state import SourceSubscriptionRecord
from youtube_intel.transcripts import TranscriptError
from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub
from youtube_intel.youtube_auth_fallback import (
    CIRCUIT_BREAK_MINUTES,
    YouTubeAuthFallbackService,
    validate_netscape_cookies_txt,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
VALID_VTT = b"WEBVTT\n\n00:00:00.000 --> 00:00:04.000\nLocal test subtitle cue.\n"
VALID_COOKIES = (
    "# Netscape HTTP Cookie File\n"
    ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\tdummy_secret_cookie_val\n"
    ".google.com\tTRUE\t/\tTRUE\t1893456000\tSID\tdummy_google_sid\n"
)


class _MemorySecret:
    def __init__(self, initial: str | None = None) -> None:
        self.secret = initial

    def get(self) -> str | None:
        return self.secret

    def load(self) -> str | None:
        return self.secret

    def save(self, value: str) -> None:
        self.secret = value

    def delete(self) -> None:
        self.secret = None


class _FakeHttpResponse:
    def __init__(self, payload: bytes, *, status: int = 200) -> None:
        self._buf = io.BytesIO(payload)
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


def _build_runtime_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    ollama_pull_runner: Any = None,
    whisper_download_runner: Any = None,
    cloud_test_runner: Any = None,
) -> dict[str, Any]:
    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_models", lambda *_a: {"models": []}
    )
    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_runtime_version", lambda *_a: {}
    )
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe",
        lambda *_a: "MODEL_UNAVAILABLE",
    )

    project_root = tmp_path.resolve() / "workspace"
    for folder in ("data", "logs", "templates", "vault"):
        (project_root / folder).mkdir(parents=True, exist_ok=True)
    values = load_settings(REPO_ROOT / "config" / "settings.example.yaml").model_dump()
    values["storage"]["vault_root"] = str(project_root / "vault")
    config = AppConfig(channels=(), settings=AppSettings.model_validate(values))
    db_path = project_root / "state.sqlite3"
    byok_store = _MemorySecret()

    composition = build_local_source_run_runtime(
        config=config,
        project_root=project_root,
        database=db_path,
        credential_store=_MemorySecret(),
        bigmodel_credential_store=_MemorySecret(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        probe_local_runtime=False,
        now=lambda: BASE_NOW,
    )
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=project_root / "data",
        project_root=project_root,
        byok_credential_store=byok_store,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        ollama_pull_runner=ollama_pull_runner,
        whisper_download_runner=whisper_download_runner,
        cloud_test_runner=cloud_test_runner,
        now=lambda: BASE_NOW,
    )
    hub.ensure_ready()
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)
    fast_app._youtube_auth._cookie_store = _MemorySecret()
    return {
        "project_root": project_root,
        "data_root": project_root / "data",
        "config": config,
        "repo": composition.repository,
        "runtime": composition.runtime,
        "source_policy": composition.source_policy,
        "raw_app": composition.application,
        "hub": hub,
        "fast_app": fast_app,
        "byok_store": byok_store,
    }


def _seed_video_source(
    repo: Any,
    *,
    source_id: str,
    video_id: str,
    now: datetime = BASE_NOW,
    policy: ProcessingPolicy = ProcessingPolicy.DISCOVER_ONLY,
) -> None:
    repo.create_source_subscription(
        SourceSubscriptionRecord(
            source_id=source_id,
            source_type=SourceType.VIDEO_URL,
            canonical_url=f"https://www.youtube.com/watch?v={video_id}",
            channel_id=None,
            video_id=video_id,
            display_name=f"Video {video_id}",
            enabled=True,
            processing_policy=policy,
            last_checked_at=None,
            last_success_at=None,
            last_error_code=None,
            last_error_message=None,
            created_at=now,
            updated_at=now,
            provider="YOUTUBE",
        )
    )


def _success_ydl_factory(video_id: str) -> Any:
    def factory(_opts: dict[str, Any]) -> Any:
        class _FakeYdl:
            cookiejar = None

            def __enter__(self) -> _FakeYdl:
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
                del download
                resolved_id = (
                    url.split("v=")[-1].split("&")[0] if "v=" in url else video_id
                )
                return {
                    "id": resolved_id,
                    "title": f"Test Title {resolved_id}",
                    "description": "Concise anonymous single-video fetch",
                    "channel_id": "UC_TEST_0000000000000001",
                    "channel": "Anonymous Channel",
                    "timestamp": int(BASE_NOW.timestamp()),
                    "duration": 240,
                    "language": "en",
                    "live_status": "not_live",
                    "availability": "public",
                    "subtitles": {
                        "en": [
                            {
                                "ext": "vtt",
                                "url": "https://www.youtube.com/api/timedtext?v=" + resolved_id,
                            }
                        ]
                    },
                    "automatic_captions": {},
                }

        return _FakeYdl()

    return factory


# ---------------------------------------------------------------------------
# Issue #3 & #4 — Anonymous yt-dlp safety options, proxy forwarding, error split
# ---------------------------------------------------------------------------


def test_youtube_and_subtitle_safe_opts_ignore_no_formats_and_inject_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert METADATA_SAFE_YDL_OPTS["ignore_no_formats_error"] is True
    assert SUBTITLE_SAFE_YDL_OPTS["ignore_no_formats_error"] is True

    monkeypatch.setattr(
        "youtube_intel.providers.youtube._resolve_system_proxy_url",
        lambda: "http://127.0.0.1:7890",
    )
    built = _build_ydl_opts(socket_timeout=10.0)
    assert built["proxy"] == "http://127.0.0.1:7890"
    assert built["ignore_no_formats_error"] is True
    for forbidden in ("cookiefile", "cookiesfrombrowser", "format"):
        assert forbidden not in built


def test_youtube_and_subtitle_providers_distinguish_auth_gate_vs_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "youtube_intel.providers.youtube._resolve_system_proxy_url", lambda: None
    )
    monkeypatch.setattr(
        "youtube_intel.providers.subtitles._resolve_system_proxy_url", lambda: None
    )

    class _BotGateYdl:
        def __enter__(self) -> _BotGateYdl:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

        def extract_info(self, url: str, download: bool = False) -> object:
            del url, download
            raise DownloadError(
                "ERROR: [youtube] Y5MuBWwN8IA: Sign in to confirm you're not a bot. Use --cookies-from-browser"
            )

    class _NoVpnNetworkYdl:
        def __enter__(self) -> _NoVpnNetworkYdl:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

        def extract_info(self, url: str, download: bool = False) -> object:
            del url, download
            raise DownloadError(
                "ERROR: Unable to download webpage: http://127.0.0.1:7890 <urlopen error [Errno 61] Connection refused> (caused by URLError)"
            )

    meta_auth = YtDlpMetadataProvider(timeout_seconds=5.0)
    bind_metadata_hooks(meta_auth, ydl_factory=lambda _opts: _BotGateYdl())
    with pytest.raises(AdapterError) as auth_err:
        meta_auth.fetch("Y5MuBWwN8IA")
    assert auth_err.value.error.code is ErrorCode.PERMISSION_DENIED

    meta_net = YtDlpMetadataProvider(timeout_seconds=5.0)
    bind_metadata_hooks(meta_net, ydl_factory=lambda _opts: _NoVpnNetworkYdl())
    with pytest.raises(AdapterError) as net_err:
        meta_net.fetch("Y5MuBWwN8IA")
    assert net_err.value.error.code is ErrorCode.TRANSIENT_NETWORK

    sub_auth = YtDlpSubtitleAdapter(timeout_seconds=5.0)
    bind_subtitle_hooks(sub_auth, ydl_factory=lambda _opts: _BotGateYdl())
    with pytest.raises(TranscriptError) as sub_auth_err:
        sub_auth.enumerate_tracks("Y5MuBWwN8IA")
    assert sub_auth_err.value.error.code is ErrorCode.PERMISSION_DENIED

    sub_net = YtDlpSubtitleAdapter(timeout_seconds=5.0)
    bind_subtitle_hooks(sub_net, ydl_factory=lambda _opts: _NoVpnNetworkYdl())
    with pytest.raises(TranscriptError) as sub_net_err:
        sub_net.enumerate_tracks("Y5MuBWwN8IA")
    assert sub_net_err.value.error.code is ErrorCode.TRANSIENT_NETWORK
    assert "http" not in sub_net_err.value.error.message.lower()


# ---------------------------------------------------------------------------
# Issue #3 Option B — YouTubeAuthFallbackService storage, guardrails, execution
# ---------------------------------------------------------------------------


def test_youtube_auth_fallback_storage_isolation_and_validation(tmp_path: Path) -> None:
    secret_store = _MemorySecret()
    service = YouTubeAuthFallbackService(
        project_root=tmp_path,
        cookie_store=secret_store,
        now=lambda: BASE_NOW,
    )
    # Must NOT eagerly create hub.sqlite3 on initial status/read calls.
    initial = service.get_status()
    assert initial["enabled"] is False
    assert initial["auth_mode"] == "disabled"
    assert initial["cookie_configured"] is False
    assert initial["daily_limit"] == 20
    assert initial["cooldown_seconds"] == 15
    assert not service.db_path.exists()
    assert service.can_attempt("vidA0000001") == (False, "YOUTUBE_AUTH_DISABLED")

    with pytest.raises(ValueError, match="Netscape"):
        validate_netscape_cookies_txt("just random text")
    with pytest.raises(ValueError, match="youtube.com"):
        validate_netscape_cookies_txt(
            ".example.com\tTRUE\t/\tTRUE\t1893456000\tTOKEN\tabc\n"
        )

    updated = service.update_config(
        {
            "enabled": True,
            "auth_mode": "cookie_file",
            "cookies_txt": VALID_COOKIES,
            "daily_limit": 12,
            "cooldown_seconds": 15,
        }
    )
    assert updated["enabled"] is True
    assert updated["auth_mode"] == "cookie_file"
    assert updated["cookie_configured"] is True
    assert "dummy_secret_cookie_val" not in json.dumps(updated)
    assert secret_store.get() is not None and "dummy_secret_cookie_val" in secret_store.get()

    # Verify SQLite has ZERO cookie secret stored.
    with sqlite3.connect(service.db_path) as conn:
        dump = "\n".join(conn.iterdump())
    assert "dummy_secret_cookie_val" not in dump

    disconnected = service.disconnect()
    assert disconnected["enabled"] is False
    assert disconnected["auth_mode"] == "disabled"
    assert disconnected["cookie_configured"] is False
    assert secret_store.get() is None


def test_youtube_auth_fallback_execution_temp_cleanup_and_rate_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_runtime_env(tmp_path, monkeypatch)
    runtime: RuntimeOperations = env["runtime"]
    secret_store = _MemorySecret()
    clock = {"now": BASE_NOW}
    seen_opts: list[dict[str, Any]] = []
    seen_cookie_paths: list[Path] = []
    outcome_mode = {"kind": "ok"}

    monkeypatch.setattr(
        "youtube_intel.providers.youtube._resolve_system_proxy_url", lambda: None
    )
    monkeypatch.setattr(
        "youtube_intel.providers.subtitles._resolve_system_proxy_url", lambda: None
    )
    monkeypatch.setattr(
        "urllib.request.OpenerDirector.open",
        lambda _self, _req, timeout=None: _FakeHttpResponse(VALID_VTT),
    )

    def ydl_factory(opts: dict[str, Any]) -> Any:
        seen_opts.append(dict(opts))
        if "cookiefile" in opts:
            p = Path(opts["cookiefile"])
            seen_cookie_paths.append(p)
            assert p.is_file()
        if outcome_mode["kind"] == "auth_rejected":
            class _ErrYdl:
                cookiejar = None
                def __enter__(self) -> _ErrYdl:
                    return self
                def __exit__(self, *_a: object) -> None:
                    return None
                def extract_info(self, url: str, download: bool = False) -> object:
                    del url, download
                    raise DownloadError("HTTP Error 401: Unauthorized Sign in required")
            return _ErrYdl()
        return _success_ydl_factory("Y5MuBWwN8IA")(opts)

    service = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=secret_store,
        ydl_factory=ydl_factory,
        now=lambda: clock["now"],
    )
    service.update_config(
        {
            "enabled": True,
            "auth_mode": "cookie_file",
            "cookies_txt": VALID_COOKIES,
            "daily_limit": 2,
            "cooldown_seconds": 15,
        }
    )

    _seed_video_source(env["repo"], source_id="src-auth-1", video_id="Y5MuBWwN8IA")
    res1 = service.attempt_authenticated_ingest(runtime, "src-auth-1", "Y5MuBWwN8IA")
    assert res1 is None
    assert any("cookiefile" in o for o in seen_opts)
    # Ephemeral cookie temp file and parent dir must be deleted immediately.
    assert seen_cookie_paths and all(not p.exists() and not p.parent.exists() for p in seen_cookie_paths)

    # Inter-attempt cooldown blocks immediate second run.
    assert service.can_attempt("vidNext0002") == (False, "YOUTUBE_AUTH_RATE_LIMITED")

    # Advancing +16s clears cooldown; switching to browser mode sends cookiesfrombrowser.
    clock["now"] = clock["now"] + timedelta(seconds=16)
    seen_opts.clear()
    service.update_config({"enabled": True, "auth_mode": "browser", "browser_name": "chrome", "daily_limit": 2, "cooldown_seconds": 15})
    _seed_video_source(env["repo"], source_id="src-auth-2", video_id="vidNext0002", now=clock["now"])
    res2 = service.attempt_authenticated_ingest(runtime, "src-auth-2", "vidNext0002")
    assert res2 is None
    assert any(o.get("cookiesfrombrowser") == ("chrome",) for o in seen_opts)

    # Daily limit (2) now exhausted -> blocks next attempt even after cooldown.
    clock["now"] = clock["now"] + timedelta(seconds=60)
    assert service.can_attempt("vidNext0003") == (False, "YOUTUBE_AUTH_RATE_LIMITED")

    # Reset limit higher, then trigger auth rejection -> opens 30-min circuit breaker.
    service.update_config({"enabled": True, "auth_mode": "browser", "browser_name": "chrome", "daily_limit": 10, "cooldown_seconds": 10})
    outcome_mode["kind"] = "auth_rejected"
    _seed_video_source(env["repo"], source_id="src-auth-3", video_id="vidFail0003", now=clock["now"])
    fail_code = service.attempt_authenticated_ingest(runtime, "src-auth-3", "vidFail0003")
    assert fail_code == "YOUTUBE_AUTH_EXPIRED"
    status_open = service.get_status()
    assert status_open["circuit_open"] is True
    assert service.can_attempt("vidFail0003") == (False, "YOUTUBE_AUTH_RATE_LIMITED")

    # After CIRCUIT_BREAK_MINUTES + 1, circuit closes cleanly.
    clock["now"] = clock["now"] + timedelta(minutes=CIRCUIT_BREAK_MINUTES + 1)
    assert service.can_attempt("vidFail0003") == (True, None)


# ---------------------------------------------------------------------------
# RuntimeSourceRunIngestion: anonymous-first + Option B + API parity
# ---------------------------------------------------------------------------


def test_ingestion_anonymous_first_skips_auth_when_anonymous_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_runtime_env(tmp_path, monkeypatch)
    runtime: RuntimeOperations = env["runtime"]
    meta = YtDlpMetadataProvider(timeout_seconds=5.0)
    bind_metadata_hooks(meta, ydl_factory=_success_ydl_factory("vidAnon0001"))

    def sub_factory() -> YtDlpSubtitleAdapter:
        sub = YtDlpSubtitleAdapter(timeout_seconds=5.0)
        bind_subtitle_hooks(
            sub,
            ydl_factory=_success_ydl_factory("vidAnon0001"),
            opener=lambda _req, _t: _FakeHttpResponse(VALID_VTT),
        )
        return sub

    from dataclasses import replace

    anon_runtime = RuntimeOperations(
        config=runtime._config,
        project_root=runtime._root,
        dependencies=replace(
            runtime._dependencies,
            metadata_provider=meta,
            subtitle_adapter_factory=sub_factory,
        ),
        repository=env["repo"],
    )
    auth_calls = {"count": 0}
    auth_svc = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=_MemorySecret(),
        now=lambda: BASE_NOW,
    )
    auth_svc.update_config({"enabled": True, "auth_mode": "browser", "browser_name": "chrome"})

    def spy_attempt(*_a: object) -> str | None:
        auth_calls["count"] += 1
        return None

    monkeypatch.setattr(auth_svc, "attempt_authenticated_ingest", spy_attempt)

    ingestion = RuntimeSourceRunIngestion(anon_runtime, env["source_policy"], None)
    ingestion._youtube_auth_fallback = auth_svc  # type: ignore[attr-defined]

    _seed_video_source(env["repo"], source_id="src-anon-ok", video_id="vidAnon0001")
    ingestion.ingest("src-anon-ok")

    assert auth_calls["count"] == 0
    assert env["repo"].get_video("vidAnon0001") is not None
    assert env["repo"].get_verified_timed_transcript(video_id="vidAnon0001") is not None


def test_ingestion_error_classification_and_api_parity_for_network_vs_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_runtime_env(tmp_path, monkeypatch)
    runtime: RuntimeOperations = env["runtime"]
    from dataclasses import replace

    # Case 1: Network unreachable (no VPN) -> NEVER invokes Option B fallback & persists YOUTUBE_NETWORK_UNAVAILABLE
    class _NetDownMeta:
        def fetch(self, video_id: str) -> Any:
            del video_id
            raise AdapterError(
                AppError(
                    code=ErrorCode.TRANSIENT_NETWORK,
                    message="Unable to reach YouTube",
                    retryable=True,
                )
            )

    net_runtime = RuntimeOperations(
        config=runtime._config,
        project_root=runtime._root,
        dependencies=replace(runtime._dependencies, metadata_provider=_NetDownMeta()),
        repository=env["repo"],
    )
    auth_svc = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=_MemorySecret(),
        now=lambda: BASE_NOW,
    )
    auth_svc.update_config({"enabled": True, "auth_mode": "browser", "browser_name": "chrome"})
    auth_calls = {"count": 0}
    monkeypatch.setattr(
        auth_svc,
        "attempt_authenticated_ingest",
        lambda *_a: (auth_calls.__setitem__("count", auth_calls["count"] + 1) or None),
    )

    net_ingestor = RuntimeSourceRunIngestion(net_runtime, env["source_policy"], None)
    net_ingestor._youtube_auth_fallback = auth_svc  # type: ignore[attr-defined]
    _seed_video_source(env["repo"], source_id="src-net-fail", video_id="vidNetDown1")
    with pytest.raises(SourceRunDiscoveryError):
        net_ingestor.ingest("src-net-fail")
    assert auth_calls["count"] == 0

    # Case 2: Bot check when Option B DISABLED -> persists YOUTUBE_AUTH_REQUIRED
    class _AuthGateMeta:
        def fetch(self, video_id: str) -> Any:
            del video_id
            raise AdapterError(
                AppError(
                    code=ErrorCode.PERMISSION_DENIED,
                    message="youtube authentication required (anonymous verification gate)",
                    retryable=False,
                )
            )

    auth_gate_runtime = RuntimeOperations(
        config=runtime._config,
        project_root=runtime._root,
        dependencies=replace(runtime._dependencies, metadata_provider=_AuthGateMeta()),
        repository=env["repo"],
    )
    disabled_auth = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=_MemorySecret(),
        now=lambda: BASE_NOW,
    )
    disabled_auth.disconnect()

    auth_ingestor = RuntimeSourceRunIngestion(auth_gate_runtime, env["source_policy"], None)
    auth_ingestor._youtube_auth_fallback = disabled_auth  # type: ignore[attr-defined]
    _seed_video_source(env["repo"], source_id="src-auth-req", video_id="vidAuthReq2")
    with pytest.raises(SourceRunDiscoveryError):
        auth_ingestor.ingest("src-auth-req")

    # Verify both LocalApiApplication and FastReadApiApplication expose matching import_error_code
    raw_code, raw_body = env["raw_app"].handle("GET", "/api/v1/videos")
    fast_code, fast_body = env["fast_app"].handle("GET", "/api/v1/videos")
    assert raw_code == HTTPStatus.OK
    assert fast_code == HTTPStatus.OK
    raw_pending = {item["video_id"]: item for item in raw_body["videos"]}
    fast_pending = {item["video_id"]: item for item in fast_body["videos"]}
    assert raw_pending["vidNetDown1"]["import_error_code"] == "YOUTUBE_NETWORK_UNAVAILABLE"
    assert fast_pending["vidNetDown1"]["import_error_code"] == "YOUTUBE_NETWORK_UNAVAILABLE"
    assert raw_pending["vidAuthReq2"]["import_error_code"] == "YOUTUBE_AUTH_REQUIRED"
    assert fast_pending["vidAuthReq2"]["import_error_code"] == "YOUTUBE_AUTH_REQUIRED"
    raw_det_c, raw_det = env["raw_app"].handle("GET", "/api/v1/videos/vidAuthReq2")
    fast_det_c, fast_det = env["fast_app"].handle("GET", "/api/v1/videos/vidAuthReq2")
    assert raw_det_c == HTTPStatus.OK and fast_det_c == HTTPStatus.OK
    assert raw_det["video"]["import_error_code"] == "YOUTUBE_AUTH_REQUIRED"
    assert fast_det["video"]["import_error_code"] == "YOUTUBE_AUTH_REQUIRED"

    # Case 3: Bot check when Option B IS enabled -> triggers Option B & completes ingestion!
    monkeypatch.setattr(
        "youtube_intel.providers.youtube._resolve_system_proxy_url", lambda: None
    )
    monkeypatch.setattr(
        "youtube_intel.providers.subtitles._resolve_system_proxy_url", lambda: None
    )
    monkeypatch.setattr(
        "urllib.request.OpenerDirector.open",
        lambda _self, _req, timeout=None: _FakeHttpResponse(VALID_VTT),
    )
    live_auth = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=_MemorySecret(),
        ydl_factory=_success_ydl_factory("vidAuthOk03"),
        now=lambda: BASE_NOW,
    )
    live_auth.update_config({"enabled": True, "auth_mode": "browser", "browser_name": "chrome"})
    live_ingestor = RuntimeSourceRunIngestion(auth_gate_runtime, env["source_policy"], None)
    live_ingestor._youtube_auth_fallback = live_auth  # type: ignore[attr-defined]
    _seed_video_source(env["repo"], source_id="src-auth-ok", video_id="vidAuthOk03")
    live_ingestor.ingest("src-auth-ok")
    assert env["repo"].get_video("vidAuthOk03") is not None
    assert env["repo"].get_verified_timed_transcript(video_id="vidAuthOk03") is not None


# ---------------------------------------------------------------------------
# Issue #2 & #4 — Curated Ollama / Whisper downloads, Cloud test, Zero-secret backup
# ---------------------------------------------------------------------------


def test_workspace_ai_curated_downloads_cloud_test_and_routes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_ollama_pull(_base_url: str, model: str, report: Any) -> None:
        report({"completed_bytes": 500, "total_bytes": 1000, "percent": 50, "status_text": "downloading"})
        assert model == "qwen3:8b"

    whisper_calls: list[tuple[str, str]] = []

    def fake_whisper_download(model_id: str, slug: str, mirror: str, report: Any) -> Path:
        whisper_calls.append((model_id, mirror))
        report({"completed_files": 1, "total_files": 2, "percent": 50, "mirror_used": "https://hf-mirror.com"})
        out_dir = tmp_path.resolve() / "workspace" / ".local-transcription" / "models" / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "config.json").write_text("{}", encoding="utf-8")
        (out_dir / "weights.safetensors").write_bytes(b"weights")
        return out_dir

    def fake_cloud_test(url: str, api_key: str) -> dict[str, object]:
        if api_key == "sk-bad-key":
            return {"ok": False, "code": "INVALID_API_KEY", "message": "API Key 无效或已过期"}
        return {"ok": True, "latency_ms": 42, "message": f"connected to {url}"}

    env = _build_runtime_env(
        tmp_path,
        monkeypatch,
        ollama_pull_runner=fake_ollama_pull,
        whisper_download_runner=fake_whisper_download,
        cloud_test_runner=fake_cloud_test,
    )
    fast_app: FastReadApiApplication = env["fast_app"]

    # 1. Settings exposes curated catalogs
    s_code, settings_body = fast_app.handle("GET", "/api/v1/workspace-ai/settings")
    assert s_code == HTTPStatus.OK
    assert len(settings_body["curated_ollama_models"]) >= 3
    assert len(settings_body["curated_whisper_models"]) >= 2

    # 2. 1-click Ollama pull auto-enables pulled model
    p_code, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/ollama/pull",
        json.dumps({"model": "qwen3:8b"}).encode("utf-8"),
    )
    assert p_code == HTTPStatus.ACCEPTED
    for _ in range(40):
        _, st = fast_app.handle("GET", "/api/v1/workspace-ai/ollama/pull-status")
        if st["state"] == "succeeded":
            break
        time.sleep(0.02)
    assert st["state"] == "succeeded"
    assert st["percent"] == 100
    _, s_after_pull = fast_app.handle("GET", "/api/v1/workspace-ai/settings")
    assert s_after_pull["active_mode"] == "local_ollama"
    assert s_after_pull["ollama_model"] == "qwen3:8b"

    # 3. 1-click Whisper download writes model.json & hot-reloads readiness
    w_code, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/whisper/download",
        json.dumps({"model_id": "mlx-community/whisper-large-v3-turbo", "mirror": "cn_mirror"}).encode("utf-8"),
    )
    assert w_code == HTTPStatus.ACCEPTED
    for _ in range(40):
        _, wst = fast_app.handle("GET", "/api/v1/workspace-ai/whisper/download-status")
        if wst["state"] == "succeeded":
            break
        time.sleep(0.02)
    assert wst["state"] == "succeeded"
    assert whisper_calls == [("mlx-community/whisper-large-v3-turbo", "cn_mirror")]
    model_json = env["project_root"] / ".local-transcription" / "model.json"
    assert model_json.is_file()
    _, s_after_whisper = fast_app.handle("GET", "/api/v1/workspace-ai/settings")
    assert s_after_whisper["local_mlx_Whisper_ready"] is True
    assert s_after_whisper["active_whisper_slug"] == "whisper-large-v3-turbo"

    # 4. Cloud test validates SSRF and handles valid vs 401
    monkeypatch.setattr(
        "youtube_intel.workspace_intelligence_hub._verify_cloud_endpoint_dns",
        lambda _url: None,
    )
    ok_c, ok_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/test-cloud",
        json.dumps({"cloud_base_url": "https://api.deepseek.com/v1", "cloud_api_key": "sk-good-123"}).encode("utf-8"),
    )
    assert ok_c == HTTPStatus.OK and ok_body["ok"] is True

    bad_c, bad_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/test-cloud",
        json.dumps({"cloud_base_url": "https://api.deepseek.com/v1", "cloud_api_key": "sk-bad-key"}).encode("utf-8"),
    )
    assert bad_c == HTTPStatus.OK and bad_body["ok"] is False
    assert bad_body["code"] == "INVALID_API_KEY"

    ssrf_code, ssrf_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/test-cloud",
        json.dumps({"cloud_base_url": "http://127.0.0.1:8080/v1", "cloud_api_key": "sk-good-123"}).encode("utf-8"),
    )
    assert ssrf_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert ssrf_body["error"]["code"] == "VALIDATION_ERROR"

    # 5. YouTube auth HTTP routes + zero-secret backup export check
    y_put, y_put_body = fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/youtube-auth",
        json.dumps({"enabled": True, "auth_mode": "cookie_file", "cookies_txt": VALID_COOKIES}).encode("utf-8"),
    )
    assert y_put == HTTPStatus.OK and y_put_body["enabled"] is True
    env["byok_store"].save("sk-secret-cloud-key-999")

    b_code, b_body = fast_app.handle("GET", "/api/v1/workspace-ai/backup")
    assert b_code == HTTPStatus.OK
    serialized_backup = json.dumps(b_body)
    assert "dummy_secret_cookie_val" not in serialized_backup
    assert "sk-secret-cloud-key-999" not in serialized_backup
    assert "youtube_auth" not in serialized_backup

    y_dis, y_dis_body = fast_app.handle("POST", "/api/v1/workspace-ai/youtube-auth/disconnect", b"{}")
    assert y_dis == HTTPStatus.OK and y_dis_body["enabled"] is False


def test_p2_02_cookie_domain_filtering_and_secret_non_leakage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    env = _build_runtime_env(tmp_path, monkeypatch)
    fast_app: FastReadApiApplication = env["fast_app"]
    secret_store = _MemorySecret()
    service = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=secret_store,
        now=lambda: BASE_NOW,
    )

    # Reject deceptive lookalike / suffix-spoofed / IP / wildcard domains
    for bad_cookie in (
        ".evil-youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\tBAD_TOKEN_1\n",
        "youtube.com.attacker.test\tTRUE\t/\tTRUE\t1893456000\tSID\tBAD_TOKEN_2\n",
        ".notgoogle.com\tTRUE\t/\tTRUE\t1893456000\tSID\tBAD_TOKEN_3\n",
        "127.0.0.1\tFALSE\t/\tFALSE\t1893456000\tSID\tBAD_TOKEN_4\n",
        "*.youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\tBAD_TOKEN_5\n",
    ):
        with pytest.raises(ValueError, match="youtube.com"):
            validate_netscape_cookies_txt(bad_cookie)

    # Mixed file: valid YouTube/Google cookies preserved; third-party unrelated site cookies dropped
    mixed_cookies = (
        "# Netscape HTTP Cookie File\n"
        "bank.example\tFALSE\t/\tTRUE\t1893456000\tBANK_SESSION\tFAKE_THIRD_PARTY_SECRET_BANK\n"
        "#HttpOnly_github.com\tFALSE\t/\tTRUE\t1893456000\tGH_SESS\tFAKE_GITHUB_SECRET\n"
        ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\tFAKE_YT_SECRET_999\n"
        "accounts.google.com\tFALSE\t/\tTRUE\t1893456000\tSID\tFAKE_GOOGLE_SECRET_888\n"
        ".googlevideo.com\tTRUE\t/\tTRUE\t1893456000\tPREF\tFAKE_GV_SECRET_777\n"
    )
    filtered = validate_netscape_cookies_txt(mixed_cookies)
    assert "FAKE_YT_SECRET_999" in filtered
    assert "FAKE_GOOGLE_SECRET_888" in filtered
    assert "FAKE_GV_SECRET_777" in filtered
    assert "bank.example" not in filtered
    assert "FAKE_THIRD_PARTY_SECRET_BANK" not in filtered
    assert "github.com" not in filtered
    assert "FAKE_GITHUB_SECRET" not in filtered

    with caplog.at_level("DEBUG"):
        status = service.update_config(
            {
                "enabled": True,
                "auth_mode": "cookie_file",
                "cookies_txt": mixed_cookies,
            }
        )
    assert status["cookie_configured"] is True
    stored = secret_store.get() or ""
    assert "bank.example" not in stored
    assert "FAKE_THIRD_PARTY_SECRET_BANK" not in stored
    assert "FAKE_YT_SECRET_999" in stored

    # Fake secret never leaks via status, SQLite DB dump, backup JSON, or logs
    assert "FAKE_YT_SECRET_999" not in json.dumps(service.get_status())
    assert "FAKE_YT_SECRET_999" not in caplog.text
    with sqlite3.connect(service.db_path) as conn:
        db_dump = "\n".join(conn.iterdump())
    assert "FAKE_YT_SECRET_999" not in db_dump
    b_code, b_body = fast_app.handle("GET", "/api/v1/workspace-ai/backup")
    assert b_code == HTTPStatus.OK
    serialized_backup = json.dumps(b_body)
    assert "FAKE_YT_SECRET_999" not in serialized_backup
    assert "FAKE_GOOGLE_SECRET_888" not in serialized_backup


def test_p1_04_atomic_sqlite_slot_reservation_cross_instance_race_and_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    env = _build_runtime_env(tmp_path, monkeypatch)
    runtime: RuntimeOperations = env["runtime"]
    secret_store = _MemorySecret()
    secret_store.save(VALID_COOKIES)

    monkeypatch.setattr(
        "youtube_intel.providers.youtube._resolve_system_proxy_url", lambda: None
    )
    monkeypatch.setattr(
        "youtube_intel.providers.subtitles._resolve_system_proxy_url", lambda: None
    )
    monkeypatch.setattr(
        "urllib.request.OpenerDirector.open",
        lambda _self, _req, timeout=None: _FakeHttpResponse(VALID_VTT),
    )

    calls: list[str] = []
    calls_lock = threading.Lock()
    entered_network = threading.Event()
    release_network = threading.Event()

    def make_slow_ydl(vid: str) -> Any:
        base_factory = _success_ydl_factory(vid)

        def factory(opts: dict[str, Any]) -> Any:
            with calls_lock:
                calls.append(str(opts.get("cookiefile", "browser")))
            entered_network.set()
            assert release_network.wait(timeout=3.0)
            return base_factory(opts)

        return factory

    # Two independent service instances pointing to same workspace/SQLite
    svc_a = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=secret_store,
        ydl_factory=make_slow_ydl("vidRace0001"),
        now=lambda: BASE_NOW,
    )
    svc_b = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=secret_store,
        ydl_factory=make_slow_ydl("vidRace0002"),
        now=lambda: BASE_NOW,
    )
    svc_a.update_config(
        {
            "enabled": True,
            "auth_mode": "cookie_file",
            "cookies_txt": VALID_COOKIES,
            "daily_limit": 1,
            "cooldown_seconds": 15,
        }
    )

    _seed_video_source(env["repo"], source_id="src-race-1", video_id="vidRace0001")
    _seed_video_source(env["repo"], source_id="src-race-2", video_id="vidRace0002")

    results: list[str | None] = []
    res_lock = threading.Lock()
    barrier = threading.Barrier(2)

    def worker(svc: YouTubeAuthFallbackService, src_id: str, vid_id: str) -> None:
        barrier.wait(timeout=3.0)
        res = svc.attempt_authenticated_ingest(runtime, src_id, vid_id)
        with res_lock:
            results.append(res)

    t1 = threading.Thread(target=worker, args=(svc_a, "src-race-1", "vidRace0001"))
    t2 = threading.Thread(target=worker, args=(svc_b, "src-race-2", "vidRace0002"))
    t1.start()
    t2.start()
    assert entered_network.wait(timeout=3.0)
    # Give second thread ample opportunity to attempt reservation BEFORE thread 1 completes
    time.sleep(0.08)
    release_network.set()
    t1.join(timeout=5.0)
    t2.join(timeout=5.0)

    # Strictly 1 attempt execution (one temp cookiefile dir) despite 2 independent service instances racing for the last slot
    assert len(set(calls)) == 1
    assert sorted(r or "OK" for r in results) == ["OK", "YOUTUBE_AUTH_RATE_LIMITED"]

    # Subsequent cross-instance check sees quota consumed (used_today == 1)
    assert svc_b.get_status()["used_today"] == 1
    assert svc_b.can_attempt("vidRace0003") == (False, "YOUTUBE_AUTH_RATE_LIMITED")

    # Crash/BaseException simulation: unfinalized RESERVED slot still conservatively consumes quota & cooldown
    clock = {"now": BASE_NOW + timedelta(seconds=60)}

    class _AbortCrash(BaseException):
        pass

    def crash_factory(_opts: dict[str, Any]) -> Any:
        raise _AbortCrash("simulated abrupt process abort")

    svc_c = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=secret_store,
        ydl_factory=crash_factory,
        now=lambda: clock["now"],
    )
    svc_c.update_config(
        {
            "enabled": True,
            "auth_mode": "cookie_file",
            "cookies_txt": VALID_COOKIES,
            "daily_limit": 2,
            "cooldown_seconds": 15,
        }
    )
    _seed_video_source(env["repo"], source_id="src-crash-1", video_id="vidCrash001", now=clock["now"])
    with pytest.raises(_AbortCrash):
        svc_c.attempt_authenticated_ingest(runtime, "src-crash-1", "vidCrash001")
    # Quota 2/2 is now conservatively exhausted (1 succeeded + 1 RESERVED crash)
    assert svc_c.get_status()["used_today"] == 2
    assert svc_c.can_attempt("vidAfterCrash") == (False, "YOUTUBE_AUTH_RATE_LIMITED")

    # Disconnect cleanly clears config and immediately blocks all instances
    svc_c.disconnect()
    assert svc_a.can_attempt("vidAfterDisconnect") == (False, "YOUTUBE_AUTH_DISABLED")


def test_p1_r02_circuit_breaker_preserved_across_config_saves_and_disconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_runtime_env(tmp_path, monkeypatch)
    runtime: RuntimeOperations = env["runtime"]
    secret_store = _MemorySecret()
    secret_store.save(VALID_COOKIES)
    clock = {"now": BASE_NOW}
    network_calls: list[str] = []

    monkeypatch.setattr("youtube_intel.providers.youtube._resolve_system_proxy_url", lambda: None)
    monkeypatch.setattr("youtube_intel.providers.subtitles._resolve_system_proxy_url", lambda: None)

    class _RateLimitYdl:
        cookiejar = None

        def __enter__(self) -> _RateLimitYdl:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

        def extract_info(self, url: str, download: bool = False) -> object:
            del download
            network_calls.append(url)
            raise DownloadError("HTTP Error 429: Too Many Requests")

    svc_a = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=secret_store,
        ydl_factory=lambda _opts: _RateLimitYdl(),
        now=lambda: clock["now"],
    )
    svc_a.update_config(
        {"enabled": True, "auth_mode": "browser", "browser_name": "chrome", "daily_limit": 10, "cooldown_seconds": 15}
    )
    _seed_video_source(env["repo"], source_id="src-cb-1", video_id="vidCbGate01", now=clock["now"])
    code_fail = svc_a.attempt_authenticated_ingest(runtime, "src-cb-1", "vidCbGate01")
    assert code_fail == "YOUTUBE_RATE_LIMITED"
    assert len(network_calls) == 1
    first_status = svc_a.get_status()
    assert first_status["circuit_open"] is True
    first_deadline = str(first_status["circuit_open_until"])

    # Advance past normal cooldown (15s), still well inside 30-min circuit breaker
    clock["now"] = clock["now"] + timedelta(minutes=2)
    svc_b = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=secret_store,
        ydl_factory=lambda _opts: _RateLimitYdl(),
        now=lambda: clock["now"],
    )
    # Ordinary re-save (same or modified settings) MUST NOT clear active circuit or cooldown
    b_status = svc_b.update_config(
        {"enabled": True, "auth_mode": "browser", "browser_name": "safari", "daily_limit": 20, "cooldown_seconds": 10}
    )
    assert b_status["circuit_open"] is True
    assert b_status["circuit_open_until"] == first_deadline

    # Even disconnect + re-enable cannot bypass active 30-min rate limit breaker
    svc_b.disconnect()
    svc_b.update_config({"enabled": True, "auth_mode": "browser", "browser_name": "chrome"})

    svc_c = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=secret_store,
        ydl_factory=lambda _opts: _RateLimitYdl(),
        now=lambda: clock["now"],
    )
    assert svc_c.can_attempt("vidCbGate02") == (False, "YOUTUBE_AUTH_RATE_LIMITED")
    assert svc_c.attempt_authenticated_ingest(runtime, "src-cb-1", "vidCbGate02") == "YOUTUBE_AUTH_RATE_LIMITED"
    assert len(network_calls) == 1  # Zero extra external calls

    # Later finalization extends or preserves max deadline, never shortens it
    svc_c._record_usage(video_id="vidCbExtend", outcome="RATE_LIMITED", open_circuit=True)
    extended_deadline = str(svc_c.get_status()["circuit_open_until"])
    assert extended_deadline >= first_deadline


def test_p2_r03_legacy_keychain_and_browser_cookiejar_strict_filtering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import http.cookiejar

    env = _build_runtime_env(tmp_path, monkeypatch)
    runtime: RuntimeOperations = env["runtime"]
    monkeypatch.setattr("youtube_intel.providers.youtube._resolve_system_proxy_url", lambda: None)
    monkeypatch.setattr("youtube_intel.providers.subtitles._resolve_system_proxy_url", lambda: None)
    monkeypatch.setattr(
        "urllib.request.OpenerDirector.open",
        lambda _self, _req, timeout=None: _FakeHttpResponse(VALID_VTT),
    )

    # 1. Arbitrary comments stripped on validate_netscape_cookies_txt while preserving #HttpOnly_
    cleaned = validate_netscape_cookies_txt(
        "# arbitrary sensitive comment\n"
        ".evil.example\tTRUE\t/\tFALSE\t0\tBAD\tLEAK1\n"
        "#HttpOnly_.youtube.com\tTRUE\t/\tTRUE\t1893456000\tHSID\tGOOD_YT_HTTPONLY\n"
    )
    assert "arbitrary sensitive comment" not in cleaned
    assert "evil.example" not in cleaned
    assert "#HttpOnly_.youtube.com" in cleaned
    assert "GOOD_YT_HTTPONLY" in cleaned

    # 2. Legacy unfiltered Keychain store is re-filtered BEFORE temp file creation
    class _LegacyDirtyStore:
        def get(self) -> str:
            return (
                "# leaked note\n"
                "bank.example\tFALSE\t/\tTRUE\t1893456000\tSESS\tDIRTY_BANK_SECRET\n"
                ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\tCLEAN_YT_SECRET\n"
            )

        def save(self, value: str) -> None:
            del value

        def delete(self) -> None:
            pass

    observed_cookie_files: list[str] = []

    def _inspecting_factory(vid: str) -> Any:
        base = _success_ydl_factory(vid)

        def _make(opts: dict[str, Any]) -> Any:
            cf = opts.get("cookiefile")
            if cf:
                observed_cookie_files.append(Path(cf).read_text(encoding="utf-8"))
            return base(opts)

        return _make

    svc_legacy = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=_LegacyDirtyStore(),
        ydl_factory=_inspecting_factory("vidLegacy01"),
        now=lambda: BASE_NOW,
    )
    # Write config enabling cookie_file without re-uploading cookies
    svc_legacy.update_config({"enabled": True, "auth_mode": "cookie_file"})
    _seed_video_source(env["repo"], source_id="src-leg-1", video_id="vidLegacy01")
    assert svc_legacy.attempt_authenticated_ingest(runtime, "src-leg-1", "vidLegacy01") is None
    assert observed_cookie_files and "CLEAN_YT_SECRET" in observed_cookie_files[0]
    assert "DIRTY_BANK_SECRET" not in observed_cookie_files[0]
    assert "bank.example" not in observed_cookie_files[0]
    assert "leaked note" not in observed_cookie_files[0]

    # 3. Browser mode filters non-YouTube/Google cookies in handle.cookiejar BEFORE extract_info & opener
    jar = http.cookiejar.CookieJar()
    for dom, cname, cval in (
        (".bank.example", "BANK_TOK", "SECRET_BANK_COOKIE"),
        (".youtube.com.evil.test", "SPOOF", "SECRET_SPOOF"),
        (".youtube.com", "SAPISID", "VALID_YT_BROWSER_COOKIE"),
        (".google.com", "NID", "VALID_GOOGLE_BROWSER_COOKIE"),
    ):
        jar.set_cookie(
            http.cookiejar.Cookie(
                version=0, name=cname, value=cval, port=None, port_specified=False,
                domain=dom, domain_specified=True, domain_initial_dot=dom.startswith("."),
                path="/", path_specified=True, secure=True, expires=1893456000,
                discard=False, comment=None, comment_url=None, rest={},
            )
        )

    saw_domains_in_extract: list[set[str]] = []

    def _browser_jar_factory(opts: dict[str, Any]) -> Any:
        del opts
        base = _success_ydl_factory("vidJar00001")({})

        class _JarYdl:
            cookiejar = jar

            def __enter__(self) -> _JarYdl:
                return self

            def __exit__(self, *_a: object) -> None:
                return None

            def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
                saw_domains_in_extract.append({c.domain for c in jar})
                return base.extract_info(url, download=download)

        return _JarYdl()

    clock2 = {"now": BASE_NOW + timedelta(seconds=60)}
    svc_browser = YouTubeAuthFallbackService(
        project_root=env["project_root"],
        cookie_store=_LegacyDirtyStore(),
        ydl_factory=_browser_jar_factory,
        now=lambda: clock2["now"],
    )
    svc_browser.update_config({"enabled": True, "auth_mode": "browser", "browser_name": "chrome"})
    _seed_video_source(env["repo"], source_id="src-jar-1", video_id="vidJar00001", now=clock2["now"])
    assert svc_browser.attempt_authenticated_ingest(runtime, "src-jar-1", "vidJar00001") is None
    assert saw_domains_in_extract
    assert saw_domains_in_extract[0] == {".youtube.com", ".google.com"}
