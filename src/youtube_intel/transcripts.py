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
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    JobRecord,
    ProviderCallCompletion,
    ProviderCallRecord,
    ProviderCallRequest,
    ProviderCallStatus,
    ProviderReservation,
    RetentionClass,
    StageCompletionResult,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VerifiedArtifact,
    VideoRecord,
    build_evidence_id,
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
SELECTION_POLICY_VERSION: Final = "subtitle-selection-v2-original-tracks"
FORMAT_POLICY_VERSION: Final = "subtitle-format-v2-native-timing"
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
    timed_cues: tuple[CanonicalTimedCue, ...] = ()


@dataclass(frozen=True, slots=True)
class CanonicalTimedCue:
    """One immutable, cue-granular canonical transcript interval."""

    start_ms: int
    end_ms: int
    text: str

    def __post_init__(self) -> None:
        if self.start_ms < 0 or self.end_ms <= self.start_ms or not self.text:
            raise ValueError("canonical timed cue is invalid")


@dataclass(frozen=True, slots=True)
class _SourceTimedCue:
    start_ms: int
    end_ms: int
    text: str


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
class CaptionRepairContext:
    source_run_id: str
    expected_canonical_artifact_id: str


@dataclass(frozen=True, slots=True)
class TranscriptJobContext:
    job_id: str
    owner: str
    pipeline_version: str
    refresh_generation: int = 0
    repair: CaptionRepairContext | None = None

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
    def bind_source_storage(self, root: Path) -> None: ...

    def get_artifact_by_key(self, artifact_key: str) -> ArtifactRecord | None: ...

    def get_job(self, job_id: str) -> JobRecord | None: ...

    def get_video(self, video_id: str) -> VideoRecord | None: ...

    def register_subtitle_source_capture(
        self, *, artifact: ArtifactWrite, body: bytes, context: TranscriptJobContext,
        provider_request: ProviderCallRequest, language_preferences: Sequence[str],
        provider_version: str, data_root: Path, now: datetime,
    ) -> ArtifactRecord: ...

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

    def create_timed_transcript(
        self, timed: TimedTranscriptWrite, *, now: datetime
    ) -> TimedTranscriptWrite: ...


def normalize_language_tag(value: str) -> str:
    normalized = value.strip().replace("_", "-").casefold()
    if not normalized:
        msg = "language tags must be non-empty"
        raise ValueError(msg)
    return normalized


def _original_transcript_evidence_writes(
    timed: TimedTranscriptWrite, language: str,
) -> tuple[tuple[EvidenceWrite, EvidenceTextBindingWrite], ...]:
    writes = []
    first = 0
    while first < len(timed.cues):
        last = first + 1
        excerpt_chars = len(timed.cues[first].text)
        while (
            last < len(timed.cues)
            and excerpt_chars + 1 + len(timed.cues[last].text) <= 800
        ):
            excerpt_chars += 1 + len(timed.cues[last].text)
            last += 1
        cues = timed.cues[first:last]
        excerpt = "\n".join(cue.text for cue in cues)
        start_ms = cues[0].start_ms
        end_ms = cues[-1].end_ms
        evidence_id = build_evidence_id(
            video_id=timed.video_id,
            artifact_id=timed.canonical_artifact_id,
            start_ms=start_ms,
            end_ms=end_ms,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
        )
        evidence = EvidenceWrite(
            evidence_id=evidence_id,
            video_id=timed.video_id,
            artifact_id=timed.canonical_artifact_id,
            start_ms=start_ms,
            end_ms=end_ms,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language=language,
            availability=EvidenceAvailability.AVAILABLE,
        )
        writes.append((evidence, EvidenceTextBindingWrite.from_timed_transcript(
            evidence=evidence, timed_transcript_id=timed.timed_transcript_id,
            start_cue_index=first, end_cue_index=last, excerpt=excerpt,
        )))
        first = last
    return tuple(writes)


def _persist_original_transcript_evidence(
    repository: object, *, timed: TimedTranscriptWrite, language: str, now: datetime,
) -> None:
    """Bind bounded, contiguous Evidence spans to the canonical timed transcript."""
    create = getattr(repository, "create_evidence_with_text_binding", None)
    get_evidence = getattr(repository, "get_evidence", None)
    resolve_text = getattr(repository, "resolve_verified_evidence_text", None)
    if not (callable(create) and callable(get_evidence) and callable(resolve_text)):
        return
    for evidence, binding in _original_transcript_evidence_writes(timed, language):
        existing = get_evidence(evidence.evidence_id)
        if existing is None:
            create(
                evidence,
                binding,
                now=now,
            )
        elif (
            existing.video_id != evidence.video_id
            or existing.artifact_id != evidence.artifact_id
            or existing.start_ms != evidence.start_ms
            or existing.end_ms != evidence.end_ms
            or existing.language != evidence.language
            or (verified := resolve_text(evidence.evidence_id)) is None
            or verified.excerpt != binding.excerpt
        ):
            raise ValueError("existing transcript Evidence conflicts with canonical cues")


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


def _timestamp_ms(value: str) -> int:
    token = value.replace(",", ".")
    fields = token.split(":")
    if len(fields) == 2:
        hours = "0"
        minutes, seconds = fields
    elif len(fields) == 3:
        hours, minutes, seconds = fields
    else:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
    try:
        whole_seconds, milliseconds = seconds.split(".")
        result = ((int(hours) * 60 + int(minutes)) * 60 + int(whole_seconds)) * 1000 + int(milliseconds)
    except (TypeError, ValueError):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED) from None
    if result < 0:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
    return result


def _timed_vtt_or_srt_cues(text: str, *, source_format: SubtitleFormat) -> list[_SourceTimedCue]:
    blocks = re.split(r"\n{2,}", text.strip("\n"))
    if source_format is SubtitleFormat.VTT:
        if not blocks or not blocks[0].splitlines() or not blocks[0].splitlines()[0].strip().startswith("WEBVTT"):
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
        blocks = blocks[1:]
        timestamp_pattern = _VTT_TIMESTAMP
    else:
        timestamp_pattern = _SRT_TIMESTAMP
    result: list[_SourceTimedCue] = []
    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines()]
        if not lines or (source_format is SubtitleFormat.VTT and _is_vtt_control_block(lines[0])):
            continue
        index = 0
        if not timestamp_pattern.fullmatch(lines[0].strip()):
            index = 1
        if index >= len(lines) or not timestamp_pattern.fullmatch(lines[index].strip()) or index + 1 >= len(lines):
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
        start_text, end_text = lines[index].split("-->", 1)
        start_ms = _timestamp_ms(start_text.strip())
        end_ms = _timestamp_ms(end_text.strip().split()[0])
        if end_ms <= start_ms:
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
        result.append(_SourceTimedCue(start_ms=start_ms, end_ms=end_ms, text="\n".join(lines[index + 1 :])))
    return result


