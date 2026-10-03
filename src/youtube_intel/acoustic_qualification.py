"""Machine-only acoustic receipts. Settings cannot seal or replace evidence.

An engineering runner seals measured evidence, not a user-selectable PASS boolean.
The private seal and hardware binding prevent ordinary configuration edits or
portable DATA restores from creating qualification. This is not protection against
a machine owner executing arbitrary Python or replacing application code.
"""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import importlib.metadata
import inspect
import json
import math
import os
import platform
import re
import subprocess
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from youtube_intel.source_authority import read_managed

REPOSITORY = "mlx-community/whisper-large-v3-turbo"
POLICY = "private-acoustic-gates-v1"
REQUIRED = frozenset({"english-clean", "mandarin-clean", "mixed-clean", "very-short", "medium", "designed-pauses", "mild-noise", "english-video"})


class SampleResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    name: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    error_rate: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    duration_seconds: float = Field(gt=0, allow_inf_nan=False)
    processing_seconds: float = Field(gt=0, allow_inf_nan=False)
    completed: bool
    timestamps_valid: bool
    coverage_passed: bool
    no_omission: bool


class QualificationEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    corpus_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    samples: tuple[SampleResult, ...]
    offline: bool
    cloud_dispatches: int = Field(ge=0)
    source_uploads: int = Field(ge=0)


