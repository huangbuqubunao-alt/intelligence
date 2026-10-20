"""Offline fixed-runtime contracts; no fake result grants model qualification."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta

import pytest
from conftest import _load_module

from youtube_intel import local_model_capacity as capacity
from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    KnownLocalDistillationResponseError,
    OllamaLocalDistillationTransport,
    bind_local_profile,
    build_local_distillation_request,
    local_profile_for_scope,
    local_profile_projection,
    validate_local_grounding_response,
)
from youtube_intel.local_distillation_profile import (
    PROFILE_ID,
    canonical,
    digest,
    resolve_profile,
)
from youtube_intel.local_distillation_qualification import (
    LocalExecutionPermit,
    qualification_binding,
    read_reviewed_qualifications,
)

V2 = "local-grounding-qwen35-9b-fixed-runtime-v2"
support = _load_module("test_local_grounding_profile")
old_capacity = _load_module("test_local_model_capacity")


def _value():
    return bind_local_profile(support._input(), V2)


def test_v1_projection_and_request_remain_golden():
    expected = {
        "YT_TIMED": "908575e9dbbdc6c0fa68c6ba0f2754ce1a463cc342202e09301abb79176389b7",
        "LOCAL_TIMED": "da0b574bc10225da1c8fc99e491bdb7d292ba259c8b7729d6d065d9ecc58e69b",
        "LOCAL_TEXT": "832f1243c1c25dddeb69f521e750fc0cfd352beecbcc643c15042370ea4d21d2",
    }
    for scope, golden in expected.items():
        assert digest(local_profile_for_scope(PROFILE_ID, scope)) == golden
    assert (
        digest(build_local_distillation_request(support._input()))
        == "c9959904b49362ad8f4f6caef4cad67478547390843b9aaaf0226bc0b2259be1"
    )
    assert resolve_profile(PROFILE_ID).options()["num_predict"] == 6144
    assert "num_batch" not in resolve_profile(PROFILE_ID).options()
    assert "max_response_bytes" not in local_profile_for_scope(PROFILE_ID, "YT_TIMED")


def test_fixed_variant_is_immutable_distinct_and_fully_projected():
    profile = resolve_profile(V2)
    old = resolve_profile(PROFILE_ID)
    assert profile is resolve_profile(V2)
    with pytest.raises(FrozenInstanceError):
        profile.max_content_bytes = 1
    assert profile.options() == {**old.options(), "num_predict": 8192, "num_batch": 512}
    assert (profile.model, profile.model_digest, profile.runtime) == (
        old.model,
        old.model_digest,
        old.runtime,
    )
    assert (
        profile.timeout_seconds,
        profile.max_request_bytes,
        profile.max_content_bytes,
        profile.max_response_bytes,
    ) == (300, 12288, 8101, 1000000)
    for scope in ("YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT"):
        previous = local_profile_for_scope(PROFILE_ID, scope)
        current = local_profile_for_scope(V2, scope)
        assert current == {
            **previous,
            "local_profile_id": V2,
            "options": profile.options(),
            "max_content_bytes": 8101,
            "max_response_bytes": 1000000,
        }
        assert digest(current) != digest(previous)
    assert build_local_distillation_request(
        _value()
    ) == build_local_distillation_request(_value())
    assert _value().local_profile_hash != support._input().local_profile_hash
    with pytest.raises(ValueError):
        resolve_profile(V2 + "-override")


def test_v2_complete_input_boundary_reserves_every_output_token():
    profile = resolve_profile(V2)
    request = build_local_distillation_request(_value())
    system = len(request["messages"][0]["content"].encode())
    request["messages"][1]["content"] = "汉" * ((8101 - system) // 3) + "a" * (
        (8101 - system) % 3
    )
    assert len(canonical(request)) <= 12288
    assert profile.complete_input_token_upper_bound(request) == 8191
    assert 8191 + profile.options()["num_predict"] + 1 == profile.options()["num_ctx"]
    request["messages"][1]["content"] += "a"
    with pytest.raises(ValueError):
        profile.complete_input_token_upper_bound(request)
    request["messages"][1]["content"] = "\n" * (8101 - system)
    with pytest.raises(ValueError):
        profile.complete_input_token_upper_bound(request)


@pytest.mark.parametrize(
    "profile_id,accepted,rejected", [(PROFILE_ID, 6143, 6144), (V2, 8191, 8192)]
)
def test_response_uses_resolved_profile_budget(profile_id, accepted, rejected):
    value = bind_local_profile(support._input(), profile_id)
    response = {
        "model": resolve_profile(profile_id).model,
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 100,
        "eval_count": accepted,
        "message": {"content": "{}"},
    }
    assert (
        validate_local_grounding_response(response, value, duration_ms=1).output_tokens
        == accepted
    )
    with pytest.raises(KnownLocalDistillationResponseError):
        validate_local_grounding_response(
            {**response, "eval_count": rejected}, value, duration_ms=1
        )


@pytest.mark.parametrize(
    "damage",
    [
        {"done": False},
        {"done_reason": "length"},
        {"done_reason": "timeout"},
        {"done_reason": "unknown"},
        {"prompt_eval_count": None},
        {"prompt_eval_count": True},
        {"prompt_eval_count": -1},
        {"eval_count": None},
        {"eval_count": False},
        {"eval_count": -1},
        {"eval_count": 8192},
        {"model": "other"},
        {"message": {"content": ""}},
    ],
)
def test_v2_response_retains_strict_completion_gate(damage):
    value = _value()
    response = {
        "model": resolve_profile(V2).model,
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 100,
        "eval_count": 6144,
        "message": {"content": "{}"},
    }
    with pytest.raises(KnownLocalDistillationResponseError):
        validate_local_grounding_response({**response, **damage}, value, duration_ms=1)


def _session(tmp_path, monkeypatch, *, batch=None, memory=None):
    """Real strict observer with tiny pinned-install fixtures and fake HTTP."""
    from youtube_intel.state import SQLiteStateRepository

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=datetime.now(UTC))
    data = tmp_path / "data"
    data.mkdir()
    manifests = _load_module("test_capacity_host_manifest")
    _, parent, _, binary, _ = manifests.fixture_installation(tmp_path, monkeypatch)
    root, cache = binary.parent, parent.parent.parent
    profile = replace(
        resolve_profile(V2),
        model_digest="sha256:" + parent.name.removeprefix("sha256-"),
    )
    monkeypatch.setattr(capacity, "resolve_profile", lambda _: profile)
    server = f"77 Thu Oct 01 00:00:00 2026 {root / 'ollama'} serve"
    extras = f" --log-verbosity 4 --no-log-prefix --no-log-timestamps --mmproj {cache / 'blobs/sha256-f836f08f921193f4d6b6a6952dba0a6fb116759d26a757bcb395d570d73976ca'} --flash-attn auto"
    runner = [
        ""
        if batch is None
        else old_capacity._runner(capacity, cache) + extras + f" -b {batch} -ub {batch}"
    ]
    monkeypatch.setattr(
        capacity, "processes", lambda name: server if name == "ollama" else runner[0]
    )
    if memory is not None:
        monkeypatch.setattr(capacity, "available_memory_bytes", lambda: memory)
    session = capacity.LocalCapacitySession(
        repository=repository, data_root=data, profile_id=V2
    )
    calls = []
    loaded = (
        []
        if batch is None
        else [
            {
                "name": profile.model,
                "digest": profile.model_digest,
                "runner": "llamacpp",
                "context_length": 16384,
            }
        ]
    )

    def send(path, *, method, body=None):
        calls.append((path, method, deepcopy(body)))
        if path == "/api/version":
            return {"version": profile.runtime}
        if path == "/api/tags":
            return {"models": [{"name": profile.model, "digest": profile.model_digest}]}
        if path == "/api/show":
            return {
                "template": "{{ .Prompt }}",
                "system": "",
                "messages": [],
                "model_info": {
                    "general.architecture": "qwen35",
                    "qwen35.context_length": 262144,
                    "tokenizer.ggml.model": "gpt2",
                    "tokenizer.ggml.pre": "qwen35",
                },
                "modelfile": "RENDERER qwen3.5\nPARSER qwen3.5\n",
            }
        if path == "/api/ps":
            return {"models": deepcopy(loaded)}
        assert path == "/api/chat" and method == "POST"
        assert body == {
            "model": profile.model,
            "messages": [],
            "stream": False,
            "think": True,
            "truncate": False,
            "shift": False,
            "options": profile.options(),
            "keep_alive": "5m",
        }
        loaded[:] = [
            {
                "name": profile.model,
                "digest": profile.model_digest,
                "runner": "llamacpp",
                "context_length": 16384,
            }
        ]
        runner[0] = old_capacity._runner(capacity, cache) + extras + " -b 512 -ub 512"
        return {
            "model": profile.model,
            "done": True,
            "done_reason": "load",
            "message": {"role": "assistant", "content": ""},
        }

    return session, send, calls, runner, loaded


@pytest.mark.parametrize("batch", [None, 512, 1024])
def test_v2_cold_warm_and_legacy_transition_always_load_empty_then_require_512(
    tmp_path, monkeypatch, batch
):
    session, send, calls, runner, _ = _session(tmp_path, monkeypatch, batch=batch)
    value = _value()
    request = build_local_distillation_request(value)
    assert session.prepare("exec", value, request, send)
    loads = [body for path, _, body in calls if path == "/api/chat"]
    assert len(loads) == 1 and loads[0]["messages"] == []
    assert loads[0]["options"] == request["options"]
    assert runner[0].endswith("-b 512 -ub 512")
    assert session.prepare("exec", value, request, send)
    assert len([c for c in calls if c[0] == "/api/chat"]) == 1
    assert session.ready_for_claim("exec", request)
    session.arm("exec", request)
    before = list(calls)
    session.consume("exec", request)
    assert calls == before
    with pytest.raises(RuntimeError):
        session.consume("exec", request)
    session.release()


@pytest.mark.parametrize("batch", [None, 1024])
def test_cold_and_legacy_transition_require_full_cold_ram_before_load(
    tmp_path, monkeypatch, batch
):
    session, send, calls, _, _ = _session(
        tmp_path, monkeypatch, batch=batch, memory=2 * capacity.GIB
    )
    value = _value()
    assert not session.prepare(
        "exec", value, build_local_distillation_request(value), send
    )
    assert not any(path == "/api/chat" for path, _, _ in calls)
    assert session.lease.fd is None


@pytest.mark.parametrize(
    "damage",
    [
        "batch",
        "asymmetric",
        "missing-batch",
        "binary",
        "prefix",
        "model",
        "context",
        "slot",
        "parallel",
        "server",
        "concurrent",
    ],
)
def test_transition_unknown_or_busy_state_rejects_before_load(
    tmp_path, monkeypatch, damage
):
    session, send, calls, runner, loaded = _session(tmp_path, monkeypatch, batch=1024)
    other = None
    if damage == "batch":
        runner[0] = runner[0].replace("1024", "256")
    elif damage == "asymmetric":
        runner[0] = runner[0].replace("-ub 1024", "-ub 512")
    elif damage == "missing-batch":
        runner[0] = runner[0].replace(" -ub 1024", "")
    elif damage == "binary":
        runner[0] = runner[0].replace("llama-server", "unknown-runner")
    elif damage == "prefix":
        runner[0] = runner[0].replace(
            str(capacity.ROOT / "llama-server"),
            "/other/" + str(capacity.ROOT / "llama-server"),
        )
    elif damage == "model":
        runner[0] = runner[0].replace("sha256-02d45", "sha256-unknown-02d45")
    elif damage == "context":
        runner[0] = runner[0].replace("-c 16384", "-c 32768")
    elif damage == "slot":
        loaded[0]["context_length"] = 32768
    elif damage == "parallel":
        runner[0] = runner[0].replace("-np 1", "-np 2")
    elif damage == "server":
        original = capacity.processes
        monkeypatch.setattr(
            capacity,
            "processes",
            lambda name: (
                original(name) + ("\nunknown serve" if name == "ollama" else "")
            ),
        )
    else:
        other = capacity.ApplicationHeavyLease(
            repository=session.repository, data_root=session.data_root
        )
        assert other.acquire()
    value = _value()
    assert not session.prepare(
        "exec", value, build_local_distillation_request(value), send
    )
    assert not any(path == "/api/chat" for path, _, _ in calls)
    assert session.lease.fd is None
    if other:
        other.release()


@pytest.mark.parametrize(
    "damage", ["batch", "context", "nonempty", "eval", "model", "done"]
)
def test_transition_never_ready_until_final_strict_observation(
    tmp_path, monkeypatch, damage
):
    session, send, calls, runner, loaded = _session(tmp_path, monkeypatch, batch=1024)

    def changed(path, **kwargs):
        result = send(path, **kwargs)
        if path == "/api/chat":
            if damage == "batch":
                runner[0] = runner[0].replace("512", "1024")
            elif damage == "context":
                loaded[0]["context_length"] = 8192
            elif damage == "nonempty":
                result["message"]["content"] = "generated"
            elif damage == "eval":
                result["eval_count"] = 0
            elif damage == "model":
                result["model"] = "other"
            else:
                result["done"] = False
        return result

    value = _value()
    request = build_local_distillation_request(value)
    assert not session.prepare("exec", value, request, changed)
    assert len([c for c in calls if c[0] == "/api/chat"]) == 1
    assert not session.ready_for_claim("exec", request)
    assert session.lease.fd is None


@pytest.mark.parametrize(
    "damage", ["old-value", "old-request", "value", "hash", "profile"]
)
def test_session_binds_profile_complete_value_and_exact_request_before_io(
    tmp_path, monkeypatch, damage
):
    session, send, calls, _, _ = _session(tmp_path, monkeypatch)
    value, request = _value(), build_local_distillation_request(_value())
    if damage == "old-value":
        value = support._input()
    elif damage == "old-request":
        request = build_local_distillation_request(support._input())
    elif damage == "value":
        value = replace(value, video_title="Changed source")
    elif damage == "hash":
        value = replace(value, local_profile_hash="0" * 64)
    else:
        value = replace(value, local_profile_id="unknown")
    assert not session.prepare("exec", value, request, send)
    assert calls == [] and session.lease.fd is None


def test_reprepare_cannot_reuse_proof_for_changed_value_or_profile(
    tmp_path, monkeypatch
):
    session, send, calls, _, _ = _session(tmp_path, monkeypatch)
    value = _value()
    request = build_local_distillation_request(value)
    assert session.prepare("exec", value, request, send)
    before = list(calls)
    assert not session.prepare("exec", support._input(), request, send)
    assert not session.prepare(
        "exec", replace(value, semantic_hash="d" * 64), request, send
    )
    assert calls == before
    session.release()


def test_resigned_generic_permit_cannot_authorize_v2_generation(tmp_path, monkeypatch):
    value = _value()
    projection = local_profile_projection(value)
    now = datetime.now(UTC)
    data = {
        "version": "local-grounding-once-permit-v1",
        "case_id": "real-deepthink-en",
        "execution_id": "offline-case",
        "input_hash": value.semantic_hash,
        "context_hash": "a" * 64,
        "request_hash": digest(build_local_distillation_request(value)),
        "binding": qualification_binding(projection),
        "source_manifest_hash": "b" * 64,
        "capacity_proof_hash": "c" * 64,
        "runtime_proof_hash": "d" * 64,
        "harness_hash": "e" * 64,
        "freeze_hash": "f" * 64,
        "prior_review_hashes": [],
        "issued_at": (now - timedelta(seconds=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=1)).isoformat(),
    }
    permit = LocalExecutionPermit.model_validate({**data, "permit_hash": digest(data)})
    assert permit.matches(
        projection, value.semantic_hash, data["request_hash"], value.output_language
    )
    profile = resolve_profile(V2)
    transport = OllamaLocalDistillationTransport(
        settings=LocalScoringSettings(
            model=profile.model, expected_model_digest=profile.model_digest
        ),
        local_profile_id=V2,
        qualification_permit=permit,
        before_dispatch=lambda *a: pytest.fail("v2 must not arm"),
    )
    monkeypatch.setattr(
        transport,
        "_request",
        lambda *a, **k: pytest.fail("zero real or fake generation"),
    )
    assert transport.is_authorized_for(value)
    assert not transport.is_authorized_for_qualification(value)
    assert not transport.is_authorized_for_normal_production(value)
    assert not read_reviewed_qualifications().permits(projection, value.output_language)
    assert not transport.prepare_execution(
        permit.execution_id, value, qualification=True
    )
    with pytest.raises(RuntimeError):
        transport.generate(value)


@pytest.mark.parametrize("damage", ["suffix-binary", "request-during-probe"])
def test_identity_cannot_change_during_or_before_empty_probe(
    tmp_path, monkeypatch, damage
):
    session, send, calls, runner, _ = _session(tmp_path, monkeypatch, batch=1024)
    value = _value()
    request = build_local_distillation_request(value)
    if damage == "suffix-binary":
        runner[0] = runner[0].replace("llama-server ", "llama-server-unknown ")

    def changed(path, **kwargs):
        result = send(path, **kwargs)
        if damage == "request-during-probe" and path == "/api/chat":
            request["options"]["num_batch"] = 1024
        return result

    assert not session.prepare("exec", value, request, changed)
    assert not session.ready_for_claim("exec", request)
    assert session.lease.fd is None
    assert len([c for c in calls if c[0] == "/api/chat"]) == (
        0 if damage == "suffix-binary" else 1
    )


@pytest.mark.parametrize(
    "damage", ["expired", "runner", "file", "wire", "foreign-thread"]
)
def test_v2_claim_rechecks_host_ttl_wire_and_thread_before_arming(
    tmp_path, monkeypatch, damage
):
    import threading

    session, send, calls, runner, _ = _session(tmp_path, monkeypatch)
    value = _value()
    request = build_local_distillation_request(value)
    assert session.prepare("exec", value, request, send)
    assert session.matches_value(value)
    assert not session.matches_value(replace(value, semantic_hash="d" * 64))
    before = list(calls)
    if damage == "expired":
        monkeypatch.setattr(capacity, "monotonic", lambda: 1e20)
    elif damage == "runner":
        runner[0] = runner[0].replace("-b 512", "-b 1024")
    elif damage == "file":
        (capacity.ROOT / "ollama").write_bytes(b"changed runtime")
    elif damage == "wire":
        request = dict(reversed(list(request.items())))
    else:
        failures = []

        def foreign():
            assert not session.ready_for_claim("exec", request)
            with pytest.raises(capacity.CapacityUnavailable):
                session.arm("exec", request)
            with pytest.raises(RuntimeError):
                session.consume("exec", request)
            session.release()
            failures.append(True)

        thread = threading.Thread(target=foreign)
        thread.start()
        thread.join(5)
        assert not thread.is_alive() and failures == [True]
        assert session.ready_for_claim("exec", request)
        assert calls == before
        session.release()
        return
    assert not session.ready_for_claim("exec", request)
    with pytest.raises(capacity.CapacityUnavailable):
        session.arm("exec", request)
    with pytest.raises(RuntimeError):
        session.consume("exec", request)
    assert calls == before
    session.release()


def test_resealed_v2_receipts_are_refused_by_original_v1_reader_and_harness(
    tmp_path, monkeypatch
):
    qualification = _load_module("test_local_grounding_qualification")
    record = qualification._audit_fixture()
    projection = local_profile_projection(_value())
    record["binding"] = qualification_binding(projection)
    for case in record["cases"]:
        case["profile_hash"] = record["binding"]["profile_hash"]
    assert not qualification.QualificationRecord.model_validate(
        qualification._seal(record)
    ).permits(projection, "en", qualification.NOW)
    harness = _load_module("test_local_grounding_harness")._harness()
    permit_data = {
        "version": "local-grounding-once-permit-v1",
        "case_id": "real-deepthink-en",
        "execution_id": "offline",
        "input_hash": "a" * 64,
        "context_hash": "b" * 64,
        "request_hash": "c" * 64,
        "binding": qualification_binding(projection),
        "source_manifest_hash": "d" * 64,
        "capacity_proof_hash": "e" * 64,
        "runtime_proof_hash": "f" * 64,
        "harness_hash": "1" * 64,
        "freeze_hash": "2" * 64,
        "prior_review_hashes": [],
        "issued_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
    }
    prepared = {
        "case_id": "real-deepthink-en",
        "database": str(tmp_path / "isolated.sqlite"),
        "data_root": str(tmp_path / "data"),
        "workspace_ownership": {},
        "binding": qualification_binding(projection),
    }
    freeze = {
        "version": "local-grounding-freeze-v1",
        "status": "PRE_OUTPUT_REVIEWED",
        "profile_id": V2,
    }
    permit = {**permit_data, "permit_hash": digest(permit_data)}
    monkeypatch.setattr(harness, "owned_workspace", lambda *a: {})
    monkeypatch.setattr(
        harness,
        "read_object",
        lambda path: (
            prepared
            if path.name == "prepared.json"
            else freeze
            if path.name == "freeze.json"
            else permit
        ),
    )
    with pytest.raises(ValueError, match="unreviewed"):
        harness.validate_execution_package(
            tmp_path, tmp_path / "permit.json", tmp_path / "freeze.json"
        )


def test_v2_no_session_can_bypass_explicit_generation_refusal(tmp_path, monkeypatch):
    session, send, calls, _, _ = _session(tmp_path, monkeypatch)
    value = _value()
    request = build_local_distillation_request(value)
    assert session.prepare("exec", value, request, send)
    session.arm("exec", request)
    profile = resolve_profile(V2)
    transport = OllamaLocalDistillationTransport(
        settings=LocalScoringSettings(
            model=profile.model, expected_model_digest=profile.model_digest
        ),
        local_profile_id=V2,
    )
    transport._capacity_session, transport._prepared_execution = session, "exec"
    monkeypatch.setattr(
        transport, "_request", lambda *a, **k: pytest.fail("v2 never generates")
    )
    with pytest.raises(RuntimeError, match="load-only"):
        transport.generate(value)
    assert not session._consumed and not transport.last_grounding_post_attempted
    session.release()
