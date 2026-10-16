"""Real composition/file-slot tests with fake wire only; no model is loaded."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.request
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.config import load_app_config
from youtube_intel.distillation import (
    OllamaLocalDistillationTransport,
    bind_local_profile,
    build_local_distillation_request,
)
from youtube_intel.local_distillation_profile import (
    PROFILE_ID,
    canonical,
    resolve_profile,
)
from youtube_intel.local_distillation_qualification import (
    LocalExecutionPermit,
    qualification_binding,
)
from youtube_intel.local_model_capacity import (
    ApplicationHeavyLease,
    SharedHeavyGuard,
)
from youtube_intel.runtime_composition import build_local_source_run_runtime

support = _load_module("test_runtime_composition")
unit = _load_module("test_local_model_capacity")


def _composition(tmp_path, monkeypatch):
    monkeypatch.setattr(
        OllamaLocalDistillationTransport, "available", property(lambda _: False)
    )
    project = support._project(tmp_path)
    config = load_app_config(
        project / "config/channels.yaml", project / "config/settings.yaml"
    )
    return build_local_source_run_runtime(
        config=config,
        project_root=project,
        database=project / "state.sqlite",
        now=lambda: datetime.now(UTC),
    )


@pytest.mark.parametrize("kind", ["score", "judge", "summary", "translation"])
@pytest.mark.parametrize("failure", [None, "read", "close"])
def test_actual_factories_hold_asr_slot_until_response_close_and_release_all_failures(
    tmp_path, monkeypatch, kind, failure
):
    composition = _composition(tmp_path, monkeypatch)
    data = tmp_path / "data"
    entered, resume = threading.Event(), threading.Event()
    calls, errors = [], []

    class Response:
        def read(self, maximum):
            entered.set()
            assert resume.wait(5)
            if failure == "read":
                raise TimeoutError("fixture read timeout")
            return b"{}"

        def close(self):
            calls.append("closed")
            if failure == "close":
                raise OSError("fixture close failure")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: Response())
    dependencies = composition.runtime._dependencies
    if kind in {"score", "judge"}:
        factory = (
            dependencies.scoring_provider_factory
            if kind == "score"
            else dependencies.quality_judge_provider_factory
        )
        provider = factory()
        from youtube_intel.providers.ollama import (
            OllamaQualityJudgeProvider,
            OllamaScoringProvider,
        )

        assert type(provider) is (
            OllamaScoringProvider if kind == "score" else OllamaQualityJudgeProvider
        )

        def invoke():
            response = provider._transport(
                urllib.request.Request(
                    "http://127.0.0.1:11434/api/generate", data=b"{}"
                ),
                300,
            )
            try:
                response.read(10)
            finally:
                response.close()
    else:
        provider = (
            dependencies.analysis_provider_factory()
            if kind == "summary"
            else composition.application._evidence_translation_service._translator
        )

        def invoke():
            provider._read(
                urllib.request.Request("http://127.0.0.1:11434/api/chat", data=b"{}")
            )

    def run():
        try:
            invoke()
        except (OSError, RuntimeError):
            errors.append(True)

    thread = threading.Thread(target=run)
    thread.start()
    assert entered.wait(5)
    contender = ApplicationHeavyLease(repository=composition.repository, data_root=data)
    assert not contender.acquire()
    # The actual ASR slot is a file lock and conflicts across processes too.
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from pathlib import Path; from youtube_intel.state import SQLiteStateRepository; "
            "from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs; "
            "jobs=LocalTranscriptionJobs(SQLiteStateRepository(Path(sys.argv[1])),Path(sys.argv[2])); "
            "fd=jobs._slot(); sys.exit(7 if fd is None else 8)",
            str(composition.repository._database_path),
            str(data),
        ],
        capture_output=True,
        timeout=5,
    )
    assert child.returncode == 7, child.stderr.decode()
    with composition.repository._connect() as connection:
        assert "SOURCE_RUN_ACTIVE" in composition.backup_restore._quiescence_reasons(
            connection
        )
    resume.set()
    thread.join(5)
    assert not thread.is_alive() and calls
    assert bool(errors) is (failure is not None)
    assert contender.acquire()
    contender.release()


def test_guard_reentry_and_worker_owned_nonreentrant_lock_do_not_self_deadlock(
    tmp_path, monkeypatch
):
    composition = _composition(tmp_path, monkeypatch)
    guard = SharedHeavyGuard(
        repository=composition.repository,
        data_root=tmp_path / "data",
        backup_restore=composition.backup_restore,
    )
    assert composition.worker._execution.acquire(blocking=False)
    try:
        with guard(), guard():
            other = ApplicationHeavyLease(
                repository=composition.repository, data_root=tmp_path / "data"
            )
            assert not other.acquire()
    finally:
        composition.worker._execution.release()
    assert other.acquire()
    other.release()


def test_other_request_cannot_release_another_threads_preclaim_readiness(
    tmp_path, monkeypatch
):
    session, send, calls, _ = unit._session(tmp_path, monkeypatch)
    value = unit.support._input()
    request = build_local_distillation_request(value)
    assert session.prepare("first", value, request, send)

    def second():
        assert not session.prepare("second", value, request, send)
        session.release()

    thread = threading.Thread(target=second)
    thread.start()
    thread.join(5)
    assert session.ready_for_claim("first", request)
    reordered = dict(reversed(list(request.items())))
    assert canonical(request) == canonical(reordered)
    assert not session.ready_for_claim("first", reordered)  # wire identity also matters
    session.release()


def test_all_original_four_inputs_fit_without_truncating_fifteen_evidence(
    tmp_path, monkeypatch
):
    from scripts import qualify_readiness_local_intelligence as controls
    from scripts import qualify_readiness_qwen35_intelligence as research

    actual = _load_module("test_readiness_qwen35_capacity").actual_input()
    docs = Path(__file__).parents[2] / "docs/validation/end-to-end-user-readiness"
    cases = [
        c
        for name in (
            "INTELLIGENCE_REAL_CORPUS_V2.json",
            "INTELLIGENCE_FROZEN_CORPUS.json",
        )
        for c in json.loads((docs / name).read_bytes())["cases"]
    ]
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: pytest.fail("no provider IO")
    )
    observed = []
    for case_id in research.CASE_IDS:
        case = next(c for c in cases if c["id"] == case_id)
        if case_id.startswith("real-"):
            value = replace(actual, output_language=case["output_language"])
        else:
            root = tmp_path / case_id
            repository, sid, vid = controls.setup(case, root, datetime.now(UTC))
            service, _ = research.make_service(repository, case, root)
            _, value = service._reserved_command(
                source_id=sid,
                video_id=vid,
                evidence_ids=repository.list_canonical_coverage_evidence_ids(vid),
                output_language=case["output_language"],
                reason=service._RESERVATION_REASON,
            )
        value = bind_local_profile(value, PROFILE_ID)
        request = build_local_distillation_request(value)
        assert len(canonical(request)) <= 12288
        assert (
            resolve_profile(PROFILE_ID).complete_input_token_upper_bound(request)
            + 6144
            + 1
            <= 16384
        )
        assert len(value.evidence) == (15 if case_id == "no-new-fifteen" else 2)
        observed.append(len(canonical(request)))
    assert observed == [4822, 4825, 7869, 4149]


@pytest.mark.parametrize("stopped", [False, True])
def test_asr_actual_slot_distinguishes_active_unknown_and_stopped_terminal_history(
    tmp_path, monkeypatch, stopped
):
    from youtube_intel import local_model_capacity as capacity
    from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs

    backup = _load_module("test_backup_restore")
    media = _load_module("test_offline_transcription_jobs")
    database, data, _, repository, _ = backup._workspace(tmp_path)
    backup._add_source(repository)
    jobs = LocalTranscriptionJobs(repository, data, executor=media.Executor())
    execution_id = backup._reserve_ambiguous_execution(repository)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: pytest.fail("active claim makes zero metadata calls"),
    )
    assert jobs._slot() is None
    backup._finish_ambiguous_execution(repository, execution_id=execution_id)
    before = (
        repository.get_distillation_execution(execution_id),
        repository.get_distillation_resource_usage(execution_id),
    )
    assert backup._service(tmp_path)._is_terminal_ambiguous_execution(
        repository, execution_id
    )
    monkeypatch.setattr(capacity, "file_hash", lambda _: capacity.BINARIES["ollama"])
    date = "Thu Oct 01 00:00:00 2026" if stopped else "Mon Sep 01 00:00:00 2025"
    server = f"77 {date} {capacity.ROOT / 'ollama'} serve"
    monkeypatch.setattr(
        capacity, "processes", lambda name: server if name == "ollama" else ""
    )

    class Metadata:
        def __init__(self, payload):
            self.payload = payload

        def read(self, maximum):
            return json.dumps(self.payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    calls = []

    def read_metadata(request, **kwargs):
        calls.append(request.full_url)
        return Metadata(
            {"version": "0.40.1"}
            if request.full_url.endswith("version")
            else {"models": []}
        )

    monkeypatch.setattr("urllib.request.urlopen", read_metadata)
    fd = jobs._slot()
    if stopped:
        assert fd is not None and len(calls) == 2
        jobs._release(fd)
        # A restore/restart has no magic in-memory or on-disk 'stopped' bool.
        monkeypatch.setattr(capacity, "processes", lambda _: "")
        assert jobs._slot() is None
    else:
        assert fd is None and calls == []
    assert before == (
        repository.get_distillation_execution(execution_id),
        repository.get_distillation_resource_usage(execution_id),
    )
    assert repository.get_distillation_execution(execution_id).status == "AMBIGUOUS"


def test_asr_predicate_exception_releases_existing_file_slot(tmp_path, monkeypatch):
    from youtube_intel import local_model_capacity as capacity
    from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs

    composition = _composition(tmp_path, monkeypatch)
    media = _load_module("test_offline_transcription_jobs")
    jobs = LocalTranscriptionJobs(
        composition.repository, tmp_path / "data", executor=media.Executor()
    )

    def failed(_):
        raise RuntimeError("fixture metadata failure")

    monkeypatch.setattr(capacity, "unresolved_local_work", failed)
    assert jobs._slot() is None
    monkeypatch.setattr(capacity, "unresolved_local_work", lambda _: False)
    fd = jobs._slot()
    assert fd is not None
    jobs._release(fd)


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "metadata-fail",
        "cancel-during-load",
        "identity-change",
        "expire-before-arm",
        "expire-after-claim",
        "intent-io",
        "cancel-at-claim",
        "postclaim-lost",
        "wrong-permit-execution",
        "timeout",
    ],
)
def test_ordinary_reserved_service_preclaims_once_and_never_queries_metadata_after_claim(
    tmp_path, monkeypatch, mode
):
    from youtube_intel import local_model_capacity as capacity
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.distillation import (
        PersonalizedDistillationService,
        local_profile_projection,
    )
    from youtube_intel.local_distillation_profile import digest
    from youtube_intel.source_policy import SourcePolicyApplicationService

    timed = _load_module("test_local_intelligence_timed")
    repository, provider, cid, ids, old_wire, _ = timed._local(tmp_path)
    metadata_root = tmp_path / "metadata"
    metadata_root.mkdir()
    _, send, metadata_calls, _ = unit._session(metadata_root, monkeypatch)
    profile = resolve_profile(PROFILE_ID)
    claimed, generations = [], []

    class Wire(OllamaLocalDistillationTransport):
        def _request(self, path, *, method, body=None):
            if path != "/api/chat" or body["messages"] == []:
                assert not claimed
                if mode == "metadata-fail" and path == "/api/version":
                    return {"version": "future"}
                result = send(path, method=method, body=body)
                if path == "/api/chat":
                    if mode == "cancel-during-load":
                        repository.finish_distillation_without_admission(
                            execution_id=reservation.execution_id,
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
                            now=timed.support.NOW,
                        )
                        repository.cancel_waiting_model_execution(
                            execution_id=reservation.execution_id,
                            video_id=cid,
                            now=timed.support.NOW,
                        )
                    if mode == "identity-change":
                        monkeypatch.setattr(
                            capacity.HostObservation, "is_current", lambda _: False
                        )
                return result
            assert claimed
            generations.append(body)
            if mode == "timeout":
                raise TimeoutError("fixture POST outcome unknown")
            return {
                "model": profile.model,
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 100,
                "eval_count": 50,
                "message": {"content": old_wire.raw},
            }

    intent = tmp_path / "dispatch.armed.json"

    def arm_intent(*_):
        assert not claimed and not generations
        if mode == "intent-io":
            raise OSError("fixture durable intent IO failure")
        # The real harness primitive refuses an already spent intent.
        harness = _load_module("test_local_grounding_harness")._harness()
        harness.write_once(intent, {"status": "ARMED", "generation_post_proven": False})

    wire = Wire(
        settings=LocalScoringSettings(
            model=profile.model, expected_model_digest=profile.model_digest
        ),
        local_profile_id=PROFILE_ID,
        before_dispatch=arm_intent,
    )
    service = PersonalizedDistillationService(
        repository,
        SourcePolicyApplicationService(repository, now=lambda: timed.support.NOW),
        wire,
        timed.support._FakeBudget(True),
        now=lambda: timed.support.NOW,
        output_language_for_video=lambda _: "en",
    )
    reservation = service.reserve_distillation_execution(
        source_id=timed.LOCAL_SOURCE_ID,
        video_id=cid,
        evidence_ids=ids,
        manual_command_id="capacity-test",
    )
    _, value = service._reserved_command_from_record(
        repository.get_distillation_execution(reservation.execution_id)
    )
    now = datetime.now(UTC)
    permit = {
        "version": "local-grounding-once-permit-v1",
        "case_id": "local-timed-en",
        "execution_id": (
            "different-execution"
            if mode == "wrong-permit-execution"
            else reservation.execution_id
        ),
        "input_hash": value.semantic_hash,
        "context_hash": value.local_content_context_hash,
        "request_hash": digest(build_local_distillation_request(value)),
        "binding": qualification_binding(local_profile_projection(value)),
        "source_manifest_hash": "a" * 64,
        "capacity_proof_hash": "b" * 64,
        "runtime_proof_hash": "c" * 64,
        "harness_hash": "d" * 64,
        "freeze_hash": "e" * 64,
        "prior_review_hashes": [],
        "issued_at": (now - timedelta(seconds=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=5)).isoformat(),
    }
    wire._local_permit = LocalExecutionPermit.model_validate(
        {**permit, "permit_hash": digest(permit)}
    )
    original_claim = repository.claim_reserved_distillation_execution

    if mode == "expire-before-arm":
        original_arm = capacity.LocalCapacitySession.arm

        def expired_arm(session, execution_id, request):
            session._ready = replace(session._ready, expires=-1)
            return original_arm(session, execution_id, request)

        monkeypatch.setattr(capacity.LocalCapacitySession, "arm", expired_arm)

    def claim(**kwargs):
        if mode == "cancel-at-claim":
            assert intent.exists() and not generations
            repository.finish_distillation_without_admission(
                execution_id=reservation.execution_id,
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
                now=timed.support.NOW,
            )
            repository.cancel_waiting_model_execution(
                execution_id=reservation.execution_id,
                video_id=cid,
                now=timed.support.NOW,
            )
        result = original_claim(**kwargs)
        if result:
            claimed.append(True)
            if mode == "expire-after-claim":
                wire._capacity_session._ready = replace(
                    wire._capacity_session._ready, expires=-1
                )
            if mode == "postclaim-lost":
                wire._capacity_session._armed = False
        return result

    monkeypatch.setattr(repository, "claim_reserved_distillation_execution", claim)
    result = service.continue_qualification_reserved_distillation(
        reservation.execution_id
    )
    if mode in {"success", "expire-after-claim"}:
        assert (
            result.status.value == "SUCCEEDED_NO_NEW_INTELLIGENCE"
            and len(generations) == result.invocation_count == 1
        )
    elif mode == "postclaim-lost":
        assert result.status.value == "AMBIGUOUS" and result.invocation_count == 1
        assert not generations and not wire.last_grounding_post_attempted
    elif mode == "timeout":
        assert (
            result.status.value == "AMBIGUOUS"
            and len(generations) == result.invocation_count == 1
        )
    else:
        assert (
            result.status.value in {"WAITING_MODEL", "CANCELLED"}
            and result.invocation_count == 0
            and not generations
        )
    assert wire.last_grounding_post_attempted == bool(generations)
    assert intent.exists() == (
        mode
        in {
            "success",
            "expire-before-arm",
            "expire-after-claim",
            "cancel-at-claim",
            "postclaim-lost",
            "timeout",
        }
    )
    if mode == "wrong-permit-execution":
        assert not metadata_calls
    before = list(metadata_calls), list(generations)
    assert (
        service.continue_qualification_reserved_distillation(reservation.execution_id)
        == result
    )
    assert before == (metadata_calls, generations)
    assert wire._capacity_session.lease.fd is None
