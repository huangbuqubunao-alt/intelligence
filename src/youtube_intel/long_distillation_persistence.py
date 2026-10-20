"""Source-authoritative long timed waiting lifecycle; no model dispatch capability.

Historical validation consumes retained files/records, never current Summary,
policy or model qualification. All production long result authority stays closed.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import asdict, replace
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from youtube_intel.domain import (
    AnalysisPoint,
    AnalysisResult,
    EvidenceExcerpt,
    EvidenceSource,
    PointKind,
)
from youtube_intel.local_distillation_profile import canonical, digest
from youtube_intel.long_distillation_profile import (
    PROFILE_ID,
    PreparedLongRequest,
    prepare_long_request,
    resolve_long_profile,
)
from youtube_intel.long_grounding_codec import (
    EncodedGrounding,
    EvidenceSpan,
    encode_grounding,
    expand_grounding,
)
from youtube_intel.source_authority import read_managed
from youtube_intel.state import (
    SQLiteStateRepository,
    StateStoreError,
    _immediate_transaction,
    format_utc_datetime,
)

if TYPE_CHECKING:
    from youtube_intel.distillation import (
        DistillationCommand,
        PersonalizedDistillationService,
        VerifiedDistillationInput,
    )

FAMILY = "distillation:long-timed"
PREFIX = "distillation:long-timed-v1:"
PROOFS = "long_distillation_input_proofs"
RECEIPTS = "long_distillation_completion_receipts"


def is_long(execution_id: str) -> bool:
    return execution_id.casefold().startswith(FAMILY)


def is_long_revision(revision_id: str) -> bool:
    return revision_id.casefold().startswith("revision:distillation:" + FAMILY)


def reject_generic(execution_id: str) -> None:
    if is_long(execution_id):
        raise StateStoreError("long execution requires its dedicated lifecycle")


def require_identity(execution_id: str) -> None:
    if re.fullmatch(re.escape(PREFIX) + r"[0-9a-f]{64}", execution_id) is None:
        raise StateStoreError("unknown or malformed long execution version")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate long provenance key")
        result[key] = value
    return result


def _nonfinite(value: str) -> Any:
    raise ValueError("nonfinite long provenance value")


def loads(wire: str) -> dict[str, Any]:
    value = json.loads(wire, object_pairs_hook=_object, parse_constant=_nonfinite)
    if not isinstance(value, dict):
        raise ValueError("long provenance requires an object")
    canonical(value)  # strict Unicode and finite numbers
    return cast(dict[str, Any], value)


def _row(
    connection: sqlite3.Connection, table: str, key: str, value: str
) -> dict[str, Any]:
    # Table/key are exclusively fixed application literals.
    row = connection.execute(
        f"SELECT * FROM {table} WHERE {key}=?", (value,)
    ).fetchone()
    if row is None:
        raise StateStoreError("long source record is missing")
    return dict(row)


def _file(repository: SQLiteStateRepository, artifact: dict[str, Any]) -> bytes:
    if (
        repository._source_data_root is None
        or artifact["storage_root"] != "DATA"
        or artifact["deleted_at"] is not None
    ):
        raise StateStoreError("long source file authority is unavailable")
    wire = read_managed(
        repository._source_data_root, artifact["relative_path"], maximum=4_000_000
    )
    if hashlib.sha256(wire).hexdigest() != artifact["content_hash"]:
        raise StateStoreError("long source file hash differs")
    wire.decode("utf-8", errors="strict")
    return wire


def _summary(
    repository: SQLiteStateRepository,
    connection: sqlite3.Connection,
    video_id: str,
    artifact_id: str,
) -> dict[str, Any]:
    artifact = _row(connection, "artifacts", "artifact_id", artifact_id)
    if (
        artifact["video_id"] != video_id
        or artifact["kind"] != "analysis_structured"
        or artifact["provider"] != "extractive-source"
        or artifact["producer_version"]
        not in {"extractive-summary-v1", "extractive-summary-v2"}
    ):
        raise StateStoreError("long original Summary provenance is unsupported")
    wire = _file(repository, artifact)
    result = AnalysisResult.model_validate_json(wire)
    if not 1 <= len(result.evidence) <= 6:
        raise StateStoreError("long original Summary parent count differs")
    parents = []
    excerpts = []
    for item in result.evidence:
        verified = repository._resolve_verified_evidence_text_in_transaction(
            connection, item.evidence_id
        )
        if (
            verified is None
            or verified.video_id != video_id
            or verified.excerpt != item.excerpt
            or len(item.excerpt) > 2000
        ):
            raise StateStoreError("long original Summary parent does not resolve")
        parents.append(
            {
                "evidence": _row(
                    connection, "evidence", "evidence_id", item.evidence_id
                ),
                "binding": _row(
                    connection,
                    "evidence_text_bindings",
                    "evidence_id",
                    item.evidence_id,
                ),
                "verified": asdict(verified),
            }
        )
        excerpts.append(
            EvidenceExcerpt(
                evidence_id=item.evidence_id,
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                excerpt=verified.excerpt,
            )
        )
    version = artifact["producer_version"]
    identity = digest(
        {
            "contract": version,
            "content_id": video_id,
            "evidence": [e.model_dump(mode="json") for e in excerpts],
        }
    )
    expected = AnalysisResult(
        provider="extractive-source",
        model="deterministic-excerpts-v2"
        if version.endswith("v2")
        else "deterministic-excerpts-v1",
        prompt_version="analysis-prompt-v6",
        request_hash=identity,
        one_sentence_summary=excerpts[0].excerpt[:500],
        core_points=tuple(
            AnalysisPoint(
                text=e.excerpt, kind=PointKind.FACT, evidence_ids=(e.evidence_id,)
            )
            for e in excerpts
        ),
        keywords=("source excerpts",),
        evidence=tuple(excerpts),
    )
    if (
        result != expected
        or artifact["artifact_id"] != f"summary/{identity}/structured"
        or artifact["model"] != result.model
    ):
        raise StateStoreError("long original Summary reconstruction differs")
    return {
        "artifact": artifact,
        "original_utf8_wire": wire.decode(),
        "parents": parents,
        "reconstruction": expected.model_dump(mode="json"),
    }


def _policy(
    repository: SQLiteStateRepository,
    connection: sqlite3.Connection,
    command: DistillationCommand,
    global_id: str,
) -> dict[str, Any]:
    from youtube_intel.source_policy import SourcePolicyApplicationService

    global_row = _row(connection, "source_policy_revisions", "revision_id", global_id)
    source_row = (
        None
        if command.source_policy_revision_id is None
        else _row(
            connection,
            "source_policy_revisions",
            "revision_id",
            command.source_policy_revision_id,
        )
    )
    if (
        global_row["policy_scope"] != "GLOBAL"
        or global_row["source_id"] is not None
        or (
            source_row is not None
            and (
                source_row["policy_scope"] != "SOURCE"
                or source_row["source_id"] != command.source_id
            )
        )
    ):
        raise StateStoreError("long policy scope differs")
    policy = SourcePolicyApplicationService._policy_from_revisions(
        repository._source_policy_revision_from_row(
            connection.execute(
                "SELECT * FROM source_policy_revisions WHERE revision_id=?",
                (global_id,),
            ).fetchone()
        ),
        None
        if source_row is None
        else repository._source_policy_revision_from_row(
            connection.execute(
                "SELECT * FROM source_policy_revisions WHERE revision_id=?",
                (command.source_policy_revision_id,),
            ).fetchone()
        ),
    )
    if (
        command.source_focus_rules != policy.focus_rules
        or command.source_ignore_rules != policy.ignore_rules
        or command.distillation_style != policy.distillation_style.value
    ):
        raise StateStoreError("long effective policy differs")
    preferences = []
    for preference in command.active_preferences:
        row = _row(connection, "preferences", "preference_id", preference.preference_id)
        if any(
            row[key] != getattr(preference, key)
            for key in ("statement", "scope", "target_id", "horizon", "provenance")
        ):
            raise StateStoreError("long preference identity differs")
        preferences.append(row)
    return {
        "global_revision": global_row,
        "source_revision": source_row,
        "preferences": preferences,
        "command": asdict(command),
    }


def _source(
    repository: SQLiteStateRepository,
    connection: sqlite3.Connection,
    source_id: str,
    video_id: str,
    canonical_id: str | None = None,
    frozen: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], EncodedGrounding]:
    source = _row(connection, "source_subscriptions", "source_id", source_id)
    video = _row(connection, "videos", "video_id", video_id)
    if (
        source["provider"] != "YOUTUBE"
        or video["provider"] != "YOUTUBE"
        or video["availability"] != "public"
        or not connection.execute(
            "SELECT 1 FROM source_video_links WHERE source_id=? AND video_id=?",
            (source_id, video_id),
        ).fetchone()
    ):
        raise StateStoreError("long source association differs")
    if canonical_id is None:
        all_original = connection.execute(
            "SELECT * FROM evidence WHERE video_id=? AND availability='AVAILABLE' AND lineage_kind='ORIGINAL_TRANSCRIPT'",
            (video_id,),
        ).fetchall()
        if not all_original or len(all_original) > 4102:
            raise StateStoreError(
                "long complete ORIGINAL Evidence set exceeds its bound or is empty"
            )
        for original in all_original:
            parent = _row(
                connection, "artifacts", "artifact_id", original["artifact_id"]
            )
            binding = _row(
                connection,
                "evidence_text_bindings",
                "evidence_id",
                original["evidence_id"],
            )
            if (
                parent["video_id"] != video_id
                or parent["kind"] != "transcript_canonical"
                or parent["deleted_at"] is not None
            ):
                raise StateStoreError("long AVAILABLE ORIGINAL parent is invalid")
            timed_parent = _row(
                connection,
                "timed_transcripts",
                "timed_transcript_id",
                binding["timed_transcript_id"],
            )
            if (
                timed_parent["video_id"] != video_id
                or timed_parent["canonical_artifact_id"] != original["artifact_id"]
            ):
                raise StateStoreError("long AVAILABLE ORIGINAL timed parent differs")
        rows = connection.execute(
            "SELECT DISTINCT a.* FROM artifacts a JOIN evidence e USING(artifact_id) WHERE a.video_id=? AND a.kind='transcript_canonical' AND a.deleted_at IS NULL AND e.availability='AVAILABLE' AND e.lineage_kind='ORIGINAL_TRANSCRIPT' ",
            (video_id,),
        ).fetchall()
        if len(rows) != 1:
            raise StateStoreError("long canonical source is ambiguous")
        artifact = dict(rows[0])
    else:
        artifact = _row(connection, "artifacts", "artifact_id", canonical_id)
    if artifact["video_id"] != video_id or artifact["kind"] != "transcript_canonical":
        raise StateStoreError("long canonical artifact differs")
    wire = _file(repository, artifact)
    timed_rows = connection.execute(
        "SELECT * FROM timed_transcripts WHERE canonical_artifact_id=? AND video_id=?",
        (artifact["artifact_id"], video_id),
    ).fetchall()
    if len(timed_rows) != 1:
        raise StateStoreError("long timed source is missing or ambiguous")
    if frozen is None:
        if (
            connection.execute(
                "SELECT count(*) FROM timed_transcripts WHERE video_id=?", (video_id,)
            ).fetchone()[0]
            != 1
        ):
            raise StateStoreError("long timed source is ambiguous")
        timed = repository._get_verified_timed_transcript_in_transaction(
            connection, video_id
        )
    else:
        from youtube_intel.state import (
            VerifiedTimedTranscript,
            VerifiedTimedTranscriptCue,
        )

        row = timed_rows[0]
        cues = connection.execute(
            "SELECT * FROM timed_transcript_cues WHERE timed_transcript_id=? ORDER BY cue_index",
            (row["timed_transcript_id"],),
        ).fetchall()
        timed = VerifiedTimedTranscript(
            row["timed_transcript_id"],
            row["video_id"],
            row["canonical_artifact_id"],
            row["timed_transcript_hash"],
            tuple(
                VerifiedTimedTranscriptCue(
                    c["cue_index"],
                    c["start_ms"],
                    c["end_ms"],
                    c["cue_text"],
                    c["cue_text_hash"],
                )
                for c in cues
            ),
        )
    if timed is None or timed.canonical_artifact_id != artifact["artifact_id"]:
        raise StateStoreError("long timed source failed verification")
    cue_wire = "\n".join(c.text for c in timed.cues).encode()
    # Production canonical serialization terminates with LF; older exact test
    # and retained source representations may omit that terminal separator.
    # Retain and hash the original bytes; never strip/normalize cue contents.
    if wire not in (cue_wire, cue_wire + b"\n"):
        raise StateStoreError("long canonical file and complete cues differ")
    rows = connection.execute(
        "SELECT e.*,b.start_cue_index,b.end_cue_index FROM evidence e JOIN evidence_text_bindings b USING(evidence_id) WHERE e.video_id=? AND e.artifact_id=? AND e.availability='AVAILABLE' AND e.lineage_kind='ORIGINAL_TRANSCRIPT' ORDER BY b.start_cue_index,b.end_cue_index,e.evidence_id",
        (video_id, artifact["artifact_id"]),
    ).fetchall()
    if frozen is not None:
        ids = [e["evidence"]["evidence_id"] for e in frozen["evidence"]]
        by_id = {row["evidence_id"]: row for row in rows}
        if len(ids) != len(set(ids)) or any(eid not in by_id for eid in ids):
            raise StateStoreError("long frozen Evidence set differs")
        rows = [by_id[eid] for eid in ids]
    if not rows or len(rows) > 4102:
        raise StateStoreError("long complete Evidence set is invalid")
    spans, evidence_rows = [], []
    for row in rows:
        verified = repository._resolve_verified_evidence_text_in_transaction(
            connection, row["evidence_id"]
        )
        if verified is None:
            raise StateStoreError("long Evidence failed verification")
        spans.append(
            EvidenceSpan(verified, row["start_cue_index"], row["end_cue_index"])
        )
        evidence_rows.append(
            {
                "evidence": _row(
                    connection, "evidence", "evidence_id", row["evidence_id"]
                ),
                "binding": _row(
                    connection,
                    "evidence_text_bindings",
                    "evidence_id",
                    row["evidence_id"],
                ),
            }
        )
    packet = encode_grounding(
        source_id=source_id,
        content_provider="YOUTUBE",
        source_content_hash=artifact["content_hash"],
        canonical_text_hash=artifact["content_hash"],
        transcript=timed,
        evidence=tuple(spans),
    )
    return {
        "source_identity": {
            k: source[k]
            for k in ("source_id", "provider", "source_type", "canonical_url")
        },
        "video_identity": {k: video[k] for k in ("video_id", "provider", "source_url")},
        "canonical_artifact": artifact,
        "canonical_utf8_wire": wire.decode(),
        "timed": asdict(timed),
        "evidence": evidence_rows,
    }, packet


def _value(
    command: DistillationCommand,
    source: dict[str, Any],
    video: dict[str, Any],
    packet: EncodedGrounding,
    profile_id: str | None,
) -> VerifiedDistillationInput:
    from youtube_intel.distillation import (
        VerifiedDistillationInput,
        VerifiedEvidenceInput,
        bind_local_profile,
    )

    evidence = tuple(
        VerifiedEvidenceInput(
            **{k: v for k, v in asdict(span.evidence).items() if k != "video_id"}
        )
        for span in expand_grounding(packet).evidence
    )
    value = VerifiedDistillationInput(
        source_display_name=source["display_name"] or video["channel_name"],
        video_id=command.video_id,
        video_title=video["title"],
        evidence=evidence,
        personalization=tuple(p.statement for p in command.active_preferences),
        source_focus_rules=command.source_focus_rules,
        source_ignore_rules=command.source_ignore_rules,
        distillation_style=command.distillation_style,
        selected_provider=command.selected_provider,
        selected_model=command.selected_model,
        output_language=command.output_language,
        semantic_hash="0" * 64,
    )
    if profile_id is not None:
        value = bind_local_profile(value, profile_id)
    semantic: dict[str, Any] = {
        "distillation_style": value.distillation_style,
        "evidence": [
            {
                k: getattr(e, k)
                for k in (
                    "end_ms",
                    "evidence_id",
                    "excerpt_hash",
                    "start_ms",
                    "timed_transcript_hash",
                    "timed_transcript_id",
                )
            }
            for e in evidence
        ],
        "personalization": value.personalization,
        "selected_model": value.selected_model,
        "selected_provider": value.selected_provider,
        "output_language": value.output_language,
        "source_focus_rules": value.source_focus_rules,
        "source_id": command.source_id,
        "source_ignore_rules": value.source_ignore_rules,
        "source_display_name": value.source_display_name,
        "video_id": value.video_id,
        "video_title": value.video_title,
    }
    if profile_id is not None:
        semantic.update(
            local_profile_id=value.local_profile_id,
            local_profile_hash=value.local_profile_hash,
        )
    return replace(value, semantic_hash=digest(semantic))


def candidate_evidence_ids(
    service: PersonalizedDistillationService, video_id: str
) -> tuple[str, ...]:
    video = service._repository.get_video(video_id)
    profile = loads(resolve_long_profile(PROFILE_ID).profile_wire.decode())
    if (
        video is None
        or video.provider != "YOUTUBE"
        or service._selected_provider != "ollama"
        or service._selected_model != profile["model"]
    ):
        return service._repository.list_canonical_coverage_evidence_ids(video_id)
    with service._repository._connect() as connection:
        rows = connection.execute(
            "SELECT e.evidence_id FROM evidence e WHERE e.video_id=? AND e.availability='AVAILABLE' AND e.lineage_kind='ORIGINAL_TRANSCRIPT' ORDER BY e.start_ms,e.evidence_id LIMIT 4103",
            (video_id,),
        ).fetchall()
    if len(rows) > 4102:
        raise StateStoreError("long full source exceeds its storage bound")
    return tuple(str(row[0]) for row in rows)


def route_required(
    service: PersonalizedDistillationService,
    video_id: str,
    evidence_ids: tuple[str, ...],
    source_id: str | None = None,
) -> bool:
    from youtube_intel.distillation import (
        DistillationCommand,
        build_local_distillation_request,
    )

    video = service._repository.get_video(video_id)
    profile = loads(resolve_long_profile(PROFILE_ID).profile_wire.decode())
    if (
        video is None
        or video.provider != "YOUTUBE"
        or service._selected_provider != "ollama"
        or service._selected_model != profile["model"]
    ):
        return False
    if len(evidence_ids) > 20:
        return True
    if service._local_profile_id is None:
        return False
    if source_id is None:
        return False
    command = service._projection(
        DistillationCommand(
            execution_id="",
            source_id=source_id,
            video_id=video_id,
            evidence_ids=evidence_ids,
            reason=service._RESERVATION_REASON,
            use_case=service._RESERVATION_USE_CASE,
            selected_provider=service._selected_provider,
            selected_model=service._selected_model,
            output_language=cast(Any, service.capability_output_language(video_id)),
        )
    )
    value = service._compose_verified_input(command)
    try:
        build_local_distillation_request(value)
    except ValueError as error:
        if "UTF-8" in str(error) or "budget" in str(error):
            return True
        raise
    return False


def _proof_digest(proof: dict[str, Any]) -> str:
    return digest({k: v for k, v in proof.items() if k != "proof_hash"})


def _execution_id(proof: dict[str, Any], command: dict[str, Any]) -> str:
    return PREFIX + digest(
        {
            "source_id": proof["source_id"],
            "video_id": proof["video_id"],
            "reason": command["reason"],
            "use_case": command["use_case"],
            "freeze_hash": proof["freeze_hash"],
            "global_policy_revision_id": proof["global_policy_revision_id"],
            "source_policy_revision_id": proof["source_policy_revision_id"],
        }
    )


def reserve_wait(
    service: PersonalizedDistillationService,
    *,
    source_id: str,
    video_id: str,
    evidence_ids: tuple[str, ...],
    manual_command_id: str | None,
) -> str:
    from youtube_intel.distillation import DistillationCommand

    repository = service._repository
    reason = (
        service._RESERVATION_REASON
        if manual_command_id is None
        else "MANUAL_CONTENT:" + manual_command_id
    )
    if (
        manual_command_id is not None
        and re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", manual_command_id) is None
    ):
        raise ValueError("manual Content command identity is invalid")
    language = service.capability_output_language(video_id)
    if language not in {"en", "zh-CN"}:
        raise StateStoreError("long output language is unavailable")
    with repository._connect() as connection, _immediate_transaction(connection):
        source_snapshot, packet = _source(repository, connection, source_id, video_id)
        expanded = expand_grounding(packet)
        if set(evidence_ids) != {
            s.evidence.evidence_id for s in expanded.evidence
        } or len(evidence_ids) != len(expanded.evidence):
            raise StateStoreError(
                "long request must contain the exact complete Evidence set"
            )
        command = service._projection(
            DistillationCommand(
                execution_id="",
                source_id=source_id,
                video_id=video_id,
                evidence_ids=evidence_ids,
                reason=reason,
                use_case=service._RESERVATION_USE_CASE,
                selected_provider=service._selected_provider,
                selected_model=service._selected_model,
                output_language=cast(Any, language),
            )
        )
        source = _row(connection, "source_subscriptions", "source_id", source_id)
        latest_filter = connection.execute(
            "SELECT outcome FROM source_video_filter_decisions WHERE source_id=? AND video_id=? ORDER BY decision_order DESC LIMIT 1",
            (source_id, video_id),
        ).fetchone()
        if manual_command_id is None and (
            not source["enabled"]
            or latest_filter is None
            or latest_filter[0] != "RELEVANT"
        ):
            raise StateStoreError("long source is not eligible")
        pointer = _row(connection, "current_content_summaries", "video_id", video_id)
        if pointer["analysis_artifact_id"] is None or pointer[
            "output_language"
        ] not in {"en", "zh-CN"}:
            raise StateStoreError("long Summary pointer is unavailable")
        summary = _summary(
            repository, connection, video_id, pointer["analysis_artifact_id"]
        )
        global_id = connection.execute(
            "SELECT revision_id FROM source_policy_current WHERE policy_key='GLOBAL'"
        ).fetchone()[0]
        policy = _policy(repository, connection, command, global_id)
        value = _value(
            command,
            source,
            _row(connection, "videos", "video_id", video_id),
            packet,
            service._local_profile_id,
        )
        prepared = prepare_long_request(
            packet,
            value,
            source_snapshot=canonical(source_snapshot),
            summary_snapshot=canonical(summary),
            policy_snapshot=canonical(policy),
        )
        now = format_utc_datetime(service._now())
        from youtube_intel.local_distillation_qualification import CODE_FILES

        package = resources.files("youtube_intel")
        proof: dict[str, Any] = dict(
            execution_id="",
            proof_version="long-timed-input-proof-v1",
            wire_version="long-grounding-lossless-timed-v1",
            source_id=source_id,
            video_id=video_id,
            canonical_artifact_id=expanded.transcript.canonical_artifact_id,
            timed_transcript_id=expanded.transcript.timed_transcript_id,
            original_summary_artifact_id=pointer["analysis_artifact_id"],
            global_policy_revision_id=global_id,
            source_policy_revision_id=command.source_policy_revision_id,
            semantic_snapshot_wire=prepared.projection.semantic_snapshot_wire.decode(),
            semantic_snapshot_hash=prepared.projection.semantic_snapshot_hash,
            profile_wire=resolve_long_profile(PROFILE_ID).profile_wire.decode(),
            profile_hash=prepared.profile_hash,
            request_wire=prepared.request_wire.decode(),
            request_hash=prepared.request_hash,
            schema_hash=prepared.schema_hash,
            freeze_hash=prepared.freeze_hash,
            code_identity_json=canonical(
                {
                    "contract": "long-code-identity-v1",
                    "files": {
                        name: hashlib.sha256(
                            package.joinpath(name).read_bytes()
                        ).hexdigest()
                        for name in CODE_FILES
                    },
                }
            ).decode(),
            proof_hash="",
            created_at=now,
        )
        execution_id = proof["execution_id"] = _execution_id(proof, policy["command"])
        existing = connection.execute(
            f"SELECT * FROM {PROOFS} WHERE execution_id=?", (execution_id,)
        ).fetchone()
        if existing is not None:
            verify_execution(repository, connection, execution_id)
            return execution_id
        proof["proof_hash"] = _proof_digest(proof)
        decision = service._budget.check(replace(command, execution_id=execution_id))
        state = "WAITING_MODEL" if decision.allowed else "WAITING_BUDGET"
        outcome = (
            "MODEL_UNAVAILABLE_BEFORE_TRANSPORT"
            if decision.allowed
            else "BUDGET_BLOCKED_BEFORE_TRANSPORT"
        )
        if decision.allowed and decision.state not in {
            "ADMITTED",
            "RUNTIME_BUDGET_ADMITTED",
        }:
            raise StateStoreError("long model wait requires a real admitted budget")
        connection.execute(
            "INSERT INTO distillation_execution_checkpoints(execution_id,source_id,video_id,reason,use_case,selected_provider,selected_model,output_language,status,budget_state,invocation_count,intelligence_id,revision_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?, 'PENDING','RESERVED_NOT_DISPATCHED',0,NULL,NULL,?,?)",
            (
                execution_id,
                source_id,
                video_id,
                reason,
                command.use_case,
                command.selected_provider,
                command.selected_model,
                language,
                now,
                now,
            ),
        )
        connection.execute(
            f"INSERT INTO {PROOFS}({','.join(proof)}) VALUES({','.join('?' for _ in proof)})",
            tuple(proof.values()),
        )
        _checkpoint_wait(connection, execution_id, state, decision.state, outcome, now)
        verify_execution(repository, connection, execution_id)
        return execution_id


def _checkpoint_wait(
    connection: sqlite3.Connection,
    execution_id: str,
    state: str,
    budget_state: str,
    outcome: str,
    now: str,
) -> None:
    connection.execute(
        "UPDATE distillation_execution_checkpoints SET status=?,budget_state=?,updated_at=? WHERE execution_id=?",
        (state, budget_state, now, execution_id),
    )
    checkpoint = _row(
        connection, "distillation_execution_checkpoints", "execution_id", execution_id
    )
    keys = (
        "execution_id",
        "reason",
        "use_case",
        "source_id",
        "video_id",
        "selected_provider",
        "selected_model",
    )
    values = {k: checkpoint[k] for k in keys}
    values.update(
        status=state,
        invocation_count=0,
        budget_state=budget_state,
        outcome=outcome,
        created_at=now,
    )
    connection.execute(
        f"INSERT INTO distillation_resource_usage({','.join(values)}) VALUES({','.join('?' for _ in values)})",
        tuple(values.values()),
    )


def verify_proof(
    repository: SQLiteStateRepository, connection: sqlite3.Connection, execution_id: str
) -> dict[str, Any]:
    from youtube_intel.distillation import (
        ActivePreferenceProjection,
        DistillationCommand,
        VerifiedDistillationInput,
        VerifiedEvidenceInput,
    )

    require_identity(execution_id)
    proof = _row(connection, PROOFS, "execution_id", execution_id)
    checkpoint = _row(
        connection, "distillation_execution_checkpoints", "execution_id", execution_id
    )
    if (
        proof["proof_version"] != "long-timed-input-proof-v1"
        or proof["wire_version"] != "long-grounding-lossless-timed-v1"
        or proof["proof_hash"] != _proof_digest(proof)
    ):
        raise StateStoreError("long input proof hash/version differs")
    side = loads(proof["semantic_snapshot_wire"])
    snapshots = {
        k: loads(side["snapshots"][k]["wire"]) for k in ("source", "summary", "policy")
    }
    command_data = dict(snapshots["policy"]["command"])
    command_data["evidence_ids"] = tuple(command_data["evidence_ids"])
    for key in ("preference_ids", "source_focus_rules", "source_ignore_rules"):
        command_data[key] = tuple(command_data[key])
    command_data["active_preferences"] = tuple(
        ActivePreferenceProjection(**p) for p in command_data["active_preferences"]
    )
    command = DistillationCommand(**command_data)
    if (
        any(
            checkpoint[k] != getattr(command, k)
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
        or checkpoint["created_at"] != proof["created_at"]
    ):
        raise StateStoreError("long checkpoint/input identity differs")
    source_snapshot, packet = _source(
        repository,
        connection,
        proof["source_id"],
        proof["video_id"],
        proof["canonical_artifact_id"],
        snapshots["source"],
    )
    summary = _summary(
        repository, connection, proof["video_id"], proof["original_summary_artifact_id"]
    )
    policy = _policy(
        repository, connection, command, proof["global_policy_revision_id"]
    )
    if canonical(snapshots) != canonical(
        {"source": source_snapshot, "summary": summary, "policy": policy}
    ):
        raise StateStoreError("long frozen historical source/Summary/policy differs")
    value_data = dict(side["value"])
    value_data["evidence"] = tuple(
        VerifiedEvidenceInput(**e) for e in value_data["evidence"]
    )
    for key in ("personalization", "source_focus_rules", "source_ignore_rules"):
        value_data[key] = tuple(value_data[key])
    value = VerifiedDistillationInput(**value_data)
    # Validate the complete old semantic identity using the frozen metadata;
    # legitimate later title/display-name changes do not rewrite history.
    source = {"display_name": value.source_display_name}
    video = {"channel_name": value.source_display_name, "title": value.video_title}
    expected_value = _value(command, source, video, packet, value.local_profile_id)
    if expected_value != value:
        raise StateStoreError("long original semantic input differs")
    prepared = prepare_long_request(
        packet, value, **{k + "_snapshot": canonical(snapshots[k]) for k in snapshots}
    )
    _verify_prepared(proof, prepared)
    code = loads(proof["code_identity_json"])
    if (
        set(code) != {"contract", "files"}
        or code["contract"] != "long-code-identity-v1"
        or not isinstance(code["files"], dict)
        or not code["files"]
        or any(
            not isinstance(k, str) or re.fullmatch(r"[0-9a-f]{64}", str(v)) is None
            for k, v in code["files"].items()
        )
    ):
        raise StateStoreError("long historical code identity differs")
    if (
        execution_id != _execution_id(proof, snapshots["policy"]["command"])
        or proof["timed_transcript_id"]
        != expand_grounding(packet).transcript.timed_transcript_id
    ):
        raise StateStoreError("long execution freeze identity differs")
    return proof


def _verify_prepared(proof: dict[str, Any], prepared: PreparedLongRequest) -> None:
    expected = {
        "semantic_snapshot_wire": prepared.projection.semantic_snapshot_wire.decode(),
        "semantic_snapshot_hash": prepared.projection.semantic_snapshot_hash,
        "profile_wire": resolve_long_profile(PROFILE_ID).profile_wire.decode(),
        "profile_hash": prepared.profile_hash,
        "request_wire": prepared.request_wire.decode(),
        "request_hash": prepared.request_hash,
        "schema_hash": prepared.schema_hash,
        "freeze_hash": prepared.freeze_hash,
    }
    if any(proof[k] != v for k, v in expected.items()):
        raise StateStoreError("long complete native request freeze differs")


def verify_execution(
    repository: SQLiteStateRepository, connection: sqlite3.Connection, execution_id: str
) -> None:
    proof = verify_proof(repository, connection, execution_id)
    checkpoint = _row(
        connection, "distillation_execution_checkpoints", "execution_id", execution_id
    )
    usage = _row(
        connection, "distillation_resource_usage", "execution_id", execution_id
    )
    receipt = connection.execute(
        f"SELECT * FROM {RECEIPTS} WHERE execution_id=?", (execution_id,)
    ).fetchone()
    if receipt is not None:
        verify_receipt_payload(connection, proof, dict(receipt))
    # No result capability is registered in this slice. A retained receipt is
    # inspected by the final-contract verifier separately, never trusted here.
    if (
        checkpoint["status"] not in {"WAITING_MODEL", "WAITING_BUDGET"}
        or checkpoint["invocation_count"] != 0
    ):
        raise StateStoreError("long result/claimed execution authority is not enabled")
    bindings = (
        "execution_id",
        "source_id",
        "video_id",
        "reason",
        "use_case",
        "selected_provider",
        "selected_model",
        "budget_state",
        "invocation_count",
        "status",
        "intelligence_id",
        "revision_id",
    )
    if (
        any(usage[k] != checkpoint[k] for k in bindings)
        or usage["created_at"] != checkpoint["updated_at"]
        or checkpoint["created_at"] != proof["created_at"]
        or checkpoint["intelligence_id"] is not None
        or checkpoint["revision_id"] is not None
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
            )
        )
        or usage["outcome"]
        != (
            "MODEL_UNAVAILABLE_BEFORE_TRANSPORT"
            if checkpoint["status"] == "WAITING_MODEL"
            else "BUDGET_BLOCKED_BEFORE_TRANSPORT"
        )
    ):
        raise StateStoreError("long zero-invocation ledger differs")
    for table in (
        RECEIPTS,
        "distillation_no_new_intelligence_results",
        "distillation_cloud_response_failures",
        "distillation_unidentified_http_responses",
        "distillation_openai_unidentified_http_responses",
        "distillation_moonshot_unidentified_http_responses",
    ):
        if connection.execute(
            f"SELECT 1 FROM {table} WHERE execution_id=?", (execution_id,)
        ).fetchone():
            raise StateStoreError(
                "long waiting execution has conflicting result authority"
            )
    if connection.execute(
        "SELECT 1 FROM intelligence_revisions WHERE revision_id=?",
        ("revision:distillation:" + execution_id,),
    ).fetchone():
        raise StateStoreError("long waiting execution has an admitted revision")


def _schema(connection: sqlite3.Connection) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        tuple(row)
        for row in connection.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL AND (name LIKE 'long_distillation_%' OR tbl_name IN ('long_distillation_input_proofs','long_distillation_completion_receipts')) ORDER BY type,name"
        )
    )


@lru_cache(maxsize=1)
def _expected_schema() -> tuple[tuple[Any, ...], ...]:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("PRAGMA legacy_alter_table=ON")
        for migration in SQLiteStateRepository(Path(":memory:"))._load_migrations():
            connection.executescript(migration.sql)
        return _schema(connection)
    finally:
        connection.close()


def verify_database(
    repository: SQLiteStateRepository, connection: sqlite3.Connection
) -> None:
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version < 41:
        if _schema(connection):
            raise StateStoreError("legacy database contains unversioned long authority")
    elif _schema(connection) != _expected_schema():
        raise StateStoreError("long provenance schema is incompatible")
    for row in connection.execute(
        "SELECT execution_id FROM distillation_execution_checkpoints WHERE execution_id LIKE 'distillation:long-timed%'"
    ):
        verify_execution(repository, connection, row[0])
    for row in connection.execute(
        "SELECT revision_id FROM intelligence_revisions WHERE revision_id LIKE 'revision:distillation:distillation:long-timed%'"
    ):
        raise StateStoreError("long revision authority is not enabled")
    if version >= 41:
        for table in (PROOFS, RECEIPTS):
            for row in connection.execute(f"SELECT execution_id FROM {table}"):
                verify_execution(repository, connection, row[0])


def verify_receipt_payload(
    connection: sqlite3.Connection, proof: dict[str, Any], receipt: dict[str, Any]
) -> None:
    """Final storage consistency only; never a model/admission capability.

    Called after source proof verification. The WAIT-only reader still refuses
    result authority even when every representation and observation is coherent.
    """
    from youtube_intel.long_card_canonical import canonicalize_long_card
    from youtube_intel.long_grounding_codec import decode_output

    if (
        receipt["receipt_version"] != "long-timed-completion-receipt-v1"
        or receipt["execution_id"] != proof["execution_id"]
        or receipt["proof_hash"] != proof["proof_hash"]
        or receipt["receipt_hash"]
        != digest({k: v for k, v in receipt.items() if k != "receipt_hash"})
    ):
        raise StateStoreError("long receipt identity/hash differs")
    for wire_key, hash_key in (
        ("public_wire", "public_hash"),
        ("decoded_wire", "decoded_hash"),
        ("completion_json", "completion_hash"),
    ):
        wire, observed_hash = receipt[wire_key], receipt[hash_key]
        if (wire is None) != (observed_hash is None) or (
            wire is not None
            and (
                not isinstance(wire, str)
                or hashlib.sha256(wire.encode()).hexdigest() != observed_hash
            )
        ):
            raise StateStoreError("long receipt wire/hash differs")
    metadata = loads(receipt["completion_json"])
    if set(metadata) != {
        "done",
        "done_reason",
        "actual_provider",
        "actual_model",
        "request_hash",
        "input_tokens",
        "output_tokens",
        "cost_microunits",
        "duration_ms",
        "public_state",
    }:
        raise StateStoreError("long completion metadata fields differ")
    if (metadata["done"] is not None and type(metadata["done"]) is not bool) or (
        metadata["done_reason"] is not None and type(metadata["done_reason"]) is not str
    ):
        raise StateStoreError("long completion observation types differ")
    for key in ("input_tokens", "output_tokens", "cost_microunits", "duration_ms"):
        value = metadata[key]
        if value is not None and (
            type(value) is not int or not 0 <= value <= 2**63 - 1
        ):
            raise StateStoreError("long completion usage observation is unreliable")
    if (metadata["input_tokens"] is None) != (metadata["output_tokens"] is None):
        raise StateStoreError("long completion token observations are unpaired")
    if metadata["request_hash"] != proof["request_hash"]:
        raise StateStoreError("long completion request differs")
    checkpoint = _row(
        connection,
        "distillation_execution_checkpoints",
        "execution_id",
        proof["execution_id"],
    )
    kind = receipt["result_kind"]
    if kind not in {"INTELLIGENCE", "NO_NEW_INTELLIGENCE", "REJECTED"}:
        raise StateStoreError("long completion branch is unknown")
    if kind != "REJECTED" and (
        metadata["done"] is not True
        or metadata["done_reason"] != "stop"
        or metadata["actual_provider"] != checkpoint["selected_provider"]
        or metadata["actual_model"] != checkpoint["selected_model"]
    ):
        raise StateStoreError(
            "long completed result has incomplete/foreign observations"
        )
    if receipt["public_wire"] is None:
        if (
            metadata["public_state"] not in {"ABSENT", "OVERSIZE"}
            or receipt["decoded_wire"] is not None
            or kind != "REJECTED"
        ):
            raise StateStoreError("long missing public output is inconsistent")
    elif metadata["public_state"] != "PRESENT":
        raise StateStoreError("long public output presence differs")
    if receipt["decoded_wire"] is not None:
        side = loads(proof["semantic_snapshot_wire"])
        decoded = decode_output(
            receipt["public_wire"].encode(),
            EncodedGrounding(side["codec"]["canonical_wire"].encode()),
        )
        if (
            decoded.decoded_wire.decode() != receipt["decoded_wire"]
            or decoded.decoded_hash != receipt["decoded_hash"]
        ):
            raise StateStoreError("long public/decoded output association differs")
        decoded_value = loads(receipt["decoded_wire"])
        if kind != "REJECTED" and decoded_value["result"] != kind:
            raise StateStoreError("long decoded result branch differs")
    elif kind != "REJECTED":
        raise StateStoreError("long completed output has no strict decoded wire")
    zero = kind == "NO_NEW_INTELLIGENCE"
    authority = _row(
        connection,
        "distillation_no_new_intelligence_results"
        if zero
        else "distillation_resource_usage",
        "execution_id",
        proof["execution_id"],
    )
    for key in (
        "actual_provider",
        "actual_model",
        "input_tokens",
        "output_tokens",
        "cost_microunits",
        "duration_ms",
    ):
        if authority[key] != metadata[key]:
            raise StateStoreError("long receipt and observed usage authority differ")
    if authority["created_at"] != receipt["created_at"] or any(
        authority[k] != checkpoint[k]
        for k in ("source_id", "video_id", "reason", "use_case", "budget_state")
    ):
        raise StateStoreError("long completion ledger context differs")
    if zero:
        ids = sorted(
            e["evidence_id"]
            for e in loads(proof["semantic_snapshot_wire"])["value"]["evidence"]
        )
        encoded_ids = json.dumps(ids, separators=(",", ":"))
        if (
            receipt["usage_execution_id"] is not None
            or receipt["no_new_execution_id"] != proof["execution_id"]
            or authority["evidence_ids_json"] != encoded_ids
            or authority["evidence_set_hash"]
            != hashlib.sha256(encoded_ids.encode()).hexdigest()
            or checkpoint["status"] != "PENDING"
            or checkpoint["invocation_count"] != 1
            or connection.execute(
                "SELECT 1 FROM distillation_resource_usage WHERE execution_id=?",
                (proof["execution_id"],),
            ).fetchone()
        ):
            raise StateStoreError("long zero result/sidecar closure differs")
    elif (
        receipt["usage_execution_id"] != proof["execution_id"]
        or authority["status"] != receipt["terminal"]
        or checkpoint["status"] != receipt["terminal"]
        or authority["invocation_count"] != 1
    ):
        raise StateStoreError("long physical usage closure differs")
    if kind == "INTELLIGENCE":
        projected = canonicalize_long_card(receipt["decoded_wire"].encode())
        revision = _row(
            connection, "intelligence_revisions", "revision_id", receipt["revision_id"]
        )
        card = _row(
            connection, "distillation_cards", "revision_id", receipt["revision_id"]
        )
        value = loads(receipt["decoded_wire"])
        if (
            receipt["admitted_content_hash"] != projected.content_hash
            or revision["content_hash"] != projected.content_hash
            or revision["claim_kind"] != value["claim_kind"]
            or card["core_conclusion"] != value["core_conclusion"]
            or any(
                json.loads(card[k + "_json"]) != value[k]
                for k in (
                    "user_relevant_information",
                    "important_new_information",
                    "meaningful_details",
                    "filtered_noise",
                )
            )
            or any(
                checkpoint[k] != receipt[k] for k in ("intelligence_id", "revision_id")
            )
        ):
            raise StateStoreError("long canonical card/revision association differs")
