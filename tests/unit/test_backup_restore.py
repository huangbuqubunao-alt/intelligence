from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest

from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    DistillationExecutionStatus,
    OllamaLocalDistillationTransport,
    PersonalizedDistillationService,
)
from youtube_intel.orchestration import ProcessingPolicy, SourceType
from youtube_intel.source_run import (
    SourceRunAttentionReason,
    SourceRunChildState,
    SourceRunPriority,
    SourceRunState,
    SourceRunWrite,
)
from youtube_intel.state import (
    DistillationExecutionWrite,
    IntegrityConflict,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    StateStoreError,
)

NOW = datetime(2026, 9, 23, 8, 0, tzinfo=UTC)


def _waiting_model(repository: SQLiteStateRepository, execution_id: str = "waiting-model") -> str:
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id=execution_id, source_id="source-1", video_id="video-1",
            reason="MANUAL_CONTENT:cancel-test", use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="ollama", selected_model="qwen3:8b", output_language="en",
        ), now=NOW,
    )
    repository.finish_distillation_without_admission(
        execution_id=execution_id, status="WAITING_MODEL",
        budget_state="RUNTIME_BUDGET_ADMITTED", outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT",
        invocation_count=0, actual_provider=None, actual_model=None,
        input_tokens=None, output_tokens=None, cost_microunits=None, duration_ms=None, now=NOW,
    )
    return execution_id


def test_waiting_model_zero_invocation_cancel_is_durable_idempotent_and_backup_safe(tmp_path: Path) -> None:
    database, data_root, vault, repository, artifact = _workspace(tmp_path)
    _add_source(repository)
    execution_id = _waiting_model(repository)
    service = _service(tmp_path)
    assert service.readiness()["ready"] is False
    with repository._connect() as connection:
        checkpoint_before = tuple(connection.execute("SELECT * FROM distillation_execution_checkpoints").fetchone())
        ledger_before = tuple(connection.execute("SELECT * FROM distillation_resource_usage").fetchone())
    cancelled = repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW)
    assert cancelled.status == "CANCELLED"
    assert cancelled.invocation_count == 0
    assert cancelled.intelligence_id is None and cancelled.revision_id is None
    assert repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW) == cancelled
    with repository._connect() as connection:
        assert tuple(connection.execute("SELECT * FROM distillation_execution_checkpoints").fetchone()) == checkpoint_before
        assert tuple(connection.execute("SELECT * FROM distillation_resource_usage").fetchone()) == ledger_before
        assert connection.execute("SELECT COUNT(*) FROM distillation_waiting_model_cancellations").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("UPDATE distillation_waiting_model_cancellations SET cancelled_at=cancelled_at")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM distillation_waiting_model_cancellations")
    restarted = SQLiteStateRepository(database)
    restarted.initialize(now=NOW)
    assert restarted.get_distillation_execution(execution_id) == cancelled
    # The real unqualified transport remains closed; continuing a cancelled identity
    # must return before policy, budget, preflight or transport are consulted.
    transport = OllamaLocalDistillationTransport(settings=LocalScoringSettings(
        model="qwen3:8b", expected_model_digest="sha256:" + "0" * 64,
    ))
    resumed = PersonalizedDistillationService(
        restarted, None, transport, None, now=lambda: NOW,  # type: ignore[arg-type]
    ).continue_reserved_distillation(execution_id)
    assert resumed.status is DistillationExecutionStatus.CANCELLED
    assert resumed.invocation_count == 0
    assert service.readiness()["ready"] is True
    backup = service.create_backup()
    archive, _ = service.backup_download(backup.backup_id)
    repository.save_global_output_language(output_language="zh-CN", now=NOW)
    staged = service.stage_restore(archive.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(database)
    restored.initialize(now=NOW)
    assert restored.get_distillation_execution(execution_id) == cancelled
    assert restored.get_global_user_settings().output_language == "en"
    assert service.readiness()["ready"] is True
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact
    assert (vault / "owner-note.md").read_text() == "owner text stays outside restore"


def test_cancel_does_not_release_another_pending_execution(tmp_path: Path) -> None:
    _, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution_id = _waiting_model(repository)
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id="another-pending", source_id="source-1", video_id="video-1",
            reason="OTHER_TASK", use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="ollama", selected_model="qwen3:8b", output_language="en",
        ), now=NOW,
    )
    repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW)
    assert _service(tmp_path).readiness()["ready"] is False
    assert "DISTILLATION_ACTIVE" in _service(tmp_path).readiness()["reasons"]
    with pytest.raises(StateStoreError):
        repository.cancel_waiting_model_execution("another-pending", video_id="video-1", now=NOW)



@pytest.mark.parametrize("provider,model", [("moonshot", "kimi-k3"), ("moonshot", "kimi-k2.6"), ("openai", "gpt-4.1")])
@pytest.mark.parametrize("claimed", [False, True])
def test_cloud_model_wait_never_acquires_local_cancellation_authority(
    tmp_path: Path, provider: str, model: str, claimed: bool,
) -> None:
    _, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    request = dict(execution_id="cloud-wait", source_id="source-1", video_id="video-1",
                   reason=PersonalizedDistillationService._RESERVATION_REASON,
                   use_case=PersonalizedDistillationService._RESERVATION_USE_CASE,
                   selected_provider=provider, selected_model=model, output_language="en")
    repository.reserve_distillation_execution(DistillationExecutionWrite(**request), now=NOW)
    consent = repository.authorize_cloud_execution(
        authorization_id="cloud-wait-consent-1", execution_id="cloud-wait", provider=provider,
        model=model, verified_input_hash="a" * 64, consent_kind="USER_CONFIRMATION", now=NOW,
    )
    if claimed:
        assert repository.claim_reserved_distillation_execution(**request, now=NOW)
    # Preserve the existing cloud pre-dispatch accounting contract, including the
    # stale-preflight sequence found in review. It cannot confer local cancellation.
    repository.finish_distillation_without_admission(
        execution_id="cloud-wait", status="WAITING_MODEL", budget_state="RUNTIME_BUDGET_ADMITTED",
        outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT", invocation_count=0,
        actual_provider=None, actual_model=None, input_tokens=None, output_tokens=None,
        cost_microunits=None, duration_ms=None, now=NOW,
    )
    assert repository.can_cancel_waiting_model_execution("cloud-wait") is False
    with pytest.raises(StateStoreError):
        repository.cancel_waiting_model_execution("cloud-wait", video_id="video-1", now=NOW)
    with repository._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="zero-invocation"):
            connection.execute(
                "INSERT INTO distillation_waiting_model_cancellations "
                "SELECT execution_id, source_id, video_id, reason, use_case, selected_provider, "
                "selected_model, output_language, updated_at, budget_state, updated_at, "
                "'CANCELLED_BEFORE_MODEL_INVOCATION' FROM distillation_execution_checkpoints"
            )
        assert connection.execute("SELECT COUNT(*) FROM distillation_waiting_model_cancellations").fetchone()[0] == 0
    assert repository.get_distillation_execution("cloud-wait").status == "WAITING_MODEL"
    assert repository.get_cloud_execution_authorization("cloud-wait") == consent
    assert _service(tmp_path).readiness()["ready"] is False


def test_cancel_rejects_claimed_or_unknown_execution(tmp_path: Path) -> None:
    _, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution_id = _reserve_ambiguous_execution(repository)
    with pytest.raises(StateStoreError):
        repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW)
    assert repository.get_distillation_execution(execution_id).invocation_count == 1


@pytest.mark.parametrize("unsafe", ["missing-ledger", "unknown-budget", "called", "wrong-content", "unknown-outcome", "observed-cost"])
def test_model_wait_cancellation_requires_complete_zero_call_proof(tmp_path: Path, unsafe: str) -> None:
    _, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution_id = _waiting_model(repository)
    with repository._connect() as connection:
        if unsafe == "missing-ledger":
            connection.execute("DROP TRIGGER distillation_resource_usage_immutable_delete")
            connection.execute("DELETE FROM distillation_resource_usage")
        elif unsafe in {"unknown-budget", "called"}:
            connection.execute("DROP TRIGGER distillation_checkpoint_terminal_immutable")
            connection.execute("UPDATE distillation_execution_checkpoints SET " + (
                "budget_state='UNKNOWN'" if unsafe == "unknown-budget" else "invocation_count=1"
            ))
        elif unsafe in {"unknown-outcome", "observed-cost"}:
            connection.execute("DROP TRIGGER distillation_resource_usage_immutable_update")
            connection.execute("UPDATE distillation_resource_usage SET " + (
                "outcome='TRANSPORT_OUTCOME_UNKNOWN'" if unsafe == "unknown-outcome" else "cost_microunits=0"
            ))
    assert repository.can_cancel_waiting_model_execution(execution_id) is (unsafe == "wrong-content")
    if unsafe != "wrong-content":
        with repository._connect() as connection:
            with pytest.raises(sqlite3.IntegrityError, match="zero-invocation"):
                connection.execute(
                    "INSERT INTO distillation_waiting_model_cancellations "
                    "SELECT execution_id, source_id, video_id, reason, use_case, selected_provider, "
                    "selected_model, output_language, updated_at, budget_state, updated_at, "
                    "'CANCELLED_BEFORE_MODEL_INVOCATION' FROM distillation_execution_checkpoints"
                )
    with pytest.raises(StateStoreError):
        repository.cancel_waiting_model_execution(
            execution_id, video_id="different-content" if unsafe == "wrong-content" else "video-1", now=NOW,
        )
    assert _service(tmp_path).readiness()["ready"] is False


