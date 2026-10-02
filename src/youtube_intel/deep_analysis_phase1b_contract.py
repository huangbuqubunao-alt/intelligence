"""Native five-role contract: model candidate selection and durable projection.

The provider contract retains Phase 1A's bounded capacity and epistemic kinds.
Citation cardinality follows the existing AnalysisPoint policy (1..10). Neither
the model nor this pure binding function establishes Evidence authority: the
transactional store must resolve every resulting id through the one repository.
"""

from collections.abc import Mapping
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from youtube_intel.deep_analysis_contracts import DeepAnalysisValidationPolicyIdentityV1
from youtube_intel.deep_analysis_phase1a_contract import (
    PHASE_1A_MODEL_CONCEPTS,
    DeepAnalysisClaimV1,
    DeepAnalysisPhase1AModelOutput,
    map_phase_1a_output_to_knowledge_content,
)
from youtube_intel.domain import (
    KnowledgeContent,
    ScoringLanguageValidation,
    detect_scoring_language_violation,
)

PHASE_1B_PROMPT_IDENTITY = "v1x-content-deep-analysis-phase1b-prompt-v1"
PHASE_1B_MODEL_SCHEMA = "v1x-content-deep-analysis-model-output-v2"
PHASE_1B_PERSISTENCE_VERSION = "deep-analysis-persistence-v2"
PHASE_1B_VALIDATION_POLICY = DeepAnalysisValidationPolicyIdentityV1(
    schema_version="deep-analysis-validation-policy-identity-v1",
    strict_json_policy_version="strict-json-v1",
    schema_policy_version=PHASE_1B_MODEL_SCHEMA,
    domain_policy_version="deep-analysis-five-roles-v1",
    grounding_policy_version="durable-evidence-membership-same-content-v1",
    kg2_policy_version="deep-analysis-no-knowledge-graph-v1",
    language_policy_version="deep-analysis-five-roles-language-v1",
    provenance_policy_version="deep-analysis-durable-provenance-v1",
)


class DeepAnalysisCandidateClaim(DeepAnalysisClaimV1):
    evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=10)

    @field_validator("evidence_refs")
    @classmethod
    def _refs(cls, refs: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(refs)) != len(refs) or any(not ref or ref != ref.strip() for ref in refs):
            raise ValueError("candidate refs must be unique and non-empty")
        return refs


class DeepAnalysisPhase1BModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["v1x-content-deep-analysis-model-output-v2"] = "v1x-content-deep-analysis-model-output-v2"
    core_conclusion: tuple[DeepAnalysisCandidateClaim, ...] = Field(min_length=1, max_length=10)
    key_evidence: tuple[DeepAnalysisCandidateClaim, ...] = Field(min_length=1, max_length=20)
    uncertainty: tuple[DeepAnalysisCandidateClaim, ...] = Field(default=(), max_length=10)
    relevance_to_user: tuple[DeepAnalysisCandidateClaim, ...] = Field(min_length=1, max_length=10)
    next_question: tuple[DeepAnalysisCandidateClaim, ...] = Field(default=(), max_length=10)

    @model_validator(mode="after")
    def _bounded_semantics(self) -> Self:
        # Reuse the accepted capacity/text/kind rules without asking the model
        # for KnowledgeContent or constructing its historical carrier.
        DeepAnalysisPhase1AModelOutput.model_validate({
            role: [{"text": claim.text, "point_kind": claim.point_kind} for claim in getattr(self, role)]
            for role in PHASE_1A_MODEL_CONCEPTS
        })
        return self

    def claims_by_role(self) -> tuple[tuple[str, DeepAnalysisCandidateClaim], ...]:
        return tuple((role.upper(), claim) for role in PHASE_1A_MODEL_CONCEPTS for claim in getattr(self, role))

    def cited_refs(self) -> tuple[str, ...]:
        return tuple(sorted({ref for _, claim in self.claims_by_role() for ref in claim.evidence_refs}))


class DurableDeepAnalysisClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["CORE_CONCLUSION", "KEY_EVIDENCE", "UNCERTAINTY", "RELEVANCE_TO_USER", "NEXT_QUESTION"]
    text: str = Field(min_length=1, max_length=2000)
    point_kind: Literal["fact", "inference", "recommendation"]
    evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=10)
    language_validation: Literal["VALID", "UNCERTAIN"]


class DeepAnalysisDurableResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["v1x-content-deep-analysis-durable-result-v1"] = "v1x-content-deep-analysis-durable-result-v1"
    output_language: Literal["en", "zh-CN"]
    claims: tuple[DurableDeepAnalysisClaim, ...]


def claim_language(text: str, output_language: str) -> ScoringLanguageValidation:
    if output_language not in {"en", "zh-CN"}:
        raise ValueError("unsupported output language")
    language: Literal["en", "zh-CN"] = "en" if output_language == "en" else "zh-CN"
    return detect_scoring_language_violation(text, language)


def bind_durable_result(
    output: DeepAnalysisPhase1BModelOutput,
    durable_by_ref: Mapping[str, str],
    output_language: str,
) -> DeepAnalysisDurableResult:
    claims = []
    for role, claim in output.claims_by_role():
        language = claim_language(claim.text, output_language)
        if language is ScoringLanguageValidation.INVALID:
            raise ValueError("claim output language is invalid")
        if any(ref not in durable_by_ref for ref in claim.evidence_refs):
            raise ValueError("claim references an unvalidated candidate")
        claims.append({
            "role": role, "text": claim.text, "point_kind": claim.point_kind,
            "evidence_refs": tuple(durable_by_ref[ref] for ref in claim.evidence_refs),
            "language_validation": language.value,
        })
    return DeepAnalysisDurableResult.model_validate({"output_language": output_language, "claims": claims})


def durable_compatibility_content(result: DeepAnalysisDurableResult) -> KnowledgeContent:
    """Internal read adapter only. The native result remains persisted authority.

    Keep old consumers' type contract, while preserving every exact relationship.
    Compatibility topics remain inert and are excluded by the native Note gate.
    """
    grouped = {role: tuple(c for c in result.claims if c.role == role.upper()) for role in PHASE_1A_MODEL_CONCEPTS}
    output = DeepAnalysisPhase1AModelOutput.model_validate({
        role: [{"text": c.text, "point_kind": c.point_kind} for c in claims]
        for role, claims in grouped.items()
    })
    content = map_phase_1a_output_to_knowledge_content(output, summary_evidence_ids=grouped["core_conclusion"][0].evidence_refs)
    data = content.model_dump(mode="json")
    for role, field in (("core_conclusion", "core_points"), ("key_evidence", "key_facts"), ("uncertainty", "counterpoints"), ("relevance_to_user", "product_opportunities"), ("next_question", "hypotheses_to_validate")):
        data[field] = [{"text": c.text, "kind": c.point_kind, "evidence_ids": list(c.evidence_refs)} for c in grouped[role]]
    first = grouped["relevance_to_user"][0]
    data["why_it_matters"] = {"text": first.text, "kind": first.point_kind, "evidence_ids": list(first.evidence_refs)}
    return KnowledgeContent.model_validate(data)
