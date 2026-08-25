"""TASK-016C Phase H2-B — RED tests for the frozen runtime REPAIR seams.

Covers the narrow provider/admission/evidence seams authorized by
``docs/TASK-016C-PHASE-H2B-AUTHORIZATION.md``:

- the frozen ``TASK016C_REPAIR_PROMPT_V2`` template and the exact outbound
  Ollama REPAIR payload contract;
- the exact-payload REPAIR dispatch seam (payload hash/length equality,
  ``/api/tags`` before ``/api/generate``, exact raw return);
- the PRIMARY parse-failure raw capture seam;
- the strict REPAIR Judge seam (UNKNOWN vs semantic UNCERTAIN split);
- the private atomic role-consumption-and-dispatch admission composition;
- the REPAIR Judge trusted-context derivation helper.

Runtime end-to-end behavior lives in ``test_task016c_phase_h2b_repair_flow.py``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    Availability,
    ContentQualityInput,
    QualityJudgeOperationInput,
    ScoringCandidate,
    ScoringEvidenceSource,
    VideoMetadata,
)
from youtube_intel.h2_evidence import (
    build_primary_trusted_context,
    derive_primary_judge_trusted_context,
    derive_repair_judge_trusted_context,
)
from youtube_intel.h2_jcs import jcs_serialize
from youtube_intel.providers.ollama import (
    _SCORE_RESULT_FORMAT,
    OllamaProviderError,
    OllamaQualityJudgeProvider,
    OllamaScoringProvider,
    PrimaryRawCapture,
    build_task016c_repair_generate_body,
    render_task016c_repair_prompt_v2,
)
from youtube_intel.quality import build_content_quality_input_hash, build_judge_h1_h2
from youtube_intel.scoring import build_scoring_input
from youtube_intel.scoring_admission import (
    ScoringDispatchAdmission,
    ScoringDispatchDenied,
    ScoringDispatchIdentity,
    ScoringDispatchRole,
)
from youtube_intel.state import JobRecord, JobStatus, JobType, ProcessingStage

_NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + "4" * 64
_PROMPT = "prompt_version: scoring-prompt-v2\nYou are a strict scorer."
_EN_REASON = "This repaired response explains a concrete product strategy clearly."


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if not isinstance(self._payload, bytes):
            return json.dumps(self._payload).encode("utf-8")
        return self._payload

    def close(self) -> None:
        self.closed = True


class _Timeout(Exception):
    pass


class _FakeTransport:
    """Scripted transport that records every outbound request."""

    def __init__(self, responses: list[object]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str, bytes | None]] = []

    def __call__(self, request: object, timeout: float) -> _Response:
        method = getattr(request, "method")
        url = getattr(request, "full_url")
        data = getattr(request, "data")
        self.requests.append((method, url, data))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return _Response(response)

    @property
    def tags_calls(self) -> int:
        return sum(1 for _, url, _ in self.requests if url.endswith("/api/tags"))

    @property
    def generate_calls(self) -> int:
        return sum(1 for _, url, _ in self.requests if url.endswith("/api/generate"))


def _tags_payload() -> dict:
    return {"models": [{"name": _MODEL, "digest": "4" * 64}]}


def _settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model=_MODEL,
        expected_model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_transcript_chars=64,
        max_description_chars=32,
    )


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-h2b",
        channel_id="channel-h2b",
        channel_name="H2B Channel",
        title="A useful scoring title",
        description="A deliberately bounded scoring description.",
        source_url="https://example.invalid/watch?v=video-h2b",
        published_at=datetime(2026, 8, 25, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status="none",
        availability=Availability.PUBLIC,
    )


def _scoring_input():
    return build_scoring_input(
        video=_video(),
        transcript_text="This transcript contains enough text for a stable sample.",
        language="en",
        output_language="en",
        settings=_settings(),
    )


def _generate_body(inner: str) -> bytes:
    return json.dumps(
        {"model": _MODEL, "response": inner, "done": True},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _valid_candidate_inner(reason: str = _EN_REASON) -> str:
    return json.dumps(
        {"score": 8, "reason": reason, "topics": ["product"], "should_summarize": True},
        ensure_ascii=False,
        separators=(",", ":"),
    )


# ---------------------------------------------------------------------------
# Frozen REPAIR prompt template
# ---------------------------------------------------------------------------


def test_repair_prompt_v2_is_assembled_with_exact_blocks_and_order() -> None:
    scoring_input = _scoring_input()
    rni_text = '{"role":"REPAIR"}'
    pfe_text = '{"failure_class":"SCHEMA_OR_PARSE_INVALID"}'
    si_text = '{"video_id":"video-h2b"}'
    raw_text = '{"response":"{not-json"}'
    candidate_text = '{"kind":"CANDIDATE"}'
    extracted = "{not-json"
    schema_text = jcs_serialize(_SCORE_RESULT_FORMAT).decode("utf-8")

    prompt = render_task016c_repair_prompt_v2(
        output_language=scoring_input.output_language,
        repair_request_hash="a" * 64,
        rni_jcs_utf8=rni_text,
        pfe_jcs_utf8=pfe_text,
        scoring_input_jcs_utf8=si_text,
        primary_raw_utf8=raw_text,
        candidate_evidence_jcs_utf8=candidate_text,
        extracted_model_content=extracted,
    )

    assert prompt == "\n".join(
        [
            "prompt_version: scoring-prompt-v2",
            "You are repairing one invalid local-scoring result.",
            "Return exactly one JSON object and no commentary.",
            "The object MUST satisfy the supplied score-result-v2 JSON schema.",
            "The reason field MUST use output language: en.",
            "REPAIR request hash: " + "a" * 64,
            "REPAIR normalized input: " + rni_text,
            "PRIMARY failure evidence: " + pfe_text,
            "ORIGINAL scoring input: " + si_text,
            "PRIMARY raw body: " + raw_text,
            "PRIMARY candidate evidence: " + candidate_text,
            "Invalid PRIMARY model content follows:",
            extracted,
            "Required JSON schema follows:",
            schema_text,
        ]
    )


def test_repair_prompt_v2_null_blocks_use_literal_null() -> None:
    prompt = render_task016c_repair_prompt_v2(
        output_language="zh-CN",
        repair_request_hash="b" * 64,
        rni_jcs_utf8="{}",
        pfe_jcs_utf8="{}",
        scoring_input_jcs_utf8="{}",
        primary_raw_utf8="{}",
        candidate_evidence_jcs_utf8=None,
        extracted_model_content=None,
    )
    assert "PRIMARY candidate evidence: null" in prompt.splitlines()
    assert "Invalid PRIMARY model content follows:" in prompt.splitlines()
    assert prompt.splitlines()[12] == "null"
    assert "The reason field MUST use output language: zh-CN." in prompt.splitlines()


# ---------------------------------------------------------------------------
# Frozen Ollama REPAIR payload
# ---------------------------------------------------------------------------


def test_repair_generate_body_uses_exactly_the_frozen_fields() -> None:
    body = build_task016c_repair_generate_body(
        model=_MODEL,
        prompt="prompt_version: scoring-prompt-v2\nP",
        temperature=0.0,
        max_output_tokens=1200,
    )
    payload = json.loads(body.decode("utf-8"))
    assert set(payload) == {"model", "prompt", "stream", "format", "think", "options"}
    assert payload["model"] == _MODEL
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["format"] == _SCORE_RESULT_FORMAT
    assert payload["options"] == {"temperature": 0.0, "num_predict": 1200}
    # Exact compact serialization with ensure_ascii=False.
    assert body == json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def test_repair_generate_body_preserves_non_ascii_prompt_bytes() -> None:
    body = build_task016c_repair_generate_body(
        model=_MODEL,
        prompt="prompt_version: scoring-prompt-v2\n中文修复内容",
        temperature=0.5,
        max_output_tokens=99,
    )
    assert "中文修复内容".encode("utf-8") in body


# ---------------------------------------------------------------------------
# Exact-payload REPAIR dispatch seam
# ---------------------------------------------------------------------------


def _scoring_provider(transport: _FakeTransport) -> OllamaScoringProvider:
    return OllamaScoringProvider(
        settings=_settings(), prompt=_PROMPT, transport=transport
    )


def test_repair_dispatch_rejects_payload_hash_mismatch_before_any_transport() -> None:
    transport = _FakeTransport([_tags_payload(), {"response": "{}"}])
    provider = _scoring_provider(transport)
    body = b'{"prompt":"x"}'

    with pytest.raises(ScoringDispatchDenied, match="payload"):
        provider.dispatch_exact_repair_generate(
            body=body,
            body_sha256="f" * 64,
            body_length=len(body),
        )

    assert transport.requests == []


def test_repair_dispatch_rejects_payload_length_mismatch_before_any_transport() -> None:
    transport = _FakeTransport([_tags_payload()])
    provider = _scoring_provider(transport)
    body = b'{"prompt":"x"}'

    with pytest.raises(ScoringDispatchDenied, match="payload"):
        provider.dispatch_exact_repair_generate(
            body=body,
            body_sha256=hashlib.sha256(body).hexdigest(),
            body_length=len(body) + 1,
        )

    assert transport.requests == []


def test_repair_dispatch_sends_exact_body_after_tags_preflight() -> None:
    repair_raw = _generate_body(_valid_candidate_inner())
    transport = _FakeTransport([_tags_payload(), repair_raw])
    provider = _scoring_provider(transport)
    body = build_task016c_repair_generate_body(
        model=_MODEL,
        prompt="prompt_version: scoring-prompt-v2\nrepair",
        temperature=0.0,
        max_output_tokens=1200,
    )

    returned = provider.dispatch_exact_repair_generate(
        body=body,
        body_sha256=hashlib.sha256(body).hexdigest(),
        body_length=len(body),
    )

    assert returned == repair_raw
    assert [method for method, _, _ in transport.requests] == ["GET", "POST"]
    assert transport.requests[0][1].endswith("/api/tags")
    assert transport.requests[1][1].endswith("/api/generate")
    assert transport.requests[1][2] == body


def test_repair_dispatch_tags_timeout_propagates_for_unknown_mapping() -> None:
    transport = _FakeTransport([TimeoutError("tags timeout")])
    provider = _scoring_provider(transport)
    body = b'{"prompt":"x"}'

    with pytest.raises(OllamaProviderError):
        provider.dispatch_exact_repair_generate(
            body=body,
            body_sha256=hashlib.sha256(body).hexdigest(),
            body_length=len(body),
        )

    assert transport.tags_calls == 1
    assert transport.generate_calls == 0


# ---------------------------------------------------------------------------
# PRIMARY parse-failure raw capture seam
# ---------------------------------------------------------------------------


def test_primary_attempt_stashes_sealed_capture_on_inner_parse_failure() -> None:
    invalid_inner = _generate_body("{not-json")
    transport = _FakeTransport([_tags_payload(), invalid_inner])
    provider = _scoring_provider(transport)

    with pytest.raises(ValueError):
        provider.primary_attempt(_scoring_input())

    capture = provider.consume_primary_parse_failure_capture()
    assert type(capture) is PrimaryRawCapture
    assert capture.utf8 == invalid_inner.decode("utf-8")
    assert capture.sha256 == hashlib.sha256(invalid_inner).hexdigest()
    assert capture.byte_length == len(invalid_inner)
    # The capture is consumed exactly once.
    assert provider.consume_primary_parse_failure_capture() is None


def test_primary_attempt_exposes_no_capture_after_successful_parse() -> None:
    transport = _FakeTransport([_tags_payload(), _generate_body(_valid_candidate_inner())])
    provider = _scoring_provider(transport)

    attempt = provider.primary_attempt(_scoring_input())

    assert attempt.attempt_role == "PRIMARY"
    assert provider.consume_primary_parse_failure_capture() is None


def test_primary_attempt_duplicate_outer_response_key_stays_uncapturable() -> None:
    body = (
        b'{"model":"qwen3:8b","response":"{not-json",'
        b'"response":"{not-json","done":true}'
    )
    transport = _FakeTransport([_tags_payload(), body])
    provider = _scoring_provider(transport)

    with pytest.raises(ValueError):
        provider.primary_attempt(_scoring_input())

    # Duplicate outer keys are ambiguous: no eligible capture is promoted.
    assert provider.consume_primary_parse_failure_capture() is None


# ---------------------------------------------------------------------------
# Strict REPAIR Judge seam (UNKNOWN vs semantic UNCERTAIN)
# ---------------------------------------------------------------------------


def _judge_materials() -> tuple[QualityJudgeOperationInput, ContentQualityInput]:
    content = ContentQualityInput.model_validate(
        {
            "scoring_request_hash": "a" * 64,
            "candidate_hash": "b" * 64,
            "output_language": "en",
            "reason": "A concise repaired reason",
            "topics": ("topic-a",),
            "evidence_registry": [
                {
                    "evidence_id": "title-1",
                    "source": ScoringEvidenceSource.TITLE.value,
                    "excerpt": "excerpt for title-1",
                }
            ],
        }
    )
    operation = QualityJudgeOperationInput.model_validate(
        {
            "scoring_request_hash": "a" * 64,
            "attempt_role": "REPAIR",
            "candidate_hash": "b" * 64,
            "quality_input_hash": build_content_quality_input_hash(content),
            "policy_version": "content-quality-policy-v1",
            "prompt_version": "content-quality-prompt-v1",
            "schema_version": "content-quality-result-v1",
            "judge_provider": "ollama",
            "judge_model": _MODEL,
            "judge_model_digest": _DIGEST,
        }
    )
    return operation, content


def _judge_provider(transport: _FakeTransport) -> OllamaQualityJudgeProvider:
    return OllamaQualityJudgeProvider(settings=_settings(), transport=transport)


def test_judge_exact_seam_returns_extracted_model_content_on_success() -> None:
    operation, content = _judge_materials()
    h1, h2 = build_judge_h1_h2(operation)
    identity = ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR_JUDGE,
        operation="local-content-quality-v1",
        normalized_input_hash=h1,
        request_hash=h2,
    )
    judge_raw = json.dumps({"status": "PASS"})
    transport = _FakeTransport(
        [_tags_payload(), _generate_body(judge_raw)]
    )
    provider = _judge_provider(transport)

    extracted = provider.judge_exact_model_content(
        operation, content_input=content, expected_identity=identity
    )

    assert extracted == judge_raw
    assert [method for method, _, _ in transport.requests] == ["GET", "POST"]


def test_judge_exact_seam_transport_timeout_raises_not_uncertain() -> None:
    operation, content = _judge_materials()
    h1, h2 = build_judge_h1_h2(operation)
    identity = ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR_JUDGE,
        operation="local-content-quality-v1",
        normalized_input_hash=h1,
        request_hash=h2,
    )
    transport = _FakeTransport([TimeoutError("judge tags timeout")])
    provider = _judge_provider(transport)

    with pytest.raises(OllamaProviderError):
        provider.judge_exact_model_content(
            operation, content_input=content, expected_identity=identity
        )

    assert transport.tags_calls == 1
    assert transport.generate_calls == 0


def test_judge_exact_seam_identity_mismatch_rejects_before_contact() -> None:
    operation, content = _judge_materials()
    wrong_identity = ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR_JUDGE,
        operation="local-content-quality-v1",
        normalized_input_hash="c" * 64,
        request_hash="d" * 64,
    )
    transport = _FakeTransport([_tags_payload()])
    provider = _judge_provider(transport)

    with pytest.raises(ScoringDispatchDenied, match="identity"):
        provider.judge_exact_model_content(
            operation, content_input=content, expected_identity=wrong_identity
        )

    assert transport.requests == []


def test_primary_judge_identity_substituted_into_repair_judge_is_rejected() -> None:
    from youtube_intel.domain import QualityJudgeAttemptRole
    from youtube_intel.scoring_admission import build_judge_scoring_dispatch_identity

    operation, content = _judge_materials()
    primary_operation = QualityJudgeOperationInput.model_validate(
        {
            **operation.model_dump(mode="json"),
            "attempt_role": QualityJudgeAttemptRole.PRIMARY.value,
        }
    )
    primary_identity = build_judge_scoring_dispatch_identity(primary_operation)
    assert primary_identity.role is ScoringDispatchRole.PRIMARY_JUDGE
    transport = _FakeTransport([_tags_payload()])
    provider = _judge_provider(transport)

    # The strict seam rejects the PRIMARY Judge identity for a REPAIR operation
    # before any external contact.
    with pytest.raises(ScoringDispatchDenied, match="identity"):
        provider.judge_exact_model_content(
            operation, content_input=content, expected_identity=primary_identity
        )

    assert transport.requests == []

    # The private admission operation also refuses non-REPAIR roles.
    repository = _Repository()
    _consume_primary(repository)
    with pytest.raises(ScoringDispatchDenied, match="REPAIR roles"):
        _gate(repository)._consume_runtime_role_and_dispatch(
            primary_identity, lambda: "dispatched", now=_NOW
        )


def test_judge_exact_seam_binding_mismatch_rejects_before_contact() -> None:
    operation, content = _judge_materials()
    forged = QualityJudgeOperationInput.model_validate(
        {**operation.model_dump(mode="json"), "judge_model": "other-model:1b"}
    )
    h1, h2 = build_judge_h1_h2(forged)
    identity = ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR_JUDGE,
        operation="local-content-quality-v1",
        normalized_input_hash=h1,
        request_hash=h2,
    )
    transport = _FakeTransport([_tags_payload()])
    provider = _judge_provider(transport)

    with pytest.raises(ScoringDispatchDenied):
        provider.judge_exact_model_content(
            forged, content_input=content, expected_identity=identity
        )

    assert transport.requests == []


def test_legacy_judge_stash_exposes_exact_raw_for_primary_evidence() -> None:
    operation, content = _judge_materials()
    judge_raw = json.dumps(
        {
            "status": "PASS",
            "decision_confidence": "HIGH",
            "grounding_confidence": "MEDIUM",
            "usefulness_confidence": "MEDIUM",
            "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
            "reason": None,
            "evidence_ids": ["title-1"],
        }
    )
    transport = _FakeTransport([_tags_payload(), _generate_body(judge_raw)])
    provider = _judge_provider(transport)

    result = provider.judge(operation, content_input=content)

    assert result.status.value == "PASS"
    assert provider.consume_extracted_judge_model_content() == judge_raw
    assert provider.consume_extracted_judge_model_content() is None


def test_legacy_judge_transport_failure_stashes_no_raw() -> None:
    operation, content = _judge_materials()
    transport = _FakeTransport([TimeoutError("gone")])
    provider = _judge_provider(transport)

    result = provider.judge(operation, content_input=content)

    assert result.status.value == "UNCERTAIN"
    assert provider.consume_extracted_judge_model_content() is None


# ---------------------------------------------------------------------------
# Private atomic role-consumption-and-dispatch composition
# ---------------------------------------------------------------------------


class _Repository:
    def __init__(self, *, owner: str = "runtime-a") -> None:
        self.job = JobRecord(
            job_id="scoring-job",
            scope_key="video:video-1:SCORING",
            video_id="video-1",
            job_type=JobType.VIDEO_STAGE,
            target_stage=ProcessingStage.SCORING,
            pipeline_version="runtime-v1",
            status=JobStatus.RUNNING,
            attempt_count=1,
            max_attempts=3,
            available_at=_NOW,
            lease_owner=owner,
            lease_until=_NOW + timedelta(minutes=5),
            last_error_code=None,
            last_error_message=None,
            created_at=_NOW,
            updated_at=_NOW,
            finished_at=None,
        )
        self.calls: dict[str, object] = {}

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.job if job_id == self.job.job_id else None

    def get_provider_call(self, request_hash: str) -> object | None:
        return self.calls.get(request_hash)


def _gate(repository: _Repository, *, owner: str = "runtime-a") -> ScoringDispatchAdmission:
    return ScoringDispatchAdmission(
        repository=repository, job_id="scoring-job", owner=owner
    )


def _repair_identity(suffix: str = "a") -> ScoringDispatchIdentity:
    return ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR,
        operation="local-scoring-repair-v1",
        normalized_input_hash=(suffix * 64)[:64],
        request_hash=(suffix * 64)[:64],
    )


def _repair_judge_identity(suffix: str = "j") -> ScoringDispatchIdentity:
    return ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR_JUDGE,
        operation="local-content-quality-v1",
        normalized_input_hash=(suffix * 64)[:64],
        request_hash=(suffix * 64)[:64],
    )


def _consume_primary(repository: _Repository) -> None:
    _gate(repository).admit(
        ScoringDispatchIdentity(
            role=ScoringDispatchRole.PRIMARY,
            operation="local-scoring",
            normalized_input_hash="p" * 64,
            request_hash="p" * 64,
        ),
        now=_NOW,
    )


def test_private_dispatch_rejects_non_repair_roles() -> None:
    repository = _Repository()
    _consume_primary(repository)
    primary_identity = ScoringDispatchIdentity(
        role=ScoringDispatchRole.PRIMARY,
        operation="local-scoring",
        normalized_input_hash="q" * 64,
        request_hash="q" * 64,
    )

    with pytest.raises(ScoringDispatchDenied, match="REPAIR roles"):
        _gate(repository)._consume_runtime_role_and_dispatch(
            primary_identity, lambda: "dispatched", now=_NOW
        )


def test_private_dispatch_repair_requires_consumed_primary() -> None:
    repository = _Repository()
    dispatched: list[str] = []

    with pytest.raises(ScoringDispatchDenied, match="PRIMARY"):
        _gate(repository)._consume_runtime_role_and_dispatch(
            _repair_identity(),
            lambda: dispatched.append("x"),
            now=_NOW,
        )

    assert dispatched == []


def test_private_dispatch_repair_judge_requires_consumed_repair() -> None:
    repository = _Repository()
    _consume_primary(repository)
    dispatched: list[str] = []

    with pytest.raises(ScoringDispatchDenied, match="REPAIR"):
        _gate(repository)._consume_runtime_role_and_dispatch(
            _repair_judge_identity(),
            lambda: dispatched.append("x"),
            now=_NOW,
        )

    assert dispatched == []


def test_private_dispatch_rejects_wrong_operation_literal() -> None:
    repository = _Repository()
    _consume_primary(repository)
    wrong_operation = ScoringDispatchIdentity(
        role=ScoringDispatchRole.REPAIR,
        operation="local-scoring",
        normalized_input_hash="a" * 64,
        request_hash="a" * 64,
    )

    with pytest.raises(ScoringDispatchDenied):
        _gate(repository)._consume_runtime_role_and_dispatch(
            wrong_operation, lambda: "dispatched", now=_NOW
        )


def test_private_dispatch_duplicate_repair_role_is_rejected() -> None:
    repository = _Repository()
    _consume_primary(repository)
    gate = _gate(repository)
    first = gate._consume_runtime_role_and_dispatch(
        _repair_identity(), lambda: "first", now=_NOW
    )
    assert first == "first"

    with pytest.raises(ScoringDispatchDenied, match="already consumed"):
        gate._consume_runtime_role_and_dispatch(
            _repair_identity("b"), lambda: "second", now=_NOW
        )


def test_private_dispatch_existing_provider_call_blocks_repair() -> None:
    repository = _Repository()
    _consume_primary(repository)
    identity = _repair_identity()
    repository.calls[identity.request_hash] = object()

    with pytest.raises(ScoringDispatchDenied, match="existing provider state"):
        _gate(repository)._consume_runtime_role_and_dispatch(
            identity, lambda: "dispatched", now=_NOW
        )


def test_private_dispatch_lost_lease_is_rejected_before_dispatch() -> None:
    repository = _Repository()
    _consume_primary(repository)
    dispatched: list[str] = []

    with pytest.raises(ScoringDispatchDenied, match="lease"):
        _gate(repository, owner="other-runtime")._consume_runtime_role_and_dispatch(
            _repair_identity(), lambda: dispatched.append("x"), now=_NOW
        )

    assert dispatched == []


# ---------------------------------------------------------------------------
# REPAIR Judge trusted-context derivation
# ---------------------------------------------------------------------------


def test_derive_repair_judge_context_binds_repair_request_hash() -> None:
    scoring_input = _scoring_input()
    candidate = ScoringCandidate.model_validate(
        {"score": 8, "reason": _EN_REASON, "topics": ["t"], "should_summarize": True}
    )
    repair_request_hash = "e" * 64

    ctx, judge_input = derive_repair_judge_trusted_context(
        repair_request_hash=repair_request_hash,
        trusted_candidate=candidate,
        scoring_input=scoring_input,
        validated_settings=_settings(),
    )

    assert ctx.role == "REPAIR"
    assert ctx.scoring_request_hash == repair_request_hash
    assert ctx.operation_input.attempt_role.value == "REPAIR"
    assert ctx.operation_input.scoring_request_hash == repair_request_hash
    assert judge_input.scoring_request_hash == repair_request_hash
    assert judge_input.reason == candidate.reason
    assert judge_input.output_language == "en"
    h1, h2 = build_judge_h1_h2(ctx.operation_input)
    assert (ctx.expected_h1, ctx.expected_h2) == (h1, h2)
    assert ctx.model == _MODEL
    assert ctx.model_digest == _DIGEST


def test_derive_repair_judge_context_is_distinct_from_primary_judge() -> None:
    scoring_input = _scoring_input()
    candidate = ScoringCandidate.model_validate(
        {"score": 8, "reason": _EN_REASON, "topics": ["t"], "should_summarize": True}
    )
    trusted_context = build_primary_trusted_context(
        scoring_input=scoring_input,
        model=_MODEL,
        model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )
    primary_ctx, primary_input = derive_primary_judge_trusted_context(
        primary_trusted_context=trusted_context,
        trusted_candidate=candidate,
        validated_settings=_settings(),
    )
    repair_ctx, repair_input = derive_repair_judge_trusted_context(
        repair_request_hash="e" * 64,
        trusted_candidate=candidate,
        scoring_input=scoring_input,
        validated_settings=_settings(),
    )

    assert repair_ctx.expected_h1 != primary_ctx.expected_h1
    assert repair_ctx.expected_h2 != primary_ctx.expected_h2
    assert repair_input.scoring_request_hash != primary_input.scoring_request_hash