def test_cancelled_wait_parent_quiescence_requires_all_children_terminal(tmp_path: Path) -> None:
    _, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution_id = _waiting_model(repository)
    run_id = _ambiguous_parent_source_run(repository, execution_id=execution_id)
    with repository._connect() as connection:
        connection.execute(
            "INSERT INTO videos (video_id, channel_id, pipeline_status, pipeline_version, "
            "availability, discovered_at, updated_at) "
            "VALUES ('video-2', 'UC_TEST', 'DISCOVERED', 'fixture-v1', 'public', ?, ?)",
            (NOW.isoformat(), NOW.isoformat()),
        )
    repository.link_source_video("source-1", "video-2", discovered_at=NOW)
    repository.record_source_run_child(run_id, video_id="video-2", state=SourceRunChildState.PENDING,
                                       distillation_execution_id=None, now=NOW)
    repository.transition_source_run_child(run_id, video_id="video-1", to_state=SourceRunChildState.WAITING, now=NOW)
    assert repository.can_cancel_waiting_model_execution(execution_id) is False
    with pytest.raises(StateStoreError):
        repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW)
    repository.transition_source_run(run_id, to_state=SourceRunState.NEEDS_ATTENTION,
                                    attention_reason=SourceRunAttentionReason.MODEL_UNAVAILABLE, now=NOW)
    repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW)
    assert repository.get_source_run(run_id).state is SourceRunState.NEEDS_ATTENTION
    assert _service(tmp_path).readiness()["ready"] is False
    assert "SOURCE_RUN_ACTIVE" in _service(tmp_path).readiness()["reasons"]
    repository.transition_source_run_child(run_id, video_id="video-2", to_state=SourceRunChildState.FAILED, now=NOW)
    assert _service(tmp_path).readiness()["ready"] is True
    with pytest.raises(IntegrityConflict):
        repository.transition_source_run_child(run_id, video_id="video-1", to_state=SourceRunChildState.PENDING, now=NOW)


@pytest.mark.parametrize("state", ["WAITING_BUDGET", "PENDING"])
def test_cancellation_does_not_change_budget_or_pending_rules(tmp_path: Path, state: str) -> None:
    _, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution_id = _waiting_model(repository, "cancel-me")
    repository.reserve_distillation_execution(DistillationExecutionWrite(
        execution_id="keep-blocking", source_id="source-1", video_id="video-1",
        reason="OTHER_TASK", use_case="PERSONALIZED_INTELLIGENCE", selected_provider="ollama",
        selected_model="qwen3:8b", output_language="en",
    ), now=NOW)
    if state == "WAITING_BUDGET":
        repository.finish_distillation_without_admission(
            execution_id="keep-blocking", status=state, budget_state="BLOCKED",
            outcome="BUDGET_BLOCKED_BEFORE_TRANSPORT", invocation_count=0,
            actual_provider=None, actual_model=None, input_tokens=None, output_tokens=None,
            cost_microunits=None, duration_ms=None, now=NOW,
        )
    repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW)
    with pytest.raises(StateStoreError):
        repository.cancel_waiting_model_execution("keep-blocking", video_id="video-1", now=NOW)
    assert repository.get_distillation_execution("keep-blocking").status == state
    assert _service(tmp_path).readiness()["ready"] is False


@pytest.mark.parametrize("round", range(4))
def test_preflight_cancel_and_dispatch_claim_are_serialized(tmp_path: Path, round: int) -> None:
    _, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution_id = "cancel-claim-race"
    request = dict(execution_id=execution_id, source_id="source-1", video_id="video-1",
                   reason="RACE", use_case="PERSONALIZED_INTELLIGENCE", selected_provider="ollama",
                   selected_model="qwen3:8b", output_language="en")
    repository.reserve_distillation_execution(DistillationExecutionWrite(**request), now=NOW)
    barrier = Barrier(2)

    def claim() -> bool:
        barrier.wait(timeout=5)
        return repository.claim_reserved_distillation_execution(**request, now=NOW)

    def wait_then_cancel() -> bool:
        barrier.wait(timeout=5)
        try:
            repository.finish_distillation_without_admission(
                execution_id=execution_id, status="WAITING_MODEL", budget_state="RUNTIME_BUDGET_ADMITTED",
                outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT", invocation_count=0,
                actual_provider=None, actual_model=None, input_tokens=None, output_tokens=None,
                cost_microunits=None, duration_ms=None, now=NOW,
            )
            repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW)
            return True
        except StateStoreError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        started = pool.submit(claim)
        cancelled = pool.submit(wait_then_cancel)
        assert started.result(timeout=10) != cancelled.result(timeout=10)
    record = repository.get_distillation_execution(execution_id)
    assert (record.status, record.invocation_count) in {("CANCELLED", 0), ("PENDING", 1)}


@pytest.mark.parametrize("tamper", ["receipt", "ledger", "trigger"])
def test_cancelled_wait_corruption_cannot_pass_backup(tmp_path: Path, tamper: str) -> None:
    _, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution_id = _waiting_model(repository)
    repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW)
    with repository._connect() as connection:
        if tamper == "receipt":
            connection.execute("DROP TRIGGER waiting_model_cancellation_immutable_update")
            connection.execute("UPDATE distillation_waiting_model_cancellations SET selected_model='other'")
        elif tamper == "ledger":
            connection.execute("DROP TRIGGER distillation_resource_usage_immutable_update")
            connection.execute("UPDATE distillation_resource_usage SET outcome='UNKNOWN'")
        else:
            connection.execute("DROP TRIGGER waiting_model_cancelled_checkpoint_terminal")
    assert _service(tmp_path).readiness()["ready"] is False
    with pytest.raises(BackupRestoreError):
        _service(tmp_path).create_backup()


def test_schema36_backup_restore_upgrades_without_inventing_cancellations(tmp_path: Path, monkeypatch) -> None:
    load = SQLiteStateRepository._load_migrations
    with monkeypatch.context() as legacy:
        legacy.setattr(SQLiteStateRepository, "_load_migrations", lambda self: tuple(m for m in load(self) if m.version <= 36))
        database, _, _, repository, _ = _workspace(tmp_path)
        _add_source(repository)
        service = _service(tmp_path)
        backup = service.create_backup()
        archive, _ = service.backup_download(backup.backup_id)
        execution_id = _waiting_model(repository)
    with repository._connect() as connection:
        before = tuple(connection.execute("SELECT * FROM distillation_execution_checkpoints").fetchone())
    assert repository.initialize(now=NOW).version == 42
    with repository._connect() as connection:
        assert tuple(connection.execute("SELECT * FROM distillation_execution_checkpoints").fetchone()) == before
        assert connection.execute("SELECT COUNT(*) FROM distillation_waiting_model_cancellations").fetchone()[0] == 0
    assert service.readiness()["ready"] is False
    repository.cancel_waiting_model_execution(execution_id, video_id="video-1", now=NOW)
    staged = service.stage_restore(archive.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(database)
    assert restored.initialize(now=NOW).version == 42
    assert restored.get_distillation_execution(execution_id) is None
    assert service.readiness()["ready"] is True


def test_cancel_api_is_content_bound_idempotent_and_keeps_all_waits_visible(tmp_path: Path) -> None:
    from youtube_intel.local_api import ApiError, LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService

    _, data_root, vault, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    first = _waiting_model(repository, "wait-1")
    second = _waiting_model(repository, "wait-2")
    app = LocalApiApplication(repository, ProductOrchestrationService(repository, now=lambda: NOW),
                              data_root=data_root, vault_root=vault, now=lambda: NOW)
    # The low-level backup fixture uses ISO offsets; API readers require canonical UTC-Z.
    with repository._connect() as connection:
        timestamp = NOW.isoformat().replace("+00:00", "Z")
        connection.execute("UPDATE videos SET discovered_at=?, updated_at=?", (timestamp, timestamp))
        connection.execute("UPDATE artifacts SET created_at=?", (timestamp,))
    route = "/api/v1/videos/video-1/intelligence/cancel"
    body = json.dumps({"execution_id": first}).encode()
    status, response = app.handle("POST", route, body)
    assert status == 200 and response["execution"]["status"] == "CANCELLED"
    assert app.handle("POST", route, body) == (status, response)
    with pytest.raises(ApiError) as wrong_content:
        app.handle("POST", route.replace("video-1", "wrong"), body)
    assert wrong_content.value.status == 409
    with pytest.raises(ApiError) as extra_authority:
        app.handle("POST", route, json.dumps({"execution_id": second, "authorize": True}).encode())
    assert extra_authority.value.status == 422
    waiting = app.handle("GET", "/api/v1/videos/video-1")[1]["waiting_model_executions"]
    assert [item["execution_id"] for item in waiting] == [second]
    assert waiting[0]["can_cancel"] is True
    assert _service(tmp_path).readiness()["ready"] is False
    assert app.handle("POST", route, json.dumps({"execution_id": second}).encode())[0] == 200
    assert _service(tmp_path).readiness()["ready"] is True



def _workspace(tmp_path: Path) -> tuple[Path, Path, Path, SQLiteStateRepository, bytes]:
    database = tmp_path / "state.sqlite3"
    data_root = tmp_path / "data"
    data_root.mkdir()
    artifact = b"A real canonical transcript excerpt for fixture verification.\n"
    artifact_path = data_root / "transcripts" / "video-1.txt"
    artifact_path.parent.mkdir()
    artifact_path.write_bytes(artifact)
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO videos "
            "(video_id, channel_id, pipeline_status, pipeline_version, availability, discovered_at, updated_at) "
            "VALUES ('video-1', 'UC_TEST', 'DISCOVERED', 'fixture-v1', 'public', ?, ?)",
            (NOW.isoformat(), NOW.isoformat()),
        )
        connection.execute(
            "INSERT INTO artifacts "
            "(artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
            "VALUES ('artifact-1', 'artifact-key-1', 'video-1', NULL, 'transcript_canonical', 'DATA', 'transcripts/video-1.txt', ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            (hashlib.sha256(artifact).hexdigest(), NOW.isoformat()),
        )
    finally:
        connection.close()
    repository.save_global_output_language(output_language="en", now=NOW)
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "owner-note.md").write_text("owner text stays outside restore", encoding="utf-8")
    return database, data_root, vault, repository, artifact


def _service(tmp_path: Path) -> BackupRestoreService:
    return BackupRestoreService(database=tmp_path / "state.sqlite3", data_root=tmp_path / "data")


def _add_source(repository: SQLiteStateRepository) -> None:
    repository.create_source_subscription(
        SourceSubscriptionRecord(
            source_id="source-1",
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
    repository.link_source_video("source-1", "video-1", discovered_at=NOW)


def _reserve_ambiguous_execution(
    repository: SQLiteStateRepository, *, execution_id: str = "execution-ambiguous"
) -> str:
    reason = PersonalizedDistillationService._RESERVATION_REASON
    use_case = PersonalizedDistillationService._RESERVATION_USE_CASE
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id=execution_id,
            source_id="source-1",
            video_id="video-1",
            reason=reason,
            use_case=use_case,
            selected_provider="ollama",
            selected_model="qwen3:8b",
            output_language="en",
        ),
        now=NOW,
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id=execution_id,
        source_id="source-1",
        video_id="video-1",
        reason=reason,
        use_case=use_case,
        selected_provider="ollama",
        selected_model="qwen3:8b",
        output_language="en",
        now=NOW,
    )
    return execution_id


