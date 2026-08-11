"""Shared path validation contract between note producer and weekly consumer."""

from __future__ import annotations

import pytest

from youtube_intel.notes import build_video_note_filename
from youtube_intel.path_validation import (
    InvalidNotePathError,
    validate_video_note_relative_path,
)


def _relative_path(filename: str) -> str:
    return f"Videos/{filename}"


@pytest.mark.parametrize(
    "title",
    (
        "中文标题",
        "日文タイトル",
        "Product 2026",
        "版本２",
        # Devanagari with explicit combining marks.
        "हिन्दी में",
        # Arabic with tashkil combining marks.
        "تحليل عربي",
    ),
    ids=("chinese", "japanese", "latin-number", "chinese-number", "hindi-combining", "arabic-combining"),
)
def test_producer_filename_passes_consumer_validation(title: str) -> None:
    """Every filename the producer generates must be accepted by the consumer."""
    filename = build_video_note_filename(title, "video-a")
    relative_path = _relative_path(filename)
    assert validate_video_note_relative_path(relative_path) == relative_path


@pytest.mark.parametrize(
    "relative_path",
    (
        "../evil.md",
        "[link].md",
        "![[embed]].md",
        "Videos/[link]--video-a.md",
        "Videos/![[embed]]--video-a.md",
        "Videos/Title--x.md",
        "/absolute/path.md",
        "Videos/\x01control--video-a.md",
    ),
    ids=("traversal", "plain-link", "plain-embed", "video-link", "video-embed", "short-id", "absolute", "control-char"),
)
def test_invalid_paths_are_rejected(relative_path: str) -> None:
    with pytest.raises(InvalidNotePathError):
        validate_video_note_relative_path(relative_path)


def test_injection_characters_are_replaced_by_producer() -> None:
    """Characters that would be rejected by the consumer are sanitized by the producer."""
    filename = build_video_note_filename("[link] ![image] #tag", "video-a")
    relative_path = _relative_path(filename)
    assert validate_video_note_relative_path(relative_path) == relative_path
