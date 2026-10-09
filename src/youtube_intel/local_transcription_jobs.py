"""One task-owned local heavy job, existing durable jobs and Phase 7 authority."""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import tempfile
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from youtube_intel.local_content import LocalContentProvider, LocalImportError
from youtube_intel.offline_transcription import (
    MlxTimedExecutor,
    OfflineError,
    TranscriptionCapability,
    TranscriptionExecutor,
    media_tool,
)
from youtube_intel.source_authority import (
    MAX_MEDIA_BYTES,
    open_managed,
    read_managed,
    sha256,
    stage_stream,
    verify_source,
)
from youtube_intel.state import SQLiteStateRepository, format_utc_datetime

PREFIX = "offline-timed-v1:"
SAFE_FAILURES = frozenset(
    {
        "EXECUTOR_FAILED",
        "EXECUTOR_TIMEOUT",
        "EXECUTOR_OUTPUT_LIMIT",
        "TRANSCRIPT_INVALID",
        "RUNTIME_UNAVAILABLE",
        "MODEL_MISSING",
        "MODEL_INVALID",
        "MODEL_CHANGED",
        "EXECUTOR_INCOMPATIBLE",
        "MEDIA_TOOL_UNAVAILABLE",
        "MEDIA_INVALID",
        "LOCAL_INVALID_MEDIA",
        "LOCAL_SOURCE_UNTRUSTED",
        "SOURCE_CHANGED",
        "EXECUTOR_IDENTITY_CHANGED",
        "INTERRUPTED",
        "LOCAL_STORAGE_FAILED",
        "ACOUSTIC_NOT_QUALIFIED",
    }
)


