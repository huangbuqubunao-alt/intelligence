"""TASK-022 evidence-bound personalized distillation and resource ledger contracts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.distillation import (
    BudgetDecision,
    DistillationCommand,
    DistillationExecutionStatus,
    DistillationTransportResult,
    PersonalizedDistillationService,
)
from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
    VerifiedIntelligenceRead,
)
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.preference_service import PreferenceApplicationService
from youtube_intel.source_policy import (
    MetadataFilterCandidate,
    SourcePolicyApplicationService,
    VideoType,
)
from youtube_intel.state import (
    Availability,
    DistillationCardWrite,
    DistillationExecutionWrite,
    DistillationStyle,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceStance,
    EvidenceWrite,
    FeedbackKind,
    FeedbackWrite,
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
    LiveStatus,
    PreferenceScope,
    SQLiteStateRepository,
    VideoMetadata,
    build_evidence_id,
)

NOW = datetime(2026, 9, 7, 9, 0, tzinfo=UTC)


class _FakeBudget:
    def __init__(self, allowed: bool, *, state: str = "ADMITTED") -> None:
        self._decision = BudgetDecision(allowed=allowed, state=state)
        self.calls = 0

    def check(self, command: DistillationCommand) -> BudgetDecision:
        self.calls += 1
        return self._decision


class _FakeTransport:
    is_offline_test_transport = True

    def __init__(
        self,
        raw: str,
        *,
        available: bool = True,
        actual_provider: str = "test-transport",
        actual_model: str = "deterministic-v1",
        input_tokens: int | None = 120,
        output_tokens: int | None = 45,
        cost_microunits: int | None = 7,
        duration_ms: int | None = 8,
    ) -> None:
        self.raw = raw
        self.available = available
        self.actual_provider = actual_provider
        self.actual_model = actual_model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost_microunits = cost_microunits
        self.duration_ms = duration_ms
        self.calls = 0
        self.commands: list[DistillationCommand] = []

    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        self.commands.append(command)
        return DistillationTransportResult(
            raw=self.raw,
            actual_provider=self.actual_provider,
            actual_model=self.actual_model,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cost_microunits=self.cost_microunits,
            duration_ms=self.duration_ms,
        )


class _RaisingTransport(_FakeTransport):
    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        self.commands.append(command)
        raise RuntimeError("transport outcome is unknown")


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=NOW).version == 17
    return repository


def _source_and_video(repository: SQLiteStateRepository) -> tuple[str, str]:
    source = ProductOrchestrationService(repository, now=lambda: NOW).add_source(
        url="https://www.youtube.com/channel/UC______________________",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    video_id = "video-022"
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UC______________________",
            channel_name="Fixture channel",
            title="AI Agent product update",
            description="Developer tools and product cases.",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=NOW,
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    repository.link_source_video(source.source_id, video_id, discovered_at=NOW)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    policy.update_global(
        command_id=f"eligible-{video_id}",
        initial_history_count=5,
        per_run_max_new_videos=5,
        focus_rules=("AI Agent",),
        ignore_rules=(),
        distillation_style=DistillationStyle.BALANCED,
    )
    policy.evaluate_and_record_stage_one(
        source.source_id,
        MetadataFilterCandidate(
            video_id=video_id,
            title="AI Agent product update",
            description="Developer tools and product cases.",
            channel_name="Fixture channel",
            published_at=NOW,
            video_type=VideoType.STANDARD,
        ),
    )
    return source.source_id, video_id


def _evidence(
    repository: SQLiteStateRepository,
    video_id: str,
    *,
    start_ms: int = 1_000,
    end_ms: int = 1_500,
    source_excerpt: str | None = None,
) -> str:
    timestamp = "2026-09-07T09:00:00Z"
    artifact_id = f"artifact-{video_id}"
    connection = repository._connect()
    try:
        existing = connection.execute(
            "SELECT artifact_id FROM artifacts WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        if existing is None:
            connection.execute(
                "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
                "VALUES (?, ?, ?, NULL, 'transcript_canonical', 'DATA', ?, ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
                (artifact_id, f"artifact-key-{video_id}", video_id, f"{video_id}.txt", "a" * 64, timestamp),
            )
    finally:
        connection.close()
    evidence_id = build_evidence_id(
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=start_ms,
        end_ms=end_ms,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    repository.create_evidence(
        EvidenceWrite(
            evidence_id=evidence_id,
            video_id=video_id,
            artifact_id=artifact_id,
            start_ms=start_ms,
            end_ms=end_ms,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
            source_excerpt=source_excerpt,
        ),
        now=NOW,
    )
    return evidence_id


def _raw(
    evidence_id: str,
    *,
    claim_kind: IntelligenceClaimKind = IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
    start_ms: int = 1_000,
    end_ms: int = 1_500,
    stance: str = "supporting",
) -> str:
    return json.dumps(
        {
            "core_conclusion": "The release adds evidence-bound execution records.",
            "user_relevant_information": ["It foregrounds product evidence."],
            "important_new_information": ["Execution identity is retained."],
            "meaningful_details": ["The transcript names the release boundary."],
            "filtered_noise": ["Sponsor segment omitted."],
            "claim_kind": claim_kind.value,
            "evidence": [
                {"evidence_id": evidence_id, "start_ms": start_ms, "end_ms": end_ms, "stance": stance}
            ],
        },
        separators=(",", ":"),
    )


def _service(
    repository: SQLiteStateRepository,
    transport: _FakeTransport,
    budget: _FakeBudget | None = None,
) -> PersonalizedDistillationService:
    return PersonalizedDistillationService(
        repository,
        SourcePolicyApplicationService(repository, now=lambda: NOW),
        transport,
        budget or _FakeBudget(True),
        now=lambda: NOW,
    )


def _command(source_id: str, video_id: str, evidence_id: str, *, execution_id: str = "exec-1") -> DistillationCommand:
    return DistillationCommand(
        execution_id=execution_id,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=(evidence_id,),
        reason="MANUAL_PERSONALIZED_DISTILLATION",
        use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider="test-transport",
        selected_model="deterministic-v1",
    )


def test_fresh_database_reaches_exactly_v017_with_evidence_relation_fields(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 17
        migrations = tuple(
            row["name"]
            for row in connection.execute("SELECT name FROM schema_migrations ORDER BY version")
        )
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        connection.close()

    assert migrations[-1] == "017_add_evidence_excerpt_stance.sql"
    assert "topics" in tables
    with repository._connect() as connection:
        evidence_columns = {
            row["name"] for row in connection.execute('PRAGMA table_info("evidence")')
        }
        relation_columns = {
            row["name"]
            for row in connection.execute(
                'PRAGMA table_info("intelligence_revision_evidence")'
            )
        }
    assert "source_excerpt" in evidence_columns
    assert "stance" in relation_columns


def test_v009_upgrade_preserves_existing_product_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "state.sqlite3"
    legacy = SQLiteStateRepository(path)
    migrations = legacy._load_migrations()
    monkeypatch.setattr(legacy, "_load_migrations", lambda: migrations[:9])
    assert legacy.initialize(now=NOW).version == 9
    source_id, _ = _source_and_video(legacy)
    preference = PreferenceApplicationService(legacy, now=lambda: NOW).set_explicit_long_term(
        command_id="preserved-preference",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Keep explicit user intent.",
    )
    legacy.create_intelligence(intelligence_id="preserved-intelligence", now=NOW)
    monkeypatch.undo()

    upgraded = SQLiteStateRepository(path)
    assert upgraded.initialize(now=NOW).version == 17
    assert upgraded.get_source_subscription(source_id) is not None
    assert upgraded.get_preference(preference.preference_id) == preference
    assert upgraded.get_intelligence("preserved-intelligence") is not None


def test_v016_legacy_null_stance_keeps_old_card_hash_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "legacy-v16.sqlite3"
    legacy = SQLiteStateRepository(path)
    migrations = legacy._load_migrations()
    monkeypatch.setattr(legacy, "_load_migrations", lambda: migrations[:16])
    assert legacy.initialize(now=NOW).version == 16
    source_id, video_id = _source_and_video(legacy)

    artifact_id = "legacy-artifact-v16"
    evidence_id = build_evidence_id(
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=1_000,
        end_ms=1_500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    with legacy._connect() as connection:
        connection.execute(
            "INSERT INTO artifacts "
            "(artifact_id, artifact_key, video_id, job_id, kind, storage_root, "
            "relative_path, content_hash, provider, model, producer_version, "
            "retention_class, created_at, expires_at, deleted_at) "
            "VALUES (?, ?, ?, NULL, 'transcript_canonical', 'DATA', ?, ?, "
            "NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            (
                artifact_id,
                "legacy-artifact-key-v16",
                video_id,
                "legacy-v16.txt",
                "a" * 64,
                "2026-09-07T09:00:00Z",
            ),
        )
        connection.execute(
            "INSERT INTO evidence "
            "(evidence_id, video_id, artifact_id, start_ms, end_ms, lineage_kind, "
            "role, language, availability, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'ORIGINAL_TRANSCRIPT', 'PRIMARY_ORIGINAL', "
            "'en', 'AVAILABLE', ?)",
            (
                evidence_id,
                video_id,
                artifact_id,
                1_000,
                1_500,
                "2026-09-07T09:00:00Z",
            ),
        )

    payload = {
        "core_conclusion": "Legacy card remains readable after M4C migration.",
        "user_relevant_information": ["Legacy authority is preserved."],
        "important_new_information": [],
        "meaningful_details": [],
        "filtered_noise": [],
        "claim_kind": IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT.value,
        "evidence": [
            {
                "evidence_id": evidence_id,
                "start_ms": 1_000,
                "end_ms": 1_500,
            }
        ],
    }
    content_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    legacy.create_intelligence(intelligence_id="legacy-intel-v16", now=NOW)
    legacy.append_intelligence_revision(
        intelligence_id="legacy-intel-v16",
        revision=IntelligenceRevisionWrite(
            revision_id="legacy-revision-v16",
            interpretation_kind=IntelligenceInterpretationKind.DISTILLATION,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash=content_hash,
            state=IntelligenceState.NEW,
            reason="LEGACY_DISTILLATION_ADMITTED",
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    with legacy._connect() as connection:
        connection.execute(
            "INSERT INTO dependency_edges "
            "(edge_id, dependent_revision_id, relation, input_evidence_id, "
            "input_revision_id, created_at) "
            "VALUES (?, ?, 'EVIDENCE_SUPPORT', ?, NULL, ?)",
            (
                "legacy-support-edge-v16",
                "legacy-revision-v16",
                evidence_id,
                "2026-09-07T09:00:00Z",
            ),
        )
        connection.execute(
            "INSERT INTO distillation_cards "
            "(revision_id, source_id, video_id, core_conclusion, "
            "user_relevant_information_json, important_new_information_json, "
            "meaningful_details_json, filtered_noise_json, preference_ids_json, "
            "source_policy_revision_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
            (
                "legacy-revision-v16",
                source_id,
                video_id,
                payload["core_conclusion"],
                json.dumps(payload["user_relevant_information"], separators=(",", ":")),
                json.dumps(payload["important_new_information"], separators=(",", ":")),
                json.dumps(payload["meaningful_details"], separators=(",", ":")),
                json.dumps(payload["filtered_noise"], separators=(",", ":")),
                "[]",
                "2026-09-07T09:00:00Z",
            ),
        )

    monkeypatch.undo()
    upgraded = SQLiteStateRepository(path)
    assert upgraded.initialize(now=NOW).version == 17

    relations = upgraded.list_intelligence_revision_evidence_relations(
        "legacy-revision-v16"
    )
    assert len(relations) == 1
    assert relations[0].stance is None
    assert upgraded.get_evidence(evidence_id).source_excerpt is None
    card = AuthoritativeIntelligenceReader(upgraded).read_current_card(
        "legacy-intel-v16"
    )
    assert card.core_conclusion == payload["core_conclusion"]


def test_generic_evidence_write_rejects_unverified_source_excerpt(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    _, video_id = _source_and_video(repository)

    with pytest.raises(ValueError, match="trusted capture path"):
        _evidence(
            repository,
            video_id,
            source_excerpt="Caller-provided text must not become source truth.",
        )

    assert repository.list_available_canonical_evidence_ids(video_id) == ()


def test_repository_admission_requires_supporting_evidence_independently(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id="direct-admit-no-support",
            source_id=source_id,
            video_id=video_id,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="test-transport",
            selected_model="deterministic-v1",
        ),
        now=NOW,
    )

    with pytest.raises(ValueError, match="at least one supporting Evidence"):
        repository.admit_distillation(
            execution_id="direct-admit-no-support",
            intelligence_id="intel-direct-no-support",
            revision_id="revision-direct-no-support",
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash="b" * 64,
            evidence_ids=(evidence_id,),
            evidence_stances=((evidence_id, EvidenceStance.CONTRADICTING),),
            card=DistillationCardWrite(
                source_id=source_id,
                video_id=video_id,
                core_conclusion="This must not be admitted without supporting Evidence.",
                user_relevant_information=("No supporting relation exists.",),
                important_new_information=(),
                meaningful_details=(),
                filtered_noise=(),
                preference_ids=(),
                source_policy_revision_id=None,
            ),
            actual_provider="test-transport",
            actual_model="deterministic-v1",
            input_tokens=1,
            output_tokens=1,
            cost_microunits=0,
            duration_ms=1,
            now=NOW,
        )

    assert repository.list_current_intelligence_ids() == ()


def test_m017_constraints_keep_excerpt_and_relation_immutable(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    first_evidence = _evidence(repository, video_id)
    second_evidence = _evidence(
        repository, video_id, start_ms=2_000, end_ms=2_500
    )
    result = _service(
        repository, _FakeTransport(_raw(first_evidence))
    ).distill(_command(source_id, video_id, first_evidence))
    card = AuthoritativeIntelligenceReader(repository).read_current_card(
        result.intelligence_id or ""
    )

    with repository._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="source excerpt is immutable"):
            connection.execute(
                "UPDATE evidence SET source_excerpt = ? WHERE evidence_id = ?",
                ("Unverified mutation", first_evidence),
            )
        with pytest.raises(sqlite3.IntegrityError, match="revision evidence links are immutable"):
            connection.execute(
                "UPDATE intelligence_revision_evidence SET stance = ? "
                "WHERE revision_id = ? AND evidence_id = ?",
                ("conditional", card.verified.revision_id, first_evidence),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO intelligence_revision_evidence "
                "(revision_id, evidence_id, stance) VALUES (?, ?, ?)",
                (card.verified.revision_id, second_evidence, "unknown"),
            )


def test_mixed_legacy_and_new_stance_fails_closed(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    first_evidence = _evidence(repository, video_id)
    second_evidence = _evidence(
        repository, video_id, start_ms=2_000, end_ms=2_500
    )
    raw = json.loads(_raw(first_evidence))
    raw["evidence"].append(
        {
            "evidence_id": second_evidence,
            "start_ms": 2_000,
            "end_ms": 2_500,
            "stance": "supporting",
        }
    )
    command = _command(source_id, video_id, first_evidence)
    command = DistillationCommand(
        execution_id=command.execution_id,
        source_id=command.source_id,
        video_id=command.video_id,
        evidence_ids=(first_evidence, second_evidence),
        reason=command.reason,
        use_case=command.use_case,
        selected_provider=command.selected_provider,
        selected_model=command.selected_model,
    )
    result = _service(repository, _FakeTransport(json.dumps(raw))).distill(command)
    revision_id = result.revision_id
    assert revision_id is not None

    with repository._connect() as connection:
        connection.execute("DROP TRIGGER revision_evidence_immutable_update")
        connection.execute(
            "UPDATE intelligence_revision_evidence SET stance = NULL "
            "WHERE revision_id = ? AND evidence_id = ?",
            (revision_id, second_evidence),
        )

    with pytest.raises(IntelligenceReadRejected, match="stance is incomplete"):
        AuthoritativeIntelligenceReader(repository).read_current_card(
            result.intelligence_id or ""
        )


def test_distillation_requires_at_least_one_supporting_evidence(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _FakeTransport(_raw(evidence_id, stance="contradicting"))

    result = _service(repository, transport).distill(
        _command(source_id, video_id, evidence_id)
    )

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert result.intelligence_id is None
    assert repository.list_current_intelligence_ids() == ()


def test_distillation_rejects_non_product_evidence_stance(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _FakeTransport(_raw(evidence_id, stance="unknown"))

    result = _service(repository, transport).distill(
        _command(source_id, video_id, evidence_id)
    )

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert result.intelligence_id is None
    assert repository.list_current_intelligence_ids() == ()


def test_personalization_projection_is_active_only_and_never_mutates_source_policy(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    preferences = PreferenceApplicationService(repository, now=lambda: NOW)
    long_term = preferences.set_explicit_long_term(
        command_id="long", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="Long term."
    )
    recent = preferences.record_derived_recent(
        command_id="recent", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="Recent."
    )
    temporary = preferences.set_temporary_focus(
        command_id="temporary", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="Temporary.", expires_at=NOW + timedelta(days=1)
    )
    PreferenceApplicationService(repository, now=lambda: NOW - timedelta(days=2)).set_temporary_focus(
        command_id="expired", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="Expired.", expires_at=NOW - timedelta(days=1)
    )
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    before = policy.effective_policy(source_id)
    transport = _FakeTransport(_raw(evidence_id))

    result = _service(repository, transport).distill(_command(source_id, video_id, evidence_id))

    assert result.status is DistillationExecutionStatus.SUCCEEDED
    assert transport.calls == 1
    assert transport.commands[0].preference_ids == (
        long_term.preference_id,
        recent.preference_id,
        temporary.preference_id,
    )
    assert tuple(item.statement for item in transport.commands[0].active_preferences) == (
        "Long term.",
        "Recent.",
        "Temporary.",
    )
    assert tuple(item.provenance for item in transport.commands[0].active_preferences) == (
        "EXPLICIT",
        "DERIVED",
        "TEMPORARY",
    )
    assert transport.commands[0].source_focus_rules == ("AI Agent",)
    assert transport.commands[0].source_ignore_rules == ()
    assert transport.commands[0].distillation_style == DistillationStyle.BALANCED.value
    assert transport.commands[0].source_policy_revision_id == before.source_policy_revision_id
    assert policy.effective_policy(source_id) == before
    card = AuthoritativeIntelligenceReader(repository).read_current_card(result.intelligence_id or "")
    assert card.core_conclusion.startswith("The release")
    relation = repository.list_intelligence_revision_evidence_relations(
        card.verified.revision_id
    )[0]
    assert relation.stance is not None
    assert relation.stance.value == "supporting"
    assert repository.get_evidence(evidence_id).source_excerpt is None
    assert card.verified.claim_kind is IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT
    assert card.verified.is_confirmed is False


def test_feedback_derived_preference_changes_a_later_distillation_request_only(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, first_video_id = _source_and_video(repository)
    first_evidence_id = _evidence(repository, first_video_id)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    before = policy.effective_policy(source_id)

    first_transport = _FakeTransport(_raw(first_evidence_id))
    assert _service(repository, first_transport).distill(
        _command(source_id, first_video_id, first_evidence_id, execution_id="feedback-run-a")
    ).status is DistillationExecutionStatus.SUCCEEDED
    assert first_transport.commands[0].active_preferences == ()

    preferences = PreferenceApplicationService(repository, now=lambda: NOW)
    feedback = preferences.record_feedback(
        FeedbackWrite(
            feedback_id="feedback-product-evidence",
            kind=FeedbackKind.IMPORTANT,
            scope=PreferenceScope.GLOBAL_CONTENT,
            target_id=None,
            content=None,
            correction_kind=None,
        )
    )
    derived = preferences.record_derived_recent(
        command_id="derive-product-evidence",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Emphasize evidence-led product execution detail.",
    )

    later_video_id = "video-022-feedback-later"
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=later_video_id,
            channel_id="UC______________________",
            channel_name="Fixture channel",
            title="AI Agent evidence update",
            description="Developer tools and product cases.",
            source_url=f"https://www.youtube.com/watch?v={later_video_id}",
            published_at=NOW + timedelta(minutes=1),
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    repository.link_source_video(source_id, later_video_id, discovered_at=NOW)
    policy.evaluate_and_record_stage_one(
        source_id,
        MetadataFilterCandidate(
            video_id=later_video_id,
            title="AI Agent evidence update",
            description="Developer tools and product cases.",
            channel_name="Fixture channel",
            published_at=NOW + timedelta(minutes=1),
            video_type=VideoType.STANDARD,
        ),
    )
    later_evidence_id = _evidence(repository, later_video_id)
    later_transport = _FakeTransport(_raw(later_evidence_id))

    assert _service(repository, later_transport).distill(
        _command(source_id, later_video_id, later_evidence_id, execution_id="feedback-run-b")
    ).status is DistillationExecutionStatus.SUCCEEDED
    assert repository.list_feedback() == (feedback,)
    assert later_transport.commands[0].preference_ids == (derived.preference_id,)
    assert tuple(item.statement for item in later_transport.commands[0].active_preferences) == (
        "Emphasize evidence-led product execution detail.",
    )
    assert policy.effective_policy(source_id) == before


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
def test_valid_finite_claim_kinds_are_preserved_without_lifecycle_inference(
    tmp_path: Path, claim_kind: IntelligenceClaimKind
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)

    result = _service(repository, _FakeTransport(_raw(evidence_id, claim_kind=claim_kind))).distill(
        _command(source_id, video_id, evidence_id, execution_id=f"exec-{claim_kind.value}")
    )

    verified = AuthoritativeIntelligenceReader(repository).read_current(result.intelligence_id or "")
    assert verified.claim_kind is claim_kind
    assert verified.is_confirmed is False


@pytest.mark.parametrize(
    "raw",
    (
        "{not-json",
        json.dumps({"core_conclusion": "partial"}),
        json.dumps(
            {
                "core_conclusion": "x",
                "user_relevant_information": [],
                "important_new_information": [],
                "meaningful_details": [],
                "filtered_noise": [],
                "claim_kind": "UNCLASSIFIED",
                "evidence": [],
            }
        ),
    ),
)
def test_malformed_or_unclassified_output_fails_closed_without_repair_or_retry(tmp_path: Path, raw: str) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _FakeTransport(raw)

    result = _service(repository, transport).distill(_command(source_id, video_id, evidence_id))

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert transport.calls == 1
    assert result.intelligence_id is None
    assert repository.list_distillation_cards() == ()


@pytest.mark.parametrize(
    "raw",
    (
        "```json\n{}\n```",
        json.dumps(
            {
                **json.loads(_raw("evidence-id")),
                "generated_text_as_evidence": "the model said so",
            }
        ),
    ),
)
def test_fenced_or_generated_text_evidence_is_not_repaired_or_admitted(
    tmp_path: Path, raw: str
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    if "generated_text_as_evidence" in raw:
        raw = raw.replace("evidence-id", evidence_id)
    transport = _FakeTransport(raw)

    result = _service(repository, transport).distill(_command(source_id, video_id, evidence_id))

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert transport.calls == 1
    assert repository.list_distillation_cards() == ()


def test_missing_or_foreign_requested_evidence_is_rejected_before_transport(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    raw_without_evidence = json.loads(_raw(evidence_id))
    raw_without_evidence["evidence"] = []
    missing_support = _FakeTransport(json.dumps(raw_without_evidence))
    result = _service(repository, missing_support).distill(
        _command(source_id, video_id, evidence_id)
    )
    foreign_requested = _FakeTransport(_raw(evidence_id))

    foreign_result = _service(repository, foreign_requested).distill(
        _command(source_id, video_id, "not-an-evidence", execution_id="foreign-request")
    )

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert missing_support.calls == 1
    assert foreign_result.status is DistillationExecutionStatus.REJECTED_EVIDENCE
    assert foreign_requested.calls == 0


def test_unbounded_evidence_request_is_rejected_before_transport(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_ids = tuple(
        _evidence(
            repository,
            video_id,
            start_ms=1_000 + index * 1_000,
            end_ms=1_500 + index * 1_000,
        )
        for index in range(21)
    )
    transport = _FakeTransport("{}")
    command = _command(source_id, video_id, evidence_ids[0])
    command = DistillationCommand(
        execution_id=command.execution_id,
        source_id=command.source_id,
        video_id=command.video_id,
        evidence_ids=evidence_ids,
        reason=command.reason,
        use_case=command.use_case,
        selected_provider=command.selected_provider,
        selected_model=command.selected_model,
    )

    result = _service(repository, transport).distill(command)

    assert result.status is DistillationExecutionStatus.REJECTED_EVIDENCE
    assert transport.calls == 0


def test_foreign_or_hallucinated_evidence_is_rejected_and_cannot_be_admitted(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    other_video = "foreign-022"
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=other_video,
            channel_id="UC_OTHER", channel_name="Other", title="Other", description="Other",
            source_url=f"https://www.youtube.com/watch?v={other_video}", published_at=NOW,
            duration_seconds=60, default_language="en", available_languages=("en",),
            live_status=LiveStatus.NONE, availability=Availability.PUBLIC,
        ), pipeline_version="fixture-v1", now=NOW,
    )
    foreign_evidence = _evidence(repository, other_video)

    foreign = _service(repository, _FakeTransport(_raw(foreign_evidence))).distill(
        _command(source_id, video_id, evidence_id)
    )
    hallucinated = _service(repository, _FakeTransport(_raw(evidence_id, end_ms=1_499))).distill(
        _command(source_id, video_id, evidence_id, execution_id="exec-timestamp")
    )

    assert foreign.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert hallucinated.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert repository.list_distillation_cards() == ()


def test_multiple_evidence_stances_are_canonicalized_and_supporting_anchors_state(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_ids = (
        _evidence(repository, video_id),
        _evidence(repository, video_id, start_ms=2_000, end_ms=2_500),
        _evidence(repository, video_id, start_ms=3_000, end_ms=3_500),
    )
    ordered = tuple(sorted(evidence_ids))
    stance_by_id = {
        ordered[0]: "contradicting",
        ordered[1]: "conditional",
        ordered[2]: "supporting",
    }
    raw = json.loads(_raw(ordered[2]))
    raw["evidence"] = [
        {
            "evidence_id": evidence_id,
            "start_ms": repository.get_evidence(evidence_id).start_ms,
            "end_ms": repository.get_evidence(evidence_id).end_ms,
            "stance": stance_by_id[evidence_id],
        }
        for evidence_id in reversed(ordered)
    ]
    command = _command(source_id, video_id, ordered[0])
    command = DistillationCommand(
        execution_id=command.execution_id,
        source_id=command.source_id,
        video_id=command.video_id,
        evidence_ids=evidence_ids,
        reason=command.reason,
        use_case=command.use_case,
        selected_provider=command.selected_provider,
        selected_model=command.selected_model,
    )

    result = _service(repository, _FakeTransport(json.dumps(raw))).distill(command)
    card = AuthoritativeIntelligenceReader(repository).read_current_card(
        result.intelligence_id or ""
    )

    assert result.status is DistillationExecutionStatus.SUCCEEDED
    assert card.verified.evidence_ids == ordered
    relations = repository.list_intelligence_revision_evidence_relations(
        card.verified.revision_id
    )
    assert {item.evidence_id: item.stance.value for item in relations if item.stance} == stance_by_id
    history = repository.list_intelligence_state_history(card.verified.intelligence_id)
    state_event = next(
        item for item in history if item.revision_id == card.verified.revision_id
    )
    assert state_event.evidence_id == ordered[2]
    dependency_edges = repository.list_dependency_edges_for_revision(
        card.verified.revision_id
    )
    assert {
        edge.input_evidence_id
        for edge in dependency_edges
        if edge.relation.value == "EVIDENCE_SUPPORT"
    } == set(ordered)


def test_normal_skip_is_not_eligible_and_manual_override_still_cannot_bypass_budget(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    policy.update_global(
        command_id="skip", initial_history_count=5, per_run_max_new_videos=5,
        focus_rules=(), ignore_rules=("advertisement",), distillation_style=policy.global_policy().distillation_style,
    )
    policy.evaluate_and_record_stage_one(
        source_id,
        MetadataFilterCandidate(video_id=video_id, title="Advertisement", description="", channel_name="Fixture channel", published_at=NOW, video_type=VideoType.STANDARD),
    )
    transport = _FakeTransport(_raw(evidence_id))

    skipped = _service(repository, transport).distill(_command(source_id, video_id, evidence_id))
    policy_before_override = policy.effective_policy(source_id)
    policy.manual_analyze_override(source_id=source_id, video_id=video_id, command_id="manual")
    same_execution = _service(repository, transport).distill(
        _command(source_id, video_id, evidence_id)
    )
    budget_blocked = _service(repository, transport, _FakeBudget(False, state="EXHAUSTED")).distill(
        _command(source_id, video_id, evidence_id, execution_id="exec-manual")
    )

    assert skipped.status is DistillationExecutionStatus.REJECTED_INELIGIBLE
    assert same_execution == skipped
    assert budget_blocked.status is DistillationExecutionStatus.WAITING_BUDGET
    assert transport.calls == 0
    assert budget_blocked.invocation_count == 0
    assert policy.effective_policy(source_id) == policy_before_override


def test_model_wait_unknown_usage_and_completed_reuse_are_truthful(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    unavailable = _FakeTransport(_raw(evidence_id), available=False)
    waiting = _service(repository, unavailable).distill(_command(source_id, video_id, evidence_id))
    transport = _FakeTransport(
        _raw(evidence_id), input_tokens=None, output_tokens=None, cost_microunits=None, duration_ms=None
    )
    service = _service(repository, transport)
    first = service.distill(_command(source_id, video_id, evidence_id, execution_id="exec-complete"))
    second = service.distill(_command(source_id, video_id, evidence_id, execution_id="exec-complete"))

    assert waiting.status is DistillationExecutionStatus.WAITING_MODEL
    assert unavailable.calls == 0
    assert first.status is DistillationExecutionStatus.SUCCEEDED
    assert second == first
    assert transport.calls == 1
    ledger = repository.get_distillation_resource_usage("exec-complete")
    assert ledger.actual_provider == "test-transport"
    assert ledger.actual_model == "deterministic-v1"
    assert ledger.input_tokens is None and ledger.output_tokens is None and ledger.cost_microunits is None


def test_actual_model_mismatch_is_recorded_without_fallback_or_admission(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _FakeTransport(_raw(evidence_id), actual_model="test-model-b")
    command = _command(source_id, video_id, evidence_id)

    result = _service(repository, transport).distill(command)

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert transport.calls == 1
    ledger = repository.get_distillation_resource_usage(command.execution_id)
    assert ledger.selected_model == "deterministic-v1"
    assert ledger.actual_model == "test-model-b"
    assert ledger.input_tokens == 120 and ledger.output_tokens == 45
    assert ledger.cost_microunits == 7 and ledger.duration_ms == 8


def test_service_rejects_non_offline_transport_before_any_execution(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    transport = _FakeTransport("{}")
    transport.is_offline_test_transport = False

    with pytest.raises(ValueError, match="offline deterministic"):
        _service(repository, transport)
    assert transport.calls == 0


def test_ambiguous_transport_outcome_is_not_automatically_retried(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _RaisingTransport(_raw(evidence_id))
    service = _service(repository, transport)
    command = _command(source_id, video_id, evidence_id)

    first = service.distill(command)
    second = service.distill(command)

    assert first.status is DistillationExecutionStatus.AMBIGUOUS
    assert second == first
    assert transport.calls == 1
    assert repository.get_distillation_resource_usage(command.execution_id).outcome == "TRANSPORT_OUTCOME_UNKNOWN"


def test_raw_candidate_never_mints_verified_read_and_ledger_has_no_credential_fields(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    result = _service(repository, _FakeTransport(_raw(evidence_id))).distill(
        _command(source_id, video_id, evidence_id)
    )

    with pytest.raises(TypeError):
        VerifiedIntelligenceRead(  # type: ignore[call-arg]
            intelligence_id=result.intelligence_id,
            revision_id="forged",
            claim_kind=IntelligenceClaimKind.FACT,
            state="CONFIRMED",
            evidence_ids=(),
        )
    with pytest.raises(IntelligenceReadRejected):
        AuthoritativeIntelligenceReader(repository).read_current("missing")
    connection = repository._connect()
    try:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(distillation_resource_usage)")
        }
    finally:
        connection.close()
    assert not {"credential", "secret", "api_key", "prompt"} & columns


def test_loopback_manual_admission_accepts_no_raw_model_fields_and_reads_card_through_authority(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        distillation_service=_service(repository, _FakeTransport(_raw(evidence_id))),
        now=lambda: NOW,
    )

    status, payload = app.handle(
        "POST",
        f"/api/v1/sources/{source_id}/videos/{video_id}/distill",
        json.dumps(
            {
                "execution_id": "api-exec",
                "evidence_ids": [evidence_id],
            }
        ).encode(),
    )

    assert status == 201
    assert payload["execution"]["status"] == "SUCCEEDED"
    intelligence_id = payload["execution"]["intelligence_id"]
    read_status, read_payload = app.handle("GET", f"/api/v1/intelligence/{intelligence_id}")
    assert read_status == 200
    assert read_payload["intelligence"]["trusted"] is True
    assert read_payload["intelligence"]["card"]["core_conclusion"].startswith("The release")
    assert read_payload["intelligence"]["card"]["original_video_url"].endswith(video_id)
    assert read_payload["intelligence"]["card"]["evidence_links"] == [
        {
            "evidence_id": evidence_id,
            "artifact_id": f"artifact-{video_id}",
            "start_ms": 1_000,
            "end_ms": 1_500,
            "language": "en",
            "lineage_kind": "ORIGINAL_TRANSCRIPT",
            "role": "PRIMARY_ORIGINAL",
            "original_excerpt": None,
            "translated_excerpt": None,
            "translated_language": None,
            "stance": "supporting",
        }
    ]
    with pytest.raises(ApiError):
        app.handle(
            "POST",
            f"/api/v1/sources/{source_id}/videos/{video_id}/distill",
            json.dumps({"execution_id": "bad", "evidence_ids": [evidence_id], "provider": "real"}).encode(),
        )


def test_loopback_distillation_fails_closed_when_no_offline_transport_is_configured(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        now=lambda: NOW,
    )

    with pytest.raises(ApiError) as error:
        app.handle(
            "POST",
            f"/api/v1/sources/{source_id}/videos/{video_id}/distill",
            json.dumps({"execution_id": "unavailable", "evidence_ids": [evidence_id]}).encode(),
        )

    assert error.value.code == "DISTILLATION_UNAVAILABLE"
