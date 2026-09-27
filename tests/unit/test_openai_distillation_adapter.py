"""Offline contract tests for the bounded OpenAI Responses distillation route."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import replace

import pytest

from youtube_intel.distillation import (
    CloudDistillationAuthorization,
    CloudDistillationPreDispatchError,
    KnownCloudDistillationResponseError,
    OpenAICloudDistillationTransport,
    PersonalizedDistillationService,
    VerifiedDistillationInput,
    VerifiedEvidenceInput,
    _openai_responses_http_transport,
)


def _input() -> VerifiedDistillationInput:
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
        selected_provider="openai",
        selected_model="gpt-4.1",
        semantic_hash="c" * 64,
        output_language="zh-CN",
    )


def _response(*, content: object = '{"result":"NO_NEW_INTELLIGENCE"}', model: object = "gpt-4.1", status: object = "completed") -> dict[str, object]:
    return {
        "object": "response",
        "status": status,
        "model": model,
        "output": [{"type": "message", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": content}]}],
        "usage": {"input_tokens": 5644, "output_tokens": 321},
    }


def _transport(response: Mapping[str, object] | Exception, calls: list[object]) -> OpenAICloudDistillationTransport:
    def wire(request: Mapping[str, object], credential: str, timeout: float, retries: int) -> Mapping[str, object]:
        calls.append((request, credential, timeout, retries))
        if isinstance(response, Exception):
            raise response
        return response

    return OpenAICloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="openai",
            model="gpt-4.1",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=_input().semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: "test-secret-never-persist",
        wire_transport=wire,
    )


def test_raw_responses_output_is_final_content_and_input_stays_complete() -> None:
    calls: list[object] = []
    transport = _transport(_response(content="final JSON"), calls)

    result = transport.generate(_input())

    assert result.raw == "final JSON"
    assert result.actual_provider == "openai"
    assert result.actual_model == "gpt-4.1"
    assert (result.input_tokens, result.output_tokens) == (5644, 321)
    assert len(calls) == 1
    request, credential, _, retries = calls[0]
    assert credential == "test-secret-never-persist"
    assert retries == 0
    assert request["model"] == "gpt-4.1"
    assert request["store"] is False
    assert request["stream"] is False
    assert request["max_output_tokens"] == 4096
    assert "relevant subset" in str(request["input"])
    assert "every supplied evidence_id" in str(request["input"])
    assert len(json.loads(request["input"][2]["content"].split("=", 1)[1])["evidence"]) == 15
    assert "test-secret-never-persist" not in str(request)


def test_multiple_typed_output_parts_are_combined_without_other_output_items() -> None:
    response = _response()
    response["output"] = [
        {"type": "other"},
        {"type": "message", "role": "assistant", "status": "completed",
         "content": [{"type": "output_text", "text": "{\"result\":\""},
                     {"type": "output_text", "text": "NO_NEW_INTELLIGENCE\"}"}]},
    ]
    result = _transport(response, []).generate(_input())
    assert result.raw == '{"result":"NO_NEW_INTELLIGENCE"}'


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (_response(content=None), "CLOUD_FINAL_CONTENT_MISSING"),
        (_response(content=""), "CLOUD_FINAL_CONTENT_MISSING"),
        ({**_response(status="incomplete"), "incomplete_details": {"reason": "max_output_tokens"}}, "CLOUD_OUTPUT_TRUNCATED"),
        ({**_response(), "output": [{}]}, "CLOUD_HTTP_RESPONSE_INVALID"),
        ({**_response(), "model": None}, "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN"),
    ],
)
def test_known_http_envelope_failures_are_not_ambiguous(response: Mapping[str, object], reason: str) -> None:
    with pytest.raises(KnownCloudDistillationResponseError) as error:
        _transport(response, []).generate(_input())
    assert error.value.reason == reason
    assert error.value.http_status == 200
    assert "test-secret-never-persist" not in str(error.value)


def test_wrong_model_is_reported_for_authoritative_mismatch() -> None:
    result = _transport(_response(model="gpt-4.1-mini"), []).generate(_input())
    assert result.actual_model == "gpt-4.1-mini"


def test_missing_credential_is_pre_dispatch() -> None:
    calls: list[object] = []
    transport = OpenAICloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True, provider="openai", model="gpt-4.1",
            credential_available=True, provider_available=True,
            qualification_input_hash=_input().semantic_hash,
        ),
        credential_resolver=lambda: "",
        wire_transport=lambda *args: calls.append(args) or {},
    )
    with pytest.raises(CloudDistillationPreDispatchError):
        transport.generate(_input())
    assert calls == []


@pytest.mark.parametrize(
    "change",
    [
        {"selected_provider": "nvidia_nim"},
        {"selected_model": "gpt-4.1-mini"},
    ],
)
def test_wrong_provider_or_model_has_no_request(change: dict[str, str]) -> None:
    calls: list[object] = []
    transport = _transport(_response(), calls)
    with pytest.raises(CloudDistillationPreDispatchError):
        transport.generate(replace(_input(), **change))
    assert calls == []


def test_transport_without_response_remains_unknown() -> None:
    with pytest.raises(TimeoutError):
        _transport(TimeoutError("no confirmed HTTP response"), []).generate(_input())


def test_received_http_error_is_known_and_never_exposes_body_or_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    class Opener:
        def open(self, outbound: urllib.request.Request, *, timeout: float) -> object:
            assert outbound.full_url == "https://api.openai.com/v1/responses"
            assert outbound.get_method() == "POST"
            assert outbound.get_header("Authorization") == "Bearer test-secret-never-persist"
            assert timeout == 120.0
            assert outbound.data is not None
            assert b"test-secret-never-persist" not in outbound.data
            assert b"endpoint_identity" not in outbound.data
            assert b"max_retries" not in outbound.data
            raise urllib.error.HTTPError(outbound.full_url, 401, "secret in provider body", {}, None)

    monkeypatch.setattr("youtube_intel.distillation.urllib.request.build_opener", lambda handler: Opener())
    request = OpenAICloudDistillationTransport._request(_input())
    with pytest.raises(KnownCloudDistillationResponseError) as error:
        _openai_responses_http_transport(request, "test-secret-never-persist", 120.0, 0)
    assert error.value.http_status == 401
    assert "secret in provider body" not in str(error.value)
    assert "test-secret-never-persist" not in str(error.value)


def test_no_confirmed_http_response_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    class Opener:
        def open(self, outbound: urllib.request.Request, *, timeout: float) -> object:
            raise TimeoutError("test-secret-never-persist")

    monkeypatch.setattr("youtube_intel.distillation.urllib.request.build_opener", lambda handler: Opener())
    with pytest.raises(RuntimeError, match="outcome is not confirmed") as error:
        _openai_responses_http_transport(
            OpenAICloudDistillationTransport._request(_input()),
            "test-secret-never-persist", 120.0, 0,
        )
    assert "test-secret-never-persist" not in str(error.value)


def test_opener_setup_failure_is_pre_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_handler: object) -> object:
        raise RuntimeError("test-secret-never-persist")

    monkeypatch.setattr("youtube_intel.distillation.urllib.request.build_opener", fail)
    with pytest.raises(CloudDistillationPreDispatchError) as error:
        _openai_responses_http_transport(
            OpenAICloudDistillationTransport._request(_input()),
            "test-secret-never-persist", 120.0, 0,
        )
    assert "test-secret-never-persist" not in str(error.value)


def test_fixed_http_boundary_reads_one_completed_response(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[str] = []

    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def read(self, size: int) -> bytes:
            assert size == 2_000_001
            return json.dumps(_response(content="final JSON")).encode()

    class Opener:
        def open(self, outbound: urllib.request.Request, *, timeout: float) -> Response:
            requests.append(outbound.full_url)
            assert timeout == 120.0
            return Response()

    monkeypatch.setattr("youtube_intel.distillation.urllib.request.build_opener", lambda handler: Opener())
    transport = OpenAICloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True, provider="openai", model="gpt-4.1",
            credential_available=True, provider_available=True,
            qualification_input_hash=_input().semantic_hash,
        ),
        credential_resolver=lambda: "test-secret-never-persist",
    )

    result = transport.generate(_input())

    assert result.raw == "final JSON"
    assert (result.input_tokens, result.output_tokens) == (5644, 321)
    assert result.duration_ms is not None
    assert requests == ["https://api.openai.com/v1/responses"]


def test_request_profile_version_changes_execution_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    identity = dict(
        source_id="source-cnn", video_id="cnn-video",
        evidence_ids=tuple(f"evidence-{index}" for index in range(15)),
        selected_provider="openai", selected_model="gpt-4.1",
        output_language="zh-CN", verified_input_hash="c" * 64,
    )
    first = PersonalizedDistillationService._reservation_id(**identity)
    monkeypatch.setattr(
        OpenAICloudDistillationTransport,
        "_REQUEST_PROFILE_VERSION",
        "openai-gpt-4.1-qualification-v2",
    )
    assert PersonalizedDistillationService._reservation_id(**identity) != first
