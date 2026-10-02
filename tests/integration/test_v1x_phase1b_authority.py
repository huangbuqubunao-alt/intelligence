"""Real SQLite authority, restart, failure, forgery and claim round trips."""

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import _load_module

from youtube_intel.deep_analysis_persistence import (
    DeepAnalysisPersistenceStore,
    _durable_authority_identity,
)
from youtube_intel.deep_analysis_service import (
    DeepAnalysisCapability,
    DeepAnalysisRejected,
    DeepAnalysisService,
    build_local_ollama_phase1b_route,
)
from youtube_intel.note_v2 import build_note_v2
from youtube_intel.state import SQLiteStateRepository

support = _load_module("test_analysis_atomic_persistence")
activation = _load_module("test_v1x_deep_analysis_activation")
contract = _load_module("test_v1x_phase1b_contract")
NOW = support.NOW
VIDEO = support.VIDEO_ID


def seed(tmp_path: Path) -> SQLiteStateRepository:
    repository = support._seed(tmp_path)
    data = tmp_path / "data" / "transcripts" / VIDEO
    data.mkdir(parents=True)
    (data / "canonical.txt").write_text("".join(support.CUE_TEXTS))
    repository.save_global_output_language(output_language="en", now=NOW)
    return repository


def service(repository: SQLiteStateRepository, *, mutate=None, capture=None) -> DeepAnalysisService:
    def transport(request, timeout):
        del timeout
        prompt = request["messages"][0]["content"]
        payload = json.loads(prompt.split("Authorized payload: ", 1)[1])
        candidates = payload["selected_evidence"]
        refs = [c["evidence_id"] for c in candidates]
        raw = contract.output(refs[0])
        # Two independent claims per role, with differing refs and ordering.
        for role in ("core_conclusion", "key_evidence", "uncertainty", "relevance_to_user", "next_question"):
            second = dict(raw[role][0])
            second["text"] += " This second claim retains its own evidence."
            second["evidence_refs"] = refs[-1:]
            raw[role].append(second)
        if mutate:
            mutate(raw, refs)
        if capture is not None:
            capture["output"] = raw
            capture["candidates"] = refs
        return {"model": "qwen2.5-coder:7b", "done": True, "done_reason": "stop", "message": {"content": json.dumps(raw)}}
    return DeepAnalysisService(
        repository=repository,
        capability=DeepAnalysisCapability((build_local_ollama_phase1b_route(transport=transport),)),
        scoring_reader=lambda video: activation._scoring_read(video),
        transcript_reader=lambda *, video_id: SimpleNamespace(language="en"),
        evidence_reader=lambda _: (), evidence_text_reader=lambda _: None,
        now=lambda: NOW,
    )


def test_durable_claims_restart_note_and_retry(tmp_path: Path) -> None:
    repository = seed(tmp_path)
    captured = {}
    instance = service(repository, capture=captured)
    view = instance.run(content_id=VIDEO)
    assert view.evidence_citation_status == "DURABLE_EVIDENCE_VERIFIED"
    assert len(view.roles) == 10
    assert all(claim.evidence_ids for claim in view.roles)
    assert not any(ref in captured["candidates"] for claim in view.roles for ref in claim.evidence_ids)
    restarted = SQLiteStateRepository(tmp_path / "state.sqlite3")
    stored = DeepAnalysisPersistenceStore(restarted).read_persisted_deep_analysis_result(result_identity=view.result_identity)
    assert stored is not None and stored.durable_result is not None
    note = build_note_v2(stored)
    assert {e.evidence_id for e in note.evidence_references} == {ref for claim in view.roles for ref in claim.evidence_ids}
    assert not any("Topics:" in entry.text for section in note.sections for entry in section.entries)
    assert service(restarted).read(content_id=VIDEO).as_dict() == view.as_dict()
    assert instance.run(content_id=VIDEO).result_identity == view.result_identity
    with repository._connect() as connection:
        assert connection.execute("SELECT count(*) FROM deep_analysis_persisted_results").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM deep_analysis_evidence").fetchone()[0] == len(note.evidence_references)
        assert not connection.execute("SELECT 1 FROM current_content_summaries").fetchall()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO deep_analysis_evidence SELECT * FROM deep_analysis_evidence LIMIT 1")


