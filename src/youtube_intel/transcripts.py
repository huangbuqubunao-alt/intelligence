"""Deterministic subtitle selection, normalization, quality, and cache policy."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import math
import os
import re
import tempfile
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Final, Protocol, runtime_checkable

from youtube_intel.domain import (
    AppError,
    DiagnosticEntry,
    ErrorCode,
    JobStatus,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    SubtitleFormat,
    TranscriptArtifact,
    TranscriptFetchResult,
    TranscriptionReason,
    TranscriptionRequired,
    TranscriptQualityFlag,
    TranscriptReady,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.providers.whisper import (
    WhisperAdapterError,
    WhisperDecodePolicy,
    WhisperTranscription,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactWrite,
    JobRecord,
    ProviderCallCompletion,
    ProviderCallRecord,
    ProviderCallRequest,
    ProviderCallStatus,
    ProviderReservation,
    RetentionClass,
    StageCompletionResult,
    StorageRoot,
    VerifiedArtifact,
    VideoRecord,
)
from youtube_intel.transcription import (
    AudioArtifact,
    AudioResourceSnapshot,
    TranscriptionPolicy,
    build_transcription_cache_key,
    cleanup_successful_audio,
)

_SOURCE_RANK = {
    TranscriptSourceType.MANUAL_SUBTITLE: 0,
    TranscriptSourceType.AUTO_SUBTITLE: 1,
}
_FORMAT_RANK = {
    SubtitleFormat.JSON3: 0,
    SubtitleFormat.VTT: 1,
    SubtitleFormat.SRT: 2,
}
SELECTION_POLICY_VERSION: Final = "subtitle-selection-v1"
FORMAT_POLICY_VERSION: Final = "subtitle-format-v1"
NORMALIZATION_VERSION: Final = "subtitle-normalization-v1"
QUALITY_POLICY_VERSION: Final = "subtitle-quality-v1"
_RAW_PRODUCER_VERSION: Final = (
    f"{SELECTION_POLICY_VERSION}+{FORMAT_POLICY_VERSION}"
)
_CANONICAL_PRODUCER_VERSION: Final = (
    f"{NORMALIZATION_VERSION}+{QUALITY_POLICY_VERSION}"
)
_NO_TRACKS_MESSAGE: Final = "subtitle provider returned no tracks"
_NO_MATCH_MESSAGE: Final = "no subtitle tracks matched language preferences"
_ALL_INVALID_MESSAGE: Final = "all subtitle candidates invalid"
_FILE_CHUNK_BYTES: Final = 64 * 1024
_MAX_CANONICAL_BYTES: Final = 4_000_000
_SAFE_VIDEO_ID: Final = re.compile(r"^[A-Za-z0-9_-]{6,32}$")

_VTT_TIMESTAMP = re.compile(
    r"^(?:\d{2}:)?\d{2}:\d{2}\.\d{3}\s+-->\s+"
    r"(?:\d{2}:)?\d{2}:\d{2}\.\d{3}(?:\s+.*)?$"
)
_SRT_TIMESTAMP = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+"
    r"\d{2}:\d{2}:\d{2},\d{3}(?:\s+.*)?$"
)
_INLINE_VTT_TIMESTAMP = re.compile(r"<(?:\d{2}:)?\d{2}:\d{2}\.\d{3}>")
_VOICE_TAG = re.compile(r"<v(?:\.[^ >]+)*(?:\s+([^>]+))?>", re.IGNORECASE)
_VOICE_SPAN = re.compile(
    r"<v(?:\.[^ >]+)*(?:\s+([^>]+))?>(.*?)</v>",
    re.IGNORECASE | re.DOTALL,
)
_STYLE_TAG = re.compile(
    r"</?(?:c(?:\.[^ >]+)*|i|b|u|ruby|rt|font|span)(?:\s+[^>]*)?>",
    re.IGNORECASE,
)
_ASS_STYLE = re.compile(r"\{\\[^}]*\}")
_SPEAKER_PREFIX = re.compile(r"^[^:\n]{1,60}:\s+\S")
_NON_SPEECH_MARKER = re.compile(
    r"(?:\[(?:music|applause|laughter|laughs|cheering|silence|"
    r"sound effect|sfx|inaudible)\]|\((?:music|applause|laughter|"
    r"laughs|cheering|silence|sound effect|sfx|inaudible)\)|[♪♫]+)",
    re.IGNORECASE,
)


class InvalidSubtitleReason(str, Enum):
    INVALID_UTF8 = "INVALID_UTF8"
    MALFORMED = "MALFORMED"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    QUALITY = "QUALITY"


class InvalidSubtitleCandidate(ValueError):
    def __init__(self, reason: InvalidSubtitleReason) -> None:
        self.reason = reason
        super().__init__(f"invalid subtitle candidate: {reason.value.lower()}")


class TranscriptError(Exception):
    """Task-scoped exception carrying a safe, structured AppError."""

    def __init__(self, error: AppError) -> None:
        self.error = error
        super().__init__(error.message)


@dataclass(frozen=True, slots=True)
class SubtitleQualityPolicy:
    max_raw_bytes: int
    max_canonical_code_points: int
    max_segments: int
    min_semantic_characters: int
    max_replacement_ratio: float
    max_deduplication_ratio: float
    compression_check_min_raw_bytes: int
    min_compression_ratio: float


SUBTITLE_QUALITY_POLICY: Final = SubtitleQualityPolicy(
    max_raw_bytes=5_000_000,
    max_canonical_code_points=1_000_000,
    max_segments=100_000,
    min_semantic_characters=20,
    max_replacement_ratio=0.01,
    max_deduplication_ratio=0.80,
    compression_check_min_raw_bytes=10_000,
    min_compression_ratio=0.01,
)


@dataclass(frozen=True, slots=True)
class SubtitleQualityMetrics:
    raw_byte_count: int
    canonical_code_points: int
    segment_count: int
    semantic_character_count: int
    replacement_character_count: int
    non_whitespace_character_count: int
    input_character_count: int
    removed_character_count: int
    canonical_byte_count: int

    def __post_init__(self) -> None:
        if any(
            value < 0
            for value in (
                self.raw_byte_count,
                self.canonical_code_points,
                self.segment_count,
                self.semantic_character_count,
                self.replacement_character_count,
                self.non_whitespace_character_count,
                self.input_character_count,
                self.removed_character_count,
                self.canonical_byte_count,
            )
        ):
            msg = "subtitle quality metrics must be non-negative"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class NormalizedSubtitle:
    text: str
    source_content_hash: str
    source_byte_count: int
    content_hash: str
    char_count: int
    segment_count: int
    quality_flags: tuple[TranscriptQualityFlag, ...]


@dataclass(frozen=True, slots=True)
class SubtitleTrack:
    source_type: TranscriptSourceType
    language: str
    source_format: SubtitleFormat
    name: str
    url: str
    provider_position: int

    def __post_init__(self) -> None:
        if self.source_type not in _SOURCE_RANK:
            msg = "subtitle tracks must be manual or automatic"
            raise ValueError(msg)
        if not isinstance(self.source_format, SubtitleFormat):
            msg = "subtitle track source_format must be a frozen SubtitleFormat"
            raise ValueError(msg)
        if not self.language or self.language.strip() != self.language:
            msg = "subtitle track language must be non-empty without surrounding whitespace"
            raise ValueError(msg)
        if not self.url:
            msg = "subtitle track URL must be non-empty"
            raise ValueError(msg)
        if self.provider_position < 0:
            msg = "provider_position must be non-negative"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class RankedSubtitleCandidate:
    track: SubtitleTrack
    requested_language: str
    language_preference_index: int
    match_rank: int


@dataclass(frozen=True, slots=True)
class SubtitleTrackListing:
    tracks: tuple[SubtitleTrack, ...]
    call: ProviderCallMetadata


@dataclass(frozen=True, slots=True)
class SubtitleReadResult:
    body: bytes
    call: ProviderCallMetadata


@runtime_checkable
class SubtitleAdapter(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def provider_version(self) -> str: ...

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing: ...

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult: ...


@dataclass(frozen=True, slots=True)
class TranscriptJobContext:
    job_id: str
    owner: str
    pipeline_version: str
    refresh_generation: int = 0

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not self.owner.strip():
            msg = "job_id and owner must be non-empty"
            raise ValueError(msg)
        if not self.pipeline_version.strip():
            msg = "pipeline_version must be non-empty"
            raise ValueError(msg)
        if self.refresh_generation < 0:
            msg = "refresh_generation must be non-negative"
            raise ValueError(msg)


@runtime_checkable
class TranscriptRepository(Protocol):
    def get_artifact_by_key(self, artifact_key: str) -> ArtifactRecord | None: ...

    def get_job(self, job_id: str) -> JobRecord | None: ...

    def get_video(self, video_id: str) -> VideoRecord | None: ...

    def mark_artifact_deleted(
        self,
        artifact_id: str,
        expected_content_hash: str,
        now: datetime,
    ) -> bool: ...

    def get_provider_call(self, request_hash: str) -> ProviderCallRecord | None: ...

    def reserve_provider_call(
        self,
        request: ProviderCallRequest,
        *,
        owner: str,
        lease_until: datetime,
        available_at: datetime,
        now: datetime,
        verified_artifact: VerifiedArtifact | None = None,
    ) -> ProviderReservation: ...

    def fail_provider_call(
        self,
        request_hash: str,
        *,
        owner: str,
        retryable: bool,
        available_at: datetime,
        error_code: ErrorCode,
        error_message: str,
        now: datetime,
    ) -> ProviderCallRecord: ...

    def complete_stage(
        self,
        *,
        job_id: str,
        owner: str,
        video_id: str,
        expected_status: PipelineStatus,
        target_status: PipelineStatus,
        pipeline_version: str,
        artifacts: tuple[ArtifactWrite, ...],
        provider_call: ProviderCallCompletion | None,
        now: datetime,
    ) -> StageCompletionResult: ...


def normalize_language_tag(value: str) -> str:
    normalized = value.strip().replace("_", "-").casefold()
    if not normalized:
        msg = "language tags must be non-empty"
        raise ValueError(msg)
    return normalized


def _language_match_rank(actual: str, requested: str) -> int | None:
    if actual == requested:
        return 0
    requested_base = requested.split("-", 1)[0]
    actual_base = actual.split("-", 1)[0]
    if actual == requested_base:
        return 1
    if actual_base == requested_base:
        return 2
    return None


def _normalized_track_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def rank_subtitle_candidates(
    tracks: Sequence[SubtitleTrack],
    language_preferences: Sequence[str],
) -> tuple[RankedSubtitleCandidate, ...]:
    normalized_preferences = tuple(
        normalize_language_tag(language) for language in language_preferences
    )
    ranked: list[RankedSubtitleCandidate] = []
    for track in tracks:
        actual = normalize_language_tag(track.language)
        best_match: tuple[int, int, str] | None = None
        for preference_index, requested in enumerate(normalized_preferences):
            match_rank = _language_match_rank(actual, requested)
            if match_rank is None:
                continue
            best_match = (
                preference_index,
                match_rank,
                language_preferences[preference_index],
            )
            break
        if best_match is None:
            continue
        preference_index, match_rank, requested_language = best_match
        ranked.append(
            RankedSubtitleCandidate(
                track=track,
                requested_language=requested_language,
                language_preference_index=preference_index,
                match_rank=match_rank,
            )
        )

    return tuple(
        sorted(
            ranked,
            key=lambda candidate: (
                _SOURCE_RANK[candidate.track.source_type],
                candidate.language_preference_index,
                candidate.match_rank,
                normalize_language_tag(candidate.track.language),
                _FORMAT_RANK[candidate.track.source_format],
                _normalized_track_name(candidate.track.name),
                candidate.track.provider_position,
            ),
        )
    )


def _parse_json3(text: str) -> list[str]:
    malformed = False
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError:
        malformed = True
        payload = None
    if malformed:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
    if not isinstance(payload, dict):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
    events = payload.get("events")
    if not isinstance(events, list):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)

    cues: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
        segments = event.get("segs")
        if segments is None:
            continue
        if not isinstance(segments, list):
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
        pieces: list[str] = []
        for segment in segments:
            if not isinstance(segment, dict):
                raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
            value = segment.get("utf8")
            if not isinstance(value, str):
                raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
            pieces.append(value)
        cue = "".join(pieces)
        if cue.strip():
            cues.append(cue)
    return cues


def _is_vtt_control_block(first_line: str) -> bool:
    token = first_line.strip().upper()
    return (
        token in {"STYLE", "REGION", "NOTE"}
        or token.startswith("NOTE ")
        or token.startswith("NOTE\t")
    )


def _parse_vtt_block(block: str) -> str | None:
    lines = [line.rstrip() for line in block.splitlines()]
    if not lines:
        return None
    if _is_vtt_control_block(lines[0]):
        return None
    timestamp_index = 0
    if not _VTT_TIMESTAMP.fullmatch(lines[0].strip()):
        timestamp_index = 1
    if (
        timestamp_index >= len(lines)
        or not _VTT_TIMESTAMP.fullmatch(lines[timestamp_index].strip())
        or timestamp_index + 1 >= len(lines)
    ):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
    return "\n".join(lines[timestamp_index + 1 :])


def _parse_vtt(text: str) -> list[str]:
    blocks = re.split(r"\n{2,}", text.strip("\n"))
    if not blocks:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
    header = blocks[0].splitlines()[0].strip()
    if (
        header != "WEBVTT"
        and not header.startswith("WEBVTT ")
        and not header.startswith("WEBVTT\t")
    ):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)

    cues: list[str] = []
    for block in blocks[1:]:
        cue = _parse_vtt_block(block)
        if cue is not None:
            cues.append(cue)
    return cues


def _parse_srt(text: str) -> list[str]:
    blocks = re.split(r"\n{2,}", text.strip("\n"))
    cues: list[str] = []
    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines()]
        if not lines:
            continue
        timestamp_index = 0
        if not _SRT_TIMESTAMP.fullmatch(lines[0].strip()):
            if not lines[0].strip().isdigit():
                raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
            timestamp_index = 1
        if (
            timestamp_index >= len(lines)
            or not _SRT_TIMESTAMP.fullmatch(lines[timestamp_index].strip())
            or timestamp_index + 1 >= len(lines)
        ):
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
        cues.append("\n".join(lines[timestamp_index + 1 :]))
    return cues


def _preserve_vtt_voice_spans(value: str) -> str:
    def replace_voice(match: re.Match[str]) -> str:
        speaker = match.group(1)
        content = match.group(2)
        if speaker is None:
            return content
        normalized_speaker = " ".join(speaker.split())
        return content if not normalized_speaker else f"{normalized_speaker}: {content}"

    return _VOICE_SPAN.sub(replace_voice, value)


def _normalize_cue(value: str) -> str:
    cue = _preserve_vtt_voice_spans(html.unescape(value))
    cue = _VOICE_TAG.sub("", cue)
    cue = re.sub(r"</v>", "", cue, flags=re.IGNORECASE)
    cue = _INLINE_VTT_TIMESTAMP.sub("", cue)
    cue = _STYLE_TAG.sub("", cue)
    cue = _ASS_STYLE.sub("", cue)
    cue = unicodedata.normalize("NFC", cue)
    cue = " ".join(cue.split())
    return cue


def _deduplicate_cues(cues: Sequence[str]) -> tuple[list[str], int, int, bool]:
    output: list[str] = []
    previous: str | None = None
    input_characters = 0
    removed_characters = 0
    changed = False
    for cue in cues:
        input_characters += len(cue)
        if previous is not None and cue == previous:
            removed_characters += len(cue)
            changed = True
            previous = cue
            continue
        if (
            previous is not None
            and cue.startswith(previous)
            and len(cue) > len(previous)
            and cue[len(previous)].isspace()
        ):
            suffix = cue[len(previous) :].strip()
            removed_characters += len(cue) - len(suffix)
            changed = True
            if suffix:
                output.append(suffix)
            previous = cue
            continue
        output.append(cue)
        previous = cue
    return output, input_characters, removed_characters, changed


def _semantic_character_count(cues: Sequence[str]) -> int:
    count = 0
    for cue in cues:
        without_markers = _NON_SPEECH_MARKER.sub("", cue)
        count += sum(not char.isspace() for char in without_markers)
    return count


def validate_subtitle_quality(
    metrics: SubtitleQualityMetrics,
    policy: SubtitleQualityPolicy = SUBTITLE_QUALITY_POLICY,
) -> None:
    if (
        metrics.raw_byte_count > policy.max_raw_bytes
        or metrics.canonical_code_points > policy.max_canonical_code_points
        or metrics.segment_count > policy.max_segments
    ):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.RESOURCE_LIMIT)
    if metrics.semantic_character_count < policy.min_semantic_characters:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.QUALITY)
    if (
        metrics.non_whitespace_character_count > 0
        and metrics.replacement_character_count
        / metrics.non_whitespace_character_count
        > policy.max_replacement_ratio
    ):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.QUALITY)
    if (
        metrics.input_character_count > 0
        and metrics.removed_character_count / metrics.input_character_count
        >= policy.max_deduplication_ratio
    ):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.QUALITY)
    if (
        metrics.raw_byte_count >= policy.compression_check_min_raw_bytes
        and metrics.canonical_byte_count / metrics.raw_byte_count
        < policy.min_compression_ratio
    ):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.QUALITY)


def _stable_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def build_raw_request_hash(
    *,
    video_id: str,
    language_preferences: Sequence[str],
    provider: str,
    provider_version: str,
    refresh_generation: int,
    selection_policy_version: str = SELECTION_POLICY_VERSION,
    format_policy_version: str = FORMAT_POLICY_VERSION,
) -> str:
    if not video_id or not provider or not provider_version:
        msg = "video_id, provider, and provider_version must be non-empty"
        raise ValueError(msg)
    if refresh_generation < 0:
        msg = "refresh_generation must be non-negative"
        raise ValueError(msg)
    normalized_languages = tuple(
        normalize_language_tag(language) for language in language_preferences
    )
    if not normalized_languages:
        msg = "language_preferences must be non-empty"
        raise ValueError(msg)
    return _stable_hash(
        {
            "format_policy_version": format_policy_version,
            "language_preferences": normalized_languages,
            "provider": provider,
            "provider_version": provider_version,
            "refresh_generation": refresh_generation,
            "selection_policy_version": selection_policy_version,
            "video_id": video_id,
        }
    )


def build_canonical_request_hash(
    *,
    source_content_hash: str,
    source_format: SubtitleFormat,
    normalization_version: str = NORMALIZATION_VERSION,
    quality_policy_version: str = QUALITY_POLICY_VERSION,
) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", source_content_hash):
        msg = "source_content_hash must be a lowercase SHA-256 digest"
        raise ValueError(msg)
    if not normalization_version or not quality_policy_version:
        msg = "normalization and quality policy versions must be non-empty"
        raise ValueError(msg)
    return _stable_hash(
        {
            "normalization_version": normalization_version,
            "quality_policy_version": quality_policy_version,
            "source_content_hash": source_content_hash,
            "source_format": source_format.value,
        }
    )


def normalize_subtitle(
    raw: bytes,
    source_format: SubtitleFormat,
) -> NormalizedSubtitle:
    if len(raw) > SUBTITLE_QUALITY_POLICY.max_raw_bytes:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.RESOURCE_LIMIT)
    invalid_utf8 = False
    try:
        decoded = raw.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        invalid_utf8 = True
        decoded = ""
    if invalid_utf8:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.INVALID_UTF8)
    decoded = decoded.replace("\r\n", "\n").replace("\r", "\n")

    if source_format is SubtitleFormat.JSON3:
        parsed = _parse_json3(decoded)
    elif source_format is SubtitleFormat.VTT:
        parsed = _parse_vtt(decoded)
    elif source_format is SubtitleFormat.SRT:
        parsed = _parse_srt(decoded)
    else:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)

    if len(parsed) > SUBTITLE_QUALITY_POLICY.max_segments:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.RESOURCE_LIMIT)
    normalized_cues = [cue for cue in (_normalize_cue(item) for item in parsed) if cue]
    (
        canonical_cues,
        input_characters,
        removed_characters,
        deduplicated,
    ) = _deduplicate_cues(normalized_cues)
    canonical = "\n".join(canonical_cues)
    if canonical:
        canonical += "\n"

    non_whitespace = sum(not char.isspace() for char in canonical)
    replacement_count = canonical.count("\ufffd")
    canonical_bytes = canonical.encode("utf-8")
    validate_subtitle_quality(
        SubtitleQualityMetrics(
            raw_byte_count=len(raw),
            canonical_code_points=len(canonical),
            segment_count=len(parsed),
            semantic_character_count=_semantic_character_count(canonical_cues),
            replacement_character_count=replacement_count,
            non_whitespace_character_count=non_whitespace,
            input_character_count=input_characters,
            removed_character_count=removed_characters,
            canonical_byte_count=len(canonical_bytes),
        )
    )

    flags: list[TranscriptQualityFlag] = []
    if deduplicated:
        flags.append(TranscriptQualityFlag.ROLLING_CUES_DEDUPED)
    if any(_SPEAKER_PREFIX.match(cue) for cue in canonical_cues):
        flags.append(TranscriptQualityFlag.SPEAKER_LABELS_PRESENT)
    if any(_NON_SPEECH_MARKER.search(cue) for cue in canonical_cues):
        flags.append(TranscriptQualityFlag.NON_SPEECH_MARKERS_PRESENT)

    return NormalizedSubtitle(
        text=canonical,
        source_content_hash=hashlib.sha256(raw).hexdigest(),
        source_byte_count=len(raw),
        content_hash=hashlib.sha256(canonical_bytes).hexdigest(),
        char_count=len(canonical),
        segment_count=len(canonical_cues),
        quality_flags=tuple(flags),
    )


@dataclass(frozen=True, slots=True)
class _SourceMetadata:
    source_type: TranscriptSourceType
    requested_language: str
    actual_language: str
    source_format: SubtitleFormat


def _service_error(
    code: ErrorCode,
    message: str,
    *,
    retryable: bool,
    video_id: str,
    retry_after_seconds: float | None = None,
) -> TranscriptError:
    return TranscriptError(
        AppError(
            code=code,
            message=message,
            retryable=retryable,
            retry_after_seconds=retry_after_seconds,
            video_id=video_id,
            stage=ProcessingStage.TRANSCRIPT,
        )
    )


def _copy_app_error(error: AppError, *, video_id: str) -> AppError:
    return AppError(
        code=error.code,
        message=error.message,
        retryable=error.retryable,
        retry_after_seconds=error.retry_after_seconds,
        run_id=error.run_id,
        job_id=error.job_id,
        video_id=error.video_id or video_id,
        stage=error.stage,
    )


def _adapter_boundary_error(
    error: AppError,
    *,
    operation: str,
    video_id: str,
) -> AppError:
    if error.code is ErrorCode.CONFIG_INVALID:
        detail = "configuration invalid"
    elif error.code is ErrorCode.PERMISSION_DENIED:
        detail = "access denied"
    elif error.code is ErrorCode.CONTENT_UNAVAILABLE:
        detail = "content unavailable"
    elif error.code is ErrorCode.RATE_LIMITED:
        detail = "rate limited"
    elif error.code is ErrorCode.TRANSIENT_NETWORK:
        detail = "network request failed"
    elif error.code is ErrorCode.PROVIDER_UNAVAILABLE:
        detail = "provider unavailable"
    elif error.code is ErrorCode.INVALID_RESPONSE:
        detail = "response invalid"
    else:
        detail = "local resource failed"
    retry_after = error.retry_after_seconds
    if (
        retry_after is not None
        and (not error.retryable or not math.isfinite(retry_after) or retry_after < 0)
    ):
        retry_after = None
    return AppError(
        code=error.code,
        message=f"subtitle adapter {detail} during {operation}",
        retryable=error.retryable,
        retry_after_seconds=retry_after,
        video_id=video_id,
        stage=ProcessingStage.TRANSCRIPT,
    )


def _unexpected_adapter_error(*, operation: str, video_id: str) -> AppError:
    return AppError(
        code=ErrorCode.PROVIDER_UNAVAILABLE,
        message=f"subtitle adapter provider unavailable during {operation}",
        retryable=True,
        video_id=video_id,
        stage=ProcessingStage.TRANSCRIPT,
    )


def _persisted_error_message_is_safe(value: str | None) -> bool:
    if (
        value is None
        or not value
        or len(value) > 500
        or value != " ".join(value.split())
    ):
        return False
    lowered = value.casefold()
    return not any(
        marker in lowered
        for marker in (
            "http://",
            "https://",
            "file://",
            "/users/",
            "/private/",
            "authorization",
            "bearer ",
            "cookie",
            "token",
            "secret",
            "api_key",
            "api-key",
        )
    )


def _aware_utc(value: datetime, *, video_id: str) -> datetime:
    if value.tzinfo is None:
        raise _service_error(
            ErrorCode.CONFIG_INVALID,
            "subtitle clock must return a timezone-aware value",
            retryable=False,
            video_id=video_id,
        )
    return value.astimezone(UTC)


def _raw_artifact_key(raw_request_hash: str) -> str:
    return f"subtitle-source:{raw_request_hash}"


def _raw_artifact_id(
    *,
    raw_request_hash: str,
    metadata: _SourceMetadata,
    source_content_hash: str,
    provider: str,
) -> str:
    provenance_hash = _stable_hash(
        {
            "actual_language": metadata.actual_language,
            "provider": provider,
            "provenance_version": "subtitle-source-provenance-v1",
            "raw_request_hash": raw_request_hash,
            "requested_language": metadata.requested_language,
            "source_content_hash": source_content_hash,
            "source_format": metadata.source_format.value,
            "source_type": metadata.source_type.value,
            "source_producer_version": _RAW_PRODUCER_VERSION,
        }
    )
    return f"subtitle-source-{provenance_hash}"


def _canonical_artifact_key(
    raw_request_hash: str,
    canonical_request_hash: str,
) -> str:
    return f"transcript-canonical:{raw_request_hash}:{canonical_request_hash}"


def _canonical_artifact_id(
    *,
    raw_artifact_id: str,
    raw_content_hash: str,
    provider: str,
    model: str | None,
    raw_request_hash: str,
    canonical_request_hash: str,
    content_hash: str,
    quality_flags: Sequence[TranscriptQualityFlag],
) -> str:
    provenance_hash = _stable_hash(
        {
            "canonical_content_hash": content_hash,
            "canonical_producer_version": _CANONICAL_PRODUCER_VERSION,
            "canonical_request_hash": canonical_request_hash,
            "model": model,
            "provider": provider,
            "provenance_version": "transcript-canonical-provenance-v1",
            "quality_flags": _encode_quality_flags(quality_flags),
            "raw_artifact_id": raw_artifact_id,
            "raw_content_hash": raw_content_hash,
            "raw_request_hash": raw_request_hash,
        }
    )
    return f"transcript-canonical-{provenance_hash}"


def _encode_source_metadata(metadata: _SourceMetadata) -> str:
    raw = json.dumps(
        [
            metadata.source_type.value,
            metadata.requested_language,
            metadata.actual_language,
            metadata.source_format.value,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_source_metadata(
    filename: str,
    *,
    video_id: str,
) -> _SourceMetadata:
    parts = filename.split(".")
    if len(parts) != 3 or parts[0] != "source":
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached subtitle source path metadata is invalid",
            retryable=False,
            video_id=video_id,
        )
    token, extension = parts[1], parts[2]
    padding = "=" * (-len(token) % 4)
    invalid = False
    decoded: Any = None
    source_type: TranscriptSourceType | None = None
    source_format: SubtitleFormat | None = None
    requested_language = ""
    actual_language = ""
    try:
        decoded = json.loads(
            base64.urlsafe_b64decode(token + padding).decode("utf-8")
        )
        if (
            not isinstance(decoded, list)
            or len(decoded) != 4
            or not all(isinstance(item, str) for item in decoded)
        ):
            raise ValueError
        source_type = TranscriptSourceType(decoded[0])
        source_format = SubtitleFormat(decoded[3])
        requested_language = decoded[1]
        actual_language = decoded[2]
    except (ValueError, UnicodeError, json.JSONDecodeError):
        invalid = True
    if invalid or source_type is None or source_format is None:
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached subtitle source path metadata is invalid",
            retryable=False,
            video_id=video_id,
        )
    if (
        source_type is TranscriptSourceType.WHISPER
        or source_format.value != extension
        or not requested_language
        or not actual_language
        or actual_language.strip() != actual_language
    ):
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached subtitle source path metadata is inconsistent",
            retryable=False,
            video_id=video_id,
        )
    return _SourceMetadata(
        source_type=source_type,
        requested_language=requested_language,
        actual_language=actual_language,
        source_format=source_format,
    )


def _validate_source_provenance(
    metadata: _SourceMetadata,
    language_preferences: Sequence[str],
    *,
    video_id: str,
) -> None:
    invalid = False
    expected_requested_language: str | None = None
    try:
        actual = normalize_language_tag(metadata.actual_language)
        for preference in language_preferences:
            requested = normalize_language_tag(preference)
            if _language_match_rank(actual, requested) is not None:
                expected_requested_language = preference
                break
    except ValueError:
        invalid = True
    if (
        invalid
        or expected_requested_language is None
        or metadata.requested_language != expected_requested_language
    ):
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached subtitle source provenance is inconsistent",
            retryable=False,
            video_id=video_id,
        )


_FLAG_TO_CODE: Final = {
    TranscriptQualityFlag.ROLLING_CUES_DEDUPED: "r",
    TranscriptQualityFlag.SPEAKER_LABELS_PRESENT: "s",
    TranscriptQualityFlag.NON_SPEECH_MARKERS_PRESENT: "n",
}
_CODE_TO_FLAG: Final = {code: flag for flag, code in _FLAG_TO_CODE.items()}


def _encode_quality_flags(flags: Sequence[TranscriptQualityFlag]) -> str:
    return "".join(_FLAG_TO_CODE[flag] for flag in flags) or "-"


def _decode_quality_flags(value: str, *, video_id: str) -> tuple[TranscriptQualityFlag, ...]:
    if value == "-":
        return ()
    invalid = False
    flags: tuple[TranscriptQualityFlag, ...] = ()
    try:
        flags = tuple(_CODE_TO_FLAG[code] for code in value)
    except KeyError:
        invalid = True
    if invalid:
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached transcript quality metadata is invalid",
            retryable=False,
            video_id=video_id,
        )
    if len(flags) != len(set(flags)):
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached transcript quality metadata is invalid",
            retryable=False,
            video_id=video_id,
        )
    return flags


def _validate_cached_quality_metadata(
    canonical_text: str,
    flags: tuple[TranscriptQualityFlag, ...],
    encoded_flags: str,
    *,
    video_id: str,
) -> None:
    canonical_cues = canonical_text.splitlines()
    speaker_expected = any(_SPEAKER_PREFIX.match(cue) for cue in canonical_cues)
    non_speech_expected = any(_NON_SPEECH_MARKER.search(cue) for cue in canonical_cues)
    has_speaker_flag = TranscriptQualityFlag.SPEAKER_LABELS_PRESENT in flags
    has_non_speech_flag = TranscriptQualityFlag.NON_SPEECH_MARKERS_PRESENT in flags
    if (
        _encode_quality_flags(flags) != encoded_flags
        or has_speaker_flag != speaker_expected
        or has_non_speech_flag != non_speech_expected
    ):
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached transcript quality metadata is inconsistent",
            retryable=False,
            video_id=video_id,
        )


def _source_relative_path(
    *,
    video_id: str,
    raw_request_hash: str,
    metadata: _SourceMetadata,
) -> str:
    token = _encode_source_metadata(metadata)
    return (
        f"transcripts/{video_id}/{raw_request_hash}/"
        f"source.{token}.{metadata.source_format.value}"
    )


def _canonical_relative_path(
    *,
    video_id: str,
    raw_request_hash: str,
    canonical_request_hash: str,
    quality_flags: Sequence[TranscriptQualityFlag],
) -> str:
    flag_code = _encode_quality_flags(quality_flags)
    return (
        f"transcripts/{video_id}/{raw_request_hash}/"
        f"canonical.{canonical_request_hash}.{flag_code}.txt"
    )


def _resolve_data_path(
    data_root: Path,
    relative_path: str,
    *,
    video_id: str,
    boundary_error_code: ErrorCode = ErrorCode.PERMISSION_DENIED,
) -> Path:
    pure = PurePosixPath(relative_path)
    if (
        not relative_path
        or "\\" in relative_path
        or pure.is_absolute()
        or ".." in pure.parts
        or not pure.parts
        or pure.parts[0] != "transcripts"
    ):
        raise _service_error(
            boundary_error_code,
            (
                "cached subtitle artifact path is inconsistent"
                if boundary_error_code is ErrorCode.LOCAL_RESOURCE
                else "subtitle artifact path is outside the DATA boundary"
            ),
            retryable=False,
            video_id=video_id,
        )
    root = data_root.resolve()
    target = (root / Path(*pure.parts)).resolve()
    if not target.is_relative_to(root):
        raise _service_error(
            boundary_error_code,
            (
                "cached subtitle artifact path is inconsistent"
                if boundary_error_code is ErrorCode.LOCAL_RESOURCE
                else "subtitle artifact path is outside the DATA boundary"
            ),
            retryable=False,
            video_id=video_id,
        )
    return target


def _read_verified_file(
    path: Path,
    *,
    expected_hash: str | None,
    max_bytes: int,
    video_id: str,
    permission_error_code: ErrorCode = ErrorCode.LOCAL_RESOURCE,
) -> tuple[bytes, str]:
    failure: TranscriptError | None = None
    chunks: list[bytes] = []
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            total = 0
            while True:
                chunk = handle.read(_FILE_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise _service_error(
                        ErrorCode.LOCAL_RESOURCE,
                        "cached subtitle artifact exceeds its resource limit",
                        retryable=False,
                        video_id=video_id,
                    )
                chunks.append(chunk)
                hasher.update(chunk)
    except FileNotFoundError:
        failure = _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached subtitle artifact is missing",
            retryable=False,
            video_id=video_id,
        )
    except PermissionError:
        failure = _service_error(
            permission_error_code,
            "subtitle artifact is not readable",
            retryable=False,
            video_id=video_id,
        )
    except OSError:
        failure = _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "subtitle artifact could not be read",
            retryable=False,
            video_id=video_id,
        )
    if failure is not None:
        raise failure
    digest = hasher.hexdigest()
    if expected_hash is not None and digest != expected_hash:
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached subtitle artifact hash does not match its index",
            retryable=False,
            video_id=video_id,
        )
    return b"".join(chunks), digest


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(
    path: Path,
    body: bytes,
    *,
    data_root: Path,
    expected_hash: str,
    max_bytes: int,
    video_id: str,
) -> None:
    if len(body) > max_bytes:
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "subtitle artifact exceeds its write limit",
            retryable=False,
            video_id=video_id,
        )
    if path.exists():
        _read_verified_file(
            path,
            expected_hash=expected_hash,
            max_bytes=max_bytes,
            video_id=video_id,
            permission_error_code=ErrorCode.PERMISSION_DENIED,
        )
        return
    temp_path: Path | None = None
    failure: TranscriptError | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        root = data_root.resolve()
        resolved_parent = path.parent.resolve()
        resolved_target = (resolved_parent / path.name).resolve()
        if (
            not resolved_parent.is_relative_to(root)
            or not resolved_target.is_relative_to(root)
        ):
            raise _service_error(
                ErrorCode.PERMISSION_DENIED,
                "subtitle artifact path escaped the DATA boundary before write",
                retryable=False,
                video_id=video_id,
            )
        path = resolved_target
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            hasher = hashlib.sha256()
            total = 0
            for offset in range(0, len(body), _FILE_CHUNK_BYTES):
                chunk = body[offset : offset + _FILE_CHUNK_BYTES]
                total += len(chunk)
                if total > max_bytes:
                    raise _service_error(
                        ErrorCode.LOCAL_RESOURCE,
                        "subtitle artifact exceeds its write limit",
                        retryable=False,
                        video_id=video_id,
                    )
                handle.write(chunk)
                hasher.update(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if hasher.hexdigest() != expected_hash:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "subtitle artifact hash changed during write",
                retryable=False,
                video_id=video_id,
            )
        os.replace(temp_path, path)
        temp_path = None
        _fsync_directory(path.parent)
    except PermissionError:
        failure = _service_error(
            ErrorCode.PERMISSION_DENIED,
            "subtitle artifact path is not writable",
            retryable=False,
            video_id=video_id,
        )
    except OSError:
        failure = _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "subtitle artifact could not be written",
            retryable=False,
            video_id=video_id,
        )
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
    if failure is not None:
        raise failure


def _normalize_recovered_raw(
    raw_body: bytes,
    source_format: SubtitleFormat,
    *,
    video_id: str,
) -> NormalizedSubtitle:
    invalid = False
    try:
        normalized = normalize_subtitle(raw_body, source_format)
    except InvalidSubtitleCandidate:
        invalid = True
        normalized = None
    if invalid or normalized is None:
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "unindexed recovered subtitle file is invalid",
            retryable=False,
            video_id=video_id,
        )
    return normalized


class SubtitleAcquisitionService:
    """Job-bound TranscriptProvider using validated files and repository semantics."""

    def __init__(
        self,
        *,
        adapter: SubtitleAdapter,
        repository: TranscriptRepository,
        data_root: Path,
        context: TranscriptJobContext,
        clock: Callable[[], datetime],
        provider_lease_seconds: float = 300.0,
    ) -> None:
        if not data_root.is_absolute():
            msg = "data_root must be an absolute resolved DATA path"
            raise ValueError(msg)
        if provider_lease_seconds <= 0:
            msg = "provider_lease_seconds must be positive"
            raise ValueError(msg)
        self._adapter = adapter
        self._repository = repository
        self._data_root = data_root
        self._context = context
        self._clock = clock
        self._provider_lease_seconds = provider_lease_seconds

    def _get_artifact(
        self,
        artifact_key: str,
        *,
        video_id: str,
    ) -> ArtifactRecord | None:
        failed = False
        record: ArtifactRecord | None = None
        try:
            record = self._repository.get_artifact_by_key(artifact_key)
        except Exception:
            failed = True
        if failed:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "subtitle artifact index could not be read",
                retryable=True,
                video_id=video_id,
            )
        return record

    def _get_provider_call(
        self,
        request_hash: str,
        *,
        video_id: str,
    ) -> ProviderCallRecord | None:
        failed = False
        record: ProviderCallRecord | None = None
        try:
            record = self._repository.get_provider_call(request_hash)
        except Exception:
            failed = True
        if failed:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "subtitle provider call state could not be read",
                retryable=True,
                video_id=video_id,
            )
        return record

    def _provider_request(self, raw_request_hash: str) -> ProviderCallRequest:
        return ProviderCallRequest(
            operation="subtitle.fetch",
            normalized_input_hash=raw_request_hash,
            provider=self._adapter.provider_name,
            model=None,
            prompt_version=SELECTION_POLICY_VERSION,
            schema_version=FORMAT_POLICY_VERSION,
            deterministic_artifact_key=_raw_artifact_key(raw_request_hash),
        )

    def _validate_cached_provider_binding(
        self,
        *,
        provider_record: ProviderCallRecord | None,
        provider_request: ProviderCallRequest,
        raw_record: ArtifactRecord,
        video_id: str,
    ) -> None:
        if (
            provider_record is None
            or provider_record.status is not ProviderCallStatus.SUCCEEDED
            or provider_record.request_hash != provider_request.request_hash
            or provider_record.operation != provider_request.operation
            or provider_record.provider != provider_request.provider
            or provider_record.model != provider_request.model
            or provider_record.prompt_version != provider_request.prompt_version
            or provider_record.schema_version != provider_request.schema_version
            or provider_record.response_artifact_id != raw_record.artifact_id
            or provider_record.reservation_owner is not None
            or provider_record.lease_until is not None
            or provider_record.finished_at is None
            or raw_record.artifact_key
            != provider_request.deterministic_artifact_key
        ):
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached subtitle source is not bound to its provider result",
                retryable=False,
                video_id=video_id,
            )

    def _enumerate_adapter_tracks(self, video_id: str) -> SubtitleTrackListing:
        listing: SubtitleTrackListing | None = None
        failure: AppError | None = None
        try:
            listing = self._adapter.enumerate_tracks(video_id)
        except TranscriptError as exc:
            failure = _adapter_boundary_error(
                exc.error,
                operation="track enumeration",
                video_id=video_id,
            )
        except Exception:
            failure = _unexpected_adapter_error(
                operation="track enumeration",
                video_id=video_id,
            )
        if failure is not None:
            raise TranscriptError(failure)
        if listing is None:
            raise TranscriptError(
                _unexpected_adapter_error(
                    operation="track enumeration",
                    video_id=video_id,
                )
            )
        return listing

    def _read_adapter_track(
        self,
        track: SubtitleTrack,
        *,
        video_id: str,
    ) -> SubtitleReadResult:
        result: SubtitleReadResult | None = None
        failure: AppError | None = None
        invalid_reason: InvalidSubtitleReason | None = None
        try:
            result = self._adapter.read_track(track)
        except InvalidSubtitleCandidate as exc:
            invalid_reason = exc.reason
        except TranscriptError as exc:
            failure = _adapter_boundary_error(
                exc.error,
                operation="body read",
                video_id=video_id,
            )
        except Exception:
            failure = _unexpected_adapter_error(
                operation="body read",
                video_id=video_id,
            )
        if invalid_reason is not None:
            raise InvalidSubtitleCandidate(invalid_reason)
        if failure is not None:
            raise TranscriptError(failure)
        if result is None:
            raise TranscriptError(
                _unexpected_adapter_error(
                    operation="body read",
                    video_id=video_id,
                )
            )
        return result

    def _recorded_terminal_result(
        self,
        record: ProviderCallRecord,
    ) -> TranscriptionRequired | None:
        if record.status is not ProviderCallStatus.FAILED_FINAL:
            return None
        reason: TranscriptionReason | None = None
        diagnostic = ""
        if (
            record.last_error_code == ErrorCode.CONTENT_UNAVAILABLE.value
            and record.last_error_message == _NO_TRACKS_MESSAGE
        ):
            reason = TranscriptionReason.NO_TRACKS
            diagnostic = "cached_no_tracks"
        elif (
            record.last_error_code == ErrorCode.CONTENT_UNAVAILABLE.value
            and record.last_error_message == _NO_MATCH_MESSAGE
        ):
            reason = TranscriptionReason.NO_MATCHING_LANGUAGE
            diagnostic = "cached_no_matching_language"
        elif (
            record.last_error_code == ErrorCode.INVALID_RESPONSE.value
            and record.last_error_message == _ALL_INVALID_MESSAGE
        ):
            reason = TranscriptionReason.ALL_CANDIDATES_INVALID
            diagnostic = "cached_all_candidates_invalid"
        if reason is None:
            return None
        finished_at = record.finished_at or record.updated_at
        return TranscriptionRequired(
            reason=reason,
            call=ProviderCallMetadata(
                provider=record.provider,
                provider_version=self._adapter.provider_version,
                started_at=record.started_at,
                finished_at=finished_at,
                diagnostics=(
                    DiagnosticEntry(
                        code=diagnostic,
                        message=diagnostic.replace("_", " "),
                    ),
                ),
            ),
            attempted_track_count=0,
        )

    def _existing_provider_outcome(
        self,
        *,
        record: ProviderCallRecord,
        raw_request_hash: str,
        language_preferences: Sequence[str],
        now: datetime,
        video_id: str,
    ) -> TranscriptFetchResult | None:
        if record.status is ProviderCallStatus.SUCCEEDED:
            cached = self._load_cached(
                video_id=video_id,
                raw_request_hash=raw_request_hash,
                language_preferences=language_preferences,
                now=now,
                provider_record=record,
            )
            if cached is not None:
                return cached
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "successful subtitle provider call has no verified artifacts",
                retryable=False,
                video_id=video_id,
            )
        terminal_result = self._recorded_terminal_result(record)
        if terminal_result is not None:
            return terminal_result
        if (
            record.status is ProviderCallStatus.PENDING
            and record.lease_until is not None
            and record.lease_until > now
        ) or (
            record.status is ProviderCallStatus.FAILED_RETRYABLE
            and record.available_at > now
        ):
            raise _service_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "subtitle provider call is already reserved or unavailable",
                retryable=True,
                video_id=video_id,
            )
        if record.status is ProviderCallStatus.FAILED_FINAL:
            code: ErrorCode | None = None
            try:
                if record.last_error_code is not None:
                    code = ErrorCode(record.last_error_code)
            except ValueError:
                code = None
            if (
                code is None
                or not _persisted_error_message_is_safe(record.last_error_message)
            ):
                raise _service_error(
                    ErrorCode.LOCAL_RESOURCE,
                    "subtitle provider terminal state is inconsistent",
                    retryable=False,
                    video_id=video_id,
                )
            raise _service_error(
                code,
                record.last_error_message or "subtitle provider call failed",
                retryable=False,
                video_id=video_id,
            )
        return None

    def _preflight_provider_call(
        self,
        *,
        request: ProviderCallRequest,
        raw_request_hash: str,
        language_preferences: Sequence[str],
        now: datetime,
        video_id: str,
    ) -> TranscriptFetchResult | None:
        record = self._get_provider_call(request.request_hash, video_id=video_id)
        if record is None:
            return None
        return self._existing_provider_outcome(
            record=record,
            raw_request_hash=raw_request_hash,
            language_preferences=language_preferences,
            now=now,
            video_id=video_id,
        )

    def _complete_cached_stage(
        self,
        *,
        video_id: str,
        now: datetime,
    ) -> None:
        failed = False
        try:
            self._repository.complete_stage(
                job_id=self._context.job_id,
                owner=self._context.owner,
                video_id=video_id,
                expected_status=PipelineStatus.METADATA_READY,
                target_status=PipelineStatus.TRANSCRIPT_READY,
                pipeline_version=self._context.pipeline_version,
                artifacts=(),
                provider_call=None,
                now=now,
            )
        except Exception:
            failed = True
        if failed:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached transcript stage could not be committed",
                retryable=True,
                video_id=video_id,
            )

    def _rebuild_canonical_from_raw(
        self,
        *,
        video_id: str,
        raw_request_hash: str,
        raw_record: ArtifactRecord,
        raw_body: bytes,
        raw_hash: str,
        metadata: _SourceMetadata,
        canonical_request_hash: str,
        now: datetime,
    ) -> TranscriptReady:
        invalid = False
        try:
            normalized = normalize_subtitle(raw_body, metadata.source_format)
        except InvalidSubtitleCandidate:
            invalid = True
            normalized = None
        if invalid or normalized is None:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached subtitle source is invalid under the current policy",
                retryable=False,
                video_id=video_id,
            )
        if (
            normalized.source_content_hash != raw_hash
            or normalized.source_byte_count != len(raw_body)
        ):
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached subtitle source normalization is inconsistent",
                retryable=False,
                video_id=video_id,
            )
        canonical_relative_path = _canonical_relative_path(
            video_id=video_id,
            raw_request_hash=raw_request_hash,
            canonical_request_hash=canonical_request_hash,
            quality_flags=normalized.quality_flags,
        )
        canonical_path = _resolve_data_path(
            self._data_root,
            canonical_relative_path,
            video_id=video_id,
        )
        _atomic_write(
            canonical_path,
            normalized.text.encode("utf-8"),
            data_root=self._data_root,
            expected_hash=normalized.content_hash,
            max_bytes=_MAX_CANONICAL_BYTES,
            video_id=video_id,
        )
        provider = raw_record.provider
        if provider is None:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached subtitle source provider metadata is missing",
                retryable=False,
                video_id=video_id,
            )
        canonical_artifact_id = _canonical_artifact_id(
            raw_artifact_id=raw_record.artifact_id,
            raw_content_hash=raw_record.content_hash,
            provider=provider,
            model=raw_record.model,
            raw_request_hash=raw_request_hash,
            canonical_request_hash=canonical_request_hash,
            content_hash=normalized.content_hash,
            quality_flags=normalized.quality_flags,
        )
        stage_persistence_failed = False
        try:
            self._repository.complete_stage(
                job_id=self._context.job_id,
                owner=self._context.owner,
                video_id=video_id,
                expected_status=PipelineStatus.METADATA_READY,
                target_status=PipelineStatus.TRANSCRIPT_READY,
                pipeline_version=self._context.pipeline_version,
                artifacts=(
                    ArtifactWrite(
                        artifact_id=canonical_artifact_id,
                        artifact_key=_canonical_artifact_key(
                            raw_request_hash,
                            canonical_request_hash,
                        ),
                        video_id=video_id,
                        job_id=self._context.job_id,
                        kind=ArtifactKind.TRANSCRIPT_CANONICAL,
                        storage_root=StorageRoot.DATA,
                        relative_path=canonical_relative_path,
                        content_hash=normalized.content_hash,
                        provider=provider,
                        model=raw_record.model,
                        producer_version=_CANONICAL_PRODUCER_VERSION,
                        retention_class=RetentionClass.LONG_LIVED,
                        expires_at=None,
                    ),
                ),
                provider_call=None,
                now=now,
            )
        except Exception:
            stage_persistence_failed = True
        if stage_persistence_failed:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "rebuilt canonical transcript stage could not be committed",
                retryable=True,
                video_id=video_id,
            )
        return TranscriptReady(
            artifact=TranscriptArtifact(
                video_id=video_id,
                language=metadata.actual_language,
                source_type=metadata.source_type,
                requested_language=metadata.requested_language,
                source_format=metadata.source_format,
                text_path=canonical_relative_path,
                timed_text_path=raw_record.relative_path,
                source_content_hash=raw_hash,
                source_byte_count=len(raw_body),
                content_hash=normalized.content_hash,
                char_count=normalized.char_count,
                segment_count=normalized.segment_count,
                normalization_version=NORMALIZATION_VERSION,
                provider=provider,
                model=raw_record.model,
                created_at=now,
                quality_flags=normalized.quality_flags,
            ),
            call=ProviderCallMetadata(
                provider=self._adapter.provider_name,
                provider_version=self._adapter.provider_version,
                started_at=now,
                finished_at=now,
                diagnostics=(
                    DiagnosticEntry(
                        code="canonical_rebuilt_from_raw",
                        message="canonical transcript rebuilt from verified source",
                    ),
                ),
            ),
        )

    def _load_cached(
        self,
        *,
        video_id: str,
        raw_request_hash: str,
        language_preferences: Sequence[str],
        now: datetime,
        provider_record: ProviderCallRecord | None,
    ) -> TranscriptReady | None:
        provider_request = self._provider_request(raw_request_hash)
        raw_record = self._get_artifact(
            _raw_artifact_key(raw_request_hash),
            video_id=video_id,
        )
        if raw_record is None:
            return None
        self._validate_cached_provider_binding(
            provider_record=provider_record,
            provider_request=provider_request,
            raw_record=raw_record,
            video_id=video_id,
        )
        if (
            raw_record.video_id != video_id
            or raw_record.kind is not ArtifactKind.SUBTITLE_SOURCE
            or raw_record.storage_root is not StorageRoot.DATA
            or raw_record.deleted_at is not None
            or raw_record.producer_version != _RAW_PRODUCER_VERSION
            or raw_record.provider != self._adapter.provider_name
            or raw_record.model is not None
        ):
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached subtitle source index is inconsistent",
                retryable=False,
                video_id=video_id,
            )
        raw_relative = PurePosixPath(raw_record.relative_path)
        expected_parent = PurePosixPath(
            "transcripts", video_id, raw_request_hash
        )
        if raw_relative.parent != expected_parent:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached subtitle source path is inconsistent",
                retryable=False,
                video_id=video_id,
            )
        metadata = _decode_source_metadata(raw_relative.name, video_id=video_id)
        if (
            _source_relative_path(
                video_id=video_id,
                raw_request_hash=raw_request_hash,
                metadata=metadata,
            )
            != raw_record.relative_path
        ):
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached subtitle source path metadata is inconsistent",
                retryable=False,
                video_id=video_id,
            )
        _validate_source_provenance(
            metadata,
            language_preferences,
            video_id=video_id,
        )
        raw_path = _resolve_data_path(
            self._data_root,
            raw_record.relative_path,
            video_id=video_id,
            boundary_error_code=ErrorCode.LOCAL_RESOURCE,
        )
        raw_body, raw_hash = _read_verified_file(
            raw_path,
            expected_hash=raw_record.content_hash,
            max_bytes=SUBTITLE_QUALITY_POLICY.max_raw_bytes,
            video_id=video_id,
        )
        expected_raw_artifact_id = _raw_artifact_id(
            raw_request_hash=raw_request_hash,
            metadata=metadata,
            source_content_hash=raw_hash,
            provider=self._adapter.provider_name,
        )
        if raw_record.artifact_id != expected_raw_artifact_id:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached subtitle source provenance is not production-bound",
                retryable=False,
                video_id=video_id,
            )
        canonical_request_hash = build_canonical_request_hash(
            source_content_hash=raw_hash,
            source_format=metadata.source_format,
            normalization_version=NORMALIZATION_VERSION,
            quality_policy_version=QUALITY_POLICY_VERSION,
        )
        canonical_record = self._get_artifact(
            _canonical_artifact_key(raw_request_hash, canonical_request_hash),
            video_id=video_id,
        )
        if canonical_record is None:
            return self._rebuild_canonical_from_raw(
                video_id=video_id,
                raw_request_hash=raw_request_hash,
                raw_record=raw_record,
                raw_body=raw_body,
                raw_hash=raw_hash,
                metadata=metadata,
                canonical_request_hash=canonical_request_hash,
                now=now,
            )
        if (
            canonical_record.video_id != video_id
            or canonical_record.artifact_key
            != _canonical_artifact_key(
                raw_request_hash,
                canonical_request_hash,
            )
            or canonical_record.kind is not ArtifactKind.TRANSCRIPT_CANONICAL
            or canonical_record.storage_root is not StorageRoot.DATA
            or canonical_record.deleted_at is not None
            or canonical_record.producer_version != _CANONICAL_PRODUCER_VERSION
            or canonical_record.provider != raw_record.provider
            or canonical_record.model != raw_record.model
        ):
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached canonical transcript index is inconsistent",
                retryable=False,
                video_id=video_id,
            )
        canonical_relative = PurePosixPath(canonical_record.relative_path)
        if canonical_relative.parent != expected_parent:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached canonical transcript path is inconsistent",
                retryable=False,
                video_id=video_id,
            )
        name_parts = canonical_relative.name.split(".")
        if (
            len(name_parts) != 4
            or name_parts[0] != "canonical"
            or name_parts[1] != canonical_request_hash
            or name_parts[3] != "txt"
        ):
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached canonical transcript path metadata is invalid",
                retryable=False,
                video_id=video_id,
            )
        quality_flags = _decode_quality_flags(name_parts[2], video_id=video_id)
        canonical_path = _resolve_data_path(
            self._data_root,
            canonical_record.relative_path,
            video_id=video_id,
            boundary_error_code=ErrorCode.LOCAL_RESOURCE,
        )
        canonical_body, canonical_hash = _read_verified_file(
            canonical_path,
            expected_hash=canonical_record.content_hash,
            max_bytes=_MAX_CANONICAL_BYTES,
            video_id=video_id,
        )
        invalid_utf8 = False
        canonical_text = ""
        try:
            canonical_text = canonical_body.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            invalid_utf8 = True
        if invalid_utf8:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached canonical transcript is not valid UTF-8",
                retryable=False,
                video_id=video_id,
            )
        if not canonical_text.endswith("\n"):
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached canonical transcript has invalid framing",
                retryable=False,
                video_id=video_id,
            )
        _validate_cached_quality_metadata(
            canonical_text,
            quality_flags,
            name_parts[2],
            video_id=video_id,
        )
        expected_canonical_artifact_id = _canonical_artifact_id(
            raw_artifact_id=raw_record.artifact_id,
            raw_content_hash=raw_record.content_hash,
            provider=raw_record.provider or "",
            model=raw_record.model,
            raw_request_hash=raw_request_hash,
            canonical_request_hash=canonical_request_hash,
            content_hash=canonical_hash,
            quality_flags=quality_flags,
        )
        if canonical_record.artifact_id != expected_canonical_artifact_id:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached transcript provenance is not production-bound",
                retryable=False,
                video_id=video_id,
            )
        artifact = TranscriptArtifact(
            video_id=video_id,
            language=metadata.actual_language,
            source_type=metadata.source_type,
            requested_language=metadata.requested_language,
            source_format=metadata.source_format,
            text_path=canonical_record.relative_path,
            timed_text_path=raw_record.relative_path,
            source_content_hash=raw_hash,
            source_byte_count=len(raw_body),
            content_hash=canonical_hash,
            char_count=len(canonical_text),
            segment_count=len(canonical_text.splitlines()),
            normalization_version=NORMALIZATION_VERSION,
            provider=canonical_record.provider or self._adapter.provider_name,
            model=canonical_record.model,
            created_at=canonical_record.created_at,
            quality_flags=quality_flags,
        )
        self._complete_cached_stage(video_id=video_id, now=now)
        return TranscriptReady(
            artifact=artifact,
            call=ProviderCallMetadata(
                provider=self._adapter.provider_name,
                provider_version=self._adapter.provider_version,
                started_at=now,
                finished_at=now,
                diagnostics=(
                    DiagnosticEntry(
                        code="cache_hit",
                        message="verified transcript artifact cache hit",
                    ),
                ),
            ),
        )

    def _reserve_provider_call(
        self,
        *,
        request: ProviderCallRequest,
        now: datetime,
        video_id: str,
    ) -> ProviderReservation:
        failed = False
        reservation: ProviderReservation | None = None
        try:
            reservation = self._repository.reserve_provider_call(
                request,
                owner=self._context.owner,
                lease_until=now + timedelta(seconds=self._provider_lease_seconds),
                available_at=now,
                now=now,
            )
        except Exception:
            failed = True
        if failed or reservation is None:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "subtitle provider call reservation failed",
                retryable=True,
                video_id=video_id,
            )
        return reservation

    def _record_provider_failure(
        self,
        *,
        request_hash: str,
        error: AppError,
        now: datetime,
        message: str | None = None,
    ) -> None:
        available_at = now
        if error.retry_after_seconds is not None:
            available_at = now + timedelta(seconds=error.retry_after_seconds)
        try:
            self._repository.fail_provider_call(
                request_hash,
                owner=self._context.owner,
                retryable=error.retryable,
                available_at=available_at,
                error_code=error.code,
                error_message=message or error.message,
                now=now,
            )
        except Exception:
            pass

    def _terminal_result(
        self,
        *,
        request_hash: str,
        reason: TranscriptionReason,
        call: ProviderCallMetadata,
        attempted_track_count: int,
        video_id: str,
        now: datetime,
    ) -> TranscriptionRequired:
        if reason is TranscriptionReason.NO_TRACKS:
            code = ErrorCode.CONTENT_UNAVAILABLE
            message = _NO_TRACKS_MESSAGE
        elif reason is TranscriptionReason.NO_MATCHING_LANGUAGE:
            code = ErrorCode.CONTENT_UNAVAILABLE
            message = _NO_MATCH_MESSAGE
        else:
            code = ErrorCode.INVALID_RESPONSE
            message = _ALL_INVALID_MESSAGE
        failure = AppError(
            code=code,
            message=message,
            retryable=False,
            video_id=video_id,
            stage=ProcessingStage.TRANSCRIPT,
        )
        self._record_provider_failure(
            request_hash=request_hash,
            error=failure,
            now=now,
            message=message,
        )
        return TranscriptionRequired(
            reason=reason,
            call=call,
            attempted_track_count=attempted_track_count,
        )

    def _fetch_reserved(
        self,
        *,
        video_id: str,
        language_preferences: Sequence[str],
        raw_request_hash: str,
        provider_request: ProviderCallRequest,
        now: datetime,
    ) -> TranscriptFetchResult:
        listing = self._enumerate_adapter_tracks(video_id)
        if not listing.tracks:
            return self._terminal_result(
                request_hash=provider_request.request_hash,
                reason=TranscriptionReason.NO_TRACKS,
                call=listing.call,
                attempted_track_count=0,
                video_id=video_id,
                now=now,
            )
        ranked = rank_subtitle_candidates(listing.tracks, language_preferences)
        if not ranked:
            return self._terminal_result(
                request_hash=provider_request.request_hash,
                reason=TranscriptionReason.NO_MATCHING_LANGUAGE,
                call=listing.call,
                attempted_track_count=0,
                video_id=video_id,
                now=now,
            )

        attempted = 0
        last_call = listing.call
        for candidate in ranked:
            attempted += 1
            metadata = _SourceMetadata(
                source_type=candidate.track.source_type,
                requested_language=candidate.requested_language,
                actual_language=candidate.track.language,
                source_format=candidate.track.source_format,
            )
            raw_relative_path = _source_relative_path(
                video_id=video_id,
                raw_request_hash=raw_request_hash,
                metadata=metadata,
            )
            raw_path = _resolve_data_path(
                self._data_root,
                raw_relative_path,
                video_id=video_id,
            )
            try:
                if raw_path.exists():
                    raw_body, _ = _read_verified_file(
                        raw_path,
                        expected_hash=None,
                        max_bytes=SUBTITLE_QUALITY_POLICY.max_raw_bytes,
                        video_id=video_id,
                        permission_error_code=ErrorCode.PERMISSION_DENIED,
                    )
                    normalized = _normalize_recovered_raw(
                        raw_body,
                        candidate.track.source_format,
                        video_id=video_id,
                    )
                else:
                    read_result = self._read_adapter_track(
                        candidate.track,
                        video_id=video_id,
                    )
                    last_call = read_result.call
                    raw_body = read_result.body
                    normalized = normalize_subtitle(
                        raw_body,
                        candidate.track.source_format,
                    )
            except InvalidSubtitleCandidate:
                continue

            canonical_request_hash = build_canonical_request_hash(
                source_content_hash=normalized.source_content_hash,
                source_format=candidate.track.source_format,
                normalization_version=NORMALIZATION_VERSION,
                quality_policy_version=QUALITY_POLICY_VERSION,
            )
            canonical_relative_path = _canonical_relative_path(
                video_id=video_id,
                raw_request_hash=raw_request_hash,
                canonical_request_hash=canonical_request_hash,
                quality_flags=normalized.quality_flags,
            )
            canonical_path = _resolve_data_path(
                self._data_root,
                canonical_relative_path,
                video_id=video_id,
            )
            canonical_body = normalized.text.encode("utf-8")
            _atomic_write(
                raw_path,
                raw_body,
                data_root=self._data_root,
                expected_hash=normalized.source_content_hash,
                max_bytes=SUBTITLE_QUALITY_POLICY.max_raw_bytes,
                video_id=video_id,
            )
            _atomic_write(
                canonical_path,
                canonical_body,
                data_root=self._data_root,
                expected_hash=normalized.content_hash,
                max_bytes=_MAX_CANONICAL_BYTES,
                video_id=video_id,
            )
            raw_artifact_id = _raw_artifact_id(
                raw_request_hash=raw_request_hash,
                metadata=metadata,
                source_content_hash=normalized.source_content_hash,
                provider=self._adapter.provider_name,
            )
            canonical_artifact_id = _canonical_artifact_id(
                raw_artifact_id=raw_artifact_id,
                raw_content_hash=normalized.source_content_hash,
                provider=self._adapter.provider_name,
                model=None,
                raw_request_hash=raw_request_hash,
                canonical_request_hash=canonical_request_hash,
                content_hash=normalized.content_hash,
                quality_flags=normalized.quality_flags,
            )
            artifacts = (
                ArtifactWrite(
                    artifact_id=raw_artifact_id,
                    artifact_key=provider_request.deterministic_artifact_key,
                    video_id=video_id,
                    job_id=self._context.job_id,
                    kind=ArtifactKind.SUBTITLE_SOURCE,
                    storage_root=StorageRoot.DATA,
                    relative_path=raw_relative_path,
                    content_hash=normalized.source_content_hash,
                    provider=self._adapter.provider_name,
                    model=None,
                    producer_version=_RAW_PRODUCER_VERSION,
                    retention_class=RetentionClass.LONG_LIVED,
                    expires_at=None,
                ),
                ArtifactWrite(
                    artifact_id=canonical_artifact_id,
                    artifact_key=_canonical_artifact_key(
                        raw_request_hash,
                        canonical_request_hash,
                    ),
                    video_id=video_id,
                    job_id=self._context.job_id,
                    kind=ArtifactKind.TRANSCRIPT_CANONICAL,
                    storage_root=StorageRoot.DATA,
                    relative_path=canonical_relative_path,
                    content_hash=normalized.content_hash,
                    provider=self._adapter.provider_name,
                    model=None,
                    producer_version=_CANONICAL_PRODUCER_VERSION,
                    retention_class=RetentionClass.LONG_LIVED,
                    expires_at=None,
                ),
            )
            stage_persistence_failed = False
            try:
                self._repository.complete_stage(
                    job_id=self._context.job_id,
                    owner=self._context.owner,
                    video_id=video_id,
                    expected_status=PipelineStatus.METADATA_READY,
                    target_status=PipelineStatus.TRANSCRIPT_READY,
                    pipeline_version=self._context.pipeline_version,
                    artifacts=artifacts,
                    provider_call=ProviderCallCompletion(
                        request_hash=provider_request.request_hash,
                        response_artifact_id=raw_artifact_id,
                        input_tokens=None,
                        output_tokens=None,
                        cost_microusd=None,
                    ),
                    now=now,
                )
            except Exception:
                stage_persistence_failed = True
            if stage_persistence_failed:
                raise _service_error(
                    ErrorCode.LOCAL_RESOURCE,
                    "subtitle files were saved but stage persistence failed",
                    retryable=True,
                    video_id=video_id,
                )
            return TranscriptReady(
                artifact=TranscriptArtifact(
                    video_id=video_id,
                    language=candidate.track.language,
                    source_type=candidate.track.source_type,
                    requested_language=candidate.requested_language,
                    source_format=candidate.track.source_format,
                    text_path=canonical_relative_path,
                    timed_text_path=raw_relative_path,
                    source_content_hash=normalized.source_content_hash,
                    source_byte_count=normalized.source_byte_count,
                    content_hash=normalized.content_hash,
                    char_count=normalized.char_count,
                    segment_count=normalized.segment_count,
                    normalization_version=NORMALIZATION_VERSION,
                    provider=self._adapter.provider_name,
                    model=None,
                    created_at=now,
                    quality_flags=normalized.quality_flags,
                ),
                call=last_call,
            )

        return self._terminal_result(
            request_hash=provider_request.request_hash,
            reason=TranscriptionReason.ALL_CANDIDATES_INVALID,
            call=last_call,
            attempted_track_count=attempted,
            video_id=video_id,
            now=now,
        )

    def fetch(
        self,
        video: VideoMetadata,
        language_preferences: Sequence[str],
    ) -> TranscriptFetchResult:
        video_id = video.video_id
        if _SAFE_VIDEO_ID.fullmatch(video_id) is None:
            raise _service_error(
                ErrorCode.INVALID_RESPONSE,
                "video_id is unsafe for transcript storage",
                retryable=False,
                video_id=video_id,
            )
        now = _aware_utc(self._clock(), video_id=video_id)
        try:
            raw_request_hash = build_raw_request_hash(
                video_id=video_id,
                language_preferences=language_preferences,
                provider=self._adapter.provider_name,
                provider_version=self._adapter.provider_version,
                refresh_generation=self._context.refresh_generation,
            )
        except ValueError:
            invalid_preferences = True
            raw_request_hash = ""
        else:
            invalid_preferences = False
        if invalid_preferences:
            raise _service_error(
                ErrorCode.CONFIG_INVALID,
                "subtitle language preferences are invalid",
                retryable=False,
                video_id=video_id,
            )
        provider_request = self._provider_request(raw_request_hash)
        existing_outcome = self._preflight_provider_call(
            request=provider_request,
            raw_request_hash=raw_request_hash,
            language_preferences=language_preferences,
            now=now,
            video_id=video_id,
        )
        if existing_outcome is not None:
            return existing_outcome
        cached = self._load_cached(
            video_id=video_id,
            raw_request_hash=raw_request_hash,
            language_preferences=language_preferences,
            now=now,
            provider_record=None,
        )
        if cached is not None:
            return cached

        reservation = self._reserve_provider_call(
            request=provider_request,
            now=now,
            video_id=video_id,
        )
        if not reservation.acquired:
            reservation_outcome = self._existing_provider_outcome(
                record=reservation.record,
                raw_request_hash=raw_request_hash,
                language_preferences=language_preferences,
                now=now,
                video_id=video_id,
            )
            if reservation_outcome is not None:
                return reservation_outcome
            raise _service_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "subtitle provider call is already reserved or unavailable",
                retryable=True,
                video_id=video_id,
            )
        owner_result: TranscriptFetchResult | None = None
        owner_failure: AppError | None = None
        try:
            owner_result = self._fetch_reserved(
                video_id=video_id,
                language_preferences=language_preferences,
                raw_request_hash=raw_request_hash,
                provider_request=provider_request,
                now=now,
            )
        except TranscriptError as exc:
            owner_failure = _copy_app_error(exc.error, video_id=video_id)
        except Exception:
            owner_failure = AppError(
                code=ErrorCode.LOCAL_RESOURCE,
                message="subtitle acquisition failed",
                retryable=True,
                video_id=video_id,
                stage=ProcessingStage.TRANSCRIPT,
            )
        if owner_failure is not None:
            self._record_provider_failure(
                request_hash=provider_request.request_hash,
                error=owner_failure,
                now=now,
            )
            raise TranscriptError(owner_failure)
        if owner_result is None:
            fallback = AppError(
                code=ErrorCode.LOCAL_RESOURCE,
                message="subtitle acquisition returned no result",
                retryable=True,
                video_id=video_id,
                stage=ProcessingStage.TRANSCRIPT,
            )
            self._record_provider_failure(
                request_hash=provider_request.request_hash,
                error=fallback,
                now=now,
            )
            raise TranscriptError(fallback)
        return owner_result


_WHISPER_OPERATION: Final = "local-whisper-transcription-v1"
_WHISPER_CANONICAL_VERSION: Final = "whisper-canonical-v1"
_MAX_WHISPER_TRANSCRIPT_BYTES: Final = 4_000_000


@runtime_checkable
class LocalWhisperAdapter(Protocol):
    """Minimum persistent-service boundary implemented by ``MlxWhisperAdapter``."""

    def transcribe(
        self,
        audio: AudioArtifact,
        *,
        audio_path: Path,
        resources: AudioResourceSnapshot,
        policy: TranscriptionPolicy | None = None,
    ) -> WhisperTranscription: ...


class LocalTranscriptionService:
    """Persist a verified MLX Whisper result as a TRANSCRIPT stage completion.

    The adapter deliberately owns only model execution and its in-memory cache.
    This service owns the durable cache, file boundary, and SQLite stage boundary.
    """

    def __init__(
        self,
        *,
        adapter: LocalWhisperAdapter,
        repository: TranscriptRepository,
        context: TranscriptJobContext,
        data_root: Path,
        resources: AudioResourceSnapshot,
        decode_policy: WhisperDecodePolicy,
        transcription_policy: TranscriptionPolicy | None = None,
        clock: Callable[[], datetime],
        provider_lease_seconds: float = 300.0,
    ) -> None:
        if not data_root.is_absolute():
            msg = "data_root must be an absolute resolved DATA path"
            raise ValueError(msg)
        if provider_lease_seconds <= 0:
            msg = "provider_lease_seconds must be positive"
            raise ValueError(msg)
        self._adapter = adapter
        self._repository = repository
        self._context = context
        self._data_root = data_root
        self._resources = resources
        self._decode_policy = decode_policy
        self._transcription_policy = transcription_policy
        self._clock = clock
        self._provider_lease_seconds = provider_lease_seconds

    def _error(
        self, code: ErrorCode, message: str, *, retryable: bool, video_id: str
    ) -> TranscriptError:
        return TranscriptError(
            AppError(
                code=code,
                message=message,
                retryable=retryable,
                video_id=video_id,
                stage=ProcessingStage.TRANSCRIPT,
            )
        )

    @property
    def _model_identity(self) -> str:
        return f"{self._decode_policy.model}@{self._decode_policy.model_revision}"

    def _request(self, audio: ArtifactRecord) -> ProviderCallRequest:
        cache_key = build_transcription_cache_key(
            audio_content_hash=audio.content_hash,
            language_hint=self._decode_policy.language_hint,
            model=self._decode_policy.model,
            model_revision=self._decode_policy.model_revision,
            parameter_policy_version=self._decode_policy.parameter_policy_version,
        )
        return ProviderCallRequest(
            operation=_WHISPER_OPERATION,
            normalized_input_hash=cache_key,
            provider="mlx-whisper",
            model=self._model_identity,
            prompt_version=self._decode_policy.parameter_policy_version,
            schema_version=_WHISPER_CANONICAL_VERSION,
            deterministic_artifact_key=f"transcript-canonical:whisper:{cache_key}",
        )

    def _validate_audio(self, audio: ArtifactRecord) -> tuple[AudioArtifact, Path]:
        video_id = audio.video_id or ""
        registered = self._repository.get_artifact_by_key(audio.artifact_key)
        if (
            not video_id
            or audio.kind is not ArtifactKind.AUDIO
            or audio.storage_root is not StorageRoot.DATA
            or audio.retention_class is not RetentionClass.EPHEMERAL_AUDIO
            or audio.deleted_at is not None
            or registered is None
            or registered != audio
        ):
            raise self._error(
                ErrorCode.LOCAL_RESOURCE,
                "local transcription audio artifact is not eligible",
                retryable=False,
                video_id=video_id,
            )
        relative = PurePosixPath(audio.relative_path)
        if (
            not audio.relative_path
            or "\\" in audio.relative_path
            or relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
        ):
            raise self._error(
                ErrorCode.PERMISSION_DENIED,
                "local transcription audio path is outside the DATA boundary",
                retryable=False,
                video_id=video_id,
            )
        try:
            root = self._data_root.resolve(strict=True)
            candidate = root.joinpath(*relative.parts)
            current = candidate
            while current != root:
                if current.is_symlink():
                    raise ValueError
                current = current.parent
            if candidate.is_dir():
                raise ValueError
            path = candidate.resolve(strict=True)
            if not path.is_relative_to(root):
                raise ValueError
            body, digest = _read_verified_file(
                path,
                expected_hash=audio.content_hash,
                max_bytes=(
                    self._transcription_policy.max_audio_bytes
                    if self._transcription_policy is not None
                    else 2_000_000_000
                ),
                video_id=video_id,
            )
        except ValueError:
            raise self._error(
                ErrorCode.PERMISSION_DENIED,
                "local transcription audio path is outside the DATA boundary",
                retryable=False,
                video_id=video_id,
            ) from None
        except TranscriptError as error:
            raise self._error(
                error.error.code,
                "local transcription audio file is not verified",
                retryable=False,
                video_id=video_id,
            ) from None
        if digest != audio.content_hash or len(body) == 0:
            raise self._error(
                ErrorCode.LOCAL_RESOURCE,
                "local transcription audio file is not verified",
                retryable=False,
                video_id=video_id,
            )
        return (
            AudioArtifact(
                artifact_id=audio.artifact_id,
                video_id=video_id,
                relative_path=audio.relative_path,
                content_hash=audio.content_hash,
                byte_count=len(body),
                duration_seconds=0,
            ),
            path,
        )

    def _validate_stage_context(self, video_id: str) -> None:
        job = self._repository.get_job(self._context.job_id)
        video = self._repository.get_video(video_id)
        if (
            job is None
            or video is None
            or job.video_id != video_id
            or job.target_stage is not ProcessingStage.TRANSCRIPT
            or job.pipeline_version != self._context.pipeline_version
            or job.status is not JobStatus.RUNNING
            or job.lease_owner != self._context.owner
            or video.pipeline_status is not PipelineStatus.METADATA_READY
            or video.pipeline_version != self._context.pipeline_version
        ):
            raise self._error(
                ErrorCode.LOCAL_RESOURCE,
                "local transcription stage context is invalid",
                retryable=True,
                video_id=video_id,
            )

    def _relative_path(self, video_id: str, request: ProviderCallRequest) -> str:
        return f"transcripts/{video_id}/{request.request_hash}/canonical.whisper.txt"

    def _managed_transcript_path(self, relative_path: str, *, video_id: str) -> Path:
        """Reject every existing symlink before reading or writing a transcript."""
        _resolve_data_path(self._data_root, relative_path, video_id=video_id)
        try:
            root = self._data_root.resolve(strict=True)
            candidate = root.joinpath(*PurePosixPath(relative_path).parts)
            current = candidate
            while current != root:
                if current.is_symlink():
                    raise ValueError
                current = current.parent
            if candidate.exists() and candidate.is_dir():
                raise ValueError
        except (OSError, ValueError):
            raise self._error(
                ErrorCode.PERMISSION_DENIED,
                "local transcription artifact path is outside the DATA boundary",
                retryable=False,
                video_id=video_id,
            ) from None
        return candidate

    @staticmethod
    def _producer_version(language: str) -> str:
        token = base64.urlsafe_b64encode(language.encode("utf-8")).rstrip(b"=").decode("ascii")
        return f"{_WHISPER_CANONICAL_VERSION}.{token}"

    @staticmethod
    def _language_from_producer_version(value: str, *, video_id: str) -> str:
        prefix = f"{_WHISPER_CANONICAL_VERSION}."
        try:
            token = value.removeprefix(prefix)
            language = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode("utf-8")
        except UnicodeError:
            language = ""
        if not value.startswith(prefix) or not language or language.strip() != language:
            raise TranscriptError(AppError(code=ErrorCode.LOCAL_RESOURCE, message="persisted local transcription cache is invalid", retryable=False, video_id=video_id, stage=ProcessingStage.TRANSCRIPT))
        return language

    def _artifact(
        self, *, video_id: str, request: ProviderCallRequest, body: bytes, language: str
    ) -> ArtifactWrite:
        producer_version = self._producer_version(language)
        return ArtifactWrite(
            artifact_id=f"whisper-canonical-{_stable_hash({'request_hash': request.request_hash, 'content_hash': hashlib.sha256(body).hexdigest(), 'producer_version': producer_version})}",
            artifact_key=request.deterministic_artifact_key,
            video_id=video_id,
            job_id=self._context.job_id,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=self._relative_path(video_id, request),
            content_hash=hashlib.sha256(body).hexdigest(),
            provider=request.provider,
            model=request.model,
            producer_version=producer_version,
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        )

    def _cached_artifact(self, *, video_id: str, request: ProviderCallRequest) -> tuple[ArtifactRecord, bytes, str]:
        provider_call = self._repository.get_provider_call(request.request_hash)
        artifact = self._repository.get_artifact_by_key(request.deterministic_artifact_key)
        if (
            provider_call is None
            or provider_call.request_hash != request.request_hash
            or provider_call.operation != request.operation
            or provider_call.provider != request.provider
            or provider_call.model != request.model
            or provider_call.prompt_version != request.prompt_version
            or provider_call.schema_version != request.schema_version
            or provider_call.status is not ProviderCallStatus.SUCCEEDED
            or artifact is None
            or provider_call.response_artifact_id != artifact.artifact_id
            or artifact.video_id != video_id
            or artifact.kind is not ArtifactKind.TRANSCRIPT_CANONICAL
            or artifact.storage_root is not StorageRoot.DATA
            or artifact.relative_path != self._relative_path(video_id, request)
            or artifact.provider != request.provider
            or artifact.model != request.model
            or artifact.retention_class is not RetentionClass.LONG_LIVED
            or artifact.expires_at is not None
            or artifact.deleted_at is not None
        ):
            raise self._error(
                ErrorCode.LOCAL_RESOURCE,
                "persisted local transcription cache is invalid",
                retryable=False,
                video_id=video_id,
            )
        language = self._language_from_producer_version(artifact.producer_version, video_id=video_id)
        path = self._managed_transcript_path(
            artifact.relative_path, video_id=video_id
        )
        body, _ = _read_verified_file(
            path,
            expected_hash=artifact.content_hash,
            max_bytes=_MAX_WHISPER_TRANSCRIPT_BYTES,
            video_id=video_id,
        )
        return artifact, body, language

    def _ready(
        self,
        artifact: ArtifactRecord | ArtifactWrite,
        *,
        source_audio: AudioArtifact,
        body: bytes,
        language: str,
        now: datetime,
        cache_hit: bool,
    ) -> TranscriptReady:
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            raise self._error(ErrorCode.LOCAL_RESOURCE, "persisted local transcription cache is invalid", retryable=False, video_id=source_audio.video_id) from None
        return TranscriptReady(
            artifact=TranscriptArtifact(
                video_id=artifact.video_id or "",
                language=language,
                source_type=TranscriptSourceType.WHISPER,
                requested_language=None,
                source_format=None,
                text_path=artifact.relative_path,
                timed_text_path=None,
                source_content_hash=source_audio.content_hash,
                source_byte_count=source_audio.byte_count,
                content_hash=artifact.content_hash,
                char_count=len(text.rstrip("\n")),
                segment_count=len(text.rstrip("\n").splitlines()),
                normalization_version=_WHISPER_CANONICAL_VERSION,
                provider=artifact.provider or "mlx-whisper",
                model=artifact.model,
                created_at=now,
            ),
            call=ProviderCallMetadata(
                provider="mlx-whisper",
                model=self._model_identity,
                started_at=now,
                finished_at=now,
                diagnostics=(
                    (DiagnosticEntry(code="PERSISTED_CACHE_HIT", message="reused persisted local transcription"),)
                    if cache_hit
                    else ()
                ),
            ),
        )

    def _complete_cached(self, *, video_id: str, now: datetime) -> None:
        try:
            self._repository.complete_stage(
                job_id=self._context.job_id,
                owner=self._context.owner,
                video_id=video_id,
                expected_status=PipelineStatus.METADATA_READY,
                target_status=PipelineStatus.TRANSCRIPT_READY,
                pipeline_version=self._context.pipeline_version,
                artifacts=(),
                provider_call=None,
                now=now,
            )
        except Exception as error:
            raise self._error(ErrorCode.LOCAL_RESOURCE, "cached local transcription stage could not be committed", retryable=True, video_id=video_id) from error

    def transcribe(self, audio: ArtifactRecord) -> TranscriptReady:
        now = _aware_utc(self._clock(), video_id=audio.video_id or "")
        verified_audio, audio_path = self._validate_audio(audio)
        self._validate_stage_context(verified_audio.video_id)
        request = self._request(audio)
        existing = self._repository.get_provider_call(request.request_hash)
        if existing is not None and existing.status is ProviderCallStatus.SUCCEEDED:
            cached_artifact, body, language = self._cached_artifact(video_id=verified_audio.video_id, request=request)
            self._complete_cached(video_id=verified_audio.video_id, now=now)
            return self._ready(cached_artifact, source_audio=verified_audio, body=body, language=language, now=now, cache_hit=True)
        reservation = self._repository.reserve_provider_call(
            request,
            owner=self._context.owner,
            lease_until=now + timedelta(seconds=self._provider_lease_seconds),
            available_at=now,
            now=now,
        )
        if not reservation.acquired:
            if reservation.record.status is ProviderCallStatus.SUCCEEDED:
                cached_artifact, body, language = self._cached_artifact(video_id=verified_audio.video_id, request=request)
                self._complete_cached(video_id=verified_audio.video_id, now=now)
                return self._ready(cached_artifact, source_audio=verified_audio, body=body, language=language, now=now, cache_hit=True)
            raise self._error(ErrorCode.PROVIDER_UNAVAILABLE, "local transcription provider call is already reserved", retryable=True, video_id=verified_audio.video_id)
        written_path: Path | None = None
        try:
            result = self._adapter.transcribe(
                verified_audio,
                audio_path=audio_path,
                resources=self._resources,
                policy=self._transcription_policy,
            )
            text = unicodedata.normalize("NFC", result.text).replace("\r\n", "\n").replace("\r", "\n").strip()
            if not text:
                raise self._error(ErrorCode.INVALID_RESPONSE, "local Whisper response is invalid", retryable=False, video_id=verified_audio.video_id)
            body = (text + "\n").encode("utf-8")
            language = normalize_language_tag(result.language)
            artifact = self._artifact(video_id=verified_audio.video_id, request=request, body=body, language=language)
            target = self._managed_transcript_path(
                artifact.relative_path, video_id=verified_audio.video_id
            )
            if not target.exists():
                written_path = target
            _atomic_write(target, body, data_root=self._data_root, expected_hash=artifact.content_hash, max_bytes=_MAX_WHISPER_TRANSCRIPT_BYTES, video_id=verified_audio.video_id)
            self._repository.complete_stage(
                job_id=self._context.job_id,
                owner=self._context.owner,
                video_id=verified_audio.video_id,
                expected_status=PipelineStatus.METADATA_READY,
                target_status=PipelineStatus.TRANSCRIPT_READY,
                pipeline_version=self._context.pipeline_version,
                artifacts=(artifact,),
                provider_call=ProviderCallCompletion(
                    request_hash=request.request_hash,
                    response_artifact_id=artifact.artifact_id,
                    input_tokens=None,
                    output_tokens=None,
                    cost_microusd=None,
                ),
                now=now,
            )
        except WhisperAdapterError as error:
            failure = error.error
        except TranscriptError as error:
            failure = error.error
        except Exception:
            failure = AppError(code=ErrorCode.LOCAL_RESOURCE, message="local transcription stage persistence failed", retryable=True, video_id=verified_audio.video_id, stage=ProcessingStage.TRANSCRIPT)
        else:
            cleanup_successful_audio(audio, data_root=self._data_root, repository=self._repository, now=now)
            return self._ready(artifact, source_audio=verified_audio, body=body, language=language, now=now, cache_hit=False)
        if written_path is not None:
            try:
                written_path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            self._repository.fail_provider_call(
                request.request_hash,
                owner=self._context.owner,
                retryable=failure.retryable,
                available_at=now,
                error_code=failure.code,
                error_message="local transcription stage failed",
                now=now,
            )
        except Exception:
            pass
        raise TranscriptError(failure)


__all__ = [
    "FORMAT_POLICY_VERSION",
    "InvalidSubtitleCandidate",
    "InvalidSubtitleReason",
    "LocalWhisperAdapter",
    "NORMALIZATION_VERSION",
    "NormalizedSubtitle",
    "QUALITY_POLICY_VERSION",
    "RankedSubtitleCandidate",
    "SELECTION_POLICY_VERSION",
    "SUBTITLE_QUALITY_POLICY",
    "SubtitleQualityMetrics",
    "SubtitleQualityPolicy",
    "SubtitleReadResult",
    "SubtitleAdapter",
    "SubtitleAcquisitionService",
    "LocalTranscriptionService",
    "SubtitleTrack",
    "SubtitleTrackListing",
    "TranscriptJobContext",
    "TranscriptError",
    "TranscriptRepository",
    "build_canonical_request_hash",
    "build_raw_request_hash",
    "normalize_language_tag",
    "normalize_subtitle",
    "rank_subtitle_candidates",
    "validate_subtitle_quality",
]
