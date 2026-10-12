"""A failed product result cannot mint an acoustic PASS receipt."""
from __future__ import annotations

import copy
from unittest.mock import patch

import pytest

from scripts.qualify_readiness_asr_product import product_evidence, seal_product_result
from youtube_intel.acoustic_qualification import NEGATIVE_REQUIRED, REQUIRED, evaluate


def complete_results():
    samples = []
    frozen = []
    for name in sorted(REQUIRED):
        frozen.append({'id':name,'expected_sha256':'b'*64,'duration_seconds':125. if name=='medium' else 4. if name=='very-short' else 25.})
        samples.append({'id':name,'source_sha256':'a'*64,'product_wall_seconds':1.,'status':{'status':'READY'},'trusted_timed_transcript':True,'summary':True,'evidence_resolves':True,'passed':True,'score':{'error_rate':.01},'recalls':[1.],'coverage':{'passed':True}})
    for name in sorted(NEGATIVE_REQUIRED):
        samples.append({'id':name,'source_sha256':'a'*64,'product_wall_seconds':1.,'status':{'status':'FAILED'},'no_authority':True,'acoustic_guard':'NOISE_ONLY' if 'noise' in name else 'NO_SIGNAL','decoder_invocations':0,'passed':True})
    return {'verdict':'PASSED','samples':samples}, frozen


@pytest.mark.parametrize('missing', ['summary','evidence_resolves','trusted_timed_transcript'])
def test_missing_product_authority_never_qualifies(tmp_path, missing):
    report, frozen = complete_results()
    report['samples'][0][missing] = False
    report['samples'][0]['passed'] = False
    report['verdict'] = 'FAILED'
    result = product_evidence(report, frozen, b'frozen')
    assert evaluate(result) == 'FAILED'
    with patch('scripts.qualify_readiness_asr_product.seal_record') as writer:
        seal_product_result(tmp_path, {}, result, report, b'audit')
    assert evaluate(writer.call_args.kwargs['evidence']) == 'FAILED'


def test_inconsistent_report_rejected_before_any_receipt_write(tmp_path):
    report, frozen = complete_results()
    result = product_evidence(report, frozen, b'frozen')
    report['verdict'] = 'FAILED'
    with patch('scripts.qualify_readiness_asr_product.seal_record') as writer:
        with pytest.raises(ValueError,match='before sealing'):
            seal_product_result(tmp_path, {}, result, report, b'audit')
    writer.assert_not_called()
    assert not (tmp_path/'qualification.json').exists()


def test_stale_pass_flag_cannot_hide_missing_evidence_or_pending_status():
    report, frozen = complete_results()
    for mutate in ('evidence_resolves','status'):
        bad = copy.deepcopy(report)
        if mutate == 'status':
            bad['samples'][0]['status']['status'] = 'PENDING'
        else:
            bad['samples'][0][mutate] = False
        assert evaluate(product_evidence(bad,frozen,b'frozen')) == 'FAILED'
    assert evaluate(product_evidence(report,frozen,b'frozen')) == 'PASSED'
