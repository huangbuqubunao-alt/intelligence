"""Backend-owned RC4 readiness projection for normal V1 Source Runs.

The projection deliberately combines finite existing authorities without
persisting a new readiness state.  Credentials remain outside the product; the
only credential fact accepted here is presence as determined by server-side
composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from youtube_intel.distillation import (
    DistillationCapabilityScope,
    ProviderProductionEligibility,
)
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.state import SourceSubscriptionRecord, SQLiteStateRepository


@dataclass(frozen=True, slots=True)
class BudgetReadiness:
    """A bounded snapshot from the configured production budget authority."""

    code: str
    limit: int | None
    used: int | None

    @classmethod
    def within_limit(cls, *, limit: int, used: int) -> BudgetReadiness:
        if limit <= 0 or used < 0 or used >= limit:
            raise ValueError("within-limit budget values are invalid")
        return cls("WITHIN_LIMIT", limit, used)

    @classmethod
    def limit_reached(cls, *, limit: int, used: int) -> BudgetReadiness:
        if limit < 0 or used < limit:
            raise ValueError("limit-reached budget values are invalid")
        return cls("LIMIT_REACHED", limit, used)

    @classmethod
    def status_unavailable(cls) -> BudgetReadiness:
        return cls("STATUS_UNAVAILABLE", None, None)


class BudgetReadinessAuthority(Protocol):
    def snapshot(self) -> BudgetReadiness: ...


def _dimension(code: str, label: str, message: str) -> dict[str, object]:
    return {"code": code, "label": label, "message": message}


class ProductionReadinessAuthority:
    """Project normal-production readiness from server-owned facts only."""

    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        runtime_enabled: bool,
        eligibility: ProviderProductionEligibility | None,
        credential_available: bool | None,
        budget: BudgetReadiness | BudgetReadinessAuthority,
    ) -> None:
        if type(runtime_enabled) is not bool:
            raise TypeError("runtime readiness must be backend-owned")
        if credential_available is not None and type(credential_available) is not bool:
            raise TypeError("credential readiness must be finite")
        if not isinstance(budget, BudgetReadiness) and not callable(
            getattr(budget, "snapshot", None)
        ):
            raise TypeError("budget readiness must use the bounded authority")
        self._repository = repository
        self._runtime_enabled = runtime_enabled
        self._eligibility = eligibility
        self._credential_available = credential_available
        self._budget = budget

    @classmethod
    def unconfigured(
        cls, repository: SQLiteStateRepository
    ) -> ProductionReadinessAuthority:
        return cls(
            repository,
            runtime_enabled=False,
            eligibility=None,
            credential_available=None,
            budget=BudgetReadiness.status_unavailable(),
        )

    def can_start(self, *, source_id: str) -> bool:
        overall = cast(dict[str, object], self.project(source_id=source_id)["overall"])
        return overall.get("code") == "READY"

    def project(self, *, source_id: str | None = None) -> dict[str, object]:
        source = self._source(source_id)
        source_dimension = self._source_dimension(source)
        model_dimension = self._model_dimension()
        processing_dimension = self._processing_dimension()
        credential_dimension = self._credential_dimension()
        budget_dimension = self._budget_dimension()
        overall = self._overall(
            processing=processing_dimension["code"],
            model=model_dimension["code"],
            credential=credential_dimension["code"],
            budget=budget_dimension["code"],
            source=source_dimension["code"],
        )
        return {
            "overall": overall,
            "application": _dimension(
                "CONNECTED",
                "Application connected",
                "The local application service is responding.",
            ),
            "video_distillation": processing_dimension,
            "model": model_dimension,
            "credential": credential_dimension,
            "budget": budget_dimension,
            "source": source_dimension,
            "deep_analysis": _dimension(
                "BLOCKED",
                "Deep Analysis unavailable",
                "This release supports normal Video Distillation only.",
            ),
        }

    def _source(self, source_id: str | None) -> SourceSubscriptionRecord | None:
        if source_id is not None:
            return self._repository.get_source_subscription(source_id)
        sources = self._repository.list_source_subscriptions()
        ready = next((item for item in sources if self._source_is_ready(item)), None)
        return ready or (sources[0] if sources else None)

    @staticmethod
    def _source_is_ready(source: SourceSubscriptionRecord) -> bool:
        return (
            source.enabled
            and source.processing_policy
            in {
                ProcessingPolicy.STANDARD_INTELLIGENCE,
                ProcessingPolicy.FULL_INTELLIGENCE,
            }
            and not (
                source.last_error_code is not None
                and "CONFIG" in source.last_error_code.upper()
            )
        )

    def _source_dimension(
        self, source: SourceSubscriptionRecord | None
    ) -> dict[str, object]:
        if source is None:
            return _dimension(
                "ADD_SOURCE",
                "Add a Source",
                "Add a YouTube Source before starting a manual check.",
            )
        if not source.enabled:
            return {
                **_dimension(
                    "DISABLED",
                    "Source disabled",
                    "Enable this Source before starting a manual check.",
                ),
                "source_id": source.source_id,
                "recovery": {
                    "action": "EDIT_SOURCE_CONFIGURATION",
                    "will_not": "The product will not enable this Source automatically.",
                },
            }
        if not self._source_is_ready(source):
            return {
                **_dimension(
                    "FIX_CONFIGURATION",
                    "Fix Source configuration",
                    "Choose a Video Distillation processing policy for this Source.",
                ),
                "source_id": source.source_id,
                "recovery": {
                    "action": "EDIT_SOURCE_CONFIGURATION",
                    "will_not": "The product will not change Source processing settings automatically.",
                },
            }
        return {
            **_dimension(
                "READY_FOR_MANUAL_CHECK",
                "Source ready for manual check",
                "This Source is enabled and configured for Video Distillation.",
            ),
            "source_id": source.source_id,
        }

    def _model_dimension(self) -> dict[str, object]:
        eligibility = self._eligibility
        if (
            eligibility is None
            or not eligibility._is_authoritative()
            or not eligibility.qualified
            or not eligibility.authorized
            or eligibility.capability_scope
            is not DistillationCapabilityScope.V1_VIDEO_DISTILLATION
        ):
            return _dimension(
                "NOT_APPROVED",
                "Video analysis model not approved",
                "The configured model is not approved for this capability.",
            )
        if not eligibility.available:
            return _dimension(
                "TEMPORARILY_UNAVAILABLE",
                "Video analysis model temporarily unavailable",
                "The approved Kimi model is not currently available through the configured production provider.",
            )
        return _dimension(
            "APPROVED",
            "Video analysis model approved",
            "The approved Kimi model is limited to V1 Video Distillation.",
        )

    def _processing_dimension(self) -> dict[str, object]:
        if not self._runtime_enabled:
            return _dimension(
                "SETUP_REQUIRED",
                "Source processing setup required",
                "Restart the supported local service with Video Distillation enabled.",
            )
        eligibility = self._eligibility
        if eligibility is None or not eligibility._is_authoritative():
            return _dimension(
                "SETUP_REQUIRED",
                "Source processing setup required",
                "No approved normal-production route is attached.",
            )
        if not eligibility.available:
            return {
                **_dimension(
                    "TEMPORARILY_UNAVAILABLE",
                    "Video Distillation temporarily unavailable",
                    "The configured production provider is not currently available.",
                ),
                "recovery": {
                    "action": "CHECK_READINESS",
                    "will_not": "The product will not switch provider or model, enable Deep Analysis, or retry a protected execution.",
                },
            }
        if not eligibility.production_eligible:
            return _dimension(
                "SETUP_REQUIRED",
                "Source processing setup required",
                "The configured route is not approved for normal Video Distillation.",
            )
        return _dimension(
            "READY_TO_START",
            "Video Distillation ready to start",
            "The normal production processing route is available.",
        )

    def _credential_dimension(self) -> dict[str, object]:
        if self._credential_available is None:
            return _dimension(
                "STATUS_UNAVAILABLE",
                "Credential status unavailable",
                "Start the supported production service to check credential presence.",
            )
        if not self._credential_available:
            return {
                **_dimension(
                    "SETUP_REQUIRED",
                    "NVIDIA credential setup required",
                    "On your Mac, make NVIDIA_API_KEY available to the Terminal session that starts the local service, then restart it. Use your approved password manager or environment setup; never add the key to project files or enter it in this browser.",
                ),
                "recovery": {
                    "action": "VIEW_SETUP_INSTRUCTIONS",
                    "will_not": "The product will not store the key or call the model just to check presence.",
                },
            }
        return _dimension(
            "AVAILABLE",
            "NVIDIA credential available",
            "The server detected credential presence. Provider success is not guaranteed.",
        )

    def _budget_dimension(self) -> dict[str, object]:
        budget = (
            self._budget
            if isinstance(self._budget, BudgetReadiness)
            else self._budget.snapshot()
        )
        if budget.code == "WITHIN_LIMIT":
            return {
                **_dimension(
                    "WITHIN_LIMIT",
                    "Within current usage limit",
                    "The configured call limit has remaining capacity.",
                ),
                "limit": budget.limit,
                "used": budget.used,
            }
        if budget.code == "LIMIT_REACHED":
            return {
                **_dimension(
                    "LIMIT_REACHED",
                    "Usage limit reached",
                    "Execution is blocked until you explicitly review the usage limit.",
                ),
                "limit": budget.limit,
                "used": budget.used,
                "recovery": {
                    "action": "VIEW_USAGE",
                    "will_not": "The product will not increase the limit or authorize spending automatically.",
                },
            }
        return _dimension(
            "STATUS_UNAVAILABLE",
            "Usage limit status unavailable",
            "The supported production service is required to check the usage limit.",
        )

    @staticmethod
    def _overall(
        *,
        processing: object,
        model: object,
        credential: object,
        budget: object,
        source: object,
    ) -> dict[str, object]:
        if budget == "LIMIT_REACHED":
            return _dimension(
                "BUDGET_BLOCKED",
                "Review usage limit",
                "The current usage limit is blocking a Source Run.",
            )
        if processing == "TEMPORARILY_UNAVAILABLE":
            return _dimension(
                "TEMPORARILY_UNAVAILABLE",
                "Temporarily unavailable",
                "Video Distillation cannot run with the configured provider right now.",
            )
        if (
            processing == "READY_TO_START"
            and model == "APPROVED"
            and credential == "AVAILABLE"
            and budget == "WITHIN_LIMIT"
            and source == "READY_FOR_MANUAL_CHECK"
        ):
            return _dimension(
                "READY",
                "Ready to check a Source",
                "All required normal Video Distillation prerequisites are available.",
            )
        return _dimension(
            "SETUP_REQUIRED",
            "Setup required",
            "Review the prerequisite details before checking this Source.",
        )


__all__ = [
    "BudgetReadiness",
    "BudgetReadinessAuthority",
    "ProductionReadinessAuthority",
]
