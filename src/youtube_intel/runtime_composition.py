"""Production composition for loopback GUI-triggered durable Source Runs."""

from __future__ import annotations

import hashlib
import logging
import secrets
import threading
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.config import AppConfig
from youtube_intel.deep_analysis_obsidian import DeepAnalysisObsidianPublisher
from youtube_intel.deep_analysis_service import (
    DeepAnalysisCapability,
    DeepAnalysisService,
)
from youtube_intel.distillation import (
    BudgetDecision,
    CloudDistillationAuthorization,
    DistillationCapabilityScope,
    DistillationCommand,
    M12QualifiedCloudProductionAuthorizationAuthority,
    MoonshotK26NonThinkingCloudDistillationTransport,
    OllamaLocalDistillationTransport,
    PersonalizedDistillationService,
)
from youtube_intel.domain import (
    ErrorCode,
    JobStatus,
    PipelineStatus,
    TranscriptReady,
)
from youtube_intel.evidence_translation import EvidenceTranslationPresentationService
from youtube_intel.following_scheduler import AUTOMATIC_CHECK_PREFIX, FollowingScheduler
from youtube_intel.following_tracking import FollowingTrackingService, is_tracked
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.model_settings import (
    CredentialStore,
    MacOSKeychainCredentialStore,
    ModelSettingsService,
    local_models,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.processing_orchestrator import (
    DurableProcessingOrchestrator,
    PersistedSourceRunDiscovery,
    SourceRunDiscoveryError,
)
from youtube_intel.providers.ollama_evidence_translation import OllamaEvidenceTranslator
from youtube_intel.runtime import (
    PIPELINE_VERSION,
    RuntimeDependencies,
    RuntimeOperations,
)
from youtube_intel.scoring import AuthoritativeScoringReader
from youtube_intel.source_policy import (
    SourcePolicyApplicationService,
)
from youtube_intel.source_run import SourceRunRecord, SourceRunState, SourceRunTrigger
from youtube_intel.state import ArtifactKind, ProviderCallRequest, SQLiteStateRepository
from youtube_intel.transcripts import (
    FORMAT_POLICY_VERSION,
    SELECTION_POLICY_VERSION,
    CaptionRepairContext,
    SubtitleAcquisitionService,
    TranscriptError,
    TranscriptJobContext,
    build_raw_request_hash,
)


class RuntimeSourceRunIngestion:
    """Persist bounded production ingestion for the durable discovery checkpoint."""

    def __init__(
        self,
        runtime: RuntimeOperations,
        source_policy: SourcePolicyApplicationService,
        source_tracking: FollowingTrackingService | None = None,
    ) -> None:
        self._runtime = runtime
        self._source_policy = source_policy
        self._source_tracking = source_tracking

    def caption_repair_is_waiting(self, run: SourceRunRecord) -> bool:
        """On restart, respect both existing leases before resuming this child."""
        repository = self._runtime._repository
        source = repository.get_source_subscription(run.source_id)
        if source is None or source.video_id is None:
            return False
        identity = hashlib.sha256(f"{run.run_id}:{source.video_id}".encode()).hexdigest()
        job = repository.get_job("caption-repair-" + identity)
        if job is None:
            return False
        now = datetime.now(UTC)
        if ((job.status is JobStatus.RUNNING and job.lease_until is not None and job.lease_until > now)
            or (job.status is JobStatus.RETRY_PENDING and job.available_at > now)):
            return True
        adapter = self._runtime._dependencies.subtitle_adapter_factory()
        raw_hash = build_raw_request_hash(video_id=source.video_id,
            language_preferences=self._runtime._config.settings.general.transcript_languages,
            provider=adapter.provider_name, provider_version=adapter.provider_version,
            refresh_generation=int(identity[:15], 16))
        request = ProviderCallRequest(operation="subtitle.fetch", normalized_input_hash=raw_hash,
            provider=adapter.provider_name, model=None, prompt_version=SELECTION_POLICY_VERSION,
            schema_version=FORMAT_POLICY_VERSION, deterministic_artifact_key="subtitle-source:" + raw_hash)
        call = repository.get_provider_call(request.request_hash)
        return bool(call is not None and call.lease_until is not None and call.lease_until > now)

    def _repair_plain_captions(self, source_id: str, video_id: str) -> None:
        repository = self._runtime._repository
        video = repository.get_video(video_id)
        if (video is None or video.pipeline_status is not PipelineStatus.TRANSCRIPT_READY
            or repository.get_verified_timed_transcript(video_id=video_id) is not None):
            return
        runs = tuple(run for run in repository.list_source_runs()
                     if run.source_id == source_id and run.state is SourceRunState.RUNNING
                     and run.trigger is SourceRunTrigger.MANUAL_CHECK_NOW
                     and run.manual_command_id is not None
                     and not run.manual_command_id.startswith(AUTOMATIC_CHECK_PREFIX))
        if len(runs) != 1:
            raise SourceRunDiscoveryError("Caption repair requires an explicit active source check")
        run = runs[0]
        canonical = repository.latest_artifact(video_id, ArtifactKind.TRANSCRIPT_CANONICAL)
        prior = None if canonical is None or canonical.job_id is None else repository.get_job(canonical.job_id)
        if prior is None or canonical is None:
            raise SourceRunDiscoveryError("Caption repair source history is unavailable")
        now = datetime.now(UTC)
        identity = hashlib.sha256(f"{run.run_id}:{video_id}".encode()).hexdigest()
        job_id = "caption-repair-" + identity
        if any(job.job_id != job_id and job.status in {JobStatus.PENDING, JobStatus.RUNNING, JobStatus.RETRY_PENDING}
               for job in repository.list_video_jobs(video_id, limit=1000)):
            raise SourceRunDiscoveryError("Caption repair cannot overlap active Content work")
        job = repository.get_job(job_id)
        if job is None:
            if prior.status is not JobStatus.SUCCEEDED:
                raise SourceRunDiscoveryError("Caption repair requires completed source history")
            job = repository.rerun_job(prior.job_id, new_job_id=job_id, available_at=now, now=now)
        repository.reclaim_expired_jobs(now=now)
        repository.activate_retry_jobs(now=now)
        claimed = repository.claim_next_job(owner=self._runtime._runtime_owner,
            lease_until=now + timedelta(seconds=300), now=now, video_id=video_id, job_id=job_id)
        if claimed is None or claimed.job_id != job_id:
            raise SourceRunDiscoveryError("Caption repair job is already owned or unavailable")
        service = SubtitleAcquisitionService(
            adapter=self._runtime._dependencies.subtitle_adapter_factory(), repository=repository,
            data_root=self._runtime._data_root,
            context=TranscriptJobContext(job_id=job_id, owner=self._runtime._runtime_owner,
                pipeline_version=video.pipeline_version, refresh_generation=int(identity[:15], 16),
                repair=CaptionRepairContext(run.run_id, canonical.artifact_id)),
            clock=lambda: datetime.now(UTC),
        )
        try:
            result = service.fetch(self._runtime._video_metadata(video), self._runtime._config.settings.general.transcript_languages)
            if not isinstance(result, TranscriptReady):
                raise SourceRunDiscoveryError("Native timed captions are unavailable")
        except Exception as error:
            saved = repository.get_job(job_id)
            if saved is not None and saved.status is JobStatus.RUNNING:
                code = error.error.code if isinstance(error, TranscriptError) else ErrorCode.LOCAL_RESOURCE
                repository.fail_job(job_id, owner=self._runtime._runtime_owner, error_code=code,
                    error_message="Caption repair needs attention", retry_at=None, now=datetime.now(UTC))
            raise SourceRunDiscoveryError("Caption repair needs attention") from error

    def ingest(self, source_id: str) -> None:
        source = self._runtime._repository.get_source_subscription(source_id)
        if source is not None and is_tracked(self._runtime._repository, source.source_id):
            if self._source_tracking is None:
                raise SourceRunDiscoveryError("Source tracking is unavailable")
            # The persisted command identity owns automatic origin even after
            # process recovery; no thread-local or scheduler job is authority.
            with self._runtime._repository._connect() as connection:
                active = connection.execute(
                    "SELECT manual_command_id FROM source_runs WHERE source_id=? AND state='RUNNING'",
                    (source_id,),
                ).fetchall()
            automatic = any(str(row[0]).startswith(AUTOMATIC_CHECK_PREFIX) for row in active)
            category = self._source_tracking.check(source_id, automatic=automatic)
            if automatic and category == "BUSY":
                self._source_tracking.defer_automatic(source_id)
            if category not in {"COMPLETE", "UPDATE_GAP", "COOLDOWN"}:
                raise SourceRunDiscoveryError("Source check did not complete")
            return
        policy = self._source_policy.effective_policy(source_id)
        if source is not None and source.video_id is not None and source.processing_policy.value == "DISCOVER_ONLY":
            failed = self._runtime._repository.latest_content_job(source.video_id)
            if failed is not None and failed.status.value == "FAILED_FINAL" and failed.last_error_code in {"CAPABILITY_UNAVAILABLE", "TRUST_INTEGRITY_INVALID"}:
                # Do not let the ordinary planner create a fresh job that
                # bypasses the existing non-retryable trust/capability terminal.
                raise SourceRunDiscoveryError("Content cannot be safely retried")
            if (failed is not None and failed.status.value == "FAILED_FINAL"
                and not failed.job_id.startswith("caption-repair-")
                and failed.target_stage is not None and failed.target_stage.value in {"METADATA", "TRANSCRIPT"}
                and failed.last_error_code not in {"CAPABILITY_UNAVAILABLE", "TRUST_INTEGRITY_INVALID"}):
                # This is an explicit one-time source check, with the same trust
                # exclusions as normal retry, bounded strictly to Content stages.
                from youtube_intel.runtime import _utcnow

                now = _utcnow()
                self._runtime._repository.rerun_job(failed.job_id, new_job_id="content-retry-" + secrets.token_hex(16), available_at=now, now=now)
        try:
            if source is not None and source.video_id is not None and source.processing_policy.value == "DISCOVER_ONLY":
                self._repair_plain_captions(source_id, source.video_id)
            video_ids = self._runtime.ingest_source_to_transcript(
                source_id,
                limit=policy.per_run_max_new_videos,
            )
            from youtube_intel.extractive_summary import ExtractiveSummaryService
            # New Content-only imports organize without changing the established
            # scoring/Summary pipeline of legacy STANDARD_INTELLIGENCE sources.
            content_only = source is not None and source.processing_policy.value == "DISCOVER_ONLY"
            for video_id in video_ids if content_only else ():
                job = self._runtime._repository.latest_content_job(video_id)
                if job is not None and job.status.value in {"PENDING", "RUNNING", "RETRY_PENDING", "FAILED_FINAL"}:
                    # A one-time import has no Following scheduler. Retain a
                    # durable attention outcome and expose explicit retry.
                    raise SourceRunDiscoveryError("Content processing needs attention")
                if self._runtime._repository.get_verified_timed_transcript(video_id=video_id) is not None and self._runtime._repository.current_local_summary_pointer(video_id) is None:
                    ExtractiveSummaryService(self._runtime._repository, self._runtime._data_root).create(video_id, now=datetime.now(UTC))
                if self._runtime._repository.get_verified_timed_transcript(video_id=video_id) is None:
                    raise SourceRunDiscoveryError("Content captions need verified source timing")
        except Exception as error:
            if isinstance(error, SourceRunDiscoveryError):
                raise
            raise SourceRunDiscoveryError("Source ingestion failed safely") from error


class RuntimeSourceRunPreparation:
    """Run the existing M1 pipeline only after durable filtering marks content relevant."""

    def __init__(self, runtime: RuntimeOperations) -> None:
        self._runtime = runtime

    def prepare(self, video_id: str) -> bool:
        pointer = self._runtime._repository.current_local_summary_pointer(video_id)
        if (
            pointer is not None
            and self._runtime._repository.get_verified_timed_transcript(
                video_id=video_id
            )
            is not None
        ):
            from youtube_intel.extractive_summary import ExtractiveSummaryService

            artifact = self._runtime._repository.get_artifact(pointer.artifact_id)
            if artifact is not None and artifact.provider == "extractive-source":
                try:
                    ExtractiveSummaryService(
                        self._runtime._repository, self._runtime._data_root
                    ).read(video_id, pointer.artifact_id)
                    return True
                except (ValueError, OSError):
                    return False
        if any(is_tracked(self._runtime._repository, source.source_id)
               and self._runtime._repository.source_has_video(source.source_id, video_id)
               for source in self._runtime._repository.list_source_subscriptions()):
            # Optional analysis must never substitute a full pipeline for missing
            # trusted Content. The tracked Content preparation owns that work.
            return False
        outcome = self._runtime.process(video=video_id, resume=True)
        return not outcome.failed


class ProductionDistillationBudget:
    """Explicit production budget seam; provider authorization still gates dispatch."""

    def check(self, command: DistillationCommand) -> BudgetDecision:
        del command
        return BudgetDecision(allowed=True, state="RUNTIME_BUDGET_ADMITTED")


class DurableSourceRunWorker:
    """One task-owned worker that drains only the persisted Source Run queue."""

    def __init__(
        self,
        orchestrator: DurableProcessingOrchestrator,
        *,
        poll_seconds: float = 0.5,
        scheduler: FollowingScheduler | None = None,
        backup_restore: BackupRestoreService | None = None,
    ) -> None:
        if poll_seconds <= 0:
            raise ValueError("worker poll interval must be positive")
        self._orchestrator = orchestrator
        self._poll_seconds = poll_seconds
        self.scheduler = scheduler
        self.backup_restore = backup_restore
        self._execution = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._maintenance_context = threading.local()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="youtube-intel-source-runs",
            daemon=True,
        )
        self._thread.start()

    def notify(self) -> None:
        self._wake.set()

    def notify_backup_window_closed(self) -> None:
        # Our idle maintenance closes its own protected window. Do not turn
        # that callback into an idle self-wakeup loop; other threads still wake.
        if not getattr(self._maintenance_context, "active", False):
            self.notify()

    def run_once(self) -> SourceRunRecord | None:
        if not self._execution.acquire(blocking=False):
            return None
        try:
            # An idle authority read is not active source work. Actual due
            # admission/execution still rechecks the protected Backup gate.
            if not self._orchestrator.queued_runs(limit=1) and (
                self.scheduler is None or self.scheduler.wait_seconds() != 0
            ):
                if self.backup_restore is not None and not self._stop.is_set():
                    self._maintenance_context.active = True
                    try:
                        self._orchestrator._repository.retire_known_failed_subtitle_calls(
                            backup_restore=self.backup_restore, now=self._orchestrator._now(),
                        )
                    finally:
                        self._maintenance_context.active = False
                return None
            gate = (nullcontext(True) if self.backup_restore is None
                    else self.backup_restore.background_work())
            with gate as allowed:
                if not allowed or self._stop.is_set():
                    return None
                if self.scheduler is not None:
                    self.scheduler.admit_due()
                queued = self._orchestrator.queued_runs(limit=1)
                if not queued:
                    return None
                run = queued[0]
                ingestion = self._orchestrator._ingestion
                if isinstance(ingestion, RuntimeSourceRunIngestion) and ingestion.caption_repair_is_waiting(run):
                    return run
                try:
                    return self._orchestrator.resume(run.run_id)
                except Exception:
                    if (self.scheduler is None or run.trigger is SourceRunTrigger.MANUAL_ANALYZE_VIDEO
                            or not is_tracked(self.scheduler.tracking.repository, run.source_id)):
                        raise
                    self.scheduler.tracking.settle_local_failure(run.source_id)
                    return self.scheduler.tracking.repository.transition_source_run(
                        run.run_id, to_state=SourceRunState.FAILED, now=self.scheduler.now()
                    )
        finally:
            self._execution.release()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None:
            thread.join()
        self._thread = None

    def _run(self) -> None:
        # resume_next already reloads RUNNING work alongside the durable queue;
        # recovery must use the same execution and Backup/Restore gate.
        while not self._stop.is_set():
            # Clear before reading durable work, so a notification during that
            # read/execution remains set and cannot be lost before the wait.
            self._wake.clear()
            try:
                result = self.run_once()
            except Exception:
                logging.getLogger(__name__).error("Source worker failed safely; retry deferred.")
                self._wake.wait(max(60.0, self._poll_seconds))
                continue
            if result is not None:
                continue
            try:
                protected = self.backup_restore is not None and not self.backup_restore.background_allowed
                wait = None if self.scheduler is None or protected else self.scheduler.wait_seconds()
            except Exception:
                logging.getLogger(__name__).error("Following schedule authority unavailable; retry deferred.")
                wait = 60.0
            self._wake.wait(wait)


