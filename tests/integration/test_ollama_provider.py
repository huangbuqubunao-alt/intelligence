"""Offline integration tests for the injected Ollama HTTP transport."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from http.client import IncompleteRead
from pathlib import Path
from types import TracebackType
from typing import Any

import pytest

from youtube_intel.config import LocalScoringSettings, load_app_config
from youtube_intel.domain import (
    Availability,
    ContentQualityInput,
    ContentQualityReason,
    ContentQualitySignal,
    ContentQualityStatus,
    ErrorCode,
    JobStatus,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    ScoringEvidence,
    ScoringEvidenceSource,
    ScoringInput,
    VideoMetadata,
)
from youtube_intel.providers.ollama import (
    OllamaProviderError,
    OllamaQualityJudgeProvider,
    OllamaScoringProvider,
    parse_scoring_candidate,
)
from youtube_intel.quality import build_content_quality_input_hash, build_judge_h1_h2
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.scoring import (
    PrimaryScoringAttempt,
    build_primary_scoring_attempt,
    build_scoring_input,
)
from youtube_intel.scoring_admission import ScoringDispatchAdmission
from youtube_intel.state import ArtifactKind, JobType, ProviderCallStatus

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "scoring"
PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "scoring.md"


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if not isinstance(self._payload, bytes):
            return json.dumps(self._payload).encode("utf-8")
        return self._payload

    def close(self) -> None:
        self.closed = True


class _IncompleteResponse(_Response):
    def __init__(self, partial: bytes) -> None:
        super().__init__(partial)

    def read(self, size: int = -1) -> bytes:
        raise IncompleteRead(self._payload, len(self._payload) + 1)


class _FakeTransport:
    def __init__(self, responses: list[object]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str, bytes | None]] = []

    def __call__(self, request: object, timeout: float) -> _Response:
        method = getattr(request, "method")
        url = getattr(request, "full_url")
        data = getattr(request, "data")
        self.requests.append((method, url, data))
        response = self._responses.pop(0)
        if isinstance(response, _Response):
            return response
        return _Response(response)


def _assert_exception_graph_is_redacted(error: BaseException, sentinel: str) -> None:
    seen: set[int] = set()

    def visit(value: Any) -> None:
        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        if isinstance(value, str):
            assert sentinel not in value
            return
        if isinstance(value, BaseException):
            visit(value.args)
            visit(value.__cause__)
            visit(value.__context__)
            visit(vars(value))
            visit_traceback(value.__traceback__)
            return
        if isinstance(value, dict):
            for item in value.values():
                visit(item)
            return
        if isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item)

    def visit_traceback(traceback: TracebackType | None) -> None:
        while traceback is not None:
            module_name = str(traceback.tb_frame.f_globals.get("__name__", ""))
            if not module_name.startswith("youtube_intel"):
                traceback = traceback.tb_next
                continue
            for name, local in traceback.tb_frame.f_locals.items():
                try:
                    visit(local)
                except AssertionError as error:
                    msg = (
                        "sentinel reached traceback local "
                        f"{traceback.tb_frame.f_code.co_name}.{name}"
                    )
                    raise AssertionError(msg) from error
            traceback = traceback.tb_next

    visit(error)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:" + ("b" * 64),
    )


def _input(
    *,
    transcript_text: str = "A sufficiently long canonical transcript for scoring.",
    output_language: str = "en",
) -> object:
    return build_scoring_input(
        video=_video(),
        transcript_text=transcript_text,
        language="en",
        output_language=output_language,
        settings=_settings(),
    )


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-123",
        channel_id="channel-123",
        channel_name="Example Channel",
        title="A useful title",
        source_url="https://example.invalid/watch?v=video-123",
        published_at=datetime(2026, 7, 19, tzinfo=UTC),
        duration_seconds=120,
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


class _RepairFlowProvider:
    """Test-only bridge from the legacy repair transport to a trusted attempt.

    The production trusted provider remains PRIMARY-only.  This adapter drives
    the existing fake transport through its one-shot repair behavior, then
    passes only the canonical final repair envelope into the trusted runtime
    path.  No legacy persistence service receives the result.
    """

    def __init__(self, provider: OllamaScoringProvider) -> None:
        self._provider = provider
        self.calls = 0
        self.final_raw_response: str | None = None

    def primary_attempt(self, scoring_input: ScoringInput) -> PrimaryScoringAttempt:
        self.calls += 1
        self._provider.score(scoring_input)
        raw = self._provider.consume_raw_response(
            request_hash=scoring_input.request_hash
        )
        self.final_raw_response = raw
        return build_primary_scoring_attempt(
            scoring_input=scoring_input,
            candidate=parse_scoring_candidate(raw),
            final_raw_response=raw,
            provider="ollama",
            model=_settings().model,
            model_digest=_settings().expected_model_digest,
            temperature=_settings().temperature,
            max_output_tokens=_settings().max_output_tokens,
            max_description_chars=_settings().max_description_chars,
        )


def _trusted_repair_runtime(
    tmp_path: Path,
    provider: _RepairFlowProvider,
) -> tuple[RuntimeOperations, str, _FakeTransport]:
    project = tmp_path / "project"
    config_root = project / "config"
    config_root.mkdir(parents=True)
    vault_root = project / "vault"
    vault_root.mkdir()
    (config_root / "channels.yaml").write_text(
        "channels:\n  - channel_id: UC_OFFLINE\n", encoding="utf-8"
    )
    (config_root / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
  output_language: en
local_scoring:
  model: {_settings().model}
  expected_model_digest: {_settings().expected_model_digest}
  temperature: {_settings().temperature}
  max_output_tokens: {_settings().max_output_tokens}
  max_transcript_chars: 30000
  max_description_chars: {_settings().max_description_chars}
cloud:
  enabled: false
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {vault_root}
  vault_subdir: Knowledge
""",
        encoding="utf-8",
    )
    config = load_app_config(
        channels_path=config_root / "channels.yaml",
        settings_path=config_root / "settings.yaml",
    )
    quality_transport = _FakeTransport(
        [
            _tags(),
            _judge_response_payload(
                status="PASS",
                signals=["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
                evidence_ids=["title-1"],
            ),
        ]
    )
    runtime = RuntimeOperations(
        config=config,
        project_root=project,
        dependencies=RuntimeDependencies(
            discovery_source=object(),
            metadata_provider=object(),
            subtitle_adapter_factory=lambda: object(),
            scoring_provider_factory=lambda: provider,
            analysis_provider_factory=lambda: object(),
            quality_judge_provider_factory=lambda: _judge_provider(quality_transport),
        ),
    )
    repository = runtime._repository
    now = datetime.now(UTC)
    repository.upsert_video_metadata(_video(), pipeline_version="runtime-v1", now=now)
    assert repository.advance_pipeline(
        "video-123",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="runtime-v1",
        now=now,
    )
    assert repository.advance_pipeline(
        "video-123",
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="runtime-v1",
        now=now,
    )
    repository.create_job(
        job_id="scoring-job-1",
        scope_key="video:video-123:SCORING",
        video_id="video-123",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=3,
        available_at=now,
        now=now,
    )
    claimed = repository.claim_next_job(
        owner="test-worker",
        lease_until=now + timedelta(minutes=5),
        now=now,
    )
    assert claimed is not None
    return runtime, claimed.job_id, quality_transport


def _assert_no_trusted_scoring_success(
    runtime: RuntimeOperations,
    *,
    scoring_input: ScoringInput,
    job_id: str,
) -> None:
    repository = runtime._repository
    assert repository.get_artifact_by_key(
        f"scoring/{scoring_input.request_hash}/raw"
    ) is None
    assert repository.get_artifact_by_key(
        f"scoring/{scoring_input.request_hash}/structured"
    ) is None
    assert repository.get_provider_call(scoring_input.request_hash) is None
    video = repository.get_video("video-123")
    assert video is not None
    assert video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
    job = repository.get_job(job_id)
    assert job is not None
    assert job.status is JobStatus.RUNNING


def _tags(*, digest: str | None = None) -> dict[str, object]:
    return {
        "models": [
            {
                "name": "qwen3:8b",
                "digest": digest or ("sha256:" + ("b" * 64)),
            }
        ]
    }


def _generate(response: str) -> dict[str, str]:
    return {"response": response}


def _provider(transport: _FakeTransport) -> OllamaScoringProvider:
    return OllamaScoringProvider(
        settings=_settings(),
        prompt=PROMPT.read_text(encoding="utf-8"),
        transport=transport,
    )


def test_fake_transport_returns_valid_scoring_result_without_real_ollama() -> None:
    transport = _FakeTransport([_tags(), _generate(_fixture("valid_result.json"))])

    result = _provider(transport).score(_input())

    assert result.score == 8.5
    assert result.provider == "ollama"
    assert result.model == "qwen3:8b"
    assert result.output_language == "en"
    assert [method for method, _, _ in transport.requests] == ["GET", "POST"]
    assert [url for _, url, _ in transport.requests] == [
        "http://127.0.0.1:11434/api/tags",
        "http://127.0.0.1:11434/api/generate",
    ]


@pytest.mark.parametrize(
    ("output_language", "required_instruction"),
    [("zh-CN", "Simplified Chinese"), ("en", "English")],
)
def test_primary_prompt_contains_authoritative_output_language_instruction(
    output_language: str,
    required_instruction: str,
) -> None:
    reason = (
        "视频清楚说明了产品工作流，因此具有实际参考价值。"
        if output_language == "zh-CN"
        else "The video clearly explains the product workflow and has practical value."
    )
    transport = _FakeTransport(
        [
            _tags(),
            _generate(
                json.dumps(
                    {
                        "score": 8,
                        "reason": reason,
                        "topics": ["product"],
                        "should_summarize": True,
                    }
                )
            ),
        ]
    )

    _provider(transport).score(_input(output_language=output_language))

    payload = json.loads(transport.requests[1][2] or b"{}")
    prompt = payload["prompt"]
    assert f'"output_language":"{output_language}"' in prompt
    assert required_instruction in prompt
    assert "untrusted" in prompt


@pytest.mark.parametrize(
    ("output_language", "primary_reason", "repair_reason", "instruction"),
    [
        (
            "zh-CN",
            "The video clearly explains the product workflow and gives useful advice.\n中",
            "视频清楚说明了产品工作流，因此具有实际参考价值。",
            "Simplified Chinese",
        ),
        (
            "zh-CN",
            "Useful clear practical product workflow advice.\n"
            "这个视频介绍产品流程。",
            "视频清楚说明了产品工作流，因此具有实际参考价值。",
            "Simplified Chinese",
        ),
        (
            "zh-CN",
            "中 Useful clear practical product workflow advice 中",
            "视频清楚说明了产品工作流，因此具有实际参考价值。",
            "Simplified Chinese",
        ),
        (
            "zh-CN",
            "中文 Useful clear practical product workflow advice 中文",
            "视频清楚说明了产品工作流，因此具有实际参考价值。",
            "Simplified Chinese",
        ),
        (
            "en",
            "a 这个视频详细解释产品流程 a",
            "The video clearly explains the product workflow and has practical value.",
            "English",
        ),
        (
            "en",
            "a clear 这个视频详细解释产品流程 advice",
            "The video clearly explains the product workflow and has practical value.",
            "English",
        ),
        (
            "zh-CN",
            "good nice happy 中文",
            "视频清楚说明了产品工作流，因此具有实际参考价值。",
            "Simplified Chinese",
        ),
        (
            "en",
            "clear 中文 advice",
            "The video clearly explains the product workflow and has practical value.",
            "English",
        ),
        (
            "zh-CN",
            "この動画はAPIの製品ワークフローを詳しく説明します。",
            "视频清楚说明了产品工作流，因此具有实际参考价值。",
            "Simplified Chinese",
        ),
        (
            "zh-CN",
            "中 REST CUDA NLP CNN",
            "视频清楚说明了产品工作流，因此具有实际参考价值。",
            "Simplified Chinese",
        ),
        (
            "en",
            "a API SDK LLM GPT MLX",
            "The video clearly explains the product workflow and has practical value.",
            "English",
        ),
        (
            "en",
            "Docker Kubernetes Terraform Ansible",
            "Docker containers help developers deploy applications.",
            "English",
        ),
        (
            "en",
            "这个视频详细解释了产品工作流程并给出了建议。\n"
            "Useful clear practical product workflow advice.",
            "The video clearly explains the product workflow and has practical value.",
            "English",
        ),
    ],
)
def test_wrong_language_reason_uses_one_language_bound_repair(
    output_language: str,
    primary_reason: str,
    repair_reason: str,
    instruction: str,
) -> None:
    result_template = {
        "score": 8,
        "topics": ["product"],
        "should_summarize": True,
    }
    transport = _FakeTransport(
        [
            _tags(),
            _generate(json.dumps({**result_template, "reason": primary_reason})),
            _generate(json.dumps({**result_template, "reason": repair_reason})),
        ]
    )

    result = _provider(transport).score(_input(output_language=output_language))

    repair_payload = json.loads(transport.requests[2][2] or b"{}")
    assert result.reason == repair_reason
    assert result.output_language == output_language
    assert instruction in repair_payload["prompt"]
    assert len(transport.requests) == 3


@pytest.mark.parametrize(
    ("output_language", "reason"),
    [
        ("zh-CN", "Useful, clear, practical, product, workflow, advice."),
        ("zh-CN", "Useful, clear, practical, product, workflow, advice. 中"),
        (
            "zh-CN",
            "The video clearly explains the product workflow and gives useful advice.\n中",
        ),
        (
            "zh-CN",
            "Useful clear practical product workflow advice.\n"
            "这个视频介绍产品流程。",
        ),
        ("zh-CN", "中 Useful clear practical product workflow advice 中"),
        ("zh-CN", "中文 Useful clear practical product workflow advice 中文"),
        ("en", "这个视频详细解释了 api、sdk、llm 的产品工作流程。"),
        (
            "en",
            "这个视频详细解释了产品工作流程并给出了建议。\n"
            "Useful clear practical product workflow advice.",
        ),
        ("en", "a 这个视频详细解释产品流程 a"),
        ("en", "a clear 这个视频详细解释产品流程 advice"),
        ("zh-CN", "good nice happy 中文"),
        ("en", "clear 中文 advice"),
        ("zh-CN", "この動画はAPIの製品ワークフローを詳しく説明します。"),
        ("zh-CN", "中 REST CUDA NLP CNN"),
        ("en", "a API SDK LLM GPT MLX"),
        ("en", "Amazon Connect Salesforce"),
        ("en", "Amazon Connect General Electric"),
        ("en", "Amazon Connect Jack in the Box"),
        ("en", "Amazon Connect The Home Depot"),
        ("en", "Docker Kubernetes Terraform Ansible"),
        ("en", "docker kubernetes terraform ansible"),
        ("en", "Docker Terraform Kubernetes Ansible"),
        ("en", "Redis Kafka PostgreSQL MongoDB"),
        ("en", "redis kafka postgresql mongodb"),
        ("en", "Docker helps"),
        ("en", "Redis stores"),
        ("en", "OpenAI develops"),
    ],
)
def test_wrong_language_after_single_repair_fails_closed(
    output_language: str,
    reason: str,
) -> None:
    wrong_language = json.dumps(
        {
            "score": 8,
            "reason": reason,
            "topics": ["product"],
            "should_summarize": True,
        }
    )
    transport = _FakeTransport(
        [_tags(), _generate(wrong_language), _generate(wrong_language)]
    )

    with pytest.raises(OllamaProviderError) as exc_info:
        _provider(transport).score(_input(output_language=output_language))

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert len(transport.requests) == 3


@pytest.mark.parametrize(
    ("output_language", "wrong_reason"),
    [
        ("zh-CN", "中 REST CUDA NLP CNN"),
        ("en", "a API SDK LLM GPT MLX"),
        ("en", "Amazon Connect Salesforce"),
        ("en", "Amazon Connect General Electric"),
        ("en", "Amazon Connect Jack in the Box"),
        ("en", "Amazon Connect The Home Depot"),
        ("en", "Docker Kubernetes Terraform Ansible"),
        ("en", "docker kubernetes terraform ansible"),
        ("en", "Redis Kafka PostgreSQL MongoDB"),
        ("en", "redis kafka postgresql mongodb"),
    ],
)
def test_failed_language_repair_never_persists_a_formal_scoring_artifact(
    tmp_path: Path,
    output_language: str,
    wrong_reason: str,
) -> None:
    wrong_response = json.dumps(
        {
            "score": 8,
            "reason": wrong_reason,
            "topics": ["product"],
            "should_summarize": True,
        }
    )
    transport = _FakeTransport(
        [_tags(), _generate(wrong_response), _generate(wrong_response)]
    )
    repair_provider = _RepairFlowProvider(_provider(transport))
    runtime, job_id, quality_transport = _trusted_repair_runtime(
        tmp_path, repair_provider
    )
    scoring_input = _input(output_language=output_language)

    with pytest.raises(OllamaProviderError) as exc_info:
        repair_provider.primary_attempt(scoring_input)

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert [method for method, _, _ in transport.requests] == ["GET", "POST", "POST"]
    assert quality_transport.requests == []
    _assert_no_trusted_scoring_success(
        runtime, scoring_input=scoring_input, job_id=job_id
    )


def test_successful_language_repair_persists_only_the_valid_repair_response(
    tmp_path: Path,
) -> None:
    primary_reason = "Amazon Connect General Electric"
    repaired_reason = "Docker containers help developers deploy applications."
    result_template = {
        "score": 8,
        "topics": ["product"],
        "should_summarize": True,
    }
    transport = _FakeTransport(
        [
            _tags(),
            _generate(json.dumps({**result_template, "reason": primary_reason})),
            _generate(json.dumps({**result_template, "reason": repaired_reason})),
        ]
    )
    repair_provider = _RepairFlowProvider(_provider(transport))
    runtime, job_id, quality_transport = _trusted_repair_runtime(
        tmp_path, repair_provider
    )
    scoring_input = _input(transcript_text="canonical transcript")
    success = runtime.run_primary_trusted_scoring(
        attempt=repair_provider.primary_attempt(scoring_input),
        scoring_input=scoring_input,
        admission=ScoringDispatchAdmission(
            repository=runtime._repository,
            job_id=job_id,
            owner="test-worker",
        ),
    )
    runtime._trusted_persistence_entry(
        job_id=job_id,
        owner="test-worker",
        pipeline_version="runtime-v1",
    ).persist_success(success)

    repository = runtime._repository
    raw = repository.get_artifact_by_key(
        f"scoring/{scoring_input.request_hash}/raw"
    )
    assert raw is not None
    assert raw.kind is ArtifactKind.SCORING_RAW
    persisted_response = json.loads(
        (runtime._data_root / raw.relative_path).read_text(encoding="utf-8")
    )
    persisted_result = json.loads(persisted_response["provider_raw_response"])["response"]
    persisted_result = json.loads(persisted_result)
    assert persisted_result["reason"] == repaired_reason
    assert persisted_result["reason"] != primary_reason
    assert repair_provider.final_raw_response == persisted_response["provider_raw_response"]
    assert primary_reason not in json.dumps(persisted_response)
    assert [method for method, _, _ in transport.requests] == ["GET", "POST", "POST"]
    assert [method for method, _, _ in quality_transport.requests] == ["GET", "POST"]
    scoring_call = repository.get_provider_call(scoring_input.request_hash)
    assert scoring_call is not None
    assert scoring_call.status is ProviderCallStatus.SUCCEEDED
    assert scoring_call.response_artifact_id == raw.artifact_id
    structured = repository.get_artifact_by_key(
        f"scoring/{scoring_input.request_hash}/structured"
    )
    assert structured is not None
    video = repository.get_video("video-123")
    assert video is not None
    assert video.pipeline_status is PipelineStatus.SCORED
    job = repository.get_job(job_id)
    assert job is not None
    assert job.status is JobStatus.SUCCEEDED


def test_primary_provider_failure_does_not_repair_or_persist_in_trusted_flow(
    tmp_path: Path,
) -> None:
    transport = _FakeTransport([_tags(), _IncompleteResponse(b"partial")])
    repair_provider = _RepairFlowProvider(_provider(transport))
    runtime, job_id, quality_transport = _trusted_repair_runtime(
        tmp_path, repair_provider
    )
    scoring_input = _input()

    with pytest.raises(OllamaProviderError) as exc_info:
        repair_provider.primary_attempt(scoring_input)

    assert exc_info.value.error.code is ErrorCode.TRANSIENT_NETWORK
    assert [method for method, _, _ in transport.requests] == ["GET", "POST"]
    assert quality_transport.requests == []
    _assert_no_trusted_scoring_success(
        runtime, scoring_input=scoring_input, job_id=job_id
    )


def test_official_bare_sha256_digest_shape_matches_frozen_config() -> None:
    transport = _FakeTransport(
        [_tags(digest="b" * 64), _generate(_fixture("valid_result.json"))]
    )

    result = _provider(transport).score(_input())

    assert result.score == 8.5
    payload = json.loads(transport.requests[1][2] or b"{}")
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"]["temperature"] == 0.0
    serialized_format = json.dumps(payload["format"])
    assert all(
        keyword not in serialized_format
        for keyword in (
            '"minimum"',
            '"maximum"',
            '"minLength"',
            '"maxLength"',
            '"minItems"',
            '"maxItems"',
        )
    )
    assert payload["format"]["properties"]["score"] == {
        "type": "integer",
        "enum": list(range(11)),
    }


def test_provider_exposes_the_final_generate_envelope_for_artifact_persistence() -> None:
    generate = _generate(_fixture("valid_result.json"))
    provider = _provider(_FakeTransport([_tags(), generate]))

    provider.score(_input())

    assert json.loads(
        provider.consume_raw_response(request_hash=_input().request_hash)
    ) == generate


@pytest.mark.parametrize(
    "invalid_fixture",
    ["out_of_range_result.json", "missing_field_result.json", "invalid_json.txt"],
)
def test_invalid_primary_response_uses_exactly_one_repair_request(
    invalid_fixture: str,
) -> None:
    transport = _FakeTransport(
        [
            _tags(),
            _generate(_fixture(invalid_fixture)),
            _generate(_fixture("repair_result.json")),
        ]
    )

    result = _provider(transport).score(_input())

    assert result.score == 7.5
    assert [method for method, _, _ in transport.requests] == ["GET", "POST", "POST"]


def test_invalid_repair_response_fails_closed_as_invalid_response() -> None:
    transport = _FakeTransport(
        [
            _tags(),
            _generate(_fixture("invalid_json.txt")),
            _generate(_fixture("missing_field_result.json")),
        ]
    )

    with pytest.raises(OllamaProviderError) as exc_info:
        _provider(transport).score(_input())

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert exc_info.value.error.retryable is True
    assert len(transport.requests) == 3


def test_saved_primary_response_is_repaired_without_a_second_preflight_or_primary_call() -> None:
    primary = _generate(_fixture("invalid_json.txt"))
    repaired = _generate(_fixture("repair_result.json"))
    transport = _FakeTransport(
        [
            _tags(),
            primary,
            _generate(_fixture("missing_field_result.json")),
            repaired,
        ]
    )
    provider = _provider(transport)
    scoring_input = _input()

    with pytest.raises(OllamaProviderError) as exc_info:
        provider.score(scoring_input)

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    saved_primary = provider.consume_raw_response(
        request_hash=scoring_input.request_hash
    )
    result = provider._repair_saved_primary_response(
        primary_raw_response=saved_primary,
        scoring_input=scoring_input,
    )

    assert result.score == 7.5
    assert json.loads(saved_primary) == primary
    assert [method for method, _, _ in transport.requests] == [
        "GET",
        "POST",
        "POST",
        "POST",
    ]
    assert [url for _, url, _ in transport.requests[-1:]] == [
        "http://127.0.0.1:11434/api/generate"
    ]


def test_saved_primary_repair_failure_redacts_the_primary_response_from_tracebacks() -> None:
    sentinel = "/private/saved-primary-response"
    transport = _FakeTransport([_generate(_fixture("missing_field_result.json"))])
    provider = _provider(transport)

    with pytest.raises(OllamaProviderError) as exc_info:
        provider._repair_saved_primary_response(
            primary_raw_response=json.dumps(_generate("not json " + sentinel)),
            scoring_input=_input(),
        )

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert [method for method, _, _ in transport.requests] == ["POST"]
    _assert_exception_graph_is_redacted(exc_info.value, sentinel)


def test_invalid_repair_response_is_redacted_through_the_complete_exception_graph() -> None:
    sentinel = "/private/secret-transcript-response"
    transport = _FakeTransport(
        [
            _tags(),
            _generate("not json"),
            _generate('{"reason":"' + sentinel + '"}'),
        ]
    )

    with pytest.raises(OllamaProviderError) as exc_info:
        _provider(transport).score(_input())

    _assert_exception_graph_is_redacted(exc_info.value, sentinel)


@pytest.mark.parametrize(
    ("response", "error_code"),
    [
        ({}, ErrorCode.INVALID_RESPONSE),
        ({"response": "x" * 20_001}, ErrorCode.INVALID_RESPONSE),
        (_IncompleteResponse(b"partial /private/secret-response"), ErrorCode.TRANSIENT_NETWORK),
    ],
)
def test_invalid_or_short_generate_response_fails_as_a_named_redacted_error(
    response: object,
    error_code: ErrorCode,
) -> None:
    transport = _FakeTransport([_tags(), response])

    with pytest.raises(OllamaProviderError) as exc_info:
        _provider(transport).score(_input())

    assert exc_info.value.error.code is error_code
    assert exc_info.value.error.video_id == "video-123"
    _assert_exception_graph_is_redacted(exc_info.value, "/private/secret-response")


def test_transport_failure_redacts_the_rendered_prompt_and_transcript_from_tracebacks() -> None:
    sentinel = "/private/temporary-transcript-url"
    transport = _FakeTransport([_tags(), _IncompleteResponse(b"partial")])

    with pytest.raises(OllamaProviderError) as exc_info:
        _provider(transport).score(_input(transcript_text=sentinel))

    _assert_exception_graph_is_redacted(exc_info.value, sentinel)


def test_mismatched_digest_fails_before_any_generate_request() -> None:
    transport = _FakeTransport([_tags(digest="sha256:" + ("c" * 64))])

    with pytest.raises(OllamaProviderError) as exc_info:
        _provider(transport).score(_input())

    assert exc_info.value.error.code is ErrorCode.CONFIG_INVALID
    assert exc_info.value.error.retryable is False
    assert [method for method, _, _ in transport.requests] == ["GET"]


# ---------------------------------------------------------------------------
# TASK-016C Phase C — focused fake-transport Quality Judge contract coverage
# ---------------------------------------------------------------------------


def _judge_settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:" + ("b" * 64),
    )