def _finish_ambiguous_execution(
    repository: SQLiteStateRepository, *, execution_id: str
) -> None:
    repository.finish_distillation_without_admission(
        execution_id=execution_id,
        status="AMBIGUOUS",
        budget_state="RUNTIME_BUDGET_ADMITTED",
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
def _ambiguous_parent_source_run(
    repository: SQLiteStateRepository, *, execution_id: str
) -> str:
    run = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id="source-1",
            command_id="manual-check-ambiguous",
            priority=SourceRunPriority.P2,
            created_at=NOW,
        )
    )
    repository.transition_source_run(
        run.run_id, to_state=SourceRunState.RUNNING, now=NOW
    )
    repository.record_source_run_child(
        run.run_id,
        video_id="video-1",
        state=SourceRunChildState.PENDING,
        distillation_execution_id=execution_id,
        now=NOW,
    )
    return run.run_id


def _finish_ambiguous_parent_source_run(
    repository: SQLiteStateRepository, *, run_id: str
) -> None:
    repository.transition_source_run_child(
        run_id,
        video_id="video-1",
        to_state=SourceRunChildState.AMBIGUOUS,
        now=NOW,
    )
    repository.transition_source_run(
        run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.AMBIGUOUS_EXTERNAL_OUTCOME,
        now=NOW,
    )


def _install_current_local_summary(database: Path, data_root: Path) -> None:
    value = b'{"summary":"verified fixture"}'
    stored_at = NOW.replace(tzinfo=None).isoformat()
    artifact_path = data_root / "analysis" / "video-1.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(value)
    repository = SQLiteStateRepository(database)
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO artifacts "
            "(artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
            "VALUES ('analysis-artifact-1', 'analysis-key-1', 'video-1', NULL, 'analysis_structured', 'DATA', 'analysis/video-1.json', ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            (hashlib.sha256(value).hexdigest(), stored_at),
        )
        connection.execute(
            "INSERT INTO current_content_summaries "
            "(video_id, result_identity, analysis_artifact_id, output_language, updated_at) "
            "VALUES ('video-1', NULL, 'analysis-artifact-1', 'en', ?)",
            (stored_at,),
        )
    finally:
        connection.close()


def test_create_backup_stage_confirm_restart_round_trip_and_vault_exclusion(
    tmp_path: Path,
) -> None:
    database, data_root, vault, repository, artifact_a = _workspace(tmp_path)
    service = _service(tmp_path)
    vault_before = (vault / "owner-note.md").read_bytes()

    assert service.readiness()["ready"] is True
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["exclusions"] == {
            "vault": True,
            "credentials": True,
            "model_weights": True,
        }
        assert {item.filename for item in archive.infolist()} == {
            "manifest.json",
            "database/state.sqlite",
            "data/transcripts/video-1.txt",
        }
        assert archive.read("data/transcripts/video-1.txt") == artifact_a

    repository.save_global_output_language(output_language="zh-CN", now=NOW)
    artifact_b = b"Changed transcript state B.\n"
    (data_root / "transcripts/video-1.txt").write_bytes(artifact_b)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE artifacts SET content_hash=? WHERE artifact_id='artifact-1'",
            (hashlib.sha256(artifact_b).hexdigest(),),
        )
    finally:
        connection.close()

    staged = service.stage_restore(archive_path.read_bytes())
    assert staged.preview["following_count"] == 0
    assert staged.preview["content_count"] == 1
    assert staged.preview["data_artifact_count"] == 1
    assert staged.preview["vault_excluded"] is True
    assert repository.get_global_user_settings().output_language == "zh-CN"  # type: ignore[union-attr]
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact_b

    service.confirm_restore(staged.restore_id)
    readiness_while_pending = service.readiness()
    assert readiness_while_pending["ready"] is False
    assert readiness_while_pending["reasons"] == ["RESTORE_PENDING"]
    assert "restart" in str(readiness_while_pending["message"]).lower()
    with pytest.raises(BackupRestoreError, match="no longer valid"):
        service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()

    restored = SQLiteStateRepository(database)
    restored.initialize(now=NOW)
    assert restored.get_global_user_settings().output_language == "en"  # type: ignore[union-attr]
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact_a
    assert (vault / "owner-note.md").read_bytes() == vault_before
    assert service.readiness()["last_restore"]["state"] == "APPLIED"  # type: ignore[index]
    assert not service.restore_pending


