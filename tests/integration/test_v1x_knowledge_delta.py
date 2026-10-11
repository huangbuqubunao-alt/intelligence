"""Computed Home changes: real SQLite, fixed clock, no provider or runtime."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.knowledge_delta import KnowledgeDeltaService
from youtube_intel.orchestration import ProcessingPolicy, SourceType
from youtube_intel.source_run import (
    SOURCE_RUN_CHECKPOINT_ORDER,
    SourceRunAttentionReason,
    SourceRunCheckpoint,
    SourceRunPriority,
    SourceRunState,
    SourceRunWrite,
)
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
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    TopicAssociationKind,
    build_evidence_id,
    format_utc_datetime,
)
from youtube_intel.topic import TopicApplicationService

NOW = datetime(2026, 10, 3, 8, tzinfo=UTC)
START = NOW - timedelta(days=7)


@pytest.fixture
def repository(tmp_path: Path) -> SQLiteStateRepository:
    result = SQLiteStateRepository(tmp_path / "state.sqlite3")
    result.initialize(now=NOW)
    return result


def content(
    repository: SQLiteStateRepository,
    identity: str,
    at: datetime,
    *,
    completed: bool = True,
) -> None:
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO videos (video_id, channel_id, title, pipeline_status, "
            "pipeline_version, discovered_at, updated_at, completed_at, availability) "
            "VALUES (?, 'channel', ?, ?, 'fixture', ?, ?, ?, 'public')",
            (
                identity,
                f"Content {identity}",
                "COMPLETE" if completed else "DISCOVERED",
                format_utc_datetime(at - timedelta(days=1)),
                format_utc_datetime(at),
                format_utc_datetime(at) if completed else None,
            ),
        )
    finally:
        connection.close()


def read(repository: SQLiteStateRepository) -> dict[str, object]:
    return KnowledgeDeltaService(repository, now=lambda: NOW).read().as_dict()


def category(result: dict[str, object], kind: str) -> dict[str, object]:
    return next(item for item in result["categories"] if item["kind"] == kind)  # type: ignore[union-attr]


def test_empty_is_complete_and_has_one_testable_window(
    repository: SQLiteStateRepository,
) -> None:
    result = read(repository)
    assert result["status"] == "available"
    assert result["window_start"] == format_utc_datetime(START)
    assert result["window_end"] == format_utc_datetime(NOW)
    assert all(item["count"] == 0 for item in result["categories"])  # type: ignore[union-attr]


def test_content_boundaries_future_and_discovery_are_explicit(
    repository: SQLiteStateRepository,
) -> None:
    content(repository, "before", START - timedelta(microseconds=1))
    content(repository, "start", START)
    content(repository, "end", NOW)
    content(repository, "future", NOW + timedelta(microseconds=1))
    content(repository, "pending", NOW, completed=False)
    result = category(read(repository), "content_completed")
    assert result["count"] == 2
    assert [item["target"]["id"] for item in result["items"]] == ["end", "start"]  # type: ignore[union-attr]


def test_same_time_is_stable_and_response_is_bounded(
    repository: SQLiteStateRepository,
) -> None:
    for i in reversed(range(120)):
        content(repository, f"item-{i:03}", NOW)
    first = read(repository)
    assert first == read(repository)
    result = category(first, "content_completed")
    assert result["count"] == 120
    assert [item["target"]["id"] for item in result["items"]] == [
        "item-000",
        "item-001",
    ]  # type: ignore[union-attr]


def test_clock_normalizes_aware_offsets_and_rejects_naive(
    repository: SQLiteStateRepository,
) -> None:
    from zoneinfo import ZoneInfo

    result = KnowledgeDeltaService(
        repository, now=lambda: NOW.astimezone(ZoneInfo("Asia/Shanghai"))
    ).read()
    assert result.as_dict() == read(repository)
    with pytest.raises(ValueError, match="aware"):
        KnowledgeDeltaService(repository, now=lambda: NOW.replace(tzinfo=None)).read()


def evidence(
    repository: SQLiteStateRepository, identity: str, *, start_ms: int = 0
) -> str:
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT OR IGNORE INTO artifacts (artifact_id, artifact_key, video_id, kind, "
            "storage_root, relative_path, content_hash, producer_version, retention_class, created_at) "
            "VALUES (?, ?, ?, 'transcript_canonical', 'DATA', 'transcript.txt', ?, 'fixture', 'LONG_LIVED', ?)",
            (
                f"artifact-{identity}",
                f"artifact-{identity}",
                identity,
                "a" * 64,
                format_utc_datetime(START),
            ),
        )
    finally:
        connection.close()
    artifact = f"artifact-{identity}"
    evidence_id = build_evidence_id(
        video_id=identity,
        artifact_id=artifact,
        start_ms=start_ms,
        end_ms=start_ms + 100,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    repository.create_evidence(
        EvidenceWrite(
            evidence_id=evidence_id,
            video_id=identity,
            artifact_id=artifact,
            start_ms=start_ms,
            end_ms=start_ms + 100,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
        ),
        now=START,
    )
    return evidence_id


def revision(
    repository: SQLiteStateRepository,
    identity: str,
    number: int,
    at: datetime,
    support: tuple[str, ...],
    state: IntelligenceState = IntelligenceState.NEW,
) -> None:
    if number == 1:
        # Identity allocation is not admission: creation can precede revision 1.
        repository.create_intelligence(
            intelligence_id=identity, now=START - timedelta(days=30)
        )
    repository.append_intelligence_revision(
        intelligence_id=identity,
        revision=IntelligenceRevisionWrite(
            revision_id=f"{identity}-r{number}",
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash="b" * 64,
            state=state,
            reason="Explicit recorded evidence revision",
            evidence_ids=support,
        ),
        now=at,
    )
    for evidence_id in support:
        repository.create_dependency_edge(
            DependencyEdgeWrite(
                edge_id=f"{identity}-r{number}:{evidence_id}",
                dependent_revision_id=f"{identity}-r{number}",
                relation=DependencyRelation.EVIDENCE_SUPPORT,
                input_evidence_id=evidence_id,
                input_revision_id=None,
            ),
            now=at,
        )


def test_admission_and_many_revisions_are_not_double_counted(
    repository: SQLiteStateRepository,
) -> None:
    content(repository, "original", START, completed=False)
    support = (evidence(repository, "original"),)
    revision(repository, "new", 1, START, support)
    for number in range(2, 11):
        revision(repository, "new", number, NOW, support, IntelligenceState.UPDATED)
    result = read(repository)
    added = category(result, "intelligence_added")
    assert added["count"] == 1
    assert category(result, "intelligence_revised")["count"] == 0
    item = added["items"][0]  # type: ignore[index]
    assert item["facts"]["revision_count"] == 9
    assert item["facts"]["state_after"] is None  # NEW/UPDATED lifecycle noise
    assert item["target"] == {"kind": "intelligence", "id": "new"}
    assert item["title"] == "Content original"  # context, not an invented conclusion


def test_revision_evidence_set_and_explicit_state_change(
    repository: SQLiteStateRepository,
) -> None:
    content(repository, "original", START, completed=False)
    first = evidence(repository, "original")
    second = evidence(repository, "original", start_ms=1000)
    revision(repository, "old", 1, START - timedelta(microseconds=1), (first,))
    revision(repository, "old", 2, START, (first, second), IntelligenceState.CONFIRMED)
    revision(repository, "old", 3, NOW, (second,), IntelligenceState.DISPUTED)
    result = category(read(repository), "intelligence_revised")
    assert result["count"] == 1
    facts = result["items"][0]["facts"]  # type: ignore[index]
    assert facts["revision_count"] == 2
    assert (facts["evidence_before"], facts["evidence_after"]) == (1, 1)
    assert facts["evidence_set_changed"] is True  # replacement, not just count growth
    assert (facts["state_before"], facts["state_after"]) == ("Confirmed", "Disputed")


def test_future_revision_is_excluded_and_empty_identity_is_not_admission(
    repository: SQLiteStateRepository,
) -> None:
    content(repository, "original", START, completed=False)
    support = (evidence(repository, "original"),)
    repository.create_intelligence(intelligence_id="empty", now=NOW)
    revision(repository, "new", 1, NOW, support)
    revision(
        repository,
        "new",
        2,
        NOW + timedelta(microseconds=1),
        support,
        IntelligenceState.UPDATED,
    )
    result = read(repository)
    assert category(result, "intelligence_added")["count"] == 1
    assert (
        category(result, "intelligence_added")["items"][0]["facts"]["revision_count"]
        == 0
    )  # type: ignore[index]


def source(repository: SQLiteStateRepository, identity: str = "source") -> None:
    repository.create_source_subscription(
        SourceSubscriptionRecord(
            source_id=identity,
            source_type=SourceType.CHANNEL,
            canonical_url=f"https://www.youtube.com/channel/{identity}",
            channel_id=identity,
            video_id=None,
            display_name=f"Source {identity}",
            enabled=True,
            processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
            last_checked_at=None,
            last_success_at=None,
            last_error_code=None,
            last_error_message=None,
            created_at=START,
            updated_at=START,
        )
    )


def source_run(
    repository: SQLiteStateRepository,
    identity: str,
    at: datetime,
    *,
    source_id: str = "source",
    success: bool = False,
    model_noise: bool = False,
) -> None:
    run = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=source_id,
            command_id=identity,
            priority=SourceRunPriority.P0,
            created_at=at,
        )
    )
    repository.transition_source_run(
        run.run_id, to_state=SourceRunState.RUNNING, now=at
    )
    if success:
        for checkpoint in SOURCE_RUN_CHECKPOINT_ORDER:
            repository.complete_source_run_checkpoint(run.run_id, checkpoint, now=at)
        repository.transition_source_run(
            run.run_id, to_state=SourceRunState.COMPLETED, now=at
        )
    else:
        if model_noise:
            repository.complete_source_run_checkpoint(
                run.run_id, SourceRunCheckpoint.DISCOVERY, now=at
            )
        repository.block_source_run_checkpoint(
            run.run_id,
            SourceRunCheckpoint.SELECTION
            if model_noise
            else SourceRunCheckpoint.DISCOVERY,
            now=at,
        )
        repository.transition_source_run(
            run.run_id,
            to_state=SourceRunState.NEEDS_ATTENTION,
            attention_reason=SourceRunAttentionReason.MODEL_UNAVAILABLE
            if model_noise
            else SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED,
            now=at,
        )


def test_repeated_discovery_failure_is_bounded_not_model_noise(
    repository: SQLiteStateRepository,
) -> None:
    source(repository)
    source_run(repository, "one", START)
    assert category(read(repository), "source_health")["count"] == 0
    source_run(repository, "two", NOW)
    for number in range(10):
        source_run(repository, f"noise-{number}", NOW, model_noise=True)
    result = category(read(repository), "source_health")
    assert result["count"] == 1
    assert result["items"][0]["label"] == "Source discovery repeatedly blocked"  # type: ignore[index]
    assert result["items"][0]["facts"]["failure_count"] == 2  # type: ignore[index]


def test_recovery_requires_historical_failure_and_success_proof(
    repository: SQLiteStateRepository,
) -> None:
    source(repository)
    source_run(repository, "a", START)
    source_run(repository, "b", START + timedelta(hours=1))
    source_run(repository, "recovered", NOW, success=True)
    result = category(read(repository), "source_health")
    assert result["count"] == 1
    assert result["items"][0]["label"] == "Source checks resumed"  # type: ignore[index]
    source(repository, "healthy")
    source_run(repository, "normal", NOW, source_id="healthy", success=True)
    assert category(read(repository), "source_health")["count"] == 1


def test_explicit_check_failure_excludes_guard_and_future(
    repository: SQLiteStateRepository,
) -> None:
    for identity, code, at in [
        ("failed", "SOURCE_CHECK_FAILED", NOW),
        ("guard", "EXECUTION_GUARD_BLOCKED", NOW),
        ("future", "SOURCE_CHECK_FAILED", NOW + timedelta(microseconds=1)),
    ]:
        source(repository, identity)
        repository.record_source_check(
            identity, now=at, succeeded=False, error_code=code, error_message="PRIVATE"
        )
    result = category(read(repository), "source_health")
    assert result["count"] == 1
    assert "PRIVATE" not in str(result)


def test_topics_use_real_memberships_not_names_or_compatibility(
    repository: SQLiteStateRepository,
) -> None:
    content(repository, "original", START, completed=False)
    support = (evidence(repository, "original"),)
    revision(repository, "intel", 1, START, support)
    service = TopicApplicationService(repository, now=lambda: NOW)
    first = service.create_topic(command_id="one", name="First real Topic")
    second = service.create_topic(command_id="two", name="Second real Topic")
    service.create_topic(command_id="empty", name="Renaming is not knowledge")
    for item in [first, second]:
        service.associate_intelligence(
            topic_id=item.topic_id,
            intelligence_id="intel",
            kind=TopicAssociationKind.NEW_INFORMATION,
        )
    result = category(read(repository), "topic_updated")
    assert result["count"] == 2
    assert [item["target"]["id"] for item in result["items"]] == [
        first.topic_id,
        second.topic_id,
    ]  # type: ignore[union-attr]
    assert all(item["facts"]["topic_event_count"] == 1 for item in result["items"])  # type: ignore[union-attr]


def test_offset_and_noncanonical_aware_timestamps_are_exact(
    repository: SQLiteStateRepository,
) -> None:
    content(repository, "offset", NOW)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET completed_at='2026-10-03T16:00:00+08:00' WHERE video_id='offset'"
        )
    finally:
        connection.close()
    result = category(read(repository), "content_completed")
    assert result["count"] == 1
    assert result["items"][0]["occurred_at"] == format_utc_datetime(NOW)  # type: ignore[index]


def test_malformed_or_naive_completion_dates_never_reach_ui(
    repository: SQLiteStateRepository,
) -> None:
    content(repository, "bad", NOW)
    connection = repository._connect()
    try:
        for timestamp in ("2026-10-02nonsense", "2026-10-02T18:00:00"):
            connection.execute(
                "UPDATE videos SET completed_at=? WHERE video_id='bad'", (timestamp,)
            )
            assert category(read(repository), "content_completed")["count"] == 0
    finally:
        connection.close()


def test_incomplete_revision_authority_is_unavailable_not_admitted(
    repository: SQLiteStateRepository,
) -> None:
    content(repository, "original", START, completed=False)
    support = (evidence(repository, "original"),)
    repository.create_intelligence(intelligence_id="incomplete", now=NOW)
    repository.append_intelligence_revision(
        intelligence_id="incomplete",
        revision=IntelligenceRevisionWrite(
            revision_id="incomplete-r1",
            interpretation_kind=IntelligenceInterpretationKind.DISTILLATION,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash="b" * 64,
            state=IntelligenceState.NEW,
            reason="Not fully admitted; dependency write missing",
            evidence_ids=support,
        ),
        now=NOW,
    )
    result = read(repository)
    assert result["status"] == "partial"
    assert category(result, "intelligence_added")["count"] is None
    assert category(result, "intelligence_revised")["count"] is None


def test_dst_window_is_168_elapsed_hours_and_clock_is_called_once(
    repository: SQLiteStateRepository,
) -> None:
    from zoneinfo import ZoneInfo

    instant = datetime(2026, 11, 3, 12, tzinfo=ZoneInfo("America/New_York"))
    calls = 0

    def clock() -> datetime:
        nonlocal calls
        calls += 1
        return instant

    result = KnowledgeDeltaService(
        repository, now=clock, timezone="America/New_York"
    ).read()
    assert calls == 1
    assert datetime.fromisoformat(result.window_end) - datetime.fromisoformat(
        result.window_start
    ) == timedelta(hours=168)
    assert result.window_start == "2026-10-27T17:00:00.000000Z"


def test_read_is_same_after_restart_and_never_writes_authority(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    content(repository, "original", NOW)
    support = (evidence(repository, "original"),)
    revision(repository, "intel", 1, START, support)
    revision(repository, "intel", 2, NOW, support, IntelligenceState.CONFIRMED)
    connection = repository._connect()
    before = tuple(connection.iterdump())
    connection.close()
    expected = read(repository)
    restarted = SQLiteStateRepository(database)
    restarted.initialize(now=NOW)
    assert expected == read(restarted)
    connection = restarted._connect()
    try:
        assert before == tuple(connection.iterdump())
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 37
        assert not [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            if any(
                word in row[0]
                for word in ("delta", "watermark", "last_seen", "last_home_view")
            )
        ]
    finally:
        connection.close()


def test_core_backup_restore_recomputes_same_delta(tmp_path: Path) -> None:
    from youtube_intel.backup_restore import BackupRestoreService

    database = tmp_path / "state.sqlite3"
    data_root = tmp_path / "data"
    data_root.mkdir()
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    content(repository, "original", NOW)
    expected = read(repository)
    backup_service = BackupRestoreService(database=database, data_root=data_root)
    backup = backup_service.create_backup()
    archive, _ = backup_service.backup_download(backup.backup_id) or (None, None)
    assert archive is not None
    content(repository, "later", NOW)
    assert expected != read(repository)
    staged = backup_service.stage_restore(archive.read_bytes())
    backup_service.confirm_restore(staged.restore_id)
    backup_service.recover_and_apply_pending_restore()
    restarted = SQLiteStateRepository(database)
    restarted.initialize(now=NOW)
    assert read(restarted) == expected


def test_compatibility_topics_and_metadata_alone_are_inert(
    repository: SQLiteStateRepository,
) -> None:
    import json

    content(repository, "topic-keyword", NOW, completed=False)
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, kind, storage_root, "
            "relative_path, content_hash, producer_version, retention_class, created_at) "
            "VALUES ('compatibility', 'compatibility', 'topic-keyword', 'analysis_structured', 'DATA', ?, ?, 'fixture', 'LONG_LIVED', ?)",
            (
                json.dumps(
                    {"knowledge_graph": {"topics": ["AI agents", "Personal beliefs"]}}
                ),
                "a" * 64,
                format_utc_datetime(NOW),
            ),
        )
        repository.create_topic(topic_id="metadata-only", name="AI agents", now=NOW)
    finally:
        connection.close()
    result = read(repository)
    assert category(result, "topic_updated")["count"] == 0
    assert category(result, "intelligence_added")["count"] == 0
    assert category(result, "content_completed")["count"] == 0


def test_large_dataset_has_constant_query_count_and_bounded_titles(
    repository: SQLiteStateRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = repository._connect()
    try:
        connection.executemany(
            "INSERT INTO videos (video_id, channel_id, title, pipeline_status, pipeline_version, discovered_at, updated_at, completed_at) "
            "VALUES (?, 'channel', ?, 'COMPLETE', 'fixture', ?, ?, ?)",
            [
                (
                    f"large-{number:05}",
                    "Long title " * 1000,
                    format_utc_datetime(START),
                    format_utc_datetime(NOW),
                    format_utc_datetime(NOW),
                )
                for number in range(10000)
            ],
        )
    finally:
        connection.close()
    statements: list[str] = []
    original_connect = repository._connect

    def traced_connect(*, read_only: bool = False):  # type: ignore[no-untyped-def]
        connection = original_connect(read_only=read_only)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(repository, "_connect", traced_connect)
    result = read(repository)
    assert category(result, "content_completed")["count"] == 10000
    assert sum(len(item["items"]) for item in result["categories"]) <= 10  # type: ignore[union-attr]
    assert len(category(result, "content_completed")["items"][0]["title"]) == 240  # type: ignore[index,arg-type]
    reads = [
        statement
        for statement in statements
        if statement.lstrip().startswith(("SELECT", "WITH"))
    ]
    assert len(reads) == 5  # Count/detail combined, no per-item queries.
    assert not any(
        statement.lstrip().startswith(
            ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP")
        )
        for statement in statements
    )


def test_recovery_remains_recent_after_ordinary_successful_checks(
    repository: SQLiteStateRepository,
) -> None:
    source(repository)
    source_run(repository, "a", START)
    source_run(repository, "b", START + timedelta(hours=1))
    source_run(repository, "recovered", START + timedelta(hours=2), success=True)
    source_run(repository, "ordinary", NOW, success=True)
    result = category(read(repository), "source_health")
    assert result["count"] == 1
    assert result["items"][0]["label"] == "Source checks resumed"  # type: ignore[index]
    assert result["items"][0]["occurred_at"] == format_utc_datetime(
        START + timedelta(hours=2)
    )  # type: ignore[index]


def test_single_snapshot_does_not_mix_concurrent_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "state.sqlite3"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    content(repository, "original", NOW)
    support = (evidence(repository, "original"),)
    writer = SQLiteStateRepository(database)
    original_connect = repository._connect
    mutated = False

    def connect(*, read_only: bool = False):  # type: ignore[no-untyped-def]
        connection = original_connect(read_only=read_only)

        def concurrent_write(statement: str) -> None:
            nonlocal mutated
            if statement.lstrip().startswith("SELECT EXISTS") and not mutated:
                mutated = True
                revision(writer, "concurrent", 1, NOW, support)

        connection.set_trace_callback(concurrent_write)
        return connection

    monkeypatch.setattr(repository, "_connect", connect)
    snapshot = read(repository)
    assert mutated
    assert category(snapshot, "content_completed")["count"] == 1
    assert category(snapshot, "intelligence_added")["count"] == 0
    assert category(read(writer), "intelligence_added")["count"] == 1


def test_cross_content_topic_links_are_only_explicit_memberships(
    repository: SQLiteStateRepository,
) -> None:
    service = TopicApplicationService(repository, now=lambda: NOW)
    topic = service.create_topic(command_id="explicit", name="AI agents")
    for identity in ("content-a", "content-b"):
        content(repository, identity, NOW, completed=False)
        support = (evidence(repository, identity),)
        revision(repository, f"intel-{identity}", 1, START, support)
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intel-content-a",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    result = category(read(repository), "topic_updated")
    assert result["count"] == 1
    assert result["items"][0]["facts"]["topic_event_count"] == 1  # type: ignore[index]
    service.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id="intel-content-b",
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    result = category(read(repository), "topic_updated")
    assert result["count"] == 1
    assert result["items"][0]["facts"]["topic_event_count"] == 2  # type: ignore[index]


def test_source_failure_ties_are_stable_and_disabled_sources_are_excluded(
    repository: SQLiteStateRepository,
) -> None:
    for identity in ("z", "a", "disabled"):
        source(repository, identity)
        source_run(repository, f"{identity}-first", NOW, source_id=identity)
        source_run(repository, f"{identity}-second", NOW, source_id=identity)
    repository.update_source_subscription("disabled", enabled=False, now=NOW)
    result = category(read(repository), "source_health")
    assert result["count"] == 2
    assert [item["target"]["id"] for item in result["items"]] == ["a", "z"]  # type: ignore[union-attr]


def test_same_instant_failure_and_recovery_use_event_identity(
    repository: SQLiteStateRepository,
) -> None:
    source(repository)
    source_run(repository, "first", NOW)
    source_run(repository, "second", NOW)
    source_run(repository, "recovered", NOW, success=True)
    result = read(repository)
    item = category(result, "source_health")["items"][0]  # type: ignore[index]
    assert item["label"] == "Source checks resumed"
    assert item["facts"]["failure_count"] == 2
    assert result == read(repository)
