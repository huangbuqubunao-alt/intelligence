import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CreatorFollowingDetail, type CreatorFollowingCapabilityState } from "./CreatorFollowing";
import { UiLanguageProvider } from "./uiLanguage";

const withdrawn: CreatorFollowingCapabilityState = { known: true, capability: { available: false, code: "CREATOR_TRACKING_UNAVAILABLE" } };
const detail = (id: string, provider = "YOUTUBE", active = false) => ({ source: {
  source_id: id, provider, display_name: id === "channel-a" ? "Google for Developers" : "Other source",
  canonical_url: provider === "YOUTUBE" ? "https://www.youtube.com/@GoogleDevelopers" : "https://space.bilibili.com/123",
  enabled: true, last_checked_at: null, last_success_at: null,
  tracking: { health: "HEALTHY", coverage: "COMPLETE", update_count: 0, pending_count: 0 },
}, recent_videos: [], source_runs: active ? [{ run_id: "existing-run", state: "RUNNING" }] : [] });
const response = (value: unknown) => ({ ok: true, json: async () => value });
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }
const props = { capability: withdrawn, onClose: vi.fn(), onRefresh: vi.fn() };
const view = (id = "channel-a") => <UiLanguageProvider><CreatorFollowingDetail id={id} {...props} /></UiLanguageProvider>;
beforeEach(() => { localStorage.setItem("yia.ui-language", "en"); vi.clearAllMocks(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear(); });

it.each(["en", "zh-CN"])("uses a neutral initial loading identity, then real YouTube without a Bilibili notice (%s)", async language => {
  localStorage.setItem("yia.ui-language", language);
  const pending = deferred<ReturnType<typeof response>>();
  const fetch = vi.fn(() => pending.promise); vi.stubGlobal("fetch", fetch);
  render(view());
  expect(screen.getByRole("dialog", { name: language === "en" ? "Following" : "关注" })).toBeTruthy();
  expect(screen.getByText(language === "en" ? "Loading Source…" : "正在加载关注…")).toBeTruthy();
  expect(screen.queryByText(language === "en" ? "Continuous creator tracking is currently unavailable" : "UP 主持续关注当前暂不可用")).toBeNull();
  expect(screen.queryByRole("button", { name: language === "en" ? "Check Now" : "立即检查" })).toBeNull();
  await act(async () => pending.resolve(response(detail("channel-a"))));
  expect(await screen.findByRole("heading", { name: "Google for Developers" })).toBeTruthy();
  expect(screen.getByRole("dialog", { name: language === "en" ? "Channel Following" : "频道关注" })).toBeTruthy();
  expect(screen.queryByText(language === "en" ? "Continuous creator tracking is currently unavailable" : "UP 主持续关注当前暂不可用")).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("drops the previous identity immediately on ID change and ignores its late read", async () => {
  const old = deferred<ReturnType<typeof response>>(), next = deferred<ReturnType<typeof response>>();
  const fetch = vi.fn((url: string) => url.endsWith("channel-a") ? old.promise : next.promise); vi.stubGlobal("fetch", fetch);
  const { rerender } = render(view());
  rerender(view("channel-b"));
  await act(async () => old.resolve(response(detail("channel-a"))));
  expect(screen.queryByText("Google for Developers")).toBeNull();
  expect(screen.getByRole("dialog", { name: "Following" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Pause monitoring" })).toBeNull();
  await act(async () => next.resolve(response(detail("channel-b"))));
  expect(await screen.findByRole("heading", { name: "Other source" })).toBeTruthy();
  expect(fetch.mock.calls.map(([url]) => url)).toEqual(["/api/v1/sources/channel-a", "/api/v1/sources/channel-b"]);
});

it.each(["en", "zh-CN"])("keeps a failed first read explicit and only retries GET before showing the actual provider (%s)", async language => {
  localStorage.setItem("yia.ui-language", language);
  const next = deferred<ReturnType<typeof response>>();
  const fetch = vi.fn().mockRejectedValueOnce(new TypeError("offline socket fixture")).mockImplementation(() => next.promise); vi.stubGlobal("fetch", fetch);
  render(view());
  const retry = await screen.findByRole("button", { name: language === "en" ? "Retry source details" : "重试加载来源详情" });
  expect(screen.getByRole("alert").textContent).not.toContain("socket");
  expect(screen.getByRole("dialog", { name: language === "en" ? "Following" : "关注" })).toBeTruthy();
  fireEvent.click(retry);
  expect(screen.getByRole("alert")).toBeTruthy();
  await act(async () => next.resolve(response(detail("channel-a"))));
  expect(await screen.findByText("Google for Developers")).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
  expect(fetch.mock.calls.every(([, init]) => !init || (init as RequestInit).method === undefined || (init as RequestInit).method === "GET")).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("hides loaded identity and controls while the next source is pending", async () => {
  const next = deferred<ReturnType<typeof response>>();
  vi.stubGlobal("fetch", vi.fn((url: string) => url.endsWith("channel-a") ? Promise.resolve(response(detail("channel-a"))) : next.promise));
  const { rerender } = render(view()); await screen.findByText("Google for Developers");
  rerender(view("channel-b"));
  expect(screen.queryByText("Google for Developers")).toBeNull();
  expect(screen.queryByRole("button", { name: "Pause monitoring" })).toBeNull();
  expect(screen.getByRole("dialog", { name: "Following" })).toBeTruthy();
  await act(async () => next.resolve(response(detail("channel-b", "BILIBILI"))));
  await screen.findByText("Other source");
  expect(screen.getByText("Continuous creator tracking is currently unavailable")).toBeTruthy();
  expect((screen.getByRole("button", { name: "Check Now" }) as HTMLButtonElement).disabled).toBe(true);
});

it("preserves loaded identity on failed polling and manual read recovery never replays the check", async () => {
  vi.useFakeTimers();
  let reads = 0;
  const fetch = vi.fn(async (_url: string, init?: RequestInit) => {
    expect(init?.method).not.toBe("POST"); expect(init?.method).not.toBe("PATCH");
    if (++reads === 2) throw new TypeError("temporary read failure");
    return response(detail("channel-a", "YOUTUBE", reads === 1));
  }); vi.stubGlobal("fetch", fetch);
  render(view()); await act(async () => {});
  expect(screen.getByText("Google for Developers")).toBeTruthy();
  await act(async () => vi.advanceTimersByTime(2000));
  expect(screen.getByRole("alert")).toBeTruthy();
  expect(screen.getByText("Google for Developers")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Retry source details" }));
  await act(async () => {});
  expect(screen.queryByRole("alert")).toBeNull(); expect(reads).toBe(3);
  expect(props.onRefresh).not.toHaveBeenCalled();
});

it("rejects a source response for a different ID and can recover through a fresh read", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(response(detail("channel-b"))).mockResolvedValueOnce(response(detail("channel-a"))); vi.stubGlobal("fetch", fetch);
  render(view());
  fireEvent.click(await screen.findByRole("button", { name: "Retry source details" }));
  expect(await screen.findByText("Google for Developers")).toBeTruthy();
  expect(screen.queryByText("Other source")).toBeNull();
});

it("ignores a delayed response after the detail is closed", async () => {
  const pending = deferred<ReturnType<typeof response>>(); vi.stubGlobal("fetch", vi.fn(() => pending.promise));
  const { unmount } = render(view()); unmount();
  await act(async () => pending.resolve(response(detail("channel-a"))));
  expect(screen.queryByRole("dialog")).toBeNull(); expect(props.onRefresh).not.toHaveBeenCalled();
});

it.each(["empty-500", "invalid-json", "missing-source", "unknown-provider"])("keeps an unreadable/unknown identity neutral and recovers with only GET (%s)", async failure => {
  const bad = failure === "empty-500" ? { ok: false, status: 500, json: async () => { throw new SyntaxError("Unexpected end"); } }
    : failure === "invalid-json" ? { ok: true, status: 200, json: async () => { throw new SyntaxError("invalid fixture"); } }
    : response(failure === "unknown-provider" ? detail("channel-a", "UNKNOWN") : {});
  const fetch = vi.fn().mockResolvedValueOnce(bad).mockResolvedValueOnce(response(detail("channel-a"))); vi.stubGlobal("fetch", fetch);
  render(view());
  const retry = await screen.findByRole("button", { name: "Retry source details" });
  expect(screen.getByRole("dialog", { name: "Following" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Pause monitoring" })).toBeNull();
  fireEvent.click(retry); await screen.findByText("Google for Developers");
  expect(screen.queryByRole("alert")).toBeNull();
  expect(fetch.mock.calls.every(([, init]) => !(init as RequestInit | undefined)?.method)).toBe(true);
});

it("manual recovery after a check response never repeats the accepted command", async () => {
  let reads = 0, commands = 0;
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === "POST") { commands++; return response({ source_run: { run_id: "accepted-check" } }); }
    expect(url).toBe("/api/v1/sources/channel-a");
    if (++reads === 2) throw new TypeError("read after accepted command failed");
    return response({ ...detail("channel-a"), source_runs: reads > 2 ? [{ run_id: "accepted-check", state: "SUCCEEDED" }] : [] });
  }); vi.stubGlobal("fetch", fetch);
  render(view()); fireEvent.click(await screen.findByRole("button", { name: "Check Now" }));
  const retry = await screen.findByRole("button", { name: "Retry source details" });
  expect(screen.getByText("Google for Developers")).toBeTruthy();
  fireEvent.click(retry);
  await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  expect(commands).toBe(1); expect(reads).toBe(3); expect(props.onRefresh).toHaveBeenCalledTimes(1);
  expect(screen.queryByText("Checking…")).toBeNull();
});

it.each(["check", "pause", "policy"])("ignores a delayed %s result after closing instead of changing another source", async action => {
  const command = deferred<ReturnType<typeof response>>();
  const fetch = vi.fn((url: string, init?: RequestInit) => init?.method
    ? command.promise : Promise.resolve(response(detail(url.endsWith("channel-b") ? "channel-b" : "channel-a")))); vi.stubGlobal("fetch", fetch);
  const { rerender } = render(view()); await screen.findByText("Google for Developers");
  if (action === "policy") fireEvent.change(screen.getByRole("combobox", { name: "When new content is found" }), { target: { value: "EXTRACT_INTELLIGENCE" } });
  else fireEvent.click(screen.getByRole("button", { name: action === "check" ? "Check Now" : "Pause monitoring" }));
  rerender(view("channel-b")); await screen.findByText("Other source");
  await act(async () => command.resolve(response({ source_run: { run_id: "old-source-command" } })));
  expect(screen.queryByText("Google for Developers")).toBeNull();
  expect(screen.queryByText("Saved")).toBeNull(); expect(screen.queryByText("Checking…")).toBeNull();
  expect(props.onRefresh).not.toHaveBeenCalled();
  expect(fetch.mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method)).toHaveLength(1);
});
