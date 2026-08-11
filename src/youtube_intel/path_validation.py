"""Shared validation for managed video note paths.

This module contains the single source of truth for what characters and path
shapes are allowed in a managed Obsidian video note relative path. Both the
producer (`youtube_intel.notes.build_video_note_filename`) and the consumer
(`youtube_intel.reporting._safe_note_path`) must use it so their rules never
 diverge.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath
from typing import Final

_SAFE_VIDEO_ID_RE: Final = re.compile(r"^[A-Za-z0-9_-]{6,32}$")
# Punctuation permitted in the human-readable base of a note filename.
_SAFE_BASE_PUNCTUATION: Final = frozenset(" -_.()")

# Characters that could form Markdown / Obsidian links, embeds, HTML, or
# template injection inside a wiki-link destination.
_FORBIDDEN_INJECTION_CHARS: Final = frozenset("[]!<>\"'`|#^\n\r")


class InvalidNotePathError(ValueError):
    """Raised when a note relative path violates the shared contract."""


def is_safe_note_base_character(char: str) -> bool:
    """Return True for Unicode letters, numbers, marks, and safe punctuation."""
    category = unicodedata.category(char)
    return category.startswith(("L", "N", "M")) or char in _SAFE_BASE_PUNCTUATION


def validate_video_note_relative_path(value: str) -> str:
    """Validate a managed video note relative path.

    Allowed paths look like ``Videos/<base>--<video_id>.md`` where ``<base>``
    may contain Unicode letters, numbers, combining marks, spaces, and a small
    set of safe punctuation; ``<video_id>`` is alphanumeric/hyphen/underscore.

    Rejects: empty paths, control characters, path traversal, absolute paths,
    Markdown / Obsidian link/embed injection characters, and malformed stems.
    """
    normalized = unicodedata.normalize("NFC", value)
    if not normalized:
        raise InvalidNotePathError("note path is empty")
    if any(unicodedata.category(char) == "Cc" for char in normalized):
        raise InvalidNotePathError("note path contains control characters")
    if any(char in normalized for char in _FORBIDDEN_INJECTION_CHARS):
        raise InvalidNotePathError("note path contains markdown/obsidian injection characters")

    path = PurePosixPath(normalized)
    if path.is_absolute() or len(path.parts) != 2 or path.parts[0] != "Videos":
        raise InvalidNotePathError("note path must be under Videos/")

    filename = path.parts[1]
    if not filename.endswith(".md"):
        raise InvalidNotePathError("note path must end with .md")

    stem = filename[:-3]
    if "--" not in stem:
        raise InvalidNotePathError("note path is missing video-id separator")
    base, video_id = stem.rsplit("--", 1)
    if not base or not _SAFE_VIDEO_ID_RE.match(video_id):
        raise InvalidNotePathError("note path has invalid video id")
    if not all(is_safe_note_base_character(char) for char in base):
        raise InvalidNotePathError("note path base contains unsafe characters")

    return value
