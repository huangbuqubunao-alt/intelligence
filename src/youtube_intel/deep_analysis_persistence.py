"""Provider-aware Deep Analysis persistence and exact-cache lookup boundary."""

from __future__ import annotations

import json
import sqlite3
import weakref
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from youtube_intel.deep_analysis_contracts import (
    CanonicalDeepAnalysisInputV1,
    ContextBudgetProfileV1,
    DeepAnalysisCacheIdentityV1,
    DeepAnalysisDispatchEnvelopeV1,
    DeepAnalysisExecutionProfileV1,
    DeepAnalysisFallbackAttemptProvenanceV1,
    DeepAnalysisPayloadScope,
    DeepAnalysisRequestProjectionV1,
    DeepAnalysisValidationPolicyIdentityV1,
    PayloadConsentIdentityV1,
    SelectedEvidenceProjectionV1,
    TrustedDeepAnalysisSuccess,
    UntrustedDeepAnalysisResponseV1,
    dacs1_sha256,
)
from youtube_intel.deep_analysis_evidence import resolve_deep_analysis_authority
from youtube_intel.deep_analysis_phase1b_contract import (
    PHASE_1B_MODEL_SCHEMA,
    PHASE_1B_PERSISTENCE_VERSION,
    PHASE_1B_PROMPT_IDENTITY,
    PHASE_1B_VALIDATION_POLICY,
    DeepAnalysisDurableResult,
    DeepAnalysisPhase1BModelOutput,
    durable_compatibility_content,
)
from youtube_intel.deep_analysis_runtime import (
    DeepAnalysisResponseMetadataV1,
    _capture_trusted_success_for_persistence,
    _extract_payload,
    _grounded_in_registry,
    _kg2_valid,
    _language_valid,
    _matches_early_dispatch_binding,
    _single_attempt_provenance,
)
from youtube_intel.domain import EvidenceRegistry, KnowledgeContent
from youtube_intel.state import IntegrityConflict, StateStoreError, format_utc_datetime

if TYPE_CHECKING:
    from youtube_intel.state import SQLiteStateRepository


class DeepAnalysisPersistenceError(StateStoreError):
    """A Deep Analysis row is incomplete, altered, or not runtime-admitted."""


@dataclass(frozen=True)
class VerifiedPersistedDeepAnalysisRead:
    """A revalidated persisted result; intentionally not a runtime success."""

    result_identity: str
    cache_identity: str | None
    content_identity: str
    content: KnowledgeContent
    canonical_input: CanonicalDeepAnalysisInputV1
    evidence_registry: EvidenceRegistry
    request_projection: DeepAnalysisRequestProjectionV1
    execution_profile: DeepAnalysisExecutionProfileV1
    validation_policy: DeepAnalysisValidationPolicyIdentityV1
    #: Authoritative persisted timestamps. These come from the durable row, so a
    #: read or restart can never make an old result look newly generated.
    created_at: datetime
    validated_at: datetime
    durable_result: DeepAnalysisDurableResult | None = None


#: Phase-1A results are persisted under this request prompt identity. It is the
#: unambiguous, durable discriminator used to keep Phase-1A results out of
#: trusted Evidence-bearing projections. See :func:`is_phase_1a_result`.
PHASE_1A_PROMPT_IDENTITY = "v1x-content-deep-analysis-phase1a-prompt-v1"


def is_phase_1a_result(source: object) -> bool:
    """Whether one verified Deep Analysis read is a Phase-1A transitional result.

    Phase 1A has not yet converged transient candidate refs onto durable
    ``evidence.evidence_id``. Its persisted results therefore carry candidate
    refs, and must never be treated as trusted Evidence-bearing authority.

    The state is derived from the durable persisted request projection rather
    than a caller-supplied flag, so it survives restart and cannot be forged by
    the caller. It is intentionally fail-closed: anything not positively
    identified as a later, Evidence-converged contract stays ineligible.
    """

    if type(source) is not VerifiedPersistedDeepAnalysisRead:
        return False
    projection = source.request_projection
    if projection.prompt_identity != PHASE_1A_PROMPT_IDENTITY:
        return False
    # The five-concept provider-facing schema is the second, independent signal.
    return projection.knowledge_content_schema_identity == (
        "v1x-content-deep-analysis-model-output-v1"
    )


