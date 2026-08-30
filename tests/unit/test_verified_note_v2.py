"""TASK-016E/F verified Note V2 aggregation handoff contract."""

from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

import youtube_intel.verified_note_v2 as verified_note_v2
from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
from youtube_intel.verified_note_v2 import (
    VerifiedNoteV2ArtifactError,
    verify_verified_note_v2_artifact,
)
from youtube_intel.weekly_v2 import build_weekly_v2


def test_boundary_is_available_only_from_runtime_owned_composition(
    tmp_path: Path, admitted_artifact_bundle: object
) -> None:
    assert callable(admitted_artifact_bundle)
    artifact, source, _repository, _scoring_reader, runtime = admitted_artifact_bundle(
        tmp_path
    )

    assert verify_verified_note_v2_artifact(artifact)
    assert callable(runtime.build_verified_note_v2_artifact)
    with pytest.raises(VerifiedNoteV2ArtifactError, match="runtime-owned composition"):
        runtime.__class__.build_verified_note_v2_artifact(
            object.__new__(runtime.__class__), source
        )


def test_public_boundary_exposes_no_admission_or_metadata_minting_seam(
    tmp_path: Path, admitted_artifact_bundle: object
) -> None:
    assert callable(admitted_artifact_bundle)
    _artifact, _source, _repository, _scoring_reader, runtime = (
        admitted_artifact_bundle(tmp_path)
    )

    assert not hasattr(runtime, "_verified_note_v2_admit")
    assert not hasattr(runtime, "_verified_note_v2_build")
    assert not hasattr(verified_note_v2, "create_verified_note_v2_artifact_boundary")
    assert not hasattr(verified_note_v2, "_build_from_authorities")
    assert not hasattr(verified_note_v2, "_make_boundary_authority")
    assert tuple(
        inspect.signature(runtime.build_verified_note_v2_artifact).parameters
    ) == ("source",)

    class CallerCreatedRuntime:
        pass

    with pytest.raises(RuntimeError, match="requires RuntimeOperations"):
        verified_note_v2._bind_verified_note_v2_runtime(CallerCreatedRuntime)


def test_note_identity_is_stable_when_authoritative_weekly_only_metadata_changes(
    tmp_path: Path, admitted_artifact_bundle: object
) -> None:
    assert callable(admitted_artifact_bundle)
    first, source, repository, _scoring_reader, runtime = admitted_artifact_bundle(
        tmp_path
    )
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET completed_at = ? WHERE video_id = ?",
            ("2026-08-31T12:00:00Z", first.video_id),
        )
    finally:
        connection.close()
    second = runtime.build_verified_note_v2_artifact(source)

    assert first.note.identity == second.note.identity
    assert first.identity != second.identity


def test_lookalike_and_url_tampering_cannot_cross_process_local_admission(
    tmp_path: Path, admitted_artifact_bundle: object
) -> None:
    assert callable(admitted_artifact_bundle)
    artifact, _source, _repository, _scoring_reader, _runtime = (
        admitted_artifact_bundle(tmp_path)
    )

    assert not verify_verified_note_v2_artifact(replace(artifact))
    assert not verify_verified_note_v2_artifact(
        replace(artifact, source_url="https://attacker.invalid/forged")
    )


def test_fake_score_date_or_url_are_not_supported_builder_inputs(
    tmp_path: Path, admitted_artifact_bundle: object
) -> None:
    assert callable(admitted_artifact_bundle)
    artifact, source, _repository, _scoring_reader, runtime = admitted_artifact_bundle(
        tmp_path
    )

    assert "score" not in runtime.build_verified_note_v2_artifact.__annotations__
    assert "completed_at" not in runtime.build_verified_note_v2_artifact.__annotations__
    assert "source_url" not in runtime.build_verified_note_v2_artifact.__annotations__
    assert runtime.build_verified_note_v2_artifact(source) == artifact


def test_runtime_boundary_ignores_caller_mutated_repository_and_reader_instances(
    tmp_path: Path, admitted_artifact_bundle: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert callable(admitted_artifact_bundle)
    artifact, source, repository, _scoring_reader, runtime = admitted_artifact_bundle(
        tmp_path
    )

    def forged_lookup(_video_id: str) -> object:
        raise AssertionError(
            "runtime-owned boundary must not use caller-mutated repository"
        )

    monkeypatch.setattr(repository, "get_video", forged_lookup)
    monkeypatch.setattr(
        runtime,
        "_scoring_reader",
        lambda: (_ for _ in ()).throw(
            AssertionError("runtime-owned boundary must not use caller-mutated reader")
        ),
    )

    assert runtime.build_verified_note_v2_artifact(source) == artifact


def test_live_and_verified_persisted_sources_produce_equivalent_weekly_v2(
    tmp_path: Path, admitted_artifact_bundle: object
) -> None:
    assert callable(admitted_artifact_bundle)
    live, source, repository, _scoring_reader, runtime = admitted_artifact_bundle(
        tmp_path
    )
    persisted = DeepAnalysisPersistenceStore(
        repository
    ).persist_trusted_deep_analysis_success(
        success=source, now=datetime(2026, 8, 30, tzinfo=UTC)
    )
    rehydrated = runtime.build_verified_note_v2_artifact(persisted)
    now = datetime(2026, 8, 27, tzinfo=UTC)
    live_weekly = build_weekly_v2((live,), now=now, timezone="Asia/Shanghai", top_n=10)
    persisted_weekly = build_weekly_v2(
        (rehydrated,), now=now, timezone="Asia/Shanghai", top_n=10
    )

    assert rehydrated == live
    assert persisted_weekly == live_weekly
