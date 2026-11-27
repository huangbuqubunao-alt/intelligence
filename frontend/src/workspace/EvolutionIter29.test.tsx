import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceAiSettingsPanel } from "./WorkspaceAiWidgets";
import { listPersonalNoteVideoIds, listPersonalTagCounts, savePersonalNote } from "./personalNotes";
import { readReadingHistory, recordReadingVisit } from "./readingHistory";
import { readSavedContentViews, saveContentView } from "./savedViews";
import { UiLanguageProvider } from "./uiLanguage";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 29 — Settings local study data governance", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    vi.stubGlobal(
      "fetch",
      vi.fn(() => jsonResponse({})),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("displays accurate local study data counts and clears reading trail & saved views without deleting personal notes or tags", async () => {
    savePersonalNote("vidGov1", {
      text: "Architecture decision note",
      tags: ["核心结论", "Agent"],
    });
    savePersonalNote("vidGov2", {
      text: "Market positioning reflection",
      tags: ["核心结论"],
    });
    saveContentView(
      {
        name: "必看核心视图",
        searchQuery: "",
        providerFilter: "ALL",
        bucketFilter: "MUST_WATCH",
        topicFilter: "ALL",
        channelFilter: "ALL",
        tagFilter: "核心结论",
      },
      true,
    );
    recordReadingVisit({
      videoId: "vidGov1",
      title: "State Machines Architecture",
      estimatedMinutes: 4,
    });
    recordReadingVisit({
      videoId: "vidGov2",
      title: "Local-First Workflow",
      estimatedMinutes: 3,
    });

    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel />
      </UiLanguageProvider>,
    );

    expect(
      screen.getByText("本机学习数据：笔记 2 条 · 标签 2 个 · 常用视图 1 个 · 最近阅读 2 条"),
    ).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "清空最近阅读 (2)" }));

    await waitFor(() => {
      expect(
        screen.getByText("已清空本机最近阅读记录（个人笔记与标签已保留）。"),
      ).toBeTruthy();
      expect(
        screen.getByText("本机学习数据：笔记 2 条 · 标签 2 个 · 常用视图 1 个 · 最近阅读 0 条"),
      ).toBeTruthy();
    });
    expect(readReadingHistory()).toHaveLength(0);
    expect(readSavedContentViews()).toHaveLength(1);
    expect(listPersonalNoteVideoIds().size).toBe(2);
    expect(listPersonalTagCounts().length).toBe(2);

    await user.click(screen.getByRole("button", { name: "清空常用视图 (1)" }));

    await waitFor(() => {
      expect(
        screen.getByText("已清空本机常用筛选视图（个人笔记与标签已保留）。"),
      ).toBeTruthy();
      expect(
        screen.getByText("本机学习数据：笔记 2 条 · 标签 2 个 · 常用视图 0 个 · 最近阅读 0 条"),
      ).toBeTruthy();
    });
    expect(readSavedContentViews()).toHaveLength(0);
    expect(listPersonalNoteVideoIds().size).toBe(2);
    expect(listPersonalTagCounts().length).toBe(2);
  });

  it("hides session cleanup buttons cleanly when reading trail and saved views are both empty", () => {
    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel />
      </UiLanguageProvider>,
    );

    expect(
      screen.getByText("本机学习数据：笔记 0 条 · 标签 0 个 · 常用视图 0 个 · 最近阅读 0 条"),
    ).toBeTruthy();
    expect(screen.queryByRole("group", { name: "本机轻量记录清理" })).toBeNull();
  });
});
