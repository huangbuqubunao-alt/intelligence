import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { savePersonalNote } from "./personalNotes";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

const videosPayload = {
  videos: [
    {
      video_id: "vidTag1",
      title: "Agent State Machine Alpha",
      provider: "YOUTUBE",
      channel_id: "UC1",
      channel_name: "Atlas",
      published_at: "2026-11-27T08:00:00Z",
      processing_status: "READY",
      duration_seconds: 900,
      ai_brief: {
        video_id: "vidTag1",
        headline_zh: "状态机核心结论",
        summary_zh: "核心摘要一",
        score: 9.3,
        score_reason_zh: "高价值",
        recommendation_tier: "MUST_WATCH",
        content_bucket: "DEEP_DIVE",
        is_short_noise: false,
        starred: false,
        is_read: false,
        topics_zh: ["Agent"],
        topic_cluster_zh: "Agent 架构",
        product_opportunities_zh: [],
        business_opportunities_zh: [],
      },
    },
    {
      video_id: "vidUntagged2",
      title: "Other Video Beta",
      provider: "BILIBILI",
      channel_id: "bili_1",
      channel_name: "Beta",
      published_at: "2026-11-26T08:00:00Z",
      processing_status: "READY",
      duration_seconds: 800,
      ai_brief: {
        video_id: "vidUntagged2",
        headline_zh: "普通视频摘要",
        summary_zh: "核心摘要二",
        score: 8.2,
        score_reason_zh: "参考",
        recommendation_tier: "WORTH_SKIMMING",
        content_bucket: "DEEP_DIVE",
        is_short_noise: false,
        starred: false,
        is_read: false,
        topics_zh: ["Tools"],
        topic_cluster_zh: "工具链",
        product_opportunities_zh: [],
        business_opportunities_zh: [],
      },
    },
  ],
};

describe("Iteration 20 — Personal #Tag Taxonomy across #Content and #Topics", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
    savePersonalNote("vidTag1", {
      text: "关键架构思考",
      tags: ["核心结论", "Agent架构"],
    });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
    location.hash = "";
  });

  function installFetchMock() {
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/videos" || path.startsWith("/api/v1/videos?")) {
          return jsonResponse(videosPayload);
        }
        if (path === "/api/v1/topics") {
          return jsonResponse({
            topics: [
              {
                topic_id: "top_1",
                name: "Agent 架构",
                current_state: "ACTIVE",
                lifecycle: "ACTIVE",
                pinned: false,
                independence: "VERIFIED",
                ai_evolution: {
                  video_count: 1,
                  must_watch_count: 1,
                  recent_7d_count: 1,
                  avg_score: 9.3,
                  source_channels: ["Atlas"],
                  latest_headline_zh: "状态机核心结论",
                },
              },
            ],
          });
        }
        if (path === "/api/v1/workspace-ai/research/sessions") {
          return jsonResponse({ sessions: [] });
        }
        if (path === "/api/v1/intelligence") {
          return jsonResponse({ intelligence: [] });
        }
        return jsonResponse({});
      }),
    );
  }

  it("bridges personal tags from #Topics into tag-filtered #Content and resets cleanly", async () => {
    location.hash = "#Topics";
    installFetchMock();
    const user = userEvent.setup();

    render(<App />);

    expect(await screen.findByText("我的自建标签")).toBeTruthy();
    const topicTagChip = await screen.findByRole("button", { name: "#核心结论 (1)" });
    await user.click(topicTagChip);

    await waitFor(() => {
      expect(location.hash).toBe("#Content");
    });

    expect(await screen.findByText("Agent State Machine Alpha")).toBeTruthy();
    expect(screen.queryByText("Other Video Beta")).toBeNull();

    const activeTagChip = screen.getByRole("button", { name: "#核心结论 (1)" });
    expect(activeTagChip.getAttribute("aria-pressed")).toBe("true");

    await user.click(screen.getByRole("button", { name: "重置筛选" }));
    expect(await screen.findByText("Other Video Beta")).toBeTruthy();
  });

  it("filters Content by personal tag via Cmd+K command palette selection", async () => {
    location.hash = "#Content";
    installFetchMock();

    render(<App />);
    await screen.findByText("Other Video Beta");

    fireEvent.click(screen.getByRole("button", { name: /搜索与直达/i }));
    const combobox = await screen.findByRole("combobox", { name: "搜索页面、内容、洞察或命令" }, { timeout: 8000 });
    fireEvent.change(combobox, { target: { value: "#Agent架构" } });

    const filterOption = await screen.findByText("按个人标签筛选：#Agent架构");
    fireEvent.click(filterOption);

    await waitFor(() => {
      expect(screen.queryByText("Other Video Beta")).toBeNull();
    });
    expect(screen.getByText("Agent State Machine Alpha")).toBeTruthy();
  }, 15_000);
});
