"""Offline integration tests for the injected Ollama HTTP transport."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    Availability,
    ErrorCode,
    LiveStatus,
    VideoMetadata,
)
from youtube_intel.providers.ollama import OllamaProviderError, OllamaScoringProvider
from youtube_intel.scoring import build_scoring_input

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


class _FakeTransport:
    def __init__(self, responses: list[object]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str, bytes | None]] = []

    def __call__(self, request: object, timeout: float) -> _Response:
        method = getattr(request, "method")
        url = getattr(request, "full_url")
        data = getattr(request, "data")
        self.requests.append((method, url, data))
        return _Response(self._responses.pop(0))


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:" + ("b" * 64),
    )


def _input() -> object:
    video = VideoMetadata(
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
    return build_scoring_input(
        video=video,
        transcript_text="A sufficiently long canonical transcript for scoring.",
        language="en",
        settings=_settings(),
    )


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
    assert [method for method, _, _ in transport.requests] == ["GET", "POST"]
    assert [url for _, url, _ in transport.requests] == [
        "http://127.0.0.1:11434/api/tags",
        "http://127.0.0.1:11434/api/generate",
    ]
    payload = json.loads(transport.requests[1][2] or b"{}")
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"]["temperature"] == 0.0


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


def test_mismatched_digest_fails_before_any_generate_request() -> None:
    transport = _FakeTransport([_tags(digest="sha256:" + ("c" * 64))])

    with pytest.raises(OllamaProviderError) as exc_info:
        _provider(transport).score(_input())

    assert exc_info.value.error.code is ErrorCode.CONFIG_INVALID
    assert exc_info.value.error.retryable is False
    assert [method for method, _, _ in transport.requests] == ["GET"]
