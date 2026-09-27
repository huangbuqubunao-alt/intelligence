"""Offline contract tests for the bounded Moonshot Kimi K2.6 route."""

from __future__ import annotations

import io
import json
from collections.abc import Mapping
from dataclasses import replace

import pytest

from youtube_intel.distillation import (
    CloudDistillationAuthorization,
    CloudDistillationPreDispatchError,
    KnownCloudDistillationResponseError,
    MoonshotK26CloudDistillationTransport,
    MoonshotK26NonThinkingCloudDistillationTransport,
    PersonalizedDistillationService,
    VerifiedDistillationInput,
    VerifiedEvidenceInput,
    _moonshot_chat_completions_http_transport,
    _MoonshotWireResponse,
    _parse_moonshot_sse_stream,
)

_SECRET = "test-moonshot-key-never-persist"
_PRIVATE_REASONING = "private reasoning text must never become Intelligence"


def _input(
    *, provider: str = "moonshot", model: str = "kimi-k2.6"
) -> VerifiedDistillationInput:
    return VerifiedDistillationInput(
        source_display_name="CNN",
        video_id="cnn-video",
        video_title="CNN interview",
        evidence=tuple(
            VerifiedEvidenceInput(
                evidence_id=f"evidence-{index}",
                start_ms=index * 1000,
                end_ms=index * 1000 + 500,
                excerpt=f"Verified excerpt {index}",
                excerpt_hash="a" * 64,
                timed_transcript_id=f"timed-{index}",
                timed_transcript_hash="b" * 64,
            )
            for index in range(15)
        ),
        personalization=(),
        source_focus_rules=(),
        source_ignore_rules=(),
        distillation_style=None,
        selected_provider=provider,
        selected_model=model,
        semantic_hash="c" * 64,
        output_language="zh-CN",
    )


def _response(
    *,
    content: str | None = '{"result":"NO_NEW_INTELLIGENCE"}',
    model: str | None = "kimi-k2.6",
    finish_reason: str | None = "stop",
    http_status: int = 200,
    stream_complete: bool = True,
    malformed: bool = False,
) -> _MoonshotWireResponse:
    return _MoonshotWireResponse(
        http_status=http_status,
        response_object_type="chat.completion.chunk",
        model_identity=model,
        choices_count=1,
        message_exists=True,
        content_type="str" if content is not None else "null",
        content_present=content is not None,
        content_length=0 if content is None else len(content),
        final_content=content,
        reasoning_present=True,
        reasoning_length=len(_PRIVATE_REASONING),
        finish_reason=finish_reason,
        prompt_tokens=5644,
        completion_tokens=321,
        reasoning_tokens=300,
        stream_complete=stream_complete,
        malformed_envelope=malformed,
    )


def _transport(
    response: _MoonshotWireResponse | Exception,
    calls: list[object],
    *,
    model: str = "kimi-k2.6",
) -> MoonshotK26CloudDistillationTransport:
    def wire(
        request: Mapping[str, object],
        credential: str,
        timeout: float,
        retries: int,
    ) -> _MoonshotWireResponse:
        calls.append((request, credential, timeout, retries))
        if isinstance(response, Exception):
            raise response
        return response

    return MoonshotK26CloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="moonshot",
            model=model,
            credential_available=True,
            provider_available=True,
            qualification_input_hash=_input(model=model).semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: _SECRET,
        wire_transport=wire,
    )


def _sse(events: list[object]) -> bytes:
    return b"".join(
        b"data: " + json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n\n"
        for event in events
    ) + b"data: [DONE]\n\n"


def _parse_stream(events: list[object]) -> _MoonshotWireResponse:
    return _parse_moonshot_sse_stream(_http_response(_sse(events)))


def _event(
    *,
    delta: Mapping[str, object] | None = None,
    finish_reason: str | None = None,
    model: str | None = "kimi-k2.6",
    usage: Mapping[str, object] | None = None,
    choices: object | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "object": "chat.completion.chunk",
        "choices": (
            [{"index": 0, "delta": dict(delta or {}), "finish_reason": finish_reason}]
            if choices is None
            else choices
        ),
    }
    if model is not None:
        value["model"] = model
    if usage is not None:
        value["usage"] = dict(usage)
    return value


