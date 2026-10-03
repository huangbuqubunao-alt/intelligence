"""Hostile persistence, scope, provenance and bounded-execution probes."""

import json
import sqlite3

import pytest
from conftest import _load_module

from youtube_intel.research_contract import (
    CONTRACT,
    MAX_EVIDENCE,
    ResearchRequest,
    canonical,
    digest,
)
from youtube_intel.research_lite import ResearchLiteService, ResearchRejected

support = _load_module("test_research_lite")
authority = support.authority


def damage(repo, result, change, *, reseal=False):
    # Simulate out-of-band corruption: bypass triggers/FKs in a disposable DB.
    db = sqlite3.connect(repo._database_path)
    db.row_factory = sqlite3.Row
    try:
        db.execute("DROP TRIGGER research_results_immutable_update")
        row = db.execute("SELECT * FROM research_results WHERE result_identity=?", (result.result_identity,)).fetchone()
        payload = json.loads(row["payload_json"])
        change(payload)
        payload_hash = digest(payload) if reseal else row["payload_hash"]
        identity = digest({"contract": CONTRACT, "research_id": payload["research_id"], "execution_id": payload["execution_id"], "payload_hash": payload_hash}) if reseal else result.result_identity
        db.execute("UPDATE research_results SET payload_json=?,payload_hash=?,result_identity=? WHERE result_identity=?", (canonical(payload), payload_hash, identity, result.result_identity))
        db.execute("UPDATE research_items SET current_result_identity=? WHERE research_id=?", (identity, result.packet.research_id))
        db.commit()
    finally:
        db.close()


@pytest.mark.parametrize("field,value", [
    ("question", "fabricated question"), ("output_language", "zh-CN"),
    ("contract", "unsupported"), ("execution_id", "0" * 32),
    ("assembled_at", "not-a-date"), ("assembly_status", "TRUSTED"),
    ("synthesis_status", "MODEL_SYNTHESIZED"), ("material_status", "INSUFFICIENT_MATERIAL"),
])
def test_tampered_payload_is_not_trusted(tmp_path, field, value):
    repo = authority.seed(tmp_path)
    result = support.run(repo)
    damage(repo, result, lambda p: p.update({field: value}))
    with pytest.raises(ResearchRejected):
        ResearchLiteService(repo).read(result.packet.research_id)


@pytest.mark.parametrize("field,value", [
    ("evidence_id", "missing-evidence"), ("evidence_id", "candidate-transient"),
    ("content_id", "other-content"), ("excerpt", "invented quotation"),
    ("start_ms", 987), ("end_ms", 999999), ("artifact_id", "foreign-artifact"),
    ("source_language", "fabricated-language"), ("created_at", "2099-01-01T00:00:00Z"),
    ("timed_transcript_hash", "f" * 64), ("lineage_kind", "TRANSLATION"),
])
def test_resealed_evidence_still_must_resolve(tmp_path, field, value):
    repo = authority.seed(tmp_path)
    result = support.run(repo)
    damage(repo, result, lambda p: p["evidence"][0].update({field: value}), reseal=True)
    with pytest.raises(ResearchRejected):
        ResearchLiteService(repo).read(result.packet.research_id)


def test_foreign_real_evidence_cannot_escape_selected_scope(tmp_path):
    repo = authority.seed(tmp_path)
    other = authority.seed_other(tmp_path, repo)
    authority.service(repo).run(content_id=other)
    foreign = support.run(repo, content_ids=[other])
    result = support.run(repo)
    damage(repo, result, lambda p: p["evidence"].__setitem__(0, foreign.packet.evidence[0].model_dump(mode="json")), reseal=True)
    with pytest.raises(ResearchRejected, match="SOURCE_AUTHORITY_UNAVAILABLE"):
        ResearchLiteService(repo).read(result.packet.research_id)


def test_candidate_and_phase1a_never_supply_research_authority(tmp_path):
    repo = authority.seed(tmp_path)
    activation = authority.activation
    activation._seed_content(repo, "phase1a-only")
    activation._service(repo).run(content_id="phase1a-only")
    result = support.run(repo, "Core conclusion", ["phase1a-only"])
    assert not result.packet.evidence and not result.packet.intelligence
    assert result.packet.material_status == "INSUFFICIENT_MATERIAL"


def test_phase1b_promoted_evidence_uses_shared_authority_without_da_claims(tmp_path):
    repo = authority.seed(tmp_path)
    authority.service(repo).run(content_id=authority.VIDEO)
    result = support.run(repo)
    assert result.packet.evidence
    assert not result.packet.intelligence
    assert all(repo.resolve_verified_evidence_text(e.evidence_id) is not None for e in result.packet.evidence)


