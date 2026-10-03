"""Cloud governance uses fakes through the real product/Evidence pipeline."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from conftest import _load_module

from youtube_intel.deep_analysis_qualification import QualificationAuthority
from youtube_intel.deep_analysis_service import (
    DeepAnalysisCapability,
    DeepAnalysisRejected,
    DeepAnalysisService,
    build_openai_phase1b_route,
)

support = _load_module("test_v1x_phase1b_authority")
qualification = _load_module("test_v1x_phase1c_qualification")
contract = support.contract
NOW, VIDEO = support.NOW, support.VIDEO


def setup(
    tmp_path, *, qualified=True, credential=True, reachable="REACHABLE", failure=None
):
    repository = support.seed(tmp_path)
    calls = []

    def transport(request, secret, timeout, retries):
        assert secret == "injected-test-credential"
        assert retries == 0
        calls.append(request)
        if failure:
            raise failure
        payload = json.loads(
            request["input"][-1]["content"].split("Authorized payload: ", 1)[1]
        )
        refs = [c["evidence_id"] for c in payload["selected_evidence"]]
        return {
            "kind": "response",
            "response": {
                "id": "fixture-response",
                "model": "gpt-5.4-mini-2026-03-17",
                "status": "completed",
                "output_text": json.dumps(contract.output(refs[0])),
                "usage": {"input_tokens": 234, "output_tokens": 123},
            },
        }

    route = build_openai_phase1b_route(
        transport=transport,
        credential_resolver=lambda: "injected-test-credential" if credential else None,
        reachability=lambda: reachable,
    )
    authority = QualificationAuthority(
        (qualification.record(route),) if qualified else ()
    )
    capability = DeepAnalysisCapability((route,), authority=authority)
    service = DeepAnalysisService(
        repository=repository,
        capability=capability,
        scoring_reader=lambda video: support.activation._scoring_read(video),
        transcript_reader=lambda **_: SimpleNamespace(language="en"),
        evidence_reader=lambda _: (),
        evidence_text_reader=lambda _: None,
        now=lambda: NOW,
    )
    return repository, service, route, calls


def test_local_model_digest_is_rechecked_after_cached_health_before_dispatch(
    tmp_path, monkeypatch
):
    import youtube_intel.deep_analysis_activation as activation

    calls = []
    route = replace(
        qualification.build_local_ollama_phase1b_route(),
        dispatch=lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(activation, "build_local_ollama_phase1b_route", lambda: route)
    monkeypatch.setattr(
        activation, "PRODUCTION_QUALIFICATION_RECORDS", (qualification.record(route),)
    )
    monkeypatch.setattr(activation, "_local_probe", lambda _: "REACHABLE")
    monkeypatch.setattr(
        activation, "_fresh_local_probe", lambda: "PROFILE_MISMATCH", raising=False
    )
    capability = activation.production_deep_analysis_capability()
    assert capability.describe()[0]["production_eligible"]
    service = DeepAnalysisService(
        repository=support.seed(tmp_path),
        capability=capability,
        scoring_reader=lambda video: support.activation._scoring_read(video),
        transcript_reader=lambda **_: SimpleNamespace(language="en"),
        evidence_reader=lambda _: (),
        evidence_text_reader=lambda _: None,
        now=lambda: NOW,
    )
    with pytest.raises(DeepAnalysisRejected):
        service.run(content_id=VIDEO)
    assert calls == []


@pytest.mark.parametrize("qualified,credential", [(False, True), (True, False)])
def test_cloud_requires_both_qualification_and_credential(
    tmp_path, qualified, credential
):
    _, service, route, calls = setup(
        tmp_path, qualified=qualified, credential=credential
    )
    with pytest.raises(DeepAnalysisRejected):
        service.run(content_id=VIDEO, route_id=route.route_id, cloud_consent=True)
    assert calls == []


@pytest.mark.parametrize(
    "credential,reachable,reason",
    [
        (False, "REACHABLE", "CREDENTIAL_MISSING"),
        (True, "UNREACHABLE", "ROUTE_UNREACHABLE"),
    ],
)
def test_content_status_preserves_qualification_when_activation_is_unavailable(
    tmp_path, credential, reachable, reason
):
    _, service, _, calls = setup(tmp_path, credential=credential, reachable=reachable)
    status = service.status(content_id=VIDEO)
    assert status.qualified and not status.production_eligible
    assert status.availability.value == "UNAVAILABLE"
    assert status.reason_code.value == reason
    assert calls == []


def test_cloud_consent_requires_exact_preflight_and_unknown_cost_acknowledgement(
    tmp_path,
):
    _, service, route, calls = setup(tmp_path)
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    assert preflight["cost"]["state"] == "UNKNOWN"
    assert preflight["cost"]["hard_monetary_cap"] is False
    for kwargs in (
        {},
        {"cloud_consent": False},
        {"cloud_consent": True},
        {"cloud_consent": True, "execution_id": preflight["execution_id"]},
    ):
        with pytest.raises(DeepAnalysisRejected):
            service.run(content_id=VIDEO, route_id=route.route_id, **kwargs)
    assert calls == []


def test_exactly_one_dispatch_usage_and_restart_evidence(tmp_path):
    repository, service, route, calls = setup(tmp_path)
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    args = dict(
        content_id=VIDEO,
        route_id=route.route_id,
        execution_id=preflight["execution_id"],
        cloud_consent=True,
        acknowledge_unknown_cost=True,
    )
    result = service.run(**args)
    assert result.evidence_citation_status == "DURABLE_EVIDENCE_VERIFIED"
    with pytest.raises(DeepAnalysisRejected):
        service.run(**args)
    assert len(calls) == 1
    serialized = json.dumps(calls)
    assert (
        "transcript_text" not in serialized
        or '\\"transcript_text\\": null' in serialized
    )
    assert "injected-test-credential" not in serialized
    with repository._connect() as connection:
        row = connection.execute(
            "SELECT * FROM provider_calls WHERE operation='content-deep-analysis-cloud'"
        ).fetchone()
        assert (row["input_tokens"], row["output_tokens"], row["cost_microusd"]) == (
            234,
            123,
            None,
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM provider_dispatch_states"
            ).fetchone()[0]
            == 1
        )
        assert "injected-test-credential" not in str(list(connection.iterdump()))
    assert service.read(content_id=VIDEO).as_dict() == result.as_dict()


def test_backup_restore_preserves_cloud_evidence_usage_and_dispatch_barrier(tmp_path):
    from youtube_intel.backup_restore import BackupRestoreService

    repository, service, route, calls = setup(tmp_path)
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    args = dict(
        content_id=VIDEO,
        route_id=route.route_id,
        execution_id=preflight["execution_id"],
        cloud_consent=True,
        acknowledge_unknown_cost=True,
    )
    result = service.run(**args)
    backup = BackupRestoreService(
        database=tmp_path / "state.sqlite3", data_root=tmp_path / "data"
    )
    created = backup.create_backup()
    archive, _ = backup.backup_download(created.backup_id)
    preview = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert service.read(content_id=VIDEO).as_dict() == result.as_dict()
    with repository._connect() as connection:
        row = connection.execute(
            "SELECT status,input_tokens,output_tokens,cost_microusd FROM provider_calls "
            "WHERE operation='content-deep-analysis-cloud'"
        ).fetchone()
        assert tuple(row) == ("SUCCEEDED", 234, 123, None)
    with pytest.raises(DeepAnalysisRejected) as error:
        service.run(**args)
    assert error.value.status.reason_code.value == "EXECUTION_ALREADY_DISPATCHED"
    assert len(calls) == 1


def test_ambiguous_dispatch_does_not_retry(tmp_path):
    _, service, route, calls = setup(
        tmp_path, failure=TimeoutError("do not expose this provider detail")
    )
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    for _ in range(2):
        with pytest.raises(DeepAnalysisRejected) as rejection:
            service.run(
                content_id=VIDEO,
                route_id=route.route_id,
                execution_id=preflight["execution_id"],
                cloud_consent=True,
                acknowledge_unknown_cost=True,
            )
        assert rejection.value.status.reason_code.value == "DISPATCH_AMBIGUOUS"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "attack", ["provider", "model", "content", "egress", "output_language", "expiry"]
)
def test_preflight_cannot_be_substituted(tmp_path, attack):
    repository, service, route, calls = setup(tmp_path)
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    args = dict(
        content_id=VIDEO,
        route_id=route.route_id,
        execution_id=preflight["execution_id"],
        cloud_consent=True,
        acknowledge_unknown_cost=True,
    )
    if attack == "provider":
        args["route_id"] = "other-provider"
    if attack == "model":
        service._capability = DeepAnalysisCapability(
            (replace(route, model_id="other-model"),),
            authority=service._capability.authority,
        )
    if attack == "content":
        args["content_id"] = support.seed_other(tmp_path, repository)
    if attack == "egress":
        args["egress_mode"] = "FULL_TRANSCRIPT"
    if attack == "output_language":
        repository.save_global_output_language(output_language="zh-CN", now=NOW)
    if attack == "expiry":
        from datetime import timedelta

        service._clock = lambda: NOW + timedelta(minutes=11)
    with pytest.raises(DeepAnalysisRejected):
        service.run(**args)
    assert calls == []


@pytest.mark.parametrize(
    "reachable", ["NOT_CHECKED", "UNREACHABLE", "PROFILE_MISMATCH"]
)
def test_unreachable_qualified_route_is_not_production_eligible(tmp_path, reachable):
    _, service, route, calls = setup(tmp_path, reachable=reachable)
    report = service.capability_report()
    assert report["qualified"] is True
    assert report["production_eligible"] is False
    with pytest.raises(DeepAnalysisRejected):
        service.preflight(content_id=VIDEO, route_id=route.route_id)
    assert calls == []


def test_provider_error_does_not_expose_secret_or_fall_back(tmp_path, caplog):
    _, service, route, calls = setup(
        tmp_path, failure=RuntimeError("injected-test-credential")
    )
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    with pytest.raises(DeepAnalysisRejected) as error:
        service.run(
            content_id=VIDEO,
            route_id=route.route_id,
            execution_id=preflight["execution_id"],
            cloud_consent=True,
            acknowledge_unknown_cost=True,
        )
    assert "injected-test-credential" not in str(error.value)
    assert "injected-test-credential" not in caplog.text
    assert "injected-test-credential" not in json.dumps(service.capability_report())
    assert "injected-test-credential" not in json.dumps(preflight)
    assert len(calls) == 1


def test_cloud_failure_never_substitutes_an_eligible_local_route(tmp_path):
    _, service, route, calls = setup(tmp_path, failure=TimeoutError())
    local_calls = []
    local = replace(
        qualification.build_local_ollama_phase1b_route(),
        dispatch=lambda **kwargs: local_calls.append(kwargs),
    )
    service._capability = DeepAnalysisCapability(
        (route, local),
        authority=QualificationAuthority(
            (qualification.record(route), qualification.record(local))
        ),
    )
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    with pytest.raises(DeepAnalysisRejected):
        service.run(
            content_id=VIDEO,
            route_id=route.route_id,
            execution_id=preflight["execution_id"],
            cloud_consent=True,
            acknowledge_unknown_cost=True,
        )
    assert len(calls) == 1 and local_calls == []


def test_fake_credential_safe_probe_is_non_generating_and_fail_closed(
    monkeypatch, caplog
):
    import youtube_intel.openai_deep_analysis as provider

    calls = []

    def reject(request, timeout):
        calls.append((request.get_method(), request.full_url, request.data, timeout))
        raise OSError("test-only-fake-credential")

    monkeypatch.setattr(provider, "urlopen", reject)
    assert provider.probe_openai_model(None) == "NOT_CHECKED"
    assert calls == []
    assert provider.probe_openai_model("test-only-fake-credential") == "UNREACHABLE"
    assert len(calls) == 1
    assert calls[0][0] == "GET" and calls[0][2] is None
    assert "/v1/models/" in calls[0][1]
    assert "test-only-fake-credential" not in caplog.text


def test_repeated_http_post_and_real_preflight_surface(tmp_path):
    from youtube_intel.local_api import ApiError, LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService

    repository, service, route, calls = setup(tmp_path)
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        data_root=tmp_path / "data",
        vault_root=tmp_path / "vault",
        now=lambda: NOW,
        deep_analysis_service=service,
    )
    path = f"/api/v1/videos/{VIDEO}/deep-analysis"
    status, response = app.handle(
        "POST", path + "/preflight", json.dumps({"route_id": route.route_id}).encode()
    )
    assert status == 200 and calls == []
    body = json.dumps(
        {
            "route_id": route.route_id,
            "execution_id": response["preflight"]["execution_id"],
            "authorize_cloud": True,
            "acknowledge_unknown_cost": True,
        }
    ).encode()
    assert app.handle("POST", path, body)[0] == 201
    with pytest.raises(ApiError) as error:
        app.handle("POST", path, body)
    assert error.value.details["reason_code"] == "EXECUTION_ALREADY_DISPATCHED"
    assert len(calls) == 1


def test_concurrent_approval_dispatches_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    _, service, route, calls = setup(tmp_path)
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)

    def run():
        try:
            return service.run(
                content_id=VIDEO,
                route_id=route.route_id,
                execution_id=preflight["execution_id"],
                cloud_consent=True,
                acknowledge_unknown_cost=True,
            )
        except DeepAnalysisRejected:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: run(), range(2)))
    assert len(calls) == 1
    assert sum(result is not None for result in results) == 1


def test_response_handling_failure_is_not_a_second_paid_call(tmp_path, monkeypatch):
    repository, service, route, calls = setup(tmp_path)
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    monkeypatch.setattr(
        service._store,
        "persist_trusted_deep_analysis_success",
        lambda **_: (_ for _ in ()).throw(RuntimeError("response storage failed")),
    )
    for _ in range(2):
        with pytest.raises(DeepAnalysisRejected):
            service.run(
                content_id=VIDEO,
                route_id=route.route_id,
                execution_id=preflight["execution_id"],
                cloud_consent=True,
                acknowledge_unknown_cost=True,
            )
    assert len(calls) == 1
    assert service.read(content_id=VIDEO) is None
    with repository._connect() as connection:
        assert (
            connection.execute(
                "SELECT input_tokens FROM provider_calls WHERE operation='content-deep-analysis-cloud'"
            ).fetchone()[0]
            == 234
        )
        assert (
            connection.execute(
                "SELECT status FROM provider_dispatch_states"
            ).fetchone()[0]
            == "AMBIGUOUS"
        )


def test_restart_loses_preflight_instead_of_reusing_consent(tmp_path):
    _, service, route, calls = setup(tmp_path)
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    service._preflights.clear()
    with pytest.raises(DeepAnalysisRejected):
        service.run(
            content_id=VIDEO,
            route_id=route.route_id,
            execution_id=preflight["execution_id"],
            cloud_consent=True,
            acknowledge_unknown_cost=True,
        )
    assert calls == []


def test_cloud_without_authority_cannot_use_legacy_developer_seam(tmp_path):
    _, service, route, calls = setup(tmp_path)
    service._capability = DeepAnalysisCapability((route,))
    with pytest.raises(DeepAnalysisRejected):
        service.preflight(content_id=VIDEO, route_id=route.route_id)
    assert calls == []


def test_cloud_execution_identity_requires_explicit_route(tmp_path):
    _, service, route, calls = setup(tmp_path)
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    with pytest.raises(DeepAnalysisRejected):
        service.run(
            content_id=VIDEO,
            execution_id=preflight["execution_id"],
            cloud_consent=True,
            acknowledge_unknown_cost=True,
        )
    assert calls == []


def test_changed_execution_profile_invalidates_preflight(tmp_path):
    _, service, route, calls = setup(tmp_path)
    current = {"generation": None}
    original = route.build_execution_profile

    def build(**kwargs):
        profile = original(**kwargs)
        return (
            profile
            if current["generation"] is None
            else type(profile).model_validate(
                {
                    **profile.model_dump(mode="python"),
                    "generation_profile_identity": current["generation"],
                }
            )
        )

    route = replace(route, build_execution_profile=build)
    service._capability = DeepAnalysisCapability(
        (route,), authority=service._capability.authority
    )
    preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
    current["generation"] = "changed-profile"
    with pytest.raises(DeepAnalysisRejected):
        service.run(
            content_id=VIDEO,
            route_id=route.route_id,
            execution_id=preflight["execution_id"],
            cloud_consent=True,
            acknowledge_unknown_cost=True,
        )
    assert calls == []


def test_input_change_between_preflight_reads_cannot_send_undisclosed_payload(
    tmp_path, monkeypatch
):
    repository, service, route, calls = setup(tmp_path)
    original = service._prepare

    def interleaved(content_id, candidate, authorization_identity=None):
        if authorization_identity and authorization_identity.startswith("phase1c:"):
            repository.save_global_output_language(output_language="zh-CN", now=NOW)
            prepared = original(content_id, candidate, authorization_identity)
            repository.save_global_output_language(output_language="en", now=NOW)
            return prepared
        return original(content_id, candidate, authorization_identity)

    monkeypatch.setattr(service, "_prepare", interleaved)
    with pytest.raises(DeepAnalysisRejected):
        preflight = service.preflight(content_id=VIDEO, route_id=route.route_id)
        service.run(
            content_id=VIDEO,
            route_id=route.route_id,
            execution_id=preflight["execution_id"],
            cloud_consent=True,
            acknowledge_unknown_cost=True,
        )
    assert calls == []
