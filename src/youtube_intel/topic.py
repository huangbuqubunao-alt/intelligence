"""Trusted Topic aggregation over legally readable Intelligence revisions.

Topics are navigation and accumulated context, never a second source of truth.
The only contribution admission path starts with ``AuthoritativeIntelligenceReader``;
the repository persists its exact opaque revision and Evidence identities.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
    VerifiedIntelligenceRead,
)
from youtube_intel.state import (
    EvidenceRole,
    IntelligenceClaimKind,
    IntelligenceState,
    SQLiteStateRepository,
    TopicAssociationKind,
    TopicCurrentState,
    TopicLifecycle,
    TopicMembershipRecord,
    TopicMembershipWrite,
    TopicRecord,
    TopicRelationKind,
    TopicTimelineEventKind,
    TopicTimelineEventRecord,
    TopicTimelineEventWrite,
)


class TopicReadRejected(ValueError):
    """A Topic cannot be projected as current trusted knowledge."""


@dataclass(frozen=True, slots=True)
class TopicContribution:
    membership_id: str
    intelligence_id: str
    revision_id: str
    evidence_ids: tuple[str, ...]
    association_kind: TopicAssociationKind
    claim_kind: IntelligenceClaimKind
    state: IntelligenceState
    available: bool


@dataclass(frozen=True, slots=True)
class TopicTimelineEvent:
    event_id: str
    event_kind: TopicTimelineEventKind
    state: TopicCurrentState
    dependency_revision_ids: tuple[str, ...]
    dependency_evidence_ids: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TopicRelation:
    topic_id: str
    related_topic_id: str
    relation: TopicRelationKind
    causal: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TopicRead:
    topic_id: str
    name: str
    pinned: bool
    lifecycle: TopicLifecycle
    merged_into_topic_id: str | None
    current_event_id: str | None
    current_state: TopicCurrentState
    independence: str
    contributions: tuple[TopicContribution, ...]
    timeline: tuple[TopicTimelineEvent, ...]
    relations: tuple[TopicRelation, ...]


class TopicApplicationService:
    """The narrow Topic command/read seam for TASK-023.

    A caller can name, pin, and navigate a Topic.  It cannot submit summary
    text, a revision ID, lifecycle, claim kind, Evidence IDs, confidence, or
    an arbitrary relation type as Topic truth.
    """

    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._reader = AuthoritativeIntelligenceReader(repository)
        self._now = now or (lambda: datetime.now(UTC))

    @staticmethod
    def _command_id(command_id: str) -> str:
        if not isinstance(command_id, str) or not command_id.strip() or command_id != command_id.strip() or len(command_id) > 240:
            raise ValueError("topic command identity is invalid")
        return command_id

    @staticmethod
    def _membership_id(topic_id: str, verified: VerifiedIntelligenceRead) -> str:
        value = "\0".join((topic_id, verified.intelligence_id, verified.revision_id))
        return "topic-membership:" + hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _event_id(membership_id: str, event_kind: TopicTimelineEventKind) -> str:
        value = "\0".join((membership_id, event_kind.value))
        return "topic-event:" + hashlib.sha256(value.encode("utf-8")).hexdigest()

    def create_topic(self, *, command_id: str, name: str) -> TopicRecord:
        command = self._command_id(command_id)
        return self._repository.create_topic(
            topic_id=f"topic:{command}", name=name, now=self._now()
        )

    def rename_topic(self, *, topic_id: str, name: str) -> TopicRecord:
        return self._repository.rename_topic(topic_id=topic_id, name=name, now=self._now())

    def set_pinned(self, *, topic_id: str, pinned: bool) -> TopicRecord:
        return self._repository.set_topic_pinned(
            topic_id=topic_id, pinned=pinned, now=self._now()
        )

    def _active_topic(self, topic_id: str) -> TopicRecord:
        topic = self._repository.get_topic(topic_id)
        if topic is None or topic.lifecycle is not TopicLifecycle.ACTIVE:
            raise ValueError("active topic does not exist")
        return topic

    def _verified_current(self, intelligence_id: str) -> VerifiedIntelligenceRead:
        try:
            return self._reader.read_current(intelligence_id)
        except IntelligenceReadRejected as error:
            raise TopicReadRejected("intelligence is not legally readable") from error

    @staticmethod
    def _event_kind(
        kind: TopicAssociationKind,
    ) -> TopicTimelineEventKind | None:
        return {
            TopicAssociationKind.NEW_INFORMATION: TopicTimelineEventKind.NEW_INFORMATION,
            TopicAssociationKind.NEW_EVIDENCE: TopicTimelineEventKind.NEW_EVIDENCE,
            TopicAssociationKind.CONTRADICTORY_INFORMATION: TopicTimelineEventKind.CONTRADICTION,
        }.get(kind)

    def associate_intelligence(
        self,
        *,
        topic_id: str,
        intelligence_id: str,
        kind: TopicAssociationKind,
    ) -> TopicMembershipRecord:
        """Associate only the exact current revision minted by the trusted reader."""

        self._active_topic(topic_id)
        if not isinstance(kind, TopicAssociationKind):
            raise ValueError("topic association kind must be finite")
        verified = self._verified_current(intelligence_id)
        membership_id = self._membership_id(topic_id, verified)
        existing = self._repository.get_topic_membership(membership_id)
        membership = self._repository.create_topic_membership(
            TopicMembershipWrite(
                membership_id=membership_id,
                topic_id=topic_id,
                intelligence_id=verified.intelligence_id,
                revision_id=verified.revision_id,
                association_kind=kind,
                source_claim_kind=verified.claim_kind,
                source_state=verified.state,
                evidence_ids=verified.evidence_ids,
            ),
            now=self._now(),
        )
        if existing is None:
            event_kind = self._event_kind(kind)
            if event_kind is not None:
                state = self._state_for_memberships(
                    self._repository.list_topic_memberships(topic_id)
                )
                event = self._repository.create_topic_timeline_event(
                    TopicTimelineEventWrite(
                        event_id=self._event_id(membership.membership_id, event_kind),
                        topic_id=topic_id,
                        event_kind=event_kind,
                        state=state,
                        membership_ids=(membership.membership_id,),
                    ),
                    now=self._now(),
                )
                self._repository.set_topic_current_event(
                    topic_id=topic_id, event_id=event.event_id, now=self._now()
                )
        return membership

    def _contribution(
        self, membership: TopicMembershipRecord
    ) -> TopicContribution:
        try:
            verified = self._reader.read_current(membership.intelligence_id)
        except IntelligenceReadRejected:
            return TopicContribution(
                membership_id=membership.membership_id,
                intelligence_id=membership.intelligence_id,
                revision_id=membership.revision_id,
                evidence_ids=membership.evidence_ids,
                association_kind=membership.association_kind,
                claim_kind=membership.source_claim_kind,
                state=membership.source_state,
                available=False,
            )
        if (
            verified.revision_id != membership.revision_id
            or verified.claim_kind is not membership.source_claim_kind
            or verified.state is not membership.source_state
            or verified.evidence_ids != membership.evidence_ids
        ):
            return TopicContribution(
                membership_id=membership.membership_id,
                intelligence_id=membership.intelligence_id,
                revision_id=membership.revision_id,
                evidence_ids=membership.evidence_ids,
                association_kind=membership.association_kind,
                claim_kind=membership.source_claim_kind,
                state=membership.source_state,
                available=False,
            )
        return TopicContribution(
            membership_id=membership.membership_id,
            intelligence_id=verified.intelligence_id,
            revision_id=verified.revision_id,
            evidence_ids=verified.evidence_ids,
            association_kind=membership.association_kind,
            claim_kind=verified.claim_kind,
            state=verified.state,
            available=True,
        )

    def _has_independent_evidence(self, membership: TopicMembershipRecord) -> bool:
        if membership.association_kind is not TopicAssociationKind.NEW_EVIDENCE:
            return False
        return any(
            (evidence := self._repository.get_evidence(evidence_id)) is not None
            and evidence.role is EvidenceRole.INDEPENDENT_VERIFICATION
            for evidence_id in membership.evidence_ids
        )

    def _state_for_memberships(
        self, memberships: tuple[TopicMembershipRecord, ...]
    ) -> TopicCurrentState:
        contributions = tuple(self._contribution(membership) for membership in memberships)
        active = tuple(
            (membership, contribution)
            for membership, contribution in zip(memberships, contributions, strict=True)
            if contribution.available
        )
        if not active:
            return TopicCurrentState.DEGRADED if memberships else TopicCurrentState.UNRESOLVED
        if any(
            contribution.association_kind is TopicAssociationKind.CONTRADICTORY_INFORMATION
            for _, contribution in active
        ):
            return TopicCurrentState.DISAGREEMENT
        if len(active) >= 2 and any(
            self._has_independent_evidence(membership) for membership, _ in active
        ):
            return TopicCurrentState.CONSENSUS
        return TopicCurrentState.UNRESOLVED

    def _timeline(
        self,
        events: tuple[TopicTimelineEventRecord, ...],
        memberships: dict[str, TopicMembershipRecord],
    ) -> tuple[TopicTimelineEvent, ...]:
        result: list[TopicTimelineEvent] = []
        for event in events:
            dependencies = tuple(memberships[membership_id] for membership_id in event.membership_ids)
            result.append(
                TopicTimelineEvent(
                    event_id=event.event_id,
                    event_kind=event.event_kind,
                    state=event.state,
                    dependency_revision_ids=tuple(
                        sorted({item.revision_id for item in dependencies})
                    ),
                    dependency_evidence_ids=tuple(
                        sorted(
                            {
                                evidence_id
                                for item in dependencies
                                for evidence_id in item.evidence_ids
                            }
                        )
                    ),
                    created_at=event.created_at,
                )
            )
        return tuple(result)

    def read_topic(self, topic_id: str) -> TopicRead:
        topic = self._repository.get_topic(topic_id)
        if topic is None:
            raise TopicReadRejected("topic does not exist")
        memberships = self._repository.list_topic_memberships(topic_id)
        membership_by_id = {item.membership_id: item for item in memberships}
        contributions = tuple(self._contribution(item) for item in memberships)
        contribution_by_id = {item.membership_id: item for item in contributions}
        events = self._repository.list_topic_timeline_events(topic_id)
        timeline = self._timeline(events, membership_by_id)
        current_event = next(
            (event for event in events if event.event_id == topic.current_event_id), None
        )
        if current_event is None:
            current_state = TopicCurrentState.UNRESOLVED
        elif any(
            not contribution_by_id[membership_id].available
            for membership_id in current_event.membership_ids
        ):
            current_state = TopicCurrentState.DEGRADED
        else:
            # An event is immutable audit history, not an independent truth
            # source.  Recompute the live state solely from reader-validated
            # memberships so a raw event row cannot mint consensus/disagreement.
            current_state = self._state_for_memberships(memberships)
        independence = (
            "KNOWN_INDEPENDENT"
            if any(
                contribution.available and self._has_independent_evidence(membership)
                for membership, contribution in zip(memberships, contributions, strict=True)
            )
            else "UNKNOWN"
        )
        relations = tuple(
            TopicRelation(
                topic_id=relation.topic_id,
                related_topic_id=relation.related_topic_id,
                relation=relation.relation,
                causal=False,
                created_at=relation.created_at,
            )
            for relation in self._repository.list_topic_relations(topic_id)
        )
        return TopicRead(
            topic_id=topic.topic_id,
            name=topic.name,
            pinned=topic.pinned,
            lifecycle=topic.lifecycle,
            merged_into_topic_id=topic.merged_into_topic_id,
            current_event_id=topic.current_event_id,
            current_state=current_state,
            independence=independence,
            contributions=contributions,
            timeline=timeline,
            relations=relations,
        )

    def relate_topics(
        self,
        topic_id: str,
        related_topic_id: str,
        *,
        relation: TopicRelationKind = TopicRelationKind.RELATED,
    ) -> TopicRelation:
        self._active_topic(topic_id)
        self._active_topic(related_topic_id)
        if relation is not TopicRelationKind.RELATED:
            raise ValueError("topic relation must be a finite navigational relation")
        stored = self._repository.create_topic_relation(
            topic_id=topic_id, related_topic_id=related_topic_id, now=self._now()
        )
        related = (
            stored.related_topic_id
            if stored.topic_id == topic_id
            else stored.topic_id
        )
        return TopicRelation(
            topic_id=topic_id,
            related_topic_id=related,
            relation=stored.relation,
            causal=False,
            created_at=stored.created_at,
        )

    def merge_topics(self, *, target_topic_id: str, source_topic_id: str) -> TopicRecord:
        self._active_topic(target_topic_id)
        self._active_topic(source_topic_id)
        if target_topic_id == source_topic_id:
            raise ValueError("topic merge requires different topics")
        for membership in self._repository.list_topic_memberships(source_topic_id):
            self.associate_intelligence(
                topic_id=target_topic_id,
                intelligence_id=membership.intelligence_id,
                kind=membership.association_kind,
            )
        return self._repository.mark_topic_merged(
            source_topic_id=source_topic_id, target_topic_id=target_topic_id, now=self._now()
        )

    def split_topic(
        self,
        *,
        source_topic_id: str,
        command_id: str,
        name: str,
        membership_ids: tuple[str, ...],
    ) -> TopicRecord:
        self._active_topic(source_topic_id)
        if not membership_ids or len(membership_ids) != len(set(membership_ids)):
            raise ValueError("topic split requires unique membership identities")
        source_members = {
            item.membership_id: item
            for item in self._repository.list_topic_memberships(source_topic_id)
        }
        if any(membership_id not in source_members for membership_id in membership_ids):
            raise ValueError("topic split membership does not belong to source topic")
        split = self.create_topic(command_id=command_id, name=name)
        for membership_id in membership_ids:
            membership = source_members[membership_id]
            self.associate_intelligence(
                topic_id=split.topic_id,
                intelligence_id=membership.intelligence_id,
                kind=membership.association_kind,
            )
        return split

    def affected_memberships(
        self, intelligence_id: str, revision_id: str
    ) -> tuple[TopicMembershipRecord, ...]:
        """Direct correction/deletion impact seam; historical records remain intact."""

        return self._repository.list_topic_memberships_for_revision(
            intelligence_id, revision_id
        )
