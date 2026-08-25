"""TASK-016C Phase H2-B — RED tests for the runtime REPAIR control flow.

These tests drive the production ``RuntimeOperations`` composition (real
pipeline, real SQLite state, real Ollama adapters) with a scripted HTTP
transport boundary, per ``docs/TASK-016C-PHASE-H2B-AUTHORIZATION.md``.

Covered:

- runtime entry authority (no caller ingress, forged PFE, UNKNOWN relabel,
  lease/role predicates);
- REPAIR admission-to-dispatch atomicity, concurrency, and duplicates;
- REPAIR transport outcomes (``/api/tags`` vs ``/api/generate`` ambiguity,
  outer-protocol UNKNOWN vs inner known failures);
- TASK-016B language validation of the repaired candidate;
- REPAIR Judge PASS/REJECT/UNCERTAIN/UNKNOWN behavior;
- known-terminal flow (``fail_job`` exactly once, ``FAILED_FINAL``,
  ``StageDisposition.TERMINAL`` read-back defense);
- ``PhaseH2BValidatedRepairResult`` untrusted-aggregate semantics and Phase G
  direct-persistence rejection;
- no recursive repair.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pickle
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path

import pytest

import youtube_intel.h2_evidence as h2_evidence_module
import youtube_intel.scoring as scoring_module
from youtube_intel.config import load_app_config
from youtube_intel.domain import (
    Availability,
    ChannelRef,
    ContentQualityStatus,
    DiscoveryBatch,
    DiscoveryCursor,
    JobStatus,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    SubtitleFormat,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.h2_evidence import (
    PhaseH2BValidatedRepairResult,
    PrimaryFailureClass,
    build_repair_request_hash,
    repair_normalized_input_hash,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.pipeline import (
    PipelineInterrupted,
    PipelineOrchestrator,
    StageDisposition,
)
from youtube_intel.providers.ollama import (
    OllamaQualityJudgeProvider,
    OllamaScoringProvider,
)
from youtube_intel.quality import build_judge_h1_h2
from youtube_intel.retry import RetryPolicy
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.scoring_admission import (
    ScoringDispatchAdmission,
    ScoringDispatchDenied,
    ScoringDispatchIdentity,
    ScoringDispatchRole,
    UnknownProviderState,
)
from youtube_intel.state import (
    ArtifactKind,
    JobRecord,
    JobType,
    SQLiteStateRepository,
)
from youtube_intel.transcripts import (
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
)

NOW = datetime(2026, 8, 25, 8, tzinfo=UTC)
VIDEO_ID = "2A1IEBFt6Xg"
CHANNEL_ID = "UCsooa4yRKGN_zEE8iknghZA"
MODEL = "qwen3:8b"
DIGEST = "sha256:" + "4" * 64
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "subtitles"
_EN_REASON = "This repaired response explains a concrete product strategy clearly."


# ---------------------------------------------------------------------------
# Transport and provider fixtures
# ---------------------------------------------------------------------------


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
        self.requests: list[tuple[str, str, bytes | None]] = []

    def __call__(self, request: object, timeout: float) -> _Response:
        self.requests.append(
            (getattr(request, "method"), getattr(request, "full_url"), getattr(request, "data"))
        )
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return _Response(response)

    @property
    def tags_calls(self) -> int:
        return sum(1 for _, url, _ in self.requests if url.endswith("/api/tags"))

    @property
    def generate_calls(self) -> int:
        return sum(1 for _, url, _ in self.requests if url.endswith("/api/generate"))


def _tags() -> dict:
    return {"models": [{"name": MODEL, "digest": "4" * 64}]}


def _outer(inner: str) -> bytes:
    return json.dumps(
        {"model": MODEL, "response": inner, "done": True},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _valid_candidate(reason: str = _EN_REASON, *, score: int = 8) -> str:
    return json.dumps(
        {"score": score, "reason": reason, "topics": ["product"], "should_summarize": True},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _judge_raw(status: str) -> str:
    if status == "PASS":
        payload = {
            "status": "PASS",
            "decision_confidence": "HIGH",
            "grounding_confidence": "MEDIUM",
            "usefulness_confidence": "MEDIUM",
            "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
            "reason": None,
            "evidence_ids": ["title-1"],
        }
    elif status == "REJECT":
        payload = {
            "status": "REJECT",
            "decision_confidence": "HIGH",
            "grounding_confidence": "LOW",
            "usefulness_confidence": "LOW",
            "signals": ["LOW_INFORMATION"],
            "reason": "LOW_INFORMATION",
            "evidence_ids": [],
        }
    else:
        payload = {
            "status": "UNCERTAIN",
            "decision_confidence": "LOW",
            "grounding_confidence": "LOW",
            "usefulness_confidence": "LOW",
            "signals": ["GROUNDING_INSUFFICIENT"],
            "reason": "GROUNDING_INSUFFICIENT",
            "evidence_ids": [],
        }
    return json.dumps(payload)


class _DiscoverySource:
    def discover(self, channel: ChannelRef, cursor: DiscoveryCursor) -> DiscoveryBatch:
        return DiscoveryBatch(
            channel_id=channel.channel_id,
            video_ids=(VIDEO_ID,),
            next_cursor=DiscoveryCursor(
                channel_id=channel.channel_id,
                last_checked_at=NOW,
                latest_published_at=NOW,
                latest_video_id=VIDEO_ID,
            ),
            call=ProviderCallMetadata(
                provider="controlled-rss-boundary", started_at=NOW, finished_at=NOW
            ),
        )


class _MetadataProvider:
    def fetch(self, video_id: str) -> VideoMetadata:
        return VideoMetadata(
            video_id=VIDEO_ID,
            channel_id=CHANNEL_ID,
            channel_name="Public test channel",
            title="A short public product lesson",
            description="Public metadata fixture.",
            source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
            published_at=NOW,
            duration_seconds=120,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        )


class _SubtitleAdapter:
    provider_name = "controlled-subtitle-boundary"
    provider_version = "fixture-v1"

    def __init__(self) -> None:
        self._call = ProviderCallMetadata(
            provider=self.provider_name,
            provider_version=self.provider_version,
            started_at=NOW,
            finished_at=NOW,
        )

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        return SubtitleTrackListing(
            tracks=(
                SubtitleTrack(
                    source_type=TranscriptSourceType.MANUAL_SUBTITLE,
                    language="en",
                    source_format=SubtitleFormat.JSON3,
                    name="English",
                    url="https://example.invalid/subtitle",
                    provider_position=0,
                ),
            ),
            call=self._call,
        )

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        return SubtitleReadResult(
            body=(FIXTURES / "manual_en.json3").read_bytes(),
            call=self._call,
        )


def _project(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "vault").mkdir(parents=True)
    (tmp_path / "config" / "channels.yaml").write_text(
        f"channels:\n  - channel_id: {CHANNEL_ID}\n", encoding="utf-8"
    )
    (tmp_path / "config" / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
  output_language: en
local_scoring:
  model: {MODEL}
  expected_model_digest: {DIGEST}
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
  vault_root: {tmp_path / 'vault'}
  vault_subdir: YouTube Intel
""",
        encoding="utf-8",
    )
    return tmp_path


