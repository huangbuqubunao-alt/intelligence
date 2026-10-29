"""One fixed Summary-aware QA continuation; not a runtime/provider or permit.

Root alone may prepare the real package, review it and record NEW owner consent.
The known parent's REJECT/reserve stays untouched. No automatic next case/retry.
"""

from __future__ import annotations

import fcntl
import importlib.util
import os
import re
import sqlite3
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from youtube_intel import summary_baseline as baseline
from youtube_intel.domain import AnalysisResult
from youtube_intel.source_authority import read_managed
from youtube_intel.state import SQLiteStateRepository

_helper = Path(__file__).resolve().with_name("kimi_public_diagnostic.py")
_spec = importlib.util.spec_from_file_location(
    "_accepted_kimi_diagnostic_helpers", _helper
)
assert _spec is not None and _spec.loader is not None
old: Any = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(old)  # definitions only; never old prepare/execute

ROOT: Path = old.ROOT
SOURCE: Path = old.SOURCE
LEDGER: Path = old.LEDGER  # fixed outside Restore and copied worktree/package
PACKAGE = (
    Path(__file__).resolve().parents[2] / ".var/kimi-summary-aware-diagnostic/package"
)
SOURCE_HASHES = dict(old.SOURCE_HASHES)
DOCS, DOC_HASHES = dict(old.DOCS), dict(old.DOC_HASHES)
DATE, MODEL, VIDEO = "2026-10-29", "kimi-k3.1-pro", "aircAruvnKk"
PARENT = "public-aircAruvnKk-zh-kimi-k3.1-pro"
CASE = "public-aircAruvnKk-zh-kimi-k3.1-pro-summary-aware-1"
MAX_OUTPUT = 5888
PROFILE = {
    **old.PROFILE,
    "id": "qa-kimi-k31-summary-aware-bound-reference-20261029",
    "max_completion_tokens": MAX_OUTPUT,
}
QACredentialStore = old.QACredentialStore
MISSING_PROOF = (
    ROOT
    / "docs/validation/end-to-end-user-readiness/SUMMARY_BASELINE_MISSING_INPUT_PROOF_2026_10_29.json"
)
MISSING_PROOF_SHA = "baa9f16f3eec73600f82b12cba20c3de79fc403bc990e98834b99ef8dbeddfdc"
PARENT_HASHES = {
    "reservation.json": "5eb8fa2aa42851afa778aa7983294e2e7e6cd4788ed1ebb188b32ec1372586de",
    "result.json": "12d8b78bd554e97c43037fdd7f40382976c0da7cab8a6b6599ca5a8fbcb0f860",
    "public-final.txt": "5a14748751402859b84034873b6b36937e9dc6984930c1ce979c22e81ddfd434",
    "semantic-reject.json": "14618db5ea73b9488d154bc62e6df9ab752bb49cb13f9e111f9ba4cb2f8467a3",
}
_CAPTURE_KEYS = (
    "video_id",
    "evidence_id",
    "excerpt",
    "excerpt_hash",
    "start_ms",
    "end_ms",
    "timed_transcript_id",
    "timed_transcript_hash",
)


def code_hashes() -> dict[str, str]:
    project = Path(__file__).resolve().parents[2]
    paths = [
        Path(__file__).resolve(),
        _helper,
        *sorted((project / "src").rglob("*.py")),
    ]
    hashes = {str(path.relative_to(project)): old.sha(old.read(path)) for path in paths}
    # Freeze bytes actually imported, not just a neighboring candidate directory.
    for name, module in list(sys.modules.items()):
        if name == "youtube_intel" or name.startswith("youtube_intel."):
            path = getattr(module, "__file__", None)
            if path and str(path).endswith(".py"):
                relative = Path(path).relative_to(
                    Path(baseline.__file__).resolve().parents[1]
                )
                old.require(
                    hashes.get("src/" + str(relative)) == old.sha(old.read(Path(path)))
                )
    return hashes


