"""Bounded FFmpeg keyframe extraction, 64-bit dHash deduplication, and cue alignment."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import tempfile
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from youtube_intel.offline_transcription import OfflineError, media_tool, run_bounded
from youtube_intel.state import VerifiedTimedTranscriptCue

DEFAULT_KEYFRAME_COUNT = 8
MIN_KEYFRAME_COUNT = 3
MAX_KEYFRAME_COUNT = 12
MAX_FRAME_WIDTH = 960
MAX_SINGLE_FRAME_BYTES = 512 * 1024
MAX_TOTAL_VISION_BYTES = 4 * 1024 * 1024
DHASH_DUP_THRESHOLD = 5
FRAME_ID_PATTERN = re.compile(r"^f\d{2}-\d{1,9}$")

_PTS_TIME_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")
_SCENE_SCORE_RE = re.compile(r"lavfi\.scene_score=([0-9]+(?:\.[0-9]+)?)")


class VisualExtractionError(ValueError):
    """Structured failure during bounded keyframe extraction or visual eligibility checks."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class ExtractedKeyframe:
    frame_index: int
    frame_id: str
    filename: str
    path: Path
    timestamp_ms: int
    timestamp_label: str
    selection_reason: str
    byte_count: int
    sha256: str
    dhash: int


def format_timestamp_label(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def compute_dhash_64(gray_9x8: bytes) -> int:
    """Compute a 64-bit horizontal gradient difference hash from 9x8 8-bit grayscale bytes."""
    if len(gray_9x8) != 72:
        raise ValueError(f"Expected 72 raw gray bytes (9x8), got {len(gray_9x8)}")
    digest = 0
    bit = 0
    for row in range(8):
        row_offset = row * 9
        for col in range(8):
            if gray_9x8[row_offset + col] < gray_9x8[row_offset + col + 1]:
                digest |= 1 << bit
            bit += 1
    return digest


def hamming_distance_64(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def parse_scene_metadata_output(
    raw_output: str,
    *,
    min_gap_seconds: float = 1.5,
) -> list[tuple[float, float]]:
    """Parse ffmpeg `metadata=print:file=-` output into non-overlapping `(ts_sec, score)` cuts."""
    raw_cuts: list[tuple[float, float]] = []
    pending_pts: float | None = None
    for line in raw_output.splitlines():
        pts_m = _PTS_TIME_RE.search(line)
        if pts_m is not None:
            pending_pts = float(pts_m.group(1))
            continue
        score_m = _SCENE_SCORE_RE.search(line)
        if score_m is not None and pending_pts is not None:
            raw_cuts.append((max(0.0, pending_pts), float(score_m.group(1))))
            pending_pts = None

    deduped: list[tuple[float, float]] = []
    for ts_sec, score in sorted(raw_cuts, key=lambda item: item[0]):
        if deduped and (ts_sec - deduped[-1][0]) < min_gap_seconds:
            if score > deduped[-1][1]:
                deduped[-1] = (ts_sec, score)
            continue
        deduped.append((ts_sec, score))
    return deduped


def detect_scene_timestamps(
    ffmpeg_path: str,
    video_path: Path,
    *,
    duration_seconds: float,
    max_frames: int,
) -> list[tuple[float, float]]:
    """Scan video at bounded low fps to detect slide/UI/scene change timestamps."""
    safe_duration = max(1.0, float(duration_seconds))
    if safe_duration <= 120.0:
        sample_fps = "1"
        threshold = 0.18
    elif safe_duration <= 1200.0:
        sample_fps = "0.5"
        threshold = 0.22
    else:
        sample_fps = "0.1"
        threshold = 0.22

    min_gap = max(1.0 if safe_duration <= 15.0 else 1.5, safe_duration / (max_frames * 2.5))
    try:
        raw = run_bounded(
            [
                ffmpeg_path,
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-enable_drefs",
                "0",
                "-use_absolute_path",
                "0",
                "-i",
                str(video_path),
                "-an",
                "-vf",
                f"fps={sample_fps},scale=320:-2,select='gt(scene,{threshold})',metadata=print:file=-",
                "-f",
                "null",
                "-",
            ],
            timeout=60.0 if safe_duration <= 1200.0 else 120.0,
            maximum=2 * 1024 * 1024,
        )
    except OfflineError:
        return []
    return parse_scene_metadata_output(
        raw.decode("utf-8", errors="replace"),
        min_gap_seconds=min_gap,
    )


def select_candidate_timestamps(
    scene_cuts: Sequence[tuple[float, float]],
    *,
    duration_seconds: float,
    target_frames: int,
) -> list[tuple[float, str]]:
    """Merge prioritized scene cuts with uniform temporal coverage anchors."""
    safe_duration = max(0.2, float(duration_seconds))
    max_ts = max(0.0, safe_duration - 0.1)
    min_spacing = max(0.6 if safe_duration <= 12.0 else 1.5, safe_duration / (target_frames * 2.5))

    candidates: list[tuple[float, str, float]] = []
    # Keep top scene-change timestamps first so dedup prefers actual visual transitions.
    ranked_cuts = sorted(scene_cuts, key=lambda item: (-item[1], item[0]))
    for ts_sec, score in ranked_cuts[: max(target_frames * 2, target_frames + 4)]:
        settled_ts = min(max_ts, max(0.0, ts_sec + (0.08 if safe_duration > 2.0 else 0.02)))
        if any(abs(settled_ts - existing[0]) < min_spacing * 0.6 for existing in candidates):
            continue
        candidates.append((settled_ts, "SCENE_CHANGE", score))

    opening_ts = min(max_ts, max(0.0, min(2.0, safe_duration * 0.08)))
    if not any(abs(opening_ts - existing[0]) < min_spacing for existing in candidates):
        candidates.append((opening_ts, "OPENING", 0.5))

    anchor_count = max(target_frames + 2, 6)
    for idx in range(anchor_count):
        ratio = 0.08 + 0.84 * (idx / max(1, anchor_count - 1))
        anchor_ts = min(max_ts, max(0.0, safe_duration * ratio))
        if not any(abs(anchor_ts - existing[0]) < min_spacing for existing in candidates):
            candidates.append((anchor_ts, "UNIFORM", 0.1))

    candidates.sort(key=lambda item: item[0])
    limit = max(target_frames * 2, target_frames + 4)
    return [(ts, reason) for ts, reason, _ in candidates[:limit]]


def _extract_single_frame_jpeg(
    ffmpeg_path: str,
    video_path: Path,
    ts_sec: float,
) -> tuple[bytes, int]:
    try:
        jpeg_bytes = run_bounded(
            [
                ffmpeg_path,
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-enable_drefs",
                "0",
                "-use_absolute_path",
                "0",
                "-ss",
                f"{ts_sec:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-vf",
                f"scale='min({MAX_FRAME_WIDTH},iw)':-2",
                "-q:v",
                "5",
                "-f",
                "image2pipe",
                "-vcodec",
                "mjpeg",
                "pipe:1",
            ],
            timeout=20.0,
            maximum=MAX_SINGLE_FRAME_BYTES,
        )
        gray_bytes = run_bounded(
            [
                ffmpeg_path,
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-enable_drefs",
                "0",
                "-use_absolute_path",
                "0",
                "-ss",
                f"{ts_sec:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-vf",
                "scale=9:8,format=gray",
                "-f",
                "rawvideo",
                "pipe:1",
            ],
            timeout=15.0,
            maximum=1024,
        )
    except OfflineError as err:
        raise VisualExtractionError(
            "VISUAL_EXTRACTION_FAILED",
            f"关键画面截取失败（{err.code}）。",
        ) from err
    if len(jpeg_bytes) < 4 or jpeg_bytes[:2] != b"\xff\xd8":
        raise VisualExtractionError(
            "VISUAL_EXTRACTION_FAILED",
            "截取的视频关键帧不是有效的 JPEG 图像。",
        )
    if len(gray_bytes) != 72:
        raise VisualExtractionError(
            "VISUAL_EXTRACTION_FAILED",
            "未能读取关键帧灰度特征矩阵。",
        )
    return jpeg_bytes, compute_dhash_64(gray_bytes)


def extract_video_keyframes(
    video_path: Path,
    output_dir: Path,
    *,
    duration_seconds: float,
    max_frames: int = DEFAULT_KEYFRAME_COUNT,
) -> list[ExtractedKeyframe]:
    """Extract deduplicated `<=960px` JPEG keyframes atomically into `output_dir`."""
    target_frames = max(MIN_KEYFRAME_COUNT, min(MAX_KEYFRAME_COUNT, int(max_frames)))
    ffmpeg_path = media_tool("ffmpeg")
    if ffmpeg_path is None:
        raise VisualExtractionError(
            "VISUAL_FFMPEG_UNAVAILABLE",
            "未检测到受信任的 ffmpeg 可执行程序，请先通过 Homebrew/系统包管理器安装 ffmpeg。",
        )
    if video_path.is_symlink() or not video_path.is_file():
        raise VisualExtractionError(
            "VISUAL_EXTRACTION_FAILED",
            "本地视频源文件不存在或路径不受信任。",
        )

    cuts = detect_scene_timestamps(
        ffmpeg_path,
        video_path,
        duration_seconds=duration_seconds,
        max_frames=target_frames,
    )
    candidates = select_candidate_timestamps(
        cuts,
        duration_seconds=duration_seconds,
        target_frames=target_frames,
    )

    deduped_raw: list[tuple[float, str, bytes, int]] = []
    for ts_sec, reason in candidates:
        jpeg_bytes, dhash = _extract_single_frame_jpeg(ffmpeg_path, video_path, ts_sec)
        if deduped_raw and any(
            hamming_distance_64(prev_hash, dhash) <= DHASH_DUP_THRESHOLD
            for _, _, _, prev_hash in deduped_raw
        ):
            continue
        deduped_raw.append((ts_sec, reason, jpeg_bytes, dhash))

    if not deduped_raw:
        raise VisualExtractionError(
            "VISUAL_EXTRACTION_FAILED",
            "未能从视频流中提取出有效关键画面。",
        )

    if len(deduped_raw) > target_frames:
        # Preserve first, scene-change frames, and last uniformly under target_frames cap.
        picked_indices: set[int] = {0, len(deduped_raw) - 1}
        scene_indices = [
            idx
            for idx, item in enumerate(deduped_raw)
            if item[1] == "SCENE_CHANGE" and idx not in picked_indices
        ]
        for idx in scene_indices:
            if len(picked_indices) >= target_frames:
                break
            picked_indices.add(idx)
        remaining_slots = target_frames - len(picked_indices)
        if remaining_slots > 0:
            for slot in range(1, len(deduped_raw) - 1):
                if len(picked_indices) >= target_frames:
                    break
                if slot not in picked_indices:
                    picked_indices.add(slot)
        deduped_raw = [deduped_raw[idx] for idx in sorted(picked_indices)[:target_frames]]

    # Enforce cumulative image payload budget across selected frames.
    bounded_raw: list[tuple[float, str, bytes, int]] = []
    running_bytes = 0
    for item in deduped_raw:
        if bounded_raw and running_bytes + len(item[2]) > MAX_TOTAL_VISION_BYTES:
            continue
        bounded_raw.append(item)
        running_bytes += len(item[2])

    output_dir.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    stage_dir = Path(
        tempfile.mkdtemp(prefix=f".tmp-keyframes-{uuid.uuid4().hex[:8]}-", dir=output_dir.parent)
    )
    os.chmod(stage_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    old_backup = output_dir.parent / f".old-keyframes-{uuid.uuid4().hex[:8]}"
    try:
        staged_frames: list[ExtractedKeyframe] = []
        for idx, (ts_sec, reason, jpeg_bytes, dhash) in enumerate(bounded_raw, start=1):
            ts_ms = max(0, int(round(ts_sec * 1000)))
            frame_id = f"f{idx:02d}-{ts_ms}"
            filename = f"frame_{idx:02d}_{ts_ms:08d}.jpg"
            stage_file = stage_dir / filename
            stage_file.write_bytes(jpeg_bytes)
            os.chmod(stage_file, stat.S_IRUSR | stat.S_IWUSR)
            staged_frames.append(
                ExtractedKeyframe(
                    frame_index=idx,
                    frame_id=frame_id,
                    filename=filename,
                    path=output_dir / filename,
                    timestamp_ms=ts_ms,
                    timestamp_label=format_timestamp_label(ts_sec),
                    selection_reason=reason,
                    byte_count=len(jpeg_bytes),
                    sha256=hashlib.sha256(jpeg_bytes).hexdigest(),
                    dhash=dhash,
                )
            )
        if output_dir.exists():
            os.replace(output_dir, old_backup)
        os.replace(stage_dir, output_dir)
        if old_backup.exists():
            shutil.rmtree(old_backup, ignore_errors=True)
        return staged_frames
    except BaseException:
        if not output_dir.exists() and old_backup.exists():
            try:
                os.replace(old_backup, output_dir)
            except OSError:
                pass
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise


def align_keyframes_with_cues(
    keyframes: Sequence[ExtractedKeyframe],
    cues: Sequence[VerifiedTimedTranscriptCue],
    *,
    window_before_ms: int = 15_000,
    window_after_ms: int = 25_000,
    max_excerpt_chars: int = 320,
) -> list[dict[str, object]]:
    """Pair each extracted keyframe timestamp with overlapping nearby verified transcript cues."""
    aligned: list[dict[str, object]] = []
    for kf in keyframes:
        lo = max(0, kf.timestamp_ms - window_before_ms)
        hi = kf.timestamp_ms + window_after_ms
        nearby = [
            cue.text.strip()
            for cue in cues
            if cue.end_ms >= lo and cue.start_ms <= hi and cue.text.strip()
        ]
        excerpt = " ".join(nearby).strip()
        if len(excerpt) > max_excerpt_chars:
            excerpt = excerpt[: max_excerpt_chars - 1].rstrip() + "…"
        aligned.append(
            {
                "frame": kf,
                "nearby_transcript": excerpt,
            }
        )
    return aligned
