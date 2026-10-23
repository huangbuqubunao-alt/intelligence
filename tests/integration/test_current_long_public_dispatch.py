"""ENGINEERING_ONLY normal public routing and one-shot native integration."""

import pytest
from conftest import _load_module

from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    OllamaLocalDistillationTransport,
    PersonalizedDistillationService,
)
from youtube_intel.local_distillation_profile import CURRENT_RUNTIME_PROFILE_ID as SHORT
from youtube_intel.local_distillation_profile import resolve_profile
from youtube_intel.local_distillation_qualification import LONG_CURRENT
from youtube_intel.long_distillation_persistence import RECEIPTS
from youtube_intel.source_policy import SourcePolicyApplicationService

life = _load_module("test_long_completion_lifecycle")


def fixture(tmp_path, monkeypatch, *, qualified=True):
    repo, root, sid, vid, previous, _old, lease = life.ready_fixture(tmp_path)
    lease.release()
    profile = resolve_profile(SHORT)
    transport = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model=profile.model,
        expected_model_digest=profile.model_digest), local_profile_id=SHORT)
    # Explicit audit seam, not a reviewed registry or real qualification.
    monkeypatch.setattr(transport._local_authority, "permits", lambda projection, language, **kw:
        qualified and projection["local_profile_id"] == LONG_CURRENT)
    service = PersonalizedDistillationService(repo, SourcePolicyApplicationService(repo, now=lambda: life.wait.NOW),
        transport, previous._budget, now=lambda: life.wait.NOW)
    return repo, root, sid, vid, service, transport


@pytest.mark.parametrize("kind", ["INTELLIGENCE", "NO_NEW_INTELLIGENCE", "REJECTED"])
def test_public_long_new_command_completes_one_true_branch_and_never_redispatches(tmp_path, monkeypatch, kind):
    from youtube_intel.long_distillation_execution import rebuild_long
    repo, root, sid, vid, service, transport = fixture(tmp_path, monkeypatch)
    reservation = service.reserve_distillation_execution(source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="public")
    eid = reservation.execution_id
    assert repo.get_distillation_execution(eid).status == "PENDING"
    with repo._connect() as c:
        rebuilt = rebuild_long(repo, c, eid)
    storage = _load_module("test_long_completion_storage_contract")
    raw = storage.receipt(rebuilt.proof, kind)["public_wire"]
    calls = []
    monkeypatch.setattr(transport, "prepare_long_execution", lambda *args, **kw: True)
    monkeypatch.setattr(transport, "arm_long_for_claim", lambda *args, **kw: True)
    monkeypatch.setattr(transport, "armed_long_for_claim", lambda *args, **kw: True)
    def generate(execution_id, prepared):
        calls.append((execution_id, prepared))
        assert repo.get_distillation_execution(eid).invocation_count == 1
        return {"model": transport.actual_model, "done": True, "done_reason": "stop",
            "prompt_eval_count": 100, "eval_count": 20, "message": {"content": raw}}
    monkeypatch.setattr(transport, "generate_long", generate)
    result = service.continue_reserved_distillation(eid)
    expected = {"INTELLIGENCE": "SUCCEEDED", "NO_NEW_INTELLIGENCE": "SUCCEEDED_NO_NEW_INTELLIGENCE", "REJECTED": "REJECTED_OUTPUT"}[kind]
    assert result.status.value == expected
    assert repo.get_distillation_resource_usage(eid).invocation_count == 1
    assert service.continue_reserved_distillation(eid).status.value == expected
    assert len(calls) == 1
    with repo._connect() as c:
        assert c.execute(f"SELECT count(*) FROM {RECEIPTS} WHERE execution_id=?", (eid,)).fetchone()[0] == 1


