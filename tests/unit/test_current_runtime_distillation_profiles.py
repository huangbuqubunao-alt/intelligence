"""ENGINEERING_ONLY finite profile freezes; no model/tokenizer/network calls."""

import hashlib
import json

import pytest
from conftest import _load_module

from youtube_intel.distillation import local_profile_for_scope
from youtube_intel.local_distillation_profile import (
    FIXED_RUNTIME_PROFILE_ID,
    PROFILE_ID,
    canonical,
    resolve_profile,
)
from youtube_intel.long_distillation_profile import (
    PROFILE_ID as OLD_LONG,
)
from youtube_intel.long_distillation_profile import (
    prepare_long_request,
    resolve_long_profile,
)

cases = _load_module("test_long_distillation_profile")
CURRENT_SHORT = "local-grounding-qwen35-9b-runtime-0.40.6-v3"
CURRENT_LONG = "local-grounding-qwen35-9b-lossless-rle-runtime-0.40.6-v2"


def test_historical_profiles_and_request_bytes_remain_exact():
    old = cases.prepare()
    assert resolve_long_profile(OLD_LONG).profile_hash == "2fb51df81b7962b9f831e70720985656220e3be8d32dc92fb15ee755a6ef1a82"
    assert hashlib.sha256(canonical(local_profile_for_scope(PROFILE_ID, "YT_TIMED"))).hexdigest() == "908575e9dbbdc6c0fa68c6ba0f2754ce1a463cc342202e09301abb79176389b7"
    assert old.request_hash == "67e41a75862ad5df8c2a8404e240a7ea7f687d32aaeb5685d0053064df4c254f"
    assert old.freeze_hash == "d789559bb01f94895ab16460cb13887e4f0d4ac26ccad7063a63e2c2803108c8"
    assert resolve_profile(FIXED_RUNTIME_PROFILE_ID).runtime == "0.40.1"
    assert resolve_profile(FIXED_RUNTIME_PROFILE_ID).options()["num_predict"] == 8192
    assert "num_batch" not in old.request()["options"]


def test_current_short_profile_is_a_distinct_fixed_runtime_contract():
    profile = resolve_profile(CURRENT_SHORT)
    assert profile.runtime == "0.40.6" and profile.timeout_seconds == 300
    assert profile.options() == {**resolve_profile(FIXED_RUNTIME_PROFILE_ID).options()}
    assert profile.max_content_bytes == 8101
    assert profile.prompt("YT_TIMED") == resolve_profile(PROFILE_ID).prompt("YT_TIMED")
    assert local_profile_for_scope(CURRENT_SHORT, "YT_TIMED")["local_profile_id"] == CURRENT_SHORT


def test_current_long_profile_changes_only_named_runtime_and_explicit_batch_contract():
    current = resolve_long_profile(CURRENT_LONG)
    old = resolve_long_profile(OLD_LONG)
    descriptor = json.loads(current.profile_wire)
    old_descriptor = json.loads(old.profile_wire)
    assert current.profile_id == CURRENT_LONG and current.profile_hash != old.profile_hash
    assert descriptor == {**old_descriptor, "profile_id": CURRENT_LONG, "runtime": "0.40.6", "options": {**old_descriptor["options"], "num_batch": 512}}
    packet, value = cases.fixture(114, 2406)
    prepared = prepare_long_request(packet, value, profile_id=CURRENT_LONG, **cases.SNAPSHOTS)
    historical = prepare_long_request(packet, value, profile_id=OLD_LONG, **cases.SNAPSHOTS)
    assert prepared.profile_hash == current.profile_hash
    assert prepared.request() == {**historical.request(), "options": {**historical.request()["options"], "num_batch": 512}}
    assert prepared.projection == historical.projection
    assert prepared.request_hash != historical.request_hash and prepared.freeze_hash != historical.freeze_hash
    assert prepared.request()["options"]["num_ctx"] == 32768
    assert prepared.request()["options"]["num_predict"] == 6144


@pytest.mark.parametrize("bad", [CURRENT_LONG.upper(), CURRENT_LONG + "-unknown", "arbitrary", None, 1, True])
def test_current_profile_dispatch_is_finite(bad):
    with pytest.raises(ValueError):
        resolve_long_profile(bad)
    with pytest.raises(ValueError):
        resolve_profile(bad)
