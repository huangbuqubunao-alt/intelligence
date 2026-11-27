import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { savePersonalNote } from "./personalNotes";
import {
  clearSavedContentViews,
  deleteSavedContentView,
  matchesSavedContentView,
  readSavedContentViews,
  saveContentView,
  suggestSavedViewName,
  type ContentFilterCriteria,
} from "./savedViews";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

const sampleVideos = {
  videos: [
    {
      video_id: "vidView1",
      title: "Agent Evaluation Deep Dive",
      provider: "YOUTUBE",
      channel_id: "UC1",
      channel_name: "Atlas",
      published_at: "2026-11-27T08:00:00Z",
      processing_status: "READY",
      duration_seconds: 900,
      ai_brief: {
        video_id: "vidView1",
        headline_zh: "Agent 评测体系",
        summary_zh: "核心摘要一",
        score: 9.4,
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
      video_id: "vidView2",
      title: "Casual Update Vlog",
      provider: "YOUTUBE",
      channel_id: "UC2",
      channel_name: "Beta",
      published_at: "2026-11-26T08:00:00Z",
      processing_status: "READY",
      duration_seconds: 700,
      ai_brief: {
        video_id: "vidView2",
        headline_zh: "日常开发流水账",
        summary_zh: "核心摘要二",
        score: 6.9,
        score_reason_zh: "一般参考",
        recommendation_tier: "WORTH_SKIMMING",
        content_bucket: "DEEP_DIVE",
        is_short_noise: false,
        starred: false,
        is_read: false,
        topics_zh: ["Misc"],
        topic_cluster_zh: "其他",
        product_opportunities_zh: [],
        business_opportunities_zh: [],
      },
    },
  ],
};

describe("Iteration 24 — Content saved smart filter views", () => {
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

  it("suggests names, deduplicates matching filter criteria, and deletes views cleanly", () => {
    const filters: ContentFilterCriteria = {
      searchQuery: "",
      providerFilter: "ALL",
      bucketFilter: "MUST_WATCH",
      topicFilter: "ALL",
      channelFilter: "ALL",
      tagFilter: "核心结论",
    };
    expect(suggestSavedViewName(filters, true)).toBe("必看 · #核心结论");

    const afterFirst = saveContentView({ ...filters, name: "我的周巡检" }, true);
    expect(afterFirst).toHaveLength(1);
    expect(matchesSavedContentView(afterFirst[0], filters)).toBe(true);

    const renamed = saveContentView({ ...filters, name: "重命名周巡检" }, true);
    expect(renamed).toHaveLength(1);
    expect(renamed[0].name).toBe("重命名周巡检");

    expect(deleteSavedContentView(renamed[0].id)).toHaveLength(0);
    clearSavedContentViews();
    expect(readSavedContentViews()).toEqual([]);
  });

  it("saves multi-facet Content filters, restores them after reset, and deletes the preset via sibling button", async () => {
    savePersonalNote("vidView1", {
      text: "Important eval insight",
      tags: ["核心结论"],
    });
    location.hash = "#Content";
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/videos" || path.startsWith("/api/v1/videos?")) {
          return jsonResponse(sampleVideos);
        }
        return jsonResponse({});
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("Agent Evaluation Deep Dive")).toBeTruthy();
    expect(screen.getByText("Casual Update Vlog")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "必看长视频" }));
    await user.click(screen.getByRole("button", { name: "#核心结论 (1)" }));
    expect(screen.queryByText("Casual Update Vlog")).toBeNull();

    await user.click(screen.getByRole("button", { name: "保存视图" }));
    const nameInput = screen.getByLabelText("常用视图名称") as HTMLInputElement;
    await user.clear(nameInput);
    await user.type(nameInput, "核心必看精选");
    await user.click(screen.getByRole("button", { name: "保存" }));

    const presetBtn = await screen.findByRole("button", { name: "核心必看精选" });
    expect(presetBtn.getAttribute("aria-pressed")).toBe("true");
    expect(presetBtn.closest(".content-saved-view-pill")).not.toBeNull();

    await user.click(screen.getByRole("button", { name: "重置筛选" }));
    expect(await screen.findByText("Casual Update Vlog")).toBeTruthy();
    expect(screen.getByRole("button", { name: "核心必看精选" }).getAttribute("aria-pressed")).toBe(
      "false",
    );

    await user.click(screen.getByRole("button", { name: "核心必看精选" }));
    await waitFor(() => {
      expect(screen.queryByText("Casual Update Vlog")).toBeNull();
    });
    expect(screen.getByText("Agent Evaluation Deep Dive")).toBeTruthy();

    const deleteBtn = screen.getByRole("button", { name: "删除常用视图 核心必看精选" });
    expect(deleteBtn.closest("button.content-saved-view-select")).toBeNull();
    await user.click(deleteBtn);
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "核心必看精选" })).toBeNull();
    });
  });
});
