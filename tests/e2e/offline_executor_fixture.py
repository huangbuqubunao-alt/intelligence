"""TEST ONLY: real bounded processes/media, deterministic SDK response injection."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from youtube_intel.offline_transcription import MlxTimedExecutor

DIMENSIONS = {
    name: 1
    for name in (
        "n_mels",
        "n_audio_ctx",
        "n_audio_state",
        "n_audio_head",
        "n_audio_layer",
        "n_vocab",
        "n_text_ctx",
        "n_text_state",
        "n_text_head",
        "n_text_layer",
    )
}


def fixture_model(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.json").write_text(json.dumps(DIMENSIONS))
    (root / "weights.safetensors").write_bytes(b"fixture-not-real-model-weights")
    return root


class ProcessFixtureExecutor(MlxTimedExecutor):
    """Only the MLX worker command is injected; production preprocess/parse run."""

    def __init__(self, root: Path, *, timeout: float = 5):
        self.root = root
        super().__init__(
            model_path=fixture_model(root / "fixture-model"),
            temporary_root=root / "temporary",
            timeout=timeout,
        )

    def _command(self, *args: str) -> list[str]:
        command = [
            sys.executable,
            str(Path(__file__).with_name("offline_fixture_worker.py")),
            "--fixture-root",
            str(self.root),
            *args,
        ]
        sandbox = Path("/usr/bin/sandbox-exec")
        if sandbox.is_file():
            command = [
                str(sandbox),
                "-p",
                "(version 1)(allow default)(deny network*)",
                *command,
            ]
        return command

    def _runtime_package_installed(self) -> bool:
        """Synthesized E2E process executor validates the Python worker, not host mlx_whisper."""
        return True

    def capability(self):
        mode = (
            (self.root / "capability-mode.txt").read_text().strip()
            if (self.root / "capability-mode.txt").exists()
            else "READY"
        )
        if mode != "READY":
            from youtube_intel.offline_transcription import TranscriptionCapability

            return TranscriptionCapability(
                mode,
                mode != "RUNTIME_UNAVAILABLE",
                mode != "RUNTIME_UNAVAILABLE",
                reason_code=mode,
            )
        return super().capability()
