"""Unit tests for state-store boundary validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from youtube_intel.domain import InvalidTransitionError, PipelineStatus
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    build_provider_request_hash,
    format_utc_datetime,
)


def test_utc_datetime_uses_fixed_rfc3339_microseconds() -> None:
    value = datetime(2026, 7, 15, 8, 30, 1, 42, tzinfo=UTC)

    assert format_utc_datetime(value) == "2026-07-15T08:30:01.000042Z"


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 7, 15, 8, 30),
        datetime(2026, 7, 15, 8, 30, tzinfo=timezone(timedelta(hours=8))),
    ],
)
def test_state_store_rejects_naive_or_non_utc_datetime(value: datetime) -> None:
    with pytest.raises(ValueError, match="UTC datetime"):
        format_utc_datetime(value)


def _repository_with_candidate(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=datetime(2026, 7, 15, tzinfo=UTC))
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO videos "
            "(video_id, channel_id, pipeline_status, pipeline_version, "
            "discovered_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "video-1",
                "UC_TEST",
                PipelineStatus.DISCOVERED.value,
                "pipeline-v1",
                "2026-07-15T00:00:00.000000Z",
                "2026-07-15T00:00:00.000000Z",
            ),
        )
    finally:
        connection.close()
    return repository


def test_pipeline_cas_accepts_legal_transition(tmp_path: Path) -> None:
    repository = _repository_with_candidate(tmp_path)

    changed = repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="pipeline-v1",
        now=datetime(2026, 7, 15, tzinfo=UTC),
    )

    assert changed is True
    assert repository.get_video("video-1").pipeline_status is PipelineStatus.METADATA_READY


def test_pipeline_cas_rejects_illegal_or_stale_transition_without_write(
    tmp_path: Path,
) -> None:
    repository = _repository_with_candidate(tmp_path)

    with pytest.raises(InvalidTransitionError):
        repository.advance_pipeline(
            "video-1",
            expected_status=PipelineStatus.DISCOVERED,
            target_status=PipelineStatus.COMPLETE,
            pipeline_version="pipeline-v1",
            now=datetime(2026, 7, 15, tzinfo=UTC),
        )
    stale = repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="stale-version",
        now=datetime(2026, 7, 15, tzinfo=UTC),
    )

    assert stale is False
    assert repository.get_video("video-1").pipeline_status is PipelineStatus.DISCOVERED


def test_provider_request_hash_covers_every_cache_dimension() -> None:
    base = {
        "operation": "summarize",
        "normalized_input_hash": "a" * 64,
        "provider": "openai",
        "model": "model-a",
        "prompt_version": "prompt-v1",
        "schema_version": "schema-v1",
    }
    original = build_provider_request_hash(**base)

    for field, replacement in (
        ("operation", "score"),
        ("normalized_input_hash", "b" * 64),
        ("provider", "ollama"),
        ("model", "model-b"),
        ("prompt_version", "prompt-v2"),
        ("schema_version", "schema-v2"),
    ):
        changed = dict(base)
        changed[field] = replacement
        assert build_provider_request_hash(**changed) != original


@pytest.mark.parametrize("relative_path", ["/private/note.md", "../note.md", "C:/note.md"])
def test_artifact_rejects_absolute_or_escaping_path(
    tmp_path: Path, relative_path: str
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=datetime(2026, 7, 15, tzinfo=UTC))
    artifact = ArtifactWrite(
        artifact_id="artifact-1",
        artifact_key="artifact-key",
        video_id=None,
        job_id=None,
        kind=ArtifactKind.ANALYSIS_STRUCTURED,
        storage_root=StorageRoot.VAULT,
        relative_path=relative_path,
        content_hash="a" * 64,
        provider=None,
        model=None,
        producer_version="v1",
        retention_class=RetentionClass.LONG_LIVED,
        expires_at=None,
    )

    with pytest.raises(ValueError, match="safe relative paths"):
        repository.upsert_artifact(
            artifact, now=datetime(2026, 7, 15, tzinfo=UTC)
        )
