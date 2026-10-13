"""Neutral archives settle only proven failed repair children, never Evidence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.state import SQLiteStateRepository

support = _load_module("test_runtime_composition")


def _repaired_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Real installed adapter identity with a bounded local transport fixture.
    monkeypatch.setattr(support._NativeCaptionRepairAdapter, "provider_name", "yt-dlp")
    monkeypatch.setattr(
        support._NativeCaptionRepairAdapter, "provider_version", "2026.7.4"
    )
    runtime, adapter, source_id, config, dependencies = (
        support._completed_plain_caption_runtime(tmp_path)
    )
    original = runtime.repository._inject_failure

    def fail(point: str) -> None:
        if point == "caption_repair.after_authority":
            raise RuntimeError("controlled completion transaction failure")

    monkeypatch.setattr(runtime.repository, "_inject_failure", fail)
    runtime.application.handle(
        "POST",
        f"/api/v1/sources/{source_id}/check",
        b'{"command_id":"archive-failed-child"}',
    )
    runtime.worker.run_once()
    with runtime.repository._connect() as connection:
        old = dict(
            connection.execute(
                "SELECT * FROM provider_calls WHERE status='FAILED_RETRYABLE'"
            ).fetchone()
        )
    assert (
        old["last_error_message"]
        == "subtitle files were saved but stage persistence failed"
    )
    monkeypatch.setattr(runtime.repository, "_inject_failure", original)
    runtime.application.handle(
        "POST",
        f"/api/v1/sources/{source_id}/check",
        b'{"command_id":"archive-successor-child"}',
    )
    runtime.worker.run_once()
    assert (
        runtime.repository.get_verified_timed_transcript(video_id=support.VIDEO_ID)
        is not None
    )
    return runtime, adapter, old, config, dependencies


def _files(root: Path):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }


def _tables(repository):
    with repository._connect() as connection:
        return {
            row[0]: sorted(
                (
                    tuple(r)
                    for r in connection.execute('SELECT * FROM "' + row[0] + '"')
                ),
                key=repr,
            )
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


def test_retained_failed_repair_is_atomic_durable_idempotent_and_full_restore(
    tmp_path, monkeypatch
):
    runtime, adapter, old, _, _ = _repaired_failure(tmp_path, monkeypatch)
    repo, backup = runtime.repository, runtime.backup_restore
    before_files, before_tables, reads = (
        _files(backup.data_root),
        _tables(repo),
        adapter.read_calls,
    )
    assert not backup.readiness()["ready"]
    retired = repo.archive_failed_caption_repairs(
        backup_restore=backup, now=datetime.now(UTC) + timedelta(seconds=1)
    )
    assert retired == (old["request_hash"],)
    assert backup.readiness()["ready"]
    with repo._connect() as connection:
        terminal = dict(
            connection.execute(
                "SELECT * FROM provider_calls WHERE request_hash=?",
                (old["request_hash"],),
            ).fetchone()
        )
        archives = connection.execute(
            "SELECT * FROM retained_subtitle_derivations"
        ).fetchall()
        assert len(archives) == 1 and len(archives[0]) == 23
        assert (
            archives[0]["derived_sha256"]
            == hashlib.sha256(before_files[archives[0]["relative_path"]]).hexdigest()
        )
        assert (
            connection.execute(
                "SELECT 1 FROM artifacts WHERE relative_path=?",
                (archives[0]["relative_path"],),
            ).fetchone()
            is None
        )
        for sql in (
            "UPDATE retained_subtitle_derivations SET reason=reason",
            "DELETE FROM retained_subtitle_derivations",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(sql)
    assert {
        k: v
        for k, v in terminal.items()
        if k not in {"status", "finished_at", "updated_at"}
    } == {
        k: v for k, v in old.items() if k not in {"status", "finished_at", "updated_at"}
    }
    assert terminal["status"] == "FAILED_FINAL"
    after_tables = _tables(repo)
    assert {
        k: v
        for k, v in before_tables.items()
        if k not in {"provider_calls", "retained_subtitle_derivations"}
    } == {
        k: v
        for k, v in after_tables.items()
        if k not in {"provider_calls", "retained_subtitle_derivations"}
    }
    assert _files(backup.data_root) == before_files and adapter.read_calls == reads
    assert (
        repo.archive_failed_caption_repairs(
            backup_restore=backup, now=datetime.now(UTC) + timedelta(seconds=2)
        )
        == ()
    )
    restored = SQLiteStateRepository(backup.database)
    restored.bind_source_storage(backup.data_root)
    assert (
        restored.archive_failed_caption_repairs(
            backup_restore=backup, now=datetime.now(UTC) + timedelta(seconds=3)
        )
        == ()
    )
    result = backup.create_backup()
    archive, _ = backup.backup_download(result.backup_id)
    preview = backup.stage_restore(archive.read_bytes())
    with zipfile.ZipFile(archive) as package:
        manifest = json.loads(package.read("manifest.json"))
    assert manifest["counts"]["retained_derivations"] == 1
    assert (
        preview.preview["data_artifact_count"] == manifest["counts"]["data_artifacts"]
    )
    assert all(
        set(row)
        == {
            "relative_path",
            "sha256",
            "size_bytes",
            "artifacts",
            "retained_subtitle_derivations",
        }
        for row in manifest["data_files"]
    )
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert (
        _tables(restored) == after_tables and _files(backup.data_root) == before_files
    )
    assert adapter.read_calls == reads


def _settle(runtime):
    return runtime.repository.archive_failed_caption_repairs(
        backup_restore=runtime.backup_restore,
        now=datetime.now(UTC) + timedelta(seconds=1),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider", "other-provider"),
        ("model", "cloud-model"),
        ("operation", "cloud.execute"),
        ("prompt_version", "subtitle-selection-v1"),
        ("schema_version", "subtitle-format-v1"),
        ("last_error_code", "RATE_LIMITED"),
        ("last_error_message", "a different persistence error"),
        ("reservation_owner", "unknown-owner"),
        ("lease_until", "2020-01-01T00:00:00Z"),
        ("input_tokens", 0),
        ("output_tokens", 1),
        ("cost_microusd", 0),
        ("attempt_count", 0),
        ("attempt_count", 1.5),
        ("started_at", "2026-10-13T00:00:00"),
        ("updated_at", "2099-01-01T00:00:00Z"),
        ("available_at", "2000-01-01T00:00:00Z"),
    ],
)
def test_unknown_execution_policy_usage_time_or_count_keeps_batch_unchanged(
    tmp_path, monkeypatch, field, value
):
    runtime, adapter, old, _, _ = _repaired_failure(tmp_path, monkeypatch)
    with runtime.repository._connect() as connection:
        if field in {"reservation_owner", "lease_until"}:
            lease = value if field == "lease_until" else "2099-01-01T00:00:00Z"
            connection.execute(
                "UPDATE provider_calls SET status='PENDING',reservation_owner='unknown-owner',lease_until=? WHERE request_hash=?",
                (lease, old["request_hash"]),
            )
        else:
            connection.execute(
                f"UPDATE provider_calls SET {field}=? WHERE request_hash=?",
                (value, old["request_hash"]),
            )
    before, files, reads = (
        _tables(runtime.repository),
        _files(runtime.backup_restore.data_root),
        adapter.read_calls,
    )
    assert _settle(runtime) == ()
    assert (
        _tables(runtime.repository) == before
        and _files(runtime.backup_restore.data_root) == files
    )
    assert (
        adapter.read_calls == reads and not runtime.backup_restore.readiness()["ready"]
    )


@pytest.mark.parametrize(
    "fault",
    [
        "raw-bytes",
        "derived-bytes",
        "extra-file",
        "missing-derived",
        "summary-pointer",
        "summary-bytes",
        "dispatch",
        "mixed-batch",
        "other-active-job",
        "response",
        "attempt-open",
        "attempt-ambiguous",
    ],
)
def test_changed_source_or_successor_or_unindexed_files_or_other_work_fail_closed(
    tmp_path, monkeypatch, fault
):
    from youtube_intel.domain import ProcessingStage
    from youtube_intel.state import JobType, ProviderCallRequest

    runtime, adapter, old, _, _ = _repaired_failure(tmp_path, monkeypatch)
    repo, root = runtime.repository, runtime.backup_restore.data_root
    with repo._connect() as connection:
        indexed = {
            r[0]
            for r in connection.execute(
                "SELECT relative_path FROM artifacts WHERE storage_root='DATA'"
            )
        }
        orphan = next(path for path in _files(root) if path not in indexed)
        if fault == "raw-bytes":
            row = connection.execute(
                "SELECT relative_path FROM artifacts WHERE job_id LIKE 'caption-repair-%' AND relative_path LIKE '%.vtt' ORDER BY created_at LIMIT 1"
            ).fetchone()
            (root / row[0]).write_bytes(
                (root / row[0]).read_bytes().replace(b"00:00:00", b"00:00:01")
            )
        elif fault == "derived-bytes":
            (root / orphan).write_bytes(
                b"Valid ordinary text, but not the captured derivation.\n"
            )
        elif fault == "missing-derived":
            (root / orphan).unlink()  # isolated fault fixture; never product deletion
        elif fault == "extra-file":
            (root / "unknown.txt").write_text(
                "Unowned bytes must never enter a backup silently."
            )
        elif fault == "summary-pointer":
            connection.execute("DELETE FROM current_content_summaries")
        elif fault == "summary-bytes":
            summary = connection.execute(
                "SELECT relative_path FROM artifacts WHERE provider='extractive-source'"
            ).fetchone()
            (root / summary[0]).write_text("{}")
        elif fault == "response":
            artifact = connection.execute(
                "SELECT artifact_id FROM artifacts LIMIT 1"
            ).fetchone()[0]
            connection.execute(
                "UPDATE provider_calls SET response_artifact_id=? WHERE request_hash=?",
                (artifact, old["request_hash"]),
            )
        elif fault == "attempt-open":
            connection.execute(
                "UPDATE job_attempts SET finished_at=NULL,outcome=NULL WHERE job_id=(SELECT job_id FROM artifacts WHERE artifact_key LIKE 'subtitle-source-capture:%' AND job_id LIKE 'caption-repair-%' ORDER BY created_at LIMIT 1)"
            )
        elif fault == "attempt-ambiguous":
            connection.execute(
                "UPDATE job_attempts SET outcome='LEASE_EXPIRED' WHERE job_id=(SELECT job_id FROM artifacts WHERE artifact_key LIKE 'subtitle-source-capture:%' AND job_id LIKE 'caption-repair-%' ORDER BY created_at LIMIT 1)"
            )
        elif fault == "dispatch":
            connection.execute(
                "INSERT INTO provider_dispatch_states(request_hash,status,updated_at) VALUES (?,'FAILED_KNOWN',?)",
                (old["request_hash"], old["updated_at"]),
            )
    if fault == "mixed-batch":
        request = ProviderCallRequest(
            operation="subtitle.fetch",
            normalized_input_hash="b" * 64,
            provider="yt-dlp",
            model=None,
            prompt_version="subtitle-selection-v2-original-tracks",
            schema_version="subtitle-format-v2-native-timing",
            deterministic_artifact_key="unused",
        )
        repo.reserve_provider_call(
            request,
            owner="unknown",
            lease_until=datetime.now(UTC) + timedelta(hours=1),
            available_at=datetime.now(UTC),
            now=datetime.now(UTC),
        )
    elif fault == "other-active-job":
        repo.create_job(
            job_id="other-live-work",
            scope_key="channel:UC_ARCHIVE_NEGATIVE:discovery",
            video_id=None,
            job_type=JobType.CHANNEL_DISCOVERY,
            target_stage=ProcessingStage.DISCOVERY,
            pipeline_version="test",
            max_attempts=1,
            available_at=datetime.now(UTC),
            now=datetime.now(UTC),
        )
    before, files, reads = _tables(repo), _files(root), adapter.read_calls
    assert _settle(runtime) == ()
    assert (
        _tables(repo) == before
        and _files(root) == files
        and adapter.read_calls == reads
    )
    assert not runtime.backup_restore.readiness()["ready"]


def test_archive_transaction_fault_rolls_back_every_mutation_and_restart_can_retry(
    tmp_path, monkeypatch
):
    runtime, _, _, _, _ = _repaired_failure(tmp_path, monkeypatch)
    before, files = (
        _tables(runtime.repository),
        _files(runtime.backup_restore.data_root),
    )
    original = runtime.repository._inject_failure

    def fail(point):
        if point == "subtitle_archive.before_commit":
            raise RuntimeError("controlled archive transaction fault")

    monkeypatch.setattr(runtime.repository, "_inject_failure", fail)
    with pytest.raises(RuntimeError, match="controlled archive transaction fault"):
        _settle(runtime)
    assert (
        _tables(runtime.repository) == before
        and _files(runtime.backup_restore.data_root) == files
    )
    monkeypatch.setattr(runtime.repository, "_inject_failure", original)
    restarted = SQLiteStateRepository(runtime.backup_restore.database)
    assert restarted.archive_failed_caption_repairs(
        backup_restore=runtime.backup_restore,
        now=datetime.now(UTC) + timedelta(seconds=1),
    )
    assert runtime.backup_restore.readiness()["ready"]


def test_idle_maintenance_closes_known_failure_without_fetch_or_repeat(
    tmp_path, monkeypatch
):
    runtime, adapter, old, _, _ = _repaired_failure(tmp_path, monkeypatch)
    reads = adapter.read_calls
    assert runtime.worker.run_once() is None
    assert (
        runtime.repository.get_provider_call(old["request_hash"]).status.value
        == "FAILED_FINAL"
    )
    assert runtime.backup_restore.readiness()["ready"]
    assert runtime.worker.run_once() is None and adapter.read_calls == reads


def test_unknown_physical_data_blocks_readiness_and_create_without_retirement(tmp_path):
    from youtube_intel.backup_restore import BackupRestoreError

    backup_support = _load_module("test_backup_restore")
    backup_support._workspace(tmp_path)
    backup = backup_support._service(tmp_path)
    (backup.data_root / "unknown.txt").write_text("Unindexed content")
    assert not backup.readiness()["ready"]
    with pytest.raises(BackupRestoreError, match="unindexed"):
        backup.create_backup()


@pytest.mark.parametrize("version", [34, 35, 36, 37])
def test_old_manifest_contract_restores_then_adds_empty_archive_table(
    tmp_path, monkeypatch, version
):
    backup_support = _load_module("test_backup_restore")
    migrations = SQLiteStateRepository(
        tmp_path / "not-opened.sqlite3"
    )._load_migrations()
    with monkeypatch.context() as scoped:
        scoped.setattr(
            SQLiteStateRepository,
            "_load_migrations",
            lambda self: tuple(m for m in migrations if m.version <= version),
        )
        _, root, _, repo, _ = backup_support._workspace(tmp_path)
    backup = backup_support._service(tmp_path)
    files, tables = _files(root), _tables(repo)
    result = backup.create_backup()
    path, _ = backup.backup_download(result.backup_id)
    with zipfile.ZipFile(path) as package:
        manifest = json.loads(package.read("manifest.json"))
    assert manifest["schema_version"] == version
    assert "retained_derivations" not in manifest["counts"]
    assert all(
        set(row) == {"relative_path", "sha256", "size_bytes", "artifacts"}
        for row in manifest["data_files"]
    )
    staged = backup.stage_restore(path.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert _tables(repo) == tables and _files(root) == files
    assert repo.initialize(now=backup_support.NOW).version == 38
    with repo._connect() as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM retained_subtitle_derivations"
            ).fetchone()[0]
            == 0
        )
    assert {
        k: v
        for k, v in _tables(repo).items()
        if k in tables and k != "schema_migrations"
    } == {k: v for k, v in tables.items() if k != "schema_migrations"}
    assert _files(root) == files


def test_migration38_ddl_fault_rolls_back_and_preserves37_exactly(
    tmp_path, monkeypatch
):
    from dataclasses import replace

    from youtube_intel.state import MigrationError

    migrations = SQLiteStateRepository(
        tmp_path / "not-opened.sqlite3"
    )._load_migrations()
    repo = SQLiteStateRepository(tmp_path / "migration.sqlite3")
    monkeypatch.setattr(
        repo,
        "_load_migrations",
        lambda: tuple(m for m in migrations if m.version <= 37),
    )
    assert repo.initialize(now=datetime.now(UTC)).version == 37
    before = _tables(repo)
    broken = replace(
        migrations[-1],
        sql=migrations[-1].sql + "\nSELECT unknown_migration_function();",
    )
    monkeypatch.setattr(
        repo,
        "_load_migrations",
        lambda: (*tuple(m for m in migrations if m.version <= 37), broken),
    )
    with pytest.raises(MigrationError):
        repo.initialize(now=datetime.now(UTC))
    assert _tables(repo) == before
    with repo._connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 37
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='retained_subtitle_derivations'"
            ).fetchone()
            is None
        )
    monkeypatch.setattr(repo, "_load_migrations", lambda: migrations)
    assert repo.initialize(now=datetime.now(UTC)).version == 38
    assert {
        k: v
        for k, v in _tables(repo).items()
        if k in before and k != "schema_migrations"
    } == {k: v for k, v in before.items() if k != "schema_migrations"}


@pytest.mark.parametrize(
    "fault",
    [
        "missing-ref",
        "duplicate-ref",
        "extra-ref",
        "wrong-proof-hash",
        "wrong-count",
        "old-shape",
        "wrong-file-hash",
    ],
)
def test_schema38_manifest_neutral_refs_are_strict_and_never_authority(
    tmp_path, monkeypatch, fault
):
    import io

    from youtube_intel.backup_restore import BackupRestoreError

    runtime, _, _, _, _ = _repaired_failure(tmp_path, monkeypatch)
    assert _settle(runtime)
    backup = runtime.backup_restore
    result = backup.create_backup()
    path, _ = backup.backup_download(result.backup_id)
    with zipfile.ZipFile(path) as source:
        manifest = json.loads(source.read("manifest.json"))
        record = next(
            r for r in manifest["data_files"] if r["retained_subtitle_derivations"]
        )
        refs = record["retained_subtitle_derivations"]
        if fault == "missing-ref":
            refs.clear()
        elif fault == "duplicate-ref":
            refs.append(dict(refs[0]))
        elif fault == "extra-ref":
            refs.append({**refs[0], "archive_id": "f" * 64})
        elif fault == "wrong-proof-hash":
            refs[0]["proof_sha256"] = "0" * 64
        elif fault == "wrong-count":
            manifest["counts"]["retained_derivations"] += 1
        elif fault == "old-shape":
            record.pop("retained_subtitle_derivations")
        elif fault == "wrong-file-hash":
            record["sha256"] = "f" * 64
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for name in source.namelist():
                target.writestr(
                    name,
                    json.dumps(manifest).encode()
                    if name == "manifest.json"
                    else source.read(name),
                )
    before, files = _tables(runtime.repository), _files(backup.data_root)
    with pytest.raises(BackupRestoreError):
        backup.stage_restore(output.getvalue())
    assert _tables(runtime.repository) == before and _files(backup.data_root) == files


def test_archive_gate_respects_background_and_staged_restore_lock(
    tmp_path, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    runtime, _, _, _, _ = _repaired_failure(tmp_path, monkeypatch)
    backup = runtime.backup_restore
    before = _tables(runtime.repository)
    with backup.background_work() as allowed:
        assert allowed and _settle(runtime) == ()
    with backup._protect_background():
        assert _settle(runtime) == ()
    assert _tables(runtime.repository) == before
    started = Event()

    def maintenance():
        started.set()
        return _settle(runtime)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with backup._staged_lock:
            future = pool.submit(maintenance)
            assert started.wait(2)
            assert not future.done()
            assert _tables(runtime.repository) == before
        assert future.result(timeout=10)
    assert backup.readiness()["ready"]


def test_reservation_race_has_one_winner_and_never_restarts_a_retired_call(
    tmp_path, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from youtube_intel.state import ProviderCallRequest

    runtime, _, old, _, _ = _repaired_failure(tmp_path, monkeypatch)
    repo = runtime.repository
    with repo._connect() as connection:
        captures = connection.execute(
            "SELECT artifact_key FROM artifacts WHERE job_id LIKE 'caption-repair-%'"
        ).fetchall()
    requests = [
        ProviderCallRequest(
            operation="subtitle.fetch",
            normalized_input_hash=r[0].split(":")[1],
            provider="yt-dlp",
            model=None,
            prompt_version="subtitle-selection-v2-original-tracks",
            schema_version="subtitle-format-v2-native-timing",
            deterministic_artifact_key="subtitle-source:" + r[0].split(":")[1],
        )
        for r in captures
        if r[0].startswith("subtitle-source-capture:")
    ]
    request = next(r for r in requests if r.request_hash == old["request_hash"])
    barrier = Barrier(2)
    now = datetime.now(UTC) + timedelta(seconds=1)

    def archive():
        barrier.wait()
        return repo.archive_failed_caption_repairs(
            backup_restore=runtime.backup_restore, now=now
        )

    def reserve():
        barrier.wait()
        return repo.reserve_provider_call(
            request,
            owner="concurrent-start",
            lease_until=now + timedelta(minutes=1),
            available_at=now,
            now=now,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1, f2 = pool.submit(archive), pool.submit(reserve)
        retired, reservation = f1.result(timeout=15), f2.result(timeout=15)
    assert bool(retired) != reservation.acquired
    if retired:
        assert reservation.record.status.value == "FAILED_FINAL"
        assert runtime.backup_restore.readiness()["ready"]
    else:
        with repo._connect() as connection:
            assert (
                connection.execute(
                    "SELECT count(*) FROM retained_subtitle_derivations"
                ).fetchone()[0]
                == 0
            )
        assert not runtime.backup_restore.readiness()["ready"]


def test_frozen_chinese_english_input_is_proven_without_using_mutable_current_settings(
    tmp_path, monkeypatch
):
    original_project = support._project

    def frozen_project(path):
        project = original_project(path)
        settings = project / "config/settings.yaml"
        settings.write_text(
            settings.read_text().replace(
                "transcript_languages: [en]", "transcript_languages: [zh, en]"
            )
        )
        return project

    monkeypatch.setattr(support, "_project", frozen_project)
    runtime, _, _, _, _ = _repaired_failure(tmp_path, monkeypatch)
    assert _settle(runtime)
    with runtime.repository._connect() as connection:
        proof = json.loads(
            connection.execute(
                "SELECT proof_json FROM retained_subtitle_derivations"
            ).fetchone()[0]
        )
        assert proof["input"]["language_preferences"] == ["zh", "en"]
    assert runtime.backup_restore.readiness()["ready"]


def test_immutable_archive_does_not_require_current_summary_pointer_forever(
    tmp_path, monkeypatch
):
    runtime, _, _, _, _ = _repaired_failure(tmp_path, monkeypatch)
    assert _settle(runtime)
    # A later ordinary Summary refresh may move/remove only the current pointer;
    # retained historical artifacts/Evidence/provider graph stay verifiable.
    with runtime.repository._connect() as connection:
        connection.execute("DELETE FROM current_content_summaries")
    assert runtime.backup_restore.readiness()["ready"]
    backup = runtime.backup_restore.create_backup()
    archive, _ = runtime.backup_restore.backup_download(backup.backup_id)
    assert (
        runtime.backup_restore.stage_restore(archive.read_bytes()).preview[
            "summary_count"
        ]
        == 0
    )


def test_neutral_and_ordinary_references_share_bytes_once_without_evidence_promotion(
    tmp_path, monkeypatch
):
    from youtube_intel.state import (
        ArtifactKind,
        ArtifactWrite,
        RetentionClass,
        StorageRoot,
    )

    runtime, _, _, _, _ = _repaired_failure(tmp_path, monkeypatch)
    assert _settle(runtime)
    repo, backup = runtime.repository, runtime.backup_restore
    evidence = repo.list_evidence_for_presentation(support.VIDEO_ID)
    timed = repo.get_verified_timed_transcript(video_id=support.VIDEO_ID)
    with repo._connect() as connection:
        row = dict(
            connection.execute("SELECT * FROM retained_subtitle_derivations").fetchone()
        )
    repo.upsert_artifact(
        ArtifactWrite(
            artifact_id="neutral-byte-copy",
            artifact_key="neutral-byte-copy",
            video_id=support.VIDEO_ID,
            job_id=None,
            kind=ArtifactKind.SCORING_RAW,
            storage_root=StorageRoot.DATA,
            relative_path=row["relative_path"],
            content_hash=row["derived_sha256"],
            provider=None,
            model=None,
            producer_version="test-only-byte-retention",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=datetime.now(UTC),
    )
    assert repo.list_evidence_for_presentation(support.VIDEO_ID) == evidence
    assert repo.get_verified_timed_transcript(video_id=support.VIDEO_ID) == timed
    result = backup.create_backup()
    path, _ = backup.backup_download(result.backup_id)
    with zipfile.ZipFile(path) as package:
        manifest = json.loads(package.read("manifest.json"))
    record = next(
        r for r in manifest["data_files"] if r["relative_path"] == row["relative_path"]
    )
    assert record["artifacts"] and record["retained_subtitle_derivations"]
    assert manifest["counts"]["data_bytes"] == sum(
        len(v) for v in _files(backup.data_root).values()
    )
    assert (
        backup.stage_restore(path.read_bytes()).preview["data_size_bytes"]
        == manifest["counts"]["data_bytes"]
    )


@pytest.mark.parametrize("status", ["WAITING_BUDGET", "PENDING"])
def test_other_checkpoint_states_keep_archive_and_backup_closed(
    tmp_path, monkeypatch, status
):
    from youtube_intel.state import DistillationExecutionWrite

    runtime, _, _, _, _ = _repaired_failure(tmp_path, monkeypatch)
    repo = runtime.repository
    source = repo.list_source_subscriptions()[0]
    now = datetime.now(UTC)
    repo.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id="archive-other-checkpoint",
            source_id=source.source_id,
            video_id=support.VIDEO_ID,
            reason="MANUAL_CONTENT:archive-negative",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="ollama",
            selected_model="qwen3:8b",
            output_language="en",
        ),
        now=now,
    )
    if status == "WAITING_BUDGET":
        repo.finish_distillation_without_admission(
            execution_id="archive-other-checkpoint",
            status="WAITING_BUDGET",
            budget_state="WAITING_BUDGET",
            outcome="BUDGET_UNAVAILABLE_BEFORE_TRANSPORT",
            invocation_count=0,
            actual_provider=None,
            actual_model=None,
            input_tokens=None,
            output_tokens=None,
            cost_microunits=None,
            duration_ms=None,
            now=now,
        )
    before = _tables(repo)
    assert _settle(runtime) == () and _tables(repo) == before
    assert not runtime.backup_restore.readiness()["ready"]
