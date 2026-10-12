"""Task-owned MLX process. Local paths only; deny SDK download and sockets."""

from __future__ import annotations

import argparse
import contextlib
import importlib.metadata
import json
import socket
import sys
from pathlib import Path
from typing import NoReturn


def _offline(*args: object, **kwargs: object) -> NoReturn:
    raise RuntimeError("offline execution")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--validate-model")
    parser.add_argument("--transcribe")
    parser.add_argument("--model")
    args = parser.parse_args()
    socket.socket.connect = _offline  # type: ignore[method-assign]
    socket.create_connection = _offline
    with contextlib.redirect_stdout(sys.stderr):
        import mlx_whisper  # type: ignore[import-untyped]
        import mlx_whisper.load_models as loader  # type: ignore[import-untyped]

        loader.snapshot_download = _offline
        if args.probe:
            response: object = {
                "runtime": "mlx-whisper",
                "version": importlib.metadata.version("mlx-whisper"),
            }
        elif args.validate_model:
            loader.load_model(str(Path(args.validate_model).resolve(strict=True)))
            response = {"compatible": True}
        else:
            if not args.model or not args.transcribe or not Path(args.model).is_dir():
                raise ValueError("local model required")
            from youtube_intel.acoustic_remediation import transcribe_pcm

            response = transcribe_pcm(
                Path(args.transcribe),
                lambda audio: mlx_whisper.transcribe(
                    audio,
                    path_or_hf_repo=str(Path(args.model).resolve(strict=True)),
                    task="transcribe", language=None, temperature=0.0,
                    compression_ratio_threshold=2.4, logprob_threshold=-1.0,
                    no_speech_threshold=0.6, initial_prompt=None, verbose=None,
                    word_timestamps=True, condition_on_previous_text=False,
                ),
            )
    sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
