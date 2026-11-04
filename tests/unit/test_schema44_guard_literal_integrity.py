"""Quoted SQL literal changes must fail closed, even with no synthesis rows."""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import Path
from typing import cast

import pytest
from conftest import _load_module

from youtube_intel import system_synthesis_persistence as persistence
from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
from youtube_intel.state import (
    DistillationExecutionWrite,
    SQLiteStateRepository,
    StateStoreError,
)

support = _load_module("test_long_input_wait_lifecycle")
GUARD = "distillation_moonshot_cloud_dispatch_requires_authorization"


def workspace(tmp_path: Path) -> tuple[SQLiteStateRepository, Path, str, str]:
    return cast(tuple[SQLiteStateRepository, Path, str, str], support.workspace(tmp_path, 2)[:4])


def alter_literal(connection: sqlite3.Connection, provider: str) -> None:
    original = connection.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?", (GUARD,)).fetchone()[
        0
    ]
    old = "WHEN NEW.selected_provider = 'moonshot'"
    assert original.count(old) == 1
    changed = original.replace(old, "WHEN NEW.selected_provider = '" + provider + "'", 1)
    assert changed != original
    connection.execute("DROP TRIGGER " + GUARD)
    connection.execute(changed)


@pytest.mark.parametrize("provider", ["moon shot", "moon\tshot", "moon\nshot"])
@pytest.mark.parametrize("boundary", ["schema", "startup", "backup"])
def test_quoted_predicate_whitespace_is_rejected_without_any_sidecars(
    tmp_path: Path, provider: str, boundary: str
) -> None:
    repo, data, _, _ = workspace(tmp_path)
    with repo._connect() as connection:
        persistence.verify_schema(connection)
        assert all(
            connection.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0 for table in persistence.TABLES
        )
    assert repo.initialize(now=support.NOW).version == 44
    backup = BackupRestoreService(database=repo._database_path, data_root=data)
    assert backup.readiness()["ready"]
    with repo._connect() as connection:
        alter_literal(connection, provider)
    if boundary == "schema":
        with repo._connect() as connection, pytest.raises(StateStoreError, match="schema44"):
            persistence.verify_schema(connection)
    elif boundary == "startup":
        with pytest.raises(StateStoreError, match="schema44"):
            repo.initialize(now=support.NOW)
    else:
        assert not backup.readiness()["ready"]


def test_restore_refuses_resigned_archive_with_changed_quoted_authorization_predicate(tmp_path: Path) -> None:
    repo, data, _, _ = workspace(tmp_path)
    backup = BackupRestoreService(database=repo._database_path, data_root=data)
    download = backup.backup_download(backup.create_backup().backup_id)
    assert download is not None
    archive, _ = download
    with zipfile.ZipFile(io.BytesIO(archive.read_bytes())) as source:
        infos = source.infolist()
        members = {info.filename: source.read(info) for info in infos}
    database = tmp_path / "synthetic-mutated-archive.sqlite3"
    database.write_bytes(members["database/state.sqlite"])
    with sqlite3.connect(database) as connection:
        alter_literal(connection, "moon shot")
    # A SQLite connection context commits but does not close/checkpoint WAL.
    assert connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
    connection.close()
    changed = database.read_bytes()
    manifest = json.loads(members["manifest.json"])
    manifest["database"]["sha256"] = hashlib.sha256(changed).hexdigest()
    manifest["database"]["size_bytes"] = len(changed)
    members["database/state.sqlite"] = changed
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as target:
        for info in infos:
            target.writestr(info, members[info.filename])
    with zipfile.ZipFile(io.BytesIO(output.getvalue())) as repacked:
        assert repacked.testzip() is None
        packed_database = repacked.read("database/state.sqlite")
        packed_manifest = json.loads(repacked.read("manifest.json"))
        assert packed_manifest["database"]["size_bytes"] == len(packed_database)
        assert packed_manifest["database"]["sha256"] == hashlib.sha256(packed_database).hexdigest()
        packed_database_path = tmp_path / "packed-sqlite-check.sqlite3"
        packed_database_path.write_bytes(packed_database)
        archived_connection = sqlite3.connect(packed_database_path)
        try:
            archived_guard = archived_connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?", (GUARD,)
            ).fetchone()[0]
            assert "WHEN NEW.selected_provider = 'moon shot'" in archived_guard
        finally:
            archived_connection.close()
    # Size/SHA/CRC are repaired, so rejection must reach SQLite authority checks.
    with pytest.raises(BackupRestoreError, match="System synthesis provenance"):
        backup.stage_restore(output.getvalue())
    with repo._connect() as connection:
        persistence.verify_schema(connection)  # rejected archive did not replace the live database
        assert all(
            connection.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0 for table in persistence.TABLES
        )


def test_normal_schema44_keeps_legacy_reserved_claim_without_consent_blocked(tmp_path: Path) -> None:
    repo, _, source, video = workspace(tmp_path)
    execution = DistillationExecutionWrite(
        execution_id="synthetic-legacy-no-consent",
        source_id=source,
        video_id=video,
        reason="MANUAL_CONTENT:synthetic-no-consent",
        use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider="moonshot",
        selected_model="kimi-k2.6",
        output_language="en",
    )
    repo.reserve_distillation_execution(execution, now=support.NOW)
    with pytest.raises(sqlite3.IntegrityError, match="prior execution authorization"):
        repo.claim_reserved_distillation_execution(
            **{
                name: getattr(execution, name)
                for name in (
                    "execution_id",
                    "source_id",
                    "video_id",
                    "reason",
                    "use_case",
                    "selected_provider",
                    "selected_model",
                    "output_language",
                )
            },
            now=support.NOW,
        )
    with repo._connect() as connection:
        assert (
            connection.execute(
                "SELECT invocation_count FROM distillation_execution_checkpoints WHERE execution_id=?",
                (execution.execution_id,),
            ).fetchone()[0]
            == 0
        )
        assert connection.execute("SELECT count(*) FROM distillation_moonshot_cloud_authorizations").fetchone()[0] == 0
        assert all(
            connection.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0 for table in persistence.TABLES
        )
