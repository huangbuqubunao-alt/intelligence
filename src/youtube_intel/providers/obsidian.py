"""Fail-closed, temporary-Vault-safe Obsidian video-note persistence."""

from __future__ import annotations

import hashlib
import os
import secrets
import stat
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Protocol

import yaml  # type: ignore[import-untyped]

from youtube_intel.domain import (
    AnalysisOutcome,
    AppError,
    ErrorCode,
    KnowledgeSink,
    NoteKind,
    NoteRef,
    PipelineStatus,
    ProcessingStage,
    ScoringOutcome,
    TranscriptArtifact,
    VideoMetadata,
    WeeklyReportInput,
)
from youtube_intel.notes import (
    NoteRenderingError,
    RenderedVideoNote,
    is_video_note_candidate,
    render_video_note,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    StorageRoot,
)

_MAX_EXISTING_NOTE_BYTES = 5 << 20
_MANAGED_START = "<!-- youtube-intel:managed:start:v1 -->\n"
_MANAGED_END = "<!-- youtube-intel:managed:end:v1 -->\n"
_USER_START = "<!-- youtube-intel:user:start:v1 -->\n"
_USER_END = "<!-- youtube-intel:user:end:v1 -->\n"
_VIDEO_NOTE_PRODUCER_VERSION = "obsidian-note-v1"


