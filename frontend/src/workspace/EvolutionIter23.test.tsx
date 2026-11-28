import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceAiSettingsPanel } from "./WorkspaceAiWidgets";
import { exportPersonalNotesMarkdown, importPersonalNotesJson, savePersonalNote } from "./personalNotes";
import { UiLanguageProvider } from "./uiLanguage";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 23 — Obsidian Markdown personal notes digest export", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("formats Obsidian wikilinks, sanitizes title brackets, orders newest first, and handles 0 notes safely", () => {
    const empty = exportPersonalNotesMarkdown({}, true);
    expect(empty.noteCount).toBe(0);
    expect(empty.markdown).toContain("# 个人研究笔记与标签汇编");
    expect(empty.markdown).toContain("暂无本地个人笔记");

    importPersonalNotesJson(
      JSON.stringify({
        version: 1,
        notes: {
          vidOlder: {
            text: "First study takeaway",
            tags: ["旧标签"],
            updatedAt: "2026-11-26T08:00:00Z",
          },
          vidNewer: {
            text: "Latest architecture reflection\n\n> [01:20] Deterministic checkpointing",
            tags: ["核心结论", "Agent"],
            updatedAt: "2026-11-27T10:00:00Z",
          },
        },
      }),
    );

    const result = exportPersonalNotesMarkdown(
      {
        vidNewer: "State [Machines] | Guide",
        vidOlder: "Legacy Summary",
      },
      true,
    );
    expect(result.noteCount).toBe(2);
    expect(result.markdown).toContain("## 标签索引");
    expect(result.markdown).toContain("#核心结论 (1)");
    expect(result.markdown).toContain("## [[State Machines Guide]]");
    expect(result.markdown.indexOf("## [[State Machines Guide]]")).toBeLessThan(
      result.markdown.indexOf("## [[Legacy Summary]]"),
    );
  });

  it("downloads resolved Obsidian Markdown personal notes digest from Settings backup bar", async () => {
    savePersonalNote("vidMd1", {
      text: "Verified quote note body",
      tags: ["高价值"],
    });

    let exportedBlob: Blob | null = null;
    const createObjectUrlMock = vi.fn((blob: Blob) => {
      exportedBlob = blob;
      return "blob:mock-personal-md";
    });
    const revokeObjectUrlMock = vi.fn();
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: createObjectUrlMock,
      revokeObjectURL: revokeObjectUrlMock,
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path.startsWith("/api/v1/videos")) {
          return jsonResponse({
            videos: [{ video_id: "vidMd1", title: "Local-First Knowledge Vaults" }],
          });
        }
        return jsonResponse({});
      }),
    );
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel />
      </UiLanguageProvider>,
    );

    await user.click(screen.getByRole("button", { name: "导出笔记汇编 (.md)" }));

    await waitFor(() => {
      expect(screen.getByText("已导出 Obsidian 个人笔记汇编 (.md，共 1 条)。")).toBeTruthy();
    });
    expect(createObjectUrlMock).toHaveBeenCalledTimes(1);
    expect(exportedBlob).not.toBeNull();
    const mdText = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ""));
      reader.onerror = () => reject(reader.error ?? new Error("FileReader failed"));
      reader.readAsText(exportedBlob!);
    });
    expect(mdText).toContain("## [[Local-First Knowledge Vaults]]");
    expect(mdText).toContain("#高价值");
    expect(mdText).toContain("Verified quote note body");
    clickSpy.mockRestore();
  });
});
