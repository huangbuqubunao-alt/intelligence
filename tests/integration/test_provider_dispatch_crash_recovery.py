"""Crash-window regression tests for cloud Provider dispatches.

These tests use no network or credentials.  They prove the persisted protocol
never turns a possibly dispatched cloud request into an automatic retry.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from importlib import resources

import pytest

from youtube_intel import state as state_mod
from youtube_intel.domain import ErrorCode
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    ProviderCallRequest,
    ProviderCallStatus,
    ProviderDispatchStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    VerifiedArtifact,
)

NOW = datetime(2026, 8, 31, tzinfo=UTC)


def _request() -> ProviderCallRequest:
    return ProviderCallRequest(
        operation="cloud-analysis",
        normalized_input_hash="a" * 64,
        provider="openai",
        model="gpt-4.1-mini",
        prompt_version="analysis-prompt-v1",
        schema_version="analysis-schema-v1",
        deterministic_artifact_key="analysis/dispatch-crash/raw",
    )


def _repository(tmp_path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    return repository


def _migrations_through_v3() -> tuple[state_mod._Migration, ...]:
    names = (
        "001_initial.sql",
        "002_add_scoring_lineage.sql",
        "003_add_deep_analysis_persistence.sql",
    )
    migrations = []
    for version, name in enumerate(names, start=1):
        sql = resources.files("youtube_intel").joinpath("migrations", name).read_bytes()
        migrations.append(
            state_mod._Migration(
                version=version,
                name=name,
                sql=sql.decode("utf-8"),
                checksum=hashlib.sha256(sql).hexdigest(),
            )
        )
    return tuple(migrations)


def _reserve(
    repository: SQLiteStateRepository, *, owner: str = "worker", now: datetime = NOW
):
    return repository.reserve_provider_call(
        _request(),
        owner=owner,
        lease_until=now + timedelta(minutes=5),
        available_at=now,
        now=now,
        fail_closed_on_ambiguous_dispatch=True,
    )


def test_restart_after_crash_before_dispatch_can_take_over_not_dispatched_call(
    tmp_path,
) -> None:
    """A crash before intent is safe: no external operation was authorized."""

    repository = _repository(tmp_path)
    initial = _reserve(repository)
    assert initial.acquired is True
    assert (
        repository.get_provider_dispatch(initial.record.request_hash).status
        is ProviderDispatchStatus.NOT_DISPATCHED
    )

    restarted = _reserve(repository, owner="recovery", now=NOW + timedelta(minutes=6))

    assert restarted.acquired is True
    assert restarted.record.reservation_owner == "recovery"
    assert restarted.record.attempt_count == 2
    assert (
        repository.get_provider_dispatch(initial.record.request_hash).status
        is ProviderDispatchStatus.NOT_DISPATCHED
    )


def test_migration_marks_pre_protocol_pending_call_ambiguous(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An old PENDING row is preserved but can never gain an automatic retry."""

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    monkeypatch.setattr(repository, "_load_migrations", _migrations_through_v3)
    repository.initialize(now=NOW)
    initial = repository.reserve_provider_call(
        _request(),
        owner="legacy-worker",
        lease_until=NOW + timedelta(minutes=5),
        available_at=NOW,
        now=NOW,
    )
    monkeypatch.undo()

    assert repository.initialize(now=NOW + timedelta(minutes=1)).version == 8
    dispatch = repository.get_provider_dispatch(initial.record.request_hash)

    assert dispatch is not None
    assert dispatch.status is ProviderDispatchStatus.AMBIGUOUS
    restarted = _reserve(repository, owner="recovery", now=NOW + timedelta(minutes=6))
    assert restarted.acquired is False
    assert restarted.record.status is ProviderCallStatus.FAILED_FINAL


def test_restart_after_durable_intent_before_provider_call_fails_closed(
    tmp_path,
) -> None:
    """Intent is conservative: a crash here must not authorize a duplicate call."""

    repository = _repository(tmp_path)
    initial = _reserve(repository)
    repository.record_provider_dispatch_intent(
        initial.record.request_hash, owner="worker", now=NOW
    )

    restarted = _reserve(repository, owner="recovery", now=NOW + timedelta(minutes=6))

    assert restarted.acquired is False
    assert restarted.record.status is ProviderCallStatus.FAILED_FINAL
    assert restarted.record.last_error_code == ErrorCode.PROVIDER_UNAVAILABLE.value
    assert restarted.record.attempt_count == 1
    assert (
        repository.get_provider_dispatch(initial.record.request_hash).status
        is ProviderDispatchStatus.AMBIGUOUS
    )


