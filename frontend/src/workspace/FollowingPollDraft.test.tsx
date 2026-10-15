import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "./App";

const response = (value: unknown, status = 200) => ({ ok: status < 400, status, json: async () => value });
const deferred = <T,>() => { let resolve!: (value: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { promise, resolve }; };
const source = (id = "channel-a", checking = true) => ({ source_id: id, source_type: "CHANNEL", provider: "YOUTUBE", display_name: id === "channel-a" ? "Channel A" : "Channel B", canonical_url: `https://www.youtube.com/@${id}`, enabled: true, processing_policy: "DISCOVER_ONLY", last_error: null, last_checked_at: null, last_success_at: null, tracking: { checking, health: "HEALTHY", coverage: "COMPLETE", update_count: 0, pending_count: 0 } });
let active = false;
const detail = (id = "channel-a") => ({ source: source(id), recent_videos: [], schedules: [], source_runs: active ? [{ run_id: "checking-run", state: "RUNNING" }] : [], policy: { source_id: id, source_policy_revision_id: "r0", initial_history_count: 3, per_run_max_new_videos: 10, focus_rules: ["robotics, autonomy"], ignore_rules: [], distillation_style: "BALANCED" }, policy_modes: { focus: "OVERRIDE", ignore: "INHERIT", style: "INHERIT" } });
let listRead: () => Promise<ReturnType<typeof response>>;
let detailRead: (id: string) => Promise<ReturnType<typeof response>>;
let fetcher: ReturnType<typeof vi.fn>;
const flush = async () => { await act(async () => {}); };
const tick = async (ms = 2000) => { await act(async () => { vi.advanceTimersByTime(ms); }); };
async function openDraft() {
  render(<App />); await flush();
  fireEvent.click(screen.getByRole("button", { name: /Channel A/ })); await flush();
  fireEvent.click(screen.getByRole("button", { name: "Edit interests" })); await flush();
  const input = screen.getByLabelText("Focus"); input.focus();
  fireEvent.change(input, { target: { value: "unsaved，draft\nwith  spaces" } });
  return input;
}
beforeEach(() => {
  vi.useFakeTimers(); location.hash = "#Following"; localStorage.setItem("yia.ui-language", "en"); active = false;
  listRead = async () => response({ sources: [source(), source("channel-b", false)] });
  detailRead = async id => response(detail(id));
  fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === "PUT") return response({ error: { code: "CONFLICT", message: "conflict" } }, 409);
    if (url.endsWith("/sources/check-stale")) return response({});
    if (url.endsWith("/sources")) return listRead();
    if (url.endsWith("/videos")) return response({ videos: [] });
    if (/\/sources\/channel-[ab]$/.test(url)) return detailRead(url.endsWith("channel-b") ? "channel-b" : "channel-a");
    return response({});
  }); vi.stubGlobal("fetch", fetcher);
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });

it.each([false, true])("retains the actual Sources/detail/editor tree and input focus across repeated polls (run active=%s)", async running => {
  active = running; const input = await openDraft(); const before = fetcher.mock.calls.filter(([url]) => url.endsWith("/sources")).length;
  for (let cycle = 0; cycle < 3; cycle++) {
    await tick();
    expect(screen.getByLabelText("Focus")).toBe(input); expect(document.activeElement).toBe(input);
    expect((input as HTMLTextAreaElement).value).toBe("unsaved，draft\nwith  spaces");
  }
  expect(fetcher.mock.calls.filter(([url]) => url.endsWith("/sources")).length).toBeGreaterThanOrEqual(before + 3);
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === "PUT")).toHaveLength(0);
});

it("keeps the editor during a slow list refresh and exposes failure until a successful retry", async () => {
  const input = await openDraft(); const pending = deferred<ReturnType<typeof response>>(); listRead = () => pending.promise;
  await tick(); await tick(4000);
  expect(screen.getByLabelText("Focus")).toBe(input); expect(document.activeElement).toBe(input);
  await act(async () => pending.resolve(response({ error: { code: "READ_SERVICE_UNAVAILABLE", message: "offline" } }, 503)));
  expect(screen.getByText("The Following list could not be refreshed. Showing previously loaded sources.")).toBeTruthy();
  expect(screen.getByLabelText("Focus")).toBe(input);
  const recovered = deferred<ReturnType<typeof response>>(); listRead = () => recovered.promise;
  fireEvent.click(screen.getAllByRole("button", { name: "Reload page data" }).at(-1)!); await flush();
  expect(screen.getByText("The Following list could not be refreshed. Showing previously loaded sources.")).toBeTruthy();
  await act(async () => recovered.resolve(response({ sources: [source("channel-a", false)] })));
  expect(screen.queryByText("The Following list could not be refreshed. Showing previously loaded sources.")).toBeNull();
  expect(screen.getByLabelText("Focus")).toBe(input);
});

it("does not rebase or replay the interest command when polls update the server policy", async () => {
  const input = await openDraft(); detailRead = async id => response({ ...detail(id), policy: { ...detail(id).policy, source_policy_revision_id: "r1", focus_rules: ["server changed"] } });
  await tick(); fireEvent.click(screen.getByRole("button", { name: "Save interests" })); await flush();
  expect(JSON.parse(fetcher.mock.calls.find(([, init]) => init?.method === "PUT")![1].body as string).expected_source_policy_revision_id).toBe("r0");
  expect(screen.getByRole("alert").textContent).toContain("Your draft is preserved");
  await tick(); await tick();
  expect(screen.getByLabelText("Focus")).toBe(input); expect((input as HTMLTextAreaElement).value).toBe("unsaved，draft\nwith  spaces");
  expect((screen.getByRole("button", { name: "Save interests" }) as HTMLButtonElement).disabled).toBe(true);
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === "PUT")).toHaveLength(1);
});

