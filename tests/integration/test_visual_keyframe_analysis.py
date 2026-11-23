"""Integration tests for on-demand keyframe + transcript fusion analysis MVP."""

from __future__ import annotations

import base64
import email.message
import io
import json
import stat
import subprocess
import urllib.error
import wave
import zipfile
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest
import yaml

from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.fast_read_api import FastReadApiApplication
from youtube_intel.local_content import LocalContentProvider, MediaTranscript
from youtube_intel.offline_transcription import media_tool
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.state import TimedTranscriptCueWrite
from youtube_intel.visual_keyframes import extract_video_keyframes
from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub

NOW = datetime(2026, 11, 23, 14, 0, tzinfo=UTC)


class _MemorySecretStore:
    def __init__(self) -> None:
        self.secret: str | None = None

    def get(self) -> str | None:
        return self.secret

    def load(self) -> str | None:
        return self.secret

    def save(self, value: str) -> None:
        self.secret = value

    def delete(self) -> None:
        self.secret = None


class _DeterministicCompleter:
    def __call__(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        _ = (system_prompt, user_prompt, mode, max_tokens)
        return (
            {
                "headline_zh": "多模态 Agent 架构设计与实机成本对照",
                "summary_zh": "系统梳理分层工作流、视觉关键帧抽取时机及单机推理成本控制策略。",
                "score": 9.1,
                "score_reason_zh": "架构清晰且包含可复用工程落地方案。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["多模态", "Agent 架构"],
                "topic_cluster_zh": "AI Agent 与自动化架构",
                "core_points": [
                    {
                        "text_zh": "按场景切换抽帧并做 dHash 去重可将视觉开销限制在少数关键页",
                        "cue_window_index": 0,
                    }
                ],
                "product_opportunities_zh": ["为技术演讲视频提供带原图对照的 Obsidian 知识包"],
                "business_opportunities_zh": ["轻量按需视觉研究插件增值包"],
                "filtered_noise_zh": ["开场静音片段"],
            },
            provider,
            model,
        )


class _RecordingVisionCompleter:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self.should_fail = should_fail

    def __call__(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        image_paths: Any,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 2200,
    ) -> tuple[dict[str, Any], str, str]:
        if self.should_fail:
            raise RuntimeError("simulated vision completer failure")
        paths = list(image_paths)
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "image_count": len(paths),
                "mode": mode,
                "provider": provider,
                "model": model,
                "max_tokens": max_tokens,
            }
        )
        frames_payload: list[dict[str, Any]] = []
        for idx in range(1, len(paths) + 1):
            is_speaker = idx == 2 and len(paths) >= 3
            frames_payload.append(
                {
                    "frame_index": idx,
                    "frame_kind": "SPEAKER" if is_speaker else ("ARCHITECTURE" if idx == 1 else "CHART"),
                    "has_visual_info": not is_speaker,
                    "title_zh": f"讲者过渡镜头 {idx}" if is_speaker else f"第 {idx} 帧核心系统图解",
                    "visual_detail_zh": (
                        "仅见主讲人镜头，无新增 PPT 或图表文字。"
                        if is_speaker
                        else f"展示关键图表模块与第 {idx} 阶段数据流向关系。"
                    ),
                    "transcript_fusion_zh": (
                        "讲者做口头过渡衔接，主要论点见下一张架构页。"
                        if is_speaker
                        else f"结合该时刻原话字幕说明核心吞吐指标变化（帧 {idx}）。"
                    ),
                }
            )
        return (
            {
                "visual_summary_zh": "课程通过架构图与性能柱状图对比验证了按需抽帧的可控推理成本。",
                "visual_takeaways_zh": [
                    "架构总览帧展示采集、抽帧去重与多模态核验三层隔离链路。",
                    "成本对比图表证实 dHash 去重显著降低重复幻灯片送审次数。",
                ],
                "frames": frames_payload,
            },
            provider,
            model,
        )


