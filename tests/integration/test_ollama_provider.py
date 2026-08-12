"""Offline integration tests for the injected Ollama HTTP transport."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from http.client import IncompleteRead
from pathlib import Path
from types import TracebackType
from typing import Any

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    Availability,
    ErrorCode,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
)
from youtube_intel.providers.ollama import OllamaProviderError, OllamaScoringProvider
from youtube_intel.scoring import (
    RepositoryBackedScoringService,
    ScoringJobContext,
    ScoringPersistenceError,
    build_scoring_input,
)
from youtube_intel.state import (
    ArtifactKind,
    JobType,
    ProviderCallStatus,
    SQLiteStateRepository,
)

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


def _repository_scoring_service(
    tmp_path: Path,
    provider: OllamaScoringProvider,
) -> tuple[SQLiteStateRepository, RepositoryBackedScoringService]:
    now = datetime(2026, 8, 13, tzinfo=UTC)
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=now)
    repository.upsert_video_metadata(_video(), pipeline_version="pipeline-v1", now=now)
    assert repository.advance_pipeline(
        "video-123",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="pipeline-v1",
        now=now,
    )
    assert repository.advance_pipeline(
        "video-123",
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="pipeline-v1",
        now=now,
    )
    repository.create_job(
        job_id="scoring-job-1",
        scope_key="video:video-123:SCORING",
        video_id="video-123",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="pipeline-v1",
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
    service = RepositoryBackedScoringService(
        provider=provider,
        settings=_settings(),
        summary_threshold=7.0,
        repository=repository,
        context=ScoringJobContext(
            job_id=claimed.job_id,
            owner="test-worker",
            pipeline_version="pipeline-v1",
        ),
        artifact_root=tmp_path / "artifacts",
        clock=lambda: now,
    )
    return repository, service


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


def test_failed_language_repair_never_persists_a_formal_scoring_artifact(
    tmp_path: Path,
) -> None:
    wrong_reason = "中 Useful clear practical product workflow advice 中"
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
    repository, service = _repository_scoring_service(
        tmp_path,
        _provider(transport),
    )

    with pytest.raises(ScoringPersistenceError) as exc_info:
        service.score(
            video=_video(),
            transcript_text="canonical transcript",
            language="en",
            output_language="zh-CN",
        )

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    connection = repository._connect()
    try:
        artifact_kinds = tuple(
            row[0] for row in connection.execute("SELECT kind FROM artifacts")
        )
        provider_call = connection.execute(
            "SELECT status, response_artifact_id FROM provider_calls"
        ).fetchone()
    finally:
        connection.close()
    assert ArtifactKind.SCORING_RAW.value not in artifact_kinds
    assert ArtifactKind.SCORING_STRUCTURED.value not in artifact_kinds
    assert provider_call is not None
    assert provider_call[0] == ProviderCallStatus.FAILED_RETRYABLE.value
    assert provider_call[1] is None
    assert not any(
        path.is_file() for path in (tmp_path / "artifacts").rglob("*")
    )


def test_successful_language_repair_persists_only_the_valid_repair_response(
    tmp_path: Path,
) -> None:
    primary_reason = "中 Useful clear practical product workflow advice 中"
    repaired_reason = "视频清楚说明了产品工作流，因此具有实际参考价值。"
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
    repository, service = _repository_scoring_service(
        tmp_path,
        _provider(transport),
    )

    outcome = service.score(
        video=_video(),
        transcript_text="canonical transcript",
        language="en",
        output_language="zh-CN",
    )

    raw = repository.get_artifact_by_key(
        f"scoring/{outcome.result.request_hash}/raw"
    )
    assert raw is not None
    assert raw.kind is ArtifactKind.SCORING_RAW
    raw_content = (tmp_path / "artifacts" / raw.relative_path).read_text(
        encoding="utf-8"
    )
    persisted_response = json.loads(raw_content)
    persisted_result = json.loads(persisted_response["response"])
    assert persisted_result["reason"] == repaired_reason
    assert persisted_result["reason"] != primary_reason


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
