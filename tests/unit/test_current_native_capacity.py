"""ENGINEERING_ONLY current native token accounting; no model or qualification."""

from copy import deepcopy

import pytest

from youtube_intel.local_distillation_profile import ACTUAL_RUNTIME_PROFILE_ID as SHORT
from youtube_intel.long_distillation_profile import ACTUAL_RUNTIME_PROFILE_ID as LONG


def request(profile=LONG):
    import json

    from youtube_intel.local_distillation_profile import resolve_profile
    from youtube_intel.long_distillation_profile import resolve_long_profile

    options = json.loads(resolve_long_profile(LONG).profile_wire)["options"] if profile == LONG else resolve_profile(SHORT).options()
    return {"model": "qwen3.5:9b-q4_K_M", "messages": [
        {"role": "system", "content": " S \n"}, {"role": "user", "content": "\u001cU\u001c"}],
        "format": {"type": "object"}, "options": options, "stream": False,
        "think": True, "truncate": False, "shift": False}


def test_exact_thinking_frame_is_derived_from_pinned_go_source_not_false_golden():
    from youtube_intel.local_native_capacity import render_qwen35_prompt

    rendered = render_qwen35_prompt(request())
    assert rendered == "<|im_start|>system\nS<|im_end|>\n<|im_start|>user\n\u001cU\u001c<|im_end|>\n<|im_start|>assistant\n<think>\n"
    assert not rendered.endswith("</think>\n")
    value = request()
    value["messages"][0]["content"] = "\u2003\u0085S\u00a0\u3000"
    assert render_qwen35_prompt(value) == rendered


@pytest.mark.parametrize("damage", ["tools", "context", "images", "history", "role", "think", "truncate", "shift", "stream"])
def test_native_renderer_rejects_unknown_multi_turn_media_or_changed_contract(damage):
    from youtube_intel.local_native_capacity import render_qwen35_prompt

    value = request()
    if damage in {"tools", "context"}:
        value[damage] = []
    elif damage == "images":
        value["messages"][1]["images"] = []
    elif damage == "history":
        value["messages"].append({"role": "assistant", "content": "history"})
    elif damage == "role":
        value["messages"][0]["role"] = "user"
    else:
        value[damage] = damage != "think"
    with pytest.raises(ValueError):
        render_qwen35_prompt(value)


@pytest.mark.parametrize("profile,context,predict", [(SHORT, 16384, 8192), (LONG, 32768, 6144)])
def test_real_native_sequence_capacity_boundary_binds_full_request_schema_and_tokens(profile, context, predict):
    from youtube_intel.local_native_capacity import native_capacity_witness

    value = request(profile)
    count = context - predict - 2
    tokens = [17] * count
    proof = native_capacity_witness(value, profile_id=profile, native_tokens={"tokens": tokens}, actual_slot_context=context)
    assert proof.input_tokens == count
    assert proof.context_tokens == context and proof.predict_tokens == predict
    assert len(proof.token_sequence_hash) == len(proof.rendered_hash) == len(proof.request_hash) == 64
    changed = deepcopy(value)
    changed["messages"][1]["content"] += "changed"
    other = native_capacity_witness(changed, profile_id=profile, native_tokens={"tokens": tokens}, actual_slot_context=context)
    assert other.request_hash != proof.request_hash and other.rendered_hash != proof.rendered_hash
    tokens[-1] = 18
    other = native_capacity_witness(value, profile_id=profile, native_tokens={"tokens": tokens}, actual_slot_context=context)
    assert other.token_sequence_hash != proof.token_sequence_hash
    with pytest.raises(ValueError):
        native_capacity_witness(value, profile_id=profile, native_tokens={"tokens": tokens + [19]}, actual_slot_context=context)


@pytest.mark.parametrize("damage", ["unknown-profile", "slot", "slot-bool", "missing-token-list", "empty", "bool-token", "float-token", "negative-token", "unknown-upper-bound", "model", "options"])
def test_native_capacity_does_not_accept_bytes_estimate_unknown_slot_or_arbitrary_options(damage):
    from youtube_intel.local_native_capacity import native_capacity_witness

    value, profile, slot, response = request(), LONG, 32768, {"tokens": [1, 2, 3]}
    if damage == "unknown-profile":
        profile = "arbitrary-profile"
    elif damage == "slot":
        slot = 16384
    elif damage == "slot-bool":
        slot = True
    elif damage == "missing-token-list":
        response = {"count": 3}
    elif damage == "empty":
        response = {"tokens": []}
    elif damage in {"bool-token", "float-token", "negative-token"}:
        response = {"tokens": [{"bool-token": True, "float-token": 1.0, "negative-token": -1}[damage]]}
    elif damage == "unknown-upper-bound":
        value["options"]["num_predict"] = -1
    elif damage == "model":
        value["model"] = "foreign"
    else:
        value["options"]["temperature"] = 0.0
    with pytest.raises(ValueError):
        native_capacity_witness(value, profile_id=profile, native_tokens=response, actual_slot_context=slot)