def summary_snapshot(
    verified: dict[str, Any],
) -> tuple[baseline.SummaryBaseline, dict[str, bytes]]:
    """Single SQLite read snapshot, mature cue/Evidence validators, safe DATA read."""
    db, data = SOURCE / "state.sqlite3", SOURCE / "data"
    old.require(
        not db.is_symlink() and not data.is_symlink() and verified["video_id"] == VIDEO
    )
    repository = SQLiteStateRepository(db)
    repository.bind_source_storage(data)
    connection = sqlite3.connect(
        db.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None
    )
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        old.require(15 <= version <= 43)
        video = connection.execute(
            "SELECT provider FROM videos WHERE video_id=?", (VIDEO,)
        ).fetchone()
        old.require(video is not None and video[0] == "YOUTUBE")
        timed = repository._get_verified_timed_transcript_in_transaction(
            connection, VIDEO
        )
        old.require(timed is not None)
        assert timed is not None
        canonical = connection.execute(
            "SELECT * FROM artifacts WHERE artifact_id=?",
            (timed.canonical_artifact_id,),
        ).fetchone()
        old.require(canonical is not None and canonical["storage_root"] == "DATA")
        canonical_raw = read_managed(
            data, canonical["relative_path"], maximum=old.MAX_BODY
        )
        old.require(old.sha(canonical_raw) == canonical["content_hash"])

        def capture(identity: str) -> dict[str, Any]:
            item = repository._resolve_verified_evidence_text_in_transaction(
                connection, identity
            )
            old.require(item is not None)
            assert item is not None
            old.require(
                item.video_id == VIDEO
                and item.timed_transcript_id == timed.timed_transcript_id
                and item.timed_transcript_hash == timed.timed_transcript_hash
                and item.locator_type == "TIMED_MEDIA"
            )
            return asdict(item)

        refs = []
        for i, evidence in enumerate(
            sorted(
                verified["evidence"],
                key=lambda e: (e["start_ms"], e["end_ms"], e["evidence_id"]),
            )
        ):
            live = capture(evidence["evidence_id"])
            old.require(
                all(
                    key in live and live[key] == value
                    for key, value in evidence.items()
                )
            )
            refs.append(
                {"ref": f"E{i + 1:02d}", **{key: live[key] for key in _CAPTURE_KEYS}}
            )
        row = connection.execute(
            "SELECT * FROM current_content_summaries WHERE video_id=?", (VIDEO,)
        ).fetchone()
        old.require(row is not None)
        pointer = dict(row)
        row = connection.execute(
            "SELECT * FROM artifacts WHERE artifact_id=?",
            (pointer["analysis_artifact_id"],),
        ).fetchone()
        old.require(row is not None)
        artifact = dict(row)
        raw = read_managed(data, artifact["relative_path"], maximum=128000)
        result = AnalysisResult.model_validate_json(raw, strict=True)
        bindings = [
            {key: item[key] for key in _CAPTURE_KEYS}
            for item in (capture(e.evidence_id) for e in result.evidence)
        ]
        context = baseline.build_summary_baseline(
            expected_video_id=VIDEO,
            current_pointer=pointer,
            artifact=artifact,
            raw_summary=raw,
            source_refs=refs,
            summary_evidence=bindings,
        )
        capture_proof = {
            "schema_version": version,
            "timed_transcript_id": timed.timed_transcript_id,
            "timed_transcript_hash": timed.timed_transcript_hash,
            "canonical_sha256": old.sha(canonical_raw),
            "pointer": pointer,
            "artifact": artifact,
            "source_refs": refs,
            "summary_evidence": bindings,
        }
        return context, {
            "summary-raw.json": raw,
            "summary-context.json": context.projection_json.encode(),
            "summary-capture.json": old.canonical(capture_proof),
        }
    finally:
        connection.rollback()
        connection.close()


