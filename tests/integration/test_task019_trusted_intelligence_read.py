"""TASK-019 trusted Intelligence read and dependency-impact contracts."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
    VerifiedIntelligenceRead,
)
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import (
    DependencyEdgeWrite,
    DependencyRelation,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceWrite,
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
    SQLiteStateRepository,
    build_evidence_id,
)

NOW = datetime(2026, 9, 7, 9, 0, tzinfo=UTC)


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    tmp_path.mkdir(parents=True, exist_ok=True)
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    timestamp = "2026-09-07T09:00:00Z"
    connection = repository._connect()  # test-only fixture setup; no production read path.
    try:
        connection.execute(
            "INSERT INTO videos (video_id, channel_id, pipeline_status, pipeline_version, availability, discovered_at, updated_at) "
            "VALUES ('video-1', 'UC_TEST', 'DISCOVERED', 'pipeline-v1', 'public', ?, ?)",
            (timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
            "VALUES ('artifact-1', 'artifact-key-1', 'video-1', NULL, 'transcript_canonical', 'DATA', 'transcript.txt', ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            ("a" * 64, timestamp),
        )
    finally:
        connection.close()
    return repository


def _evidence(repository: SQLiteStateRepository) -> str:
    evidence_id = build_evidence_id(
        video_id="video-1",
        artifact_id="artifact-1",
        start_ms=1_000,
        end_ms=1_500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    repository.create_evidence(
        EvidenceWrite(
            evidence_id=evidence_id,
            video_id="video-1",
            artifact_id="artifact-1",
            start_ms=1_000,
            end_ms=1_500,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
        ),
        now=NOW,
    )
    return evidence_id


def _write(
    revision_id: str,
    evidence_id: str,
    *,
    claim_kind: IntelligenceClaimKind = IntelligenceClaimKind.FACT,
    state: IntelligenceState = IntelligenceState.NEW,
) -> IntelligenceRevisionWrite:
    return IntelligenceRevisionWrite(
        revision_id=revision_id,
        interpretation_kind=IntelligenceInterpretationKind.DISTILLATION,
        claim_kind=claim_kind,
        content_hash="b" * 64,
        state=state,
        reason="evidence-bound revision",
        evidence_ids=(evidence_id,),
    )


def _supported_current(
    tmp_path: Path,
    *,
    claim_kind: IntelligenceClaimKind = IntelligenceClaimKind.FACT,
    state: IntelligenceState = IntelligenceState.CONFIRMED,
) -> tuple[SQLiteStateRepository, str, str, str]:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository)
    repository.create_intelligence(intelligence_id="intelligence-1", now=NOW)
    repository.append_intelligence_revision(
        intelligence_id="intelligence-1",
        revision=_write("revision-1", evidence_id, claim_kind=claim_kind),
        now=NOW,
    )
    repository.append_intelligence_revision(
        intelligence_id="intelligence-1",
        revision=_write("revision-2", evidence_id, claim_kind=claim_kind, state=state),
        now=NOW,
    )
    for revision_id in ("revision-1", "revision-2"):
        repository.create_dependency_edge(
            DependencyEdgeWrite(
                edge_id=f"support:{revision_id}",
                dependent_revision_id=revision_id,
                relation=DependencyRelation.EVIDENCE_SUPPORT,
                input_evidence_id=evidence_id,
                input_revision_id=None,
            ),
            now=NOW,
        )
    return repository, "intelligence-1", "revision-2", evidence_id


def test_valid_current_read_mints_a_sealed_typed_projection(tmp_path: Path) -> None:
    repository, intelligence_id, revision_id, evidence_id = _supported_current(tmp_path)

    verified = AuthoritativeIntelligenceReader(repository).read_current(intelligence_id)

    assert isinstance(verified, VerifiedIntelligenceRead)
    assert verified.intelligence_id == intelligence_id
    assert verified.revision_id == revision_id
    assert verified.claim_kind is IntelligenceClaimKind.FACT
    assert verified.state is IntelligenceState.CONFIRMED
    assert verified.evidence_ids == (evidence_id,)
    assert verified.is_confirmed is True
    with pytest.raises(TypeError):
        verified._state = IntelligenceState.DISPUTED  # type: ignore[attr-defined]


def test_missing_pointer_or_evidence_support_fails_closed(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    repository.create_intelligence(intelligence_id="empty", now=NOW)
    with pytest.raises(IntelligenceReadRejected, match="current revision"):
        AuthoritativeIntelligenceReader(repository).read_current("empty")

    repository, intelligence_id, _, _ = _supported_current(tmp_path / "supported")
    connection = repository._connect()
    try:
        connection.execute("DROP TRIGGER dependency_edge_immutable_delete")
        connection.execute("DELETE FROM dependency_edges WHERE edge_id = 'support:revision-2'")
    finally:
        connection.close()
    with pytest.raises(IntelligenceReadRejected, match="dependency set is incomplete"):
        AuthoritativeIntelligenceReader(repository).read_current(intelligence_id)


@pytest.mark.parametrize(
    "claim_kind",
    (
        IntelligenceClaimKind.FACT,
        IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
        IntelligenceClaimKind.OPINION,
        IntelligenceClaimKind.PREDICTION,
        IntelligenceClaimKind.RUMOR,
        IntelligenceClaimKind.SYSTEM_INFERENCE,
    ),
)
def test_claim_kind_and_lifecycle_are_preserved_without_inference(
    tmp_path: Path, claim_kind: IntelligenceClaimKind
) -> None:
    repository, intelligence_id, _, _ = _supported_current(
        tmp_path, claim_kind=claim_kind, state=IntelligenceState.DISPUTED
    )

    verified = AuthoritativeIntelligenceReader(repository).read_current(intelligence_id)

    assert verified.claim_kind is claim_kind
    assert verified.state is IntelligenceState.DISPUTED
    assert verified.is_confirmed is False


def test_invalidated_is_not_an_ordinary_verified_current_read(tmp_path: Path) -> None:
    repository, intelligence_id, _, _ = _supported_current(
        tmp_path, state=IntelligenceState.INVALIDATED
    )

    with pytest.raises(IntelligenceReadRejected, match="not active"):
        AuthoritativeIntelligenceReader(repository).read_current(intelligence_id)


def test_unavailable_evidence_and_caller_forgery_cannot_mint_authority(tmp_path: Path) -> None:
    repository, intelligence_id, _, _ = _supported_current(tmp_path)
    reader = AuthoritativeIntelligenceReader(repository)
    verified = reader.read_current(intelligence_id)
    with pytest.raises(TypeError):
        VerifiedIntelligenceRead(
            intelligence_id=verified.intelligence_id,
            revision_id=verified.revision_id,
            claim_kind=verified.claim_kind,
            state=verified.state,
            evidence_ids=verified.evidence_ids,
        )
    reader._repository = _UnavailableEvidenceRepository(repository)  # adversarial stale source.
    with pytest.raises(IntelligenceReadRejected, match="unavailable"):
        reader.read_current(intelligence_id)


@pytest.mark.parametrize(
    "claim_kind, code",
    ((IntelligenceClaimKind.UNCLASSIFIED, "CLAIM_KIND_UNCLASSIFIED"), ("TAMPERED", "CLAIM_KIND_INVALID")),
)
def test_legacy_or_malformed_claim_kind_cannot_enter_trusted_read(
    tmp_path: Path, claim_kind: IntelligenceClaimKind | str, code: str
) -> None:
    repository, intelligence_id, _, _ = _supported_current(tmp_path)
    reader = AuthoritativeIntelligenceReader(_ClaimKindRepository(repository, claim_kind))

    with pytest.raises(IntelligenceReadRejected) as rejected:
        reader.read_current(intelligence_id)

    assert rejected.value.code == code


class _ClaimKindRepository:
    def __init__(self, repository: SQLiteStateRepository, claim_kind: IntelligenceClaimKind | str) -> None:
        self._repository = repository
        self._claim_kind = claim_kind

    def __getattr__(self, name: str) -> object:
        return getattr(self._repository, name)

    def list_intelligence_revisions(self, intelligence_id: str) -> object:
        revisions = self._repository.list_intelligence_revisions(intelligence_id)
        return tuple(
            replace(item, claim_kind=cast(IntelligenceClaimKind, self._claim_kind))
            if item.revision_id == "revision-2"
            else item
            for item in revisions
        )


class _UnavailableEvidenceRepository:
    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> object:
        return getattr(self._repository, name)

    def get_evidence(self, evidence_id: str) -> object:
        evidence = self._repository.get_evidence(evidence_id)
        assert evidence is not None
        return replace(evidence, availability=EvidenceAvailability.UNAVAILABLE)


def test_newer_history_cannot_bypass_the_explicit_current_pointer(tmp_path: Path) -> None:
    repository, intelligence_id, _, _ = _supported_current(tmp_path)
    reader = AuthoritativeIntelligenceReader(_RegressedPointerRepository(repository))

    with pytest.raises(IntelligenceReadRejected) as rejected:
        reader.read_current(intelligence_id)

    assert rejected.value.code == "CURRENT_POINTER_REGRESSED"


class _RegressedPointerRepository:
    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> object:
        return getattr(self._repository, name)

    def get_intelligence(self, intelligence_id: str) -> object:
        intelligence = self._repository.get_intelligence(intelligence_id)
        assert intelligence is not None
        return replace(intelligence, current_revision_id="revision-1")


def test_corrupt_persistence_is_projected_fail_closed_not_as_a_raw_error(tmp_path: Path) -> None:
    repository, intelligence_id, _, _ = _supported_current(tmp_path)
    reader = AuthoritativeIntelligenceReader(_CorruptEvidenceRepository(repository))

    with pytest.raises(IntelligenceReadRejected) as rejected:
        reader.read_current(intelligence_id)

    assert rejected.value.code == "PERSISTENCE_INVALID"


class _CorruptEvidenceRepository:
    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> object:
        return getattr(self._repository, name)

    def get_evidence(self, evidence_id: str) -> object:
        raise ValueError("tampered persisted enum")


def test_impact_reports_direct_current_and_history_dependencies(tmp_path: Path) -> None:
    repository, intelligence_id, _, evidence_id = _supported_current(tmp_path)

    impact = AuthoritativeIntelligenceReader(repository).impact_for_evidence(evidence_id)

    assert impact.evidence_id == evidence_id
    assert {(item.intelligence_id, item.revision_id, item.is_current) for item in impact.revisions} == {
        (intelligence_id, "revision-1", False),
        (intelligence_id, "revision-2", True),
    }


def test_local_api_projects_only_reader_minted_intelligence_and_impact(tmp_path: Path) -> None:
    repository, intelligence_id, revision_id, evidence_id = _supported_current(
        tmp_path, claim_kind=IntelligenceClaimKind.SYSTEM_INFERENCE
    )
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        now=lambda: NOW,
    )

    status, payload = app.handle("GET", f"/api/v1/intelligence/{intelligence_id}")
    impact_status, impact_payload = app.handle("GET", f"/api/v1/evidence/{evidence_id}/impact")

    assert status == 200
    assert payload["intelligence"] == {
        "status": "AVAILABLE",
        "trusted": True,
        "intelligence_id": intelligence_id,
        "revision_id": revision_id,
        "claim_kind": "SYSTEM_INFERENCE",
        "state": "CONFIRMED",
        "evidence_ids": [evidence_id],
        "confirmed": True,
    }
    assert impact_status == 200
    assert impact_payload["impact"]["revisions"][-1]["revision_id"] == revision_id