@pytest.mark.parametrize("failure", ["prepare", "prepare-exception", "arm", "budget", "unknown"])
def test_public_long_preclaim_failure_is_durable_wait_but_claimed_unknown_never_retries(tmp_path, monkeypatch, failure):
    repo, root, sid, vid, service, transport = fixture(tmp_path, monkeypatch)
    reservation = service.reserve_distillation_execution(source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="failure")
    eid = reservation.execution_id
    assert repo.get_distillation_execution(eid).status == "PENDING"
    calls = []
    def prepare(*args, **kw):
        if failure == "prepare-exception":
            raise OSError("ENGINEERING_ONLY actual prepare error")
        return failure != "prepare"
    monkeypatch.setattr(transport, "prepare_long_execution", prepare)
    monkeypatch.setattr(transport, "arm_long_for_claim", lambda *args, **kw: failure != "arm")
    monkeypatch.setattr(transport, "armed_long_for_claim", lambda *args, **kw: True)
    def unknown(*args):
        calls.append(1)
        raise OSError("ENGINEERING_ONLY actual result unknown")
    monkeypatch.setattr(transport, "generate_long", unknown)
    if failure == "budget":
        service._budget = life.wait.support._FakeBudget(False)
    if failure in {"unknown", "prepare-exception"}:
        with pytest.raises(OSError):
            service.continue_reserved_distillation(eid)
    else:
        service.continue_reserved_distillation(eid)
    record = repo.get_distillation_execution(eid)
    assert record.status == ("PENDING" if failure == "unknown" else "WAITING_BUDGET" if failure == "budget" else "WAITING_MODEL")
    assert record.invocation_count == (failure == "unknown")
    service.continue_reserved_distillation(eid)
    assert len(calls) == (failure == "unknown")
    if failure not in {"unknown", "budget"}:
        repo.cancel_waiting_model_execution(eid, video_id=vid, now=life.wait.NOW)
        assert repo.get_distillation_execution(eid).status == "CANCELLED"
    with repo._connect() as c:
        assert not c.execute(f"SELECT 1 FROM {RECEIPTS} WHERE execution_id=?", (eid,)).fetchone()


def test_current_service_session_profile_and_unqualified_public_wait(tmp_path, monkeypatch):
    repo, root, sid, vid, service, transport = fixture(tmp_path, monkeypatch, qualified=False)
    assert transport._capacity_session._profile_id == SHORT
    reservation = service.reserve_distillation_execution(source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="not-qualified")
    assert repo.get_distillation_execution(reservation.execution_id).status == "WAITING_MODEL"
    assert service.continue_reserved_distillation(reservation.execution_id).status.value == "WAITING_MODEL"


def test_current_factory_and_settings_select_same_current_identity_without_grant(tmp_path, monkeypatch):
    from youtube_intel.runtime_composition import (
        build_production_local_distillation_transport,
        local_distillation_capabilities,
    )
    profile = resolve_profile(SHORT)
    transport = build_production_local_distillation_transport(LocalScoringSettings(model=profile.model,
        expected_model_digest=profile.model_digest))
    assert transport.local_profile_id == SHORT
    states = local_distillation_capabilities()
    assert len(states) == 6 and {row["profile_id"] for row in states} == {SHORT}
    assert all(row["status"] == "NOT_QUALIFIED" for row in states)


