"""Self-contained fake-only continuation: no actual source, model or Native."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from youtube_intel.state import TimedTranscriptCueWrite, build_timed_transcript_hash


@pytest.fixture
def qa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    import socket

    monkeypatch.setattr(
        socket, "create_connection", lambda *_a, **_k: pytest.fail("actual network")
    )
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts/validation/kimi_summary_aware_diagnostic.py"
    )
    spec = importlib.util.spec_from_file_location("summary_aware_fake", path)
    assert spec and spec.loader
    m: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    class Clock:
        current = datetime(2026, 10, 29, 12, tzinfo=UTC)

        @classmethod
        def now(cls, _tz: Any = None) -> datetime:
            return cls.current

        fromisoformat = staticmethod(datetime.fromisoformat)

    m.datetime = Clock
    m.SOURCE = tmp_path / "source"
    m.PACKAGE = tmp_path / "package"
    m.LEDGER = tmp_path / "outside-restore-ledger"
    m.MISSING_PROOF = tmp_path / "missing-proof.json"
    m.SOURCE.mkdir()
    m.LEDGER.mkdir()
    (m.SOURCE / "data").mkdir()
    m.MISSING_PROOF.write_bytes(
        m.old.canonical(
            {"model_request_missing_baseline": True, "old_result_preserved": True}
        )
    )
    m.MISSING_PROOF_SHA = m.old.sha(m.MISSING_PROOF.read_bytes())
    text = "Wholly synthetic comparison text café 中文🙂. " * 8
    timed_hash = build_timed_transcript_hash(
        (TimedTranscriptCueWrite(start_ms=10, end_ms=100, text=text),)
    )
    ev = {
        "evidence_id": "outgoing-id",
        "start_ms": 10,
        "end_ms": 100,
        "excerpt": text,
        "excerpt_hash": m.old.sha(text.encode()),
        "timed_transcript_id": "capture",
        "timed_transcript_hash": timed_hash,
    }
    source = {
        "video_id": m.VIDEO,
        "reference_protocol": "bound-evidence-reference-v1",
        "evidence": [{"ref": "E01", "excerpt": text}],
    }
    original = {
        "messages": [
            {"role": "system", "content": "Original JSON/NO_NEW/ref/stance rules."},
            {
                "role": "system",
                "content": 'TASK_AND_PERSONALIZATION={"focus":["synthetic"]}',
            },
            {
                "role": "user",
                "content": "UNTRUSTED_SOURCE_EVIDENCE="
                + m.old.canonical(source).decode(),
            },
        ]
    }
    files = {
        "request-body.json": original,
        "reference-context.json": source,
        "verified-input.json": {"video_id": m.VIDEO, "evidence": [ev]},
    }
    for name, value in files.items():
        (m.SOURCE / name).write_bytes(m.old.canonical(value))
    m.SOURCE_HASHES = {
        name: m.old.sha((m.SOURCE / name).read_bytes()) for name in files
    }
    m.DOCS = {"official.txt": tmp_path / "official.txt"}
    m.DOCS["official.txt"].write_text("Synthetic fixed official snapshot only.")
    m.DOC_HASHES = {"official.txt": m.old.sha(m.DOCS["official.txt"].read_bytes())}
    raw = {
        "schema_version": "analysis-result-v1",
        "provider": "extractive-source",
        "model": "fake-excerpts",
        "prompt_version": "analysis-prompt-v6",
        "request_hash": "b" * 64,
        "one_sentence_summary": text[:100],
        "core_points": [{"text": text, "kind": "fact", "evidence_ids": ["old-id"]}],
        "key_facts": [],
        "product_opportunities": [],
        "business_opportunities": [],
        "actionable_directions": [],
        "hypotheses_to_validate": [],
        "action_recommendations": [],
        "risks": [],
        "keywords": ["synthetic"],
        "evidence": [
            {
                "evidence_id": "old-id",
                "source": "transcript_sample",
                "excerpt": text,
                "start_seconds": None,
                "end_seconds": None,
            }
        ],
    }
    (m.SOURCE / "data/summary.json").write_bytes(m.old.canonical(raw))
    (m.SOURCE / "data/canonical.txt").write_text(text)
    with sqlite3.connect(m.SOURCE / "state.sqlite3") as c:
        c.executescript("""PRAGMA user_version=15;
        CREATE TABLE videos(video_id TEXT,provider TEXT);
        CREATE TABLE current_content_summaries(video_id TEXT,result_identity TEXT,analysis_artifact_id TEXT,output_language TEXT,updated_at TEXT);
        CREATE TABLE artifacts(artifact_id TEXT,artifact_key TEXT,video_id TEXT,kind TEXT,storage_root TEXT,relative_path TEXT,content_hash TEXT,provider TEXT,model TEXT,deleted_at TEXT,expires_at TEXT);
        CREATE TABLE timed_transcripts(timed_transcript_id TEXT,video_id TEXT,canonical_artifact_id TEXT,timed_transcript_hash TEXT);
        CREATE TABLE timed_transcript_cues(timed_transcript_id TEXT,cue_index INTEGER,start_ms INTEGER,end_ms INTEGER,cue_text TEXT,cue_text_hash TEXT);
        CREATE TABLE evidence(evidence_id TEXT,video_id TEXT,artifact_id TEXT,start_ms INTEGER,end_ms INTEGER,availability TEXT);
        CREATE TABLE evidence_text_bindings(evidence_id TEXT,timed_transcript_id TEXT,start_cue_index INTEGER,end_cue_index INTEGER,excerpt TEXT,excerpt_hash TEXT,timed_transcript_hash TEXT);""")
        c.execute("INSERT INTO videos VALUES (?,?)", (m.VIDEO, "YOUTUBE"))
        c.execute(
            "INSERT INTO current_content_summaries VALUES (?,NULL,?,?,?)",
            (m.VIDEO, "summary/current", "en", "version-one"),
        )
        c.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?,?,NULL,NULL)",
            (
                "summary/current",
                "summary/current",
                m.VIDEO,
                "analysis_structured",
                "DATA",
                "summary.json",
                m.old.sha(m.old.canonical(raw)),
                "extractive-source",
                "fake-excerpts",
            ),
        )
        c.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?,?,NULL,NULL)",
            (
                "canonical",
                "canonical",
                m.VIDEO,
                "transcript_canonical",
                "DATA",
                "canonical.txt",
                m.old.sha(text.encode()),
                "fake",
                "fake",
            ),
        )
        c.execute(
            "INSERT INTO timed_transcripts VALUES (?,?,?,?)",
            ("capture", m.VIDEO, "canonical", timed_hash),
        )
        c.execute(
            "INSERT INTO timed_transcript_cues VALUES (?,0,10,100,?,?)",
            ("capture", text, m.old.sha(text.encode())),
        )
        for identity in ("old-id", "outgoing-id"):
            c.execute(
                "INSERT INTO evidence VALUES (?,?,?,10,100,?)",
                (identity, m.VIDEO, "canonical", "AVAILABLE"),
            )
            c.execute(
                "INSERT INTO evidence_text_bindings VALUES (?,?,0,1,?,?,?)",
                (identity, "capture", text, m.old.sha(text.encode()), timed_hash),
            )
    parent = {
        "reservation.json": {
            "case": m.PARENT,
            "model": m.MODEL,
            "reserve_microunits": 952118,
        },
        "result.json": {
            "case": m.PARENT,
            "status": "PUBLIC_FINAL_REVIEW_ONLY",
            "http_status": 200,
            "actual_model": m.MODEL,
            "finish_reason": "stop",
            "public_final_sha256": m.old.sha(b"{}"),
        },
        "public-final.txt": b"{}",
        "semantic-reject.json": {"decision": "REJECT", "reviewer": "Root"},
    }
    m.PARENT_HASHES = {}
    for suffix, parent_value in parent.items():
        data = (
            parent_value
            if isinstance(parent_value, bytes)
            else m.old.canonical(parent_value)
        )
        (m.LEDGER / f"{m.PARENT}.{suffix}").write_bytes(data)
        m.PARENT_HASHES[suffix] = m.old.sha(data)

    class NoNative:
        def get(self) -> None:
            pytest.fail("actual Native")

    m.QACredentialStore = NoNative
    return m


def approve(m: Any, *, continuation: bool = True) -> dict[str, Any]:
    _, prepared, _ = m.snapshot()
    m.prepare()
    expires = (m.datetime.now(UTC) + timedelta(minutes=10)).isoformat()
    m.old.write_once(
        m.PACKAGE / "review.json",
        m.old.canonical(
            {
                "decision": "APPROVE",
                "reviewer": "Root",
                "prepared_sha256": prepared["prepared_sha256"],
                "review_commit": "a" * 40,
                "max_calls": 1,
                "expires_at": expires,
            }
        ),
    )
    if continuation:
        m.old.write_once(
            m.PACKAGE / "owner-continuation.json",
            m.old.canonical(
                {
                    "decision": "AUTHORIZE_MISSING_SUMMARY_CONTINUATION",
                    "owner": "USER",
                    "user_decision_reference": "explicit-new-decision",
                    "case": m.CASE,
                    "prepared_sha256": prepared["prepared_sha256"],
                    "profile_id": m.PROFILE["id"],
                    "review_commit": "a" * 40,
                    "parent_case": m.PARENT,
                    "parent_hashes": m.PARENT_HASHES,
                    "missing_baseline_proof_sha256": m.MISSING_PROOF_SHA,
                    "max_calls": 1,
                    "max_reserve_microunits": 1_000_000,
                    "total_authorized_microunits": 8_000_000,
                    "expires_at": expires,
                }
            ),
        )
    return cast(dict[str, Any], prepared)


def envelope(m: Any, **changes: Any) -> bytes:
    value = {
        "model": m.MODEL,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": '{ "synthetic_public_final": true }',
                    "reasoning_content": "Private not retained.",
                },
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 14, "total_tokens": 26},
    }
    for key, item in changes.items():
        value[key] = item
    return cast(bytes, m.old.canonical(value))


def test_pure_prepare_complete_summary_proof_and_original_messages_unchanged(
    qa: Any,
) -> None:
    before = {
        p.relative_to(qa.SOURCE).as_posix(): p.read_bytes()
        for p in qa.SOURCE.rglob("*")
        if p.is_file()
    }
    prepared = qa.prepare()
    request = json.loads((qa.PACKAGE / "request.json").read_bytes())
    assert (
        request["messages"][:3] == json.loads(before["request-body.json"])["messages"]
    )
    assert (
        request["max_completion_tokens"] == 5888
        and qa.PROFILE["max_completion_tokens"] == 5888
    )
    assert len(request["messages"]) == 5
    assert request["messages"][-1]["content"].startswith(
        "UNTRUSTED_CURRENT_SUMMARY_BASELINE="
    )
    assert (
        len(qa.old.canonical(request)) <= 32768
        and prepared["reserve_microunits"] <= 1_000_000
    )
    proof = json.loads((qa.PACKAGE / "summary-context.json").read_bytes())
    assert set(proof["summary"]) == set(qa.baseline.SEMANTIC_FIELDS)
    assert "summary_raw_sha256" in proof and "summary_binding_sha256" in proof
    assert before == {
        p.relative_to(qa.SOURCE).as_posix(): p.read_bytes()
        for p in qa.SOURCE.rglob("*")
        if p.is_file()
    }
    assert not qa.reservation_path().exists()


def test_prior_reject_needs_new_owner_receipt_before_key_or_reserve(qa: Any) -> None:
    approve(qa, continuation=False)
    with pytest.raises(qa.old.Refused):
        qa.execute(
            credential=lambda: pytest.fail("key"), wire=lambda *_: pytest.fail("wire")
        )
    assert not qa.reservation_path().exists()


def test_new_bounded_continuation_preserves_parent_and_reserve_then_once(
    qa: Any, tmp_path: Path
) -> None:
    approve(qa)
    previous = {p.name: p.read_bytes() for p in qa.LEDGER.glob(qa.PARENT + ".*")}
    calls = []

    def key() -> str:
        assert qa.reservation_path().exists()
        calls.append("key")
        return "synthetic-secret"

    def wire(_body: bytes, _key: str) -> tuple[int, bytes]:
        calls.append("wire")
        return 200, envelope(qa)

    result = qa.execute(credential=key, wire=wire)
    assert (
        result["status"] == "PUBLIC_FINAL_REVIEW_ONLY"
        and result["semantic"] == "NOT_REVIEWED"
    )
    assert qa.final_path().read_bytes() == b'{ "synthetic_public_final": true }'
    assert result["actual_bill"] == "UNKNOWN"
    reserve = json.loads(qa.reservation_path().read_bytes())
    assert reserve["prior_reserved_microunits"] == 952118
    assert previous == {
        p.name: p.read_bytes() for p in qa.LEDGER.glob(qa.PARENT + ".*")
    }
    copied = tmp_path / "copy"
    shutil.copytree(qa.PACKAGE, copied)
    qa.PACKAGE = copied
    assert qa.execute(credential=lambda: pytest.fail("repeat key"), wire=wire) == result
    assert calls == ["key", "wire"]
    assert b"Private not retained" not in b"".join(
        p.read_bytes() for p in qa.LEDGER.iterdir() if p.is_file()
    )


@pytest.mark.parametrize(
    "bad",
    [
        "parent-raw",
        "parent-result",
        "parent-reject",
        "proof",
        "waiver",
        "expires",
        "naive",
        "bool-calls",
        "profile",
        "source",
        "missing-summary",
        "unknown-prior",
        "eight",
        "budget",
    ],
)
def test_tamper_unknown_history_and_expiry_refuse_before_key(qa: Any, bad: str) -> None:
    approve(qa)
    if bad.startswith("parent-"):
        suffix = {
            "parent-raw": "public-final.txt",
            "parent-result": "result.json",
            "parent-reject": "semantic-reject.json",
        }[bad]
        (qa.LEDGER / f"{qa.PARENT}.{suffix}").write_text('{"tampered":true}')
    elif bad == "proof":
        qa.MISSING_PROOF.write_text("{}")
    elif bad in ("waiver", "expires", "naive", "bool-calls"):
        path = qa.PACKAGE / "owner-continuation.json"
        value = json.loads(path.read_bytes())
        if bad == "waiver":
            value["parent_hashes"] = {}
        if bad == "expires":
            value["expires_at"] = "2000-01-01T00:00:00Z"
        if bad == "naive":
            value["expires_at"] = "2099-01-01T00:00:00"
        if bad == "bool-calls":
            value["max_calls"] = True
        path.write_bytes(qa.old.canonical(value))
    elif bad == "profile":
        (qa.PACKAGE / "request.json").write_text("{}")
    elif bad == "source":
        (qa.SOURCE / "reference-context.json").write_text("{}")
    elif bad == "missing-summary":
        (qa.SOURCE / "data/summary.json").unlink()
    else:
        for i in range(7 if bad == "eight" else 1):
            (qa.LEDGER / f"other-{i}.reservation.json").write_bytes(
                qa.old.canonical(
                    {
                        "case": f"other-{i}",
                        "reserve_microunits": 8_000_000
                        if bad == "budget"
                        else 1_000_000,
                    }
                )
            )
    with pytest.raises((qa.old.Refused, ValueError, OSError)):
        qa.execute(
            credential=lambda: pytest.fail("key"), wire=lambda *_: pytest.fail("wire")
        )
    assert not qa.reservation_path().exists()


def test_key_callback_source_drift_stops_without_post_and_keeps_reserve(
    qa: Any,
) -> None:
    approve(qa)

    def key() -> str:
        with sqlite3.connect(qa.SOURCE / "state.sqlite3") as c:
            c.execute("UPDATE current_content_summaries SET updated_at='changed'")
        return "synthetic-secret"

    result = qa.execute(credential=key, wire=lambda *_: pytest.fail("wire"))
    assert result["status"] == "PRE_SEND_STOP" and not result["send_attempted"]
    assert qa.reservation_path().exists()


@pytest.mark.parametrize(
    "bad",
    [
        "wrong-model",
        "length",
        "over5888",
        "secret-final",
        "secret-reasoning",
        "secret-metadata",
        "thought",
        "http429",
        "timeout",
    ],
)
def test_failed_new_result_stops_without_public_or_private_leak(
    qa: Any, bad: str
) -> None:
    approve(qa)
    secret = "synthetic-secret"

    def wire(_body: bytes, _secret: str) -> tuple[int, bytes]:
        if bad == "timeout":
            raise TimeoutError(secret)
        value = json.loads(envelope(qa))
        if bad == "wrong-model":
            value["model"] = "other-model"
        if bad == "length":
            value["choices"][0]["finish_reason"] = "length"
        if bad == "over5888":
            value["usage"] = {
                "prompt_tokens": 1,
                "completion_tokens": 5889,
                "total_tokens": 5890,
            }
        if bad == "secret-final":
            value["choices"][0]["message"]["content"] = json.dumps({"x": secret})
        if bad == "secret-reasoning":
            value["choices"][0]["message"]["reasoning_content"] = "".join(
                "\\u%04x" % ord(x) for x in secret
            )
        if bad == "secret-metadata":
            value["usage"]["untrusted"] = secret
        if bad == "thought":
            value["choices"][0]["message"]["content"] = '{"x":"<think>hidden</think>"}'
        return (429 if bad == "http429" else 200), qa.old.canonical(value)

    result = qa.execute(credential=lambda: secret, wire=wire)
    assert result["status"].endswith("_STOP") and not qa.final_path().exists()
    assert result["actual_bill"] == "UNKNOWN"
    assert (
        secret not in qa.result_path().read_text()
        and "Private not retained" not in qa.result_path().read_text()
    )
    assert (
        qa.execute(
            credential=lambda: pytest.fail("replay"),
            wire=lambda *_: pytest.fail("replay"),
        )
        == result
    )
    if bad.startswith("secret"):
        assert (
            not {"usage", "actual_model", "finish_reason", "response_body_sha256"}
            & result.keys()
        )


def test_concurrent_and_interrupted_reservation_cannot_replay(qa: Any) -> None:
    approve(qa)
    calls = []

    def wire(_body: bytes, _key: str) -> tuple[int, bytes]:
        calls.append(1)
        return 200, envelope(qa)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: qa.execute(
                    credential=lambda: "unique-fake-key-98471", wire=wire
                ),
                range(2),
            )
        )
    assert results[0] == results[1] and len(calls) == 1
    qa.result_path().unlink()
    qa.final_path().unlink()
    recovered = qa.execute(credential=lambda: pytest.fail("replay"), wire=wire)
    assert recovered["status"] == "RESERVED_UNKNOWN_STOP" and len(calls) == 1
    assert json.loads(qa.result_path().read_bytes()) == recovered


@pytest.mark.parametrize("completion", [5888, 5889])
def test_fixed_new_completion_bound_is_stricter_without_mutating_old_helper(
    qa: Any, completion: int
) -> None:
    frozen = approve(qa)
    value = json.loads(envelope(qa))
    value["usage"] = {
        "prompt_tokens": 12,
        "completion_tokens": completion,
        "total_tokens": 12 + completion,
    }
    body = qa.old.canonical(value)
    assert qa.old.MAX_OUTPUT == qa.old.PROFILE["max_completion_tokens"] == 6144
    # Existing decoder accepts this under its own unchanged 6144 limit.
    assert (
        qa.old.decoded(body, "unique-fake-key-98471", frozen)[1]["completion_tokens"]
        == completion
    )
    if completion == 5888:
        assert (
            qa.decoded(body, "unique-fake-key-98471", frozen)[1]["completion_tokens"]
            == completion
        )
    else:
        with pytest.raises(qa.old.ObservedOutputRejected) as rejected:
            qa.decoded(body, "unique-fake-key-98471", frozen)
        assert rejected.value.observation["failure_reason"] == "USAGE_OUT_OF_BOUND"
        assert rejected.value.observation["usage"]["completion_tokens"] == 5889
    assert qa.old.MAX_OUTPUT == qa.old.PROFILE["max_completion_tokens"] == 6144


def add_passed_prior(qa: Any, case: str) -> None:
    raw = b'{"other_synthetic_public_final":true}'
    values = {
        "reservation.json": {"case": case, "reserve_microunits": 1_000_000},
        "result.json": {
            "status": "PUBLIC_FINAL_REVIEW_ONLY",
            "public_final_sha256": qa.old.sha(raw),
        },
        "semantic-pass.json": {
            "decision": "PASS",
            "reviewer": "Root",
            "public_final_sha256": qa.old.sha(raw),
        },
    }
    for suffix, value in values.items():
        (qa.LEDGER / f"{case}.{suffix}").write_bytes(qa.old.canonical(value))
    (qa.LEDGER / f"{case}.public-final.txt").write_bytes(raw)


def test_seven_total_prior_pass_controls_leave_only_one_generation_slot(
    qa: Any,
) -> None:
    for i in range(6):
        add_passed_prior(qa, f"passed-{i}")
    frozen = approve(qa)
    assert len(frozen["prior_reservations"]) == 7
    assert (
        sum(row["reserve_microunits"] for row in frozen["prior_reservations"])
        == 6_952_118
    )
    assert qa.validated()[0] == frozen
    add_passed_prior(qa, "passed-seventh")
    with pytest.raises(qa.old.Refused):
        qa.execute(
            credential=lambda: pytest.fail("ninth call"),
            wire=lambda *_: pytest.fail("wire"),
        )
    assert not qa.reservation_path().exists()


@pytest.mark.parametrize(
    "change",
    [
        "pointer",
        "cue",
        "binding",
        "canonical",
        "canonical-root",
        "code",
        "false-parent-pass",
    ],
)
def test_live_readonly_authority_and_code_drift_are_refused(
    qa: Any, change: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    approve(qa)
    if change in ("pointer", "cue", "binding", "canonical-root"):
        with sqlite3.connect(qa.SOURCE / "state.sqlite3") as connection:
            if change == "pointer":
                connection.execute(
                    "UPDATE current_content_summaries SET updated_at='changed'"
                )
            elif change == "cue":
                connection.execute(
                    "UPDATE timed_transcript_cues SET cue_text='changed'"
                )
            elif change == "binding":
                connection.execute(
                    "UPDATE evidence_text_bindings SET excerpt='changed' WHERE evidence_id='old-id'"
                )
            else:
                connection.execute(
                    "UPDATE artifacts SET storage_root='VAULT' WHERE artifact_id='canonical'"
                )
    elif change == "canonical":
        (qa.SOURCE / "data/canonical.txt").write_text("changed")
    elif change == "code":
        original = qa.code_hashes
        monkeypatch.setattr(
            qa, "code_hashes", lambda: {**original(), "new-changed-helper.py": "f" * 64}
        )
    else:
        (qa.LEDGER / f"{qa.PARENT}.semantic-pass.json").write_text(
            '{"decision":"PASS"}'
        )
    with pytest.raises((ValueError, qa.old.Refused)):
        qa.execute(
            credential=lambda: pytest.fail("key"), wire=lambda *_: pytest.fail("wire")
        )
    assert not qa.reservation_path().exists()


def test_expiry_during_key_callback_stops_and_no_key_missing_replay(qa: Any) -> None:
    approve(qa)

    def key() -> str:
        qa.datetime.current += timedelta(minutes=11)
        return "unique-fake-key-98471"

    result = qa.execute(credential=key, wire=lambda *_: pytest.fail("expired wire"))
    assert result["status"] == "PRE_SEND_STOP" and result["send_attempted"] is False
    assert qa.execute(credential=lambda: pytest.fail("key replay")) == result


def test_missing_key_is_terminal_reserve_held_not_a_renewed_consent(qa: Any) -> None:
    approve(qa)
    result = qa.execute(credential=lambda: None, wire=lambda *_: pytest.fail("wire"))
    assert result["status"] == "PRE_SEND_STOP" and qa.reservation_path().exists()
    assert qa.execute(credential=lambda: pytest.fail("key replay")) == result


@pytest.mark.parametrize("size", [25000, 40000])
def test_wire_size_or_reserve_excess_refuses_without_truncation(
    qa: Any, size: int
) -> None:
    path = qa.SOURCE / "request-body.json"
    value = json.loads(path.read_bytes())
    value["messages"][0]["content"] = "x" * size
    path.write_bytes(qa.old.canonical(value))
    qa.SOURCE_HASHES[path.name] = qa.old.sha(path.read_bytes())
    with pytest.raises(qa.old.Refused):
        qa.prepare()
    assert not qa.PACKAGE.exists() and not qa.reservation_path().exists()


def test_shared_http_and_qa_namespace_are_reused_not_reconfigured(qa: Any) -> None:
    import inspect

    assert inspect.signature(qa.execute).parameters["wire"].default is qa.old.http_wire
    assert (
        qa.old.QACredentialStore._service
        == b"com.huangbuqubunao.intelligence.qa.kimi-public-20261029"
    )
    assert qa.old.QACredentialStore._account == b"api-key"
    assert qa.old.PROFILE["deadline_seconds"] == 300 and qa.old.PROFILE["retries"] == 0
    assert qa.old.MAX_BODY == 2 * 1024 * 1024
    assert (
        qa.old.LEDGER != qa.LEDGER
    )  # fake fixture changes only the new wrapper's local path
