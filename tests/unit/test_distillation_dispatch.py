from __future__ import annotations

import io
import json
import urllib.error
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    BudgetDecision,
    DistillationCommand,
    DistillationExecutionStatus,
    OllamaLocalDistillationTransport,
    PersonalizedDistillationService,
    VerifiedDistillationInput,
    VerifiedEvidenceInput,
)
from youtube_intel.orchestration import ProcessingPolicy, SourceType
from youtube_intel.state import (
    DistillationExecutionWrite,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
)

NOW = datetime(2026, 9, 24, 8, 0, tzinfo=UTC)
MODEL_DIGEST = "sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
EXECUTION_ID = "distillation:reservation:v3:test-dispatch-boundary"
SOURCE_ID = "source-1"
VIDEO_ID = "video-1"


def _verified_input() -> VerifiedDistillationInput:
    return VerifiedDistillationInput(
        source_display_name="Public source",
        video_id=VIDEO_ID,
        video_title="A public title",
        evidence=(
            VerifiedEvidenceInput(
                evidence_id="evidence-1",
                start_ms=1_000,
                end_ms=2_000,
                excerpt="The product launched in April.",
                excerpt_hash="a" * 64,
                timed_transcript_id="transcript-1",
                timed_transcript_hash="b" * 64,
            ),
        ),
        personalization=(),
        source_focus_rules=(),
        source_ignore_rules=(),
        distillation_style=None,
        selected_provider="ollama",
        selected_model="qwen3:8b",
        semantic_hash="c" * 64,
        output_language="en",
    )


class _AllowedBudget:
    def check(self, _command: DistillationCommand) -> BudgetDecision:
        return BudgetDecision(allowed=True, state="RUNTIME_BUDGET_ADMITTED")


def _workspace(tmp_path: Path) -> tuple[SQLiteStateRepository, DistillationCommand]:
    database = tmp_path / "state.sqlite3"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    repository.create_source_subscription(
        SourceSubscriptionRecord(
            source_id=SOURCE_ID,
            source_type=SourceType.CHANNEL,
            canonical_url="https://www.youtube.com/channel/UC_TEST",
            channel_id="UC_TEST",
            video_id=None,
            display_name="Public source",
            enabled=True,
            processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
            last_checked_at=None,
            last_success_at=None,
            last_error_code=None,
            last_error_message=None,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO videos "
            "(video_id, channel_id, pipeline_status, pipeline_version, availability, discovered_at, updated_at) "
            "VALUES (?, ?, 'DISCOVERED', 'fixture-v1', 'public', ?, ?)",
            (VIDEO_ID, "UC_TEST", NOW.isoformat(), NOW.isoformat()),
        )
    finally:
        connection.close()

    command = DistillationCommand(
        execution_id=EXECUTION_ID,
        source_id=SOURCE_ID,
        video_id=VIDEO_ID,
        evidence_ids=("evidence-1",),
        reason=PersonalizedDistillationService._RESERVATION_REASON,
        use_case=PersonalizedDistillationService._RESERVATION_USE_CASE,
        selected_provider="ollama",
        selected_model="qwen3:8b",
        output_language="en",
    )
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id=EXECUTION_ID,
            source_id=SOURCE_ID,
            video_id=VIDEO_ID,
            reason=command.reason,
            use_case=command.use_case,
            selected_provider=command.selected_provider,
            selected_model=command.selected_model,
            output_language=command.output_language,
        ),
        now=NOW,
    )
    return repository, command


def _service(
    repository: SQLiteStateRepository,
) -> PersonalizedDistillationService:
    return PersonalizedDistillationService(
        repository,
        source_policy=None,  # type: ignore[arg-type]
        transport=OllamaLocalDistillationTransport(
            settings=LocalScoringSettings(
                model="qwen3:8b", expected_model_digest=MODEL_DIGEST
            ),
            production_qualified=True,
        ),
        budget=_AllowedBudget(),  # type: ignore[arg-type]
        now=lambda: NOW,
    )


def test_known_model_unavailable_is_waiting_before_dispatch_and_never_ambiguous(
    tmp_path: Path, monkeypatch
) -> None:
    repository, command = _workspace(tmp_path)
    requests: list[tuple[str, str]] = []

    class Response(io.BytesIO):
        pass

    def urlopen(request, timeout):
        assert timeout == 300.0
        requests.append((request.get_method(), urlsplit(request.full_url).path))
        return Response(b'{"models": []}')

    monkeypatch.setattr("youtube_intel.distillation.urllib.request.urlopen", urlopen)
    service = _service(repository)
    service._reserved_command_from_record = lambda _record: (  # type: ignore[method-assign]
        command,
        _verified_input(),
    )
    service._eligible = lambda _command: True  # type: ignore[method-assign]
    service._legal_evidence = lambda _command: True  # type: ignore[method-assign]
    service._projection = lambda value: value  # type: ignore[method-assign]
    service._transport_permits = lambda _value, **_kwargs: True  # type: ignore[method-assign]

    result = service.continue_reserved_distillation(EXECUTION_ID)

    execution = repository.get_distillation_execution(EXECUTION_ID)
    usage = repository.get_distillation_resource_usage(EXECUTION_ID)
    assert result.status is DistillationExecutionStatus.WAITING_MODEL
    assert result.invocation_count == 0
    assert execution is not None
    assert execution.status == "WAITING_MODEL"
    assert execution.invocation_count == 0
    assert usage.status == "WAITING_MODEL"
    assert usage.invocation_count == 0
    assert requests == [("GET", "/api/tags")]


