from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from youtube_intel.analysis import KnownLocalSummaryResponseError, build_analysis_input
from youtube_intel.config import LocalAnalysisSettings
from youtube_intel.domain import Availability, LiveStatus, VideoMetadata
from youtube_intel.providers.ollama_analysis import OllamaSummaryProvider
from youtube_intel.state import VerifiedTimedTranscript, VerifiedTimedTranscriptCue
from youtube_intel.summary_draft import (
    SUMMARY_DRAFT_PROMPT_VERSION,
    SummaryDraft,
    SummaryDraftError,
)
from youtube_intel.summary_evidence_candidates import build_trusted_evidence_registry

VIDEO_ID = "video-123"


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id=VIDEO_ID,
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


def _timed_transcript() -> VerifiedTimedTranscript:
    texts = ("The transcript says a product launch happened.",
             "A second cue describes the pricing model.")
    return VerifiedTimedTranscript(
        timed_transcript_id="tt-1",
        video_id=VIDEO_ID,
        canonical_artifact_id="artifact-1",
        timed_transcript_hash="b" * 64,
        cues=tuple(
            VerifiedTimedTranscriptCue(
                cue_index=index,
                start_ms=index * 1000,
                end_ms=(index + 1) * 1000,
                text=text,
                text_hash=sha256(text.encode()).hexdigest(),
            )
            for index, text in enumerate(texts)
        ),
    )


def _registry():
    return build_trusted_evidence_registry(
        transcript=_timed_transcript(),
        title="Useful title",
        channel_name="Example Channel",
        description="description",
        input_identity="a" * 64,
    )


def _transcript_ref() -> str:
    from youtube_intel.domain import EvidenceSource

    return next(
        candidate.ref
        for candidate in _registry().candidates
        if candidate.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )


def _input(**kwargs: object):
    return build_analysis_input(
        video=_video(),
        transcript_text=kwargs.pop("transcript_text", "The transcript is English."),
        language="en",
        output_language=kwargs.pop("output_language", "en"),
        settings=_settings(),
        provider="ollama",
        operation="local-analysis",
        prompt_version="analysis-prompt-v5",
        registry=kwargs.pop("registry", _registry()),
    )


def test_local_summary_request_identity_binds_language_and_model_digest() -> None:
    settings = _settings()
    transcript = "The transcript says a product launch happened in April."
    common = dict(
        video=_video(),
        transcript_text=transcript,
        language="en",
        settings=settings,
        provider="ollama",
        operation="local-analysis",
        prompt_version="analysis-prompt-v5",
        registry=_registry(),
    )
    chinese = build_analysis_input(output_language="zh-CN", **common)
    english = build_analysis_input(output_language="en", **common)
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
        prompt_version="analysis-prompt-v5",
        registry=_registry(),
    )
    assert chinese.request_hash != english.request_hash
    assert english.request_hash != other_model_identity.request_hash


def test_local_summary_request_identity_binds_context_size(monkeypatch) -> None:
    kwargs = dict(
        video=_video(),
        transcript_text="A real transcript.",
        language="en",
        output_language="en",
        settings=_settings(),
        provider="ollama",
        operation="local-analysis",
        prompt_version="analysis-prompt-v5",
        registry=_registry(),
    )
    before = build_analysis_input(**kwargs)
    monkeypatch.setattr("youtube_intel.analysis.LOCAL_ANALYSIS_CONTEXT_TOKENS", 4_096)
    after = build_analysis_input(**kwargs)
    assert before.request_hash != after.request_hash