def _create_multiscene_mp4(base_dir: Path, name: str = "slide_demo_lecture.mp4") -> Path:
    """Create a synthetic multi-scene MP4 with a repeated duplicate slide using core lavfi filters."""
    ffmpeg = media_tool("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg unavailable")
    mp4_path = base_dir.resolve() / name
    # Segment 1 (0-1.5s): Red + white box (slide A)
    # Segment 2 (1.5-3.0s): RGB test bars (slide B)
    # Segment 3 (3.0-4.5s): Red + white box (duplicate of slide A -> dHash dedup target)
    # Segment 4 (4.5-6.0s): SMPTE color bars (slide C)
    # Segment 5 (6.0-7.5s): Blue + yellow box (slide D)
    filter_complex = (
        "[1:v]drawbox=x=40:y=30:w=240:h=80:color=white:t=fill[v0];"
        "[2:v]scale=320:180[v1];"
        "[3:v]drawbox=x=40:y=30:w=240:h=80:color=white:t=fill[v2];"
        "[4:v]scale=320:180[v3];"
        "[5:v]drawbox=x=80:y=60:w=160:h=70:color=yellow:t=fill[v4];"
        "[v0][v1][v2][v3][v4]concat=n=5:v=1:a=0,format=yuv420p[vout]"
    )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=7.5",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x180:d=1.5:r=10",
            "-f",
            "lavfi",
            "-i",
            "rgbtestsrc=s=320x180:d=1.5:r=10",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x180:d=1.5:r=10",
            "-f",
            "lavfi",
            "-i",
            "smptebars=s=320x180:d=1.5:r=10",
            "-f",
            "lavfi",
            "-i",
            "color=c=navy:s=320x180:d=1.5:r=10",
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "0:a",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(mp4_path),
        ],
        check=True,
        capture_output=True,
    )
    return mp4_path


def _create_sample_wav(base_dir: Path, name: str = "audio_only_note.wav") -> Path:
    wav_path = base_dir.resolve() / name
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)
    return wav_path


def _build_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    vision_completer: Any = None,
) -> dict[str, Any]:
    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_models", lambda *_a: {"models": []}
    )
    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_runtime_version", lambda *_a: {}
    )
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe",
        lambda *_a: "MODEL_UNAVAILABLE",
    )

    repo_root = Path(__file__).resolve().parents[2]
    resolved_tmp = tmp_path.resolve()
    project_root = resolved_tmp / "owner"
    for folder in ("data", "logs", "templates", "vault"):
        (project_root / folder).mkdir(parents=True, exist_ok=True)
    values = load_settings(repo_root / "config" / "settings.example.yaml").model_dump()
    values["storage"]["vault_root"] = str(project_root / "vault")
    config = AppConfig(channels=(), settings=AppSettings.model_validate(values))
    db_path = project_root / "state.sqlite3"
    byok_store = _MemorySecretStore()

    composition = build_local_source_run_runtime(
        config=config,
        project_root=project_root,
        database=db_path,
        credential_store=_MemorySecretStore(),
        bigmodel_credential_store=_MemorySecretStore(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        now=lambda: NOW,
    )
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=project_root / "data",
        project_root=project_root,
        byok_credential_store=byok_store,
        llm_completer=_DeterministicCompleter(),
        vision_completer=vision_completer,
        installed_ollama_probe=lambda _url: (True, ("gemma3:4b", "qwen3.5:9b")),
        now=lambda: NOW,
    )
    hub.ensure_ready()
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)
    return {
        "tmp": resolved_tmp,
        "project_root": project_root,
        "data_root": project_root / "data",
        "db_path": db_path,
        "repo": composition.repository,
        "byok_store": byok_store,
        "fast_app": fast_app,
        "hub": hub,
    }


