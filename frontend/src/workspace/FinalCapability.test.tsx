import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "./App";

const model = "qwen3.5:9b-q4_K_M", profile = "local-grounding-qwen35-9b-thinking-v1";
const binding = { provider: "ollama", model: "qwen3:8b", profile_id: null };
const matrix = () => ({ status: "KNOWN", model, profile_id: profile, runtime_binding: binding,
  scopes: ["YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT"].flatMap(scope => ["en", "zh-CN"].map(output_language => ({ scope, output_language, model, profile_id: profile, status: "NOT_QUALIFIED" }))) });
const capability = (scope = "YT_TIMED", output_language = "en", video_id = "content-a") => ({ video_id, scope, output_language,
  model, profile_id: profile, runtime_binding: binding, qualification_status: "NOT_QUALIFIED", request_state: "WAITING_MODEL", reason: "NOT_QUALIFIED" });
const item = (scope: string, id = "content-a") => ({ video_id: id, title: `Content ${id}`, provider: scope === "YT_TIMED" ? "YOUTUBE" : "LOCAL", media_kind: scope === "LOCAL_TEXT" ? "TEXT" : "VIDEO", processing_status: "ORGANIZED" });
const detail = (sourceScope: string, id: string, status: unknown) => ({
  video: item(sourceScope, id), local_intelligence: status, transcript: { status: "AVAILABLE", text: "Original source" },
  note: { v2: { status: "AVAILABLE", summary: "Preserved Summary" } }, manual_intelligence_eligible: true,
  cloud_intelligence_available: false, history: [], intelligence_result: { status: "NOT_PROCESSED" }, waiting_model_executions: [],
});
let local: unknown, settingsLocal: unknown, scope: string, waiting: boolean, cancelled: boolean;
let fetcher: ReturnType<typeof vi.fn>;
const response = (data: unknown) => ({ ok: true, json: async () => data });
beforeEach(() => {
  localStorage.setItem("yia.ui-language", "en"); location.hash = "#Content/content-a";
  scope = "YT_TIMED"; local = capability(); settingsLocal = matrix(); waiting = false; cancelled = false;
  fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      if (path.endsWith("/intelligence/cancel")) { waiting = false; cancelled = true; }
      else if (path.endsWith("/intelligence")) waiting = true;
      else throw Error(`Unexpected mutation ${path}`);
      return response({ execution: { status: waiting ? "WAITING_MODEL" : "CANCELLED" } });
    }
    if (path.endsWith("/videos/content-a")) return response({ ...detail(scope, "content-a", local),
      intelligence_result: { status: waiting ? "WAITING_MODEL" : cancelled ? "CANCELLED" : "NOT_PROCESSED" },
      waiting_model_executions: waiting ? [{ execution_id: "wait", can_cancel: true, updated_at: "2026-10-15T00:00:00Z" }] : [] });
    if (path.endsWith("/videos")) return response({ videos: [item(scope)] });
    if (path.endsWith("/settings")) return response({ general: { output_language: "zh-CN", timezone: "Asia/Shanghai" }, providers: [],
      runtime_local_model: { model: "qwen3:8b", status: "READY" }, local_intelligence: settingsLocal });
    if (path.endsWith("/settings/preferences")) return response({ active: [], history: [] });
    if (path.endsWith("/settings/source-policy")) return response({ policy: { focus_rules: [], ignore_rules: [], distillation_style: "BALANCED", initial_history_count: 3, per_run_max_new_videos: 5 } });
    if (path.endsWith("/settings/resource-usage")) return response({ usage: [] });
    return response({});
  }); vi.stubGlobal("fetch", fetcher);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });

it.each(["en", "zh-CN"])("shows six exact qualification rows separately from the fast runtime (%s)", async language => {
  localStorage.setItem("yia.ui-language", language); location.hash = "#Settings"; render(<App />);
  const region = await screen.findByRole("region", { name: language === "en" ? "Local Intelligence qualification" : "本地洞察资格" });
  expect(within(region).getAllByRole("listitem")).toHaveLength(6);
  expect(region.textContent).toContain(model); expect(region.textContent).toContain("English"); expect(region.textContent).toContain("中文");
  expect(region.textContent).not.toContain("qwen3:8b");
  expect(screen.getByText(/qwen3:8b ·/)).toBeTruthy();
  expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it.each(["YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT"].flatMap(s => ["en", "zh-CN"].map(l => [s, l])))("uses server %s/%s and preserves safe wait/cancel without client model authority", async (s, l) => {
  scope = s; local = capability(s, l); render(<App />);
  const region = await screen.findByRole("region", { name: "Local Intelligence for this Content" });
  expect(region.textContent).toContain(model); expect(region.textContent).toContain(l === "en" ? "English" : "中文");
  expect(region.textContent).toContain("qwen3:8b");
  fireEvent.click(screen.getByRole("button", { name: "Extract Intelligence" }));
  await screen.findByRole("button", { name: "Cancel this extraction" });
  const command = JSON.parse(fetcher.mock.calls.find(([, init]) => init?.method === "POST")![1].body as string);
  expect(Object.keys(command)).toEqual(["command_id"]);
  fireEvent.click(screen.getByRole("button", { name: "Cancel this extraction" }));
  await screen.findByText("Extraction cancelled. No Intelligence was generated by this task. Original Content, transcript, Summary and Evidence are preserved.");
  expect(screen.getByText("Preserved Summary")).toBeTruthy();
});

it.each([undefined, null, {}, { ...capability(), model: {} }, { ...capability(), scope: "LOCAL_TEXT" },
  { ...capability(), video_id: "foreign" }, { ...capability(), output_language: "fr" },
  { ...capability(), request_state: "ELIGIBLE_FOR_ADMISSION" }])("closes unknown/malformed/foreign Content capabilities (%j)", async value => {
  local = value; render(<App />);
  await screen.findByRole("button", { name: "Retry local Intelligence status" });
  const button = screen.getByRole("button", { name: "Extract Intelligence" }) as HTMLButtonElement;
  expect(button.disabled).toBe(true);
  local = capability(); fireEvent.click(screen.getByRole("button", { name: "Retry local Intelligence status" }));
  await screen.findByRole("region", { name: "Local Intelligence for this Content" });
  expect((screen.getByRole("button", { name: "Extract Intelligence" }) as HTMLButtonElement).disabled).toBe(false);
  expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it("does not use a qualified callback row as a claim that the current route matches", async () => {
  local = { ...capability(), qualification_status: "QUALIFIED", reason: "ROUTE_REINITIALIZATION_REQUIRED" };
  render(<App />);
  expect(await screen.findByText("The verified model does not match the current route. Restart the local service to reinitialize it; extraction will wait." )).toBeTruthy();
  expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it.each([
  ["ELIGIBLE_FOR_ADMISSION", "ADMISSION_CHECKS_REQUIRED", false, "Qualified for this source and output language. Admission checks still apply."],
  ["WAITING_MODEL", "MODEL_UNAVAILABLE", false, "The qualified model is unavailable. A request will wait; check local model setup."],
  ["UNKNOWN", "RESOURCE_STATUS_UNKNOWN", true, "Local model resource status is unknown. Read the status again before requesting extraction."],
])("keeps qualification distinct from resource/admission %s", async (request_state, reason, disabled, message) => {
  local = { ...capability(), qualification_status: "QUALIFIED", request_state, reason,
    runtime_binding: { provider: "ollama", model, profile_id: profile } };
  render(<App />); expect(await screen.findByText(message as string)).toBeTruthy();
  expect((screen.getByRole("button", { name: "Extract Intelligence" }) as HTMLButtonElement).disabled).toBe(disabled);
  expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it.each([null, {}, { ...matrix(), scopes: matrix().scopes.slice(1) },
  { ...matrix(), scopes: matrix().scopes.map(row => ({ ...row, status: true })) }])("Settings rejects partial or malformed status and recovers with GET (%j)", async value => {
  settingsLocal = value; location.hash = "#Settings"; render(<App />);
  const retry = await screen.findByRole("button", { name: "Retry local Intelligence status" });
  settingsLocal = matrix(); fireEvent.click(retry);
  const region = await screen.findByRole("region", { name: "Local Intelligence qualification" });
  expect(within(region).getAllByRole("listitem")).toHaveLength(6);
  expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it("does not let a late Content capability authorize another Content", async () => {
  let release: (value: unknown) => void = () => {};
  const original = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/content-a")) return await new Promise(resolve => { release = resolve; });
    if (path.endsWith("/videos/content-b")) return response(detail("LOCAL_TEXT", "content-b", capability("LOCAL_TEXT", "zh-CN", "content-b")));
    return original(path, init);
  });
  render(<App />);
  await act(async () => { location.hash = "#Content/content-b"; window.dispatchEvent(new HashChangeEvent("hashchange")); });
  const region = await screen.findByRole("region", { name: "Local Intelligence for this Content" });
  expect(region.textContent).toContain("Local text documents");
  await act(async () => { release(response(detail("YT_TIMED", "content-a", capability()))); });
  expect(screen.getByRole("region", { name: "Local Intelligence for this Content" }).textContent).toContain("Local text documents");
  expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it("shows a failed capability GET and retries explicitly without a request mutation", async () => {
  let failed = true;
  const original = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/videos/content-a') && failed) throw new TypeError('Failed to fetch');
    return original(path, init);
  });
  render(<App />);
  expect(await screen.findByRole('alert')).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Extract Intelligence' })).toBeNull();
  failed = false; fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
  await screen.findByRole('region', { name: 'Local Intelligence for this Content' });
  expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === 'GET')).toBe(true);
});

it("keeps cancellation usable when a later capability is unknown", async () => {
  waiting = true; local = null; render(<App />);
  const cancel = await screen.findByRole('button', { name: 'Cancel this extraction' });
  expect((screen.getByRole('button', { name: 'Extract Intelligence' }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(cancel);
  await screen.findByText('Extraction cancelled. No Intelligence was generated by this task. Original Content, transcript, Summary and Evidence are preserved.');
  const writes = fetcher.mock.calls.filter(([, init]) => init?.method === 'POST');
  expect(writes).toHaveLength(1); expect(writes[0][0]).toContain('/intelligence/cancel');
  expect(screen.getByText('Preserved Summary')).toBeTruthy();
});