def _judge_operation_input(
    *,
    attempt_role: QualityJudgeAttemptRole = QualityJudgeAttemptRole.PRIMARY,
    quality_input_hash: str = "a" * 64,
) -> QualityJudgeOperationInput:
    return QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": "a" * 64,
            "attempt_role": attempt_role,
            "candidate_hash": "a" * 64,
            "quality_input_hash": quality_input_hash,
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v1",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": "qwen3:8b",
            "judge_model_digest": "sha256:" + ("b" * 64),
        }
    )


def _judge_response_payload(
    *,
    status: str = "PASS",
    signals: list[str] | None = None,
    reason: str | None = None,
    evidence_ids: list[str] | None = None,
) -> dict[str, object]:
    return {
        "response": json.dumps(
            {
                "status": status,
                "decision_confidence": "HIGH",
                "grounding_confidence": "MEDIUM",
                "usefulness_confidence": "MEDIUM",
                "signals": signals if signals is not None else [],
                "reason": reason,
                "evidence_ids": evidence_ids if evidence_ids is not None else [],
            }
        ),
    }


def _judge_provider(transport: _FakeTransport) -> OllamaQualityJudgeProvider:
    return OllamaQualityJudgeProvider(
        settings=_judge_settings(),
        transport=transport,
    )


