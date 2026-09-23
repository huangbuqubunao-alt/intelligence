"""TASK-016C Phase E trusted-finalizer contract tests (RED first)."""

from __future__ import annotations

import copy
import pickle
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.config import LocalScoringSettings, load_app_config
from youtube_intel.domain import (
    Availability,
    ContentQualityInput,
    ContentQualityResult,
    LiveStatus,
    QualityJudgeOperationInput,
    ScoringCandidate,
    ScoringEvidenceSource,
    VideoMetadata,
)
from youtube_intel.quality import (
    TrustedScoreResult,
    TrustedScoringContext,
    TrustedScoringFinalizer,
    build_content_quality_input_hash,
    build_quality_pass_attestation,
    build_scoring_candidate_hash,
)
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.scoring import build_scoring_input, build_scoring_request_identity


def _settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:" + "a" * 64,
        temperature=0.0,
        max_output_tokens=1200,
        max_transcript_chars=64,
        max_description_chars=32,
    )


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-phase-e",
        channel_id="channel-phase-e",
        channel_name="Phase E Channel",
        title="A useful scoring title",
        description="A deliberately bounded scoring description.",
        source_url="https://example.invalid/watch?v=video-phase-e",
        published_at=datetime(2026, 8, 15, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def test_canonical_identity_matches_existing_scoring_input_hash() -> None:
    """Phase E extraction must preserve the existing cache identity byte-for-byte."""

    settings = _settings()
    scoring_input = build_scoring_input(
        video=_video(),
        transcript_text="This transcript contains enough text for a stable sample.",
        language="en",
        output_language="en",
        settings=settings,
    )

    identity = build_scoring_request_identity(
        scoring_input=scoring_input,
        model=settings.model,
        temperature=settings.temperature,
        max_output_tokens=settings.max_output_tokens,
        max_description_chars=settings.max_description_chars,
    )

    assert identity.request_hash == scoring_input.request_hash


def _write_project(project: Path) -> None:
    (project / "config").mkdir(parents=True)
    (project / "vault").mkdir()
    (project / "config" / "channels.yaml").write_text(
        "channels:\n  - channel_id: UCtest000000000000000000000000000\n",
        encoding="utf-8",
    )
    (project / "config" / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
  output_language: en
local_scoring:
  model: qwen3:8b
  expected_model_digest: sha256:{"a" * 64}
  temperature: 0.0
  max_output_tokens: 1200
  max_transcript_chars: 64
  max_description_chars: 32
cloud:
  enabled: false
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {project / "vault"}
  vault_subdir: YouTube Intel
""",
        encoding="utf-8",
    )


def _runtime(project: Path) -> RuntimeOperations:
    _write_project(project)
    config = load_app_config(
        channels_path=project / "config" / "channels.yaml",
        settings_path=project / "config" / "settings.yaml",
    )
    return RuntimeOperations(
        config=config,
        project_root=project,
        dependencies=RuntimeDependencies(
            discovery_source=object(),  # type: ignore[arg-type]
            metadata_provider=object(),  # type: ignore[arg-type]
            subtitle_adapter_factory=lambda: object(),  # type: ignore[arg-type]
            scoring_provider_factory=lambda: object(),  # type: ignore[arg-type]
            analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
        ),
    )


def test_finalizer_accepts_only_runtime_bound_pass_material(tmp_path: Path) -> None:
    """The trust boundary must bind candidate, PASS and scoring provenance."""

    runtime = _runtime(tmp_path / "project")
    settings = _settings()
    scoring_input = build_scoring_input(
        video=_video(),
        transcript_text="This transcript contains enough text for a stable sample.",
        language="en",
        output_language="en",
        settings=settings,
    )
    candidate = ScoringCandidate.model_validate(
        {
            "score": 8.0,
            "reason": "This response explains practical workflow recommendations.",
            "topics": ["workflow"],
            "should_summarize": True,
            "dimensions": None,
        }
    )
    candidate_hash = build_scoring_candidate_hash(candidate)
    quality_input = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": scoring_input.request_hash,
            "candidate_hash": candidate_hash,
            "output_language": "en",
            "reason": candidate.reason,
            "topics": candidate.topics,
            "evidence_registry": [
                {
                    "evidence_id": "title-1",
                    "source": ScoringEvidenceSource.TITLE,
                    "excerpt": "A useful scoring title",
                }
            ],
        }
    )
    quality_input_hash = build_content_quality_input_hash(quality_input)
    operation = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": scoring_input.request_hash,
            "attempt_role": "PRIMARY",
            "candidate_hash": candidate_hash,
            "quality_input_hash": quality_input_hash,
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v3",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": settings.model,
            "judge_model_digest": settings.expected_model_digest,
        }
    )
    quality_result = ContentQualityResult.model_validate(
        {
            "schema_version": "content-quality-result-v1",
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v3",
            "status": "PASS",
            "decision_source": "LOCAL_JUDGE",
            "decision_confidence": "HIGH",
            "grounding_confidence": "MEDIUM",
            "usefulness_confidence": "MEDIUM",
            "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
            "reason": None,
            "evidence_ids": ["title-1"],
            "candidate_hash": candidate_hash,
            "quality_input_hash": quality_input_hash,
            "scoring_request_hash": scoring_input.request_hash,
            "judge_provider": "ollama",
            "judge_model": settings.model,
            "judge_model_digest": settings.expected_model_digest,
        }
    )
    attestation = build_quality_pass_attestation(
        quality_result=quality_result,
        operation_input=operation,
        quality_input=quality_input,
        authority=runtime._quality_provenance_authority,
    )

    trusted = TrustedScoringFinalizer().finalize(
        candidate=candidate,
        scoring_input=scoring_input,
        quality_input=quality_input,
        quality_result=quality_result,
        quality_operation=operation,
        attestation=attestation,
        quality_authority=runtime._quality_provenance_authority,
        scoring_context=runtime._trusted_scoring_context,
    )

    assert type(trusted) is TrustedScoreResult
    assert trusted.result.request_hash == scoring_input.request_hash
    assert trusted.result.output_language == "en"
    with pytest.raises(TypeError, match="immutable"):
        runtime._trusted_scoring_context._output_language = "zh-CN"  # type: ignore[attr-defined]
    with pytest.raises(TypeError, match="immutable"):
        trusted._result = trusted.result  # type: ignore[attr-defined]

    with pytest.raises(ValueError, match="candidate_hash"):
        TrustedScoringFinalizer().finalize(
            candidate={**candidate.model_dump(), "score": 7.0},
            scoring_input=scoring_input,
            quality_input=quality_input,
            quality_result=quality_result,
            quality_operation=operation,
            attestation=attestation,
            quality_authority=runtime._quality_provenance_authority,
            scoring_context=runtime._trusted_scoring_context,
        )

    with pytest.raises(TypeError, match="TrustedScoringContext"):
        TrustedScoringFinalizer().finalize(
            candidate=candidate,
            scoring_input=scoring_input,
            quality_input=quality_input,
            quality_result=quality_result,
            quality_operation=operation,
            attestation=attestation,
            quality_authority=runtime._quality_provenance_authority,
            scoring_context={},  # type: ignore[arg-type]
        )


def test_trusted_capabilities_reject_direct_construction_copy_and_pickle(
    tmp_path: Path,
) -> None:
    """Only runtime/finalizer sentinels may mint opaque trusted objects."""

    with pytest.raises(ValueError, match="runtime"):
        TrustedScoringContext(
            sentinel=object(),
            scoring_provider="ollama",
            scoring_model="qwen3:8b",
            scoring_model_digest="sha256:" + "a" * 64,
            output_language="en",
            scoring_schema_version="scoring-schema-v1",
            scoring_prompt_version="scoring-prompt-v1",
            scoring_operation="local-scoring",
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=32,
        )

    with pytest.raises(ValueError, match="finalizer"):
        TrustedScoreResult(sentinel=object(), result=object())  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="cannot be subclassed"):

        class DerivedContext(TrustedScoringContext):
            pass

    with pytest.raises(TypeError, match="cannot be subclassed"):

        class DerivedResult(TrustedScoreResult):
            pass

    context = _runtime(tmp_path / "project")._trusted_scoring_context
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.copy(context)
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.deepcopy(context)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(context)
