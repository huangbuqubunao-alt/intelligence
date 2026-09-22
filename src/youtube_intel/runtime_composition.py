"""Production composition for loopback GUI-triggered durable Source Runs."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from youtube_intel.config import AppConfig
from youtube_intel.distillation import (
    BudgetDecision,
    CloudDistillationAuthorization,
    DistillationCommand,
    NvidiaNimCloudDistillationTransport,
    PersonalizedDistillationService,
)
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.processing_orchestrator import (
    DurableProcessingOrchestrator,
    PersistedSourceRunDiscovery,
    SourceRunDiscoveryError,
)
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
            raise SourceRunDiscoveryError("Source ingestion failed safely") from error


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
    orchestrator: DurableProcessingOrchestrator
    product: ProductOrchestrationService
    worker: DurableSourceRunWorker
    application: LocalApiApplication


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
    repository = SQLiteStateRepository(database)
    repository.initialize(now=now_fn())
    runtime = RuntimeOperations(
        config=config,
        project_root=project_root,
        dependencies=dependencies,
        repository=repository,
    )
    source_policy = SourcePolicyApplicationService(repository, now=now_fn)
    authorization = CloudDistillationAuthorization()

    def unavailable_credential() -> str:
        raise RuntimeError("cloud credentials are not enabled for local GUI execution")

    transport = NvidiaNimCloudDistillationTransport(
        authorization=authorization,
        credential_resolver=unavailable_credential,
    )
    distillation = PersonalizedDistillationService(
        repository,
        source_policy,
        transport,
        ProductionDistillationBudget(),
        now=now_fn,
    )
    orchestrator = DurableProcessingOrchestrator(
        repository,
        source_policy=source_policy,
        distillation=distillation,
        discovery=PersistedSourceRunDiscovery(repository),
        ingestion=RuntimeSourceRunIngestion(runtime, source_policy),
        now=now_fn,
    )
    product = ProductOrchestrationService(
        repository,
        source_run_submitter=orchestrator,
        now=now_fn,
    )
    worker = DurableSourceRunWorker(orchestrator)
    data_root = (project_root / config.settings.storage.data_dir).resolve()
    reader = AuthoritativeScoringReader(
        repository=repository,
        data_root=data_root,
        summary_threshold=config.settings.thresholds.summary_score,
        pipeline_version=PIPELINE_VERSION,
        current_model=config.settings.local_scoring.model,
    )
    application = LocalApiApplication(
        repository,
        product,
        scoring_reader=reader,
        distillation_service=distillation,
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
        nvidia_distillation_available=transport.available,
    )
    return LocalSourceRunRuntime(
        repository=repository,
        runtime=runtime,
        source_policy=source_policy,
        distillation=distillation,
        orchestrator=orchestrator,
        product=product,
        worker=worker,
        application=application,
    )
