"""Command-line entry point for YouTube Intelligence Agent."""

from __future__ import annotations

from youtube_intel.fast_read_api import run_cli_with_fast_reads

if __name__ == "__main__":
    raise SystemExit(run_cli_with_fast_reads())
