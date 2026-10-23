"""ENGINEERING_ONLY audit shapes; no fixture can mint production qualification."""
from __future__ import annotations

import copy
import json
from datetime import timedelta

import pytest
from conftest import _load_module

from youtube_intel import local_distillation_qualification as qualification
from youtube_intel.local_distillation_profile import CURRENT_RUNTIME_PROFILE_ID as SHORT
from youtube_intel.local_distillation_profile import (
    FIXED_RUNTIME_PROFILE_ID,
    PROFILE_ID,
    digest,
)
from youtube_intel.long_distillation_profile import CURRENT_RUNTIME_PROFILE_ID as LONG

old = _load_module("test_local_grounding_qualification")


def fixture(profile_id, scope):
    projection = qualification.qualification_projection(profile_id, scope)
    record = old._audit_fixture()
    record["binding"] = qualification.qualification_binding(projection)
    cases = []
    for index, (name, language) in enumerate(qualification.qualification_cases(projection).items()):
        case = copy.deepcopy(record["cases"][index % 10])
        case_scope = qualification.case_scope(name, profile_id=profile_id)
        binding = qualification.qualification_binding(qualification.qualification_projection(profile_id, case_scope))
        case.update(case_id=name, output_language=language, scope=case_scope,
            execution_id="ENGINEERING_ONLY-" + name, profile_hash=binding["profile_hash"],
            code_hash=binding["code_hash"], runtime=binding["runtime"], model_digest=binding["model_digest"],
            completed_at=f"2026-10-14T23:{index:02}:00Z")
        case["review"].update(case_id=name, reviewed_at=f"2026-10-14T23:{index:02}:30Z")
        if profile_id != PROFILE_ID:
            case["outcome"] = case["review"]["outcome"] = qualification.case_outcome(name)
        if name.startswith("local-"):
            case["source_manifest"]["origin"] = "LOCAL_SNAPSHOT"
        if name.startswith("long-full-"):
            case["source_manifest"].update(origin="PUBLIC_SNAPSHOT", source_id="0eMzc-WnBfQ", evidence_count=114, cue_count=2406,
                snapshot_hash=digest("same full snapshot"))
        cases.append(case)
    record["cases"] = cases
    return old._seal(record), projection


@pytest.mark.parametrize("profile_id,scope", [(PROFILE_ID, "YT_TIMED"), (SHORT, "YT_TIMED"),
    (SHORT, "LOCAL_TIMED"), (SHORT, "LOCAL_TEXT"), (LONG, "YT_TIMED")])
def test_finite_record_structure_and_raw_bytes_remain_unsealed(profile_id, scope):
    record, projection = fixture(profile_id, scope)
    assert qualification.QualificationRecord.model_validate(record).permits(projection, "en", old.NOW)
    authority = qualification.read_reviewed_qualifications(json.dumps({"version": qualification.VERSION, "records": [record]}).encode())
    assert len(authority.states(now=old.NOW)) == 1
    assert not authority.permits(projection, "en", now=old.NOW)
    assert not qualification.read_reviewed_qualifications().permits(projection, "en", now=old.NOW)


def test_long_requires_original_ten_then_two_full_cases_and_unchanged_local_eight():
    record, projection = fixture(LONG, "YT_TIMED")
    assert list(qualification.qualification_cases(projection)) == [*qualification.CASE_LANGUAGES["YT_TIMED"], "long-full-en", "long-full-zh"]
    assert len(qualification.qualification_cases(qualification.qualification_projection(SHORT, "LOCAL_TEXT"))) == 8
    for cases in (record["cases"][:10], [*record["cases"][:10], *reversed(record["cases"][10:])]):
        damaged = {**record, "cases": cases}
        assert not qualification.QualificationRecord.model_validate(old._seal(damaged)).permits(projection, "en", old.NOW)
    with pytest.raises(ValueError):
        qualification.case_scope("long-full-en")
    assert qualification.case_scope("long-full-en", profile_id=LONG) == "YT_TIMED"


@pytest.mark.parametrize("damage", ["scope", "short-profile", "short-receipt", "full-origin", "full-source", "full-snapshot", "capacity", "output", "options", "schema"])
def test_resealed_cross_profile_full_source_and_capacity_damage_rejected(damage):
    record, projection = fixture(LONG, "YT_TIMED")
    if damage == "scope":
        projection = {**projection, "scope": "LOCAL_TEXT"}
    elif damage == "short-profile":
        record["binding"] = qualification.qualification_binding(qualification.qualification_projection(SHORT, "YT_TIMED"))
    elif damage == "short-receipt":
        record["cases"][0]["profile_hash"] = qualification.qualification_binding(qualification.qualification_projection(SHORT, "YT_TIMED"))["profile_hash"]
    elif damage in {"full-origin", "full-source", "full-snapshot"}:
        key = {"full-origin": "origin", "full-source": "source_id", "full-snapshot": "snapshot_hash"}[damage]
        record["cases"][-1]["source_manifest"][key] = "SYNTHETIC_CONTROL" if damage == "full-origin" else digest("different")
    elif damage == "capacity":
        record["cases"][0]["prompt_tokens"] = 32768 - 6144 - 1
    elif damage == "output":
        record["cases"][0]["output_tokens"] = 6144
    else:
        projection = {**projection, damage: {}}
        record["binding"] = qualification.qualification_binding(projection)
    assert not qualification.QualificationRecord.model_validate(old._seal(record)).permits(projection, "en", old.NOW)


