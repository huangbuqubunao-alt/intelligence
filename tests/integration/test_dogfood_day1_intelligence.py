"""Content success and optional analysis have independent trusted authority."""
import json
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.distillation import DistillationExecutionStatus
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.processing_orchestrator import PersistedSourceRunDiscovery


def completed_content(tmp_path: Path, *, available: bool = True):
    support = _load_module("test_task024_processing_orchestration")
    repo = support._repository(tmp_path)
    source_id = support._source(repo)
    video_id, _ = support._video_with_evidence(repo, source_id)
    service = ProductOrchestrationService(repo, now=lambda: support.NOW)
    service.update_source(source_id, processing_policy=ProcessingPolicy.DISCOVER_ONLY, enabled=False)
    ExtractiveSummaryService(repo, tmp_path / "data").create(video_id, now=support.NOW)
    class CompleteNoNewTransport(support._NoNewTransport):
        def generate(self, command):
            result = super().generate(command)
            evidence = []
            for evidence_id in command.evidence_ids:
                item = repo.get_evidence(evidence_id)
                evidence.append({"evidence_id": evidence_id, "start_ms": item.start_ms, "end_ms": item.end_ms})
            return replace(result, raw=json.dumps({"result": "NO_NEW_INTELLIGENCE", "evidence": evidence}))
    transport = CompleteNoNewTransport(available=available)
    distillation = support._orchestrator(repo, transport)._distillation
    app = LocalApiApplication(repo, service, data_root=tmp_path / "data", distillation_service=distillation, now=lambda: support.NOW)
    return repo, source_id, video_id, transport, distillation, app


@pytest.mark.parametrize("available", [True, False])
def test_manual_completed_content_without_forged_relevance_and_even_when_paused(tmp_path, available):
    repo, source_id, video_id, transport, service, app = completed_content(tmp_path, available=available)
    assert repo.current_filter_decision(source_id, video_id) is None
    before = repo.current_local_summary_pointer(video_id)
    detail = app.handle("GET", f"/api/v1/videos/{video_id}")[1]
    assert detail["manual_intelligence_eligible"] is True
    command = json.dumps({"command_id": "manual-day1"}).encode()
    status, result = app.handle("POST", f"/api/v1/videos/{video_id}/intelligence", command)
    assert status == 202
    expected = "SUCCEEDED_NO_NEW_INTELLIGENCE" if available else "WAITING_MODEL"
    assert result["execution"]["status"] == expected
    assert transport.calls == (1 if available else 0)
    assert repo.current_filter_decision(source_id, video_id) is None
    assert repo.current_local_summary_pointer(video_id) == before
    assert repo.list_topics() == ()
    assert repo.list_distillation_cards() == ()
    activity = app.handle("GET", "/api/v1/intelligence")[1]["activity"]
    assert activity[0]["status"] == expected
    assert activity[0]["video_id"] == video_id
    again = app.handle("POST", f"/api/v1/videos/{video_id}/intelligence", command)[1]
    assert again == result
    assert transport.calls == (1 if available else 0)


def test_content_only_never_enters_intelligence_discovery(tmp_path):
    repo, source_id, video_id, transport, service, app = completed_content(tmp_path)
    assert PersistedSourceRunDiscovery(repo).discover(source_id) == ()
    assert transport.calls == 0
    assert repo.latest_distillation_execution_for_video(video_id) is None


def test_manual_intent_is_sealed_and_normal_reservation_still_requires_relevance(tmp_path):
    repo, source_id, video_id, transport, service, app = completed_content(tmp_path)
    evidence = repo.list_canonical_coverage_evidence_ids(video_id)
    with pytest.raises(ValueError, match="not eligible"):
        service.reserve_distillation_execution(source_id=source_id, video_id=video_id, evidence_ids=evidence)
    reservation = service.reserve_distillation_execution(source_id=source_id, video_id=video_id, evidence_ids=evidence, manual_command_id="explicit-user-action")
    record = repo.get_distillation_execution(reservation.execution_id)
    assert record.reason == "MANUAL_CONTENT:explicit-user-action"
    assert transport.calls == 0
    assert service.continue_reserved_distillation(reservation.execution_id).status is DistillationExecutionStatus.SUCCEEDED_NO_NEW_INTELLIGENCE

