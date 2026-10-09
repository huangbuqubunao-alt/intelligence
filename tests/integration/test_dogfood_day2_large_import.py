"""D2-02 isolated streaming admission; no owner database or cloud calls."""

import concurrent.futures
import io
import os
import struct
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel import local_content, source_authority
from youtube_intel.local_content import LocalContentProvider, LocalImportError
from youtube_intel.source_authority import MAX_MEDIA_BYTES, MAX_TEXT_BYTES, hash_managed
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 9, tzinfo=UTC)


@pytest.fixture
def provider(tmp_path: Path) -> LocalContentProvider:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    return LocalContentProvider(repository, tmp_path / "data", now=lambda: NOW)


class GeneratedStream:
    def __init__(self, length: int) -> None:
        self.remaining = length
        self.maximum_read = 0

    def read(self, size: int = -1) -> bytes:
        assert 0 < size <= 1024 * 1024
        self.maximum_read = max(self.maximum_read, size)
        count = min(size, self.remaining)
        self.remaining -= count
        return b"x" * count


def test_over_64_mib_stream_deduplicates_and_verifies(provider, monkeypatch):
    # Real streamed byte count and filesystem/hash checks; media probe is a
    # deliberate boundary simulation here. Real ffprobe runs are separate.
    monkeypatch.setattr(local_content, "probe_media", lambda *_: 1.0)
    size = 64 * 1024 * 1024 + 17
    stream = GeneratedStream(size)
    result = provider.import_stream("large.mp4", stream, size)
    assert result.status == "TRANSCRIPTION_UNAVAILABLE"
    assert stream.remaining == 0 and stream.maximum_read == 1024 * 1024
    relative = f"transcripts/local/{result.content_id}/source.mp4"
    assert hash_managed(provider.data_root, relative, maximum=MAX_MEDIA_BYTES) == (size, result.content_id[6:])
    repeated = provider.import_stream("copy.mp4", GeneratedStream(size), size)
    assert repeated.duplicate and repeated.content_id == result.content_id
    assert len(provider.repository.list_videos()) == 1
    assert list((provider.data_root / ".imports").iterdir()) == []


@pytest.mark.parametrize("name,length,code", [
    ("empty.mp4", 0, "LOCAL_EMPTY_FILE"),
    ("oversized.mp4", MAX_MEDIA_BYTES + 1, "LOCAL_FILE_TOO_LARGE"),
    ("large.txt", MAX_TEXT_BYTES + 1, "LOCAL_FILE_TOO_LARGE"),
    ("large.md", MAX_TEXT_BYTES + 1, "LOCAL_FILE_TOO_LARGE"),
    ("bad.pdf", 1, "LOCAL_UNSUPPORTED_FORMAT"),
])
def test_rejected_size_or_format_never_reads_or_creates_storage(provider, name, length, code):
    with pytest.raises(LocalImportError, match=code):
        provider.import_stream(name, GeneratedStream(0), length)
    assert not provider.data_root.exists()
    assert not provider.repository.list_videos()


@pytest.mark.parametrize("reason,code", [
    (EOFError(), "LOCAL_IMPORT_INTERRUPTED"),
    (TimeoutError(), "LOCAL_IMPORT_TIMEOUT"),
    (OSError(28, "disk full"), "LOCAL_DISK_SPACE_INSUFFICIENT"),
])
def test_failed_receive_cleans_only_its_staging(provider, reason, code):
    class Interrupted:
        calls = 0

        def read(self, size):
            self.calls += 1
            if self.calls == 1:
                return b"x"
            raise reason

    with pytest.raises(LocalImportError, match=code):
        provider.import_stream("clip.mp4", Interrupted(), 2)
    assert list((provider.data_root / ".imports").iterdir()) == []
    assert not provider.repository.list_videos()


def test_disk_space_checked_before_receive(provider, monkeypatch):
    monkeypatch.setattr(source_authority.os, "fstatvfs", lambda _: os.statvfs_result((1, 1, 0, 0, 1, 0, 0, 0, 0, 255)))
    with pytest.raises(LocalImportError, match="LOCAL_DISK_SPACE_INSUFFICIENT"):
        provider.import_stream("clip.mp4", GeneratedStream(1), 1)
    assert list((provider.data_root / ".imports").iterdir()) == []


