"""Isolated test worker; never a production runtime or model validation claim."""

import argparse
import json
import socket
import sys
import time
import wave
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--fixture-root", type=Path, required=True)
parser.add_argument("--probe", action="store_true")
parser.add_argument("--validate-model")
parser.add_argument("--transcribe")
parser.add_argument("--model")
args = parser.parse_args()
if args.probe:
    print(json.dumps({"runtime": "mlx-whisper", "version": "0.4.3"}))
elif args.validate_model:
    print(json.dumps({"compatible": True}))
else:
    with wave.open(args.transcribe) as stream:
        assert (
            stream.getnchannels() == 1
            and stream.getframerate() == 16000
            and stream.getsampwidth() == 2
        )
        duration = stream.getnframes() / stream.getframerate()
    # Attempted network access must be denied by the isolated OS process policy.
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=0.1)
    except OSError as error:
        assert error.errno == 1  # sandbox denied; connection refusal is insufficient proof
    else:
        raise AssertionError("network was permitted")
    mode = (
        (args.fixture_root / "result-mode.txt").read_text().strip()
        if (args.fixture_root / "result-mode.txt").exists()
        else "success"
    )
    if mode == "failure":
        sys.stderr.write(
            "private-path /Users/private/media and raw details must stay hidden"
        )
        raise SystemExit(7)
    if mode == "timeout":
        time.sleep(60)
    if mode == "flood":
        print("x" * (9 * 1024 * 1024))
        raise SystemExit()
    if mode == "malformed":
        print("{broken")
        raise SystemExit()
    if mode == "slow":
        time.sleep(3)
    print(
        json.dumps(
            {
                "language": "zh",
                "segments": [
                    {
                        "start": 0.125,
                        "end": min(1.75, duration),
                        "text": "Sentence1 本地离线 evidence stays private.",
                    }
                ],
            },
            ensure_ascii=False,
        )
    )