def _timed_json3_cues(text: str) -> list[_SourceTimedCue]:
    try:
        payload: Any = json.loads(text)
        events = payload["events"]
    except (KeyError, TypeError, json.JSONDecodeError):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED) from None
    if not isinstance(events, list):
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
    result: list[_SourceTimedCue] = []
    for event in events:
        if not isinstance(event, dict) or event.get("segs") is None:
            continue
        segments = event.get("segs")
        start_ms = event.get("tStartMs")
        duration_ms = event.get("dDurationMs")
        if not isinstance(segments, list) or not isinstance(start_ms, int) or not isinstance(duration_ms, int) or start_ms < 0 or duration_ms <= 0:
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
        pieces: list[str] = []
        for segment in segments:
            if not isinstance(segment, dict) or not isinstance(segment.get("utf8"), str):
                raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
            pieces.append(str(segment["utf8"]))
        value = "".join(pieces)
        if value.strip():
            result.append(_SourceTimedCue(start_ms=start_ms, end_ms=start_ms + duration_ms, text=value))
    return result


def _canonicalize_timed_cues(cues: Sequence[_SourceTimedCue]) -> tuple[CanonicalTimedCue, ...]:
    output: list[CanonicalTimedCue] = []
    previous: str | None = None
    previous_end = -1
    for source in cues:
        normalized = _normalize_cue(source.text)
        if not normalized:
            continue
        if source.start_ms < previous_end:
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
        if previous is not None and normalized == previous:
            previous = normalized
            continue
        text = normalized
        if previous is not None and normalized.startswith(previous) and len(normalized) > len(previous) and normalized[len(previous)].isspace():
            text = normalized[len(previous) :].strip()
        if text:
            output.append(CanonicalTimedCue(source.start_ms, source.end_ms, text))
            previous_end = source.end_ms
        previous = normalized
    return tuple(output)


def normalize_timed_subtitle(raw: bytes, source_format: SubtitleFormat) -> NormalizedSubtitle:
    """Preserve source timing while proving its text projection equals v1 plain text."""
    normalized = normalize_subtitle(raw, source_format)
    try:
        decoded = raw.decode("utf-8-sig", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.INVALID_UTF8) from None
    try:
        if source_format is SubtitleFormat.JSON3:
            source_cues = _timed_json3_cues(decoded)
        elif source_format in {SubtitleFormat.VTT, SubtitleFormat.SRT}:
            source_cues = _timed_vtt_or_srt_cues(decoded, source_format=source_format)
        else:
            raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
    except InvalidSubtitleCandidate:
        # Historical/current accepted subtitle payloads may lack source timing.
        # They retain their existing plain-text contract, explicitly unbound.
        return normalized
    try:
        timed_cues = _canonicalize_timed_cues(source_cues)
    except InvalidSubtitleCandidate:
        return normalized
    projection = "\n".join(cue.text for cue in timed_cues)
    if projection:
        projection += "\n"
    if not timed_cues or projection != normalized.text:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.MALFORMED)
    return NormalizedSubtitle(
        text=normalized.text, source_content_hash=normalized.source_content_hash,
        source_byte_count=normalized.source_byte_count, content_hash=normalized.content_hash,
        char_count=normalized.char_count, segment_count=normalized.segment_count,
        quality_flags=normalized.quality_flags, timed_cues=timed_cues,
    )


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


# Frozen recovery inputs are deliberately independent of mutable user settings.
_RETAINED_LANGUAGES: Final = (("en",), ("zh", "en"))
# Exact historical adapter strings; never normalize or consult mutable installs.
_RETAINED_PROVIDER_VERSIONS: Final = ("2026.7.4", "2026.07.04")
_RETAINED_PROOF_VERSION: Final = "failed-caption-derivation-v1"


def _retention_require(condition: object) -> None:
    if not condition:
        raise ValueError("failed caption derivation has no complete deterministic proof")


def _retention_utc(value: object) -> datetime:
    _retention_require(isinstance(value, str))
    assert isinstance(value, str)
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _retention_require(stamp.tzinfo is not None and stamp.utcoffset() == timedelta(0))
    return stamp


def _retained_execution(
    connection: Any, job: Any, call: Any, run: Any, *, now: datetime, failed: bool = False,
) -> dict[str, Any]:
    """Prove and snapshot every original or successor execution field."""
    from youtube_intel.source_run import (
        _SOURCE_RUN_STATE_TRANSITIONS,
        SourceRunState,
        SourceRunTrigger,
        build_source_run_id,
        build_source_run_idempotency_key,
    )

    _retention_require(
        job["status"] == ("FAILED_FINAL" if failed else "SUCCEEDED") and job["job_type"] == "VIDEO_STAGE"
        and job["target_stage"] == "TRANSCRIPT"
        and type(job["attempt_count"]) is int and type(job["max_attempts"]) is int
        and 0 < job["attempt_count"] <= job["max_attempts"]
        and all(job[k] is None for k in (
            "lease_owner", "lease_until",
            "authoritative_scoring_artifact_key", "scoring_success_provenance", "scoring_lineage_version"))
    )
    _retention_require((job["last_error_code"], job["last_error_message"]) == (
        ("LOCAL_RESOURCE", "Caption repair needs attention") if failed else (None, None)))
    created, finished = _retention_utc(job["created_at"]), _retention_utc(job["finished_at"])
    _retention_require(created <= _retention_utc(job["available_at"]) <= finished <= now
        and finished == _retention_utc(job["updated_at"]))
    attempts = connection.execute(
        "SELECT * FROM job_attempts WHERE job_id=? ORDER BY attempt_number LIMIT 1001",
        (job["job_id"],),
    ).fetchall()
    _retention_require(len(attempts) == job["attempt_count"] <= 1000)
    prior_finish = created
    for number, attempt in enumerate(attempts, 1):
        _retention_require(type(attempt["attempt_id"]) is int and attempt["attempt_id"] > 0
            and type(attempt["attempt_number"]) is int and attempt["attempt_number"] == number
            and attempt["job_id"] == job["job_id"]
            and isinstance(attempt["lease_owner"], str) and bool(attempt["lease_owner"].strip()))
        start, end = _retention_utc(attempt["started_at"]), _retention_utc(attempt["finished_at"])
        _retention_require(prior_finish <= start <= end <= finished
            and end < _retention_utc(attempt["lease_until"]))
        if number == len(attempts):
            _retention_require(attempt["outcome"] == ("FAILED_FINAL" if failed else "SUCCEEDED") and end == finished
                and attempt["error_code"] == job["last_error_code"] and attempt["error_message"] == job["last_error_message"]
                and _retention_utc(job["available_at"]) <= start)
        else:
            _retention_require(attempt["outcome"] == "RETRY_PENDING"
                and attempt["error_code"] in {code.value for code in ErrorCode}
                and isinstance(attempt["error_message"], str) and bool(attempt["error_message"].strip()))
        prior_finish = end
    _retention_require(call["status"] == ("FAILED_RETRYABLE" if failed else "SUCCEEDED")
        and type(call["attempt_count"]) is int and 0 < call["attempt_count"] <= len(attempts)
        and all(call[k] is None for k in (
            "reservation_owner", "lease_until", "input_tokens", "output_tokens",
            "cost_microusd"))
        and call["response_artifact_id"] == (None if failed else call["raw_id"])
        and connection.execute("SELECT 1 FROM provider_dispatch_states WHERE request_hash=?",
                               (call["request_hash"],)).fetchone() is None)
    if failed:
        _retention_require(call["finished_at"] is None
            and (call["last_error_code"], call["last_error_message"]) == (
                "LOCAL_RESOURCE", "subtitle files were saved but stage persistence failed")
            and created <= _retention_utc(call["started_at"]) <= _retention_utc(call["updated_at"]) <= finished
            and _retention_utc(call["updated_at"]) <= _retention_utc(call["available_at"]))
    else:
        _retention_require(call["last_error_code"] is None and call["last_error_message"] is None
            and created <= _retention_utc(call["started_at"])
            <= _retention_utc(call["finished_at"]) <= finished
            and _retention_utc(call["finished_at"]) == _retention_utc(call["updated_at"])
            and created <= _retention_utc(call["available_at"]) <= _retention_utc(call["finished_at"]))
    trigger = SourceRunTrigger.MANUAL_CHECK_NOW
    terminal = SourceRunState.NEEDS_ATTENTION if failed else SourceRunState.COMPLETED
    attention = "EXECUTION_CONDITION_UNRESOLVED" if failed else None
    _retention_require(run["trigger"] == trigger.value and run["state"] == terminal.value
        and run["priority"] == "P0" and run["attention_reason"] == attention
        and run["automation_run_id"] is None and run["manual_analyze_override_id"] is None
        and run["trigger_reference"] == run["manual_command_id"]
        and run["run_id"] == build_source_run_id(source_id=run["source_id"], trigger=trigger,
                                                 trigger_reference=run["manual_command_id"])
        and run["idempotency_key"] == build_source_run_idempotency_key(
            source_id=run["source_id"], trigger=trigger, trigger_reference=run["manual_command_id"]))
    run_created, run_finished = _retention_utc(run["created_at"]), _retention_utc(run["updated_at"])
    _retention_require(run_created <= created <= finished <= run_finished <= now)
    events = connection.execute(
        "SELECT * FROM source_run_state_events WHERE run_id=? ORDER BY event_id LIMIT 1001",
        (run["run_id"],),
    ).fetchall()
    _retention_require(0 < len(events) <= 1000)
    prior_state: SourceRunState | None = None
    prior_time = run_created
    for index, event in enumerate(events):
        current = SourceRunState(event["state"])
        occurred = _retention_utc(event["occurred_at"])
        _retention_require(type(event["event_id"]) is int and event["event_id"] > 0
            and event["run_id"] == run["run_id"] and event["attention_reason"] == (attention if index == len(events) - 1 else None)
            and prior_time <= occurred <= run_finished)
        if index == 0:
            _retention_require(event["prior_state"] is None and current is SourceRunState.QUEUED
                and occurred == run_created)
        else:
            _retention_require(prior_state is not None and event["prior_state"] == prior_state.value
                and current in _SOURCE_RUN_STATE_TRANSITIONS[prior_state])
        prior_state, prior_time = current, occurred
    _retention_require(prior_state is terminal and prior_time == run_finished)
    return {"job": dict(job), "provider_call": {k: call[k] for k in call.keys() if k != "raw_id"},
            "attempts": [dict(a) for a in attempts], "source_run": dict(run),
            "source_run_events": [dict(e) for e in events]}


