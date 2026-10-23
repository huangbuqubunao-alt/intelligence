import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { NativeJob } from "./NativeLocalImport";

const response = (body: object) => ({ ok: true, json: async () => body });
const emptyCopy = "No Content yet. Add a video link, follow a YouTube channel, or import a local file.";
const isMutation = ([path, init]: [string, RequestInit?]) => init?.method === "POST" && path !== "/api/v1/local/native/jobs";
const video = {
  video_id: "abcdefghijk", title: "Imported source", provider: "LOCAL", media_kind: "TEXT",
  format: "txt", processing_status: "READY", channel_name: "Local library",
};
const detail = {
  video, transcript: { status: "AVAILABLE", text: "Original imported text." },
  note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
  intelligence_result: { status: "NOT_PROCESSED" }, history: [],
};

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });

function open(language: string, readVideos?: () => Promise<ReturnType<typeof response>>) {
  localStorage.setItem("yia.ui-language", language);
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  if (!location.hash.startsWith("#Content")) location.hash = "#Content";
  vi.stubGlobal("navigator", { platform: "MacIntel" });
  let saved = false;
  let job: NativeJob = {
    job_id: "selected-file", state: "SELECTED", error_code: null,
    files: [{ filename: "first-source.txt", byte_count: 20, loaded: 0, phase: "SELECTED",
      snapshot_method: "PENDING", error_code: null, processing_error_code: null, import: null }],
  };
  const fetch = vi.fn(async (path: string, init?: RequestInit) => {
    if (path === "/api/v1/videos") return readVideos ? readVideos() : response({ videos: saved ? [video] : [] });
    if (path === "/api/v1/local/native/capability") return response({ capability: { available: true } });
    if (path === "/api/v1/local/native/jobs") return response({ jobs: saved ? [job] : [] });
    if (path === "/api/v1/local/native/picks") return response({ job });
    if (path === "/api/v1/local/native/picks/selected-file/confirm") {
      saved = true;
      job = { ...job, state: "COMPLETE", files: [{ ...job.files[0], phase: "SAVED",
        import: { content_id: video.video_id, filename: "first-source.txt", status: "READY", duplicate: false } }] };
      return response({ job });
    }
    if (path === "/api/v1/sources/import") { saved = true; return response({ source: { video_id: video.video_id } }); }
    if (path === `/api/v1/videos/${video.video_id}`) return response(detail);
    if (path.endsWith("/evidence")) return response({ evidence: [] });
    if (path.endsWith("/deep-analysis")) return response({ deep_analysis: { status: {
      availability: "NOT_QUALIFIED", reason_code: "NO_QUALIFIED_MODEL", qualified: false,
      production_eligible: false, consent_required: false, routes: [],
    }, result: null } });
    throw new Error(`Unexpected request: ${path} ${init?.method ?? "GET"}`);
  });
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  return { fetch, t: (en: string, zh: string) => language === "en" ? en : zh };
}

