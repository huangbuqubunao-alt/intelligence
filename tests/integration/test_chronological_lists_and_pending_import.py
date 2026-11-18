from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest
from test_workspace_intelligence_hub import (
    _build_env,
    _seed_youtube_video,
)

from youtube_intel.local_content import LocalContentProvider
from youtube_intel.offline_transcription import media_tool
from youtube_intel.state import TimedTranscriptCueWrite


def _create_tiny_mp4(path: Path, freq: int = 440) -> Path:
    ffmpeg = media_tool("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg unavailable")
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq}:duration=2",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


def test_intelligence_and_topics_sort_chronologically_with_local_dates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    repo = env["repo"]
    hub = env["hub"]
    fast_app = env["fast_app"]

    # 1. Seed older local video (imported Oct 10)
    oct_mp4 = _create_tiny_mp4(tmp_path / "oct_course.mp4")
    oct_time = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
    oct_local = LocalContentProvider(
        repo, env["data_root"], now=lambda: oct_time
    ).import_file(oct_mp4)

    # 2. Seed mid YouTube video (published Nov 12)
    nov12_time = datetime(2026, 11, 12, 14, 0, tzinfo=UTC)
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="ytMidNov120",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Nov 12 Agent Workflows",
        duration_seconds=900,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=4000,
                text="November 12 deep dive on developer agent workflows.",
            ),
        ),
        now=nov12_time,
    )

    # 3. Seed newest local video (imported Nov 18) with distinct bytes
    nov18_mp4 = _create_tiny_mp4(tmp_path / "nov18_course.mp4", freq=880)
    nov18_time = datetime(2026, 11, 18, 1, 0, tzinfo=UTC)
    nov18_local = LocalContentProvider(
        repo, env["data_root"], now=lambda: nov18_time
    ).import_file(nov18_mp4)

    class _TopicRoutingCompleter:
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
            _ = (system_prompt, mode, max_tokens)
            cluster = (
                "开发者工具与工程效能"
                if "Nov 12 Agent Workflows" in user_prompt
                else "AI Agent 与自动化架构"
            )
            return (
                {
                    "headline_zh": f"{cluster} 要点总结",
                    "summary_zh": f"{cluster} 摘要内容。",
                    "score": 8.8,
                    "score_reason_zh": "测试评分。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": [cluster],
                    "topic_cluster_zh": cluster,
                    "core_points": [
                        {"text_zh": f"{cluster} 关键结论", "cue_window_index": 0}
                    ],
                    "product_opportunities_zh": [],
                    "business_opportunities_zh": [],
                    "filtered_noise_zh": [],
                },
                provider,
                model,
            )

    hub._llm_completer = _TopicRoutingCompleter()

    # Distill OUT OF CONTENT DATE ORDER (just like user's batch distillation on Nov 13):
    # ytMidNov120 first (08:00), nov18_local second (10:00), oct_local LAST (15:00 -> newest intel created_at!)
    clock_state = {"now": datetime(2026, 11, 13, 8, 0, tzinfo=UTC)}
    hub._now = lambda: clock_state["now"]
    hub.distill_video("ytMidNov120", persist_intelligence_card=True)

    clock_state["now"] = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)
    hub.transcribe_and_distill_local_video(nov18_local.content_id)

    clock_state["now"] = datetime(2026, 11, 13, 15, 0, tzinfo=UTC)
    hub.transcribe_and_distill_local_video(oct_local.content_id)

    fast_app._bump_mutation_epoch()

    # Verify /api/v1/intelligence sorts newest-first by effective content date (Nov 18 -> Nov 12 -> Oct 10)
    st_intel, intel_body = fast_app.handle("GET", "/api/v1/intelligence")
    assert st_intel == HTTPStatus.OK
    available = [i for i in intel_body["intelligence"] if i["status"] == "AVAILABLE"]
    assert [i["card"]["video_id"] for i in available] == [
        nov18_local.content_id,
        "ytMidNov120",
        oct_local.content_id,
    ]
    assert all(i.get("effective_published_at") for i in available)

    # Verify /api/v1/topics sorts by latest_published_at descending & exposes latest_published_at
    st_topics, topics_body = fast_app.handle("GET", "/api/v1/topics")
    assert st_topics == HTTPStatus.OK
    assert [tp["name"] for tp in topics_body["topics"]] == [
        "AI Agent 与自动化架构",
        "开发者工具与工程效能",
    ]
    assert topics_body["topics"][0]["ai_evolution"]["latest_published_at"].startswith("2026-11-18")
    assert topics_body["topics"][1]["ai_evolution"]["latest_published_at"].startswith("2026-11-12")

    # Verify /api/v1/topics/<id> orders entries newest-first (Nov 18 -> Oct 10) with non-empty published_at on LOCAL videos
    agent_topic_id = topics_body["topics"][0]["topic_id"]
    st_tdet, tdet = fast_app.handle("GET", f"/api/v1/topics/{agent_topic_id}")
    assert st_tdet == HTTPStatus.OK
    entries = tdet["topic"]["ai_evolution"]["entries"]
    assert [e["video_id"] for e in entries] == [nov18_local.content_id, oct_local.content_id]
    assert entries[0]["published_at"].startswith("2026-11-18")
    assert entries[1]["published_at"].startswith("2026-10-10")


def test_single_video_pending_import_can_be_disabled_and_re_imported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app = env["fast_app"]

    st_imp, imp_body = fast_app.handle(
        "POST",
        "/api/v1/sources/import",
        json.dumps(
            {
                "url": "https://www.youtube.com/watch?v=2hJkprFnzhY",
                "command_id": "cmd-test-import-1",
            }
        ).encode(),
    )
    assert st_imp == HTTPStatus.ACCEPTED
    source_id = imp_body["source"]["source_id"]

    env["hub"].get_settings()
    fast_app._bump_mutation_epoch()

    st_v, v_body = fast_app.handle("GET", "/api/v1/videos")
    assert st_v == HTTPStatus.OK
    assert any(
        v["video_id"] == "2hJkprFnzhY" and v.get("work_kind") == "DURABLE_CONTENT_IDENTITY"
        for v in v_body["videos"]
    )

    st_patch, patch_body = fast_app.handle(
        "PATCH",
        f"/api/v1/sources/{source_id}",
        json.dumps({"enabled": False}).encode(),
    )
    assert st_patch == HTTPStatus.OK
    assert patch_body["source"]["enabled"] is False

    st_v2, v_body2 = fast_app.handle("GET", "/api/v1/videos")
    assert st_v2 == HTTPStatus.OK
    assert all(v["video_id"] != "2hJkprFnzhY" for v in v_body2["videos"])

    st_dash, dash_body = fast_app.handle("GET", "/api/v1/dashboard")
    assert st_dash == HTTPStatus.OK
    assert all(
        run.get("source_id") != source_id for run in dash_body.get("needs_attention", [])
    )

    st_reimp, reimp_body = fast_app.handle(
        "POST",
        "/api/v1/sources/import",
        json.dumps(
            {
                "url": "https://www.youtube.com/watch?v=2hJkprFnzhY",
                "command_id": "cmd-test-import-2",
            }
        ).encode(),
    )
    assert st_reimp == HTTPStatus.ACCEPTED
    assert reimp_body["source"]["enabled"] is True
    st_v3, v_body3 = fast_app.handle("GET", "/api/v1/videos")
    assert st_v3 == HTTPStatus.OK
    assert any(v["video_id"] == "2hJkprFnzhY" for v in v_body3["videos"])
