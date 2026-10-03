"""Untrusted local executor boundary and bounded task-owned subprocesses."""

import json
import sys

import pytest

from youtube_intel.offline_transcription import (
    OfflineError,
    run_bounded,
    validate_result,
)


def result(segments=None, language="zh"):
    return json.dumps(
        {
            "language": language,
            "segments": segments
            if segments is not None
            else [{"start": 0.125, "end": 1.5, "text": "你好 café العربية"}],
        },
        ensure_ascii=True,
    ).encode()


def test_multilingual_timing_and_original_output():
    raw = result()
    transcript = validate_result(raw, duration_seconds=2, provenance="fixture-v1")
    assert transcript.cues[0].start_ms == 125
    assert transcript.cues[0].end_ms == 1500
    assert transcript.cues[0].text == "你好 café العربية"
    assert transcript.language == "zh"
    assert transcript.raw_output == raw


def test_real_whisper_boundary_spaces_are_preserved():
    raw = result([{"start": 0, "end": 1.5, "text": " The library opens. "}], language="en")
    transcript = validate_result(raw, duration_seconds=2, provenance="fixture-v1")
    assert transcript.cues[0].text == " The library opens. "
    assert transcript.raw_output == raw


def test_whitespace_only_cue_still_rejected():
    from youtube_intel.state import TimedTranscriptCueWrite

    with pytest.raises(ValueError):
        TimedTranscriptCueWrite(start_ms=0, end_ms=1000, text=" \n\t ")


@pytest.mark.parametrize(
    "segments",
    [
        [],
        [{"start": -1, "end": 1, "text": "x"}],
        [{"start": 2, "end": 1, "text": "x"}],
        [{"start": 0, "end": 4, "text": "x"}],
        [{"start": 0, "end": 1, "text": ""}],
        [{"start": 0, "end": 1, "text": 2}],
        [{"start": float("nan"), "end": 1, "text": "x"}],
        [{"start": 0, "end": float("inf"), "text": "x"}],
        [{"start": True, "end": 1, "text": "x"}],
        [{"start": 0, "end": 1, "text": "\ud800"}],
        [{"start": 0, "end": 1, "text": "x"}, {"start": 0.5, "end": 2, "text": "y"}],
    ],
)
def test_invalid_transcript_fails_closed(segments):
    with pytest.raises(OfflineError, match="TRANSCRIPT_INVALID"):
        validate_result(result(segments), duration_seconds=2, provenance="fixture")


@pytest.mark.parametrize(
    "raw",
    [
        b"no json",
        b"\xff",
        b"[]",
        b'{"language":"en","segments":null}',
        b'{"language":"en","language":"zh","segments":[]}',
    ],
)
def test_malformed_response(raw):
    with pytest.raises(OfflineError):
        validate_result(raw, duration_seconds=2, provenance="fixture")


def test_unknown_language():
    assert (
        validate_result(
            result(language=None), duration_seconds=2, provenance="fixture"
        ).language
        == "und"
    )


def test_bounded_success_nonzero_timeout_and_flood():
    assert run_bounded([sys.executable, "-c", 'print("ok")'], timeout=2) == b"ok\n"
    for script, code in [
        ("raise SystemExit(7)", "EXECUTOR_FAILED"),
        ("import time; time.sleep(5)", "EXECUTOR_TIMEOUT"),
        ('print("x" * 100000)', "EXECUTOR_OUTPUT_LIMIT"),
        ('import sys; sys.stderr.write("x" * 100000)', "EXECUTOR_OUTPUT_LIMIT"),
    ]:
        with pytest.raises(OfflineError) as caught:
            run_bounded(
                [sys.executable, "-c", script],
                timeout=0.15 if "sleep" in script else 2,
                maximum=1024,
            )
        assert caught.value.code == code


def test_task_owned_child_stops_when_application_parent_dies(tmp_path):
    import subprocess
    import time

    flag = tmp_path / "child-heartbeat"
    script = (
        "from pathlib import Path; import time; p=Path("
        + repr(str(flag))
        + '); exec("while True:\\n p.write_text(str(time.time()))\\n time.sleep(.1)")'
    )
    parent = subprocess.Popen(
        [
            sys.executable,
            "-c",
            'from youtube_intel.offline_transcription import run_bounded; import sys; run_bounded([sys.executable,"-c",'
            + repr(script)
            + "],timeout=20)",
        ]
    )
    try:
        deadline = time.monotonic() + 3
        while not flag.exists():
            assert time.monotonic() < deadline
            time.sleep(0.05)
        parent.terminate()
        parent.wait(timeout=3)
        time.sleep(0.5)
        previous = flag.read_text()
        time.sleep(0.5)
        assert flag.read_text() == previous
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait()


def test_executable_spoofing_in_arbitrary_path_is_unavailable(tmp_path, monkeypatch):
    from youtube_intel import offline_transcription as module

    spoof = tmp_path / "ffmpeg"
    spoof.write_text("#!/bin/sh\nexit 0\n")
    spoof.chmod(0o755)
    monkeypatch.setattr(module.shutil, "which", lambda _: str(spoof))
    assert module.media_tool("ffmpeg") is None
    assert module.media_tool("whisper") is None
