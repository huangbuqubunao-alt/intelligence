import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { mergePersonalNoteIntoMarkdown, savePersonalNote } from "./personalNotes";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

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

it("keeps Obsidian Markdown unchanged when personal note is empty, and appends demarcated section when populated", () => {
  const base = "# Title\n\n## Core Summary\nContent here.\n";
  expect(mergePersonalNoteIntoMarkdown(base, null, true)).toBe(base);
  expect(
    mergePersonalNoteIntoMarkdown(base, { text: "   ", tags: [], updatedAt: "2026-11-27T09:00:00Z" }, true),
  ).toBe(base);

  const mergedZh = mergePersonalNoteIntoMarkdown(
    base,
    { text: "Very sharp insight.", tags: ["架构", "Agent"], updatedAt: "2026-11-27T09:00:00Z" },
    true,
  );
  expect(mergedZh).toContain("## 我的思考与摘录");
  expect(mergedZh).toContain("#架构 #Agent");
  expect(mergedZh).toContain("Very sharp insight.");
});

it("clips evidence quote into ReaderPersonalNoteCard, merges into Obsidian copy, persists across reload, and displays Content note badge", async () => {
  location.hash = "#Content/vidNoteDemo";
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) => {
      if (path === "/api/v1/videos" || path.startsWith("/api/v1/videos?")) {
        return jsonResponse({
          videos: [
            {
              video_id: "vidNoteDemo",
              title: "State Machines Video",
              provider: "YOUTUBE",
              channel_id: "UC1",
              channel_name: "Atlas",
              published_at: "2026-11-26T10:00:00Z",
              processing_status: "READY",
              duration_seconds: 1200,
              ai_brief: {
                video_id: "vidNoteDemo",
                headline_zh: "状态机设计指南",
                summary_zh: "核心摘要。",
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
          ],
        });
      }
      if (path === "/api/v1/videos/vidNoteDemo") {
        return jsonResponse({
          video: {
            video_id: "vidNoteDemo",
            title: "State Machines Video",
            provider: "YOUTUBE",
            media_kind: "VIDEO",
            source_url: "https://www.youtube.com/watch?v=abcdefghijk",
            channel_id: "UC1",
            channel_name: "Atlas",
            processing_status: "READY",
            published_at: "2026-11-26T10:00:00Z",
            duration_seconds: 1200,
            ai_brief: {
              video_id: "vidNoteDemo",
              headline_zh: "状态机设计指南",
              summary_zh: "核心摘要。",
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
          transcript: {
            status: "AVAILABLE",
            text: "Explicit state transitions keep agents deterministic.",
          },
          note: { v2: { status: "NOT_AVAILABLE" } },
          intelligence_result: { status: "NOT_AVAILABLE" },
          history: [],
          obsidian_markdown: "# State Machines Video\n\n[[Agent 架构]]\n",
        });
      }
      if (path.endsWith("/evidence")) {
        return jsonResponse({
          evidence: [
            {
              evidence_id: "ev-clip-1",
              artifact_id: "art-1",
              locator_type: "TIMED_SEGMENT",
              start_ms: 12000,
              end_ms: 34000,
              start_line: null,
              end_line: null,
              source_language: "en",
              translation_target_language: "zh-CN",
              translated_language: "zh-CN",
              translated_excerpt: "显式状态迁移让 Agent 更确定。",
              original_excerpt: "Explicit state transitions keep agents deterministic.",
              lineage_kind: "CANONICAL_TRANSCRIPT",
              role: "PRIMARY",
              created_at: "2026-11-26T08:00:00Z",
            },
          ],
        });
      }
      if (path.endsWith("/deep-analysis")) {
        return jsonResponse({
          deep_analysis: {
            status: {
              availability: "NOT_QUALIFIED",
              reason_code: "NO_QUALIFIED_MODEL",
              qualified: false,
              production_eligible: false,
              consent_required: false,
              routes: [],
            },
            result: null,
          },
        });
      }
      return jsonResponse({});
    }),
  );

  const user = userEvent.setup();
  const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
  const firstView = render(<App />);

  // Open Evidence drawer and clip quote
  await user.click(await screen.findByRole("button", { name: /查看时间轴原话证据/ }));
  await user.click(await screen.findByRole("button", { name: /摘录到笔记：0:12–0:34/ }));

  // Close drawer via Escape and verify ReaderPersonalNoteCard auto-expanded with clipped quote
  await user.keyboard("{Escape}");
  const textarea = (await screen.findByRole("textbox", {
    name: "我的思考与批注内容",
  })) as HTMLTextAreaElement;
  expect(textarea.value).toContain("Explicit state transitions keep agents deterministic.");

  // Add tags and reflection, blur to flush save
  await user.type(
    screen.getByRole("textbox", { name: "个人标签（逗号或空格分隔）" }),
    "状态机, 生产实践",
  );
  fireEvent.blur(screen.getByRole("textbox", { name: "个人标签（逗号或空格分隔）" }));

  // Copy Obsidian wikilinks note and verify personal notes & tags merged in
  await user.click(screen.getByRole("button", { name: "复制双链笔记" }));
  expect(writeText).toHaveBeenCalledWith(expect.stringContaining("## 我的思考与摘录"));
  expect(writeText).toHaveBeenCalledWith(expect.stringContaining("#状态机 #生产实践"));

  // Remount cleanly (reload simulation) and verify persistence + Content badge
  firstView.unmount();
  location.hash = "#Content";
  render(<App />);
  expect(await screen.findByText("有笔记")).toBeTruthy();

  // Cleanup helper check
  savePersonalNote("vidNoteDemo", { text: "", tags: [] });
});
