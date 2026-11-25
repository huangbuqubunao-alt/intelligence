"""End-to-end regression suite verifying all Codex review findings (P1-1..P1-5, P2-2)."""

from __future__ import annotations

import importlib.util
import io
import json
import socket
import sqlite3
import ssl
import threading
import zipfile
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from tests.e2e.offline_executor_fixture import ProcessFixtureExecutor
from tests.integration.test_codex_review_remediation import _build_env, _StubCompleter
from youtube_intel.demo_showcase import prepare_demo_showcase
from youtube_intel.local_content import LocalContentProvider
from youtube_intel.offline_transcription import MlxTimedExecutor
from youtube_intel.source_authority import verify_source
from youtube_intel.workspace_intelligence_hub import ApiError, WorkspaceIntelligenceHub

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 24, 16, 0, tzinfo=UTC)
MINIMAL_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


def _extract_zip_qa_markdown(zip_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        md_names = [n for n in zf.namelist() if n.startswith("04-跨视频深度问答/") and n.endswith(".md")]
        assert md_names, f"No Q&A markdown found in ZIP: {zf.namelist()}"
        return "\n".join(zf.read(n).decode("utf-8") for n in md_names)


# ---------------------------------------------------------------------------
# P1-1: Independent fact & list-item citation grounding + short valid answers
# ---------------------------------------------------------------------------


def test_p1_1_ungrounded_comma_and_inline_list_claims_stripped_while_short_answer_survives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenarios: dict[str, dict[str, Any]] = {
        "comma_trailing_fab": {
            "answerable": True,
            "answer_zh": "清点七件样品[E1]，明年已售九十件。",
            "key_takeaways_zh": ["清点七件样品[E1]\n明年已售九十件"],
            "action_items_zh": ["核对七件样品[E1]，明年已售九十件"],
            "citations": [{"ref": "E1", "note_zh": "原文来源"}],
        },
        "nospace_cn_num": {
            "answerable": True,
            "answer_zh": "一、清点七件样品[E1]二、明年已售九十件",
            "key_takeaways_zh": ["（1）清点七件样品[E1]（2）明年已售九十件"],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "原文来源"}],
        },
        "leading_ungrounded": {
            "answerable": True,
            "answer_zh": "明年已售九十件，清点七件样品[E1]。",
            "key_takeaways_zh": [],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "原文来源"}],
        },
        "short_valid": {
            "answerable": True,
            "answer_zh": "七件 [E1]。",
            "key_takeaways_zh": ["七件 [E1]"],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "精确依据"}],
        },
    }

    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            for key, payload in scenarios.items():
                if key in user_prompt:
                    return dict(payload), provider, model
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, name="p1_1", completer=_StubCompleter(_completer))
    hub: WorkspaceIntelligenceHub = env["hub"]
    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_bytes(
        "samples.md", "清点七件样品".encode("utf-8")
    )
    vid = imp.content_id

    for key in ("comma_trailing_fab", "nospace_cn_num", "leading_ungrounded"):
        sess = hub.ask_research_question({"question": f"{key} 样品数量是多少？", "video_ids": [vid]})["session"]
        assert sess["answer_status"] == "GROUNDED"
        assert "七件" in str(sess["answer_zh"])
        assert "九十件" not in str(sess["answer_zh"])
        assert "九十件" not in " ".join(sess["key_takeaways_zh"])
        assert "九十件" not in " ".join(sess["action_items_zh"])
        assert "九十件" not in str(sess["obsidian_markdown"])

    # Short valid grounded answer must survive pruning as GROUNDED
    s_short = hub.ask_research_question({"question": "short_valid 样品共几件？", "video_ids": [vid]})["session"]
    assert s_short["answer_status"] == "GROUNDED"
    assert s_short["refused"] is False
    assert "七件" in str(s_short["answer_zh"])
    assert len(s_short["citations"]) == 1

    # History, restore, and ZIP export all preserve "七件" and exclude "九十件"
    hist = hub.list_research_sessions()["sessions"]
    for item in hist:
        assert "七件" in str(item["answer_zh"])
        assert "九十件" not in str(item["answer_zh"])
        assert "九十件" not in str(item["obsidian_markdown"])

    snap = hub.export_backup_snapshot()
    hub.restore_backup_snapshot(snap)
    restored_hist = hub.list_research_sessions()["sessions"]
    for item in restored_hist:
        assert "七件" in str(item["answer_zh"])
        assert "九十件" not in str(item["answer_zh"])

    _, zip_bytes, _, _ = hub.build_obsidian_vault_zip(scope="all")
    qa_zip_md = _extract_zip_qa_markdown(zip_bytes)
    assert "七件" in qa_zip_md
    assert "九十件" not in qa_zip_md


