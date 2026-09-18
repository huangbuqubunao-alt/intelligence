"""Integration tests for confirmed, restart-boundary core restore coordination."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.core_backup import CoreBackupService
from youtube_intel.core_restore import (
    CoreRestoreCoordinator,
    CoreRestoreError,
    apply_pending_core_restore,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
)

NOW = datetime(2026, 9, 18, 15, tzinfo=UTC)


def _workspace(
    tmp_path: Path,
) -> tuple[Path, Path, SQLiteStateRepository]:
    project_root = tmp_path / "workspace"
    data_root = project_root / "data"
    data_root.mkdir(parents=True)
    repository = SQLiteStateRepository(data_root / "state.sqlite")
    repository.initialize(now=NOW)

    body = b"restore-boundary transcript"
    relative = "transcripts/restore.txt"
    target = data_root / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(body)
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="restore-artifact-1",
            artifact_key="restore/data/1",
            video_id=None,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=relative,
            content_hash=hashlib.sha256(body).hexdigest(),
            provider=None,
            model=None,
            producer_version="restore-fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    return project_root, data_root, repository


def _archive(tmp_path: Path, data_root: Path) -> Path:
    exports = tmp_path / "exports"
    exports.mkdir(exist_ok=True)
    archive = exports / "restore-test.intelligence-backup"
    CoreBackupService(
        data_root=data_root,
        app_version="0.1.0-test",
        now=lambda: NOW,
    ).create_backup(archive)
    return archive


def _coordinator(project_root: Path, data_root: Path) -> CoreRestoreCoordinator:
    return CoreRestoreCoordinator(
        project_root=project_root,
        data_root=data_root,
        app_version="0.1.0-test",
        now=lambda: NOW,
    )


def test_confirmed_restore_swaps_only_on_restart_and_preserves_previous_data(
    tmp_path: Path,
) -> None:
    project_root, data_root, repository = _workspace(tmp_path)
    archive = _archive(tmp_path, data_root)

    # Change current live state after the backup so a successful restore is visible.
    repository.save_global_output_language_preference(
        output_language="en",
        now=NOW,
    )
    assert repository.get_global_output_language_preference() is not None

    coordinator = _coordinator(project_root, data_root)
    staged = coordinator.stage_backup(archive)
    pending = coordinator.schedule_restore(staged, confirmed=True)

    # Scheduling only records intent. Live data is untouched until startup apply.
    assert pending.staging_root == staged.staging_root
    assert (
        SQLiteStateRepository(data_root / "state.sqlite")
        .get_global_output_language_preference()
        .output_language
        == "en"
    )

    applied = coordinator.apply_pending_on_startup()

    assert applied is not None
    assert applied.restored_data_root == data_root
    assert coordinator.read_pending() is None
    assert (
        SQLiteStateRepository(data_root / "state.sqlite")
        .get_global_output_language_preference()
        is None
    )
    previous_preference = SQLiteStateRepository(
        applied.previous_data_root / "state.sqlite"
    ).get_global_output_language_preference()
    assert previous_preference is not None
    assert previous_preference.output_language == "en"
    assert (
        data_root / "transcripts" / "restore.txt"
    ).read_bytes() == b"restore-boundary transcript"


def test_unconfirmed_restore_cannot_create_pending_intent(tmp_path: Path) -> None:
    project_root, data_root, _repository = _workspace(tmp_path)
    archive = _archive(tmp_path, data_root)
    coordinator = _coordinator(project_root, data_root)
    staged = coordinator.stage_backup(archive)

    with pytest.raises(CoreRestoreError, match="explicit confirmation"):
        coordinator.schedule_restore(staged, confirmed=False)

    assert coordinator.read_pending() is None
    assert data_root.is_dir()


def test_live_change_after_confirmation_blocks_restore_without_touching_data(
    tmp_path: Path,
) -> None:
    project_root, data_root, repository = _workspace(tmp_path)
    archive = _archive(tmp_path, data_root)
    coordinator = _coordinator(project_root, data_root)
    staged = coordinator.stage_backup(archive)
    coordinator.schedule_restore(staged, confirmed=True)

    repository.save_global_output_language_preference(
        output_language="en",
        now=NOW,
    )

    with pytest.raises(CoreRestoreError, match="changed after restore confirmation"):
        coordinator.apply_pending_on_startup()

    live = SQLiteStateRepository(data_root / "state.sqlite")
    preference = live.get_global_output_language_preference()
    assert preference is not None
    assert preference.output_language == "en"
    assert coordinator.read_pending() is not None
    assert staged.staging_root.is_dir()

    assert coordinator.cancel_pending_restore() is True
    assert coordinator.read_pending() is None
    assert not staged.staging_root.exists()


def test_staged_change_after_confirmation_blocks_before_live_swap(
    tmp_path: Path,
) -> None:
    project_root, data_root, _repository = _workspace(tmp_path)
    archive = _archive(tmp_path, data_root)
    coordinator = _coordinator(project_root, data_root)
    staged = coordinator.stage_backup(archive)
    coordinator.schedule_restore(staged, confirmed=True)

    (staged.data_root / "transcripts" / "restore.txt").write_bytes(b"tampered")

    with pytest.raises((CoreRestoreError, ValueError)):
        coordinator.apply_pending_on_startup()

    assert (data_root / "state.sqlite").is_file()
    assert (
        data_root / "transcripts" / "restore.txt"
    ).read_bytes() == b"restore-boundary transcript"
    assert coordinator.read_pending() is not None
    coordinator.cancel_pending_restore()


def test_startup_restore_seam_is_noop_without_pending_marker(tmp_path: Path) -> None:
    project_root, data_root, _repository = _workspace(tmp_path)

    result = apply_pending_core_restore(
        project_root=project_root,
        data_root=data_root,
        app_version="0.1.0-test",
        now=lambda: NOW,
    )

    assert result is None
    assert not (project_root / ".intelligence-restore").exists()
