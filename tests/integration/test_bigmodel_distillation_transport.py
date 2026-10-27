"""Real isolated audit/lifecycle with fake BigModel wire, never qualification."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
import test_task022_personalized_distillation as fixtures
from test_task022_personalized_distillation import (
    NOW,
    _evidence,
    _FakeBudget,
    _repository,
    _service,
    _source_and_video,
)

from youtube_intel import distillation as d
from youtube_intel.state import SQLiteStateRepository


def _snapshot(repository, root):
    with repository._connect() as connection:
        rows = tuple(connection.iterdump())
    return rows, {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
        and path.name != "state.sqlite3"
        and not path.name.startswith("state.sqlite3-")
    }


def _setup(tmp_path, wire=None, *, hash_value="0" * 64, credentials=None):
    data = tmp_path / "DATA"
    data.mkdir(exist_ok=True)
    (data / "public-sentinel.txt").write_bytes(
        b"Public offline fixture; preserve exact bytes.\n"
    )
    repository = _repository(tmp_path)
    source, video = _source_and_video(repository, "bigmodel-offline-public")
    evidence = _evidence(repository, video)
    transport = d.BigModelGlm47FlashDistillationTransport(
        authorization=d.CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="zhipu_bigmodel",
            model="glm-4.7-flash",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=hash_value,
        ),
        credential_resolver=credentials or (lambda: "synthetic-bigmodel-secret"),
        wire_transport=wire or (lambda *_: pytest.fail("unexpected wire")),
    )
    return repository, source, video, evidence, _service(repository, transport)


def _permit(service, verified):
    service._transport._authorization = d.CloudDistillationAuthorization(
        cloud_enabled=True,
        provider="zhipu_bigmodel",
        model="glm-4.7-flash",
        credential_available=True,
        provider_available=True,
        qualification_input_hash=verified.semantic_hash,
    )


def test_keyless_preview_is_physically_readonly_and_profile_bound(
    tmp_path, monkeypatch
):
    repository, source, video, evidence, service = _setup(
        tmp_path, credentials=lambda: pytest.fail("preview must not resolve credential")
    )
    service._budget = _FakeBudget(False)
    before = _snapshot(repository, tmp_path)
    preview = service.preview_cloud_execution(
        source_id=source,
        video_id=video,
        evidence_ids=(evidence,),
        qualified=False,
        credential_available=False,
    )
    assert preview["outgoing_request"] == service._transport._request(
        service._prospective_cloud_command(
            source_id=source, video_id=video, evidence_ids=(evidence,)
        )[1]
    )
    assert (
        preview["provider"] == "zhipu_bigmodel" and preview["model"] == "glm-4.7-flash"
    )
    assert (
        not preview["readiness"]["can_confirm"]
        and "CREDENTIAL_REQUIRED" in preview["readiness"]["blockers"]
    )
    assert service._budget.calls == 0 and _snapshot(repository, tmp_path) == before
    monkeypatch.setattr(
        d.BigModelGlm47FlashDistillationTransport,
        "_REQUEST_PROFILE_VERSION",
        "different-offline-profile",
    )
    changed = service.preview_cloud_execution(
        source_id=source,
        video_id=video,
        evidence_ids=(evidence,),
        qualified=False,
        credential_available=False,
    )
    assert changed["verified_input_hash"] != preview["verified_input_hash"]
    assert changed["execution_id"] != preview["execution_id"]
    assert _snapshot(repository, tmp_path) == before


@pytest.mark.parametrize(
    "outcome",
    [
        "no-new",
        "admitted",
        "schema",
        "foreign",
        "401",
        "429",
        "202",
        "timeout",
        "connect",
        "identity",
        "truncated",
    ],
)
def test_existing_consent_claim_accounting_and_restart_never_replay(tmp_path, outcome):
    calls = []

    def wire(request, key, timeout, retries):
        calls.append(request)
        assert (timeout, retries) == (300.0, 0)
        items = json.loads(request["messages"][2]["content"].split("=", 1)[1])[
            "evidence"
        ]
        if outcome == "timeout":
            raise TimeoutError("synthetic-bigmodel-secret private reasoning")
        if outcome == "connect":
            raise d.CloudDistillationPreDispatchError("known no HTTP bytes sent")
        if outcome in {"401", "429", "202"}:
            return d._BigModelWireResponse(int(outcome), b"")
        citations = [
            {key: item[key] for key in ("evidence_id", "start_ms", "end_ms")}
            for item in items
        ]
        answer = {"result": "NO_NEW_INTELLIGENCE", "evidence": citations}
        if outcome == "admitted":
            answer = {
                "core_conclusion": "Offline synthetic claim, not real model output.",
                "user_relevant_information": [],
                "important_new_information": [],
                "meaningful_details": [],
                "filtered_noise": [],
                "claim_kind": "SYSTEM_INFERENCE",
                "evidence": [dict(item, stance="supporting") for item in citations],
            }
        if outcome == "schema":
            answer = {"invented": True}
        if outcome == "foreign":
            answer["evidence"][0]["evidence_id"] = "foreign-evidence"
        return d._BigModelWireResponse(
            200,
            json.dumps(
                {
                    "model": "other" if outcome == "identity" else "glm-4.7-flash",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "length"
                            if outcome == "truncated"
                            else "stop",
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(answer),
                                "reasoning_content": "private reasoning never persisted",
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 30},
                }
            ).encode(),
        )

    repository, source, video, evidence, service = _setup(tmp_path, wire)
    reservation = service.reserve_distillation_execution(
        source_id=source, video_id=video, evidence_ids=(evidence,)
    )
    _, verified = service._reserved_command_from_record(
        repository.get_distillation_execution(reservation.execution_id)
    )
    _permit(service, verified)
    before = _snapshot(repository, tmp_path)
    with pytest.raises(d.CloudConsentRequiredError):
        service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert calls == [] and _snapshot(repository, tmp_path) == before
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    consent = repository.get_cloud_execution_authorization(reservation.execution_id)
    assert consent.verified_input_hash == verified.semantic_hash and (
        consent.provider,
        consent.model,
    ) == ("zhipu_bigmodel", "glm-4.7-flash")
    result = service.continue_qualification_reserved_distillation(
        reservation.execution_id
    )
    expected = {
        "no-new": "SUCCEEDED_NO_NEW_INTELLIGENCE",
        "admitted": "SUCCEEDED",
        "timeout": "AMBIGUOUS",
        "202": "AMBIGUOUS",
        "connect": "WAITING_MODEL",
    }.get(outcome, "REJECTED_OUTPUT")
    assert result.status.value == expected
    assert (
        result.invocation_count == (0 if outcome == "connect" else 1)
        and len(calls) == 1
    )
    with repository._connect() as connection:
        repository.verify_cloud_audit_database(connection)
        dump = "\n".join(connection.iterdump())
        assert (
            "synthetic-bigmodel-secret" not in dump and "private reasoning" not in dump
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM distillation_zhipu_cloud_authorizations"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM distillation_cloud_authorizations"
            ).fetchone()[0]
            == 0
        )
        assert connection.execute(
            "SELECT count(*) FROM distillation_zhipu_cloud_response_failures"
        ).fetchone()[0] == (1 if outcome in {"401", "429", "identity"} else 0)
    if outcome in {"401", "429", "identity"}:
        # The existing reader projects the separate failure receipt as usage;
        # it does not fabricate a physical resource-usage row or model identity.
        usage = repository.get_distillation_resource_usage(reservation.execution_id)
        assert usage.actual_model is None and usage.actual_provider == "zhipu_bigmodel"
        assert (usage.input_tokens, usage.output_tokens, usage.cost_microunits) == (
            None,
            None,
            None,
        )
        assert usage.http_status_code == (
            200 if outcome == "identity" else int(outcome)
        )
        with repository._connect() as connection:
            assert (
                connection.execute(
                    "SELECT count(*) FROM distillation_resource_usage"
                ).fetchone()[0]
                == 0
            )
    else:
        usage = repository.get_distillation_resource_usage(reservation.execution_id)
        assert usage.cost_microunits is None
        assert (usage.input_tokens, usage.output_tokens) == (
            (None, None) if outcome in {"timeout", "202", "connect"} else (100, 30)
        )
        if outcome == "202":
            assert usage.http_status_code == 202
    settled = _snapshot(repository, tmp_path)
    restarted = SQLiteStateRepository(tmp_path / "state.sqlite3")
    restarted.initialize(now=NOW)
    service = _service(restarted, service._transport)
    assert (
        service.continue_qualification_reserved_distillation(reservation.execution_id)
        == result
    )
    assert len(calls) == 1 and _snapshot(restarted, tmp_path) == settled


def test_normal_path_cannot_inherit_qualification_and_does_not_resolve_key(tmp_path):
    repository, source, video, evidence, service = _setup(
        tmp_path,
        credentials=lambda: pytest.fail("normal path must not resolve credential"),
    )
    reservation = service.reserve_distillation_execution(
        source_id=source, video_id=video, evidence_ids=(evidence,)
    )
    _, verified = service._reserved_command_from_record(
        repository.get_distillation_execution(reservation.execution_id)
    )
    _permit(service, verified)
    result = service.continue_reserved_distillation(reservation.execution_id)
    assert result.status.value == "WAITING_MODEL" and result.invocation_count == 0
    assert (
        repository.get_cloud_execution_authorization(reservation.execution_id) is None
    )


def test_changed_profile_invalidates_existing_permit_and_reservation(
    tmp_path, monkeypatch
):
    repository, source, video, evidence, service = _setup(
        tmp_path,
        credentials=lambda: pytest.fail("stale binding must not resolve credential"),
    )
    reservation = service.reserve_distillation_execution(
        source_id=source, video_id=video, evidence_ids=(evidence,)
    )
    _, verified = service._reserved_command_from_record(
        repository.get_distillation_execution(reservation.execution_id)
    )
    _permit(service, verified)
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    monkeypatch.setattr(
        d.BigModelGlm47FlashDistillationTransport,
        "_REQUEST_PROFILE_VERSION",
        "changed-profile",
    )
    result = service.continue_qualification_reserved_distillation(
        reservation.execution_id
    )
    assert result.status.value == "REJECTED_EVIDENCE" and result.invocation_count == 0


def test_generic_source_run_cannot_borrow_owner_qualification_permit(tmp_path):
    repository, source, video, evidence, service = _setup(
        tmp_path,
        credentials=lambda: pytest.fail("source-run must not resolve credential"),
    )
    command = d.DistillationCommand(
        "direct-normal",
        source,
        video,
        (evidence,),
        "MANUAL_PERSONALIZED_DISTILLATION",
        "PERSONALIZED_INTELLIGENCE",
        "zhipu_bigmodel",
        "glm-4.7-flash",
        "en",
    )
    verified = service._compose_verified_input(service._projection(command))
    _permit(service, verified)
    result = service.distill(command)
    assert result.status.value == "WAITING_MODEL" and result.invocation_count == 0
    assert repository.get_cloud_execution_authorization(command.execution_id) is None


def test_concurrent_owner_continuations_and_claimed_restart_make_one_post(tmp_path):
    calls = []

    def wire(*args):
        calls.append(args)
        raise TimeoutError("simulated unknown post outcome")

    repository, source, video, evidence, service = _setup(tmp_path, wire)
    reservation = service.reserve_distillation_execution(
        source_id=source, video_id=video, evidence_ids=(evidence,)
    )
    _, verified = service._reserved_command_from_record(
        repository.get_distillation_execution(reservation.execution_id)
    )
    _permit(service, verified)
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    other = _service(
        SQLiteStateRepository(tmp_path / "state.sqlite3"), service._transport
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda current: current.continue_qualification_reserved_distillation(
                    reservation.execution_id
                ),
                (service, other),
            )
        )
    assert len(calls) == 1
    assert all(
        item.status.value == "AMBIGUOUS" and item.invocation_count == 1
        for item in results
    )
    assert (
        repository.get_distillation_execution(reservation.execution_id).invocation_count
        == 1
    )
    before = _snapshot(repository, tmp_path)
    assert (
        service.continue_qualification_reserved_distillation(
            reservation.execution_id
        ).status.value
        == "AMBIGUOUS"
    )
    assert len(calls) == 1 and _snapshot(repository, tmp_path) == before


@pytest.mark.parametrize("consent", ["absent", "wrong-hash", "wrong-kind"])
def test_missing_or_mismatched_consent_refuses_before_credential_without_writes(
    tmp_path, consent
):
    repository, source, video, evidence, service = _setup(
        tmp_path,
        credentials=lambda: pytest.fail("refused consent must not resolve credential"),
    )
    reservation = service.reserve_distillation_execution(
        source_id=source, video_id=video, evidence_ids=(evidence,)
    )
    _, verified = service._reserved_command_from_record(
        repository.get_distillation_execution(reservation.execution_id)
    )
    _permit(service, verified)
    if consent != "absent":
        repository.authorize_cloud_execution(
            authorization_id="offline-mismatched-consent",
            execution_id=reservation.execution_id,
            provider="zhipu_bigmodel",
            model="glm-4.7-flash",
            verified_input_hash="a" * 64
            if consent == "wrong-hash"
            else verified.semantic_hash,
            consent_kind="USER_CONFIRMATION"
            if consent == "wrong-kind"
            else "OWNER_QUALIFICATION",
            now=NOW,
        )
    before = _snapshot(repository, tmp_path)
    with pytest.raises(d.CloudConsentRequiredError):
        service.continue_qualification_reserved_distillation(reservation.execution_id)
    assert _snapshot(repository, tmp_path) == before


def test_oversized_trusted_input_is_terminal_before_credential_preflight(
    tmp_path, monkeypatch
):
    lookups = []
    wires = []
    text = "Public caption factual sentence. " * 5000
    cue = fixtures.TimedTranscriptCueWrite
    binding = fixtures.EvidenceTextBindingWrite.from_timed_transcript
    with monkeypatch.context() as patch:
        patch.setattr(
            fixtures, "TimedTranscriptCueWrite", lambda **kw: cue(**dict(kw, text=text))
        )
        patch.setattr(
            fixtures.EvidenceTextBindingWrite,
            "from_timed_transcript",
            lambda **kw: binding(**dict(kw, excerpt=text)),
        )
        repository, source, video, evidence, service = _setup(
            tmp_path,
            credentials=lambda: (
                lookups.append("credential") or "synthetic-bigmodel-secret"
            ),
            wire=lambda *args: (
                wires.append(args) or pytest.fail("invalid input must not reach wire")
            ),
        )
    reservation = service.reserve_distillation_execution(
        source_id=source, video_id=video, evidence_ids=(evidence,)
    )
    _, verified = service._reserved_command_from_record(
        repository.get_distillation_execution(reservation.execution_id)
    )
    assert verified.evidence[0].excerpt == text and len(text.encode()) == 165000
    with pytest.raises(d.CloudDistillationPreDispatchError, match="UTF-8 bound"):
        service._transport._request(verified)
    _permit(service, verified)
    service.authorize_reserved_cloud_execution(
        reservation.execution_id, consent_kind="OWNER_QUALIFICATION"
    )
    consent = repository.get_cloud_execution_authorization(reservation.execution_id)
    before = _snapshot(repository, tmp_path)
    result = service.continue_qualification_reserved_distillation(
        reservation.execution_id
    )
    assert lookups == [] and wires == []  # Pure refusal precedes any key read.
    assert result.status.value == "REJECTED_EVIDENCE" and result.invocation_count == 0
    usage = repository.get_distillation_resource_usage(reservation.execution_id)
    assert usage.outcome == "CLOUD_INPUT_NOT_SUPPORTED_BEFORE_TRANSPORT"
    assert (
        usage.actual_provider,
        usage.actual_model,
        usage.input_tokens,
        usage.output_tokens,
        usage.cost_microunits,
        usage.http_status_code,
    ) == (None, None, None, None, None, None)
    assert (
        repository.get_cloud_execution_authorization(reservation.execution_id)
        == consent
    )
    assert _snapshot(repository, tmp_path)[1] == before[1]
    with repository._connect() as connection:
        repository.verify_cloud_audit_database(connection)
        assert (
            connection.execute(
                "SELECT count(*) FROM distillation_execution_checkpoints WHERE status='PENDING'"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM distillation_zhipu_cloud_response_failures"
            ).fetchone()[0]
            == 0
        )
    restarted = SQLiteStateRepository(tmp_path / "state.sqlite3")
    restarted.initialize(now=NOW)
    settled = _snapshot(restarted, tmp_path)
    assert (
        _service(
            restarted, service._transport
        ).continue_qualification_reserved_distillation(reservation.execution_id)
        == result
    )
    assert lookups == [] and wires == [] and _snapshot(restarted, tmp_path) == settled
