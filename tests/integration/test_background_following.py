"""Phase 13 uses production composition; only external boundaries are controlled."""

from datetime import timedelta

from conftest import _load_module

from youtube_intel.config import load_app_config
from youtube_intel.providers.youtube_channel import canonical_channel
from youtube_intel.runtime import RuntimeDependencies
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.source_run import SourceRunState


def setup_runtime(tmp_path, monkeypatch):
    support = _load_module("test_runtime_composition")
    youtube = _load_module("test_youtube_following")
    fixture = youtube.YouTubeFixture()
    project = support._project(tmp_path)
    config = load_app_config(
        project / "config/channels.yaml", project / "config/settings.yaml"
    )

    def denied():
        raise AssertionError("automatic tracking must never construct a model")

    monkeypatch.setattr("youtube_intel.runtime._utcnow", lambda: fixture.now)
    monkeypatch.setattr(
        "youtube_intel.providers.youtube_channel.public_operation",
        lambda operation: operation(),
    )
    composition = build_local_source_run_runtime(
        config=config, project_root=project, database=project / "state.sqlite",
        dependencies=RuntimeDependencies(
            discovery_source=support._DiscoverySource(), metadata_provider=fixture,
            subtitle_adapter_factory=denied, scoring_provider_factory=denied,
            analysis_provider_factory=denied, quality_judge_provider_factory=denied,
        ),
        now=lambda: fixture.now,
    )
    tracker = composition.application._source_tracking
    tracker.providers["YOUTUBE"]._fetch = fixture.feed
    tracker.providers["YOUTUBE"]._resolve = lambda value: canonical_channel(youtube.CHANNEL, fixture.name)
    source = tracker.follow(youtube.CHANNEL, provider="YOUTUBE")
    return composition, fixture, source


def test_due_following_is_checked_without_a_ui_event(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    run = composition.worker.run_once()
    assert run is not None and run.state is SourceRunState.COMPLETED
    assert run.source_id == source.source_id
    assert len(fixture.calls) == 2  # baseline, then one automatic check
    assert composition.repository.get_source_subscription(source.source_id).last_success_at == fixture.now
    assert composition.repository.list_videos() == ()


def test_not_due_source_is_not_checked(tmp_path, monkeypatch):
    composition, fixture, _ = setup_runtime(tmp_path, monkeypatch)
    assert composition.worker.run_once() is None
    assert len(fixture.calls) == 1


def test_pause_and_resume_reenter_durable_scheduling(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    composition.product.update_source(source.source_id, enabled=False)
    assert composition.worker.run_once() is None
    assert len(fixture.calls) == 1
    composition.product.update_source(source.source_id, enabled=True)
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert len(fixture.calls) == 2
