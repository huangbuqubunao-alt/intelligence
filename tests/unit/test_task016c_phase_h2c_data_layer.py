"""TASK-016C Phase H2-C — pure persistence data layer tests.

Covers H2CSettingsProvenance, RepairProviderEvidence v2, the bounded
RepairCompositeEnvelope, RepairPersistenceGraphIdentityV2 (E/S/G, no
circularity), G-based artifact keys/paths, and the opaque
PhaseHTrustedRepairSuccess carrier + private mint.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pickle
import sys
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.h2_evidence import (
    H2CSettingsProvenance,
    RepairCandidateEvidence,
    RepairCompositeEnvelope,
    RepairFinalizerBinding,
    RepairPersistenceGraphIdentityV2,
    RepairProviderEvidence,
    RepairQualityEvidence,
    build_h2c_settings_provenance,
    repair_persistence_graph_hash,
    replay_language_validation,
)
from youtube_intel.h2_jcs import jcs_serialize
from youtube_intel.quality import (
    RepairTrustedScoringFinalizer,
    build_scoring_candidate_hash,
)
from youtube_intel.scoring import (
    PhaseHTrustedRepairSuccess,
    _H2CEnvelopeOversize,
    _mint_phase_h_trusted_repair_success,
    build_repair_artifact_keys,
    build_repair_composite_envelope,
    build_repair_persistence_graph_identity,
    h2c_replay_invalid_detail,
    parse_repair_raw_key,
    parse_repair_raw_relative_path,
    parse_repair_structured_key,
    parse_repair_structured_relative_path,
    verify_repair_envelope_admission,
)

MODEL = "hf.co/bartowski/Qwen2.5-7B-Instruct-GGUF:Q4_K_M"
_DIGEST = "sha256:" + "4" * 64
_EN_REASON = "This repaired response explains a concrete product strategy clearly."


def _load_module(name: str) -> Any:
    support_path = Path(__file__).with_name(f"{name}.py")
    specification = importlib.util.spec_from_file_location(name, support_path)
    assert specification is not None and specification.loader is not None
    support = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = support
    specification.loader.exec_module(support)
    return support


def _settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model=MODEL,
        expected_model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_transcript_chars=64,
        max_description_chars=32,
    )


def _valid_chain() -> dict[str, Any]:
    """One complete self-consistent REPAIR chain through the finalizer."""

    finalizer_support = _load_module("test_task016c_phase_h2b_correction_finalizer")
    chain = finalizer_support._valid_chain()
    output = RepairTrustedScoringFinalizer().finalize(
        candidate=chain["candidate"],
        scoring_input=chain["scoring_input"],
        repair_normalized_input=chain["rni"],
        rni_hash=chain["rni_hash"],
        repair_request_hash=chain["repair_request_hash"],
        quality_input=chain["judge_input"],
        quality_result=chain["judge_result"],
        quality_operation=chain["judge_ctx"].operation_input,
        judge_evidence=chain["judge_evidence"],
        attestation=chain["attestation"],
        quality_authority=chain["authority"],
        scoring_context=finalizer_support._scoring_context(),
        validated_settings=chain["settings"],
    )
    chain["finalization"] = output
    repair_raw = json.dumps(
        {"model": MODEL, "response": _candidate_json(), "done": True},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    chain["repair_raw"] = repair_raw
    chain["repair_model_content"] = _candidate_json()
    chain["language_evidence"] = replay_language_validation(
        candidate=chain["candidate"], output_language="en"
    )
    assert chain["language_evidence"].result == "VALID"
    return chain


def _candidate_json() -> str:
    return json.dumps(
        {
            "score": 8,
            "reason": _EN_REASON,
            "topics": ["product"],
            "should_summarize": True,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _settings_provenance(settings: LocalScoringSettings) -> H2CSettingsProvenance:
    return build_h2c_settings_provenance(
        validated_settings=settings,
        output_language="en",
        summary_score_threshold=7.0,
    )


def _provider_evidence(chain: dict[str, Any]) -> RepairProviderEvidence:
    settings = chain["settings"]
    provenance = _settings_provenance(settings)
    return RepairProviderEvidence.model_validate(
        {
            "schema_version": "task016c-repair-provider-evidence-v2",
            "operation": "local-scoring-repair-v1",
            "normalized_input": chain["rni"].model_dump(mode="json"),
            "normalized_input_hash": chain["rni_hash"],
            "request_hash": chain["repair_request_hash"],
            "provider": "ollama",
            "model": settings.model,
            "model_digest": settings.expected_model_digest,
            "prompt_version": "scoring-prompt-v3",
            "operation_schema_version": "score-result-v2",
            "output_language": "en",
            "temperature": settings.temperature,
            "max_output_tokens": settings.max_output_tokens,
            "max_description_chars": settings.max_description_chars,
            "settings_provenance": provenance.model_dump(mode="json"),
            "settings_provenance_sha256": hashlib.sha256(
                jcs_serialize(provenance.model_dump(mode="json"))
            ).hexdigest(),
        }
    )


def _candidate_evidence(chain: dict[str, Any]) -> RepairCandidateEvidence:
    raw = chain["repair_raw"]
    raw_bytes = raw.encode("utf-8")
    return RepairCandidateEvidence.model_validate(
        {
            "schema_version": "task016c-repair-candidate-evidence-v1",
            "repair_raw_utf8": raw,
            "repair_raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "repair_raw_length": len(raw_bytes),
            "repair_model_content": chain["repair_model_content"],
            "candidate": chain["candidate"].model_dump(mode="json"),
            "candidate_sha256": build_scoring_candidate_hash(chain["candidate"]),
            "language_evidence": chain["language_evidence"].model_dump(mode="json"),
        }
    )


def _quality_evidence(chain: dict[str, Any]) -> RepairQualityEvidence:
    from youtube_intel.quality import build_content_quality_input_hash

    judge_raw = chain["judge_raw"]
    judge_raw_bytes = judge_raw.encode("utf-8")
    return RepairQualityEvidence.model_validate(
        {
            "schema_version": "task016c-repair-quality-evidence-v1",
            "quality_input": chain["judge_input"].model_dump(mode="json"),
            "quality_input_hash": build_content_quality_input_hash(
                chain["judge_input"]
            ),
            "deterministic_gate_status": "PASS",
            "judge_operation_input": chain["judge_ctx"]
            .operation_input.model_dump(mode="json"),
            "judge_h1": chain["judge_ctx"].expected_h1,
            "judge_h2": chain["judge_ctx"].expected_h2,
            "judge_raw_utf8": judge_raw,
            "judge_raw_sha256": hashlib.sha256(judge_raw_bytes).hexdigest(),
            "judge_raw_length": len(judge_raw_bytes),
            "judge_evidence": chain["judge_evidence"].model_dump(mode="json"),
            "quality_result": chain["judge_result"].model_dump(mode="json"),
            "attestation": chain["attestation"].model_dump(mode="json"),
        }
    )


def _finalizer_binding(chain: dict[str, Any]) -> RepairFinalizerBinding:
    output = chain["finalization"]
    return RepairFinalizerBinding.model_validate(
        {
            "schema_version": "task016c-repair-finalizer-binding-v1",
            "trusted_result": output.trusted_result.result.model_dump(mode="json"),
            "structured_result_sha256": output.structured_sha256,
            "structured_result_length": output.structured_length,
            "structured_result_schema_version": "score-result-v2",
            "structured_result_prompt_version": "scoring-prompt-v2",
            "primary_request_hash": chain["trusted_context"].request_hash,
            "repair_request_hash": chain["repair_request_hash"],
            "repair_judge_request_hash": chain["judge_ctx"].expected_h2,
        }
    )


def _build_envelope(chain: dict[str, Any]) -> tuple[Any, bytes, str, int]:
    return build_repair_composite_envelope(
        primary_failure_evidence=chain["pfe"],
        repair_provider_evidence=_provider_evidence(chain),
        repair_candidate_evidence=_candidate_evidence(chain),
        repair_quality_evidence=_quality_evidence(chain),
        finalizer_binding=_finalizer_binding(chain),
    )


def _graph_inputs(chain: dict[str, Any], envelope_sha256: str) -> dict[str, str]:
    provider = _provider_evidence(chain)
    return {
        "primary_request_hash": chain["trusted_context"].request_hash,
        "repair_request_hash": chain["repair_request_hash"],
        "repair_judge_request_hash": chain["judge_ctx"].expected_h2,
        "settings_provenance_sha256": provider.settings_provenance_sha256,
        "repair_envelope_sha256": envelope_sha256,
        "structured_result_sha256": chain["finalization"].structured_sha256,
    }


# ---------------------------------------------------------------------------
# Settings provenance
# ---------------------------------------------------------------------------


def test_settings_provenance_binds_every_identity_bearing_setting() -> None:
    provenance = _settings_provenance(_settings())
    assert provenance.schema_version == "task016c-h2c-settings-provenance-v1"
    assert provenance.scoring_provider == "ollama"
    assert provenance.judge_provider == "ollama"
    assert provenance.judge_base_url == provenance.scoring_base_url
    assert provenance.repair_num_predict == provenance.max_output_tokens
    assert provenance.repair_stream is False
    assert provenance.repair_think is False
    assert provenance.language_validator_contract == (
        "task016b-scoring-language-validator-v1"
    )
    assert len(H2CSettingsProvenance.model_fields) == 30


def test_settings_provenance_mutation_changes_identity() -> None:
    base = _settings_provenance(_settings())
    base_hash = hashlib.sha256(
        jcs_serialize(base.model_dump(mode="json"))
    ).hexdigest()

    def _mutated(**update: Any) -> str:
        mutated = base.model_copy(update=update)
        return hashlib.sha256(
            jcs_serialize(mutated.model_dump(mode="json"))
        ).hexdigest()

    assert _mutated(output_language="zh-CN") != base_hash
    assert _mutated(scoring_model="other-model") != base_hash
    assert _mutated(scoring_model_digest="sha256:" + "5" * 64) != base_hash
    assert _mutated(judge_model="other-model") != base_hash
    assert _mutated(judge_model_digest="sha256:" + "5" * 64) != base_hash
    assert _mutated(temperature=0.5) != base_hash
    assert _mutated(max_output_tokens=1300) != base_hash
    assert _mutated(max_transcript_chars=48) != base_hash
    assert _mutated(summary_score_threshold=8.0) != base_hash
    assert _mutated(scoring_prompt_version="scoring-prompt-v2") != base_hash


def test_settings_provenance_rejects_invalid_bounds() -> None:
    valid = _settings_provenance(_settings()).model_dump(mode="json")
    with pytest.raises(ValueError):
        H2CSettingsProvenance.model_validate(
            {**valid, "judge_base_url": "http://127.0.0.1:9999"}
        )
    with pytest.raises(ValueError):
        H2CSettingsProvenance.model_validate(
            {**valid, "repair_num_predict": valid["max_output_tokens"] + 1}
        )
    with pytest.raises(ValueError):
        H2CSettingsProvenance.model_validate(
            {**valid, "max_transcript_chars": 131_073}
        )
    with pytest.raises(ValueError):
        H2CSettingsProvenance.model_validate(
            {**valid, "max_output_tokens": 2_147_483_648}
        )
    with pytest.raises(ValueError):
        H2CSettingsProvenance.model_validate({**valid, "extra_field": 1})


def test_build_settings_provenance_requires_exact_settings_type() -> None:
    with pytest.raises(ValueError):
        build_h2c_settings_provenance(
            validated_settings=object(),  # type: ignore[arg-type]
            output_language="en",
            summary_score_threshold=7.0,
        )


# ---------------------------------------------------------------------------
# Envelope: six fields, canonical E, bounded admission
# ---------------------------------------------------------------------------


def test_envelope_has_exactly_six_ordered_fields_and_canonical_e() -> None:
    chain = _valid_chain()
    envelope, envelope_bytes, envelope_sha256, envelope_length = _build_envelope(
        chain
    )
    assert list(envelope.model_dump(mode="json").keys()) == [
        "envelope_schema",
        "primary_failure_evidence",
        "repair_provider_evidence",
        "repair_candidate_evidence",
        "repair_quality_evidence",
        "finalizer_binding",
    ]
    assert envelope.envelope_schema == "trusted-scoring-repair-envelope-v1"
    assert hashlib.sha256(envelope_bytes).hexdigest() == envelope_sha256
    assert len(envelope_bytes) == envelope_length
    # Canonical reserialize equality.
    assert jcs_serialize(envelope.model_dump(mode="json")) == envelope_bytes
    # The envelope carries neither G nor artifact keys/paths.
    text = envelope_bytes.decode("utf-8")
    assert "/repair/" not in text
    assert "artifact" not in text.lower()


def test_envelope_rejects_extra_root_field() -> None:
    chain = _valid_chain()
    with pytest.raises(ValueError):
        RepairCompositeEnvelope.model_validate(
            {
                "envelope_schema": "trusted-scoring-repair-envelope-v1",
                "primary_failure_evidence": chain["pfe"].model_dump(mode="json"),
                "repair_provider_evidence": _provider_evidence(chain).model_dump(
                    mode="json"
                ),
                "repair_candidate_evidence": _candidate_evidence(chain).model_dump(
                    mode="json"
                ),
                "repair_quality_evidence": _quality_evidence(chain).model_dump(
                    mode="json"
                ),
                "finalizer_binding": _finalizer_binding(chain).model_dump(
                    mode="json"
                ),
                "graph_hash": "g",
            }
        )


def test_envelope_admission_rejects_oversize_repair_raw() -> None:
    chain = _valid_chain()
    candidate_evidence = _candidate_evidence(chain)
    oversize_raw = '{"response": "' + "x" * 1_000_001 + '"}'
    mutated = candidate_evidence.model_copy(
        update={
            "repair_raw_utf8": oversize_raw,
            "repair_raw_sha256": hashlib.sha256(
                oversize_raw.encode("utf-8")
            ).hexdigest(),
            "repair_raw_length": len(oversize_raw.encode("utf-8")),
        }
    )
    with pytest.raises(_H2CEnvelopeOversize):
        build_repair_composite_envelope(
            primary_failure_evidence=chain["pfe"],
            repair_provider_evidence=_provider_evidence(chain),
            repair_candidate_evidence=mutated,
            repair_quality_evidence=_quality_evidence(chain),
            finalizer_binding=_finalizer_binding(chain),
        )


def test_envelope_admission_rejects_oversize_judge_raw() -> None:
    chain = _valid_chain()
    quality = _quality_evidence(chain)
    oversized = "y" * 20_001
    mutated = quality.model_copy(
        update={
            "judge_raw_utf8": oversized,
            "judge_raw_sha256": hashlib.sha256(oversized.encode()).hexdigest(),
            "judge_raw_length": len(oversized.encode()),
        }
    )
    envelope = RepairCompositeEnvelope.model_validate(
        {
            "envelope_schema": "trusted-scoring-repair-envelope-v1",
            "primary_failure_evidence": chain["pfe"].model_dump(mode="json"),
            "repair_provider_evidence": _provider_evidence(chain).model_dump(
                mode="json"
            ),
            "repair_candidate_evidence": _candidate_evidence(chain).model_dump(
                mode="json"
            ),
            "repair_quality_evidence": mutated.model_dump(mode="json"),
            "finalizer_binding": _finalizer_binding(chain).model_dump(mode="json"),
        }
    )
    with pytest.raises(_H2CEnvelopeOversize):
        verify_repair_envelope_admission(envelope)


# ---------------------------------------------------------------------------
# Graph identity v2: E/S/G, determinism, no circularity
# ---------------------------------------------------------------------------


def test_graph_identity_fields_and_deterministic_g() -> None:
    chain = _valid_chain()
    _, _, envelope_sha256, _ = _build_envelope(chain)
    identity = build_repair_persistence_graph_identity(
        **_graph_inputs(chain, envelope_sha256)
    )
    assert identity.schema_version == "task016c-repair-persistence-graph-v2"
    assert len(RepairPersistenceGraphIdentityV2.model_fields) == 14
    first = repair_persistence_graph_hash(identity)
    second = repair_persistence_graph_hash(identity)
    assert first == second
    assert len(first) == 64
    assert first == first.lower()


def test_materially_different_graphs_produce_different_g() -> None:
    chain = _valid_chain()
    _, _, envelope_sha256, _ = _build_envelope(chain)
    inputs = _graph_inputs(chain, envelope_sha256)
    base_g = repair_persistence_graph_hash(
        build_repair_persistence_graph_identity(**inputs)
    )

    def _g(**update: str) -> str:
        return repair_persistence_graph_hash(
            build_repair_persistence_graph_identity(**{**inputs, **update})
        )

    other = "f" * 64
    assert _g(repair_request_hash=other) != base_g
    assert _g(repair_judge_request_hash=other) != base_g
    assert _g(settings_provenance_sha256=other) != base_g
    assert _g(repair_envelope_sha256=other) != base_g
    assert _g(structured_result_sha256=other) != base_g
    assert _g(primary_request_hash=other) != base_g


def test_envelope_and_structured_bytes_do_not_depend_on_g() -> None:
    chain = _valid_chain()
    envelope, envelope_bytes, envelope_sha256, _ = _build_envelope(chain)
    structured_bytes = chain["finalization"].structured_bytes
    identity = build_repair_persistence_graph_identity(
        **_graph_inputs(chain, envelope_sha256)
    )
    g = repair_persistence_graph_hash(identity)
    # No circularity: neither sealed byte stream contains the G commitment.
    assert g.encode() not in envelope_bytes
    assert g.encode() not in structured_bytes
    assert envelope_sha256.encode() not in structured_bytes


# ---------------------------------------------------------------------------
# G-based keys/paths and grammar
# ---------------------------------------------------------------------------


def test_repair_artifact_keys_and_grammar() -> None:
    p = "a" * 64
    g = "b" * 64
    raw_key, raw_path, structured_key, structured_path = build_repair_artifact_keys(
        primary_request_hash=p, graph_hash=g
    )
    assert raw_key == f"scoring/{p}/repair/{g}/raw"
    assert raw_path == f"scoring/{p}/repair/{g}/raw.json"
    assert structured_key == f"scoring/{p}/repair/{g}/structured"
    assert structured_path == f"scoring/{p}/repair/{g}/structured.json"
    assert parse_repair_raw_key(raw_key) == (p, g)
    assert parse_repair_structured_key(structured_key) == (p, g)
    assert parse_repair_raw_relative_path(raw_path) == (p, g)
    assert parse_repair_structured_relative_path(structured_path) == (p, g)


def test_repair_key_grammar_rejects_unsafe_shapes() -> None:
    p = "a" * 64
    g = "b" * 64
    for bad_key in (
        f"scoring/{p}/repair/{g}/structured.json",  # path where key expected
        f"scoring/{p}/{g}/structured",
        f"scoring/{p.upper()}/repair/{g}/structured",
        f"scoring/../{p}/repair/{g}/structured",
        f"scoring/{p}/repair/{g[:-1]}/structured",
        f"scoring/{p}/repair/{g}/other",
        "scoring/x/repair/y/structured",
    ):
        with pytest.raises(ValueError):
            parse_repair_structured_key(bad_key)
    with pytest.raises(ValueError):
        build_repair_artifact_keys(primary_request_hash="A" * 64, graph_hash=g)
    with pytest.raises(ValueError):
        build_repair_artifact_keys(primary_request_hash=p, graph_hash="z" * 64)


def test_no_p_only_repair_authoritative_alias() -> None:
    p = "a" * 64
    g = "b" * 64
    raw_key, _, structured_key, _ = build_repair_artifact_keys(
        primary_request_hash=p, graph_hash=g
    )
    # Repair keys are never the legacy P-only keys.
    assert raw_key != f"scoring/{p}/raw"
    assert structured_key != f"scoring/{p}/structured"


# ---------------------------------------------------------------------------
# Closed diagnostic details
# ---------------------------------------------------------------------------


def test_h2c_diagnostic_details_are_closed() -> None:
    assert (
        h2c_replay_invalid_detail("SCORING_LINEAGE_VERSION_INVALID")
        == "H2C_REPLAY_INVALID:SCORING_LINEAGE_VERSION_INVALID"
    )
    assert (
        h2c_replay_invalid_detail("ENVELOPE_OVERSIZE")
        == "H2C_REPLAY_INVALID:ENVELOPE_OVERSIZE"
    )
    for reason in (
        "H2C_SCORING_LINEAGE_VERSION_INVALID",
        "ARBITRARY_REASON",
        "SCORING_LINEAGE_VERSION_INVALID:extra",
        "",
    ):
        with pytest.raises(ValueError):
            h2c_replay_invalid_detail(reason)


# ---------------------------------------------------------------------------
# PhaseHTrustedRepairSuccess carrier and private mint
# ---------------------------------------------------------------------------


def _mint_valid_success(chain: dict[str, Any]) -> PhaseHTrustedRepairSuccess:
    envelope, envelope_bytes, _, _ = _build_envelope(chain)
    return _mint_phase_h_trusted_repair_success(
        job_id="h2c-job",
        owner="runtime-owner",
        pipeline_version="runtime-v1",
        primary_request_hash=chain["trusted_context"].request_hash,
        primary_normalized_input_hash=chain["trusted_context"].normalized_input_hash,
        scoring_input_sha256=chain["trusted_context"].scoring_input_sha256,
        envelope=envelope,
        envelope_bytes=envelope_bytes,
        trusted_result=chain["finalization"].trusted_result,
        structured_bytes=chain["finalization"].structured_bytes,
    )


def test_success_carrier_mint_seals_self_consistent_data() -> None:
    chain = _valid_chain()
    success = _mint_valid_success(chain)
    assert success.job_id == "h2c-job"
    assert success.prompt_version == "scoring-prompt-v3"
    assert success.schema_version == "score-result-v2"
    assert (
        hashlib.sha256(success.repair_composite_envelope_bytes).hexdigest()
        == success.repair_composite_envelope_sha256
    )
    assert (
        hashlib.sha256(success.structured_bytes).hexdigest()
        == success.structured_sha256
    )
    assert success.primary_request_hash == chain["trusted_context"].request_hash


def test_success_carrier_rejects_public_construction_and_copy() -> None:
    chain = _valid_chain()
    envelope, envelope_bytes, _, _ = _build_envelope(chain)
    with pytest.raises(ValueError):
        PhaseHTrustedRepairSuccess(
            sentinel=object(),
            job_id="h2c-job",
            owner="runtime-owner",
            pipeline_version="runtime-v1",
            primary_request_hash=chain["trusted_context"].request_hash,
            primary_normalized_input_hash=(
                chain["trusted_context"].normalized_input_hash
            ),
            scoring_input_sha256=chain["trusted_context"].scoring_input_sha256,
            repair_composite_envelope_bytes=envelope_bytes,
            repair_composite_envelope_sha256=hashlib.sha256(
                envelope_bytes
            ).hexdigest(),
            repair_composite_envelope_length=len(envelope_bytes),
            trusted_result=chain["finalization"].trusted_result,
            structured_bytes=chain["finalization"].structured_bytes,
            structured_sha256=chain["finalization"].structured_sha256,
            structured_length=chain["finalization"].structured_length,
            prompt_version="scoring-prompt-v2",
            schema_version="score-result-v2",
            envelope=envelope,
        )
    success = _mint_valid_success(chain)
    with pytest.raises(TypeError):
        copy.copy(success)
    with pytest.raises(TypeError):
        copy.deepcopy(success)
    with pytest.raises(TypeError):
        pickle.dumps(success)
    with pytest.raises(TypeError):

        class _Subclass(PhaseHTrustedRepairSuccess):  # noqa: F841
            pass

    with pytest.raises(TypeError):
        success._sealed = False  # type: ignore[misc]


def test_success_carrier_mint_rejects_inconsistent_binding() -> None:
    chain = _valid_chain()
    envelope, envelope_bytes, _, _ = _build_envelope(chain)
    wrong_p = "c" * 64
    with pytest.raises(ValueError):
        _mint_phase_h_trusted_repair_success(
            job_id="h2c-job",
            owner="runtime-owner",
            pipeline_version="runtime-v1",
            primary_request_hash=wrong_p,
            primary_normalized_input_hash=(
                chain["trusted_context"].normalized_input_hash
            ),
            scoring_input_sha256=chain["trusted_context"].scoring_input_sha256,
            envelope=envelope,
            envelope_bytes=envelope_bytes,
            trusted_result=chain["finalization"].trusted_result,
            structured_bytes=chain["finalization"].structured_bytes,
        )
    with pytest.raises(ValueError):
        _mint_phase_h_trusted_repair_success(
            job_id="h2c-job",
            owner="runtime-owner",
            pipeline_version="runtime-v1",
            primary_request_hash=chain["trusted_context"].request_hash,
            primary_normalized_input_hash=(
                chain["trusted_context"].normalized_input_hash
            ),
            scoring_input_sha256=chain["trusted_context"].scoring_input_sha256,
            envelope=envelope,
            envelope_bytes=envelope_bytes,
            trusted_result=chain["finalization"].trusted_result,
            structured_bytes=chain["finalization"].structured_bytes + b"x",
        )