def test_local_transcript_sample_normalizes_only_whitespace_for_grounding() -> None:
    request = _input(
        transcript_text="A source line\nwraps here.",
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


def test_live_local_summary_returns_a_summary_draft_not_a_result() -> None:
    """The live local provider's contract is ``summary-draft-v1``."""

    provider = OllamaSummaryProvider(settings=_settings())
    ref = _transcript_ref()
    response = {
        "model": "qwen3:8b",
        "message": {
            "content": json.dumps(
                {
                    "one_sentence_summary": "The video introduces a product idea.",
                    "core_points": [
                        {
                            "text": "The transcript describes a launch.",
                            "kind": "fact",
                            "evidence_refs": [ref],
                        }
                    ],
                    "keywords": ["product"],
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
            return {
                "models": [
                    {
                        "name": "qwen3:8b",
                        "digest": _settings().expected_model_digest,
                    }
                ]
            }
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
    value = _input()
    provider.preflight()
    assert len(requests) == 1
    draft = provider.summarize(value)
    assert isinstance(draft, SummaryDraft)
    assert not hasattr(draft, "evidence")
    assert not hasattr(draft, "request_hash")
    assert draft.cited_refs() == (ref,)
    assert len(requests) == 2
    assert provider.consume_raw_response(request_hash=value.request_hash)


def test_live_local_model_schema_has_no_excerpt_or_offset_authority() -> None:
    """The actual schema sent to the qualified local model cannot carry one."""

    provider = OllamaSummaryProvider(settings=_settings())
    captured: dict[str, object] = {}
    provider._read = lambda request: (  # type: ignore[method-assign]
        captured.update(body=json.loads(request.data))
        or {"model": "qwen3:8b", "message": {"content": "{}"}, "done": True}
    )
    with pytest.raises(KnownLocalSummaryResponseError):
        provider.summarize(_input())
    schema_text = json.dumps(captured["body"]["format"])
    assert "excerpt" not in schema_text
    assert "evidence_id" not in schema_text
    assert "start_ms" not in schema_text
    assert "timestamp" not in schema_text
    assert "offset" not in schema_text
    assert "evidence_refs" in schema_text
    prompt = captured["body"]["messages"][0]["content"]
    assert "Never reproduce, quote, or paraphrase source transcript text" in prompt
    assert _transcript_ref() in prompt


def test_local_model_attempting_an_excerpt_fails_closed() -> None:
    provider = OllamaSummaryProvider(settings=_settings())
    provider._read = lambda _request: {  # type: ignore[method-assign]
        "model": "qwen3:8b",
        "message": {
            "content": json.dumps(
                {
                    "one_sentence_summary": "s",
                    "core_points": [
                        {
                            "text": "t",
                            "kind": "fact",
                            "evidence_refs": [_transcript_ref()],
                        }
                    ],
                    "keywords": ["k"],
                    "evidence": [
                        {
                            "evidence_id": _transcript_ref(),
                            "source": "transcript_sample",
                            "excerpt": "authored by the model",
                        }
                    ],
                }
            )
        },
        "done": True,
    }

    with pytest.raises(KnownLocalSummaryResponseError) as raised:
        provider.summarize(_input())

    assert "author authoritative Evidence text" in raised.value.reason


def test_local_model_attempting_a_nested_excerpt_field_fails_closed() -> None:
    provider = OllamaSummaryProvider(settings=_settings())
    provider._read = lambda _request: {  # type: ignore[method-assign]
        "model": "qwen3:8b",
        "message": {
            "content": json.dumps(
                {
                    "one_sentence_summary": "s",
                    "core_points": [
                        {
                            "text": "t",
                            "kind": "fact",
                            "evidence_refs": [_transcript_ref()],
                            "excerpt": "authored by the model",
                        }
                    ],
                    "keywords": ["k"],
                }
            )
        },
        "done": True,
    }

    with pytest.raises(KnownLocalSummaryResponseError) as raised:
        provider.summarize(_input())

    assert "contract validation" in raised.value.reason


def test_local_summary_without_a_trusted_evidence_offer_fails_closed() -> None:
    provider = OllamaSummaryProvider(settings=_settings())
    dispatched: list[object] = []
    provider._read = lambda request: dispatched.append(request)  # type: ignore[method-assign]
    without_offer = build_analysis_input(
        video=_video(),
        transcript_text="The transcript is English.",
        language="en",
        output_language="en",
        settings=_settings(),
        provider="ollama",
        operation="local-analysis",
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
    )

    with pytest.raises(ValueError, match="trusted Evidence offer"):
        provider.summarize(without_offer)

    assert dispatched == []


def test_definite_truncated_ollama_response_is_known_invalid() -> None:
    provider = OllamaSummaryProvider(settings=_settings())
    provider._read = lambda _request: {  # type: ignore[method-assign]
        "model": "qwen3:8b", "message": {"content": '{"one_sentence_summary":'},
        "done": True, "done_reason": "length",
        "prompt_eval_count": 3_850, "eval_count": 1_200,
    }

    with pytest.raises(KnownLocalSummaryResponseError) as raised:
        provider.summarize(_input())

    assert raised.value.reason == "generation truncated"
    assert raised.value.prompt_eval_count == 3_850
    assert raised.value.eval_count == 1_200
    assert raised.value.done_reason == "length"
    assert raised.value.response_length == 24


def test_strict_parser_rejects_every_unsupported_authority_field() -> None:
    """The shared parser is the single fail-closed gate for both providers."""

    from youtube_intel.summary_draft import parse_summary_draft

    ref = _transcript_ref()
    base = {
        "one_sentence_summary": "s",
        "core_points": [{"text": "t", "kind": "fact", "evidence_refs": [ref]}],
        "keywords": ["k"],
    }
    for forbidden in (
        {"excerpt": "authored"},
        {"evidence": []},
        {"start_ms": 0},
        {"end_ms": 1},
        {"start_seconds": 0},
        {"timestamp": "00:00:01"},
        {"offsets": [0, 1]},
    ):
        with pytest.raises(SummaryDraftError):
            parse_summary_draft(json.dumps({**base, **forbidden}))
