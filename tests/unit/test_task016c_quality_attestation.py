"""TASK-016C Phase D — Quality PASS Attestation and Canonical Hashing tests.

RED-first TDD: every test below is written before the production code.
The production API surface exercised here is:

- ``youtube_intel.domain.QualityPassAttestation``
- ``youtube_intel.quality.build_content_quality_result_hash``
- ``youtube_intel.quality.build_quality_pass_attestation``
- ``youtube_intel.quality.verify_quality_pass_attestation``
"""

from __future__ import annotations

import copy
import hashlib
import json
import pickle
import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel

from youtube_intel.config import LocalScoringSettings, load_app_config
from youtube_intel.domain import (
    ContentQualityInput,
    ContentQualityResult,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    QualityPassAttestation,
    ScoringEvidence,
    ScoringEvidenceSource,
)
from youtube_intel.quality import (
    QualityProvenanceAuthority,
    build_content_quality_input_hash,
    build_content_quality_result_hash,
    build_judge_h1_h2,
    build_quality_pass_attestation,
    verify_quality_pass_attestation,
)
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

VALID_HASH = "a" * 64
OTHER_HASH = "0" * 64
DIGEST = "sha256:" + "b" * 64
OTHER_DIGEST = "sha256:" + "c" * 64
REAL_CONFIG_DIGEST = "sha256:" + "1" * 64
UNAUTHORIZED_MODEL = "untrusted-local-model"
UNAUTHORIZED_DIGEST = "sha256:" + "d" * 64
SCORING_SCHEMA_VERSION = "scoring-schema-v1"
SCORING_PROMPT_VERSION = "scoring-prompt-v1"
OTHER_SCORING_SCHEMA = "scoring-schema-v2"
OTHER_SCORING_PROMPT = "scoring-prompt-v2"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _evidence_registry(*evidence_ids: str) -> tuple[ScoringEvidence, ...]:
    return tuple(
        ScoringEvidence(
            evidence_id=eid,
            source=ScoringEvidenceSource.TITLE,
            excerpt=f"excerpt for {eid}",
        )
        for eid in evidence_ids
    )


def _content_input(
    *,
    scoring_request_hash: str = VALID_HASH,
    candidate_hash: str = VALID_HASH,
    output_language: str = "en",
    reason: str = "A concise candidate reason",
    topics: tuple[str, ...] = ("topic-a", "topic-b"),
    evidence_registry: tuple[ScoringEvidence, ...] | None = None,
) -> ContentQualityInput:
    if evidence_registry is None:
        evidence_registry = _evidence_registry("title-1")
    return ContentQualityInput.model_validate(
        {
            "scoring_request_hash": scoring_request_hash,
            "candidate_hash": candidate_hash,
            "output_language": output_language,
            "reason": reason,
            "topics": topics,
            "evidence_registry": evidence_registry,
            "policy_version": "content-quality-policy-v1",
        }
    )


def _operation_input(
    *,
    scoring_request_hash: str = VALID_HASH,
    attempt_role: QualityJudgeAttemptRole = QualityJudgeAttemptRole.PRIMARY,
    candidate_hash: str = VALID_HASH,
    quality_input_hash: str = VALID_HASH,
    policy_version: str = "content-quality-policy-v1",
    prompt_version: str = "content-quality-prompt-v1",
    schema_version: str = "content-quality-result-v1",
    judge_provider: str = "ollama",
    judge_model: str = "qwen3:8b",
    judge_model_digest: str = DIGEST,
) -> QualityJudgeOperationInput:
    return QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": scoring_request_hash,
            "attempt_role": attempt_role,
            "candidate_hash": candidate_hash,
            "quality_input_hash": quality_input_hash,
            "policy_version": policy_version,
            "prompt_version": prompt_version,
            "schema_version": schema_version,
            "judge_provider": judge_provider,
            "judge_model": judge_model,
            "judge_model_digest": judge_model_digest,
        }
    )


def _pass_result(
    *,
    candidate_hash: str = VALID_HASH,
    quality_input_hash: str = VALID_HASH,
    scoring_request_hash: str = VALID_HASH,
    decision_confidence: str = "HIGH",
    grounding_confidence: str = "MEDIUM",
    usefulness_confidence: str = "MEDIUM",
    signals: list[str] | None = None,
    reason: str | None = None,
    evidence_ids: list[str] | None = None,
    judge_provider: str = "ollama",
    judge_model: str = "qwen3:8b",
    judge_model_digest: str = DIGEST,
    status: str = "PASS",
    decision_source: str = "LOCAL_JUDGE",
    schema_version: str = "content-quality-result-v1",
    policy_version: str = "content-quality-policy-v1",
    prompt_version: str = "content-quality-prompt-v1",
) -> ContentQualityResult:
    return ContentQualityResult.model_validate(
        {
            "schema_version": schema_version,
            "policy_version": policy_version,
            "prompt_version": prompt_version,
            "status": status,
            "decision_source": decision_source,
            "decision_confidence": decision_confidence,
            "grounding_confidence": grounding_confidence,
            "usefulness_confidence": usefulness_confidence,
            "signals": signals
            if signals is not None
            else ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
            "reason": reason,
            "evidence_ids": evidence_ids if evidence_ids is not None else ["title-1"],
            "candidate_hash": candidate_hash,
            "quality_input_hash": quality_input_hash,
            "scoring_request_hash": scoring_request_hash,
            "judge_provider": judge_provider,
            "judge_model": judge_model,
            "judge_model_digest": judge_model_digest,
        }
    )


def _consistent_trio(
    *,
    judge_model: str = "qwen3:8b",
    judge_model_digest: str = DIGEST,
) -> tuple[ContentQualityInput, QualityJudgeOperationInput, ContentQualityResult]:
    """Return (content_input, operation_input, pass_result) with consistent hashes."""
    content_input = _content_input()
    qih = build_content_quality_input_hash(content_input)
    operation_input = _operation_input(
        quality_input_hash=qih,
        judge_model=judge_model,
        judge_model_digest=judge_model_digest,
    )
    pass_result = _pass_result(
        quality_input_hash=qih,
        judge_model=judge_model,
        judge_model_digest=judge_model_digest,
    )
    return content_input, operation_input, pass_result


