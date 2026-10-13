import { act, cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

const response = (body: object) => ({ ok: true, json: async () => body });
const status = { availability: "NOT_QUALIFIED", reason_code: "NO_QUALIFIED_MODEL", qualified: false, production_eligible: false, consent_required: false, routes: [] };
const detail = (id: string) => ({
  video: { video_id: id, title: `Content ${id}`, provider: "YOUTUBE", source_url: `https://youtube.test/${id}`, processing_status: "COMPLETE" },
  transcript: { status: "AVAILABLE", text: `Original ${id} transcript.`, created_at: "2026-09-01T00:00:00Z" },
  note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
  intelligence_result: { status: "NOT_PROCESSED" }, history: [],
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });
function open(language: string, read: (path: string) => Promise<ReturnType<typeof response>>) {
  localStorage.setItem("yia.ui-language", language);
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/a";
  const fetch = vi.fn((path: string, _init?: RequestInit) => {
    if (path.endsWith("/deep-analysis")) return read(path);
    if (path.endsWith("/evidence")) return Promise.resolve(response({ evidence: [] }));
    if (/\/videos\/[ab]$/.test(path)) return Promise.resolve(response(detail(path.slice(-1))));
    if (path.endsWith("/videos")) return Promise.resolve(response({ videos: [detail("a").video, detail("b").video] }));
    return Promise.resolve(response({}));
  });
  vi.stubGlobal("fetch", fetch); render(<App />); return fetch;
}
async function panel(language: string) {
  return (await screen.findByRole("heading", { name: language === "en" ? "Deep Analysis" : "深度分析" })).closest("section")!;
}

it.each(["en", "zh-CN"])("reads delayed Deep Analysis without inventing a lifecycle or qualification in %s", async language => {
  let finish!: (value: ReturnType<typeof response>) => void;
  const fetch = open(language, () => new Promise(resolve => { finish = resolve; }));
  const view = within(await panel(language));
  expect(view.getByText(language === "en" ? "Reading Deep Analysis status…" : "正在读取深度分析状态…")).toBeTruthy();
  expect(view.queryByText(language === "en" ? "Not run yet" : "尚未运行")).toBeNull();
  expect((view.getByRole("button", { name: language === "en" ? "Run Deep Analysis" : "开始深度分析" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("Original a transcript.")).toBeTruthy();
  await act(async () => finish(response({ deep_analysis: { status, result: null } })));
  expect(view.queryByText(language === "en" ? "Reading Deep Analysis status…" : "正在读取深度分析状态…")).toBeNull();
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it.each(["en", "zh-CN"])("retries a failed Deep Analysis read with GET only in %s", async language => {
  let attempts = 0;
  const fetch = open(language, () => ++attempts === 1 ? Promise.reject(new Error("private raw detail")) : Promise.resolve(response({ deep_analysis: { status, result: null } })));
  const view = within(await panel(language));
  const reload = await view.findByRole("button", { name: language === "en" ? "Reload page data" : "重新加载页面数据" });
  expect(view.queryByText(language === "en" ? "Not run yet" : "尚未运行")).toBeNull();
  expect(screen.getByText("Original a transcript.")).toBeTruthy();
  await userEvent.click(reload);
  await view.findByText(language === "en" ? "Unavailable until a model is qualified for Deep Analysis." : "在有模型通过深度分析资格之前，此功能不可用。");
  expect(attempts).toBe(2);
  expect(fetch.mock.calls.every(([, init]) => (!init?.method || init.method === "GET") && init?.body === undefined)).toBe(true);
});

it("keeps late prior Content Deep Analysis from changing the new route", async () => {
  let finishOld!: (value: ReturnType<typeof response>) => void;
  const fetch = open("en", path => path.includes("/a/") ? new Promise(resolve => { finishOld = resolve; }) : Promise.resolve(response({ deep_analysis: { status, result: null } })));
  await panel("en");
  await act(async () => { location.hash = "#Content/b"; dispatchEvent(new HashChangeEvent("hashchange")); });
  await screen.findByText("Original b transcript.");
  await act(async () => finishOld(response({ deep_analysis: { status: { ...status, availability: "NOT_REQUESTED", qualified: true, production_eligible: true }, result: null } })));
  const view = within(await panel("en"));
  expect(view.queryByText("Not run yet")).toBeNull();
  expect((view.getByRole("button", { name: "Run Deep Analysis" }) as HTMLButtonElement).disabled).toBe(true);
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it("does not turn an incomplete Deep Analysis projection into NOT_REQUESTED and restores a known state by GET", async () => {
  let reads = 0;
  const fetch = open("en", () => Promise.resolve(response(++reads === 1 ? { deep_analysis: {} } : { deep_analysis: { status: { ...status, availability: "NOT_REQUESTED" }, result: null } })));
  const view = within(await panel("en"));
  const reload = await view.findByRole("button", { name: "Reload page data" });
  expect(view.queryByText("Not run yet")).toBeNull();
  expect((view.getByRole("button", { name: "Run Deep Analysis" }) as HTMLButtonElement).disabled).toBe(true);
  await userEvent.click(reload);
  await view.findByText("Not run yet");
  expect(reads).toBe(2);
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});
