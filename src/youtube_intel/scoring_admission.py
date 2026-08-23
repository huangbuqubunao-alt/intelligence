"""Runtime-local, fail-closed admission for trusted scoring dispatches."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol

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
    build_provider_request_hash,
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


class _AdmissionRepository(Protocol):
    def get_job(self, job_id: str) -> JobRecord | None: ...

    def get_provider_call(self, request_hash: str) -> ProviderCallRecord | None: ...


def _canonical_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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


def build_repair_scoring_dispatch_identity(
    *,
    primary_scoring_request_hash: str,
    primary_normalized_input_hash: str,
    primary_raw_response_hash: str,
    primary_failure_class: str,
    repair_prompt_version: str,
    repair_schema_version: str,
    scoring_provider: str,
    scoring_model: str,
    scoring_model_digest: str,
    temperature: float,
    max_output_tokens: int,
    max_description_chars: int,
    output_language: str,
) -> ScoringDispatchIdentity:
    """Return the stable REPAIR identity without authorizing repair execution."""

    if primary_failure_class not in {
        "SCHEMA_OR_PARSE_INVALID",
        "LANGUAGE_INVALID",
        "DETERMINISTIC_QUALITY_REJECT",
        "JUDGE_REJECT",
        "JUDGE_UNCERTAIN",
    }:
        raise ValueError("primary failure class is not eligible for repair")
    operation = "local-scoring-repair-v1"
    normalized_input_hash = _canonical_hash(
        {
            "operation": operation,
            "primary_scoring_request_hash": primary_scoring_request_hash,
            "primary_normalized_input_hash": primary_normalized_input_hash,
            "primary_raw_response_hash": primary_raw_response_hash,
            "primary_failure_class": primary_failure_class,
            "repair_prompt_version": repair_prompt_version,
            "repair_schema_version": repair_schema_version,
            "scoring_provider": scoring_provider,
            "scoring_model": scoring_model,
            "scoring_model_digest": scoring_model_digest,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "max_description_chars": max_description_chars,
            "output_language": output_language,
        }
    )
    return ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR,
        operation=operation,
        normalized_input_hash=normalized_input_hash,
        request_hash=build_provider_request_hash(
            operation=operation,
            normalized_input_hash=normalized_input_hash,
            provider=scoring_provider,
            model=scoring_model,
            prompt_version=repair_prompt_version,
            schema_version=repair_schema_version,
        ),
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
    """One-shot in-memory admission tied to one uniquely owned SCORING job."""

    repository: _AdmissionRepository
    job_id: str
    owner: str
    _consumed_roles: set[ScoringDispatchRole] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not self.owner.strip():
            raise ValueError("scoring admission requires a job id and owner")

    def admit(self, identity: ScoringDispatchIdentity, *, now: datetime) -> None:
        """Consume a role only after durable lease and unknown-state checks."""

        if identity.role in self._consumed_roles:
            raise ScoringDispatchDenied("scoring dispatch role is already consumed")
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
        if self.repository.get_provider_call(identity.request_hash) is not None:
            raise ScoringDispatchDenied("existing provider state blocks scoring dispatch")
        self._consumed_roles.add(identity.role)
