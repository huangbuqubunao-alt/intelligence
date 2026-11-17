"""Owner-approved 4-hour local media duration & macOS xattr ctime tolerance."""

from __future__ import annotations

import os
import struct
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel import local_content, source_authority
from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.local_content import LocalContentProvider, LocalImportError
from youtube_intel.native_import import NativeImportService
from youtube_intel.state import SQLiteStateRepository

ORIGIN = "http://127.0.0.1:5488"
NOW = datetime(2026, 11, 17, 16, 0, tzinfo=UTC)


def _write_sparse_pcm_wav(path: Path, seconds: int) -> None:
    frames = 16000 * seconds
    data_size = frames * 2
    with path.open("wb") as output:
        output.write(
            struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF",
                min(data_size + 36, 0xFFFFFFFF),
                b"WAVE",
                b"fmt ",
                16,
                1,
                1,
                16000,
                32000,
                2,
                16,
                b"data",
                min(data_size, 0xFFFFFFFF),
            )
        )
        output.truncate(data_size + 44)


def _settled(service: NativeImportService, job_id: str, states: tuple[str, ...] = ("SELECTED", "FAILED", "CANCELLED")) -> dict[str, object]:
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        current = service.status(job_id, ORIGIN)
        if current["state"] in states:
            return current
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not settle: {service.status(job_id, ORIGIN)}")


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS xattr ctime behavior")
def test_macos_xattr_ctime_update_during_pick_and_clone_imports_cleanly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repo.initialize(now=NOW)
    provider = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)
    source = tmp_path / "lecture_ev.mp4"
    source.write_bytes(b"\x00\x00\x00 ftypisom" + b"a" * 4096)
    monkeypatch.setattr(local_content, "probe_media", lambda *_: 7773.2)

    import ctypes
    libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    libc.setxattr.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int)
    libc.setxattr.restype = ctypes.c_int

    xattr_calls = 0

    def touch_finder_xattr() -> None:
        nonlocal xattr_calls
        xattr_calls += 1
        payload = struct.pack("<QQ", int(time.time()) + xattr_calls, xattr_calls)
        rc = libc.setxattr(
            os.fsencode(source),
            b"com.apple.lastuseddate#PS",
            payload,
            len(payload),
            0,
            0,
        )
        assert rc == 0

    service = NativeImportService(provider, origins=(ORIGIN,), picker=lambda _: [source])
    try:
        job_id = str(service.choose(ORIGIN)["job_id"])
        picked = _settled(service, job_id)
        assert picked["state"] == "SELECTED"

        # 1) Finder/LaunchServices updates xattr (st_ctime_ns) after NSOpenPanel returns, before confirm:
        before_stat = source.stat()
        time.sleep(0.005)
        touch_finder_xattr()
        after_xattr_stat = source.stat()
        assert after_xattr_stat.st_mtime_ns == before_stat.st_mtime_ns
        assert after_xattr_stat.st_ctime_ns != before_stat.st_ctime_ns

        # 2) Spotlight updates xattr again mid-stage_native:
        orig_clone = source_authority.clone_descriptor

        def clone_with_xattr(src_fd: int, dst_dir: int, name: str) -> bool:
            res = orig_clone(src_fd, dst_dir, name)
            time.sleep(0.005)
            touch_finder_xattr()
            return res

        monkeypatch.setattr(source_authority, "clone_descriptor", clone_with_xattr)

        service.confirm(job_id, ORIGIN)
        done = _settled(service, job_id, ("COMPLETE", "FAILED"))
        assert done["state"] == "COMPLETE"
        files = done["files"]
        assert isinstance(files, list) and files[0]["error_code"] is None
        assert files[0]["phase"] == "SAVED"
        assert len(repo.list_videos()) == 1
    finally:
        service.shutdown()


def test_source_content_mutation_mid_stage_maps_to_selected_file_changed_not_untrusted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repo.initialize(now=NOW)
    provider = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)
    source = tmp_path / "notes.md"
    source.write_bytes(b"Original lecture transcript.\n")
    monkeypatch.setattr(source_authority, "clone_descriptor", lambda *_: False)

    service = NativeImportService(provider, origins=(ORIGIN,), picker=lambda _: [source])
    try:
        job_id = str(service.choose(ORIGIN)["job_id"])
        assert _settled(service, job_id)["state"] == "SELECTED"

        # Trigger content mutation during stage_native's stream fallback
        def progress_hook(phase: str, *_args: object) -> None:
            if phase == "COPYING":
                time.sleep(0.005)
                source.write_bytes(b"Mutated same-length text!!\n\n")

        with source.open("rb") as fh, pytest.raises(LocalImportError) as exc_info:
            provider.import_selected("notes.md", fh, cancelled=lambda: False, progress=progress_hook)
        assert exc_info.value.code == "LOCAL_SELECTED_FILE_CHANGED"
    finally:
        service.shutdown()


def test_local_media_two_to_four_hours_admitted_and_over_four_hours_rejected(tmp_path: Path) -> None:
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    version = repo.initialize(now=NOW)
    assert version.version == 45
    provider = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)

    # 2h 10m (7800s) lecture WAV probes and imports cleanly
    lecture_wav = tmp_path / "2.Prompt Engineering.wav"
    _write_sparse_pcm_wav(lecture_wav, 7800)
    probed = local_content.probe_media(lecture_wav, ".wav")
    assert 7799.0 <= probed <= 7801.0

    service = NativeImportService(provider, origins=(ORIGIN,), picker=lambda _: [lecture_wav])
    try:
        job_id = str(service.choose(ORIGIN)["job_id"])
        assert _settled(service, job_id)["state"] == "SELECTED"
        service.confirm(job_id, ORIGIN)
        done = _settled(service, job_id, ("COMPLETE", "FAILED"))
        assert done["files"][0]["error_code"] is None
        assert done["files"][0]["phase"] == "SAVED"
    finally:
        service.shutdown()

    backup = BackupRestoreService(database=repo._database_path, data_root=tmp_path / "data")
    assert backup.readiness()["ready"] is True

    # > 4h (14401s) media rejects cleanly with LOCAL_MEDIA_TOO_LONG
    over_four_hours = tmp_path / "too_long.wav"
    _write_sparse_pcm_wav(over_four_hours, 14401)
    with pytest.raises(LocalImportError, match="LOCAL_MEDIA_TOO_LONG"):
        local_content.probe_media(over_four_hours, ".wav")
