import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { LocalImport } from "./LocalImport";
import { UiLanguageProvider } from "./uiLanguage";

class Upload {
  static current: Upload;
  upload = { onprogress: null as ((event: ProgressEvent) => void) | null, onload: null as (() => void) | null };
  onload: (() => void) | null = null;
  onabort: (() => void) | null = null;
  ontimeout: (() => void) | null = null;
  onerror: (() => void) | null = null;
  timeout = 0;
  status = 201;
  responseText = JSON.stringify({ import: { content_id: "saved-large", filename: "large.mp4", status: "TRANSCRIPTION_UNAVAILABLE", duplicate: false } });
  headers: Record<string, string> = {};
  body: File | null = null;
  path = "";
  constructor() { Upload.current = this; }
  open(_method: string, path: string) { this.path = path; }
  setRequestHeader(name: string, value: string) { this.headers[name] = value; }
  send(file: File) { this.body = file; }
  abort() { this.onabort?.(); }
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function view() {
  localStorage.setItem("yia.ui-language", "en");
  vi.stubGlobal("XMLHttpRequest", Upload);
  const onImported = vi.fn();
  render(<UiLanguageProvider><LocalImport onClose={vi.fn()} onSaved={vi.fn()} onYouTube={vi.fn()} onImported={onImported} /></UiLanguageProvider>);
  return onImported;
}
function sizedFile(size: number, name = "large.mp4") {
  const file = new File(["boundary simulation"], name);
  Object.defineProperty(file, "size", { value: size });
  return file;
}

it.each([2 * 1024 ** 3 - 1, 2 * 1024 ** 3])("admits simulated boundary %i with real upload events and saved navigation", async size => {
  const imported = view(), file = sizedFile(size);
  await userEvent.upload(screen.getByLabelText("Choose local files"), file);
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  const upload = Upload.current;
  expect(upload.body).toBe(file);
  expect(upload.headers["X-YIA-Request"]).toBe("local-ui");
  expect(upload.timeout).toBeGreaterThan(2 * 60 * 60 * 1000);
  act(() => upload.upload.onprogress?.(new ProgressEvent("progress", { lengthComputable: true, loaded: Math.ceil(size / 2), total: size })));
  expect(screen.getByText("large.mp4: 50%")).toBeTruthy();
  expect(screen.getByRole("progressbar").getAttribute("max")).toBe(String(size));
  expect(imported).not.toHaveBeenCalled();
  act(() => upload.upload.onload?.());
  expect(screen.getByRole("status").textContent).toBe("Verifying imported file…");
  expect(screen.queryByRole("progressbar")).toBeNull();
  act(() => upload.onload?.());
  await waitFor(() => expect(imported).toHaveBeenCalledWith("saved-large"));
  expect(screen.getByText("Import successful. File saved.")).toBeTruthy();
  expect(screen.getByText("Local transcription is unavailable")).toBeTruthy();
});

it.each([[2 * 1024 ** 3 + 1, "large.mp4", "2 GiB"], [2 * 1024 ** 2 + 1, "notes.md", "2 MiB"], [0, "empty.wav", "empty"]] as const)("rejects simulated size %i for %s before uploading", async (size, name, message) => {
  view();
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  await userEvent.upload(screen.getByLabelText("Choose local files"), sizedFile(size, name));
  expect(screen.getByRole("alert").textContent).toContain(message);
  expect(screen.getByRole("button", { name: "Confirm import" }).hasAttribute("disabled")).toBe(true);
  expect(fetch).not.toHaveBeenCalled();
});

it("cancel keeps the dialog and explicitly reports retry-safe uncertainty", async () => {
  const imported = view();
  await userEvent.upload(screen.getByLabelText("Choose local files"), sizedFile(100 * 1024 ** 2));
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  await userEvent.click(screen.getByRole("button", { name: "Cancel import" }));
  await screen.findByRole("button", { name: "Retry failed files" });
  expect(screen.getByRole("alert").textContent).toContain("Import cancelled");
  expect(screen.getByRole("dialog")).toBeTruthy();
  expect(imported).not.toHaveBeenCalled();
});

it("reports timeout separately from duration and file size", async () => {
  view();
  await userEvent.upload(screen.getByLabelText("Choose local files"), sizedFile(100 * 1024 ** 2));
  await userEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  act(() => Upload.current.ontimeout?.());
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Import timed out"));
});
