"""Offline policy and request construction for optional cloud analysis.

This module owns the privacy boundary before the OpenAI adapter: it builds the
exclusive :class:`AnalysisPayload`, applies deterministic local token checks,
and enforces cache/budget/credential ordering.  It deliberately imports no
OpenAI SDK; that SDK is isolated in ``providers.cloud_llm``.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path
from typing import Any, Final, Protocol

import tiktoken

from youtube_intel.config import CloudSettings
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisInput,
    AnalysisOutcome,
    AnalysisPayload,
    AnalysisResult,
    AnalysisSkipped,
    AnalysisSkipReason,
    AppError,
    DiagnosticEntry,
    ErrorCode,
    JobStatus,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    SummaryProvider,
    VideoMetadata,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    ProviderCallCompletion,
    ProviderCallRequest,
    ProviderCallStatus,
    RetentionClass,
    StorageRoot,
    build_provider_request_hash,
)

_PROVIDER: Final = "openai"
_OPERATION: Final = "cloud-analysis"
_SAMPLING_VERSION: Final = "cloud-token-sampling-v1"
_PRIVACY_VERSION: Final = "cloud-privacy-v1"
O200K_BASE_FILENAME: Final = "o200k_base.tiktoken"
O200K_BASE_SHA256: Final = (
    "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
)
O200K_BASE_SIZE: Final = 3_613_922
PACKAGED_O200K_RESOURCE: Final = (
    Path(__file__).parent / "resources" / O200K_BASE_FILENAME
)
_MAX_SAMPLE_CODEPOINTS: Final = 4_000
_O200K_PAT_STR: Final = "|".join(
    (
        r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
        r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
        r"""\p{N}{1,3}""",
        r""" ?[^\s\p{L}\p{N}]+[\r\n/]*""",
        r"""\s*[\r\n]+""",
        r"""\s+(?!\S)""",
        r"""\s+""",
    )
)
_CLOCK = Callable[[], datetime]


class AnalysisPolicyError(Exception):
    """A safe hard failure that must be handled as a named application error."""

    def __init__(self, error: AppError) -> None:
        super().__init__(error.message)
        self.error = error


class LocalTokenizerResourceError(ValueError):
    """A safe local failure for the explicitly provisioned o200k resource."""


class CredentialResolver(Protocol):
    """Resolve a validated environment-variable name only after all local gates."""

    def resolve(self, env_name: str) -> str | None: ...


class EnvironmentCredentialResolver:
    """Production resolver; callers must ensure policy ordering before invoking it."""

    def resolve(self, env_name: str) -> str | None:
        return os.environ.get(env_name)


class AnalysisCache(Protocol):
    def get(self, request_hash: str) -> AnalysisResult | None: ...

    def put(self, result: AnalysisResult) -> None: ...


class InMemoryAnalysisCache:
    """Small deterministic cache for local composition and offline tests."""

    def __init__(self) -> None:
        self._values: dict[str, AnalysisResult] = {}

    def get(self, request_hash: str) -> AnalysisResult | None:
        return self._values.get(request_hash)

    def put(self, result: AnalysisResult) -> None:
        self._values[result.request_hash] = result


class CloudCallBudget:
    """Single-process budget consumed immediately before a real provider attempt."""

    def __init__(self, *, limit: int) -> None:
        if limit <= 0 or limit > 5:
            msg = "cloud call budget limit must be in 1..5"
            raise ValueError(msg)
        self._limit = limit
        self._used = 0

    @property
    def remaining(self) -> int:
        return self._limit - self._used

    def try_consume(self) -> bool:
        if self._used >= self._limit:
            return False
        self._used += 1
        return True


@dataclass(frozen=True, slots=True)
class _RequestParts:
    system: str
    developer: str
    schema: dict[str, object]
    payload_json: str


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sample_transcript_for_cloud(transcript_text: str) -> str:
    """Return a stable head/body/tail sample no larger than 4k code points."""

    if not transcript_text.strip():
        msg = "canonical transcript must be non-empty"
        raise ValueError(msg)
    if len(transcript_text) <= _MAX_SAMPLE_CODEPOINTS:
        return transcript_text
    head_size = 1_334
    body_size = 1_333
    tail_size = 1_333
    body_start = (len(transcript_text) - body_size) // 2
    return (
        transcript_text[:head_size]
        + transcript_text[body_start : body_start + body_size]
        + transcript_text[-tail_size:]
    )


def _analysis_schema() -> dict[str, object]:
    """The provider-neutral strict output schema, generated from frozen contracts."""

    point = {
        "type": "object",
        "additionalProperties": False,
        "required": ["text", "kind", "evidence_ids"],
        "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": 2000},
            "kind": {"enum": ["fact", "inference", "recommendation"]},
            "evidence_ids": {
                "type": "array", "minItems": 1, "maxItems": 10,
                "items": {"type": "string", "minLength": 1},
            },
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["one_sentence_summary", "core_points", "keywords", "evidence"],
        "properties": {
            "one_sentence_summary": {"type": "string", "minLength": 1, "maxLength": 500},
            "core_points": {"type": "array", "minItems": 1, "maxItems": 10, "items": point},
            "key_facts": {"type": "array", "maxItems": 20, "items": point},
            "product_opportunities": {"type": "array", "maxItems": 10, "items": point},
            "business_opportunities": {"type": "array", "maxItems": 10, "items": point},
            "actionable_directions": {"type": "array", "maxItems": 10, "items": point},
            "hypotheses_to_validate": {"type": "array", "maxItems": 10, "items": point},
            "action_recommendations": {"type": "array", "maxItems": 10, "items": point},
            "risks": {"type": "array", "maxItems": 10, "items": point},
            "keywords": {"type": "array", "minItems": 1, "maxItems": 20, "items": {"type": "string", "minLength": 1}},
            "evidence": {
                "type": "array", "maxItems": 20,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["evidence_id", "source", "excerpt"],
                    "properties": {
                        "evidence_id": {"type": "string", "minLength": 1},
                        "source": {"enum": ["title", "channel_name", "description", "transcript_sample"]},
                        "excerpt": {"type": "string", "minLength": 1, "maxLength": 2000},
                    },
                },
            },
        },
    }


def _request_parts(payload: AnalysisPayload) -> _RequestParts:
    prompt = resources.files("youtube_intel").joinpath("prompts", "summary.md").read_text("utf-8")
    if "analysis-prompt-v1" not in prompt:
        msg = "summary prompt must declare analysis-prompt-v1"
        raise ValueError(msg)
    return _RequestParts(
        system="You are a precise research analyst. Return only the declared JSON schema.",
        developer=prompt,
        schema=_analysis_schema(),
        payload_json=_canonical_json(payload.model_dump(mode="json")),
    )


def _provisioned_o200k_path(data_root: Path) -> Path:
    """Return the sole administrator-provisioned tokenizer location.

    The fixed child path prevents caller-controlled tokenizer selection.  It is
    intentionally not created here: provisioning is an explicit pre-runtime
    operator action under ADR-028.
    """

    try:
        if stat.S_ISLNK(data_root.lstat().st_mode):
            raise LocalTokenizerResourceError("local o200k asset path is unsafe")
        root = data_root.resolve(strict=True)
    except OSError as exc:
        raise LocalTokenizerResourceError("local o200k asset is missing") from exc
    if not root.is_dir():
        raise LocalTokenizerResourceError("local o200k asset is missing")

    directory = root / "tokenizers"
    path = directory / O200K_BASE_FILENAME
    for candidate in (directory, path):
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError as exc:
            raise LocalTokenizerResourceError("local o200k asset is missing") from exc
        except OSError as exc:
            raise LocalTokenizerResourceError("local o200k asset is invalid") from exc
        if stat.S_ISLNK(mode):
            raise LocalTokenizerResourceError("local o200k asset path is unsafe")
    if not stat.S_ISDIR(directory.lstat().st_mode) or not stat.S_ISREG(path.lstat().st_mode):
        raise LocalTokenizerResourceError("local o200k asset is invalid")
    return path


def _read_provisioned_o200k(data_root: Path) -> bytes:
    path = _provisioned_o200k_path(data_root)
    if not hasattr(os, "O_NOFOLLOW"):
        raise LocalTokenizerResourceError("local o200k asset path is unsafe")
    directory_flags = (
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
    )
    file_flags = os.O_RDONLY | os.O_NOFOLLOW
    try:
        directory_descriptor = os.open(path.parent, directory_flags)
    except FileNotFoundError as exc:
        raise LocalTokenizerResourceError("local o200k asset is missing") from exc
    except OSError as exc:
        raise LocalTokenizerResourceError("local o200k asset path is unsafe") from exc
    try:
        descriptor = os.open(path.name, file_flags, dir_fd=directory_descriptor)
    except FileNotFoundError as exc:
        os.close(directory_descriptor)
        raise LocalTokenizerResourceError("local o200k asset is missing") from exc
    except OSError as exc:
        os.close(directory_descriptor)
        raise LocalTokenizerResourceError("local o200k asset path is unsafe") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != O200K_BASE_SIZE:
            raise LocalTokenizerResourceError("local o200k asset is invalid")
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            contents = source.read(O200K_BASE_SIZE + 1)
        if len(contents) != O200K_BASE_SIZE:
            raise LocalTokenizerResourceError("local o200k asset is invalid")
    except OSError as exc:
        raise LocalTokenizerResourceError("local o200k asset is invalid") from exc
    finally:
        os.close(descriptor)
        os.close(directory_descriptor)
    if hashlib.sha256(contents).hexdigest() != O200K_BASE_SHA256:
        raise LocalTokenizerResourceError("local o200k asset is invalid")
    return contents


def _parse_o200k_ranks(contents: bytes) -> dict[bytes, int]:
    ranks: dict[bytes, int] = {}
    try:
        for line in contents.splitlines():
            if not line:
                continue
            token, rank = line.split()
            ranks[base64.b64decode(token, validate=True)] = int(rank)
    except (binascii.Error, ValueError, UnicodeError) as exc:
        raise LocalTokenizerResourceError("local o200k asset is invalid") from exc
    if not ranks:
        raise LocalTokenizerResourceError("local o200k asset is invalid")
    return ranks


def load_provisioned_o200k_encoding(data_root: Path) -> tiktoken.Encoding:
    """Load only the exact, explicitly provisioned local o200k resource."""

    ranks = _parse_o200k_ranks(_read_provisioned_o200k(data_root))
    try:
        return tiktoken.Encoding(
            name="o200k_base-local",
            pat_str=_O200K_PAT_STR,
            mergeable_ranks=ranks,
            special_tokens={"<|endoftext|>": 199999, "<|endofprompt|>": 200018},
        )
    except ValueError as exc:
        raise LocalTokenizerResourceError("local o200k asset is invalid") from exc


def tokenizer_resource_status(data_root: Path) -> str:
    """Return a safe diagnostic state without exposing filesystem paths."""

    try:
        load_provisioned_o200k_encoding(data_root)
    except LocalTokenizerResourceError as exc:
        return "MISSING" if "missing" in str(exc) else "INVALID"
    return "READY"


def _input_tokens(parts: _RequestParts, data_root: Path | None) -> int:
    if data_root is None:
        raise LocalTokenizerResourceError("local o200k asset is missing")
    encoding = load_provisioned_o200k_encoding(data_root)
    return sum(
        len(encoding.encode(part, disallowed_special=()))
        for part in (parts.system, parts.developer, _canonical_json(parts.schema), parts.payload_json)
    )


def build_analysis_input(
    *,
    video: VideoMetadata,
    transcript_text: str,
    language: str,
    output_language: str,
    settings: CloudSettings,
) -> AnalysisInput:
    """Build the sole outbound object and its complete, deterministic cache key."""

    if settings.model is None:
        msg = "cloud model is required to build an analysis input"
        raise ValueError(msg)
    payload = AnalysisPayload(
        video_id=video.video_id,
        title=video.title,
        channel_name=video.channel_name,
        published_at=video.published_at,
        duration_seconds=video.duration_seconds,
        default_language=video.default_language,
        description=video.description[: settings.max_description_chars],
        transcript_language=language,
        output_language=output_language,
        transcript_sample=sample_transcript_for_cloud(transcript_text),
    )
    normalized_input_hash = _normalized_input_hash(
        payload=payload, transcript_text=transcript_text, settings=settings
    )
    request_hash = build_provider_request_hash(
        operation=_OPERATION, normalized_input_hash=normalized_input_hash,
        provider=_PROVIDER, model=settings.model, prompt_version=settings.prompt_version,
        schema_version=settings.schema_version,
    )
    return AnalysisInput(
        payload=payload, transcript_content_hash=_sha256_text(transcript_text),
        request_hash=request_hash, prompt_version=settings.prompt_version,
        schema_version=settings.schema_version, sampling_version=settings.sampling_version,
        privacy_version=settings.privacy_version,
    )


def _normalized_input_hash(*, payload: AnalysisPayload, transcript_text: str, settings: CloudSettings) -> str:
    return _sha256_text(
        _canonical_json(
            {
                "payload": payload.model_dump(mode="json"),
                "transcript_content_hash": _sha256_text(transcript_text),
                "sampling_version": settings.sampling_version,
                "privacy_version": settings.privacy_version,
                "max_output_tokens": settings.max_output_tokens,
            }
        )
    )


class AnalysisService:
    """Enforce all no-call policy gates around one structural summary provider."""

    def __init__(
        self,
        *,
        provider: SummaryProvider,
        settings: CloudSettings,
        cache: AnalysisCache,
        budget: CloudCallBudget,
        credential_resolver: CredentialResolver,
        tokenizer_data_root: Path | None = None,
        output_language: str = "zh-CN",
        clock: _CLOCK = _utcnow,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._cache = cache
        self._budget = budget
        self._credential_resolver = credential_resolver
        self._tokenizer_data_root = tokenizer_data_root
        self._output_language = output_language
        self._clock = clock

    def _skipped(self, reason: AnalysisSkipReason, message: str) -> AnalysisOutcome:
        from youtube_intel.domain import AnalysisSkipped

        return AnalysisSkipped(reason=reason, call=None, safe_message=message)

    def analyze(
        self,
        *,
        video: VideoMetadata,
        transcript_text: str,
        language: str,
        should_summarize: bool = True,
    ) -> AnalysisOutcome | None:
        # Low-value videos do not create an AnalysisOutcome or reach any cloud gate.
        if not should_summarize:
            return None
        if not self._settings.enabled:
            return self._skipped(AnalysisSkipReason.CLOUD_DISABLED, "cloud analysis is disabled")
        try:
            analysis_input = build_analysis_input(
                video=video, transcript_text=transcript_text, language=language,
                output_language=self._output_language, settings=self._settings,
            )
            parts = _request_parts(analysis_input.payload)
            if _input_tokens(parts, self._tokenizer_data_root) > self._settings.max_local_input_tokens_per_video:
                return self._skipped(AnalysisSkipReason.INPUT_TOO_LARGE, "local input token limit exceeded")
        except ValueError as exc:
            raise AnalysisPolicyError(
                AppError(code=ErrorCode.CONFIG_INVALID, message="cloud analysis local configuration is invalid", retryable=False, video_id=video.video_id, stage=ProcessingStage.ANALYSIS)
            ) from exc
        cached = self._cache.get(analysis_input.request_hash)
        if cached is not None:
            return AnalysisCompleted(
                result=cached,
                call=ProviderCallMetadata(provider=cached.provider, model=cached.model, started_at=self._clock(), finished_at=self._clock(), diagnostics=(DiagnosticEntry(code="CACHE_HIT", message="reused cached structured cloud analysis"),)),
            )
        if self._budget.remaining == 0:
            return self._skipped(AnalysisSkipReason.BUDGET_EXHAUSTED, "cloud call budget is exhausted")
        credential = self._credential_resolver.resolve(self._settings.api_key_env)
        if not credential:
            return self._skipped(AnalysisSkipReason.CREDENTIAL_UNAVAILABLE, "cloud credential is unavailable")
        # A call is consumed at the last possible moment, immediately before transport.
        if not self._budget.try_consume():
            return self._skipped(AnalysisSkipReason.BUDGET_EXHAUSTED, "cloud call budget is exhausted")
        started_at = self._clock()
        try:
            provider_with_credential = getattr(self._provider, "summarize_with_credential", None)
            result = (
                provider_with_credential(analysis_input, credential)
                if callable(provider_with_credential)
                else self._provider.summarize(analysis_input)
            )
        except Exception as exc:
            candidate = getattr(exc, "error", None)
            if getattr(exc, "refusal", False):
                return self._skipped(AnalysisSkipReason.PROVIDER_REFUSAL, "cloud analysis request was refused")
            if isinstance(candidate, AppError):
                raise AnalysisPolicyError(candidate) from None
            raise AnalysisPolicyError(
                AppError(code=ErrorCode.INVALID_RESPONSE, message="cloud analysis provider failed", retryable=True, video_id=video.video_id, stage=ProcessingStage.ANALYSIS)
            ) from None
        finally:
            credential = ""
        if result.request_hash != analysis_input.request_hash:
            raise AnalysisPolicyError(AppError(code=ErrorCode.INVALID_RESPONSE, message="cloud analysis result belongs to a different request", retryable=True, video_id=video.video_id, stage=ProcessingStage.ANALYSIS))
        self._cache.put(result)
        return AnalysisCompleted(
            result=result,
            call=ProviderCallMetadata(provider=result.provider, model=result.model, started_at=started_at, finished_at=self._clock()),
        )


@dataclass(frozen=True, slots=True)
class AnalysisJobContext:
    job_id: str
    owner: str
    pipeline_version: str


class RepositoryBackedAnalysisService:
    """Persist a successful analysis and its provider call in one repository transaction."""

    def __init__(self, *, provider: Any, settings: CloudSettings, repository: Any,
                 context: AnalysisJobContext, artifact_root: Path,
                 credential_resolver: CredentialResolver, budget: CloudCallBudget) -> None:
        self.provider, self.settings, self.repository = provider, settings, repository
        self.context, self.artifact_root = context, artifact_root
        self.credential_resolver, self.budget = credential_resolver, budget

    def _validate_upstream(self, *, video: VideoMetadata, transcript_text: str) -> bool:
        video_record = self.repository.get_video(video.video_id)
        job = self.repository.get_job(self.context.job_id)
        if (
            video_record is None
            or job is None
            or video_record.pipeline_status is not PipelineStatus.SCORED
            or video_record.pipeline_version != self.context.pipeline_version
            or job.video_id != video.video_id
            or job.target_stage is not ProcessingStage.ANALYSIS
            or job.pipeline_version != self.context.pipeline_version
            or job.status is not JobStatus.RUNNING
            or job.lease_owner != self.context.owner
            or not transcript_text.strip()
        ):
            raise AnalysisPolicyError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message="cloud analysis upstream state is invalid",
                    retryable=True,
                    video_id=video.video_id,
                    stage=ProcessingStage.ANALYSIS,
                )
            )
        if video_record.should_summarize is None:
            raise AnalysisPolicyError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message="cloud analysis value policy is unavailable",
                    retryable=True,
                    video_id=video.video_id,
                    stage=ProcessingStage.ANALYSIS,
                )
            )
        return video_record.should_summarize is True

    @staticmethod
    def _cache_error(video_id: str) -> AnalysisPolicyError:
        return AnalysisPolicyError(AppError(code=ErrorCode.INVALID_RESPONSE,
            message="persisted cloud analysis cache is invalid", retryable=True,
            video_id=video_id, stage=ProcessingStage.ANALYSIS))

    def _read_verified_artifact(
        self, *, artifact: Any, request: ProviderCallRequest, video_id: str,
        name: str, kind: ArtifactKind, retention: RetentionClass,
        expires_at: datetime | None, job_id: str | None = None,
    ) -> bytes:
        key = request.deterministic_artifact_key if name == "raw" else (
            f"analysis/{request.request_hash}/structured"
        )
        relative_path = artifact.relative_path if artifact is not None else None
        if (
            artifact is None
            or artifact.artifact_key != key
            or artifact.video_id != video_id
            or artifact.job_id is None
            or (job_id is not None and artifact.job_id != job_id)
            or artifact.kind is not kind
            or artifact.storage_root is not StorageRoot.DATA
            or not isinstance(relative_path, str)
            or relative_path != f"analysis/{request.request_hash}/{name}.json"
            or artifact.provider != request.provider
            or artifact.model != request.model
            or artifact.producer_version != f"analysis-{name}-v1"
            or artifact.retention_class is not retention
            or artifact.expires_at != expires_at
            or artifact.deleted_at is not None
        ):
            raise self._cache_error(video_id)
        try:
            contents = (self.artifact_root / relative_path).read_bytes()
        except OSError:
            raise self._cache_error(video_id) from None
        if hashlib.sha256(contents).hexdigest() != artifact.content_hash:
            raise self._cache_error(video_id)
        return contents

    def _reuse_persisted_result(
        self, *, request: ProviderCallRequest, provider_call: Any, video_id: str,
        now: datetime,
    ) -> AnalysisCompleted:
        raw = self.repository.get_artifact_by_key(request.deterministic_artifact_key)
        structured = self.repository.get_artifact_by_key(
            f"analysis/{request.request_hash}/structured"
        )
        if (
            provider_call.request_hash != request.request_hash
            or provider_call.operation != request.operation
            or provider_call.provider != request.provider
            or provider_call.model != request.model
            or provider_call.prompt_version != request.prompt_version
            or provider_call.schema_version != request.schema_version
            or provider_call.status is not ProviderCallStatus.SUCCEEDED
        ):
            raise self._cache_error(video_id)
        self._read_verified_artifact(
            artifact=raw, request=request, video_id=video_id, name="raw",
            kind=ArtifactKind.ANALYSIS_RAW, retention=RetentionClass.RAW_RESPONSE_30D,
            expires_at=None if raw is None else raw.created_at + timedelta(days=30),
        )
        if provider_call.response_artifact_id != raw.artifact_id:
            raise self._cache_error(video_id)
        structured_contents = self._read_verified_artifact(
            artifact=structured, request=request, video_id=video_id, name="structured",
            kind=ArtifactKind.ANALYSIS_STRUCTURED, retention=RetentionClass.LONG_LIVED,
            expires_at=None, job_id=raw.job_id,
        )
        try:
            result = AnalysisResult.model_validate_json(structured_contents)
        except (TypeError, ValueError):
            raise self._cache_error(video_id) from None
        if (
            result.request_hash != request.request_hash
            or result.provider != request.provider
            or result.model != request.model
        ):
            raise self._cache_error(video_id)
        self.repository.complete_stage(job_id=self.context.job_id, owner=self.context.owner,
            video_id=video_id, expected_status=PipelineStatus.SCORED,
            target_status=PipelineStatus.ANALYSIS_READY, pipeline_version=self.context.pipeline_version,
            artifacts=(), provider_call=None, now=now)
        return AnalysisCompleted(result=result, call=ProviderCallMetadata(provider=result.provider,
            model=result.model, started_at=now, finished_at=_utcnow(), diagnostics=(DiagnosticEntry(code="PERSISTED_CACHE_HIT", message="reused persisted cloud analysis"),)))

    def analyze(self, *, video: VideoMetadata, transcript_text: str, language: str,
                output_language: str = "zh-CN") -> AnalysisOutcome | None:
        if not self._validate_upstream(video=video, transcript_text=transcript_text):
            return None
        if not self.settings.enabled:
            return AnalysisSkipped(reason=AnalysisSkipReason.CLOUD_DISABLED, call=None,
                safe_message="cloud analysis is disabled")
        analysis_input = build_analysis_input(video=video, transcript_text=transcript_text,
            language=language, output_language=output_language, settings=self.settings)
        if _input_tokens(
            _request_parts(analysis_input.payload), self.artifact_root
        ) > self.settings.max_local_input_tokens_per_video:
            return AnalysisSkipped(reason=AnalysisSkipReason.INPUT_TOO_LARGE, call=None,
                safe_message="local input token limit exceeded")
        request = ProviderCallRequest(operation=_OPERATION,
            normalized_input_hash=_normalized_input_hash(payload=analysis_input.payload,
                transcript_text=transcript_text, settings=self.settings), provider=_PROVIDER,
            model=self.settings.model, prompt_version=self.settings.prompt_version,
            schema_version=self.settings.schema_version,
            deterministic_artifact_key=f"analysis/{analysis_input.request_hash}/raw")
        now = _utcnow()
        existing = self.repository.get_provider_call(request.request_hash)
        if existing is not None and existing.status is ProviderCallStatus.SUCCEEDED:
            return self._reuse_persisted_result(
                request=request, provider_call=existing, video_id=video.video_id, now=now
            )
        if self.budget.remaining == 0:
            return AnalysisSkipped(reason=AnalysisSkipReason.BUDGET_EXHAUSTED, call=None,
                safe_message="cloud call budget is exhausted")
        credential = self.credential_resolver.resolve(self.settings.api_key_env)
        if not credential:
            return AnalysisSkipped(reason=AnalysisSkipReason.CREDENTIAL_UNAVAILABLE, call=None,
                safe_message="cloud credential is unavailable")
        reservation = self.repository.reserve_provider_call(request, owner=self.context.owner,
            lease_until=now + timedelta(seconds=300), available_at=now, now=now)
        if not reservation.acquired:
            if reservation.record.status is not ProviderCallStatus.SUCCEEDED:
                raise AnalysisPolicyError(AppError(code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message="cloud analysis call is already reserved", retryable=True,
                    video_id=video.video_id, stage=ProcessingStage.ANALYSIS))
            return self._reuse_persisted_result(
                request=request, provider_call=reservation.record, video_id=video.video_id, now=now
            )
        if not self.budget.try_consume():
            raise AnalysisPolicyError(AppError(code=ErrorCode.LOCAL_RESOURCE,
                message="cloud analysis could not start", retryable=True, video_id=video.video_id,
                stage=ProcessingStage.ANALYSIS))
        try:
            result = self.provider.summarize_with_credential(analysis_input, credential)
            raw = self.provider.consume_raw_response(request_hash=request.request_hash).encode()
            structured = _canonical_json(result.model_dump(mode="json")).encode()
            artifacts = self._artifacts(request, video.video_id, raw, structured, now)
            paths = self._write(artifacts, (raw, structured))
            self.repository.complete_stage(job_id=self.context.job_id, owner=self.context.owner,
                video_id=video.video_id, expected_status=PipelineStatus.SCORED,
                target_status=PipelineStatus.ANALYSIS_READY, pipeline_version=self.context.pipeline_version,
                artifacts=artifacts, provider_call=ProviderCallCompletion(request_hash=request.request_hash,
                response_artifact_id=artifacts[0].artifact_id, input_tokens=None, output_tokens=None,
                cost_microusd=None), now=now)
        except Exception as exc:
            for path in locals().get("paths", ()):
                path.unlink(missing_ok=True)
            error = getattr(exc, "error", None)
            self.repository.fail_provider_call(request.request_hash, owner=self.context.owner,
                retryable=True, available_at=now,
                error_code=ErrorCode.LOCAL_RESOURCE if not isinstance(error, AppError) else error.code,
                error_message="cloud analysis stage persistence failed", now=now)
            raise
        return AnalysisCompleted(result=result, call=ProviderCallMetadata(provider=result.provider,
            model=result.model, started_at=now, finished_at=_utcnow()))

    def _artifacts(self, request: ProviderCallRequest, video_id: str, raw: bytes, structured: bytes,
                   now: datetime) -> tuple[ArtifactWrite, ArtifactWrite]:
        values = (("raw", raw, ArtifactKind.ANALYSIS_RAW, RetentionClass.RAW_RESPONSE_30D, now),
                  ("structured", structured, ArtifactKind.ANALYSIS_STRUCTURED, RetentionClass.LONG_LIVED, None))
        return tuple(ArtifactWrite(artifact_id=f"analysis-{name}-{_sha256_text(key + hashlib.sha256(data).hexdigest())}",
            artifact_key=key, video_id=video_id, job_id=self.context.job_id, kind=kind,
            storage_root=StorageRoot.DATA, relative_path=f"analysis/{request.request_hash}/{name}.json",
            content_hash=hashlib.sha256(data).hexdigest(), provider=_PROVIDER, model=request.model,
            producer_version=f"analysis-{name}-v1", retention_class=retention,
            expires_at=None if expires is None else expires + timedelta(days=30))
            for name, data, kind, retention, expires in values
            for key in (request.deterministic_artifact_key if name == "raw" else f"analysis/{request.request_hash}/structured",))  # type: ignore[return-value]

    def _write(self, artifacts: tuple[ArtifactWrite, ArtifactWrite], contents: tuple[bytes, bytes]) -> tuple[Path, ...]:
        paths = []
        for artifact, content in zip(artifacts, contents, strict=True):
            path = self.artifact_root / artifact.relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            paths.append(path)
        return tuple(paths)


__all__ = [
    "AnalysisCache", "AnalysisPolicyError", "AnalysisService", "CloudCallBudget",
    "CredentialResolver", "EnvironmentCredentialResolver", "InMemoryAnalysisCache",
    "build_analysis_input", "sample_transcript_for_cloud",
]
