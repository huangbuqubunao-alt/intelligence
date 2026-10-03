"""Derived comparison consumes two immutable authorities, never live retrieval."""

import pytest
from conftest import _load_module

from youtube_intel.research_lite import ResearchLiteService, ResearchRejected

support = _load_module("test_research_lite")


def compare(service, base, target):
    return service.diff(base.packet.research_id, base.result_identity, target.result_identity).model_dump(mode="json")


def test_identical_reruns_self_comparison_and_pointer_independence(tmp_path):
    repo = support.authority.seed(tmp_path)
    first, second = support.run(repo), support.run(repo)
    service = ResearchLiteService(repo)
    diff = compare(service, first, second)
    assert diff["no_material_changes"]
    assert diff["summary"] == {"added": 0, "removed": 0, "changed": 0}
    assert diff["base"]["revision_id"] == first.result_identity
    assert diff["target"]["revision_id"] == second.result_identity
    assert compare(service, first, first)["no_material_changes"]
    support.run(repo)
    assert compare(service, first, second) == diff


@pytest.mark.parametrize("side", ["BASE", "TARGET"])
def test_missing_and_foreign_revision_errors(tmp_path, side):
    repo = support.authority.seed(tmp_path)
    first, other = support.run(repo), support.run(repo, language="zh-CN")
    service = ResearchLiteService(repo)
    for revision, code in [("f" * 64, f"RESEARCH_DIFF_{side}_NOT_FOUND"), (other.result_identity, "RESEARCH_DIFF_WRONG_RESEARCH")]:
        ids = [first.result_identity, first.result_identity]
        ids[0 if side == "BASE" else 1] = revision
        with pytest.raises(ResearchRejected, match=code):
            service.diff(first.packet.research_id, *ids)


def append_snapshot(repo, source, **changes):
    """Persist a bounded fixture snapshot through the actual sealed validator."""
    import uuid

    from youtube_intel.research_contract import ResearchRequest
    service = ResearchLiteService(repo)
    with repo._connect() as db:
        db.execute("BEGIN IMMEDIATE")
        number = db.execute("SELECT max(execution_number)+1 FROM research_results WHERE research_id=?", (source.packet.research_id,)).fetchone()[0]
        packet = source.packet.model_copy(update={"execution_id": uuid.uuid4().hex, "execution_number": number, **changes})
        if "evidence" in changes:
            packet = packet.model_copy(update={
                "material_status": "EVIDENCE_AVAILABLE" if packet.evidence else "INSUFFICIENT_MATERIAL",
                "unresolved": ["NO_SYNTHESIS", "LEXICAL_RETRIEVAL", *(["BOUNDED_PACKET"] if packet.retrieval_truncated else []), *([] if packet.evidence else ["NO_MATCHING_EVIDENCE"])],
            })
        return service._persist(db, ResearchRequest(question=packet.question, content_ids=[c.content_id for c in packet.scope]), packet)


def test_evidence_add_remove_content_references_and_both_material_transitions(tmp_path):
    repo = support.authority.seed(tmp_path)
    full = support.run(repo)
    empty = append_snapshot(repo, full, evidence=[], intelligence=[])
    restored = append_snapshot(repo, full)
    service = ResearchLiteService(repo)
    removed, added = compare(service, full, empty), compare(service, empty, restored)
    assert [e["evidence_id"] for e in removed["evidence"]["removed"]] == sorted(e.evidence_id for e in full.packet.evidence)
    assert not removed["evidence"]["added"]
    assert added["evidence"]["added"] == removed["evidence"]["removed"]
    assert removed["content"]["removed"][0]["content_id"] == support.authority.VIDEO
    assert added["content"]["added"] == removed["content"]["removed"]
    change = next(c for c in removed["packet_changes"] if c["field"] == "material_status")
    assert (change["base"], change["target"]) == ("EVIDENCE_AVAILABLE", "INSUFFICIENT_MATERIAL")
    change = next(c for c in added["packet_changes"] if c["field"] == "material_status")
    assert (change["base"], change["target"]) == ("INSUFFICIENT_MATERIAL", "EVIDENCE_AVAILABLE")
    assert compare(service, restored, full)["no_material_changes"]


