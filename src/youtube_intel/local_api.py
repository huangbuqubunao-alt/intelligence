"""Loopback-only local API exposing safe application-service projections."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Callable
from urllib.parse import parse_qs, urlparse

from youtube_intel.brief import WeeklyBrief, WeeklyBriefService
from youtube_intel.content_summary_read import (
    AuthoritativeContentSummaryReader,
    ContentSummaryReadRejected,
)
from youtube_intel.distillation import PersonalizedDistillationService
from youtube_intel.domain import JobStatus, ProcessingStage, ScoringOutputLanguage
from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
)
from youtube_intel.orchestration import (
    AutomationTargetType,
    ProcessingPolicy,
    ScheduleFrequency,
    next_scheduled_for,
    provider_model_statuses,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.output_language import OutputLanguagePreferenceService
from youtube_intel.preference_service import PreferenceApplicationService
from youtube_intel.processing_orchestrator import DurableProcessingOrchestrator
from youtube_intel.saved_intelligence import (
    SavedIntelligenceItem,
    SavedIntelligenceService,
    SaveIntelligence,
    UnsaveIntelligence,
)
from youtube_intel.scoring import AuthoritativeScoringReader, VerifiedScoringRead
from youtube_intel.source_policy import (
    EffectiveSourcePolicy,
    SourcePolicyApplicationService,
)
from youtube_intel.source_run import SourceRunRecord
from youtube_intel.state import (
    ArtifactKind,
    AutomationRunRecord,
    AutomationScheduleRecord,
    DistillationResourceUsageRecord,
    DistillationStyle,
    FeedbackCorrectionKind,
    FeedbackKind,
    FeedbackRecord,
    FeedbackWrite,
    FilterDecisionRecord,
    IntegrityConflict,
    PolicyOverrideMode,
    PreferenceRecord,
    PreferenceScope,
    ReportRecord,
    SavedIntelligenceRecord,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    TopicAssociationKind,
    TopicMembershipRecord,
    VideoRecord,
)
from youtube_intel.topic import TopicApplicationService, TopicRead, TopicRelation


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, code: str, message: str) -> None:
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


def _timestamp(value: datetime | None) -> str | None:
    return (
        None
        if value is None
        else value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    )


def _saved_relation_dto(relation: SavedIntelligenceRecord) -> dict[str, object]:
    return {
        "intelligence_id": relation.intelligence_id,
        "saved_at": _timestamp(relation.saved_at),
    }


def _saved_item_dto(item: SavedIntelligenceItem) -> dict[str, object]:
    projection = _saved_relation_dto(item.relation)
    verified = item.verified
    if verified is None:
        projection["intelligence"] = {
            "status": "UNAVAILABLE",
            "trusted": False,
            "code": item.unavailable_code,
        }
    else:
        projection["intelligence"] = {
            "status": "AVAILABLE",
            "trusted": True,
            "intelligence_id": verified.intelligence_id,
            "revision_id": verified.revision_id,
            "claim_kind": verified.claim_kind.value,
            "state": verified.state.value,
            "evidence_ids": list(verified.evidence_ids),
            "confirmed": verified.is_confirmed,
        }
    return projection


def _source_dto(source: SourceSubscriptionRecord) -> dict[str, object]:
    return {
        "source_id": source.source_id,
        "source_type": source.source_type.value,
        "canonical_url": source.canonical_url,
        "channel_id": source.channel_id,
        "video_id": source.video_id,
        "display_name": source.display_name,
        "enabled": source.enabled,
        "processing_policy": source.processing_policy.value,
        "last_checked_at": _timestamp(source.last_checked_at),
        "last_success_at": _timestamp(source.last_success_at),
        "last_error": None
        if source.last_error_code is None
        else {"code": source.last_error_code, "message": source.last_error_message},
        "created_at": _timestamp(source.created_at),
        "updated_at": _timestamp(source.updated_at),
    }


def _source_run_dto(run: SourceRunRecord) -> dict[str, object]:
    """Expose finite durable execution facts only; no exception detail is stored."""

    return {
        "run_id": run.run_id,
        "source_id": run.source_id,
        "trigger": run.trigger.value,
        "trigger_reference": run.trigger_reference,
        "priority": run.priority.value,
        "state": run.state.value,
        "attention_reason": (
            None if run.attention_reason is None else run.attention_reason.value
        ),
        "automation_run_id": run.automation_run_id,
        "manual_command_id": run.manual_command_id,
        "manual_analyze_override_id": run.manual_analyze_override_id,
        "created_at": _timestamp(run.created_at),
        "updated_at": _timestamp(run.updated_at),
    }


def _video_dto(video: VideoRecord) -> dict[str, object]:
    # Do not expose raw scoring/analysis artifacts.  Score authority is read by
    # AuthoritativeScoringReader only and intentionally omitted until that safe
    # reader is wired to a dedicated projection service.
    return {
        "video_id": video.video_id,
        "channel_id": video.channel_id,
        "channel_name": video.channel_name,
        "title": video.title,
        "source_url": video.source_url,
        "published_at": _timestamp(video.published_at),
        "processing_status": video.pipeline_status.value,
        "scoring": {"status": "NOT_AVAILABLE"},
        "note": {"status": "UNAVAILABLE"},
        "deep_analysis": {"status": "BLOCKED", "reason": "No qualified live provider."},
        "last_updated": _timestamp(video.updated_at),
    }


def _preference_dto(preference: PreferenceRecord) -> dict[str, object]:
    return {
        "preference_id": preference.preference_id,
        "horizon": preference.horizon.value,
        "provenance": preference.provenance.value,
        "scope": preference.scope.value,
        "target_id": preference.target_id,
        "statement": preference.statement,
        "starts_at": _timestamp(preference.starts_at),
        "expires_at": _timestamp(preference.expires_at),
        "supersedes_preference_id": preference.supersedes_preference_id,
        "created_at": _timestamp(preference.created_at),
    }


def _resource_usage_dto(usage: DistillationResourceUsageRecord) -> dict[str, object]:
    """Expose bounded TASK-022 ledger facts without credentials or estimates."""

    return {
        "execution_id": usage.execution_id,
        "reason": usage.reason,
        "use_case": usage.use_case,
        "actual_provider": usage.actual_provider,
        "actual_model": usage.actual_model,
        "status": usage.status,
        "invocation_count": usage.invocation_count,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_microunits": usage.cost_microunits,
        "duration_ms": usage.duration_ms,
        "budget_state": usage.budget_state,
        "outcome": usage.outcome,
        "created_at": _timestamp(usage.created_at),
    }


def _distillation_execution_dto(execution: object | None) -> dict[str, object]:
    if execution is None:
        return {
            "status": "NOT_PROCESSED",
            "execution_id": None,
            "has_new_intelligence": None,
            "intelligence_id": None,
            "revision_id": None,
            "updated_at": None,
        }
    status = str(getattr(execution, "status"))
    return {
        "status": status,
        "execution_id": str(getattr(execution, "execution_id")),
        "has_new_intelligence": (
            True
            if status == "SUCCEEDED"
            else False
            if status == "SUCCEEDED_NO_NEW_INTELLIGENCE"
            else None
        ),
        "intelligence_id": getattr(execution, "intelligence_id"),
        "revision_id": getattr(execution, "revision_id"),
        "updated_at": _timestamp(getattr(execution, "updated_at")),
    }


def _feedback_dto(feedback: FeedbackRecord) -> dict[str, object]:
    return {
        "feedback_id": feedback.feedback_id,
        "kind": feedback.kind.value,
        "scope": feedback.scope.value,
        "target_id": feedback.target_id,
        "content": feedback.content,
        "correction_kind": None
        if feedback.correction_kind is None
        else feedback.correction_kind.value,
        "effect_status": feedback.effect_status,
        "created_at": _timestamp(feedback.created_at),
    }


def _source_policy_dto(policy: EffectiveSourcePolicy) -> dict[str, object]:
    return {
        "source_id": policy.source_id,
        "initial_history_count": policy.initial_history_count,
        "per_run_max_new_videos": policy.per_run_max_new_videos,
        "focus_rules": list(policy.focus_rules),
        "ignore_rules": list(policy.ignore_rules),
        "distillation_style": policy.distillation_style.value,
        "global_revision_id": policy.global_revision_id,
        "source_policy_revision_id": policy.source_policy_revision_id,
    }


def _filter_decision_dto(decision: FilterDecisionRecord) -> dict[str, object]:
    return {
        "decision_id": decision.decision_id,
        "source_id": decision.source_id,
        "video_id": decision.video_id,
        "stage": decision.stage.value,
        "outcome": decision.outcome.value,
        "reason": decision.reason.value,
        "global_policy_revision_id": decision.global_policy_revision_id,
        "source_policy_revision_id": decision.source_policy_revision_id,
        "manual_override_id": decision.manual_override_id,
        "prior_decision_id": decision.prior_decision_id,
        "evaluated_at": _timestamp(decision.evaluated_at),
        "execution_authorized": False,
    }


def _topic_association_dto(association: TopicMembershipRecord) -> dict[str, object]:
    return {
        "membership_id": association.membership_id,
        "topic_id": association.topic_id,
        "intelligence_id": association.intelligence_id,
        "revision_id": association.revision_id,
        "association_kind": association.association_kind.value,
        "claim_kind": association.source_claim_kind.value,
        "state": association.source_state.value,
        "evidence_ids": list(association.evidence_ids),
        "created_at": _timestamp(association.created_at),
        "effective_at": _timestamp(association.effective_at),
    }


def _topic_relation_dto(relation: TopicRelation) -> dict[str, object]:
    return {
        "topic_id": relation.topic_id,
        "related_topic_id": relation.related_topic_id,
        "relation": relation.relation.value,
        "causal": False,
        "created_at": _timestamp(relation.created_at),
    }


def _topic_dto(topic: TopicRead) -> dict[str, object]:
    return {
        "topic_id": topic.topic_id,
        "name": topic.name,
        "pinned": topic.pinned,
        "lifecycle": topic.lifecycle.value,
        "merged_into_topic_id": topic.merged_into_topic_id,
        "current_event_id": topic.current_event_id,
        "current_state": topic.current_state.value,
        "independence": topic.independence,
        "contributions": [
            {
                "membership_id": contribution.membership_id,
                "intelligence_id": contribution.intelligence_id,
                "revision_id": contribution.revision_id,
                "evidence_ids": list(contribution.evidence_ids),
                "association_kind": contribution.association_kind.value,
                "claim_kind": contribution.claim_kind.value,
                "state": contribution.state.value,
                "available": contribution.available,
            }
            for contribution in topic.contributions
        ],
        "timeline": [
            {
                "event_id": event.event_id,
                "event_kind": event.event_kind.value,
                "state": event.state.value,
                "dependency_revision_ids": list(event.dependency_revision_ids),
                "dependency_evidence_ids": list(event.dependency_evidence_ids),
                "created_at": _timestamp(event.created_at),
            }
            for event in topic.timeline
        ],
        "relations": [_topic_relation_dto(relation) for relation in topic.relations],
    }


class LocalApiApplication:
    """Framework-free route dispatcher.  Controllers validate then delegate."""

    def __init__(
        self,
        repository: SQLiteStateRepository,
        service: ProductOrchestrationService,
        *,
        scoring_reader: AuthoritativeScoringReader | None = None,
        distillation_service: PersonalizedDistillationService | None = None,
        processing_orchestrator: DurableProcessingOrchestrator | None = None,
        data_root: Path | None = None,
        vault_root: Path | None = None,
        timezone: str = "Asia/Shanghai",
        output_language_default: ScoringOutputLanguage = "zh-CN",
        now: Callable[[], datetime] | None = None,
        source_run_wakeup: Callable[[], None] | None = None,
        nvidia_distillation_available: bool | None = None,
        runtime_mode: str = "STANDARD_LOCAL",
        demo_data: bool = False,
    ) -> None:
        self._repository = repository
        self._service = service
        self._scoring_reader = scoring_reader
        self._distillation_service = distillation_service
        self._processing_orchestrator = processing_orchestrator
        self._intelligence_reader = AuthoritativeIntelligenceReader(repository)
        self._content_summary_reader = AuthoritativeContentSummaryReader(repository)
        self._data_root = None if data_root is None else data_root.resolve()
        self._vault_root = None if vault_root is None else vault_root.resolve()
        self._timezone = timezone
        self._now = now or (lambda: datetime.now(UTC))
        self._source_run_wakeup = source_run_wakeup
        self._nvidia_distillation_available = nvidia_distillation_available
        self._output_language_service = OutputLanguagePreferenceService(
            repository,
            bootstrap_default=output_language_default,
        )
        self._preference_service = PreferenceApplicationService(
            repository, now=self._now
        )
        self._source_policy_service = SourcePolicyApplicationService(
            repository, now=self._now
        )
        self._topic_service = TopicApplicationService(repository, now=self._now)
        self._saved_service = SavedIntelligenceService(repository, now=self._now)
        self._weekly_brief_service = WeeklyBriefService(
            repository, timezone=timezone, now=self._now
        )
        self._runtime_mode = runtime_mode
        self._demo_data = demo_data

    @staticmethod
    def _body(body: bytes) -> dict[str, object]:
        if len(body) > 32_768:
            raise ApiError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "PAYLOAD_TOO_LARGE",
                "Request body is too large.",
            )
        try:
            parsed: object = json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "INVALID_JSON",
                "Request must contain valid JSON.",
            ) from error
        if not isinstance(parsed, dict):
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "Request JSON must be an object.",
            )
        return parsed

    @staticmethod
    def _string(
        data: dict[str, object], key: str, *, required: bool = False
    ) -> str | None:
        value = data.get(key)
        if value is None and not required:
            return None
        if not isinstance(value, str) or not value.strip() or len(value) > 2048:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"{key} is invalid.",
            )
        return value.strip()

    @staticmethod
    def _boolean(data: dict[str, object], key: str) -> bool | None:
        value = data.get(key)
        if value is None:
            return None
        if not isinstance(value, bool):
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"{key} must be boolean.",
            )
        return value

    @staticmethod
    def _integer(
        data: dict[str, object], key: str, *, required: bool = False
    ) -> int | None:
        value = data.get(key)
        if value is None and not required:
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"{key} must be an integer.",
            )
        return value

    @staticmethod
    def _rules(
        data: dict[str, object], key: str, *, required: bool = False
    ) -> tuple[str, ...] | None:
        value = data.get(key)
        if value is None and not required:
            return None
        if not isinstance(value, list) or not all(
            isinstance(rule, str) for rule in value
        ):
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"{key} must be a list of strings.",
            )
        return tuple(value)

    @staticmethod
    def _only_keys(data: dict[str, object], allowed: set[str]) -> None:
        if set(data).difference(allowed):
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "Request contains unsupported fields.",
            )

    @staticmethod
    def _utc_timestamp(data: dict[str, object], key: str) -> datetime:
        value = LocalApiApplication._string(data, key, required=True)
        assert value is not None
        if not value.endswith("Z"):
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"{key} must be an RFC 3339 UTC timestamp.",
            )
        try:
            timestamp = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
        except ValueError as error:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"{key} must be an RFC 3339 UTC timestamp.",
            ) from error
        if timestamp.utcoffset() != UTC.utcoffset(timestamp):
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"{key} must use UTC.",
            )
        return timestamp.astimezone(UTC)

    def handle(
        self, method: str, path: str, body: bytes = b""
    ) -> tuple[int, dict[str, object]]:
        route = urlparse(path).path.rstrip("/") or "/"
        try:
            if method == "GET" and route == "/api/v1/saved-intelligence":
                return HTTPStatus.OK, self._saved_list(path)
            if method == "GET":
                return HTTPStatus.OK, self._get(route)
            data = self._body(body)
            if method == "POST" and route in {
                "/api/v1/saved-intelligence/save",
                "/api/v1/saved-intelligence/unsave",
            }:
                self._only_keys(data, {"intelligence_id"})
                intelligence_id = data.get("intelligence_id")
                if not isinstance(intelligence_id, str):
                    raise ValueError("Intelligence identity is required")
                if route.endswith("/unsave"):
                    self._saved_service.unsave(
                        UnsaveIntelligence(intelligence_id=intelligence_id)
                    )
                    return HTTPStatus.OK, {"saved": False}
                try:
                    saved = self._saved_service.save(
                        SaveIntelligence(intelligence_id=intelligence_id)
                    )
                except IntegrityConflict as error:
                    raise ApiError(
                        HTTPStatus.CONFLICT,
                        "SAVED_TARGET_CHANGED",
                        "Intelligence changed before Save; read its current state.",
                    ) from error
                return HTTPStatus.OK, {"saved": _saved_relation_dto(saved)}
            if method == "POST" and route == "/api/v1/settings/preferences/long-term":
                self._only_keys(data, {"command_id", "scope", "target_id", "statement"})
                preference = self._preference_service.set_explicit_long_term(
                    command_id=self._string(data, "command_id", required=True) or "",
                    scope=PreferenceScope(
                        self._string(data, "scope", required=True) or ""
                    ),
                    target_id=self._string(data, "target_id"),
                    statement=self._string(data, "statement", required=True) or "",
                )
                return HTTPStatus.CREATED, {"preference": _preference_dto(preference)}
            if (
                method == "POST"
                and route == "/api/v1/settings/preferences/temporary-focus"
            ):
                self._only_keys(
                    data,
                    {"command_id", "scope", "target_id", "statement", "expires_at"},
                )
                expires_at = self._utc_timestamp(data, "expires_at")
                if expires_at <= self._now():
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "VALIDATION_ERROR",
                        "expires_at must be after the backend current time.",
                    )
                preference = self._preference_service.set_temporary_focus(
                    command_id=self._string(data, "command_id", required=True) or "",
                    scope=PreferenceScope(
                        self._string(data, "scope", required=True) or ""
                    ),
                    target_id=self._string(data, "target_id"),
                    statement=self._string(data, "statement", required=True) or "",
                    expires_at=expires_at,
                )
                return HTTPStatus.CREATED, {"preference": _preference_dto(preference)}
            if method == "POST" and route == "/api/v1/settings/feedback":
                self._only_keys(
                    data,
                    {
                        "feedback_id",
                        "kind",
                        "scope",
                        "target_id",
                        "content",
                        "correction_kind",
                    },
                )
                content = data.get("content")
                if content is not None and not isinstance(content, str):
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "VALIDATION_ERROR",
                        "content is invalid.",
                    )
                correction_value = self._string(data, "correction_kind")
                feedback = self._preference_service.record_feedback(
                    FeedbackWrite(
                        feedback_id=self._string(data, "feedback_id", required=True)
                        or "",
                        kind=FeedbackKind(
                            self._string(data, "kind", required=True) or ""
                        ),
                        scope=PreferenceScope(
                            self._string(data, "scope", required=True) or ""
                        ),
                        target_id=self._string(data, "target_id"),
                        content=None if content is None else content.strip(),
                        correction_kind=None
                        if correction_value is None
                        else FeedbackCorrectionKind(correction_value),
                    )
                )
                return HTTPStatus.CREATED, {"feedback": _feedback_dto(feedback)}
            if method == "POST" and route == "/api/v1/topics":
                self._only_keys(data, {"command_id", "name"})
                topic = self._topic_service.create_topic(
                    command_id=self._string(data, "command_id", required=True) or "",
                    name=self._string(data, "name", required=True) or "",
                )
                return HTTPStatus.CREATED, {
                    "topic": _topic_dto(self._topic_service.read_topic(topic.topic_id))
                }
            topic_prefix = "/api/v1/topics/"
            if method == "PATCH" and route.startswith(topic_prefix):
                topic_id = route.removeprefix(topic_prefix)
                if not topic_id or "/" in topic_id:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(data, {"name"})
                topic = self._topic_service.rename_topic(
                    topic_id=topic_id,
                    name=self._string(data, "name", required=True) or "",
                )
                return HTTPStatus.OK, {
                    "topic": _topic_dto(self._topic_service.read_topic(topic.topic_id))
                }
            if (
                method == "POST"
                and route.startswith(topic_prefix)
                and route.endswith("/pin")
            ):
                topic_id = route.removeprefix(topic_prefix).removesuffix("/pin")
                if not topic_id or "/" in topic_id:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(data, {"pinned"})
                pinned = self._boolean(data, "pinned")
                if pinned is None:
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "VALIDATION_ERROR",
                        "pinned is required.",
                    )
                topic = self._topic_service.set_pinned(topic_id=topic_id, pinned=pinned)
                return HTTPStatus.OK, {
                    "topic": _topic_dto(self._topic_service.read_topic(topic.topic_id))
                }
            if (
                method == "POST"
                and route.startswith(topic_prefix)
                and route.endswith("/associations")
            ):
                topic_id = route.removeprefix(topic_prefix).removesuffix(
                    "/associations"
                )
                if not topic_id or "/" in topic_id:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(data, {"intelligence_id", "association_kind"})
                association = self._topic_service.associate_intelligence(
                    topic_id=topic_id,
                    intelligence_id=self._string(data, "intelligence_id", required=True)
                    or "",
                    kind=TopicAssociationKind(
                        self._string(data, "association_kind", required=True) or ""
                    ),
                )
                return HTTPStatus.CREATED, {
                    "association": _topic_association_dto(association)
                }
            if (
                method == "POST"
                and route.startswith(topic_prefix)
                and route.endswith("/relations")
            ):
                topic_id = route.removeprefix(topic_prefix).removesuffix("/relations")
                if not topic_id or "/" in topic_id:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(data, {"related_topic_id"})
                relation = self._topic_service.relate_topics(
                    topic_id,
                    self._string(data, "related_topic_id", required=True) or "",
                )
                return HTTPStatus.CREATED, {"relation": _topic_relation_dto(relation)}
            if (
                method == "POST"
                and route.startswith(topic_prefix)
                and route.endswith("/merge")
            ):
                topic_id = route.removeprefix(topic_prefix).removesuffix("/merge")
                if not topic_id or "/" in topic_id:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(data, {"source_topic_id"})
                topic = self._topic_service.merge_topics(
                    target_topic_id=topic_id,
                    source_topic_id=self._string(data, "source_topic_id", required=True)
                    or "",
                )
                return HTTPStatus.OK, {
                    "topic": _topic_dto(self._topic_service.read_topic(topic.topic_id))
                }
            if (
                method == "POST"
                and route.startswith(topic_prefix)
                and route.endswith("/split")
            ):
                topic_id = route.removeprefix(topic_prefix).removesuffix("/split")
                if not topic_id or "/" in topic_id:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(data, {"command_id", "name", "membership_ids"})
                topic = self._topic_service.split_topic(
                    source_topic_id=topic_id,
                    command_id=self._string(data, "command_id", required=True) or "",
                    name=self._string(data, "name", required=True) or "",
                    membership_ids=self._rules(data, "membership_ids", required=True)
                    or (),
                )
                return HTTPStatus.CREATED, {
                    "topic": _topic_dto(self._topic_service.read_topic(topic.topic_id))
                }
            preference_prefix = "/api/v1/settings/preferences/"
            if (
                method == "PATCH"
                and route.startswith(preference_prefix)
                and "/" not in route.removeprefix(preference_prefix)
            ):
                self._only_keys(data, {"command_id", "statement"})
                preference = self._preference_service.replace_explicit_long_term(
                    command_id=self._string(data, "command_id", required=True) or "",
                    preference_id=route.removeprefix(preference_prefix),
                    statement=self._string(data, "statement", required=True) or "",
                )
                return HTTPStatus.OK, {"preference": _preference_dto(preference)}
            if (
                method == "DELETE"
                and route.startswith(preference_prefix)
                and "/" not in route.removeprefix(preference_prefix)
            ):
                self._only_keys(data, {"command_id"})
                event = self._preference_service.delete_preference(
                    command_id=self._string(data, "command_id", required=True) or "",
                    preference_id=route.removeprefix(preference_prefix),
                )
                return HTTPStatus.OK, {
                    "state_event_id": event.state_event_id,
                    "preference_id": event.preference_id,
                    "state": event.state.value,
                    "created_at": _timestamp(event.created_at),
                }
            if method == "PUT" and route == "/api/v1/settings/output-language":
                self._only_keys(data, {"output_language"})
                try:
                    language = self._output_language_service.set(
                        output_language=self._string(
                            data, "output_language", required=True
                        )
                        or "",
                        now=self._now(),
                    )
                except ValueError as error:
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "VALIDATION_ERROR",
                        "output_language must be zh-CN or en.",
                    ) from error
                return HTTPStatus.OK, {
                    "output_language": language.value,
                    "source": language.source,
                    "updated_at": _timestamp(language.updated_at),
                }
            if method == "PUT" and route == "/api/v1/settings/source-policy":
                self._only_keys(
                    data,
                    {
                        "command_id",
                        "initial_history_count",
                        "per_run_max_new_videos",
                        "focus_rules",
                        "ignore_rules",
                        "distillation_style",
                    },
                )
                source_policy = self._source_policy_service.update_global(
                    command_id=self._string(data, "command_id", required=True) or "",
                    initial_history_count=self._integer(
                        data, "initial_history_count", required=True
                    )
                    or 0,
                    per_run_max_new_videos=self._integer(
                        data, "per_run_max_new_videos", required=True
                    )
                    or 0,
                    focus_rules=self._rules(data, "focus_rules", required=True) or (),
                    ignore_rules=self._rules(data, "ignore_rules", required=True) or (),
                    distillation_style=DistillationStyle(
                        self._string(data, "distillation_style", required=True) or ""
                    ),
                )
                return HTTPStatus.OK, {"policy": _source_policy_dto(source_policy)}
            if method == "POST" and route == "/api/v1/sources":
                processing_policy = ProcessingPolicy(
                    self._string(data, "processing_policy", required=True) or ""
                )
                source = self._service.add_source(
                    url=self._string(data, "url", required=True) or "",
                    processing_policy=processing_policy,
                )
                return HTTPStatus.CREATED, {"source": _source_dto(source)}
            source_policy_prefix = "/api/v1/sources/"
            if (
                method == "PUT"
                and route.startswith(source_policy_prefix)
                and route.endswith("/policy")
            ):
                source_id = route.removeprefix(source_policy_prefix).removesuffix(
                    "/policy"
                )
                if not source_id or "/" in source_id:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(
                    data,
                    {
                        "command_id",
                        "initial_history_count",
                        "per_run_max_new_videos",
                        "focus_mode",
                        "focus_rules",
                        "ignore_mode",
                        "ignore_rules",
                        "distillation_style_mode",
                        "distillation_style",
                    },
                )
                source_policy = self._source_policy_service.update_source(
                    source_id=source_id,
                    command_id=self._string(data, "command_id", required=True) or "",
                    initial_history_count=self._integer(data, "initial_history_count"),
                    per_run_max_new_videos=self._integer(
                        data, "per_run_max_new_videos"
                    ),
                    focus_mode=PolicyOverrideMode(
                        self._string(data, "focus_mode", required=True) or ""
                    ),
                    focus_rules=self._rules(data, "focus_rules", required=True) or (),
                    ignore_mode=PolicyOverrideMode(
                        self._string(data, "ignore_mode", required=True) or ""
                    ),
                    ignore_rules=self._rules(data, "ignore_rules", required=True) or (),
                    distillation_style_mode=PolicyOverrideMode(
                        self._string(data, "distillation_style_mode", required=True)
                        or ""
                    ),
                    distillation_style=(
                        None
                        if self._string(data, "distillation_style") is None
                        else DistillationStyle(
                            self._string(data, "distillation_style") or ""
                        )
                    ),
                )
                return HTTPStatus.OK, {"policy": _source_policy_dto(source_policy)}
            if (
                method == "POST"
                and route.startswith(source_policy_prefix)
                and route.endswith("/manual-analyze")
            ):
                remainder = route.removeprefix(source_policy_prefix).removesuffix(
                    "/manual-analyze"
                )
                parts = remainder.split("/")
                if len(parts) != 3 or parts[1] != "videos" or not all(parts):
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(data, {"command_id"})
                command_id = self._string(data, "command_id", required=True) or ""
                if self._processing_orchestrator is None:
                    decision = self._source_policy_service.manual_analyze_override(
                        source_id=parts[0], video_id=parts[2], command_id=command_id
                    )
                    return HTTPStatus.CREATED, {
                        "decision": _filter_decision_dto(decision)
                    }
                run = self._processing_orchestrator.enqueue_manual_analyze_video(
                    source_id=parts[0],
                    video_id=parts[2],
                    command_id=command_id,
                )
                assert run.manual_analyze_override_id is not None
                manual_decision = self._repository.filter_decision_for_manual_override(
                    run.manual_analyze_override_id
                )
                if manual_decision is None:
                    raise ApiError(
                        HTTPStatus.CONFLICT,
                        "CONFLICT",
                        "Manual Analyze was not durably admitted.",
                    )
                return HTTPStatus.ACCEPTED, {
                    "decision": _filter_decision_dto(manual_decision),
                    "source_run": _source_run_dto(run),
                }
            if (
                method == "POST"
                and route.startswith(source_policy_prefix)
                and route.endswith("/distill")
            ):
                remainder = route.removeprefix(source_policy_prefix).removesuffix(
                    "/distill"
                )
                parts = remainder.split("/")
                if len(parts) != 3 or parts[1] != "videos" or not all(parts):
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(data, {"execution_id", "evidence_ids"})
                if self._distillation_service is None:
                    raise ApiError(
                        HTTPStatus.CONFLICT,
                        "DISTILLATION_UNAVAILABLE",
                        "Personalized distillation requires an authorized offline transport.",
                    )
                evidence_ids = self._rules(data, "evidence_ids", required=True)
                distillation_result = self._distillation_service.distill(
                    self._distillation_service.manual_command(
                        execution_id=self._string(data, "execution_id", required=True)
                        or "",
                        source_id=parts[0],
                        video_id=parts[2],
                        evidence_ids=evidence_ids or (),
                    )
                )
                status = (
                    HTTPStatus.CREATED
                    if distillation_result.status.value == "SUCCEEDED"
                    else HTTPStatus.ACCEPTED
                )
                return status, {
                    "execution": {
                        "execution_id": distillation_result.execution_id,
                        "status": distillation_result.status.value,
                        "invocation_count": distillation_result.invocation_count,
                        "intelligence_id": distillation_result.intelligence_id,
                        "revision_id": distillation_result.revision_id,
                    }
                }
            if method == "PATCH" and route.startswith("/api/v1/sources/"):
                source_id = route.rsplit("/", 1)[1]
                self._only_keys(data, {"enabled", "processing_policy"})
                policy_value = self._string(data, "processing_policy")
                updated_source = self._service.update_source(
                    source_id,
                    enabled=self._boolean(data, "enabled"),
                    processing_policy=None
                    if policy_value is None
                    else ProcessingPolicy(policy_value),
                )
                if updated_source is None:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Source was not found."
                    )
                return HTTPStatus.OK, {"source": _source_dto(updated_source)}
            if (
                method == "POST"
                and route.endswith("/check")
                and route.startswith("/api/v1/sources/")
            ):
                source_id = route.split("/")[-2]
                self._only_keys(data, {"command_id"})
                result = self._service.check_source(
                    source_id,
                    command_id=self._string(data, "command_id"),
                )
                if result.source_run is not None:
                    if self._source_run_wakeup is not None:
                        self._source_run_wakeup()
                    return HTTPStatus.ACCEPTED, {
                        "source_run": _source_run_dto(result.source_run),
                        "message": result.safe_message,
                    }
                return HTTPStatus.OK, {
                    "status": result.status.value,
                    "message": result.safe_message,
                }
            if method == "POST" and route == "/api/v1/automation":
                target_type = AutomationTargetType(
                    self._string(data, "target_type", required=True) or ""
                )
                frequency = ScheduleFrequency(
                    self._string(data, "frequency", required=True) or ""
                )
                weekday = data.get("weekday")
                if weekday is not None and (
                    not isinstance(weekday, int) or isinstance(weekday, bool)
                ):
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "VALIDATION_ERROR",
                        "weekday is invalid.",
                    )
                schedule = self._service.save_schedule(
                    schedule_id=self._string(data, "schedule_id"),
                    target_type=target_type,
                    target_id=self._string(data, "target_id"),
                    frequency=frequency,
                    weekday=weekday,
                    local_time=self._string(data, "local_time"),
                    timezone=self._string(data, "timezone") or self._timezone,
                    enabled=self._boolean(data, "enabled") is not False,
                )
                return HTTPStatus.CREATED, {"schedule": self._schedule_dto(schedule)}
            if method == "PUT" and route == "/api/v1/settings/model-preference":
                self._only_keys(data, {"provider", "model"})
                pref = self._service.set_desired_model(
                    provider=self._string(data, "provider"),
                    model=self._string(data, "model"),
                )
                return HTTPStatus.OK, {
                    "desired_provider": pref.desired_provider,
                    "desired_model": pref.desired_model,
                    "active_production_default": None,
                    "reason": "No production-eligible Deep Analysis model is currently available.",
                }
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")
        except ApiError:
            raise
        except IntegrityConflict as error:
            raise ApiError(
                HTTPStatus.CONFLICT,
                "CONFLICT",
                "Preference or feedback command conflicts with existing history.",
            ) from error
        except (ValueError, KeyError) as error:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "Request values are invalid or unavailable.",
            ) from error

    def _saved_list(self, path: str) -> dict[str, object]:
        query = parse_qs(urlparse(path).query, keep_blank_values=True, max_num_fields=3)
        if set(query) - {"limit", "after_id", "after_saved_at"} or any(
            len(v) != 1 for v in query.values()
        ):
            raise ValueError("unsupported Saved query")
        limit = int(query.get("limit", ["100"])[0])
        after = None
        if "after_id" in query or "after_saved_at" in query:
            if "after_id" not in query or "after_saved_at" not in query:
                raise ValueError("incomplete Saved cursor")
            after = SavedIntelligenceRecord(
                query["after_id"][0],
                self._utc_timestamp(
                    {"saved_at": query["after_saved_at"][0]}, "saved_at"
                ),
            )
        page = self._saved_service.list_saved(limit=limit, after=after)
        return {
            "saved": [_saved_item_dto(item) for item in page.items],
            "next_cursor": None
            if page.next_cursor is None
            else _saved_relation_dto(page.next_cursor),
        }

    def _get(self, route: str) -> dict[str, object]:
        if route == "/api/v1/settings/source-policy":
            return {
                "policy": _source_policy_dto(
                    self._source_policy_service.global_policy()
                )
            }
        if route == "/api/v1/settings/preferences":
            return {
                "active": [
                    _preference_dto(item)
                    for item in self._preference_service.active_preferences(
                        now=self._now()
                    )
                ],
                "history": [
                    _preference_dto(item)
                    for item in self._repository.list_preferences()
                ],
            }
        if route == "/api/v1/settings/resource-usage":
            return {
                "usage": [
                    _resource_usage_dto(item)
                    for item in self._repository.list_distillation_resource_usage()
                ]
            }
        if route == "/api/v1/settings/feedback":
            return {
                "feedback": [
                    _feedback_dto(item) for item in self._repository.list_feedback()
                ]
            }
        if route == "/api/v1/topics":
            return {
                "topics": [
                    _topic_dto(self._topic_service.read_topic(topic.topic_id))
                    for topic in self._repository.list_topics()
                ]
            }
        source_run_prefix = "/api/v1/source-runs/"
        if route.startswith(source_run_prefix):
            run_id = route.removeprefix(source_run_prefix)
            if not run_id or "/" in run_id:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                )
            run = self._repository.get_source_run(run_id)
            if run is None:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Source Run was not found."
                )
            return {"source_run": _source_run_dto(run)}
        topic_prefix = "/api/v1/topics/"
        if route.startswith(topic_prefix):
            topic_id = route.removeprefix(topic_prefix)
            if not topic_id or "/" in topic_id:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                )
            return {"topic": _topic_dto(self._topic_service.read_topic(topic_id))}
        if route == "/api/v1/dashboard":
            sources = self._repository.list_source_subscriptions()
            source_runs = self._repository.list_source_runs()
            return {
                "intelligence": self._intelligence_list(limit=5),
                "pinned_topics": [
                    _topic_dto(self._topic_service.read_topic(topic.topic_id))
                    for topic in self._repository.list_topics()
                    if topic.pinned
                ],
                "weekly_v1": [
                    self._weekly_v1_dto(item)
                    for item in self._weekly_brief_service.list_finalized()[:3]
                ],
                "needs_attention": [
                    _source_run_dto(run)
                    for run in source_runs
                    if run.attention_reason is not None
                    or run.state.value == "NEEDS_ATTENTION"
                ][:10],
                "operations": {
                    "source_count": len(sources),
                    "next_scheduled_run": self._next_schedule_dto(),
                },
            }
        if route == "/api/v1/intelligence":
            return {"intelligence": self._intelligence_list(limit=100)}
        if route == "/api/v1/sources":
            return {
                "sources": [
                    self._source_projection(source)
                    for source in self._repository.list_source_subscriptions()
                ]
            }
        source_prefix = "/api/v1/sources/"
        if route.startswith(source_prefix) and route.endswith("/policy"):
            source_id = route.removeprefix(source_prefix).removesuffix("/policy")
            if not source_id or "/" in source_id:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                )
            if self._repository.get_source_subscription(source_id) is None:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Source was not found."
                )
            return {
                "policy": _source_policy_dto(
                    self._source_policy_service.effective_policy(source_id)
                )
            }
        if route.startswith(source_prefix) and route.endswith("/filter"):
            remainder = route.removeprefix(source_prefix).removesuffix("/filter")
            parts = remainder.split("/")
            if len(parts) != 3 or parts[1] != "videos" or not all(parts):
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                )
            if self._repository.get_source_subscription(parts[0]) is None:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Source was not found."
                )
            current = self._repository.current_filter_decision(parts[0], parts[2])
            return {
                "current": None if current is None else _filter_decision_dto(current),
                "history": [
                    _filter_decision_dto(item)
                    for item in self._repository.list_filter_decisions(
                        parts[0], parts[2]
                    )
                ],
            }
        if route.startswith("/api/v1/sources/"):
            source = self._repository.get_source_subscription(route.rsplit("/", 1)[1])
            if source is None:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Source was not found."
                )
            return {
                "source": self._source_projection(source),
                "policy": _source_policy_dto(
                    self._source_policy_service.effective_policy(source.source_id)
                ),
                "schedules": [
                    self._schedule_dto(item)
                    for item in self._repository.list_automation_schedules()
                    if item.target_id == source.source_id
                ],
                "recent_videos": [
                    self._source_video_dto(video, source.source_id)
                    for video in self._repository.list_source_videos(
                        source.source_id, limit=10
                    )
                ],
                "source_runs": [
                    _source_run_dto(run)
                    for run in self._repository.list_source_runs()
                    if run.source_id == source.source_id
                ][-20:],
            }
        if route == "/api/v1/videos":
            return {
                "videos": [
                    _video_dto(video) for video in self._repository.list_videos()
                ]
            }
        if route.startswith("/api/v1/videos/"):
            video = self._repository.get_video(route.rsplit("/", 1)[1])
            if video is None:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Video was not found."
                )
            return {
                "video": _video_dto(video),
                "scoring": self._scoring_projection(video.video_id),
                "transcript": self._transcript_projection(video.video_id),
                "note": self._note_projection(video.video_id),
                "intelligence_result": _distillation_execution_dto(
                    self._repository.latest_distillation_execution_for_video(
                        video.video_id
                    )
                ),
                "history": self._history_projection(video.video_id),
            }
        if route.startswith("/api/v1/intelligence/"):
            intelligence_id = route.rsplit("/", 1)[1]
            return {"intelligence": self._intelligence_projection(intelligence_id)}
        if route.startswith("/api/v1/evidence/") and route.endswith("/impact"):
            evidence_id = route.split("/")[-2]
            return {"impact": self._evidence_impact_projection(evidence_id)}
        if route == "/api/v1/weekly/v1":
            return {
                "weekly_v1": [
                    self._weekly_v1_dto(item)
                    for item in self._weekly_brief_service.list_finalized()
                ]
            }
        weekly_v1_prefix = "/api/v1/weekly/v1/"
        if route.startswith(weekly_v1_prefix):
            brief_id = route.removeprefix(weekly_v1_prefix)
            if not brief_id or "/" in brief_id:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                )
            try:
                return {
                    "weekly_v1": self._weekly_v1_dto(
                        self._weekly_brief_service.read(brief_id)
                    )
                }
            except ValueError as error:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Weekly V1 was not found."
                ) from error
        if route == "/api/v1/weekly":
            return {
                "weekly": [
                    self._report_dto(item) for item in self._repository.list_reports()
                ]
            }
        if route == "/api/v1/activity":
            return {
                "runs": [
                    self._run_dto(run)
                    for run in self._repository.list_automation_runs()
                ]
            }
        if route == "/api/v1/automation":
            return {
                "schedules": [
                    self._schedule_dto(item)
                    for item in self._repository.list_automation_schedules()
                ]
            }
        if route == "/api/v1/settings":
            preference = self._repository.get_global_model_preference()
            language = self._output_language_service.effective()
            return {
                "processing_defaults": {
                    "policy": ProcessingPolicy.STANDARD_INTELLIGENCE.value
                },
                "general": {
                    "timezone": self._timezone,
                    "output_language": language.value,
                    "output_language_source": language.source,
                    "output_language_updated_at": _timestamp(language.updated_at),
                },
                "model_preference": {
                    "desired_provider": None
                    if preference is None
                    else preference.desired_provider,
                    "desired_model": None
                    if preference is None
                    else preference.desired_model,
                    "active_production_default": None,
                },
                "providers": [
                    asdict(item)
                    for item in provider_model_statuses(
                        None if preference is None else preference.desired_provider,
                        None if preference is None else preference.desired_model,
                        nvidia_runtime_available=self._nvidia_distillation_available,
                    )
                ],
            }
        if route == "/api/v1/system":
            return {
                "release_posture": "NO-GO",
                "version": "0.1.0",
                "doctor": {"status": "NOT_RUN"},
                "backup": {"status": "NOT_RUN"},
                "credential_status": "Blocked",
                "runtime": {
                    "mode": self._runtime_mode,
                    "demo_data": self._demo_data,
                },
            }
        raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")

    def _intelligence_projection(self, intelligence_id: str) -> dict[str, object]:
        try:
            verified = self._intelligence_reader.read_current(intelligence_id)
        except IntelligenceReadRejected as error:
            return {"status": "UNAVAILABLE", "trusted": False, "code": error.code}
        projection: dict[str, object] = {
            "status": "AVAILABLE",
            "trusted": True,
            "intelligence_id": verified.intelligence_id,
            "revision_id": verified.revision_id,
            "claim_kind": verified.claim_kind.value,
            "state": verified.state.value,
            "evidence_ids": list(verified.evidence_ids),
            "confirmed": verified.is_confirmed,
        }
        try:
            card = self._intelligence_reader.read_current_card(intelligence_id)
        except IntelligenceReadRejected:
            return projection
        video = self._repository.get_video(card.video_id)
        source = self._repository.get_source_subscription(card.source_id)
        relations = {
            item.evidence_id: item
            for item in self._repository.list_intelligence_revision_evidence_relations(
                card.verified.revision_id
            )
        }
        if set(relations) != set(card.verified.evidence_ids):
            return projection
        evidence_links = []
        for evidence_id in card.verified.evidence_ids:
            evidence = self._repository.get_evidence(evidence_id)
            verified_text = self._repository.resolve_verified_evidence_text(evidence_id)
            relation = relations.get(evidence_id)
            if (
                evidence is None
                or relation is None
                or evidence.video_id != card.video_id
            ):
                return projection
            evidence_links.append(
                {
                    "evidence_id": evidence.evidence_id,
                    "artifact_id": evidence.artifact_id,
                    "start_ms": evidence.start_ms,
                    "end_ms": evidence.end_ms,
                    "language": evidence.language,
                    "lineage_kind": evidence.lineage_kind.value,
                    "role": evidence.role.value,
                    "original_excerpt": (
                        verified_text.excerpt
                        if verified_text is not None
                        else evidence.source_excerpt
                    ),
                    "translated_excerpt": None,
                    "translated_language": None,
                    "stance": None
                    if relation.stance is None
                    else relation.stance.value,
                }
            )
        source_display_name = None
        if source is not None and source.display_name:
            source_display_name = source.display_name
        elif video is not None and video.channel_name:
            source_display_name = video.channel_name
        elif source is not None:
            source_display_name = source.channel_id or source.video_id
        projection["card"] = {
            "core_conclusion": card.core_conclusion,
            "user_relevant_information": list(card.user_relevant_information),
            "important_new_information": list(card.important_new_information),
            "meaningful_details": list(card.meaningful_details),
            "filtered_noise": list(card.filtered_noise),
            "source_id": card.source_id,
            "source_display_name": source_display_name,
            "source_url": None if source is None else source.canonical_url,
            "video_id": card.video_id,
            "video_title": None if video is None else video.title,
            "original_video_url": None if video is None else video.source_url,
            "evidence_links": evidence_links,
            "preference_ids": list(card.preference_ids),
            "source_policy_revision_id": card.source_policy_revision_id,
        }
        return projection

    def _source_projection(self, source: SourceSubscriptionRecord) -> dict[str, object]:
        """Project the best persisted public Source name without network lookup."""
        projection = _source_dto(source)
        friendly_name = source.display_name
        if friendly_name is None:
            videos = self._repository.list_source_videos(source.source_id, limit=1)
            if videos and videos[0].channel_name:
                friendly_name = videos[0].channel_name
        projection["friendly_name"] = (
            friendly_name or source.channel_id or source.video_id
        )
        return projection

    def _intelligence_list(self, *, limit: int) -> list[dict[str, object]]:
        """A bounded UI projection: raw identities enumerate, TASK-019 decides trust."""
        return [
            self._intelligence_projection(intelligence_id)
            for intelligence_id in self._repository.list_current_intelligence_ids(
                limit=limit
            )
        ]

    def _evidence_impact_projection(self, evidence_id: str) -> dict[str, object]:
        try:
            impact = self._intelligence_reader.impact_for_evidence(evidence_id)
        except IntelligenceReadRejected as error:
            return {"status": "UNAVAILABLE", "code": error.code, "revisions": []}
        return {
            "status": "AVAILABLE",
            "evidence_id": impact.evidence_id,
            "revisions": [
                {
                    "intelligence_id": item.intelligence_id,
                    "revision_id": item.revision_id,
                    "is_current": item.is_current,
                }
                for item in impact.revisions
            ],
        }

    def _scoring_projection(self, video_id: str) -> dict[str, object]:
        """Project only a value already verified by AuthoritativeScoringReader."""
        if self._scoring_reader is None:
            return {
                "status": "NOT_AVAILABLE",
                "reason": "Verified scoring is unavailable in this local service configuration.",
            }
        try:
            verified: VerifiedScoringRead = self._scoring_reader.read(video_id)
        except Exception:
            job = self._repository.latest_video_job(
                video_id, target_stage=ProcessingStage.SCORING
            )
            if job is not None and job.status is JobStatus.FAILED_FINAL:
                return {
                    "status": "FAILED",
                    "reason": "Scoring did not complete with a trusted result.",
                    "code": job.last_error_code or "SCORING_FAILED",
                }
            return {
                "status": "NOT_AVAILABLE",
                "reason": "No verified scoring result is available for this video.",
            }
        outcome = verified.scoring_outcome
        result = outcome.result
        return {
            "status": "AVAILABLE",
            "score": result.score,
            "reason": result.reason,
            "topics": list(result.topics),
            "should_summarize": outcome.decision.final_should_summarize,
            "trusted": True,
            "completed_at": _timestamp(outcome.call.finished_at),
            "provenance": {
                "provider": result.provider,
                "model": result.model,
                "prompt_version": result.prompt_version,
                "success_provenance": verified.scoring_success_provenance,
            },
        }

    @staticmethod
    def _safe_artifact_text(
        root: Path | None, record: object, *, max_bytes: int
    ) -> str | None:
        """Read a hash-bound local artifact without revealing its location."""

        if root is None:
            return None
        relative_path = getattr(record, "relative_path", None)
        content_hash = getattr(record, "content_hash", None)
        if not isinstance(relative_path, str) or not isinstance(content_hash, str):
            return None
        relative = PurePosixPath(relative_path)
        if (
            not relative.parts
            or relative.is_absolute()
            or ".." in relative.parts
            or "\\" in relative_path
        ):
            return None
        path = root.joinpath(*relative.parts)
        current = path
        while current != root:
            if current.is_symlink():
                return None
            current = current.parent
        try:
            body = path.read_bytes()
        except OSError:
            return None
        if len(body) > max_bytes or hashlib.sha256(body).hexdigest() != content_hash:
            return None
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def _transcript_projection(self, video_id: str) -> dict[str, object]:
        artifact = self._repository.latest_artifact(
            video_id, ArtifactKind.TRANSCRIPT_CANONICAL
        )
        if artifact is not None:
            relative = PurePosixPath(artifact.relative_path)
            if (
                artifact.video_id != video_id
                or artifact.kind is not ArtifactKind.TRANSCRIPT_CANONICAL
                or artifact.deleted_at is not None
                or artifact.storage_root.value != "DATA"
                or relative.parts[:1] != ("transcripts",)
            ):
                text = None
            else:
                text = self._safe_artifact_text(
                    self._data_root, artifact, max_bytes=1_000_000
                )
            if text is not None:
                return {
                    "status": "AVAILABLE",
                    "text": text,
                    "created_at": _timestamp(artifact.created_at),
                    "content_length": len(text),
                }
            return {
                "status": "UNAVAILABLE",
                "code": "TRANSCRIPT_UNAVAILABLE",
                "reason": "The recorded canonical transcript cannot be safely read.",
            }
        job = self._repository.latest_video_job(
            video_id, target_stage=ProcessingStage.TRANSCRIPT
        )
        if job is not None and job.status is JobStatus.FAILED_FINAL:
            return {
                "status": "FAILED",
                "code": job.last_error_code or "TRANSCRIPT_FAILED",
                "reason": "Transcript processing ended without a canonical transcript.",
            }
        return {
            "status": "NOT_PROCESSED",
            "reason": "No canonical transcript has been recorded for this video.",
        }

    def _note_projection(self, video_id: str) -> dict[str, object]:
        """Project only the explicit current verified Summary result."""

        try:
            current = self._content_summary_reader.read_current(video_id)
        except ContentSummaryReadRejected as error:
            return {
                "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                "v2": {"status": "UNAVAILABLE", "code": error.code},
            }
        note = current.note
        summary = next(
            (
                section.entries[0].text
                for section in note.sections
                if section.kind.value == "SUMMARY" and section.entries
            ),
            None,
        )
        core_point_entries = next(
            (
                tuple(section.entries)
                for section in note.sections
                if section.kind.value == "CORE_POINTS"
            ),
            (),
        )
        core_points = [entry.text for entry in core_point_entries]
        references_by_id = {
            reference.evidence_id: reference for reference in note.evidence_references
        }
        timestamped_key_points: list[dict[str, object]] = []
        for entry in core_point_entries:
            timed = [
                references_by_id[evidence_id]
                for evidence_id in entry.evidence_ids
                if evidence_id in references_by_id
                and references_by_id[evidence_id].start_seconds is not None
            ]
            if not timed:
                continue
            start_seconds = min(
                float(reference.start_seconds) for reference in timed
                if reference.start_seconds is not None
            )
            end_seconds = max(
                float(
                    reference.end_seconds
                    if reference.end_seconds is not None
                    else reference.start_seconds
                )
                for reference in timed
                if reference.start_seconds is not None
            )
            timestamped_key_points.append(
                {
                    "text": entry.text,
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "evidence_ids": [
                        reference.evidence_id
                        for reference in sorted(
                            timed,
                            key=lambda item: (
                                float(item.start_seconds or 0),
                                item.evidence_id,
                            ),
                        )
                    ],
                }
            )
        return {
            "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
            "v2": {
                "status": "AVAILABLE",
                "note_identity": note.identity,
                "result_identity": current.result_identity,
                "language": note.language,
                "summary": summary,
                "core_points": core_points,
                "timestamped_key_points": timestamped_key_points,
                "evidence_references": [
                    {
                        "evidence_id": reference.evidence_id,
                        "source": reference.source,
                        "excerpt": reference.excerpt,
                        "start_seconds": reference.start_seconds,
                        "end_seconds": reference.end_seconds,
                    }
                    for reference in note.evidence_references
                ],
            },
        }

    def _history_projection(self, video_id: str) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        for job in self._repository.list_video_jobs(video_id, limit=100):
            events.append(
                {
                    "timestamp": _timestamp(job.created_at),
                    "type": "JOB_CREATED",
                    "status": "PENDING",
                    "summary": f"{job.target_stage.value} processing was queued.",
                    "code": None,
                    "context": {"stage": job.target_stage.value},
                }
            )
            status = (
                "AMBIGUOUS" if job.last_error_code == "AMBIGUOUS" else job.status.value
            )
            events.append(
                {
                    "timestamp": _timestamp(job.finished_at or job.updated_at),
                    "type": "JOB_STATUS",
                    "status": status,
                    "summary": (
                        "Provider may have received the request. The system will not automatically retry to avoid duplicate calls or charges."
                        if status == "AMBIGUOUS"
                        else f"{job.target_stage.value} processing is {job.status.value}."
                    ),
                    "code": job.last_error_code,
                    "context": {"stage": job.target_stage.value},
                }
            )
            for attempt in self._repository.list_job_attempts(job.job_id):
                events.append(
                    {
                        "timestamp": _timestamp(
                            attempt.finished_at or attempt.started_at
                        ),
                        "type": "ATTEMPT",
                        "status": "AMBIGUOUS"
                        if attempt.error_code == "AMBIGUOUS"
                        else (attempt.outcome.value if attempt.outcome else "RUNNING"),
                        "summary": f"Attempt {attempt.attempt_number} for {job.target_stage.value} was recorded.",
                        "code": attempt.error_code,
                        "context": {"stage": job.target_stage.value},
                    }
                )
        return sorted(events, key=lambda event: str(event["timestamp"]), reverse=True)

    def _report_dto(self, report: ReportRecord) -> dict[str, object]:
        content = self._safe_artifact_text(
            self._vault_root, report, max_bytes=1_000_000
        )
        return {
            "report_id": report.report_id,
            "iso_year": report.iso_year,
            "iso_week": report.iso_week,
            "timezone": report.timezone,
            "version": "UNKNOWN",
            "status": report.status.value,
            "created_at": _timestamp(report.created_at),
            "updated_at": _timestamp(report.updated_at),
            "content": content,
            "content_status": "AVAILABLE" if content is not None else "UNAVAILABLE",
            "weekly_v2": {"status": "UNAVAILABLE", "code": "WEEKLY_V2_UNAVAILABLE"},
            "linkage": {"status": "UNAVAILABLE_IN_CURRENT_AUTHORITY", "videos": []},
        }

    @staticmethod
    def _weekly_v1_dto(brief: WeeklyBrief) -> dict[str, object]:
        return {
            "brief_id": brief.brief_id,
            "version": brief.version,
            "logical_period_id": brief.logical_period_id,
            "timezone": brief.timezone,
            "period_start": _timestamp(brief.period_start),
            "period_end": _timestamp(brief.period_end),
            "generated_at": _timestamp(brief.generated_at),
            "finalized_at": _timestamp(brief.finalized_at),
            "status": brief.status,
            "no_important_information": brief.no_important_information,
            "preference_ids": list(brief.preference_ids),
            "items": [
                {
                    "brief_item_id": item.brief_item_id,
                    "topic_id": item.topic_id,
                    "topic_name": item.topic_name,
                    "intelligence_id": item.intelligence_id,
                    "revision_id": item.revision_id,
                    "association_kind": item.association_kind.value,
                    "claim_kind": item.claim_kind.value,
                    "source_state": item.source_state,
                    "summary": item.summary,
                    "evidence_ids": list(item.evidence_ids),
                    "markers": [
                        {
                            "marker_id": marker.marker_id,
                            "kind": marker.kind,
                            "reason": marker.reason,
                            "current_revision_id": marker.current_revision_id,
                            "evidence_id": marker.evidence_id,
                            "marked_at": _timestamp(marker.marked_at),
                        }
                        for marker in item.markers
                    ],
                }
                for item in brief.items
            ],
            "weekly_v2": {"status": "UNAVAILABLE", "code": "WEEKLY_V2_UNAVAILABLE"},
        }

    def _source_video_dto(
        self, video: VideoRecord, source_id: str
    ) -> dict[str, object]:
        decision = self._repository.current_filter_decision(source_id, video.video_id)
        return {
            "video_id": video.video_id,
            "title": video.title,
            "published_at": _timestamp(video.published_at),
            "processing_status": video.pipeline_status.value,
            "filter": None if decision is None else _filter_decision_dto(decision),
            "navigation": {"video_id": video.video_id},
        }

    def _next_schedule_dto(self) -> dict[str, object] | None:
        schedules = self._repository.list_automation_schedules()
        schedule = next(
            (
                item
                for item in schedules
                if item.enabled and item.frequency is not ScheduleFrequency.MANUAL
            ),
            None,
        )
        return None if schedule is None else self._schedule_dto(schedule)

    def _schedule_dto(self, schedule: AutomationScheduleRecord) -> dict[str, object]:
        next_run = next_scheduled_for(
            frequency=schedule.frequency,
            weekday=schedule.weekday,
            local_time=schedule.local_time,
            timezone=schedule.timezone,
            after=self._now(),
        )
        completed_runs = [
            run
            for run in self._repository.list_automation_runs(limit=100)
            if run.schedule_id == schedule.schedule_id and run.finished_at is not None
        ]
        last_run = max(
            completed_runs,
            key=lambda run: run.finished_at or run.scheduled_for,
            default=None,
        )
        return {
            "schedule_id": schedule.schedule_id,
            "target_type": schedule.target_type.value,
            "target_id": schedule.target_id,
            "frequency": schedule.frequency.value,
            "weekday": schedule.weekday,
            "local_time": schedule.local_time,
            "timezone": schedule.timezone,
            "enabled": schedule.enabled,
            "last_run": None if last_run is None else _timestamp(last_run.finished_at),
            "next_run": _timestamp(next_run),
        }

    @staticmethod
    def _run_dto(run: AutomationRunRecord) -> dict[str, object]:
        return {
            "run_id": run.run_id,
            "schedule_id": run.schedule_id,
            "target_type": run.target_type.value,
            "target_id": run.target_id,
            "scheduled_for": _timestamp(run.scheduled_for),
            "status": "AMBIGUOUS"
            if run.error_code == "AMBIGUOUS"
            else run.status.value,
            "error": None if run.error_code is None else {"code": run.error_code},
            "summary": None,
        }


_LOCAL_ORIGIN = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")


def serve_loopback(
    application: LocalApiApplication, *, port: int = 8765
) -> ThreadingHTTPServer:
    """Create, but do not start, a loopback-only server with mutation protection."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def _send(self, status: int, payload: dict[str, object]) -> None:
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy", "default-src 'self'; connect-src 'self'"
            )
            self.end_headers()
            self.wfile.write(encoded)

        def _handle(self) -> None:
            is_mutation = self.command not in {"GET", "HEAD"}
            origin = self.headers.get("Origin")
            if is_mutation and (
                self.headers.get("X-YIA-Request") != "local-ui"
                or (origin is not None and _LOCAL_ORIGIN.fullmatch(origin) is None)
            ):
                self._send(
                    HTTPStatus.FORBIDDEN,
                    {
                        "error": {
                            "code": "ORIGIN_REJECTED",
                            "message": "Unsafe local mutation request was rejected.",
                        }
                    },
                )
                return
            length = int(self.headers.get("Content-Length", "0")) if is_mutation else 0
            try:
                status, payload = application.handle(
                    self.command, self.path, self.rfile.read(length)
                )
                self._send(status, payload)
            except ApiError as error:
                self._send(
                    error.status,
                    {"error": {"code": error.code, "message": error.message}},
                )
            except Exception:
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Local service failed safely.",
                        }
                    },
                )

        do_GET = _handle
        do_POST = _handle
        do_PATCH = _handle
        do_PUT = _handle
        do_DELETE = _handle

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
