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


# ---------------------------------------------------------------------------
# Correction Round 2 — Fix 2: reader must rederive request roots
# ---------------------------------------------------------------------------


def _forge_tampered_repair_graph(repository, tmp_path, tamper, forge_calls=None) -> None:
    """Persist a self-consistent forged repair graph with a tampered envelope.

    ``tamper`` mutates the parsed envelope dict in place.  The helper
    re-canonicalizes the tampered envelope, recomputes E and G so the forged
    artifacts are internally consistent (canonical + E + G all agree), persists
    them under the new G, and points the authoritative Job pointer at the forged
    structured artifact.  The persisted root CLAIMS (normalized_input_hash,
    request_hash, judge_h1/h2) are whatever the tamper leaves them as, so a test
    can make them inconsistent with the sealed semantic inputs.

    If the tamper changes the REPAIR/JUDGE request-hash claims, the persisted
    ProviderCall rows are re-keyed accordingly.  ``forge_calls``, when given,
    is invoked as ``forge_calls(connection, r, j, raw_artifact_id)`` to forge
    the persisted ProviderCall fields consistently with the forged envelope
    metadata; otherwise the rows are only rebound to the forged raw artifact.
    """

    from youtube_intel.h2_evidence import repair_persistence_graph_hash
    from youtube_intel.h2_jcs import jcs_loads_strict, jcs_serialize
    from youtube_intel.scoring import (
        build_repair_persistence_graph_identity,
        parse_repair_structured_key,
    )
    from youtube_intel.state import ArtifactWrite, RetentionClass, StorageRoot

    _claim_scoring_job(repository)
    entry = _entry(repository, tmp_path)
    entry.persist_success(_repair_success())
    job = repository.get_job("h2c-persist-job")
    structured_key = job.authoritative_scoring_artifact_key
    raw_key = structured_key.removesuffix("/structured") + "/raw"
    data_root = tmp_path / "data"
    raw_bytes = (data_root / f"{raw_key}.json").read_bytes()
    structured_bytes = (data_root / f"{structured_key}.json").read_bytes()
    p, _old_g = parse_repair_structured_key(structured_key)
    s_hash = hashlib.sha256(structured_bytes).hexdigest()
    original_raw = repository.get_artifact_by_key(raw_key)

    original_envelope = jcs_loads_strict(raw_bytes)
    original_r = original_envelope["repair_provider_evidence"]["request_hash"]
    original_j = original_envelope["repair_quality_evidence"]["judge_h2"]
    envelope = jcs_loads_strict(raw_bytes)
    tamper(envelope)
    tampered_bytes = jcs_serialize(envelope)
    new_e = hashlib.sha256(tampered_bytes).hexdigest()

    r = envelope["repair_provider_evidence"]["request_hash"]
    j = envelope["repair_quality_evidence"]["judge_h2"]
    settings_hash = hashlib.sha256(
        jcs_serialize(envelope["repair_provider_evidence"]["settings_provenance"])
    ).hexdigest()
    identity = build_repair_persistence_graph_identity(
        primary_request_hash=p,
        repair_request_hash=r,
        repair_judge_request_hash=j,
        settings_provenance_sha256=settings_hash,
        repair_envelope_sha256=new_e,
        structured_result_sha256=s_hash,
    )
    new_g = repair_persistence_graph_hash(identity)

    new_raw_key = f"scoring/{p}/repair/{new_g}/raw"
    new_structured_key = f"scoring/{p}/repair/{new_g}/structured"
    now = datetime(2026, 8, 26, 9, tzinfo=UTC)
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=f"repair-raw-{new_g}",
            artifact_key=new_raw_key,
            video_id=_VIDEO_ID,
            job_id="h2c-persist-job",
            kind=ArtifactKind.SCORING_RAW,
            storage_root=StorageRoot.DATA,
            relative_path=f"{new_raw_key}.json",
            content_hash=new_e,
            provider=original_raw.provider,
            model=original_raw.model,
            producer_version="scoring-raw-content-quality-repair-v1",
            retention_class=RetentionClass.RAW_RESPONSE_30D,
            expires_at=original_raw.expires_at,
        ),
        now=now,
    )
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=f"repair-structured-{new_g}",
            artifact_key=new_structured_key,
            video_id=_VIDEO_ID,
            job_id="h2c-persist-job",
            kind=ArtifactKind.SCORING_STRUCTURED,
            storage_root=StorageRoot.DATA,
            relative_path=f"{new_structured_key}.json",
            content_hash=s_hash,
            provider=original_raw.provider,
            model=original_raw.model,
            producer_version="scoring-structured-content-quality-repair-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=now,
    )
    (data_root / f"{new_raw_key}.json").parent.mkdir(parents=True, exist_ok=True)
    (data_root / f"{new_raw_key}.json").write_bytes(tampered_bytes)
    (data_root / f"{new_structured_key}.json").write_bytes(structured_bytes)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE jobs SET authoritative_scoring_artifact_key = :key "
            "WHERE job_id = 'h2c-persist-job'",
            {"key": new_structured_key},
        )
        # Re-key the persisted ProviderCall rows if the tamper changed the
        # request-hash claims, so the reader's lookup by the forged claims
        # resolves to the forged rows.
        if r != original_r:
            connection.execute(
                "UPDATE provider_calls SET request_hash = :new "
                "WHERE request_hash = :old",
                {"new": r, "old": original_r},
            )
        if j != original_j:
            connection.execute(
                "UPDATE provider_calls SET request_hash = :new "
                "WHERE request_hash = :old",
                {"new": j, "old": original_j},
            )
        new_raw_artifact_id = f"repair-raw-{new_g}"
        if forge_calls is not None:
            forge_calls(connection, r, j, new_raw_artifact_id)
        else:
            # Rebind the persisted REPAIR / REPAIR_JUDGE ProviderCall rows to
            # the forged raw artifact so the forged graph is internally
            # consistent.
            connection.execute(
                "UPDATE provider_calls SET response_artifact_id = :artifact_id "
                "WHERE request_hash = :request_hash",
                {"artifact_id": new_raw_artifact_id, "request_hash": r},
            )
            connection.execute(
                "UPDATE provider_calls SET response_artifact_id = :artifact_id "
                "WHERE request_hash = :request_hash",
                {"artifact_id": new_raw_artifact_id, "request_hash": j},
            )
    finally:
        connection.close()


