"""Persisted, fail-closed Evidence translation presentation service."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Callable, Protocol

from youtube_intel.state import (
    EvidenceAvailability,
    EvidenceTranslationPresentationRecord,
    EvidenceTranslationPresentationWrite,
    IntegrityConflict,
    SQLiteStateRepository,
)

TARGET_LANGUAGES = frozenset({"zh-CN", "en"})
TRANSLATION_PROVIDER = "ollama"
TRANSLATION_MODEL = "qwen3:8b"
TRANSLATION_MODEL_DIGEST = (
    "sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
)
TRANSLATION_PROMPT_VERSION = "evidence-translation-v1"
TRANSLATION_SCHEMA_VERSION = "evidence-translation-schema-v1"
MAX_EVIDENCE_EXCERPT_CHARS = 4000


class EvidenceTranslator(Protocol):
    provider: str
    model: str
    model_digest: str
    prompt_version: str
    schema_version: str

    def translate(
        self, *, excerpt: str, source_language: str, target_language: str
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class TranslationSource:
    evidence_id: str
    excerpt: str
    excerpt_hash: str
    source_language: str


def source_matches_target(source_language: str, target_language: str) -> bool:
    """Match only explicit source language tags; never inspect generated text."""
    source = source_language.strip().replace("_", "-").casefold()
    if target_language == "en":
        return source == "en" or source.startswith("en-")
    if target_language == "zh-CN":
        return source in {"zh-cn", "zh-hans", "zh-hans-cn"}
    return False


def _text_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def validate_translation(
    *, excerpt: str, translated_excerpt: str, target_language: str
) -> str:
    """Apply bounded V1 semantic checks before persistence or presentation."""
    translated = translated_excerpt.strip()
    if not translated or len(translated) > MAX_EVIDENCE_EXCERPT_CHARS:
        raise ValueError("translated excerpt is empty or exceeds 4000 characters")
    if target_language not in TARGET_LANGUAGES:
        raise ValueError("translation target language is unsupported")
    if target_language == "zh-CN" and not re.search(r"[\u3400-\u9fff]", translated):
        raise ValueError("translation does not contain Chinese text")
    if target_language == "en" and not re.search(r"[A-Za-z]", translated):
        raise ValueError("translation does not contain English text")

    source_numbers = Counter(re.findall(r"\d+(?:[.,]\d+)*(?:%|°)?", excerpt))
    translated_numbers = Counter(
        re.findall(r"\d+(?:[.,]\d+)*(?:%|°)?", translated)
    )
    if source_numbers != translated_numbers:
        raise ValueError("translation changed or omitted a numeric value")

    source_identifiers = set(
        re.findall(r"\b(?:[A-Z]{2,}[A-Z0-9.-]*|[A-Z][A-Za-z]*-\d+[A-Za-z0-9.-]*)\b", excerpt)
    )
    missing_identifiers = source_identifiers - set(
        re.findall(
            r"\b(?:[A-Z]{2,}[A-Z0-9.-]*|[A-Z][A-Za-z]*-\d+[A-Za-z0-9.-]*)\b",
            translated,
        )
    )
    if missing_identifiers:
        raise ValueError("translation changed or omitted a source acronym or named identifier")

    if target_language == "zh-CN":
        if re.search(r"\b(?:not|no|never|cannot|can't|without|neither)\b", excerpt, re.I) and not re.search(
            r"不|没|未|无|非|从未", translated
        ):
            raise ValueError("translation did not preserve source negation")
        if re.search(
            r"\b(?:may|might|could|likely|possible|probably|perhaps|uncertain|seems?)\b",
            excerpt,
            re.I,
        ) and not re.search(r"可能|或许|也许|不确定|似乎|大概", translated):
            raise ValueError("translation did not preserve source uncertainty")
    return translated


class EvidenceTranslationPresentationService:
    """Generate explicitly, then read only validated persisted presentation."""

    def __init__(
        self,
        repository: SQLiteStateRepository,
        translator: EvidenceTranslator,
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._translator = translator
        self._now = now

    def present(
        self, *, evidence_id: str, target_language: str
    ) -> EvidenceTranslationPresentationRecord | None:
        if target_language not in TARGET_LANGUAGES:
            raise ValueError("translation target language is unsupported")
        source = self._source(evidence_id)
        if source_matches_target(source.source_language, target_language):
            return None
        existing = self._repository.get_evidence_translation_presentation(
            evidence_id, target_language
        )
        if existing is not None:
            if not self._valid(existing, source, target_language):
                raise IntegrityConflict("persisted Evidence translation is invalid")
            return existing

        metadata = (
            self._translator.provider,
            self._translator.model,
            self._translator.model_digest,
            self._translator.prompt_version,
            self._translator.schema_version,
        )
        if metadata != (
            TRANSLATION_PROVIDER,
            TRANSLATION_MODEL,
            TRANSLATION_MODEL_DIGEST,
            TRANSLATION_PROMPT_VERSION,
            TRANSLATION_SCHEMA_VERSION,
        ):
            raise ValueError("Evidence translation provider provenance is unqualified")
        translated_excerpt = validate_translation(
            excerpt=source.excerpt,
            translated_excerpt=self._translator.translate(
                excerpt=source.excerpt,
                source_language=source.source_language,
                target_language=target_language,
            ),
            target_language=target_language,
        )

        write = EvidenceTranslationPresentationWrite(
            evidence_id=evidence_id,
            source_excerpt_hash=source.excerpt_hash,
            source_language=source.source_language,
            target_language=target_language,
            translated_excerpt=translated_excerpt,
            translated_excerpt_hash=_text_hash(translated_excerpt),
            provider=self._translator.provider,
            model=self._translator.model,
            model_digest=self._translator.model_digest,
            prompt_version=self._translator.prompt_version,
            schema_version=self._translator.schema_version,
        )
        try:
            saved = self._repository.create_evidence_translation_presentation(
                write, now=self._now()
            )
        except IntegrityConflict:
            # An overlapping explicit request may have won the unique insert.
            current = self._repository.get_evidence_translation_presentation(
                evidence_id, target_language
            )
            if current is None or not self._valid(current, source, target_language):
                raise
            saved = current
        if not self._valid(saved, source, target_language):
            raise IntegrityConflict("saved Evidence translation failed validation")
        return saved

    def read(
        self, *, evidence_id: str, target_language: str
    ) -> EvidenceTranslationPresentationRecord | None:
        if target_language not in TARGET_LANGUAGES:
            return None
        try:
            source = self._source(evidence_id)
            if source_matches_target(source.source_language, target_language):
                return None
            presentation = self._repository.get_evidence_translation_presentation(
                evidence_id, target_language
            )
            if presentation is None or not self._valid(
                presentation, source, target_language
            ):
                return None
            return presentation
        except (IntegrityConflict, ValueError, OverflowError):
            return None

    def _source(self, evidence_id: str) -> TranslationSource:
        evidence = self._repository.get_evidence(evidence_id)
        verified = self._repository.resolve_verified_evidence_text(evidence_id)
        if (
            evidence is None
            or evidence.availability is not EvidenceAvailability.AVAILABLE
            or verified is None
            or verified.evidence_id != evidence_id
            or len(verified.excerpt) > MAX_EVIDENCE_EXCERPT_CHARS
            or not evidence.language.strip()
        ):
            raise ValueError("Evidence original excerpt is unavailable or unverified")
        return TranslationSource(
            evidence_id=evidence_id,
            excerpt=verified.excerpt,
            excerpt_hash=verified.excerpt_hash,
            source_language=evidence.language,
        )

    @staticmethod
    def _valid(
        record: EvidenceTranslationPresentationRecord,
        source: TranslationSource,
        target_language: str,
    ) -> bool:
        try:
            translated = validate_translation(
                excerpt=source.excerpt,
                translated_excerpt=record.translated_excerpt,
                target_language=target_language,
            )
        except ValueError:
            return False
        return (
            record.evidence_id == source.evidence_id
            and record.source_excerpt_hash == source.excerpt_hash
            and record.source_language == source.source_language
            and record.target_language == target_language
            and record.translated_excerpt == translated
            and record.translated_excerpt_hash == _text_hash(record.translated_excerpt)
            and record.provider == TRANSLATION_PROVIDER
            and record.model == TRANSLATION_MODEL
            and record.model_digest == TRANSLATION_MODEL_DIGEST
            and record.prompt_version == TRANSLATION_PROMPT_VERSION
            and record.schema_version == TRANSLATION_SCHEMA_VERSION
        )