# ---------------------------------------------------------------------------
# P1-2: Disk-backed evidence freshness even with unchanged DB/WAL fingerprint
# ---------------------------------------------------------------------------


def test_p1_2_mutated_or_restored_local_file_syncs_hot_cache_cold_hub_and_zip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del user_prompt, mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            return (
                {
                    "answerable": True,
                    "answer_zh": "本地文稿确认核心策略为清点七件样品[E1]。",
                    "key_takeaways_zh": ["文稿确认七件样品[E1]"],
                    "action_items_zh": [],
                    "citations": [{"ref": "E1", "note_zh": "本地文稿依据"}],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt="",
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, name="p1_2", completer=_StubCompleter(_completer))
    hub: WorkspaceIntelligenceHub = env["hub"]
    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_bytes(
        "mutable.md", "清点七件样品".encode("utf-8")
    )
    vid = imp.content_id

    sess = hub.ask_research_question({"question": "文稿核对几个样品？", "video_ids": [vid]})["session"]
    assert sess["answer_status"] == "GROUNDED"

    # Hold an external SQLite read connection to keep DB/WAL fingerprint stable
    held_conn = sqlite3.connect(env["db_path"])
    try:
        rel_rows = held_conn.execute(
            "SELECT a.relative_path FROM content_source_snapshots cs "
            "JOIN artifacts a ON a.artifact_id = cs.canonical_artifact_id "
            "WHERE cs.content_id = ?",
            (vid,),
        ).fetchall()
        managed_files = [env["data_root"] / str(r[0]) for r in rel_rows]
        assert managed_files and all(p.is_file() for p in managed_files)
        saved_bytes = {p: p.read_bytes() for p in managed_files}

        # Warm the cache first while intact
        warm_ok = hub.list_research_sessions()["sessions"][0]
        assert warm_ok["answer_status"] == "GROUNDED"
        fp_before = hub._core_repo_fingerprint()

        # Tamper disk file (DB/WAL unchanged)
        target_file = managed_files[0]
        target_file.write_bytes(b"TAMPERED ON DISK")
        assert hub._core_repo_fingerprint() == fp_before
        with env["repo"]._connect(read_only=True) as ro_c:
            assert verify_source(env["repo"], ro_c, vid) is None

        hot_tampered = hub.list_research_sessions()["sessions"][0]
        assert hot_tampered["answer_status"] == "NEEDS_REVERIFICATION"
        assert all(not c.get("verified") for c in hot_tampered["citations"])

        cold_hub = WorkspaceIntelligenceHub(
            repository=env["repo"],
            data_root=env["data_root"],
            project_root=env["project_root"],
            now=lambda: NOW,
        )
        assert cold_hub.list_research_sessions()["sessions"][0]["answer_status"] == "NEEDS_REVERIFICATION"
        _, zip_tampered, _, _ = hub.build_obsidian_vault_zip(scope="all")
        assert "NEEDS_REVERIFICATION" in _extract_zip_qa_markdown(zip_tampered)

        # Delete file -> still NEEDS_REVERIFICATION
        target_file.unlink()
        assert hub.list_research_sessions()["sessions"][0]["answer_status"] == "NEEDS_REVERIFICATION"

        # Restore original file bytes -> hot cache, cold hub, and ZIP ALL recover to GROUNDED!
        target_file.write_bytes(saved_bytes[target_file])
        hot_restored = hub.list_research_sessions()["sessions"][0]
        assert hot_restored["answer_status"] == "GROUNDED"
        assert all(bool(c.get("verified")) for c in hot_restored["citations"])
        assert cold_hub.list_research_sessions()["sessions"][0]["answer_status"] == "GROUNDED"
        _, zip_restored, _, _ = hub.build_obsidian_vault_zip(scope="all")
        assert "answer_status: \"GROUNDED\"" in _extract_zip_qa_markdown(zip_restored)
    finally:
        held_conn.close()


# ---------------------------------------------------------------------------
# P1-3: Controlled refusal reasons across create, history, restore, and ZIP
# ---------------------------------------------------------------------------


def test_p1_3_refusal_reasons_never_leak_model_hallucinations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _refusal_completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del user_prompt, mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            return (
                {
                    "answerable": False,
                    "refusal_reason_zh": "因为明年已售九十件，所以不能回答",
                    "answer_zh": "明年已售九十件，无法回答。",
                    "key_takeaways_zh": ["明年已售九十件"],
                    "action_items_zh": ["明年已售九十件"],
                    "citations": [],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt="",
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, name="p1_3", completer=_StubCompleter(_refusal_completer))
    hub: WorkspaceIntelligenceHub = env["hub"]
    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_bytes(
        "only.md", "清点七件样品".encode("utf-8")
    )

    sess = hub.ask_research_question({"question": "明年销量多少？", "video_ids": [imp.content_id]})["session"]
    assert sess["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
    assert sess["refused"] is True
    assert sess["citations"] == []
    assert "九十件" not in str(sess["refusal_reason_zh"])
    assert "九十件" not in str(sess["answer_zh"])
    assert "九十件" not in str(sess["obsidian_markdown"])

    hist = hub.list_research_sessions()["sessions"][0]
    assert "九十件" not in str(hist["refusal_reason_zh"])
    assert "九十件" not in str(hist["answer_zh"])
    assert "九十件" not in str(hist["obsidian_markdown"])

    _, zip_bytes, _, _ = hub.build_obsidian_vault_zip(scope="all")
    assert "九十件" not in _extract_zip_qa_markdown(zip_bytes)

    # Also sanitize tampered legacy/backup rows whose answer/markdown contain fake refusal text
    snap = hub.export_backup_snapshot()
    snap_sessions = snap["research_qa_sessions"]
    assert isinstance(snap_sessions, list) and len(snap_sessions) == 1
    snap_sessions[0]["answer_zh"] = "证据不足：因为明年已售九十件，所以不能回答"
    snap_sessions[0]["obsidian_markdown"] = "# 旧导出\n因为明年已售九十件，所以不能回答\n"
    hub.restore_backup_snapshot(snap)
    restored = hub.list_research_sessions()["sessions"][0]
    assert "九十件" not in str(restored["answer_zh"])
    assert "九十件" not in str(restored["obsidian_markdown"])


# ---------------------------------------------------------------------------
# P1-4: Fail-closed DNS + pinned-IP TLS across text, vision, and test-cloud
# ---------------------------------------------------------------------------


def _run_with_pinned_socket_capture(
    monkeypatch: pytest.MonkeyPatch,
    *,
    dns_ips_sequence: list[list[str]],
    response_payload: dict[str, object],
    fn: Any,
) -> tuple[list[tuple[str, int]], list[tuple[bool, ssl.VerifyMode, str | None]], int]:
    connected_addrs: list[tuple[str, int]] = []
    tls_wraps: list[tuple[bool, ssl.VerifyMode, str | None]] = []
    dns_calls = {"count": 0}
    raw_resp_body = json.dumps(response_payload).encode("utf-8")
    raw_http = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(raw_resp_body)}\r\n".encode("ascii")
        + b"Connection: close\r\n\r\n"
        + raw_resp_body
    )

    def fake_getaddrinfo(_host: Any, port: Any, *_args: Any, **_kwargs: Any) -> list[Any]:
        idx = min(dns_calls["count"], len(dns_ips_sequence) - 1)
        dns_calls["count"] += 1
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, int(port or 443)))
            for ip in dns_ips_sequence[idx]
        ]

    real_socket_cls = socket.socket
    real_socketpair = socket.socketpair

    class _FakeTcpSocket:
        def __init__(self) -> None:
            c_sock, s_sock = real_socketpair()
            self._client = c_sock
            self._server = s_sock
            self._sent = False

        def settimeout(self, timeout: float | None) -> None:
            self._client.settimeout(timeout)

        def bind(self, _addr: Any) -> None:
            return None

        def connect(self, addr: tuple[str, int]) -> None:
            connected_addrs.append((str(addr[0]), int(addr[1])))

        def _respond_once(self) -> None:
            if not self._sent:
                self._sent = True

                def _feed() -> None:
                    try:
                        self._server.settimeout(2.0)
                        buf = bytearray()
                        while b"\r\n\r\n" not in buf:
                            chunk = self._server.recv(65536)
                            if not chunk:
                                break
                            buf.extend(chunk)
                        sep = buf.find(b"\r\n\r\n")
                        if sep != -1:
                            expected_total = sep + 4
                            for hdr_line in buf[:sep].decode("latin1").split("\r\n")[1:]:
                                if hdr_line.lower().startswith("content-length:"):
                                    try:
                                        expected_total += max(
                                            0, int(hdr_line.split(":", 1)[1].strip())
                                        )
                                    except ValueError:
                                        pass
                                    break
                            while len(buf) < expected_total:
                                chunk = self._server.recv(65536)
                                if not chunk:
                                    break
                                buf.extend(chunk)
                        self._server.sendall(raw_http)
                        try:
                            self._server.shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                    except OSError:
                        pass
                    finally:
                        try:
                            self._server.close()
                        except OSError:
                            pass

                threading.Thread(target=_feed, daemon=True).start()

        def close(self) -> None:
            self._client.close()
            try:
                self._server.close()
            except OSError:
                pass

    def fake_socket(*args: Any, **kwargs: Any) -> Any:
        if len(args) > 2 or "fileno" in kwargs:
            return real_socket_cls(*args, **kwargs)
        return _FakeTcpSocket()

    def fake_wrap_socket(
        ctx: ssl.SSLContext,
        sock: _FakeTcpSocket,
        *,
        server_hostname: str | None = None,
        **_kwargs: Any,
    ) -> socket.socket:
        tls_wraps.append((ctx.check_hostname, ctx.verify_mode, server_hostname))
        sock._respond_once()
        return sock._client

    with monkeypatch.context() as mp:
        mp.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        mp.setattr(socket, "socket", fake_socket)
        mp.setattr(ssl.SSLContext, "wrap_socket", fake_wrap_socket)
        fn()
    return connected_addrs, tls_wraps, dns_calls["count"]


