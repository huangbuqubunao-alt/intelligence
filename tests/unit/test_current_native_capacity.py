"""ENGINEERING_ONLY current native token accounting; no model or qualification."""

from copy import deepcopy

import pytest

from youtube_intel.local_distillation_profile import CURRENT_RUNTIME_PROFILE_ID as SHORT
from youtube_intel.long_distillation_profile import CURRENT_RUNTIME_PROFILE_ID as LONG


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
