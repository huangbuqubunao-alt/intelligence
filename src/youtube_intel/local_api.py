"""Loopback-only local API exposing safe application-service projections."""

from __future__ import annotations

import hashlib
import json
import os
import re
import select
import socket
import sqlite3
import threading
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Callable, Final, cast
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from youtube_intel.backup_restore import (
    MAX_ARCHIVE_BYTES,
    BackupRestoreError,
    BackupRestoreService,
)
from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.brief import WeeklyBrief, WeeklyBriefService
from youtube_intel.cloud_spending_policy import (
    CloudSpendingPolicy,
    SpendingPolicyRejected,
)
from youtube_intel.content_summary_read import (
    AuthoritativeContentSummaryReader,
    ContentSummaryReadRejected,
)
from youtube_intel.deep_analysis_obsidian import (
    DeepAnalysisObsidianPublisher,
    DeepAnalysisPublishError,
)
from youtube_intel.deep_analysis_service import (
    DeepAnalysisRejected,
    DeepAnalysisService,
)
from youtube_intel.distillation import PersonalizedDistillationService
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisOutcome,
    JobStatus,
    PipelineStatus,
    ProcessingStage,
    ScoringOutputLanguage,
)
from youtube_intel.evidence_translation import (
    EvidenceTranslationPresentationService,
    source_matches_target,
)
from youtube_intel.extractive_summary import PROVIDER as EXTRACTIVE_PROVIDER
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.following_provider import TrackingError
from youtube_intel.following_tracking import FollowingTrackingService, is_tracked
from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
)
from youtube_intel.knowledge_delta import KnowledgeDeltaService
from youtube_intel.local_content import LocalContentProvider, LocalImportError
from youtube_intel.local_intelligence_settings import (
    LocalIntelligenceSettings,
    SettingsRejected,
)
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.model_settings import (
    BigModelCredentialSettings,
    CredentialStoreError,
    ModelSettingsService,
)
from youtube_intel.native_import import NativeImportService, macos_pick
from youtube_intel.offline_transcription import OfflineError
from youtube_intel.orchestration import (
    AutomationTargetType,
    ProcessingPolicy,
    ScheduleFrequency,
    SourceType,
    next_scheduled_for,
    provider_model_statuses,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.output_language import OutputLanguagePreferenceService
from youtube_intel.preference_service import PreferenceApplicationService
from youtube_intel.processing_orchestrator import DurableProcessingOrchestrator
from youtube_intel.providers.bilibili import (
    CREATOR_FOLLOWING_AVAILABLE,
    CREATOR_FOLLOWING_CODE,
    BilibiliAdapter,
    BilibiliError,
)
from youtube_intel.research_contract import ResearchRequest
from youtube_intel.research_lite import ResearchLiteService, ResearchRejected
from youtube_intel.saved_intelligence import (
    SavedIntelligenceItem,
    SavedIntelligenceService,
    SaveIntelligence,
    UnsaveIntelligence,
)
from youtube_intel.scoring import AuthoritativeScoringReader, VerifiedScoringRead
from youtube_intel.source_authority import (
    IO_CHUNK_BYTES,
    MAX_MEDIA_BYTES,
    MAX_TEXT_BYTES,
    open_managed,
    safe_filename,
    verify_source,
)
from youtube_intel.source_policy import (
    _EXPECTED_MISSING,
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
    FilterOutcome,
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
from youtube_intel.summary_evidence_authority import (
    LegacySummaryNotCurrentAuthority,
)
from youtube_intel.topic import TopicApplicationService, TopicRead, TopicRelation
from youtube_intel.tracked_content_retry import TrackedContentRetryService
from youtube_intel.tracked_retry_context import RetryConflict, RetryIntegrity

# One shared BilibiliError -> HTTP status map for every Bilibili entry point, so
# the same provider failure is never reported as 422 here and 429 there.  The
# codes are the truthful category of what the provider actually said; a genuine
# user-input problem still stays 422.
_BILIBILI_ERROR_STATUS = {
    "RATE_LIMITED": HTTPStatus.TOO_MANY_REQUESTS,
    "RISK_CONTROLLED": HTTPStatus.TOO_MANY_REQUESTS,
    "ACCESS_DENIED": HTTPStatus.FORBIDDEN,
    "NOT_FOUND": HTTPStatus.NOT_FOUND,
    "VIDEO_UNAVAILABLE": HTTPStatus.NOT_FOUND,
    "NETWORK_UNAVAILABLE": HTTPStatus.SERVICE_UNAVAILABLE,
    "METADATA_FAILED": HTTPStatus.BAD_GATEWAY,
    "RESPONSE_TOO_LARGE": HTTPStatus.BAD_GATEWAY,
    "SOURCE_UNTRUSTED": HTTPStatus.CONFLICT,
    "CAPTION_UNAVAILABLE": HTTPStatus.BAD_GATEWAY,
    "CAPTION_INVALID": HTTPStatus.BAD_GATEWAY,
    "DURATION_UNSUPPORTED": HTTPStatus.UNPROCESSABLE_ENTITY,
    "UNSUPPORTED_URL": HTTPStatus.UNPROCESSABLE_ENTITY,
    "INVALID_INPUT": HTTPStatus.UNPROCESSABLE_ENTITY,
}
CREATOR_FOLLOWING_UNAVAILABLE_MESSAGE = (
    "Continuous Bilibili creator tracking is currently unavailable. "
    "You can still add public Bilibili videos."
)
# Truthful, code-based capability projection for the user interface.  Structured
# codes let the Chinese UI localize without translating backend prose.
_BILIBILI_CAPABILITY: dict[str, object] = {
    "provider": "BILIBILI",
    "video_ingestion": {
        "available": True,
        "code": "PUBLIC_VIDEO_INGESTION_AVAILABLE",
    },
    "creator_following": {
        "available": CREATOR_FOLLOWING_AVAILABLE,
        "code": "CREATOR_FOLLOWING_AVAILABLE"
        if CREATOR_FOLLOWING_AVAILABLE
        else CREATOR_FOLLOWING_CODE,
        "endpoint": "/x/space/arc/search",
        "message": None
        if CREATOR_FOLLOWING_AVAILABLE
        else CREATOR_FOLLOWING_UNAVAILABLE_MESSAGE,
    },
    "public_captions": {
        # Truthful current state, not a removal of the caption path.  Every
        # bounded compliant sample so far returned zero public captions, so this
        # must not claim the capability.  A trusted public caption still yields
        # transcript -> Summary -> Evidence; without one the Content stays
        # metadata-only and nothing is fabricated.
        "available": False,
        "code": "PUBLIC_CAPTIONS_NOT_OBSERVED",
        "note": "No trusted public Bilibili caption has been observed on the "
        "compliant no-login path, so this capability is not claimed. Metadata "
        "import is unaffected; without a trusted caption there is no transcript, "
        "Summary or Evidence.",
    },
}


class ApiError(Exception):
    def __init__(
        self,
        status: HTTPStatus,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        self.status, self.code, self.message = status, code, message
        # Optional machine-readable context (e.g. a stable reason_code) so the
        # user interface can localize without parsing English prose.
        self.details = details
        super().__init__(message)


#: Error-detail keys safe to expose over the local HTTP boundary.
#:
#: Only stable, non-secret machine fields are allowed. Stack traces, file
#: paths, credentials, and free-form internal diagnostics are never serialized.
_PUBLIC_ERROR_DETAIL_KEYS: Final = frozenset(
    {"reason_code", "availability", "consent_required"}
)


def _error_body(error: ApiError) -> dict[str, object]:
    """Serialize an :class:`ApiError` for the real local HTTP boundary.

    The machine ``code`` is always present. Safe machine-readable ``details``
    are preserved so the user interface can localize by code instead of parsing
    English prose. Anything outside the allowlist is dropped rather than
    forwarded.
    """

    body: dict[str, object] = {
        "error": {"code": error.code, "message": error.message}
    }
    details = error.details
    if isinstance(details, Mapping):
        safe = {
            key: value
            for key, value in details.items()
            if key in _PUBLIC_ERROR_DETAIL_KEYS
            and isinstance(value, (str, bool, int, float, type(None)))
        }
        if safe:
            body["error"]["details"] = safe  # type: ignore[index]
    return body


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
        "provider": source.provider,
        "source_type": source.source_type.value,
        "canonical_url": source.canonical_url,
        "channel_id": source.channel_id,
        "video_id": source.video_id,
        "display_name": source.display_name,
        "enabled": source.enabled,
        "processing_policy": source.processing_policy.value,
        "processing_mode": source.processing_policy.product_mode,
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


def _video_dto(
    video: VideoRecord,
    *,
    deep_analysis_status: str = "NOT_QUALIFIED",
    deep_analysis_reason: str | None = None,
) -> dict[str, object]:
    # Do not expose raw scoring/analysis artifacts.  Score authority is read by
    # AuthoritativeScoringReader only and intentionally omitted until that safe
    # reader is wired to a dedicated projection service.
    return {
        "video_id": video.video_id,
        "provider": video.provider,
        "channel_id": video.channel_id if video.provider == "YOUTUBE" else None,
        "channel_name": video.channel_name,
        "title": video.title,
        "source_url": video.source_url,
        "published_at": _timestamp(video.published_at),
        "processing_status": video.pipeline_status.value,
        "scoring": {"status": "NOT_AVAILABLE"},
        "note": {"status": "UNAVAILABLE"},
        "deep_analysis": {
            "status": deep_analysis_status,
            "reason": deep_analysis_reason,
        },
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
        "selected_provider": getattr(execution, "selected_provider", None),
        "output_language": getattr(execution, "output_language"),
        "has_new_intelligence": (
            True
            if status == "SUCCEEDED"
            else False
            if status in {"SUCCEEDED_NO_NEW_INTELLIGENCE", "CANCELLED"}
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
        cloud_distillation_service: PersonalizedDistillationService | None = None,
        cloud_synthesis_service: PersonalizedDistillationService | None = None,
        cloud_spending_policy: CloudSpendingPolicy | None = None,
        cloud_synthesis_qualified: bool = False,
        cloud_intelligence_qualified: bool = False,
        cloud_execution_enabled: bool = True,
        cloud_credential_available: bool = False,
        model_settings: ModelSettingsService | None = None,
        bigmodel_settings: BigModelCredentialSettings | None = None,
        refresh_cloud_distillation: Callable[[], PersonalizedDistillationService] | None = None,
        refresh_cloud_synthesis: Callable[[], PersonalizedDistillationService] | None = None,
        processing_orchestrator: DurableProcessingOrchestrator | None = None,
        data_root: Path | None = None,
        vault_root: Path | None = None,
        timezone: str = "Asia/Shanghai",
        output_language_default: ScoringOutputLanguage = "zh-CN",
        now: Callable[[], datetime] | None = None,
        source_run_wakeup: Callable[[], None] | None = None,
        tracked_content_retry: TrackedContentRetryService | None = None,
        local_distillation_available: bool | None = None,
        analysis_reader: Callable[[str, str], AnalysisOutcome] | None = None,
        evidence_translation_service: EvidenceTranslationPresentationService | None = None,
        runtime_mode: str = "STANDARD_LOCAL",
        demo_data: bool = False,
        backup_restore_service: BackupRestoreService | None = None,
        deep_analysis_service: DeepAnalysisService | None = None,
        deep_analysis_publisher: DeepAnalysisObsidianPublisher | None = None,
        transcription_jobs: LocalTranscriptionJobs | None = None,
        bilibili_adapter: BilibiliAdapter | None = None,
        source_tracking: FollowingTrackingService | None = None,
        runtime_model: str | None = None,
        runtime_model_digest: str | None = None,
        local_distillation_capabilities: Callable[[], tuple[dict[str, object], ...]] | None = None,
        local_intelligence_settings: LocalIntelligenceSettings | None = None,
    ) -> None:
        self._repository = repository
        self._service = service
        self._scoring_reader = scoring_reader
        self._distillation_service = distillation_service
        self._deep_analysis_service = deep_analysis_service
        self._deep_analysis_publisher = deep_analysis_publisher or DeepAnalysisObsidianPublisher(
            repository, vault_root=vault_root
        )
        self._cloud_distillation_service = cloud_distillation_service
        self._cloud_synthesis_service = cloud_synthesis_service
        self._cloud_spending_policy = cloud_spending_policy
        self._cloud_synthesis_qualified = cloud_synthesis_qualified
        self._refresh_cloud_synthesis = refresh_cloud_synthesis
        self._cloud_intelligence_qualified = cloud_intelligence_qualified
        # Trusted composition restriction; never writable by a request body.
        self._cloud_execution_enabled = cloud_execution_enabled
        self._cloud_credential_available = cloud_credential_available
        self._model_settings = model_settings
        self._bigmodel_settings = bigmodel_settings
        self._local_intelligence_settings = local_intelligence_settings
        self._runtime_model = runtime_model
        self._runtime_model_digest = runtime_model_digest
        self._local_distillation_capabilities = local_distillation_capabilities
        self._refresh_cloud_distillation = refresh_cloud_distillation
        self._processing_orchestrator = processing_orchestrator
        self._intelligence_reader = AuthoritativeIntelligenceReader(repository)
        self._content_summary_reader = AuthoritativeContentSummaryReader(repository)
        self._data_root = None if data_root is None else data_root.resolve()
        if self._data_root is not None:
            repository.bind_source_storage(self._data_root)
        self._transcription_jobs = transcription_jobs
        self._transcription_init_lock = threading.Lock()
        self._local_import_slot = threading.BoundedSemaphore(1)
        self._local_provider = None if self._data_root is None else LocalContentProvider(repository, self._data_root, now=now)
        self._bilibili_provider = None if self._data_root is None else BilibiliContentProvider(repository, self._data_root, adapter=bilibili_adapter, now=now)
        self._source_tracking = source_tracking or (None if self._bilibili_provider is None else FollowingTrackingService(repository, self._bilibili_provider, now=now))
        if self._source_tracking is not None:
            service.bind_source_tracking(self._source_tracking)
        self._bilibili_import_slot = threading.BoundedSemaphore(1)
        self._vault_root = None if vault_root is None else vault_root.resolve()
        self._timezone = timezone
        self._now = now or (lambda: datetime.now(UTC))
        self._knowledge_delta_service = KnowledgeDeltaService(
            repository, now=self._now, timezone=timezone
        )
        self._research_service = ResearchLiteService(repository, now=self._now)
        self._tracked_content_retry = tracked_content_retry
        self._source_run_wakeup = source_run_wakeup
        self._local_distillation_available = local_distillation_available
        self._analysis_reader = analysis_reader
        self._evidence_translation_service = evidence_translation_service
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
        self._backup_restore_service = backup_restore_service
        self._native_import: NativeImportService | None = None

    def enable_native_import(self, origins: tuple[str, ...], *, picker_executable: Path) -> None:
        for origin in origins:
            parsed = urlparse(origin)
            if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port or parsed.netloc != f"{parsed.hostname}:{parsed.port}" or parsed.path or parsed.query or parsed.fragment:
                raise ValueError("Native import requires an exact local application origin")
        if self._local_provider is None or not origins:
            raise ValueError("Native import needs local source storage")
        def process_saved(content_id: str) -> None:
            jobs = self._require_transcription()
            capability = jobs.capability()
            deadline = time.monotonic() + 30
            while capability.get("checking") is True and time.monotonic() < deadline:
                time.sleep(0.1)  # background admission thread; Content is already visible
                capability = jobs.capability()
            # Existing provisioned offline adapter only; no model download/cloud.
            if capability.get("state") == "READY" and capability.get("production_eligible") is True:
                identity = capability.get("execution_identity")
                if isinstance(identity, str):
                    jobs.start(content_id, identity)
        self._native_import = NativeImportService(self._local_provider,
            origins=origins, backup=self._backup_restore_service, process_saved=process_saved,
            picker=partial(macos_pick, executable=picker_executable))

    def shutdown_native_import(self) -> None:
        if self._native_import:
            self._native_import.shutdown()

    def native_request(self, method: str, route: str, body: bytes, origin: str) -> tuple[int, dict[str, object]]:
        with self._configuration_admission(route):
            return self._native_request(method, route, body, origin)

    def _native_request(self, method: str, route: str, body: bytes, origin: str) -> tuple[int, dict[str, object]]:
        service = self._native_import
        if service is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "LOCAL_NATIVE_PICKER_UNAVAILABLE", "Native local selection is unavailable.")
        if method != "POST":
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Native route is unavailable.")
        self._only_keys(self._body(body), set())  # no paths, filenames or caller scripts
        try:
            if route == "/api/v1/local/native/picks":
                return HTTPStatus.ACCEPTED, {"job": service.choose(origin)}
            if route == "/api/v1/local/native/jobs":
                return HTTPStatus.OK, {"jobs": service.jobs(origin)}
            match = re.fullmatch(r"/api/v1/local/native/picks/([A-Za-z0-9_-]{43})(?:/(confirm|cancel))?", route)
            if match:
                key, action = match.groups()
                result = service.confirm(key, origin) if action == "confirm" else service.cancel(key, origin) if action == "cancel" else service.status(key, origin)
                return HTTPStatus.ACCEPTED if action else HTTPStatus.OK, {"job": result}
        except LocalImportError as error:
            raise ApiError(HTTPStatus.CONFLICT, error.code, "The native local import could not proceed.") from None
        raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Native route is unavailable.")

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
    def _retry_string(data: dict[str, object], key: str) -> str:
        value=data.get(key)
        if type(value) is not str or not value.strip() or len(value)>512:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY,'VALIDATION_ERROR','Content retry command input is invalid.')
        return value

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

    @contextmanager
    def _configuration_admission(self, route: str) -> Iterator[None]:
        settings = self._local_intelligence_settings
        if settings is None or route.startswith("/api/v1/backup-restore/"):
            # Backup control methods recheck the same guard under their EX lock.
            yield
            return
        maintenance = route.endswith("/intelligence/cancel")
        with settings.admission(maintenance=maintenance) as allowed:
            if not allowed:
                raise ApiError(HTTPStatus.CONFLICT, "CONFIGURATION_APPLYING",
                    "Local model settings are applying. Wait for the local service to reconnect.")
            if maintenance or self._backup_restore_service is None:
                yield
                return
            with self._backup_restore_service.background_work() as admitted:
                if not admitted:
                    raise ApiError(HTTPStatus.CONFLICT, "CONFIGURATION_APPLYING",
                        "Protected local work prevents this request. Try again after it settles.")
                yield

    def handle(self, method: str, path: str, body: bytes = b"") -> tuple[int, dict[str, object]]:
        route = urlparse(path).path.rstrip("/")
        if route == "/api/v1/settings/local-intelligence":
            settings = self._local_intelligence_settings
            if settings is None:
                raise ApiError(HTTPStatus.CONFLICT, "SETTINGS_UNAVAILABLE", "Local Intelligence settings are unavailable.")
            if method == "GET":
                return HTTPStatus.OK, {"local_intelligence": settings.status()}
            if method == "PUT":
                data = self._body(body)
                self._only_keys(data, {"candidate_id", "expected_etag"})
                candidate = self._string(data, "candidate_id", required=True) or ""
                token = self._string(data, "expected_etag", required=True) or ""
                try:
                    result = settings.apply(candidate, token)
                except SettingsRejected as error:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY if error.code == "MODEL_CANDIDATE_INVALID"
                        else HTTPStatus.CONFLICT, error.code,
                        "Local Intelligence settings could not apply. Keep this selection and check model identity or unfinished tasks.",
                        details={"reason_code": error.reason}) from error
                restarting = result["restart_required"] is True
                return (HTTPStatus.ACCEPTED if restarting else HTTPStatus.OK), {
                    "local_intelligence": result, "runtime_restart_required": restarting}
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")
        if method in {"GET", "HEAD"}:
            return self._handle(method, path, body)
        with self._configuration_admission(route):
            return self._handle(method, path, body)

    def _handle(
        self, method: str, path: str, body: bytes = b""
    ) -> tuple[int, dict[str, object]]:
        route = urlparse(path).path.rstrip("/") or "/"
        try:
            if method == "GET" and route == "/api/v1/local/native/capability":
                return HTTPStatus.OK, {"capability": {"available": self._native_import is not None}}
            creator_from_content = re.fullmatch(r"/api/v1/videos/([^/]+)/follow-(creator|channel)", route)
            following_provider = "YOUTUBE" if route == "/api/v1/sources/channels" or (creator_from_content and creator_from_content[2] == "channel") else "BILIBILI"
            if method == "POST" and (route in {"/api/v1/sources/creators", "/api/v1/sources/channels"} or creator_from_content):
                if self._source_tracking is None:
                    raise ApiError(HTTPStatus.CONFLICT, "TRACKING_UNAVAILABLE", "Source storage is unavailable.")
                data = self._body(body)
                self._only_keys(data, set() if creator_from_content else {"input", "processing_mode"})
                mode = ProcessingPolicy.from_product_mode(self._string(data, "processing_mode") or "ORGANIZE_CONTENT")
                if following_provider == "BILIBILI" and not CREATOR_FOLLOWING_AVAILABLE:
                    # The capability is withdrawn, so no provider request is made,
                    # no source row is created, and nothing is silently scheduled.
                    raise ApiError(
                        HTTPStatus.CONFLICT,
                        "BILIBILI_" + CREATOR_FOLLOWING_CODE,
                        CREATOR_FOLLOWING_UNAVAILABLE_MESSAGE,
                    )
                try:
                    source = self._source_tracking.follow_content(creator_from_content[1], provider=following_provider) if creator_from_content else self._source_tracking.follow(self._string(data, "input", required=True) or "", provider=following_provider)
                except (BilibiliError, TrackingError) as error:
                    raise ApiError(_BILIBILI_ERROR_STATUS.get(error.code, HTTPStatus.UNPROCESSABLE_ENTITY), following_provider + "_" + error.code, "The public source could not be followed.") from None
                if not creator_from_content and following_provider == "YOUTUBE":
                    updated = self._service.update_source(source.source_id, processing_policy=mode)
                    assert updated is not None
                    source = updated
                if self._source_run_wakeup is not None:
                    self._source_run_wakeup()
                return HTTPStatus.OK, {"source": self._source_projection(source)}
            if method == "POST" and route == "/api/v1/sources/check-stale":
                self._only_keys(self._body(body), set())
                from youtube_intel.following_tracking import tracking_due
                results: list[str] = []
                unavailable: list[str] = []
                # Scheduling follows the oldest due frontier, not the UI list's
                # creation order, so newer follows cannot starve older providers.
                with self._repository._connect() as connection:
                    sources = connection.execute("SELECT s.source_id FROM source_tracking_state t JOIN source_subscriptions s USING(source_id) WHERE s.enabled=1 ORDER BY t.next_check_at,s.source_id").fetchall()
                for row in sources:
                    if len(results) >= 3:
                        break
                    source_id = row[0]
                    tracked_source = self._repository.get_source_subscription(source_id)
                    if tracked_source and tracked_source.provider == "BILIBILI" and not CREATOR_FOLLOWING_AVAILABLE:
                        if tracking_due(self._repository, source_id, self._now()):
                            unavailable.append("CAPABILITY_UNAVAILABLE")
                        continue
                    if tracking_due(self._repository, source_id, self._now()):
                        from youtube_intel.following_scheduler import (
                            AUTOMATIC_CHECK_PREFIX,
                        )
                        with self._repository._connect() as connection:
                            due = connection.execute("SELECT next_check_at FROM source_tracking_state WHERE source_id=?", (source_id,)).fetchone()[0]
                        result = self._service.check_source(source_id, command_id=AUTOMATIC_CHECK_PREFIX + source_id + ":" + due, automatic=True)
                        results.append(result.status.value)
                if self._source_run_wakeup is not None:
                    self._source_run_wakeup()
                return HTTPStatus.ACCEPTED, {"checks": results + unavailable[:3]}
            tracked_retry_route=re.fullmatch(r'/api/v1/content/([^/]+)/retry(?:/(actions))?',route)
            if tracked_retry_route and method in {'GET','POST'}:
                if self._tracked_content_retry is None:
                    raise ApiError(HTTPStatus.CONFLICT,'RETRY_CONTRACT_UNAVAILABLE','Content retry is unavailable in this session.')
                try:
                    if method=='GET':
                        return HTTPStatus.OK,{'tracked_content_retry':self._tracked_content_retry.status(tracked_retry_route[1])}
                    data=self._body(body)
                    if tracked_retry_route[2]:
                        self._only_keys(data,{'request_id','operation','command_id','expected_revision'})
                        request_id=self._retry_string(data, 'request_id')
                        revision=self._integer(data,'expected_revision',required=True)
                        if revision is None:
                            raise RetryConflict('Content retry revision is missing')
                        receipt=self._tracked_content_retry.action(request_id,
                            operation=self._retry_string(data, 'operation'),command_id=self._retry_string(data, 'command_id'),
                            expected_revision=revision,expected_video_id=tracked_retry_route[1])
                    else:
                        self._only_keys(data,{'command_id','expected_job_id'})
                        receipt=self._tracked_content_retry.request(tracked_retry_route[1],
                            command_id=self._retry_string(data, 'command_id'),expected_job_id=self._retry_string(data, 'expected_job_id'))
                except RetryIntegrity as error:
                    raise ApiError(HTTPStatus.CONFLICT,'RETRY_INTEGRITY_INVALID','Content retry evidence could not be verified. No new request was sent.') from error
                except RetryConflict as error:
                    raise ApiError(HTTPStatus.CONFLICT,'RETRY_CONFLICT','Content retry state changed or is busy. Refresh and try again.') from error
                if self._source_run_wakeup is not None:
                    self._source_run_wakeup()
                return HTTPStatus.ACCEPTED,{'tracked_content_retry':receipt}
            if method == "POST" and (route == "/api/v1/bilibili/imports" or re.fullmatch(r"/api/v1/videos/[^/]+/captions/retry", route)):
                if self._bilibili_provider is None:
                    raise ApiError(HTTPStatus.CONFLICT, "BILIBILI_STORAGE_UNAVAILABLE", "Content storage is unavailable.")
                data = self._body(body)
                self._only_keys(data, {"input"} if route == "/api/v1/bilibili/imports" else set())
                if not self._bilibili_import_slot.acquire(blocking=False):
                    raise ApiError(HTTPStatus.TOO_MANY_REQUESTS, "BILIBILI_RATE_LIMITED", "An import is already processing.")
                try:
                    if route == "/api/v1/bilibili/imports":
                        bilibili_input = self._string(data, "input", required=True)
                        assert bilibili_input is not None
                        imported = self._bilibili_provider.import_input(bilibili_input)
                    else:
                        imported = self._bilibili_provider.retry(route.split("/")[4])
                except BilibiliError as rejection:
                    status = _BILIBILI_ERROR_STATUS.get(
                        rejection.code, HTTPStatus.UNPROCESSABLE_ENTITY
                    )
                    raise ApiError(status, "BILIBILI_" + rejection.code, "The public video could not be imported.") from None
                finally:
                    self._bilibili_import_slot.release()
                return HTTPStatus.OK if imported.reused else HTTPStatus.CREATED, {"import": imported.as_dict()}
            if route.startswith("/api/v1/local/transcription/") or re.fullmatch(r"/api/v1/videos/[^/]+/transcription", route):
                return self._transcription_route(method, route, body)
            if method == "POST" and route == "/api/v1/local/imports":
                if self._local_provider is None:
                    raise ApiError(HTTPStatus.CONFLICT, "LOCAL_STORAGE_UNAVAILABLE", "Local storage is unavailable.")
                query = parse_qs(urlparse(path).query, keep_blank_values=True)
                names = query.get("filename", [])
                if set(query) != {"filename"} or len(names) != 1 or len(names[0]) > 1024:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY,"LOCAL_INVALID_FILENAME","Select a supported file.")
                try:
                    import_result = self._local_provider.import_bytes(names[0], body)
                except LocalImportError as rejection:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY,rejection.code,"The selected file could not be imported.") from None
                return HTTPStatus.OK if import_result.duplicate else HTTPStatus.CREATED, {"import":import_result.as_dict()}
            if route == "/api/v1/research" or route.startswith("/api/v1/research/"):
                return self._research_route(method, path, body)
            if method == "GET" and route == "/api/v1/backup-restore/status":
                if self._backup_restore_service is None:
                    raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Backup and Restore is unavailable.")
                return HTTPStatus.OK, {"status": self._backup_restore_service.readiness()}
            if method == "POST" and route == "/api/v1/backup-restore/restore/stage":
                if self._backup_restore_service is None:
                    raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Backup and Restore is unavailable.")
                staged = self._backup_restore_service.stage_restore(body)
                return HTTPStatus.OK, {
                    "restore": {
                        "restore_id": staged.restore_id,
                        "archive_sha256": staged.archive_sha256,
                        "preview": staged.preview,
                    }
                }
            if route == "/api/v1/settings/cloud-spending-policy" and method in {"GET", "PUT"}:
                if self._cloud_spending_policy is None:
                    raise ApiError(HTTPStatus.CONFLICT, "CLOUD_POLICY_UNAVAILABLE", "Cloud spending settings are unavailable in this runtime.")
                if urlparse(path).query:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Request contains unsupported fields.")
                policy_data = self._body(body)
                if method == "GET":
                    self._only_keys(policy_data, set())
                    return HTTPStatus.OK, {"spending_policy": self._cloud_spending_policy.status()}
                self._only_keys(policy_data, {"expected_revision", "enabled", "total_cny", "per_request_cny", "max_calls", "accept_price_hash", "acknowledge"})
                try:
                    policy_result = self._cloud_spending_policy.update(expected_revision=policy_data.get("expected_revision"),
                        enabled=policy_data.get("enabled"), total_cny=policy_data.get("total_cny"), per_request_cny=policy_data.get("per_request_cny"),
                        max_calls=policy_data.get("max_calls"), accept_price_hash=policy_data.get("accept_price_hash"), acknowledge=policy_data.get("acknowledge"))
                except SpendingPolicyRejected as error:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY if error.code == "CLOUD_POLICY_INVALID" else HTTPStatus.CONFLICT,
                        error.code, "Cloud spending settings were not changed. Keep this draft and check current policy or retained reservations.") from None
                return HTTPStatus.OK, {"spending_policy": policy_result}
            if method == "GET" and route == "/api/v1/saved-intelligence":
                return HTTPStatus.OK, self._saved_list(path)
            if route in {"/api/v1/settings/bigmodel-credential", "/api/v1/settings/bigmodel-credential/delete"}:
                if urlparse(path).query:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Request contains unsupported fields.")
                data = self._body(body)
                secret = ""
                if method == "GET" and route == "/api/v1/settings/bigmodel-credential":
                    self._only_keys(data, set())
                elif method == "PUT" and route == "/api/v1/settings/bigmodel-credential":
                    self._only_keys(data, {"credential"})
                    secret = BigModelCredentialSettings.validate_credential(data.get("credential"))
                elif method == "POST" and route.endswith("/delete"):
                    self._only_keys(data, {"confirm"})
                    if data.get("confirm") != "DELETE":
                        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "CONFIRMATION_REQUIRED", "Confirm credential deletion explicitly.")
                else:
                    raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")
                if self._bigmodel_settings is None:
                    raise ApiError(HTTPStatus.CONFLICT, "CREDENTIAL_STORE_UNAVAILABLE", "System credential store is unavailable.")
                if method == "PUT":
                    self._bigmodel_settings.save(secret)
                elif method == "POST":
                    self._bigmodel_settings.delete()
                return HTTPStatus.OK, self._bigmodel_settings.status()
            if method == "GET":
                return HTTPStatus.OK, self._get(route)
            # Local provider capability is explicit: source material never
            # enters YouTube ingestion or external Intelligence transports.
            local_target = re.fullmatch(r'/api/v1/videos/([^/]+)/cloud-intelligence/(?:review|confirm)',route)
            source_target = re.fullmatch(r'/api/v1/sources/([^/]+)/videos/([^/]+)/(?:manual-analyze|distill)',route)
            if local_target is not None or source_target is not None:
                content_id=local_target[1] if local_target is not None else source_target[2] if source_target is not None else ''
                selected_local_content=self._repository.get_video(content_id)
                if selected_local_content is not None and selected_local_content.provider=='LOCAL':
                    raise ApiError(HTTPStatus.CONFLICT,'LOCAL_PROVIDER_CAPABILITY_UNAVAILABLE','Local Content uses on-device source processing.')
                if selected_local_content is not None and selected_local_content.provider=='BILIBILI':
                    raise ApiError(HTTPStatus.CONFLICT,'BILIBILI_PROVIDER_CAPABILITY_UNAVAILABLE','Public caption Content uses stored source processing.')
            data = self._body(body)
            if route in {"/api/v1/settings/cloud-credential", "/api/v1/settings/cloud-credential/delete"}:
                if self._model_settings is None:
                    raise ApiError(HTTPStatus.CONFLICT, "CREDENTIAL_STORE_UNAVAILABLE", "System credential store is unavailable.")
                if method == "PUT" and route == "/api/v1/settings/cloud-credential":
                    self._only_keys(data, {"credential"})
                    self._model_settings.save_credential(self._string(data, "credential", required=True) or "")
                elif method == "POST" and route.endswith("/delete"):
                    self._only_keys(data, {"confirm"})
                    if data.get("confirm") != "DELETE":
                        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "CONFIRMATION_REQUIRED", "Confirm credential deletion explicitly.")
                    self._model_settings.delete_credential()
                else:
                    raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")
                self._cloud_credential_available = bool(self._model_settings.credential())
                if self._refresh_cloud_distillation is not None:
                    self._cloud_distillation_service = self._refresh_cloud_distillation()
                if self._refresh_cloud_synthesis is not None:
                    self._cloud_synthesis_service = self._refresh_cloud_synthesis()
                return HTTPStatus.OK, self._model_settings.credential_status()
            if method == "POST" and route.startswith("/api/v1/videos/") and route.endswith("/deep-analysis/obsidian"):
                content_id = self._obsidian_content_id(route)
                self._only_keys(data, {"result_identity"})
                result_identity = self._string(data, "result_identity", required=True)
                assert result_identity is not None
                try:
                    published = self._deep_analysis_publisher.publish(content_id=content_id, result_identity=result_identity)
                except DeepAnalysisPublishError as rejection:
                    raise ApiError(HTTPStatus.CONFLICT, rejection.code, "Deep Analysis could not be published to Obsidian.") from None
                return HTTPStatus.OK, {"publish": published}
            if method == "POST" and re.fullmatch(r"/api/v1/videos/[^/]+/intelligence", route):
                self._only_keys(data, {"command_id"})
                video_id = route.split("/")[4]
                source_id = self._manual_content_source(video_id)
                if source_id is None or self._distillation_service is None:
                    raise ApiError(HTTPStatus.CONFLICT, "CONTENT_NOT_READY", "Finish organizing this Content before extracting Intelligence.")
                command_id = self._string(data, "command_id", required=True) or ""
                from .long_distillation_persistence import (
                    ModelConfigurationRequired,
                    configuration_required,
                )
                from .state import StateStoreError
                try:
                    if configuration_required(self._distillation_service):
                        raise ModelConfigurationRequired("MODEL_CONFIGURATION_REQUIRED")
                    reservation = self._distillation_service.reserve_distillation_execution(
                        source_id=source_id, video_id=video_id,
                        evidence_ids=self._distillation_service.reservation_evidence_ids(video_id),
                        manual_command_id=command_id,
                    )
                except ModelConfigurationRequired as error:
                    raise ApiError(HTTPStatus.CONFLICT, "MODEL_CONFIGURATION_REQUIRED",
                        "Select the fixed local Intelligence model in Settings before requesting extraction.") from error
                except StateStoreError as error:
                    raise ApiError(HTTPStatus.CONFLICT, "CONTENT_INTELLIGENCE_UNAVAILABLE",
                        "Content source could not be verified for Intelligence. Existing source material was kept.") from error
                # This service is the local route. Cloud review/authorization is
                # a separate explicit command and is never an automatic fallback.
                self._distillation_service.continue_reserved_distillation(reservation.execution_id)
                return HTTPStatus.ACCEPTED, {"execution": self._distillation_execution_dto(
                    self._repository.get_distillation_execution(reservation.execution_id)
                )}
            if method == "POST" and re.fullmatch(r"/api/v1/videos/[^/]+/intelligence/cancel", route):
                self._only_keys(data, {"execution_id"})
                video_id = route.split("/")[4]
                execution_id = self._string(data, "execution_id", required=True) or ""
                from .state import StateStoreError
                try:
                    from . import system_synthesis_persistence as synthesis
                    current = self._repository.get_distillation_execution(execution_id)
                    if (current is not None and current.video_id == video_id
                        and self._synthesis_pending_cancelable(current)):
                        synthesis.abandon_unclaimed(self._repository, execution_id, now=self._now())
                    execution = self._repository.cancel_waiting_model_execution(
                        execution_id, video_id=video_id, now=self._now(),
                    )
                except StateStoreError:
                    raise ApiError(HTTPStatus.CONFLICT, "WAITING_MODEL_CANCEL_UNSAFE",
                                   "This task cannot be safely cancelled. Refresh its current state.") from None
                return HTTPStatus.OK, {"execution": self._distillation_execution_dto(execution)}
            cloud_prefix = "/api/v1/videos/"
            if method == "GET" and route == "/api/v1/cloud-intelligence/profiles":
                from .system_synthesis_profile import PROFILE_ID
                profiles = []
                for profile_id, candidate_service, qualified in (
                    ("legacy", self._cloud_distillation_service, self._cloud_intelligence_qualified),
                    (PROFILE_ID, self._cloud_synthesis_service, self._cloud_synthesis_qualified),
                ):
                    if candidate_service is not None:
                        profiles.append({"profile_id": profile_id,
                            "provider": candidate_service._selected_provider, "model": candidate_service._selected_model,
                            "adapter_available": True, "qualified": qualified,
                            "execution_enabled": self._cloud_execution_enabled,
                            "credential_available": self._cloud_credential_available})
                return HTTPStatus.OK, {"profiles": profiles}
            if method == "POST" and route.startswith(cloud_prefix) and (
                route.endswith("/cloud-intelligence/review")
                or route.endswith("/cloud-intelligence/confirm")
            ):
                from .system_synthesis_profile import PROFILE_ID
                selected_profile = data.get("profile_id", "legacy")
                if not isinstance(selected_profile, str) or selected_profile not in {"legacy", PROFILE_ID}:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "CLOUD_PROFILE_UNKNOWN", "Select a supported backend model profile.")
                cloud_service = self._cloud_synthesis_service if selected_profile == PROFILE_ID else self._cloud_distillation_service
                cloud_qualified = self._cloud_synthesis_qualified if selected_profile == PROFILE_ID else self._cloud_intelligence_qualified
                if cloud_service is None:
                    raise ApiError(HTTPStatus.CONFLICT, "CLOUD_INTELLIGENCE_UNAVAILABLE",
                                   "Cloud Intelligence preview is unavailable.")
                video_id, _, cloud_action = route.removeprefix(cloud_prefix).partition("/")
                if cloud_action not in {"cloud-intelligence/review", "cloud-intelligence/confirm"}:
                    raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Cloud Intelligence route was not found.")
                if not video_id or self._repository.get_video(video_id) is None:
                    raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Video was not found.")
                if route.endswith("/cloud-intelligence/review"):
                    self._only_keys(data, {"command_id", "profile_id"})
                    manual_command_id = self._string(data, "command_id")
                    manual_source = self._manual_content_source(video_id) if manual_command_id else None
                    candidates = (manual_source,) if manual_source else tuple(
                        source.source_id for source in self._repository.list_source_subscriptions()
                        if source.enabled and self._repository.source_has_video(source.source_id, video_id)
                        and (
                            (decision := self._repository.current_filter_decision(source.source_id, video_id))
                            is not None and decision.outcome is FilterOutcome.RELEVANT
                        )
                    )
                    if not candidates:
                        raise ApiError(HTTPStatus.CONFLICT, "EVIDENCE_UNAVAILABLE",
                                       "No eligible source and Evidence are available for this Content.")
                    cloud_evidence_ids = self._repository.list_canonical_coverage_evidence_ids(video_id)
                    review = cloud_service.preview_cloud_execution(
                            source_id=sorted(candidates)[0], video_id=video_id,
                            evidence_ids=cloud_evidence_ids, manual_command_id=manual_command_id,
                            qualified=cloud_qualified,
                            credential_available=self._cloud_credential_available,
                        )
                    if not self._cloud_execution_enabled:
                        readiness = cast(dict[str, object], review["readiness"])
                        readiness["can_confirm"] = False
                        cast(list[str], readiness["blockers"]).append("CLOUD_EXECUTION_DISABLED")
                    return HTTPStatus.OK, {"review": review}
                self._only_keys(data, {"execution_id", "review_hash", "authorize", "profile_id"})
                if data.get("authorize") is not True:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "CONSENT_REQUIRED",
                                   "Cloud execution requires affirmative confirmation.")
                execution_id = self._string(data, "execution_id", required=True) or ""
                review_hash = self._string(data, "review_hash", required=True) or ""
                if not self._cloud_execution_enabled:
                    raise ApiError(HTTPStatus.CONFLICT, "CLOUD_EXECUTION_DISABLED",
                                   "Cloud execution is disabled for this runtime.")
                if not cloud_qualified or not self._cloud_credential_available:
                    raise ApiError(HTTPStatus.CONFLICT, "CLOUD_INTELLIGENCE_UNAVAILABLE",
                                   "Qualified Cloud Intelligence requires an available backend credential.")
                from .distillation import CloudPreviewRejected
                from .state import StateStoreError
                try:
                    authorization_id, cloud_result = cloud_service.confirm_cloud_preview(
                        video_id=video_id, execution_id=execution_id, review_hash=review_hash,
                    )
                except CloudPreviewRejected as error:
                    raise ApiError(HTTPStatus.CONFLICT, error.code,
                                   "Cloud confirmation was refused. Check current data, model and spending policy.",
                                   details={"reason_code": error.reason}) from None
                except (ValueError, StateStoreError):
                    raise ApiError(HTTPStatus.CONFLICT, "CLOUD_CONFIRMATION_REFUSED",
                                   "Cloud confirmation is unavailable or changed. Review current data, model and budget again.") from None
                return HTTPStatus.ACCEPTED, {
                    "authorization_id": authorization_id,
                    "execution": {
                        "execution_id": cloud_result.execution_id,
                        "status": cloud_result.status.value,
                        "invocation_count": cloud_result.invocation_count,
                        "intelligence_id": cloud_result.intelligence_id,
                        "revision_id": cloud_result.revision_id,
                    },
                }
            if (
                method == "GET"
                and route == "/api/v1/deep-analysis/capability"
            ):
                return HTTPStatus.OK, {
                    "capability": self._require_deep_analysis().capability_report()
                }
            deep_analysis_prefix = "/api/v1/videos/"
            if (
                method == "POST"
                and route.startswith(deep_analysis_prefix)
                and (route.endswith("/deep-analysis") or route.endswith("/deep-analysis/preflight"))
            ):
                deep_analysis_service = self._require_deep_analysis()
                video_id, _, tail = route.removeprefix(
                    deep_analysis_prefix
                ).partition("/")
                if tail not in {"deep-analysis", "deep-analysis/preflight"} or not video_id:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND,
                        "NOT_FOUND",
                        "Deep Analysis route was not found.",
                    )
                if self._repository.get_video(video_id) is None:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Content was not found."
                    )
                self._only_keys(data, {"authorize_cloud", "execution_id", "route_id", "acknowledge_unknown_cost", "egress_mode"})
                for identity in ("execution_id", "route_id", "egress_mode"):
                    value = data.get(identity)
                    if identity in data and (not isinstance(value, str) or not value or len(value) > 256):
                        raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "Invalid Deep Analysis identity.")
                authorize_cloud = data.get("authorize_cloud") is True
                try:
                    if tail == "deep-analysis/preflight":
                        self._only_keys(data, {"route_id"})
                        if not isinstance(data.get("route_id"), str):
                            raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "A route is required.")
                        return HTTPStatus.OK, {"preflight": deep_analysis_service.preflight(content_id=video_id, route_id=cast(str, data["route_id"]))}
                    deep_analysis_run = deep_analysis_service.run(
                        content_id=video_id, cloud_consent=authorize_cloud,
                        route_id=cast(str | None, data.get("route_id")), execution_id=cast(str | None, data.get("execution_id")),
                        acknowledge_unknown_cost=data.get("acknowledge_unknown_cost") is True,
                        egress_mode=cast(str, data.get("egress_mode", "SELECTED_EVIDENCE_ONLY")),
                    )
                except DeepAnalysisRejected as rejection:
                    # The stable machine code drives localized UI copy; the
                    # English prose is a developer diagnostic only.
                    raise ApiError(
                        HTTPStatus.CONFLICT,
                        f"DEEP_ANALYSIS_{rejection.status.availability.value}",
                        rejection.status.reason or "Deep Analysis is unavailable.",
                        details={
                            "reason_code": (
                                None
                                if rejection.status.reason_code is None
                                else rejection.status.reason_code.value
                            ),
                            "availability": rejection.status.availability.value,
                            "consent_required": rejection.status.consent_required,
                        },
                    ) from None
                return HTTPStatus.CREATED, {
                    "deep_analysis": {"result": deep_analysis_run.as_dict()}
                }
            if method == "POST" and route == "/api/v1/backup-restore/backups":
                service = self._require_backup_restore()
                self._only_keys(data, set())
                backup_result = service.create_backup()
                return HTTPStatus.CREATED, {
                    "backup": {
                        "backup_id": backup_result.backup_id,
                        "file_name": backup_result.file_name,
                        "size_bytes": backup_result.size_bytes,
                        "created_at": backup_result.created_at,
                        "preview": backup_result.preview,
                    }
                }
            if method == "POST" and route == "/api/v1/backup-restore/restore/confirm":
                service = self._require_backup_restore()
                self._only_keys(data, {"restore_id"})
                restore_id = self._string(data, "restore_id", required=True) or ""
                return HTTPStatus.ACCEPTED, {
                    "restore": service.confirm_restore(restore_id)
                }
            if method == "POST" and route == "/api/v1/backup-restore/restore/cancel":
                service = self._require_backup_restore()
                self._only_keys(data, {"restore_id"})
                restore_id = self._string(data, "restore_id", required=True) or ""
                cancelled = service.cancel_restore(restore_id)
                if not cancelled:
                    raise ApiError(HTTPStatus.CONFLICT, "RESTORE_CANNOT_CANCEL", "Inspected Restore is no longer available.")
                return HTTPStatus.OK, {"cancelled": True}
            translation_route = self._translation_route(route)
            if method == "POST" and translation_route is not None:
                self._only_keys(data, set())
                return HTTPStatus.OK, self._translate_presented_evidence(
                    intelligence_id=translation_route[0],
                    evidence_id=translation_route[1],
                )
            content_translation_route = self._content_translation_route(route)
            if method == "POST" and content_translation_route is not None:
                self._only_keys(data, set())
                return HTTPStatus.OK, self._translate_content_evidence(
                    video_id=content_translation_route[0],
                    evidence_id=content_translation_route[1],
                )
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
            if method == "POST" and route == "/api/v1/sources/import":
                self._only_keys(data, {"url", "command_id"})
                from youtube_intel.orchestration import normalize_source_url
                url = self._string(data, "url", required=True) or ""
                if normalize_source_url(url).source_type is not SourceType.VIDEO_URL:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "YOUTUBE_INVALID_INPUT", "Paste a single video link, or use channel following.")
                source = self._service.add_source(url=url, processing_policy=ProcessingPolicy.DISCOVER_ONLY)
                import_run = self._service.check_source(source.source_id, command_id=self._string(data, "command_id", required=True))
                if self._source_run_wakeup is not None:
                    self._source_run_wakeup()
                return HTTPStatus.ACCEPTED, {"source": self._source_projection(source), "source_run": None if import_run.source_run is None else _source_run_dto(import_run.source_run)}
            if method == "POST" and route == "/api/v1/sources":
                processing_policy = ProcessingPolicy(
                    self._string(data, "processing_policy", required=True) or ""
                )
                from youtube_intel.orchestration import normalize_source_url
                source_url = self._string(data, "url", required=True) or ""
                if normalize_source_url(source_url).source_type is SourceType.CHANNEL:
                    if self._source_tracking is None:
                        raise ApiError(HTTPStatus.CONFLICT, "TRACKING_UNAVAILABLE", "Channel following is unavailable; no unresolved source was created.")
                    source = self._source_tracking.follow(source_url, provider="YOUTUBE")
                    source = self._service.update_source(source.source_id, processing_policy=processing_policy) or source
                else:
                    source = self._service.add_source(url=source_url, processing_policy=processing_policy)
                return HTTPStatus.CREATED, {"source": _source_dto(source)}
            source_policy_prefix = "/api/v1/sources/"
            if (
                method == "PUT"
                and route.startswith(source_policy_prefix)
                and (route.endswith("/policy") or route.endswith("/interests"))
            ):
                interest_only = route.endswith("/interests")
                source_id = route.removeprefix(source_policy_prefix).removesuffix(
                    "/interests" if interest_only else "/policy"
                )
                if not source_id or "/" in source_id:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                    )
                self._only_keys(
                    data,
                    {
                        "command_id",
                        "expected_source_policy_revision_id",
                        "focus_mode",
                        "focus_rules",
                        "ignore_mode",
                        "ignore_rules",
                        "distillation_style_mode",
                        "distillation_style",
                    } | (set() if interest_only else {"initial_history_count", "per_run_max_new_videos"}),
                )
                if interest_only and "expected_source_policy_revision_id" not in data:
                    raise ValueError("interest requires an explicit expected revision")
                source_policy = self._source_policy_service.update_source(
                    source_id=source_id,
                    command_id=self._string(data, "command_id", required=True) or "",
                    expected_source_policy_revision_id=data.get("expected_source_policy_revision_id", _EXPECTED_MISSING),
                    _interest_only=interest_only,
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
                return HTTPStatus.OK, {"policy": _source_policy_dto(source_policy),
                    "applied_source_policy_revision_id": source_policy.applied_revision_id,
                    "current_source_policy_revision_id": source_policy.source_policy_revision_id,
                    "historical_replay": source_policy.applied_revision_id != source_policy.source_policy_revision_id}
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
                if self._source_run_wakeup is not None:
                    self._source_run_wakeup()
                return HTTPStatus.OK, {"source": _source_dto(updated_source)}
            if (
                method == "POST"
                and route.endswith("/check")
                and route.startswith("/api/v1/sources/")
            ):
                source_id = route.split("/")[-2]
                self._only_keys(data, {"command_id"})
                existing = self._repository.get_source_subscription(source_id)
                if (
                    existing is not None
                    and existing.provider == "BILIBILI"
                    and existing.source_type is SourceType.CREATOR
                    and not CREATOR_FOLLOWING_AVAILABLE
                ):
                    # Stored creator rows stay readable, but a withdrawn
                    # capability must not answer Check Now with a silent request.
                    return HTTPStatus.OK, {
                        "status": "CAPABILITY_UNAVAILABLE",
                        "message": CREATOR_FOLLOWING_CODE,
                    }
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
        except OfflineError as error:
            return HTTPStatus.CONFLICT, {"error": {"code": error.code, "message": "Local transcription is unavailable or could not complete."}}
        except ApiError:
            raise
        except IntegrityConflict as error:
            raise ApiError(
                HTTPStatus.CONFLICT,
                "CONFLICT",
                "Preference or feedback command conflicts with existing history.",
            ) from error
        except CredentialStoreError:
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "CREDENTIAL_STORE_UNAVAILABLE", "System credential store is unavailable.") from None
        except BackupRestoreError as error:
            raise ApiError(
                HTTPStatus.CONFLICT,
                "BACKUP_RESTORE_REJECTED",
                str(error),
            ) from error
        except (ValueError, KeyError) as error:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "Request values are invalid or unavailable.",
            ) from error

    def _research_route(self, method: str, path: str, body: bytes) -> tuple[int, dict[str, object]]:
        parsed = urlparse(path)
        route = parsed.path.rstrip("/")
        try:
            if method == "POST" and route == "/api/v1/research":
                data = self._body(body)
                try:
                    request = ResearchRequest.model_validate(data)
                except ValidationError as error:
                    fields = {e["loc"][0] for e in error.errors() if e["loc"]}
                    code = "RESEARCH_INVALID_QUESTION" if "question" in fields else (
                        "RESEARCH_EMPTY_SCOPE" if data.get("content_ids") == [] else "RESEARCH_INVALID_SCOPE"
                    )
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, code, "Research input is invalid.") from None
                result = self._research_service.assemble(request, output_language=self._output_language_service.effective().value)
                return HTTPStatus.CREATED, {"research": result.as_dict()}
            if method == "GET" and route == "/api/v1/research/capability":
                return HTTPStatus.OK, {"capability": {"mode": "DETERMINISTIC_LIBRARY_PACKET", "scope_types": ["SELECTED_CONTENT"], "synthesis_status": "UNSUPPORTED_MODEL_SYNTHESIS", "provider_dispatch": False}}
            if method == "GET" and route in {"/api/v1/research", "/api/v1/research/scope"}:
                params = parse_qs(parsed.query, keep_blank_values=True)
                if set(params) - {"offset", "query"} or any(len(v) != 1 for v in params.values()):
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "RESEARCH_INVALID_SCOPE", "Invalid Research pagination.")
                try:
                    offset = int(params.get("offset", ["0"])[0])
                except ValueError:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "RESEARCH_INVALID_SCOPE", "Invalid Research pagination.") from None
                query = params.get("query", [""])[0]
                if offset < 0 or offset > 10000 or len(query) > 120:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "RESEARCH_INVALID_SCOPE", "Research retrieval is bounded.")
                projection = self._research_service.scope_options(query=query, offset=offset) if route.endswith("/scope") else self._research_service.list_current(offset=offset)
                return HTTPStatus.OK, projection
            diff = re.fullmatch(r"/api/v1/research/([a-f0-9]{64})/diff", route)
            if method == "GET" and diff:
                params = parse_qs(parsed.query, keep_blank_values=True)
                if set(params) != {"base_revision", "target_revision"} or any(len(v) != 1 for v in params.values()):
                    raise ResearchRejected("RESEARCH_DIFF_INVALID_REQUEST")
                comparison = self._research_service.diff(diff[1], params["base_revision"][0], params["target_revision"][0])
                return HTTPStatus.OK, {"diff": comparison.model_dump(mode="json")}
            history = re.fullmatch(r"/api/v1/research/([a-f0-9]{64})/history(?:/([a-f0-9]{64}))?", route)
            if method == "GET" and history:
                research_id, revision_id = history.groups()
                params = parse_qs(parsed.query, keep_blank_values=True)
                if set(params) - ({"cursor"} if revision_id is None else set()) or any(len(v) != 1 for v in params.values()):
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "RESEARCH_INVALID_CURSOR", "Invalid History pagination.")
                if revision_id is not None:
                    result = self._research_service.read_revision(research_id, revision_id)
                    return HTTPStatus.OK, {"research": result.as_dict(), "is_current": result.is_current}
                return HTTPStatus.OK, self._research_service.history(research_id, cursor=params.get("cursor", [None])[0])
            if method == "GET" and re.fullmatch(r"/api/v1/research/[a-f0-9]{64}", route):
                return HTTPStatus.OK, {"research": self._research_service.read(route.rsplit("/", 1)[1]).as_dict()}
            raise ApiError(HTTPStatus.NOT_FOUND, "RESEARCH_NOT_FOUND", "Research route was not found.")
        except ResearchRejected as error:
            status = HTTPStatus.NOT_FOUND if error.code in {"RESEARCH_NOT_FOUND", "RESEARCH_SCOPE_NOT_FOUND", "RESEARCH_REVISION_NOT_FOUND", "RESEARCH_DIFF_BASE_NOT_FOUND", "RESEARCH_DIFF_TARGET_NOT_FOUND"} else (HTTPStatus.UNPROCESSABLE_ENTITY if error.code in {"RESEARCH_INVALID_CURSOR", "RESEARCH_DIFF_INVALID_REQUEST"} else HTTPStatus.CONFLICT)
            raise ApiError(status, error.code, "Research could not be read or assembled.") from None
        except (sqlite3.Error, OSError) as error:
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "RESEARCH_EXECUTION_FAILED", "Research library access failed.") from error

    def _require_backup_restore(self) -> BackupRestoreService:
        if self._backup_restore_service is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Backup and Restore is unavailable.")
        return self._backup_restore_service

    def _pending_content_work(self) -> list[dict[str, object]]:
        """Real durable video import/discovery identities; never baseline history."""
        with self._repository._connect() as connection:
            rows = connection.execute(
                "SELECT s.source_id,s.video_id,s.canonical_url,s.created_at,NULL AS enrollment FROM source_subscriptions s LEFT JOIN videos v ON v.video_id=s.video_id WHERE s.provider='YOUTUBE' AND s.source_type='VIDEO_URL' AND v.video_id IS NULL "
                "UNION ALL SELECT o.source_id,o.canonical_identity,'https://www.youtube.com/watch?v='||o.canonical_identity,o.observed_at,o.enrollment FROM source_observations o JOIN source_subscriptions s USING(source_id) LEFT JOIN videos v ON v.video_id=o.canonical_identity WHERE s.provider='YOUTUBE' AND o.baseline=0 AND v.video_id IS NULL LIMIT 100"
            ).fetchall()
        runs = self._repository.list_source_runs()
        items: dict[str, dict[str, object]] = {}
        for row in rows:
            video_id = row["video_id"]
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id or "") is None:
                continue
            own_runs = [run for run in runs if run.source_id == row["source_id"]]
            latest = own_runs[-1] if own_runs else None
            state = "WAITING"
            if row["enrollment"] in {"UNSUPPORTED", "UNAVAILABLE"} or (latest and latest.state.value in {"FAILED", "NEEDS_ATTENTION", "AMBIGUOUS"}):
                state = "NEEDS_ATTENTION"
            elif latest and latest.state.value == "RUNNING":
                state = "FETCHING"
            items[video_id] = {"video_id": video_id, "provider": "YOUTUBE", "title": row["canonical_url"], "source_url": row["canonical_url"], "channel_id": None, "channel_name": None, "published_at": None, "last_updated": row["created_at"], "processing_status": state, "work_kind": "DURABLE_CONTENT_IDENTITY", "source_id": row["source_id"]}
        return list(items.values())

    def _local_intelligence_status(self) -> dict[str, object]:
        """Reviewed scope/language facts only, never a model load or admission."""
        binding = None if self._distillation_service is None else self._distillation_service.capability_binding()
        unknown: dict[str, object] = {"status": "UNKNOWN", "model": None, "profile_id": None,
                                      "runtime_binding": binding, "scopes": []}
        try:
            if self._local_distillation_capabilities is None:
                return unknown
            rows = self._local_distillation_capabilities()
            expected = {(scope, language) for scope in ("YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT") for language in ("en", "zh-CN")}
            if not isinstance(rows, tuple) or len(rows) != len(expected):
                return unknown
            pairs: set[tuple[str, str]] = set()
            identities: set[tuple[str, str]] = set()
            for row in rows:
                if (not isinstance(row, dict) or set(row) != {"profile_id", "model", "scope", "output_language", "status"}
                    or any(not isinstance(row[key], str) or not cast(str, row[key]).strip() for key in row)
                    or row["status"] not in {"QUALIFIED", "NOT_QUALIFIED"}):
                    return unknown
                pairs.add((cast(str, row["scope"]), cast(str, row["output_language"])))
                identities.add((cast(str, row["profile_id"]), cast(str, row["model"])))
            if pairs != expected or len(identities) != 1:
                return unknown
            profile_id, model = next(iter(identities))
            return {"status": "KNOWN", "model": model, "profile_id": profile_id,
                    "runtime_binding": binding, "scopes": [dict(row) for row in rows]}
        except Exception:
            return unknown

    def _distillation_execution_dto(self, execution: object | None) -> dict[str, object]:
        result = _distillation_execution_dto(execution)
        if execution is not None:
            execution_id = str(getattr(execution, "execution_id"))
            if result["status"] == "WAITING_MODEL":
                result["can_cancel"] = self._repository.can_cancel_waiting_model_execution(execution_id)
            elif result["status"] == "PENDING":
                result["can_cancel"] = self._synthesis_pending_cancelable(execution)
            code = self._repository.get_bigmodel_http429_code(execution_id)
            if code is not None:
                result["cloud_http429_code"] = code
        return result

    def _synthesis_pending_cancelable(self, execution: object) -> bool:
        from . import system_synthesis_persistence as synthesis
        from .state import StateStoreError
        if (getattr(execution, "status", None) != "PENDING"
            or getattr(execution, "invocation_count", None) != 0
            or not synthesis.is_synthesis(str(getattr(execution, "execution_id", "")))):
            return False
        try:
            with self._repository._connect() as connection:
                synthesis.verify_execution(self._repository, connection, str(getattr(execution, "execution_id")))
            return True
        except (StateStoreError, ValueError, sqlite3.Error):
            return False

    def _pending_synthesis_executions(self, video_id: str) -> list[dict[str, object]]:
        with self._repository._connect() as connection:
            identities = [str(row[0]) for row in connection.execute(
                "SELECT execution_id FROM distillation_execution_checkpoints WHERE video_id=? AND status='PENDING' "
                "AND invocation_count=0 AND execution_id LIKE 'distillation:system-synthesis-%'", (video_id,))]
        return [self._distillation_execution_dto(execution) for identity in identities
            if (execution := self._repository.get_distillation_execution(identity)) is not None]

    def _content_local_intelligence_status(self, video_id: str, source_id: str | None) -> dict[str, object]:
        matrix = self._local_intelligence_status()
        language = None if self._distillation_service is None else self._distillation_service.capability_output_language(video_id)
        result: dict[str, object] = {"video_id": video_id, "scope": None, "output_language": language,
            "model": None, "profile_id": None, "qualification_status": "UNKNOWN",
            "runtime_binding": matrix["runtime_binding"], "request_state": "UNKNOWN", "reason": "CAPABILITY_STATUS_UNAVAILABLE"}
        if matrix["status"] != "KNOWN":
            return result
        video = self._repository.get_video(video_id)
        if video is None or source_id is None:
            result["reason"] = "CONTENT_NOT_READY"
            return result
        from .state import StateStoreError
        try:
            ids = (self._repository.list_canonical_coverage_evidence_ids(video_id) if self._distillation_service is None
                else self._distillation_service.reservation_evidence_ids(video_id))
        except StateStoreError:
            result["reason"] = "EVIDENCE_UNAVAILABLE"
            return result
        resolved = [self._repository.resolve_verified_evidence_text(identity) for identity in ids]
        if not resolved or any(item is None or item.video_id != video_id for item in resolved):
            result["reason"] = "EVIDENCE_UNAVAILABLE"
            return result
        locators = {item.locator_type for item in resolved if item is not None}
        scope = ("YT_TIMED" if video.provider == "YOUTUBE" and locators == {"TIMED_MEDIA"}
            else "LOCAL_TIMED" if video.provider == "LOCAL" and locators == {"TIMED_MEDIA"}
            else "LOCAL_TEXT" if video.provider == "LOCAL" and locators == {"TEXT_RANGE"} else None)
        result["scope"] = scope
        if scope is None or language not in {"en", "zh-CN"}:
            result["reason"] = "SCOPE_OR_LANGUAGE_UNAVAILABLE"
            return result
        from .long_distillation_persistence import route_required
        if self._local_intelligence_settings is not None and not self._local_intelligence_settings.admission_allowed():
            result.update(model=matrix["model"], profile_id=matrix["profile_id"],
                request_state="CONFIGURATION_REQUIRED", reason="MODEL_CONFIGURATION_REQUIRED")
            return result
        if self._distillation_service is not None and route_required(self._distillation_service, video_id, ids, source_id):
            from .local_distillation_profile import (
                NATIVE_SHORT_PROFILES,
                paired_long_profile,
            )
            from .long_distillation_execution import profile_qualified
            from .long_distillation_profile import resolve_long_profile
            profile_id = paired_long_profile(self._distillation_service._local_profile_id)
            long_profile = json.loads(resolve_long_profile(profile_id).profile_wire)
            qualified = self._distillation_service._local_profile_id in NATIVE_SHORT_PROFILES and profile_qualified(self._distillation_service, language)
            result.update(model=long_profile["model"], profile_id=profile_id,
                qualification_status="QUALIFIED" if qualified else "NOT_QUALIFIED",
                request_state="WAITING_MODEL", reason="NOT_QUALIFIED")
            if qualified:
                if self._local_distillation_available is True:
                    result.update(request_state="ELIGIBLE_FOR_ADMISSION", reason="ADMISSION_CHECKS_REQUIRED")
                elif self._local_distillation_available is False:
                    result["reason"] = "MODEL_UNAVAILABLE"
                else:
                    result.update(request_state="UNKNOWN", reason="RESOURCE_STATUS_UNKNOWN")
            return result
        rows = cast(list[dict[str, object]], matrix["scopes"])
        row = next(item for item in rows if item["scope"] == scope and item["output_language"] == language)
        result.update(model=row["model"], profile_id=row["profile_id"], qualification_status=row["status"], request_state="WAITING_MODEL")
        from .long_distillation_persistence import configuration_required
        if self._distillation_service is not None and configuration_required(self._distillation_service):
            result.update(request_state="CONFIGURATION_REQUIRED", reason="MODEL_CONFIGURATION_REQUIRED")
            return result
        if row["status"] != "QUALIFIED":
            result["reason"] = "NOT_QUALIFIED"
        elif matrix["runtime_binding"] != {"provider": "ollama", "model": row["model"], "profile_id": row["profile_id"]}:
            result["reason"] = "ROUTE_REINITIALIZATION_REQUIRED"
        elif self._local_distillation_available is False:
            result["reason"] = "MODEL_UNAVAILABLE"
        elif self._local_distillation_available is not True:
            result.update(request_state="UNKNOWN", reason="RESOURCE_STATUS_UNKNOWN")
        else:
            result.update(request_state="ELIGIBLE_FOR_ADMISSION", reason="ADMISSION_CHECKS_REQUIRED")
        return result

    def _manual_content_source(self, video_id: str) -> str | None:
        video = self._repository.get_video(video_id)
        note = self._note_projection(video_id).get("v2")
        if video is not None and video.provider == "LOCAL":
            return next((source.source_id for source in self._repository.list_source_subscriptions()
                         if (self._repository.manual_local_timed_context_hash(source.source_id, video_id) is not None
                             or self._repository.manual_local_text_context_hash(source.source_id, video_id) is not None)), None)
        if video is None or video.provider != "YOUTUBE" or not isinstance(note, dict) or note.get("status") != "AVAILABLE":
            return None
        if self._repository.get_verified_timed_transcript(video_id=video_id) is None:
            return None
        return next((source.source_id for source in self._repository.list_source_subscriptions()
                     if self._repository.source_has_video(source.source_id, video_id)), None)

    def _intelligence_activity(self) -> list[dict[str, object]]:
        activity: list[dict[str, object]] = []
        for video in self._repository.list_videos(limit=100):
            execution = self._repository.latest_distillation_execution_for_video(video.video_id)
            if execution is not None and execution.status != "SUCCEEDED":
                activity.append({"video_id": video.video_id, "title": video.title,
                                 **self._distillation_execution_dto(execution)})
        # A relevance/preparation wait can precede a distillation reservation.
        seen = {item["video_id"] for item in activity}
        for run in self._repository.list_source_runs():
            source = self._repository.get_source_subscription(run.source_id)
            if source is None or source.processing_policy != "STANDARD_INTELLIGENCE":
                continue
            for child in self._repository.list_source_run_children(run.run_id):
                if child.video_id in seen or child.distillation_execution_id is not None:
                    continue
                child_video = self._repository.get_video(child.video_id)
                if child_video is not None and child.state.value not in {"COMPLETED", "SKIPPED"}:
                    activity.append({"video_id": child_video.video_id, "title": child_video.title,
                                     "status": child.state.value})
                    seen.add(child.video_id)
        for source in self._repository.list_source_subscriptions():
            if source.processing_policy != "STANDARD_INTELLIGENCE" or not is_tracked(self._repository, source.source_id):
                continue
            for video in self._repository.list_source_videos(source.source_id, limit=100):
                if video.video_id not in seen and self._repository.latest_distillation_execution_for_video(video.video_id) is None and self._manual_content_source(video.video_id) is None:
                    activity.append({"video_id": video.video_id, "title": video.title, "status": "WAITING_CONTENT"})
                    seen.add(video.video_id)
        return activity

    def _video_dto_with_deep_analysis(self, video: VideoRecord) -> dict[str, object]:
        """Project a Content row with its truthful Deep Analysis availability.

        Deep Analysis stays a separate capability: this only reports whether the
        action is currently usable for that Content.  It never implies Summary
        or Evidence authority was changed.
        """

        if self._deep_analysis_service is None:
            projection = _video_dto(video,deep_analysis_status="UNAVAILABLE",deep_analysis_reason="Deep Analysis is unavailable.")
        else:
            status = self._deep_analysis_service.status(content_id=video.video_id)
            projection = _video_dto(video,deep_analysis_status=status.availability.value,deep_analysis_reason=status.reason)
        if video.provider in {"LOCAL", "BILIBILI"}:
            with self._repository._connect() as connection:
                source = verify_source(self._repository,connection,video.video_id)
                if source is None:
                    projection["processing_status"] = "SOURCE_UNAVAILABLE"
                else:
                    projection.update({"processing_status":source["status"],"filename":source["filename"],"media_kind":source["media_kind"],"format":source["format"],"imported_at":source["imported_at"],"source_language":source["language"],"duration_seconds":source["duration_seconds"]})
                    if video.provider == "BILIBILI" and self._data_root is not None:
                        artifact = self._repository.get_artifact(source["snapshot_artifact_id"])
                        if artifact is not None:
                            from youtube_intel.source_authority import read_managed
                            metadata = json.loads(read_managed(self._data_root, artifact.relative_path, maximum=256 * 1024))
                            projection.update(source_url=metadata["canonical_url"], channel_name=metadata["uploader_name"], uploader_id=metadata["uploader_id"], published_at=metadata["published_at"])
        if video.provider == "LOCAL" and self._transcription_jobs is not None and projection.get("media_kind") in {"AUDIO", "VIDEO"}:
            try:
                state = self._transcription_jobs.status(video.video_id)["status"]
                if state in {"RUNNING", "FAILED", "INTERRUPTED"}:
                    projection["processing_status"] = "TRANSCRIPTION_FAILED" if state == "FAILED" else state
            except OfflineError:
                projection["processing_status"] = "SOURCE_UNAVAILABLE"
        if video.provider == "YOUTUBE":
            retry_sources = tuple(source for source in self._repository.list_source_subscriptions()
                                  if source.enabled and source.source_type.value == "VIDEO_URL"
                                  and source.video_id == video.video_id)
            if retry_sources:
                projection["source_id"] = retry_sources[0].source_id
            job = self._repository.latest_content_job(video.video_id)
            projection["processing_job"] = None if job is None else {"status": job.status.value, "stage": job.target_stage.value if job.target_stage is not None else None, "retry_at": _timestamp(job.available_at), "error_code": job.last_error_code}
            projection["retry_allowed"] = not (job is not None and job.status.value == "FAILED_FINAL" and job.last_error_code in {"CAPABILITY_UNAVAILABLE", "TRUST_INTEGRITY_INVALID"})
            if job is not None and job.status.value in {"PENDING", "RUNNING", "RETRY_PENDING", "FAILED_FINAL"}:
                projection["processing_status"] = ("RETRY_REQUIRED" if retry_sources else "RETRY_PENDING") if job.status.value == "RETRY_PENDING" else "FAILED" if job.status.value == "FAILED_FINAL" else "READING_CAPTIONS" if job.target_stage is not None and job.target_stage.value == "TRANSCRIPT" else "FETCHING"
            elif self._repository.current_local_summary_pointer(video.video_id) is not None:
                summary = self._note_projection(video.video_id).get("v2")
                projection["processing_status"] = "ORGANIZED" if isinstance(summary, dict) and summary.get("status") == "AVAILABLE" else "NEEDS_ATTENTION"
            elif (video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
                  and self._repository.get_verified_timed_transcript(video_id=video.video_id) is None):
                projection["processing_status"] = "NEEDS_ATTENTION"
                projection["caption_timing_status"] = "UNAVAILABLE"
            source_ids = {source.source_id for source in retry_sources}
            source_runs = tuple(run for run in self._repository.list_source_runs()
                                if run.source_id in source_ids) if source_ids else ()
            active_source = any(run.state.value in {"QUEUED", "RUNNING"} for run in source_runs)
            latest_run = source_runs[-1] if source_runs else None
            if (not active_source and latest_run is not None
                    and latest_run.state.value == "NEEDS_ATTENTION"
                    and any(source.source_id == latest_run.source_id
                            and source.processing_policy.value == "DISCOVER_ONLY" for source in retry_sources)
                    and job is not None and job.status is JobStatus.SUCCEEDED
                    and video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
                    and self._repository.current_local_summary_pointer(video.video_id) is None
                    and self._repository.get_verified_timed_transcript(video_id=video.video_id) is not None):
                # Native caption authority already committed, but the ordinary
                # source check stopped before Summary. Offer that same command
                # again instead of presenting a settled failure as live work.
                projection["processing_status"] = "RETRY_REQUIRED"
                projection["summary_preparation_status"] = "NEEDS_ATTENTION"
            if (retry_sources and not active_source and job is not None
                    and job.status is JobStatus.PENDING and job.last_error_code is not None):
                # Global recovery can activate this retry without a Source Run
                # to drain it. Offer the normal check command; keep the job and
                # Backup safety state intact until that command executes it.
                projection["processing_status"] = "RETRY_REQUIRED"
            if active_source:
                projection["processing_status"] = "WAITING"
        if video.provider=='YOUTUBE' and self._tracked_content_retry is not None:
            try:
                projection['tracked_content_retry']=self._tracked_content_retry.status(video.video_id)
            except (RetryIntegrity,ValueError,OSError,sqlite3.Error):
                projection['tracked_content_retry']={'request':None,'retry_allowed':False,'expected_job_id':None,'error_code':'RETRY_INTEGRITY_INVALID'}
        return projection

    def _require_transcription(self) -> LocalTranscriptionJobs:
        with self._transcription_init_lock:
            if self._transcription_jobs is None:
                if self._data_root is None:
                    raise ApiError(HTTPStatus.CONFLICT, "LOCAL_STORAGE_UNAVAILABLE", "Local storage is unavailable.")
                self._transcription_jobs = LocalTranscriptionJobs(self._repository, self._data_root, now=self._now)
            return self._transcription_jobs

    def _transcription_route(self, method: str, route: str, body: bytes) -> tuple[int, dict[str, object]]:
        service = self._require_transcription()
        if route == "/api/v1/local/transcription/capability" and method == "GET":
            return HTTPStatus.OK, {"capability": service.capability()}
        if route == "/api/v1/local/transcription/refresh" and method == "POST":
            self._only_keys(self._body(body), set())
            service.refresh()
            return HTTPStatus.ACCEPTED, {"capability": service.capability()}
        if route == "/api/v1/local/transcription/model" and method == "PUT":
            data = self._body(body)
            self._only_keys(data, {"model_path"})
            path = data.get("model_path")
            if path is not None and not isinstance(path, str):
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "MODEL_INVALID", "Select a local MLX model directory.")
            service.configure(path)
            return HTTPStatus.ACCEPTED, {"capability": service.capability()}
        match = re.fullmatch(r"/api/v1/videos/([^/]+)/transcription", route)
        if match is not None:
            content_id = match[1]
            if method == "GET":
                return HTTPStatus.OK, {"transcription": service.status(content_id)}
            if method == "POST":
                data = self._body(body)
                self._only_keys(data, {"execution_identity"})
                identity = self._string(data, "execution_identity", required=True)
                return HTTPStatus.ACCEPTED, {"transcription": service.start(content_id, identity or "")}
        raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")

    def _obsidian_content_id(self, route: str) -> str:
        content_id = route.removeprefix("/api/v1/videos/").removesuffix("/deep-analysis/obsidian")
        if not content_id or "/" in content_id or self._repository.get_video(content_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Content was not found.")
        return content_id

    def _require_deep_analysis(self) -> DeepAnalysisService:
        if self._deep_analysis_service is None:
            raise ApiError(
                HTTPStatus.NOT_FOUND,
                "DEEP_ANALYSIS_UNAVAILABLE",
                "Deep Analysis is unavailable.",
            )
        return self._deep_analysis_service

    def handle_stream(self, path: str, stream: BinaryIO, length: int, *,
        cancelled: Callable[[], bool] | None = None) -> tuple[int, dict[str, object]]:
        with self._configuration_admission(urlparse(path).path.rstrip("/")):
            return self._handle_stream(path, stream, length, cancelled=cancelled)

    def _handle_stream(
        self, path: str, stream: BinaryIO, length: int,
        *, cancelled: Callable[[], bool] | None = None,
    ) -> tuple[int, dict[str, object]]:
        route = urlparse(path).path.rstrip("/")
        if self._backup_restore_service and self._backup_restore_service.restore_pending:
            raise ApiError(HTTPStatus.CONFLICT, "RESTORE_PENDING", "Restore is pending. Reopen after restart.")
        try:
            if route == "/api/v1/local/imports":
                if self._local_provider is None:
                    raise ApiError(HTTPStatus.CONFLICT, "LOCAL_STORAGE_UNAVAILABLE", "Local storage is unavailable.")
                query = parse_qs(urlparse(path).query, keep_blank_values=True, max_num_fields=3)
                names = query.get("filename", [])
                if set(query) != {"filename"} or len(names) != 1 or len(names[0]) > 1024:
                    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "LOCAL_INVALID_FILENAME", "Select a supported file.")
                imported = self._local_provider.import_stream(names[0], stream, length, cancelled=cancelled)
                return HTTPStatus.OK if imported.duplicate else HTTPStatus.CREATED, {"import": imported.as_dict()}
            if route == "/api/v1/backup-restore/restore/stage":
                staged = self._require_backup_restore().stage_restore_stream(stream, length, cancelled=cancelled)
                return HTTPStatus.OK, {"restore": {"restore_id": staged.restore_id, "archive_sha256": staged.archive_sha256, "preview": staged.preview}}
        except LocalImportError as error:
            raise ApiError(HTTPStatus.REQUEST_TIMEOUT if error.code == "LOCAL_IMPORT_TIMEOUT" else HTTPStatus.UNPROCESSABLE_ENTITY, error.code, "The selected file could not be imported.") from None
        except BackupRestoreError as error:
            raise ApiError(HTTPStatus.CONFLICT, "BACKUP_RESTORE_REJECTED", str(error)) from None
        raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Stream route is unavailable.")

    def backup_download(self, path: str) -> tuple[int, dict[str, str], bytes | Path] | None:
        if self._backup_restore_service is None:
            return None
        match = re.fullmatch(
            r"/api/v1/backup-restore/backups/([a-f0-9]{32})/download",
            urlparse(path).path.rstrip("/"),
        )
        if match is None:
            return None
        found = self._backup_restore_service.backup_download(match.group(1))
        if found is None:
            return int(HTTPStatus.NOT_FOUND), {"Content-Type": "application/json; charset=utf-8"}, b'{"error":{"message":"Backup was not found."}}'
        archive_path, file_name = found
        return int(HTTPStatus.OK), {
            "Content-Type": "application/zip",
            "Content-Disposition": f'attachment; filename="{file_name}"',
        }, archive_path

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
        if route == "/api/v1/settings/local-models":
            if self._model_settings is None:
                return {"connection": "UNAVAILABLE", "models": []}
            return self._model_settings.discovered_models()

        if route.startswith("/api/v1/videos/") and route.endswith("/deep-analysis/obsidian"):
            return {"publish": self._deep_analysis_publisher.status(content_id=self._obsidian_content_id(route))}
        if route == "/api/v1/knowledge-delta":
            return {"knowledge_delta": self._knowledge_delta_service.read().as_dict()}
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
            from .state import StateStoreError

            try:
                usage = self._repository.list_distillation_resource_usage()
            except StateStoreError as error:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "RESOURCE_USAGE_UNAVAILABLE",
                    "Resource usage history could not be safely verified.",
                ) from error
            return {
                "usage": [
                    _resource_usage_dto(item)
                    for item in usage
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
            return {"intelligence": self._intelligence_list(limit=100), "activity": self._intelligence_activity()}
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
            effective_policy, source_policy_revision = self._source_policy_service.policy_snapshot(source.source_id)
            return {
                "source": self._source_projection(source),
                "policy": _source_policy_dto(
                    effective_policy
                ),
                "policy_modes": {
                    "focus": "INHERIT" if source_policy_revision is None else source_policy_revision.focus_mode.value,
                    "ignore": "INHERIT" if source_policy_revision is None else source_policy_revision.ignore_mode.value,
                    "style": "INHERIT" if source_policy_revision is None else source_policy_revision.distillation_style_mode.value,
                },
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
                    self._video_dto_with_deep_analysis(video)
                    for video in self._repository.list_videos()
                ] + self._pending_content_work()
            }
        if route == "/api/v1/deep-analysis/capability":
            return {"capability": self._require_deep_analysis().capability_report()}
        if route.startswith("/api/v1/videos/") and route.endswith("/deep-analysis"):
            deep_analysis_service = self._require_deep_analysis()
            video_id = route.removeprefix("/api/v1/videos/").removesuffix(
                "/deep-analysis"
            )
            if not video_id or "/" in video_id:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                )
            if self._repository.get_video(video_id) is None:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Content was not found."
                )
            deep_analysis_state = deep_analysis_service.status(content_id=video_id)
            deep_analysis_read = deep_analysis_service.read(content_id=video_id)
            return {
                "deep_analysis": {
                    "status": deep_analysis_state.as_dict(),
                    "result": (
                        None
                        if deep_analysis_read is None
                        else deep_analysis_read.as_dict()
                    ),
                }
            }
        if route.startswith("/api/v1/videos/") and route.endswith("/evidence"):
            video_id = route.removeprefix("/api/v1/videos/").removesuffix(
                "/evidence"
            )
            if not video_id or "/" in video_id:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found."
                )
            return self._content_evidence_projection(video_id)
        if route.startswith("/api/v1/videos/"):
            video = self._repository.get_video(route.rsplit("/", 1)[1])
            if video is None:
                pending = next((item for item in self._pending_content_work() if item["video_id"] == route.rsplit("/", 1)[1]), None)
                if pending is not None:
                    return {"video": pending, "transcript": {"status": "NOT_AVAILABLE"}, "note": {"v2": {"status": "UNAVAILABLE"}}, "scoring": {"status": "NOT_AVAILABLE"}, "intelligence_result": self._distillation_execution_dto(None), "history": [], "cloud_intelligence_available": False}
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Video was not found."
                )
            manual_source = self._manual_content_source(video.video_id)
            return {
                "video": self._video_dto_with_deep_analysis(video),
                "scoring": self._scoring_projection(video.video_id),
                "transcript": self._transcript_projection(video.video_id),
                "note": self._note_projection(video.video_id),
                "intelligence_result": self._distillation_execution_dto(
                    self._repository.latest_distillation_execution_for_video(
                        video.video_id
                    )
                ),
                "manual_intelligence_eligible": manual_source is not None,
                "local_intelligence": self._content_local_intelligence_status(video.video_id, manual_source),
                "pending_synthesis_executions": self._pending_synthesis_executions(video.video_id),
                "waiting_model_executions": [
                    self._distillation_execution_dto(wait)
                    for wait in self._repository.list_waiting_model_executions_for_video(video.video_id)
                ],
                "cloud_intelligence_available": (
                    self._cloud_execution_enabled and video.provider == "YOUTUBE" and self._cloud_intelligence_qualified and self._cloud_credential_available
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
            local_model_status = (
                self._model_settings.runtime_status(self._runtime_model, self._runtime_model_digest)
                if self._model_settings is not None and self._runtime_model is not None and self._runtime_model_digest is not None
                else {"model": self._runtime_model, "status": "UNKNOWN"}
            )
            return {
                "processing_defaults": {
                    "policy": ProcessingPolicy.DISCOVER_ONLY.value,
                    "processing_mode": "ORGANIZE_CONTENT"
                },
                "general": {
                    "timezone": self._timezone,
                    "output_language": language.value,
                    "output_language_source": language.source,
                    "output_language_updated_at": _timestamp(language.updated_at),
                },
                "cloud_credential": {"configured": self._cloud_credential_available, "source": "ENVIRONMENT" if self._cloud_credential_available else "NONE"} if self._model_settings is None else self._model_settings.credential_status(),
                "cloud_execution_enabled": self._cloud_execution_enabled,
                "model_preference": {
                    "desired_provider": None
                    if preference is None
                    else preference.desired_provider,
                    "desired_model": None
                    if preference is None
                    else preference.desired_model,
                    "active_production_default": None,
                },
                "runtime_local_model": local_model_status,
                "local_intelligence": self._local_intelligence_status(),
                "content_processing": {"status": "READY", "method": "EXTRACTIVE_SOURCE", "requires_cloud": False},
                "providers": [
                    asdict(item) | ({"production_eligible": False,
                        "reason": "Cloud execution is disabled for this runtime; model qualification is unchanged."}
                        if not self._cloud_execution_enabled and item.provider == "moonshot" else {})
                    for item in provider_model_statuses(
                        None if preference is None else preference.desired_provider,
                        None if preference is None else preference.desired_model,
                        local_runtime_available=(local_model_status["status"] == "READY") if self._runtime_model else self._local_distillation_available,
                        moonshot_qualified=self._cloud_intelligence_qualified,
                        moonshot_credential_available=self._cloud_credential_available,
                    )
                ],
                "bilibili": _BILIBILI_CAPABILITY,
                "youtube": {"channel_following": {"available": self._source_tracking is not None and "YOUTUBE" in self._source_tracking.providers, "code": "PUBLIC_CHANNEL_FOLLOWING"}},
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
        provenance = []
        for evidence_id in verified.evidence_ids:
            evidence = self._repository.get_evidence(evidence_id)
            text = self._repository.resolve_verified_evidence_text(evidence_id)
            if evidence is None or text is None:
                continue
            content = self._repository.get_video(evidence.video_id)
            provenance.append({"evidence_id":evidence_id,"content_id":evidence.video_id,"provider":None if content is None else getattr(content,"provider","YOUTUBE"),"locator_type":getattr(text,"locator_type","TIMED_MEDIA"),"start_ms":text.start_ms,"end_ms":text.end_ms,"start_line":getattr(text,"start_line",None),"end_line":getattr(text,"end_line",None),"excerpt":text.excerpt})
        if provenance:
            projection["source_provenance"] = provenance
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
        target_language = self._output_language_service.effective().value
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
            translation = None
            if self._evidence_translation_service is not None and not source_matches_target(
                evidence.language, target_language
            ):
                translation = self._evidence_translation_service.read(
                    evidence_id=evidence_id,
                    target_language=target_language,
                )
            evidence_links.append(
                {
                    "evidence_id": evidence.evidence_id,
                    "artifact_id": evidence.artifact_id,
                    "start_ms": evidence.start_ms,
                    "end_ms": evidence.end_ms,
                    **({"locator_type": verified_text.locator_type,
                        "start_offset": verified_text.start_offset, "end_offset": verified_text.end_offset,
                        "start_line": verified_text.start_line, "end_line": verified_text.end_line}
                       if verified_text is not None and verified_text.locator_type == "TEXT_RANGE" else {}),
                    "language": evidence.language,
                    "lineage_kind": evidence.lineage_kind.value,
                    "role": evidence.role.value,
                    "original_excerpt": (
                        verified_text.excerpt
                        if verified_text is not None
                        else evidence.source_excerpt
                    ),
                    "translated_excerpt": (
                        None if translation is None else translation.translated_excerpt
                    ),
                    "translated_language": (
                        None if translation is None else translation.target_language
                    ),
                    "translation_target_language": target_language,
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
            "source_url": None if source is None or getattr(source, "provider", None) == "LOCAL" else source.canonical_url,
            "video_id": card.video_id,
            "video_title": None if video is None else video.title,
            "original_video_url": None if video is None or getattr(video, "provider", None) == "LOCAL" else video.source_url,
            "evidence_links": evidence_links,
            "preference_ids": list(card.preference_ids),
            "source_policy_revision_id": card.source_policy_revision_id,
        }
        return projection

    @staticmethod
    def _translation_route(route: str) -> tuple[str, str] | None:
        parts = route.split("/")
        if (
            len(parts) == 8
            and parts[1:4] == ["api", "v1", "intelligence"]
            and parts[5] == "evidence"
            and parts[7] == "translation"
            and all(parts[index] for index in (4, 6))
        ):
            return parts[4], parts[6]
        return None

    @staticmethod
    def _content_translation_route(route: str) -> tuple[str, str] | None:
        parts = route.split("/")
        if (
            len(parts) == 8
            and parts[1:4] == ["api", "v1", "videos"]
            and parts[5] == "evidence"
            and parts[7] == "translation"
            and all(parts[index] for index in (4, 6))
        ):
            return parts[4], parts[6]
        return None

    def _content_evidence_projection(self, video_id: str) -> dict[str, object]:
        video = self._repository.get_video(video_id)
        if video is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Video was not found.")
        target_language = self._output_language_service.effective().value
        evidence_cards: list[dict[str, object]] = []
        local_pairs = self._repository.get_verified_local_media_evidence(video_id) if video.provider in {"LOCAL", "BILIBILI"} else None
        local_verified = {} if local_pairs is None else {e.evidence_id: (e, verified) for e, verified in local_pairs}
        evidence_ids = self._repository.list_evidence_for_presentation(video_id) if local_pairs is None else tuple(local_verified)
        for evidence_id in evidence_ids:
            if local_pairs is None:
                evidence = self._repository.get_evidence(evidence_id)
                verified = self._repository.resolve_verified_evidence_text(evidence_id)
            else:
                evidence, verified = local_verified[evidence_id]
            if (
                evidence is None
                or evidence.video_id != video_id
                or verified is None
                or verified.video_id != video_id
                or verified.evidence_id != evidence_id
            ):
                continue
            translated_excerpt: str | None = None
            translated_language: str | None = None
            translation_status = "NOT_REQUIRED" if source_matches_target(
                evidence.language, target_language
            ) else "UNAVAILABLE"
            if (
                translation_status != "NOT_REQUIRED"
                and self._evidence_translation_service is not None
            ):
                try:
                    presentation = self._evidence_translation_service.read(
                        evidence_id=evidence_id,
                        target_language=target_language,
                    )
                except (IntegrityConflict, ValueError):
                    presentation = None
                if presentation is not None:
                    translated_excerpt = presentation.translated_excerpt
                    translated_language = presentation.target_language
                    translation_status = "AVAILABLE"
            evidence_cards.append(
                {
                    "evidence_id": evidence.evidence_id,
                    "artifact_id": evidence.artifact_id,
                    "lineage_kind": evidence.lineage_kind.value,
                    "role": evidence.role.value,
                    "source_language": evidence.language,
                    "language": evidence.language,
                    "original_excerpt": verified.excerpt,
                    "translated_excerpt": translated_excerpt,
                    "translated_language": translated_language,
                    "translation_target_language": target_language,
                    "translation_status": translation_status,
                    "start_ms": verified.start_ms,
                    "end_ms": verified.end_ms,
                    "locator_type": verified.locator_type,
                    "start_offset": verified.start_offset,
                    "end_offset": verified.end_offset,
                    "start_line": verified.start_line,
                    "end_line": verified.end_line,
                    "provider": video.provider,
                    "created_at": _timestamp(evidence.created_at),
                    "source_url": video.source_url,
                }
            )
        return {"evidence": evidence_cards}

    def _translate_content_evidence(
        self, *, video_id: str, evidence_id: str
    ) -> dict[str, object]:
        service = self._evidence_translation_service
        if service is None:
            raise ApiError(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "LOCAL_TRANSLATION_UNAVAILABLE",
                "The local Evidence translation path is not configured.",
            )
        if self._repository.get_video(video_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Video was not found.")
        if evidence_id not in self._repository.list_translatable_evidence_ids(
            video_id
        ):
            raise ApiError(
                HTTPStatus.NOT_FOUND,
                "EVIDENCE_NOT_AVAILABLE",
                "Available canonical Evidence was not found for this Content.",
            )
        verified = self._repository.resolve_verified_evidence_text(evidence_id)
        evidence = self._repository.get_evidence(evidence_id)
        if (
            verified is None
            or verified.video_id != video_id
            or evidence is None
            or evidence.video_id != video_id
        ):
            raise ApiError(
                HTTPStatus.CONFLICT,
                "EVIDENCE_TRANSLATION_INVALID",
                "The original Evidence is unavailable or no longer matches this Content.",
            )
        target_language = self._output_language_service.effective().value
        try:
            presentation = service.present(
                evidence_id=evidence_id,
                target_language=target_language,
            )
        except IntegrityConflict as error:
            raise ApiError(
                HTTPStatus.CONFLICT,
                "EVIDENCE_TRANSLATION_INVALID",
                "The Evidence translation could not be safely presented.",
            ) from error
        except ValueError as error:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "EVIDENCE_TRANSLATION_REJECTED",
                "The local translation failed Evidence validation.",
            ) from error
        except RuntimeError as error:
            raise ApiError(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "LOCAL_TRANSLATION_UNAVAILABLE",
                "The qualified local Evidence translation model is unavailable.",
            ) from error
        return {
            "evidence_id": evidence_id,
            "translated_excerpt": (
                None if presentation is None else presentation.translated_excerpt
            ),
            "translated_language": (
                None if presentation is None else presentation.target_language
            ),
            "translation_target_language": target_language,
            "translation_status": (
                "NOT_REQUIRED" if presentation is None else "AVAILABLE"
            ),
        }

    def _translate_presented_evidence(
        self, *, intelligence_id: str, evidence_id: str
    ) -> dict[str, object]:
        service = self._evidence_translation_service
        if service is None:
            raise ApiError(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "LOCAL_TRANSLATION_UNAVAILABLE",
                "The local Evidence translation path is not configured.",
            )
        try:
            card = self._intelligence_reader.read_current_card(intelligence_id)
        except IntelligenceReadRejected as error:
            raise ApiError(
                HTTPStatus.CONFLICT,
                "INTELLIGENCE_UNAVAILABLE",
                "Current Intelligence is unavailable for Evidence presentation.",
            ) from error
        if evidence_id not in card.verified.evidence_ids:
            raise ApiError(
                HTTPStatus.NOT_FOUND,
                "EVIDENCE_NOT_LINKED",
                "Evidence is not linked to this current Intelligence.",
            )
        target_language = self._output_language_service.effective().value
        try:
            presentation = service.present(
                evidence_id=evidence_id,
                target_language=target_language,
            )
        except IntegrityConflict as error:
            raise ApiError(
                HTTPStatus.CONFLICT,
                "EVIDENCE_TRANSLATION_INVALID",
                "The Evidence translation could not be safely presented.",
            ) from error
        except ValueError as error:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "EVIDENCE_TRANSLATION_REJECTED",
                "The local translation failed Evidence validation.",
            ) from error
        except RuntimeError as error:
            raise ApiError(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "LOCAL_TRANSLATION_UNAVAILABLE",
                "The qualified local Evidence translation model is unavailable.",
            ) from error
        return {
            "evidence_id": evidence_id,
            "translated_excerpt": (
                None
                if presentation is None
                else presentation.translated_excerpt
            ),
            "translated_language": (
                None if presentation is None else presentation.target_language
            ),
            "translation_target_language": target_language,
            "translation_status": (
                "NOT_REQUIRED" if presentation is None else "AVAILABLE"
            ),
        }

    def _source_projection(self, source: SourceSubscriptionRecord) -> dict[str, object]:
        """Project the best persisted public Source name without network lookup."""
        projection = _source_dto(source)
        projection["tracking"] = None if self._source_tracking is None else self._source_tracking.projection(source.source_id)
        with self._repository._connect() as connection:
            projection["tracking_parent_source_ids"] = [row[0] for row in connection.execute(
                "SELECT source_id FROM source_observations WHERE content_id=? AND enrollment='ENROLLED' ORDER BY source_id", (source.video_id,))] if source.video_id is not None else []
            candidates = tuple(row[0] for row in connection.execute(
                "SELECT DISTINCT i.intelligence_id FROM intelligences i JOIN intelligence_revision_evidence r ON r.revision_id=i.current_revision_id JOIN evidence e USING(evidence_id) JOIN source_video_links l ON l.video_id=e.video_id WHERE l.source_id=? LIMIT 100", (source.source_id,)))
        projection["insight_count"] = sum(self._intelligence_projection(identity).get("status") == "AVAILABLE" for identity in candidates)
        friendly_name = source.display_name
        if friendly_name is None:
            videos = self._repository.list_source_videos(source.source_id, limit=1)
            if videos:
                friendly_name = videos[0].title if source.video_id is not None else videos[0].channel_name
        projection["friendly_name"] = (
            friendly_name or (urlparse(source.canonical_url).path.split("/")[1] if "/@" in source.canonical_url else None) or source.channel_id or source.video_id
        )
        projection["needs_attention"] = source.source_type.value == "CHANNEL" and not projection["tracking"]
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
        video = self._repository.get_video(video_id)
        if video is not None and video.provider in {"LOCAL", "BILIBILI"}:
            with self._repository._connect() as connection:
                source = verify_source(self._repository, connection, video_id)
                if source is None:
                    return {"status":"UNAVAILABLE","code":f"{video.provider}_SOURCE_UNTRUSTED"}
                if source["status"] != "READY":
                    return {"status":source["status"],"code":source["status"]}
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
                    self._data_root, artifact, max_bytes=MAX_TEXT_BYTES if video is not None and video.provider in {"LOCAL", "BILIBILI"} else 1_000_000
                )
            if text is not None:
                return {
                    "status": "AVAILABLE",
                    **({"timed_segments": [{"start_ms": c.start_ms, "end_ms": c.end_ms, "text": c.text} for c in timed.cues]} if (timed := self._repository.get_verified_timed_transcript(video_id=video_id)) is not None else {}),
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

        local_pointer = self._repository.current_local_summary_pointer(video_id)
        analysis_reader = self._analysis_reader
        if local_pointer is not None:
            artifact = self._repository.get_artifact(local_pointer.artifact_id)
            if artifact is not None and artifact.provider == EXTRACTIVE_PROVIDER and self._data_root is not None:
                analysis_reader = ExtractiveSummaryService(self._repository,self._data_root).read
            if analysis_reader is None:
                return {
                    "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                    "v2": {"status": "UNAVAILABLE", "code": "CURRENT_SUMMARY_INVALID"},
                }
            try:
                outcome = analysis_reader(video_id, local_pointer.artifact_id)
            except LegacySummaryNotCurrentAuthority:
                # The stored Summary is readable but its citations are temporary
                # model-facing refs, so it is not current trusted authority.
                # Surface a truthful regeneration-required state; never render a
                # t*/m* ref as if it were an Evidence id.
                return {
                    "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                    "v2": {
                        "status": "UNAVAILABLE",
                        "code": "CURRENT_SUMMARY_LEGACY_REGENERATION_REQUIRED",
                    },
                }
            except (ValueError, OSError):
                outcome = None
            if not isinstance(outcome, AnalysisCompleted):
                return {
                    "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                    "v2": {"status": "UNAVAILABLE", "code": "CURRENT_SUMMARY_INVALID"},
                }
            result = outcome.result
            summary_language = local_pointer.output_language
            content = self._repository.get_video(video_id)
            if result.provider == EXTRACTIVE_PROVIDER:
                summary_language = "und" if content is None else content.default_language or "und"
            verified_refs = {item.evidence_id: self._repository.resolve_verified_evidence_text(item.evidence_id) for item in result.evidence} if content is not None and content.provider in {"LOCAL", "BILIBILI"} else {}
            timed_points = []
            for point in result.core_points:
                spans = [verified_refs[eid] for eid in point.evidence_ids if verified_refs.get(eid) is not None]
                if spans and all(span is not None and span.video_id == video_id and span.start_ms is not None and span.end_ms is not None for span in spans):
                    timed_points.append({"text": point.text, "start_seconds": min(span.start_ms for span in spans if span is not None and span.start_ms is not None) / 1000,
                                         "end_seconds": max(span.end_ms for span in spans if span is not None and span.end_ms is not None) / 1000,
                                         "evidence_ids": list(point.evidence_ids)})
            return {
                "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
                "v2": {
                    "status": "AVAILABLE",
                    "note_identity": f"analysis/{result.request_hash}/structured",
                    "result_identity": result.request_hash,
                    "language": summary_language,
                    "summary": result.one_sentence_summary,
                    "method": "SOURCE_EXCERPTS" if result.provider == EXTRACTIVE_PROVIDER else "MODEL_SUMMARY",
                    "core_points": [point.text for point in result.core_points],
                    "timestamped_key_points": timed_points,
                    "evidence_references": [
                        {
                            "evidence_id": item.evidence_id,
                            "source": item.source.value,
                            "excerpt": item.excerpt,
                            "start_seconds": None if (ref := verified_refs.get(item.evidence_id)) is None or ref.start_ms is None else ref.start_ms / 1000,
                            "end_seconds": None if ref is None or ref.end_ms is None else ref.end_ms / 1000,
                        }
                        for item in result.evidence
                    ],
                },
            }
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
            "processing_status": self._video_dto_with_deep_analysis(video)["processing_status"],
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


UPLOAD_IDLE_TIMEOUT_SECONDS = 120
_LOCAL_ORIGIN = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")


def serve_loopback(
    application: LocalApiApplication, *, port: int = 8765
) -> ThreadingHTTPServer:
    """Create, but do not start, a loopback-only server with mutation protection."""

    class DrainingHTTPServer(ThreadingHTTPServer):
        # server_close must join every accepted request before a new runtime
        # opens the same database/DATA. Daemon handlers are not joined by the
        # stdlib, including a status request still verifying Backup under EX.
        daemon_threads = False

    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            super().setup()
            # The existing stream idle bound also covers an incomplete request
            # line or JSON body, so draining cannot wait on an idle socket forever.
            self.connection.settimeout(UPLOAD_IDLE_TIMEOUT_SECONDS)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def _send(self, status: int, payload: dict[str, object]) -> None:
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(status, {"Content-Type": "application/json; charset=utf-8"}, encoded)

        def _send_bytes(
            self, status: int, headers: dict[str, str], encoded: bytes
        ) -> None:
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy", "default-src 'self'; connect-src 'self'"
            )
            self.end_headers()
            self.wfile.write(encoded)

        def _send_file(self, status: int, headers: dict[str, str], path: Path) -> None:
            with open_managed(path.parent, path.name, maximum=MAX_ARCHIVE_BYTES) as source:
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(os.fstat(source.fileno()).st_size))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                while chunk := source.read(IO_CHUNK_BYTES):
                    self.wfile.write(chunk)

        def _cancelled(self) -> bool:
            if select.select([self.connection], [], [], 0)[0]:
                return bool(self.connection.recv(1, socket.MSG_PEEK) == b"")
            return False

        def _handle(self) -> None:
            is_mutation = self.command not in {"GET", "HEAD"}
            origin = self.headers.get("Origin")
            native_route = urlparse(self.path).path.rstrip("/")
            is_native = native_route.startswith("/api/v1/local/native/") and native_route != "/api/v1/local/native/capability"
            if is_native:
                service = application._native_import
                if service is None:
                    self._send(HTTPStatus.NOT_FOUND, {"error": {"code": "LOCAL_NATIVE_PICKER_UNAVAILABLE", "message": "Native selection is unavailable."}})
                    return
                server_port = cast(ThreadingHTTPServer, self.server).server_port
                hosts = {urlparse(value).netloc for value in service.origins} | {f"127.0.0.1:{server_port}", f"localhost:{server_port}"}
                if origin not in service.origins or self.headers.get("Host") not in hosts or self.headers.get("X-YIA-Request") != "local-ui" or self.headers.get("Sec-Fetch-Site") not in {None, "same-origin"}:
                    self._send(HTTPStatus.FORBIDDEN, {"error": {"code": "LOCAL_NATIVE_ACCESS_REJECTED", "message": "Only the current local application can request native selection."}})
                    return
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
            if self.command == "GET":
                binary = application.backup_download(self.path)
                if binary is not None:
                    status, headers, binary_payload = binary
                    try:
                        if isinstance(binary_payload, Path):
                            self.connection.settimeout(UPLOAD_IDLE_TIMEOUT_SECONDS)
                            self._send_file(status, headers, binary_payload)
                        else:
                            self._send_bytes(status, headers, binary_payload)
                    except (OSError, ValueError):
                        self.close_connection = True
                    return
            length = 0
            is_local_import = False
            is_stage = False
            if is_mutation:
                if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) > 1:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": {"code": "INVALID_LENGTH", "message": "Use a single fixed request length."}})
                    return
                raw_length = self.headers.get("Content-Length", "0")
                if not raw_length.isdecimal():
                    self._send(HTTPStatus.BAD_REQUEST, {"error": {"code": "INVALID_LENGTH", "message": "Request size is invalid."}})
                    return
                length = int(raw_length)
                is_stage = self.command == "POST" and urlparse(self.path).path.rstrip("/") == "/api/v1/backup-restore/restore/stage"
                is_local_import = self.command == "POST" and urlparse(self.path).path.rstrip("/") == "/api/v1/local/imports"
                maximum = 4096 if is_native else MAX_ARCHIVE_BYTES if is_stage else MAX_MEDIA_BYTES if is_local_import else 2 * 1024 * 1024
                if is_local_import:
                    names=parse_qs(urlparse(self.path).query).get('filename',[])
                    if len(names)==1 and Path(safe_filename(names[0])).suffix.lower() in {'.txt','.md'}:
                        maximum=MAX_TEXT_BYTES
                if is_local_import and self.headers.get_content_type() != "application/octet-stream":
                    self._send(HTTPStatus.UNSUPPORTED_MEDIA_TYPE,{"error":{"code":"LOCAL_INVALID_CONTENT_TYPE","message":"Select a supported file."}})
                    return
                if length > maximum:
                    self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": {"code": "LOCAL_FILE_TOO_LARGE" if is_local_import else "REQUEST_TOO_LARGE", "message": "Request exceeds the supported size."}})
                    return
                if is_stage and self.headers.get_content_type() != "application/zip":
                    self._send(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": {"code": "INVALID_CONTENT_TYPE", "message": "Choose a ZIP backup archive."}})
                    return
            acquired = False
            if is_local_import:
                acquired=application._local_import_slot.acquire(blocking=False)
                if not acquired:
                    self._send(HTTPStatus.TOO_MANY_REQUESTS,{"error":{"code":"LOCAL_IMPORT_BUSY","message":"Another local import is processing. Try again shortly."}})
                    return
            staged_restore_id: str | None = None
            response_sent = False
            try:
                if is_native:
                    self.connection.settimeout(UPLOAD_IDLE_TIMEOUT_SECONDS)
                    native_body = self.rfile.read(length)
                    if len(native_body) != length:
                        raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_LENGTH", "Control request is incomplete.")
                    status, response_payload = application.native_request(self.command, native_route, native_body, origin or "")
                elif is_local_import or is_stage:
                    self.connection.settimeout(UPLOAD_IDLE_TIMEOUT_SECONDS)
                    status, response_payload = application.handle_stream(self.path, cast(BinaryIO, self.rfile), length, cancelled=self._cancelled)
                else:
                    request_body = self.rfile.read(length)
                    if len(request_body) != length:
                        raise ApiError(HTTPStatus.BAD_REQUEST, "INVALID_LENGTH", "Request upload is incomplete.")
                    status, response_payload = application.handle(self.command, self.path, request_body)
                if is_stage:
                    staged_restore = response_payload.get("restore")
                    if isinstance(staged_restore, dict) and isinstance(staged_restore.get("restore_id"), str):
                        staged_restore_id = staged_restore["restore_id"]
                    if self._cancelled():
                        self.close_connection = True
                        return
                restore = response_payload.get("restore")
                if response_payload.get("runtime_restart_required") is True or (
                    isinstance(restore, dict) and restore.get("restart_required") is True
                ):
                    # Persisted configuration and Restore must both restart even
                    # when acknowledgement is lost. shutdown runs off this handler;
                    # server_close later drains handlers before reconstruction.
                    threading.Timer(0.25, self.server.shutdown).start()
                self._send(status, response_payload)
                response_sent = True
            except ApiError as error:
                try:
                    self._send(error.status, _error_body(error))
                except OSError:
                    self.close_connection = True
            except (BrokenPipeError, ConnectionResetError):
                self.close_connection = True
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

            finally:
                if staged_restore_id is not None and not response_sent and application._backup_restore_service is not None:
                    application._backup_restore_service.cancel_restore(staged_restore_id)
                if acquired:
                    application._local_import_slot.release()

        do_GET = _handle
        do_POST = _handle
        do_PATCH = _handle
        do_PUT = _handle
        do_DELETE = _handle

    return DrainingHTTPServer(("127.0.0.1", port), Handler)