def test_cancelled_or_invalid_media_never_publishes(provider, monkeypatch):
    monkeypatch.setattr(local_content, "probe_media", lambda *_: 1.0)
    with pytest.raises(LocalImportError, match="LOCAL_IMPORT_CANCELLED"):
        provider.import_stream("clip.mp4", io.BytesIO(b"x"), 1, cancelled=lambda: True)
    monkeypatch.setattr(local_content, "probe_media", lambda *_: (_ for _ in ()).throw(LocalImportError("LOCAL_MEDIA_TOO_LONG")))
    with pytest.raises(LocalImportError, match="LOCAL_MEDIA_TOO_LONG"):
        provider.import_stream("clip.mp4", io.BytesIO(b"x"), 1)
    assert list((provider.data_root / ".imports").iterdir()) == []
    assert not (provider.data_root / "transcripts").exists()


def test_streamed_snapshot_tampering_fails_closed(provider, monkeypatch):
    monkeypatch.setattr(local_content, "probe_media", lambda *_: 1.0)
    imported = provider.import_stream("clip.mp4", io.BytesIO(b"media"), 5)
    snapshot = provider.data_root / f"transcripts/local/{imported.content_id}/source.mp4"
    snapshot.write_bytes(b"other")
    with pytest.raises(LocalImportError, match="LOCAL_SOURCE_UNTRUSTED"):
        provider.import_stream("copy.mp4", io.BytesIO(b"media"), 5)
    assert snapshot.read_bytes() == b"other"


def test_staging_symlink_rejected_without_touching_target(provider, tmp_path):
    target = tmp_path / "private"
    target.mkdir()
    provider.data_root.mkdir()
    (provider.data_root / ".imports").symlink_to(target)
    with pytest.raises(LocalImportError, match="LOCAL_FILE_UNREADABLE"):
        provider.import_stream("clip.mp4", io.BytesIO(b"x"), 1)
    assert list(target.iterdir()) == []


def test_concurrent_provider_retries_share_one_content(provider, monkeypatch):
    monkeypatch.setattr(local_content, "probe_media", lambda *_: 1.0)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(lambda _: provider.import_stream("clip.mp4", io.BytesIO(b"same"), 4), range(4)))
    assert len({result.content_id for result in results}) == 1
    assert sum(not result.duplicate for result in results) == 1
    assert len(provider.repository.list_videos()) == 1
    assert list((provider.data_root / ".imports").iterdir()) == []


def test_read1_deadline_checked_after_each_receive(provider, monkeypatch):
    clock = iter([0.0, 0.0, 7201.0])
    monkeypatch.setattr(source_authority.time, "monotonic", lambda: next(clock))
    class Trickle:
        def read(self, size):
            raise AssertionError("buffered full-chunk read must not be used")

        def read1(self, size):
            return b"x"
    with pytest.raises(LocalImportError, match="LOCAL_IMPORT_TIMEOUT"):
        provider.import_stream("clip.mp4", Trickle(), 2)
    assert list((provider.data_root / ".imports").iterdir()) == []


def test_stage_replacement_during_validation_is_rejected(provider, monkeypatch, tmp_path):
    private = tmp_path / "private.wav"
    private.write_bytes(b"private bytes must never gain authority")
    def replace(path, extension):
        path.unlink()
        path.symlink_to(private)
        return 1.0
    monkeypatch.setattr(local_content, "probe_media", replace)
    with pytest.raises(LocalImportError, match="LOCAL_SOURCE_UNTRUSTED"):
        provider.import_stream("clip.mp4", io.BytesIO(b"same"), 4)
    assert not provider.repository.list_videos()
    assert private.read_bytes() == b"private bytes must never gain authority"
    assert not (provider.data_root / "transcripts").exists()


