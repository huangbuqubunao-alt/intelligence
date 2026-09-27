"""TASK-018 RED contracts for the m006 Intelligence persistence foundation."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import pytest

from youtube_intel import state as state_mod
from youtube_intel.state import (
    DependencyEdgeWrite,
    DependencyRelation,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceWrite,
    IntegrityConflict,
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
    MigrationError,
    SQLiteStateRepository,
    StateStoreError,
    build_evidence_id,
)

NOW = datetime(2026, 9, 4, 9, 0, tzinfo=UTC)


def _database_path(tmp_path: Path) -> Path:
    return tmp_path / "state.sqlite3"


def _connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _v005_migrations() -> tuple[state_mod._Migration, ...]:
    migrations: list[state_mod._Migration] = []
    for version, name in enumerate(
        (
            "001_initial.sql",
            "002_add_scoring_lineage.sql",
            "003_add_deep_analysis_persistence.sql",
            "004_add_provider_dispatch_state.sql",
            "005_add_product_orchestration.sql",
        ),
        start=1,
    ):
        sql_bytes = resources.files("youtube_intel").joinpath("migrations", name).read_bytes()
        migrations.append(
            state_mod._Migration(
                version=version,
                name=name,
                sql=sql_bytes.decode("utf-8"),
                checksum=hashlib.sha256(sql_bytes).hexdigest(),
            )
        )
    return tuple(migrations)


def _initialize_v005(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    monkeypatch.setattr(repository, "_load_migrations", _v005_migrations)
    assert repository.initialize(now=NOW).version == 5
    monkeypatch.undo()
    return repository


def _seed_video_and_artifact(path: Path) -> None:
    now = state_mod.format_utc_datetime(NOW)
    with _connection(path) as connection:
        connection.execute(
            "INSERT INTO videos (video_id, channel_id, pipeline_status, pipeline_version, discovered_at, updated_at) "
            "VALUES ('video-1', 'UC_TEST', 'DISCOVERED', 'pipeline-v1', ?, ?)",
            (now, now),
        )
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
            "VALUES ('artifact-1', 'artifact-key-1', 'video-1', NULL, 'transcript_canonical', 'DATA', 'transcript.txt', ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            ("a" * 64, now),
        )


def _evidence_write(*, artifact_id: str = "artifact-1", start_ms: int = 1000) -> EvidenceWrite:
    return EvidenceWrite(
        evidence_id=build_evidence_id(
            video_id="video-1",
            artifact_id=artifact_id,
            start_ms=start_ms,
            end_ms=start_ms + 500,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
        ),
        video_id="video-1",
        artifact_id=artifact_id,
        start_ms=start_ms,
        end_ms=start_ms + 500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en",
        availability=EvidenceAvailability.AVAILABLE,
    )


def _append_first_revision(
    repository: SQLiteStateRepository, evidence_id: str
) -> tuple[str, str]:
    intelligence_id = "intelligence-1"
    revision_id = "revision-1"
    repository.create_intelligence(intelligence_id=intelligence_id, now=NOW)
    repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id=revision_id,
            interpretation_kind=IntelligenceInterpretationKind.DISTILLATION,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash="b" * 64,
            state=IntelligenceState.NEW,
            reason="initial evidence-bound interpretation",
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    return intelligence_id, revision_id


def test_fresh_database_applies_m006_with_exact_domain_schema(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))

    version = repository.initialize(now=NOW)

    assert (version.version, version.name) == (
        28,
        "028_add_cloud_response_failure_ledger.sql",
    )
    with _connection(_database_path(tmp_path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 28
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert {
            "evidence",
            "intelligences",
            "intelligence_revisions",
            "intelligence_state_history",
            "intelligence_revision_evidence",
            "dependency_edges",
        } <= tables
        revision_fks = {
            (row["from"], row["table"], row["to"], row["on_delete"])
            for row in connection.execute('PRAGMA foreign_key_list("intelligence_revisions")')
        }
    assert ("intelligence_id", "intelligences", "intelligence_id", "RESTRICT") in revision_fks


def test_v005_upgrade_preserves_source_and_automation_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _database_path(tmp_path)
    repository = _initialize_v005(tmp_path, monkeypatch)
    now = state_mod.format_utc_datetime(NOW)
    with _connection(path) as connection:
        connection.execute(
            "INSERT INTO source_subscriptions (source_id, source_type, canonical_url, channel_id, video_id, display_name, enabled, processing_policy, created_at, updated_at) "
            "VALUES ('source-1', 'CHANNEL', 'https://www.youtube.com/channel/UC_TEST', 'UC_TEST', NULL, 'Test', 1, 'STANDARD_INTELLIGENCE', ?, ?)",
            (now, now),
        )
        connection.execute(
            "INSERT INTO automation_schedules (schedule_id, target_type, target_id, frequency, weekday, local_time, timezone, enabled, created_at, updated_at) "
            "VALUES ('schedule-1', 'SOURCE_CHECK', 'source-1', 'DAILY', NULL, '09:00', 'UTC', 1, ?, ?)",
            (now, now),
        )

    assert repository.initialize(now=NOW).version == 28
    assert repository.initialize(now=NOW).version == 28
    with _connection(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM source_subscriptions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM automation_schedules").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 8").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 9").fetchone()[0] == 1


def test_m006_failure_rolls_back_schema_history_and_user_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _database_path(tmp_path)
    repository = _initialize_v005(tmp_path, monkeypatch)
    bad = state_mod._Migration(
        version=6,
        name="006_bad.sql",
        sql="CREATE TABLE must_rollback (id TEXT);\nTHIS IS NOT SQL;\n",
        checksum="f" * 64,
    )
    monkeypatch.setattr(repository, "_load_migrations", lambda: _v005_migrations() + (bad,))

    with pytest.raises(MigrationError, match="failed to apply migration 6"):
        repository.initialize(now=NOW)

    with _connection(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 6").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'must_rollback'").fetchone()[0] == 0


def test_evidence_identity_is_deterministic_and_provenance_specific(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    _seed_video_and_artifact(_database_path(tmp_path))
    first = _evidence_write()
    same = _evidence_write()
    different_timestamp = _evidence_write(start_ms=1500)

    saved = repository.create_evidence(first, now=NOW)

    assert saved.evidence_id == same.evidence_id
    assert saved.evidence_id != different_timestamp.evidence_id
    assert saved.video_id == "video-1"
    assert saved.artifact_id == "artifact-1"
    with pytest.raises(IntegrityConflict):
        repository.create_evidence(same, now=NOW)


def test_revisions_append_preserve_history_and_current_pointer_is_scoped(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    _seed_video_and_artifact(_database_path(tmp_path))
    evidence = repository.create_evidence(_evidence_write(), now=NOW)
    intelligence_id, first_revision_id = _append_first_revision(repository, evidence.evidence_id)

    second = repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id="revision-2",
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=IntelligenceClaimKind.FACT,
            content_hash="c" * 64,
            state=IntelligenceState.UPDATED,
            reason="correction preserves prior interpretation",
            evidence_ids=(evidence.evidence_id,),
        ),
        now=NOW,
    )

    assert second.prior_revision_id == first_revision_id
    assert [record.revision_id for record in repository.list_intelligence_revisions(intelligence_id)] == [
        first_revision_id,
        "revision-2",
    ]
    assert repository.get_intelligence(intelligence_id).current_revision_id == "revision-2"
    repository.create_intelligence(intelligence_id="intelligence-2", now=NOW)
    with _connection(_database_path(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE intelligences SET current_revision_id = 'revision-1' WHERE intelligence_id = 'intelligence-2'")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE intelligence_revisions SET content_hash = ? WHERE revision_id = ?", ("d" * 64, first_revision_id))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE intelligences SET current_revision_id = ? WHERE intelligence_id = ?",
                (first_revision_id, intelligence_id),
            )


def test_unavailable_or_missing_evidence_cannot_support_current_revision_or_be_deleted(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    _seed_video_and_artifact(_database_path(tmp_path))
    evidence = repository.create_evidence(_evidence_write(), now=NOW)
    intelligence_id, _ = _append_first_revision(repository, evidence.evidence_id)

    with pytest.raises(StateStoreError, match="evidence does not exist"):
        repository.append_intelligence_revision(
            intelligence_id=intelligence_id,
            revision=IntelligenceRevisionWrite(
                revision_id="revision-missing-evidence",
                interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
                claim_kind=IntelligenceClaimKind.FACT,
                content_hash="e" * 64,
                state=IntelligenceState.UPDATED,
                reason="must fail closed",
                evidence_ids=("missing-evidence",),
            ),
            now=NOW,
        )
    with pytest.raises(IntegrityConflict, match="current"):
        repository.set_evidence_availability(
            evidence_id=evidence.evidence_id,
            availability=EvidenceAvailability.UNAVAILABLE,
        )
    with _connection(_database_path(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM evidence WHERE evidence_id = ?", (evidence.evidence_id,))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE artifacts SET deleted_at = ? WHERE artifact_id = 'artifact-1'",
                (state_mod.format_utc_datetime(NOW),),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE videos SET availability = 'deleted' WHERE video_id = 'video-1'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO intelligence_revision_evidence (revision_id, evidence_id) VALUES ('revision-1', ?)",
                (evidence.evidence_id,),
            )


def test_dependency_edges_are_directed_finite_and_identity_bound(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    _seed_video_and_artifact(_database_path(tmp_path))
    evidence = repository.create_evidence(_evidence_write(), now=NOW)
    intelligence_id, revision_id = _append_first_revision(repository, evidence.evidence_id)

    edge = repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id="edge-1",
            dependent_revision_id=revision_id,
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=evidence.evidence_id,
            input_revision_id=None,
        ),
        now=NOW,
    )

    assert edge.dependent_revision_id == revision_id
    unlinked_evidence = repository.create_evidence(
        _evidence_write(start_ms=2000), now=NOW
    )
    with pytest.raises(IntegrityConflict, match="dependency edge"):
        repository.create_dependency_edge(
            DependencyEdgeWrite(
                edge_id="edge-unlinked-evidence",
                dependent_revision_id=revision_id,
                relation=DependencyRelation.EVIDENCE_SUPPORT,
                input_evidence_id=unlinked_evidence.evidence_id,
                input_revision_id=None,
            ),
            now=NOW,
        )
    with pytest.raises(StateStoreError, match="requires exactly one"):
        repository.create_dependency_edge(
            DependencyEdgeWrite(
                edge_id="edge-bad",
                dependent_revision_id=revision_id,
                relation=DependencyRelation.EVIDENCE_SUPPORT,
                input_evidence_id=evidence.evidence_id,
                input_revision_id=revision_id,
            ),
            now=NOW,
        )
    with _connection(_database_path(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO dependency_edges (edge_id, dependent_revision_id, relation, input_evidence_id, input_revision_id, created_at) "
                "VALUES ('edge-forged', ?, 'ARBITRARY_AUTHORITY', ?, NULL, ?)",
                (revision_id, evidence.evidence_id, state_mod.format_utc_datetime(NOW)),
            )


def test_m006_is_package_discoverable_and_contains_no_execution_tables() -> None:
    migration = resources.files("youtube_intel").joinpath("migrations", "006_add_intelligence_domain.sql")

    assert migration.is_file()
    sql = migration.read_text(encoding="utf-8")
    assert "CREATE TABLE provider" not in sql
    assert "CREATE TABLE queue" not in sql
