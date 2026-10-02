"""The model selects candidates; it cannot author durable Evidence fields."""

import pytest
from pydantic import ValidationError

from youtube_intel.deep_analysis_phase1b_contract import (
    DeepAnalysisPhase1BModelOutput,
    bind_durable_result,
)


def output(ref: str = "candidate") -> dict:
    def claim(text: str, kind: str) -> dict:
        return {"text": text, "point_kind": kind, "evidence_refs": [ref]}
    return {
        "schema_version": "v1x-content-deep-analysis-model-output-v2",
        "core_conclusion": [claim("This content supports the conclusion.", "inference")],
        "key_evidence": [claim("The transcript states the measured result.", "fact")],
        "uncertainty": [claim("The causal explanation remains uncertain.", "inference")],
        "relevance_to_user": [claim("This result changes the reader's planning.", "inference")],
        "next_question": [claim("The reader should investigate the second source.", "inference")],
    }


def test_binding_preserves_every_role_and_canonical_text() -> None:
    raw = output()
    raw["core_conclusion"][0]["text"] = "\u2003This content supports the conclusion.\u2003"
    admitted = DeepAnalysisPhase1BModelOutput.model_validate(raw)
    result = bind_durable_result(admitted, {"candidate": "real-evidence"}, "en")
    assert len(result.claims) == 5
    assert result.claims[0].text == "This content supports the conclusion."
    assert all(c.evidence_refs == ("real-evidence",) for c in result.claims)
    assert all(c.language_validation == "VALID" for c in result.claims)


@pytest.mark.parametrize("role", ["core_conclusion", "key_evidence", "uncertainty", "relevance_to_user", "next_question"])
def test_language_invalid_in_any_role_rejects_binding(role: str) -> None:
    raw = output()
    raw[role][0]["text"] = "这个结果说明了数据存在明显差异。"
    admitted = DeepAnalysisPhase1BModelOutput.model_validate(raw)
    with pytest.raises(ValueError, match="language"):
        bind_durable_result(admitted, {"candidate": "real-evidence"}, "en")


def test_mixed_language_is_honestly_uncertain() -> None:
    raw = output()
    raw["next_question"][0]["text"] = "This claim about 数据 requires another source."
    result = bind_durable_result(DeepAnalysisPhase1BModelOutput.model_validate(raw), {"candidate": "real"}, "en")
    assert result.claims[-1].language_validation == "UNCERTAIN"


@pytest.mark.parametrize("field", ["excerpt", "start_ms", "end_ms", "evidence_id", "knowledge_delta"])
def test_model_authority_fields_rejected(field: str) -> None:
    raw = output()
    raw["core_conclusion"][0][field] = "forged"
    with pytest.raises(ValidationError):
        DeepAnalysisPhase1BModelOutput.model_validate(raw)


def test_unknown_candidate_cannot_bind() -> None:
    with pytest.raises(ValueError, match="candidate"):
        bind_durable_result(DeepAnalysisPhase1BModelOutput.model_validate(output()), {}, "en")
