"""Frozen, synthetic inputs for the future OpenAI qualification package."""

from youtube_intel.openai_qualification import FROZEN_OPENAI_QUALIFICATION_MANIFESTS


def test_exactly_two_synthetic_openai_qualification_manifests_are_frozen() -> None:
    assert tuple(item.manifest_id for item in FROZEN_OPENAI_QUALIFICATION_MANIFESTS) == (
        "openai-live-qualification-1",
        "openai-live-qualification-2",
    )
    assert all(item.is_synthetic is True for item in FROZEN_OPENAI_QUALIFICATION_MANIFESTS)
