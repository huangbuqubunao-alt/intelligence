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
from typing import Any, Callable, NoReturn, cast

from youtube_intel.analysis import (
    AnalysisJobContext,
    CloudCallBudget,
    EnvironmentCredentialResolver,
    RepositoryBackedAnalysisService,
    tokenizer_resource_status,
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
    ContentQualityStatus,
    DeterministicGateReason,
    ErrorCode,
    JobStatus,
    MetadataProvider,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    ScoringCandidate,
    ScoringEvidenceSource,
    ScoringInput,
    ScoringOutcome,
    ScoringOutputLanguage,
    SourceProvider,
    TranscriptionRequired,
    TranscriptReady,
    VideoMetadata,
    scoring_reason_matches_output_language,
)
from youtube_intel.h2_evidence import (
    H2_ELIGIBLE_PARSER_CODES,
    CandidateEvidence,
    JudgeEvidence,
    NotApplicableEvidence,
    PhaseH2BValidatedRepairResult,
    PrimaryFailureClass,
    PrimaryFailureEvidence,
    PrimaryTrustedContext,
    RepairCandidateEvidence,
    RepairFinalizerBinding,
    RepairNormalizedInput,
    RepairProviderEvidence,
    RepairQualityEvidence,
    build_h2c_settings_provenance,
    build_judge_evidence,
    build_primary_trusted_context,
    build_repair_normalized_input,
    build_repair_request_hash,
    derive_repair_judge_trusted_context,
    h2_canonical_bytes,
    repair_normalized_input_hash,
    replay_language_validation,
    replay_primary_parser_failure,
    verify_judge_evidence_replay,
    verify_primary_failure_evidence,
)
from youtube_intel.h2_jcs import jcs_loads_strict
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.operations import CommandOutcome, ExitCode, Operations
from youtube_intel.output_language import OutputLanguagePreferenceService
from youtube_intel.pipeline import PipelineOrchestrator, StageDisposition
from youtube_intel.providers.cloud_llm import OpenAIResponsesProvider
from youtube_intel.providers.obsidian import NoteWriteContext, ObsidianNoteSink
from youtube_intel.providers.ollama import (
    OllamaQualityJudgeProvider,
    OllamaScoringProvider,
    PrimaryRawCapture,
    build_quality_judge_generate_body,
    build_task016c_repair_generate_body,
    parse_scoring_candidate,
    render_task016c_repair_prompt_v2,
    seal_judge_raw_capture,
    seal_primary_raw_capture,
    verify_judge_model_content,
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
    RepairFinalizationInvalid,
    RepairTrustedScoringFinalizer,
    TrustedScoreResult,
    TrustedScoringContext,
    _mint_quality_provenance_authority,
    _mint_trusted_scoring_context,
    build_content_quality_input_hash,
    build_quality_pass_attestation,
    build_scoring_candidate_hash,
    verify_quality_pass_attestation,
)
from youtube_intel.reporting import WeeklyReportService
from youtube_intel.retry import RetryPolicy
from youtube_intel.scoring import (
    _SCORING_OPERATION,
    H2C_REPLAY_INVALID_REASONS,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    AuthoritativeScoringReader,
    H2CStaleScoringLease,
    PhaseFTrustedScoringSuccess,
    PhaseHTrustedRepairSuccess,
    PrimaryScoringAttempt,
    ScoringJobContext,
    TrustedPersistenceEntry,
    _H2CEnvelopeOversize,
    _H2CLineageTerminalHandled,
    _mint_phase_h_trusted_repair_success,
    _run_primary_trusted_scoring_seam,
    build_repair_composite_envelope,
    build_scoring_input,
    build_scoring_request_identity,
    h2c_replay_invalid_detail,
)
from youtube_intel.scoring_admission import (
    ScoringAdmissionRegistry,
    ScoringDispatchAdmission,
    ScoringDispatchDenied,
    ScoringDispatchIdentity,
    ScoringDispatchRole,
    UnknownProviderState,
    build_judge_scoring_dispatch_identity,
    build_primary_scoring_dispatch_identity,
)
from youtube_intel.state import (
    SCORING_LINEAGE_VERSION_V1,
    ArtifactKind,
    ArtifactRecord,
    JobRecord,
    LeaseConflict,
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
from youtube_intel.verified_note_v2 import _bind_verified_note_v2_runtime


class _KnownPrimaryFailure(ValueError):
    """A received PRIMARY response failed locally without exposing repair authority."""

    def __init__(
        self,
        message: str = "received PRIMARY response is ineligible for trusted scoring",
    ) -> None:
        super().__init__(message)
        self.error = AppError(
            code=ErrorCode.INVALID_RESPONSE,
            message=message,
            retryable=False,
            stage=ProcessingStage.SCORING,
        )


class _H2CReplayInvalid(Exception):
    """One closed H2-C replay/pre-entry integrity predicate failed.

    Carries exactly one approved reason literal from the closed
    ``H2C_REPLAY_INVALID:<REASON>`` set; the continuation maps it to one
    owner-authoritative ``TRUST_INTEGRITY_INVALID`` terminal.  Construction
    itself enforces the closed set: an arbitrary reason is rejected before
    any terminal emission can occur.
    """

    def __init__(self, reason: str) -> None:
        if reason not in H2C_REPLAY_INVALID_REASONS:
            msg = f"H2-C replay reason is not in the closed set: {reason!r}"
            raise ValueError(msg)
        super().__init__(reason)
        self.reason = reason


class _H2CSettingsBoundExceeded(Exception):
    """Current settings exceed an H2-C persistence admission ceiling."""


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


def _build_trusted_scoring_context(
    config: AppConfig, output_language: ScoringOutputLanguage | None = None
) -> TrustedScoringContext:
    """Mint one batch-stable scoring context from config + effective preference."""

    local_scoring = config.settings.local_scoring
    effective_language = output_language or config.settings.general.output_language
    return _mint_trusted_scoring_context(
        sentinel=_TRUSTED_SCORING_CONTEXT_SENTINEL,
        scoring_provider=_JUDGE_PROVIDER,
        scoring_model=local_scoring.model,
        scoring_model_digest=local_scoring.expected_model_digest,
        output_language=effective_language,
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
    scoring_prompt = (
        resources.files("youtube_intel")
        .joinpath("prompts", "scoring.md")
        .read_text(encoding="utf-8")
    )
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
        self._output_language_service = OutputLanguagePreferenceService(
            self._repository,
            bootstrap_default=config.settings.general.output_language,
        )
        self._effective_output_language = (
            self._output_language_service.effective().value
        )
        self._trusted_scoring_context = _build_trusted_scoring_context(
            config, self._effective_output_language
        )
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
        # H2-B is memory-only: the PRIMARY Judge raw evidence used to classify
        # an eligible Judge failure is retained for classification within the
        # live execution.  The H2-B aggregate is never retained: it is a
        # lexical local of the scoring frame, and the current staged build
        # terminalizes an H2-B-only PASS with CAPABILITY_UNAVAILABLE /
        # H2B_PASS_AWAITING_H2C (a future separately authorized H2-C will
        # replace that terminalization with the immediate lexical handoff).
        self._last_primary_judge_raw: str | None = None
        self._last_primary_judge_operation: QualityJudgeOperationInput | None = None
        self._last_primary_judge_input: ContentQualityInput | None = None
        self._last_primary_judge_result: Any = None

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
        # Runtime-owned evidence for the H2-B eligibility classification of an
        # eligible PRIMARY Judge failure; memory-only, never restored.
        self._last_primary_judge_operation = quality_operation
        self._last_primary_judge_input = quality_input
        self._last_primary_judge_result = quality_result
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
            result = provider.judge(
                operation_input,
                content_input=content_input,
            )
        except Exception as error:
            raise UnknownProviderState(
                "scoring provider outcome is unknown after external dispatch"
            ) from error
        # Preserve the exact Judge raw model content, when the provider
        # established trustworthy raw, as runtime-owned evidence for the H2-B
        # eligibility classification of an eligible PRIMARY Judge failure.
        self._last_primary_judge_raw = None
        consume_raw = getattr(provider, "consume_extracted_judge_model_content", None)
        if callable(consume_raw):
            self._last_primary_judge_raw = consume_raw()
        return result

    def _create_quality_judge_provider_for_dispatch(self) -> Any:
        """Construct the Judge client before the admitted external call begins."""

        try:
            factory = self._dependencies.quality_judge_provider_factory
            if factory is not None:
                return factory()
            return OllamaQualityJudgeProvider(
                settings=self._config.settings.local_scoring
            )
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

    # ------------------------------------------------------------------
    # TASK-016C Phase H2-B — runtime REPAIR control flow.
    #
    # These methods are PRIVATE and runtime-owned.  REPAIR eligibility arises
    # only inside the actual PRIMARY failure branch of the scoring stage; there
    # is no caller-facing repair entry point, no repair token/receipt/registry,
    # and no persistence.  H2-B stops at an untrusted in-memory evidence
    # aggregate (or a known-terminal FAILED_FINAL job); it never mints a trusted
    # repair success and never persists.  H2-C is not implemented here.
    # ------------------------------------------------------------------

    def _h2b_local_scoring(self) -> LocalScoringSettings:
        return self._config.settings.local_scoring

    def _h2b_primary_trusted_context(
        self, scoring_input: ScoringInput
    ) -> PrimaryTrustedContext:
        settings = self._h2b_local_scoring()
        return build_primary_trusted_context(
            scoring_input=scoring_input,
            model=settings.model,
            model_digest=settings.expected_model_digest,
            temperature=settings.temperature,
            max_output_tokens=settings.max_output_tokens,
            max_description_chars=settings.max_description_chars,
        )

    def _h2b_eligible_parse_failure_capture(
        self, provider: Any
    ) -> PrimaryRawCapture | None:
        """Return a closed-class parse-failure raw capture, if one was produced.

        Only a post-capture deterministic parser failure is repair-eligible; the
        shared parser's diagnostic code must fall in the frozen H2-eligible set.
        Any other outcome (including UNKNOWN/ambiguous) yields ``None``.
        """

        from youtube_intel.providers.ollama import diagnose_scoring_parse_failure

        consume = getattr(provider, "consume_primary_parse_failure_capture", None)
        if not callable(consume):
            return None
        capture = consume()
        if type(capture) is not PrimaryRawCapture:
            return None
        code = diagnose_scoring_parse_failure(capture.utf8)
        if code is None or code not in H2_ELIGIBLE_PARSER_CODES:
            return None
        return capture

    def _h2b_pfe_base(
        self,
        *,
        trusted_context: PrimaryTrustedContext,
        scoring_input: ScoringInput,
        raw_utf8: str,
        failure_class: PrimaryFailureClass,
    ) -> dict[str, object]:
        """Return the shared PRIMARY provenance/raw fields of a PFE payload."""

        raw_bytes = raw_utf8.encode("utf-8", errors="strict")
        return {
            "schema_version": "task016c-primary-failure-evidence-v1",
            "primary_attempt_identity": "local-scoring",
            "primary_request_hash": trusted_context.request_hash,
            "primary_normalized_input_hash": trusted_context.normalized_input_hash,
            "primary_provider": trusted_context.provider,
            "primary_model": trusted_context.model,
            "primary_model_digest": trusted_context.model_digest,
            "primary_prompt_version": trusted_context.prompt_version,
            "primary_schema_version": trusted_context.schema_version,
            "primary_output_language": trusted_context.output_language,
            "primary_temperature": trusted_context.temperature,
            "primary_max_output_tokens": trusted_context.max_output_tokens,
            "primary_max_description_chars": trusted_context.max_description_chars,
            "primary_scoring_input": scoring_input,
            "primary_scoring_input_sha256": trusted_context.scoring_input_sha256,
            "primary_raw_capture_kind": "OLLAMA_GENERATE_HTTP_BODY_V1",
            "primary_raw_utf8": raw_utf8,
            "primary_raw_utf8_length": len(raw_bytes),
            "primary_raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "failure_class": failure_class,
        }

    @staticmethod
    def _h2b_candidate_evidence(attempt: PrimaryScoringAttempt) -> CandidateEvidence:
        return CandidateEvidence(
            schema_version="task016c-candidate-evidence-v1",
            kind="CANDIDATE",
            candidate=attempt.candidate,
            candidate_sha256=build_scoring_candidate_hash(attempt.candidate),
        )

    @staticmethod
    def _h2b_not_applicable() -> NotApplicableEvidence:
        return NotApplicableEvidence(kind="NOT_APPLICABLE")

    def _h2b_pfe_for_parse_failure(
        self,
        *,
        scoring_input: ScoringInput,
        capture: PrimaryRawCapture,
    ) -> PrimaryFailureEvidence | None:
        """Construct and verify PFE for an eligible SCHEMA_OR_PARSE failure.

        Pure eligibility classification only: this helper builds the
        ``PrimaryFailureEvidence`` from the runtime-captured PRIMARY raw body
        and immediately verifies it against the same runtime-owned trusted
        context/settings.  It grants no REPAIR admission, contacts no provider,
        and returns data only.  Returns ``None`` when the failure is not
        repair-eligible.
        """

        parser_evidence = replay_primary_parser_failure(capture.utf8)
        if parser_evidence is None:
            return None
        trusted_context = self._h2b_primary_trusted_context(scoring_input)
        base = self._h2b_pfe_base(
            trusted_context=trusted_context,
            scoring_input=scoring_input,
            raw_utf8=capture.utf8,
            failure_class=PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID,
        )
        pfe = PrimaryFailureEvidence.model_validate(
            {
                **base,
                "primary_candidate": self._h2b_not_applicable(),
                "parser_evidence": parser_evidence,
                "language_evidence": self._h2b_not_applicable(),
                "judge_evidence": self._h2b_not_applicable(),
            }
        )
        try:
            verify_primary_failure_evidence(
                pfe, trusted_context, self._h2b_local_scoring()
            )
        except ValueError:
            return None
        return pfe

    def _h2b_pfe_for_known_failure(
        self,
        *,
        scoring_input: ScoringInput,
        attempt: PrimaryScoringAttempt,
    ) -> PrimaryFailureEvidence | None:
        """Classify a closed eligible PRIMARY failure and seal its PFE.

        Pure eligibility classification only: returns ``None`` when the failure
        is not repair-eligible (so the caller re-raises the original known
        failure), or the immediately verified ``PrimaryFailureEvidence`` for one
        of the closed eligible classes.  This helper grants no REPAIR admission,
        contacts no provider, and returns data only.
        """

        trusted_context = self._h2b_primary_trusted_context(scoring_input)
        candidate = attempt.candidate
        language_ev = replay_language_validation(
            candidate=candidate,
            output_language=scoring_input.output_language,
        )
        if language_ev.result != "VALID":
            if language_ev.result != "INVALID":
                return None
            base = self._h2b_pfe_base(
                trusted_context=trusted_context,
                scoring_input=scoring_input,
                raw_utf8=attempt.final_raw_response,
                failure_class=PrimaryFailureClass.LANGUAGE_INVALID,
            )
            pfe = PrimaryFailureEvidence.model_validate(
                {
                    **base,
                    "primary_candidate": self._h2b_candidate_evidence(attempt),
                    "parser_evidence": self._h2b_not_applicable(),
                    "language_evidence": language_ev,
                    "judge_evidence": self._h2b_not_applicable(),
                }
            )
            try:
                verify_primary_failure_evidence(
                    pfe, trusted_context, self._h2b_local_scoring()
                )
            except ValueError:
                return None
            return pfe

        # Deterministic-quality rejection is never repair-eligible.
        candidate_hash = build_scoring_candidate_hash(candidate)
        quality_input = self._h2b_quality_input(
            scoring_input=scoring_input,
            candidate=candidate,
            candidate_hash=candidate_hash,
        )
        quality_input_hash = build_content_quality_input_hash(quality_input)
        gate_result = DeterministicContentQualityGate().evaluate(
            content=candidate.reason,
            candidate_hash=candidate_hash,
            quality_input_hash=quality_input_hash,
            scoring_request_hash=scoring_input.request_hash,
        )
        if gate_result is not None:
            return None

        # Judge-based failures require trustworthy Judge raw from the actual
        # PRIMARY Judge dispatch; without it the failure is not repair-eligible.
        judge_raw = self._last_primary_judge_raw
        judge_operation = self._last_primary_judge_operation
        judge_input = self._last_primary_judge_input
        if judge_raw is None or judge_operation is None or judge_input is None:
            return None
        try:
            judge_evidence = build_judge_evidence(
                role="PRIMARY",
                operation_input=judge_operation,
                judge_input=judge_input,
                raw_utf8=judge_raw,
                model=self._h2b_local_scoring().model,
                model_digest=self._h2b_local_scoring().expected_model_digest,
                policy_version=_QUALITY_POLICY_VERSION,
                prompt_version=_QUALITY_PROMPT_VERSION,
                operation_schema_version=_QUALITY_SCHEMA_VERSION,
            )
        except ValueError:
            return None
        status = judge_evidence.derived_result.status
        if status is ContentQualityStatus.REJECT:
            failure_class = PrimaryFailureClass.JUDGE_REJECT
        elif status is ContentQualityStatus.UNCERTAIN:
            failure_class = PrimaryFailureClass.JUDGE_UNCERTAIN
        else:
            return None
        base = self._h2b_pfe_base(
            trusted_context=trusted_context,
            scoring_input=scoring_input,
            raw_utf8=attempt.final_raw_response,
            failure_class=failure_class,
        )
        pfe = PrimaryFailureEvidence.model_validate(
            {
                **base,
                "primary_candidate": self._h2b_candidate_evidence(attempt),
                "parser_evidence": self._h2b_not_applicable(),
                "language_evidence": self._h2b_not_applicable(),
                "judge_evidence": judge_evidence,
            }
        )
        try:
            verify_primary_failure_evidence(
                pfe, trusted_context, self._h2b_local_scoring()
            )
        except ValueError:
            return None
        return pfe

    def _h2b_quality_input(
        self,
        *,
        scoring_input: ScoringInput,
        candidate: ScoringCandidate,
        candidate_hash: str,
    ) -> ContentQualityInput:
        return ContentQualityInput.model_validate(
            {
                "scoring_request_hash": scoring_input.request_hash,
                "candidate_hash": candidate_hash,
                "output_language": scoring_input.output_language,
                "reason": candidate.reason,
                "topics": list(candidate.topics),
                "evidence_registry": [
                    {
                        "evidence_id": "title-1",
                        "source": ScoringEvidenceSource.TITLE.value,
                        "excerpt": scoring_input.video.title,
                    }
                ],
            }
        )

    def _h2b_known_terminal_failure(
        self, *, job_id: str, detail: str
    ) -> StageDisposition:
        """Finalize a known H2-B failure as a non-retryable FAILED_FINAL job."""

        self._repository.fail_job(
            job_id,
            owner=self._runtime_owner,
            error_code=ErrorCode.INVALID_RESPONSE,
            error_message=detail,
            retry_at=None,
            now=_utcnow(),
        )
        confirmed = self._repository.get_job(job_id)
        if confirmed is None or confirmed.status is not JobStatus.FAILED_FINAL:
            raise UnknownProviderState(
                "known H2-B terminal failure could not be finalized"
            )
        return StageDisposition.TERMINAL

    @staticmethod
    def _h2b_extract_model_content(raw_utf8: str) -> str | None:
        try:
            payload = jcs_loads_strict(raw_utf8)
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        response = payload.get("response")
        if not isinstance(response, str):
            return None
        return response

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
                "video_id",
                "channel_id",
                "channel_name",
                "title",
                "description",
                "source_url",
                "published_at",
                "duration_seconds",
                "default_language",
                "available_languages",
                "live_status",
                "availability",
            )
        }
        if any(
            values[name] is None
            for name in (
                "channel_name",
                "title",
                "source_url",
                "published_at",
                "duration_seconds",
                "live_status",
                "availability",
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
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in record.relative_path
        ):
            raise ValueError("persisted artifact path is unsafe")
        path = self._data_root.joinpath(*relative.parts)
        current = path
        while current != self._data_root:
            if current.is_symlink():
                raise ValueError("persisted artifact path is unsafe")
            current = current.parent
        body = path.read_bytes()
        if (
            len(body) > max_bytes
            or hashlib.sha256(body).hexdigest() != record.content_hash
        ):
            raise ValueError("persisted artifact hash is invalid")
        return body

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
            raise ValueError(
                "persisted analysis model does not match current configuration"
            )
        if result.provider != self._config.settings.cloud.provider:
            raise ValueError(
                "persisted analysis provider does not match current configuration"
            )
        self._verified_artifact(raw, max_bytes=1_000_000)

    def _scoring_reader(self) -> AuthoritativeScoringReader:
        return AuthoritativeScoringReader(
            repository=self._repository,
            data_root=self._data_root,
            summary_threshold=self._config.settings.thresholds.summary_score,
            pipeline_version=PIPELINE_VERSION,
            current_model=self._config.settings.local_scoring.model,
        )

    def _load_scoring(self, video_id: str) -> ScoringOutcome:
        return self._scoring_reader().read(video_id).scoring_outcome

    def _downstream_output_language(
        self, video_id: str
    ) -> ScoringOutputLanguage:
        """Once scoring succeeds, downstream generation keeps that language."""

        language = self._load_scoring(video_id).result.output_language
        if language not in {"zh-CN", "en"}:
            raise ValueError("authoritative scoring language is unsupported")
        return language

    def _load_analysis(self, video_id: str) -> AnalysisOutcome:
        if not self._config.settings.cloud.enabled:
            return AnalysisSkipped(
                reason=AnalysisSkipReason.CLOUD_DISABLED,
                call=None,
                safe_message="cloud analysis is disabled",
            )
        artifact = self._repository.latest_artifact(
            video_id, ArtifactKind.ANALYSIS_STRUCTURED
        )
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
                job_id=job.job_id,
                owner=owner,
                video_id=metadata.video_id,
                expected_status=PipelineStatus.DISCOVERED,
                target_status=PipelineStatus.METADATA_READY,
                pipeline_version=PIPELINE_VERSION,
                artifacts=(),
                provider_call=None,
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

        def scoring_stage(
            job: JobRecord, record: VideoRecord
        ) -> StageDisposition | None:
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
            scoring_input = build_scoring_input(
                video=video,
                transcript_text=text,
                language=transcript.language,
                output_language=self._effective_output_language,
                settings=self._config.settings.local_scoring,
            )
            admission = self._scoring_admission_for(job.job_id)
            if type(admission) is not ScoringDispatchAdmission:
                raise ValueError("runtime scoring admission is invalid")
            primary_identity = build_primary_scoring_dispatch_identity(
                scoring_input=scoring_input,
                context=self._trusted_scoring_context,
            )

            def _h2b_repair_continuation(
                pfe: PrimaryFailureEvidence,
            ) -> StageDisposition | None:
                """The lexical H2-B REPAIR branch of exactly this PRIMARY attempt.

                Defined and invoked only inside this actual scoring-execution
                frame: it captures the runtime-owned job/lease/scoring input/
                admission of this frame and receives only the PFE constructed
                from this exact captured PRIMARY failure.  It is never exposed
                as a class/module attribute, so a forged PFE obtained anywhere
                else has no caller-facing H2-B ingress and cannot trigger a
                REPAIR.

                Ownership order: verified eligible PFE -> RNI/request/payload
                derivation -> state-only H1 REPAIR consumption -> same-frame
                identity/payload revalidation -> exact REPAIR dispatch ->
                raw/candidate/language/gate validation -> state-only
                REPAIR_JUDGE consumption -> same-frame Judge identity
                revalidation -> exact Judge dispatch -> Judge replay requiring
                PASS -> attestation -> REPAIR-aware finalization -> sealed
                structured evidence -> untrusted aggregate.  H2-B stops here:
                no persistence, no PhaseHTrustedRepairSuccess, no H2-C.
                """

                settings = self._h2b_local_scoring()
                trusted_context = self._h2b_primary_trusted_context(scoring_input)

                # Verify the sealed evidence against the same runtime-owned
                # context/settings (fail closed, before REPAIR contact).
                verify_primary_failure_evidence(pfe, trusted_context, settings)

                def _derive_repair_identity() -> tuple[
                    RepairNormalizedInput, str, str, str, bytes, bytes, str, int
                ]:
                    rni_local = build_repair_normalized_input(
                        job_id=job.job_id,
                        primary_trusted_context=trusted_context,
                        failure_evidence=pfe,
                        validated_settings=settings,
                    )
                    rni_hash_local = repair_normalized_input_hash(rni_local)
                    request_hash_local = build_repair_request_hash(rni_local)
                    rni_bytes_local = h2_canonical_bytes(rni_local)
                    pfe_bytes_local = h2_canonical_bytes(pfe)
                    si_bytes_local = h2_canonical_bytes(rni_local.scoring_input)
                    cand_ev_local: str | None = None
                    if isinstance(pfe.primary_candidate, CandidateEvidence):
                        cand_ev_local = h2_canonical_bytes(
                            pfe.primary_candidate
                        ).decode("utf-8")
                    extracted_local = self._h2b_extract_model_content(
                        pfe.primary_raw_utf8
                    )
                    prompt_local = render_task016c_repair_prompt_v2(
                        output_language=rni_local.output_language,
                        repair_request_hash=request_hash_local,
                        rni_jcs_utf8=rni_bytes_local.decode("utf-8"),
                        pfe_jcs_utf8=pfe_bytes_local.decode("utf-8"),
                        scoring_input_jcs_utf8=si_bytes_local.decode("utf-8"),
                        primary_raw_utf8=pfe.primary_raw_utf8,
                        candidate_evidence_jcs_utf8=cand_ev_local,
                        extracted_model_content=extracted_local,
                    )
                    body_local = build_task016c_repair_generate_body(
                        model=rni_local.repair_model,
                        prompt=prompt_local,
                        temperature=rni_local.temperature,
                        max_output_tokens=rni_local.max_output_tokens,
                    )
                    return (
                        rni_local,
                        rni_hash_local,
                        request_hash_local,
                        prompt_local,
                        rni_bytes_local,
                        body_local,
                        hashlib.sha256(body_local).hexdigest(),
                        len(body_local),
                    )

                (
                    rni,
                    rni_hash,
                    repair_request_hash,
                    prompt,
                    rni_bytes,
                    body,
                    body_sha256,
                    body_length,
                ) = _derive_repair_identity()

                # Defense-in-depth collision guards before admission.
                if repair_request_hash == trusted_context.request_hash:
                    raise ScoringDispatchDenied(
                        "REPAIR identity collides with the PRIMARY scoring identity"
                    )
                primary_judge_ev = pfe.judge_evidence
                if (
                    type(primary_judge_ev) is JudgeEvidence
                    and repair_request_hash == primary_judge_ev.judge_h2
                ):
                    raise ScoringDispatchDenied(
                        "REPAIR identity collides with the PRIMARY Judge identity"
                    )

                repair_identity = ScoringDispatchIdentity(
                    role=ScoringDispatchRole.REPAIR,
                    operation="local-scoring-repair-v1",
                    normalized_input_hash=rni_hash,
                    request_hash=repair_request_hash,
                )
                # State-only H1 REPAIR consumption (no callback authority).
                admission.consume_repair_role(repair_identity, now=_utcnow())

                # Immediately before first transport: recompute every identity
                # and payload value from the same runtime-owned values and
                # require exact equality with the pre-admission derivation.
                (
                    rni_re,
                    rni_hash_re,
                    request_hash_re,
                    prompt_re,
                    _rni_bytes_re,
                    body_re,
                    sha_re,
                    len_re,
                ) = _derive_repair_identity()
                if (
                    rni_re != rni
                    or rni_hash_re != rni_hash
                    or request_hash_re != repair_request_hash
                    or prompt_re != prompt
                    or body_re != body
                    or sha_re != body_sha256
                    or len_re != body_length
                ):
                    raise ScoringDispatchDenied(
                        "REPAIR identity or payload changed after admission"
                    )

                # Role-neutral transport: the runtime frame alone interprets
                # the returned raw bytes as this admitted REPAIR attempt.
                repair_provider = self._create_scoring_provider_for_dispatch()
                try:
                    raw_body = repair_provider.dispatch_exact_generate(
                        body=body, body_sha256=body_sha256, body_length=body_length
                    )
                except ScoringDispatchDenied:
                    raise
                except Exception as error:
                    raise UnknownProviderState(
                        "REPAIR provider outcome is unknown after external dispatch"
                    ) from error

                # Authoritative outer capture: strict UTF-8, bounded, full-body
                # hash, and strict outer protocol.  Ambiguity after contact is
                # UNKNOWN.
                try:
                    outer_capture = seal_primary_raw_capture(raw_body)
                except ValueError as error:
                    raise UnknownProviderState(
                        "REPAIR outer provider protocol is ambiguous after contact"
                    ) from error

                # Inner repaired candidate parse/schema: known deterministic
                # terminal; empty/whitespace content fails here before the gate.
                try:
                    repaired_candidate = parse_scoring_candidate(outer_capture.utf8)
                except ValueError:
                    return self._h2b_known_terminal_failure(
                        job_id=job.job_id, detail="REPAIR_SCHEMA_OR_PARSE_INVALID"
                    )

                # TASK-016B language validation of the repaired candidate.
                repair_language_ev = replay_language_validation(
                    candidate=repaired_candidate,
                    output_language=rni.output_language,
                )
                if repair_language_ev.result != "VALID":
                    return self._h2b_known_terminal_failure(
                        job_id=job.job_id, detail="REPAIR_LANGUAGE_INVALID"
                    )

                # Derive (not accept) the exact REPAIR Judge context/identity,
                # which is also the accepted deterministic gate input.
                repaired_candidate_hash = build_scoring_candidate_hash(
                    repaired_candidate
                )
                judge_ctx, judge_input = derive_repair_judge_trusted_context(
                    repair_request_hash=repair_request_hash,
                    trusted_candidate=repaired_candidate,
                    scoring_input=scoring_input,
                    validated_settings=settings,
                )
                quality_input_hash = build_content_quality_input_hash(judge_input)

                # Deterministic Content Quality gate: PASS (None) alone may
                # proceed to the REPAIR Judge; a reject is known terminal with
                # zero Judge contact.
                gate_reject = DeterministicContentQualityGate().evaluate(
                    content=repaired_candidate.reason,
                    candidate_hash=repaired_candidate_hash,
                    quality_input_hash=quality_input_hash,
                    scoring_request_hash=repair_request_hash,
                )
                if gate_reject is not None:
                    gate_reason = gate_reject.reason
                    if not isinstance(gate_reason, DeterministicGateReason):
                        return self._h2b_known_terminal_failure(
                            job_id=job.job_id, detail="REPAIR_FINALIZATION_INVALID"
                        )
                    return self._h2b_known_terminal_failure(
                        job_id=job.job_id,
                        detail=f"REPAIR_DETERMINISTIC_GATE_REJECT:{gate_reason.value}",
                    )

                if repair_request_hash == judge_ctx.expected_h2:
                    raise ScoringDispatchDenied(
                        "REPAIR identity collides with the REPAIR Judge identity"
                    )
                judge_identity = ScoringDispatchIdentity(
                    role=ScoringDispatchRole.REPAIR_JUDGE,
                    operation="local-content-quality-v1",
                    normalized_input_hash=judge_ctx.expected_h1,
                    request_hash=judge_ctx.expected_h2,
                )
                # Derive the exact Judge payload locally; its integrity binding
                # is the payload-level J-to-J guarantee.
                judge_body = build_quality_judge_generate_body(
                    operation_input=judge_ctx.operation_input,
                    content_input=judge_input,
                    model=settings.model,
                    max_output_tokens=settings.max_output_tokens,
                )
                judge_body_sha256 = hashlib.sha256(judge_body).hexdigest()
                judge_body_length = len(judge_body)
                # State-only H1 REPAIR_JUDGE consumption (no callback authority).
                admission.consume_repair_judge_role(judge_identity, now=_utcnow())

                # Revalidate the same local Judge identity/input/payload in the
                # same frame before Judge contact.
                judge_ctx_re, judge_input_re = derive_repair_judge_trusted_context(
                    repair_request_hash=repair_request_hash,
                    trusted_candidate=repaired_candidate,
                    scoring_input=scoring_input,
                    validated_settings=settings,
                )
                judge_body_re = build_quality_judge_generate_body(
                    operation_input=judge_ctx_re.operation_input,
                    content_input=judge_input_re,
                    model=settings.model,
                    max_output_tokens=settings.max_output_tokens,
                )
                if (
                    judge_ctx_re.expected_h1 != judge_ctx.expected_h1
                    or judge_ctx_re.expected_h2 != judge_ctx.expected_h2
                    or judge_ctx_re.operation_input != judge_ctx.operation_input
                    or judge_input_re != judge_input
                    or judge_body_re != judge_body
                    or hashlib.sha256(judge_body_re).hexdigest() != judge_body_sha256
                    or len(judge_body_re) != judge_body_length
                ):
                    raise ScoringDispatchDenied(
                        "REPAIR Judge identity changed after admission"
                    )

                # Role-neutral transport: the runtime frame alone interprets
                # the returned raw bytes as this admitted REPAIR_JUDGE attempt.
                judge_provider = self._create_quality_judge_provider_for_dispatch()
                try:
                    judge_outer = judge_provider.dispatch_exact_generate(
                        body=judge_body,
                        body_sha256=judge_body_sha256,
                        body_length=judge_body_length,
                    )
                except ScoringDispatchDenied:
                    raise
                except Exception as error:
                    raise UnknownProviderState(
                        "REPAIR Judge outcome is unknown after external dispatch"
                    ) from error

                # Authoritative outer capture and strict model-content
                # extraction: any ambiguity after contact is UNKNOWN, never
                # semantic UNCERTAIN.
                try:
                    seal_primary_raw_capture(judge_outer)
                except ValueError as error:
                    raise UnknownProviderState(
                        "REPAIR Judge outer provider protocol is ambiguous after contact"
                    ) from error
                judge_raw = self._h2b_extract_model_content(judge_outer.decode("utf-8"))
                if judge_raw is None:
                    raise UnknownProviderState(
                        "REPAIR Judge model content is ambiguous after contact"
                    )

                # Judge raw must be a trustworthy captured model content;
                # strict UTF-8/byte-bound failure after contact is UNKNOWN.
                try:
                    judge_capture = seal_judge_raw_capture(judge_raw)
                except ValueError as error:
                    raise UnknownProviderState(
                        "REPAIR Judge raw is ambiguous after external contact"
                    ) from error

                # Pure replay of the exact Judge raw against the derived identity.
                judge_result = verify_judge_model_content(
                    judge_raw,
                    operation_input=judge_ctx.operation_input,
                    content_input=judge_input,
                )
                if judge_result.status is ContentQualityStatus.REJECT:
                    return self._h2b_known_terminal_failure(
                        job_id=job.job_id, detail="REPAIR_JUDGE_REJECT"
                    )
                if judge_result.status is not ContentQualityStatus.PASS:
                    return self._h2b_known_terminal_failure(
                        job_id=job.job_id, detail="REPAIR_JUDGE_UNCERTAIN"
                    )

                judge_evidence = build_judge_evidence(
                    role="REPAIR",
                    operation_input=judge_ctx.operation_input,
                    judge_input=judge_input,
                    raw_utf8=judge_raw,
                    model=settings.model,
                    model_digest=settings.expected_model_digest,
                    policy_version=_QUALITY_POLICY_VERSION,
                    prompt_version=_QUALITY_PROMPT_VERSION,
                    operation_schema_version=_QUALITY_SCHEMA_VERSION,
                )
                attestation = build_quality_pass_attestation(
                    quality_result=judge_result,
                    operation_input=judge_ctx.operation_input,
                    quality_input=judge_input,
                    authority=self._quality_provenance_authority,
                )

                # REPAIR-aware trusted finalization: an independent boundary
                # that replays gate/Judge/attestation/identity itself.  Any
                # deterministic local failure terminalizes exactly once.
                try:
                    finalization = RepairTrustedScoringFinalizer().finalize(
                        candidate=repaired_candidate,
                        scoring_input=scoring_input,
                        repair_normalized_input=rni,
                        rni_hash=rni_hash,
                        repair_request_hash=repair_request_hash,
                        quality_input=judge_input,
                        quality_result=judge_result,
                        quality_operation=judge_ctx.operation_input,
                        judge_evidence=judge_evidence,
                        attestation=attestation,
                        quality_authority=self._quality_provenance_authority,
                        scoring_context=self._trusted_scoring_context,
                        validated_settings=settings,
                    )
                except (ValueError, TypeError):
                    return self._h2b_known_terminal_failure(
                        job_id=job.job_id, detail="REPAIR_FINALIZATION_INVALID"
                    )

                # Construct the UNTRUSTED in-memory evidence aggregate as a
                # lexical local value only.  This confers no trust, persistence
                # authority, or H2-C ingress; the frame terminalizes and exits,
                # and the aggregate becomes unreachable.
                aggregate = PhaseH2BValidatedRepairResult(
                    primary_trusted_context=trusted_context,
                    primary_failure_evidence=pfe,
                    failure_class=pfe.failure_class,
                    repair_normalized_input=rni,
                    repair_normalized_input_bytes=rni_bytes,
                    rni_hash=rni_hash,
                    repair_request_hash=repair_request_hash,
                    repair_prompt=prompt,
                    repair_payload_bytes=body,
                    repair_payload_sha256=body_sha256,
                    repair_payload_length=body_length,
                    repair_raw_utf8=outer_capture.utf8,
                    repair_raw_sha256=outer_capture.sha256,
                    repair_raw_length=outer_capture.byte_length,
                    repair_model_content=self._h2b_extract_model_content(
                        outer_capture.utf8
                    )
                    or "",
                    repaired_candidate=repaired_candidate,
                    repaired_candidate_hash=repaired_candidate_hash,
                    language_evidence=repair_language_ev,
                    quality_input_hash=quality_input_hash,
                    deterministic_gate_status="PASS",
                    judge_operation_input=judge_ctx.operation_input,
                    judge_input=judge_input,
                    judge_h1=judge_ctx.expected_h1,
                    judge_h2=judge_ctx.expected_h2,
                    judge_evidence=judge_evidence,
                    judge_raw_utf8=judge_capture.utf8,
                    judge_raw_sha256=judge_capture.sha256,
                    judge_raw_length=judge_capture.byte_length,
                    judge_result=judge_result,
                    attestation=attestation,
                    finalizer_trusted_result=finalization.trusted_result,
                    structured_result_bytes=finalization.structured_bytes,
                    structured_result_sha256=finalization.structured_sha256,
                    structured_result_length=finalization.structured_length,
                    structured_result_schema_version=(
                        finalization.trusted_result.result.schema_version
                    ),
                    structured_result_prompt_version=(
                        finalization.trusted_result.result.prompt_version
                    ),
                    model=settings.model,
                    model_digest=settings.expected_model_digest,
                    prompt_version="scoring-prompt-v2",
                    schema_version="score-result-v2",
                    policy_version=_QUALITY_POLICY_VERSION,
                    quality_prompt_version=_QUALITY_PROMPT_VERSION,
                    quality_schema_version=_QUALITY_SCHEMA_VERSION,
                    temperature=settings.temperature,
                    max_output_tokens=settings.max_output_tokens,
                    max_description_chars=settings.max_description_chars,
                )
                # The aggregate is a lexical local H2-B completion point only:
                # it is never retained on the runtime, in globals, or in any
                # cache/registry.  It is untrusted input to the H2-C replay.

                def _h2c_replay_continuation() -> PhaseHTrustedRepairSuccess:
                    """The approved 23-step no-network H2-C replay.

                    Defined and invoked only inside this actual SCORING frame,
                    immediately after the local H2-B aggregate.  Every
                    security-significant claim is re-derived from the trusted
                    roots of this frame (job/owner/lease, original
                    ScoringInput, rebuilt PRIMARY context, validated settings,
                    runtime quality authority) and compared against the
                    untrusted aggregate; pure checks are rerun from the
                    aggregate's sealed captures.  Zero /api/tags, zero
                    /api/generate, zero provider-factory, and zero Judge
                    network contact.  Only after all 23 checks does it mint
                    the PhaseHTrustedRepairSuccess data.
                    """

                    def _invalid(reason: str) -> NoReturn:
                        raise _H2CReplayInvalid(reason)

                    # 1. Current job/owner/active lease.
                    current = self._repository.get_job(job.job_id)
                    now = _utcnow()
                    if (
                        current is None
                        or current.status is not JobStatus.RUNNING
                        or current.lease_owner != self._runtime_owner
                        or current.lease_until is None
                        or current.lease_until <= now
                    ):
                        raise H2CStaleScoringLease(
                            "H2-C replay lost the active scoring lease"
                        )

                    # 2. Rebuild the PRIMARY trusted context from the original
                    #    input and settings.
                    replayed_context = build_primary_trusted_context(
                        scoring_input=scoring_input,
                        model=settings.model,
                        model_digest=settings.expected_model_digest,
                        temperature=settings.temperature,
                        max_output_tokens=settings.max_output_tokens,
                        max_description_chars=settings.max_description_chars,
                    )
                    if replayed_context != aggregate.primary_trusted_context:
                        _invalid("PRIMARY_EVIDENCE_MISMATCH")

                    # 3. Strictly reconstruct and verify the PRIMARY failure
                    #    evidence against the rebuilt context/settings.
                    replayed_pfe = PrimaryFailureEvidence.model_validate(
                        aggregate.primary_failure_evidence.model_dump(mode="json")
                    )
                    try:
                        verify_primary_failure_evidence(
                            replayed_pfe, replayed_context, settings
                        )
                    except ValueError:
                        _invalid("PFE_INVALID")

                    # 4. Eligible exact failure class only (UNKNOWN rejects).
                    if (
                        replayed_pfe.failure_class is not aggregate.failure_class
                        or replayed_pfe.failure_class
                        not in {
                            PrimaryFailureClass.SCHEMA_OR_PARSE_INVALID,
                            PrimaryFailureClass.LANGUAGE_INVALID,
                            PrimaryFailureClass.JUDGE_REJECT,
                            PrimaryFailureClass.JUDGE_UNCERTAIN,
                        }
                    ):
                        _invalid("FAILURE_CLASS_INELIGIBLE")
                    if replayed_pfe != pfe:
                        _invalid("PRIMARY_EVIDENCE_MISMATCH")

                    # 5-7. Rebuild RNI, recompute exact H2-JCS bytes and hash.
                    replayed_rni = build_repair_normalized_input(
                        job_id=job.job_id,
                        primary_trusted_context=replayed_context,
                        failure_evidence=replayed_pfe,
                        validated_settings=settings,
                    )
                    if replayed_rni != aggregate.repair_normalized_input:
                        _invalid("RNI_MISMATCH")
                    if (
                        h2_canonical_bytes(replayed_rni)
                        != aggregate.repair_normalized_input_bytes
                    ):
                        _invalid("RNI_MISMATCH")
                    replayed_rni_hash = repair_normalized_input_hash(replayed_rni)
                    if replayed_rni_hash != aggregate.rni_hash:
                        _invalid("RNI_MISMATCH")

                    # 8-10. Recompute REPAIR request hash, prompt, and exact
                    #       payload; compare bytes/hash/length.
                    replayed_request_hash = build_repair_request_hash(replayed_rni)
                    if replayed_request_hash != aggregate.repair_request_hash:
                        _invalid("REPAIR_REQUEST_MISMATCH")
                    replayed_prompt = render_task016c_repair_prompt_v2(
                        output_language=replayed_rni.output_language,
                        repair_request_hash=replayed_request_hash,
                        rni_jcs_utf8=h2_canonical_bytes(replayed_rni).decode("utf-8"),
                        pfe_jcs_utf8=h2_canonical_bytes(replayed_pfe).decode("utf-8"),
                        scoring_input_jcs_utf8=h2_canonical_bytes(
                            replayed_rni.scoring_input
                        ).decode("utf-8"),
                        primary_raw_utf8=replayed_pfe.primary_raw_utf8,
                        candidate_evidence_jcs_utf8=(
                            h2_canonical_bytes(replayed_pfe.primary_candidate).decode(
                                "utf-8"
                            )
                            if isinstance(
                                replayed_pfe.primary_candidate, CandidateEvidence
                            )
                            else None
                        ),
                        extracted_model_content=self._h2b_extract_model_content(
                            replayed_pfe.primary_raw_utf8
                        ),
                    )
                    if replayed_prompt != aggregate.repair_prompt:
                        _invalid("REPAIR_PAYLOAD_MISMATCH")
                    replayed_body = build_task016c_repair_generate_body(
                        model=replayed_rni.repair_model,
                        prompt=replayed_prompt,
                        temperature=replayed_rni.temperature,
                        max_output_tokens=replayed_rni.max_output_tokens,
                    )
                    if (
                        replayed_body != aggregate.repair_payload_bytes
                        or hashlib.sha256(replayed_body).hexdigest()
                        != aggregate.repair_payload_sha256
                        or len(replayed_body) != aggregate.repair_payload_length
                    ):
                        _invalid("REPAIR_PAYLOAD_MISMATCH")

                    # 11. Replay strict REPAIR raw/hash/length/protocol.
                    try:
                        replayed_capture = seal_primary_raw_capture(
                            aggregate.repair_raw_utf8.encode("utf-8")
                        )
                    except ValueError:
                        _invalid("REPAIR_RAW_INVALID")
                    if (
                        replayed_capture.utf8 != aggregate.repair_raw_utf8
                        or replayed_capture.sha256 != aggregate.repair_raw_sha256
                        or replayed_capture.byte_length != aggregate.repair_raw_length
                    ):
                        _invalid("REPAIR_RAW_INVALID")
                    if (
                        self._h2b_extract_model_content(aggregate.repair_raw_utf8)
                        != aggregate.repair_model_content
                    ):
                        _invalid("REPAIR_RAW_INVALID")

                    # 12. Parse candidate again; compare candidate/hash.
                    try:
                        replayed_candidate = parse_scoring_candidate(
                            aggregate.repair_raw_utf8
                        )
                    except ValueError:
                        _invalid("CANDIDATE_MISMATCH")
                    if replayed_candidate != aggregate.repaired_candidate:
                        _invalid("CANDIDATE_MISMATCH")
                    if (
                        build_scoring_candidate_hash(replayed_candidate)
                        != aggregate.repaired_candidate_hash
                    ):
                        _invalid("CANDIDATE_MISMATCH")

                    # 13. Rerun TASK-016B only; require exact VALID evidence.
                    replayed_language = replay_language_validation(
                        candidate=replayed_candidate,
                        output_language=replayed_rni.output_language,
                    )
                    if (
                        replayed_language.result != "VALID"
                        or replayed_language != aggregate.language_evidence
                    ):
                        _invalid("LANGUAGE_INVALID")

                    # 14. Reconstruct quality input; rerun deterministic gate.
                    replayed_judge_ctx, replayed_judge_input = (
                        derive_repair_judge_trusted_context(
                            repair_request_hash=replayed_request_hash,
                            trusted_candidate=replayed_candidate,
                            scoring_input=scoring_input,
                            validated_settings=settings,
                        )
                    )
                    if replayed_judge_input != aggregate.judge_input:
                        _invalid("JUDGE_EVIDENCE_INVALID")
                    if (
                        build_content_quality_input_hash(replayed_judge_input)
                        != aggregate.quality_input_hash
                    ):
                        _invalid("JUDGE_EVIDENCE_INVALID")
                    gate_reject = DeterministicContentQualityGate().evaluate(
                        content=replayed_candidate.reason,
                        candidate_hash=aggregate.repaired_candidate_hash,
                        quality_input_hash=aggregate.quality_input_hash,
                        scoring_request_hash=replayed_request_hash,
                    )
                    if (
                        gate_reject is not None
                        or aggregate.deterministic_gate_status != "PASS"
                    ):
                        _invalid("DETERMINISTIC_GATE_INVALID")

                    # 15-16. Rebuild REPAIR Judge context; recompute H1/H2.
                    if (
                        replayed_judge_ctx.expected_h1 != aggregate.judge_h1
                        or replayed_judge_ctx.expected_h2 != aggregate.judge_h2
                        or replayed_judge_ctx.operation_input
                        != aggregate.judge_operation_input
                    ):
                        _invalid("JUDGE_EVIDENCE_INVALID")

                    # 17. Replay strict Judge raw; pure-verify PASS.
                    replayed_judge_result = verify_judge_model_content(
                        aggregate.judge_raw_utf8,
                        operation_input=replayed_judge_ctx.operation_input,
                        content_input=replayed_judge_input,
                    )
                    if (
                        replayed_judge_result.status is not ContentQualityStatus.PASS
                        or replayed_judge_result != aggregate.judge_result
                    ):
                        _invalid("JUDGE_EVIDENCE_INVALID")
                    try:
                        replayed_judge_capture = seal_judge_raw_capture(
                            aggregate.judge_raw_utf8
                        )
                    except ValueError:
                        _invalid("JUDGE_EVIDENCE_INVALID")
                    if (
                        replayed_judge_capture.utf8 != aggregate.judge_raw_utf8
                        or replayed_judge_capture.sha256 != aggregate.judge_raw_sha256
                        or replayed_judge_capture.byte_length
                        != aggregate.judge_raw_length
                    ):
                        _invalid("JUDGE_EVIDENCE_INVALID")
                    try:
                        verify_judge_evidence_replay(
                            aggregate.judge_evidence, replayed_judge_ctx
                        )
                    except ValueError:
                        _invalid("JUDGE_EVIDENCE_INVALID")

                    # 18. Revalidate the exact REPAIR attestation.
                    try:
                        verify_quality_pass_attestation(
                            aggregate.attestation,
                            quality_result=replayed_judge_result,
                            operation_input=replayed_judge_ctx.operation_input,
                            quality_input=replayed_judge_input,
                            authority=self._quality_provenance_authority,
                        )
                    except ValueError:
                        _invalid("ATTESTATION_INVALID")

                    # 19-21. Independent finalizer; exact trusted-result and
                    #        sealed structured bytes equality.
                    try:
                        replayed_finalization = (
                            RepairTrustedScoringFinalizer().finalize(
                                candidate=replayed_candidate,
                                scoring_input=scoring_input,
                                repair_normalized_input=replayed_rni,
                                rni_hash=replayed_rni_hash,
                                repair_request_hash=replayed_request_hash,
                                quality_input=replayed_judge_input,
                                quality_result=replayed_judge_result,
                                quality_operation=replayed_judge_ctx.operation_input,
                                judge_evidence=aggregate.judge_evidence,
                                attestation=aggregate.attestation,
                                quality_authority=self._quality_provenance_authority,
                                scoring_context=self._trusted_scoring_context,
                                validated_settings=settings,
                            )
                        )
                    except (ValueError, TypeError, RepairFinalizationInvalid):
                        _invalid("FINALIZER_INVALID")
                    if (
                        type(aggregate.finalizer_trusted_result)
                        is not TrustedScoreResult
                        or aggregate.finalizer_trusted_result.result
                        != replayed_finalization.trusted_result.result
                    ):
                        _invalid("TRUSTED_RESULT_MISMATCH")
                    if (
                        replayed_finalization.structured_bytes
                        != aggregate.structured_result_bytes
                        or replayed_finalization.structured_sha256
                        != aggregate.structured_result_sha256
                        or replayed_finalization.structured_length
                        != aggregate.structured_result_length
                        or replayed_finalization.trusted_result.result.schema_version
                        != aggregate.structured_result_schema_version
                        or replayed_finalization.trusted_result.result.prompt_version
                        != aggregate.structured_result_prompt_version
                    ):
                        _invalid("STRUCTURED_RESULT_MISMATCH")

                    # 22. Recheck settings and complete cross-bindings.
                    if (
                        settings.max_transcript_chars > 131_072
                        or settings.max_output_tokens > 2_147_483_647
                    ):
                        raise _H2CSettingsBoundExceeded()
                    settings_provenance = build_h2c_settings_provenance(
                        validated_settings=settings,
                        output_language=scoring_input.output_language,
                        summary_score_threshold=(
                            self._config.settings.thresholds.summary_score
                        ),
                    )
                    from youtube_intel.h2_jcs import jcs_serialize as _jcs_serialize

                    settings_provenance_sha256 = hashlib.sha256(
                        _jcs_serialize(settings_provenance.model_dump(mode="json"))
                    ).hexdigest()
                    if (
                        len(_jcs_serialize(settings_provenance.model_dump(mode="json")))
                        > 8_192
                    ):
                        raise _H2CSettingsBoundExceeded()
                    provider_evidence = RepairProviderEvidence.model_validate(
                        {
                            "schema_version": "task016c-repair-provider-evidence-v2",
                            "operation": replayed_rni.operation,
                            "normalized_input": replayed_rni.model_dump(mode="json"),
                            "normalized_input_hash": replayed_rni_hash,
                            "request_hash": replayed_request_hash,
                            "provider": replayed_rni.repair_provider,
                            "model": replayed_rni.repair_model,
                            "model_digest": replayed_rni.repair_model_digest,
                            "prompt_version": replayed_rni.repair_prompt_version,
                            "operation_schema_version": (
                                replayed_rni.repair_schema_version
                            ),
                            "output_language": replayed_rni.output_language,
                            "temperature": replayed_rni.temperature,
                            "max_output_tokens": replayed_rni.max_output_tokens,
                            "max_description_chars": (
                                replayed_rni.max_description_chars
                            ),
                            "settings_provenance": settings_provenance.model_dump(
                                mode="json"
                            ),
                            "settings_provenance_sha256": (settings_provenance_sha256),
                        }
                    )
                    candidate_evidence = RepairCandidateEvidence.model_validate(
                        {
                            "schema_version": ("task016c-repair-candidate-evidence-v1"),
                            "repair_raw_utf8": aggregate.repair_raw_utf8,
                            "repair_raw_sha256": aggregate.repair_raw_sha256,
                            "repair_raw_length": aggregate.repair_raw_length,
                            "repair_model_content": aggregate.repair_model_content,
                            "candidate": replayed_candidate.model_dump(mode="json"),
                            "candidate_sha256": aggregate.repaired_candidate_hash,
                            "language_evidence": replayed_language.model_dump(
                                mode="json"
                            ),
                        }
                    )
                    quality_evidence = RepairQualityEvidence.model_validate(
                        {
                            "schema_version": "task016c-repair-quality-evidence-v1",
                            "quality_input": replayed_judge_input.model_dump(
                                mode="json"
                            ),
                            "quality_input_hash": aggregate.quality_input_hash,
                            "deterministic_gate_status": "PASS",
                            "judge_operation_input": (
                                replayed_judge_ctx.operation_input.model_dump(
                                    mode="json"
                                )
                            ),
                            "judge_h1": replayed_judge_ctx.expected_h1,
                            "judge_h2": replayed_judge_ctx.expected_h2,
                            "judge_raw_utf8": aggregate.judge_raw_utf8,
                            "judge_raw_sha256": aggregate.judge_raw_sha256,
                            "judge_raw_length": aggregate.judge_raw_length,
                            "judge_evidence": aggregate.judge_evidence.model_dump(
                                mode="json"
                            ),
                            "quality_result": replayed_judge_result.model_dump(
                                mode="json"
                            ),
                            "attestation": aggregate.attestation.model_dump(
                                mode="json"
                            ),
                        }
                    )
                    finalizer_binding = RepairFinalizerBinding.model_validate(
                        {
                            "schema_version": ("task016c-repair-finalizer-binding-v1"),
                            "trusted_result": (
                                replayed_finalization.trusted_result.result.model_dump(
                                    mode="json"
                                )
                            ),
                            "structured_result_sha256": (
                                replayed_finalization.structured_sha256
                            ),
                            "structured_result_length": (
                                replayed_finalization.structured_length
                            ),
                            "structured_result_schema_version": SCHEMA_VERSION,
                            "structured_result_prompt_version": PROMPT_VERSION,
                            "primary_request_hash": replayed_context.request_hash,
                            "repair_request_hash": replayed_request_hash,
                            "repair_judge_request_hash": (
                                replayed_judge_ctx.expected_h2
                            ),
                        }
                    )

                    # 23. Build the envelope and mint the trusted success data.
                    envelope, envelope_bytes, _, _ = build_repair_composite_envelope(
                        primary_failure_evidence=replayed_pfe,
                        repair_provider_evidence=provider_evidence,
                        repair_candidate_evidence=candidate_evidence,
                        repair_quality_evidence=quality_evidence,
                        finalizer_binding=finalizer_binding,
                    )
                    return _mint_phase_h_trusted_repair_success(
                        job_id=job.job_id,
                        owner=self._runtime_owner,
                        pipeline_version=PIPELINE_VERSION,
                        primary_request_hash=replayed_context.request_hash,
                        primary_normalized_input_hash=(
                            replayed_context.normalized_input_hash
                        ),
                        scoring_input_sha256=replayed_context.scoring_input_sha256,
                        envelope=envelope,
                        envelope_bytes=envelope_bytes,
                        trusted_result=replayed_finalization.trusted_result,
                        structured_bytes=replayed_finalization.structured_bytes,
                    )

                def _h2c_integrity_terminal(detail: str) -> StageDisposition:
                    """One owner-authoritative trust-integrity fail_job."""

                    try:
                        self._repository.fail_job(
                            job.job_id,
                            owner=self._runtime_owner,
                            error_code=ErrorCode.TRUST_INTEGRITY_INVALID,
                            error_message=detail,
                            retry_at=None,
                            now=_utcnow(),
                        )
                    except LeaseConflict as error:
                        raise H2CStaleScoringLease(
                            "lease lost during H2-C integrity terminalization"
                        ) from error
                    confirmed = self._repository.get_job(job.job_id)
                    if (
                        confirmed is None
                        or confirmed.status is not JobStatus.FAILED_FINAL
                    ):
                        raise UnknownProviderState(
                            "H2-C integrity terminalization could not be finalized"
                        )
                    return StageDisposition.TERMINAL

                # --- Generation decision point (after validated H2-B PASS). ---
                decision_job = self._repository.get_job(job.job_id)
                generation = (
                    None
                    if decision_job is None
                    else decision_job.scoring_lineage_version
                )
                if generation is None:
                    # Known pre-lineage: the frozen compatibility terminal.  No
                    # H2-C entry, admission, replay, provider/Judge work, or
                    # repair persistence.
                    self._repository.fail_job(
                        job.job_id,
                        owner=self._runtime_owner,
                        error_code=ErrorCode.CAPABILITY_UNAVAILABLE,
                        error_message="H2B_PASS_AWAITING_H2C",
                        retry_at=None,
                        now=_utcnow(),
                    )
                    confirmed = self._repository.get_job(job.job_id)
                    if (
                        confirmed is None
                        or confirmed.status is not JobStatus.FAILED_FINAL
                    ):
                        raise UnknownProviderState(
                            "H2-B staged terminalization could not be finalized"
                        )
                    return StageDisposition.TERMINAL
                if generation != SCORING_LINEAGE_VERSION_V1:
                    # Unknown non-NULL generation: closed pre-entry integrity
                    # terminal; never H2-C entry and never legacy fallback.
                    return _h2c_integrity_terminal(
                        h2c_replay_invalid_detail("SCORING_LINEAGE_VERSION_INVALID")
                    )

                # v1 generation: the only branch that may enter H2-C.
                try:
                    repair_success = _h2c_replay_continuation()
                except _H2CSettingsBoundExceeded:
                    return _h2c_integrity_terminal(
                        h2c_replay_invalid_detail("SETTINGS_BOUND_EXCEEDED")
                    )
                except _H2CEnvelopeOversize:
                    return _h2c_integrity_terminal(
                        h2c_replay_invalid_detail("ENVELOPE_OVERSIZE")
                    )
                except _H2CReplayInvalid as replay_invalid:
                    return _h2c_integrity_terminal(
                        h2c_replay_invalid_detail(replay_invalid.reason)
                    )

                entry = self._trusted_persistence_entry(
                    job_id=job.job_id,
                    owner=self._runtime_owner,
                    pipeline_version=PIPELINE_VERSION,
                )
                try:
                    committed = entry.persist_success(repair_success)
                except _H2CLineageTerminalHandled:
                    return StageDisposition.TERMINAL
                if committed.job.status is not JobStatus.SUCCEEDED:
                    raise UnknownProviderState(
                        "H2-C repair persistence could not be finalized"
                    )
                ScoringAdmissionRegistry.release_terminal(
                    repository=self._repository,
                    job_id=job.job_id,
                    attempt_count=job.attempt_count,
                )
                return None

            admission.admit(primary_identity, now=_utcnow())
            provider = self._create_scoring_provider_for_dispatch()
            try:
                attempt = self._dispatch_primary_attempt_after_admission(
                    provider, scoring_input
                )
            except UnknownProviderState:
                capture = self._h2b_eligible_parse_failure_capture(provider)
                if capture is None:
                    raise
                repair_pfe = self._h2b_pfe_for_parse_failure(
                    scoring_input=scoring_input,
                    capture=capture,
                )
                if repair_pfe is None:
                    raise
                repair_outcome = _h2b_repair_continuation(repair_pfe)
                if repair_outcome is StageDisposition.TERMINAL:
                    return StageDisposition.TERMINAL
                return None
            try:
                success = self.run_primary_trusted_scoring(
                    attempt=attempt,
                    scoring_input=scoring_input,
                    job_id=job.job_id,
                )
            except _KnownPrimaryFailure:
                repair_pfe = self._h2b_pfe_for_known_failure(
                    scoring_input=scoring_input,
                    attempt=attempt,
                )
                if repair_pfe is None:
                    raise
                repair_outcome = _h2b_repair_continuation(repair_pfe)
                if repair_outcome is StageDisposition.TERMINAL:
                    return StageDisposition.TERMINAL
                return None
            self._persist_trusted_scoring_success(
                success=success,
                job=job,
                owner=owner,
                pipeline_version=PIPELINE_VERSION,
            )
            return None

        def analysis_stage(
            job: JobRecord, record: VideoRecord
        ) -> AnalysisOutcome | None:
            if not self._config.settings.cloud.enabled:
                return AnalysisSkipped(
                    reason=AnalysisSkipReason.CLOUD_DISABLED,
                    call=None,
                    safe_message="cloud analysis is disabled",
                )
            video = self._video_metadata(record)
            transcript = self._load_transcript(job, video).artifact
            artifact = self._repository.latest_artifact(
                video.video_id, ArtifactKind.TRANSCRIPT_CANONICAL
            )
            if artifact is None:
                raise ValueError("transcript is unavailable")
            text = self._verified_artifact(artifact, max_bytes=4_000_000).decode(
                "utf-8"
            )
            scoring_language = self._downstream_output_language(video.video_id)
            return RepositoryBackedAnalysisService(
                provider=self._dependencies.analysis_provider_factory(),
                settings=self._config.settings.cloud,
                repository=self._repository,
                context=AnalysisJobContext(job.job_id, owner, PIPELINE_VERSION),
                artifact_root=self._data_root,
                credential_resolver=EnvironmentCredentialResolver(),
                budget=CloudCallBudget(
                    limit=self._config.settings.cloud.max_calls_per_run
                ),
            ).analyze(
                video=video,
                transcript_text=text,
                language=transcript.language,
                output_language=scoring_language,
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

    def _refresh_output_language_for_new_batch(self) -> None:
        """Freeze the latest preference for the next processing batch only."""

        effective = self._output_language_service.effective().value
        self._effective_output_language = effective
        self._trusted_scoring_context = _build_trusted_scoring_context(
            self._config, effective
        )

    def process(self, *, video: str | None, resume: bool) -> CommandOutcome:
        del resume
        self._refresh_output_language_for_new_batch()
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
                None if persisted is None else PipelineJobPlanner.next_stage(persisted)
            )
            latest = self._repository.latest_video_job(
                failed_record.video_id,
                target_stage=target_stage,
            )
            stage = "unknown" if latest is None else latest.target_stage.value.lower()
            error = (
                "prerequisite unavailable"
                if latest is None
                else (latest.last_error_message or "stage failed")
            )
            return CommandOutcome(
                attempted=len(selected),
                failed=failed,
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
                # CAPABILITY_UNAVAILABLE terminals are excluded by code alone
                # (never by detail) before rerun_job/process: the staged build
                # lacks the required continuation, so retrying cannot resolve it.
                and job.last_error_code != ErrorCode.CAPABILITY_UNAVAILABLE.value
                # TRUST_INTEGRITY_INVALID terminals are non-retryable
                # automatically and manually; the sole exclusion predicate is
                # the error code alone (never the diagnostic detail).
                and job.last_error_code != ErrorCode.TRUST_INTEGRITY_INVALID.value
                and job.video_id is not None
                and (video is None or job.video_id == video)
                and (
                    (record := self._repository.get_video(job.video_id)) is not None
                    and PipelineJobPlanner.next_stage(record) is job.target_stage
                )
            )
        )
        if not selected:
            return CommandOutcome(
                safe_message="No final failed video job is available to retry."
            )
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
                context=NoteWriteContext(
                    "weekly-runtime", "youtube-intel-runtime", PIPELINE_VERSION
                ),
            ),
            artifact_root=self._data_root,
            timezone=self._config.settings.general.timezone,
            top_n=self._config.settings.weekly.top_n,
            scoring_reader=self._scoring_reader().read,
        ).generate(now=_utcnow())
        return CommandOutcome(
            attempted=1,
            safe_message=f"Weekly report written to {report.note_ref.relative_path}.",
        )