it("isolates a newly selected source and ignores old list and detail responses after navigation", async () => {
  await openDraft(); const late = deferred<ReturnType<typeof response>>(); listRead = () => late.promise;
  await tick(); fireEvent.click(screen.getByRole("button", { name: "Close" }));
  fireEvent.click(screen.getByRole("button", { name: /Channel B/ })); await flush();
  expect(within(screen.getByRole("dialog")).getByRole("heading", { name: "Channel B" })).toBeTruthy();
  expect(screen.queryByLabelText("Focus")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Content" })); await flush();
  await act(async () => late.resolve(response({ sources: [source()] })));
  expect(screen.queryByRole("dialog")).toBeNull(); expect(screen.queryByText("Channel A")).toBeNull();
});

it("keeps the draft on unknown list/detail payloads and never presents a foreign source", async () => {
  active = true; const input = await openDraft();
  listRead = async () => response({ sources: null });
  detailRead = async () => response(detail("foreign"));
  await tick();
  expect(screen.getByLabelText("Focus")).toBe(input);
  expect(screen.getByText("The Following list could not be refreshed. Showing previously loaded sources.")).toBeTruthy();
  expect(screen.getByText("Source details could not be refreshed. Showing previously loaded details.")).toBeTruthy();
  expect(screen.queryByRole("heading", { name: "Channel B" })).toBeNull();
});
it("updates checking-only detail state without replacing the open draft", async () => {
  const input = await openDraft();
  listRead = async () => response({ sources: [source("channel-a", false)] });
  detailRead = async id => response({ ...detail(id), source: { ...source(id, false), tracking: { ...source(id, false).tracking, health: "OFFLINE" } } });
  await tick();
  expect(within(screen.getByRole("dialog")).getByText("Unable to connect to YouTube. Check your network or VPN and try again.")).toBeTruthy();
  expect(screen.getByLabelText("Focus")).toBe(input);
});
it("keeps the editor through slow and failed detail polling, and resumes reads without replaying commands", async () => {
  active = true; const input = await openDraft(); const pending = deferred<ReturnType<typeof response>>(); detailRead = () => pending.promise;
  await tick(1000); await tick(4000);
  expect(screen.getByLabelText("Focus")).toBe(input); expect(document.activeElement).toBe(input);
  await act(async () => pending.resolve(response({ error: { code: "READ_SERVICE_UNAVAILABLE", message: "offline" } }, 503)));
  expect(screen.getByText("Source details could not be refreshed. Showing previously loaded details.")).toBeTruthy();
  detailRead = async id => response(detail(id));
  fireEvent.click(screen.getAllByRole("button", { name: "Reload page data" })[0]); await flush();
  expect(screen.queryByText("Source details could not be refreshed. Showing previously loaded details.")).toBeNull();
  expect(screen.getByLabelText("Focus")).toBe(input);
  expect(fetcher.mock.calls.filter(([, init]) => ["PUT", "PATCH"].includes(init?.method ?? ""))).toHaveLength(0);
});
it("masks the old source immediately on ID change and ignores a late detail read", async () => {
  active = true; await openDraft(); const late = deferred<ReturnType<typeof response>>();
  detailRead = id => id === "channel-a" ? late.promise : Promise.resolve(response(detail(id)));
  await tick(1000);
  fireEvent.click(screen.getByRole("button", { name: /Channel B/ }));
  expect(screen.queryByLabelText("Focus")).toBeNull(); await flush();
  expect(within(screen.getByRole("dialog")).getByRole("heading", { name: "Channel B" })).toBeTruthy();
  await act(async () => late.resolve(response(detail())));
  expect(within(screen.getByRole("dialog")).queryByRole("heading", { name: "Channel A" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Edit interests" })); await flush();
  expect((screen.getByLabelText("Focus") as HTMLTextAreaElement).value).toBe("robotics, autonomy");
});
it("keeps initial failed reads closed and performs an explicit safe GET recovery", async () => {
  listRead = async () => response({ error: { code: "READ_SERVICE_UNAVAILABLE", message: "offline" } }, 503);
  render(<App />); await flush(); expect(screen.queryByText("Channel A")).toBeNull();
  expect(screen.getByRole("alert").textContent).toContain("temporarily unavailable");
  listRead = async () => response({ sources: [source()] }); fireEvent.click(screen.getByRole("button", { name: "Reload page data" })); await flush();
  expect(screen.getByRole("button", { name: /Channel A/ })).toBeTruthy(); expect(screen.queryByRole("alert")).toBeNull();
});
it("rejects a refresh that drops the established tracking identity instead of replacing the editor with a legacy source", async () => {
  active = true; const input = await openDraft();
  detailRead = async id => response({ ...detail(id), source: { ...source(id), tracking: undefined } });
  await tick(); expect(screen.getByLabelText("Focus")).toBe(input);
  expect(screen.getByText("Source details could not be refreshed. Showing previously loaded details.")).toBeTruthy();
});
