import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import {
  buildActiveRecallDeck,
  markRecalledToday,
  readRecalledTodayIds,
} from "./activeRecall";
import { savePersonalNote } from "./personalNotes";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 32 — Home Active Recall card", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("yia.onboarding_completed.v1", "1");
    window.location.hash = "#Home";
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
    window.location.hash = "";
  });

  it("prioritizes noted entries over unnoted entries and auto-resets daily recall progress on a new calendar date", () => {
    savePersonalNote("vidNoted", {
      text: "My personal synthesis check",
      tags: ["核心结论"],
    });

    const deck = buildActiveRecallDeck(
      [
        {
          video_id: "vidHighUnnoted",
          title: "Unnoted High Score Video",
          channel_name: "Channel A",
          ai_brief: { score: 9.6, headline_zh: "高分结论", key_takeaways_zh: ["要点一"] },
        },
        {
          video_id: "vidNoted",
          title: "My Annotated Video",
          channel_name: "Channel B",
          ai_brief: { score: 7.5, headline_zh: "个人笔记关联结论", key_takeaways_zh: ["边界要点"] },
        },
      ],
      [],
      true,
    );

    expect(deck.map((card) => card.videoId)).toEqual(["vidNoted", "vidHighUnnoted"]);

    markRecalledToday("vidNoted", new Date(2026, 10, 27, 10, 0));
    expect(readRecalledTodayIds(new Date(2026, 10, 27, 23, 0)).has("vidNoted")).toBe(true);
    expect(readRecalledTodayIds(new Date(2026, 10, 28, 8, 0)).size).toBe(0);
  });

  it("hides answer until user clicks 展开核对, marks recalled today with 记住了 ✓, and advances card", async () => {
    savePersonalNote("vidRec1", {
      text: "记忆检验批注内容 Alpha",
      tags: ["复盘"],
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/system") {
          return jsonResponse({ health: "ready", edition: "LOCAL" });
        }
        if (path === "/api/v1/dashboard") {
          return jsonResponse({
            intelligence: [
              {
                intelligence_id: "intRec1",
                status: "AVAILABLE",
                trusted: true,
                state: "NEW",
                linked_topics: [{ topic_id: "t1", name: "Agent" }],
                card: {
                  core_conclusion: "确定性工具校验是核心结论 Alpha",
                  user_relevant_information: ["核心校验要点 1"],
                  important_new_information: [],
                  meaningful_details: [],
                  source_id: "s1",
                  source_display_name: "Atlas Lab",
                  source_url: null,
                  video_id: "vidRec1",
                  video_title: "First Recall Card",
                  original_video_url: null,
                  evidence_links: [],
                },
              },
              {
                intelligence_id: "intRec2",
                status: "AVAILABLE",
                trusted: true,
                state: "NEW",
                linked_topics: [{ topic_id: "t1", name: "Agent" }],
                card: {
                  core_conclusion: "第二张卡的隐藏答案 Beta",
                  user_relevant_information: [],
                  important_new_information: [],
                  meaningful_details: [],
                  source_id: "s1",
                  source_display_name: "Atlas Lab",
                  source_url: null,
                  video_id: "vidRec2",
                  video_title: "Second Recall Card",
                  original_video_url: null,
                  evidence_links: [],
                },
              },
            ],
            saved_intelligence_ids: [],
            pinned_topics: [],
            needs_attention: [],
          });
        }
        if (path.startsWith("/api/v1/videos")) {
          return jsonResponse({
            videos: [
              {
                video_id: "vidRec1",
                title: "First Recall Card",
                channel_name: "Atlas Lab",
                duration_seconds: 900,
                ai_brief: { score: 9.2, headline_zh: "确定性工具校验是核心结论 Alpha" },
              },
              {
                video_id: "vidRec2",
                title: "Second Recall Card",
                channel_name: "Atlas Lab",
                duration_seconds: 900,
                ai_brief: { score: 8.8, headline_zh: "第二张卡的隐藏答案 Beta" },
              },
            ],
          });
        }
        return jsonResponse({});
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    const recallHeading = await screen.findByRole("heading", { name: "温故知新 · 主动回忆" });
    const recallSection = recallHeading.closest("section")!;
    expect(within(recallSection).getByText("First Recall Card")).toBeTruthy();
    expect(within(recallSection).getByText("今日已复习 0 / 2")).toBeTruthy();
    expect(within(recallSection).queryByText("确定性工具校验是核心结论 Alpha")).toBeNull();
    expect(within(recallSection).queryByText(/记忆检验批注内容 Alpha/)).toBeNull();

    await user.click(within(recallSection).getByRole("button", { name: "展开核对" }));

    expect(within(recallSection).getByText("确定性工具校验是核心结论 Alpha")).toBeTruthy();
    expect(within(recallSection).getByText(/记忆检验批注内容 Alpha/)).toBeTruthy();

    await user.click(within(recallSection).getByRole("button", { name: "记住了 ✓" }));

    expect(within(recallSection).getByText("今日已复习 1 / 2")).toBeTruthy();
    expect(within(recallSection).getByText("Second Recall Card")).toBeTruthy();
    expect(within(recallSection).queryByText("第二张卡的隐藏答案 Beta")).toBeNull();
    expect(readRecalledTodayIds().has("vidRec1")).toBe(true);
  });
});
