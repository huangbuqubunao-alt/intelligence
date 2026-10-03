"""TASK-022 evidence-bound personalized distillation and resource ledger contracts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.distillation import (
    BudgetDecision,
    CloudConsentRequiredError,
    CloudDistillationAuthorization,
    CloudDistillationPreDispatchError,
    DistillationCapabilityScope,
    DistillationCommand,
    DistillationExecutionStatus,
    DistillationTransportResult,
    KnownCloudDistillationResponseError,
    MoonshotK26CloudDistillationTransport,
    MoonshotK26NonThinkingCloudDistillationTransport,
    NormalV1ProductionAuthorizationAuthority,
    NvidiaNimCloudDistillationTransport,
    OpenAICloudDistillationTransport,
    PersonalizedDistillationService,
    _MoonshotWireResponse,
)
from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
    VerifiedIntelligenceRead,
)
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.preference_service import PreferenceApplicationService
from youtube_intel.source_policy import (
    MetadataFilterCandidate,
    SourcePolicyApplicationService,
    VideoType,
)
from youtube_intel.source_run import (
    SourceRunAttentionReason,
    SourceRunChildState,
    SourceRunPriority,
    SourceRunState,
    SourceRunWrite,
)
from youtube_intel.state import (
    Availability,
    DistillationCardWrite,
    DistillationExecutionWrite,
    DistillationStyle,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceStance,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    FeedbackKind,
    FeedbackWrite,
    IntegrityConflict,
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
    LiveStatus,
    PreferenceScope,
    SQLiteStateRepository,
    StateStoreError,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VideoMetadata,
    build_evidence_id,
)

NOW = datetime(2026, 9, 7, 9, 0, tzinfo=UTC)


class _FakeBudget:
    def __init__(self, allowed: bool, *, state: str = "ADMITTED") -> None:
        self._decision = BudgetDecision(allowed=allowed, state=state)
        self.calls = 0

    def check(self, command: DistillationCommand) -> BudgetDecision:
        self.calls += 1
        return self._decision


class _FakeTransport:
    is_offline_test_transport = True

    def __init__(
        self,
        raw: str,
        *,
        available: bool = True,
        actual_provider: str = "test-transport",
        actual_model: str = "deterministic-v1",
        input_tokens: int | None = 120,
        output_tokens: int | None = 45,
        cost_microunits: int | None = 7,
        duration_ms: int | None = 8,
    ) -> None:
        self.raw = raw
        self.available = available
        self.actual_provider = actual_provider
        self.actual_model = actual_model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost_microunits = cost_microunits
        self.duration_ms = duration_ms
        self.calls = 0
        self.commands: list[DistillationCommand] = []

    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        self.commands.append(command)
        return DistillationTransportResult(
            raw=self.raw,
            actual_provider=self.actual_provider,
            actual_model=self.actual_model,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cost_microunits=self.cost_microunits,
            duration_ms=self.duration_ms,
        )


class _RaisingTransport(_FakeTransport):
    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        self.commands.append(command)
        raise RuntimeError("transport outcome is unknown")


def test_cloud_transport_is_default_denied_and_never_invokes_wire_adapter() -> None:
    calls: list[object] = []
    transport = OpenAICloudDistillationTransport(
        authorization=CloudDistillationAuthorization(),
        credential_resolver=lambda: "credential-not-used",
        wire_transport=lambda request, credential, timeout, retries: calls.append(request) or {},
    )

    assert transport.available is False
    assert transport.is_authorized_for(_verified_input_for_cloud_test()) is False
    assert calls == []


def test_cloud_transport_qualification_scope_uses_no_retry_wire_contract() -> None:
    calls: list[tuple[object, str, float, int]] = []
    verified = _verified_input_for_cloud_test()
    transport = OpenAICloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="openai",
            model="gpt-4.1",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified.semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: "test-credential",
        wire_transport=lambda request, credential, timeout, retries: calls.append(
            (request, credential, timeout, retries)
        ) or {
            "object": "response", "status": "completed", "model": "gpt-4.1",
            "output": [{"type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": "{}"}]}],
        },
    )

    response = transport.generate(verified)

    assert response.actual_model == "gpt-4.1"
    assert len(calls) == 1
    request, credential, _timeout, retries = calls[0]
    assert credential == "test-credential"
    assert retries == 0
    assert request["endpoint_identity"] == "openai-responses-v1"
    assert [item["role"] for item in request["input"]] == ["system", "developer", "user"]


def test_openai_transport_rejects_nvidia_authorization_before_credential_or_wire() -> None:
    credential_resolutions = 0
    calls: list[object] = []

    def resolve_credential() -> str:
        nonlocal credential_resolutions
        credential_resolutions += 1
        return "credential-not-used"

    transport = OpenAICloudDistillationTransport(
        authorization=_normal_nvidia_authorization(
            provider="nvidia_nim",
            model="moonshotai/kimi-k3",
            credential_available=True,
        ),
        credential_resolver=resolve_credential,
        wire_transport=lambda request, credential, timeout, retries: calls.append(request)
        or {},
    )
    verified = _verified_input_for_nvidia_nim_test()

    assert transport.is_authorized_for(verified) is False
    with pytest.raises(CloudDistillationPreDispatchError, match="not authorized"):
        transport.generate(verified)
    assert credential_resolutions == 0
    assert calls == []


def test_nvidia_nim_transport_is_default_denied_before_credential_or_http_boundary() -> None:
    credential_resolutions = 0
    calls: list[object] = []

    def resolve_credential() -> str:
        nonlocal credential_resolutions
        credential_resolutions += 1
        return "credential-not-used"

    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(),
        credential_resolver=resolve_credential,
        wire_transport=lambda endpoint, request, credential, timeout, retries: calls.append(
            request
        )
        or {},
    )

    assert transport.available is False
    assert transport.is_authorized_for(_verified_input_for_nvidia_nim_test()) is False
    assert credential_resolutions == 0
    assert calls == []


def test_nvidia_nim_transport_uses_fixed_endpoint_model_and_zero_retry_contract() -> None:
    calls: list[tuple[str, object, str, float, int]] = []
    verified = _verified_input_for_nvidia_nim_test()
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="nvidia_nim",
            model="moonshotai/kimi-k3",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified.semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: "test-only-nvidia-credential",
        wire_transport=lambda endpoint, request, credential, timeout, retries: calls.append(
            (endpoint, request, credential, timeout, retries)
        )
        or {
            "id": "request-fixture",
            "model": "moonshotai/kimi-k3",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "{}", "role": "assistant"},
                }
            ],
            "usage": {"prompt_tokens": 120, "completion_tokens": 45},
        },
    )

    response = transport.generate(verified)

    assert response.actual_provider == "nvidia_nim"
    assert response.actual_model == "moonshotai/kimi-k3"
    assert response.input_tokens == 120
    assert response.output_tokens == 45
    assert len(calls) == 1
    endpoint, request, credential, _timeout, retries = calls[0]
    assert endpoint == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert credential == "test-only-nvidia-credential"
    assert retries == 0
    assert request["model"] == "moonshotai/kimi-k3"
    assert request["stream"] is False
    assert "response_format" not in request
    assert [item["role"] for item in request["messages"]] == ["system", "system", "user"]
    assert "test-only-nvidia-credential" not in json.dumps(request, sort_keys=True)
    contract = request["messages"][0]["content"]
    assert "revisable judgment worth retaining beyond a one-off Summary" in contract
    assert "Cite only the relevant subset of supplied Evidence" in contract
    assert "at least one supporting item" in contract
    assert "stance exactly supporting, contradicting, or conditional" in contract
    assert "Include material relevant contradiction or qualification" in contract
    assert "every supplied evidence_id, start_ms, and end_ms once" in contract
    assert "Write generated Intelligence text in zh-CN" in contract
    assert "evidence must cite every supplied" not in contract
    assert request["max_tokens"] == 8_192
    assert request["reasoning_effort"] == "high"
    assert request["temperature"] == 1.0


def test_kimi_reasoning_metadata_never_becomes_final_content_or_diagnostics_text() -> None:
    verified = _verified_input_for_nvidia_nim_test()
    secret = "synthetic-secret-never-report"
    reasoning = "synthetic-reasoning-never-report"
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True, provider="nvidia_nim", model="moonshotai/kimi-k3",
            credential_available=True, provider_available=True,
            qualification_input_hash=verified.semantic_hash,
        ),
        credential_resolver=lambda: secret,
        wire_transport=lambda *_: {
            "model": "moonshotai/kimi-k3",
            "choices": [{"finish_reason": "stop", "message": {
                "content": "{}", "reasoning_content": reasoning,
            }}],
            "usage": {"prompt_tokens": 45, "completion_tokens": 67,
                      "completion_tokens_details": {"reasoning_tokens": 23}},
        },
    )

    result = transport.generate(verified)
    diagnostics = transport.last_response_diagnostics
    assert result.raw == "{}"
    assert diagnostics is not None
    assert diagnostics.content_present is True
    assert diagnostics.content_length == 2
    assert diagnostics.reasoning_present is True
    assert diagnostics.reasoning_length == len(reasoning)
    assert diagnostics.finish_reason == "stop"
    assert diagnostics.reasoning_tokens == 23
    assert reasoning not in repr(diagnostics)
    assert reasoning not in json.dumps(asdict(diagnostics))
    assert secret not in repr(diagnostics)


@pytest.mark.parametrize(
    ("choice", "expected_reason"),
    [
        ({"finish_reason": "stop", "message": {"content": None, "reasoning_content": "private-reasoning"}}, "CLOUD_FINAL_CONTENT_MISSING"),
        ({"finish_reason": "stop", "message": {"content": "", "reasoning_content": "private-reasoning"}}, "CLOUD_FINAL_CONTENT_MISSING"),
        ({"finish_reason": "length", "message": {"content": None, "reasoning_content": "private-reasoning"}}, "CLOUD_OUTPUT_TRUNCATED"),
        ({"finish_reason": "stop", "message": "malformed-message"}, "CLOUD_HTTP_RESPONSE_INVALID"),
        ({"finish_reason": ["malformed"], "message": {"content": "{}"}}, "CLOUD_HTTP_RESPONSE_INVALID"),
        ({"message": {"content": "{}"}}, "CLOUD_HTTP_RESPONSE_INVALID"),
    ],
)
def test_kimi_known_response_cases_are_finite_and_never_expose_reasoning(
    choice: object, expected_reason: str,
) -> None:
    verified = _verified_input_for_nvidia_nim_test()
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True, provider="nvidia_nim", model="moonshotai/kimi-k3",
            credential_available=True, provider_available=True,
            qualification_input_hash=verified.semantic_hash,
        ),
        credential_resolver=lambda: "synthetic-secret-never-report",
        wire_transport=lambda *_: {
            "model": "moonshotai/kimi-k3", "choices": [choice],
            "usage": {"prompt_tokens": 120, "completion_tokens": 32},
        },
    )

    with pytest.raises(KnownCloudDistillationResponseError) as captured:
        transport.generate(verified)
    error = captured.value
    assert error.reason == expected_reason
    assert error.result is not None
    assert error.result.input_tokens == 120
    assert error.result.output_tokens == 32
    assert "private-reasoning" not in repr(error)
    assert "synthetic-secret-never-report" not in repr(error)
    diagnostics = transport.last_response_diagnostics
    assert diagnostics is not None
    assert "private-reasoning" not in json.dumps(asdict(diagnostics))


def test_kimi_wrong_model_is_known_response_not_ambiguous() -> None:
    verified = _verified_input_for_nvidia_nim_test()
    untrusted_model = "synthetic-secret-model-value"
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True, provider="nvidia_nim", model="moonshotai/kimi-k3",
            credential_available=True, provider_available=True,
            qualification_input_hash=verified.semantic_hash,
        ),
        credential_resolver=lambda: "synthetic-secret",
        wire_transport=lambda *_: {"model": untrusted_model, "choices": [
            {"finish_reason": "stop", "message": {"content": "{}"}}
        ]},
    )
    result = transport.generate(verified)
    assert result.actual_model == untrusted_model
    assert transport.last_response_diagnostics is not None
    assert transport.last_response_diagnostics.model_identity == "OTHER"
    assert untrusted_model not in repr(transport.last_response_diagnostics)


def test_kimi_v3_request_keeps_all_fifteen_candidate_evidence() -> None:
    base = _verified_input_for_nvidia_nim_test()
    evidence = tuple(
        replace(base.evidence[0], evidence_id=f"candidate-{index:02d}",
                start_ms=index * 1_000, end_ms=(index + 1) * 1_000)
        for index in range(15)
    )
    request = NvidiaNimCloudDistillationTransport._request(
        replace(base, evidence=evidence)
    )
    payload = json.loads(request["messages"][2]["content"].removeprefix("UNTRUSTED_SOURCE_EVIDENCE="))
    assert len(payload["evidence"]) == 15
    assert [item["evidence_id"] for item in payload["evidence"]] == [
        item.evidence_id for item in evidence
    ]
    assert [(item["start_ms"], item["end_ms"]) for item in payload["evidence"]] == [
        (item.start_ms, item.end_ms) for item in evidence
    ]


@pytest.mark.parametrize(
    ("content", "finish_reason", "expected_outcome"),
    [(None, "stop", "CLOUD_FINAL_CONTENT_MISSING"),
     (None, "length", "CLOUD_OUTPUT_TRUNCATED")],
)
def test_kimi_known_final_output_failure_is_persisted_without_reasoning(
    tmp_path: Path, content: object, finish_reason: str, expected_outcome: str,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    reasoning = "private-reasoning-must-not-persist"
    calls = 0

    def wire(*_args):
        nonlocal calls
        calls += 1
        return {
            "model": "moonshotai/kimi-k3",
            "choices": [{"finish_reason": finish_reason, "message": {
                "content": content, "reasoning_content": reasoning,
            }}],
            "usage": {"prompt_tokens": 5644, "completion_tokens": 32},
        }

    transport = NvidiaNimCloudDistillationTransport(
        authorization=_normal_nvidia_authorization(),
        credential_resolver=lambda: "synthetic-secret-must-not-persist",
        wire_transport=wire,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    service.authorize_reserved_cloud_execution(reservation.execution_id)
    first = service.continue_reserved_distillation(reservation.execution_id)
    second = service.continue_reserved_distillation(reservation.execution_id)
    ledger = repository.get_distillation_resource_usage(reservation.execution_id)
    assert first.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert second == first
    assert first.invocation_count == calls == 1
    assert ledger.outcome == expected_outcome
    assert ledger.actual_provider == "nvidia_nim"
    assert ledger.actual_model == "moonshotai/kimi-k3"
    assert (ledger.input_tokens, ledger.output_tokens) == (5644, 32)
    assert repository.list_distillation_cards() == ()
    assert reasoning.encode() not in (tmp_path / "state.sqlite3").read_bytes()
    assert b"synthetic-secret-must-not-persist" not in (tmp_path / "state.sqlite3").read_bytes()


def test_nvidia_nim_qualification_can_wait_300_seconds_for_the_same_single_request() -> None:
    calls: list[tuple[float, int]] = []
    credential_resolutions = 0
    verified = _verified_input_for_nvidia_nim_test()

    def resolve_credential() -> str:
        nonlocal credential_resolutions
        credential_resolutions += 1
        return "test-only-nvidia-credential"

    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="nvidia_nim",
            model="moonshotai/kimi-k3",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified.semantic_hash,
            qualification_max_calls=1,
            qualification_response_wait_timeout_seconds=300,
        ),
        credential_resolver=resolve_credential,
        wire_transport=lambda endpoint, request, credential, timeout, retries: calls.append(
            (timeout, retries)
        )
        or {
            "model": "moonshotai/kimi-k3",
            "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
        },
    )

    transport.generate(verified)

    assert credential_resolutions == 1
    assert calls == [(300.0, 0)]


def test_qualification_scope_never_authorizes_a_normal_source_run() -> None:
    verified = _verified_input_for_nvidia_nim_test()
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="nvidia_nim",
            model="moonshotai/kimi-k3",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified.semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: "credential-not-used",
        wire_transport=lambda endpoint, request, credential, timeout, retries: {},
    )

    assert transport.is_authorized_for(verified) is True
    assert transport.is_authorized_for_normal_production(verified) is False


def test_absent_qualification_hash_cannot_equal_malformed_verified_identity() -> None:
    verified = replace(
        _verified_input_for_nvidia_nim_test(), semantic_hash=cast(str, None)
    )
    authorization = CloudDistillationAuthorization(
        cloud_enabled=True,
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        credential_available=True,
        provider_available=True,
    )

    assert authorization.permits(verified) is False


def test_nvidia_nim_qualification_timeout_cannot_expand_normal_production() -> None:
    eligibility = NormalV1ProductionAuthorizationAuthority.resolve(
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=True,
    )

    with pytest.raises(TypeError):
        CloudDistillationAuthorization.for_normal_production(
            eligibility=eligibility,
            cloud_enabled=True,
            credential_available=True,
            qualification_response_wait_timeout_seconds=300,  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        ("openai", "moonshotai/kimi-k3"),
        ("nvidia_nim", "kimi-k3"),
        ("nvidia_nim", "moonshotai/kimi-k2-thinking"),
    ],
)
def test_nvidia_nim_transport_rejects_provider_or_model_substitution_before_dispatch(
    provider: str, model: str
) -> None:
    verified = _verified_input_for_nvidia_nim_test()
    calls: list[object] = []
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider=provider,
            model=model,
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified.semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: "credential-not-used",
        wire_transport=lambda endpoint, request, credential, timeout, retries: calls.append(
            request
        )
        or {},
    )

    assert transport.is_authorized_for(verified) is False
    with pytest.raises(CloudDistillationPreDispatchError, match="not authorized"):
        transport.generate(verified)
    assert calls == []


def _verified_input_for_cloud_test():
    from youtube_intel.distillation import VerifiedDistillationInput

    return VerifiedDistillationInput(
        source_display_name="Public source",
        video_id="video-cloud",
        video_title="Public video",
        evidence=(),
        personalization=(),
        source_focus_rules=(),
        source_ignore_rules=(),
        distillation_style=None,
        selected_provider="openai",
        selected_model="gpt-4.1",
        semantic_hash="a" * 64,
        output_language="zh-CN",
    )


def _verified_input_for_nvidia_nim_test():
    from youtube_intel.distillation import (
        VerifiedDistillationInput,
        VerifiedEvidenceInput,
    )

    return VerifiedDistillationInput(
        source_display_name="Public source",
        video_id="video-nvidia-nim",
        video_title="Public video",
        evidence=(
            VerifiedEvidenceInput(
                evidence_id="evidence-nvidia-nim",
                start_ms=1_000,
                end_ms=2_000,
                excerpt="A bounded public evidence excerpt.",
                excerpt_hash="c" * 64,
                timed_transcript_id="timed-nvidia-nim",
                timed_transcript_hash="d" * 64,
            ),
        ),
        personalization=("Prefer actionable product lessons.",),
        source_focus_rules=("AI infrastructure",),
        source_ignore_rules=("sponsor messages",),
        distillation_style="BALANCED",
        selected_provider="nvidia_nim",
        selected_model="moonshotai/kimi-k3",
        semantic_hash="b" * 64,
        output_language="zh-CN",
    )


def _normal_nvidia_authorization(
    *,
    provider: str = "nvidia_nim",
    model: str = "moonshotai/kimi-k3",
    available: bool = True,
    cloud_enabled: bool = True,
    credential_available: bool = True,
) -> CloudDistillationAuthorization:
    eligibility = NormalV1ProductionAuthorizationAuthority.resolve(
        provider=provider,
        model=model,
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=available,
    )
    return CloudDistillationAuthorization.for_normal_production(
        eligibility=eligibility,
        cloud_enabled=cloud_enabled,
        credential_available=credential_available,
    )


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=NOW).version == 31
    return repository


def _source_and_video(
    repository: SQLiteStateRepository, video_id: str = "video-022"
) -> tuple[str, str]:
    source = ProductOrchestrationService(repository, now=lambda: NOW).add_source(
        url="https://www.youtube.com/channel/UC______________________",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UC______________________",
            channel_name="Fixture channel",
            title="AI Agent product update",
            description="Developer tools and product cases.",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=NOW,
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    repository.link_source_video(source.source_id, video_id, discovered_at=NOW)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    policy.update_global(
        command_id=f"eligible-{video_id}",
        initial_history_count=5,
        per_run_max_new_videos=5,
        focus_rules=("AI Agent",),
        ignore_rules=(),
        distillation_style=DistillationStyle.BALANCED,
    )
    policy.evaluate_and_record_stage_one(
        source.source_id,
        MetadataFilterCandidate(
            video_id=video_id,
            title="AI Agent product update",
            description="Developer tools and product cases.",
            channel_name="Fixture channel",
            published_at=NOW,
            video_type=VideoType.STANDARD,
        ),
    )
    return source.source_id, video_id


def _evidence(
    repository: SQLiteStateRepository,
    video_id: str,
    *,
    start_ms: int = 1_000,
    end_ms: int = 1_500,
    source_excerpt: str | None = None,
) -> str:
    timestamp = "2026-09-07T09:00:00Z"
    artifact_id = f"artifact-{video_id}-{start_ms}-{end_ms}"
    connection = repository._connect()
    try:
        existing = connection.execute(
            "SELECT artifact_id FROM artifacts WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        if existing is None:
            connection.execute(
                "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
                "VALUES (?, ?, ?, NULL, 'transcript_canonical', 'DATA', ?, ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
                (artifact_id, f"artifact-key-{video_id}-{start_ms}-{end_ms}", video_id, f"{video_id}-{start_ms}-{end_ms}.txt", "a" * 64, timestamp),
            )
    finally:
        connection.close()
    evidence_id = build_evidence_id(
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=start_ms,
        end_ms=end_ms,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    evidence = EvidenceWrite(
        evidence_id=evidence_id,
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=start_ms,
        end_ms=end_ms,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en",
        availability=EvidenceAvailability.AVAILABLE,
        source_excerpt=source_excerpt,
    )
    if source_excerpt is not None:
        repository.create_evidence(evidence, now=NOW)
        return evidence_id
    timed = TimedTranscriptWrite.from_cues(
        video_id=video_id,
        canonical_artifact_id=artifact_id,
        cues=(TimedTranscriptCueWrite(start_ms=start_ms, end_ms=end_ms, text="Fixture canonical evidence."),),
    )
    repository.create_timed_transcript(timed, now=NOW)
    repository.create_evidence_with_text_binding(
        evidence,
        EvidenceTextBindingWrite.from_timed_transcript(
            evidence=evidence,
            timed_transcript_id=timed.timed_transcript_id,
            start_cue_index=0,
            end_cue_index=1,
            excerpt="Fixture canonical evidence.",
        ),
        now=NOW,
    )
    return evidence_id


def _raw(
    evidence_id: str,
    *,
    claim_kind: IntelligenceClaimKind = IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
    start_ms: int = 1_000,
    end_ms: int = 1_500,
    stance: str = "supporting",
) -> str:
    return json.dumps(
        {
            "core_conclusion": "The release adds evidence-bound execution records.",
            "user_relevant_information": ["It foregrounds product evidence."],
            "important_new_information": ["Execution identity is retained."],
            "meaningful_details": ["The transcript names the release boundary."],
            "filtered_noise": ["Sponsor segment omitted."],
            "claim_kind": claim_kind.value,
            "evidence": [
                {
                    "evidence_id": evidence_id,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "stance": stance,
                }
            ],
        },
        separators=(",", ":"),
    )


def _no_new_raw(
    evidence_id: str, *, start_ms: int = 1_000, end_ms: int = 1_500
) -> str:
    return json.dumps(
        {
            "result": "NO_NEW_INTELLIGENCE",
            "evidence": [
                {
                    "evidence_id": evidence_id,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                }
            ],
        },
        separators=(",", ":"),
    )


def _service(
    repository: SQLiteStateRepository,
    transport: _FakeTransport,
    budget: _FakeBudget | None = None,
) -> PersonalizedDistillationService:
    return PersonalizedDistillationService(
        repository,
        SourcePolicyApplicationService(repository, now=lambda: NOW),
        transport,
        budget or _FakeBudget(True),
        now=lambda: NOW,
    )


def _openai_qualification_service(
    repository: SQLiteStateRepository,
    *,
    source_id: str,
    video_id: str,
    evidence_ids: tuple[str, ...],
    wire_transport,
) -> tuple[PersonalizedDistillationService, object, object]:
    initial_transport = OpenAICloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="openai",
            model="gpt-4.1",
            credential_available=True,
            provider_available=True,
            qualification_input_hash="0" * 64,
        ),
        credential_resolver=lambda: "synthetic-openai-secret",
        wire_transport=lambda *_args: {},
    )
    initial_service = _service(repository, initial_transport)  # type: ignore[arg-type]
    reservation = initial_service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=evidence_ids
    )
    record = repository.get_distillation_execution(reservation.execution_id)
    assert record is not None
    _, verified_input = initial_service._reserved_command_from_record(record)
    transport = OpenAICloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="openai",
            model="gpt-4.1",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified_input.semantic_hash,
        ),
        credential_resolver=lambda: "synthetic-openai-secret",
        wire_transport=wire_transport,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]
    return service, reservation, verified_input


def _moonshot_qualification_service(
    repository: SQLiteStateRepository,
    *,
    source_id: str,
    video_id: str,
    evidence_ids: tuple[str, ...],
    wire_transport,
    transport_type: type[MoonshotK26CloudDistillationTransport] = MoonshotK26CloudDistillationTransport,
) -> tuple[PersonalizedDistillationService, object, object, MoonshotK26CloudDistillationTransport]:
    initial_transport = transport_type(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="moonshot",
            model="kimi-k2.6",
            credential_available=True,
            provider_available=True,
            qualification_input_hash="0" * 64,
        ),
        credential_resolver=lambda: "synthetic-moonshot-secret",
        wire_transport=lambda *_args: {},
    )
    initial_service = _service(repository, initial_transport)  # type: ignore[arg-type]
    reservation = initial_service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=evidence_ids
    )
    record = repository.get_distillation_execution(reservation.execution_id)
    assert record is not None
    _, verified_input = initial_service._reserved_command_from_record(record)
    transport = transport_type(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="moonshot",
            model="kimi-k2.6",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified_input.semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: "synthetic-moonshot-secret",
        wire_transport=wire_transport,
    )
    return _service(repository, transport), reservation, verified_input, transport  # type: ignore[arg-type]


def _nvidia_qualification_service(
    repository: SQLiteStateRepository,
    *,
    source_id: str,
    video_id: str,
    evidence_ids: tuple[str, ...],
    wire_transport,
) -> tuple[PersonalizedDistillationService, object]:
    initial_transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="nvidia_nim",
            model="moonshotai/kimi-k3",
            credential_available=True,
            provider_available=True,
            qualification_input_hash="0" * 64,
        ),
        credential_resolver=lambda: "synthetic-historical-secret",
        wire_transport=lambda *_args: {},
    )
    initial_service = _service(repository, initial_transport)  # type: ignore[arg-type]
    reservation = initial_service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=evidence_ids
    )
    record = repository.get_distillation_execution(reservation.execution_id)
    assert record is not None
    _, verified_input = initial_service._reserved_command_from_record(record)
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="nvidia_nim",
            model="moonshotai/kimi-k3",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified_input.semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: "synthetic-historical-secret",
        wire_transport=wire_transport,
    )
    return _service(repository, transport), reservation  # type: ignore[arg-type]


def _command(source_id: str, video_id: str, evidence_id: str, *, execution_id: str = "exec-1") -> DistillationCommand:
    return DistillationCommand(
        execution_id=execution_id,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=(evidence_id,),
        reason="MANUAL_PERSONALIZED_DISTILLATION",
        use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider="test-transport",
        selected_model="deterministic-v1",
        output_language="zh-CN",
    )


def test_successful_no_new_intelligence_is_durable_and_non_redispatchable(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _FakeTransport(_no_new_raw(evidence_id))
    command = _command(
        source_id, video_id, evidence_id, execution_id="exec-no-new"
    )

    result = _service(repository, transport).distill(command)

    assert result.status is DistillationExecutionStatus.SUCCEEDED_NO_NEW_INTELLIGENCE
    assert result.invocation_count == 1
    assert result.intelligence_id is None
    assert result.revision_id is None
    assert repository.list_current_intelligence_ids() == ()
    assert repository.list_distillation_cards() == ()
    usage = repository.get_distillation_resource_usage("exec-no-new")
    assert usage.status == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    assert usage.outcome == "NO_NEW_INTELLIGENCE"
    assert usage.intelligence_id is None
    assert usage.revision_id is None
    assert usage.actual_provider == "test-transport"
    assert usage.actual_model == "deterministic-v1"

    restarted = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert restarted.initialize(now=NOW).version == 31
    persisted = restarted.get_distillation_execution("exec-no-new")
    assert persisted is not None
    assert persisted.status == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    repeated = _service(restarted, transport).distill(command)
    assert repeated.status is DistillationExecutionStatus.SUCCEEDED_NO_NEW_INTELLIGENCE
    assert transport.calls == 1

    with restarted._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE distillation_no_new_intelligence_results "
                "SET outcome = 'FORGED' WHERE execution_id = ?",
                ("exec-no-new",),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM distillation_no_new_intelligence_results "
                "WHERE execution_id = ?",
                ("exec-no-new",),
            )


def test_no_new_result_requires_a_claimed_real_invocation(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id="exec-uninvoked-zero",
            source_id=source_id,
            video_id=video_id,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="test-transport",
            selected_model="deterministic-v1",
        ),
        now=NOW,
    )

    with pytest.raises(StateStoreError, match="legal invocation"):
        repository.record_distillation_no_new_intelligence(
            execution_id="exec-uninvoked-zero",
            evidence_ids=(evidence_id,),
            budget_state="ADMITTED",
            actual_provider="test-transport",
            actual_model="deterministic-v1",
            input_tokens=None,
            output_tokens=None,
            cost_microunits=None,
            duration_ms=None,
            now=NOW,
        )

    persisted = repository.get_distillation_execution("exec-uninvoked-zero")
    assert persisted is not None
    assert persisted.status == "PENDING"
    assert persisted.invocation_count == 0


@pytest.mark.parametrize(
    ("actual_provider", "actual_model"),
    (
        ("other-provider", "deterministic-v1"),
        ("test-transport", "other-model"),
    ),
)
def test_no_new_result_rejects_actual_execution_identity_mismatch(
    tmp_path: Path, actual_provider: str, actual_model: str
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _FakeTransport(
        _no_new_raw(evidence_id),
        actual_provider=actual_provider,
        actual_model=actual_model,
    )

    result = _service(repository, transport).distill(
        _command(source_id, video_id, evidence_id, execution_id="exec-zero-mismatch")
    )

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert result.intelligence_id is None
    assert result.revision_id is None
    with repository._connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM distillation_no_new_intelligence_results"
        ).fetchone()[0] == 0


@pytest.mark.parametrize(
    "raw",
    ("", "{}", "not-json", json.dumps({"result": "UNKNOWN", "evidence": []})),
)
def test_invalid_or_empty_output_never_becomes_no_new_success(
    tmp_path: Path, raw: str
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)

    result = _service(repository, _FakeTransport(raw)).distill(
        _command(source_id, video_id, evidence_id, execution_id=f"exec-invalid-{len(raw)}")
    )

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert result.intelligence_id is None
    assert repository.list_current_intelligence_ids() == ()


def test_no_new_result_fails_closed_if_canonical_evidence_changes_before_write(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)

    class _ChangingEvidenceTransport(_FakeTransport):
        def generate(self, command: DistillationCommand) -> DistillationTransportResult:
            response = super().generate(command)
            _evidence(repository, video_id, start_ms=2_000, end_ms=2_500)
            return response

    result = _service(
        repository, _ChangingEvidenceTransport(_no_new_raw(evidence_id))
    ).distill(
        _command(source_id, video_id, evidence_id, execution_id="exec-stale-evidence")
    )

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert repository.list_current_intelligence_ids() == ()


def test_no_new_result_read_fails_closed_on_evidence_hash_tamper(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    result = _service(repository, _FakeTransport(_no_new_raw(evidence_id))).distill(
        _command(source_id, video_id, evidence_id, execution_id="exec-tamper")
    )
    assert result.status is DistillationExecutionStatus.SUCCEEDED_NO_NEW_INTELLIGENCE

    with repository._connect() as connection:
        connection.execute("DROP TRIGGER distillation_no_new_result_immutable_update")
        connection.execute(
            "UPDATE distillation_no_new_intelligence_results "
            "SET evidence_set_hash = ? WHERE execution_id = ?",
            ("0" * 64, "exec-tamper"),
        )

    with pytest.raises(StateStoreError, match="Evidence hash"):
        repository.get_distillation_execution("exec-tamper")


def test_no_new_result_rejects_stance_or_claim_payload(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    payload = json.loads(_no_new_raw(evidence_id))
    payload["evidence"][0]["stance"] = "supporting"

    result = _service(repository, _FakeTransport(json.dumps(payload))).distill(
        _command(source_id, video_id, evidence_id, execution_id="exec-zero-stance")
    )

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert repository.list_current_intelligence_ids() == ()


def _nvidia_nim_command(
    source_id: str,
    video_id: str,
    evidence_id: str,
    *,
    execution_id: str,
) -> DistillationCommand:
    return DistillationCommand(
        execution_id=execution_id,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=(evidence_id,),
        reason="MANUAL_PERSONALIZED_DISTILLATION",
        use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider="nvidia_nim",
        selected_model="moonshotai/kimi-k3",
        output_language="zh-CN",
    )


def test_nvidia_nim_transport_runs_exact_task022_admission_and_authoritative_read(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    calls: list[tuple[str, object, str, float, int]] = []

    def wire_transport(endpoint, request, credential, timeout, retries):
        calls.append((endpoint, request, credential, timeout, retries))
        return {
            "id": "fixture-nvidia-request",
            "model": "moonshotai/kimi-k3",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": _raw(evidence_id), "role": "assistant"},
                }
            ],
            "usage": {"prompt_tokens": 210, "completion_tokens": 80},
        }

    transport = NvidiaNimCloudDistillationTransport(
        authorization=_normal_nvidia_authorization(),
        credential_resolver=lambda: "synthetic-nvidia-credential",
        wire_transport=wire_transport,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )

    service.authorize_reserved_cloud_execution(reservation.execution_id)
    result = service.continue_reserved_distillation(reservation.execution_id)

    assert result.status is DistillationExecutionStatus.SUCCEEDED
    assert len(calls) == 1
    endpoint, request, credential, _timeout, retries = calls[0]
    assert endpoint == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert credential == "synthetic-nvidia-credential"
    assert retries == 0
    assert "synthetic-nvidia-credential" not in json.dumps(request, sort_keys=True)
    evidence_payload = json.loads(request["messages"][2]["content"].removeprefix("UNTRUSTED_SOURCE_EVIDENCE="))
    assert evidence_payload["evidence"] == [
        {
            "evidence_id": evidence_id,
            "start_ms": 1_000,
            "end_ms": 1_500,
            "excerpt": "Fixture canonical evidence.",
            "excerpt_hash": repository.resolve_verified_evidence_text(evidence_id).excerpt_hash,
            "timed_transcript_id": repository.resolve_verified_evidence_text(evidence_id).timed_transcript_id,
            "timed_transcript_hash": repository.resolve_verified_evidence_text(evidence_id).timed_transcript_hash,
        }
    ]
    card = AuthoritativeIntelligenceReader(repository).read_current_card(
        result.intelligence_id or ""
    )
    assert card.verified.evidence_ids == (evidence_id,)
    ledger = repository.get_distillation_resource_usage(reservation.execution_id)
    assert ledger.selected_provider == "nvidia_nim"
    assert ledger.selected_model == "moonshotai/kimi-k3"
    assert ledger.actual_provider == "nvidia_nim"
    assert ledger.actual_model == "moonshotai/kimi-k3"
    assert ledger.input_tokens == 210 and ledger.output_tokens == 80


def test_normal_production_authority_cannot_use_legacy_unreserved_distill(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    wire_calls = 0

    def wire_transport(endpoint, request, credential, timeout, retries):
        nonlocal wire_calls
        wire_calls += 1
        return {}

    transport = NvidiaNimCloudDistillationTransport(
        authorization=_normal_nvidia_authorization(),
        credential_resolver=lambda: "credential-not-used",
        wire_transport=wire_transport,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]

    result = service.distill(
        _nvidia_nim_command(
            source_id,
            video_id,
            evidence_id,
            execution_id="forged-unreserved-production-execution",
        )
    )

    assert result.status is DistillationExecutionStatus.WAITING_MODEL
    assert result.invocation_count == 0
    assert wire_calls == 0


@pytest.mark.parametrize("raw", ("{not-json", "```json\n{}\n```"))
def test_nvidia_nim_malformed_output_fails_closed_without_repair_or_redispatch(
    tmp_path: Path, raw: str
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    calls = 0

    def wire_transport(endpoint, request, credential, timeout, retries):
        nonlocal calls
        calls += 1
        return {
            "id": "fixture-malformed",
            "model": "moonshotai/kimi-k3",
            "choices": [{"finish_reason": "stop", "message": {"content": raw}}],
        }

    transport = NvidiaNimCloudDistillationTransport(
        authorization=_normal_nvidia_authorization(),
        credential_resolver=lambda: "synthetic-nvidia-credential",
        wire_transport=wire_transport,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )

    service.authorize_reserved_cloud_execution(reservation.execution_id)
    first = service.continue_reserved_distillation(reservation.execution_id)
    second = service.continue_reserved_distillation(reservation.execution_id)

    assert first.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert second == first
    assert calls == 1
    assert repository.list_distillation_cards() == ()


def test_nvidia_nim_missing_backend_credential_is_zero_dispatch(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    wire_calls = 0

    def wire_transport(endpoint, request, credential, timeout, retries):
        nonlocal wire_calls
        wire_calls += 1
        return {}

    transport = NvidiaNimCloudDistillationTransport(
        authorization=_normal_nvidia_authorization(),
        credential_resolver=lambda: "",
        wire_transport=wire_transport,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )

    first = service.continue_reserved_distillation(reservation.execution_id)
    second = service.continue_reserved_distillation(reservation.execution_id)

    assert first.status is DistillationExecutionStatus.WAITING_MODEL
    assert first.invocation_count == 0
    assert second == first
    assert wire_calls == 0
    assert repository.get_distillation_resource_usage(reservation.execution_id).invocation_count == 0


def test_nvidia_nim_environment_resolver_uses_only_backend_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    wire_calls = 0

    def wire_transport(endpoint, request, credential, timeout, retries):
        nonlocal wire_calls
        wire_calls += 1
        return {}

    transport = NvidiaNimCloudDistillationTransport.with_environment_credential(
        authorization=_normal_nvidia_authorization(),
        wire_transport=wire_transport,
    )
    assert transport.preflight_available() is False
    with pytest.raises(CloudDistillationPreDispatchError):
        transport.generate(_verified_input_for_nvidia_nim_test())
    assert wire_calls == 0


def test_nvidia_nim_credential_disappearing_after_preflight_is_known_no_dispatch(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    resolutions = 0
    wire_calls = 0

    def resolve_credential() -> str:
        nonlocal resolutions
        resolutions += 1
        return "present" if resolutions == 1 else ""

    def wire_transport(endpoint, request, credential, timeout, retries):
        nonlocal wire_calls
        wire_calls += 1
        return {}

    transport = NvidiaNimCloudDistillationTransport(
        authorization=_normal_nvidia_authorization(),
        credential_resolver=resolve_credential,
        wire_transport=wire_transport,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )

    service.authorize_reserved_cloud_execution(reservation.execution_id)
    result = service.continue_reserved_distillation(reservation.execution_id)

    assert result.status is DistillationExecutionStatus.WAITING_MODEL
    assert result.invocation_count == 0
    assert resolutions == 2
    assert wire_calls == 0


def test_nvidia_nim_definite_invalid_structured_content_is_rejected_not_ambiguous(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    wire_calls = 0

    def wire_transport(endpoint, request, credential, timeout, retries):
        nonlocal wire_calls
        wire_calls += 1
        return {
            "model": "moonshotai/kimi-k3",
            "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
        }

    transport = NvidiaNimCloudDistillationTransport(
        authorization=_normal_nvidia_authorization(),
        credential_resolver=lambda: "present",
        wire_transport=wire_transport,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )

    service.authorize_reserved_cloud_execution(reservation.execution_id)
    first = service.continue_reserved_distillation(reservation.execution_id)
    second = service.continue_reserved_distillation(reservation.execution_id)

    assert first.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert first.invocation_count == 1
    assert second == first
    assert wire_calls == 1
    assert repository.list_distillation_cards() == ()


def test_nvidia_nim_wire_error_is_sanitized_without_credential_value() -> None:
    verified = _verified_input_for_nvidia_nim_test()
    secret = "synthetic-nvidia-secret-sentinel"

    def wire_transport(endpoint, request, credential, timeout, retries):
        raise RuntimeError(f"unsafe wire detail {credential}")

    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="nvidia_nim",
            model="moonshotai/kimi-k3",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified.semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: secret,
        wire_transport=wire_transport,
    )

    with pytest.raises(RuntimeError) as error:
        transport.generate(verified)
    assert secret not in str(error.value)
    assert secret not in repr(error.value)


def test_nvidia_nim_default_http_boundary_is_fully_mocked_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = _verified_input_for_nvidia_nim_test()
    credential = "synthetic-http-credential"
    connections: list[tuple[str, float]] = []
    requests: list[tuple[str, str, bytes, dict[str, str]]] = []

    class FakeHttpResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exception_type, exception, traceback):
            return False

        def read(self, maximum_bytes: int) -> bytes:
            assert maximum_bytes == 2_000_001
            return json.dumps(
                {
                    "id": "mock-http-response",
                    "model": "moonshotai/kimi-k3",
                    "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                },
                separators=(",", ":"),
            ).encode()

    class FakeHttpsConnection:
        def __init__(self, host: str, *, timeout: float) -> None:
            connections.append((host, timeout))

        def request(
            self, method: str, path: str, *, body: bytes, headers: dict[str, str]
        ) -> None:
            requests.append((method, path, body, headers))

        def getresponse(self) -> FakeHttpResponse:
            return FakeHttpResponse()

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        "youtube_intel.distillation.HTTPSConnection", FakeHttpsConnection
    )
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="nvidia_nim",
            model="moonshotai/kimi-k3",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified.semantic_hash,
            qualification_max_calls=1,
        ),
        credential_resolver=lambda: credential,
    )

    response = transport.generate(verified)

    assert response.actual_model == "moonshotai/kimi-k3"
    assert connections == [("integrate.api.nvidia.com", 120.0)]
    assert len(requests) == 1
    method, path, request_body, headers = requests[0]
    assert method == "POST"
    assert path == "/v1/chat/completions"
    assert headers["Authorization"] == f"Bearer {credential}"
    assert headers["Accept"] == "application/json"
    body = json.loads(request_body)
    assert body["model"] == "moonshotai/kimi-k3"
    assert body["stream"] is False


def test_kimi_http_202_polls_existing_invocation_without_second_post(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = _verified_input_for_nvidia_nim_test()
    request_id = "0f3839f4-a088-42e3-a0b3-ad4509f90f22"
    requests: list[tuple[str, str]] = []

    class FakeHttpResponse:
        def __init__(self, status: int, payload: dict[str, object]) -> None:
            self.status = status
            self.payload = payload

        def getheader(self, name: str) -> None:
            assert name == "NVCF-REQID"
            return None

        def read(self, maximum_bytes: int) -> bytes:
            assert maximum_bytes == 2_000_001
            return json.dumps(self.payload).encode()

    responses = [
        FakeHttpResponse(202, {"requestId": request_id}),
        FakeHttpResponse(200, {"model": "moonshotai/kimi-k3", "choices": [
            {"finish_reason": "stop", "message": {"content": "{}"}}
        ]}),
    ]

    class FakeHttpsConnection:
        def __init__(self, host: str, *, timeout: float) -> None:
            assert host == "integrate.api.nvidia.com"
            assert timeout > 0

        def request(self, method: str, path: str, *, body=None, headers) -> None:
            requests.append((method, path))

        def getresponse(self) -> FakeHttpResponse:
            return responses.pop(0)

        def close(self) -> None:
            pass

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", FakeHttpsConnection)
    monkeypatch.setattr("youtube_intel.distillation.time.sleep", lambda _seconds: None)
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True, provider="nvidia_nim", model="moonshotai/kimi-k3",
            credential_available=True, provider_available=True,
            qualification_input_hash=verified.semantic_hash,
        ),
        credential_resolver=lambda: "synthetic-secret",
    )
    assert transport.generate(verified).raw == "{}"
    assert requests == [
        ("POST", "/v1/chat/completions"),
        ("GET", f"/v1/status/{request_id}"),
    ]
    assert transport.last_response_diagnostics is not None
    assert transport.last_response_diagnostics.http_status == 200


def test_kimi_http_202_without_request_id_is_known_pending_not_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = _verified_input_for_nvidia_nim_test()
    requests: list[str] = []

    class FakeHttpResponse:
        status = 202

        def getheader(self, _name: str) -> None:
            return None

        def read(self, _maximum_bytes: int) -> bytes:
            return b"{}"

    class FakeHttpsConnection:
        def __init__(self, _host: str, *, timeout: float) -> None:
            assert timeout > 0

        def request(self, method: str, _path: str, *, body=None, headers) -> None:
            requests.append(method)

        def getresponse(self) -> FakeHttpResponse:
            return FakeHttpResponse()

        def close(self) -> None:
            pass

    monkeypatch.setattr("youtube_intel.distillation.HTTPSConnection", FakeHttpsConnection)
    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True, provider="nvidia_nim", model="moonshotai/kimi-k3",
            credential_available=True, provider_available=True,
            qualification_input_hash=verified.semantic_hash,
        ),
        credential_resolver=lambda: "synthetic-secret",
    )
    with pytest.raises(KnownCloudDistillationResponseError) as captured:
        transport.generate(verified)
    assert captured.value.reason == "CLOUD_RESULT_PENDING"
    assert requests == ["POST"]
    assert transport.last_response_diagnostics is not None
    assert transport.last_response_diagnostics.http_status == 202


def test_fresh_database_reaches_current_schema_with_integrated_schema(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 31
        migrations = tuple(
            row["name"]
            for row in connection.execute("SELECT name FROM schema_migrations ORDER BY version")
        )
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        connection.close()

    assert migrations[-16:] == (
        "015_add_timed_transcript_evidence_bindings.sql",
        "016_add_ambiguous_resource_ledger_outcome.sql",
        "017_add_current_content_summary.sql",
        "018_add_global_output_language.sql",
        "019_add_evidence_excerpt_stance.sql",
        "020_add_no_new_intelligence_result.sql",
        "021_seal_distillation_output_language.sql",
        "022_bind_current_local_summary.sql",
        "023_add_evidence_translation_presentation.sql",
        "024_bind_current_summary_to_content.sql",
        "025_add_explicit_cloud_execution_audit.sql",
        "026_add_openai_cloud_execution_audit.sql",
        "027_add_moonshot_cloud_execution_audit.sql",
        "028_add_cloud_response_failure_ledger.sql",
        "030_add_deep_analysis_durable_evidence.sql",
        "031_add_research_lite.sql",
    )
    assert "topics" in tables
    with repository._connect() as connection:
        evidence_columns = {
            row["name"] for row in connection.execute('PRAGMA table_info("evidence")')
        }
        relation_columns = {
            row["name"]
            for row in connection.execute(
                'PRAGMA table_info("intelligence_revision_evidence")'
            )
        }
    assert "source_excerpt" in evidence_columns
    assert "stance" in relation_columns


def test_v025_to_v026_preserves_nvidia_consent_known_failure_and_ambiguity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.sqlite3"
    repository = SQLiteStateRepository(path)
    migrations = repository._load_migrations()
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations[:25])
    assert repository.initialize(now=NOW).version == 25

    source_id, ambiguous_video = _source_and_video(repository, "v025-ambiguous-video")
    ambiguous_evidence = _evidence(repository, ambiguous_video)
    ambiguous_service, ambiguous_reservation = _nvidia_qualification_service(
        repository,
        source_id=source_id,
        video_id=ambiguous_video,
        evidence_ids=(ambiguous_evidence,),
        wire_transport=lambda *_args: (_ for _ in ()).throw(RuntimeError("unknown transport")),
    )
    ambiguous_service.authorize_reserved_cloud_execution(
        ambiguous_reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    ambiguous_result = ambiguous_service.continue_qualification_reserved_distillation(
        ambiguous_reservation.execution_id
    )
    assert ambiguous_result.status is DistillationExecutionStatus.AMBIGUOUS

    known_video = "v025-known-response-video"
    _, known_video = _source_and_video(repository, known_video)
    known_evidence = _evidence(repository, known_video)
    known_service, known_reservation = _nvidia_qualification_service(
        repository,
        source_id=source_id,
        video_id=known_video,
        evidence_ids=(known_evidence,),
        wire_transport=lambda *_args: {"choices": [{"message": {"content": "{}"}}]},
    )
    known_service.authorize_reserved_cloud_execution(
        known_reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    known_result = known_service.continue_qualification_reserved_distillation(
        known_reservation.execution_id
    )
    assert known_result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    with repository._connect() as connection:
        consent_before = tuple(tuple(row) for row in connection.execute(
            "SELECT * FROM distillation_cloud_authorizations ORDER BY execution_id"
        ))
        responses_before = tuple(tuple(row) for row in connection.execute(
            "SELECT * FROM distillation_unidentified_http_responses ORDER BY execution_id"
        ))
        history_before = tuple(tuple(row) for row in connection.execute(
            "SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version"
        ))
    assert len(consent_before) == 2
    assert len(responses_before) == 1

    upgraded = SQLiteStateRepository(path)
    monkeypatch.setattr(upgraded, "_load_migrations", lambda: migrations[:26])
    assert upgraded.initialize(now=NOW).version == 26
    assert upgraded.initialize(now=NOW).version == 26
    historical_ambiguous = upgraded.get_distillation_resource_usage(
        ambiguous_reservation.execution_id
    )
    historical_known = upgraded.get_distillation_resource_usage(known_reservation.execution_id)
    assert historical_ambiguous.status == "AMBIGUOUS"
    assert historical_ambiguous.invocation_count == 1
    assert historical_known.status == "REJECTED_OUTPUT"
    assert historical_known.outcome == "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN"
    assert historical_known.invocation_count == 1
    with upgraded._connect() as connection:
        consent_after = tuple(tuple(row) for row in connection.execute(
            "SELECT * FROM distillation_cloud_authorizations ORDER BY execution_id"
        ))
        responses_after = tuple(tuple(row) for row in connection.execute(
            "SELECT * FROM distillation_unidentified_http_responses ORDER BY execution_id"
        ))
        history_after = tuple(tuple(row) for row in connection.execute(
            "SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version"
        ))
        assert connection.execute(
            "SELECT COUNT(*) FROM distillation_openai_cloud_authorizations"
        ).fetchone()[0] == 0
    assert consent_after == consent_before
    assert responses_after == responses_before
    assert history_after[:25] == history_before
    assert len(history_after) == 26


def test_v026_to_v028_preserves_nvidia_and_openai_audit_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.sqlite3"
    repository = SQLiteStateRepository(path)
    migrations = repository._load_migrations()
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations[:26])
    assert repository.initialize(now=NOW).version == 26
    execution_ids: list[str] = []

    def run_nvidia(video_id: str, wire_transport) -> str:
        source_id, video_id = _source_and_video(repository, video_id)
        evidence_id = _evidence(repository, video_id)
        service, reservation = _nvidia_qualification_service(
            repository,
            source_id=source_id,
            video_id=video_id,
            evidence_ids=(evidence_id,),
            wire_transport=wire_transport,
        )
        service.authorize_reserved_cloud_execution(
            reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
        )
        service.continue_qualification_reserved_distillation(reservation.execution_id)
        execution_ids.append(reservation.execution_id)
        return reservation.execution_id

    def run_openai(video_id: str, wire_transport) -> str:
        source_id, video_id = _source_and_video(repository, video_id)
        evidence_id = _evidence(repository, video_id)
        service, reservation, _ = _openai_qualification_service(
            repository,
            source_id=source_id,
            video_id=video_id,
            evidence_ids=(evidence_id,),
            wire_transport=wire_transport,
        )
        service.authorize_reserved_cloud_execution(
            reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
        )
        service.continue_qualification_reserved_distillation(reservation.execution_id)
        execution_ids.append(reservation.execution_id)
        return reservation.execution_id

    nvidia_ambiguous = run_nvidia(
        "v026-nvidia-ambiguous",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("unknown transport")),
    )
    nvidia_known = run_nvidia("v026-nvidia-known", lambda *_args: {})
    openai_ambiguous = run_openai(
        "v026-openai-ambiguous",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("unknown transport")),
    )
    openai_known = run_openai(
        "v026-openai-known",
        lambda *_args: {
            "object": "response",
            "status": "completed",
            "model": "gpt-4.1",
            "output": [],
            "usage": {"input_tokens": 44, "output_tokens": 8},
        },
    )
    expected = {
        nvidia_ambiguous: "AMBIGUOUS",
        nvidia_known: "REJECTED_OUTPUT",
        openai_ambiguous: "AMBIGUOUS",
        openai_known: "REJECTED_OUTPUT",
    }
    historical_resource_columns = (
        "execution_id, reason, use_case, source_id, video_id, intelligence_id, "
        "revision_id, selected_provider, selected_model, actual_provider, "
        "actual_model, status, invocation_count, input_tokens, output_tokens, "
        "cost_microunits, duration_ms, budget_state, outcome, created_at"
    )
    with repository._connect() as connection:
        old_history = tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT version, name, checksum, applied_at "
                "FROM schema_migrations ORDER BY version"
            )
        )
        old_nvidia_consents = tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM distillation_cloud_authorizations ORDER BY execution_id"
            )
        )
        old_nvidia_responses = tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM distillation_unidentified_http_responses ORDER BY execution_id"
            )
        )
        old_openai_consents = tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM distillation_openai_cloud_authorizations ORDER BY execution_id"
            )
        )
        old_openai_responses = tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM distillation_openai_unidentified_http_responses ORDER BY execution_id"
            )
        )
        old_resource_rows = tuple(
            tuple(row)
            for row in connection.execute(
                f"SELECT {historical_resource_columns} FROM distillation_resource_usage "
                "WHERE execution_id IN (?, ?, ?, ?) ORDER BY execution_id",
                tuple(execution_ids),
            )
        )

    upgraded = SQLiteStateRepository(path)
    assert upgraded.initialize(now=NOW).version == 31
    assert upgraded.initialize(now=NOW).version == 31
    with upgraded._connect() as connection:
        assert tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT version, name, checksum, applied_at "
                "FROM schema_migrations ORDER BY version LIMIT 26"
            )
        ) == old_history
        assert tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM distillation_cloud_authorizations ORDER BY execution_id"
            )
        ) == old_nvidia_consents
        assert tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM distillation_unidentified_http_responses ORDER BY execution_id"
            )
        ) == old_nvidia_responses
        assert tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM distillation_openai_cloud_authorizations ORDER BY execution_id"
            )
        ) == old_openai_consents
        assert tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM distillation_openai_unidentified_http_responses ORDER BY execution_id"
            )
        ) == old_openai_responses
        assert tuple(
            tuple(row)
            for row in connection.execute(
                f"SELECT {historical_resource_columns} FROM distillation_resource_usage "
                "WHERE execution_id IN (?, ?, ?, ?) ORDER BY execution_id",
                tuple(execution_ids),
            )
        ) == old_resource_rows
        assert all(
            row[0] is None
            for row in connection.execute(
                "SELECT http_status_code FROM distillation_resource_usage "
                "WHERE execution_id IN (?, ?, ?, ?) ORDER BY execution_id",
                tuple(execution_ids),
            )
        )
    usage_after = {
        execution_id: upgraded.get_distillation_resource_usage(execution_id)
        for execution_id in execution_ids
    }
    for execution_id, status in expected.items():
        assert usage_after[execution_id].status == status
    assert usage_after[nvidia_ambiguous].outcome == "TRANSPORT_OUTCOME_UNKNOWN"
    assert usage_after[nvidia_known].outcome == "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN"
    assert usage_after[openai_ambiguous].outcome == "TRANSPORT_OUTCOME_UNKNOWN"
    assert usage_after[openai_known].outcome == "CLOUD_HTTP_RESPONSE_INVALID"


def test_v009_upgrade_preserves_existing_product_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "state.sqlite3"
    legacy = SQLiteStateRepository(path)
    migrations = legacy._load_migrations()
    monkeypatch.setattr(legacy, "_load_migrations", lambda: migrations[:9])
    assert legacy.initialize(now=NOW).version == 9
    source_id, _ = _source_and_video(legacy)
    preference = PreferenceApplicationService(legacy, now=lambda: NOW).set_explicit_long_term(
        command_id="preserved-preference",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Keep explicit user intent.",
    )
    legacy.create_intelligence(intelligence_id="preserved-intelligence", now=NOW)
    monkeypatch.undo()

    upgraded = SQLiteStateRepository(path)
    assert upgraded.initialize(now=NOW).version == 31
    assert upgraded.get_source_subscription(source_id) is not None
    assert upgraded.get_preference(preference.preference_id) == preference
    assert upgraded.get_intelligence("preserved-intelligence") is not None


def test_v015_upgrade_preserves_ledger_rows_constraints_and_immutability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.sqlite3"
    legacy = SQLiteStateRepository(path)
    migrations = legacy._load_migrations()
    monkeypatch.setattr(legacy, "_load_migrations", lambda: migrations[:15])
    assert legacy.initialize(now=NOW).version == 15
    source_id, video_id = _source_and_video(legacy)
    execution_id = "exec-v015-ledger"
    legacy.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id=execution_id,
            source_id=source_id,
            video_id=video_id,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="test-transport",
            selected_model="deterministic-v1",
        ),
        now=NOW,
    )
    legacy.finish_distillation_without_admission(
        execution_id=execution_id,
        status="WAITING_MODEL",
        budget_state="MODEL_UNAVAILABLE",
        outcome="MODEL_UNAVAILABLE",
        invocation_count=0,
        actual_provider=None,
        actual_model=None,
        input_tokens=None,
        output_tokens=None,
        cost_microunits=None,
        duration_ms=None,
        now=NOW,
    )
    connection = legacy._connect()
    try:
        historical_columns = tuple(
            str(row[1]) for row in connection.execute("PRAGMA table_info(distillation_resource_usage)")
        )
        before_row = tuple(
            connection.execute(
                "SELECT * FROM distillation_resource_usage WHERE execution_id = ?", (execution_id,)
            ).fetchone()
        )
        before_indexes = tuple(
            tuple(row) for row in connection.execute("PRAGMA index_list(distillation_resource_usage)")
        )
        before_foreign_keys = tuple(
            tuple(row) for row in connection.execute("PRAGMA foreign_key_list(distillation_resource_usage)")
        )
    finally:
        connection.close()
    monkeypatch.undo()

    upgraded = SQLiteStateRepository(path)
    assert upgraded.initialize(now=NOW).version == 31
    connection = upgraded._connect()
    try:
        after_row = tuple(
            connection.execute(
                f"SELECT {', '.join(historical_columns)} "
                "FROM distillation_resource_usage WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        )
        assert before_row == after_row
        assert connection.execute(
            "SELECT http_status_code FROM distillation_resource_usage WHERE execution_id = ?",
            (execution_id,),
        ).fetchone()[0] is None
        assert before_indexes == tuple(
            tuple(row) for row in connection.execute("PRAGMA index_list(distillation_resource_usage)")
        )
        assert before_foreign_keys == tuple(
            tuple(row) for row in connection.execute("PRAGMA foreign_key_list(distillation_resource_usage)")
        )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE distillation_resource_usage SET outcome = 'FORGED' WHERE execution_id = ?",
                (execution_id,),
            )
    finally:
        connection.close()


def test_ledger_sql_rejects_unknown_status_and_nonambiguous_unknown_identity(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    for execution_id in ("exec-unknown-status", "exec-unknown-identity"):
        repository.begin_distillation_execution(
            DistillationExecutionWrite(
                execution_id=execution_id,
                source_id=source_id,
                video_id=video_id,
                reason="MANUAL_PERSONALIZED_DISTILLATION",
                use_case="PERSONALIZED_INTELLIGENCE",
                selected_provider="test-transport",
                selected_model="deterministic-v1",
            ),
            now=NOW,
        )
    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO distillation_resource_usage "
                "(execution_id, reason, use_case, source_id, video_id, selected_provider, "
                "selected_model, status, invocation_count, budget_state, outcome, created_at) "
                "VALUES (?, 'reason', 'use-case', ?, ?, 'test-transport', 'deterministic-v1', "
                "'ARBITRARY', 0, 'UNKNOWN', 'UNKNOWN', ?)",
                ("exec-unknown-status", source_id, video_id, "2026-09-07T09:00:00.000000Z"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO distillation_resource_usage "
                "(execution_id, reason, use_case, source_id, video_id, selected_provider, "
                "selected_model, status, invocation_count, budget_state, outcome, created_at) "
                "VALUES (?, 'reason', 'use-case', ?, ?, 'test-transport', 'deterministic-v1', "
                "'REJECTED_OUTPUT', 1, 'UNKNOWN', 'UNKNOWN', ?)",
                ("exec-unknown-identity", source_id, video_id, "2026-09-07T09:00:00.000000Z"),
            )
    finally:
        connection.close()


def test_v018_legacy_null_stance_keeps_old_card_hash_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "legacy-v18.sqlite3"
    legacy = SQLiteStateRepository(path)
    migrations = legacy._load_migrations()
    monkeypatch.setattr(legacy, "_load_migrations", lambda: migrations[:18])
    assert legacy.initialize(now=NOW).version == 18
    source_id, video_id = _source_and_video(legacy)

    artifact_id = "legacy-artifact-v18"
    evidence_id = build_evidence_id(
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=1_000,
        end_ms=1_500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    with legacy._connect() as connection:
        connection.execute(
            "INSERT INTO artifacts "
            "(artifact_id, artifact_key, video_id, job_id, kind, storage_root, "
            "relative_path, content_hash, provider, model, producer_version, "
            "retention_class, created_at, expires_at, deleted_at) "
            "VALUES (?, ?, ?, NULL, 'transcript_canonical', 'DATA', ?, ?, "
            "NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            (
                artifact_id,
                "legacy-artifact-key-v18",
                video_id,
                "legacy-v18.txt",
                "a" * 64,
                "2026-09-07T09:00:00Z",
            ),
        )
        connection.execute(
            "INSERT INTO evidence "
            "(evidence_id, video_id, artifact_id, start_ms, end_ms, lineage_kind, "
            "role, language, availability, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'ORIGINAL_TRANSCRIPT', 'PRIMARY_ORIGINAL', "
            "'en', 'AVAILABLE', ?)",
            (
                evidence_id,
                video_id,
                artifact_id,
                1_000,
                1_500,
                "2026-09-07T09:00:00Z",
            ),
        )

    payload = {
        "core_conclusion": "Legacy card remains readable after M4C migration.",
        "user_relevant_information": ["Legacy authority is preserved."],
        "important_new_information": [],
        "meaningful_details": [],
        "filtered_noise": [],
        "claim_kind": IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT.value,
        "evidence": [
            {
                "evidence_id": evidence_id,
                "start_ms": 1_000,
                "end_ms": 1_500,
            }
        ],
    }
    content_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    legacy.create_intelligence(intelligence_id="legacy-intel-v18", now=NOW)
    legacy.append_intelligence_revision(
        intelligence_id="legacy-intel-v18",
        revision=IntelligenceRevisionWrite(
            revision_id="legacy-revision-v18",
            interpretation_kind=IntelligenceInterpretationKind.DISTILLATION,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash=content_hash,
            state=IntelligenceState.NEW,
            reason="LEGACY_DISTILLATION_ADMITTED",
            evidence_ids=(evidence_id,),
        ),
        now=NOW,
    )
    with legacy._connect() as connection:
        connection.execute(
            "INSERT INTO dependency_edges "
            "(edge_id, dependent_revision_id, relation, input_evidence_id, "
            "input_revision_id, created_at) "
            "VALUES (?, ?, 'EVIDENCE_SUPPORT', ?, NULL, ?)",
            (
                "legacy-support-edge-v18",
                "legacy-revision-v18",
                evidence_id,
                "2026-09-07T09:00:00Z",
            ),
        )
        connection.execute(
            "INSERT INTO distillation_cards "
            "(revision_id, source_id, video_id, core_conclusion, "
            "user_relevant_information_json, important_new_information_json, "
            "meaningful_details_json, filtered_noise_json, preference_ids_json, "
            "source_policy_revision_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
            (
                "legacy-revision-v18",
                source_id,
                video_id,
                payload["core_conclusion"],
                json.dumps(payload["user_relevant_information"], separators=(",", ":")),
                json.dumps(payload["important_new_information"], separators=(",", ":")),
                json.dumps(payload["meaningful_details"], separators=(",", ":")),
                json.dumps(payload["filtered_noise"], separators=(",", ":")),
                "[]",
                "2026-09-07T09:00:00Z",
            ),
        )

    monkeypatch.undo()
    upgraded = SQLiteStateRepository(path)
    assert upgraded.initialize(now=NOW).version == 31
    relations = upgraded.list_intelligence_revision_evidence_relations(
        "legacy-revision-v18"
    )
    assert len(relations) == 1
    assert relations[0].stance is None
    assert upgraded.get_evidence(evidence_id).source_excerpt is None
    card = AuthoritativeIntelligenceReader(upgraded).read_current_card(
        "legacy-intel-v18"
    )
    assert card.core_conclusion == payload["core_conclusion"]


def test_generic_evidence_write_rejects_unverified_source_excerpt(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    _, video_id = _source_and_video(repository)
    with pytest.raises(ValueError, match="trusted capture path"):
        _evidence(
            repository,
            video_id,
            source_excerpt="Caller-provided text must not become source truth.",
        )
    assert repository.list_available_canonical_evidence_ids(video_id) == ()


def test_repository_admission_requires_supporting_evidence_independently(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id="direct-admit-no-support",
            source_id=source_id,
            video_id=video_id,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="test-transport",
            selected_model="deterministic-v1",
        ),
        now=NOW,
    )
    with pytest.raises(ValueError, match="at least one supporting Evidence"):
        repository.admit_distillation(
            execution_id="direct-admit-no-support",
            intelligence_id="intel-direct-no-support",
            revision_id="revision-direct-no-support",
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash="b" * 64,
            evidence_ids=(evidence_id,),
            evidence_stances=((evidence_id, EvidenceStance.CONTRADICTING),),
            card=DistillationCardWrite(
                source_id=source_id,
                video_id=video_id,
                core_conclusion="This must not be admitted without supporting Evidence.",
                user_relevant_information=("No supporting relation exists.",),
                important_new_information=(),
                meaningful_details=(),
                filtered_noise=(),
                preference_ids=(),
                source_policy_revision_id=None,
            ),
            actual_provider="test-transport",
            actual_model="deterministic-v1",
            input_tokens=1,
            output_tokens=1,
            cost_microunits=0,
            duration_ms=1,
            now=NOW,
        )
    assert repository.list_current_intelligence_ids() == ()


def test_m019_constraints_keep_excerpt_and_relation_immutable(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    first_evidence = _evidence(repository, video_id)
    second_evidence = _evidence(repository, video_id, start_ms=2_000, end_ms=2_500)
    result = _service(repository, _FakeTransport(_raw(first_evidence))).distill(
        _command(source_id, video_id, first_evidence)
    )
    card = AuthoritativeIntelligenceReader(repository).read_current_card(
        result.intelligence_id or ""
    )
    with repository._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="source excerpt is immutable"):
            connection.execute(
                "UPDATE evidence SET source_excerpt = ? WHERE evidence_id = ?",
                ("Unverified mutation", first_evidence),
            )
        with pytest.raises(sqlite3.IntegrityError, match="revision evidence links are immutable"):
            connection.execute(
                "UPDATE intelligence_revision_evidence SET stance = ? "
                "WHERE revision_id = ? AND evidence_id = ?",
                ("conditional", card.verified.revision_id, first_evidence),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO intelligence_revision_evidence "
                "(revision_id, evidence_id, stance) VALUES (?, ?, ?)",
                (card.verified.revision_id, second_evidence, "unknown"),
            )


def test_mixed_legacy_and_new_stance_fails_closed(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    first_evidence = _evidence(repository, video_id)
    second_evidence = _evidence(repository, video_id, start_ms=2_000, end_ms=2_500)
    raw = json.loads(_raw(first_evidence))
    raw["evidence"].append(
        {
            "evidence_id": second_evidence,
            "start_ms": 2_000,
            "end_ms": 2_500,
            "stance": "supporting",
        }
    )
    command = _command(source_id, video_id, first_evidence)
    command = replace(command, evidence_ids=(first_evidence, second_evidence))
    result = _service(repository, _FakeTransport(json.dumps(raw))).distill(command)
    assert result.revision_id is not None
    with repository._connect() as connection:
        connection.execute("DROP TRIGGER revision_evidence_immutable_update")
        connection.execute(
            "UPDATE intelligence_revision_evidence SET stance = NULL "
            "WHERE revision_id = ? AND evidence_id = ?",
            (result.revision_id, second_evidence),
        )
    with pytest.raises(IntelligenceReadRejected, match="stance is incomplete"):
        AuthoritativeIntelligenceReader(repository).read_current_card(
            result.intelligence_id or ""
        )


@pytest.mark.parametrize("stance", ("contradicting", "conditional"))
def test_distillation_requires_at_least_one_supporting_evidence(
    tmp_path: Path, stance: str
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    result = _service(repository, _FakeTransport(_raw(evidence_id, stance=stance))).distill(
        _command(source_id, video_id, evidence_id)
    )
    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert result.intelligence_id is None
    assert repository.list_current_intelligence_ids() == ()


def test_distillation_rejects_non_product_evidence_stance(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    result = _service(repository, _FakeTransport(_raw(evidence_id, stance="unknown"))).distill(
        _command(source_id, video_id, evidence_id)
    )
    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert result.intelligence_id is None
    assert repository.list_current_intelligence_ids() == ()


def test_personalization_projection_is_active_only_and_never_mutates_source_policy(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    preferences = PreferenceApplicationService(repository, now=lambda: NOW)
    preferences.set_explicit_long_term(
        command_id="long", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="Long term."
    )
    preferences.record_derived_recent(
        command_id="recent", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="Recent."
    )
    preferences.set_temporary_focus(
        command_id="temporary", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="Temporary.", expires_at=NOW + timedelta(days=1)
    )
    PreferenceApplicationService(repository, now=lambda: NOW - timedelta(days=2)).set_temporary_focus(
        command_id="expired", scope=PreferenceScope.GLOBAL_CONTENT, target_id=None, statement="Expired.", expires_at=NOW - timedelta(days=1)
    )
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    before = policy.effective_policy(source_id)
    transport = _FakeTransport(_raw(evidence_id))

    result = _service(repository, transport).distill(_command(source_id, video_id, evidence_id))

    assert result.status is DistillationExecutionStatus.SUCCEEDED
    assert transport.calls == 1
    assert transport.commands[0].personalization == (
        "Long term.",
        "Recent.",
        "Temporary.",
    )
    assert transport.commands[0].source_focus_rules == ("AI Agent",)
    assert transport.commands[0].source_ignore_rules == ()
    assert transport.commands[0].distillation_style == DistillationStyle.BALANCED.value
    assert policy.effective_policy(source_id) == before
    card = AuthoritativeIntelligenceReader(repository).read_current_card(result.intelligence_id or "")
    assert card.core_conclusion.startswith("The release")
    assert card.verified.claim_kind is IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT
    assert card.verified.is_confirmed is False


def test_feedback_derived_preference_changes_a_later_distillation_request_only(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, first_video_id = _source_and_video(repository)
    first_evidence_id = _evidence(repository, first_video_id)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    before = policy.effective_policy(source_id)

    first_transport = _FakeTransport(_raw(first_evidence_id))
    assert _service(repository, first_transport).distill(
        _command(source_id, first_video_id, first_evidence_id, execution_id="feedback-run-a")
    ).status is DistillationExecutionStatus.SUCCEEDED
    assert first_transport.commands[0].personalization == ()

    preferences = PreferenceApplicationService(repository, now=lambda: NOW)
    feedback = preferences.record_feedback(
        FeedbackWrite(
            feedback_id="feedback-product-evidence",
            kind=FeedbackKind.IMPORTANT,
            scope=PreferenceScope.GLOBAL_CONTENT,
            target_id=None,
            content=None,
            correction_kind=None,
        )
    )
    preferences.record_derived_recent(
        command_id="derive-product-evidence",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Emphasize evidence-led product execution detail.",
    )

    later_video_id = "video-022-feedback-later"
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=later_video_id,
            channel_id="UC______________________",
            channel_name="Fixture channel",
            title="AI Agent evidence update",
            description="Developer tools and product cases.",
            source_url=f"https://www.youtube.com/watch?v={later_video_id}",
            published_at=NOW + timedelta(minutes=1),
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    repository.link_source_video(source_id, later_video_id, discovered_at=NOW)
    policy.evaluate_and_record_stage_one(
        source_id,
        MetadataFilterCandidate(
            video_id=later_video_id,
            title="AI Agent evidence update",
            description="Developer tools and product cases.",
            channel_name="Fixture channel",
            published_at=NOW + timedelta(minutes=1),
            video_type=VideoType.STANDARD,
        ),
    )
    later_evidence_id = _evidence(repository, later_video_id)
    later_transport = _FakeTransport(_raw(later_evidence_id))

    assert _service(repository, later_transport).distill(
        _command(source_id, later_video_id, later_evidence_id, execution_id="feedback-run-b")
    ).status is DistillationExecutionStatus.SUCCEEDED
    assert repository.list_feedback() == (feedback,)
    assert later_transport.commands[0].personalization == (
        "Emphasize evidence-led product execution detail.",
    )
    assert policy.effective_policy(source_id) == before


@pytest.mark.parametrize(
    "claim_kind",
    (
        IntelligenceClaimKind.FACT,
        IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
        IntelligenceClaimKind.OPINION,
        IntelligenceClaimKind.PREDICTION,
        IntelligenceClaimKind.RUMOR,
        IntelligenceClaimKind.SYSTEM_INFERENCE,
    ),
)
def test_valid_finite_claim_kinds_are_preserved_without_lifecycle_inference(
    tmp_path: Path, claim_kind: IntelligenceClaimKind
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)

    result = _service(repository, _FakeTransport(_raw(evidence_id, claim_kind=claim_kind))).distill(
        _command(source_id, video_id, evidence_id, execution_id=f"exec-{claim_kind.value}")
    )

    verified = AuthoritativeIntelligenceReader(repository).read_current(result.intelligence_id or "")
    assert verified.claim_kind is claim_kind
    assert verified.is_confirmed is False


@pytest.mark.parametrize(
    "raw",
    (
        "{not-json",
        json.dumps({"core_conclusion": "partial"}),
        json.dumps(
            {
                "core_conclusion": "x",
                "user_relevant_information": [],
                "important_new_information": [],
                "meaningful_details": [],
                "filtered_noise": [],
                "claim_kind": "UNCLASSIFIED",
                "evidence": [],
            }
        ),
    ),
)
def test_malformed_or_unclassified_output_fails_closed_without_repair_or_retry(tmp_path: Path, raw: str) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _FakeTransport(raw)

    result = _service(repository, transport).distill(_command(source_id, video_id, evidence_id))

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert transport.calls == 1
    assert result.intelligence_id is None
    assert repository.list_distillation_cards() == ()


@pytest.mark.parametrize(
    "raw",
    (
        "```json\n{}\n```",
        json.dumps(
            {
                **json.loads(_raw("evidence-id")),
                "generated_text_as_evidence": "the model said so",
            }
        ),
    ),
)
def test_fenced_or_generated_text_evidence_is_not_repaired_or_admitted(
    tmp_path: Path, raw: str
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    if "generated_text_as_evidence" in raw:
        raw = raw.replace("evidence-id", evidence_id)
    transport = _FakeTransport(raw)

    result = _service(repository, transport).distill(_command(source_id, video_id, evidence_id))

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert transport.calls == 1
    assert repository.list_distillation_cards() == ()


def test_missing_or_foreign_requested_evidence_is_rejected_before_transport(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    raw_without_evidence = json.loads(_raw(evidence_id))
    raw_without_evidence["evidence"] = []
    missing_support = _FakeTransport(json.dumps(raw_without_evidence))
    result = _service(repository, missing_support).distill(
        _command(source_id, video_id, evidence_id)
    )
    foreign_requested = _FakeTransport(_raw(evidence_id))

    foreign_result = _service(repository, foreign_requested).distill(
        _command(source_id, video_id, "not-an-evidence", execution_id="foreign-request")
    )

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert missing_support.calls == 1
    assert foreign_result.status is DistillationExecutionStatus.REJECTED_EVIDENCE
    assert foreign_requested.calls == 0


def test_unbounded_evidence_request_is_rejected_before_transport(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_ids = tuple(
        _evidence(
            repository,
            video_id,
            start_ms=1_000 + index * 1_000,
            end_ms=1_500 + index * 1_000,
        )
        for index in range(21)
    )
    transport = _FakeTransport("{}")
    command = _command(source_id, video_id, evidence_ids[0])
    command = DistillationCommand(
        execution_id=command.execution_id,
        source_id=command.source_id,
        video_id=command.video_id,
        evidence_ids=evidence_ids,
        reason=command.reason,
        use_case=command.use_case,
        selected_provider=command.selected_provider,
        selected_model=command.selected_model,
        output_language=command.output_language,
    )

    result = _service(repository, transport).distill(command)

    assert result.status is DistillationExecutionStatus.REJECTED_EVIDENCE
    assert transport.calls == 0


def test_foreign_or_hallucinated_evidence_is_rejected_and_cannot_be_admitted(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    other_video = "foreign-022"
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=other_video,
            channel_id="UC_OTHER", channel_name="Other", title="Other", description="Other",
            source_url=f"https://www.youtube.com/watch?v={other_video}", published_at=NOW,
            duration_seconds=60, default_language="en", available_languages=("en",),
            live_status=LiveStatus.NONE, availability=Availability.PUBLIC,
        ), pipeline_version="fixture-v1", now=NOW,
    )
    foreign_evidence = _evidence(repository, other_video)

    foreign = _service(repository, _FakeTransport(_raw(foreign_evidence))).distill(
        _command(source_id, video_id, evidence_id)
    )
    hallucinated = _service(repository, _FakeTransport(_raw(evidence_id, end_ms=1_499))).distill(
        _command(source_id, video_id, evidence_id, execution_id="exec-timestamp")
    )

    assert foreign.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert hallucinated.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert repository.list_distillation_cards() == ()


def test_multiple_evidence_stances_are_canonicalized_and_supporting_anchors_state(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_ids = (
        _evidence(repository, video_id),
        _evidence(repository, video_id, start_ms=2_000, end_ms=2_500),
        _evidence(repository, video_id, start_ms=3_000, end_ms=3_500),
    )
    ordered = tuple(sorted(evidence_ids))
    stance_by_id = {
        ordered[0]: "contradicting",
        ordered[1]: "conditional",
        ordered[2]: "supporting",
    }
    raw = json.loads(_raw(ordered[2]))
    raw["evidence"] = [
        {
            "evidence_id": evidence_id,
            "start_ms": repository.get_evidence(evidence_id).start_ms,
            "end_ms": repository.get_evidence(evidence_id).end_ms,
            "stance": stance_by_id[evidence_id],
        }
        for evidence_id in reversed(ordered)
    ]
    command = replace(
        _command(source_id, video_id, ordered[0]),
        evidence_ids=evidence_ids,
    )

    result = _service(repository, _FakeTransport(json.dumps(raw))).distill(command)
    card = AuthoritativeIntelligenceReader(repository).read_current_card(
        result.intelligence_id or ""
    )

    assert result.status is DistillationExecutionStatus.SUCCEEDED
    assert card.verified.evidence_ids == ordered
    relations = repository.list_intelligence_revision_evidence_relations(
        card.verified.revision_id
    )
    assert {
        item.evidence_id: item.stance.value
        for item in relations
        if item.stance is not None
    } == stance_by_id
    history = repository.list_intelligence_state_history(
        card.verified.intelligence_id
    )
    state_event = next(
        item for item in history if item.revision_id == card.verified.revision_id
    )
    assert state_event.evidence_id == ordered[2]
    dependency_edges = repository.list_dependency_edges_for_revision(
        card.verified.revision_id
    )
    assert {
        edge.input_evidence_id
        for edge in dependency_edges
        if edge.relation.value == "EVIDENCE_SUPPORT"
    } == set(ordered)


def test_admitted_subset_preserves_complete_candidate_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    candidates = tuple(
        _evidence(repository, video_id, start_ms=start, end_ms=start + 500)
        for start in (1_000, 2_000, 3_000, 4_000)
    )
    raw = json.loads(_raw(candidates[0]))
    raw["evidence"] = [
        {"evidence_id": candidates[0], "start_ms": 1_000, "end_ms": 1_500, "stance": "supporting"},
        {"evidence_id": candidates[2], "start_ms": 3_000, "end_ms": 3_500, "stance": "conditional"},
    ]
    command = replace(
        _command(source_id, video_id, candidates[0], execution_id="exec-subset"),
        evidence_ids=candidates,
    )

    result = _service(repository, _FakeTransport(json.dumps(raw))).distill(command)

    assert result.status is DistillationExecutionStatus.SUCCEEDED
    assert result.revision_id is not None
    relations = repository.list_intelligence_revision_evidence_relations(result.revision_id)
    assert {item.evidence_id: item.stance for item in relations} == {
        candidates[0]: EvidenceStance.SUPPORTING,
        candidates[2]: EvidenceStance.CONDITIONAL,
    }
    edges = repository.list_dependency_edges_for_revision(result.revision_id)
    assert {edge.input_evidence_id for edge in edges} == {candidates[0], candidates[2]}
    reservation = PersonalizedDistillationService._reservation_id(
        source_id=source_id, video_id=video_id, evidence_ids=tuple(sorted(candidates)),
        selected_provider="ollama", selected_model="qwen3:8b",
        output_language="zh-CN", verified_input_hash="a" * 64,
    )
    cited_only = PersonalizedDistillationService._reservation_id(
        source_id=source_id, video_id=video_id,
        evidence_ids=tuple(sorted((candidates[0], candidates[2]))),
        selected_provider="ollama", selected_model="qwen3:8b",
        output_language="zh-CN", verified_input_hash="a" * 64,
    )
    assert reservation != cited_only
    monkeypatch.setattr(
        "youtube_intel.distillation.OllamaLocalDistillationTransport._PROMPT_VERSION",
        "local-distillation-admission-v3",
    )
    changed_prompt = PersonalizedDistillationService._reservation_id(
        source_id=source_id, video_id=video_id, evidence_ids=tuple(sorted(candidates)),
        selected_provider="ollama", selected_model="qwen3:8b",
        output_language="zh-CN", verified_input_hash="a" * 64,
    )
    assert changed_prompt != reservation


@pytest.mark.parametrize(
    "bad_evidence",
    [
        [],
        [{"evidence_id": "foreign", "start_ms": 1_000, "end_ms": 1_500, "stance": "supporting"}],
        [{"evidence_id": "first", "start_ms": 1_000, "end_ms": 1_500, "stance": "conditional"}],
        [
            {"evidence_id": "first", "start_ms": 1_000, "end_ms": 1_500, "stance": "supporting"},
            {"evidence_id": "first", "start_ms": 1_000, "end_ms": 1_500, "stance": "supporting"},
        ],
        [{"evidence_id": "first", "start_ms": 1_001, "end_ms": 1_500, "stance": "supporting"}],
    ],
    ids=["empty", "foreign", "no-support", "duplicate", "wrong-timestamp"],
)
def test_admitted_subset_rejects_invalid_citations(
    tmp_path: Path, bad_evidence: list[dict[str, object]]
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    first = _evidence(repository, video_id)
    second = _evidence(repository, video_id, start_ms=2_000, end_ms=2_500)
    raw = json.loads(_raw(first))
    raw["evidence"] = [
        {**item, "evidence_id": first if item["evidence_id"] == "first" else item["evidence_id"]}
        for item in bad_evidence
    ]
    command = replace(_command(source_id, video_id, first), evidence_ids=(first, second))

    result = _service(repository, _FakeTransport(json.dumps(raw))).distill(command)

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert repository.list_current_intelligence_ids() == ()


def test_positive_zero_rejects_candidate_subset(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    first = _evidence(repository, video_id)
    second = _evidence(repository, video_id, start_ms=2_000, end_ms=2_500)
    command = replace(_command(source_id, video_id, first), evidence_ids=(first, second))

    result = _service(repository, _FakeTransport(_no_new_raw(first))).distill(command)

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert repository.list_current_intelligence_ids() == ()


def test_normal_skip_is_not_eligible_and_manual_override_still_cannot_bypass_budget(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    policy.update_global(
        command_id="skip", initial_history_count=5, per_run_max_new_videos=5,
        focus_rules=(), ignore_rules=("advertisement",), distillation_style=policy.global_policy().distillation_style,
    )
    policy.evaluate_and_record_stage_one(
        source_id,
        MetadataFilterCandidate(video_id=video_id, title="Advertisement", description="", channel_name="Fixture channel", published_at=NOW, video_type=VideoType.STANDARD),
    )
    transport = _FakeTransport(_raw(evidence_id))

    skipped = _service(repository, transport).distill(_command(source_id, video_id, evidence_id))
    policy_before_override = policy.effective_policy(source_id)
    policy.manual_analyze_override(source_id=source_id, video_id=video_id, command_id="manual")
    same_execution = _service(repository, transport).distill(
        _command(source_id, video_id, evidence_id)
    )
    budget_blocked = _service(repository, transport, _FakeBudget(False, state="EXHAUSTED")).distill(
        _command(source_id, video_id, evidence_id, execution_id="exec-manual")
    )

    assert skipped.status is DistillationExecutionStatus.REJECTED_INELIGIBLE
    assert same_execution == skipped
    assert budget_blocked.status is DistillationExecutionStatus.WAITING_BUDGET
    assert transport.calls == 0
    assert budget_blocked.invocation_count == 0
    assert policy.effective_policy(source_id) == policy_before_override


def test_model_wait_unknown_usage_and_completed_reuse_are_truthful(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    unavailable = _FakeTransport(_raw(evidence_id), available=False)
    waiting = _service(repository, unavailable).distill(_command(source_id, video_id, evidence_id))
    transport = _FakeTransport(
        _raw(evidence_id), input_tokens=None, output_tokens=None, cost_microunits=None, duration_ms=None
    )
    service = _service(repository, transport)
    first = service.distill(_command(source_id, video_id, evidence_id, execution_id="exec-complete"))
    second = service.distill(_command(source_id, video_id, evidence_id, execution_id="exec-complete"))

    assert waiting.status is DistillationExecutionStatus.WAITING_MODEL
    assert unavailable.calls == 0
    assert first.status is DistillationExecutionStatus.SUCCEEDED
    assert second == first
    assert transport.calls == 1
    ledger = repository.get_distillation_resource_usage("exec-complete")
    assert ledger.actual_provider == "test-transport"
    assert ledger.actual_model == "deterministic-v1"
    assert ledger.input_tokens is None and ledger.output_tokens is None and ledger.cost_microunits is None


def test_actual_model_mismatch_is_recorded_without_fallback_or_admission(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _FakeTransport(_raw(evidence_id), actual_model="test-model-b")
    command = _command(source_id, video_id, evidence_id)

    result = _service(repository, transport).distill(command)

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert transport.calls == 1
    ledger = repository.get_distillation_resource_usage(command.execution_id)
    assert ledger.selected_model == "deterministic-v1"
    assert ledger.actual_model == "test-model-b"
    assert ledger.input_tokens == 120 and ledger.output_tokens == 45
    assert ledger.cost_microunits == 7 and ledger.duration_ms == 8


def test_service_rejects_non_offline_transport_before_any_execution(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    transport = _FakeTransport("{}")
    transport.is_offline_test_transport = False

    with pytest.raises(ValueError, match="transport kind is not legal"):
        _service(repository, transport)
    assert transport.calls == 0


def test_ambiguous_transport_outcome_is_not_automatically_retried(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    transport = _RaisingTransport(_raw(evidence_id))
    service = _service(repository, transport)
    command = _command(source_id, video_id, evidence_id)

    first = service.distill(command)
    second = service.distill(command)

    assert first.status is DistillationExecutionStatus.AMBIGUOUS
    assert second == first
    assert transport.calls == 1
    ledger = repository.get_distillation_resource_usage(command.execution_id)
    assert ledger.outcome == "TRANSPORT_OUTCOME_UNKNOWN"
    assert ledger.actual_provider is None
    assert ledger.actual_model is None
    assert ledger.cost_microunits is None


def test_nvidia_nim_qualification_timeout_is_terminal_without_redispatch(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    command = _nvidia_nim_command(
        source_id, video_id, evidence_id, execution_id="nvidia-timeout"
    )
    projection_service = _service(repository, _FakeTransport("{}"))
    verified = projection_service._compose_verified_input(
        projection_service._projection(command)
    )
    calls: list[tuple[float, int]] = []

    def wire_transport(endpoint, request, credential, timeout, retries):
        calls.append((timeout, retries))
        raise TimeoutError("synthetic timeout")

    transport = NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="nvidia_nim",
            model="moonshotai/kimi-k3",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=verified.semantic_hash,
            qualification_max_calls=1,
            qualification_response_wait_timeout_seconds=300,
        ),
        credential_resolver=lambda: "synthetic-nvidia-credential",
        wire_transport=wire_transport,
    )
    service = PersonalizedDistillationService(
        repository,
        SourcePolicyApplicationService(repository, now=lambda: NOW),
        transport,
        _FakeBudget(True),
        now=lambda: NOW,
    )

    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    first = service.continue_qualification_reserved_distillation(reservation.execution_id)
    second = service.continue_qualification_reserved_distillation(reservation.execution_id)

    assert first.status is DistillationExecutionStatus.AMBIGUOUS
    assert second == first
    assert calls == [(300.0, 0)]
    ledger = repository.get_distillation_resource_usage(reservation.execution_id)
    assert ledger.invocation_count == 1
    assert ledger.outcome == "TRANSPORT_OUTCOME_UNKNOWN"


def test_cloud_dispatch_requires_one_matching_persisted_consent(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    calls = 0

    def wire(*_args):
        nonlocal calls
        calls += 1
        return {}

    transport = NvidiaNimCloudDistillationTransport(
        authorization=_normal_nvidia_authorization(),
        credential_resolver=lambda: "synthetic-test-credential",
        wire_transport=wire,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    with pytest.raises(CloudConsentRequiredError):
        service.continue_reserved_distillation(reservation.execution_id)
    assert calls == 0
    pending = repository.get_distillation_execution(reservation.execution_id)
    assert pending is not None and pending.invocation_count == 0
    assert pending.status == "PENDING"

    repository.authorize_cloud_execution(
        authorization_id="cloud-consent:wrong-hash-identity",
        execution_id=reservation.execution_id,
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        verified_input_hash="0" * 64,
        consent_kind="USER_CONFIRMATION",
        now=NOW,
    )
    with pytest.raises(CloudConsentRequiredError):
        service.continue_reserved_distillation(reservation.execution_id)
    assert calls == 0
    assert repository.get_distillation_execution(reservation.execution_id).invocation_count == 0
    with pytest.raises(IntegrityConflict):
        service.authorize_reserved_cloud_execution(reservation.execution_id)


def test_openai_consent_is_bound_to_one_execution_and_complete_15_evidence_input(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_ids = tuple(
        _evidence(repository, video_id, start_ms=1_000 + index * 1_000,
                  end_ms=1_500 + index * 1_000)
        for index in range(15)
    )
    calls: list[tuple[object, str, float, int]] = []

    def wire(request, credential, timeout, retries):
        calls.append((request, credential, timeout, retries))
        candidate_input = request["input"]
        source_payload = json.loads(candidate_input[2]["content"].split("=", 1)[1])
        evidence = source_payload["evidence"]
        output = json.dumps({
            "result": "NO_NEW_INTELLIGENCE",
            "evidence": [
                {"evidence_id": item["evidence_id"], "start_ms": item["start_ms"], "end_ms": item["end_ms"]}
                for item in evidence
            ],
        })
        return {
            "object": "response", "status": "completed", "model": "gpt-4.1",
            "output": [{"type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": output}]}],
            "usage": {"input_tokens": 5644, "output_tokens": 321},
        }

    service, reservation, verified_input = _openai_qualification_service(
        repository, source_id=source_id, video_id=video_id,
        evidence_ids=evidence_ids, wire_transport=wire,
    )
    with pytest.raises(CloudConsentRequiredError):
        service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert calls == []
    with pytest.raises(
        sqlite3.IntegrityError,
        match="OpenAI dispatch requires prior execution authorization",
    ):
        repository.claim_reserved_distillation_execution(
            execution_id=reservation.execution_id,
            source_id=source_id,
            video_id=video_id,
            reason=PersonalizedDistillationService._RESERVATION_REASON,
            use_case=PersonalizedDistillationService._RESERVATION_USE_CASE,
            selected_provider="openai",
            selected_model="gpt-4.1",
            output_language="zh-CN",
            now=NOW,
        )
    unclaimed = repository.get_distillation_execution(reservation.execution_id)
    assert unclaimed is not None
    assert unclaimed.status == "PENDING" and unclaimed.invocation_count == 0

    with pytest.raises(IntegrityConflict):
        repository.authorize_cloud_execution(
            authorization_id="openai-consent-wrong-execution",
            execution_id="unrelated-openai-execution",
            provider="openai", model="gpt-4.1",
            verified_input_hash=verified_input.semantic_hash,
            consent_kind="OWNER_QUALIFICATION", now=NOW,
        )
    with pytest.raises(ValueError, match="identity is invalid"):
        repository.authorize_cloud_execution(
            authorization_id="openai-consent-wrong-model",
            execution_id=reservation.execution_id,
            provider="openai", model="gpt-4.1-mini",
            verified_input_hash=verified_input.semantic_hash,
            consent_kind="OWNER_QUALIFICATION", now=NOW,
        )
    with pytest.raises(ValueError, match="identity is invalid"):
        repository.authorize_cloud_execution(
            authorization_id="unsupported-provider-consent",
            execution_id=reservation.execution_id,
            provider="unapproved", model="gpt-4.1",
            verified_input_hash=verified_input.semantic_hash,
            consent_kind="OWNER_QUALIFICATION", now=NOW,
        )
    for authorization_id, provider, model in (
        ("openai-sql-unsupported-model", "openai", "gpt-4.1-mini"),
        ("openai-sql-unsupported-provider", "unapproved", "gpt-4.1"),
    ):
        with repository._connect() as connection:
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO distillation_openai_cloud_authorizations "
                    "(authorization_id, execution_id, provider, model, verified_input_hash, "
                    "consent_kind, disclosure_version, cost_status, authorized_at) "
                    "VALUES (?, ?, ?, ?, ?, 'OWNER_QUALIFICATION', "
                    "'m12-cloud-intelligence-v1', 'UNKNOWN', ?)",
                    (
                        authorization_id,
                        reservation.execution_id,
                        provider,
                        model,
                        verified_input.semantic_hash,
                        NOW.isoformat(),
                    ),
                )

    authorization_id = service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    consent = repository.get_cloud_execution_authorization(reservation.execution_id)
    assert consent is not None
    assert consent.authorization_id == authorization_id
    assert consent.provider == "openai" and consent.model == "gpt-4.1"
    assert consent.verified_input_hash == verified_input.semantic_hash
    assert consent.consent_kind == "OWNER_QUALIFICATION"
    with repository._connect() as connection:
        row = connection.execute(
            "SELECT cost_status FROM distillation_openai_cloud_authorizations WHERE execution_id = ?",
            (reservation.execution_id,),
        ).fetchone()
        assert row["cost_status"] == "UNKNOWN"

    other_source_id, other_video_id = _source_and_video(
        repository, "video-openai-other-execution"
    )
    other_evidence_id = _evidence(repository, other_video_id)
    other_reservation = service.reserve_distillation_execution(
        source_id=other_source_id,
        video_id=other_video_id,
        evidence_ids=(other_evidence_id,),
    )
    assert repository.get_cloud_execution_authorization(other_reservation.execution_id) is None
    with pytest.raises(
        sqlite3.IntegrityError,
        match="OpenAI dispatch requires prior execution authorization",
    ):
        repository.claim_reserved_distillation_execution(
            execution_id=other_reservation.execution_id,
            source_id=other_source_id,
            video_id=other_video_id,
            reason=PersonalizedDistillationService._RESERVATION_REASON,
            use_case=PersonalizedDistillationService._RESERVATION_USE_CASE,
            selected_provider="openai",
            selected_model="gpt-4.1",
            output_language="zh-CN",
            now=NOW,
        )
    other_pending = repository.get_distillation_execution(other_reservation.execution_id)
    assert other_pending is not None and other_pending.invocation_count == 0
    assert calls == []

    result = service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert result.status is DistillationExecutionStatus.SUCCEEDED_NO_NEW_INTELLIGENCE
    assert result.invocation_count == 1
    ledger = repository.get_distillation_resource_usage(reservation.execution_id)
    assert ledger.actual_provider == "openai"
    assert ledger.actual_model == "gpt-4.1"
    assert (ledger.input_tokens, ledger.output_tokens) == (5644, 321)
    assert ledger.cost_microunits is None
    assert len(calls) == 1
    assert calls[0][0]["model"] == "gpt-4.1"
    assert len(json.loads(calls[0][0]["input"][2]["content"].split("=", 1)[1])["evidence"]) == 15
    assert calls[0][1] == "synthetic-openai-secret"

    restarted = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert restarted.initialize(now=NOW).version == 31
    assert restarted.get_cloud_execution_authorization(reservation.execution_id) == consent
    assert restarted.get_distillation_resource_usage(reservation.execution_id) == ledger
    assert service.continue_qualification_reserved_distillation(reservation.execution_id) == result
    assert len(calls) == 1
    with restarted._connect() as connection:
        assert "synthetic-openai-secret" not in "\n".join(connection.iterdump())
        assert connection.execute(
            "SELECT COUNT(*) FROM distillation_openai_cloud_authorizations"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM distillation_cloud_authorizations"
        ).fetchone()[0] == 0


@pytest.mark.parametrize(
    ("unknown_transport", "expected_status", "expected_outcome"),
    [
        (False, DistillationExecutionStatus.REJECTED_OUTPUT, "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN"),
        (True, DistillationExecutionStatus.AMBIGUOUS, "TRANSPORT_OUTCOME_UNKNOWN"),
    ],
)
def test_openai_known_response_and_ambiguous_transport_accounting_are_distinct(
    tmp_path: Path,
    unknown_transport: bool,
    expected_status: DistillationExecutionStatus,
    expected_outcome: str,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    calls = 0

    def wire(*_args):
        nonlocal calls
        calls += 1
        if unknown_transport:
            raise RuntimeError("synthetic transport outcome unknown")
        return {"object": "response", "status": "completed",
                "usage": {"input_tokens": 50, "output_tokens": 10}}

    service, reservation, _ = _openai_qualification_service(
        repository, source_id=source_id, video_id=video_id,
        evidence_ids=(evidence_id,), wire_transport=wire,
    )
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    result = service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert result.status is expected_status
    assert result.invocation_count == 1
    ledger = repository.get_distillation_resource_usage(reservation.execution_id)
    assert ledger.outcome == expected_outcome
    assert ledger.invocation_count == 1
    assert ledger.actual_provider == (None if unknown_transport else "openai")
    assert any(
        item.execution_id == reservation.execution_id
        for item in repository.list_distillation_resource_usage()
    )
    assert calls == 1

    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert reopened.initialize(now=NOW).version == 31
    assert reopened.get_distillation_resource_usage(reservation.execution_id) == ledger
    replay = service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert replay == result
    assert calls == 1
    with reopened._connect() as connection:
        failure_count = connection.execute(
            "SELECT COUNT(*) FROM distillation_cloud_response_failures "
            "WHERE execution_id = ?",
            (reservation.execution_id,),
        ).fetchone()[0]
    assert failure_count == (0 if unknown_transport else 1)


@pytest.mark.parametrize(
    "transport_type",
    [MoonshotK26CloudDistillationTransport, MoonshotK26NonThinkingCloudDistillationTransport],
)
def test_moonshot_k2_6_consent_positive_zero_and_restart_are_exactly_once(
    tmp_path: Path,
    transport_type: type[MoonshotK26CloudDistillationTransport],
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository, "video-moonshot-positive-zero")
    evidence_ids = tuple(
        _evidence(
            repository,
            video_id,
            start_ms=1_000 + index * 1_000,
            end_ms=1_500 + index * 1_000,
        )
        for index in range(15)
    )
    calls: list[tuple[Mapping[str, object], str, float, int]] = []

    def wire(request, credential, timeout, retries):
        calls.append((request, credential, timeout, retries))
        messages = request["messages"]
        evidence = json.loads(messages[2]["content"].split("=", 1)[1])["evidence"]
        answer = json.dumps(
            {
                "result": "NO_NEW_INTELLIGENCE",
                "evidence": [
                    {
                        "evidence_id": item["evidence_id"],
                        "start_ms": item["start_ms"],
                        "end_ms": item["end_ms"],
                    }
                    for item in evidence
                ],
            },
            ensure_ascii=False,
        )
        return _MoonshotWireResponse(
            http_status=200,
            response_object_type=(
                "chat.completion.chunk" if request["stream"] else "chat.completion"
            ),
            model_identity="kimi-k2.6",
            choices_count=1,
            message_exists=True,
            content_type="str",
            content_present=True,
            content_length=len(answer),
            final_content=answer,
            reasoning_present=True,
            reasoning_length=103,
            finish_reason="stop",
            prompt_tokens=5_644,
            completion_tokens=321,
            reasoning_tokens=300,
            stream_complete=True,
            malformed_envelope=False,
        )

    service, reservation, verified_input, transport = _moonshot_qualification_service(
        repository,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=evidence_ids,
        wire_transport=wire,
        transport_type=transport_type,
    )
    with pytest.raises(CloudConsentRequiredError):
        service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert calls == []
    with pytest.raises(IntegrityConflict):
        repository.authorize_cloud_execution(
            authorization_id="moonshot-wrong-execution-identity",
            execution_id="moonshot-execution-does-not-exist",
            provider="moonshot",
            model="kimi-k2.6",
            verified_input_hash=verified_input.semantic_hash,
            consent_kind="OWNER_QUALIFICATION",
            now=NOW,
        )
    with pytest.raises(ValueError, match="identity is invalid"):
        repository.authorize_cloud_execution(
            authorization_id="moonshot-wrong-model-identity",
            execution_id=reservation.execution_id,
            provider="moonshot",
            model="kimi-k2.7-code",
            verified_input_hash=verified_input.semantic_hash,
            consent_kind="OWNER_QUALIFICATION",
            now=NOW,
        )
    with pytest.raises(IntegrityConflict):
        repository.authorize_cloud_execution(
            authorization_id="moonshot-model-mismatch-authority",
            execution_id=reservation.execution_id,
            provider="moonshot",
            model="kimi-k3",
            verified_input_hash=verified_input.semantic_hash,
            consent_kind="OWNER_QUALIFICATION",
            now=NOW,
        )

    authorization_id = service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    consent = repository.get_cloud_execution_authorization(reservation.execution_id)
    assert consent is not None
    assert consent.authorization_id == authorization_id
    assert (consent.provider, consent.model) == ("moonshot", "kimi-k2.6")
    assert consent.verified_input_hash == verified_input.semantic_hash
    assert consent.authorized_at == NOW

    result = service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert result.status is DistillationExecutionStatus.SUCCEEDED_NO_NEW_INTELLIGENCE
    assert result.invocation_count == 1
    ledger = repository.get_distillation_resource_usage(reservation.execution_id)
    assert ledger.actual_provider == "moonshot"
    assert ledger.actual_model == "kimi-k2.6"
    assert ledger.http_status_code == 200
    assert (ledger.input_tokens, ledger.output_tokens) == (5_644, 321)
    assert ledger.cost_microunits is None
    assert len(calls) == 1
    request, credential, timeout, retries = calls[0]
    assert request["model"] == "kimi-k2.6"
    assert request["stream"] is (transport_type is MoonshotK26CloudDistillationTransport)
    assert len(json.loads(request["messages"][2]["content"].split("=", 1)[1])["evidence"]) == 15
    assert (credential, timeout, retries) == (
        "synthetic-moonshot-secret",
        300.0,
        0,
    )

    with repository._connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM distillation_no_new_intelligence_results "
            "WHERE execution_id = ?",
            (reservation.execution_id,),
        ).fetchone()[0] == 1
        no_new = connection.execute(
            "SELECT evidence_ids_json FROM distillation_no_new_intelligence_results "
            "WHERE execution_id = ?",
            (reservation.execution_id,),
        ).fetchone()
        assert len(json.loads(no_new["evidence_ids_json"])) == 15
        assert "synthetic-moonshot-secret" not in "\n".join(connection.iterdump())

    other_source_id, other_video_id = _source_and_video(
        repository, "video-moonshot-no-blanket-consent"
    )
    other_evidence_id = _evidence(repository, other_video_id)
    other_reservation = service.reserve_distillation_execution(
        source_id=other_source_id,
        video_id=other_video_id,
        evidence_ids=(other_evidence_id,),
    )
    assert repository.get_cloud_execution_authorization(other_reservation.execution_id) is None
    other_result = service.continue_qualification_reserved_distillation(
        other_reservation.execution_id
    )
    assert other_result.status is DistillationExecutionStatus.WAITING_MODEL
    assert repository.get_distillation_execution(other_reservation.execution_id).invocation_count == 0
    assert len(calls) == 1

    restarted_repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert restarted_repository.initialize(now=NOW).version == 31
    restarted = _service(restarted_repository, transport)  # type: ignore[arg-type]
    assert restarted.continue_qualification_reserved_distillation(
        reservation.execution_id
    ).status is DistillationExecutionStatus.SUCCEEDED_NO_NEW_INTELLIGENCE
    assert len(calls) == 1


def test_non_thinking_k2_6_admits_legal_subset_with_new_execution_identity(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository, "video-moonshot-nonthinking-admitted")
    evidence_ids = tuple(
        _evidence(
            repository,
            video_id,
            start_ms=1_000 + index * 1_000,
            end_ms=1_500 + index * 1_000,
        )
        for index in range(15)
    )
    calls = 0
    reasoning = "SYNTHETIC_REASONING_MUST_NOT_PERSIST"

    def wire(request, _credential, _timeout, retries):
        nonlocal calls
        calls += 1
        assert retries == 0
        assert request["stream"] is False
        assert request["thinking"] == {"type": "disabled"}
        payload = json.loads(request["messages"][2]["content"].split("=", 1)[1])
        assert len(payload["evidence"]) == 15
        cited = [payload["evidence"][0], payload["evidence"][2]]
        answer = json.dumps({
            "core_conclusion": "紧急关闭机制依赖人类仍能有效介入。",
            "user_relevant_information": ["评估时应跟踪人的实际控制能力。"],
            "important_new_information": ["关闭开关本身并不构成完整的长期控制。"],
            "meaningful_details": ["监测和干预能力需要跟随系统能力变化。"],
            "filtered_noise": [],
            "claim_kind": "SYSTEM_INFERENCE",
            "evidence": [
                {
                    "evidence_id": item["evidence_id"],
                    "start_ms": item["start_ms"],
                    "end_ms": item["end_ms"],
                    "stance": "supporting" if index == 0 else "conditional",
                }
                for index, item in enumerate(cited)
            ],
        }, ensure_ascii=False)
        return _MoonshotWireResponse(
            http_status=200,
            response_object_type="chat.completion",
            model_identity="kimi-k2.6",
            choices_count=1,
            message_exists=True,
            content_type="string",
            content_present=True,
            content_length=len(answer),
            final_content=answer,
            reasoning_present=True,
            reasoning_length=len(reasoning),
            finish_reason="stop",
            prompt_tokens=5_644,
            completion_tokens=900,
            reasoning_tokens=None,
            stream_complete=True,
            malformed_envelope=False,
        )

    service, reservation, verified, _transport = _moonshot_qualification_service(
        repository,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=evidence_ids,
        wire_transport=wire,
        transport_type=MoonshotK26NonThinkingCloudDistillationTransport,
    )
    previous_profile_id = PersonalizedDistillationService._reservation_id(
        source_id=source_id,
        video_id=video_id,
        evidence_ids=tuple(sorted(evidence_ids)),
        selected_provider="moonshot",
        selected_model="kimi-k2.6",
        output_language="zh-CN",
        verified_input_hash=verified.semantic_hash,
    )
    assert reservation.execution_id != previous_profile_id
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    result = service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert result.status is DistillationExecutionStatus.SUCCEEDED
    assert result.invocation_count == 1
    assert result.revision_id is not None
    relations = repository.list_intelligence_revision_evidence_relations(result.revision_id)
    ordered = tuple(sorted(evidence_ids))
    assert {relation.evidence_id: relation.stance for relation in relations} == {
        ordered[0]: EvidenceStance.SUPPORTING,
        ordered[2]: EvidenceStance.CONDITIONAL,
    }
    usage = repository.get_distillation_resource_usage(reservation.execution_id)
    assert usage.http_status_code == 200
    assert (usage.input_tokens, usage.output_tokens) == (5_644, 900)
    assert calls == 1
    with repository._connect() as connection:
        persisted = "\n".join(connection.iterdump())
    assert reasoning not in persisted
    assert "synthetic-moonshot-secret" not in persisted


@pytest.mark.parametrize(
    ("consent_kind", "http_status_code", "quiescent"),
    [
        ("USER_CONFIRMATION", 200, True),
        ("OWNER_QUALIFICATION", 200, False),
        ("USER_CONFIRMATION", None, False),
    ],
)
def test_backup_quiescence_requires_confirmed_user_cloud_success_for_local_wait(
    tmp_path: Path,
    consent_kind: str,
    http_status_code: int | None,
    quiescent: bool,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository, "video-cloud-backup")
    evidence_id = _evidence(repository, video_id)
    local_execution_id = "local-waiting-for-model"
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id=local_execution_id,
            source_id=source_id,
            video_id=video_id,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="ollama",
            selected_model="qwen3:8b",
            output_language="zh-CN",
        ),
        now=NOW,
    )
    repository.finish_distillation_without_admission(
        execution_id=local_execution_id,
        status="WAITING_MODEL",
        budget_state="ADMITTED",
        outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT",
        invocation_count=0,
        actual_provider=None,
        actual_model=None,
        input_tokens=None,
        output_tokens=None,
        cost_microunits=None,
        duration_ms=None,
        now=NOW,
    )
    run = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=source_id,
            command_id="cloud-backup-source-run",
            priority=SourceRunPriority.P2,
            created_at=NOW,
        )
    )
    repository.transition_source_run(run.run_id, to_state=SourceRunState.RUNNING, now=NOW)
    repository.record_source_run_child(
        run.run_id,
        video_id=video_id,
        state=SourceRunChildState.PENDING,
        distillation_execution_id=local_execution_id,
        now=NOW,
    )
    repository.transition_source_run_child(
        run.run_id, video_id=video_id, to_state=SourceRunChildState.WAITING, now=NOW
    )
    repository.transition_source_run(
        run.run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.MODEL_UNAVAILABLE,
        now=NOW,
    )
    backup = BackupRestoreService(database=tmp_path / "state.sqlite3", data_root=tmp_path)
    with repository._connect() as connection:
        assert {"SOURCE_RUN_ACTIVE", "DISTILLATION_ACTIVE"} <= set(
            backup._quiescence_reasons(connection)
        )

    service, reservation, verified, _transport = _moonshot_qualification_service(
        repository,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=(evidence_id,),
        wire_transport=lambda *_args: None,
        transport_type=MoonshotK26NonThinkingCloudDistillationTransport,
    )
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind=consent_kind
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id=reservation.execution_id,
        source_id=source_id,
        video_id=video_id,
        reason=PersonalizedDistillationService._RESERVATION_REASON,
        use_case=PersonalizedDistillationService._RESERVATION_USE_CASE,
        selected_provider="moonshot",
        selected_model="kimi-k2.6",
        output_language="zh-CN",
        now=NOW,
    )
    assert verified.semantic_hash
    repository.admit_distillation(
        execution_id=reservation.execution_id,
        intelligence_id="cloud-intelligence-for-backup",
        revision_id="cloud-revision-for-backup",
        claim_kind=IntelligenceClaimKind.SYSTEM_INFERENCE,
        content_hash="a" * 64,
        evidence_ids=(evidence_id,),
        evidence_stances=((evidence_id, EvidenceStance.SUPPORTING),),
        card=DistillationCardWrite(
            source_id=source_id,
            video_id=video_id,
            core_conclusion="一条由原始证据支持的长期判断。",
            user_relevant_information=(),
            important_new_information=("应保留这条判断。",),
            meaningful_details=(),
            filtered_noise=(),
            preference_ids=(),
            source_policy_revision_id=None,
        ),
        actual_provider="moonshot",
        actual_model="kimi-k2.6",
        input_tokens=100,
        output_tokens=30,
        cost_microunits=None,
        duration_ms=100,
        http_status_code=http_status_code,
        now=NOW,
    )
    with repository._connect() as connection:
        reasons = backup._quiescence_reasons(connection)
    assert (reasons == []) is quiescent
    if not quiescent:
        assert {"SOURCE_RUN_ACTIVE", "DISTILLATION_ACTIVE"} <= set(reasons)


@pytest.mark.parametrize(
    "transport_type",
    [MoonshotK26CloudDistillationTransport, MoonshotK26NonThinkingCloudDistillationTransport],
)
def test_moonshot_known_response_and_unknown_transport_accounting_are_distinct(
    tmp_path: Path,
    transport_type: type[MoonshotK26CloudDistillationTransport],
) -> None:
    for unknown_transport, expected_status, expected_outcome in (
        (False, DistillationExecutionStatus.REJECTED_OUTPUT, "CLOUD_HTTP_ERROR"),
        (True, DistillationExecutionStatus.AMBIGUOUS, "TRANSPORT_OUTCOME_UNKNOWN"),
    ):
        scoped = tmp_path / ("ambiguous" if unknown_transport else "known")
        scoped.mkdir()
        repository = _repository(scoped)
        source_id, video_id = _source_and_video(repository, f"video-moonshot-{scoped.name}")
        evidence_id = _evidence(repository, video_id)
        calls = 0

        def wire(*_args):
            nonlocal calls
            calls += 1
            if unknown_transport:
                raise TimeoutError("no confirmed HTTP response")
            raise KnownCloudDistillationResponseError(http_status=503)

        service, reservation, _verified, transport = _moonshot_qualification_service(
            repository,
            source_id=source_id,
            video_id=video_id,
            evidence_ids=(evidence_id,),
            wire_transport=wire,
            transport_type=transport_type,
        )
        service.authorize_reserved_cloud_execution(
            reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
        )
        result = service.continue_qualification_reserved_distillation(
            reservation.execution_id
        )
        assert result.status is expected_status
        assert result.invocation_count == 1
        ledger = repository.get_distillation_resource_usage(reservation.execution_id)
        assert ledger.outcome == expected_outcome
        assert ledger.invocation_count == 1
        assert ledger.http_status_code == (None if unknown_transport else 503)
        assert ledger.cost_microunits is None
        assert calls == 1

        restarted_repository = SQLiteStateRepository(scoped / "state.sqlite3")
        assert restarted_repository.initialize(now=NOW).version == 31
        restarted = _service(restarted_repository, transport)  # type: ignore[arg-type]
        assert restarted.continue_qualification_reserved_distillation(
            reservation.execution_id
        ).status is expected_status
        assert calls == 1


@pytest.mark.parametrize("http_status", [400, 401, 403, 429, 500, 503])
@pytest.mark.parametrize(
    "transport_type",
    [MoonshotK26CloudDistillationTransport, MoonshotK26NonThinkingCloudDistillationTransport],
)
def test_known_cloud_http_errors_keep_status_and_never_become_ambiguous(
    tmp_path: Path,
    http_status: int,
    transport_type: type[MoonshotK26CloudDistillationTransport],
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository, f"video-moonshot-http-{http_status}")
    evidence_id = _evidence(repository, video_id)
    calls = 0

    def wire(*_args):
        nonlocal calls
        calls += 1
        raise KnownCloudDistillationResponseError(
            reason="MOONSHOT_RAW_ERROR_SECRET",
            http_status=http_status,
        )

    service, reservation, _verified, transport = _moonshot_qualification_service(
        repository,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=(evidence_id,),
        wire_transport=wire,
        transport_type=transport_type,
    )
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    if http_status == 400:
        with pytest.raises(ValueError, match="metadata is invalid"):
            repository.finish_distillation_cloud_response_failure(
                execution_id=reservation.execution_id,
                budget_state="RUNTIME_BUDGET_ADMITTED",
                outcome="MOONSHOT_RAW_ERROR_SECRET",
                http_status_code=http_status,
                now=NOW,
            )
        with pytest.raises(ValueError, match="metadata is invalid"):
            repository.finish_distillation_cloud_response_failure(
                execution_id=reservation.execution_id,
                budget_state="RUNTIME_BUDGET_ADMITTED",
                outcome="HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN",
                http_status_code=None,
                now=NOW,
            )

    first = service.continue_qualification_reserved_distillation(reservation.execution_id)
    usage = repository.get_distillation_resource_usage(reservation.execution_id)
    assert first.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert first.invocation_count == 1
    assert usage.outcome == "CLOUD_HTTP_ERROR"
    assert usage.http_status_code == http_status
    assert usage.actual_provider == "moonshot"
    assert usage.actual_model is None
    assert usage.input_tokens is None and usage.output_tokens is None
    assert calls == 1

    restarted = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert restarted.initialize(now=NOW).version == 31
    assert restarted.get_distillation_resource_usage(reservation.execution_id) == usage
    assert _service(restarted, transport).continue_qualification_reserved_distillation(
        reservation.execution_id
    ) == first
    assert calls == 1
    with restarted._connect() as connection:
        persisted = "\n".join(connection.iterdump())
    assert "synthetic-moonshot-secret" not in persisted
    assert "MOONSHOT_RAW_ERROR_SECRET" not in persisted


@pytest.mark.parametrize("http_status_code", [None, 200])
def test_confirmed_cloud_failure_ledger_rejects_free_text_outcomes(
    tmp_path: Path,
    http_status_code: int | None,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository, "video-moonshot-finite-http-failure")
    evidence_id = _evidence(repository, video_id)
    service, reservation, _verified, _transport = _moonshot_qualification_service(
        repository,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=(evidence_id,),
        wire_transport=lambda *_args: None,
    )
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id=reservation.execution_id,
        source_id=source_id,
        video_id=video_id,
        reason=PersonalizedDistillationService._RESERVATION_REASON,
        use_case=PersonalizedDistillationService._RESERVATION_USE_CASE,
        selected_provider="moonshot",
        selected_model="kimi-k2.6",
        output_language="zh-CN",
        now=NOW,
    )

    with pytest.raises(IntegrityConflict):
        repository.finish_distillation_without_admission(
            execution_id=reservation.execution_id,
            status="REJECTED_OUTPUT",
            budget_state="RUNTIME_BUDGET_ADMITTED",
            outcome="MOONSHOT_RAW_ERROR_SECRET",
            invocation_count=1,
            actual_provider="moonshot",
            actual_model="kimi-k2.6",
            input_tokens=None,
            output_tokens=None,
            cost_microunits=None,
            duration_ms=None,
            now=NOW,
            http_status_code=http_status_code,
        )

    record = repository.get_distillation_execution(reservation.execution_id)
    assert record is not None
    assert record.status == "PENDING" and record.invocation_count == 1
    with pytest.raises(StateStoreError, match="resource usage does not exist"):
        repository.get_distillation_resource_usage(reservation.execution_id)


@pytest.mark.parametrize(
    ("model", "malformed", "identity_invalid", "expected_outcome", "actual_model"),
    [
        (None, False, False, "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN", None),
        ("kimi-k3", False, False, "HTTP_RESPONSE_MODEL_IDENTITY_INVALID", None),
        ("kimi-k2.6", True, False, "CLOUD_HTTP_RESPONSE_MALFORMED", "kimi-k2.6"),
        ("kimi-k2.6", False, True, "HTTP_RESPONSE_MODEL_IDENTITY_INVALID", None),
    ],
)
@pytest.mark.parametrize(
    "transport_type",
    [MoonshotK26CloudDistillationTransport, MoonshotK26NonThinkingCloudDistillationTransport],
)
def test_confirmed_http_200_failures_have_finite_distinct_ledger_outcomes(
    tmp_path: Path,
    model: str | None,
    malformed: bool,
    identity_invalid: bool,
    expected_outcome: str,
    actual_model: str | None,
    transport_type: type[MoonshotK26CloudDistillationTransport],
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository, "video-moonshot-http-200")
    evidence_id = _evidence(repository, video_id)
    response = _MoonshotWireResponse(
        http_status=200,
        response_object_type="chat.completion.chunk",
        model_identity=model,
        choices_count=1,
        message_exists=True,
        content_type="string",
        content_present=True,
        content_length=28,
        final_content="BODY_SENTINEL_NO_PERSISTENCE",
        reasoning_present=True,
        reasoning_length=77,
        finish_reason="stop",
        prompt_tokens=90,
        completion_tokens=12,
        reasoning_tokens=7,
        stream_complete=True,
        malformed_envelope=malformed,
        model_identity_invalid=identity_invalid,
    )
    calls = 0

    def wire(*_args):
        nonlocal calls
        calls += 1
        return response

    service, reservation, _verified, transport = _moonshot_qualification_service(
        repository,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=(evidence_id,),
        wire_transport=wire,
        transport_type=transport_type,
    )
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    result = service.continue_qualification_reserved_distillation(reservation.execution_id)
    usage = repository.get_distillation_resource_usage(reservation.execution_id)
    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert result.invocation_count == 1
    assert usage.status == "REJECTED_OUTPUT"
    assert usage.outcome == expected_outcome
    assert usage.http_status_code == 200
    assert usage.actual_provider == "moonshot"
    assert usage.actual_model == actual_model
    assert calls == 1
    with repository._connect() as connection:
        persisted = "\n".join(connection.iterdump())
    assert "BODY_SENTINEL_NO_PERSISTENCE" not in persisted
    assert "synthetic-moonshot-secret" not in persisted
    assert "reasoning" not in persisted.lower()


@pytest.mark.parametrize(
    ("finish_reason", "content_present", "final_content", "expected_outcome"),
    [
        ("length", True, "partial final JSON", "CLOUD_OUTPUT_TRUNCATED"),
        ("stop", False, None, "CLOUD_FINAL_CONTENT_MISSING"),
    ],
)
@pytest.mark.parametrize(
    "transport_type",
    [MoonshotK26CloudDistillationTransport, MoonshotK26NonThinkingCloudDistillationTransport],
)
def test_confirmed_http_200_content_failures_retain_status(
    tmp_path: Path,
    finish_reason: str,
    content_present: bool,
    final_content: str | None,
    expected_outcome: str,
    transport_type: type[MoonshotK26CloudDistillationTransport],
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository, "video-moonshot-content-failure")
    evidence_id = _evidence(repository, video_id)
    response = _MoonshotWireResponse(
        http_status=200,
        response_object_type=(
            "chat.completion.chunk"
            if transport_type is MoonshotK26CloudDistillationTransport
            else "chat.completion"
        ),
        model_identity="kimi-k2.6",
        choices_count=1,
        message_exists=True,
        content_type="string" if content_present else "missing",
        content_present=content_present,
        content_length=0 if final_content is None else len(final_content),
        final_content=final_content,
        reasoning_present=True,
        reasoning_length=88,
        finish_reason=finish_reason,
        prompt_tokens=100,
        completion_tokens=10,
        reasoning_tokens=8,
        stream_complete=True,
        malformed_envelope=False,
    )
    calls = 0

    def wire(*_args):
        nonlocal calls
        calls += 1
        return response

    service, reservation, _verified, transport = _moonshot_qualification_service(
        repository,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=(evidence_id,),
        wire_transport=wire,
        transport_type=transport_type,
    )
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    result = service.continue_qualification_reserved_distillation(reservation.execution_id)
    usage = repository.get_distillation_resource_usage(reservation.execution_id)
    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert result.invocation_count == 1
    assert usage.outcome == expected_outcome
    assert usage.http_status_code == 200
    assert usage.actual_provider == "moonshot"
    assert usage.actual_model == "kimi-k2.6"
    assert calls == 1


def test_moonshot_incomplete_stream_is_ambiguous_and_never_retried(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository, "video-moonshot-incomplete-stream")
    evidence_id = _evidence(repository, video_id)
    calls = 0

    def interrupted_stream(*_args):
        nonlocal calls
        calls += 1
        return _MoonshotWireResponse(
            http_status=200,
            response_object_type="chat.completion.chunk",
            model_identity="kimi-k2.6",
            choices_count=1,
            message_exists=True,
            content_type="string",
            content_present=True,
            content_length=len("partial final"),
            final_content="partial final",
            reasoning_present=True,
            reasoning_length=42,
            finish_reason="stop",
            prompt_tokens=5_644,
            completion_tokens=321,
            reasoning_tokens=300,
            stream_complete=False,
            malformed_envelope=False,
            stream_started=True,
        )

    service, reservation, _verified, transport = _moonshot_qualification_service(
        repository,
        source_id=source_id,
        video_id=video_id,
        evidence_ids=(evidence_id,),
        wire_transport=interrupted_stream,
    )
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )

    result = service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert result.status is DistillationExecutionStatus.AMBIGUOUS
    assert result.invocation_count == 1
    ledger = repository.get_distillation_resource_usage(reservation.execution_id)
    assert ledger.outcome == "TRANSPORT_OUTCOME_UNKNOWN"
    assert ledger.invocation_count == 1
    assert ledger.actual_provider is None
    assert ledger.actual_model is None
    assert ledger.http_status_code == 200
    assert calls == 1

    restarted_repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert restarted_repository.initialize(now=NOW).version == 31
    restarted = _service(restarted_repository, transport)  # type: ignore[arg-type]
    assert restarted.continue_qualification_reserved_distillation(
        reservation.execution_id
    ).status is DistillationExecutionStatus.AMBIGUOUS
    assert calls == 1


def test_v027_accepts_only_the_two_finite_moonshot_consent_pairs(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    reason = PersonalizedDistillationService._RESERVATION_REASON
    use_case = PersonalizedDistillationService._RESERVATION_USE_CASE

    def reserve(execution_id: str, model: str) -> tuple[str, str]:
        source_id, video_id = _source_and_video(repository, f"video-{execution_id}")
        evidence_id = _evidence(repository, video_id)
        repository.reserve_distillation_execution(
            DistillationExecutionWrite(
                execution_id=execution_id,
                source_id=source_id,
                video_id=video_id,
                reason=reason,
                use_case=use_case,
                selected_provider="moonshot",
                selected_model=model,
                output_language="zh-CN",
            ),
            now=NOW,
        )
        return source_id, evidence_id

    k2_source, _ = reserve("moonshot-k2-6-consent", "kimi-k2.6")
    del k2_source
    k2_consent = repository.authorize_cloud_execution(
        authorization_id="moonshot-k2-6-qualification-consent",
        execution_id="moonshot-k2-6-consent",
        provider="moonshot",
        model="kimi-k2.6",
        verified_input_hash="a" * 64,
        consent_kind="OWNER_QUALIFICATION",
        now=NOW,
    )
    k3_source, _ = reserve("moonshot-k3-consent", "kimi-k3")
    del k3_source
    k3_consent = repository.authorize_cloud_execution(
        authorization_id="moonshot-k3-qualification-consent",
        execution_id="moonshot-k3-consent",
        provider="moonshot",
        model="kimi-k3",
        verified_input_hash="b" * 64,
        consent_kind="OWNER_QUALIFICATION",
        now=NOW,
    )

    assert repository.get_cloud_execution_authorization("moonshot-k2-6-consent") == k2_consent
    assert repository.get_cloud_execution_authorization("moonshot-k3-consent") == k3_consent
    assert not NormalV1ProductionAuthorizationAuthority.resolve(
        provider="moonshot",
        model="kimi-k2.6",
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=True,
    ).authorized

    unsupported_source, unsupported_video = _source_and_video(
        repository, "video-moonshot-unsupported-model"
    )
    unsupported_evidence = _evidence(repository, unsupported_video)
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id="moonshot-k2-7-rejected",
            source_id=unsupported_source,
            video_id=unsupported_video,
            reason=reason,
            use_case=use_case,
            selected_provider="moonshot",
            selected_model="kimi-k2.7-code",
            output_language="zh-CN",
        ),
        now=NOW,
    )
    with pytest.raises(ValueError, match="identity is invalid"):
        repository.authorize_cloud_execution(
            authorization_id="moonshot-k2-7-no-authority",
            execution_id="moonshot-k2-7-rejected",
            provider="moonshot",
            model="kimi-k2.7-code",
            verified_input_hash="c" * 64,
            consent_kind="OWNER_QUALIFICATION",
            now=NOW,
        )
    with pytest.raises(sqlite3.IntegrityError, match="Moonshot dispatch requires prior execution authorization"):
        repository.claim_reserved_distillation_execution(
            execution_id="moonshot-k2-7-rejected",
            source_id=unsupported_source,
            video_id=unsupported_video,
            reason=reason,
            use_case=use_case,
            selected_provider="moonshot",
            selected_model="kimi-k2.7-code",
            output_language="zh-CN",
            now=NOW,
        )
    assert unsupported_evidence
    assert repository.get_cloud_execution_authorization("moonshot-k2-7-rejected") is None


def test_v028_preserves_v027_moonshot_identity_unknown_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.sqlite3"
    legacy = SQLiteStateRepository(path)
    migrations = legacy._load_migrations()
    monkeypatch.setattr(legacy, "_load_migrations", lambda: migrations[:27])
    assert legacy.initialize(now=NOW).version == 27
    source_id, video_id = _source_and_video(legacy, "video-moonshot-history-v027")
    execution_id = "moonshot-v027-historical-response"
    reason = PersonalizedDistillationService._RESERVATION_REASON
    use_case = PersonalizedDistillationService._RESERVATION_USE_CASE
    legacy.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id=execution_id,
            source_id=source_id,
            video_id=video_id,
            reason=reason,
            use_case=use_case,
            selected_provider="moonshot",
            selected_model="kimi-k2.6",
            output_language="zh-CN",
        ),
        now=NOW,
    )
    legacy.authorize_cloud_execution(
        authorization_id="moonshot-v027-historical-consent",
        execution_id=execution_id,
        provider="moonshot",
        model="kimi-k2.6",
        verified_input_hash="f" * 64,
        consent_kind="OWNER_QUALIFICATION",
        now=NOW,
    )
    assert legacy.claim_reserved_distillation_execution(
        execution_id=execution_id,
        source_id=source_id,
        video_id=video_id,
        reason=reason,
        use_case=use_case,
        selected_provider="moonshot",
        selected_model="kimi-k2.6",
        output_language="zh-CN",
        now=NOW,
    )
    legacy.finish_distillation_unidentified_http_response(
        execution_id=execution_id,
        budget_state="RUNTIME_BUDGET_ADMITTED",
        now=NOW,
    )
    with legacy._connect() as connection:
        old_response = tuple(
            connection.execute(
                "SELECT * FROM distillation_moonshot_unidentified_http_responses "
                "WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        )
        old_consent = tuple(
            connection.execute(
                "SELECT * FROM distillation_moonshot_cloud_authorizations "
                "WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        )

    monkeypatch.setattr(legacy, "_load_migrations", lambda: migrations)
    assert legacy.initialize(now=NOW).version == 31
    with legacy._connect() as connection:
        assert tuple(
            connection.execute(
                "SELECT * FROM distillation_moonshot_unidentified_http_responses "
                "WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        ) == old_response
        assert tuple(
            connection.execute(
                "SELECT * FROM distillation_moonshot_cloud_authorizations "
                "WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        ) == old_consent
    historical = legacy.get_distillation_resource_usage(execution_id)
    assert historical.outcome == "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN"
    assert historical.http_status_code is None
    assert historical.invocation_count == 1


def test_definite_cloud_http_response_without_model_is_not_ambiguous(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    calls = 0

    def wire(*_args):
        nonlocal calls
        calls += 1
        return {"choices": [{"message": {"content": "{}"}}],
                "usage": {"prompt_tokens": 99, "completion_tokens": 9}}

    transport = NvidiaNimCloudDistillationTransport(
        authorization=_normal_nvidia_authorization(),
        credential_resolver=lambda: "synthetic-test-credential",
        wire_transport=wire,
    )
    service = _service(repository, transport)  # type: ignore[arg-type]
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    service.authorize_reserved_cloud_execution(reservation.execution_id)
    first = service.continue_reserved_distillation(reservation.execution_id)
    assert first.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert first.invocation_count == 1
    ledger = repository.get_distillation_resource_usage(reservation.execution_id)
    assert ledger.status == "REJECTED_OUTPUT"
    assert ledger.outcome == "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN"
    assert ledger.actual_provider == "nvidia_nim"
    assert ledger.actual_model is None
    assert ledger.input_tokens is None and ledger.output_tokens is None
    assert ledger.cost_microunits is None
    assert ledger in repository.list_distillation_resource_usage()
    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert reopened.initialize(now=NOW).version == 31
    assert reopened.get_distillation_resource_usage(reservation.execution_id) == ledger
    replay = _service(reopened, transport).continue_reserved_distillation(reservation.execution_id)  # type: ignore[arg-type]
    assert replay == first
    assert calls == 1


def test_cloud_review_and_confirmation_are_separate_api_actions(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    calls = 0

    def wire(*_args):
        nonlocal calls
        calls += 1
        return {
            "model": "moonshotai/kimi-k3",
            "choices": [{"finish_reason": "stop", "message": {"content": _raw(evidence_id)}}],
        }

    cloud = _service(
        repository,
        NvidiaNimCloudDistillationTransport(
            authorization=_normal_nvidia_authorization(),
            credential_resolver=lambda: "synthetic-test-credential",
            wire_transport=wire,
        ),
    )
    without_credential = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        cloud_distillation_service=cloud,
        cloud_intelligence_qualified=True,
        cloud_credential_available=False,
        now=lambda: NOW,
    )
    assert without_credential.handle("GET", f"/api/v1/videos/{video_id}")[1][
        "cloud_intelligence_available"
    ] is False
    with pytest.raises(ApiError):
        without_credential.handle(
            "POST", f"/api/v1/videos/{video_id}/cloud-intelligence/review", b"{}"
        )
    assert calls == 0
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        cloud_distillation_service=cloud,
        cloud_intelligence_qualified=True,
        cloud_credential_available=True,
        now=lambda: NOW,
    )
    review_path = f"/api/v1/videos/{video_id}/cloud-intelligence/review"
    confirm_path = f"/api/v1/videos/{video_id}/cloud-intelligence/confirm"
    with pytest.raises(ApiError):
        app.handle("POST", f"/api/v1/videos/{video_id}/extra/cloud-intelligence/review", b"{}")
    assert calls == 0
    status, payload = app.handle("POST", review_path, b"{}")
    assert status == 201
    review = payload["review"]
    assert isinstance(review, dict)
    assert review["source_id"] == source_id
    assert review["evidence_ids"] == [evidence_id]
    assert review["cost_status"] == "UNKNOWN"
    assert calls == 0
    assert repository.get_cloud_execution_authorization(str(review["execution_id"])) is None
    with pytest.raises(ApiError):
        app.handle("POST", confirm_path, json.dumps({
            "execution_id": review["execution_id"],
            "review_hash": "0" * 64,
            "authorize": True,
        }).encode())
    with pytest.raises(ApiError):
        app.handle("POST", confirm_path, json.dumps({
            "execution_id": review["execution_id"],
            "review_hash": review["verified_input_hash"],
            "authorize": False,
        }).encode())
    assert calls == 0
    status, confirmed = app.handle("POST", confirm_path, json.dumps({
        "execution_id": review["execution_id"],
        "review_hash": review["verified_input_hash"],
        "authorize": True,
    }).encode())
    assert status == 202
    assert confirmed["execution"]["status"] == "SUCCEEDED"
    assert calls == 1
    consent = repository.get_cloud_execution_authorization(str(review["execution_id"]))
    assert consent is not None and consent.consent_kind == "USER_CONFIRMATION"
    assert consent.verified_input_hash == review["verified_input_hash"]
    with pytest.raises(ApiError):
        app.handle("POST", confirm_path, json.dumps({
            "execution_id": review["execution_id"],
            "review_hash": review["verified_input_hash"],
            "authorize": True,
        }).encode())
    assert calls == 1


def test_ambiguous_invocation_round_trips_with_unknown_actual_identity_only(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    execution_id = "exec-ambiguous-unknown-identity"
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id=execution_id,
            source_id=source_id,
            video_id=video_id,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="test-transport",
            selected_model="deterministic-v1",
        ),
        now=NOW,
    )

    result = repository.finish_distillation_without_admission(
        execution_id=execution_id,
        status="AMBIGUOUS",
        budget_state="UNKNOWN",
        outcome="TRANSPORT_OUTCOME_UNKNOWN",
        invocation_count=1,
        actual_provider=None,
        actual_model=None,
        input_tokens=None,
        output_tokens=None,
        cost_microunits=None,
        duration_ms=None,
        now=NOW,
    )

    assert result.status == "AMBIGUOUS"
    ledger = repository.get_distillation_resource_usage(execution_id)
    assert ledger.status == "AMBIGUOUS"
    assert ledger.invocation_count == 1
    assert ledger.actual_provider is None
    assert ledger.actual_model is None
    assert ledger.input_tokens is None and ledger.output_tokens is None
    assert ledger.cost_microunits is None


def test_raw_candidate_never_mints_verified_read_and_ledger_has_no_credential_fields(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    result = _service(repository, _FakeTransport(_raw(evidence_id))).distill(
        _command(source_id, video_id, evidence_id)
    )

    with pytest.raises(TypeError):
        VerifiedIntelligenceRead(  # type: ignore[call-arg]
            intelligence_id=result.intelligence_id,
            revision_id="forged",
            claim_kind=IntelligenceClaimKind.FACT,
            state="CONFIRMED",
            evidence_ids=(),
        )
    with pytest.raises(IntelligenceReadRejected):
        AuthoritativeIntelligenceReader(repository).read_current("missing")
    connection = repository._connect()
    try:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(distillation_resource_usage)")
        }
    finally:
        connection.close()
    assert not {"credential", "secret", "api_key", "prompt"} & columns


def test_loopback_manual_admission_accepts_no_raw_model_fields_and_reads_card_through_authority(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        distillation_service=_service(repository, _FakeTransport(_raw(evidence_id))),
        now=lambda: NOW,
    )

    status, payload = app.handle(
        "POST",
        f"/api/v1/sources/{source_id}/videos/{video_id}/distill",
        json.dumps(
            {
                "execution_id": "api-exec",
                "evidence_ids": [evidence_id],
            }
        ).encode(),
    )

    assert status == 201
    assert payload["execution"]["status"] == "SUCCEEDED"
    intelligence_id = payload["execution"]["intelligence_id"]
    read_status, read_payload = app.handle("GET", f"/api/v1/intelligence/{intelligence_id}")
    assert read_status == 200
    assert read_payload["intelligence"]["trusted"] is True
    assert read_payload["intelligence"]["card"]["core_conclusion"].startswith("The release")
    assert read_payload["intelligence"]["card"]["original_video_url"].endswith(video_id)
    assert read_payload["intelligence"]["card"]["evidence_links"] == [
        {
            "evidence_id": evidence_id,
            "artifact_id": f"artifact-{video_id}-1000-1500",
            "start_ms": 1_000,
            "end_ms": 1_500,
            "language": "en",
            "lineage_kind": "ORIGINAL_TRANSCRIPT",
            "role": "PRIMARY_ORIGINAL",
            "original_excerpt": "Fixture canonical evidence.",
            "translated_excerpt": None,
            "translated_language": None,
            "translation_target_language": "zh-CN",
            "stance": "supporting",
        }
    ]
    with pytest.raises(ApiError):
        app.handle(
            "POST",
            f"/api/v1/sources/{source_id}/videos/{video_id}/distill",
            json.dumps({"execution_id": "bad", "evidence_ids": [evidence_id], "provider": "real"}).encode(),
        )


def test_loopback_distillation_fails_closed_when_no_offline_transport_is_configured(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id = _source_and_video(repository)
    evidence_id = _evidence(repository, video_id)
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        now=lambda: NOW,
    )

    with pytest.raises(ApiError) as error:
        app.handle(
            "POST",
            f"/api/v1/sources/{source_id}/videos/{video_id}/distill",
            json.dumps({"execution_id": "unavailable", "evidence_ids": [evidence_id]}).encode(),
        )

    assert error.value.code == "DISTILLATION_UNAVAILABLE"
