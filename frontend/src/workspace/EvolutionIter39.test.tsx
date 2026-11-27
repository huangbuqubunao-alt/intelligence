import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readPersonalNote } from "./personalNotes";
import { UiLanguageProvider } from "./uiLanguage";
import { WorkspaceAiResearchPanel } from "./WorkspaceAiWidgets";

function okJson(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("Iteration 39 (EVO-W7-04): #Research pinned-only filter & save grounded answer to cited source note", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("filters history by pinned-only, saves grounded answer to cited source personal note without server POST, and hides save button on refused sessions", async () => {
    const askPosts: string[] = [];
    vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/research/ask") && init?.method === "POST") {
        askPosts.push(url);
      }
      if (url.includes("/api/v1/workspace-ai/research/sessions")) {
        return okJson({
          sessions: [
            {
              session_id: "sess-grounded",
              question: "为什么必须使用显式状态机？",
              answer_zh: "确定性状态机能消除盲循环幻觉并保证单步可审计 [E1]。",
              pinned: true,
              refused: false,
              fact_verification_state: "SUPPORTED",
              source_integrity_status: "VERIFIED",
              verified_citation_count: 1,
              covered_source_count: 1,
              key_takeaways_zh: ["显式状态转移可追踪"],
              action_items_zh: [],
              citations: [
                {
                  ref_label: "E1",
                  video_id: "vid-state-machine",
                  video_title: "Deterministic State Machines",
                  channel_name: "Atlas Lab",
                  evidence_id: "ev-1",
                  timestamp_label: "04:12–04:45",
                  excerpt: "Explicit state transitions prevent silent agent loops.",
                  verified: true,
                },
              ],
              obsidian_markdown: "# [[为什么必须使用显式状态机？]]\n...",
              updated_at: "2026-11-27T08:00:00Z",
            },
            {
              session_id: "sess-refused",
              question: "未收录材料里提了什么未公开数据？",
              answer_zh: "当前所选资料中未包含该信息，无法编造结论。",
              pinned: false,
              refused: true,
              fact_verification_state: "NO_VERIFIED_CITATIONS",
              source_integrity_status: "REFUSED",
              verified_citation_count: 0,
              covered_source_count: 0,
              key_takeaways_zh: [],
              action_items_zh: [],
              citations: [],
              obsidian_markdown: "",
              updated_at: "2026-11-27T07:00:00Z",
            },
          ],
          suggested_questions: [],
          scope_options: {
            starred_count: 0,
            channels: [],
            topic_clusters: [],
            videos: [],
          },
        });
      }
      return okJson({});
    });

    render(
      <UiLanguageProvider>
        <WorkspaceAiResearchPanel onOpen={vi.fn()} />
      </UiLanguageProvider>,
    );

    const saveBtn = await screen.findByRole("button", { name: "摘录进来源批注" });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText(/已将研究结论摘录进《Deterministic State Machines》个人批注/)).toBeTruthy();
    });
    expect(screen.getByRole("button", { name: "已摘录进来源批注 ✓" })).toBeTruthy();

    const savedNote = readPersonalNote("vid-state-machine");
    expect(savedNote?.text).toContain("【跨视频研究结论】为什么必须使用显式状态机？");
    expect(savedNote?.text).toContain("确定性状态机能消除盲循环幻觉并保证单步可审计 [E1]。");
    expect(askPosts).toHaveLength(0);

    const pinnedBtn = screen.getByRole("button", { name: /仅看置顶 \(1\)/ });
    expect(screen.getByText(/未收录材料里提了什么未公开数据？/)).toBeTruthy();
    fireEvent.click(pinnedBtn);
    expect(pinnedBtn.getAttribute("aria-pressed")).toBe("true");
    expect(screen.queryByText(/未收录材料里提了什么未公开数据？/)).toBeNull();

    // Unfilter, switch to refused session, verify save-to-source-note button is hidden
    fireEvent.click(pinnedBtn);
    fireEvent.click(screen.getByRole("button", { name: /未收录材料里提了什么未公开数据？/ }));
    expect(screen.queryByRole("button", { name: /摘录进来源批注/ })).toBeNull();
  });
});
