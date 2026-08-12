"""Production composition root for the local-first command operations."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from youtube_intel.analysis import (
    AnalysisJobContext,
    CloudCallBudget,
    EnvironmentCredentialResolver,
    RepositoryBackedAnalysisService,
)
from youtube_intel.config import AppConfig
from youtube_intel.discovery import DiscoveryService, YouTubeRssSourceProvider
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisOutcome,
    AnalysisSkipped,
    AnalysisSkipReason,
    AppError,
    ChannelRef,
    ErrorCode,
    JobStatus,
    MetadataProvider,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    ScoringDecision,
    ScoringOutcome,
    SourceProvider,
    TranscriptionRequired,
    TranscriptReady,
    VideoMetadata,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.operations import CommandOutcome, ExitCode, Operations
from youtube_intel.pipeline import PipelineOrchestrator
from youtube_intel.providers.cloud_llm import OpenAIResponsesProvider
from youtube_intel.providers.obsidian import NoteWriteContext, ObsidianNoteSink
from youtube_intel.providers.ollama import OllamaScoringProvider
from youtube_intel.providers.subtitles import YtDlpSubtitleAdapter
from youtube_intel.providers.youtube import YtDlpMetadataProvider
from youtube_intel.reporting import WeeklyReportService
from youtube_intel.retry import RetryPolicy
from youtube_intel.scoring import RepositoryBackedScoringService, ScoringJobContext
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    JobRecord,
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


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    status: str
    message: str
    blocking: bool


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


def bootstrap_runtime(config: AppConfig, project_root: Path) -> SQLiteStateRepository:
    """Idempotently create the declared local runtime state."""

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
        self._discovery = DiscoveryService(
            self._dependencies.discovery_source,
            self._repository,
            self._dependencies.metadata_provider,
        )
        self._data_root = _safe_project_path(
            self._root, self._config.settings.storage.data_dir
        ).resolve(strict=True)

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
                owner="youtube-intel-runtime",
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

    def _load_scoring(self, video_id: str) -> ScoringOutcome:
        artifact = self._repository.latest_artifact(video_id, ArtifactKind.SCORING_STRUCTURED)
        if artifact is None:
            raise ValueError("persisted score is unavailable")
        from youtube_intel.domain import ScoreResult

        result = ScoreResult.model_validate_json(
            self._verified_artifact(artifact, max_bytes=1_000_000)
        )
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
        from youtube_intel.domain import AnalysisResult

        result = AnalysisResult.model_validate_json(
            self._verified_artifact(artifact, max_bytes=1_000_000)
        )
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
        owner = "youtube-intel-runtime"

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
            RepositoryBackedScoringService(
                provider=self._dependencies.scoring_provider_factory(),
                settings=self._config.settings.local_scoring,
                summary_threshold=self._config.settings.thresholds.summary_score,
                repository=self._repository,
                context=ScoringJobContext(job.job_id, owner, PIPELINE_VERSION),
                artifact_root=self._data_root,
                clock=_utcnow,
            ).score(video=video, transcript_text=text, language=transcript.language)

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
