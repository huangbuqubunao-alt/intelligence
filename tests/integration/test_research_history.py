"""Immutable History uses accepted execution authority, never a live replay."""

import sqlite3

import pytest
from conftest import _load_module

from youtube_intel.research_contract import canonical
from youtube_intel.research_lite import ResearchLiteService, ResearchRejected
from youtube_intel.state import SQLiteStateRepository

support = _load_module("test_research_lite")


def test_three_revisions_exact_reads_and_one_semantic_item(tmp_path):
    repo = support.authority.seed(tmp_path)
    service = ResearchLiteService(repo)
    first = support.run(repo)
    identity = first.packet.research_id
    assert service.history(identity)["revisions"] == []
    second, third = support.run(repo), support.run(repo)
    history = service.history(identity)
    assert [r["revision_id"] for r in history["revisions"]] == [second.result_identity, first.result_identity]
    assert history["current_revision_id"] == third.result_identity
    assert not history["has_more"]
    assert history["unavailable_count"] == 0
    assert all("packet" not in r and "evidence" not in r for r in history["revisions"])
    assert service.read_revision(identity, first.result_identity).as_dict() == first.as_dict()
    assert service.read(identity).as_dict() == third.as_dict()
    assert service.list_current()["total"] == 1
    restarted = ResearchLiteService(SQLiteStateRepository(tmp_path / "state.sqlite3"))
    assert restarted.history(identity) == history
    assert restarted.read_revision(identity, first.result_identity).as_dict() == first.as_dict()


def test_tied_pagination_is_stable_and_rerun_does_not_shift_pages(tmp_path):
    repo = support.authority.seed(tmp_path)
    results = [support.run(repo) for _ in range(8)]
    service = ResearchLiteService(repo)
    identity = results[0].packet.research_id
    page = service.history(identity, limit=2)
    seen = [r["revision_id"] for r in page["revisions"]]
    support.run(repo)
    while page["has_more"]:
        page = service.history(identity, limit=2, cursor=page["next_cursor"])
        seen.extend(r["revision_id"] for r in page["revisions"])
    assert seen == [r.result_identity for r in reversed(results[:-1])]
    assert len(seen) == len(set(seen))


def test_corrupt_old_revision_is_excluded_without_poisoning_valid_history(tmp_path):
    repo = support.authority.seed(tmp_path)
    first, second, third = [support.run(repo) for _ in range(3)]
    db = sqlite3.connect(tmp_path / "state.sqlite3")
    db.execute("DROP TRIGGER research_results_immutable_update")
    db.execute("UPDATE research_results SET payload_json='{}' WHERE result_identity=?", (first.result_identity,))
    db.commit()
    db.close()
    service = ResearchLiteService(repo)
    page = service.history(first.packet.research_id)
    assert [r["revision_id"] for r in page["revisions"]] == [second.result_identity]
    assert page["unavailable_count"] == 1
    assert service.read(first.packet.research_id).as_dict() == third.as_dict()
    with pytest.raises(ResearchRejected, match="CORRUPTED_RESULT"):
        service.read_revision(first.packet.research_id, first.result_identity)


def test_wrong_research_and_nonexistent_revision_rejected(tmp_path):
    repo = support.authority.seed(tmp_path)
    first, other = support.run(repo), support.run(repo, language="zh-CN")
    service = ResearchLiteService(repo)
    for research, revision in [(other.packet.research_id, first.result_identity), (first.packet.research_id, "f" * 64)]:
        with pytest.raises(ResearchRejected, match="REVISION_NOT_FOUND"):
            service.read_revision(research, revision)
    assert service.history(other.packet.research_id)["revisions"] == []
    with pytest.raises(ResearchRejected, match="NOT_FOUND"):
        service.history("f" * 64)
    with pytest.raises(ResearchRejected, match="INVALID_CURSOR"):
        service.history(other.packet.research_id, cursor=f"{first.packet.research_id}:2:1")


def test_history_does_not_mutate_any_domain_or_dispatch(tmp_path, monkeypatch):
    import socket
    import urllib.request

    repo = support.authority.seed(tmp_path)
    first = support.run(repo)
    support.run(repo)
    def prohibited(*args, **kwargs):
        raise AssertionError("History dispatched externally")
    monkeypatch.setattr(socket, "create_connection", prohibited)
    monkeypatch.setattr(urllib.request, "urlopen", prohibited)
    with repo._connect() as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before = {t: [tuple(r) for r in db.execute(f'SELECT * FROM "{t}"')] for t in tables}
    service = ResearchLiteService(repo)
    service.history(first.packet.research_id)
    service.read_revision(first.packet.research_id, first.result_identity)
    with repo._connect() as db:
        assert before == {t: [tuple(r) for r in db.execute(f'SELECT * FROM "{t}"')] for t in tables}
        assert not any("diff" in t for t in tables)


