"""Exact configurable identity never grants execution or borrows qualifications."""
import pytest


def test_actual0409_binding_is_finite_immutable_and_not_0406():
    from youtube_intel.local_distillation_profile import resolve_model_binding
    value=resolve_model_binding('ollama','qwen3.5:9b-q4_K_M','sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90','0.40.9')
    assert value.runtime == '0.40.9' and value.executable is True
    assert '0.40.9' in value.short_profile_id and '0.40.9' in value.long_profile_id
    assert dict(value.binary_hashes)['ollama']=='be4b054f8ebf8b3b185daa30671849a80f22c2b2ef45e064de562f69aba46a96'
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        value.runtime='0.40.6'


@pytest.mark.parametrize('provider,model,digest,runtime',[
    ('cloud','qwen3.5:9b-q4_K_M','sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90','0.40.9'),
    ('ollama','qwen3.5:4b-q4_K_M','sha256:d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04','0.40.9'),
    ('ollama','qwen3.5:9b-q4_K_M','wrong','0.40.9'),
    ('ollama','qwen3.5:9b-q4_K_M','sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90','0.40.10'),
])
def test_unknown_or_failed_model_cannot_resolve_execution_binding(provider,model,digest,runtime):
    from youtube_intel.local_distillation_profile import resolve_model_binding
    with pytest.raises(ValueError):
        resolve_model_binding(provider,model,digest,runtime)


def test_nominal0406_binding_is_history_only_and_native_host_must_deny():
    from youtube_intel.local_distillation_profile import (
        CURRENT_RUNTIME_PROFILE_ID,
        binding_for_profile,
    )
    from youtube_intel.local_model_capacity import runtime_binary_hashes
    assert binding_for_profile(CURRENT_RUNTIME_PROFILE_ID).executable is False
    with pytest.raises(OSError):
        runtime_binary_hashes(CURRENT_RUNTIME_PROFILE_ID)
