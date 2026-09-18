"""Persisted global output-language preference with config fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast

from youtube_intel.domain import ScoringOutputLanguage
from youtube_intel.state import GlobalUserSettingsRecord, SQLiteStateRepository


@dataclass(frozen=True, slots=True)
class EffectiveOutputLanguage:
    value: ScoringOutputLanguage
    source: str
    updated_at: datetime | None


class OutputLanguagePreferenceService:
    """One global V1 preference; historical artifacts keep their own language."""

    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        bootstrap_default: ScoringOutputLanguage,
    ) -> None:
        if bootstrap_default not in {"zh-CN", "en"}:
            raise ValueError("bootstrap output language is unsupported")
        self._repository = repository
        self._bootstrap_default = bootstrap_default

    def effective(self) -> EffectiveOutputLanguage:
        persisted = self._repository.get_global_user_settings()
        if persisted is None:
            return EffectiveOutputLanguage(
                value=self._bootstrap_default,
                source="BOOTSTRAP_DEFAULT",
                updated_at=None,
            )
        return self._from_record(persisted)

    def set(
        self, *, output_language: str, now: datetime
    ) -> EffectiveOutputLanguage:
        if output_language not in {"zh-CN", "en"}:
            raise ValueError("output language is unsupported")
        record = self._repository.save_global_output_language(
            output_language=output_language, now=now
        )
        return self._from_record(record)

    @staticmethod
    def _from_record(record: GlobalUserSettingsRecord) -> EffectiveOutputLanguage:
        if record.output_language not in {"zh-CN", "en"}:
            raise ValueError("persisted output language is unsupported")
        return EffectiveOutputLanguage(
            value=cast(ScoringOutputLanguage, record.output_language),
            source="USER_PREFERENCE",
            updated_at=record.updated_at,
        )