it.each(["en", "zh-CN"])("opens the shared Add dialog from empty Content with Tab and Enter, then closes back (%s)", async language => {
  const user = userEvent.setup();
  const { fetch, t } = open(language);
  const add = await screen.findByRole("button", { name: t("Add content", "添加内容") });
  expect(screen.getByText(t(emptyCopy, "暂无内容。添加视频链接，持续关注 YouTube 频道，或导入本地文件。"))).toBeTruthy();
  expect(add.tagName).toBe("BUTTON");
  for (let index = 0; index < 7; index++) await user.tab();
  expect(document.activeElement).toBe(add);
  await user.keyboard("{Enter}");
  expect(screen.getByRole("dialog", { name: t("Add a Source", "添加关注") })).toBeTruthy();
  expect(document.activeElement).toBe(screen.getByRole("textbox", { name: t("Paste link", "粘贴链接") }));
  expect(screen.getByRole("button", { name: t("Import local file", "导入本地文件") })).toBeTruthy();
  await user.click(screen.getByRole("button", { name: t("Close", "关闭") }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(location.hash).toBe("#Content");
  expect(screen.getByRole("button", { name: t("Add content", "添加内容") })).toBeTruthy();
  expect(fetch.mock.calls.filter(isMutation)).toHaveLength(0);
});

it.each(["en", "zh-CN"])("uses the existing URL importer and opens its saved Content without changing Following (%s)", async language => {
  const user = userEvent.setup();
  const { fetch, t } = open(language);
  await user.click(await screen.findByRole("button", { name: t("Add content", "添加内容") }));
  await user.type(screen.getByRole("textbox", { name: t("Paste link", "粘贴链接") }), "https://youtu.be/abcdefghijk");
  await user.click(screen.getByRole("button", { name: t("Confirm import", "确认导入") }));
  await user.click(await screen.findByRole("link", { name: t("Open Content", "打开内容") }));
  expect(await screen.findByRole("heading", { name: video.title })).toBeTruthy();
  expect(location.hash).toBe(`#Content/${video.video_id}`);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.queryByRole("button", { name: t("Add content", "添加内容") })).toBeNull();
  const writes = fetch.mock.calls.filter(isMutation);
  expect(writes).toHaveLength(1);
  expect(writes[0][0]).toBe("/api/v1/sources/import");
  expect(JSON.parse(writes[0][1]!.body as string)).toEqual({ url: "https://www.youtube.com/watch?v=abcdefghijk", command_id: expect.any(String) });
  await user.click(screen.getByRole("button", { name: t("Back to Content", "返回内容") }));
  expect(await screen.findByRole("button", { name: /Imported source/ })).toBeTruthy();
  expect(location.hash).toBe("#Content");
  expect(screen.queryByRole("button", { name: t("Add content", "添加内容") })).toBeNull();
});

it.each(["en", "zh-CN"])("reuses native local selection, cancel, import feedback and Content return (%s)", async language => {
  const user = userEvent.setup();
  const { fetch, t } = open(language);
  const add = await screen.findByRole("button", { name: t("Add content", "添加内容") });
  await user.click(add);
  await user.click(screen.getByRole("button", { name: t("Import local file", "导入本地文件") }));
  expect(await screen.findByRole("heading", { name: t("Add local files", "添加本地文件") })).toBeTruthy();
  await user.click(screen.getByRole("button", { name: t("Cancel", "取消") }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(location.hash).toBe("#Content");
  await user.click(add);
  await user.click(screen.getByRole("button", { name: t("Import local file", "导入本地文件") }));
  const choose = screen.getByRole("button", { name: t("Choose local files", "选择本地文件") });
  await waitFor(() => expect((choose as HTMLButtonElement).disabled).toBe(false));
  expect(document.querySelector('input[type="file"]')).toBeNull();
  await user.click(choose);
  await user.click(await screen.findByRole("button", { name: t("Confirm import", "确认导入") }));
  expect(await screen.findByRole("heading", { name: video.title })).toBeTruthy();
  expect(location.hash).toBe(`#Content/${video.video_id}`);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByText(t("File imported. Its processing status appears below.", "文件已导入。处理状态显示在下方。"))).toBeTruthy();
  const writes = fetch.mock.calls.filter(isMutation);
  expect(writes.map(([path]) => path)).toEqual(["/api/v1/local/native/picks", "/api/v1/local/native/picks/selected-file/confirm"]);
  expect(writes.every(([, init]) => init?.body === "{}")).toBe(true);
  await user.click(screen.getByRole("button", { name: t("Back to Content", "返回内容") }));
  expect(await screen.findByRole("button", { name: /Imported source/ })).toBeTruthy();
  expect(screen.queryByText(t("File imported. Its processing status appears below.", "文件已导入。处理状态显示在下方。"))).toBeNull();
});

it.each(["en", "zh-CN"])("offers the empty action only after a successful list read, preserving error retry (%s)", async language => {
  let reject!: (reason: Error) => void;
  let reads = 0;
  const { t } = open(language, () => ++reads === 1
    ? new Promise((_resolve, fail) => { reject = fail; })
    : Promise.resolve(response({ videos: [] })));
  expect(screen.getByText(t("Loading Content…", "正在加载内容…"))).toBeTruthy();
  expect(screen.queryByRole("button", { name: t("Add content", "添加内容") })).toBeNull();
  await act(async () => reject(new Error("Failed to fetch")));
  expect(screen.getByRole("alert")).toBeTruthy();
  expect(screen.queryByRole("button", { name: t("Add content", "添加内容") })).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: t("Retry", "重试") }));
  expect(await screen.findByRole("button", { name: t("Add content", "添加内容") })).toBeTruthy();
  expect(reads).toBe(2);
});

it.each(["en", "zh-CN"])("preserves a direct Content route even when its list is empty (%s)", async language => {
  location.hash = `#Content/${video.video_id}`;
  const { t } = open(language);
  expect(await screen.findByRole("heading", { name: video.title })).toBeTruthy();
  expect(screen.queryByRole("button", { name: t("Add content", "添加内容") })).toBeNull();
  expect(screen.getByText("Original imported text.")).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: t("Back to Content", "返回内容") }));
  expect(await screen.findByRole("button", { name: t("Add content", "添加内容") })).toBeTruthy();
});
