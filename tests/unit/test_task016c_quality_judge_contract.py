"""TASK-016C Phase C local Judge contract and H1/H2 identity tests."""

from __future__ import annotations

import hashlib
import json
from http.client import IncompleteRead

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    ContentQualityConfidence,
    ContentQualityDecisionSource,
    ContentQualityInput,
    ContentQualityReason,
    ContentQualityResult,
    ContentQualitySignal,
    ContentQualityStatus,
    QualityJudgeAttemptRole,
    QualityJudgeOperationInput,
    ScoringEvidence,
    ScoringEvidenceSource,
)
from youtube_intel.providers.ollama import (
    OllamaQualityJudgeProvider,
)
from youtube_intel.quality import (
    build_content_quality_input_hash,
    build_judge_h1_h2,
)
from youtube_intel.state import build_provider_request_hash

VALID_HASH = "a" * 64
OTHER_HASH = "0" * 64
DIGEST = "sha256:" + "b" * 64
OTHER_DIGEST = "sha256:" + "c" * 64


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if isinstance(self._payload, bytes):
            return self._payload
        return json.dumps(self._payload).encode("utf-8")

    def close(self) -> None:
        self.closed = True


class _IncompleteResponse(_Response):
    def __init__(self, partial: bytes) -> None:
        super().__init__(partial)

    def read(self, size: int = -1) -> bytes:
        raise IncompleteRead(self._payload, len(self._payload) + 1)


class _FakeTransport:
    def __init__(self, responses: list[object]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str, bytes | None]] = []

    def __call__(self, request: object, timeout: float) -> _Response:
        method = getattr(request, "method")
        url = getattr(request, "full_url")
        data = getattr(request, "data")
        self.requests.append((method, url, data))
        response = self._responses.pop(0)
        if isinstance(response, _Response):
            return response
        return _Response(response)


def _settings(
    *,
    model: str = "qwen3:8b",
    digest: str = DIGEST,
    base_url: str = "http://127.0.0.1:11434",
) -> LocalScoringSettings:
    return LocalScoringSettings(
        model=model,
        expected_model_digest=digest,
        base_url=base_url,
    )