def history() -> list[dict[str, Any]]:
    """Known rejected parent is a narrowly bound exception, never a fake PASS."""
    old.require(old.sha(old.read(MISSING_PROOF)) == MISSING_PROOF_SHA)
    proof = old.parse(old.read(MISSING_PROOF))
    old.require(
        proof["model_request_missing_baseline"] is True
        and proof["old_result_preserved"] is True
    )
    for suffix, expected in PARENT_HASHES.items():
        old.require(old.sha(old.read(LEDGER / f"{PARENT}.{suffix}")) == expected)
    parent = old.parse(old.read(LEDGER / f"{PARENT}.result.json"))
    old.require(
        parent["case"] == PARENT
        and parent["status"] == "PUBLIC_FINAL_REVIEW_ONLY"
        and parent["http_status"] == 200
        and parent["actual_model"] == MODEL
        and parent["finish_reason"] == "stop"
        and parent["public_final_sha256"] == PARENT_HASHES["public-final.txt"]
        and not (LEDGER / f"{PARENT}.semantic-pass.json").exists()
    )
    result = []
    for path in sorted(LEDGER.glob("*.reservation.json")):
        if path == reservation_path():
            continue
        raw = old.read(path)
        value = old.parse(raw)
        case, cost = value["case"], value["reserve_microunits"]
        old.require(
            isinstance(case, str)
            and re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", case)
            and path.name == f"{case}.reservation.json"
            and type(cost) is int
            and 0 < cost <= 1_000_000
        )
        hashes = {"reservation": old.sha(raw)}
        if case == PARENT:
            old.require(cost == 952118)
        else:
            finished = old.parse(old.read(LEDGER / f"{case}.result.json"))
            semantic = old.parse(old.read(LEDGER / f"{case}.semantic-pass.json"))
            old.require(
                finished["status"] == "PUBLIC_FINAL_REVIEW_ONLY"
                and semantic
                == {
                    "decision": "PASS",
                    "reviewer": "Root",
                    "public_final_sha256": finished["public_final_sha256"],
                }
            )
            for suffix in ("result.json", "semantic-pass.json", "public-final.txt"):
                hashes[suffix] = old.sha(old.read(LEDGER / f"{case}.{suffix}"))
            old.require(hashes["public-final.txt"] == finished["public_final_sha256"])
        result.append({"case": case, "reserve_microunits": cost, "hashes": hashes})
    old.require(sum(row["case"] == PARENT for row in result) == 1 and len(result) < 8)
    return result


def snapshot() -> tuple[dict[str, bytes], dict[str, Any], bytes]:
    old.require(
        datetime.now(UTC).date().isoformat() == DATE
        and MAX_OUTPUT == 5888
        and PROFILE["max_completion_tokens"] == 5888
        and PROFILE["model"] == MODEL
    )
    files = {name: old.read(SOURCE / name) for name in SOURCE_HASHES}
    old.require({name: old.sha(raw) for name, raw in files.items()} == SOURCE_HASHES)
    docs = {name: old.read(path) for name, path in DOCS.items()}
    old.require({name: old.sha(raw) for name, raw in docs.items()} == DOC_HASHES)
    original = old.parse(files["request-body.json"])["messages"]
    old.require(len(original) == 3)
    verified = old.parse(files["verified-input.json"])
    context, capture = summary_snapshot(verified)
    source_refs = old.parse(capture["summary-capture.json"])["source_refs"]
    messages = baseline.summary_baseline_prompt_messages(
        original, context, source_refs=source_refs
    )
    body = old.canonical(
        {
            "model": MODEL,
            "messages": messages,
            **{
                key: PROFILE[key]
                for key in (
                    "reasoning_effort",
                    "max_completion_tokens",
                    "stream",
                    "response_format",
                    "prompt_cache_options",
                )
            },
        }
    )
    input_bound = sum(len(message["content"].encode()) for message in messages) + 2048
    reserve = input_bound * 26 + MAX_OUTPUT * 68
    prior = history()
    old.require(
        len(body) <= 32768
        and reserve <= 1_000_000
        and sum(row["reserve_microunits"] for row in prior) + reserve <= 8_000_000
    )
    files.update(docs)
    files.update(capture)
    frozen = {
        "case": CASE,
        "date": DATE,
        "profile": PROFILE,
        "source": SOURCE_HASHES,
        "official_documents": DOC_HASHES,
        "code": code_hashes(),
        "parent_case": PARENT,
        "parent_hashes": PARENT_HASHES,
        "missing_baseline_proof_sha256": MISSING_PROOF_SHA,
        "prior_reservations": prior,
        "summary_context_sha256": context.context_sha256,
        "capture_files": {name: old.sha(raw) for name, raw in capture.items()},
        "wire_sha256": old.sha(body),
        "input_token_bound_assumption": input_bound,
        "reserve_microunits": reserve,
        "origin_sha256": old.sha(
            old.canonical(
                {
                    "profile": PROFILE,
                    "wire_sha256": old.sha(body),
                    "full_summary_context": old.parse(context.projection_json),
                }
            )
        ),
    }
    frozen["prepared_sha256"] = old.sha(old.canonical(frozen))
    return files, frozen, body


