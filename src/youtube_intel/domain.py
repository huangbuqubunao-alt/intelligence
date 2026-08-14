"""Domain contracts: entities, provider ports, state machines, and errors.

This module must not import concrete provider SDKs or free-form dict public APIs.
"""

from __future__ import annotations

import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from importlib import import_module
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import (
    Any,
    Final,
    Literal,
    Never,
    Protocol,
    Self,
    TypeAlias,
    cast,
    no_type_check,
    runtime_checkable,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

# ---------------------------------------------------------------------------
# Shared model config
# ---------------------------------------------------------------------------

_FROZEN: Final = ConfigDict(extra="forbid", frozen=True)


class _DomainModel(BaseModel):
    model_config = _FROZEN


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class LiveStatus(str, Enum):
    NONE = "none"
    UPCOMING = "upcoming"
    LIVE = "live"
    ENDED = "ended"


class Availability(str, Enum):
    PUBLIC = "public"
    UNAVAILABLE = "unavailable"
    PRIVATE = "private"
    DELETED = "deleted"
    RESTRICTED = "restricted"


class TranscriptSourceType(str, Enum):
    MANUAL_SUBTITLE = "manual_subtitle"
    AUTO_SUBTITLE = "auto_subtitle"
    WHISPER = "whisper"


class SubtitleFormat(str, Enum):
    JSON3 = "json3"
    VTT = "vtt"
    SRT = "srt"


class TranscriptQualityFlag(str, Enum):
    ROLLING_CUES_DEDUPED = "ROLLING_CUES_DEDUPED"
    SPEAKER_LABELS_PRESENT = "SPEAKER_LABELS_PRESENT"
    NON_SPEECH_MARKERS_PRESENT = "NON_SPEECH_MARKERS_PRESENT"


class TranscriptionReason(str, Enum):
    NO_TRACKS = "NO_TRACKS"
    NO_MATCHING_LANGUAGE = "NO_MATCHING_LANGUAGE"
    ALL_CANDIDATES_INVALID = "ALL_CANDIDATES_INVALID"


class PointKind(str, Enum):
    FACT = "fact"
    INFERENCE = "inference"
    RECOMMENDATION = "recommendation"


class IntelligenceMode(str, Enum):
    LOCAL_ONLY = "local-only"
    HYBRID = "hybrid"
    CLOUD = "cloud"


class KnowledgeExecutionMode(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


class KnowledgeFallbackReason(str, Enum):
    CREDENTIAL_UNAVAILABLE = "credential-unavailable"
    BUDGET_EXHAUSTED = "budget-exhausted"
    INPUT_NOT_ELIGIBLE = "input-not-eligible"
    PROVIDER_UNAVAILABLE = "provider-unavailable"
    PROVIDER_TIMEOUT = "provider-timeout"
    INVALID_RESPONSE = "invalid-response"


class EvidenceSource(str, Enum):
    TITLE = "title"
    CHANNEL_NAME = "channel_name"
    DESCRIPTION = "description"
    TRANSCRIPT_SAMPLE = "transcript_sample"


class AnalysisSkipReason(str, Enum):
    CLOUD_DISABLED = "CLOUD_DISABLED"
    CREDENTIAL_UNAVAILABLE = "CREDENTIAL_UNAVAILABLE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
    PROVIDER_REFUSAL = "PROVIDER_REFUSAL"


class NotAvailableReason(str, Enum):
    NO_MATCHING_LANGUAGE = "NO_MATCHING_LANGUAGE"
    NO_CONTENT = "NO_CONTENT"
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"


class NoteKind(str, Enum):
    VIDEO = "video"
    WEEKLY = "weekly"


class PipelineStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    METADATA_READY = "METADATA_READY"
    DEFERRED = "DEFERRED"
    TRANSCRIPT_READY = "TRANSCRIPT_READY"
    SCORED = "SCORED"
    LOW_VALUE_READY = "LOW_VALUE_READY"
    ANALYSIS_READY = "ANALYSIS_READY"
    NOTE_WRITTEN = "NOTE_WRITTEN"
    COMPLETE = "COMPLETE"
    SKIPPED_DURATION_LIMIT = "SKIPPED_DURATION_LIMIT"


class ProcessingStage(str, Enum):
    DISCOVERY = "DISCOVERY"
    METADATA = "METADATA"
    TRANSCRIPT = "TRANSCRIPT"
    SCORING = "SCORING"
    ANALYSIS = "ANALYSIS"
    NOTE_WRITE = "NOTE_WRITE"
    WEEKLY_REPORT = "WEEKLY_REPORT"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRY_PENDING = "RETRY_PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_FINAL = "FAILED_FINAL"


class ErrorCode(str, Enum):
    """Unified error codes frozen in System Design §12 (exact set; no extras)."""

    TRANSIENT_NETWORK = "TRANSIENT_NETWORK"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"
    CONFIG_INVALID = "CONFIG_INVALID"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    LOCAL_RESOURCE = "LOCAL_RESOURCE"


SCORE_DIMENSION_NAMES: Final[tuple[str, ...]] = (
    "technical",
    "business",
    "product",
    "originality",
    "practicality",
    "industry_impact",
)

# Private mutable builders → public runtime-immutable mappings (values are frozensets).
_PIPELINE_TRANSITIONS: dict[PipelineStatus, frozenset[PipelineStatus]] = {
    PipelineStatus.DISCOVERED: frozenset(
        {PipelineStatus.METADATA_READY, PipelineStatus.DEFERRED}
    ),
    PipelineStatus.DEFERRED: frozenset({PipelineStatus.METADATA_READY}),
    PipelineStatus.METADATA_READY: frozenset(
        {PipelineStatus.TRANSCRIPT_READY, PipelineStatus.SKIPPED_DURATION_LIMIT}
    ),
    PipelineStatus.TRANSCRIPT_READY: frozenset({PipelineStatus.SCORED}),
    PipelineStatus.SCORED: frozenset(
        {PipelineStatus.LOW_VALUE_READY, PipelineStatus.ANALYSIS_READY}
    ),
    PipelineStatus.LOW_VALUE_READY: frozenset({PipelineStatus.COMPLETE}),
    PipelineStatus.ANALYSIS_READY: frozenset({PipelineStatus.NOTE_WRITTEN}),
    PipelineStatus.NOTE_WRITTEN: frozenset({PipelineStatus.COMPLETE}),
    PipelineStatus.COMPLETE: frozenset(),
    PipelineStatus.SKIPPED_DURATION_LIMIT: frozenset(),
}
PIPELINE_TRANSITIONS: Final[Mapping[PipelineStatus, frozenset[PipelineStatus]]] = (
    MappingProxyType(_PIPELINE_TRANSITIONS)
)

_JOB_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.PENDING: frozenset({JobStatus.RUNNING}),
    JobStatus.RUNNING: frozenset(
        {JobStatus.SUCCEEDED, JobStatus.RETRY_PENDING, JobStatus.FAILED_FINAL}
    ),
    JobStatus.RETRY_PENDING: frozenset({JobStatus.PENDING}),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.FAILED_FINAL: frozenset(),
}
JOB_TRANSITIONS: Final[Mapping[JobStatus, frozenset[JobStatus]]] = MappingProxyType(
    _JOB_TRANSITIONS
)


# ---------------------------------------------------------------------------
# Structured errors
# ---------------------------------------------------------------------------


class AppError(_DomainModel):
    """Structured, redacted application error.

    Retry semantics live in ``retryable`` and ``retry_after_seconds``, not in
    free-form message strings.
    """

    code: ErrorCode
    message: str = Field(min_length=1, max_length=2000)
    retryable: bool
    retry_after_seconds: float | None = Field(default=None, ge=0)
    run_id: str | None = None
    job_id: str | None = None
    video_id: str | None = None
    stage: ProcessingStage | None = None

    @model_validator(mode="after")
    def _retry_after_only_when_retryable(self) -> AppError:
        if self.retry_after_seconds is not None and not self.retryable:
            msg = "retry_after_seconds requires retryable=True"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Core data objects
# ---------------------------------------------------------------------------


class VideoMetadata(_DomainModel):
    video_id: str = Field(min_length=1)
    channel_id: str = Field(min_length=1)
    channel_name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    source_url: str = Field(min_length=1)
    published_at: datetime
    duration_seconds: int = Field(ge=0)
    default_language: str | None = None
    available_languages: tuple[str, ...] = ()
    live_status: LiveStatus
    availability: Availability


class TranscriptArtifact(_DomainModel):
    video_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    source_type: TranscriptSourceType
    requested_language: str | None
    source_format: SubtitleFormat | None
    text_path: str = Field(min_length=1)
    timed_text_path: str | None = None
    source_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_byte_count: int = Field(gt=0)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    char_count: int = Field(ge=0)
    segment_count: int = Field(ge=0)
    normalization_version: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str | None = None
    created_at: datetime
    quality_flags: tuple[TranscriptQualityFlag, ...] = ()

    @field_validator("requested_language")
    @classmethod
    def _validate_requested_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or value.strip() != value:
            msg = "requested_language must be non-empty without surrounding whitespace"
            raise ValueError(msg)
        return value

    @field_validator("text_path", "timed_text_path")
    @classmethod
    def _safe_data_relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or value.strip() != value or "\\" in value:
            msg = "transcript paths must be safe DATA-relative POSIX paths"
            raise ValueError(msg)
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or not path.parts
            or path.parts[0] != "transcripts"
        ):
            msg = "transcript paths must be safe DATA-relative paths under transcripts/"
            raise ValueError(msg)
        return value

    @field_validator("quality_flags")
    @classmethod
    def _unique_quality_flags(
        cls,
        value: tuple[TranscriptQualityFlag, ...],
    ) -> tuple[TranscriptQualityFlag, ...]:
        if len(value) != len(set(value)):
            msg = "quality_flags must be unique"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _source_specific_fields(self) -> TranscriptArtifact:
        if self.source_type is TranscriptSourceType.WHISPER:
            if self.requested_language is not None:
                msg = "requested_language must be None for whisper"
                raise ValueError(msg)
            if self.source_format is not None:
                msg = "source_format must be None for whisper"
                raise ValueError(msg)
            return self

        if self.requested_language is None:
            msg = "requested_language is required for subtitle sources"
            raise ValueError(msg)
        if self.source_format is None:
            msg = "source_format is required for subtitle sources"
            raise ValueError(msg)
        if self.timed_text_path is None:
            msg = "timed_text_path is required for subtitle sources"
            raise ValueError(msg)
        return self


