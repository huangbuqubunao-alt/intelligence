import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceAiResearchPanel, type AiResearchSession } from "./WorkspaceAiWidgets";
import { buildLensPrompt, buildResearchDossierMarkdown } from "./researchExport";
import { UiLanguageProvider } from "./uiLanguage";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

function makeSession(overrides: Partial<AiResearchSession>): AiResearchSession {
  return {
    session_id: "sess_1",
    question: "Agent evaluation strategies",
    scope_label_zh: "全库对比",
    answer_zh: "Deterministic eval harnesses reduce flakiness [E1].",
    obsidian_markdown: "",
    provider: "ollama",
    model: "qwen3.5:9b",
    refused: false,
    key_takeaways_zh: ["Always isolate tool side effects"],
    action_items_zh: ["Add golden replay tests"],
    citations: [
      {
        ref_label: "E1",
        video_id: "vid1",
        video_title: "Eval Engineering",
        channel_name: "Atlas Lab",
        evidence_id: "ev_1",
        start_ms: 252000,
        end_ms: 260000,
        locator_type: "TIMECODE",
        timestamp_label: "04:12",
        excerpt: "Replay fixtures guarantee repeatable runs.",
      },
    ],
    created_at: "2026-11-27T09:00:00Z",
    pinned: false,
    ...overrides,
  };
}

describe("Iteration 25 — Structured Research lenses & grounded multi-session dossier export", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("excludes refused and uncited sessions from dossier Markdown and promotes pinned sessions first", () => {
    const groundedOld = makeSession({
      session_id: "s_old",
      question: "Pinned Old Session",
      pinned: true,
      created_at: "2026-11-26T08:00:00Z",
    });
    const refused = makeSession({
      session_id: "s_refused",
      question: "Hallucination Trap",
      refused: true,
      citations: [],
    });
    const uncited = makeSession({
      session_id: "s_uncited",
      question: "Uncited Claim",
      refused: false,
      citations: [],
    });

    const res = buildResearchDossierMarkdown([uncited, refused, groundedOld], true);
    expect(res.includedCount).toBe(1);
    expect(res.skippedCount).toBe(2);
    expect(res.markdown).toContain("# 跨来源研究汇编");
    expect(res.markdown).toContain("## 1. [置顶] Pinned Old Session");
    expect(res.markdown).not.toContain("Hallucination Trap");
    expect(res.markdown).not.toContain("Uncited Claim");
    expect(buildLensPrompt("consensus_diff", "Agent 架构", true)).toContain("Agent 架构");
  });

  it("prefills structured lens prompts without firing /ask and downloads filtered grounded dossier", async () => {
    const grounded = makeSession({ session_id: "s_ok", question: "Grounded Architecture Q" });
    const refused = makeSession({
      session_id: "s_bad",
      question: "Secret Refused Question",
      refused: true,
      citations: [],
    });

    let exportedBlob: Blob | null = null;
    const createObjectUrlMock = vi.fn((blob: Blob) => {
      exportedBlob = blob;
      return "blob:mock-dossier";
    });
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: createObjectUrlMock,
      revokeObjectURL: vi.fn(),
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const fetchMock = vi.fn((path: string) => {
      if (path === "/api/v1/workspace-ai/research/sessions") {
        return jsonResponse({
          sessions: [grounded, refused],
          suggested_questions: [],
          scope_options: {
            channels: [],
            topic_clusters: [],
            videos: [{ video_id: "vid1", title: "Eval Engineering", starred: false }],
          },
        });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <WorkspaceAiResearchPanel onOpen={vi.fn()} />
      </UiLanguageProvider>,
    );

    const lensBtn = await screen.findByRole("button", { name: "视角 · 共识与分歧" });
    await user.click(lensBtn);

    const input = screen.getByLabelText("跨视频提问") as HTMLTextAreaElement;
    expect(input.value).toContain("共识");
    const askCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes("/research/ask"));
    expect(askCalls).toHaveLength(0);

    const exportBtn = screen.getByRole("button", { name: "导出研究汇编 (.md)" });
    await user.click(exportBtn);

    await waitFor(() => {
      expect(screen.getByText(/已导出研究汇编/)).toBeTruthy();
    });
    expect(createObjectUrlMock).toHaveBeenCalledTimes(1);
    const mdText = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ""));
      reader.onerror = () => reject(reader.error ?? new Error("FileReader failed"));
      reader.readAsText(exportedBlob!);
    });
    expect(mdText).toContain("Grounded Architecture Q");
    expect(mdText).not.toContain("Secret Refused Question");
    clickSpy.mockRestore();
  });
});