def require_trusted_note_eligibility(source: object) -> None:
    """Fail closed for Phase-1A results used as trusted Note / export authority.

    Phase-1A Deep Analysis results may be persisted, read after restart, and
    shown in the Content panel. They may **not** act as a trusted Note V2
    source, an Obsidian source, an Evidence-bearing export source, or any other
    durable citation authority, because their Evidence refs are transitional
    candidate refs rather than durable Evidence identity.
    """

    if type(source) is VerifiedPersistedDeepAnalysisRead and (
        is_phase_1a_result(source)
        or source.canonical_input.operation == "content-deep-analysis"
        and source.durable_result is None
    ):
        raise DeepAnalysisPersistenceError(
            "Phase-1A Deep Analysis results are not eligible as trusted "
            "Evidence-bearing Note or export authority until Phase-1B "
            "durable-Evidence convergence is complete"
        )
    if type(source) is VerifiedPersistedDeepAnalysisRead and source.durable_result is not None and not verify_persisted_deep_analysis_read(source):
        raise DeepAnalysisPersistenceError("durable Note eligibility requires a verified read")


_verified_reads: dict[
    int,
    tuple[weakref.ReferenceType[VerifiedPersistedDeepAnalysisRead], str],
] = {}


def _read_snapshot(value: VerifiedPersistedDeepAnalysisRead) -> str:
    return dacs1_sha256(
        {
            "schema_version": "verified-persisted-deep-analysis-read-v1",
            "result_identity": value.result_identity,
            "cache_identity": value.cache_identity,
            "content_identity": value.content_identity,
            "content": _model_json(value.content),
            "evidence_registry": _model_json(value.evidence_registry),
            "canonical_input": _model_json(value.canonical_input),
            "request_projection": _model_json(value.request_projection),
            "execution_profile": _model_json(value.execution_profile),
            "validation_policy": _model_json(value.validation_policy),
            "created_at": format_utc_datetime(value.created_at),
            "validated_at": format_utc_datetime(value.validated_at),
            "durable_result": None if value.durable_result is None else _model_json(value.durable_result),
        }
    )


def _record_verified_read(value: VerifiedPersistedDeepAnalysisRead) -> None:
    key = id(value)

    def remove(
        _reference: weakref.ReferenceType[VerifiedPersistedDeepAnalysisRead],
    ) -> None:
        _verified_reads.pop(key, None)

    _verified_reads[key] = (weakref.ref(value, remove), _read_snapshot(value))


def verify_persisted_deep_analysis_read(value: object) -> bool:
    """Return true only for an unchanged result returned by the verified reader."""

    if type(value) is not VerifiedPersistedDeepAnalysisRead:
        return False
    recorded = _verified_reads.get(id(value))
    if recorded is None or recorded[0]() is not value:
        return False
    return recorded[1] == _read_snapshot(value)


def _json(value: object) -> str:
    def thaw(item: object) -> object:
        if item is None or isinstance(item, (str, int, float, bool)):
            return item
        if isinstance(item, Mapping):
            return {str(key): thaw(value) for key, value in item.items()}
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            return [thaw(value) for value in item]
        if isinstance(item, BaseModel):
            return thaw(item.model_dump(mode="python"))
        raise TypeError(f"non-JSON persistence value: {type(item).__name__}")

    return json.dumps(
        thaw(value), separators=(",", ":"), sort_keys=True, ensure_ascii=False
    )


def _load_json(value: object) -> object:
    try:
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError) as error:
        raise DeepAnalysisPersistenceError("persisted JSON is invalid") from error


def _parse_persisted_timestamp(value: object) -> datetime:
    """Parse one persisted UTC timestamp, rejecting anything ambiguous.

    Trusted Deep Analysis timestamps must be timezone-aware. A timezone-free
    value is ambiguous rather than implicitly UTC, so it fails verification:

        2035-06-07T12:34:56Z          -> valid
        2035-06-07T12:34:56+00:00     -> valid
        2035-06-07T12:34:56           -> invalid

    On corruption this never substitutes the current time and never assumes UTC,
    so no forged ``generated_at`` can be served.
    """

    text = str(value).strip()
    if not text:
        raise DeepAnalysisPersistenceError("persisted timestamp is empty")
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise DeepAnalysisPersistenceError(
            "persisted timestamp is malformed"
        ) from error
    if parsed.tzinfo is None:
        raise DeepAnalysisPersistenceError(
            "persisted timestamp is not timezone-aware"
        )
    return parsed.astimezone(UTC)


