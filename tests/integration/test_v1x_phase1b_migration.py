"""Phase 1B upgrades the accepted 028 schema without claiming M13's 029."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 2, tzinfo=UTC)


def test_upgrade_028_retry_and_authority_constraints(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    migrations = tuple(m for m in repository._load_migrations() if m.version <= 30)
    assert [m.version for m in migrations] == [*range(1, 29), 30]
    repository._load_migrations = lambda: migrations[:-1]
    assert repository.initialize(now=NOW).version == 28
    repository._load_migrations = lambda: migrations
    assert repository.initialize(now=NOW).version == 30
    assert repository.initialize(now=NOW).version == 30
    with repository._connect() as connection:
        columns = {r[1]: r[5] for r in connection.execute("PRAGMA table_info(deep_analysis_evidence)")}
        assert columns == {"result_identity": 1, "evidence_id": 2, "created_at": 0}
        foreign_keys = {r[2] for r in connection.execute("PRAGMA foreign_key_list(deep_analysis_evidence)")}
        assert foreign_keys == {"evidence", "deep_analysis_persisted_results"}
        indexes = {r[1] for r in connection.execute("PRAGMA index_list(deep_analysis_evidence)")}
        assert "idx_deep_analysis_evidence_evidence_id" in indexes
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO deep_analysis_evidence VALUES (?, ?, ?)", ("a" * 64, "missing", NOW.isoformat()))
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()


def test_failed_030_leaves_028_schema_and_history_unchanged(tmp_path: Path, monkeypatch) -> None:
    from dataclasses import replace

    from youtube_intel.state import MigrationError

    repository = SQLiteStateRepository(tmp_path / "rollback.sqlite3")
    migrations = tuple(m for m in repository._load_migrations() if m.version <= 30)
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations[:-1])
    repository.initialize(now=NOW)
    with repository._connect() as connection:
        before = [tuple(r) for r in connection.execute("SELECT * FROM schema_migrations ORDER BY version")]
    broken = replace(migrations[-1], sql=migrations[-1].sql + "\nCREATE TABLE invalid(;", checksum="f" * 64)
    monkeypatch.setattr(repository, "_load_migrations", lambda: (*migrations[:-1], broken))
    with pytest.raises(MigrationError, match="failed to apply migration 30"):
        repository.initialize(now=NOW)
    with repository._connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 28
        assert [tuple(r) for r in connection.execute("SELECT * FROM schema_migrations ORDER BY version")] == before
        assert not connection.execute("SELECT 1 FROM sqlite_master WHERE name='deep_analysis_evidence'").fetchall()
        assert "persistence_version" not in {r[1] for r in connection.execute("PRAGMA table_info(deep_analysis_persisted_results)")}
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations)
    assert repository.initialize(now=NOW).version == 30


def test_real_phase1a_row_remains_readable_without_backfill_after_upgrade(tmp_path: Path, monkeypatch) -> None:
    from conftest import _load_module

    from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
    from youtube_intel.note_v2 import NoteV2Error, build_note_v2

    activation = _load_module("test_v1x_deep_analysis_activation")
    fixture = SQLiteStateRepository(tmp_path / "fixture.sqlite3")
    fixture.initialize(now=NOW)
    activation._seed_content(fixture, "video-1")
    view = activation._service(fixture).run(content_id="video-1")
    with fixture._connect() as connection:
        row = dict(connection.execute("SELECT * FROM deep_analysis_persisted_results").fetchone())
    row.pop("persistence_version")
    row.pop("durable_authority_identity")
    repository = SQLiteStateRepository(tmp_path / "legacy.sqlite3")
    migrations = tuple(m for m in repository._load_migrations() if m.version <= 30)
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations[:-1])
    repository.initialize(now=NOW)
    activation._seed_content(repository, "video-1")
    with repository._connect() as connection:
        connection.execute(f"INSERT INTO deep_analysis_persisted_results ({', '.join(row)}) VALUES ({', '.join(':'+key for key in row)})", row)
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations)
    repository.initialize(now=NOW)
    read = DeepAnalysisPersistenceStore(repository).read_persisted_deep_analysis_result(result_identity=view.result_identity)
    assert read is not None and read.durable_result is None
    assert activation._service(repository).read(content_id="video-1").as_dict() == view.as_dict()
    with pytest.raises(NoteV2Error):
        build_note_v2(read)
    with repository._connect() as connection:
        assert connection.execute("SELECT knowledge_content_json FROM deep_analysis_persisted_results").fetchone()[0] == row["knowledge_content_json"]
        assert not connection.execute("SELECT * FROM deep_analysis_evidence").fetchall()