_bind_verified_note_v2_runtime(RuntimeOperations)
del _bind_verified_note_v2_runtime


def create_runtime_operations(
    config: AppConfig, project_root: Path
) -> RuntimeOperations:
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
        if integrity != ("ok",) or version != 14:
            raise sqlite3.DatabaseError
    except (OSError, sqlite3.Error):
        return DoctorCheck("SQLite", "FAIL", "state database is invalid.", True)
    return DoctorCheck("SQLite", "PASS", "schema and integrity check passed.", False)


def _ollama_check(config: AppConfig) -> tuple[DoctorCheck, DoctorCheck]:
    settings = config.settings.local_scoring
    request = urllib.request.Request(
        settings.base_url + "/api/tags",
        headers={"Accept": "application/json"},
        method="GET",
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
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        ValueError,
        json.JSONDecodeError,
    ):
        unavailable = DoctorCheck(
            "Ollama", "FAIL", "loopback service is unavailable or invalid.", True
        )
        return unavailable, DoctorCheck(
            "Local scoring model",
            "FAIL",
            "model cannot be verified until Ollama is available.",
            True,
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
    if config.settings.cloud.enabled:
        tokenizer_status = tokenizer_resource_status(data_root)
        checks.append(
            DoctorCheck(
                "Cloud tokenizer",
                "PASS" if tokenizer_status == "READY" else "FAIL",
                "explicitly provisioned local o200k tokenizer asset is ready."
                if tokenizer_status == "READY"
                else "explicitly provisioned local o200k tokenizer asset is missing or invalid.",
                tokenizer_status != "READY",
            )
        )
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
