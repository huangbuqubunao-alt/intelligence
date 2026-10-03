"""Normal Summary/Evidence and mixed Research/Intelligence admission after Phase 8."""

import sqlite3

import pytest
from conftest import _load_module

from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
from youtube_intel.local_content import LocalContentProvider
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.research_contract import ResearchRequest
from youtube_intel.research_lite import ResearchLiteService
from youtube_intel.state import (
    DependencyEdgeWrite,
    DependencyRelation,
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
)


def test_three_source_research_and_mixed_timed_intelligence(tmp_path):
    authority = _load_module("test_v1x_phase1b_authority")
    fixture = _load_module("test_offline_transcription_jobs")
    repo = authority.seed(tmp_path)
    local = LocalContentProvider(repo, tmp_path / "data", now=lambda: fixture.NOW)
    text = local.import_bytes("notes.md", b"Sentence1 local research source.\n")
    media = local.import_bytes("voice.wav", fixture.audio_bytes())
    jobs = LocalTranscriptionJobs(
        repo, local.data_root, executor=fixture.Executor(), now=lambda: fixture.NOW
    )
    fixture.wait_for(lambda: not jobs.capability()["checking"])
    jobs.start(media.content_id, fixture.IDENTITY)
    fixture.wait_for(lambda: jobs.status(media.content_id)["status"] == "READY")
    service = ResearchLiteService(repo, now=lambda: fixture.NOW)
    request = ResearchRequest(
        question="sentence1",
        content_ids=[authority.VIDEO, text.content_id, media.content_id],
    )
    packet = service.assemble(request, output_language="en").packet
    repeat = service.assemble(request, output_language="en").packet
    assert packet.model_dump(
        exclude={"execution_id", "execution_number"}
    ) == repeat.model_dump(exclude={"execution_id", "execution_number"})
    assert repeat.execution_number == packet.execution_number + 1
    assert {e.content_id for e in packet.evidence} == set(request.content_ids)
    assert {e.provider for e in packet.evidence} == {"YOUTUBE", "LOCAL"}
    assert {e.locator_type for e in packet.evidence} == {"TIMED_MEDIA", "TEXT_RANGE"}
    evidence = tuple(
        e.evidence_id for e in packet.evidence if e.locator_type == "TIMED_MEDIA"
    )
    assert len(evidence) >= 2
    repo.create_intelligence(intelligence_id="mixed-timed", now=fixture.NOW)
    repo.append_intelligence_revision(
        intelligence_id="mixed-timed",
        revision=IntelligenceRevisionWrite(
            revision_id="mixed-timed-r1",
            interpretation_kind=IntelligenceInterpretationKind.SYNTHESIS,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash="a" * 64,
            state=IntelligenceState.NEW,
            reason="Timed mixed fixture authority",
            evidence_ids=evidence,
        ),
        now=fixture.NOW,
    )
    for index, eid in enumerate(evidence):
        repo.create_dependency_edge(
            DependencyEdgeWrite(
                edge_id=f"mixed-timed-e{index}",
                dependent_revision_id="mixed-timed-r1",
                relation=DependencyRelation.EVIDENCE_SUPPORT,
                input_evidence_id=eid,
                input_revision_id=None,
            ),
            now=fixture.NOW,
        )
    read = AuthoritativeIntelligenceReader(repo).read_current("mixed-timed")
    assert set(read.evidence_ids) == set(evidence)
    local_evidence = next(
        e for e in packet.evidence if e.content_id == media.content_id
    )
    assert (
        repo.resolve_verified_evidence_text(local_evidence.evidence_id).video_id
        == media.content_id
    )
    # Same-Content authority remains exact; a foreign Content cannot acquire the local timed source.
    with repo._connect() as connection, pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute(
            "UPDATE evidence SET video_id=? WHERE evidence_id=?",
            (authority.VIDEO, local_evidence.evidence_id),
        )
    assert repo.resolve_verified_evidence_text(local_evidence.evidence_id).video_id == media.content_id
    assert repo.get_verified_timed_transcript(video_id=authority.VIDEO) is not None
