"""TASK-021 explicit source policy and provider-free relevance filtering.

This module is intentionally an application seam: it persists explicit user
policy and deterministic filter decisions, but never creates work, dispatches a
provider, retries a request, or evaluates Stage 2.  TASK-024 owns legal
execution; TASK-022 owns personalized distillation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import Enum
from typing import Callable
from uuid import uuid4

from youtube_intel.state import (
    DistillationStyle,
    FilterDecisionRecord,
    FilterDecisionWrite,
    FilterOutcome,
    FilterReason,
    FilterStage,
    ManualAnalyzeOverrideWrite,
    PolicyOverrideMode,
    SourcePolicyRevisionRecord,
    SourcePolicyRevisionWrite,
    SQLiteStateRepository,
)

_EXPECTED_MISSING = object()


class VideoType(str, Enum):
    STANDARD = "STANDARD"
    SHORT = "SHORT"
    LIVE_REPLAY = "LIVE_REPLAY"


@dataclass(frozen=True, slots=True)
class MetadataFilterCandidate:
    video_id: str
    title: str
    description: str
    channel_name: str | None
    published_at: datetime | None
    video_type: VideoType


@dataclass(frozen=True, slots=True)
class EffectiveSourcePolicy:
    source_id: str | None
    initial_history_count: int
    per_run_max_new_videos: int
    focus_rules: tuple[str, ...]
    ignore_rules: tuple[str, ...]
    distillation_style: DistillationStyle
    global_revision_id: str
    source_policy_revision_id: str | None
    applied_revision_id: str | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class StageTwoFilterRequest:
    """Typed request for a later qualified Stage-2 evaluator; not executable."""

    source_id: str
    candidate: MetadataFilterCandidate
    effective_policy: EffectiveSourcePolicy
    stage_one_reason: FilterReason


@dataclass(frozen=True, slots=True)
class StageOneEvaluation:
    decision: FilterDecisionWrite
    stage_two_request: StageTwoFilterRequest | None


@dataclass(frozen=True, slots=True)
class BoundedCandidateSelection:
    limit: int
    eligible: tuple[MetadataFilterCandidate, ...]
    pending: tuple[MetadataFilterCandidate, ...]


class SourcePolicyApplicationService:
    """Validates source policy without granting any execution authority."""

    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._now = now or (lambda: datetime.now(UTC))

    @staticmethod
    def _command_id(command_id: str) -> str:
        if (
            not isinstance(command_id, str)
            or not command_id.strip()
            or command_id != command_id.strip()
            or len(command_id) > 200
        ):
            raise ValueError("source policy command identity is invalid")
        return command_id

    @staticmethod
    def _identity_digest(*parts: str) -> str:
        return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()

    @staticmethod
    def _rules(rules: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        if not isinstance(rules, (tuple, list)):
            raise ValueError("source policy rules must be a finite list")
        normalized = tuple(rules)
        SQLiteStateRepository._validate_policy_rules(
            normalized, field_name="source policy rules"
        )
        return normalized

    @staticmethod
    def _policy_from_revisions(
        global_revision: SourcePolicyRevisionRecord,
        source_revision: SourcePolicyRevisionRecord | None,
    ) -> EffectiveSourcePolicy:
        if (
            global_revision.policy_scope != "GLOBAL"
            or global_revision.initial_history_count is None
            or global_revision.per_run_max_new_videos is None
            or global_revision.distillation_style is None
        ):
            raise ValueError("global source policy is incomplete")
        if source_revision is None:
            return EffectiveSourcePolicy(
                source_id=None,
                initial_history_count=global_revision.initial_history_count,
                per_run_max_new_videos=global_revision.per_run_max_new_videos,
                focus_rules=global_revision.focus_rules,
                ignore_rules=global_revision.ignore_rules,
                distillation_style=global_revision.distillation_style,
                global_revision_id=global_revision.revision_id,
                source_policy_revision_id=None,
            )
        source_style = source_revision.distillation_style
        if (
            source_revision.distillation_style_mode is PolicyOverrideMode.OVERRIDE
            and source_style is None
        ):
            raise ValueError("source distillation style override is incomplete")
        effective_style = (
            global_revision.distillation_style
            if source_revision.distillation_style_mode is PolicyOverrideMode.INHERIT
            else source_style
        )
        if effective_style is None:
            raise ValueError("source distillation style override is incomplete")
        return EffectiveSourcePolicy(
            source_id=source_revision.source_id,
            initial_history_count=(
                global_revision.initial_history_count
                if source_revision.initial_history_count is None
                else source_revision.initial_history_count
            ),
            per_run_max_new_videos=(
                global_revision.per_run_max_new_videos
                if source_revision.per_run_max_new_videos is None
                else source_revision.per_run_max_new_videos
            ),
            focus_rules=(
                global_revision.focus_rules
                if source_revision.focus_mode is PolicyOverrideMode.INHERIT
                else source_revision.focus_rules
            ),
            ignore_rules=(
                global_revision.ignore_rules
                if source_revision.ignore_mode is PolicyOverrideMode.INHERIT
                else source_revision.ignore_rules
            ),
            distillation_style=effective_style,
            global_revision_id=global_revision.revision_id,
            source_policy_revision_id=source_revision.revision_id,
        )

    def global_policy(self) -> EffectiveSourcePolicy:
        return self._policy_from_revisions(
            self._repository.get_global_source_policy_revision(), None
        )

    def effective_policy(self, source_id: str) -> EffectiveSourcePolicy:
        return self.policy_snapshot(source_id)[0]

    def policy_snapshot(self, source_id: str) -> tuple[EffectiveSourcePolicy, SourcePolicyRevisionRecord | None]:
        if self._repository.get_source_subscription(source_id) is None:
            raise ValueError("source does not exist")
        global_revision, raw = self._repository.read_source_policy_snapshot(source_id)
        effective = self._policy_from_revisions(
            global_revision, raw,
        )
        return replace(effective, source_id=source_id), raw

    def update_global(
        self,
        *,
        command_id: str,
        initial_history_count: int,
        per_run_max_new_videos: int,
        focus_rules: tuple[str, ...] | list[str],
        ignore_rules: tuple[str, ...] | list[str],
        distillation_style: DistillationStyle,
    ) -> EffectiveSourcePolicy:
        command = self._command_id(command_id)
        if not isinstance(distillation_style, DistillationStyle):
            raise ValueError("distillation style must be a finite V1 value")
        self._repository.create_source_policy_revision(
            SourcePolicyRevisionWrite(
                revision_id=f"source-policy:global:{command}",
                policy_scope="GLOBAL",
                source_id=None,
                initial_history_count=initial_history_count,
                per_run_max_new_videos=per_run_max_new_videos,
                focus_mode=PolicyOverrideMode.OVERRIDE,
                focus_rules=self._rules(focus_rules),
                ignore_mode=PolicyOverrideMode.OVERRIDE,
                ignore_rules=self._rules(ignore_rules),
                distillation_style_mode=PolicyOverrideMode.OVERRIDE,
                distillation_style=distillation_style,
                created_at=self._now(),
            )
        )
        return self.global_policy()

    def update_source(
        self,
        *,
        source_id: str,
        command_id: str,
        initial_history_count: int | None,
        per_run_max_new_videos: int | None,
        focus_mode: PolicyOverrideMode,
        focus_rules: tuple[str, ...] | list[str],
        ignore_mode: PolicyOverrideMode,
        ignore_rules: tuple[str, ...] | list[str],
        distillation_style_mode: PolicyOverrideMode,
        distillation_style: DistillationStyle | None,
        expected_source_policy_revision_id: object = _EXPECTED_MISSING,
        _interest_only: bool = False,
    ) -> EffectiveSourcePolicy:
        command = self._command_id(command_id)
        expected_supplied = expected_source_policy_revision_id is not _EXPECTED_MISSING
        expected = expected_source_policy_revision_id if expected_supplied else None
        if expected is not None and (not isinstance(expected, str) or not expected.strip()
            or expected != expected.strip() or len(expected) > 512):
            raise ValueError("source policy expected revision identity is invalid")
        if self._repository.get_source_subscription(source_id) is None:
            raise ValueError("source does not exist")
        if not isinstance(focus_mode, PolicyOverrideMode) or not isinstance(
            ignore_mode, PolicyOverrideMode
        ) or not isinstance(distillation_style_mode, PolicyOverrideMode):
            raise ValueError("source override mode must be finite")
        if distillation_style is not None and not isinstance(
            distillation_style, DistillationStyle
        ):
            raise ValueError("distillation style must be a finite V1 value")
        focus = self._rules(focus_rules)
        ignore = self._rules(ignore_rules)
        operation = "interest" if _interest_only else "full"
        prefix = "source-policy:source-interest:v1:" + hashlib.sha256(json.dumps(
            [operation, source_id, command], ensure_ascii=False, separators=(",", ":")
        ).encode()).hexdigest() + ":"
        request: dict[str, object] = {"expected_supplied": expected_supplied, "expected": expected,
            "focus_mode": focus_mode.value, "focus_rules": focus,
            "ignore_mode": ignore_mode.value, "ignore_rules": ignore,
            "distillation_style_mode": distillation_style_mode.value,
            "distillation_style": None if distillation_style is None else distillation_style.value}
        if not _interest_only:
            request.update(initial_history_count=initial_history_count, per_run_max_new_videos=per_run_max_new_videos)
        revision_id = prefix + hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        applied = self._repository.create_source_policy_revision(
            SourcePolicyRevisionWrite(
                revision_id=revision_id,
                policy_scope="SOURCE",
                source_id=source_id,
                initial_history_count=initial_history_count,
                per_run_max_new_videos=per_run_max_new_videos,
                focus_mode=focus_mode,
                focus_rules=focus,
                ignore_mode=ignore_mode,
                ignore_rules=ignore,
                distillation_style_mode=distillation_style_mode,
                distillation_style=distillation_style,
                created_at=self._now(),
            ), command_prefix=prefix, expected_revision_id=expected,
            expected_supplied=expected_supplied, preserve_source_counts=_interest_only,
            legacy_revision_id=None if _interest_only else "source-policy:source:" + self._identity_digest(source_id, command),
        )
        return replace(self.effective_policy(source_id), applied_revision_id=applied.revision_id)

    def update_source_interests(
        self, *, source_id: str, command_id: str, expected_source_policy_revision_id: str | None,
        focus_mode: PolicyOverrideMode, focus_rules: tuple[str, ...] | list[str],
        ignore_mode: PolicyOverrideMode, ignore_rules: tuple[str, ...] | list[str],
        distillation_style_mode: PolicyOverrideMode, distillation_style: DistillationStyle | None,
    ) -> EffectiveSourcePolicy:
        return self.update_source(source_id=source_id, command_id=command_id,
            expected_source_policy_revision_id=expected_source_policy_revision_id,
            initial_history_count=None, per_run_max_new_videos=None,
            focus_mode=focus_mode, focus_rules=focus_rules, ignore_mode=ignore_mode, ignore_rules=ignore_rules,
            distillation_style_mode=distillation_style_mode, distillation_style=distillation_style,
            _interest_only=True)

    @staticmethod
    def _candidate_text(candidate: MetadataFilterCandidate) -> str:
        return " ".join(
            value.strip()
            for value in (
                candidate.title,
                candidate.description,
                candidate.channel_name or "",
            )
            if value and value.strip()
        ).casefold()

    @staticmethod
    def _has_primary_metadata(candidate: MetadataFilterCandidate) -> bool:
        """A channel label alone cannot support a confident video decision."""

        return bool(candidate.title.strip() or candidate.description.strip())

    @staticmethod
    def _validate_candidate(candidate: MetadataFilterCandidate) -> None:
        if (
            not isinstance(candidate.video_id, str)
            or not candidate.video_id.strip()
            or len(candidate.video_id) > 512
            or not isinstance(candidate.title, str)
            or not isinstance(candidate.description, str)
            or not isinstance(candidate.video_type, VideoType)
            or len(candidate.title) > 2048
            or len(candidate.description) > 16_384
        ):
            raise ValueError("metadata filter candidate is invalid")
        if candidate.published_at is not None and candidate.published_at.utcoffset() is None:
            raise ValueError("metadata filter candidate publish time must be timezone-aware")

    @staticmethod
    def _decision_id(stage: FilterStage) -> str:
        return f"filter-decision:{stage.value.lower()}:{uuid4().hex}"

    def evaluate_stage_one(
        self, source_id: str, candidate: MetadataFilterCandidate
    ) -> StageOneEvaluation:
        self._validate_candidate(candidate)
        policy = self.effective_policy(source_id)
        if candidate.video_type is VideoType.SHORT:
            outcome, reason = FilterOutcome.NOT_RELEVANT, FilterReason.SHORT_VIDEO
        else:
            searchable = self._candidate_text(candidate)
            if not self._has_primary_metadata(candidate):
                outcome, reason = (
                    FilterOutcome.UNCERTAIN,
                    FilterReason.INSUFFICIENT_METADATA,
                )
            elif any(rule.casefold() in searchable for rule in policy.ignore_rules):
                outcome, reason = (
                    FilterOutcome.NOT_RELEVANT,
                    FilterReason.IGNORE_RULE_MATCH,
                )
            elif not policy.focus_rules:
                outcome, reason = FilterOutcome.UNCERTAIN, FilterReason.NO_FOCUS_RULES
            elif any(rule.casefold() in searchable for rule in policy.focus_rules):
                outcome, reason = FilterOutcome.RELEVANT, FilterReason.FOCUS_MATCH
            else:
                outcome, reason = FilterOutcome.NOT_RELEVANT, FilterReason.NO_FOCUS_MATCH
        decision = FilterDecisionWrite(
            decision_id=self._decision_id(FilterStage.STAGE_1),
            source_id=source_id,
            video_id=candidate.video_id,
            stage=FilterStage.STAGE_1,
            outcome=outcome,
            reason=reason,
            global_policy_revision_id=policy.global_revision_id,
            source_policy_revision_id=policy.source_policy_revision_id,
            manual_override_id=None,
            prior_decision_id=None,
            evaluated_at=self._now(),
        )
        return StageOneEvaluation(
            decision=decision,
            stage_two_request=(
                None
                if outcome is not FilterOutcome.UNCERTAIN
                else StageTwoFilterRequest(
                    source_id=source_id,
                    candidate=candidate,
                    effective_policy=policy,
                    stage_one_reason=reason,
                )
            ),
        )

    def evaluate_and_record_stage_one(
        self, source_id: str, candidate: MetadataFilterCandidate
    ) -> StageOneEvaluation:
        evaluated = self.evaluate_stage_one(source_id, candidate)
        saved = self._repository.append_filter_decision(evaluated.decision)
        return StageOneEvaluation(
            decision=FilterDecisionWrite(
                decision_id=saved.decision_id,
                source_id=saved.source_id,
                video_id=saved.video_id,
                stage=saved.stage,
                outcome=saved.outcome,
                reason=saved.reason,
                global_policy_revision_id=saved.global_policy_revision_id,
                source_policy_revision_id=saved.source_policy_revision_id,
                manual_override_id=saved.manual_override_id,
                prior_decision_id=saved.prior_decision_id,
                evaluated_at=saved.evaluated_at,
            ),
            stage_two_request=evaluated.stage_two_request,
        )

    def manual_analyze_override(
        self, *, source_id: str, video_id: str, command_id: str
    ) -> FilterDecisionRecord:
        """Persist relevance-only intent; this method cannot create or retry work."""

        command = self._command_id(command_id)
        identity = self._identity_digest(source_id, video_id, command)
        override_id = f"manual-analyze:{identity}"
        existing = self._repository.filter_decision_for_manual_override(override_id)
        if existing is not None:
            return existing
        prior = self._repository.current_filter_decision(source_id, video_id)
        if prior is None or prior.outcome is not FilterOutcome.NOT_RELEVANT:
            raise ValueError("manual analyze requires a currently skipped video")
        policy = self.effective_policy(source_id)
        return self._repository.record_manual_analyze_override(
            ManualAnalyzeOverrideWrite(
                override_id=override_id,
                source_id=source_id,
                video_id=video_id,
                command_id=command,
                prior_decision_id=prior.decision_id,
                created_at=self._now(),
            ),
            FilterDecisionWrite(
                decision_id=f"filter-decision:manual:{identity}",
                source_id=source_id,
                video_id=video_id,
                stage=FilterStage.MANUAL_OVERRIDE,
                outcome=FilterOutcome.RELEVANT,
                reason=FilterReason.MANUAL_ANALYZE,
                global_policy_revision_id=policy.global_revision_id,
                source_policy_revision_id=policy.source_policy_revision_id,
                manual_override_id=override_id,
                prior_decision_id=prior.decision_id,
                evaluated_at=self._now(),
            ),
        )

    @staticmethod
    def _bounded_selection(
        candidates: tuple[MetadataFilterCandidate, ...], *, limit: int
    ) -> BoundedCandidateSelection:
        ordered = tuple(
            sorted(
                candidates,
                key=lambda candidate: (
                    -(
                        candidate.published_at.astimezone(UTC).timestamp()
                        if candidate.published_at is not None
                        else float("-inf")
                    ),
                    candidate.video_id,
                ),
            )
        )
        return BoundedCandidateSelection(
            limit=limit,
            eligible=ordered[:limit],
            pending=ordered[limit:],
        )

    def select_for_recurring_run(
        self, source_id: str, candidates: tuple[MetadataFilterCandidate, ...]
    ) -> BoundedCandidateSelection:
        policy = self.effective_policy(source_id)
        for candidate in candidates:
            self._validate_candidate(candidate)
        return self._bounded_selection(
            candidates, limit=policy.per_run_max_new_videos
        )

    def select_for_initial_history(
        self, source_id: str, candidates: tuple[MetadataFilterCandidate, ...]
    ) -> BoundedCandidateSelection:
        policy = self.effective_policy(source_id)
        for candidate in candidates:
            self._validate_candidate(candidate)
        return self._bounded_selection(candidates, limit=policy.initial_history_count)
