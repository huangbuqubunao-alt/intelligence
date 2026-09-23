"""TASK-016C Phase F trusted-scoring-seam contract tests (RED first).

Covers the frozen Phase F contract: candidate-only PRIMARY attempts, the
single canonical raw->candidate parser, raw/candidate/request binding,
legacy isolation, and the in-memory ``PhaseFTrustedScoringSuccess`` aggregate.

Reference documents (authoritative):
- agent-prompts/TASK-016C-PHASE-F-IMPLEMENTATION-AUTHORIZATION.md
- docs/TASK-016C-PHASE-F-RUNTIME-INTEGRATION-AMENDMENT.md (Round 4)
- docs/TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import pickle
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.config import LocalScoringSettings, load_app_config
from youtube_intel.domain import (
    Availability,
    ContentQualityConfidence,
    ContentQualityDecisionSource,
    ContentQualityInput,
    ContentQualityResult,
    ContentQualitySignal,
    ContentQualityStatus,
    JobStatus,
    LiveStatus,
    ProcessingStage,
    QualityJudgeOperationInput,
    QualityPassAttestation,
    ScoreResult,
    ScoringCandidate,
    ScoringEvidenceSource,
    ScoringInput,
    VideoMetadata,
)
from youtube_intel.providers.ollama import (
    OllamaQualityJudgeProvider,
    OllamaScoringProvider,
    parse_scoring_candidate,
)
from youtube_intel.quality import (
    TrustedScoreResult,
    TrustedScoringFinalizer,
    build_content_quality_input_hash,
    build_quality_pass_attestation,
    build_scoring_candidate_hash,
)
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.scoring import (
    PhaseFTrustedScoringSuccess,
    PrimaryScoringAttempt,
    _mint_phase_f_trusted_scoring_success,
    _run_primary_trusted_scoring_seam,
    build_primary_scoring_attempt,
    build_scoring_input,
    build_scoring_request_identity,
)
from youtube_intel.scoring_admission import ScoringDispatchAdmission

_EN_REASON = (
    "This response explains a concrete product strategy with useful trade-offs."
)

_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + ("a" * 64)


class _AdmissionRepository:
    def get_job(self, job_id: str) -> object | None:
        if job_id != "phase-f-admission-job":
            return None
        return type(
            "_AdmissionJob",
            (),
            {
                "target_stage": ProcessingStage.SCORING,
                "status": JobStatus.RUNNING,
                "lease_owner": "phase-f-test",
                "lease_until": datetime.now(UTC) + timedelta(minutes=5),
            },
        )()

    def get_provider_call(self, request_hash: str) -> None:
        del request_hash
        return None


def _h1_admission() -> ScoringDispatchAdmission:
    return ScoringDispatchAdmission(
        repository=_AdmissionRepository(),  # type: ignore[arg-type]
        job_id="phase-f-admission-job",
        owner="phase-f-test",
    )


def _settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model=_MODEL,
        expected_model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_transcript_chars=64,
        max_description_chars=32,
    )


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-phase-f",
        channel_id="channel-phase-f",
        channel_name="Phase F Channel",
        title="A useful scoring title",
        description="A deliberately bounded scoring description.",
        source_url="https://example.invalid/watch?v=video-phase-f",
        published_at=datetime(2026, 8, 18, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _scoring_input(*, output_language: str = "en") -> ScoringInput:
    return build_scoring_input(
        video=_video(),
        transcript_text="This transcript contains enough text for a stable sample.",
        language="en",
        output_language=output_language,
        settings=_settings(),
    )


def _candidate_fields(
    *,
    score: float = 8.0,
    reason: str = _EN_REASON,
) -> dict[str, object]:
    return {
        "score": score,
        "reason": reason,
        "topics": ["product strategy", "experimentation"],
        "should_summarize": True,
        "dimensions": {"product": 9.0, "practicality": 8.0},
    }


def _raw_response(
    inner: dict[str, object] | str,
    *,
    extra: dict[str, object] | None = None,
) -> str:
    inner_text = (
        inner
        if isinstance(inner, str)
        else json.dumps(inner, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    payload: dict[str, object] = {
        "model": _MODEL,
        "response": inner_text,
        "done": True,
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identity(scoring_input: ScoringInput) -> object:
    return build_scoring_request_identity(
        scoring_input=scoring_input,
        model=_MODEL,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )


def _attempt_kwargs(
    *,
    scoring_input: ScoringInput,
    raw: str,
    candidate: ScoringCandidate,
    identity: object,
) -> dict[str, object]:
    return {
        "scoring_input_normalized_hash": identity.normalized_input_hash,  # type: ignore[attr-defined]
        "scoring_request_hash": identity.request_hash,  # type: ignore[attr-defined]
        "candidate": candidate,
        "candidate_hash": build_scoring_candidate_hash(candidate),
        "raw_response_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "provider": "ollama",
        "model": _MODEL,
        "model_digest": _DIGEST,
        "attempt_role": "PRIMARY",
        "final_raw_response": raw,
    }


def _build_attempt(
    *,
    scoring_input: ScoringInput,
    raw: str,
    candidate: ScoringCandidate | None = None,
) -> PrimaryScoringAttempt:
    return build_primary_scoring_attempt(
        scoring_input=scoring_input,
        candidate=candidate if candidate is not None else parse_scoring_candidate(raw),
        final_raw_response=raw,
        provider="ollama",
        model=_MODEL,
        model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )


def _quality_materials(
    runtime: RuntimeOperations,
    scoring_input: ScoringInput,
    candidate: ScoringCandidate,
) -> tuple[
    ContentQualityInput,
    ContentQualityResult,
    QualityJudgeOperationInput,
    QualityPassAttestation,
]:
    candidate_hash = build_scoring_candidate_hash(candidate)
    quality_input = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": scoring_input.request_hash,
            "candidate_hash": candidate_hash,
            "output_language": scoring_input.output_language,
            "reason": candidate.reason,
            "topics": list(candidate.topics),
            "evidence_registry": [
                {
                    "evidence_id": "title-1",
                    "source": ScoringEvidenceSource.TITLE.value,
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
            "judge_model": _MODEL,
            "judge_model_digest": _DIGEST,
        }
    )
    quality_result = ContentQualityResult.model_validate(
        {
            "schema_version": "content-quality-result-v1",
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v3",
            "status": ContentQualityStatus.PASS.value,
            "decision_source": ContentQualityDecisionSource.LOCAL_JUDGE.value,
            "decision_confidence": ContentQualityConfidence.HIGH.value,
            "grounding_confidence": ContentQualityConfidence.MEDIUM.value,
            "usefulness_confidence": ContentQualityConfidence.MEDIUM.value,
            "signals": [
                ContentQualitySignal.MINIMAL_CLAIM_PRESENT.value,
                ContentQualitySignal.GROUNDING_PRESENT.value,
            ],
            "reason": None,
            "evidence_ids": ["title-1"],
            "candidate_hash": candidate_hash,
            "quality_input_hash": quality_input_hash,
            "scoring_request_hash": scoring_input.request_hash,
            "judge_provider": "ollama",
            "judge_model": _MODEL,
            "judge_model_digest": _DIGEST,
        }
    )
    attestation = build_quality_pass_attestation(
        quality_result=quality_result,
        operation_input=operation,
        quality_input=quality_input,
        authority=runtime._quality_provenance_authority,
    )
    return quality_input, quality_result, operation, attestation


def _seam_kwargs(
    runtime: RuntimeOperations,
    scoring_input: ScoringInput,
    candidate: ScoringCandidate,
) -> dict[str, object]:
    quality_input, quality_result, operation, attestation = _quality_materials(
        runtime, scoring_input, candidate
    )
    return {
        "scoring_input": scoring_input,
        "quality_input": quality_input,
        "quality_result": quality_result,
        "quality_operation": operation,
        "attestation": attestation,
        "quality_authority": runtime._quality_provenance_authority,
        "scoring_context": runtime._trusted_scoring_context,
    }




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


def _snapshot(root: Path) -> dict[str, int]:
    return {
        str(path.relative_to(root)): path.stat().st_size
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def read(self, size: int = -1) -> bytes:
        if not isinstance(self._payload, bytes):
            return json.dumps(self._payload).encode("utf-8")
        return self._payload

    def close(self) -> None:
        pass


class _FakeTransport:
    def __init__(self, responses: list[object]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str]] = []

    def __call__(self, request: object, timeout: float) -> _Response:
        method = getattr(request, "method")
        url = getattr(request, "full_url")
        self.requests.append((method, url))
        response = self._responses.pop(0)
        if isinstance(response, _Response):
            return response
        return _Response(response)


def _tags() -> dict[str, object]:
    return {"models": [{"name": _MODEL, "digest": "a" * 64}]}


def _generate(inner: dict[str, object]) -> dict[str, str]:
    return {
        "response": json.dumps(
            inner, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    }


# ---------------------------------------------------------------------------
# Provider: candidate-only PRIMARY attempt (authorization area 1, matrix 12)
# ---------------------------------------------------------------------------


def test_provider_primary_attempt_returns_candidate_only_continuation(
    tmp_path: Path,
) -> None:
    prompt = Path(__file__).resolve().parents[2] / "prompts" / "scoring.md"
    transport = _FakeTransport([_tags(), _generate(_candidate_fields())])
    provider = OllamaScoringProvider(
        settings=_settings(),
        prompt=prompt.read_text(encoding="utf-8"),
        transport=transport,
    )
    value = _scoring_input()

    attempt = provider.primary_attempt(value)

    assert type(attempt) is PrimaryScoringAttempt
    assert type(attempt.candidate) is ScoringCandidate
    assert attempt.candidate.score == 8.0
    assert attempt.candidate.reason == _EN_REASON
    assert attempt.candidate.topics == ("product strategy", "experimentation")
    assert attempt.candidate.should_summarize is True
    assert attempt.candidate.dimensions is not None
    assert attempt.provider == "ollama"
    assert attempt.model == _MODEL
    assert attempt.model_digest == _DIGEST
    assert attempt.attempt_role == "PRIMARY"
    assert attempt.scoring_request_hash == value.request_hash
    assert attempt.raw_response_hash == hashlib.sha256(
        attempt.final_raw_response.encode("utf-8")
    ).hexdigest()
    # exactly one preflight + one generate; no repair call on the trusted path
    assert [method for method, _ in transport.requests] == ["GET", "POST"]


def test_candidate_business_fields_match_score_result_contract() -> None:
    candidate = parse_scoring_candidate(_raw_response(_candidate_fields(score=8.5)))

    assert type(candidate) is ScoringCandidate
    assert candidate.score == 8.5
    assert set(candidate.model_dump()) == {
        "score",
        "reason",
        "topics",
        "should_summarize",
        "dimensions",
    }
    assert candidate.dimensions is not None
    assert candidate.dimensions.product == 9.0
    assert candidate.dimensions.practicality == 8.0


# ---------------------------------------------------------------------------
# Raw -> candidate canonical parser and attempt factory binding
# (authorization areas 2-4; matrix 1-4, 12)
# ---------------------------------------------------------------------------


def test_attempt_factory_rejects_raw_a_candidate_b() -> None:
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields(score=8.0))
    candidate_b = ScoringCandidate.model_validate(_candidate_fields(score=9.0))

    with pytest.raises(ValueError, match="candidate"):
        build_primary_scoring_attempt(
            scoring_input=scoring_input,
            candidate=candidate_b,
            final_raw_response=raw,
            provider="ollama",
            model=_MODEL,
            model_digest=_DIGEST,
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=32,
        )


def test_attempt_factory_rejects_post_parse_candidate_mutation() -> None:
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields(score=8.0))
    candidate = parse_scoring_candidate(raw)
    mutated = ScoringCandidate.model_validate(
        {**candidate.model_dump(), "score": 7.0}
    )

    with pytest.raises(ValueError, match="candidate"):
        build_primary_scoring_attempt(
            scoring_input=scoring_input,
            candidate=mutated,
            final_raw_response=raw,
            provider="ollama",
            model=_MODEL,
            model_digest=_DIGEST,
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=32,
        )


def test_attempt_factory_rejects_bare_score_result_candidate() -> None:
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    legacy = ScoreResult.model_validate(
        {
            "schema_version": "score-result-v2",
            "score": 8.0,
            "reason": _EN_REASON,
            "topics": ["product strategy", "experimentation"],
            "should_summarize": True,
            "dimensions": {"product": 9.0, "practicality": 8.0},
            "provider": "ollama",
            "model": _MODEL,
            "prompt_version": "scoring-prompt-v2",
            "request_hash": scoring_input.request_hash,
            "output_language": "en",
        }
    )

    with pytest.raises(ValueError, match="candidate"):
        build_primary_scoring_attempt(
            scoring_input=scoring_input,
            candidate=legacy,
            final_raw_response=raw,
            provider="ollama",
            model=_MODEL,
            model_digest=_DIGEST,
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=32,
        )


def test_attempt_factory_rejects_mapping_candidate() -> None:
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())

    with pytest.raises(ValueError, match="candidate"):
        build_primary_scoring_attempt(
            scoring_input=scoring_input,
            candidate=_candidate_fields(),
            final_raw_response=raw,
            provider="ollama",
            model=_MODEL,
            model_digest=_DIGEST,
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=32,
        )


def test_attempt_factory_rejects_oversized_raw() -> None:
    scoring_input = _scoring_input()
    raw = _raw_response(
        _candidate_fields(),
        extra={"padding": "x" * 1_000_000},
    )

    with pytest.raises(ValueError, match="raw"):
        build_primary_scoring_attempt(
            scoring_input=scoring_input,
            candidate=parse_scoring_candidate(raw),
            final_raw_response=raw,
            provider="ollama",
            model=_MODEL,
            model_digest=_DIGEST,
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=32,
        )


def test_attempt_factory_rejects_invalid_utf8_raw() -> None:
    scoring_input = _scoring_input()
    raw = json.dumps(
        {
            "model": "\ud800",
            "response": json.dumps(
                _candidate_fields(), ensure_ascii=False, sort_keys=True
            ),
            "done": True,
        },
        ensure_ascii=False,
    )

    with pytest.raises(ValueError, match="raw"):
        build_primary_scoring_attempt(
            scoring_input=scoring_input,
            candidate=ScoringCandidate.model_validate(_candidate_fields()),
            final_raw_response=raw,
            provider="ollama",
            model=_MODEL,
            model_digest=_DIGEST,
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=32,
        )


def test_attempt_factory_rejects_oversized_inner_response() -> None:
    scoring_input = _scoring_input()
    raw = _raw_response(
        {
            "score": 8,
            "reason": "x" * 20_001,
            "topics": ["topic"],
            "should_summarize": True,
        }
    )

    with pytest.raises(ValueError, match="response"):
        build_primary_scoring_attempt(
            scoring_input=scoring_input,
            candidate=ScoringCandidate.model_validate(_candidate_fields()),
            final_raw_response=raw,
            provider="ollama",
            model=_MODEL,
            model_digest=_DIGEST,
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=32,
        )


def test_one_byte_raw_mutation_changes_raw_hash() -> None:
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields(score=8.0))

    attempt_a = _build_attempt(scoring_input=scoring_input, raw=raw)
    attempt_b = _build_attempt(scoring_input=scoring_input, raw=raw + " ")

    assert attempt_a.raw_response_hash != attempt_b.raw_response_hash
    assert attempt_a.candidate_hash == attempt_b.candidate_hash
    assert attempt_a.candidate == attempt_b.candidate


def test_semantically_equal_different_bytes_raw_hash_differs() -> None:
    scoring_input = _scoring_input()
    fields = _candidate_fields(score=8.0)
    raw_compact = _raw_response(fields)
    raw_pretty = json.dumps(
        {
            "model": _MODEL,
            "response": json.dumps(
                fields, ensure_ascii=False, sort_keys=True, indent=2
            ),
            "done": True,
        },
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )

    attempt_compact = _build_attempt(scoring_input=scoring_input, raw=raw_compact)
    attempt_pretty = _build_attempt(scoring_input=scoring_input, raw=raw_pretty)

    assert attempt_compact.raw_response_hash != attempt_pretty.raw_response_hash
    assert attempt_compact.candidate == attempt_pretty.candidate


def test_attempt_is_frozen_and_exact_type() -> None:
    scoring_input = _scoring_input()
    attempt = _build_attempt(
        scoring_input=scoring_input,
        raw=_raw_response(_candidate_fields()),
    )

    assert type(attempt) is PrimaryScoringAttempt
    with pytest.raises(AttributeError):
        attempt.final_raw_response = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Seam binding rejection (authorization area 4; matrix 6, 8)
# ---------------------------------------------------------------------------


def test_seam_rejects_attempt_raw_hash_mismatch(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    candidate = parse_scoring_candidate(raw)
    identity = _identity(scoring_input)
    kwargs = _attempt_kwargs(
        scoring_input=scoring_input, raw=raw, candidate=candidate, identity=identity
    )
    attempt = PrimaryScoringAttempt(
        **{**kwargs, "raw_response_hash": "0" * 64}  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="raw"):
        _run_primary_trusted_scoring_seam(
            attempt=attempt, **_seam_kwargs(runtime, scoring_input, candidate)
        )


def test_seam_rejects_attempt_candidate_hash_mismatch(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    candidate = parse_scoring_candidate(raw)
    identity = _identity(scoring_input)
    kwargs = _attempt_kwargs(
        scoring_input=scoring_input, raw=raw, candidate=candidate, identity=identity
    )
    attempt = PrimaryScoringAttempt(
        **{**kwargs, "candidate_hash": "0" * 64}  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="candidate"):
        _run_primary_trusted_scoring_seam(
            attempt=attempt, **_seam_kwargs(runtime, scoring_input, candidate)
        )


def test_seam_rejects_attempt_candidate_not_from_raw(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields(score=8.0))
    candidate_b = ScoringCandidate.model_validate(_candidate_fields(score=9.0))
    identity = _identity(scoring_input)
    kwargs = _attempt_kwargs(
        scoring_input=scoring_input, raw=raw, candidate=candidate_b, identity=identity
    )
    attempt = PrimaryScoringAttempt(**kwargs)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="candidate"):
        _run_primary_trusted_scoring_seam(
            attempt=attempt, **_seam_kwargs(runtime, scoring_input, candidate_b)
        )


def test_seam_rejects_request_identity_mismatch(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    candidate = parse_scoring_candidate(raw)
    identity = _identity(scoring_input)
    kwargs = _attempt_kwargs(
        scoring_input=scoring_input, raw=raw, candidate=candidate, identity=identity
    )
    attempt = PrimaryScoringAttempt(
        **{**kwargs, "scoring_request_hash": "0" * 64}  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="request"):
        _run_primary_trusted_scoring_seam(
            attempt=attempt, **_seam_kwargs(runtime, scoring_input, candidate)
        )


def test_seam_rejects_provider_model_digest_mismatch(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    candidate = parse_scoring_candidate(raw)
    identity = _identity(scoring_input)
    kwargs = _attempt_kwargs(
        scoring_input=scoring_input, raw=raw, candidate=candidate, identity=identity
    )
    attempt = PrimaryScoringAttempt(
        **{**kwargs, "model_digest": "sha256:" + ("f" * 64)}  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="provider"):
        _run_primary_trusted_scoring_seam(
            attempt=attempt, **_seam_kwargs(runtime, scoring_input, candidate)
        )


def test_seam_rejects_non_primary_attempt_role(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    candidate = parse_scoring_candidate(raw)
    identity = _identity(scoring_input)
    kwargs = _attempt_kwargs(
        scoring_input=scoring_input, raw=raw, candidate=candidate, identity=identity
    )
    attempt = PrimaryScoringAttempt(
        **{**kwargs, "attempt_role": "REPAIR"}  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="PRIMARY"):
        _run_primary_trusted_scoring_seam(
            attempt=attempt, **_seam_kwargs(runtime, scoring_input, candidate)
        )


# ---------------------------------------------------------------------------
# Legacy isolation (authorization area 6)
# ---------------------------------------------------------------------------


def test_seam_rejects_bare_score_result(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    candidate = parse_scoring_candidate(_raw_response(_candidate_fields()))
    legacy = ScoreResult.model_validate(
        {
            "schema_version": "score-result-v2",
            "score": 8.0,
            "reason": _EN_REASON,
            "topics": ["product strategy", "experimentation"],
            "should_summarize": True,
            "dimensions": {"product": 9.0, "practicality": 8.0},
            "provider": "ollama",
            "model": _MODEL,
            "prompt_version": "scoring-prompt-v2",
            "request_hash": scoring_input.request_hash,
            "output_language": "en",
        }
    )

    with pytest.raises(ValueError, match="PrimaryScoringAttempt"):
        _run_primary_trusted_scoring_seam(
            attempt=legacy, **_seam_kwargs(runtime, scoring_input, candidate)
        )


def test_seam_rejects_mapping_and_json_in_attempt_slot(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    candidate = parse_scoring_candidate(_raw_response(_candidate_fields()))
    base = _seam_kwargs(runtime, scoring_input, candidate)

    for forged in (_candidate_fields(), json.dumps(_candidate_fields())):
        with pytest.raises(ValueError, match="PrimaryScoringAttempt"):
            _run_primary_trusted_scoring_seam(attempt=forged, **base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Legal PRIMARY flow and fail-closed success aggregate
# (authorization area 5; matrix 13)
# ---------------------------------------------------------------------------


def test_primary_flow_reaches_phase_f_trusted_scoring_success(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    success = runtime._run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
    )

    assert type(success) is PhaseFTrustedScoringSuccess
    assert type(success.trusted_result) is TrustedScoreResult
    assert type(success.primary_attempt) is PrimaryScoringAttempt
    assert success.scoring_request_hash == attempt.scoring_request_hash
    assert success.candidate_hash == attempt.candidate_hash
    assert success.raw_response_hash == attempt.raw_response_hash
    assert success.trusted_result.result.request_hash == attempt.scoring_request_hash
    assert success.trusted_result.result.score == 8.0
    assert success.trusted_result.result.output_language == "en"


def test_trusted_result_alone_is_not_a_phase_f_success(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime._run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
    )

    assert not isinstance(success.trusted_result, PhaseFTrustedScoringSuccess)
    with pytest.raises(ValueError, match="PrimaryScoringAttempt"):
        _mint_phase_f_trusted_scoring_success(
            trusted_result=success.trusted_result, primary_attempt=object()
        )


def test_language_failure_blocks_success_aggregate(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input(output_language="en")
    raw = _raw_response(
        _candidate_fields(reason="该视频清楚说明了实用的产品工作流，具有参考价值。")
    )
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    with pytest.raises(ValueError):
        runtime._run_primary_trusted_scoring(
            attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
        )


def test_quality_reject_blocks_success_aggregate(tmp_path: Path) -> None:
    """A deterministic gate rejection blocks the trusted success aggregate.

    The runtime no longer accepts caller-provided quality results; this test
    exercises the same fail-closed path through the deterministic gate.
    """

    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(
        _candidate_fields(
            reason="This video explains product strategy.\nThis video explains product strategy."
        )
    )
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    with pytest.raises(ValueError):
        runtime._run_primary_trusted_scoring(
            attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
        )


def test_attestation_mismatch_blocks_success_aggregate(tmp_path: Path) -> None:
    """A foreign attestation supplied to the private seam must fail finalization.

    The public runtime method constructs the attestation internally; the
    mismatch attack is only possible against the private seam, which remains
    fail-closed.
    """

    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields(score=8.0))
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    kwargs = _seam_kwargs(runtime, scoring_input, attempt.candidate)
    candidate_b = ScoringCandidate.model_validate(_candidate_fields(score=7.0))
    _, _, _, foreign_attestation = _quality_materials(
        runtime, scoring_input, candidate_b
    )
    kwargs["attestation"] = foreign_attestation

    with pytest.raises(ValueError, match="attestation"):
        _run_primary_trusted_scoring_seam(attempt=attempt, **kwargs)


# ---------------------------------------------------------------------------
# Aggregate capability and zero side effects (authorization area 7; matrix 15)
# ---------------------------------------------------------------------------


def test_success_mint_rejects_forged_trusted_result(tmp_path: Path) -> None:
    del tmp_path
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    with pytest.raises(ValueError, match="TrustedScoreResult"):
        _mint_phase_f_trusted_scoring_success(
            trusted_result=object(), primary_attempt=attempt
        )


def test_success_aggregate_is_opaque_immutable_and_non_serializable(
    tmp_path: Path,
) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)
    success = runtime._run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
    )

    with pytest.raises(ValueError, match="mint"):
        PhaseFTrustedScoringSuccess(
            sentinel=object(),
            trusted_result=success.trusted_result,
            primary_attempt=success.primary_attempt,
            scoring_request_hash="0" * 64,
            candidate_hash="0" * 64,
            raw_response_hash="0" * 64,
        )
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.copy(success)
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.deepcopy(success)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(success)
    with pytest.raises(TypeError, match="cannot be subclassed"):

        class DerivedSuccess(PhaseFTrustedScoringSuccess):
            pass

    with pytest.raises(TypeError, match="immutable"):
        success._sealed = False  # type: ignore[attr-defined]


def test_primary_flow_has_zero_persistence_and_no_legacy_service(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    runtime, _ = _judge_runtime(project)
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    before = _snapshot(project)
    data_before = _snapshot(project / "data")
    success = runtime._run_primary_trusted_scoring(
        attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
    )
    after = _snapshot(project)
    data_after = _snapshot(project / "data")

    assert after == before
    assert data_after == data_before
    assert type(success) is PhaseFTrustedScoringSuccess
    seam_source = inspect.getsource(_run_primary_trusted_scoring_seam)
    assert "RepositoryBackedScoringService" not in seam_source
    # the seam has no provider handle, so it cannot recall the provider
    assert "provider" not in inspect.signature(
        _run_primary_trusted_scoring_seam
    ).parameters


def _judge_pass() -> dict[str, object]:
    return {
        "status": "PASS",
        "decision_confidence": "HIGH",
        "grounding_confidence": "MEDIUM",
        "usefulness_confidence": "MEDIUM",
        "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
        "reason": None,
        "evidence_ids": ["title-1"],
    }


def _judge_reject() -> dict[str, object]:
    return {
        "status": "REJECT",
        "decision_confidence": "HIGH",
        "grounding_confidence": "LOW",
        "usefulness_confidence": "LOW",
        "signals": ["LOW_INFORMATION"],
        "reason": "Content exhibits spam patterns.",
        "evidence_ids": [],
    }


def _judge_runtime(
    project: Path,
    *,
    responses: list[object] | None = None,
) -> tuple[RuntimeOperations, _FakeTransport]:
    """Create a runtime whose local Judge provider uses a fake transport.

    If the current ``RuntimeDependencies`` does not yet support a Judge provider
    factory, the runtime is created without one and the calling test will fail
    at the public API boundary instead.
    """

    _write_project(project)
    config = load_app_config(
        channels_path=project / "config" / "channels.yaml",
        settings_path=project / "config" / "settings.yaml",
    )
    transport = _FakeTransport(
        responses if responses is not None else [_tags(), _generate(_judge_pass())]
    )
    deps_kwargs: dict[str, object] = {
        "discovery_source": object(),  # type: ignore[arg-type]
        "metadata_provider": object(),  # type: ignore[arg-type]
        "subtitle_adapter_factory": lambda: object(),  # type: ignore[arg-type]
        "scoring_provider_factory": lambda: object(),  # type: ignore[arg-type]
        "analysis_provider_factory": lambda: object(),  # type: ignore[arg-type]
    }
    if "quality_judge_provider_factory" in inspect.signature(
        RuntimeDependencies
    ).parameters:
        deps_kwargs["quality_judge_provider_factory"] = (
            lambda: OllamaQualityJudgeProvider(
                settings=config.settings.local_scoring,
                transport=transport,
            )
        )
    return (
        RuntimeOperations(
            config=config,
            project_root=project,
            dependencies=RuntimeDependencies(**deps_kwargs),  # type: ignore[arg-type]
        ),
        transport,
    )


# ---------------------------------------------------------------------------
# Phase F Correction Round 1: public surface and authority boundaries (P1-1, P1-3)
# ---------------------------------------------------------------------------


def test_mint_is_not_a_public_export() -> None:
    import youtube_intel.scoring as scoring_module

    assert "_mint_phase_f_trusted_scoring_success" not in scoring_module.__all__


def test_seam_is_not_a_public_export() -> None:
    import youtube_intel.scoring as scoring_module

    assert "_run_primary_trusted_scoring_seam" not in scoring_module.__all__


def test_mint_rejects_raw_a_candidate_b_bypass(tmp_path: Path) -> None:
    """A legitimate TrustedScoreResult B plus a forged raw-A/candidate-B attempt
    must be rejected at the aggregate mint.

    The attack relies on constructing ``PrimaryScoringAttempt`` directly (it is
    a frozen dataclass) so that ``build_primary_scoring_attempt`` cannot enforce
    raw->candidate equality.  The mint must independently re-parse the raw body
    and verify it matches the attempt's candidate.
    """

    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw_a = _raw_response(_candidate_fields(score=8.0))
    candidate_b = ScoringCandidate.model_validate(_candidate_fields(score=9.0))
    identity = _identity(scoring_input)

    forged = PrimaryScoringAttempt(
        scoring_input_normalized_hash=identity.normalized_input_hash,
        scoring_request_hash=identity.request_hash,
        candidate=candidate_b,
        candidate_hash=build_scoring_candidate_hash(candidate_b),
        raw_response_hash=hashlib.sha256(raw_a.encode("utf-8")).hexdigest(),
        provider="ollama",
        model=_MODEL,
        model_digest=_DIGEST,
        attempt_role="PRIMARY",
        final_raw_response=raw_a,
    )

    quality_input, quality_result, operation, attestation = _quality_materials(
        runtime, scoring_input, candidate_b
    )
    trusted_b = TrustedScoringFinalizer().finalize(
        candidate=candidate_b,
        scoring_input=scoring_input,
        quality_input=quality_input,
        quality_result=quality_result,
        quality_operation=operation,
        attestation=attestation,
        quality_authority=runtime._quality_provenance_authority,
        scoring_context=runtime._trusted_scoring_context,
    )

    with pytest.raises(ValueError, match="candidate"):
        _mint_phase_f_trusted_scoring_success(
            trusted_result=trusted_b, primary_attempt=forged
        )


def test_mint_rejects_business_field_mismatch(tmp_path: Path) -> None:
    """A TrustedScoreResult from candidate B bound to a legitimate attempt for
    candidate A must be rejected: the aggregate mint must verify score, reason,
    topics, should_summarize, and dimensions match the attempt's candidate.
    """

    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw_a = _raw_response(_candidate_fields(score=8.0))
    attempt_a = _build_attempt(scoring_input=scoring_input, raw=raw_a)
    candidate_b = ScoringCandidate.model_validate(_candidate_fields(score=9.0))

    quality_input, quality_result, operation, attestation = _quality_materials(
        runtime, scoring_input, candidate_b
    )
    trusted_b = TrustedScoringFinalizer().finalize(
        candidate=candidate_b,
        scoring_input=scoring_input,
        quality_input=quality_input,
        quality_result=quality_result,
        quality_operation=operation,
        attestation=attestation,
        quality_authority=runtime._quality_provenance_authority,
        scoring_context=runtime._trusted_scoring_context,
    )

    with pytest.raises(ValueError, match="business|score|reason|topics|should_summarize|dimensions"):
        _mint_phase_f_trusted_scoring_success(
            trusted_result=trusted_b, primary_attempt=attempt_a
        )


# ---------------------------------------------------------------------------
# Phase F Correction Round 1: deterministic gate and Local Judge ordering (P1-2)
# ---------------------------------------------------------------------------


def test_deterministic_gate_blocks_exact_repetition(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields(reason="This video explains product strategy.\nThis video explains product strategy."))
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    with pytest.raises(ValueError):
        runtime._run_primary_trusted_scoring(
            attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
        )


def test_deterministic_reject_prevents_judge_call(tmp_path: Path) -> None:
    runtime, transport = _judge_runtime(tmp_path / "project", responses=[])
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields(reason="This video explains product strategy.\nThis video explains product strategy."))
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    with pytest.raises(ValueError):
        runtime._run_primary_trusted_scoring(
            attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
        )

    assert transport.requests == []


def test_judge_non_pass_prevents_trusted_success(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(
        tmp_path / "project",
        responses=[_tags(), _generate(_judge_reject())],
    )
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    with pytest.raises(ValueError):
        runtime._run_primary_trusted_scoring(
            attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
        )


def test_judge_failure_prevents_trusted_success(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(
        tmp_path / "project",
        responses=[_tags(), ConnectionRefusedError("judge down")],
    )
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    with pytest.raises(ValueError):
        runtime._run_primary_trusted_scoring(
            attempt=attempt, scoring_input=scoring_input, admission=_h1_admission()
        )


# ---------------------------------------------------------------------------
# Phase F Correction Round 1: runtime authority boundary (P1-3)
# ---------------------------------------------------------------------------


def test_runtime_rejects_quality_authority_param(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    with pytest.raises(TypeError):
        runtime._run_primary_trusted_scoring(
            attempt=attempt,
            scoring_input=scoring_input,
            admission=_h1_admission(),
            quality_authority=runtime._quality_provenance_authority,
        )


def test_runtime_rejects_scoring_context_param(tmp_path: Path) -> None:
    runtime, _ = _judge_runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    attempt = _build_attempt(scoring_input=scoring_input, raw=raw)

    with pytest.raises(TypeError):
        runtime._run_primary_trusted_scoring(
            attempt=attempt,
            scoring_input=scoring_input,
            admission=_h1_admission(),
            scoring_context=runtime._trusted_scoring_context,
        )


# ---------------------------------------------------------------------------
# Phase F Correction Round 1: independent provider/model/digest regression (P2)
# ---------------------------------------------------------------------------


def test_seam_rejects_provider_mismatch(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    candidate = parse_scoring_candidate(raw)
    identity = _identity(scoring_input)
    kwargs = _attempt_kwargs(
        scoring_input=scoring_input, raw=raw, candidate=candidate, identity=identity
    )
    attempt = PrimaryScoringAttempt(
        **{**kwargs, "provider": "openai"}  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="provider"):
        _run_primary_trusted_scoring_seam(
            attempt=attempt, **_seam_kwargs(runtime, scoring_input, candidate)
        )


def test_seam_rejects_model_mismatch(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    candidate = parse_scoring_candidate(raw)
    identity = _identity(scoring_input)
    kwargs = _attempt_kwargs(
        scoring_input=scoring_input, raw=raw, candidate=candidate, identity=identity
    )
    attempt = PrimaryScoringAttempt(
        **{**kwargs, "model": "qwen3:14b"}  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="model"):
        _run_primary_trusted_scoring_seam(
            attempt=attempt, **_seam_kwargs(runtime, scoring_input, candidate)
        )


def test_seam_rejects_digest_mismatch_independent(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "project")
    scoring_input = _scoring_input()
    raw = _raw_response(_candidate_fields())
    candidate = parse_scoring_candidate(raw)
    identity = _identity(scoring_input)
    kwargs = _attempt_kwargs(
        scoring_input=scoring_input, raw=raw, candidate=candidate, identity=identity
    )
    attempt = PrimaryScoringAttempt(
        **{**kwargs, "model_digest": "sha256:" + ("f" * 64)}  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="digest"):
        _run_primary_trusted_scoring_seam(
            attempt=attempt, **_seam_kwargs(runtime, scoring_input, candidate)
        )