def prepare() -> dict[str, Any]:
    files, frozen, body = snapshot()
    PACKAGE.mkdir(parents=True, exist_ok=True, mode=0o700)
    old.require(not PACKAGE.is_symlink())
    for name, raw in {
        **files,
        "prepared.json": old.canonical(frozen),
        "request.json": body,
    }.items():
        path = PACKAGE / name
        if path.exists():
            old.require(old.read(path) == raw)
        else:
            old.write_once(path, raw)
    return frozen


def _unexpired(receipt: dict[str, Any]) -> None:
    try:
        expires = datetime.fromisoformat(receipt["expires_at"])
        old.require(expires.utcoffset() is not None and datetime.now(UTC) < expires)
    except (ValueError, TypeError):
        raise old.Refused() from None


def validated() -> tuple[dict[str, Any], bytes]:
    files, frozen, body = snapshot()
    old.require(
        old.read(PACKAGE / "prepared.json") == old.canonical(frozen)
        and old.read(PACKAGE / "request.json") == body
    )
    for name, raw in files.items():
        old.require(old.read(PACKAGE / name) == raw)
    review = old.parse(old.read(PACKAGE / "review.json"))
    old.require(
        set(review)
        == {
            "decision",
            "reviewer",
            "prepared_sha256",
            "review_commit",
            "max_calls",
            "expires_at",
        }
        and review["decision"] == "APPROVE"
        and review["reviewer"] == "Root"
        and review["prepared_sha256"] == frozen["prepared_sha256"]
        and type(review["max_calls"]) is int
        and review["max_calls"] == 1
        and re.fullmatch("[0-9a-f]{40}", review["review_commit"])
    )
    _unexpired(review)
    receipt = old.parse(old.read(PACKAGE / "owner-continuation.json"))
    expected = {
        "decision": "AUTHORIZE_MISSING_SUMMARY_CONTINUATION",
        "owner": "USER",
        "case": CASE,
        "prepared_sha256": frozen["prepared_sha256"],
        "profile_id": PROFILE["id"],
        "review_commit": review["review_commit"],
        "parent_case": PARENT,
        "parent_hashes": PARENT_HASHES,
        "missing_baseline_proof_sha256": MISSING_PROOF_SHA,
        "max_calls": 1,
        "max_reserve_microunits": 1_000_000,
        "total_authorized_microunits": 8_000_000,
    }
    old.require(
        set(receipt) == set(expected) | {"user_decision_reference", "expires_at"}
        and all(receipt[key] == value for key, value in expected.items())
        and all(
            type(receipt[key]) is int
            for key in (
                "max_calls",
                "max_reserve_microunits",
                "total_authorized_microunits",
            )
        )
        and isinstance(receipt["user_decision_reference"], str)
        and 1 <= len(receipt["user_decision_reference"].strip()) <= 1000
    )
    _unexpired(receipt)
    return frozen, body


def reservation_path() -> Path:
    return LEDGER / f"{CASE}.reservation.json"


def result_path() -> Path:
    return LEDGER / f"{CASE}.result.json"


def final_path() -> Path:
    return LEDGER / f"{CASE}.public-final.txt"


