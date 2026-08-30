"""TASK-016F deterministic Weekly V2 aggregation from verified Note artifacts."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
from youtube_intel.deep_analysis_runtime import _capture_trusted_success_for_persistence
from youtube_intel.note_v2 import render_note_v2
from youtube_intel.weekly_v2 import WeeklyV2Error, build_weekly_v2, render_weekly_v2


def test_weekly_v2_requires_admitted_artifacts_and_rejects_raw_boundary_bypasses(
    tmp_path: Path, admitted_artifact_bundle: object
) -> None:
    assert callable(admitted_artifact_bundle)
    artifact, source, repository, _scoring_reader, _runtime = admitted_artifact_bundle(
        tmp_path
    )
    DeepAnalysisPersistenceStore(repository).persist_trusted_deep_analysis_success(
        success=source, now=datetime(2026, 8, 30, tzinfo=UTC)
    )
    connection = repository._connect()
    try:
        raw_persisted_row = connection.execute(
            "SELECT * FROM deep_analysis_persisted_results LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    material = _capture_trusted_success_for_persistence(source)
    assert material is not None

    raw_values = (
        artifact.note,
        render_note_v2(artifact.note),
        source,
        material.content,
        raw_persisted_row,
        replace(artifact),
        replace(artifact, source_url="https://attacker.invalid/forged"),
        {"identity": artifact.identity},
        artifact.identity,
    )
    for raw_value in raw_values:
        with pytest.raises(WeeklyV2Error, match="verified Note V2 artifact"):
            build_weekly_v2(
                (raw_value,),
                now=datetime(2026, 8, 30, tzinfo=UTC),
                timezone="Asia/Shanghai",
                top_n=10,
            )


@pytest.mark.parametrize(
    ("completed_at", "included"),
    (
        (datetime(2026, 8, 23, 15, 59, 59, tzinfo=UTC), False),
        (datetime(2026, 8, 23, 16, tzinfo=UTC), True),
        (datetime(2026, 8, 27, 12, tzinfo=UTC), True),
        (datetime(2026, 8, 30, 15, 59, 59, tzinfo=UTC), True),
        (datetime(2026, 8, 30, 16, tzinfo=UTC), False),
    ),
)
def test_weekly_v2_uses_authoritative_completed_at_in_configured_iso_window(
    tmp_path: Path, completed_at: datetime, included: bool, admitted_artifact: object
) -> None:
    assert callable(admitted_artifact)
    report = build_weekly_v2(
        (admitted_artifact(tmp_path, completed_at=completed_at),),
        now=datetime(2026, 8, 27, 12, tzinfo=UTC),
        timezone="Asia/Shanghai",
        top_n=10,
    )

    assert bool(report.items) is included


def test_weekly_v2_top_n_ties_duplicates_and_input_permutation_are_deterministic(
    tmp_path: Path, admitted_artifact: object
) -> None:
    assert callable(admitted_artifact)
    highest = admitted_artifact(tmp_path, video_id="video-a", score=9.0)
    tied_first = admitted_artifact(tmp_path, video_id="video-b", score=8.0)
    tied_second = admitted_artifact(tmp_path, video_id="video-c", score=8.0)
    lowest = admitted_artifact(tmp_path, video_id="video-d", score=7.1)
    duplicate = highest
    forward = build_weekly_v2(
        (lowest, tied_second, highest, tied_first, duplicate),
        now=datetime(2026, 8, 30, tzinfo=UTC),
        timezone="Asia/Shanghai",
        top_n=3,
    )
    reverse = build_weekly_v2(
        (duplicate, tied_first, highest, tied_second, lowest),
        now=datetime(2026, 8, 30, tzinfo=UTC),
        timezone="Asia/Shanghai",
        top_n=3,
    )

    assert forward == reverse
    assert [item.video_id for item in forward.items] == [
        "video-a",
        "video-b",
        "video-c",
    ]
    assert render_weekly_v2(forward) == render_weekly_v2(reverse)


def test_selected_evidence_privacy_sentinel_is_absent_from_note_artifact_and_weekly(
    tmp_path: Path, admitted_artifact_bundle: object
) -> None:
    assert callable(admitted_artifact_bundle)
    secret = "SECRET_WEEKLY_UNSELECTED_TEXT"
    artifact, _source, _repository, _scoring_reader, _runtime = (
        admitted_artifact_bundle(tmp_path, public_description=secret)
    )
    report = build_weekly_v2(
        (artifact,),
        now=datetime(2026, 8, 30, tzinfo=UTC),
        timezone="Asia/Shanghai",
        top_n=10,
    )

    for value in (
        render_note_v2(artifact.note),
        repr(artifact),
        artifact.identity,
        artifact.deep_analysis_result_identity,
        repr(report),
        report.identity,
        render_weekly_v2(report),
    ):
        assert secret not in value