@pytest.mark.parametrize("profile", [SHORT, LONG])
def test_current_host_pins_distinct_runtime_bytes_without_reinterpreting_old(profile):
    from youtube_intel import local_model_capacity as capacity
    from youtube_intel.local_distillation_profile import (
        FIXED_RUNTIME_PROFILE_ID,
        PROFILE_ID,
    )

    assert capacity.runtime_binary_hashes(profile) == {
        "ollama": "be4b054f8ebf8b3b185daa30671849a80f22c2b2ef45e064de562f69aba46a96",
        "llama-server": "831a41b83171eb00710d75e55bc1d995c8bc61e01bee547420ca52c02448275d",
        "libllama-server-impl.dylib": "c9d3c06fe860e99823811e0716766fae9589b40b800b91cbcb9f78dda1df2a7c",
    }
    assert capacity.runtime_binary_hashes(PROFILE_ID) == capacity.BINARIES
    assert capacity.runtime_binary_hashes(FIXED_RUNTIME_PROFILE_ID) == capacity.BINARIES
    assert capacity.runtime_binary_hashes(profile) != capacity.runtime_binary_hashes(PROFILE_ID)
    with pytest.raises(ValueError):
        capacity.runtime_binary_hashes("arbitrary-profile")


@pytest.mark.parametrize("profile,context", [(SHORT, 16384), (LONG, 32768)])
def test_current_host_observation_checks_finite_actual_slot_and512_before_capacity(tmp_path, monkeypatch, profile, context):
    from conftest import _load_module

    from youtube_intel import local_model_capacity as capacity

    old = _load_module("test_local_model_capacity")
    cache = tmp_path / ".ollama/models"
    runner = old._runner(capacity, cache).replace("-c 16384", "-c " + str(context)) + " -b 512 -ub 512"
    server = f"78 Thu Oct 01 00:00:00 2026 {capacity.ROOT / 'ollama'} serve"
    seen = []
    def verify_installed(_cache, *, profile_id):
        seen.append(profile_id)
        return (), ()
    monkeypatch.setattr(capacity.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(capacity, "verify_installed_model_bytes", verify_installed)
    monkeypatch.setattr(capacity, "processes", lambda binary: server if binary == "ollama" else runner)
    monkeypatch.setattr(capacity.shutil, "disk_usage", lambda _: type("Usage", (), {"free": 20 * capacity.GIB})())
    monkeypatch.setattr(capacity, "available_memory_bytes", lambda: 10 * capacity.GIB)
    observed = capacity.observe_host(data_root=tmp_path, loaded=True, profile_id=profile)
    assert seen == [profile]
    assert observed.server == server and observed.runner == runner
    monkeypatch.setattr(capacity, "processes", lambda binary: server if binary == "ollama" else runner.replace(" -b 512", " -b 1024"))
    with pytest.raises(capacity.CapacityUnavailable):
        capacity.observe_host(data_root=tmp_path, loaded=True, profile_id=profile)


def test_current_runtime_verifies_v2_parent_reference_and_payloads_without_legacy_anchor(tmp_path, monkeypatch):
    from conftest import _load_module

    from youtube_intel import local_model_capacity as capacity

    manifests = _load_module("test_capacity_host_manifest")
    wrapper, parent, reference, _binary, payloads = manifests.fixture_installation(tmp_path, monkeypatch)
    monkeypatch.setattr(capacity, "runtime_binary_hashes", lambda profile_id: dict(capacity.BINARIES))
    wrapper.rename(tmp_path / "historical-anchor-retained")
    cache = parent.parent.parent
    files, links = capacity.verify_installed_model_bytes(cache, profile_id=SHORT)
    assert parent in {p for p, _identity in files}
    assert reference in {p for p, _identity in files}
    assert set(payloads) <= {p for p, _identity in files}
    assert links[0][0] == reference and wrapper not in {p for p, _identity in files}
    with pytest.raises(OSError):
        capacity.verify_installed_model_bytes(cache)
    parent.write_bytes(parent.read_bytes() + b" ")
    with pytest.raises(capacity.CapacityUnavailable):
        capacity.verify_installed_model_bytes(cache, profile_id=LONG)