def _retained_caption_proof(
    repository: Any, connection: Any, data_root: Path, ledger: dict[str, Any],
    *, now: datetime, successor: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Recompute a failed child's bounded neutral proof, without fetching input.

    With a successor binding this verifies retained history, independently of
    future current pointers. Admission additionally verifies current authority.
    """
    from youtube_intel.domain import AnalysisPoint, AnalysisResult, PointKind
    from youtube_intel.research_contract import digest
    from youtube_intel.source_authority import read_managed

    _retention_require(
        ledger["operation"] == "subtitle.fetch" and ledger["provider"] == "yt-dlp"
        and ledger["model"] is None and ledger["status"] == "FAILED_RETRYABLE"
        and ledger["prompt_version"] == SELECTION_POLICY_VERSION
        and ledger["schema_version"] == FORMAT_POLICY_VERSION
        and ledger["last_error_code"] == "LOCAL_RESOURCE"
        and ledger["last_error_message"] == "subtitle files were saved but stage persistence failed"
        and type(ledger["attempt_count"]) is int and ledger["attempt_count"] > 0
        and all(ledger[k] is None for k in (
            "reservation_owner", "lease_until", "response_artifact_id", "finished_at",
            "input_tokens", "output_tokens", "cost_microusd"))
        and re.fullmatch(r"[a-f0-9]{64}", ledger["request_hash"]) is not None
        and connection.execute("SELECT 1 FROM provider_dispatch_states WHERE request_hash=?",
                               (ledger["request_hash"],)).fetchone() is None
    )
    _retention_require(_retention_utc(ledger["started_at"]) <= _retention_utc(ledger["updated_at"]) <= now
                       and _retention_utc(ledger["available_at"]) >= _retention_utc(ledger["updated_at"]))
    captures = connection.execute(
        "SELECT * FROM artifacts WHERE artifact_key LIKE 'subtitle-source-capture:%' "
        "AND job_id LIKE 'caption-repair-%' AND provider='yt-dlp' AND deleted_at IS NULL "
        "ORDER BY artifact_id LIMIT 10001").fetchall()
    _retention_require(len(captures) <= 10000)
    candidates = []
    for capture in captures:
        pieces = str(capture["artifact_key"]).split(":")
        if len(pieces) != 3:
            continue
        raw_hash = pieces[1]
        request = ProviderCallRequest(operation="subtitle.fetch", normalized_input_hash=raw_hash,
            provider="yt-dlp", model=None, prompt_version=SELECTION_POLICY_VERSION,
            schema_version=FORMAT_POLICY_VERSION, deterministic_artifact_key=_raw_artifact_key(raw_hash))
        if request.request_hash != ledger["request_hash"]:
            continue
        video_id, job_id = str(capture["video_id"]), str(capture["job_id"])
        runs = connection.execute(
            "SELECT r.* FROM source_runs r JOIN source_video_links l USING(source_id) "
            "JOIN source_subscriptions s USING(source_id) WHERE l.video_id=? AND s.video_id=? "
            "AND s.source_type='VIDEO_URL' AND s.processing_policy='DISCOVER_ONLY' "
            "AND r.trigger='MANUAL_CHECK_NOW' AND r.manual_command_id IS NOT NULL "
            "AND r.manual_command_id NOT LIKE 'following-auto:%' LIMIT 1001", (video_id,video_id)).fetchall()
        _retention_require(len(runs) <= 1000)
        matched_runs = [r for r in runs if job_id == "caption-repair-" + hashlib.sha256(
            f"{r['run_id']}:{video_id}".encode()).hexdigest()]
        _retention_require(len(matched_runs) == 1)
        run = matched_runs[0]
        identity = job_id.removeprefix("caption-repair-")
        refresh = int(identity[:15], 16)
        input_matches = [(p, version) for p in _RETAINED_LANGUAGES
                         for version in _RETAINED_PROVIDER_VERSIONS if build_raw_request_hash(
            video_id=video_id, language_preferences=p, provider="yt-dlp",
            provider_version=version, refresh_generation=refresh) == raw_hash]
        _retention_require(len(input_matches) == 1)
        languages, provider_version = input_matches[0]
        metadata = _decode_source_metadata(PurePosixPath(capture["relative_path"]).name, video_id=video_id)
        raw = read_managed(data_root, capture["relative_path"], maximum=SUBTITLE_QUALITY_POLICY.max_raw_bytes)
        expected = _capture_artifact_write(raw_request_hash=raw_hash, metadata=metadata,
            content_hash=hashlib.sha256(raw).hexdigest(), provider="yt-dlp",
            provider_version=provider_version, video_id=video_id,
            context=TranscriptJobContext(job_id=job_id, owner="proof-only", pipeline_version="proof-only", refresh_generation=refresh))
        _retention_require(all(capture[k] == getattr(expected,k) for k in (
            "artifact_id", "artifact_key", "video_id", "job_id", "relative_path", "content_hash", "provider", "model", "producer_version"))
            and capture["kind"] == ArtifactKind.SUBTITLE_SOURCE.value and capture["storage_root"] == "DATA"
            and capture["retention_class"] == "LONG_LIVED" and capture["expires_at"] is None)
        normalized = normalize_timed_subtitle(raw, metadata.source_format)
        if not normalized.timed_cues:
            continue  # A plain capture is retained by its existing Artifact.
        canonical_hash = build_canonical_request_hash(source_content_hash=normalized.source_content_hash,
            source_format=metadata.source_format)
        relative = _canonical_relative_path(video_id=video_id, raw_request_hash=raw_hash,
            canonical_request_hash=canonical_hash, quality_flags=normalized.quality_flags)
        body = read_managed(data_root, relative, maximum=_MAX_CANONICAL_BYTES)
        _retention_require(body == normalized.text.encode("utf-8")
            and (successor is not None or connection.execute("SELECT 1 FROM artifacts WHERE relative_path=?", (relative,)).fetchone() is None))
        job = connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        attempts = connection.execute("SELECT * FROM job_attempts WHERE job_id=? ORDER BY attempt_number", (job_id,)).fetchall()
        _retention_require(job is not None and job["status"] == "FAILED_FINAL"
            and job["video_id"] == video_id and job["scope_key"] == f"video:{video_id}:TRANSCRIPT"
            and job["job_type"] == "VIDEO_STAGE" and job["target_stage"] == "TRANSCRIPT"
            and job["lease_owner"] is None and job["lease_until"] is None
            and type(job["attempt_count"]) is int and job["attempt_count"] == len(attempts) > 0
            and run["state"] == "NEEDS_ATTENTION")
        started, finished = _retention_utc(job["created_at"]), _retention_utc(job["finished_at"])
        _retention_require(started <= _retention_utc(capture["created_at"]) <= finished <= now
            and started <= _retention_utc(ledger["started_at"]) <= _retention_utc(ledger["updated_at"]) <= finished
            and _retention_utc(job["updated_at"]) == finished)
        for number, attempt in enumerate(attempts, 1):
            _retention_require(type(attempt["attempt_number"]) is int and attempt["attempt_number"] == number
                and attempt["outcome"] in {"FAILED_FINAL", "RETRY_PENDING"}
                and started <= _retention_utc(attempt["started_at"]) <= _retention_utc(attempt["finished_at"]) <= finished
                and _retention_utc(attempt["lease_until"]) >= _retention_utc(attempt["started_at"]))
        parents = connection.execute(
            "SELECT a.artifact_id FROM artifacts a JOIN jobs j USING(job_id) "
            "WHERE a.video_id=? AND a.kind='transcript_canonical' AND j.status='SUCCEEDED' "
            "AND j.created_at<? AND j.scope_key=? AND j.pipeline_version=? AND a.deleted_at IS NULL",
            (video_id,job["created_at"],job["scope_key"],job["pipeline_version"])).fetchall()
        _retention_require(len(parents) == 1)
        same_job_captures = [c for c in captures if c["job_id"] == job_id]
        _retention_require(1 <= len(same_job_captures) <= 2
            and all(str(c["artifact_key"]).split(":")[1] == raw_hash for c in same_job_captures))
        parent = connection.execute("SELECT * FROM artifacts WHERE artifact_id=?",(parents[0][0],)).fetchone()
        parent_raws = connection.execute("SELECT a.* FROM artifacts a JOIN provider_calls p ON p.response_artifact_id=a.artifact_id WHERE a.job_id=? AND a.video_id=? AND a.kind='subtitle_source' AND p.status='SUCCEEDED' AND p.provider='yt-dlp' AND a.deleted_at IS NULL",(parent["job_id"],video_id)).fetchall()
        _retention_require(len(parent_raws)==1)
        parent_raw = parent_raws[0]
        parent_call = connection.execute("SELECT * FROM provider_calls WHERE response_artifact_id=? AND status='SUCCEEDED'",(parent_raw["artifact_id"],)).fetchall()
        _retention_require(len(parent_call)==1 and parent_raw["model"] is None and parent["model"] is None)
        parent_metadata = _decode_source_metadata(PurePosixPath(parent_raw["relative_path"]).name,video_id=video_id)
        parent_body = read_managed(data_root,parent_raw["relative_path"],maximum=SUBTITLE_QUALITY_POLICY.max_raw_bytes)
        parent_normalized = normalize_timed_subtitle(parent_body,parent_metadata.source_format)
        _retention_require(not parent_normalized.timed_cues
            and hashlib.sha256(parent_body).hexdigest()==parent_raw["content_hash"]
            and read_managed(data_root,parent["relative_path"],maximum=_MAX_CANONICAL_BYTES)==parent_normalized.text.encode()
            and parent["content_hash"]==parent_normalized.content_hash
            and metadata.source_type is parent_metadata.source_type
            and normalize_language_tag(metadata.actual_language)==normalize_language_tag(parent_metadata.actual_language))
        parent_hash = str(parent_raw["artifact_key"]).removeprefix("subtitle-source:")
        parent_canonical_hash = build_canonical_request_hash(source_content_hash=parent_raw["content_hash"],source_format=parent_metadata.source_format)
        _retention_require(parent_raw["artifact_id"]==_raw_artifact_id(raw_request_hash=parent_hash,metadata=parent_metadata,source_content_hash=parent_raw["content_hash"],provider="yt-dlp",source_producer_version=parent_raw["producer_version"])
            and parent["artifact_id"]==_canonical_artifact_id(raw_artifact_id=parent_raw["artifact_id"],raw_content_hash=parent_raw["content_hash"],provider="yt-dlp",model=None,raw_request_hash=parent_hash,canonical_request_hash=parent_canonical_hash,content_hash=parent["content_hash"],quality_flags=parent_normalized.quality_flags)
            and parent["producer_version"]==_CANONICAL_PRODUCER_VERSION
            and parent_call[0]["operation"]=="subtitle.fetch" and parent_call[0]["model"] is None
            and parent_raw["producer_version"]==f"{parent_call[0]['prompt_version']}+{parent_call[0]['schema_version']}"
            and (parent_call[0]["prompt_version"],parent_call[0]["schema_version"]) in {
                (SELECTION_POLICY_VERSION,FORMAT_POLICY_VERSION),("subtitle-selection-v1","subtitle-format-v1"),
                ("subtitle-selection-v2-original-tracks","subtitle-format-v1")})
        parent_request = ProviderCallRequest(operation="subtitle.fetch",normalized_input_hash=parent_hash,
            provider="yt-dlp",model=None,prompt_version=parent_call[0]["prompt_version"],schema_version=parent_call[0]["schema_version"],
            deterministic_artifact_key=_raw_artifact_key(parent_hash))
        _retention_require(parent_request.request_hash==parent_call[0]["request_hash"])
        _validate_source_provenance(metadata,languages,video_id=video_id)
        candidates.append((capture,run,job,attempts,languages,provider_version,raw_hash,metadata,normalized,canonical_hash,relative,body,parents[0][0]))
    _retention_require(len(candidates) == 1)
    capture,run,job,attempts,languages,provider_version,raw_hash,metadata,normalized,canonical_hash,relative,body,parent_id = candidates[0]
    original_execution = _retained_execution(connection, job, ledger, run, now=now, failed=True)
    video_id = str(capture["video_id"])
    video = connection.execute("SELECT * FROM videos WHERE video_id=?",(video_id,)).fetchone()
    _retention_require(video is not None and video["provider"]=="YOUTUBE" and video["pipeline_version"]==job["pipeline_version"])
    admitting = successor is None
    if successor is None:
        timed = repository._get_verified_timed_transcript_in_transaction(connection, video_id)
        pointer = connection.execute("SELECT * FROM current_content_summaries WHERE video_id=?",(video_id,)).fetchone()
        _retention_require(timed is not None and pointer is not None and pointer["analysis_artifact_id"] is not None)
        successor = {"canonical": timed.canonical_artifact_id, "summary": str(pointer["analysis_artifact_id"])}
    canonical = connection.execute("SELECT * FROM artifacts WHERE artifact_id=?",(successor["canonical"],)).fetchone()
    summary = connection.execute("SELECT * FROM artifacts WHERE artifact_id=?",(successor["summary"],)).fetchone()
    _retention_require(canonical is not None and summary is not None
        and canonical["video_id"] == video_id and canonical["kind"] == ArtifactKind.TRANSCRIPT_CANONICAL.value
        and canonical["provider"] == "yt-dlp" and canonical["producer_version"] == _CANONICAL_PRODUCER_VERSION
        and canonical["deleted_at"] is None and summary["video_id"] == video_id
        and summary["kind"] == ArtifactKind.ANALYSIS_STRUCTURED.value and summary["provider"] == "extractive-source"
        and summary["producer_version"] == "extractive-summary-v2" and summary["deleted_at"] is None)
    successor_job = connection.execute("SELECT * FROM jobs WHERE job_id=?", (canonical["job_id"],)).fetchone()
    _retention_require(successor_job is not None and successor_job["status"] == "SUCCEEDED"
        and successor_job["video_id"] == video_id and successor_job["scope_key"] == job["scope_key"]
        and successor_job["pipeline_version"] == job["pipeline_version"] and successor_job["job_id"] != job["job_id"]
        and _retention_utc(successor_job["created_at"]) >= _retention_utc(job["finished_at"])
        and _retention_utc(successor_job["finished_at"]) <= now)
    calls = connection.execute(
        "SELECT p.*,a.artifact_id AS raw_id FROM provider_calls p JOIN artifacts a ON p.response_artifact_id=a.artifact_id "
        "WHERE a.job_id=? AND a.video_id=? AND a.kind='subtitle_source' AND a.deleted_at IS NULL "
        "AND p.status='SUCCEEDED' AND p.operation='subtitle.fetch' AND p.provider='yt-dlp' AND p.model IS NULL "
        "AND p.prompt_version=? AND p.schema_version=?",(successor_job["job_id"],video_id,SELECTION_POLICY_VERSION,FORMAT_POLICY_VERSION)).fetchall()
    _retention_require(len(calls)==1)
    successor_call = calls[0]
    successor_runs = connection.execute("SELECT * FROM source_runs WHERE source_id=? AND trigger='MANUAL_CHECK_NOW' AND manual_command_id IS NOT NULL AND manual_command_id NOT LIKE 'following-auto:%' LIMIT 1001",(run["source_id"],)).fetchall()
    _retention_require(len(successor_runs) <= 1000)
    matched_successors = [r for r in successor_runs if successor_job["job_id"] == "caption-repair-" + hashlib.sha256(f"{r['run_id']}:{video_id}".encode()).hexdigest()]
    _retention_require(len(matched_successors) == 1)
    successor_execution = _retained_execution(
        connection, successor_job, successor_call, matched_successors[0], now=now)
    successor_raw = connection.execute("SELECT * FROM artifacts WHERE artifact_id=?",(successor_call["raw_id"],)).fetchone()
    successor_raw_hash = str(successor_raw["artifact_key"]).removeprefix("subtitle-source:")
    successor_refresh = int(str(successor_job["job_id"]).removeprefix("caption-repair-")[:15],16)
    _retention_require(build_raw_request_hash(video_id=video_id,language_preferences=languages,
        provider="yt-dlp",provider_version=provider_version,refresh_generation=successor_refresh)==successor_raw_hash
        and successor_raw["producer_version"]==_RAW_PRODUCER_VERSION and successor_raw["provider"]=="yt-dlp" and successor_raw["model"] is None)
    successor_metadata = _decode_source_metadata(PurePosixPath(successor_raw["relative_path"]).name,video_id=video_id)
    successor_body = read_managed(data_root,successor_raw["relative_path"],maximum=SUBTITLE_QUALITY_POLICY.max_raw_bytes)
    successor_normalized = normalize_timed_subtitle(successor_body,successor_metadata.source_format)
    successor_canonical_hash = build_canonical_request_hash(source_content_hash=successor_normalized.source_content_hash,source_format=successor_metadata.source_format)
    successor_request = ProviderCallRequest(operation="subtitle.fetch",normalized_input_hash=successor_raw_hash,
        provider="yt-dlp",model=None,prompt_version=SELECTION_POLICY_VERSION,schema_version=FORMAT_POLICY_VERSION,
        deterministic_artifact_key=_raw_artifact_key(successor_raw_hash))
    _retention_require(successor_normalized.timed_cues and successor_request.request_hash==successor_call["request_hash"]
        and successor_normalized.source_content_hash==successor_raw["content_hash"]
        and successor_raw["artifact_id"]==_raw_artifact_id(raw_request_hash=successor_raw_hash,metadata=successor_metadata,source_content_hash=successor_normalized.source_content_hash,provider="yt-dlp")
        and canonical["artifact_id"]==_canonical_artifact_id(raw_artifact_id=successor_raw["artifact_id"],raw_content_hash=successor_raw["content_hash"],provider="yt-dlp",model=None,raw_request_hash=successor_raw_hash,canonical_request_hash=successor_canonical_hash,content_hash=successor_normalized.content_hash,quality_flags=successor_normalized.quality_flags)
        and read_managed(data_root,canonical["relative_path"],maximum=_MAX_CANONICAL_BYTES)==successor_normalized.text.encode()
        and canonical["content_hash"]==successor_normalized.content_hash
        and successor_metadata.source_type is metadata.source_type and successor_metadata.actual_language==metadata.actual_language)
    expected_timed = TimedTranscriptWrite.from_cues(video_id=video_id,canonical_artifact_id=canonical["artifact_id"],
        cues=tuple(TimedTranscriptCueWrite(start_ms=c.start_ms,end_ms=c.end_ms,text=c.text) for c in successor_normalized.timed_cues))
    _retention_require(type(successor_call["attempt_count"]) is int and successor_call["attempt_count"]>0
        and _retention_utc(successor_call["started_at"]) <= _retention_utc(successor_call["updated_at"]) <= now
        and _retention_utc(successor_call["finished_at"]) <= now
        and all(successor_call[k] is None for k in ("reservation_owner","lease_until","input_tokens","output_tokens","cost_microusd")))
    summary_body = read_managed(data_root,summary["relative_path"],maximum=1_000_000)
    _retention_require(hashlib.sha256(summary_body).hexdigest()==summary["content_hash"])
    result = AnalysisResult.model_validate_json(summary_body)
    _retention_require(result.provider == "extractive-source" and result.model == "deterministic-excerpts-v2"
        and summary["artifact_id"] == f"summary/{result.request_hash}/structured")
    evidence = connection.execute("SELECT * FROM evidence WHERE artifact_id=? AND lineage_kind='ORIGINAL_TRANSCRIPT' ORDER BY start_ms,evidence_id",(canonical["artifact_id"],)).fetchall()
    expected_evidence = _original_transcript_evidence_writes(expected_timed,successor_metadata.actual_language)
    _retention_require({e["evidence_id"] for e in evidence}=={e.evidence_id for e,_ in expected_evidence})
    for e,b in expected_evidence:
        binding = connection.execute("SELECT * FROM evidence_text_bindings WHERE evidence_id=?",(e.evidence_id,)).fetchone()
        _retention_require(binding is not None and binding["timed_transcript_id"]==b.timed_transcript_id
            and binding["start_cue_index"]==b.start_cue_index and binding["end_cue_index"]==b.end_cue_index
            and binding["excerpt"]==b.excerpt and binding["excerpt_hash"]==b.excerpt_hash
            and binding["timed_transcript_hash"]==expected_timed.timed_transcript_hash)
    for row in evidence:
        verified = repository._resolve_verified_evidence_text_in_transaction(connection,str(row["evidence_id"]))
        _retention_require(verified is not None and verified.video_id == video_id)
    for item in result.evidence:
        verified = repository._resolve_verified_evidence_text_in_transaction(connection,item.evidence_id)
        _retention_require(verified is not None and verified.video_id == video_id and verified.excerpt == item.excerpt)
        row = connection.execute("SELECT artifact_id FROM evidence WHERE evidence_id=?",(item.evidence_id,)).fetchone()
        _retention_require(row is not None and row[0] == canonical["artifact_id"])
    expected_result = AnalysisResult(provider="extractive-source",model="deterministic-excerpts-v2",prompt_version="analysis-prompt-v6",
        request_hash=digest({"contract":"extractive-summary-v2","content_id":video_id,"evidence":[e.model_dump(mode="json") for e in result.evidence]}),
        one_sentence_summary=result.evidence[0].excerpt[:500],core_points=tuple(AnalysisPoint(text=e.excerpt,kind=PointKind.FACT,evidence_ids=(e.evidence_id,)) for e in result.evidence),
        keywords=("source excerpts",),evidence=result.evidence)
    _retention_require(result==expected_result)
    if admitting:
        from youtube_intel.extractive_summary import ExtractiveSummaryService
        _retention_require(ExtractiveSummaryService(repository,data_root).read(video_id,str(summary["artifact_id"])).result==result)
    archive = dict(proof_version=_RETAINED_PROOF_VERSION, request_hash=ledger["request_hash"],
        job_id=job["job_id"], source_run_id=run["run_id"], source_id=run["source_id"], video_id=video_id,
        raw_capture_artifact_id=capture["artifact_id"],raw_sha256=normalized.source_content_hash,
        relative_path=relative,derived_sha256=hashlib.sha256(body).hexdigest(),size_bytes=len(body),
        normalization_version=NORMALIZATION_VERSION,quality_profile_version=QUALITY_POLICY_VERSION,
        canonical_request_hash=canonical_hash,successor_job_id=successor_job["job_id"],
        successor_request_hash=successor_call["request_hash"],successor_canonical_artifact_id=canonical["artifact_id"],
        successor_summary_artifact_id=summary["artifact_id"],reason="COMPLETION_PERSISTENCE_FAILED_WITH_VERIFIED_SUCCESSOR",
        created_at=now.isoformat(timespec="microseconds").replace("+00:00","Z"))
    archive["archive_id"] = _stable_hash({"proof_version":_RETAINED_PROOF_VERSION,"request_hash":ledger["request_hash"],"relative_path":relative})
    payload = {"archive":archive,"input":{"language_preferences":languages,"provider_version":provider_version,
        "refresh_generation":int(str(job["job_id"]).removeprefix("caption-repair-")[:15],16),
        "raw_request_hash":raw_hash,"source_metadata":_encode_source_metadata(metadata),
        "quality_flags":_encode_quality_flags(normalized.quality_flags),"parent_canonical_artifact_id":parent_id},
        "original_ledger":ledger,"attempts":[dict(a) for a in attempts],
        "successor_execution":successor_execution,"original_execution":original_execution,
        "evidence_ids":[str(e["evidence_id"]) for e in evidence],"successor_raw_artifact_id":successor_call["raw_id"]}
    encoded = json.dumps(payload,ensure_ascii=True,sort_keys=True,separators=(",",":"))
    _retention_require(len(encoded) <= 1_000_000)
    archive.update(proof_json=encoded,proof_sha256=hashlib.sha256(encoded.encode()).hexdigest())
    return archive


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
    elif error.code is ErrorCode.CAPABILITY_UNAVAILABLE:
        detail = "required capability unavailable in this build"
    elif error.code is ErrorCode.TRUST_INTEGRITY_INVALID:
        detail = "trust integrity verification failed"
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
    source_producer_version: str = _RAW_PRODUCER_VERSION,
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
            "source_producer_version": source_producer_version,
        }
    )
    return f"subtitle-source-{provenance_hash}"


def _capture_artifact_key(raw_request_hash: str, metadata: _SourceMetadata) -> str:
    # The key deliberately excludes content hash: changed bytes cannot rebind it.
    return f"subtitle-source-capture:{raw_request_hash}:{_encode_source_metadata(metadata)}"


def _capture_artifact_write(
    *, video_id: str, context: TranscriptJobContext, raw_request_hash: str,
    metadata: _SourceMetadata, content_hash: str, provider: str, provider_version: str,
) -> ArtifactWrite:
    identity = _stable_hash({
        "role": "subtitle-source-capture-v1", "job_id": context.job_id,
        "provider_version": provider_version,
        "raw_id": _raw_artifact_id(raw_request_hash=raw_request_hash, metadata=metadata,
                                   source_content_hash=content_hash, provider=provider),
    })
    return ArtifactWrite(
        artifact_id=f"subtitle-source-capture-{identity}",
        artifact_key=_capture_artifact_key(raw_request_hash, metadata),
        video_id=video_id, job_id=context.job_id, kind=ArtifactKind.SUBTITLE_SOURCE,
        storage_root=StorageRoot.DATA,
        relative_path=_source_relative_path(video_id=video_id, raw_request_hash=raw_request_hash, metadata=metadata),
        content_hash=content_hash, provider=provider, model=None,
        producer_version=_RAW_PRODUCER_VERSION, retention_class=RetentionClass.LONG_LIVED,
        expires_at=None,
    )


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
    from youtube_intel.tracked_retry_context import intercept_write

    if intercept_write(data_root, str(path.relative_to(data_root)), body):
        return
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
        normalized = normalize_timed_subtitle(raw_body, source_format)
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
        repository.bind_source_storage(data_root)
        self._repository = repository
        self._data_root = data_root
        self._context = context
        self._clock = clock
        self._provider_lease_seconds = provider_lease_seconds

    def _persist_timed_source(
        self, *, video_id: str, canonical_artifact_id: str,
        normalized: NormalizedSubtitle, language: str, now: datetime,
    ) -> None:
        persist = getattr(self._repository, "create_timed_transcript", None)
        if not callable(persist) or not normalized.timed_cues:
            return
        timed = TimedTranscriptWrite.from_cues(
            video_id=video_id, canonical_artifact_id=canonical_artifact_id,
            cues=tuple(TimedTranscriptCueWrite(
                start_ms=cue.start_ms, end_ms=cue.end_ms, text=cue.text,
            ) for cue in normalized.timed_cues),
        )
        persist(timed, now=now)
        _persist_original_transcript_evidence(
            self._repository, timed=timed, language=language, now=now,
        )

    def _read_capture_candidate(
        self, *, candidate: RankedSubtitleCandidate, video_id: str, raw_request_hash: str,
        provider_request: ProviderCallRequest, language_preferences: Sequence[str],
        now: datetime, require_timing: bool = False,
    ) -> tuple[bytes, NormalizedSubtitle, ProviderCallMetadata, ArtifactWrite] | None:
        track = candidate.track
        metadata = _SourceMetadata(track.source_type, candidate.requested_language, track.language, track.source_format)
        relative = _source_relative_path(video_id=video_id, raw_request_hash=raw_request_hash, metadata=metadata)
        path = _resolve_data_path(self._data_root, relative, video_id=video_id)
        record = self._get_artifact(_capture_artifact_key(raw_request_hash, metadata), video_id=video_id)
        if record is None and path.exists():
            raise _service_error(ErrorCode.LOCAL_RESOURCE, "unindexed subtitle source has no capture proof",
                                 retryable=False, video_id=video_id)
        if record is not None and path.exists():
            body, _ = _read_verified_file(path, expected_hash=record.content_hash,
                max_bytes=SUBTITLE_QUALITY_POLICY.max_raw_bytes, video_id=video_id,
                permission_error_code=ErrorCode.PERMISSION_DENIED)
            call = ProviderCallMetadata(provider=self._adapter.provider_name, provider_version=self._adapter.provider_version, started_at=now, finished_at=now)
            normalized = _normalize_recovered_raw(body, track.source_format, video_id=video_id)
        else:
            read = self._read_adapter_track(track, video_id=video_id)
            body, call = read.body, read.call
            normalized = normalize_timed_subtitle(body, track.source_format)
        if require_timing and not normalized.timed_cues:
            return None
        capture = _capture_artifact_write(video_id=video_id, context=self._context,
            raw_request_hash=raw_request_hash, metadata=metadata, content_hash=normalized.source_content_hash,
            provider=self._adapter.provider_name, provider_version=self._adapter.provider_version)
        from youtube_intel.tracked_retry_context import active_provider

        tracked = active_provider(provider_request.request_hash)
        # Retry's file journal freezes producer/hash before any write. Publish
        # before indexing so a failed write cannot leave an ordinary missing file.
        if tracked:
            _atomic_write(path, body, data_root=self._data_root, expected_hash=capture.content_hash,
                          max_bytes=SUBTITLE_QUALITY_POLICY.max_raw_bytes, video_id=video_id)
        self._repository.register_subtitle_source_capture(artifact=capture, body=body,
            context=self._context, provider_request=provider_request, language_preferences=language_preferences,
            provider_version=self._adapter.provider_version, data_root=self._data_root,
            now=_aware_utc(self._clock(), video_id=video_id))
        if not tracked:
            _atomic_write(path, body, data_root=self._data_root, expected_hash=capture.content_hash,
                          max_bytes=SUBTITLE_QUALITY_POLICY.max_raw_bytes, video_id=video_id)
        return body, normalized, call, capture

    def _native_timing_alternate(
        self, *, candidate: RankedSubtitleCandidate,
        ranked: Sequence[RankedSubtitleCandidate], video_id: str,
        raw_request_hash: str, provider_request: ProviderCallRequest,
        language_preferences: Sequence[str], now: datetime,
    ) -> tuple[RankedSubtitleCandidate, bytes, NormalizedSubtitle, ProviderCallMetadata, ArtifactWrite] | None:
        """Try one native body per alternate format for this exact caption track."""
        attempted_formats = {candidate.track.source_format}
        for alternate in ranked:
            track = alternate.track
            if (track.source_format not in {SubtitleFormat.VTT, SubtitleFormat.SRT}
                or track.source_format in attempted_formats
                or track.source_type is not candidate.track.source_type
                or normalize_language_tag(track.language) != normalize_language_tag(candidate.track.language)
                or _normalized_track_name(track.name) != _normalized_track_name(candidate.track.name)):
                continue
            attempted_formats.add(track.source_format)
            try:
                read = self._read_capture_candidate(candidate=alternate, video_id=video_id,
                    raw_request_hash=raw_request_hash, provider_request=provider_request,
                    language_preferences=language_preferences, now=now, require_timing=True)
            except InvalidSubtitleCandidate:
                continue
            if read is not None:
                body, normalized, call, capture = read
                return alternate, body, normalized, call, capture
        return None

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
            normalized = normalize_timed_subtitle(raw_body, metadata.source_format)
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
        self._persist_timed_source(
            video_id=video_id, canonical_artifact_id=canonical_artifact_id,
            normalized=normalized, language=metadata.actual_language, now=now,
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
        complete_stage: bool = True,
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
        if canonical_record is None and not complete_stage:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "verified canonical transcript artifact is missing",
                retryable=False,
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
        if complete_stage:
            self._complete_cached_stage(video_id=video_id, now=now)
        read_timed = getattr(self._repository, "get_verified_timed_transcript", None)
        current_timed = read_timed(video_id=video_id) if callable(read_timed) else None
        if current_timed is None:
            normalized = _normalize_recovered_raw(raw_body, metadata.source_format, video_id=video_id)
            if normalized.text != canonical_text:
                raise _service_error(ErrorCode.LOCAL_RESOURCE, "cached timed transcript text is inconsistent",
                                     retryable=False, video_id=video_id)
            self._persist_timed_source(
                video_id=video_id, canonical_artifact_id=canonical_record.artifact_id,
                normalized=normalized, language=metadata.actual_language, now=now,
            )
        elif current_timed.canonical_artifact_id == canonical_record.artifact_id:
            _persist_original_transcript_evidence(
                self._repository, timed=current_timed, language=metadata.actual_language, now=now,
            )
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
                accepted = self._read_capture_candidate(candidate=candidate, video_id=video_id,
                    raw_request_hash=raw_request_hash, provider_request=provider_request,
                    language_preferences=language_preferences, now=now)
                assert accepted is not None
                raw_body, normalized, last_call, capture = accepted
            except InvalidSubtitleCandidate:
                continue
            captures: tuple[ArtifactWrite, ...] = (capture,)

            if not normalized.timed_cues:
                # Preserve the original accepted plain body even if a native
                # alternate proves timing. No timing is inferred or clipped.
                _atomic_write(raw_path, raw_body, data_root=self._data_root,
                              expected_hash=normalized.source_content_hash,
                              max_bytes=SUBTITLE_QUALITY_POLICY.max_raw_bytes, video_id=video_id)
                alternate = self._native_timing_alternate(
                    candidate=candidate, ranked=ranked, video_id=video_id,
                    raw_request_hash=raw_request_hash, provider_request=provider_request,
                    language_preferences=language_preferences, now=now,
                )
                if alternate is not None:
                    candidate, raw_body, normalized, last_call, alternate_capture = alternate
                    captures += (alternate_capture,)
                    metadata = _SourceMetadata(
                        source_type=candidate.track.source_type, requested_language=candidate.requested_language,
                        actual_language=candidate.track.language, source_format=candidate.track.source_format,
                    )
                    raw_relative_path = _source_relative_path(
                        video_id=video_id, raw_request_hash=raw_request_hash, metadata=metadata,
                    )
                    raw_path = _resolve_data_path(self._data_root, raw_relative_path, video_id=video_id)

            from youtube_intel.tracked_retry_context import require_native_timing

            require_native_timing(bool(normalized.timed_cues))
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
            ) + captures
            completion = ProviderCallCompletion(
                request_hash=provider_request.request_hash, response_artifact_id=raw_artifact_id,
                input_tokens=None, output_tokens=None, cost_microusd=None,
            )
            from youtube_intel.tracked_retry_context import active_provider

            if active_provider(provider_request.request_hash):
                getattr(self._repository, "record_provider_dispatch_result_unknown")(
                    provider_request.request_hash, owner=self._context.owner, now=_aware_utc(self._clock(), video_id=video_id),
                )
            stage_persistence_failed = False
            try:
                repair = self._context.repair
                if repair is not None:
                    completion_now = _aware_utc(self._clock(), video_id=video_id)
                    if completion_now < now:
                        raise ValueError("caption repair clock moved backwards during acquisition")
                    complete_repair = getattr(self._repository, "complete_caption_repair")
                    repair_result: StageCompletionResult = complete_repair(
                        job_id=self._context.job_id, owner=self._context.owner, video_id=video_id,
                        pipeline_version=self._context.pipeline_version, source_run_id=repair.source_run_id,
                        expected_canonical_artifact_id=repair.expected_canonical_artifact_id,
                        artifacts=artifacts, provider_call=completion, data_root=self._data_root, now=completion_now,
                        language_preferences=language_preferences, provider_version=self._adapter.provider_version,
                        clock=self._clock,
                        timed=TimedTranscriptWrite.from_cues(video_id=video_id, canonical_artifact_id=canonical_artifact_id,
                            cues=tuple(TimedTranscriptCueWrite(start_ms=c.start_ms, end_ms=c.end_ms, text=c.text)
                                       for c in normalized.timed_cues)),
                    )
                    now = next(a.created_at for a in repair_result.artifacts if a.artifact_id == canonical_artifact_id)
                else:
                    self._repository.complete_stage(
                    job_id=self._context.job_id,
                    owner=self._context.owner,
                    video_id=video_id,
                    expected_status=PipelineStatus.METADATA_READY,
                    target_status=PipelineStatus.TRANSCRIPT_READY,
                    pipeline_version=self._context.pipeline_version,
                    artifacts=artifacts,
                    provider_call=completion,
                    now=now,
                )
                    self._persist_timed_source(
                        video_id=video_id, canonical_artifact_id=canonical_artifact_id,
                        normalized=normalized, language=candidate.track.language, now=now,
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
            failure_now = now
            if self._context.repair is not None:
                failure_now = _aware_utc(self._clock(), video_id=video_id)
                if failure_now < now:
                    raise TranscriptError(owner_failure)
            self._record_provider_failure(
                request_hash=provider_request.request_hash,
                error=owner_failure,
                now=failure_now,
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
            failure_now = now
            if self._context.repair is not None:
                failure_now = _aware_utc(self._clock(), video_id=video_id)
                if failure_now < now:
                    raise TranscriptError(fallback)
            self._record_provider_failure(
                request_hash=provider_request.request_hash,
                error=fallback,
                now=failure_now,
            )
            raise TranscriptError(fallback)
        return owner_result

    def load_verified_transcript(
        self,
        video: VideoMetadata,
        language_preferences: Sequence[str],
    ) -> TranscriptReady:
        """Recover an existing canonical transcript without completing a stage.

        This public application boundary reuses the same provider binding,
        path, hash, provenance, UTF-8, and quality checks as normal cache
        recovery, while avoiding a second Job transition.
        """

        video_id = video.video_id
        now = _aware_utc(self._clock(), video_id=video_id)
        raw_request_hash = build_raw_request_hash(
            video_id=video_id,
            language_preferences=language_preferences,
            provider=self._adapter.provider_name,
            provider_version=self._adapter.provider_version,
            refresh_generation=self._context.refresh_generation,
        )
        provider_request = self._provider_request(raw_request_hash)
        provider_record = self._get_provider_call(
            provider_request.request_hash,
            video_id=video_id,
        )
        cached = self._load_cached(
            video_id=video_id,
            raw_request_hash=raw_request_hash,
            language_preferences=language_preferences,
            now=now,
            provider_record=provider_record,
            complete_stage=False,
        )
        if cached is None:
            raise _service_error(
                ErrorCode.LOCAL_RESOURCE,
                "verified canonical transcript is unavailable",
                retryable=False,
                video_id=video_id,
            )
        return cached


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
        artifact_job = (
            None
            if artifact is None or artifact.job_id is None
            else self._repository.get_job(artifact.job_id)
        )
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
            or artifact_job is None
            or artifact_job.video_id != video_id
            or artifact_job.target_stage is not ProcessingStage.TRANSCRIPT
            or artifact_job.status is not JobStatus.SUCCEEDED
            or artifact_job.finished_at is None
            or artifact_job.pipeline_version != self._context.pipeline_version
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
