"""Schema44 sidecars around existing distillation; no dispatch/quality authority."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from . import summary_baseline as baseline
from . import system_synthesis as synthesis
from . import system_synthesis_profile as profile
from .domain import AnalysisResult
from .source_authority import read_managed
from .source_policy import SourcePolicyApplicationService
from .state import (
    SQLiteStateRepository,
    StateStoreError,
    _immediate_transaction,
    _read_snapshot,
    format_utc_datetime,
)

canonical = profile.canonical
sha = profile.sha
PREFIX = "distillation:system-synthesis-v1:"
TABLE = "system_synthesis_wait_cancellations"
PROOFS = "system_synthesis_input_proofs"
AUTHORIZATIONS = "system_synthesis_cloud_authorizations"
RECEIPTS = "system_synthesis_result_receipts"
TABLES = (PROOFS, AUTHORIZATIONS, RECEIPTS, TABLE)
OUTCOME = "CANCELLED_BEFORE_CLOUD_MODEL_INVOCATION"
BINDINGS = (
    "execution_id",
    "source_id",
    "video_id",
    "reason",
    "use_case",
    "selected_provider",
    "selected_model",
    "output_language",
    "budget_state",
)
_CAPTURE = (
    "video_id",
    "evidence_id",
    "excerpt",
    "excerpt_hash",
    "start_ms",
    "end_ms",
    "timed_transcript_id",
    "timed_transcript_hash",
)
_SEAL = object()


def loads(text: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in items:
            if k in result:
                raise ValueError("Duplicate synthesis proof field")
            result[k] = v
        return result

    value = json.loads(text, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError("Synthesis proof must be an object")
    canonical(value)
    return value


def is_synthesis(execution_id: str) -> bool:
    return execution_id.casefold().startswith("distillation:system-synthesis-")


def owns(checkpoint: sqlite3.Row) -> bool:
    return (
        is_synthesis(str(checkpoint["execution_id"]))
        or (checkpoint["selected_provider"], checkpoint["selected_model"]) == profile.PAIR
    )


def _row(c: sqlite3.Connection, table: str, key: str, identity: str) -> dict[str, Any]:
    # Only application literals are used for table/key.
    row = c.execute(f"SELECT * FROM {table} WHERE {key}=?", (identity,)).fetchone()
    if row is None:
        raise StateStoreError("Synthesis source/proof record is missing")
    return dict(row)


def _file(repo: SQLiteStateRepository, artifact: dict[str, Any]) -> str:
    if repo._source_data_root is None or artifact["storage_root"] != "DATA" or artifact["deleted_at"] is not None:
        raise StateStoreError("Synthesis source file unavailable")
    raw = read_managed(repo._source_data_root, artifact["relative_path"], maximum=128000)
    text = raw.decode("utf-8")
    if sha(text) != artifact["content_hash"]:
        raise StateStoreError("Synthesis source bytes changed")
    return text


def _capture(repo: SQLiteStateRepository, c: sqlite3.Connection, video: str, identity: str) -> dict[str, Any]:
    item = repo._resolve_verified_evidence_text_in_transaction(c, identity)
    if item is None or item.video_id != video or item.locator_type != "TIMED_MEDIA":
        raise StateStoreError("Synthesis Evidence authority unavailable")
    return {k: getattr(item, k) for k in _CAPTURE}


@dataclass(frozen=True, slots=True)
class PreparedSynthesis:
    execution_id: str
    proof_json: str
    proof_sha256: str


@dataclass(frozen=True, slots=True)
class SynthesisBudget:
    """Trusted backend policy input ONLY; never bind these values from an API body.

    Construction records an explicit bounded owner decision, not eligibility.
    Production composition must not construct a default policy.
    """

    scope: str
    limit_microunits: int
    max_calls: int
    prior_reserved_microunits: int = 0
    prior_calls: int = 0


@dataclass(frozen=True, slots=True)
class Completion:
    """Only authentic public-final text; invalid responses retain safe hash only."""

    raw_text: str | None = None
    raw_sha256: str | None = None


def _assemble(command: dict[str, Any], capture: dict[str, Any]) -> PreparedSynthesis:
    refs = capture["source_refs"]
    context = baseline.build_summary_baseline(
        expected_video_id=command["video_id"],
        current_pointer=capture["summary_pointer"],
        artifact=capture["summary_artifact"],
        raw_summary=capture["summary_raw"].encode(),
        source_refs=refs,
        summary_evidence=capture["summary_evidence"],
    )
    rows = capture["policy"]
    global_row = next(r for r in rows if r["policy_scope"] == "GLOBAL")
    source_row = next((r for r in rows if r["policy_scope"] == "SOURCE"), None)
    policy = SourcePolicyApplicationService._policy_from_revisions(
        SQLiteStateRepository._source_policy_revision_from_row(global_row),
        None if source_row is None else SQLiteStateRepository._source_policy_revision_from_row(source_row),
    )
    if (
        command["preference_ids"] != [r["preference_id"] for r in capture["preferences"]]
        or command["source_policy_revision_id"] != policy.source_policy_revision_id
    ):
        raise StateStoreError("Synthesis policy command differs")
    messages = [
        {"role": "system", "content": "Host system-analysis operation; replaced by the pure contract."},
        {
            "role": "system",
            "content": "TASK_AND_PERSONALIZATION="
            + canonical(
                {
                    "focus": policy.focus_rules,
                    "ignore": policy.ignore_rules,
                    "style": policy.distillation_style.value,
                    "personalization": [r["statement"] for r in capture["preferences"]],
                    "output_language": command["output_language"],
                }
            ),
        },
        {
            "role": "user",
            "content": "UNTRUSTED_SOURCE_EVIDENCE="
            + canonical(
                {
                    "video_id": command["video_id"],
                    "video_title": capture["video"]["title"],
                    "source_display_name": capture["source"]["display_name"] or capture["video"]["channel_name"],
                    "reference_protocol": "bound-evidence-reference-v1",
                    "evidence": [{k: r[k] for k in ("ref", "excerpt")} for r in refs],
                }
            ),
        },
    ]
    request = synthesis.build_system_synthesis_request(
        original_messages=messages,
        summary_baseline=context,
        source_refs=refs,
        output_language=command["output_language"],
    )
    descriptor = profile.resolve_profile(profile.PROFILE_ID)
    wire, reserve = profile.provider_wire(request)
    proof = {
        "command": command,
        "capture": capture,
        "transport": descriptor,
        "transport_sha256": sha(canonical(descriptor)),
        "request": loads(request.projection_json),
        "pure_wire": request.wire_json,
        "origin_sha256": request.origin_sha256,
        "provider_wire": wire,
        "wire_sha256": sha(wire),
        "reserve_microunits": reserve,
        "source_scope": "PUBLIC_YOUTUBE_TIMED_MEDIA",
    }
    encoded = canonical(proof)
    if len(encoded.encode()) > 524288:
        raise ValueError("Synthesis proof exceeds bound")
    digest = sha(encoded)
    return PreparedSynthesis(PREFIX + digest, encoded, digest)


def _prepare(
    repo: SQLiteStateRepository,
    c: sqlite3.Connection,
    *,
    source_id: str,
    video_id: str,
    command_id: str,
    output_language: str,
    now: datetime,
) -> PreparedSynthesis:
    if re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", command_id) is None or output_language not in {"en", "zh-CN"}:
        raise ValueError("Synthesis command invalid")
    source = _row(c, "source_subscriptions", "source_id", source_id)
    video = _row(c, "videos", "video_id", video_id)
    if (
        source["provider"] != "YOUTUBE"
        or video["provider"] != "YOUTUBE"
        or video["availability"] != "public"
        or c.execute(
            "SELECT 1 FROM source_video_links WHERE source_id=? AND video_id=?", (source_id, video_id)
        ).fetchone()
        is None
    ):
        raise StateStoreError("Synthesis first route only accepts linked public YouTube")
    ids = [
        r[0]
        for r in c.execute(
            "SELECT evidence_id FROM evidence WHERE video_id=? AND availability='AVAILABLE' AND lineage_kind='ORIGINAL_TRANSCRIPT' ORDER BY start_ms,end_ms,evidence_id LIMIT 21",
            (video_id,),
        )
    ]
    if not 1 <= len(ids) <= 20:
        raise StateStoreError("Complete synthesis Evidence set exceeds bounds")
    refs = [{"ref": f"E{i + 1:02d}", **_capture(repo, c, video_id, eid)} for i, eid in enumerate(ids)]
    pointer = _row(c, "current_content_summaries", "video_id", video_id)
    artifact = _row(c, "artifacts", "artifact_id", pointer["analysis_artifact_id"])
    raw = _file(repo, artifact)
    result = AnalysisResult.model_validate_json(raw, strict=True)
    policy = [
        dict(r)
        for r in c.execute(
            "SELECT r.* FROM source_policy_current p JOIN source_policy_revisions r USING(revision_id) WHERE p.policy_key IN ('GLOBAL',?) ORDER BY p.policy_key",
            ("SOURCE:" + source_id,),
        )
    ]
    preferences = [
        dict(r)
        for r in c.execute(
            "SELECT p.* FROM preferences p WHERE EXISTS(SELECT 1 FROM preference_state_events e WHERE e.preference_id=p.preference_id AND e.state='ACTIVATED') AND NOT EXISTS(SELECT 1 FROM preference_state_events e WHERE e.preference_id=p.preference_id AND e.state IN ('REPLACED','DELETED')) AND (p.horizon!='TEMPORARY_FOCUS' OR p.expires_at>?) ORDER BY p.created_at,p.preference_id",
            (format_utc_datetime(now),),
        )
    ]
    command = {
        "source_id": source_id,
        "video_id": video_id,
        "reason": "MANUAL_CONTENT:" + command_id,
        "use_case": "PERSONALIZED_INTELLIGENCE",
        "selected_provider": profile.PAIR[0],
        "selected_model": profile.PAIR[1],
        "output_language": output_language,
        "preference_ids": [r["preference_id"] for r in preferences],
        "source_policy_revision_id": next((r["revision_id"] for r in policy if r["policy_scope"] == "SOURCE"), None),
    }
    capture = {
        "source": source,
        "video": video,
        "source_refs": refs,
        "summary_pointer": pointer,
        "summary_artifact": artifact,
        "summary_raw": raw,
        "summary_evidence": [_capture(repo, c, video_id, e.evidence_id) for e in result.evidence],
        "policy": policy,
        "preferences": preferences,
    }
    return _assemble(command, capture)


def prepare(
    repo: SQLiteStateRepository, *, source_id: str, video_id: str, command_id: str, output_language: str, now: datetime
) -> PreparedSynthesis:
    with closing(repo._connect()) as c, _read_snapshot(c):
        return _prepare(
            repo,
            c,
            source_id=source_id,
            video_id=video_id,
            command_id=command_id,
            output_language=output_language,
            now=now,
        )


def request_from_proof(prepared: PreparedSynthesis) -> synthesis.SystemSynthesisRequest:
    p = loads(prepared.proof_json)
    r = p["request"]
    summary = baseline.SummaryBaseline(canonical(r["summary_context"]), r["summary_context_sha256"])
    request = synthesis.build_system_synthesis_request(
        original_messages=r["input_messages"],
        summary_baseline=summary,
        source_refs=r["source_refs"],
        output_language=r["output_language"],
    )
    if (
        loads(request.projection_json) != r
        or request.wire_json != p["pure_wire"]
        or request.origin_sha256 != p["origin_sha256"]
        or profile.provider_wire(request) != (p["provider_wire"], p["reserve_microunits"])
    ):
        raise StateStoreError("Full synthesis projection/wire/origin replay differs")
    return request


def _replay(repo: SQLiteStateRepository, c: sqlite3.Connection, row: dict[str, Any]) -> PreparedSynthesis:
    prepared = PreparedSynthesis(row["execution_id"], row["proof_json"], row["proof_sha256"])
    p = loads(prepared.proof_json)
    if (
        canonical(p) != prepared.proof_json
        or sha(prepared.proof_json) != prepared.proof_sha256
        or prepared.execution_id != PREFIX + prepared.proof_sha256
        or row["profile_id"] != profile.PROFILE_ID
        or _assemble(p["command"], p["capture"]) != prepared
    ):
        raise StateStoreError("Synthesis complete proof differs")
    request_from_proof(prepared)
    command, capture = p["command"], p["capture"]
    video = command["video_id"]
    source = command["source_id"]
    live_video = _row(c, "videos", "video_id", video)
    live_source = _row(c, "source_subscriptions", "source_id", source)
    if (
        live_video["provider"] != "YOUTUBE"
        or live_source["provider"] != "YOUTUBE"
        or c.execute("SELECT 1 FROM source_video_links WHERE source_id=? AND video_id=?", (source, video)).fetchone()
        is None
    ):
        raise StateStoreError("Synthesis source binding missing")
    if (
        _row(c, "artifacts", "artifact_id", capture["summary_artifact"]["artifact_id"]) != capture["summary_artifact"]
        or _file(repo, capture["summary_artifact"]) != capture["summary_raw"]
    ):
        raise StateStoreError("Synthesis historical Summary differs")
    for saved in capture["source_refs"] + capture["summary_evidence"]:
        live = _capture(repo, c, video, saved["evidence_id"])
        if any(saved[k] != live[k] for k in _CAPTURE):
            raise StateStoreError("Synthesis retained Evidence differs")
    for saved in capture["policy"]:
        if _row(c, "source_policy_revisions", "revision_id", saved["revision_id"]) != saved:
            raise StateStoreError("Synthesis retained policy differs")
    for saved in capture["preferences"]:
        if _row(c, "preferences", "preference_id", saved["preference_id"]) != saved:
            raise StateStoreError("Synthesis retained preference differs")
    return prepared


def reserve(repo: SQLiteStateRepository, prepared: PreparedSynthesis, *, now: datetime) -> None:
    with closing(repo._connect()) as c, _immediate_transaction(c):
        p = loads(prepared.proof_json)
        cmd = p["command"]
        current = _prepare(
            repo,
            c,
            source_id=cmd["source_id"],
            video_id=cmd["video_id"],
            command_id=cmd["reason"][15:],
            output_language=cmd["output_language"],
            now=now,
        )
        if current != prepared:
            raise StateStoreError("Synthesis prepared input changed before reservation")
        timestamp = format_utc_datetime(now)
        c.execute(
            f"INSERT INTO {PROOFS} VALUES (?,?,?,?,?)",
            (prepared.execution_id, profile.PROFILE_ID, prepared.proof_json, prepared.proof_sha256, timestamp),
        )
        repo._inject_failure("synthesis_after_proof")
        c.execute(
            "INSERT INTO distillation_execution_checkpoints (execution_id,source_id,video_id,reason,use_case,selected_provider,selected_model,output_language,status,budget_state,invocation_count,intelligence_id,revision_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,'PENDING','RESERVED_NOT_DISPATCHED',0,NULL,NULL,?,?)",
            (
                prepared.execution_id,
                *[
                    cmd[k]
                    for k in (
                        "source_id",
                        "video_id",
                        "reason",
                        "use_case",
                        "selected_provider",
                        "selected_model",
                        "output_language",
                    )
                ],
                timestamp,
                timestamp,
            ),
        )
        repo._inject_failure("synthesis_after_reservation")
        verify_execution(repo, c, prepared.execution_id)


def confirm_and_claim(
    repo: SQLiteStateRepository,
    prepared: PreparedSynthesis,
    *,
    budget: SynthesisBudget,
    consent_kind: str,
    now: datetime,
) -> None:
    if (
        type(budget) is not SynthesisBudget
        or not isinstance(budget.scope, str)
        or not budget.scope.strip()
        or len(budget.scope) > 160
        or any(
            type(v) is not int or v < minimum
            for v, minimum in (
                (budget.limit_microunits, 1),
                (budget.max_calls, 1),
                (budget.prior_reserved_microunits, 0),
                (budget.prior_calls, 0),
            )
        )
        or consent_kind not in {"USER_CONFIRMATION", "OWNER_QUALIFICATION"}
    ):
        raise ValueError("Explicit trusted bounded fee policy and affirmative consent required")
    with closing(repo._connect()) as c, _immediate_transaction(c):
        existing = verify_execution(repo, c, prepared.execution_id)
        p = loads(prepared.proof_json)
        cmd = p["command"]
        if (
            existing != prepared
            or _prepare(
                repo,
                c,
                source_id=cmd["source_id"],
                video_id=cmd["video_id"],
                command_id=cmd["reason"][15:],
                output_language=cmd["output_language"],
                now=now,
            )
            != prepared
        ):
            raise StateStoreError("Synthesis input changed before confirmation")
        checkpoint = _row(c, "distillation_execution_checkpoints", "execution_id", prepared.execution_id)
        if (
            checkpoint["status"] != "PENDING"
            or checkpoint["invocation_count"] != 0
            or checkpoint["budget_state"] != "RESERVED_NOT_DISPATCHED"
            or c.execute(f"SELECT 1 FROM {TABLE} WHERE execution_id=?", (prepared.execution_id,)).fetchone()
        ):
            raise StateStoreError("Synthesis reservation cannot be claimed")
        timestamp = format_utc_datetime(now)
        c.execute(
            f"INSERT INTO {AUTHORIZATIONS} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "synthesis-consent:" + prepared.proof_sha256,
                prepared.execution_id,
                *profile.PAIR,
                prepared.proof_sha256,
                consent_kind,
                "system-synthesis-disclosure-v1",
                "UNKNOWN",
                timestamp,
                budget.scope,
                budget.limit_microunits,
                budget.max_calls,
                p["reserve_microunits"],
                budget.prior_reserved_microunits,
                budget.prior_calls,
                p["transport_sha256"],
            ),
        )
        repo._inject_failure("synthesis_after_consent")
        if (
            c.execute(
                "UPDATE distillation_execution_checkpoints SET budget_state='DISPATCH_CLAIMED',invocation_count=1,updated_at=? WHERE execution_id=? AND status='PENDING' AND invocation_count=0",
                (timestamp, prepared.execution_id),
            ).rowcount
            != 1
        ):
            raise StateStoreError("Synthesis claim conflicts")
        repo._inject_failure("synthesis_after_claim")
        verify_execution(repo, c, prepared.execution_id)


def has_table(c: sqlite3.Connection) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone() is not None


def _observation(c: sqlite3.Connection, eid: str) -> dict[str, Any] | None:
    rows = []
    for table in (
        "distillation_resource_usage",
        "distillation_no_new_intelligence_results",
        "distillation_cloud_response_failures",
    ):
        row = c.execute(f"SELECT * FROM {table} WHERE execution_id=?", (eid,)).fetchone()
        if row is not None:
            rows.append({"table": table, "row": dict(row)})
    if len(rows) > 1:
        raise StateStoreError("Synthesis attempt has competing accounting")
    return rows[0] if rows else None


def _validate_receipt(
    repo: SQLiteStateRepository,
    c: sqlite3.Connection,
    prepared: PreparedSynthesis,
    checkpoint: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    observation = _observation(c, prepared.execution_id)
    if (
        receipt["proof_sha256"] != prepared.proof_sha256
        or observation is None
        or canonical(observation) != receipt["observation_json"]
        or receipt["created_at"] != checkpoint["updated_at"]
        or receipt["revision_id"] != checkpoint["revision_id"]
        or checkpoint["invocation_count"] != 1
    ):
        raise StateStoreError("Synthesis receipt/ledger identity differs")
    accounting = observation["row"]
    if observation["table"] == "distillation_resource_usage":
        if any(accounting[k] != checkpoint[k] for k in BINDINGS if k != "output_language") or any(
            accounting[k] != checkpoint[k] for k in ("status", "invocation_count", "intelligence_id", "revision_id")
        ):
            raise StateStoreError("Synthesis physical usage differs from checkpoint")
    if (
        accounting.get("actual_model") is not None
        and (accounting.get("actual_provider"), accounting["actual_model"]) != profile.PAIR
    ):
        raise StateStoreError("Synthesis actual response identity differs")
    if (
        accounting.get("actual_model") is None
        and observation["table"] != "distillation_cloud_response_failures"
        and checkpoint["status"] != "AMBIGUOUS"
    ):
        raise StateStoreError("Synthesis result lacks actual identity")
    if (
        observation["table"] != "distillation_cloud_response_failures"
        and accounting["created_at"] != checkpoint["updated_at"]
    ):
        raise StateStoreError("Synthesis accounting clock differs")
    raw = receipt["raw_text"]
    positive = checkpoint["status"] == "SUCCEEDED"
    zero = observation["table"] == "distillation_no_new_intelligence_results"
    if positive or zero:
        if not isinstance(raw, str) or sha(raw) != receipt["raw_sha256"]:
            raise StateStoreError("Synthesis authentic public final missing or changed")
        request = request_from_proof(prepared)
        decoded = synthesis.decode_system_synthesis(raw, request, request_origin_sha256=request.origin_sha256)
        candidate: dict[str, Any] = dict(decoded.candidate_projection())
        if decoded.no_new != zero:
            raise StateStoreError("Synthesis result branch differs")
        if zero:
            if sorted(e["evidence_id"] for e in candidate["evidence"]) != json.loads(
                observation["row"]["evidence_ids_json"]
            ):
                raise StateStoreError("Synthesis NO_NEW membership differs")
        else:
            revision = _row(c, "intelligence_revisions", "revision_id", checkpoint["revision_id"])
            card = _row(c, "distillation_cards", "revision_id", checkpoint["revision_id"])
            if (
                revision["claim_kind"] != "SYSTEM_INFERENCE"
                or revision["intelligence_id"] != checkpoint["intelligence_id"]
                or card["source_id"] != checkpoint["source_id"]
                or card["video_id"] != checkpoint["video_id"]
                or card["core_conclusion"] != candidate["core_conclusion"]
            ):
                raise StateStoreError("Synthesis domain card differs")
            for key in (
                "user_relevant_information",
                "important_new_information",
                "meaningful_details",
                "filtered_noise",
            ):
                if json.loads(card[key + "_json"]) != candidate[key]:
                    raise StateStoreError("Synthesis domain card fields differ")
            relations = [
                dict(r)
                for r in c.execute(
                    "SELECT evidence_id,stance FROM intelligence_revision_evidence WHERE revision_id=? ORDER BY evidence_id",
                    (checkpoint["revision_id"],),
                )
            ]
            if relations != sorted(
                [{k: e[k] for k in ("evidence_id", "stance")} for e in candidate["evidence"]],
                key=lambda e: e["evidence_id"],
            ):
                raise StateStoreError("Synthesis card Evidence differs")
            expected = {
                k: candidate[k]
                for k in (
                    "core_conclusion",
                    "user_relevant_information",
                    "important_new_information",
                    "meaningful_details",
                    "filtered_noise",
                    "claim_kind",
                )
            }
            expected["evidence"] = sorted(candidate["evidence"], key=lambda e: e["evidence_id"])
            # Existing card canonicalization intentionally uses default ensure_ascii.
            if sha(json.dumps(expected, sort_keys=True, separators=(",", ":"))) != revision["content_hash"]:
                raise StateStoreError("Synthesis card canonical hash differs")
    elif raw is not None:
        raise StateStoreError("Synthesis invalid response must retain safe observations only")


def verify_execution(
    repo: SQLiteStateRepository, c: sqlite3.Connection, eid: str, *, completing: bool = False
) -> PreparedSynthesis:
    verify_schema(c)
    row = _row(c, PROOFS, "execution_id", eid)
    prepared = _replay(repo, c, row)
    checkpoint = _row(c, "distillation_execution_checkpoints", "execution_id", eid)
    cmd = loads(prepared.proof_json)["command"]
    if (
        any(
            checkpoint[k] != cmd[k]
            for k in (
                "source_id",
                "video_id",
                "reason",
                "use_case",
                "selected_provider",
                "selected_model",
                "output_language",
            )
        )
        or row["created_at"] != checkpoint["created_at"]
    ):
        raise StateStoreError("Synthesis checkpoint/proof identity differs")
    auth = c.execute(f"SELECT * FROM {AUTHORIZATIONS} WHERE execution_id=?", (eid,)).fetchone()
    if checkpoint["invocation_count"] == 1 and auth is None:
        raise StateStoreError("Synthesis claimed execution lacks affirmative consent")
    if auth is not None:
        p = loads(prepared.proof_json)
        if (
            auth["verified_input_hash"] != prepared.proof_sha256
            or (auth["provider"], auth["model"]) != profile.PAIR
            or auth["reserve_microunits"] != p["reserve_microunits"]
            or auth["price_sha256"] != p["transport_sha256"]
            or auth["authorized_at"] < checkpoint["created_at"]
            or auth["authorized_at"] > checkpoint["updated_at"]
        ):
            raise StateStoreError("Synthesis consent/profile/price differs")
    if auth is not None:
        peers = c.execute(f"SELECT * FROM {AUTHORIZATIONS} WHERE budget_scope=?", (auth["budget_scope"],)).fetchall()
        policy_keys = ("budget_limit_microunits", "max_calls", "prior_reserved_microunits", "prior_calls")
        if (
            any(any(peer[k] != auth[k] for k in policy_keys) for peer in peers)
            or sum(peer["reserve_microunits"] for peer in peers) + auth["prior_reserved_microunits"]
            > auth["budget_limit_microunits"]
            or len(peers) + auth["prior_calls"] > auth["max_calls"]
        ):
            raise StateStoreError("Synthesis cumulative fee reservation exceeds its explicit policy")
    observation = _observation(c, eid)
    receipt = c.execute(f"SELECT * FROM {RECEIPTS} WHERE execution_id=?", (eid,)).fetchone()
    terminal = checkpoint["status"] in {"SUCCEEDED", "REJECTED_OUTPUT", "AMBIGUOUS"} or (
        observation is not None and observation["table"] == "distillation_no_new_intelligence_results"
    )
    if terminal and receipt is None and not completing:
        raise StateStoreError("Synthesis terminal result lacks original receipt")
    if receipt is not None:
        if not terminal or auth is None:
            raise StateStoreError("Synthesis receipt is not terminal")
        _validate_receipt(repo, c, prepared, checkpoint, dict(receipt))
    cancellation = c.execute(f"SELECT * FROM {TABLE} WHERE execution_id=?", (eid,)).fetchone()
    if checkpoint["status"] == "WAITING_MODEL" or cancellation is not None:
        verify_wait(
            c,
            c.execute("SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?", (eid,)).fetchone(),
            repository=repo,
        )
    return prepared


def verify_wait(
    c: sqlite3.Connection, checkpoint: sqlite3.Row, *, repository: SQLiteStateRepository | None = None
) -> None:
    repo = repository or SQLiteStateRepository(Path(":memory:"))
    prepared = _replay(repo, c, _row(c, PROOFS, "execution_id", checkpoint["execution_id"]))
    observation = _observation(c, prepared.execution_id)
    if (
        checkpoint["status"] != "WAITING_MODEL"
        or checkpoint["invocation_count"] != 0
        or checkpoint["budget_state"] != "RESERVED_NOT_DISPATCHED"
        or checkpoint["intelligence_id"] is not None
        or checkpoint["revision_id"] is not None
        or observation is None
        or observation["table"] != "distillation_resource_usage"
    ):
        raise StateStoreError("Synthesis cancellation needs proven WAIT0")
    usage = observation["row"]
    if (
        any(usage[k] != checkpoint[k] for k in BINDINGS if k != "output_language")
        or usage["status"] != "WAITING_MODEL"
        or usage["invocation_count"] != 0
        or usage["outcome"] != "MODEL_UNAVAILABLE_BEFORE_TRANSPORT"
        or usage["created_at"] != checkpoint["updated_at"]
        or any(
            usage[k] is not None
            for k in (
                "actual_provider",
                "actual_model",
                "input_tokens",
                "output_tokens",
                "cost_microunits",
                "duration_ms",
                "http_status_code",
                "intelligence_id",
                "revision_id",
            )
        )
        or c.execute(f"SELECT 1 FROM {AUTHORIZATIONS} WHERE execution_id=?", (prepared.execution_id,)).fetchone()
        or c.execute(f"SELECT 1 FROM {RECEIPTS} WHERE execution_id=?", (prepared.execution_id,)).fetchone()
    ):
        raise StateStoreError("Synthesis zero-call accounting differs")


def read_cancellation(
    c: sqlite3.Connection, checkpoint: sqlite3.Row, *, repository: SQLiteStateRepository | None = None
) -> sqlite3.Row | None:
    if not has_table(c):
        return None
    row = c.execute(f"SELECT * FROM {TABLE} WHERE execution_id=?", (checkpoint["execution_id"],)).fetchone()
    if row is not None:
        verify_wait(c, checkpoint, repository=repository)
        if (
            any(row[k] != checkpoint[k] for k in BINDINGS)
            or row["checkpoint_updated_at"] != checkpoint["updated_at"]
            or row["cancelled_at"] < checkpoint["updated_at"]
            or row["outcome"] != OUTCOME
        ):
            raise StateStoreError("Synthesis cancellation identity differs")
    return cast(sqlite3.Row | None, row)


def abandon_unclaimed(repo: SQLiteStateRepository, eid: str, *, now: datetime) -> None:
    """Explicitly abandon ONLY this proven never-authorized new-family reservation."""
    with closing(repo._connect()) as c, _immediate_transaction(c):
        verify_execution(repo, c, eid)
        checkpoint = c.execute(
            "SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?", (eid,)
        ).fetchone()
        assert checkpoint is not None
        if (
            checkpoint["status"] != "PENDING"
            or checkpoint["invocation_count"] != 0
            or c.execute(f"SELECT 1 FROM {AUTHORIZATIONS} WHERE execution_id=?", (eid,)).fetchone()
            or _observation(c, eid) is not None
        ):
            raise StateStoreError("Synthesis unclaimed abandonment not proven")
        timestamp = format_utc_datetime(now)
        if timestamp < checkpoint["updated_at"]:
            raise ValueError("Synthesis cancellation clock precedes reservation")
        c.execute(
            "UPDATE distillation_execution_checkpoints SET status='WAITING_MODEL',updated_at=? WHERE execution_id=?",
            (timestamp, eid),
        )
        repo._insert_distillation_usage(
            c,
            checkpoint=checkpoint,
            status="WAITING_MODEL",
            budget_state="RESERVED_NOT_DISPATCHED",
            outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT",
            invocation_count=0,
            actual_provider=None,
            actual_model=None,
            input_tokens=None,
            output_tokens=None,
            cost_microunits=None,
            duration_ms=None,
            http_status_code=None,
            intelligence_id=None,
            revision_id=None,
            now=now,
        )
        values = [checkpoint[k] for k in BINDINGS]
        c.execute(f"INSERT INTO {TABLE} VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (*values, timestamp, timestamp, OUTCOME))
        verify_execution(repo, c, eid)


def append_receipt(repo: SQLiteStateRepository, c: sqlite3.Connection, eid: str, completion: Completion | None) -> None:
    checkpoint = c.execute("SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?", (eid,)).fetchone()
    if checkpoint is None or not owns(checkpoint):
        if completion is not None:
            raise StateStoreError("Synthesis receipt cannot be attached to legacy operation")
        return
    if checkpoint["invocation_count"] == 0:
        if completion is not None:
            raise StateStoreError("Synthesis zero invocation has no response")
        verify_execution(repo, c, eid)
        return
    if type(completion) is not Completion:
        raise StateStoreError("Synthesis original result receipt required")
    prepared = verify_execution(repo, c, eid, completing=True)
    raw = completion.raw_text
    rawhash = sha(raw) if raw is not None else completion.raw_sha256
    if completion.raw_sha256 is not None and completion.raw_sha256 != rawhash:
        raise StateStoreError("Synthesis original raw hash differs")
    observation = _observation(c, eid)
    c.execute(
        f"INSERT INTO {RECEIPTS} VALUES (?,?,?,?,?,?,?)",
        (
            eid,
            prepared.proof_sha256,
            raw,
            rawhash,
            canonical(observation),
            checkpoint["revision_id"],
            checkpoint["updated_at"],
        ),
    )
    verify_execution(repo, c, eid)


CLOUD_GUARDS = (
    "distillation_moonshot_cloud_dispatch_requires_authorization",
    "distillation_no_new_http_status_bound",
    "distillation_resource_usage_http_status_bound",
    "distillation_cloud_failure_outcome_finite",
    "distillation_cloud_response_failure_bound",
)


def _schema(c: sqlite3.Connection) -> list[tuple[str, str, str]]:
    tables = ",".join("?" for _ in TABLES)
    guards = ",".join("?" for _ in CLOUD_GUARDS)
    return [
        (r[0], r[1], "".join(r[2].split()).rstrip(";"))
        for r in c.execute(
            f"SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL AND (tbl_name IN ({tables}) OR name LIKE 'system_synthesis_%' OR name LIKE 'synthesis_%' OR name IN ({guards})) ORDER BY type,name",
            (*TABLES, *CLOUD_GUARDS),
        )
    ]


@lru_cache(maxsize=1)
def _expected_schema() -> list[tuple[str, str, str]]:
    repo = SQLiteStateRepository(Path(":memory:"))
    with closing(sqlite3.connect(":memory:")) as c:
        c.executescript(
            "CREATE TABLE distillation_execution_checkpoints(execution_id TEXT); CREATE TABLE distillation_resource_usage(execution_id TEXT); CREATE TABLE distillation_no_new_intelligence_results(execution_id TEXT); CREATE TABLE distillation_cloud_response_failures(execution_id TEXT); CREATE TABLE source_run_video_executions(distillation_execution_id TEXT);"
        )
        for name in (
            "distillation_moonshot_cloud_dispatch_requires_authorization",
            "distillation_no_new_http_status_bound",
            "distillation_resource_usage_http_status_bound",
            "distillation_cloud_failure_outcome_finite",
            "distillation_cloud_response_failure_bound",
        ):
            c.executescript(f"CREATE TRIGGER {name} BEFORE INSERT ON distillation_resource_usage BEGIN SELECT 1; END;")
        c.executescript(next(m.sql for m in repo._load_migrations() if m.version == 44))
        return _schema(c)


def verify_schema(c: sqlite3.Connection) -> None:
    version = int(c.execute("PRAGMA user_version").fetchone()[0])
    if version < 44:
        if c.execute(
            "SELECT 1 FROM sqlite_master WHERE name LIKE 'system_synthesis_%' OR name LIKE 'synthesis_%'"
        ).fetchone():
            raise StateStoreError("Synthesis proof appeared in legacy schema")
        return
    if _schema(c) != _expected_schema():
        raise StateStoreError("Synthesis schema44 constraints differ")


def verify_database(repo: SQLiteStateRepository, c: sqlite3.Connection) -> None:
    verify_schema(c)
    if int(c.execute("PRAGMA user_version").fetchone()[0]) < 44:
        return
    for row in c.execute(
        "SELECT * FROM distillation_execution_checkpoints WHERE lower(execution_id) LIKE 'distillation:system-synthesis-%' OR (selected_provider='moonshot' AND selected_model='kimi-k3.1-pro')"
    ):
        verify_execution(repo, c, row["execution_id"])
    for table in TABLES:
        for row in c.execute(f"SELECT execution_id FROM {table}"):
            checkpoint = c.execute(
                "SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?", (row[0],)
            ).fetchone()
            if checkpoint is None or not owns(checkpoint):
                raise StateStoreError("Orphan synthesis sidecar")
    for row in c.execute(
        "SELECT revision_id FROM intelligence_revisions WHERE lower(revision_id) LIKE 'revision:distillation:system-synthesis-%'"
    ):
        verify_revision(repo, c, row[0])


def verify_revision(repo: SQLiteStateRepository, c: sqlite3.Connection, revision_id: str) -> None:
    row = (
        c.execute(f"SELECT execution_id FROM {RECEIPTS} WHERE revision_id=?", (revision_id,)).fetchone()
        if has_table(c)
        else None
    )
    reserved = revision_id.casefold().startswith("revision:distillation:system-synthesis-")
    checkpoint = c.execute(
        "SELECT * FROM distillation_execution_checkpoints WHERE revision_id=?", (revision_id,)
    ).fetchone()
    if row is not None or reserved or (checkpoint is not None and owns(checkpoint)):
        if row is None or checkpoint is None or row[0] != checkpoint["execution_id"]:
            raise StateStoreError("Synthesis revision lacks complete receipt")
        verify_execution(repo, c, row[0])