def _runtime(tmp_path: Path, transport: _FakeTransport) -> RuntimeOperations:
    project = _project(tmp_path)
    config = load_app_config(
        channels_path=project / "config" / "channels.yaml",
        settings_path=project / "config" / "settings.yaml",
    )
    prompt = resources.files("youtube_intel").joinpath("prompts", "scoring.md").read_text(
        encoding="utf-8"
    )
    return RuntimeOperations(
        config=config,
        project_root=project,
        dependencies=RuntimeDependencies(
            discovery_source=_DiscoverySource(),
            metadata_provider=_MetadataProvider(),
            subtitle_adapter_factory=lambda: _SubtitleAdapter(),
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


def _run_process(runtime: RuntimeOperations) -> None:
    assert runtime.check(channel=None, limit=None).safe_message
    runtime.process(video=VIDEO_ID, resume=False)


def _scoring_job(runtime: RuntimeOperations) -> JobRecord:
    job = runtime._repository.latest_video_job(
        VIDEO_ID, target_stage=ProcessingStage.SCORING
    )
    assert job is not None
    return job


def _repair_script(
    *,
    primary_inner: str | bytes | Exception,
    repair_inner: str | bytes | Exception | None = None,
    judge_status: str | Exception | None = None,
    repair_tags: object | None = None,
    judge_tags: object | None = None,
) -> list[object]:
    """Build the transport script: PRIMARY(tags,generate)[, REPAIR(tags,generate)][, JUDGE(tags,generate)]."""

    script: list[object] = [_tags()]
    script.append(_outer(primary_inner) if isinstance(primary_inner, str) else primary_inner)
    if repair_inner is not None or repair_tags is not None:
        script.append(repair_tags if repair_tags is not None else _tags())
        if repair_inner is not None:
            script.append(
                _outer(repair_inner) if isinstance(repair_inner, str) else repair_inner
            )
    if judge_status is not None or judge_tags is not None:
        script.append(judge_tags if judge_tags is not None else _tags())
        if judge_status is not None:
            script.append(
                _outer(_judge_raw(judge_status))
                if isinstance(judge_status, str)
                else judge_status
            )
    return script


# ---------------------------------------------------------------------------
# ENTRY / AUTHORITY
# ---------------------------------------------------------------------------


def test_no_public_repair_entry_or_h2c_api_exists(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, _FakeTransport([]))
    for forbidden in (
        "repair",
        "run_repair",
        "dispatch_repair",
        "repair_dispatch",
        "finalize_repair",
        "h2c_finalize",
        "mint_repair_success",
        "persist_validated_repair",
        "verify_h2b_result",
        "_admit_runtime_repair",
        "_primary_failure_continuation",
    ):
        assert not hasattr(runtime, forbidden), forbidden
    assert not hasattr(scoring_module, "PhaseHTrustedRepairSuccess")
    assert not hasattr(h2_evidence_module, "PhaseHTrustedRepairSuccess")


def test_forged_eligible_pfe_cannot_start_repair_without_actual_primary(
    tmp_path: Path,
) -> None:
    import importlib.util
    import sys

    from youtube_intel.h2_evidence import build_primary_trusted_context

    support_path = Path(__file__).with_name("test_task016c_phase_h2a_evidence.py")
    specification = importlib.util.spec_from_file_location(
        "_h2a_evidence_support", support_path
    )
    assert specification is not None and specification.loader is not None
    support = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = support
    specification.loader.exec_module(support)

    transport = _FakeTransport([_tags(), _tags()])
    runtime = _runtime(tmp_path, transport)
    # Build self-consistent eligible evidence against the runtime's own trusted
    # context: even a PFE that independently verifies cannot start a repair.
    scoring_input = support._scoring_input()
    ctx = build_primary_trusted_context(
        scoring_input=scoring_input,
        model=MODEL,
        model_digest=DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )
    pfe = support._schema_invalid_pfe(ctx, scoring_input)
    admission = ScoringDispatchAdmission(
        repository=runtime._repository,
        job_id="scoring-job",
        owner=runtime._runtime_owner,
    )

    # The rejected authoritative executor shape is gone: there is no
    # caller-facing H2-B ingress that accepts a PFE and contacts a provider.
    assert not hasattr(runtime, "_h2b_execute_repair")
    # Caller REPAIR admission stays denied.
    with pytest.raises(ScoringDispatchDenied):
        admission.admit(
            ScoringDispatchIdentity(
                role=ScoringDispatchRole.REPAIR,
                operation="local-scoring-repair-v1",
                normalized_input_hash="a" * 64,
                request_hash="a" * 64,
            ),
            now=datetime.now(UTC),
        )
    # No actual PRIMARY execution consumed the PRIMARY role in this runtime, so
    # even the state-only REPAIR consumption is denied before any contact.
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_role(
            ScoringDispatchIdentity(
                role=ScoringDispatchRole.REPAIR,
                operation="local-scoring-repair-v1",
                normalized_input_hash="a" * 64,
                request_hash="a" * 64,
            ),
            now=datetime.now(UTC),
        )

    assert transport.requests == []
    del pfe


def test_unknown_primary_failure_is_not_relabeled_into_repair_eligibility(
    tmp_path: Path,
) -> None:
    transport = _FakeTransport([_tags(), TimeoutError("transport interrupted")])
    runtime = _runtime(tmp_path, transport)
    provider = OllamaScoringProvider(
        settings=runtime._config.settings.local_scoring,
        prompt=resources.files("youtube_intel")
        .joinpath("prompts", "scoring.md")
        .read_text(encoding="utf-8"),
        transport=transport,
    )

    with pytest.raises(UnknownProviderState):
        runtime._dispatch_primary_attempt_after_admission(provider, object())  # type: ignore[arg-type]

    # The ambiguous PRIMARY attempt exposes no eligible parse-failure capture.
    assert runtime._h2b_eligible_parse_failure_capture(provider) is None
    assert transport.generate_calls == 0


def test_repair_role_consumption_requires_active_lease_and_primary_role(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path, _FakeTransport([]))
    admission = runtime._scoring_admission_for("missing-job")

    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_role(
            ScoringDispatchIdentity(
                role=ScoringDispatchRole.REPAIR,
                operation="local-scoring-repair-v1",
                normalized_input_hash="a" * 64,
                request_hash="a" * 64,
            ),
            now=datetime.now(UTC),
        )
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_judge_role(
            ScoringDispatchIdentity(
                role=ScoringDispatchRole.REPAIR_JUDGE,
                operation="local-content-quality-v1",
                normalized_input_hash="b" * 64,
                request_hash="b" * 64,
            ),
            now=datetime.now(UTC),
        )


# ---------------------------------------------------------------------------
# H2-B full flow: REPAIR PASS aggregate (schema/parse PRIMARY failure)
# ---------------------------------------------------------------------------


def test_repair_pass_produces_untrusted_aggregate_without_persistence(
    tmp_path: Path,
) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(),
            judge_status="PASS",
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    aggregate = runtime._last_h2b_validated_repair_result
    assert type(aggregate) is PhaseH2BValidatedRepairResult
    # Exactly one admitted REPAIR and one admitted REPAIR_JUDGE contact.
    assert transport.tags_calls == 3
    assert transport.generate_calls == 3
    # The aggregate binds the exact REPAIR identity and raw evidence.
    rni = aggregate.repair_normalized_input
    assert aggregate.repair_request_hash == build_repair_request_hash(rni)
    assert aggregate.rni_hash == repair_normalized_input_hash(rni)
    assert aggregate.repair_payload_sha256 == hashlib.sha256(
        aggregate.repair_payload_bytes
    ).hexdigest()
    assert aggregate.repair_payload_length == len(aggregate.repair_payload_bytes)
    assert aggregate.repair_raw_sha256 == hashlib.sha256(
        aggregate.repair_raw_utf8.encode("utf-8")
    ).hexdigest()
    assert aggregate.repair_raw_length == len(aggregate.repair_raw_utf8.encode("utf-8"))
    assert aggregate.failure_class is PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID
    assert aggregate.language_evidence.result == "VALID"
    assert aggregate.judge_evidence.role == "REPAIR"
    assert aggregate.judge_result.status is ContentQualityStatus.PASS
    h1, h2 = build_judge_h1_h2(aggregate.judge_operation_input)
    assert (aggregate.judge_h1, aggregate.judge_h2) == (h1, h2)
    payload = json.loads(aggregate.repair_payload_bytes.decode("utf-8"))
    assert aggregate.repair_prompt == payload["prompt"]
    # The repaired candidate parses from the exact REPAIR raw, and the exact
    # outbound REPAIR body is the payload whose identity was derived.
    generate_bodies = [
        data for _, url, data in transport.requests if url.endswith("/api/generate")
    ]
    assert generate_bodies[1] == aggregate.repair_payload_bytes

    # H2-B performs no persistence of any kind.
    repository = runtime._repository
    assert repository.get_provider_call(aggregate.repair_request_hash) is None
    assert (
        repository.latest_artifact(VIDEO_ID, ArtifactKind.SCORING_STRUCTURED) is None
    )
    video = repository.get_video(VIDEO_ID)
    assert video is not None
    assert video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
    # Without H2-C the job cannot succeed: the existing generic path finalizes it.
    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert not hasattr(scoring_module, "PhaseHTrustedRepairSuccess")

    # Corrected H2-B: deterministic gate PASS evidence plus finalizer-produced
    # TrustedScoreResult and sealed structured bytes/hash/length.
    from youtube_intel.quality import (
        TrustedScoreResult,
        build_content_quality_input_hash,
    )
    from youtube_intel.scoring import _sealed_trusted_score_result_serializer

    assert aggregate.deterministic_gate_status == "PASS"
    assert aggregate.quality_input_hash == build_content_quality_input_hash(
        aggregate.judge_input
    )
    assert aggregate.judge_input.scoring_request_hash == aggregate.repair_request_hash
    trusted_result = aggregate.finalizer_trusted_result
    assert type(trusted_result) is TrustedScoreResult
    # Dual binding: the semantic score keeps the PRIMARY request hash while the
    # REPAIR transport provenance stays separate and intact.
    assert (
        trusted_result.result.request_hash
        == aggregate.primary_trusted_context.request_hash
    )
    assert trusted_result.result.request_hash != aggregate.repair_request_hash
    assert aggregate.structured_result_bytes == _sealed_trusted_score_result_serializer(
        trusted_result
    )
    assert aggregate.structured_result_sha256 == hashlib.sha256(
        aggregate.structured_result_bytes
    ).hexdigest()
    assert aggregate.structured_result_length == len(aggregate.structured_result_bytes)


# ---------------------------------------------------------------------------
# REPAIR TRANSPORT outcomes
# ---------------------------------------------------------------------------


def test_repair_tags_timeout_is_unknown_provider_state(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_tags=TimeoutError("tags lost"),
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert transport.tags_calls == 2
    assert transport.generate_calls == 1  # only PRIMARY generate
    assert runtime._last_h2b_validated_repair_result is None
    # No second REPAIR and no success persistence.
    assert runtime._repository.get_video(VIDEO_ID).pipeline_status is (
        PipelineStatus.TRANSCRIPT_READY
    )


def test_repair_generate_timeout_is_unknown_provider_state(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=TimeoutError("generate interrupted"),
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert transport.tags_calls == 2
    assert transport.generate_calls == 2
    assert runtime._last_h2b_validated_repair_result is None


def test_repair_malformed_outer_body_is_unknown_not_known_failure(
    tmp_path: Path,
) -> None:
    transport = _FakeTransport(
        _repair_script(primary_inner="{not-json", repair_inner=b"not-json{{")
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert job.last_error_message != "REPAIR_SCHEMA_OR_PARSE_INVALID"
    assert transport.generate_calls == 2


def test_repair_duplicate_outer_keys_is_unknown(tmp_path: Path) -> None:
    ambiguous = b'{"model":"qwen3:8b","response":"x","response":"y","done":true}'
    transport = _FakeTransport(
        _repair_script(primary_inner="{not-json", repair_inner=ambiguous)
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "UNKNOWN_PROVIDER_STATE"


# ---------------------------------------------------------------------------
# REPAIR VALIDATION known terminal failures
# ---------------------------------------------------------------------------


def test_repair_schema_failure_is_terminal_without_judge(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(score=99),
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "INVALID_RESPONSE"
    assert job.last_error_message == "REPAIR_SCHEMA_OR_PARSE_INVALID"
    assert transport.tags_calls == 2
    assert transport.generate_calls == 2  # no Judge transport at all
    assert runtime._last_h2b_validated_repair_result is None
    # fail_job exactly once: one job attempt row, no duplicate generic failure.
    attempts = runtime._repository.list_job_attempts(job.job_id)
    assert len(attempts) == 1
    assert attempts[0].error_message == "REPAIR_SCHEMA_OR_PARSE_INVALID"


def test_repair_language_failure_is_terminal_without_judge(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(
                reason="这是完全用中文撰写的修复理由，没有任何英文内容。"
            ),
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "INVALID_RESPONSE"
    assert job.last_error_message == "REPAIR_LANGUAGE_INVALID"
    assert transport.tags_calls == 2
    assert transport.generate_calls == 2
    assert runtime._last_h2b_validated_repair_result is None


# ---------------------------------------------------------------------------
# REPAIR JUDGE outcomes
# ---------------------------------------------------------------------------


def test_repair_judge_reject_is_terminal(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(),
            judge_status="REJECT",
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_message == "REPAIR_JUDGE_REJECT"
    assert transport.tags_calls == 3
    assert transport.generate_calls == 3
    assert runtime._last_h2b_validated_repair_result is None
    assert len(runtime._repository.list_job_attempts(job.job_id)) == 1


def test_repair_judge_uncertain_is_terminal_not_unknown(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(),
            judge_status="UNCERTAIN",
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "INVALID_RESPONSE"
    assert job.last_error_message == "REPAIR_JUDGE_UNCERTAIN"
    assert runtime._last_h2b_validated_repair_result is None


def test_repair_judge_tags_timeout_is_unknown_not_uncertain(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(),
            judge_tags=TimeoutError("judge tags lost"),
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert job.last_error_message != "REPAIR_JUDGE_UNCERTAIN"
    assert transport.tags_calls == 3
    assert transport.generate_calls == 2  # judge generate never ran
    assert runtime._last_h2b_validated_repair_result is None


def test_repair_judge_generate_timeout_is_unknown_not_uncertain(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(),
            judge_status=TimeoutError("judge generate lost"),
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert job.last_error_message != "REPAIR_JUDGE_UNCERTAIN"
    assert transport.generate_calls == 3


# ---------------------------------------------------------------------------
# Eligible PRIMARY failure classes: LANGUAGE_INVALID and JUDGE failures
# ---------------------------------------------------------------------------


def test_language_invalid_primary_failure_is_repaired(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner=_valid_candidate(
                reason="这是完全用中文撰写的理由，没有任何英文内容。"
            ),
            repair_inner=_valid_candidate(),
            judge_status="PASS",
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    aggregate = runtime._last_h2b_validated_repair_result
    assert type(aggregate) is PhaseH2BValidatedRepairResult
    assert aggregate.failure_class is PrimaryFailureClass.LANGUAGE_INVALID
    assert transport.tags_calls == 3
    assert transport.generate_calls == 3


def test_judge_reject_primary_failure_is_repaired(tmp_path: Path) -> None:
    script: list[object] = [
        _tags(),
        _outer(_valid_candidate()),
        _tags(),
        _outer(_judge_raw("REJECT")),  # PRIMARY Judge rejects
        _tags(),
        _outer(
            _valid_candidate(
                reason="The repaired response explains the concrete product strategy with clear and useful trade-offs."
            )
        ),
        _tags(),
        _outer(_judge_raw("PASS")),
    ]
    transport = _FakeTransport(script)
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    aggregate = runtime._last_h2b_validated_repair_result
    assert type(aggregate) is PhaseH2BValidatedRepairResult
    assert aggregate.failure_class is PrimaryFailureClass.JUDGE_REJECT
    assert aggregate.primary_failure_evidence.judge_evidence.role == "PRIMARY"
    assert (
        aggregate.primary_failure_evidence.judge_evidence.derived_result.status
        is ContentQualityStatus.REJECT
    )
    assert transport.tags_calls == 4
    assert transport.generate_calls == 4


def test_judge_uncertain_primary_failure_is_repaired(tmp_path: Path) -> None:
    script: list[object] = [
        _tags(),
        _outer(_valid_candidate()),
        _tags(),
        _outer(_judge_raw("UNCERTAIN")),
        _tags(),
        _outer(
            _valid_candidate(
                reason="This repaired response restates the concrete product strategy with several practical trade-offs."
            )
        ),
        _tags(),
        _outer(_judge_raw("PASS")),
    ]
    transport = _FakeTransport(script)
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    aggregate = runtime._last_h2b_validated_repair_result
    assert type(aggregate) is PhaseH2BValidatedRepairResult
    assert aggregate.failure_class is PrimaryFailureClass.JUDGE_UNCERTAIN


def test_primary_judge_transport_failure_is_not_repair_eligible(tmp_path: Path) -> None:
    script: list[object] = [
        _tags(),
        _outer(_valid_candidate()),
        TimeoutError("primary judge tags lost"),
    ]
    transport = _FakeTransport(script)
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    # The legacy Judge path collapses transport failure to UNCERTAIN; without
    # trustworthy Judge raw the failure is not repair-eligible, so the original
    # known-failure route finalizes the job (no REPAIR contact).
    assert job.last_error_code == "INVALID_RESPONSE"
    assert runtime._last_h2b_validated_repair_result is None
    assert transport.tags_calls == 2
    assert transport.generate_calls == 1


# ---------------------------------------------------------------------------
# NO RECURSION / duplicates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "repair_inner",
    [
        _valid_candidate(score=99),  # schema failure
        _valid_candidate(reason="这是完全用中文撰写的修复理由，没有任何英文内容。"),
        json.dumps({"model": MODEL, "response": "{not-json", "done": True}),
    ],
    ids=["schema", "language", "inner-json"],
)
def test_no_second_repair_after_known_repair_failure(
    tmp_path: Path, repair_inner: str
) -> None:
    transport = _FakeTransport(
        _repair_script(primary_inner="{not-json", repair_inner=repair_inner)
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    # A second REPAIR attempt on the same job attempt is rejected before any
    # further transport (the REPAIR role is already consumed).
    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    admission = runtime._scoring_admission_for(job.job_id)
    before = len(transport.requests)

    # The one-shot REPAIR role is already consumed and the terminal job owns no
    # active lease; the state-only consumption denies any second REPAIR, and no
    # dispatch authority exists anywhere regardless.
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_role(
            ScoringDispatchIdentity(
                role=ScoringDispatchRole.REPAIR,
                operation="local-scoring-repair-v1",
                normalized_input_hash="a" * 64,
                request_hash="a" * 64,
            ),
            now=datetime.now(UTC),
        )

    assert len(transport.requests) == before


@pytest.mark.parametrize(
    "judge_status", ["REJECT", "UNCERTAIN"], ids=["reject", "uncertain"]
)
def test_no_second_repair_after_judge_failure(
    tmp_path: Path, judge_status: str
) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(),
            judge_status=judge_status,
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_message in {
        "REPAIR_JUDGE_REJECT",
        "REPAIR_JUDGE_UNCERTAIN",
    }
    admission = runtime._scoring_admission_for(job.job_id)
    before = len(transport.requests)

    # The one-shot REPAIR role is already consumed and the terminal job owns no
    # active lease; the state-only consumption denies any second REPAIR, and no
    # dispatch authority exists anywhere regardless.
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_role(
            ScoringDispatchIdentity(
                role=ScoringDispatchRole.REPAIR,
                operation="local-scoring-repair-v1",
                normalized_input_hash="a" * 64,
                request_hash="a" * 64,
            ),
            now=datetime.now(UTC),
        )

    assert len(transport.requests) == before


def test_no_second_repair_after_unknown_provider_state(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=TimeoutError("generate interrupted"),
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "UNKNOWN_PROVIDER_STATE"
    admission = runtime._scoring_admission_for(job.job_id)
    before = len(transport.requests)

    # The one-shot REPAIR role is already consumed and the terminal job owns no
    # active lease; the state-only consumption denies any second REPAIR, and no
    # dispatch authority exists anywhere regardless.
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_role(
            ScoringDispatchIdentity(
                role=ScoringDispatchRole.REPAIR,
                operation="local-scoring-repair-v1",
                normalized_input_hash="a" * 64,
                request_hash="a" * 64,
            ),
            now=datetime.now(UTC),
        )

    assert len(transport.requests) == before


def test_no_second_repair_judge_after_judge_consumed(tmp_path: Path) -> None:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(),
            judge_status="REJECT",
        )
    )
    runtime = _runtime(tmp_path, transport)

    _run_process(runtime)

    job = _scoring_job(runtime)
    admission = runtime._scoring_admission_for(job.job_id)
    before = len(transport.requests)

    # The one-shot REPAIR_JUDGE role is already consumed; the state-only
    # consumption denies a second Judge, and no dispatch authority exists.
    with pytest.raises(ScoringDispatchDenied):
        admission.consume_repair_judge_role(
            ScoringDispatchIdentity(
                role=ScoringDispatchRole.REPAIR_JUDGE,
                operation="local-content-quality-v1",
                normalized_input_hash="b" * 64,
                request_hash="b" * 64,
            ),
            now=datetime.now(UTC),
        )

    assert len(transport.requests) == before


def test_concurrent_repair_attempts_contact_the_provider_exactly_once(
    tmp_path: Path,
) -> None:
    transport = _FakeTransport([_tags(), _tags()])
    runtime = _runtime(tmp_path, transport)
    repository = runtime._repository
    repository.save_discovery_batch(
        DiscoveryBatch(
            channel_id=CHANNEL_ID,
            video_ids=(VIDEO_ID,),
            next_cursor=DiscoveryCursor(
                channel_id=CHANNEL_ID,
                last_checked_at=NOW,
                latest_published_at=NOW,
                latest_video_id=VIDEO_ID,
                provider_cursor="cursor-1",
            ),
            call=ProviderCallMetadata(provider="fake", started_at=NOW, finished_at=NOW),
        ),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="runtime-v1",
        now=NOW,
    )
    repository.advance_pipeline(
        VIDEO_ID,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="runtime-v1",
        now=NOW,
    )
    repository.advance_pipeline(
        VIDEO_ID,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="runtime-v1",
        now=NOW,
    )
    repository.create_job(
        job_id="scoring-job",
        scope_key=f"video:{VIDEO_ID}:SCORING",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    claimed = repository.claim_next_job(
        owner=runtime._runtime_owner,
        lease_until=NOW + timedelta(minutes=5),
        now=NOW,
    )
    assert claimed is not None
    admission = runtime._scoring_admission_for(claimed.job_id)
    admission.admit(
        ScoringDispatchIdentity(
            role=ScoringDispatchRole.PRIMARY,
            operation="local-scoring",
            normalized_input_hash="p" * 64,
            request_hash="p" * 64,
        ),
        now=NOW,
    )

    def attempt() -> str:
        try:
            runtime._scoring_admission_for(claimed.job_id).consume_repair_role(
                ScoringDispatchIdentity(
                    role=ScoringDispatchRole.REPAIR,
                    operation="local-scoring-repair-v1",
                    normalized_input_hash="c" * 64,
                    request_hash="c" * 64,
                ),
                now=NOW,
            )
        except ScoringDispatchDenied:
            return "denied"
        return "consumed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = set(executor.map(lambda _: attempt(), (0, 1)))

    # Exactly one concurrent consumer wins the one-shot REPAIR role; the loser
    # is denied before any contact, and the state-only operation never grants
    # dispatch authority, so zero external transport occurs.
    assert results == {"denied", "consumed"}
    assert transport.requests == []


# ---------------------------------------------------------------------------
# Pipeline TERMINAL disposition
# ---------------------------------------------------------------------------


def _pipeline_repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        DiscoveryBatch(
            channel_id=CHANNEL_ID,
            video_ids=(VIDEO_ID,),
            next_cursor=DiscoveryCursor(
                channel_id=CHANNEL_ID,
                last_checked_at=NOW,
                latest_published_at=NOW,
                latest_video_id=VIDEO_ID,
                provider_cursor="cursor-1",
            ),
            call=ProviderCallMetadata(provider="fake", started_at=NOW, finished_at=NOW),
        ),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="runtime-v1",
        now=NOW,
    )
    repository.advance_pipeline(
        VIDEO_ID,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="runtime-v1",
        now=NOW,
    )
    repository.advance_pipeline(
        VIDEO_ID,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="runtime-v1",
        now=NOW,
    )
    repository.create_job(
        job_id="terminal-job",
        scope_key=f"video:{VIDEO_ID}:SCORING",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    return repository


def _orchestrator(repository: SQLiteStateRepository, handler) -> PipelineOrchestrator:
    return PipelineOrchestrator(
        repository=repository,
        planner=PipelineJobPlanner(
            repository=repository, pipeline_version="runtime-v1", max_attempts=3
        ),
        owner="runtime-a",
        lease_seconds=300,
        retry_policy=RetryPolicy(1, 1, 0),
        handlers={ProcessingStage.SCORING: handler},
        clock=lambda: NOW,
    )


def test_known_terminal_disposition_suppresses_duplicate_generic_fail(
    tmp_path: Path,
) -> None:
    from youtube_intel.domain import ErrorCode

    repository = _pipeline_repository(tmp_path)
    claimed = repository.claim_next_job(
        owner="runtime-a",
        lease_until=NOW + timedelta(minutes=5),
        now=NOW,
    )
    assert claimed is not None

    def handler(job: JobRecord, _video) -> StageDisposition:
        repository.fail_job(
            job.job_id,
            owner="runtime-a",
            error_code=ErrorCode.INVALID_RESPONSE,
            error_message="REPAIR_SCHEMA_OR_PARSE_INVALID",
            retry_at=None,
            now=NOW,
        )
        return StageDisposition.TERMINAL

    _orchestrator(repository, handler)._execute(claimed, now=NOW)

    saved = repository.get_job(claimed.job_id)
    assert saved is not None
    assert saved.status is JobStatus.FAILED_FINAL
    assert saved.last_error_message == "REPAIR_SCHEMA_OR_PARSE_INVALID"
    attempts = repository.list_job_attempts(claimed.job_id)
    assert len(attempts) == 1


def test_fake_terminal_disposition_preserves_generic_failure(tmp_path: Path) -> None:
    repository = _pipeline_repository(tmp_path)
    claimed = repository.claim_next_job(
        owner="runtime-a",
        lease_until=NOW + timedelta(minutes=5),
        now=NOW,
    )
    assert claimed is not None

    def handler(job: JobRecord, _video) -> StageDisposition:
        del job
        return StageDisposition.TERMINAL  # claims terminal handling but did not fail the job

    _orchestrator(repository, handler)._execute(claimed, now=NOW)

    saved = repository.get_job(claimed.job_id)
    assert saved is not None
    # The repository read-back disproves the fake disposition: generic failure runs.
    assert saved.status is JobStatus.FAILED_FINAL
    assert saved.last_error_message == (
        "claimed job is incompatible with the persisted pipeline state"
    )


def test_unrelated_generic_failure_behavior_is_unchanged(tmp_path: Path) -> None:
    repository = _pipeline_repository(tmp_path)
    claimed = repository.claim_next_job(
        owner="runtime-a",
        lease_until=NOW + timedelta(minutes=5),
        now=NOW,
    )
    assert claimed is not None

    def handler(job: JobRecord, _video) -> None:
        del job
        raise RuntimeError("ordinary stage failure")

    _orchestrator(repository, handler)._execute(claimed, now=NOW)

    saved = repository.get_job(claimed.job_id)
    assert saved is not None
    assert saved.status is JobStatus.RETRY_PENDING
    assert saved.last_error_code == "LOCAL_RESOURCE"


def test_crash_after_failed_final_keeps_job_terminal_on_restart(tmp_path: Path) -> None:
    from youtube_intel.domain import ErrorCode

    repository = _pipeline_repository(tmp_path)
    claimed = repository.claim_next_job(
        owner="runtime-a",
        lease_until=NOW + timedelta(minutes=5),
        now=NOW,
    )
    assert claimed is not None

    def handler(job: JobRecord, _video) -> StageDisposition:
        repository.fail_job(
            job.job_id,
            owner="runtime-a",
            error_code=ErrorCode.INVALID_RESPONSE,
            error_message="REPAIR_JUDGE_REJECT",
            retry_at=None,
            now=NOW,
        )
        raise PipelineInterrupted("crash before the disposition returns")

    with pytest.raises(PipelineInterrupted):
        _orchestrator(repository, handler)._execute(claimed, now=NOW)

    restarted = SQLiteStateRepository(tmp_path / "state.sqlite")
    restarted.initialize(now=NOW + timedelta(minutes=1))
    after_restart = restarted.get_job(claimed.job_id)
    assert after_restart is not None
    assert after_restart.status is JobStatus.FAILED_FINAL
    assert after_restart.last_error_message == "REPAIR_JUDGE_REJECT"
    assert (
        restarted.claim_next_job(
            owner="runtime-b",
            lease_until=NOW + timedelta(minutes=6),
            now=NOW + timedelta(minutes=1),
        )
        is None
    )


# ---------------------------------------------------------------------------
# Phase G direct persistence rejection (including low-level forgery)
# ---------------------------------------------------------------------------


def _valid_aggregate(
    tmp_path: Path,
) -> tuple[RuntimeOperations, PhaseH2BValidatedRepairResult]:
    transport = _FakeTransport(
        _repair_script(
            primary_inner="{not-json",
            repair_inner=_valid_candidate(),
            judge_status="PASS",
        )
    )
    runtime = _runtime(tmp_path / "aggregate", transport)
    _run_process(runtime)
    aggregate = runtime._last_h2b_validated_repair_result
    assert type(aggregate) is PhaseH2BValidatedRepairResult
    return runtime, aggregate


def test_valid_h2b_result_cannot_persist_directly(tmp_path: Path) -> None:
    runtime, aggregate = _valid_aggregate(tmp_path)
    entry = runtime._trusted_persistence_entry(
        job_id="scoring-job", owner=runtime._runtime_owner, pipeline_version="runtime-v1"
    )
    before_video = runtime._repository.get_video(VIDEO_ID)

    with pytest.raises(ValueError):
        entry.persist_success(aggregate)  # type: ignore[arg-type]

    assert runtime._repository.get_video(VIDEO_ID) == before_video
    assert runtime._repository.get_provider_call(aggregate.repair_request_hash) is None


def test_forged_h2b_results_cannot_gain_persistence_authority(tmp_path: Path) -> None:
    runtime, aggregate = _valid_aggregate(tmp_path)
    entry = runtime._trusted_persistence_entry(
        job_id="scoring-job", owner=runtime._runtime_owner, pipeline_version="runtime-v1"
    )

    forged_new = object.__new__(PhaseH2BValidatedRepairResult)
    mutated = copy.copy(aggregate)
    object.__setattr__(mutated, "repair_request_hash", "f" * 64)
    structured_mutated = copy.copy(aggregate)
    object.__setattr__(structured_mutated, "structured_result_sha256", "e" * 64)

    for candidate in (forged_new, mutated, structured_mutated):
        with pytest.raises((ValueError, TypeError, AttributeError)):
            entry.persist_success(candidate)  # type: ignore[arg-type]

    # The finalizer-produced TrustedScoreResult is non-copyable and
    # non-serializable, so deep-copy/pickle restoration of the aggregate fails
    # closed before any forged restored shape can even reach persistence.
    with pytest.raises(TypeError):
        copy.deepcopy(aggregate)
    with pytest.raises(TypeError):
        pickle.dumps(aggregate)
