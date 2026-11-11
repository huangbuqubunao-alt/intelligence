"""v5 judgment contract: restores the Intelligence/field definition; v1-v4 unchanged."""
from __future__ import annotations

import json
import re

import pytest
from conftest import _load_module

from youtube_intel import system_synthesis as synthesis
from youtube_intel import system_synthesis_profile as profile
from youtube_intel import system_synthesis_qualification as qualification
from youtube_intel.distillation import CloudDistillationPreDispatchError
from youtube_intel.synthesis_runtime import (
    MoonshotJudgmentSynthesisTransport,
    MoonshotReadableSummarySynthesisTransport,
)

pure = _load_module('test_system_synthesis')
V5, POLICY = profile.JUDGMENT_PROFILE_ID, synthesis.JUDGMENT_PROFILE_ID
V4, V4_POLICY = profile.READABLE_SUMMARY_PROFILE_ID, synthesis.READABLE_SUMMARY_PROFILE_ID
# Historical v4 descriptor bound in the frozen r2 package (immutable-profile.json).
V4_POLICY_SHA = 'e4f62bf8b8ef7a00789282dbe781305f516ef0a4d4d05b388dce6fc165a2ef8f'


def test_historical_v4_identity_and_reserve_formula_are_unchanged():
    assert profile.resolve_profile(V4)['policy_sha256'] == V4_POLICY_SHA
    assert profile.resolve_profile(V4)['reasoning_effort'] == 'low'
    assert profile.resolve_profile(V4)['max_completion_tokens'] == 5888
    request = synthesis.build_system_synthesis_request(**pure.inputs(), profile_id=V4_POLICY)
    wire, reserve = profile.provider_wire(request, V4)
    messages = json.loads(wire)['messages']
    assert reserve == (sum(len(m['content'].encode()) for m in messages) + 2048) * 26 + 5888 * 68


def test_v5_is_v4_contract_plus_generic_judgment_policy_only():
    v4 = synthesis._contract(V4_POLICY)
    v5 = synthesis._contract(POLICY)
    assert v5.startswith(v4 + ' ') and v5 != v4
    added = v5[len(v4) + 1:]
    assert added == synthesis._JUDGMENT_POLICY
    for field in ('core_conclusion', 'user_relevant_information', 'important_new_information', 'meaningful_details'):
        assert field in added
    assert 'NO_NEW_INTELLIGENCE' in added and 'Empty arrays are valid' in added


@pytest.mark.parametrize('term', ['relu', 'sigmoid', 'mole', 'codeforces', 'deep think', 'gemini', 'neural',
    'aircaruvnkk', 'iwglw', 'experiment', 'verification plan', 'test-time', 'minimax', '160', 'kimi'])
def test_v5_policy_names_no_case_topic_keyword_or_recommendation_template(term):
    assert term not in synthesis._JUDGMENT_POLICY.lower()


def test_v5_policy_contains_no_digits_or_quoted_answer_text():
    assert not re.search(r'\d', synthesis._JUDGMENT_POLICY)
    assert '"' not in synthesis._JUDGMENT_POLICY


def test_v5_profile_changes_only_reasoning_completion_and_policy():
    v4, v5 = profile.resolve_profile(V4), profile.resolve_profile(V5)
    changed = {key for key in v4.keys() | v5.keys() if v4.get(key) != v5.get(key)}
    assert changed == {'id', 'reasoning_effort', 'max_completion_tokens', 'policy_id', 'policy_sha256'}
    assert (v5['reasoning_effort'], v5['max_completion_tokens']) == ('high', 12288)
    assert v5['qualified'] is False and v5['normal_spending_authorized'] is False and v5['retries'] == 0
    assert profile.policy_id(V5) == POLICY and V5 in profile.REVIEWED_PROFILE_IDS and V5 in profile.PROFILE_IDS


def test_v5_wire_keeps_task_source_and_readable_summary_messages_of_v4():
    v4 = synthesis.build_system_synthesis_request(**pure.inputs(), profile_id=V4_POLICY)
    v5 = synthesis.build_system_synthesis_request(**pure.inputs(), profile_id=POLICY)
    old, new = json.loads(v4.wire_json)['messages'], json.loads(v5.wire_json)['messages']
    assert new[1:] == old[1:] and new[0]['content'].startswith(synthesis._contract(POLICY))
    wire, reserve = profile.provider_wire(v5, V5)
    body = json.loads(wire)
    assert body['reasoning_effort'] == 'high' and body['max_completion_tokens'] == 12288
    assert reserve == (sum(len(m['content'].encode()) for m in body['messages']) + 2048) * 26 + 12288 * 68
    with pytest.raises(ValueError, match='mixture'):
        profile.provider_wire(v5, V4)
    with pytest.raises(ValueError, match='mixture'):
        profile.provider_wire(v4, V5)


def test_v5_positive_may_leave_fields_empty_and_no_new_stays_strict():
    request = synthesis.build_system_synthesis_request(**pure.inputs(), profile_id=POLICY)
    refs = json.loads(request.projection_json)['source_refs']
    positive = {'core_conclusion': 'Owned fixture judgment.', 'user_relevant_information': [],
        'important_new_information': [], 'meaningful_details': [], 'filtered_noise': [],
        'evidence': [{'ref': refs[0]['ref'], 'stance': 'supporting'}], 'reference_protocol': 'bound-evidence-reference-v1'}
    decoded = synthesis.decode_system_synthesis(json.dumps(positive), request, request_origin_sha256=request.origin_sha256)
    assert not decoded.no_new and decoded.claim_kind == 'SYSTEM_INFERENCE'
    zero = {'result': 'NO_NEW_INTELLIGENCE', 'reference_protocol': 'bound-evidence-reference-v1',
        'evidence': [{'ref': r['ref']} for r in refs[:-1]]}
    if len(refs) > 1:
        with pytest.raises(ValueError, match='coverage'):
            synthesis.decode_system_synthesis(json.dumps(zero), request, request_origin_sha256=request.origin_sha256)


def test_v5_transport_is_distinct_and_never_inherits_v4_qualification():
    assert MoonshotJudgmentSynthesisTransport.synthesis_profile_id == V5
    assert MoonshotJudgmentSynthesisTransport is not MoonshotReadableSummarySynthesisTransport
    assert MoonshotJudgmentSynthesisTransport._PROMPT_VERSION == 'system-synthesis-v5-judgment'
    assert not qualification.read_reviewed_qualifications(profile_id=V5).permits(V5, 'en')
    assert not qualification.read_reviewed_qualifications(profile_id=V4).permits(V5, 'en')
    assert issubclass(CloudDistillationPreDispatchError, Exception)


def test_v5_matrix_is_the_same_eight_cases_with_positive_material_first():
    assert set(qualification.case_languages(V5).items()) == set(qualification.CASE_LANGUAGES.items())
    order = list(qualification.case_languages(V5))
    assert order[:2] == ['public-IwglW_hIL_g-en', 'public-IwglW_hIL_g-zh-CN']
    assert order[4:] == list(qualification.CASE_LANGUAGES)[4:]
    assert list(qualification.case_languages(V4)) == list(qualification.CASE_LANGUAGES)
    binding = qualification.qualification_binding(V5)
    assert binding['profile_id'] == V5 and binding['policy_id'] == POLICY
