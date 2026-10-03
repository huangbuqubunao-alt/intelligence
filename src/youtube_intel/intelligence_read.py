"""Authoritative read boundary for persisted Intelligence.

Repository records are deliberately raw persistence.  Only this reader may
mint the sealed projection consumed by the local application layer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final, NoReturn

from youtube_intel.domain import Availability
from youtube_intel.state import (
    DependencyRelation,
    EvidenceAvailability,
    IntelligenceClaimKind,
    IntelligenceRevisionRecord,
    IntelligenceState,
    IntelligenceStateHistoryRecord,
    SQLiteStateRepository,
    StateStoreError,
)


class IntelligenceReadRejected(ValueError):
    """Persisted data does not satisfy the authoritative read contract."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


_MINT_SENTINEL: Final = object()


class VerifiedIntelligenceRead:
    """A sealed, validated revision read minted only by this module.

    Current consumers use read_current; recorded snapshots use the explicitly
    named read_recorded_card and must present the recorded state as historical.
    """

    __slots__ = (
        "_claim_kind",
        "_evidence_ids",
        "_intelligence_id",
        "_revision_id",
        "_sealed",
        "_state",
    )

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("VerifiedIntelligenceRead is final")

    def __init__(
        self,
        *,
        _sentinel: object | None = None,
        intelligence_id: str,
        revision_id: str,
        claim_kind: IntelligenceClaimKind,
        state: IntelligenceState,
        evidence_ids: tuple[str, ...],
    ) -> None:
        if _sentinel is not _MINT_SENTINEL:
            raise TypeError("VerifiedIntelligenceRead is minted by AuthoritativeIntelligenceReader")
        self._intelligence_id = intelligence_id
        self._revision_id = revision_id
        self._claim_kind = claim_kind
        self._state = state
        self._evidence_ids = evidence_ids
        self._sealed = True

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("VerifiedIntelligenceRead is immutable")
        object.__setattr__(self, name, value)

    @property
    def intelligence_id(self) -> str:
        return self._intelligence_id

    @property
    def revision_id(self) -> str:
        return self._revision_id

    @property
    def claim_kind(self) -> IntelligenceClaimKind:
        return self._claim_kind

    @property
    def state(self) -> IntelligenceState:
        return self._state

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return self._evidence_ids

    @property
    def is_confirmed(self) -> bool:
        return self._state is IntelligenceState.CONFIRMED

    def __copy__(self) -> None:
        raise TypeError("VerifiedIntelligenceRead cannot be copied")

    def __deepcopy__(self, memo: object) -> None:
        raise TypeError("VerifiedIntelligenceRead cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("VerifiedIntelligenceRead cannot be serialized")


@dataclass(frozen=True, slots=True)
class EvidenceRevisionImpact:
    intelligence_id: str
    revision_id: str
    is_current: bool


@dataclass(frozen=True, slots=True)
class EvidenceDependencyImpact:
    evidence_id: str
    revisions: tuple[EvidenceRevisionImpact, ...]


@dataclass(frozen=True, slots=True)
class IntelligenceCard:
    """A card projection reached only after the existing authoritative read."""

    verified: VerifiedIntelligenceRead
    source_id: str
    video_id: str
    core_conclusion: str
    user_relevant_information: tuple[str, ...]
    important_new_information: tuple[str, ...]
    meaningful_details: tuple[str, ...]
    filtered_noise: tuple[str, ...]
    preference_ids: tuple[str, ...]
    source_policy_revision_id: str | None


class AuthoritativeIntelligenceReader:
    """The sole validator and issuer of a current trusted Intelligence read."""

    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository

    def read_current(self, intelligence_id: str) -> VerifiedIntelligenceRead:
        try:
            return self._read_current(intelligence_id)
        except IntelligenceReadRejected:
            raise
        except (AttributeError, StateStoreError, ValueError) as error:
            raise IntelligenceReadRejected(
                "PERSISTENCE_INVALID", "intelligence persistence is invalid"
            ) from error

    def read_current_card(self, intelligence_id: str) -> IntelligenceCard:
        """Return persisted card content only after minting the trusted revision read."""

        return self._read_card(self.read_current(intelligence_id))

    def read_recorded_card(self, intelligence_id: str, revision_id: str) -> IntelligenceCard:
        """Reverify an admitted snapshot without relabeling its state as current.

        Research execution provenance may outlive a later Intelligence revision.
        This does not expose a History API or restore invalidated claims as current.
        """
        try:
            intelligence = self._repository.get_intelligence(intelligence_id)
            revisions = self._repository.list_intelligence_revisions(intelligence_id)
            revision = next((r for r in revisions if r.revision_id == revision_id), None)
            if revision is None or intelligence.current_revision_id is None:
                raise IntelligenceReadRejected("REVISION_INVALID", "recorded revision is unavailable")
            current = next((r for r in revisions if r.revision_id == intelligence.current_revision_id), None)
            if current is None or current.revision_number != max(r.revision_number for r in revisions):
                raise IntelligenceReadRejected("CURRENT_POINTER_INVALID", "current revision pointer is invalid")
            state = self._validate_history(revision, revisions)
            if revision.claim_kind is IntelligenceClaimKind.UNCLASSIFIED or state.state in {
                IntelligenceState.INVALIDATED, IntelligenceState.OVERTURNED,
            }:
                raise IntelligenceReadRejected("CURRENT_NOT_ACTIVE", "recorded revision was not active")
            evidence_ids = self._repository.list_intelligence_revision_evidence(revision_id)
            if not evidence_ids or state.evidence_id not in evidence_ids:
                raise IntelligenceReadRejected("EVIDENCE_MISSING", "recorded evidence is unavailable")
            self._validate_evidence_dependency_edges(revision_id, evidence_ids)
            self._validate_evidence(evidence_ids)
            verified = VerifiedIntelligenceRead(
                _sentinel=_MINT_SENTINEL, intelligence_id=intelligence_id, revision_id=revision_id,
                claim_kind=revision.claim_kind, state=state.state, evidence_ids=evidence_ids,
            )
            return self._read_card(verified)
        except IntelligenceReadRejected:
            raise
        except (AttributeError, StateStoreError, ValueError) as error:
            raise IntelligenceReadRejected("PERSISTENCE_INVALID", "recorded card is invalid") from error

    def _read_card(self, verified: VerifiedIntelligenceRead) -> IntelligenceCard:
        try:
            revision = self._repository.get_intelligence_revision(verified.revision_id)
            card = self._repository.get_distillation_card(verified.revision_id)
            if revision is None or card is None:
                raise IntelligenceReadRejected("CARD_MISSING", "distillation card is unavailable")
            evidence_records = tuple(
                self._repository.get_evidence(evidence_id)
                for evidence_id in verified.evidence_ids
            )
            if any(record is None or record.video_id != card.video_id for record in evidence_records):
                raise IntelligenceReadRejected("CARD_EVIDENCE_INVALID", "card evidence target is invalid")
            relations = self._repository.list_intelligence_revision_evidence_relations(
                verified.revision_id
            )
            if tuple(item.evidence_id for item in relations) != verified.evidence_ids:
                raise IntelligenceReadRejected(
                    "CARD_EVIDENCE_INVALID", "card evidence relation is invalid"
                )
            stance_presence = tuple(item.stance is not None for item in relations)
            if any(stance_presence) and not all(stance_presence):
                raise IntelligenceReadRejected(
                    "CARD_EVIDENCE_INVALID", "card evidence stance is incomplete"
                )
            if not self._repository.source_has_video(card.source_id, card.video_id):
                raise IntelligenceReadRejected("CARD_SOURCE_INVALID", "card source target is invalid")
            canonical_evidence: list[dict[str, int | str]] = []
            for evidence_id, evidence, relation in zip(
                verified.evidence_ids, evidence_records, relations, strict=True
            ):
                if evidence is None:
                    continue
                item: dict[str, int | str] = {
                    "evidence_id": evidence_id,
                    "start_ms": evidence.start_ms,
                    "end_ms": evidence.end_ms,
                }
                if relation.stance is not None:
                    item["stance"] = relation.stance.value
                canonical_evidence.append(item)
            canonical = json.dumps(
                {
                    "core_conclusion": card.core_conclusion,
                    "user_relevant_information": list(card.user_relevant_information),
                    "important_new_information": list(card.important_new_information),
                    "meaningful_details": list(card.meaningful_details),
                    "filtered_noise": list(card.filtered_noise),
                    "claim_kind": verified.claim_kind.value,
                    "evidence": canonical_evidence,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if hashlib.sha256(canonical).hexdigest() != revision.content_hash:
                raise IntelligenceReadRejected("CARD_HASH_INVALID", "distillation card content is invalid")
            return IntelligenceCard(
                verified=verified,
                source_id=card.source_id,
                video_id=card.video_id,
                core_conclusion=card.core_conclusion,
                user_relevant_information=card.user_relevant_information,
                important_new_information=card.important_new_information,
                meaningful_details=card.meaningful_details,
                filtered_noise=card.filtered_noise,
                preference_ids=card.preference_ids,
                source_policy_revision_id=card.source_policy_revision_id,
            )
        except IntelligenceReadRejected:
            raise
        except (AttributeError, StateStoreError, ValueError) as error:
            raise IntelligenceReadRejected(
                "PERSISTENCE_INVALID", "intelligence card persistence is invalid"
            ) from error

    def _read_current(self, intelligence_id: str) -> VerifiedIntelligenceRead:
        try:
            intelligence = self._repository.get_intelligence(intelligence_id)
        except (StateStoreError, ValueError) as error:
            raise IntelligenceReadRejected("INTELLIGENCE_NOT_FOUND", "intelligence does not exist") from error
        pointer = intelligence.current_revision_id
        if pointer is None:
            raise IntelligenceReadRejected("CURRENT_REVISION_MISSING", "current revision is missing")
        try:
            revisions = self._repository.list_intelligence_revisions(intelligence_id)
        except ValueError as error:
            raise IntelligenceReadRejected("REVISION_INVALID", "revision persistence is invalid") from error
        revision = next((item for item in revisions if item.revision_id == pointer), None)
        if revision is None or revision.intelligence_id != intelligence_id:
            raise IntelligenceReadRejected("CURRENT_POINTER_INVALID", "current revision pointer is invalid")
        if not revisions or revision.revision_number != max(item.revision_number for item in revisions):
            raise IntelligenceReadRejected("CURRENT_POINTER_REGRESSED", "current revision pointer regressed")
        if not isinstance(revision.claim_kind, IntelligenceClaimKind):
            raise IntelligenceReadRejected("CLAIM_KIND_INVALID", "claim classification is invalid")
        if revision.claim_kind is IntelligenceClaimKind.UNCLASSIFIED:
            raise IntelligenceReadRejected("CLAIM_KIND_UNCLASSIFIED", "claim classification is unclassified")
        state_event = self._validate_history(revision, revisions)
        evidence_ids = self._repository.list_intelligence_revision_evidence(revision.revision_id)
        if not evidence_ids:
            raise IntelligenceReadRejected("EVIDENCE_MISSING", "current revision has no evidence")
        if state_event.evidence_id not in evidence_ids:
            raise IntelligenceReadRejected("STATE_HISTORY_INVALID", "state history evidence is invalid")
        self._validate_evidence_dependency_edges(revision.revision_id, evidence_ids)
        self._validate_evidence(evidence_ids)
        if state_event.state in {
            IntelligenceState.INVALIDATED,
            IntelligenceState.OVERTURNED,
        }:
            raise IntelligenceReadRejected("CURRENT_NOT_ACTIVE", "current intelligence is not active")
        return VerifiedIntelligenceRead(
            _sentinel=_MINT_SENTINEL,
            intelligence_id=intelligence_id,
            revision_id=revision.revision_id,
            claim_kind=revision.claim_kind,
            state=state_event.state,
            evidence_ids=evidence_ids,
        )

    def impact_for_evidence(self, evidence_id: str) -> EvidenceDependencyImpact:
        try:
            if self._repository.get_evidence(evidence_id) is None:
                raise IntelligenceReadRejected("EVIDENCE_NOT_FOUND", "evidence does not exist")
            impacts: list[EvidenceRevisionImpact] = []
            for revision_id in self._repository.list_revision_ids_for_evidence(evidence_id):
                revision = self._repository.get_intelligence_revision(revision_id)
                if revision is None:
                    raise IntelligenceReadRejected("DEPENDENCY_INVALID", "evidence dependency is invalid")
                intelligence = self._repository.get_intelligence(revision.intelligence_id)
                impacts.append(
                    EvidenceRevisionImpact(
                        intelligence_id=revision.intelligence_id,
                        revision_id=revision.revision_id,
                        is_current=intelligence.current_revision_id == revision.revision_id,
                    )
                )
            return EvidenceDependencyImpact(evidence_id=evidence_id, revisions=tuple(impacts))
        except IntelligenceReadRejected:
            raise
        except (AttributeError, StateStoreError, ValueError) as error:
            raise IntelligenceReadRejected(
                "PERSISTENCE_INVALID", "intelligence persistence is invalid"
            ) from error

    def _validate_history(
        self, revision: IntelligenceRevisionRecord, revisions: tuple[IntelligenceRevisionRecord, ...]
    ) -> IntelligenceStateHistoryRecord:
        history = self._repository.list_intelligence_state_history(revision.intelligence_id)
        events = [item for item in history if item.revision_id == revision.revision_id]
        if len(events) != 1:
            raise IntelligenceReadRejected("STATE_HISTORY_INVALID", "current revision state history is invalid")
        event = events[0]
        if event.intelligence_id != revision.intelligence_id or not event.reason.strip():
            raise IntelligenceReadRejected("STATE_HISTORY_INVALID", "current revision state history is invalid")
        ordered = sorted(revisions, key=lambda item: item.revision_number)
        expected_ids = {record.revision_id for record in ordered}
        events_by_revision = {
            item.revision_id: item for item in history if item.revision_id in expected_ids
        }
        if len(history) != len(ordered) or len(events_by_revision) != len(ordered):
            raise IntelligenceReadRejected("STATE_HISTORY_INVALID", "revision state history is invalid")
        if ordered[0].prior_revision_id is not None:
            raise IntelligenceReadRejected("REVISION_HISTORY_INVALID", "revision history is invalid")
        first_event = events_by_revision[ordered[0].revision_id]
        if first_event.state is not IntelligenceState.NEW or first_event.prior_state is not None:
            raise IntelligenceReadRejected("STATE_HISTORY_INVALID", "revision state history is invalid")
        for prior, following in zip(ordered, ordered[1:]):
            if following.prior_revision_id != prior.revision_id:
                raise IntelligenceReadRejected("REVISION_HISTORY_INVALID", "revision history is invalid")
            following_event = events_by_revision[following.revision_id]
            if following_event.prior_state is not events_by_revision[prior.revision_id].state:
                raise IntelligenceReadRejected("STATE_HISTORY_INVALID", "revision state history is invalid")
        return event

    def _validate_evidence_dependency_edges(
        self, revision_id: str, evidence_ids: tuple[str, ...]
    ) -> None:
        """Validate the legacy structural Evidence dependency set.

        EVIDENCE_SUPPORT is an older schema name for dependency completeness. It
        is not the M4C semantic stance authority; stance is read exclusively
        from intelligence_revision_evidence.stance.
        """

        dependencies = {
            edge.input_evidence_id
            for edge in self._repository.list_dependency_edges_for_revision(revision_id)
            if edge.relation is DependencyRelation.EVIDENCE_SUPPORT
        }
        if dependencies != set(evidence_ids) or None in dependencies:
            raise IntelligenceReadRejected(
                "EVIDENCE_SUPPORT_INVALID", "evidence dependency set is incomplete"
            )

    def _validate_evidence(self, evidence_ids: tuple[str, ...]) -> None:
        for evidence_id in evidence_ids:
            evidence = self._repository.get_evidence(evidence_id)
            if evidence is None:
                raise IntelligenceReadRejected("EVIDENCE_MISSING", "evidence is missing")
            if evidence.availability is not EvidenceAvailability.AVAILABLE:
                raise IntelligenceReadRejected("EVIDENCE_UNAVAILABLE", "evidence is unavailable")
            artifact = self._repository.get_artifact(evidence.artifact_id)
            video = self._repository.get_video(evidence.video_id)
            if (
                artifact is None
                or artifact.deleted_at is not None
                or artifact.video_id != evidence.video_id
                or video is None
                or video.availability is not Availability.PUBLIC
            ):
                raise IntelligenceReadRejected("EVIDENCE_UNAVAILABLE", "evidence provenance is unavailable")
