"""Integration tests for V1 core backup archive creation and restore staging."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.core_backup import CoreBackupError, CoreBackupService
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    format_utc_datetime,
)

NOW = datetime(2026, 9, 18, 14, tzinfo=UTC)


def _workspace(tmp_path: Path) -> tuple[Path, SQLiteStateRepository]:
    data_root = tmp_path / "workspace" / "data"
    data_root.mkdir(parents=True)
    repository = SQLiteStateRepository(data_root / "state.sqlite")
    repository.initialize(now=NOW)

    body = b"canonical transcript body"
    relative = "transcripts/example.txt"
    path = data_root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(body)
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="artifact-data-1",
            artifact_key="backup/data/1",
            video_id=None,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=relative,
            content_hash=hashlib.sha256(body).hexdigest(),
            provider=None,
            model=None,
            producer_version="backup-fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )

    external = b"user-owned vault content"
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="artifact-vault-1",
            artifact_key="backup/vault/1",
            video_id=None,
            job_id=None,
            kind=ArtifactKind.VIDEO_NOTE,
            storage_root=StorageRoot.VAULT,
            relative_path="Videos/external.md",
            content_hash=hashlib.sha256(external).hexdigest(),
            provider=None,
            model=None,
            producer_version="backup-fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    return data_root, repository


def _service(data_root: Path) -> CoreBackupService:
    return CoreBackupService(
        data_root=data_root,
        app_version="0.1.0-test",
        now=lambda: NOW,
    )


def test_core_backup_round_trip_inspection_and_staging_excludes_vault(
    tmp_path: Path,
) -> None:
    data_root, _repository = _workspace(tmp_path)
    output = tmp_path / "exports"
    output.mkdir()
    destination = output / "intelligence-2026-09-18.intelligence-backup"

    result = _service(data_root).create_backup(destination)

    assert result.archive_path == destination
    assert destination.is_file()
    assert result.inspection.schema_version == 16
    assert result.inspection.artifact_count == 1
    assert result.inspection.excluded_vault_artifact_count == 1
    assert "Summary / Video Notes" in result.inspection.core_scope

    staging_parent = tmp_path / "restore-staging"
    staging_parent.mkdir()
    staged = _service(data_root).stage_restore(
        destination, staging_parent=staging_parent
    )
    try:
        assert staged.inspection == result.inspection
        assert (staged.data_root / "state.sqlite").is_file()
        assert (
            staged.data_root / "transcripts" / "example.txt"
        ).read_bytes() == b"canonical transcript body"
        assert not (staged.data_root / "Videos" / "external.md").exists()

        connection = sqlite3.connect(staged.data_root / "state.sqlite")
        try:
            assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 16
        finally:
            connection.close()
    finally:
        shutil.rmtree(staged.staging_root)


def test_corrupt_backup_is_rejected_before_restore_staging(
    tmp_path: Path,
) -> None:
    data_root, _repository = _workspace(tmp_path)
    output = tmp_path / "exports"
    output.mkdir()
    good = output / "good.intelligence-backup"
    _service(data_root).create_backup(good)

    bad = output / "bad.intelligence-backup"
    with zipfile.ZipFile(good, "r") as source, zipfile.ZipFile(
        bad, "w", compression=zipfile.ZIP_DEFLATED
    ) as target:
        for info in source.infolist():
            body = source.read(info)
            if info.filename == "data/transcripts/example.txt":
                body = b"tampered"
            target.writestr(info.filename, body)

    with pytest.raises(CoreBackupError, match="checksum"):
        _service(data_root).inspect_backup(bad)

    staging_parent = tmp_path / "restore-staging"
    staging_parent.mkdir()
    with pytest.raises(CoreBackupError):
        _service(data_root).stage_restore(bad, staging_parent=staging_parent)
    assert list(staging_parent.iterdir()) == []


def test_missing_live_data_artifact_aborts_without_publishing_backup(
    tmp_path: Path,
) -> None:
    data_root, _repository = _workspace(tmp_path)
    (data_root / "transcripts" / "example.txt").unlink()
    output = tmp_path / "exports"
    output.mkdir()
    destination = output / "should-not-exist.intelligence-backup"

    with pytest.raises(CoreBackupError):
        _service(data_root).create_backup(destination)

    assert not destination.exists()


def test_active_pipeline_job_blocks_backup_snapshot(
    tmp_path: Path,
) -> None:
    data_root, repository = _workspace(tmp_path)
    timestamp = format_utc_datetime(NOW)
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO jobs "
            "(job_id, scope_key, video_id, job_type, target_stage, pipeline_version, "
            "status, max_attempts, available_at, created_at, updated_at) "
            "VALUES (?, ?, NULL, 'CHANNEL_DISCOVERY', 'DISCOVERY', ?, 'PENDING', "
            "3, ?, ?, ?)",
            (
                "backup-active-job",
                "backup-active-scope",
                "runtime-v1",
                timestamp,
                timestamp,
                timestamp,
            ),
        )
    finally:
        connection.close()

    output = tmp_path / "exports"
    output.mkdir()
    destination = output / "blocked.intelligence-backup"
    with pytest.raises(CoreBackupError, match="active pipeline jobs"):
        _service(data_root).create_backup(destination)
    assert not destination.exists()


def test_backup_never_overwrites_an_existing_destination(tmp_path: Path) -> None:
    data_root, _repository = _workspace(tmp_path)
    output = tmp_path / "exports"
    output.mkdir()
    destination = output / "existing.intelligence-backup"
    destination.write_bytes(b"keep me")

    with pytest.raises(CoreBackupError, match="already exists"):
        _service(data_root).create_backup(destination)

    assert destination.read_bytes() == b"keep me"