class ScoreDimensions(_DomainModel):
    technical: float | None = Field(default=None, ge=0, le=10)
    business: float | None = Field(default=None, ge=0, le=10)
    product: float | None = Field(default=None, ge=0, le=10)
    originality: float | None = Field(default=None, ge=0, le=10)
    practicality: float | None = Field(default=None, ge=0, le=10)
    industry_impact: float | None = Field(default=None, ge=0, le=10)


ScoringOutputLanguage: TypeAlias = Literal["zh-CN", "en"]
_ScoringScript: TypeAlias = Literal[
    "Han",
    "Latin",
    "Hiragana",
    "Katakana",
    "Hangul",
    "Cyrillic",
    "Arabic",
    "Other",
]
_SCORING_NON_TARGET_SCRIPTS: Final[frozenset[_ScoringScript]] = frozenset(
    {"Hiragana", "Katakana", "Hangul", "Cyrillic", "Arabic"}
)
_SCORING_NAMED_SCRIPTS: Final[tuple[_ScoringScript, ...]] = (
    "Latin",
    "Hiragana",
    "Katakana",
    "Hangul",
    "Cyrillic",
    "Arabic",
)


@dataclass(frozen=True, slots=True)
class _ScoringScriptSpan:
    script: _ScoringScript
    text: str


class ScoringLanguageValidation(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNCERTAIN = "UNCERTAIN"


def _scoring_character_script(character: str) -> _ScoringScript:
    codepoint = ord(character)
    if (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x323AF
    ):
        return "Han"
    if character.isalpha():
        unicode_name = unicodedata.name(character, "")
        for script in _SCORING_NAMED_SCRIPTS:
            if script.upper() in unicode_name:
                return script
    return "Other"


def _scoring_script_spans(value: str) -> tuple[_ScoringScriptSpan, ...]:
    """Split text by Unicode script without interpreting span position."""

    spans: list[_ScoringScriptSpan] = []
    current_script: _ScoringScript | None = None
    current_characters: list[str] = []
    for character in value:
        script = _scoring_character_script(character)
        if current_script is not None and script != current_script:
            spans.append(
                _ScoringScriptSpan(current_script, "".join(current_characters))
            )
            current_characters.clear()
        current_script = script
        current_characters.append(character)
    if current_script is not None:
        spans.append(_ScoringScriptSpan(current_script, "".join(current_characters)))
    return tuple(spans)


class _DependencyToken(Protocol):
    pos_: str
    dep_: str
    ent_iob_: str
    head: _DependencyToken

    @property
    def children(self) -> Iterable[_DependencyToken]: ...


class _DependencyParser(Protocol):
    def __call__(self, text: str) -> Sequence[_DependencyToken]: ...


@lru_cache(maxsize=1)
def _load_english_dependency_parser() -> _DependencyParser | None:
    """Load only the installed fixed model package; never resolve or download."""

    try:
        module = import_module("en_core_web_sm")
        load = cast(Callable[..., object], getattr(module, "load"))
        parser = load(exclude=("lemmatizer",))
    except Exception:
        return None
    return cast(_DependencyParser, parser)


_DEPENDENCY_SUBJECTS: Final[frozenset[str]] = frozenset(
    {"nsubj", "nsubjpass", "csubj", "csubjpass"}
)
_DEPENDENCY_ARGUMENTS: Final[frozenset[str]] = frozenset(
    {"dobj", "obj", "iobj", "attr", "oprd", "ccomp", "xcomp", "acomp"}
)
_NATURAL_STRUCTURE_DEPENDENCIES: Final[frozenset[str]] = frozenset(
    {
        "acl",
        "advcl",
        "advmod",
        "amod",
        "aux",
        "cc",
        "ccomp",
        "det",
        "mark",
        "prep",
        "relcl",
        "xcomp",
    }
)
_ENTITY_INTERNAL_DEPENDENCIES: Final[frozenset[str]] = frozenset(
    {"amod", "appos", "compound", "det", "flat", "pobj", "prep"}
)
_NATURAL_NOMINAL_DEPENDENCIES: Final[frozenset[str]] = frozenset(
    {"acl", "advmod", "det", "nummod", "poss", "prep", "relcl"}
)


def _has_natural_dependency_structure(tokens: Sequence[_DependencyToken]) -> bool:
    return any(token.dep_ in _NATURAL_STRUCTURE_DEPENDENCIES for token in tokens)


def _coordinated_predicate_has_subject_context(token: _DependencyToken) -> bool:
    if token.dep_ != "conj" or token.head.pos_ not in {"INTJ", "NOUN", "PROPN"}:
        return False
    head_children = tuple(token.head.children)
    return any(child.dep_ == "cc" for child in head_children) and any(
        child is not token
        and child.pos_ in {"NOUN", "PROPN"}
        and child.dep_ in {"compound", "conj", "nsubj"}
        for child in head_children
    )


def _nominal_argument_has_natural_structure(token: _DependencyToken) -> bool:
    children = tuple(token.children)
    for child in children:
        if child.dep_ in _NATURAL_NOMINAL_DEPENDENCIES:
            return True
    modifiers = {child.dep_ for child in children}
    related = (token, *children)
    if (
        {"amod", "compound"} <= modifiers
        and all(item.ent_iob_ == "O" for item in related)
    ):
        return True
    return False


def _nominal_argument_is_named_entity_structure(token: _DependencyToken) -> bool:
    related = (token, *tuple(token.children))
    if any(item.ent_iob_ != "O" for item in related):
        return all(
            child is token
            or child.dep_ in _ENTITY_INTERNAL_DEPENDENCIES
            or child.pos_ == "PUNCT"
            for child in related
        )
    return False


def _nominal_argument_is_det_compound_entity_structure(
    token: _DependencyToken,
) -> bool:
    children = tuple(token.children)
    dependencies = {child.dep_ for child in children}
    return (
        "det" in dependencies
        and dependencies <= _ENTITY_INTERNAL_DEPENDENCIES
        and any(child.dep_ in {"compound", "flat"} for child in children)
    )


def _nominal_argument_is_entity_like(token: _DependencyToken) -> bool:
    if token.pos_ not in {"NOUN", "PROPN"}:
        return False
    if _nominal_argument_is_named_entity_structure(token):
        return True
    if _nominal_argument_is_det_compound_entity_structure(token):
        return True
    return not _nominal_argument_has_natural_structure(token)


def _nominal_argument_has_only_entity_internal_structure(
    token: _DependencyToken,
) -> bool:
    """Return whether a nominal subtree contains no natural-language evidence."""

    if token.pos_ not in {"NOUN", "PROPN"}:
        return False
    return all(
        child.pos_ == "PUNCT"
        or child.dep_ in _ENTITY_INTERNAL_DEPENDENCIES
        for child in token.children
    )


def _predicate_direct_arguments(
    children: Sequence[_DependencyToken],
) -> tuple[_DependencyToken, ...]:
    return tuple(child for child in children if child.dep_ in _DEPENDENCY_ARGUMENTS)


def _predicate_prepositional_arguments(
    children: Sequence[_DependencyToken],
) -> tuple[_DependencyToken, ...]:
    arguments: list[_DependencyToken] = []
    for child in children:
        if child.dep_ != "prep":
            continue
        arguments.extend(
            complement
            for complement in child.children
            if complement.dep_ in {"pcomp", "pobj"}
        )
    return tuple(arguments)


def _predicate_has_complete_structure(
    token: _DependencyToken,
    tokens: Sequence[_DependencyToken],
) -> bool:
    if token.pos_ != "VERB" or token.dep_ not in {"ROOT", "conj"}:
        return False
    children = tuple(token.children)
    subjects = tuple(child for child in children if child.dep_ in _DEPENDENCY_SUBJECTS)
    direct_arguments = _predicate_direct_arguments(children)
    prepositional_arguments = _predicate_prepositional_arguments(children)
    arguments = (*direct_arguments, *prepositional_arguments)
    if not arguments:
        return False
    coordinated_subject = _coordinated_predicate_has_subject_context(token)
    if not subjects and not coordinated_subject:
        return False
    if token.ent_iob_ != "O":
        return False
    if not coordinated_subject:
        core_arguments_are_entities = bool(direct_arguments) and all(
            _nominal_argument_is_entity_like(argument)
            for argument in (*subjects, *direct_arguments)
        )
        prepositions_are_entity_internal = all(
            _nominal_argument_has_only_entity_internal_structure(argument)
            for argument in prepositional_arguments
        )
        if core_arguments_are_entities and prepositions_are_entity_internal:
            return False
    return _has_natural_dependency_structure(tokens)


def _parse_has_complete_english_structure(
    parser: _DependencyParser,
    text: str,
) -> bool:
    try:
        # Parse one deterministic case-neutral representation. This avoids
        # selecting a permissive result from multiple casing-dependent parses.
        tokens = tuple(parser(text.casefold()))
        return any(
            _predicate_has_complete_structure(token, tokens)
            for token in tokens
        )
    except Exception:
        return False


def _has_english_relation_structure(reason: str) -> bool:
    """Require one complete parse with a predicate, arguments, and structure."""

    parser = _load_english_dependency_parser()
    if parser is None:
        return False
    return _parse_has_complete_english_structure(parser, reason)


def _latin_text_groups(
    spans: Sequence[_ScoringScriptSpan],
) -> tuple[str, ...]:
    """Return Latin groups separated by a non-Latin language script."""

    groups: list[str] = []
    current: list[str] = []
    for span in spans:
        if span.script == "Latin":
            current.append(span.text)
        elif span.script == "Other":
            current.append(" ")
        elif current:
            text = "".join(current).strip()
            if any(character.isalpha() for character in text):
                groups.append(text)
            current.clear()
    if current:
        text = "".join(current).strip()
        if any(character.isalpha() for character in text):
            groups.append(text)
    return tuple(groups)


_IDENTIFIER_COMPATIBLE_POS: Final[frozenset[str]] = frozenset(
    {"NOUN", "PROPN", "X", "SYM", "NUM"}
)


def _latin_groups_are_identifier_material(
    spans: Sequence[_ScoringScriptSpan],
) -> bool:
    """Accept mixed-script Latin only when the parser sees nominal material."""

    parser = _load_english_dependency_parser()
    if parser is None:
        return False
    groups = _latin_text_groups(spans)
    if not groups:
        return True
    try:
        return all(
            all(
                token.pos_ in _IDENTIFIER_COMPATIBLE_POS
                for token in parser(group)
                if token.pos_ not in {"PUNCT", "SPACE"}
            )
            for group in groups
        )
    except Exception:
        return False


def _has_weak_latin_evidence(spans: Sequence[_ScoringScriptSpan]) -> bool:
    return any(span.script == "Latin" for span in spans)


def detect_scoring_language_violation(
    reason: str,
    output_language: ScoringOutputLanguage,
) -> ScoringLanguageValidation:
    """Detect only unambiguous wrong-script responses; mixed text is uncertain."""

    spans = _scoring_script_spans(reason)
    has_han = any(span.script == "Han" and len(span.text) > 1 for span in spans)
    has_weak_latin = _has_weak_latin_evidence(spans)
    has_other_language_script = any(
        span.script in _SCORING_NON_TARGET_SCRIPTS for span in spans
    )
    if output_language == "zh-CN":
        if not has_han:
            if has_other_language_script:
                return ScoringLanguageValidation.INVALID
            if _has_english_relation_structure(reason):
                return ScoringLanguageValidation.INVALID
            return ScoringLanguageValidation.UNCERTAIN
        if has_other_language_script:
            return ScoringLanguageValidation.UNCERTAIN
        if not has_weak_latin or _latin_groups_are_identifier_material(spans):
            return ScoringLanguageValidation.VALID
        return ScoringLanguageValidation.UNCERTAIN

    if has_other_language_script:
        return ScoringLanguageValidation.UNCERTAIN
    if has_han:
        if has_weak_latin:
            return ScoringLanguageValidation.UNCERTAIN
        return ScoringLanguageValidation.INVALID
    if _has_english_relation_structure(reason):
        return ScoringLanguageValidation.VALID
    return ScoringLanguageValidation.UNCERTAIN


def scoring_reason_matches_output_language(
    reason: str,
    output_language: ScoringOutputLanguage,
) -> bool:
    """Return whether a reason has one unambiguous configured-language subject."""

    return (
        detect_scoring_language_violation(reason, output_language)
        is ScoringLanguageValidation.VALID
    )


class ScoreResult(_DomainModel):
    schema_version: str = Field(min_length=1)
    score: float = Field(ge=0, le=10)
    reason: str = Field(min_length=1, max_length=2000)
    topics: tuple[str, ...] = Field(min_length=1, max_length=10)
    should_summarize: bool
    dimensions: ScoreDimensions | None = None
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    request_hash: str = Field(min_length=1)
    output_language: ScoringOutputLanguage

    def model_copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            msg = "model_copy(update=...) is disabled for scoring contracts"
            raise ValueError(msg)
        return super().model_copy(deep=deep)

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "reason must be non-empty after strip"
            raise ValueError(msg)
        if len(stripped) > 2000:
            msg = "reason must be at most 2000 characters after strip"
            raise ValueError(msg)
        return stripped

    @field_validator("topics")
    @classmethod
    def _validate_topics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            msg = "topics must contain at least one item"
            raise ValueError(msg)
        if len(value) > 10:
            msg = "topics must contain at most 10 items"
            raise ValueError(msg)
        seen: set[str] = set()
        for topic in value:
            if not 1 <= len(topic) <= 80:
                msg = "each topic must have length 1..80"
                raise ValueError(msg)
            if topic in seen:
                msg = "topics must be unique"
                raise ValueError(msg)
            seen.add(topic)
        return value

    @model_validator(mode="after")
    def _reason_matches_output_language(self) -> ScoreResult:
        if not scoring_reason_matches_output_language(
            self.reason, self.output_language
        ):
            msg = "reason does not match output_language"
            raise ValueError(msg)
        return self


def validate_score_result(value: object) -> ScoreResult:
    """Revalidate an untrusted score even when it is already a Pydantic instance.

    Pydantic intentionally exposes unchecked construction/copy APIs.  Provider,
    cache, artifact, and Runtime boundaries therefore treat model instances as
    data and rebuild them through the complete schema and language validators.
    """

    candidate = (
        value.model_dump(mode="python") if isinstance(value, ScoreResult) else value
    )
    return ScoreResult.model_validate(candidate)


def validate_score_result_json(value: str | bytes | bytearray) -> ScoreResult:
    """Parse persisted JSON and apply the same trusted score validation entry."""

    return validate_score_result(ScoreResult.model_validate_json(value))


class _UpdateProtectedAnalysisContract(_DomainModel):
    """Preserve validation boundaries for shared cloud-analysis contracts."""

    def model_copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            msg = "model_copy(update=...) is disabled for analysis contracts"
            raise ValueError(msg)
        return super().model_copy(deep=deep)


class AnalysisPayload(_UpdateProtectedAnalysisContract):
    """The complete and exclusive set of fields permitted to leave the machine."""

    video_id: str = Field(min_length=1, pattern=r"\S")
    title: str = Field(min_length=1, pattern=r"\S")
    channel_name: str = Field(min_length=1, pattern=r"\S")
    published_at: datetime
    duration_seconds: int = Field(ge=0)
    default_language: str | None = Field(default=None, pattern=r"\S")
    description: str = Field(default="", max_length=4000)
    transcript_language: str = Field(min_length=1, pattern=r"\S")
    output_language: str = Field(min_length=1, pattern=r"\S")
    transcript_sample: str = Field(min_length=1, pattern=r"\S")


class EvidenceExcerpt(_UpdateProtectedAnalysisContract):
    evidence_id: str = Field(min_length=1, pattern=r"\S")
    source: EvidenceSource
    excerpt: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    start_seconds: Literal[None] = None
    end_seconds: Literal[None] = None


class AnalysisPoint(_UpdateProtectedAnalysisContract):
    text: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    kind: PointKind
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=10)

    @field_validator("evidence_ids")
    @classmethod
    def _unique_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "evidence_ids must be unique"
            raise ValueError(msg)
        for eid in value:
            if not eid.strip():
                msg = "evidence_ids items must be non-empty"
                raise ValueError(msg)
        return value


