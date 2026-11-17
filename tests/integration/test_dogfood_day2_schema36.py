"""Approved Schema 36 changes only Local media capacity, preserving authority."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from youtube_intel.local_content import LocalContentProvider
from youtube_intel.state import MigrationError, SQLiteStateRepository

NOW = datetime(2026, 10, 9, tzinfo=UTC)


def legacy35(tmp_path):
    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    migrations = repo._load_migrations()
    repo._load_migrations = lambda: tuple(m for m in migrations if m.version <= 35)
    assert repo.initialize(now=NOW).version == 35
    provider = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)
    imported = provider.import_bytes("notes.md", b"Exact existing Evidence remains intact.\n")
    repo._load_migrations = lambda: migrations
    return repo, imported


def rows(repo):
    with repo._connect() as db:
        return {table: [tuple(row) for row in db.execute(f"SELECT * FROM {table}")]
                for table in ("videos", "artifacts", "content_source_snapshots", "evidence", "evidence_source_ranges", "source_subscriptions")}


def test_upgrade_preserves_all_rows_evidence_and_immutable_triggers(tmp_path):
    repo, imported = legacy35(tmp_path)
    before = rows(repo)
    evidence = repo.list_evidence_for_presentation(imported.content_id)[0]
    verified = repo.resolve_verified_evidence_text(evidence)
    assert repo.initialize(now=NOW).version == 45
    assert rows(repo) == before
    assert repo.resolve_verified_evidence_text(evidence) == verified
    with repo._connect() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        for sql in ["DELETE FROM content_source_snapshots", "UPDATE content_source_snapshots SET source_hash='f' || substr(source_hash,2)"]:
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(sql)
        table = db.execute("SELECT sql FROM sqlite_master WHERE name='content_source_snapshots'").fetchone()[0]
        assert "2147483648" in table and "2097152" in table and "67108864" in table
    assert repo.initialize(now=NOW).version == 45
    assert rows(repo) == before


def test_failed_migration_rolls_back_schema_rows_and_history(tmp_path):
    repo, _ = legacy35(tmp_path)
    before = rows(repo)
    migrations = repo._load_migrations()
    repo._load_migrations = lambda: tuple(
        replace(m, sql=m.sql + "\nINVALID MIGRATION;") if m.version == 36 else m
        for m in migrations
    )
    with pytest.raises(MigrationError, match="migration 36"):
        repo.initialize(now=NOW)
    assert rows(repo) == before
    with repo._connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 35
        assert db.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 35
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    repo._load_migrations = lambda: migrations
    assert repo.initialize(now=NOW).version == 45


def test_schema35_archive_restores_before_schema36_startup(tmp_path):
    from youtube_intel.backup_restore import BackupRestoreService
    repo, imported = legacy35(tmp_path)
    backup = BackupRestoreService(database=repo._database_path, data_root=tmp_path / "data")
    created = backup.create_backup()
    path, _ = backup.backup_download(created.backup_id)
    with path.open("rb") as archive:
        staged = backup.stage_restore_stream(archive, path.stat().st_size)
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert repo.schema_version().version == 35
    assert repo.initialize(now=NOW).version == 45
    assert repo.get_video(imported.content_id)
    assert repo.resolve_verified_evidence_text(repo.list_evidence_for_presentation(imported.content_id)[0])