def test_claimed_dispatch_failure_is_ambiguous_and_restart_never_redispatches(
    tmp_path: Path, monkeypatch
) -> None:
    repository, command = _workspace(tmp_path)
    requests: list[tuple[str, str]] = []
    tag_checks = 0

    class Response(io.BytesIO):
        pass

    def urlopen(request, timeout):
        nonlocal tag_checks
        assert timeout == 300.0
        path = urlsplit(request.full_url).path
        method = request.get_method()
        requests.append((method, path))
        if path == "/api/tags":
            tag_checks += 1
            models = (
                [{"name": "qwen3:8b", "digest": MODEL_DIGEST.removeprefix("sha256:")}]
                if tag_checks == 1
                else []
            )
            return Response(json.dumps({"models": models}).encode())
        assert (method, path) == ("POST", "/api/chat")
        raise urllib.error.URLError("connection ended after generation request dispatch")

    monkeypatch.setattr("youtube_intel.distillation.urllib.request.urlopen", urlopen)
    service = _service(repository)
    service._reserved_command_from_record = lambda _record: (  # type: ignore[method-assign]
        command,
        _verified_input(),
    )
    service._eligible = lambda _command: True  # type: ignore[method-assign]
    service._legal_evidence = lambda _command: True  # type: ignore[method-assign]
    service._projection = lambda value: value  # type: ignore[method-assign]
    service._transport_permits = lambda _value, **_kwargs: True  # type: ignore[method-assign]

    result = service.continue_reserved_distillation(EXECUTION_ID)

    assert result.status is DistillationExecutionStatus.AMBIGUOUS
    assert result.invocation_count == 1
    assert requests == [("GET", "/api/tags"), ("POST", "/api/chat")]
    execution = repository.get_distillation_execution(EXECUTION_ID)
    usage = repository.get_distillation_resource_usage(EXECUTION_ID)
    assert execution is not None
    assert execution.status == "AMBIGUOUS"
    assert execution.invocation_count == 1
    assert usage.status == "AMBIGUOUS"
    assert usage.invocation_count == 1
    assert usage.outcome == "TRANSPORT_OUTCOME_UNKNOWN"
    assert usage.actual_provider is None
    assert usage.actual_model is None
    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.cost_microunits is None

    # Simulate a fresh app service after restart. A terminal ambiguous identity
    # is returned before transport preflight or generation can run again.
    monkeypatch.setattr(
        "youtube_intel.distillation.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("terminal execution must not call Ollama after restart")
        ),
    )
    restarted_repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    restarted = _service(restarted_repository)
    replay = restarted.continue_reserved_distillation(EXECUTION_ID)
    assert replay.status is DistillationExecutionStatus.AMBIGUOUS
    assert replay.invocation_count == 1
    assert requests == [("GET", "/api/tags"), ("POST", "/api/chat")]


def test_definite_truncated_chat_response_is_rejected_not_ambiguous(
    tmp_path: Path, monkeypatch
) -> None:
    repository, command = _workspace(tmp_path)
    requests: list[str] = []

    class Response(io.BytesIO):
        pass

    def urlopen(request, timeout):
        assert timeout == 300.0
        path = urlsplit(request.full_url).path
        requests.append(path)
        if path == "/api/tags":
            return Response(json.dumps({"models": [
                {"name": "qwen3:8b", "digest": MODEL_DIGEST.removeprefix("sha256:")}
            ]}).encode())
        assert path == "/api/chat"
        return Response(json.dumps({
            "model": "qwen3:8b", "message": {"content": '{"core_conclusion":'},
            "done": True, "done_reason": "length",
            "prompt_eval_count": 3_850, "eval_count": 1_200,
        }).encode())

    monkeypatch.setattr("youtube_intel.distillation.urllib.request.urlopen", urlopen)
    service = _service(repository)
    service._reserved_command_from_record = lambda _record: (  # type: ignore[method-assign]
        command, _verified_input(),
    )
    service._eligible = lambda _command: True  # type: ignore[method-assign]
    service._legal_evidence = lambda _command: True  # type: ignore[method-assign]
    service._projection = lambda value: value  # type: ignore[method-assign]
    service._transport_permits = lambda _value, **_kwargs: True  # type: ignore[method-assign]

    result = service.continue_reserved_distillation(EXECUTION_ID)

    assert result.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert result.invocation_count == 1
    usage = repository.get_distillation_resource_usage(EXECUTION_ID)
    assert usage.outcome == "LOCAL_RESPONSE_TRUNCATED"
    assert usage.actual_provider == "ollama"
    assert usage.actual_model == "qwen3:8b"
    assert usage.input_tokens == 3_850
    assert usage.output_tokens == 1_200
    assert requests == ["/api/tags", "/api/chat"]
    restarted = _service(SQLiteStateRepository(tmp_path / "state.sqlite3"))
    assert restarted.continue_reserved_distillation(EXECUTION_ID).status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert requests == ["/api/tags", "/api/chat"]
