import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";

// Offline UI fixtures only. These are not provider qualification or real calls.
const inputHash = "a".repeat(64), ticket = "b".repeat(64);
function review(overrides: object = {}) {
  return { execution_id: "offline-execution", video_id: "cloud-content", source_id: "offline-source",
    provider: "offline-preview-provider", model: "offline-preview-model", verified_input_hash: inputHash,
    review_hash: ticket, expires_at: new Date(Date.now() + 300_000).toISOString(), output_language: "en",
    evidence_ids: ["offline-evidence"], cost_status: "UNKNOWN", disclosure_version: "m12-cloud-intelligence-v1",
    outgoing_data: { video_id: "cloud-content", video_title: "Offline Content", source_display_name: "Offline source",
      output_language: "en", content_provider: "YOUTUBE",
      evidence: [{ evidence_id: "offline-evidence", excerpt: "Only this verified fixture excerpt leaves the device.", start_ms: 1000, end_ms: 2000 }],
      personalization: ["My fixture interest"], source_focus_rules: ["Fixture focus"], source_ignore_rules: [], distillation_style: "BALANCED" },
    outgoing_request: { model: "offline-preview-model", max_tokens: 8192, messages: [] },
    readiness: { can_confirm: false, blockers: ["CREDENTIAL_REQUIRED", "CLOUD_SPENDING_POLICY_REQUIRED"], budget_state: "CLOUD_SPENDING_POLICY_REQUIRED" },
    ...overrides };
}
function detail(id = "cloud-content", provider = "YOUTUBE") {
  return { video: { video_id: id, provider, title: `Offline Content ${id}`, channel_id: "offline", channel_name: "Offline source",
    source_url: null, processing_status: "COMPLETE", published_at: "2026-10-26T00:00:00Z", last_updated: "2026-10-26T00:00:00Z" },
    transcript: { status: "AVAILABLE", text: "Retained original transcript." },
    note: { v2: { status: "AVAILABLE", summary: "Retained local Summary." } },
    intelligence_result: { status: "WAITING_MODEL", execution_id: null, has_new_intelligence: null },
    cloud_intelligence_available: false, history: [] };
}
let returnedReview: unknown, confirmations: object[], requests: string[], provider = "YOUTUBE";
let profiles: object[], manual = false;
let reviewResponse: (() => Promise<unknown>) | null, confirmResponse: (() => Promise<unknown>) | null;
const response = (body: unknown, ok = true) => Promise.resolve({ ok, json: async () => body } as Response);
beforeEach(() => {
  localStorage.setItem("yia.ui-language", "en");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/cloud-content";
  provider = "YOUTUBE"; returnedReview = review(); confirmations = []; requests = [];
  profiles = []; manual = false;
  reviewResponse = null; confirmResponse = null;
  vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
    requests.push(input);
    if (input.endsWith("/cloud-intelligence/profiles")) return response({ profiles });
    if (input.endsWith("/cloud-intelligence/review")) return response({ review: await (reviewResponse?.() ?? returnedReview) });
    if (input.endsWith("/cloud-intelligence/confirm")) {
      confirmations.push(JSON.parse(String(init?.body)));
      return response(await (confirmResponse?.() ?? { execution: { status: "SUCCEEDED" } }));
    }
    const id = /\/videos\/([^/]+)$/.exec(input)?.[1];
    if (id) return response({ ...detail(id, provider), manual_intelligence_eligible: manual });
    if (input.endsWith("/evidence")) return response({ evidence: [] });
    if (input.endsWith("/videos")) return response({ videos: [detail().video] });
    return response({});
  }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });
async function prepare() {
  fireEvent.click(await screen.findByRole("button", { name: "Review cloud Intelligence" }));
  fireEvent.click(screen.getByRole("button", { name: "Prepare one request for review" }));
}

