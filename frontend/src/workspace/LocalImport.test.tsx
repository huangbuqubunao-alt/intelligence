import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { LocalImport } from "./LocalImport";
import { UiLanguageProvider } from "./uiLanguage";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
it("requires explicit confirmation and submits only selected File bytes", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ import: { content_id: "local-id", filename: "notes.md", status: "READY", duplicate: false } }) });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><LocalImport onClose={() => {}} onSaved={() => {}} onYouTube={() => {}} /></UiLanguageProvider>);
  const file = new File(["# Original notes\n"], "notes.md", { type: "text/markdown" });
  await userEvent.upload(screen.getByLabelText("Choose local files"), file);
  expect(fetch).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  await screen.findByText("Ready");
  expect(fetch.mock.calls[0][0]).toBe("/api/v1/local/imports?filename=notes.md");
  expect(fetch.mock.calls[0][1].body).toBe(file);
  expect(fetch.mock.calls[0][1].headers["Content-Type"]).toBe("application/octet-stream");
});
it("localizes invalid file feedback without attempting import", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><LocalImport onClose={() => {}} onSaved={() => {}} onYouTube={() => {}} /></UiLanguageProvider>);
  const input = screen.getByLabelText("选择本地文件");
  await userEvent.upload(input, new File(["PDF"], "paper.pdf"), { applyAccept: false });
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("不支持"));
  expect(fetch).not.toHaveBeenCalled();
});
it("imports multiple selections sequentially, keeps per-file errors and recognizes duplicates", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const fetch = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ import: { content_id: "first", filename: "first.txt", status: "READY", duplicate: false } }) })
    .mockResolvedValueOnce({ ok: false, json: async () => ({ error: { code: "LOCAL_INVALID_TEXT", message: "invalid" } }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ import: { content_id: "first", filename: "first.txt", status: "READY", duplicate: true } }) });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><LocalImport onClose={() => {}} onSaved={() => {}} onYouTube={() => {}} /></UiLanguageProvider>);
  const files = [new File(["first"], "first.txt"), new File(["bad"], "bad.txt"), new File(["first"], "copy.txt")];
  await userEvent.upload(screen.getByLabelText("Choose local files"), files);
  expect(fetch).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  await screen.findByText(/Already imported/);
  expect(fetch.mock.calls.map(call => call[1].body)).toEqual(files);
  expect(screen.getByRole("alert").textContent).toContain("valid UTF-8");
  expect(screen.getAllByRole("link", { name: "Open Content" })).toHaveLength(2);
  expect(screen.queryByRole("button", { name: "Confirm import" })).toBeNull();
});