def _judge_evidence_registry() -> tuple[ScoringEvidence, ...]:
    return (
        ScoringEvidence(
            evidence_id="title-1",
            source=ScoringEvidenceSource.TITLE,
            excerpt="A useful title excerpt",
        ),
    )


def _judge_content_input(
    output_language: str = "en",
    reason: str = "The video explains the product workflow clearly.",
    topics: tuple[str, ...] = ("product", "workflow"),
) -> ContentQualityInput:
    return ContentQualityInput.model_validate(
        {
            "scoring_request_hash": "a" * 64,
            "candidate_hash": "a" * 64,
            "output_language": output_language,
            "reason": reason,
            "topics": topics,
            "evidence_registry": _judge_evidence_registry(),
            "policy_version": "content-quality-policy-v1",
        }
    )


def test_quality_judge_fake_transport_returns_pass_without_real_ollama() -> None:
    transport = _FakeTransport(
        [
            _tags(),
            _judge_response_payload(
                status="PASS",
                signals=[
                    "MINIMAL_CLAIM_PRESENT",
                    "GROUNDING_PRESENT",
                ],
                evidence_ids=["title-1"],
            ),
        ]
    )
    content_input = _judge_content_input()
    operation_input = _judge_operation_input(
        quality_input_hash=build_content_quality_input_hash(content_input),
    )

    result = _judge_provider(transport).judge(
        operation_input,
        content_input=content_input,
    )

    assert result.status is ContentQualityStatus.PASS
    assert result.decision_source.value == "LOCAL_JUDGE"
    assert ContentQualitySignal.MINIMAL_CLAIM_PRESENT in result.signals
    assert ContentQualitySignal.GROUNDING_PRESENT in result.signals
    assert result.evidence_ids == ("title-1",)


def test_quality_judge_computes_h1_h2_identity_from_operation_input() -> None:
    operation_input = _judge_operation_input(
        attempt_role=QualityJudgeAttemptRole.PRIMARY,
    )
    h1, h2 = build_judge_h1_h2(operation_input)

    assert h1 != h2
    assert len(h1) == 64
    assert len(h2) == 64


def test_quality_judge_invalid_response_fails_closed_as_uncertain() -> None:
    transport = _FakeTransport([_tags(), {"response": "not json"}])
    content_input = _judge_content_input()
    operation_input = _judge_operation_input(
        quality_input_hash=build_content_quality_input_hash(content_input),
    )

    result = _judge_provider(transport).judge(
        operation_input,
        content_input=content_input,
    )

    assert result.status is ContentQualityStatus.UNCERTAIN
    assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE
