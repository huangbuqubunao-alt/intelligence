"""Phase 7 adversarial source, exact-range and mixed-source integration gates."""

from __future__ import annotations

import io
import json
import socket
import subprocess
import wave
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.local_content import (
    LocalContentProvider,
    LocalImportError,
    MediaTranscript,
    selected_file_bytes,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.research_contract import ResearchRequest
from youtube_intel.research_lite import ResearchLiteService, ResearchRejected
from youtube_intel.source_authority import MAX_MEDIA_BYTES, MAX_TEXT_BYTES
from youtube_intel.state import (
    MigrationError,
    SQLiteStateRepository,
    TimedTranscriptCueWrite,
)

NOW = datetime(2026, 10, 3, tzinfo=UTC)


@pytest.fixture
def local(tmp_path):
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    return LocalContentProvider(repository, tmp_path / "data", now=lambda: NOW)


def wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(16000)
        sound.writeframes(b"\x00\x00" * 16000)
    return output.getvalue()


class FakeTimedTranscriber:
    def transcribe(self, snapshot, *, duration_seconds):
        assert snapshot.is_file() and 0 < duration_seconds <= 2
        return MediaTranscript(
            "en",
            (
                TimedTranscriptCueWrite(
                    start_ms=0,
                    end_ms=500,
                    text="Local research evidence is reproducible.",
                ),
            ),
            "fixture-offline-transcriber-v1",
        )


@pytest.mark.parametrize("extension", [".wav", ".mp3", ".m4a", ".mp4", ".mov", ".m4v"])
def test_real_media_formats_accept_truthful_processing(
    local, tmp_path, extension, monkeypatch
):
    source = tmp_path / "fixture.wav"
    source.write_bytes(wav_bytes())
    output = tmp_path / ("fixture" + extension)
    if extension != ".wav":
        command = ["ffmpeg", "-v", "error", "-y", "-i", str(source)]
        if extension in {".mp4", ".mov", ".m4v"}:
            command = [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=32x32:r=5:d=1",
                "-i",
                str(source),
                "-shortest",
                "-c:v",
                "mpeg4",
            ]
        subprocess.run(
            [*command, str(output)], check=True, timeout=20, capture_output=True
        )
    run = subprocess.run
    probes = []

    def bounded_probe(command, **kwargs):
        probes.append(command)
        return run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", bounded_probe)
    result = local.import_bytes(output.name, output.read_bytes())
    assert len(probes) == 1
    assert probes[0][probes[0].index("-f") + 1] == {".mp3": "mp3", ".wav": "wav"}.get(
        extension, "mov"
    )
    assert result.status == "TRANSCRIPTION_UNAVAILABLE"
    assert local.repository.get_video(result.content_id) is not None
    assert source.read_bytes() == wav_bytes()


def test_trusted_media_has_real_timed_locator_and_normal_summary(local):
    local.transcriber = FakeTimedTranscriber()
    result = local.import_bytes("voice.wav", wav_bytes())
    assert result.status == "READY"
    ids = local.repository.list_evidence_for_presentation(result.content_id)
    text = local.repository.resolve_verified_evidence_text(ids[0])
    assert (
        text
        and text.locator_type == "TIMED_MEDIA"
        and text.start_ms == 0
        and text.end_ms == 500
    )
    pointer = local.repository.current_local_summary_pointer(result.content_id)
    assert pointer
    assert (
        ExtractiveSummaryService(local.repository, local.data_root)
        .read(result.content_id, pointer.artifact_id)
        .result.evidence[0]
        .evidence_id
        == ids[0]
    )


@pytest.mark.parametrize("payload", [b"not media", b"RIFF\x00\x00WAVE", b"\x00" * 200])
def test_malformed_media_never_gains_content_authority(local, payload):
    with pytest.raises(LocalImportError, match="LOCAL_INVALID_MEDIA"):
        local.import_bytes("bad.mp4", payload)
    assert not local.repository.list_videos()


def test_playlist_disguised_as_audio_never_gains_authority(local, tmp_path):
    private = tmp_path / "not-selected.wav"
    private.write_bytes(wav_bytes())
    playlist = f"#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXTINF:1,\n{private}\n#EXT-X-ENDLIST\n".encode()
    with pytest.raises(LocalImportError, match="LOCAL_INVALID_MEDIA"):
        local.import_bytes("disguised.mp3", playlist)
    assert not local.repository.list_videos()
    assert private.read_bytes() == wav_bytes()


@pytest.mark.parametrize(
    ("filename", "maximum"), [("big.txt", MAX_TEXT_BYTES), ("big.wav", MAX_MEDIA_BYTES)]
)
def test_size_limits_before_storage(local, filename, maximum):
    with pytest.raises(LocalImportError, match="LOCAL_FILE_TOO_LARGE"):
        local.import_bytes(filename, b"x" * (maximum + 1))
    assert not local.data_root.exists()


@pytest.mark.parametrize(
    "filename",
    [
        "../../escape.txt",
        "/Users/private/person/notes.txt",
        "C:\\private\\notes.txt",
        "\x00\x1bodd\u202e名.txt",
    ],
)
def test_names_cannot_choose_storage_or_leak_paths(local, filename, tmp_path):
    result = local.import_bytes(filename, b"Canonical text evidence.\n")
    app = LocalApiApplication(
        local.repository,
        ProductOrchestrationService(local.repository),
        data_root=local.data_root,
    )
    payload = json.dumps(
        app.handle("GET", "/api/v1/videos/" + result.content_id)[1], ensure_ascii=False
    )
    assert (
        "/Users/private" not in payload
        and "C:\\private" not in payload
        and "../" not in payload
    )
    assert "\\u0000" not in payload and "\\u001b" not in payload
    assert not (tmp_path / "escape.txt").exists()
    with local.repository._connect() as db:
        paths = [r[0] for r in db.execute("SELECT relative_path FROM artifacts")]
    assert all(".." not in path and not path.startswith("/") for path in paths)


def test_original_move_delete_mutation_dedupe_and_changed_import(local, tmp_path):
    original = tmp_path / "original.md"
    payload = b"# Heading\r\nExact **markdown** <script>safe text</script>.\n"
    original.write_bytes(payload)
    result = local.import_bytes(original.name, selected_file_bytes(original))
    assert original.read_bytes() == payload
    original.rename(tmp_path / "moved.md")
    (tmp_path / "moved.md").write_bytes(b"Changed original research.\n")
    changed = local.import_bytes("changed.md", (tmp_path / "moved.md").read_bytes())
    assert changed.content_id != result.content_id
    (tmp_path / "moved.md").unlink()
    same = local.import_bytes("other.txt", payload)
    assert same.duplicate and same.content_id == result.content_id
    pointer = local.repository.current_local_summary_pointer(result.content_id)
    assert pointer
    verified = ExtractiveSummaryService(local.repository, local.data_root).read(
        result.content_id, pointer.artifact_id
    )
    assert verified.result.evidence[0].excerpt == "# Heading\r\n"
    with local.repository._connect() as db:
        source = db.execute(
            "SELECT * FROM content_source_snapshots WHERE content_id=?",
            (result.content_id,),
        ).fetchone()
        assert source["canonical_text"] == payload.decode("utf-8")


def test_selected_symlink_replacement_reads_one_selected_inode(local, tmp_path):
    original = tmp_path / "original.txt"
    other = tmp_path / "other.txt"
    link = tmp_path / "selected.txt"
    original.write_bytes(b"Original selected bytes.\n")
    other.write_bytes(b"Other target bytes.\n")
    link.symlink_to(original)

    def replace():
        link.unlink()
        link.symlink_to(other)

    payload = selected_file_bytes(link, after_open=replace)
    assert payload == original.read_bytes()
    result = local.import_bytes(link.name, payload)
    original.unlink()
    other.unlink()
    assert local.repository.resolve_verified_evidence_text(
        local.repository.list_evidence_for_presentation(result.content_id)[0]
    )


def test_selected_inplace_mutation_rejected(tmp_path):
    original = tmp_path / "selected.txt"
    original.write_bytes(b"Original selected bytes.\n")
    with pytest.raises(LocalImportError, match="LOCAL_FILE_CHANGED"):
        selected_file_bytes(
            original, after_open=lambda: original.write_bytes(b"Changed data.\n")
        )


def test_managed_symlink_is_never_source_authority(local, tmp_path):
    local.data_root.mkdir()
    (local.data_root / "transcripts").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(OSError):
        local.import_bytes("selected.txt", b"Canonical source material.\n")
    assert not (tmp_path / "local").exists()


def test_source_and_canonical_tamper_fail_closed(local):
    result = local.import_bytes("notes.txt", b"Research evidence stays local.\n")
    eid = local.repository.list_evidence_for_presentation(result.content_id)[0]
    with local.repository._connect() as db:
        canonical = db.execute(
            "SELECT relative_path FROM artifacts WHERE artifact_id=(SELECT canonical_artifact_id FROM content_source_snapshots WHERE content_id=?)",
            (result.content_id,),
        ).fetchone()[0]
        snapshot = db.execute(
            "SELECT relative_path FROM artifacts WHERE artifact_id=(SELECT snapshot_artifact_id FROM content_source_snapshots WHERE content_id=?)",
            (result.content_id,),
        ).fetchone()[0]
    (local.data_root / canonical).write_bytes(b"Tampered canonical text.\n")
    assert local.repository.resolve_verified_evidence_text(eid) is None
    (local.data_root / canonical).write_bytes(b"Research evidence stays local.\n")
    (local.data_root / snapshot).write_bytes(b"Tampered imported source.\n")
    assert local.repository.resolve_verified_evidence_text(eid) is None
    with pytest.raises(ResearchRejected, match="RESEARCH_SOURCE_AUTHORITY_UNAVAILABLE"):
        ResearchLiteService(local.repository).assemble(
            ResearchRequest(question="research", content_ids=[result.content_id]),
            output_language="en",
        )


def test_no_network_model_or_folder_scan(local, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("external execution during local import")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(Path, "rglob", forbidden)
    monkeypatch.setattr(Path, "glob", forbidden)
    result = local.import_bytes("plain.txt", b"Research is fully local.\n")
    assert result.status == "READY"


def test_research_and_backup_restore_preserve_source_text(local, tmp_path):
    result = local.import_bytes(
        "notes.md", b"# Research\nResearch evidence stays on device.\n"
    )
    service = ResearchLiteService(local.repository, now=lambda: NOW)
    request = ResearchRequest(question="research", content_ids=[result.content_id])
    first = service.assemble(request, output_language="en")
    assert (
        first.packet.evidence and first.packet.evidence[0].locator_type == "TEXT_RANGE"
    )
    assert service.read(first.packet.research_id).packet == first.packet
    backup = BackupRestoreService(
        database=local.repository._database_path, data_root=local.data_root
    )
    created = backup.create_backup()
    archive = backup.backup_download(created.backup_id)[0].read_bytes()
    target = tmp_path / "restore"
    target.mkdir()
    restore = BackupRestoreService(
        database=target / "state.sqlite", data_root=target / "data"
    )
    stage = restore.stage_restore(archive)
    restore.confirm_restore(stage.restore_id)
    restore.recover_and_apply_pending_restore()
    assert (target / "state.sqlite").is_file()
    repo = SQLiteStateRepository(target / "state.sqlite")
    repo.bind_source_storage(target / "data")
    assert (
        ResearchLiteService(repo).read(first.packet.research_id).packet == first.packet
    )
    restored = LocalContentProvider(repo, target / "data").import_bytes(
        "again.md", b"# Research\nResearch evidence stays on device.\n"
    )
    assert restored.duplicate


def test_backup_rejects_tampered_source(local):
    result = local.import_bytes("notes.txt", b"Research source bytes.\n")
    with local.repository._connect() as db:
        path = db.execute(
            "SELECT relative_path FROM artifacts WHERE artifact_id=(SELECT snapshot_artifact_id FROM content_source_snapshots WHERE content_id=?)",
            (result.content_id,),
        ).fetchone()[0]
    (local.data_root / path).write_bytes(b"Tampered.\n")
    with pytest.raises(BackupRestoreError):
        BackupRestoreService(
            database=local.repository._database_path, data_root=local.data_root
        ).create_backup()


def test_interrupted_ready_transaction_recovers_without_partial_authority(
    local, monkeypatch
):
    original = local._text_evidence

    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("simulated interruption before READY")

    monkeypatch.setattr(local, "_text_evidence", interrupted)
    with pytest.raises(RuntimeError, match="interruption"):
        local.import_bytes("retry.txt", b"Research evidence survives retry.\n")
    with local.repository._connect() as db:
        assert (
            db.execute("SELECT status FROM content_source_snapshots").fetchone()[0]
            == "IMPORTED"
        )
        assert db.execute("SELECT count(*) FROM evidence").fetchone()[0] == 0
    monkeypatch.setattr(local, "_text_evidence", original)
    result = local.import_bytes("retry.txt", b"Research evidence survives retry.\n")
    assert result.duplicate and result.status == "READY"
    assert local.repository.resolve_verified_evidence_text(
        local.repository.list_evidence_for_presentation(result.content_id)[0]
    )


def test_foreign_content_range_cannot_bind(local):
    import sqlite3

    first = local.import_bytes("first.txt", b"First research authority.\n")
    second = local.import_bytes("second.txt", b"Second research authority.\n")
    with local.repository._connect() as db:
        artifact = db.execute(
            "SELECT canonical_artifact_id FROM content_source_snapshots WHERE content_id=?",
            (first.content_id,),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match="mismatched"):
            db.execute(
                "INSERT INTO evidence(evidence_id,video_id,artifact_id,locator_type,start_offset,end_offset,lineage_kind,role,language,availability,created_at,source_excerpt) VALUES('forged',?,?,'TEXT_RANGE',0,5,'ORIGINAL_TRANSCRIPT','PRIMARY_ORIGINAL','und','AVAILABLE',?,'First')",
                (second.content_id, artifact, NOW.isoformat()),
            )


def test_media_snapshot_tamper_invalidates_transcript_and_evidence(local):
    local.transcriber = FakeTimedTranscriber()
    result = local.import_bytes("voice.wav", wav_bytes())
    eid = local.repository.list_evidence_for_presentation(result.content_id)[0]
    assert local.repository.get_verified_timed_transcript(video_id=result.content_id)
    with local.repository._connect() as db:
        path = db.execute(
            "SELECT relative_path FROM artifacts WHERE artifact_id=(SELECT snapshot_artifact_id FROM content_source_snapshots WHERE content_id=?)",
            (result.content_id,),
        ).fetchone()[0]
    (local.data_root / path).write_bytes(b"corrupt media")
    assert (
        local.repository.get_verified_timed_transcript(video_id=result.content_id)
        is None
    )
    assert local.repository.resolve_verified_evidence_text(eid) is None


def test_media_backup_restore_keeps_real_source_and_timed_evidence(local):
    local.transcriber = FakeTimedTranscriber()
    result = local.import_bytes("voice.wav", wav_bytes())
    eid = local.repository.list_evidence_for_presentation(result.content_id)[0]
    expected = local.repository.resolve_verified_evidence_text(eid)
    service = BackupRestoreService(
        database=local.repository._database_path, data_root=local.data_root
    )
    created = service.create_backup()
    path, _ = service.backup_download(created.backup_id)
    staged = service.stage_restore(path.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    repo = SQLiteStateRepository(local.repository._database_path)
    repo.bind_source_storage(local.data_root)
    assert repo.resolve_verified_evidence_text(eid) == expected
    assert repo.get_verified_timed_transcript(video_id=result.content_id)


def test_mixed_source_research_intelligence_topic_and_knowledge_delta(tmp_path):
    from conftest import _load_module

    from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
    from youtube_intel.knowledge_delta import KnowledgeDeltaService
    from youtube_intel.state import (
        IntelligenceClaimKind,
        IntelligenceInterpretationKind,
        IntelligenceRevisionWrite,
        IntelligenceState,
        TopicAssociationKind,
    )
    from youtube_intel.topic import TopicApplicationService

    authority = _load_module("test_v1x_phase1b_authority")
    repo = authority.seed(tmp_path)
    local = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)
    imported = local.import_bytes("notes.md", b"Sentence1 local research source.\n")
    service = ResearchLiteService(repo, now=lambda: NOW)
    request = ResearchRequest(
        question="sentence1", content_ids=[authority.VIDEO, imported.content_id]
    )
    packet = service.assemble(request, output_language="en").packet
    assert {e.provider for e in packet.evidence} == {"YOUTUBE", "LOCAL"}
    assert {e.content_id for e in packet.evidence} == set(request.content_ids)
    for ref in packet.evidence:
        verified = repo.resolve_verified_evidence_text(ref.evidence_id)
        assert verified.video_id == ref.content_id and verified.excerpt == ref.excerpt
    repeat = service.assemble(request, output_language="en").packet
    assert packet.evidence == repeat.evidence and packet.scope == repeat.scope
    assert packet.research_id == repeat.research_id
    evidence = tuple(e.evidence_id for e in packet.evidence)
    repo.create_intelligence(intelligence_id="mixed-synthesis", now=NOW)
    repo.append_intelligence_revision(
        intelligence_id="mixed-synthesis",
        revision=IntelligenceRevisionWrite(
            revision_id="mixed-revision",
            interpretation_kind=IntelligenceInterpretationKind.SYNTHESIS,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash="a" * 64,
            state=IntelligenceState.NEW,
            reason="Fixture mixed-source provenance, no model conclusion",
            evidence_ids=evidence,
        ),
        now=NOW,
    )
    from youtube_intel.state import DependencyEdgeWrite, DependencyRelation

    for index, eid in enumerate(evidence):
        repo.create_dependency_edge(
            DependencyEdgeWrite(
                edge_id=f"mixed-edge-{index}",
                dependent_revision_id="mixed-revision",
                relation=DependencyRelation.EVIDENCE_SUPPORT,
                input_evidence_id=eid,
                input_revision_id=None,
            ),
            now=NOW,
        )
    read = AuthoritativeIntelligenceReader(repo).read_current("mixed-synthesis")
    assert set(read.evidence_ids) == set(evidence)
    topics = TopicApplicationService(repo, now=lambda: NOW)
    assert not repo.list_topics()
    topic = topics.create_topic(command_id="mixed-topic", name="Research sources")
    association = topics.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="mixed-synthesis",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    assert set(association.evidence_ids) == set(evidence)
    delta = KnowledgeDeltaService(repo, now=lambda: NOW).read().as_dict()
    completed = next(c for c in delta["categories"] if c["kind"] == "content_completed")
    assert any(
        item["target"]["id"] == imported.content_id for item in completed["items"]
    )
    app = LocalApiApplication(
        repo, ProductOrchestrationService(repo), data_root=local.data_root
    )
    status, dto = app.handle("GET", "/api/v1/intelligence/mixed-synthesis")
    assert status == 200 and {
        p["provider"] for p in dto["intelligence"]["source_provenance"]
    } == {"LOCAL", "YOUTUBE"}


def test_local_cannot_enter_external_or_youtube_processing_routes(local):
    from youtube_intel.local_api import ApiError

    result = local.import_bytes("notes.txt", b"Private research source.\n")
    app = LocalApiApplication(
        local.repository,
        ProductOrchestrationService(local.repository),
        data_root=local.data_root,
    )
    for route in [
        f"/api/v1/videos/{result.content_id}/cloud-intelligence/review",
        f"/api/v1/videos/{result.content_id}/cloud-intelligence/confirm",
        f"/api/v1/sources/local-library/videos/{result.content_id}/manual-analyze",
        f"/api/v1/sources/local-library/videos/{result.content_id}/distill",
    ]:
        with pytest.raises(ApiError) as error:
            app.handle("POST", route, b"{}")
        assert error.value.code == "LOCAL_PROVIDER_CAPABILITY_UNAVAILABLE"
    assert (
        ProductOrchestrationService(local.repository)
        .check_source("local-library")
        .status.value
        == "BLOCKED"
    )


def test_local_timed_media_fits_existing_da_fixture_authority(local):
    from conftest import _load_module

    local.transcriber = FakeTimedTranscriber()
    result = local.import_bytes("voice.wav", wav_bytes())
    authority = _load_module("test_v1x_phase1b_authority")
    local.repository.save_global_output_language(output_language="en", now=NOW)
    service = authority.service(local.repository)
    view = service.run(content_id=result.content_id)
    assert view.evidence_citation_status == "DURABLE_EVIDENCE_VERIFIED"
    for claim in view.roles:
        for eid in claim.evidence_ids:
            evidence = local.repository.resolve_verified_evidence_text(eid)
            assert (
                evidence.video_id == result.content_id
                and evidence.locator_type == "TIMED_MEDIA"
            )
    assert service.read(content_id=result.content_id).as_dict() == view.as_dict()


@pytest.mark.parametrize(
    "attack", ["snapshot_hash", "range_excerpt", "missing_trigger", "cue_time"]
)
def test_corrupt_archive_source_authority_rejected_without_live_mutation(
    local, tmp_path, attack
):
    from conftest import _load_module

    from youtube_intel.source_authority import sha256

    local.transcriber = FakeTimedTranscriber()
    result = (
        local.import_bytes("voice.wav", wav_bytes())
        if attack == "cue_time"
        else local.import_bytes("notes.txt", b"Research source authority.\n")
    )
    backup = BackupRestoreService(
        database=local.repository._database_path, data_root=local.data_root
    )
    created = backup.create_backup()
    path, _ = backup.backup_download(created.backup_id)
    raw = path.read_bytes()

    def mutate(db):
        table = (
            "timed_transcript_cues"
            if attack == "cue_time"
            else "evidence_source_ranges"
            if attack == "range_excerpt"
            else "content_source_snapshots"
        )
        triggers = db.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
            (table,),
        ).fetchall()
        for name, _ in triggers:
            db.execute(f'DROP TRIGGER "{name}"')
        if attack == "snapshot_hash":
            db.execute("UPDATE content_source_snapshots SET source_hash=?", ("f" * 64,))
        if attack == "range_excerpt":
            db.execute("UPDATE evidence_source_ranges SET excerpt='forged text'")
        if attack == "cue_time":
            db.execute("UPDATE timed_transcript_cues SET end_ms=600")
        if attack != "missing_trigger":
            for _, sql in triggers:
                db.execute(sql)

    corrupt = _load_module("test_v1x_phase1b_backup_restore").alter_archive(
        tmp_path, raw, mutate
    )
    before = sha256(local.repository._database_path.read_bytes())
    with pytest.raises(BackupRestoreError):
        backup.stage_restore(corrupt)
    assert sha256(local.repository._database_path.read_bytes()) == before
    assert not backup.restore_pending
    assert local.repository.get_video(result.content_id)


def test_logical_content_removal_never_deletes_original_or_snapshot(local, tmp_path):
    from youtube_intel.domain import Availability

    original = tmp_path / "original.txt"
    original.write_bytes(b"User-owned research.\n")
    result = local.import_bytes(original.name, selected_file_bytes(original))
    with local.repository._connect() as db:
        db.execute(
            "UPDATE videos SET availability=? WHERE video_id=?",
            (Availability.DELETED.value, result.content_id),
        )
        snapshot = db.execute(
            "SELECT a.relative_path FROM artifacts a JOIN content_source_snapshots s ON s.snapshot_artifact_id=a.artifact_id WHERE s.content_id=?",
            (result.content_id,),
        ).fetchone()[0]
    assert original.read_bytes() == b"User-owned research.\n"
    assert (local.data_root / snapshot).read_bytes() == original.read_bytes()
    assert (
        local.repository.resolve_verified_evidence_text(
            local.repository.list_evidence_for_presentation(result.content_id)[0]
        )
        is None
    )


def test_duplicate_cannot_bypass_extension_container_validation(local):
    payload = wav_bytes()
    local.import_bytes("voice.wav", payload)
    with pytest.raises(LocalImportError, match="LOCAL_INVALID_MEDIA"):
        local.import_bytes("fake.mp3", payload)
    text = b"Original text bytes.\n"
    local.import_bytes("notes.txt", text)
    with pytest.raises(LocalImportError, match="LOCAL_INVALID_MEDIA"):
        local.import_bytes("fake.mp4", text)


def test_original_text_summary_does_not_claim_english_translation(local):
    result = local.import_bytes(
        "中文.md", "原始中文证据，不应标记成英文翻译。\n".encode()
    )
    app = LocalApiApplication(
        local.repository,
        ProductOrchestrationService(local.repository),
        data_root=local.data_root,
    )
    status, detail = app.handle("GET", f"/api/v1/videos/{result.content_id}", b"")
    assert status == 200
    summary = detail["note"]["v2"]
    assert summary["language"] == "und"
    assert summary["method"] == "SOURCE_EXCERPTS"
    assert summary["summary"] == "原始中文证据，不应标记成英文翻译。\n"


def test_schema31_upgrade_preserves_all_evidence_dependency_guards(
    tmp_path, monkeypatch
):
    repo = SQLiteStateRepository(tmp_path / "migration.sqlite")
    migrations = repo._load_migrations()
    monkeypatch.setattr(
        repo,
        "_load_migrations",
        lambda: tuple(m for m in migrations if m.version <= 31),
    )
    assert repo.initialize(now=NOW).version == 31
    with repo._connect() as db:
        previous = dict(
            db.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name IN ('evidence','source_subscriptions','videos')"
            )
        )
        history = [
            tuple(r)
            for r in db.execute("SELECT * FROM schema_migrations ORDER BY version")
        ]
    monkeypatch.undo()
    assert repo.initialize(now=NOW).version == 32
    with repo._connect() as db:
        current = dict(
            db.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name IN ('evidence','source_subscriptions','videos')"
            )
        )
        assert set(previous) <= set(current)
        assert (
            previous["evidence_availability_requires_no_current_support"]
            == current["evidence_availability_requires_no_current_support"]
        )
        assert [
            tuple(r)
            for r in db.execute("SELECT * FROM schema_migrations ORDER BY version")
        ][:-1] == history
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert 29 not in [
            r[0] for r in db.execute("SELECT version FROM schema_migrations")
        ]


