import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReaderPersonalNoteCard } from "./ReaderPersonalNoteCard";
import { readPersonalNote, savePersonalNote } from "./personalNotes";
import { UiLanguageProvider } from "./uiLanguage";

describe("Iteration 44 — Reader note copy, inline task toggle strip & live stats", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("copies formatted tags + note body, toggles Markdown action checkboxes in 1 click, and updates live stats", async () => {
    savePersonalNote("vidReader44", {
      text: "### 实践行动项\n- [ ] 验证沙箱边界\n- [x] 完成首轮基线测试",
      tags: ["架构", "Agent"],
    });

    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(
      <UiLanguageProvider>
        <ReaderPersonalNoteCard videoId="vidReader44" />
      </UiLanguageProvider>,
    );

    expect(screen.getByText(/行动项 1\/2 已完成/)).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "复制笔记" }));
    expect(writeText).toHaveBeenCalledTimes(1);
    const copiedPayload = writeText.mock.calls[0]?.[0] as string;
    expect(copiedPayload).toContain("#架构 #Agent");
    expect(copiedPayload).toContain("- [ ] 验证沙箱边界");
    expect(screen.getByRole("button", { name: "已复制 ✓" })).toBeTruthy();

    const taskCheckbox = screen.getByRole("checkbox", { name: "验证沙箱边界" });
    await user.click(taskCheckbox);

    const textarea = screen.getByLabelText("我的思考与批注内容") as HTMLTextAreaElement;
    expect(textarea.value).toContain("- [x] 验证沙箱边界");
    expect(readPersonalNote("vidReader44")?.text).toContain("- [x] 验证沙箱边界");
    expect(screen.getByText(/行动项 2\/2 已完成/)).toBeTruthy();
  });
});
