import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { readPersonalNote } from "./personalNotes";

function okJson(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("Iteration 40 (EVO-W7-05): Reader 1-click AI takeaway capture into personal notes", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.onboarding_completed.v1", "1");
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Content/vid40";
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
    location.hash = "";
  });

  it("captures an AI takeaway bullet into personal notes idempotently and updates ReaderPersonalNoteCard live", async () => {
    vi.stubGlobal("fetch", (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/system")) {
        return okJson({ health: "ready", edition: "LOCAL" });
      }
      if (url.includes("/api/v1/settings")) {
        return okJson({ general: { output_language: "zh-CN", output_language_updated_at: null }, providers: [] });
      }
      if (url.includes("/api/v1/videos/vid40/evidence")) {
        return okJson({ evidence: [] });
      }
      if (url.includes("/api/v1/videos/vid40")) {
        return okJson({
          video: {
            video_id: "vid40",
            channel_id: "ch40",
            channel_name: "Product Engineering",
            title: "可审计 AI 产品架构设计",
            source_url: "https://youtube.com/watch?v=vid40",
            published_at: "2026-11-26T10:00:00Z",
            last_updated: "2026-11-26T10:00:00Z",
            processing_status: "READY",
            duration_seconds: 900,
            provider: "YOUTUBE",
            ai_brief: {
              video_id: "vid40",
              headline_zh: "核心结论：把 AI 结论与原话证据锚点绑定",
              summary_zh: "产品正文摘要",
              score: 9.3,
              score_reason_zh: "干货密度高",
              recommendation_tier: "MUST_WATCH",
              content_bucket: "DEEP_DIVE",
              is_short_noise: false,
              topics_zh: ["AI"],
              topic_cluster_zh: "AI Agent 工程架构",
              product_opportunities_zh: ["为每条 AI 摘要挂载一键摘录按钮"],
              business_opportunities_zh: ["面向科研团队打包可审计知识工作台订阅"],
            },
          },
          transcript: { status: "AVAILABLE", text: "原文内容", timed_segments: [] },
          note: { v2: null },
          intelligence_result: { status: "UNAVAILABLE" },
          history: [],
        });
      }
      if (url.includes("/api/v1/videos")) {
        return okJson({ videos: [], total: 0, has_more: false });
      }
      return okJson({});
    });

    render(<App />);

    const captureBtn = await screen.findByRole("button", {
      name: "摘录进个人批注：为每条 AI 摘要挂载一键摘录按钮",
    });
    fireEvent.click(captureBtn);

    await waitFor(() => {
      const saved = readPersonalNote("vid40");
      expect(saved?.text).toContain("【AI 产品化启发】为每条 AI 摘要挂载一键摘录按钮");
      expect(saved?.text).toContain("— 《可审计 AI 产品架构设计》");
    });

    expect(
      screen.getByRole("button", { name: "已摘录：为每条 AI 摘要挂载一键摘录按钮" }).textContent,
    ).toBe("已摘录 ✓");

    // Re-clicking must stay idempotent without duplicating the quote
    fireEvent.click(
      screen.getByRole("button", { name: "已摘录：为每条 AI 摘要挂载一键摘录按钮" }),
    );
    const savedAfter = readPersonalNote("vid40")?.text ?? "";
    expect(savedAfter.split("为每条 AI 摘要挂载一键摘录按钮").length - 1).toBe(1);
  });
});