def evaluate(evidence: QualificationEvidence) -> Literal["PASSED", "FAILED"]:
    names = [s.name for s in evidence.samples]
    if (not REQUIRED <= set(names) or len(names) != len(set(names)) or not evidence.offline or evidence.cloud_dispatches or evidence.source_uploads):
        return "FAILED"
    for sample in evidence.samples:
        if (not sample.completed or not sample.timestamps_valid or not sample.coverage_passed or not sample.no_omission or not math.isfinite(sample.processing_seconds) or not 0 < sample.processing_seconds < 1800):
            return "FAILED"
        if sample.name == "very-short" and not 3 <= sample.duration_seconds <= 10:
            return "FAILED"
        if sample.name == "medium" and sample.duration_seconds < 120:
            return "FAILED"
        limit = 0.20 if sample.name == "mixed-clean" else 0.15
        if sample.error_rate is None or not math.isfinite(sample.error_rate) or sample.error_rate > limit:
            return "FAILED"
    return "PASSED"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def machine_binding(key: bytes) -> str:
    # Stable hardware UUID is never stored or returned; only a private keyed digest.
    result = subprocess.run(["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True, timeout=5, check=True)
    match = re.search(rb'"IOPlatformUUID"\s*=\s*"([A-Fa-f0-9-]+)"', result.stdout)
    if match is None:
        raise ValueError("machine binding unavailable")
    return hmac.new(key, match[1], "sha256").hexdigest()


def current_tuple(model: Path, identity: str, origin: dict[str, JsonValue]) -> dict[str, JsonValue]:
    from youtube_intel.offline_transcription import (
        CONTRACT,
        PROFILE,
        MlxTimedExecutor,
        media_tool,
        model_identity,
        validate_result,
    )
    from youtube_intel.state import TimedTranscriptCueWrite
    if origin.get("repository") != REPOSITORY or origin.get("phase8_model_identity") != identity:
        raise ValueError("model origin does not match sealed assets")
    revision = origin.get("revision")
    if not isinstance(revision, str) or re.fullmatch(r"[a-f0-9]{40}", revision) is None:
        raise ValueError("exact model revision required")
    manifest = dict(origin)
    expected_digest = manifest.pop("manifest_sha256", None)
    if hashlib.sha256(canonical(manifest)).hexdigest() != expected_digest:
        raise ValueError("origin manifest changed")
    if not (model / "weights.safetensors").is_file():
        raise ValueError("complete authorized model required")
    tools: dict[str, JsonValue] = {}
    for name in ("ffmpeg", "ffprobe"):
        executable = media_tool(name)
        if executable is None:
            raise ValueError("preprocessing tool unavailable")
        with Path(executable).open("rb") as stream:
            tools[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    hardware = subprocess.run(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string", "hw.memsize"], capture_output=True, text=True, check=True, timeout=5).stdout.splitlines()
    hardware_values: list[JsonValue] = [line for line in hardware]
    return {
        "qualification_policy": POLICY,
        "executor_contract": CONTRACT,
        "executor": "mlx-whisper-timed-v1",
        "mlx_whisper": importlib.metadata.version("mlx-whisper"),
        "mlx": importlib.metadata.version("mlx"),
        "model_repository": origin["repository"],
        "model_revision": origin["revision"],
        "model_digest": identity,
        "model_manifest": origin["manifest_sha256"],
        "decoding_profile": {"name": PROFILE, "task": "transcribe", "language": None, "temperature": 0.0, "compression_ratio_threshold": 2.4, "logprob_threshold": -1.0, "no_speech_threshold": 0.6, "initial_prompt": None, "word_timestamps": False, "condition_on_previous_text": True, "fp16": True, "beam_size": None, "best_of": None},
        "transcript_contract": "source-transcript-provenance-v2-exact-boundary-spaces-v2",
        "timestamp_policy": "finite-monotonic-nonoverlap-positive-ms-duration-plus1s-v1",
        "preprocessing_profile": "first-audio-mono16k-pcm-s16le-max2h-v1",
        "platform": {"system": platform.system(), "machine": platform.machine(), "os": platform.mac_ver()[0], "python": platform.python_version(), "hardware": hardware_values},
        "preprocessing_tools": tools,
        # Bind implementation changes even when a developer forgets a version bump.
        "implementation": {
            **{name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ("offline_whisper_worker.py", "local_content.py", "source_authority.py", "acoustic_scoring.py", "acoustic_qualification.py")},
            **{function.__qualname__: hashlib.sha256(inspect.getsource(function).encode()).hexdigest() for function in (MlxTimedExecutor.transcribe, MlxTimedExecutor._command, MlxTimedExecutor._env, validate_result, model_identity, TimedTranscriptCueWrite)},
        },
    }


def _key(root: Path) -> bytes:
    path = root / "qualification.seal"
    info = path.lstat()
    if info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise ValueError("private machine seal required")
    key = read_managed(root, path.name, maximum=32)
    if len(key) != 32:
        raise ValueError("invalid machine seal")
    return key


def _write(root: Path, name: str, data: bytes) -> None:
    if root.resolve() != root or root.is_symlink():
        raise ValueError("private regular storage required")
    temporary = root / (uuid.uuid4().hex + ".tmp")
    try:
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, root / name)
    finally:
        temporary.unlink(missing_ok=True)


def seal_record(root: Path, identity: dict[str, JsonValue], *, evidence: QualificationEvidence | None, audit: bytes | None) -> None:
    """Engineering-only writer; no API/Settings route calls this function."""
    root = root.absolute()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.resolve() != root:
        raise ValueError("unsafe qualification storage")
    if not (root / "qualification.seal").exists():
        with os.fdopen(os.open(root / "qualification.seal", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as stream:
            stream.write(os.urandom(32))
            stream.flush()
            os.fsync(stream.fileno())
    key = _key(root)
    body = {"version": POLICY, "tuple": identity, "machine_binding": machine_binding(key), "state": "RUNNING" if evidence is None else evaluate(evidence), "evidence": None if evidence is None else evidence.model_dump(mode="json"), "audit_sha256": None}
    if evidence is not None:
        if audit is None or not 0 < len(audit) <= 4 * 1024 * 1024:
            raise ValueError("bounded immutable audit required")
        digest = hashlib.sha256(audit).hexdigest()
        directory = root / "qualification"
        directory.mkdir(mode=0o700, exist_ok=True)
        _write(directory, digest + ".json", audit)
        body["audit_sha256"] = digest
    record = {"body": body, "signature": hmac.new(key, canonical(body), "sha256").hexdigest()}
    _write(root, "qualification.json", canonical(record))


def qualification_status(root: Path, identity: dict[str, JsonValue] | None) -> dict[str, object]:
    if not (root / "qualification.json").exists():
        return {"state": "NOT_TESTED", "production_eligible": False}
    try:
        key = _key(root)
        record = json.loads(read_managed(root, "qualification.json", maximum=1024 * 1024))
        body = record["body"]
        if not hmac.compare_digest(record["signature"], hmac.new(key, canonical(body), "sha256").hexdigest()):
            raise ValueError("receipt seal invalid")
        if body["version"] != POLICY or body["tuple"] != identity or body["machine_binding"] != machine_binding(key):
            raise ValueError("qualification tuple changed")
        state = body["state"]
        if state == "RUNNING":
            fd = os.open(root / "qualification.lock", os.O_RDWR | os.O_NOFOLLOW)
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    state = "FAILED"  # interrupted engineering run cannot stay RUNNING
                except BlockingIOError:
                    pass
            finally:
                os.close(fd)
        else:
            audit = read_managed(root, "qualification/" + body["audit_sha256"] + ".json", maximum=4 * 1024 * 1024)
            if hashlib.sha256(audit).hexdigest() != body["audit_sha256"]:
                raise ValueError("audit changed")
            evidence = QualificationEvidence.model_validate_json(canonical(body["evidence"]))
            if state != evaluate(evidence):
                raise ValueError("verdict changed")
        return {"state": state, "production_eligible": state == "PASSED", "identity": hashlib.sha256(canonical(body)).hexdigest()}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return {"state": "STALE", "production_eligible": False}