def test_ordinary_service_uses_actual_native_session_then_one_post(tmp_path, monkeypatch):
    from youtube_intel import local_model_capacity as capacity
    native_support = _load_module("test_current_native_session")
    repo, root, sid, vid, service, transport = fixture(tmp_path, monkeypatch)
    session, _value, metadata, calls, native_calls, loaded = native_support.fixture(tmp_path / "native", monkeypatch)
    session.release()
    posts = []
    def request(path, **kwargs):
        body = kwargs.get("body")
        if path == "/api/chat" and body.get("messages"):
            from youtube_intel.long_distillation_execution import rebuild_long
            assert repo.get_distillation_execution(eid).invocation_count == 1
            # Metadata probing is forbidden once this actual dispatch begins.
            monkeypatch.setattr(capacity, "native_runner_request", lambda *a, **k: pytest.fail("post-claim probe"))
            posts.append(body)
            with repo._connect() as c:
                rebuilt = rebuild_long(repo, c, eid)
            raw = _load_module("test_long_completion_storage_contract").receipt(rebuilt.proof, "INTELLIGENCE")["public_wire"]
            return {"model": transport.actual_model, "done": True, "done_reason": "stop",
                "prompt_eval_count": 22000, "eval_count": 20, "message": {"content": raw}}
        result = metadata(path, **kwargs)
        if path == "/api/chat":
            loaded[0]["context_length"] = 32768
        return result
    def native(host, path, *, body=None):
        if path == "/props":
            return {"default_generation_settings": {"n_ctx": 32768}, "total_slots": 1,
                "is_sleeping": False, "endpoint_slots": True}
        if path == "/slots":
            return [{"id": 0, "n_ctx": 32768, "is_processing": False, "speculative": False}]
        return {"tokens": [42] * 22000}
    monkeypatch.setattr(capacity, "native_runner_request", native)
    monkeypatch.setattr(transport, "_request", request)
    eid = service.reserve_distillation_execution(source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="native-public").execution_id
    assert service.continue_reserved_distillation(eid).status.value == "SUCCEEDED"
    assert len(posts) == 1
    assert transport._long_capacity_session.lease.fd is None
    assert service.continue_reserved_distillation(eid).status.value == "SUCCEEDED" and len(posts) == 1


@pytest.mark.parametrize("short_qualified,long_qualified", [(True, False), (False, True)])
def test_long_content_preflight_uses_precise_independent_profile(tmp_path, monkeypatch, short_qualified, long_qualified):
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.local_distillation_qualification import qualification_projection
    repo, root, sid, vid, service, transport = fixture(tmp_path, monkeypatch, qualified=long_qualified)
    rows = tuple(transport._local_authority.scope_status(qualification_projection(SHORT, scope), language)
        for scope in ("YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT") for language in ("en", "zh-CN"))
    rows = tuple({**row, "status": "QUALIFIED" if short_qualified else "NOT_QUALIFIED"} for row in rows)
    # This read-only projection neither creates tasks nor probes/loads a model.
    from youtube_intel.orchestration_service import ProductOrchestrationService
    app = LocalApiApplication(repo, ProductOrchestrationService(repo, now=lambda: life.wait.NOW),
        distillation_service=service, data_root=root,
        local_distillation_capabilities=lambda: rows, local_distillation_available=True)
    before = life.wait._inventory(repo, root)
    status = app._content_local_intelligence_status(vid, sid)
    assert status["profile_id"] == LONG_CURRENT
    assert status["qualification_status"] == ("QUALIFIED" if long_qualified else "NOT_QUALIFIED")
    assert status["request_state"] == ("ELIGIBLE_FOR_ADMISSION" if long_qualified else "WAITING_MODEL")
    assert life.wait._inventory(repo, root) == before


@pytest.mark.parametrize("damage", ["redirect", "duplicates", "oversize"])
def test_current_public_transport_refuses_endpoint_or_raw_response_ambiguity(tmp_path, monkeypatch, damage):
    import json
    import urllib.request
    repo, root, sid, vid, service, transport = fixture(tmp_path, monkeypatch)
    payload = json.dumps({"model": transport.actual_model, "done": True}).encode()
    if damage == "duplicates":
        payload = b'{"done":true,"done":false}'
    elif damage == "oversize":
        payload = b"x" * 1_000_001
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def geturl(self):
            return "http://remote.invalid/api/chat" if damage == "redirect" else "http://127.0.0.1:11434/api/chat"
        def read(self, limit):
            assert limit == 1_000_001
            return payload
    class Opener:
        def open(self, request, *, timeout):
            assert request.full_url == "http://127.0.0.1:11434/api/chat" and timeout == 300
            return Response()
    def opener(*handlers):
        assert any(isinstance(handler, urllib.request.ProxyHandler) and handler.proxies == {} for handler in handlers)
        return Opener()
    monkeypatch.setattr(urllib.request, "build_opener", opener)
    with pytest.raises((ValueError, RuntimeError)):
        transport._request("/api/chat", method="POST", body={"fixture": True})
    with repo._connect() as connection:
        assert connection.execute("SELECT count(*) FROM distillation_execution_checkpoints").fetchone()[0] == 0
