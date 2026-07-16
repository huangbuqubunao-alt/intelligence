"""Deterministic subtitle selection, normalization, quality, and cache policy."""

from __future__ import annotations

import base64
import hashlib
import html
import json
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
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactWrite,
    ProviderCallCompletion,
    ProviderCallRecord,
    ProviderCallRequest,
    ProviderCallStatus,
    ProviderReservation,
    RetentionClass,
    StageCompletionResult,
    StorageRoot,
    VerifiedArtifact,
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
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED) from exc
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
        lines = [line.rstrip() for line in block.splitlines()]
        if not lines:
            continue
        control = lines[0].strip().upper()
        if control.startswith(("STYLE", "REGION", "NOTE")):
            continue
        timestamp_index = 0
        if not _VTT_TIMESTAMP.fullmatch(lines[0].strip()):
            timestamp_index = 1
        if (
            timestamp_index >= len(lines)
            or not _VTT_TIMESTAMP.fullmatch(lines[timestamp_index].strip())
            or timestamp_index + 1 >= len(lines)
        ):
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
        cues.append("\n".join(lines[timestamp_index + 1 :]))
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


def _normalize_cue(value: str) -> str:
    cue = html.unescape(value)
    voice = _VOICE_TAG.search(cue)
    speaker = voice.group(1).strip() if voice and voice.group(1) else None
    cue = _VOICE_TAG.sub("", cue)
    cue = re.sub(r"</v>", "", cue, flags=re.IGNORECASE)
    cue = _INLINE_VTT_TIMESTAMP.sub("", cue)
    cue = _STYLE_TAG.sub("", cue)
    cue = _ASS_STYLE.sub("", cue)
    cue = unicodedata.normalize("NFC", cue)
    cue = " ".join(cue.split())
    if speaker and cue:
        cue = f"{speaker}: {cue}"
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
    try:
        decoded = raw.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.INVALID_UTF8) from exc
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


