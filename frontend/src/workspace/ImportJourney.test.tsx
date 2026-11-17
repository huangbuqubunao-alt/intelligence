import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { NativeImportActivity, NativeJob } from "./NativeLocalImport";
import { UiLanguageProvider } from "./uiLanguage";

const errors = {
  LOCAL_MEDIA_TOO_LONG: "This media exceeds the four-hour duration limit. Choose a shorter recording.",
};
const pendingFile = {
  filename: "short-video.mp4", byte_count: 1024, phase: "VERIFYING", loaded: 1024,
  snapshot_method: "APFS_CLONE", error_code: null, processing_error_code: null, import: null,
};

function importing(id: string): NativeJob {
  return { job_id: id, state: "IMPORTING", files: [{ ...pendingFile }], error_code: null };
}

function mixedComplete(id: string): NativeJob {
  return {
    job_id: id, state: "COMPLETE", error_code: null,
    files: [
      { ...pendingFile, filename: "too-long-video.mp4", phase: "FAILED", error_code: "LOCAL_MEDIA_TOO_LONG" },
      { ...pendingFile, phase: "SAVED", import: {
        content_id: `content-${id}`, filename: pendingFile.filename,
        status: "TRANSCRIPTION_UNAVAILABLE", duplicate: false,
      } },
    ],
  };
}

function nativeApi(initialJobs: NativeJob[]) {
  let jobs = initialJobs;
  let reads = 0;
  localStorage.setItem("yia.ui-language", "en");
  vi.stubGlobal("navigator", { platform: "MacIntel" });
  const fetch = vi.fn(async (path: string) => {
    if (path === "/api/v1/local/native/capability") {
      return new Response(JSON.stringify({ capability: { available: true } }));
    }
    if (path === "/api/v1/local/native/jobs") {
      reads += 1;
      return new Response(JSON.stringify({ jobs }));
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetch);
  return {
    fetch,
    emit(nextJobs: NativeJob[]) {
      jobs = nextJobs;
      window.dispatchEvent(new Event("native-imports-changed"));
    },
    async loaded() {
      await waitFor(() => expect(reads).toBeGreaterThan(0));
    },
    async update(nextJobs: NativeJob[]) {
      const previousReads = reads;
      jobs = nextJobs;
      act(() => window.dispatchEvent(new Event("native-imports-changed")));
      await waitFor(() => expect(reads).toBeGreaterThan(previousReads));
    },
  };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
  localStorage.clear();
});

it("does not replay historical COMPLETE or FAILED import notices when opening the app", async () => {
  const api = nativeApi([
    mixedComplete("old-complete"),
    { ...mixedComplete("old-failure"), state: "FAILED" },
  ]);
  render(<UiLanguageProvider><NativeImportActivity onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await api.loaded();
  expect(screen.queryByRole("region", { name: "Local imports" })).toBeNull();
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.queryByText("too-long-video.mp4")).toBeNull();
});

it("reports each current batch result after a background import completes", async () => {
  const api = nativeApi([importing("current")]);
  const onOpen = vi.fn();
  render(<UiLanguageProvider><NativeImportActivity onOpen={onOpen} errors={errors} /></UiLanguageProvider>);
  await screen.findByText("Verifying imported file…");
  await api.update([mixedComplete("current")]);
  expect((await screen.findByRole("alert")).textContent).toContain("four-hour duration limit");
  expect(screen.getByText("Import failed")).toBeTruthy();
  expect(screen.getByText("Import successful. File saved.")).toBeTruthy();
  expect(screen.getByText("File saved. Local transcription status appears in Content.")).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: "Open Content: short-video.mp4" }));
  expect(onOpen).toHaveBeenCalledWith("content-current");
});

it("dismisses a completed notice without suppressing errors from a later import", async () => {
  const api = nativeApi([importing("first")]);
  render(<UiLanguageProvider><NativeImportActivity onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await screen.findByText("Verifying imported file…");
  await api.update([mixedComplete("first")]);
  expect((await screen.findByRole("alert")).textContent).toContain("four-hour duration limit");
  await userEvent.click(screen.getByRole("button", { name: "Dismiss import notice" }));
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.queryByRole("region", { name: "Local imports" })).toBeNull();
  await api.update([mixedComplete("first"), importing("second")]);
  expect(await screen.findByText("Verifying imported file…")).toBeTruthy();
  await api.update([mixedComplete("first"), mixedComplete("second")]);
  expect((await screen.findByRole("alert")).textContent).toContain("four-hour duration limit");
  expect(screen.getByRole("button", { name: "Open Content: short-video.mp4" })).toBeTruthy();
  expect(api.fetch.mock.calls.some(([path]) => path.endsWith("/cancel"))).toBe(false);
});

