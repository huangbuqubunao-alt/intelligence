"""TASK-016D provider-aware Deep Analysis persistence boundary."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.deep_analysis_contracts import (
    CanonicalDeepAnalysisInputV1,
    CredentialExecutionProfileIdentityV1,
    DeepAnalysisPayloadScope,
    PayloadConsentIdentityV1,
    PayloadConsentMode,
    TrustedDeepAnalysisSuccess,
    verify_trusted_deep_analysis_success,
)
from youtube_intel.deep_analysis_persistence import (
    DeepAnalysisPersistenceError,
    DeepAnalysisPersistenceStore,
    VerifiedPersistedDeepAnalysisRead,
)
from youtube_intel.deep_analysis_runtime import DeepAnalysisRuntime
from youtube_intel.domain import (
    EvidenceRegistry,
    EvidenceSource,
    KnowledgeEvidence,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.note_v2 import NoteV2Error, build_note_v2, render_note_v2
from youtube_intel.openai_deep_analysis import (
    OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE,
    OpenAIDeepAnalysisProviderAdapter,
    build_openai_reference_context_budget,
    build_openai_reference_execution_profile,
    build_openai_reference_request_projection,
)
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 8, 30, tzinfo=UTC)


def _trusted_success(
    *,
    video_id: str = "video-1",
    score: float = 8.0,
    public_description: str = "Selected evidence only.",
    verified_scoring_read: VerifiedScoringRead | None = None,
) -> TrustedDeepAnalysisSuccess:
    read = verified_scoring_read or VerifiedScoringRead(
        scoring_outcome=ScoringOutcome(
            result=ScoreResult(
                schema_version="score-result-v2",
                score=score,
                reason="This result contains a concrete useful explanation of the score.",
                topics=("workflow",),
                should_summarize=True,
                provider="scoring-provider",
                model="scoring-model",
                prompt_version="scoring-prompt-v2",
                request_hash="a" * 64,
                output_language="en",
            ),
            decision=ScoringDecision(
                threshold=7.0, final_should_summarize=True, model_disagrees=False
            ),
            call=ProviderCallMetadata(
                provider="scoring-provider",
                model="scoring-model",
                started_at=NOW,
                finished_at=NOW,
            ),
        ),
        video_id=video_id,
        scoring_job_id="job-1",
        scoring_success_provenance="PRIMARY",
    )
    canonical = CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
        verified_scoring_read=read,
        schema_version="canonical-deep-analysis-input-v1",
        operation="deep-analysis",
        input_schema_version="input-v1",
        video_identity=read.video_id,
        transcript_identity="transcript-1",
        transcript_language="en",
        transcript_normalization_version="normalized-v1",
        evidence_registry_identity="registry-v1",
        selected_evidence=(
            {
                "schema_version": "selected-evidence-projection-v1",
                "evidence_id": "e1",
                "source": "description",
                "excerpt": "Selected evidence only.",
            },
        ),
        selection_policy_identity="selection-v1",
        coverage_policy_identity="coverage-v1",
        coverage_complete=False,
        output_language="en",
        knowledge_content_schema_version="knowledge-v1",
        prompt_version="prompt-v1",
        operation_version="operation-v1",
    )
    runtime = DeepAnalysisRuntime()
    admitted = runtime.admit_verified_scoring_read(
        verified_scoring_read=read, canonical_input=canonical
    )
    consent = PayloadConsentIdentityV1(
        schema_version="payload-consent-identity-v1",
        consent_mode=PayloadConsentMode.CLOUD_EXPLICIT,
        authorization_record_identity="openai-test-consent-v1",
        named_provider_id="openai",
        provider_kind=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.provider_kind,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        allowed_model_constraint=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.model_id,
    )
    payload = runtime.authorize_payload(
        authoritative_input=admitted,
        evidence_registry=EvidenceRegistry(
            items=(
                KnowledgeEvidence(
                    evidence_id="e1",
                    source=EvidenceSource.DESCRIPTION,
                    excerpt="Selected evidence only.",
                    source_content_hash="d" * 64,
                ),
            )
        ),
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_consent=consent,
        video_title="Title",
        channel_name="Channel",
        published_at="2026-01-01T00:00:00Z",
        duration_seconds=42,
        source_language="en",
        public_description=public_description,
    )
    request = build_openai_reference_request_projection(
        canonical_input=canonical,
        authorized_payload=payload.payload,
        payload_consent=consent,
    )
    execution = build_openai_reference_execution_profile(
        request_projection=request,
        credential_execution_profile=CredentialExecutionProfileIdentityV1(
            schema_version="credential-execution-profile-v1",
            provider_id="openai",
            execution_profile_identity="b" * 64,
        ),
    )
    prepared = runtime.prepare_dispatch(
        authoritative_input=admitted,
        authorized_payload=payload,
        request_projection=request,
        execution_profile=execution,
        payload_consent=consent,
        context_budget_profile=build_openai_reference_context_budget(input_budget=1024),
        timeout_profile_identity=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.timeout_profile_identity,
        fallback_policy_identity="c" * 64,
    )
    content = {
        "one_sentence_summary": "This result contains a concrete useful explanation of the score.",
        "summary_evidence_ids": ["e1"],
        "why_it_matters": {
            "text": "This result contains a concrete useful explanation of the score.",
            "kind": "inference",
            "evidence_ids": ["e1"],
        },
        "core_points": [
            {
                "text": "This result contains a concrete useful explanation of the score.",
                "kind": "fact",
                "evidence_ids": ["e1"],
            }
        ],
        "knowledge_graph": {"topics": ["workflow"]},
    }
    response = OpenAIDeepAnalysisProviderAdapter(
        transport=lambda *_args: {
            "kind": "response",
            "response": {
                "id": "request-observational-only",
                "model": OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.model_id,
                "status": "completed",
                "output_text": __import__("json").dumps(content),
            },
        }
    ).dispatch(prepared_dispatch=prepared, credential="sk-task016-DO-NOT-PERSIST")
    result = runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=response
    )
    assert result.success is not None
    assert verify_trusted_deep_analysis_success(result.success)
    return result.success


def _seed_summary_content(repository: SQLiteStateRepository) -> None:
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT OR IGNORE INTO videos "
            "(video_id, channel_id, pipeline_status, pipeline_version, availability, discovered_at, updated_at) "
            "VALUES ('video-1', 'UC_TEST', 'DISCOVERED', 'fixture-v1', 'public', ?, ?)",
            (NOW.isoformat(), NOW.isoformat()),
        )
    finally:
        connection.close()


def test_fresh_database_has_provider_aware_persistence_schema(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")

    version = repository.initialize(now=NOW)

    assert version.version == 41
    store = DeepAnalysisPersistenceStore(repository)
    assert store.lookup_deep_analysis_cache(cache_identity="a" * 64) is None


def test_verified_persistence_promotes_one_explicit_current_summary_pointer(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    store = DeepAnalysisPersistenceStore(repository)

    persisted = store.persist_trusted_deep_analysis_success(
        success=_trusted_success(), now=NOW
    )

    current = store.read_current_content_summary_result(
        video_id=persisted.canonical_input.video_identity
    )
    assert current is not None
    assert current.result_identity == persisted.result_identity
    assert current.content == persisted.content


def test_tampered_current_summary_target_fails_closed_without_raw_fallback(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    store = DeepAnalysisPersistenceStore(repository)
    persisted = store.persist_trusted_deep_analysis_success(
        success=_trusted_success(), now=NOW
    )
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE deep_analysis_persisted_results "
            "SET knowledge_content_json = '{}' WHERE result_identity = ?",
            (persisted.result_identity,),
        )
    finally:
        connection.close()

    assert (
        store.read_current_content_summary_result(
            video_id=persisted.canonical_input.video_identity
        )
        is None
    )


def test_runtime_verified_success_persists_and_reloads_by_exact_cache_identity(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    success = _trusted_success()
    store = DeepAnalysisPersistenceStore(repository)

    persisted = store.persist_trusted_deep_analysis_success(success=success, now=NOW)
    assert persisted.cache_identity is not None

    assert persisted.cache_identity == success.cache_identity
    assert (
        store.lookup_deep_analysis_cache(cache_identity=success.cache_identity)
        == persisted
    )
    assert isinstance(persisted, VerifiedPersistedDeepAnalysisRead)
    assert not verify_trusted_deep_analysis_success(persisted)


def test_persisted_verified_read_builds_deterministic_traceable_note_v2(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    success = _trusted_success()
    persisted = DeepAnalysisPersistenceStore(
        repository
    ).persist_trusted_deep_analysis_success(success=success, now=NOW)

    live_note = build_note_v2(success)
    persisted_note = build_note_v2(persisted)

    assert persisted_note == live_note
    assert persisted_note.identity == live_note.identity
    assert (
        persisted_note.provenance.deep_analysis_result_identity
        == persisted.result_identity
    )
    assert persisted_note.provenance.scoring_request_hash == "a" * 64
    assert persisted_note.provenance.scoring_success_provenance == "PRIMARY"
    assert tuple(item.evidence_id for item in persisted_note.evidence_references) == (
        "e1",
    )
    rendered = render_note_v2(persisted_note)
    assert "Selected evidence only." in rendered
    assert "unselected full transcript" not in repr(persisted_note)
    assert "unselected full transcript" not in rendered


def test_note_v2_rejects_raw_or_reconstructed_persisted_read(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    persisted = DeepAnalysisPersistenceStore(
        repository
    ).persist_trusted_deep_analysis_success(success=_trusted_success(), now=NOW)

    with pytest.raises(NoteV2Error, match="authoritative Deep Analysis"):
        build_note_v2(
            {"knowledge_content_json": persisted.content.model_dump(mode="json")}
        )
    with pytest.raises(NoteV2Error, match="persisted read is untrusted"):
        build_note_v2(replace(persisted))


def test_tampered_persisted_result_is_rejected_before_note_v2(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    store = DeepAnalysisPersistenceStore(repository)
    persisted = store.persist_trusted_deep_analysis_success(
        success=_trusted_success(), now=NOW
    )
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE deep_analysis_persisted_results SET knowledge_content_json = ?",
            ("{}",),
        )
    finally:
        connection.close()

    assert (
        store.read_persisted_deep_analysis_result(
            result_identity=persisted.result_identity
        )
        is None
    )
    with pytest.raises(NoteV2Error, match="authoritative Deep Analysis"):
        build_note_v2(None)


def test_failed_new_attempt_cannot_displace_last_verified_current_summary(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    store = DeepAnalysisPersistenceStore(repository)
    real = _trusted_success()
    current = store.persist_trusted_deep_analysis_success(success=real, now=NOW)

    forged = object.__new__(type(real))
    for name in (
        "_content_identity",
        "_cache_identity",
        "_provenance_identity",
        "_sealed",
    ):
        object.__setattr__(forged, name, getattr(real, name))

    with pytest.raises(DeepAnalysisPersistenceError, match="runtime-verified"):
        store.persist_trusted_deep_analysis_success(success=forged, now=NOW)

    still_current = store.read_current_content_summary_result(
        video_id=current.canonical_input.video_identity
    )
    assert still_current is not None
    assert still_current.result_identity == current.result_identity


def test_forged_or_reconstructed_success_cannot_write_authoritative_row(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    real = _trusted_success()
    forged = object.__new__(type(real))
    for name in (
        "_content_identity",
        "_cache_identity",
        "_provenance_identity",
        "_sealed",
    ):
        object.__setattr__(forged, name, getattr(real, name))

    with pytest.raises(DeepAnalysisPersistenceError, match="runtime-verified"):
        DeepAnalysisPersistenceStore(repository).persist_trusted_deep_analysis_success(
            success=forged, now=NOW
        )

    connection = repository._connect()
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM deep_analysis_persisted_results"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()


@pytest.mark.parametrize(
    "column",
    (
        "a1_identity",
        "a2_identity",
        "a3_identity",
        "cache_identity",
        "knowledge_content_json",
        "content_identity",
        "provenance_identity",
        "provider_id",
        "scoring_request_hash",
        "scoring_success_provenance",
        "evidence_registry_identity",
        "validation_policy_identity",
        "payload_scope",
    ),
)
def test_tampered_row_is_never_returned_as_exact_cache_hit(
    tmp_path: Path, column: str
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    success = _trusted_success()
    store = DeepAnalysisPersistenceStore(repository)
    persisted = store.persist_trusted_deep_analysis_success(success=success, now=NOW)
    assert persisted.cache_identity is not None
    connection = repository._connect()
    try:
        value = "b" * 64 if column != "scoring_success_provenance" else "REPAIR_H2C"
        if column == "knowledge_content_json":
            value = "{}"
        elif column == "provider_id":
            value = "other-provider"
        elif column == "payload_scope":
            value = "FULL_TRANSCRIPT"
        connection.execute(
            f"UPDATE deep_analysis_persisted_results SET {column} = ?", (value,)
        )
    finally:
        connection.close()

    assert (
        store.lookup_deep_analysis_cache(cache_identity=persisted.cache_identity)
        is None
    )


def test_secret_and_unselected_transcript_are_absent_from_persisted_record(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    success = _trusted_success()
    DeepAnalysisPersistenceStore(repository).persist_trusted_deep_analysis_success(
        success=success, now=NOW
    )
    connection = repository._connect()
    try:
        row = connection.execute(
            "SELECT * FROM deep_analysis_persisted_results"
        ).fetchone()
        assert row is not None
        serialized = " ".join(
            str(row[name]) for name in row.keys() if name != "structured_payload_bytes"
        )
        assert "sk-task016-DO-NOT-PERSIST" not in serialized
        assert "unselected full transcript" not in serialized
    finally:
        connection.close()


def test_cache_eligibility_must_match_the_persisted_model_identity_class(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    success = _trusted_success()
    store = DeepAnalysisPersistenceStore(repository)
    persisted = store.persist_trusted_deep_analysis_success(success=success, now=NOW)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE deep_analysis_persisted_results SET cache_eligibility = 'INELIGIBLE_FLOATING_MODEL', "
            "cache_identity = NULL"
        )
    finally:
        connection.close()

    assert (
        store.read_persisted_deep_analysis_result(
            result_identity=persisted.result_identity
        )
        is None
    )


def test_same_cache_identity_with_different_content_is_rejected_by_sqlite(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_summary_content(repository)
    success = _trusted_success()
    store = DeepAnalysisPersistenceStore(repository)
    persisted = store.persist_trusted_deep_analysis_success(success=success, now=NOW)
    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO deep_analysis_persisted_results "
                "SELECT ?, cache_identity, cache_eligibility, a1_identity, a2_identity, a3_identity, "
                "validation_policy_identity, validation_policy_json, provider_kind, provider_id, adapter_identity, "
                "adapter_version, endpoint_deployment_profile_identity, model_id, model_identity_class, "
                "model_resolved_revision, payload_scope, scoring_request_hash, scoring_success_provenance, "
                "evidence_registry_identity, ?, provider_envelope_identity, structured_payload_identity, ?, "
                "canonical_input_json, evidence_registry_json, authorized_payload_json, request_projection_json, "
                "execution_profile_json, payload_consent_json, context_budget_json, response_metadata_json, "
                "knowledge_content_json, fallback_attempts_json, fallback_policy_identity, timeout_profile_identity, "
                "response_envelope_bytes, structured_payload_kind, structured_payload_bytes, created_at, validated_at, persistence_version, durable_authority_identity "
                "FROM deep_analysis_persisted_results WHERE result_identity = ?",
                ("b" * 64, "c" * 64, "d" * 64, persisted.result_identity),
            )
    finally:
        connection.close()