def _canonical_artifact_key(
    raw_request_hash: str,
    canonical_request_hash: str,
) -> str:
    return f"transcript-canonical:{raw_request_hash}:{canonical_request_hash}"


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
    try:
        decoded: Any = json.loads(
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
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached subtitle source path metadata is invalid",
            retryable=False,
            video_id=video_id,
        ) from None
    if (
        source_type is TranscriptSourceType.WHISPER
        or source_format.value != extension
        or not requested_language
        or not actual_language
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
    try:
        flags = tuple(_CODE_TO_FLAG[code] for code in value)
    except KeyError:
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached transcript quality metadata is invalid",
            retryable=False,
            video_id=video_id,
        ) from None
    if len(flags) != len(set(flags)):
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached transcript quality metadata is invalid",
            retryable=False,
            video_id=video_id,
        )
    return flags


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
            ErrorCode.PERMISSION_DENIED,
            "subtitle artifact path is outside the DATA boundary",
            retryable=False,
            video_id=video_id,
        )
    root = data_root.resolve()
    target = (root / Path(*pure.parts)).resolve()
    if not target.is_relative_to(root):
        raise _service_error(
            ErrorCode.PERMISSION_DENIED,
            "subtitle artifact path is outside the DATA boundary",
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
) -> tuple[bytes, str]:
    try:
        with path.open("rb") as handle:
            chunks: list[bytes] = []
            hasher = hashlib.sha256()
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
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "cached subtitle artifact is missing",
            retryable=False,
            video_id=video_id,
        ) from None
    except PermissionError:
        raise _service_error(
            ErrorCode.PERMISSION_DENIED,
            "subtitle artifact is not readable",
            retryable=False,
            video_id=video_id,
        ) from None
    except OSError:
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "subtitle artifact could not be read",
            retryable=False,
            video_id=video_id,
        ) from None
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
        )
        return
    temp_path: Path | None = None
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
    except TranscriptError:
        raise
    except PermissionError:
        raise _service_error(
            ErrorCode.PERMISSION_DENIED,
            "subtitle artifact path is not writable",
            retryable=False,
            video_id=video_id,
        ) from None
    except OSError:
        raise _service_error(
            ErrorCode.LOCAL_RESOURCE,
            "subtitle artifact could not be written",
            retryable=False,
            video_id=video_id,
        ) from None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


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
        try:
            return self._repository.get_artifact_by_key(artifact_key)
        except Exception:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "subtitle artifact index could not be read",
                retryable=True,
                video_id=video_id,
            ) from None

    def _complete_cached_stage(
        self,
        *,
        video_id: str,
        now: datetime,
    ) -> None:
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
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached transcript stage could not be committed",
                retryable=True,
                video_id=video_id,
            ) from None

    def _load_cached(
        self,
        *,
        video_id: str,
        raw_request_hash: str,
        now: datetime,
    ) -> TranscriptReady | None:
        raw_record = self._get_artifact(
            _raw_artifact_key(raw_request_hash),
            video_id=video_id,
        )
        if raw_record is None:
            return None
        if (
            raw_record.video_id != video_id
            or raw_record.kind is not ArtifactKind.SUBTITLE_SOURCE
            or raw_record.storage_root is not StorageRoot.DATA
            or raw_record.deleted_at is not None
            or raw_record.producer_version != _RAW_PRODUCER_VERSION
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
        raw_path = _resolve_data_path(
            self._data_root,
            raw_record.relative_path,
            video_id=video_id,
        )
        raw_body, raw_hash = _read_verified_file(
            raw_path,
            expected_hash=raw_record.content_hash,
            max_bytes=SUBTITLE_QUALITY_POLICY.max_raw_bytes,
            video_id=video_id,
        )
        canonical_request_hash = build_canonical_request_hash(
            source_content_hash=raw_hash,
            source_format=metadata.source_format,
        )
        canonical_record = self._get_artifact(
            _canonical_artifact_key(raw_request_hash, canonical_request_hash),
            video_id=video_id,
        )
        if canonical_record is None:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached canonical transcript index is missing",
                retryable=False,
                video_id=video_id,
            )
        if (
            canonical_record.video_id != video_id
            or canonical_record.kind is not ArtifactKind.TRANSCRIPT_CANONICAL
            or canonical_record.storage_root is not StorageRoot.DATA
            or canonical_record.deleted_at is not None
            or canonical_record.producer_version != _CANONICAL_PRODUCER_VERSION
            or canonical_record.job_id != raw_record.job_id
            or canonical_record.provider != raw_record.provider
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
        )
        canonical_body, canonical_hash = _read_verified_file(
            canonical_path,
            expected_hash=canonical_record.content_hash,
            max_bytes=_MAX_CANONICAL_BYTES,
            video_id=video_id,
        )
        try:
            canonical_text = canonical_body.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached canonical transcript is not valid UTF-8",
                retryable=False,
                video_id=video_id,
            ) from None
        if not canonical_text.endswith("\n"):
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "cached canonical transcript has invalid framing",
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
            provider=raw_record.provider or self._adapter.provider_name,
            model=raw_record.model,
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
        try:
            return self._repository.reserve_provider_call(
                request,
                owner=self._context.owner,
                lease_until=now + timedelta(seconds=self._provider_lease_seconds),
                available_at=now,
                now=now,
            )
        except Exception:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "subtitle provider call reservation failed",
                retryable=True,
                video_id=video_id,
            ) from None

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
            raise _service_error(
                ErrorCode.CONFIG_INVALID,
                "subtitle language preferences are invalid",
                retryable=False,
                video_id=video_id,
            ) from None
        cached = self._load_cached(
            video_id=video_id,
            raw_request_hash=raw_request_hash,
            now=now,
        )
        if cached is not None:
            return cached

        listing = self._adapter.enumerate_tracks(video_id)
        if not listing.tracks:
            return TranscriptionRequired(
                reason=TranscriptionReason.NO_TRACKS,
                call=listing.call,
                attempted_track_count=0,
            )
        ranked = rank_subtitle_candidates(listing.tracks, language_preferences)
        if not ranked:
            return TranscriptionRequired(
                reason=TranscriptionReason.NO_MATCHING_LANGUAGE,
                call=listing.call,
                attempted_track_count=0,
            )

        raw_key = _raw_artifact_key(raw_request_hash)
        provider_request = ProviderCallRequest(
            operation="subtitle.fetch",
            normalized_input_hash=raw_request_hash,
            provider=self._adapter.provider_name,
            model=None,
            prompt_version=SELECTION_POLICY_VERSION,
            schema_version=FORMAT_POLICY_VERSION,
            deterministic_artifact_key=raw_key,
        )
        reservation = self._reserve_provider_call(
            request=provider_request,
            now=now,
            video_id=video_id,
        )
        if not reservation.acquired:
            if reservation.record.status is ProviderCallStatus.SUCCEEDED:
                cached = self._load_cached(
                    video_id=video_id,
                    raw_request_hash=raw_request_hash,
                    now=now,
                )
                if cached is not None:
                    return cached
                raise _service_error(
                    ErrorCode.LOCAL_RESOURCE,
                    "successful subtitle provider call has no verified artifacts",
                    retryable=False,
                    video_id=video_id,
                )
            raise _service_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "subtitle provider call is already reserved or unavailable",
                retryable=True,
                video_id=video_id,
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
                    )
                    try:
                        normalized = normalize_subtitle(
                            raw_body,
                            candidate.track.source_format,
                        )
                    except InvalidSubtitleCandidate:
                        raise _service_error(
                            ErrorCode.LOCAL_RESOURCE,
                            "unindexed recovered subtitle file is invalid",
                            retryable=False,
                            video_id=video_id,
                        ) from None
                else:
                    read_result = self._adapter.read_track(candidate.track)
                    last_call = read_result.call
                    raw_body = read_result.body
                    normalized = normalize_subtitle(
                        raw_body,
                        candidate.track.source_format,
                    )
            except InvalidSubtitleCandidate:
                continue
            except TranscriptError as exc:
                self._record_provider_failure(
                    request_hash=provider_request.request_hash,
                    error=exc.error,
                    now=now,
                )
                raise

            canonical_request_hash = build_canonical_request_hash(
                source_content_hash=normalized.source_content_hash,
                source_format=candidate.track.source_format,
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
            raw_artifact_id = f"subtitle-source-{raw_request_hash}"
            canonical_artifact_id = (
                f"transcript-canonical-{raw_request_hash}-{canonical_request_hash}"
            )
            artifacts = (
                ArtifactWrite(
                    artifact_id=raw_artifact_id,
                    artifact_key=raw_key,
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
                raise _service_error(
                    ErrorCode.LOCAL_RESOURCE,
                    "subtitle files were saved but stage persistence failed",
                    retryable=True,
                    video_id=video_id,
                ) from None
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

        failure = AppError(
            code=ErrorCode.INVALID_RESPONSE,
            message="all subtitle candidates invalid",
            retryable=False,
            video_id=video_id,
            stage=ProcessingStage.TRANSCRIPT,
        )
        self._record_provider_failure(
            request_hash=provider_request.request_hash,
            error=failure,
            now=now,
            message="all subtitle candidates invalid",
        )
        return TranscriptionRequired(
            reason=TranscriptionReason.ALL_CANDIDATES_INVALID,
            call=last_call,
            attempted_track_count=attempted,
        )


__all__ = [
    "FORMAT_POLICY_VERSION",
    "InvalidSubtitleCandidate",
    "InvalidSubtitleReason",
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
