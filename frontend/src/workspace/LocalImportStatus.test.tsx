import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { LocalImport, localStatus } from "./LocalImport";
import { UiLanguageProvider } from "./uiLanguage";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

/**
 * A stored snapshot that no longer verifies has to say so in the user's own
 * language.  Before this was resolved, the code fell through to the raw enum,
 * so the Chinese interface displayed backend vocabulary.
 */
const UNTRUSTED = "LOCAL_SOURCE_UNTRUSTED";
const zh = "已导入的快照未通过验证，现有证据暂不可用。";
const en = "The imported snapshot failed verification. Existing Evidence is unavailable.";

it("resolves an untrusted Local source to explicit copy in both languages", () => {
  expect(localStatus(UNTRUSTED)).toBe(en);
  expect(localStatus("SOURCE_UNTRUSTED")).toBe(en);
  // The resolved label must be a sentence the interface can localize, not a code.
  expect(localStatus(UNTRUSTED)).not.toMatch(/_/);
});

it("never falls back to a raw backend code, whatever the state", () => {
  for (const code of ["UNRECOGNISED_FUTURE_STATE", "CAPTION_UNAVAILABLE", "", "local_source_untrusted"]) {
    expect(localStatus(code)).not.toContain("_");
    expect(localStatus(code).length).toBeGreaterThan(0);
  }
});

it("keeps historical snapshot unavailability separate from current model capability", () => {
  expect(localStatus("TRANSCRIPTION_UNAVAILABLE")).toBe("File saved");
  expect(localStatus("RUNNING")).toBe("Transcribing…");
  expect(localStatus("TRANSCRIPTION_FAILED")).toBe("Local transcription failed");
  expect(localStatus("READY")).toBe("Ready");
});

const renderLocalLibraryRow = async (status: string, language: string) => {
  localStorage.setItem("yia.ui-language", language);
  const fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ import: { content_id: "local-id", filename: "notes.md", status, duplicate: false } }),
  });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><LocalImport onClose={() => {}} onSaved={() => {}} onYouTube={() => {}} /></UiLanguageProvider>);
  await userEvent.upload(screen.getByLabelText(language === "en" ? "Choose local files" : "选择本地文件"), new File(["# notes\n"], "notes.md", { type: "text/markdown" }));
  await userEvent.click(screen.getByRole("button", { name: language === "en" ? "Confirm import" : "确认导入" }));
};

it("shows an untrusted Local source in Chinese without backend vocabulary", async () => {
  await renderLocalLibraryRow(UNTRUSTED, "zh-CN");
  await waitFor(() => expect(screen.getByText(zh)).toBeTruthy());
  const shown = document.body.textContent ?? "";
  expect(shown).toContain(zh);
  expect(shown).not.toContain(UNTRUSTED);
  expect(shown).not.toContain("LOCAL_SOURCE");
});

it("shows an untrusted Local source in English without backend vocabulary", async () => {
  await renderLocalLibraryRow(UNTRUSTED, "en");
  await waitFor(() => expect(screen.getByText(en)).toBeTruthy());
  const shown = document.body.textContent ?? "";
  expect(shown).not.toContain(UNTRUSTED);
  expect(shown).not.toContain("LOCAL_SOURCE");
});

it.each(["en", "zh-CN"])("uses the saved snapshot label and current Content guidance in %s", async language => {
  await renderLocalLibraryRow("TRANSCRIPTION_UNAVAILABLE", language);
  await screen.findByText(language === "en" ? "File saved" : "文件已保存");
  expect(screen.getByText(language === "en" ? "File saved. Open Content to check the current transcription status." : "文件已保存。请打开内容查看当前转写状态。")).toBeTruthy();
  expect(screen.queryByText(language === "en" ? "Local transcription is unavailable" : "本地转写暂不可用")).toBeNull();
  expect(screen.getByRole("link", { name: language === "en" ? "Open Content" : "打开内容" }).getAttribute("href")).toBe("#Content/local-id");
});
