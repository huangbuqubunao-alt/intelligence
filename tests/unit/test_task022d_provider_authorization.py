"""TASK-022D exact normal-production provider authorization contract."""

from __future__ import annotations

import pytest

from youtube_intel.distillation import (
    CloudDistillationAuthorization,
    DistillationCapabilityScope,
    M12QualifiedCloudProductionAuthorizationAuthority,
    NormalV1ProductionAuthorizationAuthority,
    ProviderProductionEligibility,
)


@pytest.mark.parametrize(
    ("provider", "model", "scope", "expected"),
    [
        ("nvidia_nim", "moonshotai/kimi-k3", DistillationCapabilityScope.V1_VIDEO_DISTILLATION, True),
        ("nvidia_nim", "moonshotai/kimi-k2-thinking", DistillationCapabilityScope.V1_VIDEO_DISTILLATION, False),
        ("openai", "moonshotai/kimi-k3", DistillationCapabilityScope.V1_VIDEO_DISTILLATION, False),
        ("nvidia_nim", "moonshotai/kimi-k3", DistillationCapabilityScope.DEEP_ANALYSIS, False),
        ("nvidia_nim", "moonshotai/kimi-k3", DistillationCapabilityScope.INVESTIGATION, False),
        ("nvidia_nim", "moonshotai/kimi-k3", DistillationCapabilityScope.ASK, False),
        ("nvidia_nim", "moonshotai/kimi-k3", DistillationCapabilityScope.DAILY, False),
        ("nvidia_nim", "moonshotai/kimi-k3", DistillationCapabilityScope.EVIDENCE_EXPANSION, False),
        ("nvidia_nim", "moonshotai/kimi-k3", DistillationCapabilityScope.TASK_016G, False),
        ("nvidia_nim", "moonshotai/kimi-k3", DistillationCapabilityScope.V2, False),
        ("NVIDIA NIM", "moonshotai/kimi-k3", DistillationCapabilityScope.V1_VIDEO_DISTILLATION, False),
        ("nvidia_nim", "moonshotai/kimi-k3-extra", DistillationCapabilityScope.V1_VIDEO_DISTILLATION, False),
    ],
)
def test_authorization_is_an_exact_provider_model_capability_tuple(
    provider: str,
    model: str,
    scope: DistillationCapabilityScope,
    expected: bool,
) -> None:
    eligibility = NormalV1ProductionAuthorizationAuthority.resolve(
        provider=provider,
        model=model,
        capability_scope=scope,
        available=True,
    )

    assert eligibility.qualified is expected
    assert eligibility.authorized is expected
    assert eligibility.production_eligible is expected


def test_availability_remains_an_independent_runtime_gate() -> None:
    eligibility = NormalV1ProductionAuthorizationAuthority.resolve(
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=False,
    )

    assert eligibility.qualified is True
    assert eligibility.authorized is True
    assert eligibility.production_eligible is False


@pytest.mark.parametrize("forged_field", ("qualified", "authorized", "production_eligible"))
def test_callers_cannot_submit_derived_production_authority(forged_field: str) -> None:
    with pytest.raises(TypeError):
        CloudDistillationAuthorization(**{forged_field: True})


def test_callers_cannot_construct_a_backend_eligibility_record() -> None:
    with pytest.raises(TypeError, match="backend-authoritative"):
        ProviderProductionEligibility()


def test_backend_authority_mints_normal_production_state_without_forcing_cloud() -> None:
    eligibility = NormalV1ProductionAuthorizationAuthority.resolve(
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=True,
    )

    disabled = CloudDistillationAuthorization.for_normal_production(
        eligibility=eligibility,
        cloud_enabled=False,
        credential_available=True,
    )
    enabled = CloudDistillationAuthorization.for_normal_production(
        eligibility=eligibility,
        cloud_enabled=True,
        credential_available=True,
    )

    assert disabled.qualified is True
    assert disabled.authorized is True
    assert disabled.production_eligible is True
    assert disabled.cloud_enabled is False
    assert enabled.cloud_enabled is True


@pytest.mark.parametrize(
    ("provider", "model", "scope", "expected"),
    [
        ("moonshot", "kimi-k2.6", DistillationCapabilityScope.V1_VIDEO_DISTILLATION, True),
        ("moonshot", "kimi-k3", DistillationCapabilityScope.V1_VIDEO_DISTILLATION, False),
        ("nvidia_nim", "moonshotai/kimi-k3", DistillationCapabilityScope.V1_VIDEO_DISTILLATION, False),
        ("openai", "gpt-4.1", DistillationCapabilityScope.V1_VIDEO_DISTILLATION, False),
        ("moonshot", "kimi-k2.6", DistillationCapabilityScope.DEEP_ANALYSIS, False),
    ],
)
def test_m12_selected_cloud_authority_is_exact(
    provider: str,
    model: str,
    scope: DistillationCapabilityScope,
    expected: bool,
) -> None:
    eligibility = M12QualifiedCloudProductionAuthorizationAuthority.resolve(
        provider=provider, model=model, capability_scope=scope, available=True,
    )
    assert eligibility.qualified is expected
    assert eligibility.authorized is expected
    assert eligibility.production_eligible is expected
