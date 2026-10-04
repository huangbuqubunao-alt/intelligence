"""Three-provider sealed reads, Research, Topic, Delta and portable authority."""

import hashlib
import io
import json
import sqlite3
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
from youtube_intel.knowledge_delta import KnowledgeDeltaService
from youtube_intel.local_content import LocalContentProvider
from youtube_intel.providers.bilibili import BilibiliAdapter
from youtube_intel.research_contract import ResearchRequest, digest
from youtube_intel.research_lite import ResearchLiteService
from youtube_intel.state import (
    DependencyEdgeWrite,
    DependencyRelation,
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
    MigrationError,
    SQLiteStateRepository,
    TopicAssociationKind,
)
from youtube_intel.topic import TopicApplicationService

fixtures = _load_module("test_bilibili_content")
authority = _load_module("test_v1x_phase1b_authority")
NOW = fixtures.NOW


def seed_three(tmp_path: Path):
    repo = authority.seed(tmp_path)
    local = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)
    local_id = local.import_bytes("notes.md", b"Sentence1 local research source.\n").content_id
    network = fixtures.PublicFixture()
    network.text = "Sentence1 Bilibili research source."
    bilibili = BilibiliContentProvider(repo, tmp_path / "data", adapter=BilibiliAdapter(fetch=network.fetch), now=lambda: NOW)
    bili_id = bilibili.import_input(fixtures.BV).content_id
    return repo, network, [authority.VIDEO, local_id, bili_id]


def test_three_provider_research_sealed_intelligence_topic_delta(tmp_path: Path) -> None:
    repo, network, content_ids = seed_three(tmp_path)
    research = ResearchLiteService(repo, now=lambda: NOW)
    request = ResearchRequest(question="sentence1", content_ids=content_ids)
    packet = research.assemble(request, output_language="en").packet
    assert {e.provider for e in packet.evidence} == {"YOUTUBE", "LOCAL", "BILIBILI"}
    assert {e.content_id for e in packet.evidence} == set(content_ids)
    repeated = research.assemble(request, output_language="en").packet
    assert repeated.model_dump(exclude={"execution_id", "execution_number"}) == packet.model_dump(exclude={"execution_id", "execution_number"})
    assert repeated.execution_id != packet.execution_id and repeated.execution_number == packet.execution_number + 1
    refs = tuple(e.evidence_id for e in packet.evidence)
    for ref in packet.evidence:
        verified = repo.resolve_verified_evidence_text(ref.evidence_id)
        assert verified is not None and verified.video_id == ref.content_id and verified.excerpt == ref.excerpt
    repo.create_intelligence(intelligence_id="three-provider-synthesis", now=NOW)
    repo.append_intelligence_revision(intelligence_id="three-provider-synthesis", revision=IntelligenceRevisionWrite(
        revision_id="three-provider-revision", interpretation_kind=IntelligenceInterpretationKind.SYNTHESIS,
        claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
        content_hash=digest({"fixture": "three-provider-provenance", "evidence_ids": refs}),
        state=IntelligenceState.NEW, reason="Deterministic three-provider provenance fixture; no model interpretation", evidence_ids=refs), now=NOW)
    for index, eid in enumerate(refs):
        repo.create_dependency_edge(DependencyEdgeWrite(edge_id=f"three-edge-{index}",
            dependent_revision_id="three-provider-revision", relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=eid, input_revision_id=None), now=NOW)
    sealed = AuthoritativeIntelligenceReader(repo).read_current("three-provider-synthesis")
    assert set(sealed.evidence_ids) == set(refs)
    with pytest.raises(TypeError, match="immutable"):
        sealed._evidence_ids = ()
    topic_service = TopicApplicationService(repo, now=lambda: NOW)
    assert not repo.list_topics()
    topic = topic_service.create_topic(command_id="three-provider-topic", name="Sources")
    association = topic_service.associate_intelligence(topic_id=topic.topic_id,
        intelligence_id="three-provider-synthesis", kind=TopicAssociationKind.NEW_INFORMATION)
    assert set(association.evidence_ids) == set(refs)
    delta = KnowledgeDeltaService(repo, now=lambda: NOW).read().as_dict()
    completed = next(c for c in delta["categories"] if c["kind"] == "content_completed")
    assert content_ids[-1] in {item["target"]["id"] for item in completed["items"]}
    assert not any("bilibili" in c["kind"].lower() for c in delta["categories"])
    network.offline = True
    restarted = SQLiteStateRepository(repo._database_path)
    restarted.bind_source_storage(tmp_path / "data")
    assert AuthoritativeIntelligenceReader(restarted).read_current("three-provider-synthesis").evidence_ids == sealed.evidence_ids
    restarted_packet = ResearchLiteService(restarted, now=lambda: NOW).assemble(request, output_language="en").packet
    assert restarted_packet.model_dump(exclude={"execution_id", "execution_number"}) == packet.model_dump(exclude={"execution_id", "execution_number"})


