"""STRUCTURAL FAKE evidence/transport only: none of these fixtures qualify a model.

Only the fixed package read is substituted to prove the future reviewed seam.
The actual resource stays empty; factory, API, budgets, SQLite and restore run.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import _load_module

from youtube_intel import system_synthesis_persistence as persistence
from youtube_intel import system_synthesis_profile as profile
from youtube_intel import system_synthesis_qualification as q
from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.cloud_spending_policy import price_disclosure
from youtube_intel.distillation import (
    CloudDistillationAuthorization,
    CloudDistillationPreDispatchError,
    ReviewedSynthesisProductionAuthorizationAuthority,
)
from youtube_intel.local_api import ApiError
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.synthesis_runtime import MoonshotSystemSynthesisTransport

runtime_tests = _load_module("test_synthesis_runtime")
qa = _load_module("test_qa_launch_isolation")
NOW = datetime.now(UTC).replace(microsecond=0)


def seal_record(value: dict[str, Any]) -> dict[str, Any]:
    for case in value["cases"]:
        review = case["review"]
        review["review_sha256"] = q.digest({k: v for k, v in review.items() if k != "review_sha256"})
    value["matrix_sha256"] = q.digest([{key: case[key] for key in (
        "case_id", "output_language", "scope", "source_origin", "source_id", "snapshot_sha256",
        "summary_sha256", "evidence_sha256", "input_sha256", "wire_sha256")} for case in value["cases"]])
    value["record_sha256"] = q.digest({k: v for k, v in value.items() if k != "record_sha256"})
    return value


def record_fixture() -> dict[str, Any]:
    binding = q.qualification_binding()
    cases = []
    for index, (case_id, language) in enumerate(q.CASE_LANGUAGES.items()):
        identity = "aircAruvnKk" if index < 2 else "IwglW_hIL_g" if index < 4 else case_id
        outcome = "INTELLIGENCE" if index < 4 else "NO_NEW_INTELLIGENCE"
        case = {"case_id": case_id, "output_language": language, "scope": q.SCOPE, "mode": "LIVE_MODEL",
            "source_origin": "PUBLIC_SNAPSHOT" if index < 4 else "SYNTHETIC_CONTROL", "source_id": identity,
            "producer_id": "STRUCTURAL_FAKE_PRODUCER", "execution_id": "STRUCTURAL_FAKE:" + case_id,
            "profile_sha256": binding["profile_sha256"], "code_sha256": binding["code_sha256"],
            "freeze_sha256": q.digest("STRUCTURAL_FAKE_FREEZE"), "oracle_sha256": q.digest("STRUCTURAL_FAKE_ORACLE"),
            **{key: q.digest(identity + key) for key in ("snapshot_sha256", "summary_sha256", "evidence_sha256")},
            **{key: q.digest(case_id + key) for key in ("input_sha256", "wire_sha256", "raw_sha256", "final_sha256", "receipt_sha256")},
            "generation_count": 1, "ledger_invocation_count": 1, "done_reason": "stop", "prompt_tokens": 100,
            "output_tokens": 100, "outcome": outcome,
            "completed_at": (NOW - timedelta(seconds=20 - index * 2)).isoformat()}
        case["review"] = {"reviewer_id": "STRUCTURAL_FAKE_INDEPENDENT_REVIEWER", "verdict": "PASS", "outcome": outcome,
            **{key: case[key] for key in ("case_id", "input_sha256", "wire_sha256", "receipt_sha256", "final_sha256", "oracle_sha256")},
            "reviewed_at": (NOW - timedelta(seconds=19 - index * 2)).isoformat()}
        cases.append(case)
    return seal_record({"version": q.VERSION, "binding": binding, "generated_at": (NOW - timedelta(seconds=1)).isoformat(),
        "freeze_sha256": cases[0]["freeze_sha256"], "oracle_sha256": cases[0]["oracle_sha256"], "cases": cases})


def payload(record: dict[str, Any]) -> bytes:
    return profile.canonical({"version": q.VERSION, "records": [record]}).encode()


def package_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: bytes) -> None:
    resource = tmp_path / "STRUCTURAL_FAKE_PACKAGE.json"
    resource.write_bytes(raw)
    package = Path(q.__file__).parent
    class Package:
        def joinpath(self, name: str) -> Path:
            return resource if name == "resources/system_synthesis_qualification_v1.json" else package / name
    monkeypatch.setattr(q, "resources", SimpleNamespace(files=lambda name: Package()))


def test_default_raw_and_constructor_cannot_mint_reviewed_production(tmp_path, monkeypatch):
    record = record_fixture()
    assert q.QualificationRecord.model_validate(record).permits(profile.ATTRIBUTION_PROFILE_ID, q.SCOPE, "en", NOW)
    assert not q.read_reviewed_qualifications().permits(profile.ATTRIBUTION_PROFILE_ID, "en", now=NOW)
    raw_authority = q.read_reviewed_qualifications(payload(record))
    assert not raw_authority.permits(profile.ATTRIBUTION_PROFILE_ID, "en", now=NOW)
    assert not ReviewedSynthesisProductionAuthorizationAuthority.resolve(authority=raw_authority, available=True).qualified
    with pytest.raises(TypeError):
        q.SynthesisQualificationAuthority(record, object())
    with pytest.raises(TypeError):
        ReviewedSynthesisProductionAuthorizationAuthority.resolve(authority=SimpleNamespace(permits=lambda *a: True), available=True)
    package_fixture(tmp_path, monkeypatch, payload(record))
    authority = q.read_reviewed_qualifications()
    assert authority.permits(profile.ATTRIBUTION_PROFILE_ID, "en", now=NOW)
    assert authority.permits(profile.ATTRIBUTION_PROFILE_ID, "zh-CN", now=NOW + timedelta(days=365))
    assert not authority.permits(profile.PROFILE_ID, "en", now=NOW)
    assert not authority.permits(profile.ATTRIBUTION_PROFILE_ID, "fr", now=NOW)
    assert not authority.permits(profile.ATTRIBUTION_PROFILE_ID, "en", scope="LOCAL_TIMED", now=NOW)


@pytest.mark.parametrize("damage", ["missing", "order", "language", "scope", "profile", "policy", "code", "fixture",
    "generation", "ledger", "failed", "same-reviewer", "receipt", "final", "oracle", "matrix", "freeze", "time",
    "positive-en", "positive-zh", "positive-control", "public-source", "snapshot", "duplicate-execution", "unknown"])
def test_rehashed_incomplete_or_false_records_stay_closed(tmp_path, monkeypatch, damage):
    record = record_fixture()
    case = record["cases"][0]
    if damage == "missing":
        record["cases"].pop()
    elif damage == "order":
        record["cases"].reverse()
    elif damage == "language":
        case["output_language"] = "zh-CN"
    elif damage == "scope":
        record["binding"]["scope"] = "LOCAL_TIMED"
    elif damage in {"profile", "policy", "code"}:
        record["binding"][damage + "_sha256"] = "0" * 64
    elif damage == "fixture":
        case["mode"] = "FIXTURE_CONTRACT"
    elif damage in {"generation", "ledger"}:
        case["generation_count" if damage == "generation" else "ledger_invocation_count"] = 2
    elif damage == "failed":
        case["review"]["verdict"] = "FAIL"
    elif damage == "same-reviewer":
        case["review"]["reviewer_id"] = case["producer_id"]
    elif damage in {"receipt", "final", "oracle"}:
        case["review"][damage + "_sha256"] = "0" * 64
    elif damage == "matrix":
        case["snapshot_sha256"] = "not-a-hash"
    elif damage == "freeze":
        case["freeze_sha256"] = "0" * 64
    elif damage == "time":
        case["completed_at"] = (NOW + timedelta(days=1)).isoformat()
    elif damage in {"positive-en", "positive-zh"}:
        for item in record["cases"][:4]:
            if item["output_language"] == ("en" if damage == "positive-en" else "zh-CN"):
                item["outcome"] = item["review"]["outcome"] = "NO_NEW_INTELLIGENCE"
    elif damage == "positive-control":
        record["cases"][4]["outcome"] = record["cases"][4]["review"]["outcome"] = "INTELLIGENCE"
    elif damage == "public-source":
        case["source_origin"] = "SYNTHETIC_CONTROL"
    elif damage == "snapshot":
        case["snapshot_sha256"] = "0" * 64
    elif damage == "duplicate-execution":
        case["execution_id"] = record["cases"][1]["execution_id"]
    else:
        record["eligibility"] = True
    package_fixture(tmp_path, monkeypatch, payload(seal_record(record)))
    authority = q.read_reviewed_qualifications()
    assert not authority.permits(profile.ATTRIBUTION_PROFILE_ID, "en", now=NOW)
    assert not ReviewedSynthesisProductionAuthorizationAuthority.resolve(authority=authority, available=True).production_eligible


@pytest.mark.parametrize("raw", [b"", b"{}", b"[]", b"{", b"\xff", b"x" * 262145,
    b'{"version":"system-synthesis-reviewed-qualification-v1","version":"bad","records":[]}',
    b'{"version":"unknown","records":[]}'])
def test_malformed_package_is_fail_closed(tmp_path, monkeypatch, raw):
    package_fixture(tmp_path, monkeypatch, raw)
    assert not q.read_reviewed_qualifications().permits(profile.ATTRIBUTION_PROFILE_ID, "en")


def test_missing_or_duplicate_package_records_never_select_a_favorable_record(tmp_path, monkeypatch):
    record = record_fixture()
    package_fixture(tmp_path, monkeypatch, profile.canonical({"version": q.VERSION, "records": [record, record]}).encode())
    assert not q.read_reviewed_qualifications().permits(profile.ATTRIBUTION_PROFILE_ID, "en")
    (tmp_path / "STRUCTURAL_FAKE_PACKAGE.json").unlink()
    assert not q.read_reviewed_qualifications().permits(profile.ATTRIBUTION_PROFILE_ID, "en")


def materializer() -> Any:
    script = Path(__file__).resolve().parents[2] / "scripts/validation/materialize_synthesis_inputs.py"
    spec = importlib.util.spec_from_file_location("authority_offline_domain_fixture", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def actual_factory(tmp_path, monkeypatch, *, qualified=True, credential=True, enabled=True, record=None):
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *args: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *args: {})
    monkeypatch.setattr("youtube_intel.deep_analysis_activation._local_probe", lambda *args: "MODEL_UNAVAILABLE")
    if qualified:
        package_fixture(tmp_path, monkeypatch, payload(record if record is not None else record_fixture()))
    module = materializer()
    root = tmp_path / "owned-domain"
    with module.offline():
        video = module.seed_synthetic(root, "STRUCTURAL_FAKE_NORMAL_AUTHORITY", "en", False)
        for name in ("data", "logs", "templates", "vault"):
            (root / name).mkdir(exist_ok=True)
        values = module.load_settings(module.REPO / "config/settings.example.yaml").model_dump()
        values["storage"]["vault_root"] = str(root / "vault")
        config = module.AppConfig(channels=(), settings=module.AppSettings.model_validate(values))
        store = qa.FakeStore()
        if credential:
            store.save("STRUCTURAL_FAKE_KEY")
        composition = build_local_source_run_runtime(config=config, project_root=root, database=root / "state.sqlite3",
            credential_store=store, bigmodel_credential_store=qa.FakeStore(), allow_environment_credentials=False,
            allow_cloud_execution=enabled, now=lambda: NOW)
        # The input-only fixture keeps its trusted timed-cue parent outside the
        # UI's canonical display directory. Add a genuine same-byte owned
        # canonical display artifact; do not edit its original parent/proofs.
        original = composition.repository.latest_artifact(video, module.ArtifactKind.TRANSCRIPT_CANONICAL)
        raw = (root / "data" / original.relative_path).read_bytes()
        relative = "transcripts/STRUCTURAL_FAKE_CANONICAL.txt"
        path = root / "data" / relative
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
        composition.repository.upsert_artifact(module.ArtifactWrite(
            artifact_id=original.artifact_id + "-ui", artifact_key=original.artifact_key + "-ui", video_id=video, job_id=None,
            kind=module.ArtifactKind.TRANSCRIPT_CANONICAL, storage_root=module.StorageRoot.DATA,
            relative_path=relative, content_hash=original.content_hash, provider=module.SYNTHETIC, model=None,
            producer_version="STRUCTURAL_FAKE_UI_DISPLAY", retention_class=module.RetentionClass.LONG_LIVED, expires_at=None), now=NOW)
        composition.application.handle("PUT", "/api/v1/settings/output-language", b'{"output_language":"en"}')
    calls = []
    service = composition.application._cloud_synthesis_v2_service
    def wire(request, secret, timeout, retries):
        assert secret == "STRUCTURAL_FAKE_KEY" and retries == 0
        calls.append(request)
        return runtime_tests.moonshot._response(content=runtime_tests.storage.raw_positive(), model=profile.PAIR[1])
    monkeypatch.setattr(service._transport, "_wire_transport", wire)
    return module, root, video, composition, service, calls


def configure(app, *, amount="1"):
    return app.handle("PUT", "/api/v1/settings/cloud-spending-policy", json.dumps({"expected_revision": 0,
        "enabled": True, "total_cny": "8", "per_request_cny": amount, "max_calls": 8,
        "accept_price_hash": price_disclosure(profile.ATTRIBUTION_PROFILE_ID)["price_hash"], "acknowledge": True}).encode())


def review(app, video, identity=profile.ATTRIBUTION_PROFILE_ID, **extra):
    return app.handle("POST", f"/api/v1/videos/{video}/cloud-intelligence/review", json.dumps({
        "profile_id": identity, "command_id": "STRUCTURAL_FAKE_NORMAL", **extra}).encode())[1]["review"]


def confirm(app, video, value, **extra):
    return app.handle("POST", f"/api/v1/videos/{video}/cloud-intelligence/confirm", json.dumps({
        "profile_id": profile.ATTRIBUTION_PROFILE_ID, "execution_id": value["execution_id"],
        "review_hash": value["review_hash"], "authorize": True, **extra}).encode())


@pytest.mark.parametrize("gate", ["qualification", "credential", "execution", "budget", "insufficient", "consent"])
def test_actual_factory_independent_gates_refuse_without_claim_or_wire(tmp_path, monkeypatch, gate):
    module, root, video, composition, service, calls = actual_factory(tmp_path, monkeypatch,
        qualified=gate != "qualification", credential=gate != "credential", enabled=gate != "execution")
    app = composition.application
    if gate != "budget":
        configure(app, amount="0.000001" if gate == "insufficient" else "1")
    before = module.inventory(root)
    with module.offline():
        value = review(app, video)
        assert value["readiness"]["can_confirm"] is (gate == "consent")
        with pytest.raises(ApiError):
            confirm(app, video, value, **({"authorize": False} if gate == "consent" else {}))
    assert calls == [] and composition.repository.get_distillation_execution(value["execution_id"]) is None
    assert module.inventory(root) == before
    assert composition.backup_restore.readiness()["ready"]


def test_actual_normal_confirm_save_topic_restart_restore_and_holds(tmp_path, monkeypatch):
    module, root, video, composition, service, calls = actual_factory(tmp_path, monkeypatch)
    app = composition.application
    configure(app)
    with module.offline():
        profiles = app.handle("GET", "/api/v1/cloud-intelligence/profiles")[1]["profiles"]
        assert profiles[-1]["qualified"] and not profiles[-2]["qualified"]
        old = review(app, video, profile.PROFILE_ID)
        assert "MODEL_UNQUALIFIED" in old["readiness"]["blockers"]
        value = review(app, video)
        assert value["readiness"]["can_confirm"]
        before = module.inventory(root)
        assert review(app, video)["verified_input_hash"] == value["verified_input_hash"]
        assert module.inventory(root) == before and calls == []
        status, result = confirm(app, video, value)
        assert status == 202 and result["execution"]["status"] == "SUCCEEDED" and len(calls) == 1
        intelligence = result["execution"]["intelligence_id"]
        assert app.handle("GET", f"/api/v1/intelligence/{intelligence}")[1]["intelligence"]["trusted"]
        app.handle("POST", "/api/v1/saved-intelligence/save", json.dumps({"intelligence_id": intelligence}).encode())
        topic = app.handle("POST", "/api/v1/topics", b'{"command_id":"authority-fixture","name":"Structural fixture"}')[1]["topic"]["topic_id"]
        app.handle("POST", f"/api/v1/topics/{topic}/associations", json.dumps({"intelligence_id": intelligence,
            "association_kind": "NEW_INFORMATION"}).encode())
        with pytest.raises(ApiError):
            confirm(app, video, value)
    policy = service._spending_policy
    assert policy.status()["held_requests"] == 1
    journal = policy.path.read_bytes()
    before_restore = module.inventory(root)
    backup = composition.backup_restore
    archive = backup.backup_download(backup.create_backup().backup_id)[0]
    import zipfile
    with zipfile.ZipFile(archive) as zipped:
        assert not any("qualification" in name for name in zipped.namelist())
    staged = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert backup.readiness()["last_restore"]["state"] == "APPLIED"
    assert module.inventory(root) == before_restore
    assert policy.path.read_bytes() == journal
    restarted = BackupRestoreService(database=composition.repository._database_path, data_root=root / "data")
    from youtube_intel.cloud_spending_policy import CloudSpendingPolicy
    assert CloudSpendingPolicy(composition.repository, restarted).status()["held_requests"] == 1
    assert composition.repository.get_distillation_execution(value["execution_id"]).invocation_count == 1
    assert app.handle("GET", f"/api/v1/topics/{topic}")[0] == 200
    assert len(calls) == 1 and service.reviewed_synthesis_qualified()


def test_permit_checks_exact_proof_scope_language_and_current_binding_at_boundary(tmp_path, monkeypatch):
    module, root, video, composition, service, calls = actual_factory(tmp_path, monkeypatch)
    app = composition.application
    configure(app)
    value = review(app, video)
    verified = service._cloud_previews[value["review_hash"]][1]
    transport = service._transport
    assert transport.is_authorized_for_normal_production(verified)
    v1_transport = MoonshotSystemSynthesisTransport(authorization=transport._authorization,
        credential_resolver=lambda: pytest.fail("v1 borrowed a v2 permit"))
    old_review = review(app, video, profile.PROFILE_ID)
    old_verified = app._cloud_synthesis_service._cloud_previews[old_review["review_hash"]][1]
    assert not v1_transport.is_authorized_for(old_verified)
    for changed in (replace(verified, content_provider="LOCAL"), replace(verified, wire_version=profile.PROFILE_ID),
        replace(verified, output_language="zh-CN"), replace(verified, input_json="{}")):
        assert not transport.is_authorized_for_normal_production(changed)
        with pytest.raises(CloudDistillationPreDispatchError):
            transport.generate(changed)
    before = module.inventory(root)
    binding = q.qualification_binding()
    monkeypatch.setattr(q, "qualification_binding", lambda: {**binding, "code_sha256": "0" * 64})
    assert not service.reviewed_synthesis_qualified()
    assert not app.handle("GET", "/api/v1/cloud-intelligence/profiles")[1]["profiles"][-1]["qualified"]
    with pytest.raises(ApiError):
        confirm(app, video, value)
    with pytest.raises(CloudDistillationPreDispatchError):
        transport.generate(verified)
    assert calls == [] and module.inventory(root) == before


def test_authority_is_checked_again_after_credential_resolution_before_wire(tmp_path, monkeypatch):
    module, root, video, composition, service, calls = actual_factory(tmp_path, monkeypatch)
    value = review(composition.application, video)
    verified = service._cloud_previews[value["review_hash"]][1]
    before = module.inventory(root)
    binding = q.qualification_binding()
    def credential():
        monkeypatch.setattr(q, "qualification_binding", lambda: {**binding, "code_sha256": "0" * 64})
        return "STRUCTURAL_FAKE_KEY"
    monkeypatch.setattr(service._transport, "_credential_resolver", credential)
    with pytest.raises(CloudDistillationPreDispatchError, match="changed before dispatch"):
        service._transport.generate(verified)
    assert calls == [] and module.inventory(root) == before


@pytest.mark.parametrize("damage", ["scope", "source-provider", "video-provider", "availability", "capture"])
def test_rehashed_scope_or_capture_mixture_cannot_reach_actual_transport(tmp_path, monkeypatch, damage):
    module, root, video, composition, service, calls = actual_factory(tmp_path, monkeypatch)
    value = review(composition.application, video)
    verified = service._cloud_previews[value["review_hash"]][1]
    proof = json.loads(verified.input_json)
    if damage == "scope":
        proof["source_scope"] = "LOCAL_TIMED"
    elif damage in {"source-provider", "video-provider"}:
        proof["capture"]["source" if damage == "source-provider" else "video"]["provider"] = "LOCAL"
    elif damage == "availability":
        proof["capture"]["video"]["availability"] = "private"
    else:
        proof["capture"]["video"]["title"] = "Unbound capture cannot borrow reviewed input"
    wire = profile.canonical(proof)
    changed = replace(verified, input_json=wire, semantic_hash=profile.sha(wire))
    before = module.inventory(root)
    assert not service._transport.is_authorized_for_normal_production(changed)
    with pytest.raises(CloudDistillationPreDispatchError):
        service._transport.generate(changed)
    assert calls == [] and module.inventory(root) == before


def test_possibly_sent_failure_keeps_invocation_and_unknown_cost_hold(tmp_path, monkeypatch):
    module, root, video, composition, service, calls = actual_factory(tmp_path, monkeypatch)
    app = composition.application
    configure(app)
    value = review(app, video)
    def sent_then_failed(request, *args):
        calls.append(request)
        raise CloudDistillationPreDispatchError("synthetic wire cannot assert a pre-send outcome")
    monkeypatch.setattr(service._transport, "_wire_transport", sent_then_failed)
    with module.offline():
        status, result = confirm(app, video, value)
    assert status == 202 and result["execution"]["status"] == "AMBIGUOUS"
    execution = composition.repository.get_distillation_execution(value["execution_id"])
    assert execution.invocation_count == 1 and len(calls) == 1
    assert service._spending_policy.status()["held_requests"] == 1
    assert composition.repository.get_distillation_resource_usage(execution.execution_id).cost_microunits is None


@pytest.mark.parametrize("damage", ["missing-case", "language", "profile", "policy", "failed", "raw"])
def test_invalid_authority_reaches_no_normal_api_service_or_transport_claim(tmp_path, monkeypatch, damage):
    record = record_fixture()
    if damage == "missing-case":
        record["cases"].pop()
    elif damage == "language":
        record["cases"][0]["output_language"] = "zh-CN"
    elif damage in {"profile", "policy"}:
        record["binding"][damage + "_sha256"] = "0" * 64
    elif damage == "failed":
        record["cases"][0]["review"]["verdict"] = "FAIL"
    seal_record(record)
    if damage == "raw":
        unsealed = q.read_reviewed_qualifications(payload(record))
        monkeypatch.setattr(q, "read_reviewed_qualifications", lambda: unsealed)
    module, root, video, composition, service, calls = actual_factory(tmp_path, monkeypatch,
        qualified=damage != "raw", record=record)
    app = composition.application
    configure(app)
    before = module.inventory(root)
    with module.offline():
        value = review(app, video)
        assert "MODEL_UNQUALIFIED" in value["readiness"]["blockers"]
        with pytest.raises(ApiError):
            confirm(app, video, value)
        with pytest.raises(ValueError):
            service.confirm_cloud_preview(video_id=video, execution_id=value["execution_id"], review_hash=value["review_hash"])
        verified = service._cloud_previews[value["review_hash"]][1]
        with pytest.raises(CloudDistillationPreDispatchError):
            service._transport.generate(verified)
    assert calls == [] and composition.repository.get_distillation_execution(value["execution_id"]) is None
    assert module.inventory(root) == before and service._spending_policy.status()["held_requests"] == 0


def test_raw_record_http_flags_and_pair_only_authority_do_not_open_v2(tmp_path, monkeypatch):
    module, root, video, composition, service, calls = actual_factory(tmp_path, monkeypatch, qualified=False)
    app = composition.application
    configure(app)
    value = review(app, video)
    for extra in ({"qualified": True}, {"authority": record_fixture()}, {"qualification_path": "/tmp/not-authority"}):
        with pytest.raises(ApiError) as error:
            review(app, video, **extra)
        assert error.value.status == 422
    source = value["source_id"]
    direct = service.preview_cloud_execution(source_id=source, video_id=video, evidence_ids=tuple(value["evidence_ids"]),
        manual_command_id="STRUCTURAL_FAKE_NORMAL", qualified=True, credential_available=True)
    assert "MODEL_UNQUALIFIED" in direct["readiness"]["blockers"]
    with pytest.raises(ValueError):
        service.confirm_cloud_preview(video_id=video, execution_id=direct["execution_id"], review_hash=direct["review_hash"])
    from youtube_intel.synthesis_runtime import MoonshotAttributionSynthesisTransport
    pair_only = runtime_tests.SimulatedFutureQualification.resolve(provider=profile.PAIR[0], model=profile.PAIR[1],
        capability_scope=runtime_tests.DistillationCapabilityScope.V1_VIDEO_DISTILLATION, available=True)
    adapter = MoonshotAttributionSynthesisTransport(authorization=CloudDistillationAuthorization.for_normal_production(
        eligibility=pair_only, cloud_enabled=True, credential_available=True), credential_resolver=lambda: pytest.fail("pair-only credential read"))
    verified = service._cloud_previews[value["review_hash"]][1]
    assert not adapter.is_authorized_for_normal_production(verified)
    with pytest.raises(CloudDistillationPreDispatchError):
        adapter.generate(verified)
    assert calls == [] and composition.repository.get_distillation_execution(value["execution_id"]) is None


@pytest.mark.parametrize("terminal", ["CANCELLED", "REJECTED_OUTPUT"])
def test_actual_factory_terminal_history_allows_fresh_explicit_review_only(tmp_path, monkeypatch, terminal):
    module, root, video, composition, service, calls = actual_factory(tmp_path, monkeypatch)
    app = composition.application
    configure(app)
    old_review = review(app, video)
    if terminal == "CANCELLED":
        verified = service._cloud_previews[old_review["review_hash"]][1]
        from youtube_intel.synthesis_runtime import prepared_input
        prepared = prepared_input(verified)
        persistence.reserve(composition.repository, prepared, now=NOW)
        persistence.abandon_unclaimed(composition.repository, prepared.execution_id, now=NOW)
    else:
        def rejected(request, *args):
            calls.append(request)
            return runtime_tests.moonshot._response(content='{"invalid":"STRUCTURAL_FAKE_REJECTION"}', model=profile.PAIR[1])
        monkeypatch.setattr(service._transport, "_wire_transport", rejected)
        assert confirm(app, video, old_review)[1]["execution"]["status"] == "REJECTED_OUTPUT"
    old = composition.repository.get_distillation_execution(old_review["execution_id"])
    assert old.status == terminal and old.invocation_count == (0 if terminal == "CANCELLED" else 1)
    before = module.inventory(root)
    calls_before = len(calls)
    with module.offline():
        detail = app.handle("GET", f"/api/v1/videos/{video}")[1]
        assert detail["intelligence_result"]["status"] == terminal
        assert detail["manual_intelligence_eligible"] is True
        assert detail["transcript"]["status"] == "AVAILABLE" and detail["note"]["v2"]["status"] == "AVAILABLE"
        fresh = review(app, video, command_id="fresh-after-" + terminal)
    assert fresh["readiness"]["can_confirm"] and fresh["execution_id"] != old.execution_id
    assert composition.repository.get_distillation_execution(fresh["execution_id"]) is None
    assert composition.repository.get_distillation_execution(old.execution_id) == old
    assert module.inventory(root) == before and len(calls) == calls_before
