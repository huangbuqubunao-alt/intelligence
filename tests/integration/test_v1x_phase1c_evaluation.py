"""Reproducible qualification exercises real schema, promotion and restart."""

import json

import pytest

from youtube_intel.deep_analysis_evaluation import evaluate_route
from youtube_intel.deep_analysis_qualification import QualificationAuthority
from youtube_intel.deep_analysis_service import (
    build_local_ollama_phase1b_route,
    build_openai_phase1b_route,
)


def route_with_response(mutate=None):
    def transport(request, timeout):
        payload = json.loads(
            request["messages"][0]["content"].split("Authorized payload: ", 1)[1]
        )
        refs = [c["evidence_id"] for c in payload["selected_evidence"]]
        chinese = payload["output_language"] == "zh-CN"
        texts = (
            (
                "能耗测量仍需更多实验验证。",
                "实验记录了能耗测量。",
                "证据不足，结论仍有不确定性。",
                "这对用户规划能耗实验具有意义。",
                "下一步如何验证能耗结果？",
            )
            if chinese
            else (
                "The energy measurement needs further replication before generalizing.",
                "The source records an energy measurement.",
                "The evidence remains limited and uncertain.",
                "This matters for planning an energy experiment.",
                "What further energy experiments would resolve this uncertainty?",
            )
        )
        output = {"schema_version": "v1x-content-deep-analysis-model-output-v2"}
        for i, role in enumerate(
            (
                "core_conclusion",
                "key_evidence",
                "uncertainty",
                "relevance_to_user",
                "next_question",
            )
        ):
            output[role] = [
                {
                    "text": texts[i],
                    "point_kind": "fact" if i == 1 else "inference",
                    "evidence_refs": refs[-1:],
                }
            ]
        if mutate:
            mutate(output)
        return {
            "model": "qwen2.5-coder:7b",
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps(output)},
        }

    return build_local_ollama_phase1b_route(transport=transport)


def test_bounded_fixture_contract_checks_never_mint_live_authority(tmp_path):
    route = route_with_response()
    receipt = evaluate_route(route=route, root=tmp_path, mode="FIXTURE_CONTRACT")
    assert receipt.passes()
    assert len(receipt.checks) == 14
    assert QualificationAuthority((receipt,)).state(route) == "CONTRACT_VERIFIED"
    assert not QualificationAuthority((receipt,)).qualified(route)


def test_fixture_exercises_selection_among_several_real_candidates(tmp_path):
    from dataclasses import replace

    from youtube_intel.deep_analysis_qualification import FIXTURES

    assert any(f.case_id == "several-candidates" for f in FIXTURES)
    route = route_with_response()
    candidate_counts = []

    def dispatch(*, prepared_dispatch):
        payload = json.loads(
            prepared_dispatch.envelope.request_projection.provider_visible_messages[
                -1
            ].content.split("Authorized payload: ", 1)[1]
        )
        candidate_counts.append(len(payload["selected_evidence"]))
        return route.dispatch(prepared_dispatch=prepared_dispatch)

    receipt = evaluate_route(
        route=replace(route, dispatch=dispatch), root=tmp_path, mode="FIXTURE_CONTRACT"
    )
    assert receipt.passes()
    assert max(candidate_counts) >= 3


@pytest.mark.parametrize(
    "attack",
    ["candidate", "relevance", "deferred", "uncertainty", "next_question", "metadata"],
)
def test_qualification_rejects_product_contract_failures(tmp_path, attack):
    def mutate(output):
        if attack == "candidate":
            output["key_evidence"][0]["evidence_refs"] = ["invented-candidate-999"]
        if attack == "relevance":
            output["relevance_to_user"] = []
        if attack == "deferred":
            output["knowledge_delta"] = []
        if attack == "uncertainty":
            output["uncertainty"] = []
        if attack == "next_question":
            output["next_question"] = []
        if attack == "metadata":
            output["core_conclusion"][0]["text"] = (
                "The energy experiment provides guaranteed profit."
            )

    route = route_with_response(mutate)
    receipt = evaluate_route(route=route, root=tmp_path, mode="FIXTURE_CONTRACT")
    assert not receipt.passes()
    assert not QualificationAuthority((receipt,)).qualified(route)


def test_live_cloud_evaluation_has_separate_paid_authorization_gate(tmp_path):
    calls = []
    route = build_openai_phase1b_route(
        transport=lambda *args: calls.append(args),
        credential_resolver=lambda: "test-only",
    )
    with pytest.raises(ValueError, match="separately authorized"):
        evaluate_route(route=route, root=tmp_path, mode="LIVE_MODEL")
    assert calls == []