it("keeps a genuine active import visible during navigation and never cancels it", async () => {
  const api = nativeApi([importing("active")]);
  function Page({ page }: { page: string }) {
    return <UiLanguageProvider><h1>{page}</h1><NativeImportActivity onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>;
  }
  const view = render(<Page page="Content" />);
  expect(await screen.findByText("Verifying imported file…")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Dismiss import notice" })).toBeNull();
  view.rerender(<Page page="Following" />);
  expect(screen.getByRole("heading", { name: "Following" })).toBeTruthy();
  expect(screen.getByText("Verifying imported file…")).toBeTruthy();
  expect(screen.getByRole("region", { name: "Local imports" })).toBeTruthy();
  expect(api.fetch.mock.calls.some(([path]) => path.endsWith("/cancel"))).toBe(false);
});

it("clears only terminal notices on route changes while another import remains visible", async () => {
  const api = nativeApi([importing("done"), importing("active")]);
  const view = render(<UiLanguageProvider><NativeImportActivity routeKey="Content" onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await api.loaded();
  await api.update([mixedComplete("done"), importing("active")]);
  await screen.findByRole("alert");
  view.rerender(<UiLanguageProvider><NativeImportActivity routeKey="Following" onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.getByText("Verifying imported file…")).toBeTruthy();
  await api.update([mixedComplete("done"), mixedComplete("active")]);
  expect((await screen.findByRole("alert")).textContent).toContain("four-hour duration limit");
  expect(screen.getAllByRole("button", { name: "Open Content: short-video.mp4" })).toHaveLength(1);
});

it("does not duplicate a current result already shown in the import dialog", async () => {
  const api = nativeApi([importing("inline")]);
  const view = render(<UiLanguageProvider><NativeImportActivity modalOpen routeKey="Following" onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await api.loaded();
  act(() => window.dispatchEvent(new CustomEvent("native-imports-changed", { detail: mixedComplete("inline") })));
  await api.update([mixedComplete("inline")]);
  expect(screen.queryByRole("alert")).toBeNull();
  view.rerender(<UiLanguageProvider><NativeImportActivity routeKey="Content" onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await api.update([mixedComplete("inline")]);
  expect(screen.queryByRole("region", { name: "Local imports" })).toBeNull();
});

it("shows background failure after selection in a dialog without acknowledging it early", async () => {
  const api = nativeApi([]);
  const view = render(<UiLanguageProvider><NativeImportActivity modalOpen routeKey="Following" onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await api.loaded();
  const selected = { ...importing("selected"), state: "SELECTED" };
  act(() => window.dispatchEvent(new CustomEvent("native-imports-changed", { detail: selected })));
  await api.update([selected]);
  await api.update([importing("selected")]);
  await screen.findByText("Verifying imported file…");
  view.rerender(<UiLanguageProvider><NativeImportActivity routeKey="Content" onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await api.update([{ ...mixedComplete("selected"), state: "FAILED" }]);
  expect((await screen.findByRole("alert")).textContent).toContain("four-hour duration limit");
});

it("does not hide an unrelated background result while another Add dialog is open", async () => {
  const api = nativeApi([importing("background")]);
  const view = render(<UiLanguageProvider><NativeImportActivity onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await screen.findByText("Verifying imported file…");
  view.rerender(<UiLanguageProvider><NativeImportActivity modalOpen onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await api.update([mixedComplete("background")]);
  expect((await screen.findByRole("alert")).textContent).toContain("four-hour duration limit");
});

it("expires a terminal notice while preserving its backend history", async () => {
  const api = nativeApi([importing("expiry")]);
  render(<UiLanguageProvider><NativeImportActivity onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await screen.findByText("Verifying imported file…");
  vi.useFakeTimers();
  await act(async () => { api.emit([mixedComplete("expiry")]); });
  expect(screen.getByRole("alert")).toBeTruthy();
  await act(async () => { await vi.advanceTimersByTimeAsync(15000); });
  expect(screen.queryByRole("region", { name: "Local imports" })).toBeNull();
  expect(api.fetch.mock.calls.some(([path]) => path.endsWith("/cancel"))).toBe(false);
});

it("does not poll idle history, and resumes when an import event arrives", async () => {
  const api = nativeApi([mixedComplete("history")]);
  render(<UiLanguageProvider><NativeImportActivity onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await api.loaded();
  const reads = api.fetch.mock.calls.length;
  vi.useFakeTimers();
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(api.fetch.mock.calls.length).toBe(reads);
  vi.useRealTimers();
  await api.update([mixedComplete("history"), importing("new")]);
  expect(await screen.findByText("Verifying imported file…")).toBeTruthy();
});

it("starts the notice timeout at completion, even after a long file-selection pause", async () => {
  const api = nativeApi([importing("delayed")]);
  render(<UiLanguageProvider><NativeImportActivity onOpen={vi.fn()} errors={errors} /></UiLanguageProvider>);
  await screen.findByText("Verifying imported file…");
  vi.useFakeTimers();
  await act(async () => { api.emit([{ ...importing("delayed"), state: "SELECTED" }]); });
  await act(async () => { await vi.advanceTimersByTimeAsync(16000); });
  await act(async () => { api.emit([mixedComplete("delayed")]); });
  expect(screen.getByRole("alert")).toBeTruthy();
  await act(async () => { await vi.advanceTimersByTimeAsync(14000); });
  expect(screen.getByRole("alert")).toBeTruthy();
  await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
  expect(screen.queryByRole("region", { name: "Local imports" })).toBeNull();
});
