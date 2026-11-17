import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { completeOnboarding } from "./Onboarding";

function okJson(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
  });
}

function isHiddenInsideClosedDetails(el: Element): boolean {
  const details = el.closest("details");
  return details !== null && !details.hasAttribute("open");
}

describe("Freshly imported local video Content detail UX", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    location.hash = "";
  });

  it("replaces contradictory missing-model/unknown/unqualified errors with a clear 1-click ready state and supports async transcription polling", async () => {
    localStorage.setItem("yia.ui.language", "zh-CN");
    completeOnboarding();
    location.hash = "#Content/localCourse137m";

    let jobState: "IDLE" | "RUNNING" | "READY" = "IDLE";
    let pollCalls = 0;

    const readyBrief = {
      video_id: "localCourse137m",
      headline_zh: "AI 大模型全栈工程师导论：从 Prompt 工程到企业级 Agent 闭环实战",
      summary_zh: "系统拆解全栈大模型开发路线图、RAG 检索增强与工具调用状态机。",
      score: 9.4,
      score_reason_zh: "体系化全栈大模型实战导学课。",
      recommendation_tier: "MUST_WATCH",
      content_bucket: "TUTORIAL",
      is_short_noise: false,
      topics_zh: ["大模型全栈", "Agent 架构"],
      topic_cluster_zh: "AI Agent 工程架构",
      product_opportunities_zh: ["企业私有知识库闭环智能体"],
      business_opportunities_zh: ["垂直行业 Agent 交付服务"],
      obsidian_markdown: "# 1.简介 - AI 大模型全栈工程师\n\n- 主题：[[AI Agent 工程架构]]",
    };

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (
        input.endsWith("/workspace-ai/videos/localCourse137m/transcribe") &&
        init?.method === "POST"
      ) {
        jobState = "RUNNING";
        return okJson({
          video_id: "localCourse137m",
          transcription_status: "RUNNING",
          stage: "TRANSCRIBING",
        });
      }
      if (input.endsWith("/workspace-ai/videos/localCourse137m/transcribe-status")) {
        pollCalls += 1;
        if (jobState === "RUNNING" && pollCalls >= 2) {
          jobState = "READY";
        }
        return okJson({
          video_id: "localCourse137m",
          transcriber_ready: true,
          job:
            jobState === "IDLE"
              ? null
              : {
                  status: jobState,
                  stage: jobState === "RUNNING" ? "TRANSCRIBING" : "READY",
                  started_at: "2026-11-18T01:00:00Z",
                  updated_at: "2026-11-18T01:00:05Z",
                  error_code: null,
                },
        });
      }
      if (input.endsWith("/videos/localCourse137m/transcription")) {
        return okJson({
          transcription: {
            status: jobState === "READY" ? "READY" : "MODEL_MISSING",
            retry_available: false,
            start_available: false,
            capability: {
              state: "MODEL_MISSING",
              runtime_detected: true,
              runtime_available: true,
              model_present: false,
              executor_compatible: true,
              executor: "MLX Whisper",
              reason_code: "MODEL_MISSING",
            },
          },
        });
      }
      if (input.endsWith("/videos/localCourse137m/evidence")) {
        return okJson({
          evidence:
            jobState === "READY"
              ? [
                  {
                    evidence_id: "ev-1",
                    locator_type: "TIMED_MEDIA",
                    start_ms: 0,
                    end_ms: 8000,
                    source_language: "zh-CN",
                    translation_target_language: "zh-CN",
                    original_excerpt: "大家好，欢迎来到 AI 大模型全栈工程师第一节导论课。",
                  },
                ]
              : [],
        });
      }
      if (input.endsWith("/videos/localCourse137m/deep-analysis/obsidian")) {
        return okJson({ publish: { state: "RESULT_INELIGIBLE" } });
      }
      if (input.endsWith("/videos/localCourse137m/deep-analysis")) {
        return okJson({
          deep_analysis: {
            content_id: "localCourse137m",
            status: {
              availability: "NOT_QUALIFIED",
              qualified: false,
              production_eligible: false,
              consent_required: false,
              reason: "No Deep Analysis model is currently qualified.",
              reason_code: "NO_QUALIFIED_MODEL",
              routes: [
                {
                  route_id: "ollama-local",
                  provider_id: "ollama-local",
                  model_id: "qwen2.5-coder:7b",
                  configured: true,
                  credential_configured: true,
                  reachability: "REACHABLE",
                  qualification_status: "STALE",
                  production_eligible: false,
                },
              ],
            },
            result: null,
          },
        });
      }
      if (input.endsWith("/videos/localCourse137m")) {
        return okJson({
          video: {
            video_id: "localCourse137m",
            provider: "LOCAL",
            media_kind: "VIDEO",
            format: ".mp4",
            channel_id: "local",
            channel_name: "Local",
            title: "1.简介 - AI 大模型全栈工程师_ev.mp4",
            source_url: null,
            imported_at: "2026-11-18T00:55:00Z",
            published_at: "2026-11-18T00:55:00Z",
            processing_status: jobState === "READY" ? "READY" : "TRANSCRIPTION_UNAVAILABLE",
            last_updated: "2026-11-18T00:55:00Z",
            duration_seconds: 8236,
            ...(jobState === "READY" ? { ai_brief: readyBrief } : {}),
          },
          scoring: { status: "NOT_AVAILABLE" },
          transcript:
            jobState === "READY"
              ? {
                  status: "AVAILABLE",
                  text: "大家好，欢迎来到 AI 大模型全栈工程师第一节导论课。",
                  timed_segments: [
                    {
                      start_ms: 0,
                      end_ms: 8000,
                      text: "大家好，欢迎来到 AI 大模型全栈工程师第一节导论课。",
                    },
                  ],
                }
              : { status: "NOT_PROCESSED" },
          note: {
            v1: { status: "UNAVAILABLE" },
            v2:
              jobState === "READY"
                ? {
                    status: "AVAILABLE",
                    note_identity: "workspace-ai/localCourse137m",
                    language: "zh-CN",
                    summary: readyBrief.summary_zh,
                    core_points: ["全栈大模型开发路线图"],
                  }
                : { status: "UNAVAILABLE" },
          },
          intelligence_result: { status: "NOT_PROCESSED" },
          manual_intelligence_eligible: false,
          local_intelligence: {
            video_id: "localCourse137m",
            qualification_status: "UNKNOWN",
            request_state: "UNKNOWN",
            reason: "CAPABILITY_STATUS_UNAVAILABLE",
          },
          workspace_ai_capabilities: {
            ready: true,
            transcriber_ready: true,
            transcribe_job:
              jobState === "IDLE"
                ? null
                : {
                    status: jobState,
                    stage: jobState === "RUNNING" ? "TRANSCRIBING" : "READY",
                    started_at: "2026-11-18T01:00:00Z",
                    updated_at: "2026-11-18T01:00:05Z",
                    error_code: null,
                  },
          },
          history: [],
        });
      }
      if (input.endsWith("/videos")) {
        return okJson({ videos: [] });
      }
      if (input.endsWith("/settings")) {
        return okJson({
          target_language: "zh-CN",
          preferences: { focus_rules: [], ignore_rules: [], distillation_style: "BALANCED" },
        });
      }
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(
      await screen.findByText("1.简介 - AI 大模型全栈工程师_ev.mp4"),
    ).toBeTruthy();

    // 1. Top hero badge shows friendly ready-to-transcribe status instead of "缺少本地模型"
    expect(await screen.findByText("已导入 · 待语音转写")).toBeTruthy();

    // 2. Scary legacy diagnostic strings are NOT visibly shown outside collapsed <details>
    for (const scaryText of [
      "缺少本地模型",
      "本地洞察状态未知。请重新读取状态后再请求提炼。",
      "当前没有通过深度分析资格的模型，因此深度分析不可用。系统不会静默降级，摘要与证据仍可正常使用。",
    ]) {
      const matches = screen.queryAllByText(scaryText);
      for (const match of matches) {
        expect(isHiddenInsideClosedDetails(match)).toBe(true);
      }
    }

    // 3. Clicking the green action button starts async transcription and polls until READY
    const actionButtons = screen.getAllByRole("button", {
      name: /离线语音转写并提炼中文洞察/,
    });
    expect(actionButtons.length).toBeGreaterThanOrEqual(1);
    fireEvent.click(actionButtons[0]);

    await waitFor(
      () => {
        expect(
          screen.getByText(
            "AI 大模型全栈工程师导论：从 Prompt 工程到企业级 Agent 闭环实战",
          ),
        ).toBeTruthy();
      },
      { timeout: 6000 },
    );
  });
});