it.each(["en", "zh-CN"])("opens a keyless read-only review with actual bounded data and blockers (%s)", async language => {
  localStorage.setItem("yia.ui-language", language);
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: language === "en" ? "Review cloud Intelligence" : "查看云端洞察预览" }));
  expect(requests.some(path => path.endsWith("/cloud-intelligence/review"))).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Prepare one request for review" : "准备审核本次请求" }));
  await screen.findByText(/offline-preview-provider/);
  expect(screen.getByText("Only this verified fixture excerpt leaves the device.")).toBeTruthy();
  expect(screen.getByText(/My fixture interest/, { selector: "p" })).toBeTruthy();
  expect(screen.getByText(/Fixture focus/, { selector: "p" })).toBeTruthy();
  expect(screen.getByText(/8192/, { selector: "p" })).toBeTruthy();
  expect(within(screen.getByRole("region", { name: language === "en" ? "Cloud Intelligence disclosure" : "云端洞察数据与费用说明" })).getByRole("link", { name: language === "en" ? "Open model settings" : "打开模型设置" }).getAttribute("href")).toBe("#Settings/models/bigmodel?return=%23Content%2Fcloud-content");
  expect((screen.getByRole("button", { name: language === "en" ? "Authorize this one cloud execution" : "授权本次云端执行" }) as HTMLButtonElement).disabled).toBe(true);
  expect(document.body.textContent).not.toMatch(/¥6\.50|Moonshot API usage/);
  expect(requests.filter(path => /credential|cloud-intelligence\/confirm/.test(path))).toEqual([]);
  expect(confirmations).toEqual([]);
});

