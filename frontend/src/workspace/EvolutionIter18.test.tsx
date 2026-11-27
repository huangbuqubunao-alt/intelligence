import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceAiResearchPanel, AiResearchSession } from "./WorkspaceAiWidgets";
import { buildResearchSynthesisMarkdown, deriveResearchNoteFilename } from "./researchExport";
import { UiLanguageProvider } from "./uiLanguage";

const { apiMock, uploadLocalMock } = vi.hoisted(() => ({
  apiMock: vi.fn(),
  uploadLocalMock: vi.fn(),
}));

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return {
    ...actual,
    api: apiMock,
    uploadLocal: uploadLocalMock,
  };
});

const groundedSession: AiResearchSession = {
  session_id: "sessGrounded1",
  question: "Agent 状态机 vs 对话循环的核心分歧",
  answer_status: "GROUNDED",
  source_integrity_status: "VERIFIED",
  refused: false,
  scope_label_zh: "全部高信号长视频",
  pinned: false,
  answer_zh: "确定性状态机将副作用与推理彻底隔离 [E1]。",
  key_takeaways_zh: ["工具调用必须有界校验 [E1]"],
  action_items_zh: ["引入 SQLite 检查点"],
  citations: [
    {
      ref_label: "E1",
      video_id: "vid1",
      video_title: "Deterministic Agents",
      channel_name: "Atlas",
      evidence_id: "ev1",
      start_ms: 12000,
      end_ms: 32000,
      timestamp_label: "00:12",
      excerpt: "Production agents fail when side effects run inside unstructured loops.",
    },
  ],
  obsidian_markdown: "",
  provider: "ollama",
  model: "qwen3.5:9b",
  created_at: "2026-11-27T10:00:00Z",
};

const refusedSession: AiResearchSession = {
  ...groundedSession,
  session_id: "sessRefused2",
  question: "无根据问题",
  answer_status: "REFUSED_INSUFFICIENT_EVIDENCE",
  source_integrity_status: "REFUSED",
  refused: true,
  citations: [],
  answer_zh: "未找到支持回答该问题的原文证据。",
};

describe("Iteration 18 — Promote Grounded Research Synthesis to Local Library", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
  });

  it("refuses Markdown generation on refused or zero-citation sessions and builds fallback synthesis for grounded ones", () => {
    expect(buildResearchSynthesisMarkdown(refusedSession, true)).toBe("");
    const md = buildResearchSynthesisMarkdown(groundedSession, true);
    expect(md).toContain("# Agent 状态机 vs 对话循环的核心分歧");
    expect(md).toContain("确定性状态机将副作用与推理彻底隔离 [E1]");
    expect(md).toContain("[E1] Deterministic Agents (00:12)");
    expect(deriveResearchNoteFilename("Agent 状态机", "sessGrounded1")).toBe("research-Agent-状态机-rounded1.md");
  });

  it("hides promote button on refused sessions, uploads Markdown for grounded sessions, and opens the newly saved note", async () => {
    const user = userEvent.setup();
    const onOpenMock = vi.fn();

    apiMock.mockImplementation(async (path: string) => {
      if (path === "/workspace-ai/research/sessions") {
        return { sessions: [groundedSession, refusedSession] };
      }
      return {};
    });
    uploadLocalMock.mockResolvedValue({ import: { content_id: "docResearchSaved1" } });

    render(
      <UiLanguageProvider>
        <WorkspaceAiResearchPanel onOpen={onOpenMock} />
      </UiLanguageProvider>,
    );

    const saveBtn = await screen.findByRole("button", { name: /沉淀为本地研究笔记|Save as local note/i });
    await user.click(saveBtn);

    await waitFor(() => {
      expect(uploadLocalMock).toHaveBeenCalledTimes(1);
    });
    expect(String(uploadLocalMock.mock.calls[0]?.[0])).toContain("/local/imports?filename=research-");

    const openSavedBtn = await screen.findByRole("button", { name: /已沉淀入内容库 · 打开阅读|Saved to library · Open note/i });
    await user.click(openSavedBtn);
    expect(onOpenMock).toHaveBeenCalledWith("content", "docResearchSaved1");

    // Switching to refused session must hide promotion button
    await user.click(screen.getByRole("button", { name: /无根据问题/ }));
    expect(screen.queryByRole("button", { name: /沉淀为本地研究笔记|Save as local note/i })).toBeNull();
  });
});
