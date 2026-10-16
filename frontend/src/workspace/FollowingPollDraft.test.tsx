import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "./App";
import { CreatorFollowingDetail } from "./CreatorFollowing";
import { UiLanguageProvider } from "./uiLanguage";

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
    if (url.endsWith("/settings/source-policy")) return response({ policy: detail().policy });
    if (/\/sources\/[^/]+$/.test(url)) return detailRead(url.split("/").at(-1)!);
    return response({});
  }); vi.stubGlobal("fetch", fetcher);
});

// The matrix follows the consumer table in the task handoff, across visible,
// legacy and hidden row types. Each mutation goes through the actual App tree.
const rowKinds = ["tracked", "creator", "local", "bilibili", "video", "legacy", "generic"] as const;
const contractRow = (kind: typeof rowKinds[number]) => ({
  ...source(`row-${kind}`, false), display_name: `Row ${kind}`,
  provider: kind === "local" ? "LOCAL" : ["bilibili", "creator"].includes(kind) ? "BILIBILI" : kind === "generic" ? undefined : "YOUTUBE",
  source_type: kind === "local" ? "LOCAL_LIBRARY" : kind === "creator" ? "CREATOR" : ["bilibili", "video"].includes(kind) ? "VIDEO_URL" : kind === "generic" ? undefined : "CHANNEL",
  tracking: ["tracked", "creator"].includes(kind) ? source().tracking : null,
  processing_policy: "STANDARD_INTELLIGENCE", tracking_parent_source_ids: [], insight_count: 0,
});
const withField = (input: unknown, path: string, value: unknown) => {
  const result = JSON.parse(JSON.stringify(input));
  const keys = path.split("."); let target = result;
  for (const key of keys.slice(0, -1)) target = target[key] ??= {};
  target[keys.at(-1)!] = value; return result;
};
const sourceMutations: [string, unknown][] = [
  ["source_id", {}], ["source_id", ""], ["canonical_url", {}], ["enabled", null],
  ["display_name", {}], ["friendly_name", {}], ["channel_id", {}], ["video_id", {}],
  ["provider", {}], ["provider", "UNKNOWN"], ["source_type", {}], ["source_type", "UNKNOWN"],
  ["processing_policy", {}], ["processing_policy", "UNKNOWN"], ["processing_mode", {}], ["processing_mode", "UNKNOWN"],
  ["tracking_parent_source_ids", {}], ["tracking_parent_source_ids", "parent"], ["tracking_parent_source_ids", [null]],
  ["insight_count", {}], ["insight_count", -1], ["last_error", "error"], ["last_error", []], ["last_error", {}],
  ["last_error.code", {}], ["last_error.code", ""], ["last_error.code", "__proto__"], ["last_error.message", {}],
  ["last_checked_at", {}], ["last_checked_at", "invalid date"], ["last_success_at", {}], ["tracking", []],
];
describe.each(rowKinds)("source consumer contract: %s", kind => {
  it.each(sourceMutations)("rejects %s=%j without losing any loaded row or the focused draft", async (path, value) => {
    const rows = [source(), ...rowKinds.map(contractRow)]; listRead = async () => response({ sources: rows });
    const input = await openDraft(); (input as HTMLTextAreaElement).setSelectionRange(2, 5);
    const loadedRows = [...document.querySelectorAll("[data-source-id]")];
    listRead = async () => response({ sources: rows.map(row => row.source_id === `row-${kind}`
      ? withField(path === "last_error.message" ? { ...row, last_error: { code: "OFFLINE", message: null } } : row, path, value) : row) });
    await tick();
    expect(screen.getByText("The Following list could not be refreshed. Showing previously loaded sources.")).toBeTruthy();
    expect([...document.querySelectorAll("[data-source-id]")]).toEqual(loadedRows);
    expect(screen.getByLabelText("Focus")).toBe(input); expect(document.activeElement).toBe(input);
    expect([(input as HTMLTextAreaElement).value, (input as HTMLTextAreaElement).selectionStart, (input as HTMLTextAreaElement).selectionEnd]).toEqual(["unsaved，draft\nwith  spaces", 2, 5]);
    listRead = async () => response({ sources: rows }); fireEvent.click(screen.getByRole("button", { name: "Reload page data" })); await flush();
    expect(screen.queryByText("The Following list could not be refreshed. Showing previously loaded sources.")).toBeNull();
    expect(screen.getByLabelText("Focus")).toBe(input);
    expect(fetcher.mock.calls.filter(([, init]) => ["PUT", "PATCH"].includes(init?.method ?? ""))).toHaveLength(0);
  });
});