class _NoteRepository(Protocol):
    def get_video(self, video_id: str) -> object: ...

    def get_artifact_by_key(self, artifact_key: str) -> object | None: ...

    def complete_stage(
        self,
        *,
        job_id: str,
        owner: str,
        video_id: str,
        expected_status: PipelineStatus,
        target_status: PipelineStatus,
        pipeline_version: str,
        artifacts: tuple[ArtifactWrite, ...],
        provider_call: None,
        now: datetime,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class NoteWriteContext:
    job_id: str
    owner: str
    pipeline_version: str

    def __post_init__(self) -> None:
        if not all(value.strip() == value and value for value in (self.job_id, self.owner, self.pipeline_version)):
            raise ValueError("note write context values must be non-empty without surrounding whitespace")


class NotePersistenceError(Exception):
    """Safe note-writing failure that deliberately excludes filesystem detail."""

    def __init__(self, error: AppError) -> None:
        self.error = error
        super().__init__(error.message)


@dataclass(frozen=True, slots=True)
class _ExistingFile:
    content: bytes
    device: int
    inode: int


class ObsidianNoteSink(KnowledgeSink):
    """Persist one managed note through an anchored directory file descriptor."""

    def __init__(
        self,
        *,
        vault_root: Path,
        vault_subdir: str,
        repository: _NoteRepository,
        context: NoteWriteContext,
    ) -> None:
        self._vault_root = vault_root
        self._vault_subdir = _safe_subdir(vault_subdir)
        self._repository = repository
        self._context = context

    def _upsert_video_note(
        self,
        *,
        video: VideoMetadata,
        transcript: TranscriptArtifact,
        scoring: ScoringOutcome,
        analysis: AnalysisOutcome,
        processed_at: datetime,
        pipeline_version: str,
    ) -> NoteRef:
        try:
            if pipeline_version != self._context.pipeline_version:
                raise _failure(ErrorCode.CONFIG_INVALID, "note pipeline version does not match the job", video.video_id)
            current = self._repository.get_video(video.video_id)
            status = getattr(current, "pipeline_status", None)
            if status in {PipelineStatus.NOTE_WRITTEN, PipelineStatus.COMPLETE}:
                return self._verify_existing(self._artifact_relative_path(video.video_id), video.video_id)
            if status is not PipelineStatus.ANALYSIS_READY:
                raise _failure(ErrorCode.INVALID_RESPONSE, "note write job is not eligible", video.video_id)
            rendered = render_video_note(
                video=video,
                transcript=transcript,
                scoring=scoring,
                analysis=analysis,
                processed_at=processed_at,
                pipeline_version=pipeline_version,
            )
            ref = self._write_or_verify(rendered, video.video_id)
            self._repository.complete_stage(
                job_id=self._context.job_id,
                owner=self._context.owner,
                video_id=video.video_id,
                expected_status=PipelineStatus.ANALYSIS_READY,
                target_status=PipelineStatus.NOTE_WRITTEN,
                pipeline_version=pipeline_version,
                artifacts=(self._artifact(ref, video.video_id),),
                provider_call=None,
                now=processed_at,
            )
            return ref
        except NotePersistenceError:
            raise
        except NoteRenderingError:
            raise _failure(ErrorCode.CONFIG_INVALID, "note template or identity is invalid", video.video_id) from None
        except (OSError, UnicodeError, yaml.YAMLError):
            raise _failure(ErrorCode.LOCAL_RESOURCE, "note persistence failed", video.video_id) from None
        except Exception:
            raise _failure(ErrorCode.LOCAL_RESOURCE, "note stage could not be committed", video.video_id) from None

    def upsert_weekly_report(self, report: WeeklyReportInput) -> NoteRef:
        """TASK-011 owns weekly-report persistence and its state semantics."""
        del report
        raise NotImplementedError("weekly report persistence is not implemented by TASK-009")

    def _artifact(self, ref: NoteRef, video_id: str) -> ArtifactWrite:
        artifact_key = f"video-note/{self._context.pipeline_version}/{video_id}"
        return ArtifactWrite(
            artifact_id="video-note-" + hashlib.sha256((artifact_key + ref.content_hash).encode()).hexdigest(),
            artifact_key=artifact_key,
            video_id=video_id,
            job_id=self._context.job_id,
            kind=ArtifactKind.VIDEO_NOTE,
            storage_root=StorageRoot.VAULT,
            relative_path=ref.relative_path,
            content_hash=ref.content_hash,
            provider=None,
            model=None,
            producer_version=_VIDEO_NOTE_PRODUCER_VERSION,
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        )

    def _artifact_relative_path(self, video_id: str) -> str | None:
        artifact = self._repository.get_artifact_by_key(
            f"video-note/{self._context.pipeline_version}/{video_id}"
        )
        if artifact is None:
            return None
        relative_path = getattr(artifact, "relative_path", None)
        if (
            getattr(artifact, "video_id", None) != video_id
            or getattr(artifact, "kind", None) is not ArtifactKind.VIDEO_NOTE
            or getattr(artifact, "storage_root", None) is not StorageRoot.VAULT
            or getattr(artifact, "deleted_at", None) is not None
            or not isinstance(relative_path, str)
            or len(relative_path.split("/")) != 2
            or not relative_path.startswith("Videos/")
            or not is_video_note_candidate(relative_path.removeprefix("Videos/"), video_id)
        ):
            raise _failure(ErrorCode.INVALID_RESPONSE, "video note artifact is invalid", video_id)
        return relative_path

    def _verify_existing(self, relative_path: str | None, video_id: str) -> NoteRef:
        content = self._read_existing(relative_path, video_id)
        if relative_path is None:
            raise _failure(ErrorCode.INVALID_RESPONSE, "completed note artifact is missing", video_id)
        return NoteRef(
            kind=NoteKind.VIDEO,
            relative_path=relative_path,
            content_hash=hashlib.sha256(content).hexdigest(),
        )

    def _write_or_verify(self, rendered: RenderedVideoNote, video_id: str) -> NoteRef:
        root_fd, subdir_fd, videos_fd = self._open_videos_dir()
        try:
            artifact_path = self._artifact_relative_path(video_id)
            filename = self._candidate_filename(
                videos_fd,
                video_id,
                expected_filename=(
                    None if artifact_path is None else artifact_path.removeprefix("Videos/")
                ),
            )
            if artifact_path is not None and filename is None:
                raise _failure(ErrorCode.INVALID_RESPONSE, "managed note is missing", video_id)
            rendered = replace(
                rendered,
                relative_path=rendered.relative_path if filename is None else "Videos/" + filename,
            )
            filename = rendered.relative_path.removeprefix("Videos/")
            existing = _read_regular_file(videos_fd, filename)
            desired = rendered.content.encode("utf-8")
            if existing is not None:
                desired = _merge_user_region(
                    existing=existing.content,
                    rendered=desired,
                    video_id=video_id,
                )
            if existing is None or existing.content != desired:
                _atomic_replace(videos_fd, filename, desired, expected=existing)
            self._verify_directory_chain(root_fd, subdir_fd, videos_fd)
            return NoteRef(
                kind=NoteKind.VIDEO,
                relative_path=rendered.relative_path,
                content_hash=hashlib.sha256(desired).hexdigest(),
            )
        finally:
            os.close(videos_fd)
            os.close(subdir_fd)
            os.close(root_fd)

    def _read_existing(self, relative_path: str | None, video_id: str) -> bytes:
        root_fd, subdir_fd, videos_fd = self._open_videos_dir(create_videos=False)
        try:
            filename = self._candidate_filename(
                videos_fd,
                video_id,
                expected_filename=(
                    None if relative_path is None else relative_path.removeprefix("Videos/")
                ),
            )
            if filename is None:
                raise _failure(ErrorCode.INVALID_RESPONSE, "completed note is missing", video_id)
            content = _read_regular_file(videos_fd, filename)
            if content is None:
                raise _failure(ErrorCode.INVALID_RESPONSE, "completed note is missing", video_id)
            _validate_managed_note(content.content, video_id)
            return content.content
        finally:
            os.close(videos_fd)
            os.close(subdir_fd)
            os.close(root_fd)

    @staticmethod
    def _candidate_filename(
        videos_fd: int,
        video_id: str,
        *,
        expected_filename: str | None,
    ) -> str | None:
        candidates = sorted(
            name for name in os.listdir(videos_fd) if is_video_note_candidate(name, video_id)
        )
        if len(candidates) > 1:
            raise _failure(ErrorCode.INVALID_RESPONSE, "multiple notes claim this video", video_id)
        if not candidates:
            return None
        candidate = candidates[0]
        if expected_filename is not None and candidate != expected_filename:
            raise _failure(ErrorCode.INVALID_RESPONSE, "managed note identity conflicts", video_id)
        return candidate

    def _open_videos_dir(self, *, create_videos: bool = True) -> tuple[int, int, int]:
        if not self._vault_root.is_absolute():
            raise _failure(ErrorCode.CONFIG_INVALID, "vault root must be absolute", None)
        root_fd = _open_directory(self._vault_root)
        try:
            subdir_fd = root_fd
            for part in self._vault_subdir.parts:
                next_fd = _open_directory_at(subdir_fd, part)
                if subdir_fd != root_fd:
                    os.close(subdir_fd)
                subdir_fd = next_fd
            try:
                videos_fd = _open_directory_at(subdir_fd, "Videos")
            except FileNotFoundError:
                if not create_videos:
                    raise
                os.mkdir("Videos", mode=0o700, dir_fd=subdir_fd)
                videos_fd = _open_directory_at(subdir_fd, "Videos")
            return root_fd, subdir_fd, videos_fd
        except Exception:
            os.close(root_fd)
            raise

    def _verify_directory_chain(self, root_fd: int, subdir_fd: int, videos_fd: int) -> None:
        reopened = self._open_videos_dir(create_videos=False)
        try:
            expected = tuple((os.fstat(fd).st_dev, os.fstat(fd).st_ino) for fd in (root_fd, subdir_fd, videos_fd))
            actual = tuple((os.fstat(fd).st_dev, os.fstat(fd).st_ino) for fd in reopened)
            if actual != expected:
                raise _failure(ErrorCode.INVALID_RESPONSE, "vault directory changed during note write", None)
        finally:
            for fd in reversed(reopened):
                os.close(fd)


def _safe_subdir(value: str) -> PurePosixPath:
    if not value or value.strip() != value or "\\" in value or "\x00" in value:
        raise ValueError("vault subdirectory is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(
        part in {"", ".", ".."} or (len(part) >= 2 and part[0].isalpha() and part[1] == ":")
        for part in path.parts
    ):
        raise ValueError("vault subdirectory is invalid")
    return path


def _open_directory(path: Path) -> int:
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise _failure(ErrorCode.INVALID_RESPONSE, "vault directory is unsafe", None)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        raise _failure(ErrorCode.INVALID_RESPONSE, "vault directory is unsafe", None)
    return fd


def _open_directory_at(parent_fd: int, name: str) -> int:
    st = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise _failure(ErrorCode.INVALID_RESPONSE, "vault directory is unsafe", None)
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        raise _failure(ErrorCode.INVALID_RESPONSE, "vault directory is unsafe", None)
    return fd


def _read_regular_file(directory_fd: int, filename: str) -> _ExistingFile | None:
    try:
        st = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise _failure(ErrorCode.INVALID_RESPONSE, "managed note is unsafe", None)
    fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
    try:
        content = _read_limited(fd)
        after = os.fstat(fd)
        if (st.st_dev, st.st_ino) != (after.st_dev, after.st_ino):
            raise _failure(ErrorCode.INVALID_RESPONSE, "managed note changed during read", None)
        return _ExistingFile(content=content, device=after.st_dev, inode=after.st_ino)
    finally:
        os.close(fd)


def _read_limited(fd: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(fd, 64 * 1024)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > _MAX_EXISTING_NOTE_BYTES:
            raise _failure(ErrorCode.LOCAL_RESOURCE, "managed note exceeds the resource limit", None)
        chunks.append(chunk)


def _merge_user_region(*, existing: bytes, rendered: bytes, video_id: str) -> bytes:
    _validate_managed_note(existing, video_id)
    user_start = existing.index(_USER_START.encode()) + len(_USER_START)
    user_end = existing.index(_USER_END.encode())
    rendered_start = rendered.index(_USER_START.encode()) + len(_USER_START)
    rendered_end = rendered.index(_USER_END.encode())
    return rendered[:rendered_start] + existing[user_start:user_end] + rendered[rendered_end:]


def _validate_managed_note(content: bytes, video_id: str) -> None:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise _failure(ErrorCode.INVALID_RESPONSE, "managed note is not valid UTF-8", video_id) from None
    if "\r" in text:
        raise _failure(ErrorCode.INVALID_RESPONSE, "managed note markers are invalid", video_id)
    markers = (_MANAGED_START, _MANAGED_END, _USER_START, _USER_END)
    if any(text.count(marker) != 1 for marker in markers):
        raise _failure(ErrorCode.INVALID_RESPONSE, "managed note markers are invalid", video_id)
    positions = [text.index(marker) for marker in markers]
    if positions != sorted(positions):
        raise _failure(ErrorCode.INVALID_RESPONSE, "managed note markers are invalid", video_id)
    if not text.startswith("---\n"):
        raise _failure(ErrorCode.INVALID_RESPONSE, "managed note frontmatter is invalid", video_id)
    end = text.find("---\n", 4)
    if end < 0:
        raise _failure(ErrorCode.INVALID_RESPONSE, "managed note frontmatter is invalid", video_id)
    frontmatter = yaml.safe_load(text[4:end])
    if not isinstance(frontmatter, dict) or frontmatter.get("video_id") != video_id:
        raise _failure(ErrorCode.INVALID_RESPONSE, "managed note provenance is invalid", video_id)


def _atomic_replace(
    directory_fd: int,
    filename: str,
    content: bytes,
    *,
    expected: _ExistingFile | None,
) -> None:
    temporary = f".youtube-intel-{secrets.token_hex(16)}.tmp"
    fd: int | None = None
    try:
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        _write_all(fd, content)
        os.fsync(fd)
        os.close(fd)
        fd = None
        verified = _read_regular_file(directory_fd, temporary)
        if verified is None or verified.content != content:
            raise _failure(ErrorCode.LOCAL_RESOURCE, "temporary note verification failed", None)
        current = _read_regular_file(directory_fd, filename)
        if expected is None:
            if current is not None:
                raise _failure(ErrorCode.INVALID_RESPONSE, "managed note changed during write", None)
        elif (
            current is None
            or (current.device, current.inode) != (expected.device, expected.inode)
            or current.content != expected.content
        ):
            raise _failure(ErrorCode.INVALID_RESPONSE, "managed note changed during write", None)
        os.replace(temporary, filename, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass


def _write_all(fd: int, content: bytes) -> None:
    offset = 0
    while offset < len(content):
        written = os.write(fd, content[offset:])
        if written <= 0:
            raise _failure(ErrorCode.LOCAL_RESOURCE, "temporary note write failed", None)
        offset += written


def _failure(code: ErrorCode, message: str, video_id: str | None) -> NotePersistenceError:
    return NotePersistenceError(
        AppError(
            code=code,
            message=message,
            retryable=code in {ErrorCode.LOCAL_RESOURCE, ErrorCode.PERMISSION_DENIED},
            video_id=video_id,
            stage=ProcessingStage.NOTE_WRITE,
        )
    )
