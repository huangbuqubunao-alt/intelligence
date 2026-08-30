"""Provider-aware Deep Analysis persistence and exact-cache lookup boundary."""

from __future__ import annotations

import json
import sqlite3
import weakref
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
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
from youtube_intel.deep_analysis_runtime import (
    DeepAnalysisResponseMetadataV1,
    _capture_trusted_success_for_persistence,
    _extract_payload,
    _grounded_in_registry,
    _kg2_valid,
    _language_valid,
    _matches_early_dispatch_binding,
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


def _model_json(value: BaseModel) -> str:
    return _json(value.model_dump(mode="python", by_alias=True))


class DeepAnalysisPersistenceStore:
    """Append-only writer and integrity-verifying exact cache reader."""

    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository

    def persist_trusted_deep_analysis_success(
        self, *, success: object, now: datetime
    ) -> VerifiedPersistedDeepAnalysisRead:
        material = _capture_trusted_success_for_persistence(success)
        if material is None or type(success) is not TrustedDeepAnalysisSuccess:
            raise DeepAnalysisPersistenceError(
                "persistence requires runtime-verified success"
            )
        envelope = material.envelope
        response = material.response
        trusted = success
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
            existing = (
                None
                if cache_identity is None
                else connection.execute(
                    "SELECT result_identity, content_identity FROM deep_analysis_persisted_results WHERE cache_identity = ?",
                    (cache_identity.identity,),
                ).fetchone()
            )
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
                return found
            columns = ", ".join(values)
            placeholders = ", ".join(f":{key}" for key in values)
            connection.execute(
                f"INSERT INTO deep_analysis_persisted_results ({columns}) VALUES ({placeholders})",
                values,
            )
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

    @staticmethod
    def _verify_row(row: sqlite3.Row) -> VerifiedPersistedDeepAnalysisRead:
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
            content = KnowledgeContent.model_validate(
                _load_json(row["knowledge_content_json"])
            )
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
        if (
            not isinstance(extracted, dict)
            or KnowledgeContent.model_validate(extracted) != content
        ):
            raise DeepAnalysisPersistenceError(
                "KnowledgeContent does not match response"
            )
        content_identity = dacs1_sha256(
            {
                "schema_version": "trusted-deep-analysis-content-v1",
                "content": content.model_dump(mode="json"),
            }
        )
        if (
            content_identity != row["content_identity"]
            or not _grounded_in_registry(content, registry)
            or not _kg2_valid(content)
            or not _language_valid(content, request.output_language)
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
            evidence_registry=registry,
            request_projection=request,
            execution_profile=execution,
            validation_policy=policy,
        )
        _record_verified_read(verified)
        return verified
