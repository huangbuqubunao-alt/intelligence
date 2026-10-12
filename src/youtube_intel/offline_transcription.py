"""Offline timed execution boundary. No model installation or network discovery."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import platform
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from youtube_intel.local_content import MediaTranscript
from youtube_intel.source_authority import MAX_TEXT_BYTES, read_managed, sha256
from youtube_intel.state import TimedTranscriptCueWrite

CONTRACT = "offline-timed-transcription-v1"
PROFILE = "mlx-source-silence-native-word-auto-t0-v4"
MAX_RESULT = 4 * 1024 * 1024
MAX_AUDIO = 7200 * 16000 * 2 + 4096


class OfflineError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def media_tool(name: str) -> str | None:
    """Known installed media tools only; a matching name in an arbitrary PATH is insufficient."""
    if name not in {"ffmpeg", "ffprobe"}:
        return None
    candidate = shutil.which(name)
    if candidate is None:
        return None
    try:
        path = Path(candidate).resolve(strict=True)
        trusted = any(
            path.is_relative_to(root)
            for root in (
                Path("/opt/homebrew"),
                Path("/usr/local"),
                Path("/usr/bin"),
                Path("/bin"),
            )
        )
        info = path.stat()
        if (
            not trusted
            or not stat.S_ISREG(info.st_mode)
            or info.st_uid not in {0, os.getuid()}
            or info.st_mode & 0o022
        ):
            return None
        return str(path)
    except OSError:
        return None


def run_bounded(
    args: list[str],
    *,
    timeout: float,
    maximum: int = MAX_RESULT,
    env: dict[str, str] | None = None,
    pass_fds: tuple[int, ...] = (),
) -> bytes:
    """Drain both pipes incrementally; terminate only our isolated process group."""
    process = None
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).with_name("task_process_guard.py")),
                str(os.getpid()),
                *(f"--pass-fd={fd}" for fd in pass_fds),
                *args,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=env,
            pass_fds=pass_fds,
        )
        assert process.stdout is not None and process.stderr is not None
        output = bytearray()
        stderr_size = 0
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, True)
            selector.register(process.stderr, selectors.EVENT_READ, False)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise OfflineError("EXECUTOR_TIMEOUT")
                for key, _ in selector.select(min(0.2, remaining)):
                    chunk = os.read(key.fd, 16384)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    elif key.data:
                        output.extend(chunk)
                        if len(output) > maximum:
                            raise OfflineError("EXECUTOR_OUTPUT_LIMIT")
                    else:
                        stderr_size += len(chunk)
                        if stderr_size > min(maximum, 65536):
                            raise OfflineError("EXECUTOR_OUTPUT_LIMIT")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise OfflineError("EXECUTOR_TIMEOUT")
            if process.wait(timeout=remaining):
                raise OfflineError("EXECUTOR_FAILED")
        return bytes(output)
    except subprocess.TimeoutExpired:
        raise OfflineError("EXECUTOR_TIMEOUT") from None
    except OSError:
        raise OfflineError("RUNTIME_UNAVAILABLE") from None
    finally:
        if process is not None:
            # Descendants may hold pipes after their parent exits. Never use pkill.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def validate_result(
    raw: bytes, *, duration_seconds: float, provenance: str
) -> MediaTranscript:
    """Seconds from MLX become integer milliseconds once; text stays exact."""
    try:
        if (
            not 0 < len(raw) <= MAX_RESULT
            or not math.isfinite(duration_seconds)
            or not 0 < duration_seconds <= 7200
        ):
            raise ValueError("bounds")
        def finite_number(value: str) -> float:
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("nonfinite JSON number")
            return number

        response = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=finite_number,
            parse_float=finite_number,
        )
        if not isinstance(response, dict):
            raise ValueError("object")
        segments = response.get("segments")
        if not isinstance(segments, list) or not 1 <= len(segments) <= 4096:
            raise ValueError("segments")
        language = response.get("language")
        if language is None:
            language = "und"
        if (
            not isinstance(language, str)
            or re.fullmatch(r"[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{1,8})*", language) is None
        ):
            raise ValueError("language")
        cues = []
        previous_seconds = 0.0
        previous_ms = 0
        for segment in segments:
            if not isinstance(segment, dict):
                raise ValueError("segment")
            start, end, text = (
                segment.get("start"),
                segment.get("end"),
                segment.get("text"),
            )
            if (
                not isinstance(start, (int, float))
                or isinstance(start, bool)
                or not isinstance(end, (int, float))
                or isinstance(end, bool)
                or not math.isfinite(start)
                or not math.isfinite(end)
                or start < previous_seconds
                or end <= start
                or end > duration_seconds + 1
                or not isinstance(text, str)
                or not text.strip()
                or len(text) > 2000
                or any(
                    (ord(c) < 32 and c not in "\n\r\t")
                    or ord(c) == 127
                    or c == "\ufffd"
                    for c in text
                )
            ):
                raise ValueError("invalid segment")
            text.encode("utf-8", errors="strict")
            start_ms, end_ms = round(start * 1000), round(end * 1000)
            if start_ms < previous_ms or end_ms <= start_ms:
                raise ValueError("precision")
            cues.append(
                TimedTranscriptCueWrite(start_ms=start_ms, end_ms=end_ms, text=text)
            )
            previous_seconds, previous_ms = end, end_ms
        if len("\n".join(c.text for c in cues).encode("utf-8")) > MAX_TEXT_BYTES:
            raise ValueError("text limit")
        return MediaTranscript(
            language=language, cues=tuple(cues), provenance=provenance, raw_output=raw
        )
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeError,
        OverflowError,
        RecursionError,
    ):
        raise OfflineError("TRANSCRIPT_INVALID") from None


@dataclass(frozen=True)
class TranscriptionCapability:
    state: str
    runtime_detected: bool = False
    runtime_available: bool = False
    model_present: bool = False
    executor_compatible: bool = False
    executor: str = "mlx-whisper-timed-v1"
    model_identity: str | None = None
    execution_identity: str | None = None
    reason_code: str | None = None
    qualification_state: str = "NOT_TESTED"
    qualification_identity: str | None = None
    production_eligible: bool = False

    def as_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


class TranscriptionExecutor(Protocol):
    def capability(self) -> TranscriptionCapability: ...
    def transcribe(
        self, snapshot: Path, *, duration_seconds: float
    ) -> MediaTranscript: ...
    def validate_result(
        self, raw: bytes, *, duration_seconds: float, provenance: str
    ) -> MediaTranscript: ...


def _safe_directory(path: Path) -> Path:
    absolute = path.absolute()
    if (
        not absolute.is_absolute()
        or absolute.resolve() != absolute
        or not absolute.is_dir()
    ):
        raise OfflineError("MODEL_INVALID")
    return absolute


def model_identity(path: Path) -> str:
    """Full content digests, regular non-symlink model files, bounded config/weights."""
    import hashlib

    path = _safe_directory(path)
    config = read_managed(path, "config.json", maximum=65536)
    parsed = json.loads(config)
    limits = {
        "n_mels": 128,
        "n_audio_ctx": 1500,
        "n_audio_state": 1280,
        "n_audio_head": 20,
        "n_audio_layer": 32,
        "n_vocab": 52000,
        "n_text_ctx": 448,
        "n_text_state": 1280,
        "n_text_head": 20,
        "n_text_layer": 32,
    }
    if (
        not isinstance(parsed, dict)
        or not limits.keys() <= parsed.keys()
        or any(
            type(parsed[k]) is not int or not 0 < parsed[k] <= maximum
            for k, maximum in limits.items()
        )
    ):
        raise OfflineError("MODEL_INVALID")
    weights = path / "weights.safetensors"
    if not weights.exists():
        weights = path / "weights.npz"
    fd = os.open(weights, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 4 * 1024**3:
            raise OfflineError("MODEL_INVALID")
        if weights.suffix == ".npz":
            with zipfile.ZipFile(stream) as archive:
                members = archive.infolist()
                if (
                    not 1 <= len(members) <= 4000
                    or sum(member.file_size for member in members) > 4 * 1024**3
                    or any(
                        member.file_size > 1024**3
                        or not member.filename.endswith(".npy")
                        for member in members
                    )
                ):
                    raise OfflineError("MODEL_INVALID")
            stream.seek(0)
        digest = hashlib.sha256(config)
        read_bytes = 0
        for chunk in iter(
            lambda: stream.read(min(1024 * 1024, before.st_size - read_bytes + 1)), b""
        ):
            read_bytes += len(chunk)
            if read_bytes > before.st_size:
                raise OfflineError("MODEL_CHANGED")
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise OfflineError("MODEL_CHANGED")
    return "sha256:" + digest.hexdigest()


class MlxTimedExecutor:
    """Approved installed SDK only; explicit local model directory, never HF names."""

    def __init__(
        self,
        *,
        model_path: Path | None = None,
        temporary_root: Path,
        timeout: float = 1800,
    ) -> None:
        self.model_path = model_path
        self.temporary_root = temporary_root
        self.timeout = timeout
        self._cached_capability: TranscriptionCapability | None = None
        self._cache_key: object = None

    def qualified_capability(self, capability: TranscriptionCapability) -> TranscriptionCapability:
        from youtube_intel.acoustic_qualification import (
            current_tuple,
            qualification_status,
        )

        identity = None
        try:
            if self.model_path is not None and capability.model_identity is not None:
                origin = json.loads(read_managed(self.model_path, "model-origin.json", maximum=16384))
                identity = current_tuple(self.model_path, capability.model_identity, origin)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            pass
        status = qualification_status(self.temporary_root.parent, identity)
        receipt_identity = status.get("identity")
        return replace(capability, qualification_state=str(status["state"]), qualification_identity=receipt_identity if isinstance(receipt_identity, str) else None, production_eligible=status["production_eligible"] is True)

    def _env(self) -> dict[str, str]:
        return {
            "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
            "HOME": str(Path.home()),
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "OMP_NUM_THREADS": "2",
        }

    def _command(self, *args: str) -> list[str]:
        command = [sys.executable, "-m", "youtube_intel.offline_whisper_worker", *args]
        sandbox = "/usr/bin/sandbox-exec"
        if platform.system() == "Darwin" and Path(sandbox).is_file():
            command = [
                sandbox,
                "-p",
                "(version 1)(allow default)(deny network*)",
                *command,
            ]
        return command

    def capability(self) -> TranscriptionCapability:
        detected = importlib.util.find_spec("mlx_whisper") is not None
        if not detected:
            return self.qualified_capability(TranscriptionCapability(
                "RUNTIME_UNAVAILABLE", reason_code="RUNTIME_UNAVAILABLE"
            ))
        paths = (
            []
            if self.model_path is None
            else [
                self.model_path / n
                for n in ("config.json", "weights.safetensors", "weights.npz", "model-origin.json")
            ]
        )
        runtime_available = False
        model_present = False
        try:
            key = (
                str(self.model_path),
                tuple(
                    (p.lstat().st_size, p.lstat().st_mtime_ns, p.lstat().st_ctime_ns)
                    if p.exists()
                    else None
                    for p in paths
                ),
            )
            if self._cached_capability is not None and self._cache_key == key:
                return self.qualified_capability(self._cached_capability)
            raw = run_bounded(
                self._command("--probe"), timeout=20, maximum=65536, env=self._env()
            )
            runtime = json.loads(raw)
            if runtime != {"runtime": "mlx-whisper", "version": "0.4.3"}:
                raise OfflineError("EXECUTOR_INCOMPATIBLE")
            runtime_available = True
            model_present = (
                self.model_path is not None
                and self.model_path.is_dir()
                and (self.model_path / "config.json").exists()
                and any(
                    (self.model_path / n).exists()
                    for n in ("weights.safetensors", "weights.npz")
                )
            )
            if not model_present:
                result = TranscriptionCapability(
                    "MODEL_MISSING", True, True, reason_code="MODEL_MISSING"
                )
            else:
                assert self.model_path is not None
                identity = model_identity(self.model_path)
                compatible = run_bounded(
                    self._command("--validate-model", str(self.model_path)),
                    timeout=60,
                    maximum=65536,
                    env=self._env(),
                )
                if json.loads(compatible) != {"compatible": True}:
                    raise OfflineError("EXECUTOR_INCOMPATIBLE")
                provenance = json.dumps(
                    {
                        "contract": CONTRACT,
                        "executor": "mlx-whisper-timed-v1",
                        "runtime": runtime,
                        "model": identity,
                        "profile": PROFILE,
                        "language_mode": "auto-source",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                result = TranscriptionCapability(
                    "READY",
                    True,
                    True,
                    True,
                    True,
                    model_identity=identity,
                    execution_identity=sha256(provenance.encode()),
                )
            self._cached_capability, self._cache_key = result, key
            return self.qualified_capability(result)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, RecursionError):
            return self.qualified_capability(TranscriptionCapability(
                "UNSUPPORTED",
                True,
                runtime_available,
                model_present,
                reason_code="EXECUTOR_INCOMPATIBLE",
            ))

    validate_result = staticmethod(validate_result)

    def transcribe(self, snapshot: Path, *, duration_seconds: float) -> MediaTranscript:
        import tempfile

        capability = self.capability()
        if capability.state != "READY" or self.model_path is None:
            raise OfflineError(capability.reason_code or capability.state)
        ffmpeg = media_tool("ffmpeg")
        if ffmpeg is None:
            raise OfflineError("MEDIA_TOOL_UNAVAILABLE")
        from youtube_intel.local_content import probe_media

        duration = probe_media(snapshot, snapshot.suffix.lower())
        if abs(duration - duration_seconds) > 0.001:
            raise OfflineError("SOURCE_CHANGED")
        self.temporary_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        _safe_directory(self.temporary_root)
        with tempfile.TemporaryDirectory(
            prefix="attempt-", dir=self.temporary_root
        ) as temporary:
            audio = Path(temporary) / "audio.wav"
            run_bounded(
                [
                    ffmpeg,
                    "-nostdin",
                    "-v",
                    "error",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-max_alloc",
                    "16777216",
                    "-threads",
                    "2",
                    "-f",
                    {".mp3": "mp3", ".wav": "wav"}.get(snapshot.suffix.lower(), "mov"),
                    *(
                        []
                        if snapshot.suffix.lower() in {".mp3", ".wav"}
                        else ["-enable_drefs", "0", "-use_absolute_path", "0"]
                    ),
                    "-i",
                    str(snapshot),
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    "-t",
                    "7200",
                    "-fs",
                    str(MAX_AUDIO),
                    str(audio),
                ],
                timeout=120,
                maximum=65536,
            )
            if (
                not audio.is_file()
                or audio.is_symlink()
                or not 44 < audio.stat().st_size <= MAX_AUDIO
            ):
                raise OfflineError("MEDIA_INVALID")
            # Do not execute with an asset changed after readiness was established.
            if model_identity(self.model_path) != capability.model_identity:
                raise OfflineError("MODEL_CHANGED")
            raw = run_bounded(
                self._command(
                    "--transcribe", str(audio), "--model", str(self.model_path)
                ),
                timeout=self.timeout,
                env=self._env(),
            )
            if model_identity(self.model_path) != capability.model_identity:
                raise OfflineError("MODEL_CHANGED")
            provenance = json.dumps(
                {
                    "contract": CONTRACT,
                    "executor": capability.executor,
                    "runtime": {"runtime": "mlx-whisper", "version": "0.4.3"},
                    "model": capability.model_identity,
                    "profile": PROFILE,
                    "language_mode": "auto-source",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            return self.validate_result(
                raw, duration_seconds=duration_seconds, provenance=provenance
            )
