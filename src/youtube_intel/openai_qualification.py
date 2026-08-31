"""Frozen synthetic inputs for the future OpenAI live-qualification package.

This module performs no credential resolution and no provider dispatch.  It is
the single tracked source of the two permitted qualification cases; a later
v4-backed executor consumes only these exact immutable values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from youtube_intel.deep_analysis_contracts import dacs1_sha256


@dataclass(frozen=True, slots=True)
class OpenAIQualificationManifest:
    """One non-secret, selected-evidence-only qualification input."""

    manifest_id: str
    semantic_purpose: str
    video_id: str
    video_title: str
    channel_name: str
    published_at: str
    duration_seconds: int
    output_language: str
    scoring_request_hash: str
    evidence_id: str
    evidence_source: str
    evidence_excerpt: str
    evidence_content_hash: str
    expected_schema_contract: str
    expected_validation_policy: str
    expected_provider: str
    expected_model: str
    expected_profile: str
    expected_structured_output_mode: str
    timeout_seconds: int
    sdk_retries: int
    semantic_retries: int
    fallback_allowed: bool
    substitution_allowed: bool
    is_synthetic: bool = True

    @property
    def identity(self) -> str:
        return dacs1_sha256(
            {
                "schema_version": "openai-live-qualification-manifest-v1",
                "manifest_id": self.manifest_id,
                "semantic_purpose": self.semantic_purpose,
                "video_id": self.video_id,
                "video_title": self.video_title,
                "channel_name": self.channel_name,
                "published_at": self.published_at,
                "duration_seconds": self.duration_seconds,
                "output_language": self.output_language,
                "scoring_request_hash": self.scoring_request_hash,
                "evidence_id": self.evidence_id,
                "evidence_source": self.evidence_source,
                "evidence_excerpt": self.evidence_excerpt,
                "evidence_content_hash": self.evidence_content_hash,
                "expected_schema_contract": self.expected_schema_contract,
                "expected_validation_policy": self.expected_validation_policy,
                "expected_provider": self.expected_provider,
                "expected_model": self.expected_model,
                "expected_profile": self.expected_profile,
                "expected_structured_output_mode": self.expected_structured_output_mode,
                "timeout_seconds": self.timeout_seconds,
                "sdk_retries": self.sdk_retries,
                "semantic_retries": self.semantic_retries,
                "fallback_allowed": self.fallback_allowed,
                "substitution_allowed": self.substitution_allowed,
                "is_synthetic": self.is_synthetic,
            }
        )


_COMMON: Final = {
    "published_at": "2026-01-01T00:00:00Z",
    "duration_seconds": 42,
    "output_language": "en",
    "expected_schema_contract": "knowledge-content-pydantic-v1",
    "expected_validation_policy": "strict-json-v1/knowledge-schema-v1/evidence-registry-grounding-v1/knowledge-graph-v2/scoring-language-v1/deep-analysis-provenance-v1",
    "expected_provider": "openai",
    "expected_model": "gpt-5.4-mini-2026-03-17",
    "expected_profile": "openai-deep-analysis-reference-capabilities-v1",
    "expected_structured_output_mode": "PROVIDER_JSON_SCHEMA",
    "timeout_seconds": 30,
    "sdk_retries": 0,
    "semantic_retries": 0,
    "fallback_allowed": False,
    "substitution_allowed": False,
}

FROZEN_OPENAI_QUALIFICATION_MANIFESTS: Final[tuple[OpenAIQualificationManifest, ...]] = (
    OpenAIQualificationManifest(
        manifest_id="openai-live-qualification-1",
        semantic_purpose="synthetic selected-evidence grounding and strict-schema qualification",
        video_id="qualification-video-1",
        video_title="Synthetic evidence workflow",
        channel_name="Synthetic Qualification Channel",
        scoring_request_hash="1" * 64,
        evidence_id="qualification-1-evidence-1",
        evidence_source="description",
        evidence_excerpt="A synthetic workflow records evidence before drafting a conclusion.",
        evidence_content_hash="2" * 64,
        **_COMMON,
    ),
    OpenAIQualificationManifest(
        manifest_id="openai-live-qualification-2",
        semantic_purpose="synthetic independent evidence timeline and strict-schema qualification",
        video_id="qualification-video-2",
        video_title="Synthetic incident handoff",
        channel_name="Synthetic Qualification Channel",
        scoring_request_hash="3" * 64,
        evidence_id="qualification-2-evidence-1",
        evidence_source="description",
        evidence_excerpt="A synthetic incident handoff records a sequenced evidence-linked timeline.",
        evidence_content_hash="4" * 64,
        **_COMMON,
    ),
)


def require_frozen_openai_qualification_manifest(
    manifest: object,
) -> OpenAIQualificationManifest:
    """Accept only one unchanged member of the fixed two-case package."""

    if type(manifest) is not OpenAIQualificationManifest:
        raise ValueError("OpenAI qualification manifest is not an exact frozen manifest")
    for frozen in FROZEN_OPENAI_QUALIFICATION_MANIFESTS:
        if manifest.manifest_id == frozen.manifest_id and manifest.identity == frozen.identity:
            return frozen
    raise ValueError("OpenAI qualification manifest is not an exact frozen manifest")


__all__ = [
    "FROZEN_OPENAI_QUALIFICATION_MANIFESTS",
    "OpenAIQualificationManifest",
    "require_frozen_openai_qualification_manifest",
]
