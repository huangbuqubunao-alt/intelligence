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
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
    SQLiteStateRepository,
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
    assert repository.initialize(now=NOW).version == 11
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


def test_m011_fresh_database_reaches_exactly_v011_and_m012_is_absent(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 11
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

    assert migrations[-1] == "011_add_topic_timeline.sql"
    assert not any(name.startswith("012_") for name in migrations)
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
    assert upgraded.initialize(now=NOW).version == 11
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
    assert consensus.independence is "KNOWN_INDEPENDENT"
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
    membership = service.associate_intelligence(
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