def _http_response(stream: bytes, status: int = 200) -> object:
    class Response(io.BytesIO):
        def __init__(self) -> None:
            super().__init__(stream)
            self.status = status

    return Response()


def test_k2_6_request_profile_is_versioned_bounded_and_uses_all_15_evidence() -> None:
    calls: list[object] = []
    transport = _transport(_response(content="final JSON"), calls)

    result = transport.generate(_input())

    assert result.raw == "final JSON"
    assert result.actual_provider == "moonshot"
    assert result.actual_model == "kimi-k2.6"
    assert (result.input_tokens, result.output_tokens) == (5644, 321)
    assert result.cost_microunits is None
    assert result.duration_ms is not None
    assert len(calls) == 1
    request, credential, timeout, retries = calls[0]
    assert credential == _SECRET
    assert timeout == 300.0
    assert retries == 0
    assert request["model"] == "kimi-k2.6"
    messages = request["messages"]
    assert [message["role"] for message in messages] == ["system", "system", "user"]
    assert all(message["role"] in {"system", "user", "assistant", "tool"} for message in messages)
    assert "input" not in request
    assert "store" not in request
    assert "truncation" not in request
    assert "max_output_tokens" not in request
    assert request["stream"] is True
    assert request["stream_options"] == {"include_usage": True}
    assert request["max_tokens"] == 16_384
    assert request["thinking"] == {"type": "enabled"}
    assert "temperature" not in request
    assert "reasoning_effort" not in request
    assert "relevant subset" in messages[0]["content"]
    assert "every supplied evidence_id" in messages[0]["content"]
    source_payload = json.loads(messages[2]["content"].split("=", 1)[1])
    assert len(source_payload["evidence"]) == 15
    assert all(item["evidence_id"] == f"evidence-{i}" for i, item in enumerate(source_payload["evidence"]))
    assert _SECRET not in str(request)


def test_request_profile_version_is_bound_into_execution_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = dict(
        source_id="source-cnn",
        video_id="cnn-video",
        evidence_ids=tuple(f"evidence-{index}" for index in range(15)),
        selected_provider="moonshot",
        selected_model="kimi-k2.6",
        output_language="zh-CN",
        verified_input_hash="c" * 64,
    )
    first = PersonalizedDistillationService._reservation_id(**identity)
    monkeypatch.setattr(
        MoonshotK26CloudDistillationTransport,
        "_REQUEST_PROFILE_VERSION",
        "moonshot-kimi-k2.6-qualification-v4",
    )
    assert PersonalizedDistillationService._reservation_id(**identity) != first


def test_non_thinking_profile_has_distinct_identity_and_bounded_json_request() -> None:
    request = MoonshotK26NonThinkingCloudDistillationTransport._request(_input())
    prior = MoonshotK26CloudDistillationTransport._request(_input())
    assert set(request) == set(prior) - {"stream_options"}
    assert request["endpoint_identity"] == "https://api.moonshot.cn/v1/chat/completions"
    assert request["model"] == "kimi-k2.6"
    assert request["stream"] is False
    assert "stream_options" not in request
    assert request["thinking"] == {"type": "disabled"}
    assert request["max_tokens"] == 8_192
    assert [message["role"] for message in request["messages"]] == ["system", "system", "user"]
    assert not {"temperature", "top_p", "reasoning_effort"} & request.keys()
    identity = dict(
        source_id="source-cnn",
        video_id="cnn-video",
        evidence_ids=tuple(f"evidence-{index}" for index in range(15)),
        selected_provider="moonshot",
        selected_model="kimi-k2.6",
        output_language="zh-CN",
        verified_input_hash="c" * 64,
    )
    old_id = PersonalizedDistillationService._reservation_id(**identity)
    new_id = PersonalizedDistillationService._reservation_id(
        **identity,
        cloud_request_profile_version=(
            MoonshotK26NonThinkingCloudDistillationTransport._REQUEST_PROFILE_VERSION
        ),
    )
    assert old_id != new_id


