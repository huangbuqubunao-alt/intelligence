import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { savePersonalNote } from "./personalNotes";
import { findRelatedContentItems, type RelatedContentCandidate } from "./relatedContent";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

const libraryVideos: RelatedContentCandidate[] = [
  {
    video_id: "vidMain",
    title: "Agent State Machine Core",
    channel_id: "UC_ATLAS",
    channel_name: "Atlas Lab",
    provider: "YOUTUBE",
    duration_seconds: 900,
    ai_brief: {
      video_id: "vidMain",
      headline_zh: "状态机核心",
      summary_zh: "摘要",
      score: 9.4,
      score_reason_zh: "高价值",
      recommendation_tier: "MUST_WATCH",
      content_bucket: "DEEP_DIVE",
      is_short_noise: false,
      topics_zh: ["Agent", "Eval"],
      topic_cluster_zh: "Agent 架构",
      product_opportunities_zh: [],
      business_opportunities_zh: [],
    },
  },
  {
    video_id: "vidPeerTag",
    title: "Deterministic Replay Harnesses",
    channel_id: "UC_OTHER",
    channel_name: "Foundry",
    provider: "YOUTUBE",
    duration_seconds: 850,
    ai_brief: {
      video_id: "vidPeerTag",
      headline_zh: "回放评测工具",
      summary_zh: "摘要二",
      score: 9.1,
      score_reason_zh: "高价值",
      recommendation_tier: "MUST_WATCH",
      content_bucket: "DEEP_DIVE",
      is_short_noise: false,
      topics_zh: ["Testing"],
      topic_cluster_zh: "其他",
      product_opportunities_zh: [],
      business_opportunities_zh: [],
    },
  },
  {
    video_id: "vidShortNoise",
    title: "Quick Promo Short",
    channel_id: "UC_ATLAS",
    channel_name: "Atlas Lab",
    provider: "YOUTUBE",
    duration_seconds: 40,
    ai_brief: {
      video_id: "vidShortNoise",
      headline_zh: "短片",
      summary_zh: "短",
      score: 4.0,
      score_reason_zh: "短片",
      recommendation_tier: "SKIP_NOISE",
      content_bucket: "SHORTS_PROMO",
      is_short_noise: true,
      topics_zh: ["Agent"],
      topic_cluster_zh: "Agent 架构",
      product_opportunities_zh: [],
      business_opportunities_zh: [],
    },
  },
];

describe("Iteration 26 — Reader connected knowledge & pairwise Research compare", () => {
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

  it("ranks shared personal #tags above topic/channel overlap and filters out short noise", () => {
    savePersonalNote("vidMain", { text: "Main insight", tags: ["核心结论"] });
    savePersonalNote("vidPeerTag", { text: "Peer insight", tags: ["核心结论"] });

    const matches = findRelatedContentItems(
      libraryVideos[0],
      libraryVideos,
      {
        vidMain: { text: "Main", tags: ["核心结论"], updatedAt: "" },
        vidPeerTag: { text: "Peer", tags: ["核心结论"], updatedAt: "" },
      },
      true,
      4,
    );

    expect(matches).toHaveLength(1);
    expect(matches[0].video.video_id).toBe("vidPeerTag");
    expect(matches[0].reasonLabel).toBe("共标 #核心结论");
  });

  it("renders Connected in your library inside Reader and routes 2-way compare into Research", async () => {
    savePersonalNote("vidMain", { text: "Main", tags: ["核心结论"] });
    savePersonalNote("vidPeerTag", { text: "Peer", tags: ["核心结论"] });
    location.hash = "#Content/vidMain";

    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/videos" || path.startsWith("/api/v1/videos?")) {
          return jsonResponse({ videos: libraryVideos });
        }
        if (path === "/api/v1/videos/vidMain") {
          return jsonResponse({
            video: { ...libraryVideos[0], processing_status: "READY" },
            transcript: { status: "AVAILABLE", text: "State machine transcript", timed_segments: [] },
            note: { v2: { status: "AVAILABLE", summary: "Summary", core_points: [] } },
            intelligence_result: { status: "AVAILABLE", items: [] },
            evidence: [],
            history: [],
          });
        }
        if (path === "/api/v1/research" || path.startsWith("/api/v1/research?")) {
          return jsonResponse({ research: [], total: 0 });
        }
        if (path === "/api/v1/workspace-ai/research/sessions") {
          return jsonResponse({
            sessions: [],
            suggested_questions: [],
            scope_options: {
              channels: [],
              topic_clusters: [],
              videos: libraryVideos.slice(0, 2).map((v) => ({
                video_id: v.video_id,
                title: v.title,
                starred: false,
              })),
            },
          });
        }
        return jsonResponse({});
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("关联延伸阅读")).toBeTruthy();
    expect(screen.getByText(/共标 #核心结论/)).toBeTruthy();
    expect(screen.queryByText("Deterministic Replay Harnesses")).toBeNull();

    const expandBtn = screen.getByRole("button", { name: "展开关联 (1)" });
    await user.click(expandBtn);

    expect(await screen.findByText("Deterministic Replay Harnesses")).toBeTruthy();

    const compareBtn = screen.getByRole("button", { name: "对比提问 →" });
    expect(compareBtn.closest("button.reader-related-open")).toBeNull();
    await user.click(compareBtn);

    await waitFor(() => {
      expect(location.hash).toBe("#Research");
    });
    expect(await screen.findByText(/已锁定 2 篇指定源视频/)).toBeTruthy();
  });
});