def test_cloud_authorization_and_unidentified_response_survive_backup_restore(
    tmp_path: Path,
) -> None:
    database, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution_id = "execution-cloud-response-unknown-model"
    reason = PersonalizedDistillationService._RESERVATION_REASON
    use_case = PersonalizedDistillationService._RESERVATION_USE_CASE
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id=execution_id,
            source_id="source-1",
            video_id="video-1",
            reason=reason,
            use_case=use_case,
            selected_provider="nvidia_nim",
            selected_model="moonshotai/kimi-k3",
            output_language="en",
        ),
        now=NOW,
    )
    authorization = repository.authorize_cloud_execution(
        authorization_id="authorization-backup-restore-1",
        execution_id=execution_id,
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        verified_input_hash="a" * 64,
        consent_kind="USER_CONFIRMATION",
        now=NOW,
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id=execution_id,
        source_id="source-1",
        video_id="video-1",
        reason=reason,
        use_case=use_case,
        selected_provider="nvidia_nim",
        selected_model="moonshotai/kimi-k3",
        output_language="en",
        now=NOW,
    )
    repository.finish_distillation_unidentified_http_response(
        execution_id=execution_id,
        budget_state="RUNTIME_BUDGET_ADMITTED",
        now=NOW,
    )
    usage = repository.get_distillation_resource_usage(execution_id)
    assert usage.status == "REJECTED_OUTPUT"
    assert usage.outcome == "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN"
    assert usage.actual_model is None
    assert usage.cost_microunits is None

    openai_execution_id = "execution-openai-cloud-consent-backup"
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id=openai_execution_id,
            source_id="source-1",
            video_id="video-1",
            reason=reason,
            use_case=use_case,
            selected_provider="openai",
            selected_model="gpt-4.1",
            output_language="en",
        ),
        now=NOW,
    )
    openai_authorization = repository.authorize_cloud_execution(
        authorization_id="authorization-openai-backup-restore-1",
        execution_id=openai_execution_id,
        provider="openai",
        model="gpt-4.1",
        verified_input_hash="b" * 64,
        consent_kind="USER_CONFIRMATION",
        now=NOW,
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id=openai_execution_id,
        source_id="source-1",
        video_id="video-1",
        reason=reason,
        use_case=use_case,
        selected_provider="openai",
        selected_model="gpt-4.1",
        output_language="en",
        now=NOW,
    )
    repository.finish_distillation_unidentified_http_response(
        execution_id=openai_execution_id,
        budget_state="RUNTIME_BUDGET_ADMITTED",
        now=NOW,
    )
    openai_usage = repository.get_distillation_resource_usage(openai_execution_id)
    assert openai_usage.status == "REJECTED_OUTPUT"
    assert openai_usage.outcome == "HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN"
    assert openai_usage.actual_provider == "openai"

    moonshot_execution_id = "execution-moonshot-k2-6-consent-backup"
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id=moonshot_execution_id,
            source_id="source-1",
            video_id="video-1",
            reason=reason,
            use_case=use_case,
            selected_provider="moonshot",
            selected_model="kimi-k2.6",
            output_language="zh-CN",
        ),
        now=NOW,
    )
    moonshot_authorization = repository.authorize_cloud_execution(
        authorization_id="authorization-moonshot-backup-restore-1",
        execution_id=moonshot_execution_id,
        provider="moonshot",
        model="kimi-k2.6",
        verified_input_hash="d" * 64,
        consent_kind="USER_CONFIRMATION",
        now=NOW,
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id=moonshot_execution_id,
        source_id="source-1",
        video_id="video-1",
        reason=reason,
        use_case=use_case,
        selected_provider="moonshot",
        selected_model="kimi-k2.6",
        output_language="zh-CN",
        now=NOW,
    )
    repository.finish_distillation_unidentified_http_response(
        execution_id=moonshot_execution_id,
        budget_state="RUNTIME_BUDGET_ADMITTED",
        now=NOW,
    )
    moonshot_usage = repository.get_distillation_resource_usage(moonshot_execution_id)
    assert moonshot_usage.status == "REJECTED_OUTPUT"
    assert moonshot_usage.actual_provider == "moonshot"
    assert moonshot_usage.actual_model is None

    failure_execution_id = "execution-moonshot-http-error-backup"
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id=failure_execution_id,
            source_id="source-1",
            video_id="video-1",
            reason=reason,
            use_case=use_case,
            selected_provider="moonshot",
            selected_model="kimi-k2.6",
            output_language="zh-CN",
        ),
        now=NOW,
    )
    failure_authorization = repository.authorize_cloud_execution(
        authorization_id="authorization-moonshot-http-error-backup",
        execution_id=failure_execution_id,
        provider="moonshot",
        model="kimi-k2.6",
        verified_input_hash="e" * 64,
        consent_kind="USER_CONFIRMATION",
        now=NOW,
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id=failure_execution_id,
        source_id="source-1",
        video_id="video-1",
        reason=reason,
        use_case=use_case,
        selected_provider="moonshot",
        selected_model="kimi-k2.6",
        output_language="zh-CN",
        now=NOW,
    )
    repository.finish_distillation_cloud_response_failure(
        execution_id=failure_execution_id,
        budget_state="RUNTIME_BUDGET_ADMITTED",
        outcome="CLOUD_HTTP_ERROR",
        http_status_code=429,
        now=NOW,
    )
    failure_usage = repository.get_distillation_resource_usage(failure_execution_id)
    assert failure_usage.outcome == "CLOUD_HTTP_ERROR"
    assert failure_usage.http_status_code == 429

    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None
    staged = service.stage_restore(archive_path.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()

    restored = SQLiteStateRepository(database)
    assert restored.initialize(now=NOW).version == 42
    assert restored.get_cloud_execution_authorization(execution_id) == authorization
    assert restored.get_cloud_execution_authorization(openai_execution_id) == openai_authorization
    assert restored.get_cloud_execution_authorization(moonshot_execution_id) == moonshot_authorization
    assert restored.get_distillation_resource_usage(execution_id) == usage
    assert restored.get_distillation_execution(execution_id).status == "REJECTED_OUTPUT"
    assert restored.get_distillation_resource_usage(openai_execution_id) == openai_usage
    assert restored.get_distillation_execution(openai_execution_id).status == "REJECTED_OUTPUT"
    assert restored.get_distillation_resource_usage(moonshot_execution_id) == moonshot_usage
    assert restored.get_distillation_execution(moonshot_execution_id).status == "REJECTED_OUTPUT"
    assert restored.get_cloud_execution_authorization(failure_execution_id) == failure_authorization
    assert restored.get_distillation_resource_usage(failure_execution_id) == failure_usage
    assert service.readiness()["last_restore"]["state"] == "APPLIED"  # type: ignore[index]


def test_download_rejects_tampered_content_disposition_filename(tmp_path: Path) -> None:
    _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    metadata_path = service.control_root / f"backup-{backup.backup_id}.json"
    metadata = json.loads(metadata_path.read_text("utf-8"))
    metadata["file_name"] = 'backup.zip"\r\nX-Injected: yes'
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    assert service.backup_download(backup.backup_id) is None


def _mutate_archive(source: bytes, mutation: str) -> bytes:
    output = __import__("io").BytesIO()
    with zipfile.ZipFile(__import__("io").BytesIO(source), "r") as original:
        members = [(item.filename, original.read(item)) for item in original.infolist()]
    manifest = json.loads(next(value for name, value in members if name == "manifest.json"))
    changed: list[tuple[str, bytes]] = []
    for name, value in members:
        if mutation == "manifest-hash" and name == "manifest.json":
            manifest["database"]["sha256"] = "0" * 64
            value = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        elif mutation == "sqlite-corrupt" and name == "database/state.sqlite":
            value = b"not a sqlite database"
            manifest["database"]["size_bytes"] = len(value)
            manifest["database"]["sha256"] = hashlib.sha256(value).hexdigest()
        elif mutation == "schema-incompatible" and name == "database/state.sqlite":
            database = __import__("tempfile").NamedTemporaryFile(suffix=".sqlite", delete=False)
            database.write(value)
            database.close()
            with sqlite3.connect(database.name) as connection:
                connection.execute("PRAGMA user_version=26")
            value = Path(database.name).read_bytes()
            Path(database.name).unlink()
            manifest["database"]["size_bytes"] = len(value)
            manifest["database"]["sha256"] = hashlib.sha256(value).hexdigest()
        elif mutation == "artifact-hash" and name.startswith("data/"):
            value += b"tampered"
        if mutation != "missing-artifact" or not name.startswith("data/"):
            changed.append((name, value))
    if mutation == "manifest-hash":
        changed = [
            (name, json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode())
            if name == "manifest.json" else (name, value)
            for name, value in changed
        ]
    if mutation == "extra-file":
        changed.append(("unexpected.txt", b"extra"))
    if mutation == "path-traversal":
        changed.append(("../outside.txt", b"escape"))
    if mutation == "duplicate-path":
        changed.append(changed[-1])
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in changed:
            archive.writestr(name, value)
    return output.getvalue()


@pytest.mark.parametrize(
    "mutation",
    [
        "manifest-hash",
        "sqlite-corrupt",
        "artifact-hash",
        "missing-artifact",
        "extra-file",
        "path-traversal",
        "duplicate-path",
        "schema-incompatible",
    ],
)
def test_invalid_backup_never_changes_live_data(tmp_path: Path, mutation: str) -> None:
    database, data_root, _vault, repository, artifact = _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None
    before_db = hashlib.sha256(database.read_bytes()).hexdigest()
    before_data = hashlib.sha256((data_root / "transcripts/video-1.txt").read_bytes()).hexdigest()

    with pytest.raises(BackupRestoreError):
        service.stage_restore(_mutate_archive(archive_path.read_bytes(), mutation))

    assert hashlib.sha256(database.read_bytes()).hexdigest() == before_db
    assert hashlib.sha256((data_root / "transcripts/video-1.txt").read_bytes()).hexdigest() == before_data
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact
    assert repository.get_global_user_settings().output_language == "en"  # type: ignore[union-attr]


def test_cancelled_staged_restore_leaves_live_data_untouched(tmp_path: Path) -> None:
    database, data_root, _vault, repository, artifact = _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None
    staged = service.stage_restore(archive_path.read_bytes())

    assert service.cancel_restore(staged.restore_id)
    assert not service.restore_pending
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact
    assert repository.get_global_user_settings().output_language == "en"  # type: ignore[union-attr]
    assert database.is_file()


def test_local_current_summary_uses_configured_trusted_reader_at_backup_and_stage(
    tmp_path: Path,
) -> None:
    database, data_root, _vault, _repository, _artifact = _workspace(tmp_path)
    _install_current_local_summary(database, data_root)
    validated: list[tuple[str, str]] = []

    def validate_current_summary(
        repository: SQLiteStateRepository,
        artifact_data_root: Path,
        video_id: str,
        artifact_id: str,
    ) -> object:
        artifact = repository.get_artifact(artifact_id)
        assert artifact is not None
        assert video_id == artifact.video_id == "video-1"
        payload = (artifact_data_root / artifact.relative_path).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == artifact.content_hash
        validated.append((video_id, artifact_id))
        return object()

    service = BackupRestoreService(
        database=database,
        data_root=data_root,
        current_local_summary_validator=validate_current_summary,
    )
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None
    staged = service.stage_restore(archive_path.read_bytes())
    assert service.cancel_restore(staged.restore_id)
    assert len(validated) == 2
    assert validated == [
        ("video-1", "analysis-artifact-1"),
        ("video-1", "analysis-artifact-1"),
    ]


def test_local_current_summary_fails_closed_without_trusted_reader(
    tmp_path: Path,
) -> None:
    database, data_root, _vault, _repository, _artifact = _workspace(tmp_path)
    _install_current_local_summary(database, data_root)

    with pytest.raises(BackupRestoreError, match="cannot be validated"):
        _service(tmp_path).create_backup()


@pytest.mark.parametrize("subdirectory", ["backups", "staging"])
def test_backup_service_rejects_symlinked_control_subdirectories(
    tmp_path: Path,
    subdirectory: str,
) -> None:
    database, data_root, _vault, _repository, _artifact = _workspace(tmp_path)
    control_root = tmp_path / "backup-control"
    control_root.mkdir()
    external_directory = tmp_path / "external"
    external_directory.mkdir()
    (control_root / subdirectory).symlink_to(external_directory, target_is_directory=True)

    with pytest.raises(BackupRestoreError, match="storage is unsafe"):
        BackupRestoreService(
            database=database,
            data_root=data_root,
            control_root=control_root,
        )

    assert list(external_directory.iterdir()) == []


def test_staged_data_tamper_is_rejected_before_confirmation(tmp_path: Path) -> None:
    database, data_root, _vault, repository, artifact = _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None
    staged = service.stage_restore(archive_path.read_bytes())
    staged_transcript = (
        service.staging_root / staged.restore_id / "data" / "transcripts" / "video-1.txt"
    )
    staged_transcript.write_bytes(b"tampered after inspection")
    before_database = hashlib.sha256(database.read_bytes()).hexdigest()

    with pytest.raises(BackupRestoreError):
        service.confirm_restore(staged.restore_id)

    assert not service.restore_pending
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before_database
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact
    assert repository.get_global_user_settings().output_language == "en"  # type: ignore[union-attr]


def test_staged_archive_identity_change_is_rejected_before_confirmation(tmp_path: Path) -> None:
    database, data_root, _vault, repository, artifact = _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None
    staged = service.stage_restore(archive_path.read_bytes())
    selected_archive = service.staging_root / staged.restore_id / "selected.zip"
    original = selected_archive.read_bytes()
    changed_archive = io.BytesIO(original)
    with zipfile.ZipFile(changed_archive, "a") as archive:
        archive.comment = b"same payload, different inspected archive identity"
    with zipfile.ZipFile(io.BytesIO(original)) as original_zip, zipfile.ZipFile(
        io.BytesIO(changed_archive.getvalue())
    ) as changed_zip:
        assert changed_zip.read("manifest.json") == original_zip.read("manifest.json")
    selected_archive.write_bytes(changed_archive.getvalue())
    before_database = hashlib.sha256(database.read_bytes()).hexdigest()

    with pytest.raises(BackupRestoreError, match="identity changed"):
        service.confirm_restore(staged.restore_id)

    assert not service.restore_pending
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before_database
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact
    assert repository.get_global_user_settings().output_language == "en"  # type: ignore[union-attr]


def test_activation_failure_rolls_back_database_and_data_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, data_root, _vault, repository, _artifact = _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None

    changed_artifact = b"Current state B transcript.\n"
    (data_root / "transcripts/video-1.txt").write_bytes(changed_artifact)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE artifacts SET content_hash=? WHERE artifact_id='artifact-1'",
            (hashlib.sha256(changed_artifact).hexdigest(),),
        )
    finally:
        connection.close()
    repository.save_global_output_language(output_language="zh-CN", now=NOW)
    staged = service.stage_restore(archive_path.read_bytes())
    service.confirm_restore(staged.restore_id)

    def fail_pair_validation(_manifest: dict[str, object]) -> None:
        database.with_name(database.name + "-wal").write_bytes(b"failed restore WAL")
        database.with_name(database.name + "-shm").write_bytes(b"failed restore SHM")
        raise BackupRestoreError("injected activation validation failure")

    monkeypatch.setattr(service, "_verify_live_pair", fail_pair_validation)
    service.recover_and_apply_pending_restore()

    restored_repository = SQLiteStateRepository(database)
    restored_repository.initialize(now=NOW)
    assert restored_repository.get_global_user_settings().output_language == "zh-CN"  # type: ignore[union-attr]
    assert (data_root / "transcripts/video-1.txt").read_bytes() == changed_artifact
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        content_hash = connection.execute(
            "SELECT content_hash FROM artifacts WHERE artifact_id='artifact-1'"
        ).fetchone()[0]
    assert content_hash == hashlib.sha256(changed_artifact).hexdigest()
    assert not service.restore_pending
    assert service.readiness()["last_restore"]["state"] == "ROLLED_BACK"  # type: ignore[index]