@pytest.mark.parametrize('policy', [ProcessingPolicy.DISCOVER_ONLY, ProcessingPolicy.STANDARD_INTELLIGENCE])
def test_optional_automatic_analysis_never_blocks_real_content(tmp_path, monkeypatch, policy):
    youtube = _load_module('test_youtube_following')
    support = _load_module('test_task024_processing_orchestration')
    from youtube_intel.runtime_composition import (
        RuntimeSourceRunIngestion,
        RuntimeSourceRunPreparation,
    )
    from youtube_intel.state import DistillationStyle
    repo, tracker, fixture, runtime = youtube.youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(youtube.CHANNEL, provider='YOUTUBE')
    product = ProductOrchestrationService(repo, now=lambda: fixture.now)
    product.update_source(source.source_id, processing_policy=policy)
    transport = support._Transport(available=False)
    orchestrator = support._orchestrator(repo, transport)
    orchestrator._now = lambda: fixture.now
    orchestrator._source_policy.update_global(command_id='optional-policy', initial_history_count=5, per_run_max_new_videos=5, focus_rules=('Sentence1',), ignore_rules=(), distillation_style=DistillationStyle.BALANCED)
    orchestrator._ingestion = RuntimeSourceRunIngestion(runtime, orchestrator._source_policy, tracker)
    orchestrator._preparation = RuntimeSourceRunPreparation(runtime)
    assert repo.list_videos() == ()
    fixture.publish(youtube.NEW)
    run = orchestrator.enqueue_manual_check_now(source_id=source.source_id, command_id='optional-check')
    orchestrator.resume(run.run_id)
    assert [video.video_id for video in repo.list_videos()] == [youtube.NEW]
    pointer = repo.current_local_summary_pointer(youtube.NEW)
    assert pointer is not None
    ExtractiveSummaryService(repo, runtime._data_root).read(youtube.NEW, pointer.artifact_id)
    assert repo.list_canonical_coverage_evidence_ids(youtube.NEW)
    execution = repo.latest_distillation_execution_for_video(youtube.NEW)
    if policy is ProcessingPolicy.DISCOVER_ONLY:
        assert execution is None
    else:
        assert execution is not None and execution.status == 'WAITING_MODEL'
    assert transport.calls == 0
    assert repo.list_distillation_cards() == ()
    assert repo.list_topics() == ()


