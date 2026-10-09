"""Real AppKit-selected 2 GiB native clone, independence, fallback and ZIP64 proof.

The first selection uses the real OS dialog (complete through native UI tooling).
Later dedupe/boundary/fallback cases explicitly use a test-only picker seam.
No file body crosses HTTP on the native import route. No model is called.
"""

import http.client
import json
import struct
import subprocess
import tempfile
import time
import tracemalloc
from pathlib import Path

from dogfood_day2_large_media import get, measure, post, workspace

from youtube_intel import source_authority
from youtube_intel.local_content import LocalContentProvider, MediaTranscript
from youtube_intel.native_picker_build import prepare_native_picker
from youtube_intel.source_authority import MAX_MEDIA_BYTES, hash_managed
from youtube_intel.state import TimedTranscriptCueWrite

ORIGIN = "http://127.0.0.1:5598"
REPORT = Path("docs/validation/dogfood-day2-d2-02/actual-native-media.json")


def control(server, route):
    client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=30)
    client.request("POST", "/api/v1/local/native/" + route, "{}", headers={"Origin": ORIGIN, "X-YIA-Request": "local-ui", "Sec-Fetch-Site": "same-origin"})
    response = client.getresponse()
    assert response.status in {200, 202}, response.read()
    body = json.loads(response.read())
    client.close()
    return body["job"]


def wait(server, key, wanted):
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        job = control(server, "picks/" + key)
        if job["state"] in wanted:
            return job
        assert job["state"] not in {"FAILED", "CANCELLED"}, job
        time.sleep(0.05)
    raise AssertionError("native selection/import did not finish")


def native_add(server, service):
    selected = control(server, "picks")
    key = selected["job_id"]
    wait(server, key, {"SELECTED"})
    started = time.monotonic()
    assert control(server, f"picks/{key}/confirm")["state"] == "IMPORTING"
    accepted_seconds = time.monotonic() - started
    assert accepted_seconds < 1
    completed = wait(server, key, {"COMPLETE"})
    item = completed["files"][0]
    assert item["import"], item
    return {"item": item, "accepted_seconds": accepted_seconds, "saved_seconds": time.monotonic() - started}


def media(seed, target, size):
    with seed.open("rb") as source, target.open("wb") as output:
        output.write(source.read(1024 * 1024))
        output.write(struct.pack(">I4s", size - output.tell(), b"free"))
        output.truncate(size)