def test_validated_recovery_failure_rolls_back_database_and_data_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, data_root, _vault, repository, _artifact = _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None

    changed_artifact = b"Current state B transcript.\n"
    transcript_path = data_root / "transcripts/video-1.txt"
    transcript_path.write_bytes(changed_artifact)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE artifacts SET content_hash=? WHERE artifact_id='artifact-1'",
            (hashlib.sha256(changed_artifact).hexdigest(),),
        )
    finally:
        connection.close()
    repository.save_global_output_language(output_language="zh-CN", now=NOW)
    staged = service.stage_restore(archive_path.read_bytes())
    service.confirm_restore(staged.restore_id)

    verify_live_pair = service._verify_live_pair
    validations = 0

    def tamper_after_activation(manifest: dict[str, object]) -> None:
        nonlocal validations
        validations += 1
        if validations == 2:
            transcript_path.write_bytes(b"post-activation corruption")
        verify_live_pair(manifest)  # type: ignore[arg-type]

    monkeypatch.setattr(service, "_verify_live_pair", tamper_after_activation)
    service.recover_and_apply_pending_restore()

    restored_repository = SQLiteStateRepository(database)
    restored_repository.initialize(now=NOW)
    assert restored_repository.get_global_user_settings().output_language == "zh-CN"  # type: ignore[union-attr]
    assert transcript_path.read_bytes() == changed_artifact
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        content_hash = connection.execute(
            "SELECT content_hash FROM artifacts WHERE artifact_id='artifact-1'"
        ).fetchone()[0]
    assert content_hash == hashlib.sha256(changed_artifact).hexdigest()
    assert not service.restore_pending
    assert service.readiness()["last_restore"]["state"] == "ROLLED_BACK"  # type: ignore[index]


def test_activated_database_must_match_confirmed_snapshot_before_workers_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, data_root, _vault, repository, artifact = _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None

    repository.save_global_output_language(output_language="zh-CN", now=NOW)
    staged = service.stage_restore(archive_path.read_bytes())
    service.confirm_restore(staged.restore_id)

    verify_live_pair = service._verify_live_pair
    validations = 0

    def tamper_live_database(manifest: dict[str, object]) -> None:
        nonlocal validations
        validations += 1
        if validations == 1:
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE global_user_settings SET updated_at='2026-09-23T09:00:00Z'"
                )
        verify_live_pair(manifest)  # type: ignore[arg-type]

    monkeypatch.setattr(service, "_verify_live_pair", tamper_live_database)
    service.recover_and_apply_pending_restore()

    restored_repository = SQLiteStateRepository(database)
    restored_repository.initialize(now=NOW)
    assert restored_repository.get_global_user_settings().output_language == "zh-CN"  # type: ignore[union-attr]
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert not service.restore_pending
    assert service.readiness()["last_restore"]["state"] == "ROLLED_BACK"  # type: ignore[index]


def test_applied_restore_recovers_after_rollback_retirement_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, data_root, _vault, repository, artifact = _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None
    repository.save_global_output_language(output_language="zh-CN", now=NOW)
    staged = service.stage_restore(archive_path.read_bytes())
    service.confirm_restore(staged.restore_id)

    retire_rollback = service._retire_rollback

    def interrupt_retirement(_restore_id: str) -> None:
        raise OSError("simulated interruption after restore commit")

    monkeypatch.setattr(service, "_retire_rollback", interrupt_retirement)
    with pytest.raises(OSError, match="simulated interruption"):
        service.recover_and_apply_pending_restore()
    assert json.loads(service.marker_path.read_text("utf-8"))["state"] == "APPLIED"

    monkeypatch.setattr(service, "_retire_rollback", retire_rollback)
    service.recover_and_apply_pending_restore()

    restored_repository = SQLiteStateRepository(database)
    restored_repository.initialize(now=NOW)
    assert restored_repository.get_global_user_settings().output_language == "en"  # type: ignore[union-attr]
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact
    assert not service.restore_pending
    assert service.readiness()["last_restore"]["state"] == "APPLIED"  # type: ignore[index]


def test_quiescence_accepts_terminal_ambiguous_execution_and_its_exact_parent(
    tmp_path: Path,
) -> None:
    database, data_root, _vault, repository, _artifact = _workspace(tmp_path)
    _add_source(repository)
    execution_id = _reserve_ambiguous_execution(repository)
    run_id = _ambiguous_parent_source_run(repository, execution_id=execution_id)
    _finish_ambiguous_execution(repository, execution_id=execution_id)
    _finish_ambiguous_parent_source_run(repository, run_id=run_id)

    service = BackupRestoreService(database=database, data_root=data_root)
    readiness = service.readiness()

    assert readiness["ready"] is True
    usage = repository.get_distillation_resource_usage(execution_id)
    assert usage.status == "AMBIGUOUS"
    assert usage.outcome == "TRANSPORT_OUTCOME_UNKNOWN"
    assert usage.actual_provider is None
    assert usage.actual_model is None
    assert usage.cost_microunits is None
    backup = service.create_backup()
    assert backup.size_bytes > 0


def test_quiescence_fails_closed_for_legacy_source_run_schema_with_active_state(
    tmp_path: Path,
) -> None:
    database, data_root, _vault, repository, _artifact = _workspace(tmp_path)
    connection = repository._connect()
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("DROP TABLE source_runs")
        connection.execute("CREATE TABLE source_runs (state TEXT NOT NULL)")
        connection.execute("INSERT INTO source_runs (state) VALUES ('RUNNING')")
    finally:
        connection.close()

    service = BackupRestoreService(database=database, data_root=data_root)
    connection = repository._connect()
    try:
        reasons = service._quiescence_reasons(connection)
    finally:
        connection.close()

    assert "SOURCE_RUN_ACTIVE" in reasons


def test_quiescence_fails_closed_for_tampered_ambiguous_resource_truth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, data_root, _vault, repository, _artifact = _workspace(tmp_path)
    _add_source(repository)
    execution_id = _reserve_ambiguous_execution(repository)
    run_id = _ambiguous_parent_source_run(repository, execution_id=execution_id)
    _finish_ambiguous_execution(repository, execution_id=execution_id)
    _finish_ambiguous_parent_source_run(repository, run_id=run_id)
    original_get_usage = SQLiteStateRepository.get_distillation_resource_usage

    def forged_usage(
        current: SQLiteStateRepository, current_execution_id: str
    ):
        usage = original_get_usage(current, current_execution_id)
        if current_execution_id == execution_id:
            return replace(usage, outcome="FABRICATED_SUCCESS")
        return usage

    monkeypatch.setattr(
        SQLiteStateRepository, "get_distillation_resource_usage", forged_usage
    )

    readiness = BackupRestoreService(database=database, data_root=data_root).readiness()

    assert readiness["ready"] is False
    assert readiness["reasons"] == ["DATABASE_UNAVAILABLE"]


def test_quiescence_keeps_resumable_model_work_and_other_attention_runs_blocked(
    tmp_path: Path,
) -> None:
    database, data_root, _vault, repository, _artifact = _workspace(tmp_path)
    _add_source(repository)
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id="execution-waiting-model",
            source_id="source-1",
            video_id="video-1",
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="ollama",
            selected_model="qwen3:8b",
            output_language="en",
        ),
        now=NOW,
    )
    repository.finish_distillation_without_admission(
        execution_id="execution-waiting-model",
        status="WAITING_MODEL",
        budget_state="RUNTIME_BUDGET_ADMITTED",
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
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id="execution-waiting-budget",
            source_id="source-1",
            video_id="video-1",
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="ollama",
            selected_model="qwen3:8b",
            output_language="en",
        ),
        now=NOW,
    )
    repository.finish_distillation_without_admission(
        execution_id="execution-waiting-budget",
        status="WAITING_BUDGET",
        budget_state="RUNTIME_BUDGET_BLOCKED",
        outcome="BUDGET_BLOCKED_BEFORE_TRANSPORT",
        invocation_count=0,
        actual_provider=None,
        actual_model=None,
        input_tokens=None,
        output_tokens=None,
        cost_microunits=None,
        duration_ms=None,
        now=NOW,
    )
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id="execution-reserved-active",
            source_id="source-1",
            video_id="video-1",
            reason=PersonalizedDistillationService._RESERVATION_REASON,
            use_case=PersonalizedDistillationService._RESERVATION_USE_CASE,
            selected_provider="ollama",
            selected_model="qwen3:8b",
            output_language="en",
        ),
        now=NOW,
    )
    run = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id="source-1",
            command_id="manual-check-model-unavailable",
            priority=SourceRunPriority.P2,
            created_at=NOW,
        )
    )
    repository.transition_source_run(
        run.run_id, to_state=SourceRunState.RUNNING, now=NOW
    )
    repository.transition_source_run(
        run.run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.MODEL_UNAVAILABLE,
        now=NOW,
    )

    readiness = BackupRestoreService(database=database, data_root=data_root).readiness()

    assert readiness["ready"] is False
    assert "DISTILLATION_ACTIVE" in readiness["reasons"]
    assert "SOURCE_RUN_ACTIVE" in readiness["reasons"]


