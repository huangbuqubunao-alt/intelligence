"""031 extends the accepted schema without occupying M13's 029."""

import hashlib
from datetime import UTC, datetime

import pytest

from youtube_intel.state import MigrationError, SQLiteStateRepository

NOW = datetime(2026, 10, 3, tzinfo=UTC)


def test_upgrade_30_to_31_and_integrity(tmp_path, monkeypatch):
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    migrations = repo._load_migrations()
    assert [m.version for m in migrations] == [*range(1, 29), 30, 31]
    monkeypatch.setattr(repo, "_load_migrations", lambda: migrations[:-1])
    assert repo.initialize(now=NOW).version == 30
    monkeypatch.setattr(repo, "_load_migrations", lambda: migrations)
    assert repo.initialize(now=NOW).version == 31
    assert repo.initialize(now=NOW).version == 31
    assert migrations[-1].checksum == hashlib.sha256(migrations[-1].sql.encode()).hexdigest()
    with repo._connect() as db:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()


def test_failed_31_is_atomic(tmp_path, monkeypatch):
    from dataclasses import replace

    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    migrations = repo._load_migrations()
    monkeypatch.setattr(repo, "_load_migrations", lambda: migrations[:-1])
    repo.initialize(now=NOW)
    broken = replace(migrations[-1], sql=migrations[-1].sql + "\nCREATE TABLE broken(;")
    monkeypatch.setattr(repo, "_load_migrations", lambda: (*migrations[:-1], broken))
    with pytest.raises(MigrationError, match="failed to apply migration 31"):
        repo.initialize(now=NOW)
    with repo._connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 30
        assert not db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'research_%'").fetchall()