class LocalTranscriptionJobs:
    def __init__(
        self,
        repository: SQLiteStateRepository,
        data_root: Path,
        *,
        executor: TranscriptionExecutor | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.data_root = data_root.absolute()
        self.provider = LocalContentProvider(repository, self.data_root, now=now)
        self.now = now or (lambda: datetime.now(UTC))
        # Machine configuration and temporary derivatives are outside DATA archives.
        self.machine_root = self.data_root.parent / ".local-transcription"
        self.machine_root.mkdir(mode=0o700, exist_ok=True)
        if (
            self.machine_root.is_symlink()
            or self.machine_root.resolve() != self.machine_root
        ):
            raise OfflineError("LOCAL_STORAGE_FAILED")
        self._mutex = threading.RLock()
        self._capability = TranscriptionCapability(
            "PENDING", reason_code="CAPABILITY_CHECKING"
        )
        self._checking = False
        self._injected = executor is not None
        path = None
        try:
            config = json.loads(
                read_managed(self.machine_root, "model.json", maximum=16384)
            )
            if (
                isinstance(config, dict)
                and set(config) == {"model_path"}
                and isinstance(config["model_path"], str)
            ):
                path = Path(config["model_path"])
        except (OSError, ValueError):
            pass
        self.executor: TranscriptionExecutor = executor or MlxTimedExecutor(
            model_path=path, temporary_root=self.machine_root / "temporary"
        )
        self._recover()
        try:
            self.refresh()
        except OfflineError:
            pass  # a live application worker owns the shared machine slot

    def _slot(self) -> int | None:
        if (
            self.machine_root.resolve() != self.machine_root
            or self.machine_root.is_symlink()
        ):
            raise OfflineError("LOCAL_STORAGE_FAILED")
        fd = os.open(
            self.machine_root / "worker.lock",
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            os.close(fd)
            return None

    @staticmethod
    def _release(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    def _recover(self) -> None:
        fd = self._slot()
        if fd is None:
            return  # another application process actually owns the worker
        try:
            for directory in (self.machine_root, self.machine_root / "temporary"):
                if (
                    not directory.is_dir()
                    or directory.is_symlink()
                    or directory.resolve() != directory
                ):
                    continue
                with os.scandir(directory) as entries:
                    for index, entry in enumerate(entries):
                        if index >= 128:
                            break
                        if re.fullmatch(
                            r"(?:source-)?attempt-[a-z0-9_]{8}", entry.name
                        ) and entry.is_dir(follow_symlinks=False):
                            shutil.rmtree(
                                entry.path
                            )  # exact application-owned stale attempt directory only
            timestamp = format_utc_datetime(self.now())
            with self.repository._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "UPDATE job_attempts SET finished_at=?,outcome='LEASE_EXPIRED',error_code='INTERRUPTED',error_message='Local transcription was interrupted.' WHERE finished_at IS NULL AND job_id IN (SELECT job_id FROM jobs WHERE pipeline_version LIKE ? AND status IN ('PENDING','RUNNING','RETRY_PENDING'))",
                    (timestamp, PREFIX + "%"),
                )
                connection.execute(
                    "UPDATE jobs SET status='FAILED_FINAL',lease_owner=NULL,lease_until=NULL,finished_at=?,updated_at=?,last_error_code='INTERRUPTED',last_error_message='Local transcription was interrupted.' WHERE pipeline_version LIKE ? AND status IN ('PENDING','RUNNING','RETRY_PENDING')",
                    (timestamp, timestamp, PREFIX + "%"),
                )
        finally:
            self._release(fd)

    def refresh(self) -> None:
        with self._mutex:
            if self._checking:
                return
            fd = self._slot()
            if fd is None:
                raise OfflineError("TRANSCRIPTION_BUSY")
            self._checking = True
            self._capability = TranscriptionCapability(
                "PENDING", reason_code="CAPABILITY_CHECKING"
            )
            selected = self.executor

        def check() -> None:
            try:
                capability = selected.capability()
                if capability.state == "READY" and (
                    not capability.executor_compatible
                    or not capability.runtime_available
                    or not capability.model_present
                    or not capability.execution_identity
                    or not capability.model_identity
                ):
                    capability = TranscriptionCapability(
                        "UNSUPPORTED", reason_code="EXECUTOR_INCOMPATIBLE"
                    )
                with self._mutex:
                    self._capability = capability
            except Exception:
                with self._mutex:
                    self._capability = TranscriptionCapability(
                        "RUNTIME_UNAVAILABLE", reason_code="RUNTIME_UNAVAILABLE"
                    )
            finally:
                self._release(fd)
                with self._mutex:
                    self._checking = False

        threading.Thread(
            target=check, name="local-transcription-capability", daemon=True
        ).start()

    def configure(self, path: str | None) -> None:
        if self._injected:
            raise OfflineError("EXECUTOR_INCOMPATIBLE")
        if path is not None and (
            not path
            or len(path) > 4096
            or any(ord(c) < 32 for c in path)
            or not Path(path).is_absolute()
            or Path(path).absolute().resolve() != Path(path).absolute()
        ):
            raise OfflineError("MODEL_INVALID")
        with self._mutex:
            fd = self._slot()
            if fd is None:
                raise OfflineError("TRANSCRIPTION_BUSY")
            temporary = self.machine_root / (uuid.uuid4().hex + ".tmp")
            try:
                payload = json.dumps({"model_path": path}).encode()
                with os.fdopen(
                    os.open(
                        temporary,
                        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                        0o600,
                    ),
                    "wb",
                ) as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.machine_root / "model.json")
                self.executor = MlxTimedExecutor(
                    model_path=None if path is None else Path(path),
                    temporary_root=self.machine_root / "temporary",
                )
            finally:
                temporary.unlink(
                    missing_ok=True
                )  # only the task-owned configuration staging file
                self._release(fd)
            self.refresh()

    def capability(self) -> dict[str, object]:
        with self._mutex:
            capability = self._capability.as_dict()
        capability.update(
            media_tools_available=all(media_tool(n) for n in ("ffmpeg", "ffprobe")),
            checking=self._checking,
            production_eligible=capability["production_eligible"] is True,
        )
        if capability["state"] == "READY" and not capability["media_tools_available"]:
            capability.update(
                state="RUNTIME_UNAVAILABLE", reason_code="MEDIA_TOOL_UNAVAILABLE"
            )
        return capability

    def _eligible(self, capability: dict[str, object]) -> bool:
        return capability["state"] == "READY" and (self._injected or capability["production_eligible"] is True)

    def status(self, content_id: str) -> dict[str, object]:
        self._recover()  # reconcile an owner that exited after another app instance started
        with self.repository._connect() as connection:
            source = verify_source(self.repository, connection, content_id)
            if source is None:
                raise OfflineError("LOCAL_SOURCE_UNTRUSTED")
            if source["media_kind"] == "TEXT":
                return {"status": "NOT_REQUIRED", "retry_available": False}
            job = connection.execute(
                "SELECT * FROM jobs WHERE video_id=? AND pipeline_version LIKE ? ORDER BY created_at DESC,rowid DESC LIMIT 1",
                (content_id, PREFIX + "%"),
            ).fetchone()
        capability = self.capability()
        if source["status"] == "READY":
            complete = (
                self.repository.current_local_summary_pointer(content_id) is not None
            )
            running = job is not None and job["status"] == "RUNNING"
            return {
                "status": "READY"
                if complete
                else "RUNNING"
                if running
                else "INTERRUPTED",
                "retry_available": not complete and not running,
                "summary_recovery": not complete and not running,
                "attempt_id": None if job is None else job["job_id"],
                "capability": capability,
            }
        eligible = self._eligible(capability)
        state = "PENDING" if eligible else "QUALIFICATION_REQUIRED" if capability["state"] == "READY" else capability["state"]
        code = None
        if job is not None:
            if job["status"] in {"PENDING", "RUNNING"}:
                state = job["status"]
            elif job["status"] == "FAILED_FINAL":
                code = (
                    job["last_error_code"]
                    if job["last_error_code"] in SAFE_FAILURES
                    else "EXECUTOR_FAILED"
                )
                state = "INTERRUPTED" if code == "INTERRUPTED" else "FAILED"
        return {
            "status": state,
            "last_failure_category": code,
            "attempt_id": None if job is None else job["job_id"],
            "retry_available": eligible
            and state not in {"PENDING", "RUNNING"},
            "start_available": eligible and job is None,
            "capability": capability,
        }

    def start(self, content_id: str, execution_identity: str) -> dict[str, object]:
        with self._mutex:
            with self.repository._connect() as connection:
                source = verify_source(self.repository, connection, content_id)
                if source is None:
                    raise OfflineError("LOCAL_SOURCE_UNTRUSTED")
                if source["media_kind"] == "TEXT":
                    raise OfflineError("LOCAL_NOT_MEDIA")
                if source["status"] == "READY":
                    self.provider._finish_summary(
                        content_id, self.now(), source["language"]
                    )
                    return self.status(content_id)
                active = connection.execute(
                    "SELECT job_id FROM jobs WHERE video_id=? AND pipeline_version LIKE ? AND status IN ('PENDING','RUNNING','RETRY_PENDING')",
                    (content_id, PREFIX + "%"),
                ).fetchone()
                if active is not None:
                    return self.status(content_id)
                capability = self._capability
                if not self._eligible(self.capability()):
                    raise OfflineError(
                        "ACOUSTIC_NOT_QUALIFIED" if self.capability()["state"] == "READY" else str(
                            self.capability().get("reason_code")
                            or "RUNTIME_UNAVAILABLE"
                        )
                    )
                if execution_identity != capability.execution_identity:
                    raise OfflineError("EXECUTOR_IDENTITY_CHANGED")
                fd = self._slot()
                if fd is None:
                    raise OfflineError("TRANSCRIPTION_BUSY")
                job_id = "local-transcription-" + uuid.uuid4().hex
                timestamp = format_utc_datetime(self.now())
                lease = format_utc_datetime(self.now() + timedelta(seconds=2100))
                try:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        "INSERT INTO jobs(job_id,scope_key,video_id,job_type,target_stage,pipeline_version,status,attempt_count,max_attempts,lease_owner,lease_until,available_at,created_at,updated_at) VALUES(?,?,?,'VIDEO_STAGE','TRANSCRIPT',?,'RUNNING',1,1,?,?,?,?,?)",
                        (
                            job_id,
                            "local-transcription:" + content_id,
                            content_id,
                            PREFIX + execution_identity,
                            job_id,
                            lease,
                            timestamp,
                            timestamp,
                            timestamp,
                        ),
                    )
                except Exception:
                    self._release(fd)
                    raise
            selected = self.executor
            thread = threading.Thread(
                target=self._run,
                args=(job_id, content_id, selected, capability, fd),
                name="local-transcription-worker",
                daemon=True,
            )
            try:
                thread.start()
            except Exception:
                self._finish(job_id, "FAILED_FINAL", "LOCAL_STORAGE_FAILED")
                self._release(fd)
                raise OfflineError("LOCAL_STORAGE_FAILED") from None
            return self.status(content_id)

    def _finish(self, job_id: str, state: str, code: str | None) -> None:
        timestamp = format_utc_datetime(self.now())
        with self.repository._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE job_attempts SET finished_at=?,outcome=?,error_code=?,error_message=? WHERE job_id=? AND finished_at IS NULL",
                (
                    timestamp,
                    state,
                    code,
                    None if code is None else "Local transcription did not complete.",
                    job_id,
                ),
            )
            connection.execute(
                "UPDATE jobs SET status=?,lease_owner=NULL,lease_until=NULL,finished_at=?,updated_at=?,last_error_code=?,last_error_message=? WHERE job_id=?",
                (
                    state,
                    timestamp,
                    timestamp,
                    code,
                    None if code is None else "Local transcription did not complete.",
                    job_id,
                ),
            )

    def _run(
        self,
        job_id: str,
        content_id: str,
        selected: TranscriptionExecutor,
        capability: TranscriptionCapability,
        fd: int,
    ) -> None:
        try:
            with self.repository._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                job = connection.execute(
                    "SELECT * FROM jobs WHERE job_id=? AND status='RUNNING' AND lease_owner=?",
                    (job_id, job_id),
                ).fetchone()
                if job is None:
                    raise OfflineError("INTERRUPTED")
                connection.execute(
                    "INSERT INTO job_attempts(job_id,attempt_number,lease_owner,started_at,lease_until) VALUES(?,1,?,?,?)",
                    (job_id, job_id, job["created_at"], job["lease_until"]),
                )
                source = verify_source(self.repository, connection, content_id)
                if source is None:
                    raise OfflineError("LOCAL_SOURCE_UNTRUSTED")
                artifact = connection.execute(
                    "SELECT relative_path FROM artifacts WHERE artifact_id=?",
                    (source["snapshot_artifact_id"],),
                ).fetchone()
                duration = source["duration_seconds"]
                relative = artifact["relative_path"]
                digest, size = source["source_hash"], source["byte_count"]
                extension = source["format"]
            current = selected.capability()
            if (
                current.state != "READY"
                or current.execution_identity != capability.execution_identity
                or (not self._injected and not current.production_eligible)
            ):
                raise OfflineError("EXECUTOR_IDENTITY_CHANGED")
            if self.machine_root.resolve() != self.machine_root:
                raise OfflineError("LOCAL_STORAGE_FAILED")
            with tempfile.TemporaryDirectory(
                prefix="source-attempt-", dir=self.machine_root
            ) as temporary:
                snapshot = Path(temporary) / ("source" + extension)
                with open_managed(self.data_root, relative, maximum=MAX_MEDIA_BYTES) as input_file:
                    with stage_stream(Path(temporary), input_file, size, maximum=MAX_MEDIA_BYTES) as staged:
                        if staged.digest != digest:
                            raise OfflineError("LOCAL_SOURCE_UNTRUSTED")
                        staged.publish(Path(temporary), snapshot.name)
                transcript = selected.transcribe(snapshot, duration_seconds=duration)
            if (
                sha256(transcript.provenance.encode()) != capability.execution_identity
                or transcript.raw_output is None
            ):
                raise OfflineError("EXECUTOR_IDENTITY_CHANGED")
            # Treat even typed executor results as untrusted; shared raw validation is mandatory.
            from youtube_intel.offline_transcription import validate_result

            validated = validate_result(
                transcript.raw_output,
                duration_seconds=duration,
                provenance=transcript.provenance,
            )
            if validated != transcript:
                raise OfflineError("TRANSCRIPT_INVALID")
            self.provider.accept_transcript(content_id, validated)
            self._finish(job_id, "SUCCEEDED", None)
        except (OfflineError, LocalImportError) as error:
            code = error.code if error.code in SAFE_FAILURES else "EXECUTOR_FAILED"
            self._finish(job_id, "FAILED_FINAL", code)
        except Exception:
            self._finish(job_id, "FAILED_FINAL", "LOCAL_STORAGE_FAILED")
        finally:
            self._release(fd)