@pytest.mark.parametrize("tamper", [False, True])
def test_completed_no_new_attention_run_backup_restore_or_fail_closed(
    tmp_path: Path, tamper: bool,
) -> None:
    """A locally finished "no new Intelligence" extraction must not block Backup.

    The repository already projects the durable no-new result as completed,
    while its immutable raw checkpoint remains PENDING. The parent source-run
    quiescence query must recognize that completion too, and still reject a
    result whose Evidence binding is corrupt.
    """
    from youtube_intel.state import (
        EvidenceAvailability,
        EvidenceLineageKind,
        EvidenceRole,
        EvidenceWrite,
        build_evidence_id,
    )

    database, data_root, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    artifact_id = "artifact-1"
    evidence_id = build_evidence_id(
        video_id="video-1",
        artifact_id=artifact_id,
        start_ms=1000,
        end_ms=1500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    repository.create_evidence(
        EvidenceWrite(
            evidence_id=evidence_id,
            video_id="video-1",
            artifact_id=artifact_id,
            start_ms=1000,
            end_ms=1500,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
        ),
        now=NOW,
    )
    reason = PersonalizedDistillationService._RESERVATION_REASON
    use_case = PersonalizedDistillationService._RESERVATION_USE_CASE
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(
            execution_id="execution-no-new",
            source_id="source-1",
            video_id="video-1",
            reason=reason,
            use_case=use_case,
            selected_provider="ollama",
            selected_model="qwen3:8b",
            output_language="en",
        ),
        now=NOW,
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id="execution-no-new",
        source_id="source-1",
        video_id="video-1",
        reason=reason,
        use_case=use_case,
        selected_provider="ollama",
        selected_model="qwen3:8b",
        output_language="en",
        now=NOW,
    )
    repository.record_distillation_no_new_intelligence(
        execution_id="execution-no-new",
        evidence_ids=(evidence_id,),
        budget_state="RUNTIME_BUDGET_ADMITTED",
        actual_provider="ollama",
        actual_model="qwen3:8b",
        input_tokens=100,
        output_tokens=50,
        cost_microunits=0,
        duration_ms=1200,
        now=NOW,
    )

    run_id = _ambiguous_parent_source_run(repository, execution_id="execution-no-new")
    repository.transition_source_run_child(
        run_id, video_id="video-1", to_state=SourceRunChildState.COMPLETED, now=NOW
    )
    repository.transition_source_run(
        run_id, to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.MODEL_UNAVAILABLE, now=NOW
    )
    service = BackupRestoreService(database=database, data_root=data_root)
    if tamper:
        with sqlite3.connect(database) as connection:
            # Deliberately corrupt only this isolated fixture; production
            # immutability remains intact.
            connection.execute("DROP TRIGGER distillation_no_new_result_immutable_update")
            connection.execute("UPDATE distillation_no_new_intelligence_results SET evidence_set_hash = ?", ("0" * 64,))
        assert service.readiness()["ready"] is False
        with pytest.raises(BackupRestoreError):
            service.create_backup()
        return

    assert service.readiness()["ready"] is True
    before = repository.get_distillation_execution("execution-no-new")
    assert before is not None
    assert before.status == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    assert before.invocation_count == 1
    before_evidence = repository.get_evidence(evidence_id)
    assert before_evidence is not None
    before_usage = repository.get_distillation_resource_usage("execution-no-new")
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id) or (None, None)
    assert archive_path is not None
    staged = service.stage_restore(archive_path.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(database)
    assert restored.get_distillation_execution("execution-no-new") == before
    assert restored.get_evidence(evidence_id) == before_evidence
    assert restored.get_distillation_resource_usage("execution-no-new") == before_usage
    assert not restored.claim_reserved_distillation_execution(
        execution_id="execution-no-new", source_id="source-1", video_id="video-1",
        reason=reason, use_case=use_case, selected_provider="ollama",
        selected_model="qwen3:8b", output_language="en", now=NOW,
    )
    assert service.readiness()["ready"] is True


def test_preview_distinguishes_artifact_references_from_physical_data_files(tmp_path: Path) -> None:
    database, data_root, _vault, repository, artifact = _workspace(tmp_path)
    with repository._connect() as connection:
        connection.execute("INSERT INTO artifacts SELECT 'artifact-2', 'artifact-key-2', video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at FROM artifacts WHERE artifact_id='artifact-1'")
        before = tuple(connection.iterdump())
    service = _service(tmp_path)
    backup = service.create_backup()
    archive, _ = service.backup_download(backup.backup_id)
    assert backup.preview["data_artifact_count"] == 2
    assert backup.preview["data_file_count"] == 1
    assert backup.preview["data_file_size_bytes"] == len(artifact)
    assert backup.preview["data_size_bytes"] == len(artifact)
    with zipfile.ZipFile(archive) as saved:
        manifest = json.loads(saved.read("manifest.json"))
        assert manifest["format_version"] == 1
        assert manifest["counts"]["data_artifacts"] == 2
        assert manifest["counts"]["data_bytes"] == len(artifact)
        assert len(manifest["data_files"]) == 1
        assert [name for name in saved.namelist() if name.startswith("data/")] == ["data/transcripts/video-1.txt"]
    staged = service.stage_restore(archive.read_bytes())
    assert staged.preview == backup.preview
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    with SQLiteStateRepository(database)._connect() as connection:
        assert tuple(connection.iterdump()) == before
    assert (data_root / "transcripts/video-1.txt").read_bytes() == artifact


@pytest.mark.parametrize('version',[34,35,36,37,38,39,40,41])
def test_all_supported_schema_backups_restore_then_migrate_without_backfill(tmp_path,monkeypatch,version):
    load=SQLiteStateRepository._load_migrations
    with monkeypatch.context() as patch:
        patch.setattr(SQLiteStateRepository,'_load_migrations',lambda self:tuple(m for m in load(self) if m.version<=version))
        database,data_root,_vault,repository,_artifact=_workspace(tmp_path)
        with repository._connect() as connection:
            assert connection.execute('PRAGMA user_version').fetchone()[0]==version
            tables={row[0]:[tuple(value) for value in connection.execute(f'SELECT * FROM "{row[0]}"')] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        files={str(path.relative_to(data_root)):path.read_bytes() for path in data_root.rglob('*') if path.is_file()}
        service=_service(tmp_path)
        backup=service.create_backup()
        path,_=service.backup_download(backup.backup_id)
        payload=path.read_bytes()
    repository.initialize(now=NOW)
    repository.save_global_output_language(output_language='zh-CN',now=NOW)
    staged=service.stage_restore(payload)
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    restored=SQLiteStateRepository(database)
    with restored._connect() as connection:
        assert {row[0]:[tuple(value) for value in connection.execute(f'SELECT * FROM "{row[0]}"')] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}==tables
    assert {str(path.relative_to(data_root)):path.read_bytes() for path in data_root.rglob('*') if path.is_file()}==files
    assert restored.initialize(now=NOW).version==42
    assert restored.get_global_user_settings().output_language=='en'
    with restored._connect() as connection:
        for table,rows in tables.items():
            if table!='schema_migrations':
                assert [tuple(row) for row in connection.execute(f'SELECT * FROM "{table}"')]==rows
        assert [tuple(row) for row in connection.execute('SELECT * FROM schema_migrations WHERE version<=? ORDER BY version',(version,))]==tables['schema_migrations']
        assert all(connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0 for table in ('tracked_content_retry_requests','tracked_content_retry_executions','tracked_content_retry_files'))
        assert all(connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0 for table in ('distillation_zhipu_cloud_authorizations','distillation_zhipu_cloud_response_failures'))
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()
    assert {str(path.relative_to(data_root)):path.read_bytes() for path in data_root.rglob('*') if path.is_file()}==files
    assert len(files)==1


def _zhipu_request(repository, execution_id="zhipu-audit"):
    _add_source(repository)
    request = dict(execution_id=execution_id, source_id="source-1", video_id="video-1",
        reason=PersonalizedDistillationService._RESERVATION_REASON,
        use_case=PersonalizedDistillationService._RESERVATION_USE_CASE,
        selected_provider="zhipu_bigmodel", selected_model="glm-4.7-flash", output_language="en")
    repository.reserve_distillation_execution(DistillationExecutionWrite(**request), now=NOW)
    return request


def test_zhipu_dispatch_requires_its_own_exact_consent(tmp_path):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    with pytest.raises(sqlite3.IntegrityError, match="authorization"):
        repository.claim_reserved_distillation_execution(**request, now=NOW)
    assert repository.get_distillation_execution(request["execution_id"]).invocation_count == 0


def test_zhipu_429_audit_survives_full_backup_restore(tmp_path):
    database, data_root, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    consent = repository.authorize_cloud_execution(authorization_id="zhipu-audit-consent",
        execution_id=request["execution_id"], provider="zhipu_bigmodel", model="glm-4.7-flash",
        verified_input_hash="f" * 64, consent_kind="OWNER_QUALIFICATION", now=NOW)
    assert repository.claim_reserved_distillation_execution(**request, now=NOW)
    repository.finish_distillation_cloud_response_failure(execution_id=request["execution_id"],
        budget_state="ADMITTED", outcome="CLOUD_HTTP_ERROR", http_status_code=429, now=NOW)
    usage = repository.get_distillation_resource_usage(request["execution_id"])
    assert usage.http_status_code == 429 and usage.cost_microunits is None
    assert usage.actual_provider == "zhipu_bigmodel" and usage.actual_model is None
    with repository._connect() as connection:
        before = tuple(connection.iterdump())
    files = {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()}
    service = _service(tmp_path)
    backup = service.create_backup()
    archive, _ = service.backup_download(backup.backup_id)
    staged = service.stage_restore(archive.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    restarted = SQLiteStateRepository(database)
    assert restarted.initialize(now=NOW).version == 42
    assert restarted.get_cloud_execution_authorization(request["execution_id"]) == consent
    assert restarted.get_distillation_resource_usage(request["execution_id"]) == usage
    with restarted._connect() as connection:
        assert tuple(connection.iterdump()) == before
    assert {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()} == files


@pytest.mark.parametrize("outcome,status", [
    ("CLOUD_HTTP_ERROR", 429), ("CLOUD_HTTP_ERROR", 503), ("CLOUD_RESULT_PENDING", 202),
    ("HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN", 200), ("HTTP_RESPONSE_MODEL_IDENTITY_INVALID", 200),
    ("CLOUD_HTTP_RESPONSE_MALFORMED", 200),
])
def test_zhipu_finite_failure_receipts_are_immutable_and_restart_safe(tmp_path, outcome, status):
    database, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    consent = repository.authorize_cloud_execution(authorization_id="zhipu-audit-consent",
        execution_id=request["execution_id"], provider="zhipu_bigmodel", model="glm-4.7-flash",
        verified_input_hash="a" * 64, consent_kind="USER_CONFIRMATION", now=NOW)
    assert repository.claim_reserved_distillation_execution(**request, now=NOW)
    repository.finish_distillation_cloud_response_failure(execution_id=request["execution_id"],
        budget_state="ADMITTED", outcome=outcome, http_status_code=status, now=NOW)
    usage = repository.get_distillation_resource_usage(request["execution_id"])
    assert usage.outcome == outcome and usage.http_status_code == status
    assert usage.input_tokens is None and usage.output_tokens is None and usage.cost_microunits is None
    with repository._connect() as connection:
        for table in ("distillation_zhipu_cloud_authorizations", "distillation_zhipu_cloud_response_failures"):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(f"UPDATE {table} SET execution_id=execution_id")
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(f"DELETE FROM {table}")
    restarted = SQLiteStateRepository(database)
    restarted.initialize(now=NOW)
    assert restarted.get_cloud_execution_authorization(request["execution_id"]) == consent
    assert restarted.get_distillation_resource_usage(request["execution_id"]) == usage
    assert any(row.execution_id == request["execution_id"] for row in restarted.list_distillation_resource_usage())
    assert not restarted.claim_reserved_distillation_execution(**request, now=NOW)
    assert not restarted.can_cancel_waiting_model_execution(request["execution_id"])


@pytest.mark.parametrize("claimed", [False, True])
def test_zhipu_failure_before_claim_is_atomic_and_duplicate_claim_is_once(tmp_path, claimed):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    repository.authorize_cloud_execution(authorization_id="zhipu-audit-consent",
        execution_id=request["execution_id"], provider="zhipu_bigmodel", model="glm-4.7-flash",
        verified_input_hash="a" * 64, consent_kind="USER_CONFIRMATION", now=NOW)
    if claimed:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: repository.claim_reserved_distillation_execution(**request, now=NOW), range(2)))
        assert sorted(results) == [False, True]
        assert _service(tmp_path).readiness()["ready"] is False
        repository.finish_distillation_without_admission(execution_id=request["execution_id"],
            status="AMBIGUOUS", budget_state="UNKNOWN", outcome="TRANSPORT_OUTCOME_UNKNOWN", invocation_count=1,
            actual_provider=None, actual_model=None, input_tokens=None, output_tokens=None,
            cost_microunits=None, duration_ms=None, http_status_code=None, now=NOW)
        assert repository.get_distillation_resource_usage(request["execution_id"]).status == "AMBIGUOUS"
    else:
        with repository._connect() as connection:
            before = tuple(connection.iterdump())
        with pytest.raises(StateStoreError, match="claimed authorized"):
            repository.finish_distillation_cloud_response_failure(execution_id=request["execution_id"],
                budget_state="ADMITTED", outcome="CLOUD_HTTP_ERROR", http_status_code=429, now=NOW)
        with repository._connect() as connection:
            assert tuple(connection.iterdump()) == before
    assert not repository.can_cancel_waiting_model_execution(request["execution_id"])


@pytest.mark.parametrize("mutation", ["missing_guard", "weakened_union", "missing_table", "orphan_failure", "missing_consent"])
def test_zhipu_audit_corruption_blocks_backup_without_changing_data(tmp_path, mutation):
    _, data_root, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    repository.authorize_cloud_execution(authorization_id="zhipu-audit-consent",
        execution_id=request["execution_id"], provider="zhipu_bigmodel", model="glm-4.7-flash",
        verified_input_hash="a" * 64, consent_kind="USER_CONFIRMATION", now=NOW)
    assert repository.claim_reserved_distillation_execution(**request, now=NOW)
    repository.finish_distillation_cloud_response_failure(execution_id=request["execution_id"],
        budget_state="ADMITTED", outcome="CLOUD_HTTP_ERROR", http_status_code=429, now=NOW)
    with repository._connect() as connection:
        if mutation == "missing_guard":
            connection.execute("DROP TRIGGER local_text_input_proofs_zhipu_cloud_denied")
        elif mutation == "weakened_union":
            connection.execute("DROP TRIGGER distillation_resource_usage_http_status_bound")
            connection.execute("CREATE TRIGGER distillation_resource_usage_http_status_bound BEFORE INSERT ON distillation_resource_usage BEGIN SELECT 1; END;")
        elif mutation == "missing_table":
            connection.execute("DROP TABLE distillation_zhipu_cloud_response_failures")
        elif mutation == "missing_consent":
            connection.execute("DROP TRIGGER distillation_zhipu_cloud_authorization_immutable_delete")
            connection.execute("DELETE FROM distillation_zhipu_cloud_authorizations")
        else:
            connection.execute("DROP TRIGGER distillation_zhipu_cloud_response_failure_immutable_update")
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("UPDATE distillation_zhipu_cloud_response_failures SET execution_id='missing-execution'")
        before = tuple(connection.iterdump())
    files = {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()}
    with pytest.raises(BackupRestoreError):
        _service(tmp_path).create_backup()
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before
    assert {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()} == files


def test_zhipu_rehashed_archive_with_missing_guard_is_refused_without_live_changes(tmp_path):
    database, data_root, _, repository, _ = _workspace(tmp_path)
    service = _service(tmp_path)
    backup = service.create_backup()
    archive_path, _ = service.backup_download(backup.backup_id)
    with zipfile.ZipFile(archive_path) as archive:
        infos = {info.filename: info for info in archive.infolist()}
        members = {name: archive.read(name) for name in infos}
    snapshot = tmp_path / "corruption-fixture.sqlite"
    snapshot.write_bytes(members["database/state.sqlite"])
    with sqlite3.connect(snapshot) as connection:
        connection.execute("DROP TRIGGER distillation_zhipu_cloud_dispatch_requires_authorization")
    connection.close()  # Flush the isolated snapshot's WAL before repackaging its bytes.
    changed_database = snapshot.read_bytes()
    assert changed_database != members["database/state.sqlite"]
    members["database/state.sqlite"] = changed_database
    manifest = json.loads(members["manifest.json"])
    manifest["database"]["size_bytes"] = len(members["database/state.sqlite"])
    manifest["database"]["sha256"] = hashlib.sha256(members["database/state.sqlite"]).hexdigest()
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in members.items():
            archive.writestr(infos[name], value)
    with repository._connect() as connection:
        before = tuple(connection.iterdump())
    files = {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()}
    with pytest.raises(BackupRestoreError, match="persistence constraints"):
        service.stage_restore(payload.getvalue())
    assert not service.restore_pending
    with SQLiteStateRepository(database)._connect() as connection:
        assert tuple(connection.iterdump()) == before
    assert {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()} == files


def test_zhipu_direct_invoked_insert_and_unknown_model_cannot_bypass_consent(tmp_path):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    with repository._connect() as connection:
        columns = [str(row["name"]) for row in connection.execute("PRAGMA table_info(distillation_execution_checkpoints)")]
        values = dict(connection.execute("SELECT * FROM distillation_execution_checkpoints").fetchone())
        values.update(execution_id="forged-invoked", invocation_count=1)
        with pytest.raises(sqlite3.IntegrityError, match="authorization"):
            connection.execute(f"INSERT INTO distillation_execution_checkpoints ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", tuple(values[key] for key in columns))
    unknown = {**request, "execution_id": "zhipu-paid-model-denied", "selected_model": "glm-5.3-flash"}
    repository.reserve_distillation_execution(DistillationExecutionWrite(**unknown), now=NOW)
    with pytest.raises(ValueError, match="authorization identity"):
        repository.authorize_cloud_execution(authorization_id="zhipu-paid-model-consent",
            execution_id=unknown["execution_id"], provider="zhipu_bigmodel", model=unknown["selected_model"],
            verified_input_hash="a" * 64, consent_kind="USER_CONFIRMATION", now=NOW)
    with pytest.raises(StateStoreError, match="finite audit authority"):
        repository.claim_reserved_distillation_execution(**unknown, now=NOW)
    with repository._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="authorization"):
            connection.execute("UPDATE distillation_execution_checkpoints SET invocation_count=1,budget_state='DISPATCH_CLAIMED' WHERE execution_id=?", (unknown["execution_id"],))
        assert connection.execute("SELECT invocation_count FROM distillation_execution_checkpoints WHERE execution_id=?", (unknown["execution_id"],)).fetchone()[0] == 0


