"""Phase 7 real filesystem/provider authority, with no external execution."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 3, tzinfo=UTC)


def test_text_snapshot_ready_and_restart(tmp_path: Path) -> None:
    from youtube_intel.local_content import LocalContentProvider

    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    repo.initialize(now=NOW)
    provider = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)
    result = provider.import_bytes(
        "notes.txt", b"Trusted local source.\nEvidence remains on device.\n"
    )
    assert result.status == "READY"
    restarted = SQLiteStateRepository(tmp_path / "state.sqlite")
    restarted.bind_source_storage(tmp_path / "data")
    assert restarted.get_video(result.content_id) is not None
    evidence = restarted.list_evidence_for_presentation(result.content_id)
    assert evidence
    verified = restarted.resolve_verified_evidence_text(evidence[0])
    assert verified is not None
    assert verified.locator_type == "TEXT_RANGE"
    assert verified.start_ms is None and verified.end_ms is None
    assert verified.start_offset == 0
    assert verified.excerpt == "Trusted local source.\n"


@pytest.mark.parametrize(
    ("filename", "payload", "code"),
    [
        ("bad.pdf", b"hello", "LOCAL_UNSUPPORTED_FORMAT"),
        ("bad.txt", b"\xff\x00", "LOCAL_INVALID_TEXT"),
        ("bad.md", b"hello\x00binary", "LOCAL_INVALID_TEXT"),
    ],
)
def test_invalid_sources_rejected(
    tmp_path: Path, filename: str, payload: bytes, code: str
) -> None:
    from youtube_intel.local_content import LocalContentProvider, LocalImportError

    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    repo.initialize(now=NOW)
    with pytest.raises(LocalImportError) as caught:
        LocalContentProvider(repo, tmp_path / "data").import_bytes(filename, payload)
    assert caught.value.code == code
    assert repo.list_videos() == ()
