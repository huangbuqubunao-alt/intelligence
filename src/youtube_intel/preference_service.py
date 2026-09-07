"""Narrow application-service commands for TASK-020 preference and feedback."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable

from youtube_intel.state import (
    FeedbackRecord,
    FeedbackWrite,
    PreferenceHorizon,
    PreferenceProvenance,
    PreferenceRecord,
    PreferenceScope,
    PreferenceState,
    PreferenceStateEventRecord,
    PreferenceWrite,
    SQLiteStateRepository,
)


class PreferenceApplicationService:
    """Keeps explicit commands, learned state, and raw feedback separate."""

    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._now = now or (lambda: datetime.now(UTC))

    @staticmethod
    def _command_preference_id(command_id: str) -> str:
        if not command_id.strip() or len(command_id) > 2000:
            raise ValueError("preference command identity is invalid")
        return f"preference:{command_id}"

    def _create(
        self,
        *,
        command_id: str,
        horizon: PreferenceHorizon,
        provenance: PreferenceProvenance,
        scope: PreferenceScope,
        target_id: str | None,
        statement: str,
        starts_at: datetime | None,
        expires_at: datetime | None,
    ) -> PreferenceRecord:
        preference_id = self._command_preference_id(command_id)
        return self._repository.create_preference(
            PreferenceWrite(
                preference_id=preference_id,
                horizon=horizon,
                provenance=provenance,
                scope=scope,
                target_id=target_id,
                statement=statement,
                starts_at=starts_at,
                expires_at=expires_at,
            ),
            activation_event_id=f"{preference_id}:activated",
            now=self._now(),
        )

    def set_explicit_long_term(
        self,
        *,
        command_id: str,
        scope: PreferenceScope,
        target_id: str | None,
        statement: str,
    ) -> PreferenceRecord:
        """Persist only a user-confirmed long-term preference command."""
        return self._create(
            command_id=command_id,
            horizon=PreferenceHorizon.LONG_TERM,
            provenance=PreferenceProvenance.EXPLICIT,
            scope=scope,
            target_id=target_id,
            statement=statement,
            starts_at=None,
            expires_at=None,
        )

    def record_derived_recent(
        self,
        *,
        command_id: str,
        scope: PreferenceScope,
        target_id: str | None,
        statement: str,
    ) -> PreferenceRecord:
        """Internal learning seam; no local API route can invoke this command."""
        return self._create(
            command_id=command_id,
            horizon=PreferenceHorizon.RECENT,
            provenance=PreferenceProvenance.DERIVED,
            scope=scope,
            target_id=target_id,
            statement=statement,
            starts_at=None,
            expires_at=None,
        )

    def set_temporary_focus(
        self,
        *,
        command_id: str,
        scope: PreferenceScope,
        target_id: str | None,
        statement: str,
        expires_at: datetime,
    ) -> PreferenceRecord:
        starts_at = self._now()
        return self._create(
            command_id=command_id,
            horizon=PreferenceHorizon.TEMPORARY_FOCUS,
            provenance=PreferenceProvenance.TEMPORARY,
            scope=scope,
            target_id=target_id,
            statement=statement,
            starts_at=starts_at,
            expires_at=expires_at,
        )

    def record_feedback(self, feedback: FeedbackWrite) -> FeedbackRecord:
        """Record an immutable event; it never mutates a preference or source policy."""
        return self._repository.record_feedback(feedback, now=self._now())

    def replace_explicit_long_term(
        self, *, command_id: str, preference_id: str, statement: str
    ) -> PreferenceRecord:
        prior = self._repository.get_preference(preference_id)
        if (
            prior is None
            or prior.horizon is not PreferenceHorizon.LONG_TERM
            or prior.provenance is not PreferenceProvenance.EXPLICIT
        ):
            raise ValueError("only an explicit long-term preference can be edited")
        replacement_id = self._command_preference_id(command_id)
        now = self._now()
        return self._repository.replace_preference(
            PreferenceWrite(
                preference_id=replacement_id,
                horizon=PreferenceHorizon.LONG_TERM,
                provenance=PreferenceProvenance.EXPLICIT,
                scope=prior.scope,
                target_id=prior.target_id,
                statement=statement,
                starts_at=None,
                expires_at=None,
                supersedes_preference_id=prior.preference_id,
            ),
            activation_event_id=f"{replacement_id}:activated",
            replacement_event_id=f"{replacement_id}:replaced:{prior.preference_id}",
            now=now,
        )

    def delete_preference(
        self, *, command_id: str, preference_id: str
    ) -> PreferenceStateEventRecord:
        if not command_id.strip() or len(command_id) > 2000:
            raise ValueError("preference command identity is invalid")
        return self._repository.retire_preference(
            preference_id=preference_id,
            state_event_id=f"preference:{command_id}:deleted:{preference_id}",
            state=PreferenceState.DELETED,
            now=self._now(),
        )

    def active_preferences(self, *, now: datetime | None = None) -> tuple[PreferenceRecord, ...]:
        return self._repository.list_active_preferences(now=self._now() if now is None else now)