def test_extract_video_keyframes_dedupes_identical_slides_and_sets_restrictive_perms(
    tmp_path: Path,
) -> None:
    mp4_path = _create_multiscene_mp4(tmp_path)
    out_dir = tmp_path / "keyframes_out"
    frames = extract_video_keyframes(
        mp4_path, out_dir, duration_seconds=7.5, max_frames=8
    )

    # Video has 4 visually unique slides (slide A appears twice and must dedup via dHash)
    assert 3 <= len(frames) <= 5
    dhashes = [kf.dhash for kf in frames]
    assert len(set(dhashes)) == len(frames)
    assert stat.S_IMODE(out_dir.stat().st_mode) == 0o700
    for kf in frames:
        assert kf.path.is_file()
        assert stat.S_IMODE(kf.path.stat().st_mode) == 0o600
        assert kf.path.read_bytes()[:2] == b"\xff\xd8"
        assert kf.byte_count == kf.path.stat().st_size


def test_visual_analysis_rejects_audio_text_and_path_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vision = _RecordingVisionCompleter()
    env = _build_env(tmp_path, monkeypatch, vision_completer=vision)
    fast_app: FastReadApiApplication = env["fast_app"]
    provider = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW)

    wav_path = _create_sample_wav(env["tmp"])
    md_path = env["tmp"] / "research_note.md"
    md_path.write_text("# 笔记\n\n纯文本笔记不应该允许抽帧。", encoding="utf-8")

    audio_imp = provider.import_file(wav_path)
    text_imp = provider.import_file(md_path)

    for cid in (audio_imp.content_id, text_imp.content_id):
        cap_code, cap_body = fast_app.handle(
            "GET", f"/api/v1/workspace-ai/videos/{cid}/visual-analysis"
        )
        assert cap_code == HTTPStatus.OK
        assert cap_body["eligible"] is False
        assert cap_body["ineligible_reason_code"] == "VISUAL_MEDIA_REQUIRED"

        post_code, post_body = fast_app.handle(
            "POST", f"/api/v1/workspace-ai/videos/{cid}/visual-analysis", b"{}"
        )
        assert post_code == HTTPStatus.CONFLICT
        assert post_body["error"]["code"] == "VISUAL_MEDIA_REQUIRED"

    assert vision.calls == []
    # Path traversal / invalid frame_id must fail closed with 404
    bad_img = fast_app.backup_download(
        f"/api/v1/workspace-ai/videos/{audio_imp.content_id}/keyframes/../../etc/passwd.jpg"
    )
    assert bad_img is None or bad_img[0] == HTTPStatus.NOT_FOUND


def test_visual_analysis_enforces_cloud_guards_and_preserves_prior_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vision = _RecordingVisionCompleter()
    env = _build_env(tmp_path, monkeypatch, vision_completer=vision)
    fast_app: FastReadApiApplication = env["fast_app"]
    hub: WorkspaceIntelligenceHub = env["hub"]

    mp4_path = _create_multiscene_mp4(env["tmp"])
    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_file(
        mp4_path
    )
    vid = imp.content_id

    # Initial local free analysis succeeds & persists JPEGs + row
    ok_code, ok_body = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{vid}/visual-analysis", b"{}"
    )
    assert ok_code == HTTPStatus.OK
    first_frame_id = ok_body["analysis"]["frames"][0]["frame_id"]
    first_img = hub.read_video_keyframe_image(vid, first_frame_id)
    assert first_img is not None

    # Switch to cloud_byok without re-auth / missing key / daily budget exhausted
    fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/settings",
        json.dumps(
            {
                "active_mode": "cloud_byok",
                "cloud_provider": "openai_compatible",
                "cloud_base_url": "https://api.openai.com/v1",
                "cloud_model": "gpt-4o-mini",
                "cloud_daily_call_limit": 1,
            }
        ).encode("utf-8"),
    )
    no_key_code, no_key_body = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{vid}/visual-analysis", b"{}"
    )
    assert no_key_code == HTTPStatus.CONFLICT
    assert no_key_body["error"]["code"] == "CLOUD_CREDENTIAL_MISSING"

    # Configure key -> 1st cloud call succeeds, 2nd fails budget limit, and 1st analysis stays intact!
    fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/settings",
        json.dumps({"cloud_api_key": "sk-test-visual-key"}).encode("utf-8"),
    )
    c1_code, _ = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{vid}/visual-analysis", b"{}"
    )
    assert c1_code == HTTPStatus.OK

    c2_code, c2_body = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{vid}/visual-analysis", b"{}"
    )
    assert c2_code == HTTPStatus.TOO_MANY_REQUESTS
    assert c2_body["error"]["code"] == "CLOUD_DAILY_BUDGET_EXCEEDED"

    # Prior saved keyframe JPEG and analysis must still be intact after blocked 2nd run
    saved_after = hub.get_video_visual_analysis(vid)
    assert saved_after is not None
    latest_fid = saved_after["frames"][0]["frame_id"]
    assert hub.read_video_keyframe_image(vid, latest_fid) is not None


