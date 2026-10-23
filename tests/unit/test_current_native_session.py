"""ENGINEERING_ONLY local IO seams, never a model qualification grant."""
from dataclasses import replace

import pytest
from conftest import _load_module

from youtube_intel import local_model_capacity as capacity
from youtube_intel.distillation import (
    build_local_distillation_request,
    local_profile_for_scope,
)
from youtube_intel.local_distillation_profile import CURRENT_RUNTIME_PROFILE_ID as SHORT
from youtube_intel.local_distillation_profile import digest, resolve_profile

old = _load_module("test_local_model_capacity")


def fixture(tmp_path, monkeypatch):
    tmp_path.mkdir(parents=True, exist_ok=True)
    previous, old_send, calls, loaded = old._session(tmp_path, monkeypatch)
    previous.release()
    session = capacity.LocalCapacitySession(repository=previous.repository, data_root=previous.data_root, profile_id=SHORT)
    value = replace(old.support._input(), local_profile_id=SHORT, local_profile_hash=digest(local_profile_for_scope(SHORT, "YT_TIMED")))
    profile = resolve_profile(SHORT)
    native_calls = []
    def send(path, **kwargs):
        if path == "/api/version":
            return {"version": profile.runtime}
        return old_send(path, **kwargs)
    def native(host, path, *, body=None):
        native_calls.append((host, path, body))
        if path == "/tokenize":
            return {"tokens": [42] * 100}
        if path == "/slots":
            return [{"id": 0, "n_ctx": 16384, "is_processing": False, "speculative": False}]
        assert path == "/props"
        return {"default_generation_settings": {"n_ctx": 16384}, "total_slots": 1, "is_sleeping": False, "endpoint_slots": True}
    monkeypatch.setattr(capacity, "native_runner_request", native, raising=False)
    return session, value, send, calls, native_calls, loaded


def test_current_prepare_reads_full_native_tokens_and_actual_slot_before_one_shot(tmp_path, monkeypatch):
    session, value, send, calls, native, loaded = fixture(tmp_path, monkeypatch)
    request = build_local_distillation_request(value)
    assert session.prepare("current", value, request, send)
    assert [path for _, path, _ in native] == ["/props", "/slots", "/tokenize", "/props", "/slots"]
    token_body = native[2][2]
    from youtube_intel.local_native_capacity import render_qwen35_prompt
    assert token_body == {"content": render_qwen35_prompt(request), "add_special": True, "parse_special": True}
    assert session.native_witness.input_tokens == 100
    assert session.native_witness.request_hash == digest(request)
    assert loaded[0]["context_length"] == 16384
    assert session.ready_for_claim("current", request)
    session.arm("current", request)
    before = list(calls), list(native)
    session.consume("current", request)
    assert before == (calls, native)
    with pytest.raises(RuntimeError):
        session.consume("current", request)
    session.release()


@pytest.mark.parametrize("damage", ["slot", "unknown-slot", "overflow", "no-tokens", "host-change", "hidden-messages", "expired", "foreign-thread", "busy-slot", "slot-bool", "sleeping", "parallel", "speculative"])
def test_current_native_failure_never_mints_readiness(tmp_path, monkeypatch, damage):
    session, value, send, calls, native_calls, _ = fixture(tmp_path, monkeypatch)
    native = capacity.native_runner_request
    def changed(host, path, *, body=None):
        result = native(host, path, body=body)
        if path == "/props" and damage in {"sleeping", "parallel"}:
            result["is_sleeping" if damage == "sleeping" else "total_slots"] = True if damage == "sleeping" else 2
        if path == "/slots" and damage in {"busy-slot", "slot-bool", "speculative"}:
            result[0][{"busy-slot": "is_processing", "slot-bool": "n_ctx", "speculative": "speculative"}[damage]] = True
        if damage in {"slot", "unknown-slot"} and path == "/props":
            return {"default_generation_settings": {"n_ctx": 8192}, "total_slots": 1, "is_sleeping": False, "endpoint_slots": True} if damage == "slot" else {}
        if damage == "overflow" and path == "/tokenize":
            return {"tokens": [42] * (16384 - 8192 - 1)}
        if damage == "no-tokens" and path == "/tokenize":
            return {"count": 100}
        if damage == "host-change" and path == "/tokenize":
            monkeypatch.setattr(capacity.HostObservation, "is_current", lambda self: False)
        return result
    def metadata(path, **kwargs):
        result = send(path, **kwargs)
        if damage == "hidden-messages" and path == "/api/show":
            result["messages"] = [{"role": "user", "content": "hidden"}]
        return result
    monkeypatch.setattr(capacity, "native_runner_request", changed)
    request = build_local_distillation_request(value)
    if damage in {"expired", "foreign-thread"}:
        assert session.prepare("current", value, request, metadata)
        if damage == "expired":
            monkeypatch.setattr(capacity, "monotonic", lambda: 10**20)
            assert not session.ready_for_claim("current", request)
        else:
            import threading
            result = []
            thread = threading.Thread(target=lambda: result.append(session.ready_for_claim("current", request)))
            thread.start()
            thread.join()
            assert result == [False]
        session.release()
    else:
        assert not session.prepare("current", value, request, metadata)
        assert not session.ready_for_claim("current", request)
        assert session.lease.fd is None
    assert not any(path == "/api/chat" and body.get("messages") for path, _, body in calls if body)