def _operation_input(
    *,
    scoring_request_hash: str = VALID_HASH,
    attempt_role: QualityJudgeAttemptRole = QualityJudgeAttemptRole.PRIMARY,
    candidate_hash: str = VALID_HASH,
    quality_input_hash: str = VALID_HASH,
    policy_version: str = "content-quality-policy-v1",
    prompt_version: str = "content-quality-prompt-v3",
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


def _judge_response(
    *,
    status: str = "PASS",
    decision_confidence: str = "HIGH",
    grounding_confidence: str = "MEDIUM",
    usefulness_confidence: str = "MEDIUM",
    signals: list[str] | None = None,
    reason: str | None = None,
    evidence_ids: list[str] | None = None,
) -> dict[str, object]:
    return {
        "response": json.dumps(
            {
                "status": status,
                "decision_confidence": decision_confidence,
                "grounding_confidence": grounding_confidence,
                "usefulness_confidence": usefulness_confidence,
                "signals": signals if signals is not None else [],
                "reason": reason,
                "evidence_ids": evidence_ids if evidence_ids is not None else [],
            }
        ),
    }


def _tags(*, digest: str | None = None) -> dict[str, object]:
    return {
        "models": [
            {
                "name": "qwen3:8b",
                "digest": digest or DIGEST.removeprefix("sha256:"),
            }
        ]
    }


class TestJudgeIdentity:
    def test_h1_is_sha256_of_canonical_json(self) -> None:
        operation_input = _operation_input()
        h1, _ = build_judge_h1_h2(operation_input)
        canonical = json.dumps(
            operation_input.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert h1 == expected

    def test_h1_is_stable_for_identical_validated_input(self) -> None:
        operation_input = _operation_input()
        h1_a, _ = build_judge_h1_h2(operation_input)
        h1_b, _ = build_judge_h1_h2(_operation_input())
        assert h1_a == h1_b

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("scoring_request_hash", OTHER_HASH),
            ("attempt_role", QualityJudgeAttemptRole.REPAIR),
            ("candidate_hash", OTHER_HASH),
            ("quality_input_hash", OTHER_HASH),
            ("policy_version", "content-quality-policy-v2"),
            ("prompt_version", "content-quality-prompt-v1"),
            ("schema_version", "content-quality-result-v2"),
            ("judge_provider", "other-provider"),
            ("judge_model", "other-model"),
            ("judge_model_digest", OTHER_DIGEST),
        ],
    )
    def test_h1_changes_when_any_input_field_changes(
        self,
        field_name: str,
        value: object,
    ) -> None:
        base = _operation_input()
        h1_base, _ = build_judge_h1_h2(base)
        changed = base.model_dump(mode="python")
        changed[field_name] = value
        h1_changed, _ = build_judge_h1_h2(
            QualityJudgeOperationInput.model_validate(changed)
        )
        assert h1_base != h1_changed

    def test_primary_and_repair_roles_produce_different_h1_h2(self) -> None:
        primary = _operation_input(attempt_role=QualityJudgeAttemptRole.PRIMARY)
        repair = _operation_input(attempt_role=QualityJudgeAttemptRole.REPAIR)
        h1_primary, h2_primary = build_judge_h1_h2(primary)
        h1_repair, h2_repair = build_judge_h1_h2(repair)
        assert h1_primary != h1_repair
        assert h2_primary != h2_repair

    def test_h2_equals_existing_builder_output(self) -> None:
        operation_input = _operation_input()
        h1, h2 = build_judge_h1_h2(operation_input)
        expected_h2 = build_provider_request_hash(
            operation="local-content-quality-v1",
            normalized_input_hash=h1,
            provider=operation_input.judge_provider,
            model=operation_input.judge_model,
            prompt_version=operation_input.prompt_version,
            schema_version=operation_input.schema_version,
        )
        assert h2 == expected_h2

    def test_h1_and_h2_differ(self) -> None:
        operation_input = _operation_input()
        h1, h2 = build_judge_h1_h2(operation_input)
        assert h1 != h2
        assert len(h1) == 64
        assert len(h2) == 64

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("operation", "other-operation"),
            ("provider", "other-provider"),
            ("model", "other-model"),
            ("prompt_version", "other-prompt"),
            ("schema_version", "other-schema"),
        ],
    )
    def test_h2_changes_when_builder_dimension_changes(
        self,
        field_name: str,
        value: str,
    ) -> None:
        operation_input = _operation_input()
        _, h2_base = build_judge_h1_h2(operation_input)
        kwargs = {
            "operation": "local-content-quality-v1",
            "normalized_input_hash": build_judge_h1_h2(operation_input)[0],
            "provider": operation_input.judge_provider,
            "model": operation_input.judge_model,
            "prompt_version": operation_input.prompt_version,
            "schema_version": operation_input.schema_version,
        }
        kwargs[field_name] = value
        h2_changed = build_provider_request_hash(**kwargs)
        assert h2_base != h2_changed

    def test_unchecked_model_copy_update_cannot_produce_trusted_h1(self) -> None:
        operation_input = _operation_input()
        with pytest.raises(ValueError, match="model_copy"):
            operation_input.model_copy(update={"judge_model": "tampered"})

    def test_deprecated_copy_update_cannot_produce_trusted_h1(self) -> None:
        operation_input = _operation_input()
        with pytest.raises(ValueError, match="copy"):
            operation_input.copy(update={"judge_model": "tampered"})

    def test_unchecked_model_construct_cannot_produce_trusted_h1(self) -> None:
        with pytest.raises(ValueError):
            QualityJudgeOperationInput.model_construct(
                scoring_request_hash=VALID_HASH,
                attempt_role=QualityJudgeAttemptRole.PRIMARY,
                candidate_hash=VALID_HASH,
                quality_input_hash=VALID_HASH,
                policy_version="content-quality-policy-v1",
                prompt_version="content-quality-prompt-v1",
                schema_version="content-quality-result-v1",
                judge_provider="ollama",
                judge_model="qwen3:8b",
                judge_model_digest=DIGEST,
            )

    def test_model_construct_and_private_marker_injection_fails(
        self,
    ) -> None:
        """Private marker injection cannot promote trust: construction itself is disabled."""
        with pytest.raises(ValueError):
            constructed = QualityJudgeOperationInput.model_construct(
                scoring_request_hash=VALID_HASH,
                attempt_role=QualityJudgeAttemptRole.PRIMARY,
                candidate_hash=VALID_HASH,
                quality_input_hash=VALID_HASH,
                policy_version="content-quality-policy-v1",
                prompt_version="content-quality-prompt-v1",
                schema_version="content-quality-result-v1",
                judge_provider="ollama",
                judge_model="qwen3:8b",
                judge_model_digest=DIGEST,
            )
            object.__setattr__(constructed, "_validated", True)
            build_judge_h1_h2(constructed)

    def test_unchecked_mapping_cannot_produce_trusted_h1(self) -> None:
        raw = {
            "scoring_request_hash": VALID_HASH,
            "attempt_role": "PRIMARY",
            "candidate_hash": VALID_HASH,
            "quality_input_hash": VALID_HASH,
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v1",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": "qwen3:8b",
            "judge_model_digest": "not-a-valid-digest",
        }
        with pytest.raises(ValueError):
            QualityJudgeOperationInput.model_validate(raw)

    def test_unchecked_json_cannot_produce_trusted_h1(self) -> None:
        raw = {
            "scoring_request_hash": VALID_HASH,
            "attempt_role": "PRIMARY",
            "candidate_hash": VALID_HASH,
            "quality_input_hash": VALID_HASH,
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v1",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": "qwen3:8b",
            "judge_model_digest": DIGEST,
        }
        payload = json.dumps(raw).replace("PRIMARY", "INVALID_ROLE")
        with pytest.raises(ValueError):
            QualityJudgeOperationInput.model_validate_json(payload)

    def test_subclass_property_override_rejected_for_h1_h2(self) -> None:
        class _TamperedInput(QualityJudgeOperationInput):
            @property
            def judge_provider(self) -> str:
                return "tampered-provider"

        base = _operation_input()
        tampered = _TamperedInput.model_validate(base.model_dump(mode="python"))
        with pytest.raises(ValueError):
            build_judge_h1_h2(tampered)

    def test_model_dump_override_rejected_for_h1_h2(self) -> None:
        class _MismatchInput(QualityJudgeOperationInput):
            def model_dump(self, **kwargs: object) -> dict[str, object]:
                data = super().model_dump(**kwargs)
                data["judge_model"] = "tampered-model"
                return data

        base = _operation_input()
        mismatch = _MismatchInput.model_validate(base.model_dump(mode="python"))
        with pytest.raises(ValueError):
            build_judge_h1_h2(mismatch)