def test_visual_analysis_reports_local_vision_unsupported_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch, vision_completer=None)
    fast_app: FastReadApiApplication = env["fast_app"]

    mp4_path = _create_multiscene_mp4(env["tmp"])
    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_file(
        mp4_path
    )

    def _fake_urlopen(*_args: Any, **_kwargs: Any) -> Any:
        headers = email.message.Message()
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:11434/api/chat",
            code=400,
            msg="Bad Request",
            hdrs=headers,
            fp=io.BytesIO(
                json.dumps({"error": "model qwen3:8b does not support vision inputs"}).encode(
                    "utf-8"
                )
            ),
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    code, body = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{imp.content_id}/visual-analysis", b"{}"
    )
    assert code == HTTPStatus.CONFLICT
    assert body["error"]["code"] == "LOCAL_VISION_MODEL_UNSUPPORTED"
    assert "视觉" in body["error"]["message"]
    assert env["hub"].get_video_visual_analysis(imp.content_id) is None


def test_visual_analysis_happy_path_image_serving_obsidian_zip_and_backup_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vision = _RecordingVisionCompleter()
    env = _build_env(tmp_path, monkeypatch, vision_completer=vision)
    fast_app: FastReadApiApplication = env["fast_app"]
    hub: WorkspaceIntelligenceHub = env["hub"]

    mp4_path = _create_multiscene_mp4(env["tmp"], name="2026 多模态关键帧架构演讲.mp4")
    provider = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW)
    imp = provider.import_file(mp4_path)
    vid = imp.content_id

    # Seed verified timed transcript cues to test audio+visual alignment & brief merge
    provider.accept_transcript(
        vid,
        MediaTranscript(
            cues=(
                TimedTranscriptCueWrite(
                    start_ms=0,
                    end_ms=2500,
                    text="首先我们看这张三层多模态系统架构图，先抽帧再去重。",
                ),
                TimedTranscriptCueWrite(
                    start_ms=2500,
                    end_ms=7000,
                    text="右侧柱状图展示了去重后视觉延迟从 12 秒降到 2 秒。",
                ),
            ),
            language="zh",
            provenance='{"contract":"offline-timed-transcription-v1"}',
        ),
    )

    # Distill text brief first, then trigger visual keyframe analysis -> must enrich obsidian_markdown!
    distill_code, _ = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{vid}/distill", b"{}"
    )
    assert distill_code == HTTPStatus.OK

    vis_code, vis_body = fast_app.handle(
        "POST",
        f"/api/v1/workspace-ai/videos/{vid}/visual-analysis",
        json.dumps({"max_frames": 6}).encode("utf-8"),
    )
    assert vis_code == HTTPStatus.OK
    assert vis_body["ai_brief_updated"] is True
    analysis = vis_body["analysis"]
    assert analysis["frame_count"] >= 3
    assert len(vision.calls) == 1
    assert "首先我们看这张三层多模态系统架构图" in vision.calls[0]["user_prompt"]

    # Detail GET projection includes visual_analysis & visual capabilities
    det_code, det_body = fast_app.handle("GET", f"/api/v1/videos/{vid}")
    assert det_code == HTTPStatus.OK
    assert det_body["workspace_ai_capabilities"]["visual_analysis_eligible"] is True
    assert det_body["workspace_ai_capabilities"]["ffmpeg_available"] is True
    assert det_body["visual_analysis"]["frame_count"] == analysis["frame_count"]

    # Keyframe JPEG endpoint returns valid JPEG bytes
    first_frame = analysis["frames"][0]
    img_res = fast_app.backup_download(first_frame["image_url"])
    assert img_res is not None
    img_status, img_headers, img_bytes = img_res
    assert img_status == int(HTTPStatus.OK)
    assert img_headers["Content-Type"] == "image/jpeg"
    assert isinstance(img_bytes, bytes) and img_bytes[:2] == b"\xff\xd8"

    # Single-video visual-pack.zip unpacks cleanly with valid YAML & every ![[assets/...]] image present!
    vpack_res = fast_app.backup_download(f"/api/v1/workspace-ai/videos/{vid}/visual-pack.zip")
    assert vpack_res is not None
    vp_status, vp_headers, vp_bytes = vpack_res
    assert vp_status == int(HTTPStatus.OK)
    assert vp_headers["Content-Type"] == "application/zip"
    assert isinstance(vp_bytes, bytes)
    unpack_single = env["tmp"] / "unpack_single"
    with zipfile.ZipFile(io.BytesIO(vp_bytes), "r") as zf_single:
        assert zf_single.testzip() is None
        zf_single.extractall(unpack_single)

    md_files = list(unpack_single.glob("*.md"))
    assert len(md_files) == 1
    md_text = md_files[0].read_text(encoding="utf-8")
    assert md_text.startswith("---\n")
    fm = yaml.safe_load(md_text.split("---\n", 2)[1])
    assert isinstance(fm, dict) and fm["video_id"] == vid
    assert "## 5. 关键画面与字幕融合分析" in md_text
    assert f"![[assets/{first_frame['obsidian_asset_name']}]]" in md_text
    assert (unpack_single / "assets" / first_frame["obsidian_asset_name"]).read_bytes()[:2] == b"\xff\xd8"

    # Full Obsidian Vault bundle includes both note visual section AND physical JPEG under assets/
    bundle_code, bundle_json = fast_app.handle(
        "GET", "/api/v1/workspace-ai/obsidian-bundle?scope=all"
    )
    assert bundle_code == HTTPStatus.OK
    assert bundle_json["counts"]["visual_assets"] >= 2
    unpack_vault = env["tmp"] / "unpack_vault"
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(bundle_json["archive_base64"])), "r") as zf_all:
        assert zf_all.testzip() is None
        zf_all.extractall(unpack_vault)
    assert (unpack_vault / "assets" / first_frame["obsidian_asset_name"]).is_file()
    vault_video_mds = list((unpack_vault / "03-视频深度笔记").glob("*.md"))
    assert len(vault_video_mds) == 1
    assert "## 5. 关键画面与字幕融合分析" in vault_video_mds[0].read_text(encoding="utf-8")

    # Sidecar backup & restore preserves video_visual_analyses cleanly
    bk_code, bk_snap = fast_app.handle("GET", "/api/v1/workspace-ai/backup")
    assert bk_code == HTTPStatus.OK
    assert bk_snap["counts"]["visual_analyses"] == 1

    (env["project_root"] / ".workspace-ai" / "hub.sqlite3").unlink()
    assert hub.get_video_visual_analysis(vid) is None
    rs_code, rs_body = fast_app.handle(
        "POST", "/api/v1/workspace-ai/restore", json.dumps(bk_snap).encode("utf-8")
    )
    assert rs_code == HTTPStatus.OK
    assert rs_body["restored"]["visual_analyses"] == 1
    restored = hub.get_video_visual_analysis(vid)
    assert restored is not None
    assert restored["frame_count"] == analysis["frame_count"]
