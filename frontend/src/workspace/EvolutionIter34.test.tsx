import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QuickPasteNoteForm } from "./QuickPasteNoteForm";
import { ReaderPersonalNoteCard } from "./ReaderPersonalNoteCard";
import { UiLanguageProvider } from "./uiLanguage";

describe("Iteration 34 — Quick Paste templates, live reading metrics & Reader N note-focus shortcut", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("appends starter templates cleanly without overwriting text and shows live reading-time metrics in QuickPasteNoteForm", async () => {
    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <QuickPasteNoteForm
          onClose={vi.fn()}
          onSaved={vi.fn()}
          onYouTube={vi.fn()}
          onLocalFiles={vi.fn()}
        />
      </UiLanguageProvider>,
    );

    const textarea = screen.getByLabelText("粘贴正文内容") as HTMLTextAreaElement;
    await user.type(textarea, "Initial project context");

    await user.click(screen.getByRole("button", { name: "+ 会议纪要" }));

    expect(textarea.value).toContain("Initial project context");
    expect(textarea.value).toContain("## 参会背景与目标");
    expect(screen.getByText(/约 \d+ 分钟精读 · \d+ 字/)).toBeTruthy();
  });

  it("expands and focuses ReaderPersonalNoteCard textarea on single-key N, and ignores N while typing in an input", async () => {
    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <div>
          <input aria-label="other-input" />
          <ReaderPersonalNoteCard videoId="vidShortcut1" />
        </div>
      </UiLanguageProvider>,
    );

    expect(screen.queryByLabelText("我的思考与批注内容")).toBeNull();

    const otherInput = screen.getByLabelText("other-input");
    await user.click(otherInput);
    await user.keyboard("n");
    expect(screen.queryByLabelText("我的思考与批注内容")).toBeNull();

    (otherInput as HTMLInputElement).blur();
    await user.keyboard("n");

    const noteTextarea = (await screen.findByLabelText("我的思考与批注内容")) as HTMLTextAreaElement;
    await waitFor(() => {
      expect(document.activeElement).toBe(noteTextarea);
    });
    expect(noteTextarea.value).toBe("");
  });
});