def _insert_zhipu_consent_with_raw_identity(connection, execution_id, authorization_id, **overrides):
    timestamp = connection.execute("SELECT updated_at FROM distillation_execution_checkpoints WHERE execution_id=?", (execution_id,)).fetchone()[0]
    connection.execute("INSERT INTO distillation_zhipu_cloud_authorizations "
        "(authorization_id,execution_id,provider,model,verified_input_hash,consent_kind,disclosure_version,cost_status,authorized_at) "
        "VALUES (?,?,'zhipu_bigmodel','glm-4.7-flash',?,'USER_CONFIRMATION','m12-cloud-intelligence-v1','UNKNOWN',?)",
        (authorization_id, execution_id, overrides.get("verified_input_hash", "a" * 64), overrides.get("authorized_at", timestamp)))


def _corrupt_zhipu_audit_row(connection, table, changes):
    """Isolated raw corruption: weaken one table, retain its guards and other row fields."""
    assert table in {"distillation_zhipu_cloud_authorizations", "distillation_zhipu_cloud_response_failures"}
    connection.row_factory = sqlite3.Row
    rows = [dict(row) for row in connection.execute(f"SELECT * FROM {table}")]
    columns = list(connection.execute(f"PRAGMA table_info({table})"))
    guards = [row[0] for row in connection.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND tbl_name=? ORDER BY name", (table,))]
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute(f"DROP TABLE {table}")
    definition = ",".join(f'"{row["name"]}" {row["type"]}' + (" PRIMARY KEY" if row["pk"] else "") for row in columns)
    connection.execute(f"CREATE TABLE {table} ({definition})")
    for row in rows:
        row.update(changes)
        connection.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))
    for guard in guards:
        connection.execute(guard)
    connection.execute("PRAGMA foreign_keys=ON")


def _corrupt_zhipu_authorization_identity(connection, **changes):
    _corrupt_zhipu_audit_row(connection, "distillation_zhipu_cloud_authorizations", changes or {"authorization_id": None})


def test_zhipu_null_authorization_identity_cannot_pass_sql_checks(tmp_path):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    with repository._connect() as connection:
        before = tuple(connection.iterdump())
        with pytest.raises(sqlite3.IntegrityError, match="NOT NULL"):
            _insert_zhipu_consent_with_raw_identity(connection, request["execution_id"], None)
        assert tuple(connection.iterdump()) == before
        for table, key in (("distillation_zhipu_cloud_authorizations", "authorization_id"), ("distillation_zhipu_cloud_response_failures", "execution_id")):
            assert next(row["notnull"] for row in connection.execute(f"PRAGMA table_info({table})") if row["name"] == key) == 1


