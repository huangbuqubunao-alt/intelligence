"""Library assembly uses real durable authority and never dispatches a provider."""

from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.research_contract import ResearchRequest
from youtube_intel.research_lite import ResearchLiteService, ResearchRejected
from youtube_intel.state import SQLiteStateRepository

authority = _load_module("test_v1x_phase1b_authority")


def run(repo, question="sentence1", content_ids=None, language="en"):
    return ResearchLiteService(repo, now=lambda: authority.NOW).assemble(
        ResearchRequest(question=question, content_ids=content_ids or [authority.VIDEO]),
        output_language=language,
    )


def test_real_evidence_and_restart(tmp_path: Path):
    repo = authority.seed(tmp_path)
    result = run(repo)
    assert result.packet.material_status == "EVIDENCE_AVAILABLE"
    assert result.packet.synthesis_status == "UNSUPPORTED_MODEL_SYNTHESIS"
    assert result.packet.evidence
    for ref in result.packet.evidence:
        actual = repo.resolve_verified_evidence_text(ref.evidence_id)
        assert actual is not None and actual.excerpt == ref.excerpt
        assert actual.video_id == authority.VIDEO
    restarted = ResearchLiteService(SQLiteStateRepository(tmp_path / "state.sqlite3"))
    assert restarted.read(result.packet.research_id).as_dict() == result.as_dict()


def test_rerun_keeps_semantic_identity_and_changes_execution(tmp_path):
    repo = authority.seed(tmp_path)
    first, second = run(repo), run(repo)
    assert first.packet.research_id == second.packet.research_id
    assert first.packet.execution_id != second.packet.execution_id
    assert first.result_identity != second.result_identity
    with repo._connect() as db:
        assert db.execute("SELECT count(*) FROM research_items").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM research_results").fetchone()[0] == 2
    assert ResearchLiteService(repo).read(first.packet.research_id).result_identity == second.result_identity


def test_insufficient_and_metadata_only(tmp_path):
    repo = authority.seed(tmp_path)
    authority.activation._seed_content(repo, "metadata-only")
    for question, scope in [("not-present-xyz", [authority.VIDEO]), ("metadata", ["metadata-only"])]:
        result = run(repo, question, scope)
        assert result.packet.material_status == "INSUFFICIENT_MATERIAL"
        assert not result.packet.evidence
        assert "NO_MATCHING_EVIDENCE" in result.packet.unresolved


def test_missing_scope_is_rejected(tmp_path):
    repo = authority.seed(tmp_path)
    with pytest.raises(ResearchRejected, match="SCOPE_NOT_FOUND"):
        run(repo, content_ids=["missing"])


def test_scope_includes_content_without_channel_metadata(tmp_path):
    repo = authority.seed(tmp_path)
    with repo._connect() as db:
        db.execute("UPDATE videos SET channel_name=NULL WHERE video_id=?", (authority.VIDEO,))
    result = ResearchLiteService(repo).scope_options()
    item = next(c for c in result["content"] if c["content_id"] == authority.VIDEO)
    assert item["channel_name"] == ""
    assert item["title"] == repo.get_video(authority.VIDEO).title
    assert result["total"] >= 1


def test_only_selected_content_and_no_mutation(tmp_path):
    repo = authority.seed(tmp_path)
    other = authority.seed_other(tmp_path, repo)
    with repo._connect() as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if not r[0].startswith("research_")]
        before = {t: [tuple(r) for r in db.execute(f'SELECT * FROM "{t}"')] for t in tables}
    result = run(repo)
    assert all(e.content_id != other for e in result.packet.evidence)
    with repo._connect() as db:
        assert before == {t: [tuple(r) for r in db.execute(f'SELECT * FROM "{t}"')] for t in tables}


def test_language_identity(tmp_path):
    repo = authority.seed(tmp_path)
    en, zh = run(repo), run(repo, language="zh-CN")
    assert en.packet.research_id != zh.packet.research_id
    assert en.packet.evidence == zh.packet.evidence


def test_admitted_intelligence_keeps_claim_kind_state_and_exact_citations(tmp_path):
    support = _load_module("test_task022_personalized_distillation")
    repo = support._repository(tmp_path)
    source, video = support._source_and_video(repo)
    evidence = support._evidence(repo, video)
    admitted = support._service(repo, support._FakeTransport(support._raw(evidence))).distill(
        support._command(source, video, evidence)
    )
    result = ResearchLiteService(repo, now=lambda: support.NOW).assemble(
        ResearchRequest(question="Canonical evidence", content_ids=[video]), output_language="en"
    )
    assert len(result.packet.intelligence) == 1
    finding = result.packet.intelligence[0]
    card = support.AuthoritativeIntelligenceReader(repo).read_current_card(admitted.intelligence_id)
    assert finding.revision_id == card.verified.revision_id
    assert finding.conclusion == card.core_conclusion
    assert finding.claim_kind == card.verified.claim_kind.value
    assert finding.state == card.verified.state.value
    assert finding.evidence_ids == list(card.verified.evidence_ids)
    assert set(finding.evidence_ids) <= {e.evidence_id for e in result.packet.evidence}
    assert ResearchLiteService(repo).read(result.packet.research_id).packet == result.packet
