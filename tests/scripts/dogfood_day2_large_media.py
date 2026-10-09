"""Actual isolated 2 GiB HTTP/ffprobe/ZIP64 round trip and bounded RSS evidence.

Run: PYTHONPATH=src .venv/bin/python tests/scripts/dogfood_day2_large_media.py
Source is a real one-second MP4 followed by a standards-valid sparse free atom.
Every upload, snapshot, hash, archive download and restore byte is read/written.
No transcriber/model is called; test-owned timed cues exercise Evidence authority.
"""

import http.client
import json
import resource
import struct
import subprocess
import tempfile
import threading
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.local_content import LocalContentProvider, MediaTranscript
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.source_authority import MAX_MEDIA_BYTES, hash_managed
from youtube_intel.state import SQLiteStateRepository, TimedTranscriptCueWrite

NOW = datetime(2026, 10, 9, tzinfo=UTC)
CHUNK = 1024 * 1024
REPORT = Path("docs/validation/dogfood-day2-d2-02/actual-large-media.json")


def workspace(root):
    root.mkdir()
    repo = SQLiteStateRepository(root / "state.sqlite")
    repo.initialize(now=NOW)
    data = root / "data"
    data.mkdir()
    backup = BackupRestoreService(database=root / "state.sqlite", data_root=data)
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=data, backup_restore_service=backup)
    server = serve_loopback(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return repo, backup, app, server, thread


def post(server, route, file=None, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=600)
    connection.putrequest("POST", route)
    connection.putheader("X-YIA-Request", "local-ui")
    connection.putheader("Content-Type", "application/zip" if file and file.suffix == ".zip" else "application/octet-stream" if file else "application/json")
    payload = json.dumps(body or {}).encode() if file is None else None
    connection.putheader("Content-Length", str(file.stat().st_size if file else len(payload)))
    connection.endheaders()
    if file:
        with file.open("rb") as source:
            while chunk := source.read(CHUNK):
                connection.send(chunk)
    else:
        connection.send(payload)
    response = connection.getresponse()
    result = json.loads(response.read(1024 * 1024))
    assert response.status in (200, 201, 202), (response.status, result)
    connection.close()
    return result


def get(server, route, output=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=600)
    connection.request("GET", route)
    response = connection.getresponse()
    assert response.status == 200
    if output:
        size = 0
        with output.open("wb") as destination:
            while chunk := response.read(CHUNK):
                size += len(chunk)
                destination.write(chunk)
        assert size == int(response.getheader("Content-Length"))
        result = {"download_bytes": size}
    else:
        result = json.loads(response.read(4 * CHUNK))
    connection.close()
    return result


def measure(name, action, evidence):
    started = time.monotonic()
    tracemalloc.reset_peak()
    baseline = tracemalloc.get_traced_memory()[0]
    result = action()
    current, peak = tracemalloc.get_traced_memory()
    record = {"stage": name, "seconds": round(time.monotonic() - started, 3),
              "python_peak_delta_bytes": peak - baseline,
              "process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    evidence.append(record)
    print(json.dumps(record), flush=True)
    assert peak - baseline < 64 * CHUNK, record
    assert record["process_peak_rss_bytes"] < 512 * CHUNK, record
    return result


def large_mp4(seed, target, size):
    with seed.open("rb") as source, target.open("wb") as output:
        output.write(source.read(CHUNK))
        padding = size - output.tell()
        assert 8 <= padding < 2 ** 32
        output.write(struct.pack(">I4s", padding, b"free"))
        output.truncate(size)
    assert target.stat().st_size == size


def main():
    evidence = []
    tracemalloc.start()
    with tempfile.TemporaryDirectory(prefix="intelligence-d2-02-actual-") as directory:
        root = Path(directory)
        seed = root / "real-video.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=32x32:r=5:d=1", str(seed)], check=True, timeout=20)
        for size in [MAX_MEDIA_BYTES - 1, MAX_MEDIA_BYTES]:
            source = root / f"real-{size}.mp4"
            large_mp4(seed, source, size)
            repo, backup, app, server, thread = workspace(root / str(size))
            try:
                imported = measure(f"HTTP import {size}", lambda: post(server, f"/api/v1/local/imports?filename={quote(source.name)}", file=source), evidence)["import"]
                content_id = imported["content_id"]
                assert imported["status"] == "TRANSCRIPTION_UNAVAILABLE"
                relative = f"transcripts/local/{content_id}/source.mp4"
                verified = measure(f"snapshot SHA256 {size}", lambda: hash_managed(backup.data_root, relative, maximum=MAX_MEDIA_BYTES), evidence)
                assert verified == (size, content_id[6:])
                detail = measure(f"normal Content read {size}", lambda: get(server, f"/api/v1/videos/{content_id}"), evidence)
                assert detail["video"]["processing_status"] == "TRANSCRIPTION_UNAVAILABLE"
                repeated = measure(f"duplicate HTTP import {size}", lambda: post(server, f"/api/v1/local/imports?filename={source.name}", file=source), evidence)["import"]
                assert repeated["duplicate"] and repeated["content_id"] == content_id
                assert len(repo.list_videos()) == 1
                if size == MAX_MEDIA_BYTES:
                    # Deterministic transcript authority fixture; no actual ASR claim.
                    provider = LocalContentProvider(repo, backup.data_root)
                    transcript = MediaTranscript("en", (TimedTranscriptCueWrite(start_ms=0, end_ms=500, text="Isolated two GiB Evidence round trip."),), "d2-02-test-owned-timed-cues-v1")
                    measure("accept deterministic timed Evidence", lambda: provider.accept_transcript(content_id, transcript), evidence)
                    eid = repo.list_evidence_for_presentation(content_id)[0]
                    original = repo.resolve_verified_evidence_text(eid)
                    created = measure("HTTP create ZIP64 backup", lambda: post(server, "/api/v1/backup-restore/backups"), evidence)["backup"]
                    archive = root / "downloaded.zip"
                    measure("HTTP stream backup download", lambda: get(server, f"/api/v1/backup-restore/backups/{created['backup_id']}/download", output=archive), evidence)
                    assert archive.stat().st_size > MAX_MEDIA_BYTES
                    restored, recovery, restored_app, target_server, target_thread = workspace(root / "restore")
                    try:
                        staged = measure("HTTP stream restore stage", lambda: post(target_server, "/api/v1/backup-restore/restore/stage", file=archive), evidence)["restore"]
                        measure("HTTP confirm restore", lambda: post(target_server, "/api/v1/backup-restore/restore/confirm", body={"restore_id": staged["restore_id"]}), evidence)
                        measure("restart-boundary restore activation", recovery.recover_and_apply_pending_restore, evidence)
                        restored.bind_source_storage(recovery.data_root)
                        assert restored.resolve_verified_evidence_text(eid) == original
                        assert len(restored.list_videos()) == 1
                        with restored._connect() as db:
                            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
                        result = measure("restored normal Content read", lambda: restored_app.handle("GET", f"/api/v1/videos/{content_id}")[1], evidence)
                        assert result["video"]["processing_status"] == "READY"
                        assert hash_managed(recovery.data_root, relative, maximum=MAX_MEDIA_BYTES) == verified
                    finally:
                        target_server.shutdown()
                        target_server.server_close()
                        target_thread.join()
                assert not list((backup.data_root / ".imports").iterdir())
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
            # Remove only this test-owned workspace before the next size.
            import shutil
            shutil.rmtree(root / str(size))
        REPORT.write_text(json.dumps({"real_media": "ffmpeg one-second MP4 with valid sparse free atom; full bytes transferred", "actual_sizes": [MAX_MEDIA_BYTES - 1, MAX_MEDIA_BYTES], "asr": "not called; deterministic timed-cue fixture for Evidence", "steps": evidence}, indent=2) + "\n")
        print("ACTUAL_2_GIB_IMPORT_BACKUP_RESTORE_PASSED", flush=True)


if __name__ == "__main__":
    main()
