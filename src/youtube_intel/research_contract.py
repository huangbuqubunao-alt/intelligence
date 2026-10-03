"""Research Lite v1: explicit local Content scope and source-owned findings."""

from __future__ import annotations

import hashlib
import json
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACT: Final[Literal["research-lite-v1"]] = "research-lite-v1"
MAX_CONTENT = 20
MAX_EVIDENCE = 24
MAX_INTELLIGENCE = 6
CANDIDATE_LIMIT = 100
ResearchUnresolved = Literal["NO_SYNTHESIS", "LEXICAL_RETRIEVAL", "BOUNDED_PACKET", "NO_MATCHING_EVIDENCE"]


class ResearchValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ResearchRequest(ResearchValue):
    question: str = Field(max_length=2000)
    content_ids: list[str] = Field(min_length=1, max_length=MAX_CONTENT)

    @field_validator("question")
    @classmethod
    def question_text(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("invalid research question")
        # Retain internal whitespace and exact case: no semantic rewriting.
        return value

    @field_validator("content_ids")
    @classmethod
    def bounded_content(cls, values: list[str]) -> list[str]:
        if any(not v or v != v.strip() or len(v) > 256 or any(ord(c) < 32 for c in v) for v in values):
            raise ValueError("invalid content scope")
        return sorted(set(values))


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def semantic_identity(request: ResearchRequest, output_language: str) -> str:
    if output_language not in {"en", "zh-CN"}:
        raise ValueError("unsupported output language")
    return digest({"contract": CONTRACT, **request.model_dump(), "output_language": output_language})


class ResearchContent(ResearchValue):
    content_id: str
    title: str | None


class ResearchEvidence(ResearchValue):
    evidence_id: str
    content_id: str
    artifact_id: str
    excerpt: str = Field(min_length=1, max_length=4000)
    excerpt_hash: str
    timed_transcript_hash: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    source_language: str
    lineage_kind: Literal["ORIGINAL_TRANSCRIPT", "EXTRACTION"]
    role: str
    created_at: str


class ResearchIntelligence(ResearchValue):
    intelligence_id: str
    revision_id: str
    content_id: str
    source_id: str
    conclusion: str = Field(max_length=4000)
    claim_kind: str
    state: str
    evidence_ids: list[str] = Field(min_length=1, max_length=MAX_EVIDENCE)
    stances: list[str | None]


class ResearchPacket(ResearchValue):
    contract: Literal["research-lite-v1"] = CONTRACT
    research_id: str
    execution_id: str
    execution_number: int = Field(ge=1)
    question: str
    output_language: Literal["zh-CN", "en"]
    assembled_at: str
    scope_kind: Literal["SELECTED_CONTENT"] = "SELECTED_CONTENT"
    scope: list[ResearchContent] = Field(min_length=1, max_length=MAX_CONTENT)
    assembly_status: Literal["ASSEMBLED"] = "ASSEMBLED"
    material_status: Literal["EVIDENCE_AVAILABLE", "INSUFFICIENT_MATERIAL"]
    synthesis_status: Literal["UNSUPPORTED_MODEL_SYNTHESIS"] = "UNSUPPORTED_MODEL_SYNTHESIS"
    evidence: list[ResearchEvidence] = Field(max_length=MAX_EVIDENCE)
    intelligence: list[ResearchIntelligence] = Field(max_length=MAX_INTELLIGENCE)
    evidence_candidates: int = Field(ge=0)
    intelligence_candidates: int = Field(ge=0)
    retrieval_truncated: bool
    unresolved: list[ResearchUnresolved]
