import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

const sampleVideos = [
  {
    video_id: "vidYt1",
    title: "YouTube Agent Patterns",
    provider: "YOUTUBE",
    channel_id: "UC1",
    channel_name: "Atlas",
    published_at: "2026-11-27T08:00:00Z",
    processing_status: "READY",
    duration_seconds: 1200,
    ai_brief: {
      video_id: "vidYt1",
      headline_zh: "状态机 Agent 工程实战",
      summary_zh: "状态机替代自由循环可降低副作用故障。",
      score: 9.2,
      score_reason_zh: "高密度工程架构",
      recommendation_tier: "MUST_WATCH",
      content_bucket: "DEEP_DIVE",
      is_short_noise: false,
      starred: false,
      is_read: false,
      topics_zh: ["Agent"],
      topic_cluster_zh: "Agent 架构",
      product_opportunities_zh: ["操作审计工作台"],
      business_opportunities_zh: [],
    },
  },
  {
    video_id: "vidBili1",
    title: "Bilibili Local Knowledge Stack",
    provider: "BILIBILI",
    channel_id: "bili_1",
    channel_name: "极客架构演示室",
    published_at: "2026-11-26T08:00:00Z",
    processing_status: "READY",
    duration_seconds: 960,
    ai_brief: {
      video_id: "vidBili1",
      headline_zh: "多源本地知识库反幻觉架构",
      summary_zh: "本地 Obsidian 导出必须回溯时间戳原文。",
      score: 8.9,
      score_reason_zh: "实战证据链",
      recommendation_tier: "MUST_WATCH",
      content_bucket: "DEEP_DIVE",
      is_short_noise: false,
      starred: false,
      is_read: false,
      topics_zh: ["Knowledge"],
      topic_cluster_zh: "Agent 架构",
      product_opportunities_zh: ["双链笔记插件"],
      business_opportunities_zh: [],
    },
  },
  {
    video_id: "vidLocal1",
    title: "architecture-notes.md",
    provider: "LOCAL",
    channel_id: null,
    channel_name: null,
    published_at: "2026-11-25T08:00:00Z",
    processing_status: "READY",
    duration_seconds: null,
    ai_brief: {
      video_id: "vidLocal1",
      headline_zh: "离线文档证据校验总结",
      summary_zh: "纯文档段落检索保障无幻觉降级。",
      score: 8.5,
      score_reason_zh: "高信息密度",
      recommendation_tier: "MUST_WATCH",
      content_bucket: "DEEP_DIVE",
      is_short_noise: false,
      starred: false,
      is_read: false,
      topics_zh: ["Reliability"],
      topic_cluster_zh: "Agent 架构",
      product_opportunities_zh: [],
      business_opportunities_zh: [],
    },
  },
];

describe("Iteration 16 — #Content Multi-Select Cross-Source Workbench", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
    location.hash = "";
  });

  function installFetchMock() {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === "/api/v1/videos" || path.startsWith("/api/v1/videos?")) {
        return jsonResponse({ videos: sampleVideos });
      }
      if (path === "/api/v1/workspace-ai/curation/batch") {
        const parsed = JSON.parse(String(init?.body ?? "{}"));
        return jsonResponse({ updated: parsed.video_ids?.length ?? 0 });
      }
      if (path === "/api/v1/workspace-ai/research/sessions") {
        return jsonResponse({ sessions: [] });
      }
      if (path === "/api/v1/research" || path.startsWith("/api/v1/research?")) {
        return jsonResponse({ research: [], total: 0 });
      }
      if (path === "/api/v1/workspace-ai/overview") {
        return jsonResponse({ overview: null });
      }
      if (path === "/api/v1/workspace-ai/model-status") {
        return jsonResponse({
          ready: true,
          transcriber_ready: true,
          effective_provider: "ollama",
          effective_model: "qwen2.5:7b",
          local_ready: true,
          cloud_ready: false,
        });
      }
      if (path === "/api/v1/workspace-ai/research/ask" || path === "/api/v1/workspace-ai/ask") {
        throw new Error("Ask must NOT be auto-fired when comparing selected items");
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("copies selected cross-source digest, runs batch star & read curation, and hands off scoped comparison draft to Research without auto-asking", async () => {
    location.hash = "#Content";
    const fetchMock = installFetchMock();
    const user = userEvent.setup();
    const writeTextSpy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);

    render(<App />);

    const enterSelectBtn = await screen.findByRole("button", { name: /多选对比|Select & compare/i });
    await user.click(enterSelectBtn);

    const ytBox = await screen.findByRole("checkbox", { name: /YouTube Agent Patterns/i });
    const biliBox = screen.getByRole("checkbox", { name: /Bilibili Local Knowledge Stack/i });
    await user.click(ytBox);
    await user.click(biliBox);

    expect(screen.getByText("已选 2 条")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: /复制所选摘要|Copy selected/i }));
    expect(writeTextSpy).toHaveBeenCalledTimes(1);
    const copied = writeTextSpy.mock.calls[0]?.[0] ?? "";
    expect(copied).toContain("YouTube Agent Patterns");
    expect(copied).toContain("Bilibili Local Knowledge Stack");

    await user.click(screen.getByRole("button", { name: /批量收藏|Star selected/i }));
    await waitFor(() => {
      const curationCalls = fetchMock.mock.calls.filter(
        ([url]) => url === "/api/v1/workspace-ai/curation/batch",
      );
      expect(curationCalls).toHaveLength(1);
      expect(JSON.parse(String(curationCalls[0]?.[1]?.body))).toEqual({
        video_ids: ["vidYt1", "vidBili1"],
        starred: true,
      });
    });

    await user.click(screen.getByRole("button", { name: /对比提问 \(2\) →/ }));

    await waitFor(() => {
      expect(location.hash).toContain("#Research");
    });

    const qInput = (await screen.findByRole("textbox", {
      name: /跨视频提问|Ask across videos/i,
    })) as HTMLTextAreaElement;
    expect(qInput.value).toContain("横向对比这 2 篇指定视频");
    expect(
      fetchMock.mock.calls.some(
        ([url]) => url === "/api/v1/workspace-ai/research/ask" || url === "/api/v1/workspace-ai/ask",
      ),
    ).toBe(false);
  });
});