def test_p1_4_cloud_dns_fail_closed_and_pinned_ip_tls_on_all_three_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch, name="p1_4")
    hub: WorkspaceIntelligenceHub = env["hub"]
    hub._byok_store.save("sk-fake-pinned-tls-test")
    hub.update_settings(
        {
            "active_mode": "cloud_byok",
            "cloud_provider": "openai_compatible",
            "cloud_base_url": "https://rebind-check.example/v1",
            "cloud_model": "gpt-4o-mini",
            "cloud_daily_call_limit": 20,
        }
    )
    hub._llm_completer = None
    hub._vision_completer = None
    hub._http_opener = None

    img_path = tmp_path / "frame.jpg"
    img_path.write_bytes(MINIMAL_JPEG)

    # 1. DNS OSError MUST fail closed (NOT silently proceed) across text, vision, and test-cloud
    with monkeypatch.context() as dns_err_mp:
        dns_err_mp.setattr(
            socket,
            "getaddrinfo",
            lambda *_a, **_k: (_ for _ in ()).throw(socket.gaierror("DNS temporary failure")),
        )
        for call in (
            lambda: hub._complete_json(system_prompt="s", user_prompt="u", allow_cloud=True),
            lambda: hub._complete_vision_json(
                system_prompt="s",
                user_prompt="u",
                image_paths=[img_path],
                allow_cloud=True,
            ),
            lambda: hub.test_cloud_connection({"cloud_base_url": "https://rebind-check.example/v1"}),
        ):
            with pytest.raises(ApiError) as exc:
                call()
            assert exc.value.code == "CLOUD_ENDPOINT_BLOCKED"

    # 2. DNS rebinding flip (public 93.184.216.34 first, private 127.0.0.1 if re-resolved):
    # All three paths must perform a single DNS lookup, dial ("93.184.216.34", 443), and
    # verify TLS server_hostname == "rebind-check.example"
    llm_ok_payload = {"choices": [{"message": {"content": json.dumps({"ok": True})}}]}
    for label, action in (
        ("text", lambda: hub._complete_json(system_prompt="s", user_prompt="u", allow_cloud=True)),
        (
            "vision",
            lambda: hub._complete_vision_json(
                system_prompt="s",
                user_prompt="u",
                image_paths=[img_path],
                allow_cloud=True,
            ),
        ),
        (
            "test_cloud",
            lambda: hub.test_cloud_connection({"cloud_base_url": "https://rebind-check.example/v1"}),
        ),
    ):
        addrs, tls_wraps, dns_count = _run_with_pinned_socket_capture(
            monkeypatch,
            dns_ips_sequence=[["93.184.216.34"], ["127.0.0.1"]],
            response_payload=(
                {"data": [{"id": "gpt-4o-mini"}]} if label == "test_cloud" else llm_ok_payload
            ),
            fn=action,
        )
        assert dns_count == 1, f"{label} performed {dns_count} DNS resolutions"
        assert addrs == [("93.184.216.34", 443)], f"{label} dialed wrong addr: {addrs}"
        assert tls_wraps == [(True, ssl.CERT_REQUIRED, "rebind-check.example")], (
            f"{label} TLS verification mismatch: {tls_wraps}"
        )


