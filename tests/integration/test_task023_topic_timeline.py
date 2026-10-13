"""TASK-023 Topic and Timeline Foundation contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import pytest

import youtube_intel.state as state_mod
from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
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
    SQLiteStateRepository,
    TopicMembershipWrite,
    TopicTimelineEventKind,
    TopicTimelineEventWrite,
    build_evidence_id,
)
from youtube_intel.topic import (
    TopicApplicationService,
    TopicAssociationKind,
    TopicCurrentState,
    TopicRelationKind,
)

NOW = datetime(2026, 9, 7, 9, 0, tzinfo=UTC)


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=NOW).version == 38
    return repository


def _v010_migrations() -> tuple[state_mod._Migration, ...]:
    migrations: list[state_mod._Migration] = []
    for version, name in enumerate(
        (
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
        ),
        start=1,
    ):
        sql_bytes = resources.files("youtube_intel").joinpath("migrations", name).read_bytes()
        migrations.append(
            state_mod._Migration(
                version=version,
                name=name,
                sql=sql_bytes.decode("utf-8"),
                checksum=state_mod.hashlib.sha256(sql_bytes).hexdigest(),
            )
        )
    return tuple(migrations)


def _insert_video_and_artifact(repository: SQLiteStateRepository, video_id: str) -> str:
    timestamp = "2026-09-07T09:00:00Z"
    artifact_id = f"artifact-{video_id}"
    connection = repository._connect()  # test fixture setup, never a product read path.
    try:
        connection.execute(
            "INSERT INTO videos (video_id, channel_id, pipeline_status, pipeline_version, availability, discovered_at, updated_at) "
            "VALUES (?, 'UC_TEST', 'DISCOVERED', 'fixture-v1', 'public', ?, ?)",
            (video_id, timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
            "VALUES (?, ?, ?, NULL, 'transcript_canonical', 'DATA', ?, ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            (artifact_id, f"artifact-key-{video_id}", video_id, f"{video_id}.txt", "a" * 64, timestamp),
        )
    finally:
        connection.close()
    return artifact_id


def _evidence(
    repository: SQLiteStateRepository,
    video_id: str,
    *,
    role: EvidenceRole = EvidenceRole.PRIMARY_ORIGINAL,
) -> str:
    artifact_id = _insert_video_and_artifact(repository, video_id)
    evidence_id = build_evidence_id(
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=1_000,
        end_ms=1_500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=role,
    )
    repository.create_evidence(
        EvidenceWrite(
            evidence_id=evidence_id,
            video_id=video_id,
            artifact_id=artifact_id,
            start_ms=1_000,
            end_ms=1_500,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=role,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
        ),
        now=NOW,
    )
    return evidence_id


def _admit(
    repository: SQLiteStateRepository,
    intelligence_id: str,
    evidence_id: str,
    *,
    claim_kind: IntelligenceClaimKind = IntelligenceClaimKind.FACT,
    state: IntelligenceState = IntelligenceState.CONFIRMED,
    content_hash: str = "b" * 64,
) -> str:
    repository.create_intelligence(intelligence_id=intelligence_id, now=NOW)
    first_revision = f"{intelligence_id}:r1"
    repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id=first_revision,
            interpretation_kind=IntelligenceInterpretationKind.DISTILLATION,
            claim_kind=claim_kind,
            content_hash=content_hash,
            state=IntelligenceState.NEW,
            reason="initial evidence-bound interpretation",
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id=f"support:{first_revision}",
            dependent_revision_id=first_revision,
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=evidence_id,
            input_revision_id=None,
        ),
        now=NOW,
    )
    if state is IntelligenceState.NEW:
        return first_revision
    revision_id = f"{intelligence_id}:r2"
    repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id=revision_id,
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=claim_kind,
            content_hash=content_hash,
            state=state,
            reason="current evidence-bound interpretation",
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id=f"support:{revision_id}",
            dependent_revision_id=revision_id,
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=evidence_id,
            input_revision_id=None,
        ),
        now=NOW,
    )
    return revision_id


def _topic_service(repository: SQLiteStateRepository) -> TopicApplicationService:
    return TopicApplicationService(repository, now=lambda: NOW)


def test_topic_contract_remains_available_with_m013_weekly_foundation(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 38
        migrations = tuple(
            row["name"]
            for row in connection.execute("SELECT name FROM schema_migrations ORDER BY version")
        )
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    finally:
        connection.close()

    assert migrations[-23:] == (
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
        "025_add_explicit_cloud_execution_audit.sql",
        "026_add_openai_cloud_execution_audit.sql",
        "027_add_moonshot_cloud_execution_audit.sql",
        "028_add_cloud_response_failure_ledger.sql",
        "030_add_deep_analysis_durable_evidence.sql",
        "031_add_research_lite.sql",
        "032_add_source_provider_authority.sql",
        "033_add_bilibili_provider.sql",
        "034_add_source_tracking.sql",
        "035_align_no_new_canonical_evidence.sql",
        "036_expand_local_media_snapshot_limit.sql",
        "037_add_waiting_model_cancellation.sql",
        "038_add_retained_subtitle_derivations.sql",
    )
    assert {"topics", "topic_memberships", "topic_timeline_events", "topic_relations"} <= tables


def test_v010_upgrade_preserves_data_and_creates_no_synthetic_topic_truth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.sqlite3"
    legacy = SQLiteStateRepository(path)
    monkeypatch.setattr(legacy, "_load_migrations", _v010_migrations)
    assert legacy.initialize(now=NOW).version == 10
    legacy.create_intelligence(intelligence_id="preserved-intelligence", now=NOW)
    monkeypatch.undo()

    upgraded = SQLiteStateRepository(path)
    assert upgraded.initialize(now=NOW).version == 38
    assert upgraded.get_intelligence("preserved-intelligence").intelligence_id == "preserved-intelligence"
    assert upgraded.list_topics() == ()


def test_topic_identity_rename_and_pin_are_stable_and_separate_from_truth(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    service = _topic_service(repository)

    topic = service.create_topic(command_id="topic-command", name="Claude Code")
    renamed = service.rename_topic(topic_id=topic.topic_id, name="Claude Code tools")
    pinned = service.set_pinned(topic_id=topic.topic_id, pinned=True)
    replay = service.create_topic(command_id="topic-command", name="Claude Code")

    assert topic.topic_id == "topic:topic-command"
    assert renamed.topic_id == topic.topic_id == pinned.topic_id
    assert pinned.pinned is True
    assert replay.topic_id == topic.topic_id
    assert replay.name == "Claude Code tools"
    read = service.read_topic(topic.topic_id)
    assert read.current_state is TopicCurrentState.UNRESOLVED
    assert read.contributions == ()


def test_association_uses_reader_minted_current_revision_and_preserves_semantics(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, "video-opinion")
    revision_id = _admit(
        repository,
        "intelligence-opinion",
        evidence_id,
        claim_kind=IntelligenceClaimKind.OPINION,
        state=IntelligenceState.DISPUTED,
    )
    service = _topic_service(repository)
    topic = service.create_topic(command_id="opinion-topic", name="Tool direction")

    association = service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-opinion",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    read = service.read_topic(topic.topic_id)

    assert association.revision_id == revision_id
    assert association.evidence_ids == (evidence_id,)
    assert read.contributions[0].claim_kind is IntelligenceClaimKind.OPINION
    assert read.contributions[0].state is IntelligenceState.DISPUTED
    assert read.current_state is TopicCurrentState.UNRESOLVED
    assert read.timeline[0].dependency_revision_ids == (revision_id,)
    assert read.timeline[0].dependency_evidence_ids == (evidence_id,)


@pytest.mark.parametrize(
    "claim_kind",
    (
        IntelligenceClaimKind.PREDICTION,
        IntelligenceClaimKind.RUMOR,
        IntelligenceClaimKind.SYSTEM_INFERENCE,
    ),
)
def test_topic_never_upgrades_claim_kind_or_lifecycle(
    tmp_path: Path, claim_kind: IntelligenceClaimKind
) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, f"video-{claim_kind.value.lower()}")
    _admit(
        repository,
        f"intelligence-{claim_kind.value.lower()}",
        evidence_id,
        claim_kind=claim_kind,
        state=IntelligenceState.DISPUTED,
    )
    service = _topic_service(repository)
    topic = service.create_topic(command_id=f"topic-{claim_kind.value}", name="Unresolved")

    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id=f"intelligence-{claim_kind.value.lower()}",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )

    contribution = service.read_topic(topic.topic_id).contributions[0]
    assert contribution.claim_kind is claim_kind
    assert contribution.state is IntelligenceState.DISPUTED


def test_duplicate_and_repetition_membership_are_idempotent_without_endless_timeline(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    first_evidence = _evidence(repository, "video-first")
    repeat_evidence = _evidence(repository, "video-repeat")
    _admit(repository, "intelligence-first", first_evidence, content_hash="c" * 64)
    _admit(repository, "intelligence-repeat", repeat_evidence, content_hash="c" * 64)
    service = _topic_service(repository)
    topic = service.create_topic(command_id="dedupe", name="Release")

    first = service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-first",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    replay = service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-first",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    repetition = service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-repeat",
        kind=TopicAssociationKind.SUPPORTING_REPETITION,
    )
    read = service.read_topic(topic.topic_id)

    assert replay.membership_id == first.membership_id
    assert repetition.membership_id != first.membership_id
    assert len(read.contributions) == 2
    assert len(read.timeline) == 1
    assert read.timeline[0].event_kind.value == "NEW_INFORMATION"
    assert AuthoritativeIntelligenceReader(repository).read_current("intelligence-repeat").revision_id == repetition.revision_id


def test_new_evidence_can_form_bounded_consensus_but_source_count_cannot(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    primary_evidence = _evidence(repository, "video-primary")
    independent_evidence = _evidence(
        repository, "video-independent", role=EvidenceRole.INDEPENDENT_VERIFICATION
    )
    repeat_evidence = _evidence(repository, "video-relay", role=EvidenceRole.SECONDARY_RELAY)
    _admit(repository, "intelligence-primary", primary_evidence)
    _admit(repository, "intelligence-independent", independent_evidence)
    _admit(repository, "intelligence-relay", repeat_evidence)
    service = _topic_service(repository)
    topic = service.create_topic(command_id="consensus", name="Evidence state")

    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-primary",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    unresolved = service.read_topic(topic.topic_id)
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-relay",
        kind=TopicAssociationKind.SUPPORTING_REPETITION,
    )
    still_unresolved = service.read_topic(topic.topic_id)
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-independent",
        kind=TopicAssociationKind.NEW_EVIDENCE,
    )
    consensus = service.read_topic(topic.topic_id)

    assert unresolved.current_state is TopicCurrentState.UNRESOLVED
    assert still_unresolved.current_state is TopicCurrentState.UNRESOLVED
    assert consensus.current_state is TopicCurrentState.CONSENSUS
    assert consensus.independence == "KNOWN_INDEPENDENT"
    assert len(consensus.timeline) == 2


def test_contradiction_is_preserved_as_disagreement_not_overwritten(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    first_evidence = _evidence(repository, "video-fact")
    conflict_evidence = _evidence(repository, "video-rumor")
    _admit(repository, "intelligence-fact", first_evidence)
    _admit(
        repository,
        "intelligence-rumor",
        conflict_evidence,
        claim_kind=IntelligenceClaimKind.RUMOR,
        state=IntelligenceState.DISPUTED,
    )
    service = _topic_service(repository)
    topic = service.create_topic(command_id="conflict", name="Product change")

    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-fact",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-rumor",
        kind=TopicAssociationKind.CONTRADICTORY_INFORMATION,
    )
    read = service.read_topic(topic.topic_id)

    assert read.current_state is TopicCurrentState.DISAGREEMENT
    assert {item.claim_kind for item in read.contributions} == {
        IntelligenceClaimKind.FACT,
        IntelligenceClaimKind.RUMOR,
    }
    assert any(item.event_kind.value == "CONTRADICTION" for item in read.timeline)


def test_current_state_is_event_backed_and_history_is_append_only(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    evidence_one = _evidence(repository, "video-one")
    evidence_two = _evidence(repository, "video-two", role=EvidenceRole.INDEPENDENT_VERIFICATION)
    _admit(repository, "intelligence-one", evidence_one)
    _admit(repository, "intelligence-two", evidence_two)
    service = _topic_service(repository)
    topic = service.create_topic(command_id="timeline", name="Timeline")

    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-one",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    before = service.read_topic(topic.topic_id)
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-two",
        kind=TopicAssociationKind.NEW_EVIDENCE,
    )
    after = service.read_topic(topic.topic_id)

    assert before.current_event_id == before.timeline[-1].event_id
    assert after.current_event_id == after.timeline[-1].event_id
    assert after.current_event_id != before.current_event_id
    assert tuple(event.event_id for event in after.timeline[:1]) == tuple(
        event.event_id for event in before.timeline
    )
    connection = repository._connect()
    try:
        with pytest.raises(Exception, match="immutable"):
            connection.execute(
                "DELETE FROM topic_timeline_events WHERE event_id = ?", (before.current_event_id,)
            )
    finally:
        connection.close()


def test_invalidated_current_support_degrades_current_projection_but_not_history(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, "video-invalidated")
    current_revision = _admit(repository, "intelligence-invalidated", evidence_id)
    service = _topic_service(repository)
    topic = service.create_topic(command_id="invalidated", name="Correction")
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-invalidated",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    before = service.read_topic(topic.topic_id)
    repository.append_intelligence_revision(
        intelligence_id="intelligence-invalidated",
        revision=IntelligenceRevisionWrite(
            revision_id="intelligence-invalidated:r3",
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=IntelligenceClaimKind.FACT,
            content_hash="d" * 64,
            state=IntelligenceState.INVALIDATED,
            reason="correction invalidated current interpretation",
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id="support:intelligence-invalidated:r3",
            dependent_revision_id="intelligence-invalidated:r3",
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=evidence_id,
            input_revision_id=None,
        ),
        now=NOW,
    )
    after = service.read_topic(topic.topic_id)

    assert before.timeline[0].dependency_revision_ids == (current_revision,)
    assert after.current_state is TopicCurrentState.DEGRADED
    assert after.contributions[0].available is False
    assert after.timeline[0].event_id == before.timeline[0].event_id
    assert service.affected_memberships("intelligence-invalidated", current_revision)[0].topic_id == topic.topic_id


def test_related_topics_are_finite_navigational_and_noncausal(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    service = _topic_service(repository)
    first = service.create_topic(command_id="claude", name="Claude Code")
    second = service.create_topic(command_id="mcp", name="MCP")

    relation = service.relate_topics(first.topic_id, second.topic_id)
    read = service.read_topic(first.topic_id)

    assert relation.relation is TopicRelationKind.RELATED
    assert relation.causal is False
    assert read.relations[0].relation is TopicRelationKind.RELATED
    with pytest.raises(ValueError, match="relation"):
        service.relate_topics(first.topic_id, second.topic_id, relation="CAUSES")  # type: ignore[arg-type]


def test_merge_and_split_copy_associations_without_rewriting_source_identity(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, "video-merge")
    revision_id = _admit(repository, "intelligence-merge", evidence_id)
    service = _topic_service(repository)
    source = service.create_topic(command_id="source", name="Source")
    target = service.create_topic(command_id="target", name="Target")
    service.associate_intelligence(
        topic_id=source.topic_id,
        intelligence_id="intelligence-merge",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )

    service.merge_topics(target_topic_id=target.topic_id, source_topic_id=source.topic_id)
    target_membership = service.read_topic(target.topic_id).contributions[0]
    split = service.split_topic(
        source_topic_id=target.topic_id,
        command_id="split",
        name="Split",
        membership_ids=(target_membership.membership_id,),
    )

    assert service.read_topic(source.topic_id).contributions[0].revision_id == revision_id
    assert service.read_topic(target.topic_id).contributions[0].revision_id == revision_id
    assert service.read_topic(split.topic_id).contributions[0].revision_id == revision_id
    assert repository.get_intelligence_revision(revision_id).revision_id == revision_id  # type: ignore[union-attr]


def test_local_api_accepts_only_controlled_topic_commands_not_raw_topic_truth(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, "video-api")
    _admit(repository, "intelligence-api", evidence_id)
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        now=lambda: NOW,
    )

    status, created = app.handle(
        "POST", "/api/v1/topics", b'{"command_id":"api-topic","name":"API topic"}'
    )
    topic_id = created["topic"]["topic_id"]
    association_status, association = app.handle(
        "POST",
        f"/api/v1/topics/{topic_id}/associations",
        b'{"intelligence_id":"intelligence-api","association_kind":"NEW_INFORMATION"}',
    )
    get_status, projected = app.handle("GET", f"/api/v1/topics/{topic_id}")

    assert status == 201
    assert association_status == 201
    assert association["association"]["revision_id"] == "intelligence-api:r2"
    assert get_status == 200
    assert projected["topic"]["current_state"] == "UNRESOLVED"
    with pytest.raises(ApiError) as raw_revision:
        app.handle(
            "POST",
            f"/api/v1/topics/{topic_id}/associations",
            b'{"intelligence_id":"intelligence-api","revision_id":"intelligence-api:r1","association_kind":"NEW_INFORMATION"}',
        )
    with pytest.raises(ApiError) as raw_summary:
        app.handle(
            "POST", "/api/v1/topics", b'{"command_id":"bad","name":"Bad","summary":"invented truth"}'
        )
    assert raw_revision.value.code == "VALIDATION_ERROR"
    assert raw_summary.value.code == "VALIDATION_ERROR"


def test_raw_invalidated_membership_cannot_become_current_topic_truth(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, "video-raw-invalid")
    revision_id = _admit(
        repository,
        "intelligence-raw-invalid",
        evidence_id,
        state=IntelligenceState.INVALIDATED,
    )
    service = _topic_service(repository)
    topic = service.create_topic(command_id="raw-invalid", name="Raw invalid")

    with pytest.raises(Exception, match="legally readable"):
        service.associate_intelligence(
            topic_id=topic.topic_id,
            intelligence_id="intelligence-raw-invalid",
            kind=TopicAssociationKind.NEW_INFORMATION,
        )
    raw_membership = repository.create_topic_membership(
        TopicMembershipWrite(
            membership_id="raw-membership",
            topic_id=topic.topic_id,
            intelligence_id="intelligence-raw-invalid",
            revision_id=revision_id,
            association_kind=TopicAssociationKind.NEW_INFORMATION,
            source_claim_kind=IntelligenceClaimKind.FACT,
            source_state=IntelligenceState.INVALIDATED,
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    event = repository.create_topic_timeline_event(
        TopicTimelineEventWrite(
            event_id="raw-event",
            topic_id=topic.topic_id,
            event_kind=TopicTimelineEventKind.NEW_INFORMATION,
            state=TopicCurrentState.UNRESOLVED,
            membership_ids=(raw_membership.membership_id,),
        ),
        now=NOW,
    )
    repository.set_topic_current_event(topic_id=topic.topic_id, event_id=event.event_id, now=NOW)

    read = service.read_topic(topic.topic_id)

    assert read.current_state is TopicCurrentState.DEGRADED
    assert read.contributions[0].available is False


def test_foreign_or_mismatched_revision_cannot_enter_topic_membership(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, "video-owned")
    revision_id = _admit(repository, "intelligence-owned", evidence_id)
    topic = _topic_service(repository).create_topic(command_id="foreign", name="Foreign")

    with pytest.raises(IntegrityConflict):
        repository.create_topic_membership(
            TopicMembershipWrite(
                membership_id="foreign-membership",
                topic_id=topic.topic_id,
                intelligence_id="foreign-intelligence",
                revision_id=revision_id,
                association_kind=TopicAssociationKind.NEW_INFORMATION,
                source_claim_kind=IntelligenceClaimKind.FACT,
                source_state=IntelligenceState.CONFIRMED,
                evidence_ids=(evidence_id,),
            ),
            now=NOW,
        )


def test_timeline_event_without_a_meaningful_provenance_dependency_is_rejected(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    topic = _topic_service(repository).create_topic(command_id="empty-event", name="No source")
    connection = repository._connect()
    try:
        with pytest.raises(Exception, match="topic timeline event"):
            connection.execute(
                "INSERT INTO topic_timeline_events (event_id, topic_id, primary_membership_id, event_kind, state, created_at) "
                "VALUES ('orphan-event', ?, 'orphan-membership', 'NEW_INFORMATION', 'UNRESOLVED', '2026-09-07T09:00:00.000000Z')",
                (topic.topic_id,),
            )
    finally:
        connection.close()


def test_timeline_projection_includes_its_primary_membership_provenance(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, "video-primary-provenance")
    revision_id = _admit(repository, "intelligence-primary-provenance", evidence_id)
    service = _topic_service(repository)
    topic = service.create_topic(command_id="primary-provenance", name="Primary provenance")
    membership = repository.create_topic_membership(
        TopicMembershipWrite(
            membership_id="primary-provenance-membership",
            topic_id=topic.topic_id,
            intelligence_id="intelligence-primary-provenance",
            revision_id=revision_id,
            association_kind=TopicAssociationKind.NEW_INFORMATION,
            source_claim_kind=IntelligenceClaimKind.FACT,
            source_state=IntelligenceState.CONFIRMED,
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO topic_timeline_events (event_id, topic_id, primary_membership_id, event_kind, state, created_at) "
            "VALUES ('primary-provenance-event', ?, ?, 'NEW_INFORMATION', 'UNRESOLVED', '2026-09-07T09:00:00.000000Z')",
            (topic.topic_id, membership.membership_id),
        )
    finally:
        connection.close()

    event = service.read_topic(topic.topic_id).timeline[0]

    assert event.dependency_revision_ids == (revision_id,)
    assert event.dependency_evidence_ids == (evidence_id,)


def test_later_active_intelligence_revision_does_not_silently_overwrite_topic_history(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, "video-updated")
    original_revision = _admit(repository, "intelligence-updated", evidence_id)
    service = _topic_service(repository)
    topic = service.create_topic(command_id="updated", name="Updated")
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-updated",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    repository.append_intelligence_revision(
        intelligence_id="intelligence-updated",
        revision=IntelligenceRevisionWrite(
            revision_id="intelligence-updated:r3",
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=IntelligenceClaimKind.FACT,
            content_hash="e" * 64,
            state=IntelligenceState.UPDATED,
            reason="later trusted update requires explicit Topic association",
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id="support:intelligence-updated:r3",
            dependent_revision_id="intelligence-updated:r3",
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=evidence_id,
            input_revision_id=None,
        ),
        now=NOW,
    )

    read = service.read_topic(topic.topic_id)

    assert read.current_state is TopicCurrentState.DEGRADED
    assert read.timeline[0].dependency_revision_ids == (original_revision,)
    assert read.contributions[0].revision_id == original_revision


def test_pin_and_low_value_duplicate_do_not_change_topic_truth_or_timeline(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    first_evidence = _evidence(repository, "video-pin-one")
    duplicate_evidence = _evidence(repository, "video-pin-two")
    _admit(repository, "intelligence-pin-one", first_evidence)
    _admit(repository, "intelligence-pin-two", duplicate_evidence)
    service = _topic_service(repository)
    topic = service.create_topic(command_id="pin-truth", name="Pinned")
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-pin-one",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    before = service.read_topic(topic.topic_id)
    service.set_pinned(topic_id=topic.topic_id, pinned=True)
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intelligence-pin-two",
        kind=TopicAssociationKind.LOW_VALUE_DUPLICATE,
    )
    after = service.read_topic(topic.topic_id)

    assert after.pinned is True
    assert after.current_event_id == before.current_event_id
    assert after.current_state is before.current_state
    assert tuple(event.event_id for event in after.timeline) == tuple(
        event.event_id for event in before.timeline
    )
    assert len(after.contributions) == 2


def test_raw_timeline_state_cannot_mint_consensus_without_trusted_aggregation(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    evidence_id = _evidence(repository, "video-raw-state")
    revision_id = _admit(repository, "intelligence-raw-state", evidence_id)
    service = _topic_service(repository)
    topic = service.create_topic(command_id="raw-state", name="Raw state")
    membership = repository.create_topic_membership(
        TopicMembershipWrite(
            membership_id="raw-state-membership",
            topic_id=topic.topic_id,
            intelligence_id="intelligence-raw-state",
            revision_id=revision_id,
            association_kind=TopicAssociationKind.NEW_INFORMATION,
            source_claim_kind=IntelligenceClaimKind.FACT,
            source_state=IntelligenceState.CONFIRMED,
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    with pytest.raises(IntegrityConflict):
        repository.create_topic_timeline_event(
            TopicTimelineEventWrite(
                event_id="raw-state-event",
                topic_id=topic.topic_id,
                event_kind=TopicTimelineEventKind.NEW_INFORMATION,
                state=TopicCurrentState.CONSENSUS,
                membership_ids=(membership.membership_id,),
            ),
            now=NOW,
        )

    read = service.read_topic(topic.topic_id)
    assert read.current_state is TopicCurrentState.UNRESOLVED
    assert read.timeline == ()
