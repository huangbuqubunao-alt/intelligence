"""Deterministic local-scoring sampling, cache, and threshold policy.

This module deliberately owns no network or SQLite implementation.  It produces
the frozen domain contracts and keeps model suggestions distinct from the
application's configured summary threshold.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Final, Protocol

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    DiagnosticEntry,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringInput,
    ScoringOutcome,
    ScoringProvider,
    TranscriptSample,
    VideoMetadata,
)
from youtube_intel.state import build_provider_request_hash

PROMPT_VERSION: Final = "scoring-prompt-v1"
SCHEMA_VERSION: Final = "score-result-v1"
SAMPLING_VERSION: Final = "sampling-v1"
_SCORING_OPERATION: Final = "local-scoring"
_CLOCK = Callable[[], datetime]


class ScoringCache(Protocol):
    """Cache boundary keyed by the canonical primary scoring request hash."""

    def get(self, request_hash: str) -> ScoreResult | None: ...

    def put(self, result: ScoreResult) -> None: ...


class InMemoryScoringCache:
    """Small deterministic cache suitable for offline tests and local composition."""

    def __init__(self) -> None:
        self._results: dict[str, ScoreResult] = {}

    def get(self, request_hash: str) -> ScoreResult | None:
        return self._results.get(request_hash)

    def put(self, result: ScoreResult) -> None:
        self._results[result.request_hash] = result


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sample_transcript(transcript_text: str, *, max_chars: int) -> TranscriptSample:
    """Select the ADR-007 ``sampling-v1`` head/centre/tail transcript sample."""

    if max_chars < 3:
        msg = "max_chars must be at least 3"
        raise ValueError(msg)
    if len(transcript_text) < 3:
        msg = "transcript_text must contain at least 3 characters"
        raise ValueError(msg)

    transcript_length = len(transcript_text)
    if transcript_length <= max_chars:
        head = transcript_text
        body = ""
        tail = ""
    else:
        head_length = (max_chars + 2) // 3
        body_length = (max_chars + 1) // 3
        tail_length = max_chars // 3
        available_body_start = head_length
        available_body_end = transcript_length - tail_length
        available_body_length = available_body_end - available_body_start
        body_start = available_body_start + (available_body_length - body_length) // 2
        head = transcript_text[:head_length]
        body = transcript_text[body_start : body_start + body_length]
        tail = transcript_text[available_body_end:]

    return TranscriptSample(
        head=head,
        body=body,
        tail=tail,
        selected_char_count=len(head) + len(body) + len(tail),
        source_content_hash=_sha256_text(transcript_text),
        sampling_version=SAMPLING_VERSION,
    )


def build_scoring_input(
    *,
    video: VideoMetadata,
    transcript_text: str,
    language: str,
    settings: LocalScoringSettings,
) -> ScoringInput:
    """Build one versioned scoring input and its provider-call cache key."""

    if not language or language != language.strip():
        msg = "language must be a non-empty value without surrounding whitespace"
        raise ValueError(msg)

    sample = sample_transcript(
        transcript_text,
        max_chars=settings.max_transcript_chars,
    )
    selected_metadata = [
        video.video_id,
        video.title,
        video.channel_name,
        video.published_at.astimezone(UTC).isoformat(),
        video.duration_seconds,
        video.default_language,
        language,
        video.description[: settings.max_description_chars],
    ]
    normalized_input_hash = _sha256_text(
        _canonical_json(
            {
                "metadata": selected_metadata,
                "transcript_content_hash": sample.source_content_hash,
                "sample": {
                    "head": sample.head,
                    "body": sample.body,
                    "tail": sample.tail,
                    "selected_char_count": sample.selected_char_count,
                    "sampling_version": sample.sampling_version,
                },
                "language": language,
                "model": settings.model,
                "temperature": settings.temperature,
                "max_output_tokens": settings.max_output_tokens,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
            }
        )
    )
    request_hash = build_provider_request_hash(
        operation=_SCORING_OPERATION,
        normalized_input_hash=normalized_input_hash,
        provider="ollama",
        model=settings.model,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    return ScoringInput(
        video=video,
        sample=sample,
        transcript_content_hash=sample.source_content_hash,
        language=language,
        request_hash=request_hash,
    )


class ScoringService:
    """Apply cache and threshold policy around a structural scoring Provider."""

    def __init__(
        self,
        *,
        provider: ScoringProvider,
        settings: LocalScoringSettings,
        summary_threshold: float,
        cache: ScoringCache,
        clock: _CLOCK = _utcnow,
    ) -> None:
        if not 0 <= summary_threshold <= 10:
            msg = "summary_threshold must be in 0..10"
            raise ValueError(msg)
        self._provider = provider
        self._settings = settings
        self._summary_threshold = summary_threshold
        self._cache = cache
        self._clock = clock

    def score(
        self,
        *,
        video: VideoMetadata,
        transcript_text: str,
        language: str,
    ) -> ScoringOutcome:
        scoring_input = build_scoring_input(
            video=video,
            transcript_text=transcript_text,
            language=language,
            settings=self._settings,
        )
        started_at = self._clock()
        cached = self._cache.get(scoring_input.request_hash)
        diagnostics: list[DiagnosticEntry] = []
        if cached is None:
            result = self._provider.score(scoring_input)
            if result.request_hash != scoring_input.request_hash:
                msg = "scoring provider returned a result for a different request"
                raise ValueError(msg)
            self._cache.put(result)
        else:
            result = cached
            diagnostics.append(
                DiagnosticEntry(
                    code="CACHE_HIT",
                    message="reused cached structured local-scoring result",
                )
            )
        final_should_summarize = result.score >= self._summary_threshold
        model_disagrees = result.should_summarize != final_should_summarize
        if model_disagrees:
            diagnostics.append(
                DiagnosticEntry(
                    code="MODEL_POLICY_DISAGREEMENT",
                    message="configured summary threshold overrides the model suggestion",
                )
            )
        finished_at = self._clock()
        return ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=self._summary_threshold,
                final_should_summarize=final_should_summarize,
                model_disagrees=model_disagrees,
            ),
            call=ProviderCallMetadata(
                provider=result.provider,
                model=result.model,
                started_at=started_at,
                finished_at=finished_at,
                diagnostics=tuple(diagnostics),
            ),
        )


__all__ = [
    "InMemoryScoringCache",
    "PROMPT_VERSION",
    "SAMPLING_VERSION",
    "SCHEMA_VERSION",
    "ScoringCache",
    "ScoringService",
    "build_scoring_input",
    "sample_transcript",
]