def test_four_unique_current_profile_scope_records_coexist_but_never_choose_a_duplicate():
    records = [fixture(profile, scope)[0] for profile, scope in [(SHORT, "YT_TIMED"),
        (SHORT, "LOCAL_TIMED"), (SHORT, "LOCAL_TEXT"), (LONG, "YT_TIMED")]]
    def raw(values):
        return json.dumps({"version": qualification.VERSION, "records": values}).encode()
    authority = qualification.read_reviewed_qualifications(raw(records))
    assert len(authority.states(now=old.NOW)) == 4
    # Explicit internal seal is ENGINEERING_ONLY: test pair selection, not live package admission.
    authority._seal = qualification._PACKAGE_AUTHORITY_SEAL
    for profile, scope in [(SHORT, "YT_TIMED"), (LONG, "YT_TIMED")]:
        assert authority.permits(qualification.qualification_projection(profile, scope), "en", now=old.NOW)
    assert qualification.read_reviewed_qualifications(raw([records[0], records[0]])).states() == ()
    assert qualification.read_reviewed_qualifications(raw([*records, records[0]])).states() == ()
    for profile, scope in [(FIXED_RUNTIME_PROFILE_ID, "YT_TIMED"), (LONG, "LOCAL_TIMED"), ("unknown", "YT_TIMED")]:
        with pytest.raises(ValueError):
            qualification.qualification_projection(profile, scope)
    unknown = copy.deepcopy(records[0])
    unknown["binding"]["profile_id"] = "unknown"
    assert qualification.read_reviewed_qualifications(raw([old._seal(unknown)])).states() == ()


def test_long_single_case_permit_requires_all_prior_ten_and_first_full_review(monkeypatch):
    record, projection = fixture(LONG, "YT_TIMED")
    case = record["cases"][-1]
    issued = __import__("datetime").datetime.now(__import__("datetime").UTC)
    value = dict(version="local-grounding-once-permit-v1", case_id=case["case_id"], execution_id=case["execution_id"],
        input_hash=case["input_hash"], context_hash=case["context_hash"], request_hash=case["request_hash"],
        binding=record["binding"], source_manifest_hash=case["source_manifest_hash"], capacity_proof_hash="e" * 64,
        runtime_proof_hash="f" * 64, harness_hash="a" * 64, freeze_hash="b" * 64,
        issued_at=issued.isoformat(), expires_at=(issued + timedelta(minutes=5)).isoformat(), prior_review_hashes=["c" * 64] * 11)
    def permit():
        return qualification.LocalExecutionPermit.model_validate({**value, "permit_hash": digest(value)})
    assert permit().matches(projection, case["input_hash"], case["request_hash"], "zh-CN")
    value["prior_review_hashes"].pop()
    assert not permit().matches(projection, case["input_hash"], case["request_hash"], "zh-CN")


@pytest.mark.parametrize("profile_id,scope", [(SHORT, "LOCAL_TIMED"), (SHORT, "LOCAL_TEXT"), (LONG, "YT_TIMED")])
@pytest.mark.parametrize("damage", ["missing", "zero-positive", "positive-negative", "review-differs"])
def test_current_receipts_require_matching_independent_reviewed_real_outcome(profile_id, scope, damage):
    record, projection = fixture(profile_id, scope)
    case = record["cases"][-1 if damage == "positive-negative" else 0]
    if damage == "missing":
        del case["outcome"]
        del case["review"]["outcome"]
    elif damage == "review-differs":
        case["review"]["outcome"] = "NO_NEW"
    else:
        case["outcome"] = case["review"]["outcome"] = "NO_NEW" if damage == "zero-positive" else "INTELLIGENCE"
        if profile_id == LONG and damage == "positive-negative":
            # last long case is a substantive positive: damage a real negative instead.
            case = record["cases"][2]
            case["outcome"] = case["review"]["outcome"] = "INTELLIGENCE"
    assert not qualification.QualificationRecord.model_validate(old._seal(record)).permits(projection, "en", old.NOW)


@pytest.mark.parametrize("key,bad", [("evidence_count", 20), ("cue_count", 2405), ("source_id", "other")])
def test_long_full_requires_exact_complete_source_metadata(key, bad):
    record, projection = fixture(LONG, "YT_TIMED")
    for case in record["cases"][-2:]:
        case["source_manifest"][key] = bad
    assert not qualification.QualificationRecord.model_validate(old._seal(record)).permits(projection, "en", old.NOW)