@pytest.mark.parametrize("forged", ["missing-candidate", "a" * 64, "mtitle-0-10-context"])
def test_provider_cannot_mint_or_cite_context(tmp_path: Path, forged: str) -> None:
    repository = seed(tmp_path)
    def mutate(raw, refs):
        del refs
        raw["key_evidence"][0]["evidence_refs"] = [forged]
    with pytest.raises(DeepAnalysisRejected):
        service(repository, mutate=mutate).run(content_id=VIDEO)
    with repository._connect() as connection:
        assert not connection.execute("SELECT * FROM deep_analysis_persisted_results").fetchall()
        assert not connection.execute("SELECT * FROM deep_analysis_evidence").fetchall()


def test_failed_promotion_rolls_back_every_new_authority_row(tmp_path: Path, monkeypatch) -> None:
    repository = seed(tmp_path)
    original = repository._promote_summary_evidence_in_transaction
    calls = []
    def fail_second(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(result)
        if len(calls) == 2:
            raise RuntimeError("injected promotion failure")
        return result
    with repository._connect() as connection:
        before = connection.execute("SELECT evidence_id FROM evidence ORDER BY evidence_id").fetchall()
    monkeypatch.setattr(repository, "_promote_summary_evidence_in_transaction", fail_second)
    with pytest.raises(RuntimeError, match="promotion failure"):
        service(repository).run(content_id=VIDEO)
    with repository._connect() as connection:
        assert connection.execute("SELECT evidence_id FROM evidence ORDER BY evidence_id").fetchall() == before
        assert not connection.execute("SELECT * FROM deep_analysis_persisted_results").fetchall()
        assert not connection.execute("SELECT * FROM deep_analysis_evidence").fetchall()


@pytest.mark.parametrize("sql", [
    "DELETE FROM deep_analysis_evidence",
    "UPDATE deep_analysis_persisted_results SET knowledge_content_json = '{}'",
    "UPDATE deep_analysis_persisted_results SET durable_authority_identity = 'forged'",
    "UPDATE deep_analysis_persisted_results SET persistence_version = 'unsupported'",
])
def test_restart_rejects_tampered_authority(tmp_path: Path, sql: str) -> None:
    repository = seed(tmp_path)
    view = service(repository).run(content_id=VIDEO)
    with repository._connect() as connection:
        connection.execute(sql)
    store = DeepAnalysisPersistenceStore(SQLiteStateRepository(tmp_path / "state.sqlite3"))
    assert store.read_persisted_deep_analysis_result(result_identity=view.result_identity) is None


def test_canonical_only_fails_before_dispatch(tmp_path: Path) -> None:
    repository = seed(tmp_path)
    activation._seed_content(repository, "canonical-only")
    with pytest.raises(DeepAnalysisRejected) as rejected:
        service(repository).run(content_id="canonical-only")
    assert rejected.value.status.availability.value == "EVIDENCE_UNAVAILABLE"


def seed_other(tmp_path: Path, repository: SQLiteStateRepository) -> str:
    video = "other-content"
    activation._seed_content(repository, video)
    data = tmp_path / "data" / "transcripts" / video
    data.mkdir(parents=True)
    text = "".join(support.CUE_TEXTS)
    (data / "canonical.txt").write_text(text)
    repository.upsert_artifact(support.ArtifactWrite(
        artifact_id="artifact-other", artifact_key="transcript/other", video_id=video,
        job_id=None, kind=support.ArtifactKind.TRANSCRIPT_CANONICAL,
        storage_root=support.StorageRoot.DATA, relative_path=f"transcripts/{video}/canonical.txt",
        content_hash=support.sha256(text.encode()).hexdigest(), provider="fixture", model=None,
        producer_version="fixture-v1", retention_class=support.RetentionClass.LONG_LIVED, expires_at=None,
    ), now=NOW)
    repository.create_timed_transcript(support.TimedTranscriptWrite.from_cues(
        video_id=video, canonical_artifact_id="artifact-other",
        cues=tuple(support.TimedTranscriptCueWrite(start_ms=i*1000, end_ms=(i+1)*1000, text=text)
                   for i, text in enumerate(support.CUE_TEXTS)),
    ), now=NOW)
    return video


def reseal(connection, result_identity: str, change) -> None:
    row = dict(connection.execute("SELECT * FROM deep_analysis_persisted_results WHERE result_identity=?", (result_identity,)).fetchone())
    payload = json.loads(row["knowledge_content_json"])
    change(payload)
    row["knowledge_content_json"] = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    connection.execute("UPDATE deep_analysis_persisted_results SET knowledge_content_json=?, durable_authority_identity=? WHERE result_identity=?",
                       (row["knowledge_content_json"], _durable_authority_identity(row), result_identity))


def test_candidate_without_promotion_rejected(tmp_path: Path, monkeypatch) -> None:
    repository = seed(tmp_path)
    monkeypatch.setattr(repository, "_promote_summary_evidence_in_transaction", lambda *a, **k: None)
    with pytest.raises(ValueError, match="promotion is missing"):
        service(repository).run(content_id=VIDEO)
    with repository._connect() as connection:
        assert not connection.execute("SELECT * FROM deep_analysis_persisted_results").fetchall()
        assert not connection.execute("SELECT * FROM deep_analysis_evidence").fetchall()


def test_promotion_into_other_content_rejected_atomically(tmp_path: Path, monkeypatch) -> None:
    from youtube_intel import deep_analysis_evidence
    repository = seed(tmp_path)
    other = seed_other(tmp_path, repository)
    foreign = service(repository).run(content_id=other)
    original = deep_analysis_evidence._plan_promotion
    def foreign_plan(candidate, **kwargs):
        plan = original(candidate, **kwargs)
        transcript = repository.get_verified_timed_transcript(video_id=other)
        candidate_b = deep_analysis_evidence.deep_analysis_candidates(transcript).candidates[0]
        return original(candidate_b, video_id=other, canonical_artifact_id=transcript.canonical_artifact_id,
                        timed_transcript_id=transcript.timed_transcript_id, timed_transcript_hash=transcript.timed_transcript_hash,
                        language=plan.language)
    monkeypatch.setattr(deep_analysis_evidence, "_plan_promotion", foreign_plan)
    with pytest.raises(ValueError, match="same-Content"):
        service(repository).run(content_id=VIDEO)
    with repository._connect() as connection:
        assert [r[0] for r in connection.execute("SELECT result_identity FROM deep_analysis_persisted_results")] == [foreign.result_identity]


@pytest.mark.parametrize("attack", ["claim_without_membership", "different_membership", "extra_membership", "cross_content", "resealed_text"])
def test_semantic_authority_attacks_fail_even_with_recomputed_hash(tmp_path: Path, attack: str) -> None:
    repository = seed(tmp_path)
    view = service(repository).run(content_id=VIDEO)
    other = seed_other(tmp_path, repository)
    foreign = service(repository).run(content_id=other)
    with repository._connect() as connection:
        original_id = connection.execute("SELECT evidence_id FROM evidence WHERE video_id=? AND lineage_kind!='EXTRACTION' LIMIT 1", (VIDEO,)).fetchone()[0]
        foreign_id = foreign.roles[0].evidence_ids[0]
        if attack == "claim_without_membership":
            reseal(connection, view.result_identity, lambda p: p["claims"][0].update(evidence_refs=[original_id]))
        elif attack == "different_membership":
            connection.execute("DELETE FROM deep_analysis_evidence WHERE result_identity=?", (view.result_identity,))
            connection.execute("INSERT INTO deep_analysis_evidence VALUES (?, ?, ?)", (view.result_identity, original_id, support.NOW.isoformat()))
        elif attack in {"extra_membership", "cross_content"}:
            connection.execute("INSERT INTO deep_analysis_evidence VALUES (?, ?, ?)", (view.result_identity, foreign_id if attack == "cross_content" else original_id, support.NOW.isoformat()))
            if attack == "cross_content":
                reseal(connection, view.result_identity, lambda p: p["claims"][0].update(evidence_refs=[foreign_id]))
        else:
            reseal(connection, view.result_identity, lambda p: p["claims"][0].update(text="This is a tampered claim with a recomputed hash."))
    assert DeepAnalysisPersistenceStore(repository).read_persisted_deep_analysis_result(result_identity=view.result_identity) is None


@pytest.mark.parametrize("point", ["result", "membership", "precommit"])
def test_transaction_failure_at_every_authority_stage_rolls_back(tmp_path: Path, monkeypatch, point: str) -> None:
    repository = seed(tmp_path)
    with repository._connect() as connection:
        before = [r[0] for r in connection.execute("SELECT evidence_id FROM evidence ORDER BY evidence_id")]
        if point != "precommit":
            table = "deep_analysis_persisted_results" if point == "result" else "deep_analysis_evidence"
            connection.execute(f"CREATE TRIGGER injected_failure BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT, 'injected authority failure'); END")
    instance = service(repository)
    if point == "precommit":
        def fail(*args, **kwargs):
            raise RuntimeError("injected authority failure")
        monkeypatch.setattr(instance._store, "_verify_row", fail)
    with pytest.raises((RuntimeError, sqlite3.IntegrityError), match="injected authority failure"):
        instance.run(content_id=VIDEO)
    with repository._connect() as connection:
        assert [r[0] for r in connection.execute("SELECT evidence_id FROM evidence ORDER BY evidence_id")] == before
        assert not connection.execute("SELECT * FROM deep_analysis_persisted_results").fetchall()
        assert not connection.execute("SELECT * FROM deep_analysis_evidence").fetchall()


def test_dangling_membership_is_prevented_by_database(tmp_path: Path) -> None:
    repository = seed(tmp_path)
    view = service(repository).run(content_id=VIDEO)
    with repository._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO deep_analysis_evidence VALUES (?, ?, ?)", (view.result_identity, "a"*64, support.NOW.isoformat()))


def test_old_phase1a_remains_visible_but_note_rejected(tmp_path: Path) -> None:
    from youtube_intel.note_v2 import NoteV2Error
    repository = seed(tmp_path)
    instance = activation._service(repository)
    view = instance.run(content_id=VIDEO)
    assert view.evidence_citation_status == "PENDING_DURABLE_EVIDENCE_CONVERGENCE"
    assert all(not claim.evidence_ids for claim in view.roles)
    stored = DeepAnalysisPersistenceStore(repository).read_persisted_deep_analysis_result(result_identity=view.result_identity)
    assert stored is not None
    with pytest.raises(NoteV2Error, match="Phase-1A"):
        build_note_v2(stored)


def test_corrupt_newer_native_row_falls_back_to_verified_old_result(tmp_path: Path) -> None:
    repository = seed(tmp_path)
    old = service(repository).run(content_id=VIDEO)
    # Represent a corrupt newer execution without issuing another dispatch.
    with repository._connect() as connection:
        row = dict(connection.execute("SELECT * FROM deep_analysis_persisted_results").fetchone())
        row.update(result_identity="b"*64, cache_identity="c"*64, created_at="2099-01-01T00:00:00Z", validated_at="2099-01-01T00:00:00Z", knowledge_content_json="{}")
        connection.execute(f"INSERT INTO deep_analysis_persisted_results ({', '.join(row)}) VALUES ({', '.join('?' for _ in row)})", tuple(row.values()))
    assert service(repository).read(content_id=VIDEO).result_identity == old.result_identity


@pytest.mark.parametrize("field,value", [
    ("provider_id", "forged-provider"), ("model_selection_identity", "b" * 64),
    ("transport_result_identity", "b" * 64), ("consent_identity", "b" * 64), ("ordinal", 2),
])
def test_restart_rejects_corrupted_attempt_provenance(tmp_path: Path, field: str, value) -> None:
    repository = seed(tmp_path)
    view = service(repository).run(content_id=VIDEO)
    with repository._connect() as connection:
        raw = json.loads(connection.execute("SELECT fallback_attempts_json FROM deep_analysis_persisted_results").fetchone()[0])
        raw[0][field] = value
        connection.execute("UPDATE deep_analysis_persisted_results SET fallback_attempts_json=?", (json.dumps(raw),))
    assert DeepAnalysisPersistenceStore(repository).read_persisted_deep_analysis_result(result_identity=view.result_identity) is None


def test_all_five_role_relationships_survive_note_and_snapshot(tmp_path: Path) -> None:
    repository = seed(tmp_path)
    def multiple_refs(raw, refs):
        for claims in [raw[role] for role in ("core_conclusion", "key_evidence", "uncertainty", "relevance_to_user", "next_question")]:
            claims[0]["evidence_refs"] = [refs[-1], refs[0]]
    instance = service(repository, mutate=multiple_refs)
    view = instance.run(content_id=VIDEO)
    read = DeepAnalysisPersistenceStore(repository).read_persisted_deep_analysis_result(result_identity=view.result_identity)
    note = build_note_v2(read)
    relationships = {(entry.text, entry.evidence_ids) for section in note.sections for entry in section.entries}
    for claim in view.roles:
        assert (claim.text, claim.evidence_ids) in relationships
    snapshot = json.loads(instance.canonical_snapshot(content_id=VIDEO))
    assert [claim["evidence_ids"] for claim in snapshot["roles"]] == [list(claim.evidence_ids) for claim in view.roles]
    assert [claim["language_validation"] for claim in snapshot["roles"]] == [claim.language_validation for claim in view.roles]


def test_chinese_output_keeps_original_english_evidence_and_mixed_script_uncertain(tmp_path: Path) -> None:
    repository = seed(tmp_path)
    repository.save_global_output_language(output_language="zh-CN", now=NOW)
    def chinese(raw, refs):
        del refs
        for role in ("core_conclusion", "key_evidence", "uncertainty", "relevance_to_user", "next_question"):
            for claim in raw[role]:
                claim["text"] = "这段内容支持目前的分析结论，但还需要核验。"
        raw["next_question"][-1]["text"] = "这个结论里 This claim about 数据 requires another source."
    view = service(repository, mutate=chinese).run(content_id=VIDEO)
    assert view.output_language == "zh-CN"
    assert view.roles[-1].language_validation == "UNCERTAIN"
    with repository._connect() as connection:
        assert {r[0] for r in connection.execute("SELECT language FROM evidence")} == {"en"}
    read = DeepAnalysisPersistenceStore(repository).read_persisted_deep_analysis_result(result_identity=view.result_identity)
    assert build_note_v2(read).language == "zh-CN"


def test_existing_durable_id_is_not_an_issued_candidate(tmp_path: Path) -> None:
    repository = seed(tmp_path)
    with repository._connect() as connection:
        actual = connection.execute("SELECT evidence_id FROM evidence LIMIT 1").fetchone()[0]
    def mint(raw, refs):
        del refs
        raw["core_conclusion"][0]["evidence_refs"] = [actual]
    with pytest.raises(DeepAnalysisRejected):
        service(repository, mutate=mint).run(content_id=VIDEO)


def test_native_runtime_success_is_not_note_authority_and_exact_persistence_retry_is_safe(tmp_path: Path, monkeypatch) -> None:
    from datetime import timedelta

    from youtube_intel.note_v2 import NoteV2Error

    repository = seed(tmp_path)
    instance = service(repository)
    original = instance._store.persist_trusted_deep_analysis_success
    captured = {}
    def persist(**kwargs):
        captured.update(kwargs)
        with pytest.raises(NoteV2Error, match="persisted durable"):
            build_note_v2(kwargs["success"])
        return original(**kwargs)
    monkeypatch.setattr(instance._store, "persist_trusted_deep_analysis_success", persist)
    view = instance.run(content_id=VIDEO)
    retry = original(**{**captured, "now": NOW + timedelta(hours=1)})
    assert retry.result_identity == view.result_identity
    assert retry.created_at == NOW
    assert build_note_v2(retry).evidence_references


def test_corrupt_newer_payload_encoding_preserves_older_verified_read(tmp_path: Path) -> None:
    repository = seed(tmp_path)
    view = service(repository).run(content_id=VIDEO)
    with repository._connect() as connection:
        row = dict(connection.execute("SELECT * FROM deep_analysis_persisted_results").fetchone())
        row.update(result_identity="b" * 64, cache_identity="c" * 64,
                   created_at="2099-01-01T00:00:00Z", validated_at="2099-01-01T00:00:00Z",
                   structured_payload_kind="JSON", structured_payload_bytes=b"\xff")
        connection.execute(f"INSERT INTO deep_analysis_persisted_results ({', '.join(row)}) VALUES ({', '.join('?' for _ in row)})", tuple(row.values()))
    store = DeepAnalysisPersistenceStore(repository)
    assert store.read_persisted_deep_analysis_result(result_identity="b" * 64) is None
    assert service(repository).read(content_id=VIDEO).result_identity == view.result_identity
