"""Complete synthetic source; no model, HTTP or qualification authority."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.distillation import PersonalizedDistillationService
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.local_distillation_profile import (
    FIXED_RUNTIME_PROFILE_ID,
    resolve_profile,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    build_evidence_id,
)

support = _load_module("test_task022_personalized_distillation")
NOW = support.NOW


def workspace(tmp_path: Path, count: int = 114, texts=None):
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    source_id, video_id = support._source_and_video(repository, "abcdefghijk")
    root = tmp_path / "data"
    root.mkdir()
    repository.bind_source_storage(root)
    cues = tuple(
        TimedTranscriptCueWrite(
            i * 1000, i * 1000 + 900, f"Source fact {i}." if texts is None else texts[i]
        )
        for i in range(count)
    )
    wire = "\n".join(c.text for c in cues).encode()
    (root / "canonical.txt").write_bytes(wire)
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="canonical-long",
            artifact_key="canonical-long",
            video_id=video_id,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path="canonical.txt",
            content_hash=hashlib.sha256(wire).hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    timed = TimedTranscriptWrite.from_cues(
        video_id=video_id, canonical_artifact_id="canonical-long", cues=cues
    )
    repository.create_timed_transcript(timed, now=NOW)
    for i, cue in enumerate(cues):
        evidence = EvidenceWrite(
            evidence_id=build_evidence_id(
                video_id=video_id,
                artifact_id="canonical-long",
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
                role=EvidenceRole.PRIMARY_ORIGINAL,
            ),
            video_id=video_id,
            artifact_id="canonical-long",
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
        )
        repository.create_evidence_with_text_binding(
            evidence,
            EvidenceTextBindingWrite.from_timed_transcript(
                evidence=evidence,
                timed_transcript_id=timed.timed_transcript_id,
                start_cue_index=i,
                end_cue_index=i + 1,
                excerpt=cue.text,
            ),
            now=NOW,
        )
    ExtractiveSummaryService(repository, root).create(video_id, now=NOW)
    transport = support._FakeTransport(
        "must never execute",
        available=False,
        actual_provider="ollama",
        actual_model=resolve_profile(FIXED_RUNTIME_PROFILE_ID).model,
    )
    transport.local_profile_id = FIXED_RUNTIME_PROFILE_ID
    service = PersonalizedDistillationService(
        repository,
        support.SourcePolicyApplicationService(repository, now=lambda: NOW),
        transport,
        support._FakeBudget(True),
        now=lambda: NOW,
    )
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        data_root=root,
        distillation_service=service,
        now=lambda: NOW,
    )
    return repository, root, source_id, video_id, service, app, transport


def test_ordinary_content_full_source_wait_cancel_and_restart(tmp_path):
    repository, _root, _sid, vid, service, app, transport = workspace(tmp_path)
    status, response = app.handle(
        "POST",
        f"/api/v1/videos/{vid}/intelligence",
        body=json.dumps({"command_id": "full-source"}).encode(),
    )
    execution_id = response["execution"]["execution_id"]
    assert status == 202
    assert execution_id.startswith("distillation:long-timed-v1:")
    wait = repository.get_distillation_execution(execution_id)
    assert wait.status == "WAITING_MODEL" and wait.invocation_count == 0
    assert repository.can_cancel_waiting_model_execution(execution_id)
    status, response = app.handle(
        "POST",
        f"/api/v1/videos/{vid}/intelligence/cancel",
        body=json.dumps({"execution_id": execution_id}).encode(),
    )
    assert status == 200 and response["execution"]["status"] == "CANCELLED"
    assert (
        service.continue_reserved_distillation(execution_id).status.value == "CANCELLED"
    )
    assert transport.calls == 0 and repository.list_distillation_cards() == ()


def _inventory(repository, root):
    with repository._connect() as connection:
        tables = {
            r[0]: sorted(
                [
                    tuple(row)
                    for row in connection.execute('SELECT * FROM "' + r[0] + '"')
                ],
                key=repr,
            )
            for r in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    files = {
        p.relative_to(root).as_posix(): (
            p.stat().st_size,
            hashlib.sha256(p.read_bytes()).hexdigest(),
        )
        for p in root.rglob("*")
        if p.is_file()
    }
    return tables, files


def test_cancelled_full_source_backup_restore_all_tables_and_data(tmp_path):
    from youtube_intel.backup_restore import BackupRestoreService

    repository, root, sid, vid, service, _app, transport = workspace(tmp_path)
    first = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="restore",
    )
    repository.cancel_waiting_model_execution(first.execution_id, video_id=vid, now=NOW)
    before = _inventory(repository, root)
    backup = BackupRestoreService(database=repository._database_path, data_root=root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    preview = backup.stage_restore(package.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert _inventory(repository, root) == before
    restarted = SQLiteStateRepository(repository._database_path)
    restarted.bind_source_storage(root)
    assert (
        restarted.get_distillation_execution(first.execution_id).status == "CANCELLED"
    )
    assert transport.calls == 0


def test_reserved_family_all_generic_writers_refuse_before_mutation(tmp_path):
    import inspect
    from types import SimpleNamespace

    import pytest

    from youtube_intel.state import StateStoreError

    repository, root, _sid, _vid, _service, _app, _transport = workspace(tmp_path, 21)
    before = _inventory(repository, root)
    for name in (
        "begin_distillation_execution",
        "reserve_distillation_execution",
        "claim_reserved_distillation_execution",
        "claim_distillation_execution",
        "finish_distillation_without_admission",
        "finish_distillation_unidentified_http_response",
        "finish_distillation_cloud_response_failure",
        "record_distillation_no_new_intelligence",
        "admit_distillation",
    ):
        method = getattr(repository, name)
        kwargs = {
            key: None
            for key, arg in inspect.signature(method).parameters.items()
            if arg.default is inspect.Parameter.empty
        }
        if "execution" in kwargs:
            kwargs["execution"] = SimpleNamespace(
                execution_id="distillation:long-timed-v999:unknown"
            )
        else:
            kwargs["execution_id"] = "distillation:long-timed-v999:unknown"
        with pytest.raises(StateStoreError, match="dedicated"):
            method(**kwargs)
    assert _inventory(repository, root) == before


def test_transaction_failure_after_proof_or_usage_leaves_no_half_reservation(
    tmp_path, monkeypatch
):
    import pytest

    from youtube_intel import long_distillation_persistence as long

    repository, root, sid, vid, service, _app, transport = workspace(tmp_path, 21)
    before = _inventory(repository, root)
    original = long._checkpoint_wait

    def fail(*args):
        original(*args)
        raise RuntimeError("injected after wait and ledger")

    monkeypatch.setattr(long, "_checkpoint_wait", fail)
    with pytest.raises(RuntimeError, match="injected"):
        service.reserve_distillation_execution(
            source_id=sid,
            video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid),
            manual_command_id="rollback",
        )
    assert _inventory(repository, root) == before and transport.calls == 0


def test_long_cancellation_does_not_reopen_settled_no_child_attention_run(tmp_path):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.source_run import (
        SourceRunAttentionReason,
        SourceRunPriority,
        SourceRunState,
        SourceRunWrite,
    )

    repository, root, sid, vid, service, _app, _transport = workspace(tmp_path, 21)
    run = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=sid,
            command_id="old-no-child",
            priority=SourceRunPriority.P0,
            created_at=NOW,
        )
    )
    repository.transition_source_run(
        run.run_id, to_state=SourceRunState.RUNNING, now=NOW
    )
    repository.transition_source_run(
        run.run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED,
        now=NOW,
    )
    backup = BackupRestoreService(database=repository._database_path, data_root=root)
    assert backup.readiness()["ready"]
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="new-long-wait",
    )
    assert not backup.readiness()["ready"]
    repository.cancel_waiting_model_execution(
        reservation.execution_id, video_id=vid, now=NOW
    )
    assert backup.readiness()["ready"]
    assert repository.get_source_run(run.run_id).state is SourceRunState.NEEDS_ATTENTION


def test_source_run_uses_complete_candidates_and_cancelled_child_stays_waiting(
    tmp_path,
):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.processing_orchestrator import DurableProcessingOrchestrator
    from youtube_intel.source_run import SourceRunChildState, SourceRunState

    repository, root, sid, vid, service, _app, transport = workspace(tmp_path, 21)
    orchestrator = DurableProcessingOrchestrator(
        repository,
        source_policy=service._source_policy,
        distillation=service,
        now=lambda: NOW,
    )
    run = orchestrator.enqueue_manual_check_now(
        source_id=sid, command_id="full-source-run"
    )
    result = orchestrator.resume(run.run_id)
    assert (
        result.state is SourceRunState.NEEDS_ATTENTION
        and result.attention_reason.value == "MODEL_UNAVAILABLE"
    )
    child = repository.list_source_run_children(run.run_id)[0]
    assert child.state is SourceRunChildState.WAITING
    assert repository.can_cancel_waiting_model_execution(
        child.distillation_execution_id
    )
    repository.cancel_waiting_model_execution(
        child.distillation_execution_id, video_id=vid, now=NOW
    )
    assert repository.list_source_run_children(run.run_id)[0] == child
    assert orchestrator.resume(run.run_id) == result
    assert BackupRestoreService(
        database=repository._database_path, data_root=root
    ).readiness()["ready"]
    assert transport.calls == 0


def test_history_survives_legitimate_summary_and_policy_pointer_refresh(tmp_path):
    from youtube_intel.state import DistillationStyle

    repository, root, sid, vid, service, _app, _transport = workspace(tmp_path, 21)
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="historical",
    )
    original = repository.current_local_summary_pointer(vid).artifact_id
    summaries = ExtractiveSummaryService(repository, root)
    result = summaries._result(vid, use_timed_candidates=False)
    wire = result.model_dump_json().encode()
    relative = "new-valid-v1.json"
    (root / relative).write_bytes(wire)
    artifact = repository.get_artifact(original)
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=f"summary/{result.request_hash}/structured",
            artifact_key=f"summary/{result.request_hash}/structured",
            video_id=vid,
            job_id=None,
            kind=ArtifactKind.ANALYSIS_STRUCTURED,
            storage_root=StorageRoot.DATA,
            relative_path=relative,
            content_hash=hashlib.sha256(wire).hexdigest(),
            provider="extractive-source",
            model=result.model,
            producer_version="extractive-summary-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    repository.promote_current_local_summary(
        video_id=vid,
        artifact_id=f"summary/{result.request_hash}/structured",
        output_language="en",
        now=NOW,
    )
    service._source_policy.update_global(
        command_id="new-valid-policy",
        initial_history_count=10,
        per_run_max_new_videos=10,
        focus_rules=("a new legitimate policy",),
        ignore_rules=(),
        distillation_style=DistillationStyle.BALANCED,
    )
    assert (
        repository.get_distillation_execution(reservation.execution_id).status
        == "WAITING_MODEL"
    )
    repository.cancel_waiting_model_execution(
        reservation.execution_id, video_id=vid, now=NOW
    )
    assert (
        repository.get_distillation_execution(reservation.execution_id).status
        == "CANCELLED"
    )
    (root / artifact.relative_path).write_bytes(b"corrupt retained original Summary")
    import pytest

    from youtube_intel.state import StateStoreError

    with pytest.raises(StateStoreError):
        repository.get_distillation_execution(reservation.execution_id)
    assert not repository.can_cancel_waiting_model_execution(reservation.execution_id)


def test_bad_available_original_parent_cannot_hide_behind_artifact_or_binding_join(
    tmp_path,
):
    import pytest

    from youtube_intel.state import StateStoreError

    repository, root, sid, vid, service, _app, _transport = workspace(tmp_path, 21)
    (root / "bad-parent.txt").write_bytes(b"not a canonical source")
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="bad-parent",
            artifact_key="bad-parent",
            video_id=vid,
            job_id=None,
            kind=ArtifactKind.ANALYSIS_STRUCTURED,
            storage_root=StorageRoot.DATA,
            relative_path="bad-parent.txt",
            content_hash=hashlib.sha256(b"not a canonical source").hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    with repository._connect() as c:
        c.execute(
            "INSERT INTO evidence(evidence_id,video_id,artifact_id,start_ms,end_ms,lineage_kind,role,language,availability,created_at) VALUES('bad-extra',?,'bad-parent',999000,999900,'ORIGINAL_TRANSCRIPT','PRIMARY_ORIGINAL','en','AVAILABLE',?)",
            (vid, NOW.isoformat()),
        )
    assert len(service.reservation_evidence_ids(vid)) == 22
    with pytest.raises(StateStoreError):
        service.reserve_distillation_execution(
            source_id=sid,
            video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid),
            manual_command_id="bad-extra",
        )
    with repository._connect() as c:
        assert (
            c.execute("SELECT count(*) FROM long_distillation_input_proofs").fetchone()[
                0
            ]
            == 0
        )


def test_unused_untimed_canonical_is_retained_without_becoming_second_authority(
    tmp_path,
):
    repository, root, sid, vid, service, _app, _transport = workspace(tmp_path, 21)
    (root / "unused.txt").write_bytes(b"old unused canonical\n")
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="unused",
            artifact_key="unused",
            video_id=vid,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path="unused.txt",
            content_hash=hashlib.sha256(b"old unused canonical\n").hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="unused-retained",
    )
    assert (
        repository.get_distillation_execution(reservation.execution_id).status
        == "WAITING_MODEL"
    )
    assert (
        repository.get_artifact("unused").deleted_at is None
        and (root / "unused.txt").read_bytes() == b"old unused canonical\n"
    )


def test_content_capability_and_post_select_same_unqualified_long_profile(tmp_path):
    from youtube_intel.long_distillation_profile import PROFILE_ID

    repository, _root, _sid, vid, _service, app, _transport = workspace(tmp_path, 21)
    app._local_distillation_capabilities = lambda: tuple(
        {
            "profile_id": FIXED_RUNTIME_PROFILE_ID,
            "model": resolve_profile(FIXED_RUNTIME_PROFILE_ID).model,
            "scope": scope,
            "output_language": language,
            "status": "NOT_QUALIFIED",
        }
        for scope in ("YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT")
        for language in ("en", "zh-CN")
    )
    status, detail = app.handle("GET", f"/api/v1/videos/{vid}")
    assert status == 200 and detail["manual_intelligence_eligible"]
    assert detail["local_intelligence"]["profile_id"] == PROFILE_ID
    assert detail["local_intelligence"]["qualification_status"] == "NOT_QUALIFIED"
    assert detail["local_intelligence"]["request_state"] == "WAITING_MODEL"
    status, response = app.handle(
        "POST",
        f"/api/v1/videos/{vid}/intelligence",
        body=json.dumps({"command_id": "ordinary-status"}).encode(),
    )
    assert status == 202 and response["execution"]["status"] == "WAITING_MODEL"
    with repository._connect() as c:
        proof = c.execute(
            "SELECT profile_wire FROM long_distillation_input_proofs"
        ).fetchone()[0]
        assert json.loads(proof)["profile_id"] == PROFILE_ID


def test_budget_wait_remains_uncancellable_and_blocks_backup(tmp_path):
    from youtube_intel.backup_restore import BackupRestoreService

    repository, root, sid, vid, service, _app, transport = workspace(tmp_path, 21)
    service._budget = support._FakeBudget(False, state="EXHAUSTED")
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="budget",
    )
    assert (
        repository.get_distillation_execution(reservation.execution_id).status
        == "WAITING_BUDGET"
    )
    assert not repository.can_cancel_waiting_model_execution(reservation.execution_id)
    assert not BackupRestoreService(
        database=repository._database_path, data_root=root
    ).readiness()["ready"]
    assert transport.calls == 0


def test_concurrent_cancel_and_generic_claim_cannot_dispatch_or_duplicate_receipts(
    tmp_path,
):
    import concurrent.futures

    from youtube_intel.state import StateStoreError

    repository, root, sid, vid, service, _app, transport = workspace(tmp_path, 21)
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="race",
    )

    def cancel(_):
        return repository.cancel_waiting_model_execution(
            reservation.execution_id, video_id=vid, now=NOW
        ).status

    def claim():
        try:
            repository.claim_reserved_distillation_execution(
                execution_id=reservation.execution_id,
                source_id=sid,
                video_id=vid,
                reason="race",
                use_case="PERSONALIZED_INTELLIGENCE",
                selected_provider="ollama",
                selected_model=transport.actual_model,
                now=NOW,
            )
        except StateStoreError:
            return "CLOSED"
        raise AssertionError("generic long claim was accepted")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as workers:
        futures = [workers.submit(cancel, n) for n in range(2)] + [
            workers.submit(claim)
        ]
        assert [f.result() for f in futures] == ["CANCELLED", "CANCELLED", "CLOSED"]
    with repository._connect() as c:
        assert (
            c.execute(
                "SELECT count(*) FROM distillation_waiting_model_cancellations WHERE execution_id=?",
                (reservation.execution_id,),
            ).fetchone()[0]
            == 1
        )
    assert transport.calls == 0


@pytest.mark.parametrize("version", range(34, 41))
def test_every_legacy_backup_restore_then_normal41_upgrade_retains_all_rows_and_data(
    tmp_path, monkeypatch, version
):
    from youtube_intel.backup_restore import BackupRestoreService

    migrations = SQLiteStateRepository(tmp_path / "unused")._load_migrations()
    with monkeypatch.context() as patch:
        patch.setattr(
            SQLiteStateRepository,
            "_load_migrations",
            lambda _: tuple(m for m in migrations if m.version <= version),
        )
        repository, root, _sid, _vid, _service, _app, _transport = workspace(
            tmp_path, 2
        )
    before = _inventory(repository, root)
    backup = BackupRestoreService(database=repository._database_path, data_root=root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    preview = backup.stage_restore(package.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert _inventory(repository, root) == before
    assert repository.initialize(now=NOW).version == 43
    after, files = _inventory(repository, root)
    assert {
        k: v for k, v in after.items() if k in before[0] and k != "schema_migrations"
    } == {k: v for k, v in before[0].items() if k != "schema_migrations"}
    assert (
        files == before[1]
        and after["long_distillation_input_proofs"] == []
        and after["long_distillation_completion_receipts"] == []
    )


@pytest.mark.parametrize(
    "damage",
    [
        "proof",
        "ledger",
        "proof+ledger",
        "proof+card+ledger+receipt",
        "unknown-family",
        "malformed-family",
    ],
)
def test_rehashed_backup_cannot_remove_long_provenance_and_downgrade_to_generic(
    tmp_path, damage
):
    import io
    import sqlite3
    import zipfile

    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService

    repository, root, sid, vid, service, _app, _transport = workspace(tmp_path, 21)
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="archive-counter",
    )
    repository.cancel_waiting_model_execution(
        reservation.execution_id, video_id=vid, now=NOW
    )
    backup = BackupRestoreService(database=repository._database_path, data_root=root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    with zipfile.ZipFile(package) as archive:
        members = {item.filename: archive.read(item) for item in archive.infolist()}
        entries = {item.filename: item for item in archive.infolist()}
    path = tmp_path / "attacker.sqlite"
    path.write_bytes(members["database/state.sqlite"])
    with sqlite3.connect(path) as c:
        c.execute("PRAGMA foreign_keys=OFF")
        if damage in {"unknown-family", "malformed-family"}:
            table = "distillation_execution_checkpoints"
            triggers = c.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                (table,),
            ).fetchall()
            for name, _ in triggers:
                c.execute('DROP TRIGGER "' + name + '"')
            altered = (
                "distillation:long-timed-v999:" + "1" * 64
                if damage == "unknown-family"
                else "distillation:long-timed-v1:bad"
            )
            c.execute(
                "UPDATE distillation_execution_checkpoints SET execution_id=? WHERE execution_id=?",
                (altered, reservation.execution_id),
            )
            for _, sql in triggers:
                c.execute(sql)
        else:
            tablemap = {
                "proof": "long_distillation_input_proofs",
                "ledger": "distillation_resource_usage",
                "receipt": "long_distillation_completion_receipts",
                "card": "distillation_cards",
            }
            for part in damage.split("+"):
                table = tablemap[part]
                triggers = c.execute(
                    "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                    (table,),
                ).fetchall()
                for name, _ in triggers:
                    c.execute('DROP TRIGGER "' + name + '"')
                c.execute('DELETE FROM "' + table + '"')
                for _, sql in triggers:
                    c.execute(sql)
        c.commit()
    # sqlite connection context commits but does not close. Ensure the attacked
    # rows are in the exact main-file bytes, not merely an omitted WAL sidecar.
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
    c.execute("PRAGMA journal_mode=DELETE").fetchone()
    c.close()
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as check:
        if damage in {"unknown-family", "malformed-family"}:
            assert check.execute(
                "SELECT 1 FROM distillation_execution_checkpoints WHERE execution_id=?",
                (altered,),
            ).fetchone()
        else:
            assert (
                check.execute(
                    "SELECT count(*) FROM " + tablemap[damage.split("+")[0]]
                ).fetchone()[0]
                == 0
            )
    members["database/state.sqlite"] = path.read_bytes()
    manifest = json.loads(members["manifest.json"])
    manifest["database"]["sha256"] = hashlib.sha256(
        members["database/state.sqlite"]
    ).hexdigest()
    manifest["database"]["size_bytes"] = len(members["database/state.sqlite"])
    members["manifest.json"] = json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(entries[name], payload)
    before = _inventory(repository, root)
    with pytest.raises(BackupRestoreError):
        backup.stage_restore(out.getvalue())
    assert _inventory(repository, root) == before and not backup.restore_pending


def test_two_available_timed_canonical_authorities_are_rejected(tmp_path):
    from youtube_intel.state import StateStoreError

    repository, root, sid, vid, service, _app, _transport = workspace(tmp_path, 21)
    wire = b"second active source"
    (root / "second.txt").write_bytes(wire)
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="second-canonical",
            artifact_key="second-canonical",
            video_id=vid,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path="second.txt",
            content_hash=hashlib.sha256(wire).hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    timed = TimedTranscriptWrite.from_cues(
        video_id=vid,
        canonical_artifact_id="second-canonical",
        cues=(TimedTranscriptCueWrite(100000, 100900, wire.decode()),),
    )
    repository.create_timed_transcript(timed, now=NOW)
    evidence = EvidenceWrite(
        evidence_id=build_evidence_id(
            video_id=vid,
            artifact_id="second-canonical",
            start_ms=100000,
            end_ms=100900,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
        ),
        video_id=vid,
        artifact_id="second-canonical",
        start_ms=100000,
        end_ms=100900,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en",
        availability=EvidenceAvailability.AVAILABLE,
    )
    repository.create_evidence_with_text_binding(
        evidence,
        EvidenceTextBindingWrite.from_timed_transcript(
            evidence=evidence,
            timed_transcript_id=timed.timed_transcript_id,
            start_cue_index=0,
            end_cue_index=1,
            excerpt=wire.decode(),
        ),
        now=NOW,
    )
    with pytest.raises(StateStoreError, match="ambiguous"):
        service.reserve_distillation_execution(
            source_id=sid,
            video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid),
            manual_command_id="ambiguous",
        )


@pytest.mark.parametrize("point", ["proof", "wait", "validator"])
def test_all_reservation_write_boundaries_roll_back(tmp_path, monkeypatch, point):
    from youtube_intel import long_distillation_persistence as long

    repository, root, sid, vid, service, _app, _transport = workspace(tmp_path, 21)
    before = _inventory(repository, root)

    def failure(*_args, **_kwargs):
        raise RuntimeError("injected " + point)

    if point == "validator":
        monkeypatch.setattr(long, "verify_execution", failure)
    elif point == "wait":
        monkeypatch.setattr(long, "_checkpoint_wait", failure)
    else:
        original = long._proof_digest

        def fail_proof(proof):
            original(proof)
            raise RuntimeError("injected proof")

        monkeypatch.setattr(long, "_proof_digest", fail_proof)
    with pytest.raises(RuntimeError, match="injected"):
        service.reserve_distillation_execution(
            source_id=sid,
            video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid),
            manual_command_id="all-rollback",
        )
    assert _inventory(repository, root) == before


def test_complete_short_request_byte_overflow_uses_same_long_factory(tmp_path):
    repository, _root, sid, vid, service, _app, transport = workspace(
        tmp_path, 4, texts=("Short source fact.", "x" * 3000, "y" * 3000, "z" * 3000)
    )
    ids = service.reservation_evidence_ids(vid)
    assert len(ids) == 4
    reservation = service.reserve_distillation_execution(
        source_id=sid, video_id=vid, evidence_ids=ids, manual_command_id="byte-overflow"
    )
    assert reservation.execution_id.startswith("distillation:long-timed-v1:")
    assert (
        repository.get_distillation_execution(reservation.execution_id).status
        == "WAITING_MODEL"
    )
    assert transport.calls == 0


def test_full_candidate_sentinel_rejects_4103_without_truncating(tmp_path):
    from youtube_intel.state import StateStoreError, format_utc_datetime

    repository, _root, _sid, vid, service, _app, _transport = workspace(tmp_path, 2)
    with repository._connect() as connection:
        connection.executemany(
            "INSERT INTO evidence(evidence_id,video_id,artifact_id,start_ms,end_ms,lineage_kind,role,language,availability,created_at) "
            "VALUES(?,?,'canonical-long',?,?,'ORIGINAL_TRANSCRIPT','PRIMARY_ORIGINAL','en','AVAILABLE',?)",
            [
                (
                    f"extra-{i}",
                    vid,
                    10000 + i * 10,
                    10009 + i * 10,
                    format_utc_datetime(NOW),
                )
                for i in range(4101)
            ],
        )
    with pytest.raises(StateStoreError, match="storage bound"):
        service.reservation_evidence_ids(vid)
