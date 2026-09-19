"""Fail-closed, provider-free personalized distillation admission service."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Protocol

from youtube_intel.domain import Availability
from youtube_intel.source_policy import SourcePolicyApplicationService
from youtube_intel.state import (
    ArtifactKind,
    DistillationCardWrite,
    DistillationExecutionRecord,
    DistillationExecutionWrite,
    EvidenceAvailability,
    EvidenceStance,
    FilterOutcome,
    IntegrityConflict,
    IntelligenceClaimKind,
    SQLiteStateRepository,
    StateStoreError,
)


class DistillationExecutionStatus(str, Enum):
    WAITING_BUDGET = "WAITING_BUDGET"
    WAITING_MODEL = "WAITING_MODEL"
    REJECTED_INELIGIBLE = "REJECTED_INELIGIBLE"
    REJECTED_EVIDENCE = "REJECTED_EVIDENCE"
    REJECTED_OUTPUT = "REJECTED_OUTPUT"
    AMBIGUOUS = "AMBIGUOUS"
    SUCCEEDED = "SUCCEEDED"
    SUCCEEDED_NO_NEW_INTELLIGENCE = "SUCCEEDED_NO_NEW_INTELLIGENCE"


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    allowed: bool
    state: str

    def __post_init__(self) -> None:
        if not self.state.strip() or len(self.state) > 160:
            raise ValueError("budget state is invalid")


@dataclass(frozen=True, slots=True)
class ActivePreferenceProjection:
    """Legal, immutable personalization input passed to the offline transport."""

    preference_id: str
    horizon: str
    provenance: str
    scope: str
    target_id: str | None
    statement: str


@dataclass(frozen=True, slots=True)
class DistillationCommand:
    execution_id: str
    source_id: str
    video_id: str
    evidence_ids: tuple[str, ...]
    reason: str
    use_case: str
    selected_provider: str
    selected_model: str
    preference_ids: tuple[str, ...] = ()
    active_preferences: tuple[ActivePreferenceProjection, ...] = ()
    source_focus_rules: tuple[str, ...] = ()
    source_ignore_rules: tuple[str, ...] = ()
    source_policy_revision_id: str | None = None
    distillation_style: str | None = None


@dataclass(frozen=True, slots=True)
class DistillationTransportResult:
    raw: str
    actual_provider: str
    actual_model: str
    input_tokens: int | None
    output_tokens: int | None
    cost_microunits: int | None
    duration_ms: int | None


@dataclass(frozen=True, slots=True)
class DistillationResult:
    execution_id: str
    status: DistillationExecutionStatus
    invocation_count: int
    intelligence_id: str | None
    revision_id: str | None


@dataclass(frozen=True, slots=True)
class DistillationReservation:
    """Canonical TASK-022 execution identity safe to bind before dispatch."""

    execution_id: str
    source_id: str
    video_id: str


class DistillationBudget(Protocol):
    def check(self, command: DistillationCommand) -> BudgetDecision: ...


class DistillationTransport(Protocol):
    """A deliberately offline deterministic transport used only in this task."""

    is_offline_test_transport: bool
    available: bool
    actual_provider: str
    actual_model: str

    def generate(self, command: DistillationCommand) -> DistillationTransportResult: ...


@dataclass(frozen=True, slots=True)
class _Candidate:
    claim_kind: IntelligenceClaimKind
    evidence_ids: tuple[str, ...]
    evidence_stances: tuple[tuple[str, EvidenceStance], ...]
    card: DistillationCardWrite
    canonical_content: bytes


@dataclass(frozen=True, slots=True)
class _NoNewCandidate:
    """A positive zero-result bound to the exact current Evidence set."""

    evidence_ids: tuple[str, ...]


class PersonalizedDistillationService:
    """Admits only evidence-bound output from an injected offline/test transport."""

    _RESERVED_NOT_DISPATCHED = "RESERVED_NOT_DISPATCHED"
    _DISPATCH_CLAIMED = "DISPATCH_CLAIMED"
    _RESERVATION_REASON = "SOURCE_RUN_PERSONALIZED_DISTILLATION"
    _RESERVATION_USE_CASE = "PERSONALIZED_INTELLIGENCE"

    def __init__(
        self,
        repository: SQLiteStateRepository,
        source_policy: SourcePolicyApplicationService,
        transport: DistillationTransport,
        budget: DistillationBudget,
        *,
        now: Callable[[], datetime],
    ) -> None:
        if not transport.is_offline_test_transport:
            raise ValueError("TASK-022 accepts only offline deterministic transports")
        if not transport.actual_provider.strip() or not transport.actual_model.strip():
            raise ValueError("offline transport identity is invalid")
        self._repository = repository
        self._source_policy = source_policy
        self._transport = transport
        self._budget = budget
        self._now = now
        self._selected_provider = transport.actual_provider
        self._selected_model = transport.actual_model

    def manual_command(
        self,
        *,
        execution_id: str,
        source_id: str,
        video_id: str,
        evidence_ids: tuple[str, ...],
    ) -> DistillationCommand:
        """Build an API-safe manual command without caller-selected model inputs."""
        return DistillationCommand(
            execution_id=execution_id,
            source_id=source_id,
            video_id=video_id,
            evidence_ids=evidence_ids,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider=self._selected_provider,
            selected_model=self._selected_model,
        )

    @staticmethod
    def _reservation_id(
        *,
        source_id: str,
        video_id: str,
        evidence_ids: tuple[str, ...],
        selected_provider: str,
        selected_model: str,
    ) -> str:
        canonical = json.dumps(
            {
                "evidence_ids": evidence_ids,
                "reason": PersonalizedDistillationService._RESERVATION_REASON,
                "selected_model": selected_model,
                "selected_provider": selected_provider,
                "source_id": source_id,
                "use_case": PersonalizedDistillationService._RESERVATION_USE_CASE,
                "video_id": video_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"distillation:reservation:v1:{hashlib.sha256(canonical).hexdigest()}"

    def _canonical_reservation_evidence(
        self, *, video_id: str, evidence_ids: tuple[str, ...]
    ) -> tuple[str, ...]:
        if (
            not isinstance(evidence_ids, tuple)
            or not evidence_ids
            or any(
                not isinstance(evidence_id, str)
                or not evidence_id.strip()
                or evidence_id != evidence_id.strip()
                or len(evidence_id) > 512
                for evidence_id in evidence_ids
            )
        ):
            raise ValueError("reservation evidence is invalid")
        normalized = tuple(sorted(evidence_ids))
        if len(normalized) > 20 or len(set(normalized)) != len(normalized):
            raise ValueError("reservation evidence is invalid")
        canonical = self._repository.list_available_canonical_evidence_ids(video_id)
        if normalized != canonical:
            raise ValueError("reservation requires the current canonical evidence set")
        return canonical

    def _reserved_command(
        self, *, source_id: str, video_id: str, evidence_ids: tuple[str, ...]
    ) -> DistillationCommand:
        return DistillationCommand(
            execution_id=self._reservation_id(
                source_id=source_id,
                video_id=video_id,
                evidence_ids=evidence_ids,
                selected_provider=self._selected_provider,
                selected_model=self._selected_model,
            ),
            source_id=source_id,
            video_id=video_id,
            evidence_ids=evidence_ids,
            reason=self._RESERVATION_REASON,
            use_case=self._RESERVATION_USE_CASE,
            selected_provider=self._selected_provider,
            selected_model=self._selected_model,
        )

    @staticmethod
    def _same_execution_identity(
        record: DistillationExecutionRecord, command: DistillationCommand
    ) -> bool:
        return (
            record.execution_id == command.execution_id
            and record.source_id == command.source_id
            and record.video_id == command.video_id
            and record.reason == command.reason
            and record.use_case == command.use_case
            and record.selected_provider == command.selected_provider
            and record.selected_model == command.selected_model
        )

    def reserve_distillation_execution(
        self, *, source_id: str, video_id: str, evidence_ids: tuple[str, ...]
    ) -> DistillationReservation:
        """Mint the sole canonical execution identity before any dispatch exists.

        The supplied evidence set must equal the current persisted canonical
        transcript evidence set.  That lets a later process rebuild and verify
        the exact command from m010/Evidence persistence rather than memory.
        """
        canonical_evidence = self._canonical_reservation_evidence(
            video_id=video_id, evidence_ids=evidence_ids
        )
        command = self._reserved_command(
            source_id=source_id, video_id=video_id, evidence_ids=canonical_evidence
        )
        if not self._eligible(command):
            raise ValueError("reservation source/video is not eligible")
        if not self._legal_evidence(command):
            raise ValueError("reservation evidence is not legal")
        existing = self._repository.get_distillation_execution(command.execution_id)
        if existing is None:
            try:
                existing = self._repository.reserve_distillation_execution(
                    DistillationExecutionWrite(
                        execution_id=command.execution_id,
                        source_id=command.source_id,
                        video_id=command.video_id,
                        reason=command.reason,
                        use_case=command.use_case,
                        selected_provider=command.selected_provider,
                        selected_model=command.selected_model,
                    ),
                    now=self._now(),
                )
            except IntegrityConflict:
                existing = self._repository.get_distillation_execution(command.execution_id)
        if existing is None or not self._same_execution_identity(existing, command):
            raise StateStoreError("distillation reservation identity conflicts")
        if not (
            existing.status == "PENDING"
            and existing.budget_state == self._RESERVED_NOT_DISPATCHED
            and existing.invocation_count == 0
        ):
            raise StateStoreError("existing execution is no longer a safe reservation")
        return DistillationReservation(
            execution_id=existing.execution_id,
            source_id=existing.source_id,
            video_id=existing.video_id,
        )

    @staticmethod
    def _result(record: DistillationExecutionRecord) -> DistillationResult:
        try:
            status = DistillationExecutionStatus(record.status)
        except ValueError as error:
            raise StateStoreError("distillation execution persistence is invalid") from error
        return DistillationResult(
            execution_id=record.execution_id,
            status=status,
            invocation_count=record.invocation_count,
            intelligence_id=record.intelligence_id,
            revision_id=record.revision_id,
        )

    def _begin(self, command: DistillationCommand) -> None:
        self._repository.begin_distillation_execution(
            DistillationExecutionWrite(
                execution_id=command.execution_id,
                source_id=command.source_id,
                video_id=command.video_id,
                reason=command.reason,
                use_case=command.use_case,
                selected_provider=command.selected_provider,
                selected_model=command.selected_model,
            ),
            now=self._now(),
        )

    def _finish(
        self,
        command: DistillationCommand,
        *,
        status: DistillationExecutionStatus,
        budget_state: str,
        outcome: str,
        invocation_count: int,
        result: DistillationTransportResult | None = None,
    ) -> DistillationResult:
        return self._finish_execution(
            execution_id=command.execution_id,
            status=status,
            budget_state=budget_state,
            outcome=outcome,
            invocation_count=invocation_count,
            result=result,
        )

    def _finish_execution(
        self,
        *,
        execution_id: str,
        status: DistillationExecutionStatus,
        budget_state: str,
        outcome: str,
        invocation_count: int,
        result: DistillationTransportResult | None = None,
    ) -> DistillationResult:
        record = self._repository.finish_distillation_without_admission(
            execution_id=execution_id,
            status=status.value,
            budget_state=budget_state,
            outcome=outcome,
            invocation_count=invocation_count,
            actual_provider=None if result is None else result.actual_provider,
            actual_model=None if result is None else result.actual_model,
            input_tokens=None if result is None else result.input_tokens,
            output_tokens=None if result is None else result.output_tokens,
            cost_microunits=None if result is None else result.cost_microunits,
            duration_ms=None if result is None else result.duration_ms,
            now=self._now(),
        )
        return self._result(record)

    def _finish_or_recover(
        self,
        command: DistillationCommand,
        *,
        status: DistillationExecutionStatus,
        budget_state: str,
        outcome: str,
        invocation_count: int,
        result: DistillationTransportResult | None = None,
    ) -> DistillationResult:
        try:
            return self._finish(
                command,
                status=status,
                budget_state=budget_state,
                outcome=outcome,
                invocation_count=invocation_count,
                result=result,
            )
        except StateStoreError:
            persisted = self._repository.get_distillation_execution(command.execution_id)
            if persisted is not None and persisted.status != "PENDING":
                return self._result(persisted)
            raise

    def _projection(self, command: DistillationCommand) -> DistillationCommand:
        policy = self._source_policy.effective_policy(command.source_id)
        projection = replace(
            command,
            evidence_ids=tuple(sorted(command.evidence_ids)),
            active_preferences=tuple(
                ActivePreferenceProjection(
                    preference_id=item.preference_id,
                    horizon=item.horizon.value,
                    provenance=item.provenance.value,
                    scope=item.scope.value,
                    target_id=item.target_id,
                    statement=item.statement,
                )
                for item in self._repository.list_active_preferences(now=self._now())
            ),
            source_focus_rules=policy.focus_rules,
            source_ignore_rules=policy.ignore_rules,
            source_policy_revision_id=policy.source_policy_revision_id,
            distillation_style=policy.distillation_style.value,
        )
        return replace(
            projection,
            preference_ids=tuple(item.preference_id for item in projection.active_preferences),
        )

    def _dispatch_and_admit(
        self, projection: DistillationCommand, decision: BudgetDecision
    ) -> DistillationResult:
        try:
            response = self._transport.generate(projection)
        except Exception:
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.AMBIGUOUS,
                budget_state=decision.state,
                outcome="TRANSPORT_OUTCOME_UNKNOWN",
                invocation_count=1,
                result=DistillationTransportResult(
                    raw="",
                    actual_provider=self._transport.actual_provider,
                    actual_model=self._transport.actual_model,
                    input_tokens=None,
                    output_tokens=None,
                    cost_microunits=None,
                    duration_ms=None,
                ),
            )
        if (
            response.actual_provider != projection.selected_provider
            or response.actual_model != projection.selected_model
        ):
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.REJECTED_OUTPUT,
                budget_state=decision.state,
                outcome="ACTUAL_MODEL_MISMATCH",
                invocation_count=1,
                result=response,
            )
        try:
            candidate = self._parse_candidate(response.raw, projection)
            if isinstance(candidate, _NoNewCandidate):
                record = self._repository.record_distillation_no_new_intelligence(
                    execution_id=projection.execution_id,
                    evidence_ids=candidate.evidence_ids,
                    budget_state=decision.state,
                    actual_provider=response.actual_provider,
                    actual_model=response.actual_model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost_microunits=response.cost_microunits,
                    duration_ms=response.duration_ms,
                    now=self._now(),
                )
            else:
                record = self._repository.admit_distillation(
                    execution_id=projection.execution_id,
                    intelligence_id=f"intelligence:distillation:{projection.execution_id}",
                    revision_id=f"revision:distillation:{projection.execution_id}",
                    claim_kind=candidate.claim_kind,
                    content_hash=hashlib.sha256(candidate.canonical_content).hexdigest(),
                    evidence_ids=candidate.evidence_ids,
                    evidence_stances=candidate.evidence_stances,
                    card=candidate.card,
                    actual_provider=response.actual_provider,
                    actual_model=response.actual_model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost_microunits=response.cost_microunits,
                    duration_ms=response.duration_ms,
                    now=self._now(),
                )
        except (IntegrityConflict, StateStoreError, ValueError):
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.REJECTED_OUTPUT,
                budget_state=decision.state,
                outcome="STRUCTURED_OR_EVIDENCE_VALIDATION_REJECTED",
                invocation_count=1,
                result=response,
            )
        return self._result(record)

    def _reserved_command_from_record(
        self, record: DistillationExecutionRecord
    ) -> DistillationCommand:
        if (
            record.selected_provider != self._selected_provider
            or record.selected_model != self._selected_model
        ):
            raise ValueError("reserved execution model identity does not match TASK-022 transport")
        evidence_ids = self._repository.list_available_canonical_evidence_ids(record.video_id)
        command = self._reserved_command(
            source_id=record.source_id,
            video_id=record.video_id,
            evidence_ids=evidence_ids,
        )
        if not self._same_execution_identity(record, command):
            raise StateStoreError("reserved execution context is not persistently reconstructible")
        return command

    def _close_claimed_reservation_as_ambiguous(
        self, record: DistillationExecutionRecord
    ) -> DistillationResult:
        if (
            record.selected_provider != self._selected_provider
            or record.selected_model != self._selected_model
        ):
            raise ValueError("reserved execution model identity does not match TASK-022 transport")
        try:
            return self._finish_execution(
                execution_id=record.execution_id,
                status=DistillationExecutionStatus.AMBIGUOUS,
                budget_state="UNKNOWN",
                outcome="RESERVED_DISPATCH_OUTCOME_UNKNOWN",
                invocation_count=1,
                result=DistillationTransportResult(
                    raw="",
                    actual_provider=self._transport.actual_provider,
                    actual_model=self._transport.actual_model,
                    input_tokens=None,
                    output_tokens=None,
                    cost_microunits=None,
                    duration_ms=None,
                ),
            )
        except StateStoreError:
            persisted = self._repository.get_distillation_execution(record.execution_id)
            if persisted is not None and persisted.status != "PENDING":
                return self._result(persisted)
            raise

    def _recover_reserved_execution(self, execution_id: str) -> DistillationResult:
        record = self._repository.get_distillation_execution(execution_id)
        if record is None:
            raise StateStoreError("reserved execution disappeared")
        if record.status != "PENDING":
            return self._result(record)
        if (
            record.budget_state == self._DISPATCH_CLAIMED
            and record.invocation_count == 1
        ):
            return self._close_claimed_reservation_as_ambiguous(record)
        raise StateStoreError("distillation execution is not a safely reserved pre-dispatch state")

    def continue_reserved_distillation(self, execution_id: str) -> DistillationResult:
        """Continue exactly one persisted reservation through the TASK-022 path.

        The public seam accepts only the canonical execution identity.  It rebuilds
        the command from persisted m010/Evidence rows, applies normal policy and
        budget gates, and atomically records a possible dispatch before calling
        the transport.  A claimed record is AMBIGUOUS, never redispatchable.
        """
        if not isinstance(execution_id, str) or not execution_id.strip() or len(execution_id) > 512:
            raise ValueError("reserved execution identity is invalid")
        record = self._repository.get_distillation_execution(execution_id)
        if record is None:
            raise ValueError("reserved execution does not exist")
        if record.status != "PENDING":
            return self._result(record)
        if (
            record.budget_state == self._DISPATCH_CLAIMED
            and record.invocation_count == 1
        ):
            return self._close_claimed_reservation_as_ambiguous(record)
        if not (
            record.budget_state == self._RESERVED_NOT_DISPATCHED
            and record.invocation_count == 0
        ):
            raise StateStoreError("distillation execution is not a safely reserved pre-dispatch state")
        command = self._reserved_command_from_record(record)
        if not self._eligible(command):
            return self._finish_or_recover(
                command,
                status=DistillationExecutionStatus.REJECTED_INELIGIBLE,
                budget_state="NOT_CHECKED",
                outcome="SOURCE_POLICY_INELIGIBLE",
                invocation_count=0,
            )
        if not self._legal_evidence(command):
            return self._finish_or_recover(
                command,
                status=DistillationExecutionStatus.REJECTED_EVIDENCE,
                budget_state="NOT_CHECKED",
                outcome="EVIDENCE_UNAVAILABLE_OR_FOREIGN",
                invocation_count=0,
            )
        projection = self._projection(command)
        decision = self._budget.check(projection)
        if not decision.allowed:
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.WAITING_BUDGET,
                budget_state=decision.state,
                outcome="BUDGET_BLOCKED_BEFORE_TRANSPORT",
                invocation_count=0,
            )
        if not self._transport.available:
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.WAITING_MODEL,
                budget_state=decision.state,
                outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT",
                invocation_count=0,
            )
        claimed = self._repository.claim_reserved_distillation_execution(
            execution_id=projection.execution_id,
            source_id=projection.source_id,
            video_id=projection.video_id,
            reason=projection.reason,
            use_case=projection.use_case,
            selected_provider=projection.selected_provider,
            selected_model=projection.selected_model,
            now=self._now(),
        )
        if not claimed:
            return self._recover_reserved_execution(projection.execution_id)
        return self._dispatch_and_admit(projection, decision)

    def _eligible(self, command: DistillationCommand) -> bool:
        source = self._repository.get_source_subscription(command.source_id)
        if source is None or not source.enabled:
            return False
        decision = self._repository.current_filter_decision(command.source_id, command.video_id)
        return decision is not None and decision.outcome is FilterOutcome.RELEVANT

    def _legal_evidence(self, command: DistillationCommand) -> bool:
        if (
            not isinstance(command.evidence_ids, tuple)
            or not command.evidence_ids
            or len(command.evidence_ids) > 20
            or any(
                not isinstance(evidence_id, str)
                or not evidence_id.strip()
                or len(evidence_id) > 512
                for evidence_id in command.evidence_ids
            )
        ):
            return False
        evidence_ids = tuple(sorted(command.evidence_ids))
        if len(set(evidence_ids)) != len(evidence_ids):
            return False
        video = self._repository.get_video(command.video_id)
        if video is None or video.availability is not Availability.PUBLIC:
            return False
        if not self._repository.source_has_video(command.source_id, command.video_id):
            return False
        for evidence_id in evidence_ids:
            evidence = self._repository.get_evidence(evidence_id)
            if (
                evidence is None
                or evidence.video_id != command.video_id
                or evidence.availability is not EvidenceAvailability.AVAILABLE
            ):
                return False
            artifact = self._repository.get_artifact(evidence.artifact_id)
            if (
                artifact is None
                or artifact.video_id != command.video_id
                or artifact.deleted_at is not None
                or artifact.kind is not ArtifactKind.TRANSCRIPT_CANONICAL
            ):
                return False
        return True

    @staticmethod
    def _text(value: object, *, field_name: str, maximum: int = 2_000) -> str:
        if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > maximum:
            raise ValueError(f"{field_name} is invalid")
        return value

    @classmethod
    def _texts(cls, value: object, *, field_name: str) -> tuple[str, ...]:
        if not isinstance(value, list) or len(value) > 20:
            raise ValueError(f"{field_name} is invalid")
        return tuple(cls._text(item, field_name=field_name) for item in value)

    def _parse_candidate(
        self, raw: str, command: DistillationCommand
    ) -> _Candidate | _NoNewCandidate:
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("structured distillation output is malformed") from error

        if isinstance(payload, dict) and set(payload) == {"result", "evidence"}:
            if payload["result"] != "NO_NEW_INTELLIGENCE":
                raise ValueError("positive zero-result marker is invalid")
            evidence = payload["evidence"]
            if not isinstance(evidence, list) or not evidence:
                raise ValueError("no-new Intelligence evidence is missing")
            expected_evidence_ids = tuple(sorted(command.evidence_ids))
            if (
                expected_evidence_ids
                != self._repository.list_available_canonical_evidence_ids(
                    command.video_id
                )
            ):
                raise ValueError(
                    "no-new Intelligence requires the current canonical Evidence set"
                )
            cited: set[str] = set()
            for item in evidence:
                if (
                    not isinstance(item, dict)
                    or set(item) != {"evidence_id", "start_ms", "end_ms"}
                ):
                    raise ValueError("no-new Intelligence evidence schema is invalid")
                evidence_id = item["evidence_id"]
                start_ms = item["start_ms"]
                end_ms = item["end_ms"]
                if (
                    not isinstance(evidence_id, str)
                    or isinstance(start_ms, bool)
                    or isinstance(end_ms, bool)
                    or not isinstance(start_ms, int)
                    or not isinstance(end_ms, int)
                    or evidence_id in cited
                    or evidence_id not in expected_evidence_ids
                ):
                    raise ValueError("no-new Intelligence evidence reference is invalid")
                evidence_record = self._repository.get_evidence(evidence_id)
                if (
                    evidence_record is None
                    or evidence_record.video_id != command.video_id
                    or evidence_record.start_ms != start_ms
                    or evidence_record.end_ms != end_ms
                ):
                    raise ValueError("no-new Intelligence evidence binding is invalid")
                cited.add(evidence_id)
            if tuple(sorted(cited)) != expected_evidence_ids:
                raise ValueError("no-new Intelligence evidence set is incomplete")
            return _NoNewCandidate(evidence_ids=expected_evidence_ids)

        expected_keys = {
            "core_conclusion", "user_relevant_information", "important_new_information",
            "meaningful_details", "filtered_noise", "claim_kind", "evidence",
        }
        if not isinstance(payload, dict) or set(payload) != expected_keys:
            raise ValueError("structured distillation schema is invalid")
        try:
            claim_kind = IntelligenceClaimKind(payload["claim_kind"])
        except (TypeError, ValueError) as error:
            raise ValueError("distillation claim kind is invalid") from error
        if claim_kind is IntelligenceClaimKind.UNCLASSIFIED:
            raise ValueError("distillation claim kind is unclassified")
        evidence = payload["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("distillation evidence is missing")
        expected_evidence_ids = set(command.evidence_ids)
        cited_evidence_ids: set[str] = set()
        canonical_supports: dict[str, dict[str, int | str]] = {}
        evidence_stances: dict[str, EvidenceStance] = {}
        for support in evidence:
            if not isinstance(support, dict) or set(support) != {"evidence_id", "start_ms", "end_ms", "stance"}:
                raise ValueError("distillation evidence schema is invalid")
            evidence_id = support["evidence_id"]
            start_ms = support["start_ms"]
            end_ms = support["end_ms"]
            try:
                stance = EvidenceStance(support["stance"])
            except (TypeError, ValueError) as error:
                raise ValueError("distillation evidence stance is invalid") from error
            if (
                not isinstance(evidence_id, str)
                or isinstance(start_ms, bool)
                or isinstance(end_ms, bool)
                or not isinstance(start_ms, int)
                or not isinstance(end_ms, int)
                or evidence_id in cited_evidence_ids
                or evidence_id not in expected_evidence_ids
            ):
                raise ValueError("distillation evidence reference is invalid")
            evidence_record = self._repository.get_evidence(evidence_id)
            if (
                evidence_record is None
                or evidence_record.video_id != command.video_id
                or evidence_record.start_ms != start_ms
                or evidence_record.end_ms != end_ms
            ):
                raise ValueError("distillation evidence support is invalid")
            cited_evidence_ids.add(evidence_id)
            evidence_stances[evidence_id] = stance
            canonical_supports[evidence_id] = {
                "evidence_id": evidence_id,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "stance": stance.value,
            }
        if cited_evidence_ids != expected_evidence_ids:
            raise ValueError("distillation evidence support is incomplete")
        if EvidenceStance.SUPPORTING not in evidence_stances.values():
            raise ValueError("distillation requires at least one supporting Evidence")
        card = DistillationCardWrite(
            source_id=command.source_id,
            video_id=command.video_id,
            core_conclusion=self._text(payload["core_conclusion"], field_name="core conclusion", maximum=4_000),
            user_relevant_information=self._texts(payload["user_relevant_information"], field_name="user relevance"),
            important_new_information=self._texts(payload["important_new_information"], field_name="important information"),
            meaningful_details=self._texts(payload["meaningful_details"], field_name="meaningful details"),
            filtered_noise=self._texts(payload["filtered_noise"], field_name="filtered noise"),
            preference_ids=command.preference_ids,
            source_policy_revision_id=command.source_policy_revision_id,
        )
        canonical_payload = {
            **payload,
            "evidence": [
                canonical_supports[evidence_id]
                for evidence_id in sorted(cited_evidence_ids)
            ],
        }
        canonical_content = json.dumps(
            canonical_payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return _Candidate(
            claim_kind=claim_kind,
            evidence_ids=tuple(sorted(cited_evidence_ids)),
            evidence_stances=tuple(
                (evidence_id, evidence_stances[evidence_id])
                for evidence_id in sorted(cited_evidence_ids)
            ),
            card=card,
            canonical_content=canonical_content,
        )

    def distill(self, command: DistillationCommand) -> DistillationResult:
        existing = self._repository.get_distillation_execution(command.execution_id)
        if existing is not None:
            if existing.status == "PENDING":
                return self._finish(
                    command,
                    status=DistillationExecutionStatus.AMBIGUOUS,
                    budget_state="UNKNOWN",
                    outcome="PRIOR_ATTEMPT_STATE_UNKNOWN",
                    invocation_count=0,
                )
            return self._result(existing)
        if not self._eligible(command):
            self._begin(command)
            return self._finish(
                command,
                status=DistillationExecutionStatus.REJECTED_INELIGIBLE,
                budget_state="NOT_CHECKED",
                outcome="SOURCE_POLICY_INELIGIBLE",
                invocation_count=0,
            )
        if not self._legal_evidence(command):
            self._begin(command)
            return self._finish(
                command,
                status=DistillationExecutionStatus.REJECTED_EVIDENCE,
                budget_state="NOT_CHECKED",
                outcome="EVIDENCE_UNAVAILABLE_OR_FOREIGN",
                invocation_count=0,
            )
        projection = self._projection(command)
        self._begin(projection)
        decision = self._budget.check(projection)
        if not decision.allowed:
            return self._finish(
                projection,
                status=DistillationExecutionStatus.WAITING_BUDGET,
                budget_state=decision.state,
                outcome="BUDGET_BLOCKED_BEFORE_TRANSPORT",
                invocation_count=0,
            )
        if not self._transport.available:
            return self._finish(
                projection,
                status=DistillationExecutionStatus.WAITING_MODEL,
                budget_state=decision.state,
                outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT",
                invocation_count=0,
            )
        return self._dispatch_and_admit(projection, decision)
