import { cleanup, render, screen, waitFor } from "@testing-library/react";
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

describe("Iteration 35 — Power-user Go-To keyboard chords (G+key), Shortcuts Modal sync & Command Palette noted action", () => {
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

  it("navigates via G+T / G+S without firing Content S star, ignores G inside inputs, opens noted content via ⌘K, and displays G chords + N in Shortcuts Modal", async () => {
    savePersonalNote("vidNoted35", {
      text: "Shortcut navigation verification note",
      tags: ["快捷键"],
    });

    const curationPosts: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (String(path).includes("/curation")) {
          curationPosts.push(String(path));
        }
        if (path === "/api/v1/system") {
          return jsonResponse({ health: "ready", edition: "LOCAL" });
        }
        if (path === "/api/v1/dashboard") {
          return jsonResponse({
            intelligence: [],
            saved_intelligence_ids: [],
            pinned_topics: [],
            needs_attention: [],
          });
        }
        if (path === "/api/v1/topics") {
          return jsonResponse({ topics: [] });
        }
        if (String(path).startsWith("/api/v1/videos")) {
          return jsonResponse({
            videos: [
              {
                video_id: "vidNoted35",
                title: "Annotated Target Video",
                provider: "YOUTUBE",
                channel_name: "Atlas Lab",
                duration_seconds: 900,
                processing_status: "READY",
                published_at: "2026-11-27T08:00:00Z",
                ai_brief: {
                  video_id: "vidNoted35",
                  score: 9.1,
                  score_reason_zh: "高信息密度",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  headline_zh: "快捷键验证高优内容",
                  summary_zh: "摘要说明",
                  key_takeaways_zh: ["核心要点"],
                  topics_zh: ["Agent"],
                  topic_cluster_zh: "Agent 架构",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                },
              },
              {
                video_id: "vidUnnoted35",
                title: "Unnoted Other Video",
                provider: "YOUTUBE",
                channel_name: "Atlas Lab",
                duration_seconds: 900,
                processing_status: "READY",
                published_at: "2026-11-26T08:00:00Z",
                ai_brief: {
                  video_id: "vidUnnoted35",
                  score: 8.4,
                  score_reason_zh: "对照组",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  headline_zh: "未批注对照内容",
                  summary_zh: "对照组摘要",
                  key_takeaways_zh: ["对照要点"],
                  topics_zh: ["Agent"],
                  topic_cluster_zh: "Agent 架构",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                },
              },
            ],
          });
        }
        if (path === "/api/v1/workspace-ai/settings") {
          return jsonResponse({
            mode: "LOCAL_OLLAMA",
            local_ready: true,
          });
        }
        if (path === "/api/v1/settings") {
          return jsonResponse({
            general: {
              output_language: "zh-CN",
              output_language_updated_at: null,
            },
            providers: [],
          });
        }
        if (path === "/api/v1/settings/preferences") {
          return jsonResponse({ active: [], history: [] });
        }
        if (path === "/api/v1/settings/source-policy") {
          return jsonResponse({
            policy: {
              focus_rules: [],
              ignore_rules: [],
              distillation_style: "BALANCED",
              initial_history_count: 5,
              per_run_max_new_videos: 5,
            },
          });
        }
        if (path === "/api/v1/settings/resource-usage") {
          return jsonResponse({ usage: [] });
        }
        return jsonResponse({});
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "首页" });

    // G + T -> Topics
    await user.keyboard("gt");
    expect(await screen.findByRole("heading", { name: "主题" })).toBeTruthy();

    // Open Command Palette via Cmd+K and click "查看有批注的内容"
    await user.keyboard("{Meta>}k{/Meta}");
    const notedCmd = await screen.findByText("查看有批注的内容");
    await user.click(notedCmd);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "有笔记" }).getAttribute("aria-pressed")).toBe("true");
    });

    // Typing G + S inside Content search input must NOT navigate away
    const searchInput = (await screen.findByPlaceholderText("按标题或频道筛选内容…")) as HTMLInputElement;
    await user.click(searchInput);
    await user.keyboard("gs");
    expect(searchInput.value).toBe("gs");
    expect(screen.getByRole("heading", { name: "内容" })).toBeTruthy();
    await user.clear(searchInput);
    searchInput.blur();

    // While in #Content (where single-key `s` would star), G + S must navigate to #Settings and NOT dispatch curation POST!
    await user.keyboard("gs");
    expect(await screen.findByRole("heading", { name: "设置" })).toBeTruthy();
    expect(curationPosts).toHaveLength(0);

    // Open Keyboard Shortcuts Modal via `?` and verify both `页面直达（G + 键）` and `N` shortcut appear
    await user.keyboard("?");
    expect(await screen.findByRole("heading", { name: "键盘快捷键指南" })).toBeTruthy();
    expect(screen.getByText("页面直达（G + 键）")).toBeTruthy();
    expect(screen.getByText("聚焦「我的思考与批注」输入框")).toBeTruthy();
  });
});