def test_deleted_evidence_breaks_trusted_read(tmp_path):
    repo = authority.seed(tmp_path)
    result = support.run(repo)
    with repo._connect() as db:
        db.execute("UPDATE evidence SET availability='UNAVAILABLE' WHERE evidence_id=?", (result.packet.evidence[0].evidence_id,))
    with pytest.raises(ResearchRejected):
        ResearchLiteService(repo).read(result.packet.research_id)


def test_pointer_regression_rejected_without_fallback(tmp_path):
    repo = authority.seed(tmp_path)
    first = support.run(repo)
    support.run(repo)
    with repo._connect() as db:
        db.execute("UPDATE research_items SET current_result_identity=?", (first.result_identity,))
    with pytest.raises(ResearchRejected, match="CORRUPTED_RESULT"):
        ResearchLiteService(repo).read(first.packet.research_id)


def test_deterministic_packet_and_injection_is_plain_text(tmp_path):
    repo = authority.seed(tmp_path)
    question = "sentence1 '; DROP TABLE videos; -- <script>alert(1)</script>"
    first, second = support.run(repo, question), support.run(repo, question)
    a, b = first.packet.model_dump(), second.packet.model_dump()
    for key in ["execution_id", "execution_number"]:
        a.pop(key)
        b.pop(key)
    assert a == b
    assert a["question"] == question
    assert repo.get_video(authority.VIDEO) is not None


def test_zero_network_or_provider_dispatch(tmp_path, monkeypatch):
    import socket
    import urllib.request

    repo = authority.seed(tmp_path)
    def prohibited(*args, **kwargs):
        raise AssertionError("Research dispatched externally")
    monkeypatch.setattr(socket, "create_connection", prohibited)
    monkeypatch.setattr(urllib.request, "urlopen", prohibited)
    result = support.run(repo)
    assert result.packet.synthesis_status == "UNSUPPORTED_MODEL_SYNTHESIS"


def test_large_scope_and_ties_are_bounded_and_stable(tmp_path):
    admitted = _load_module("test_task022_personalized_distillation")
    repo = admitted._repository(tmp_path)
    _, video = admitted._source_and_video(repo)
    for index in range(130):
        admitted._evidence(repo, video, start_ms=index * 1000, end_ms=index * 1000 + 500)
    service = ResearchLiteService(repo, now=lambda: admitted.NOW)
    request = ResearchRequest(question="canonical", content_ids=[video])
    first, second = service.assemble(request, output_language="en"), service.assemble(request, output_language="en")
    assert first.packet.evidence_candidates == 130
    assert first.packet.retrieval_truncated
    assert len(first.packet.evidence) == MAX_EVIDENCE
    assert first.packet.evidence == second.packet.evidence
    assert [e.start_ms for e in first.packet.evidence] == list(range(0, MAX_EVIDENCE * 1000, 1000))


def test_failed_write_rolls_back_and_preserves_current(tmp_path, monkeypatch):
    repo = authority.seed(tmp_path)
    first = support.run(repo)
    service = ResearchLiteService(repo, now=lambda: authority.NOW)
    original = service.verify_row
    def fail_after_persistence(db, row):
        original(db, row)
        raise RuntimeError("injected before commit")
    monkeypatch.setattr(service, "verify_row", fail_after_persistence)
    with pytest.raises(RuntimeError, match="before commit"):
        service.assemble(ResearchRequest(question="sentence1", content_ids=[authority.VIDEO]), output_language="en")
    assert ResearchLiteService(repo).read(first.packet.research_id).as_dict() == first.as_dict()
    with repo._connect() as db:
        assert db.execute("SELECT count(*) FROM research_results").fetchone()[0] == 1


def test_evidence_validation_uses_bounded_batch_queries(tmp_path, monkeypatch):
    admitted = _load_module("test_task022_personalized_distillation")
    repo = admitted._repository(tmp_path)
    _, video = admitted._source_and_video(repo)
    for index in range(24):
        admitted._evidence(repo, video, start_ms=index * 1000, end_ms=index * 1000 + 500)
    queries = []
    original = repo._connect
    def traced(**kwargs):
        db = original(**kwargs)
        db.set_trace_callback(queries.append)
        return db
    monkeypatch.setattr(repo, "_connect", traced)
    result = ResearchLiteService(repo, now=lambda: admitted.NOW).assemble(
        ResearchRequest(question="canonical", content_ids=[video]), output_language="en"
    )
    assert len(result.packet.evidence) >= 10
    evidence_reads = [sql for sql in queries if sql.startswith("SELECT") and ("FROM evidence " in sql or "FROM timed_transcript_cues " in sql)]
    assert len(evidence_reads) <= 10


def admitted_packet(tmp_path):
    fixture = _load_module("test_task022_personalized_distillation")
    repo = fixture._repository(tmp_path)
    source, video = fixture._source_and_video(repo)
    evidence = fixture._evidence(repo, video)
    admitted = fixture._service(repo, fixture._FakeTransport(fixture._raw(evidence))).distill(fixture._command(source, video, evidence))
    result = ResearchLiteService(repo, now=lambda: fixture.NOW).assemble(
        ResearchRequest(question="canonical", content_ids=[video]), output_language="en"
    )
    return fixture, repo, result, admitted