@pytest.mark.parametrize("retryable", [True, False])
@pytest.mark.parametrize("recovered_elsewhere", [True, False])
@pytest.mark.parametrize("metadata_finished_later", [True, False])
def test_one_time_content_failure_is_visible_and_explicit_retry_recovers(tmp_path, monkeypatch, retryable, recovered_elsewhere, metadata_finished_later):
    from youtube_intel.config import load_app_config
    from youtube_intel.domain import AppError, ErrorCode
    from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
    from youtube_intel.runtime_composition import RuntimeSourceRunIngestion
    from youtube_intel.source_run import SourceRunState
    from youtube_intel.transcripts import TranscriptError

    support = _load_module("test_runtime_composition")
    pipeline = _load_module("test_task024_processing_orchestration")
    current = support.NOW
    monkeypatch.setattr("youtube_intel.runtime._utcnow", lambda: current)
    class Failed(support._TimedSubtitleAdapter):
        def enumerate_tracks(self, video_id):
            raise TranscriptError(AppError(code=ErrorCode.TRANSIENT_NETWORK, message="controlled timeout", retryable=retryable))
    def denied():
        raise AssertionError("Content-only work must never construct a model provider")
    project = support._project(tmp_path)
    runtime = RuntimeOperations(
        config=load_app_config(project / "config/channels.yaml", project / "config/settings.yaml"),
        project_root=project,
        dependencies=RuntimeDependencies(discovery_source=support._DiscoverySource(), metadata_provider=support._MetadataProvider(), subtitle_adapter_factory=Failed, scoring_provider_factory=denied, analysis_provider_factory=denied, quality_judge_provider_factory=denied),
    )
    repo = runtime._repository
    if metadata_finished_later:
        from youtube_intel.domain import ProcessingStage

        latest = repo.latest_video_job
        def reordered_latest(video_id, *, target_stage=None):
            # Both rows are actual pipeline records; vary only which completion
            # timestamp wins the generic latest read, as in the real import.
            if target_stage is None:
                metadata = latest(video_id, target_stage=ProcessingStage.METADATA)
                if metadata is not None and metadata.status.value == "SUCCEEDED":
                    return metadata
            return latest(video_id, target_stage=target_stage)
        monkeypatch.setattr(repo, "latest_video_job", reordered_latest)
    orchestrator = pipeline._orchestrator(repo, pipeline._Transport(available=False))
    orchestrator._now = lambda: current
    orchestrator._ingestion = RuntimeSourceRunIngestion(runtime, orchestrator._source_policy)
    product = ProductOrchestrationService(repo, source_run_submitter=orchestrator, now=lambda: current)
    source = product.add_source(url=f"https://youtube.com/watch?v={support.VIDEO_ID}", processing_policy=ProcessingPolicy.DISCOVER_ONLY)
    run = product.check_source(source.source_id, command_id="failed-content").source_run
    assert orchestrator.resume(run.run_id).state is SourceRunState.NEEDS_ATTENTION
    job = repo.latest_content_job(support.VIDEO_ID)
    assert job.status.value == ("RETRY_PENDING" if retryable else "FAILED_FINAL")
    app = LocalApiApplication(repo, product, data_root=runtime._data_root)
    detail = app.handle("GET", f"/api/v1/videos/{support.VIDEO_ID}")[1]
    assert detail["video"]["processing_status"] == ("RETRY_REQUIRED" if retryable else "FAILED")
    assert detail["video"]["source_id"] == source.source_id
    from datetime import timedelta
    current = job.available_at + timedelta(seconds=1)
    if recovered_elsewhere and retryable:
        # Recovery for another video activates all due caption jobs. A one-off
        # import has no Following scheduler to execute its now-PENDING job.
        assert repo.activate_retry_jobs(now=current)
        app = LocalApiApplication(repo, product, data_root=runtime._data_root)
        recovered = app.handle("GET", f"/api/v1/videos/{support.VIDEO_ID}")[1]
        assert recovered["video"]["processing_job"]["status"] == "PENDING"
        assert recovered["video"]["processing_status"] == "RETRY_REQUIRED"
        assert recovered["video"]["retry_allowed"] is True
    runtime._dependencies = replace(runtime._dependencies, subtitle_adapter_factory=support._TimedSubtitleAdapter)
    status, accepted = app.handle("POST", f"/api/v1/sources/{source.source_id}/check", b'{"command_id":"retry-content"}')
    assert status == 202
    assert app.handle("GET", f"/api/v1/videos/{support.VIDEO_ID}")[1]["video"]["processing_status"] == "WAITING"
    assert orchestrator.resume(accepted["source_run"]["run_id"]).state is SourceRunState.COMPLETED
    pointer = repo.current_local_summary_pointer(support.VIDEO_ID)
    assert pointer is not None
    ExtractiveSummaryService(repo, runtime._data_root).read(support.VIDEO_ID, pointer.artifact_id)
    assert repo.latest_distillation_execution_for_video(support.VIDEO_ID) is None
    assert repo.list_topics() == ()


def test_tracked_missing_summary_cannot_enter_legacy_full_pipeline(tmp_path, monkeypatch):
    youtube = _load_module("test_youtube_following")
    from youtube_intel.runtime_composition import RuntimeSourceRunPreparation
    repo, tracker, fixture, runtime = youtube.youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(youtube.CHANNEL, provider="YOUTUBE")
    fixture.publish(youtube.NEW)
    assert tracker.check(source.source_id) == "COMPLETE"
    monkeypatch.setattr(repo, "current_local_summary_pointer", lambda video_id: None)
    monkeypatch.setattr(runtime, "process", lambda **kwargs: pytest.fail("Optional analysis cannot replace Content preparation"))
    assert RuntimeSourceRunPreparation(runtime).prepare(youtube.NEW) is False


