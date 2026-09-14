"""Supported local normal-production composition for V1 Video Distillation."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from threading import Lock
from typing import cast

from youtube_intel.distillation import (
    BudgetDecision,
    CloudDistillationAuthorization,
    DistillationCapabilityScope,
    DistillationCommand,
    DistillationTransport,
    NormalV1ProductionAuthorizationAuthority,
    NvidiaNimCloudDistillationTransport,
    PersonalizedDistillationService,
    ProviderProductionEligibility,
)
from youtube_intel.processing_orchestrator import DurableProcessingOrchestrator
from youtube_intel.readiness import BudgetReadiness, ProductionReadinessAuthority
from youtube_intel.source_policy import SourcePolicyApplicationService
from youtube_intel.source_run import SourceRunRecord
from youtube_intel.state import SQLiteStateRepository


class PersistentDistillationCallBudget:
    """Enforce one explicit call-count limit from existing TASK-022 ledger truth."""

    def __init__(self, repository: SQLiteStateRepository, *, call_limit: int) -> None:
        if not isinstance(call_limit, int) or isinstance(call_limit, bool):
            raise TypeError("Video Distillation call limit must be an integer")
        if not 0 <= call_limit <= 5:
            raise ValueError("Video Distillation call limit must be between 0 and 5")
        self._repository = repository
        self._call_limit = call_limit

    def snapshot(self) -> BudgetReadiness:
        used = self._repository.total_distillation_invocation_count()
        if used >= self._call_limit:
            return BudgetReadiness.limit_reached(limit=self._call_limit, used=used)
        return BudgetReadiness.within_limit(limit=self._call_limit, used=used)

    def check(self, command: DistillationCommand) -> BudgetDecision:
        del command
        snapshot = self.snapshot()
        return BudgetDecision(
            allowed=snapshot.code == "WITHIN_LIMIT", state=snapshot.code
        )


class DurableSourceRunWorker:
    """Execute accepted durable runs off the API request thread, one at a time."""

    def __init__(self, orchestrator: DurableProcessingOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="source-run"
        )
        self._lock = Lock()
        self._active: dict[str, Future[SourceRunRecord]] = {}
        self._closed = False

    def submit(self, run_id: str) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("Source Run worker is closed")
            if run_id in self._active:
                return
            future = self._executor.submit(self._orchestrator.resume, run_id)
            self._active[run_id] = future
            future.add_done_callback(partial(self._finished, run_id))

    def _finished(self, run_id: str, future: Future[SourceRunRecord]) -> None:
        del future
        with self._lock:
            self._active.pop(run_id, None)

    def wait_for_idle(self, *, timeout: float) -> None:
        if timeout <= 0:
            raise ValueError("worker wait timeout must be positive")
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                futures = tuple(self._active.values())
            if not futures:
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Source Run worker did not become idle")
            for future in futures:
                future.result(timeout=remaining)

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=False)


@dataclass(frozen=True, slots=True)
class NormalProductionRuntime:
    eligibility: ProviderProductionEligibility
    budget: PersistentDistillationCallBudget
    readiness: ProductionReadinessAuthority
    distillation: PersonalizedDistillationService
    orchestrator: DurableProcessingOrchestrator
    worker: DurableSourceRunWorker


def build_normal_production_runtime(
    repository: SQLiteStateRepository,
    *,
    enabled: bool,
    call_limit: int,
    environment: Mapping[str, str] | None = None,
    provider_available: bool = True,
    wire_transport: Callable[..., Mapping[str, object]] | None = None,
    now: Callable[[], datetime] | None = None,
) -> NormalProductionRuntime:
    """Connect the standard API runtime to the exact TASK-022D route.

    ``wire_transport`` is the sole deterministic test seam.  Production callers
    omit it and therefore use the fixed NVIDIA NIM HTTPS adapter endpoint.
    """

    if type(enabled) is not bool or type(provider_available) is not bool:
        raise TypeError("production runtime gates must be finite")
    current_time = now or (lambda: datetime.now(UTC))
    source_environment = os.environ if environment is None else environment
    credential_value = source_environment.get("NVIDIA_API_KEY")
    credential_available = isinstance(credential_value, str) and bool(
        credential_value.strip()
    )
    credential_value = None

    def resolve_credential() -> str:
        value = source_environment.get("NVIDIA_API_KEY")
        return value if isinstance(value, str) and bool(value.strip()) else ""

    eligibility = NormalV1ProductionAuthorizationAuthority.resolve(
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=provider_available,
    )
    authorization = CloudDistillationAuthorization.for_normal_production(
        eligibility=eligibility,
        cloud_enabled=enabled,
        credential_available=credential_available,
    )
    transport = (
        NvidiaNimCloudDistillationTransport(
            authorization=authorization,
            credential_resolver=resolve_credential,
        )
        if wire_transport is None
        else NvidiaNimCloudDistillationTransport(
            authorization=authorization,
            credential_resolver=resolve_credential,
            wire_transport=wire_transport,
        )
    )
    budget = PersistentDistillationCallBudget(repository, call_limit=call_limit)
    source_policy = SourcePolicyApplicationService(repository, now=current_time)
    distillation = PersonalizedDistillationService(
        repository,
        source_policy,
        cast(DistillationTransport, transport),
        budget,
        now=current_time,
    )
    orchestrator = DurableProcessingOrchestrator(
        repository,
        source_policy=source_policy,
        distillation=distillation,
        now=current_time,
    )
    readiness = ProductionReadinessAuthority(
        repository,
        runtime_enabled=enabled,
        eligibility=eligibility,
        credential_available=credential_available,
        budget=budget,
    )
    worker = DurableSourceRunWorker(orchestrator)
    runtime = NormalProductionRuntime(
        eligibility=eligibility,
        budget=budget,
        readiness=readiness,
        distillation=distillation,
        orchestrator=orchestrator,
        worker=worker,
    )
    for run in orchestrator.queued_runs():
        if readiness.can_start(source_id=run.source_id):
            worker.submit(run.run_id)
    return runtime


__all__ = [
    "DurableSourceRunWorker",
    "NormalProductionRuntime",
    "PersistentDistillationCallBudget",
    "build_normal_production_runtime",
]
