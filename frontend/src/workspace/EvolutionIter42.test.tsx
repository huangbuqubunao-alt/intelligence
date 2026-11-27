import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import {
  collectWorkspaceChecklistItems,
  extractNoteChecklistItems,
  toggleChecklistLineInMarkdown,
  togglePersonalNoteChecklistItem,
} from "./actionChecklists";
import { readPersonalNote, savePersonalNote } from "./personalNotes";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 42 — Home interactive learning action checklist from personal notes", () => {
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

  it("extracts Markdown tasks cleanly, prioritizes open items, and toggles checkboxes back to storage", () => {
    const emptyBlank = extractNoteChecklistItems(
      "vid1",
      "### 实践行动项\n- [ ] \n- [ ] 实现上下文压缩策略\n- [x] 已验证接口契约",
      "2026-11-27T10:00:00Z",
    );
    expect(emptyBlank).toHaveLength(2);
    expect(emptyBlank[0]).toMatchObject({
      videoId: "vid1",
      lineIndex: 2,
      text: "实现上下文压缩策略",
      checked: false,
    });
    expect(emptyBlank[1]).toMatchObject({
      videoId: "vid1",
      lineIndex: 3,
      text: "已验证接口契约",
      checked: true,
    });

    const toggled = toggleChecklistLineInMarkdown(
      "Header\r\n- [ ] Task A\r\n* [x] Task B",
      1,
    );
    expect(toggled).toBe("Header\r\n- [x] Task A\r\n* [x] Task B");

    savePersonalNote("vidOld", {
      text: "- [x] Done earlier\n- [ ] Pending old",
      tags: ["复盘"],
    });
    savePersonalNote("vidNew", {
      text: "- [ ] Pending new",
      tags: [],
    });
    const sorted = collectWorkspaceChecklistItems();
    expect(sorted.filter((i) => !i.checked)).toHaveLength(2);
    expect(sorted[sorted.length - 1].checked).toBe(true);

    togglePersonalNoteChecklistItem("vidOld", 1);
    expect(readPersonalNote("vidOld")?.text).toContain("- [x] Pending old");
  });

  it("renders open note action items inside Home Study Momentum, flips status cleanly, and jumps to source video", async () => {
    savePersonalNote("vidAct1", {
      text: "### 实践行动项\n- [ ] 在项目中落地工具沙箱鉴权\n- [x] 阅读完原始架构文档",
      tags: ["架构"],
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
                intelligence_id: "intAct1",
                status: "AVAILABLE",
                trusted: true,
                state: "NEW",
                linked_topics: [],
                card: {
                  core_conclusion: "沙箱最小权限结论",
                  user_relevant_information: [],
                  important_new_information: [],
                  meaningful_details: [],
                  source_id: "s1",
                  source_display_name: "System Craft",
                  source_url: null,
                  video_id: "vidAct1",
                  video_title: "Agent Sandbox Deep Dive",
                },
              },
            ],
            saved_intelligence_ids: [],
            pinned_topics: [],
            needs_attention: [],
          });
        }
        if (path.startsWith("/api/v1/videos/vidAct1")) {
          return jsonResponse({
            video_id: "vidAct1",
            title: "Agent Sandbox Deep Dive",
            channel_name: "System Craft",
            processing_status: "SUMMARIZED",
            ai_brief: { score: 9.1, headline_zh: "沙箱最小权限设计" },
            transcript_text: "Transcript body",
          });
        }
        if (path.startsWith("/api/v1/videos")) {
          return jsonResponse({
            videos: [
              {
                video_id: "vidAct1",
                title: "Agent Sandbox Deep Dive",
                channel_name: "System Craft",
                duration_seconds: 900,
                ai_brief: { score: 9.1, headline_zh: "沙箱最小权限设计" },
              },
            ],
          });
        }
        return jsonResponse({});
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    const momentumHeading = await screen.findByRole("heading", { name: "知识沉淀进度" });
    const momentumPanel = momentumHeading.closest("section")!;
    expect(within(momentumPanel).getByText("待办行动项 (1)")).toBeTruthy();
    expect(within(momentumPanel).getByText("在项目中落地工具沙箱鉴权")).toBeTruthy();
    expect(within(momentumPanel).queryByText("阅读完原始架构文档")).toBeNull();

    await user.click(within(momentumPanel).getByRole("button", { name: "显示已完成 (1)" }));
    expect(within(momentumPanel).getByText("阅读完原始架构文档")).toBeTruthy();

    const openCheckbox = within(momentumPanel).getByRole("checkbox", {
      name: "标为完成：在项目中落地工具沙箱鉴权",
    });
    await user.click(openCheckbox);

    expect(within(momentumPanel).getByText("待办行动项 (0)")).toBeTruthy();
    expect(readPersonalNote("vidAct1")?.text).toContain("- [x] 在项目中落地工具沙箱鉴权");

    await user.click(
      within(momentumPanel).getAllByRole("button", { name: /沙箱最小权限设计/ })[0],
    );
    expect(decodeURIComponent(window.location.hash)).toContain("#Content/vidAct1");
  });
});