def test_provider_success_before_sqlite_commit_never_auto_redispatches(
    tmp_path,
) -> None:
    """A returned response without the atomic success receipt remains ambiguous."""

    repository = _repository(tmp_path)
    initial = _reserve(repository)
    repository.record_provider_dispatch_intent(
        initial.record.request_hash, owner="worker", now=NOW
    )
    repository.record_provider_dispatch_result_unknown(
        initial.record.request_hash, owner="worker", now=NOW
    )

    restarted = _reserve(repository, owner="recovery", now=NOW + timedelta(minutes=6))

    assert restarted.acquired is False
    assert restarted.recovered_from_artifact is False
    assert restarted.record.status is ProviderCallStatus.FAILED_FINAL
    assert (
        repository.get_provider_dispatch(initial.record.request_hash).status
        is ProviderDispatchStatus.AMBIGUOUS
    )


def test_ambiguous_dispatch_cannot_be_promoted_by_a_matching_cache_artifact(
    tmp_path,
) -> None:
    """Only the success transaction, never a cache artifact, establishes success."""

    repository = _repository(tmp_path)
    initial = _reserve(repository)
    repository.record_provider_dispatch_intent(
        initial.record.request_hash, owner="worker", now=NOW
    )
    repository.record_provider_dispatch_result_unknown(
        initial.record.request_hash, owner="worker", now=NOW
    )
    contents = b"untrusted orphan response"
    artifact = ArtifactWrite(
        artifact_id="ambiguous-raw",
        artifact_key=_request().deterministic_artifact_key,
        video_id=None,
        job_id=None,
        kind=ArtifactKind.ANALYSIS_RAW,
        storage_root=StorageRoot.DATA,
        relative_path="analysis/dispatch-crash/raw.json",
        content_hash=hashlib.sha256(contents).hexdigest(),
        provider="openai",
        model="gpt-4.1-mini",
        producer_version="analysis-raw-v1",
        retention_class=RetentionClass.RAW_RESPONSE_30D,
        expires_at=NOW + timedelta(days=30),
    )
    repository.upsert_artifact(artifact, now=NOW)

    restarted = repository.reserve_provider_call(
        _request(),
        owner="recovery",
        lease_until=NOW + timedelta(minutes=11),
        available_at=NOW + timedelta(minutes=6),
        now=NOW + timedelta(minutes=6),
        verified_artifact=VerifiedArtifact(
            artifact.artifact_key, artifact.content_hash
        ),
        fail_closed_on_ambiguous_dispatch=True,
    )

    assert restarted.acquired is False
    assert restarted.recovered_from_artifact is False
    assert restarted.record.status is ProviderCallStatus.FAILED_FINAL
    assert (
        repository.get_provider_dispatch(initial.record.request_hash).status
        is ProviderDispatchStatus.AMBIGUOUS
    )


def test_known_provider_failure_remains_distinct_from_ambiguous_dispatch(
    tmp_path,
) -> None:
    repository = _repository(tmp_path)
    initial = _reserve(repository)
    repository.record_provider_dispatch_intent(
        initial.record.request_hash, owner="worker", now=NOW
    )
    repository.record_provider_dispatch_known_failure(
        initial.record.request_hash, owner="worker", now=NOW
    )
    failed = repository.fail_provider_call(
        initial.record.request_hash,
        owner="worker",
        retryable=True,
        available_at=NOW + timedelta(minutes=1),
        error_code=ErrorCode.INVALID_RESPONSE,
        error_message="synthetic provider rejection",
        now=NOW,
    )

    assert failed.status is ProviderCallStatus.FAILED_RETRYABLE
    assert (
        repository.get_provider_dispatch(initial.record.request_hash).status
        is ProviderDispatchStatus.FAILED_KNOWN
    )


def test_normal_success_commits_the_provider_receipt_once(tmp_path) -> None:
    repository = _repository(tmp_path)
    initial = _reserve(repository)
    repository.record_provider_dispatch_intent(
        initial.record.request_hash, owner="worker", now=NOW
    )
    repository.record_provider_dispatch_result_unknown(
        initial.record.request_hash, owner="worker", now=NOW
    )
    contents = b"verified response"
    artifact = ArtifactWrite(
        artifact_id="success-raw",
        artifact_key=_request().deterministic_artifact_key,
        video_id=None,
        job_id=None,
        kind=ArtifactKind.ANALYSIS_RAW,
        storage_root=StorageRoot.DATA,
        relative_path="analysis/dispatch-crash/raw.json",
        content_hash=hashlib.sha256(contents).hexdigest(),
        provider="openai",
        model="gpt-4.1-mini",
        producer_version="analysis-raw-v1",
        retention_class=RetentionClass.RAW_RESPONSE_30D,
        expires_at=NOW + timedelta(days=30),
    )
    repository.upsert_artifact(artifact, now=NOW)
    completed = repository.complete_provider_call(
        initial.record.request_hash,
        owner="worker",
        response_artifact_id=artifact.artifact_id,
        input_tokens=1,
        output_tokens=1,
        cost_microusd=1,
        now=NOW,
    )

    assert completed.status is ProviderCallStatus.SUCCEEDED
    assert (
        repository.get_provider_dispatch(initial.record.request_hash).status
        is ProviderDispatchStatus.SUCCESS_DURABLY_RECORDED
    )