def test_order_and_context_title_noise_are_not_product_changes(tmp_path):
    fixture = _load_module("test_task022_personalized_distillation")
    repo = fixture._repository(tmp_path)
    _, video = fixture._source_and_video(repo)
    for index in range(3):
        fixture._evidence(repo, video, start_ms=index * 1000, end_ms=index * 1000 + 500)
    first = support.run(repo, question="canonical", content_ids=[video])
    second = append_snapshot(repo, first, evidence=list(reversed(first.packet.evidence)), scope=[c.model_copy(update={"title": "Changed contextual label"}) for c in first.packet.scope])
    assert compare(ResearchLiteService(repo), first, second)["no_material_changes"]


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("field,value,code", [
    ("question", "another question", "RESEARCH_DIFF_UNTRUSTED_REVISION"),
    ("scope", [{"content_id": "other", "title": "other"}], "RESEARCH_DIFF_UNTRUSTED_REVISION"),
    ("output_language", "zh-CN", "RESEARCH_DIFF_UNTRUSTED_REVISION"),
    ("contract", "research-lite-v999", "RESEARCH_DIFF_INCOMPATIBLE_CONTRACT"),
    ("assembly_status", "FAILED", "RESEARCH_DIFF_UNTRUSTED_REVISION"),
    ("evidence", [{"fabricated": "NEVER EXPOSE"}], "RESEARCH_DIFF_UNTRUSTED_REVISION"),
])
def test_corrupt_or_identity_incompatible_sides_fail_closed(tmp_path, side, field, value, code):
    hostile = _load_module("test_research_adversarial")
    repo = support.authority.seed(tmp_path)
    results = [support.run(repo), support.run(repo)]
    hostile.damage(repo, results[side], lambda p: p.update({field: value}))
    with pytest.raises(ResearchRejected, match=code):
        compare(ResearchLiteService(repo), *results)


def test_all_domain_tables_unchanged_no_rerun_or_network(tmp_path, monkeypatch):
    import socket
    import urllib.request
    repo = support.authority.seed(tmp_path)
    first, second = support.run(repo), support.run(repo)
    def prohibited(*args, **kwargs):
        raise AssertionError("Diff attempted retrieval, provider dispatch or external request")
    monkeypatch.setattr(socket, "create_connection", prohibited)
    monkeypatch.setattr(urllib.request, "urlopen", prohibited)
    monkeypatch.setattr(ResearchLiteService, "assemble", prohibited)
    monkeypatch.setattr(ResearchLiteService, "_assemble_packet", prohibited, raising=False)
    with repo._connect() as db:
        before = list(db.iterdump())
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert not any("diff" in t for t in tables)
        assert db.execute("PRAGMA user_version").fetchone()[0] == 31
    assert compare(ResearchLiteService(repo), first, second)["no_material_changes"]
    with repo._connect() as db:
        assert list(db.iterdump()) == before


def test_restore_recomputes_exact_diff(tmp_path):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.state import SQLiteStateRepository
    repo = support.authority.seed(tmp_path)
    first = support.run(repo)
    second = append_snapshot(repo, first, evidence=[], intelligence=[])
    expected = compare(ResearchLiteService(repo), first, second)
    backup = BackupRestoreService(database=tmp_path / "state.sqlite3", data_root=tmp_path / "data")
    created = backup.create_backup()
    path, _ = backup.backup_download(created.backup_id)
    staged = backup.stage_restore(path.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert restored.initialize(now=support.authority.NOW).version == 31
    assert compare(ResearchLiteService(restored), first, second) == expected
    with restored._connect() as db:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()


def test_large_packet_stable_sort_and_complete_bounds(tmp_path):
    fixture = _load_module("test_task022_personalized_distillation")
    repo = fixture._repository(tmp_path)
    _, video = fixture._source_and_video(repo)
    for index in range(130):
        fixture._evidence(repo, video, start_ms=index * 1000, end_ms=index * 1000 + 500)
    first = support.run(repo, question="canonical", content_ids=[video])
    second = append_snapshot(repo, first, evidence=[], intelligence=[])
    diff = compare(ResearchLiteService(repo), second, first)
    assert len(diff["evidence"]["added"]) == diff["evidence_limit_per_side"] == 24
    assert first.packet.retrieval_truncated and diff["complete"]
    assert [e["evidence_id"] for e in diff["evidence"]["added"]] == sorted(e.evidence_id for e in first.packet.evidence)
    assert compare(ResearchLiteService(repo), second, first) == diff


def test_intelligence_reference_add_remove_and_later_authority_does_not_leak(tmp_path):
    from datetime import timedelta

    from youtube_intel.state import SQLiteStateRepository
    hostile = _load_module("test_research_adversarial")
    hostile.test_later_intelligence_revision_preserves_recorded_research(tmp_path)
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    service = ResearchLiteService(repo)
    first = service.read(service.list_current()["research"][0]["research_id"])
    no_interpretation = append_snapshot(repo, first, intelligence=[])
    diff = compare(service, no_interpretation, first)
    assert diff["interpretations"]["added"][0]["revision_id"] == first.packet.intelligence[0].revision_id
    assert diff["interpretations"]["added"][0]["revision_id"] != "recorded-following-revision"
    assert compare(service, first, no_interpretation)["interpretations"]["removed"] == diff["interpretations"]["added"]
    fixture = _load_module("test_task022_personalized_distillation")
    new = ResearchLiteService(repo, now=lambda: fixture.NOW + timedelta(days=2)).assemble(
        support.ResearchRequest(question=first.packet.question, content_ids=[c.content_id for c in first.packet.scope]), output_language="en")
    assert compare(service, no_interpretation, first) == diff
    # Current admission lacks the recorded card for this correction, so it is
    # truthfully omitted rather than substituted for the historical reference.
    assert not new.packet.intelligence
