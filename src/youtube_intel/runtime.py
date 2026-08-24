"""Production composition root for the local-first command operations."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any, Callable, cast

from youtube_intel.analysis import (
    AnalysisJobContext,
    CloudCallBudget,
    EnvironmentCredentialResolver,
    RepositoryBackedAnalysisService,
)
from youtube_intel.config import AppConfig, LocalScoringSettings
from youtube_intel.discovery import DiscoveryService, YouTubeRssSourceProvider
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisOutcome,
    AnalysisResult,
    AnalysisSkipped,
    AnalysisSkipReason,
    AppError,
    ChannelRef,
    ContentQualityInput,
    ErrorCode,
    JobStatus,
    MetadataProvider,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    ScoreResult,
    ScoringDecision,
    ScoringEvidenceSource,
    ScoringInput,
    ScoringOutcome,
    SourceProvider,
    TranscriptionRequired,
    TranscriptReady,
    VideoMetadata,
    scoring_reason_matches_output_language,
    validate_score_result_json,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.operations import CommandOutcome, ExitCode, Operations
from youtube_intel.pipeline import PipelineOrchestrator
from youtube_intel.providers.cloud_llm import OpenAIResponsesProvider
from youtube_intel.providers.obsidian import NoteWriteContext, ObsidianNoteSink
from youtube_intel.providers.ollama import (
    OllamaQualityJudgeProvider,
    OllamaScoringProvider,
)
from youtube_intel.providers.subtitles import YtDlpSubtitleAdapter
from youtube_intel.providers.youtube import YtDlpMetadataProvider
from youtube_intel.quality import (
    _JUDGE_PROVIDER,
    _QUALITY_JUDGE_OPERATION,
    _QUALITY_POLICY_VERSION,
    _QUALITY_PROMPT_VERSION,
    _QUALITY_PROVENANCE_AUTHORITY_SENTINEL,
    _QUALITY_SCHEMA_VERSION,
    _SCORING_PROMPT_VERSION,
    _SCORING_SCHEMA_VERSION,
    _TRUSTED_SCORING_CONTEXT_SENTINEL,
    DeterministicContentQualityGate,
    QualityProvenanceAuthority,
    TrustedScoringContext,
    _mint_quality_provenance_authority,
    _mint_trusted_scoring_context,
    build_content_quality_input_hash,
    build_quality_pass_attestation,
)
from youtube_intel.reporting import WeeklyReportService
from youtube_intel.retry import RetryPolicy
from youtube_intel.scoring import (
    _G_RAW_ARTIFACT_PRODUCER_VERSION,
    _G_STRUCTURED_ARTIFACT_PRODUCER_VERSION,
    _RAW_ARTIFACT_PRODUCER_VERSION,
    _SCORING_OPERATION,
    _STRUCTURED_ARTIFACT_PRODUCER_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    PhaseFTrustedScoringSuccess,
    PrimaryScoringAttempt,
    ScoringJobContext,
    TrustedPersistenceEntry,
    _run_primary_trusted_scoring_seam,
    build_scoring_input,
    build_scoring_request_identity,
)
from youtube_intel.scoring_admission import (
    ScoringAdmissionRegistry,
    ScoringDispatchAdmission,
    ScoringDispatchDenied,
    UnknownProviderState,
    build_judge_scoring_dispatch_identity,
    build_primary_scoring_dispatch_identity,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    JobRecord,
    ProviderCallStatus,
    SQLiteStateRepository,
    StorageRoot,
    VideoRecord,
)
from youtube_intel.transcripts import (
    SubtitleAcquisitionService,
    SubtitleAdapter,
    TranscriptError,
    TranscriptJobContext,
)


class _KnownPrimaryFailure(ValueError):
    """A received PRIMARY response failed locally without exposing repair authority."""

    def __init__(
        self, message: str = "received PRIMARY response is ineligible for trusted scoring"
    ) -> None:
        super().__init__(message)
        self.error = AppError(
            code=ErrorCode.INVALID_RESPONSE,
            message=message,
            retryable=False,
            stage=ProcessingStage.SCORING,
        )


PIPELINE_VERSION = "runtime-v1"
_MAX_OLLAMA_TAGS_BYTES = 1_000_000


@dataclass(frozen=True, slots=True)
class RuntimeDependencies:
    """External boundaries; defaults are real and tests may replace only these."""

    discovery_source: SourceProvider
    metadata_provider: MetadataProvider
    subtitle_adapter_factory: Callable[[], SubtitleAdapter]
    scoring_provider_factory: Callable[[], Any]
    analysis_provider_factory: Callable[[], Any]
    quality_judge_provider_factory: Callable[[], Any] | None = None


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    status: str
    message: str
    blocking: bool


def _build_quality_provenance_authority(
    local_scoring: LocalScoringSettings,
) -> QualityProvenanceAuthority:
    """Mint the current quality provenance authority from validated config.

    This is the sole production path from an already-loaded ``AppConfig`` to a
    ``QualityProvenanceAuthority``.  It is called during ``RuntimeOperations``
    composition and is not exposed as a public factory.
    """

    return _mint_quality_provenance_authority(
        sentinel=_QUALITY_PROVENANCE_AUTHORITY_SENTINEL,
        judge_provider=_JUDGE_PROVIDER,
        judge_model=local_scoring.model,
        judge_model_digest=local_scoring.expected_model_digest,
        scoring_schema_version=_SCORING_SCHEMA_VERSION,
        scoring_prompt_version=_SCORING_PROMPT_VERSION,
        quality_policy_version=_QUALITY_POLICY_VERSION,
        quality_schema_version=_QUALITY_SCHEMA_VERSION,
        quality_prompt_version=_QUALITY_PROMPT_VERSION,
        judge_operation=_QUALITY_JUDGE_OPERATION,
    )


def _build_trusted_scoring_context(config: AppConfig) -> TrustedScoringContext:
    """Mint scoring provenance from the validated runtime configuration only."""

    local_scoring = config.settings.local_scoring
    return _mint_trusted_scoring_context(
        sentinel=_TRUSTED_SCORING_CONTEXT_SENTINEL,
        scoring_provider=_JUDGE_PROVIDER,
        scoring_model=local_scoring.model,
        scoring_model_digest=local_scoring.expected_model_digest,
        output_language=config.settings.general.output_language,
        scoring_schema_version=_SCORING_SCHEMA_VERSION,
        scoring_prompt_version=_SCORING_PROMPT_VERSION,
        scoring_operation=_SCORING_OPERATION,
        temperature=local_scoring.temperature,
        max_output_tokens=local_scoring.max_output_tokens,
        max_description_chars=local_scoring.max_description_chars,
    )


@dataclass(frozen=True, slots=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]

    @property
    def exit_code(self) -> ExitCode:
        return (
            ExitCode.LOCAL_RESOURCE
            if any(check.blocking for check in self.checks)
            else ExitCode.OK
        )

    def render(self) -> str:
        return "\n".join(
            f"{check.status}: {check.name} — {check.message}" for check in self.checks
        )


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _safe_project_path(root: Path, configured: str) -> Path:
    candidate = PurePosixPath(configured.replace("\\", "/"))
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        raise ValueError("configured project path is unsafe")
    path = (root / Path(*candidate.parts)).resolve(strict=False)
    if not path.is_relative_to(root):
        raise ValueError("configured project path escapes project root")
    return path


def _ensure_project_directory(root: Path, configured: str) -> Path:
    path = _safe_project_path(root, configured)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or not resolved.is_relative_to(root):
        raise OSError("configured project directory is unsafe")
    return resolved


def _ensure_vault_subdir(vault_root: Path, vault_subdir: str) -> None:
    """Create the managed subdirectory without following a substituted symlink."""

    root = vault_root.resolve(strict=True)
    if not root.is_dir() or vault_root.is_symlink():
        raise OSError("vault root is unavailable")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    current = os.open(root, flags)
    try:
        for part in PurePosixPath(vault_subdir.replace("\\", "/")).parts:
            if part in {"", ".", ".."}:
                raise OSError("vault subdirectory is unsafe")
            try:
                next_fd = os.open(part, flags, dir_fd=current)
            except FileNotFoundError:
                os.mkdir(part, mode=0o700, dir_fd=current)
                next_fd = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = next_fd
    finally:
        os.close(current)


def bootstrap_runtime(
    config: AppConfig,
    project_root: Path,
) -> SQLiteStateRepository:
    """Idempotently create the declared local runtime state.

    The returned repository is a low-level SQLite adapter.  Phase G trusted
    registration is composed only inside ``RuntimeOperations``.
    """

    root = project_root.resolve(strict=True)
    storage = config.settings.storage
    data_root = _ensure_project_directory(root, storage.data_dir)
    _ensure_project_directory(root, storage.logs_dir)
    _ensure_vault_subdir(Path(storage.vault_root), storage.vault_subdir)
    repository = SQLiteStateRepository(data_root / "state.sqlite")
    repository.initialize(now=_utcnow())
    return repository


def _production_dependencies(config: AppConfig) -> RuntimeDependencies:
    timeout = config.settings.timeouts.http_seconds
    scoring_prompt = resources.files("youtube_intel").joinpath(
        "prompts", "scoring.md"
    ).read_text(encoding="utf-8")
    cloud = config.settings.cloud
    return RuntimeDependencies(
        discovery_source=YouTubeRssSourceProvider(timeout_seconds=timeout),
        metadata_provider=YtDlpMetadataProvider(timeout_seconds=timeout),
        subtitle_adapter_factory=lambda: YtDlpSubtitleAdapter(timeout_seconds=timeout),
        scoring_provider_factory=lambda: OllamaScoringProvider(
            settings=config.settings.local_scoring,
            prompt=scoring_prompt,
        ),
        analysis_provider_factory=lambda: OpenAIResponsesProvider(
            model=cloud.model or "cloud-disabled",
            max_output_tokens=cloud.max_output_tokens,
        ),
        quality_judge_provider_factory=lambda: OllamaQualityJudgeProvider(
            settings=config.settings.local_scoring,
        ),
    )


class RuntimeOperations(Operations):
    def __init__(
        self,
        *,
        config: AppConfig,
        project_root: Path,
        dependencies: RuntimeDependencies | None = None,
    ) -> None:
        self._config = config
        self._root = project_root.resolve(strict=True)
        self._repository = bootstrap_runtime(config, self._root)
        self._dependencies = dependencies or _production_dependencies(config)
        self._quality_provenance_authority = _build_quality_provenance_authority(
            config.settings.local_scoring
        )
        self._trusted_scoring_context = _build_trusted_scoring_context(config)
        self._discovery = DiscoveryService(
            self._dependencies.discovery_source,
            self._repository,
            self._dependencies.metadata_provider,
        )
        self._data_root = _safe_project_path(
            self._root, self._config.settings.storage.data_dir
        ).resolve(strict=True)
        self._runtime_owner = f"youtube-intel-runtime:{uuid.uuid4().hex}"
        self._scoring_admissions = ScoringAdmissionRegistry(self._repository)

    def _scoring_admission_for(self, job_id: str) -> ScoringDispatchAdmission:
        """Return this runtime's shared admission view for an active scoring job."""

        registry = getattr(self, "_scoring_admissions", None)
        if registry is None:
            registry = ScoringAdmissionRegistry(self._repository)
            self._scoring_admissions = registry
        return registry.admission_for(job_id=job_id, owner=self._runtime_owner)

    def run_primary_trusted_scoring(
        self,
        *,
        attempt: PrimaryScoringAttempt,
        scoring_input: ScoringInput,
        job_id: str,
    ) -> PhaseFTrustedScoringSuccess:
        """Run PRIMARY Judge work under this runtime's active SCORING lease."""

        return self._run_primary_trusted_scoring(
            attempt=attempt,
            scoring_input=scoring_input,
            admission=self._scoring_admission_for(job_id),
        )

    def _run_primary_trusted_scoring(
        self,
        *,
        attempt: PrimaryScoringAttempt,
        scoring_input: ScoringInput,
        admission: ScoringDispatchAdmission,
    ) -> PhaseFTrustedScoringSuccess:
        """Run the Phase F in-memory trusted scoring seam (memory only).

        The runtime owns the quality provenance authority and trusted scoring
        context; callers cannot inject them.  The method enforces the mandatory
        order: attempt binding, TASK-016B language validation,
        ``DeterministicContentQualityGate``, PRIMARY Local Quality Judge,
        attestation construction, and finalization through the private seam.
        """

        if type(attempt) is not PrimaryScoringAttempt:
            msg = "trusted scoring requires an exact PrimaryScoringAttempt"
            raise ValueError(msg)
        if attempt.attempt_role != "PRIMARY":
            msg = "trusted scoring accepts only PRIMARY attempts"
            raise ValueError(msg)
        if type(scoring_input) is not ScoringInput:
            msg = "trusted scoring requires an exact ScoringInput"
            raise ValueError(msg)

        context = self._trusted_scoring_context
        if attempt.provider != context.scoring_provider:
            msg = "attempt provider mismatches the trusted scoring context"
            raise ValueError(msg)
        if attempt.model != context.scoring_model:
            msg = "attempt model mismatches the trusted scoring context"
            raise ValueError(msg)
        if attempt.model_digest != context.scoring_model_digest:
            msg = "attempt model digest mismatches the trusted scoring context"
            raise ValueError(msg)

        try:
            raw_bytes = attempt.final_raw_response.encode("utf-8")
        except UnicodeEncodeError:
            msg = "raw response is not valid strict UTF-8"
            raise ValueError(msg) from None
        raw_response_hash = hashlib.sha256(raw_bytes).hexdigest()
        if raw_response_hash != attempt.raw_response_hash:
            msg = "raw response hash mismatches the primary attempt binding"
            raise ValueError(msg)

        from youtube_intel.providers.ollama import parse_scoring_candidate

        reparsed_candidate = parse_scoring_candidate(attempt.final_raw_response)
        if reparsed_candidate != attempt.candidate:
            msg = "candidate does not match the canonical parse of the raw response"
            raise ValueError(msg)

        from youtube_intel.quality import build_scoring_candidate_hash

        candidate_hash = build_scoring_candidate_hash(attempt.candidate)
        if candidate_hash != attempt.candidate_hash:
            msg = "candidate hash mismatches the primary attempt binding"
            raise ValueError(msg)

        identity = build_scoring_request_identity(
            scoring_input=scoring_input,
            model=context.scoring_model,
            temperature=context.temperature,
            max_output_tokens=context.max_output_tokens,
            max_description_chars=context.max_description_chars,
        )
        if attempt.scoring_request_hash != identity.request_hash:
            msg = "scoring request hash mismatches the canonical identity"
            raise ValueError(msg)
        if attempt.scoring_input_normalized_hash != identity.normalized_input_hash:
            msg = "scoring input identity mismatches the canonical identity"
            raise ValueError(msg)
        if scoring_input.request_hash != identity.request_hash:
            msg = "scoring request hash mismatches the trusted scoring input"
            raise ValueError(msg)

        # TASK-016B language validation before the deterministic gate.
        if not scoring_reason_matches_output_language(
            attempt.candidate.reason, scoring_input.output_language
        ):
            raise _KnownPrimaryFailure()

        # Build the content-quality input from the candidate and scoring input.
        quality_input = ContentQualityInput.model_validate(
            {
                "scoring_request_hash": scoring_input.request_hash,
                "candidate_hash": candidate_hash,
                "output_language": scoring_input.output_language,
                "reason": attempt.candidate.reason,
                "topics": list(attempt.candidate.topics),
                "evidence_registry": [
                    {
                        "evidence_id": "title-1",
                        "source": ScoringEvidenceSource.TITLE.value,
                        "excerpt": scoring_input.video.title,
                    }
                ],
            }
        )
        quality_input_hash = build_content_quality_input_hash(quality_input)

        # Deterministic gate: fail closed on deterministic rejection.
        gate_result = DeterministicContentQualityGate().evaluate(
            content=attempt.candidate.reason,
            candidate_hash=candidate_hash,
            quality_input_hash=quality_input_hash,
            scoring_request_hash=scoring_input.request_hash,
        )
        if gate_result is not None:
            raise _KnownPrimaryFailure()

        # PRIMARY Local Quality Judge: caller cannot supply a result.
        quality_operation = QualityJudgeOperationInput.model_validate(
            {
                "scoring_request_hash": scoring_input.request_hash,
                "attempt_role": QualityJudgeAttemptRole.PRIMARY.value,
                "candidate_hash": candidate_hash,
                "quality_input_hash": quality_input_hash,
                "policy_version": _QUALITY_POLICY_VERSION,
                "prompt_version": _QUALITY_PROMPT_VERSION,
                "schema_version": _QUALITY_SCHEMA_VERSION,
                "judge_provider": _JUDGE_PROVIDER,
                "judge_model": self._config.settings.local_scoring.model,
                "judge_model_digest": self._config.settings.local_scoring.expected_model_digest,
            }
        )
        quality_result = self._dispatch_quality_judge(
            operation_input=quality_operation,
            content_input=quality_input,
            admission=admission,
        )
        if quality_result.status.value != "PASS":
            raise _KnownPrimaryFailure()

        attestation = build_quality_pass_attestation(
            quality_result=quality_result,
            operation_input=quality_operation,
            quality_input=quality_input,
            authority=self._quality_provenance_authority,
        )

        return _run_primary_trusted_scoring_seam(
            attempt=attempt,
            scoring_input=scoring_input,
            quality_input=quality_input,
            quality_result=quality_result,
            quality_operation=quality_operation,
            attestation=attestation,
            quality_authority=self._quality_provenance_authority,
            scoring_context=self._trusted_scoring_context,
        )

    def _dispatch_quality_judge(
        self,
        *,
        operation_input: QualityJudgeOperationInput,
        content_input: ContentQualityInput,
        admission: ScoringDispatchAdmission,
    ) -> Any:
        """Admit the Judge call before its provider can be contacted."""

        admission.verify_active_lease(now=_utcnow())
        provider = self._create_quality_judge_provider_for_dispatch()
        admission.admit(
            build_judge_scoring_dispatch_identity(operation_input),
            now=_utcnow(),
        )
        try:
            return provider.judge(
                operation_input,
                content_input=content_input,
            )
        except Exception as error:
            raise UnknownProviderState(
                "scoring provider outcome is unknown after external dispatch"
            ) from error

    def _create_quality_judge_provider_for_dispatch(self) -> Any:
        """Construct the Judge client before the admitted external call begins."""

        try:
            factory = self._dependencies.quality_judge_provider_factory
            if factory is not None:
                return factory()
            return OllamaQualityJudgeProvider(settings=self._config.settings.local_scoring)
        except Exception as error:
            raise ScoringDispatchDenied(
                "quality judge dispatch failed before external provider contact"
            ) from error

    def _create_scoring_provider_for_dispatch(self) -> Any:
        """Construct the provider before any external scoring call begins."""

        try:
            return self._dependencies.scoring_provider_factory()
        except Exception as error:
            raise ScoringDispatchDenied(
                "scoring provider dispatch failed before external provider contact"
            ) from error

    def _dispatch_primary_attempt_after_admission(
        self, provider: Any, scoring_input: ScoringInput
    ) -> PrimaryScoringAttempt:
        """Contact PRIMARY only after its H1 admission has been consumed."""

        try:
            return cast(PrimaryScoringAttempt, provider.primary_attempt(scoring_input))
        except Exception as error:
            raise UnknownProviderState(
                "scoring provider outcome is unknown after external dispatch"
            ) from error

    def _trusted_persistence_entry(
        self,
        *,
        job_id: str,
        owner: str,
        pipeline_version: str,
    ) -> TrustedPersistenceEntry:
        """Mint the runtime-owned Phase G persistence committer.

        Authority, context, DATA root and job identity come from the runtime
        closure; callers cannot substitute them.
        """

        return TrustedPersistenceEntry(
            repository=self._repository,
            data_root=self._data_root,
            quality_authority=self._quality_provenance_authority,
            scoring_context=self._trusted_scoring_context,
            context=ScoringJobContext(
                job_id=job_id,
                owner=owner,
                pipeline_version=pipeline_version,
            ),
            summary_threshold=self._config.settings.thresholds.summary_score,
        )

    def _persist_trusted_scoring_success(
        self,
        *,
        success: PhaseFTrustedScoringSuccess,
        job: JobRecord,
        owner: str,
        pipeline_version: str,
    ) -> Any:
        """Commit Phase G success, then release its runtime-only admission state."""

        entry = self._trusted_persistence_entry(
            job_id=job.job_id,
            owner=owner,
            pipeline_version=pipeline_version,
        )
        committed = entry.persist_success(success)
        ScoringAdmissionRegistry.release_terminal(
            repository=self._repository,
            job_id=job.job_id,
            attempt_count=job.attempt_count,
        )
        return committed


    # Private compatibility seam for the already-approved Phase G test suite.
    # It exposes the same runtime-local entry, never a repository capability.
    def _trusted_scoring_committer(
        self, *, job_id: str, owner: str, pipeline_version: str
    ) -> TrustedPersistenceEntry:
        return self._trusted_persistence_entry(
            job_id=job_id, owner=owner, pipeline_version=pipeline_version
        )

    @staticmethod
    def _video_metadata(record: object) -> VideoMetadata:
        values = {
            name: getattr(record, name)
            for name in (
                "video_id", "channel_id", "channel_name", "title", "description",
                "source_url", "published_at", "duration_seconds", "default_language",
                "available_languages", "live_status", "availability",
            )
        }
        if any(
            values[name] is None
            for name in (
                "channel_name", "title", "source_url", "published_at", "duration_seconds",
                "live_status", "availability",
            )
        ):
            raise ValueError("persisted video metadata is incomplete")
        return VideoMetadata.model_validate(values)

    def _transcript_service(self, job: JobRecord) -> SubtitleAcquisitionService:
        if job.video_id is None:
            raise ValueError("transcript job is missing its video identity")
        return SubtitleAcquisitionService(
            adapter=self._dependencies.subtitle_adapter_factory(),
            repository=self._repository,
            data_root=self._data_root,
            context=TranscriptJobContext(
                job_id=job.job_id,
                owner=self._runtime_owner,
                pipeline_version=PIPELINE_VERSION,
                refresh_generation=self._repository.transcript_refresh_generation(
                    job.video_id
                ),
            ),
            clock=_utcnow,
        )

    def _load_transcript(self, job: JobRecord, video: VideoMetadata) -> TranscriptReady:
        return self._transcript_service(job).load_verified_transcript(
            video, self._config.settings.general.transcript_languages
        )

    def _verified_artifact(self, record: ArtifactRecord, *, max_bytes: int) -> bytes:
        if (
            record.storage_root is not StorageRoot.DATA
            or record.deleted_at is not None
            or not record.relative_path
        ):
            raise ValueError("persisted artifact index is invalid")
        relative = PurePosixPath(record.relative_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in record.relative_path:
            raise ValueError("persisted artifact path is unsafe")
        path = self._data_root.joinpath(*relative.parts)
        current = path
        while current != self._data_root:
            if current.is_symlink():
                raise ValueError("persisted artifact path is unsafe")
            current = current.parent
        body = path.read_bytes()
        if len(body) > max_bytes or hashlib.sha256(body).hexdigest() != record.content_hash:
            raise ValueError("persisted artifact hash is invalid")
        return body

    def _validate_scoring_provenance(
        self, artifact: ArtifactRecord, result: ScoreResult, video_id: str
    ) -> None:
        """Fail-closed provenance check before Runtime reuses a persisted score."""

        accepted_structured_producers = {
            _STRUCTURED_ARTIFACT_PRODUCER_VERSION,
            _G_STRUCTURED_ARTIFACT_PRODUCER_VERSION,
        }
        if (
            artifact.video_id != video_id
            or artifact.kind is not ArtifactKind.SCORING_STRUCTURED
            or artifact.artifact_key != f"scoring/{result.request_hash}/structured"
            or artifact.producer_version not in accepted_structured_producers
            or artifact.provider != "ollama"
            or artifact.provider != result.provider
            or artifact.model is None
            or artifact.model != result.model
            or not artifact.job_id
        ):
            raise ValueError("persisted scoring artifact identity is invalid")
        job = self._repository.get_job(artifact.job_id)
        if (
            job is None
            or job.video_id != video_id
            or job.target_stage is not ProcessingStage.SCORING
            or job.pipeline_version != PIPELINE_VERSION
            or job.status is not JobStatus.SUCCEEDED
        ):
            raise ValueError("persisted scoring job provenance is invalid")
        provider_call = self._repository.get_provider_call(result.request_hash)
        accepted_result_schema_versions = {SCHEMA_VERSION, _SCORING_SCHEMA_VERSION}
        accepted_result_prompt_versions = {PROMPT_VERSION, _SCORING_PROMPT_VERSION}
        if (
            provider_call is None
            or provider_call.status is not ProviderCallStatus.SUCCEEDED
            or provider_call.operation != "local-scoring"
            or provider_call.provider != "ollama"
            or provider_call.provider != result.provider
            or provider_call.model != result.model
            or provider_call.prompt_version != PROMPT_VERSION
            or provider_call.schema_version != SCHEMA_VERSION
            or provider_call.request_hash != result.request_hash
            or not provider_call.response_artifact_id
            or result.schema_version not in accepted_result_schema_versions
            or result.prompt_version not in accepted_result_prompt_versions
        ):
            raise ValueError("persisted scoring provider call provenance is invalid")
        raw = self._repository.get_artifact_by_key(
            f"scoring/{result.request_hash}/raw"
        )
        accepted_raw_producers = {
            _RAW_ARTIFACT_PRODUCER_VERSION,
            _G_RAW_ARTIFACT_PRODUCER_VERSION,
        }
        if (
            raw is None
            or raw.artifact_id != provider_call.response_artifact_id
            or raw.kind is not ArtifactKind.SCORING_RAW
            or raw.video_id != video_id
            or raw.job_id != artifact.job_id
            or raw.provider != result.provider
            or raw.provider != artifact.provider
            or raw.model != result.model
            or raw.model != artifact.model
            or raw.producer_version not in accepted_raw_producers
        ):
            raise ValueError("persisted scoring raw artifact provenance is invalid")
        if result.model != self._config.settings.local_scoring.model:
            raise ValueError("persisted scoring model does not match current configuration")
        if result.output_language != self._config.settings.general.output_language:
            raise ValueError(
                "persisted scoring output language does not match current configuration"
            )
        self._verified_artifact(raw, max_bytes=1_000_000)

    def _validate_analysis_provenance(
        self, artifact: ArtifactRecord, result: AnalysisResult, video_id: str
    ) -> None:
        """Fail-closed provenance check before Runtime reuses persisted analysis."""

        if (
            artifact.video_id != video_id
            or artifact.kind is not ArtifactKind.ANALYSIS_STRUCTURED
            or artifact.artifact_key != f"analysis/{result.request_hash}/structured"
            or artifact.producer_version != "analysis-structured-v1"
            or artifact.provider != self._config.settings.cloud.provider
            or artifact.provider != result.provider
            or artifact.model is None
            or artifact.model != result.model
            or not artifact.job_id
        ):
            raise ValueError("persisted analysis artifact identity is invalid")
        job = self._repository.get_job(artifact.job_id)
        if (
            job is None
            or job.video_id != video_id
            or job.target_stage is not ProcessingStage.ANALYSIS
            or job.pipeline_version != PIPELINE_VERSION
            or job.status is not JobStatus.SUCCEEDED
        ):
            raise ValueError("persisted analysis job provenance is invalid")
        provider_call = self._repository.get_provider_call(result.request_hash)
        if (
            provider_call is None
            or provider_call.status is not ProviderCallStatus.SUCCEEDED
            or provider_call.operation != "cloud-analysis"
            or provider_call.provider != "openai"
            or provider_call.provider != result.provider
            or provider_call.model != result.model
            or provider_call.prompt_version != "analysis-prompt-v1"
            or provider_call.prompt_version != result.prompt_version
            or provider_call.schema_version != "analysis-result-v1"
            or provider_call.schema_version != result.schema_version
            or provider_call.request_hash != result.request_hash
            or not provider_call.response_artifact_id
        ):
            raise ValueError("persisted analysis provider call provenance is invalid")
        raw = self._repository.get_artifact_by_key(
            f"analysis/{result.request_hash}/raw"
        )
        if (
            raw is None
            or raw.artifact_id != provider_call.response_artifact_id
            or raw.kind is not ArtifactKind.ANALYSIS_RAW
            or raw.video_id != video_id
            or raw.job_id != artifact.job_id
            or raw.provider != result.provider
            or raw.provider != artifact.provider
            or raw.model != result.model
            or raw.model != artifact.model
            or raw.producer_version != "analysis-raw-v1"
        ):
            raise ValueError("persisted analysis raw artifact provenance is invalid")
        if result.model != self._config.settings.cloud.model:
            raise ValueError("persisted analysis model does not match current configuration")
        if result.provider != self._config.settings.cloud.provider:
            raise ValueError("persisted analysis provider does not match current configuration")
        self._verified_artifact(raw, max_bytes=1_000_000)

    def _load_scoring(self, video_id: str) -> ScoringOutcome:
        artifact = self._repository.latest_artifact(video_id, ArtifactKind.SCORING_STRUCTURED)
        if artifact is None:
            raise ValueError("persisted score is unavailable")
        result = validate_score_result_json(
            self._verified_artifact(artifact, max_bytes=1_000_000)
        )
        self._validate_scoring_provenance(artifact, result, video_id)
        decision = result.score >= self._config.settings.thresholds.summary_score
        return ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=self._config.settings.thresholds.summary_score,
                final_should_summarize=decision,
                model_disagrees=result.should_summarize is not decision,
            ),
            call=ProviderCallMetadata(
                provider=result.provider,
                model=result.model,
                started_at=artifact.created_at,
                finished_at=artifact.created_at,
            ),
        )

    def _load_analysis(self, video_id: str) -> AnalysisOutcome:
        if not self._config.settings.cloud.enabled:
            return AnalysisSkipped(
                reason=AnalysisSkipReason.CLOUD_DISABLED,
                call=None,
                safe_message="cloud analysis is disabled",
            )
        artifact = self._repository.latest_artifact(video_id, ArtifactKind.ANALYSIS_STRUCTURED)
        if artifact is None:
            raise ValueError("persisted analysis is unavailable")
        result = AnalysisResult.model_validate_json(
            self._verified_artifact(artifact, max_bytes=1_000_000)
        )
        self._validate_analysis_provenance(artifact, result, video_id)
        return AnalysisCompleted(
            result=result,
            call=ProviderCallMetadata(
                provider=result.provider,
                model=result.model,
                started_at=artifact.created_at,
                finished_at=artifact.created_at,
            ),
        )

    def _orchestrator(self) -> PipelineOrchestrator:
        owner = self._runtime_owner

        def metadata_stage(job: JobRecord, _record: VideoRecord) -> None:
            metadata = self._discovery.fetch_and_store_metadata(
                job.video_id or "", pipeline_version=PIPELINE_VERSION, now=_utcnow()
            )
            current = self._repository.get_video(metadata.video_id)
            if current is None:
                raise ValueError("metadata stage lost its video")
            self._repository.complete_stage(
                job_id=job.job_id, owner=owner, video_id=metadata.video_id,
                expected_status=PipelineStatus.DISCOVERED,
                target_status=PipelineStatus.METADATA_READY,
                pipeline_version=PIPELINE_VERSION, artifacts=(), provider_call=None,
                now=_utcnow(),
            )

        def transcript_stage(job: JobRecord, record: VideoRecord) -> None:
            video = self._video_metadata(record)
            if video.duration_seconds > (
                self._config.settings.execution.max_video_duration_minutes * 60
            ):
                self._repository.complete_stage(
                    job_id=job.job_id,
                    owner=owner,
                    video_id=video.video_id,
                    expected_status=PipelineStatus.METADATA_READY,
                    target_status=PipelineStatus.SKIPPED_DURATION_LIMIT,
                    pipeline_version=PIPELINE_VERSION,
                    artifacts=(),
                    provider_call=None,
                    now=_utcnow(),
                )
                return
            result = self._transcript_service(job).fetch(
                video, self._config.settings.general.transcript_languages
            )
            if isinstance(result, TranscriptionRequired):
                raise TranscriptError(
                    AppError(
                        code=ErrorCode.CONTENT_UNAVAILABLE,
                        message=(
                            "no usable subtitle is available; managed audio "
                            "transcription is not yet composed"
                        ),
                        retryable=False,
                        video_id=video.video_id,
                        stage=ProcessingStage.TRANSCRIPT,
                    )
                )

        def scoring_stage(job: JobRecord, record: VideoRecord) -> None:
            video = self._video_metadata(record)
            transcript = self._load_transcript(job, video).artifact
            artifact = self._repository.latest_artifact(
                video.video_id, ArtifactKind.TRANSCRIPT_CANONICAL
            )
            if artifact is None:
                raise ValueError("transcript is unavailable")
            text = self._verified_artifact(
                artifact,
                max_bytes=4_000_000,
            ).decode("utf-8")
            configured_output_language = self._config.settings.general.output_language
            scoring_input = build_scoring_input(
                video=video,
                transcript_text=text,
                language=transcript.language,
                output_language=configured_output_language,
                settings=self._config.settings.local_scoring,
            )
            admission = self._scoring_admission_for(job.job_id)
            if type(admission) is not ScoringDispatchAdmission:
                raise ValueError("runtime scoring admission is invalid")
            primary_identity = build_primary_scoring_dispatch_identity(
                scoring_input=scoring_input,
                context=self._trusted_scoring_context,
            )
            admission.admit(primary_identity, now=_utcnow())
            provider = self._create_scoring_provider_for_dispatch()
            attempt = self._dispatch_primary_attempt_after_admission(provider, scoring_input)
            success = self.run_primary_trusted_scoring(
                attempt=attempt,
                scoring_input=scoring_input,
                job_id=job.job_id,
            )
            self._persist_trusted_scoring_success(
                success=success,
                job=job,
                owner=owner,
                pipeline_version=PIPELINE_VERSION,
            )

        def analysis_stage(job: JobRecord, record: VideoRecord) -> AnalysisOutcome | None:
            if not self._config.settings.cloud.enabled:
                return AnalysisSkipped(
                    reason=AnalysisSkipReason.CLOUD_DISABLED,
                    call=None,
                    safe_message="cloud analysis is disabled",
                )
            video = self._video_metadata(record)
            transcript = self._load_transcript(job, video).artifact
            artifact = self._repository.latest_artifact(video.video_id, ArtifactKind.TRANSCRIPT_CANONICAL)
            if artifact is None:
                raise ValueError("transcript is unavailable")
            text = self._verified_artifact(artifact, max_bytes=4_000_000).decode("utf-8")
            return RepositoryBackedAnalysisService(
                provider=self._dependencies.analysis_provider_factory(),
                settings=self._config.settings.cloud,
                repository=self._repository,
                context=AnalysisJobContext(job.job_id, owner, PIPELINE_VERSION),
                artifact_root=self._data_root,
                credential_resolver=EnvironmentCredentialResolver(),
                budget=CloudCallBudget(limit=self._config.settings.cloud.max_calls_per_run),
            ).analyze(
                video=video,
                transcript_text=text,
                language=transcript.language,
                output_language=self._config.settings.general.output_language,
            )

        def note_stage(job: JobRecord, record: VideoRecord) -> None:
            video = self._video_metadata(record)
            transcript = self._load_transcript(job, video).artifact
            ObsidianNoteSink(
                vault_root=Path(self._config.settings.storage.vault_root),
                vault_subdir=self._config.settings.storage.vault_subdir,
                repository=self._repository,
                context=NoteWriteContext(job.job_id, owner, PIPELINE_VERSION),
            ).upsert_video_note(
                video=video,
                transcript=transcript,
                scoring=self._load_scoring(video.video_id),
                analysis=self._load_analysis(video.video_id),
                processed_at=_utcnow(),
                pipeline_version=PIPELINE_VERSION,
            )

        retry = self._config.settings.retry
        return PipelineOrchestrator(
            repository=self._repository,
            planner=PipelineJobPlanner(
                repository=self._repository,
                pipeline_version=PIPELINE_VERSION,
                max_attempts=retry.max_attempts,
            ),
            owner=owner,
            lease_seconds=300,
            retry_policy=RetryPolicy(
                base_delay_seconds=retry.base_delay_seconds,
                max_delay_seconds=retry.max_delay_seconds,
                jitter_ratio=retry.jitter_ratio,
            ),
            handlers={
                ProcessingStage.METADATA: metadata_stage,
                ProcessingStage.TRANSCRIPT: transcript_stage,
                ProcessingStage.SCORING: scoring_stage,
                ProcessingStage.ANALYSIS: analysis_stage,
                ProcessingStage.NOTE_WRITE: note_stage,
            },
            clock=_utcnow,
        )

    def check(self, *, channel: str | None, limit: int | None) -> CommandOutcome:
        selected = tuple(
            item
            for item in self._config.channels
            if item.enabled and (channel is None or item.channel_id == channel)
        )
        if not selected:
            return CommandOutcome(
                prerequisite_failed=True,
                safe_message="No enabled configured channel matches the request.",
            )
        attempted = 0
        failed = 0
        discovered = 0
        remaining = limit
        for item in selected:
            attempted += 1
            try:
                batch = self._discovery.discover_and_save(
                    ChannelRef(
                        channel_id=item.channel_id,
                        enabled=item.enabled,
                        priority=item.priority,
                    ),
                    pipeline_version=PIPELINE_VERSION,
                    now=_utcnow(),
                    limit=remaining,
                )
                identifiers = batch.video_ids
                if remaining is not None:
                    remaining -= len(identifiers)
                discovered += len(identifiers)
                if remaining == 0:
                    break
            except Exception:
                failed += 1
        return CommandOutcome(
            attempted=attempted,
            failed=failed,
            safe_message=(
                f"Discovered {discovered} video(s) from {attempted - failed} channel(s)."
                if failed == 0
                else f"Discovered {discovered} video(s); {failed} channel(s) failed."
            ),
        )

    def process(self, *, video: str | None, resume: bool) -> CommandOutcome:
        del resume
        selected: tuple[VideoRecord, ...]
        if video is not None:
            candidate = self._repository.get_video(video)
            selected = () if candidate is None else (candidate,)
        else:
            selected = self._repository.list_videos_for_processing(
                pipeline_version=PIPELINE_VERSION
            )
        if not selected:
            return CommandOutcome(
                prerequisite_failed=True,
                safe_message="No discovered video is available. Run `youtube-intel check` first.",
            )
        failed = 0
        orchestrator = self._orchestrator()
        for record in selected:
            orchestrator.resume_video(record.video_id)
            saved = self._repository.get_video(record.video_id)
            if saved is None or saved.pipeline_status not in {
                PipelineStatus.COMPLETE,
                PipelineStatus.SKIPPED_DURATION_LIMIT,
            }:
                failed += 1
        if failed:
            failed_record = next(
                (
                    item
                    for item in selected
                    if (
                        (saved := self._repository.get_video(item.video_id)) is None
                        or saved.pipeline_status
                        not in {
                            PipelineStatus.COMPLETE,
                            PipelineStatus.SKIPPED_DURATION_LIMIT,
                        }
                    )
                ),
                selected[0],
            )
            persisted = self._repository.get_video(failed_record.video_id)
            target_stage = (
                None
                if persisted is None
                else PipelineJobPlanner.next_stage(persisted)
            )
            latest = self._repository.latest_video_job(
                failed_record.video_id,
                target_stage=target_stage,
            )
            stage = "unknown" if latest is None else latest.target_stage.value.lower()
            error = "prerequisite unavailable" if latest is None else (latest.last_error_message or "stage failed")
            return CommandOutcome(
                attempted=len(selected), failed=failed,
                safe_message=f"Processing stopped at {stage}: {error}. Run `youtube-intel doctor` for prerequisites.",
            )
        return CommandOutcome(
            attempted=len(selected),
            safe_message=f"Processed {len(selected)} video(s) to a terminal state.",
        )

    def retry(self, *, video: str | None, failed_only: bool) -> CommandOutcome:
        del failed_only
        jobs = self._repository.list_failed_video_jobs()
        selected = tuple(
            job
            for job in jobs
            if (
                job.status is JobStatus.FAILED_FINAL
                and job.video_id is not None
                and (video is None or job.video_id == video)
                and (
                    (record := self._repository.get_video(job.video_id)) is not None
                    and PipelineJobPlanner.next_stage(record) is job.target_stage
                )
            )
        )
        if not selected:
            return CommandOutcome(safe_message="No final failed video job is available to retry.")
        for job in selected:
            self._repository.rerun_job(
                job.job_id,
                new_job_id=f"retry-{os.urandom(16).hex()}",
                available_at=_utcnow(),
                now=_utcnow(),
            )
        return self.process(video=video, resume=True)

    def weekly(self, *, week: str | None) -> CommandOutcome:
        if week is not None:
            return CommandOutcome(
                prerequisite_failed=True,
                safe_message="Historical --week generation is not available; omit --week for the current ISO week.",
            )
        report = WeeklyReportService(
            repository=self._repository,
            sink=ObsidianNoteSink(
                vault_root=Path(self._config.settings.storage.vault_root),
                vault_subdir=self._config.settings.storage.vault_subdir,
                repository=self._repository,
                context=NoteWriteContext("weekly-runtime", "youtube-intel-runtime", PIPELINE_VERSION),
            ),
            artifact_root=self._data_root,
            timezone=self._config.settings.general.timezone,
            top_n=self._config.settings.weekly.top_n,
        ).generate(now=_utcnow())
        return CommandOutcome(
            attempted=1,
            safe_message=f"Weekly report written to {report.note_ref.relative_path}.",
        )