def _model_json(value: BaseModel) -> str:
    return _json(value.model_dump(mode="python", by_alias=True))


def _durable_authority_identity(values: Mapping[str, object]) -> str:
    return dacs1_sha256({
        "schema_version": PHASE_1B_PERSISTENCE_VERSION,
        **{key: values[key] for key in (
            "result_identity", "content_identity", "validation_policy_identity",
            "knowledge_content_json", "created_at", "validated_at",
        )},
    })


class DeepAnalysisPersistenceStore:
    """Append-only writer and integrity-verifying exact cache reader."""

    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository

    def persist_trusted_deep_analysis_success(
        self,
        *,
        success: object,
        now: datetime,
        promote_current_summary: bool = True,
    ) -> VerifiedPersistedDeepAnalysisRead:
        """Persist one runtime-admitted success and return its verified read.

        ``promote_current_summary`` exists for the V1.x Content-level Deep
        Analysis action.  Deep Analysis is a distinct product capability and must
        never replace or rewrite Summary / Video Notes authority, so the V1.x
        caller passes ``False`` and the result stays a Deep Analysis record only.
        The default preserves the frozen Summary cutover behavior.
        """
        material = _capture_trusted_success_for_persistence(success)
        if material is None or type(success) is not TrustedDeepAnalysisSuccess:
            raise DeepAnalysisPersistenceError(
                "persistence requires runtime-verified success"
            )
        envelope = material.envelope
        response = material.response
        trusted = success
        phase1b = isinstance(material.content, DeepAnalysisPhase1BModelOutput)
        if phase1b and promote_current_summary:
            raise DeepAnalysisPersistenceError("Content Deep Analysis cannot promote Summary authority")
        cache_identity = material.cache_decision.cache_identity
        if response.response_metadata is None:
            raise DeepAnalysisPersistenceError(
                "runtime success lacks response metadata"
            )
        payload = response.structured_payload
        payload_kind = "BYTES" if isinstance(payload, bytes) else "JSON"
        payload_bytes = (
            payload if isinstance(payload, bytes) else _json(payload).encode("utf-8")
        )
        model = envelope.execution_profile.model_selection
        values: dict[str, object] = {
            "result_identity": trusted.provenance_identity,
            "cache_identity": None
            if cache_identity is None
            else cache_identity.identity,
            "cache_eligibility": material.cache_decision.eligibility.value,
            "a1_identity": envelope.a1_identity,
            "a2_identity": envelope.a2_identity,
            "a3_identity": envelope.a3_identity,
            "validation_policy_identity": material.validation_policy.identity,
            "validation_policy_json": _json(
                material.validation_policy.model_dump(mode="json")
            ),
            "provider_kind": envelope.execution_profile.provider_kind.value,
            "provider_id": envelope.execution_profile.provider_id,
            "adapter_identity": envelope.execution_profile.adapter_identity,
            "adapter_version": envelope.execution_profile.adapter_version,
            "endpoint_deployment_profile_identity": envelope.execution_profile.endpoint_deployment_profile_identity,
            "model_id": model.model_id,
            "model_identity_class": model.identity_class.value,
            "model_resolved_revision": model.resolved_revision,
            "payload_scope": envelope.request_projection.payload_scope.value,
            "scoring_request_hash": envelope.canonical_input.scoring_request_hash,
            "scoring_success_provenance": envelope.canonical_input.scoring_success_provenance,
            "evidence_registry_identity": envelope.canonical_input.evidence_registry_identity,
            "content_identity": trusted.content_identity,
            "provider_envelope_identity": response.provider_envelope_identity,
            "structured_payload_identity": response.structured_payload_identity,
            "provenance_identity": trusted.provenance_identity,
            "canonical_input_json": _json(
                envelope.canonical_input.model_dump(mode="json")
            ),
            "evidence_registry_json": _json(
                material.evidence_registry.model_dump(mode="json")
            ),
            "authorized_payload_json": _json(
                envelope.request_projection.authorized_payload.model_dump(mode="json")
            ),
            "request_projection_json": _model_json(envelope.request_projection),
            "execution_profile_json": _model_json(envelope.execution_profile),
            "payload_consent_json": _json(
                envelope.payload_consent.model_dump(mode="json")
            ),
            "context_budget_json": _json(
                envelope.context_budget_profile.model_dump(mode="json")
            ),
            "response_metadata_json": _json(response.response_metadata),
            "knowledge_content_json": _json(material.content.model_dump(mode="json")),
            "fallback_attempts_json": _json(
                [x.model_dump(mode="json") for x in material.attempt_history]
            ),
            "fallback_policy_identity": envelope.fallback_policy_identity,
            "timeout_profile_identity": envelope.timeout_profile_identity,
            "response_envelope_bytes": response.provider_envelope_bytes,
            "structured_payload_kind": payload_kind,
            "structured_payload_bytes": payload_bytes,
            "created_at": format_utc_datetime(now),
            "validated_at": format_utc_datetime(now),
        }
        connection = self._repository._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT result_identity, content_identity FROM deep_analysis_persisted_results "
                "WHERE result_identity = ? OR cache_identity = ?",
                (trusted.provenance_identity, None if cache_identity is None else cache_identity.identity),
            ).fetchone()
            if existing is not None:
                if existing["content_identity"] != trusted.content_identity:
                    raise IntegrityConflict(
                        "same cache identity has conflicting KnowledgeContent"
                    )
                connection.execute("ROLLBACK")
                found = self.read_persisted_deep_analysis_result(
                    result_identity=str(existing["result_identity"])
                )
                if found is None:
                    raise DeepAnalysisPersistenceError(
                        "existing cache row fails verification"
                    )
                if promote_current_summary:
                    self._promote_current_content_summary(found, now=now)
                return found
            if phase1b:
                if material.validation_policy != PHASE_1B_VALIDATION_POLICY:
                    raise DeepAnalysisPersistenceError("unsupported durable validation policy")
                assert isinstance(material.content, DeepAnalysisPhase1BModelOutput)
                durable, _ = resolve_deep_analysis_authority(
                    connection=connection, repository=self._repository,
                    canonical=envelope.canonical_input, request=envelope.request_projection,
                    registry=material.evidence_registry, output=material.content, promote_at=now,
                )
                values["knowledge_content_json"] = _model_json(durable)
                values["persistence_version"] = PHASE_1B_PERSISTENCE_VERSION
                values["durable_authority_identity"] = _durable_authority_identity(values)
            columns = ", ".join(values)
            placeholders = ", ".join(f":{key}" for key in values)
            connection.execute(
                f"INSERT INTO deep_analysis_persisted_results ({columns}) VALUES ({placeholders})",
                values,
            )
            if phase1b:
                ids = {ref for claim in durable.claims for ref in claim.evidence_refs}
                connection.executemany(
                    "INSERT INTO deep_analysis_evidence (result_identity, evidence_id, created_at) VALUES (?, ?, ?)",
                    [(trusted.provenance_identity, eid, format_utc_datetime(now)) for eid in sorted(ids)],
                )
                row = connection.execute("SELECT * FROM deep_analysis_persisted_results WHERE result_identity = ?", (trusted.provenance_identity,)).fetchone()
                if row is None:
                    raise DeepAnalysisPersistenceError("trusted result did not persist")
                self._verify_row(row, connection)
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        result = self.read_persisted_deep_analysis_result(
            result_identity=trusted.provenance_identity
        )
        if result is None:
            raise DeepAnalysisPersistenceError("new cache row fails verification")
        if promote_current_summary:
            self._promote_current_content_summary(result, now=now)
        return result

    def _promote_current_content_summary(
        self, result: VerifiedPersistedDeepAnalysisRead, *, now: datetime
    ) -> None:
        """Promote only a still-verified persisted result to current Summary authority."""

        if not verify_persisted_deep_analysis_read(result):
            raise DeepAnalysisPersistenceError(
                "current Summary promotion requires a verified persisted result"
            )
        if result.durable_result is not None or is_phase_1a_result(result):
            raise DeepAnalysisPersistenceError("Content Deep Analysis cannot become Summary authority")
        video_id = result.canonical_input.video_identity
        if not video_id.strip():
            raise DeepAnalysisPersistenceError(
                "current Summary promotion requires a video identity"
            )
        connection = self._repository._connect()
        try:
            with connection:
                content = connection.execute(
                    "SELECT 1 FROM videos WHERE video_id = ?", (video_id,)
                ).fetchone()
                if content is None:
                    raise DeepAnalysisPersistenceError(
                        "current Summary promotion requires existing Content"
                    )
                connection.execute(
                    "INSERT INTO current_content_summaries "
                    "(video_id, result_identity, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(video_id) DO UPDATE SET "
                    "result_identity=excluded.result_identity, "
                    "analysis_artifact_id=NULL, output_language=NULL, "
                    "updated_at=excluded.updated_at",
                    (
                        video_id,
                        result.result_identity,
                        format_utc_datetime(now),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise DeepAnalysisPersistenceError(
                "current Summary pointer violates persistence integrity"
            ) from error

    def read_deep_analysis_result_for_content(
        self, *, video_id: str
    ) -> VerifiedPersistedDeepAnalysisRead | None:
        """Read the most recent verified Deep Analysis record for one Content.

        This is the V1.x Content-level Deep Analysis read seam.  It is
        deliberately independent of ``current_content_summaries``: Deep Analysis
        is a separate product capability and must not be read as, or write to,
        Summary / Video Notes authority.

        Selection is the newest ``validated_at``/``created_at`` row whose
        canonical input names this exact Content.  The winner is fully
        re-verified by the same integrity path used for every other read, and a
        row that fails verification is skipped rather than returned.
        """

        if not isinstance(video_id, str) or not video_id.strip():
            raise ValueError("video_id must be non-empty")
        connection = self._repository._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM deep_analysis_persisted_results "
                "WHERE CASE WHEN json_valid(canonical_input_json) THEN json_extract(canonical_input_json, '$.video_identity') END = ? "
                "ORDER BY validated_at DESC, created_at DESC, result_identity ASC",
                (video_id,),
            ).fetchall()
        finally:
            connection.close()
        for row in rows:
            try:
                result = self._verify_row(row)
            except DeepAnalysisPersistenceError:
                continue
            if result.canonical_input.video_identity == video_id:
                return result
        return None

    def read_current_content_summary_result(
        self, *, video_id: str
    ) -> VerifiedPersistedDeepAnalysisRead | None:
        """Read the explicit current Summary pointer and revalidate its target."""

        if not video_id.strip():
            raise ValueError("video_id must be non-empty")
        connection = self._repository._connect()
        try:
            row = connection.execute(
                "SELECT result_identity FROM current_content_summaries "
                "WHERE video_id = ?",
                (video_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        result = self.read_persisted_deep_analysis_result(
            result_identity=str(row["result_identity"])
        )
        if result is None:
            return None
        if result.canonical_input.video_identity != video_id:
            return None
        if result.durable_result is not None:
            return None
        return result

    def lookup_deep_analysis_cache(
        self, *, cache_identity: str
    ) -> VerifiedPersistedDeepAnalysisRead | None:
        if len(cache_identity) != 64 or any(
            char not in "0123456789abcdef" for char in cache_identity
        ):
            raise ValueError("cache identity must be a SHA-256 digest")
        connection = self._repository._connect()
        try:
            row = connection.execute(
                "SELECT result_identity FROM deep_analysis_persisted_results "
                "WHERE cache_identity = ? AND cache_eligibility = 'ELIGIBLE'",
                (cache_identity,),
            ).fetchone()
        finally:
            connection.close()
        return (
            None
            if row is None
            else self.read_persisted_deep_analysis_result(
                result_identity=str(row["result_identity"])
            )
        )

    def read_persisted_deep_analysis_result(
        self, *, result_identity: str
    ) -> VerifiedPersistedDeepAnalysisRead | None:
        connection = self._repository._connect()
        try:
            row = connection.execute(
                "SELECT * FROM deep_analysis_persisted_results WHERE result_identity = ?",
                (result_identity,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        try:
            return self._verify_row(row)
        except DeepAnalysisPersistenceError:
            return None

    def _verify_row(self, row: sqlite3.Row, connection: sqlite3.Connection | None = None) -> VerifiedPersistedDeepAnalysisRead:
        if connection is None:
            owned = self._repository._connect()
            try:
                owned.execute("BEGIN")
                fresh = owned.execute("SELECT * FROM deep_analysis_persisted_results WHERE result_identity = ?", (row["result_identity"],)).fetchone()
                if fresh is None:
                    raise DeepAnalysisPersistenceError("persisted result disappeared")
                return self._verify_row(fresh, owned)
            except DeepAnalysisPersistenceError:
                raise
            except Exception as error:
                # Corrupt encodings or structures must obey the same rejection
                # semantics as bad hashes, allowing an older verified result.
                raise DeepAnalysisPersistenceError("persisted record integrity failed") from error
            finally:
                owned.close()
        persistence_version = row["persistence_version"]
        if persistence_version not in {"deep-analysis-persistence-v1", PHASE_1B_PERSISTENCE_VERSION}:
            raise DeepAnalysisPersistenceError("unsupported persistence version")
        phase1b = persistence_version == PHASE_1B_PERSISTENCE_VERSION
        try:
            canonical_data = _load_json(row["canonical_input_json"])
            if not isinstance(canonical_data, dict):
                raise ValueError("canonical input is not an object")
            selected = canonical_data.get("selected_evidence")
            if not isinstance(selected, list):
                raise ValueError("selected evidence is invalid")
            canonical = CanonicalDeepAnalysisInputV1.model_construct(
                **{
                    **canonical_data,
                    "selected_evidence": tuple(
                        SelectedEvidenceProjectionV1.model_validate(item)
                        for item in selected
                    ),
                }
            )
            registry = EvidenceRegistry.model_validate(
                _load_json(row["evidence_registry_json"])
            )
            request = DeepAnalysisRequestProjectionV1.model_validate(
                _load_json(row["request_projection_json"])
            )
            execution = DeepAnalysisExecutionProfileV1.model_validate(
                _load_json(row["execution_profile_json"])
            )
            consent = PayloadConsentIdentityV1.model_validate(
                _load_json(row["payload_consent_json"])
            )
            context = ContextBudgetProfileV1.model_validate(
                _load_json(row["context_budget_json"])
            )
            policy = DeepAnalysisValidationPolicyIdentityV1.model_validate(
                _load_json(row["validation_policy_json"])
            )
            metadata_data = _load_json(row["response_metadata_json"])
            metadata = DeepAnalysisResponseMetadataV1.model_validate(metadata_data)
            persisted_content = _load_json(row["knowledge_content_json"])
            attempts_data = _load_json(row["fallback_attempts_json"])
            if not isinstance(attempts_data, list):
                raise ValueError("attempt history is invalid")
            attempts = tuple(
                DeepAnalysisFallbackAttemptProvenanceV1.model_validate(item)
                for item in attempts_data
            )
        except Exception as error:
            raise DeepAnalysisPersistenceError(
                "persisted record is incomplete"
            ) from error
        if not (
            canonical.a1_identity == row["a1_identity"]
            and request.a2_identity == row["a2_identity"]
            and execution.a3_identity == row["a3_identity"]
            and request.authorized_payload.model_dump(mode="json")
            == _load_json(row["authorized_payload_json"])
            and canonical.evidence_registry_identity
            == row["evidence_registry_identity"]
            and canonical.scoring_request_hash == row["scoring_request_hash"]
            and canonical.scoring_success_provenance
            == row["scoring_success_provenance"]
            and request.payload_scope.value == row["payload_scope"]
            and consent.identity == request.payload_consent_identity
            and context.authority_identity == execution.context_authority_identity
            and policy.identity == row["validation_policy_identity"]
            and execution.provider_kind.value == row["provider_kind"]
            and execution.provider_id == row["provider_id"]
            and execution.adapter_identity == row["adapter_identity"]
            and execution.adapter_version == row["adapter_version"]
            and execution.endpoint_deployment_profile_identity
            == row["endpoint_deployment_profile_identity"]
            and execution.model_selection.model_id == row["model_id"]
            and execution.model_selection.identity_class.value
            == row["model_identity_class"]
            and execution.model_selection.resolved_revision
            == row["model_resolved_revision"]
        ):
            raise DeepAnalysisPersistenceError("persisted semantic identities disagree")
        if (
            request.payload_scope is DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY
            and request.authorized_payload.transcript_text is not None
        ):
            raise DeepAnalysisPersistenceError(
                "selected-evidence record contains transcript"
            )
        policy_identity = row["validation_policy_identity"]
        if not isinstance(policy_identity, str) or len(policy_identity) != 64:
            raise DeepAnalysisPersistenceError("validation policy identity is invalid")
        payload_bytes = row["structured_payload_bytes"]
        if not isinstance(payload_bytes, bytes):
            raise DeepAnalysisPersistenceError("structured payload is invalid")
        structured: bytes | object = (
            payload_bytes
            if row["structured_payload_kind"] == "BYTES"
            else _load_json(payload_bytes.decode("utf-8"))
        )
        response = UntrustedDeepAnalysisResponseV1(
            schema_version="untrusted-deep-analysis-response-v1",
            expected_dispatch_identity=metadata.dispatch_identity,
            provider_envelope_bytes=row["response_envelope_bytes"],
            structured_payload=structured,
            structured_output_mode=request.structured_output.mode,
            delivery_certainty="CONFIRMED",
            response_metadata=metadata_data,
        )
        envelope = DeepAnalysisDispatchEnvelopeV1(
            schema_version="deep-analysis-dispatch-envelope-v1",
            canonical_input=canonical,
            request_projection=request,
            execution_profile=execution,
            payload_consent=consent,
            context_budget_profile=context,
            timeout_profile_identity=row["timeout_profile_identity"],
            fallback_policy_identity=row["fallback_policy_identity"],
            prompt_identity=request.prompt_identity,
            schema_identity=request.knowledge_content_schema_identity,
        )
        if (
            not _matches_early_dispatch_binding(envelope, response, metadata)
            or metadata.validation_policy_identity != policy.identity
        ):
            raise DeepAnalysisPersistenceError(
                "response does not bind to the persisted dispatch"
            )
        extracted = _extract_payload(envelope, metadata, response)
        durable_result = None
        try:
            admitted_content: KnowledgeContent | DeepAnalysisPhase1BModelOutput
            if phase1b:
                if (request.prompt_identity != PHASE_1B_PROMPT_IDENTITY
                    or request.knowledge_content_schema_identity != PHASE_1B_MODEL_SCHEMA
                    or policy != PHASE_1B_VALIDATION_POLICY):
                    raise ValueError("unsupported Phase-1B schema/policy")
                admitted_content = DeepAnalysisPhase1BModelOutput.model_validate(extracted)
                durable_result = DeepAnalysisDurableResult.model_validate(persisted_content)
                expected, durable_registry = resolve_deep_analysis_authority(
                    connection=connection, repository=self._repository,
                    canonical=canonical, request=request, registry=registry, output=admitted_content,
                )
                members = connection.execute("SELECT evidence_id, created_at FROM deep_analysis_evidence WHERE result_identity = ?", (row["result_identity"],)).fetchall()
                if (durable_result != expected
                    or {m["evidence_id"] for m in members} != {ref for claim in expected.claims for ref in claim.evidence_refs}
                    or len(members) != len({ref for claim in expected.claims for ref in claim.evidence_refs})
                    or _parse_persisted_timestamp(row["validated_at"]) != _parse_persisted_timestamp(row["created_at"])
                    or any(m["created_at"] != row["created_at"] for m in members)
                    or row["durable_authority_identity"] != _durable_authority_identity(dict(row))):
                    raise ValueError("durable claim/membership authority mismatch")
                content = durable_compatibility_content(durable_result)
            else:
                if request.knowledge_content_schema_identity == PHASE_1B_MODEL_SCHEMA or request.prompt_identity == PHASE_1B_PROMPT_IDENTITY:
                    raise ValueError("durable schema cannot be a legacy row")
                if row["durable_authority_identity"] is not None or connection.execute("SELECT 1 FROM deep_analysis_evidence WHERE result_identity = ?", (row["result_identity"],)).fetchone():
                    raise ValueError("legacy result cannot acquire durable memberships")
                admitted_content = KnowledgeContent.model_validate(extracted)
                content = KnowledgeContent.model_validate(persisted_content)
                if admitted_content != content:
                    raise ValueError("KnowledgeContent does not match response")
        except Exception as error:
            raise DeepAnalysisPersistenceError("persisted result authority failed") from error
        content_identity = dacs1_sha256(
            {
                "schema_version": "trusted-deep-analysis-content-v1",
                "content": admitted_content.model_dump(mode="json"),
            }
        )
        if (
            content_identity != row["content_identity"]
            or not _grounded_in_registry(admitted_content, registry)
            or not _kg2_valid(admitted_content)
            or not _language_valid(admitted_content, request.output_language)
        ):
            raise DeepAnalysisPersistenceError("KnowledgeContent validation failed")
        if (
            response.provider_envelope_identity != row["provider_envelope_identity"]
            or response.structured_payload_identity
            != row["structured_payload_identity"]
        ):
            raise DeepAnalysisPersistenceError("response identity failed")
        expected_provenance_identity = dacs1_sha256(
            {
                "schema_version": "trusted-deep-analysis-provenance-v1",
                "A1": canonical.a1_identity,
                "A2": request.a2_identity,
                "A3": execution.a3_identity,
                "scoring_request_hash": canonical.scoring_request_hash,
                "scoring_success_provenance": canonical.scoring_success_provenance,
                "evidence_registry_identity": canonical.evidence_registry_identity,
                "payload_scope": request.payload_scope.value,
                "payload_consent_identity": consent.identity,
                "provider_envelope_identity": response.provider_envelope_identity,
                "payload_identity": response.structured_payload_identity,
                "validation_policy_identity": policy.identity,
                "content_identity": content_identity,
            }
        )
        if (
            row["provenance_identity"] != expected_provenance_identity
            or row["result_identity"] != expected_provenance_identity
        ):
            raise DeepAnalysisPersistenceError("persisted provenance identity failed")
        if len(attempts) != 1 or any(
            (
                attempts[0].a1_identity != canonical.a1_identity,
                attempts[0].a2_identity != request.a2_identity,
                attempts[0].a3_identity != execution.a3_identity,
            )
        ):
            raise DeepAnalysisPersistenceError("attempt provenance failed")
        if phase1b and attempts != (_single_attempt_provenance(envelope, response),):
            raise DeepAnalysisPersistenceError("durable attempt provenance failed replay")
        cache = DeepAnalysisCacheIdentityV1(
            schema_version="deep-analysis-cache-identity-v1",
            a1_identity=canonical.a1_identity,
            a2_identity=request.a2_identity,
            a3_identity=execution.a3_identity,
            validation_policy_identity=policy_identity,
        )
        if row["cache_eligibility"] == "ELIGIBLE":
            if cache.identity != row["cache_identity"]:
                raise DeepAnalysisPersistenceError("cache identity failed")
            verified_cache_identity: str | None = cache.identity
        elif row["cache_eligibility"] == "INELIGIBLE_FLOATING_MODEL":
            if (
                row["cache_identity"] is not None
                or execution.model_selection.identity_class.value != "FLOATING"
            ):
                raise DeepAnalysisPersistenceError("floating cache eligibility failed")
            verified_cache_identity = None
        else:
            raise DeepAnalysisPersistenceError("unknown cache eligibility")
        verified = VerifiedPersistedDeepAnalysisRead(
            result_identity=row["result_identity"],
            cache_identity=verified_cache_identity,
            content_identity=content_identity,
            content=content,
            canonical_input=canonical,
            evidence_registry=durable_registry if phase1b else registry,
            request_projection=request,
            execution_profile=execution,
            validation_policy=policy,
            created_at=_parse_persisted_timestamp(row["created_at"]),
            validated_at=_parse_persisted_timestamp(row["validated_at"]),
            durable_result=durable_result,
        )
        _record_verified_read(verified)
        return verified