def test_artifact_owner_must_match_evidence_content(tmp_path):
    repo = authority.seed(tmp_path)
    other = authority.seed_other(tmp_path, repo)
    result = support.run(repo)
    ref = result.packet.evidence[0]
    with repo._connect() as db:
        db.execute("UPDATE artifacts SET video_id=? WHERE artifact_id=?", (other, ref.artifact_id))
    with pytest.raises(ResearchRejected, match="SOURCE_AUTHORITY_UNAVAILABLE"):
        ResearchLiteService(repo).read(result.packet.research_id)


@pytest.mark.parametrize("field,value", [
    ("intelligence_id", "missing-intelligence"), ("revision_id", "missing-revision"),
    ("content_id", "outside-scope"), ("source_id", "different-source"),
    ("conclusion", "Fabricated claim"), ("claim_kind", "EVIDENCE_BACKED_STATEMENT_FAKE"),
    ("state", "CONFIRMED"), ("evidence_ids", ["candidate-ref"]), ("stances", ["contradicting"]),
])
def test_resealed_intelligence_still_must_resolve(tmp_path, field, value):
    _, repo, result, _ = admitted_packet(tmp_path)
    damage(repo, result, lambda p: p["intelligence"][0].update({field: value}), reseal=True)
    with pytest.raises(ResearchRejected, match="SOURCE_AUTHORITY_UNAVAILABLE"):
        ResearchLiteService(repo).read(result.packet.research_id)


def test_deleted_source_relationship_rejects_recorded_intelligence(tmp_path):
    _, repo, result, _ = admitted_packet(tmp_path)
    with repo._connect() as db:
        db.execute("DELETE FROM source_video_links")
    with pytest.raises(ResearchRejected, match="SOURCE_AUTHORITY_UNAVAILABLE"):
        ResearchLiteService(repo).read(result.packet.research_id)


def test_future_intelligence_cannot_support_earlier_execution(tmp_path):
    _, repo, result, _ = admitted_packet(tmp_path)
    with repo._connect() as db:
        db.execute("DROP TRIGGER intelligence_revision_immutable")
        db.execute("UPDATE intelligence_revisions SET created_at='2099-01-01T00:00:00Z'")
    with pytest.raises(ResearchRejected, match="SOURCE_AUTHORITY_UNAVAILABLE"):
        ResearchLiteService(repo).read(result.packet.research_id)


def test_recorded_intelligence_rejects_corrupt_current_pointer(tmp_path):
    _, repo, result, _ = admitted_packet(tmp_path)
    db = sqlite3.connect(repo._database_path)
    db.execute("DROP TRIGGER intelligence_current_revision_must_advance")
    db.execute("DROP TRIGGER intelligence_current_revision_must_be_supported")
    db.execute("UPDATE intelligences SET current_revision_id='missing-revision'")
    db.commit()
    db.close()
    with pytest.raises(ResearchRejected, match="SOURCE_AUTHORITY_UNAVAILABLE"):
        ResearchLiteService(repo).read(result.packet.research_id)


def test_later_intelligence_revision_preserves_recorded_research(tmp_path):
    from datetime import timedelta

    from youtube_intel.state import (
        DependencyEdgeWrite,
        DependencyRelation,
        IntelligenceInterpretationKind,
        IntelligenceRevisionWrite,
        IntelligenceState,
    )

    fixture, repo, result, admitted = admitted_packet(tmp_path)
    old_id = result.packet.intelligence[0].revision_id
    old = repo.get_intelligence_revision(old_id)
    card = repo.get_distillation_card(old_id)
    assert old is not None and card is not None
    repo.append_intelligence_revision(
        intelligence_id=admitted.intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id="recorded-following-revision", interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=old.claim_kind, content_hash=old.content_hash, state=IntelligenceState.UPDATED,
            reason="Same claim rechecked later", evidence_ids=tuple(result.packet.intelligence[0].evidence_ids),
        ), now=fixture.NOW + timedelta(days=1),
    )
    for eid in result.packet.intelligence[0].evidence_ids:
        repo.create_dependency_edge(DependencyEdgeWrite(
            edge_id="later-edge-" + eid, dependent_revision_id="recorded-following-revision",
            relation=DependencyRelation.EVIDENCE_SUPPORT, input_evidence_id=eid, input_revision_id=None,
        ), now=fixture.NOW + timedelta(days=1))
    # A later legitimate domain revision does not replace the recorded card.
    assert fixture.AuthoritativeIntelligenceReader(repo).read_current(admitted.intelligence_id).revision_id == "recorded-following-revision"
    assert ResearchLiteService(repo).read(result.packet.research_id).as_dict() == result.as_dict()
