"""Runtime-local, fail-closed admission for trusted scoring dispatches."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from itertools import count
from pathlib import Path
from threading import Lock
from typing import ClassVar, Protocol
from weakref import WeakKeyDictionary

from youtube_intel.domain import (
    AppError,
    ErrorCode,
    JobStatus,
    ProcessingStage,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    ScoringInput,
)
from youtube_intel.quality import TrustedScoringContext, build_judge_h1_h2
from youtube_intel.scoring import build_scoring_request_identity
from youtube_intel.state import (
    JobRecord,
    ProviderCallRecord,
)


class ScoringDispatchRole(str, Enum):
    PRIMARY = "PRIMARY"
    REPAIR = "REPAIR"
    PRIMARY_JUDGE = "PRIMARY_JUDGE"
    REPAIR_JUDGE = "REPAIR_JUDGE"


@dataclass(frozen=True, slots=True)
class ScoringDispatchIdentity:
    """Stable dispatch identity; it is never a durable reservation."""

    role: ScoringDispatchRole
    operation: str
    normalized_input_hash: str
    request_hash: str


class ScoringDispatchDenied(RuntimeError):
    """Raised before an external attempt whose ownership cannot be proven."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error = AppError(
            code=ErrorCode.INVALID_RESPONSE,
            message="scoring dispatch was denied before external provider contact",
            retryable=False,
            stage=ProcessingStage.SCORING,
        )


class UnknownProviderState(RuntimeError):
    """An external scoring provider may have received the request, but did not settle."""


class _AdmissionRepository(Protocol):
    def get_job(self, job_id: str) -> JobRecord | None: ...

    def get_provider_call(self, request_hash: str) -> ProviderCallRecord | None: ...


@dataclass(frozen=True, slots=True)
class _AdmissionExecutionKey:
    repository_scope: str
    job_id: str
    owner: str
    attempt_count: int


@dataclass(slots=True)
class _AdmissionExecutionState:
    consumed_roles: set[ScoringDispatchRole] = field(default_factory=set)
    lock: Lock = field(default_factory=Lock)


_IN_MEMORY_SCOPE_LOCK = Lock()
_IN_MEMORY_SCOPES: WeakKeyDictionary[object, str] = WeakKeyDictionary()
_IN_MEMORY_SCOPE_SEQUENCE = count()


def _repository_scope(repository: _AdmissionRepository) -> str:
    database_path = getattr(repository, "_database_path", None)
    if isinstance(database_path, Path):
        return str(database_path.resolve())
    with _IN_MEMORY_SCOPE_LOCK:
        try:
            scope = _IN_MEMORY_SCOPES.get(repository)
            if scope is None:
                scope = f"in-memory:{next(_IN_MEMORY_SCOPE_SEQUENCE)}"
                _IN_MEMORY_SCOPES[repository] = scope
            return scope
        except TypeError:
            # An unweakrefable test double cannot be retained by the registry.
            return f"in-memory-untracked:{id(repository)}"


class ScoringAdmissionRegistry:
    """Share one in-memory budget state for an active scoring job attempt."""

    _lock: ClassVar[Lock] = Lock()
    _states: ClassVar[dict[_AdmissionExecutionKey, _AdmissionExecutionState]] = {}

    def __init__(self, repository: _AdmissionRepository) -> None:
        self._repository = repository

    def admission_for(self, *, job_id: str, owner: str) -> ScoringDispatchAdmission:
        job = self._repository.get_job(job_id)
        if job is None:
            return ScoringDispatchAdmission(
                repository=self._repository,
                job_id=job_id,
                owner=owner,
            )
        return ScoringDispatchAdmission(
            repository=self._repository,
            job_id=job_id,
            owner=owner,
        )

    @classmethod
    def release_terminal(
        cls,
        *,
        repository: _AdmissionRepository,
        job_id: str,
        attempt_count: int,
    ) -> None:
        """Release shared state only after its job attempt is durably terminal."""

        scope = _repository_scope(repository)
        with cls._lock:
            for key in tuple(cls._states):
                if (
                    key.repository_scope == scope
                    and key.job_id == job_id
                    and key.attempt_count == attempt_count
                ):
                    del cls._states[key]

    @staticmethod
    def _key_for(
        *,
        repository: _AdmissionRepository,
        job_id: str,
        job: JobRecord,
        owner: str,
    ) -> _AdmissionExecutionKey:
        return _AdmissionExecutionKey(
            repository_scope=_repository_scope(repository),
            job_id=job_id,
            owner=owner,
            attempt_count=getattr(job, "attempt_count", 1),
        )

    @classmethod
    def state_for(
        cls,
        *,
        repository: _AdmissionRepository,
        job_id: str,
        job: JobRecord,
        owner: str,
    ) -> _AdmissionExecutionState:
        key = cls._key_for(
            repository=repository,
            job_id=job_id,
            job=job,
            owner=owner,
        )
        with cls._lock:
            return cls._states.setdefault(key, _AdmissionExecutionState())