def test_post_link_substitution_never_gains_authority(provider, monkeypatch, tmp_path):
    monkeypatch.setattr(local_content, "probe_media", lambda *_: 1.0)
    original = os.link
    def substitute(source, destination, **kwargs):
        if destination.startswith("source"):
            os.unlink(source, dir_fd=kwargs["src_dir_fd"])
            fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=kwargs["src_dir_fd"])
            os.write(fd, b"evil")
            os.close(fd)
        return original(source, destination, **kwargs)
    monkeypatch.setattr(source_authority.os, "link", substitute)
    with pytest.raises(LocalImportError, match="LOCAL_SOURCE_UNTRUSTED"):
        provider.import_stream("clip.mp4", io.BytesIO(b"same"), 4)
    assert not provider.repository.list_videos()
    assert list(provider.data_root.rglob("source.mp4")) == []


def test_failed_admission_cleans_new_snapshot_only(provider, monkeypatch):
    def failed(_):
        raise RuntimeError("isolated admission failure")
    monkeypatch.setattr(provider, "_library", failed)
    with pytest.raises(RuntimeError, match="admission failure"):
        provider.import_stream("notes.md", io.BytesIO(b"source"), 6)
    assert list(provider.data_root.rglob("source.md")) == []
    assert list((provider.data_root / ".imports").iterdir()) == []


def test_backup_capacity_prevents_success_that_cannot_be_backed_up(provider, monkeypatch):
    from youtube_intel import backup_restore
    monkeypatch.setattr(backup_restore, "MAX_TOTAL_BYTES", 1024 * 1024 * 1024 + 3)
    with pytest.raises(LocalImportError, match="LOCAL_BACKUP_CAPACITY_EXCEEDED"):
        provider.import_stream("notes.md", io.BytesIO(b"source"), 6)
    assert not provider.repository.list_videos()
    assert list((provider.data_root / ".imports").iterdir()) == []


def test_real_two_hour_duration_is_a_separate_rejection(tmp_path):
    # Real ffprobe parses a sparse, valid PCM WAV with >2-hour sample count;
    # no large Python allocation and no full-length playback/model invocation.
    path = tmp_path / "long.wav"
    frames = 16000 * 7201
    data_size = frames * 2
    with path.open("wb") as output:
        output.write(struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", data_size + 36, b"WAVE", b"fmt ", 16, 1, 1, 16000, 32000, 2, 16, b"data", data_size))
        output.truncate(data_size + 44)
    with pytest.raises(LocalImportError, match="LOCAL_MEDIA_TOO_LONG"):
        local_content.probe_media(path, ".wav")


def test_native_source_mutation_is_checked_before_content_admission(provider, monkeypatch, tmp_path):
    original = tmp_path / "notes.md"
    original.write_bytes(b"selected text")
    stage = local_content.stage_stream
    @contextmanager
    def mutate(*args, **kwargs):
        with stage(*args, **kwargs) as staged:
            original.write_bytes(b"changed source")
            yield staged
    monkeypatch.setattr(local_content, "stage_stream", mutate)
    with pytest.raises(ValueError, match="changed while reading"):
        provider.import_file(original)
    assert not provider.repository.list_videos()
    assert list((provider.data_root / ".imports").iterdir()) == []


def test_restart_cleans_only_abandoned_private_staging_and_keeps_live_import(provider):
    root = provider.data_root / ".imports"
    root.mkdir(parents=True)
    keep = root / "keep-user-file.txt"
    keep.write_text("must remain")
    program = """
import io, sys
from pathlib import Path
from youtube_intel.source_authority import stage_stream
with stage_stream(Path(sys.argv[1]), io.BytesIO(b'private attempt'), 15, maximum=16) as staged:
    print(staged.name, flush=True)
    sys.stdin.read()
"""
    child = subprocess.Popen([sys.executable, "-c", program, str(root)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        name = child.stdout.readline().strip()
        assert name.startswith(".import-") and (root / name).is_file()
        LocalContentProvider(provider.repository, provider.data_root)
        assert (root / name).is_file(), "live writer lock must prevent cleanup"
        child.kill()  # Only this isolated test-owned process; simulate hard crash.
        child.wait(timeout=5)
        LocalContentProvider(provider.repository, provider.data_root)
        assert not (root / name).exists()
        assert keep.read_text() == "must remain"
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        child.stdin.close()
        child.stdout.close()
