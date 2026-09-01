"""Frozen, synthetic inputs for the future OpenAI qualification package."""

from dataclasses import replace

import pytest

from youtube_intel.openai_qualification import (
    FROZEN_OPENAI_QUALIFICATION_MANIFESTS,
    openai_qualification_request_for_manifest,
    require_frozen_openai_qualification_manifest,
)


def test_exactly_two_synthetic_openai_qualification_manifests_are_frozen() -> None:
    assert tuple(item.manifest_id for item in FROZEN_OPENAI_QUALIFICATION_MANIFESTS) == (
        "openai-live-qualification-1",
        "openai-live-qualification-2",
    )
    assert all(item.is_synthetic is True for item in FROZEN_OPENAI_QUALIFICATION_MANIFESTS)


def test_altered_or_unfrozen_manifest_cannot_obtain_a_qualification_request() -> None:
    frozen = FROZEN_OPENAI_QUALIFICATION_MANIFESTS[0]

    with pytest.raises(ValueError, match="exact frozen"):
        require_frozen_openai_qualification_manifest(
            replace(frozen, evidence_excerpt="altered synthetic evidence")
        )
    with pytest.raises(ValueError, match="exact frozen"):
        openai_qualification_request_for_manifest(
            replace(frozen, manifest_id="openai-live-qualification-3")
        )


def test_each_manifest_freezes_the_future_provider_contract() -> None:
    for manifest in FROZEN_OPENAI_QUALIFICATION_MANIFESTS:
        assert manifest.expected_provider == "openai"
        assert manifest.expected_model == "gpt-5.4-mini-2026-03-17"
        assert manifest.expected_structured_output_mode == "PROVIDER_JSON_SCHEMA"
        assert manifest.timeout_seconds == 30
        assert manifest.sdk_retries == 0
        assert manifest.semantic_retries == 0
        assert manifest.fallback_allowed is False
        assert manifest.substitution_allowed is False
