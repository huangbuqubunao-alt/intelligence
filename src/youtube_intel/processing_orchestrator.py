"""TASK-024 durable, unified Source Run orchestration.

This service owns only the top-level Source Run state machine.  It deliberately
does not implement Source policy, provider dispatch, Intelligence admission, a
resource ledger, or Topic truth.  Those remain with TASK-021, TASK-022/023B,
and TASK-023 respectively.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from youtube_intel.distillation import (
    DistillationExecutionStatus,
    PersonalizedDistillationService,
)
from youtube_intel.source_policy import (
    MetadataFilterCandidate,
    SourcePolicyApplicationService,
    VideoType,
)
from youtube_intel.source_run import (
    SourceRunAttentionReason,
    SourceRunCheckpoint,
    SourceRunChildRecord,
    SourceRunChildState,
    SourceRunPriority,
    SourceRunRecord,
    SourceRunState,
    SourceRunTrigger,
    SourceRunWrite,
)
from youtube_intel.state import (
    FilterDecisionRecord,
    FilterOutcome,
    FilterStage,
    IntegrityConflict,
    SQLiteStateRepository,
    StateStoreError,
    TopicAssociationKind,
)
from youtube_intel.topic import TopicApplicationService


class SourceRunDiscovery(Protocol):
    """Read durable, previously discovered Source memberships only.

    TASK-024 does not obtain an external discovery or YouTube authority.  An
    adapter may only return candidates already represented by persistent Source
    and Video records, which lets restart reconstruct the input without a
    process-local queue or provider call.
    """

    def discover(self, source_id: str) -> tuple[MetadataFilterCandidate, ...]: ...


@dataclass(frozen=True, slots=True)
class TopicAssociationUpdater:
    """Delegate one configured association to the trusted TASK-023 service.

    It accepts only an existing Topic identity and a finite association kind.
    The service, rather than this orchestrator, obtains the trusted current
    Intelligence read and performs deterministic membership/event dedupe.
    """

    service: TopicApplicationService
    topic_id: str
    kind: TopicAssociationKind

    def __post_init__(self) -> None:
        if (
            not isinstance(self.service, TopicApplicationService)
            or not isinstance(self.topic_id, str)
            or not self.topic_id.strip()
            or not isinstance(self.kind, TopicAssociationKind)
        ):
            raise ValueError("topic update configuration is invalid")

    def update(self, *, source_run: SourceRunRecord, intelligence_id: str) -> None:
        # ``source_run`` is intentionally not used to invent Topic truth.
        self.service.associate_intelligence(
            topic_id=self.topic_id,
            intelligence_id=intelligence_id,
            kind=self.kind,
        )


class PersistedSourceRunDiscovery:
    """Project persistent Source/Video membership into TASK-021 candidates."""

    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository

    def discover(self, source_id: str) -> tuple[MetadataFilterCandidate, ...]:
        return tuple(
            MetadataFilterCandidate(
                video_id=video.video_id,
                title=video.title or "",
                description=video.description or "",
                channel_name=video.channel_name,
                published_at=video.published_at,
                # Source/Video persistence does not own a separate presentation
                # type.  A new external metadata/discovery policy is out of scope.
                video_type=VideoType.STANDARD,
            )
            for video in self._repository.list_source_videos(source_id, limit=100)
        )


class DurableProcessingOrchestrator:
    """Normalize triggers into one persistent, restart-safe Source Run flow."""

    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        source_policy: SourcePolicyApplicationService,
        distillation: PersonalizedDistillationService,
        discovery: SourceRunDiscovery | None = None,
        topic_updater: TopicAssociationUpdater | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._source_policy = source_policy
        self._distillation = distillation
        self._discovery = discovery or PersistedSourceRunDiscovery(repository)
        if topic_updater is not None and not isinstance(
            topic_updater, TopicAssociationUpdater
        ):
            raise ValueError("topic update authority must use TASK-023 association service")
        self._topic_updater = topic_updater
        self._now = now or (lambda: datetime.now(UTC))

    def enqueue_manual_check_now(
        self,
        *,
        source_id: str,
        command_id: str,
        priority: SourceRunPriority = SourceRunPriority.P0,
    ) -> SourceRunRecord:
        return self._admit(
            SourceRunWrite.manual_check_now(
                source_id=source_id,
                command_id=command_id,
                priority=priority,
                created_at=self._now(),
            )
        )

    def enqueue_scheduled_source_run(
        self,
        *,
        source_id: str,
        automation_run_id: str,
        priority: SourceRunPriority = SourceRunPriority.P2,
    ) -> SourceRunRecord:
        return self._admit(
            SourceRunWrite.scheduled_source_run(
                source_id=source_id,
                automation_run_id=automation_run_id,
                priority=priority,
                created_at=self._now(),
            )
        )

    def enqueue_manual_analyze_video(
        self,
        *,
        source_id: str,
        video_id: str,
        command_id: str,
        priority: SourceRunPriority = SourceRunPriority.P0,
    ) -> SourceRunRecord:
        """Persist the TASK-021 relevance override, then admit the same core run."""

        override = self._source_policy.manual_analyze_override(
            source_id=source_id, video_id=video_id, command_id=command_id
        )
        if override.manual_override_id is None:
            raise StateStoreError("manual analyze override persistence is invalid")
        return self._admit(
            SourceRunWrite.manual_analyze_video(
                source_id=source_id,
                override_id=override.manual_override_id,
                command_id=command_id,
                priority=priority,
                created_at=self._now(),
            )
        )

    def _admit(self, write: SourceRunWrite) -> SourceRunRecord:
        return self._repository.create_source_run(write)

    def get_run(self, run_id: str) -> SourceRunRecord:
        run = self._repository.get_source_run(run_id)
        if run is None:
            raise ValueError("Source Run does not exist")
        return run

    def queued_runs(self, *, limit: int | None = None) -> tuple[SourceRunRecord, ...]:
        """Read the durable queue; no process-local FIFO is an authority."""

        runs = tuple(
            run
            for run in self._repository.list_source_runs()
            if run.state
            in {
                SourceRunState.QUEUED,
                SourceRunState.RUNNING,
                SourceRunState.WAITING,
                SourceRunState.PARTIAL,
            }
        )
        order = {
            SourceRunPriority.P0: 0,
            SourceRunPriority.P1: 1,
            SourceRunPriority.P2: 2,
            SourceRunPriority.P3: 3,
        }
        ordered = tuple(
            sorted(runs, key=lambda run: (order[run.priority], run.created_at, run.run_id))
        )
        if limit is None:
            return ordered
        if limit <= 0:
            raise ValueError("durable queue limit is invalid")
        return ordered[:limit]

    def resume_next(self) -> SourceRunRecord | None:
        queued = self.queued_runs(limit=1)
        return None if not queued else self.resume(queued[0].run_id)

    def resume(self, run_id: str) -> SourceRunRecord:
        """Continue exactly the next legal persisted Source Run stage.

        Re-entering this method after a restart is intentionally safe: queue,
        checkpoints, children, reservation identities, and all protected
        dispatch evidence are read from SQLite.  Calling it on any terminal
        Source Run is a no-op, never an implicit Retry.
        """

        run = self.get_run(run_id)
        if run.state in {
            SourceRunState.NEEDS_ATTENTION,
            SourceRunState.COMPLETED,
            SourceRunState.FAILED,
            SourceRunState.AMBIGUOUS,
            SourceRunState.CANCELLED,
        }:
            return run
        if run.state in {
            SourceRunState.QUEUED,
            SourceRunState.WAITING,
            SourceRunState.PARTIAL,
        }:
            run = self._repository.transition_source_run(
                run.run_id, to_state=SourceRunState.RUNNING, now=self._now()
            )
        source = self._repository.get_source_subscription(run.source_id)
        if source is None or not source.enabled:
            return self._needs_attention(
                run,
                reason=SourceRunAttentionReason.USER_DECISION_REQUIRED,
            )

        while True:
            progress = self._repository.source_run_checkpoint_progress(run.run_id)
            checkpoint = progress.next_checkpoint
            if checkpoint is None:
                return self.get_run(run.run_id)
            if checkpoint is SourceRunCheckpoint.DISCOVERY:
                self._discover_candidates(run)
                self._complete_checkpoint(run, checkpoint)
            elif checkpoint is SourceRunCheckpoint.SELECTION:
                self._selected_candidates(run)
                self._complete_checkpoint(run, checkpoint)
            elif checkpoint is SourceRunCheckpoint.FILTERING:
                attention = self._filter_selected_candidates(run)
                self._complete_checkpoint(run, checkpoint)
                if attention is not None:
                    return self._needs_attention(run, reason=attention)
            elif checkpoint is SourceRunCheckpoint.SOURCE_PREPARATION:
                attention = self._prepare_selected_children(run)
                if attention is not None:
                    return self._needs_attention(run, reason=attention)
                self._complete_checkpoint(run, checkpoint)
            elif checkpoint is SourceRunCheckpoint.DISTILLATION:
                outcome = self._continue_children(run)
                if outcome is not None:
                    return outcome
                self._complete_checkpoint(run, checkpoint)
            elif checkpoint is SourceRunCheckpoint.INTELLIGENCE_ADMISSION:
                if not self._admitted_children_are_legal(run):
                    return self._fail(run)
                self._complete_checkpoint(run, checkpoint)
            elif checkpoint is SourceRunCheckpoint.TOPIC_UPDATE:
                if not self._update_topics(run):
                    return self._partial(run)
                self._complete_checkpoint(run, checkpoint)
            elif checkpoint is SourceRunCheckpoint.FINALIZATION:
                if not self._children_are_finalizable(run):
                    return self._fail(run)
                # Source check success is only recorded after the entire legal
                # pipeline above has completed and immediately before final proof.
                self._repository.record_source_check(
                    run.source_id, now=self._now(), succeeded=True
                )
                self._complete_checkpoint(run, checkpoint)
                current = self.get_run(run.run_id)
                if current.state is SourceRunState.COMPLETED:
                    return current
                try:
                    return self._repository.transition_source_run(
                        current.run_id,
                        to_state=SourceRunState.COMPLETED,
                        now=self._now(),
                    )
                except ValueError:
                    recovered = self.get_run(run.run_id)
                    if recovered.state is SourceRunState.COMPLETED:
                        return recovered
                    raise
            else:  # pragma: no cover - enum exhaustiveness guard
                raise StateStoreError("Source Run checkpoint is invalid")

    def _discover_candidates(
        self, run: SourceRunRecord
    ) -> tuple[MetadataFilterCandidate, ...]:
        candidates = self._discovery.discover(run.source_id)
        if not isinstance(candidates, tuple):
            raise ValueError("Source Run discovery must return an immutable candidate tuple")
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.video_id in seen or not self._repository.source_has_video(
                run.source_id, candidate.video_id
            ):
                raise ValueError("Source Run discovery candidate is not persistently legal")
            seen.add(candidate.video_id)
        return candidates

    def _selected_candidates(
        self, run: SourceRunRecord
    ) -> tuple[MetadataFilterCandidate, ...]:
        if run.trigger is SourceRunTrigger.MANUAL_ANALYZE_VIDEO:
            if run.manual_analyze_override_id is None:
                raise StateStoreError("manual analyze Source Run context is invalid")
            decision = self._repository.filter_decision_for_manual_override(
                run.manual_analyze_override_id
            )
            if (
                decision is None
                or decision.source_id != run.source_id
                or decision.outcome is not FilterOutcome.RELEVANT
            ):
                raise StateStoreError("manual analyze override is not a legal relevance input")
            return (self._candidate_from_persistence(run.source_id, decision.video_id),)

        own_children = {
            child.video_id for child in self._repository.list_source_run_children(run.run_id)
        }
        prior_claims = self._prior_child_video_ids(run.source_id, excluding_run_id=run.run_id)
        available = tuple(
            candidate
            for candidate in self._discover_candidates(run)
            if candidate.video_id in own_children or candidate.video_id not in prior_claims
        )
        source = self._repository.get_source_subscription(run.source_id)
        if source is None:
            raise StateStoreError("Source Run Source disappeared")
        selection = (
            self._source_policy.select_for_initial_history(run.source_id, available)
            if source.last_success_at is None
            else self._source_policy.select_for_recurring_run(run.source_id, available)
        )
        # Overflow remains in durable Source/Video membership; it is intentionally
        # absent from the bounded child set and can be selected by a later run.
        return selection.eligible

    def _candidate_from_persistence(
        self, source_id: str, video_id: str
    ) -> MetadataFilterCandidate:
        if not self._repository.source_has_video(source_id, video_id):
            raise StateStoreError("manual Source Run video is no longer in its Source")
        video = self._repository.get_video(video_id)
        if video is None:
            raise StateStoreError("Source Run video disappeared")
        return MetadataFilterCandidate(
            video_id=video.video_id,
            title=video.title or "",
            description=video.description or "",
            channel_name=video.channel_name,
            published_at=video.published_at,
            video_type=VideoType.STANDARD,
        )

    def _prior_child_video_ids(self, source_id: str, *, excluding_run_id: str) -> set[str]:
        return {
            child.video_id
            for prior_run in self._repository.list_source_runs()
            if prior_run.source_id == source_id and prior_run.run_id != excluding_run_id
            for child in self._repository.list_source_run_children(prior_run.run_id)
        }

    @staticmethod
    def _child_by_video(
        children: tuple[SourceRunChildRecord, ...]
    ) -> dict[str, SourceRunChildRecord]:
        return {child.video_id: child for child in children}

    def _filter_selected_candidates(
        self, run: SourceRunRecord
    ) -> SourceRunAttentionReason | None:
        children = self._child_by_video(self._repository.list_source_run_children(run.run_id))
        for candidate in self._selected_candidates(run):
            child = children.get(candidate.video_id)
            if child is not None and child.state in {
                SourceRunChildState.SKIPPED,
                SourceRunChildState.COMPLETED,
                SourceRunChildState.AMBIGUOUS,
                SourceRunChildState.FAILED,
                SourceRunChildState.NEEDS_ATTENTION,
            }:
                continue
            decision = self._filter_decision_for_run(run, candidate)
            if decision.outcome is FilterOutcome.NOT_RELEVANT:
                if child is None:
                    child = self._repository.record_source_run_child(
                        run.run_id,
                        video_id=candidate.video_id,
                        state=SourceRunChildState.PENDING,
                        distillation_execution_id=None,
                        now=self._now(),
                    )
                    children[candidate.video_id] = child
                if child.state is SourceRunChildState.PENDING:
                    self._repository.transition_source_run_child(
                        run.run_id,
                        video_id=candidate.video_id,
                        to_state=SourceRunChildState.SKIPPED,
                        now=self._now(),
                    )
            elif decision.outcome is FilterOutcome.UNCERTAIN:
                if child is None:
                    child = self._repository.record_source_run_child(
                        run.run_id,
                        video_id=candidate.video_id,
                        state=SourceRunChildState.PENDING,
                        distillation_execution_id=None,
                        now=self._now(),
                    )
                    children[candidate.video_id] = child
                if child.state is SourceRunChildState.PENDING:
                    self._repository.transition_source_run_child(
                        run.run_id,
                        video_id=candidate.video_id,
                        to_state=SourceRunChildState.WAITING,
                        now=self._now(),
                    )
            elif decision.outcome is not FilterOutcome.RELEVANT:
                raise StateStoreError("filter decision is not finite")
        return None

    def _filter_decision_for_run(
        self, run: SourceRunRecord, candidate: MetadataFilterCandidate
    ) -> FilterDecisionRecord:
        if run.trigger is SourceRunTrigger.MANUAL_ANALYZE_VIDEO:
            assert run.manual_analyze_override_id is not None
            decision = self._repository.filter_decision_for_manual_override(
                run.manual_analyze_override_id
            )
            if decision is None or decision.video_id != candidate.video_id:
                raise StateStoreError("manual analyze filter context is invalid")
            return decision
        policy = self._source_policy.effective_policy(run.source_id)
        current = self._repository.current_filter_decision(run.source_id, candidate.video_id)
        if (
            current is not None
            and current.stage is FilterStage.STAGE_1
            and current.global_policy_revision_id == policy.global_revision_id
            and current.source_policy_revision_id == policy.source_policy_revision_id
        ):
            return current
        self._source_policy.evaluate_and_record_stage_one(run.source_id, candidate)
        recorded = self._repository.current_filter_decision(
            run.source_id, candidate.video_id
        )
        if recorded is None:
            raise StateStoreError("filter decision was not durably recorded")
        return recorded

    def _prepare_selected_children(
        self, run: SourceRunRecord
    ) -> SourceRunAttentionReason | None:
        children = self._child_by_video(self._repository.list_source_run_children(run.run_id))
        for candidate in self._selected_candidates(run):
            child = children.get(candidate.video_id)
            if child is not None:
                if child.state is SourceRunChildState.WAITING:
                    return SourceRunAttentionReason.MODEL_UNAVAILABLE
                if child.state in {
                    SourceRunChildState.SKIPPED,
                    SourceRunChildState.COMPLETED,
                    SourceRunChildState.AMBIGUOUS,
                    SourceRunChildState.FAILED,
                    SourceRunChildState.NEEDS_ATTENTION,
                }:
                    continue
                if child.distillation_execution_id is not None:
                    continue
                return SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED
            decision = self._repository.current_filter_decision(run.source_id, candidate.video_id)
            if decision is None or decision.outcome is not FilterOutcome.RELEVANT:
                return SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED
            evidence_ids = self._repository.list_available_canonical_evidence_ids(
                candidate.video_id
            )
            if not evidence_ids:
                return SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED
            # TASK-023B must mint the canonical execution before m012 child bind.
            reservation = self._distillation.reserve_distillation_execution(
                source_id=run.source_id,
                video_id=candidate.video_id,
                evidence_ids=evidence_ids,
            )
            child = self._repository.record_source_run_child(
                run.run_id,
                video_id=candidate.video_id,
                state=SourceRunChildState.PENDING,
                distillation_execution_id=reservation.execution_id,
                now=self._now(),
            )
            children[candidate.video_id] = child
        return None

    def _continue_children(self, run: SourceRunRecord) -> SourceRunRecord | None:
        attention: SourceRunAttentionReason | None = None
        has_failure = False
        for child in self._repository.list_source_run_children(run.run_id):
            if child.state in {SourceRunChildState.SKIPPED, SourceRunChildState.COMPLETED}:
                continue
            if child.state is SourceRunChildState.AMBIGUOUS:
                attention = SourceRunAttentionReason.AMBIGUOUS_EXTERNAL_OUTCOME
                continue
            if child.state is SourceRunChildState.WAITING:
                attention = SourceRunAttentionReason.MODEL_UNAVAILABLE
                continue
            if child.state in {
                SourceRunChildState.FAILED,
                SourceRunChildState.NEEDS_ATTENTION,
            }:
                has_failure = True
                continue
            if child.distillation_execution_id is None:
                has_failure = True
                continue
            result = self._distillation.continue_reserved_distillation(
                child.distillation_execution_id
            )
            if result.status is DistillationExecutionStatus.SUCCEEDED:
                self._transition_pending_child(
                    run,
                    video_id=child.video_id,
                    to_state=SourceRunChildState.COMPLETED,
                )
            elif result.status is DistillationExecutionStatus.AMBIGUOUS:
                self._transition_pending_child(
                    run,
                    video_id=child.video_id,
                    to_state=SourceRunChildState.AMBIGUOUS,
                )
                attention = SourceRunAttentionReason.AMBIGUOUS_EXTERNAL_OUTCOME
            elif result.status is DistillationExecutionStatus.WAITING_BUDGET:
                self._transition_pending_child(
                    run,
                    video_id=child.video_id,
                    to_state=SourceRunChildState.WAITING,
                )
                attention = SourceRunAttentionReason.BUDGET_BLOCKED
            elif result.status is DistillationExecutionStatus.WAITING_MODEL:
                self._transition_pending_child(
                    run,
                    video_id=child.video_id,
                    to_state=SourceRunChildState.WAITING,
                )
                attention = SourceRunAttentionReason.MODEL_UNAVAILABLE
            else:
                self._transition_pending_child(
                    run,
                    video_id=child.video_id,
                    to_state=SourceRunChildState.FAILED,
                )
                has_failure = True
        if attention is not None:
            return self._needs_attention(run, reason=attention)
        if has_failure:
            return self._fail(run)
        return None

    def _transition_pending_child(
        self,
        run: SourceRunRecord,
        *,
        video_id: str,
        to_state: SourceRunChildState,
    ) -> SourceRunChildRecord:
        """Apply a durable child outcome once despite duplicate worker resume.

        TASK-023B may conservatively settle a competing continuation as
        ``AMBIGUOUS`` while the original caller is still unwinding.  The later
        caller must observe that persisted result instead of attempting an
        illegal terminal-to-terminal child transition.
        """

        current = next(
            (
                child
                for child in self._repository.list_source_run_children(run.run_id)
                if child.video_id == video_id
            ),
            None,
        )
        if current is None:
            raise StateStoreError("Source Run child disappeared")
        if current.state is to_state:
            return current
        if current.state is not SourceRunChildState.PENDING:
            return current
        return self._repository.transition_source_run_child(
            run.run_id,
            video_id=video_id,
            to_state=to_state,
            now=self._now(),
        )

    def _admitted_children_are_legal(self, run: SourceRunRecord) -> bool:
        for child in self._repository.list_source_run_children(run.run_id):
            if child.state is SourceRunChildState.SKIPPED:
                continue
            if (
                child.state is not SourceRunChildState.COMPLETED
                or child.distillation_execution_id is None
            ):
                return False
            execution = self._repository.get_distillation_execution(
                child.distillation_execution_id
            )
            if (
                execution is None
                or execution.status != DistillationExecutionStatus.SUCCEEDED.value
                or execution.intelligence_id is None
                or execution.revision_id is None
            ):
                return False
        return True

    def _update_topics(self, run: SourceRunRecord) -> bool:
        if self._topic_updater is None:
            return True
        try:
            for child in self._repository.list_source_run_children(run.run_id):
                if child.state is SourceRunChildState.SKIPPED:
                    continue
                if child.distillation_execution_id is None:
                    return False
                execution = self._repository.get_distillation_execution(
                    child.distillation_execution_id
                )
                if execution is None or execution.intelligence_id is None:
                    return False
                self._topic_updater.update(
                    source_run=run, intelligence_id=execution.intelligence_id
                )
        except (StateStoreError, ValueError):
            return False
        return True

    def _children_are_finalizable(self, run: SourceRunRecord) -> bool:
        return all(
            child.state in {SourceRunChildState.COMPLETED, SourceRunChildState.SKIPPED}
            for child in self._repository.list_source_run_children(run.run_id)
        )

    def _complete_checkpoint(
        self, run: SourceRunRecord, checkpoint: SourceRunCheckpoint
    ) -> None:
        progress = self._repository.source_run_checkpoint_progress(run.run_id)
        if checkpoint in progress.completed:
            return
        try:
            self._repository.complete_source_run_checkpoint(
                run.run_id, checkpoint, now=self._now()
            )
        except IntegrityConflict:
            # A second worker may have appended the same immutable proof in the
            # interval between this read and the guarded insert.  Re-read the
            # durable event rather than treating duplicate resume as an error.
            recovered = self._repository.source_run_checkpoint_progress(run.run_id)
            if checkpoint not in recovered.completed:
                raise

    def _block_checkpoint(self, run: SourceRunRecord) -> None:
        progress = self._repository.source_run_checkpoint_progress(run.run_id)
        if progress.next_checkpoint is not None and progress.blocked_checkpoint is None:
            self._repository.block_source_run_checkpoint(
                run.run_id, progress.next_checkpoint, now=self._now()
            )

    def _needs_attention(
        self, run: SourceRunRecord, *, reason: SourceRunAttentionReason
    ) -> SourceRunRecord:
        current = self.get_run(run.run_id)
        if current.state is SourceRunState.NEEDS_ATTENTION:
            return current
        if current.state in {
            SourceRunState.COMPLETED,
            SourceRunState.FAILED,
            SourceRunState.AMBIGUOUS,
            SourceRunState.CANCELLED,
        }:
            return current
        self._block_checkpoint(current)
        return self._repository.transition_source_run(
            current.run_id,
            to_state=SourceRunState.NEEDS_ATTENTION,
            attention_reason=reason,
            now=self._now(),
        )

    def _partial(self, run: SourceRunRecord) -> SourceRunRecord:
        self._block_checkpoint(run)
        return self._repository.transition_source_run(
            run.run_id, to_state=SourceRunState.PARTIAL, now=self._now()
        )

    def _fail(self, run: SourceRunRecord) -> SourceRunRecord:
        self._block_checkpoint(run)
        return self._repository.transition_source_run(
            run.run_id, to_state=SourceRunState.FAILED, now=self._now()
        )
