from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from youtube_intel.analysis import KnownLocalSummaryResponseError, build_analysis_input
from youtube_intel.config import LocalAnalysisSettings
from youtube_intel.domain import Availability, LiveStatus, VideoMetadata
from youtube_intel.providers.ollama_analysis import OllamaSummaryProvider


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-123",
        channel_id="channel-123",
        channel_name="Example Channel",
        title="Useful title",
        description="description",
        source_url="https://example.invalid/watch?v=video-123",
        published_at=datetime(2026, 7, 20, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _settings() -> LocalAnalysisSettings:
    return LocalAnalysisSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41",
    )


def test_local_summary_request_identity_binds_language_and_model_digest() -> None:
    settings = _settings()
    transcript = "The transcript says a product launch happened in April."
    chinese = build_analysis_input(
        video=_video(),
        transcript_text=transcript,
        language="en",
        output_language="zh-CN",
        settings=settings,
        provider="ollama",
        operation="local-analysis",
        prompt_version="analysis-prompt-v4",
    )
    english = build_analysis_input(
        video=_video(),
        transcript_text=transcript,
        language="en",
        output_language="en",
        settings=settings,
        provider="ollama",
        operation="local-analysis",
        prompt_version="analysis-prompt-v4",
    )
    other_digest = LocalAnalysisSettings(
        model="qwen3:8b", expected_model_digest="sha256:" + "6" * 64
    )
    other_model_identity = build_analysis_input(
        video=_video(),
        transcript_text=transcript,
        language="en",
        output_language="en",
        settings=other_digest,
        provider="ollama",
        operation="local-analysis",
        prompt_version="analysis-prompt-v4",
    )
    assert chinese.request_hash != english.request_hash
    assert english.request_hash != other_model_identity.request_hash


def test_local_summary_request_identity_binds_context_size(monkeypatch) -> None:
    kwargs = dict(
        video=_video(), transcript_text="A real transcript.", language="en",
        output_language="en", settings=_settings(), provider="ollama",
        operation="local-analysis", prompt_version="analysis-prompt-v4",
    )
    before = build_analysis_input(**kwargs)
    monkeypatch.setattr("youtube_intel.analysis.LOCAL_ANALYSIS_CONTEXT_TOKENS", 4_096)
    after = build_analysis_input(**kwargs)
    assert before.request_hash != after.request_hash


def test_local_transcript_sample_normalizes_only_whitespace_for_grounding() -> None:
    request = build_analysis_input(
        video=_video(),
        transcript_text="A source line\nwraps here.",
        language="en",
        output_language="zh-CN",
        settings=_settings(),
        provider="ollama",
        operation="local-analysis",
        prompt_version="analysis-prompt-v4",
    )
    assert "\n" not in request.payload.transcript_sample
    assert "A source line wraps here." in request.payload.transcript_sample


def test_unqualified_local_summary_model_is_rejected_before_transport() -> None:
    settings = LocalAnalysisSettings(
        model="other-model", expected_model_digest="sha256:" + "6" * 64
    )
    provider = OllamaSummaryProvider(settings=settings)
    requests: list[object] = []
    provider._read = lambda request: requests.append(request)  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="not qualified"):
        provider.preflight()
    assert requests == []


def test_local_summary_uses_loopback_digest_preflight_and_grounded_structured_result() -> (
    None
):
    provider = OllamaSummaryProvider(settings=_settings())
    response = {
        "model": "qwen3:8b",
        "message": {
            "content": json.dumps(
                {
                    "one_sentence_summary": "The video introduces a product idea.",
                    "core_points": [
                        {
                            "text": "The title names the subject.",
                            "kind": "fact",
                            "evidence_ids": ["e1"],
                        }
                    ],
                    "keywords": ["product"],
                    "evidence": [
                        {
                            "evidence_id": "e1",
                            "source": "title",
                            "excerpt": "Useful title",
                        }
                    ],
                }
            )
        },
        "done": True,
        "prompt_eval_count": 321,
        "eval_count": 72,
    }
    requests: list[object] = []

    def fake_read(request):
        requests.append(request)
        if request.full_url.endswith("/api/tags"):
            return {"models": [{"name": "qwen3:8b", "digest": _settings().expected_model_digest}]}
        body = json.loads(request.data)
        assert body["stream"] is False
        assert body["options"]["num_ctx"] == 8_192
        assert body["format"]["type"] == "object"
        schema_text = json.dumps(body["format"])
        assert "minLength" not in schema_text
        assert "maxLength" not in schema_text
        assert "minItems" not in schema_text
        assert "maxItems" not in schema_text
        assert "Write all generated text in en" in body["messages"][0]["content"]
        return response

    provider._read = fake_read  # type: ignore[method-assign]
    value = build_analysis_input(
        video=_video(),
        transcript_text="The transcript is English.",
        language="en",
        output_language="en",
        settings=_settings(),
        provider="ollama",
        operation="local-analysis",
        prompt_version="analysis-prompt-v4",
    )
    provider.preflight()
    assert len(requests) == 1
    result = provider.summarize(value)
    assert result.provider == "ollama"
    assert result.prompt_version == "analysis-prompt-v4"
    assert len(requests) == 2
    assert provider.consume_raw_response(request_hash=value.request_hash)


def test_definite_truncated_ollama_response_is_known_invalid() -> None:
    provider = OllamaSummaryProvider(settings=_settings())
    provider._read = lambda _request: {  # type: ignore[method-assign]
        "model": "qwen3:8b", "message": {"content": '{"one_sentence_summary":'},
        "done": True, "done_reason": "length",
        "prompt_eval_count": 3_850, "eval_count": 1_200,
    }
    value = build_analysis_input(
        video=_video(), transcript_text="A real transcript.", language="en",
        output_language="en", settings=_settings(), provider="ollama",
        operation="local-analysis", prompt_version="analysis-prompt-v4",
    )

    with pytest.raises(KnownLocalSummaryResponseError) as raised:
        provider.summarize(value)

    assert raised.value.reason == "generation truncated"
    assert raised.value.prompt_eval_count == 3_850
    assert raised.value.eval_count == 1_200
    assert raised.value.done_reason == "length"
    assert raised.value.response_length == 24
