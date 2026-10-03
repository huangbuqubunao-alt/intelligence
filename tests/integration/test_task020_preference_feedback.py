"""TASK-020 preference, feedback, expiry, and intent-boundary contracts."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel import state as state_mod
from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.preference_service import PreferenceApplicationService
from youtube_intel.state import (
    FeedbackCorrectionKind,
    FeedbackKind,
    FeedbackWrite,
    IntegrityConflict,
    PreferenceHorizon,
    PreferenceProvenance,
    PreferenceScope,
    PreferenceState,
    PreferenceWrite,
    SQLiteStateRepository,
)

NOW = datetime(2026, 9, 7, 9, 0, tzinfo=UTC)


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    version = repository.initialize(now=NOW)
    assert version.version == 32
    return repository


def _service(repository: SQLiteStateRepository) -> PreferenceApplicationService:
    return PreferenceApplicationService(repository, now=lambda: NOW)


def _app(repository: SQLiteStateRepository) -> LocalApiApplication:
    return LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        now=lambda: NOW,
    )


def test_m008_fresh_database_reaches_exactly_user_version_8_and_no_m009(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    m008 = repository._load_migrations()[:8]
    monkeypatch.setattr(repository, "_load_migrations", lambda: m008)
    assert repository.initialize(now=NOW).version == 8

    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 8
        migrations = tuple(
            row["name"]
            for row in connection.execute(
                "SELECT name FROM schema_migrations ORDER BY version"
            )
        )
        assert migrations[-1] == "008_add_preference_feedback.sql"
        assert not any(name.startswith("009_") for name in migrations)
    finally:
        connection.close()


def test_long_term_recent_and_temporary_preferences_remain_distinct(
    tmp_path: Path,
) -> None:
    service = _service(_repository(tmp_path))
    long_term = service.set_explicit_long_term(
        command_id="long-term-1",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="长期重点关注 AI Agent 产品落地。",
    )
    recent = service.record_derived_recent(
        command_id="recent-1",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Recent interest in Gemini.",
    )
    temporary = service.set_temporary_focus(
        command_id="temporary-1",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="未来 7 天重点关注 Claude Code。",
        expires_at=NOW + timedelta(days=7),
    )

    active = service.active_preferences(now=NOW)

    assert [(item.preference_id, item.horizon, item.provenance) for item in active] == [
        (long_term.preference_id, PreferenceHorizon.LONG_TERM, PreferenceProvenance.EXPLICIT),
        (recent.preference_id, PreferenceHorizon.RECENT, PreferenceProvenance.DERIVED),
        (temporary.preference_id, PreferenceHorizon.TEMPORARY_FOCUS, PreferenceProvenance.TEMPORARY),
    ]


def test_temporary_focus_is_historical_but_inactive_at_its_expiry_boundary(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    service = _service(repository)
    temporary = service.set_temporary_focus(
        command_id="temporary-boundary",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="这个月多看本地模型。",
        expires_at=NOW + timedelta(hours=1),
    )

    assert [item.preference_id for item in service.active_preferences(now=NOW)] == [
        temporary.preference_id
    ]
    assert service.active_preferences(now=NOW + timedelta(hours=1)) == ()
    assert repository.get_preference(temporary.preference_id) == temporary
    assert repository.list_preference_state_events(temporary.preference_id)


def test_feedback_is_append_only_and_cannot_overwrite_explicit_preference(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    service = _service(repository)
    explicit = service.set_explicit_long_term(
        command_id="explicit-rule",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="少给我 benchmark。",
    )
    first = service.record_feedback(
        FeedbackWrite(
            feedback_id="feedback-more",
            kind=FeedbackKind.MORE_LIKE_THIS,
            scope=PreferenceScope.GLOBAL_CONTENT,
            target_id=None,
            content=None,
            correction_kind=None,
        )
    )
    second = service.record_feedback(
        FeedbackWrite(
            feedback_id="feedback-less",
            kind=FeedbackKind.LESS_LIKE_THIS,
            scope=PreferenceScope.GLOBAL_CONTENT,
            target_id=None,
            content=None,
            correction_kind=None,
        )
    )

    assert [item.feedback_id for item in repository.list_feedback()] == [
        first.feedback_id,
        second.feedback_id,
    ]
    assert repository.get_preference(explicit.preference_id) == explicit
    assert repository.list_preferences() == (explicit,)
    with pytest.raises(sqlite3.IntegrityError, match="feedback events are immutable"):
        connection = repository._connect()
        try:
            connection.execute(
                "UPDATE feedback_events SET kind = 'IMPORTANT' WHERE feedback_id = ?",
                (first.feedback_id,),
            )
        finally:
            connection.close()


@pytest.mark.parametrize(
    "kind",
    (FeedbackKind.MORE_LIKE_THIS, FeedbackKind.LESS_LIKE_THIS, FeedbackKind.IMPORTANT),
)
def test_quick_feedback_kinds_round_trip_as_distinct_finite_values(
    tmp_path: Path, kind: FeedbackKind
) -> None:
    repository = _repository(tmp_path)
    feedback = _service(repository).record_feedback(
        FeedbackWrite(
            feedback_id=f"quick-{kind.value}",
            kind=kind,
            scope=PreferenceScope.GLOBAL_CONTENT,
            target_id=None,
            content=None,
            correction_kind=None,
        )
    )

    assert feedback.kind is kind
    assert repository.list_feedback() == (feedback,)


def test_factual_correction_is_not_preference_feedback_and_does_not_derive_state(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    service = _service(repository)
    correction = service.record_feedback(
        FeedbackWrite(
            feedback_id="correction-1",
            kind=FeedbackKind.FACTUAL_CORRECTION,
            scope=PreferenceScope.GLOBAL_CONTENT,
            target_id=None,
            content="The Intelligence interpreted the source incorrectly.",
            correction_kind=FeedbackCorrectionKind.WRONG_INTERPRETATION,
        )
    )

    assert correction.kind is FeedbackKind.FACTUAL_CORRECTION
    assert correction.correction_kind is FeedbackCorrectionKind.WRONG_INTERPRETATION
    assert repository.list_preferences() == ()
    assert service.active_preferences(now=NOW) == ()


def test_invalid_kind_horizon_scope_and_untrusted_derived_api_command_are_rejected(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    service = _service(repository)
    with pytest.raises(ValueError):
        service.record_feedback(
            FeedbackWrite(  # type: ignore[arg-type]
                feedback_id="invalid-kind",
                kind="CONFIGURE_SOURCE",  # type: ignore[arg-type]
                scope=PreferenceScope.GLOBAL_CONTENT,
                target_id=None,
                content=None,
                correction_kind=None,
            )
        )
    with pytest.raises(ValueError):
        service.set_explicit_long_term(
            command_id="invalid-scope",
            scope="ARBITRARY_SCOPE",  # type: ignore[arg-type]
            target_id=None,
            statement="nope",
        )

    with pytest.raises(ApiError) as rejected:
        _app(repository).handle(
            "POST",
            "/api/v1/settings/preferences/recent",
            b'{"command_id":"forged","statement":"make this explicit"}',
        )
    assert rejected.value.status == 404
    assert rejected.value.code == "NOT_FOUND"


def test_api_accepts_only_validated_explicit_temporary_and_feedback_commands(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    app = _app(repository)

    created, preference_payload = app.handle(
        "POST",
        "/api/v1/settings/preferences/long-term",
        b'{"command_id":"api-long","scope":"GLOBAL_CONTENT","statement":"Focus on agents"}',
    )
    temporary_status, temporary_payload = app.handle(
        "POST",
        "/api/v1/settings/preferences/temporary-focus",
        b'{"command_id":"api-temp","scope":"GLOBAL_CONTENT","statement":"Claude Code","expires_at":"2026-09-08T09:00:00Z"}',
    )
    feedback_status, feedback_payload = app.handle(
        "POST",
        "/api/v1/settings/feedback",
        b'{"feedback_id":"api-natural","kind":"NATURAL_LANGUAGE","scope":"GLOBAL_CONTENT","content":"More implementation detail please."}',
    )
    with pytest.raises(ApiError) as rejected:
        app.handle(
            "POST",
            "/api/v1/settings/feedback",
            b'{"feedback_id":"invalid","kind":"ARBITRARY","scope":"GLOBAL_CONTENT"}',
        )

    assert created == 201
    assert preference_payload["preference"]["provenance"] == "EXPLICIT"  # type: ignore[index]
    assert temporary_status == 201
    assert temporary_payload["preference"]["horizon"] == "TEMPORARY_FOCUS"  # type: ignore[index]
    assert feedback_status == 201
    assert feedback_payload["feedback"]["kind"] == "NATURAL_LANGUAGE"  # type: ignore[index]
    assert rejected.value.status == 422
    assert rejected.value.code == "VALIDATION_ERROR"
    assert repository.get_source_subscription("any-source") is None


def test_edit_and_delete_create_immutable_state_history_without_rewriting_records(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    service = _service(repository)
    original = service.set_explicit_long_term(
        command_id="edit-original",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Focus on AI agents.",
    )

    replacement = service.replace_explicit_long_term(
        command_id="edit-replacement",
        preference_id=original.preference_id,
        statement="Focus on AI agent implementation.",
    )
    deleted = service.delete_preference(
        command_id="delete-replacement", preference_id=replacement.preference_id
    )

    assert repository.get_preference(original.preference_id) == original
    assert repository.get_preference(replacement.preference_id) == replacement
    assert [event.state for event in repository.list_preference_state_events(original.preference_id)] == [
        PreferenceState.ACTIVATED,
        PreferenceState.REPLACED,
    ]
    assert deleted.state is PreferenceState.DELETED
    assert service.active_preferences(now=NOW) == ()


def test_duplicate_feedback_command_is_idempotent_but_conflicting_reuse_is_rejected(
    tmp_path: Path,
) -> None:
    service = _service(_repository(tmp_path))
    command = FeedbackWrite(
        feedback_id="idempotent-feedback",
        kind=FeedbackKind.IMPORTANT,
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        content=None,
        correction_kind=None,
    )

    assert service.record_feedback(command) == service.record_feedback(command)
    with pytest.raises(IntegrityConflict, match="identity conflicts"):
        service.record_feedback(
            FeedbackWrite(
                feedback_id="idempotent-feedback",
                kind=FeedbackKind.NATURAL_LANGUAGE,
                scope=PreferenceScope.GLOBAL_CONTENT,
                target_id=None,
                content="Different payload",
                correction_kind=None,
            )
        )


def test_v007_upgrade_preserves_source_automation_and_trusted_intelligence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.sqlite3"
    legacy = SQLiteStateRepository(path)
    all_migrations = legacy._load_migrations()
    v007 = all_migrations[:7]
    monkeypatch.setattr(legacy, "_load_migrations", lambda: v007)
    assert legacy.initialize(now=NOW).version == 7
    timestamp = "2026-09-07T09:00:00.000000Z"
    connection = legacy._connect()
    try:
        connection.execute(
            "INSERT INTO source_subscriptions (source_id, source_type, canonical_url, channel_id, video_id, display_name, enabled, processing_policy, created_at, updated_at) VALUES ('source-1', 'CHANNEL', 'https://www.youtube.com/channel/UC_TEST', 'UC_TEST', NULL, 'Source', 1, 'STANDARD_INTELLIGENCE', ?, ?)",
            (timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO automation_schedules (schedule_id, target_type, target_id, frequency, weekday, local_time, timezone, enabled, created_at, updated_at) VALUES ('schedule-1', 'SOURCE_CHECK', 'source-1', 'DAILY', NULL, '09:00', 'UTC', 1, ?, ?)",
            (timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO videos (video_id, channel_id, pipeline_status, pipeline_version, availability, discovered_at, updated_at) VALUES ('video-1', 'UC_TEST', 'DISCOVERED', 'v1', 'public', ?, ?)",
            (timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) VALUES ('artifact-1', 'artifact-key', 'video-1', NULL, 'transcript_canonical', 'DATA', 'transcript.txt', ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            ("a" * 64, timestamp),
        )
        connection.execute(
            "INSERT INTO evidence (evidence_id, video_id, artifact_id, start_ms, end_ms, lineage_kind, role, language, availability, created_at) VALUES ('evidence-1', 'video-1', 'artifact-1', 0, 1, 'ORIGINAL_TRANSCRIPT', 'PRIMARY_ORIGINAL', 'en', 'AVAILABLE', ?)",
            (timestamp,),
        )
        connection.execute(
            "INSERT INTO intelligences (intelligence_id, current_revision_id, created_at) VALUES ('intelligence-1', NULL, ?)",
            (timestamp,),
        )
        connection.execute(
            "INSERT INTO intelligence_revisions (revision_id, intelligence_id, revision_number, prior_revision_id, interpretation_kind, content_hash, created_at, claim_kind) VALUES ('revision-1', 'intelligence-1', 1, NULL, 'DISTILLATION', ?, ?, 'FACT')",
            ("b" * 64, timestamp),
        )
        connection.execute("INSERT INTO intelligence_revision_evidence (revision_id, evidence_id) VALUES ('revision-1', 'evidence-1')")
        connection.execute(
            "INSERT INTO intelligence_state_history (state_event_id, intelligence_id, revision_id, state, prior_state, reason, evidence_id, created_at) VALUES ('state-1', 'intelligence-1', 'revision-1', 'NEW', NULL, 'seed', 'evidence-1', ?)",
            (timestamp,),
        )
        connection.execute("UPDATE intelligences SET current_revision_id = 'revision-1' WHERE intelligence_id = 'intelligence-1'")
        connection.execute(
            "INSERT INTO dependency_edges (edge_id, dependent_revision_id, relation, input_evidence_id, input_revision_id, created_at) VALUES ('support-1', 'revision-1', 'EVIDENCE_SUPPORT', 'evidence-1', NULL, ?)",
            (timestamp,),
        )
    finally:
        connection.close()
    v008 = all_migrations[:8]
    monkeypatch.setattr(legacy, "_load_migrations", lambda: v008)
    upgraded = legacy
    assert upgraded.initialize(now=NOW).version == 8
    assert upgraded.get_source_subscription("source-1") is not None
    assert len(upgraded.list_automation_schedules()) == 1
    assert upgraded.list_preferences() == ()
    assert upgraded.list_feedback() == ()
    with upgraded._connect() as connection:
        preserved = connection.execute(
            "SELECT claim_kind FROM intelligence_revisions WHERE revision_id = 'revision-1'"
        ).fetchone()
    assert preserved is not None
    assert preserved["claim_kind"] == "FACT"

    monkeypatch.undo()
    assert upgraded.initialize(now=NOW).version == 32
    assert (
        AuthoritativeIntelligenceReader(upgraded)
        .read_current("intelligence-1")
        .claim_kind.value
        == "FACT"
    )


def test_m008_failure_rolls_back_and_a_later_restart_applies_without_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.sqlite3"
    repository = SQLiteStateRepository(path)
    all_migrations = repository._load_migrations()
    v007 = all_migrations[:7]
    monkeypatch.setattr(repository, "_load_migrations", lambda: v007)
    assert repository.initialize(now=NOW).version == 7
    broken_sql = "CREATE TABLE task020_half_applied (value TEXT);\nTHIS IS NOT SQL;\n"
    broken = state_mod._Migration(
        version=8,
        name="008_add_preference_feedback.sql",
        sql=broken_sql,
        checksum="0" * 64,
    )
    monkeypatch.setattr(repository, "_load_migrations", lambda: (*v007, broken))
    with pytest.raises(state_mod.MigrationError, match="failed to apply migration 8"):
        repository.initialize(now=NOW)
    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 7
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'task020_half_applied'").fetchone() is None
    finally:
        connection.close()
    v008 = all_migrations[:8]
    monkeypatch.setattr(repository, "_load_migrations", lambda: v008)
    assert repository.initialize(now=NOW).version == 8
    assert repository.list_preferences() == ()
    assert repository.list_feedback() == ()


def test_replacement_command_cannot_silently_accept_a_different_payload(
    tmp_path: Path,
) -> None:
    service = _service(_repository(tmp_path))
    original = service.set_explicit_long_term(
        command_id="original",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Original explicit rule.",
    )
    replacement = service.replace_explicit_long_term(
        command_id="replace-once",
        preference_id=original.preference_id,
        statement="First replacement.",
    )
    assert (
        service.replace_explicit_long_term(
            command_id="replace-once",
            preference_id=original.preference_id,
            statement="First replacement.",
        )
        == replacement
    )

    with pytest.raises(IntegrityConflict, match="identity conflicts"):
        service.replace_explicit_long_term(
            command_id="replace-once",
            preference_id=original.preference_id,
            statement="Different replacement.",
        )


def test_repository_cannot_activate_an_unreviewed_direct_supersession(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    original = _service(repository).set_explicit_long_term(
        command_id="direct-original",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Explicit rule.",
    )

    with pytest.raises(IntegrityConflict, match="immutable"):
        repository.create_preference(
            PreferenceWrite(
                preference_id="forged-direct-replacement",
                horizon=PreferenceHorizon.LONG_TERM,
                provenance=PreferenceProvenance.EXPLICIT,
                scope=PreferenceScope.GLOBAL_CONTENT,
                target_id=None,
                statement="Forged replacement.",
                starts_at=None,
                expires_at=None,
                supersedes_preference_id=original.preference_id,
            ),
            activation_event_id="forged-direct-replacement:activated",
            now=NOW,
        )
    assert [item.preference_id for item in _service(repository).active_preferences(now=NOW)] == [
        original.preference_id
    ]


def test_source_scoped_feedback_cannot_mutate_source_policy_or_call_a_provider(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_service = ProductOrchestrationService(repository, now=lambda: NOW)
    source = source_service.add_source(
        url="https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    original = repository.get_source_subscription(source.source_id)
    assert original is not None

    _service(repository).record_feedback(
        FeedbackWrite(
            feedback_id="source-feedback",
            kind=FeedbackKind.LESS_LIKE_THIS,
            scope=PreferenceScope.SOURCE_CONTENT,
            target_id=source.source_id,
            content=None,
            correction_kind=None,
        )
    )

    assert repository.get_source_subscription(source.source_id) == original
    connection = repository._connect()
    try:
        assert connection.execute("SELECT COUNT(*) FROM provider_calls").fetchone()[0] == 0
    finally:
        connection.close()


def test_api_rejects_naive_or_expired_temporary_focus_timestamps(
    tmp_path: Path,
) -> None:
    app = _app(_repository(tmp_path))
    for expires_at in ("2026-09-08T09:00:00", "2026-09-07T09:00:00Z"):
        with pytest.raises(ApiError) as rejected:
            app.handle(
                "POST",
                "/api/v1/settings/preferences/temporary-focus",
                (
                    '{"command_id":"timestamp-' + expires_at + '",'
                    '"scope":"GLOBAL_CONTENT","statement":"focus",'
                    '"expires_at":"' + expires_at + '"}'
                ).encode(),
            )
        assert rejected.value.status == 422


def test_api_edits_only_explicit_long_term_and_deletes_by_finite_command(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    app = _app(repository)
    _, created = app.handle(
        "POST",
        "/api/v1/settings/preferences/long-term",
        b'{"command_id":"api-edit-original","scope":"GLOBAL_CONTENT","statement":"Original"}',
    )
    preference_id = created["preference"]["preference_id"]  # type: ignore[index]
    assert isinstance(preference_id, str)

    status, replacement = app.handle(
        "PATCH",
        f"/api/v1/settings/preferences/{preference_id}",
        b'{"command_id":"api-edit-replacement","statement":"Replacement"}',
    )
    replacement_id = replacement["preference"]["preference_id"]  # type: ignore[index]
    assert isinstance(replacement_id, str)
    deletion_status, deletion = app.handle(
        "DELETE",
        f"/api/v1/settings/preferences/{replacement_id}",
        b'{"command_id":"api-delete"}',
    )

    assert status == 200
    assert deletion_status == 200
    assert deletion["state"] == "DELETED"
    assert _service(repository).active_preferences(now=NOW) == ()


def test_api_surfaces_duplicate_feedback_conflict_without_a_server_error(
    tmp_path: Path,
) -> None:
    app = _app(_repository(tmp_path))
    body = b'{"feedback_id":"api-duplicate","kind":"IMPORTANT","scope":"GLOBAL_CONTENT"}'
    assert app.handle("POST", "/api/v1/settings/feedback", body)[0] == 201

    with pytest.raises(ApiError) as rejected:
        app.handle(
            "POST",
            "/api/v1/settings/feedback",
            b'{"feedback_id":"api-duplicate","kind":"NATURAL_LANGUAGE","scope":"GLOBAL_CONTENT","content":"Different"}',
        )
    assert rejected.value.status == 409
    assert rejected.value.code == "CONFLICT"


def test_database_rejects_raw_arbitrary_types_targets_and_derived_overwrite(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    explicit = _service(repository).set_explicit_long_term(
        command_id="raw-explicit",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Explicit rule remains authoritative.",
    )
    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO feedback_events (feedback_id, kind, scope, target_id, content, correction_kind, effect_status, created_at) VALUES ('raw-kind', 'ARBITRARY', 'GLOBAL_CONTENT', NULL, NULL, NULL, 'RECORDED', ?)",
                ("2026-09-07T09:00:00.000000Z",),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO preferences (preference_id, horizon, provenance, scope, target_id, statement, starts_at, expires_at, supersedes_preference_id, created_at) VALUES ('raw-horizon', 'ARBITRARY', 'DERIVED', 'GLOBAL_CONTENT', NULL, 'bad', NULL, NULL, NULL, ?)",
                ("2026-09-07T09:00:00.000000Z",),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO feedback_events (feedback_id, kind, scope, target_id, content, correction_kind, effect_status, created_at) VALUES ('raw-target', 'IMPORTANT', 'SOURCE_CONTENT', 'missing-source', NULL, NULL, 'RECORDED', ?)",
                ("2026-09-07T09:00:00.000000Z",),
            )
    finally:
        connection.close()
    with pytest.raises(IntegrityConflict, match="finite immutable"):
        repository.create_preference(
            PreferenceWrite(
                preference_id="derived-overwrite",
                horizon=PreferenceHorizon.RECENT,
                provenance=PreferenceProvenance.DERIVED,
                scope=PreferenceScope.GLOBAL_CONTENT,
                target_id=None,
                statement="Derived observation.",
                starts_at=None,
                expires_at=None,
                supersedes_preference_id=explicit.preference_id,
            ),
            activation_event_id="derived-overwrite:activated",
            now=NOW,
        )
    assert _service(repository).active_preferences(now=NOW) == (explicit,)