def main():
    evidence = []
    clone_times = []
    original_clone = source_authority.clone_descriptor
    def measured_clone(*args):
        start = time.monotonic()
        cloned = original_clone(*args)
        clone_times.append({"cloned": cloned, "seconds": time.monotonic() - start})
        return cloned
    source_authority.clone_descriptor = measured_clone
    tracemalloc.start()
    with tempfile.TemporaryDirectory(prefix="intelligence-d2-02-native-") as directory:
        root = Path(directory).resolve()
        seed = root / "small.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=32x32:r=5:d=1", str(seed)], check=True, timeout=20)
        source = root / "native-two-gib.mp4"
        media(seed, source, MAX_MEDIA_BYTES)
        repo, backup, app, server, thread = workspace(root / "native")
        app.enable_native_import((ORIGIN,), picker_executable=prepare_native_picker(Path.cwd()))
        service = app._native_import
        try:
            print(f"REAL_NATIVE_PICKER_FILE {source}", flush=True)
            imported = measure("real AppKit selection + native 2 GiB clone admission", lambda: native_add(server, service), evidence)
            item = imported["item"]
            assert item["snapshot_method"] == "APFS_CLONE"
            content_id = item["import"]["content_id"]
            relative = f"transcripts/local/{content_id}/source.mp4"
            snapshot = backup.data_root / relative
            assert snapshot.stat().st_ino != source.stat().st_ino
            assert source.stat().st_size == MAX_MEDIA_BYTES
            verified = hash_managed(backup.data_root, relative, maximum=MAX_MEDIA_BYTES)
            assert verified == (MAX_MEDIA_BYTES, content_id[6:])
            # Other HTTP actions remain responsive while background copying runs.
            assert get(server, f"/api/v1/videos/{content_id}")["video"]["processing_status"] == "TRANSCRIPTION_UNAVAILABLE"
            service.picker = lambda _: [source]  # explicit test seam after real picker proof
            repeated = measure("native duplicate: test-only selection seam", lambda: native_add(server, service), evidence)
            assert repeated["item"]["import"]["duplicate"]
            assert len(repo.list_videos()) == 1
            with source.open("r+b") as original:
                original.seek(MAX_MEDIA_BYTES - 4096)
                original.write(b"Changed original; clone must stay independent.")
            moved = source.rename(root / "moved-original.mp4")
            moved.unlink()  # only the test-generated original
            assert hash_managed(backup.data_root, relative, maximum=MAX_MEDIA_BYTES) == verified
            # Force the documented unsupported-filesystem path over actual 2 GiB.
            fallback = root / "fallback-two-gib.mp4"
            media(seed, fallback, MAX_MEDIA_BYTES)
            source_authority.clone_descriptor = lambda *_: False
            service.picker = lambda _: [fallback]
            copied = measure("actual 2 GiB native stream fallback: test-only selection/unsupported clone seam", lambda: native_add(server, service), evidence)
            assert copied["item"]["snapshot_method"] == "STREAM_COPY"
            assert copied["item"]["import"]["duplicate"]
            source_authority.clone_descriptor = measured_clone
            # Near-boundary bytes are real; chooser substitution is clearly labelled.
            near = root / "near-two-gib.mp4"
            media(seed, near, MAX_MEDIA_BYTES - 1)
            _, near_backup, near_app, near_server, near_thread = workspace(root / "near")
            near_app.enable_native_import((ORIGIN,), picker_executable=prepare_native_picker(Path.cwd()))
            near_app._native_import.picker = lambda _: [near]
            try:
                near_result = measure("actual 2 GiB - 1 native clone: test-only selection seam", lambda: native_add(near_server, near_app._native_import), evidence)
                assert near_result["item"]["byte_count"] == MAX_MEDIA_BYTES - 1
                assert near_result["item"]["snapshot_method"] == "APFS_CLONE"
                assert hash_managed(near_backup.data_root, f"transcripts/local/{near_result['item']['import']['content_id']}/source.mp4", maximum=MAX_MEDIA_BYTES)[0] == MAX_MEDIA_BYTES - 1
            finally:
                near_app.shutdown_native_import()
                near_server.shutdown()
                near_server.server_close()
                near_thread.join()
            transcript = MediaTranscript("en", (TimedTranscriptCueWrite(start_ms=0, end_ms=500, text="Native isolated two GiB Evidence round trip."),), "d2-02-native-test-owned-timed-cues-v1")
            measure("accept deterministic Evidence, no actual ASR", lambda: LocalContentProvider(repo, backup.data_root).accept_transcript(content_id, transcript), evidence)
            eid = repo.list_evidence_for_presentation(content_id)[0]
            original_evidence = repo.resolve_verified_evidence_text(eid)
            created = measure("native snapshot ZIP64 backup", lambda: post(server, "/api/v1/backup-restore/backups"), evidence)["backup"]
            archive = root / "backup.zip"
            measure("stream backup download", lambda: get(server, f"/api/v1/backup-restore/backups/{created['backup_id']}/download", output=archive), evidence)
            target, recovery, target_app, target_server, target_thread = workspace(root / "restore")
            try:
                staged = measure("stream restore stage", lambda: post(target_server, "/api/v1/backup-restore/restore/stage", file=archive), evidence)["restore"]
                measure("confirm restore", lambda: post(target_server, "/api/v1/backup-restore/restore/confirm", body={"restore_id": staged["restore_id"]}), evidence)
                measure("restart restore activation", recovery.recover_and_apply_pending_restore, evidence)
                target.bind_source_storage(recovery.data_root)
                assert target.resolve_verified_evidence_text(eid) == original_evidence
                assert hash_managed(recovery.data_root, relative, maximum=MAX_MEDIA_BYTES) == verified
                # Confirmation intentionally shuts down the HTTP listener for restart.
                assert target_app.handle("GET", f"/api/v1/videos/{content_id}")[1]["video"]["processing_status"] == "READY"
            finally:
                target_server.shutdown()
                target_server.server_close()
                target_thread.join()
            REPORT.write_text(json.dumps({"real_native_selection": True, "actual_bytes": MAX_MEDIA_BYTES,
                "source": "real ffmpeg 1-second MP4 + valid sparse free atom; all source bytes hashed",
                "http_file_upload_bytes": 0, "native_control_request_bytes": 2,
                "accepted_seconds": imported["accepted_seconds"], "saved_seconds": imported["saved_seconds"],
                "clones": clone_times, "original_edit_move_delete_independence": "passed",
                "fallback": "real 2 GiB stream copy; unsupported-volume response forced; chooser substituted only in explicitly labelled later cases",
                "backup_restore_content_evidence_hash": "passed", "actual_asr": False, "steps": evidence}, indent=2) + "\n")
            print("ACTUAL_NATIVE_2_GIB_APFS_ZERO_UPLOAD_BACKUP_RESTORE_PASSED", flush=True)
        finally:
            source_authority.clone_descriptor = original_clone
            app.shutdown_native_import()
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    main()
