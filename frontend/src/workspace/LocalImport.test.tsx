import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
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

it("guards synchronous double confirmation and preserves pending upload across parent rerenders", async () => {
  localStorage.setItem("yia.ui-language", "en");
  let resolve!: (value: unknown) => void;
  const fetch = vi.fn(() => new Promise(value => { resolve = value; }));
  vi.stubGlobal("fetch", fetch);
  const onImported = vi.fn();
  const props = { onClose: vi.fn(), onSaved: vi.fn(), onYouTube: vi.fn(), onImported };
  const view = render(<UiLanguageProvider><LocalImport {...props} /></UiLanguageProvider>);
  const file = new File(["synthetic"], "video.mp4");
  await userEvent.upload(screen.getByLabelText("Choose local files"), file);
  const confirm = screen.getByRole("button", { name: "Confirm import" });
  // Dispatch twice before React flushes state; the ref protects this boundary.
  act(() => {
    confirm.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    confirm.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
  view.rerender(<UiLanguageProvider><LocalImport {...props} onClose={vi.fn()} /></UiLanguageProvider>);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("status").textContent).toContain("Importing selected files");
  expect(screen.getByRole("button", { name: "Cancel" }).hasAttribute("disabled")).toBe(true);
  resolve({ ok: true, json: async () => ({ import: { content_id: "saved-video", filename: file.name, status: "TRANSCRIPTION_UNAVAILABLE", duplicate: false } }) });
  await waitFor(() => expect(onImported.mock.calls).toEqual([["saved-video"]]));
  expect(screen.getByText("Local transcription is unavailable")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Confirm import" })).toBeNull();
});

it("keeps mixed outcomes visible and retries only failed files without resubmitting saved Content", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const onImported = vi.fn();
  const fetch = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ import: { content_id: "saved", filename: "good.txt", status: "READY", duplicate: false } }) })
    .mockResolvedValueOnce({ ok: false, json: async () => ({ error: { code: "LOCAL_IMPORT_BUSY" } }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ import: { content_id: "retried", filename: "retry.txt", status: "READY", duplicate: false } }) });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><LocalImport onClose={vi.fn()} onSaved={vi.fn()} onYouTube={vi.fn()} onImported={onImported} /></UiLanguageProvider>);
  const good = new File(["good"], "good.txt"), failed = new File(["retry"], "retry.txt");
  await userEvent.upload(screen.getByLabelText("Choose local files"), [good, failed]);
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  await screen.findByRole("button", { name: "Retry failed files" });
  expect(onImported).not.toHaveBeenCalled();
  expect(screen.getByRole("alert").textContent).toContain("Another local import");
  await userEvent.click(screen.getByRole("button", { name: "Retry failed files" }));
  await waitFor(() => expect(onImported.mock.calls).toEqual([["saved"]]));
  expect(fetch.mock.calls.map(call => call[1].body)).toEqual([good, failed, failed]);
});

it.each(["en", "zh-CN"])("retains an import error and selected bytes for explicit retry (%s)", async language => {
  localStorage.setItem("yia.ui-language", language);
  const t = (en: string, zh: string) => language === "en" ? en : zh;
  const fetch = vi.fn().mockResolvedValue({ ok: false, json: async () => ({ error: { code: "LOCAL_INVALID_MEDIA", message: "technical backend prose" } }) });
  vi.stubGlobal("fetch", fetch);
  const onImported = vi.fn();
  render(<UiLanguageProvider><LocalImport onClose={vi.fn()} onSaved={vi.fn()} onYouTube={vi.fn()} onImported={onImported} /></UiLanguageProvider>);
  await userEvent.upload(screen.getByLabelText(t("Choose local files", "选择本地文件")), new File(["bad"], "bad.mp4"));
  await userEvent.click(screen.getByRole("button", { name: t("Confirm import", "确认导入") }));
  const alert = await screen.findByRole("alert");
  expect(alert.textContent).toContain(t("malformed", "损坏"));
  expect(alert.textContent).not.toContain("technical backend prose");
  expect(onImported).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: t("Retry failed files", "重试失败的文件") })).toBeTruthy();
});

it.each(["PENDING", "RUNNING", "TRANSCRIPTION_FAILED", "READY"])("keeps file admission distinct from persisted processing state %s", async status => {
  localStorage.setItem("yia.ui-language", "en");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ import: { content_id: "persisted", filename: "video.mp4", status, duplicate: false } }) }));
  const onImported = vi.fn();
  render(<UiLanguageProvider><LocalImport onClose={vi.fn()} onSaved={vi.fn()} onYouTube={vi.fn()} onImported={onImported} /></UiLanguageProvider>);
  await userEvent.upload(screen.getByLabelText("Choose local files"), new File(["synthetic"], "video.mp4"));
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  await waitFor(() => expect(onImported.mock.calls).toEqual([["persisted"]]));
  expect(screen.getByText(({ PENDING: "Awaiting transcription", RUNNING: "Transcribing…", TRANSCRIPTION_FAILED: "Local transcription failed", READY: "Ready" })[status]!)).toBeTruthy();
});

it("does not expose navigation before a sequential batch settles", async () => {
  localStorage.setItem("yia.ui-language", "en");
  let resolve!: (value: unknown) => void;
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ import: { content_id: "saved", filename: "one.txt", status: "READY", duplicate: false } }) })
    .mockImplementationOnce(() => new Promise(value => { resolve = value; })));
  render(<UiLanguageProvider><LocalImport onClose={vi.fn()} onSaved={vi.fn()} onYouTube={vi.fn()} /></UiLanguageProvider>);
  await userEvent.upload(screen.getByLabelText("Choose local files"), [new File(["one"], "one.txt"), new File(["two"], "two.txt")]);
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  await screen.findByText("Ready");
  expect(screen.queryByRole("link", { name: "Open Content" })).toBeNull();
  resolve({ ok: true, json: async () => ({ import: { content_id: "saved-two", filename: "two.txt", status: "READY", duplicate: false } }) });
  await waitFor(() => expect(screen.getAllByRole("link", { name: "Open Content" })).toHaveLength(2));
});

it("keeps rejected selections visible when the valid part of a batch is saved", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const onImported = vi.fn();
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ import: { content_id: "saved", filename: "one.txt", status: "READY", duplicate: false } }) });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><LocalImport onClose={vi.fn()} onSaved={vi.fn()} onYouTube={vi.fn()} onImported={onImported} /></UiLanguageProvider>);
  await userEvent.upload(screen.getByLabelText("Choose local files"), [new File(["one"], "one.txt"), new File(["invalid"], "bad.pdf")], { applyAccept: false });
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  await screen.findByText("Ready");
  expect(screen.getByRole("alert").textContent).toContain("bad.pdf");
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(onImported).not.toHaveBeenCalled();
  expect(screen.getByRole("link", { name: "Open Content" })).toBeTruthy();
});