@pytest.mark.parametrize("failure", ["verify", "pointer"])
def test_failed_or_corrupt_rerun_rolls_back_revision_and_pointer(tmp_path, monkeypatch, failure):
    repo = support.authority.seed(tmp_path)
    first = support.run(repo)
    service = ResearchLiteService(repo, now=lambda: support.authority.NOW)
    if failure == "verify":
        def reject(*args, **kwargs):
            raise ResearchRejected("RESEARCH_CORRUPTED_RESULT")
        monkeypatch.setattr(service, "verify_row", reject)
    else:
        with repo._connect() as db:
            db.execute("CREATE TRIGGER reject_research_pointer BEFORE UPDATE ON research_items BEGIN SELECT RAISE(ABORT,'pointer failure'); END")
    with pytest.raises((ResearchRejected, sqlite3.IntegrityError)):
        service.assemble(support.ResearchRequest(question=first.packet.question, content_ids=[support.authority.VIDEO]), output_language="en")
    restarted = ResearchLiteService(repo)
    assert restarted.read(first.packet.research_id).as_dict() == first.as_dict()
    assert restarted.history(first.packet.research_id)["revisions"] == []
    with repo._connect() as db:
        assert db.execute("SELECT count(*) FROM research_results").fetchone()[0] == 1


def test_large_history_is_bounded_and_shared_evidence_validation_is_batched(tmp_path, monkeypatch):
    repo = support.authority.seed(tmp_path)
    results = [support.run(repo) for _ in range(32)]
    calls = []
    resolve = repo.resolve_verified_evidence_text_batch_in_transaction
    def record(connection, evidence_ids):
        calls.append(evidence_ids)
        return resolve(connection, evidence_ids)
    monkeypatch.setattr(repo, "resolve_verified_evidence_text_batch_in_transaction", record)
    page = ResearchLiteService(repo).history(results[0].packet.research_id)
    assert len(page["revisions"]) == page["limit"] == 25 and page["has_more"]
    assert len(calls) == 2  # current + one shared page batch, not one per revision
    next_page = ResearchLiteService(repo).history(results[0].packet.research_id, cursor=page["next_cursor"])
    assert len(next_page["revisions"]) == 6 and not next_page["has_more"]


def test_evidence_changes_do_not_rebuild_old_revision(tmp_path):
    repo = support.authority.seed(tmp_path)
    first = support.run(repo)
    support.run(repo)
    with repo._connect() as db:
        db.execute("UPDATE evidence SET availability='UNAVAILABLE' WHERE evidence_id=?", (first.packet.evidence[0].evidence_id,))
    service = ResearchLiteService(repo)
    with pytest.raises(ResearchRejected, match="SOURCE_AUTHORITY_UNAVAILABLE"):
        service.read_revision(first.packet.research_id, first.result_identity)
    page = service.history(first.packet.research_id)
    assert not page["revisions"] and not page["current_available"]
    assert page["unavailable_count"] == 2
    with repo._connect() as db:
        assert db.execute("SELECT payload_json FROM research_results WHERE result_identity=?", (first.result_identity,)).fetchone()[0] == canonical(first.packet.model_dump(mode="json"))


def test_historical_intelligence_keeps_its_recorded_revision_after_new_admission(tmp_path):
    from datetime import timedelta

    hostile = _load_module("test_research_adversarial")
    hostile.test_later_intelligence_revision_preserves_recorded_research(tmp_path)
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    service = ResearchLiteService(repo)
    identity = service.list_current()["research"][0]["research_id"]
    old = service.read(identity)
    new = ResearchLiteService(repo, now=lambda: _load_module("test_task022_personalized_distillation").NOW + timedelta(days=2)).assemble(
        support.ResearchRequest(question=old.packet.question, content_ids=[c.content_id for c in old.packet.scope]), output_language="en"
    )
    assert new.result_identity != old.result_identity
    assert service.read_revision(identity, old.result_identity).as_dict() == old.as_dict()
    assert service.history(identity)["revisions"][0]["revision_id"] == old.result_identity
    assert old.packet.intelligence[0].revision_id != "recorded-following-revision"


def test_corrupt_current_does_not_hide_valid_old_revision(tmp_path):
    repo = support.authority.seed(tmp_path)
    first, current = support.run(repo), support.run(repo)
    db = sqlite3.connect(tmp_path / "state.sqlite3")
    db.execute("DROP TRIGGER research_results_immutable_update")
    db.execute("UPDATE research_results SET payload_json='{}' WHERE result_identity=?", (current.result_identity,))
    db.commit()
    db.close()
    page = ResearchLiteService(repo).history(first.packet.research_id)
    assert page["current_revision_id"] is None and not page["current_available"]
    assert [r["revision_id"] for r in page["revisions"]] == [first.result_identity]
    assert page["unavailable_count"] == 1


