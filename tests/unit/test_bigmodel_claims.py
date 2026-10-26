"""Offline repository claim boundaries; never model or fee qualification."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta

import pytest
from test_backup_restore import (
    NOW,
    _add_source,
    _corrupt_zhipu_authorization_identity,
    _corrupt_zhipu_scalar_preserving_schema,
    _workspace,
)

from youtube_intel.distillation import PersonalizedDistillationService
from youtube_intel.state import (
    DistillationCardWrite,
    DistillationExecutionWrite,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceStance,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    IntelligenceClaimKind,
    SQLiteStateRepository,
    StateStoreError,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    build_evidence_id,
)


def _request_fields():
    return dict(execution_id="zhipu-direct-claim", source_id="source-1", video_id="video-1",
        reason=PersonalizedDistillationService._RESERVATION_REASON,
        use_case=PersonalizedDistillationService._RESERVATION_USE_CASE,
        selected_provider="zhipu_bigmodel", selected_model="glm-4.7-flash", output_language="en")


def _direct_request(repository, *, reserved=False, authorize=True):
    _add_source(repository)
    request = _request_fields()
    create = repository.reserve_distillation_execution if reserved else repository.begin_distillation_execution
    create(DistillationExecutionWrite(**request), now=NOW)
    if authorize:
        repository.authorize_cloud_execution(authorization_id="direct-claim-valid-consent",
            execution_id=request["execution_id"], provider="zhipu_bigmodel", model="glm-4.7-flash",
            verified_input_hash="a" * 64, consent_kind="USER_CONFIRMATION", now=NOW)
    return request


def test_direct_not_checked_blob_hash_refuses_before_claim_write(tmp_path):
    _, data_root, _, repository, _ = _workspace(tmp_path)
    request = _direct_request(repository)
    with repository._connect() as connection:
        checkpoint = connection.execute("SELECT * FROM distillation_execution_checkpoints").fetchone()
        assert checkpoint["budget_state"] == "NOT_CHECKED" and checkpoint["invocation_count"] == 0
        _corrupt_zhipu_scalar_preserving_schema(connection, "distillation_zhipu_cloud_authorizations", "verified_input_hash", b"a" * 64)
        before = tuple(connection.iterdump())
    files = {str(path.relative_to(data_root)): path.read_bytes() for path in data_root.rglob("*") if path.is_file()}
    with pytest.raises(StateStoreError, match="identity"):
        repository.claim_distillation_execution(**request, now=NOW)
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before
        assert connection.execute("SELECT invocation_count FROM distillation_execution_checkpoints").fetchone()[0] == 0
    assert {str(path.relative_to(data_root)): path.read_bytes() for path in data_root.rglob("*") if path.is_file()} == files


def _complete(repository, request, data_root, kind):
    if kind == "rejected":
        return repository.finish_distillation_without_admission(execution_id=request["execution_id"],
            status="AMBIGUOUS", budget_state="UNKNOWN", outcome="TRANSPORT_OUTCOME_UNKNOWN", invocation_count=1,
            actual_provider=None, actual_model=None, input_tokens=None, output_tokens=None,
            cost_microunits=None, duration_ms=None, http_status_code=None, now=NOW)
    evidence_id = build_evidence_id(video_id=request["video_id"], artifact_id="artifact-1", start_ms=0, end_ms=1000,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL)
    common = dict(execution_id=request["execution_id"], evidence_ids=(evidence_id,),
        actual_provider="zhipu_bigmodel", actual_model="glm-4.7-flash", input_tokens=None,
        output_tokens=None, cost_microunits=None, duration_ms=None, http_status_code=200, now=NOW)
    if kind == "no_new":
        return repository.record_distillation_no_new_intelligence(**common, budget_state="ADMITTED")
    return repository.admit_distillation(**common, intelligence_id="offline-claim-card", revision_id="offline-claim-revision",
        claim_kind=IntelligenceClaimKind.SYSTEM_INFERENCE, content_hash="a" * 64,
        evidence_stances=((evidence_id, EvidenceStance.SUPPORTING),),
        card=DistillationCardWrite(source_id=request["source_id"], video_id=request["video_id"],
            core_conclusion="Offline repository fixture, no model output or qualification.",
            user_relevant_information=(), important_new_information=(), meaningful_details=(),
            filtered_noise=(), preference_ids=(), source_policy_revision_id=None))


def _completion_evidence(repository, request, data_root):
    repository.link_source_video(request["source_id"], request["video_id"], discovered_at=NOW)
    evidence_id = build_evidence_id(video_id=request["video_id"], artifact_id="artifact-1", start_ms=0, end_ms=1000,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL)
    text = (data_root / "transcripts/video-1.txt").read_text().strip()
    timed = TimedTranscriptWrite.from_cues(video_id=request["video_id"], canonical_artifact_id="artifact-1",
        cues=(TimedTranscriptCueWrite(start_ms=0, end_ms=1000, text=text),))
    repository.create_timed_transcript(timed, now=NOW)
    evidence = EvidenceWrite(evidence_id=evidence_id, video_id=request["video_id"], artifact_id="artifact-1",
        start_ms=0, end_ms=1000, lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en", availability=EvidenceAvailability.AVAILABLE)
    repository.create_evidence_with_text_binding(evidence, EvidenceTextBindingWrite.from_timed_transcript(
        evidence=evidence, timed_transcript_id=timed.timed_transcript_id, start_cue_index=0, end_cue_index=1, excerpt=text), now=NOW)


@pytest.mark.parametrize("kind", ["rejected", "admitted", "no_new"])
def test_completion_writes_refuse_raw_corrupt_audit_without_row_or_data_changes(tmp_path, kind):
    _, data_root, _, repository, _ = _workspace(tmp_path)
    request = _direct_request(repository)
    _completion_evidence(repository, request, data_root)
    if kind == "no_new":
        assert repository.claim_distillation_execution(**request, now=NOW)
    with repository._connect() as connection:
        _corrupt_zhipu_scalar_preserving_schema(connection, "distillation_zhipu_cloud_authorizations", "verified_input_hash", b"a" * 64)
        before = tuple(connection.iterdump())
    files = {str(path.relative_to(data_root)): path.read_bytes() for path in data_root.rglob("*") if path.is_file()}
    with pytest.raises(StateStoreError, match="identity"):
        _complete(repository, request, data_root, kind)
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before
    assert {str(path.relative_to(data_root)): path.read_bytes() for path in data_root.rglob("*") if path.is_file()} == files


@pytest.mark.parametrize("reserved", [False, True])
@pytest.mark.parametrize("field,value", [
    ("authorization_id", None), ("authorization_id", b"blob-identity-sixteen"),
    ("verified_input_hash", b"a" * 64), ("authorized_at", "0" * 20),
    ("authorized_at", "2028-02-30T08:00:00.000000Z"),
])
def test_every_existing_claim_rejects_raw_new_audit_variants_without_writes(tmp_path, reserved, field, value):
    _, data_root, _, repository, _ = _workspace(tmp_path)
    request = _direct_request(repository, reserved=reserved)
    with repository._connect() as connection:
        if value is None:
            _corrupt_zhipu_authorization_identity(connection)
        else:
            _corrupt_zhipu_scalar_preserving_schema(connection, "distillation_zhipu_cloud_authorizations", field, value)
        before = tuple(connection.iterdump())
    files = {str(path.relative_to(data_root)): path.read_bytes() for path in data_root.rglob("*") if path.is_file()}
    claim = repository.claim_reserved_distillation_execution if reserved else repository.claim_distillation_execution
    with pytest.raises(StateStoreError, match="identity"):
        claim(**request, now=NOW)
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before
    assert {str(path.relative_to(data_root)): path.read_bytes() for path in data_root.rglob("*") if path.is_file()} == files


@pytest.mark.parametrize("reserved", [False, True])
def test_valid_claims_are_once_under_concurrency_and_restart(tmp_path, reserved):
    database, _, _, repository, _ = _workspace(tmp_path)
    request = _direct_request(repository, reserved=reserved)
    method = "claim_reserved_distillation_execution" if reserved else "claim_distillation_execution"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: getattr(SQLiteStateRepository(database), method)(**request, now=NOW + timedelta(seconds=1)), range(2)))
    assert sorted(results) == [False, True]
    restarted = SQLiteStateRepository(database)
    restarted.initialize(now=NOW + timedelta(seconds=2))
    assert getattr(restarted, method)(**request, now=NOW + timedelta(seconds=2)) is False
    with restarted._connect() as connection:
        assert connection.execute("SELECT invocation_count FROM distillation_execution_checkpoints").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM distillation_zhipu_cloud_authorizations").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM distillation_resource_usage").fetchone()[0] == 0


@pytest.mark.parametrize("reserved", [False, True])
def test_claim_without_consent_is_still_refused_without_writes(tmp_path, reserved):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _direct_request(repository, reserved=reserved, authorize=False)
    with repository._connect() as connection:
        before = tuple(connection.iterdump())
    claim = repository.claim_reserved_distillation_execution if reserved else repository.claim_distillation_execution
    with pytest.raises(sqlite3.IntegrityError, match="authorization"):
        claim(**request, now=NOW)
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before


@pytest.mark.parametrize("reserved", [False, True])
def test_claim_preserves_legitimate_later_consent_time(tmp_path, reserved):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _direct_request(repository, reserved=reserved, authorize=False)
    repository.authorize_cloud_execution(authorization_id="direct-later-valid-consent",
        execution_id=request["execution_id"], provider="zhipu_bigmodel", model="glm-4.7-flash",
        verified_input_hash="a" * 64, consent_kind="USER_CONFIRMATION", now=NOW + timedelta(microseconds=123456))
    claim = repository.claim_reserved_distillation_execution if reserved else repository.claim_distillation_execution
    assert claim(**request, now=NOW + timedelta(seconds=1)) is True
    assert claim(**request, now=NOW + timedelta(seconds=2)) is False


@pytest.mark.parametrize("reserved", [False, True])
@pytest.mark.parametrize("status,outcome,budget", [
    ("WAITING_MODEL", "MODEL_UNAVAILABLE_BEFORE_TRANSPORT", "ADMITTED"),
    ("WAITING_BUDGET", "BUDGET_BLOCKED_BEFORE_TRANSPORT", "CLOUD_SPENDING_POLICY_REQUIRED"),
])
def test_zero_call_denial_without_consent_still_records_real_terminal_wait(tmp_path, reserved, status, outcome, budget):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = _direct_request(repository, reserved=reserved, authorize=False)
    result = repository.finish_distillation_without_admission(execution_id=request["execution_id"],
        status=status, budget_state=budget, outcome=outcome, invocation_count=0,
        actual_provider=None, actual_model=None, input_tokens=None, output_tokens=None,
        cost_microunits=None, duration_ms=None, http_status_code=None, now=NOW)
    assert result.status == status and result.invocation_count == 0
    assert repository.get_distillation_resource_usage(request["execution_id"]).invocation_count == 0
    claim = repository.claim_reserved_distillation_execution if reserved else repository.claim_distillation_execution
    assert claim(**request, now=NOW) is False
    with repository._connect() as connection:
        assert connection.execute("SELECT count(*) FROM distillation_zhipu_cloud_authorizations").fetchone()[0] == 0


@pytest.mark.parametrize("kind", ["rejected", "admitted", "no_new"])
def test_legitimate_completion_contracts_remain_supported_without_real_generation(tmp_path, kind):
    _, data_root, _, repository, _ = _workspace(tmp_path)
    request = _direct_request(repository)
    _completion_evidence(repository, request, data_root)
    if kind == "no_new":
        assert repository.claim_distillation_execution(**request, now=NOW)
    result = _complete(repository, request, data_root, kind)
    expected = {"rejected": "AMBIGUOUS", "admitted": "SUCCEEDED", "no_new": "SUCCEEDED_NO_NEW_INTELLIGENCE"}
    assert result.status == expected[kind] and result.invocation_count == 1
    assert repository.get_distillation_resource_usage(request["execution_id"]).status == expected[kind]
    assert repository.claim_distillation_execution(**request, now=NOW) is False


@pytest.mark.parametrize("parameter,value", [
    ("verified_input_hash", b"a" * 64), ("authorization_id", None),
])
def test_atomic_confirmation_malformed_input_never_creates_rows(tmp_path, parameter, value):
    _, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    with repository._connect() as connection:
        before = tuple(connection.iterdump())
    args = dict(authorization_id="cloud-consent:" + "a" * 32, verified_input_hash="a" * 64)
    args[parameter] = value
    with pytest.raises(TypeError):
        repository.confirm_and_claim_cloud_execution(DistillationExecutionWrite(**_request_fields()),
            **args, validate_current=lambda: None, now=NOW)
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before


def test_atomic_confirmation_is_fresh_once_and_cannot_adopt_prior_corrupt_execution(tmp_path):
    database, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution = DistillationExecutionWrite(**_request_fields())
    repository.confirm_and_claim_cloud_execution(execution, authorization_id="cloud-consent:" + "a" * 32,
        verified_input_hash="a" * 64, validate_current=lambda: None, now=NOW)
    with repository._connect() as connection:
        assert connection.execute("SELECT invocation_count FROM distillation_execution_checkpoints").fetchone()[0] == 1
        _corrupt_zhipu_scalar_preserving_schema(connection, "distillation_zhipu_cloud_authorizations", "verified_input_hash", b"a" * 64)
        before = tuple(connection.iterdump())
    with pytest.raises(StateStoreError, match="already exists"):
        SQLiteStateRepository(database).confirm_and_claim_cloud_execution(execution, authorization_id="cloud-consent:" + "b" * 32,
            verified_input_hash="a" * 64, validate_current=lambda: pytest.fail("must not readopt existing execution"), now=NOW)
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before


def test_atomic_fresh_confirmations_race_to_one_claim_without_generation(tmp_path):
    database, _, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    execution = DistillationExecutionWrite(**_request_fields())
    def confirm(index):
        try:
            SQLiteStateRepository(database).confirm_and_claim_cloud_execution(execution,
                authorization_id="cloud-consent:" + str(index) * 32, verified_input_hash="a" * 64,
                validate_current=lambda: None, now=NOW)
            return True
        except StateStoreError as error:
            assert "already exists" in str(error)
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(confirm, [1, 2])) == [False, True]
    with repository._connect() as connection:
        assert connection.execute("SELECT count(*) FROM distillation_zhipu_cloud_authorizations").fetchone()[0] == 1
        assert connection.execute("SELECT invocation_count FROM distillation_execution_checkpoints").fetchone()[0] == 1


@pytest.mark.parametrize("method", ["claim_distillation_execution", "claim_reserved_distillation_execution", "atomic"])
def test_generic_cloud_claim_cannot_take_long_lifecycle_authority(tmp_path, method):
    _, _, _, repository, _ = _workspace(tmp_path)
    request = {**_request_fields(), "execution_id": "distillation:long-timed-v1:" + "a" * 64}
    with repository._connect() as connection:
        before = tuple(connection.iterdump())
    with pytest.raises(StateStoreError, match="dedicated lifecycle"):
        if method == "atomic":
            repository.confirm_and_claim_cloud_execution(DistillationExecutionWrite(**request),
                authorization_id="cloud-consent:" + "a" * 32, verified_input_hash="a" * 64,
                validate_current=lambda: None, now=NOW)
        else:
            getattr(repository, method)(**request, now=NOW)
    with repository._connect() as connection:
        assert tuple(connection.iterdump()) == before


def test_new_cloud_pair_cannot_bind_the_local_long_profile():
    from test_long_distillation_profile import fixture

    from youtube_intel.distillation import bind_local_profile
    from youtube_intel.local_distillation_profile import PROFILE_ID

    _, value = fixture()
    with pytest.raises(ValueError, match="local execution model/input"):
        bind_local_profile(replace(value, selected_provider="zhipu_bigmodel", selected_model="glm-4.7-flash"), PROFILE_ID)