def test_non_thinking_http_200_uses_json_only_and_discards_reasoning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = json.dumps({
        "result": "NO_NEW_INTELLIGENCE",
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "start_ms": item.start_ms,
                "end_ms": item.end_ms,
            }
            for item in _input().evidence
        ],
    })
    body = json.dumps({
        "object": "chat.completion",
        "model": "kimi-k2.6",
        "choices": [{
            "message": {"content": content, "reasoning_content": _PRIVATE_REASONING},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 5644, "completion_tokens": 321, "total_tokens": 5965},
    }).encode()
    calls: list[dict[str, object]] = []

    class Connection:
        def __init__(self, host: str, *, timeout: float) -> None:
            assert (host, timeout) == ("api.moonshot.cn", 300.0)

        def request(self, method: str, path: str, *, body: bytes, headers: Mapping[str, str]) -> None:
            assert (method, path) == ("POST", "/v1/chat/completions")
            assert headers["Accept"] == "application/json"
            assert headers["Authorization"] == f"Bearer {_SECRET}"
            calls.append(json.loads(body))

        def getresponse(self) -> object:
            return _http_response(body)

        def close(self) -> None:
            pass

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", Connection)
    monkeypatch.setattr(
        "youtube_intel.distillation._parse_moonshot_sse_stream",
        lambda *_args: pytest.fail("non-streaming profile entered SSE parser"),
    )
    transport = MoonshotK26NonThinkingCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="moonshot",
            model="kimi-k2.6",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=_input().semantic_hash,
        ),
        credential_resolver=lambda: _SECRET,
    )
    result = transport.generate(_input())
    assert len(calls) == 1
    assert calls[0]["stream"] is False
    assert calls[0]["thinking"] == {"type": "disabled"}
    assert "stream_options" not in calls[0]
    assert result.raw == content
    assert len(json.loads(result.raw)["evidence"]) == 15
    assert result.http_status_code == 200
    assert (result.input_tokens, result.output_tokens) == (5644, 321)
    assert _PRIVATE_REASONING not in repr(result)
    assert _SECRET not in repr(result)


@pytest.mark.parametrize(
    ("case", "status", "expected_reason"),
    [
        ("missing_content", 200, "CLOUD_FINAL_CONTENT_MISSING"),
        ("missing_model", 200, "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN"),
        ("wrong_model", 200, "HTTP_RESPONSE_MODEL_IDENTITY_INVALID"),
        ("malformed_json", 200, "CLOUD_HTTP_RESPONSE_MALFORMED"),
        ("http_error", 400, "CLOUD_HTTP_RESPONSE_INVALID"),
        ("http_error", 401, "CLOUD_HTTP_RESPONSE_INVALID"),
        ("http_error", 429, "CLOUD_HTTP_RESPONSE_INVALID"),
        ("http_error", 500, "CLOUD_HTTP_RESPONSE_INVALID"),
    ],
)
def test_non_thinking_confirmed_http_failures_are_not_transport_ambiguity(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    status: int,
    expected_reason: str,
) -> None:
    payload = {
        "object": "chat.completion",
        **({} if case == "missing_model" else {
            "model": "kimi-k3" if case == "wrong_model" else "kimi-k2.6"
        }),
        "choices": [{
            "message": {"content": None if case == "missing_content" else "final"},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
    }
    response_bytes = b"{malformed" if case == "malformed_json" else json.dumps(payload).encode()
    requests = 0

    class Connection:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def request(self, *_args: object, **_kwargs: object) -> None:
            nonlocal requests
            requests += 1

        def getresponse(self) -> object:
            return _http_response(response_bytes, status)

        def close(self) -> None:
            pass

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", Connection)
    monkeypatch.setattr(
        "youtube_intel.distillation._parse_moonshot_sse_stream",
        lambda *_args: pytest.fail("non-streaming profile entered SSE parser"),
    )
    transport = MoonshotK26NonThinkingCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="moonshot",
            model="kimi-k2.6",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=_input().semantic_hash,
        ),
        credential_resolver=lambda: _SECRET,
    )
    with pytest.raises(KnownCloudDistillationResponseError) as error:
        transport.generate(_input())
    assert error.value.http_status == status
    assert error.value.reason == expected_reason
    assert requests == 1
    assert _SECRET not in repr(error.value)