# ---------------------------------------------------------------------------
# P1-5: ProcessFixtureExecutor succeeds without host mlx_whisper package
# ---------------------------------------------------------------------------


def test_p1_5_process_fixture_executor_independent_of_host_mlx_whisper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.integration.test_offline_transcription_jobs import audio_bytes
    from youtube_intel.local_content import probe_media

    orig_find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name, *a, **kw: None if name == "mlx_whisper" else orig_find_spec(name, *a, **kw),
    )

    assert MlxTimedExecutor(temporary_root=tmp_path / "prod_tmp").capability().state == "RUNTIME_UNAVAILABLE"

    executor = ProcessFixtureExecutor(tmp_path / "fx")
    source = tmp_path / "voice.wav"
    source.write_bytes(audio_bytes())
    cap = executor.capability()
    assert cap.state == "READY" and cap.model_present
    res = executor.transcribe(source, duration_seconds=probe_media(source, ".wav"))
    assert res.language == "zh" and res.cues[0].start_ms == 125


# ---------------------------------------------------------------------------
# P2-2: Demo showcase bilingual parity (pricing traps, inverted premises, valid Qs)
# ---------------------------------------------------------------------------


def test_p2_2_demo_showcase_bilingual_pricing_negation_and_normal_question_parity(
    tmp_path: Path,
) -> None:
    runtime = prepare_demo_showcase(REPO_ROOT, demo_root=tmp_path / "demo_p2_2", reset=True)

    # All pricing & inverted-premise traps must refuse with 0 citations in BOTH zh & en
    for trap_q in (
        "Ollama 多少钱？",
        "How much does Ollama cost?",
        "How much is Ollama?",
        "What is the price of Ollama?",
        "为什么不需要证据引用？",
        "Why don't we need evidence citations?",
        "Why skip state machines?",
    ):
        c, body = runtime.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps({"question": trap_q}).encode("utf-8"),
        )
        assert c == HTTPStatus.OK, f"{trap_q} failed with {c}: {body}"
        sess = body["session"]
        assert sess["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE", f"Expected refusal for {trap_q}"
        assert sess["refused"] is True
        assert sess["citations"] == []

    # Normal explanatory questions (including positive prevention wording) must remain GROUNDED
    for valid_q in (
        "如何避免忽略证据引用？",
        "How to avoid ignoring evidence citations?",
        "Why are state machines useful?",
    ):
        c, body = runtime.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps({"question": valid_q}).encode("utf-8"),
        )
        assert c == HTTPStatus.OK, f"{valid_q} failed with {c}: {body}"
        sess = body["session"]
        assert sess["answer_status"] == "GROUNDED", f"False refusal on valid question: {valid_q} -> {sess}"
        assert sess["refused"] is False
        assert len(sess["citations"]) >= 1