def build_primary_scoring_dispatch_identity(
    *,
    scoring_input: ScoringInput,
    context: TrustedScoringContext,
) -> ScoringDispatchIdentity:
    """Return the frozen PRIMARY identity from current trusted context."""

    identity = build_scoring_request_identity(
        scoring_input=scoring_input,
        model=context.scoring_model,
        temperature=context.temperature,
        max_output_tokens=context.max_output_tokens,
        max_description_chars=context.max_description_chars,
    )
    return ScoringDispatchIdentity(
        role=ScoringDispatchRole.PRIMARY,
        operation=context.scoring_operation,
        normalized_input_hash=identity.normalized_input_hash,
        request_hash=identity.request_hash,
    )


def build_judge_scoring_dispatch_identity(
    operation_input: QualityJudgeOperationInput,
) -> ScoringDispatchIdentity:
    """Return the role-distinct, two-layer identity for a Judge dispatch."""

    h1, h2 = build_judge_h1_h2(operation_input)
    role = (
        ScoringDispatchRole.PRIMARY_JUDGE
        if operation_input.attempt_role is QualityJudgeAttemptRole.PRIMARY
        else ScoringDispatchRole.REPAIR_JUDGE
    )
    return ScoringDispatchIdentity(
        role=role,
        operation="local-content-quality-v1",
        normalized_input_hash=h1,
        request_hash=h2,
    )


@dataclass(slots=True)
class ScoringDispatchAdmission:
    """A view of the shared admission state for one active SCORING execution."""

    repository: _AdmissionRepository
    job_id: str
    owner: str

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not self.owner.strip():
            raise ValueError("scoring admission requires a job id and owner")

    def verify_active_lease(self, *, now: datetime) -> JobRecord:
        """Prove this view still owns the active SCORING lease without consuming budget."""

        job = self.repository.get_job(self.job_id)
        if job is None or job.target_stage is not ProcessingStage.SCORING:
            raise ScoringDispatchDenied("scoring lease is not exclusively active")
        if (
            job.status is not JobStatus.RUNNING
            or job.lease_owner != self.owner
            or job.lease_until is None
            or job.lease_until <= now
        ):
            raise ScoringDispatchDenied("scoring lease is not exclusively active")
        return job

    def admit(self, identity: ScoringDispatchIdentity, *, now: datetime) -> None:
        """Consume a role only after durable lease and unknown-state checks."""

        job = self.verify_active_lease(now=now)
        state = ScoringAdmissionRegistry.state_for(
            repository=self.repository,
            job_id=self.job_id,
            job=job,
            owner=self.owner,
        )
        with state.lock:
            if identity.role in {
                ScoringDispatchRole.REPAIR,
                ScoringDispatchRole.REPAIR_JUDGE,
            }:
                raise ScoringDispatchDenied("REPAIR admission is runtime-owned")
            if identity.role in state.consumed_roles:
                raise ScoringDispatchDenied("scoring dispatch role is already consumed")
            if self.repository.get_provider_call(identity.request_hash) is not None:
                raise ScoringDispatchDenied("existing provider state blocks scoring dispatch")
            state.consumed_roles.add(identity.role)
