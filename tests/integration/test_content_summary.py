"""Integration coverage for the explicit current Summary / Video Notes authority."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

import pytest

from youtube_intel.content_summary import (
    ContentSummaryAuthority,
    ContentSummaryReadRejected,
)
from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.note_v2 import NoteV2SectionKind, build_note_v2
from youtube_intel.orchestration_service import ProductOrchestrationService

NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _persist(
    admitted_artifact_bundle: Callable[..., tuple[object, object, object, object, object]],
    tmp_path: Path,
) -> tuple[object, object, object]:
    artifact, source, repository, _scoring_reader, _runtime = admitted_artifact_bundle(
        tmp_path
    )
    persisted = DeepAnalysisPersistenceStore(repository).persist_trusted_deep_analysis_success(
        success=source, now=NOW
    )
    return artifact, repository, persisted


def test_persisted_result_is_not_current_until_explicitly_promoted(
    tmp_path: Path,
    admitted_artifact_bundle: Callable[..., tuple[object, object, object, object, object]],
) -> None:
    artifact, repository, persisted = _persist(admitted_artifact_bundle, tmp_path)
    authority = ContentSummaryAuthority(repository)

    with pytest.raises(ContentSummaryReadRejected) as missing:
        authority.read_current(artifact.video_id)
    assert missing.value.code == "CURRENT_SUMMARY_MISSING"

    binding = authority.promote_verified_result(persisted, now=NOW)
    current = authority.read_current(artifact.video_id)

    assert binding.video_id == artifact.video_id
    assert binding.result_identity == persisted.result_identity
    assert current.binding == binding
    assert current.note == build_note_v2(persisted)
    assert current.note.identity == binding.note_identity
    assert current.note.language == binding.output_language

    # Re-promoting the same verified result is idempotent and does not mint a
    # newer apparent version.
    assert authority.promote_verified_result(persisted, now=NOW) == binding


def test_current_summary_reader_rejects_tampered_pointer_metadata(
    tmp_path: Path,
    admitted_artifact_bundle: Callable[..., tuple[object, object, object, object, object]],
) -> None:
    artifact, repository, persisted = _persist(admitted_artifact_bundle, tmp_path)
    authority = ContentSummaryAuthority(repository)
    authority.promote_verified_result(persisted, now=NOW)

    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE current_content_summaries SET note_identity = ? WHERE video_id = ?",
            ("f" * 64, artifact.video_id),
        )
    finally:
        connection.close()

    with pytest.raises(ContentSummaryReadRejected) as rejected:
        authority.read_current(artifact.video_id)
    assert rejected.value.code == "CURRENT_SUMMARY_BINDING_INVALID"


def test_current_summary_reader_fails_closed_on_malformed_binding_timestamp(
    tmp_path: Path,
    admitted_artifact_bundle: Callable[..., tuple[object, object, object, object, object]],
) -> None:
    artifact, repository, persisted = _persist(admitted_artifact_bundle, tmp_path)
    authority = ContentSummaryAuthority(repository)
    authority.promote_verified_result(persisted, now=NOW)

    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE current_content_summaries SET promoted_at = ? WHERE video_id = ?",
            ("not-a-timestamp", artifact.video_id),
        )
    finally:
        connection.close()

    with pytest.raises(ContentSummaryReadRejected) as rejected:
        authority.read_current(artifact.video_id)
    assert rejected.value.code == "CURRENT_SUMMARY_BINDING_INVALID"


def test_verified_read_from_another_repository_cannot_be_promoted(
    tmp_path: Path,
    admitted_artifact_bundle: Callable[..., tuple[object, object, object, object, object]],
) -> None:
    _artifact, _repository, persisted = _persist(
        admitted_artifact_bundle, tmp_path / "source"
    )
    target_artifact, _target_source, target_repository, _reader, _runtime = (
        admitted_artifact_bundle(tmp_path / "target")
    )
    authority = ContentSummaryAuthority(target_repository)

    with pytest.raises(ValueError, match="not present in this repository"):
        authority.promote_verified_result(persisted, now=NOW)

    with pytest.raises(ContentSummaryReadRejected):
        authority.read_current(target_artifact.video_id)


def test_local_api_projects_one_line_summary_core_points_and_evidence_only_after_promotion(
    tmp_path: Path,
    admitted_artifact_bundle: Callable[..., tuple[object, object, object, object, object]],
) -> None:
    artifact, repository, persisted = _persist(admitted_artifact_bundle, tmp_path)
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        data_root=tmp_path,
        output_language="zh-CN",
        now=lambda: NOW,
    )

    before = app.handle("GET", f"/api/v1/videos/{artifact.video_id}")[1]["note"]["v2"]
    assert before["status"] == "UNAVAILABLE"
    assert before["code"] == "CURRENT_SUMMARY_MISSING"

    ContentSummaryAuthority(repository).promote_verified_result(persisted, now=NOW)
    after = app.handle("GET", f"/api/v1/videos/{artifact.video_id}")[1]["note"]["v2"]

    note = build_note_v2(persisted)
    summary = next(
        section for section in note.sections if section.kind is NoteV2SectionKind.SUMMARY
    )
    core_points = next(
        section
        for section in note.sections
        if section.kind is NoteV2SectionKind.CORE_POINTS
    )

    assert after["status"] == "AVAILABLE"
    assert after["note_identity"] == note.identity
    assert after["result_identity"] == persisted.result_identity
    assert after["language"] == note.language
    assert after["one_sentence_summary"] == summary.entries[0].text
    assert [point["text"] for point in after["core_points"]] == [
        point.text for point in core_points.entries
    ]
    assert after["evidence"]
    assert all(item["evidence_id"] for item in after["evidence"])
