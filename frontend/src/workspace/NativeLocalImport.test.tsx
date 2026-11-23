import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { LocalImport } from "./LocalImport";
import { NativeImportActivity, NativeJob } from "./NativeLocalImport";
import { UiLanguageProvider } from "./uiLanguage";

const file = { filename: "native-two-gib.mp4", byte_count: 2 * 1024 ** 3, phase: "SELECTED", loaded: 0, snapshot_method: "PENDING", error_code: null, processing_error_code: null, import: null };
let job: NativeJob;
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function view(available = true) {
  localStorage.setItem("yia.ui-language", "en");
  vi.stubGlobal("navigator", { platform: "MacIntel" });
  job = { job_id: "grant", state: "SELECTED", files: [{ ...file }], error_code: null };
  const fetch = vi.fn(async (path: string, options?: RequestInit) => {
    if (path.endsWith("capability")) return { ok: true, json: async () => ({ capability: { available } }) };
    if (path.endsWith("confirm")) job = { ...job, state: "IMPORTING", files: [{ ...file, phase: "VERIFYING", snapshot_method: "APFS_CLONE" }] };
    if (path.endsWith("cancel")) job = { ...job, state: "CANCELLED" };
    return { ok: true, json: async () => path.endsWith("jobs") ? { jobs: [job] } : { job } };
  });
  vi.stubGlobal("fetch", fetch);
  const onImported = vi.fn(), onClose = vi.fn();
  render(<UiLanguageProvider><LocalImport onClose={onClose} onSaved={vi.fn()} onYouTube={vi.fn()} onImported={onImported} /></UiLanguageProvider>);
  return { fetch, onImported, onClose };
}
async function choose() {
  await waitFor(() => expect(screen.getByRole("button", { name: "Choose local files" }).hasAttribute("disabled")).toBe(false));
  await userEvent.click(screen.getByRole("button", { name: "Choose local files" }));
}

it("uses only native JSON controls, keeps selection on focus and navigates to saved Content", async () => {
  const { fetch, onImported } = view();
  await choose();
  expect(document.querySelector('input[type="file"]')).toBeNull();
  act(() => window.dispatchEvent(new Event("focus")));
  expect(screen.getByText(file.filename)).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  expect(screen.getByText("Verifying imported file…")).toBeTruthy();
  expect(screen.queryByRole("progressbar")).toBeNull();
  expect(onImported).not.toHaveBeenCalled();
  job = { ...job, state: "COMPLETE", files: [{ ...file, phase: "SAVED", snapshot_method: "APFS_CLONE", import: { content_id: "native-content", filename: file.filename, status: "TRANSCRIPTION_UNAVAILABLE", duplicate: false } }] };
  await waitFor(() => expect(onImported).toHaveBeenCalledWith("native-content"), { timeout: 2000 });
  expect(screen.getByText("File saved. Local transcription status appears in Content.")).toBeTruthy();
  for (const [path, options] of fetch.mock.calls.filter(([path]) => !path.endsWith("capability"))) {
    expect(path).toContain("/local/native/");
    expect(options?.body).toBe("{}");
  }
});

it("continues in the background without cancelling the import", async () => {
  const { fetch, onClose } = view();
  await choose();
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  await userEvent.click(screen.getByRole("button", { name: "Continue in background" }));
  expect(onClose).toHaveBeenCalledOnce();
  expect(fetch.mock.calls.some(([path]) => path.endsWith("cancel"))).toBe(false);
});

it("revokes the selected grant when closed before confirmation", async () => {
  const { fetch, onClose } = view();
  await choose();
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(fetch.mock.calls.some(([path]) => path.endsWith("cancel"))).toBe(true);
  expect(onClose).toHaveBeenCalledOnce();
});

it("clearly rejects unavailable native selection", async () => {
  const { fetch } = view(false);
  expect((await screen.findByRole("alert")).textContent).toContain("current launcher");
  expect(screen.getByRole("button", { name: "Choose local files" }).hasAttribute("disabled")).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(document.querySelector('input[type="file"]')).toBeNull();
});

it("shows actual fallback bytes and reports duration errors independently", async () => {
  view();
  await choose();
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  job = { ...job, files: [{ ...file, phase: "COPYING", loaded: 1024 ** 3, snapshot_method: "STREAM_COPY" }] };
  await screen.findByRole("progressbar");
  expect(screen.getByText("50%")).toBeTruthy();
  expect(screen.getByRole("progressbar").getAttribute("max")).toBe(String(file.byte_count));
  job = { ...job, state: "COMPLETE", files: [{ ...file, phase: "FAILED", error_code: "LOCAL_MEDIA_TOO_LONG" }] };
  expect((await screen.findByRole("alert")).textContent).toContain("four-hour duration limit");
  expect(screen.queryByRole("progressbar")).toBeNull();
});

it("shows and opens committed work outside the modal", async () => {
  const { onImported } = view();
  cleanup();
  job = { ...job, state: "IMPORTING", files: [{ ...file, phase: "SAVED", import: { content_id: "background-content", filename: file.filename, status: "TRANSCRIPTION_UNAVAILABLE", duplicate: false } }] };
  render(<UiLanguageProvider><NativeImportActivity onOpen={onImported} /></UiLanguageProvider>);
  await userEvent.click(await screen.findByRole("button", { name: `Open Content: ${file.filename}` }));
  expect(onImported).toHaveBeenCalledWith("background-content");
});

it("reports an independent duration error after the modal closes", async () => {
  view();
  cleanup();
  job = { ...job, state: "IMPORTING", files: [{ ...file, phase: "VERIFYING" }] };
  render(<UiLanguageProvider><NativeImportActivity onOpen={vi.fn()} errors={{ LOCAL_MEDIA_TOO_LONG: "This media exceeds the four-hour duration limit. Choose a shorter recording." }} /></UiLanguageProvider>);
  await screen.findByText("Verifying imported file…");
  job = { ...job, state: "COMPLETE", files: [{ ...file, phase: "FAILED", error_code: "LOCAL_MEDIA_TOO_LONG" }] };
  act(() => window.dispatchEvent(new Event("native-imports-changed")));
  expect((await screen.findByRole("alert")).textContent).toContain("four-hour duration limit");
});

it("offers browser upload fallback on macOS when native capability is unavailable and closes on Escape", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  vi.stubGlobal("navigator", { platform: "MacIntel" });
  const fetchMock = vi.fn(async (path: string) => {
    if (path.endsWith("capability")) return { ok: true, json: async () => ({ capability: { available: false } }) };
    return { ok: true, json: async () => ({}) };
  });
  vi.stubGlobal("fetch", fetchMock);
  const onClose = vi.fn();
  render(<UiLanguageProvider><LocalImport onClose={onClose} onSaved={vi.fn()} onYouTube={vi.fn()} /></UiLanguageProvider>);
  expect((await screen.findByRole("alert")).textContent).toContain("原生文件选择不可用");
  expect(document.querySelector('input[type="file"]')).toBeNull();

  const fallbackBtn = screen.getByRole("button", { name: "使用浏览器本地上传（.md / .txt / 音视频）" });
  await userEvent.click(fallbackBtn);
  const fileInput = screen.getByLabelText("选择本地文件") as HTMLInputElement;
  expect(fileInput.type).toBe("file");

  await userEvent.keyboard("{Escape}");
  expect(onClose).toHaveBeenCalledOnce();
});