def test_optional_intelligence_waits_for_organized_content_before_relevance(tmp_path, monkeypatch):
    youtube = _load_module("test_youtube_following")
    support = _load_module("test_task024_processing_orchestration")
    from youtube_intel.runtime_composition import (
        RuntimeSourceRunIngestion,
        RuntimeSourceRunPreparation,
    )
    from youtube_intel.state import DistillationStyle
    repo, tracker, fixture, runtime = youtube.youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(youtube.CHANNEL, provider="YOUTUBE")
    product = ProductOrchestrationService(repo, now=lambda: fixture.now)
    product.update_source(source.source_id, processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE)
    transport = support._Transport(available=False)
    orchestrator = support._orchestrator(repo, transport)
    orchestrator._now = lambda: fixture.now
    orchestrator._source_policy.update_global(command_id="caption-wait-policy", initial_history_count=5, per_run_max_new_videos=5, focus_rules=("Sentence1",), ignore_rules=(), distillation_style=DistillationStyle.BALANCED)
    orchestrator._ingestion = RuntimeSourceRunIngestion(runtime, orchestrator._source_policy, tracker)
    orchestrator._preparation = RuntimeSourceRunPreparation(runtime)
    fixture.caption = False
    fixture.publish(youtube.NEW)
    run = orchestrator.enqueue_manual_check_now(source_id=source.source_id, command_id="caption-wait-check")
    orchestrator.resume(run.run_id)
    assert repo.get_video(youtube.NEW) is not None
    assert repo.current_local_summary_pointer(youtube.NEW) is None
    assert repo.current_filter_decision(source.source_id, youtube.NEW) is None
    assert repo.latest_distillation_execution_for_video(youtube.NEW) is None
    assert transport.calls == 0
    app = LocalApiApplication(repo, product, data_root=runtime._data_root)
    activity = app.handle("GET", "/api/v1/intelligence")[1]["activity"]
    assert activity == [{"video_id": youtube.NEW, "title": repo.get_video(youtube.NEW).title, "status": "WAITING_CONTENT"}]
    assert repo.list_topics() == ()


def test_production_manual_content_uses_output_preference_without_scoring(tmp_path, monkeypatch):
    from youtube_intel.config import load_app_config
    from youtube_intel.runtime import RuntimeDependencies
    from youtube_intel.runtime_composition import build_local_source_run_runtime
    support = _load_module("test_runtime_composition")
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    class NoCredentials:
        def get(self): return None
        def save(self, value): pytest.fail("No credential writes")
        def delete(self): pytest.fail("No credential writes")
    def denied():
        pytest.fail("Organized Content must not invent Scoring or invoke its providers")
    from youtube_intel.local_distillation_profile import (
        CURRENT_RUNTIME_PROFILE_ID,
        resolve_profile,
    )
    candidate = resolve_profile(CURRENT_RUNTIME_PROFILE_ID)
    # This single fixture requires a configured unqualified route; old 8b now
    # correctly requests Settings before a task exists. No provider is called.
    project = support._project(tmp_path, model=candidate.model, digest=candidate.model_digest)
    runtime = build_local_source_run_runtime(
        config=load_app_config(project / "config/channels.yaml", project / "config/settings.yaml"),
        project_root=project, database=project / "state.sqlite3", credential_store=NoCredentials(),
        dependencies=RuntimeDependencies(discovery_source=support._DiscoverySource(), metadata_provider=support._MetadataProvider(), subtitle_adapter_factory=support._TimedSubtitleAdapter, scoring_provider_factory=denied, analysis_provider_factory=denied, quality_judge_provider_factory=denied),
    )
    source = runtime.product.add_source(url=f"https://youtu.be/{support.VIDEO_ID}", processing_policy=ProcessingPolicy.DISCOVER_ONLY)
    run = runtime.product.check_source(source.source_id, command_id="organize-first").source_run
    runtime.orchestrator.resume(run.run_id)
    assert runtime.repository.current_local_summary_pointer(support.VIDEO_ID) is not None
    runtime.application.handle("PUT", "/api/v1/settings/output-language", b'{"output_language":"zh-CN"}')
    status, result = runtime.application.handle("POST", f"/api/v1/videos/{support.VIDEO_ID}/intelligence", b'{"command_id":"production-manual"}')
    assert status == 202
    assert result["execution"]["status"] == "WAITING_MODEL"
    execution = runtime.repository.get_distillation_execution(result["execution"]["execution_id"])
    assert execution.invocation_count == 0
    assert execution.output_language == "zh-CN"
    assert runtime.repository.current_filter_decision(source.source_id, support.VIDEO_ID) is None
    assert runtime.repository.get_video(support.VIDEO_ID).authoritative_scoring_job_id is None
    assert runtime.repository.list_topics() == ()