def test_non_thinking_timeout_before_http_response_is_unknown_and_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = 0

    class Connection:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def request(self, *_args: object, **_kwargs: object) -> None:
            nonlocal requests
            requests += 1

        def getresponse(self) -> object:
            raise TimeoutError("private transport detail")

        def close(self) -> None:
            pass

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", Connection)
    transport = MoonshotK26NonThinkingCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="moonshot",
            model="kimi-k2.6",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=_input().semantic_hash,
        ),
        credential_resolver=lambda: _SECRET,
    )
    with pytest.raises(RuntimeError, match="outcome is not confirmed") as error:
        transport.generate(_input())
    assert requests == 1
    assert "private transport detail" not in str(error.value)


def test_non_thinking_profile_rejects_chunk_envelope_as_confirmed_malformed_response() -> None:
    transport = MoonshotK26NonThinkingCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="moonshot",
            model="kimi-k2.6",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=_input().semantic_hash,
        ),
        credential_resolver=lambda: _SECRET,
        wire_transport=lambda *_args: _response(content="final"),
    )
    with pytest.raises(KnownCloudDistillationResponseError) as error:
        transport.generate(_input())
    assert error.value.reason == "CLOUD_HTTP_RESPONSE_MALFORMED"
    assert error.value.http_status == 200


def test_reasoning_stream_metadata_never_becomes_final_intelligence() -> None:
    events = [
        _event(delta={"reasoning_content": _PRIVATE_REASONING}),
        _event(delta={"content": "FINAL CONTENT ONLY"}),
        _event(finish_reason="stop"),
        _event(
            choices=[],
            usage={
                "prompt_tokens": 5644,
                "completion_tokens": 321,
                "total_tokens": 5965,
                "cached_tokens": 900,
                "completion_tokens_details": {"reasoning_tokens": 300},
            },
        ),
    ]

    response = _parse_stream(events)

    assert response.final_content == "FINAL CONTENT ONLY"
    assert response.reasoning_present is True
    assert response.reasoning_length == len(_PRIVATE_REASONING)
    assert response.reasoning_tokens == 300
    assert (response.prompt_tokens, response.completion_tokens) == (5644, 321)
    assert response.total_tokens == 5965
    assert response.cached_tokens == 900
    assert _PRIVATE_REASONING not in repr(response)


