"""Qualification authority is independent of user configuration and fixtures."""
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from youtube_intel.deep_analysis_qualification import (
    QualificationAuthority,
    QualificationCheck,
    QualificationRecord,
    qualification_binding,
    qualification_cases,
)
from youtube_intel.deep_analysis_service import build_local_ollama_phase1b_route

NOW = datetime(2026, 10, 2, tzinfo=UTC)


def record(route, *, mode="LIVE_MODEL", failed=False):
    return QualificationRecord.create(
        binding=qualification_binding(route), mode=mode, generated_at=NOW,
        checks=tuple(QualificationCheck(case_id=c.case_id, output_language=lang,
                    passed=not failed, reason_code="PASSED" if not failed else "CONTRACT_FAILED")
                     for c, lang in qualification_cases()),
        limitations=("Bounded synthetic sources; no general reasoning guarantee.",),
    )


def test_configuration_and_health_are_not_qualification():
    route = build_local_ollama_phase1b_route()
    assert QualificationAuthority().state(route) == "NOT_TESTED"


def test_fixture_pass_never_becomes_live_qualified():
    route = build_local_ollama_phase1b_route()
    receipt = record(route, mode="FIXTURE_CONTRACT")
    assert QualificationAuthority((receipt,)).state(route) == "CONTRACT_VERIFIED"
    assert not QualificationAuthority((receipt,)).qualified(route)


def test_live_pass_is_attributable_and_inspectable():
    route = build_local_ollama_phase1b_route()
    receipt = record(route)
    assert QualificationAuthority((receipt,)).qualified(route)
    assert receipt.binding["provider_id"] == route.provider_id
    assert receipt.binding["model_id"] == route.model_id
    assert receipt.generated_at == NOW


@pytest.mark.parametrize("field,value", [
    ("model_id", "other-model"), ("provider_id", "other-provider"),
    ("route_id", "other-route"), ("qualified_capability_profile_identity", "changed"),
    ("model_output_schema_identity", "changed"), ("input_budget", 128),
])
def test_material_route_change_invalidates_receipt(field, value):
    route = build_local_ollama_phase1b_route()
    authority = QualificationAuthority((record(route),))
    assert not authority.qualified(replace(route, **{field: value}))


def test_incomplete_evaluation_and_failure_remain_nonproduction():
    route = build_local_ollama_phase1b_route()
    receipt = record(route)
    assert not QualificationAuthority((record(route, failed=True),)).qualified(route)
    incomplete = receipt.model_copy(update={"checks": receipt.checks[:1]})
    assert not QualificationAuthority((incomplete,)).qualified(route)


def test_resealed_modified_receipt_does_not_match_current_contract():
    route = build_local_ollama_phase1b_route()
    receipt = record(route)
    for key in ("contract_identity", "evidence_contract_identity", "validation_policy_identity", "fixture_identity", "policy_version"):
        changed = receipt.model_copy(update={"binding": {**receipt.binding, key: "changed"}})
        assert not QualificationAuthority((changed,)).qualified(route)
