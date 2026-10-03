"""Question and scope are semantic input, never provider or query instructions."""

import pytest
from pydantic import ValidationError

from youtube_intel.research_contract import ResearchRequest, semantic_identity


@pytest.mark.parametrize("question", ["", " \n\t", "x" * 2001, "\ud800"])
def test_invalid_question(question: str) -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(question=question, content_ids=["one"])


@pytest.mark.parametrize("scope", [[], [""], ["x" * 257], [str(i) for i in range(21)], ["\udfff"]])
def test_scope_is_explicit_and_bounded(scope: list[str]) -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(question="What can I inspect?", content_ids=scope)


def test_identity_is_deterministic_and_language_specific() -> None:
    first = ResearchRequest(question="  What  evidence?\n", content_ids=["b", "a", "b"])
    second = ResearchRequest(question="What  evidence?", content_ids=["a", "b"])
    assert first.question == "What  evidence?"
    assert first.content_ids == ["a", "b"]
    assert semantic_identity(first, "en") == semantic_identity(second, "en")
    assert semantic_identity(first, "en") != semantic_identity(first, "zh-CN")
    assert semantic_identity(first, "en") != semantic_identity(
        ResearchRequest(question="What evidence?", content_ids=["a", "b"]), "en"
    )


def test_no_model_scope_or_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(question="hello", content_ids=["a"], scope="all")