def test_documented_non_streaming_chat_completion_parses_final_only() -> None:
    body = json.dumps(
        {
            "id": "cmpl-safe-test",
            "object": "chat.completion",
            "model": "kimi-k2.6",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "最终答案",
                        "reasoning_content": _PRIVATE_REASONING,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 5644,
                "completion_tokens": 321,
                "total_tokens": 5965,
                "cached_tokens": 900,
                "completion_tokens_details": {"reasoning_tokens": 300},
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")

    response = _parse_moonshot_sse_stream(_http_response(body))
    result = _transport(response, []).generate(_input())

    assert response.response_object_type == "chat.completion"
    assert response.model_identity == "kimi-k2.6"
    assert response.finish_reason == "stop"
    assert (response.prompt_tokens, response.completion_tokens, response.total_tokens) == (
        5644,
        321,
        5965,
    )
    assert response.cached_tokens == 900
    assert response.reasoning_present is True
    assert response.reasoning_tokens == 300
    assert result.raw == "最终答案"
    assert _PRIVATE_REASONING not in repr(response)
    assert _PRIVATE_REASONING not in repr(result)


def test_stream_identity_must_be_present_exact_and_consistent() -> None:
    missing = _parse_stream(
        [
            _event(model=None, delta={"content": "answer"}),
            _event(model=None, finish_reason="stop"),
        ]
    )
    wrong = _parse_stream([_event(model="kimi-k3", delta={"content": "answer"})])
    conflicting = _parse_stream(
        [
            _event(delta={"content": "answer"}),
            _event(model="kimi-k3", finish_reason="stop"),
        ]
    )

    assert missing.model_identity is None
    assert conflicting.model_identity == "kimi-k2.6"
    assert conflicting.malformed_envelope is True
    assert conflicting.model_identity_invalid is True
    expected_reasons = (
        "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN",
        "HTTP_RESPONSE_MODEL_IDENTITY_INVALID",
        "HTTP_RESPONSE_MODEL_IDENTITY_INVALID",
    )
    for response, expected_reason in zip(
        (missing, wrong, conflicting), expected_reasons, strict=True
    ):
        with pytest.raises(KnownCloudDistillationResponseError) as error:
            _transport(response, []).generate(_input())
        assert error.value.reason == expected_reason
        assert _PRIVATE_REASONING not in repr(error.value)


@pytest.mark.parametrize(
    "body",
    [
        b"data: {not-json}\n\n",
        b"data: \"not-an-object\"\n\n",
        b"not an SSE event\n",
    ],
)
def test_malformed_sse_and_json_chunks_fail_closed(body: bytes) -> None:
    response = _parse_moonshot_sse_stream(_http_response(body))
    assert response.malformed_envelope is True
    assert response.final_content is None


def test_stream_requires_done_even_after_stop_and_never_uses_reasoning_as_final() -> None:
    body = _sse(
        [
            _event(delta={"reasoning_content": _PRIVATE_REASONING}),
            _event(finish_reason="stop"),
        ]
    ).removesuffix(b"data: [DONE]\n\n")
    response = _parse_moonshot_sse_stream(_http_response(body))

    assert response.model_identity == "kimi-k2.6"
    assert response.finish_reason == "stop"
    assert response.stream_complete is False
    assert response.stream_started is True
    assert response.content_present is False
    assert response.reasoning_present is True
    assert _PRIVATE_REASONING not in repr(response)
    calls: list[object] = []
    with pytest.raises(RuntimeError, match="outcome is not confirmed"):
        _transport(response, calls).generate(_input())
    assert len(calls) == 1
    dispatch = calls[0]
    assert isinstance(dispatch, tuple)
    assert dispatch[3] == 0


def test_non_streaming_response_rejects_missing_or_wrong_model_identity() -> None:
    base = {
        "object": "chat.completion",
        "choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}],
    }
    missing = _parse_moonshot_sse_stream(
        _http_response(json.dumps(base).encode("utf-8"))
    )
    wrong = _parse_moonshot_sse_stream(
        _http_response(json.dumps({**base, "model": "kimi-k3"}).encode("utf-8"))
    )

    assert missing.model_identity is None
    with pytest.raises(KnownCloudDistillationResponseError) as error:
        _transport(missing, []).generate(_input())
    assert error.value.result is None
    with pytest.raises(KnownCloudDistillationResponseError) as error:
        _transport(wrong, []).generate(_input())
    assert error.value.result is not None


def test_reasoning_only_responses_never_count_as_final_content() -> None:
    non_streaming = _parse_moonshot_sse_stream(
        _http_response(
            json.dumps(
                {
                    "object": "chat.completion",
                    "model": "kimi-k2.6",
                    "choices": [
                        {
                            "message": {"reasoning_content": _PRIVATE_REASONING},
                            "finish_reason": "stop",
                        }
                    ],
                }
            ).encode("utf-8")
        )
    )
    streaming = _parse_stream(
        [
            _event(delta={"reasoning_content": _PRIVATE_REASONING}),
            _event(finish_reason="stop"),
        ]
    )

    for response in (non_streaming, streaming):
        assert response.reasoning_present is True
        assert response.content_present is False
        assert _PRIVATE_REASONING not in repr(response)
        with pytest.raises(KnownCloudDistillationResponseError) as error:
            _transport(response, []).generate(_input())
        assert error.value.reason == "CLOUD_FINAL_CONTENT_MISSING"
        assert error.value.result is not None
        assert error.value.result.raw == ""
        assert _PRIVATE_REASONING not in repr(error.value)


@pytest.mark.parametrize("content", [None, ""])
def test_reasoning_without_final_content_is_known_missing_output(content: str | None) -> None:
    with pytest.raises(KnownCloudDistillationResponseError) as error:
        _transport(_response(content=content), []).generate(_input())

    assert error.value.reason == "CLOUD_FINAL_CONTENT_MISSING"
    assert error.value.result is not None
    assert error.value.result.raw == ""
    assert _PRIVATE_REASONING not in repr(error.value)


def test_output_budget_exhaustion_is_known_truncation() -> None:
    with pytest.raises(KnownCloudDistillationResponseError) as error:
        _transport(_response(content="", finish_reason="length"), []).generate(_input())

    assert error.value.reason == "CLOUD_OUTPUT_TRUNCATED"
    assert error.value.http_status == 200


def test_wrong_model_and_malformed_envelope_are_known_responses() -> None:
    for response in (
        _response(model="kimi-k3"),
        _response(malformed=True),
        _response(stream_complete=False),
    ):
        with pytest.raises(KnownCloudDistillationResponseError) as error:
            _transport(response, []).generate(_input())
        assert error.value.http_status == 200
        assert "reasoning" not in str(error.value).lower()


def test_provider_reasoning_chunks_are_discarded_while_usage_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    response_bytes = _sse(
        [
            _event(delta={"reasoning_content": _PRIVATE_REASONING}),
            _event(delta={"content": "final"}),
            _event(finish_reason="stop"),
            _event(
                choices=[],
                usage={
                    "prompt_tokens": 5644,
                    "completion_tokens": 321,
                    "completion_tokens_details": {"reasoning_tokens": 300},
                },
            ),
        ]
    )
    requests: list[tuple[str, str]] = []

    class Connection:
        def __init__(self, host: str, *, timeout: float) -> None:
            assert host == "api.moonshot.cn"
            assert timeout == 300.0

        def request(self, method: str, path: str, *, body: bytes, headers: Mapping[str, str]) -> None:
            requests.append((method, path))
            assert path == "/v1/chat/completions"
            assert method == "POST"
            assert headers["Authorization"] == f"Bearer {_SECRET}"
            assert headers["Accept"] == "text/event-stream, application/json"
            assert _SECRET.encode() not in body
            assert b'"model":"kimi-k2.6"' in body
            assert b'"max_tokens":16384' in body
            assert b'"temperature"' not in body

        def getresponse(self) -> object:
            return _http_response(response_bytes)

        def close(self) -> None:
            pass

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", Connection)
    response = _moonshot_chat_completions_http_transport(
        MoonshotK26CloudDistillationTransport._request(_input()), _SECRET, 300.0, 0
    )

    assert response.final_content == "final"
    assert response.reasoning_present is True
    assert response.reasoning_length == len(_PRIVATE_REASONING)
    assert _PRIVATE_REASONING not in repr(response)
    assert requests == [("POST", "/v1/chat/completions")]


def test_cn_endpoint_identity_is_fixed_and_rejects_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = MoonshotK26CloudDistillationTransport._request(_input())
    assert request["endpoint_identity"] == "https://api.moonshot.cn/v1/chat/completions"
    assert "api.moonshot.ai" not in request["endpoint_identity"]

    connections: list[str] = []

    class Connection:
        def __init__(self, host: str, *, timeout: float) -> None:
            connections.append(host)

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", Connection)
    with pytest.raises(CloudDistillationPreDispatchError) as error:
        _moonshot_chat_completions_http_transport(
            {
                **request,
                "endpoint_identity": "https://api.moonshot.ai/v1/chat/completions",
            },
            _SECRET,
            300.0,
            0,
        )

    assert connections == []
    assert _SECRET not in str(error.value)


@pytest.mark.parametrize("status", [400, 429, 500, 503])
def test_known_http_error_is_not_ambiguous_and_body_is_not_retained(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    class Connection:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def request(self, *_args: object, **_kwargs: object) -> None:
            pass

        def getresponse(self) -> object:
            return _http_response(b"provider error body with private data", status=status)

        def close(self) -> None:
            pass

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", Connection)
    with pytest.raises(KnownCloudDistillationResponseError) as error:
        _moonshot_chat_completions_http_transport(
            MoonshotK26CloudDistillationTransport._request(_input()), _SECRET, 300.0, 0
        )
    assert error.value.http_status == status
    assert "private data" not in str(error.value)
    assert _SECRET not in str(error.value)


def test_transport_unknown_before_http_response_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    class Connection:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def request(self, *_args: object, **_kwargs: object) -> None:
            nonlocal calls
            calls += 1

        def getresponse(self) -> object:
            raise TimeoutError("unconfirmed response")

        def close(self) -> None:
            pass

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", Connection)
    with pytest.raises(RuntimeError, match="outcome is not confirmed"):
        _moonshot_chat_completions_http_transport(
            MoonshotK26CloudDistillationTransport._request(_input()), _SECRET, 300.0, 0
        )
    assert calls == 1


def test_wrong_provider_model_or_input_hash_fails_before_wire() -> None:
    calls: list[object] = []
    transport = _transport(_response(), calls)

    for value in (
        replace(_input(), selected_provider="openai"),
        replace(_input(), selected_model="kimi-k2.7-code"),
        replace(_input(), semantic_hash="d" * 64),
    ):
        with pytest.raises(CloudDistillationPreDispatchError):
            transport.generate(value)

    assert calls == []


def test_missing_credential_is_pre_dispatch_and_not_logged() -> None:
    calls: list[object] = []
    transport = MoonshotK26CloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="moonshot",
            model="kimi-k2.6",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=_input().semantic_hash,
        ),
        credential_resolver=lambda: "",
        wire_transport=lambda *args: calls.append(args),
    )

    with pytest.raises(CloudDistillationPreDispatchError) as error:
        transport.generate(_input())

    assert calls == []
    assert _SECRET not in str(error.value)


def test_environment_credential_contract_is_backend_only_moonshot_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOONSHOT_API_KEY", _SECRET)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    transport = MoonshotK26CloudDistillationTransport.with_environment_credential(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="moonshot",
            model="kimi-k2.6",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=_input().semantic_hash,
        ),
        wire_transport=lambda *_args: _response(),
    )

    assert transport.preflight_available() is True
    assert _SECRET not in repr(transport)


def test_stream_parser_rejects_malformed_choice_and_wrong_identity_without_raw_body(monkeypatch: pytest.MonkeyPatch) -> None:
    malformed = _sse([_event(choices=[{"index": 0, "delta": None}])])

    class Connection:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def request(self, *_args: object, **_kwargs: object) -> None:
            pass

        def getresponse(self) -> object:
            return _http_response(malformed)

        def close(self) -> None:
            pass

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", Connection)
    response = _moonshot_chat_completions_http_transport(
        MoonshotK26CloudDistillationTransport._request(_input()), _SECRET, 300.0, 0
    )
    assert response.malformed_envelope is True
    assert _PRIVATE_REASONING not in repr(response)


def test_openai_and_nvidia_authorities_are_not_reassigned_to_moonshot() -> None:
    assert not _transport(_response(), []).is_authorized_for_qualification(
        replace(_input(), selected_provider="nvidia_nim", selected_model="kimi-k2.6")
    )
    assert MoonshotK26CloudDistillationTransport._PROVIDER == "moonshot"
    assert MoonshotK26CloudDistillationTransport._MODEL == "kimi-k2.6"
