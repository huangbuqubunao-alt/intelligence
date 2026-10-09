"""Large-media backup gates fail safely before allocating or changing live data."""

import stat
import struct
import zipfile
from datetime import UTC, datetime

import pytest

from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
from youtube_intel.local_content import LocalContentProvider
from youtube_intel.state import SQLiteStateRepository


@pytest.fixture
def service(tmp_path):
    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    repo.initialize(now=datetime(2026, 10, 9, tzinfo=UTC))
    imported = LocalContentProvider(repo, tmp_path / "data").import_bytes("notes.md", b"Existing isolated source Evidence.\n")
    return BackupRestoreService(database=tmp_path / "state.sqlite", data_root=tmp_path / "data"), repo, imported


def low_disk(*_):
    raise BackupRestoreError("Insufficient available disk space for Backup or Restore.")


def test_backup_disk_rejection_preserves_content_and_cleans_attempt(service, monkeypatch):
    backup, repo, imported = service
    monkeypatch.setattr(backup, "_require_disk_space", low_disk)
    with pytest.raises(BackupRestoreError, match="Insufficient available disk"):
        backup.create_backup()
    assert list(backup.backup_root.iterdir()) == []
    assert repo.get_video(imported.content_id)
    assert repo.resolve_verified_evidence_text(repo.list_evidence_for_presentation(imported.content_id)[0])


@pytest.mark.parametrize("failure", ["disk", "cancel"])
def test_restore_validation_failure_cleans_stage_preserves_existing_evidence(service, monkeypatch, failure):
    backup, repo, imported = service
    created = backup.create_backup()
    path, _ = backup.backup_download(created.backup_id)
    if failure == "disk":
        monkeypatch.setattr(backup, "_require_disk_space", low_disk)
    with path.open("rb") as source, pytest.raises(BackupRestoreError, match="disk|cancelled"):
        backup.stage_restore_stream(source, path.stat().st_size, cancelled=lambda: failure == "cancel")
    assert list(backup.staging_root.iterdir()) == []
    assert not backup.restore_pending
    assert repo.get_video(imported.content_id)
    assert repo.resolve_verified_evidence_text(repo.list_evidence_for_presentation(imported.content_id)[0])


def test_oversized_central_directory_rejected_before_zip_metadata_allocation(service, tmp_path):
    backup, repo, imported = service
    size = 17 * 1024 * 1024
    path = tmp_path / "hostile.zip"
    with path.open("wb") as output:
        output.seek(size)
        output.write(struct.pack("<4s4H2IH", b"PK\x05\x06", 0, 0, 10_000, 10_000, size, 0, 0))
    with path.open("rb") as source, pytest.raises(BackupRestoreError, match="ZIP metadata exceeds"):
        backup.stage_restore_stream(source, path.stat().st_size)
    assert list(backup.staging_root.iterdir()) == []
    assert repo.get_video(imported.content_id)


def test_oversized_manifest_is_rejected_before_reading_into_memory(service, tmp_path):
    backup, _, _ = service
    path = tmp_path / "hostile-manifest.zip"
    with zipfile.ZipFile(path, "w") as archive:
        manifest = zipfile.ZipInfo("manifest.json")
        manifest.external_attr = (stat.S_IFREG | 0o600) << 16
        with archive.open(manifest, "w", force_zip64=True) as output:
            for _ in range(17):
                output.write(b" " * (1024 * 1024))
        database = zipfile.ZipInfo("database/state.sqlite")
        database.external_attr = (stat.S_IFREG | 0o600) << 16
        archive.writestr(database, b"not reached")
    with path.open("rb") as source, pytest.raises(BackupRestoreError, match="manifest exceeds"):
        backup.stage_restore_stream(source, path.stat().st_size)
    assert list(backup.staging_root.iterdir()) == []