def test_long_session_rebuilds_the_persisted_complete_proof_and_never_trusts_caller_bytes(tmp_path, monkeypatch):
    import json

    from youtube_intel.local_distillation_qualification import LONG_CURRENT
    from youtube_intel.long_distillation_execution import rebuild_long, reserve_pending

    lifecycle = _load_module("test_long_completion_lifecycle")
    (tmp_path / "full").mkdir()
    repo, root, sid, vid, service, transport, lease = lifecycle.ready_fixture(tmp_path / "full", full=True)
    eid = reserve_pending(service, source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="native-proof")
    with repo._connect() as connection:
        rebuilt = rebuild_long(repo, connection, eid)
    lease.release()
    _short, _value, send, calls, _native, loaded = fixture(tmp_path / "native", monkeypatch)
    def current_send(path, **kwargs):
        result = send(path, **kwargs)
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
    session = capacity.LocalCapacitySession(repository=repo, data_root=root, profile_id=LONG_CURRENT)
    changed = replace(rebuilt.prepared, request_wire=rebuilt.prepared.request_wire + b" ")
    assert not session.prepare_long(eid, changed, current_send)
    assert not calls  # Persisted request equality precedes even metadata IO.
    assert session.prepare_long(eid, rebuilt.prepared, current_send)
    assert session.native_witness.context_tokens == 32768 and session.native_witness.input_tokens == 22000
    assert session.matches_long(eid, rebuilt.prepared)
    assert not session.matches_long("foreign", rebuilt.prepared)
    request = json.loads(rebuilt.prepared.request_wire)
    session.arm(eid, request)
    session.consume(eid, request)
    with pytest.raises(RuntimeError):
        session.consume(eid, request)
    assert repo.get_distillation_execution(eid).invocation_count == 0
    session.release()


@pytest.mark.parametrize("damage", ["redirect", "oversize", "duplicate-json", "host-change", "wrong-shape", "port"])
def test_native_http_adapter_binds_local_port_bounded_no_redirect_and_strict_json(tmp_path, monkeypatch, damage):
    import json

    runner = old._runner(capacity, tmp_path) + " -b 512 -ub 512"
    if damage == "port":
        runner = runner.replace("--port 12345", "--port 80")
    host = capacity.HostObservation((), "fixture", runner)
    monkeypatch.setattr(capacity.HostObservation, "is_current", lambda self: True)
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def geturl(self):
            return "http://remote.invalid/tokenize" if damage == "redirect" else self.url
        def read(self, maximum):
            assert maximum == 1_000_001
            if damage == "host-change":
                monkeypatch.setattr(capacity.HostObservation, "is_current", lambda self: False)
            return {"oversize": b"x" * 1_000_001, "duplicate-json": b'{"tokens":[],"tokens":[1]}',
                "wrong-shape": b"[]"}.get(damage, json.dumps({"tokens": [42]}).encode())
    class Opener:
        def open(self, request, *, timeout):
            assert request.full_url.startswith("http://127.0.0.1:") and timeout == 5
            response = Response()
            response.url = request.full_url
            return response
    monkeypatch.setattr(capacity.urllib.request, "build_opener", lambda *handlers: Opener())
    with pytest.raises((OSError, ValueError)):
        capacity.native_runner_request(host, "/tokenize", body={"content": "x", "add_special": True, "parse_special": True})


@pytest.mark.parametrize("warm", [False, True])
def test_current_cold_and_warm_always_reassert_same_empty_load_contract(tmp_path, monkeypatch, warm):
    session, value, send, calls, native, loaded = fixture(tmp_path, monkeypatch)
    if warm:
        loaded.append({"name": value.selected_model, "digest": resolve_profile(SHORT).model_digest,
            "runner": "llamacpp", "context_length": 16384})
    # The fake load must replace the slot, not invent two loaded models.
    def load(path, **kwargs):
        if path == "/api/chat":
            loaded.clear()
        return send(path, **kwargs)
    assert session.prepare("current", value, build_local_distillation_request(value), load)
    loads = [body for path, _, body in calls if path == "/api/chat"]
    assert len(loads) == 1 and loads[0]["messages"] == []
    assert loads[0]["truncate"] is loads[0]["shift"] is False
    assert loads[0]["options"] == resolve_profile(SHORT).options()
    session.release()


@pytest.mark.parametrize("context,batch,allowed", [(16384, 512, True), (32768, 512, True),
    (16384, 1024, True), (32768, 1024, False), (8192, 512, False), (16384, 256, False)])
def test_current_load_only_reconfiguration_accepts_only_known_finite_shapes(tmp_path, monkeypatch, context, batch, allowed):
    runner = old._runner(capacity, tmp_path).replace("-c 16384", "-c " + str(context)) + f" -b {batch} -ub {batch}"
    monkeypatch.setattr(capacity, "processes", lambda binary: runner)
    seen = []
    def observe(**kwargs):
        seen.append(kwargs)
        if (kwargs["context_tokens"], kwargs["fixed_batch"]) not in {(16384, 512), (32768, 512), (16384, 1024)}:
            raise capacity.CapacityUnavailable("unknown shape")
        return capacity.HostObservation((), "fixture", runner)
    monkeypatch.setattr(capacity, "_observe_host", observe)
    if allowed:
        result = capacity.observe_current_load_only_reconfiguration(data_root=tmp_path, profile_id=SHORT)
        assert result.runner == runner and seen[0]["load_only_reconfiguration"] is True
    else:
        with pytest.raises(capacity.CapacityUnavailable):
            capacity.observe_current_load_only_reconfiguration(data_root=tmp_path, profile_id=SHORT)


def test_current_expiry_between_arm_and_consume_never_sends(tmp_path, monkeypatch):
    session, value, send, calls, native, _ = fixture(tmp_path, monkeypatch)
    request = build_local_distillation_request(value)
    assert session.prepare("current", value, request, send)
    session.arm("current", request)
    monkeypatch.setattr(capacity, "monotonic", lambda: 10**20)
    before = list(calls), list(native)
    with pytest.raises(RuntimeError):
        session.consume("current", request)
    assert before == (calls, native)
    session.release()