class TestJudgeConfigBinding:
    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("judge_model", "mismatched-model"),
            ("judge_model_digest", OTHER_DIGEST),
            ("judge_provider", "openai"),
            ("policy_version", "content-quality-policy-v2"),
            ("prompt_version", "content-quality-prompt-v1"),
            ("schema_version", "content-quality-result-v2"),
        ],
    )
    def test_config_mismatch_fails_closed_without_transport(
        self,
        field_name: str,
        value: object,
    ) -> None:
        transport = _FakeTransport([])
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
            **{field_name: value},
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []


class TestJudgeReconstructionAtEntry:
    def test_subclass_getattribute_spoof_emits_zero_transport(self) -> None:
        """Spoofed __getattribute__ on a subclass must not reach GET /api/tags."""

        _trusted = {
            "judge_provider": "ollama",
            "judge_model": "qwen3:8b",
            "judge_model_digest": DIGEST,
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v1",
            "schema_version": "content-quality-result-v1",
        }

        class _TamperedInput(QualityJudgeOperationInput):
            def __getattribute__(self, name: str) -> object:
                if name in _trusted:
                    return _trusted[name]
                return object.__getattribute__(self, name)

        transport = _FakeTransport([])
        content_input = _content_input()
        base = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        malicious_dump = base.model_dump(mode="python")
        malicious_dump["judge_model"] = "other-model"
        malicious_dump["judge_provider"] = "openai"
        tampered = _TamperedInput.model_validate(malicious_dump)
        assert tampered.judge_model == "qwen3:8b"
        assert tampered.judge_provider == "ollama"
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            tampered,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []

    def test_subclass_model_dump_spoof_emits_zero_transport(self) -> None:
        class _MismatchInput(QualityJudgeOperationInput):
            def model_dump(self, **kwargs: object) -> dict[str, object]:
                data = super().model_dump(**kwargs)
                data["judge_model"] = "qwen3:8b"
                return data

        transport = _FakeTransport([])
        content_input = _content_input()
        base = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        malicious_dump = base.model_dump(mode="python")
        malicious_dump["judge_model"] = "other-model"
        mismatch = _MismatchInput.model_validate(malicious_dump)
        assert mismatch.model_dump()["judge_model"] == "qwen3:8b"
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            mismatch,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []

    def test_model_construct_operation_input_emits_zero_transport(self) -> None:
        transport = _FakeTransport([])
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )
        content_input = _content_input()

        with pytest.raises(ValueError):
            constructed = QualityJudgeOperationInput.model_construct(
                scoring_request_hash=VALID_HASH,
                attempt_role=QualityJudgeAttemptRole.PRIMARY,
                candidate_hash=VALID_HASH,
                quality_input_hash=VALID_HASH,
                policy_version="content-quality-policy-v1",
                prompt_version="content-quality-prompt-v1",
                schema_version="content-quality-result-v1",
                judge_provider="ollama",
                judge_model="qwen3:8b",
                judge_model_digest=DIGEST,
            )
            provider.judge(constructed, content_input=content_input)

        assert transport.requests == []

    def test_truly_malformed_content_input_fails_closed_without_validation_error(
        self,
    ) -> None:
        transport = _FakeTransport([])
        operation_input = _operation_input()
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )
        malformed = ContentQualityInput.model_construct(
            scoring_request_hash="not-a-valid-hash",
            candidate_hash=VALID_HASH,
            output_language="en",
            reason="reason",
            topics=("topic",),
            evidence_registry=(),
            policy_version="content-quality-policy-v1",
        )

        result = provider.judge(
            operation_input,
            content_input=malformed,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []

    def test_zero_transport_on_content_input_hash_mismatch(self) -> None:
        transport = _FakeTransport([])
        content_input = _content_input()
        operation_input = _operation_input(quality_input_hash=OTHER_HASH)
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("candidate_hash", OTHER_HASH),
            ("scoring_request_hash", OTHER_HASH),
        ],
    )
    def test_content_input_hash_mismatch_fails_closed_before_transport(
        self,
        field_name: str,
        value: str,
    ) -> None:
        content_input = _content_input()
        altered = content_input.model_dump(mode="python")
        altered[field_name] = value
        altered_content_input = ContentQualityInput.model_validate(altered)
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(altered_content_input),
        )
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="PASS",
                    signals=[
                        "MINIMAL_CLAIM_PRESENT",
                        "GROUNDING_PRESENT",
                    ],
                    evidence_ids=["title-1"],
                ),
            ]
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=altered_content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("judge_provider", ""),
            ("judge_model", ""),
            ("judge_model_digest", "not-a-valid-digest"),
            ("scoring_request_hash", "not-a-hash"),
            ("candidate_hash", "not-a-hash"),
            ("quality_input_hash", "not-a-hash"),
        ],
    )
    def test_malformed_exact_base_operation_input_fails_closed(
        self,
        field_name: str,
        value: object,
    ) -> None:
        transport = _FakeTransport([])
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        object.__setattr__(operation_input, field_name, value)
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(operation_input, content_input=content_input)

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []

    def test_malformed_exact_base_operation_input_returns_no_validation_error(
        self,
    ) -> None:
        transport = _FakeTransport([])
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        object.__setattr__(operation_input, "candidate_hash", "not-a-hash")
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(operation_input, content_input=content_input)

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []


class TestJudgeLoopback:
    @pytest.mark.parametrize(
        "base_url",
        [
            "https://example.com",
            "http://example.com:11434",
            "http://user@127.0.0.1:11434",
            "http://127.0.0.1:11434?query=1",
            "http://127.0.0.1:11434#fragment",
        ],
    )
    def test_non_loopback_base_url_fails_closed_before_transport(
        self,
        base_url: str,
    ) -> None:
        transport = _FakeTransport([])
        settings = LocalScoringSettings.model_construct(
            model="qwen3:8b",
            expected_model_digest=DIGEST,
            base_url=base_url,
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=settings,
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []


class TestJudgePayload:
    def test_missing_payload_is_rejected(self) -> None:
        transport = _FakeTransport([])
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=None,  # type: ignore[arg-type]
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []

    def test_noncanonical_payload_type_is_rejected(self) -> None:
        transport = _FakeTransport([])
        operation_input = _operation_input()
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input={"not": "a validated payload"},  # type: ignore[arg-type]
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []

    def test_quality_input_hash_mismatch_is_rejected(self) -> None:
        transport = _FakeTransport([])
        content_input = _content_input()
        operation_input = _operation_input(quality_input_hash=OTHER_HASH)
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE
        assert transport.requests == []

    def test_empty_reason_rejected(self) -> None:
        with pytest.raises(ValueError):
            ContentQualityInput.model_validate(
                {
                    "scoring_request_hash": VALID_HASH,
                    "candidate_hash": VALID_HASH,
                    "output_language": "en",
                    "reason": "",
                    "topics": ("topic-a",),
                    "evidence_registry": (),
                    "policy_version": "content-quality-policy-v1",
                }
            )

    def test_empty_topics_rejected(self) -> None:
        with pytest.raises(ValueError):
            ContentQualityInput.model_validate(
                {
                    "scoring_request_hash": VALID_HASH,
                    "candidate_hash": VALID_HASH,
                    "output_language": "en",
                    "reason": "A reason",
                    "topics": (),
                    "evidence_registry": (),
                    "policy_version": "content-quality-policy-v1",
                }
            )

    def test_empty_evidence_registry_is_valid(self) -> None:
        content_input = ContentQualityInput.model_validate(
            {
                "scoring_request_hash": VALID_HASH,
                "candidate_hash": VALID_HASH,
                "output_language": "en",
                "reason": "A concise candidate reason",
                "topics": ("topic-a",),
                "evidence_registry": (),
                "policy_version": "content-quality-policy-v1",
            }
        )
        assert content_input.evidence_registry == ()

    def test_empty_evidence_registry_hash_is_deterministic(self) -> None:
        content_input_a = ContentQualityInput.model_validate(
            {
                "scoring_request_hash": VALID_HASH,
                "candidate_hash": VALID_HASH,
                "output_language": "en",
                "reason": "A concise candidate reason",
                "topics": ("topic-a",),
                "evidence_registry": (),
                "policy_version": "content-quality-policy-v1",
            }
        )
        content_input_b = ContentQualityInput.model_validate(
            {
                "scoring_request_hash": VALID_HASH,
                "candidate_hash": VALID_HASH,
                "output_language": "en",
                "reason": "A concise candidate reason",
                "topics": ("topic-a",),
                "evidence_registry": (),
                "policy_version": "content-quality-policy-v1",
            }
        )
        assert build_content_quality_input_hash(content_input_a) == build_content_quality_input_hash(content_input_b)

    def test_judge_empty_registry_pass_with_empty_evidence_fails_closed(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="PASS",
                    signals=[
                        "MINIMAL_CLAIM_PRESENT",
                        "GROUNDING_PRESENT",
                    ],
                    evidence_ids=[],
                ),
            ]
        )
        content_input = ContentQualityInput.model_validate(
            {
                "scoring_request_hash": VALID_HASH,
                "candidate_hash": VALID_HASH,
                "output_language": "en",
                "reason": "A concise candidate reason",
                "topics": ("topic-a",),
                "evidence_registry": (),
                "policy_version": "content-quality-policy-v1",
            }
        )
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE


class TestJudgeRequest:
    def test_judge_request_uses_trusted_config_and_fixed_parameters(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="PASS",
                    signals=[
                        "MINIMAL_CLAIM_PRESENT",
                        "GROUNDING_PRESENT",
                    ],
                    evidence_ids=["title-1"],
                ),
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert [method for method, _, _ in transport.requests] == ["GET", "POST"]
        assert [url for _, url, _ in transport.requests] == [
            "http://127.0.0.1:11434/api/tags",
            "http://127.0.0.1:11434/api/generate",
        ]
        generate_payload = json.loads(transport.requests[1][2] or b"{}")
        assert generate_payload["model"] == "qwen3:8b"
        assert generate_payload["stream"] is False
        assert generate_payload["think"] is False
        assert generate_payload["options"]["temperature"] == 0.0
        assert "tools" not in generate_payload
        assert generate_payload["format"]["type"] == "object"

    def test_judge_request_body_contains_h1_identity(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="PASS",
                    signals=[
                        "MINIMAL_CLAIM_PRESENT",
                        "GROUNDING_PRESENT",
                    ],
                    evidence_ids=["title-1"],
                ),
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        provider.judge(
            operation_input,
            content_input=content_input,
        )

        generate_payload = json.loads(transport.requests[1][2] or b"{}")
        h1, _ = build_judge_h1_h2(operation_input)
        assert h1 in generate_payload["prompt"]
        prompt = generate_payload["prompt"]
        assert "content-quality-prompt-v3" in prompt
        assert (
            "IDENTIFIER_ONLY, ENTITY_ONLY, LOW_INFORMATION, MINIMAL_CLAIM_MISSING"
            in prompt
        )
        assert (
            "GROUNDING_INSUFFICIENT, JUDGE_UNAVAILABLE, or JUDGE_INVALID_RESPONSE"
            in prompt
        )

    def test_judge_request_payload_contains_bounded_evaluation_content(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="PASS",
                    signals=[
                        "MINIMAL_CLAIM_PRESENT",
                        "GROUNDING_PRESENT",
                    ],
                    evidence_ids=["title-1"],
                ),
            ]
        )
        content_input = _content_input(
            output_language="zh-CN",
            reason="A concise reason",
            topics=("topic-a", "topic-b"),
        )
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        provider.judge(
            operation_input,
            content_input=content_input,
        )

        generate_payload = json.loads(transport.requests[1][2] or b"{}")
        prompt = generate_payload["prompt"]
        h1, _ = build_judge_h1_h2(operation_input)
        assert h1 in prompt
        # Prompt is a fixed prefix followed by one canonical JSON object.
        json_start = prompt.index("{")
        embedded = json.loads(prompt[json_start:])
        assert embedded["judge_identity"] == h1
        assert embedded["quality_input_hash"] == operation_input.quality_input_hash
        assert embedded["language"] == "zh-CN"
        assert embedded["candidate_reason"] == "A concise reason"
        assert embedded["candidate_topics"] == ["topic-a", "topic-b"]
        registry = embedded["evidence_registry"]
        assert any(item["id"] == "title-1" for item in registry)
        assert any("excerpt for title-1" in item["excerpt"] for item in registry)


