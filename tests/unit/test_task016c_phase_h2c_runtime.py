"""TASK-016C Phase H2-C — runtime generation decision and replay tests.

Covers the post-H2-B-PASS generation decision point (NULL capability
terminal, v1 entry, unknown non-NULL integrity terminal), the closed
SCORING_LINEAGE_VERSION_INVALID diagnostic, H2-C entry gating, replay
tamper fail-closed behavior, the settings admission ceiling, and the
code-only retry exclusion.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

import youtube_intel.runtime as runtime_module
from youtube_intel.domain import JobStatus, ProcessingStage
from youtube_intel.state import SCORING_LINEAGE_VERSION_V1


def _load_flow() -> Any:
    support_path = (
        Path(__file__).resolve().parents[1] / "unit"
        / "test_task016c_phase_h2b_repair_flow.py"
    )
    specification = importlib.util.spec_from_file_location(
        "test_task016c_phase_h2b_repair_flow", support_path
    )
    assert specification is not None and specification.loader is not None
    if specification.name in sys.modules:
        return sys.modules[specification.name]
    support = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = support
    specification.loader.exec_module(support)
    return support


def _override_scoring_generation(runtime: Any, generation: str | None) -> None:
    """Force the generation written for newly created SCORING jobs (NULL only).

    The schema CHECK admits NULL or v1 at write time, so this DB-level override
    is used for the pre-lineage NULL case.
    """

    repository = runtime._repository
    original = repository.create_job

    def create_job(**kwargs: Any) -> Any:
        job = original(**kwargs)
        if job.target_stage is ProcessingStage.SCORING:
            connection = repository._connect()
            try:
                connection.execute(
                    "UPDATE jobs SET scoring_lineage_version = ? "
                    "WHERE job_id = ?",
                    (generation, job.job_id),
                )
            finally:
                connection.close()
            job = repository.get_job(job.job_id)
        return job

    repository.create_job = create_job


def _patch_read_generation(runtime: Any, generation: str) -> None:
    """Inject an unknown generation at read time.

    The schema CHECK admits only NULL or v1 at write time, so an unknown
    non-NULL generation (a defensive/corruption state) is simulated by
    overriding ``scoring_lineage_version`` on every record returned by
    ``get_job`` while preserving all other fields.
    """

    import dataclasses

    repository = runtime._repository
    original_get_job = repository.get_job

    def get_job(job_id: str) -> Any:
        job = original_get_job(job_id)
        if job is None or job.target_stage is not ProcessingStage.SCORING:
            return job
        return dataclasses.replace(job, scoring_lineage_version=generation)

    repository.get_job = get_job


def _repair_pass_script(flow: Any) -> list:
    return flow._repair_script(
        primary_inner="{not-json",
        repair_inner=flow._valid_candidate(),
        judge_status="PASS",
    )


def test_pre_lineage_live_job_pass_keeps_capability_terminal(
    tmp_path: Path,
) -> None:
    flow = _load_flow()
    transport = flow._FakeTransport(_repair_pass_script(flow))
    runtime = flow._runtime(tmp_path, transport)
    _override_scoring_generation(runtime, None)

    flow._run_process(runtime)

    # A NULL-generation (pre-lineage) live SCORING job never enters H2-C:
    # the frozen compatibility terminal remains exact.
    assert transport.tags_calls == 3
    assert transport.generate_calls == 3
    job = flow._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "CAPABILITY_UNAVAILABLE"
    assert job.last_error_message == "H2B_PASS_AWAITING_H2C"
    assert job.scoring_lineage_version is None
    assert job.scoring_success_provenance is None
    assert job.authoritative_scoring_artifact_key is None
    video = runtime._repository.get_video(flow.VIDEO_ID)
    assert video.authoritative_scoring_job_id is None


def test_unknown_generation_terminalizes_with_closed_qualified_detail(
    tmp_path: Path,
) -> None:
    flow = _load_flow()
    transport = flow._FakeTransport(_repair_pass_script(flow))
    runtime = flow._runtime(tmp_path, transport)
    _patch_read_generation(runtime, "task016c-scoring-lineage-v9")

    flow._run_process(runtime)

    job = flow._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "TRUST_INTEGRITY_INVALID"
    assert (
        job.last_error_message
        == "H2C_REPLAY_INVALID:SCORING_LINEAGE_VERSION_INVALID"
    )
    # No legacy fallback, no H2-C entry, no repair persistence.
    assert job.scoring_success_provenance is None
    assert job.authoritative_scoring_artifact_key is None
    video = runtime._repository.get_video(flow.VIDEO_ID)
    assert video.authoritative_scoring_job_id is None
    # The unqualified legacy detail is never emitted.
    assert job.last_error_message != "H2C_SCORING_LINEAGE_VERSION_INVALID"
    # Code-only retry exclusion: the terminal job is never resurrected.
    outcome = runtime.retry(video=None, failed_only=False)
    assert outcome.safe_message == (
        "No final failed video job is available to retry."
    )
    assert runtime._repository.get_job(job.job_id).status is JobStatus.FAILED_FINAL


def test_only_v1_generation_enters_h2c(tmp_path: Path) -> None:
    flow = _load_flow()
    transport = flow._FakeTransport(_repair_pass_script(flow))
    runtime = flow._runtime(tmp_path, transport)

    flow._run_process(runtime)

    job = flow._scoring_job(runtime)
    assert job.scoring_lineage_version == SCORING_LINEAGE_VERSION_V1
    assert job.status is JobStatus.SUCCEEDED
    assert job.scoring_success_provenance == "REPAIR_H2C"


def test_replay_judge_evidence_tamper_fails_closed(tmp_path: Path) -> None:
    flow = _load_flow()
    transport = flow._FakeTransport(_repair_pass_script(flow))
    runtime = flow._runtime(tmp_path, transport)

    def _exploding_replay(*args: Any, **kwargs: Any) -> None:
        raise ValueError("injected judge evidence tamper")

    original = runtime_module.verify_judge_evidence_replay
    runtime_module.verify_judge_evidence_replay = _exploding_replay
    try:
        flow._run_process(runtime)
    finally:
        runtime_module.verify_judge_evidence_replay = original

    # The replay fails closed with the closed diagnostic; no second dispatch.
    assert transport.tags_calls == 3
    assert transport.generate_calls == 3
    job = flow._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "TRUST_INTEGRITY_INVALID"
    assert job.last_error_message == "H2C_REPLAY_INVALID:JUDGE_EVIDENCE_INVALID"
    assert job.authoritative_scoring_artifact_key is None


def test_replay_attestation_tamper_fails_closed(tmp_path: Path) -> None:
    flow = _load_flow()
    transport = flow._FakeTransport(_repair_pass_script(flow))
    runtime = flow._runtime(tmp_path, transport)

    def _exploding_replay(*args: Any, **kwargs: Any) -> None:
        raise ValueError("injected attestation tamper")

    original = runtime_module.verify_quality_pass_attestation
    runtime_module.verify_quality_pass_attestation = _exploding_replay
    try:
        flow._run_process(runtime)
    finally:
        runtime_module.verify_quality_pass_attestation = original

    job = flow._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "TRUST_INTEGRITY_INVALID"
    assert job.last_error_message == "H2C_REPLAY_INVALID:ATTESTATION_INVALID"


def test_settings_bound_exceeded_terminalizes(tmp_path: Path) -> None:
    flow = _load_flow()
    project = flow._project(tmp_path)
    settings_path = project / "config" / "settings.yaml"
    settings_path.write_text(
        settings_path.read_text(encoding="utf-8").replace(
            "max_transcript_chars: 64", "max_transcript_chars: 131073"
        ),
        encoding="utf-8",
    )
    from youtube_intel.config import load_app_config
    from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations

    config = load_app_config(
        channels_path=project / "config" / "channels.yaml",
        settings_path=settings_path,
    )
    assert config.settings.local_scoring.max_transcript_chars == 131073
    from importlib import resources

    from youtube_intel.providers.ollama import (
        OllamaQualityJudgeProvider,
        OllamaScoringProvider,
    )

    prompt = resources.files("youtube_intel").joinpath(
        "prompts", "scoring.md"
    ).read_text(encoding="utf-8")
    transport = flow._FakeTransport(_repair_pass_script(flow))
    runtime = RuntimeOperations(
        config=config,
        project_root=project,
        dependencies=RuntimeDependencies(
            discovery_source=flow._DiscoverySource(),
            metadata_provider=flow._MetadataProvider(),
            subtitle_adapter_factory=lambda: flow._SubtitleAdapter(),
            scoring_provider_factory=lambda: OllamaScoringProvider(
                settings=config.settings.local_scoring,
                prompt=prompt,
                transport=transport,
            ),
            analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
            quality_judge_provider_factory=lambda: OllamaQualityJudgeProvider(
                settings=config.settings.local_scoring,
                transport=transport,
            ),
        ),
    )

    flow._run_process(runtime)

    job = flow._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "TRUST_INTEGRITY_INVALID"
    assert job.last_error_message == "H2C_REPLAY_INVALID:SETTINGS_BOUND_EXCEEDED"
    # Zero persistence side effects.
    assert job.authoritative_scoring_artifact_key is None
    video = runtime._repository.get_video(flow.VIDEO_ID)
    assert video.authoritative_scoring_job_id is None


# ---------------------------------------------------------------------------
# Correction Round 1 — Fix 1: closed H2C_REPLAY_INVALID detail enforcement
# ---------------------------------------------------------------------------


def test_replay_invalid_constructor_enforces_closed_reason_set() -> None:
    from youtube_intel.runtime import _H2CReplayInvalid
    from youtube_intel.scoring import H2C_REPLAY_INVALID_REASONS

    # Every authorized reason is accepted.
    for reason in sorted(H2C_REPLAY_INVALID_REASONS):
        assert _H2CReplayInvalid(reason).reason == reason
    # Arbitrary reasons are rejected before any terminal emission.
    for bad in (
        "ARBITRARY_REASON",
        "SCORING_LINEAGE_VERSION_INVALID:extra",
        "H2C_SCORING_LINEAGE_VERSION_INVALID",
        "",
        "PRIMARY_EVIDENCE_MISMATCH and more",
    ):
        with pytest.raises(ValueError):
            _H2CReplayInvalid(bad)


def test_every_authorized_reason_produces_exact_qualified_detail() -> None:
    from youtube_intel.scoring import (
        H2C_REPLAY_INVALID_REASONS,
        h2c_replay_invalid_detail,
    )

    for reason in sorted(H2C_REPLAY_INVALID_REASONS):
        assert h2c_replay_invalid_detail(reason) == f"H2C_REPLAY_INVALID:{reason}"


def test_unknown_generation_live_path_emits_through_closed_helper(
    tmp_path: Path,
) -> None:
    flow = _load_flow()
    transport = flow._FakeTransport(_repair_pass_script(flow))
    runtime = flow._runtime(tmp_path, transport)
    _patch_read_generation(runtime, "task016c-scoring-lineage-v9")

    calls: list[str] = []
    original = runtime_module.h2c_replay_invalid_detail

    def recorder(reason: str) -> str:
        calls.append(reason)
        return original(reason)

    runtime_module.h2c_replay_invalid_detail = recorder
    try:
        flow._run_process(runtime)
    finally:
        runtime_module.h2c_replay_invalid_detail = original

    # The live production terminal path must route through the closed helper.
    assert calls == ["SCORING_LINEAGE_VERSION_INVALID"]
    job = flow._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "TRUST_INTEGRITY_INVALID"
    assert (
        job.last_error_message
        == "H2C_REPLAY_INVALID:SCORING_LINEAGE_VERSION_INVALID"
    )
    assert job.last_error_message != "H2C_SCORING_LINEAGE_VERSION_INVALID"


def test_live_replay_tamper_emits_through_closed_helper(tmp_path: Path) -> None:
    flow = _load_flow()
    transport = flow._FakeTransport(_repair_pass_script(flow))
    runtime = flow._runtime(tmp_path, transport)

    def _exploding_replay(*args: Any, **kwargs: Any) -> None:
        raise ValueError("injected attestation tamper")

    calls: list[str] = []
    original_helper = runtime_module.h2c_replay_invalid_detail
    original_attestation = runtime_module.verify_quality_pass_attestation

    def recorder(reason: str) -> str:
        calls.append(reason)
        return original_helper(reason)

    runtime_module.verify_quality_pass_attestation = _exploding_replay
    runtime_module.h2c_replay_invalid_detail = recorder
    try:
        flow._run_process(runtime)
    finally:
        runtime_module.verify_quality_pass_attestation = original_attestation
        runtime_module.h2c_replay_invalid_detail = original_helper

    # The live replay terminal path cannot bypass the closed helper and never
    # formats an arbitrary suffix.
    assert calls == ["ATTESTATION_INVALID"]
    job = flow._scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "TRUST_INTEGRITY_INVALID"
    assert job.last_error_message == "H2C_REPLAY_INVALID:ATTESTATION_INVALID"
