"""Minimal, safe JSONL operation logging.

This module deliberately accepts only bounded operational metadata.  It never
serializes an exception object, configuration object, path, request, or
response body.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

_PATH_RE = re.compile(r"(?:(?:[A-Za-z]:)?/|~/?)[^\s,;:]+")
_SECRET_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|token|secret|password)\b\s*(?:=|:)\s*[^\s,;]+"
)


def _sanitize_message(value: str) -> str:
    """Return bounded diagnostic text with common secrets and paths removed."""

    collapsed = " ".join(value.split())[:300]
    collapsed = _SECRET_RE.sub("[REDACTED]", collapsed)
    return _PATH_RE.sub("[PATH]", collapsed)


def safe_message(value: str) -> str:
    """Public helper for displaying a bounded, redacted diagnostic."""

    return _sanitize_message(value)


@dataclass(frozen=True, slots=True)
class JsonlLogger:
    """Append one safe, schema-stable event per JSONL line."""

    path: Path

    def emit(
        self,
        *,
        level: str,
        event: str,
        run_id: str,
        stage: str,
        safe_message: str,
        video_id: str | None = None,
        job_id: str | None = None,
        error_code: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        if UUID(run_id).version != 4:
            raise ValueError("run_id must be a UUID4")
        record: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": level,
            "event": event,
            "run_id": run_id,
            "stage": stage,
            "safe_message": _sanitize_message(safe_message),
        }
        for name, value in (
            ("video_id", video_id),
            ("job_id", job_id),
            ("error_code", error_code),
            ("duration_ms", duration_ms),
        ):
            if value is not None:
                record[name] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")


__all__ = ["JsonlLogger", "safe_message"]
