"""Schema 35 changes only a trigger and preserves unresolved Day 1 authority."""
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import MigrationError, SQLiteStateRepository

NOW = datetime(2026, 10, 8, tzinfo=UTC)


def database34(tmp_path: Path):
    repo = SQLiteStateRepository(tmp_path / 'state.sqlite3')
    migrations = tuple(m for m in repo._load_migrations() if m.version <= 35)
    repo._load_migrations = lambda: migrations[:-1]
    assert repo.initialize(now=NOW).version == 34
    source = ProductOrchestrationService(repo, now=lambda: NOW).add_source(url='https://www.youtube.com/@lingdujieshuo', processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE)
    repo._load_migrations = lambda: migrations
    return repo, source


def test_34_to_35_preserves_unresolved_source_and_is_restart_idempotent(tmp_path):
    repo, source = database34(tmp_path)
    assert repo.initialize(now=NOW).version == 35
    assert repo.get_source_subscription(source.source_id) == source
    assert repo.list_videos() == ()
    with repo._connect() as connection:
        assert connection.execute('pragma integrity_check').fetchone()[0] == 'ok'
        assert connection.execute('pragma foreign_key_check').fetchall() == []
        assert connection.execute('select count(*) from source_tracking_state').fetchone()[0] == 0
        sql = connection.execute("select sql from sqlite_master where name='distillation_no_new_result_requires_claimed_checkpoint'").fetchone()[0]
        assert "lineage_kind = 'ORIGINAL_TRANSCRIPT'" in sql
        count = connection.execute('select count(*) from schema_migrations').fetchone()[0]
    assert repo.initialize(now=NOW).version == 35
    with repo._connect() as connection:
        assert connection.execute('select count(*) from schema_migrations').fetchone()[0] == count


def test_schema35_failure_rolls_back_trigger_and_history_atomically(tmp_path):
    repo, source = database34(tmp_path)
    migrations = tuple(m for m in repo._load_migrations() if m.version <= 35)
    repo._load_migrations = lambda: (*migrations[:-1], replace(migrations[-1], sql=migrations[-1].sql + '\nINVALID MIGRATION;'))
    with pytest.raises(MigrationError, match='migration 35'):
        repo.initialize(now=NOW)
    with repo._connect() as connection:
        assert connection.execute('pragma user_version').fetchone()[0] == 34
        sql = connection.execute("select sql from sqlite_master where name='distillation_no_new_result_requires_claimed_checkpoint'").fetchone()[0]
        assert 'lineage_kind' not in sql
        assert connection.execute('select max(version) from schema_migrations').fetchone()[0] == 34
    assert repo.get_source_subscription(source.source_id) == source
    repo._load_migrations = lambda: migrations
    assert repo.initialize(now=NOW).version == 35


def test_schema34_backup_restores_then_supported_startup_migrates(tmp_path):
    from youtube_intel.backup_restore import BackupRestoreService
    repo, source = database34(tmp_path)
    data = tmp_path / 'data'
    data.mkdir()
    backup = BackupRestoreService(database=tmp_path / 'state.sqlite3', data_root=data)
    archive = backup.create_backup()
    staged = backup.stage_restore((backup.backup_root / f'{archive.backup_id}.zip').read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert repo.initialize(now=NOW).version == 35
    assert repo.get_source_subscription(source.source_id) == source