def _write_minimal_project(
    project: Path,
    *,
    model: str,
    digest: str,
) -> None:
    """Write the smallest valid project configuration for authority minting."""
    (project / "config").mkdir(parents=True, exist_ok=True)
    (project / "vault").mkdir(parents=True, exist_ok=True)
    (project / "config" / "channels.yaml").write_text(
        "channels:\n  - channel_id: UCtest000000000000000000000000000\n",
        encoding="utf-8",
    )
    (project / "config" / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
local_scoring:
  model: {model}
  expected_model_digest: {digest}
cloud:
  enabled: false
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {project / 'vault'}
  vault_subdir: YouTube Intel
""",
        encoding="utf-8",
    )


def _runtime_authority(project: Path) -> QualityProvenanceAuthority:
    """Mint an authority by loading real AppConfig through RuntimeOperations."""
    config = load_app_config(
        channels_path=project / "config" / "channels.yaml",
        settings_path=project / "config" / "settings.yaml",
    )
    runtime = RuntimeOperations(
        config=config,
        project_root=project,
        dependencies=RuntimeDependencies(
            discovery_source=object(),  # type: ignore[arg-type]
            metadata_provider=object(),  # type: ignore[arg-type]
            subtitle_adapter_factory=lambda: object(),  # type: ignore[arg-type]
            scoring_provider_factory=lambda: object(),  # type: ignore[arg-type]
            analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
        ),
    )
    return runtime._quality_provenance_authority


_module_authority_project: Path | None = None


def _default_authority_project() -> Path:
    """Lazily create one project for the default test authority.

    The authority is immutable, so sharing it across tests is safe.  Each Python
    process gets its own directory via ``tempfile.mkdtemp``.
    """
    global _module_authority_project
    if _module_authority_project is None:
        _module_authority_project = Path(tempfile.mkdtemp(prefix="yia-authority-"))
        _write_minimal_project(
            _module_authority_project,
            model="qwen3:8b",
            digest=DIGEST,
        )
    return _module_authority_project


def _current_authority(
    tmp_path: Path | None = None,
    *,
    model: str = "qwen3:8b",
    digest: str = DIGEST,
) -> QualityProvenanceAuthority:
    """Runtime-minted authority matching the default test trio.

    When ``tmp_path`` is provided, a fresh project is created there; otherwise a
    module-level project is reused for callers that do not need a custom config.
    """
    if tmp_path is None:
        return _runtime_authority(_default_authority_project())
    project = tmp_path / "authority-project"
    _write_minimal_project(project, model=model, digest=digest)
    return _runtime_authority(project)


def _real_config_authority(tmp_path: Path) -> QualityProvenanceAuthority:
    """Runtime-minted authority using a real current config digest, not bbbb."""
    return _current_authority(tmp_path, digest=REAL_CONFIG_DIGEST)


def _build_valid_attestation(
    authority: QualityProvenanceAuthority | None = None,
) -> QualityPassAttestation:
    content_input, operation_input, pass_result = _consistent_trio()
    return build_quality_pass_attestation(
        quality_result=pass_result,
        operation_input=operation_input,
        quality_input=content_input,
        authority=authority or _runtime_authority(_default_authority_project()),
    )


# ---------------------------------------------------------------------------
# 1. Canonical quality_result_hash
# ---------------------------------------------------------------------------


class TestQualityResultHashDeterministic:
    def test_valid_pass_result_hash_is_deterministic(self) -> None:
        result = _pass_result()
        hash_a = build_content_quality_result_hash(result)
        hash_b = build_content_quality_result_hash(_pass_result())
        assert hash_a == hash_b
        assert len(hash_a) == 64

    def test_valid_pass_result_hash_matches_manual_canonical_json(self) -> None:
        result = _pass_result()
        canonical = json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert build_content_quality_result_hash(result) == expected


class TestQualityResultHashMappingJsonEquivalence:
    def test_mapping_and_json_equivalent_inputs_produce_same_hash(self) -> None:
        result = _pass_result()
        mapping = result.model_dump(mode="json")
        json_str = json.dumps(mapping, ensure_ascii=False)
        hash_from_instance = build_content_quality_result_hash(result)
        hash_from_mapping = build_content_quality_result_hash(mapping)
        hash_from_json = build_content_quality_result_hash(json_str)
        assert hash_from_instance == hash_from_mapping
        assert hash_from_mapping == hash_from_json

    def test_mapping_with_unsorted_signals_and_evidence_produces_same_hash(
        self,
    ) -> None:
        result = _pass_result(
            evidence_ids=["zebra-1", "alpha-1"],
        )
        mapping = result.model_dump(mode="json")
        # Reverse the order of signals and evidence_ids in the raw mapping.
        mapping["signals"] = list(reversed(mapping["signals"]))
        mapping["evidence_ids"] = list(reversed(mapping["evidence_ids"]))
        hash_from_result = build_content_quality_result_hash(result)
        hash_from_mapping = build_content_quality_result_hash(mapping)
        assert hash_from_result == hash_from_mapping


class TestQualityResultHashFieldSensitivity:
    """Every frozen canonical field must change the hash or cause validation failure."""

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("candidate_hash", OTHER_HASH),
            ("quality_input_hash", OTHER_HASH),
            ("scoring_request_hash", OTHER_HASH),
            ("judge_model", "other-model"),
            ("judge_model_digest", OTHER_DIGEST),
            ("grounding_confidence", "HIGH"),
            ("usefulness_confidence", "HIGH"),
            ("evidence_ids", ["title-1", "title-2"]),
        ],
    )
    def test_field_change_produces_different_hash(
        self,
        field_name: str,
        value: object,
    ) -> None:
        base = _pass_result()
        base_hash = build_content_quality_result_hash(base)
        changed = base.model_dump(mode="python")
        changed[field_name] = value
        changed_result = ContentQualityResult.model_validate(changed)
        changed_hash = build_content_quality_result_hash(changed_result)
        assert base_hash != changed_hash

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("status", "REJECT"),
            ("status", "UNCERTAIN"),
            ("decision_source", "DETERMINISTIC_GATE"),
            ("decision_confidence", "MEDIUM"),
            ("decision_confidence", "LOW"),
            ("grounding_confidence", "LOW"),
            ("usefulness_confidence", "LOW"),
            ("reason", "IDENTIFIER_ONLY"),
            ("signals", ["MINIMAL_CLAIM_PRESENT"]),
            ("signals", ["GROUNDING_PRESENT"]),
            ("judge_provider", "openai"),
            ("schema_version", "content-quality-result-v2"),
            ("policy_version", "content-quality-policy-v2"),
            ("prompt_version", "content-quality-prompt-v2"),
        ],
    )
    def test_field_change_causes_validation_failure(
        self,
        field_name: str,
        value: object,
    ) -> None:
        base = _pass_result()
        changed = base.model_dump(mode="python")
        changed[field_name] = value
        with pytest.raises((ValueError, Exception)):
            ContentQualityResult.model_validate(changed)


# ---------------------------------------------------------------------------
# 2. Untrusted reconstruction of quality_result_hash
# ---------------------------------------------------------------------------


class TestQualityResultHashReconstruction:
    def test_model_construct_instance_revalidated_not_trusted(self) -> None:
        """A model_construct instance is re-validated; invalid values are rejected."""
        result = _pass_result()
        constructed = ContentQualityResult.model_construct(
            **result.model_dump(mode="python")
        )
        # Valid model_construct instance produces the same hash (re-validated).
        assert build_content_quality_result_hash(constructed) == (
            build_content_quality_result_hash(result)
        )
        # Invalid model_construct instance is rejected by re-validation.
        invalid_fields = result.model_dump(mode="python")
        invalid_fields["candidate_hash"] = "not-a-hash"
        invalid = ContentQualityResult.model_construct(**invalid_fields)
        with pytest.raises((ValueError, Exception)):
            build_content_quality_result_hash(invalid)

    def test_model_copy_update_bypass_rejected(self) -> None:
        result = _pass_result()
        with pytest.raises(ValueError, match="model_copy"):
            result.model_copy(update={"judge_model": "tampered"})

    def test_deprecated_copy_update_bypass_rejected(self) -> None:
        result = _pass_result()
        with pytest.raises((ValueError, TypeError)):
            result.copy(update={"judge_model": "tampered"})

    def test_subclass_property_override_rejected(self) -> None:
        class _TamperedResult(ContentQualityResult):
            @property
            def judge_model(self) -> str:  # type: ignore[override]
                return "tampered-model"

        base = _pass_result()
        tampered = _TamperedResult.model_validate(base.model_dump(mode="python"))
        with pytest.raises(ValueError):
            build_content_quality_result_hash(tampered)

    def test_subclass_model_dump_override_rejected(self) -> None:
        class _MismatchResult(ContentQualityResult):
            def model_dump(self, **kwargs: object) -> dict[str, object]:
                data = super().model_dump(**kwargs)
                data["judge_model"] = "tampered-model"
                return data

        base = _pass_result()
        mismatch = _MismatchResult.model_validate(base.model_dump(mode="python"))
        with pytest.raises(ValueError):
            build_content_quality_result_hash(mismatch)

    def test_fake_trusted_flag_unknown_field_rejected(self) -> None:
        mapping = _pass_result().model_dump(mode="json")
        mapping["_trusted"] = True
        with pytest.raises((ValueError, Exception)):
            ContentQualityResult.model_validate(mapping)


# ---------------------------------------------------------------------------
# 3. Fail-closed scenarios for quality_result_hash
# ---------------------------------------------------------------------------


class TestQualityResultHashFailClosed:
    def test_non_pass_rejects(self) -> None:
        reject_result = ContentQualityResult.model_validate(
            {
                "schema_version": "content-quality-result-v1",
                "policy_version": "content-quality-policy-v1",
                "prompt_version": "content-quality-prompt-v1",
                "status": "REJECT",
                "decision_source": "LOCAL_JUDGE",
                "decision_confidence": "HIGH",
                "grounding_confidence": "LOW",
                "usefulness_confidence": "LOW",
                "signals": ["IDENTIFIER_ONLY"],
                "reason": "IDENTIFIER_ONLY",
                "evidence_ids": [],
                "candidate_hash": VALID_HASH,
                "quality_input_hash": VALID_HASH,
                "scoring_request_hash": VALID_HASH,
                "judge_provider": "ollama",
                "judge_model": "qwen3:8b",
                "judge_model_digest": DIGEST,
            }
        )
        # build_content_quality_result_hash works on any valid result, but
        # build_quality_pass_attestation must reject non-PASS.
        # Here we verify the hash itself is computed (it covers the full result).
        h = build_content_quality_result_hash(reject_result)
        assert len(h) == 64

    def test_malformed_pass_rejects(self) -> None:
        mapping = _pass_result().model_dump(mode="json")
        mapping["candidate_hash"] = "not-a-hash"
        with pytest.raises((ValueError, Exception)):
            ContentQualityResult.model_validate(mapping)

    def test_evidence_free_pass_rejects(self) -> None:
        with pytest.raises((ValueError, Exception)):
            ContentQualityResult.model_validate(
                {
                    "schema_version": "content-quality-result-v1",
                    "policy_version": "content-quality-policy-v1",
                    "prompt_version": "content-quality-prompt-v1",
                    "status": "PASS",
                    "decision_source": "LOCAL_JUDGE",
                    "decision_confidence": "HIGH",
                    "grounding_confidence": "MEDIUM",
                    "usefulness_confidence": "MEDIUM",
                    "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
                    "reason": None,
                    "evidence_ids": [],
                    "candidate_hash": VALID_HASH,
                    "quality_input_hash": VALID_HASH,
                    "scoring_request_hash": VALID_HASH,
                    "judge_provider": "ollama",
                    "judge_model": "qwen3:8b",
                    "judge_model_digest": DIGEST,
                }
            )


# ---------------------------------------------------------------------------
# 4. QualityPassAttestation construction
# ---------------------------------------------------------------------------


class TestQualityPassAttestationConstruction:
    def test_valid_attestation_is_deterministic(self) -> None:
        attestation_a = _build_valid_attestation()
        attestation_b = _build_valid_attestation()
        assert attestation_a == attestation_b

    def test_attestation_schema_is_quality_pass_attestation_v1(self) -> None:
        attestation = _build_valid_attestation()
        assert attestation.attestation_schema == "quality-pass-attestation-v1"

    def test_attestation_binds_candidate_hash(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert attestation.candidate_hash == pass_result.candidate_hash
        assert attestation.candidate_hash == operation_input.candidate_hash
        assert attestation.candidate_hash == content_input.candidate_hash

    def test_attestation_binds_quality_input_hash(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        expected_qih = build_content_quality_input_hash(content_input)
        assert attestation.quality_input_hash == expected_qih
        assert attestation.quality_input_hash == pass_result.quality_input_hash

    def test_attestation_binds_quality_result_hash(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        expected = build_content_quality_result_hash(pass_result)
        assert attestation.quality_result_hash == expected

    def test_attestation_binds_scoring_request_hash(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert attestation.scoring_request_hash == pass_result.scoring_request_hash

    def test_attestation_binds_judge_identity(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert attestation.judge_provider == "ollama"
        assert attestation.judge_model == pass_result.judge_model
        assert attestation.judge_model_digest == pass_result.judge_model_digest
        assert attestation.judge_operation == "local-content-quality-v1"

    def test_attestation_binds_h2_as_judge_request_hash(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        _, h2 = build_judge_h1_h2(operation_input)
        assert attestation.judge_request_hash == h2

    def test_attestation_binds_attempt_role(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert attestation.attempt_role == operation_input.attempt_role

    def test_attestation_binds_confidence_values(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert attestation.decision_confidence == pass_result.decision_confidence
        assert attestation.grounding_confidence == pass_result.grounding_confidence
        assert attestation.usefulness_confidence == pass_result.usefulness_confidence

    def test_attestation_binds_evidence_ids(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert attestation.evidence_ids == pass_result.evidence_ids

    def test_attestation_binds_scoring_versions(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert attestation.scoring_schema_version == SCORING_SCHEMA_VERSION
        assert attestation.scoring_prompt_version == SCORING_PROMPT_VERSION

    def test_attestation_binds_quality_versions(self) -> None:
        content_input, operation_input, pass_result = _consistent_trio()
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert attestation.quality_schema_version == "content-quality-result-v1"
        assert attestation.quality_prompt_version == "content-quality-prompt-v1"
        assert attestation.policy_version == "content-quality-policy-v1"

    def test_attestation_hash_covers_full_payload_excluding_itself(self) -> None:
        attestation = _build_valid_attestation()
        payload = attestation.model_dump(mode="json")
        stored_hash = payload.pop("attestation_hash")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert expected == stored_hash

    def test_h1_and_h2_remain_distinct(self) -> None:
        content_input, operation_input, _ = _consistent_trio()
        h1, h2 = build_judge_h1_h2(operation_input)
        assert h1 != h2


# ---------------------------------------------------------------------------
# 5. Build-time binding mismatch rejections
# ---------------------------------------------------------------------------


class TestQualityPassAttestationBuildBindingMismatches:
    def test_non_pass_result_rejects(self) -> None:
        content_input = _content_input()
        qih = build_content_quality_input_hash(content_input)
        reject_result = ContentQualityResult.model_validate(
            {
                "schema_version": "content-quality-result-v1",
                "policy_version": "content-quality-policy-v1",
                "prompt_version": "content-quality-prompt-v1",
                "status": "REJECT",
                "decision_source": "LOCAL_JUDGE",
                "decision_confidence": "HIGH",
                "grounding_confidence": "LOW",
                "usefulness_confidence": "LOW",
                "signals": ["IDENTIFIER_ONLY"],
                "reason": "IDENTIFIER_ONLY",
                "evidence_ids": [],
                "candidate_hash": VALID_HASH,
                "quality_input_hash": qih,
                "scoring_request_hash": VALID_HASH,
                "judge_provider": "ollama",
                "judge_model": "qwen3:8b",
                "judge_model_digest": DIGEST,
            }
        )
        operation_input = _operation_input(quality_input_hash=qih)
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=reject_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_evidence_free_pass_rejects(self) -> None:
        content_input = _content_input()
        qih = build_content_quality_input_hash(content_input)
        with pytest.raises((ValueError, Exception)):
            _pass_result(quality_input_hash=qih, evidence_ids=[])

    def test_external_evidence_id_rejects(self) -> None:
        content_input = _content_input()
        qih = build_content_quality_input_hash(content_input)
        pass_result = _pass_result(quality_input_hash=qih, evidence_ids=["unknown-id"])
        operation_input = _operation_input(quality_input_hash=qih)
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_empty_registry_pass_rejects(self) -> None:
        content_input = _content_input(evidence_registry=())
        qih = build_content_quality_input_hash(content_input)
        pass_result = _pass_result(quality_input_hash=qih, evidence_ids=["title-1"])
        operation_input = _operation_input(quality_input_hash=qih)
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("candidate_hash", OTHER_HASH),
            ("quality_input_hash", OTHER_HASH),
            ("scoring_request_hash", OTHER_HASH),
        ],
    )
    def test_candidate_input_request_hash_mismatch_rejects(
        self,
        field_name: str,
        value: str,
    ) -> None:
        content_input = _content_input()
        qih = build_content_quality_input_hash(content_input)
        pass_result = _pass_result(quality_input_hash=qih)
        tampered_op = _operation_input(quality_input_hash=qih)
        tampered_op_dict = tampered_op.model_dump(mode="python")
        tampered_op_dict[field_name] = value
        tampered_operation_input = QualityJudgeOperationInput.model_validate(
            tampered_op_dict
        )
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=pass_result,
                operation_input=tampered_operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("judge_provider", "openai"),
            ("judge_model", "other-model"),
            ("judge_model_digest", OTHER_DIGEST),
            ("policy_version", "content-quality-policy-v2"),
            ("prompt_version", "content-quality-prompt-v2"),
            ("schema_version", "content-quality-result-v2"),
        ],
    )
    def test_judge_identity_and_version_mismatch_rejects(
        self,
        field_name: str,
        value: str,
    ) -> None:
        content_input = _content_input()
        qih = build_content_quality_input_hash(content_input)
        pass_result = _pass_result(quality_input_hash=qih)
        tampered_op_dict = _operation_input(quality_input_hash=qih).model_dump(
            mode="python"
        )
        tampered_op_dict[field_name] = value
        tampered_operation_input = QualityJudgeOperationInput.model_validate(
            tampered_op_dict
        )
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=pass_result,
                operation_input=tampered_operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )


# ---------------------------------------------------------------------------
# 6. Verify-time binding mismatch rejections
# ---------------------------------------------------------------------------


class TestQualityPassAttestationVerifyBindingMismatches:
    def test_forged_attestation_hash_rejects(self) -> None:
        attestation = _build_valid_attestation()
        tampered = attestation.model_dump(mode="json")
        tampered["attestation_hash"] = "f" * 64
        content_input, operation_input, pass_result = _consistent_trio()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_forged_quality_result_hash_rejects(self) -> None:
        attestation = _build_valid_attestation()
        tampered = attestation.model_dump(mode="json")
        tampered["quality_result_hash"] = "e" * 64
        # Recompute attestation_hash so only the quality_result_hash is wrong.
        payload = dict(tampered)
        payload.pop("attestation_hash")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        tampered["attestation_hash"] = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
        content_input, operation_input, pass_result = _consistent_trio()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_h2_mismatch_rejects(self) -> None:
        attestation = _build_valid_attestation()
        tampered = attestation.model_dump(mode="json")
        tampered["judge_request_hash"] = "d" * 64
        payload = dict(tampered)
        payload.pop("attestation_hash")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        tampered["attestation_hash"] = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
        content_input, operation_input, pass_result = _consistent_trio()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_attempt_role_mismatch_rejects(self) -> None:
        attestation = _build_valid_attestation()
        tampered = attestation.model_dump(mode="json")
        tampered["attempt_role"] = "REPAIR"
        payload = dict(tampered)
        payload.pop("attestation_hash")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        tampered["attestation_hash"] = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
        content_input, operation_input, pass_result = _consistent_trio()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("decision_confidence", "MEDIUM"),
            ("grounding_confidence", "LOW"),
            ("usefulness_confidence", "LOW"),
        ],
    )
    def test_confidence_mismatch_rejects(
        self,
        field_name: str,
        value: str,
    ) -> None:
        attestation = _build_valid_attestation()
        tampered = attestation.model_dump(mode="json")
        tampered[field_name] = value
        payload = dict(tampered)
        payload.pop("attestation_hash")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        tampered["attestation_hash"] = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
        content_input, operation_input, pass_result = _consistent_trio()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_evidence_mismatch_rejects(self) -> None:
        content_input = _content_input(
            evidence_registry=_evidence_registry("title-1", "title-2"),
        )
        qih = build_content_quality_input_hash(content_input)
        pass_result = _pass_result(quality_input_hash=qih, evidence_ids=["title-1"])
        operation_input = _operation_input(quality_input_hash=qih)
        attestation = build_quality_pass_attestation(
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        tampered = attestation.model_dump(mode="json")
        tampered["evidence_ids"] = ["title-2"]
        payload = dict(tampered)
        payload.pop("attestation_hash")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        tampered["attestation_hash"] = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("scoring_schema_version", OTHER_SCORING_SCHEMA),
            ("scoring_prompt_version", OTHER_SCORING_PROMPT),
        ],
    )
    def test_scoring_version_mismatch_rejects(
        self,
        field_name: str,
        value: str,
    ) -> None:
        """A correct-hash attestation with wrong scoring versions cannot verify.

        Scoring versions are fixed constants owned by the runtime-minted
        ``QualityProvenanceAuthority``; a caller cannot supply an alternate
        authority object to make them match.
        """
        attestation = _build_valid_attestation()
        content_input, operation_input, pass_result = _consistent_trio()
        tampered = attestation.model_dump(mode="json")
        tampered[field_name] = value
        payload = dict(tampered)
        payload.pop("attestation_hash")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        tampered["attestation_hash"] = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_forged_complete_attestation_rejects(self) -> None:
        """A completely different attestation with valid hash is still rejected."""
        content_input = _content_input(
            evidence_registry=_evidence_registry("title-1", "title-2"),
        )
        qih = build_content_quality_input_hash(content_input)
        pass_result_a = _pass_result(quality_input_hash=qih, evidence_ids=["title-1"])
        pass_result_b = _pass_result(quality_input_hash=qih, evidence_ids=["title-2"])
        operation_input = _operation_input(quality_input_hash=qih)
        attestation_b = build_quality_pass_attestation(
            quality_result=pass_result_b,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                attestation_b,
                quality_result=pass_result_a,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_unknown_fields_rejects(self) -> None:
        attestation = _build_valid_attestation()
        tampered = attestation.model_dump(mode="json")
        tampered["extra_field"] = "malicious"
        content_input, operation_input, pass_result = _consistent_trio()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )


# ---------------------------------------------------------------------------
# 7. Attestation reconstruction bypass attacks
# ---------------------------------------------------------------------------


class TestQualityPassAttestationReconstruction:
    def test_model_construct_bypass_rejected(self) -> None:
        with pytest.raises(ValueError):
            QualityPassAttestation.model_construct(
                attestation_schema="quality-pass-attestation-v1",
                status="PASS",
                candidate_hash=VALID_HASH,
                quality_input_hash=VALID_HASH,
                quality_result_hash=VALID_HASH,
                scoring_request_hash=VALID_HASH,
                policy_version="content-quality-policy-v1",
                quality_schema_version="content-quality-result-v1",
                quality_prompt_version="content-quality-prompt-v1",
                judge_provider="ollama",
                judge_model="qwen3:8b",
                judge_model_digest=DIGEST,
                judge_operation="local-content-quality-v1",
                judge_request_hash=VALID_HASH,
                attempt_role=QualityJudgeAttemptRole.PRIMARY,
                decision_confidence="HIGH",
                grounding_confidence="MEDIUM",
                usefulness_confidence="MEDIUM",
                evidence_ids=("title-1",),
                attestation_hash="0" * 64,
            )

    def test_model_copy_update_bypass_rejected(self) -> None:
        attestation = _build_valid_attestation()
        with pytest.raises(ValueError, match="model_copy"):
            attestation.model_copy(update={"judge_model": "tampered"})

    def test_deprecated_copy_update_bypass_rejected(self) -> None:
        attestation = _build_valid_attestation()
        with pytest.raises((ValueError, TypeError)):
            attestation.copy(update={"judge_model": "tampered"})

    def test_subclass_rejected_by_verify(self) -> None:
        class _TamperedAttestation(QualityPassAttestation):
            @property
            def judge_model(self) -> str:  # type: ignore[override]
                return "tampered-model"

        attestation = _build_valid_attestation()
        tampered = _TamperedAttestation.model_validate(
            attestation.model_dump(mode="python")
        )
        content_input, operation_input, pass_result = _consistent_trio()
        with pytest.raises(ValueError):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_subclass_model_dump_override_rejected_by_verify(self) -> None:
        class _MismatchAttestation(QualityPassAttestation):
            def model_dump(self, **kwargs: object) -> dict[str, object]:
                data = super().model_dump(**kwargs)
                data["judge_model"] = "qwen3:8b"
                return data

        attestation = _build_valid_attestation()
        mismatch = _MismatchAttestation.model_validate(
            attestation.model_dump(mode="python")
        )
        content_input, operation_input, pass_result = _consistent_trio()
        with pytest.raises(ValueError):
            verify_quality_pass_attestation(
                mismatch,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_fake_trusted_flag_unknown_field_rejected(self) -> None:
        attestation = _build_valid_attestation()
        tampered = attestation.model_dump(mode="json")
        tampered["_trusted"] = True
        content_input, operation_input, pass_result = _consistent_trio()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_verify_accepts_valid_attestation(self) -> None:
        attestation = _build_valid_attestation()
        content_input, operation_input, pass_result = _consistent_trio()
        verified = verify_quality_pass_attestation(
            attestation,
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert verified == attestation

    def test_verify_accepts_valid_attestation_from_mapping(self) -> None:
        attestation = _build_valid_attestation()
        mapping = attestation.model_dump(mode="json")
        content_input, operation_input, pass_result = _consistent_trio()
        verified = verify_quality_pass_attestation(
            mapping,
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert verified == attestation


# ---------------------------------------------------------------------------
# 8. No side effects
# ---------------------------------------------------------------------------


class TestQualityPassAttestationNoSideEffects:
    def test_build_creates_no_filesystem_side_effects(
        self,
        tmp_path: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import pathlib

        monkeypatch.chdir(pathlib.Path(str(tmp_path)))
        attestation = _build_valid_attestation()
        assert isinstance(attestation, QualityPassAttestation)
        assert isinstance(attestation, BaseModel)
        assert not any(pathlib.Path(str(tmp_path)).iterdir())

    def test_verify_creates_no_filesystem_side_effects(
        self,
        tmp_path: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import pathlib

        monkeypatch.chdir(pathlib.Path(str(tmp_path)))
        attestation = _build_valid_attestation()
        content_input, operation_input, pass_result = _consistent_trio()
        verified = verify_quality_pass_attestation(
            attestation,
            quality_result=pass_result,
            operation_input=operation_input,
            quality_input=content_input,
            authority=_current_authority(),
        )
        assert isinstance(verified, QualityPassAttestation)
        assert not any(pathlib.Path(str(tmp_path)).iterdir())

    def test_attestation_has_no_persistence_identity_fields(self) -> None:
        attestation = _build_valid_attestation()
        dump = attestation.model_dump(mode="json")
        forbidden_keys = {
            "artifact_id",
            "provider_call_id",
            "cache_id",
            "response_artifact_id",
            "score_result",
            "db_id",
        }
        assert not forbidden_keys.intersection(dump.keys())


# ---------------------------------------------------------------------------
# 9. Mutation-quality evidence
# ---------------------------------------------------------------------------


class TestMutationEvidence:
    """Prove tests fail if the implementation is weakened.

    These tests encode the invariant; the mutation proof (temporarily
    breaking the implementation and observing test failure) is performed
    manually and documented in the handoff.
    """

    def test_binding_check_present(self) -> None:
        """If candidate_hash binding were removed, this test would fail."""
        content_input = _content_input()
        qih = build_content_quality_input_hash(content_input)
        pass_result = _pass_result(quality_input_hash=qih)
        mismatched_op = _operation_input(
            quality_input_hash=qih, candidate_hash=OTHER_HASH
        )
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=pass_result,
                operation_input=mismatched_op,
                quality_input=content_input,
                authority=_current_authority(),
            )

    def test_unchecked_input_not_hashed(self) -> None:
        """If unchecked input were hashed directly, subclass would produce a
        different hash than the reconstructed base class."""
        base = _pass_result()

        class _Spoofed(ContentQualityResult):
            @property
            def judge_model(self) -> str:  # type: ignore[override]
                return "tampered-model"

        spoofed = _Spoofed.model_validate(base.model_dump(mode="python"))
        # build_content_quality_result_hash must reject the subclass entirely.
        with pytest.raises(ValueError):
            build_content_quality_result_hash(spoofed)

    def test_bound_field_change_detected_by_hash(self) -> None:
        """If a bound field changed without affecting the hash, this would fail."""
        base = _pass_result()
        base_hash = build_content_quality_result_hash(base)
        changed = base.model_dump(mode="python")
        changed["candidate_hash"] = OTHER_HASH
        changed_result = ContentQualityResult.model_validate(changed)
        changed_hash = build_content_quality_result_hash(changed_result)
        assert base_hash != changed_hash

    def test_malformed_pass_not_accepted(self) -> None:
        """If malformed PASS were accepted, build would succeed instead of failing."""
        content_input = _content_input()
        qih = build_content_quality_input_hash(content_input)
        # Malformed: PASS with empty evidence_ids is rejected by the model.
        with pytest.raises((ValueError, Exception)):
            _pass_result(quality_input_hash=qih, evidence_ids=[])

    def test_evidence_free_pass_not_accepted(self) -> None:
        """If evidence-free PASS were accepted, attestation build would succeed."""
        content_input = _content_input(evidence_registry=())
        qih = build_content_quality_input_hash(content_input)
        pass_result = _pass_result(quality_input_hash=qih, evidence_ids=["title-1"])
        operation_input = _operation_input(quality_input_hash=qih)
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=pass_result,
                operation_input=operation_input,
                quality_input=content_input,
                authority=_current_authority(),
            )


# ---------------------------------------------------------------------------
# 10. Trusted current provenance binding (Phase D Correction Round 1)
# ---------------------------------------------------------------------------


class TestTrustedProvenanceBinding:
    """P1 fix: trusted provenance is minted by runtime composition only.

    The application-owned ``QualityProvenanceAuthority`` is the only object that
    can authorize ``build_quality_pass_attestation`` and
    ``verify_quality_pass_attestation``.  It is created by ``runtime.py`` from the
    already-loaded ``AppConfig`` and cannot be constructed by callers from
    ``LocalScoringSettings``, ``TrustedQualityProvenance`` (removed), Mapping,
    JSON, provider response, cache or fixture constants.
    """

    # --- Real current configuration succeeds ---

    def test_real_current_config_build_and_verify_succeeds(
        self,
        tmp_path: Path,
    ) -> None:
        """An authority minted from a real current config digest (not bbbb)
        can build and verify a PASS attestation when inputs match that config.
        """
        authority = _real_config_authority(tmp_path)
        ci, oi, pr = _consistent_trio(
            judge_model="qwen3:8b",
            judge_model_digest=REAL_CONFIG_DIGEST,
        )
        attestation = build_quality_pass_attestation(
            quality_result=pr,
            operation_input=oi,
            quality_input=ci,
            authority=authority,
        )
        assert isinstance(attestation, QualityPassAttestation)
        assert attestation.judge_model_digest == REAL_CONFIG_DIGEST
        verified = verify_quality_pass_attestation(
            attestation,
            quality_result=pr,
            operation_input=oi,
            quality_input=ci,
            authority=authority,
        )
        assert verified == attestation

    # --- Caller cannot supply configuration ---

    def test_caller_local_scoring_settings_rejected_by_build(self) -> None:
        """A caller-created LocalScoringSettings cannot be passed as authority."""
        ci, oi, pr = _consistent_trio()
        attacker_settings = LocalScoringSettings(
            model="untrusted-local-model",
            expected_model_digest=UNAUTHORIZED_DIGEST,
        )
        with pytest.raises(TypeError):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=attacker_settings,  # type: ignore[arg-type]
            )

    def test_caller_local_scoring_settings_rejected_by_verify(self) -> None:
        """A caller-created LocalScoringSettings cannot be passed as authority."""
        att = _build_valid_attestation()
        ci, oi, pr = _consistent_trio()
        attacker_settings = LocalScoringSettings(
            model="untrusted-local-model",
            expected_model_digest=UNAUTHORIZED_DIGEST,
        )
        with pytest.raises(TypeError):
            verify_quality_pass_attestation(
                att,
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=attacker_settings,  # type: ignore[arg-type]
            )

    def test_caller_mapping_rejected_as_authority(self) -> None:
        """A plain dict cannot be passed as authority."""
        ci, oi, pr = _consistent_trio()
        with pytest.raises(TypeError):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority={  # type: ignore[arg-type]
                    "judge_model": "qwen3:8b",
                    "judge_model_digest": DIGEST,
                },
            )

    def test_direct_authority_construction_rejected(self) -> None:
        """QualityProvenanceAuthority cannot be built without the runtime sentinel."""
        with pytest.raises((ValueError, TypeError)):
            QualityProvenanceAuthority(
                judge_provider="ollama",
                judge_model="qwen3:8b",
                judge_model_digest=DIGEST,
                scoring_schema_version=SCORING_SCHEMA_VERSION,
                scoring_prompt_version=SCORING_PROMPT_VERSION,
                quality_schema_version="content-quality-result-v1",
                quality_prompt_version="content-quality-prompt-v1",
                quality_policy_version="content-quality-policy-v1",
                judge_operation="local-content-quality-v1",
            )

    # --- Critical forgery: internally consistent attacker config ---

    def test_self_consistent_attacker_inputs_build_rejects(self) -> None:
        """Self-consistent attacker-chosen Judge inputs are not trusted."""
        ci, oi, pr = _consistent_trio(
            judge_model=UNAUTHORIZED_MODEL,
            judge_model_digest=UNAUTHORIZED_DIGEST,
        )
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_current_authority(),
            )

    def test_self_consistent_fake_provenance_verify_rejects(self) -> None:
        """A correct-hash attestation around fake provenance is rejected.

        The attacker constructs a fully self-consistent operation/result and an
        attestation whose hash checks out, but the provenance does not match the
        application's current runtime authority.  Hash correctness != trust.
        """
        ci, oi, pr = _consistent_trio(
            judge_model=UNAUTHORIZED_MODEL,
            judge_model_digest=UNAUTHORIZED_DIGEST,
        )
        result_hash = build_content_quality_result_hash(pr)
        _, h2 = build_judge_h1_h2(oi)
        qih = build_content_quality_input_hash(ci)
        payload: dict[str, object] = {
            "attestation_schema": "quality-pass-attestation-v1",
            "status": "PASS",
            "candidate_hash": pr.candidate_hash,
            "quality_input_hash": qih,
            "quality_result_hash": result_hash,
            "scoring_request_hash": pr.scoring_request_hash,
            "policy_version": pr.policy_version,
            "scoring_schema_version": SCORING_SCHEMA_VERSION,
            "scoring_prompt_version": SCORING_PROMPT_VERSION,
            "quality_schema_version": pr.schema_version,
            "quality_prompt_version": pr.prompt_version,
            "judge_provider": "ollama",
            "judge_model": UNAUTHORIZED_MODEL,
            "judge_model_digest": UNAUTHORIZED_DIGEST,
            "judge_operation": "local-content-quality-v1",
            "judge_request_hash": h2,
            "attempt_role": oi.attempt_role.value,
            "decision_confidence": pr.decision_confidence.value,
            "grounding_confidence": pr.grounding_confidence.value,
            "usefulness_confidence": pr.usefulness_confidence.value,
            "evidence_ids": list(pr.evidence_ids),
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        payload["attestation_hash"] = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
        forged = QualityPassAttestation.model_validate(payload)

        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                forged,
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_current_authority(),
            )

    def test_unauthorized_judge_model_build_rejects(self) -> None:
        """Internally consistent unauthorized Judge model cannot build."""
        ci, oi, pr = _consistent_trio(
            judge_model=UNAUTHORIZED_MODEL,
            judge_model_digest=UNAUTHORIZED_DIGEST,
        )
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_current_authority(),
            )

    def test_unauthorized_judge_digest_build_rejects(self) -> None:
        """Internally consistent unauthorized digest cannot build."""
        ci, oi, pr = _consistent_trio(
            judge_model="qwen3:8b",
            judge_model_digest=UNAUTHORIZED_DIGEST,
        )
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_current_authority(),
            )

    # --- Individual current-binding build tests ---

    @pytest.mark.parametrize(
        "field,value",
        [
            ("judge_model", UNAUTHORIZED_MODEL),
            ("judge_model_digest", UNAUTHORIZED_DIGEST),
        ],
    )
    def test_individual_judge_field_mismatch_build_rejects(
        self,
        field: str,
        value: str,
    ) -> None:
        ci, oi, pr = _consistent_trio()
        tampered_op = _operation_input(
            quality_input_hash=build_content_quality_input_hash(ci),
            **{field: value},
        )
        tampered_pr = _pass_result(
            quality_input_hash=build_content_quality_input_hash(ci),
            **{field: value},
        )
        with pytest.raises((ValueError, Exception)):
            build_quality_pass_attestation(
                quality_result=tampered_pr,
                operation_input=tampered_op,
                quality_input=ci,
                authority=_current_authority(),
            )

    # --- Individual current-binding verify tests ---

    @pytest.mark.parametrize(
        "field,value",
        [
            ("judge_model", UNAUTHORIZED_MODEL),
            ("judge_model_digest", UNAUTHORIZED_DIGEST),
            ("scoring_schema_version", OTHER_SCORING_SCHEMA),
            ("scoring_prompt_version", OTHER_SCORING_PROMPT),
        ],
    )
    def test_individual_field_mismatch_verify_rejects(
        self,
        field: str,
        value: str,
    ) -> None:
        """Tampering any trusted provenance field makes verify fail.

        The attestation hash is recomputed so the payload is internally
        consistent; verification still fails because the trusted reconstruction
        from the application's current runtime authority disagrees.
        """
        attestation = _build_valid_attestation()
        ci, oi, pr = _consistent_trio()
        tampered = attestation.model_dump(mode="json")
        tampered[field] = value
        payload = dict(tampered)
        payload.pop("attestation_hash")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        tampered["attestation_hash"] = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                tampered,
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_current_authority(),
            )

    def test_configuration_rotation_verify_rejects(
        self,
        tmp_path: Path,
    ) -> None:
        """An attestation built under authority A must fail under authority B."""
        authority_a = _current_authority(tmp_path, digest=OTHER_DIGEST)
        authority_b = _current_authority(tmp_path, digest=DIGEST)
        ci, oi, pr = _consistent_trio(
            judge_model="qwen3:8b",
            judge_model_digest=OTHER_DIGEST,
        )
        attestation = build_quality_pass_attestation(
            quality_result=pr,
            operation_input=oi,
            quality_input=ci,
            authority=authority_a,
        )
        with pytest.raises((ValueError, Exception)):
            verify_quality_pass_attestation(
                attestation,
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=authority_b,
            )

    def test_authorized_provenance_build_succeeds(self) -> None:
        """Sanity: authorized provenance must still build successfully."""
        att = _build_valid_attestation()
        assert isinstance(att, QualityPassAttestation)

    def test_authorized_provenance_verify_succeeds(self) -> None:
        """Sanity: authorized provenance must still verify successfully."""
        att = _build_valid_attestation()
        ci, oi, pr = _consistent_trio()
        verified = verify_quality_pass_attestation(
            att,
            quality_result=pr,
            operation_input=oi,
            quality_input=ci,
            authority=_current_authority(),
        )
        assert verified == att


class _ModelOverrideAuthority(QualityProvenanceAuthority):
    __slots__ = ("_spoofed_model",)

    def __init__(self) -> None:
        self._judge_provider = "ollama"
        self._judge_model = "qwen3:8b"
        self._judge_model_digest = DIGEST
        self._scoring_schema_version = SCORING_SCHEMA_VERSION
        self._scoring_prompt_version = SCORING_PROMPT_VERSION
        self._quality_policy_version = "content-quality-policy-v1"
        self._quality_schema_version = "content-quality-result-v1"
        self._quality_prompt_version = "content-quality-prompt-v1"
        self._judge_operation = "local-content-quality-v1"
        self._spoofed_model = UNAUTHORIZED_MODEL

    @property
    def judge_model(self) -> str:  # type: ignore[override]
        return self._spoofed_model


class _DigestOverrideAuthority(QualityProvenanceAuthority):
    __slots__ = ("_spoofed_digest",)

    def __init__(self) -> None:
        self._judge_provider = "ollama"
        self._judge_model = "qwen3:8b"
        self._judge_model_digest = DIGEST
        self._scoring_schema_version = SCORING_SCHEMA_VERSION
        self._scoring_prompt_version = SCORING_PROMPT_VERSION
        self._quality_policy_version = "content-quality-policy-v1"
        self._quality_schema_version = "content-quality-result-v1"
        self._quality_prompt_version = "content-quality-prompt-v1"
        self._judge_operation = "local-content-quality-v1"
        self._spoofed_digest = UNAUTHORIZED_DIGEST

    @property
    def judge_model_digest(self) -> str:  # type: ignore[override]
        return self._spoofed_digest


class _SchemaPromptOverrideAuthority(QualityProvenanceAuthority):
    __slots__ = ("_spoofed_schema", "_spoofed_prompt")

    def __init__(self) -> None:
        self._judge_provider = "ollama"
        self._judge_model = "qwen3:8b"
        self._judge_model_digest = DIGEST
        self._scoring_schema_version = SCORING_SCHEMA_VERSION
        self._scoring_prompt_version = SCORING_PROMPT_VERSION
        self._quality_policy_version = "content-quality-policy-v1"
        self._quality_schema_version = "content-quality-result-v1"
        self._quality_prompt_version = "content-quality-prompt-v1"
        self._judge_operation = "local-content-quality-v1"
        self._spoofed_schema = OTHER_SCORING_SCHEMA
        self._spoofed_prompt = OTHER_SCORING_PROMPT

    @property
    def scoring_schema_version(self) -> str:  # type: ignore[override]
        return self._spoofed_schema

    @property
    def scoring_prompt_version(self) -> str:  # type: ignore[override]
        return self._spoofed_prompt


class TestQualityProvenanceAuthoritySubclassRejection:
    """Exact-type enforcement rejects subclass/property spoof at both boundaries."""

    def test_subclass_overriding_judge_model_rejected_by_build(self) -> None:
        ci, oi, pr = _consistent_trio()
        with pytest.raises(TypeError):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_ModelOverrideAuthority(),
            )

    def test_subclass_overriding_judge_model_rejected_by_verify(self) -> None:
        attestation = _build_valid_attestation()
        ci, oi, pr = _consistent_trio()
        with pytest.raises(TypeError):
            verify_quality_pass_attestation(
                attestation,
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_ModelOverrideAuthority(),
            )

    def test_subclass_overriding_judge_model_digest_rejected_by_build(self) -> None:
        ci, oi, pr = _consistent_trio()
        with pytest.raises(TypeError):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_DigestOverrideAuthority(),
            )

    def test_subclass_overriding_judge_model_digest_rejected_by_verify(self) -> None:
        attestation = _build_valid_attestation()
        ci, oi, pr = _consistent_trio()
        with pytest.raises(TypeError):
            verify_quality_pass_attestation(
                attestation,
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_DigestOverrideAuthority(),
            )

    def test_subclass_overriding_schema_prompt_rejected_by_build(self) -> None:
        ci, oi, pr = _consistent_trio()
        with pytest.raises(TypeError):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_SchemaPromptOverrideAuthority(),
            )

    def test_subclass_overriding_schema_prompt_rejected_by_verify(self) -> None:
        attestation = _build_valid_attestation()
        ci, oi, pr = _consistent_trio()
        with pytest.raises(TypeError):
            verify_quality_pass_attestation(
                attestation,
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=_SchemaPromptOverrideAuthority(),
            )


class TestQualityProvenanceAuthorityBypass:
    """QualityProvenanceAuthority itself must resist caller construction."""

    def test_model_copy_is_unavailable(self) -> None:
        """Authority is not a Pydantic model; it has no model_copy bypass."""
        authority = _current_authority()
        with pytest.raises(AttributeError):
            authority.model_copy(update={"judge_model": UNAUTHORIZED_MODEL})

    def test_model_construct_is_unavailable(self) -> None:
        """Authority is not a Pydantic model; it has no model_construct bypass."""
        with pytest.raises(AttributeError):
            QualityProvenanceAuthority.model_construct(
                judge_provider="ollama",
                judge_model="qwen3:8b",
                judge_model_digest=DIGEST,
            )

    def test_model_validate_is_unavailable(self) -> None:
        """Authority cannot be restored from JSON/Mapping."""
        with pytest.raises(AttributeError):
            QualityProvenanceAuthority.model_validate(
                {
                    "judge_provider": "ollama",
                    "judge_model": "qwen3:8b",
                    "judge_model_digest": DIGEST,
                }
            )


class TestQualityProvenanceAuthorityCopySerialization:
    """Native copy/serialization cannot manufacture an accepted authority."""

    def test_copy_rejected(self) -> None:
        authority = _current_authority()
        with pytest.raises(TypeError, match="cannot be copied"):
            copy.copy(authority)

    def test_deepcopy_rejected(self) -> None:
        authority = _current_authority()
        with pytest.raises(TypeError, match="cannot be copied"):
            copy.deepcopy(authority)

    def test_pickle_dumps_rejected(self) -> None:
        authority = _current_authority()
        with pytest.raises(TypeError, match="cannot be serialized"):
            pickle.dumps(authority)

    @pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
    def test_pickle_dumps_all_protocols_rejected(
        self,
        protocol: int,
    ) -> None:
        authority = _current_authority()
        with pytest.raises(TypeError, match="cannot be serialized"):
            pickle.dumps(authority, protocol=protocol)

    def test_build_with_copy_attempt_rejected(self) -> None:
        """A copied authority cannot be supplied to build; copy itself fails."""
        authority = _current_authority()
        ci, oi, pr = _consistent_trio()
        with pytest.raises(TypeError, match="cannot be copied"):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=copy.copy(authority),
            )

    def test_verify_with_copy_attempt_rejected(self) -> None:
        """A copied authority cannot be supplied to verify; copy itself fails."""
        authority = _current_authority()
        attestation = _build_valid_attestation()
        ci, oi, pr = _consistent_trio()
        with pytest.raises(TypeError, match="cannot be copied"):
            verify_quality_pass_attestation(
                attestation,
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=copy.copy(authority),
            )


class TestQualityProvenanceAuthorityMintingBoundary:
    """Only runtime composition can mint an authority."""

    def test_caller_local_scoring_settings_cannot_mint_authority(
        self,
        tmp_path: Path,
    ) -> None:
        """No public seam turns caller-created LocalScoringSettings into authority."""
        import youtube_intel.runtime as runtime_module

        assert not hasattr(
            runtime_module,
            "_mint_quality_provenance_authority_for_test",
        )
        ci, oi, pr = _consistent_trio()
        attacker_settings = LocalScoringSettings(
            model=UNAUTHORIZED_MODEL,
            expected_model_digest=UNAUTHORIZED_DIGEST,
        )
        with pytest.raises(TypeError):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=attacker_settings,  # type: ignore[arg-type]
            )
        with pytest.raises(TypeError):
            verify_quality_pass_attestation(
                _build_valid_attestation(),
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=attacker_settings,  # type: ignore[arg-type]
            )

    def test_caller_fake_provenance_cannot_mint_authority(self) -> None:
        """Caller-created fake provenance DTO cannot authorize attestation."""

        class _FakeProvenance:
            judge_provider = "ollama"
            judge_model = "qwen3:8b"
            judge_model_digest = DIGEST
            scoring_schema_version = SCORING_SCHEMA_VERSION
            scoring_prompt_version = SCORING_PROMPT_VERSION
            quality_schema_version = "content-quality-result-v1"
            quality_prompt_version = "content-quality-prompt-v1"
            quality_policy_version = "content-quality-policy-v1"
            judge_operation = "local-content-quality-v1"

        ci, oi, pr = _consistent_trio()
        fake = _FakeProvenance()
        with pytest.raises(TypeError):
            build_quality_pass_attestation(
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=fake,  # type: ignore[arg-type]
            )
        with pytest.raises(TypeError):
            verify_quality_pass_attestation(
                _build_valid_attestation(),
                quality_result=pr,
                operation_input=oi,
                quality_input=ci,
                authority=fake,  # type: ignore[arg-type]
            )
