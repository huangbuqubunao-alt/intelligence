"""Deterministic, immutable Weekly V1 Brief snapshots.

Weekly V1 is a presentation snapshot over trusted Intelligence and TASK-023
Topic memberships.  It is deliberately separate from legacy reports and the
frozen Weekly V2 artifact contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Sequence

from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
)
from youtube_intel.reporting import WeekPeriod, week_period_for
from youtube_intel.state import (
    EvidenceAvailability,
    IntelligenceClaimKind,
    PreferenceRecord,
    SQLiteStateRepository,
    TopicAssociationKind,
    TopicMembershipRecord,
    WeeklyBriefItemRecord,
    WeeklyBriefItemWrite,
    WeeklyBriefMarkerKind,
    WeeklyBriefMarkerRecord,
    WeeklyBriefMarkerWrite,
    WeeklyBriefPreferenceProjectionRecord,
    WeeklyBriefPreferenceProjectionWrite,
    WeeklyBriefRecord,
    WeeklyBriefStatus,
    WeeklyBriefWrite,
)


class WeeklyBriefError(ValueError):
    """Weekly V1 input or persisted history is outside its authority boundary."""


@dataclass(frozen=True, slots=True)
class WeeklyBriefMarker:
    marker_id: str
    kind: str
    reason: str
    current_revision_id: str | None
    evidence_id: str | None
    marked_at: datetime


@dataclass(frozen=True, slots=True)
class WeeklyBriefItem:
    brief_item_id: str
    topic_id: str
    topic_name: str
    intelligence_id: str
    revision_id: str
    association_kind: TopicAssociationKind
    claim_kind: IntelligenceClaimKind
    source_state: str
    summary: str
    evidence_ids: tuple[str, ...]
    markers: tuple[WeeklyBriefMarker, ...]


@dataclass(frozen=True, slots=True)
class WeeklyBrief:
    brief_id: str
    version: str
    logical_period_id: str
    timezone: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    finalized_at: datetime
    status: str
    no_important_information: bool
    preference_ids: tuple[str, ...]
    items: tuple[WeeklyBriefItem, ...]


@dataclass(frozen=True, slots=True)
class _Candidate:
    membership: TopicMembershipRecord
    topic_name: str
    summary: str
    source_content_hash: str
    preference_score: int


_PRIMARY_KINDS = {
    TopicAssociationKind.NEW_INFORMATION,
    TopicAssociationKind.NEW_EVIDENCE,
    TopicAssociationKind.CONTRADICTORY_INFORMATION,
}
_ASSOCIATION_PRIORITY = {
    TopicAssociationKind.CONTRADICTORY_INFORMATION: 0,
    TopicAssociationKind.NEW_EVIDENCE: 1,
    TopicAssociationKind.NEW_INFORMATION: 2,
}


class WeeklyBriefService:
    """Creates and reads explicit V1 Weekly snapshot authority only."""

    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        timezone: str,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(timezone, str) or not timezone.strip():
            raise ValueError("weekly timezone is invalid")
        self._repository = repository
        self._timezone = timezone
        self._now = now or (lambda: datetime.now(UTC))
        self._reader = AuthoritativeIntelligenceReader(repository)

    def finalize_week(self) -> WeeklyBrief:
        generated_at = self._now()
        period = week_period_for(generated_at, timezone=self._timezone)
        logical_period_id = self._logical_period_id(period)
        brief_id = "brief-v1:" + _sha256(logical_period_id)
        preferences = self._repository.list_active_preferences(now=generated_at)
        candidates = self._candidates(period, preferences)
        selected = self._deduplicate(candidates)
        ordered = tuple(
            sorted(
                selected,
                key=lambda candidate: (
                    -candidate.preference_score,
                    _ASSOCIATION_PRIORITY[candidate.membership.association_kind],
                    candidate.topic_name.casefold(),
                    candidate.membership.intelligence_id,
                    candidate.membership.revision_id,
                ),
            )
        )
        item_writes = tuple(
            WeeklyBriefItemWrite(
                brief_item_id=self._item_id(brief_id, candidate.membership.membership_id),
                membership_id=candidate.membership.membership_id,
                topic_id=candidate.membership.topic_id,
                topic_name=candidate.topic_name,
                intelligence_id=candidate.membership.intelligence_id,
                revision_id=candidate.membership.revision_id,
                association_kind=candidate.membership.association_kind,
                claim_kind=candidate.membership.source_claim_kind,
                source_state=candidate.membership.source_state,
                summary=candidate.summary,
                source_content_hash=candidate.source_content_hash,
                position=position,
                evidence_ids=candidate.membership.evidence_ids,
            )
            for position, candidate in enumerate(ordered, start=1)
        )
        preference_writes = tuple(
            WeeklyBriefPreferenceProjectionWrite(
                preference_id=preference.preference_id,
                horizon=preference.horizon,
                provenance=preference.provenance,
                statement_hash=_sha256(preference.statement),
            )
            for preference in preferences
        )
        self._repository.create_finalized_weekly_brief(
            WeeklyBriefWrite(
                brief_id=brief_id,
                logical_period_id=logical_period_id,
                timezone=period.timezone,
                period_start=period.start_utc,
                period_end=period.end_utc,
                no_important_information=not item_writes,
                preference_projection_hash=_projection_hash(preference_writes),
                generated_at=generated_at,
            ),
            items=item_writes,
            preferences=preference_writes,
        )
        return self.read(brief_id)

    def read(self, brief_id: str) -> WeeklyBrief:
        record = self._repository.get_weekly_v1_brief(brief_id)
        if record is None:
            raise WeeklyBriefError("Weekly V1 snapshot does not exist")
        if record.version != "weekly-v1" or record.status is not WeeklyBriefStatus.FINALIZED:
            raise WeeklyBriefError("Weekly V1 snapshot identity is invalid")
        items = tuple(self._read_item(item) for item in self._repository.list_weekly_v1_brief_items(brief_id))
        if record.no_important_information != (not items):
            raise WeeklyBriefError("Weekly V1 empty snapshot state is invalid")
        projections = self._repository.list_weekly_v1_preference_projections(brief_id)
        if record.preference_projection_hash != _projection_hash(projections):
            raise WeeklyBriefError("Weekly V1 preference provenance is invalid")
        return self._brief(record, items, tuple(item.preference_id for item in projections))

    def list_finalized(self) -> tuple[WeeklyBrief, ...]:
        return tuple(self.read(record.brief_id) for record in self._repository.list_weekly_v1_briefs())

    def append_correction_markers(self) -> int:
        appended = 0
        now = self._now()
        for item in self._repository.list_weekly_v1_items():
            try:
                current = self._reader.read_current(item.intelligence_id)
            except IntelligenceReadRejected:
                continue
            if current.revision_id == item.revision_id:
                continue
            if self._repository.append_weekly_v1_marker(
                WeeklyBriefMarkerWrite(
                    marker_id=self._marker_id(
                        item.brief_item_id,
                        WeeklyBriefMarkerKind.SUPERSEDED.value,
                        current.revision_id,
                    ),
                    brief_item_id=item.brief_item_id,
                    kind=WeeklyBriefMarkerKind.SUPERSEDED,
                    reason="A later trusted Intelligence revision supersedes this historical snapshot item.",
                    current_revision_id=current.revision_id,
                    evidence_id=None,
                ),
                now=now,
            ):
                appended += 1
        return appended

    def append_evidence_invalidation_markers(self, evidence_id: str) -> int:
        evidence = self._repository.get_evidence(evidence_id)
        if evidence is None or evidence.availability is EvidenceAvailability.AVAILABLE:
            raise WeeklyBriefError("evidence is not legally invalidated")
        kind = (
            WeeklyBriefMarkerKind.EVIDENCE_DELETED
            if evidence.availability is EvidenceAvailability.DELETED
            else WeeklyBriefMarkerKind.SOURCE_INVALIDATED
        )
        reason = (
            "Historical supporting evidence was later deleted."
            if kind is WeeklyBriefMarkerKind.EVIDENCE_DELETED
            else "Historical supporting evidence is no longer available."
        )
        appended = 0
        now = self._now()
        for item in self._repository.list_weekly_v1_items_for_evidence(evidence_id):
            if self._repository.append_weekly_v1_marker(
                WeeklyBriefMarkerWrite(
                    marker_id=self._marker_id(item.brief_item_id, kind.value, evidence_id),
                    brief_item_id=item.brief_item_id,
                    kind=kind,
                    reason=reason,
                    current_revision_id=None,
                    evidence_id=evidence_id,
                ),
                now=now,
            ):
                appended += 1
        return appended

    def _candidates(
        self, period: WeekPeriod, preferences: tuple[PreferenceRecord, ...]
    ) -> tuple[_Candidate, ...]:
        candidates: list[_Candidate] = []
        for membership in self._repository.list_topic_memberships_between(
            start=period.start_utc, end=period.end_utc
        ):
            if membership.association_kind not in _PRIMARY_KINDS:
                continue
            revision = self._repository.get_intelligence_revision(membership.revision_id)
            topic = self._repository.get_topic(membership.topic_id)
            if revision is None or topic is None or not period.contains(revision.created_at):
                continue
            try:
                card = self._reader.read_current_card(membership.intelligence_id)
            except IntelligenceReadRejected:
                continue
            verified = card.verified
            if (
                verified.revision_id != membership.revision_id
                or verified.claim_kind is not membership.source_claim_kind
                or verified.state is not membership.source_state
                or verified.evidence_ids != membership.evidence_ids
            ):
                continue
            candidates.append(
                _Candidate(
                    membership=membership,
                    topic_name=topic.name,
                    summary=card.core_conclusion,
                    source_content_hash=revision.content_hash,
                    preference_score=_preference_score(
                        preferences, topic.name, card.core_conclusion
                    ),
                )
            )
        return tuple(candidates)

    @staticmethod
    def _deduplicate(candidates: tuple[_Candidate, ...]) -> tuple[_Candidate, ...]:
        selected: dict[str, _Candidate] = {}
        for candidate in candidates:
            existing = selected.get(candidate.membership.topic_id)
            if existing is None or (
                _ASSOCIATION_PRIORITY[candidate.membership.association_kind],
                candidate.membership.effective_at,
                candidate.membership.revision_id,
            ) < (
                _ASSOCIATION_PRIORITY[existing.membership.association_kind],
                existing.membership.effective_at,
                existing.membership.revision_id,
            ):
                selected[candidate.membership.topic_id] = candidate
        return tuple(selected.values())

    def _read_item(self, item: WeeklyBriefItemRecord) -> WeeklyBriefItem:
        membership = self._repository.get_topic_membership(item.membership_id)
        revision = self._repository.get_intelligence_revision(item.revision_id)
        if (
            membership is None
            or revision is None
            or membership.topic_id != item.topic_id
            or membership.intelligence_id != item.intelligence_id
            or membership.revision_id != item.revision_id
            or membership.association_kind is not item.association_kind
            or membership.source_claim_kind is not item.claim_kind
            or membership.source_state is not item.source_state
            or membership.evidence_ids != item.evidence_ids
            or revision.content_hash != item.source_content_hash
            or self._repository.list_intelligence_revision_evidence(item.revision_id)
            != item.evidence_ids
        ):
            raise WeeklyBriefError("Weekly V1 item provenance is invalid")
        return WeeklyBriefItem(
            brief_item_id=item.brief_item_id,
            topic_id=item.topic_id,
            topic_name=item.topic_name,
            intelligence_id=item.intelligence_id,
            revision_id=item.revision_id,
            association_kind=item.association_kind,
            claim_kind=item.claim_kind,
            source_state=item.source_state.value,
            summary=item.summary,
            evidence_ids=item.evidence_ids,
            markers=tuple(
                self._marker(marker)
                for marker in self._repository.list_weekly_v1_markers(item.brief_item_id)
            ),
        )

    @staticmethod
    def _brief(
        record: WeeklyBriefRecord,
        items: tuple[WeeklyBriefItem, ...],
        preference_ids: tuple[str, ...],
    ) -> WeeklyBrief:
        return WeeklyBrief(
            brief_id=record.brief_id,
            version=record.version,
            logical_period_id=record.logical_period_id,
            timezone=record.timezone,
            period_start=record.period_start,
            period_end=record.period_end,
            generated_at=record.generated_at,
            finalized_at=record.finalized_at,
            status=record.status.value,
            no_important_information=record.no_important_information,
            preference_ids=preference_ids,
            items=items,
        )

    @staticmethod
    def _marker(record: WeeklyBriefMarkerRecord) -> WeeklyBriefMarker:
        return WeeklyBriefMarker(
            marker_id=record.marker_id,
            kind=record.kind.value,
            reason=record.reason,
            current_revision_id=record.current_revision_id,
            evidence_id=record.evidence_id,
            marked_at=record.marked_at,
        )

    @staticmethod
    def _logical_period_id(period: WeekPeriod) -> str:
        return (
            f"weekly-v1:{period.timezone}:{_utc_text(period.start_utc)}:"
            f"{_utc_text(period.end_utc)}"
        )

    @staticmethod
    def _item_id(brief_id: str, membership_id: str) -> str:
        return "brief-item-v1:" + _sha256(f"{brief_id}\0{membership_id}")

    @staticmethod
    def _marker_id(brief_item_id: str, kind: str, source_id: str) -> str:
        return "brief-marker-v1:" + _sha256(f"{brief_item_id}\0{kind}\0{source_id}")


def _projection_hash(
    projections: Sequence[
        WeeklyBriefPreferenceProjectionWrite | WeeklyBriefPreferenceProjectionRecord
    ],
) -> str:
    return _sha256(
        json.dumps(
            [
                {
                    "preference_id": projection.preference_id,
                    "horizon": projection.horizon.value,
                    "provenance": projection.provenance.value,
                    "statement_hash": projection.statement_hash,
                }
                for projection in projections
            ],
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def _preference_score(
    preferences: Sequence[PreferenceRecord], topic_name: str, summary: str
) -> int:
    haystack = set(re.findall(r"[a-z0-9]+", f"{topic_name} {summary}".casefold()))
    weights = {"EXPLICIT": 3, "TEMPORARY": 2, "DERIVED": 1}
    score = 0
    for preference in preferences:
        terms = set(re.findall(r"[a-z0-9]+", preference.statement.casefold()))
        if terms and terms <= haystack:
            score += weights[preference.provenance.value]
    return score


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise WeeklyBriefError("Weekly V1 timestamp must be UTC")
    return value.isoformat().replace("+00:00", "Z")


__all__ = [
    "WeeklyBrief",
    "WeeklyBriefError",
    "WeeklyBriefItem",
    "WeeklyBriefMarker",
    "WeeklyBriefService",
]
