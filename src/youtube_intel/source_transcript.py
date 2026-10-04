"""Provider-neutral acquired timed text; acquisition never implies ASR approval."""

from dataclasses import dataclass

from youtube_intel.state import TimedTranscriptCueWrite


@dataclass(frozen=True)
class MediaTranscript:
    language: str
    cues: tuple[TimedTranscriptCueWrite, ...]
    provenance: str
    raw_output: bytes | None = None
