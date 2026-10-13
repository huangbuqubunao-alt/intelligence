import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";

const response = (value: unknown) => ({ ok: true, json: async () => value });
const video = { provider: "LOCAL", video_id: "local-video", channel_id: "local-library", channel_name: "Local library", title: "d2-video.mp4", filename: "d2-video.mp4", media_kind: "VIDEO", processing_status: "TRANSCRIPTION_UNAVAILABLE", published_at: "2026-10-09T00:00:00Z", last_updated: "2026-10-09T00:00:00Z" };
let releaseFocus: () => void;
let releaseImport: () => void;
let transcriptionState: { status: string; retry_available: boolean; last_failure_category?: string; capability?: object };
let upload: ReturnType<typeof vi.fn>;
beforeEach(() => {
  location.hash = "#Following";
  localStorage.setItem("yia.ui-language", "en");
  upload = vi.fn(() => new Promise(resolve => { releaseImport = () => resolve(response({ import: { content_id: video.video_id, filename: video.filename, status: video.processing_status, duplicate: false } })); }));
  transcriptionState = { status: "MODEL_MISSING", retry_available: false, capability: { state: "MODEL_MISSING", reason_code: "MODEL_MISSING" } };
  let checks = 0;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/sources/check-stale")) { checks++; return checks === 1 ? Promise.resolve(response({})) : new Promise(resolve => { releaseFocus = () => resolve(response({})); }); }
    if (path.startsWith("/api/v1/local/imports")) return upload(path, init);
    if (path.endsWith("/sources")) return Promise.resolve(response({ sources: [] }));
    if (path.endsWith("/settings")) return Promise.resolve(response({ bilibili: { creator_following: { available: false } } }));
    if (path.endsWith("/videos")) return Promise.resolve(response({ videos: [video] }));
    if (path.endsWith("/videos/local-video")) return Promise.resolve(response({ video, transcript: { status: "UNAVAILABLE" }, note: {}, intelligence_result: { status: "NOT_PROCESSED" }, history: [] }));
    if (path.endsWith("/transcription")) return Promise.resolve(response({ transcription: transcriptionState }));
    if (path.endsWith("/evidence")) return Promise.resolve(response({ evidence: [] }));
    return Promise.resolve(response({}));
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); location.hash = ""; });
async function chooseVideo() {
  render(<App />);
  fireEvent.click((await screen.findAllByRole("button", { name: "Add Source" }))[0]);
  fireEvent.click(screen.getByRole("button", { name: "Import local file" }));
  const file = new File(["synthetic bytes"], video.filename, { type: "video/mp4" });
  fireEvent.change(screen.getByLabelText("Choose local files"), { target: { files: [file] } });
  return file;
}
it("D2-01 preserves the selected video when file-chooser focus triggers a Following refresh", async () => {
  const file = await chooseVideo();
  fireEvent(window, new Event("focus"));
  await act(async () => releaseFocus());
  await waitFor(() => expect(screen.getByRole("heading", { name: "Add local files" })).toBeTruthy());
  expect(screen.getByText(video.filename)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  expect(upload).toHaveBeenCalledTimes(1);
  expect(upload.mock.calls[0][1].body).toBe(file);
  await act(async () => releaseImport());
  await screen.findByRole("heading", { name: "Content" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(await screen.findByText(video.filename, { exact: true })).toBeTruthy();
});
it("D2-01 keeps in-flight import on refresh and page switches, then opens its saved Content once", async () => {
  await chooseVideo();
  fireEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  fireEvent(window, new Event("focus"));
  await act(async () => releaseFocus());
  expect(screen.getByText("Importing selected files…").getAttribute("role")).toBe("status");
  fireEvent.click(screen.getByRole("button", { name: "Content" }));
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  expect(screen.getByRole("button", { name: "Confirm import" }).hasAttribute("disabled")).toBe(true);
  await act(async () => releaseImport());
  await screen.findByRole("heading", { name: "Content" });
  expect(upload).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect((await screen.findAllByText("Local model is missing")).length).toBeGreaterThan(0);
});

// Projection fixtures cover executor states; real no-model media is exercised by browser E2E.
it.each(["en", "zh-CN"])("does not mistake an old unavailable snapshot for current model readiness (%s)", async language => {
  localStorage.setItem("yia.ui-language", language);
  transcriptionState = { status: "FAILED", retry_available: true, last_failure_category: "TRANSCRIPT_INVALID", capability: { state: "READY", qualification_state: "PASSED", production_eligible: true, runtime_available: true, model_present: true, executor_compatible: true } };
  location.hash = "#Content";
  render(<App />);
  expect(await screen.findByText(language === "en" ? "File saved" : "文件已保存")).toBeTruthy();
  expect(screen.queryByText(language === "en" ? "Local transcription is unavailable" : "本地转写暂不可用")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /d2-video\.mp4/ }));
  await screen.findByText(language === "en" ? "Local transcription failed" : "本地转写失败", { selector: "p[role=status]" });
  expect(screen.queryByText(language === "en" ? "Local transcription is unavailable" : "本地转写暂不可用")).toBeNull();
  expect(screen.getByText(language === "en" ? "No usable transcript was accepted. Your original file is saved. Check for clear speech before retrying transcription." : "未获得可用字幕，原文件已保留。请确认录音包含清晰语音后，再重试转写。")).toBeTruthy();
  expect(upload).not.toHaveBeenCalled();
});

it.each(["en", "zh-CN"])("shows live processing progress and failure reason after admission (%s)", async language => {
  localStorage.setItem("yia.ui-language", language);
  const t = (en: string, zh: string) => language === "en" ? en : zh;
  for (const status of ["RUNNING", "FAILED"]) {
    transcriptionState = { status, retry_available: status === "FAILED", last_failure_category: status === "FAILED" ? "EXECUTOR_TIMEOUT" : undefined };
    location.hash = "#Content/local-video";
    const view = render(<App />);
    await screen.findByText(t(status === "RUNNING" ? "Transcribing…" : "Local transcription failed", status === "RUNNING" ? "正在转写…" : "本地转写失败"), { selector: "p[role=status]" });
    if (status === "FAILED") {
      expect(screen.getByText(t("Transcription exceeded its time limit. You can retry the selected executor.", "转写已超时，可使用所选执行器重试。"))).toBeTruthy();
      expect(screen.getByRole("button", { name: t("Retry transcription", "重试转写") })).toBeTruthy();
    }
    expect(screen.getByRole("heading", { name: video.filename })).toBeTruthy();
    expect(upload).not.toHaveBeenCalled();
    view.unmount();
  }
});
