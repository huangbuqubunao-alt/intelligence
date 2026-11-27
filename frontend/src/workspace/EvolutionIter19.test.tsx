import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CommandPalette } from "./ui/CommandPalette";
import { listPersonalTagCounts, savePersonalNote } from "./personalNotes";
import { UiLanguageProvider } from "./uiLanguage";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 19 — Cmd+K Personal Notes & #Tag Search", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    savePersonalNote("vidAgentDemo", {
      text: "工具边界与状态机持久检查点才是生产可用关键。",
      tags: ["核心结论", "架构实战"],
    });
    savePersonalNote("vidBiliDemo", {
      text: "时间轴溯源导出双链提升复盘效率。",
      tags: ["核心结论"],
    });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("aggregates case-insensitive personal tag counts accurately", () => {
    const counts = listPersonalTagCounts();
    expect(counts[0]?.tag).toBe("核心结论");
    expect(counts[0]?.count).toBe(2);
    expect(counts[1]?.tag).toBe("架构实战");
    expect(counts[1]?.count).toBe(1);
  });

  it("searches personal note body text and #tag filter commands inside CommandPalette", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/videos") {
          return jsonResponse({
            videos: [
              {
                video_id: "vidAgentDemo",
                title: "Production Agent State Machines",
                provider: "YOUTUBE",
                channel_name: "Atlas",
              },
            ],
          });
        }
        return jsonResponse({});
      }),
    );

    const onOpenContent = vi.fn();
    const onFilterByTag = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <UiLanguageProvider>
        <CommandPalette
          open
          onClose={onClose}
          staticActions={[]}
          onOpenContent={onOpenContent}
          onOpenIntelligence={vi.fn()}
          onOpenTopic={vi.fn()}
          onFilterContentByPersonalTag={onFilterByTag}
        />
      </UiLanguageProvider>,
    );

    const searchInput = await screen.findByRole("combobox");
    await user.type(searchInput, "检查点");

    const noteHit = await screen.findByText(/工具边界与状态机持久检查点/);
    expect(screen.getByText("个人笔记与标签")).toBeTruthy();
    await user.click(noteHit);
    expect(onOpenContent).toHaveBeenCalledWith("vidAgentDemo");

    // Verify tag filter command match
    const rerenderedOnClose = vi.fn();
    cleanup();
    render(
      <UiLanguageProvider>
        <CommandPalette
          open
          onClose={rerenderedOnClose}
          staticActions={[]}
          onOpenContent={vi.fn()}
          onOpenIntelligence={vi.fn()}
          onOpenTopic={vi.fn()}
          onFilterContentByPersonalTag={onFilterByTag}
        />
      </UiLanguageProvider>,
    );

    const searchInput2 = await screen.findByRole("combobox");
    await user.type(searchInput2, "#核心结论");

    const tagFilterCmd = await screen.findByText("按个人标签筛选：#核心结论");
    await waitFor(() => expect(tagFilterCmd).toBeTruthy());
    await user.click(tagFilterCmd);
    expect(onFilterByTag).toHaveBeenCalledWith("核心结论");
  });
});
