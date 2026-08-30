"""Offline construction support for TASK-016E/F boundary tests only."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest


def _load_module(name: str) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    root = Path(__file__).resolve().parent
    for directory in ("unit", "integration"):
        candidate = root / directory / f"{name}.py"
        if candidate.exists():
            specification = importlib.util.spec_from_file_location(name, candidate)
            assert specification is not None and specification.loader is not None
            module = importlib.util.module_from_spec(specification)
            sys.modules[name] = module
            specification.loader.exec_module(module)
            return module
    raise FileNotFoundError(name)


def _admitted_artifact_bundle(
    tmp_path: Path,
    *,
    video_id: str = "video-016ef",
    completed_at: datetime | None = None,
    score: float = 8.0,
    public_description: str = "Selected evidence only.",
) -> tuple[Any, Any, Any, Any, Any]:
    phase_g = _load_module("test_task016c_phase_g")
    runtime, _ = phase_g._judge_runtime(tmp_path / video_id / "project")
    repository = runtime._repository
    job_id = f"job-{video_id}"
    phase_g._setup_transcript_ready_video(
        repository, runtime._data_root, video_id=video_id
    )
    phase_g._setup_scoring_job(repository, video_id=video_id, job_id=job_id)
    scoring_input = phase_g._scoring_input(video_id=video_id)
    attempt = phase_g._build_attempt(
        scoring_input=scoring_input,
        raw=phase_g._raw_response(phase_g._candidate_fields(score=score)),
    )
    success = runtime._run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input, admission=phase_g._h1_admission()
    )
    entry = runtime._trusted_persistence_entry(
        job_id=job_id, owner="test-owner", pipeline_version="runtime-v1"
    )
    committer = phase_g._TestPersistenceHarness(entry)
    plan = committer.prewrite_validate(success)
    committer.persist_success(plan.success)
    weekly = _load_module("test_task016c_phase_h2c_weekly")
    weekly._complete_video_for_weekly(
        repository,
        video_id=video_id,
        vault_root=tmp_path / video_id / "project" / "vault",
        vault_subdir="Knowledge",
    )
    if completed_at is not None:
        connection = repository._connect()
        try:
            connection.execute(
                "UPDATE videos SET completed_at = ? WHERE video_id = ?",
                (completed_at.isoformat().replace("+00:00", "Z"), video_id),
            )
        finally:
            connection.close()
    scoring_reader = runtime._scoring_reader()
    source_support = _load_module("test_deep_analysis_persistence")
    source = source_support._trusted_success(
        public_description=public_description,
        verified_scoring_read=scoring_reader.read(video_id),
    )
    artifact = runtime.build_verified_note_v2_artifact(source)
    return artifact, source, repository, scoring_reader, runtime


@pytest.fixture
def admitted_artifact_bundle() -> Callable[..., tuple[Any, Any, Any, Any, Any]]:
    return _admitted_artifact_bundle


@pytest.fixture
def admitted_artifact(
    admitted_artifact_bundle: Callable[..., tuple[Any, Any, Any, Any, Any]],
) -> Callable[..., Any]:
    def build(
        tmp_path: Path,
        *,
        video_id: str = "video-016ef",
        completed_at: datetime | None = None,
        score: float = 8.0,
        public_description: str = "Selected evidence only.",
    ) -> Any:
        return admitted_artifact_bundle(
            tmp_path,
            video_id=video_id,
            completed_at=completed_at,
            score=score,
            public_description=public_description,
        )[0]

    return build