const genericDetail = () => ({ ...detail("row-generic"), source: contractRow("generic"),
  schedules: [{ schedule_id: "schedule", frequency: "DAILY", enabled: true, local_time: "09:00", timezone: "UTC", weekday: null, target_id: "row-generic" }],
  source_runs: [{ run_id: "active", state: "RUNNING", attention_reason: null, source_id: "row-generic" }],
  recent_videos: [{ video_id: "video", title: "Stored video", processing_status: "IMPORTED", filter: { outcome: "UNCERTAIN", reason: "NO_FOCUS_RULES", source_id: "row-generic", video_id: "video" } }],
});
const genericMutations: [string, unknown][] = [
  ["policy", null], ["policy.initial_history_count", {}], ["policy.per_run_max_new_videos", {}],
  ["policy.focus_rules", null], ["policy.focus_rules", [{}]], ["policy.ignore_rules", {}],
  ["policy.distillation_style", {}], ["policy.source_id", "foreign"], ["policy.source_policy_revision_id", {}],
  ["policy_modes", null], ["policy_modes.focus", {}], ["policy_modes.ignore", "UNKNOWN"], ["policy_modes.style", {}],
  ["schedules", null], ["schedules.0", null], ["schedules.0.schedule_id", {}], ["schedules.0.frequency", {}],
  ["schedules.0.enabled", "false"], ["schedules.0.local_time", {}], ["schedules.0.timezone", {}], ["schedules.0.weekday", {}], ["schedules.0.target_id", "foreign"],
  ["source_runs.0.attention_reason", {}], ["source_runs.0.attention_reason", "__proto__"], ["source_runs.0.state", "__proto__"],
  ["recent_videos.0.filter.outcome", {}], ["recent_videos.0.filter.reason", "__proto__"],
  ["recent_videos.0.filter.source_id", "foreign"], ["recent_videos.0.filter.video_id", "foreign"],
  ["recent_videos.0.processing_status", "__proto__"],
];
it.each(genericMutations)("generic detail consumer rejects %s=%j while preserving the actual configuration draft", async (path, value) => {
  listRead = async () => response({ sources: [source(), contractRow("generic")] });
  detailRead = async () => response(genericDetail()); render(<App />); await flush();
  fireEvent.click(screen.getByRole("button", { name: /Row generic/ })); await flush();
  fireEvent.click(screen.getByRole("button", { name: "Edit configuration" })); await flush();
  const editor = screen.getByRole("dialog", { name: "Edit Source configuration" });
  fireEvent.click(within(editor).getByText("Advanced source configuration"));
  const input = screen.getByLabelText("Focus"); input.focus(); fireEvent.change(input, { target: { value: "generic，draft\nwith  spaces" } });
  (input as HTMLTextAreaElement).setSelectionRange(2, 5);
  detailRead = async () => response(withField(genericDetail(), path, value)); await tick(1000);
  expect(within(editor).getByText("Source details could not be refreshed. Showing previously loaded details.")).toBeTruthy();
  expect(screen.getByLabelText("Focus")).toBe(input); expect(document.activeElement).toBe(input);
  expect([(input as HTMLTextAreaElement).value, (input as HTMLTextAreaElement).selectionStart, (input as HTMLTextAreaElement).selectionEnd]).toEqual(["generic，draft\nwith  spaces", 2, 5]);
  detailRead = async () => response(genericDetail()); fireEvent.click(within(editor).getByRole("button", { name: "Reload page data" })); await flush();
  expect(screen.queryByText("Source details could not be refreshed. Showing previously loaded details.")).toBeNull(); expect(screen.getByLabelText("Focus")).toBe(input);
  expect(fetcher.mock.calls.filter(([, init]) => ["PUT", "PATCH"].includes(init?.method ?? ""))).toHaveLength(0);
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

const malformedDetails: [string, (id: string) => unknown][] = [
  ["null run", id => ({ ...detail(id), source_runs: [null] })],
  ["empty run", id => ({ ...detail(id), source_runs: [{}] })],
  ["wrong run state", id => ({ ...detail(id), source_runs: [{ state: {} }] })],
  ["empty run state", id => ({ ...detail(id), source_runs: [{ state: "" }] })],
  ["wrong run identity", id => ({ ...detail(id), source_runs: [{ state: "RUNNING", run_id: {} }] })],
  ["foreign run", id => ({ ...detail(id), source_runs: [{ state: "RUNNING", source_id: "foreign" }] })],
  ["null video", id => ({ ...detail(id), recent_videos: [null] })],
  ["empty video", id => ({ ...detail(id), recent_videos: [{}] })],
  ["wrong video title", id => ({ ...detail(id), recent_videos: [{ video_id: "video", title: {}, processing_status: "IMPORTED" }] })],
  ["wrong video status", id => ({ ...detail(id), recent_videos: [{ video_id: "video", title: null, processing_status: {} }] })],
  ["foreign video", id => ({ ...detail(id), recent_videos: [{ video_id: "video", title: null, processing_status: "IMPORTED", source_id: "foreign" }] })],
  ["primitive tracking", id => ({ ...detail(id), source: { ...source(id), tracking: true } })],
  ["empty tracking", id => ({ ...detail(id), source: { ...source(id), tracking: {} } })],
  ["wrong checking", id => ({ ...detail(id), source: { ...source(id), tracking: { ...source(id).tracking, checking: "false" } } })],
  ["wrong count", id => ({ ...detail(id), source: { ...source(id), tracking: { ...source(id).tracking, update_count: {} } } })],
  ["negative count", id => ({ ...detail(id), source: { ...source(id), tracking: { ...source(id).tracking, pending_count: -1 } } })],
  ["wrong date", id => ({ ...detail(id), source: { ...source(id), tracking: { ...source(id).tracking, manual_check_at: {} } } })],
  ["wrong source label", id => ({ ...detail(id), source: { ...source(id), display_name: {} } })],
  ...sourceMutations.map(([path, value]): [string, (id: string) => unknown] => [`source.${path}=${JSON.stringify(value)}`, id => ({
    ...detail(id), source: withField(path === "last_error.message" ? { ...source(id), last_error: { code: "OFFLINE", message: null } } : source(id), path, value),
  })]),
  ...["health", "coverage", "update_count", "pending_count", "unavailable_count", "processing_count", "checking", "verified_at", "baseline_at", "next_check_at", "manual_check_at"].map((key): [string, (id: string) => unknown] => [`tracking.${key}`, id => ({ ...detail(id), source: withField(source(id), `tracking.${key}`, {}) })]),
  ["tracking prototype health", id => ({ ...detail(id), source: withField(source(id), "tracking.health", "__proto__") })],
  ["tracking invalid date", id => ({ ...detail(id), source: withField(source(id), "tracking.next_check_at", "invalid date") })],
  ["null runs container", id => ({ ...detail(id), source_runs: null })],
  ["null videos container", id => ({ ...detail(id), recent_videos: null })],
];
describe.each(["App", "Creator"])("%s rejects malformed detail members before replacing the loaded tree", surface => {
  it.each(malformedDetails)("preserves the focused draft on %s and recovers with GET only", async (_name, malformed) => {
    active = true;
    let input: HTMLElement;
    if (surface === "App") input = await openDraft();
    else {
      render(<UiLanguageProvider><CreatorFollowingDetail id="channel-a" capability={{ known: true, capability: { available: true, code: "AVAILABLE" } }} onClose={() => {}} onRefresh={() => {}} /></UiLanguageProvider>);
      await flush(); fireEvent.click(screen.getByRole("button", { name: "Edit interests" })); await flush();
      input = screen.getByLabelText("Focus"); input.focus(); fireEvent.change(input, { target: { value: "unsaved，draft\nwith  spaces" } });
    }
    (input as HTMLTextAreaElement).setSelectionRange(2, 5);
    detailRead = async id => response(malformed(id)); await tick();
    expect(screen.getByLabelText("Focus")).toBe(input); expect(document.activeElement).toBe(input);
    expect((input as HTMLTextAreaElement).value).toBe("unsaved，draft\nwith  spaces");
    expect((input as HTMLTextAreaElement).selectionStart).toBe(2); expect((input as HTMLTextAreaElement).selectionEnd).toBe(5);
    expect(screen.getByText("Source details could not be loaded. Check the local connection and retry. Stored Content is preserved.")).toBeTruthy();
    if (surface === "App") expect(screen.getByText("Source details could not be refreshed. Showing previously loaded details.")).toBeTruthy();
    detailRead = async id => response(detail(id));
    if (surface === "App") fireEvent.click(screen.getByRole("button", { name: "Reload page data" }));
    fireEvent.click(screen.getByRole("button", { name: "Retry source details" })); await flush();
    expect(screen.queryByText("Source details could not be loaded. Check the local connection and retry. Stored Content is preserved.")).toBeNull();
    expect(screen.queryByText("Source details could not be refreshed. Showing previously loaded details.")).toBeNull();
    expect(screen.getByLabelText("Focus")).toBe(input);
    expect(fetcher.mock.calls.filter(([, init]) => ["PUT", "PATCH"].includes(init?.method ?? ""))).toHaveLength(0);
  });
});

it.each(["legacy", "local", "bilibili"] as const)("retains the %s detail DOM on a failed refresh and recovers with GET", async kind => {
  const row = { ...contractRow(kind), source_type: kind === "bilibili" ? undefined : contractRow(kind).source_type };
  const good = { ...detail(row.source_id), source: row, source_runs: [{ state: "RUNNING", run_id: "active" }] };
  listRead = async () => response({ sources: [source(), row] }); detailRead = async () => response(good);
  render(<App />); await flush(); fireEvent.click(screen.getByRole("button", { name: kind === "local" ? /Local library/ : new RegExp(`Row ${kind}`) })); await flush();
  const modal = screen.getByRole("dialog"); const close = within(modal).getByRole("button", { name: "Close" }); close.focus();
  detailRead = async () => response({ ...good, recent_videos: [null] }); await tick(1000);
  expect(screen.getByRole("dialog")).toBe(modal); expect(document.activeElement).toBe(close);
  expect(within(modal).getByText("Source details could not be refreshed. Showing previously loaded details.")).toBeTruthy();
  detailRead = async () => response(good); fireEvent.click(screen.getByRole("button", { name: "Reload page data" })); await flush();
  expect(screen.getByRole("dialog")).toBe(modal); expect(screen.queryByText("Source details could not be refreshed. Showing previously loaded details.")).toBeNull();
  expect(fetcher.mock.calls.filter(([, init]) => ["PUT", "PATCH"].includes(init?.method ?? ""))).toHaveLength(0);
});

it("accepts legal nullable and legacy snapshots, future machine tokens and unused DTO extensions", async () => {
  const rows = [source(), ...rowKinds.map(kind => ({ ...contractRow(kind), friendly_name: null, channel_id: null, video_id: null,
    processing_mode: null, last_error: { code: "FUTURE_ERROR_99", message: null }, unused_extension: { any: [null] } }))];
  listRead = async () => response({ sources: rows });
  const input = await openDraft();
  detailRead = async id => response({ ...detail(id), source: { ...source(id, false), display_name: null,
    tracking: { ...source().tracking, checking: false, health: "FUTURE_HEALTH_99", verified_at: null, baseline_at: null, next_check_at: null, manual_check_at: null },
    last_error: { code: "FUTURE_ERROR_99" }, unused_extension: { any: [null] } },
    recent_videos: [{ video_id: "video", title: null, processing_status: "FUTURE_STATUS_99" }], source_runs: [] });
  await tick(); expect(screen.getByLabelText("Focus")).toBe(input);
  expect(screen.getByRole("link", { name: "video" })).toBeTruthy(); expect(screen.queryByRole("alert")).toBeNull();
  expect(document.querySelectorAll("[data-source-id]").length).toBe(6); // two VIDEO_URL rows remain intentionally hidden
});

it("rejects duplicate source identities as a failed whole-list read", async () => {
  const input = await openDraft(); listRead = async () => response({ sources: [source(), source()] }); await tick();
  expect(screen.getByText("The Following list could not be refreshed. Showing previously loaded sources.")).toBeTruthy();
  expect(screen.getByLabelText("Focus")).toBe(input); expect(document.activeElement).toBe(input);
});
