"""Cross-phase authority consumption without any production generation route."""

import json
import zipfile
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
from youtube_intel.deep_analysis_qualification import PRODUCTION_QUALIFICATION_RECORDS
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.runtime_composition import _deep_analysis_production_capability
from youtube_intel.state import SQLiteStateRepository

authority = _load_module("test_v1x_phase1b_authority")
delta = _load_module("test_v1x_knowledge_delta")
governance = _load_module("test_v1x_phase1c_governance")


def application(repository, vault: Path | None, monkeypatch):
    # A failed/not-tested reviewed record cannot activate even if discovery
    # were reachable. No network or real provider is needed for consumption.
    import youtube_intel.deep_analysis_activation as activation

    monkeypatch.setattr(activation, "_local_probe", lambda _: "UNREACHABLE")
    service = authority.service(repository)
    service._capability = _deep_analysis_production_capability()
    assert service._capability.execution_route() is None
    assert not PRODUCTION_QUALIFICATION_RECORDS[0].passes()
    assert service._capability.describe()[0]["qualification_status"] == "STALE"
    return LocalApiApplication(
        repository, ProductOrchestrationService(repository),
        deep_analysis_service=service, vault_root=vault,
        now=lambda: delta.NOW,
    )


def test_production_none_publish_does_not_change_delta_or_database_and_restores(
    tmp_path: Path, monkeypatch,
) -> None:
    repository = authority.seed(tmp_path)
    captured = {}
    result = authority.service(repository, capture=captured).run(content_id=authority.VIDEO)
    delta.content(repository, "recent-content", delta.NOW)
    vault = tmp_path / "external-vault"
    vault.mkdir()
    app = application(repository, vault, monkeypatch)
    route = f"/api/v1/videos/{authority.VIDEO}/deep-analysis"
    code, body = app.handle("GET", route)
    assert code == 200
    assert body["deep_analysis"]["status"]["production_eligible"] is False
    assert body["deep_analysis"]["status"]["availability"] == "NOT_QUALIFIED"
    assert body["deep_analysis"]["result"]["evidence_citation_status"] == "DURABLE_EVIDENCE_VERIFIED"
    assert body["deep_analysis"]["result"]["result_identity"] == result.result_identity
    durable_ids = {ref for role in result.roles for ref in role.evidence_ids}
    assert not durable_ids.intersection(captured["candidates"])
    code, evidence = app.handle("GET", f"/api/v1/videos/{authority.VIDEO}/evidence")
    assert code == 200
    assert durable_ids <= {item["evidence_id"] for item in evidence["evidence"]}
    code, before_delta = app.handle("GET", "/api/v1/knowledge-delta")
    assert code == 200
    assert delta.category(before_delta["knowledge_delta"], "content_completed")["count"] == 1
    with repository._connect() as connection:
        before_database = "\n".join(connection.iterdump())
    code, status = app.handle("GET", route + "/obsidian")
    assert code == 200 and status["publish"]["state"] == "AVAILABLE"
    assert not list(vault.rglob("*.md"))
    code, published = app.handle("POST", route + "/obsidian", json.dumps({"result_identity": result.result_identity}).encode())
    assert code == 200 and published["publish"]["state"] == "PUBLISHED"
    note = vault / published["publish"]["relative_path"]
    markdown = note.read_bytes()
    assert b"[[" not in markdown
    assert all(ref.encode() in markdown for ref in durable_ids)
    assert not any(ref.encode() in markdown for ref in captured["candidates"])
    assert app.handle("GET", "/api/v1/knowledge-delta") == (200, before_delta)
    with repository._connect() as connection:
        assert "\n".join(connection.iterdump()) == before_database

    backup = BackupRestoreService(database=tmp_path / "state.sqlite3", data_root=tmp_path / "data")
    created = backup.create_backup()
    archive, _ = backup.backup_download(created.backup_id)
    with zipfile.ZipFile(archive) as contents:
        assert not any("vault" in name.lower() or "delta" in name.lower() for name in contents.namelist())
        assert not any(contents.read(name) == markdown for name in contents.namelist())
    note.unlink()  # disposable projection; restoring core state must not restore it
    staged = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert not note.exists()
    restarted = SQLiteStateRepository(tmp_path / "state.sqlite3")
    trusted = DeepAnalysisPersistenceStore(restarted).read_persisted_deep_analysis_result(result_identity=result.result_identity)
    assert trusted is not None and trusted.durable_result is not None
    restored_app = application(restarted, vault, monkeypatch)
    assert restored_app.handle("GET", "/api/v1/knowledge-delta") == (200, before_delta)
    code, republished = restored_app.handle("POST", route + "/obsidian", json.dumps({"result_identity": result.result_identity}).encode())
    assert code == 200 and republished["publish"]["state"] == "PUBLISHED"
    assert note.read_bytes() == markdown


def test_production_none_empty_delta_no_result_and_missing_vault(tmp_path: Path, monkeypatch) -> None:
    repository = authority.seed(tmp_path)
    app = application(repository, None, monkeypatch)
    route = f"/api/v1/videos/{authority.VIDEO}/deep-analysis"
    code, body = app.handle("GET", route)
    assert code == 200 and body["deep_analysis"]["result"] is None
    assert body["deep_analysis"]["status"]["availability"] == "NOT_QUALIFIED"
    with pytest.raises(ApiError) as rejected:
        app.handle("POST", route, b"{}")
    assert rejected.value.status == 409
    assert rejected.value.details["reason_code"] == "NO_QUALIFIED_MODEL"
    code, body = app.handle("GET", "/api/v1/knowledge-delta")
    assert code == 200 and body["knowledge_delta"]["status"] == "available"
    assert all(category["count"] == 0 for category in body["knowledge_delta"]["categories"])
    assert app.handle("GET", route + "/obsidian") == (200, {"publish": {"state": "NO_VAULT"}})
    result = authority.service(repository).run(content_id=authority.VIDEO)
    assert app.handle("GET", route)[1]["deep_analysis"]["result"]["result_identity"] == result.result_identity
    with pytest.raises(ApiError) as rejected:
        app.handle("POST", route + "/obsidian", json.dumps({"result_identity": result.result_identity}).encode())
    assert rejected.value.status == 409 and rejected.value.code == "NO_VAULT"


@pytest.mark.parametrize("consent", [False, None])
def test_cloud_fixture_consent_absent_or_denied_with_all_api_surfaces(tmp_path: Path, consent) -> None:
    repository, service, route, calls = governance.setup(tmp_path)
    app = LocalApiApplication(repository, ProductOrchestrationService(repository), deep_analysis_service=service, now=lambda: delta.NOW)
    path = f"/api/v1/videos/{authority.VIDEO}/deep-analysis"
    assert app.handle("GET", "/api/v1/knowledge-delta")[0] == 200
    code, body = app.handle("POST", path + "/preflight", json.dumps({"route_id": route.route_id}).encode())
    assert code == 200 and calls == []
    request = {"route_id": route.route_id, "execution_id": body["preflight"]["execution_id"], "acknowledge_unknown_cost": True}
    if consent is not None:
        request["authorize_cloud"] = consent
    with pytest.raises(ApiError) as rejected:
        app.handle("POST", path, json.dumps(request).encode())
    assert rejected.value.status == 409
    assert rejected.value.details["reason_code"] == "CLOUD_CONSENT_REQUIRED"
    assert calls == []
    assert app.handle("GET", path + "/obsidian")[0] == 200