def test_zhipu_corrupt_null_consent_is_not_coerced_to_a_valid_string(tmp_path):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    with repository._connect() as connection:
        _corrupt_zhipu_authorization_identity(connection)
        _insert_zhipu_consent_with_raw_identity(connection, request["execution_id"], None)
        before = tuple(connection.iterdump())
    with pytest.raises(StateStoreError, match="identity"):
        repository.get_cloud_execution_authorization(request["execution_id"])
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before


@pytest.mark.parametrize("field,value", [
    ("authorization_id", b"blob-identity-sixteen"),
    ("verified_input_hash", b"a" * 64),
    ("authorized_at", "0" * 20),
    ("authorized_at", "2026-02-30T08:00:00.000000Z"),
    ("authorized_at", "2028-02-30T08:00:00.000000Z"),
    ("authorized_at", "2028-01-01T24:00:00.000000Z"),
    ("authorized_at", "2028-01-01T08:00:00.abc123Z"),
    ("authorized_at", "2026-09-23T08:00:00Z"),
    ("authorized_at", "2026-09-23T10:00:00.000000+02:00"),
])
def test_zhipu_scalar_consent_sql_rejects_untyped_or_invalid_utc(tmp_path, field, value):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    parameters = {"authorization_id": "valid-scalar-consent", field: value}
    with repository._connect() as connection:
        before = tuple(connection.iterdump())
        with pytest.raises(sqlite3.IntegrityError):
            _insert_zhipu_consent_with_raw_identity(connection, request["execution_id"], **parameters)
        assert tuple(connection.iterdump()) == before


@pytest.mark.parametrize("received_at", ["0" * 20, "9999-99-99T99:99:99Z", "2026-02-30T08:00:00.000000Z"])
def test_zhipu_scalar_failure_sql_rejects_invalid_utc(tmp_path, received_at):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    repository.authorize_cloud_execution(authorization_id="valid-scalar-consent",
        execution_id=request["execution_id"], provider="zhipu_bigmodel", model="glm-4.7-flash",
        verified_input_hash="a" * 64, consent_kind="USER_CONFIRMATION", now=NOW)
    assert repository.claim_reserved_distillation_execution(**request, now=NOW)
    with repository._connect() as connection:
        connection.execute("UPDATE distillation_execution_checkpoints SET status='REJECTED_OUTPUT' WHERE execution_id=?", (request["execution_id"],))
        before = tuple(connection.iterdump())
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO distillation_zhipu_cloud_response_failures "
                "(execution_id,actual_provider,actual_model,status,outcome,http_status_code,input_tokens,output_tokens,cost_microunits,duration_ms,received_at) "
                "VALUES (?,'zhipu_bigmodel',NULL,'REJECTED_OUTPUT','CLOUD_HTTP_ERROR',429,NULL,NULL,NULL,NULL,?)",
                (request["execution_id"], received_at))
        assert tuple(connection.iterdump()) == before


def _corrupt_zhipu_scalar_preserving_schema(connection, table, field, value):
    """Only isolated adversarial copies bypass CHECK/immutability, then restore all SQL."""
    guard = {
        "distillation_zhipu_cloud_authorizations": "distillation_zhipu_cloud_authorization_immutable_update",
        "distillation_zhipu_cloud_response_failures": "distillation_zhipu_cloud_response_failure_immutable_update",
    }[table]
    assert field in {"authorization_id", "verified_input_hash", "authorized_at", "received_at"}
    schema_before = [tuple(row) for row in connection.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name")]
    sql = connection.execute("SELECT sql FROM sqlite_master WHERE name=?", (guard,)).fetchone()[0]
    connection.execute("PRAGMA ignore_check_constraints=ON")
    connection.execute(f"DROP TRIGGER {guard}")
    try:
        connection.execute(f"UPDATE {table} SET {field}=?", (value,))
    finally:
        connection.execute(sql)
        connection.execute("PRAGMA ignore_check_constraints=OFF")
    assert [tuple(row) for row in connection.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name")] == schema_before


@pytest.mark.parametrize("field,value", [
    ("authorization_id", b"blob-identity-sixteen"), ("verified_input_hash", b"a" * 64),
    ("authorized_at", "0" * 20), ("authorized_at", "2026-02-30T08:00:00.000000Z"),
    ("authorized_at", "2026-09-23T08:00:00Z"), ("authorized_at", "2026-09-23T10:00:00.000000+02:00"),
])
def test_zhipu_raw_corrupt_consent_scalar_closes_reader_claim_and_verifier(tmp_path, field, value):
    _, data_root, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    repository.authorize_cloud_execution(authorization_id="valid-scalar-consent", execution_id=request["execution_id"],
        provider="zhipu_bigmodel", model="glm-4.7-flash", verified_input_hash="a" * 64,
        consent_kind="USER_CONFIRMATION", now=NOW)
    with repository._connect() as connection:
        _corrupt_zhipu_scalar_preserving_schema(connection, "distillation_zhipu_cloud_authorizations", field, value)
        before = tuple(connection.iterdump())
    files = {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()}
    with pytest.raises(StateStoreError, match="identity"):
        repository.get_cloud_execution_authorization(request["execution_id"])
    with pytest.raises(StateStoreError, match="identity"):
        repository.claim_reserved_distillation_execution(**request, now=NOW)
    with repository._connect() as connection:
        with pytest.raises(StateStoreError, match="identity"):
            repository.verify_cloud_audit_database(connection)
        assert tuple(connection.iterdump()) == before
    assert {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()} == files


@pytest.mark.parametrize("received_at", ["0" * 20, "9999-99-99T99:99:99Z", "2026-02-30T08:00:00.000000Z"])
def test_zhipu_raw_corrupt_failure_utc_closes_usage_and_verifier(tmp_path, received_at):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    repository.authorize_cloud_execution(authorization_id="valid-scalar-consent", execution_id=request["execution_id"],
        provider="zhipu_bigmodel", model="glm-4.7-flash", verified_input_hash="a" * 64,
        consent_kind="USER_CONFIRMATION", now=NOW)
    assert repository.claim_reserved_distillation_execution(**request, now=NOW)
    repository.finish_distillation_cloud_response_failure(execution_id=request["execution_id"], budget_state="ADMITTED",
        outcome="CLOUD_HTTP_ERROR", http_status_code=429, now=NOW)
    with repository._connect() as connection:
        _corrupt_zhipu_scalar_preserving_schema(connection, "distillation_zhipu_cloud_response_failures", "received_at", received_at)
        before = tuple(connection.iterdump())
    with pytest.raises(StateStoreError, match="identity"):
        repository.get_distillation_resource_usage(request["execution_id"])
    with repository._connect() as connection:
        with pytest.raises(StateStoreError, match="identity"):
            repository.verify_cloud_audit_database(connection)
        assert tuple(connection.iterdump()) == before


@pytest.mark.parametrize("authorized_at", [NOW + timedelta(seconds=1, microseconds=123456), datetime(2028, 2, 29, 12, 34, 56, 123456, tzinfo=UTC)])
def test_zhipu_formatter_utc_and_preclaim_time_progression_remain_legal(tmp_path, authorized_at):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    consent = repository.authorize_cloud_execution(authorization_id="valid-formatter-consent", execution_id=request["execution_id"],
        provider="zhipu_bigmodel", model="glm-4.7-flash", verified_input_hash="a" * 64,
        consent_kind="USER_CONFIRMATION", now=authorized_at)
    assert consent.authorized_at == authorized_at
    assert repository.claim_reserved_distillation_execution(**request, now=authorized_at + timedelta(seconds=1))
    repository.finish_distillation_cloud_response_failure(execution_id=request["execution_id"], budget_state="ADMITTED",
        outcome="CLOUD_HTTP_ERROR", http_status_code=429, now=authorized_at + timedelta(seconds=2))
    with repository._connect() as connection:
        repository.verify_cloud_audit_database(connection)


@pytest.mark.parametrize("table,field,value", [
    ("distillation_zhipu_cloud_authorizations", "authorization_id", None),
    ("distillation_zhipu_cloud_authorizations", "authorization_id", b"blob-identity-sixteen"),
    ("distillation_zhipu_cloud_authorizations", "verified_input_hash", b"a" * 64),
    ("distillation_zhipu_cloud_authorizations", "authorized_at", "0" * 20),
    ("distillation_zhipu_cloud_response_failures", "received_at", "9999-99-99T99:99:99Z"),
])
def test_zhipu_rehashed_scalar_corruption_cannot_restore_or_change_live_data(tmp_path, table, field, value):
    _, data_root, _, repository, _ = _workspace(tmp_path)
    request = _zhipu_request(repository)
    repository.authorize_cloud_execution(authorization_id="valid-scalar-consent", execution_id=request["execution_id"],
        provider="zhipu_bigmodel", model="glm-4.7-flash", verified_input_hash="a" * 64,
        consent_kind="USER_CONFIRMATION", now=NOW)
    assert repository.claim_reserved_distillation_execution(**request, now=NOW)
    repository.finish_distillation_cloud_response_failure(execution_id=request["execution_id"], budget_state="ADMITTED",
        outcome="CLOUD_HTTP_ERROR", http_status_code=429, now=NOW)
    service = _service(tmp_path)
    backup = service.create_backup()
    path, _ = service.backup_download(backup.backup_id)
    with zipfile.ZipFile(path) as archive:
        infos = {info.filename: info for info in archive.infolist()}
        members = {name: archive.read(name) for name in infos}
    snapshot = tmp_path / "scalar-corruption-snapshot.sqlite"
    snapshot.write_bytes(members["database/state.sqlite"])
    with sqlite3.connect(snapshot) as connection:
        connection.row_factory = sqlite3.Row
        if value is None:
            _corrupt_zhipu_audit_row(connection, table, {field: value})
        else:
            _corrupt_zhipu_scalar_preserving_schema(connection, table, field, value)
    connection.close()
    changed = snapshot.read_bytes()
    assert changed != members["database/state.sqlite"]
    members["database/state.sqlite"] = changed
    manifest = json.loads(members["manifest.json"])
    manifest["database"]["size_bytes"] = len(changed)
    manifest["database"]["sha256"] = hashlib.sha256(changed).hexdigest()
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(infos[name], content)
    with repository._connect() as connection:
        before = tuple(connection.iterdump())
    files = {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()}
    with pytest.raises(BackupRestoreError, match="persistence constraints"):
        service.stage_restore(payload.getvalue())
    assert not service.restore_pending
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before
    assert {str(p.relative_to(data_root)): p.read_bytes() for p in data_root.rglob("*") if p.is_file()} == files