class AnalysisContent(_UpdateProtectedAnalysisContract):
    one_sentence_summary: str = Field(min_length=1, max_length=500, pattern=r"\S")
    core_points: tuple[AnalysisPoint, ...] = Field(min_length=1, max_length=10)
    key_facts: tuple[AnalysisPoint, ...] = Field(default=(), max_length=20)
    product_opportunities: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    business_opportunities: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    actionable_directions: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    hypotheses_to_validate: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    action_recommendations: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    risks: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    keywords: tuple[str, ...] = Field(min_length=1, max_length=20)
    evidence: tuple[EvidenceExcerpt, ...] = Field(default=(), max_length=20)

    @field_validator("keywords")
    @classmethod
    def _validate_keywords(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            msg = "keywords must contain at least one item"
            raise ValueError(msg)
        if len(value) > 20:
            msg = "keywords must contain at most 20 items"
            raise ValueError(msg)
        seen: set[str] = set()
        for kw in value:
            if not kw.strip() or not 1 <= len(kw) <= 80:
                msg = "each keyword must have length 1..80"
                raise ValueError(msg)
            if kw in seen:
                msg = "keywords must be unique"
                raise ValueError(msg)
            seen.add(kw)
        return value

    @model_validator(mode="after")
    def _cross_field_integrity(self) -> AnalysisContent:
        evidence_ids = {item.evidence_id for item in self.evidence}
        if len(evidence_ids) != len(self.evidence):
            msg = "evidence_id values must be unique within AnalysisContent"
            raise ValueError(msg)

        kind_rules = (
            ("core_points", self.core_points, {PointKind.FACT, PointKind.INFERENCE}),
            ("key_facts", self.key_facts, {PointKind.FACT}),
            ("product_opportunities", self.product_opportunities, {PointKind.INFERENCE}),
            ("business_opportunities", self.business_opportunities, {PointKind.INFERENCE}),
            ("actionable_directions", self.actionable_directions, {PointKind.RECOMMENDATION}),
            ("hypotheses_to_validate", self.hypotheses_to_validate, {PointKind.INFERENCE}),
            ("action_recommendations", self.action_recommendations, {PointKind.RECOMMENDATION}),
            ("risks", self.risks, {PointKind.INFERENCE}),
        )
        for field_name, points, allowed_kinds in kind_rules:
            for point in points:
                if point.kind not in allowed_kinds:
                    allowed = ", ".join(sorted(kind.value for kind in allowed_kinds))
                    msg = f"{field_name} items must have kind in {{{allowed}}}"
                    raise ValueError(msg)

        all_points: list[AnalysisPoint] = [
            *self.core_points,
            *self.key_facts,
            *self.product_opportunities,
            *self.business_opportunities,
            *self.actionable_directions,
            *self.hypotheses_to_validate,
            *self.action_recommendations,
            *self.risks,
        ]
        for point in all_points:
            missing = [eid for eid in point.evidence_ids if eid not in evidence_ids]
            if missing:
                msg = f"evidence_ids reference unknown evidence: {missing}"
                raise ValueError(msg)
        return self


class AnalysisResult(AnalysisContent):
    schema_version: Literal["analysis-result-v1"] = "analysis-result-v1"
    provider: str = Field(min_length=1, pattern=r"\S")
    model: str = Field(min_length=1, pattern=r"\S")
    prompt_version: Literal["analysis-prompt-v1"] = "analysis-prompt-v1"
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Provider-neutral Knowledge V2 contracts
# ---------------------------------------------------------------------------


def _validate_unique_semantic_items(
    value: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    if len(value) != len(set(value)):
        msg = f"{field_name} items must be unique"
        raise ValueError(msg)
    for item in value:
        if not item.strip() or len(item) > 2000:
            msg = f"{field_name} items must be non-empty and at most 2000 characters"
            raise ValueError(msg)
    return value


class KnowledgeEvidence(_UpdateProtectedAnalysisContract):
    evidence_id: str = Field(min_length=1, max_length=100, pattern=r"\S")
    source: EvidenceSource
    excerpt: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    source_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    start_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    end_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    timestamp_basis: Literal["timed-subtitle"] | None = None

    @model_validator(mode="after")
    def _timestamp_integrity(self) -> KnowledgeEvidence:
        timestamps_present = self.start_seconds is not None
        if timestamps_present != (self.end_seconds is not None):
            msg = "start_seconds and end_seconds must be provided together"
            raise ValueError(msg)
        if timestamps_present:
            if self.source is not EvidenceSource.TRANSCRIPT_SAMPLE:
                msg = "timestamps are allowed only for transcript evidence"
                raise ValueError(msg)
            if self.timestamp_basis != "timed-subtitle":
                msg = "timestamps require the trusted timed-subtitle basis"
                raise ValueError(msg)
            assert self.start_seconds is not None
            assert self.end_seconds is not None
            if self.end_seconds < self.start_seconds:
                msg = "end_seconds must be >= start_seconds"
                raise ValueError(msg)
        elif self.timestamp_basis is not None:
            msg = "timestamp_basis must be absent when timestamps are absent"
            raise ValueError(msg)
        return self


class EvidenceRegistry(_UpdateProtectedAnalysisContract):
    items: tuple[KnowledgeEvidence, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def _unique_ids(self) -> EvidenceRegistry:
        evidence_ids = tuple(item.evidence_id for item in self.items)
        if len(evidence_ids) != len(set(evidence_ids)):
            msg = "evidence_id values must be unique within EvidenceRegistry"
            raise ValueError(msg)
        return self


class KnowledgeGraph(_UpdateProtectedAnalysisContract):
    topics: tuple[str, ...] = Field(min_length=1, max_length=20)
    entities: tuple[str, ...] = Field(default=(), max_length=30)
    related_themes: tuple[str, ...] = Field(default=(), max_length=20)
    future_watch_topics: tuple[str, ...] = Field(default=(), max_length=20)

    @field_validator("topics", "entities", "related_themes", "future_watch_topics")
    @classmethod
    def _semantic_items(
        cls,
        value: tuple[str, ...],
        info: ValidationInfo,
    ) -> tuple[str, ...]:
        return _validate_unique_semantic_items(
            value,
            field_name=info.field_name or "knowledge_graph",
        )


class KnowledgeProvenance(_UpdateProtectedAnalysisContract):
    requested_mode: IntelligenceMode
    executed_mode: KnowledgeExecutionMode
    fallback_reason: KnowledgeFallbackReason | None = None
    provider: str = Field(min_length=1, max_length=200, pattern=r"\S")
    model: str = Field(min_length=1, max_length=300, pattern=r"\S")
    model_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    output_language: str = Field(min_length=1, max_length=40, pattern=r"\S")
    prompt_version: Literal["knowledge-prompt-v2"] = "knowledge-prompt-v2"
    schema_version: Literal["knowledge-result-v2"] = "knowledge-result-v2"
    sampling_version: Literal["knowledge-sampling-v2"] = "knowledge-sampling-v2"
    privacy_version: Literal["knowledge-privacy-v2"] = "knowledge-privacy-v2"
    transcript_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _mode_and_model_identity(self) -> KnowledgeProvenance:
        if (
            self.requested_mode is IntelligenceMode.LOCAL_ONLY
            and self.executed_mode is not KnowledgeExecutionMode.LOCAL
        ):
            msg = "local-only requests must execute locally"
            raise ValueError(msg)
        if (
            self.requested_mode is IntelligenceMode.CLOUD
            and self.executed_mode is not KnowledgeExecutionMode.CLOUD
        ):
            msg = "cloud requests must execute in cloud mode"
            raise ValueError(msg)
        if (
            self.requested_mode is IntelligenceMode.HYBRID
            and self.executed_mode is KnowledgeExecutionMode.LOCAL
        ) != (self.fallback_reason is not None):
            msg = (
                "fallback_reason is required only when a hybrid request "
                "falls back to local execution"
            )
            raise ValueError(msg)
        if (
            self.executed_mode is KnowledgeExecutionMode.LOCAL
            and self.model_digest is None
        ):
            msg = "model_digest is required for local execution"
            raise ValueError(msg)
        if (
            self.executed_mode is KnowledgeExecutionMode.CLOUD
            and self.model_digest is not None
        ):
            msg = "model_digest must be absent for cloud execution"
            raise ValueError(msg)
        return self


class KnowledgeContent(_UpdateProtectedAnalysisContract):
    one_sentence_summary: str = Field(min_length=1, max_length=500, pattern=r"\S")
    summary_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=10)
    why_it_matters: AnalysisPoint
    core_points: tuple[AnalysisPoint, ...] = Field(min_length=1, max_length=10)
    key_facts: tuple[AnalysisPoint, ...] = Field(default=(), max_length=20)
    important_concepts: tuple[AnalysisPoint, ...] = Field(default=(), max_length=20)
    key_arguments: tuple[AnalysisPoint, ...] = Field(default=(), max_length=20)
    counterpoints: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    product_opportunities: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    business_opportunities: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    actionable_directions: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    hypotheses_to_validate: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    action_recommendations: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    risks: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    knowledge_graph: KnowledgeGraph

    @field_validator("summary_evidence_ids")
    @classmethod
    def _summary_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_unique_semantic_items(
            value,
            field_name="summary_evidence_ids",
        )

    @model_validator(mode="after")
    def _semantic_kinds(self) -> KnowledgeContent:
        kind_rules = (
            ("why_it_matters", (self.why_it_matters,), {PointKind.INFERENCE}),
            ("core_points", self.core_points, {PointKind.FACT, PointKind.INFERENCE}),
            ("key_facts", self.key_facts, {PointKind.FACT}),
            ("important_concepts", self.important_concepts, {PointKind.FACT, PointKind.INFERENCE}),
            ("key_arguments", self.key_arguments, {PointKind.FACT, PointKind.INFERENCE}),
            ("counterpoints", self.counterpoints, {PointKind.INFERENCE}),
            ("product_opportunities", self.product_opportunities, {PointKind.INFERENCE}),
            ("business_opportunities", self.business_opportunities, {PointKind.INFERENCE}),
            ("actionable_directions", self.actionable_directions, {PointKind.RECOMMENDATION}),
            ("hypotheses_to_validate", self.hypotheses_to_validate, {PointKind.INFERENCE}),
            ("action_recommendations", self.action_recommendations, {PointKind.RECOMMENDATION}),
            ("risks", self.risks, {PointKind.INFERENCE}),
        )
        for field_name, points, allowed_kinds in kind_rules:
            for point in points:
                if point.kind not in allowed_kinds:
                    allowed = ", ".join(sorted(kind.value for kind in allowed_kinds))
                    msg = f"{field_name} items must have kind in {{{allowed}}}"
                    raise ValueError(msg)
        return self


class KnowledgeResult(_UpdateProtectedAnalysisContract):
    schema_version: Literal["knowledge-result-v2"] = "knowledge-result-v2"
    content: KnowledgeContent
    evidence_registry: EvidenceRegistry
    provenance: KnowledgeProvenance

    @model_validator(mode="after")
    def _references_registered_evidence(self) -> KnowledgeResult:
        evidence_ids = {item.evidence_id for item in self.evidence_registry.items}
        reference_ids = [*self.content.summary_evidence_ids]
        reference_ids.extend(self.content.why_it_matters.evidence_ids)
        for points in (
            self.content.core_points,
            self.content.key_facts,
            self.content.important_concepts,
            self.content.key_arguments,
            self.content.counterpoints,
            self.content.product_opportunities,
            self.content.business_opportunities,
            self.content.actionable_directions,
            self.content.hypotheses_to_validate,
            self.content.action_recommendations,
            self.content.risks,
        ):
            for point in points:
                reference_ids.extend(point.evidence_ids)
        missing = sorted(set(reference_ids) - evidence_ids)
        if missing:
            msg = f"knowledge fields reference unknown evidence: {missing}"
            raise ValueError(msg)
        return self


class WeeklyKnowledgeSource(_UpdateProtectedAnalysisContract):
    video_id: str = Field(min_length=1, max_length=200, pattern=r"\S")
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=20)

    @field_validator("evidence_ids")
    @classmethod
    def _evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_unique_semantic_items(value, field_name="evidence_ids")


class WeeklyKnowledgePoint(_UpdateProtectedAnalysisContract):
    text: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    sources: tuple[WeeklyKnowledgeSource, ...] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def _unique_sources(self) -> WeeklyKnowledgePoint:
        video_ids = tuple(source.video_id for source in self.sources)
        if len(video_ids) != len(set(video_ids)):
            msg = "WeeklyKnowledgePoint source video_id values must be unique"
            raise ValueError(msg)
        return self


class WeeklyKnowledgeProvenance(_UpdateProtectedAnalysisContract):
    requested_mode: IntelligenceMode
    executed_mode: KnowledgeExecutionMode
    fallback_reason: KnowledgeFallbackReason | None = None
    provider: str = Field(min_length=1, max_length=200, pattern=r"\S")
    model: str = Field(min_length=1, max_length=300, pattern=r"\S")
    model_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    output_language: str = Field(min_length=1, max_length=40, pattern=r"\S")
    prompt_version: Literal["weekly-knowledge-prompt-v2"] = (
        "weekly-knowledge-prompt-v2"
    )
    schema_version: Literal["weekly-knowledge-result-v2"] = (
        "weekly-knowledge-result-v2"
    )
    sampling_version: Literal["weekly-knowledge-sampling-v2"] = (
        "weekly-knowledge-sampling-v2"
    )
    privacy_version: Literal["weekly-knowledge-privacy-v2"] = (
        "weekly-knowledge-privacy-v2"
    )
    input_knowledge_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _mode_and_model_identity(self) -> WeeklyKnowledgeProvenance:
        if (
            self.requested_mode is IntelligenceMode.LOCAL_ONLY
            and self.executed_mode is not KnowledgeExecutionMode.LOCAL
        ):
            msg = "local-only weekly synthesis must execute locally"
            raise ValueError(msg)
        if (
            self.requested_mode is IntelligenceMode.CLOUD
            and self.executed_mode is not KnowledgeExecutionMode.CLOUD
        ):
            msg = "cloud weekly synthesis must execute in cloud mode"
            raise ValueError(msg)
        if (
            self.requested_mode is IntelligenceMode.HYBRID
            and self.executed_mode is KnowledgeExecutionMode.LOCAL
        ) != (self.fallback_reason is not None):
            msg = (
                "fallback_reason is required only when hybrid weekly synthesis "
                "falls back to local execution"
            )
            raise ValueError(msg)
        if (
            self.executed_mode is KnowledgeExecutionMode.LOCAL
            and self.model_digest is None
        ):
            msg = "model_digest is required for local weekly synthesis"
            raise ValueError(msg)
        if (
            self.executed_mode is KnowledgeExecutionMode.CLOUD
            and self.model_digest is not None
        ):
            msg = "model_digest must be absent for cloud weekly synthesis"
            raise ValueError(msg)
        return self


class WeeklyKnowledgeContent(_UpdateProtectedAnalysisContract):
    key_conclusions: tuple[WeeklyKnowledgePoint, ...] = Field(min_length=1, max_length=5)
    repeated_themes: tuple[WeeklyKnowledgePoint, ...] = Field(default=(), max_length=10)
    supporting_views: tuple[WeeklyKnowledgePoint, ...] = Field(default=(), max_length=10)
    conflicting_views: tuple[WeeklyKnowledgePoint, ...] = Field(default=(), max_length=10)
    emerging_trends: tuple[WeeklyKnowledgePoint, ...] = Field(default=(), max_length=10)
    multiweek_themes: tuple[WeeklyKnowledgePoint, ...] = Field(default=(), max_length=10)
    product_opportunities: tuple[WeeklyKnowledgePoint, ...] = Field(default=(), max_length=10)
    business_opportunities: tuple[WeeklyKnowledgePoint, ...] = Field(default=(), max_length=10)
    next_week_questions: tuple[str, ...] = Field(default=(), max_length=10)
    must_watch_video_ids: tuple[str, ...] = Field(default=(), max_length=10)

    @field_validator("next_week_questions", "must_watch_video_ids")
    @classmethod
    def _unique_text_items(
        cls,
        value: tuple[str, ...],
        info: ValidationInfo,
    ) -> tuple[str, ...]:
        return _validate_unique_semantic_items(
            value,
            field_name=info.field_name or "weekly_items",
        )


class WeeklyKnowledgeResult(WeeklyKnowledgeContent):
    schema_version: Literal["weekly-knowledge-result-v2"] = (
        "weekly-knowledge-result-v2"
    )
    provenance: WeeklyKnowledgeProvenance


# ---------------------------------------------------------------------------
# Cross-module I/O objects
# ---------------------------------------------------------------------------


class DiagnosticEntry(_DomainModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=2000)


class ProviderCallMetadata(_DomainModel):
    provider: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime
    provider_version: str | None = None
    model: str | None = None
    diagnostics: tuple[DiagnosticEntry, ...] = ()

    @model_validator(mode="after")
    def _time_order(self) -> ProviderCallMetadata:
        if self.finished_at < self.started_at:
            msg = "finished_at must be >= started_at"
            raise ValueError(msg)
        return self


class AnalysisCompleted(_UpdateProtectedAnalysisContract):
    result: AnalysisResult
    call: ProviderCallMetadata

    @field_validator("call")
    @classmethod
    def _call_matches_result(
        cls,
        value: ProviderCallMetadata,
        info: ValidationInfo,
    ) -> ProviderCallMetadata:
        if not value.provider.strip():
            msg = "analysis call provider must be non-empty"
            raise ValueError(msg)
        if value.model is None or not value.model.strip():
            msg = "analysis call model must be non-empty"
            raise ValueError(msg)
        result = info.data.get("result")
        if isinstance(result, AnalysisResult):
            if result.provider != value.provider:
                msg = "analysis result provider must match call provider"
                raise ValueError(msg)
            if result.model != value.model:
                msg = "analysis result model must match call model"
                raise ValueError(msg)
        return value


class AnalysisSkipped(_UpdateProtectedAnalysisContract):
    reason: AnalysisSkipReason
    call: ProviderCallMetadata | None
    safe_message: str = Field(min_length=1, max_length=2000)

    @field_validator("safe_message")
    @classmethod
    def _safe_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "safe_message must be non-empty after strip"
            raise ValueError(msg)
        return stripped


AnalysisOutcome: TypeAlias = AnalysisCompleted | AnalysisSkipped


class DiscoveryCursor(_DomainModel):
    channel_id: str = Field(min_length=1)
    last_checked_at: datetime | None = None
    latest_published_at: datetime | None = None
    latest_video_id: str | None = None
    provider_cursor: str | None = None


class DiscoveryBatch(_DomainModel):
    channel_id: str = Field(min_length=1)
    video_ids: tuple[str, ...]
    next_cursor: DiscoveryCursor
    call: ProviderCallMetadata

    @field_validator("video_ids")
    @classmethod
    def _unique_video_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        for vid in value:
            if not vid:
                msg = "video_ids items must be non-empty"
                raise ValueError(msg)
            if vid in seen:
                msg = "video_ids must be unique while preserving order"
                raise ValueError(msg)
            seen.add(vid)
        return value


class _UpdateProtectedScoringContract(_DomainModel):
    """Preserve validation boundaries for shared scoring contracts."""

    def model_copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            msg = "model_copy(update=...) is disabled for scoring contracts"
            raise ValueError(msg)
        return super().model_copy(deep=deep)


class TranscriptSample(_UpdateProtectedScoringContract):
    """A bounded, ordered selection from one canonical transcript.

    The scoring service owns the ``sampling-v1`` slicing algorithm. This contract
    preserves its selected segments and binds them to the full canonical content
    hash so a sample cannot be reused for different transcript content.
    """

    head: str = Field(min_length=1)
    body: str = ""
    tail: str = ""
    selected_char_count: int = Field(ge=3)
    source_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    sampling_version: Literal["sampling-v1"] = "sampling-v1"

    @model_validator(mode="after")
    def _selected_character_count_matches_segments(self) -> TranscriptSample:
        if self.selected_char_count != len(self.head) + len(self.body) + len(self.tail):
            msg = "selected_char_count must equal the total selected sample characters"
            raise ValueError(msg)
        return self


class ScoringInput(_UpdateProtectedScoringContract):
    video: VideoMetadata
    sample: TranscriptSample
    transcript_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    language: str = Field(min_length=1)
    output_language: ScoringOutputLanguage
    request_hash: str = Field(min_length=1)

    @model_validator(mode="after")
    def _sample_binds_to_full_transcript(self) -> ScoringInput:
        if self.sample.source_content_hash != self.transcript_content_hash:
            msg = "transcript_content_hash must match sample.source_content_hash"
            raise ValueError(msg)
        return self


class ScoringDecision(_UpdateProtectedScoringContract):
    threshold: float = Field(ge=0, le=10)
    final_should_summarize: bool
    model_disagrees: bool


class ScoringOutcome(_UpdateProtectedScoringContract):
    result: ScoreResult
    decision: ScoringDecision
    call: ProviderCallMetadata

    @model_validator(mode="after")
    def _final_decision_is_derived_from_score(self) -> ScoringOutcome:
        expected_final = self.result.score >= self.decision.threshold
        if self.decision.final_should_summarize is not expected_final:
            msg = "final_should_summarize must equal score >= threshold"
            raise ValueError(msg)
        expected_disagreement = (
            self.result.should_summarize != self.decision.final_should_summarize
        )
        if self.decision.model_disagrees is not expected_disagreement:
            msg = "model_disagrees must equal model suggestion disagreement"
            raise ValueError(msg)
        return self


class AnalysisInput(_UpdateProtectedAnalysisContract):
    payload: AnalysisPayload
    transcript_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_version: Literal["analysis-prompt-v1"] = "analysis-prompt-v1"
    schema_version: Literal["analysis-result-v1"] = "analysis-result-v1"
    sampling_version: Literal["cloud-token-sampling-v1"] = "cloud-token-sampling-v1"
    privacy_version: Literal["cloud-privacy-v1"] = "cloud-privacy-v1"


class NotAvailable(_DomainModel):
    reason_code: NotAvailableReason
    message: str = Field(min_length=1, max_length=2000)
    retryable: bool
    call: ProviderCallMetadata
    retry_after_seconds: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _retry_after_consistency(self) -> NotAvailable:
        if self.retry_after_seconds is not None and not self.retryable:
            msg = "retry_after_seconds requires retryable=True"
            raise ValueError(msg)
        return self


class TranscriptReady(_DomainModel):
    outcome: Literal["ready"] = "ready"
    artifact: TranscriptArtifact
    call: ProviderCallMetadata


class TranscriptionRequired(_DomainModel):
    outcome: Literal["transcription_required"] = "transcription_required"
    reason: TranscriptionReason
    call: ProviderCallMetadata
    attempted_track_count: int = Field(ge=0)


TranscriptFetchResult: TypeAlias = TranscriptReady | TranscriptionRequired


class _UpdateProtectedNoteRef(_DomainModel):
    """Prevent callers from bypassing NoteRef identity validation."""

    def model_copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            msg = "model_copy(update=...) is disabled for NoteRef"
            raise ValueError(msg)
        return super().model_copy(deep=deep)


class NoteRef(_UpdateProtectedNoteRef):
    kind: NoteKind
    relative_path: str = Field(min_length=1)
    content_hash: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )

    @field_validator("relative_path")
    @classmethod
    def _safe_relative_path(cls, value: str) -> str:
        if not value or value.strip() != value:
            msg = "relative_path must be non-empty without surrounding whitespace"
            raise ValueError(msg)
        if "\x00" in value or "\\" in value:
            msg = "relative_path must be a safe relative path under the vault"
            raise ValueError(msg)
        if len(value) >= 2 and value[0].isalpha() and value[1] == ":":
            msg = "relative_path must not include a drive prefix"
            raise ValueError(msg)
        path = PurePosixPath(value)
        if path.is_absolute() or any(
            not part or part in {".", ".."} for part in value.split("/")
        ):
            msg = "relative_path must be a canonical relative path"
            raise ValueError(msg)
        if not value.endswith(".md"):
            msg = "relative_path must end in .md"
            raise ValueError(msg)
        return value


