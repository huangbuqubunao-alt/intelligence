"""Phase 13 uses production composition; only external boundaries are controlled."""

import os
import socket
import subprocess
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.config import load_app_config
from youtube_intel.following_tracking import _stamp
from youtube_intel.providers.youtube_channel import canonical_channel
from youtube_intel.runtime import RuntimeDependencies
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.source_run import SourceRunState


def setup_runtime(tmp_path, monkeypatch, fixture=None):
    support = _load_module("test_runtime_composition")
    youtube = _load_module("test_youtube_following")
    fixture = fixture or youtube.YouTubeFixture()
    project = tmp_path if (tmp_path / "config").exists() else support._project(tmp_path)
    config = load_app_config(
        project / "config/channels.yaml", project / "config/settings.yaml"
    )

    def denied():
        raise AssertionError("automatic tracking must never construct a model")

    subtitle = support._TimedSubtitleAdapter()
    original_enumerate = subtitle.enumerate_tracks
    subtitle.enumerate_tracks = lambda video_id: original_enumerate(support.VIDEO_ID)

    monkeypatch.setattr("youtube_intel.runtime._utcnow", lambda: fixture.now)
    monkeypatch.setattr(
        "youtube_intel.providers.youtube_channel.public_operation",
        lambda operation: operation(),
    )
    composition = build_local_source_run_runtime(
        config=config, project_root=project, database=project / "state.sqlite",
        dependencies=RuntimeDependencies(
            discovery_source=support._DiscoverySource(), metadata_provider=fixture,
            subtitle_adapter_factory=lambda: subtitle, scoring_provider_factory=denied,
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


@pytest.mark.parametrize("failure,minimum", [
    ("NETWORK_UNAVAILABLE", 60), ("RATE_LIMITED", 900),
    ("METADATA_FAILED", 3600), ("RESPONSE_TOO_LARGE", 3600), ("NOT_FOUND", 3600),
])
def test_automatic_failures_back_off_without_fabricating_frontier(
    tmp_path, monkeypatch, failure, minimum
):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    tracker = composition.application._source_tracking
    before = tracker.projection(source.source_id)
    fixture.now += timedelta(minutes=16)
    fixture.failure = failure
    run = composition.worker.run_once()
    assert run.state is SourceRunState.FAILED
    after = tracker.projection(source.source_id)
    assert after["verified_at"] == before["verified_at"]
    assert after["latest_published_at"] == before["latest_published_at"]
    assert (_stamp(after["next_check_at"]) - fixture.now).total_seconds() >= minimum
    assert after["checking"] is False
    assert composition.worker.run_once() is None


def test_network_backoff_grows_and_recovery_needs_no_restart(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    tracker = composition.application._source_tracking
    fixture.now += timedelta(minutes=16)
    fixture.failure = "NETWORK_UNAVAILABLE"
    assert composition.worker.run_once().state is SourceRunState.FAILED
    first_due = _stamp(tracker.projection(source.source_id)["next_check_at"])
    fixture.now = first_due
    assert composition.worker.run_once().state is SourceRunState.FAILED
    second_due = _stamp(tracker.projection(source.source_id)["next_check_at"])
    assert second_due - fixture.now >= timedelta(minutes=2)
    fixture.now = second_due
    fixture.failure = None
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert tracker.projection(source.source_id)["health"] == "HEALTHY"
    assert _stamp(tracker.projection(source.source_id)["next_check_at"]) - fixture.now == timedelta(minutes=15)


def test_transient_not_found_recovers_on_later_automatic_check(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    fixture.failure = "NOT_FOUND"
    assert composition.worker.run_once().state is SourceRunState.FAILED
    tracker = composition.application._source_tracking
    state = tracker.projection(source.source_id)
    fixture.now = _stamp(state["next_check_at"])
    fixture.failure = None
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert tracker.projection(source.source_id)["health"] == "HEALTHY"


@pytest.mark.parametrize("failure", ["RISK_CONTROLLED", "SOURCE_UNTRUSTED", "ACCESS_DENIED"])
def test_lifecycle_refresh_cannot_bypass_automatic_refusal(tmp_path, monkeypatch, failure):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    fixture.failure = failure
    assert composition.worker.run_once().state is SourceRunState.FAILED
    fixture.now += timedelta(days=2)
    before = composition.repository.list_source_runs()
    assert composition.application.handle("POST", "/api/v1/sources/check-stale", b'{}')[0] == 202
    assert composition.repository.list_source_runs() == before
    assert composition.application._source_tracking.check(source.source_id, automatic=True) in {"STATE_INVALID", "RISK_CONTROLLED", "ACCESS_DENIED"}
    assert len(fixture.calls) == 2


def test_manual_retry_after_five_seconds_bypasses_only_network_backoff(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    fixture.failure = "NETWORK_UNAVAILABLE"
    assert composition.worker.run_once().state is SourceRunState.FAILED
    fixture.now += timedelta(seconds=5)
    fixture.failure = None
    status, payload = composition.application.handle(
        "POST", f"/api/v1/sources/{source.source_id}/check",
        b'{"command_id":"explicit-network-retry"}',
    )
    assert status == 202
    assert composition.worker.run_once().run_id == payload["source_run"]["run_id"]
    assert composition.application._source_tracking.projection(source.source_id)["health"] == "HEALTHY"


def test_protected_backup_window_does_not_admit_automatic_work(tmp_path, monkeypatch):
    composition, fixture, _ = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    with composition.backup_restore._protect_background():
        assert composition.worker.run_once() is None
        assert len(fixture.calls) == 1
        assert composition.repository.list_source_runs() == ()
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert composition.backup_restore.readiness()["ready"] is True


def test_idle_schedule_read_does_not_make_backup_unavailable(tmp_path, monkeypatch):
    composition, _, _ = setup_runtime(tmp_path, monkeypatch)
    entered, release = threading.Event(), threading.Event()
    scheduler = composition.worker.scheduler
    eligible = scheduler._eligible

    def slow_read():
        entered.set()
        assert release.wait(5)
        return eligible()

    monkeypatch.setattr(scheduler, "_eligible", slow_read)
    results = []
    thread = threading.Thread(target=lambda: results.append(composition.worker.run_once()))
    thread.start()
    try:
        assert entered.wait(5)
        assert composition.backup_restore.readiness()["ready"] is True
        assert composition.backup_restore.create_backup().backup_id
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive() and results == [None]


def test_manual_and_background_admission_reuse_one_run(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    scheduler = composition.worker.scheduler
    scheduler.admit_due()
    manual = composition.product.check_source(source.source_id, command_id="manual-race")
    runs = composition.repository.list_source_runs()
    assert len(runs) == 1 and manual.source_run.run_id == runs[0].run_id
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert len(fixture.calls) == 2


def test_overlapping_worker_ticks_and_backup_are_bounded(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    entered, release = threading.Event(), threading.Event()
    tracker = composition.application._source_tracking

    def blocked(channel):
        entered.set()
        assert release.wait(5)
        return fixture.feed(channel)

    tracker.providers["YOUTUBE"]._fetch = blocked
    results = []
    thread = threading.Thread(target=lambda: results.append(composition.worker.run_once()))
    thread.start()
    try:
        assert entered.wait(5)
        assert composition.worker.run_once() is None
        assert tracker.projection(source.source_id)["checking"] is True
        assert composition.backup_restore.readiness()["ready"] is False
        assert len(composition.repository.list_source_runs()) == 1
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert results[0].state is SourceRunState.COMPLETED
    assert composition.backup_restore.readiness()["ready"] is True


def test_restart_preserves_next_check_and_paused_state(tmp_path, monkeypatch):
    first, fixture, source = setup_runtime(tmp_path, monkeypatch)
    before = first.application._source_tracking.projection(source.source_id)
    second, fixture, source = setup_runtime(tmp_path, monkeypatch, fixture)
    assert second.worker.run_once() is None
    assert second.application._source_tracking.projection(source.source_id) == before
    first.product.update_source(source.source_id, enabled=False)
    third, fixture, source = setup_runtime(tmp_path, monkeypatch, fixture)
    fixture.now += timedelta(minutes=16)
    assert third.worker.run_once() is None
    assert third.repository.get_source_subscription(source.source_id).enabled is False
    third.product.update_source(source.source_id, enabled=True)
    assert third.worker.run_once().state is SourceRunState.COMPLETED
    assert len(fixture.calls) == 2


def test_background_enrollment_is_once_and_has_no_model_work(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    youtube = _load_module("test_youtube_following")
    assert composition.repository.list_videos() == ()
    fixture.tick()
    fixture.publish(youtube.NEW)
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert len(composition.repository.list_videos()) == 1
    assert composition.repository.get_verified_timed_transcript(video_id=youtube.NEW) is not None
    assert composition.repository.current_local_summary_pointer(youtube.NEW) is not None
    fixture.tick()
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert len(composition.repository.list_videos()) == 1
    with composition.repository._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM distillation_execution_checkpoints").fetchone()[0] == 0
    assert composition.application._source_tracking.projection(source.source_id)["update_count"] == 1


def test_idle_wait_is_a_deadline_and_paused_sources_have_no_wakeup(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    assert composition.worker.scheduler.wait_seconds() == 300
    composition.product.update_source(source.source_id, enabled=False)
    assert composition.worker.scheduler.wait_seconds() is None
    assert composition.worker.run_once() is None


def test_restored_authority_replaces_all_pre_restore_scheduling(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    composition.product.update_source(source.source_id, enabled=False)
    backup = composition.backup_restore.create_backup()
    saved = composition.application._source_tracking.projection(source.source_id)
    composition.product.update_source(source.source_id, enabled=True)
    fixture.now += timedelta(minutes=16)
    archive = composition.backup_restore.backup_download(backup.backup_id)[0].read_bytes()
    staged = composition.backup_restore.stage_restore(archive)
    composition.backup_restore.confirm_restore(staged.restore_id)
    assert composition.worker.run_once() is None
    assert composition.repository.list_source_runs() == ()
    composition.worker.stop()
    restored, fixture, source = setup_runtime(tmp_path, monkeypatch, fixture)
    assert restored.worker.run_once() is None
    assert restored.repository.get_source_subscription(source.source_id).enabled is False
    assert restored.application._source_tracking.projection(source.source_id) == saved
    assert restored.backup_restore.readiness()["ready"] is True


def test_busy_provider_defers_automatic_work_instead_of_hot_looping(tmp_path, monkeypatch):
    from youtube_intel.following_tracking import _CHECK_SLOTS

    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    slot = _CHECK_SLOTS["YOUTUBE"]
    assert slot.acquire(blocking=False)
    try:
        assert composition.worker.run_once().state is SourceRunState.FAILED
    finally:
        slot.release()
    due = _stamp(composition.application._source_tracking.projection(source.source_id)["next_check_at"])
    assert due - fixture.now >= timedelta(minutes=1)
    assert composition.worker.run_once() is None
    fixture.now = due
    assert composition.worker.run_once().state is SourceRunState.COMPLETED


def test_scheduler_startup_recovers_only_the_existing_interrupted_run(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    composition.worker.scheduler.admit_due()
    run = composition.repository.list_source_runs()[0]
    composition.repository.transition_source_run(run.run_id, to_state=SourceRunState.RUNNING, now=fixture.now)
    restarted, fixture, _ = setup_runtime(tmp_path, monkeypatch, fixture)
    result = restarted.worker.run_once()
    assert result.run_id == run.run_id and result.state is SourceRunState.COMPLETED
    assert len(restarted.repository.list_source_runs()) == 1
    assert len(fixture.calls) == 2


def test_restart_expires_stale_check_without_fabricating_success(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    composition.worker.scheduler.admit_due()
    run = composition.repository.list_source_runs()[0]
    composition.repository.transition_source_run(run.run_id, to_state=SourceRunState.RUNNING, now=fixture.now)
    with composition.repository._connect() as connection:
        connection.execute("INSERT INTO source_checks(check_id,source_id,started_at,status) VALUES('crashed-check',?,?,'RUNNING')", (source.source_id, fixture.now.isoformat()))
    before = composition.application._source_tracking.projection(source.source_id)
    fixture.now += timedelta(minutes=11)
    restarted, fixture, _ = setup_runtime(tmp_path, monkeypatch, fixture)
    assert restarted.application._source_tracking.projection(source.source_id)["verified_at"] == before["verified_at"]
    result = restarted.worker.run_once()
    assert result.run_id == run.run_id and result.state is SourceRunState.COMPLETED
    with restarted.repository._connect() as connection:
        assert connection.execute("SELECT status FROM source_checks WHERE check_id='crashed-check'").fetchone()[0] == "INTERRUPTED"
        assert connection.execute("SELECT COUNT(*) FROM source_checks WHERE status='RUNNING'").fetchone()[0] == 0
    assert len(fixture.calls) == 2
    assert restarted.repository.list_videos() == ()


def test_synchronous_tracking_seam_preserves_automatic_backoff(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    composition.product._source_run_submitter = None
    fixture.now += timedelta(minutes=16)
    fixture.failure = "NETWORK_UNAVAILABLE"
    composition.worker.scheduler.admit_due()
    state = composition.application._source_tracking.projection(source.source_id)
    assert state["health"] == "OFFLINE"
    assert _stamp(state["next_check_at"]) - fixture.now >= timedelta(minutes=1)


def test_idle_worker_waits_and_api_resume_wakes_it_then_shutdown_drains(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    composition.product.update_source(source.source_id, enabled=False)
    waiting = threading.Event()
    checked = threading.Event()
    waits = []

    class ObservedEvent(threading.Event):
        def wait(self, timeout=None):
            waits.append(timeout)
            waiting.set()
            return super().wait(timeout)

    composition.worker._wake = ObservedEvent()
    provider = composition.application._source_tracking.providers["YOUTUBE"]
    provider._fetch = lambda channel: (checked.set(), fixture.feed(channel))[1]
    composition.worker.start()
    thread = composition.worker._thread
    try:
        assert waiting.wait(5)
        assert waits == [None]
        assert len(fixture.calls) == 1
        assert composition.application.handle(
            "PATCH", f"/api/v1/sources/{source.source_id}", b'{"enabled":true}'
        )[0] == 200
        assert checked.wait(5)
    finally:
        composition.worker.stop()
    assert not thread.is_alive()
    assert len(fixture.calls) == 2
    assert composition.application._source_tracking.projection(source.source_id)["checking"] is False
    assert composition.backup_restore.readiness()["ready"] is True


def test_many_due_sources_drain_serially_and_startup_does_not_flood(tmp_path, monkeypatch):
    composition, fixture, _ = setup_runtime(tmp_path, monkeypatch)
    tracker = composition.application._source_tracking
    tracker.providers["YOUTUBE"]._resolve = lambda value: canonical_channel(value, fixture.name)
    for letter in "bcd":
        tracker.follow("UC" + letter * 22, provider="YOUTUBE")
    assert len(fixture.calls) == 4
    assert composition.worker.run_once() is None
    assert len(composition.repository.list_source_runs()) == 0
    fixture.now += timedelta(minutes=16)
    for index in range(4):
        assert composition.worker.run_once().state is SourceRunState.COMPLETED
        assert len(fixture.calls) == 5 + index
        assert all(run.state is SourceRunState.COMPLETED for run in composition.repository.list_source_runs())
    assert composition.worker.run_once() is None
    assert len(composition.repository.list_source_runs()) == 4


@pytest.mark.parametrize("failure", ["RISK_CONTROLLED", "SOURCE_UNTRUSTED", "ACCESS_DENIED", "NOT_FOUND"])
def test_failed_sources_stay_bounded_and_security_refusals_stop(tmp_path, monkeypatch, failure):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.failure = failure
    fixture.now += timedelta(minutes=16)
    assert composition.worker.run_once().state is SourceRunState.FAILED
    fixture.now += timedelta(days=2)
    if failure == "NOT_FOUND":
        assert composition.worker.run_once().state is SourceRunState.FAILED
        assert composition.worker.scheduler.wait_seconds() > 0
        assert len(fixture.calls) == 3
        assert composition.worker.run_once() is None
    else:
        assert composition.worker.run_once() is None
        assert composition.worker.scheduler.wait_seconds() is None
        assert len(fixture.calls) == 2
    assert composition.application._source_tracking.projection(source.source_id)["checking"] is False


def test_initial_baseline_failure_later_recovers_without_historical_content(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    # A fresh, separately followed source fails its first bounded baseline.
    tracker = composition.application._source_tracking
    channel = "UC" + "b" * 22
    tracker.providers["YOUTUBE"]._resolve = lambda value: canonical_channel(channel, fixture.name)
    fixture.failure = "NETWORK_UNAVAILABLE"
    new_source = tracker.follow(channel, provider="YOUTUBE")
    assert tracker.projection(new_source.source_id)["baseline_at"] is None
    fixture.now += timedelta(seconds=5)
    assert composition.worker.run_once().state is SourceRunState.FAILED
    fixture.now = _stamp(tracker.projection(new_source.source_id)["next_check_at"])
    fixture.failure = None
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert tracker.projection(new_source.source_id)["baseline_at"] is not None
    assert composition.repository.list_videos() == ()
    assert tracker.projection(source.source_id)["baseline_at"] is not None


def test_withdrawn_bilibili_capability_remains_unavailable(tmp_path, monkeypatch):
    composition, _, _ = setup_runtime(tmp_path, monkeypatch)
    settings = composition.application.handle("GET", "/api/v1/settings")[1]
    assert settings["bilibili"]["creator_following"]["available"] is False
    assert settings["bilibili"]["public_captions"]["available"] is False
    assert settings["bilibili"]["video_ingestion"]["available"] is True


def test_shutdown_waits_for_the_current_bounded_check(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    entered, release, stopped = threading.Event(), threading.Event(), threading.Event()

    def blocked(channel):
        entered.set()
        assert release.wait(5)
        return fixture.feed(channel)

    composition.application._source_tracking.providers["YOUTUBE"]._fetch = blocked
    composition.worker.start()
    worker_thread = composition.worker._thread
    assert entered.wait(5)
    stop_thread = threading.Thread(target=lambda: (composition.worker.stop(), stopped.set()))
    stop_thread.start()
    try:
        assert not stopped.wait(0.02)
    finally:
        release.set()
        stop_thread.join(5)
    assert stopped.is_set() and not worker_thread.is_alive()
    assert composition.application._source_tracking.projection(source.source_id)["checking"] is False
    assert composition.backup_restore.readiness()["ready"] is True


def test_invalid_tracking_authority_cannot_create_an_admission_hot_loop(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    with composition.repository._connect() as connection:
        connection.execute("UPDATE source_subscriptions SET processing_policy='STANDARD_INTELLIGENCE' WHERE source_id=?", (source.source_id,))
    fixture.now += timedelta(minutes=16)
    assert composition.worker.run_once().state is SourceRunState.FAILED
    assert composition.worker.scheduler.wait_seconds() is None
    assert composition.worker.run_once() is None
    assert len(fixture.calls) == 1


def test_local_processing_exception_settles_run_and_schedules_bounded_retry(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)

    def failed(source_id):
        raise RuntimeError("local processing failed")

    monkeypatch.setattr(composition.orchestrator._ingestion, "ingest", failed)
    assert composition.worker.run_once().state is SourceRunState.FAILED
    state = composition.application._source_tracking.projection(source.source_id)
    assert state["health"] == "PROVIDER_ERROR" and state["checking"] is False
    assert _stamp(state["next_check_at"]) - fixture.now >= timedelta(hours=1)
    assert composition.worker.run_once() is None
    assert composition.backup_restore.readiness()["ready"] is True


def test_permanent_network_failure_backoff_is_capped_and_durable(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    tracker = composition.application._source_tracking
    fixture.now += timedelta(minutes=16)
    fixture.failure = "NETWORK_UNAVAILABLE"
    delays = []
    for _ in range(9):
        assert composition.worker.run_once().state is SourceRunState.FAILED
        due = _stamp(tracker.projection(source.source_id)["next_check_at"])
        delays.append((due - fixture.now).total_seconds())
        fixture.now = due
    assert delays == [60, 120, 240, 480, 960, 1920, 3600, 3600, 3600]
    reopened, fixture, _ = setup_runtime(tmp_path, monkeypatch, fixture)
    fixture.now -= timedelta(seconds=1)
    assert reopened.worker.run_once() is None


def test_serve_api_sigterm_drains_active_tracking_before_exit(tmp_path):
    support = _load_module("test_runtime_composition")
    project = support._project(tmp_path)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    script = project / "shutdown_probe.py"
    script.write_text('''
import sys, time
from pathlib import Path
from datetime import UTC, datetime, timedelta
import youtube_intel.runtime_composition as composition
from youtube_intel.providers.youtube_channel import canonical_channel
from youtube_intel.cli import main
original = composition.build_local_source_run_runtime
root = Path(sys.argv[1])
class NoCredentials:
    def get(self): return None
    def set(self, value): raise AssertionError('credentials are not used')
    def delete(self): raise AssertionError('credentials are not used')
def build(**kwargs):
    kwargs['credential_store'] = NoCredentials()
    result = original(**kwargs)
    tracker = result.application._source_tracking
    provider = tracker.providers['YOUTUBE']
    channel = 'UC' + 'a' * 22
    provider._resolve = lambda value: canonical_channel(channel, 'Shutdown channel')
    def feed(channel):
        return ('<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><yt:channelId>' + channel + '</yt:channelId></feed>').encode()
    provider._fetch = feed
    source = tracker.follow(channel, provider='YOUTUBE')
    with result.repository._connect() as connection:
        connection.execute('UPDATE source_tracking_state SET next_check_at=? WHERE source_id=?', ((datetime.now(UTC)-timedelta(seconds=1)).isoformat(), source.source_id))
    def slow(channel):
        (root/'check-started').write_text('active')
        time.sleep(1)
        return feed(channel)
    provider._fetch = slow
    return result
composition.build_local_source_run_runtime = build
raise SystemExit(main(['--project-root',str(root),'serve-api','--database',str(root/'state.sqlite'),'--port',sys.argv[2]]))
''')
    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=str(root / "src"))
    process = subprocess.Popen(
        [sys.executable, str(script), str(project), str(port)], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not (project / "check-started").exists() and time.monotonic() < deadline:
            assert process.poll() is None
            time.sleep(0.01)
        assert (project / "check-started").exists()
        process.terminate()
        output = process.communicate(timeout=10)[0]
        assert process.returncode == 0, output
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
    from youtube_intel.state import SQLiteStateRepository
    repo = SQLiteStateRepository(project / "state.sqlite")
    assert repo.list_source_runs()[0].state is SourceRunState.COMPLETED
    with repo._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM source_checks WHERE status='RUNNING'").fetchone()[0] == 0
