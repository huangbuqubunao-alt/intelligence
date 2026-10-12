"""Old subset receipts and missing refusal evidence must not qualify new profile."""
from tests.unit.test_acoustic_qualification import evidence
from youtube_intel.acoustic_qualification import evaluate


def test_historical_eight_sample_subset_cannot_qualify_new_profile():
    old = evidence().model_copy(update={'samples': evidence().samples[:8], 'negative_controls': ()})
    assert evaluate(old) == 'FAILED'


def test_complete_speech_results_without_negative_controls_cannot_qualify():
    assert evaluate(evidence().model_copy(update={'negative_controls': ()})) == 'FAILED'


def test_invocation_unknown_refusal_or_authority_on_negative_control_fails_closed():
    for updates in [{'decoder_invocations': 1}, {'no_authority': False}, {'observed_outcome': 'UNKNOWN'}, {'processing_seconds': float('nan')}]:
        value = evidence()
        invalid = value.negative_controls[0].model_copy(update=updates)
        assert evaluate(value.model_copy(update={'negative_controls': (invalid, *value.negative_controls[1:])})) == 'FAILED'


def test_missing_duplicate_and_failed_required_medium_cannot_be_averaged_away():
    value = evidence()
    assert evaluate(value.model_copy(update={'negative_controls': value.negative_controls[:2]})) == 'FAILED'
    assert evaluate(value.model_copy(update={'negative_controls': (*value.negative_controls, value.negative_controls[0])})) == 'FAILED'
    sample = next(s for s in value.samples if s.name == 'silence-medium').model_copy(update={'coverage_passed': False})
    assert evaluate(value.model_copy(update={'samples': tuple(sample if s.name == sample.name else s for s in value.samples)})) == 'FAILED'
