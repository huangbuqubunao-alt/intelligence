"""Production composition for loopback GUI-triggered durable Source Runs."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.config import AppConfig
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
from youtube_intel.evidence_translation import EvidenceTranslationPresentationService
from youtube_intel.local_api import LocalApiApplication
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
from youtube_intel.source_run import SourceRunRecord
from youtube_intel.state import SQLiteStateRepository


class RuntimeSourceRunIngestion:
    """Persist bounded production ingestion for the durable discovery checkpoint."""

    def __init__(
        self,
        runtime: RuntimeOperations,
        source_policy: SourcePolicyApplicationService,
    ) -> None:
        self._runtime = runtime
        self._source_policy = source_policy

    def ingest(self, source_id: str) -> None:
        policy = self._source_policy.effective_policy(source_id)
        try:
            self._runtime.ingest_source_to_transcript(
                source_id,
                limit=policy.per_run_max_new_videos,
            )
        except Exception as error:
            if isinstance(error, SourceRunDiscoveryError):
                raise
            raise SourceRunDiscoveryError("Source ingestion failed safely") from error


class RuntimeSourceRunPreparation:
    """Run the existing M1 pipeline only after durable filtering marks content relevant."""

    def __init__(self, runtime: RuntimeOperations) -> None:
        self._runtime = runtime

    def prepare(self, video_id: str) -> bool:
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
    ) -> None:
        if poll_seconds <= 0:
            raise ValueError("worker poll interval must be positive")
        self._orchestrator = orchestrator
        self._poll_seconds = poll_seconds
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run,
            name="youtube-intel-source-runs",
            daemon=True,
        )
        self._thread.start()

    def notify(self) -> None:
        self._wake.set()

    def run_once(self) -> SourceRunRecord | None:
        return self._orchestrator.resume_next()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5)
        self._thread = None

    def _run(self) -> None:
        for interrupted in self._orchestrator.interrupted_runs():
            if self._stop.is_set():
                return
            try:
                self._orchestrator.resume(interrupted.run_id)
            except Exception:
                continue
        while not self._stop.is_set():
            try:
                result = self.run_once()
            except Exception:
                self._wake.wait(self._poll_seconds)
                self._wake.clear()
                continue
            if result is not None:
                continue
            self._wake.wait(self._poll_seconds)
            self._wake.clear()


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
    """Resolve the production Deep Analysis capability.

    Qualification is an activation gate, not an architecture gate, and it is
    **never** a configuration fact:

        CONFIGURED != AVAILABLE != QUALIFIED != PRODUCTION_ELIGIBLE

    Phase 1A ships no qualification authority or receipt, so this resolves to an
    empty capability. An empty registry yields a truthful ``NOT_QUALIFIED``
    product state; it never promotes a dev/test candidate such as
    ``qwen2.5-coder:7b`` into a production-qualified route.

    Environment variables, model presence, and configuration are deliberately
    ignored here. Real model qualification is Phase 1C work and must arrive as a
    reviewed authority, not as an environment flag.
    """

    return DeepAnalysisCapability()


def build_local_source_run_runtime(
    *,
    config: AppConfig,
    project_root: Path,
    database: Path,
    dependencies: RuntimeDependencies | None = None,
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
        output_language_for_video=runtime._downstream_output_language,
    )
    # One independently reviewed K2.6 qualification passed. The UI still
    # requires a separate consent for each normal cloud execution.
    m12_moonshot_qualified = True
    eligibility = M12QualifiedCloudProductionAuthorizationAuthority.resolve(
        provider="moonshot", model="kimi-k2.6",
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=True,
    )
    cloud_transport = MoonshotK26NonThinkingCloudDistillationTransport.with_environment_credential(
        authorization=CloudDistillationAuthorization.for_normal_production(
            eligibility=eligibility,
            cloud_enabled=m12_moonshot_qualified,
            credential_available=bool(os.environ.get("MOONSHOT_API_KEY")),
        )
    )
    cloud_distillation = PersonalizedDistillationService(
        repository, source_policy, cloud_transport, ProductionDistillationBudget(),
        now=now_fn, output_language_for_video=runtime._downstream_output_language,
    )
    evidence_translation = EvidenceTranslationPresentationService(
        repository,
        OllamaEvidenceTranslator(settings=config.settings.local_analysis),
        now=now_fn,
    )
    orchestrator = DurableProcessingOrchestrator(
        repository,
        source_policy=source_policy,
        distillation=distillation,
        discovery=PersistedSourceRunDiscovery(repository),
        ingestion=RuntimeSourceRunIngestion(runtime, source_policy),
        preparation=RuntimeSourceRunPreparation(runtime),
        now=now_fn,
    )
    product = ProductOrchestrationService(
        repository,
        source_run_submitter=orchestrator,
        now=now_fn,
    )
    worker = DurableSourceRunWorker(orchestrator)
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
        cloud_credential_available=bool(os.environ.get("MOONSHOT_API_KEY")),
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
        local_distillation_available=transport.available,
        analysis_reader=runtime._load_analysis,
        evidence_translation_service=evidence_translation,
        backup_restore_service=backup_restore,
        deep_analysis_service=deep_analysis,
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