def test_corrupt_summary_remains_real_content_and_needs_attention(tmp_path):
    repo, source_id, video_id, transport, service, app = completed_content(tmp_path)
    pointer = repo.current_local_summary_pointer(video_id)
    artifact = repo.get_artifact(pointer.artifact_id)
    (tmp_path / "data" / artifact.relative_path).write_text("controlled damaged summary")
    detail = app.handle("GET", f"/api/v1/videos/{video_id}")[1]
    assert detail["video"]["processing_status"] == "NEEDS_ATTENTION"
    assert detail["note"]["v2"]["status"] == "UNAVAILABLE"
    assert detail["manual_intelligence_eligible"] is False
    assert repo.get_video(video_id) is not None
    assert transport.calls == 0


@pytest.mark.parametrize("code", ["TRUST_INTEGRITY_INVALID", "CAPABILITY_UNAVAILABLE"])
def test_content_retry_cannot_bypass_non_retryable_terminals(tmp_path, monkeypatch, code):
    from datetime import timedelta

    from youtube_intel.config import load_app_config
    from youtube_intel.domain import AppError, ErrorCode
    from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
    from youtube_intel.runtime_composition import RuntimeSourceRunIngestion
    from youtube_intel.source_run import SourceRunState
    from youtube_intel.transcripts import TranscriptError

    support = _load_module("test_runtime_composition")
    pipeline = _load_module("test_task024_processing_orchestration")
    current = support.NOW
    monkeypatch.setattr("youtube_intel.runtime._utcnow", lambda: current)
    class Failed(support._TimedSubtitleAdapter):
        def enumerate_tracks(self, video_id):
            raise TranscriptError(AppError(code=ErrorCode(code), message="controlled terminal", retryable=False))
    def denied():
        pytest.fail("Non-retryable Content must not contact providers again")
    project = support._project(tmp_path)
    runtime = RuntimeOperations(config=load_app_config(project / "config/channels.yaml", project / "config/settings.yaml"), project_root=project,
        dependencies=RuntimeDependencies(discovery_source=support._DiscoverySource(), metadata_provider=support._MetadataProvider(), subtitle_adapter_factory=Failed, scoring_provider_factory=denied, analysis_provider_factory=denied, quality_judge_provider_factory=denied))
    repo = runtime._repository
    orchestrator = pipeline._orchestrator(repo, pipeline._Transport(available=False))
    orchestrator._now = lambda: current
    orchestrator._ingestion = RuntimeSourceRunIngestion(runtime, orchestrator._source_policy)
    product = ProductOrchestrationService(repo, source_run_submitter=orchestrator, now=lambda: current)
    source = product.add_source(url=f"https://youtu.be/{support.VIDEO_ID}", processing_policy=ProcessingPolicy.DISCOVER_ONLY)
    first = product.check_source(source.source_id, command_id="terminal-first").source_run
    assert orchestrator.resume(first.run_id).state is SourceRunState.NEEDS_ATTENTION
    terminal = repo.latest_video_job(support.VIDEO_ID)
    assert terminal.last_error_code == code and terminal.status.value == "FAILED_FINAL"
    runtime._dependencies = replace(runtime._dependencies, subtitle_adapter_factory=denied)
    current += timedelta(seconds=10)
    second = product.check_source(source.source_id, command_id="terminal-retry").source_run
    assert orchestrator.resume(second.run_id).state is SourceRunState.NEEDS_ATTENTION
    assert repo.latest_video_job(support.VIDEO_ID) == terminal
    assert repo.current_local_summary_pointer(support.VIDEO_ID) is None
    app = LocalApiApplication(repo, product, data_root=runtime._data_root)
    assert app.handle("GET", f"/api/v1/videos/{support.VIDEO_ID}")[1]["video"]["retry_allowed"] is False