def create_runtime_operations(config: AppConfig, project_root: Path) -> RuntimeOperations:
    return RuntimeOperations(config=config, project_root=project_root)


def _database_check(path: Path) -> DoctorCheck:
    if not path.is_file():
        return DoctorCheck(
            "SQLite",
            "FAIL",
            "state database is missing. Run `youtube-intel check` to initialize it.",
            True,
        )
    try:
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if integrity != ("ok",) or version != 1:
            raise sqlite3.DatabaseError
    except (OSError, sqlite3.Error):
        return DoctorCheck("SQLite", "FAIL", "state database is invalid.", True)
    return DoctorCheck("SQLite", "PASS", "schema and integrity check passed.", False)


def _ollama_check(config: AppConfig) -> tuple[DoctorCheck, DoctorCheck]:
    settings = config.settings.local_scoring
    request = urllib.request.Request(
        settings.base_url + "/api/tags", headers={"Accept": "application/json"}, method="GET"
    )
    try:
        with urllib.request.urlopen(  # noqa: S310 — base_url is config-validated loopback only
            request, timeout=min(config.settings.timeouts.http_seconds, 3.0)
        ) as response:
            body = response.read(_MAX_OLLAMA_TAGS_BYTES + 1)
        if len(body) > _MAX_OLLAMA_TAGS_BYTES:
            raise ValueError
        payload = json.loads(body.decode("utf-8"))
        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise ValueError
    except (OSError, TimeoutError, urllib.error.URLError, ValueError, json.JSONDecodeError):
        unavailable = DoctorCheck(
            "Ollama", "FAIL", "loopback service is unavailable or invalid.", True
        )
        return unavailable, DoctorCheck(
            "Local scoring model", "FAIL", "model cannot be verified until Ollama is available.", True
        )
    matched = any(
        isinstance(item, dict)
        and item.get("name") == settings.model
        and (
            item.get("digest") == settings.expected_model_digest
            or f"sha256:{item.get('digest')}" == settings.expected_model_digest
        )
        for item in models
    )
    return (
        DoctorCheck("Ollama", "PASS", "loopback service responded safely.", False),
        DoctorCheck(
            "Local scoring model",
            "PASS" if matched else "FAIL",
            "configured model and digest are available."
            if matched
            else "configured model is missing or has a different digest.",
            not matched,
        ),
    )


