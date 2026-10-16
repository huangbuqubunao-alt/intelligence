"""Read-only capability presentation; fixtures never qualify or call a model."""
import json

import pytest
from conftest import _load_module

from youtube_intel.local_api import LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService

PROFILE = "local-grounding-qwen35-9b-thinking-v1"
MODEL = "qwen3.5:9b-q4_K_M"


def statuses():
    return tuple({"profile_id": PROFILE, "model": MODEL, "scope": scope,
                  "output_language": language, "status": "NOT_QUALIFIED"}
                 for scope in ("YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT")
                 for language in ("en", "zh-CN"))


def workspace(tmp_path, kind, callback):
    if kind == "YT_TIMED":
        repo, _sid, cid, transport, service, old = _load_module("test_dogfood_day1_intelligence").completed_content(tmp_path, available=False)
        data_root = old._data_root
    else:
        module = _load_module("test_local_intelligence_text" if kind == "LOCAL_TEXT" else "test_local_intelligence_timed")
        values = module._workspace(tmp_path) if kind == "LOCAL_TEXT" else module._local(tmp_path)
        repo, provider, cid = values[:3]
        transport, service = values[-2:]
        data_root = provider.data_root
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=data_root,
                              distillation_service=service, local_distillation_capabilities=callback)
    service._output_language_for_video = lambda _: app._output_language_service.effective().value
    return repo, cid, transport, service, app


@pytest.mark.parametrize("scope", ["YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT"])
@pytest.mark.parametrize("language", ["en", "zh-CN"])
def test_current_source_and_output_language_select_exact_read_only_status(tmp_path, scope, language):
    reads = []
    repo, cid, transport, service, app = workspace(tmp_path, scope, lambda: reads.append("read") or statuses())
    app.handle("PUT", "/api/v1/settings/output-language", json.dumps({"output_language": language}).encode())
    with repo._connect() as connection:
        before = tuple(connection.iterdump())
    settings = app.handle("GET", "/api/v1/settings")[1]
    capability = settings["local_intelligence"]
    assert capability["status"] == "KNOWN" and len(capability["scopes"]) == 6
    assert "runtime_local_model" in settings and "providers" in settings
    detail = app.handle("GET", f"/api/v1/videos/{cid}")[1]["local_intelligence"]
    assert detail["video_id"] == cid and detail["scope"] == scope and detail["output_language"] == language
    assert detail["model"] == MODEL and detail["profile_id"] == PROFILE
    assert detail["qualification_status"] == "NOT_QUALIFIED"
    assert detail["request_state"] == "WAITING_MODEL"
    assert detail["runtime_binding"] == service.capability_binding()
    assert reads == ["read", "read"] and transport.calls == 0
    with repo._connect() as connection:
        assert tuple(connection.iterdump()) == before


@pytest.mark.parametrize("malformed", [None, (), ({},), (*statuses(), statuses()[0]),
    tuple({**row, "status": True} for row in statuses()),
    tuple({**row, "model": {}} for row in statuses())])
def test_missing_partial_or_malformed_status_stays_unknown(tmp_path, malformed):
    _repo, cid, transport, _service, app = workspace(tmp_path, "YT_TIMED", lambda: malformed)
    assert app.handle("GET", "/api/v1/settings")[1]["local_intelligence"]["status"] == "UNKNOWN"
    result = app.handle("GET", f"/api/v1/videos/{cid}")[1]["local_intelligence"]
    assert result["request_state"] == "UNKNOWN" and result["model"] is None
    assert transport.calls == 0


def test_reader_exception_and_current_route_mismatch_do_not_claim_availability(tmp_path):
    def broken():
        raise RuntimeError("private error is not a public status")
    _repo, cid, transport, _service, app = workspace(tmp_path, "YT_TIMED", broken)
    assert app.handle("GET", f"/api/v1/videos/{cid}")[1]["local_intelligence"]["request_state"] == "UNKNOWN"
    app._local_distillation_capabilities = lambda: tuple({**row, "status": "QUALIFIED"} for row in statuses())
    value = app.handle("GET", f"/api/v1/videos/{cid}")[1]["local_intelligence"]
    assert value["qualification_status"] == "QUALIFIED"
    assert value["reason"] == "ROUTE_REINITIALIZATION_REQUIRED" and value["request_state"] == "WAITING_MODEL"
    assert transport.calls == 0