def test_different_scope_does_not_merge_history_and_immutable_deletion_is_preserved(tmp_path):
    repo = support.authority.seed(tmp_path)
    first = support.run(repo)
    support.run(repo)
    other = support.authority.seed_other(tmp_path, repo)
    distinct = support.run(repo, content_ids=[other])
    assert distinct.packet.research_id != first.packet.research_id
    assert ResearchLiteService(repo).history(distinct.packet.research_id)["revisions"] == []
    with repo._connect() as db:
        for sql, identity in [
            ("DELETE FROM research_results WHERE result_identity=?", first.result_identity),
            ("UPDATE research_results SET payload_json='{}' WHERE result_identity=?", first.result_identity),
            ("DELETE FROM research_items WHERE research_id=?", first.packet.research_id),
        ]:
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                db.execute(sql, (identity,))
        assert not db.execute("PRAGMA foreign_key_check").fetchall()


@pytest.mark.parametrize("cursor", ["", "x", "a" * 121, "a" * 64 + ":0:0", "a" * 64 + ":999:1", "a" * 64 + ":2:3", "a" * 64 + ":2:-1"])
def test_malformed_cursor_is_bounded_rejected(tmp_path, cursor):
    repo = support.authority.seed(tmp_path)
    first = support.run(repo)
    with pytest.raises(ResearchRejected, match="INVALID_CURSOR"):
        ResearchLiteService(repo).history(first.packet.research_id, cursor=cursor)


def test_corrupt_new_packet_cannot_advance_current(tmp_path, monkeypatch):
    repo = support.authority.seed(tmp_path)
    first = support.run(repo)
    service = ResearchLiteService(repo, now=lambda: support.authority.NOW)
    persist = service._persist
    def corrupt(connection, request, packet):
        bad_ref = packet.evidence[0].model_copy(update={"excerpt": "Fabricated new packet"})
        return persist(connection, request, packet.model_copy(update={"evidence": [bad_ref]}))
    monkeypatch.setattr(service, "_persist", corrupt)
    with pytest.raises(ResearchRejected, match="SOURCE_AUTHORITY_UNAVAILABLE"):
        service.assemble(support.ResearchRequest(question=first.packet.question, content_ids=[support.authority.VIDEO]), output_language="en")
    assert ResearchLiteService(repo).read(first.packet.research_id).as_dict() == first.as_dict()
    with repo._connect() as db:
        assert db.execute("SELECT count(*) FROM research_results").fetchone()[0] == 1


def test_resealed_foreign_old_evidence_is_rejected_with_shared_page_cache(tmp_path):
    hostile = _load_module("test_research_adversarial")
    repo = support.authority.seed(tmp_path)
    other = support.authority.seed_other(tmp_path, repo)
    support.authority.service(repo).run(content_id=other)
    foreign = support.run(repo, content_ids=[other])
    first, current = support.run(repo), support.run(repo)
    hostile.damage(repo, first, lambda p: p["evidence"].__setitem__(0, foreign.packet.evidence[0].model_dump(mode="json")), reseal=True)
    with repo._connect() as db:
        db.execute("UPDATE research_items SET current_result_identity=? WHERE research_id=?", (current.result_identity, first.packet.research_id))
    page = ResearchLiteService(repo).history(first.packet.research_id)
    assert page["revisions"] == [] and page["unavailable_count"] == 1
    assert page["current_revision_id"] == current.result_identity


def test_all_corrupt_page_advances_cursor_to_valid_older_revision(tmp_path):
    repo = support.authority.seed(tmp_path)
    results = [support.run(repo) for _ in range(5)]
    db = sqlite3.connect(tmp_path / "state.sqlite3")
    db.execute("DROP TRIGGER research_results_immutable_update")
    for result in results[2:4]:
        db.execute("UPDATE research_results SET payload_json='{}' WHERE result_identity=?", (result.result_identity,))
    db.commit()
    db.close()
    service = ResearchLiteService(repo)
    page = service.history(results[0].packet.research_id, limit=2)
    assert page["has_more"] and not page["revisions"] and page["unavailable_count"] == 2
    next_page = service.history(results[0].packet.research_id, limit=2, cursor=page["next_cursor"])
    assert [r["revision_id"] for r in next_page["revisions"]] == [results[1].result_identity, results[0].result_identity]