def doctor(config: AppConfig, project_root: Path) -> DoctorReport:
    """Inspect prerequisites without creating files, jobs, logs, or directories."""

    root = project_root.resolve(strict=True)
    storage = config.settings.storage
    data_root = _safe_project_path(root, storage.data_dir)
    vault_root = Path(storage.vault_root)
    managed_vault = vault_root / storage.vault_subdir
    checks = [
        DoctorCheck("Config", "PASS", "configuration is valid.", False),
        DoctorCheck(
            "Data directory",
            "PASS" if data_root.is_dir() else "FAIL",
            "project data directory exists."
            if data_root.is_dir()
            else "project data directory is missing; a business command will create it.",
            not data_root.is_dir(),
        ),
        _database_check(data_root / "state.sqlite"),
        DoctorCheck(
            "Vault",
            "PASS" if vault_root.is_dir() and managed_vault.is_dir() else "FAIL",
            "managed test Vault directory exists."
            if vault_root.is_dir() and managed_vault.is_dir()
            else "Vault root or managed subdirectory is missing.",
            not (vault_root.is_dir() and managed_vault.is_dir()),
        ),
        DoctorCheck(
            "yt-dlp",
            "PASS" if importlib.util.find_spec("yt_dlp") is not None else "FAIL",
            "Python provider is installed."
            if importlib.util.find_spec("yt_dlp") is not None
            else "Python provider is not installed.",
            importlib.util.find_spec("yt_dlp") is None,
        ),
        DoctorCheck(
            "MLX Whisper",
            "PASS" if importlib.util.find_spec("mlx_whisper") is not None else "FAIL",
            "runtime package is installed; model weights are checked only when transcription is needed."
            if importlib.util.find_spec("mlx_whisper") is not None
            else "runtime package is not installed.",
            importlib.util.find_spec("mlx_whisper") is None,
        ),
    ]
    checks.extend(_ollama_check(config))
    checks.append(
        DoctorCheck(
            "Cloud",
            "OFF" if not config.settings.cloud.enabled else "ON",
            "cloud analysis is disabled; no credential will be read."
            if not config.settings.cloud.enabled
            else "cloud analysis is enabled and requires separate credential authorization.",
            False,
        )
    )
    return DoctorReport(tuple(checks))


__all__ = [
    "DoctorCheck",
    "DoctorReport",
    "RuntimeDependencies",
    "RuntimeOperations",
    "bootstrap_runtime",
    "create_runtime_operations",
    "doctor",
]
