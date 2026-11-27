import { cleanup, render, screen } from "@testing-library/react";
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

describe("Iteration 28 — Home study momentum card & Intelligence personal note badges", () => {
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

  it("displays honest reading progress bar & personal note counts on #Home", async () => {
    savePersonalNote("vidMom1", {
      text: "Great insight",
      tags: ["核心结论", "状态机"],
    });
    location.hash = "#Home";
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path.startsWith("/api/v1/dashboard")) {
          return jsonResponse({
            intelligence: [],
            saved_intelligence_ids: [],
            pinned_topics: [{ topic_id: "top_1", name: "Agent 架构", current_state: "ACTIVE" }],
            weekly_v1: [],
            needs_attention: [],
            operations: { source_count: 1 },
            demo_mode: false,
          });
        }
        if (path.startsWith("/api/v1/videos")) {
          return jsonResponse({
            videos: [
              {
                video_id: "vidMom1",
                title: "Read Item",
                provider: "YOUTUBE",
                processing_status: "READY",
                duration_seconds: 800,
                ai_brief: {
                  video_id: "vidMom1",
                  headline_zh: "已读内容",
                  summary_zh: "摘要",
                  score: 9.2,
                  score_reason_zh: "好",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  is_read: true,
                  topics_zh: ["Agent"],
                  topic_cluster_zh: "Agent 架构",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
              {
                video_id: "vidMom2",
                title: "Unread Item",
                provider: "YOUTUBE",
                processing_status: "READY",
                duration_seconds: 800,
                ai_brief: {
                  video_id: "vidMom2",
                  headline_zh: "未读内容",
                  summary_zh: "摘要二",
                  score: 8.8,
                  score_reason_zh: "好",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  is_read: false,
                  topics_zh: ["Agent"],
                  topic_cluster_zh: "Agent 架构",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
            ],
          });
        }
        return jsonResponse({});
      }),
    );

    render(<App />);

    expect(await screen.findByText("知识沉淀进度")).toBeTruthy();
    expect(await screen.findByText("已精读 1 / 2 篇长内容")).toBeTruthy();
    expect(screen.getByText("50%")).toBeTruthy();
    expect(screen.getByText("本机已沉淀 1 篇个人批注 · 2 个自建标签")).toBeTruthy();
    expect(screen.getByRole("button", { name: "查看笔记内容" })).toBeTruthy();
  });

  it("displays Noted badge with first #tag on #Intelligence items linked to noted videos", async () => {
    savePersonalNote("vidNotedIntel", {
      text: "Important synthesis",
      tags: ["高价值"],
    });
    location.hash = "#Intelligence";
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/intelligence") {
          return jsonResponse({
            intelligence: [
              {
                intelligence_id: "int_noted_1",
                status: "AVAILABLE",
                trusted: true,
                claim_kind: "SYSTEM_INFERENCE",
                state: "VERIFIED",
                effective_published_at: "2026-11-27T08:00:00Z",
                linked_topics: [],
                card: {
                  core_conclusion: "State machine separation yields deterministic evals.",
                  user_relevant_information: ["Isolates side effects cleanly."],
                  important_new_information: [],
                  meaningful_details: [],
                  source_id: "src1",
                  source_display_name: "Atlas",
                  source_url: "https://example.com/1",
                  video_id: "vidNotedIntel",
                  video_title: "State Machines",
                  evidence_links: [],
                },
              },
            ],
          });
        }
        if (path === "/api/v1/topics") {
          return jsonResponse({ topics: [] });
        }
        return jsonResponse({});
      }),
    );

    render(<App />);

    expect(
      await screen.findByText("State machine separation yields deterministic evals."),
    ).toBeTruthy();
    expect(screen.getByText("已批注 · #高价值")).toBeTruthy();
  });
});