# ---------------------------------------------------------------------------
# P1-03 & P2-03: Claim-vs-cited-evidence fact consistency & scope truth
# ---------------------------------------------------------------------------


def test_p1_03_deterministic_claim_vs_evidence_fact_and_negation_consistency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenarios: dict[str, dict[str, Any]] = {
        "pct_conflict": {
            "answerable": True,
            "answer_zh": "收入同比增长 300% [E1]。",
            "key_takeaways_zh": ["收入增长 300% [E1]"],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "增长数据"}],
        },
        "year_conflict": {
            "answerable": True,
            "answer_zh": "2028年公司实现营收增长 [E1]。",
            "key_takeaways_zh": [],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "年份"}],
        },
        "cur_conflict": {
            "answerable": True,
            "answer_zh": "核心客单价为 $500 [E1]。",
            "key_takeaways_zh": [],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "金额"}],
        },
        "count_conflict": {
            "answerable": True,
            "answer_zh": "已售出九十件样品 [E1]。",
            "key_takeaways_zh": [],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "样品数"}],
        },
        "negation_flip": {
            "answerable": True,
            "answer_zh": "目前已全面支持多人协作 [E1]。",
            "key_takeaways_zh": [],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "协作能力"}],
        },
        "valid_pct": {
            "answerable": True,
            "answer_zh": "营收同比上涨 5% [E1]。",
            "key_takeaways_zh": ["2025年营收增长 5% [E1]"],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "一致增长"}],
        },
        "valid_cn_to_arabic": {
            "answerable": True,
            "answer_zh": "共清点 7件样品 [E1]。",
            "key_takeaways_zh": [],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "中文阿拉伯等价"}],
        },
        "valid_negation": {
            "answerable": True,
            "answer_zh": "系统目前仍不支持多人协作 [E1]。",
            "key_takeaways_zh": [],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "否定一致"}],
        },
    }

    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            for key, payload in scenarios.items():
                if key in user_prompt:
                    return dict(payload), provider, model
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, name="p1_03", completer=_StubCompleter(_completer))
    hub: WorkspaceIntelligenceHub = env["hub"]
    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_bytes(
        "q4_report.md",
        "2025年公司收入同比增长 5%，客单价为 $50，目前尚未支持多人协作，清点七件样品。".encode(
            "utf-8"
        ),
    )
    vid = imp.content_id

    for bad_key, forbidden_tok in (
        ("pct_conflict", "300%"),
        ("year_conflict", "2028"),
        ("cur_conflict", "500"),
        ("count_conflict", "九十"),
        ("negation_flip", "已全面支持多人协作"),
    ):
        res = hub.ask_research_question(
            {"question": f"{bad_key} 公司营收和协作情况如何？", "video_ids": [vid]}
        )
        sess = res["session"]
        assert sess["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE", bad_key
        assert sess["refused"] is True, bad_key
        assert sess["citations"] == [], bad_key
        assert forbidden_tok not in str(sess["answer_zh"])
        assert forbidden_tok not in str(sess["obsidian_markdown"])

    for good_key, expected_tok in (
        ("valid_pct", "5%"),
        ("valid_cn_to_arabic", "7件"),
        ("valid_negation", "不支持多人协作"),
    ):
        res = hub.ask_research_question(
            {"question": f"{good_key} 公司营收、样品与协作情况如何？", "video_ids": [vid]}
        )
        sess = res["session"]
        assert sess["answer_status"] == "GROUNDED", f"{good_key}: {sess}"
        assert sess["refused"] is False
        assert expected_tok in str(sess["answer_zh"])
        assert len(sess["citations"]) == 1

    # Simulate pre-existing persisted GROUNDED row whose claim contradicts cited E1
    valid_cite_json = json.dumps(res["session"]["citations"], ensure_ascii=False)  # type: ignore[index]
    with sqlite3.connect(hub.db_path) as conn:
        conn.execute(
            """
            INSERT INTO research_qa_sessions (
                session_id, question, answer_zh, key_takeaways_json,
                action_items_json, citations_json, video_count,
                provider, model, obsidian_markdown, created_at, scope_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "qa-legacy-conflict",
                "历史旧会话收入增长多少？",
                "收入同比增长 300% [E1]。",
                json.dumps(["收入同比增长 300% [E1]"], ensure_ascii=False),
                "[]",
                valid_cite_json,
                1,
                "ollama",
                "stub",
                "# 历史收入增长 300%",
                NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
                json.dumps({"answer_status": "GROUNDED", "refused": False}),
            ),
        )
        conn.commit()

    sessions = {s["session_id"]: s for s in hub.list_research_sessions()["sessions"]}
    legacy = sessions["qa-legacy-conflict"]
    assert legacy["answer_status"] == "NEEDS_REVERIFICATION"
    assert legacy["verification_status"] == "NEEDS_REVERIFICATION"
    assert "300%" not in str(legacy["answer_zh"])
    assert "300%" not in str(legacy["obsidian_markdown"])

    _, zip_bytes, _, _ = hub.build_obsidian_vault_zip(scope="all")
    qa_zip_md = _extract_zip_qa_markdown(zip_bytes)
    assert "300%" not in qa_zip_md
    assert "5%" in qa_zip_md


def test_p2_03_research_scope_options_exclude_tampered_local_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch, name="p2_03", completer=_StubCompleter())
    hub: WorkspaceIntelligenceHub = env["hub"]
    fast_app = env["fast_app"]

    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_bytes(
        "candidate_source.md",
        "局部缓存测试原文内容。".encode("utf-8"),
    )
    vid = imp.content_id

    code1, body1 = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert code1 == HTTPStatus.OK
    scope1 = body1["scope_options"]
    assert any(v["video_id"] == vid for v in scope1["videos"])
    assert scope1["candidate_source_count"] >= 1

    # Tamper managed source artifact file on disk without changing SQLite DB/WAL
    db_file = getattr(env["repo"], "_database_path", None)
    assert isinstance(db_file, Path)
    with sqlite3.connect(db_file) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT a.storage_root, a.relative_path
            FROM content_source_snapshots s
            JOIN artifacts a ON a.artifact_id = s.snapshot_artifact_id
            WHERE s.content_id = ?
            """,
            (vid,),
        ).fetchone()
    assert row is not None
    src_root = getattr(env["repo"], "_source_data_root", env["data_root"])
    base_root = src_root if row["storage_root"] == "SOURCE_DATA" else env["data_root"]
    (base_root / str(row["relative_path"])).write_text("TAMPERED", encoding="utf-8")

    # Tampered local source must fail verify_source and disappear from candidate scope
    scope_after = hub._build_research_scope_options()
    assert not any(v["video_id"] == vid for v in scope_after["videos"])  # type: ignore[index]
    code2, body2 = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert code2 == HTTPStatus.OK
    assert not any(v["video_id"] == vid for v in body2["scope_options"]["videos"])
