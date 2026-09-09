"""Local Save intent; TASK-019 remains the only current Intelligence reader."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
    VerifiedIntelligenceRead,
)
from youtube_intel.state import SavedIntelligenceRecord, SQLiteStateRepository


def _validate_identity(value: str) -> None:
    if type(value) is not str or not value.strip() or len(value) > 512:
        raise ValueError("a bounded Intelligence identity is required")


@dataclass(frozen=True, slots=True, kw_only=True)
class SaveIntelligence:
    intelligence_id: str

    def __post_init__(self) -> None:
        _validate_identity(self.intelligence_id)


@dataclass(frozen=True, slots=True)
class UnsaveIntelligence:
    intelligence_id: str

    def __post_init__(self) -> None:
        _validate_identity(self.intelligence_id)


@dataclass(frozen=True, slots=True)
class SavedIntelligenceItem:
    """Read envelope, not a mintable trusted type; only verified is authority."""

    relation: SavedIntelligenceRecord
    verified: VerifiedIntelligenceRead | None
    unavailable_code: str | None


@dataclass(frozen=True, slots=True)
class SavedIntelligencePage:
    items: tuple[SavedIntelligenceItem, ...]
    next_cursor: SavedIntelligenceRecord | None


class SavedIntelligenceService:
    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._reader = AuthoritativeIntelligenceReader(repository)
        self._now = now or (lambda: datetime.now(UTC))

    def save(self, command: SaveIntelligence) -> SavedIntelligenceRecord:
        if type(command) is not SaveIntelligence:
            raise TypeError("SaveIntelligence command is required")
        _validate_identity(command.intelligence_id)
        verified = self._reader.read_current(command.intelligence_id)
        return self._repository.save_intelligence_relation(
            intelligence_id=verified.intelligence_id,
            now=self._now(),
            expected_revision_id=verified.revision_id,
        )

    def unsave(self, command: UnsaveIntelligence) -> None:
        if type(command) is not UnsaveIntelligence:
            raise TypeError("UnsaveIntelligence command is required")
        _validate_identity(command.intelligence_id)
        self._repository.unsave_intelligence_relation(command.intelligence_id)

    def list_saved(
        self, *, limit: int = 100, after: SavedIntelligenceRecord | None = None
    ) -> SavedIntelligencePage:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("saved page limit must be between 1 and 100")
        if after is not None:
            _validate_identity(after.intelligence_id)
        relations = self._repository.list_saved_intelligence_relations(
            limit=limit + 1, after=after
        )
        items = []
        for relation in relations[:limit]:
            try:
                verified = self._reader.read_current(relation.intelligence_id)
            except IntelligenceReadRejected as error:
                items.append(SavedIntelligenceItem(relation, None, error.code))
            else:
                items.append(SavedIntelligenceItem(relation, verified, None))
        return SavedIntelligencePage(
            tuple(items), relations[limit - 1] if len(relations) > limit else None
        )