it.each(["CREDENTIAL_REQUIRED", "MODEL_UNQUALIFIED", "MODEL_UNAVAILABLE", "CLOUD_SPENDING_POLICY_REQUIRED", "INPUT_NOT_SUPPORTED", "EXECUTION_ALREADY_EXISTS", "UNRECOGNIZED_BLOCKER"])("keeps blocker %s closed", async blocker => {
  returnedReview = review({ readiness: { can_confirm: true, blockers: [blocker], budget_state: "BUDGET_UNVERIFIED" } });
  render(<App />); await prepare(); await screen.findByText(/offline-preview-provider/);
  const confirm = screen.getByRole("button", { name: "Authorize this one cloud execution" });
  expect((confirm as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(confirm); expect(confirmations).toEqual([]);
});
it.each([undefined, null, {}, { can_confirm: "yes", blockers: [] }, { can_confirm: true, blockers: "none" }])("fails closed for malformed readiness %j", async readiness => {
  returnedReview = review({ readiness }); render(<App />); await prepare();
  await screen.findByText(/offline-preview-provider/);
  const confirm = screen.getByRole("button", { name: "Authorize this one cloud execution" });
  expect((confirm as HTMLButtonElement).disabled).toBe(true); fireEvent.click(confirm); expect(confirmations).toEqual([]);
});
it.each([{ expires_at: "invalid" }, { review_hash: "" }, { video_id: "other-content" }])("refuses malformed or mismatched review identity %j", async invalid => {
  returnedReview = review({ ...invalid, readiness: { can_confirm: true, blockers: [], budget_state: "OFFLINE_TEST_ONLY" } });
  render(<App />); await prepare();
  await screen.findByRole("alert");
  expect(screen.queryByRole("button", { name: "Authorize this one cloud execution" })).toBeNull();
  expect(screen.getByText("Retained local Summary.")).toBeTruthy(); expect(confirmations).toEqual([]);
});
it("disables the ticket when it actually expires and offers another review", async () => {
  returnedReview = review({ expires_at: new Date(Date.now() + 250).toISOString(), readiness: { can_confirm: true, blockers: [], budget_state: "OFFLINE_TEST_ONLY" } });
  render(<App />); await prepare(); await screen.findByText(/offline-preview-provider/);
  const confirm = screen.getByRole("button", { name: "Authorize this one cloud execution" });
  await waitFor(() => expect((confirm as HTMLButtonElement).disabled).toBe(true));
  expect(await screen.findByText("This review expired. Prepare a new review before confirming.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Prepare one request for review" })).toBeTruthy();
  fireEvent.click(confirm); expect(confirmations).toEqual([]);
});
it("confirms only the opaque ticket once while busy", async () => {
  returnedReview = review({ readiness: { can_confirm: true, blockers: [], budget_state: "OFFLINE_TEST_ONLY" } });
  let finish!: (result: unknown) => void;
  confirmResponse = () => new Promise(resolve => { finish = resolve; });
  render(<App />); await prepare(); await screen.findByText(/offline-preview-provider/);
  const confirm = screen.getByRole("button", { name: "Authorize this one cloud execution" });
  fireEvent.click(confirm); fireEvent.click(confirm);
  await waitFor(() => expect(confirmations).toEqual([{ execution_id: "offline-execution", review_hash: ticket, authorize: true }]));
  await act(async () => finish({ execution: { status: "SUCCEEDED" } }));
  expect(confirmations).toHaveLength(1);
});
it("dismisses a pending review and ignores its late response", async () => {
  let finish!: (result: unknown) => void;
  reviewResponse = () => new Promise(resolve => { finish = resolve; });
  render(<App />); await prepare();
  fireEvent.click(screen.getByRole("button", { name: "Dismiss cloud review" }));
  await act(async () => finish(review()));
  expect(screen.queryByText(/offline-preview-provider/)).toBeNull(); expect(confirmations).toEqual([]);
  fireEvent.click(screen.getByRole("button", { name: "Review cloud Intelligence" }));
  expect(screen.queryByRole("button", { name: "Authorize this one cloud execution" })).toBeNull();
});
it("does not inject a late old-content review into a new Content", async () => {
  let finish!: (result: unknown) => void;
  reviewResponse = () => new Promise(resolve => { finish = resolve; });
  render(<App />); await prepare();
  await act(async () => { location.hash = "#Content/second-content"; });
  await screen.findByText("Offline Content second-content");
  await act(async () => finish(review()));
  expect(screen.queryByText(/offline-preview-provider/)).toBeNull(); expect(confirmations).toEqual([]);
});
it("navigation and remount discard a review without confirming", async () => {
  const view = render(<App />); await prepare(); await screen.findByText(/offline-preview-provider/);
  view.unmount(); render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Review cloud Intelligence" }));
  expect(screen.queryByText(/offline-preview-provider/)).toBeNull(); expect(confirmations).toEqual([]);
});
it.each(["LOCAL", "BILIBILI"])("offers no operative cloud preview for %s", async source => {
  provider = source; render(<App />); await screen.findByText("Retained local Summary.");
  expect(screen.queryByRole("button", { name: "Review cloud Intelligence" })).toBeNull();
  expect(requests.some(path => path.includes("cloud-intelligence"))).toBe(false);
});
it("retains Content after a refused confirmation and requires a new explicit review", async () => {
  returnedReview = review({ readiness: { can_confirm: true, blockers: [], budget_state: "OFFLINE_TEST_ONLY" } });
  confirmResponse = async () => { throw new Error("Offline simulated refusal"); };
  render(<App />); await prepare(); await screen.findByText(/offline-preview-provider/);
  fireEvent.click(screen.getByRole("button", { name: "Authorize this one cloud execution" }));
  await screen.findByText(/Cloud confirmation was refused or could not be verified/);
  expect(screen.getByText("Retained local Summary.")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Authorize this one cloud execution" })).toBeNull();
  expect(confirmations).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Prepare one request for review" }));
  await screen.findByText(/offline-preview-provider/); expect(confirmations).toHaveLength(1);
});
it("ignores a confirmation response after navigating to another Content", async () => {
  returnedReview = review({ readiness: { can_confirm: true, blockers: [], budget_state: "OFFLINE_TEST_ONLY" } });
  let finish!: (result: unknown) => void;
  confirmResponse = () => new Promise(resolve => { finish = resolve; });
  render(<App />); await prepare(); await screen.findByText(/offline-preview-provider/);
  fireEvent.click(screen.getByRole("button", { name: "Authorize this one cloud execution" }));
  await waitFor(() => expect(confirmations).toHaveLength(1));
  await act(async () => { location.hash = "#Content/second-content"; });
  await screen.findByText("Offline Content second-content");
  const reads = requests.length;
  await act(async () => finish({ execution: { status: "SUCCEEDED" } }));
  expect(screen.queryByText(/Cloud confirmation returned/)).toBeNull();
  expect(requests).toHaveLength(reads); expect(confirmations).toHaveLength(1);
});
it("keeps Content and a Settings action when review preparation fails", async () => {
  reviewResponse = async () => { throw new Error("Offline missing source service"); };
  render(<App />); await prepare();
  expect(await screen.findByText(/The cloud review could not be verified/)).toBeTruthy();
  expect(screen.getByText("Retained local Summary.")).toBeTruthy();
  expect(within(screen.getByRole("region", { name: "Cloud Intelligence disclosure" })).getByRole("link", { name: "Open model settings" })).toBeTruthy();
  expect(confirmations).toEqual([]);
});

it.each(["en", "zh-CN"])("fresh eligible public Content can preview without opening local qualification (%s)", async language => {
  // Reproduce the actual isolated API posture reported by Root for IwglW_hIL_g.
  // Only the response shape is reproduced; no real provider or user data is used.
  const id = "IwglW_hIL_g";
  localStorage.setItem("yia.ui-language", language);
  location.hash = `#Content/${id}`;
  const freshReview = review();
  returnedReview = { ...freshReview, video_id: id,
    outgoing_data: { ...freshReview.outgoing_data, video_id: id } };
  const defaultFetch = globalThis.fetch;
  const writes: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (init?.method === "POST") writes.push(input);
    if (input.endsWith(`/videos/${id}`)) return response({ ...detail(id),
      manual_intelligence_eligible: true, cloud_intelligence_available: false, waiting_model_executions: [],
      intelligence_result: { status: "NOT_PROCESSED", execution_id: null, has_new_intelligence: null,
        intelligence_id: null, revision_id: null, updated_at: null },
      local_intelligence: { video_id: id, scope: "YT_TIMED", output_language: "zh-CN",
        model: "qwen3.5:9b-q4_K_M", profile_id: "local-grounding-qwen35-9b-runtime-0.40.9-v4",
        qualification_status: "NOT_QUALIFIED", runtime_binding: { provider: "ollama", model: "qwen3:8b", profile_id: null },
        request_state: "CONFIGURATION_REQUIRED", reason: "MODEL_CONFIGURATION_REQUIRED" },
    });
    return defaultFetch(input, init);
  }));
  render(<App />);
  const extract = await screen.findByRole("button", { name: language === "en" ? "Extract Intelligence" : "提炼为洞察" });
  expect((extract as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(extract);
  fireEvent.click(await screen.findByRole("button", { name: language === "en" ? "Review cloud Intelligence" : "查看云端洞察预览" }));
  expect(writes).toEqual([]);
  fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Prepare one request for review" : "准备审核本次请求" }));
  await screen.findByText(/offline-preview-provider/);
  expect(writes).toEqual([`/api/v1/videos/${id}/cloud-intelligence/review`]);
  expect((screen.getByRole("button", { name: language === "en" ? "Authorize this one cloud execution" : "授权本次云端执行" }) as HTMLButtonElement).disabled).toBe(true);
  expect(confirmations).toEqual([]);
  expect(screen.getByText("Retained local Summary.")).toBeTruthy();
  expect((extract as HTMLButtonElement).disabled).toBe(true);
});

it("reviews a finite backend synthesis profile with its own output bound and sends only its matching ticket", async () => {
  manual = true;
  profiles = [{ profile_id: "legacy", provider: "moonshot", model: "kimi-k2.6", adapter_available: true, qualified: true },
    { profile_id: "moonshot-k31-system-synthesis-v1-20261029", provider: "moonshot", model: "kimi-k3.1-pro", adapter_available: true, qualified: false }];
  returnedReview = review({ profile_id: "moonshot-k31-system-synthesis-v1-20261029",
    outgoing_request: { model: "offline-preview-model", max_completion_tokens: 5888, messages: [] },
    readiness: { can_confirm: true, blockers: [], budget_state: "OFFLINE_TEST_ONLY" } });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Review cloud Intelligence" }));
  fireEvent.change(await screen.findByRole("combobox", { name: "Cloud model profile" }), { target: { value: "moonshot-k31-system-synthesis-v1-20261029" } });
  fireEvent.click(screen.getByRole("button", { name: "Prepare one request for review" }));
  await screen.findByText(/offline-preview-provider/);
  expect(screen.getByText(/5888/, { selector: "p" })).toBeTruthy();
  expect(screen.getByText(/complete stored Summary as comparison context/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Authorize this one cloud execution" }));
  await waitFor(() => expect(confirmations).toEqual([{ execution_id: "offline-execution", review_hash: ticket, authorize: true,
    profile_id: "moonshot-k31-system-synthesis-v1-20261029" }]));
});

it("offers safe cancellation for a backend-proven unclaimed synthesis reservation while preserving Content", async () => {
  let pending = true;
  const previousFetch = fetch;
  vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
    if (input.endsWith("/videos/cloud-content") && !init?.method) return response({
      ...detail(), intelligence_result: { status: pending ? "PENDING" : "CANCELLED", execution_id: "synthesis-unclaimed", has_new_intelligence: false },
      pending_synthesis_executions: pending ? [{ execution_id: "synthesis-unclaimed", updated_at: "2026-11-04T00:00:00Z", can_cancel: true, selected_provider: "moonshot" }] : [] });
    if (input.endsWith("/intelligence/cancel")) {
      requests.push(input);
      expect(JSON.parse(String(init?.body))).toEqual({ execution_id: "synthesis-unclaimed" });
      pending = false;
      return response({ execution: { status: "CANCELLED", invocation_count: 0 } });
    }
    return previousFetch(input, init);
  }));
  render(<App />);
  expect(await screen.findByText("This extraction has not run. You can safely cancel it, then request extraction again.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Cancel this extraction" }));
  await waitFor(() => expect(requests.filter(path => path.endsWith("/intelligence/cancel"))).toHaveLength(1));
  expect(screen.getByText("Retained local Summary.")).toBeTruthy();
  expect(confirmations).toEqual([]);
});