@dataclass(frozen=True, slots=True)
class LocalSourceRunRuntime:
    repository: SQLiteStateRepository
    runtime: RuntimeOperations
    source_policy: SourcePolicyApplicationService
    distillation: PersonalizedDistillationService
    cloud_distillation: PersonalizedDistillationService
    orchestrator: DurableProcessingOrchestrator
    product: ProductOrchestrationService
    worker: DurableSourceRunWorker
    application: LocalApiApplication
    backup_restore: BackupRestoreService


def _deep_analysis_production_capability() -> DeepAnalysisCapability:
    """Configured/reachable candidates are distinct from reviewed qualification."""
    from youtube_intel.deep_analysis_activation import (
        production_deep_analysis_capability,
    )
    return production_deep_analysis_capability()


def build_local_source_run_runtime(
    *,
    config: AppConfig,
    project_root: Path,
    database: Path,
    dependencies: RuntimeDependencies | None = None,
    credential_store: CredentialStore | None = None,
    now: Callable[[], datetime] | None = None,
) -> LocalSourceRunRuntime:
    """Compose the GUI, scheduler, ingestion, and worker onto one durable authority."""

    now_fn = now or (lambda: datetime.now(UTC))
    data_root = (project_root / config.settings.storage.data_dir).resolve()

    def validate_current_local_summary(
        repository: SQLiteStateRepository,
        artifact_data_root: Path,
        video_id: str,
        artifact_id: str,
    ) -> object:
        return RuntimeOperations.validate_persisted_analysis_pointer(
            config=config,
            repository=repository,
            data_root=artifact_data_root,
            video_id=video_id,
            artifact_id=artifact_id,
        )

    backup_restore = BackupRestoreService(
        database=database,
        data_root=data_root,
        current_local_summary_validator=validate_current_local_summary,
    )
    backup_restore.recover_and_apply_pending_restore()
    repository = SQLiteStateRepository(database)
    repository.initialize(now=now_fn())
    runtime = RuntimeOperations(
        config=config,
        project_root=project_root,
        dependencies=dependencies,
        repository=repository,
    )
    source_policy = SourcePolicyApplicationService(repository, now=now_fn)
    transport = OllamaLocalDistillationTransport(
        settings=config.settings.local_scoring,
        production_qualified=False,
    )
    distillation = PersonalizedDistillationService(
        repository,
        source_policy,
        transport,
        ProductionDistillationBudget(),
        now=now_fn,
        output_language_for_video=runtime._intelligence_output_language,
    )
    # One independently reviewed K2.6 qualification passed. The UI still
    # requires a separate consent for each normal cloud execution.
    m12_moonshot_qualified = True
    eligibility = M12QualifiedCloudProductionAuthorizationAuthority.resolve(
        provider="moonshot", model="kimi-k2.6",
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=True,
    )
    model_settings = ModelSettingsService(
        credential_store or MacOSKeychainCredentialStore(),
        tags_fetch=lambda: local_models(config.settings.local_scoring.base_url),
    )

    def cloud_service() -> PersonalizedDistillationService:
        cloud_transport = MoonshotK26NonThinkingCloudDistillationTransport(
            authorization=CloudDistillationAuthorization.for_normal_production(
                eligibility=eligibility,
                cloud_enabled=m12_moonshot_qualified,
                credential_available=bool(model_settings.credential()),
            ),
            credential_resolver=model_settings.credential,
        )
        return PersonalizedDistillationService(
            repository, source_policy, cloud_transport, ProductionDistillationBudget(),
            now=now_fn, output_language_for_video=runtime._intelligence_output_language,
        )

    cloud_distillation = cloud_service()
    evidence_translation = EvidenceTranslationPresentationService(
        repository,
        OllamaEvidenceTranslator(settings=config.settings.local_analysis),
        now=now_fn,
    )
    from youtube_intel.providers.youtube_channel import YouTubeFollowingProvider
    source_tracking = FollowingTrackingService(repository, BilibiliContentProvider(repository, data_root, now=now_fn), youtube=YouTubeFollowingProvider(enroll_video=runtime.enroll_followed_youtube_video), now=now_fn)
    orchestrator = DurableProcessingOrchestrator(
        repository,
        source_policy=source_policy,
        distillation=distillation,
        discovery=PersistedSourceRunDiscovery(repository),
        ingestion=RuntimeSourceRunIngestion(runtime, source_policy, source_tracking),
        preparation=RuntimeSourceRunPreparation(runtime),
        now=now_fn,
    )
    product = ProductOrchestrationService(
        repository,
        source_run_submitter=orchestrator,
        source_tracking=source_tracking,
        now=now_fn,
    )
    worker = DurableSourceRunWorker(
        orchestrator, scheduler=FollowingScheduler(source_tracking, product, now=now_fn),
        backup_restore=backup_restore,
    )
    backup_restore.bind_background_wakeup(worker.notify_backup_window_closed)
    reader = AuthoritativeScoringReader(
        repository=repository,
        data_root=data_root,
        summary_threshold=config.settings.thresholds.summary_score,
        pipeline_version=PIPELINE_VERSION,
        current_model=config.settings.local_scoring.model,
    )
    # V1.x Content Deep Analysis. Per V1X-DR-001 and the frozen
    # CONFIGURED != QUALIFIED != PRODUCTION_ELIGIBLE rule, no route is
    # production-qualified in Phase 1A. `qwen2.5-coder:7b` stays a dev/test
    # candidate, so the production capability is empty and the product reports a
    # truthful NOT_QUALIFIED state. Tests and local development inject a route
    # explicitly through the service constructor instead of an env flag.
    deep_analysis = DeepAnalysisService(
        repository=repository,
        capability=_deep_analysis_production_capability(),
        scoring_reader=reader.read,
        transcript_reader=repository.get_verified_timed_transcript,
        evidence_reader=repository.list_canonical_coverage_evidence_ids,
        evidence_text_reader=repository.resolve_verified_evidence_text,
        now=now_fn,
    )
    application = LocalApiApplication(
        repository,
        product,
        scoring_reader=reader,
        distillation_service=distillation,
        cloud_distillation_service=cloud_distillation,
        cloud_intelligence_qualified=m12_moonshot_qualified,
        cloud_credential_available=bool(model_settings.credential()),
        model_settings=model_settings,
        refresh_cloud_distillation=cloud_service,
        processing_orchestrator=orchestrator,
        data_root=data_root,
        vault_root=(
            Path(config.settings.storage.vault_root)
            / config.settings.storage.vault_subdir
        ),
        timezone=config.settings.general.timezone,
        output_language_default=config.settings.general.output_language,
        now=now_fn,
        source_run_wakeup=worker.notify,
        source_tracking=source_tracking,
        local_distillation_available=transport.available,
        runtime_model=config.settings.local_scoring.model,
        runtime_model_digest=config.settings.local_scoring.expected_model_digest,
        analysis_reader=runtime._load_analysis,
        evidence_translation_service=evidence_translation,
        backup_restore_service=backup_restore,
        deep_analysis_service=deep_analysis,
        deep_analysis_publisher=DeepAnalysisObsidianPublisher(
            repository,
            vault_root=Path(config.settings.storage.vault_root),
            vault_subdir=config.settings.storage.vault_subdir,
        ),
    )
    return LocalSourceRunRuntime(
        repository=repository,
        runtime=runtime,
        source_policy=source_policy,
        distillation=distillation,
        cloud_distillation=cloud_distillation,
        orchestrator=orchestrator,
        product=product,
        worker=worker,
        application=application,
        backup_restore=backup_restore,
    )
