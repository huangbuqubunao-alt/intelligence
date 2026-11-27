import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ReaderPersonalNoteCard } from "./ReaderPersonalNoteCard";
import { readPersonalNote, savePersonalNote } from "./personalNotes";
import { UiLanguageProvider } from "./uiLanguage";

describe("Iteration 27 — Personal note reflection templates & canonical library tag suggestions", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  it("appends structured reflection template without overwriting existing notes and adds canonical tags in 1 click", async () => {
    savePersonalNote("vidOtherPeer", {
      text: "Other peer note",
      tags: ["核心结论", "工程方法"],
    });
    savePersonalNote("vidTarget", {
      text: "Initial observation on state machines",
      tags: ["核心结论"],
    });

    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <ReaderPersonalNoteCard videoId="vidTarget" />
      </UiLanguageProvider>,
    );

    const textarea = screen.getByLabelText("我的思考与批注内容") as HTMLTextAreaElement;
    expect(textarea.value).toBe("Initial observation on state machines");

    // Existing tag already on vidTarget ("核心结论") is omitted; only "工程方法" is suggested.
    expect(screen.queryByRole("button", { name: "+ #核心结论" })).toBeNull();
    const suggestedBtn = screen.getByRole("button", { name: "+ #工程方法" });

    await user.click(screen.getByRole("button", { name: "+ 3-2-1 复盘" }));
    expect(textarea.value).toContain("Initial observation on state machines");
    expect(textarea.value).toContain("### 3 个核心收获");
    expect(readPersonalNote("vidTarget")?.text).toContain("### 3 个核心收获");

    await user.click(suggestedBtn);
    const saved = readPersonalNote("vidTarget");
    expect(saved?.tags).toEqual(["核心结论", "工程方法"]);
    expect(screen.queryByRole("button", { name: "+ #工程方法" })).toBeNull();
  });
});
