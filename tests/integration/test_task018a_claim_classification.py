"""TASK-018A RED contracts for durable IntelligenceRevision claim classification."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import pytest

from youtube_intel import state as state_mod
from youtube_intel.state import (
    EvidenceLineageKind,
    EvidenceRole,
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
    MigrationError,
    SQLiteStateRepository,
    build_evidence_id,
)

NOW = datetime(2026, 9, 7, 9, 0, tzinfo=UTC)


def _path(tmp_path: Path) -> Path:
    return tmp_path / "state.sqlite3"


def _connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _v006_migrations() -> tuple[state_mod._Migration, ...]:
    names = (
        "001_initial.sql",
        "002_add_scoring_lineage.sql",
        "003_add_deep_analysis_persistence.sql",
        "004_add_provider_dispatch_state.sql",
        "005_add_product_orchestration.sql",
        "006_add_intelligence_domain.sql",
    )
    return tuple(
        state_mod._Migration(
            version=version,
            name=name,
            sql=(sql := resources.files("youtube_intel").joinpath("migrations", name).read_text()),
            checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        )
        for version, name in enumerate(names, start=1)
    )


def _seed_evidence(path: Path) -> str:
    timestamp = state_mod.format_utc_datetime(NOW)
    evidence_id = build_evidence_id(
        video_id="video-1",
        artifact_id="artifact-1",
        start_ms=1000,
        end_ms=1500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    with _connection(path) as connection:
        connection.execute(
            "INSERT INTO videos (video_id, channel_id, pipeline_status, pipeline_version, discovered_at, updated_at) "
            "VALUES ('video-1', 'UC_TEST', 'DISCOVERED', 'pipeline-v1', ?, ?)",
            (timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
            "VALUES ('artifact-1', 'artifact-key-1', 'video-1', NULL, 'transcript_canonical', 'DATA', 'transcript.txt', ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            ("a" * 64, timestamp),
        )
        connection.execute(
            "INSERT INTO evidence (evidence_id, video_id, artifact_id, start_ms, end_ms, lineage_kind, role, language, availability, created_at) "
            "VALUES (?, 'video-1', 'artifact-1', 1000, 1500, 'ORIGINAL_TRANSCRIPT', 'PRIMARY_ORIGINAL', 'en', 'AVAILABLE', ?)",
            (evidence_id, timestamp),
        )
    return evidence_id


def _write(
    revision_id: str,
    claim_kind: IntelligenceClaimKind | object,
    evidence_id: str,
    *,
    state: IntelligenceState = IntelligenceState.NEW,
) -> IntelligenceRevisionWrite:
    return IntelligenceRevisionWrite(
        revision_id=revision_id,
        interpretation_kind=IntelligenceInterpretationKind.DISTILLATION,
        claim_kind=claim_kind,  # type: ignore[arg-type]  # adversarial runtime input.
        content_hash="b" * 64,
        state=state,
        reason="evidence-bound interpretation",
        evidence_ids=(evidence_id,),
    )


def test_fresh_database_reaches_v007_with_finite_claim_kind_column(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_path(tmp_path))

    assert repository.initialize(now=NOW).version == 45
    with _connection(_path(tmp_path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 45
        columns = {
            row["name"]: row
            for row in connection.execute('PRAGMA table_info("intelligence_revisions")')
        }
    assert columns["claim_kind"]["dflt_value"] == "'UNCLASSIFIED'"


def test_v006_revision_migrates_to_unclassified_without_guessing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _path(tmp_path)
    repository = SQLiteStateRepository(path)
    monkeypatch.setattr(repository, "_load_migrations", _v006_migrations)
    assert repository.initialize(now=NOW).version == 6
    evidence_id = _seed_evidence(path)
    timestamp = state_mod.format_utc_datetime(NOW)
    with _connection(path) as connection:
        connection.execute(
            "INSERT INTO intelligences (intelligence_id, current_revision_id, created_at) "
            "VALUES ('legacy', NULL, ?)",
            (timestamp,),
        )
        connection.execute(
            "INSERT INTO intelligence_revisions (revision_id, intelligence_id, revision_number, prior_revision_id, interpretation_kind, content_hash, created_at) "
            "VALUES ('legacy-r1', 'legacy', 1, NULL, 'DISTILLATION', ?, ?)",
            ("b" * 64, timestamp),
        )
        connection.execute(
            "INSERT INTO intelligence_revision_evidence (revision_id, evidence_id) VALUES ('legacy-r1', ?)",
            (evidence_id,),
        )
        connection.execute(
            "INSERT INTO intelligence_state_history (state_event_id, intelligence_id, revision_id, state, prior_state, reason, evidence_id, created_at) "
            "VALUES ('state:legacy-r1', 'legacy', 'legacy-r1', 'NEW', NULL, 'legacy row', ?, ?)",
            (evidence_id, timestamp),
        )
        connection.execute(
            "UPDATE intelligences SET current_revision_id = 'legacy-r1' WHERE intelligence_id = 'legacy'"
        )
    monkeypatch.undo()

    assert repository.initialize(now=NOW).version == 45
    migrated = repository.list_intelligence_revisions("legacy")[0]
    assert migrated.claim_kind is IntelligenceClaimKind.UNCLASSIFIED
    assert migrated.interpretation_kind is IntelligenceInterpretationKind.DISTILLATION
    assert migrated.content_hash == "b" * 64


def test_m007_failure_leaves_a_v006_database_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _path(tmp_path)
    repository = SQLiteStateRepository(path)
    monkeypatch.setattr(repository, "_load_migrations", _v006_migrations)
    assert repository.initialize(now=NOW).version == 6
    failed = state_mod._Migration(
        version=7,
        name="007_bad.sql",
        sql="ALTER TABLE intelligence_revisions ADD COLUMN bad TEXT;\nTHIS IS NOT SQL;\n",
        checksum="f" * 64,
    )
    monkeypatch.setattr(repository, "_load_migrations", lambda: _v006_migrations() + (failed,))

    with pytest.raises(MigrationError, match="failed to apply migration 7"):
        repository.initialize(now=NOW)

    with _connection(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 6
        columns = {
            row["name"]
            for row in connection.execute('PRAGMA table_info("intelligence_revisions")')
        }
        assert "bad" not in columns
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 7").fetchone()[0] == 0


@pytest.mark.parametrize(
    "claim_kind",
    (
        IntelligenceClaimKind.FACT,
        IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
        IntelligenceClaimKind.OPINION,
        IntelligenceClaimKind.PREDICTION,
        IntelligenceClaimKind.RUMOR,
        IntelligenceClaimKind.SYSTEM_INFERENCE,
    ),
)
def test_each_explicit_claim_kind_round_trips_without_changing_lifecycle(
    tmp_path: Path, claim_kind: IntelligenceClaimKind
) -> None:
    path = _path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    evidence_id = _seed_evidence(path)
    intelligence_id = f"intelligence-{claim_kind.value}"
    repository.create_intelligence(intelligence_id=intelligence_id, now=NOW)

    saved = repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=_write(f"revision-{claim_kind.value}", claim_kind, evidence_id),
        now=NOW,
    )

    assert saved.claim_kind is claim_kind
    assert repository.list_intelligence_state_history(intelligence_id)[0].state is IntelligenceState.NEW


def test_new_revision_rejects_arbitrary_or_unclassified_claim_kind(tmp_path: Path) -> None:
    path = _path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    evidence_id = _seed_evidence(path)
    repository.create_intelligence(intelligence_id="intelligence-1", now=NOW)

    with pytest.raises(ValueError, match="claim kind"):
        repository.append_intelligence_revision(
            intelligence_id="intelligence-1",
            revision=_write("bad", "MADE_UP", evidence_id),
            now=NOW,
        )
    with pytest.raises(ValueError, match="UNCLASSIFIED"):
        repository.append_intelligence_revision(
            intelligence_id="intelligence-1",
            revision=_write("legacy", IntelligenceClaimKind.UNCLASSIFIED, evidence_id),
            now=NOW,
        )


def test_claim_kind_is_immutable_and_new_revision_preserves_history(tmp_path: Path) -> None:
    path = _path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    evidence_id = _seed_evidence(path)
    repository.create_intelligence(intelligence_id="intelligence-1", now=NOW)
    repository.append_intelligence_revision(
        intelligence_id="intelligence-1",
        revision=_write("revision-1", IntelligenceClaimKind.PREDICTION, evidence_id),
        now=NOW,
    )
    repository.append_intelligence_revision(
        intelligence_id="intelligence-1",
        revision=_write(
            "revision-2",
            IntelligenceClaimKind.SYSTEM_INFERENCE,
            evidence_id,
            state=IntelligenceState.UPDATED,
        ),
        now=NOW,
    )

    assert [item.claim_kind for item in repository.list_intelligence_revisions("intelligence-1")] == [
        IntelligenceClaimKind.PREDICTION,
        IntelligenceClaimKind.SYSTEM_INFERENCE,
    ]
    with _connection(path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE intelligence_revisions SET claim_kind = 'FACT' WHERE revision_id = 'revision-1'"
            )


def test_fact_is_not_trust_and_system_inference_remains_distinct(tmp_path: Path) -> None:
    path = _path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    evidence_id = _seed_evidence(path)
    repository.create_intelligence(intelligence_id="intelligence-1", now=NOW)

    saved = repository.append_intelligence_revision(
        intelligence_id="intelligence-1",
        revision=_write("revision-1", IntelligenceClaimKind.FACT, evidence_id),
        now=NOW,
    )

    assert saved.claim_kind is IntelligenceClaimKind.FACT
    assert repository.list_intelligence_state_history("intelligence-1")[0].state is IntelligenceState.NEW


def test_database_rejects_raw_arbitrary_and_new_unclassified_claim_kinds(tmp_path: Path) -> None:
    path = _path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    timestamp = state_mod.format_utc_datetime(NOW)
    repository.create_intelligence(intelligence_id="intelligence-1", now=NOW)

    with _connection(path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO intelligence_revisions (revision_id, intelligence_id, revision_number, prior_revision_id, interpretation_kind, claim_kind, content_hash, created_at) "
                "VALUES ('forged-kind', 'intelligence-1', 1, NULL, 'DISTILLATION', 'FORGED', ?, ?)",
                ("b" * 64, timestamp),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO intelligence_revisions (revision_id, intelligence_id, revision_number, prior_revision_id, interpretation_kind, claim_kind, content_hash, created_at) "
                "VALUES ('unclassified-kind', 'intelligence-1', 1, NULL, 'DISTILLATION', 'UNCLASSIFIED', ?, ?)",
                ("b" * 64, timestamp),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO intelligence_revisions (revision_id, intelligence_id, revision_number, prior_revision_id, interpretation_kind, content_hash, created_at) "
                "VALUES ('defaulted-kind', 'intelligence-1', 1, NULL, 'DISTILLATION', ?, ?)",
                ("b" * 64, timestamp),
            )


def test_m007_is_packaged_and_no_m008_is_introduced() -> None:
    migrations = resources.files("youtube_intel").joinpath("migrations")

    assert migrations.joinpath("007_add_intelligence_claim_classification.sql").is_file()
    assert not migrations.joinpath("008_add_intelligence_claim_classification.sql").exists()
    assert "UPDATE intelligence_revisions" not in migrations.joinpath(
        "007_add_intelligence_claim_classification.sql"
    ).read_text(encoding="utf-8")
