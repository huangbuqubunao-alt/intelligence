from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import zipfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
from youtube_intel.distillation import PersonalizedDistillationService
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
    SourceSubscriptionRecord,
    SQLiteStateRepository,
)

NOW = datetime(2026, 9, 23, 8, 0, tzinfo=UTC)


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
    assert restored.initialize(now=NOW).version == 28
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