def test_corrupted_sealed_repair_input_with_unchanged_root_fails_closed(
    tmp_path: Path,
) -> None:
    # Tamper the sealed normalized_input (semantic) but leave the persisted
    # normalized-input-root CLAIM unchanged; the rederived root must differ.
    def tamper(envelope):
        envelope["repair_provider_evidence"]["normalized_input"][
            "max_description_chars"
        ] = 9999

    repository = _setup_repository(tmp_path)
    _forge_tampered_repair_graph(repository, tmp_path, tamper)

    with pytest.raises(ValueError):
        _reader(repository, tmp_path).read(_VIDEO_ID)


def test_corrupted_stored_repair_root_claim_fails_closed(tmp_path: Path) -> None:
    # Tamper only the persisted normalized-input-root claim; the sealed
    # normalized_input is unchanged, so the rederived root mismatches the claim.
    def tamper(envelope):
        envelope["repair_provider_evidence"]["normalized_input_hash"] = "b" * 64

    repository = _setup_repository(tmp_path)
    _forge_tampered_repair_graph(repository, tmp_path, tamper)

    with pytest.raises(ValueError):
        _reader(repository, tmp_path).read(_VIDEO_ID)


def test_corrupted_stored_judge_h1_claim_fails_closed(tmp_path: Path) -> None:
    # Tamper only the persisted Judge H1 claim; the sealed Judge operation input
    # is unchanged, so the rederived H1 mismatches the claim.
    def tamper(envelope):
        envelope["repair_quality_evidence"]["judge_h1"] = "c" * 64

    repository = _setup_repository(tmp_path)
    _forge_tampered_repair_graph(repository, tmp_path, tamper)

    with pytest.raises(ValueError):
        _reader(repository, tmp_path).read(_VIDEO_ID)


def test_corrupted_sealed_judge_input_with_unchanged_h1_fails_closed(
    tmp_path: Path,
) -> None:
    # Tamper the sealed Judge operation input (semantic) but leave the persisted
    # H1 CLAIM unchanged; the rederived H1 must differ.
    def tamper(envelope):
        envelope["repair_quality_evidence"]["judge_operation_input"][
            "candidate_hash"
        ] = "d" * 64

    repository = _setup_repository(tmp_path)
    _forge_tampered_repair_graph(repository, tmp_path, tamper)

    with pytest.raises(ValueError):
        _reader(repository, tmp_path).read(_VIDEO_ID)


# ---------------------------------------------------------------------------
# Correction Round 3 — self-consistent forgery RED tests
# ---------------------------------------------------------------------------


