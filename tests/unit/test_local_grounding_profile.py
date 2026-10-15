"""Offline engineering fixtures confer no live model qualification."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest
from conftest import _load_module

from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    LocalTextDistillationProfile,
    OllamaLocalDistillationTransport,
    OpenAICloudDistillationTransport,
    PersonalizedDistillationService,
    bind_local_profile,
    build_local_distillation_request,
)
from youtube_intel.local_distillation_profile import PROFILE_ID, resolve_profile

legacy = _load_module("test_ollama_local_distillation")
cloud = _load_module("test_openai_distillation_adapter")


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _input():
    profile = resolve_profile(PROFILE_ID)
    return bind_local_profile(replace(legacy._input(), selected_model=profile.model), PROFILE_ID)


def test_default_none_preserves_original_request_and_execution_bytes():
    class Capture(OllamaLocalDistillationTransport):
        def _request(self, path, *, method, body=None):
            self.body = body
            return {"model": self._MODEL, "done": True, "message": {"content": "{}"}, "prompt_eval_count": 1, "eval_count": 1}
    transport = Capture(settings=LocalScoringSettings(model=transport_model(), expected_model_digest=legacy._DIGEST))
    transport.generate(legacy._input())
    assert _hash(transport.body) == "3be8a25e76756d69901591059f8c032da261b62f62b034ae8ec3e596c2f88afd"
    assert _hash(OpenAICloudDistillationTransport._request(cloud._input())) == "6ac1a0d355d8c51551385505b266e3854430bf45b4288da844adee3bef5ee4df"
    assert LocalTextDistillationProfile.identity_hash() == "d5cdb438bb949d0dae3550f3015270dbda155ed513e3cae374a51fc04c436558"
    assert PersonalizedDistillationService._reservation_id(source_id="s", video_id="v", evidence_ids=("e",),
        selected_provider="ollama", selected_model=transport_model(), output_language="en", verified_input_hash="c" * 64) == "distillation:reservation:v3:5186bc1a7fdca27974a5c1253bcff70a1d85e33c8ae646cf2c0b75a2c908a492"


def transport_model():
    return OllamaLocalDistillationTransport._MODEL


def test_new_profile_has_exact_options_and_distinct_request_identity():
    value = _input()
    request = build_local_distillation_request(value)
    assert value.local_profile_id == PROFILE_ID
    assert len(value.local_profile_hash) == 64
    assert request["model"] == "qwen3.5:9b-q4_K_M"
    assert request["think"] is True and request["stream"] is False
    assert request["options"] == {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
        "presence_penalty": 1.5, "repeat_penalty": 1.0, "seed": 20261013, "num_ctx": 8192, "num_predict": 6144}
    assert build_local_distillation_request(value) == request
    prompt = request["messages"][0]["content"]
    assert "personal experience" in prompt and "group comparison" in prompt
    assert "not independent verification" in prompt and "not equivalence" in prompt
    assert value.evidence[0].excerpt not in prompt
    assert all(word not in prompt for word in ("DeepThink", "IMO", "20/100"))


@pytest.mark.parametrize("change", [{"local_profile_hash": "0" * 64}, {"local_profile_id": "future-profile"},
    {"selected_model": "qwen3:8b"}, {"selected_provider": "openai"}, {"wire_version": "unknown"}])
def test_unknown_or_mismatched_profile_never_builds_a_request(change):
    with pytest.raises(ValueError):
        build_local_distillation_request(replace(_input(), **change))


def test_scope_identity_is_separate_and_never_inherited():
    timed = bind_local_profile(replace(legacy._input(), selected_model=resolve_profile(PROFILE_ID).model,
        content_provider="LOCAL", local_content_context_hash="d" * 64), PROFILE_ID)
    assert timed.local_profile_hash != _input().local_profile_hash
    with pytest.raises(ValueError):
        bind_local_profile(cloud._input(), PROFILE_ID)
