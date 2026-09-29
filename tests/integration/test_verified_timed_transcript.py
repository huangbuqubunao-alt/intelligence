"""Card A: trusted, hash-verifying timed-transcript cue read path."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from youtube_intel.domain import (
    Availability,
    LiveStatus,
    VideoMetadata,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
VIDEO_ID = "ausLKMojXaY"
CUE_TEXTS = (
    "Here's a surprising fact.",
    "If you take your phone number,",
    "it's possible to find another whole number",
    "bigger than zero such that multiplying",
    "the two of these results in an even bigger",
    "number consisting of just ones and zeros.",
)


def _database_path(tmp_path: Path) -> Path:
    return tmp_path / "state.sqlite3"


def _raw(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection


def _seed(path: Path, *, cues: tuple[str, ...] = CUE_TEXTS) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=VIDEO_ID,
            channel_id="UC_YOZFABF4S8U_7DXMUYrz_Q",
            channel_name="3Blue1Brown",
            title="The Phone Number puzzle",
            description="Part of a monthly series of puzzles",
            source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
            published_at=NOW,
            duration_seconds=44,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.ENDED,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    artifact_id = f"artifact-{VIDEO_ID}"
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=artifact_id,
            artifact_key=f"transcript/{VIDEO_ID}",
            video_id=VIDEO_ID,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=f"transcripts/{VIDEO_ID}/canonical.txt",
            content_hash=sha256("".join(cues).encode("utf-8")).hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    repository.create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id=VIDEO_ID,
            canonical_artifact_id=artifact_id,
            cues=tuple(
                TimedTranscriptCueWrite(
                    start_ms=index * 1000, end_ms=(index + 1) * 1000, text=text
                )
                for index, text in enumerate(cues)
            ),
        ),
        now=NOW,
    )
    return repository


def _break_immutability(path: Path) -> None:
    """Simulate a writer bug by removing the immutability guards.

    The database triggers already reject post-hoc tampering.  These tests drop
    them deliberately so the *reader's* own verification is exercised
    independently — defence in depth, not a weakening of the schema.
    """
    connection = _raw(path)
    for trigger in (
        "timed_transcript_cues_immutable_update",
        "timed_transcript_cues_immutable_delete",
        "timed_transcripts_immutable_update",
    ):
        connection.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    connection.close()


def test_A1_valid_transcript_returns_verified_cues(tmp_path: Path) -> None:
    repository = _seed(_database_path(tmp_path))
    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    assert verified.video_id == VIDEO_ID
    assert len(verified.cues) == len(CUE_TEXTS)
    assert [cue.text for cue in verified.cues] == list(CUE_TEXTS)


def test_A2_cues_are_returned_in_deterministic_cue_index_order(
    tmp_path: Path,
) -> None:
    path = _database_path(tmp_path)
    repository = _seed(path)
    first = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert first is not None
    assert [cue.cue_index for cue in first.cues] == list(range(len(CUE_TEXTS)))
    # Repeated reads are byte-identical.
    second = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert second == first


def test_A3_altered_cue_text_with_stale_hash_fails_closed(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = _seed(path)
    _break_immutability(path)
    connection = _raw(path)
    connection.execute(
        "UPDATE timed_transcript_cues SET cue_text = 'fabricated text' WHERE cue_index = 1"
    )
    connection.close()
    assert repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None


def test_A4_altered_timed_transcript_hash_fails_closed(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = _seed(path)
    _break_immutability(path)
    connection = _raw(path)
    connection.execute("UPDATE timed_transcripts SET timed_transcript_hash = ?", ("0" * 64,))
    connection.close()
    assert repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None


def test_A5_foreign_or_deleted_canonical_artifact_fails_closed(
    tmp_path: Path,
) -> None:
    path = _database_path(tmp_path)
    repository = _seed(path)
    # A genuine foreign case: point this transcript at another video's
    # canonical artifact rather than a nonexistent id (which the FK already
    # rejects at the database level).
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id="other-video",
            channel_id="UC_OTHER",
            channel_name="Other channel",
            title="Other",
            description="",
            source_url="https://www.youtube.com/watch?v=other-video",
            published_at=NOW,
            duration_seconds=10,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.ENDED,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="artifact-other",
            artifact_key="transcript/other-video",
            video_id="other-video",
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path="transcripts/other-video/canonical.txt",
            content_hash=sha256(b"other").hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    _break_immutability(path)
    connection = _raw(path)
    connection.execute(
        "UPDATE timed_transcripts SET canonical_artifact_id = 'artifact-other'"
    )
    connection.close()
    assert repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None


def test_A5b_wrong_artifact_kind_fails_closed(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = _seed(path)
    connection = _raw(path)
    connection.execute(
        "UPDATE artifacts SET kind = 'analysis_structured' WHERE artifact_id = ?",
        (f"artifact-{VIDEO_ID}",),
    )
    connection.close()
    assert repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None


def test_A6_missing_cue_fails_closed(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = _seed(path)
    _break_immutability(path)
    connection = _raw(path)
    connection.execute("DELETE FROM timed_transcript_cues WHERE cue_index = 2")
    connection.close()
    # A gap breaks cue_index contiguity, so the reader refuses the transcript.
    assert repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None


def test_A7_restart_returns_identical_verified_result(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    first = _seed(path).get_verified_timed_transcript(video_id=VIDEO_ID)
    assert first is not None
    reopened = SQLiteStateRepository(path)
    second = reopened.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert second == first


def test_A8_read_performs_no_mutation(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = _seed(path)
    before = _raw(path).execute("PRAGMA data_version").fetchone()[0]
    snapshot = _raw(path).execute(
        "SELECT timed_transcript_id, cue_index, cue_text, cue_text_hash FROM timed_transcript_cues ORDER BY cue_index"
    ).fetchall()
    for _ in range(3):
        assert repository.get_verified_timed_transcript(video_id=VIDEO_ID) is not None
    after = _raw(path).execute("PRAGMA data_version").fetchone()[0]
    rows = _raw(path).execute(
        "SELECT timed_transcript_id, cue_index, cue_text, cue_text_hash FROM timed_transcript_cues ORDER BY cue_index"
    ).fetchall()
    assert after == before
    assert [tuple(row) for row in rows] == [tuple(row) for row in snapshot]


def test_unknown_video_returns_none(tmp_path: Path) -> None:
    repository = _seed(_database_path(tmp_path))
    assert repository.get_verified_timed_transcript(video_id="not-a-video") is None


@pytest.mark.parametrize("bad", ["", "  ", "x" * 600])
def test_invalid_video_identity_raises(tmp_path: Path, bad: str) -> None:
    repository = _seed(_database_path(tmp_path))
    with pytest.raises(ValueError, match="video identity is invalid"):
        repository.get_verified_timed_transcript(video_id=bad)
