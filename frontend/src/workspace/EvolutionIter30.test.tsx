import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { KnowledgeDelta, type KnowledgeDeltaProjection } from "./KnowledgeDelta";
import { importPersonalNotesJson } from "./personalNotes";
import { buildWeeklyReviewMarkdown } from "./weeklyReviewExport";
import { UiLanguageProvider } from "./uiLanguage";

function sampleDelta(): KnowledgeDeltaProjection {
  return {
    window_start: "2026-11-20T00:00:00.000Z",
    window_end: "2026-11-27T23:59:59.000Z",
    timezone: "Asia/Shanghai",
    status: "available",
    detail_limit: 2,
    categories: [
      {
        kind: "content_completed",
        status: "available",
        count: 2,
        items: [
          {
            id: "c1",
            kind: "content_completed",
            label: "Completed content",
            title: "Deterministic [State] | Machines",
            target: { kind: "content", id: "vid1" },
            occurred_at: "2026-11-26T10:00:00.000Z",
            facts: {},
          },
        ],
      },
      {
        kind: "intelligence_revised",
        status: "available",
        count: 1,
        items: [
          {
            id: "i1",
            kind: "intelligence_revised",
            label: "Intelligence revised",
            title: "Local-First Retrieval Audit",
            target: { kind: "intelligence", id: "int1" },
            occurred_at: "2026-11-27T04:00:00.000Z",
            facts: {
              revision_count: 2,
              evidence_before: 2,
              evidence_after: 3,
              evidence_set_changed: true,
            },
          },
        ],
      },
    ],
  };
}

describe("Iteration 30 — Home 7-day Weekly Knowledge Review Markdown export", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("formats sanitized wikilinks, category deltas, checklist, and includes only notes updated inside the 7-day window", () => {
    importPersonalNotesJson(
      JSON.stringify({
        version: 1,
        notes: {
          vidInWindow: {
            text: "Key state-machine insight\nFollow up with failure tests",
            tags: ["核心结论", "状态机"],
            updatedAt: "2026-11-27T08:00:00.000Z",
          },
          vidOutOfWindow: {
            text: "Old note from last month",
            tags: ["历史"],
            updatedAt: "2026-10-15T08:00:00.000Z",
          },
        },
      }),
    );

    const out = buildWeeklyReviewMarkdown(sampleDelta(), {
      zh: true,
      personalNotes: JSON.parse(localStorage.getItem("yia.personal-notes.v1") ?? "{}"),
      titleByVideoId: { vidInWindow: "Deterministic [Agent] Workflow" },
    });

    expect(out.filename).toBe("weekly-knowledge-review-2026-11-27.md");
    expect(out.changedItemCount).toBe(2);
    expect(out.recentNoteCount).toBe(1);
    expect(out.markdown).toContain("# 每周知识复盘周报");
    expect(out.markdown).toContain("[[Deterministic State Machines]]");
    expect(out.markdown).toContain("[[Deterministic Agent Workflow]]");
    expect(out.markdown).toContain("#核心结论 #状态机");
    expect(out.markdown).toContain("> Key state-machine insight");
    expect(out.markdown).not.toContain("Old note from last month");
    expect(out.markdown).toContain("## 下周行动与待核查");
    expect(out.markdown).toContain("- [ ] ");
  });

  it("downloads structured weekly review .md when clicking 导出周报 (.md) in KnowledgeDelta", async () => {
    importPersonalNotesJson(
      JSON.stringify({
        version: 1,
        notes: {
          vidWeekly1: {
            text: "Verified weekly takeaway",
            tags: ["复盘"],
            updatedAt: "2026-11-26T09:00:00.000Z",
          },
        },
      }),
    );

    let exportedBlob: Blob | null = null;
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn((blob: Blob) => {
        exportedBlob = blob;
        return "blob:weekly-review";
      }),
      revokeObjectURL: vi.fn(),
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ knowledge_delta: sampleDelta() }),
      })),
    );
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <KnowledgeDelta refresh={0} onOpen={vi.fn()} />
      </UiLanguageProvider>,
    );

    const exportBtn = await screen.findByRole("button", { name: "导出周报 (.md)" });
    await user.click(exportBtn);

    await waitFor(() => {
      expect(
        screen.getByText("已导出本周复盘周报 (.md · 2 条动态 · 1 篇批注)。"),
      ).toBeTruthy();
    });
    expect(exportedBlob).not.toBeNull();
    const mdText = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ""));
      reader.onerror = () => reject(reader.error ?? new Error("FileReader error"));
      reader.readAsText(exportedBlob!);
    });
    expect(mdText).toContain("# 每周知识复盘周报");
    expect(mdText).toContain("Verified weekly takeaway");
    expect(mdText).toContain("[[Deterministic State Machines]]");
    clickSpy.mockRestore();
  });
});