def test_service_binding_is_a_detached_read_without_transport_work(tmp_path):
    _repo, _cid, transport, service, _app = workspace(tmp_path, "YT_TIMED", statuses)
    binding = service.capability_binding()
    expected = dict(binding)
    binding["model"] = "changed presentation"
    assert service.capability_binding() == expected and transport.calls == 0


@pytest.mark.parametrize("language", ["en", "zh-CN", "fr", None])
def test_content_uses_actual_execution_language_not_settings(tmp_path, language):
    _repo, cid, transport, service, app = workspace(tmp_path, "YT_TIMED", statuses)
    app.handle("PUT", "/api/v1/settings/output-language", b'{"output_language":"zh-CN"}')
    service._output_language_for_video = lambda _: language
    value = app.handle("GET", f"/api/v1/videos/{cid}")[1]["local_intelligence"]
    assert value["output_language"] == (language if language in {"en", "zh-CN"} else None)
    assert value["request_state"] == ("WAITING_MODEL" if language in {"en", "zh-CN"} else "UNKNOWN")
    assert transport.calls == 0


def test_execution_language_exception_is_unknown_without_private_error(tmp_path):
    _repo, cid, transport, service, app = workspace(tmp_path, "YT_TIMED", statuses)
    def broken(_):
        raise RuntimeError("not a public error")
    service._output_language_for_video = broken
    value = app.handle("GET", f"/api/v1/videos/{cid}")[1]["local_intelligence"]
    assert value["output_language"] is None and value["request_state"] == "UNKNOWN"
    assert "not a public error" not in json.dumps(value) and transport.calls == 0


@pytest.mark.parametrize("available,state,reason", [
    (True, "ELIGIBLE_FOR_ADMISSION", "ADMISSION_CHECKS_REQUIRED"),
    (False, "WAITING_MODEL", "MODEL_UNAVAILABLE"),
    (None, "UNKNOWN", "RESOURCE_STATUS_UNKNOWN"),
])
def test_qualified_matching_route_still_reports_resource_and_admission_boundary(tmp_path, available, state, reason):
    _repo, cid, transport, service, app = workspace(tmp_path, "YT_TIMED", lambda: tuple({**row, "status": "QUALIFIED"} for row in statuses()))
    service._selected_provider, service._selected_model, service._local_profile_id = "ollama", MODEL, PROFILE
    app._local_distillation_available = available
    value = app.handle("GET", f"/api/v1/videos/{cid}")[1]["local_intelligence"]
    assert value["request_state"] == state and value["reason"] == reason
    assert transport.calls == 0


def test_production_composition_injects_reviewed_reader_without_model_io(tmp_path):
    from youtube_intel.config import load_app_config
    from youtube_intel.runtime import RuntimeDependencies
    from youtube_intel.runtime_composition import build_local_source_run_runtime
    fixtures = _load_module("test_runtime_composition")
    project = fixtures._project(tmp_path)
    dependencies = RuntimeDependencies(
        discovery_source=fixtures._DiscoverySource(), metadata_provider=fixtures._MetadataProvider(),
        subtitle_adapter_factory=fixtures._TimedSubtitleAdapter,
        scoring_provider_factory=fixtures._ScoringProvider,
        analysis_provider_factory=fixtures._SummaryProvider,
        quality_judge_provider_factory=fixtures._QualityJudgeProvider,
    )
    runtime = build_local_source_run_runtime(
        config=load_app_config(project / "config/channels.yaml", project / "config/settings.yaml"),
        project_root=project, database=project / "gui.sqlite3", dependencies=dependencies,
        now=lambda: fixtures.NOW,
    )
    result = runtime.application.handle("GET", "/api/v1/settings")[1]["local_intelligence"]
    assert result["status"] == "KNOWN" and len(result["scopes"]) == 6
    assert all(row["status"] == "NOT_QUALIFIED" for row in result["scopes"])
    assert result["model"] == MODEL
    with runtime.repository._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM provider_calls").fetchone()[0] == 0