class TestJudgeResponse:
    def test_valid_pass_response_returns_trusted_result(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="PASS",
                    signals=[
                        "MINIMAL_CLAIM_PRESENT",
                        "GROUNDING_PRESENT",
                    ],
                    evidence_ids=["title-1"],
                ),
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert isinstance(result, ContentQualityResult)
        assert result.status is ContentQualityStatus.PASS
        assert result.decision_source is ContentQualityDecisionSource.LOCAL_JUDGE
        assert result.decision_confidence is ContentQualityConfidence.HIGH
        assert result.grounding_confidence is ContentQualityConfidence.MEDIUM
        assert result.usefulness_confidence is ContentQualityConfidence.MEDIUM
        assert ContentQualitySignal.MINIMAL_CLAIM_PRESENT in result.signals
        assert ContentQualitySignal.GROUNDING_PRESENT in result.signals
        assert result.reason is None
        assert result.evidence_ids == ("title-1",)
        assert result.judge_provider == "ollama"
        assert result.judge_model == "qwen3:8b"
        assert result.judge_model_digest == DIGEST

    def test_valid_reject_response_returns_trusted_result(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="REJECT",
                    decision_confidence="HIGH",
                    grounding_confidence="LOW",
                    usefulness_confidence="LOW",
                    signals=["IDENTIFIER_ONLY"],
                    reason="IDENTIFIER_ONLY",
                ),
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.REJECT
        assert result.reason is ContentQualityReason.IDENTIFIER_ONLY
        assert ContentQualitySignal.IDENTIFIER_ONLY in result.signals

    def test_duplicate_signal_fails_closed_as_uncertain(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="PASS",
                    signals=[
                        "MINIMAL_CLAIM_PRESENT",
                        "MINIMAL_CLAIM_PRESENT",
                        "GROUNDING_PRESENT",
                    ],
                    evidence_ids=["title-1"],
                ),
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE

    def test_unknown_status_fails_closed_as_uncertain(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="MAYBE",
                    signals=["JUDGE_INVALID_RESPONSE"],
                    reason="JUDGE_INVALID_RESPONSE",
                ),
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE

    def test_invalid_json_response_fails_closed_as_uncertain(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                {"response": "not valid json"},
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE

    def test_invalid_utf8_response_fails_closed_as_uncertain(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _Response(b"\xff\xfe not utf-8"),
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE

    def test_timeout_fails_closed_as_uncertain(self) -> None:
        def _timeout_transport(request: object, timeout: float) -> _Response:
            raise TimeoutError

        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=_timeout_transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE

    def test_oversized_response_fails_closed_as_uncertain(self) -> None:
        huge_response = "x" * 100_001
        transport = _FakeTransport(
            [
                _tags(),
                {"response": huge_response},
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE

    def test_model_digest_mismatch_fails_closed_as_uncertain(self) -> None:
        transport = _FakeTransport([_tags(digest="c" * 64)])
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_UNAVAILABLE

    def test_evidence_id_outside_registry_fails_closed_as_uncertain(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                _judge_response(
                    status="PASS",
                    signals=[
                        "MINIMAL_CLAIM_PRESENT",
                        "GROUNDING_PRESENT",
                    ],
                    evidence_ids=["unknown-id"],
                ),
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE

    def test_free_text_diagnostic_field_fails_closed_as_uncertain(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                {
                    "response": json.dumps(
                        {
                            "status": "PASS",
                            "decision_confidence": "HIGH",
                            "grounding_confidence": "MEDIUM",
                            "usefulness_confidence": "MEDIUM",
                            "signals": [
                                "MINIMAL_CLAIM_PRESENT",
                                "GROUNDING_PRESENT",
                            ],
                            "reason": None,
                            "evidence_ids": ["title-1"],
                            "diagnostic": "this should not be allowed",
                        }
                    ),
                },
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result.status is ContentQualityStatus.UNCERTAIN
        assert result.reason is ContentQualityReason.JUDGE_INVALID_RESPONSE


class TestJudgeNoSideEffects:
    def test_judge_does_not_raise_provider_error_for_uncertain(self) -> None:
        transport = _FakeTransport(
            [
                _tags(),
                {"response": "not valid json"},
            ]
        )
        content_input = _content_input()
        operation_input = _operation_input(
            quality_input_hash=build_content_quality_input_hash(content_input),
        )
        provider = OllamaQualityJudgeProvider(
            settings=_settings(),
            transport=transport,
        )

        result = provider.judge(
            operation_input,
            content_input=content_input,
        )

        assert result is not None
        assert result.status is ContentQualityStatus.UNCERTAIN


class TestContentQualityResultPassMatrix:
    def test_pass_with_empty_evidence_ids_rejected(self) -> None:
        with pytest.raises(ValueError, match="PASS requires at least one evidence_id"):
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
                    "signals": [
                        "MINIMAL_CLAIM_PRESENT",
                        "GROUNDING_PRESENT",
                    ],
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

    def test_pass_with_one_valid_evidence_id_accepted(self) -> None:
        result = ContentQualityResult.model_validate(
            {
                "schema_version": "content-quality-result-v1",
                "policy_version": "content-quality-policy-v1",
                "prompt_version": "content-quality-prompt-v1",
                "status": "PASS",
                "decision_source": "LOCAL_JUDGE",
                "decision_confidence": "HIGH",
                "grounding_confidence": "MEDIUM",
                "usefulness_confidence": "MEDIUM",
                "signals": [
                    "MINIMAL_CLAIM_PRESENT",
                    "GROUNDING_PRESENT",
                ],
                "reason": None,
                "evidence_ids": ["title-1"],
                "candidate_hash": VALID_HASH,
                "quality_input_hash": VALID_HASH,
                "scoring_request_hash": VALID_HASH,
                "judge_provider": "ollama",
                "judge_model": "qwen3:8b",
                "judge_model_digest": DIGEST,
            }
        )
        assert result.status is ContentQualityStatus.PASS
        assert result.evidence_ids == ("title-1",)