def test_schema32_rebuild_failure_rolls_back_entire_authority_and_retries(
    tmp_path, monkeypatch
):
    repo = SQLiteStateRepository(tmp_path / "migration.sqlite")
    migrations = repo._load_migrations()
    previous = tuple(m for m in migrations if m.version <= 31)
    monkeypatch.setattr(repo, "_load_migrations", lambda: previous)
    assert repo.initialize(now=NOW).version == 31
    with repo._connect() as db:
        schema = db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
        ).fetchall()
        history = db.execute(
            "SELECT * FROM schema_migrations ORDER BY version"
        ).fetchall()
    broken = replace(
        migrations[-1],
        sql=migrations[-1].sql + "\nCREATE TABLE invalid_syntax(;",
        checksum="f" * 64,
    )
    monkeypatch.setattr(repo, "_load_migrations", lambda: (*previous, broken))
    with pytest.raises(MigrationError, match="failed to apply migration 32"):
        repo.initialize(now=NOW)
    with repo._connect() as db:
        assert [
            tuple(r)
            for r in db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
            )
        ] == [tuple(r) for r in schema]
        assert [
            tuple(r)
            for r in db.execute("SELECT * FROM schema_migrations ORDER BY version")
        ] == [tuple(r) for r in history]
        assert db.execute("PRAGMA user_version").fetchone()[0] == 31
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.execute("PRAGMA legacy_alter_table").fetchone()[0] == 0
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    monkeypatch.setattr(repo, "_load_migrations", lambda: migrations)
    assert repo.initialize(now=NOW).version == 32