def _forge_repair_metadata_field(tmp_path, field, forged_value):
    """Forge one RepairProviderEvidence identity field self-consistently.

    The sealed normalized_input is unchanged; the evidence metadata and the
    persisted REPAIR ProviderCall are forged together with a request hash
    recomputed consistently around the forged value.
    """

    from youtube_intel.state import build_provider_request_hash

    def tamper(envelope):
        pe = envelope["repair_provider_evidence"]
        pe[field] = forged_value
        pe["request_hash"] = build_provider_request_hash(
            operation=pe["operation"],
            normalized_input_hash=pe["normalized_input_hash"],
            provider=pe["provider"],
            model=pe["model"],
            prompt_version=pe["prompt_version"],
            schema_version=pe["operation_schema_version"],
        )

    def forge_calls(connection, r, j, raw_artifact_id):
        column = {
            "provider": "provider",
            "model": "model",
            "prompt_version": "prompt_version",
            "operation_schema_version": "schema_version",
        }[field]
        connection.execute(
            f"UPDATE provider_calls SET {column} = :value, "
            "response_artifact_id = :artifact_id WHERE request_hash = :r",
            {"value": forged_value, "artifact_id": raw_artifact_id, "r": r},
        )
        connection.execute(
            "UPDATE provider_calls SET response_artifact_id = :artifact_id "
            "WHERE request_hash = :j",
            {"artifact_id": raw_artifact_id, "j": j},
        )

    repository = _setup_repository(tmp_path)
    _forge_tampered_repair_graph(repository, tmp_path, tamper, forge_calls)
    return repository


@pytest.mark.parametrize(
    "field,forged_value",
    [
        ("model", "forged-repair-model"),
        ("provider", "forged-repair-provider"),
        ("prompt_version", "forged-prompt-v9"),
        ("operation_schema_version", "forged-schema-v9"),
    ],
)
def test_forged_repair_evidence_metadata_fails_closed(
    tmp_path: Path, field, forged_value
) -> None:
    repository = _forge_repair_metadata_field(tmp_path, field, forged_value)
    with pytest.raises(ValueError):
        _reader(repository, tmp_path).read(_VIDEO_ID)


def _forge_judge_metadata_field(tmp_path, field, forged_value):
    """Forge one JudgeEvidence identity field self-consistently.

    The sealed judge_operation_input is unchanged; the JudgeEvidence metadata
    and the persisted REPAIR_JUDGE ProviderCall are forged together.  The
    judge_h2 claim remains the valid derived value, so only the sealed-semantic
    cross-binding can reject.
    """

    def tamper(envelope):
        envelope["repair_quality_evidence"]["judge_evidence"][field] = forged_value

    def forge_calls(connection, r, j, raw_artifact_id):
        column = {
            "provider": "provider",
            "model": "model",
            "prompt_version": "prompt_version",
            "operation_schema_version": "schema_version",
        }[field]
        connection.execute(
            f"UPDATE provider_calls SET {column} = :value, "
            "response_artifact_id = :artifact_id WHERE request_hash = :j",
            {"value": forged_value, "artifact_id": raw_artifact_id, "j": j},
        )
        connection.execute(
            "UPDATE provider_calls SET response_artifact_id = :artifact_id "
            "WHERE request_hash = :r",
            {"artifact_id": raw_artifact_id, "r": r},
        )

    repository = _setup_repository(tmp_path)
    _forge_tampered_repair_graph(repository, tmp_path, tamper, forge_calls)
    return repository


@pytest.mark.parametrize(
    "field,forged_value",
    [
        ("model", "forged-judge-model"),
        ("provider", "forged-judge-provider"),
        ("prompt_version", "forged-judge-prompt-v9"),
        ("operation_schema_version", "forged-judge-schema-v9"),
    ],
)
def test_forged_judge_evidence_metadata_fails_closed(
    tmp_path: Path, field, forged_value
) -> None:
    repository = _forge_judge_metadata_field(tmp_path, field, forged_value)
    with pytest.raises(ValueError):
        _reader(repository, tmp_path).read(_VIDEO_ID)


def test_forged_judge_evidence_h2_claim_fails_closed(tmp_path: Path) -> None:
    # Forge only JudgeEvidence.judge_h2; everything else (including the
    # quality-evidence judge_h2 claim and the sealed operation input) stays
    # valid, so only the derived-H2 vs JudgeEvidence.judge_h2 comparison can
    # reject.
    def tamper(envelope):
        envelope["repair_quality_evidence"]["judge_evidence"]["judge_h2"] = "f" * 64

    repository = _setup_repository(tmp_path)
    _forge_tampered_repair_graph(repository, tmp_path, tamper)
    with pytest.raises(ValueError):
        _reader(repository, tmp_path).read(_VIDEO_ID)
