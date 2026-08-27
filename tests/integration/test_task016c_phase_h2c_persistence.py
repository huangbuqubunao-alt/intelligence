"""TASK-016C Phase H2-C — repair persistence boundary tests.

Focused integration tests for the TrustedPersistenceEntry repair path:
complete lineage graph registration, same-graph idempotency, committed-graph
corruption, orphan adoption/no-clobber, descriptor-anchored directory safety,
stale-lease no-mutation, and the PRIMARY v1/pre-lineage bookkeeping split.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.domain import JobStatus, PipelineStatus
from youtube_intel.pipeline import PipelineInterrupted
from youtube_intel.quality import (
    _JUDGE_PROVIDER,
    _QUALITY_JUDGE_OPERATION,
    _QUALITY_POLICY_VERSION,
    _QUALITY_PROMPT_VERSION,
    _QUALITY_PROVENANCE_AUTHORITY_SENTINEL,
    _QUALITY_SCHEMA_VERSION,
    _SCORING_PROMPT_VERSION,
    _SCORING_SCHEMA_VERSION,
    _TRUSTED_SCORING_CONTEXT_SENTINEL,
    _mint_quality_provenance_authority,
    _mint_trusted_scoring_context,
)
from youtube_intel.scoring import (
    H2CAuthoritativeGraphConflict,
    H2CStaleScoringLease,
    ScoringJobContext,
    ScoringPersistenceError,
    TrustedPersistenceEntry,
    _mint_phase_h_trusted_repair_success,
)
from youtube_intel.state import (
    ArtifactKind,
    JobType,
    ProcessingStage,
    SQLiteStateRepository,
)

_VIDEO_ID = "video-h2a"
_PIPELINE_VERSION = "runtime-v1"
_OWNER = "h2c-test-owner"
# The chain fixture model/digest (mirrors the H2-B finalizer fixture module).
_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + "a" * 64


def _load_module(name: str) -> Any:
    support_path = (
        Path(__file__).resolve().parents[1] / "unit" / f"{name}.py"
    )
    specification = importlib.util.spec_from_file_location(name, support_path)
    assert specification is not None and specification.loader is not None
    support = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = support
    specification.loader.exec_module(support)
    return support


def _authority() -> Any:
    return _mint_quality_provenance_authority(
        sentinel=_QUALITY_PROVENANCE_AUTHORITY_SENTINEL,
        judge_provider=_JUDGE_PROVIDER,
        judge_model=_MODEL,
        judge_model_digest=_DIGEST,
        scoring_schema_version=_SCORING_SCHEMA_VERSION,
        scoring_prompt_version=_SCORING_PROMPT_VERSION,
        quality_policy_version=_QUALITY_POLICY_VERSION,
        quality_schema_version=_QUALITY_SCHEMA_VERSION,
        quality_prompt_version=_QUALITY_PROMPT_VERSION,
        judge_operation=_QUALITY_JUDGE_OPERATION,
    )


def _scoring_context() -> Any:
    return _mint_trusted_scoring_context(
        sentinel=_TRUSTED_SCORING_CONTEXT_SENTINEL,
        scoring_provider=_JUDGE_PROVIDER,
        scoring_model=_MODEL,
        scoring_model_digest=_DIGEST,
        output_language="en",
        scoring_schema_version=_SCORING_SCHEMA_VERSION,
        scoring_prompt_version=_SCORING_PROMPT_VERSION,
        scoring_operation="local-scoring",
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )


def _repair_success(*, job_id: str = "h2c-persist-job") -> Any:
    """Mint one valid PhaseHTrustedRepairSuccess through the private seam."""

    data_layer = _load_module("test_task016c_phase_h2c_data_layer")
    chain = data_layer._valid_chain()
    envelope, envelope_bytes, _, _ = data_layer._build_envelope(chain)
    return _mint_phase_h_trusted_repair_success(
        job_id=job_id,
        owner=_OWNER,
        pipeline_version=_PIPELINE_VERSION,
        primary_request_hash=chain["trusted_context"].request_hash,
        primary_normalized_input_hash=(
            chain["trusted_context"].normalized_input_hash
        ),
        scoring_input_sha256=chain["trusted_context"].scoring_input_sha256,
        envelope=envelope,
        envelope_bytes=envelope_bytes,
        trusted_result=chain["finalization"].trusted_result,
        structured_bytes=chain["finalization"].structured_bytes,
    )


def _setup_repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    now = datetime(2026, 8, 26, 8, tzinfo=UTC)
    repository.initialize(now=now)
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO videos (video_id, channel_id, pipeline_status, "
            "pipeline_version, discovered_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                _VIDEO_ID,
                "channel-h2a",
                PipelineStatus.TRANSCRIPT_READY.value,
                _PIPELINE_VERSION,
                "2026-08-26T08:00:00.000000Z",
                "2026-08-26T08:00:00.000000Z",
            ),
        )
    finally:
        connection.close()
    return repository


def _claim_scoring_job(
    repository: SQLiteStateRepository,
    *,
    job_id: str = "h2c-persist-job",
    lease_minutes: int = 10,
) -> None:
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{_VIDEO_ID}:SCORING",
        video_id=_VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version=_PIPELINE_VERSION,
        max_attempts=3,
        available_at=datetime(2026, 8, 26, 8, tzinfo=UTC),
        now=datetime(2026, 8, 26, 8, tzinfo=UTC),
    )
    repository.claim_next_job(
        owner=_OWNER,
        lease_until=datetime.now(UTC) + timedelta(minutes=lease_minutes),
        now=datetime(2026, 8, 26, 8, tzinfo=UTC),
        video_id=_VIDEO_ID,
    )


def _entry(
    repository: SQLiteStateRepository, tmp_path: Path, *, job_id: str = "h2c-persist-job"
) -> TrustedPersistenceEntry:
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    return TrustedPersistenceEntry(
        repository=repository,
        data_root=data_root,
        quality_authority=_authority(),
        scoring_context=_scoring_context(),
        context=ScoringJobContext(
            job_id=job_id, owner=_OWNER, pipeline_version=_PIPELINE_VERSION
        ),
        summary_threshold=7.0,
    )


def test_repair_persist_writes_complete_lineage_graph(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()

    result = entry.persist_success(success)

    job = repository.get_job("h2c-persist-job")
    assert job is not None
    assert job.status is JobStatus.SUCCEEDED
    assert job.scoring_success_provenance == "REPAIR_H2C"
    assert job.scoring_lineage_version == "task016c-scoring-lineage-v1"
    structured_key = job.authoritative_scoring_artifact_key
    assert structured_key is not None
    assert result.job.job_id == job.job_id

    video = repository.get_video(_VIDEO_ID)
    assert video is not None
    assert video.pipeline_status is PipelineStatus.SCORED
    assert video.authoritative_scoring_job_id == job.job_id
    assert video.score == 8
    assert video.should_summarize is True

    raw_key = structured_key.removesuffix("/structured") + "/raw"
    raw = repository.get_artifact_by_key(raw_key)
    structured = repository.get_artifact_by_key(structured_key)
    assert raw is not None and structured is not None
    assert raw.kind is ArtifactKind.SCORING_RAW
    assert structured.kind is ArtifactKind.SCORING_STRUCTURED
    data_root = tmp_path / "data"
    raw_body = (data_root / raw.relative_path).read_bytes()
    structured_body = (data_root / structured.relative_path).read_bytes()
    assert hashlib.sha256(raw_body).hexdigest() == raw.content_hash == success.repair_composite_envelope_sha256
    assert hashlib.sha256(structured_body).hexdigest() == structured.content_hash == success.structured_sha256


def test_repair_persist_is_idempotent_for_same_graph(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    # Fix the clock so the time-dependent artifact expiry is identical across
    # both persists (same technique as the frozen Phase G harness).
    fixed_now = datetime.now(UTC)
    entry._clock = lambda: fixed_now
    success = _repair_success()

    first = entry.persist_success(success)
    job = repository.get_job("h2c-persist-job")
    structured_key = job.authoritative_scoring_artifact_key
    data_root = tmp_path / "data"
    structured = repository.get_artifact_by_key(structured_key)
    before = (data_root / structured.relative_path).stat().st_mtime_ns

    second = entry.persist_success(success)

    assert second.job.job_id == first.job.job_id
    assert second.video.authoritative_scoring_job_id == job.job_id
    assert (data_root / structured.relative_path).stat().st_mtime_ns == before


def test_repair_persist_rejects_corrupted_committed_graph(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    entry.persist_success(success)

    job = repository.get_job("h2c-persist-job")
    raw_key = job.authoritative_scoring_artifact_key.removesuffix(
        "/structured"
    ) + "/raw"
    raw = repository.get_artifact_by_key(raw_key)
    (tmp_path / "data" / raw.relative_path).write_bytes(b"tampered")

    with pytest.raises(H2CAuthoritativeGraphConflict):
        entry.persist_success(success)


def test_repair_persist_stale_lease_raises_without_mutation(
    tmp_path: Path,
) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository, lease_minutes=-1)
    entry = _entry(repository, tmp_path)
    success = _repair_success()

    with pytest.raises(H2CStaleScoringLease):
        entry.persist_success(success)

    job = repository.get_job("h2c-persist-job")
    assert job is not None
    assert job.status is JobStatus.RUNNING
    assert job.authoritative_scoring_artifact_key is None
    assert job.scoring_success_provenance is None
    assert list((tmp_path / "data").iterdir()) == []


def test_repair_persist_missing_job_interrupts(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    entry = _entry(repository, tmp_path, job_id="missing-job")
    success = _repair_success(job_id="missing-job")

    with pytest.raises(PipelineInterrupted):
        entry.persist_success(success)


def test_repair_persist_conflicting_orphan_fails_closed(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()

    # Compute the G-based raw path by persisting a plan through prewrite only.
    plan = entry._prewrite_validate_repair(success)
    raw_path = tmp_path / "data" / plan.raw_artifact.relative_path
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(b"conflicting orphan material")

    with pytest.raises(ScoringPersistenceError):
        entry.persist_success(success)
    assert repository.get_job("h2c-persist-job").status is JobStatus.RUNNING


def test_repair_persist_adopts_exact_orphan(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()

    plan = entry._prewrite_validate_repair(success)
    raw_path = tmp_path / "data" / plan.raw_artifact.relative_path
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(plan.envelope_bytes)

    entry.persist_success(success)

    job = repository.get_job("h2c-persist-job")
    assert job.status is JobStatus.SUCCEEDED
    assert raw_path.read_bytes() == plan.envelope_bytes


def test_repair_persist_rejects_symlinked_graph_component(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()

    plan = entry._prewrite_validate_repair(success)
    data_root = tmp_path / "data"
    scoring_dir = data_root / "scoring"
    scoring_dir.mkdir(parents=True, exist_ok=True)
    target = data_root / "elsewhere"
    target.mkdir()
    p_dir = scoring_dir / plan.primary_request_hash
    os.symlink(target, p_dir)

    with pytest.raises(ScoringPersistenceError):
        entry.persist_success(success)
    assert repository.get_job("h2c-persist-job").status is JobStatus.RUNNING


def test_repair_persist_rejects_fifo_graph_component(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()

    plan = entry._prewrite_validate_repair(success)
    data_root = tmp_path / "data"
    scoring_dir = data_root / "scoring"
    scoring_dir.mkdir(parents=True, exist_ok=True)
    os.mkfifo(scoring_dir / plan.primary_request_hash)

    with pytest.raises(ScoringPersistenceError):
        entry.persist_success(success)


def test_primary_persist_writes_lineage_for_v1_jobs_only(tmp_path: Path) -> None:
    phase_g = _load_module("test_task016c_phase_g")
    runtime, _ = phase_g._judge_runtime(tmp_path / "project")
    video_id = "video-lineage-v1"
    job_id = "job-lineage-v1"
    phase_g._setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    phase_g._setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = phase_g._committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    committer.persist_success(plan.success)

    job = runtime._repository.get_job(job_id)
    assert job.status is JobStatus.SUCCEEDED
    assert job.scoring_lineage_version == "task016c-scoring-lineage-v1"
    assert job.scoring_success_provenance == "PRIMARY"
    assert job.authoritative_scoring_artifact_key == (
        plan.structured_artifact.artifact_key
    )
    video = runtime._repository.get_video(video_id)
    assert video.authoritative_scoring_job_id == job_id
    assert video.pipeline_status is PipelineStatus.SCORED


def test_primary_persist_skips_lineage_for_pre_lineage_jobs(
    tmp_path: Path,
) -> None:
    phase_g = _load_module("test_task016c_phase_g")
    runtime, _ = phase_g._judge_runtime(tmp_path / "project")
    video_id = "video-lineage-null"
    job_id = "job-lineage-null"
    phase_g._setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    phase_g._setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    # Simulate a pre-v2 (pre-lineage) live SCORING job: generation stays NULL.
    connection = runtime._repository._connect()
    try:
        connection.execute(
            "UPDATE jobs SET scoring_lineage_version = NULL WHERE job_id = ?",
            (job_id,),
        )
    finally:
        connection.close()
    committer, plan = phase_g._committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )

    committer.persist_success(plan.success)

    job = runtime._repository.get_job(job_id)
    assert job.status is JobStatus.SUCCEEDED
    assert job.scoring_lineage_version is None
    assert job.scoring_success_provenance is None
    assert job.authoritative_scoring_artifact_key is None
    video = runtime._repository.get_video(video_id)
    assert video.authoritative_scoring_job_id is None
    assert video.pipeline_status is PipelineStatus.SCORED


def test_retry_excludes_trust_integrity_invalid_by_code_alone(
    tmp_path: Path,
) -> None:
    final_correction = _load_module("test_task016c_phase_h2b_final_correction")
    runtime, job = final_correction._terminal_job(
        tmp_path,
        error_code="TRUST_INTEGRITY_INVALID",
        message="H2C_REPLAY_INVALID:PRIMARY_EVIDENCE_MISMATCH",
        job_id="trust-job",
    )

    outcome = runtime.retry(video=None, failed_only=False)

    assert outcome.safe_message == (
        "No final failed video job is available to retry."
    )
    saved = runtime._repository.get_job(job.job_id)
    assert saved is not None
    assert saved.status is JobStatus.FAILED_FINAL
    # A different diagnostic detail under the same code is excluded too.
    runtime2, job2 = final_correction._terminal_job(
        tmp_path / "other",
        error_code="TRUST_INTEGRITY_INVALID",
        message="H2C_REPLAY_INVALID:ENVELOPE_OVERSIZE",
        job_id="trust-job-2",
    )
    outcome2 = runtime2.retry(video=None, failed_only=False)
    assert outcome2.safe_message == (
        "No final failed video job is available to retry."
    )
    assert runtime2._repository.get_job(job2.job_id).status is JobStatus.FAILED_FINAL


# ---------------------------------------------------------------------------
# Authoritative scoring reader
# ---------------------------------------------------------------------------


from youtube_intel.scoring import AuthoritativeScoringReader  # noqa: E402


def _reader(repository: SQLiteStateRepository, tmp_path: Path) -> AuthoritativeScoringReader:
    return AuthoritativeScoringReader(
        repository=repository,
        data_root=tmp_path / "data",
        summary_threshold=7.0,
        pipeline_version=_PIPELINE_VERSION,
        current_model=_MODEL,
        current_output_language="en",
    )


def test_reader_returns_verified_repair_read(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    entry.persist_success(_repair_success())

    read = _reader(repository, tmp_path).read(_VIDEO_ID)

    assert read.video_id == _VIDEO_ID
    assert read.scoring_job_id == "h2c-persist-job"
    assert read.scoring_success_provenance == "REPAIR_H2C"
    assert read.scoring_outcome.result.score == 8
    assert read.scoring_outcome.decision.final_should_summarize is True


def test_reader_legacy_pointerless_read_requires_null_generation(
    tmp_path: Path,
) -> None:
    phase_g = _load_module("test_task016c_phase_g")
    runtime, _ = phase_g._judge_runtime(tmp_path / "project")
    video_id = "video-reader-legacy"
    job_id = "job-reader-legacy"
    phase_g._setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    phase_g._setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    # Simulate a pre-v2 live job: NULL generation, then PRIMARY success.
    connection = runtime._repository._connect()
    try:
        connection.execute(
            "UPDATE jobs SET scoring_lineage_version = NULL WHERE job_id = ?",
            (job_id,),
        )
    finally:
        connection.close()
    committer, plan = phase_g._committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    committer.persist_success(plan.success)

    read = runtime._scoring_reader().read(video_id)

    assert read.scoring_job_id == job_id
    assert read.scoring_success_provenance is None
    assert read.scoring_outcome.result.request_hash == (
        plan.scoring_call_request.request_hash
    )


def test_reader_rejects_v1_downgrade_through_legacy_branch(
    tmp_path: Path,
) -> None:
    # Persist a v1 PRIMARY success, then remove the Video pointer so only the
    # legacy (latest-artifact) selection could reach it; the reader must fail
    # closed rather than downgrade a v1 result through the legacy path.
    phase_g = _load_module("test_task016c_phase_g")
    runtime, _ = phase_g._judge_runtime(tmp_path / "project")
    video_id = "video-reader-nodowngrade"
    job_id = "job-reader-nodowngrade"
    phase_g._setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    phase_g._setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    committer, plan = phase_g._committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    committer.persist_success(plan.success)
    connection = runtime._repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET authoritative_scoring_job_id = NULL "
            "WHERE video_id = ?",
            (video_id,),
        )
    finally:
        connection.close()

    with pytest.raises(ValueError):
        runtime._scoring_reader().read(video_id)


def test_reader_rejects_pointer_with_null_generation(tmp_path: Path) -> None:
    # A non-NULL Video pointer whose Job has a NULL lineage version is
    # malformed and fails closed (no legacy fallback).
    phase_g = _load_module("test_task016c_phase_g")
    runtime, _ = phase_g._judge_runtime(tmp_path / "project")
    video_id = "video-reader-nullgen"
    job_id = "job-reader-nullgen"
    phase_g._setup_transcript_ready_video(
        runtime._repository, runtime._data_root, video_id=video_id
    )
    phase_g._setup_scoring_job(
        runtime._repository, video_id=video_id, job_id=job_id
    )
    connection = runtime._repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET authoritative_scoring_job_id = ? WHERE video_id = ?",
            (job_id, video_id),
        )
    finally:
        connection.close()

    with pytest.raises(ValueError):
        runtime._scoring_reader().read(video_id)


# ---------------------------------------------------------------------------
# Correction Round 1 — Fix 2: final-name FIFO / special-file safe inspection
# ---------------------------------------------------------------------------


def _repair_plan_paths(entry, success):
    plan = entry._prewrite_validate_repair(success)
    data_root = entry._data_root
    raw_path = data_root / plan.raw_artifact.relative_path
    structured_path = data_root / plan.structured_artifact.relative_path
    return plan, raw_path, structured_path


def _run_bounded(fn, *, timeout: float = 20.0):
    """Run fn in a daemon thread; fail the test if it blocks past timeout.

    A blocking ``open`` on a FIFO final would hang the worker thread, so a
    live thread after the join proves a blocking open path (no sleeps).
    """

    import threading

    result: dict = {}

    def target() -> None:
        try:
            result["value"] = fn()
        except Exception as exc:  # noqa: BLE001
            result["error"] = exc

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise AssertionError(
            "repair persistence blocked on a special file (possible blocking open)"
        )
    if "error" in result:
        raise result["error"]
    return result.get("value")


def test_final_raw_fifo_rejects_without_blocking(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, _ = _repair_plan_paths(entry, success)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(raw_path)

    with pytest.raises(ScoringPersistenceError):
        _run_bounded(lambda: entry.persist_success(success))
    assert repository.get_job("h2c-persist-job").status is JobStatus.RUNNING


def test_final_structured_fifo_rejects_without_blocking(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, _, structured_path = _repair_plan_paths(entry, success)
    structured_path.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(structured_path)

    with pytest.raises(ScoringPersistenceError):
        _run_bounded(lambda: entry.persist_success(success))
    assert repository.get_job("h2c-persist-job").status is JobStatus.RUNNING


def test_final_name_symlink_rejected(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, _ = _repair_plan_paths(entry, success)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    target = raw_path.parent / "elsewhere-target"
    target.write_bytes(b"not the repair envelope")
    os.symlink(target, raw_path)

    with pytest.raises(ScoringPersistenceError):
        _run_bounded(lambda: entry.persist_success(success))


def test_final_name_directory_rejected(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, _ = _repair_plan_paths(entry, success)
    raw_path.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ScoringPersistenceError):
        _run_bounded(lambda: entry.persist_success(success))


def test_exact_orphan_adoption_still_works_with_safe_inspection(
    tmp_path: Path,
) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, _ = _repair_plan_paths(entry, success)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(plan.envelope_bytes)

    _run_bounded(lambda: entry.persist_success(success))

    job = repository.get_job("h2c-persist-job")
    assert job.status is JobStatus.SUCCEEDED
    assert raw_path.read_bytes() == plan.envelope_bytes


def test_conflicting_regular_final_still_conflicts(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, _ = _repair_plan_paths(entry, success)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(b"conflicting regular bytes")

    with pytest.raises(ScoringPersistenceError):
        _run_bounded(lambda: entry.persist_success(success))
    assert repository.get_job("h2c-persist-job").status is JobStatus.RUNNING


# ---------------------------------------------------------------------------
# Correction Round 1 — Fix 3: repair ProviderCall identity revalidation
# ---------------------------------------------------------------------------


def _persisted_repair_graph(repository, tmp_path):
    """Persist one repair graph and return the sealed R/J request hashes."""

    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    entry.persist_success(_repair_success())
    job = repository.get_job("h2c-persist-job")
    structured_key = job.authoritative_scoring_artifact_key
    raw_key = structured_key.removesuffix("/structured") + "/raw"
    from youtube_intel.h2_jcs import jcs_loads_strict

    raw_body = (tmp_path / "data" / f"{raw_key}.json").read_bytes()
    envelope = jcs_loads_strict(raw_body)
    r_hash = envelope["repair_provider_evidence"]["request_hash"]
    j_hash = envelope["repair_quality_evidence"]["judge_h2"]
    return r_hash, j_hash


def _corrupt_provider_call(repository, request_hash: str, column: str, value) -> None:
    connection = repository._connect()
    try:
        connection.execute(
            f"UPDATE provider_calls SET {column} = :value "
            "WHERE request_hash = :request_hash",
            {"value": value, "request_hash": request_hash},
        )
    finally:
        connection.close()


@pytest.mark.parametrize(
    "column,value",
    [
        ("provider", "forged-provider"),
        ("model", "forged-model"),
        ("prompt_version", "forged-prompt-v9"),
        ("schema_version", "forged-schema-v9"),
        ("request_hash", "e" * 64),
        ("response_artifact_id", None),
    ],
)
def test_repair_provider_call_corruption_fails_closed(
    tmp_path: Path, column: str, value
) -> None:
    repository = _setup_repository(tmp_path)
    r_hash, _ = _persisted_repair_graph(repository, tmp_path)
    _corrupt_provider_call(repository, r_hash, column, value)

    with pytest.raises(ValueError):
        _reader(repository, tmp_path).read(_VIDEO_ID)


@pytest.mark.parametrize(
    "column,value",
    [
        ("provider", "forged-provider"),
        ("model", "forged-model"),
        ("prompt_version", "forged-prompt-v9"),
        ("schema_version", "forged-schema-v9"),
        ("request_hash", "f" * 64),
        ("response_artifact_id", None),
    ],
)
def test_repair_judge_provider_call_corruption_fails_closed(
    tmp_path: Path, column: str, value
) -> None:
    repository = _setup_repository(tmp_path)
    _, j_hash = _persisted_repair_graph(repository, tmp_path)
    _corrupt_provider_call(repository, j_hash, column, value)

    with pytest.raises(ValueError):
        _reader(repository, tmp_path).read(_VIDEO_ID)


def test_uncorrupted_repair_read_still_succeeds(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _persisted_repair_graph(repository, tmp_path)

    read = _reader(repository, tmp_path).read(_VIDEO_ID)

    assert read.scoring_success_provenance == "REPAIR_H2C"
    assert read.scoring_outcome.result.score == 8


# ---------------------------------------------------------------------------
# Correction Round 2 — Fix 1: temporary verification reopen special-file race
# ---------------------------------------------------------------------------


def _install_tmp_replacement_hook(
    monkeypatch, tmp_abs_path: Path, make_special
) -> None:
    """Swap the deterministic .tmp name for a special file at verification reopen.

    The hook intercepts ``os.open`` and, on the first O_RDONLY open of the
    ``.tmp`` name (the verification reopen after write/close), replaces the
    legitimate regular temporary file with a special file and delegates to the
    real ``os.open``.  This reproduces the close->reopen replacement race
    deterministically (no timing sleeps).
    """

    real_open = os.open
    state = {"swapped": False}

    def hooked_open(path, flags, *args, **kwargs):
        if (
            not state["swapped"]
            and isinstance(path, str)
            and path.endswith(".tmp")
            and (flags & os.O_ACCMODE) == os.O_RDONLY
        ):
            state["swapped"] = True
            os.unlink(tmp_abs_path)
            make_special(tmp_abs_path)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", hooked_open)


def _setup_materialize(entry, success):
    plan, raw_path, structured_path = _repair_plan_paths(entry, success)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    return plan, raw_path, structured_path


def test_temp_raw_fifo_replacement_before_verification_fails_closed(
    tmp_path: Path, monkeypatch
) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, _ = _setup_materialize(entry, success)
    tmp_abs = raw_path.parent / (raw_path.name + ".tmp")
    _install_tmp_replacement_hook(monkeypatch, tmp_abs, os.mkfifo)

    try:
        with pytest.raises(ScoringPersistenceError):
            _run_bounded(lambda: entry._materialize_repair_files(plan), timeout=8)
    finally:
        if tmp_abs.exists() or tmp_abs.is_fifo():
            tmp_abs.unlink()
    # The malicious replacement must not have been published.
    assert not raw_path.exists()
    assert repository.get_job("h2c-persist-job").status is JobStatus.RUNNING


def test_temp_structured_fifo_replacement_before_verification_fails_closed(
    tmp_path: Path, monkeypatch
) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, structured_path = _setup_materialize(entry, success)
    # Let raw publish normally; only race the structured temp.
    entry._write_repair_final_in_directory(
        _open_g_fd(entry, plan),
        name=raw_path.name,
        content=plan.envelope_bytes,
        expected_hash=plan.envelope_hash,
        video_id=_VIDEO_ID,
    )
    tmp_abs = structured_path.parent / (structured_path.name + ".tmp")
    _install_tmp_replacement_hook(monkeypatch, tmp_abs, os.mkfifo)

    try:
        with pytest.raises(ScoringPersistenceError):
            _run_bounded(
                lambda: entry._write_repair_final_in_directory(
                    _open_g_fd(entry, plan),
                    name=structured_path.name,
                    content=plan.structured_bytes,
                    expected_hash=plan.structured_hash,
                    video_id=_VIDEO_ID,
                ),
                timeout=8,
            )
    finally:
        if tmp_abs.exists() or tmp_abs.is_fifo():
            tmp_abs.unlink()
    assert not structured_path.exists()


def _open_g_fd(entry, plan) -> int:
    return entry._open_repair_graph_directory(
        p=plan.primary_request_hash, g=plan.graph_hash, video_id=_VIDEO_ID
    )


def test_temp_symlink_replacement_before_verification_fails_closed(
    tmp_path: Path, monkeypatch
) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, _ = _setup_materialize(entry, success)
    tmp_abs = raw_path.parent / (raw_path.name + ".tmp")
    target = raw_path.parent / "symlink-target"
    target.write_bytes(b"malicious")
    _install_tmp_replacement_hook(
        monkeypatch, tmp_abs, lambda p: os.symlink(target, p)
    )

    with pytest.raises(ScoringPersistenceError):
        _run_bounded(lambda: entry._materialize_repair_files(plan))
    assert not raw_path.exists()


def test_temp_directory_replacement_before_verification_fails_closed(
    tmp_path: Path, monkeypatch
) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, _ = _setup_materialize(entry, success)
    tmp_abs = raw_path.parent / (raw_path.name + ".tmp")
    _install_tmp_replacement_hook(monkeypatch, tmp_abs, os.mkdir)

    with pytest.raises(ScoringPersistenceError):
        _run_bounded(lambda: entry._materialize_repair_files(plan))
    assert not raw_path.exists()


def test_temp_regular_verification_still_succeeds(tmp_path: Path) -> None:
    repository = _setup_repository(tmp_path)
    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    success = _repair_success()
    plan, raw_path, structured_path = _repair_plan_paths(entry, success)

    _run_bounded(lambda: entry._materialize_repair_files(plan))

    assert raw_path.read_bytes() == plan.envelope_bytes
    assert structured_path.read_bytes() == plan.structured_bytes
