"""TASK-025 immutable Weekly V1 snapshot contracts."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from importlib import resources
from pathlib import Path

import pytest

import youtube_intel.state as state_mod
from youtube_intel.brief import WeeklyBriefError, WeeklyBriefService
from youtube_intel.distillation import (
    BudgetDecision,
    DistillationCommand,
    DistillationTransportResult,
    PersonalizedDistillationService,
)
from youtube_intel.local_api import LocalApiApplication
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
    DependencyEdgeWrite,
    DependencyRelation,
    DistillationCardWrite,
    DistillationExecutionWrite,
    DistillationStyle,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    IntegrityConflict,
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
    PreferenceProvenance,
    PreferenceScope,
    SQLiteStateRepository,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VideoMetadata,
    WeeklyBriefMarkerKind,
    WeeklyBriefMarkerWrite,
    build_evidence_id,
)
from youtube_intel.topic import TopicApplicationService, TopicAssociationKind

WEEK_START = datetime(2026, 8, 31, tzinfo=UTC)
WEEK_END = WEEK_START + timedelta(days=7)
FINALIZED_AT = WEEK_END - timedelta(hours=1)


class _Budget:
    def check(self, command: DistillationCommand) -> BudgetDecision:
        return BudgetDecision(allowed=True, state="ADMITTED")


class _Transport:
    is_offline_test_transport = True
    actual_provider = "weekly-test-transport"
    actual_model = "deterministic-fixture"
    available = True

    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.calls = 0

    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        return DistillationTransportResult(
            raw=self.raw,
            actual_provider="weekly-test-transport",
            actual_model="deterministic-fixture",
            input_tokens=1,
            output_tokens=1,
            cost_microunits=1,
            duration_ms=1,
        )


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=WEEK_START).version == 16
    return repository


def _v012_migrations() -> tuple[state_mod._Migration, ...]:
    migrations: list[state_mod._Migration] = []
    names = (
        "001_initial.sql",
        "002_add_scoring_lineage.sql",
        "003_add_deep_analysis_persistence.sql",
        "004_add_provider_dispatch_state.sql",
        "005_add_product_orchestration.sql",
        "006_add_intelligence_domain.sql",
        "007_add_intelligence_claim_classification.sql",
        "008_add_preference_feedback.sql",
        "009_add_source_policy_filtering.sql",
        "010_add_personalized_distillation.sql",
        "011_add_topic_timeline.sql",
        "012_add_source_run_orchestration.sql",
    )
    for version, name in enumerate(names, start=1):
        sql = resources.files("youtube_intel").joinpath("migrations", name).read_bytes()
        migrations.append(
            state_mod._Migration(
                version=version,
                name=name,
                sql=sql.decode("utf-8"),
                checksum=sha256(sql).hexdigest(),
            )
        )
    return tuple(migrations)


def _source(repository: SQLiteStateRepository) -> str:
    source = ProductOrchestrationService(repository, now=lambda: WEEK_START).add_source(
        url="https://www.youtube.com/channel/UC______________________",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    SourcePolicyApplicationService(repository, now=lambda: WEEK_START).update_global(
        command_id="weekly-policy",
        initial_history_count=5,
        per_run_max_new_videos=5,
        focus_rules=("weekly",),
        ignore_rules=(),
        distillation_style=DistillationStyle.BALANCED,
    )
    return source.source_id


def _admit(
    repository: SQLiteStateRepository,
    *,
    source_id: str,
    video_id: str,
    at: datetime,
    conclusion: str,
    claim_kind: IntelligenceClaimKind = IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
    bind_exact_text: bool = True,
) -> tuple[str, str, str]:
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UC______________________",
            channel_name="Fixture channel",
            title=f"Weekly fixture {video_id}",
            description="weekly topic fixture",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=at,
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status="none",
            availability=Availability.PUBLIC,
        ),
        pipeline_version="weekly-fixture",
        now=at,
    )
    repository.link_source_video(source_id, video_id, discovered_at=at)
    SourcePolicyApplicationService(repository, now=lambda: at).evaluate_and_record_stage_one(
        source_id,
        MetadataFilterCandidate(
            video_id=video_id,
            title=f"Weekly fixture {video_id}",
            description="weekly topic fixture",
            channel_name="Fixture channel",
            published_at=at,
            video_type=VideoType.STANDARD,
        ),
    )
    artifact_id = f"artifact:{video_id}"
    connection = repository._connect()  # fixture setup only; production uses the reader.
    try:
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
            "VALUES (?, ?, ?, NULL, 'transcript_canonical', 'DATA', ?, ?, NULL, NULL, 'weekly-fixture', 'LONG_LIVED', ?, NULL, NULL)",
            (artifact_id, f"artifact-key:{video_id}", video_id, f"{video_id}.txt", "a" * 64, at.isoformat().replace("+00:00", "Z")),
        )
    finally:
        connection.close()
    evidence_id = build_evidence_id(
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=1_000,
        end_ms=1_500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    evidence = EvidenceWrite(
        evidence_id=evidence_id,
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=1_000,
        end_ms=1_500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en",
        availability=EvidenceAvailability.AVAILABLE,
    )
    if bind_exact_text:
        timed = TimedTranscriptWrite.from_cues(
            video_id=video_id,
            canonical_artifact_id=artifact_id,
            cues=(TimedTranscriptCueWrite(start_ms=1_000, end_ms=1_500, text="Fixture canonical evidence."),),
        )
        repository.create_timed_transcript(timed, now=at)
        repository.create_evidence_with_text_binding(
            evidence,
            EvidenceTextBindingWrite.from_timed_transcript(
                evidence=evidence,
                timed_transcript_id=timed.timed_transcript_id,
                start_cue_index=0,
                end_cue_index=1,
                excerpt="Fixture canonical evidence.",
            ),
            now=at,
        )
    else:
        repository.create_evidence(evidence, now=at)
    raw = json.dumps(
        {
            "core_conclusion": conclusion,
            "user_relevant_information": [conclusion],
            "important_new_information": [conclusion],
            "meaningful_details": [conclusion],
            "filtered_noise": [],
            "claim_kind": claim_kind.value,
            "evidence": [{"evidence_id": evidence_id, "start_ms": 1000, "end_ms": 1500}],
        },
        separators=(",", ":"),
    )
    if not bind_exact_text:
        execution_id = f"execution:{video_id}"
        repository.begin_distillation_execution(
            DistillationExecutionWrite(
                execution_id=execution_id,
                source_id=source_id,
                video_id=video_id,
                reason="WEEKLY_TEST_ADMISSION",
                use_case="PERSONALIZED_INTELLIGENCE",
                selected_provider="weekly-test-transport",
                selected_model="deterministic-fixture",
            ),
            now=at,
        )
        record = repository.admit_distillation(
            execution_id=execution_id,
            intelligence_id=f"intelligence:distillation:{execution_id}",
            revision_id=f"revision:distillation:{execution_id}",
            claim_kind=claim_kind,
            content_hash=sha256(
                json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            evidence_ids=(evidence_id,),
            card=DistillationCardWrite(
                source_id=source_id,
                video_id=video_id,
                core_conclusion=conclusion,
                user_relevant_information=(conclusion,),
                important_new_information=(conclusion,),
                meaningful_details=(conclusion,),
                filtered_noise=(),
                preference_ids=(),
                source_policy_revision_id=None,
            ),
            actual_provider="weekly-test-transport",
            actual_model="deterministic-fixture",
            input_tokens=1,
            output_tokens=1,
            cost_microunits=1,
            duration_ms=1,
            now=at,
        )
        return record.intelligence_id or "", record.revision_id or "", evidence_id
    transport = _Transport(raw)
    result = PersonalizedDistillationService(
        repository,
        SourcePolicyApplicationService(repository, now=lambda: at),
        transport,
        _Budget(),
        now=lambda: at,
    ).distill(
        DistillationCommand(
            execution_id=f"execution:{video_id}",
            source_id=source_id,
            video_id=video_id,
            evidence_ids=(evidence_id,),
            reason="WEEKLY_TEST_ADMISSION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="weekly-test-transport",
            selected_model="deterministic-fixture",
        )
    )
    assert transport.calls == 1
    assert result.intelligence_id is not None
    assert result.revision_id is not None
    return result.intelligence_id, result.revision_id, evidence_id


def _associate(
    repository: SQLiteStateRepository,
    *,
    topic_command: str,
    topic_name: str,
    intelligence_id: str,
    kind: TopicAssociationKind,
    at: datetime,
) -> str:
    service = TopicApplicationService(repository, now=lambda: at)
    topic = service.create_topic(command_id=topic_command, name=topic_name)
    return service.associate_intelligence(
        topic_id=topic.topic_id, intelligence_id=intelligence_id, kind=kind
    ).membership_id


def _append_card_backed_revision(
    repository: SQLiteStateRepository,
    *,
    intelligence_id: str,
    prior_revision_id: str,
    revision_id: str,
    claim_kind: IntelligenceClaimKind,
    state: IntelligenceState,
    evidence_id: str,
    at: datetime,
) -> None:
    """Create a valid later card revision without exercising a provider in this test."""

    prior = repository.get_intelligence_revision(prior_revision_id)
    assert prior is not None
    repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id=revision_id,
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=claim_kind,
            content_hash=prior.content_hash,
            state=state,
            reason="Fixture later trusted Intelligence state.",
            evidence_ids=(evidence_id,),
        ),
        now=at,
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id=f"support:{revision_id}",
            dependent_revision_id=revision_id,
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=evidence_id,
            input_revision_id=None,
        ),
        now=at,
    )
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO distillation_cards "
            "(revision_id, source_id, video_id, core_conclusion, user_relevant_information_json, "
            "important_new_information_json, meaningful_details_json, filtered_noise_json, "
            "preference_ids_json, source_policy_revision_id, created_at) "
            "SELECT ?, source_id, video_id, core_conclusion, user_relevant_information_json, "
            "important_new_information_json, meaningful_details_json, filtered_noise_json, "
            "preference_ids_json, source_policy_revision_id, ? "
            "FROM distillation_cards WHERE revision_id = ?",
            (revision_id, at.isoformat().replace("+00:00", "Z"), prior_revision_id),
        )
    finally:
        connection.close()


def _weekly(repository: SQLiteStateRepository, *, now: datetime = FINALIZED_AT) -> WeeklyBriefService:
    return WeeklyBriefService(repository, timezone="UTC", now=lambda: now)


def test_m013_upgrades_v012_preserves_prior_data_and_creates_no_synthetic_weekly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.sqlite3"
    legacy = SQLiteStateRepository(path)
    monkeypatch.setattr(legacy, "_load_migrations", _v012_migrations)
    assert legacy.initialize(now=WEEK_START).version == 12
    legacy.create_intelligence(intelligence_id="preserved-intelligence", now=WEEK_START)
    monkeypatch.undo()

    upgraded = SQLiteStateRepository(path)
    # TASK-025's migration-specific gate remains an exact v012 → v013 test.
    migrations = upgraded._load_migrations()
    monkeypatch.setattr(upgraded, "_load_migrations", lambda: migrations[:13])
    assert upgraded.initialize(now=WEEK_START).version == 13
    assert upgraded.get_intelligence("preserved-intelligence") is not None
    assert upgraded.list_weekly_v1_briefs() == ()
    connection = upgraded._connect()
    try:
        names = tuple(
            row["name"]
            for row in connection.execute("SELECT name FROM schema_migrations ORDER BY version")
        )
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 13
    finally:
        connection.close()
    assert names[-1] == "013_add_weekly_brief_foundation.sql"
    assert not any(name.startswith("014_") for name in names)


def test_weekly_v1_uses_explicit_utc_period_identity_and_exact_boundaries(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    included, _, _ = _admit(
        repository,
        source_id=source_id,
        video_id="included0001",
        at=WEEK_START,
        conclusion="Included at the start boundary.",
    )
    before, _, _ = _admit(
        repository,
        source_id=source_id,
        video_id="before000001",
        at=WEEK_START - timedelta(microseconds=1),
        conclusion="Outside before boundary.",
    )
    after, _, _ = _admit(
        repository,
        source_id=source_id,
        video_id="after0000001",
        at=WEEK_END,
        conclusion="Outside end boundary.",
    )
    _associate(repository, topic_command="included", topic_name="Included", intelligence_id=included, kind=TopicAssociationKind.NEW_INFORMATION, at=WEEK_START)
    _associate(repository, topic_command="before", topic_name="Before", intelligence_id=before, kind=TopicAssociationKind.NEW_INFORMATION, at=WEEK_START - timedelta(microseconds=1))
    _associate(repository, topic_command="after", topic_name="After", intelligence_id=after, kind=TopicAssociationKind.NEW_INFORMATION, at=WEEK_END)

    brief = _weekly(repository).finalize_week()

    assert brief.version == "weekly-v1"
    assert brief.timezone == "UTC"
    assert brief.period_start == WEEK_START
    assert brief.period_end == WEEK_END
    assert brief.logical_period_id == "weekly-v1:UTC:2026-08-31T00:00:00Z:2026-09-07T00:00:00Z"
    assert [item.intelligence_id for item in brief.items] == [included]


def test_weekly_only_admits_reader_verified_topic_memberships_and_deduplicates_repetition(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    first, _, _ = _admit(repository, source_id=source_id, video_id="first000001", at=WEEK_START + timedelta(hours=1), conclusion="Original information.")
    repeated, _, _ = _admit(repository, source_id=source_id, video_id="repeat00001", at=WEEK_START + timedelta(hours=2), conclusion="Repeated information.")
    evidence, _, _ = _admit(repository, source_id=source_id, video_id="evidence0001", at=WEEK_START + timedelta(hours=3), conclusion="New evidence.")
    raw_only, _, _ = _admit(repository, source_id=source_id, video_id="rawonly0001", at=WEEK_START + timedelta(hours=4), conclusion="Raw row must not enter without a Topic membership.")
    _associate(repository, topic_command="one-topic", topic_name="One Topic", intelligence_id=first, kind=TopicAssociationKind.NEW_INFORMATION, at=WEEK_START + timedelta(hours=1))
    _associate(repository, topic_command="one-topic", topic_name="One Topic", intelligence_id=repeated, kind=TopicAssociationKind.SUPPORTING_REPETITION, at=WEEK_START + timedelta(hours=2))
    _associate(repository, topic_command="one-topic", topic_name="One Topic", intelligence_id=evidence, kind=TopicAssociationKind.NEW_EVIDENCE, at=WEEK_START + timedelta(hours=3))

    brief = _weekly(repository).finalize_week()

    assert len(brief.items) == 1
    assert brief.items[0].intelligence_id == evidence
    assert brief.items[0].association_kind is TopicAssociationKind.NEW_EVIDENCE
    assert raw_only not in {item.intelligence_id for item in brief.items}
    stored = repository.list_weekly_v1_brief_items(brief.brief_id)[0]
    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="brief item requires a current trusted topic membership"):
            connection.execute(
                "INSERT INTO brief_items "
                "(brief_item_id, brief_id, membership_id, topic_id, topic_name, intelligence_id, "
                "revision_id, association_kind, claim_kind, source_state, summary, source_content_hash, position, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'caller supplied Weekly authority', ?, ?, ?)",
                (
                    "forged-brief-item",
                    brief.brief_id,
                    stored.membership_id,
                    stored.topic_id,
                    stored.topic_name,
                    stored.intelligence_id,
                    stored.revision_id,
                    stored.association_kind.value,
                    stored.claim_kind.value,
                    stored.source_state.value,
                    stored.source_content_hash,
                    2,
                    FINALIZED_AT.isoformat().replace("+00:00", "Z"),
                ),
            )
    finally:
        connection.close()


@pytest.mark.parametrize(
    "claim_kind",
    (
        IntelligenceClaimKind.OPINION,
        IntelligenceClaimKind.PREDICTION,
        IntelligenceClaimKind.RUMOR,
        IntelligenceClaimKind.SYSTEM_INFERENCE,
    ),
)
def test_weekly_preserves_non_fact_claim_kinds(tmp_path: Path, claim_kind: IntelligenceClaimKind) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    intelligence_id, _, _ = _admit(
        repository,
        source_id=source_id,
        video_id=f"claim{claim_kind.value[:6].lower()}1"[:11],
        at=WEEK_START + timedelta(hours=1),
        conclusion=f"{claim_kind.value} remains explicitly labelled.",
        claim_kind=claim_kind,
    )
    _associate(repository, topic_command="claim-kind", topic_name="Claim Kind", intelligence_id=intelligence_id, kind=TopicAssociationKind.NEW_INFORMATION, at=WEEK_START + timedelta(hours=1))

    brief = _weekly(repository).finalize_week()

    assert brief.items[0].claim_kind is claim_kind
    assert brief.items[0].summary == f"{claim_kind.value} remains explicitly labelled."


def test_weekly_preserves_disputed_rumor_as_unresolved_disagreement(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    intelligence_id, first_revision_id, evidence_id = _admit(
        repository,
        source_id=source_id,
        video_id="disputed001",
        at=WEEK_START + timedelta(hours=1),
        conclusion="The claim remains disputed.",
        claim_kind=IntelligenceClaimKind.RUMOR,
    )
    _append_card_backed_revision(
        repository,
        intelligence_id=intelligence_id,
        prior_revision_id=first_revision_id,
        revision_id=f"{intelligence_id}:disputed",
        claim_kind=IntelligenceClaimKind.RUMOR,
        state=IntelligenceState.DISPUTED,
        evidence_id=evidence_id,
        at=WEEK_START + timedelta(hours=2),
    )
    _associate(
        repository,
        topic_command="disputed",
        topic_name="Disputed Topic",
        intelligence_id=intelligence_id,
        kind=TopicAssociationKind.CONTRADICTORY_INFORMATION,
        at=WEEK_START + timedelta(hours=2),
    )

    item = _weekly(repository).finalize_week().items[0]

    assert item.claim_kind is IntelligenceClaimKind.RUMOR
    assert item.source_state == IntelligenceState.DISPUTED.value
    assert item.association_kind is TopicAssociationKind.CONTRADICTORY_INFORMATION


def test_weekly_is_idempotent_personalized_and_never_mutates_preference(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    security, _, _ = _admit(repository, source_id=source_id, video_id="security001", at=WEEK_START + timedelta(hours=1), conclusion="Security change.")
    product, _, _ = _admit(repository, source_id=source_id, video_id="product0001", at=WEEK_START + timedelta(hours=2), conclusion="Product change.")
    _associate(repository, topic_command="security", topic_name="Security", intelligence_id=security, kind=TopicAssociationKind.NEW_INFORMATION, at=WEEK_START + timedelta(hours=1))
    _associate(repository, topic_command="product", topic_name="Product", intelligence_id=product, kind=TopicAssociationKind.NEW_INFORMATION, at=WEEK_START + timedelta(hours=2))
    preferences = PreferenceApplicationService(repository, now=lambda: FINALIZED_AT)
    explicit = preferences.set_explicit_long_term(command_id="security-first", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="security")
    derived = preferences.record_derived_recent(command_id="derived", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="product")
    before = (repository.get_preference(explicit.preference_id), repository.get_preference(derived.preference_id))

    first = _weekly(repository).finalize_week()
    replay = _weekly(repository).finalize_week()

    assert first.brief_id == replay.brief_id
    assert [item.topic_name for item in first.items] == ["Security", "Product"]
    assert set(first.preference_ids) == {explicit.preference_id, derived.preference_id}
    assert repository.get_preference(explicit.preference_id) == before[0]
    assert repository.get_preference(derived.preference_id) == before[1]
    assert repository.get_preference(derived.preference_id).provenance is PreferenceProvenance.DERIVED


def test_empty_week_is_a_finalized_no_important_information_snapshot(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    brief = _weekly(repository).finalize_week()

    assert brief.status == "FINALIZED"
    assert brief.no_important_information is True
    assert brief.items == ()


def test_finalized_snapshot_is_immutable_after_topic_rename_and_revision(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    intelligence_id, revision_id, evidence_id = _admit(repository, source_id=source_id, video_id="history0001", at=WEEK_START + timedelta(hours=1), conclusion="Historical conclusion.")
    _associate(repository, topic_command="history", topic_name="Historical Topic", intelligence_id=intelligence_id, kind=TopicAssociationKind.NEW_INFORMATION, at=WEEK_START + timedelta(hours=1))
    brief = _weekly(repository).finalize_week()
    item = brief.items[0]
    TopicApplicationService(repository, now=lambda: WEEK_END + timedelta(days=1)).rename_topic(topic_id=item.topic_id, name="Tuesday Topic")
    new_revision = f"{intelligence_id}:correction"
    repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id=new_revision,
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash="b" * 64,
            state=IntelligenceState.UPDATED,
            reason="Later correction.",
            evidence_ids=(evidence_id,),
        ),
        now=WEEK_END + timedelta(days=1),
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(edge_id=f"support:{new_revision}", dependent_revision_id=new_revision, relation=DependencyRelation.EVIDENCE_SUPPORT, input_evidence_id=evidence_id, input_revision_id=None),
        now=WEEK_END + timedelta(days=1),
    )

    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="brief marker requires an affected legal source"):
            connection.execute(
                "INSERT INTO brief_item_markers "
                "(marker_id, brief_item_id, marker_kind, reason, current_revision_id, evidence_id, marked_at) "
                "VALUES (?, ?, 'SUPERSEDED', 'caller supplied history rewrite', ?, NULL, ?)",
                (
                    "forged-marker",
                    item.brief_item_id,
                    new_revision,
                    (WEEK_END + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                ),
            )
    finally:
        connection.close()

    marked = _weekly(repository, now=WEEK_END + timedelta(days=1)).append_correction_markers()
    reread = _weekly(repository).read(brief.brief_id)

    assert marked == 1
    assert reread.items[0].topic_name == "Historical Topic"
    assert reread.items[0].summary == "Historical conclusion."
    assert reread.items[0].revision_id == revision_id
    assert [marker.kind for marker in reread.items[0].markers] == ["SUPERSEDED"]
    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="brief items are immutable"):
            connection.execute(
                "UPDATE brief_items SET summary = 'forged overwrite' WHERE brief_item_id = ?",
                (item.brief_item_id,),
            )
    finally:
        connection.close()


def test_evidence_deletion_marks_history_without_deleting_it_or_accepting_forged_marker(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    intelligence_id, _, evidence_id = _admit(repository, source_id=source_id, video_id="delete00001", at=WEEK_START + timedelta(hours=1), conclusion="Deletable historical evidence.")
    _associate(repository, topic_command="delete", topic_name="Deletion", intelligence_id=intelligence_id, kind=TopicAssociationKind.NEW_INFORMATION, at=WEEK_START + timedelta(hours=1))
    brief = _weekly(repository).finalize_week()

    with pytest.raises(WeeklyBriefError):
        _weekly(repository).append_evidence_invalidation_markers(evidence_id)
    with pytest.raises(IntegrityConflict, match="weekly marker violates"):
        repository.append_weekly_v1_marker(
            WeeklyBriefMarkerWrite(
                marker_id="forged-available-evidence-marker",
                brief_item_id=brief.items[0].brief_item_id,
                kind=WeeklyBriefMarkerKind.EVIDENCE_DELETED,
                reason="Historical supporting evidence was later deleted.",
                current_revision_id=None,
                evidence_id=evidence_id,
            ),
            now=FINALIZED_AT,
        )
    replacement_evidence_id = build_evidence_id(
        video_id="delete00001",
        artifact_id="artifact:delete00001",
        start_ms=2_000,
        end_ms=2_500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    repository.create_evidence(
        EvidenceWrite(
            evidence_id=replacement_evidence_id,
            video_id="delete00001",
            artifact_id="artifact:delete00001",
            start_ms=2_000,
            end_ms=2_500,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
        ),
        now=WEEK_END + timedelta(days=1),
    )
    replacement_revision = f"{intelligence_id}:replacement"
    repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id=replacement_revision,
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash="c" * 64,
            state=IntelligenceState.UPDATED,
            reason="Replacement evidence supports the current interpretation.",
            evidence_ids=(replacement_evidence_id,),
        ),
        now=WEEK_END + timedelta(days=1),
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id=f"support:{replacement_revision}",
            dependent_revision_id=replacement_revision,
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=replacement_evidence_id,
            input_revision_id=None,
        ),
        now=WEEK_END + timedelta(days=1),
    )
    connection = repository._connect()  # Simulates a legal later deletion after upstream impact handling.
    try:
        connection.execute("UPDATE evidence SET availability = 'DELETED' WHERE evidence_id = ?", (evidence_id,))
    finally:
        connection.close()

    assert _weekly(repository).append_evidence_invalidation_markers(evidence_id) == 1
    reread = _weekly(repository).read(brief.brief_id)
    assert reread.items[0].summary == "Deletable historical evidence."
    assert [marker.kind for marker in reread.items[0].markers] == ["EVIDENCE_DELETED"]


def test_weekly_v1_read_projection_is_separate_from_generic_reports_and_weekly_v2(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: FINALIZED_AT),
        timezone="UTC",
        now=lambda: FINALIZED_AT,
    )

    status, v1 = app.handle("GET", "/api/v1/weekly/v1")
    generic_status, generic = app.handle("GET", "/api/v1/weekly")

    assert status == generic_status == 200
    assert v1 == {"weekly_v1": []}
    assert generic == {"weekly": []}
