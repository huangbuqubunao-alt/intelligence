"""Deep Analysis converges onto the shared timed-transcript Evidence authority."""

import hashlib
import sqlite3
from datetime import datetime

from youtube_intel.deep_analysis_contracts import (
    CanonicalDeepAnalysisInputV1,
    DeepAnalysisRequestProjectionV1,
)
from youtube_intel.deep_analysis_phase1b_contract import (
    PHASE_1B_MODEL_SCHEMA,
    PHASE_1B_PROMPT_IDENTITY,
    DeepAnalysisDurableResult,
    DeepAnalysisPhase1BModelOutput,
    bind_durable_result,
)
from youtube_intel.domain import EvidenceRegistry, EvidenceSource, KnowledgeEvidence
from youtube_intel.state import (
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    SQLiteStateRepository,
    VerifiedTimedTranscript,
)
from youtube_intel.summary_evidence_authority import _plan_promotion
from youtube_intel.summary_evidence_candidates import (
    TrustedEvidenceRegistry,
    timed_transcript_candidates,
)


def deep_analysis_candidates(transcript: VerifiedTimedTranscript) -> TrustedEvidenceRegistry:
    """Whole real cue groups only; never truncate an authoritative excerpt."""
    return TrustedEvidenceRegistry(candidates=tuple(
        candidate for candidate in timed_transcript_candidates(transcript)
        if len(candidate.text) <= 2000
    )[:24])


def candidate_projection(registry: TrustedEvidenceRegistry) -> EvidenceRegistry:
    return EvidenceRegistry(items=tuple(KnowledgeEvidence(
        evidence_id=candidate.ref, source=EvidenceSource.TRANSCRIPT_SAMPLE,
        excerpt=candidate.text,
        source_content_hash=hashlib.sha256(candidate.text.encode("utf-8")).hexdigest(),
    ) for candidate in registry.candidates))


def resolve_deep_analysis_authority(
    *, connection: sqlite3.Connection, repository: SQLiteStateRepository,
    canonical: CanonicalDeepAnalysisInputV1, request: DeepAnalysisRequestProjectionV1,
    registry: EvidenceRegistry, output: DeepAnalysisPhase1BModelOutput,
    promote_at: datetime | None = None,
) -> tuple[DeepAnalysisDurableResult, EvidenceRegistry]:
    """Promote or reverify in one caller-owned transaction/snapshot.

    Identity shape is never proof. Candidates must be reconstructed from the
    same Content's live trusted cues and match the complete admitted projection.
    Promotion uses the Summary authority's builder, text binding, and resolver.
    """
    transcript = repository._get_verified_timed_transcript_in_transaction(connection, canonical.video_identity)
    if transcript is None:
        raise ValueError("Deep Analysis requires trusted timed transcript authority")
    candidates = deep_analysis_candidates(transcript)
    expected_registry = candidate_projection(candidates)
    expected_selected = tuple({
        "schema_version": "selected-evidence-projection-v1",
        "evidence_id": c.ref, "source": c.source.value, "excerpt": c.text,
    } for c in candidates.candidates)
    if (
        canonical.schema_version != "canonical-deep-analysis-input-v1"
        or canonical.operation != "content-deep-analysis"
        or canonical.knowledge_content_schema_version != PHASE_1B_MODEL_SCHEMA
        or canonical.prompt_version != PHASE_1B_PROMPT_IDENTITY
        or canonical.transcript_identity != transcript.timed_transcript_id
        or canonical.evidence_registry_identity != candidates.identity_hash()
        or registry != expected_registry
        or tuple(c.model_dump(mode="json") for c in canonical.selected_evidence) != expected_selected
        or request.a1_identity != canonical.a1_identity
        or request.output_language != canonical.output_language
        or request.authorized_payload.output_language != canonical.output_language
        or request.authorized_payload.selected_evidence != canonical.selected_evidence
        or request.authorized_payload.source_language != canonical.transcript_language
    ):
        raise ValueError("Deep Analysis candidate/source identity mismatch")
    issued = candidates.by_ref()
    durable_by_ref = {}
    evidence_items = []
    for ref in output.cited_refs():
        candidate = issued.get(ref)
        if candidate is None or not candidate.is_citable:
            raise ValueError("Deep Analysis references a foreign or non-citable candidate")
        plan = _plan_promotion(
            candidate, video_id=canonical.video_identity,
            canonical_artifact_id=transcript.canonical_artifact_id,
            timed_transcript_id=transcript.timed_transcript_id,
            timed_transcript_hash=transcript.timed_transcript_hash,
            language=canonical.transcript_language,
        )
        if promote_at is not None:
            repository._promote_summary_evidence_in_transaction(
                connection, plan.as_evidence_write(), plan.as_text_binding(), now=promote_at,
            )
        row = connection.execute("SELECT * FROM evidence WHERE evidence_id = ?", (plan.evidence_id,)).fetchone()
        verified = repository._resolve_verified_evidence_text_in_transaction(connection, plan.evidence_id)
        if row is None or verified is None:
            raise ValueError("Deep Analysis durable Evidence promotion is missing")
        evidence = repository._evidence_from_row(row)
        if (
            evidence.video_id != canonical.video_identity
            or verified.video_id != canonical.video_identity
            or evidence.artifact_id != transcript.canonical_artifact_id
            or evidence.lineage_kind is not EvidenceLineageKind.EXTRACTION
            or evidence.role is not EvidenceRole.PRIMARY_ORIGINAL
            or evidence.availability is not EvidenceAvailability.AVAILABLE
            or evidence.language != canonical.transcript_language
            or verified.timed_transcript_id != transcript.timed_transcript_id
            or verified.start_ms != plan.start_ms or verified.end_ms != plan.end_ms
            or verified.excerpt != plan.excerpt or verified.excerpt_hash != plan.excerpt_hash
        ):
            raise ValueError("Deep Analysis Evidence violates same-Content/source authority")
        durable_by_ref[ref] = plan.evidence_id
        evidence_items.append(KnowledgeEvidence(
            evidence_id=plan.evidence_id, source=EvidenceSource.TRANSCRIPT_SAMPLE,
            excerpt=verified.excerpt, source_content_hash=verified.excerpt_hash,
            start_seconds=verified.start_ms / 1000, end_seconds=verified.end_ms / 1000,
            timestamp_basis="timed-subtitle",
        ))
    return bind_durable_result(output, durable_by_ref, request.output_language), EvidenceRegistry(items=tuple(evidence_items))
