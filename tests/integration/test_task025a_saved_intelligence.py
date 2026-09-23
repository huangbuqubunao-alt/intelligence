"""TASK-025A organization state stays separate from Intelligence authority."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_task025_weekly_foundation import (
    WEEK_START,
    _admit,
    _append_card_backed_revision,
    _source,
)

from youtube_intel.intelligence_read import (
    IntelligenceReadRejected,
    VerifiedIntelligenceRead,
)
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.saved_intelligence import (
    SavedIntelligenceService,
    SaveIntelligence,
    UnsaveIntelligence,
)
from youtube_intel.state import (
    IntelligenceClaimKind,
    IntelligenceState,
    SQLiteStateRepository,
)

NOW = datetime(2026, 9, 8, 10, tzinfo=UTC)


def test_fresh_m014_creates_empty_saved_state(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=NOW).version == 24
    connection = repository._connect()
    try:
        assert connection.execute("SELECT * FROM saved_intelligences").fetchall() == []
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 24
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM schema_migrations ORDER BY version"
            )
        ]
        assert names[-10:] == [
            "015_add_timed_transcript_evidence_bindings.sql",
            "016_add_ambiguous_resource_ledger_outcome.sql",
            "017_add_current_content_summary.sql",
            "018_add_global_output_language.sql",
            "019_add_evidence_excerpt_stance.sql",
            "020_add_no_new_intelligence_result.sql",
            "021_seal_distillation_output_language.sql",
            "022_bind_current_local_summary.sql",
            "023_add_evidence_translation_presentation.sql",
            "024_bind_current_summary_to_content.sql",
        ]
    finally:
        connection.close()


def test_save_is_idempotent_and_reads_through_existing_authority(
    tmp_path: Path,
) -> None:
    from youtube_intel.saved_intelligence import (
        SavedIntelligenceService,
        SaveIntelligence,
    )

    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    source_id = _source(repository)
    intelligence_id, revision_id, evidence_id = _admit(
        repository,
        source_id=source_id,
        video_id="saved000001",
        at=WEEK_START,
        conclusion="Saved fixture conclusion.",
    )
    service = SavedIntelligenceService(repository, now=lambda: NOW)
    saved = service.save(SaveIntelligence(intelligence_id=intelligence_id))
    replay = SavedIntelligenceService(
        repository, now=lambda: NOW + timedelta(days=1)
    ).save(SaveIntelligence(intelligence_id=intelligence_id))
    assert replay == saved
    assert saved.intelligence_id == intelligence_id
    assert saved.saved_at == NOW
    page = service.list_saved()
    assert len(page.items) == 1
    assert page.next_cursor is None
    item = page.items[0]
    assert item.relation == saved
    assert item.verified is not None
    assert item.verified.revision_id == revision_id
    assert item.verified.evidence_ids == (evidence_id,)
    assert item.unavailable_code is None


def test_unsave_removes_only_relation_and_resave_gets_new_time(tmp_path: Path) -> None:
    from youtube_intel.saved_intelligence import (
        SavedIntelligenceService,
        SaveIntelligence,
        UnsaveIntelligence,
    )

    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    intelligence_id, revision_id, evidence_id = _admit(
        repository,
        source_id=_source(repository),
        video_id="unsave00001",
        at=WEEK_START,
        conclusion="Preserve this knowledge object.",
    )
    service = SavedIntelligenceService(repository, now=lambda: NOW)
    service.save(SaveIntelligence(intelligence_id=intelligence_id))
    assert service.unsave(UnsaveIntelligence(intelligence_id=intelligence_id)) is None
    assert service.unsave(UnsaveIntelligence(intelligence_id=intelligence_id)) is None
    assert service.unsave(UnsaveIntelligence(intelligence_id="never-existed")) is None
    assert service.list_saved().items == ()
    assert (
        repository.get_intelligence(intelligence_id).current_revision_id == revision_id
    )
    assert repository.get_evidence(evidence_id) is not None
    later = SavedIntelligenceService(repository, now=lambda: NOW + timedelta(days=1))
    assert later.save(
        SaveIntelligence(intelligence_id=intelligence_id)
    ).saved_at == NOW + timedelta(days=1)


def test_local_api_save_list_detail_unsave_contract(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    intelligence_id, revision_id, _ = _admit(
        repository,
        source_id=_source(repository),
        video_id="apisaved001",
        at=WEEK_START,
        conclusion="Existing legal detail remains the content authority.",
    )
    app = LocalApiApplication(
        repository, ProductOrchestrationService(repository), now=lambda: NOW
    )
    body = json.dumps({"intelligence_id": intelligence_id}).encode()
    status, saved = app.handle("POST", "/api/v1/saved-intelligence/save", body)
    assert status == 200
    assert saved["saved"]["intelligence_id"] == intelligence_id
    assert saved["saved"]["saved_at"] == "2026-09-08T10:00:00Z"
    status, listing = app.handle("GET", "/api/v1/saved-intelligence?limit=1")
    assert status == 200
    item = listing["saved"][0]
    assert item["intelligence"]["revision_id"] == revision_id
    assert item["intelligence"]["status"] == "AVAILABLE"
    assert "core_conclusion" not in json.dumps(item)
    detail_status, detail = app.handle("GET", f"/api/v1/intelligence/{intelligence_id}")
    assert detail_status == 200
    assert (
        detail["intelligence"]["card"]["core_conclusion"]
        == "Existing legal detail remains the content authority."
    )
    assert app.handle("POST", "/api/v1/saved-intelligence/unsave", body) == (
        200,
        {"saved": False},
    )
    assert app.handle("GET", "/api/v1/saved-intelligence")[1] == {
        "saved": [],
        "next_cursor": None,
    }


@pytest.mark.parametrize(
    "kind",
    [
        kind
        for kind in IntelligenceClaimKind
        if kind is not IntelligenceClaimKind.UNCLASSIFIED
    ],
)
@pytest.mark.parametrize("state", [IntelligenceState.NEW, IntelligenceState.DISPUTED])
def test_save_preserves_every_claim_kind_and_readable_state(
    tmp_path: Path, kind: IntelligenceClaimKind, state: IntelligenceState
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    intelligence_id, revision_id, evidence_id = _admit(
        repository,
        source_id=_source(repository),
        video_id="claimsave01",
        at=WEEK_START,
        conclusion="A claim retains its original classification.",
        claim_kind=kind,
    )
    if state is IntelligenceState.DISPUTED:
        _append_card_backed_revision(
            repository,
            intelligence_id=intelligence_id,
            prior_revision_id=revision_id,
            revision_id="disputed-revision",
            claim_kind=kind,
            state=state,
            evidence_id=evidence_id,
            at=WEEK_START + timedelta(hours=1),
        )
    before = _domain_rows(repository)
    service = SavedIntelligenceService(repository, now=lambda: NOW)
    service.save(SaveIntelligence(intelligence_id=intelligence_id))
    verified = service.list_saved().items[0].verified
    assert verified is not None
    assert verified.claim_kind is kind
    assert verified.state is state
    assert verified.is_confirmed is False
    assert _domain_rows(repository) == before
    service.unsave(UnsaveIntelligence(intelligence_id))
    assert _domain_rows(repository) == before


def _domain_rows(
    repository: SQLiteStateRepository,
) -> dict[str, tuple[tuple[object, ...], ...]]:
    """Compare all prior-domain rows, not just row counts or selected fields."""
    connection = repository._connect()
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        ]
        return {
            table: tuple(
                sorted(
                    (
                        tuple(row)
                        for row in connection.execute('SELECT * FROM "' + table + '"')
                    ),
                    key=repr,
                )
            )
            for table in tables
            if table not in {"schema_migrations", "saved_intelligences"}
        }
    finally:
        connection.close()


@pytest.mark.parametrize(
    "state", [IntelligenceState.INVALIDATED, IntelligenceState.OVERTURNED]
)
def test_saved_target_later_invalidated_keeps_relation_but_not_trusted_content(
    tmp_path: Path, state: IntelligenceState
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    intelligence_id, revision_id, evidence_id = _admit(
        repository,
        source_id=_source(repository),
        video_id="invalidsave",
        at=WEEK_START,
        conclusion="Old content must never be resurrected.",
    )
    service = SavedIntelligenceService(repository, now=lambda: NOW)
    relation = service.save(SaveIntelligence(intelligence_id=intelligence_id))
    _append_card_backed_revision(
        repository,
        intelligence_id=intelligence_id,
        prior_revision_id=revision_id,
        revision_id="invalidated-revision",
        claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
        state=state,
        evidence_id=evidence_id,
        at=NOW + timedelta(hours=1),
    )
    item = SavedIntelligenceService(repository).list_saved().items[0]
    assert item.relation == relation
    assert item.verified is None
    assert item.unavailable_code == "CURRENT_NOT_ACTIVE"
    with pytest.raises(IntelligenceReadRejected):
        service.save(SaveIntelligence(intelligence_id=intelligence_id))
    app = LocalApiApplication(repository, ProductOrchestrationService(repository))
    payload = app.handle("GET", "/api/v1/saved-intelligence")[1]
    assert payload["saved"][0]["intelligence"] == {
        "status": "UNAVAILABLE",
        "trusted": False,
        "code": "CURRENT_NOT_ACTIVE",
    }
    assert "Old content" not in json.dumps(payload)
    service.unsave(UnsaveIntelligence(intelligence_id))
    assert service.list_saved().items == ()
    assert (
        repository.get_intelligence(intelligence_id).current_revision_id
        == "invalidated-revision"
    )


def test_unavailable_evidence_and_raw_saved_row_never_bypass_reader(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    intelligence_id, _, _ = _admit(
        repository,
        source_id=_source(repository),
        video_id="evidencesav",
        at=WEEK_START,
        conclusion="Evidence must still be available.",
    )
    service = SavedIntelligenceService(repository, now=lambda: NOW)
    saved = service.save(SaveIntelligence(intelligence_id=intelligence_id))
    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="impact handling"):
            connection.execute(
                "UPDATE artifacts SET deleted_at = ? WHERE artifact_id = ?",
                (NOW.isoformat(), "artifact:evidencesav"),
            )
        # Corrupt only this disposable fixture, as if storage was externally tampered.
        # The normal production guard above must continue rejecting this deletion.
        connection.execute(
            "DROP TRIGGER artifact_deletion_requires_no_current_evidence"
        )
        connection.execute(
            "UPDATE artifacts SET deleted_at = ? WHERE artifact_id = ?",
            (NOW.isoformat(), "artifact:evidencesav"),
        )
    finally:
        connection.close()
    assert service.list_saved().items[0].relation == saved
    assert service.list_saved().items[0].verified is None
    with pytest.raises(IntelligenceReadRejected):
        service.save(SaveIntelligence(intelligence_id=intelligence_id))
    repository.create_intelligence(intelligence_id="raw-without-authority", now=NOW)
    with pytest.raises(IntelligenceReadRejected):
        service.save(SaveIntelligence(intelligence_id="raw-without-authority"))
    # Deliberately bypass admission in a persistence attack; relation is still not authority.
    repository.save_intelligence_relation(
        intelligence_id="raw-without-authority", now=NOW, expected_revision_id=None
    )
    items = service.list_saved().items
    assert len(items) == 2 and all(item.verified is None for item in items)
    with pytest.raises(IntelligenceReadRejected):
        service.save(SaveIntelligence(intelligence_id="foreign-or-missing"))


def test_saved_follows_current_legal_revision_without_changing_save_identity_or_time(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    intelligence_id, revision_id, evidence_id = _admit(
        repository,
        source_id=_source(repository),
        video_id="currentsave",
        at=WEEK_START,
        conclusion="The object evolves independently of Save.",
    )
    service = SavedIntelligenceService(repository, now=lambda: NOW)
    saved = service.save(SaveIntelligence(intelligence_id=intelligence_id))
    _append_card_backed_revision(
        repository,
        intelligence_id=intelligence_id,
        prior_revision_id=revision_id,
        revision_id="new-current-revision",
        claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
        state=IntelligenceState.UPDATED,
        evidence_id=evidence_id,
        at=NOW + timedelta(hours=1),
    )
    item = service.list_saved().items[0]
    assert item.relation == saved
    assert item.verified.revision_id == "new-current-revision"
    assert item.verified.state is IntelligenceState.UPDATED
    assert len(service.list_saved().items) == 1


def test_concurrent_saves_and_keyset_pages_are_stable(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    source_id = _source(repository)
    ids = [
        _admit(
            repository,
            source_id=source_id,
            video_id=f"pagesave00{i}",
            at=WEEK_START,
            conclusion=f"Page {i}.",
        )[0]
        for i in range(3)
    ]
    service = SavedIntelligenceService(repository, now=lambda: NOW)
    with ThreadPoolExecutor(max_workers=4) as executor:
        relations = list(
            executor.map(
                lambda _: service.save(SaveIntelligence(intelligence_id=ids[0])),
                range(8),
            )
        )
    assert all(item == relations[0] for item in relations)
    service.save(SaveIntelligence(intelligence_id=ids[1]))
    SavedIntelligenceService(repository, now=lambda: NOW + timedelta(seconds=1)).save(
        SaveIntelligence(intelligence_id=ids[2])
    )
    first = service.list_saved(limit=1)
    assert first.items[0].relation.intelligence_id == ids[2]
    service.unsave(
        UnsaveIntelligence(ids[2])
    )  # Cursor remains valid after its relation is removed.
    second = service.list_saved(limit=1, after=first.next_cursor)
    third = service.list_saved(limit=1, after=second.next_cursor)
    assert [
        second.items[0].relation.intelligence_id,
        third.items[0].relation.intelligence_id,
    ] == sorted(ids[:2])
    assert third.next_cursor is None


@pytest.mark.parametrize(
    "extra",
    [
        {"trusted": True},
        {"card_text": "arbitrary claim"},
        {"saved_at": "2020-01-01T00:00:00Z"},
        {"claim_kind": "FACT"},
        {"user_id": "foreign"},
    ],
)
def test_command_and_api_reject_caller_supplied_authority(
    tmp_path: Path, extra: dict[str, object]
) -> None:
    from youtube_intel.local_api import ApiError

    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    app = LocalApiApplication(repository, ProductOrchestrationService(repository))
    for route in ("save", "unsave"):
        with pytest.raises(ApiError) as error:
            app.handle(
                "POST",
                f"/api/v1/saved-intelligence/{route}",
                json.dumps({"intelligence_id": "target", **extra}).encode(),
            )
        assert error.value.status == 422
        assert "arbitrary claim" not in error.value.message
    with pytest.raises(TypeError):
        SaveIntelligence(intelligence_id="target", **extra)
    assert SavedIntelligenceService(repository).list_saved().items == ()


@pytest.mark.parametrize("identity", [None, True, 12, "", "   ", "x" * 513])
def test_invalid_command_identity_rejected(identity: object) -> None:
    with pytest.raises(ValueError):
        SaveIntelligence(intelligence_id=identity)
    with pytest.raises(ValueError):
        UnsaveIntelligence(intelligence_id=identity)


def test_cannot_mint_verified_read_for_saved_target() -> None:
    with pytest.raises(TypeError, match="minted by AuthoritativeIntelligenceReader"):
        VerifiedIntelligenceRead(
            intelligence_id="raw",
            revision_id="raw",
            claim_kind=IntelligenceClaimKind.FACT,
            state=IntelligenceState.CONFIRMED,
            evidence_ids=("raw",),
        )


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "limit=1&limit=2",
        "trusted=true",
        "after_id=some",
        "after_saved_at=2026-09-08T10:00:00Z",
        "after_id=x&after_saved_at=2026-09-08T10:00:00",
    ],
)
def test_saved_list_query_is_bounded_and_finite(tmp_path: Path, query: str) -> None:
    from youtube_intel.local_api import ApiError

    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    app = LocalApiApplication(repository, ProductOrchestrationService(repository))
    with pytest.raises(ApiError) as error:
        app.handle("GET", f"/api/v1/saved-intelligence?{query}")
    assert error.value.status == 422


def test_saved_relation_schema_denies_foreign_target_and_updates(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO saved_intelligences VALUES ('foreign', ?)",
                (NOW.isoformat(),),
            )
        repository.create_intelligence(intelligence_id="schema-fixture", now=NOW)
        repository.save_intelligence_relation(
            intelligence_id="schema-fixture", now=NOW, expected_revision_id=None
        )
        with pytest.raises(sqlite3.IntegrityError, match="removed before saving"):
            connection.execute("UPDATE saved_intelligences SET saved_at = 'forged'")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM intelligences WHERE intelligence_id = 'schema-fixture'"
            )
    finally:
        connection.close()


def test_v013_upgrade_to_current_preserves_prior_domains_and_save_never_mutates_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_task025_weekly_foundation import FINALIZED_AT

    from youtube_intel.brief import WeeklyBriefService
    from youtube_intel.preference_service import PreferenceApplicationService
    from youtube_intel.source_run import SourceRunPriority, SourceRunWrite
    from youtube_intel.state import FeedbackKind, FeedbackWrite, PreferenceScope
    from youtube_intel.topic import TopicApplicationService, TopicAssociationKind

    path = tmp_path / "upgrade.sqlite3"
    repository = SQLiteStateRepository(path)
    migrations = repository._load_migrations()
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations[:13])
    assert repository.initialize(now=WEEK_START).version == 13
    source_id = _source(repository)
    source = repository.get_source_subscription(source_id)
    assert source is not None
    topics = TopicApplicationService(repository, now=lambda: WEEK_START)
    topic = topics.create_topic(command_id="saved-topic", name="Preserved Topic")
    topic = topics.set_pinned(topic_id=topic.topic_id, pinned=True)
    preferences = PreferenceApplicationService(repository, now=lambda: WEEK_START)
    explicit = preferences.set_explicit_long_term(
        command_id="saved-explicit",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Explicit interest",
    )
    derived = preferences.record_derived_recent(
        command_id="saved-derived",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Derived interest",
    )
    temporary = preferences.set_temporary_focus(
        command_id="saved-temporary",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Temporary interest",
        expires_at=NOW + timedelta(days=1),
    )
    feedback = preferences.record_feedback(
        FeedbackWrite(
            feedback_id="saved-feedback",
            kind=FeedbackKind.IMPORTANT,
            scope=PreferenceScope.GLOBAL_CONTENT,
            target_id=None,
            content=None,
            correction_kind=None,
        )
    )
    source_run = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=source_id,
            command_id="saved-run",
            priority=SourceRunPriority.P0,
            created_at=WEEK_START,
        )
    )
    preserved_intelligence = repository.create_intelligence(
        intelligence_id="preserved-v013-intelligence", now=WEEK_START
    )

    monkeypatch.undo()
    upgraded = SQLiteStateRepository(path)
    assert upgraded.initialize(now=NOW).version == 24
    assert upgraded.get_source_subscription(source_id) == source
    assert upgraded.get_topic(topic.topic_id) == topic
    assert upgraded.get_preference(explicit.preference_id) == explicit
    assert upgraded.get_preference(derived.preference_id) == derived
    assert upgraded.get_preference(temporary.preference_id) == temporary
    assert feedback in upgraded.list_feedback()
    assert upgraded.get_source_run(source_run.run_id) == source_run
    assert upgraded.get_intelligence(preserved_intelligence.intelligence_id) == (
        preserved_intelligence
    )

    intelligence_id, _, _ = _admit(
        upgraded,
        source_id=source_id,
        video_id="upgrade025a",
        at=WEEK_START,
        conclusion="Saved organization must not change prior domain state.",
    )
    TopicApplicationService(upgraded, now=lambda: WEEK_START).associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id=intelligence_id,
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    weekly = WeeklyBriefService(
        upgraded, timezone="UTC", now=lambda: FINALIZED_AT
    ).finalize_week()
    assert len(weekly.items) == 1
    before = _domain_rows(upgraded)
    for table in (
        "source_subscriptions",
        "evidence",
        "intelligences",
        "topics",
        "preferences",
        "feedback_events",
        "source_policy_revisions",
        "source_runs",
        "weekly_briefs",
        "brief_items",
        "distillation_resource_usage",
    ):
        assert before[table], table
    service = SavedIntelligenceService(upgraded, now=lambda: NOW)
    assert service.list_saved().items == ()
    service.save(SaveIntelligence(intelligence_id=intelligence_id))
    assert _domain_rows(upgraded) == before
    service.unsave(UnsaveIntelligence(intelligence_id))
    assert _domain_rows(upgraded) == before
    assert SQLiteStateRepository(path).initialize(now=NOW).version == 24
    assert _domain_rows(upgraded) == before


def test_m014_failure_rolls_back_and_checksum_mismatch_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from youtube_intel.state import MigrationError

    path = tmp_path / "rollback.sqlite3"
    repository = SQLiteStateRepository(path)
    migrations = repository._load_migrations()
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations[:13])
    repository.initialize(now=NOW)
    bad = replace(migrations[13], sql=migrations[13].sql + "\nINVALID SQL;\n")
    monkeypatch.setattr(repository, "_load_migrations", lambda: (*migrations[:13], bad))
    with pytest.raises(MigrationError):
        repository.initialize(now=NOW)

    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 13
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='saved_intelligences'"
            ).fetchone()
            is None
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
            == 13
        )
    finally:
        connection.close()
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations)
    assert repository.initialize(now=NOW).version == 24
    modified = replace(migrations[13], checksum="0" * 64)
    monkeypatch.setattr(
        repository, "_load_migrations", lambda: (*migrations[:13], modified)
    )
    with pytest.raises(MigrationError):
        repository.initialize(now=NOW)


@pytest.mark.parametrize(
    "timestamp",
    [
        "forged",
        "2026-99-08T10:00:00.000000Z",
        "2026-09-08T10:00:00+08:00",
        "2026-09-08T10:00:00.abcdefZ",
    ],
)
def test_saved_timestamp_requires_canonical_utc_storage(
    tmp_path: Path, timestamp: str
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    repository.create_intelligence(intelligence_id="time-fixture", now=NOW)
    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO saved_intelligences VALUES (?, ?)",
                ("time-fixture", timestamp),
            )
    finally:
        connection.close()


def test_save_rejects_revision_changed_between_admission_and_write(tmp_path: Path) -> None:
    from youtube_intel.state import IntegrityConflict

    repository = SQLiteStateRepository(tmp_path / "race.sqlite3")
    repository.initialize(now=NOW)
    intelligence_id, revision_id, evidence_id = _admit(
        repository, source_id=_source(repository), video_id="save-race01",
        at=WEEK_START, conclusion="An old admission cannot overtake Unsave.",
    )
    normal = SavedIntelligenceService(repository, now=lambda: NOW)
    normal.save(SaveIntelligence(intelligence_id=intelligence_id))

    def interleaved_clock() -> datetime:
        # Clock is invoked after reader admission, immediately before the write.
        _append_card_backed_revision(
            repository, intelligence_id=intelligence_id, prior_revision_id=revision_id,
            revision_id="race-invalidated", claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            state=IntelligenceState.INVALIDATED, evidence_id=evidence_id,
            at=NOW + timedelta(seconds=1),
        )
        normal.unsave(UnsaveIntelligence(intelligence_id))
        return NOW + timedelta(seconds=2)

    racing = SavedIntelligenceService(repository, now=interleaved_clock)
    with pytest.raises(IntegrityConflict, match="changed"):
        racing.save(SaveIntelligence(intelligence_id=intelligence_id))
    assert normal.list_saved().items == ()