def test_three_provider_backup_restore_offline(tmp_path: Path) -> None:
    repo, network, ids = seed_three(tmp_path)
    request = ResearchRequest(question="sentence1", content_ids=ids)
    packet = ResearchLiteService(repo, now=lambda: NOW).assemble(request, output_language="en").packet
    before = {e.evidence_id: repo.resolve_verified_evidence_text(e.evidence_id) for e in packet.evidence}
    pointer = repo.current_local_summary_pointer(ids[-1])
    backup = BackupRestoreService(database=repo._database_path, data_root=tmp_path / "data")
    created = backup.create_backup()
    path, _ = backup.backup_download(created.backup_id)
    network.offline = True
    preview = backup.stage_restore(path.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(repo._database_path)
    restored.bind_source_storage(tmp_path / "data")
    assert restored.current_local_summary_pointer(ids[-1]) == pointer
    assert {eid: restored.resolve_verified_evidence_text(eid) for eid in before} == before
    assert ResearchLiteService(restored, now=lambda: NOW).read(packet.research_id).packet == packet
    restored_packet = ResearchLiteService(restored, now=lambda: NOW).assemble(request, output_language="en").packet
    assert restored_packet.model_dump(exclude={"execution_id", "execution_number"}) == packet.model_dump(exclude={"execution_id", "execution_number"})
    with restored._connect() as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 33


def test_corrupt_backed_up_caption_rejected_with_rehashed_archive(tmp_path: Path) -> None:
    repo, network, ids = seed_three(tmp_path)
    backup = BackupRestoreService(database=repo._database_path, data_root=tmp_path / "data")
    created = backup.create_backup()
    path, _ = backup.backup_download(created.backup_id)
    with zipfile.ZipFile(path) as archive:
        members = {entry.filename: archive.read(entry) for entry in archive.infolist()}
    target = next(name for name in members if "bilibili" in name and "source-caption" in name)
    caption = json.loads(members[target])
    caption["body"][0]["from"] = -1
    members[target] = json.dumps(caption).encode()
    manifest = json.loads(members["manifest.json"])
    # Keep the portable outer file envelope internally coherent; inner caption
    # authority must still reject the altered bytes instead of trusting the ZIP.
    for entry in manifest["data_files"]:
        if "data/" + entry["relative_path"] == target:
            entry["sha256"] = hashlib.sha256(members[target]).hexdigest()
            entry["size_bytes"] = len(members[target])
    members["manifest.json"] = json.dumps(manifest).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    before = repo.get_verified_timed_transcript(video_id=ids[-1])
    with pytest.raises(BackupRestoreError):
        backup.stage_restore(output.getvalue())
    assert repo.get_verified_timed_transcript(video_id=ids[-1]) == before
    assert not backup.restore_pending


def test_schema33_failure_atomic_and_upgrade_preserves_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    migrations = repo._load_migrations()
    old = tuple(m for m in migrations if m.version <= 32)
    monkeypatch.setattr(repo, "_load_migrations", lambda: old)
    assert repo.initialize(now=NOW).version == 32
    local = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)
    content_id = local.import_bytes("notes.txt", b"Existing Local authority.\n").content_id
    refs = repo.list_evidence_for_presentation(content_id)
    before = tuple(repo.resolve_verified_evidence_text(e) for e in refs)
    broken = replace(migrations[-1], sql=migrations[-1].sql + "\nCREATE TABLE invalid_syntax(;", checksum="f" * 64)
    monkeypatch.setattr(repo, "_load_migrations", lambda: (*old, broken))
    with pytest.raises(MigrationError, match="failed to apply migration 33"):
        repo.initialize(now=NOW)
    assert repo.schema_version().version == 32
    assert tuple(repo.resolve_verified_evidence_text(e) for e in refs) == before
    monkeypatch.setattr(repo, "_load_migrations", lambda: migrations)
    assert repo.initialize(now=NOW).version == 33
    assert tuple(repo.resolve_verified_evidence_text(e) for e in refs) == before
    with repo._connect() as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert 29 not in {r[0] for r in connection.execute("SELECT version FROM schema_migrations")}
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE content_source_snapshots SET provider='BILIBILI' WHERE content_id=?", (content_id,))
