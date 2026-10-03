import copy
import json

import pytest

from youtube_intel.acoustic_qualification import (
    QualificationEvidence,
    SampleResult,
    evaluate,
    qualification_status,
    seal_record,
)


def evidence():
    samples = tuple(SampleResult(name=name, source_sha256="a" * 64, expected_sha256="b" * 64, error_rate=0.01, duration_seconds=125 if name == "medium" else 4 if name == "very-short" else 25, processing_seconds=5, completed=True, timestamps_valid=True, coverage_passed=True, no_omission=True) for name in ["english-clean", "mandarin-clean", "mixed-clean", "very-short", "medium", "designed-pauses", "mild-noise", "english-video"])
    return QualificationEvidence(corpus_sha256="c" * 64, samples=samples, offline=True, cloud_dispatches=0, source_uploads=0)


def test_not_tested_and_boolean_cannot_mint_pass(tmp_path):
    assert qualification_status(tmp_path, {"runtime": "0.4.3"})["state"] == "NOT_TESTED"
    (tmp_path / "model.json").write_text(json.dumps({"model_path": "/present", "qualified": True}))
    (tmp_path / "qualification.json").write_text(json.dumps({"state": "PASSED", "qualified": True}))
    assert qualification_status(tmp_path, {"runtime": "0.4.3"})["state"] != "PASSED"


def test_signed_evidence_pass_and_failure_not_boolean(tmp_path):
    identity = {"runtime": "0.4.3", "model": "sealed"}
    seal_record(tmp_path, identity, evidence=evidence(), audit=b"measured audit")
    assert qualification_status(tmp_path, identity)["state"] == "PASSED"
    failure = evidence().model_copy(update={"samples": (evidence().samples[0].model_copy(update={"error_rate": 0.16}), *evidence().samples[1:])})
    assert evaluate(failure) == "FAILED"
    seal_record(tmp_path, identity, evidence=failure, audit=b"failed audit")
    assert qualification_status(tmp_path, identity)["state"] == "FAILED"


@pytest.mark.parametrize("dimension", ["model_digest", "model_revision", "mlx_whisper", "mlx", "executor_contract", "decoding_profile", "transcript_contract", "timestamp_policy", "preprocessing_profile", "platform", "corpus_policy"])
def test_every_material_tuple_change_is_stale(tmp_path, dimension):
    identity = {dimension: "original"}
    seal_record(tmp_path, identity, evidence=evidence(), audit=b"audit")
    changed = copy.deepcopy(identity)
    changed[dimension] = "changed"
    assert qualification_status(tmp_path, changed)["state"] == "STALE"


def test_tampered_evidence_and_receipt_cannot_pass(tmp_path):
    seal_record(tmp_path, {"model": "original"}, evidence=evidence(), audit=b"audit")
    record = json.loads((tmp_path / "qualification.json").read_text())
    (tmp_path / "qualification" / (record["body"]["audit_sha256"] + ".json")).write_bytes(b"tampered")
    assert qualification_status(tmp_path, {"model": "original"})["state"] == "STALE"
    record["body"]["state"] = "PASSED"
    record["body"]["tuple"] = {"model": "changed"}
    (tmp_path / "qualification.json").write_text(json.dumps(record))
    assert qualification_status(tmp_path, {"model": "changed"})["state"] != "PASSED"


@pytest.mark.parametrize("field", ["timestamps_valid", "coverage_passed", "no_omission", "completed"])
def test_required_sample_failures_cannot_be_averaged_away(field):
    failed = evidence().samples[1].model_copy(update={field: False})
    assert evaluate(evidence().model_copy(update={"samples": (evidence().samples[0], failed, *evidence().samples[2:])})) == "FAILED"


def test_missing_category_no_fake_pass_and_actual_performance_required():
    assert evaluate(evidence().model_copy(update={"samples": evidence().samples[1:]})) == "FAILED"
    failed = evidence().samples[4].model_copy(update={"processing_seconds": 1801})
    assert evaluate(evidence().model_copy(update={"samples": (*evidence().samples[:4], failed, *evidence().samples[5:])})) == "FAILED"


def test_running_is_only_live_owned_qualification_and_restart_recovers(tmp_path):
    import fcntl
    with (tmp_path / "qualification.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        seal_record(tmp_path, {"model": "original"}, evidence=None, audit=None)
        assert qualification_status(tmp_path, {"model": "original"})["state"] == "RUNNING"
    assert qualification_status(tmp_path, {"model": "original"})["state"] == "FAILED"


def test_symlink_receipt_or_audit_and_wrong_machine_are_rejected(tmp_path, monkeypatch):
    from youtube_intel import acoustic_qualification as module
    seal_record(tmp_path, {"model": "original"}, evidence=evidence(), audit=b"audit")
    monkeypatch.setattr(module, "machine_binding", lambda _: "different-machine")
    assert qualification_status(tmp_path, {"model": "original"})["state"] == "STALE"
    monkeypatch.undo()
    record = tmp_path / "qualification.json"
    other = tmp_path / "other"
    record.rename(other)
    record.symlink_to(other)
    assert qualification_status(tmp_path, {"model": "original"})["state"] != "PASSED"


def test_fixture_ground_truth_change_invalidates_corpus_evidence(tmp_path):
    seal_record(tmp_path, {"model": "original"}, evidence=evidence(), audit=b"frozen expected text and results")
    record = json.loads((tmp_path / "qualification.json").read_text())
    record["body"]["evidence"]["corpus_sha256"] = "d" * 64
    record["body"]["evidence"]["samples"][0]["expected_sha256"] = "e" * 64
    (tmp_path / "qualification.json").write_text(json.dumps(record))
    assert qualification_status(tmp_path, {"model": "original"})["state"] == "STALE"