class WeeklyReportItem(_DomainModel):
    video: VideoMetadata
    score: ScoreResult
    note_ref: NoteRef
    one_sentence_summary: str = Field(min_length=1, max_length=500)


class WeeklyReportInput(_DomainModel):
    iso_year: int = Field(ge=1)
    iso_week: int = Field(ge=1, le=53)
    timezone: str = Field(min_length=1)
    items: tuple[WeeklyReportItem, ...]
    generated_at: datetime

    @model_validator(mode="after")
    def _items_sorted(self) -> WeeklyReportInput:
        expected = tuple(
            sorted(
                self.items,
                key=lambda item: (-item.score.score, item.video.video_id),
            )
        )
        if self.items != expected:
            msg = "items must be sorted by score desc then video_id asc"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Channel (domain view used by SourceProvider)
# ---------------------------------------------------------------------------


class ChannelRef(_DomainModel):
    channel_id: str = Field(min_length=1)
    enabled: bool = True
    priority: int = Field(default=50, ge=0, le=100)


# ---------------------------------------------------------------------------
# State transition helpers
# ---------------------------------------------------------------------------


class InvalidTransitionError(Exception):
    """Raised when a pipeline or job transition is not allowed.

    Not mapped to a dedicated ErrorCode: System Design §12 does not freeze an
    INVALID_TRANSITION code. Callers may treat this as a programming/contract error.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def can_transition_pipeline(current: PipelineStatus, target: PipelineStatus) -> bool:
    return target in PIPELINE_TRANSITIONS.get(current, frozenset())


def transition_pipeline(current: PipelineStatus, target: PipelineStatus) -> PipelineStatus:
    if not can_transition_pipeline(current, target):
        raise InvalidTransitionError(
            f"illegal pipeline transition: {current.value} -> {target.value}"
        )
    return target


def can_transition_job(current: JobStatus, target: JobStatus) -> bool:
    return target in JOB_TRANSITIONS.get(current, frozenset())


def transition_job(current: JobStatus, target: JobStatus) -> JobStatus:
    if not can_transition_job(current, target):
        raise InvalidTransitionError(
            f"illegal job transition: {current.value} -> {target.value}"
        )
    return target


def pipeline_after_job_failure(
    pipeline_status: PipelineStatus,
    job_status: JobStatus,
) -> PipelineStatus:
    """Failed or retrying jobs do not change the video's last successful pipeline status.

    C-07 recovery stage identity is expressed by ``ProcessingStage`` (Job target stage
    enum). This task does not freeze a Job aggregate with a ``target_stage`` field;
    persistence of that field is TASK-003 scope.
    """
    if job_status not in {JobStatus.RETRY_PENDING, JobStatus.FAILED_FINAL}:
        raise InvalidTransitionError(
            "pipeline_after_job_failure only applies to RETRY_PENDING or FAILED_FINAL"
        )
    return pipeline_status


# ---------------------------------------------------------------------------
# Provider protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class SourceProvider(Protocol):
    def discover(self, channel: ChannelRef, cursor: DiscoveryCursor) -> DiscoveryBatch: ...


@runtime_checkable
class MetadataProvider(Protocol):
    def fetch(self, video_id: str) -> VideoMetadata: ...


@runtime_checkable
class TranscriptProvider(Protocol):
    def fetch(
        self,
        video: VideoMetadata,
        language_preferences: Sequence[str],
    ) -> TranscriptFetchResult: ...


@runtime_checkable
class ScoringProvider(Protocol):
    def score(self, scoring_input: ScoringInput) -> ScoreResult: ...


@runtime_checkable
class SummaryProvider(Protocol):
    def summarize(self, analysis_input: AnalysisInput) -> AnalysisResult: ...


class KnowledgeSink(ABC):
    def upsert_video_note(
        self,
        *,
        video: VideoMetadata,
        transcript: TranscriptArtifact,
        scoring: ScoringOutcome,
        analysis: AnalysisOutcome,
        processed_at: datetime,
        pipeline_version: str,
    ) -> NoteRef:
        """Validate the shared note boundary before delegating to a sink adapter."""
        if (
            not isinstance(processed_at, datetime)
            or processed_at.tzinfo is None
            or processed_at.utcoffset() != timedelta(0)
        ):
            msg = "processed_at must be a UTC-aware datetime"
            raise ValueError(msg)
        if (
            not isinstance(pipeline_version, str)
            or not pipeline_version
            or pipeline_version.strip() != pipeline_version
        ):
            msg = "pipeline_version must be non-empty without surrounding whitespace"
            raise ValueError(msg)
        if (
            not isinstance(scoring, ScoringOutcome)
            or not scoring.decision.final_should_summarize
        ):
            msg = "KnowledgeSink requires a final high-value ScoringOutcome"
            raise ValueError(msg)
        return self._upsert_video_note(
            video=video,
            transcript=transcript,
            scoring=scoring,
            analysis=analysis,
            processed_at=processed_at,
            pipeline_version=pipeline_version,
        )

    @abstractmethod
    def _upsert_video_note(
        self,
        *,
        video: VideoMetadata,
        transcript: TranscriptArtifact,
        scoring: ScoringOutcome,
        analysis: AnalysisOutcome,
        processed_at: datetime,
        pipeline_version: str,
    ) -> NoteRef:
        """Write a validated video note without bypassing ``upsert_video_note``."""

    @abstractmethod
    def upsert_weekly_report(self, report: WeeklyReportInput) -> NoteRef: ...


# ---------------------------------------------------------------------------
# Content Quality Layer contracts (TASK-016C Phase A)
# ---------------------------------------------------------------------------

# Phase A only establishes the domain contracts and candidate boundary.
# Deterministic Gate, Local Quality Judge, H1/H2 persistence, attestation,
# finalizer, write-plan, artifact persistence and repair orchestration are
# intentionally out of scope.


class ContentQualityStatus(str, Enum):
    PASS = "PASS"
    REJECT = "REJECT"
    UNCERTAIN = "UNCERTAIN"


class ContentQualityDecisionSource(str, Enum):
    DETERMINISTIC_GATE = "DETERMINISTIC_GATE"
    LOCAL_JUDGE = "LOCAL_JUDGE"


class ContentQualityConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ContentQualitySignal(str, Enum):
    IDENTIFIER_ONLY = "IDENTIFIER_ONLY"
    ENTITY_ONLY = "ENTITY_ONLY"
    LOW_INFORMATION = "LOW_INFORMATION"
    MINIMAL_CLAIM_PRESENT = "MINIMAL_CLAIM_PRESENT"
    MINIMAL_CLAIM_MISSING = "MINIMAL_CLAIM_MISSING"
    GROUNDING_PRESENT = "GROUNDING_PRESENT"
    GROUNDING_INSUFFICIENT = "GROUNDING_INSUFFICIENT"
    JUDGE_UNAVAILABLE = "JUDGE_UNAVAILABLE"
    JUDGE_INVALID_RESPONSE = "JUDGE_INVALID_RESPONSE"


class ContentQualityReason(str, Enum):
    IDENTIFIER_ONLY = "IDENTIFIER_ONLY"
    ENTITY_ONLY = "ENTITY_ONLY"
    LOW_INFORMATION = "LOW_INFORMATION"
    MINIMAL_CLAIM_MISSING = "MINIMAL_CLAIM_MISSING"
    GROUNDING_INSUFFICIENT = "GROUNDING_INSUFFICIENT"
    JUDGE_UNAVAILABLE = "JUDGE_UNAVAILABLE"
    JUDGE_INVALID_RESPONSE = "JUDGE_INVALID_RESPONSE"


class DeterministicGateReason(str, Enum):
    EMPTY_CONTENT = "EMPTY_CONTENT"
    CONTROL_CHARACTER_INVALID = "CONTROL_CHARACTER_INVALID"
    EXACT_REPETITION = "EXACT_REPETITION"


class QualityJudgeAttemptRole(str, Enum):
    PRIMARY = "PRIMARY"
    REPAIR = "REPAIR"


class ScoringEvidenceSource(str, Enum):
    TITLE = "TITLE"
    DESCRIPTION = "DESCRIPTION"
    TRANSCRIPT_HEAD = "TRANSCRIPT_HEAD"
    TRANSCRIPT_BODY = "TRANSCRIPT_BODY"
    TRANSCRIPT_TAIL = "TRANSCRIPT_TAIL"


_PASS_SIGNALS: Final[frozenset[ContentQualitySignal]] = frozenset(
    {ContentQualitySignal.MINIMAL_CLAIM_PRESENT, ContentQualitySignal.GROUNDING_PRESENT}
)

_NEGATIVE_SIGNALS: Final[frozenset[ContentQualitySignal]] = frozenset(
    {
        ContentQualitySignal.IDENTIFIER_ONLY,
        ContentQualitySignal.ENTITY_ONLY,
        ContentQualitySignal.LOW_INFORMATION,
        ContentQualitySignal.MINIMAL_CLAIM_MISSING,
        ContentQualitySignal.GROUNDING_INSUFFICIENT,
        ContentQualitySignal.JUDGE_UNAVAILABLE,
        ContentQualitySignal.JUDGE_INVALID_RESPONSE,
    }
)

_CONTENT_REJECT_REASONS: Final[frozenset[ContentQualityReason]] = frozenset(
    {
        ContentQualityReason.IDENTIFIER_ONLY,
        ContentQualityReason.ENTITY_ONLY,
        ContentQualityReason.LOW_INFORMATION,
        ContentQualityReason.MINIMAL_CLAIM_MISSING,
    }
)

_UNCERTAIN_REASONS: Final[frozenset[ContentQualityReason]] = frozenset(
    {
        ContentQualityReason.GROUNDING_INSUFFICIENT,
        ContentQualityReason.JUDGE_UNAVAILABLE,
        ContentQualityReason.JUDGE_INVALID_RESPONSE,
    }
)

# Evidence registry bounds are derived from the frozen per-item limits above
# and the existing project registry pattern (max 100 items).
_MAX_EVIDENCE_ID_LENGTH: Final[int] = 100
_MAX_EVIDENCE_EXCERPT_LENGTH: Final[int] = 2000
_MAX_EVIDENCE_REGISTRY_ITEMS: Final[int] = 100
_MAX_EVIDENCE_REGISTRY_TOTAL_CHARS: Final[int] = (
    _MAX_EVIDENCE_REGISTRY_ITEMS * _MAX_EVIDENCE_EXCERPT_LENGTH
)


def _validate_evidence_identity(value: str) -> str:
    if not value or not value.strip():
        msg = "evidence_id must be non-empty"
        raise ValueError(msg)
    if len(value) > _MAX_EVIDENCE_ID_LENGTH:
        msg = f"evidence_id must be at most {_MAX_EVIDENCE_ID_LENGTH} characters"
        raise ValueError(msg)
    return value


class _UpdateProtectedQualityContract(_DomainModel):
    """Prevent callers from bypassing content-quality validation boundaries."""

    def model_copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            msg = "model_copy(update=...) is disabled for content-quality contracts"
            raise ValueError(msg)
        return super().model_copy(deep=deep)

    @no_type_check
    def copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
        **kwargs: Never,
    ) -> Self:
        if update is not None:
            msg = "copy(update=...) is disabled for content-quality contracts"
            raise ValueError(msg)
        return super().copy(update=None, deep=deep, **kwargs)


class ScoringCandidate(_UpdateProtectedScoringContract):
    """Untrusted scoring candidate returned by a Provider Adapter.

    ``ScoringCandidate`` preserves the existing ``ScoreResult`` business fields
    but carries no trusted provenance.  It must be finalized through the
    ``TrustedScoringFinalizer`` boundary before it becomes a trusted result.
    """

    score: float = Field(ge=0, le=10, allow_inf_nan=False)
    reason: str = Field(min_length=1, max_length=2000)
    topics: tuple[str, ...] = Field(min_length=1, max_length=10)
    should_summarize: bool
    dimensions: ScoreDimensions | None = None

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "reason must be non-empty after strip"
            raise ValueError(msg)
        if len(stripped) > 2000:
            msg = "reason must be at most 2000 characters after strip"
            raise ValueError(msg)
        return stripped

    @field_validator("topics")
    @classmethod
    def _validate_topics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            msg = "topics must contain at least one item"
            raise ValueError(msg)
        if len(value) > 10:
            msg = "topics must contain at most 10 items"
            raise ValueError(msg)
        seen: set[str] = set()
        for topic in value:
            if not 1 <= len(topic) <= 80:
                msg = "each topic must have length 1..80"
                raise ValueError(msg)
            if topic in seen:
                msg = "topics must be unique"
                raise ValueError(msg)
            seen.add(topic)
        return value


class ScoringEvidence(_UpdateProtectedQualityContract):
    """One evidence entry in the content-quality input registry."""

    evidence_id: str = Field(
        min_length=1, max_length=_MAX_EVIDENCE_ID_LENGTH, pattern=r"\S"
    )
    source: ScoringEvidenceSource
    excerpt: str = Field(
        min_length=1, max_length=_MAX_EVIDENCE_EXCERPT_LENGTH, pattern=r"\S"
    )

    @field_validator("evidence_id")
    @classmethod
    def _validate_evidence_id(cls, value: str) -> str:
        return _validate_evidence_identity(value)


class ContentQualityInput(_UpdateProtectedQualityContract):
    """Trusted binding contract between a scoring candidate and its evidence."""

    scoring_request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_language: ScoringOutputLanguage
    reason: str = Field(min_length=1, max_length=2000)
    topics: tuple[str, ...] = Field(min_length=1, max_length=10)
    evidence_registry: tuple[ScoringEvidence, ...]
    policy_version: Literal["content-quality-policy-v1"] = "content-quality-policy-v1"

    @field_validator("evidence_registry")
    @classmethod
    def _canonical_registry(
        cls,
        value: tuple[ScoringEvidence, ...],
    ) -> tuple[ScoringEvidence, ...]:
        seen: set[str] = set()
        total_chars = 0
        for item in value:
            eid = item.evidence_id
            if eid in seen:
                msg = f"duplicate evidence_id in registry: {eid}"
                raise ValueError(msg)
            seen.add(eid)
            total_chars += len(eid) + len(item.excerpt)
        if len(value) > _MAX_EVIDENCE_REGISTRY_ITEMS:
            msg = (
                f"evidence_registry must contain at most "
                f"{_MAX_EVIDENCE_REGISTRY_ITEMS} items"
            )
            raise ValueError(msg)
        if total_chars > _MAX_EVIDENCE_REGISTRY_TOTAL_CHARS:
            msg = (
                f"evidence_registry total characters must be at most "
                f"{_MAX_EVIDENCE_REGISTRY_TOTAL_CHARS}"
            )
            raise ValueError(msg)
        return tuple(sorted(value, key=lambda item: item.evidence_id))

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "reason must be non-empty after strip"
            raise ValueError(msg)
        if len(stripped) > 2000:
            msg = "reason must be at most 2000 characters after strip"
            raise ValueError(msg)
        return stripped

    @field_validator("topics")
    @classmethod
    def _validate_topics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            msg = "topics must contain at least one item"
            raise ValueError(msg)
        if len(value) > 10:
            msg = "topics must contain at most 10 items"
            raise ValueError(msg)
        seen: set[str] = set()
        for topic in value:
            if not 1 <= len(topic) <= 80:
                msg = "each topic must have length 1..80"
                raise ValueError(msg)
            if topic in seen:
                msg = "topics must be unique"
                raise ValueError(msg)
            seen.add(topic)
        return value


class ContentQualityResult(_UpdateProtectedQualityContract):
    """Validated content-quality decision with frozen cross-field invariants.

    The model normalizes ``signals`` and ``evidence_ids`` to a deterministic
    canonical order and then enforces the approved status/reason/signal
    matrix.  Any unchecked construction, copy or JSON restore must be passed
    through ``validate_content_quality_result`` before it is trusted.
    """

    schema_version: Literal["content-quality-result-v1"] = "content-quality-result-v1"
    policy_version: Literal["content-quality-policy-v1"] = "content-quality-policy-v1"
    prompt_version: Literal["content-quality-prompt-v1"] = "content-quality-prompt-v1"
    status: ContentQualityStatus
    decision_source: ContentQualityDecisionSource
    decision_confidence: ContentQualityConfidence
    grounding_confidence: ContentQualityConfidence
    usefulness_confidence: ContentQualityConfidence
    signals: tuple[ContentQualitySignal, ...]
    reason: DeterministicGateReason | ContentQualityReason | None = None
    evidence_ids: tuple[str, ...] = ()
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    scoring_request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    judge_provider: Literal["ollama"] | None = None
    judge_model: str | None = None
    judge_model_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )

    @field_validator("signals")
    @classmethod
    def _canonical_signals(
        cls,
        value: tuple[ContentQualitySignal, ...],
    ) -> tuple[ContentQualitySignal, ...]:
        return tuple(sorted(frozenset(value), key=lambda s: s.value))

    @field_validator("evidence_ids")
    @classmethod
    def _canonical_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        for eid in value:
            _validate_evidence_identity(eid)
            if eid in seen:
                msg = "evidence_ids must be unique"
                raise ValueError(msg)
            seen.add(eid)
        return tuple(sorted(value))

    @model_validator(mode="after")
    def _cross_field_integrity(self) -> ContentQualityResult:
        self._validate_source_judge_consistency()
        if self.decision_source is ContentQualityDecisionSource.DETERMINISTIC_GATE:
            self._validate_gate_reject_matrix()
        elif self.status is ContentQualityStatus.PASS:
            self._validate_pass_matrix()
        elif self.status is ContentQualityStatus.REJECT:
            self._validate_reject_matrix()
        elif self.status is ContentQualityStatus.UNCERTAIN:
            self._validate_uncertain_matrix()
        return self

    def _validate_source_judge_consistency(self) -> None:
        judge_fields = (self.judge_provider, self.judge_model, self.judge_model_digest)
        if self.decision_source is ContentQualityDecisionSource.DETERMINISTIC_GATE:
            if self.status is not ContentQualityStatus.REJECT:
                msg = "DETERMINISTIC_GATE can only produce REJECT"
                raise ValueError(msg)
            if not isinstance(self.reason, DeterministicGateReason):
                msg = "DETERMINISTIC_GATE requires a deterministic reason"
                raise ValueError(msg)
            if self.signals:
                msg = "DETERMINISTIC_GATE result must have empty signals"
                raise ValueError(msg)
            if self.evidence_ids:
                msg = "DETERMINISTIC_GATE result must have empty evidence_ids"
                raise ValueError(msg)
            if any(field is not None for field in judge_fields):
                msg = "DETERMINISTIC_GATE result must have empty Judge identity"
                raise ValueError(msg)
            if (
                self.decision_confidence is not ContentQualityConfidence.HIGH
                or self.grounding_confidence is not ContentQualityConfidence.LOW
                or self.usefulness_confidence is not ContentQualityConfidence.LOW
            ):
                msg = "DETERMINISTIC_GATE confidence must be HIGH/LOW/LOW"
                raise ValueError(msg)
            return

        if self.decision_source is not ContentQualityDecisionSource.LOCAL_JUDGE:
            msg = "decision_source must be DETERMINISTIC_GATE or LOCAL_JUDGE"
            raise ValueError(msg)

        if any(field is None or field == "" for field in judge_fields):
            msg = "LOCAL_JUDGE result requires complete Judge identity"
            raise ValueError(msg)

    def _validate_gate_reject_matrix(self) -> None:
        # Source consistency already enforces the Gate path; this method exists
        # to make the source-specific dispatch explicit and to prevent future
        # edits from accidentally falling through to the Judge matrix.
        if self.status is not ContentQualityStatus.REJECT:
            msg = "DETERMINISTIC_GATE can only produce REJECT"
            raise ValueError(msg)
        if not isinstance(self.reason, DeterministicGateReason):
            msg = "DETERMINISTIC_GATE requires a deterministic reason"
            raise ValueError(msg)

    def _validate_pass_matrix(self) -> None:
        if self.decision_confidence is not ContentQualityConfidence.HIGH:
            msg = "PASS requires decision_confidence=HIGH"
            raise ValueError(msg)
        if self.grounding_confidence not in {
            ContentQualityConfidence.MEDIUM,
            ContentQualityConfidence.HIGH,
        }:
            msg = "PASS requires grounding_confidence>=MEDIUM"
            raise ValueError(msg)
        if self.usefulness_confidence not in {
            ContentQualityConfidence.MEDIUM,
            ContentQualityConfidence.HIGH,
        }:
            msg = "PASS requires usefulness_confidence>=MEDIUM"
            raise ValueError(msg)
        if self.reason is not None:
            msg = "PASS must not have a rejection reason"
            raise ValueError(msg)
        if not _PASS_SIGNALS.issubset(self.signals):
            msg = "PASS requires MINIMAL_CLAIM_PRESENT and GROUNDING_PRESENT"
            raise ValueError(msg)
        if _NEGATIVE_SIGNALS.intersection(self.signals):
            msg = "PASS must not contain negative signals"
            raise ValueError(msg)
        if not self.evidence_ids:
            msg = "PASS requires at least one evidence_id"
            raise ValueError(msg)

    def _validate_reject_matrix(self) -> None:
        if self.decision_confidence is not ContentQualityConfidence.HIGH:
            msg = "REJECT requires decision_confidence=HIGH"
            raise ValueError(msg)
        if self.reason is None:
            msg = "REJECT requires a reason"
            raise ValueError(msg)
        if self.reason in {
            ContentQualityReason.JUDGE_UNAVAILABLE,
            ContentQualityReason.JUDGE_INVALID_RESPONSE,
        }:
            msg = "REJECT may not use an UNCERTAIN-only reason"
            raise ValueError(msg)
        if self.reason not in set(ContentQualityReason):
            msg = "REJECT reason is not an approved Judge reason"
            raise ValueError(msg)

        expected_signal = ContentQualitySignal(self.reason.value)
        if expected_signal not in self.signals:
            msg = "REJECT must include the signal matching its reason"
            raise ValueError(msg)

        if self.reason is ContentQualityReason.GROUNDING_INSUFFICIENT:
            if self.grounding_confidence is not ContentQualityConfidence.LOW:
                msg = "GROUNDING_INSUFFICIENT REJECT requires grounding_confidence=LOW"
                raise ValueError(msg)
            if ContentQualitySignal.GROUNDING_PRESENT in self.signals:
                msg = "GROUNDING_INSUFFICIENT REJECT must not claim GROUNDING_PRESENT"
                raise ValueError(msg)
        else:
            if self.grounding_confidence not in {
                ContentQualityConfidence.LOW,
                ContentQualityConfidence.MEDIUM,
            }:
                msg = "content REJECT requires grounding_confidence in {LOW,MEDIUM}"
                raise ValueError(msg)
            if self.usefulness_confidence is not ContentQualityConfidence.LOW:
                msg = "content REJECT requires usefulness_confidence=LOW"
                raise ValueError(msg)

        if _PASS_SIGNALS.issubset(self.signals):
            msg = "REJECT must not claim complete PASS signals"
            raise ValueError(msg)

    def _validate_uncertain_matrix(self) -> None:
        if (
            self.decision_confidence is not ContentQualityConfidence.LOW
            or self.grounding_confidence is not ContentQualityConfidence.LOW
            or self.usefulness_confidence is not ContentQualityConfidence.LOW
        ):
            msg = "UNCERTAIN requires all confidences=LOW"
            raise ValueError(msg)
        if self.reason not in _UNCERTAIN_REASONS:
            msg = "UNCERTAIN requires an approved uncertain reason"
            raise ValueError(msg)
        expected_signal = ContentQualitySignal(self.reason.value)
        if expected_signal not in self.signals:
            msg = "UNCERTAIN must include the signal matching its reason"
            raise ValueError(msg)
        if _PASS_SIGNALS.issubset(self.signals):
            msg = "UNCERTAIN must not claim complete PASS signals"
            raise ValueError(msg)


class QualityJudgeOperationInput(_UpdateProtectedQualityContract):
    """Stable normalized input identity for a single quality Judge attempt.

    Trusted identity must never rely on a mutable instance marker.  This class
    therefore disables ``model_construct`` and rejects any attempt to treat an
    unchecked or mutated instance as validated.  Callers that need an identity
    must pass the instance to ``build_judge_h1_h2``, which reconstructs the
    input from its raw field dictionary through a fresh validation pass.
    """

    scoring_request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    attempt_role: QualityJudgeAttemptRole
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    judge_provider: str = Field(min_length=1)
    judge_model: str = Field(min_length=1)
    judge_model_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @classmethod
    def model_construct(
        cls,
        _fields_set: set[str] | None = None,
        **values: Any,
    ) -> Self:
        msg = (
            "QualityJudgeOperationInput.model_construct is disabled; "
            "use model_validate or normal construction"
        )
        raise ValueError(msg)

    @no_type_check
    def copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
        **kwargs: Never,
    ) -> Self:
        if update is not None:
            msg = "copy(update=...) is disabled for QualityJudgeOperationInput"
            raise ValueError(msg)
        return super().copy(update=None, deep=deep, **kwargs)

    def model_post_init(self, __context: Mapping[str, str]) -> None:
        super().model_post_init(__context)


class QualityPassAttestation(_UpdateProtectedQualityContract):
    """Application-created attestation binding a validated quality PASS to its
    full identity context.

    Only the application — never a provider, model, cache, artifact, or caller —
    creates this object via the trusted constructor in ``quality.py``.  The
    attestation is *not* a second PASS decision: its confidence and Evidence-ID
    fields are exact mirrors of the validated ``ContentQualityResult(PASS)``.
    ``attestation_hash`` is SHA-256 of the complete canonical payload excluding
    only itself.
    """

    attestation_schema: Literal["quality-pass-attestation-v1"] = (
        "quality-pass-attestation-v1"
    )
    status: Literal[ContentQualityStatus.PASS]
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    scoring_request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: Literal["content-quality-policy-v1"] = (
        "content-quality-policy-v1"
    )
    scoring_schema_version: str = Field(min_length=1)
    scoring_prompt_version: str = Field(min_length=1)
    quality_schema_version: Literal["content-quality-result-v1"] = (
        "content-quality-result-v1"
    )
    quality_prompt_version: Literal["content-quality-prompt-v1"] = (
        "content-quality-prompt-v1"
    )
    judge_provider: Literal["ollama"] = "ollama"
    judge_model: str = Field(min_length=1)
    judge_model_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    judge_operation: Literal["local-content-quality-v1"] = (
        "local-content-quality-v1"
    )
    judge_request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    attempt_role: QualityJudgeAttemptRole
    decision_confidence: Literal[ContentQualityConfidence.HIGH]
    grounding_confidence: Literal[
        ContentQualityConfidence.MEDIUM, ContentQualityConfidence.HIGH
    ]
    usefulness_confidence: Literal[
        ContentQualityConfidence.MEDIUM, ContentQualityConfidence.HIGH
    ]
    evidence_ids: tuple[str, ...]
    attestation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("evidence_ids")
    @classmethod
    def _canonical_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        for eid in value:
            _validate_evidence_identity(eid)
            if eid in seen:
                msg = "evidence_ids must be unique"
                raise ValueError(msg)
            seen.add(eid)
        return tuple(sorted(value))

    @classmethod
    def model_construct(
        cls,
        _fields_set: set[str] | None = None,
        **values: Any,
    ) -> Self:
        msg = (
            "QualityPassAttestation.model_construct is disabled; "
            "use model_validate or the trusted constructor"
        )
        raise ValueError(msg)

    @no_type_check
    def copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
        **kwargs: Never,
    ) -> Self:
        if update is not None:
            msg = "copy(update=...) is disabled for QualityPassAttestation"
            raise ValueError(msg)
        return super().copy(update=None, deep=deep, **kwargs)


class ContentQualityJudgeResponse(_UpdateProtectedQualityContract):
    """Validated raw response contract from the local content-quality Judge.

    This model intentionally excludes provenance fields (candidate/input hashes,
    Judge identity, decision source).  Those are supplied by the caller when the
    response is promoted to a trusted ``ContentQualityResult``.
    """

    status: ContentQualityStatus
    decision_confidence: ContentQualityConfidence
    grounding_confidence: ContentQualityConfidence
    usefulness_confidence: ContentQualityConfidence
    signals: tuple[ContentQualitySignal, ...]
    reason: ContentQualityReason | None = None
    evidence_ids: tuple[str, ...] = ()

    @field_validator("signals")
    @classmethod
    def _canonical_signals(
        cls,
        value: tuple[ContentQualitySignal, ...],
    ) -> tuple[ContentQualitySignal, ...]:
        seen: set[ContentQualitySignal] = set()
        for signal in value:
            if signal in seen:
                msg = "signals must be unique"
                raise ValueError(msg)
            seen.add(signal)
        return tuple(sorted(value, key=lambda s: s.value))

    @field_validator("evidence_ids")
    @classmethod
    def _canonical_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        for eid in value:
            _validate_evidence_identity(eid)
            if eid in seen:
                msg = "evidence_ids must be unique"
                raise ValueError(msg)
            seen.add(eid)
        return tuple(sorted(value))


def validate_scoring_candidate(value) -> ScoringCandidate:  # type: ignore[no-untyped-def]
    """Revalidate an untrusted scoring candidate even if it is already a model.

    Provider, cache and Artifact boundaries treat model instances as data and
    rebuild them through the complete schema validators.
    """

    candidate = (
        value.model_dump(mode="python") if isinstance(value, ScoringCandidate) else value
    )
    return ScoringCandidate.model_validate(candidate)


def validate_scoring_candidate_json(value: str | bytes | bytearray) -> ScoringCandidate:
    """Parse persisted JSON and apply the same trusted candidate validation."""

    return validate_scoring_candidate(ScoringCandidate.model_validate_json(value))


def validate_content_quality_result(value) -> ContentQualityResult:  # type: ignore[no-untyped-def]
    """Revalidate an untrusted quality result even if it is already a model."""

    candidate = (
        value.model_dump(mode="python")
        if isinstance(value, ContentQualityResult)
        else value
    )
    return ContentQualityResult.model_validate(candidate)


def validate_content_quality_result_json(
    value: str | bytes | bytearray,
) -> ContentQualityResult:
    """Parse persisted JSON and apply the same trusted quality validation."""

    return validate_content_quality_result(ContentQualityResult.model_validate_json(value))



# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "SCORE_DIMENSION_NAMES",
    "PIPELINE_TRANSITIONS",
    "JOB_TRANSITIONS",
    "LiveStatus",
    "Availability",
    "TranscriptSourceType",
    "SubtitleFormat",
    "TranscriptQualityFlag",
    "TranscriptionReason",
    "PointKind",
    "IntelligenceMode",
    "KnowledgeExecutionMode",
    "KnowledgeFallbackReason",
    "EvidenceSource",
    "AnalysisSkipReason",
    "NotAvailableReason",
    "NoteKind",
    "PipelineStatus",
    "ProcessingStage",
    "JobStatus",
    "ErrorCode",
    "AppError",
    "VideoMetadata",
    "TranscriptArtifact",
    "ScoreDimensions",
    "ScoreResult",
    "ScoringCandidate",
    "ContentQualityStatus",
    "ContentQualityDecisionSource",
    "ContentQualityConfidence",
    "ContentQualitySignal",
    "ContentQualityReason",
    "DeterministicGateReason",
    "ScoringEvidence",
    "ScoringEvidenceSource",
    "ContentQualityInput",
    "ContentQualityResult",
    "QualityJudgeAttemptRole",
    "QualityJudgeOperationInput",
    "QualityPassAttestation",
    "ContentQualityJudgeResponse",
    "validate_scoring_candidate",
    "validate_scoring_candidate_json",
    "validate_content_quality_result",
    "validate_content_quality_result_json",
    "AnalysisPayload",
    "EvidenceExcerpt",
    "AnalysisPoint",
    "AnalysisContent",
    "AnalysisResult",
    "KnowledgeEvidence",
    "EvidenceRegistry",
    "KnowledgeGraph",
    "KnowledgeProvenance",
    "KnowledgeContent",
    "KnowledgeResult",
    "WeeklyKnowledgeSource",
    "WeeklyKnowledgePoint",
    "WeeklyKnowledgeProvenance",
    "WeeklyKnowledgeContent",
    "WeeklyKnowledgeResult",
    "DiagnosticEntry",
    "ProviderCallMetadata",
    "AnalysisCompleted",
    "AnalysisSkipped",
    "AnalysisOutcome",
    "DiscoveryCursor",
    "DiscoveryBatch",
    "TranscriptSample",
    "ScoringInput",
    "ScoringDecision",
    "ScoringOutcome",
    "AnalysisInput",
    "NotAvailable",
    "TranscriptReady",
    "TranscriptionRequired",
    "TranscriptFetchResult",
    "NoteRef",
    "WeeklyReportItem",
    "WeeklyReportInput",
    "ChannelRef",
    "InvalidTransitionError",
    "can_transition_pipeline",
    "transition_pipeline",
    "can_transition_job",
    "transition_job",
    "pipeline_after_job_failure",
    "SourceProvider",
    "MetadataProvider",
    "TranscriptProvider",
    "ScoringProvider",
    "SummaryProvider",
    "KnowledgeSink",
]
