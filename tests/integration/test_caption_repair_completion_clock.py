"""Only caption-repair completion must use its current post-IO clock."""

from datetime import UTC, datetime, timedelta

import pytest
from conftest import _load_module

from youtube_intel import runtime_composition, transcripts
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.state import ArtifactKind

support = _load_module("test_runtime_composition")


@pytest.mark.parametrize("fault", ["short-io", "job-expiry", "provider-expiry", "owner-changed", "backwards", "job-lease-naive", "provider-lease-naive", "commit-expiry", "commit-backwards"])
def test_caption_completion_rechecks_current_clock_and_owned_leases_after_io(tmp_path, monkeypatch, fault):
    prior, adapter, source_id, config, dependencies = support._completed_plain_caption_runtime(tmp_path)
    parent = prior.repository.latest_artifact(support.VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL)
    original_job = prior.repository.latest_video_job(support.VIDEO_ID)
    clock = [datetime.now(UTC)]

    class ControlledDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0].astimezone(tz) if tz is not None else clock[0].replace(tzinfo=None)

    # The existing factory owns a real datetime.now clock independently of the
    # worker's injected clock. Both must observe this one bounded IO experiment.
    monkeypatch.setattr(runtime_composition, "datetime", ControlledDateTime)
    runtime = build_local_source_run_runtime(config=config, project_root=tmp_path,
        database=tmp_path / "gui.sqlite3", dependencies=dependencies, now=lambda: clock[0])
    original_complete = runtime.repository.complete_caption_repair
    original_inject = runtime.repository._inject_failure
    original_read = transcripts._read_verified_file
    entered = []

    def complete(**kwargs):
        entered.append(kwargs["now"])
        if fault in {"owner-changed", "provider-expiry", "job-lease-naive", "provider-lease-naive"}:
            with runtime.repository._connect() as connection:
                if fault == "owner-changed":
                    connection.execute("UPDATE jobs SET lease_owner='another-owner' WHERE job_id=?", (kwargs["job_id"],))
                elif fault == "job-lease-naive":
                    connection.execute("UPDATE jobs SET lease_until=? WHERE job_id=?", ((clock[0] + timedelta(minutes=5)).replace(tzinfo=None).isoformat(), kwargs["job_id"]))
                elif fault == "provider-lease-naive":
                    connection.execute("UPDATE provider_calls SET lease_until=? WHERE request_hash=?", ((clock[0] + timedelta(minutes=5)).replace(tzinfo=None).isoformat(), kwargs["provider_call"].request_hash))
                else:
                    connection.execute("UPDATE provider_calls SET lease_until=? WHERE request_hash=?", (
                        (clock[0] + timedelta(seconds=1)).isoformat(timespec="microseconds").replace("+00:00", "Z"), kwargs["provider_call"].request_hash))
        advanced = False

        def read(*args, **options):
            nonlocal advanced
            result = original_read(*args, **options)
            if not advanced:
                advanced = True
                clock[0] += timedelta(seconds=-1 if fault == "backwards" else 600 if fault == "job-expiry" else 2)
            return result

        with monkeypatch.context() as scoped:
            scoped.setattr(transcripts, "_read_verified_file", read)
            return original_complete(**kwargs)

    monkeypatch.setattr(runtime.repository, "complete_caption_repair", complete)

    def final_boundary(point):
        if point == "caption_repair.after_authority" and fault in {"commit-expiry", "commit-backwards"}:
            clock[0] += timedelta(seconds=600 if fault == "commit-expiry" else -1)
        original_inject(point)

    monkeypatch.setattr(runtime.repository, "_inject_failure", final_boundary)
    runtime.application.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"completion-clock-case"}')
    runtime.worker.run_once()
    assert entered
    timed = runtime.repository.get_verified_timed_transcript(video_id=support.VIDEO_ID)
    if fault == "short-io":
        assert timed is not None
        job = runtime.repository.latest_video_job(support.VIDEO_ID)
        assert job.status.value == "SUCCEEDED" and job.finished_at == clock[0] > entered[0]
        with runtime.repository._connect() as connection:
            call = connection.execute("SELECT p.* FROM provider_calls p JOIN artifacts a ON p.response_artifact_id=a.artifact_id WHERE a.job_id=?", (job.job_id,)).fetchone()
            assert datetime.fromisoformat(call["finished_at"]) == clock[0]
    else:
        assert timed is None and not runtime.repository.list_canonical_coverage_evidence_ids(support.VIDEO_ID)
        assert runtime.repository.latest_artifact(support.VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL) == parent
        with runtime.repository._connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM artifacts WHERE job_id LIKE 'caption-repair-%' AND artifact_key NOT LIKE 'subtitle-source-capture:%'").fetchone()[0] == 0
        assert not runtime.backup_restore.readiness()["ready"]
    assert runtime.repository.get_job(original_job.job_id) == original_job
    assert adapter.read_calls > 0
