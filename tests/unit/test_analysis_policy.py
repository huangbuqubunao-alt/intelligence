"""Offline policy tests for optional cloud analysis."""

from __future__ import annotations

from datetime import UTC, datetime

from youtube_intel.analysis import (
    AnalysisService,
    CloudCallBudget,
    InMemoryAnalysisCache,
    build_analysis_input,
)
from youtube_intel.config import CloudSettings
from youtube_intel.domain import (
    AnalysisResult,
    AnalysisSkipReason,
    Availability,
    LiveStatus,
    VideoMetadata,
)


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-123",
        channel_id="channel-123",
        channel_name="Example Channel",
        title="Useful title",
        description="public description",
        source_url="https://example.invalid/watch?v=video-123",
        published_at=datetime(2026, 7, 20, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _settings(*, enabled: bool = True) -> CloudSettings:
    return CloudSettings(enabled=enabled, model="gpt-4.1-mini" if enabled else None)


class _Provider:
    def __init__(self) -> None:
        self.calls = 0

    def summarize(self, analysis_input: object) -> AnalysisResult:
        self.calls += 1
        request_hash = getattr(analysis_input, "request_hash")
        return AnalysisResult.model_validate(
            {
                "one_sentence_summary": "The transcript supports one useful claim.",
                "core_points": [
                    {
                        "text": "Useful title is the stated topic.",
                        "kind": "fact",
                        "evidence_ids": ["title-1"],
                    }
                ],
                "keywords": ["useful"],
                "evidence": [
                    {
                        "evidence_id": "title-1",
                        "source": "title",
                        "excerpt": "Useful title",
                    }
                ],
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "request_hash": request_hash,
            }
        )


class _CredentialResolver:
    def __init__(self, value: str | None = "synthetic-key") -> None:
        self.value = value
        self.calls = 0

    def resolve(self, env_name: str) -> str | None:
        self.calls += 1
        return self.value


def test_disabled_policy_never_reads_credentials_or_calls_provider() -> None:
    provider = _Provider()
    resolver = _CredentialResolver()
    service = AnalysisService(
        provider=provider,
        settings=_settings(enabled=False),
        cache=InMemoryAnalysisCache(),
        budget=CloudCallBudget(limit=5),
        credential_resolver=resolver,
    )

    outcome = service.analyze(
        video=_video(), transcript_text="a canonical transcript with enough text", language="en"
    )

    assert outcome.reason is AnalysisSkipReason.CLOUD_DISABLED
    assert provider.calls == 0
    assert resolver.calls == 0


def test_low_value_video_creates_no_outcome_or_provider_side_effect() -> None:
    provider = _Provider()
    resolver = _CredentialResolver()
    service = AnalysisService(
        provider=provider, settings=_settings(), cache=InMemoryAnalysisCache(),
        budget=CloudCallBudget(limit=5), credential_resolver=resolver,
    )

    outcome = service.analyze(
        video=_video(), transcript_text="a canonical transcript with enough text", language="en",
        should_summarize=False,
    )

    assert outcome is None
    assert provider.calls == 0
    assert resolver.calls == 0


def test_analysis_input_is_deterministic_and_only_contains_whitelisted_payload() -> None:
    first = build_analysis_input(
        video=_video(),
        transcript_text="abcdefghij" * 40,
        language="en",
        output_language="zh-CN",
        settings=_settings(),
    )
    second = build_analysis_input(
        video=_video(),
        transcript_text="abcdefghij" * 40,
        language="en",
        output_language="zh-CN",
        settings=_settings(),
    )

    assert first == second
    assert set(first.payload.model_dump()) == {
        "video_id", "title", "channel_name", "published_at", "duration_seconds",
        "default_language", "description", "transcript_language", "output_language",
        "transcript_sample",
    }
    assert len(first.payload.transcript_sample) <= 4_000


def test_success_is_cached_before_credentials_are_read_again() -> None:
    provider = _Provider()
    resolver = _CredentialResolver()
    service = AnalysisService(
        provider=provider,
        settings=_settings(),
        cache=InMemoryAnalysisCache(),
        budget=CloudCallBudget(limit=5),
        credential_resolver=resolver,
    )

    first = service.analyze(
        video=_video(), transcript_text="a canonical transcript with enough text", language="en"
    )
    second = service.analyze(
        video=_video(), transcript_text="a canonical transcript with enough text", language="en"
    )

    assert first.result.request_hash == second.result.request_hash
    assert provider.calls == 1
    assert resolver.calls == 1
