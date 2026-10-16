"""Offline capacity/preflight contracts; these fixtures grant no qualification."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from conftest import _load_module

from youtube_intel.distillation import build_local_distillation_request
from youtube_intel.local_distillation_profile import (
    PROFILE_ID,
    canonical,
    resolve_profile,
)

support = _load_module("test_local_grounding_profile")


def test_capacity_contract_is_exact_chat_and_leaves_full_output_reserve():
    request = build_local_distillation_request(support._input())
    profile = resolve_profile(PROFILE_ID)
    assert request["options"]["num_ctx"] == 16384
    assert request["truncate"] is request["shift"] is False
    assert profile.max_request_bytes == 12288 and profile.max_content_bytes == 8192
    bound = profile.complete_input_token_upper_bound(request)
    assert bound == sum(len(m["content"].encode()) for m in request["messages"]) + 90
    assert bound + 6144 + 1 <= 16384


@pytest.mark.parametrize(
    "damage",
    [
        "extra",
        "role",
        "history",
        "images",
        "tools",
        "schema",
        "model",
        "options",
        "shift",
        "truncate",
        "think",
    ],
)
def test_capacity_rejects_unknown_or_overridden_request_contract(damage):
    request = deepcopy(build_local_distillation_request(support._input()))
    if damage == "extra":
        request["context"] = []
    elif damage == "role":
        request["messages"][0]["role"] = "user"
    elif damage == "history":
        request["messages"].append({"role": "assistant", "content": "x"})
    elif damage == "images":
        request["messages"][1]["images"] = []
    elif damage == "tools":
        request["tools"] = []
    elif damage == "schema":
        request["format"] = {"type": "object"}
    elif damage == "model":
        request["model"] = "qwen3:8b"
    elif damage == "options":
        request["options"]["num_ctx"] = 32768
    else:
        request[damage] = True if damage in {"shift", "truncate"} else False
    with pytest.raises(ValueError):
        resolve_profile(PROFILE_ID).complete_input_token_upper_bound(request)


def test_content_utf8_boundary_is_independent_of_json_body_boundary():
    profile = resolve_profile(PROFILE_ID)
    request = build_local_distillation_request(support._input())
    system = len(request["messages"][0]["content"].encode())
    request["messages"][1]["content"] = "汉" * ((8192 - system) // 3) + "a" * (
        (8192 - system) % 3
    )
    assert len(canonical(request)) <= 12288
    assert profile.complete_input_token_upper_bound(request) == 8282
    request["messages"][1]["content"] += "a"
    with pytest.raises(ValueError):
        profile.complete_input_token_upper_bound(request)
    request["messages"][1]["content"] = "\n" * (8192 - system)
    assert len(canonical(request)) > 12288
    with pytest.raises(ValueError):
        profile.complete_input_token_upper_bound(request)


def _session(tmp_path, monkeypatch):
    from youtube_intel import local_model_capacity as capacity
    from youtube_intel.state import SQLiteStateRepository

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=datetime.now(UTC))
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(
        capacity,
        "observe_host",
        lambda **_: capacity.HostObservation((), "server-fixture", "runner-fixture"),
    )
    monkeypatch.setattr(capacity.HostObservation, "is_current", lambda self: True)
    session = capacity.LocalCapacitySession(repository=repository, data_root=data)
    calls = []
    loaded = []
    profile = resolve_profile(PROFILE_ID)

    def send(path, *, method, body=None):
        calls.append((path, method, body))
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
            return {"models": loaded}
        assert path == "/api/chat" and body["messages"] == []
        loaded.append(
            {
                "name": profile.model,
                "digest": profile.model_digest,
                "runner": "llamacpp",
                "context_length": 16384,
            }
        )
        return {
            "model": profile.model,
            "done": True,
            "done_reason": "load",
            "message": {"role": "assistant", "content": ""},
        }

    return session, send, calls, loaded


def test_cold_preflight_loads_empty_messages_once_and_binds_one_dispatch(
    tmp_path, monkeypatch
):
    session, send, calls, _ = _session(tmp_path, monkeypatch)
    value = support._input()
    request = build_local_distillation_request(value)
    assert session.prepare("exec", value, request, send)
    from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs

    jobs = LocalTranscriptionJobs(session.repository, session.data_root)
    assert jobs._slot() is None
    assert session.prepare("exec", value, request, send)
    loads = [c for c in calls if c[0] == "/api/chat"]
    assert len(loads) == 1
    assert loads[0][2]["messages"] == [] and loads[0][2]["keep_alive"] != 0
    assert (
        "num_predict" not in loads[0][2]["options"]
        or loads[0][2]["options"]["num_predict"] != 0
    )
    assert session.ready_for_claim("exec", request)
    session.arm("exec", request)
    before = list(calls)
    session.consume("exec", request)
    assert calls == before
    with pytest.raises(RuntimeError):
        session.consume("exec", request)
    session.release()


@pytest.mark.parametrize(
    "failure",
    [
        "system",
        "messages",
        "tokenizer",
        "renderer",
        "slot",
        "runner",
        "other",
        "load-content",
        "load-eval",
        "load-done",
    ],
)
def test_metadata_or_load_failure_closes_before_claim(tmp_path, monkeypatch, failure):
    session, send, calls, loaded = _session(tmp_path, monkeypatch)

    def changed(path, **kwargs):
        result = send(path, **kwargs)
        if path == "/api/show":
            if failure in {"system", "messages"}:
                result[failure] = "unexpected"
            if failure == "tokenizer":
                result["model_info"]["tokenizer.ggml.pre"] = "qwen2"
            if failure == "renderer":
                result["modelfile"] = "RENDERER other\nPARSER qwen3.5\n"
        if path == "/api/chat":
            if failure == "slot":
                loaded[0]["context_length"] = 8192
            if failure == "runner":
                loaded[0]["runner"] = "mlx"
            if failure == "load-content":
                result["message"]["content"] = "generated"
            if failure == "load-eval":
                result["eval_count"] = 1
            if failure == "load-done":
                result["done"] = False
        if path == "/api/ps" and failure == "other":
            result["models"] = [{"name": "other"}]
        return result

    assert not session.prepare(
        "exec",
        support._input(),
        build_local_distillation_request(support._input()),
        changed,
    )
    assert not session.ready_for_claim(
        "exec", build_local_distillation_request(support._input())
    )
    assert all(c[0] != "/api/chat" or c[2]["messages"] == [] for c in calls)


def test_shared_asr_slot_and_expired_or_changed_readiness_close(tmp_path, monkeypatch):
    from youtube_intel import local_model_capacity as capacity

    session, send, calls, _ = _session(tmp_path, monkeypatch)
    request = build_local_distillation_request(support._input())
    other = capacity.ApplicationHeavyLease(
        repository=session.repository, data_root=session.data_root
    )
    assert other.acquire()
    assert not session.prepare("exec", support._input(), request, send) and calls == []
    other.release()
    assert session.prepare("exec", support._input(), request, send)
    assert not session.ready_for_claim("different", request)
    assert not session.ready_for_claim("exec", {**request, "context": []})
    monkeypatch.setattr(capacity, "monotonic", lambda: 1e20)
    assert not session.ready_for_claim("exec", request)
    session.release()


def _runner(capacity, cache):
    model = (
        cache
        / "blobs/sha256-02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d"
    )
    return f"77 Thu Oct 01 00:00:00 2026 {capacity.ROOT / 'llama-server'} --model {model} --host 127.0.0.1 --port 12345 -c 16384 -np 1 --chat-template chatml --no-jinja --offline --no-webui"


@pytest.mark.parametrize(
    "override",
    [
        "-c 8192",
        "-np 2",
        "--context-shift",
        "--chat-template other",
        "--host 0.0.0.0",
        "--port 1",
        "--flash-attn off",
        "--unknown",
    ],
)
def test_fixed_runner_rejects_context_parallel_and_any_unknown_override(
    tmp_path, override
):
    from youtube_intel import local_model_capacity as capacity

    runner = _runner(capacity, tmp_path)
    capacity.validate_runner(runner, tmp_path)
    key = override.split()[0]
    if key in {"-c", "-np", "--host", "--port", "--chat-template"}:
        import re

        runner = re.sub(re.escape(key) + r" \S+", override, runner)
    else:
        runner += " " + override
    with pytest.raises(capacity.CapacityUnavailable):
        capacity.validate_runner(runner, tmp_path)


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "manifest",
        "binary",
        "blob",
        "descriptor",
        "disk",
        "memory",
        "multiple-server",
        "runner",
        "mutating-file",
        "cold-runner",
    ],
)
def test_host_observer_verifies_all_fixed_bytes_and_resource_truth(
    tmp_path, monkeypatch, failure
):
    import hashlib
    import json
    from dataclasses import replace
    from types import SimpleNamespace

    from youtube_intel import local_model_capacity as capacity

    home = tmp_path / "home"
    root = tmp_path / "runtime"
    root.mkdir()
    cache = home / ".ollama/models"
    manifest = cache / "manifests/registry.ollama.ai/library/qwen3.5/9b-q4_K_M"
    manifest.parent.mkdir(parents=True)
    blobs = cache / "blobs"
    blobs.mkdir()
    payload = b"bounded fixture weight; never a model"
    blob_hash = hashlib.sha256(payload).hexdigest()
    (blobs / ("sha256-" + blob_hash)).write_bytes(payload)
    binary = root / "ollama"
    binary.write_bytes(b"fixture runtime")
    binary_hash = capacity.file_hash(binary)
    manifest.write_text(
        json.dumps(
            {
                "config": {
                    "digest": "sha256:" + blob_hash,
                    "size": len(payload),
                },
                "layers": [],
            }
        )
    )
    manifest_hash = capacity.file_hash(manifest)
    profile = replace(
        resolve_profile(PROFILE_ID), model_digest="sha256:" + manifest_hash
    )
    monkeypatch.setattr(capacity.Path, "home", classmethod(lambda _: home))
    monkeypatch.setattr(capacity, "ROOT", root)
    monkeypatch.setattr(capacity, "BINARIES", {"ollama": binary_hash})
    monkeypatch.setattr(capacity, "BLOBS", {blob_hash: len(payload)})
    monkeypatch.setattr(capacity, "resolve_profile", lambda _: profile)
    server = f"77 Thu Oct 01 00:00:00 2026 {root / 'ollama'} serve"
    runner = _runner(capacity, cache)
    if failure == "multiple-server":
        server += "\n" + server
    if failure == "runner":
        runner = runner.replace("-np 1", "-np 2")
    monkeypatch.setattr(
        capacity, "processes", lambda binary: server if binary == "ollama" else runner
    )
    monkeypatch.setattr(
        capacity.shutil,
        "disk_usage",
        lambda _: SimpleNamespace(free=(1 if failure == "disk" else 20) * capacity.GIB),
    )
    monkeypatch.setattr(
        capacity,
        "available_memory_bytes",
        lambda: (1 if failure == "memory" else 10) * capacity.GIB,
    )
    if failure == "manifest":
        manifest.write_text("{}")
    if failure == "binary":
        binary.write_bytes(b"other runtime")
    if failure == "blob":
        (blobs / ("sha256-" + blob_hash)).write_bytes(b"other weight")
    if failure == "descriptor":
        monkeypatch.setattr(capacity, "BLOBS", {})
    if failure == "mutating-file":
        original = capacity.file_hash

        def mutated(path):
            value = original(path)
            if path == binary:
                binary.write_bytes(b"fixture runtime changed")
            return value

        monkeypatch.setattr(capacity, "file_hash", mutated)
    if failure is None:
        observation = capacity.observe_host(data_root=tmp_path, loaded=True)
        assert {p for p, _ in observation.files} == {
            manifest,
            binary,
            blobs / ("sha256-" + blob_hash),
        }
        assert observation.is_current()
        binary.write_bytes(b"changed")
        assert not observation.is_current()
    else:
        with pytest.raises(capacity.CapacityUnavailable):
            capacity.observe_host(data_root=tmp_path, loaded=failure != "cold-runner")


def test_completion_prompt_count_must_fit_this_exact_complete_request():
    from youtube_intel.distillation import (
        KnownLocalDistillationResponseError,
        validate_local_grounding_response,
    )

    value = support._input()
    profile = resolve_profile(PROFILE_ID)
    bound = profile.complete_input_token_upper_bound(
        build_local_distillation_request(value)
    )
    response = {
        "model": profile.model,
        "done": True,
        "done_reason": "stop",
        "message": {"content": "{}"},
        "prompt_eval_count": bound,
        "eval_count": 1,
    }
    assert (
        validate_local_grounding_response(response, value, duration_ms=1).input_tokens
        == bound
    )
    with pytest.raises(KnownLocalDistillationResponseError):
        validate_local_grounding_response(
            {**response, "prompt_eval_count": bound + 1}, value, duration_ms=1
        )


def test_cold_ps_empty_with_an_existing_runner_is_rejected_before_load(
    tmp_path, monkeypatch
):
    from youtube_intel import local_model_capacity as capacity

    session, send, calls, _ = _session(tmp_path, monkeypatch)

    def observe(*, data_root, loaded):
        assert loaded is False
        raise capacity.CapacityUnavailable("untracked runner exists before load-only")

    monkeypatch.setattr(capacity, "observe_host", observe)
    assert not session.prepare(
        "exec",
        support._input(),
        build_local_distillation_request(support._input()),
        send,
    )
    assert not any(path == "/api/chat" for path, _, _ in calls)
    assert session.lease.fd is None