@contextmanager
def locked() -> Iterator[None]:
    # Same outside-Restore ledger and lock filename as accepted helper. No old
    # module constants are reassigned to route this function or the HTTP helper.
    old.require(LEDGER.is_dir() and not LEDGER.is_symlink())
    descriptor = os.open(LEDGER / "lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def decoded(
    body: bytes, secret: str, frozen: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    raw, usage = old.decoded(body, secret, frozen)
    if usage["completion_tokens"] > MAX_OUTPUT:
        observation = old.safe_observation(
            old.parse(body)
        )  # old full secret guard already passed
        raise old.ObservedOutputRejected(
            {**observation, "failure_reason": "USAGE_OUT_OF_BOUND"}
        )
    return raw, usage


def execute(
    *,
    credential: Callable[[], str | None] | None = None,
    wire: Callable[[bytes, str], tuple[int, bytes]] = old.http_wire,
) -> dict[str, Any]:
    with locked():
        if reservation_path().exists():
            if result_path().exists():
                return dict(old.parse(old.read(result_path())))
            recovered = {
                "case": CASE,
                "status": "RESERVED_UNKNOWN_STOP",
                "actual_bill": "UNKNOWN",
            }
            old.write_once(result_path(), old.canonical(recovered))
            return recovered
        frozen, body = (
            validated()
        )  # fresh review AND new explicit owner receipt before reserve/key
        reservation = old.canonical(
            {
                "case": CASE,
                "model": MODEL,
                "prepared_sha256": frozen["prepared_sha256"],
                "reserve_microunits": frozen["reserve_microunits"],
                "prior_reserved_microunits": sum(
                    row["reserve_microunits"] for row in frozen["prior_reservations"]
                ),
                "created_at": datetime.now(UTC).isoformat(),
                "bill": "UNKNOWN",
                "replay": "FORBIDDEN",
            }
        )
        old.write_once(
            reservation_path(), reservation
        )  # O_EXCL + file/directory fsync BEFORE key
        result = {
            "case": CASE,
            "model": MODEL,
            "status": "UNKNOWN_STOP",
            "actual_bill": "UNKNOWN",
            "reserve_microunits": frozen["reserve_microunits"],
            "send_attempted": False,
        }
        try:
            validated()
            old.require(old.read(reservation_path()) == reservation)
            secret = (credential or QACredentialStore().get)()
            old.require(
                isinstance(secret, str)
                and secret
                and "\r" not in secret
                and "\n" not in secret
            )
            assert isinstance(secret, str)
            validated()
            old.require(old.read(reservation_path()) == reservation)
            result["send_attempted"] = True
            status, response = wire(body, secret)
            old.require(
                type(status) is int
                and 100 <= status <= 599
                and len(response) <= old.MAX_BODY
            )
            envelope = old.parse(response)
            old.require(all(secret not in text for text in old.strings(envelope)))
            result.update(http_status=status, response_body_sha256=old.sha(response))
            if status != 200:
                result["status"] = "HTTP_ERROR_STOP"
            else:
                raw, usage = decoded(response, secret, frozen)
                old.write_once(final_path(), raw.encode())
                result.update(
                    status="PUBLIC_FINAL_REVIEW_ONLY",
                    public_final_sha256=old.sha(raw.encode()),
                    actual_model=MODEL,
                    finish_reason="stop",
                    usage=usage,
                    semantic="NOT_REVIEWED",
                )
        except old.ObservedOutputRejected as error:
            result.update(error.observation, status="OUTPUT_REJECTED_STOP")
        except Exception:
            result["status"] = (
                "UNKNOWN_STOP" if result["send_attempted"] else "PRE_SEND_STOP"
            )
        old.write_once(result_path(), old.canonical(result))
        return result


def main() -> int:
    try:
        old.require(len(sys.argv) == 2 and sys.argv[1] in {"prepare", "execute"})
        value = prepare() if sys.argv[1] == "prepare" else execute()
        print(
            old.canonical(
                {
                    key: value[key]
                    for key in ("case", "status", "prepared_sha256")
                    if key in value
                }
            ).decode()
        )
        return 0
    except Exception:
        print(
            "Summary-aware diagnostic refused; preserve package and external ledger",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
