"""Card B: provider-neutral SummaryDraft contract with no authoritative excerpt."""

from __future__ import annotations

import json

import pytest

from youtube_intel.domain import AnalysisResult
from youtube_intel.summary_draft import (
    EVIDENCE_EXCERPT_MAX_LENGTH,
    SUMMARY_DRAFT_PROMPT_VERSION,
    SUMMARY_DRAFT_SCHEMA_VERSION,
    SummaryDraft,
    SummaryDraftError,
    parse_summary_draft,
    summary_draft_instructions,
    summary_draft_schema,
)

REF = "t0-3-0f2c1a9b8d7e6f50"


def _valid() -> str:
    return json.dumps(
        {
            "one_sentence_summary": "该视频讨论了一个数学谜题。",
            "core_points": [
                {"text": "电话号码可映射到只含 1 和 0 的数。", "kind": "fact", "evidence_refs": [REF]}
            ],
            "keywords": ["电话号码", "数学谜题"],
        },
        ensure_ascii=False,
    )


# --- B1 -------------------------------------------------------------------


def test_B1_accepts_valid_claims_and_refs() -> None:
    draft = parse_summary_draft(_valid())
    assert draft.one_sentence_summary
    assert draft.cited_refs() == (REF,)
    assert draft.core_points[0].kind.value == "fact"


# --- B2 / B3: the model-facing schema has no authoritative surface --------


def test_B2_model_facing_schema_contains_no_excerpt() -> None:
    schema = summary_draft_schema()
    assert "evidence" not in schema["properties"]
    serialized = json.dumps(schema)
    assert "excerpt" not in serialized
    assert "source_excerpt" not in serialized


def test_B3_model_facing_schema_contains_no_offsets_or_timestamps() -> None:
    serialized = json.dumps(summary_draft_schema())
    for forbidden in (
        "start_offset",
        "end_offset",
        "start_seconds",
        "end_seconds",
        "start_ms",
        "end_ms",
        "timestamp",
    ):
        assert forbidden not in serialized


def test_schema_identity_is_distinct_from_persisted_contract() -> None:
    assert SUMMARY_DRAFT_PROMPT_VERSION == "analysis-prompt-v5"
    assert SUMMARY_DRAFT_PROMPT_VERSION != "analysis-prompt-v4"
    assert SUMMARY_DRAFT_SCHEMA_VERSION == "summary-draft-v1"
    assert SUMMARY_DRAFT_SCHEMA_VERSION != "analysis-result-v1"


# --- B4 / B5: unsupported fields fail closed -------------------------------


def test_B4_unsupported_excerpt_field_is_rejected() -> None:
    payload = json.loads(_valid())
    payload["core_points"][0]["excerpt"] = "fabricated authoritative quote"
    with pytest.raises(SummaryDraftError, match="contract validation"):
        parse_summary_draft(json.dumps(payload, ensure_ascii=False))


def test_B4b_top_level_evidence_collection_is_rejected() -> None:
    payload = json.loads(_valid())
    payload["evidence"] = [
        {"evidence_id": "e1", "source": "transcript_sample", "excerpt": "made up"}
    ]
    with pytest.raises(SummaryDraftError, match="authoritative Evidence text"):
        parse_summary_draft(json.dumps(payload, ensure_ascii=False))


def test_B5_unknown_extra_field_is_rejected() -> None:
    payload = json.loads(_valid())
    payload["confidence"] = 0.97
    with pytest.raises(SummaryDraftError, match="contract validation"):
        parse_summary_draft(json.dumps(payload, ensure_ascii=False))


@pytest.mark.parametrize("bad", ["", "   ", "not json", "[]", '"text"'])
def test_malformed_responses_fail_closed(bad: str) -> None:
    with pytest.raises(SummaryDraftError):
        parse_summary_draft(bad)


# --- B6: ref validity -----------------------------------------------------


def test_B6_evidence_refs_must_be_non_empty() -> None:
    with pytest.raises(SummaryDraftError):
        parse_summary_draft(
            json.dumps(
                {
                    "one_sentence_summary": "x",
                    "core_points": [{"text": "t", "kind": "fact", "evidence_refs": []}],
                    "keywords": ["k"],
                }
            )
        )


def test_B6b_duplicate_refs_are_rejected() -> None:
    with pytest.raises(SummaryDraftError):
        parse_summary_draft(
            json.dumps(
                {
                    "one_sentence_summary": "x",
                    "core_points": [
                        {"text": "t", "kind": "fact", "evidence_refs": [REF, REF]}
                    ],
                    "keywords": ["k"],
                }
            )
        )
    # The duplicate is also rejected directly by the contract.
    with pytest.raises(ValueError, match="unique"):
        SummaryDraft.model_validate(
            {
                "one_sentence_summary": "x",
                "core_points": [
                    {"text": "t", "kind": "fact", "evidence_refs": [REF, REF]}
                ],
                "keywords": ["k"],
            }
        )


# --- B7: optional legacy analytical fields remain representable -----------


def test_B7_optional_legacy_analysis_fields_remain_representable() -> None:
    payload = json.loads(_valid())
    for field in (
        "key_facts",
        "product_opportunities",
        "business_opportunities",
        "actionable_directions",
        "hypotheses_to_validate",
        "action_recommendations",
        "risks",
    ):
        payload[field] = [
            {"text": "保留的旧分析维度", "kind": "inference", "evidence_refs": [REF]}
        ]
    draft = parse_summary_draft(json.dumps(payload, ensure_ascii=False))
    assert draft.key_facts
    assert draft.risks
    assert draft.cited_refs() == (REF,)


# --- B8: the persisted AnalysisResult contract is untouched ---------------


def test_B8_old_persisted_analysis_result_contract_remains_readable() -> None:
    """A pre-existing v4 artifact must still validate unchanged."""
    legacy = {
        "one_sentence_summary": "既有摘要",
        "core_points": [{"text": "既有要点", "kind": "fact", "evidence_ids": ["e1"]}],
        "keywords": ["k"],
        "evidence": [
            {"evidence_id": "e1", "source": "transcript_sample", "excerpt": "x" * 10}
        ],
        "provider": "ollama",
        "model": "qwen3:8b",
        "prompt_version": "analysis-prompt-v4",
        "schema_version": "analysis-result-v1",
        "request_hash": "0" * 64,
    }
    result = AnalysisResult.model_validate(legacy)
    assert result.evidence[0].evidence_id == "e1"
    assert result.prompt_version == "analysis-prompt-v4"


# --- Contract immutability ------------------------------------------------


def test_draft_is_frozen_and_model_copy_update_is_disabled() -> None:
    draft = parse_summary_draft(_valid())
    with pytest.raises(ValueError, match="model_copy"):
        draft.model_copy(update={"one_sentence_summary": "x"})  # type: ignore[call-overload]


def test_instructions_never_ask_the_model_to_quote_source() -> None:
    text = summary_draft_instructions((REF,)).lower()
    assert "never reproduce" in text
    assert "verbatim substrings" not in text
    assert REF in summary_draft_instructions((REF,))


def test_excerpt_bound_is_shared_with_the_evidence_contract() -> None:
    from youtube_intel.domain import EvidenceExcerpt

    assert EVIDENCE_EXCERPT_MAX_LENGTH == 2000
    bound = EvidenceExcerpt.model_fields["excerpt"].metadata
    assert bound
